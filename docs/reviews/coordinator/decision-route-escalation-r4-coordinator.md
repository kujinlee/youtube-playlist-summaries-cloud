```yaml
round: 4
subject: decision-route-escalation
writer: coordinator
fixes_nontrivial: true
findings:
  - id: C1
    severity: High
    aim: instrument
    fix_induced: false
    component: sweep-skip
    disposition: fixed
  - id: C2
    severity: Medium
    aim: instrument
    fix_induced: true
    component: sweep-skip
    disposition: fixed
  - id: C3
    severity: High
    aim: instrument
    fix_induced: false
    component: thrashing-arming
    disposition: filed
```

# Adversarial review — `decision-route-escalation` r4 (COORDINATOR half)

**Subject:** the 17 files in `git diff ea119c82..c8c3f226` — the implementation that followed the
design reviewed in r1–r3, reviewed by nobody until this round.
**Tree:** `c8c3f226`. **Date:** 2026-10-21.

**Why this round exists, from the gate rather than from the handoff:** `check-review-recorded.py`
exits **1** — *"7 round(s) ran and guarded code was committed after every one of them."* ⚠ My first
run of it reported `rc=0` beside the word FAILED, because I piped it to `head`; the zero was
`head`'s. Re-run unpiped: `GATE_RC=1`. Recorded because it is the cheapest possible instance of this
repo's own rule about reading `$?` after a pipe, committed by the person applying the rule.

**Verdict: NOT CONVERGED** — on the findings below and the three High findings the other two halves
filed, not on mood. ⚠ "NOT CONVERGED" is this corpus's base rate (0 of 12 subjects converge), so the
verdict carries information only because each finding names a reproducible input.

---

## Round topology, and what it measured about the halves

Three independent halves ran against one brief: CODEX (`gpt-6.1-sol`), CLAUDE (subagent), and this
one. The brief told all three to EXECUTE rather than read, and to REFUTE named claims rather than
confirm them.

| Finding | CODEX | CLAUDE | coordinator |
|---|---|---|---|
| `\|\| true` → a failed diff silently disables the sweep | #1 High | H2 High | C1 |
| `scripts/`-only ≠ unchanged mutation inputs (`HARNESS_TREE`) | #2 High | — | verified, upgraded |
| transcript guard inert: rc discarded, stderr not stdout | — | **H1 High** | — |
| `convergence_unreachable` drifted from `converged` | #5 **Low** | **H3 High** | adjudicated below |
| corrupt transcript passes quiet | #3 Medium | (within H1) | — |
| reference rule duplicated / scope list incomplete | #4 Low | M1 M2 L1 L2 | — |

⭐ **ONE finding of six was found by all three halves; two were found by exactly one.** That is the
measured case for not skipping a half, restated: a Codex-only round would have shipped H1 (a
302-line guard that reaches nobody), and a Claude-only round would have shipped finding 2 (a skip
that drops real coverage). Neither half was lazy about the other's finding — each asked a different
question, and a verdict is only ever a statement about the questions that reviewer asked.

**Adjudication of the one severity split (CODEX Low vs CLAUDE High), done by reading the code rather
than averaging:** CLAUDE's is right, and the discriminator is reachability by a reader. Both halves
correctly identified that `convergence_unreachable` re-derives `converged`'s rule without the
`disposition` clause. CLAUDE additionally showed the contradiction **escapes through `decide`**,
which prints a demand for *"rounds with no Blocking/High"* — precisely the demand backlog #329
measured as unsatisfiable and removed. A diagnostic instructing a reader to produce an artifact the
workflow does not make is worse than silence, because they attempt it. Recorded here because an
uncorrected verdict in `docs/reviews/` gets cited later.

---

## C1 — High: `ci.yml`'s sweep-skip fails CLOSED when `git diff` fails, and says so falsely

`.github/workflows/ci.yml`, step `mutated_code`. **Disposition: FIXED in this branch.**

**The claim attacked (brief C2).** The block states twice, in capitals, that it *"FAILS TOWARD
RUNNING"*, and `sweep_needed` implements that honestly: `if changed is None: return True`, with a
pinned case behind it.

