---
name: concurrent-agents-go-wrong
description: "FIRES-WHEN: about to run two or more agents at the same time — ⭐ Everything measured about running agents concurrently: when it is safe, a reviewer returning the WRONG SUBJECT, a fork whose report never arrives, and two agents sharing one Postgres producing a FALSE BLOCKING. The RULE lives in docs/review-method.md"
metadata:
  type: feedback
---

> Merged 4 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `subagent-interference-open-question`, `a-reviewer-can-review-the-wrong-subject`, `a-forks-report-can-never-arrive`, `concurrent-agents-share-more-than-you-think`

## subagent interference open question

⭐ **THE RULE IS NO LONGER HERE. It is `docs/review-method.md` → "Running agents concurrently —
classify the OPERATION, not the agent"** (added 2026-09-09, backlog #67). Read it there. This memory
deliberately does **not** restate the table: a second copy of a safety table is a copy that drifts,
and that is the exact defect this row was filed for.

**What the section says, in one line, only so you know whether to open it:** a safe method exists and
is already implemented (per-run temp tree + `$HOME` redirect); file-only reviewers and
`check-plan-code.py --mutate .` are measured safe to run concurrently; three operations must be
serialised — Postgres **roles** (cluster-wide, clones do not isolate them), `git` in the main working
tree, and top-level `docs/reviews/` writes while a Codex run is in flight — and **none of the three
is mechanically enforced**.

## The durable lesson, which outlives the table

⭐ **A red observed on a shared resource is CONTAMINATION until re-measured ALONE.** Twice: 23/63 vs
63/63 alone, and 23/44 vs 44/44 on the same commit. **The near-identical ratio is the tell** — a
genuine defect does not usually reproduce as the same fraction twice.

⭐ **Concurrency safety must be OBSERVED, never inferred.** This row exists because the inference was
wrong twice. When `--mutate .` "should obviously be safe by the same argument as the reviewers", that
was not accepted either — two runs were launched together and the byte-identical verdicts recorded
before it was written down.

## Corrections this file previously carried, now resolved

- **The DB hazard is CLOSED** (2026-08-28): every writer is on a PID-suffixed scratch clone and the
  clone step is fail-closed — `mutate-live-schema-check.sh:164` prints
  `CANNOT RUN — could not build a pre-M4 base database. Treat this as NOT RUN.` and exits 2.
- **The "SILENT FALLBACK to shared `postgres`" residual is GONE**, and the code it cited
  (`mutate-schema.py:979-981`, `verify-schema.sh:90`) **no longer exists** — both scripts were
  deleted. Anything still describing that fallback is describing a fixed problem.
- **"The rule is written NOWHERE a dispatcher reads"** was true until 2026-09-09 and is now false.
  ⚠ It landed in `review-method.md`, NOT `plugins.md` as the row proposed: `plugins.md` is at exactly
  its 260-line budget and `check-docs.py` refused the addition. The guard was right about the file —
  `plugins.md` is read when choosing a skill; `review-method.md` is read when a review round starts,
  which is when two halves get dispatched. `plugins.md` carries a one-line pointer, zero net lines.
- **`pg_try_advisory_lock` was REJECTED by the user** and stays rejected: a writer-only lock does not
  protect readers, and extending it to readers would block `--prod` and `--database <scratch>` reads
  that cannot be corrupted — restriction bought with no safety.

## Still open (backlog, not here)

Rows **#92** (the Codex wrapper's intrusion detector misattributes writes) and **#103** (explainer
question monitors outlive their sessions) are separate defects in the same `(concurrency safety)`
bundle. Rows **#17 / #19 / #20** are product-pipeline races and each needs its own spec — they are
bundled by the user so the whole class is visible in one place, not because one change closes them.

Related: [[concurrent-agents-go-wrong]] ·
[[an-instrument-that-edits-the-repo-corrupts-its-peers]] · [[a-measurement-is-only-as-good-as-its-corpus]] ·
[[a-second-implementation-of-one-rule-drifts]]

## a reviewer can review the wrong subject

⭐ **A REVIEW HAS NO PROPERTY THAT DISTINGUISHES RIGHT-SUBJECT FROM WRONG-SUBJECT WORK.**
Measured 2026-09-09, `retire-plan-mode` round 3. A Claude-half subagent, briefed on branch
`retire-plan-mode` head `f9d2c498`, produced 27,489 bytes **byte-identical** (`diff` empty) to the
committed `docs/reviews/plan-project-dashboard-r3-claude.md` — a different plan, a different branch
(`docs/dashboard-plan-review`, `af9dccc`), different findings, different verdict. It then went idle
without ever sending a report.

