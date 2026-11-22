# Round 3 — `marketplace-task17` — Claude half (adversarial)

Reviewed: `548bcc39` (the r2 fold, `git diff 8d6f913f..548bcc39`) and the whole change (`git diff origin/master...HEAD`),
plan Task 17 and Task 19's row rules (`docs/superpowers/plans/2026-11-11-marketplace-inventory.md` lines 825-845,
925-945), spec `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md` §2c, §3 Effort (2), §4, §4b, §5.
Read first: the r1 and r2 coordinator docs, `docs/reviews/codex/marketplace-task17-r{1,2}-codex.md`,
`docs/reviews/claude/marketplace-task17-r1-claude.md`.

Summary: one MAJOR, fix-induced, in component `marketplace-inventory-rows`. **That arms THRASHING**: r2's X1 was
caused by the r1 fold, and r3's C1 below is caused by the r2 fold, in the same component, in consecutive rounds.
No BLOCKER.

---

## C1 — MAJOR — `fix_induced: true` — the r2 fold's cite is borrowed, and the inventory's own text says it bears on no verdict

**Where:** `docs/marketplace/inventory.json`, `coverage-verdict` (`"cites": ["check-plan-code:2:1"]`, line 63) and
`mutation-manifests` (line 79). Both lines were `"cites": []` at 8d6f913f. 548bcc39 added them.

**The rule, quoted (spec §5, item 1 of the behavioural rule):** *"⛔ AND "NEVER ALONE DECIDES A VERDICT" IS MADE
ENFORCEABLE, NOT ADVISED (r2 CLAUDE M8). Every non-`SHIP` verdict **cites the dependency-finding ids it rests on**,
and the scan **refuses to emit a dependency-finding id for a mention candidate.** Then the rule has a falsifier: a
non-`SHIP` verdict citing no id, or citing a mention candidate's id, is a defect in the inventory."*

**Letter:** satisfied. `check-plan-code:2:1` is in the scan's `findings` list (detector 2, kind `unread`, line 2494),
not in its mentions.

**Purpose:** the cite field is the inventory's machine-readable claim of *what the verdict rests on*. The test of a
cite is whether refuting it would weaken the verdict. Run that test on `check-plan-code:2:1`:

1. **What 2:1 is.** Line 2494 is `rc, so, se = control_parts(d, name, seeds, trees)`. `control_parts` is defined in
   the same file (`scripts/check-plan-code.py:442`). It is `unread` because `check-shipping-sets.python_loads`
   treats `control_parts` as a wrapper around a process run and could not bind this call's arguments
   (`check-publishability.py:423-437`: *"an unjudged coupling is shown, never counted as none"*). It is an
   unresolved call site, not an evidenced dependency.
2. **What check-plan-code's own row says about it** (unchanged by 548bcc39): *"C3 fail, argued from spec 2c ... and
   from HARNESS_TREE ...; Cited: check-plan-code:2:1 ... an unjudged coupling ... **it is not evidence of a repo
   path**."* The row's DON'T-SHIP is also spec-named outright (§3 Effort (2): *"The mutation engine itself
   (`check-plan-code.py --mutate`, `scripts/mutations/`) is the expected `DON'T-SHIP`: a stranger brings their own
   engine."*).
3. **The flip.** Suppose a later reader resolves the `control_parts` call and 2:1 disappears from the scan. No verdict
   changes. `check-plan-code` is still the engine (§2c, §3). `coverage-verdict` still has only that engine as
   runtime consumer. The manifests still name this repo's guards. **A cite whose removal changes no verdict is not
   what the verdict rests on.**

So the new notes' sentence *"this row's verdict rests on that row's, so it rests on what that row rests on"* fails on
its own terms. What that row rests on is §2c and `HARNESS_TREE`, which the bound sentence in both new notes admits
(*"argued mainly from spec 2c ... neither of which has a scan finding"*). The cite passes through a finding that the
middle link itself disclaims.

**Why this is a defect and not just a judgement call:**

- It is the outcome r2 warned against. Codex r2: *"Borrowing those citations again would not substantiate the
  verdicts."* Backlog #696 (b), from the same branch: *"a borrowed cite need not bear on the citing component."*
  8d6f913f's own note for `coverage-verdict` was *"not papered over with a borrowed cite"*. 548bcc39 reverses that
  with a label added.
