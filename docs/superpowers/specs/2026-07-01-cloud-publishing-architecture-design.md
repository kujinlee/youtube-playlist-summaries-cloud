# Cloud Publishing Architecture — Design Spec

**Date:** 2026-07-01
**Status:** Draft v2 — hardened after Codex adversarial review (`docs/reviews/cloud-publishing-architecture-spec-codex.md`). Awaiting user review. One item (yt-dlp ToS, §2) needs a user decision that may change §11 #5.
**Scope:** Turn the single-user, local-first YouTube-playlist-summary tool into a hosted web service that unregistered guests can try and registered users can use durably. Staged: **public demo first, built on the SaaS spine so Stage 1 is not throwaway.**

Related memory: `cloud-multitenant-goal`, `data-corpus-state`, `project-context`.

---

## 1. Goal

Let a stranger open a URL and try the tool, and let a returning user keep a durable, private library of their summaries across devices — without a rewrite between those two milestones.

- **Stage 1 — Public demo.** Anonymous "taste" + free sign-in tier with a small metered allowance of the expensive operations. Ships the storage/auth/cost spine and shakes out cloud packaging.
- **Stage 2 — Multi-tenant SaaS.** Durable per-user libraries, usage tiers/paid plans, dig-deeper fully enabled behind an account, `mine=true` "my playlists" (roadmap path C).

The two stages share one architecture; Stage 1 is a constrained configuration of it, not a different system.

**Non-goal:** breaking the existing local personal tool. The author's local corpus and filesystem workflow must keep working (see §4, StorageAdapter seam). Cloud is an *added* deployment mode, not a replacement.

---

## 2. Why this is a re-architecture, not a deploy

The current app is unusually local-first. Three properties block naïve hosting (confirmed by codebase scan, 2026-07-01):

1. **Filesystem-native, no database.** Every summary, HTML, PDF, slide image, and `playlist-index.json` is a file under a local `-data` folder. The only access control is a check that the path is under `os.homedir()` (`lib/index-store.ts:31-51`) — meaningless on a shared host.
2. **Heavy local binaries.** `yt-dlp` + `ffmpeg`/`ffprobe` (slide capture, `lib/dig/slides.ts`), headless Chromium (`lib/pdf/`), macOS `osascript` folder picker (`app/api/pick-folder/route.ts`). These need a real container with disk — not serverless.
3. **No concept of a user.** Zero auth/session/ownership anywhere. Endpoints trust a bare `outputFolder`. Jobs live in an in-process `Map` (`lib/job-registry.ts`) that dies on restart.

The heaviest, most cloud-hostile feature — **dig-deeper slide capture** — is the *only* thing needing `yt-dlp`/`ffmpeg`. Summaries run off captions + Gemini alone. This separability shapes the staged plan and the worker design.

> **⚠ Legal/ToS gate (Codex H9) — needs a user decision before Stage 1D.** Running `yt-dlp` to download YouTube video on a *public server* is materially different from doing it locally: it can violate YouTube's Terms of Service, get the server's IP blocked, and make hosted dig-deeper operationally fragile. This conflicts with §11 #5 (dig-deeper in Stage 1). Resolve by choosing one: **(a)** proceed with counsel-approved scope; **(b)** drop hosted video download for the demo — dig-deeper is summary/transcript-derived only (no slide capture) in Stage 1, full slide capture deferred to Stage 2 / a local-only path; **(c)** redesign dig-deeper around officially permitted APIs/transcripts. Until resolved, treat §11 #5 as provisional.

---

## 3. Target architecture

One platform for web + worker (chosen over "Vercel frontend + external worker" because both options require the same long-running worker box; a single platform is materially less to operate for a solo developer). Supabase is the entire data/auth/storage/isolation spine.

```
                         Supabase
              [ Postgres + Auth(Google) + Storage + RLS ]
                     ^            ^            ^
        data / RLS   |     auth   |            |  artifacts (md / slides / html$ / pdf$)
                     |            |            |
 Browser  <——>  [ Next.js web + API ]  ——enqueue——>  [ Worker (same image / repo) ]
   |   FSA API / zip / obsidian://                       |  yt-dlp · ffmpeg · Gemini · Playwright
   |   (local export of MD, opt. HTML)                   |  honors per-user quota + daily spend cap
   +———— "connect vault" writes .md locally              +— writes canonical MD/slides + caches html$/pdf$

   $ = derived cache (regenerable from MD), not source of truth
```

