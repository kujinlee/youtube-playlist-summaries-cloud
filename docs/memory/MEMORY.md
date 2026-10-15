# Memory Index

> One line per memory. ⛔ **CORRECTED 2026-09-28: NOTHING DECIDES RELEVANCE.** This line used to say *"the hook decides relevance"* and that was never true — measured: no file in the `remember` plugin references `MEMORY.md` at all, and all **133** rows arrive every session, unfiltered. **So every row below is always in context and none of them is ever matched to the moment** — which is why recall fails here, and why the hook's title has to do the matching by itself. Write each hook as the SITUATION you would be in, not the subject it is about (backlog #191).

- [⭐ RESUME: anchors + stable ids](anchor-name-and-stable-id-handoff.md) — M4 MERGED (#155); `0027` LIVE ON PROD. The stable-id roadmap **EXISTS** — I once re-derived it wrongly
- [⭐ Launch roadmap](launch-roadmap-state.md) — **START HERE.** M1+M2+M3 closed. Prod ops + `claude_ro` recipe
- [⭐⭐ #191 — semantic recall REPLICATED](backlog-191-semantic-recall-replicated.md) — lexical **3/20** vs semantic **20/20**, 0 false fires in 60. Triggers GOOD, matcher was the problem. 2 branches, neither merged
- [TWO deliverables + the 3→2 mapping](project-has-two-deliverables.md) — ⭐ **2026-10-15 owner RULED: goal (1) comprehensibility → D2, and REGISTER it — the `roadmap:2355` goal change is spent**

## How things go wrong here (⭐ = costly, recurring)

- [⭐⭐ Verify the OTHER copy exists before deleting](verify-the-other-copy-exists-before-deleting.md) — ⛔ I `rm`'d the ONLY copy of a 40KB page: `~/explainers` is a **symlink INTO** `docs/explainers` — one file, **UNCOMMITTED**. ⛔⛔ **NOTHING HERE MAKES DELETING SAFE — 3 rules in 3 rounds said *safe* while deleting destroyed the only copy.** You can only OBSERVE that HEAD held these bytes a moment ago (`git rev-parse HEAD:$A` vs `git hash-object $A`); A can change before the `rm`. ⭐ Can't lose it? **`mv` it aside, don't delete.** ⭐ RECOVER from `subagents/*.jsonl`: scan Bash `command`, not just Write `file_path`
- [⭐⭐⭐ A check result isn't the claim](a-check-result-is-not-the-claim.md) — ⭐⭐⭐ **a control proves the instrument RAN, never that the PATTERN was right**: 3 zeros in one day (case, markup, word order). Enumerate the SUBJECT, narrow, judge each. ⭐ Never read `$?` after a PIPE
- [⭐⭐ An inference stated as MEASURED](an-inference-stated-as-measured.md) — **3× in ONE document**, each caught by the NEXT round, never me. The fix is PARAGRAPH STRUCTURE, not "verify agent output" — a cost figure invented to support a sound argument is the tell
- [⭐⭐ A retrospective number needs provenance](a-retrospective-number-needs-provenance.md) — recall is fiction and THE CORRECTIONS FAIL TOO (**0 for 5**). DERIVE; cite the SYMBOL, not the line
- [⭐⭐ Concurrent agents go wrong](concurrent-agents-go-wrong.md) — the WRONG SUBJECT, a report that never arrives, one Postgres → a FALSE BLOCKING. ⭐⭐ **A LIVE AGENT'S FILE IS NOT STATIC** — cost TWICE in one night (appended to it; `git add -A`'d it). Stage EXPLICIT PATHS. RULE in `docs/review-method.md`
- [⭐⭐ An anchor is unbound by ANY nearby edit](a-mutation-anchor-is-unbound-by-any-edit-nearby.md) — 7 orphaned in ONE session; one was a BLOCKING red CI step. Use the HARNESS's own rule, over EVERY manifest
- [⭐⭐ "Cannot die" may mean a SECOND clause](cannot-die-may-mean-a-second-clause.md) — I deleted on that reading TWICE in two commits; both reversed by the next review. **4 masking pairs in one file.** Construct an input, and ask what ELSE answers this
- [⭐ A mutation loses its binding](a-mutation-loses-its-binding.md) — anchors bind by TEXT, so a refactor ORPHANS them; promoting one drops its fake-`HOME` redirect
- [What mutation testing proves](what-mutation-testing-proves.md) — load-bearing, never complete; a MUTATION can be masked like a fixture
- [⭐⭐ A sever: TODAY's value, and the exact SPOT](a-sever-substitutes-todays-value.md) — ⭐⭐ **placement IS the claim**: 2 indent levels moved my repro 299→300, i.e. refute→confirm
- [⭐⭐ Unit coverage does NOT compose](unit-coverage-does-not-compose.md) — 3 rounds, 3× the gap was BETWEEN two tested pieces. **Mutate the CALL SITE** — the whole change reverted there, suite green
- [⭐⭐ A forced-choice test cannot fail](a-forced-choice-test-cannot-fail.md) — must-fire-only is UNFALSIFIABLE; negatives must be ADJACENT, not absurd. State the BOUND (0 in 60 → 5%), never "no false positives"
- [⭐ Instruction is not isolation](instruction-is-not-isolation.md) — "read only these two files" is not a blind; the answer key was in the same directory. Rebuild the world, don't ask
- [⭐ A BOUND enumerates what is WITNESSED](a-bound-enumerates-what-is-witnessed.md) — I listed what the seam TOUCHES; the cases covered 3 of 4. The missing one reinstated the defect the harness exists for. ⚠ A caveat headed "stated rather than hidden" that is wrong is worse than none
- [⭐⭐ A test that cannot fail — or ALREADY DID](a-test-that-cannot-fail.md) — ⭐⭐ run the FAILS IF **against HEAD as you write it** (#282, #289 both wrong about their own); ⭐⭐ and **stating a falsifier is not running it** — mine passed
- [⭐⭐ Ask an agent to REFUTE, not confirm](ask-an-agent-to-refute-not-confirm.md) — 4-for-4 on 2026-09-23: the refuting prompts caught a wrong correction I had ALREADY PUBLISHED; the confirming one shipped a summary contradicting its own table. ⚠ The gap is VERIFICATION/RESEARCH agents — review halves already have a mandate (33 docs); I claimed otherwise without grepping
- [⭐ Dual review: what it catches](dual-review-what-it-catches.md) — halves NOT redundant; the finding-reviewer right 3/3; ⭐ and **review is the wrong instrument for a SURFACE** — 6 rounds ≈ 7 edge cases, one corpus run ≈ 5,287
- [⭐⭐ Running Codex](running-codex.md) — a "timeout" is MY `--timeout`: DOUBLE it (900s default, 2700-3600 for big reviews). Run from the coordinator
- [It exists under a name I didn't search](it-already-exists-under-a-name-i-didnt-search.md) — ⭐ 3× in ONE day. Check before proposing to BUILD
- [Parallel branches, ONE log](parallel-branches-append-to-one-log.md) — ⭐ 3 same-day PRs: #1 clean, rest CONFLICT
- [A report format is a CONTRACT](a-report-format-is-a-contract.md) — ⭐ "0 red cases" over a shape the harness can't parse
- [⭐⭐ Negatives by INTERCEPTION can't terminate](proving-a-negative-by-interception-cannot-terminate.md) — FIVE unearned passes. PRE-COMMIT the retreat
- [⭐⭐ More evidence WEAKENS substring cases](printing-more-evidence-weakens-substring-cases.md) — the traceback supplies the token the case credited to the rule. **3rd 2026-10-14**; inverted: my docstring fed my own assert
- [Passing for an AMBIENT reason](a-case-can-pass-for-an-ambient-reason.md) — ⭐⭐ 4× on one file. BUILD the world; run 3 ways
- [⭐⭐ Two DISTINCT inputs, in ONE case](exercise-the-producer-at-two-distinct-inputs.md) — a case is satisfied by the CONSTANT its own fixture supplies. 3 rounds, 9 survivors; pairwise-distinct FIXTURES are the weaker rule that already failed
- […and a CORPUS](a-measurement-is-only-as-good-as-its-corpus.md) — ⭐ 4×. Code did what I measured; I measured the wrong SET
- [Measure what the CODE sees](measure-the-population-the-code-actually-sees.md) — ⭐⭐⭐ **11×, SIX in one session**: before you trust a NEGATIVE, check a KNOWN POSITIVE. A correct run can answer about the wrong subject
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
- [A second implementation DRIFTS](a-second-implementation-of-one-rule-drifts.md) — ⭐⭐ **17×**: about to re-implement a rule a guard already owns? IMPORT it — a weaker stand-in passes what it would REFUSE
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
- [⏳ A waiting line carries a TIMESTAMP](waiting-lines-carry-a-timestamp.md) — asked 2026-10-06: `⏳ **13:25 PDT** — …`, with the START not just the duration. "~25 min" is unreadable an hour later
- [⏳ Show a WAITING SIGNAL, not prose](show-a-waiting-signal-not-prose.md) — asked for 2026-09-23: lead with `⏳ **Waiting** — <what>`; "still running" buried in a paragraph does not register
- [⭐ The user does NOT follow in real time](the-user-does-not-follow-in-real-time.md) — plain words, a `## ▶ STEP n of N` banner BEFORE each step, and a live progress line for background work. ⭐⭐ **3rd lapse 2026-09-23: a step that GREW to 12 findings stayed "step 5" for 20 tool calls.** Sub-divide with a ONE-LINE `▸ 5.3 — …` marker; the trail is DATA for a future workflow view
- [⭐ A title is SCANNED, not read](a-title-is-scanned-not-read.md) — asked 2026-10-02: lead with the concrete SCOPE, then the finding. An essayistic title says what was LEARNED and hides what was TOUCHED. The body still argues
- [⭐ How to shape a message to me](how-to-shape-a-message-to-me.md) — LEAD with the conclusion, state READINESS separately from ownership, and ⛔ CLOSE with the repo's **CHECK/RESULT table** (`process-checklists.md`), never prose
- [⭐⭐ Never close with a promise](never-close-with-a-promise.md) — ⛔ **5th instance 2026-09-25.** The Stop guard EXISTS and was INERT — I never armed it. ARM `begin-plan.py` for review/fold loops too, not just implementation
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

## Slice history (all MERGED unless noted — open the file for PR/SHA)

- [⭐⭐ recall fold — PR #360 MERGED](recall-fold-360-merged.md) — `5128b99b`, **merged NOT CONVERGED with 3 Highs open**. 9 rounds; each fix CREATED the next instance. ⭐⭐ The fix was already in the repo at `check-ci-watched.py:860` and reached **zero** siblings → ADR-0014
- [⭐⭐ backlog #154 — PR #331 READY](backlog-154-dash-scalar-ready-331.md) — `0791ca6f`, **not merged**. EIGHT rounds, each a NEW GRANULARITY (line→node→document→key-depth). Fix changed KIND: **refuse, don't widen**. ⭐ My class-fix made 6 mutations UNKILLABLE, suite green — only the sweep saw it
- [⭐ arch review #153 — PR #329 READY](arch-review-153-workflow-readers.md) — `ccff9878`, **not merged**. Verdict: extract `_structural()`, NOT parse. Found a **LIVE false green** → #154 first. 4 rounds; #155 SIZE NOT KNOWN → size by ATTEMPTING
- [M4 superseded trail](m4-superseded-trail.md) — history only, split out of the RESUME file when it outgrew the read limit. Fork (a), `0028` cannot be a migration, Phase 6 ran TWICE
- [⭐⭐ pin-python — #317](pin-python-317-merged.md) — `e7ed8c1a`. **TEN defects, ONE function, 7 rounds**, all one root cause. ⭐ I tested the CONTAINER's shape not its CONTENTS (2×); a fix landed at the WRONG LAYER (2×); my pre-committed falsifier FIRED
- [⭐⭐ closing-table r7–r11 — #327 + #328](closing-table-r7-r8-merged-327.md) — the independent read #325 shipped without. 16 findings/5 rounds. Marker fired on **96.7%→49%**, false-sentence firings **372→0**. ⛔ `check-review-recorded` keys on CODEX VERDICTS, not commit order — 2 of 5 reds
- [⭐ merge-ready + budget slack — #324](merge-ready-slice-merged-324.md) — `af4d9033`. About to judge a PR? Run `check-merge-ready.py` (the PR-only gates), never a gate subset — skipping it put TWO PRs red
- [⭐ Wake-on-visit — #322](wake-on-visit-merged-322.md) — `e693f36a`. Worker sleeps/wakes, own Fly app NO public IP. INERT except the drain-key fix
- [Lease-sweep cadence — #318](lease-sweep-merged-318.md) — ⭐ `35cf44c6`. Idle worker was **100%** of prod DB traffic. Found 🔴 **#139**; `fly.toml` drift reverts it
- [#137 schema-gates REQUIRED — #315+#316](schema-gates-required-137-merged.md) — ⭐ `[verify, schema-gates]` live. The deleted filter had a SECOND CONSUMER (#138)
- [peer-sites — #313](peer-sites-merged-pr-313.md) — `14063fe5`. Ships with NO caller by design (#134). ⛔ `NO-REVIEW:` must start the line
- [#122 manifest seeded — #311](seed-manifest-122-merged.md) — 42 entries, 7 live defects. ⛔ Codex timed out ALL 3 rounds; #129/#130 open
- [Split #295: /src/ half — #310](split-295-src-root-merged.md) — ⛔ #295 STILL OPEN, do NOT merge as-is; restart half parked
- [Guard-ratchet scope — #298](guard-coverage-scope-merged.md) — ⭐ saw 41 guards, ignored 14 on tables it BUILDS; now has a falsifier
- [Schema gates in CI — #297](schema-gates-in-ci-merged.md) — ⭐ 15 gates, 93s, zero added wall clock. ⛔ nightly cron UNARMED
- [#91 coverage-verdict union — #269](coverage-verdict-union-91-merged.md) — ⭐ 374 mutations / 0 survivors
- [Selection-card guard LIVE](selection-card-guard-built.md) — ⭐ a hook REFUSES a malformed card. Its 2 rounds found **4 Blockings**
- [#110 parser completeness](backlog-110-parser-completeness-merged.md) — ⭐⭐ BOTH Blockings were the row's own defect, reintroduced by its fix
- [Retire plan mode — #270+#271](retire-plan-mode-merged.md) — ⭐ 3,607 → 2,013 lines. The only sanctioned ratchet FALL
- [Ask-choices — #186](dashboard-ask-choices-merged.md) — ⭐⭐ **CONSENSUS IS NOT VERIFICATION**: all three agreed, `git diff` refuted
- [Page chrome seam — #185](page-chrome-seam-merged.md) — ⭐ theme+provenance on all five page producers
- [HOME-redirect — #181](mutation-harness-home-redirect-state.md) — ⭐ `$HOME` governs `Path.home()` and a bare `~`, **NOTHING else**
- [Inline renderer seam](inline-renderer-seam-merged.md) — ⭐ ONE renderer, four pages; the sum HELD at 73
- [Fixing a PREMISE ≠ covering the BRANCH](fixing-a-premise-is-not-covering-the-branch.md) — ⭐⭐ **12 unfalsifiable cases across 8 guards**
- [Mutation-manifest retarget](mutation-manifest-retarget-merged.md) — ⭐ `--mutate .` mutates DELIVERED scripts
- [Link-contrast slice](link-contrast-slice-merged.md) — ⭐ shipped UNREVIEWED; 2 rounds then found 6 defects
- [Integration suite skips migrations](integration-suite-does-not-apply-migrations.md) — ✅ FIXED (#46). A GREEN gate on the wrong schema is worse than none
- **Older slices, all MERGED unless marked:**
  [Stage 3 cloud-sync](stage3-cloud-sync-branch-state.md) (honest-blob-read open) ·
  [Blob addressing](blob-addressing-spec-state.md) ⏸ PARKED, round 10 mandatory if unparked ·
  [Worker-vs-sync fencing](worker-vs-sync-fencing-gap.md) · [Serial coherence](serial-coherence-slice-state.md) ·
  [Reservation release](reservation-release-slice-state.md) · [Section timestamps](summary-section-timestamp-guarantee-state.md) ·
  [Dig frontend](cloud-dig-deeper-frontend-state.md) · [Dig serving](cloud-dig-serving-branch-state.md) ·
  [Sidebar UX](playlist-sidebar-ux-branch-state.md) · [Summary PDF](cloud-summary-pdf-slice-state.md) ·
  [Frontend sub-project](frontend-subproject-design-state.md) · [Stage 2 autonomy](stage-2-batch-autonomy-plan.md) ·
  [1G](stage-1g-design-state.md) · [1F-c](stage-1f-c-design-state.md) · [1F-b](stage-1f-b-design-state.md) ·
  [1F-a](stage-1f-a-design-state.md) · [1D](stage-1d-merged-followups.md)
