# work-lines-backfill — round 5 — Claude half

Range reviewed: `15e8861c..2c0962ae` (the round-4 Codex fold), read against the whole change `cd7134f8..2c0962ae`.

**Deciding question: is it safe to `--write` the 31 markers into the owner's real plans?** Yes.
All 31 match the real transcripts. A `--write` trial on a copy wrote exactly the 31 expected
two-line markers and nothing else. A second run wrote 0, and the two live-marked plans came out
byte-identical. One Medium is open: a hole in the END rule. It is measured three times in the
corpus and changes **none** of the 31 rows, so it does not block the write.

## What was executed (not recalled)

| Check | Result |
|---|---|
| Dry run, real plans, `--root` = main checkout | `totals: keep 24, keep-banner 7, no-marker 92, untouched 2 (of 125 plans)`. All 31 rows equal `bf/links-r7.txt` |
| `--self-test` | `256/256 self-test cases passed` |
| `--ground-truth` | `OK — the replay reproduces work-lines-backfill <- banner-thread-armed` / `checkpoints: agree 124, disagree 0 (resolved 0), resync from unknown 329` |
| Copy `.claude/plans` (`cp -Rp`) + `last-plan` → dry run on the copy | the table is identical to the real run (`diff` empty). Note: on the copy, `st_birthtime` equals the mtime, so it is later than the real file's. No row in either run turns on the birth check |
| `--write` on the copy | `wrote 31 plan file(s)`; 31 files changed; no `.backfill-tmp` left behind |
| Every written file vs its expected text | each of the 31 is exactly `title, "", "<!-- parent: P -->", "<!-- parent-source: K S8 TS -->", rest` with P/K/S8/TS taken from `links-r7.txt`: `checked 31 mismatches 0`; mtime kept on all 31 |
| `--write` a second time | `wrote 0`; tree sha-identical to after the first write; the 31 now read `untouched: … (reconstructed)` and the 2 live ones `(live)` |
| Live-marked plans (`work-lines-backfill`, `work-lines-always-on`) | `diff` against the real files is empty |
| Real `.claude/plans` before vs after all of the above | sha list identical (`REAL-UNTOUCHED`) |
| `gen-work-lines.py` on the written copy (staged tree, `--out` to scratch) | renders: `125 plan(s), 114 line(s), 26 still owing` |
| All 101 mutations in `scripts/mutations/backfill-work-lines.json`, own runner (staged copy of `scripts/`, `HOME` redirected, control green first) | `{'killed-as-named': 101, 'killed-other': 0, 'survived': 0, 'unbound': 0}`. All 12 new or renamed entries are killed by the case each `expect` names |

Independent evidence for the 31 rows comes from my own extractor over all 520 jsonl files. It
pulls every Bash call that mentions `begin-plan`, `executing-plan` or `check-plan-progress`,
with its result, plus every Stop-hook Clearing attachment and `stop_hook_summary`. It is not
the tool's parser.

## Findings

### M1 — Medium — a background task that outlives its session gets its window cut at the session's end

**Location:** `read_transcripts`, `terminal` keyed `(session, task)` plus `end_of_session = session_end.get(ev.session)`.

The fold's rule is that a background command stays UNKNOWN until its own END, "never too short".
The END is only searched for in the **launching** session. But background tasks survive `/clear`
and resume, which start a **new** session id. Measured: each session id here sits in exactly one
file, and one file holds exactly one session. So the task's notice lands in the next session,
the `(session, task)` lookup misses it, and the window closes at the launching session's last
event. That is before the task actually ended. Probe of the tool's own `read_transcripts` (all
three are `opaque`):

```
2026-09-23T19:14:14Z 47586cf2 bciuf8g3a until 19:28:09  -- real END 19:29:53 in 3cd75aad
2026-10-01T00:32:16Z 9421c78a bts804s31 until 00:41:11  -- real END 00:52:51 in 3ec470a2
2026-10-06T03:48:23Z 43d5c426 bah529gd7 until 03:51:26  -- real END 03:57:12 in a7b78d02
```