**Components**

| Component | Responsibility | Notes |
|---|---|---|
| **Next.js web + API** | UI, auth session, light API (list/browse, enqueue jobs, serve/print/share docs) | Same repo as worker; deploy as web process |
| **Worker** | Long jobs: ingestion, summary (Gemini), dig-deeper (yt-dlp/ffmpeg/Gemini), PDF (Chromium) | Same image, runs a job loop instead of `next start`. Honors quota + spend cap. |
| **Job queue** | Durable job state + hand-off web→worker | **pg-boss** on Supabase Postgres (§11 #3). Full lifecycle — idempotency, leases, retries, dead-letter — in §9. |
| **Supabase Postgres** | Users, playlist/video index, job records, usage counters, share tokens | Source of truth for metadata. RLS-enforced isolation. |
| **Supabase Auth** | Google OAuth sign-in | Also unlocks `mine=true` playlist path C in Stage 2. |
| **Supabase Storage** | Canonical MD + slide images; cached HTML/PDF | Private buckets; served via signed URLs or proxying routes. |
| **Supabase RLS** | Per-user data isolation at the DB layer (`owner_id` policy) | Declarative tenant isolation — see §7. |

**Host for web+worker:** a long-running container platform with persistent disk. **Decided: Fly.io** (§11 #2); Cloud Run is the drop-in alternative if consolidating on GCP later. Host choice does not affect the architecture.

**AWS Lambda:** not used. The pipeline (yt-dlp/ffmpeg/long Gemini) is the opposite of Lambda's sweet spot (15-min cap, painful ffmpeg/Chromium layers, wasteful per-ms billing on long jobs). The one defensible Lambda candidate is isolated PDF export (`@sparticuz/chromium`), but with a worker box already present there is no reason to add a third deploy target. Revisit only if PDF/frame-extraction must burst in parallel beyond one worker (Stage 3+).

---

## 4. Storage model — three tiers

**Terminology (avoids a common mixup):** "Supabase" bundles *separate* services. **Supabase Postgres** is the **relational** DB (rows) — it holds structured metadata: users, index, job records, usage counters, share tokens, and *the object-storage path + version of each file*. **Supabase Storage** is an **object store** for **blobs** (S3-compatible — the same category of system as AWS S3 / Cloudflare R2). **All files — MD, slide images, HTML, PDF — live in object storage; no blob is ever stored in the relational DB.** Postgres only stores the *path/key* string into the object store (e.g. `u_abc/77/summary.md`) plus the version used for cache invalidation. "Source of truth" vs "derived cache" below is a distinction *within the same object store*: both are blobs in Supabase Storage; the only difference is source blobs must be preserved while cache blobs can be evicted and rebuilt from the MD.

**Decision (2026-07-01):** use **Supabase Storage as the single object store for all blobs** (source-of-truth *and* cache) — not raw AWS S3 / Cloudflare R2. One vendor, one credential set, access controls integrated with Supabase Auth/RLS. Portability preserved via the `StorageAdapter` seam (§4.1) and Supabase Storage's S3-compatible API, so a later move to R2/S3 is a bucket copy + adapter swap, not a re-architecture.

The central design principle. Categorize every output by **can the server cheaply regenerate it?** — not by file type.

| Tier | Artifacts | Regenerable? | Home |
|---|---|---|---|
| **Source of truth** | summary **MD**, model JSON, **slide images**, playlist/video **index + metadata** | No — MD/slides cost Gemini + yt-dlp to produce | **Server** (Supabase Storage for blobs, Postgres for index) + optional local mirror |
| **Derived cache** | **HTML doc**, **PDF** | Yes — deterministic render from MD (+ model/assets); PDF = Chromium pass | **Cache** in Supabase Storage, keyed by doc version. Safe to evict; rebuild from MD. Cached because regeneration (esp. PDF) costs time/compute. |
| **Local export** | MD → Obsidian vault; optionally HTML/PDF → download | — | User's disk, one-way. In *addition* to the server copy, never instead of it. |

**Why HTML/PDF are a cache, not a source of truth:** they are deterministic renders of the MD (`rerender-html` runs offline, no Gemini; Gemini is only invoked to regenerate the *MD*). Storing them is a valid, encouraged optimization — they just carry a version key and can be rebuilt if lost. The only artifacts that *must* persist are the MD, the slide images (un-regenerable without re-downloading video), and the index.

### 4.1 Storage seam — distinct capability contracts (preserves the local tool)

**Not one broad `StorageAdapter` (Codex H7).** `index-store`, `archive`, `settings-store`, `pdf`, `dig` have different semantics; a single adapter would leak local-only assumptions (`obsidian://`, `os.homedir()`, atomic rename, directory scans) into cloud code. Split into **five narrow capability contracts**, each with a local and a cloud implementation:

| Contract | Responsibility | Local impl | Cloud impl |
|---|---|---|---|
| `MetadataStore` | index/video/playlist records, CRUD, **transactional** mutations | `playlist-index.json` read-modify-write | Postgres rows + RLS |
| `BlobStore` | put/get/sign for MD, slides, HTML, PDF | files under `-data` | Supabase Storage |
| `ExportTarget` | one-way local export (MD/HTML → vault/download), `obsidian://` | direct FS write | browser FSA API / zip (server has none) |
| `SettingsStore` | app/user settings | `settings.json` | Postgres/env |
| `TempWorkspace` | scratch dir for yt-dlp/ffmpeg/Chromium | `.cache` | ephemeral container disk, cleaned per job |

**Rules the contracts must encode:**
- **Principal from day one (Codex H6).** Every `MetadataStore`/`BlobStore` operation takes an explicit principal (`owner_id` / anon-uid). There is no ownerless code path — the local impl passes a fixed single-user principal; the cloud impl passes the authenticated/anon uid. This prevents baking an ownerless schema in Stage 1A and reworking it in 1B.
- **Transactional metadata, not file-mimicking (Codex M4).** Cloud `MetadataStore` mutations use relational transactions with optimistic version checks or row locks — never a read-modify-write that mirrors the local JSON file's TOCTOU behavior. The index's "current position" / reconcile logic must be expressed as conditional `UPDATE`s.
- **Local-only ops are explicit.** `obsidian://` launch and `os.homedir()` guarding exist **only** in the local `ExportTarget`; the cloud impls must not reference them.

`LocalFsAdapter` (the bundle of local impls) keeps the author's personal single-user workflow intact; the Supabase bundle serves cloud. Selected by config/env. All `lib/index-store`, `lib/archive`, `lib/settings-store`, `lib/pdf`, `lib/dig` filesystem calls route through the matching contract. This is the single largest refactor and the spine both stages depend on.

**DB↔blob write consistency (Codex M3).** A blob + its metadata row must not diverge. Write order: upload to a temp key → verify → commit the DB artifact row/version → promote to the final key (or mark complete). A background sweep reconciles orphaned blobs (uploaded, never committed) and dangling rows (committed, blob missing).

---

## 5. Print & share (docs served from object storage)

**Principle: the user never talks to storage; the app does.** Buckets are private; the browser hits the app, and the app fetches from storage (signed URL or a route that streams the object *after* an RLS/token check). This preserves tenant isolation — no raw bucket URLs.

- **Print** — a browser action on a rendered page, unchanged by where bytes live: `Open doc` → app route serves the cached HTML → existing **Print** button (`window.print()`, PR #14) → browser dialog → paper or "Save as PDF." `@media print` CSS applies as today.
- **Share** — app-mediated:

| "Share" means | Mechanism |
|---|---|
| Send a viewable link | App issues `/share/<token>`; server verifies token → streams doc from storage. No raw bucket URLs. |
| Download the file | "Download PDF/HTML" → app route that **first verifies ownership/share against the DB artifact record**, then streams (Stage 1) or mints a short signed URL (later). |
| Native/mobile share | Web Share API (`navigator.share`) shares the app link or file via OS share sheet. |

**Share-token requirements (Codex B2).** Tokens are otherwise durable bearer credentials. Each token: ≥128-bit cryptographic randomness; **stored hashed at rest** (never plaintext in the DB); scoped to a specific `(document_id, owner_id)`; **default expiry** (e.g. 7 days) — not "optional"; explicitly **revocable** (revocation table / status column); audit fields (created_by, created_at, last_used_at). Every `/share/<token>` request re-checks hash + scope + expiry + revocation **before** any object is streamed.

**Signed-URL rule (Codex H2).** Never call `createSignedUrl` with a client-supplied path. A signed URL is minted only after the app resolves the artifact row by id, verifies ownership/share, and reads the *server-stored* key from that row. Stage 1 default is **app-streaming** (proxy the object through an authorized route); direct signed URLs are introduced only once storage-authorization tests exist.

**Output sanitization (Codex L1).** Model output and YouTube metadata (titles/descriptions) flow into rendered HTML → stored-XSS risk on shared docs. Markdown→HTML rendering must sanitize (allowlist), forbid raw embedded HTML, and the doc-serving routes set a restrictive CSP. Tests use hostile title/description/model-output payloads.

**PDF flow:** worker generates PDF once (Chromium) → uploads to Storage → "Download PDF" streams the cached object via the authorized route → regenerated only on doc-version change.

---

## 6. Obsidian feature in the cloud

The `obsidian://` handler is client-side (runs in the user's local Obsidian), so it survives a hosted page. Three tiers, best → universal:

1. **File System Access API** (`showDirectoryPicker()`, Chromium desktop): user grants the web app write access to their vault folder once; the app writes `.md` files straight in. Closest equivalent to today's behavior ("connect your vault"). HTTPS + user gesture; not in Firefox/Safari.
2. **Download vault `.zip`** (universal fallback): user unzips into their vault.
3. **`obsidian://new?vault=…&content=…`** deep link: works for small notes (content rides in the URI; length-limited).

Ship (2) for everyone; offer (1) as a Chromium nicety. Note: even in local-export mode, the MD's *canonical* copy stays on the server (so library + regeneration work); the vault copy is the export.

**Export conflict handling (Codex M5).** Export is strictly one-way (server → disk) and must not silently clobber a user-edited vault note. Use deterministic filenames, write a version marker in frontmatter, and on an existing local file with a different version prompt the user (overwrite / keep-both / skip) rather than overwriting.

**Rejected:** full local-first (canonical MD only on the user's disk, server as pure compute). Coherent and privacy-friendly, but breaks the guest/mobile try-it path (FSA API is Chromium-desktop-only), the Stage 2 cross-device library, and would move the regeneration/versioning machinery to the client — a large rewrite. Kept as a possible future "local-first mode" toggle, not the default.

---

## 7. Auth & tenant isolation

- **Supabase Auth with Google OAuth.** One identity provider; also the natural path to `mine=true` (roadmap C) in Stage 2.
- **Anonymous guests use Supabase anonymous auth — mandatory, not "cookie or optional session" (Codex H3).** Every guest gets a real anon `uid`; usage binds to that uid plus rate-limit dimensions (see §8). Cookie/IP are *additional* velocity signals, never the sole identity.

### 7.1 RLS policy matrix (Codex B1 — required before any SupabaseAdapter write)

RLS must be **specified, not asserted.** Before implementation, fill and enforce this matrix; `service_role` (which bypasses RLS) is confined to the **worker** and **never** used on any user-facing read/list/share path.

| Table | Owner col | RLS | Roles that read | Roles that write | Policy summary |
|---|---|---|---|---|---|
| `users` / `profiles` | `id` | force | self (authenticated) | self | row = own profile |
| `playlists` | `owner_id` | force | owner | owner + worker(service) | `owner_id = auth.uid()` |
| `videos` | `owner_id` | force | owner | owner + worker(service) | `owner_id = auth.uid()` |
| `artifacts` (md/html/pdf/slide rows + storage keys + version) | `owner_id` | force | owner (+ valid share token via a `SECURITY DEFINER` fn) | worker(service) | owner or scoped share |
| `jobs` | `owner_id` | force | owner | owner(enqueue) + worker(service) | `owner_id = auth.uid()` |
| `usage_counters` | `owner_id` | force | owner | worker(service, atomic) | see §8 |
| `share_tokens` | `owner_id` | force | none via anon; owner manages | owner | hashed; §5 |

Rules: RLS `FORCE` on every tenant table; user-facing routes use the **authenticated/anon** Supabase client (RLS applies); only the worker uses `service_role`, and every worker write sets `owner_id` explicitly. Share-token reads go through a `SECURITY DEFINER` function that validates the token rather than opening a broad policy. Isolation is verified by tests: user A cannot read/list/share user B's rows.

### 7.2 Storage key isolation (Codex H1)

Object keys are **server-constructed and canonical** — never built from user input (titles, filenames). Shape: `{owner_id}/{document_id}/{version}/{type}` (e.g. `u_abc/77/v3/summary.md`). Reject any user-derived segment containing `..`, `/`, absolute-path forms, or Unicode confusables; user-supplied text (titles) is stored in Postgres columns, not in keys. Access only via routes/functions that first evaluate ownership or a valid share token.

---

## 8. Cost & abuse model

An unauthenticated page calling a **paid** Gemini API on the app's key is a money drain and abuse target. Guardrails are non-negotiable.

**Tiers (Stage 1)**

| Tier | Identity | Allowance | Notes |
|---|---|---|---|
| Anonymous guest | Supabase anon `uid` + IP/device velocity | tiny taste: 1–2 **summaries**, **no** dig-deeper/PDF | Cheap, bounded, "see it work." |
| Free registered | Google sign-in | ~5 **dig-deeper** + ~5 **PDF** + N summaries, durable library | The real trial. Sign-in makes metering abuse-resistant (cookie-wipe can't reset a counter). |

*(Identity model decided — §11 #1: "anon taste + free Google sign-in for the 5.")*

**Enforcement — everything is preflight, before any provider work.** The cap/quota are only "backstops" if they gate *before* Gemini/yt-dlp/ffmpeg/Chromium runs; measuring spend afterward lets concurrent queued jobs blow past it (Codex B3/B4).

- **Atomic quota debit before enqueue (B4).** Reserve the unit with a single conditional statement — `UPDATE usage_counters SET remaining = remaining - 1 WHERE owner_id = $1 AND kind = $2 AND remaining > 0 RETURNING remaining` — inside the enqueue transaction. If no row returns, refuse. No read-then-decrement; concurrent submissions cannot both win.
- **Daily spend reservation (B3).** Maintain a `spend_ledger` for the day. Before enqueue, atomically **reserve** the job's *estimated* cost against `$DAILY_CAP`; refuse if it would exceed. On completion, **reconcile** to actual spend; on job failure/expiry, **release** the reservation. Endpoints return "demo at capacity, back tomorrow" once the day's reserved+actual hits the cap — regardless of per-user counters.
- **Anonymous summaries go through the same reservation (H4).** Anon taste is *not* exempt: bind the counter to the anon `uid`, add per-IP/device velocity limits, require a CAPTCHA/Turnstile challenge past a threshold, and refuse to enqueue when attribution is weak (fresh anon uid + new IP + high recent global rate).
- **yt-dlp resource limits (H5).** "Short-video allowlist" is not enough. Enforce, per download: max duration, max file size / byte cap, max resolution/bitrate, download timeout, retry cap, reject live/age-restricted/DRM formats, per-video cache reuse, and per-user + global concurrent-download limits.
- **PDF/Chromium resource limits (L3).** PDF is ~$0 in API terms but consumes CPU/memory/queue slots/storage. Meter it too: per-user PDF quota (the ~5), global Chromium concurrency, max page count/size, render timeout, and cache reuse by doc version.
- **Max free-users ceiling `N`** (waitlist beyond N) + max concurrent jobs (queue-depth limit).

**Cost sizing (from project data):** dig-deeper ≈ $0.046/section → a full dig doc ≈ $0.15–0.30 Gemini; 5 digs ≈ < ~$1.50/free user. Bounding free users + the daily cap keeps worst-case exposure predictable. Gemini 2.5 Flash list price (2026): $0.30 in / $2.50 out per 1M tokens.

### 8.1 Accounts & billing for the POC

**Claude Pro powers *development*, not the app's runtime.** A Claude Pro/Max subscription is for interactive use of Claude Code / claude.ai (i.e. building this) and **cannot be used programmatically** — subscriptions are not API access. The app itself **never calls Claude**; its AI is **Google Gemini** (`lib/gemini.ts`) plus the **YouTube Data API**. So the subscription and the app's runtime costs never intersect.

| Piece | Account / key | POC cost |
|---|---|---|
| Dev assistance (building it) | **Claude Pro** (already held) | already paid |
| App AI — summaries / dig-deeper | **Google Gemini API key** (pay-as-you-go billing enabled) | the only real cost; bounded by `$DAILY_CAP`. $0.30 in / $2.50 out per 1M tokens |
| Playlist / video metadata | **YouTube Data API key** | free (10k units/day quota) |
| Postgres + Auth + Storage | **Supabase** | free tier (≈500 MB DB / 1 GB storage) covers a POC |
| Web + worker hosting | **Fly.io** (see §11 #2) | free-ish / a few dollars |

**Gemini billing note:** for a *public* demo, enable **pay-as-you-go** on the Gemini key rather than relying on the free tier — the free tier is rate-limited (and may use data for training), which would throttle strangers mid-demo. The §8 daily kill-switch keeps the pay-as-you-go bill trivial. All keys live in the host's secret store, not `.env.local` (§9).

**Data-use & privacy requirement (Codex H8).** A public SaaS sends third-party content (playlist/video transcripts) and generated summaries to Gemini. Before launch: confirm the selected billing mode's data-use/retention terms (paid tier's no-training posture), configure retention/training controls where offered, and **disclose third-party AI processing** to users (a privacy note). This is a launch gate, not optional.

---

## 9. Server & runtime changes

Beyond storage/auth:

- **Durable job queue (pg-boss)** replaces in-memory `job-registry`; job records in Postgres survive restarts.
- **Job lifecycle — fully specified (Codex B5).** Each expensive artifact has a unique **idempotency key** `(owner_id, document_id, artifact_type, version)`; enqueuing the same key is a no-op/join, not a duplicate. Jobs use **leases with heartbeats** (a worker that dies loses its lease and the job is re-leased), **max attempts + exponential backoff**, a **dead-letter queue** for poison jobs, and **cooperative cancellation**. **Quota is charged once** — a retry does not re-debit the counter or re-reserve spend (reservation is keyed to the idempotency key). Partial outputs are written to temp keys and only committed on success (§4.1); failed/abandoned jobs release their spend reservation (§8) and get their temp artifacts swept.
- **Progress via Postgres polling (Codex M1).** The client polls the job/progress row (bounded frequency, durable status states) — **no SSE, no sticky sessions** in Stage 1. This works across multiple web instances without a shared pub/sub.
- **Worker runtime budgets (Codex M2).** Per job: wall-clock max, temp-disk cap, memory/CPU (machine size), and concurrency per worker. A job exceeding a budget is killed, its reservation released, its temp artifacts swept, and it is marked failed (not silently retried forever).
- **Graceful shutdown** (SIGTERM): stop leasing, let in-flight jobs finish or checkpoint, release leases so survivors re-lease on restart.
- **Health/readiness endpoints** for the platform LB.
- **Fail-fast env validation** at startup (`GEMINI_API_KEY`, `YOUTUBE_API_KEY`, Supabase keys, `DAILY_CAP`).
- **Config not from `process.cwd()`** — settings move to Postgres/env, not `settings.json` on disk (in the cloud `SettingsStore`).
- **Secrets** in the platform's secret store, not `.env.local`.

---

## 10. Staging & decomposition

Too large for one implementation plan. Decompose; each sub-project gets its own spec → plan → implementation cycle. This document is the north-star architecture; the first buildable slice is Stage 1A.

**Ordering correction (Codex H6):** ownership/auth schema comes **before** any cloud write, so the schema is never ownerless. Interface extraction (local-only) can precede it, but `SupabaseAdapter` writes must not land before RLS + `owner_id` exist.

**Stage 1 — public demo**
- **1A. Capability-contract interfaces** (§4.1), extracted with a **principal parameter from day one**. Refactor existing `lib/*` FS calls behind them; `LocalFsAdapter` keeps the personal tool green. *No cloud behavior yet — pure seam.*
- **1B. Auth + RLS schema + anonymous auth** (§7, §7.1, §7.2). Tables, `owner_id`, forced RLS policies, storage-key scheme — **before** any SupabaseAdapter write.
- **1C. `SupabaseAdapter` bundle** (MetadataStore/BlobStore/etc.) on the 1B schema, with the DB↔blob consistency protocol (§4.1).
- **1D. Cost guardrails** (§8): atomic quota debit, daily spend reservation/reconcile, velocity limits + CAPTCHA, yt-dlp/PDF resource caps.
- **1E. Worker + pg-boss + full job lifecycle + graceful shutdown** (§9). Summary path; dig-deeper path only if the §2 ToS gate permits (§11 #5).
- **1F. Serve/print/share from storage** (§5): app-streaming, share tokens, output sanitization/CSP; "download MD/HTML/zip" + optional FSA "connect vault" (§6).
- **1G. Operational controls (Codex M6):** per-route rate limiting, audit logging, abuse telemetry/dashboards, share-token management + revocation UI, storage/orphan cleanup jobs, backup/restore posture, and **RLS/security tests** (cross-tenant read/list/share, key traversal, token leakage).
- **1H. Deploy**: container host, secrets, health checks, spend monitoring/alerts.

**Stage 2 — SaaS**
- Durable per-user libraries + the browse/sort UI over Postgres.
- Usage tiers / paid plans / metering dashboard; **raise/monetize the dig-deeper & PDF limits** (the worker already carries yt-dlp/ffmpeg from Stage 1E — no image change; this is a quota/pricing change, and — if the §2 ToS gate deferred slide-capture — the point where hosted slide-capture is properly enabled).
- `mine=true` "my playlists" (roadmap C) via the Google identity.

**Each stage gate** follows `docs/dev-process.md` (Codex/Claude adversarial review + user approval).

---

## 11. Decisions (resolved 2026-07-01)

1. **Guest identity for the metered tier** — **anon taste + free Google sign-in for the ~5.** Anonymous visitors get summary-only (1–2); the dig/PDF allowance requires sign-in so the counter can't be reset by clearing cookies, and the auth spine is built early.
2. **Worker/web host** — **Fly.io** (long-running containers + persistent disk, simplest single-app model for the yt-dlp/ffmpeg/Chromium worker). *Cloud Run is the drop-in alternative if consolidating on GCP is preferred later — host choice does not affect the architecture.*
3. **Queue backend** — **Postgres-backed (pg-boss)**, reusing the Supabase Postgres — one fewer service than Redis/BullMQ.
4. **Spend guardrails (starting values, env-tunable)** — **`$DAILY_CAP` = $5/day**, **free-user ceiling `N` = 100**. Conservative for validation; raise via env once demand is proven.
5. **Dig-deeper in Stage 1** — **provisionally yes, metered (5) for free-registered users only** (cost ≤ ~$1.50/user, backstopped by the daily cap). **Gated on the §2 yt-dlp ToS decision:** if hosted video download is disallowed, Stage 1 dig-deeper is transcript/summary-derived only (no slide capture) and hosted slide-capture moves to Stage 2 / a local path.

**Object store (from §4)** — **Supabase Storage for all blobs** (source-of-truth + cache); portability preserved via the `StorageAdapter` seam and S3-compatible API.

---

## 12. Success criteria

- A stranger opens the URL, runs a summary on an allowlisted video, and reads/prints/downloads the result — without touching any local file or the author's data.
- A signed-in free user runs ~5 dig-deepers, sees them persist in a private library on a second device, and shares a view-only link.
- The author's existing local workflow (LocalFsAdapter) is unaffected.
- **System-wide** spend cannot exceed `$DAILY_CAP` in a day regardless of actor identity (enforced by the preflight reservation, §8) — even if one actor spreads across many IPs / anon sessions / Google accounts. Per-actor Sybil resistance (velocity limits, CAPTCHA) is best-effort, not a spend guarantee.
- Tenant data is RLS-isolated — verified by tests: user A cannot read, list, or share user B's rows or objects, and object keys resist traversal (§7.1, §7.2, §1G security tests).
