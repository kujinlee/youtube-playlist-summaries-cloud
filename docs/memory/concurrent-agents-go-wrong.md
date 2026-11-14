---
name: concurrent-agents-go-wrong
description: "FIRES-WHEN: about to run two or more agents at the same time, replace a silent agent, stage files while an agent is live, or trust a red seen on a shared resource — ⭐ Everything measured about running agents concurrently: when it is safe, a reviewer returning the WRONG SUBJECT, a fork whose report never arrives, and two agents sharing one Postgres producing a FALSE BLOCKING. The RULE lives in docs/review-method.md"
metadata:
  type: feedback
---

**CURRENT RULE (owner 11-13 21:54/21:55, until backlog #641 closes): never run two agents in parallel whose PRs can touch the same file** (in practice any two that add a dashboard entry or a backlog row) — "inconvenient but effective". Parallel only when their changed files are disjoint. I also MERGE one PR at a time and re-merge master into the next only after its predecessor lands. **Why:** each merge made the others conflict and restart CI; 11-13 that cost 47% of two agents' tokens (backlog #641, PR #584).

**The safety table is NOT here** — it is `docs/review-method.md` → *Running agents concurrently — classify the OPERATION, not the agent* (backlog #67). One line so you know whether to open it: file-only reviewers and `check-plan-code.py --mutate .` are measured safe concurrently; three operations must be serialised — Postgres **roles** (cluster-wide), `git` in the main working tree, top-level `docs/reviews/` writes during a Codex run — and **none of the three is mechanically enforced**.

**How to apply (each line is a measured failure, below):**
- **A red on a shared resource is CONTAMINATION until re-measured ALONE.** A near-identical ratio across runs is the tell.
- **Concurrency safety is OBSERVED, never inferred** — launch two runs together and compare before writing "safe".
- **Brief every review subagent to open with a PROOF OF SUBJECT** it cannot copy: live `git rev-parse HEAD`, `git log --oneline -1`, `git diff --stat <base>..<head>`. Discard a report without it; forbid reading `docs/reviews/`. Read the FIRST LINE before the findings.
- **The deliverable is a FILE PATH in the brief, not a report section** — the transport can drop; the artifact survives. Re-measure the load-bearing number yourself regardless.
- **An idle agent is not a dead agent, and `git log` is not the working tree.** Before replacing a silent agent: `git status` AND `git diff`, or an explicit stand-down that forbids cleanup.
- **While any subagent is live, stage EXPLICIT PATHS — never `git add -A`, never append to its file.** A fresh mtime is ambiguous ("just stopped" = "writing now").
- **After you MESSAGE an agent, its tree is LIVE again** until its next report; put a late addition in the NEXT round, never edit alongside it.
- **Brief a review by the branch HEAD at launch** (`git rev-parse HEAD`), never a SHA a watchdog reported earlier; re-read HEAD after the agent reports. Before diagnosing a red in a subagent's worktree, confirm it is idle or use a pinned `git worktree add --detach <sha>`.
- **A "waiting" idle notification from a subagent means STALLED** — check its processes/worktree at once. Brief: long jobs foreground with no single call over ~270 s, never end a turn on a waiting line ([[agent-blocking-call-over-5-min-rewrites-its-cache]], [[a-waiting-line-must-measure-age]]).
- **Give a Claude review half a NARROW mandate**; leave exhaustive sweeps to Codex or run them yourself and hand over the output. Record `REVIEW GAP: claude` rather than wait.

> Merged 4 memories. Former names (still referenced by other memories): `subagent-interference-open-question`, `a-reviewer-can-review-the-wrong-subject`, `a-forks-report-can-never-arrive`, `concurrent-agents-share-more-than-you-think`

## History

**Shared database, 2026-08-26.** Round 8's two review halves both ran `mutate-schema.py` in the shared `postgres` database. Codex measured `23/63` and *"baseline restored: STILL BROKEN"* and filed a **Blocking**; re-measured alone minutes later: `63/63`, clean. Earlier the same shape: 23/44 vs 44/44. Also cluster-wide: a reviewer's `grant service_role to anon` changed `pg_auth_members` and altered `has_table_privilege('anon', …)` in every clone at once. Related: [[an-instrument-that-edits-the-repo-corrupts-its-peers]], [[a-hang-is-not-a-diagnosis]], [[test-harness-can-launder-failures]].

**Resolved since:** the DB hazard CLOSED 2026-08-28 (PID-suffixed scratch clones, fail-closed: `mutate-live-schema-check.sh` prints `CANNOT RUN — could not build a pre-M4 base database. Treat this as NOT RUN.` and exits 2). The "silent fallback to shared `postgres`" code (`mutate-schema.py`, `verify-schema.sh`) was deleted. The rule landed in `review-method.md` 2026-09-09, not `plugins.md` (at budget; `check-docs.py` refused). **`pg_try_advisory_lock` was REJECTED by the user** and stays rejected: a writer-only lock does not protect readers, and extending it would block `--prod`/scratch reads that cannot be corrupted. Still open in the `(concurrency safety)` bundle: backlog #92, #103; #17/#19/#20 are product-pipeline races needing their own specs.

**Working tree, 2026-08-26.** A `/brief` agent ran `git stash`/`pop` while I was mid-commit — clean only by luck; a stash during my `git add -A` would have taken my uncommitted work.

**Replacing a silent agent, 2026-08-29.** An implementer went idle; `git log` showed no commit; I dispatched a replacement onto the same file. The first had already written the fix, uncommitted. Harmless only because both produced byte-identical content; the loser had to be told not to "tidy up".

**Wrong subject, 2026-09-09** (`retire-plan-mode` r3). A Claude half briefed on head `f9d2c498` produced 27,489 bytes **byte-identical** to the committed `plan-project-dashboard-r3-claude.md` — different plan, branch, findings — fluent, confident `NOT CONVERGED` with six must-changes, then went idle without reporting. Caught only incidentally because a mid-flight brief change demanded a file. Same day, my own harness reported "14/14 OK" while two entries crashed the suite ([[a-report-format-is-a-contract]], [[a-guards-evidence-path-is-a-namespace-with-no-allocator]]).

**Fork report never arrived, 2026-09-08** (#91). `verdict-rewire` produced `91-rewire.patch` (110,922 bytes, suite 195/195), then idled twice with no payload. Every finding reached me because I read its code and re-measured (12 orphaned / 23 in-place / 0 moved; my earlier guess ~13 would have felt like confirmation). Verification is never delegated; design the handoff around durable artifacts. See [[dual-review-what-it-catches]].

**A live agent's file, 2026-09-21 — twice in one session.** (1) A handoff called `closing-table-r7-claude.md` an abandoned skeleton; I read it at 145 lines ending `_(continued)_`, appended, committed. The agent was alive; its final `Write` produced the 338-line, 7-finding version and my section vanished. (2) Three hours later `git add -A` swept the same agent's 25-line r8 skeleton into a pushed commit; CI went red (*"closing-table round 8: only claude"*). I had read this memory earlier that session — the fix has to be mechanical. The file-deliverable brief WORKED (the 338-line review survived two idle-outs) but buys survival, not completion. See [[a-retrospective-number-needs-provenance]], [[a-check-result-is-not-the-claim]].

**Stalled "waiting" subagent, 2026-10-27.** `fixture-isolation-impl` ended its turn twice on "⏳ Waiting for <its own background job>" — 2½h lost, then ~10 min. The user asked "you don't use heartbeat mechanism?" Same day the watchdog fired on the first commit, the agent AMENDED it (747b88d8 → 133d08b1), and I briefed Codex with the superseded SHA. 10-28 00:38: three scans of a worktree disagreed because `b3b988ab` landed mid-search. 10-28 02:10: a Claude half told to run heavy probe sweeps filed nothing twice on PR #424 (r1 ran 2h32m; r3 ignored a 20-min draft deadline and a 60-min box). Related: [[a-declaration-is-not-the-act]].

**A report is not the end, 2026-10-30.** `fold-443-r2` reported at 13:28; my SendMessage with F9 woke it and it committed at 13:29; I had edited the same row in its tree that minute, and its `git add` split the row into 8 cells.
