<!-- codex-review: model=gpt-5.5 -->

**Factual Checks**

Section 1’s factual claims hold against `6c70f10`:

- 181,200ms is correctly derived: `3 * 60,000ms + 400ms + 800ms`. The magazine path does use `generateJson(..., undefined, undefined, opts)`, so it gets `GENERATE_JSON_RETRIES = 2`.
- `settle_serve_model` clears `reserved_cents`/`release_token` and adjusts ledgers, but never touches `attempt_count`.
- Current `reserve_serve_model` returns `table(status text, release_token uuid)`, no expiry/budget.
- The two cited bare awaits are real and reachable from authenticated user-facing HTML/PDF GETs: `countTokens` via `resolveMagazineModel → generateMagazineModel`, and `BlobStore.put` via `writeModelEnvelope`.

**Blocking — §3.1/§3.2: returned `budget_seconds` is already stale before the app starts its monotonic timer**

Concrete break: DB grants a 180s lease and returns `budget_seconds = 180` or `179`; the response spends network time, Supabase/PostgREST time, JS scheduling time, and only then the app starts `performance.now() + budget_seconds`. If that gap exceeds the floor’s sub-second rounding margin, the app deadline expires after `lease_expires_at`. A second producer can reclaim before the first producer’s app deadline fires, recreating the double-producer condition the spec is meant to remove.

Checked: `0020` computes leases from `now() + lease_ttl_seconds`; the proposed spec computes budget from DB `now()` and starts the app timer only after RPC return. The spec’s floor only handles fractional seconds, not transport or scheduling latency.

**Blocking — §3.1: `p_required_seconds` is caller-controlled, so the DB gate can be bypassed**

Concrete break: any `authenticated` or `anon` caller of the granted RPC can pass `p_required_seconds = 1`. The DB then grants and charges a lease even if the real app path needs far more time. That makes the gate report success without proving the required work fits the lease. A buggy app constant or hostile direct client defeats the central invariant.

Checked: `reserve_serve_model` is currently granted to `authenticated, anon` in `0020:264`; the design keeps the RPC public and makes the app declare the requirement. The DB has no independent lower bound or derivation to validate the declared number.

**High — §4: “billing.metered latch needs no change” is false for deadline expiry before generation returns**

Concrete break: deadline fires during `countTokens`. No Gemini generation body has returned, so `billing.metered` is false. But the existing classifier returns `keep` for an aborted `ourSignal`, and returns `keep` for an ordinary abort error if the original request signal is passed instead. Result: `settle_serve_model(..., p_released=false)` keeps the 6¢ charge for a deadline abort before metering.

Checked: `serve-doc.ts:130-132` releases only when `classifyGeminiFailure(err, signal) === 'release' && !billing.metered`; `gemini-failure.ts` treats `ourSignal.aborted` as `keep` and otherwise only releases `NonRetryableError`/429/503. The spec adds a new abort source but does not add a new classification path.

**Medium — §2.1/§3.3: opportunistic retries can reduce successful serves unnecessarily**

Concrete break: attempt 1 times out at 60s, backoff 400ms; attempt 2 times out at 60s, backoff 800ms. About 58.8s remains under a 180s lease. The spec says “next retry started only if `remaining ≥ one attempt`”, so attempt 3 is skipped, even though §3.3 also says each attempt should use `min(REQUEST_TIMEOUT_MS, remaining)`. A third attempt with a 58s timeout could have succeeded inside the lease.

Checked: `generateJson` currently does three attempts with 400/800ms backoff. The proposed retry-start rule conflicts with the proposed per-attempt timeout rule and silently trades away availability.

**Medium — §3.4: abandoned `BlobStore.put` is not benign on all adapters**

Concrete break: after Gemini returns, `billing.metered = true`; then `writeModelEnvelope` races `put` against the deadline. If the race times out and the Supabase upload later fails, the charge is kept, the token is settled, and no model blob exists. The next view can reserve and charge again. The late write self-heals only if it actually lands.

Checked: `SupabaseBlobStore.put` is `upload(..., upsert:true)` with no cancellation or post-timeout verification. Local/in-memory usually complete deterministically, but the spec claims all three adapters are safe while only the success-after-timeout case is self-healing.

**Medium — §5: the `lease_too_short` integration test can pass while the app still bypasses the real guard**

Concrete break: a test that calls `reserve_serve_model(..., p_required_seconds = huge)` and asserts no money/no attempt proves only that the explicit-too-large branch works. It does not prove production callers pass the derived required constant, nor that callers cannot pass `1` and get a lease too short for the real path.

Checked: §5 proposes a live Supabase `lease_too_short` assertion and mutation removing `lease_ttl_seconds < p_required_seconds`. That catches guard deletion, not under-declaration by the app or public callers.

**Verdict**

NOT CONVERGED
