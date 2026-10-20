# Memory Index

> One line per memory. ⛔ **CORRECTED 2026-09-28: NOTHING DECIDES RELEVANCE.** This line used to say *"the hook decides relevance"* and that was never true — measured: no file in the `remember` plugin references `MEMORY.md` at all, and all **133** rows arrive every session, unfiltered. **So every row below is always in context and none of them is ever matched to the moment** — which is why recall fails here, and why the hook's title has to do the matching by itself. Write each hook as the SITUATION you would be in, not the subject it is about (backlog #191).

- [⭐ RESUME: anchors + stable ids](anchor-name-and-stable-id-handoff.md) — M4 MERGED (#155); `0027` LIVE ON PROD. The stable-id roadmap **EXISTS** — I once re-derived it wrongly
- [⭐ Launch roadmap](launch-roadmap-state.md) — **START HERE.** M1+M2+M3 closed. Prod ops + `claude_ro` recipe
- [⭐⭐ #191 — semantic recall REPLICATED](backlog-191-semantic-recall-replicated.md) — lexical **3/20** vs semantic **20/20**, 0 false fires in 60. Triggers GOOD, matcher was the problem. 2 branches, neither merged
- [TWO deliverables](project-has-two-deliverables.md) — ⭐ the product AND a reusable harness (`docs/portable-practices.md`)

## How things go wrong here (⭐ = costly, recurring)

- [⭐⭐ A class fix needs an INDEPENDENT copy + identity case](a-class-fix-needs-an-independent-copy-and-an-identity-case.md) — looping over the set under test makes the case LIST shrink, not redden (57/57→56/56). The one sound duplicate
- [⭐⭐ A guard can MANDATE the duplication it audits](a-guard-can-mandate-the-duplication-it-audits.md) — deleting the stale copy went RED; 4 rounds could only reword. Ask what a guard FORBIDS
- [⭐⭐ A check result isn't the claim](a-check-result-is-not-the-claim.md) — green says nothing about the BASE (use `origin/master`); a red is a STOP, it hid a second failure. ⭐ **Never read `$?` after a PIPE**, and `grep | head || echo MISSING` can NEVER fire. ⭐⭐ **A restore verified against WHAT I DID lost a 32KB review** — diff the old tip BEFORE `reset --hard`
- [⭐⭐ An inference stated as MEASURED](an-inference-stated-as-measured.md) — **3× in ONE document**, each caught by the NEXT round, never me. The fix is PARAGRAPH STRUCTURE, not "verify agent output" — a cost figure invented to support a sound argument is the tell
- [⭐⭐ A retrospective number needs provenance](a-retrospective-number-needs-provenance.md) — recall is fiction and THE CORRECTIONS FAIL TOO (**0 for 5**). DERIVE; cite the SYMBOL, not the line
- [⭐⭐ Concurrent agents go wrong](concurrent-agents-go-wrong.md) — the WRONG SUBJECT, a report that never arrives, one Postgres → a FALSE BLOCKING. ⭐⭐ **A LIVE AGENT'S FILE IS NOT STATIC** — cost TWICE in one night (appended to it; `git add -A`'d it). Stage EXPLICIT PATHS. RULE in `docs/review-method.md`
- [⭐⭐ An anchor is unbound by ANY nearby edit](a-mutation-anchor-is-unbound-by-any-edit-nearby.md) — 7 orphaned in ONE session; one was a BLOCKING red CI step. Use the HARNESS's own rule, over EVERY manifest
- [⭐⭐ "Cannot die" may mean a SECOND clause](cannot-die-may-mean-a-second-clause.md) — I deleted on that reading TWICE in two commits; both reversed by the next review. **4 masking pairs in one file.** Construct an input, and ask what ELSE answers this
- [⭐ A mutation loses its binding](a-mutation-loses-its-binding.md) — anchors bind by TEXT, so a refactor ORPHANS them; promoting one drops its fake-`HOME` redirect
- [What mutation testing proves](what-mutation-testing-proves.md) — load-bearing, never complete; a MUTATION can be masked like a fixture
- [⭐ A sever substitutes TODAY's value](a-sever-substitutes-todays-value.md) — a literal I typed from memory went RED and read as *"wiring is protected"*; the real value → 58/58 green and the defect was live. **Fails toward GOOD NEWS.** Derive by RUNNING the callee
- [⭐⭐ Unit coverage does NOT compose](unit-coverage-does-not-compose.md) — 3 rounds, 3× the gap was BETWEEN two tested pieces. **Mutate the CALL SITE** — the whole change reverted there, suite green
- [⭐⭐ A forced-choice test cannot fail](a-forced-choice-test-cannot-fail.md) — must-fire-only is UNFALSIFIABLE; negatives must be ADJACENT, not absurd. State the BOUND (0 in 60 → 5%), never "no false positives"
- [⭐ Instruction is not isolation](instruction-is-not-isolation.md) — "read only these two files" is not a blind; the answer key was in the same directory. Rebuild the world, don't ask
- [⭐⭐ A harness cannot read a CAUSE from a child's text](a-harness-cannot-read-a-cause-from-a-childs-text.md) — 3 rounds, ONE cause; an arch review did NOT stop it. A crash FORGED a `[FAIL]`
- [⭐ A vendored LINE NUMBER has no owner](a-vendored-line-number-has-no-owner.md) — 5 sites, one the REFUSAL TEXT; `grep -r` skips symlinks. ⛔ The FIX cited a stale COMMENT
- [⭐ A BOUND enumerates what is WITNESSED](a-bound-enumerates-what-is-witnessed.md) — I listed what the seam TOUCHES; the cases covered 3 of 4. The missing one reinstated the defect the harness exists for. ⚠ A caveat headed "stated rather than hidden" that is wrong is worse than none
- [⭐⭐ Assert the emitted artifact PARSES](assert-the-emitted-artifact-parses.md) — 201 cases green over invalid JS; every control dead, and the browser's "0 flips" read as success. `}{` balances
- [⭐ A test that cannot fail](a-test-that-cannot-fail.md) — what observation makes this FAIL? Removing a signal hollows out its falsifier
- [⭐⭐ Ask an agent to REFUTE, not confirm](ask-an-agent-to-refute-not-confirm.md) — 4-for-4 on 2026-09-23: the refuting prompts caught a wrong correction I had ALREADY PUBLISHED; the confirming one shipped a summary contradicting its own table. ⚠ The gap is VERIFICATION/RESEARCH agents — review halves already have a mandate (33 docs); I claimed otherwise without grepping
- [⭐ Dual review: what it catches](dual-review-what-it-catches.md) — halves NOT redundant; the finding-reviewer right 3/3; ⭐ and **review is the wrong instrument for a SURFACE** — 6 rounds ≈ 7 edge cases, one corpus run ≈ 5,287
- [⭐⭐ Running Codex](running-codex.md) — a "timeout" is MY `--timeout`: DOUBLE it (900s default, 2700-3600 for big reviews). Run from the coordinator
- [It exists under a name I didn't search](it-already-exists-under-a-name-i-didnt-search.md) — ⭐ 3× in ONE day. Check before proposing to BUILD
- [Parallel branches, ONE log](parallel-branches-append-to-one-log.md) — ⭐ 3 same-day PRs: #1 clean, rest CONFLICT
- [A report format is a CONTRACT](a-report-format-is-a-contract.md) — ⭐ "0 red cases" over a shape the harness can't parse
- [⭐⭐ Negatives by INTERCEPTION can't terminate](proving-a-negative-by-interception-cannot-terminate.md) — FIVE unearned passes. PRE-COMMIT the retreat
- [Passing for an AMBIENT reason](a-case-can-pass-for-an-ambient-reason.md) — ⭐⭐⭐ 4× then **5 MORE**; tell = NAME vs BODY. **Flip what the case names, check it reddens** — stating a falsifier is not running one
- [⭐⭐ Two DISTINCT inputs, in ONE case](exercise-the-producer-at-two-distinct-inputs.md) — a case is satisfied by the CONSTANT its own fixture supplies. 3 rounds, 9 survivors; pairwise-distinct FIXTURES are the weaker rule that already failed
- […and a CORPUS](a-measurement-is-only-as-good-as-its-corpus.md) — ⭐ 4×. Code did what I measured; I measured the wrong SET
- [Measure what the CODE sees](measure-the-population-the-code-actually-sees.md) — ⭐⭐⭐ **12×, SIX of them in one session (2026-09-26)**: a grep filter, a wrapped line, an off-by-one `tail`, a wrong CSS class, CSS-uppercased text, and `gh` check states — **check a KNOWN POSITIVE before trusting a negative**, and ⛔ a fix inside a heredoc is not a class fix. 5×. `splitlines()` where the subject uses `split("\n")`. ⭐ 2026-09-22: the RUN was right and the CONCLUSION was about a different subject — a synthetic fixture proved what the tool does to the FIXTURE; I never opened the real callee's signature
- [The CONTROL refuted the premise](the-control-refuted-the-premise.md) — ⭐⭐ "red → fix → green" is NOT a cause
- [A mock tests the contract you IMAGINED](a-mocked-boundary-tests-the-contract-you-imagined.md) — ⭐ 2,808 green tests, 500s on first live press
- [A privilege ≠ a CAPABILITY](a-privilege-is-not-a-capability.md) — ⭐ `has_table_privilege` said granted
- [True of the name, silent on the layer](true-about-the-name-silent-about-the-layer.md) — ⭐ right about the object NAMED, silent on what overrides it
- [Worktree push needs a refspec](push-from-a-worktree-needs-an-explicit-refspec.md) — ⭐ reads SESSION cwd; the block kills the WHOLE Bash call
- [A gate's CHANNEL can be weaker](a-gates-channel-can-be-weaker-than-the-gate.md) — ⭐ a refusal on hook stdout reached NOBODY
- [⭐ Cost isn't the objective](cost-is-not-the-objective-improvement-is.md) — improving → KEEP GOING; else RESTRUCTURE, never "diminishing returns"
- [⭐ A self-authored retreat isn't a gate](a-retreat-you-author-for-yourself-is-not-a-gate.md) — I argued the rule away when my own stricter one missed
- [A framing widened to fit isn't a claim](a-framing-widened-to-fit-is-no-longer-a-claim.md) — ⭐ MOVE the member, never loosen the sentence
- [A mechanism can be silently overridden](a-mechanism-can-be-silently-overridden.md) — ⭐ ask: *what would I see if this guard did nothing?*
- [Positional reads need a VERIFIED shape](a-positional-read-needs-a-verified-shape.md) — ⭐ `cells[-2]` hit the wrong cell, closed 2 open items
- [A hang isn't a diagnosis](a-hang-is-not-a-diagnosis.md) — ⭐ `nc -z` proves a listener accepts, not that it answers
- [Separate the RULE from the FETCH](separate-the-rule-from-the-fetch.md) — ⭐ 3 ratchets untestable 8 days: the ENTRY POINT needed docker
- [A second implementation DRIFTS](a-second-implementation-of-one-rule-drifts.md) — ⭐⭐ **17×**, newest 2026-09-22: `awk -F'|'` then `split("|")` on a backlog row, TWICE, while `check-docs.CELL_SPLIT` owns the rule and `gen-backlog-page.py` imports it. A weaker stand-in passes what it'd REFUSE. ⭐ **Ask which PART is slow** — `--mutate .` refuses a bad manifest in **<1s**, so the real gate IS the cheap pre-check
- [Mechanical edits damage what they PRESERVE](a-mechanical-edit-damages-what-it-preserves.md) — ⭐ an AST pruner broke surviving code 3×
- [⭐ The answer may only be in the TRANSCRIPT](the-answer-may-only-exist-in-the-transcript.md) — "what was the conclusion?" → grep `~/.claude/projects/<slug>/*.jsonl`, not just the docs. I reported "none recorded" and invented 4 directions; the real answer was one grep away
- [An escalation has no closer](an-escalation-has-no-closer.md) — ⭐ only a REPLY closes it; work that MOOTS it leaves it standing
- [⭐ Extract and RUN a plan's code](extract-and-run-a-plans-code.md) — 39 extracted, 2 failed, read past by 3 reviewers
- [A doc inside the corpus it measures](a-document-inside-the-corpus-it-measures.md) — its counts are stale at commit time, structurally
- [After fixing, SEARCH for the class](after-fixing-search-for-the-class.md) — ⭐ 4 instance-not-class defects in ONE slice
- [Assert the PROPERTY, not the mechanism](assert-the-property-not-the-mechanism.md) — ⭐ naming the fix's own tokens defends only its deletion
- [Conventions catch what you READ](a-convention-catches-what-you-read.md) — ⭐ convention + fixing what you noticed = it's mechanical
- [Check the assumption, not the code](check-the-assumption-not-just-the-code.md) — ⭐ MEASURE the constraint; 3× the framing itself was wrong
- [A finding's proposed FIX is a hypothesis](a-filed-finding-s-proposed-fix-is-a-hypothesis.md) — ⭐ #98's own rule would have false-fired on **10 of 18**
- [A shim fails BOTH ways](a-shim-can-fail-in-both-directions.md) — fixing the one name I saw = instance-not-class
- [Findings expire when the DENOMINATOR moves](a-costbenefit-finding-expires-when-the-denominator-moves.md) — ⭐ a seam INVERTED a Phase 6 verdict
- [⭐ Convergence ≠ the final-tree gate](review-convergence-is-not-the-final-tree-gate.md) — cost 2 rounds. The tree gate has 3 answers — enumerate them
- [Gates detect defects, not design](gates-detect-defects-not-design.md) — "is this correct?" is local; Phase 6 is the design gate
- [Read the target back UNCACHED](discover-the-target-and-read-it-back-uncached.md) — ⭐ `.env.local` points at LOCAL Supabase
- [A stated bound outlives its hole](a-stated-bound-outlives-its-hole.md) — ⭐ a test asserting a gap breaks when it CLOSES; the red is the alarm
- [Harnesses launder failures](test-harness-can-launder-failures.md) — catching "any error" passes on typos; assert WHICH
- [An instrument that edits the repo](an-instrument-that-edits-the-repo-corrupts-its-peers.md) — corrupts its peers; mutate a temp copy
- [Quote code, don't characterise it](quote-the-code-dont-characterise-it.md) — paste file:line or label it unverified
- [Hardcode only what fails loudly](hardcode-only-what-fails-loudly.md) — hardcode what announces its wrongness, DERIVE the rest

## Design & guard lessons

- [⭐ The apparatus outgrew its subject](the-apparatus-outgrew-its-subject.md) — guards+tests **4.4×** the product; repo budgets PROSE, never guards; a branch shipped 46 browser-visible lines of 2,633

- [One rule, one place](one-rule-one-place.md) — duplicate vocabulary shadows a duplicate mechanism; de-duplicating DROPS the clause the signature can't see
- [anon EXECUTE is the DEFAULT](anon-execute-is-the-default-not-a-decision.md) — ⭐ anon-callable unless someone remembers
- [RLS denial looks like absence](rls-denial-is-indistinguishable-from-absence.md) — same 404 both ways; the serve guard re-charged 6¢→12¢
- [Guards: SHAPE vs SEQUENCE](guard-classification-shape-vs-sequence.md) — what does it do when the caller is merely SECOND?
- [Unsatisfiable ordering is the tell](unsatisfiable-ordering-is-the-tell.md) — a green suite can describe an unreachable world
- [Operands from one stale closure](guard-operands-from-one-closure.md) — check the test reaches the BRANCH, not just the outcome
- [A fence wrong both ways](a-fence-wrong-both-ways-asks-the-wrong-credential.md) — fix the credential, never the threshold
- [Evidence paths have no allocator](a-guards-evidence-path-is-a-namespace-with-no-allocator.md) — ⭐⭐ TWICE: `--out` clobbered a committed verdict
- [Defined, not derived constants](defined-not-derived-constants.md) — "blocked by X" can be two claims in one sentence
- [Reservations guard spending](reservation-guards-spending-not-recording.md) — rejecting the loser's record discards paid work, prevents no cost
- [postgrest aborts return, don't throw](postgrest-abort-returns-not-throws.md) — race your own timer
- [`position` is not vestigial](position-column-is-not-vestigial.md) — check consumers per usage SITE, not per symbol
- [Blocked on a decision, not work](a-gate-can-be-blocked-on-a-decision-not-work.md) — M1.4's last two items weren't engineering
- [Detached dig retention](detached-dig-retention-decision.md) — retiring a rule dissolved a review High with zero code change
- [Serve-path bounding MERGED](serve-path-bounding-merged.md) — a single CONVERGED verdict was WRONG 4 of 5 times
- [CANDIDATE stopping rule](stopping-rule-defect-class-shift.md) — ⏳ untested and partly falsified

## Working with me

- [⛔ A DECLARATION is not the act](a-declaration-is-not-the-act.md) — `--watching` only RECORDS a claim. Arm the Monitor FIRST, then declare. Measured: **43m blind on a red CI**, found only because the user asked about something else
- [⭐ A side job gets a NAME first](a-side-job-gets-a-name-first.md) — over ~5 calls or a tracked file → slug + branch BEFORE the first edit. One sentinel, so ANNOUNCE the swap
- [⏳ BANNERS + waiting lines carry a TIMESTAMP](waiting-lines-carry-a-timestamp.md) — ⭐ asked 2026-10-06, re-asked for BANNERS 2026-10-19: clock in the `▶` heading. I had shrunk the rule to its glyph
- [⏳ Show a WAITING SIGNAL, not prose](show-a-waiting-signal-not-prose.md) — asked for 2026-09-23: lead with `⏳ **Waiting** — <what>`; "still running" buried in a paragraph does not register
- [⭐ The user does NOT follow in real time](the-user-does-not-follow-in-real-time.md) — ⛔ banner BEFORE each step, format SETTLED 10-16: `## ▶ [mm-dd hh:mm] STEP n of N` — prepended, no tz/seconds/`·`. Sub-steps too: `▸ [mm-dd hh:mm] 5.3 — …`. ⭐⭐ This LINE omitted the stamp for 3 days and I copied the line, not the file
- [⭐ A title is SCANNED, not read](a-title-is-scanned-not-read.md) — asked 2026-10-02: lead with the concrete SCOPE, then the finding. An essayistic title says what was LEARNED and hides what was TOUCHED. The body still argues
- [⭐ How to shape a message to me](how-to-shape-a-message-to-me.md) — LEAD with the conclusion, state READINESS separately from ownership, and ⛔ CLOSE with the repo's **CHECK/RESULT table** (`process-checklists.md`), never prose
- [⭐⭐ Never close with a promise](never-close-with-a-promise.md) — ⛔ **5th instance 2026-09-25.** The Stop guard EXISTS and was INERT — I never armed it. ARM `begin-plan.py` for review/fold loops too, not just implementation
- [⭐⭐ Blocking on a gate that does not EXIST](a-blocking-question-while-afk-costs-the-whole-night.md) — AskUserQuestion BLOCKS (6.5h idle, 2-line change). ⭐⭐ Worse 10-19: I cited "the owner's call" — **0 hits in 5 process docs** — and folded 5 rounds / 20h. GREP the rule and QUOTE it, or there isn't one
- [⭐ Putting a choice to the user](putting-a-choice-to-the-user.md) — TAG A/B/C + a question exit; never two options that are the SAME action; decide it yourself when obvious
- [⭐ Name and define every reference](name-and-define-every-reference.md) — never a bare `#39` or `M4`; gloss jargon on first use. Do NOT try to script it
- [⛔ PUSH is mine, MERGING is theirs](push-is-mine-merging-is-theirs.md) — ruled 2026-09-30; never ask again. A PR is a SEPARATE judgement — not for unconverged work
- [⭐ Defaults I decide myself](defaults-i-decide-myself.md) — small spend incl. a bounded prod write (measure the ledger); lighter verification. ⛔ NOT the CI wait — `--auto` is UNSAFE here, it once put a red on master
- [⭐ Restart Docker, do not record CANNOT RUN](restart-docker-dont-record-cannot-run.md) — user instruction 2026-09-22. A visible Docker Desktop window is NOT a responsive daemon; `open -a Docker` is a no-op and the backend needs SIGKILL
- [Process conventions](process-conventions.md) — branch + PR for EVERY change; spec = human gate; ticks in-convo, file at milestones; resume reads the RUNNING SYSTEM
- [⛔ Specs/plans are WALKED THROUGH, not approved](document-approval-is-interactive.md) — an interactive page they can question; a yes/no on a 243-line doc is a rubber stamp BY CONSTRUCTION, and Phase 1 is the ONLY human gate
- [⛔ EVERY decision is a selection card](print-selection-cards-in-chat.md) — ⛔⛔ **ALWAYS AskUserQuestion.** The user SKIMS; prose questions are NOT SEEN
- [⭐ "FIRST" can mean before-shipping](first-can-mean-first-before-shipping.md) — open the referenced item and quote ITS trigger
- [⛔ The Agent-tool restriction has NO owner](agent-tool-restriction-has-no-owner.md) — not the user's; audited to a dead end **4×**. Spawning the review half is PRE-AUTHORISED — stop asking
- [⛔ Dual review is the PROCESS](dual-review-is-the-process-not-a-request.md) — NEVER ask permission to run a half; only CANNOT-run is a decision
- [⛔⟳ ALIGNMENT, not approval](feedback-agree-before-filing.md) — ⭐ **REVERSED 2026-09-28**: file/amend backlog WITHOUT asking; wait ONLY if the GOAL is in question. Their attention is the scarce resource
- [Flag transitional choices](feedback-flag-transitional-choices.md) — label findings transitional vs structural
- [⭐ ALWAYS subagent-driven execution](always-choose-subagent-driven-execution.md) — standing answer; the skill keeps asking — answer it myself
- [⭐ A stacked PR dies with its base](a-stacked-pr-dies-with-its-base-branch.md) — `--delete-branch` on the parent CLOSES the child, and a closed PR's base CANNOT be changed
- [gh two-remotes footgun](gh-two-remotes-footgun.md) — ✅ RESOLVED; keep `--body-file`

## Environments & product context

- [⭐ Scoped mutation run in 4s](scoped-mutation-run-in-four-seconds.md) — 8 local shards TIME OUT → NOT MEASURED; `--shard` is round-robin and cannot isolate a file. Prune a COPY of HARNESS_TREE's SIX paths. ⭐ The harness is structurally browserless (`typescript` only → ERR_MODULE_NOT_FOUND)
- [Local cloud validation](local-cloud-validation-run.md) — local Supabase (:3001); worker needs env-load + Node 22+
- [Local manual-test env](local-manual-test-env.md) — `~/code/agentic-ai-docs/yps-sync-test/`; sync is ADDITIVE
- [Staging Supabase](staging-supabase-project.md) — ⚠ throwaway `neeufoxdbgbpkjukzzuc`; DELETE when B3/B4 done
- [Access tiers vision](access-tiers-vision.md) — free tier built; the billing layer is the gap
- [backlog.md stays Markdown](backlog-md-stays-markdown.md) — decided 2026-09-10; don't re-derive the JSON question
- [Cost per video](cost-per-video-analysis.md) — real Flash ≈8¢/video vs the 150¢ reservation

## Slice history

> ⛔ **NEW SLICE ROWS GO IN THAT FILE, NOT IN THIS INDEX.** This index is injected WHOLE on
> every turn and the harness truncates it in silence once it passes 24,985 CHARACTERS — measured
> 2026-10-19, it stood at 26,930 and **8 rows** had stopped arriving, with every other memory
> signal green. ⟳ Both the unit and the count are corrections: this said "bytes" and "~30 rows",
> and the real figures were established by reading the cut point out of a consuming agent's own
> injected context. `scripts/check-memory-index-budget.py` now fails on that, so this is enforced
> rather than remembered; a convention only catches what someone happens to read.

- [⭐ Slice history — every shipped slice, with PR + SHA](slice-history.md) — 28 rows, MOVED OUT of this index 2026-10-19. ⛔ Reached by TRIGGER now, not always-loaded — verified by firing: ask for a PR number or SHA and it returns. The index was 26,930 of a 24,985-CHARACTER budget; the 28 rows are **4,912** chars without line endings, 4,940 with one newline each (the whole section 5,990). ⚠ Two earlier versions were wrong: "6,232 of 27,805 bytes" (wrong unit, and it charged the rows with the whole SECTION's cost), then "4,985" (r2 CODEX #6 — that joined 29 `- ` lines, counting the "Older slices" bullet as a 29th row)
