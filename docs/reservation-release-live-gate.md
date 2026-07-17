# Reservation-Release: Live-Verification Gate for `CLOUD_GEMINI_RELEASE_VERIFIED`

Belongs with the spend_ledger reserve→release money-path slice (`docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md`, Task 12). Not part of `docs/local-validation-findings.md` (that file tracks unrelated local-environment findings) — kept as its own doc so it stays scoped to this slice's commit.

## The flag

`lib/gemini-failure.ts` gates class-A RELEASE (a not-metered Gemini rejection releasing its
spend_ledger reservation) behind a **compile-time money gate**, not a runtime env read:

```ts
const RELEASE_VERIFIED = false;          // flip to true in CODE only after live verification below

export function releaseGateOpen(): boolean {
  if (process.env.NODE_ENV === 'test') return process.env.CLOUD_GEMINI_RELEASE_VERIFIED === 'true';
  return RELEASE_VERIFIED;
}
```

- **Default: OFF.** In production, `releaseGateOpen()` always returns the hardcoded `RELEASE_VERIFIED`
  const (`false`), independent of any environment variable. This mirrors the existing
  `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` pattern (`lib/gemini.ts`).
- In `NODE_ENV=test`, the gate reads `process.env.CLOUD_GEMINI_RELEASE_VERIFIED` so integration/unit
  tests can open it deliberately (e.g. `reservation-release.test.ts` behavior 26) without touching
  the production code path.
- The gate can only be flipped ON in production by editing `RELEASE_VERIFIED` to `true` in source —
  an env var alone can never enable release of real money in prod.

## The two facts that must be verified against LIVE Gemini before flipping the gate

`classifyGeminiFailure()` (`lib/gemini-failure.ts`) treats a Gemini failure as `'release'` (safe to
give the reservation back) in two cases: (a) a pre-send `NonRetryableError` anywhere in the error's
cause chain (a $0 failure that never reached Gemini — e.g. fail-closed transcribe/preflight), or
(b) a `GoogleGenerativeAIFetchError` (or the hand-rolled `GeminiHttpError`) whose `.status` is in
`{429, 503}`. Case (a) needs no live verification (it is a local pre-send guard); it is case (b) — the
live-outage path — whose two premises must be confirmed against the **live** Gemini API (not mocks)
before setting `RELEASE_VERIFIED = true` in prod:

1. **An overloaded/rate-limited call surfaces as `GoogleGenerativeAIFetchError` with `.status ∈ {429, 503}`.**
   Confirm the SDK actually throws this typed error (not a generic `Error`, a timeout, or a different
   status) when Gemini is genuinely overloaded or rate-limiting the caller — i.e. that the classifier's
   `instanceof` + `.status` check will actually match a real outage in the wild.
2. **Those statuses carry no token billing.** Confirm Gemini does not charge for a request that is
   rejected pre-generation with 429/503 — i.e. that the premise "this failure mode is genuinely $0"
   holds against the live billing/usage API, not just against the SDK's error shape.

Both facts are currently **unverified** (no live Gemini traffic has exercised this path). Only local
Postgres + mocked Gemini responses back the current `release` classification.

## Until verified: fail-closed to KEEP

With the gate closed (`RELEASE_VERIFIED = false` in prod), `worker-runner.ts` never releases on a
Gemini throw — `classifyGeminiFailure` may still classify an error as `'release'`, but the runner ANDs
that with `releaseGateOpen()`, which is `false` in prod, so the reservation is always KEPT:

```ts
const release = releaseGateOpen() && classifyGeminiFailure(e, signal) === 'release' && !billing.metered;
```

This is the money-safe default: every Gemini throw — including genuine $0 outages — is treated as a
billable KEEP until the two facts above are verified live. This intentionally leaves the §2.4 outage
residual documented (a real Gemini outage over-reserves rather than releasing) rather than risk an
unverified early release that could zero out a reservation for a call that actually billed.

## To flip the gate on

1. Run live Gemini traffic that reproduces a genuine 429/503 (e.g. a burst well past your quota, or a
   known-overloaded model/region) and capture the thrown error's shape and `.status`.
2. Cross-check the Gemini usage/billing dashboard (or API) for that same window to confirm no tokens
   were billed for the rejected call.
3. If both facts hold, change `RELEASE_VERIFIED` from `false` to `true` in `lib/gemini-failure.ts`,
   note the verification date/evidence in the commit message, and re-run the reservation-release
   integration suite (`npm run test:integration -- reservation-release`) to confirm no regression.
4. If either fact does NOT hold, leave the gate closed and file a follow-up — the classifier and/or
   `RELEASE_STATUSES` set needs revising before release can ever be safe.
