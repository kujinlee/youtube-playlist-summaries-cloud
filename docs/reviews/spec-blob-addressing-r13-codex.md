<!-- codex-review: model=gpt-5.5 -->

**Findings Doc**

**Blocking — `jobs_idem_active` does not provide producer execution exclusivity after lease expiry.**

Claim: ADR-0007 deletes the only slot-level in-flight producer guard, but the named successor (`jobs_idem_active`) prevents duplicate job rows, not duplicate live executions of the same job after reclaim.

Evidence:
- The index is row-identity only: `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:11-13` creates `jobs_idem_active` on `(owner_id, playlist_id, video_id, section_id, job_kind, job_version)` where status is queued/active/completed.
- Reclaim makes the same job claimable again: `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:68-75` updates expired active jobs back to `queued`.
- Every worker run starts by sweeping expired leases, then claiming: `lib/job-queue/worker-runner.ts:24-25`.
- The current handler already documents the exact stale-worker/double-Gemini limitation: `lib/job-queue/summary-handler.ts:166-169` says the pre-write abort shrinks the stale-worker window, but “the double-Gemini charge on reclaim is the known AbortSignal-does-not-stop-billing limitation”.
- The current artifact reservation explicitly exists to cover that gap: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:167-170` says without one in-flight reservation per slot, two writers under their own generation ids both call Gemini; `04_artifacts.sql:409-422` says renewal is what fixes a live worker being reclaimed mid-flight.

Reachable caller pair:
1. W1 runs `runOnce`, claims job J, starts Gemini.
2. W1’s job lease expires while W1 remains alive/in-flight.
3. W2 runs `runOnce`, calls `sweepExpired`, J becomes `queued`, W2 claims J and starts Gemini.
4. Under ADR-0007, both producers may write different new generation ids, producing different blob keys and append rows.

This is not a key collision; it is still a paid-work collision. The ADR’s row “producer exclusivity → `jobs_idem_active`” is false for executions, and “pay at most once → `ever_metered`/`reserved_cents`” is only an accounting guard, not a producer-work guard.

Fix: ADR-0007 must either retain a producer in-flight slot guard/renewal mechanism, or explicitly move the artifact lease semantics into the job queue with a measured guarantee that reclaimed live executions cannot both reach paid generation.

**High — render identity is under-specified for multi-source renders.**

Claim: ADR-0007 makes render generation ids hash over `source_generation_ids`, but the schema has one `source_generation_id` column and the ADR defers the set identity decision while relying on it for correctness.

Evidence:
- ADR states render ids are `hash(source_generation_ids, GENERATOR_VERSION)`: `docs/adr/0007-artifacts-are-an-append-only-log.md:89-94`.
- ADR admits multi-generation renders need identity over a set while the schema has one column: `docs/adr/0007-artifacts-are-an-append-only-log.md:122-127`.
- Current schema has only `source_generation_id text`: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:43`.

Recommendation: settle this in ADR-0007. Use a join table for render sources, plus a canonical sorted hash materialized for the render generation id. The join table gives GC and ranking exact source reachability; the sorted hash gives deterministic identity. A hash-only design makes GC and source-currency opaque.

**Medium — renderer version evidence is partly wrong.**

Claim: `GENERATOR_VERSION` exists for HTML/model freshness, but PDF rendering uses a separate `PDF_RENDER_VERSION`; ADR-0007’s single version name is incomplete for render identity.

Evidence:
- HTML constant exists: `lib/html-doc/constants.ts:1-5`.
- PDF cache uses `PDF_RENDER_VERSION`: `lib/pdf/pdf-render-version.ts:5-10`.
- PDF key hashes rendered HTML and truncates SHA-256 to 16 hex chars: `lib/pdf/pdf-render-version.ts:21-22`.

Fix: ADR-0007 should define per-renderer version input, e.g. `{renderer_kind, renderer_version, canonical_source_set}`. Also do not silently carry over the 16-hex PDF cache hash as the generation id hash; append-only identity should use full SHA-256 or a collision-resistant database unique input.

**Medium — H1 is honestly scoped but still leaves immutability to schema, not ADR.**

Adjudication:
- H1 (`service_role` DML bypasses fence): dissolved only for the artifact lease fence, not for append-only/history immutability. ADR is honest at `docs/adr/0007-artifacts-are-an-append-only-log.md:117-120`, but implementation must keep trigger-level immutability.
- H2 (`video_artifacts_generation_complete` misclassified): survives as a guard-classification issue if the trigger remains. If renders get generation ids, the trigger becomes more important, not less.
- H3 (`completed_by_another` wrong outcome): dissolved if `record_artifact` no longer completes pending generations through the old fence; otherwise survives.
- Medium leftovers: guard ratchet omissions survive; population-ratchet weakness survives unless retired; free-slot once-in-life dissolves if render rows are no longer generation-null/free-overwritable; pending biconditional classifications dissolve only if pending state is actually deleted.

Verification: I ran `./docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh`; it passed with `ASSERTIONS_OK`, `ALL_STATEMENTS_OK`, then rollback.

**Verdict: NOT CONVERGED** — Blocking reason: ADR-0007’s replacement matrix falsely assigns producer execution exclusivity and pay-at-most-once to `jobs_idem_active`/job accounting, but the reachable lease-expiry reclaimer path still allows two live paid producers for one slot unless the reservation/renewal concern is restored or moved with an equivalent measured guard.
