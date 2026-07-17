# Round-4 Adversarial Re-Review — Reservation Release Lifecycle Spec v4 (Claude, independent)

**Reviewer:** Claude (independent; did not read Codex or any other reviewer output)
**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v4)
**Method:** grounded against the real migrations (`0008–0019`) and lib/TS (`gemini.ts`, `transcript-source.ts`, `worker-runner.ts`, `summary-handler.ts`, `serve-doc.ts`, `supabase-job-queue.ts`, `youtube.ts`, `cancel-job-rpc.test.ts`) plus the vendored SDK `node_modules/@google/generative-ai/dist/index.js` (v0.24.1).
**Gate:** no new Blocking/High grounded in a concrete failure scenario → CONVERGED.

---

## Summary of Mandate A (round-3 fixes genuinely closed?)

| Finding | Verdict | Note |
|---|---|---|
| **B-2** §3.1 classification exists, RELEASE only positive-not-metered | Closed **in principle**, but **two reachability gaps** (see H-1, H-2 below) mean the class-A signal does not actually reach the runner for two concrete vectors | The HTTP-`.status` release path (503/429/500/502) **is** reachable through `generateJson`→`generateSummary`→`summaryCore`→handler→runner (`gemini.ts:394` cause-wrap survives, handler `throw e` unwrapped at `summary-handler.ts:141`). |
| **B-1** serve leg applies same classifier | Closed at spec level (§6). No mis-RELEASE found (class B/C on serve → `keep`, verified against `gemini.ts:551–554`). |
| **H-1** transcript wrapper preserves `{cause}` | **NOT genuinely closed** — see **High H-1** (wrong cause chosen). |
| **H-2** playlist CTE flags active jobs | Closed. The data-modifying CTE is valid Postgres; `aud` (INSERT wCTE, unreferenced) still executes exactly once; `count(*) from upd` returns jobs-flagged (queued+active). `jobs.playlist_id` exists (`0009:4`). |
| **H-3** set-based / procedural audit | Closed. `request_cancel_job` procedural `if not found then insert ledger_audit`; playlist `aud` audits every `per_day not in (select day from dec)`. |
| **H-4** cancel returns 1 for active + jobs-flagged count | Closed. Procedural `request_cancel_job` returns 1 on any matched cancel, 0 on not-found — matches all four assertions in `cancel-job-rpc.test.ts:27,39,52,61,65`. |
| **M-1** idempotency-skip removed from RELEASE set | Closed. `summary-handler.ts:91` `return`s → `complete_job` (KEEP); never reaches the classifier. |
| **M-2** `returns table` → `data[0]` | Closed. Matches the `claim_next_job` precedent (`supabase-job-queue.ts:60–61`). |
| **M-3** `fail_job` release SQL excludes `queued` requeue | Closed. `v_new in ('failed','dead_letter','cancelled')` correctly excludes `'queued'`; reads `created_at`/`reserved_cents`; stays inside the `status='active'` fence; day = `(v_created_at at time zone 'utc')::date`. |
| **L-1 / L-2** | Closed (at-capacity = no-op; behavior 3b uses the realistic "transcription billed then threw" shape). |

**Money-safety direction check (the Blocking direction):** I found **no** class-B/C error that the classifier mis-RELEASES (under-count). Timeouts and SDK aborts surface as `GoogleGenerativeAIAbortError` (`.status`/`.code` absent) → `keep`; 504/400 have `.status ∉ {429,500,502,503}` → `keep`; post-return `section count mismatch`/parse → plain `Error`, no status → `keep`. The two High findings below are both the **mis-KEPT** ($0 leak / self-DoS) direction — money-safe, but they defeat §1's stated goal for concrete vectors and falsify testable claims the spec makes.

---

## Blocking

None. No new under-count (real-money-loss) path was found; the classifier is conservative by construction.

---

## High

### H-1 — H-1's "preserve `{cause}`" fix picks the WRONG cause; the class-A signal is masked whenever captions THROW
**Where:** spec §5 ("`resolveTranscriptSegments` … preserve the original via `{ cause: err }`") and §7 behavior 3d, vs. real code `lib/transcript-source.ts:60-63`, `lib/youtube.ts:90,104`, `lib/gemini.ts:656-661`.

