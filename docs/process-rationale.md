# Process Rationale — why the rules exist

**Read on demand, not loaded into context.** `docs/dev-process.md` holds the *rules* and stays short
because it is `@`-included in every session. This file holds the *evidence* behind them.

**Read this when:** a rule in `dev-process.md` looks arbitrary, expensive, or wrong; you are about to
skip one; you are about to "simplify" one away; or a review finding looks like something the process
already claims to prevent.

The general lesson across every incident below: **the code was locally correct everywhere and wrong in
composition.** Rules that only inspect one module at a time cannot catch that class.

---

## Cross-module nullable/union values → the "value semantics" behaviour category

**Incident — Stage 3 cloud-sync (2026-07-18), 1 Blocking + 3 High, all one shape.**

The plan specified, and 6 rounds of dual plan review passed:

```
decideCompanion(args: { winnerMdHash: string; senderEnvelope: ModelEnvelope | null })
→ "ship iff senderEnvelope.sourceMdHash === winnerMdHash; else delete the receiver's model"
```

The code implemented it faithfully. The **type** was wrong: `readModelEnvelope` returns `null` for
*absent*, *corrupt*, **and** *unreadable*, because `SupabaseBlobStore.get` is `if (error) return null`
— swallowing 404, 5xx, timeout and RLS denial alike. `LocalFsBlobStore.get` nulls only on `ENOENT`.
So the two backends disagree about what `null` means, and "null → delete" destroyed paid artifacts on
a transient network blip.

Same shape, three more times:
- **B1 (Blocking):** an unreadable MD body read as "this replica holds no MD" → the healthy replica's
  body was overwritten and its `docVersion` downgraded, then laundered into an agreed baseline. Silent
  and unrecoverable.
- **H3 (High):** `playlist_title: meta.playlistTitle ?? null` — omitting an optional title *erased* it.
- **serve-doc.ts (money path, pre-existing):** a storage blip makes an existing model look absent →
  `reserve_serve_model` → paid regeneration of something already paid for.

**Why the table's third column ("produced by") is the point:** the producer usually lives in a
different file from the type you are writing. You cannot see the ambiguity by reading the consumer.

**Why "make the type honest" beats "remember to check":** the branch shipped a `provesAbsence` flag,
which works only if the next caller remembers to consult it — and it does not propagate, so the same
defect remained live in serving code outside the reviewed scope. A discriminated result
(`{ok:true,…} | {ok:false, reason:'absent'|'unreadable'}`) is enforced by the compiler at every call
site forever, including by people who never heard of this incident. See the *honest-blob-read slice*
in `docs/roadmap-to-launch.md`.

---

## Mutation-check every guard

**Incident — Stage 3 cloud-sync.** The round-1 WB-H1 fix shipped with a passing integration test that
asserted the right things — for a single run. The bug only manifested on the *second* sync, so the test
passed identically in the buggy and fixed worlds. Round 2 found the defect still live.

Later, mutating the H3 fix's third defence layer (deleting it) failed **zero** of 40 passing
integration tests: that layer had no coverage at all, and both reviewers then independently confirmed
it was unreachable dead code. It was removed.

**Why it is a checklist line and not advice:** it needs no judgement, memory or expertise — it is a
command with a pass/fail. It is the only step in the per-task list with that property.

**Commit before mutating:** `git checkout` to undo a mutation also reverts an uncommitted fix. Learned
by doing exactly that.

---

## List the consumers at fix time

**Incident — Stage 3 cloud-sync produced 3 self-inflicted follow-on defects**, one per fix round, all
the same mistake: reasoning carefully about the module being edited and not about its readers.

| Fix | State whose meaning changed | Consumer missed |
|---|---|---|
| B1 guard | "null MD body" | the **local** backend, where null *does* prove absence |
| H1 noop | receiver keeps a possibly-stale model | the **serve path**'s `isFresh`, which ignores `sourceMdHash` |
| L-R6-1 | `GENERATOR_VERSION` as freshness axis | the **cloud process**, which compiles a different value |

Note the third: the consumer was not another module, it was *the same code running in a different
process*. Hence the rule asks who reads this **and in which environment**.

---

## Reviewer disagreement is the signal

**Incident — Stage 3 cloud-sync, 7 rounds.** The two reviewers split 3 times. The reviewer *reporting a
finding* was correct all 3 times — **twice while the other returned CONVERGED over a live
Blocking/High**.

