# Block-start divergence — review round 1 (branch `fix-block-start-divergence`, 41eaf27a)

**ROUND VERDICT: NOT CONVERGED at dispatch — 3 Blocking, all now addressed. Re-verified by `--mutate .`.**

Both halves ran. Scope: the whole branch diff over `scripts/`.

## Half 1 — Codex (`gpt-5.5`, gate_ran=true)

Captured from the final message per the output contract; verdict at `docs/reviews/verdicts/codex-review.verdict.json`.
It ran the suites itself and ran `--mutate .`, which is how it found B1 and B2 — neither was visible by reading.

<!-- codex-review: model=gpt-5.5 -->

**Blocking** [scripts/mutations/check-dashboard-entry.json:234](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-dashboard-entry.json:234)

```json
"expect": [
  "the block-start rule excludes a sub-heading",
  "a level-3 heading does not split the entry"
]
```

`python3 scripts/check-plan-code.py --mutate .` fails. The second expected case is not in `check-dashboard-entry.py --self-test`, so the harness reports 0 matches:

```text
expect 'a level-3 heading does not split the entry' matched 0 red case(s)
```

This is not hidden coverage; it is a failing mutation manifest. The held gate count at 29 is plausible as a retarget, but the retarget’s `expect` is invalid.

**Blocking** [scripts/mutations/gen-dashboard.json:813](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/gen-dashboard.json:813)

```json
"expect": [
  "a level-3 heading does not split the entry",
  "and the prose after it is not lost"
]
```

The actual case name is:

```python
case("...and the prose after it is not lost",
```

at [scripts/gen-dashboard.py:1612](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:1612). The harness requires exact equality, and the mutation run fails with 0 matches for `"and the prose after it is not lost"`.

**Blocking** [scripts/gen-dashboard.py:443](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:443)

```python
for line in text.split("\n"):
    if BLOCK.match(line):
        blocks.append([line])
    elif blocks:
        blocks[-1].append(line)
```

Confirmed. There is no fence awareness here. A fenced column-0 block start creates a real parsed entry and consumes an id. I reproduced this shape:

```text
## 2026-08-27/1
```

then fenced:

```text
## 2026-08-28
```

then later resolution. `parse_entries` returned a bogus `2026-08-28/1`. Since ids are positional and `[resolved: id]` binds by id, shipping with this known parser defect is wrong. Spec §6.2 says:

```text
`##` inside detail | only column-0 `## ` splits blocks; indent or fence it to include one literally
```

at [docs/superpowers/specs/2026-08-28-project-dashboard-design.md:121](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-28-project-dashboard-design.md:121).

**Medium** [scripts/check-dashboard-entry.py:43](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-dashboard-entry.py:43)

```python
BLOCK = re.compile(r"^##(?!#)\s*\S")
```

Direction is right about `###`: the spec says block start is `## `, not H3, so the prior handoff blaming `(?!#)` is refuted. But the implementation still does not implement the literal spec grammar because it accepts `##Nospace`. The comment defends that:

