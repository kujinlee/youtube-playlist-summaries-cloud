# Codex Adversarial Review — Stage 2a Implementation Plan

**Reviewer:** Codex (gpt-5.5) · **Date:** 2026-07-10 · **Target:** `docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md` (`24abf72`)

**Verdict:** 0 Blocking · 5 High · 5 Medium · 1 Low. Core SQL/trigger/ordering **sound**.

## Sound checks (verified correct)
- T1 `BEFORE UPDATE` trigger idempotent with RPCs setting `updated_at = now()`; closes the `upsertVideo` `.update({data})` gap. No recursion.
- T7 SQL valid: `(data || v_set) - (select coalesce(array_agg(c),'{}')…)` — parens correct, `jsonb - text[]` scalar-subquery works, empty-array no-op; `GET DIAGNOSTICS n = ROW_COUNT` counts matched rows; scalar `integer` round-trips via `rpc()`.

## High
- **H1 — T3 local `listPlaylists(ownerId)` not implementable:** local helper `listRecentPlaylists(root)` needs a filesystem root, not an ownerId (`recent-provider.ts:20`). Fix: keep `MetadataStore.listPlaylists(ownerId)` **cloud-only**; local `/api/playlists?root=` delegates directly to `listRecentPlaylists(root)`.
- **H2 — T12 `.tsx` test under `tests/integration/` won't run:** integration Jest matches only `.test.ts` (`jest.integration.config.ts:7`); unit `.tsx` only under `tests/components` (`jest.config.ts:11`). Fix: move to `tests/components/page-dispatch.test.tsx`.
- **H3 — T15 omits `VideoRow`:** it threads `outputFolder` into `VideoMenu`/`StarRating`/`NoteCell`/`VideoQuickView` (`VideoRow.tsx:110-177`). Add it to T15.
- **H4 — T16 cloud E2E can pass without cloud:** Playwright starts `npm run dev` with no `STORAGE_BACKEND=supabase` (`playwright.config.ts:11`). Fix: separate Playwright project/webServer with the env set.
- **H5 — client 401→`/login` redirect unassigned:** T10 only maps 401→`UnauthorizedError`; nothing wires the redirect. Add T15/T10 acceptance.

## Medium
- **M-a** T7 migration omits `revoke … from public; grant execute … to authenticated` (`0007:43,97`). Add it.
- **M-b** cloud route tests need explicit `STORAGE_BACKEND='supabase'` per file (`setup.ts` doesn't set it; existing cloud tests pin it). Add to T4–T8.
- **M-c** T7/T8 route wiring too implicit for fresh subagents — spell out full flow (`createServerSupabase→getUser→resolveOwnedPlaylistKey→getPrincipalFromSession→getStorageBundle`).
- **M-d** T6/T8 miss wrong-scope/invalid-playlist 400 tests. Add.
- **M-e** local `createdAt` from folder mtime is "recent" not "creation" (dissolves under H1's cloud-only local).

## Low
- Migration numbering: make T7 re-run `ls supabase/migrations | tail -1` immediately before creating 0016.