The losing verdicts were not lazy. They were plausible reasoning about the *adjacent* thing:
- One cleared `companionTransfer` because it uses a precomputed `winnerMdHash` — true, and irrelevant:
  the defect was in the envelope read one line earlier.
- One downgraded a Blocking to Low by assuming `cHas === true`, when `mdHash` is derived from the blob
  **body**, so an unreadable blob made it false.

Both were settled by reading the code, not by majority. **Record the adjudication in the review doc** —
an uncorrected wrong verdict sitting in `docs/reviews/` gets cited later as fact (this happened; the
correction is appended to the round-2 Claude review).

**Reachability arguments are where reviewers most often err**, because they require knowing the
deployed system's steady state, not just the code path. One reviewer called a precondition "unlikely"
that is in fact the normal post-sync state.

---

## Convergence measures the prompt, not only the code

**Incident.** Rounds 1–4 kept surfacing **pre-existing** defects — not regressions. They appeared
because the prompt got sharper each round, decisively when it changed from "review this code" to
"hunt for siblings of this root-cause **shape**." Two of round 4's three High findings came from that
single change.

So a clean round can mean the surface is exhausted *or* that the prompt was weak, and the stopping rule
silently assumes reviewer capability is constant. Trend for the record: Blocking `1→0→1→0→0→0→0`,
High `2→2→0→3→1→1→0`. Rounds 5–7 were the genuine convergence — R5's single High was found by *both*
reviewers independently, R6's was a severity dispute over a known defect, R7 found nothing.

