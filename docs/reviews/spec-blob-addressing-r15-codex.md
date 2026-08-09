<!-- codex-review: model=gpt-5.5 -->

**Round 15 Findings**

Schema gate: `./docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` executed successfully against live Postgres and rolled back. Worktree remained clean.

## Blocking

### B1 — The scope split is incomplete: ADR-0007 still contains normative render-addressing decisions after declaring render addressing out of scope.

Evidence:

- ADR says render addressing was split and “does not attempt a third design”: `docs/adr/0007-artifacts-are-an-append-only-log.md:280-288`.
- It then still asserts render-column semantics: `docs/adr/0007-artifacts-are-an-append-only-log.md:293-295` says exactly one of `generation_id` / `render_id` is non-null, but executable schema has no `render_id`: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:34-43`.
- It still gives mechanical render consequences: `docs/adr/0007-artifacts-are-an-append-only-log.md:330-335` says `video_artifacts_free_uq` is replaced by `(workspace_id, video_id, slot, render_id)` and `art_paid_has_generation` becomes a two-column rule.
- That directly contradicts Consequences: `docs/adr/0007-artifacts-are-an-append-only-log.md:352-358` says `video_artifacts_free_uq` stays until render addressing is settled.
- It also still decides the withdrawn address: `docs/adr/0007-artifacts-are-an-append-only-log.md:440-443` says `Address = sha256(rendered bytes)`, even though the same ADR marks that design withdrawn at `docs/adr/0007-artifacts-are-an-append-only-log.md:273-276`.

Fix: remove render-addressing mechanics from ADR-0007. Keep only: render addressing unresolved, `video_artifacts_free_uq` stays, provenance join table if still in coordination scope, and link to the render brief.

### B2 — The `model` GC-floor successor is not reliable for the full paid-call window because the lease can expire before `generateMagazineModel` finishes.

Evidence:

- ADR makes the live lease the `model` GC floor: `docs/adr/0007-artifacts-are-an-append-only-log.md:381-384`, and says “the sweeper reads the lease” at `docs/adr/0007-artifacts-are-an-append-only-log.md:396-399`.
- The lease is readable by the sweeper’s role: `supabase/migrations/0012_serve_model_charge.sql:15-17`.
- TTL is 180s: `supabase/migrations/0012_serve_model_charge.sql:20-22`.
- Reserve creates or renews exactly that TTL, with no renewal during generation: `supabase/migrations/0020_reservation_release.sql:217-223`.
- The magazine path can exceed 180s: `GENERATE_JSON_RETRIES = 2`, so magazine gets 3 passes at `lib/gemini-cost.ts:20-29`; each pass uses `timeout: REQUEST_TIMEOUT_MS` at `lib/gemini.ts:246-260`, where `REQUEST_TIMEOUT_MS = 60_000` at `lib/gemini.ts:90-94`; retry sleeps add more time at `lib/gemini.ts:265-268`. `generateMagazineModel` calls this after reserve at `lib/gemini.ts:547-549`.

Caller reaching state: `resolveMagazineModel` reserves at `lib/html-doc/serve-doc.ts:73-80`, then generates and writes at `lib/html-doc/serve-doc.ts:101-126`. A slow third attempt can still succeed after the 180s lease has expired.

Fix: do not use `serve_model_charge` as a correctness floor without renewal or a separate non-expiring in-flight marker. Options: route `model` through jobs, add a renewal RPC/heartbeat, or restore an age/grace predicate for pre-publication generations.

## Low

### L1 — Sentinel gate text still says ADR-0007 removes the `generation_id` conflation.

Evidence:

- `scripts/check-sentinel-meanings.py:52-53` says `ADR-0007 removes this`.
- The same block now says the opposite: `scripts/check-sentinel-meanings.py:91-99` says ADR-0007 no longer removes it and render addressing is split out.
- ADR cites the old deletion-trigger line as `scripts/check-sentinel-meanings.py:90`, but the relevant text starts at `scripts/check-sentinel-meanings.py:91`.

Fix: change the short meaning string to “CONFLATED — see CONJUNCTION_OK; render-addressing slice removes this” and update the ADR citation to the actual line.

## What I Could Not Break

- `video_artifact_sources ... on delete cascade`: I could not find a visible GC window. A cascade delete of a render and its join rows is one SQL statement, and GC is an `update body_collected`, not a generation delete, so the cascade does not erase protection before collection.
- `least(sum(attempt_count), max_serve_attempts - 1)`: with `max_serve_attempts = 1`, the clamp yields `0`, which is correct because the next reserve increments to the one allowed attempt.
- Dropping `source_generation_id`: outside the executable schema, mutation scripts, docs, and guard metadata, I found no TS runtime consumer. The planned ranking shape `not exists (source not current)` is the right universal quantifier if the join table contains the complete source set.
- Reworded execution row: I found no surviving dependency on mutual exclusion for job execution; the ADR now consistently describes bounded stale-writer windows and idempotent merge-safety.
- Citation spot-check: the new/moved `serve_model_charge` TTL/attempt citations resolve to the claimed lines.

NOT CONVERGED — blocking reason: the split left live normative render-addressing decisions in ADR-0007, and the new `model` GC-floor successor does not cover paid calls that outlive the 180s unrenewed serve lease.