**What is true.** The guarantee covers exactly one way of being undetermined — `BASE` failing to
resolve, which `git rev-parse --verify` catches. It does not cover the diff failing *after* `BASE`
resolves. `git diff --name-only "$BASE"...HEAD > /tmp/changed.txt || true` swallows the failure, the
redirect has already truncated the file, and Python reads `[]`. **`[]` is not `None`** — the shell
could express "no paths changed" but had no way to express "I could not find out", so the `None`
arm was **unreachable from its only call site**. The callee was correct and the guarantee absent:
*unit coverage does not compose — mutate the CALL SITE.*

**Executed.** A `git` shim that succeeds on `rev-parse --verify` and fails on `diff` (the shape of a
missing merge base), against the real `run:` block extracted through a YAML parser (`node -e` +
`js-yaml`) with the two `${{ }}` expressions substituted:

```
$ GITHUB_OUTPUT=out.txt PATH="$SHIM:$PATH" bash block.run.sh
fatal: no merge base
no scripts/ file changed against origin/master — the sweep would mutate unchanged
code against unchanged suites, which can only reproduce the previous result.
$ cat out.txt
changed=false
```

The gate is skipped, the job stays green, and the log asserts **"no scripts/ file changed"** — a
false statement about the world rather than an error, so the `::warning::` arm built for exactly
this case is never reached and nothing tells a reader the gate was skipped.

**Severity — revised upward from my own initial Medium, and the reason matters.** I first rated this
Medium because `mutation-sweep`'s checkout is `fetch-depth: 0`, making the precondition non-live.
Then I read that setting's own comment: *"fetch-depth: 0 for parity with `verify`, not because the
sweep reads history — it copies the tree into a temp dir with no `.git` at all."* The only thing
protecting the fail-open is a setting documented as incidental, whose comment invites its removal.
A guard whose protection is another step's unrelated choice is not protected.

**Fix applied.** The diff's exit status is checked (`|| true` removed) and a sentinel is passed, so
`changed = None` is produced and the long-written `None` arm is finally reachable. Verified with the
same shim: `changed=true` plus two `::warning::` lines. All four arms re-executed — undetermined →
`changed=true`; staged path changed → `changed=true`; docs-only → `changed=false`; module
unimportable → `changed=true`.

---

## C2 — Medium, FIX-INDUCED BY ME, and caught in the same hour: the honest-log defect, repeated

`.github/workflows/ci.yml`, the `RUN` arm. **Disposition: FIXED.**

My first version of the C1 fix left the `RUN` arm printing *"scripts/ changed, so the sweep runs:"*
unconditionally — so on the undetermined-diff path it asserted a changed-file set it had just
failed to read, then `grep`ped an empty file. That is **the same defect as C1 in miniature**: a log
line claiming to know something the step could not determine. Observed in the verification output
of my own fix, which is the only reason it did not ship.

⚠ **And the first repair of it was also wrong, in a second way.** I replaced the `grep '^scripts/'`
with a `grep -E` alternation listing the staged roots — re-implementing `SWEEP_RELEVANT_ROOTS` in
YAML, which is `a-second-implementation-of-one-rule-drifts` (17 prior instances, and an 18th found
elsewhere in this same round). The module now prints the verdict on line 1 and the matching paths
after it; the shell reports what it is given and decides nothing.

⭐ **Worth recording as a pattern rather than an embarrassment:** both of my own errors here were in
the *reporting* layer of a correctness fix, and both were found by RUNNING the fix rather than by
re-reading it. The round's two shipped defects from the previous day had the same shape.

---

## Verified lead, escalated beyond how the finding was filed: CODEX #2

CODEX filed *"unchanged scripts do not imply unchanged mutation-test inputs"* as High, proved by
staging a tree, showing a green control at `25/25`, replacing only
`.agents/skills/shared/handoff-path.md`, and getting `24/25` with a real `[FAIL]`. Agent output is a
lead, not a finding, so I verified it by hand and it is **worse than filed**:

