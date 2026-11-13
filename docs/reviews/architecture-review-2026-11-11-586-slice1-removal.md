Reviewed head: ab43cbb1

> **For the route of subject `586-slice1` (backlog #586 slice 1, PR #557, DRAFT).** THRASHING armed this review in
> one component, `removal-detection` in `scripts/strace-measure.py`. Round 2's findings X2-X5 came from the r1 fold,
> and round 3's C2 (its doc claim), C3, C4 and C5 came from the r2 fold
> (`docs/reviews/coordinator/586-slice1-r3-coordinator.md`, *Thrashing: armed*).
>
> **Verdict: REDESIGN, by DELETION. BLOCKERs: none.** The r3 split was the right direction, but it stopped halfway.
> The thing that thrashed is a model of creation provenance, rebuilt from log TEXT. It survives in two places:
> slice 1's reader, where nothing consumes its output, and slice 2's planned refusal rule, which is the one that
> gates. **The recommendation (R1):**
> - Delete the removal model from slice 1. Slice 1 keeps only raw remover facts.
> - In slice 2, replace "a path no earlier call in the log created" with a stateless LOCATION rule: outside the copy,
>   `CHILD_HOME` and a fresh per-run `TMPDIR`, a removal is refused.
> - Backlog #600 gets that rule as its concrete mechanism.
>
> Filed: backlog #601 (slice 1 deletion), #602 (slice 2 rule). #600 amended. `scripts/strace-measure.py` is not
> changed by this review.

# Phase 6 architecture review (narrow, triggered by thrashing): removal detection in the slice-1 strace reader

**Scope.** At `ab43cbb1`:
- `scripts/strace-measure.py`: `resolve` (`:177-184`), `removed_and_created` (`:187-234`), `analyse_log`'s
  `kind_of`/`forget`/`inside` and the removal branch of `call` (`:275-345`), and `merge`'s removal tables.
- `docs/reviews/measurements/2026-11-10-strace-on-runner.md`.
- The plan `docs/superpowers/plans/2026-11-09-observed-reach-selection.md`: the Global Constraints, slices 1-5.
- Spec `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` §2.
- Backlog #600.

Read first: `CONTEXT.md` (the *Structural line* entry, `:140`, is the precedent this review leans on). No ADR in
`docs/adr/` touches the recorder, and none is re-litigated.

**Gates run here:** `python3 scripts/strace-measure.py --self-test` → **68/68 self-test cases passed**, rc 0
(MEASURED, this head). There was no live strace run: the host is macOS.

## Q1 — Is the r3 split sound: does slice 1 still claim what only log analysis could support?

**Mostly yes.** The doc's headline row and its ⚠ paragraph now qualify the 0:
- doc `:95`: "a LOWER BOUND";
- doc `:108-110`: "0 that this reader can see; the guarantee … is NOT made here".

The module docstring's r3 paragraph (`:33-41`) says the same.

**Five survivors make the claim, or lean on it** (each read by hand at this head):

| # | where | text | why it survives the split |
|---|---|---|---|
| S1 | plan `:213-216` (Slice 1 **Decides:**) | slice 1 supplies "which suites trip … an unlink/rename of a pre-existing external path" | slice 1 now says it cannot decide this |
| S2 | plan `:278-280` (Task 1.1 Step 1) | record every removal "outside the copy and was not created earlier in the same log by a creating call" | this is the EXEMPTION that r2 removed (driver `:22-24`). The plan still specifies the reader that r1 and r2 refuted |
| S3 | doc `:11` | "the round-2 fold whose reader LISTS every removal outside the copy" | an unqualified "every". `:95` and `:98` say "by TEXT" |
| S4 | doc `:126-130` | "slice 2's parser must follow each pid's cwd … before 'no external removal' is a whole claim" | this says log analysis CAN make it whole. That contradicts `:109-110` and backlog #600 |
| S5 | driver docstring `:27-30` | "so the annotation is not stale; correctness no longer depends on it. Slice 2 decides its refusal rule from the list." | r3 F2 refutes "not stale", and the same docstring's `:37-38` already says so. On "decides from the list": no slice-2 task reads the list (Q3) |

The JSON's field names (`external_removals`, `not_created_in_log`, `targets_with_not_created`) carry no bound. A
reader of `2026-11-10-strace-on-runner-run3.json` alone sees `not_created_in_log: 0` with no qualification. Nothing
reads those fields (Q3), so this is Low. It disappears under R1.

→ Finding **P2**.

## Q2 — What in the structure made each round's fix produce the next round's finding?

**The composition defect: one rule in two places, with opposite disciplines.** The question is what a removal's
path names, and whether that path was the trace's own. Two modules answer it:

- **The spec's answer is to REFUSE.** Spec §2, `:201`: "`..` is NEVER folded". `:205-207`: "symlinks on a failed or
  path-only call: REFUSED, not resolved … (`through a runtime link`)". An `unlink` is path-only (`:177`). The plan's
  Global Constraint says the same: "**Prefer a refusal to a model**". The project learned this once already, in
  `CONTEXT.md:140`: "The terminating move is therefore not a wider pattern but a **soundness check**: refuse what
  cannot be classified."
- **Slice 1's reader MODELS.** `resolve` folds with `os.path.normpath` (`:182`, `:184`), which is the folding the
  spec forbids. It resolves symlinks by text, and it reconstructs creation provenance in the `created` dict
  (`kind_of` `:275`, `forget` `:282`).
- **Its only refusal outlet is `unresolved`.** That covers arguments it cannot parse, or a relative path with no
  label (`:327-330`, `:332-333`). Every other unknown had to be classified as inside or outside, created or not.

Each round's fix was a new modelling decision, and the next round's finding sat at the seam between two of them:

| round | the fix | what it produced next |
|---|---|---|
| r1 → r2 | added creation-evidence rules: `O_EXCL`, rename-of-created, subtree (Codex X1/X2, Claude F4) | stale evidence still exempted a removal (r2 Codex 1: `mkdir; rmdir; rename pre → d; unlink d/valuable`). The new fields' merge also lost "not measured" (r2 Codex 2-4) |
| r2 → r3 | `forget` (invalidation), plus list-and-annotate with counts, totals and coverage | C3: three new behaviours unpinned. C4: failed calls counted as removals. C5: an unstated aggregation. C2's doc claim "can no longer hide one". Then r3 F1: lexical resolution, which the provenance model sat on top of |

Two features of the structure kept this going:

1. **Every fold restated the claim at the strength of the whole module.** Each fold strengthened one piece:
   evidence, invalidation, listing. Each then restated the universal negative ("every successful … is listed", "can
   no longer hide one"). The next review found the gap between that piece and the piece below it.
2. **The output surface grew every fold, and nothing consumes it (Q3).** The r2 and r3 folds added
   `external_removal_counts`, `_totals`, `_outcomes`, `_outcome_totals`, `_coverage` and `targets_with_not_created`.
   Each new field was a new claim to review. Four of r3's six findings (C3-C6) are about these reporting fields
   (r3 coordinator YAML, `component:` column).
   - The instrument is declared `NO-MUTATIONS` (driver `:13`), so the review rounds became its mutation suite. r2
     Codex and r3 Claude both ran mutations by hand.
   - The self-test grew 37 → 54 → 68 cases (r2 Codex validation line; r3 Claude gate table; this head).

**Apply the method's test** (`docs/review-method.md` → *Can a redesign remove it?*). A different shape dissolves
r1-r3's removal findings outright: if no module reconstructs provenance, there is no stale evidence, no lexical
symlink hole in a model, and no annotation to aggregate. These are **mechanism** defects, not branch coverage.

→ Findings **P1** and **P3**.

## Q3 — Can a redesign REMOVE the class? ONE recommendation

**Who consumes slice 1's removal output?** Grep over the worktree, every `.md`, `.py`, `.yml` and `.json` except the
script itself and the round docs, for these names: `external_removal`, `created_in_log`, `not_created`,
`unresolved_removal`, `targets_with_not`. Hits occur only in the measurement doc and its JSONs. **No plan task in
slices 2-5 reads a removal field:**

| slice | what it takes from slice 1 |
|---|---|
| 3 | `STRACE_VERSION` and the syscall and ioctl unions (plan Task 3.1 `:426-428`); `TRACE_FACTOR` (`:538`) |
| 2 | `cwd model disagrees` only "if slice 1 measured decoration" (`:390`) |
| 2 | the raw lines in `scripts/fixtures/strace-lines/` (Task 1.2) |
| 2 (Task 2.2's removal rule, `:391-394`) | nothing: a fixed rule, not data |

The one conceivable use of the counts is an estimate of the refusal's cost. Task 4.3 (`:618-621`) measures the
real refusal tally on master anyway.

**The two candidates in the brief:**

- **(A) The reader emits RAW per-syscall facts, and a small total function classifies them.** This is the right
  shape, and it is exactly slice 2: `resolve_calls`, then `classify`, then a refusal (plan Task 2.2 `:378-381`,
  Task 3.1). Building it in slice 1 would be a THIRD copy of the path rule. Rejected.
- **(B) Removal safety moves out of the reader, so the reader needs no removal logic.** This is adopted, with one
  correction: what replaces the model is a **stateless location rule**, not a uid or namespace sandbox. Two reasons:
  - A namespace sandbox traced from outside trips the plan's own `DENIED_SYSCALLS` (`unshare`, `mount`,
    `pivot_root`; plan `:430-432`).
  - A different uid changes the recording environment away from the sweep's. Spec §2 `:68` requires that the
    recording build "its tree as `mutate_delivered` does".

**R1 — the recommendation:**

1. **Slice 1 deletes its removal model.** The deletion list:
   - `removed_and_created`'s creation half (`:207-234`), together with the `created` dict, `kind_of`, `forget` and
     the `created_in_log` annotation;
   - `by_note`/`by_ok`, `KEEP_REMOVALS` and `external_removals`;
   - in `merge`: `external_removal_counts`/`_totals`/`_outcomes`/`_outcome_totals`/`_coverage` and
     `targets_with_not_created`;
   - the self-test cases that pin them. By their labels that is about 30 of the 57 `check(` labels: X1 1-11, X4 17,
     r2 X1 ×9, r3 F3, r3 F4 (counted by hand from the labels at this head; INFERRED, not a mutation count).

   It KEEPS:
   - per-target counts of remover calls, and the `unresolved` count with its samples (the doc's "28 targets" is
     slice 2's cwd-model input);
   - the raw-line samples, which already hold a line per (remover, return shape).

   The doc's removal row becomes those raw counts plus one pointer to backlog #600. The run-42915171820 figures
   come from a reader that r3 refuted, and they leave the doc. S1-S5 are rewritten. → **backlog #601.**
2. **Slice 2's rule `external path removed` loses its provenance clause.**
   - Today the rule is: "a path outside the copy that no earlier call in the log created" (plan `:391-394`).
   - It becomes: a SUCCESSFUL `unlink*`/`rmdir`/`rename*` (either side) whose path is outside the copy,
     `CHILD_HOME` and the run's own fresh `TMPDIR` is refused (`external path removed`). The path is resolved by
     slice 2's existing rules, which already refuse `..`, runtime links and pre-existing links into the copy.
   - That is a set-membership test on a path that is already resolved: no state, total.
   - It holds because the run's `TMPDIR` is empty when the run starts. Anything under it, or under the copy, or
     under `CHILD_HOME`, is either a staged file or something the run made.
   - What it costs is MEASURABLE before slice 2 builds it. Run 42915171820's 1,482 sampled listed paths (capped at
     20 per target and annotation, so a SAMPLE of the 63,720) are **all under `/tmp/`** (MEASURED from
     `2026-11-10-strace-on-runner-run3.json`, this review).
   - What is NOT measured: whether any suite hard-codes `/tmp` rather than honouring `TMPDIR`. A run that sets
     `TMPDIR` is the measurement. → **backlog #602.**
3. **Backlog #600 names R1.2 as its concrete mechanism** (Q4). The setting it needs is `TMPDIR` in the recording
   environment, in one place. `mutation_env` and `child_env` set no `TMPDIR` today (`scripts/check-plan-code.py:256-268`
   and `child_env`).

**What R1 deletes, in one line:** every reconstruction of creation provenance in the recorder, in both slices.

⚠ **Spec contact.** R1.2 adds one variable to spec §2's recording environment ("`env=mutation_env(copy, seed)`
plus the shard environment", `:75`). It replaces a rule that lives in the plan and in backlog #590 R4-F1, not in the
spec's text. In my reading this is a mechanism change inside the Global Constraint "prefer a refusal to a model", and
not a goal change. The spec is the human gate, so whether it needs the owner's sign-off is the coordinator's call. It
is not decided here.

## Q4 — Is backlog #600's trigger right, and is its mechanism buildable?

**The timing is right, but the observable is wrong.**
- "Before slice 4's `record-reads` job runs on master" puts the gate before the first job that accumulates read
  sets.
- But that run starts automatically on the merge push (spec §2 `:64-65`). So the FAILS IF ("runs on master
  while …") can only be observed after it is too late.
- It should be a merge-time observation: slice 4's PR merges only with a Task 4.2 live case in which a traced suite
  removes a pre-existing path outside {copy, `CHILD_HOME`, `TMPDIR`}, and the record refuses it with
  `external path removed`.

**The mechanism is not concrete enough to build.** The row offers three alternatives and a fourth disjunct: "fake
HOME, read-only or absent paths outside the copy, or a refusal rule".
- **"Fake HOME" is already in place.** Every traced run has a fresh `CHILD_HOME` (spec §2 `:74`; driver `:16-17`).
  It cannot be the fix: r3 F1's example deletes the ABSOLUTE `/home/runner/.gitconfig`.
- **"Read-only or absent" names an outcome, not a mechanism.** The two mechanisms that deliver it on a hosted
  runner each collide with the plan (Q3 (B)).
- **"A refusal rule a symlinked removal cannot evade" does exist in the spec.** Rule (i), `through a runtime link`,
  covers an `unlink` through `/t/ln` (spec `:205-207`). But plan Task 2.2's cases test it only on a PROBE ("a
  failed probe through a runtime link → INCOMPLETE", `:404`), never on a remover.

→ Finding **P4**. #600 is amended with R1.2, the merge-time FAILS IF, and the missing remover case.

## Q5 — What did we decide this slice that isn't written down?

1. **The removal list has no consumer.** No document says so. The driver says the opposite ("Slice 2 decides its
   refusal rule from the list", `:29-30`). Three review rounds were spent on an output whose only reader was the
   review. → recorded here, and removed by #601.
2. **A `NO-MUTATIONS` one-shot instrument received three full dual-review rounds.**
   - The `NO-MUTATIONS:` reason (driver `:13`) says slice 2 "re-implements the reader with its own mutated suite".
     That is the argument for NOT hardening slice 1's reader, and the folds hardened it anyway.
   - No one recorded whether a measurement instrument earns full review rounds on every output field, or only on
     the constants later slices pin (`STRACE_VERSION`, the unions, `TRACE_FACTOR`, decoration, refusal triggers).
   - **Proposed answer (stated, not decided):** only the pinned constants. → part of #601's scope note.
3. **Which committed JSON slice 3 loads is unbound.**
   - Plan Task 3.1 (`:445-446`) names `2026-11-NN-strace-on-runner.json`, and three JSONs exist (run 42893595762's,
     `-run2`, `-run3`).
   - Their unions are identical (doc `:7-8`, `:12-13`, MEASURED by the doc), so nothing is wrong today.
   - But the binding to run 42893595762's file is implicit. Low; not filed. The slice-3 author should write the file
     name in when the `NN` is filled.
4. **The split's decision-log row has `observed: null`.** That row is
   `docs/reviews/decision-scheme/decision-log.jsonl:238`, route `split`. This review is an observation on it: the
   split was right, but incomplete. The coordinator records it.

## Findings

| id | severity | finding | evidence | action |
|---|---|---|---|---|
| P1 | **High** | Slice 2's plan re-specifies the creation-provenance model that thrashed in slice 1, in the module that GATES | Plan Task 2.2 `:391-394` ("that no earlier call in the log created"); Global Constraint `:52-53` ("PRE-EXISTING path"). Task 2.2's cases (`:408-411`) carry ONE created negative and none of the inputs r1/r2 used to break the model (`O_CREAT` without `O_EXCL`; `mkdir; rmdir; rename pre → d`) | **#602**: replace with R1.2's location rule, and case the inputs |
| P2 | Medium | Five places still make, or lean on, the claim the split withdrew | S1-S5 (Q1) | **#601** (doc and docstring); plan S1/S2 edits ride the slice-1 r4 fold |
| P3 | Medium | Slice 1's removal output has no consumer. Its folds grew that surface, and four of r3's six findings came from it | Q3 grep; r3 coordinator YAML; 37 → 54 → 68 cases | **#601**: delete (R1.1) |
| P4 | Medium | #600's mechanism is not buildable as written, and its FAILS IF is observable only after the fact | Q4 | **#600 amended** |
| P5 | Low | `resolve` folds `..` (`normpath`, `:182`, `:184`) against spec §2 `:201`. This is the second copy of the path rule, with the opposite policy | Q2 | subsumed by #601: after R1.1 only `unresolved` and samples remain, and they need no folding |
| P6 | Low | Unwritten decisions | Q5 items 2-4 | item 2 → #601's scope note; items 3-4 → recorded here |

**⚠ A HOLD to expect.** R1.1 lowers the self-test's case count. `check-merge-ready.py` HOLDs on falling case
counts. Under the house rule (verify the HOLD line by line), that HOLD is explained by this review. Its falsifier:
a deleted case that pins a field some slice 2-5 task reads. Q3's grep found none.

## What this review did NOT do

- It did not change `scripts/strace-measure.py`, as briefed.
- It ran no live strace and no `TMPDIR` measurement run.
- It did not edit the plan or the spec. S1, S2 and R1.2's plan text are for the coordinator's fold.
- It did not touch GitHub.
- Every figure above is marked MEASURED (re-read at `ab43cbb1`) or INFERRED.
