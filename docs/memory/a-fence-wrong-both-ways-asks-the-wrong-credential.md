---
name: a-fence-wrong-both-ways-asks-the-wrong-credential
description: "FIRES-WHEN: tuning a guard measured BOTH too permissive and too strict — When a guard is measured BOTH too permissive and too strict, it is not mis-tuned — it is asking for a credential the honest party cannot present; fix the credential, not the threshold"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-08-09T01:19:07.111Z
---

**Measured 2026-08-08 (round 8 → PR #58, `dc92859`).** Round 7's generation-ownership fence, in one
round, from two independent reviewers:

| Direction | Measured |
|---|---|
| **too permissive** | a caller with `p_token = NULL` completed another worker's in-flight generation with its own content (`SHA_ATTACKER`) — and, re-measured, so did a caller with a **random valid non-NULL token** (`SHA_FOREIGN`) |
| **too strict** | the worker that fallback existed for — restarted (token gone) *and* reclaimed (slot gone) — was REFUSED `[P0001]` and its paid Gemini output destroyed. A control call **with** the token succeeded, isolating the fence |

**The move: stop tuning, and ask what the honest party can still present.**

Three things identify a worker mid-job and they do **not** survive equally — `worker_id` is stable
config, `job_id` is recoverable by query, and `lease_token` is a random uuid held only in memory.
Round 7 fenced on the one that cannot survive a restart, so its fallback *had* to be weak enough to
let a stranger through. Recording the durable pair at reserve time closed **both** ends with one
change; no threshold moved.

> A fence you can only fix by loosening or tightening is a fence asking the wrong question. Look for
> the credential that is **durable for the honest caller and unavailable to anyone else** — and check
> whether the system already has one (here the job queue was fencing `heartbeat_job`/`complete_job`
> on exactly this identity, so the fix reused an established credential rather than inventing a third).

**Corollary, and it is why the headline was wrong:** the permissive report said *"tokenless"*. NULL
was never the crux — a valid foreign token worked identically — so `p_token is not null` would have
fixed nothing. **Re-measure the mechanism before accepting a reviewer's framing of it**; this is the
second time a round-8 headline and its actual mechanism differed.

**⚠ SUPERSEDED IN PART, 2026-08-08 (round 10).** The diagnosis was right; my ANSWER was wrong twice
over. The `(worker_id, job_id)` pair I chose was replayable (both columns readable from the row they
fence) AND unusable (`worker_id` is regenerated per process). Round 10 then found the requirement was
never real — the party with paid bytes always still holds its token — so the resolution was to
**delete the mechanism** and make it a caller obligation (PR #59). Keep the "wrong credential"
diagnosis; discard the durable-pair remedy. See [[quote-the-code-dont-characterise-it]].

Neither reviewer could have found this alone: each saw one end and would have proposed a fix
deepening the other. See [[dual-review-what-it-catches]],
[[reservation-guards-spending-not-recording]], [[guard-classification-shape-vs-sequence]],
[[blob-addressing-spec-state]].
