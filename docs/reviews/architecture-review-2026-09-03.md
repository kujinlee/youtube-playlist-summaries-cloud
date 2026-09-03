# Architecture Review #5 — 2026-09-03

> **Anchor:** `status-visibility` — **ADRs consulted:** 0010 (documents declare their anchor). None
> re-litigated.
> **Trigger:** `docs/dev-process.md` Phase 6, second arming condition — four adversarial rounds
> without convergence on the backlog #72/#73 plan. The user chose Phase 6 over a fifth round, on the
> ground that **seven consecutive rounds whose new defects were inside the previous round's fixes**
> is a fact about the editing loop, not about prose being inexhaustible.
> **Subject:** the four hand-maintained inventories that each answer *"what does this repo check?"* —
> `scripts/check-ratchet-contract.py`, `scripts/check-selftest-counts.py`'s `POPULATION`,
> `scripts/mutations/` + `EXPECTED_MUTATIONS`, and `.github/workflows/ci.yml`.

**Method.** Coordinator-written, no subagents. Every number below was produced in this session by
**importing the module that owns the inventory** and reading the object — never by string-splitting
source. That choice is itself a finding: an earlier attempt at this measurement string-split on
`POPULATION` and `EXPECTED_MUTATIONS` and returned **`0` for two of the four**, which is the
dangerous shape — a zero is indistinguishable from "my reader could not see it". The measuring
script fails loudly (`raise`) rather than reporting an empty inventory.

---

## The one-paragraph answer

**The repo has four inventories of its own guards, they are nearly disjoint, and no code reconciles
them.** 26 guards exist on disk; 9 are pinned for self-test counts (only **6** of those are guards);
7 have mutation manifests (only **4** are guards); 17 are named in CI. **Eighteen of the twenty-six
have neither a self-test-count pin nor a mutation manifest.** Every reconciliation between these
lists is performed by a human editing two files in the same commit and hoping — and *that is what
the four plan rounds have been finding.* Round 4's Blocking is exactly this shape: the plan's T4 adds
a sixth mutation entry, T7 doesn't move `EXPECTED_MUTATIONS`, and the harness **aborts before running
anything** while printing a coverage summary. The plan under review is not failing because it is
badly written. It is failing because **it is the only place where the four inventories are
reconciled, and a document cannot enforce a reconciliation.**

---

## 1. The four inventories, measured

Read by importing each owning module. Reproducible.

| Inventory | Owner | Size | …of which are guards |
|---|---|---|---|
| the guard population | `check-ratchet-contract.py` filesystem glob + `GUARD_PATH_RE` | **26** | 26 — this is the definition |
| self-test count pins | `check-selftest-counts.POPULATION` | **9** | **6** |
| mutation manifests | `scripts/mutations/*.json` + `EXPECTED_MUTATIONS` | **7** (sum 162) | **4** |
| CI invocation | distinct `scripts/*.py` named in `ci.yml` | **20** | **17** |

Non-guards inside guard inventories: `explainer-serve`, `gen-goals-page`, `page_chrome` (in
`POPULATION`); `gen-dashboard`, `page_chrome`, `page_markup` (in the manifests). Those are not
mistakes — they are subjects worth covering. But nothing states that the populations *differ on
purpose*, so every future edit has to re-derive it.

**Reachability is fine, and that is worth saying.** Every one of the 26 guards is named by at least
one runner: 17 by `ci.yml`, 8 by `check-schema-gates.sh`, 3 by a `.claude` hook, **0 by none**. The
defect is coverage *depth*, not dead guards.

### Guards with neither a self-test pin nor a mutation manifest — 18 of 26

```
check-anon-exposure       check-arch-findings        check-catalog-coverage
check-docs                check-explainer-delivery   check-function-revokes
check-gate-falsifiability check-guard-coverage       check-handoff-path
check-live-schema         check-paid-caller-arrival  check-plan-progress
check-producer-enumeration check-ratchet-contract    check-roadmap-consistency
check-sentinel-meanings   check-storage-grant-pin    check-vocabulary-collisions
```

## 2. Closed since Architecture Review #4 — the ratchet worked

Recorded because a review that only ever adds findings cannot show whether the last one paid.

