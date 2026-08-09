# Round 12 — coordinator adjudication

**Verdict: NOT CONVERGED.** 1 Blocking (fixed), 3 High, 4 Medium. Round 13 mandatory.

Both reviewers landed. **The Blocking falsifies §12b's load-bearing claim**, which is the single
question round 12 was pointed at — so the brief did its job, and the answer was the one I did not
want.

---

## BLOCKING — FIXED THIS ROUND (`4d35402`)

### B1 — `reserve_artifact_slot` hands out a token that cannot complete the generation it just reserved

The generation insert is `on conflict … do nothing`, so when the row already existed and was still
pending it kept the **previous** caller's `reserved_by`, while the artifact upsert re-pointed
`lease_token` to the new one. RE-MEASURED by me from scratch:

```
W1 reserve -> reserved ; generation.reserved_by == W1 token: t
W2 reserve -> reserved (attempts=2) ; reserved_by == W2 token: f   STALE: t
W2 record with ITS OWN token -> REFUSED [P0001] … generation gX is pending
```

W2 asked, was told `reserved`, **paid**, and presented the token this very RPC had just returned to
it. §12b says *"the party holding paid bytes always still holds the token"* — it held both. They just
were not the same token. Shape #12, reached through the one credential round 11 kept.

**The fix is not a new design**: `04:235-237` already asserts the token is *"minted ONCE and shared
by the generation and the artifact, so the holder of a slot and the reserver of its generation are
provably the same party"*. That invariant was simply not implemented. On a **successful** reservation
the generation now names the winner — only after `found`, because re-pointing beside the insert would
hand the generation to a caller that goes on to be denied `busy`/`exhausted` (round 7 H3, inverted).

The previous holder loses nothing reachable: sharing a generation id means sharing the blob key (it
is derived from that id) and colliding on `video_artifacts_paid_uq`, so two writers on one generation
were never going to produce two rows.

---

## HIGH — open

### H1 — direct `service_role` DML completes a generation without the token *(Codex, MEASURED)*

`grant select, insert, update, delete on video_generations to service_role` means the token fence is
only enforced for callers that go through `record_artifact`. A future sync, import or repair path
using a table `UPDATE` bypasses it entirely — measured
`state=complete | md_hash=SHA_DIRECT`. This is the "rule that depends on every caller remembering"
shape, and round 11 made it the *only* fence, so the exposure is larger than when it was one of two.
Fix: a trigger refusing `pending → complete` except through the protocol, or narrower grants.

### H2 — `video_artifacts_generation_complete` is labelled SHAPE and is the guard that raised in B1 *(Claude, MEASURED)*

The classification pass's own question — *what does this guard do when the caller is merely SECOND?*
— was answered "reject", and B1 is the measurement of a blameless caller being rejected by it. Round
8's M2 said a guard is SHAPE only *given a reconciler*; this one's reconciler was the very thing B1
broke. It should be `SHAPE(reconciled)` naming that reconciler, so the next person to break it fails
the ratchet rather than a probe.

### H3 — `completed_by_another` is returned to the writer that itself completed the generation *(Claude, MEASURED)*

Round 11's new outcome fires on a second call from the **same** writer when it supplies a different
`p_md_hash` — e.g. a retry that recomputed the summary. Told its work was discarded when it was the
one who did the work. Not re-measured by me; recorded as inherited.

---

## MEDIUM — open

- **The guard ratchet omits RLS policies** (Codex) and, per Claude, **26 guards in total** — while
  printing *"every guard classified"*. Fourth guard-kind blind spot in the same enumeration: after
  triggers-on-two-tables and FKs-on-four-tables, this is the pattern, not the instance. Either
  enumerate `pg_policy` and the rest, or stop claiming totality in the success line.
- **The population ratchet still proves two INSERTs, not two callers** — documented in round 10,
  deferred again. It should be fixed or explicitly retired; carrying it a third round is how a known
  weakness becomes furniture.
- **A free slot can be reserved exactly once in its life** (Claude): `already_recorded` tells a
  re-render it is done. Interacts with round 11's typed `busy`.
- **Three `pending` biconditionals labelled bare `SHAPE`** that are `SHAPE(reconciled)` by the
  script's own rule (Claude, REASONED).

## What round 12 confirmed rather than found

- 123/123 assertions, 58/58 mutations, 45 guards — verified independently by both reviewers.
- The temp-copy isolation held again: both reviewers ran the gates, and the working tree was clean.
- **My own contract test was wrong and is fixed** (PR #60, `d2dcd40`): it asserted the abort *signal*
  was delivered, not that work was *abandoned*, and its fake returned `ok:true` unconditionally where
  the real `complete_job` is token-fenced. A fake that cannot express the fence cannot test it.

## The pattern worth naming for round 13

Rounds 7, 9, 11 and 12 have each produced a defect in the **same mechanism**, and each time the
previous round's fix was the cause. The credential is now correct in shape (one unguessable token)
and the remaining defects are about **who else can bypass it** (H1) and **whether the code keeps its
own invariant** (B1, now fixed). That is a different and healthier class than the previous three
rounds — but it is not convergence, and the honest read is that this mechanism has never once
survived a round.
