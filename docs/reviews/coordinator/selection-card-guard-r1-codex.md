# Codex adversarial review — the selection-card guard, round 1

**Subject:** commit `4fe410ca` only — `scripts/check-selection-card.py`,
`.claude/hooks/enforce-selection-card.sh`, `scripts/mutations/check-selection-card.json` and the
small edits to `.claude/settings.json`, `check-plan-code.py`, `check-selftest-counts.py`,
`dev-process.md`, `portable-practices.md`. Everything earlier on the branch is `gen-backlog-page`
and had four rounds of its own.
**Reviewer:** `codex exec` via `scripts/codex-review.py`, model `gpt-5.5`.
**Verdict file:** `docs/reviews/verdicts/selection-card-guard-r1-codex.verdict.json` (`gate_ran=true`).

**1 Blocking, 1 High, 1 Medium, 1 Low. All four taken.** Its Blocking — the hook fails open on the
bare tool-input shape the checker was written to accept — was found independently of the Claude
half, which found a different Blocking (the block message prescribing an option the tool's schema
refuses). It also ran the full harness independently: `37 files / 405 mutations / 0 survivors`.

⚠ Its High and the Claude half's M-2 wanted the `(Recommended)` token to move in OPPOSITE
directions — stricter, to stop prose collisions; looser, to allow §19's own "with its reason".
Anchoring the marker at the END of the label satisfies both and is what shipped.

Everything below the rule is the reviewer's final message verbatim.

---

<!-- codex-review: model=gpt-5.5 -->

**Subject Proof**

`git show --stat HEAD`:

```text
commit 4fe410caee3545db4055cc906c667111b765b5ff
 .claude/hooks/enforce-selection-card.sh     |  71 +++++++
 .claude/settings.json                       |   9 +
 docs/dev-process.md                         |   2 +-
 docs/portable-practices.md                  |  10 +
 scripts/check-plan-code.py                  |   9 +-
 scripts/check-selection-card.py             | 288 ++++++++++++++++++++++++++++
 scripts/check-selftest-counts.py            |   4 +
 scripts/mutations/check-selection-card.json |  68 +++++++
 8 files changed, 459 insertions(+), 2 deletions(-)
```

`python3 scripts/check-selection-card.py --self-test | tail -2`:

```text

24/24 passed
```

Two exact lines from `scripts/check-selection-card.py`:

```python
LETTER = re.compile(r"^([A-Z])\s*[—–-]\s+\S")
return 2
```

**Blocking**

`.claude/hooks/enforce-selection-card.sh:32-41` fails open before invoking the checker for an `AskUserQuestion` payload shape the checker explicitly supports.

Quoted code:

```bash
IS_CARD=$(echo "$INPUT" | python3 -c '
```

```bash
print("yes" if d.get("tool_name") == "AskUserQuestion" else "no")
```

```bash
[[ "$IS_CARD" == "yes" ]] || exit 0
```

Concrete failing input:

```json
{"questions":[{"header":"Mode","question":"Which implementation path?","options":[{"label":"Ship it","description":"short"},{"label":"Maybe later","description":"short"}]}]}
```

Observed: `python3 scripts/check-selection-card.py` returns `2`; `.claude/hooks/enforce-selection-card.sh` returns `0`.

Change I would make: because `.claude/settings.json:41` already scopes this hook to `AskUserQuestion`, remove the shell-side `IS_CARD` gate and always run `scripts/check-selection-card.py`. If the envelope is malformed, let the checker’s `CANNOT RUN` path block. Also add a hook self-test or manifest entry for bare tool input through the hook.

**High**

`scripts/check-selection-card.py:101` treats any prose occurrence of `(Recommended)` as the recommendation marker.

Quoted code:

```python
marked = [i for i, label in enumerate(labels) if RECOMMENDED in label]
```

Concrete failing input that passes:

```json
{"questions":[{"header":"Copy","question":"Which copy should I use? A/B differ in tone.","options":[{"label":"A — Explain what (Recommended) means in prose","description":"This teaches the reader the term without selecting this path as the advised one."},{"label":"B — Use plainer wording","description":"This avoids the term entirely, but loses consistency with the existing docs."},{"label":"C — I have a question about these","description":""}]}]}
```

This is plainly not marking option A as recommended; it is discussing the literal marker. Observed checker rc: `0`.

Change I would make: require the marker in a constrained position, e.g. `\s\(Recommended\)$` on the label, and add a self-test named something like “mentioning `(Recommended)` in prose is not a recommendation marker.”

**Medium**

`scripts/check-selection-card.py:126` rejects a concise option that already states rationale and trade-off, because the 40-character floor is a proxy rather than the §19 rule.

Quoted code:

```python
if len(desc.strip()) < MIN_DESCRIPTION:
```

Concrete failing input:

```json
{"questions":[{"header":"Run","question":"Run the gate? A/B differ in whether we spend time now.","options":[{"label":"A — Run it now (Recommended)","description":"Fast, exact, costs 30s."},{"label":"B — Skip it for now","description":"Saves time, leaves uncertainty."},{"label":"C — I have a question about these","description":""}]}]}
```

Observed checker rc: `2`. This is a real false positive risk: short rationale/trade-off text can be thoughtful.

Change I would make: either lower the floor substantially, or make this warning-only in the hook text, or replace the length proxy with a narrower bare-label detector.

**Low**

No surviving mutations found for the six new manifest entries. I isolated each `scripts/mutations/check-selection-card.json` entry; all six returned `ok=True`, `survivors=[]`, and each died through its named `expect`. Full delivered mutation run also passed:

```text
OK — delivered scripts mutated: 37 file(s), 405 mutation(s), 0 survivor(s)
```

Unfalsifiable/semantic cases remain explicitly out of scope. The self-test case “two options that are the SAME WORK pass — this guard cannot see that” passes by design; axis quality and rationale truth are also not machine-checked. That limitation is honestly documented at `scripts/check-selection-card.py:33-39` and `docs/portable-practices.md:821-824`.

Scope check: retiring the `gh` two-remotes row from `docs/dev-process.md` is safe. The full account is present at `docs/process-rationale.md:292`, and the old spine row existed at `HEAD^:docs/dev-process.md:218`. I found no remaining citation to that spine row; current `docs/dev-process.md` is still exactly 220 lines.

Verdict: NOT CONVERGED.
