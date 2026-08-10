<!-- codex-review: model=gpt-5.5 -->

# Round 14 Findings — ADR-0007 Revised

Gate strength: not downgraded. I ran `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh`; it ended with `ASSERTIONS_OK`, `ALL_STATEMENTS_OK`, `ROLLBACK`, `schema verified`.

Working tree remained clean.

## Blocking

### B1 — The render identity is not connected to the render blob key, so the ADR does not actually make renders append-only.

Evidence:

- `docs/adr/0007-artifacts-are-an-append-only-log.md:253-254`: render identity is `sha256(rendered bytes)` and the key keeps `<ws>/videos/<vid>/renders/...`.
- `docs/adr/0007-artifacts-are-an-append-only-log.md:319-321`: the ADR claims byte changes land on a new address.
- `docs/adr/0007-artifacts-are-an-append-only-log.md:328-330`: uniqueness becomes `(workspace_id, video_id, slot, render_id)`.
- `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:280-281`: the existing render key shape is only `<ws>/videos/<vid>/renders/<name>.html|pdf`.
- Current production PDF cache proves the missing part matters: `lib/pdf/pdf-render-version.ts:21-22` includes a hash in the object name, while the ADR never states the equivalent `<render_id>` segment for the new `renders/` key.

If `render_id` is not in `blob_key`, two different renders of one slot can have different DB rows but the same object key and overwrite. If it is in `blob_key`, the ADR must say where, and must preserve the §8 classifier by keeping path segment 4 as `renders`.

Fix: specify the render key template, for example `<ws>/videos/<vid>/renders/<slot-or-kind>/<render_id>.<ext>` or another exact shape. Add a constraint tying `blob_key` to `render_id` and preserving `split_part(blob_key, '/', 4) = 'renders'`.

## High

### H1 — The revised ADR still contains the old false concern table immediately after the corrected table.

Evidence:

- Corrected row: `docs/adr/0007-artifacts-are-an-append-only-log.md:82-85` splits enqueue dedup, execution exclusivity, accounting, and bounded spend.
- Stale duplicate row: `docs/adr/0007-artifacts-are-an-append-only-log.md:98-107` again says `jobs_idem_active` provides “producer exclusivity” and “producer idempotency”, and `jobs.ever_metered + reserved_cents` is “pay at most once”.
- Round 13 explicitly rejected those claims: `docs/reviews/spec-blob-addressing-r13-coordinator.md` says the table was false in those rows.

Fix: delete the duplicate old section at lines 98-116. In a document whose method is “one concern, one mechanism”, contradictory tables are not harmless editorial residue.

### H2 — `attempt_count` migration by `SUM` can lock an otherwise-working document for the rest of the UTC day.

Evidence:

- ADR claim: `docs/adr/0007-artifacts-are-an-append-only-log.md:156-160` says SUM is safe and any over-tightening clears next day.
- The RPC returns `attempts_exhausted` when `attempt_count >= max_serve_attempts`: `supabase/migrations/0012_serve_model_charge.sql:78-80`.
- The caller maps `attempts_exhausted` to a 503, not stale fallback: `lib/html-doc/serve-summary-core.ts:118-123`.
- Stale fallback is only for `owner_over_budget`: `lib/html-doc/serve-doc.ts:90-95`.
- Spend is already accounted separately in `serve_owner_budget` and `spend_ledger`: `supabase/migrations/0020_reservation_release.sql:237-247`.

A user with the same video in multiple playlists can have per-playlist counts that were each below K, then migration SUM collapses them to K or above and immediately returns `attempts_exhausted`.

Fix: do not justify SUM as universally safe. Either use MAX for lease-attempt state while relying on the spend ledgers for accounting, or explicitly accept and document the one-day availability regression with a migration test.

### H3 — The ADR contradicts itself on whether `video_artifacts_free_uq` is deleted or replaced.

Evidence:

- Replacement required: `docs/adr/0007-artifacts-are-an-append-only-log.md:328-330`.
- Later consequence says deleted: `docs/adr/0007-artifacts-are-an-append-only-log.md:346-347`.

Fix: say “replace `video_artifacts_free_uq` with `video_artifacts_render_uq` on `(workspace_id, video_id, slot, render_id)`” in Consequences. Do not list it as simply deleted.

## Medium

### M1 — `video_artifact_sources on delete restrict` is underspecified against workspace/video cascade paths.

Evidence:

- Existing artifacts cascade from `workspace_videos`: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:83-84`.
- `workspace_videos` cascades from `workspaces`: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql:48-49`.
- ADR only says the new join table is FK’d to `video_generations` with `on delete restrict`: `docs/adr/0007-artifacts-are-an-append-only-log.md:416-417`.

The ADR does not state whether `artifact_id` cascades, whether the FK is deferrable, or whether deleting a workspace/video first deletes source rows before restricted generations. That is exactly the kind of delete-path ambiguity §8 has repeatedly failed on.

Fix: define both FKs and delete actions explicitly. Add a measured assertion that deleting a workspace with sourced renders succeeds, while deleting an individually referenced generation is restricted.

## What I Could Not Break

- The revised model exception is real and argued: `serve_model_charge` remains a separate mechanism because the serve path has product behavior not present in jobs.
- The workspace/owner re-key is not obviously contradictory in this slice: `workspaces.owner_id` is unique in `schema/01_workspaces.sql:15`, and `(workspace_id, owner_id)` has an FK target at `schema/01_workspaces.sql:16`.
- The heartbeat abort row is true for both checked job handlers: summary checks `ctx.signal.aborted` before write at `lib/job-queue/summary-handler.ts:166-170`; dig checks it before write at `lib/job-queue/dig-handler.ts:117-119`.
- The schema verifier passed locally inside rollback.

NOT CONVERGED — Blocking reason: render identity is not mechanically tied to the render blob key, so the ADR’s new render append-only mechanism is under-specified and may still overwrite.
