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

## Verification record — 2026-07-19 ✅ GATE OPENED

`RELEASE_VERIFIED = true` as of 2026-07-19. Harness: `npm run verify:gemini-release`
(`scripts/verify-gemini-release.ts`), live key, `gemini-2.5-flash`, Tier 1 (1,000 RPM — confirmed
empirically: exactly 1,003 of a 1,200 burst succeeded). Three runs:

| Run | Attempts | Successes | Rejections | Input tokens |
|---|---|---|---|---|
| 1 (control, 16:00) | 61 | 61 | 0 | 128 |
| 2 (16:05) | 1,201 | 1,004 | 197 | 2,013 |
| 3 (16:59) | 4,001 | 1,005 | **2,996** | 2,714 |

**Fact (1) — MEASURED, decisive.** All 3,193 rejections across runs 2–3 arrived as
`GoogleGenerativeAIFetchError` with `.status === 429`, and `classifyGeminiFailure()` — the real
classifier, not a mock — routed **every one** to `'release'`. Zero misclassifications. One unrelated
`GoogleGenerativeAIError` with no `.status` appeared in run 2 and was correctly classified `'keep'`,
which is the conservative direction.

**Fact (2) — BOUNDED, not proven zero.** Runs 2 and 3 are a controlled pair: successes held constant
(1,004 → 1,005) while rejections rose 15× (197 → 2,996). Input tokens moved only 2,013 → 2,714.
- "Rejections billed like successes" predicts `8 + 4000×2 = 8,008` → **excluded by 3×**.
- Residual: 701 extra tokens over 2,799 extra rejections = **≤ 0.25 input tokens per rejection**
  (~$0.000000075), versus the **150¢** reservation at stake. Seven orders of magnitude.
- Exact zero is **not measurable with this instrument**: the same console reported 63K vs 118K
  output tokens for identical success counts (thinking-token variance), so a 35% wobble on input is
  inside its noise. `"ping"` was calibrated at exactly 2 input tokens from run 2
  (`8 + 1003×2 = 2,014` vs 2,013 observed).

**503 — INFERRED, never observed.** A burst can only provoke 429 (rate limiting); 503 (capacity
overload) cannot be summoned on demand. `RELEASE_STATUSES` still covers both, on the reasoning that
both are admission-control rejections before generation. Deliberate, and deliberately recorded as
the weaker half. Narrowing to `{429}` was considered and rejected: 503 is Gemini's *classic outage*
response, so excluding it would leave unfixed the exact scenario this gate exists to fix.

**Decision framing (user, 2026-07-19).** The premise was accepted as "bills nothing *material*
relative to the reservation" rather than "bills exactly zero" — precision beyond that is false
precision against vendor pricing that changes anyway. The durable answer to price drift is periodic
recalibration, filed in `docs/roadmap-to-launch.md` → Parking Lot.

**Still closed:** `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` (`lib/gemini.ts`) — a *different* premise
(worst-case cost of audio-fallback transcription) that this session did **not** verify.

---

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
