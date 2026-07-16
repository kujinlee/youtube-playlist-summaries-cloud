# Round-6 Adversarial Re-Review — Reservation Release Lifecycle Spec v6 (Claude, independent)

**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v6)
**Mandate:** money path; hunt any surviving metered-then-class-A-rejected RELEASE (under-count); scrutinize the v6 job-scoped `billing.metered` latch against real code and its threading.
**Grounded in:** `lib/gemini.ts`, `lib/dig/generate.ts`, `lib/transcript-source.ts`, `lib/ingestion/summary-core.ts`, `lib/job-queue/{worker-runner,summary-handler,dig-handler}.ts`, `lib/job-queue/handler-context.ts`, `lib/html-doc/serve-doc.ts`, `lib/gemini-cost.ts`, vendored SDK (`node_modules/@google/generative-ai/dist/index.js`).
**Verdict: NOT CONVERGED** (one Blocking — the right idea wired to the wrong granularity).

---

## Blocking

### B6-1 — The latch threading stops at `generateSummary`/`transcribeViaGemini`/`generateMagazineModel` and never reaches `generateJson`, so an inner-retry metered body then a final 429/503 still RELEASEs (reopens C4-B1, LIVE on the summary path)
**Where:** §3.1 line 74 (threading chain + set-points), §5 line 200, behavior 3e, §11 line 416. Code: `gemini.ts:255-269` (`generateJson` loop — body at `:258`, throws `lastErr` at `:269`), `:341-368` (`generateSummary` `attempt()` + outer loop), `:665-690` (`transcribeViaGemini`), `:543-555` (`generateMagazineModel` → `generateJson` at `:545`). `GENERATE_JSON_RETRIES=2` (`gemini-cost.ts:22`).

**The defect.** §3.1 states the principle correctly ("set `billing.metered=true` the instant any billable Gemini call returns a response body"), but the concrete **threading chain** and **set-points** it hands the implementer don't realize it for the inner retries:
- Threading (line 74) lists `generateSummary/transcribeViaGemini/generateDig/generateMagazineModel` — **not `generateJson`**, the innermost primitive that actually calls `model.generateContent` and receives the metered body (`:258`) for summary/quick-view/magazine. If `billing` never reaches `generateJson`, no code there can flip the latch.
- Set-points (line 74) — "per returned `attempt()`", "after `transcribeViaGemini` returns segments", etc. — are all **successful outer-function returns**. None fire when the outer function **throws**.

**Concrete failure (summary path, 150¢, global, not gated):**
1. `generateSummary` outer loop `i=0` → `attempt()` → `generateJson` inner attempt 0: `model.generateContent` **returns a body** (`:258`) → **metered** → `schema.parse` throws on invalid JSON (`:260`) → caught, retry.
2. inner attempt 1: `model.generateContent` throws `GoogleGenerativeAIFetchError.status=503` (SDK `index.js:402→434`, no body).
3. inner attempt 2: 503 again → `throw lastErr` (503) at `:269`.
4. `attempt()` **throws** → `generateSummary` catch (`:389-395`) wraps `{ cause: <503> }` and throws. The outer-loop set-point never ran (attempt threw).
5. Runner: `classifyGeminiFailure` → `.status=503` → `'release'`; `billing.metered` **never set** → `release=true` → `fail_job(billable=false)` → **RELEASE of a generation that metered on inner attempt 0** → under-count. Exactly C4-B1/B5-1, reopened because v6 moved the set-point from inside the retry loop to the outer-function return, which the throw path skips.

The spec is internally contradictory: §11 mandates covering "the three inner retry loops (C4-B1)" and behavior 3e asserts this KEEPs ("body set billing.metered=true"), but no section specifies where that set happens and the threading chain structurally prevents it.