```
$ python3 -c "... print(mod.HARNESS_TREE)"
('scripts', 'supabase', 'docs', 'node_modules/typescript', '.claude/hooks',
 '.github/workflows', '.agents/skills')
```

`sweep_needed` tested `startswith("scripts/")` — **wrong for six of the seven roots the harness
actually stages.** A dozen-odd guards resolve their subject from the repo root: `check-handoff-path`
reads `.agents/skills/handoff/SKILL.md`, `check-python-pin` reads `.github/workflows/`,
`check-banner-armed` reads `.claude/hooks/`. ⛔ And `CLAUDE.md` already records this exact class from
2026-09-07: *"the harness stages HARNESS_TREE, not scripts/ alone — four guards resolve their
SUBJECT from the repo root, so a scripts-only tree gave each a red control and left them
unmanifested for weeks."* The scripts-only assumption that cost four guards once was reintroduced
with the correct tuple sitting in the same module.

⭐ **The change that introduced it is an instance of it.** This branch touched
`.github/workflows/ci.yml` and `.claude/hooks/block-idle-stop.sh`, both staged, neither matched. A
branch changing only those two would have skipped its own mutation gate.

**And the realistic trigger is not hypothetical:** a vendor update (`npx skills@latest add
mattpocock/skills`) rewrites `.agents/skills/handoff/SKILL.md` and nothing else — the precise event
`check-handoff-path.py` exists to catch, per `docs/plugins.md` layer 2 — and the sweep would have
skipped.

**Fix applied, and the shape of it was constrained by a pinned decision.** The obvious fix — derive
the predicate from the whole of `HARNESS_TREE` — would have reverted backlog #173's decision that a
docs-only branch skips, which is guarded by a starred case AND a mutation entry written to forbid
the opposite, and is the whole measured saving. That is this repo's recorded trap of a guard
mandating what it audits. So: `SWEEP_RELEVANT_ROOTS = HARNESS_TREE − SWEEP_SKIP_ROOTS`, derived
rather than retyped, with `docs` the only exclusion. All 7 pre-existing pinned cases keep their
answers; 9 new cases added; 2 mutation entries added and 1 re-pointed.

⚠ **The `docs` residual, stated at the strength it was measured and no further:** 12+ guards read
`docs/` paths, and `check-anon-exposure` reads two concrete ones whose absence makes its suite exit
2 before case 1. So docs files **are** read. Whether a docs *content* change can flip a mutation
verdict is **NOT MEASURED**, and no claim is made either way. backlog #330 owns that measurement.

---

## C3 — High: an armed ARCHITECTURE_REVIEW is disarmed by the next round, and this half disarmed one

`scripts/check-review-decision.py`, `thrashing_component`. **Disposition: filed — backlog #332.**

⭐ **FOUND BY RECONCILING THE TWO HALVES AGAINST EACH OTHER, not by either of them.** The CLAUDE half
closed with *"on this branch `check-review-decision` returns `ARCHITECTURE_REVIEW`"*. My own run,
minutes later, returned `ROUND_OWED`. Two correct observations of one tool disagreeing is the kind of
split this repo records as the most valuable output of a round, so I chased the difference instead of
preferring my own reading.

**The cause is this document.** `thrashing_component` is positional:

```python
shared = induced(rounds[-2]) & induced(rounds[-1])
```

Filing an r4 half moved r2/r3 out of the window. Measured by moving one file in and out of
`docs/reviews/coordinator/`:

```
r1–r3 : ARCHITECTURE_REVIEW — thrashing: 'corpus-cannot-run' carried fix-induced
        findings in r2 and r3          (rounds=3)
r1–r4 : ROUND_OWED — r3's Blocking is still open ...   (rounds=4)
```

**My r4 found nothing about `corpus-cannot-run` and touched none of it.** It disarmed the escalation
by existing.

**The docstring names the right risk and then assumes its answer:** *"Deliberately the LAST TWO, not
any two. 'Two consecutive rounds' is the arming condition; a component that thrashed early and was
then FIXED must not arm it forever."* The reasoning is sound and the verification is absent — `grep`
confirms the module reads no architecture-review artifact at all, so a round that **ignores** the
component disarms the escalation exactly as a round that **fixes** it does. The signal's lifetime is
an accident of round count rather than of whether anyone replied.

