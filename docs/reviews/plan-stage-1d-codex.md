# Codex adversarial review — Stage 1D implementation plan (round 1)

**Date:** 2026-07-08 · task `task-mrcpnin3-1bcsda` · Target: `docs/superpowers/plans/2026-07-08-stage-1d-cost-guardrails.md`

## Blocking
- **B1 — T7/T8/T12 ordering:** the fail-closed transcribe-fallback flag is consumed (T7/T8) before T12 creates it. *Fix: define the flag with a fail-closed default early; T12 verifies+flips.*
- **B2 — T9 producer has no source for `max_duration_seconds`** (Enqueuer is booleans-only; session can't read service-only `guardrail_config`) → implementers hard-code 1800, violating the 3-site config coupling. *Fix: add a service-side config reader (`enqueuer.getGuardrailConfig()`).*
- **B3 — retry constants duplicated** across `gemini-cost.ts` and `gemini.ts` (two sources of truth). *Fix: define once, import into the other; the signature defaults and `perRunWorstCents` use the same values.*

## High
- **H1 (T5)** — RPC args must be `p_owner_id`/`p_playlist_id`/…/`p_enqueue_ip`, not camelCase.
- **H2 (T1)** — new read-only policies break `schema.test.ts`'s exact `pg_policies` assertion. *Fix: update that assertion.*
- **H3 (T1)** — `spend_ledger` client read: no grant likely yields an *error*, not `[]`. *Fix: assert `error` truthy.*
- **H4 (T2/T3)** — singleton `guardrail_config`/`quota_allowance`/`spend_ledger` mutated without `beforeEach` reset → order-dependent failures. *Fix: reset in `beforeEach`.*
- **H5 (T2)** — omits required §8 cases: UTC-month rollover, same-owner parallel distinct-video quota race, anon vs registered allowance, swept expired lease at `attempts=1` → `dead_letter`. *Fix: add them.*
- **H6 (T11)** — only calls `perRunWorstCents`; if that helper is wrong the guard still passes. *Fix: recompute independently / assert it uses every exported constant incl. audio.*
- **H7 (T13)** — inventory says "10" but lists 11; use actual `rg` output and classify by change type.

## Medium
- **M1 (T2)** — state the exact `ON CONFLICT (owner_id, playlist_id, video_id, section_id, job_kind, job_version) WHERE status in (...)` target.
- **M2 (T9)** — VOD-only block has no data source: `VideoMeta`/`fetchPlaylistVideos` don't expose `liveBroadcastContent`. *Fix: add a task to fetch `snippet.liveBroadcastContent`, extend `VideoMeta`, map to a block.*
- **M3 (T8)** — enumerate existing tests broken by the caps signatures (`summary-core.test`, `transcript-source.test`, `gemini.test`, `gemini-signal.test`).
- **M4 (T8)** — add a handler integration test that flips `guardrail_config.max_duration_seconds` and checks accept/reject follows the DB value.
- **M5 (T4)** — `mapEnqueueError` return type vs "unknown returns same object".

## Low
- **L1** — migration `0011` mutated across T1/T2/T3 commits (partial mid-way). *Fix: note per-task `db reset` applies the file-so-far coherently, or squash.*
- **L2** — T12 recorded live-gate outcome isn't a named artifact. *Fix: name the file; assert the flag is consumed fail-closed.*
