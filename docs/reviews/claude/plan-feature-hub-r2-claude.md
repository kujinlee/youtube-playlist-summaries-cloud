# Claude adversarial review — feature hub PLAN — round 2

Subject: `docs/superpowers/plans/2026-09-19-feature-hub.md` + `docs/superpowers/specs/2026-09-19-feature-hub-design.md` at HEAD `20188833`.
Reviewer: Claude half, round 2. Codex's round-2 half ran first and its findings were folded; this half reviews the plan *and those fixes*.

## Verdict: FINDINGS — 0 Blocking, 1 High, 3 Medium, 5 Low

**The round-2 gate is NOT met: this round adds one new High.** Everything Codex round 2 raised is
closed or measurably closed, the plan's code runs `23/23`, and all four mutations kill through the
case they name — but the `for:`-line fix from round 1 was applied to the *fixture only*, and the same
defect is still sitting in the spec's normative `absent` example and in Task 3's worked example. Both
are measured below, rejected by the plan's own parser.

---

## Did the plan's code run? — yes, 23/23

I assembled `check-features.py` the way an executor would: plan block at `:66` (the harness), then
block `:170` inserted above `_self_test` (Task 1 Step 3), then block `:342` appended into
`_self_test` (Task 2 Step 1), block `:375` inserted as module-level functions (Task 2 Step 3), and
the entry point replaced with block `:467`. Docstring count raised 15 → 23 as Task 2 Step 1
instructs.

| Run | Expected by the plan | Printed |
|---|---|---|
| Task 1 Step 2 (harness only) | `NameError: name 'parse_features' is not defined` | **exactly that**, rc=1 |
| Task 1 Step 4 (parser added) | `15/15 self-test cases passed` | **`15/15`**, rc=0 |
| Task 2 Step 4 (cross-file rules added) | `23/23 self-test cases passed` | **`23/23`**, rc=0 |

**Docstring count:** `count_drift` (`scripts/check-plan-code.py:1433`) reads
`--self-test\s+#\s*(\d+) cases`. The plan's docstring line is
`python3 scripts/check-features.py --self-test # 15 cases against synthetic trees` — one space
before the `#` and trailing words after `cases`. Both are tolerated by that regex, so the declaration
is canonical enough for `check-selftest-counts.py`. Raised to `# 23 cases` in Task 2, matching what
the suite prints. **No drift.**

### The mutation manifest — 4/4 killed, each through the case it names

Applied each manifest entry to the assembled source over a control proved green first
(`23/23`, rc=0):

| Manifest entry | Anchor matches | Result | Red cases |
|---|---|---|---|
| a built node with no fragment stops failing | **1** | KILLED 22/23 | `a built node with no fragment fails` |
| an absent node may carry fragments again | **1** | KILLED 22/23 | `an absent node WITH a fragment fails` |
| status tokens stop being rejected in node prose | **1** | KILLED 22/23 | `a status token in prose fails` |
| an unclaimed backlog area stops being reported | **1** | KILLED 22/23 | `an in-use area claimed by nobody fails` |

Every anchor resolves **exactly once** — not zero, not twice. Every `expect` list is an *exact* set
match against the `[FAIL]` names the mutant printed, so no mutation is credited to a sibling case
(the round-5 M1 shape `check-plan-code.py` warns about). Codex r2's High 3 is fully closed.

### The real run, against today's repo

Built a temp tree (`scripts/check-features.py` + real `docs/anchors.md`, `docs/backlog.md`, and the
Task 1 Step 5 `features.md`) and ran `main()`:

- **13 anchors** — 12 reported unclaimed, plus `cloud-publishing`. Matches the plan's claim.
- **21 backlog areas** — all 21 reported unclaimed. Matches the plan's and the spec's `~21`.
- `(cloud / money)` and `(cloud/money)` both appear as separate unclaimed areas, exactly as the spec
  predicts at `:124-126`.
- All four CANNOT-RUN paths returned **rc=2** with the `Treat this as NOT RUN.` sentence: missing
  `features.md`; `features.md` with no nodes; `anchors.md` yielding no anchors; `backlog.md`
  yielding no `(area)` tags.

---

## Codex round 2's four findings — closed?