- It disables the falsifier for this case. Task 19's guard (*"a non-ship verdict with no `cites`, or citing an id the
  scan did not emit"*) will now pass both rows. "Zero findings, non-SHIP" was the one shape the guard could catch.
  It now reads green, and the only thing marking the difference is prose in `notes`, which no check reads. Once the
  precedent is set, any zero-finding row can cite any emitted id from a neighbouring component.
- The dashboard's tech line says 2:1 is *"the one finding check-plan-code's row cites for its C3 fail"*. That
  overstates the row, which says 2:1 is not evidence for that fail.

**Mitigation, credited:** both notes label the cite *via* another component and state the bound, and the coordinator
doc records the choice openly. Nobody reading the notes is misled. A reader of `cites` or of Task 19's output is.
That is why this is MAJOR and not a BLOCKER.

**Was option (b) wrongly rejected?**

- **`coverage-verdict`: partly.** All five criteria pass, and the scan emitted nothing. The coordinator rejected SHIP
  by calling it *"an orphan library ... a scope question"* under spec §4. That misreads the table. The orphan row
  (§4 table, *"imported by **no** entry-point"*) does not apply, because `check-plan-code` imports it. The applicable
  row is *"imported only by entry-points that are themselves `argued`"*, which sets the grade to `argued` and says
  nothing against SHIP. §4b permits a DON'T-SHIP argued on reasoning, and §5 rule 1 requires a finding-id cite for
  every non-SHIP. A pure-reasoning DON'T-SHIP with zero findings is the one case where those two rules cannot both be
  met honestly. That is a spec gap, not a cite to manufacture. SHIP + `argued` (criteria-consistent, phase `later`,
  the note *"no shipped unit loads it until the engine ships"*) is a defensible reading and needs no cite. Excluding
  it from scope is the other defensible reading. Which one is right is the owner's call.
- **`mutation-manifests`: correctly rejected.** C3 fails and §3 names the DON'T-SHIP. But the true ground is a spec
  sentence, and the schema has no field for a spec cite. Same gap.

**Fix:** do not fold a third cite variant. That would be the third consecutive fold of the same rows on the same
rule, which is what THRASHING describes. Revert the two cites to `[]`, mark the rows as an open #696 (b) case, and
put the decision to the owner, because §5 rule 1 is the approved spec's rule (dev-process: *"a genuine ambiguity or
fork the spec did not settle"*). The options are:
(i) a `no-findings` marker plus a cited spec or code location as the rule for zero-finding non-SHIP rows;
(ii) SHIP + argued for `coverage-verdict`, and a spec-cite field for `mutation-manifests`;
(iii) transitive cites made the stated rule, with the bearing test above written into it.
Under the round cap this files and notifies; it does not block a merge on its own.

## C2 — MINOR — `fix_induced: true` — `mutation-manifests`' second C3 reason misapplies §2c

**Where:** the `mutation-manifests` notes, added by 548bcc39: *"C3 fails a second way, by spec 2c's own rule for a CI
piece (depending on our engine is a C3 failure): the manifest format is the input of exactly one executor ..."*.

§2c's rule reads C2/C3 *"for a CI piece"*, and the CI pieces are §3's (a), (b) and (c). §3 lists `scripts/mutations/`
as part of *"the mutation engine itself"*, not as a piece. Task 17's plan text applies *"a dependency on
`check-plan-code.py` is a C3 finding"* to those three pieces too. There are two problems:

- **Category.** The manifests are a part of the engine. They cannot fail by depending on it.
- **Direction.** Under §5 rule 1, a dependency is *"an import, an invocation, a documented prerequisite, or a runtime
  configuration read"* that the component makes. A JSON file makes none of these. The engine reads the data; the data
  does not depend on the engine.

This second reason exists only to carry C1's cite. Without the cite, the first reason (content anchored to this
repo's guards) and §3's explicit expectation already carry the verdict. **Fix:** drop the second reason together with
C1's cite.

## C3 — MINOR — `fix_induced: false` — check-plan-code's own cites do not bear on its DON'T-SHIP

