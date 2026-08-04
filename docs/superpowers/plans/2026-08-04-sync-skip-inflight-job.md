# A3 refuses to relocate a video with an in-flight job (backlog #17, partial)

**Scope: the cheap guard, not the full fence.** Closes the *wide* window in the worker-vs-sync race —
the minutes a job spends in transcription + Gemini — and leaves a millisecond one. Backlog #17 stays
open for the durable fix.

## Why

`summary-handler.ts:95-96` pins `baseName` from the serial it reserved, then runs `summaryCore`
(transcript + Gemini) for **minutes** before persisting at `:156`. If a sync relocates that video's
base inside that window, the stale persist lands afterwards and wins on the key, because
`persist_summary` resolves it as `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')`
(`0021:135` — payload wins) while `serialNumber` is restored from the row. Net: row says serial 3,
key says `007_alpha.md`, and the paid digs sit at `dig/003_alpha/` with `dig/007_alpha/*` already
deleted by A3's cleanup.

`dig-handler.ts:51-57` pins `base` the same way before its own Gemini call, so **dig jobs are exposed
too** — the guard must not filter by `job_kind`.

**Lease-fencing would not fix this.** The worker's lease is valid throughout; A3 never touches the
job. What goes stale is the *serial*. (`summary-handler.ts:167-170` records an earlier decision to
defer lease-fencing on the grounds that "a stale write is idempotent and non-corrupting" — true when
written, **invalidated by A3**, which makes a stale write corrupting.)

## Design

The guard lives **inside `reconcileCloudBase`**, not in its caller — the same reasoning as the
`claimVideoSlot` re-claim guard (`local-metadata-store.ts:29-34`): a guard in the primitive cannot be
bypassed by a future caller.

`reconcileCloudBase` gains a required probe. The result is a **union, not a boolean**, because
"no jobs" and "could not read the job table" must not collapse — the same absent-vs-unreadable rule
that produced 1 Blocking and 3 Highs in Stage 3:

```ts
export type InFlightJobProbe = (videoId: string) => Promise<
  | { ok: true; inFlight: boolean }
  | { ok: false; cause: unknown }
>;
```

Required, not optional — an optional member does not propagate and callers silently inherit the
unguarded original (`docs/dev-process.md`, cross-module nullable rule).

Two new refusal reasons on `SerialReconcileResult`: `job-in-flight` and `job-probe-unreadable`.
Both are refusals, so they reuse the existing "throw → caught per video → `report.errors` → no
baseline advanced → next run heals" path. Nothing new is needed in `sync-run`'s error handling.

## Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | No divergence → probe never runs | `describeDivergence` says not diverged | `{ok:true, action:'agreed'}`; probe **not called** (no query when nothing would move) |
| 2 | Nothing to reconcile toward → probe never runs | `localVideo.serialNumber == null`, or `!cloudVideo.summaryMd` | `{ok:true, action:'agreed'}`; probe **not called** |
| 3 | Diverged, no job in flight | probe → `{ok:true, inFlight:false}` | relocates exactly as before — existing behaviour unchanged |
| 4 | Diverged, job in flight | probe → `{ok:true, inFlight:true}` | `{ok:false, reason:'job-in-flight'}`; **zero copies, zero deletes, metadata untouched** |
| 5 | Probe reports it could not read | probe → `{ok:false, cause}` | `{ok:false, reason:'job-probe-unreadable', cause}` — **fail closed**; unreadable ≠ no jobs |
| 6 | Probe throws | probe rejects | same as #5, caught inside `reconcileCloudBase`; a throwing probe must not abort the whole sync run |
| 7 | Probe runs before ANY write | diverged + in-flight | no blob is copied and no metadata written before the refusal — assert via a fault-injecting blob store that would record a `put` |
| 8 | Refusal surfaces per video | `runSync` with an in-flight job on a diverged video | `report.errors` names that `videoId`; **no baseline advanced**; that video's Class-A transfer does **not** run |
| 9 | Other videos still sync | one video blocked, another clean | the clean video completes normally in the same run |
| 10 | Only future writers block | job `status` in `queued`/`active` | `completed`, `failed`, `cancelled` do **not** block — they will never write again |
| 11 | Expired lease still blocks | `status='active'`, `lease_expires_at` in the past | **blocks** — the reaper may reclaim and retry, which writes |
| 12 | Every job kind blocks | `job_kind` = `summary` **or** `dig` | both pin `base` before a long Gemini call; do not filter by kind |
| 13 | Scoped to this playlist | a job for the same `video_id` under a **different** `playlist_id` | does **not** block — `base` is per-playlist, so that job writes a different address |
| 14 | One probe call per video | diverged video | probe called exactly once, not once per blob |

## Files

- `lib/cloud-sync/reconcile-serial.ts` — `InFlightJobProbe` type, two refusal reasons, the guard.
- `lib/cloud-sync/sync-run.ts` — `SyncDeps.inFlightJob` (required), threaded into `reconcileCloudBase`.
- `lib/cloud-sync/in-flight-job.ts` *(new)* — the Supabase implementation of the probe. Returns
  `{ok:false, cause}` on any query error rather than throwing.
- `scripts/cloud-sync.ts` — construct the real probe from the authenticated client.
- `tests/integration/helpers/cloud.ts` — `syncDeps()` supplies a probe.

## Verification

Unit tests for #1–#7 and #14 against `reconcileCloudBase` directly (fake probe); `runSync`-level tests
for #8–#9; integration for #10–#13 against real `jobs` rows. Mutation-check the guard: remove it,
confirm tests go red, restore — **committing the implementation first**, since `git checkout` also
reverts an uncommitted fix.
