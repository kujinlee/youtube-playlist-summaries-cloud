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
here, because it is read only when someone questions a rule. ⟳ **One row WAS retired, 2026-09-10**
— the `gh` two-remotes footgun, whose full account is below — because the spine hit its 220-line
budget and that was the one line the document's own text disowned (*"history occupying spine
space"*). See *Rules flagged for review* at the end of the spine for the **three** candidates still
awaiting a decision. ⚠ Both numbers in this paragraph were false for one commit; they were caught by
a reviewer, not by a script, and nothing owns them.

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

**Exit codes, and what the wrapper now enforces.** ⟳ **CORRECTED 2026-09-24 (#176 r2, Medium) — this
passage described a THREE-way partition that the code had outgrown, and it is the page a reader is
sent to when questioning the rule.** `scripts/codex-review.py` returns **0** (a real review was
captured AND FILED), **1** (no candidate produced one — the gate did NOT run, fall back to a Claude
adversarial review and record the gap), **2** (CANNOT RUN / REFUSED — nothing was measured and
nothing was written), or **3** (`RC_NOT_FILED`: **the gate RAN and a real review EXISTS at `--out`**,
but filing it failed).

⛔ **3 IS NOT A FALLBACK, AND THAT IS WHY IT STOPPED BEING 2.** The fallback rule turns a CANNOT RUN
into *"discard it and run a Claude review in its place"*. Applied to a run whose Codex review exists,
that throws the review away — so two opposite outcomes sharing one code was a live hazard, not an
untidiness. Recover the capture from the path the wrapper prints and file it by hand. It also snapshots the `--out`
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


## The reviewer I starved and then declared absent

`scripts/codex-review.py --timeout` defaults to **900s**. On 2026-09-16 three review rounds of
`scripts/explainer-serve.py` — a 2,100-line file whose review also runs a ~12-minute mutation
harness — each returned `timed out` after about fifteen minutes. I read that as Codex being
unavailable, invoked the fallback rule three times, and merged PR #311 on **single-half review**,
recording `REVIEW GAP: codex` in all three round documents.

**The timeout was mine.** The Claude half of the same review took 40–60 minutes every round; I had
given Codex fifteen and never passed the flag. The user pointed out that this had happened before
and that doubling the limit resolved it. Re-run at `--timeout 3600`, the same review **completed on
the first attempt** — and found two defects the three Claude rounds had missed:

- `resolve_page` judged "did this name have an extension?" on the **raw, pre-decoded** path, so
  `/secret%2eenv` bypassed a rule that `/secret.env` obeyed — `safe_path` unquotes first, so the
  classifier and its resolver disagreed about what the same request said;
- `source_shell` escaped a file's **contents** and interpolated its **name** raw into `<title>` and
  `<header>`, so a file called `evil<img src=x onerror=alert(1)>.md` injected markup into the viewer.
  `safe_path` admits it: nothing in containment or the suffix allow-list has an opinion about the
  characters in a name.

⭐ **The lesson is not "raise the timeout".** It is that **a timeout is a statement about the budget,
not about the other side** — the same shape as this project's *a hang is not a diagnosis*, which it
already had a note about. And the cost was specific rather than abstract: three Claude rounds swept
that file with 151 mutations and tested hostile *content* and hostile *paths* exhaustively; Codex
tested a hostile *filename* and an *encoded* spelling of a path already covered. Neither is deeper.
They are different habits of attack, which is the whole reason `plugins.md` requires both halves —
and I traded one away for a number I could have changed.

**What changed so it cannot recur by memory alone:** the wrapper detects an all-timeouts failure and
prints *"that is probably this caller's budget, not Codex — re-run once at `<2x>`s before falling
back"*, with the doubled number computed. The rule lives where the failure happens.

---

## The eviction queue that was never drained, and the budget that reported `ok` at 100%

**Resolved 2026-09-20, at the user's decision.** `docs/dev-process.md` carried a table called
*"Rules flagged for review, not retired"* holding three entries, each with the note *"retiring a
rule is the user's call."* Nobody ever made that call, and the file sat at **exactly 220/220** —
its budget — for long enough that the next legitimate spine rule could not have landed.

**The two halves failed together, which is why neither was noticed.** The budget is the pressure and
the queue is the relief valve; `check-docs.py` printed `ok` at 100% utilisation, so the pressure was
invisible, and nothing ever asked anyone to open the valve. A budget with no eviction policy has
only two stable states: permanently blocking, or bumped whenever it is inconvenient — which is a
ratchet wearing a limit's clothing. Measured: the number had been set **once** and never raised.

⭐ **The sharper defect was the smaller one.** Every other gate in this repo is built to fail
*before* the damage. This one reported green right up to the edge, so the limit could only be
discovered by writing a rule and being refused — the worst possible moment, because the work is
already done. `check-docs.py` now warns inside the last 7% of a budget and **names both remedies**,
because they are different decisions and only a human picks between them: raise the number, or
prioritise and retire. The rule is `budget_verdict()`, pure and mutation-covered.

⚠ **And the first version of that rule shipped a false comment, caught by running its own mutation
rather than by reading — recorded because it is this project's most-filed defect class landing on
the fix for it.** The docstring claimed `<=` protected the ZERO-RUNWAY case (a file exactly at its
budget). It does not: `0 < slack` is true, so that file reads tight either way. `<` actually breaks
the file whose runway is EXACTLY the threshold. The mutation therefore killed **through a different
case than the manifest named** — a green suite and an unattributable kill, which is why coverage
here is counted in *attributed* kills and never in kills.

### The three rules, and what each was resolved to

**1. "Sub-project 2 does not begin until 1 is fully verified and merged" — RETIRED.** Superseded by
events: the frontend shipped and both sub-projects have been proceeding in parallel for months. The
rule was describing a sequencing constraint that reality had already dissolved. Kept as a sentence
saying they run in parallel, so a reader does not re-derive the old ordering from silence.

**2. `subagent-driven-development` as the Phase 3 execution default — CONFIRMED, not retired.** The
flag read *"set 2026-06-09, never re-examined."* It has now been re-examined twice over: the user
holds a standing answer to always choose subagent-driven, and the 2026-09-19/20 feature-hub session
ran it end to end. ⚠ **What that session measured is worth more than the confirmation:** six
subagents, **three finished and three stalled**, and the split was **dispatch size, not model** —
every stalled brief carried a verification section longer than its work section, and every
successful one was one or two edits plus about four commands. The default stands; the operational
lesson is that a dispatch whose verification outweighs its work spends the agent's budget before it
reaches the commit.

**3. "Currently known-red: none" — flag RETIRED; the line stays where it is.** The flag argued this
is state rather than policy and belongs in the roadmap. Correct about the *state* cell and wrong
about the *rule*: `process-checklists.md:137` says the full-suite step is satisfiable only while the
known-red set is **explicitly named**, and that is a genuine gate whose home is the checklist. Only
the current value of the list is state, it sits beside the rule it qualifies, and
`process-checklists.md` carries no line budget — so moving it buys nothing and costs a reader the
context. ⚠ Resolved by deciding, not by deleting: the flag is gone because it was answered.

**Falsifier for all of this:** `python3 scripts/check-docs.py` prints `TIGHT` with a runway count and
both remedies whenever a budgeted file is inside the band; `budget_verdict(220, 220) == "tight"`
pins the zero-runway case; and the band's upper edge is pinned by a mutation (`<=` → `<`) that must
kill **through** `"a file one line inside the warn band is 'tight'"`.

---

## The instruction with no author

A system-prompt line — *"Do not call the AgentTool unless the user requested it"* — collided with
this project's dual-review gate, whose Claude half is normally a fresh subagent. The rule that
settles it is one box in [`plugins.md`](plugins.md) → *Code Review*; this is the evidence behind it,
kept here because the **cost was in re-deriving it**, not in the answer.

**Audited 2026-09-22, six sources, all negative:**

| searched | contains it? |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `dev-process.md`, `plugins.md`, the checklists, `review-method.md` | **no** |
| `.claude/settings.json`, `~/.claude/settings.json`, `~/.claude/CLAUDE.md` | **no** |
| managed/enterprise policy — all three OS locations | **absent** |
| the session's launch argv | `claude --allow-dangerously-skip-permissions`, **no `--append-system-prompt`** |
| every occurrence across 803 project transcripts | **assistant text only** — never a user message |

⭐ **The finding is not "it has no owner". It is that FOUR sessions each discovered that
independently.** The identical audit ran on **2026-08-27** and reached the identical conclusion —
and that session then spawned the agent anyway. Nobody wrote it down, so it re-ran on **08-29**,
was cited again on **09-06** and **09-20**, and ran a fourth time on **09-22**. The instruction was
therefore never once honoured; it only ever bought a detour, and on 09-22 it also produced an
unearned `REVIEW GAP: claude` in a review document before being retracted.

This is the recorded shape *it already exists under a name I didn't search*, applied to a
conclusion rather than to code — and the reason a null result is worth a paragraph. *"We looked and
there is nothing there"* is a finding with a shelf life; left unwritten it expires the moment the
session ends, and the next reader cannot tell an unexamined question from an answered one.

**The user's ruling, 2026-09-22, given after being shown that table:** *"if the reason cannot be
found, remove this restriction."*

### ⭐ The one candidate reason — offered by the user, and it does not explain the instruction, but it BOUNDS the ruling

The user then named the thing that would justify caution: *"shared resource edit and interference
among writers in agents. We have protocol to avoid this type of interference."* That hazard is real
and measured here — a concurrency inference was wrong **twice**, each time filing a **Blocking**
finding against what turned out to be contamination.

But it does not reach the instruction, for two reasons that are already written down in
[`review-method.md`](review-method.md) → *Running agents concurrently*:

1. **The protocol classifies the OPERATION, not the agent.** *"Both review halves at once"* is in
   its ✅ MEASURED-SAFE row — they read files and each writes only its own review path, verified by
   three overlapping processes producing byte-identical data across all 23 manifest entries. Only
   three operations must be serialised: Postgres **roles**, **`git` in the main working tree**, and
   **top-level `docs/reviews/` writes while a Codex run is in flight**.
2. **That section already carries a RULE box saying spawning is the default**, with the measured
   cost of the opposite: a session running under this very instruction shipped **PR #325 after six
   review rounds with only the Codex half**, every "claude half" a coordinator self-review.

So the correct shape is not *"don't spawn"* but *"spawn, and respect the operation table"* — which
is what the `plugins.md` rule now says. **A blanket restriction and a targeted one are not the same
instrument**, and accepting the blanket version because a targeted concern exists is the recorded
*a framing widened to fit is no longer a claim*.

⚠ **AND THE COORDINATOR BROKE HAZARD 2 WHILE WRITING THIS, which is the strongest thing in this
section.** The dispatcher rule is *commit before spawning* — the only protection hazard 2 has. The
2026-09-22 session did commit (`ffc85be8`) before spawning the review half, and then **kept editing
the main working tree for the rest of the round**, leaving four modified files uncommitted while a
subagent with full tool access was live. Nothing was lost: `git stash list` empty, every edit
present. That is **luck, not safety** — the identical wording the table already uses about a
`/brief` agent that ran `stash`/`stash pop` mid-edit and *"completed cleanly by luck"*. The user's
caution was better aimed than the instruction it was offered to explain.

⚠ **What "remove" can and cannot mean, stated rather than glossed.** The line is injected into the
system prompt; no file in this repo or in `~/.claude` owns it, so it cannot be deleted. What is
removable is its **authority** — `CLAUDE.md` imports `plugins.md`, and project instructions outrank
an instruction of unknown provenance. Claiming the line was "removed" would be a green check over
the wrong subject. ⚠ Scope is the **Agent tool only**. The sibling line about workflows and
deep-research audits to the same dead end and the user did **not** rule on it, so it still needs
asking — widening a ruling to a case it did not cover is the recorded *a framing widened to fit is
no longer a claim*.

---

## The side job with no name

The rule is in [`process-checklists.md`](process-checklists.md) → *A SIDE JOB gets a name before it
gets work*. This is what it cost, because the rule reads as obvious and the incident explains why it
still had to be written.

**2026-09-22, two threads, one session.** Thread A was `banner-blind-spot` — a new warning class in
`check-banner-armed.py`, four review rounds deep. Mid-session the user reported that the Stop hook
was emitting an error on every stop. That became thread B: a real defect across three guards
(`check-ci-watched.py`, `check-plan-progress.py`, `begin-plan.py`), about forty tool calls, three
suites and nine mutations.

**Thread B ran to completion with no plan armed, no branch named in any message, and no banner
emitted.** The user's report is the measurement:

> *"you don't show what you are doing (banner or something similar) and I don't know what thread or
> work is described in your log lines — there are original work and stop-hook work"*

⭐ **THE CAUSAL CHAIN IS THE FINDING, because "remember to emit banners" would not have broken it.**
`CLAUDE.md` says to derive the thread name from the plan slug in `.claude/executing-plan`,
specifically so two banners in one thread cannot disagree about what the thread is called. Thread A
owned that sentinel and was paused. Thread B never armed one. So there was **no slug to derive a
name from** — and the response to that was to stop bannering entirely rather than to notice the
gap. The convention had a precondition nobody had named, and when the precondition failed the
convention failed silently.

⚠ **AND THE SAME SESSION HAD ALREADY DONE IT ONCE**, at smaller scale: an audit of an
unexplained instruction (→ *The instruction with no author*) ran unnamed inside thread A. That one
was small enough not to confuse anyone, which is exactly why it taught nothing at the time.

**Why the rule is a SIZE question rather than "always name it".** Naming has a real cost — a plan
file, a branch, a `--pause`/`--resume` round trip on the single sentinel — and a rule that charges
it for re-reading a file is a rule people route around. The bar (about five tool calls, or a
tracked file) is set where the cost stops mattering, and it is deliberately the same bar
`dev-process.md` Phase 5 already uses for branch + PR: *touching a tracked file* is what makes a
change worth a name, whoever asked for it.

⟳ **AND THE FIRST VERSION OF THIS SECTION GOT THE CONSTRAINT WRONG, WHICH IS THE MORE USEFUL
HALF.** It stated: *"`.claude/executing-plan` supervises exactly ONE plan. Two live threads cannot
both be armed."* Checked hours later, with both threads still live: **both were armed**, one in the
main tree and one in a worktree. `begin-plan.py` resolves `ROOT` from its own path, so each tree
has a private sentinel. The claim was generalised from a single observation — the two threads of
that afternoon happened to share a tree — and written as a property of the mechanism. The recorded
shape *check the assumption, not just the code*, committed inside a rule about not letting
unexamined preconditions fail silently.

⛔ **THE ACTUAL LIMIT IS NARROWER AND MORE DANGEROUS.** One sentinel per tree, but only one tree is
SUPERVISED: `block-idle-stop.sh` derives `REPO_ROOT` from its own path and the session runs the
hook under its cwd. Observed directly — while work ran in the worktree, every Stop-hook message
named the MAIN tree's plan. So arming a plan in a worktree buys a thread NAME for banners and buys
no premature-stop protection at all, which is the opposite of the impression "both threads are
armed" gives. A worktree is for isolating a tree from an in-flight sweep or a live agent; it is not
a way to supervise two threads at once.

Backlog #100 already records the sentinel as a structured state file with no schema and two
de-facto owners; this is a different property of the same file and, unlike #100's instances, not a
defect — it is a design that has only ever had to supervise one tree. Whether the hook should read
every worktree's sentinel is a real question and is NOT decided here. What is decided is that the
swap must be **announced** (`⤳` / `↳`), and that a pause reason must name the plan file to return
to, because the next turn will not remember it.

⭐ **The mechanical half already exists and shipped alongside this.** A turn that does substantial
work with nothing armed and no banner is `check-banner-armed.py`'s `unheralded` class — built in
thread A, in the same session, for exactly this shape. It would have flagged thread B; it was not
merged yet. That is the ordinary way round here: the guard gets built because the failure happened,
and the prose exists to say which failure.

---

## The testimony that named a scratch file

**Backlog #176, 2026-09-23.** Referenced from [`plugins.md`](plugins.md)'s call shape for
`scripts/codex-review.py`, where the rule is stated in five lines and the argument is here.

**What the mechanism is for.** Every Codex review run writes a verdict —
`docs/reviews/verdicts/<name>.verdict.json`, carrying `gate_ran` — and `check-review-rounds.py`
reads it **in CI**. The consumer is deliberately not the caller, because the caller is what loses
exit codes. It fires on one shape: *the gate did not run, and an artifact bearing its name was
filed anyway*. The join is a string comparison — the record's `review` field against the filenames
actually present in `docs/reviews/`.

**Why that join could not work.** `--out` is a scratch path and must stay one: the reviewing agent
runs under `-s danger-full-access`, so the documented shape puts the capture outside the repository
where a stray write cannot reach an artifact. `docs/plugins.md` prescribed
`--out "$(mktemp -d)/r.md"`. The wrapper then derived **both** the verdict's filename and the
`review` field from that basename — so every review in the repository was testimony about `r.md`, a
file that has never existed in `docs/reviews/`. **Measured**, driving the shipped
`verdict_problems` both ways: the identical failed gate reports **0** problems under the scratch
name and **1** under the review's real name. ⟳ **The corpus figure that stood here — "183
verdicts, 58 (32%)" — is REMOVED rather than corrected** (r1 M3): the count was **184** at both
base and head, so it was wrong when written, and it was propagated to three further sites, two of
them shipped scripts, instead of being re-derived. The denominator also moves on every run, so any
frozen copy is stale by construction. `check-review-rounds.py` now PRINTS the live counts — total
read, meaningfully checked, pre-cutover, refusals — on every run.

**Why four correct fixes could not terminate.** The namespace was patched four times in two rounds —
a refusal when the derived path was already tracked; a run token over the dispatch HEAD; the tree
added to that token; the token's width. Each was right about the failure in front of it, and none
could work, because *the name was being derived from something that is not the review's name*. The
review's identity — `<subject>-r<N>-<writer>.md` — did not exist at dispatch. It was assigned
afterwards by whoever promoted the capture, and **no code implemented the promotion**:
`docs/plugins.md` said `# then promote` and that comment was the entire mechanism. A derivation
cannot be correct about an identity that is assigned later. That is why the architecture review was
convened on THRASHING rather than another fix being written.

**The two decisions, and what each rules out.**

1. **`--review-id` is REQUIRED, and basename derivation is DELETED.** An optional id would keep two
   mechanisms for one concern, and the fallback would be the exact path every document steers
   callers into — the defect, still reachable, now behind a flag that looks like a fix. Old
   invocations get a refusal sentence rather than argparse's "unrecognized arguments"; the
   precedent is `check-plan-code.py`'s retired plan-mode flags.
2. **The wrapper performs the promotion**, so one module owns both artifacts of a run and the join
   holds by construction instead of by convention. Feasibility was checked, not assumed: the
   intrusion snapshot of `docs/reviews` is NON-RECURSIVE, so writing into `docs/reviews/<writer>/`
   cannot register as an agent guessing its way into the artifact root, and `quarantine()` on the
   failure path cannot reach it — ⟳ **on a SECOND condition this paragraph originally left
   unstated** (r1 M5). `watched_dirs` begins with `--out`'s own directory, so an `--out` inside
   `docs/reviews/<writer>/` makes that directory a watched root and recursion never enters into
   it. The r1 reviewer DROVE it: a failing run with `--out` there quarantined a concurrent half
   out of the repository — backlog #92 reproduced against the new layout, on the FALLBACK path,
   i.e. against the review being written to replace the failed one. `out_location_refusal` now
   refuses an `--out` inside `docs/reviews/`, which refuses nothing legitimate because the
   documented shape is outside the repository entirely.

⛔ **`--verdict` was the cheaper fix, and it provably could not close the join.** It named the
verdict FILE. The derivation happened TWICE, independently, from the same scratch path, and this
flag reached only one of them — the record's `review` field was built from
`os.path.basename(out_path)` and `args.verdict` was never passed to `verdict_record` at all. A
caller doing everything right, deliberately naming their testimony, still wrote a record keyed by
scratch. It is retired with rc=2.

⚠ **The pre-cutover verdicts are left untouched** (user decision). They are committed testimony
about runs nobody can re-observe, and rewriting their `review` field would be inventing a name for
a file that may never have existed — the same ground on which `read_verdicts` refuses to back-fill
history. The cost is carried as an **era boundary** in the consumer instead, and it is a NUMBER IN
THE DATA: `VERDICT_SCHEMA` moved to **3** — the `review` field's meaning changed, which is what a
schema version is for — and `check-review-rounds.TRUSTED_SCHEMA` skips anything below it, counting
what it skipped. ⟳ **It was prose with no falsifier until r1 M2**: a comment plus one `print`,
with `VERDICT_SCHEMA` sitting at `2` on both sides of the boundary, so 99 pre-cutover records were
indistinguishable from post-cutover ones and deleting both sentences went green everywhere.
⟳ **And it now really does print on every run** (r1 L2): the `print` sat after both of `main`'s
early returns, so the claim "prints it on every run" was false for the rc=1 and rc=2 paths — and a
reader hitting a RED run is exactly the reader about to re-read the verdict corpus. It is emitted
before the early returns, with counts derived from the records just read.

⛔ **AND THE REFUSAL MUST NOT DESTROY WHAT IT IS PROTECTING — r4 M5, RETIRED WITH THE WRONG
SUBJECT AND RESTORED (r1 B1).** The slice deleted `refusal_verdict_path` along with the
`--out`-derived namespace, on the argument that the entries "mutated the ALLOCATOR for a namespace
that is GONE". True of the allocator; the invariant it guarded was never about allocation. Measured
at `4c29fe25`: re-dispatching an id whose review is already filed took the new refusal path, which
returned through `emit`, whose `write_verdict` opens `"w"` — so a committed `gate_ran: true` record
became `gate_ran: false`, and the join key this very slice built then told CI to **delete a genuine
adversarial review**. `check-review-recorded.py` could not have caught it either: it selects with
`--diff-filter=A`, and an overwritten file is M, not A. The fix is two mechanisms for two concerns
— `refusal_verdict_path` stops the WRITE destroying the record next door, and a `refused` field in
the testimony stops the READ misinterpreting it — because keying the consumer on the filename would
be a second implementation of the naming rule.

⚠ **`rc=2` no longer covers two opposite outcomes** (r1 M4). A run whose gate RAN, whose review
exists at `--out`, and whose promotion was refused used to exit **2** — the code `docs/plugins.md`
documents as *CANNOT RUN*, whose fallback rule says to discard the result and run a Claude review
in its place. That instruction applied here throws away a Codex review that was paid for and
exists. It exits **3**, and the legend says so.

## The reviewer that was sandboxed out of its own evidence

*Moved here 2026-09-23 from [`docs/plugins.md`](plugins.md), which holds the RULE and is imported
by `CLAUDE.md` into every session. The rule is short; this is the measurement behind it, which a
reader needs only when asking "why". The eviction was the human's call when folding
`review-identity-176` round 1: the file sat at its 260-line budget and a corrected exit-code
contract had to go in, and raising the budget to fit new content is how a budget stops meaning
anything.*

**THERE ARE TWO SANDBOXES, AND DISABLING THE OUTER ONE DOES NOTHING TO THE INNER ONE**
(added 2026-08-07).

| Layer | Controlled by | What it governs |
|---|---|---|
| Outer | Claude Code's `dangerouslyDisableSandbox` on the Bash call | whether *we* may launch the process |
| **Inner** | **`codex exec -s <mode>`**, default `workspace-write` | what **Codex** may do to the machine |

**MEASURED in round 7 of the blob-addressing review:** the wrapper passed no `-s`, so Codex
sandboxed *itself*, could not open the Docker socket
(`dial unix …/docker.sock: connect: operation not permitted`), and reported
`0/35 mutations … SQL did not run`. **It reviewed by reading.** Its findings happened to be right,
but the whole reason that artifact was moved out of prose into executable SQL is that reading is
the most expensive way to find defects — **a reviewer that cannot execute is a downgraded gate that
still reports success.**

⭐ **Note the shape, which is the transferable part:** this is the *same class* as the fail-open
cases, one layer out. The existing memory note — *"run Codex from the coordinator with
`dangerouslyDisableSandbox`"* — covered the **outer** sandbox only, solving one instance and reading
as if it covered the class. `scripts/codex-review.py` now passes `-s danger-full-access`.
`trust_level = "trusted"` in `~/.codex/config.toml` does **not** substitute: it governs approval
prompts, not socket access, and no narrower mode works because the verifier needs a unix socket
outside every workspace root.

### Why neither exit code proves a Codex run succeeded

`scripts/codex-frontier-model.py` ranks by `priority` without filtering on what the pinned CLI
supports — it cannot, as the cache has no minimum-client-version field (re-verified 2026-07-19
across every key of all 7 cached models). It still returns `gpt-5.6-sol`, which CLI 0.142.5 rejects
with *"requires a newer version of Codex"*. The wrapper falls through
`gpt-5.6-sol → -terra → -luna → gpt-5.5` automatically.

⚠ **Correction to what `plugins.md` previously claimed:** it said such runs exit **0**. Measured
2026-07-19 — a direct `codex exec` exits **1**. The exit-0 report comes from the plugin's
background-task path, not the CLI. Because the two disagree, trust *neither* as proof of success:
**read the output FILE.** (Manual fallback if you bypass the wrapper: `codex exec -m gpt-5.5`.)

## Every double-quoted bash string

*Moved here 2026-09-23 from [`docs/plugins.md`](plugins.md), which keeps the RULE — anything longer
than a line goes in a file. This is the measurement behind it.*

It applies to **every** double-quoted bash string, not just `gh`. Measured 2026-08-04: a round-3
review prompt containing `` `key` `` produced `bash: key: command not found` — the backtick was
**command substitution**, the shell silently rewrote the prompt before Codex ever saw it, and no
review was written. In the same session `git commit -m "$(cat <<'EOF' …)"` broke on an apostrophe.

⚠ **The wrapper behaved correctly here and that is the point:** it refused to write a review file
rather than writing an empty one, so the mangled run failed **loud**. A caller checking only a raw
`codex exec`'s exit code would have recorded a completed gate.

## A count with no owner

*Moved here 2026-09-23 from [`docs/plugins.md`](plugins.md), which keeps the RULE — the count is
declared in the script's own docstring, verified by running it, and deliberately not repeated.*

⟳ **2026-09-04:** `plugins.md` said **35** while the suite ran **51** — measured, not noticed, for
an unknown span. The count was moved into the script and pinned in `check-selftest-counts.POPULATION`.

⟳⟳ **2026-09-14, r13 Medium — that fix did not hold, and the sentence describing it was the proof.**
The pin stops the SCRIPT drifting; it cannot see a second copy in prose, and
`check-selftest-counts.py` reads only `scripts/*.py`. The line went on saying **63** while the suite
ran **85** — inside the very sentence promising *"the next drift fails a gate instead of sitting in
prose"* — and `CLAUDE.md` imports that file, so the wrong number was loaded into every session.

⭐ **The number was removed rather than corrected.** A count with no owner drifts again; the only
durable fix is to have ONE copy, in the place a gate can run.
