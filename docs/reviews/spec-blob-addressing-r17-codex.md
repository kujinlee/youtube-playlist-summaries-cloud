<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking — No replacement writer creates `video_generations` at record time.**  
Evidence: the ADR deletes `reserve_artifact_slot` and says `record_artifact` “becomes an append” at `docs/adr/0007-artifacts-are-an-append-only-log.md:389-391`, while also admitting `reserve_artifact_slot` is the only production `video_generations` insert at `docs/adr/0007-artifacts-are-an-append-only-log.md:446-448`. Current schema confirms that insert is inside `reserve_artifact_slot` at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:307-312`, and current `record_artifact` only `UPDATE`s an existing pending generation gated by `g.state = 'pending'` and `g.reserved_by = p_token` at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:555-565`. The artifact FK requires the generation to exist before the artifact row at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:85-86`.  
Fix: specify the new `record_artifact` generation insert explicitly: insert the complete `video_generations` row first, then insert the artifact row in the same transaction or writable CTE, with the `pending`/`reserved_by` predicates removed and conflict/idempotency outcomes defined.

**High — §8’s “existing orphan sweeper” is prose, not an existing executable mechanism.**  
Evidence: ADR-0006 only says GC “needs a grace period” at `docs/adr/0006-stable-blob-addressing.md:42-46`; the current `BlobStore` exposes `list()` as keys only at `lib/storage/blob-store.ts:78-79`, Supabase strips storage object metadata at `lib/storage/supabase/supabase-blob-store.ts:121-126`, and local listing uses `stat()` only to filter files then returns keys at `lib/storage/local/local-blob-store.ts:81-86`. I found no production orphan sweeper implementation; the schema only documents that §8’s age predicate belongs to a future sweeper at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:868-875`.  
Fix: either stop calling it existing, or specify the sweeper and the age source concretely, e.g. storage object `updated_at`/`created_at` via a storage-specific query or a `BlobStore.listWithMetadata()` contract.

**Medium — The completeness-constraint argument overstates non-summary paid kinds.**  
Evidence: the ADR says the four completeness constraints demand `card`, `md_hash`, `doc_version_major`, and `produced_at` once `pending` is gone at `docs/adr/0007-artifacts-are-an-append-only-log.md:449-454`, but the schema requires `card`, `doc_version_major`, and `md_hash` only for `kind = 'summary'` at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql:395-412`; only `produced_at` is required for every complete generation at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql:394`. The `model` serve path currently generates then writes only the model envelope at `lib/html-doc/serve-doc.ts:112-125` and `lib/html-doc/model-store.ts:45-51`.  
Fix: restate record-time insertability per kind: `summary` needs all four summary fields; `model`/`dig`/`digDeeper` need at least `produced_at` unless the ADR adds new constraints for them.

**Measured**

`docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` ran successfully against live Postgres and rolled back. Important caveat: the executable schema is still the pre-dissolution schema with `reserve_artifact_slot`, `pending`, leases, and `record_artifact`’s pending update path intact.

**What I Could Not Break**

M1’s restated bound is coherent: the ADR correctly says the pending-transition permissions must be removed with `pending` at `docs/adr/0007-artifacts-are-an-append-only-log.md:514-518`.

The round-16 reconciliation edits are present: front matter says no GC successor at `docs/adr/0007-artifacts-are-an-append-only-log.md:8-11`, the “nothing survives” paragraph says the same at `:24-28`, the concern table row was updated at `:101`, and the Consequences block records deletion/addition/reinstated grace at `:389-400`.

I found no surviving live proposal to keep `in_flight_until`, a per-kind successor, or a vacated-but-replaced GC floor; remaining mentions are historical/refutation context.

**NOT CONVERGED**

Blocking reason: the dissolution depends on a record-time `video_generations` insert, but the ADR deletes the only production insert and does not specify the replacement writer.