These are 3 of the 4 background commands that got no END, out of 475. A shell `&` job carries
the same exposure.

**Effect on the 31:** none. No first arm and no checkpoint falls in any of the three gaps
(19:28–19:30 on 09-23, 00:41–00:53 on 10-01, 03:51–03:57 on 10-06). The two events found in the
10-01 gap are a `git status` and an inline `ast` read; neither is a checkpoint. So this is a
false "never too short", not a wrong marker.

**Fix:** also match terminal notices by `<tool-use-id>` **across sessions**. That id is globally
unique, and measured, **796 of 796** queue-operation notices for a known background launch name
the launching Bash call's own tool-use id (0 mismatches, 0 without one). Keep `(session, task)`
as the fallback for a notice that names no tool-use id. Separately, a command with no END at all
should stay open past its session's end when a later session continues in the same process. The
simplest sound version: open until the end of the transcript set. Add a mutation that cuts the
lookup back to same-session only.

### L1 — Low — the write is one-shot and not backed up; the owner should know what the 21 `-` markers assert

- `.claude/plans/` is gitignored (`.gitignore:96`). `--write` uses `os.replace`, so each file gets
  a new inode (and a new `st_birthtime`). A plan that has a marker is never touched by a later
  run (`untouched: already has a parent marker (reconstructed)`). So a mistake is not recoverable
  from git, and a later, better backfill cannot revise these 31. **Run
  `cp -Rp .claude/plans <backup>` immediately before the real `--write`.** I checked that nothing
  else in `scripts/` reads `st_birthtime` (grep: none).
- 21 of the 31 are `parent: -`, and **every one** of those 21 is preceded by a clear: a
  `--finish` (often in the same Bash command as the arm) or a Stop-hook Clearing. This is the
  owner's stated rule ("nothing armed → `-`", the documented divergence from the post-10-22 live
  code). It is replayed faithfully, so all 21 are counted as confirmed below. But the page will
  say each of these 21 plans STARTED a line, including chains like `--finish fold-r3-codex &&
  begin-plan fold-r3-claude`. These are labelled `transcript`, so they are distinguishable. This
  is not a defect. It is flagged so the owner is not surprised by what the page asserts.

### L2 — nit — operator precedence in the session-end update

`{e.session for e in mine} | {_session_of(last_line)} - {""}` parses as `A | (B - {""})`, so an
empty session id from `mine` would be kept. This is harmless today: the probe counts **0**
events with an empty session. Write it as `(A | B) - {""}`.

### nit — `--explain` prints a cleared-by-tick plan as `1/1`

`Armed(rel, 1, 1, 1, False)` (`:1139`) makes `--explain` show
`qualify-bare-refs.md 1/1` for a 6/6 plan. This is cosmetic and does not affect the replay.

### Mandate items with no finding

- **(a) wrong-record attribution:** a reused id cannot end a later task (`t > ev.ts`). A notice
  naming another tool call is rejected, and the real data has 0 such mismatches. A quoted notice
  is rejected because the record must *start* with the tag. A failed TaskStop ends nothing.
  Real statuses are only `completed` (3856), `failed` (298), `killed` (1) and `running` (1), and
  `running` is correctly non-terminal. A queue-operation `remove` record also carries the notice,
  but it is always later than the `enqueue`, so "first" is unaffected. A stop record from
  another session cannot end a task, because terminal records are keyed by session. That is
  safe, and it is the other face of M1.