`check-plan-code` cites `["check-plan-code:2:1", "check-plan-code:6:3"]`. Its notes say 2:1 *"is not evidence of a
repo path"* and cite 6:3 for a C2 **pass**. The r2 coordinator doc now states the second point outright
(*"`check-plan-code:6:3` is not cited, because that row cites it for a C2 **pass**"*), so by the fold's own reasoning
neither cite is what this DON'T-SHIP rests on. That cite list was set by the r1 fold (8d6f913f; the build cited 4:1,
4:2, 6:1, 6:3 and 2:1). 548bcc39 did not change it, so this is not fix-induced. It is the root that C1 propagated, and
it is the same #696 (b) question for a spec-named DON'T-SHIP. **Fix:** decide it together with C1.

## C4 — MINOR — `fix_induced: true` — the r2 coordinator doc misquotes spec §4's orphan row

`docs/reviews/coordinator/marketplace-task17-r2-coordinator.md` justifies rejecting SHIP for `coverage-verdict` by
saying *"spec §4 calls such an orphan library a scope question"*. The component is not an orphan by §4's definition
(see C1, option (b)). This is a review record, not a deliverable, but the misquote is the stated reason for the
verdict choice. **Fix:** correct it when C1 is resolved.

---

## Item 3 — the rest of the change, checked with no finding

- **Rows vs Task 19's rules** (plan lines 925-945): every non-SHIP row has a `route`. Both `practice` harvests
  (`check-plan-code` → §22, `mutation-manifests` → §10) name headings that exist (`docs/portable-practices.md:1039`,
  `:236`). Both `data` rows have C4 `struck`. Every grade is `argued`, there is no `measured` grade, no
  `next_project_hours` is ≤ 0, and every cost has both estimates. The scan's counts were confirmed:
  `coverage-verdict` 0 findings, `mutation-manifests` 0, `velocity-docs` 2 (`2:1`, `4:1`, both cited).
- **Engine comparison:** 15 rows (4 for piece a, 7 for b, 4 for c), matching the dashboard's *"15 entries"*. Every row
  is `fetched` with a source, so Task 17's FAILS IF (a capability with no fetched source and not `unverified`) does
  not fire. The conclusions are scoped to the fetched pages. I did not re-fetch the pages; r1 did on 2026-11-22.
- **`load_manifests` as the "one executor":** other scripts mention `scripts/mutations`, but only `check-plan-code`
  executes manifests. The wording is defensible.
- **Dashboard entry:** the plain-language half matches the rows, and *"Nothing waits on you for this"* is wrong only
  if C1 goes to the owner (see C1's fix). The tech half carries C1's overstatement.
- **goal-threads line:** grammar matches its neighbours (`- fix · PR #616 · ...`), and the content matches the rows.
- **decision-log row:** well formed, with `outcome: null`. Its bet (*"r3 finds ... no finding caused by this fold"*) is
  **LOST** by C1 and C2. The coordinator should record that outcome.
- **Plan tick** (`[x] Steps`): consistent with the step text (*"until then, validate the rows parse"*). The FAILS IF
  does not fire.
- **Backlog #696 amendment:** accurate about what was done. Its own sentence *"a borrowed cite need not bear on the
  citing component"* is the argument for C1.

## Item 4 — fix-induced, and THRASHING

- C1: introduced by 548bcc39 (the `cites` lines changed from `[]`). **fix_induced: true**, component
  `marketplace-inventory-rows`.
- C2: the sentence was added by 548bcc39. **fix_induced: true**, same component.
- C4: the coordinator doc was added by 548bcc39. **fix_induced: true** (a review record).
- C3: the cite list dates from 8d6f913f, unchanged in 548bcc39. **fix_induced: false**.

**THRASHING IS ARMED:** r2 X1 (High, fix-induced by the r1 fold) and r3 C1 (MAJOR, fix-induced by the r2 fold) are in
the same component in consecutive rounds. All three rounds have folded the same two rows against the same rule
(§5 rule 1). The redesign question, *"can a redesign remove it?"*, has a yes answer: a stated rule for zero-finding
non-SHIP rows (backlog #696 (b)). That rule is the owner's to set, not a fold's.

```yaml
round: 3
half: claude
subject: marketplace-task17
reviewed: 548bcc39
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: true, component: marketplace-inventory-rows}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: true, component: marketplace-inventory-rows}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows}
  - {id: C4, severity: Medium, aim: process, fix_induced: true, component: marketplace-task17-review-record}
blockers: 0
thrashing_armed: true
```

VERDICT: NOT CONVERGED