| #4 finding | Status 2026-09-03 | Evidence |
|---|---|---|
| A — inventory cannot see a guard nothing calls | ✅ **CLOSED** | both named scripts now wired: `check-plan-task-order` ×1, `check-producer-enumeration` ×2 in `ci.yml`; 0 of 26 guards unreachable |
| B — `dev-process.md` listed an unexecuted script as enforced | ✅ **CLOSED** | the row now names it as gate 15 of `check-schema-gates.sh` |
| C — docstring case-count drift on an unrun guard | ✅ **CLOSED** | `check-plan-task-order.py:26` says `# 16 cases`; suite reports 16/16 |
| D — inline renderer had no seam | ✅ **CLOSED** | `scripts/page_markup.py` shipped (PR #180); `CONTEXT.md` §Page Generation documents it |

Population also grew 24 → 26 without a new orphan appearing. The contract is holding.

---

# Findings

## A — 🟠 Four inventories answer one question, and nothing reconciles them

**MEASURED**, §1 above. The four lists are maintained by hand, in four files, with no script
asserting any relationship between them.

Consequence, and it is not hypothetical: **this is what four plan rounds have been finding.** The
plan document is currently the only artifact that reconciles them — §T4 against §T7 against
`EXPECTED_MUTATIONS` against the manifest directory — and a document has nothing to execute. Every
round therefore finds a reconciliation error, the fix introduces the next one, and the round count
grows without the *class* of defect changing. That is precisely the signal `review-method.md`
describes for reading a trigger off the cause rather than the count.

**Falsifier for the fix:** a script that, given the guard population, reports which guards are absent
from each derived inventory and refuses when an inventory names a file that is not a guard *and* is
not declared as a deliberate subject.

## B — 🟠 The mutation harness aborts before measuring, and prints a coverage summary on that path

**REPRODUCED by reading.** `scripts/check-plan-code.py`:

- `:591-597` — for each `EXPECTED_MUTATIONS` target, a count mismatch appends to `drift`.
- `:598-600` — a manifest file with no declared count also appends to `drift`.
- `:625-626` — `if drift: return False, drift, ev`.
- `:630` — `shutil.copytree(...)`, i.e. **the mutation run starts five lines after the return.**

`ev` at that point is still its initializer (`:584`), so the report is rendered from
`{"mutations": [], "survivors": [], …}` and the run emits **`0 mutation(s), 0 survivor(s)`** beside
the drift message.

**It is not fail-open** — the function returns `False` and the gate exits non-zero. The defect is
narrower and still real: the output contains a *true-looking coverage claim* on a path where nothing
was measured. Your own memory names this class — *"'Guard didn't fire' and 'nothing could see it
fire' look identical"* — and it has already cost this project once, over 12 mutations reported as
"0 red cases".

**This is round 4's Blocking, generalized.** The plan's T4 adds a sixth `read_population` mutation;
T7 leaves `EXPECTED_MUTATIONS` at 5; the harness aborts at `:626` and reports zero. Following T4
gives a red harness that measured nothing; following T7 leaves the CANNOT-RUN branch with no
falsifier. **The count must be decided in one place** — six entries, `EXPECTED_MUTATIONS` 6, sum 168.

**Falsifier:** run the gate with a manifest entry added and `EXPECTED_MUTATIONS` untouched; the
output must not contain a mutation/survivor tally at all.

## C — 🟡 `EXPECTED_MUTATIONS`' key set is a verified duplicate of `scripts/mutations/`

**MEASURED.** The two stem sets are **identical**:

```
EXPECTED_MUTATIONS stems == mutations/*.json stems  ->  True
{check-dashboard-entry, check-plan-code, check-selftest-counts,
 check-theme-token-coverage, gen-dashboard, page_chrome, page_markup}
```

⚠ **Two things here are deliberate and must not be swept up in a fix.**

1. The per-file **counts** live in the runner on purpose — `:426-431`: *"A count stored beside the
   entries it counts gets edited in the same breath as deleting one, which is no guard at all."*
   That reasoning is sound and survives.
2. The **sum literal** `162` is deliberate — `:1956`: *"A literal on purpose: its whole job is that
   the total cannot move without someone deciding it should."* Also survives.

Only the **key set** is redundant, and `:598-600` proves it: the code already errors when the two
lists disagree, so the second list carries no information the directory doesn't. Deriving the keys
from the directory while keeping the counts and the sum in the runner removes finding B's abort
without weakening either guard.

## D — 🟡 `docs/backlog.md` #48 records a verdict that events superseded

**MEASURED.** Row #48, closed 2026-08-21, states: **"STOP-HOOK VERDICT: NOT BUILT, deliberately."**

It was built on **2026-08-24** (`8b9643d9`) — `.claude/hooks/block-idle-stop.sh`, registered as the
`Stop` hook in `.claude/settings.json`, driven by `scripts/check-plan-progress.py` (17/17 cases).

And it is the *good* version: it does not inspect the assistant's sentences, which is the exact
ground on which #48 rejected Option B. It reads `.claude/executing-plan` and refuses the stop while a
named plan has unticked steps — a state predicate with a real falsifier. The row's reasoning was
correct for the design it rejected and was answered by a different design three days later; nobody
went back.

## E — 🟢 A hook comment states a case count nothing checks, and it has drifted

**MEASURED.** `.claude/hooks/block-idle-stop.sh:5` says *"(18 self-test cases)"*;
`python3 scripts/check-plan-progress.py --self-test` reports **17/17**.

Nothing catches it, because `check-plan-progress` is not in `check-selftest-counts.POPULATION`. This
is **finding A in miniature** — and note it is the same shape as review #4's finding C, which was
closed for one script rather than for the class. Filed at 🟢 because the guard runs and works; its
value is as evidence, not as a defect worth a slice.

---

# Refuted — recorded because it was nearly filed

**"A monitor agent should watch for stalled execution."** Raised by the user this session after an
API stream stalled mid-turn. Investigated and **not filed**, for reasons that are measurable:

- A `Stop` hook fires when a turn *ends*; a stall is a turn *dying*, so no `Stop` event exists to
  catch. `.claude/executing-plan` is absent this session, so the hook is inert regardless (`rc=0`).
- A polling monitor can only observe elapsed time, which cannot distinguish *stalled* from
  *thinking* from **stopped at a human gate** — and this repo is built out of deliberate stops.
  `docs/backlog.md` #48 already rejected a stop-guard on a near-identical discriminator argument.
- The `Monitor` tool's own documentation states the same limit: *"silence looks identical to still
  running."*
- The recovery primitive already exists and is human-triggered: `claude --continue` / `--resume`,
  restoring from the append-only session transcript.

**Recorded rather than dropped** because the underlying instinct — supervision belongs at the OS
layer — is right, and the answer is that the supervision exists at the CLI layer and deliberately
does not auto-replay a turn that may already have spent money or written to the repo.

---

# What we decided this milestone that isn't written down

The one failure no tool can see. Four items, all currently living only in a spec, a plan, or a
transcript:

1. **The guard count is 28, not 29** — `build-m4-schema.py` is OUT because its flag set has no
   `--check` mode and `assert_end_state(sql)` takes its own output. The *criterion* — "a guard has a
   mode whose only product is a verdict about a subject other than itself" — exists only in the spec
   prose. No code applies it, so the next borderline file will be argued from scratch.
2. **The population declaration is an AST node, not text** — `NOT_A_GUARD = "<reason>"` at module
   level, placed **after** the `from __future__` import (before it, the file parses but does not
   compile). **Two text grammars were tried and both failed**, because after
   `ast.get_docstring(clean=True)` dedents, a declaration and a *demonstration* of one are
   byte-identical. That negative result is worth more than the positive one and is recorded nowhere
   a future reader will look.
3. **Phase 6 was convened instead of round 5**, on the cause rather than the count. `dev-process.md`
   describes the trigger but not this precedent: *seven rounds whose defects were inside the previous
   round's fixes* is the arming signal, and the round tally is the lagging indicator.
4. **`REVIEW GAP: claude` is the correct response to an API failure** — round 2's Claude half never
   ran (529 ×2) and was recorded, not skipped. `check-review-rounds.py` reports 140 rounds, 0 silent
   gaps. The behaviour is enforced; the *reason it matters* is not written down.

---

# Candidates

Not filed — filing to `docs/backlog.md` is the user's step, per the precedent set by review #4.

## Candidate 1 — a seam that answers "what does this repo check?"

One module owning the guard population and the derived inventories; the four current lists become
views of it. **Recommended as the frame**, not as a single slice — it is too large to land at once,
and this review's own subject is what happens when a large reconciliation is attempted in a
document.

## Candidate 2 — derive `EXPECTED_MUTATIONS`' key set from `scripts/mutations/` — ⭐ RECOMMENDED FIRST

Narrow, measured, and it **dissolves finding B rather than patching it**. Keeps the per-file counts
and the sum literal, both of which are deliberate (finding C). Its own falsifier is cheap.

**Why first, specifically:** round 4's Blocking is caused by this duplication. Fixing it removes the
defect *class* that the last four rounds kept producing, which is the only intervention that can be
expected to change the round-on-round pattern rather than add to it.

## Candidate 3 — the plan document holds reconciliation no code holds

The answer to "why seven rounds". Not separately actionable: it is finding A stated from the
document's side, and candidates 1 and 2 are what acting on it looks like.

---

# Dispositions

| Finding | Disposition |
|---|---|
| A 🟠 | frame for candidate 1; **not** a slice on its own |
| B 🟠 | fixed by candidate 2; also needs the plan's count decided in one place (six / 6 / 168) |
| C 🟡 | candidate 2 |
| D 🟡 | doc correction — one row edit, no code |
| E 🟢 | one-line comment fix; the *class* is finding A |

**Recommendation: candidate 2 as the next slice, inside candidate 1's frame.** Then re-run the plan
gate — with the duplication gone, round 5 is measuring a different artifact rather than repeating
round 4.