**Same root cause, two more paths:** `transcribeViaGemini`'s loop (`:665-687`) — meter on attempt 0 (`:669`) then 503 on attempt 1 → `throw lastErr` (`:689`), latch never set (gated-safe today, but §3.1/M5-1 claim coverage "when the flag flips" — false). `generateMagazineModel` → `generateJson` (`:545`) — inner-attempt-0 metered then 503 → serve refunds a metered 6¢ (bounded ≤60¢/owner, but same class).

**Direction.** Set the latch at the **primitive**, not outer returns:
- Add `billing` to `generateJson`'s opts; set `opts.billing.metered=true` **immediately after `model.generateContent` resolves** (`:258`, before parse/assert). Covers summary/quick-view/magazine inner retries in one place.
- Same right after `model.generateContent` resolves in `transcribeViaGemini`'s loop (`:669`).
- `generateDig`'s return-point set is adequate only because its retry never meters-then-retries (retries on network/non-ok only, never after a 200) — keep it but state the rationale. (A mid-`res.json()` disconnect at `:274` → generic error → class-B KEEP.)
- Add `generateJson` + the transcribe loop to §3.1's threading chain and set-point list; drop the "per returned `attempt()`" wording (wrong granularity).

---

## Medium

### M6-1 — Latch carrier and per-call-site threading unspecified; several intermediaries would silently drop it
**Where:** §3.1 line 74, §5 line 202-206, §6 line 322-324. Code: `handler-context.ts:4-10` (`HandlerCtx` — the only runner→handler channel), `summary-handler.ts:110-118`, `summary-core.ts:66-85` (`rtsOpts`/`gsOpts` built field-by-field), `transcript-source.ts:24-42`.

The spec never names the carrier. The runner→handler interface is `HandlerCtx` (`worker-runner.ts:34-40`), so `billing` must be a `HandlerCtx` field, and every gemini-invoking opts object must copy it: `summaryCore`'s `rtsOpts`/`gsOpts` (built field-by-field — would drop an un-named field), `resolveTranscriptSegments` opts → `transcribeViaGemini`, the `generateSummary` closure wrapper (`summary-handler.ts:112-115`, forwards `...args`). For **serve** there is no runner — §6 must say who creates `billing` in `resolveMagazineModel` (`serve-doc.ts:44`, currently only `signal`). Without an explicit carrier + call-site audit, any missed intermediary silently mis-releases. **Direction:** pin `billing` as a `HandlerCtx` field (and a `resolveMagazineModel` arg for serve); enumerate every opts object that must carry it; runner reads `ctx.billing.metered`.

---

## Low

### L6-1 — `extractQuickView` bills but isn't in the threading list; benign today only by an unstated ordering invariant
`gemini.ts:409-443` (no opts/signal), `summary-core.ts:122-133` (called after `generateSummary`; error **swallowed**). Harmless now: `generateSummary` runs first and (once B6-1 fixed) sets the latch; quick-view's failure is caught so it never becomes the classified error. Safety rests on an unstated invariant. **Direction:** note the invariant in §3.1 (or thread `billing` in for defense-in-depth) so a future reorder doesn't open an under-count. Not blocking.

---

## Consistency check — clean
- Behavior 17 lists only caps-`NonRetryableError`/`{429,503}` with `billing.metered=false`; **no `connection`** (L5-1 confirmed).
- No stale `maybeMetered`/`no prior metered attempt`/`connection→release` in the live spec (only §3.1/§5 describing what the latch *replaces*, + historical changelogs).
- `{429,503}`-only, 500/502/504→KEEP, SDK-stripped-connection→KEEP consistent across §1/§2.4/§3.1/§5/§6/§7/§8. SDK grounding re-confirmed (`index.js:402-434`, `:407-418`).
- Retry/reaper/cancel interaction correct; pre-send-only failures leave latch false → class-A RELEASE, correct. SQL bodies unchanged from round-4/5, re-confirmed closed.

The spec is one genuine defect from convergence: the round-5 latch is the right idea, wired to the wrong granularity (outer-function returns instead of the `generateContent` primitive), which structurally reopens the inner-retry under-count it claims to subsume.

**NOT CONVERGED**
