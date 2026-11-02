# retire-work-lines r1 — Claude half (backlog #389, HEAD f8e974a4)

Mandate: test #389's own FAILS-IF, item by item, trying to refute it. Read-only worktree `pin-389`
(detached at f8e974a4). The main checkout (`~/explainers` → its `docs/explainers`) is at `40291231`,
which is origin/master before this branch.

## What I ran

- `grep -rnI -E 'work-lines|work_lines'` over docs/, .claude/, .agents/, scripts/, CONTEXT.md,
  README*, CLAUDE.md, AGENTS.md, plus `grep -i 'work.lines'` and `'work line'` for spaced or
  case-variant wording. Also the memory dir and `~/.claude/CLAUDE.md`, which had zero hits.
- `python3 scripts/goal-tree.py --page --out <scratch>/r389/gt.html` (rendered from the existing log.
  I left out `--snapshot` so the main checkout's log was not written), then scanned the text and hrefs.
- Diffed `~/explainers/work-lines.html` (master's generator, 16:00 today) against
  `docs/explainers/work-lines-archive.html`.
- Called `explainer-serve.index_html(~/explainers)` and `latest_target` in-process.
- `goal-tree.py --self-test` gave 162/162. `gen-work-lines.py` with no arguments gave rc=2 and named
  the archive.

## Hits

Grouped where one file has many hits of the same class. The `docs/reviews/**` and
`docs/reviews/verdicts/**` hits (≈75 files) are all dated review records or verdicts of the
`work-lines*` / `banner-thread-armed` / `trigger3-lost-bet` rounds. They are immutable history, so I
class them ARCHIVAL and do not list them one by one.

| file:line | class | text |
|---|---|---|
| ~/explainers/work-lines.html (untracked, main checkout docs/explainers/) | **CURRENT** | `<title>Work lines — how we got here</title>`, Refresh button `data-page="work-lines"`, generated 2026-10-28 16:00. Listed on `/` (see F1) |
| scripts/explainer-serve.py:35-36 | ARCHIVAL | `/work-lines-archive ← FROZEN: the retired work-lines page (backlog #389); /work-lines redirects here` |
| scripts/explainer-serve.py:167-173 | CODE | `RETIRED_PAGES = {"/work-lines": "/work-lines-archive", "/work-lines.html": ...}` |
| scripts/explainer-serve.py:1537-1543, 2432 | CODE | self-test cases for the redirect / not-regenerable |
| scripts/goal-tree.py:13, 56-57, 100-101, 497-530, 606, 863-864, 1386-1430 | ARCHIVAL / CODE | "now retired and FROZEN: the work-lines archive"; `WORK_LINES_ARCHIVE`; reads gen-work-lines as a library |
| scripts/gen-work-lines.py:4-11, 66, 369, 374 | ARCHIVAL | `RETIRED: exits 2, naming the archive` |
| scripts/gen-work-lines.py:71, 511 | CODE | provenance of reconstructed links (reader logic) |
| scripts/begin-plan.py:188-336, 373, 583, 703, 1015, 1324, 1932, 2146 | CODE | imports the plan reader; `work-lines-page` is an old plan slug |
| scripts/begin-plan.py:2185 | ARCHIVAL | "(The work-lines page that was rebuilt here … retired, backlog #389.)" |
| scripts/begin-plan.py:321 | CODE, stale present tense | "the page answers 'what did I never walk back to' across every line" |
| scripts/check-banner-armed.py:122-127 | CODE, half-updated | "(… the work-lines page that first showed it retired …)" then "never reached that page … one the page knows" |
| scripts/check-banner-armed.py:162, 172 | CODE, stale present tense | "`gen-work-lines.plan_dirs` — the page's own reader, so the two cannot disagree"; "the page then shows the new work under the old plan" |
| scripts/check-banner-armed.py:574-578 | CODE, stale present tense | `# ── THE FOURTH CLASS: a THREAD the work-lines page does not know` … "never reaches that page" |
| scripts/check-banner-armed.py:1030-1033 | CODE, stale present tense | `"""The threads the work-lines page shows: …` "the page's own reader, so this check and the page cannot disagree" |
| scripts/check-banner-armed.py:748-749 (emitted warning) | fine | "The goal tree's plan list shows a thread only when its plan file exists". Updated correctly |
| scripts/check-banner-armed.py:611, 1696, 3055-3065 | CODE | `work-lines-page` as a fixture slug |
| scripts/check-plan-progress.py:344 | CODE, stale | `# ── the work line: what a FINISHED plan leaves behind, and the page it feeds` |
| scripts/check-plan-progress.py:440, 563-564, 930-931, 992 | ARCHIVAL / CODE | "(retired with the page, backlog #389 …)" |
| scripts/backfill-work-lines.py (13) | CODE | the backfill tool, a reader of the plan files |
| scripts/check-decision-scheme.py (10), docs/reviews/decision-scheme/* | CODE / ARCHIVAL | historical plan slugs `work-lines-always-on`, `work-lines-backfill` |
| scripts/check-selftest-counts.py:229-230, check-fixture-variation.py:154-1186, check-plan-code.py (17) | CODE | suite registries / dated comments |
| .github/workflows/ci.yml:797-800 | ARCHIVAL | "The plan-file reader (the work-lines page it drew retired into the goal tree, backlog #389)" |
| .agents/skills/shared/explainer-delivery.md:147 | fine | list of tabular producers now says "goal tree" |
| docs/backlog.md:345, 366, 371 | ARCHIVAL | rows #363 / #384 / #389, dated |
| docs/dashboard-entries.md:16925-17233, 17732, 18186-18229 | ARCHIVAL | dated entries. 18213-18229 is this branch's entry: "The work-lines page is retired …" |
| docs/process-checklists.md:96 | ARCHIVAL | "On PR #384 (`work-lines`), all four review folds …" |
| docs/explainers/2026-10-2{3,7}-*.html (+ fragments) | ARCHIVAL | dated explainers, snapshots of their day |
| docs/features.md, CONTEXT.md, README, CLAUDE.md, .claude/commands, .claude/settings.json, .claude/skills | none | zero hits |
| rendered goal-tree page, timeline intro | ARCHIVAL | "Before this page, the plan history was drawn by the work-lines page, now retired and FROZEN: the work-lines archive (backlog #389)". The only work-lines href on the page is `/work-lines-archive` |
| rendered goal-tree page, PLANS NOT TICKED CLOSED | data | two plan objectives quote "…[a plan objective — redacted pending backlog #194]". These are the owner's own words stored in plan files, not a presentation |

## FAILS-IF 1: does a generated page still present work-lines as current?

There are no CURRENT hits in tracked sources, skills, commands, hooks or the feature map. The
rendered goal tree presents it only as retired. One CURRENT hit survives outside git, and the
redirect does not cover it (F1).

## FAILS-IF 2: is its history reachable from the goal-tree page?

**Holds.** The goal-tree page has exactly one archive href, `/work-lines-archive`. It sits in the
timeline intro, below the tree and the 29-plan list, so it is reachable but low on the page.

The archive is the real last output. Diffing it against `~/explainers/work-lines.html`, which master's
generator wrote at 16:00 today, the only differences are:
- the title, which gains `ARCHIVED 2026-10-28`;
- one added ARCHIVED banner;
- the timestamp, 16:00 → 16:04;
- the removed Refresh button.

Every line and plan body is the same. The source history is named in the banner: "rendered by
`scripts/gen-work-lines.py` at commit 40291231 from 138 plan files across every checkout's
`.claude/plans/`". I counted the `.claude/plans/*.md` files across `git worktree list` and got
**138**, which matches. The banner also states that the plan files are not archived (backlog #194).

Bound: I did not re-run master's generator in a separate copy. Instead I used master's own 16:00
output from today as the comparison. It is the same generator, but the run is 4 minutes earlier.

## FAILS-IF 3: do two pages again answer *which threads are live*?

| Page / block | Answers "which threads are live"? |
|---|---|
| goal tree (`/goal-tree`) | **yes**: the declared threads with derived PR / in-flight state, plus plans not ticked closed |
| dashboard (`/dashboard`) | **partly**. "What needs you" lists every open PR as a flat list (`gen-dashboard.py:994-1001`, `open_prs()`), with no thread structure. This predates the branch and was not reintroduced by it (F3) |
| session-state block (`scripts/session-state.py`, SessionStart hook) | yes, but it is text for the AGENT after a compaction, not a page. It reads the same `inflight.jsonl` and `gh pr list` the goal tree reads: one source, two readers. Not a duplicate page |
| brief (`/brief` skill) | a one-off page per request about one body of work. Not a standing answer |
| goals (`/goals`) | no: goals, milestones and ADR status keyed by anchor, not threads |
| work-lines | retired; `/work-lines` gives a 302 to the archive (self-test case at `explainer-serve.py:2432`) |

The work-lines vs goal-tree pair, which is the one the owner complained about, is gone. What remains
is the dashboard's flat open-PR list (F3).

## Findings

### F1: Major. The retired page is still on disk, listed on `/` with today's date, and the merge itself will rebuild it

Evidence:
- `~/explainers/work-lines.html` exists. It is untracked in the main checkout's `docs/explainers/`
  (it appears in the session's git status as `?? docs/explainers/work-lines.html`).
- Its title is "Work lines — how we got here", it has a live Refresh button, and it was generated at
  2026-10-28 16:00.
- `index_html(~/explainers)` today returns
  `<li><a href="/work-lines.html">work-lines.html</a><span> · 2026-10-28 16:00</span></li>`. That is
  the "All pages" list, which the dashboard links under *Elsewhere*. `explainers()`
  (`explainer-serve.py:757`) does not filter `RETIRED_PAGES`. The click does redirect to the archive,
  but the list itself presents work-lines as a current page, and it will show beside
  `work-lines-archive.html` once the archive lands.
- Opened from disk (`open ~/explainers/work-lines.html`, or any `file://` bookmark), the stale page
  is shown with no ARCHIVED banner.
- **The merge refreshes it.** `.claude/settings.json:63/113/126` runs
  `$CLAUDE_PROJECT_DIR/.claude/hooks/regen-pages.sh`. That hook resolves `REPO` from its own location,
  which is the main checkout. The main checkout is at `40291231`, where
  `explainer-serve.REGENERABLE["work-lines"] = "gen-work-lines.py"` (main checkout
  `scripts/explainer-serve.py:129`). So the `gh pr merge` that lands this branch, and every later
  merge or Stop hook (`check-plan-progress.refresh_work_lines` on master) until the main checkout is
  pulled, rewrites `work-lines.html` with a fresh timestamp.
- The code comment at `explainer-serve.py:169-172` acknowledges the stale copy and relies on the
  redirect alone. The row's DONE note says "no generated page … presents work-lines as current", and
  that claim is about the served URL, not about the page.

Fix (cheap, in code):
1. Make `explainers()` (and therefore `/` and `/latest`) skip any file whose `/<name>` is a
   `RETIRED_PAGES` key.
2. Delete the stale file. Options: a one-line removal in `regen-pages.py` for retired names, or a
   stated manual `rm` in the merge step, made AFTER the main checkout pulls.
3. Add a case: `index_html` over a root that contains `work-lines.html` does not list it.

### F2: Minor. Present-tense comments still describe a page that "shows" threads

Evidence:
- `check-banner-armed.py:125-127`, `:162`, `:172`, `:574-578` and `:1030-1033` ("The threads the
  work-lines page shows", "the page's own reader, so this check and the page cannot disagree").
- `check-plan-progress.py:344` ("the page it feeds").
- `begin-plan.py:321` ("the page answers …").

The emitted warning text was updated (`:748`), so nothing reaches the owner. But the docstrings tell
the next agent that a live page reads these plan files and must agree with this check. That page no
longer exists; the goal tree is now the reader.

Fix: change "the work-lines page" / "the page" to "the goal tree's plan list" at those sites.

### F3: Minor. The dashboard still carries a flat in-flight list

Evidence: `gen-dashboard.py:994-1001` puts every open PR (`open_prs()`) under "What needs you". The
goal tree shows the same PRs placed in their threads, and has its own NEEDS YOU. This is not the pair
#389 retired, and it was already there before the branch. But it is a second, structureless answer
to "what is in flight". Under the 2026-10-25 merge-when-ready rule, an open PR is not by itself an
owner decision.

Fix: no change on this branch. Record it under backlog #384's roles review, either as the dashboard
dropping the open-PR list in favour of a link to `/goal-tree`, or as a stated reason to keep both.

### F4: Minor. `docs/features.md` is in the row's Files column but untouched, and the feature map has no goal-tree node

Evidence:
- `git diff --stat origin/master...HEAD` shows no `docs/features.md`.
- The feature map's `status-pages` node (`features.md:135-139`) is generic. Neither page appears
  anywhere in the map, so nothing there is stale.
- This does not trip FAILS-IF 1. But the row named the file, and "where do I find the goal tree" has
  no feature-map answer.

Fix: either add a `#### goal-tree` child under `status-pages`, or drop `docs/features.md` from the
row's Files column with a note.

## Count

Blocking 0 · Major 1 · Minor 3

VERDICT: NOT CONVERGED
