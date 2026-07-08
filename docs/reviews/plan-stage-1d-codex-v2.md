# Codex plan review — round 2 (v2) · task `task-mrcq4d9l-emb4ku`

**Verdict: no new Blocking; 2 High + 1 Medium + 1 Low (all fixed in plan v3).**

## High
- **New-RPC grants omit explicit revocation.** T2/T3 only `grant execute to service_role`; repo precedent (`0009:45`, `0010:21`) does `revoke all … from public` first. Incomplete "service-role-only" fix; can false-green "any error" tests. *Fix (v3): `revoke all on function … from public, anon, authenticated;` + tests assert `42501`.*
- **`MAX_SUMMARY_ATTEMPTS` still duplicated.** T6 wires only the retry constants; the runtime loop uses `gemini.ts:201 const MAX_SUMMARY_ATTEMPTS = 4`. If `gemini-cost.ts` re-exports it, two sources → guard couples to the wrong one. *Fix (v3): T6 deletes the local const, imports from `gemini-cost.ts`.*

## Medium
- **Required `VideoMeta.liveBroadcastContent` breaks existing typed fixtures** (`producer-roundtrip`, `video-meta-to-payload.test`, `producer.test`, `pipeline.test`) → T9 `tsc` gate fails outside its named files. *Fix (v3): `.optional()`; producer treats absent as VOD (blocks only explicit live/upcoming).*

## Low
- `beforeEach` reset omits `dig_est_cents`/`dig_max_attempts` and the dig allowance rows. *Fix (v3): reset every column + all 4 allowance rows.*