**Why:** it was NOT empty, NOT a crash, NOT a timeout — each of which announces itself. It was
fluent, internally consistent, cited executed commands with plausible output, named real repo
paths, and closed with a confident `NOT CONVERGED` and six must-changes. Folded unread it would
have sent the next session to "fix" defects in files the branch never touches. This is distinct
from [[concurrent-agents-go-wrong]] (silence) — here the report ARRIVED and was wrong.

**How to apply:** brief every review subagent to open its report with a **PROOF OF SUBJECT** it
cannot produce by copying — the pasted live output of `git rev-parse HEAD`, `git log --oneline -1`,
and `git diff --stat <base>..<head>`. Discard any report that does not. Also forbid reading
anything under `docs/reviews/` (nothing there is the subject and nothing there is a template).
Read the artifact's FIRST LINE before reading its findings.

⚠ **It was caught only incidentally**, by an amendment made for a different hazard: the brief was
changed mid-flight to demand a FILE (per [[concurrent-agents-go-wrong]]), which put the
artifact in front of me early enough to check its header. Do not rely on that.

Same session, same shape one layer down — see [[a-report-format-is-a-contract]]: my own mutation
harness reported "14/14 OK" while two entries **crashed** the suite. It parsed for the named
`[FAIL]` line and never checked for a completion-summary line, and an uncaught exception also
exits 1. Two of the day's three instruments were broken and both looked fine; each was caught only
by evidence the mechanism could not itself generate — a `git status`, a summary line, a live
`git rev-parse`. See also [[an-instrument-that-edits-the-repo-corrupts-its-peers]] and
[[a-guards-evidence-path-is-a-namespace-with-no-allocator]], which fired the same day.

## a forks report can never arrive

**A fork's final report is not a reliable channel. Its ARTIFACTS are. Brief accordingly.**

On #91 (2026-09-08) I dispatched `verdict-rewire` to build the tagged union and measure the
mutation-anchor orphaning. It did the work — `91-rewire.patch` (110,922 bytes), a rewired tree whose
suite ran 195/195, a `RunContext` design, a `not_measured_reason` resolution. Then it emitted an
`idle_notification` with **no result payload**. I asked for the report explicitly. It went idle a
second time, again with nothing.

**Every finding it was dispatched to produce reached me only because I read its code and re-measured
myself.** Had I waited for the report, I would still be waiting.

## What to do instead

* **Put the deliverable in the brief as a FILE PATH, not a report section.** "Write your classified
  anchor table to `<path>.md`" survives an agent that never speaks again; "report `ANCHORS:`" does not.
  I did this for the diff — which is why the diff exists — and not for the findings, which is why
  they did not.
* **Reproduce the load-bearing measurement yourself regardless.** I re-measured the orphan count
  independently (12 orphaned / 23 in-place / 0 moved, over a control proving every anchor resolves
  uniquely in the delivered file). My own earlier *reading* had guessed ~13. The guess was close
  enough to have felt like confirmation if I had only ever seen the fork's number — which is the
  trap. See [[dual-review-what-it-catches]].
* **Read the fork's CODE for its design decisions.** Both open questions were answerable from
  signatures alone: `RunContext` at `:499`, `NotMeasured.reason` documented as "the rendered clause,
  WITHOUT the `NOT MEASURED — ` head". A report would have been a nicer summary of what the code
  already said.

## The part that generalises

This is the fork/parent split working as designed, not failing: the split says **verification is
never delegated**, and here the parent's verification was the only thing that produced findings at
all. The lesson is narrower and more mechanical than "don't trust agents" — it is that the
*transport* can drop, so **design the handoff around durable artifacts**, exactly as this project
already does for handoffs, reviews and evidence blocks.

Related: [[an-instrument-that-edits-the-repo-corrupts-its-peers]] (I verified the real repo stayed
clean throughout — `git status --porcelain` empty, and the fork's 6 `coverage_verdict` references
were all confined to its scratch tree).

## concurrent agents share more than you think

⭐ MEASURED 2026-08-26, twice in one day, at two different layers.

**Layer 1 — the database.** Round 8's two review halves both ran `mutate-schema.py`, which works
inside the **shared `postgres` database**. Codex measured `23/63` and *"baseline restored: STILL
BROKEN"* and filed `verify-schema.sh` red as a **Blocking finding**. Re-measured minutes later,
alone: `63/63`, verify-schema green, database clean. The finding was contamination, not a defect.

That is [[an-instrument-that-edits-the-repo-corrupts-its-peers]] one layer out — and note the
numbers: last time it was 23/44 vs 44/44, this time 23/63 vs 63/63. **The same near-identical ratio
should be the tell.**

