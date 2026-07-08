# Claude plan review — round 2 (v2) · Opus `acbd72564524b210e`

**Verdict: no new Blocking (B1 genuinely closed & cross-checked). 3 High + 1 Medium + 3 Low (all fixed/recorded in plan v3).**

## Round-1 fixes verified genuine
B1 drop-correct-signature (exact 0009 `enqueue_job(uuid,text,int,text,text,jsonb)` match; create-order safe; both 6-arg & 8-arg client calls tested denied); helper signatures; `anonSession→is_anonymous=true` (via `0003 handle_new_user` `coalesce(is_anonymous,false)`); beforeEach/getGuardrailConfig/SupabaseJobQueue.enqueue-removal/jobs_velocity/failed-formula/schema-policies/§8-cases/`p_*`/`mapEnqueueError`; T12 independent recompute (~115¢, `150 ≥ 115`); disjoint-sum holds; `liveBroadcastContent` source = `videos.list` (correct).

## High (fixed in v3)
- **H1 — required `liveBroadcastContent` breaks 4 typed `: VideoMeta` fixtures** (`producer-roundtrip:11`, `pipeline:41`, `video-meta-to-payload:4`, `producer:13`); `.default()` still forces it in `z.infer`. *Fix: `.optional()` + producer blocks only explicit `'live'|'upcoming'`.*
- **H2 — T10 orphans the existing `tests/lib/producer.test.ts`** (old 3-arg `enqueuePlaylist`, `jobQueue` fake, old 4-bucket sum, "no/broken jobQueue" tests); T13's grep is `tests/integration/`-scoped → `tsc`/`npm test` break. *Fix: T10 migrates it.*
- **H3 — T3 `admitted` inverts the spec ceiling.** Plan applied `max_free_users` to anon + admitted all registered; spec §5/parent = ceiling on **registered**. *Fix: `admitted = is_anonymous OR registered_rank ≤ max_free_users` + a test.*

## Medium (fixed in v3)
- **M1 — `MAX_SUMMARY_ATTEMPTS` second drift source** (= Codex). *Fix: import from `gemini-cost.ts`, delete local.*

## Low (recorded)
- **L1** — `beforeEach` never clears `jobs` (velocity/queue-depth reads accumulated rows); order-fragile. *Fix (v3): clear jobs in beforeEach.*
- **L2** — T11 fake `Enqueuer` must implement `getGuardrailConfig()`. *Noted in v3.*
- **L3** — `ON CONFLICT` predicate alias must match `jobs_idem_active`. *Noted in v3.*

**PLAN VERDICT: fix Blocking/High first** → done in v3.
