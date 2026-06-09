# Codex Adversarial Review — resolve-folder backend

**Date:** 2026-06-08 · **Model:** gpt-5.5 · **Mode:** --fresh
**Scope:** `lib/output-folder.ts`, `app/api/resolve-folder/route.ts`, `lib/youtube.ts` + tests

## Verdict: no blocking issues.

## Findings

**HIGH**
- `app/api/resolve-folder/route.ts:21-27` — every `resolveOutputFolder` failure becomes HTTP 400 with the raw error message. Internal failures (`fetchPlaylistTitle` / Google API / network) should be 500 generic; only validation ("no list= id") should be 400. Also leaks internal detail.
  → **Fixed:** title fetch now caught + falls back to id slug (no propagation); a typed `InvalidPlaylistUrlError` maps to 400, anything else → 500 generic.

**MEDIUM**
- `normalizeToRoot` returns `''` for input `/` (strips all trailing slashes). → **Fixed:** empty guard (`|| '/'`).
- `normalizeToRoot` over-strips a folder literally named `raw` that is the data root. → **Fixed:** only strip `/raw` when `raw/playlist-index.json` exists (it's a real playlist raw dir).
- Empty-slug title (all punctuation) → `<root>/raw`. → **Fixed:** `slugify(title) || slugify(playlistId) || playlistId`.

**LOW / INFO**
- Untested branches: corrupt/unreadable index skip, `readdirSync` throwing, non-dir entries, `fetchPlaylistTitle` rejection, `normalizeToRoot('/')` / root-named-`raw`. → **Added tests** for the key ones.

**Confirmed non-issues:** nested returns `<dir>/raw`, flat returns `<dir>`, `&si=` stripped by URL parser, missing `list=` rejected, corrupt indexes skipped, missing/unreadable root scans cleanly.

## Disposition
All HIGH/MEDIUM addressed; LOW test gaps added. Re-ran full suite + tsc after fixes.