| # | Finding | Status |
|---|---|---|
| Blocking 1 | Task 2 ran the checker before `main()` existed | **CLOSED.** Tasks 2/3 swapped; Task 3 `:500` now consumes "the COMPLETE checker from Tasks 1 and 2". But the swap left dangling references — see Medium 2. |
| Blocking 2 | `EXPECTED_MUTATIONS` key shape | **CLOSED and verified.** `check-plan-code.py:1145` compares keys to `m["file"]`; existing keys are paths (`"scripts/check-anchors.py": 5` at `:561`). `POPULATION` is built from `p.name` (`check-selftest-counts.py:259-264`) — bare names. The plan now states both conventions correctly at `:719-720`. |
| High 3 | stale `set(claims)` mutation anchor | **CLOSED and re-measured.** `set(area_claims)` matches the assembled source exactly once; the mutation kills. I re-checked all four anchors, not just this one — all four are unique. |
| Medium 4 | document drift from the r1 fold | **PARTLY CLOSED.** `Feature` column row gone from `:46`; self-review parenthetical rewritten; spec enforcement table `:182` now reads "every registry anchor is claimed by **exactly one** node"; `now` removed from the banned list in the plan `:24`, the spec `:157` **and** the code — `grep` finds no surviving "banned `now`" prose in either document. **Remaining:** the spec's Falsifier at `:191` still describes the dropped direction (Low 8), and `git add docs/anchors.md` at `:536` still stages a file no task touches (Low 6). |

---

## Findings

### [High] 1 — Round 1 fixed the missing `for:` line in the fixture and nowhere else; the spec's normative `absent` example and Task 3's worked example are both still rejected by the grammar

**Evidence.** Round 1 Blocking 1 (both halves) was that the self-test fixture's
`rate-limiting-per-account` had `state:` and `expected-because:` but no `for:`, while `check_nodes`
requires one on every node. The fix added `for:` **to the fixture**. The same node, in the shape it
was copied *from*, is still in the spec — and a second instance is in the plan.

Fed both through the assembled parser + `check_nodes`:

```
--- SPEC :91-96  absent-node example ---
   REJECTED: `rate-limiting-per-account` has a line that is neither a field nor a heading:
             'currently exhaust the shared spend cap.'. Keep each field on ONE line …
   REJECTED: `rate-limiting-per-account` has no `for:` line — every node says what it is for

--- PLAN :520-524  Task 3 Step 2 `dig-job-recovery` example ---
   REJECTED: `dig-job-recovery` has no `for:` line — every node says what it is for
```

Two distinct rules reject the spec's example. The `for:` half is the round-1 Blocking, unswept. The
wrapped-line half is **new damage from round 1's own fix**: the continuation-line refusal did not
exist before r1 High 8 added it, so the spec's example was legal-ish before that fix and is illegal
after it, and nobody re-ran the spec's example against the grammar the fix created.

The root cause is one line up. The spec's state table at `:86-89` reads:

| State | Must have | Must NOT have |
|---|---|---|
| `absent` | a one-line `expected-because:` | any fragment |

It never says `for:` is required — and the plan's Global Constraints repeat the same omission at
`:25` (`absent` = "an `expected-because:` line, zero fragments"). Both examples are faithful to
their own documentation; the documentation is what is wrong.

**Introduced by an earlier round's fix?** Half of it, yes — the wrapped-line rejection is r1 High
8's. The `for:` half is r1 Blocking 1 fixed as an instance rather than a class, which is this
repo's recorded *"after fixing, SEARCH for the class"* shape. It is the **third** document
occurrence of one defect and the first two were found by running code that nobody then pointed at
the remaining two.

**Why it matters.** Two costs, and the second is the larger one.

1. Task 3 Step 2 hands the executor `dig-job-recovery` as *"a true one, measured this session"* and
   Task 3 Step 4 then demands `check-features.py` exit 0. The executor pastes it, the check goes
   red on a rule the plan never stated, and the cheapest-looking repair is to weaken
   `check_nodes` — which is the one rule the `absent` state exists to carry.
2. The one-line-per-field constraint is documented **only inside the parser's error string**.
   Nothing in the spec or the plan tells an author that fields may not wrap, and the spec's single
   worked example wraps. `expected-because:` reasons are inherently long — the plan's own is 200
   characters — so this is the field most likely to wrap and the one with the least warning.

**Fix.**
- Spec `:86-89`: add `for:` to the **Must have** column for *both* states, and state the one-line
  rule for every field (a sentence beside the table, since it is grammar, not state).
- Spec `:91-96`: give `rate-limiting-per-account` a `for:` line and unwrap `expected-because:`.
- Plan `:25`: add "`for:` on every node, each field on one line" to Global Constraints.
- Plan `:520-524`: give `dig-job-recovery` a `for:` line.
- Then re-run *every* markdown node example in both documents through `parse_features` +
  `check_nodes`. There are three (spec `:91-96`, plan `:274-296`, plan `:520-524`) plus Task 4's
  inline fixture; I ran all four, and only the two named above fail.

