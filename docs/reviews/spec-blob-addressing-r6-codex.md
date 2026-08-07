<!-- codex-review: model=gpt-5.5 -->

**JOB 1: Attack Round 5 Fixes**

**BLOCKING**

1. `recorded -> detached` is allowed for every paid kind, so a current summary can be detached and then collected, defeating the new floor.
Scenario: collect `gOLD`, update current summary `gNEW` artifact to `state='detached'`, then update `video_generations.gNEW.body_collected=true`; `forbid_collecting_current()` no longer sees `gNEW` in `video_artifacts_current`, so the summary slot empties.
Evidence: `state` allows `detached` globally in `04_artifacts.sql:27-28`; append trigger allows any recorded paid row to become detached in `04_artifacts.sql:271-284`; GC trigger only checks current view membership in `04_artifacts.sql:229-232`; only dig detach is asserted in `05_assert.sql:261-267`.
Change: constrain `detached` to `kind='dig'`/`slot like 'dig:%'`, and have the trigger permit `recorded -> detached` only for dig rows. Add negative assertions for summary/model/digDeeper detach.

2. `reclaim_expired_reservation()` deletes the only durable attempt counter and does not serialize the handoff, so concurrent reclaimers can reset attempts and re-open the spend path.
Scenario: expired pending row has `lease_attempts=2`; two sessions call reclaim. One deletes and returns `2`; the other returns `0`. If the zero-attempt caller later inserts, it can undercount attempts and bypass the terminal bound the comments rely on.
Evidence: delete-return only stores attempts in a local variable in `04_artifacts.sql:113-119`; prose says “caller carries this” in `04_artifacts.sql:119-120`; the test is single-session only in `05_assert.sql:271-294`.
Change: replace delete-then-external-insert with one reservation RPC that takes an advisory or row lock, atomically deletes/claims, increments attempts durably, and returns `busy | reserved | attempts_exhausted`.

3. `md_hash` is required by schema but has no producer/API path in the spec, so the “reconcileClassA runs unmodified” fix is incomplete.
Scenario: the schema rejects a summary generation without `md_hash`, but `record_artifact(...)` has no `p_md_hash`, `p_card`, or `p_doc_version_major`, and §10.0 only orders the old card-field producer fix. The first implementation either cannot insert summary generations or silently computes hash somewhere outside the declared contract.
Evidence: required by `03_generations.sql:91`; §5.1 RPC signature omits it in `stable-blob-addressing-design.md:786-793`; §10.0 names only card fields in `stable-blob-addressing-design.md:1872-1875`; current cloud worker has `core.mdContent` but does not put `mdGeneratedAt`/`mdCorrectionsHash`/`mdHash` in `video` at `summary-handler.ts:149-164`.
Change: define a summary-generation write API that takes/derives `card`, `doc_version_major`, `produced_at`, and `md_hash = sha256(body)` in the same transaction as the pending artifact reservation. Update §10.0 for all producers, not just `summary-handler`.

**HIGH**

4. `art_key_names_generation` is not a stable blob-address guard; it accepts wildcard generation ids and keys where the generation appears in the wrong path/tenant/video.
Scenario: with an opaque `generation_id` containing `_` or `%`, the `LIKE` pattern matches unrelated path segments; even without wildcards, `OTHER/videos/other/<generation>/x.md` passes for this row as long as the slash-delimited id appears somewhere.
Evidence: `blob_key like '%/' || generation_id || '/%'` in `04_artifacts.sql:76-77`; §4.1 still leaves generation id form open in `stable-blob-addressing-design.md:307`.
Change: parse the key into exact path segments and require `<workspace>/videos/<video>/<generation>/...`, or constrain generation ids to UUIDs and compare with escaped `LIKE` plus anchored prefix.

