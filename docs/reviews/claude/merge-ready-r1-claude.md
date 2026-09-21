<!-- Claude half of code round 1. Filed 2026-09-20. -->

# Claude adversarial review — budget-slack-warning (`check-docs.py` budget WARN + `check-merge-ready.py`) — round 1

Subject: `git diff origin/master..HEAD`, HEAD `2e27bb09`, 3 commits / 12 files.
The Codex half (`docs/reviews/coordinator/merge-ready-r1-codex.md`) filed a High, a Medium and a Low,
all fixed in `2e27bb09`. This half deliberately does not re-verify those; it takes the angles that
half did not. Every finding below was **measured**, not reasoned about.

**Gates run, rc captured before any pipe:** `check-docs.py` **0**, `check-docs.py --self-test`
**0** (19/19), `check-merge-ready.py --self-test` **0** (33/33), `check-plan-code.py --self-test`
**0** (128/128), `check-ratchet-contract.py` **0** (38 guards, `check-merge-ready.py` discovered),
`check-selftest-counts.py` **0** (43 scripts), `check-fixture-variation.py` **0** (572 params / 55
files). NOT RUN: `check-plan-code.py --mutate .` (778 mutations; excluded by the dispatch).

---

## High — `mergeStateStatus: UNKNOWN` is reported as a definite NOT READY, and it is the value GitHub actually returns first

`mergeability()` (`scripts/check-merge-ready.py:138`) refuses anything outside `CLEAN`/`UNSTABLE`
with **rc=1**. `UNKNOWN` is not a state of the pull request — it is GitHub saying *"I have not
computed this yet."* Mergeability is calculated lazily by a background job; the first GraphQL read
kicks it off and returns `UNKNOWN`, and a later read returns the answer.

Measured today, in this repo, on the two open pull requests:

```
$ gh pr view 317 --json mergeStateStatus,mergeable
{"mergeStateStatus":"UNKNOWN","mergeable":"UNKNOWN"}     # first query
$ gh pr view 317 --json mergeStateStatus,mergeable
{"mergeStateStatus":"DIRTY","mergeable":"CONFLICTING"}   # second query, same second
```

PR #295 returned `UNKNOWN` on its first query too. So the ordinary invocation — a human runs this
right after pushing, which is the moment the script is for — currently prints:

```
  NO  mergeability       rc=1  mergeStateStatus is UNKNOWN
```

Two things are wrong, and the second is the one this repo files findings about:

1. **It is a false NOT READY for a clean PR.** A `CLEAN` pull request returns `UNKNOWN` on the
   first read exactly as a `DIRTY` one does — the value carries no information about the branch.
   This is the direction the brief flagged as untested: a merge-readiness checker refusing a
   mergeable PR.
2. **It is a CANNOT RUN reported as a failure.** The script's own docstring says *"every one of
   those returns 2 and says to treat the answer as NOT RUN"*, and `verdict()` carries a comment
   explaining that rc=1 for an absent check *"would send the reader to fix the wrong thing"*. An
   undetermined `mergeStateStatus` is precisely an absent measurement. It gets rc=1.

Remedy shape (not prescribing): treat `UNKNOWN` as rc=2, or re-query once before deciding, the way
`gh` itself does. `mergeable == "UNKNOWN"` is the same signal in the REST spelling.

Verified there is **no** confounder from branch protection: `master` requires `verify` and
`schema-gates` with `strict: false` and **no** required reviews, so `CLEAN` is reachable and
`BEHIND` is not — the refusal set is otherwise right. `BLOCKED` on PR #324 right now is correct
(required checks unfinished).

---

## Medium — the "derived from the workflow, never hand-written" claim is scoped to one file and one gating level, and this repo already uses the other one

The ⭐ paragraph at `scripts/check-merge-ready.py:23` says a second copy of "which steps are
PR-only" *"would drift the first time someone adds one, and it would drift SILENTLY"*, and that
`pr_only_steps()` prevents this because it parses the workflow. Two limits make that a narrower
guarantee than the sentence:

**(a) It parses `ci.yml` only.** `WORKFLOW = ROOT/".github"/"workflows"/"ci.yml"`. There are two
workflows, and `schema-gates.yml` is the *other required context* on every PR (`contexts:
['verify', 'schema-gates']`, read from branch protection). A PR-only gate added there is invisible
to the derivation — the exact silent drift the paragraph claims to have closed. The file scope is
itself the hand-written part.

**(b) It cannot see job-level `if:`, and mis-attributes it.** The parser binds an `if:` to the most
recent `- name:`. A job-level condition has no preceding step name *in its own job*, so it binds to
the **last step of the previous job**. Measured:

```python
>>> pr_only_steps("jobs:\n  a:\n    steps:\n      - name: last step of job a\n        run: x\n"
...               "  b:\n    if: github.event_name == 'pull_request'\n"
...               "    steps:\n      - name: real pr-only step\n        run: y\n")
['last step of job a']
```