---

### [Medium] 2 — The Task 2/3 swap was a block move; eight references still point at the pre-swap numbering

**Evidence.** `git show HEAD` shows the swap as a delete-and-reinsert of two whole sections. Nothing
outside those sections was renumbered. Post-swap, Task 2 = cross-file rules, Task 3 = the real tree.

Five of the fifteen rows in the self-review spec-coverage table (`:758-774`) are now inverted:

| Row | Says | Should say | Why |
|---|---|---|---|
| Feature tree, three trunks | 2 | **3** | the tree is Task 3 |
| `areas:` alias map, no per-row backlog edits | 3 | **2** | `backlog_areas` is Task 2 Step 3 |
| Every in-use area claimed exactly once | 3 | **2** | `check_cross` is Task 2 Step 3 |
| Anchors resolve to the registry | 3 | **2** | `check_cross` is Task 2 Step 3 |
| `backlog.md` unparseable → exit 2 | 3 | **2** | `main()`'s rc=2 paths are Task 2 Step 3 |

And three in prose:

- `:56` — "a minimal 3-node tree, expanded in **Task 2**" → expanded in Task 3. (Also "3-node": Step
  5 at `:274-296` creates **two** nodes. Both halves of that phrase are wrong.)
- `:776` — "the one open-ended step (**Task 2**'s tree contents)" → Task 3's.
- `:778` — "`parse_features` returns `(list[Node], list[str])` in Tasks 1, **3** and 4" → Tasks 1, 2
  and 4. Task 3 contains no Python at all.

**Introduced by an earlier round's fix?** Yes — entirely by round 2's swap.

**Why it matters.** The self-review table is the plan's own coverage claim, and it is what a Phase 2
reader checks the spec against. Five of fifteen rows send that reader to a task that does not
contain the work. It is also the exact failure mode the swap was warned about: a section move
leaves references behind, and the only defence is to grep `Task [0-9]` afterwards.

**Fix.** Correct the five table rows and the three prose references. Then `grep -n "Task [0-9]"` on
the plan once more — that command is what produced this list.

---

### [Medium] 3 — Two stale case counts survived the 12 → 15 → 23 fold, one of them into a commit message the plan tells the executor to write

**Evidence.**

- `:324` — the body of `/tmp/t1.txt`, which Task 1 Step 7 tells the executor to commit verbatim,
  ends `12/12 self-test cases pass.` The suite at that point runs **15/15** (measured above). The
  plan would put a false measured claim into permanent git history.
- `:778` — "The self-test count rises **12 → 18 in Task 3**". Every number is wrong: it is 15 → 23,
  and it happens in Task 2. (The task number is Medium 2's; the counts are this finding's.)

Everywhere else the counts are right: `:71` and `:268` and `:300` say 15, `:340` and `:474` and
`:529` and `:746` say 23, `:780` says `11/12 → 23/23`.

**Introduced by an earlier round's fix?** Yes. Round 1 raised the count from 12 to 15 and round 1's
fold raised the Task-2 total to 23; both passes updated the executable sites and missed these two
prose sites.

**Why it matters.** This repo's own rule is that *a number in prose has no owner* —
`check-selftest-counts.py` exists because of it, and it cannot see a count inside a commit-message
template or a self-review paragraph. A commit message asserting `12/12` is the durable half: it
outlives the plan and nothing will ever re-check it.

**Fix.** `:324` → `15/15 self-test cases pass.` `:778` → "rises 15 → 23 in Task 2". Consider
deleting the count from the commit template entirely — the docstring already owns it and
`check-selftest-counts.py` verifies it, so a second copy can only drift.

---

### [Medium] 4 — Both documents state that a `built` node must not carry `expected-because:`; nothing enforces it, and it is accepted silently

**Evidence.** Plan Global Constraints `:25`: "`built` (≥1 fragment, **no `expected-because:`**) or
`absent` (an `expected-because:` line, zero fragments). **Both directions enforced.**" Spec `:103`
makes the same "both directions" claim.

`check_nodes` (plan `:234-260`) only ever inspects `expected_because` inside
`if n.state == "absent":`. Measured against the assembled source:

```
built node WITH expected-because  ->  ACCEPTED (no problem reported)
   node.expected_because = 'and also it does not exist.'
```

The direction that *is* enforced is `absent` + fragments → fail (case
`an absent node WITH a fragment fails`, and a mutation covers it). The direction claimed here has
neither a rule nor a case nor a mutation.