5. Append-only freezes only `slot`, `generation_id`, and `blob_key`, but mutable provenance/span fields affect ranking and recovery.
Scenario: a stale recorded model can update `source_generation_id` to the current summary and win the source-currency rung without regenerating bytes; a detached dig can have `start_sec/end_sec` rewritten after the source summary is collected.
Evidence: trigger freezes only three fields in `04_artifacts.sql:276-284`; source ranking uses `source_generation_id` in `04_artifacts.sql:206-208`; spans are required because they are durable recovery data in `04_artifacts.sql:68-73`.
Change: freeze `source_generation_id`, `start_sec`, and `end_sec` for recorded paid rows too, allowing only the valid `state` transition.

**MEDIUM**

6. `mdGeneratedAt` is only checked non-null, while both current views and `reconcileClassA` treat it as an ordering key.
Scenario: `mdGeneratedAt='x'` or offset-form timestamps rank deterministically but not necessarily chronologically; malformed values can become current and sync will faithfully reproduce the wrong decision.
Evidence: schema only checks non-null in `03_generations.sql:88`; views order JSON text in `04_artifacts.sql:180` and `04_artifacts.sql:211`; JS compares strings in `reconcile-class-a.ts:9` and `:49`.
Change: enforce canonical UTC ISO strings or store a generated `timestamptz` ranking column while keeping the card value.

7. RLS fix looks correct for tenant isolation, but `anon` is granted select and intentionally sees nothing because no anon policy exists.
Scenario: raw tables and `security_invoker` views deny anon by policy absence; share-token serving still bypasses RLS via `serviceClient`, so it is unaffected today.
Evidence: grants include `anon` in `03_generations.sql:23,103` and `04_artifacts.sql:125,215-216`; policies are `to authenticated` only in `03_generations.sql:24,104` and `04_artifacts.sql:131`; share path reads legacy rows through `serviceClient` in `lib/share/serve.ts:19-40`.
Change: either remove anon grants from these tables/views until an anon policy exists, or document that anon access is service-mediated only.

**LOW**

8. The removed `@<generationId>` suffix is gone from live spec/schema, except historical/review text and one negative assertion.
Evidence: current rule says unchanged slot in `stable-blob-addressing-design.md:1516-1518`; remaining live schema mention is explanatory old behavior in `04_artifacts.sql:259-264`; assertion rejects rename in `05_assert.sql:256-258`.
Change: no design change; keep only if historical context is worth the noise.

**JOB 2: Execute And Mutate**

Baseline verifier did not execute: Docker socket access is blocked by this sandbox.

Measured output:
`permission denied while trying to connect to the Docker daemon socket ... connect: operation not permitted`
then `❌ schema FAILED`.

Scratch schema copy was created at `/private/tmp/blob-addressing-r6-schema-50352`.

Mutation coverage review:
- Covered in assertions: `gen_summary_has_hash`, `art_key_names_generation` basic wrong-generation case, in-flight uniqueness, single-session reclaim, append-only address update/delete/slot rename, current-GC direct collection, RLS authenticated cross-tenant read.
- Not covered: reclaim concurrency/attempt reset, stale writer after reclaim, summary/model/digDeeper detach rejection, provenance/span immutability, exact blob-key workspace/video/path position, LIKE wildcard generation ids, anon behavior.
- Masking risk: the `art_key_names_generation` fixture only proves “some other generation rejected”; it does not prove the row’s key belongs to the same workspace/video or correct path position.

**JOB 3: Invariants**

Rule 14’s floor is not true yet. `state='recorded' and not body_collected` can still be emptied by first moving the current summary out of `recorded` via the over-broad detach transition.

Rule 19’s determinacy is directionally right, but the busy/reclaim branch is not safely exitable because attempt state is not durable across delete and the reservation handoff is not atomic.

Append-only as “address of recorded paid rows” is too narrow. The invariant should be “recorded paid row identity, address, provenance, and recovery facts are immutable; only dig may transition to detached.”

Verdict: **NOT CONVERGED**. New Blocking and High remain.
