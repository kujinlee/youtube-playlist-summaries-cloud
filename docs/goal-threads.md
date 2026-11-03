# Goal threads — why each piece of work exists

The ONE hand-written input of the goal-tree page (backlog #363). It declares, for each goal the owner
set, which threads of work serve it and HOW. It declares nothing about state: whether a thread is
merged, open, red or in flight is DERIVED by `python3 scripts/goal-tree.py --snapshot` from
`git log origin/master`, `gh pr list` and `.claude/inflight.jsonl`, and logged to the main checkout's git-ignored
`.claude/goal-tree-log.jsonl`. The page is http://127.0.0.1:7391/goal-tree.

Grammar, read by `scripts/goal-tree.py` (`parse_threads`); a line that breaks it fails the snapshot loudly:

- `## GOAL <slug>` opens a goal. The slug is lowercase words joined by `-`, unique in this file.
- `> YYYY-MM-DD HH:MM "<the owner's words>"` is a request that set or widened the goal, in the owner's
  local time, quoted exactly. The first one is the goal; a goal has at least one.
- `- <relation> · <refs> · <what>` is a thread. `<relation>` is one of `fix` (serves the goal directly),
  `blocker` (stops a fix), `bookkeeping` (records findings, no new behaviour) or `side` (an aside).
  `<refs>` is one or more `backlog #N` / `PR #N`, joined by `, `. `<what>` is one line.
- A thread whose `backlog #N` rows ALL carry a fate MARKER in their Status cell prints ✖ superseded (→ backlog #M,
  only when the marker states `by backlog #M`) or ✖ withdrawn, in place of its PR's merged ✅ (backlog #484). A
  marker is `**SUPERSEDED` / `**WITHDRAWN`, bold and in capitals, leading the cell or led by a closing glyph; the
  word anywhere else is prose. An open PR or an in-flight entry still shows ⏳, and a `backlog #N` that is not a
  row of the backlog's Items table is CANNOT RUN.
- An optional last field `· waits on <what>` declares something a thread waits on that no tool can see
  (the owner's walkthrough, say). It is shown as DECLARED, never as a derived state.
- Inside a goal, every non-blank line is one of those. Prose belongs above the first goal.

## GOAL guard-harness-audit
> 2026-10-26 09:51 "in http://127.0.0.1:7391/features.html, guard-and-gate-harness section has very large number of open backlogs. when you have chance audit, scrub them then fix high priority ones."
> 2026-10-26 21:08 "keep working for guard-and-gate-harness backlog fixes along with other fixes necessary. try not to be blocked by non-critical decisions. merge when they become merge ready"
> 2026-10-27 03:28 "continue in AFK mode"
- fix · backlog #251, PR #411 · warn on each changed decision line no mutation anchor reaches
- fix · backlog #365, PR #412 · the hook guard refuses an unknown hook type and an empty exemption reason
- fix · backlog #369, PR #413 · the in-flight ledger refuses a change that would erase it
- fix · backlog #368, PR #414 · the hook guard refuses a command hook carrying args or shell
- fix · backlog #371, PR #415 · diff-coverage cannot report a clean zero through a lone CR or a textconv driver
- fix · backlog #364, PR #419 · every hook launches from the session's checkout, through one launcher
- fix · backlog #373, PR #420 · self-test fixtures that build a git repository cannot write into another one
- fix · backlog #382, PR #424 · every --self-test runs inside fixture_git.isolated()
- bookkeeping · PR #417 · the hook-launch architecture review; backlog #374 and backlog #375 filed
- bookkeeping · PR #420 · the fixture-guard architecture review; backlog #380 and backlog #382 filed
- bookkeeping · PR #422 · the em-guard architecture review; backlog #387 filed
- bookkeeping · PR #424 · the import-time-launch architecture review
- bookkeeping · PR #414 · backlog #377 filed
- bookkeeping · PR #415 · backlog #378 filed
- bookkeeping · PR #419 · backlog #379 filed
- bookkeeping · PR #421 · backlog #383 filed
- side · PR #418 · the skills explainer gets the text-style switcher; backlog #376 filed

## GOAL comprehensibility-suite
> 2026-10-27 11:30 "I am aiming to complete comprehensibility suite features. … what is current status of comprehensibility suite?"
> 2026-10-27 17:45 "we would need to define role and usages for these comprehensibility/status/explainer pages (goals, features, backlogs, dashboard, worklines, brief etc) … these pages are currently developed and produced in ad-hoc manner without overarching design"
> 2026-10-27 18:02 "Goal is to have tool for human (me) to understand what you (AI agent) [are doing]. … The tag vocabulary and tagging should serve the goal."
> 2026-10-28 03:41 "I wonder if this kind of goal tree is logged every so often (periodically in time or when meaningful changes are made) and I can see the page to learn how your work has been progressed, the page can be ideal dashboard."
- fix · backlog #381, PR #421 · a backlog row can carry several tags, read by one parser for both pages
- fix · backlog #376, PR #422 · a composed page with the Theme button gets the text-style switcher too
- fix · backlog #384 · the suite's overarching design · waits on the owner's walkthrough of the design ideas
- fix · backlog #363 · the goal tree as a logged, generated page
- bookkeeping · PR #423 · backlog #384, backlog #385 and backlog #386 filed; the design-ideas section
- side · PR #423 · the tag-vocabulary survey page and the suite inventory page
- fix · backlog #389, PR #434 · the work-lines page retires into the goal tree, its history archived (the owner's decision D2)

## GOAL compaction-guards
> 2026-10-28 04:03 "let's pause currently running works and finish the safety guards for auto compaction"
> 2026-10-28 04:12 "when auto-compaction-guard is fully built, continue the works and test the effectiveness of the guard"
- fix · backlog #361, PR #425 · a compaction leaves a snapshot of what is in flight and prints it back after

## GOAL dashboard-decisions
> 2026-10-28 09:46 "⏳ dashboard asks triage — VERIFIED 06:47, WAITS ON YOU (confirm 27 / 2 / 7) -> what is this?"
> 2026-10-28 10:23 "Meanwhile, 7 dashboard decisions are waiting for you. -> what is this?"
- fix · PR #427 · the dashboard clears 29 of its 36 waiting asks that later work had settled
- fix · PR #428 · the six unreadable asks are asked again in the form the dashboard reads
- fix · PR #429 · the owner's sixteen answers are applied to the backlog
- fix · PR #432 · backlog #337 records the owner's re-answer, a third outcome value
- fix · PR #430 · the memory-index budget warning runs when the index is edited (the owner's L3)
- fix · PR #431 · the memory index is trimmed and sixteen unbacked memory files are committed (the owner's L2)
- bookkeeping · PR #426 · backlog #388, backlog #389 and backlog #390 filed

## GOAL token-usage-first
> 2026-10-30 18:50 "For now, let's enhance token usage features first. As when we hit the limit, other optimization doesn't matter."
> 2026-10-31 04:38 "yes. measure it to confirm our assumptions"
> 2026-11-01 14:22 "4% saving is still big saving. You said you had blind spots so that you missed the duplicates issue. Try to find real impacts without blind spots."
> 2026-11-01 15:38 "it would be better to be a little aggresive earlier than later days to reset"
> 2026-11-02 02:20 "If you can make overall behavior control based on situation, it may make us smarter and more productive overall. But introduce fine-grained control after you gather evidences and periodically reassess if current control is optimal or not"
- fix · PR #453 · hook output trimmed and ledger entries carry an explicit kind, so each turn re-reads less context
- side · backlog #407, PR #454 · mutation runs skip compaction-state's real-deadline cases, so the CI sweep is faster
- fix · backlog #359, PR #455 · the mutation total is derived from the per-file pins, so open PRs stop colliding on one line
- fix · backlog #434, PR #457 · Claude review halves write verdicts; review rounds are capped at round 3
- fix · PR #458 · the always-loaded process docs are cut from 48 KB to 25 KB by moving history out, not rules
- bookkeeping · PR #464 · an optimization register records each saving with its risk, signal and revert path
- bookkeeping · PR #466 · the optimization register names each row's evidence source and decision rule
- fix · backlog #440, PR #463 · an auto compaction waits for a work boundary, up to 1.5 x the window
- fix · backlog #438, PR #465 · one command runs the per-PR gate set in one call
- side · backlog #402, PR #450 · the self-test count check runs only what a branch changed locally
- bookkeeping · PR #467 · the usage audit's findings filed as backlog #455 to backlog #461 and register rows
- fix · backlog #455, PR #468 · a subagent's foreground Bash call that can block past 270 s is refused
- fix · backlog #457, PR #469 · a subagent's read of more than 300 lines of a file in one call is refused
- bookkeeping · backlog #460, PR #470 · backlog #460 numbers, memory and goal-thread records, the memory-index trim
- fix · backlog #465, PR #471 · a subagent's ;/&& list of file reads is summed against the 300-line limit
- bookkeeping · PR #472 · work follows the budget situation (TIGHT / AMPLE), reassessed at each weekly reset
- bookkeeping · PR #473 · backlog #466 to backlog #468 filed: destructive commands measured, stale agents, AFK sleep stalls

## GOAL dev-speed-first
> 2026-11-02 09:05 "Our main thrust was comprehensibility suite and publishing them as public tool (as plugin) and development speed enhancement. After these, original youtube playlist product at 3rd priority"
> 2026-11-02 09:09 "let's make development speed issues higher priority than others"
> 2026-11-02 09:12 "If I cannot correctly understand what you are doing or how the project is progressing, dev speed in local sense doesn't have much meaning. It may be tactically fast, but heading to wrong direction (strategically incorrect or operationally sub-optimal)"
> 2026-11-02 16:35 "Now we move our focus on dev speed improvement. we have http://127.0.0.1:7391/2026-10-29-topic-dev-speed-monitor.html#remedies Can we have a list of task items in higher impact to lower impact order?"
- fix · backlog #384, PR #474 · direction lane: the comprehensibility suite's overarching design; the spec merged and its rows are filed as backlog #470 to backlog #479
- fix · backlog #405, PR #476 · early stop's METHOD proven wrong in five review rounds and discarded; the same goal moves to backlog #481 (the suite exits at its own first named failure). PR #476 shipped only two CI fixes (a running master run is not cancelled, the changed-file diff sees renames)
- fix · backlog #481 · REPLACES backlog #405 for the same goal: the suite itself exits with failure at its first named failure, so the harness infers nothing
- bookkeeping · backlog #480, backlog #481, backlog #482 · filed from PR #476's rounds: the rename skip, the sound early-stop redesign, the pending master run replacement
- fix · backlog #484, PR #480 · the goal tree prints ✖ for a thread whose backlog row is superseded or withdrawn, read from a bold marker in the row's Status cell, instead of ✅ because a PR merged
- bookkeeping · PR #479 · backlog #405's status says its method was proven wrong and its goal moved to backlog #481; backlog #484 filed
- bookkeeping · backlog #485 · filed from PR #480's round 3: six fate-reader gaps that fail back toward ✅, none on today's backlog
- side · PR #481 · the token page gets a before/after chart; the dev-speed page gets its open work ranked by impact
- bookkeeping · backlog #483 · filed from PR #475's CI: the backfill-work-lines F5 inode case is flaky
- fix · PR #475 · the backlog page shows each row's detail with line breaks and indenting, same words
- bookkeeping · PR #482 · the owner's approvals of backlog #330 and backlog #177 recorded; the dev-speed page answers when the sweep is scoped and when it is full; backlog #231 and backlog #403 ticked
- fix · backlog #415, PR #484 · the mutation sweep runs on 18 shards, one wave under the 20-job limit; paired CI runs on one commit: 1,194 s against 24 shards' 1,704 s
- fix · backlog #483, backlog #427, PR #486 · two CI flakes fixed at the cause: F5 compares by an open handle, and the memo-lifetime cases run first and stop the suite
- bookkeeping · backlog #486 · filed from PR #486's round 1: three Low leftovers of the flake fixes
- bookkeeping · PR #488 · backlog #481 corrected (the early stop must run the suite's own exit check), backlog #489 filed (the goal tree misattaches ledger entries), the early-stop explainer
- bookkeeping · backlog #488, backlog #490 · filed from PR #487's rounds: a self-test writes into the real ci-unwatched log; main()'s scoping is untested
- fix · backlog #487, PR #487 · the self-test count check runs its suites four at a time, each under its own HOME
- fix · backlog #177, PR #483 · Q0 drafted: the review method is chosen by kind of change; waits on the owner's walkthrough
- fix · backlog #330 · approved 11-02 20:53: a PR sweeps only the manifests whose subject changed, and a scheduled full sweep on master is the safety net
