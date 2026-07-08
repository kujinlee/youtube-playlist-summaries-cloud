# Stage 1D — Cost Guardrails — Design Spec

**Date:** 2026-07-08
**Status:** Draft **v7** — hardened across six dual adversarial rounds (r1–r6; Codex `task-mrclxoks`/`mrcme452`/`mrcmvol7`/`mrcnpezu`/`mrco7xj2`/`mrcopnpr` + a Claude Opus reviewer each; re-reviews in `docs/reviews/spec-stage-1d-v{2,3,4,5,6}-rereview.md`).
**v7 closes the round-6 Blocking (audio pricing) + three High:**
- **Audio input priced correctly (round-6 Blocking).** The transcription sends `fileData video/mp4` at LOW resolution, which downsamples frames but **not audio**; `gemini-2.5-flash` bills **audio input at ~$1.00/1M** vs $0.30/1M text/video. v6 priced the whole transcription input at the text rate → not a provable bound. v7 prices the **audio subset** (≤ `AUDIO_TOKENS_PER_SEC`(32) × `max_duration_seconds` — a documented, duration-bounded rate) at the audio rate and the remainder at the text rate; `est` **$1.25→$1.50**; the guard test imports the audio price + rate.
- **`countTokens` is now a hard fail-closed gate (round-6 High).** If `countTokens` cannot bound the video input (YouTube `fileData` unsupported), the cloud **disables the Gemini video-transcription fallback** (caption-less videos are rejected, never billed) — no rate-estimate escape. Top-line soundness claims are qualified as conditional on this gate.
- **Thinking + byte-cap now *verified*, not just requested (round-6 High×2):** an impl gate asserts `usageMetadata.thoughtsTokenCount == 0`; the byte primitive is named `Buffer.byteLength(rendered,'utf8')` with a mandatory multi-byte (CJK/emoji) test (the app has a first-class Korean path).
- Plus: PJ003 drops `floor` (`numeric >` matches the fractional-over-cap contract); the model assertion targets the **resolved** `SUMMARY_MODEL`/`TRANSCRIBE_MODEL` constant (not the raw env).
**v6 closed the round-5 Blocking + three High — the prior cost-leakage vectors:**
- **Byte-cap over the *rendered* prompt (round-5 Blocking).** v5 capped transcript *text* chars, but the billed prompt is `buildIndexedTranscript(segments)` (per-line `[i @m:ss] ` prefixes added *after* truncation) — pathological tiny segments explode it ~17× via the captions path, and `tokens ≤ chars` is false for multi-byte Unicode. v6 truncates by dropping whole trailing segments until **`buildIndexedTranscript(kept)` UTF-8 byte length ≤ `MAX_TRANSCRIPT_INPUT_BYTES`** (proof: `tokens ≤ bytes`); guard test + est use the byte cap.
- **Disable thinking tokens (round-5 High).** `gemini-2.5-flash` is a thinking model; thinking tokens bill at the output rate and aren't bounded by `maxOutputTokens`. v6 sets **`thinkingConfig.thinkingBudget: 0`** on the cloud calls (untyped `generationConfig` passthrough, like `mediaResolution`) so the output term is just `maxOutputTokens`.
- **Pin the priced model (round-5 High).** The model is env-selectable; v6 asserts the active model equals the priced `gemini-2.5-flash` (startup + guard test) so a pricier model can't slip past green CI.
- **`countTokens` preflight hardened (round-5 High):** identical LOW-res config, VOD-only (reject live/upcoming → closes TOCTOU), a timeout, and an impl-verification gate (honest duration×rate fallback if `countTokens` can't resolve YouTube `fileData`).
- Plus: `MAX_TRANSCRIBE_INPUT_TOKENS` consistency (300k hard reject), PJ003 regex length bound, dated/sourced price constants + deploy pricing check.
**v5 (superseded):** exported pass-count constants (guard recomputes), char truncation, `countTokens` preflight, `CloudGeminiCaps` threading, `CHECK max_attempts ≥ 1`, numeric PJ003, est $1.00→$1.25, `auth.uid()`→`p_owner_id`.
**v4 closed the round-3 Blocking (Codex): the estimate was not a *provable* upper bound because `max_duration_seconds` caps *seconds*, not *tokens*** — fix (user-chosen: enforce token caps): cloud-scoped `maxOutputTokens` + transcript truncation, `est` re-derived, plus round-3 Medium/Low fixes.
**v2 fixed** two round-1 Blockings — the bypass (→ server-mediated enqueue) and release-after-billing (→ never-release) — plus dig-reject, coarse-velocity wording, IP plumbing, distinct SQLSTATEs, UTC month, schema-test rewrites.
**v3 fixed the round-2 findings, which proved v2's cap-soundness fix incomplete:**
- **B-A (Blocking) — the reservation was still not an upper bound at the *job-retry* layer.** One job row could re-bill Gemini up to `max_attempts=5` times (requeue *and* crash-reclaim) against a single once-charged reservation. Fixed by **bounding billable executions to one per job row** (`summary_max_attempts=1`, set by `enqueue_job`) + re-deriving `est` as a genuine one-run upper bound (incl. inner `transcribe`/`generateJson` retries + `extractQuickView`) + a guard test that recomputes worst-case from **live** config × the attempt budget.
- **H-B (High) — two-client producer wiring was unspecified** and risked a cross-owner read leak. Fixed by an explicit **session-bundle (reads/resolve) vs. service `Enqueuer` (enqueue/preflight)** split; `listByPlaylist`/status/cancel never touch the service client.
- **H-C (High) — the coupling guard test was a static tautology.** Fixed: the test recomputes worst-case from the live `guardrail_config` row.
- **M-D — duration bound was producer-only.** Fixed: `enqueue_job` re-validates duration (PT003) and the handler constant drops to the 30-min cap (defense-in-depth).
- **M-E — signature-change blast radius under-enumerated.** Fixed: the ten affected integration files are enumerated in §8.

Pending round-3 re-review to convergence, then user approval.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §8, §11 (`$DAILY_CAP=$5/day`, free ceiling `N=100`, anon taste + free sign-in); §10 roadmap (`… → 1E-c → 1D → 1F/1G → 1H`).
**Stage:** 1D — the server-side money kill-switch. **Gates public deploy (1H).**
**Consumes / modifies:** the 1E-a/b/c job spine — reworks `enqueue_job` (0009→0011), the producer (`lib/job-queue/producer.ts`) + its enqueue path (now server-mediated via a service `Enqueuer`), sets `jobs.max_attempts` per kind, makes the worker's duration guard read config (`summary-handler.ts`), adds **cloud-scoped token caps** to the shared `gemini.ts` calls (options; local unchanged), and adds guardrail tables/config.

---

## 1. Goal & scope

1D adds the **preflight cost guardrails** on the enqueue path so the paid Gemini path can be safely exposed in 1H (parent §8). All server-side (SP1).

**In scope:**
- **Atomic quota debit** — per-account, per-kind, per-**month** allowance, consumed inside the enqueue transaction.
- **Daily global spend cap** — reserve a **worst-case estimated** cost against `$DAILY_CAP` at enqueue; **never released** in 1D (reserve-and-hold, fail-closed). The estimate is a genuine upper bound on a job row's **whole-lifetime** Gemini spend (one-run worst-case × the durable attempt budget; §3) and is never released, so `reserved ≥ actual` always → the cap is a *sound* money ceiling.
- **At-most-once billing** — a summary job row runs at most **once** (`summary_max_attempts = 1`, set by `enqueue_job`), so a requeue or crash-reclaim can never re-bill Gemini against the same reservation. (Inner Gemini retries — `transcribe`/`generateJson`/the 4-attempt summary loop — still provide within-run resilience.) This is what makes the once-charged reservation a lifetime upper bound; it also closes the known "AbortSignal-does-not-stop-billing on reclaim" limitation (`summary-handler.ts:130`).
- **Hosted duration cap** — reject videos longer than `max_duration_seconds` (default **30 min**) so per-job worst-case cost stays bounded and the estimate stays defensible. Enforced in the producer (nice per-video UX) **and re-validated atomically inside `enqueue_job`** (defense-in-depth backstop) so config drift or a direct service enqueue can't slip an over-long job past the estimate.
- **Enforced token limits (the token ceiling — round-3 Blocking fix)** — duration bounds *seconds*, but Gemini bills *tokens*, so 1D also enforces hard per-call token limits on the **cloud** path: `maxOutputTokens` on every cloud Gemini call and a **transcript-input truncation** to a fixed token budget before the summary/quick-view prompts. Together with the duration cap (which bounds the video-transcription *input* at fixed LOW resolution), every token term feeding `est` is code-enforced. These limits are **cloud-scoped** — threaded as options that default to unbounded, so the shared local pipeline (`gemini.ts`, which has no duration cap) is behaviorally unchanged.
- **Server-mediated enqueue (bypass closure)** — `enqueue_job` becomes **`service_role`-only**; the producer route calls it via a **service-role client** passing a **trusted `owner_id`** (from the verified session) and **trusted client IP** (from the edge header). Direct client `INSERT on jobs` and client `execute` on `enqueue_job` are **revoked**. The server route is the sole creation path — so quota/velocity/ceiling are unbypassable and the 1E-c grants-bypass is closed. Reads (`listByPlaylist`, status, cancel) stay on the caller's session client (RLS).
- **Per-IP velocity** (coarse) + **user/queue ceilings** + a **CAPTCHA seam** (`challengeRequired` signal; Turnstile widget+verify → SP2).

**Out of scope:** CAPTCHA widget + Turnstile verification → SP2; **true token-reconcile** (measured Gemini spend → enables safe *release*) → deferred refinement; per-device velocity → later; yt-dlp/ffmpeg/PDF/Chromium caps → N/A (hosted has none).

**Enforced now vs forward-looking:** only **summary** is enqueuable (dig handler = unbuilt 1E-b-2). 1D **rejects `job_kind != 'summary'`** at enqueue; the dig allowance/estimate rows exist but bind only when 1E-b-2 ships and lifts the reject.

---

## 2. Why this shape — decisions (v7)

1. **Sound cap = one-run worst-case est × bounded attempts + bounded duration + never-release (fixes round-1 Blocking-1 *and* round-2 B-A).** A cap only bounds money if `reserved ≥ actual` for the **whole lifetime** of every job row — including its durable retries. The soundness theorem:
   > `reserved = est ≥ per_run_worst(max_duration_seconds) × max_attempts ≥ Σ(actual spend over all executions of the row)`.
   The middle inequality is *pinned by an integration test* that recomputes `per_run_worst` from the **live** `guardrail_config` (`max_duration_seconds`) **and** the **imported** code constants — the enforced per-call token caps, the **exported pass-count multipliers** (`SUMMARY_MAX_PASSES`/`TRANSCRIBE_MAX_PASSES`/`QUICKVIEW_MAX_PASSES`, derived from `MAX_SUMMARY_ATTEMPTS` × `retries`), the LOW-res video token-rate, and prices — then multiplies by the **live** attempt budget (H-C fix). So *any* drift vector — DB `UPDATE` (duration/attempts) **or** a one-line code change (a token cap, a retry count, `MAX_SUMMARY_ATTEMPTS`) — that raises real cost without raising `est` fails CI (round-4 B1). The right inequality holds because each execution bills ≤ `per_run_worst` and the row executes ≤ `max_attempts` times.
   Round-2 (B-A) showed v2 satisfied neither side (once-charged `est` covered only one inner summary loop while `max_attempts=5` let requeue/reclaim re-bill). Round-3 (Codex) showed v3 *still* failed the `per_run_worst` bound: `max_duration_seconds` caps *seconds*, but Gemini bills *tokens*, and the code enforced **no** transcript-input cap and **no** `maxOutputTokens`, so a dense-caption 30-min video could out-bill the assumed 256k-in/4k-out figures. v4 makes the theorem hold by:
   - **(a) `summary_max_attempts = 1`** — `enqueue_job` sets `jobs.max_attempts` to the per-kind config value, so a summary row executes **exactly once** (any fail or reclaim → `attempts(1) ≥ max(1)` → `failed`/`dead_letter`, never requeued). Billable executions per reservation = 1. (Within-run resilience is preserved by the inner Gemini retries.)
   - **(b) bounded duration** — `max_duration_seconds` (30 min), enforced in the producer **and** re-validated in `enqueue_job` (M-D), keeps the video-**transcription input** finite (fileData tokens ≈ duration × LOW-res rate) and small.
   - **(c) enforced token caps (round-3→6 fix)** — every cloud Gemini call carries a `maxOutputTokens` cap **and `thinkingConfig.thinkingBudget: 0`** (thinking tokens bill at the output rate and aren't bounded by `maxOutputTokens`, so they are *disabled*, then **verified honored** via `usageMetadata.thoughtsTokenCount == 0` — round-6 H-r6-1); the transcript is truncated over the *rendered* `buildIndexedTranscript(kept)` string measured in **UTF-8 bytes** (`Buffer.byteLength(...,'utf8')`, not JS `.length`) ⇒ billed tokens ≤ bytes ≤ `MAX_TRANSCRIPT_INPUT_BYTES`, prefixes counted (round-5 B2 / round-6 H-r6-2); and the video-transcription **input** is hard-capped by a **`countTokens` preflight** (identical LOW-res config, VOD-only), with **audio priced at the audio rate** (round-6 Blocking). The **priced model is pinned/asserted** by its *resolved* constant so an env override can't inflate cost past CI (round-5/6). Every token term is code-enforced: transcription in (`countTokens`, audio-priced) & out (`maxOutputTokens`, no thinking), summary/quick-view in (byte cap) & out (`maxOutputTokens`, no thinking). Caps are cloud-scoped options via `CloudGeminiCaps` (§9); local passes none and is unchanged.
   - **(c′) fail-closed if the video-input can't be bounded (round-6 High).** The `countTokens` hard cap is *conditional* on `countTokens` resolving a YouTube `fileData` request (impl-verified). If it can't, the cloud **disables the Gemini video-transcription fallback entirely** — caption-less videos are rejected (`NonRetryableError`), never billed on an unbounded input. So no path ever bills an unbounded video input; the cap stays sound unconditionally (the *feature* degrades — caption-less support — not the money bound).
   - **(d) `est` re-derived** from those *enforced* limits × the full retry budget (`TRANSCRIBE_MAX_PASSES`=3; `SUMMARY_MAX_PASSES`=12; `QUICKVIEW_MAX_PASSES`=3) + fixed prompt/schema overhead + **audio-rate pricing of the transcription input** (§3), giving a true one-run upper bound. Provable worst case ≈ $1.15 → `est = $1.50` (≈30% margin).
   - **(e) never-release** in 1D. (Releasing on failure — parent §8 B3 — is only safe once true-reconcile measures actual spend; deferred. Never-release is fail-closed: a wasted reservation resets at the UTC day rollover.)
   Together `reserved ≥ actual` for the row's lifetime, so `$DAILY_CAP` is a real ceiling.
2. **Server-mediated enqueue (fixes Blocking-2 / Codex-B1 / Claude-H2).** The atomic debit is only tamper-proof if `enqueue_job` is the sole, server-controlled creation path with **trusted inputs**. Per-IP velocity can't work in a client-callable RPC (the client controls the IP arg). So: revoke client `INSERT on jobs` and client `execute` on `enqueue_job`; grant `enqueue_job` to **`service_role` only**; the producer route (already server-side) calls it via a **service-role client**, passing `p_owner_id` (the `getUser()` id) and `p_enqueue_ip` (the edge header). Running as `service_role` (which has table grants + `BYPASSRLS`, `0006:9`) lets the function write the guardrail tables **without** `SECURITY DEFINER` and sidesteps the definer-owner FORCE-RLS question (Claude-H2). Owner-safety comes from the server passing the verified `p_owner_id` + the composite FK `(playlist_id, owner_id) → playlists`. Reads stay on the session client (RLS unchanged).
3. **Monthly, period-keyed allowances (implicit refill, no reset job)** — `usage_counters(owner_id, kind, period_start, used)`, `period_start = date_trunc('month', now() at time zone 'utc')::date` (UTC, matching the daily ledger). New month → new row at `used=0`. Lets an occasional user return; the daily cap is the hard ceiling.
4. **Velocity is a *coarse* per-IP rate limit, not the money bound (Claude-M3).** With a sound cap (decision 1) the money guarantee is the daily cap; velocity is best-effort abuse-hardening enforced in the server preflight (trusted IP). It may admit a small burst past the limit — acceptable, because the cap still bounds dollars.
5. **CAPTCHA is a backend seam** (`challengeRequired` signal past a soft anon threshold; SP2's widget enforces). The coarse per-IP velocity is the 1D anon backstop.
6. **Tier = `profiles.is_anonymous`** (immutable).

---

## 3. Schema — migration `0011`

```sql
create table usage_counters (
  owner_id uuid not null references profiles(id) on delete cascade,
  kind text not null check (kind in ('summary','dig')),
  period_start date not null,                     -- date_trunc('month', now() at time zone 'utc')::date
  used int not null default 0 check (used >= 0),
  primary key (owner_id, kind, period_start));
alter table usage_counters enable row level security; alter table usage_counters force row level security;
create policy usage_counters_owner_read on usage_counters for select using (owner_id = auth.uid());
grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
grant select, insert, update, delete on usage_counters to service_role;

create table spend_ledger (                                          -- global, one row per UTC day
  day date primary key,
  reserved_cents int not null default 0 check (reserved_cents >= 0),
  actual_cents   int not null default 0 check (actual_cents   >= 0), -- inert in 1D; written by the deferred reconcile
  updated_at timestamptz not null default now());
alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)

create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
insert into quota_allowance values (false,'summary',20),(false,'dig',5),(true,'summary',2),(true,'dig',0);
alter table quota_allowance enable row level security; alter table quota_allowance force row level security;
create policy quota_allowance_read on quota_allowance for select using (true);   -- allowances are not secret → UI shows "X of N" (Claude-L3)
grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;

create table guardrail_config (id boolean primary key default true check (id),   -- singleton
  daily_cap_cents int not null default 500 check (daily_cap_cents >= 0),            -- $5.00
  summary_est_cents int not null default 150 check (summary_est_cents >= 1),        -- WORST-CASE one-run upper bound from ENFORCED token caps incl audio pricing (see below)
  dig_est_cents int not null default 150 check (dig_est_cents >= 1),
  summary_max_attempts int not null default 1 check (summary_max_attempts >= 1),    -- billable executions/row; enqueue_job sets jobs.max_attempts. ≥1: else the guard test (est≥worst×attempts) is tautological at 0 while claim_next_job still bills once (round-4 H2)
  dig_max_attempts int not null default 1 check (dig_max_attempts >= 1),
  max_duration_seconds int not null default 1800 check (max_duration_seconds >= 1),  -- 30 min hosted cap
  max_free_users int not null default 100, max_queue_depth int not null default 200,
  velocity_per_ip_hourly int not null default 15, captcha_soft_threshold int not null default 5);
insert into guardrail_config default values;
alter table guardrail_config enable row level security; alter table guardrail_config force row level security;
grant select, insert, update, delete on guardrail_config to service_role;   -- no client access

alter table jobs add column reserved_cents int not null default 0;   -- charged spend (never released in 1D)
alter table jobs add column enqueue_ip inet;                         -- server-provided (trusted); per-IP velocity
```

**Worst-case estimate derivation (the cap-soundness argument — this must hold or the cap is unsound).**
The estimate rests on **enforced** limits, not assumptions. The cloud path caps every token term; all inputs to the derivation are **exported code constants** so the §8 guard test imports and recomputes them (round-4 B1), passed as options so local is unchanged (§9):
- `MAX_TRANSCRIBE_INPUT_TOKENS` (300 000) — the video-transcription **input** hard cap: a `countTokens` preflight (identical LOW-res `generationConfig`, VOD-only) rejects a request above this *before* any billed `generateContent`. The code observes ~142 tok/s at LOW res (256k/1800s), so a real 30-min video (~256k) sits **under** the 300k reject with margin (round-5 M-new-1); 300k is the enforced bound, the rate is only a sanity note.
- `MAX_TRANSCRIBE_OUTPUT_TOKENS` (32 768) — transcription JSON output cap (sized ≥ the worst real 30-min transcript so it never truncates legitimate content — round-4 M2).
- `MAX_TRANSCRIPT_INPUT_BYTES` (40 960) — the transcript is truncated by dropping **whole trailing segments until the *rendered* `buildIndexedTranscript(kept)` UTF-8 byte length ≤ 40 960** (round-5 B2). **Proof it's a token bound:** a Gemini token spans ≥ 1 byte, so billed input tokens ≤ bytes ≤ 40 960; measuring the *rendered* string means the per-line `[i @m:ss]` prefixes + newlines are counted, not bypassed.
- `MAX_SUMMARY_OUTPUT_TOKENS` (8 192) — summary/quick-view JSON output cap. **Thinking is disabled (`thinkingBudget: 0`)**, so this bounds the entire billed output (round-5 H-new-1).
- Pass-count constants (exported): `TRANSCRIBE_MAX_PASSES` = 3, `SUMMARY_MAX_PASSES` = `MAX_SUMMARY_ATTEMPTS`(4) × (`retries`(2)+1) = 12, `QUICKVIEW_MAX_PASSES` = 3.
- `PROMPT_SCHEMA_OVERHEAD_TOKENS` (≈4 000/pass) — fixed prompt-template + responseSchema tokens added to each pass's input, on top of the (byte-capped) transcript block.
- Prices — `PRICE_IN_PER_1M_CENTS` = 30 (text/image/video), **`PRICE_AUDIO_IN_PER_1M_CENTS` = 100** (audio input; round-6 Blocking), `PRICE_OUT_PER_1M_CENTS` = 250 — **dated/sourced** (`gemini-2.5-flash`, 2026-07; no long-context tier). `AUDIO_TOKENS_PER_SEC` = 32 (Google-documented fixed audio tokenization rate) ⇒ audio tokens ≤ 32 × `max_duration_seconds` (duration-bounded, since LOW resolution downsamples frames but not audio). The **model is pinned/asserted by its resolved constant** — a deploy-time check + the guard test assert `resolved SUMMARY_MODEL/TRANSCRIBE_MODEL == priced model`; changing prices/model requires re-deriving `est`.

Caps are **generous** — they never truncate real ≤30-min speech content (≈8k tokens ≪ 40 960 bytes / 32 768 out), only the pathological/adversarial case. One-run worst case at 30 min, `gemini-2.5-flash`, thinking off, **every pass at max input+output**. The transcription input (≤ 300k tokens) is a mix of audio + video frames; since `countTokens` returns only `totalTokens`, price the **audio subset at its provable duration bound** (32×1800 = 57 600 tokens) at the audio rate, the remainder at the text rate:
- **Transcription** (`TRANSCRIBE_MAX_PASSES`=3): input/pass = 57 600×$1.00/1M (audio) + (300 000−57 600)×$0.30/1M (video) + 4 000×$0.30/1M (overhead) ≈ $0.0576+$0.0727+$0.0012 = $0.1315; output/pass = 32 768×$2.50/1M = $0.0819. Per pass $0.2134 × 3 ≈ **$0.64**.
- **Summary loop** (`SUMMARY_MAX_PASSES`=12): 12 × ((40 960+4 000)×$0.30/1M + 8 192×$2.50/1M) ≈ 12 × ($0.0135+$0.0205) ≈ **$0.41**. *(byte cap = input-token bound.)*
- **`extractQuickView`** (`QUICKVIEW_MAX_PASSES`=3): 3 × ($0.0135+$0.0205) ≈ **$0.10**. *(input bounded by summary output ≤ `MAX_SUMMARY_OUTPUT_TOKENS`; byte cap used as a safe over-estimate.)*
- One-run worst case ≈ **$1.15**. **`$1.50` (150¢) is set as the upper bound** (≈30% margin, absorbing the audio-rate/duration modeling).

**`summary_est_cents`, `max_duration_seconds`, `summary_max_attempts`, the code token caps, the pass-count constants, the prices (incl. `PRICE_AUDIO_IN_PER_1M_CENTS` + `AUDIO_TOKENS_PER_SEC`), AND the pinned model are a coupled set** — changing any requires re-deriving and raising `est`. The §8 guard test recomputes `per_run_worst` from the **live** `max_duration_seconds` **and every imported code constant** (caps, pass counts, overhead, all prices incl. audio, audio rate) × the retry budget, asserts `summary_est_cents ≥ per_run_worst × summary_max_attempts`, **and asserts the resolved model == the priced model** — so DB drift (`UPDATE`), code drift (a token cap, retry count, `MAX_SUMMARY_ATTEMPTS`, any price), and env-model drift all fail CI. At $1.50/$5 the cap admits ~3 summary jobs/day globally.

**L1 — the video-transcription input, and the fail-closed gate (round-6 High):** the video input cannot be capped a priori (you send a URL). The **runtime `countTokens` preflight** (LOW-res `generationConfig`, VOD-only) is the hard ceiling, sound iff two impl-verified facts hold: (a) `countTokens` resolves a YouTube `fileData` request (not just the URL string); (b) it uses the *same* LOW-res config as the billed call. **If (a) fails, the cloud disables the Gemini video-transcription fallback entirely** — caption-less videos are rejected (`NonRetryableError`), never billed — rather than reverting to a rate estimate (which would not be a ceiling). So the money bound is sound **unconditionally**; only the *feature* (caption-less transcription) is conditional on the impl-verification. VOD-only (reject live/upcoming) closes the mutable-URL TOCTOU (round-5 Codex-B3).

*(Config is admin-tunable via `UPDATE` — no migration. Defaults are §10 proposals.)*

---

## 4. Enforcement flow — `enqueue_job` rework (server-mediated)

**Grants/auth change:** `REVOKE INSERT on jobs FROM anon, authenticated` (keep `SELECT`); `REVOKE EXECUTE on enqueue_job FROM anon, authenticated`; `GRANT EXECUTE on enqueue_job TO service_role`. `enqueue_job` stays `security invoker` — but now runs **as `service_role`** (its only caller), which has the table grants + `BYPASSRLS` needed to write the guardrail tables. New signature adds a **trusted** `p_owner_id uuid` and `p_enqueue_ip inet` (both server-supplied):
```
enqueue_job(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int,
            p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet)
```
Body:
```
0. if auth.role() <> 'service_role' then raise 'enqueue_job: server only'; end if;   -- clients can't reach it
   if p_owner_id is null then raise 'owner required'; end if;
   if p_job_kind <> 'summary' then raise 'unsupported_job_kind';                       -- dig rejected until 1E-b-2 (Codex-H4/Claude-M1)
   end if;
   select * into v_cfg from guardrail_config where id = true;                          -- singleton, once
   v_est   := case p_job_kind when 'summary' then v_cfg.summary_est_cents   else v_cfg.dig_est_cents   end;
   v_maxatt:= case p_job_kind when 'summary' then v_cfg.summary_max_attempts else v_cfg.dig_max_attempts end;
1. INSERT job (owner_id = p_owner_id, enqueue_ip = p_enqueue_ip, max_attempts = v_maxatt, …)
     ON CONFLICT (owner,playlist,video,section,kind,version) WHERE status in (queued,active,completed)
     DO NOTHING returning id into v_id;
   if v_id is null → JOIN branch: return (existing_id, existing_status, joined=true). NO debit, NO reserve, NO duration check.  [charge-once; a drifted new payload never blocks an in-flight join — round-3 M3-3]
2. New row only → M-D duration backstop (robust cast; reject-not-admit for malformed — round-3 M3-1, round-4 M1):
     v_dur := (p_payload->>'durationSeconds');
     if v_dur is null or v_dur !~ '^[0-9]{1,7}(\.[0-9]{1,6})?$'  -- missing/non-numeric/over-long ⇒ reject. Length-bounded (≤7 int digits = ≤9,999,999s ≫ any real duration) so a 200k-digit decimal can't reach ::numeric and raise a precision error before PJ003 (round-5 Codex-M1). Exponent form (1e21) also misses the regex ⇒ reject (fail-closed).
        or v_dur::numeric > v_cfg.max_duration_seconds           -- NUMERIC compare, NO ::int and NO floor: 1800.999999 > 1800 ⇒ PJ003 (matches §8 fractional-over-cap test; round-6 M-r6). Regex length-bound already prevents ::numeric precision blowup.
        then raise 'too_long' USING ERRCODE='PJ003'; end if;     -- rolls back the INSERT
   v_anon := profiles.is_anonymous for p_owner_id; v_allow := quota_allowance[v_anon, p_job_kind];
   v_period := date_trunc('month', now() at time zone 'utc')::date; v_day := (now() at time zone 'utc')::date;
3. QUOTA DEBIT (atomic): insert usage_counters(p_owner_id,kind,v_period,0) on conflict do nothing;
     update usage_counters set used = used + 1 where owner_id=p_owner_id and kind=p_job_kind and period_start=v_period and used < v_allow;
     if NOT FOUND → raise 'quota_exceeded' USING ERRCODE='PJ001';      -- rolls back the INSERT
4. DAILY RESERVE (atomic): v_cap := v_cfg.daily_cap_cents;
     insert spend_ledger(day) values (v_day) on conflict do nothing;
     update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
       where day=v_day and reserved_cents + actual_cents + v_est <= v_cap;
     if NOT FOUND → raise 'daily_cap_exceeded' USING ERRCODE='PJ002';  -- rolls back INSERT + quota debit
5. update jobs set reserved_cents = v_est where id = v_id; return (v_id, 'queued', joined=false).
```
Distinct SQLSTATEs `PJ001` (quota) / `PJ002` (daily cap) / `PJ003` (too-long backstop) let the wrapper map typed errors without string-matching. **They deliberately avoid PostgREST's reserved `PT` class** (round-3 Codex-Low): a `PTxyz` code is reinterpreted by PostgREST as an HTTP-status override, so `PT001` would surface as a bogus status; a `PJ###` code passes through as a stable `error.code` to the supabase-js client. **`jobs.max_attempts` is set from config at INSERT** so a summary row is billable exactly once (soundness theorem, §2 dec.1) — the reservation `v_est` (one-run worst case) then bounds the row's whole lifetime. **No release path anywhere** (never-release, decision 1) — `fail_job`/`sweep_expired_leases`/`request_cancel_job` are unchanged; `reserved_cents` is retained for the deferred reconcile. **Charge-once:** debit only in the INSERT branch; auto-retry reuses the row (no re-INSERT); a manual re-submit after terminal is a new row = new charge (bounded by monthly quota + daily cap; interacts with 1E-c D2).

**Owner-safety under `service_role`:** RLS is bypassed for the write, but `owner_id = p_owner_id` is the **server-verified** session id (never client-supplied), and the composite FK `(playlist_id, owner_id) → playlists` rejects a playlist the owner doesn't own. `set search_path = public` retained.

**Migration requirement — replace EVERY `auth.uid()` with `p_owner_id` (round-4 M3).** The current `enqueue_job` (0009) uses `auth.uid()` in the auth guard, the INSERT, **and the idempotency-JOIN SELECT**. Under `service_role`, `auth.uid()` is **NULL**; a leftover in the JOIN-branch SELECT would make the idempotency lookup match nothing → the INSERT re-drives into a unique-index conflict → the 8-try loop exhausts with `retry limit exceeded` instead of joining. All `auth.uid()` references become `p_owner_id`; the caller-identity check becomes the `auth.role() <> 'service_role'` guard (step 0).

---

## 5. Producer + preflight + velocity + CAPTCHA seam + ceilings

**Two-client split (H-B).** The route holds two Supabase clients and hands the producer two distinct capabilities — never one mixed bundle:
- **session bundle** = `getStorageBundle({ supabaseClient: sessionClient })` — RLS-confined; used for auth, `resolvePlaylistId` (a per-owner `playlists` upsert, owner = `auth.uid()`), and all **reads** (`listByPlaylist`/status/cancel).
- **service `Enqueuer`** = a dedicated object built from `createServiceClient()` (`lib/supabase/service.ts`): `{ preflight(ip, ownerId), enqueue(ctx, key, payload) }`. It is the **only** thing that touches the service client, and it exposes **no read path**. The service client is **never** placed into a `StorageBundle.jobQueue` — so `SupabaseJobQueue.listByPlaylist` (whose own comment forbids service-role, else cross-owner leak) always runs on the session client.

`enqueuePlaylist(sessionBundle, enqueuer, principal, playlistUrl, { ownerId, enqueueIp })`:
1. Route authenticates via the **session** client (`createServerSupabase(cookies).getUser()`) → `ownerId`; extracts the **trusted client IP** (`Fly-Client-IP`, fallback `X-Forwarded-For` first hop).
2. `enqueuer.preflight(ip, ownerId)` (**advisory**, service client, spans all owners): `{ admitted, atCapacity, velocityExceeded, challengeRequired }` — per-IP hourly count (coarse), daily-cap-status/queue-depth, user-ceiling rank (registered beyond `max_free_users` by `profiles.created_at`), anon-past-soft-threshold. **Booleans only** (no cross-tenant data). Fast-fail: `velocityExceeded → 429`, `atCapacity → 503`, `!admitted → 403`; `challengeRequired` rides the `200`.
3. `resolvePlaylistId` via **`sessionBundle.metadataStore`** (session client, RLS); `fetchPlaylistVideos`; **blocks videos over `max_duration_seconds`** (`blocked:'too_long'`) before enqueue.
4. Fans out: for each enqueueable video, `enqueuer.enqueue({ ownerId, enqueueIp }, key, payload)` → `enqueue_job` on the service client with `p_owner_id=ownerId`, `p_enqueue_ip=enqueueIp`. `PJ001 → blocked:'quota_exceeded'` (per-video, continue); `PJ002 → blocked:'daily_cap'` (+ `dailyCapReached`, remaining cap-blocked); `PJ003 → blocked:'too_long'` (backstop; normally pre-blocked at step 3).

Velocity/ceiling/queue-depth are enforced **server-side with trusted inputs before the sole enqueue path** — not bypassable (Blocking-2 fix). They are *coarse and advisory* — **`max_queue_depth`, `max_free_users`, and per-IP velocity are checked only in the non-atomic `preflight`, not inside `enqueue_job`** (round-3 M3-4), so a concurrent burst can collectively overshoot them. This is by design: the **atomic** daily cap + quota (inside `enqueue_job`) are the real, race-free money/volume bounds; the advisory gates are abuse-hardening only.

---

## 6. Error contracts — extends the 1E-c producer/route

```ts
type JobFanoutResult = … | { videoId: string; blocked: 'quota_exceeded' | 'daily_cap' | 'too_long' };
interface ProducerCounts { enqueued; joined; skipped; failed; quotaBlocked; capBlocked; tooLong; }
//   INVARIANT: enqueued + joined + skipped + failed + quotaBlocked + capBlocked + tooLong === videos.length
//   ⇒ producer.ts:82 formula MUST become failed = enqueueable.length - created - joined - quotaBlocked - capBlocked (Claude-M4)
interface ProducerResult { playlistId; jobs; counts; challengeRequired?: boolean; dailyCapReached?: boolean; }
```
- Per-video `quota_exceeded` (PJ001): continue best-effort → `200`. Per-video `too_long`: normally blocked before enqueue (skip-like); the PJ003 backstop maps to the same `blocked:'too_long'` if it ever reaches the RPC.
- Mid-fan-out `daily_cap` (PJ002): remaining → `blocked:'daily_cap'`, `dailyCapReached:true`; jobs already enqueued this request are charged/valid → `200`. (Already-at-capacity caught by preflight → `503`.)
- Preflight: `429`/`503`/`403`; `challengeRequired` on `200`.
- The TS enqueue path maps `PJ001`/`PJ002`/`PJ003` to `QuotaExceededError`/`DailyCapError`/`VideoTooLongError`. The producer consumes a dedicated **`Enqueuer`** interface (not `StorageBundle.jobQueue`), whose `enqueue(ctx, key, payload)` takes a **context** `{ ownerId: string; enqueueIp: string | null }` so owner/IP flow through the type layer (Claude-M5/Codex-M6); the concrete `SupabaseEnqueuer` wraps the **service-role** client and also exposes `preflight`. `SupabaseJobQueue` (session client) keeps only the read/cancel surface — its `enqueue` is removed from the producer path.

---

## 7. Security & RLS

- **Server-mediated writes:** clients have **no** way to create a job — `INSERT on jobs` and `execute enqueue_job` are revoked; the server route (holding the service-role key) is the sole enqueuer, passing a verified `owner_id` + trusted edge IP. This makes quota/velocity/ceiling authoritative and closes the 1E-c bypass. `enqueue_job`'s first statement rejects any non-`service_role` caller (belt-and-suspenders).
- **Reads unchanged, and structurally isolated from the service client (H-B):** `listByPlaylist`/status/cancel run on the caller's **session** client, RLS-confined by `jobs_owner`. The service client lives **only** inside the `Enqueuer` (enqueue + preflight), which has **no read method** — so a future edit cannot accidentally route a cross-owner read through service-role. The producer route authenticates the user via the session client before invoking the service `Enqueuer`.
- **Owner-safety without RLS with_check:** the write bypasses RLS (service_role) but sets `owner_id` from the server-verified session and validates the composite FK — a caller cannot enqueue for or cite another owner.
- **Guardrail tables:** `usage_counters` — owner may `SELECT` own rows only. `quota_allowance` — world-readable (non-secret allowance numbers, for the UI). `spend_ledger`/`guardrail_config` — no client access (service_role only). No client can inflate its allowance or read/alter global spend.
- **`enqueue_preflight`** runs on the service client; returns only booleans (no cross-tenant leak). **IP privacy:** `jobs.enqueue_ip` is server-set for abuse control; RLS-confined; documented.

---

## 8. Testing strategy

The guardrail logic is integration-tested against live Postgres; the producer against a fake bundle.

| Layer | Coverage |
|---|---|
| **Integration** (live PG) | **Debit:** enqueue to allowance → `quota_exceeded (PJ001)`; JOIN/auto-retry does **not** re-debit; **UTC-month rollover** (seed prior-month row ⇒ current month fresh). **Concurrency:** N parallel distinct-video enqueues (service client, distinct `p_owner_id` or same-owner) with allowance < N ⇒ exactly `allowance` succeed (proves atomic `UPDATE…WHERE used<allowance`). **Cap:** reserve→`daily_cap_exceeded (PJ002)`; **all-or-nothing** — a cap reject leaves `usage_counters` unchanged; **no-release** — a `fail_job`→terminal does **not** change `spend_ledger` (reserve-and-hold). **At-most-once billing (B-A):** a summary job enqueued via `enqueue_job` has `jobs.max_attempts = summary_max_attempts (1)`; assert a claimed-then-`fail_job(retryable=true)` row goes **`dead_letter`, not `queued`** (no requeue → no re-bill), and a swept expired lease at `attempts=1` also `dead_letter`s. **Duration backstop (M-D/M3-1):** `enqueue_job` with `payload.durationSeconds > max_duration_seconds` → `too_long (PJ003)`; a **fractional** over-cap duration (`90.5`-style, non-int) → `PJ003` (not a raw `22P02` cast error); a **missing/non-numeric** `durationSeconds` → `PJ003` reject (not silently admitted); a live-job **JOIN** with a drifted over-cap payload returns `joined=true` (not blocked). **Bypass closure:** a client session `rpc('enqueue_job',…)` is **denied** (execute revoked, 42501) and `from('jobs').insert` is **denied**. **Owner-safety:** server enqueue with a `p_owner_id` not owning `p_playlist_id` fails the FK. **dig reject:** `p_job_kind='dig'` → `unsupported_job_kind`. anon vs registered allowance via `is_anonymous`. `enqueue_preflight` verdicts. Guardrail tables reject client writes; `quota_allowance` is client-readable; **new guardrail tables appear in the `schema.test.ts` RLS-forced assertion.** **Cap-soundness sizing (drift-proof, not tautological):** the test **reads `guardrail_config` from the DB** and **imports EVERY code constant** the derivation uses — token caps (`MAX_TRANSCRIBE_INPUT_TOKENS`, `MAX_TRANSCRIBE_OUTPUT_TOKENS`, `MAX_TRANSCRIPT_INPUT_BYTES`, `MAX_SUMMARY_OUTPUT_TOKENS`), **pass-count constants** (`TRANSCRIBE_/SUMMARY_/QUICKVIEW_MAX_PASSES`), `PROMPT_SCHEMA_OVERHEAD_TOKENS`, **all prices incl. `PRICE_AUDIO_IN_PER_1M_CENTS` + `AUDIO_TOKENS_PER_SEC`** — recomputes `per_run_worst` via the §3 derivation as a **function** (audio subset at the audio rate), and asserts `summary_est_cents ≥ per_run_worst × summary_max_attempts`. It **also asserts the resolved `SUMMARY_MODEL`/`TRANSCRIBE_MODEL` constants (post-`??`, exported from `gemini.ts`) == the priced model** (round-6 M-r6-1) — not the raw env var. So DB drift, code drift (any cap/pass-count/`MAX_SUMMARY_ATTEMPTS`/retry/**any price incl. audio**), **and** model drift without raising `est` **fail CI**. (`CHECK summary_max_attempts ≥ 1` prevents the tautological `×0`.) |
| **Unit** (gemini caps) | Each cloud Gemini call forwards `maxOutputTokens` **and `thinkingConfig.thinkingBudget: 0`** into `generationConfig` (assert all three carry both); the transcript is truncated by dropping whole trailing segments until **`Buffer.byteLength(buildIndexedTranscript(kept), 'utf8') ≤ MAX_TRANSCRIPT_INPUT_BYTES`** (round-6 H-r6-2 — measure **UTF-8 bytes**, never JS `.length`) — assert with a **multi-byte (CJK/emoji) segment set** that the *rendered* prompt's byte length (incl. `[i @m:ss]` prefixes) is ≤ cap, that the **same** kept list feeds `resolveTranscriptTokens` so `[[TS:n]]` stays in range, and a ≤cap transcript is untouched; the **`countTokens` preflight** uses the **same LOW-res config** and rejects a video > `MAX_TRANSCRIBE_INPUT_TOKENS`; a **live/upcoming video is rejected VOD-only**; **local path unchanged** (no `CloudGeminiCaps` ⇒ no caps/thinking/truncation/preflight). |
| **Impl-verification gates** (one-time, live/recorded) | (1) **thinking honored** — a representative cloud transcribe+summary with `thinkingBudget: 0` returns `usageMetadata.thoughtsTokenCount` 0/absent (round-6 H-r6-1); fail startup/flag if not. (2) **`countTokens` on YouTube `fileData`** — resolves the video's tokens (not the URL string) at LOW res; **if not, the video-transcription fallback is disabled** (caption-less → reject) so the bound stays sound (round-6 H-r6 / §2 c′). |
| **Unit** (producer) | fan-out with quota exhausting mid-list → per-video `quota_exceeded` + `counts`; `too_long` block; mid-fan-out `daily_cap` → `dailyCapReached`; preflight verdict → HTTP mapping; `challengeRequired` passthrough; **disjoint sum incl. the new buckets = videos.length** (the corrected `failed` formula); enqueue called via the service client with `{ownerId, enqueueIp}`. |
| **Route** | `429`/`403`/`503` (+ `Retry-After`); `challengeRequired` in body; `200` mixed enqueued/blocked; IP extraction from `Fly-Client-IP`/`X-Forwarded-For`; the write uses the service client, reads the session client. |

**Test-migration note (Claude-H3 / round-2 M-E — behavior-shape changes, not mechanical swaps).** The REVOKE + new `enqueue_job(p_owner_id, …, p_enqueue_ip)` signature break every test that enqueues as an authenticated session. Migrate each to the **service-client** enqueue path with explicit `p_owner_id`/`p_enqueue_ip`; `service_role` admin inserts/updates are unaffected. **Enumerated affected integration files** (`grep enqueue_job|.enqueue( tests/integration/`):
- `job-queue-schema.test.ts` (the direct jobs-insert / idempotency cases — **NOT** `schema.test.ts`, round-3 Codex fix) — "insert for another owner rejected by with-check" → now a **grant error (42501)** (owner-safety is server-set `owner_id` + FK, not a with-check policy); "idempotency index blocks a second live job" → go through `enqueue_job`, the second call **joins** (`joined=true`, **no error** — the old `.error` assertion inverts).
- `schema.test.ts` (core RLS/schema assertions, a **separate** file) — extend its "RLS enabled AND forced on every owned table" assertion to cover the new guardrail tables; no enqueue changes.
- `cancel-by-playlist.test.ts`, `cancel-job-rpc.test.ts`, `job-queue-runner.test.ts`, `job-queue-store.test.ts`, `job-queue-producer.test.ts`, `job-queue-playlist-identity.test.ts`, `job-queue-worker.test.ts`, `worker-main.test.ts` — switch direct session `enqueue_job`/`.enqueue` to the service path + new args.
- `jobs-producer-polling.test.ts` and `producer-roundtrip.test.ts` — **count/shape-asserting**; update to the two-client producer (`sessionBundle` + service `Enqueuer`) and re-baseline expected `counts`, watching for silent breakage.

---

## 9. Built in 1D but touching shared code
**Enforced token caps (cloud-scoped) — the `CloudGeminiCaps` threading contract.** All three cloud Gemini calls receive caps (the round-4 gap: only `generateSummary` was wrapped while `transcribeViaGemini` — via `resolveTranscriptSegments` — and `extractQuickView` were raw). One object threads through the whole boundary:
```ts
interface CloudGeminiCaps {
  transcribeInputTokens: number;   // countTokens preflight reject threshold (MAX_TRANSCRIBE_INPUT_TOKENS)
  transcribeOutputTokens: number;  // maxOutputTokens for transcribeViaGemini
  transcriptInputBytes: number;    // truncate rendered buildIndexedTranscript(kept) to ≤ this UTF-8 byte length (MAX_TRANSCRIPT_INPUT_BYTES)
  summaryOutputTokens: number;     // maxOutputTokens for generateSummary + extractQuickView
  // thinkingBudget is always 0 on the cloud path (constant, not tunable) — see below
}
```
- **`gemini.ts`** — add an **optional** `caps` param to `transcribeViaGemini`, `generateSummary`, `extractQuickView`; when present, set `generationConfig.maxOutputTokens` **and `generationConfig.thinkingConfig = { thinkingBudget: 0 }`** (untyped passthrough — the SDK spreads `generationConfig` into the request body; same technique as `mediaResolution`, `gemini.ts:515`). Add a `countTokens` preflight inside `transcribeViaGemini` that builds the request with the **same LOW-res `generationConfig`**, calls `model.countTokens`, and throws `NonRetryableError` when `totalTokens > transcribeInputTokens` (timeout-bounded; double fetch noted). **If the impl-verification finds `countTokens` can't resolve YouTube `fileData`, disable the transcribe fallback** (caption-less → `NonRetryableError`) rather than proceeding unbounded (§2 c′). **Export the *resolved* model constants** (`SUMMARY_MODEL`/`TRANSCRIBE_MODEL`, post-`??`), the sizing + pass-count constants, and the **dated price constants (incl. audio price + `AUDIO_TOKENS_PER_SEC`)** for the §8 guard test; assert `resolved model == priced model` at handler init.
- **`transcript-source.ts`** — `resolveTranscriptSegments` gains an optional cap slot so the transcribe fallback receives `transcribeInput/OutputTokens` (current signature carries only `{signal}`).
- **`summary-core.ts`** — `summaryCore`'s `opts` gains an optional `caps: CloudGeminiCaps`, forwarded to **all three** injected deps. The transcript truncation — **drop whole trailing segments until `Buffer.byteLength(buildIndexedTranscript(kept), 'utf8') ≤ transcriptInputBytes`** (UTF-8 bytes, *not* JS `.length` — round-6 H-r6-2), the same `kept` list feeding the prompt and `resolveTranscriptTokens` (so `[[TS:n]]` stays in range) — happens here or in the injected wrapper.
- **`summary-handler.ts`** (cloud) — constructs `CloudGeminiCaps` from the exported constants and passes it into `summaryCore`. **Local callers pass nothing** → no `maxOutputTokens`, no `thinkingBudget`, no truncation, no preflight → the local pipeline (no 30-min cap, arbitrary-length videos, thinking on) is behaviorally unchanged. **Shared-code refactor touching already-merged code** (CLAUDE.md re-review trigger) — §8 lists `gemini.ts`, `transcript-source.ts`, `summary-core.ts`, `summary-handler.ts` as touched.
- **Producer (`producer.ts`)** — reject **live/upcoming** videos alongside the `too_long` duration block (VOD-only), so the `countTokens` preflight operates on immutable media (closes the round-5 Codex-B3 TOCTOU).

## 10. Deferred / seams
- **Handler duration constant (M-D / M3-2, done in 1D):** lower `summary-handler.ts:17` `MAX_DURATION_SECONDS` from `4*3600` and make it **read `guardrail_config.max_duration_seconds`** (not a hard-coded `1800`) so that if an admin raises the cap (and `est` per the guard test), the handler doesn't then reject admitted jobs between 1800s and the new cap. The `enqueue_job` PJ003 check is the primary backstop; this handler check is the last line. `max_duration_seconds` is thus coupled to **three** sites: producer pre-block, `enqueue_job` PJ003, handler guard (all read the config value).
- **CAPTCHA widget + Turnstile verification** → SP2 (1D signals `challengeRequired`).
- **True token-reconcile → then safe release.** Thread `result.response.usageMetadata` (gemini.ts → summaryCore → handler result → `complete_job(p_actual_cents)` → `spend_ledger.actual_cents`), then switch from reserve-and-hold to reserve→reconcile-actual-on-success→release-on-failure (parent §8 B3). `spend_ledger.actual_cents` is provisioned; `jobs.reserved_cents` is retained for it. Until then, **never-release** keeps the cap sound.
- Per-device velocity; CAPTCHA hard-enforcement; refined estimates from real usage.
- **1E-c D2:** a manual re-submit after terminal failure = new job = new quota debit + reservation (documented; bounded).

## 11. Open questions / tunables
1. **Cap-soundness coupling (the load-bearing one):** `summary_est_cents` ($1.50) must remain ≥ `per_run_worst(max_duration_seconds, token-caps, pass-counts, overhead, prices incl. audio) × summary_max_attempts`. Raising the duration cap, the attempt budget, **any code token cap, pass-count/`MAX_SUMMARY_ATTEMPTS`/retry default, or any price (incl. audio)** **requires** re-deriving and raising the estimate; the §8 guard test recomputes from live config + all imported code constants and fails otherwise. Confirm the 30-min / $1.50 / 1-attempt triple (~3 summary-jobs/day at the $5 cap). **Note the est evolution across review rounds** (30¢→50¢→75¢→$1.00→$1.25→$1.50) as each round proved a term wasn't a real upper bound (retry layer, token vs duration, thinking tokens, audio pricing); ~3 jobs/day globally is the price of a *provable* cap. Raise the daily cap for more throughput.
2. **At-most-once billing (round-2 B-A, v3):** summary jobs get `max_attempts=1`, so a failure or crash-reclaim **dead-letters** rather than re-running/re-billing; the user manually re-submits (new job, new charge). This trades durable auto-retry for an airtight cap and relies on the inner Gemini retries for within-run resilience. Confirm acceptable for the demo, or raise `summary_max_attempts` (and `est` proportionally) if auto-retry is wanted.
3. **Never-release (v2):** 1D holds reservations for the UTC day (fail-closed); release requires the deferred true-reconcile. A wasted reservation resets at midnight UTC — safe/conservative. Confirm acceptable vs the parent §8 "release on failure" (unsafe without measured spend).
4. **Anon lockout, incl. the token-cap failure mode (Claude-M6 + round-4 M2):** with charge-once + never-refund-quota + anon allowance 2/mo, two failed jobs exhaust an anon month with no output. v5 adds a new failure path: a legitimate but **dense** ≤30-min video whose transcript JSON would exceed `MAX_TRANSCRIBE_OUTPUT_TOKENS` (or whose input trips the `countTokens` preflight) now **dead-letters, quota-charged, no output** where pre-1D it completed. Low-probability (caps sized ≥ worst real 30-min transcript) but real. Accept (documented, tunable) — chosen default — or refund quota on infra-terminal later. Confirm.
5. **Single user can drain the global daily cap (round-2 Low):** the daily cap is **global**; a single registered user (~3 summary/day-worth at $1.50 each = the whole `$5/day`) can consume it before their monthly quota bites, blocking everyone until UTC midnight. By-design for the validation demo (global cap is the money kill-switch; per-user monthly quota is a separate, looser bound). Confirm; a per-user *daily* sub-cap is a later refinement if needed.
6. **Thinking disabled on the cloud path (round-5 H-new-1) — quality tradeoff:** `thinkingBudget: 0` eliminates thinking-token cost (essential — with thinking on, worst-case balloons past $2.5 and `est` would be ~$3, ~1–2 jobs/day). The cost is some summary/transcription quality vs a thinking-enabled run; the 4-attempt summary quality loop + inner retries mitigate. Confirm acceptable for the demo, or raise `est` to fund a small `thinkingBudget`.
7. **Tunable defaults** (§3 seeds): registered 20 summary + 5 dig/mo, anon 2 summary/mo; `$5/day`; `$1.50`/kind one-run worst-case; `1` attempt/kind; 30-min duration; VOD-only; N=100; queue 200; velocity 15/IP/hr; CAPTCHA soft 5. Code constants (§9, deploy+guard-test, not `UPDATE`): `MAX_TRANSCRIBE_INPUT_TOKENS`=300000 (`countTokens` reject; ~142 tok/s observed ⇒ ~256k real ≤ 300k), `MAX_TRANSCRIBE_OUTPUT_TOKENS`=32768, `MAX_TRANSCRIPT_INPUT_BYTES`=40960 (rendered, UTF-8), `MAX_SUMMARY_OUTPUT_TOKENS`=8192, `thinkingBudget`=0, `PROMPT_SCHEMA_OVERHEAD_TOKENS`=4000, pass counts 3/12/3, prices 30/**100 (audio)**/250 ¢-per-1M + `AUDIO_TOKENS_PER_SEC`=32 (dated `gemini-2.5-flash` 2026-07), model pinned/asserted (resolved constant).