**Concrete failure scenario (inputs → wrong outcome):**
1. Cloud summary job for a video with no usable YouTube captions. `fetchTranscriptSegments` **throws** (`youtube.ts:90` — `throw new Error('Failed to fetch transcript…', { cause: err })`; the no-caption / ratelimit / network path throws, it does not return empty). So in `resolveTranscriptSegments`, `captionErr` is set and `captionsEmpty` stays `false`.
2. The fallback `transcribeViaGemini` runs on the cloud path (`caps` present) and immediately throws `NonRetryableError` (`gemini.ts:658`, because `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false` — this fires for **every** caption-less cloud video today). So `geminiErr` = a class-A `NonRetryableError`.
3. The catch at `transcript-source.ts:51-63` is not `PermanentTranscriptError`/`AbortError`, so it throws `new Error('transcript unavailable…', { cause: captionErr ?? geminiErr })`. Because `captionErr` is truthy, **`cause = captionErr`** (a generic YouTube `Error`) — the typed `NonRetryableError` (`geminiErr`) is **dropped from the chain**.
4. `classifyGeminiFailure` walks `.cause`, finds the generic caption `Error` (no `.status`, no `.code`, not `NonRetryableError`) → `'keep'` → `p_billable_succeeded=true` → **150¢ KEPT** for a provably pre-send $0 failure.

This is exactly the leak H-1 claims to close, and behavior 3d asserts is released. It leaks on the **common** trigger (captions throwing), so ~3 caption-less cloud videos lock the global budget until midnight at $0 spend — the §1 self-DoS, re-opened. The fix "already has a `{cause}`" (the line predates the spec), so an implementer reading "preserve via `{cause}`" may believe it is done and never correct the precedence.

**Direction:** In the wrapper, prefer the **Gemini-side** typed error as the discriminator, never the caption error — e.g. re-throw the typed cause explicitly before the generic wrap: add, alongside the existing `PermanentTranscriptError`/`AbortError` re-throws at `transcript-source.ts:52,57`, `if (geminiErr instanceof NonRetryableError) throw geminiErr;` (import it), OR change the wrap to `{ cause: geminiErr }` (the throwing side that carries the class). Update §5/behavior-3d to specify this precedence, and make the 3d fixture drive the **captions-threw** branch, not only captions-empty.

### H-2 — Classifier's connection/DNS class-A marker (`code ∈ {ECONNREFUSED,…}`) is unreachable: the SDK discards the code
**Where:** spec §3.1 (class-A "connection-refused / DNS failure", classifier step 2 `code ∈ {ECONNREFUSED, ENOTFOUND, EAI_AGAIN}`) and §7 behavior 2b / §9 unit tests, vs. `node_modules/@google/generative-ai/dist/index.js:407-418` (`handleResponseError`).

**Concrete failure scenario (inputs → wrong outcome):**
1. Gemini endpoint unreachable during an outage (connection refused, or a Fly.io resolver `EAI_AGAIN`). `fetch` throws an undici `TypeError('fetch failed')` whose `.cause` carries `{ code: 'ECONNREFUSED' }`; `.name` is `'TypeError'`, **not** `'AbortError'`.
2. The SDK's `handleResponseError` (`index.js:413-417`) takes the `else` branch and rewraps it as **`new GoogleGenerativeAIError('…: fetch failed')`, copying only `.stack`** — the Node error's `.code` and `.cause` are **thrown away**. `GoogleGenerativeAIError` has no `.status` and no `.code` (`index.js:248-252`).
3. `gemini.ts:394` wraps that as `Error('Gemini summary failed…', { cause: <GoogleGenerativeAIError> })`. The classifier walks `.cause`, finds an object with no `.status`, no `.code`, not `NonRetryableError` → `'keep'` → **150¢ KEPT**.

