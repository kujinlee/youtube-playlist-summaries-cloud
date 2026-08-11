<!-- codex-review: model=gpt-5.5 -->

**1. What Already Serves This Concern?**

The concern is already served by `serve_model_charge`.

Evidence:

| Existing mechanism | Evidence |
|---|---|
| One row per `(owner_id, doc_key, day)` | `supabase/migrations/0012_serve_model_charge.sql:7-13` |
| Lease TTL exists and is configurable | `supabase/migrations/0012_serve_model_charge.sql:22` |
| Reserve/reclaim is atomic and only reclaims after expiry | `supabase/migrations/0020_reservation_release.sql:217-223` |
| Live lease returns `in_flight`, so a second producer does not start | `supabase/migrations/0020_reservation_release.sql:226-235` |
| Charge occurs only on successful `reserved` claim | `supabase/migrations/0020_reservation_release.sql:237-254` |
| Direct table writes are service-role only; callers go through RPC | `supabase/migrations/0012_serve_model_charge.sql:15-17`, `supabase/migrations/0020_reservation_release.sql:263-264` |
| ADR names this exact exception: `model` is arbitrated by `serve_model_charge`, not `jobs` | `docs/adr/0007-artifacts-are-an-append-only-log.md:121-133` |

So v3 is not adding a mechanism for an unserved coordination concern. It adds a second mechanism for a concern already served, partly, by the existing lease: preventing a second paid producer. The unserved concern is narrower: two unbounded awaits and a retry loop whose local worst case exceeds the lease. That can be served by local time bounds without changing the DB coordination protocol.

**2. Which Coordination Pattern Is This?**

Existing mechanism: **mutual exclusion**. `serve_model_charge` is a lease lock keyed by `(owner_id, doc_key, day)`; conflict updates only succeed after `lease_expires_at < now()` and below `max_serve_attempts` (`0020_reservation_release.sql:217-223`). It is not append-only-plus-merge, and not an idempotency key, because it intentionally permits later reclaims and charges.

Proposed v3 mechanism: also **mutual exclusion / lease fencing**, but split across DB and app. The DB accepts a declared requirement, checks `lease_ttl_seconds`, returns `budget_seconds`, and the app runs a deadline derived from that budget (`docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:148-160`, `206-219`, `248-255`).

Yes: the design holds more than one mutual-exclusion pattern for the same paid-producer concern. The process checklist says that is the smell: every concern must have exactly one mechanism (`docs/process-checklists.md:181-184`).

**3. Who Are The Writers, And What Identity Does Each Carry?**

Writer classes that can reach `serve_model_charge` for a given `(owner, doc_key, day)`:

| Writer class | Identity | Evidence |
|---|---|---|
| Authenticated HTML serve request | `auth.uid()` owner, via session Supabase client | `app/api/html/[id]/route.ts:71-84`, `lib/html-doc/serve-summary-core.ts:105-116`, `lib/html-doc/serve-doc.ts:74-80`, `0020_reservation_release.sql:191-207` |
| Authenticated PDF serve request | same `auth.uid()` owner, same `resolveAndParse` path | `app/api/pdf/[id]/route.ts:39-49`, `lib/html-doc/serve-summary-core.ts:105-116` |
| Settle caller after reserve | same `auth.uid()` owner plus `release_token` minted by reserve | `0020_reservation_release.sql:249-253`, `268-281` |
| Service-role/admin/test maintenance | service_role direct table access | `0012_serve_model_charge.sql:15-17` |

Non-writers to this table:

| Non-writer | Evidence |
|---|---|
| Local HTML generation writes the model blob but never calls `reserve_serve_model` | `lib/html-doc/generate.ts:40-50` |
| Cloud sync may ship a model envelope but does not produce/pay; it copies existing bytes | `lib/cloud-sync/sync-run.ts:437-465`; ADR: `docs/adr/0007-artifacts-are-an-append-only-log.md:52-59` |

