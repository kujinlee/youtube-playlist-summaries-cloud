Reviewed head: fa54e005358539b670803e97a24d0d34a46cf46a

# PR #497 (backlog #497, goal-tree recency, numbered goal blocks) — adversarial review round 1, CLAUDE half

Mandate: REFUTE. Every finding below was reproduced with a constructed input, unless it is labelled UNVERIFIED.
The scratch harness is `probe.py` and `real.py`, both in this directory. They import `scripts/goal-tree.py` from the
worktree and call its pure functions on synthetic `src` dicts, and on a COPY of the main checkout's log
(`log-copy.jsonl`, 114 snapshots). `--snapshot` was never run.

## Findings, ranked

### 1. HIGH: in-flight work on a thread that has LANDED is folded on the page and missing from --print entirely

- **Where:** `scripts/goal-tree.py:303-322` (`bucket`), `scripts/goal-tree.py:406` (`derive_thread`), and the
  `inflight_loose` computation in `derive`.
- **Input:** goal-threads `- fix · backlog #10, PR #20 · …`, with PR #20 merged 2026-10-20, and `- fix · PR #50`
  merged 2026-10-01, in a goal with nothing else current. Ledger: routine entries
  `{"id":"fu-10","what":"follow-up fix for backlog #10 r2 fold"}`, `{"id":"re-22","what":"reopening PR #22 as a new PR"}`
  (PR #22 closed) and `{"id":"fu-50","what":"backlog #50 hotfix in flight"}`. Drawn at `2026-11-04 12:00`
  (`probe.py A`).
- **Observed:**
  - In --print, all three ledger entries appear NOWHERE. Their leaves are replaced by `… 2 older merged or closed
    (collapsed on the page)` and `… 1 older merged`.
  - `inflight_loose == []`.
  - On the page each entry sits inside a closed `<details>`. For GOAL 2 that is two levels deep, because the whole
    goal folds as "nothing current".
- **Why:** `bucket` returns on `state == "merged"` / `state in LANDED` before it looks at any ledger entry.
  `derive_thread` only lifts `next/notfound/superseded/withdrawn` to `inflight` (line 406), so merged or closed with
  `flying` stays landed and folds.
  - The PR handled exactly this shape for PARKED entries: they get `parked_loose` with `names only LANDED threads`.
    The in-flight case got no such handling.
  - Before this PR nothing folded, so `· in flight: …` was always visible. This is a regression.
- **Expected:** mandate item 1, and backlog #497's own FAILS IF ("a now … leaf is inside a closed `<details>`"). Work
  the ledger says is in flight is current, and it must be drawn open, never reduced to a count line.
- **Realistic:** yes. A follow-up or reopened fix names the old backlog/PR number. The number-only matching
  (backlog #489) also attaches `PR #376`-style mentions to a landed `backlog #376` thread. The live log already shows
  this for a parked entry (`park-376` → `fix · backlog #376, PR #422`).
- **Fix:** store `inflight=bool(flying)` beside `parked` and make `bucket` return `now` for it before the landed
  checks. Alternatively, mirror `parked_loose`: list such entries in `inflight_loose` with
  `names only LANDED threads: …`. Add a case: routine entry plus older merged thread, asserting the entry text is in
  `tree_lines` and in a non-fold block.

### 2. MEDIUM: "queued (planned)" is empty on the real tree, and declared-but-unstarted `fix` threads fold as "nothing plans it"

- **Where:** `scripts/goal-tree.py:303-322` (`bucket`: `blocked` → queued, `next` → later) and
  `scripts/goal-tree.py:929` (the fold summary text).
- **Input:** the newest real snapshot (log copy), drawn at `2026-11-04 12:00` (`real.py`).
- **Observed:** the bucket counts are `older 51, recent 14, later 9, now 2`, with **queued 0** and **parked-in-goal 0**.
  - Among the 9 `later` threads is `fix · backlog #481 · REPLACES backlog #405 for the same goal …` under
    `dev-speed-first`. That is a fix declared for the goal, so it is planned by definition. It is folded under
    `later (N) — not started, and nothing plans it`.
- **Why:** `queued` requires a hand-written `· waits on …` field, and no thread in `docs/goal-threads.md` uses one
  for that purpose. As a result the owner's "show … queued (planned) tasks for each goal" ships as a category that is
  always empty in practice. Meanwhile the work that IS planned (declared under a goal) is hidden, under a summary
  whose wording ("nothing plans it") is false for it.
- **Fix (a hypothesis):** an unstarted `fix`/`blocker` thread is `queued` (the declaration under the goal is the
  plan), and an unstarted `bookkeeping`/`side` thread is `later`. At minimum, reword the summary to "not started"
  without the false "nothing plans it". If the narrow definition is intended, this is a decision for the owner, not
  a mechanical choice.

### 3. LOW: `PARKED` is matched case-sensitively and without negation

- **Where:** `scripts/goal-tree.py:170`.
- **Input:** a routine entry `parked: backlog #60 until the owner walks the spec` (`probe.py E`).
- **Observed:** thread `side · backlog #60` becomes ⏳ `inflight` / `now`, and is never labelled parked.
- **Inverse case (UNVERIFIED, read from the regex only):** `PR #21 is NOT PARKED any more` would match and park a
  live thread.
- **Impact:** both cases stay visible, so this is a mislabel, not a drop.
- **Fix:** rely on the declared `kind` only. If the text is kept, document it as capitals-only in the grammar.

### 4. LOW: goal numbers are stable across folding, but not across an edit of the threads file or across the timeline

- **Where:** `scripts/goal-tree.py:962`.
- **Input:** insert `## GOAL inserted` between `alpha` and `beta` (`probe.py C`).
- **Observed:** `beta` goes from GOAL 2 to GOAL 3.
  - Past snapshots in the timeline are numbered by their own goal list, so one goal can carry different numbers on
    the same page (the "Now" section against an older timeline entry).
  - The `docs/goal-threads.md` grammar does not say goals are append-only.
  - `#goal-N` anchors shift with the numbers.
- **Fix:** state "new goals are appended; never insert or reorder" in the grammar and enforce it (the log can check
  that the previous snapshot's slug order is a prefix). Alternatively, accept the shift and say so in the docstring.

### 5. LOW: the fold controls the owner asked for are below WCAG AA contrast in the light theme

- **Where:** `scripts/goal-tree.py:1272` (`details.fold summary` uses `--ink-faint`); `.goal-counts` uses the same
  colour.
- **Measured:** computed in Chromium 156 on the full built page (`full-page.html`), against the card background.

| Element | Light | Dark |
|---|---|---|
| Goal heading (`--accent`) | 5.82:1 | 6.63:1 |
| Fold summaries, `.goal-counts`, `.goal-q time` | **3.43:1** at 12-14 px | 4.45:1 |

- **Result:** the heading passes in both themes (the builder had checked only dark; light is fine too). The fold
  summaries are below 4.5:1, failing in light and marginal in dark. The `older (N)` expand control is exactly what
  the owner has to find and click.
- **Fix:** use `--ink-soft` for the fold summary and counts.

### 6. LOW: a PR closed minutes ago folds as `older`

- **Where:** `scripts/goal-tree.py:315`.
- **Input:** `fix · PR #22` with `gh` state CLOSED (`probe.py A`).
- **Observed:** it folds as older at any age. "Recent past" is meant to stay open, and a closure is no less recent
  than a merge. No close time is read, so this is a known bound rather than a bug.
- **Fix:** read `closedAt` the same way as `mergedAt` and age it, or state the bound in `bucket`'s docstring.

## Checked and NOT refuted

- **`--self-test`:** `246/246 self-test cases passed`.
- **HTML validity (mandate 6):**
  - The full built page from the real log copy (`real.py` → `real-page.html`) parsed with a stack-checking
    `html.parser` pass: no mismatched or unclosed tags, no `<p>`/`<summary>` containing block content, and no
    duplicate ids. `goal-1` … `goal-6` exist on the live tree only.
  - Same result on the synthetic page (`probe.py B`). `<h3>` inside `<summary>` is permitted (heading content).
- **Fragment links into folds:** 101 of the 135 `t-*` thread anchors in the live tree sit inside closed `<details>`.
  In Chromium 156, navigating to `#t-pr-411` auto-opened its `<details>` and scrolled to it. **Safari and Firefox are
  UNVERIFIED.**
- **Snapshot log (mandate 5):** the same sources derived at `2026-11-04 12:00` and `2026-11-06 12:00` give an equal
  `fingerprint`, and every bucket moved to older. So no snapshot is logged when only time passes. `merged_at` and
  `parked` are stored. A state change also changes `detail`, so it is logged.
  - Expected one-off: the first snapshot after the merge will log, because every merged detail string gained a time.
- **Merge times (mandate 2):**
  - The real newest snapshot has 0 `time unread` leaves.
  - Both readers use the machine's local zone: git `format-local`, and `astimezone(None)`.
  - An unreadable age makes a leaf recent, never folded.
  - A multi-PR thread with one unread time is unread as a whole.
- **--print vs page (mandate 3):** both come from `tree_blocks` at the same `at` (`main` passes `now` to both), so
  fold counts are equal by construction. The whole-goal `counts` derive from the same fold lists.
- **NEEDS YOU (mandate 7):** `needs_lines` and `needs_html` give identical output between `origin/master`'s
  `goal-tree.py` and head on the real newest snapshot.

## Scope note (not reviewed: outside the reviewed head)

The owner's 01:07 request (refresh on click, not frequently) has nothing in head `fa54e005`.

- The worktree carries UNCOMMITTED edits to `scripts/explainer-serve.py`, `scripts/mutations/explainer-serve.json`
  and `scripts/check-plan-code.py`: a 60 s `REGEN_TIMEOUTS` bound for the goal-tree regenerate. I did not review them.
- That change bounds how long a click waits. It does not change how often the page refreshes.
- From the code, the page has no automatic reload: the only `location.reload` is behind the Refresh button
  (`scripts/page_chrome.py:1027`). Rebuilds happen on `gh pr merge` and on edits of the threads file
  (`scripts/regen-pages.py` `pages_for`). So 01:07 may already have been met before this PR. UNVERIFIED against the
  owner's intent.

## What I ran

- `python3 scripts/goal-tree.py --self-test`
- `probe.py A` to `probe.py E` (synthetic sources)
- `real.py`, over a copy of the main checkout's `goal-tree-log.jsonl`, writing `real-page.html` and `full-page.html`
  through `render_page` / `write_page`
- An `origin/master` scripts tree extracted to `mscripts/` for the NEEDS YOU comparison
- Playwright (Chromium 156) over a local `http.server` for the fragment navigation and computed-contrast checks

VERDICT: NOT CONVERGED
