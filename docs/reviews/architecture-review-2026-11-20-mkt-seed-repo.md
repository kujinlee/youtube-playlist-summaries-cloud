# Architecture review (Phase 6) — `mkt_seed_repo.py`: typed facts and the oracle that chases them

- **Date:** 2026-11-20
- **Subject:** `scripts/mkt_seed_repo.py` and its self-test, on branch `hse-e` (PR #604, marketplace slice E), head
  `e5839bfd`.
- **Armed by:** THRASHING in component `mkt-seed-repo`. Round 2 finding Xm1, round 3 findings Cm1 and Cm2, and round 4
  finding Xm1 (backlog row 676) were each caused by the previous round's own fold
  (`docs/reviews/coordinator/hse-slice-e-r{2,3,4}-coordinator.md`).
- **Read first:** the four coordinator round documents and the halves they name, `CONTEXT.md`, `docs/adr/` (no ADR
  governs this component; none is re-litigated), `docs/review-method.md` → *The stop condition*, *Can a redesign remove
  it?*, *The arming condition — full account*, the plan's Task 13 contract
  (`docs/superpowers/plans/2026-11-11-marketplace-inventory.md`), `.agents/skills/brief/SKILL.md` Step 1, and the two
  2026-11-16 Phase 6 reviews for shape.
- **Method:** no tracked file was edited. Every input ran on a COPY: `probe.py` applies one named edit (each anchor
  required to occur exactly once) to a copy of a variant of the script beside a copy of `fixture_git.py`, runs
  `--self-test`, and prints the exit code, the last line and every `[FAIL]` line. Two variants: `head/` (the script at
  `e5839bfd`, byte copy) and `redesign/` (the prototype of §3). All of it is under the session scratchpad,
  `…/scratchpad/p6-mkt-seed/`. Host: macOS, git 2.49.0. Nothing ran on Linux.
- **Tags:** **[M]** measured in this review, **[I]** inferred.

## Verdict

**File it. The redesign is owed and should not be done in this PR.**

The self-test is fighting itself, and the cause is a mechanism, not missing branches. The seed TYPES the answer and
the `source` label of five facts and asserts three more empty, so the self-test has to re-derive each pairing by hand,
one property at a time. Each fold pinned the one property a reviewer had just walked around. At head, 13 of 20
one-sided edits of the seed still leave the suite 14/14 **[M]**, and 12 of those 13 are not row 676. A redesign that
declares each fact once as a command, reads every answer by running it, and compares the whole result to one
independent literal turns all 20 red **[M]**. So the test *can a redesign remove it?* answers yes, and patching row 676
alone would be round 5 of the same loop.

It is filed rather than done here for three measured reasons. No finding in the chain says a shipped fact is wrong:
all four fix-induced findings have `aim: instrument`, and the `known-facts.json` the tier-A record scored is what head
still produces (HEAD `3492d62`) **[M]**. The redesign changes that file (4 `source` strings, 2 answers in form), which
is new behaviour that owes its own round 1. And nothing later in the plan edits the seed: only Tasks 13 and 14 name it
**[M]**, so the holes are reachable only by a future edit of this one file.

Row 676 is an instance of the class, and the redesign closes it **[M]** (input H6). Recommended: do not fix row 676 on
its own; replace it with the row proposed in §5.

## 1. The thrash, restated as one mechanism

| Round | Finding | What the fold pinned | What it left free |
|---|---|---|---|
| r1 CM3 | typed facts never checked against the committed files | each typed answer, by a per-fact parse of hard-coded paths | the fact's `source` |
| r2 Xm1 | the case ignores `source` | `source` names the file, by token membership | other words in `source`; facts outside the hand-listed five |
| r3 Cm1, Cm2, Cm3 | membership; hand-listed ids; emptiness of `ratchets-absent` unchecked | exact `source`; "every non-git, non-empty item has a parse"; 3 names, none tracked | which names; distinctness; every other empty or git item |
| r4 Xm1 (row 676) | the 3 names need not be distinct | (filed) | — |

Every row has the same shape: an item is a free-form triple (`id`, `source`, `expected`), `source` is a label nothing
executes, and five answers are typed. The oracle is therefore a second, hand-written implementation of each pairing,
and it can only assert the properties someone thought to write. A reviewer who edits the seed finds the next
unwritten property. **[I]** on the causal reading; the table's contents are from the round documents.

**F1 [M] — at head the loop has not converged: 13 of 20 one-sided edits pass 14/14.** The 20 are the 6 historical
inputs (H1–H6), 12 new ones written for this review (N1–N12), and 2 world edits (R10, R15).

```
$ python3 probe.py head inputs_head.py        # then inputs_head2.py
SURVIVES  | control: no edit | rc 0 | 14/14 self-test cases passed
red       | H1 r1-CM3 status reads a blank line | rc 1 | 13/14
red       | H2 r2-Xm1 roadmap-status sourced README.md | rc 1 | 13/14
red       | H3 r3-Cm1 cat scripts/check-docs.py | rc 1 | 13/14
red       | H4 r3-Cm2 new typed fact, wrong source | rc 1 | 13/14
red       | H5 r3-Cm3 an absent ratchet is committed | rc 1 | 13/14
SURVIVES  | H6 r4-Xm1 (backlog row 676) one absent name three times | rc 0 | 14/14
SURVIVES  | N1 three distinct absent names, none of them brief's | rc 0 | 14/14
SURVIVES  | N2 absent list names the ratchet the seed HAS, as a .sh | rc 0 | 14/14
SURVIVES  | N3 live-release sourced from a file the repo has | rc 0 | 14/14
SURVIVES  | N4 a new EMPTY fact about a non-empty file | rc 0 | 14/14
SURVIVES  | N5 the task-list item is dropped | rc 0 | 14/14
SURVIVES  | N6 the ahead-count item is dropped | rc 0 | 14/14
SURVIVES  | N7 git item: label says branch, command run is another | rc 0 | 14/14
SURVIVES  | N8 git item typed, and wrong | rc 0 | 14/14
SURVIVES  | N9 git item's source label names another command | rc 0 | 14/14
SURVIVES  | N10 a second waiting decision the fact omits | rc 0 | 14/14
red       | N11 a second Status line the fact omits | rc 1 | 13/14
red       | N12 the seeded ratchet exits 3, the typed fact still says rc 0 | rc 1 | 13/14
SURVIVES  | R15@head the world's README changes, no fact does | rc 0 | 14/14
SURVIVES  | R10@head the world gains a decision no parse sees | rc 0 | 14/14
```

Three things in that output matter.

- **N7, N8, N9: the round 1 and round 2 defects exist unrepaired for the four git items.** A git item's label and the
  command actually run are two hand-typed things (`"git branch --show-current"` beside
  `_git(repo, "branch", "--show-current")`), and no case compares them or pins the answer. Only `git-log` has a case.
- **N3, N4, N5, N6: the item list is not pinned.** The docstring says "12 CHOSEN items"; dropping one, or adding an
  empty one about a non-empty file, is green. The r3 identity clause exempts every item with
  `empty_is_correct: true`, so an item escapes the oracle by being typed empty.
- **N11 is red for an ambient reason.** The added line shifts `ROADMAP.splitlines()[4]`, so `roadmap-deployed` breaks;
  the case reports `['roadmap-deployed']`, not the status fact the input was about. N10, the same edit for decisions,
  survives because the check is `in decisions`, membership where the fact is a set. That is row 676's shape again
  (a count where a set was meant) in a second place.

**F2 [I] — this is a mechanism defect, not a branch-coverage one.** `review-method.md`: *"If a different shape would
dissolve the finding, it is a mechanism defect and the redesign is owed."* F4 measures that a different shape
dissolves all 13.

## 2. What the slice decided that is not written down

**U1 [M] — what `source` means was never decided.** The 12 sources at head are four different kinds of thing: a
command (`git status --short`), a bare file path (`docs/roadmap-to-launch.md`, three items), a tool name (`TaskList`),
and a space-joined list of paths (`ratchets-absent`). Rounds 2 and 3 each legislated a little more of it ("names the
file its answer was parsed from", then "the WHOLE expected source, the verb included"). Whether `source` is a label
for the human scorer or the command that produced the answer is the fork under the whole chain.

**U2 [I] — round 1's fold chose "keep the facts typed and add an oracle" over "derive them", without weighing it.**
The module already derived the git items ("read from git, never typed"). CM3's fold extended the oracle instead of the
derivation, and the docstring records the outcome ("ARE typed, so a self-test case re-reads each") but not the choice.

**U3 [M] — the bar the reviewers applied is not in the plan.** Task 13 names three cases and one falsifier (*"two runs
of `seed` produce different `git rev-parse HEAD`"*). From round 1 on, the bar was "any one-sided edit of the seed that
leaves the suite green is a finding". That is a reasonable bar for an instrument a pass condition is scored against;
it is written nowhere, so each round raised it implicitly.

**U4 [M] — the seeded HEAD is quoted by the tier-A record and pinned by nothing.** `experiment-tier-a.md` scores
against `3492d62 Add the docs ratchet`. Editing the seeded README is 14/14 at head (R15), and the record then
describes a world the script no longer builds.

**U5 [M] — the items are not bound to `brief`'s Step 1.** 8 of the 12 sources appear verbatim in
`.agents/skills/brief/SKILL.md`; 4 do not. `ahead-count` is `git rev-list --count master..HEAD` where the skill runs
`git rev-list --count $(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo master)..HEAD`, and
the skill's deployed-line command is `grep -n`. Nothing fails if the skill's Step 1 changes. (Command: for each item
of a head-built `known-facts.json`, `item["source"] in SKILL.md text`.)

**U6 [I] — `live-release` and `task-list` are claims about the stranger's WORLD, not the seeded repository.** They
hold because the tier-A world is built with `build_world(…, ["python3","git","claude"])`. The seed asserts them and
nothing connects the two files.

## 3. The proposed redesign

One declaration of the seeded world's facts; every answer read, none typed; one independent literal compared whole;
a second world.

```python
RUN, RATCHET, UNREACHABLE = "run", "ratchet", "unreachable"
FACTS = (                                   # (id, kind, argv) — the ONLY place a fact is declared
    ("git-log", RUN, ("git", "log", "--oneline", "-15")),
    ("git-status", RUN, ("git", "status", "--short")),
    ("branch", RUN, ("git", "branch", "--show-current")),
    ("ahead-count", RUN, ("git", "rev-list", "--count", f"{BRANCH}..HEAD")),
    ("roadmap-status", RUN, ("grep", "^Status: ", "docs/roadmap-to-launch.md")),
    ("roadmap-deployed", RUN, ("grep", "Deployed: release", "docs/roadmap-to-launch.md")),
    ("decision-waiting", RUN, ("grep", "Decision: ", "docs/roadmap-to-launch.md")),
    ("backlog-open", RUN, ("grep", "| open |", "docs/backlog.md")),
    ("ratchet-check-docs", RATCHET, ("python3", "scripts/check-docs.py")),
    ("ratchets-absent", RUN, ("git", "ls-files", *(f"scripts/{n}.py" for n in ABSENT_RATCHETS))),
    ("live-release", UNREACHABLE, ("flyctl", "releases")),
    ("task-list", UNREACHABLE, ("TaskList",)),
)
```

- `source` IS `shlex.join(argv)` and `expected` IS what that argv prints in the built repository. This settles U1:
  the label and the command cannot differ in a declaration, because there is one of them.
- `RUN` must exit 0, otherwise `CANNOT RUN`; empty stdout is a correctly-empty item. `RATCHET` records
  `rc <code>: <stdout>`. `UNREACHABLE` is never run and is asserted empty (U6 stays an assertion, now a visible one).
- The two hand-written oracle cases (the typed-fact case with its `parsed_from` map and `git_derived` set, and the
  absent-ratchet case) are deleted. Four cases replace them:
  1. **The independent literal, compared whole** — `(id, source, expected)` for all 12 items in order, typed out in
     the self-test and derived from nothing in the module; only the SHA column of the log is cut. This is the
     independent copy and the identity case in one: a new, dropped, reordered, re-sourced or re-answered item is a
     difference.
  2. **A second world** — the seeded repository is copied and moved (one commit on a new branch changing the roadmap,
     backlog, ratchet and adding `check-test-counts.py`, plus one untracked file) so that all ten runnable facts
     change, and `known_facts` must return the moved world's own literal. Two distinct inputs for every producer.
  3. **The world pin** — `a.head == "3492d62a20b2140ffd1bc9726910989a03c915b3"`, the HEAD the tier-A record scored.
  4. **A `RUN` source that exits non-zero is `CANNOT RUN`, never an empty answer.**
  Seeding itself becomes a named case (`the seed builds`), so a seed that raises is one attributed red line, not a
  traceback.

**F3 [M] — the prototype runs, and what it changes in the artifact is small.** `redesign/mkt_seed_repo.py`: 355 lines
against 296; `17/17 self-test cases passed`, 2.7 s against 2.1 s wall clock (one run each). Both variants seeded with
`--out`, the two `known-facts.json` files compared field by field:

```
HEAD sha equal: True 3492d62 | items 12 12 | ids equal, same order: True
  roadmap-status differs in ['source']
  decision-waiting differs in ['source', 'expected']
  backlog-open differs in ['source', 'expected']
  ratchets-absent differs in ['source']
```

The two answers change in form, not content: the decision becomes the committed line
(`- ⛔ Decision: choose the storage backend … B: Postgres.`) and the open rows become the two committed table rows. The
tier-A record's item table paraphrases both (`storage backend — A: SQLite, B: Postgres`, `#2, #3`) and stays true
**[I]** — read, not re-scored.

### The attempts to refute it

**F4 [M] — on the redesign, 39 of 40 inputs are red; all 20 of §1's are red.** The corpus is §1's 20 inputs
re-expressed on the spec (plus H3b, round 3's two-file `grep`), and 19 inputs built against the redesign itself
(engine edits, world edits, declaration edits). One clean run against the final prototype:

```
$ python3 probe.py redesign inputs_final.py
SURVIVES  | control: no edit | 17/17
red       | H1 … H6 (7 inputs, backlog row 676 among them)                     15/17 or 0/1
red       | N1 … N12 (12 inputs)                                    15/17
red       | R1 engine: every answer is a cached constant            16/17
red       | R2 engine: label is one command, the run another        16/17
red       | R3 engine: a RUN that exits non-zero recorded as empty  16/17
red       | R3b, R4, R5, R6, R7, R8, R9                             0/1 … 16/17
red       | R10 the world gains a decision the pattern cannot see   16/17
red       | R11 the world gains an OPEN row spelled differently     16/17
red       | R12, R13, R14, R15, R16                                 14/17 … 16/17
SURVIVES  | R17 engine: git log runs without its -15, label keeps it | 17/17
red       | R18, R19, R20                                           12/17 … 15/17
-- 41 inputs, 2 survive            (the control and R17)
```

The full output, one line per input with the failing case names, is `…/p6-mkt-seed/final_run.txt`.

**F5 [M] — the first prototype was refuted three times, and each refutation changed the proposal.**

| Attack | Result on the first prototype | What changed |
|---|---|---|
| R3: the engine records a failing `RUN` as an empty answer | SURVIVED 16/16 | case 4 added; now red |
| R10, R11: the world gains a waiting decision, or an open row, spelled so that no pattern sees it | SURVIVED 16/16 | the world pin (case 3) added; now red. This is a tripwire, not a proof: it forces whoever edits the world to touch the pin, it does not check the fact list is complete |
| a third oracle, "replay each item's `source` and compare" | never the sole red case over 34 inputs (sole-killer counts: literal 5, second world 3, seed-builds 2, replay 0) | REMOVED from the proposal: surface with no measured kill |

**F6 [M] — one input survives, and it is the redesign's stated bound.** R17 edits the engine so that `git log` runs
without `-15` while the label keeps it. Both tested worlds have fewer than 15 commits, so no case can tell. Killing it
means a world with 16 commits, then another world for the next argument: the per-property loop again, one level down.
The retreat is fixed here, before anyone folds it: **the redesign claims that every one-sided edit of a DECLARATION
(`FACTS`, `ABSENT_RATCHETS`, the world's text, `HISTORY`) is red; an edit of the engine (`_answer`, 17 lines) is caught
only as far as the two tested worlds differ.**

**F7 [I] — what no reshaping of this self-test can check.** (a) That the 12 items are the right 12 for `brief`
(U5): the literal pins what they are, not whether they match the skill. (b) That the two `UNREACHABLE` items are
unreachable in the tier world (U6). (c) A two-sided edit, world and literal changed together to something false.
(d) Linux: `grep` with `^Status: ` and `| open |` as basic regular expressions, and the pinned SHA, were run on macOS
only; the SHA matches the one the tier-A run recorded on a separate build, and the script at head already depends on
it being stable.

## 4. Row 676

**Is it an instance of the class?** Yes **[M]**: it is the fourth consecutive "the last fold pinned a count, the
list's content was free" (§1 table), and N1 and N2 are the same hole reached without repeating a name — three
DISTINCT wrong names pass at head, so the fix row 676 asks for (require distinct names) would itself leave N1 and N2
green.

**Would the redesign close it?** Yes **[M]**: H6 on the prototype is red in two cases (the literal and the second
world), and so are N1, N2 and R14 (a name dropped).

## 5. Recommended work, not done in this PR

Proposed backlog row (text only; `docs/backlog.md` is not edited by this review). It REPLACES row 676, which should
be marked superseded by it rather than fixed alone.

> | (next id) | 🟡 **`mkt_seed_repo.py` types five facts and their `source` labels, so its self-test re-derives each
> pairing by hand and 13 of 20 one-sided edits of the seed pass 14/14** — filed 2026-11-20 from the Phase 6 review
> armed by thrashing on marketplace slice E (`docs/reviews/architecture-review-2026-11-20-mkt-seed-repo.md`).
> Supersedes row 676, which is one of the 13. **Do:** declare each fact once as `(id, kind, argv)`; make `source` the
> joined argv and `expected` what it prints in the built repository; delete the typed-fact and absent-ratchet cases;
> add (1) one independent literal of all 12 `(id, source, expected)` compared whole, (2) a second, moved world in
> which all ten runnable facts change, (3) a pin of the seeded HEAD `3492d62…` that the tier-A record scored, (4) a
> failing `RUN` is `CANNOT RUN`. A prototype passed 39 of 40 inputs in that review; re-anchor
> `scripts/mutations/mkt_seed_repo.json` in the same change (6 of its 11 anchors name typed-fact lines that go away).
> **Land it BEFORE any edit to the seed's facts or world, and before the seed scores another run.** **Bound, fixed in
> advance:** declarations only; an engine edit is caught only as far as the two worlds differ (review F6). **Fails
> if:** on the fixed script, any of the review's inputs H1–H6, N1–N12, R10 or R15 leaves `--self-test` at rc 0.
> ⟦kind: defect⟧ | `scripts/mkt_seed_repo.py`, `scripts/mutations/mkt_seed_repo.json` | M | (marketplace) | 🟡 OPEN |

Not proposed as rows, stated as bounds in the row above or left to the owner: U5 (items against `brief` Step 1) and
U6 (unreachable items against the tier world). Both are judgments about the experiment's design, not defects of this
script, and neither changes a recorded result **[I]**.

If the coordinator prefers the redesign in this PR after all: the prototype is
`…/p6-mkt-seed/redesign/mkt_seed_repo.py` (built by `build_redesign.py` from the head copy). Still owed on top of it:
the docstring, the manifest re-anchor and its `expected_mutations.py` pin, the self-test count (14 → 17) wherever it
is stated, a re-check of the pinned edge set in `check-shipping-sets.py` (the deleted case held one of the two
`sys.executable … check-docs.py` argvs), a Linux run, and a round 1 with both halves.

## Measured and inferred

| # | Claim | Tag | Evidence |
|---|---|---|---|
| F1 | at head, 13 of 20 one-sided edits pass 14/14; 12 of the 13 are not row 676 | **[M]** | `probe.py head inputs_head.py`, `inputs_head2.py` |
| F1 | N11 is red for a positional reason, not for the status fact | **[M]** | its `[FAIL]` line names `roadmap-deployed` |
| F2 | mechanism defect, not branch coverage | **[I]** | rests on F4 |
| U1 | `source` holds four kinds of thing | **[M]** | the 12 sources of a head-built `known-facts.json` |
| U2 | round 1's fold chose oracle over derivation unweighed | **[I]** | round 1 document; the docstring |
| U3 | the reviewers' bar is not in Task 13 | **[M]** | plan lines 713–730 read |
| U4 | the seeded HEAD is pinned by nothing | **[M]** | R15 at head, 14/14 |
| U5 | 8 of 12 sources are verbatim in `brief`'s skill file, 4 are not | **[M]** | substring test per item |
| U6 | the unreachable items are claims about the tier world | **[I]** | `experiment-tier-a.md` line 21 read |
| F3 | prototype 17/17; same HEAD; 4 sources and 2 answers differ | **[M]** | both variants seeded, files compared |
| F3 | the tier-A item table stays true under the two changed answers | **[I]** | table read, not re-scored |
| F4 | on the redesign 39 of 40 inputs are red, all 20 of §1's among them | **[M]** | `probe.py redesign inputs_final.py` |
| F5 | three refutations of the first prototype, and the replay oracle never the sole killer | **[M]** | first corpus run, per-input failing-case table |
| F6 | R17 survives; the bound is declarations, not the engine | **[M]** | R17, 17/17 |
| F7 | the four things no self-test shape checks; Linux not run | **[I]** | not run |
| §4 | row 676 is an instance; the redesign closes it; its own proposed fix leaves N1, N2 green | **[M]** for H6, N1, N2 at head and on the prototype; **[I]** that a distinctness check would not catch N1, N2 (not built) |
| Verdict | no shipped fact is wrong | **[M]** for the HEAD and the round documents' `aim: instrument`; **[I]** that no reviewer missed one |
| Verdict | only Tasks 13 and 14 name the seed | **[M]** | `grep` of the plan for `mkt_seed_repo`, `known-facts` |