This is `an-escalation-has-no-closer` inverted. There, only a reply closes an escalation and work
that merely moots it leaves it standing; here the next round closes it *without* replying. And the
repo has already had this exact insight about the other half of the same function pair —
`dev-process.md`: *"rank by TOTAL appearances, not consecutive run, because one fixed, gone quiet and
COME BACK beats a longer unbroken run"* — applied to `review_scope`'s RANKING, never to the ARMING
beside it.

⚠ **NO LIVE GATE WAS MISSED HERE, and saying otherwise would be the overstatement this round keeps
catching.** The escalation armed by r2/r3 **was** answered:
`docs/reviews/architecture-review-2026-10-20-decision-route-escalation.md` quotes that exact
`ARCHITECTURE_REVIEW` line at `:6` and analyses `corpus-cannot-run` at `:24` and `:96`. So this is a
defect in the mechanism's memory, not a review that got skipped. It is filed as High rather than
Medium because the realistic bad path requires nothing unusual: thrashing arms at r3, the operator
does what the process tells them to do next — run another round — and the project's only
composition-defect gate disappears with no record that it was ever owed.

---

## Negative results — claims attacked that HELD

**N1. The heredoc indentation is fine.** I expected a defect: `<<'PYEOF'` needs its delimiter at
column 0, and in the file both `PYEOF` and the Python body sit at 10 spaces. Attacked by parsing the
workflow properly instead of reasoning about block scalars — `run: |` is at 8 and content at 10, so
YAML dedents everything to column 0; `grep -n` on the extracted block shows `PYEOF` at column 0.
**Held.**

**N2. `sys.modules["cpc"] = mod` is load-bearing, exactly as its comment claims.** Deleted the line
and ran the import: `AttributeError: 'NoneType' object has no attribute '__dict__'` from
`ns = sys.modules.get(cls.__module__).__dict__`. The documented trap is real. **Held** — the one
claim in this diff about the world that I could confirm by construction.

**N3. Every arm of the sweep-skip block except C1's behaves as documented.** RUN on the real branch
diff, SKIP on a docs-only path list, `changed=true` on an unimportable module. **Held.**

**N4. All nine changed guards' `--self-test` suites were green before this round.** Recorded because
it must NOT be mistaken for a review: both defects that shipped on this branch the previous day
passed their self-tests, one because five fixture-built cases each supplied the constant the case
then asserted. `check-decision-scheme.py`'s entry point is red by design (trigger 1) and is not a
finding.

---

## What this half did NOT cover

`check-transcript-references.py`'s 302 new lines, the 14-surface widening, and the six manifests'
anchor bindings were the other halves' subjects. CODEX closed the last two by measurement — **219
manifest anchors all binding uniquely, and all 20 added/changed entries reddening via exactly their
named case over controls proved green first** — and CLAUDE closed the first with H1. No hole.

---

## ⛔ `fixes_nontrivial: true` — THIS ROUND DOES NOT CLEAR THE BRANCH

Stated plainly because the temptation is to call four fixed Highs a converged round. The fixes
applied here are **not** trivial: a new derived constant and an extracted `round_blocker`, a
restructured `ci.yml` step, a hook rc capture, 9 + 6 new cases, 3 new mutation entries, 5
re-pointed anchors. `converged()` reads `fixes_nontrivial` and makes that a CONTINUE, for the reason
this round demonstrated twice over: **a fix is unreviewed code, and C2 is a defect I introduced
while fixing C1.** Two of the previous day's shipped defects were also fix-induced.

**So r5 is owed, and its subject is the fixes** — `SWEEP_RELEVANT_ROOTS`/`SWEEP_SKIP_ROOTS`, the
rewritten `mutated_code` step, `round_blocker`, the `TRANSCRIPT_RC` capture, and the two re-pointed
case assertions in `check-review-decision.py` whose literal token I changed. ⚠ Point r5 at the
**consumers** of what changed, not only the changed lines: a fix's blast radius reaches every reader
of the state it moved.
