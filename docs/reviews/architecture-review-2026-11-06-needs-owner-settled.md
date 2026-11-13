Reviewed head: 9131df49d1f7b947b8b2989290175c9a92a6947f

> **For the r4 fold of `needs-owner-settled` (PR #528, backlog #496).** Triggered by **THRASHING**, by the letter of
> `docs/dev-process.md` → *Phases*, row 6: the component `settled-history-reader` (clause 2) carried fix-induced
> findings in r2 (Codex R2-1, caused by r1's `--first-parent`) and r3 (Claude F1 and F2, caused by r2's
> `--topo-order --diff-merges=off`).
>
> **Verdict:** thrashing, design-caused. The class is "reconstruct, at read time, the head a marker was written under
> from git history", and it is open-ended: every round found a new git topology. **Recommend (c): drop clause 2 from
> PR #528, keep clause 1, and FILE a write-time check on the PR diff** that does what clause 2 was for without any
> history walk. Measured over all 302 backlog revisions, that check fires once, on the commit that settled backlog #384,
> and on nothing else. **BLOCKERs: none.** One defect found that is not clause 2's (§5): at HEAD, backlog #496 lists
> ITSELF in NEEDS YOU.

# Phase 6 architecture review (narrow, triggered by thrashing): clause 2 of backlog #496, the history reader in `scripts/goal-tree.py` (PR #528)

Scope: `head_moved_on`, `backlog_commits`, `status_cell`, `head_when_marked`, `git_head_when_marked`, their caller in
`collect` (the `needs_from_backlog(text, git_head_when_marked(root, run))` line) and `needs_from_backlog`'s clause order.
Read only. Read first: `CONTEXT.md`, `docs/adr/` (fourteen ADRs; none covers NEEDS YOU, the backlog marker or the goal
tree, so none is re-litigated), backlog #496 and backlog #384, the r1 and r2 coordinator documents, and the r1-r3
reviews. Nothing under `.claude/plans/` was read. Measurement scripts are outside the repository, in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/arch496/`:
`corpus.py` (runs the shipped code at each revision) and `sim.py` (an independent model of the alternatives; it does
not import the code under test's clause-2 functions).

## 1. Thrashing or prose floor?

**Thrashing, and design-caused. It is not a prose floor.** Each fix-induced finding is a behavioural defect with a
scenario that was built and run in real git.

| Round | Finding | Fix-induced by | Evidence (quoted from the review) | Kind |
|---|---|---|---|---|
| r2 | Codex R2-1 Medium | r1's `--first-parent --diff-merges=first-parent` | "fork a feature branch before an ask exists; on master, introduce the marker under `OPEN`, then rewrite the head to `SPEC MERGED`; merge master into the feature branch. The reader treats the merge as the marker's introduction … and returns no flag." | silent miss |
| r3 | Claude F1 Medium | r2's `--topo-order --diff-merges=off` (default history simplification) | "On B: the merge's backlog equals trunk's, so `git log -- <path>` … follows ONLY the trunk parent and prunes B's line entirely … → **no flag**. Under r1's `--first-parent`, B's own chain `b2, b1` was walked and the row WAS flagged." | silent miss |
| r3 | Claude F2 Low | r2's `--topo-order` | "`git log --topo-order` emits the SECOND parent's line first — so `m1` (head `OLD`) wins over `b1` (head `NEW`, which today's text actually descends from) → **flagged 'head rewritten'**, falsely." | false flag |

r2 Codex R2-2 (renumbering) and r3 F3/F4 (doc drift, unpinned `rev`) are not fix-induced.

**The cause, in one sentence: clause 2 answers a question about the TEXT ("what did this row's head say when its
marker was written?") by reconstructing it from GIT HISTORY, and git history has no single answer to "when".** A
squash collapses the moment. A merge has two parents, so the moment exists on two lines. A renumber breaks the row's
identity. A shallow clone cuts it off. Each fold chose one reading of history (first parent, then every line in
topological order) and the next round built the topology that reading gets wrong. Nothing in this repository's data
exercises those topologies: origin/master has **0 merges on its first-parent line since 10-01** (RUN:
`git log --merges --first-parent origin/master --since=2026-10-01` → 0), so every reading agrees on the corpus and
every finding came from a built scenario. The reviews will keep finding them, because the space is git's, not ours.

## 2. What clause 2 buys, measured

**Instrument 1, the shipped code** (`corpus.py`): every backlog revision on HEAD's line since 10-23, each read at its
own `rev` with `needs_from_backlog(text, git_head_when_marked(root, run, rev=sha))`. Clause 2 is also computed
independently of the other flags, to see overlap.

- **117 revisions, 1132 listed row-revisions.** These match the r2 coordinator's figures (117 and 1132).
- Flags by source:
  - clause 1: backlog #90 (43), backlog #194 (43), backlog #306 (47);
  - cross-reference: backlog #126 (3), backlog #347 (3), backlog #496 (1, see §5);
  - **clause 2, where nothing else flagged: backlog #384 only, 15 revisions;**
  - NOT READ: 0.
- **Clause 2 computed independently fires on backlog #384 and nothing else**, in the same 15 revisions. It does not
  fire on the clause-1 rows either: their heads were never rewritten.
- The 15 revisions run from `fd804427` (2026-11-02) to `a67b59a5` (2026-11-03). Then the owner wrote
  `NEEDS-OWNER answered` on #384 by hand and the row stopped being listed.
- Cost per revision: at most 1.27 s.

**So clause 2's measured value is one row, for about one day, and the owner had already caught it by hand.** That is
not nothing: #384 is one of the two rows #496's own FAILS IF names, and of the three settled rows the owner met on
11-03, it is one of the two any check could reach (dashboard `2026-10-31/4` is out of reach by #496's own account).
But at origin/master today, **NEEDS YOU lists 0 backlog rows** (RUN at `fca33440`, the last master backlog revision),
so clause 2 currently checks nothing.

**What it costs**, read from `git diff origin/master...HEAD`:
- about 120 lines of `scripts/goal-tree.py` (lines 700-820 at HEAD, docstrings included);
- about 27 of the branch's 39 backlog #496 self-test cases (17 of them build real git repositories);
- at least 16 of the 34 added mutations (a text match on the clause-2 symbols, so a lower bound);
- one `git log -p` over the whole backlog history on every page refresh. r3 measured 1.8 s at 302 commits, and the
  cost grows linearly with backlog history;
- three review rounds, with two silent-miss bounds and one false-flag bound still open (§1), plus the renumber bound.

## 3. Can a redesign remove the class?

The test: does the option still have to reconstruct, from history, the moment a marker was written? I simulated each
option with `sim.py`, an independent model. It walks all **302** backlog revisions on HEAD's line, oldest to newest.
This line is linear, since master is squash-merged, so one revision is one PR. At each revision `sim.py` reads the
whole file and its own row and status split.

### (a) Keep the git walk and document the round-3 bounds

**Does not remove the class.** It stops the rounds procedurally, because the round cap files r4's findings, but the
reader stays as wrong as it is today on squash-within-PR (r3 F1, silent), the merged-in withdrawn introduction (r3 F2,
false flag), renumbering (r2 R2-2, silent) and evil merges (NOT READ). Any future change to the walk reopens all of
them.

- **Catches:** backlog #384, 15/15 (§2).
- **It is the only option that meets #496's FAILS IF literally.** The falsifier is phrased on a historical corpus
  ("on the 2026-11-03 corpus … flag backlog #306 and backlog #384 before today's edits"). A historical corpus carries
  no baseline in its text, so only a history reader can pass it as written. **I infer that this phrasing is why a git
  walk was built.** Nothing written says so (§6).
- **Work:** S. One bound sentence for F1, one clause for F2, and the doc-drift fixes for F3 (the dashboard entry
  still says `--first-parent`, the docstring says "every line"). Add a `rev` case for F4.

### (b) The marker carries its own baseline

**Date variant, `NEEDS-OWNER (asked 2026-11-01)`: does not remove the class.** A date can only be compared with WHEN
the head was last edited, and the text does not hold that. #384's rewritten head reads "OPEN — spec merged in PR #474
(b4164c10) …", with no date (READ, `fd804427^` and `fd804427`). So the date variant needs `git log` or `git blame` to
date the head edit. That is the same history reconstruction, plus a squash moving every date to the merge day.
Rejected.

**Fingerprint variant, `NEEDS-OWNER [asked-under: 3f9a1c]`** (a short hash of the head when the ask was written):
**removes the class.** Clause 2 becomes `hash(head now) != stamp`, which is pure, needs no git, and travels with the
text through squashes, merges, renumbers and shallow clones.

- **Catches, simulated:** the stamp is the head at the revision where the marker's segment first appeared in the row.
  It flags backlog #384 on 15 revisions from `fd804427`, the same row, count and first revision as the shipped
  clause 2. Nothing else is flagged.
- **Costs:**
  - **A new marker grammar** that every writer of `NEEDS-OWNER` must produce, with an opaque token inside human prose.
  - **A stamping tool** and **a lint that refuses an open marker without a stamp**. That lint is a new guard, so
    `check-ratchet-contract.py` needs a `--self-test`, mutations and a caller.
  - **The stamp is only as good as the moment it is written.** If the lint's fix-up stamps at commit or PR time, a
    head rewritten in the same PR as the marker is stamped with the settled head: r3 F1's blind spot again, by another
    route. An agent that meets a failing lint can also restamp and hide the flag.
  - **Migration:** zero. Master has no listed backlog row today (§2).
  - **It cannot meet the FAILS IF literally either:** an unstamped historical marker is NOT READ.

### (c) Drop clause 2; keep clause 1, and make the convention a PR-time diff check

**Removes the class.** The check runs when a head is rewritten, in the PR that rewrites it, and reads exactly two
texts, the PR's base and its head. That is the same `--base origin/master` plumbing `check-dashboard-entry.py` already
uses (`fetch-depth: 0`, `.github/workflows/ci.yml`). It asks no question about when anything happened.

**Rule:** a row whose open marker segment is present, outside the head, both before and after the PR, and whose head
the PR changed, is reported. The editor then writes `NEEDS-OWNER answered` or restates the marker. The person
rewriting the head is the one who knows whether it settled the ask, which no reader of history can know.

- **Catches, simulated over all 302 revisions (not only since 10-23): exactly 1 hit, 0 others.** The hit is
  `fd804427` (2026-11-02, PR #477, "the suite spec's rows filed"), backlog #384, head
  "OPEN — filed 2026-10-27; needs an owner walkthrough (spec), not a build" → "OPEN — spec merged in PR #474 …".
  That is the true positive, caught in the PR that caused it and before any page showed it. There are **0 false
  hits**, so no unrelated head edit was made on a row with an open marker in the whole history.
- **Costs:**
  - About 120 lines, about 27 cases and at least 16 mutations deleted from PR #528.
  - A new check of perhaps 40 lines, built as its own backlog row, with its own cases and mutations.
  - #496's FAILS IF has to be restated (below).
- **Blind spot:** a marker introduced and its head rewritten in ONE PR (the base has no marker). This is the same
  shape as r3 F1. The question was asked and answered inside one PR, under the eyes of that PR's reviewers.
- **The interim:** until the check lands, a head rewrite on an open-marker row is not flagged at read time. The
  exposure today is 0 listed rows, and 1 such rewrite in 302 revisions.
- **A convention with no check** (plain (c)) would have the same value only if remembered. This repository's record
  on remembered conventions is the reason backlog #496 exists, so the check is part of the recommendation, not an
  option on top.

## 4. Recommendation

**(c), with the convention as a PR-time diff check, filed rather than built in PR #528.** It is the only option
that both removes the class and keeps clause 2's measured value (#384 at `fd804427`, 1/1, 0 false in 302 revisions).
It also catches the rewrite at the right moment: when it is made, by the person making it.

- (a) is cheaper today, but it keeps an open-ended class on a page refresh and grows with history.
- (b) removes the class at the price of a grammar, a stamper and a lint, with the same blind spot as (c). It is (c)'s
  value with more machinery.

| Item | r4 action | BLOCKER? | Why |
|---|---|---|---|
| Delete clause 2 from PR #528: `head_moved_on`, `COMMIT_MARK`, `backlog_commits`, `status_cell`, `head_when_marked`, `git_head_when_marked`, `RESTATE_REMEDY`; `collect` and the self-test caller pass no history; drop the clause-2 cases and their mutations (move the pin accordingly) | **DO in r4** | no | §1–§3: the class cannot be closed by another fold; the value it held is moved to write time |
| Restate backlog #496's FAILS IF: clause 1 flags backlog #306 on the 11-03 corpus (kept, as today's ⭐ case does); backlog #384's shape moves to the new row below, whose falsifier is "the check fires on `fd804427` and on no other of the backlog's revisions" | **DO in r4, and SAY it in the PR body** | no | A changed falsifier must be visible. If `check-merge-ready.py` reads it as a loosening and HOLDs, that HOLD is the owner's (`docs/dev-process.md`) |
| Fix §5: backlog #496's own status mentions the marker as a bare token, so NEEDS YOU lists #496 | **DO in r4** (reword the status) | no | measured at HEAD; merging as-is ships a false ask |
| Update `docs/dashboard-entries.md`'s 2026-11-06 entry and #496's status to describe clause 1 only | **DO in r4** | no | r3 F3; it already describes a design that no longer exists |
| NEW ROW: a PR-time check (in CI, `--base origin/master`) that reports a row whose open `NEEDS-OWNER` segment survives the PR outside the head while the PR rewrote the head; remedy `NEEDS-OWNER answered` or restate. Warn first; decide block vs warn with the measured rate (1 in 302) | **FILE** (tooling, S) | no | §3(c) |
| NEW ROW: the marker grammar. A mention of the token in prose (backticked, or in a sentence about markers) is read as an ask (§5) | **FILE** (S) | no | one instance measured; the class is any row that documents the marker |
| (if (a) is chosen instead) r3 F1 bound sentence, F2 clause, F3 drift, F4 `rev` case | — | no | the work (a) needs, for comparison |

## 5. A defect outside clause 2: backlog #496 lists itself

The branch's own status for backlog #496 (written in `435ef151`, extended in `a5f32c3d`) quotes the remedy
"restate the question as a new `NEEDS-OWNER` marker". `needs_owner` takes the LAST occurrence of the token, finds no
`answered` after it, and lists the row.

- RUN at HEAD (the working tree's `docs/backlog.md`, `needs_from_backlog(text, None)`): the only item listed is
  `('backlog #496', 'may already be answered by backlog #86')`.
- The corpus run shows the same at `a5f32c3d`, the last revision that touched the backlog (`9131df49` did not).
- r3 noted the listing ("HEAD lists one row (backlog #496 itself …)") but did not call it a defect.
- Merging PR #528 as-is puts a false "needs you" item on the goal tree, about the very feature meant to remove false
  ones.

The marker is a bare substring, and a row that DOCUMENTS the marker cannot be told from a row that CARRIES it.

## 6. What did we decide on this branch that isn't written down?

1. **That #496's falsifier, phrased on a historical corpus, requires a history reader.** Nowhere is it written that
   the FAILS IF chose the design. This review infers it (§3(a)), and every option that removes the class needs the
   falsifier restated.
2. **That master is linear.** r1's coordinator says "On this repository's squash-merged master the two readings
   agree". The walk's correctness on real data rests on that, and neither `backlog_commits`' docstring nor the row
   says so. The 0-merges measurement in §1 is the evidence.
3. **That a 1.8 s, linearly growing `git log -p` on every page refresh is acceptable.** No budget is written. The only
   bound is the 60 s `git log` timeout.
4. **That a status HEAD (the text before the first ⟳) is "the current state, rewritten in place".** That convention
   exists in `goal-tree.py`'s comment block and nowhere in the backlog's own conventions (READ: a grep of `docs/*.md`
   other than the backlog for "status head" finds only a goal-threads line and an old dashboard entry). Clause 2, and
   the PR-time check that replaces it, both depend on it.
5. **That the `NEEDS-OWNER` token has no grammar beyond a substring** (§5). It was never decided; it was inherited,
   and this branch is the first to write prose about markers inside a status.

## 7. Measured vs inferred

| Claim | Status | How |
|---|---|---|
| 117 revisions / 1132 row-revisions since 10-23; clause 2 flags only backlog #384, 15 revisions, independently and as shipped; 0 NOT READ | **MEASURED** | `corpus.py`, the shipped code at each `rev` |
| Clause 1 flags backlog #90 (43), #194 (43), #306 (47); cross-reference flags #126 (3), #347 (3), #496 (1) | **MEASURED** | `corpus.py` |
| NEEDS YOU lists 0 backlog rows at origin/master (`fca33440`) | **MEASURED** | `corpus.py` |
| Max 1.27 s per revision | **MEASURED** | `corpus.py` (r3: 1.8 s for the reader at HEAD's 302 commits) |
| A stamp model flags #384 on 15 revisions from `fd804427`, nothing else | **MEASURED** (a simulation: the stamp is the head at the marker's first appearance on a linear history) | `sim.py` (B) |
| A PR-time diff check fires once in 302 revisions (`fd804427`, #384) and never falsely | **MEASURED** (a simulation: one linear revision = one PR) | `sim.py` (D) |
| origin/master has 0 merges on its first-parent line since 10-01 | **MEASURED** | `git log --merges --first-parent` |
| Backlog #496 lists itself at HEAD | **MEASURED** | `needs_from_backlog` on the working tree's backlog |
| #384's rewritten head carries no date | **READ** | `git show fd804427^:` and `fd804427:docs/backlog.md` |
| ~120 lines, ~27 of 39 cases, ≥16 of 34 mutations are clause 2's | **READ** (line range and case names by hand; mutations by a symbol text match, a lower bound) | `git diff origin/master...HEAD` |
| The FAILS IF's phrasing is why a git walk was built | **INFERRED** | no written record found |
| The PR-time check is about 40 lines | **INFERRED** | an estimate from `sim.py`'s rule (D), which is 6 lines of logic |
| More review rounds on (a) would keep finding topologies | **INFERRED** | from three rounds, three topologies, and git's space of histories; not provable |
