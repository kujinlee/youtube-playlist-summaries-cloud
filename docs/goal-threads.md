# Goal threads — why each piece of work exists

The ONE hand-written input of the goal-tree page (backlog #363). It declares, for each goal the owner
set, which threads of work serve it and HOW. It declares nothing about state: whether a thread is
merged, open, red or in flight is DERIVED by `python3 scripts/goal-tree.py --snapshot` from
`git log origin/master`, `gh pr list` and `.claude/inflight.jsonl`, and logged to the main checkout's git-ignored
`.claude/goal-tree-log.jsonl`. The page is http://127.0.0.1:7391/goal-tree.

Grammar, read by `scripts/goal-tree.py` (`parse_threads`); a line that breaks it fails the snapshot loudly:

- `## GOAL <slug>` opens a goal. The slug is lowercase words joined by `-`, unique in this file.
  The page numbers goals `GOAL n` by their first request's time (ties in file order), and anchors each as
  `#goal-<slug>`, so a goal added with a later first request renumbers none; deleting one, or adding one dated earlier, can.
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
> 2026-11-07 20:06 "I will be AFK mostly until Monday Nov. 9th. Meanwhile, try to fix remaining high impact backlogs on dev-speed-first, token-usage-first, comprehensibility-suite, guard-harness-audit"
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
- fix · backlog #511 · the harness section of the features page splits into six sub-sections, so its open rows read by area
- fix · backlog #545, PR #539 · the stalled-work hook names a DIRTY PR that has no CI run
- bookkeeping · backlog #544 · measured twice more on 11-08: a merge of master that changes no flagged file still voids every sibling PR's loosening answers
- bookkeeping · backlog #578 · filed from the held-pins-head Phase 6 review: every `python3 scripts/X.py`, the merge gate included, runs a stdlib-named file committed in `scripts/`
- fix · PR #557 · closure detection cannot remove files outside its copy: the Phase 6 review deletes slice 1's guessing removal model (backlog #601); isolation refuses removals outside the sandbox (backlog #600)
## GOAL comprehensibility-suite
> 2026-10-27 11:30 "I am aiming to complete comprehensibility suite features. … what is current status of comprehensibility suite?"
> 2026-10-27 17:45 "we would need to define role and usages for these comprehensibility/status/explainer pages (goals, features, backlogs, dashboard, worklines, brief etc) … these pages are currently developed and produced in ad-hoc manner without overarching design"
> 2026-10-27 18:02 "Goal is to have tool for human (me) to understand what you (AI agent) [are doing]. … The tag vocabulary and tagging should serve the goal."
> 2026-10-28 03:41 "I wonder if this kind of goal tree is logged every so often (periodically in time or when meaningful changes are made) and I can see the page to learn how your work has been progressed, the page can be ideal dashboard."
- fix · backlog #381, PR #421 · a backlog row can carry several tags, read by one parser for both pages
- fix · backlog #376, PR #422 · a composed page with the Theme button gets the text-style switcher too
- fix · backlog #603 · explainer pages mark each owner decision with a yellow ✍ DECISION n of N tag and a top counter; an answered tag turns green
- fix · backlog #384 · the suite's overarching design · waits on the owner's walkthrough of the design ideas
- fix · backlog #363 · the goal tree as a logged, generated page
- bookkeeping · PR #423 · backlog #384, backlog #385 and backlog #386 filed; the design-ideas section
- bookkeeping · backlog #496 · filed 2026-11-03 from the owner's NEEDS YOU pass: four of six items were settled decisions whose marker still asked (backlog #2 answered, backlog #306 and backlog #384 already decided, backlog #86 moot)
- fix · backlog #198 · the recall vocabulary named with the owner 2026-11-03 and written to CONTEXT.md; backlog #307 amended (the index line is the trigger's first clause)
- side · PR #423 · the tag-vocabulary survey page and the suite inventory page
- fix · backlog #389, PR #434 · the work-lines page retires into the goal tree, its history archived (the owner's decision D2)
- fix · backlog #497 · the goal tree shows when each thread merged, shows parked and queued work per goal, and folds older merged and unplanned threads
- fix · backlog #499 · the goal tree shows the current plan in its own dated block and keeps every earlier plan as one collapsed line (owner 2026-11-04 06:05)
> 2026-11-04 15:31 "what if we start #499 today and continue to tomorrow?"
> 2026-11-04 18:09 "if slice 2 is continuation of same backlog, why wait until tomorrow? this current session already has context"
> 2026-11-04 14:33 "I have to click Refresh button two times to get real refresh"
- fix · backlog #502 · a Refresh click keeps saying "rebuilding…" until the page reloads or the rebuild reports a failure, so one click is enough
> 2026-11-05 01:38 "what you are doing currently isn't appear in goal-tree"
> 2026-11-05 01:46 "let's not wait. finish the work while memories are warm"
- fix · backlog #505, PR #505 · work in flight shows under its goal before the PR merges: a ledger entry carries its goal and thread
- bookkeeping · backlog #507 · filed 2026-11-05: closing a ledger entry whose thread is not yet on master drops the thread from the tree without a warning
> 2026-11-05 08:12 "at the merge decision by hold, can this be decided by agnet or can it be decided in gate itself"
- bookkeeping · backlog #508 · filed 2026-11-05 from the owner's card A: a rising self-test count is cleared by the gate; every other flagged line is answered by the final reviewer, not the PR's author
> 2026-11-05 08:19 "If the agenda list shows larger goat that the line item belongs to, I can see the current focus or which area you are working on"
> 2026-11-07 20:06 "I will be AFK mostly until Monday Nov. 9th. Meanwhile, try to fix remaining high impact backlogs on dev-speed-first, token-usage-first, comprehensibility-suite, guard-harness-audit"
> 2026-11-10 08:25 "last night I reviewed http://127.0.0.1:7391/2026-10-15-brief-marketplace-inventory-walkthrough.html let's add this initiative to current focus."
- fix · backlog #509 · each agenda step shows the goal it serves, derived from the thread lines, and a NOW line shows what is in flight
- fix · backlog #504 · the agenda log's record check refuses a step whose refs are not (kind, number) pairs
- fix · backlog #514 · in-flight work is added with a goal, or says why it has none
- fix · backlog #515 · an agenda step for a partly-done row is not ticked by its PR's merge
- fix · PR #511 · the agenda block as a recap: an accent heading, the thrust in one sentence, items with their purpose, focus by goal
- fix · backlog #517 · the agenda lists RUNNING work apart from OWED work, and each owed item says what it waits for
- fix · backlog #518 · a mixed thread — one ref merged, a row resolving to an open PR — owns that PR, and its wait holds it
- fix · backlog #519 · the timeline tells each entry as one sentence and folds the older ones; an empty NEEDS YOU is a muted line
- fix · backlog #520 · the wording-only timeline case tests a real wording-only tree; an added thread already merged is told as landed
- bookkeeping · backlog #516 · two agenda-block behaviours with no failing case (Focus escaping and links, the empty in-flight line)
- fix · backlog #496 · NEEDS YOU flags a row whose status records a decision after its NEEDS-OWNER marker (DECIDED / answered by the owner, or a status head rewritten after the marker), with the remedy, and keeps it listed
- fix · backlog #408, PR #536 · the generated pages are rebuilt from a fresh private tree, with a stated threat model, after a thrashing-armed architecture review
- side · PR #558 · the goal-tree page gets the Ask tray, lifted by brief-compose like the backlog and dashboard pages; answers to its questions show as a collapsed marker, never interlaced with the tree
- fix · backlog #610 · only the fresh-clone build writes the served goal-tree page; a direct run is refused
- fix · backlog #611 · an agenda step naming a backlog row is ticked by the row's status, not by the PR that filed it
- fix · backlog #612 · a declared wait whose date has passed is flagged, not shown as a reason
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
> 2026-11-04 08:37 "if we are going to run out of remaining token usage, I would spend the remainder earlier rather than stop working for tomorrow."
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
> 2026-11-04 09:29 "For example, emergency reserve is set to 5% and remaining days are 3 days(excluding today), max usage for today can be 100 - 3×5 = 85"
- fix · backlog #500 · new agents are refused at 100% − 5% × the days left after today, never above 97% (09:29), so each later day keeps a reserve and the rest is spent
- bookkeeping · backlog #501 · the usage guard should read only the tail of a large meter log (filed from backlog #500's round-1 review)
> 2026-11-05 08:36 "by reset time is approaching, gradually loosing the hard stop limit or do not apply the hard stop altogether after certain time of last day might be better"
> 2026-11-05 08:40 "what has been the burning rate of usage? Will the 6 hours before the reset be enough to utilize the remaining capacity?"
> 2026-11-07 20:06 "I will be AFK mostly until Monday Nov. 9th. Meanwhile, try to fix remaining high impact backlogs on dev-speed-first, token-usage-first, comprehensibility-suite, guard-harness-audit"
- fix · backlog #510 · the weekly stop rises from 97% to 99% over the whole last day before the reset, only on a fresh meter reading (owner card A, 08:47, replacing the 08:38 six-hour window)
- fix · backlog #521 · on the last day the usage hook leads with the room the reset would lose — USE IT — instead of only saying hold back
- fix · backlog #522 · the usage hooks run origin/master's guard, never the checked-out branch's (measured 11-05 19:58 and 20:38)
- fix · backlog #523 · on the last night the only stop is the hard 100% limit (owner 11-05 20:46/20:53, strategy B)
- bookkeeping · backlog #524 · a finer weekly estimate from the five-hour meter, so a finishing reserve can be measured
- fix · backlog #503 · measure whether agents spawned close together share one cached start-up
- fix · backlog #444 · revisit Opus-vs-Sonnet routing once the meter regression has a ratio · waits on days of meter data
- blocker · backlog #513 · the usage hook runs the checked-out branch's guard, so an unmerged branch sets the stop
- fix · backlog #630 · the Fable 5.2 pilot: a comparison week of Fable against Opus per task, reported at the 11-20 reset
- fix · backlog #645 · the 5-hour meter is paced against its fixed block clock: free, at most 2 agents, no new agents, or stop and wake at reset + 1 min (owner card A, 11-13 16:20)
## GOAL dev-speed-first
> 2026-11-02 09:05 "Our main thrust was comprehensibility suite and publishing them as public tool (as plugin) and development speed enhancement. After these, original youtube playlist product at 3rd priority"
> 2026-11-02 09:09 "let's make development speed issues higher priority than others"
> 2026-11-02 09:12 "If I cannot correctly understand what you are doing or how the project is progressing, dev speed in local sense doesn't have much meaning. It may be tactically fast, but heading to wrong direction (strategically incorrect or operationally sub-optimal)"
> 2026-11-02 16:35 "Now we move our focus on dev speed improvement. we have http://127.0.0.1:7391/2026-10-29-topic-dev-speed-monitor.html#remedies Can we have a list of task items in higher impact to lower impact order?"
> 2026-11-05 00:30 "we had backlog for formating backlog prose for human reader (newline, indenting etc) Have you implemented it?"
> 2026-11-05 00:42 "this backlog #40 shows that (1) filed entry -> formatted (2) STATUS CELL, what changed in this entry -> not formatted"
> 2026-11-10 08:25 "last night I reviewed http://127.0.0.1:7391/2026-11-09-brief-observed-reach-spec-walkthrough.html let's add this initiative to current focus."
> 2026-11-07 20:06 "I will be AFK mostly until Monday Nov. 9th. Meanwhile, try to fix remaining high impact backlogs on dev-speed-first, token-usage-first, comprehensibility-suite, guard-harness-audit"
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
- fix · PR #504 · the 20 long backlog rows that still showed as one block get cues, the Status cell and the entry diff break the same way, and the self-test refuses a new 600+ character one-block row
- bookkeeping · PR #482 · the owner's approvals of backlog #330 and backlog #177 recorded; the dev-speed page answers when the sweep is scoped and when it is full; backlog #231 and backlog #403 ticked
- fix · backlog #415, PR #484 · the mutation sweep runs on 18 shards, one wave under the 20-job limit; paired CI runs on one commit: 1,194 s against 24 shards' 1,704 s
- fix · backlog #483, backlog #427, PR #486 · two CI flakes fixed at the cause: F5 compares by an open handle, and the memo-lifetime cases run first and stop the suite
- bookkeeping · backlog #486 · filed from PR #486's round 1: three Low leftovers of the flake fixes
- bookkeeping · PR #488 · backlog #481 corrected (the early stop must run the suite's own exit check), backlog #489 filed (the goal tree misattaches ledger entries), the early-stop explainer
- bookkeeping · backlog #488, backlog #490 · filed from PR #487's rounds: a self-test writes into the real ci-unwatched log; main()'s scoping is untested
- fix · backlog #487, PR #487 · the self-test count check runs its suites four at a time, each under its own HOME
- fix · backlog #177, PR #483 · Q0 drafted: the review method is chosen by kind of change; waits on the owner's walkthrough
- fix · backlog #330 · approved 11-02 20:53: a PR sweeps only the manifests whose subject changed, and a scheduled full sweep on master is the safety net
- fix · backlog #330, PR #496 · built: a PR sweeps the manifests its diff selects (one guard ≈ 5 of 87), the harness or an unreadable diff runs all, and master + a daily schedule run the full sweep with a sweep-red issue on red
- fix · backlog #498 · the scoped sweep's import closure accepts a module loaded by its `.py` filename (Codex r4 on PR #496, filed under the round cap)
- fix · backlog #426, PR #491 · a merge of master after the final review round no longer forces another round; 5 rounds and a thrashing-armed architecture review
- fix · backlog #470, PR #489 · every backlog row and PR mentioned on the five generated pages is a link; the page reading redesigned twice, 4 rounds and an architecture review
- bookkeeping · backlog #491, backlog #493, backlog #494 · filed from PR #491's and PR #489's rounds: whitespace path names, the regen hooks' unseen failure channel, render-time key linking
- bookkeeping · backlog #495 · filed from PR #489's CI: the completion-order kill case races `as_completed`, so its mutation survives on a loaded runner; register rows 22 (the compaction deferral) and 4 (the owner keeps the 300k window) and the backlog #47 indexed-search note ride in the same docs PR
- side · backlog #492 · the owner's destructive-command recovery gate (11-03 14:20), filed to build after backlog #330 when the usage margin allows
- fix · backlog #506 · two mutations killed only by chance red unrelated PRs' sweeps — both now fail on every run; the seed-varied sweep remains
- fix · backlog #512 · self-tests leave temp directories behind, and the pile slows long-path shell commands · waits on the weekly reset (Fri 11-06 02:00)
- fix · backlog #533 · a mutation pin bump no longer sweeps the whole manifest: the pins move out of the sweep harness into a data file (phase 1 of the owner's card A, 11-06 09:10)
- fix · backlog #534 · one full sweep on a batch branch of master plus every ready PR head, instead of one per PR (phase 2 of card A); build after backlog #533
- fix · backlog #537 · the explainer question watcher no longer holds every auto compaction, so compaction comes at a pause (owner 11-06 card A; the window lowers to 200k locally)
- fix · backlog #231, PR #534 · gen-backlog-page's suite runs in 27 s instead of 73 s: its pure layout and drift builds are memoised
- fix · backlog #512, PR #535 · fixture_git.isolated() gives each self-test block its own TMPDIR and removes it
- fix · backlog #231, backlog #406, PR #537 · the self-tests of check-usage-pace, goal-tree and check-main-drivable cost less; a timing case an lru_cache masked is now a spy case
- fix · backlog #558, PR #538 · a mutant's suite timeout scales with its own control, min(600, max(120, 20×control)); master's full sweep is green again
- fix · backlog #586, PR #552 · spec approved 11-09: a PR's mutation sweep picks the guards whose tests were SEEN to read a changed file (strace -f), so a docs-only PR stops sweeping 67 of 89 manifests
- fix · backlog #586 · the plan: a committed shadow ledger read at BASE (owner 11-09 14:55, card A); redesign review round 1, then the plan PR and slices 1-5 (slice 1 measures strace on the CI runner)
- fix · backlog #586, PR #557 · slice 1 of observed-reach selection: strace records each suite's reads on the runner, so a PR's mutation sweep can be chosen by what the suites actually read
- fix · backlog #641, PR #584 · the shared dashboard log makes parallel PRs conflict and restart CI: filed with its measurement
- bookkeeping · backlog #643, PR #584 · `npm run test:e2e` is never fully green locally (F5c fails on master; production smoke needs auth fixtures)
- fix · backlog #619, PR #580 · the mutation sweep reads one record per shard, so a lost, duplicated or unfinished shard goes red instead of reading as clean

## GOAL product
> 2026-11-02 09:05 "Our main thrust was comprehensibility suite and publishing them as public tool (as plugin) and development speed enhancement. After these, original youtube playlist product at 3rd priority"
- fix · PR #392 · corrections: the daily limit is enforced before the paid call, and every attempt is metered · waits on product work resuming: the owner parked the Fly deploy 2026-11-14 06:45 (migration 0028 is applied)

## GOAL memory-hygiene
> 2026-11-13 16:22 "if memory file contains more information than necessary, will it harm the performance or doesn't matter much"
> 2026-11-13 16:25 "Rewrite the file I just edited so the current rule comes first. -> not just that file. I would audit all other memory files. And make such audit to be done periodically (weekly or monthly?)"
- fix · PR #585 · one-time audit: every memory file opens with its current rule; the always-loaded index 24,843 → 21,888 characters

## GOAL harness-ships-elsewhere
> 2026-11-10 08:25 "last night I reviewed http://127.0.0.1:7391/2026-10-15-brief-marketplace-inventory-walkthrough.html let's add this initiative to current focus."
> 2026-11-14 08:29 "this is related with harness-plugin. the marketplace work is largely about comprehensibility. By the way, let's make uniform goal name and internal work name(?) such as harness-plugin vs marketplace-work seems to be same. Let's use only one of them."
- fix · PR #376 · the marketplace-inventory spec: could a stranger use any of this; APPROVED by the owner 11-11 05:53, folded as section 2c, round 7 converged
- fix · backlog #384 · the comprehensibility suite's overarching design: the pages are a large part of what the plugin ships
- fix · backlog #644 · one piece of work has one name: goal, anchor, feature node and ledger id agree, and a check keeps them agreeing
