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
- fix · PR #453 · hook output trimmed and ledger entries carry an explicit kind, so each turn re-reads less context
- side · backlog #407, PR #454 · mutation runs skip compaction-state's real-deadline cases, so the CI sweep is faster
- fix · backlog #359, PR #455 · the mutation total is derived from the per-file pins, so open PRs stop colliding on one line