```python
# It stays PERMISSIVE about the space (`##Nospace` still starts a block) on
# purpose
```

at [scripts/check-dashboard-entry.py:39](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-dashboard-entry.py:39). That distinction is defensible as a malformed-entry visibility policy, but it is not the spec’s “Block start” rule. The naming/comment should state “block attempt” or “parser recovery start,” not imply exact §6.2 compliance.

**Low** [scripts/check-dashboard-entry.py:520](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-dashboard-entry.py:520)

```python
_agree = [(ln, bool(BLOCK.match(ln)) == bool(ENTRY_ISH.match("+" + ln)))
```

This verifies agreement, not derivation. A future edit could retype `ENTRY_ISH` independently but keep the listed examples aligned. Not vacuous for this fix, but weaker than the comment claims.

Refutations / confirmations:

Direction: your reading is right. §6.2 settles against `###` splitting blocks.

Derivation: `BLOCK.pattern.lstrip("^")` is safe for the current pattern, producing `^\+##(?!#)\s*\S`. It would strip multiple leading `^` characters if someone wrote them, so `removeprefix("^")` is cleaner, but not a current bug. Behavior did change: `+## ` and `+##` used to match `^\+##(?!#)` and no longer match. I do not think that matters for meaningful coverage; `+##2026-08-28` and `+## x` are still caught as malformed attempts.

Self-tests run:
`python3 scripts/check-dashboard-entry.py --self-test` passed: `112/112`, impure `13/13`.
`python3 scripts/gen-dashboard.py --self-test` passed: `301/301`.
`python3 scripts/check-plan-code.py --mutate .` failed: `155 mutation(s), 0 survivor(s)`, due to the two invalid `expect` strings above.

## Half 2 — Claude

⛔ **REVIEW GAP: claude — author self-review, NOT an independent half.** The session's
instructions forbid spawning subagents unless the user asks, so this half was performed by the
author of the change rather than a fresh reviewer with no stake in it. That is structurally
weaker: an author cannot easily see the assumption they built on. Recorded rather than hidden,
and re-runnable as an independent pass before merge if wanted.

**Finding C1 (Medium, FIXED) — the agreement case was an unproven guard.**
Answering the Codex half's Low. `case("the gate and the page agree on every block-start shape")`
is NOT vacuous — measured by re-typing `ENTRY_ISH` as `^\+##` on a temp copy, it goes red and
names the diverging shapes: `['### Worth knowing', '#### deeper', '## ']`. But nothing PROVED it
fired, and the existing `BLOCK` mutation provably cannot: corrupting the shared rule moves both
sides together, so the agreement case stays green. New mutation `the added-line rule is re-typed
instead of derived` closes it. `EXPECTED_MUTATIONS` gate 29 -> 30, total 155 -> 156.

**Finding C2 (Low, FIXED) — `lstrip("^")` strips a class, not a prefix.**
Adopting the Codex half's suggestion. `"^^x".lstrip("^")` yields `"x"`, dropping both anchors.
Not reachable today, but the line's whole purpose is derivation-by-construction and a
character-class strip is the wrong primitive for it. Now `removeprefix("^")`.

**Finding C3 (Low, FIXED) — `BLOCK`'s comment implied §6.2 compliance it does not have.**
Also the Codex half's Medium, and it is right. `BLOCK` accepts `##Nospace`, which §6.2's "Block
start" row does not. The comment now says block-ATTEMPT explicitly, states the gap as parser
recovery policy rather than grammar, and confines the §6.2 claim to the `###` rule, which is the
part that was actually broken.

**Finding C4 (process, RECORDED) — I asserted the harness's behaviour without running it.**
I told the user "the harness runs all suites per mutation". It does not: `mutate_delivered` calls
`run_suite(d, fname)` for the mutated file alone (`check-plan-code.py:694`). That false belief is
exactly what produced B1 — a renderer case named in a gate manifest. Same shape as the defect this
branch fixes, and as the handoff's "several entries use one": a confident statement about a
mechanism, written without running the mechanism. The Codex half caught it only because it ran
`--mutate .` rather than reading.

**Confirmed, not merely agreed:** the Codex half's B3 (fence-blindness in `parse_entries`)
reproduced independently before it was reported — writing this branch's own dashboard entry with a
fenced `## 2026-08-28` split the entry and minted a bogus `2026-08-28/2`. NOT fixed here; see the
disposition below.

## Dispositions

| # | Sev | Finding | Disposition |
|---|---|---|---|
| B1 | Blocking | gate manifest `expect` named a renderer case -> 0 red matches | FIXED — names gate-suite cases only |
| B2 | Blocking | `expect` dropped the leading `...` -> exact-match miss | FIXED — verbatim names |
| B3 | Blocking | `parse_entries` has no fence awareness; a fenced `##` splits an entry and STEALS an id | **DEFERRED, user decision pending.** Pre-existing, not introduced here; separate defect class needing its own tests and mutations. Documented in entry 2026-09-01/16 |
| Cx-Med | Medium | `BLOCK` naming implied §6.2 compliance | FIXED (C3) |
| Cx-Low | Low | agreement case verifies agreement, not derivation | FIXED (C1) — mutation added |
| C2 | Low | `lstrip("^")` vs `removeprefix("^")` | FIXED |
| C4 | process | author asserted harness behaviour unrun | RECORDED |

**Direction check — both halves agree and both read §6.2 directly:** the prior handoff
blamed the gate; the spec refutes it. Block start is `## ` at column 0 WITH the space, and
"only column-0 `## ` splits blocks". The page was the divergent side.

**Re-verification after fixes:** gate 112/112 + 13/13; renderer 301/301; plan-code 158/158;
`--mutate .` 7 files, **156 mutations, 0 survivors**, rc=0.
