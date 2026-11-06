Reviewed head: 9131df49d1f7b947b8b2989290175c9a92a6947f

# needs-owner-settled — round 3, Claude half (adversarial)

Scope: `git diff origin/master...HEAD` (backlog #496, PR #528), with the focus on round 2's change
(`--topo-order --diff-merges=off`, all lines of history). Halves alternate; this round runs Claude only.

## What was run

- `python3 scripts/goal-tree.py --self-test` → **455/455 passed** (8.9 s).
- Real-git scenarios built in throwaway repositories under the session scratchpad (scripts `scen.py`, `scen2.py`,
  `squash.py`), each calling the module's own `git_head_when_marked` + `needs_from_backlog` over the real `git`.
- Real repository: the evil-merge census over every merge reachable from `--all` that touches the backlog (125), a
  corpus run over 343 backlog revisions reachable from `--all` since 2026-10-15 (each read at its own `rev`), and the
  cost of `backlog_commits` at HEAD and at origin/master.
- Six mutations of my own on a temp copy of `scripts/` (results under *Test strength*).

## Findings

### F1 — Medium — a squash-merged master hides a head rewritten INSIDE the marker's own PR, and r2 extends that blind spot to every branch that merges master; not stated as a bound
`scripts/goal-tree.py:726-736` (`backlog_commits` docstring) and `:777-782` (`head_when_marked`).

**Scenario (built, `squash.py` S1).** Branch B: `b1` introduces `OPEN ⟳ NEEDS-OWNER — pick A`; `b2` rewrites the
head to `SPEC MERGED ⟳ NEEDS-OWNER — pick A` (the decision recorded in the same PR). B is squash-merged to trunk as
`s1`; another PR edits a different row (`m2`); B merges trunk.
- On trunk: `s1` is a single introduction under `SPEC MERGED` → **no flag**. Inherent to squash-merging.
- On B: the merge's backlog equals trunk's, so `git log -- <path>` (default history simplification) follows ONLY the
  trunk parent and prunes B's line entirely; the walk is `m2, s1, base` → `s1` is the introduction → **no flag**.
  Under r1's `--first-parent`, B's own chain `b2, b1` was walked and the row WAS flagged. r2 trades that case for the
  one Codex found; the trade is defensible (B now agrees with master) but it is not written anywhere.

**Why it matters.** This repo merges to master by squash (origin/master: 1731 commits, the page reads the main
checkout), so "each change is attributed to the commit that made it, on whichever line it was made" (`:728-729`)
is false for every change that reached master: it is attributed to the squash. The measured "0 false, 0 NOT READ"
corpus could not have seen this shape, because it was read on squashed history. The miss is silent (no flag, no NOT
READ). `grep -i squash scripts/goal-tree.py` → only an unrelated backlog #497 comment.

**Fix.** One BOUND sentence in `backlog_commits`: on squash-merged history a marker introduced and its head rewritten
in the SAME PR is one introduction under the final head, so that rewrite is not seen (on master, or on any branch
that merged the squash).

### F2 — Low — the topological "newest introduction" can be a WITHDRAWN side-line introduction that is not an ancestor of today's text → false flag in this repo's merge direction
`scripts/goal-tree.py:777-782`, `:748`.

**Scenario (built, `squash.py` S2).** Feature B introduces `NEW ⟳ NEEDS-OWNER — pick A`. Master independently
introduced the same segment under `OLD` (`m1`) and then withdrew it (`m2`, which also edits another row, so the
merge is TREESAME to neither parent and both lines are walked). B merges master (master = 2nd parent). Topo order:
`merge, m2, m1, b1, base` — `git log --topo-order` emits the SECOND parent's line first — so `m1` (head `OLD`) wins
over `b1` (head `NEW`, which today's text actually descends from) → **flagged "head rewritten"**, falsely. Mirror
(`scen2.py`): the same pair with the parents swapped is not flagged; with a side-line introduction whose head equals
today's, the same mechanism gives a miss instead.

**Assessment.** Requires the identical segment text on both lines with different heads, one later withdrawn —
rare, and a false FLAG (never a hide) in the realistic direction. The docstring's bound ("ordered as git's walk puts
them") covers it in letter, but does not say the winner may be an introduction that today's text does not descend
from, nor which line wins (the merged-in one). One clause in the bound would make it honest. File, or fix the
sentence; no code change needed.

### F3 — Low — doc drift: the dashboard entry still says `--first-parent`; the docstring says "every line" while git's history simplification prunes lines
- `docs/dashboard-entries.md:18892` (the 2026-11-06 tech note): "`backlog_commits`, one `git log -p -U0
  --first-parent -- docs/backlog.md`". Round 2 removed `--first-parent`; the shipped entry describes the r1 design.
- `scripts/goal-tree.py:726` "ONE `git log -p` over the WHOLE history, every line of it", repeated in
  `docs/reviews/coordinator/needs-owner-settled-r2-coordinator.md:28` and HEAD's commit subject ("walks every line of
  history"). Not so: without `--full-history`, a merge TREESAME to one parent for `docs/backlog.md` follows only that
  parent (F1's scenario prunes B's whole line; `scen.py` prunes the withdrawn side line). The pruning is what makes
  the r2 R2-1 case pass when the feature never touched the backlog, so it is load-bearing, and it is undocumented.
- `docs/backlog.md:477` (#496's status) describes round 1's reader only; it does not mention merges, the evil-merge
  NOT READ or the renumber bound added in r2. Minor; fold with the F1 sentence.

### F4 — Low — test strength: the history-simplification behaviour and `rev` are unpinned
Mutations on a temp copy of `scripts/` (self-test after each):

| Mutation | Result |
|---|---|
| `backlog_commits` ignores `rev` (always `HEAD`) | **survives** 455/455 |
| add `--full-history` to the walk | **survives** 455/455 |
| `status_cell` arity `< 3` → `< 1` | survives (the `endswith("\|")` check catches the built case; near-equivalent) |
| negation `\s*$` → `\s+$` | survives (equivalent for real text) |
| skip the parent's status-cell check in `head_when_marked` | killed (454/455) |
| marker-in-head guard disabled | killed (453/455) |

- `rev` is the knob every corpus number in #496's status was measured through ("Over every backlog commit
  10-23..11-05 … 0 false, 0 NOT READ"); if it were ignored, each revision would have been read against HEAD's history
  and the measurement would be wrong while the suite stays green. One case calling `git_head_when_marked(root, run,
  rev=<older sha>)` on an existing fixture repo kills it.
- `--full-history` surviving means no case pins the pruning F3 documents. Add one only if the bound sentence relies
  on it; otherwise note it.

## Refutation attempts that held

- **Evil merges in real history: none.** Over all 125 merges reachable from `--all` that touch `docs/backlog.md`, no
  merge's row status holds a last-marker segment absent from the same row in BOTH parents (script `evil.py`, 27.9 s).
  The NOT READ for a merge-only marker cannot fire on any existing row.
- **Corpus, all branches.** 343 backlog revisions from `--all` since 10-15, each read at its own `rev`: 0 NOT READ,
  0 exceptions from clause 2 (4 `ShapeError`s are `gen-backlog-page.parse` refusing very old layouts, before #496's
  code). HEAD lists one row (backlog #496 itself, flagged by its cross-reference to backlog #86; clause 2 never ran).
- **Cost.** `backlog_commits` at HEAD: 302 commits, 1.8 s including the parse (7.8 MB of `-p -U0` output); at
  origin/master 1.83 s; `--all` raw log 4.6 s. One call per refresh, inside the 60 s bound; it grows linearly with
  backlog history — worth watching, not a finding.
- **Codex's R2-1 shape and its mirror** (master introduces + settles, merged into a feature that did or did not touch
  the backlog): flagged in both, because either the walk is pruned to master's line or master's line comes first.

## Verdict rationale

No Blocking or High finding. F1 is an unstated silent-miss bound on the checkout the page normally reads, and F3 is a
shipped description of a design that no longer exists; both are one-sentence doc fixes this round can make. F2 and F4
are Low.

VERDICT: NOT CONVERGED