**Layer 2 — the working tree.** A `/brief` agent ran `git stash` / `git stash pop` in the repo while
I was mid-edit and committing. It completed cleanly (stash list empty, content intact, verified) but
it was luck, not design: a stash during my `git add -A` would have silently taken my uncommitted
work into a stash I did not know existed.

**Also cluster-wide, not just per-database:** a reviewer's `grant service_role to anon` changed
`pg_auth_members`, which altered `has_table_privilege('anon', …)` in the shared database and every
clone at once — garbaging a result table before anyone noticed.

**Layer 3 — I CREATED a collision by replacing a silent agent. MEASURED 2026-08-29.** An implementer
went idle without reporting. I checked `git log`, saw no commit, concluded nothing had happened, and
dispatched a replacement onto the same file. It had in fact already written the fix — **sitting
uncommitted in the working tree, invisible to `git log`.** Two implementers, one file. It cost
nothing only because both produced byte-identical content and `git commit` reported *"nothing to
commit"* rather than creating a duplicate; the loser then had to be told **not** to "tidy up", since
`git stash` / `git checkout -- .` by the losing agent is how the winner's work dies (layer 2).

**An idle agent is not a dead agent, and `git log` is not the working tree.** Before replacing a
silent agent: `git status` AND `git diff`, not `git log` alone — or get an explicit stand-down.
A stand-down message must also forbid unilateral cleanup and ask what is in the tree first.

**How to apply.**
- Serialise reviewers, or give each an enforced scratch prefix — and say so IN THE BRIEF, because a
  reviewer told to "verify by execution" will reach for the shared harness.
- **Never dispatch a replacement for a silent agent on `git log` evidence alone.** Its work may be
  written and uncommitted. Check the tree.
- Before believing a reviewer's red on a shared resource, **re-measure alone**. Two runs of the same
  harness disagreeing is contamination until proven otherwise.
- A subagent that can run `git` can move MY uncommitted work. Give read-only reviewers no reason to
  touch the index, and commit before spawning anything that might.

Related: [[a-hang-is-not-a-diagnosis]] (a single observation of a shared thing is not a diagnosis),
[[test-harness-can-launder-failures]].


## ⭐⭐ 2026-09-21 — A LIVE AGENT'S FILE IS NOT STATIC, and it cost TWICE in one session

The rule above already names *`git` in the main working tree* as one of the three operations that
must be serialised and that nothing enforces. Both failures below are that row being paid for.
Neither corrupted anything, neither raised: **the commits were clean, the pushes succeeded, and a
gate two steps later caught each one.** That is how this class presents.

**Costume 1 — I APPENDED to a review its author was still writing.** A handoff described
`closing-table-r7-claude.md` as an abandoned 27-line skeleton. I read it at **145 lines**, saw it end
`_(continued)_` with no verdict, concluded it had died mid-sentence, appended a verification section,
and committed. The agent was alive. Its final `Write` replaced the whole file with the finished
**338-line, 7-finding** version and my section vanished. It was never in the commit.

⚠ **The tell I misread: a FRESH MTIME IS AMBIGUOUS.** It was seconds old. That is equally
"stopped just before the boundary" and "writing right now" — and I picked the reading that matched
the handoff. ⭐ **A handoff's description of a file is a SNAPSHOT, and it is stale the moment the
file is still being written.** `wc -l` was run once and believed for hours.

**Costume 2 — `git add -A` PUBLISHED a review its author was still writing.** Three hours later,
the *same* agent was 25 lines into r8. My `git add -A` swept the skeleton into a commit and pushed
it. CI went red, correctly: *"closing-table round 8: only claude"*. A half-written review filed as a
round **is** a round with one half. Un-tracked, not deleted — the agent kept writing on disk.

⭐ **THE DURABLE FIX IS MECHANICAL, NOT ATTENTIONAL. `git add -A` is a claim about a working tree
another process is mutating.** While a subagent is live, stage EXPLICIT PATHS. Knowing the rule did
not prevent either costume; I had read this very memory earlier in the same session.

⭐ **And the positive result, which is the one to keep:** the deliverable-is-a-FILE brief WORKS. The
agent never reported back — it went idle twice — and its complete 338-line review survived anyway,
which is the whole thing the previous session's lost attempt was trying to buy.
⛔ **But it buys SURVIVAL, not COMPLETION.** Nothing in it tells you when the file is finished.
**Treat an untracked review file from a possibly-live agent as append-only by its author:
`git add <explicit path>` and diff before touching it — never append, never `-A`.**

See also [[an-instrument-that-edits-the-repo-corrupts-its-peers]],
[[a-retrospective-number-needs-provenance]] (the handoff's stale claim),
[[a-check-result-is-not-the-claim]] (the red that hid the next gate).