Wrong in both directions at once: it names a step that is not PR-only and misses the one that is.
This is not hypothetical shaping — `schema-gates.yml:183` and `:229` gate **at job level** on
`github.event_name`, so job-level event gating is the form this repo writes in practice. Today
`ci.yml` has no job-level `if:` at all (verified: zero matches), so nothing is live.

A third spelling also escapes: `- if: …` as a step's first key, before `name:`, is valid YAML and
the `IF_FIELD` regex (`^\s*if:`) does not match the `- ` prefix. Same silent-miss direction as the
double-quote case the Codex Medium fixed.

---

## Medium — the WARN message the whole feature exists to print names a section this branch deleted

`scripts/check-docs.py:265`, in the remedy text:

```
      (b) PRIORITISE and RETIRE — evict what no longer earns its line.
          dev-process.md keeps its own eviction queue under
          'Rules flagged for review, not retired'.
```

The same branch removes that section from `docs/dev-process.md` (commit `4270e576`, the
eviction-queue drain). `grep -n "Rules flagged for review" docs/dev-process.md` → **no match**;
the only hit in the repo is the string inside `check-docs.py` itself.

This is live output, not latent: both budgeted files are inside the warn band right now, so the
warning prints twice on every `check-docs.py` run and sends the reader to a heading that does not
exist. The remedy that was the *point* of the feature — "prioritise and retire" — now has no
destination, and `process-rationale.md` records the queue as *drained*, which is the opposite of a
place to add to.

```
budget docs/dev-process.md         :  212 / 220  TIGHT  (8 line(s) of runway)
budget docs/plugins.md             :  260 / 260  TIGHT  (0 line(s) of runway)
```