There are not two production writer classes needing different credentials. There is one paid producer class: an authenticated owner serve request. HTML and PDF are entrypoints, not different writer identities. The contention is real only as concurrent instances of the same writer class, carrying the same owner identity.

**Concern → Mechanism Table**

| Concern | Mechanism | Evidence |
|---|---|---|
| Bound paid model single-flight / prevent second paid producer | Existing `serve_model_charge` lease keyed by `(owner_id, doc_key, day)` | `0012_serve_model_charge.sql:7-13`; `0020_reservation_release.sql:217-235` |
| Bound paid model single-flight / prevent second paid producer | Proposed DB-issued `budget_seconds` plus app `Deadline` | spec `3.1`: lines `148-160`; spec `3.2`: lines `206-219` |
| Refuse leases shorter than the app’s declared one-attempt budget | `p_required_seconds` checked against `lease_ttl_seconds` | spec `3.1`: lines `152-155` |
| Prevent under-declared requirements by callers | `guardrail_config.min_required_seconds` plus `required_understated` | spec `3.1`: lines `155-167`, `175-193` |
| Bound `countTokens` | SDK `countTokens(..., requestOptions)` with `AbortSignal` | `node_modules/@google/generative-ai/dist/generative-ai.d.ts:778`, `1297-1306`; spec lines `252`, `283-291` |
| Bound `generateContent` attempts | Per-attempt timeout from remaining deadline and opportunistic retry gate | `lib/gemini.ts:256-267`; spec lines `253-281` |
| Bound model upload wait | Caller-side race around `writeModelEnvelope` / `blobStore.put` | `lib/html-doc/model-store.ts:45-51`; spec lines `293-320` |
| Preserve post-Gemini budget for upload/settle | `RESERVED_TAIL_MS` | spec lines `257-260`, `309-316` |
| Refund only when no Gemini call was issued | Required `BillingLatch.attempted` | current latch lacks it at `lib/job-queue/billing-latch.ts:7-8`; proposed at spec lines `372-418` |
| Avoid unit drift between seconds and ms | Unit-suffixed constants plus conversion tests | spec lines `120-146`, `449-453` |
| Avoid DB/app minimum drift | Migration literal `min_required_seconds = 85` plus anti-drift test | spec lines `179-193`, `495-498` |

The first two rows are the shape finding: one concern, two mechanisms. v3 also introduces a second DB/app anti-drift protocol to defend that second mechanism.

**Decision: REDESIGN**

v3 is the wrong shape for this slice. It takes a local bounded-await problem and turns it into a cross-authority lease protocol: new RPC argument, new return field, new DB floor, new statuses, new migration literal, new conversion rules, deploy-order constraints, and a new billing latch. The spec itself records that v3’s surface was introduced by prior fixes: viability check, refund condition, required latch field, migration literal, and conversions (`docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:603-607`). That is exactly the escalation trigger in `docs/review-method.md:45-47`.

The shape I would build instead is candidate **(b)**, with one adjustment stated plainly:

1. Bound `countTokens` locally using the SDK’s `signal` support.
2. Bound `blobStore.put` locally with a caller-side timeout/race.
3. Make the serve critical section’s worst-case budget a computed TypeScript constant: count-token timeout + one bounded `generateContent` attempt + backoff/retry policy as chosen + upload/settle tail.
4. Change retries so the total serve path cannot exceed that constant.
5. Add tests asserting the computed worst case is below the shipped/default `lease_ttl_seconds` of 180 seconds.
6. Add a focused test that a live request aborts before the lease can expire under the default configuration.

What this gives up relative to v3: it does not make Postgres reject an operator who later lowers `lease_ttl_seconds` below the app’s computed bound. Under that input, the existing reclaim clause can again admit a second paid producer after expiry. That is a real hole, but it requires service-role/admin configuration drift, not a second production writer class or a hostile anonymous caller. For task #46’s stated production purpose, fixing two unbounded awaits on a live GET path, that loss is acceptable and much smaller than installing a second coordination protocol.

VERDICT: REDESIGN