- **(b) hook evidence:** 0 subagent files carry a `stop_hook_summary` or a `hookEvent: Stop`.
  Every one of the 43 sessions with a `stop_hook_summary` has the plan guard ("Checking whether
  a plan is still mid-execution…") in **every** summary, so no session is credited with a Stop
  hook that lacked the plan guard. Every clear that decides one of the 31 is backed by the hook's
  own `Clearing` message, not inferred from a bare `end_turn`. For the 4 found in
  `hook_non_blocking_error` attachments, the message is still in `content` and still names the
  plan.
- **Other transcript directories:** 18 worktree-launched project dirs exist under
  `~/.claude/projects/*youtube*`, and the tool does not read them. I scanned every tool call in
  them. None references the main checkout's `begin-plan`, `executing-plan` or `.claude/plans`
  (15 hits, all Reads/Greps of worktree copies). So this is an unread population with a measured
  zero, not a hole today.
- **(d) mutations:** see the table above. 101/101 are killed via their named case. The names
  match what the edits do. For example, `an END before START ends the task` removes `t > ev.ts`
  and dies on the reused-id case, which is exactly an earlier END.

## The 31 rows

"Before the arm" is the transition, read from the raw transcripts, that sets the state the arm saw.

| # | plan | written | before the arm (independent evidence) | verdict |
|---|---|---|---|---|
| 1 | afk-two-folds-and-r18 | `-` transcript ee774183 | same command: `--finish` → `cleared .claude/executing-plan`, then arm. The prior `cd` to wt-staleplan was reset (`Shell cwd was reset`) | confirmed |
| 2 | approved-329-328-173 | qualify-bare-refs, banner 55e544f6 | Stop `Clearing` qualify-bare-refs (6/6) 04:41:36; no plan event until arm 05:13:37; banner 05:13:42 `⤳ SWITCHED from qualify-bare-refs (6/6 done…)` | confirmed |
| 3 | arch-review-marketplace | `-` | same command `--resume && tick×2 && --finish && arm`; the arm's output proves the chain ran | confirmed |
| 4 | backfill-177-spec-plan | `-` | 03:36:35 output `cleared .claude/executing-plan` (backlog-117-r3); arm 03:46:06 | confirmed |
| 5 | backlog-117-r3 | `-` | same command `--finish` → `cleared`, then arm (backlog-117-substrate) | confirmed |
| 6 | candidate-1-page-cites | `-` | 12:48:40 `--finish` → `cleared` (arch-review-marketplace, other session); `cat` at 15:23:30 → No such file; arm 15:23:46 | confirmed |
| 7 | corpus-pass-295 | `-` | Stop `Clearing` candidate-1-page-cites 6/6 17:00:46; arm 17:26:15 | confirmed |
| 8 | decision-log-model-r1-fold | `-` | Stop `Clearing` decision-log-model-redesign 5/5 22:55:09; arm 22:55:46; no banner | confirmed |
| 9 | decision-log-model-r2 | decision-log-model-r1-fold, banner | Stop `Clearing` r1-fold 7/7 23:07:56; banner 23:18:00 names it | confirmed |
| 10 | decision-log-model-redesign | `-` | Stop `Clearing` fix-322-unrunnable-gate 4/4 22:15:38 (e87cc09f); arm 22:28:55 | confirmed |
| 11 | declare-all-statuses | goals-page-status, banner | Stop `Clearing` goals-page-status 4/4 02:32:46 (in a `hook_non_blocking_error`); banner 09:58:30 | confirmed |
| 12 | declared-skip-r8 | declared-skip-r7, transcript | tick 22:58:34 `5/5 … will allow the turn to end`; no turn end or Stop in **any** session before arm 22:59:19 | confirmed |
| 13 | finish-364 | finish-365, banner | `--finish` 01:02:26 → `cleared`; arm's `--status` says `no plan is being executed`; banner 02:37:42 | confirmed |
| 14 | finish-365 | `-` | 23:06:01 `--resume; --finish` → `cleared` (d2-main-drivable 6/7); arm 23:06:10 | confirmed |
| 15 | fold-q3-q4-then-r3 | `-` | same command `--finish && arm` (marketplace-r3 0/6) | confirmed |
| 16 | fold-r3-claude | `-` | same command `--finish && arm` (fold-r3-codex 7/8 paused) | confirmed |
| 17 | fold-r3-codex | `-` | same command `--finish && arm` (fold-q3-q4 5/6) | confirmed |
| 18 | fold-r3-mediums | `-` | Stop `Clearing` fold-r3-claude 6/6 02:52:16, then `--finish && arm` 03:59:35 | confirmed |
| 19 | fold-r4-claude | `-` | same command `tick; --status; --finish && arm` (fold-r3-mediums 7/7) | confirmed |
| 20 | memory-index-budget-r2 | `-` | 04:44:52 output `cleared` (memory-index-budget-fold 3/3); arm 04:45:07 | confirmed |
| 21 | namespace-token-guard | `-` | Stop `Clearing` afk-r6-lows-r7-and-r18-verdict 5/5 05:33:53; no plan event until arm 12:44:27 | confirmed |
| 22 | phase6-fold-addendum | phase6-chrome-instrument, banner | Stop `Clearing` 6/6 19:45:33; banner 19:46:32 | confirmed |
| 23 | post-merge-360-reconcile | `-` | Stop `Clearing` ship-recall-fold 6/6 05:32:06; arm 12:06:39 | confirmed |
| 24 | rc-contract-reconciled | correct-arch-review-verdict, banner | Stop `Clearing` 5/5 20:34:25; banner 20:48:21, same turn as arm 20:48:26 | confirmed |
| 25 | round5-364 | finish-364, transcript | tick 05:03:36 6/6; no Stop in any session before arm 05:05:44. The `cleared` at 05:03:48 is `.claude/ci-watching`, not the sentinel. The background codex dispatch ended 05:05:30 (notice `completed`) | confirmed |
| 26 | ship-recall-fold | d1-ratchet-main-world, banner | Stop `Clearing` 5/5 03:00:50; banner 04:14:33 | confirmed |
| 27 | split-177-from-117 | `-` | 04:19:34 `--resume…` output `cleared .claude/executing-plan` (velocity-single-owner 4/4); arm 04:19:43 | confirmed |
| 28 | velocity-r3-and-pr | split-177-from-117, transcript | tick 04:28:37 5/5; no Stop or `end_turn` in any session before arm 04:29:15 | confirmed |
| 29 | velocity-single-owner | `-` | same command `--finish …;` then arm (backfill-177-spec-plan 3/4 paused) | confirmed |
| 30 | work-lines-page | `-` | 16:38:06 `--status` → `no plan is being executed`; arm 16:38:16. The edited working-tree begin-plan is the stated r3 I1 bound | confirmed |
| 31 | wrap-for-arch-review | `-` | Stop `Clearing` fold-recall-llm-r1 5/5 16:54:30; arm 17:31:52 | confirmed |

**confirmed 31 · doubtful 0 · wrong 0.** All 10 non-`-` parents are confirmed: 3 replayed
(nothing in between could have cleared the plan) and 7 banner links (the cleared plan is exactly
the one the banner says it left). The 21 `-` rows are correct under the owner's
"nothing armed → `-`" rule (see L1).

## Thrashing or prose floor?

**Neither, and this is not thrashing.** The END rule has now drawn findings in three consecutive
rounds: r3 Claude M1, r4 Codex 1–2, and this M1. But this round's finding is **not caused by
r4's fix**. Before r4, the window ended at the launching *file's* last timestamp, with `ended`
keyed per file. That had the same cross-session cut-off; r4 regrouped it by session id, and
session id is still one file. The hole predates the fold, and the fold's prose ("never too
short") made it checkable. The defect class did not shift. Coverage of what the transcripts
record is now the issue, and it changes zero output rows. That is a corpus-edge floor.
Recommendation: write now, and fix M1 as a follow-up before any re-run that could mark more
plans.

VERDICT: CONVERGED