**Introduced by an earlier round's fix?** No — pre-existing, and missed by both halves of both
rounds. I am reporting it because "both directions enforced" is asserted twice and is half true,
and because r1's Blocking was the *other* unenforced clause of the same two-state rule.

**Why it matters.** It is a leftover-state hazard aimed at the one transition this design exists to
catch. A node flipped `absent` → `built` when the feature ships keeps its stale
`expected-because:` sentence ("this does not exist because…") on a node now marked built. The
renderer's contract is unspecified for that combination, so the page can show a built feature
explaining why it is absent — and the guard whose whole job is "a feature cannot quietly get
implemented while the tree still says it does not exist" passes it.

**Fix.** Either (a) add the rule — three lines in `check_nodes`, one self-test case, one manifest
entry, count 23 → 24 and `EXPECTED_MUTATIONS` 4 → 5; or (b) drop the clause from plan `:25` and
soften "both directions enforced" in spec `:103` to name the one direction that is. (a) is the
cheaper of the two given the fixture already exists. Do not leave the sentence as written.

---

### [Low] 5 — Task 3 has no Step 3

`:503` Step 1, `:512` Step 2, `:526` **Step 4**, `:533` Step 5. The gap predates the swap (the
deleted Task 2 block had the same 1-2-4-5 sequence), so the block move preserved it faithfully.
Harmless to execution, but a checkbox plan whose numbering skips reads as a step that was cut, and
a reader cannot tell whether something was lost. Renumber to 1-2-3-4.

### [Low] 6 — Task 3's commit step stages a file no task modifies, and names a message file that is never written

`:535-538`:

```bash
git add docs/features.md docs/anchors.md
git commit -F /tmp/t2.txt
```

`docs/anchors.md` was only ever touched by the deleted `Feature` column — residue of Codex r2's
Medium 4, one line below a paragraph that announces the column is gone. And `/tmp/t2.txt` is never
written: Task 1 spells out its message file at `:310`, Task 2's Step 5 ("Commit") has no body at
all, and Tasks 4/5/6 likewise. Drop `docs/anchors.md`; either write the `/tmp/t2.txt` body or use
the same "write the message file first" instruction the other tasks now lack.

### [Low] 7 — Task 2 Step 4's quoted failure count is 33; running the plan as written gives 34

`:479` shows `FAILED — 33 feature-map problem(s):`, hedged as measured "with a one-node tree". Task
1 Step 5 creates a **two**-node tree, and both of its nodes carry `anchors: cloud-publishing`.
Measured against today's repo with the tree the plan actually produces:

```
FAILED — 34 feature-map problem(s):
  ✗ anchor `cloud-publishing` is claimed by 2 nodes: job-queue-and-worker-lifecycle, wake-on-visit
  ✗ backlog area `(cloud / money)` is claimed by no node …
```

33 = 21 areas + 12 unclaimed anchors, so the quoted number is honest for the input it names — but
no executor will see it. The extra line is the duplicate-anchor rule firing on the plan's own
starter tree. Either quote 34 and show the duplicate-anchor line (it is a nice demonstration), or
give the two starter nodes distinct anchors.

### [Low] 8 — The spec's first Falsifier still describes the dropped `Feature` column direction

`:191`: "Delete a node that `anchors.md` references → `check-features.py` fails naming it."
`anchors.md` references no nodes; the edge now points node → anchor. The check does still fail
(`anchor X is claimed by no node`), so the falsifier is *true by accident* while describing a
mechanism that does not exist. Reword to "Delete a node that claims a registry anchor → fails,
naming the now-unclaimed anchor."

### [Low] 9 — "39 suites already print it"

`:28` and `:106-107` say 39 suites print the canonical `[FAIL] ` line.
`grep -rl '\[FAIL\] ' scripts/*.py | wc -l` returns **47** today. The claim's direction is safe
(the convention is more established, not less) and nothing depends on the number, but it is another
count in prose with no owner. Say "over 40" or drop the figure.

---

## Things I checked and found correct

Every one of these was verified by running or by opening the cited file, not by reading the plan's
claim about it.

- **`EXPECTED_MUTATIONS` / `POPULATION` conventions.** `check-plan-code.py:522` is the dict;
  `:1145` compares its keys against each manifest's `"file"`; `:561` is `"scripts/check-anchors.py": 5`.
  `check-selftest-counts.py:83` is `POPULATION`; `:259-264` builds the found-set from `p.name`.
  The plan's `:719-720` states both correctly, including the warning that they are opposites.
