# Codex Adversarial Review — Cloud Publishing Architecture Spec

**Reviewer:** Codex (frontier), fresh session
**Date:** 2026-07-01
**Target:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` (commit `211f750`)
**Verdict:** 5 Blocking, 9 High, 6 Medium, 3 Low. Spec asserted security/abuse/reliability properties without specifying enforcement — the review correctly demands enforcement detail before implementation.

---

## BLOCKING

- **B1 — RLS asserted, not specified (§7).** Doesn't define which tables are tenant-owned, which routes use anon/authenticated/service-role clients, or how worker writes avoid bypassing isolation. One missed service-role read on a list/browse/share path leaks another tenant's library. → Require a schema/policy matrix: every table, owner column, RLS forced status, allowed roles, CRUD policies, and which server paths may use service-role.
- **B2 — Share tokens = durable bearer credentials (§5).** "Optionally time-limited" + unspecified entropy/scoping/revocation makes leaked links permanent cross-tenant access. → Specify: crypto-random min entropy, hashed at rest, owner/document scope, default expiry, explicit revocation, audit fields, route-level checks before streaming.
- **B3 — Daily cap has no enforcement point (§8).** Called "the real backstop" but no preflight check before Gemini/yt-dlp/ffmpeg/Chromium work. Concurrent queued jobs exceed the cap before spend is observed. → Preflight reservation/debit: atomically reserve estimated cost before enqueue/start, refuse if cap would be exceeded, reconcile after, expire reservations on failed jobs.
- **B4 — Per-user counter race (§8).** "Decremented per job" — concurrent submissions all observe remaining quota and enqueue (esp. the 5 dig/PDF). → Atomic `UPDATE ... WHERE remaining > 0 RETURNING` (or row lock) before enqueueing expensive jobs.
- **B5 — Queue reliability hand-waved (§9).** "Graceful shutdown / requeue" undefined re leases, heartbeats, cancellation, retry limits, idempotency, partial-artifact cleanup. Retried dig/PDF can double-spend quota, duplicate objects, corrupt indexes, loop as poison jobs. → Specify pg-boss lifecycle: idempotency key per (artifact,version), lease timeout, heartbeat, max attempts, dead-letter, retry backoff, quota-charge-once policy, partial-output cleanup/commit.

## HIGH

- **H1 — Object-key namespacing insufficient (§7).** Keys from titles/ids/filenames without canonicalization → traversal / key confusion across the shared bucket. → Server-only canonical keys `user_id/document_id/version/type`; reject `..`, slashes in user-derived segments, Unicode confusables, absolute-path-like keys.
- **H2 — `createSignedUrl(path)` can leak raw storage credential (§5).** Wrong `path` → browser gets a bucket credential independent of app authz for its lifetime. → Signed URL only after DB ownership/share verification against the artifact record; never from client-supplied path; prefer app streaming in Stage 1.
- **H3 — Anonymous identity undecided (§7).** "cookie+IP (+optional anon session)" leaves the riskiest entrypoint's identity semantics open; cookie/IP metering trivially reset. → Make Supabase anonymous auth mandatory for guests; bind usage to anon uid + rate-limit dims; abuse controls for cookie clearing / IP rotation / account churn.
- **H4 — Anonymous summary spend (§8).** 1–2 paid summaries with resettable identity → unauthenticated Gemini spend before sign-in. → Same atomic quota/cap reservation as registered; per-IP/device velocity limits; CAPTCHA/Turnstile at threshold; deny queueing on weak attribution.
- **H5 — yt-dlp bandwidth/wall-clock unbounded (§8).** "Short-video allowlist + max concurrent" doesn't bound resolution/retries/throttling/live/age-restricted cost. → yt-dlp limits: max duration, file size, bitrate/resolution, download timeout, byte cap, retry cap, cache policy, per-user/global concurrent download limits.
- **H6 — Stage ordering bakes ownerless schema (§10).** 1A (StorageAdapter+SupabaseAdapter) before 1B (Auth+RLS) → ownerless schema/API, rework when RLS + owner-scoped keys arrive. → Schema-first ownership: minimal auth/RLS schema ahead of SupabaseAdapter writes; adapter contract requires `owner_id`/principal from day one.
- **H7 — StorageAdapter too broad (§4.1).** One adapter over index/archive/settings/pdf/dig leaks local-only assumptions (`obsidian://`, `os.homedir()`, atomic rename, dir scans). → Separate capability contracts: MetadataStore, BlobStore, ExportTarget, SettingsStore, TempWorkspace; mark local-only ops.
- **H8 — Gemini data-use/privacy unstated (§8.1).** No retention/training settings, user disclosure, or acceptability of sending playlist/summary content under the billing mode's terms. → Confirm Gemini data-use terms for the billing mode, configure retention/training controls, disclose third-party AI processing.
- **H9 — yt-dlp ToS/legal unresolved (§2).** Public-server video download can violate YouTube ToS, trigger IP blocking, make hosted dig-deeper fragile. → Legal/ToS gate before Stage 1D: counsel-approved scope, or remove hosted download, or transcript/officially-permitted-API only. **Conflicts with decision #5 — needs a user decision.**

## MEDIUM

- **M1 — Progress mechanism undecided (§9).** SSE across instances needs shared pub/sub or sticky routing. → Pick polling Postgres job/progress rows, bounded frequency, durable states, no sticky sessions.
- **M2 — Fly runtime budgets undefined (§3).** No disk/mem/CPU/duration/shutdown-window limits for yt-dlp/ffmpeg/Chromium. → Per-job wall-clock max, temp disk cap, machine size, concurrency/worker, over-limit behavior.
- **M3 — DB↔blob consistency protocol missing (§4).** Failed uploads/commits → dangling rows, orphaned blobs, version mismatch. → Upload temp key → verify → commit DB version → promote; orphan cleanup + integrity checks.
- **M4 — Index TOCTOU under cloud concurrency (§4.1).** Mirroring file read-modify-write of `playlist-index.json` → lost updates. → Relational/transactional metadata updates; optimistic version checks / row locks.
- **M5 — Obsidian export conflict behavior unspecified (§6).** FSA write can silently overwrite user-edited vault notes. → One-way, deterministic filenames, overwrite prompt, frontmatter version markers, conflict handling.
- **M6 — Stage 1 missing production controls (§10).** No rate limiting, audit logging, abuse telemetry, share-token mgmt UI, storage cleanup, backup/restore, RLS/security tests. → Add explicit Stage 1 work items.

## LOW

- **L1 — HTML sanitization/CSP unspecified (§5).** Model output / YouTube metadata → stored XSS in shared docs. → Markdown→HTML sanitization, CSP, forbidden raw-HTML policy, hostile-payload tests.
- **L2 — Success criterion overclaims (§12).** "No single actor past cap" impossible without distributed actor detection (many IPs/accounts). → Rephrase to system-wide cap regardless of actor; anti-Sybil best-effort.
- **L3 — PDF metered only by API cost (§8).** Chromium consumes CPU/mem/queue/storage. → Per-user PDF quota, global concurrency, max page size, timeout, cache reuse by version.

---

## Disposition
Blocking + High addressed by spec hardening (v2). H9 (ToS) surfaced to user as a decision that may change decision #5. Mediums/Lows folded in where cheap; M6/L-items become Stage-1 work items.
