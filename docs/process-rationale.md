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