**Standing list of shapes seen so far** (carry into each round's prompt):
absent vs failed-to-read · acting on a reading that cannot prove what it claims · same constant,
different process · a durable commit followed by a non-durable follow-up behind a gate that assumes
convergence · a test that passes in both worlds.

---

## Gate design: a converged artifact becomes an unexamined premise

**Incident.** Once the plan converged (6 rounds, 0 Blocking/High/Medium in the final round), every
downstream gate asked *"does the code match the plan?"* and none asked *"is the plan's type honest?"*
One wrong line propagated through 14 tasks, survived 14 per-task dual reviews and 2 whole-branch
rounds, and died in whole-branch round 3.

This is not negligence — it is the *design*. Sequential gates exist so later stages need not
re-litigate earlier ones. The efficiency and the blind spot are the same property.

**Why one re-derivation beats another full round:** a further round costs a pass over everything and
mostly re-confirms what earlier rounds established. One re-derivation costs a single question asked at
a layer that holds information the earlier gate could not have had — the plan author could not see that
`SupabaseBlobStore.get` swallows errors, because that file did not exist yet. Every defect here was
invisible at plan time and visible the moment both modules existed, which is exactly the boundary where
nobody was looking.

---

## Where review effort belongs

**Incident.** 14 per-task dual reviews returned clean. The whole-branch gate then found ~11 significant
defects — every one in the *composition* between modules that were each locally correct. Review budget
was allocated almost inversely to defect density.

---

## Known-red suites: quarantine or fix

**Incident.** `tests/integration/reservation-release.test.ts` fails identically on a stashed clean tree
(local Supabase state pollution — leftover `ledger_audit` rows, a stale queued job). It is unrelated to
any branch, and it makes "run the full suite — confirm no regressions" unfalsifiable: once *some* red is
expected, *all* red becomes negotiable, which is precisely how a real money-path regression gets waved
through. Hence: prove it by stashing, name it, and keep the known-red list empty.

---

## The review gate can fail open

**Incident (2026-07-18).** `scripts/codex-frontier-model.py` returned `gpt-5.6-sol`; the pinned Codex
CLI (0.142.5) rejects it with HTTP 400. The run produced a review file containing only an error and
**exited 0** — indistinguishable from a clean review unless you open the file.

The picker cannot be fixed from the cache alone: it already filters `visibility == "list"` and
`supported_in_api`, and the cache carries no minimum-client-version field. The fix belongs at the point
of use — a dispatch wrapper that detects the 400 / findings-free output and retries the next candidate.

Separately, the fallback rules in `docs/plugins.md` handle a reviewer that is *absent* (rate limit,
auth, hang) but not one that completes and is *wrong*. Both failure modes exit 0.

---

## Turn a finding into an assertion before deferring it

**Incident — the serve-path double-charge (2026-07-19).** The Stage 3 review found by *reading* that
`lib/html-doc/serve-doc.ts` could treat an unreadable model read as "absent" and pay to regenerate a
model already in the bucket. It was written into `docs/roadmap-to-launch.md` as an **unverified
inference** and scheduled for a deploy-time check at M1.4. Recording it felt like closure. It was
actually a bet that a manual check would happen later, against a failure mode — a transient storage
error — that is hard to reproduce on demand and whose first natural evidence is a user billing complaint.

It took one test file to settle, using scaffolding the repo already had: fault-injecting blob-store
wrappers (`tests/integration/helpers/cloud.ts`) and `spendLedgerTotal()`. The `null` a transient error
produces is byte-identical to a 404's, so simulating it was exact rather than approximate.

```
before: [DIAG] status=ok   gemini_calls=1  spend 6→12  attempt_count=2
after:  [DIAG] status=busy gemini_calls=0  spend 6→6   attempt_count=1
```

A real double-charge, fixed and regression-guarded the same day (PR #24). **Two supporting details:**

- The naive version of that test would have PASSED. `reserve_serve_model` has its own single-flight
  guard, so a spurious reserve while the lease is live no-ops and never charges — a second protection
  masking the first. The existing B1 test's author had hit this and left a comment; copying their
  forced-lease-expiry made the bug visible. When a test of a money path passes, check whether some
  *other* guard is absorbing the effect.
- The error shape was determined by **probing the live stack**, not by reading vendor types (the
  installed `@supabase/storage-js` ships only a UMD bundle). A missing object returns
  `{message:"Object not found", name:"StorageApiError", status:400, statusCode:"404"}` — so 404 is
  provable absence and everything else is not. Ten seconds of probing beat inference from docs.

**The rule's boundary:** this does not mean never defer. It means the deferral decision should be made
*after* asking "can I assert this?", not instead of asking.

---

## Required beats optional; casts opt out

**Incident.** The same defect class got two remedies. Stage 3 added `BlobStore.provesAbsence` as an
**optional** member — it fixed the sync call sites and did not propagate, so the identical bug stayed
live in serving code outside the reviewed scope. PR #24 added `BlobStore.tryGet` as a **required**
member, and one `tsc` run listed all 7 implementers exhaustively. Optional members let callers keep
inheriting the ambiguous original; required members force each one to answer.

**The boundary of that enforcement:** one test double was cast `as never`, so tsc could not flag its
missing `tryGet`. The new guard threw inside a `.catch(() => {})` and silently skipped the reserve that
double exists as a *positive control* to prove. The full unit suite caught it; the compiler could not.
A cast opts out of exactly the enforcement you are relying on, so compiler and behavioural tests cover
different holes and neither subsumes the other.

---

## Debt needs a trigger, not a list

**Incident.** The Parking Lot in `docs/roadmap-to-launch.md` held four sensible items with no
checkboxes, owners or triggers, and nothing in the workflow read that section. Newly-filed
infrastructure debt was heading for the same fate.

A trigger must be something that **fires for its own reasons**. "Review the debt list quarterly" is not
a trigger — it is another thing to remember, with the same decay as the item it is meant to rescue.
"The full-suite gate cannot be satisfied without naming red suites" works because that gate fires
whether or not anyone cares about the debt.

---

## Empirical basis — Stage 1E-b (2026-07-07), why re-review to convergence exists

The spec's first dual review found 3 Blocking + 3 High. The *re-review of the fixes* found **2 new
Blocking + 4 High that the first round and the fixes both missed** — metadata keyed by a non-owner-unique
`playlist_key`, `upsertVideo` erasing artifact status, and a false "abort stops billing" premise. A
single round would have shipped those into the plan and the code.

## Adversarial review precedent — Stage 1 (spec + plan)

The Codex review of `docs/design-spec.md` and `docs/implementation-plan.md` (between Tasks 2 and 3)
caught five architectural gaps that would have affected Tasks 3–10: SSE job identity, path-traversal
risk, deep-dive transcript fallback underspecification, output-folder ambiguity, and Obsidian vault URI
semantics.

---

## Evidence moved out of the spine (2026-08-08 restructure)

`docs/dev-process.md` was split four ways. The *decisions* stayed there; the *evidence* for them is
here, because it is read only when someone questions a rule. Nothing was retired — see
*Rules flagged for review* at the end of the spine for the four candidates awaiting a decision.

### Why branch + PR has no size exemption (Phase 5)

**The axis is blast radius, not size.** A missing `sort()` silently reordered paid content (defect
D1); a one-line predicate change moves money.

**And the boundary between "just docs" and "code" is slippery in practice.** On 2026-07-30 the
coordinator reasoned *"docs commits have precedent here"* and then, in the same batch, committed a new
`lib/storage/testing/` module straight to `master`. **A rule with a judgment call in the middle is a
rule that erodes** — which is why the relief comes from *batching* rather than from an exemption.

The hook exists because prose did not prevent that: `.claude/hooks/block-default-branch-push.sh` was
written after three commits, including that module, went to `master` while a 400-line always-loaded
document said not to.

**Merge ticks:** written twice as post-merge reconciles that should have been folded into the PR they
described (PR #40, PR #43). Hence "write the tick before opening the PR, and do not chase the SHA."

### Why anything longer than a line goes in a file

Two failure modes hit in one session on 2026-08-04. A commit message broke on an **apostrophe** inside
a `"$(cat <<'EOF' …)"` heredoc. And a Codex review prompt containing `` `key` `` was mangled into
`bash: key: command not found` — **any backtick inside a double-quoted bash string is command
substitution**, so the shell rewrote the prompt before the tool saw it, and the adversarial-review
gate was silently skipped.

This is **physical**, not a preference. `--body-file`, `git commit -F`, `--prompt-file`.

### The `gh` two-remotes footgun — RESOLVED 2026-08-04

The repo carried a second remote (`upstream` = `…-official-plugins`, the frozen predecessor) whose PR
numbers **collided** with `origin`'s, so a bare `gh pr` could act on the wrong repo — a mutating
`gh pr edit 2` once overwrote the other repo's PR body. The remote was removed
(`git remote remove upstream`) and `gh pr` now resolves unambiguously, verified. Passing
`--repo kujinlee/youtube-playlist-summaries-cloud` remains a harmless safe habit for mutating commands.

*(`official-plugins` is the OLD repo, superseded — **do not edit it**. "Local" means local mode of
`-cloud`.)*

### Architecture review — lessons from the first run (2026-07-30)

`docs/reviews/architecture-review-2026-07-30.md`.

- **Verify in both directions.** That run corrected claims on *both* sides — including one where the
  **coordinator's** grep was wrong and the agent was right (a line-wrapped expression a single-line
  pattern missed). **A failed grep is not a disproof.**
- **"Zero callers" does not always mean delete.** The run found a module implementing the correct
  commit→promote protocol with zero production callers and 8 tests. The right reading was that the
  *callers* were wrong, not the module. Apply the deletion test by asking where complexity would
  reappear, not by counting references.

### Anchor every ADR where the question arises

**ADR-0005 was missed for four weeks** because nothing in the `Dockerfile` said ffmpeg's absence was
deliberate. Correctness was never the problem — **reachability** was. A one-line comment at the code
that looks wrong without it is the whole fix.

Promotion criteria are already written in
[`.claude/skills/grill-with-docs/ADR-FORMAT.md`](../.claude/skills/grill-with-docs/ADR-FORMAT.md) →
*"When to offer an ADR"*. Do not invent new ones.

---

## The handoff with no reader

**Measured 2026-08-27.** `/handoff` saved to `mktemp -t handoff-XXXXXX.md`. **Three such files sat in
`$TMPDIR` — 2026-08-26 12:09, 2026-08-26 17:44, 2026-08-27 05:48 — and not one had ever been read by a
resuming session.** Random suffix, outside the repo, unindexed. Nothing could find them, including the
agent that wrote them.

The documents were good. That is the point. This is the **"live gate with NO CALLER"** shape this repo
has now hit four times, and it is the hardest kind to notice, because **the producing step is green**:
`/handoff` ran, wrote a file, reported success. Nothing downstream consumed it, and nothing was watching
for a consumer.

**What it cost, in the resume that found it.** That session re-derived the `M1`/`M2`/`M3` cross-document
collision from scratch and reported it to the user as a *new* finding — trap 3 of the unread handoff had
already stated it in one sentence. Two open items the user should have seen (the `--expect-present`
added-column blindness; the 16 MB `.superpowers/` residue) went unsurfaced while the user was told
*"nothing is waiting on me"*.

**The near-miss worth recording.** The obvious repair was `.remember/handoff.md`. It is wrong, and
wrong invisibly: **nothing reads that name either**, so the fix would have looked complete while
rebuilding the identical defect at a prettier path. The path that works is `.remember/remember.md`
because the `remember` plugin's SessionStart hook already reads it —
`REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"` (`session-start-hook.sh:795`), emitted as
`=== LAST HANDOFF ===` and injected **before** identity and memory so it survives context-preview
truncation (`:809-812`), with fingerprinted non-destructive delivery (`:814-825`) so a read-only session
does not consume the next one's note.

**Two general lessons.**

1. **Before building a channel, check whether one exists.** A mechanism was nearly written for a job the
   installed plugin already did. The tell was in a comment enumerating the hook's own output sections —
   found by grepping the hook for what it *injects*, not by assuming.
2. **A falsifier written as a sentence is usually a lagging one.** The first guard here was
   *"if a resume ever finds a `handoff-XXXXXX.md` in `$TMPDIR`, the skill was overwritten"* — true, and
   it only fires **after** a session has already lost its handoff. The leading guard is
   `scripts/check-handoff-path.py` behind a `PreToolUse` hook: it fires at invocation, before anything
   is written. Both are kept, because they fail differently — the script guards the *instruction*, and
   cannot observe where the file actually lands.

## The review gate that wrote over its own evidence

Round 3 of the project-dashboard plan review, 2026-08-28/29. Three defects in one chain; the
contract they justify lives in [`plugins.md`](plugins.md) at the dispatch point, and is not
restated here.

**One brief, two halves that want opposite things.** The brief's Output section said *"Write to the
review path you were given."* Correct for the Claude subagent, which has file tools. Fatal for
Codex, whose capture is the final message: the agent wrote, its final message became *"I wrote the
review to …"*, and the wrapper correctly rejected a report of a review as not being one.

**The control is exact.** Round 2's brief — same wrapper, same model ladder — never mentions writing
anything and captured cleanly. One sentence was the entire difference. That is why the fix is a
per-half contract rather than a tweak to the matcher.

**The agent guessed the path, and guessed it right.** The wrapper passes codex only `-o <tempfile>`;
the real `--out` is never given to the agent. So *"the review path you were given"* referred to
nothing, and the agent inferred `docs/reviews/plan-project-dashboard-r3-codex.md` from the four
prior-round filenames listed in the brief — a naming convention entirely predictable. Running under
`-s danger-full-access` it wrote there, over a **committed** artifact. Four models were tried, each
overwriting the last, and the file's verdict flipped from `READY TO EXECUTE: NO` to `YES` between
one read and the next.

**The wrapper wrote nothing at any point.** Every version on disk came from the agents' own writes.
This is why *"we only write on success"* was never the protection it appeared to be, and why the
mechanism added in 2026-09-01 SNAPSHOTS the directory rather than trusting its own restraint: the
thing to detect is a write the wrapper did not make.

**The verdict was trivial to lose.** The call was wrapped as
`python3 scripts/codex-review.py … ; echo "WRAPPER_RC=$?"`, so the completion notification reported
the **echo's** status. `WRAPPER_RC=1` sat unread while the run was treated as successful — the
`$?`-after-the-wrong-command trap, measured a **fourth** time in this repo.

**What it cost.** Round 3's Codex half never ran. Its findings were acted on anyway — they were
independently confirmed by the Claude half and by `scripts/check-plan-code.py`, so the fixes stand —
and a committed review was silently replaced. It was mitigated by hand at the time, and a hand
mitigation is not a mechanism, which is why backlog #68 existed at all.

**Exit codes, and what the wrapper now enforces.** `scripts/codex-review.py` returns **0** (a real
review was captured and written), **1** (no candidate produced one — the gate did NOT run, fall back
to a Claude adversarial review and record the gap), or **2** (REFUSED before contacting any model,
because `--out` already exists — pass `--allow-overwrite` to mean it). It also snapshots the `--out`
directory and names any file the agent created, overwrote or deleted behind its back on BOTH the
success and failure paths, and warns — quoting the phrase — when the prompt itself tells the agent
to write a file. None of that substitutes for the brief being right; it makes the failure loud
instead of silent.

**(d) — DECIDED AND CLOSED 2026-09-01: the wrapper writes its verdict down.** The open question was
whether to constrain the caller or record the verdict; the user chose the second. Every run now
writes `docs/reviews/verdicts/<review-stem>.verdict.json` — on the success path, the failure path
and the refusal path alike, through a single `emit()` so a future branch cannot forget one.

**The obvious version of this fix does not work, and that shaped the design.** "A file the caller
must read" is not a mechanism if the *caller* is still the reader: a file ignored is an exit code
ignored with extra steps, and nothing forces a read. So the verdict lands **inside the repository**
and `scripts/check-review-rounds.py` consumes it **in CI**. The consumer is deliberately not the
caller. It fails on exactly the round-3 shape — a verdict saying the gate did not run while a review
is filed under its name — and stays silent on the honest fallback, where the gate failed and left
nothing behind. That distinction is the whole point: the documented Codex-down path must not be
punished, only the *silent* one.

Three details worth keeping. **`gate_ran` is stated, not derived from the exit code** — a reader
that recomputed it would be a second implementation of the wrapper's rule, and this repo has
measured what those do. **A verdict that cannot be written is a CANNOT RUN (exit 2)**, not a
warning: an unrecorded success is indistinguishable from the failure being fixed. And **a
malformed verdict is exit 2 on the reading side too**, never a silent skip, because "unreadable"
and "the gate ran" look identical to a check that drops it.

⚠ **Demonstrated by accident while verifying it.** The end-to-end check ran the wrapper piped into
`tail`, so the shell reported `rc=0` — `$?` after a pipe is the *last* command's status, the same
trap in a new costume. The verdict on disk read `exit_code: 1, gate_ran: false` regardless. The
shell lost the answer; the file kept it. That is the mechanism working, observed rather than argued.

## The reviewer blamed for its partner's work

**Backlog #92, measured 2026-09-04.** `scripts/codex-review.py` takes a `{filename: sha256}`
snapshot of `docs/reviews/` before and after a run and reports the difference as
*"THE AGENT WROTE BEHIND THE WRAPPER"*. That detector exists for a real failure — round 3, where an
agent guessed its way into the artifact root under `-s danger-full-access` and overwrote a committed
review — so the instinct to keep it is right.

**But a digest diff cannot see a writer.** It supports exactly one claim: *this file changed while
the run was in flight*. The wrapper asserted a second, stronger one, and the documented dual-review
workflow falsifies it by construction — both halves are told to write into `docs/reviews/`, so any
overlap is reported as an intrusion. Four review docs carry the false accusation
(`209-r1-codex`, `spec-…-r1-codex`, `spec-…-r2-codex`, `code-…-r5-coordinator`) and it was filed as
a backlog item only on the fifth occurrence. **A detector that cries wolf is one people learn to
skip**, and this one writes its accusation into `docs/reviews/verdicts/<stem>.verdict.json`, which
CI reads.

⛔ **The half nobody had noticed was not cosmetic.** On the FAILURE path the wrapper does not merely
complain — `quarantine()` **moves** every newly-appeared file out of the tree. Reproduced on
temporary directories: a legitimately written `slice-r6-claude.md` was relocated into a temp
quarantine directory. And that is the *fallback* path — `docs/plugins.md` requires a failed or
rate-limited Codex run to be replaced by a Claude adversarial review, so **the run most likely to
quarantine was the very run whose replacement was being written beside it.** The row had been filed
🟡 *"it corrupted nothing"*, which was true of the path that had been looked at.

**The fix is a layout, not a predicate**, and that is the transferable part. Three shapes were on
the table: attribute by narrowing the snapshot window (does not work — the concurrent writer writes
inside it), record the wrapper's expected outputs (does not work — the writers are other
processes), or move legitimate writes out of the watched directory. Only the third makes the two
mechanisms consistent instead of contradictory. Halves now land in `docs/reviews/<writer>/`, which a
**non-recursive** snapshot cannot see, so the top level becomes a place where nothing legitimate
appears during a run — and quarantining what does appear becomes correct rather than dangerous.
`verdicts/` had already used this trick for the same reason; the precedent was there and unread.

**Two general lessons.** *An instrument must claim only what its evidence supports* — the wording
fix (`CREATED during the run (writer unattributed)`) matters independently of the layout, because
the next unattributable writer is not necessarily a review half. And *when a guard and a workflow
contradict each other, check whether the layout can be changed before weakening the guard* — the
predicate was never wrong; the directory was.