So the connection/DNS subclass of "outage" — which §3.1/§2.4 explicitly enumerate as class-A-release ("outages are 429/503/500/connection storms — all class A → each RELEASES") — cannot actually release. Worse, the §9 unit test "`ECONNREFUSED`/`ENOTFOUND` → release" will be written against a **synthetic** `{ code }` shape that never occurs in production, giving false green. (The HTTP-status outage subclass — 503/500 from a live-but-overloaded endpoint — IS reachable via `GoogleGenerativeAIFetchError.status` at `index.js:434,272`, so the dominant outage mode is handled; this finding is the connection-error tail plus the misleading test.)

**Direction:** Either (a) drop the `code`-based connection markers from class A and document that connection/DNS outages remain KEPT (fold into the §2.4 accepted residual — honest, since the HTTP-status path already covers the common outage), or (b) if connection-release is required, classify on the SDK's actual wrapped shape (`err instanceof GoogleGenerativeAIError && /fetch failed/.test(err.message)` — fragile, note the coupling to SDK v0.24.1), and make the §9 unit fixture use the **real** SDK-wrapped error, not a raw `{ code }`. Align §2.4/§3.1's "connection storm closes the DoS" claim with whichever path is chosen.

---

## Medium

### M-1 — §9 live-verification gate enumerates only `{429,503}`, but §3.1 RELEASES `{429,500,502,503}`; 500/502 could be released un-verified (under-count risk)
**Where:** §9 ("verify … the SDK surfaces `.status` … **for 429/503** … those statuses genuinely carry no token billing") vs. §3.1 / classifier step 2 (`.status ∈ {429,500,502,503}`) and behavior 2b.

**Scenario:** An operator flips the verification flag after checking 429/503 only (the two §9 names). In production a Gemini **500** ("internal error") is then classified `'release'`. Unlike a 429/503 admission-control rejection, a 500 can be returned *after* the model began generating (metered) → `settle`/`fail_job(billable=false)` refunds a reservation for spend that occurred → **under-count** (the Blocking direction), for the one status where "rejected ⇒ $0" is least certain. This is gated behind the flag and behind §9's intent ("those statuses"), so it is not an open defect today, but the enumeration mismatch invites a narrow verification that leaves 500/502 un-checked.

**Direction:** Make §9 enumerate the **full** release set `{429,500,502,503}` explicitly, or move 500/502 to class B (KEEP) — 429/503 alone cover the admission-control outage case that §1 cares about, and 500/502 carry the highest post-metering ambiguity.

---

## Low

### L-1 — Spec should state *why* the classifier must key on `ourSignal.aborted` and not error identity
**Where:** §3.1 classifier step 1; informed by `gemini.ts:392,551` and SDK `index.js:288-289,409-411`.

The SDK wraps *both* an in-flight lease-abort and its own 60s `REQUEST_TIMEOUT_MS` timeout by aborting the **same** internal controller (`index.js:441-455`), yielding an indistinguishable `GoogleGenerativeAIAbortError` whose `.name` is `'Error'` (none of the SDK error classes set `.name`). So `gemini.ts:392`'s `err.name === 'AbortError'` guard does **not** catch an SDK-wrapped abort on the final attempt. The spec's choice to gate on `ourSignal.aborted` (not error identity) is therefore **correct and necessary** — but the spec presents it as one option among "walk `.cause`". Call this out so an implementer does not "simplify" step 1 to an `instanceof AbortError`/`err.name` check, which would silently misfire. (Money impact is nil either way here: both SDK-timeout and our-abort resolve to `keep`.)

### L-2 — "connection storm" language in §2.4/§3.1 overstates closure
Given H-2, the repeated phrasing "outages are 429/503/500/connection storms — all class A" should be softened to "HTTP-status storms" wherever it asserts the DoS is closed, so §1/§2.4/§5/§10 tell one *true* story. (Same root as H-2; recorded separately as a wording cleanup.)

---

## Verdict

Two High findings (H-1 transcript-wrapper wrong-cause precedence; H-2 SDK-stripped connection code), each grounded in a concrete production failure scenario and each falsifying a testable claim the spec makes (behaviors 3d and 2b). Both are the money-safe (mis-KEPT) direction, but both re-open the §1 self-DoS the classifier is claimed to close, for concrete vectors — so the round-3 B-2/H-1 fixes are **not yet genuinely closed** at the code-reachability level.

**NOT CONVERGED**
