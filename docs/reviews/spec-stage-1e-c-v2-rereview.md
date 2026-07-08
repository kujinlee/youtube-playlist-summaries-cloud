# Dual adversarial re-review — Stage 1E-c spec **v2** (round 2)

**Date:** 2026-07-08
**Reviewers:** Codex (`task-mrc9ig80`, fresh — the `--resume` attempt `task-mrc99njo` failed on attach in 3s) + Claude (Opus, fresh subagent).
**Target:** `docs/superpowers/specs/2026-07-08-stage-1e-c-progress-polling-design.md` (v2 → produced v3).
**Scope:** verify each round-1 finding is genuinely fixed; hunt defects the v2 fixes introduced.

---

## Verdict: all 14 round-1 items genuinely RESOLVED; the v2 cancel-RPC fix introduced new defects.

**Both reviewers independently converged on the same four new findings** (strong signal). Severity differs slightly between them; the higher is taken.

| New finding | Codex | Claude | Fixed in v3 |
|---|---|---|---|
| **Migration `0010` uses `CREATE OR REPLACE` for a `void→int` return-type change → Postgres rejects it; needs `DROP FUNCTION` first** (repo precedent: `0009:15` drops `enqueue_job`) | **Blocking** | **Blocking** | ✅ §3.7 now `drop function if exists request_cancel_job(uuid);` then `create` + re-grant |
| **Empty/all-skipped playlist still creates an orphan `playlists` row** (resolvePlaylistId ran regardless of `enqueueable.length`) | **High** | Low | ✅ §3.2 step 5 short-circuits **before** resolvePlaylistId when `enqueueable.length===0` → `playlistId:null`, no row |
| **`counts.enqueued` overlaps `counts.joined`** → a client summing buckets double-counts joins | Medium | Medium | ✅ §3.2/§4.1 disjoint: `enqueued`=new, `joined`=idempotent, `enqueued+joined+skipped+failed===videos.length` |
| **`0010` silently breaks an existing raise-asserting test** (`job-queue-producer.test.ts:108`) | Low | **High** | ✅ §3.7 enumerates the exact deltas (`foreign → error:null, data:0`; `own → data:1`); notes `job-queue-runner.test.ts:52` unaffected |

### Round-1 verification (both reviewers)
Date poison (B/H1), all-failed→200 (H), pre-fetch/cap orphaning for 4xx/5xx (H — empty/all-skipped residual now closed above), unauth→401 (B/M), cancel UUID (M), rollup scope (M), `resolvePlaylistId` atomic owner-scoped (M/L), error mapping (M), version literal (L), resolver URL (L), dig cancel scope (L) — **all confirmed genuinely fixed, not reworded.** Codex additionally verified `.upsert(...).select('id').single()` returns the modified row on conflict (PostgREST `.select()` returns modified rows) — so idempotent re-submit does not throw.

### Other v3 edits from this round
- Middleware reframed: `/api/*` is **already** `authenticated`+307-redirect; the change adjusts only that branch's unauth *response* to a JSON `401` (no new route category). Blast radius over ~10 existing `/api/*` routes documented as safe (working authenticated flows carry a user → never hit the branch); a regression smoke test pins it.
- §3.5 parenthetical corrected: the 1E-b handler is verified pure pass-through (`summary-handler.ts:119-122`), so an absent optional is omitted on serialization — **no** worker conditional-spread needed.
- `AllEnqueueFailedError` carries `playlistId` for the `503` body.

### Convergence status
Round 2 surfaced **1 new Blocking + 1 new High** — inside the round-1 Blocking fix (the migration). Per the iterate-to-convergence rule this is **not** a stopping round; a **round-3 re-review** (focused on the migration DDL, the test deltas, the empty-short-circuit, and the disjoint counts) is required before the human-approval gate.

**Note on Codex resume:** the `--resume` re-review failed to attach (3s failure); a fresh Codex thread was run in its place per `docs/plugins.md` (one quick re-run, then proceed) — it produced the findings above, so the dual-review gate is satisfied for this round.
