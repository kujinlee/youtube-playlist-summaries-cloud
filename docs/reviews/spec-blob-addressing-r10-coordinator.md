# Round 10 — coordinator adjudication

**Verdict: NOT CONVERGED.** 1 Blocking, 4 High, 4 Medium. Round 11 is mandatory.

**The headline: round 9's ownership fix is a REGRESSION, and I wrote it.** Round 8 measured round 7's
fence failing in both directions and I concluded it was "asking for the wrong credential". That
conclusion was right. The credential I chose is **also** wrong, and worse than what it replaced: it
refuses the honest restarted worker *always* rather than sometimes, and it is *replayable by anyone
who can read the row it fences*. Both reviewers found it independently, from different angles, and I
reproduced both from scratch.

The instance count that matters: this is **shape #9 (a fix that moved or reintroduced a defect) for
the eleventh time**, and the second consecutive round in which the finding is *the previous round's
fix*.

---

## BLOCKING

### B1 — the credential is stored in the row it protects, so the fence is replayable by any caller that can `select`

`record_artifact` accepts `(g.reserved_by_worker = p_worker_id and g.reserved_by_job = p_job_id)`,
and both columns live in `video_generations`, which grants `select` to `service_role` — the same role
that may call the function. The parameters are bound to nothing about the caller. So "proof of
ownership" is two plaintext values readable from the row being fenced.

MEASURED by me, no forged token and no privilege escalation (`…/scratchpad/r10-probe2.sql`):

```
M1. VICTIM reserved -> reserved (now inside its paid Gemini call)
M2. ATTACKER reads the credential: worker=worker-VICTIM  job=1ab8a512-…
M3. ATTACKER completes it -> recorded_after_token_loss ; md_hash now SHA_ATTACKER
M4. VICTIM records its REAL work -> recorded_after_token_loss
M5. md_hash the manifest now claims = SHA_ATTACKER  (victim paid for SHA_REAL)
```

The schema comment I wrote — *"A stranger presents a different pair and is rejected"* — is
measurably false.

**M4 is a second defect, and it needs no attacker at all.** The victim returns with its real token
and its real bytes and is told **`recorded_after_token_loss`** — a success outcome — while the
manifest keeps the other writer's hash. Cause: the fence UPDATE requires `g.state = 'pending'`, the
generation is already `complete`, so `coalesce(p_md_hash, g.md_hash)` never runs; the function then
falls through to the append path, whose `do update` never touches `md_hash`. Any two workers on one
generation produce this, not just an adversary. Shape #4 (a row claiming what the blob does not
satisfy) *and* shape #5 (silent failure), on the money path, on the SUCCESS path.

Codex reached the same fence from a third angle: with an **empty** `worker_id`, which a misconfigured
worker will happily reserve under, any caller presenting `''` plus the job id completes the
generation. I reproduced that too — `tldr = hijack`.

---

## HIGH

### H1 — `worker_id` is not stable config; it is regenerated on every process start

This is the factual error under my round-9 recommendation, and it invalidates the premise rather than
the implementation. `worker/main.ts:69`:

```ts
const workerId = `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}`;
```

A fresh `randomUUID()` and the pid, minted at process start. It is **exactly as volatile as the lease
token it replaced**. A restarted worker presents a different `worker_id` and fails the fence in every
case, not an edge case.

The `job_id` half fails on the same event. `sweep_expired_leases` sets
`locked_by = null, lease_token = null` and moves the job off `active`, so the recovery query I named
(*"query jobs for `locked_by = me and status = 'active'`"*) returns **zero rows precisely when
recovery is needed**. Verified by reading both sites.

Net effect: round 9 is strictly worse than round 7 for the honest worker. Round 7's slot-name
disjunct at least let a restarted worker through; the replacement lets nobody honest through and
still lets a reader through. And the refusal is a raw `P0001` from a trigger, so the caller cannot
distinguish it from a genuine caller bug.

### H2 — a tokenless caller clears another worker's free lease and repoints the slot

Caused by round 9's own lease-clearing fix (Claude H2 / Codex M1). MEASURED:

```
L1. W1 reserved a free slot -> reserved (token held)
L2. W2 tokenless record -> recorded_free ; pending rows left = 0 ; key now …/OTHER.pdf
```

This is the **fifth face of the free/paid seam** after the reconciler, the short-circuit, the tenant
confinement and the lease columns — the seam the round-10 brief explicitly asked to be enumerated,
which is the only reason it was found rather than shipped.

### H3 — the conditional corrections INSERT-sync loses a legitimate clear

Round 9 made the INSERT-half sync conditional to stop it clobbering a shared body. Codex measured the
other edge: a second-playlist row carrying an explicit empty `corrections` cannot distinguish *"never
had corrections"* from *"the user cleared them"*, so an insert-time clear is silently dropped while
the UPDATE path clears correctly. One silent data loss traded for a narrower one.

Overlaps backlog #23 (corrections as deterministic `{from,to}` pairs). Recorded as High rather than
fixed inline because the honest repairs — a tombstone, or routing corrections writes straight at
`workspace_videos` — change the representation and belong with that item.

### H4 — the fence is optional, so the invariant it enforces is opt-in

`p_worker_id`/`p_job_id` default to null. A caller that omits them at reserve time and then loses its
token has no path at all. Whatever replaces the credential must be **mandatory for paid
reservations**, or the guarantee is a convention again — which is the exact critique round 9 made of
*"'render' is free and never reserved"*.

---

## MEDIUM

- **The guard ratchet still omits `jobs` FKs.** Round 9 widened the *trigger* enumeration to six
  tables and left the FK clause on its original hand list of four, so `jobs_workspace_owner_fk` is
  invisible while the gate prints *"every guard classified"*. Shape #10, committed **inside** the fix
  that was widening an enumeration. Derive the table set instead of listing it.
- **The population ratchet proves two INSERTs, not two callers.** `t_writes` records
  `kind/paid/slot/op` and nothing about who wrote; two fixture inserts in one block satisfy it.
  Record a scenario label and require distinct scenarios.
- Two further Mediums and three Lows in `…-r10-claude.md`, not re-measured here.

## What round 10 CONFIRMED rather than found

- **The temp-copy fix is real.** Codex ran two concurrent mutation suites: both `58/58`, no repo
  diff. This is the one round-9 claim I most wanted an independent party to check, since otherwise I
  would be certifying my own instrument. The repo working tree was clean after both reviewers ran —
  the round-8 collision did not recur.
- Both reviewers verified 119/119 assertions and 58/58 mutations independently. As in round 8, every
  defect was something no instrument could see.

## The decision round 11 cannot start without

The credential question is now open for the **second** time on the same mechanism, and both attempts
failed for reasons that were visible in the repo before either was written. It needs an explicit
decision rather than another inference:

1. **A durable per-attempt secret** — reserve writes the token into the worker's own job row in the
   same transaction, so a restart recovers it. Closes replay *and* restart. Cost: `record_artifact`
   gains a dependency on `jobs`.
2. **An explicit re-adoption RPC** — a restarted worker asks to re-adopt its reservation, audited.
   Keeps the token as the only secret. Cost: a new RPC and a new state.
3. **Revert to round 7's fence** and accept the impostor hole while the credential is designed. The
   spec is not promoted and nothing runs, so this is a real option, and it restores the honest
   worker's path.

**Do not choose by inference. Both previous choices were made that way.**
