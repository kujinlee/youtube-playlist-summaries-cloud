# Task 5 Review — enqueue-dig core (Approved, converged)

Dual review of `2604b49` (base `bc01e7c`); money-invariant test hardenings `94b98df`.
Diff: `lib/dig/cloud/enqueue-dig-core.ts` (`enqueueDig`), `lib/job-queue/enqueuer.ts` (payload type widened `IngestionPayload | DigJobPayload`), + tests.

Money/auth-critical → full dual review (Claude task-reviewer + Codex adversarial).

## Both reviewers — ✅ Approved, 0 Critical/Blocking, 0 High/Important

### Claude task-reviewer (verified against source, not assumed)
- **No charge path reachable pre-enqueue:** `enqueue-dig-core.ts` imports only `loadSummaryForServe`; `resolveMagazineModel` lives solely in the separate `resolveAndParse` (not imported). Charge happens once inside `enqueue_job` on fresh enqueue only.
- **Two-client split clean:** session client → `loadSummaryForServe` only; service-role `Enqueuer` → `preflight`/`enqueue` only. No service-role tenant read.
- **§9.2 re-check structurally sound:** the same `key` (computed once, `digSectionKey(load.base, sectionId)`) feeds both the pre-enqueue dedup and the post-enqueue re-check — no key drift.
- **Dedup-key ↔ worker-write consistency PROVEN:** trigger `base = mdKey.replace(/\.md$/,'')` (`serve-summary-core.ts:76`) equals worker `base` via `resolveSummaryMdKey` (`resolve-summary-key.ts`, same `artifacts.summaryMd.key ?? summaryMd` fallback). The worker writes exactly the key the trigger deduped against.
- **Guardrail/preflight mapping** matches `app/api/jobs/route.ts:53-61` exactly. **Type-widening pure-additive:** RPC body byte-identical; a strict-superset param type can't change ingest runtime behavior. **Anon-first ordering** is the literal first statement.

### Codex adversarial — 0 Blocking, 0 High, 1 Medium, 2 Low

## Findings & dispositions

### Money-invariant test hardenings — FIXED (`94b98df`, test-only)
- (Claude Minor) `'202 …(charges once)'` now asserts `enqueue` called exactly once — the title's guarantee is now backed.
- (Codex Low) §9.2 409 test asserts both `exists` calls target the same `{id:'u1',indexKey:'PLk'}` + `digSectionKey('0007_intro',132)` — a wrong-key re-check can no longer pass on count alone.
- (Codex Low) anon test asserts `preflight` AND `enqueue` untouched — the 403 must precede ALL service-role work, not just the tenant read.
No re-review round: test-only, strengthening invariants both reviewers verified structurally.

### Claude ⚠️ (out-of-diff) — RESOLVED by the controller
*"Can `enqueue_job` return `joined:true, status:'failed'`?"* If so, the `else→202` branch would report a dead job as "enqueued." Verified: `jobs_idem_active`'s partial predicate is `where status in ('queued','active','completed')` (0009:13), and `enqueue_job`'s ON CONFLICT (0018:35) + JOIN SELECT (0018:75) use the identical predicate. A `failed` row is NOT in the index → a fresh enqueue INSERTs a new row rather than joining it. So `joined:true` ⟹ status ∈ {queued,active,completed}; the §9.2 special-case (`completed`) + `else` (queued/active→202) is exhaustive and safe. No code change needed.

### Deferred — carried into Task 6 (route) as explicit requirements
- (Claude Minor) **`Retry-After` on 429** — the core returns `{status:429, body}`; the ingest route adds `Retry-After: 60` (`jobs/route.ts:54-58`). The T6 route that consumes `enqueueDig` must add the same header on 429.
- (Claude Minor) **`challengeRequired` passthrough** — the ingest route surfaces `verdict.challengeRequired` in its 200 body; the dig core omits it (deliberate — the core returns status+body only). T6 must decide whether the dig response carries the challenge signal for a future captcha UX.

### Deferred — rolled up for whole-branch triage
- (Codex Medium) **Payload type coupling.** Widening `enqueue`'s payload to `IngestionPayload | DigJobPayload` lets a future caller compile `kind:'summary'` with a `{durationSeconds}` dig payload → a fresh summary job charged once, then failing non-retryably in the worker. NOT attacker-controlled (both current callers are correct); runtime backstops exist (`enqueue_job`'s kind-based CASE + the summary worker's `parseIngestionPayload`→`NonRetryableError`). Claude independently judged the widening safe for existing callers. A discriminated/overloaded signature would restore compile-time coupling but adds surface to the shared interface (used by ingest → own re-review). Proportionate to defer: a latent internal-only risk with runtime defenses; best tightened deliberately (e.g. when a third `job_kind` lands).

## Disposition
Converged. Both reviewers Approved; the one ⚠️ resolved against the migrations; money-invariant tests hardened. Tests: enqueue-dig-core 10/10, enqueuer 7/7, full suite 2110, tsc clean. 2 route-requirements carried to T6; 1 Medium deferred to whole-branch triage.