(Both verdicts are correct and the feature works — `docs/plugins.md` at 0 runway is exactly the
100%-utilisation case that used to print `ok`. The defect is the text of the remedy, which is where
this feature's entire value lands.)

---

## Medium — the comment above `EXPECTED_MUTATIONS`' declared sum states a transition that is two commits stale

`scripts/check-plan-code.py:3306`:

```python
# ⟳ 2026-09-20: 769 -> 770, the line-budget slack warning. ONE entry on `check-docs.py`, for
# the band's UPPER EDGE (`<=` -> `<`). …
case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 778)
```

Traced with `git log -L 3300,3315:scripts/check-plan-code.py`: the value went **769 → 770**
(`4270e576`), **770 → 775** (`b6d434ca`), **775 → 778** (`2e27bb09`). The comment was written at the
first step and never touched again. It now claims the total is 770, says the rise is "ONE entry on
`check-docs.py`", and is silent about the 8 entries on `check-merge-ready.py` that make up the rest
of the +9.

A reader sizing the number against the round's findings is nine short — which is the failure mode
the comment four lines above it explicitly warns about (*"a reader sizing this number against the
round's findings would otherwise be one short and look for the entry that was never written"*).
This repo's standing rule is that a comment asserting something false is a defect in its own right,
and the subject here is a **count**, the class this file has drifted on three times before.

---

## Low — the `UNSTABLE` allowance is unreachable at the verdict level, so the case pinning it describes a behaviour the tool does not have

`mergeability()` allows `UNSTABLE` with the comment *"a non-required check is failing — GitHub
permits the merge, so this must not refuse it"*, and a self-test case pins it. But `UNSTABLE` is
by definition "some check is failing", and `ci_conclusion()` refuses any check whose bucket is not
`pass`/`skipping` — required or not. So every PR for which `CLEAN` and `UNSTABLE` differ is refused
one line later by `CI`, and `verdict()` returns 1 regardless. The allowance never changes an answer.

Being stricter than GitHub is a defensible choice; the comment asserting the opposite intent
("this must not refuse it") and the case pinning it as reachable are what is wrong. Either the
overall verdict should honour it or the comment should say the tool is deliberately stricter.

---

## Low — `HAS_HOOKS` is a mergeable state and is refused

GitHub's `MergeStateStatus` enum is `BEHIND, BLOCKED, CLEAN, DIRTY, DRAFT, HAS_HOOKS, UNKNOWN,
UNSTABLE`. `HAS_HOOKS` means *mergeable, with passing status and pre-receive hooks* — GitHub will
merge it. `mergeability({**OK, "mergeStateStatus": "HAS_HOOKS"}, "abc")` → `(1, 'mergeStateStatus is
HAS_HOOKS')`. Not reachable on github.com (pre-receive hooks are a GHE feature), so this is latent,
but the comment enumerating the refusal set — "BLOCKED/DIRTY/BEHIND/UNKNOWN are not" — omits
`HAS_HOOKS` and `DRAFT`, i.e. it is an enumeration that does not enumerate.

---

## Low — `budget_warn_slack`'s floor makes every budget of 10 or fewer lines permanently "tight"

Measured:

```
budget   slack   verdict at n = 0, budget/2, budget
     0      10   tight, tight, tight
     5      10   tight, tight, tight
    10      10   tight, tight, tight
    20      10   ok,    tight, tight
```

For any budget ≤ `BUDGET_WARN_FLOOR`, `budget - n <= slack` holds for every `n ≤ budget`, so `"ok"`
is unreachable and the file warns from its first line. At budget 20 the warning starts at 50%
utilisation. The docstring's justification — *"the floor stops a small budget warning only after it
is already too late"* — is right about the direction and has no upper stop, so a small budget warns
before there is anything to warn about, which is how a warning gets ignored.

Not live: both budgets are 220/260, where 7% dominates the floor and the behaviour is exactly as
documented (15 and 18). `budget_verdict(0, 0) == "tight"` and a negative budget reads `"over"` for
`n=0`; neither is reachable from `LINE_BUDGETS`.

---

## Verified and found correct (no finding)

- **"52 steps carry a `run:`, and exactly 2 are gated on `pull_request`"** — measured over
  `ci.yml`: 52 `run:` lines, 2 `if:` lines, both `github.event_name == 'pull_request'`, on
  `dashboard entry ratchet` (`:417`) and `check-review-recorded (PR only)` (`:442`). True.
- **The Codex Low fix** — CI at `ci.yml:420-423` passes `--base "origin/$GITHUB_BASE_REF"
  --pr-body-file /tmp/pr-body.md`; the script now passes both. The `ci.yml:422` citation in the
  comment points at the `--base`/`--pr-body-file` continuation line. Accurate.
- **`NO-CALLER:` reasoning** — sound and non-circular: the script reads `gh pr checks`, so a CI job
  running it would wait on a verdict containing itself. `check-ratchet-contract.py` accepts it.
- **The mutation manifest** — 8 entries, and they do cover the r1 fixes: `a draft pull request
  reads as mergeable`, `the PR head stops being compared to the local HEAD`, `the condition is
  matched anywhere on the line again`. The High and Medium fixes each have a falsifier.
- **The "hollowed out its falsifier" story** (`check-merge-ready.py:262`) — checked against the
  fixture: the two-`if:`-lines case does exercise `current = None`, and a `run:` line echoing the
  condition genuinely no longer would under the `IF_FIELD` match. The account is accurate.
- **The `<=` / zero-runway correction** in `budget_verdict`'s docstring and in
  `process-rationale.md` — reproduced: `budget_verdict(260, 260) == "tight"` under both `<=` and
  `<` (because `0 < slack`), and `<` breaks `budget_verdict(220 - slack, 220)`. The corrected
  account is right and the case names the right edge.
- **The eviction-queue drain** — all three flagged rules are accounted for in `process-rationale.md`
  and the diff matches the account. Rule 1's retirement keeps the superseding statement in
  `dev-process.md` rather than deleting into silence; rules 2 and 3 are answered, not removed, and
  rule 3 correctly separates the *rule* (`process-checklists.md:137`, the known-red set must be
  explicitly named) from its current *value*. `dev-process.md` 220 → 212. Nothing still-true was
  lost. The only defect here is the dangling reference in Medium #3 above.
- **`check-fixture-variation.py`** — the three pinned keys for `check-merge-ready.py` are a *ratchet
  floor*, not an enumeration (`pinned - keys` is the only direction checked, `:900-905`), so
  `mergeability`'s two parameters being absent is not a violation; the guard passes and reports no
  unvaried parameter for the file.

---

## Premise check the brief asked for: does the script cover what CI will run?

Yes, but **not by the mechanism its docstring credits**, and that is worth stating because it
changes what the tool is for.

`READY` requires `ci_conclusion() == 0`, which requires **every** check green with none pending.
On a `pull_request` event CI has therefore already run both PR-only steps. So the three gates the
script invokes locally (`dashboard entry`, `review recorded`, `review rounds` — the last of which is
not PR-only at all, `ci.yml:172`) can only ever turn a READY into a NOT READY; they can never be
what makes READY true. Meanwhile the motivating scenario in the docstring — a working copy, gates
swept, no verdict available on the two PR-only ones — is a state the script **refuses to run in**:
`_pr_number()` finds no PR and returns rc=2.

The genuinely new information the script produces over `gh pr checks` is `mergeability()` — which
is the piece the Codex High added, and the piece the UNKNOWN finding above breaks. Not filed as a
separate finding: the coverage claim is true, the local invocations are useful as *diagnosis*
(they say which gate will fail, before CI finishes), and nothing here can produce a false READY.
It is the docstring's account of why the script exists that is off, and the High is what to fix.

---

## Verdict

**NOT CONVERGED.** One High (`UNKNOWN` reported as a definite refusal, live-reproducible on both
open PRs today), three Mediums, three Lows. The High and Medium #3 (the WARN text pointing at a
deleted section) are both *"the feature is wrong at the exact moment someone relies on it"*, which
is this branch's own stated standard for the defects it exists to prevent.
