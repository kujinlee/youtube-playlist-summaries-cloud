# Memory Index

> One line per memory, written as the SITUATION it fires in. **Every row loads on every turn** (measured 2026-09-28); past 24,985 characters the tail is cut in silence (`check-memory-index-budget.py`). Keep under ~22,500. Each file opens with its CURRENT rule ([[memory-files-are-audited-weekly]]). History about this index: [[slice-history]].

- [⭐ Launch roadmap](launch-roadmap-state.md) — **START HERE.** Need launch status or a prod recipe (`claude_ro`, prod smoke)? Derive state; recipes here
- [TWO deliverables](project-has-two-deliverables.md) — weighing harness work as overhead? It is deliverable 2 (`docs/portable-practices.md`)

## How things go wrong here (⭐ = costly, recurring)

- [⭐⭐ A class fix needs an INDEPENDENT copy + identity case](a-class-fix-needs-an-independent-copy-and-an-identity-case.md) — generalising a case over a set? Loop an independent literal + an identity case, never the code's own set
- [⭐⭐ A guard can MANDATE the duplication it audits](a-guard-can-mandate-the-duplication-it-audits.md) — rewording a copy to satisfy a drift guard? Ask what fix the guard FORBIDS
- [⭐⭐ A check result isn't the claim](a-check-result-is-not-the-claim.md) — quoting a check, an exit code, or resetting a branch? Base = `origin/master`; never `$?` after a pipe; diff the old tip before `reset --hard`
- [A tool's mode may REPLAY, not read](a-tool-whose-mode-replays-must-be-called-with-the-mode-that-reads.md) — reading goal-tree/backlog-parse output as current? `--snapshot`; pass LINES
- [⭐⭐ A sweeping conclusion that ends the work early](a-sweeping-conclusion-that-ends-the-work-early.md) — concluding a whole class is impossible or not mine? Ask: does this mean I can stop?
- [⭐⭐ An inference stated as MEASURED](an-inference-stated-as-measured.md) — writing a number or "measured" into a doc? 3× in one doc; an invented cost figure is the tell
- [⭐⭐ A retrospective number needs provenance](a-retrospective-number-needs-provenance.md) — writing a number from recall, or patching a recorded figure? Enumerate or re-run; cite the SYMBOL
- [⭐⭐ Concurrent agents go wrong](concurrent-agents-go-wrong.md) — running 2+ agents, replacing a silent one, or `git add` while one is live? Disjoint files; stage EXPLICIT paths
- [⭐⭐ An anchor is unbound by ANY nearby edit](a-mutation-anchor-is-unbound-by-any-edit-nearby.md) — edited or merged a manifested script on ANY branch? Run the all-manifest anchor resolve
- [⭐⭐ "Cannot die" may mean a SECOND clause](cannot-die-may-mean-a-second-clause.md) — about to delete a mutation as "cannot die"? Construct an input; ask what ELSE answers it
- [⭐ A mutation loses its binding](a-mutation-loses-its-binding.md) — refactoring code a mutation anchors to or whose case it names? It is a two-file edit
- [What mutation testing proves](what-mutation-testing-proves.md) — citing mutation results as coverage? Load-bearing, never complete
- [⭐ A sever substitutes TODAY's value](a-sever-substitutes-todays-value.md) — severing a call site to test it? Substitute what the callee returns today, by RUNNING it
- [⭐⭐ Unit coverage does NOT compose](unit-coverage-does-not-compose.md) — joining two well-tested pieces? Mutate the CALL SITE
- [⭐⭐ A forced-choice test cannot fail](a-forced-choice-test-cannot-fail.md) — scoring a matcher? ADJACENT negatives; state the bound (0 in 60 → 5%)
- [⭐ Instruction is not isolation](instruction-is-not-isolation.md) — spawning a "blind" agent? Rebuild its input dir; asking is not a blind
- [⭐⭐ A harness cannot read a CAUSE from a child's text](a-harness-cannot-read-a-cause-from-a-childs-text.md) — parsing a child's output for WHY it failed? It can be forged; read rc + traceback
- [⭐ A vendored LINE NUMBER has no owner](a-vendored-line-number-has-no-owner.md) — citing a line in a plugin/vendored file? Name the symbol; quote code, not comments
- [⭐ A BOUND enumerates what is WITNESSED](a-bound-enumerates-what-is-witnessed.md) — writing a "does NOT cover" bound? List the ASSERTIONS, not what the seam touches
- [⭐⭐ Assert the emitted artifact PARSES](assert-the-emitted-artifact-parses.md) — a generator emits JS/HTML/JSON? Assert it PARSES (201 green cases over invalid JS)
- [⭐ A test that cannot fail](a-test-that-cannot-fail.md) — adding/ticking a check or removing a signal? Name the observation that makes it FAIL
- [A case can pass for an ambient reason](a-case-can-pass-for-an-ambient-reason.md) — writing a case? Build its world, flip what its NAME claims, watch it go red
- [⭐⭐ Ask an agent to REFUTE, not confirm](ask-an-agent-to-refute-not-confirm.md) — briefing a verification or research agent? Ask it to refute the claim
- [⛔ Rounds are CAPPED](review-rounds-capped-at-r3.md) — starting a review loop? Both halves r1, alternate r2–r3, r4+ FILE unless BLOCKER
- [⭐ Dual review: what it catches](dual-review-what-it-catches.md) — halves disagree, or one came back clean first? Trust the finding-reviewer until traced; a SURFACE wants a corpus run
- [⭐⭐ Running Codex](running-codex.md) — dispatching Codex? `codex-review.py` only; a timeout → DOUBLE `--timeout` once
- [⛔ Codex FILES what a prompt says is filed](a-reviewer-told-findings-are-filed-files-them.md) — writing a Codex prompt? Say REPORT only; never "filed"; no GitHub
- [It exists under a name I didn't search](it-already-exists-under-a-name-i-didnt-search.md) — about to propose BUILDING something? grep the concept, `ls` the dir first
- [Parallel branches, ONE log](parallel-branches-append-to-one-log.md) — opening a 2nd branch that touches dashboard-entries/roadmap? Stack or batch
- [A report format is a CONTRACT](a-report-format-is-a-contract.md) — changing a self-test's output format? The mutation harness parses it (4 contracts)
- [⭐⭐ Negatives by INTERCEPTION can't terminate](proving-a-negative-by-interception-cannot-terminate.md) — a guard proving "nothing else does X" by interception? PRE-COMMIT the retreat
- [⭐⭐ Two DISTINCT inputs, in ONE case](exercise-the-producer-at-two-distinct-inputs.md) — a case asserts a derived value? Drive its producer at two inputs in ONE case
- […and a CORPUS](a-measurement-is-only-as-good-as-its-corpus.md) — stating a number? Name the SET, enumerate it from the rule; re-derive a surprising zero (6×)
- [Measure what the code SEES](measure-the-population-the-code-actually-sees.md) — trusting a count, grep or negative result? Ask the consumer's own parser
- [The CONTROL refuted the premise](the-control-refuted-the-premise.md) — about to call a cause PROVEN? Run the control (defect present, fix absent)
- [A mock tests the contract you IMAGINED](a-mocked-boundary-tests-the-contract-you-imagined.md) — mocking a paid/external boundary? The first live run is its own gate
- [A privilege ≠ a CAPABILITY](a-privilege-is-not-a-capability.md) — using a Postgres grant as proof an op works? Perform the op as the role
- [True of the name, silent on the layer](true-about-the-name-silent-about-the-layer.md) — about to say "X never happens"/"no such command"? Search what else touches it
- [⛔ Edited backlog.md?](backlog-edit-needs-gen-backlog-page-selftest.md) — run `gen-backlog-page --self-test` too (PR #547: 23 CANNOT RUN shards)
- [⛔ Run the PR-only gates BEFORE push](run-pr-only-gates-before-push.md) — about to push a PR branch? Namespace + fixture-variation locally; read `$?` first
- [Worktree push needs a refspec](push-from-a-worktree-needs-an-explicit-refspec.md) — pushing from a worktree? `git push origin HEAD:refs/heads/<b>`, its own Bash call
- [A gate's CHANNEL can be weaker](a-gates-channel-can-be-weaker-than-the-gate.md) — adding a refusal/warning? Ask WHERE it prints and who reads that
- [⭐ Cost isn't the objective](cost-is-not-the-objective-improvement-is.md) — about to say "diminishing returns, stop"? Improving → keep going; else restructure
- [⭐ A self-authored retreat isn't a gate](a-retreat-you-author-for-yourself-is-not-a-gate.md) — a gate fired and I have a reason it shouldn't? Quote its definition
- [A framing widened to fit isn't a claim](a-framing-widened-to-fit-is-no-longer-a-claim.md) — a member doesn't fit a group's framing? MOVE it, never widen the sentence
- [A mechanism can be silently overridden](a-mechanism-can-be-silently-overridden.md) — claiming a flag/setting is in effect? What would I see if it did nothing?
- [Positional reads need a VERIFIED shape](a-positional-read-needs-a-verified-shape.md) — reading a cell by position (`cells[-2]`)? Verify the shape first
- [A hang isn't a diagnosis](a-hang-is-not-a-diagnosis.md) — a probe hung? Say "could not determine"; ask what the liveness check opens
- [Separate the RULE from the FETCH](separate-the-rule-from-the-fetch.md) — "can't test this, needs a live service"? Split the fetch from the pure rule
- [Mechanical edits damage what they PRESERVE](a-mechanical-edit-damages-what-it-preserves.md) — running a bulk/AST edit? Control count first
- [⭐ The answer may only be in the TRANSCRIPT](the-answer-may-only-exist-in-the-transcript.md) — asked what was decided? Grep `~/.claude/projects/<slug>/*.jsonl`, not only docs
- [An escalation has no closer](an-escalation-has-no-closer.md) — work made an escalation moot? Only the owner's reply closes it
- [⭐ Extract and RUN a plan's code](extract-and-run-a-plans-code.md) — reviewing a plan with fenced code? Run the blocks before reviewers
- [A doc inside the corpus it measures](a-document-inside-the-corpus-it-measures.md) — writing counts into a doc it counts? Derive at render time
- [After fixing, SEARCH for the class](after-fixing-search-for-the-class.md) — just fixed a defect? Search for another level/site/copy first
- [Assert the PROPERTY, not the mechanism](assert-the-property-not-the-mechanism.md) — writing the test that guards your fix? Not the fix's own tokens
- [Conventions catch what you READ](a-convention-catches-what-you-read.md) — writing a convention AND hand-fixing instances? It should be a script
- [Check the assumption, not the code](check-the-assumption-not-just-the-code.md) — reviewing a fix's framing? Measure the constraint itself
- [A finding's proposed FIX is a hypothesis](a-filed-finding-s-proposed-fix-is-a-hypothesis.md) — implementing a backlog/review "Fix"? Run it on the corpus first
- [A shim fails BOTH ways](a-shim-can-fail-in-both-directions.md) — adding a CSS var fallback/shim? Fix the class, not the one name
- [Findings expire when the DENOMINATOR moves](a-costbenefit-finding-expires-when-the-denominator-moves.md) — acting on an old "costs too much"? Re-measure both sides
- [⭐ Convergence ≠ the final-tree gate](review-convergence-is-not-the-final-tree-gate.md) — rounds done but `check-review-recorded` blocks? 3 answers
- [Gates detect defects, not design](gates-detect-defects-not-design.md) — treating green gates as proof a design is right? Phase 6 arms on THRASHING
- [Read the target back UNCACHED](discover-the-target-and-read-it-back-uncached.md) — writing to a prod resource? Discover the key; read back past the CDN
- [A stated bound outlives its hole](a-stated-bound-outlives-its-hole.md) — triaging a long red, or closing a hole? Check the asserted premise still holds
- [Harnesses launder failures](test-harness-can-launder-failures.md) — a negative test catches an error? Assert WHICH error
- [An instrument that edits the repo](an-instrument-that-edits-the-repo-corrupts-its-peers.md) — mutating while agents read the tree? Mutate a copy
- [Quote code, don't characterise it](quote-the-code-dont-characterise-it.md) — stating what code does? Paste the CONSUMER's file:line, or say unverified
- [Hardcode only what fails loudly](hardcode-only-what-fails-loudly.md) — hardcode or derive a check's config? Hardcode only what announces staleness
- [A second implementation drifts](a-second-implementation-of-one-rule-drifts.md) — about to hand-write a check/split a script owns? Call the script

## Design & guard lessons

- [One rule, one place](one-rule-one-place.md) — adding a mechanism or extracting a shared function? Ask what already serves it; list ALL clauses
- [anon EXECUTE is the DEFAULT](anon-execute-is-the-default-not-a-decision.md) — adding a public SQL function? Revoke PUBLIC in its own migration
- [RLS denial looks like absence](rls-denial-is-indistinguishable-from-absence.md) — missing vs denied on Supabase Storage? Same 404; use `provesAbsence`
- [Guards: SHAPE vs SEQUENCE](guard-classification-shape-vs-sequence.md) — writing a guard? What does it do when the caller is merely SECOND?
- [Unsatisfiable ordering is the tell](unsatisfiable-ordering-is-the-tell.md) — two rules make a sequence impossible? An "always" is scoped wrong
- [Operands from one stale closure](guard-operands-from-one-closure.md) — guard compares two values from one closure? It can never fire
- [A fence wrong both ways](a-fence-wrong-both-ways-asks-the-wrong-credential.md) — guard too loose AND too strict? Fix the credential, not the threshold
- [Evidence paths have no allocator](a-guards-evidence-path-is-a-namespace-with-no-allocator.md) — picking a `--review-id` or agent output path? One unique path per writer
- [Defined, not derived constants](defined-not-derived-constants.md) — a value blocks a shape change? Define the constant, don't derive it
- [Reservations guard spending](reservation-guards-spending-not-recording.md) — rejecting a record after paid work? A lease guards SPENDING only
- [postgrest aborts return, don't throw](postgrest-abort-returns-not-throws.md) — using `.abortSignal()`? It returns `{error}`; race your own timer
- [`position` is not vestigial](position-column-is-not-vestigial.md) — about to call a column dead? Check consumers per usage SITE
- [Blocked on a decision, not work](a-gate-can-be-blocked-on-a-decision-not-work.md) — a gate not moving? It may wait on a decision, not work

## Working with me

- [⛔ "Nothing needs you" reads the DASHBOARD](nothing-needs-you-must-read-the-dashboard.md) — about to say it? Regenerate `/dashboard`, quote its open-ask count
- [⛔ A DECLARATION is not the act](a-declaration-is-not-the-act.md) — just pushed? Arm the Monitor FIRST, then `--watching` (43m blind on a red CI)
- [⛔ REUSE a teammate or PARK an agent?](usage-is-cache-rewrites-of-parked-agents.md) — fresh agent per slice and round; parked ones rewrite cache (~70% of usage)
- [⛔ Make the owner approve/run a COMMAND?](no-command-approval-ceremony.md) — never; dry-run + a recovery point instead
- [⛔ Spawning an Agent? Pick its MODEL](route-agents-by-task-model.md) — Sonnet mechanical, Opus builds/folds/reviews, Fable Phase 6/specs/plans
- [⛔ An agent that waits on CI or a long job?](agent-blocking-call-over-5-min-rewrites-its-cache.md) — it never waits on CI: it reports, I poll; no call over ~270 s
- [⛔ 5h limit: pace by block clock](a-usage-limit-stop-needs-a-wake-at-reset.md) — starting agents or hit 100%? Pace by block clock; WAKE at reset+1m
- [⛔ Correcting a memory?](memory-files-are-audited-weekly.md) — rewrite its TOP, never append ⟳; weekly audit of changed files
- [⛔ Near the weekly usage line?](a-budget-stop-is-soft-with-a-reserve.md) — ELASTIC ~14%/day, PUSH by need, ≥8% per later day; wind down, never strand work; last day use it all
- [⛔ Choosing what to work on next?](owner-priority-order-1102.md) — dev speed → token saving → others; no starvation (owner 11-12)
- [⛔ How much to start/parallelise/verify?](behavior-follows-the-budget-situation.md) — TIGHT vs AMPLE from today's room; reassess each weekly reset
- [⛔ Writing '⏳ Waiting on…' or briefing a long job?](a-waiting-line-must-measure-age.md) — the line carries AGES; agents run foreground, report as FINAL TEXT
- [⛔ A PR is ready? PUSH it to CI now](push-to-ci-as-soon-as-ready.md) — CI costs no usage; never stagger; before a usage stop push all
- [⛔ Rebase/merge = ONE command](a-rebase-is-one-command-that-completes-or-aborts.md) — completes or aborts in one call; after review MERGE master in, never rebase
- [⭐ A side job gets a NAME first](a-side-job-gets-a-name-first.md) — side work over ~5 calls or a tracked file? Slug + branch first; announce the swap
- [⏳ Timestamps on banners + waiting lines](waiting-lines-carry-a-timestamp.md) — writing a ⏳ line, status table or banner? Clock time from `date`
- [⛔ Parallel threads need a GOAL TREE](parallel-threads-need-a-thread-map.md) — several threads in flight? `/goal-tree`, named by backlog/PR, tagged banners
- [⛔ Watching questions.md?](no-question-watch-while-owner-afk.md) — one-shot background poll that exits on a new line, not Monitor (~30k tokens/wake)
- [⏳ Show a WAITING SIGNAL, not prose](show-a-waiting-signal-not-prose.md) — ending a turn with work in flight? Lead with a ⏳ status line + clock time
- [⭐ The user does NOT follow in real time](the-user-does-not-follow-in-real-time.md) — multi-step job? `## ▶ [mm-dd hh:mm] STEP n of N` banner before each step, `▸` sub-steps
- [⛔ Building an explainer page? DRAW it](explainer-pages-lead-with-diagrams.md) — inline SVG for every flow/rule/before-after, house colours
- [⭐ A title is SCANNED, not read](a-title-is-scanned-not-read.md) — writing a commit subject/PR title/heading? Concrete scope first, then finding
- [⭐ How to shape a message to me](how-to-shape-a-message-to-me.md) — writing to the user? Conclusion first, readiness separate, ⛔ CHECK/RESULT table close
- [⭐⭐ Never close with a promise](never-close-with-a-promise.md) — about to end a turn promising more? Name what wakes me; arm `begin-plan.py`
- [⭐⭐ Blocking on a gate that does not EXIST](a-blocking-question-while-afk-costs-the-whole-night.md) — owner AFK, about to ask or wait? Take the recommended option unless CRITICAL; grep the rule
- [⛔ Work with no fitting GOAL?](i-propose-goal-names-the-owner-picks.md) — I propose a goal named for its objective; the owner picks
- [⭐ Putting a choice to the user](putting-a-choice-to-the-user.md) — offering options? Verdict first, A/B/C + recommended; decide it myself when obvious
- [⭐ Name and define every reference](name-and-define-every-reference.md) — about to type `#N` or jargon? Noun before every #, every use; don't script it
- [⛔ PUSH is mine; MERGE WHEN READY](push-is-mine-merging-is-theirs.md) — about to push or merge? READY ⇒ merge; HOLD ⇒ I verify it line by line
- [⛔ A low-risk HOLD is paid for with a REVIEW](a-waiver-hold-is-paid-for-with-a-review.md) — HOLD on a low-risk reason? Decide or buy one review; `--flagged-block` in the final round
- [⭐ Defaults I decide myself](defaults-i-decide-myself.md) — about to ask about a small spend, experiment or verification depth? Cheaper to run → run it
- [⛔ Owner 11-13: marketplace, ff, 0028](owner-decisions-1113-marketplace-ff-392.md) — decision 5/7, main-checkout ff, migration 0028? ⚠ never reset docs/memory in the ff
- [Fable limit resets are MANUAL](fable-limit-resets-are-manual.md) — a Fable run blocked by its cap? Owner presses Settings > Usage; suggest only then
- [Stranger experiment token](stranger-token-h2-done.md) — running the stranger experiment? `~/.config/claude-stranger/token` via `CLAUDE_CODE_OAUTH_TOKEN`; never print it
- [⛔ Need port 7391?](may-free-port-7391.md) — stop the owner's explainer server, use it, RESTART it; no announcement needed
- [⭐ Restart Docker, never CANNOT RUN](restart-docker-dont-record-cannot-run.md) — a gate needs Docker and it hangs? SIGKILL the backend and restart
- [Process conventions](process-conventions.md) — committing, merging, resuming? Branch+PR always; spec = human gate; resume reads the RUNNING SYSTEM
- [⛔ Specs/plans are WALKED THROUGH](document-approval-is-interactive.md) — asking approval of a spec/plan? An interactive page, never a yes/no
- [⛔ Decisions go on a selection card](print-selection-cards-in-chat.md) — putting a decision to the user? Chat → AskUserQuestion; a page under review → ✍ tag; AFK → decide
- [⭐ "FIRST" can mean before-shipping](first-can-mean-first-before-shipping.md) — a roadmap says "do X FIRST"? Open X's row and quote its trigger
- [⛔ The Agent-tool restriction has NO owner](agent-tool-restriction-has-no-owner.md) — about to ask before spawning a review agent? It is pre-authorised
- [⛔ Dual review is the PROCESS](dual-review-is-the-process-not-a-request.md) — about to ask to run a review half? Never; run what the round topology owes
- [⛔ File without asking](feedback-agree-before-filing.md) — filing or amending a backlog row? Act, then report; wait only if the GOAL is in question
- [Flag transitional choices](feedback-flag-transitional-choices.md) — presenting a choice or finding? Tag it transitional or structural
- [⭐ ALWAYS subagent-driven execution](always-choose-subagent-driven-execution.md) — a skill asks subagent vs inline? Subagent, fresh each time
- [⭐ A stacked PR dies with its base](a-stacked-pr-dies-with-its-base-branch.md) — merging a base PR with `--delete-branch`? Retarget the child first
- [A signal needs its base rate](a-signal-needs-its-base-rate.md) — quoting what a gate/trigger says? Ask what it returns over the whole population

## Environments & product context

- [⛔ Mac slow / memwatch alert?](memwatch-watchdog-fseventsd.md) — fseventsd hit 44 GB on 11-09; the fix needs sudo, so it's the owner's
- [Local cloud validation](local-cloud-validation-run.md) — running the cloud stack locally? Source `.env.local` for the worker, Node 22+, check the port
- [Access tiers vision](access-tiers-vision.md) — product direction for tiers/pricing? Free tier built; billing is the gap
- [backlog.md stays Markdown](backlog-md-stays-markdown.md) — tempted to move it to JSON? Decided 2026-09-10: no
- [⭐ Terminal selection dies under fullscreen TUI](terminal-selection-dead-under-fullscreen-tui.md) — can't drag-select in the terminal? Mouse reporting; one setting fixes it

## Slice history

- [⭐ Slice history — every shipped slice, with PR + SHA](slice-history.md) — need a shipped slice's PR, SHA or rounds? ⛔ New slice rows go THERE, never here
