# Whole-Branch Holistic Review — Stage 1F-a (authorized summary-HTML serving)

**Range:** `master` (12a9f88) .. HEAD (235fd09) · 8 implementation tasks + committed per-task review trail
**Reviewer:** Claude (opus), final holistic pass after all per-task gates. Execution: SDD.
**Verification (independent run):** `tsc` clean; unit **1746/1746**; integration **182/182 + 2 expected skips** (`supabase db reset` clean, 12 migrations).

## Verdict: READY TO MERGE (no new Critical/High)

Money path bounded end-to-end; service_role genuinely off the serve path; CSP strict/coherent; cross-task interfaces line up. All new findings are Low/informational; all 7 deferred minors triaged OK-TO-DEFER.

## Money-path + auth-boundary assessment (traced end-to-end)
- **Spend bounded:** route 409s a lost/repair-needed blob **before** `resolveMagazineModel`, so it never reserves. Charge ⟺ RPC `reserved` ⟺ exactly one `generateMagazineModel` + one `writeModelEnvelope` upsert; `v_result:='reserved'` set only AFTER the cap UPDATE succeeds; `at_capacity` rolls the claim back via savepoint. No status charges-but-skips-generation; no non-`reserved` status fires a paid call (exhaustive `switch` + `default: throw`). Fresh/cached doc never reserves (B1). Drift/version-bump self-heals at exactly-K/day then 503; abort/failure → lease TTL-expires, no double-charge, no release lever. `base` (serial_slug cache key) and `videoId` (RPC charge key) derived independently + deterministically per doc; the `html-serve-cloud` coherence test pins they never swap.
- **Auth boundary:** service_role off the serve path — `createServerSupabase` uses the anon key, route builds the bundle from that session client (B20 test throws otherwise), `check:confinement` confirms the route never imports `service.ts`; the only elevated surface is the `SECURITY DEFINER` reserve RPC (owner from `auth.uid()` internally, re-verifies owned+`promoted` before money). Owner isolation via RLS + explicit playlist-row owner assert; UUID→400 before any DB call.

## New cross-task findings — all Low / informational
- **L1 — Registered residual = up to the WHOLE shared cap, not "a fraction."** `20·5·6 = 600¢ ≥ 500¢` daily cap. D10/§9 phrase it as "a bounded fraction," but a single registered account's $0 reclaim-loop can exhaust the entire shared `spend_ledger` daily budget (denying ingestion + other serves). Attributable (owner_id on marker), explicitly deferred to 1G, recorded in the invariant test as known-and-accepted. **Not blocking** — but the spec's "fraction" wording undersells it; stated honestly in the PR body. Anon (common case) stays hard-bounded (60 ≤ 100).
- **L2 — Serve + ingestion share one never-released daily cap.** Every first-view books `magazine_est_cents` of `reserved_cents` (reconcile deferred, matching 1D). Intended single kill-switch; on a busy day serve-materialization competes with enqueue for the same $5. Observation.
- **L3 — Orphaned staging blobs.** A worker attempt that uploads a uuid-staged blob then crashes before `promote` leaves an un-GC'd `_staging/<uuid>/…` object (worker MD path only; storage leak, not money/correctness; mirrors local store). Defer.

## Deferred-minor triage — ALL OK-TO-DEFER
- **T4-a** (uuid uniqueness single-call): impl is `crypto.randomUUID()` (self-evidently unique); tests assert uuid-shape + `!==` old key. 2-call distinctness = cheap follow-up, negligible residual risk. Not a merge gate.
- **T4-b** (mislabeled "swallows move error" test): cosmetic; real race covered by F5. Rename when convenient.
- **T6** (in_flight route-level race): the money-critical race (RPC single-flight) has real `Promise.all` coverage (`serve-model-charge.test.ts`); only the HTTP wrapper is untested and adds no new race.
- **T7-a** (no full-stack route→DB E2E): both halves covered (route logic mocked + primitives on real DB + `html-serve-isolation` real RLS gates). Nice-to-have.
- **T7-b** (400-before-401 on unauth dig-deeper): leaks nothing; standard static-validation-before-session ordering.
- **T2** (`assertMagazineInputWithinCap` no AbortSignal): not money path; `countTokens` cheap; the paid `generateJson` IS abort-guarded.
- **T8** (quota-drift): documented follow-up; cost operands drift-proof via `information_schema` DEFAULTs, only the quota seed (2/20) is literal-restored; a quota-seed change is a conscious migration edit, not silent drift.

## Follow-ups for 1G (recorded, non-blocking)
L1 registered-residual bound (per-owner serve budget / anon-account controls); L3 staging-blob GC; T8 quota mutators canonical restore; T4-a/T4-b/T6/T7-a nice-to-have test strengthening.
