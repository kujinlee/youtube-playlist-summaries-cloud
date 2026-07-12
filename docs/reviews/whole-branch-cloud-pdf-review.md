# Cloud Summary PDF — Whole-Branch Review (merge gate)

**Branch:** feat/cloud-summary-pdf · **Base:** merge-base(master,HEAD) = `db5cbfc` · 46 commits, 50 files, +4493/−77.
**Gate:** full unit 2076/2076, tsc 0, integration 341/343 (2 pre-existing skips). Dual whole-branch review hunting CROSS-CUTTING defects per-task reviews couldn't see.

## Verdict: ✅ SYSTEMICALLY SOUND — MERGEABLE. Both passes 0 Blocking / 0 High.

## Codex (gpt-5.5) — 0 Blk/High/Med/Low
Systemically sound. Verified: money (PDF resolves before cache lookup but fresh models short-circuit before `reserve_serve_model` → cache hits don't charge); owner-scoped isolation (session client + owner/playlist-scoped blob keys); nonce-free cache determinism + render-versioned keys; owner-scoped single-flight + bounded Chromium slots; NO schema/RPC/package drift. `check:confinement` passed; `git diff --check` clean. (`npm run build` fails only on sandbox-blocked Google Fonts fetch — not branch code.)

## Claude (opus) — ✅ mergeable, 0 Blk/High
Traced all 9 cross-cutting concerns end-to-end:
- **Money:** `resolveAndParse` is the ONLY charge path (`reserve_serve_model` inside `resolveMagazineModel`, reached only after `readFreshMagazineModel` fails). PDF route resolves exactly once; nonce difference applied AFTER resolve → charge behavior BYTE-IDENTICAL to the HTML route. PDF cache hit resolves but doesn't charge on a fresh model. No double-resolve, no PDF-only charge surface. Concurrency single-charge via the DB-level `reserve_serve_model` lease (atomic cross-instance); the in-memory single-flight/slot guards only the non-charging render, and duplicate renders write identical content-addressed bytes (idempotent).
- **Isolation:** session client only (`createServerSupabase(cookieStore)` → `getStorageBundle({supabaseClient})`); ownership via `resolveOwnedPlaylistKey`; flight key `${principal.id}/${principal.indexKey}/${key}`; every blob op principal-namespaced. No service-role anywhere.
- **Cache determinism:** `renderMagazineHtml` deterministic given (parsed, model); key salted by `PDF_RENDER_VERSION`; `base` per-video-unique disambiguates the object name; re-materialized content → new HTML → new hash (no stale served); 64-bit truncation only disambiguates different HTML under the same base → wrong-bytes collision ~2⁻⁶⁴, never cross-video/cross-owner.
- **Error mapping** consistent across both routes; PdfBusyError/PdfRendererUnavailable→503, 400→400, else 500; `assertCloudSummaryMdKey`'s 409 caught inside `loadSummaryForServe`; no internal leak.
- **assertCloudSummaryMdKey newly in html path** regression-free: legit keys `padSerial(≥3)_slugify(≤60).md` sit comfortably inside the allowlist.
- **No schema/RPC/migration change**; `merge_video_data` + `reserve_serve_model` untouched.
- **Local path intact:** `POST /api/videos/[id]/pdf` still calls `generateDocPdf(html, principal, rel)` no-opts → void; container args gate on `STORAGE_BACKEND==='supabase'`; local semantics unchanged.
- No dead/mis-wired modules, no dependency drift.

### 3 Low / informational — ALL no-fix
1. A PDF view whose MODEL blob was evicted regenerates+charges the model even on a PDF cache hit — but this is IDENTICAL to the HTML path's repair behavior (not a new charging surface, never more than HTML). No fix.
2. Cloud PDF depends on Chromium in the web-tier container — tracked as the Task-12 pending operational gate. Not a code defect.
3. Concurrent same-content single-flight sharers inherit one render's `PdfBusyError` if that render loses the slot race — retry-safe backpressure, not a correctness issue.

## Convergence
Both passes CLEAN (0 Blocking/High), corroborating across independent reviewers. The 3 Lows are known-and-accepted (two were anticipated in the design; the third is the documented single-flight composition note). No fix cycle required. Branch is mergeable pending the human merge decision (auto-merge grant spent).