- **The ratchet contract, R1–R4, for both new scripts.** `check-features.py` matches
  `GUARD_PATH_RE` (`check-ratchet-contract.py:113`), so all four rules apply: R1 self-test ✓, R2 no
  `except` returning 0 (the plan's code has no `try` at all) ✓, R3 CI caller via Task 6 Step 1 ✓,
  R4 manifest ✓. `gen-features-page.py` does **not** match that regex, so per `evaluate()`'s
  comment at `:212` only R4 is asked of it — the plan's `NO-MUTATIONS:` reason is the right escape,
  it is in the docstring (required since `:296`), and `NO_MUTATIONS_RE` (`:267`) accepts its shape
  (marker, one space, a real reason, no angle bracket). `MANIFEST_BASELINE = 0` (`:284`) is an
  exact match in both directions and **stays 0**, because the escape means the file is not counted
  as debt. The plan needs no baseline edit and correctly does not make one.
- **`CELL_SPLIT`.** `check-docs.py:319` is `re.compile(r"(?<!\\)\|")`, verbatim as the plan quotes
  it at `:31-33`. The escaped-pipe self-test case recovers `(comprehensibility)` from a row with two
  escaped pipes; a naive `split("|")` drops it.
- **`explainer-serve.py` registration.** `REGENERABLE` at `:122`, `PAGE_SOURCES` at `:139` (the plan
  says "near 140"). `_stale_sources_covered` at `:1480` asserts
  `sorted(PAGE_SOURCES) == sorted(REGENERABLE)`, so the plan's warning to add to both is real and
  the self-test it points at is the one that catches a single-sided edit.
- **`ci.yml`.** The `check-anchors` / `check-anchors self-test` pair sits at `:182-186`; the plan's
  two new steps at `:674-680` match that shape exactly.
- **The files Task 4 and Task 5 copy from exist.** `.claude/hooks/regen-goals-page.sh` and
  `scripts/gen-goals-page.py` are both present.
- **`docs/features.md` entering `check-docs.py`'s population.** `living_docs()` (`:65-70`) globs
  `docs/*.md`, so the new file is in scope. I checked what that costs: `check_duplicate_headings` is
  **ADR-scoped only** (`:266-268`), `check_line_budgets` reads an explicit `LINE_BUDGETS` map that
  will not contain it, and only `check_living_links` applies — the Task 1 tree has no markdown
  links. Nothing red on arrival, and the plan's silence about it is correct rather than lucky.
- **Task 4's inline fixture is legal.** Unlike the two in Finding 1, the `wake-on-visit` /
  `dig-job-recovery` pair at `:557-562` parses to two nodes with **zero** problems — both have
  `for:` lines, the absent one has `expected-because:` and no fragments. This is what makes Finding
  1 an unswept instance rather than a disagreement about the rule.
- **`now` is gone from the prose in both documents**, not just the code — `grep` finds no surviving
  banned-word list containing it, and the spec at `:158-160` records *why* it was dropped.
- **The `Feature` column** survives only in the spec's amendment heading and its explanatory
  sentence (`:131`, `:133`), which is the correct place for a historical record.
- **Counts.** 13 anchors and 21 backlog areas, both measured from the real files, both as the plan
  states. `(process / deliverable #2)` is an area name containing `#2`, which I checked cannot trip
  the status-token rule — `STATUS_TOKENS` is applied to `n.purpose` only, never to `areas:`.
- The spec says "a 142-row backlog" at `:11` and "not 140 row edits" at `:117`;
  `grep -cE '^\| *[0-9]+ '` says **142**. Not worth a finding, but `:117` should say 142.

## What I could not run

- **Nothing is implemented.** Everything above is the plan's extracted code executed in
  `/tmp/fhr2/`, plus real repo files read in place. No file outside `docs/reviews/claude/` was
  touched; `git status` is clean apart from this review.
- **`gen-features-page.py`'s 6 cases.** Task 4 specifies the cases but not `render`, so the suite
  cannot be assembled or run. Its declared `# 6 cases` matches the six `check()` calls the plan
  lists, which is as far as a plan can be checked. The claim "6/6 passes" is unverifiable until
  Task 4 Step 3 is written — flagging it as the one place in this plan where a stated result is
  still a prediction.
- **Task 5's hook and Task 6's CI steps** — the hook does not exist and CI cannot be run locally.
- **`check-plan-code.py --mutate .`** end to end. I applied this manifest's four entries by hand to
  the assembled source instead, which measures the same thing for these four but not the harness
  wiring. Task 6 Step 4's `4/4 killed` should still be confirmed by the real runner, and note that
  the command runs *every* manifest in the repo, not only this one.
