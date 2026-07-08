# Dual adversarial re-review — Stage 1E-c spec **v3** (round 3, convergence)

**Date:** 2026-07-08
**Reviewers:** Codex (`task-mrc9prg8`, fresh) + Claude (Opus, fresh subagent).
**Target:** `docs/superpowers/specs/2026-07-08-stage-1e-c-progress-polling-design.md` (v3 → v4 polish).
**Scope:** verify the v3 deltas (migration `DROP`, test deltas, empty short-circuit, disjoint counts, middleware reframe) are genuine; hunt for defects the v3 edits introduced.

---

## Verdict: CONVERGENCE — no new Blocking or High from either reviewer.

Per the iterate-to-convergence rule, round 3 is a **valid stopping round**: a full dual re-review returned no new Blocking/High, only one Medium + Lows (all one-line clarifications). Applied as v4 polish; no further round required.

| Reviewer | Blocking | High | Medium | Low |
|---|---|---|---|---|
| Codex | 0 | 0 | 0 | 1 (401 cookie replay) |
| Claude | 0 | 0 | 1 (mapper shape) | 3 (503-row carve-out, test-enum, extractPlaylistId guard, 401 cookie) |

### v3 fixes verified genuine (both reviewers)
- **`0010` DROP+create** — matches the `0009:15` precedent; `void→int` now legal; re-revoke/re-grant as `0008:91-92`. Claude used `drop function if exists …` (strictly safer).
- **Empty/all-skipped short-circuit** (§3.2 step 5) — returns `playlistId:null` before `resolvePlaylistId`; no orphan row; the step-8 `succeeded===0→503` "attempted≥1" premise holds because step 5 already returned for `enqueueable.length===0` (no false 503).
- **Disjoint counts** — `created+joined+failed===enqueueable.length` (mutually-exclusive try/catch) and `enqueueable+skipped===videos.length` ⇒ sum `===videos.length` in every branch (empty, all-skipped, partial, all-fail, all-join). No double-count, no gap.
- **Test-delta `:108`** — confirmed the **only** raise-assertion on cancel in the repo; `runner.test.ts:52` ignores the return; `supabase-job-queue.ts:25` is the only return consumer.
- **Middleware 401** — status correct; the `!user` branch has no session to refresh, and the current `redirect(...)` already discards `response`'s cookies, so 401 is behaviorally identical (see the L4/Codex cookie nuance below).
- **`resolvePlaylistId` `.upsert().select('id').single()`** — returns the modified row on conflict (PostgREST returns modified rows); idempotent re-submit does not throw.

### Residuals applied in v4 (polish, not a new round)
- **M1 (Claude, Medium)** — the mapper's `{ok}|{skip}` signature didn't carry `videoId`, but `JobFanoutResult` requires `videoId` on all variants, and the skip key is `skipped` not `skip`; the v3 step-5 `jobs: skipped` return exposed it. **Fix applied:** mapper returns `{ videoId, ok }|{ videoId, skipped }`; §3.2/§3.5/§3.1 aligned.
- **L1** — §6 now carves out that the `503` path leaves a legitimate idempotent row (the FK requires it before enqueue) — inherent, accepted.
- **L2** — §3.7 now notes the two benign references (`producer.test.ts:50`, `worker-runner-runtime.test.ts:26`) need no change, so "enumerated, complete" is literally true.
- **L3** — §3.2 now specifies the route-level `extractPlaylistId` call is try/caught → `400` (else an un-caught throw → 500).
- **L4 / Codex Low** — §3.1 now specifies the JSON `401` must replay cookies scheduled on `response` (`headers: response.headers`) so a stale-token clear isn't dropped.

### Convergence trail
R1 (3B/3H) → v2 → R2 (2 new B/H inside the fix) → v3 → **R3 (0 new B/H) → converged.** The re-review loop earned its cost: R2 caught a broken migration and a silently-inverted test that a single round would have shipped.
