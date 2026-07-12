# Claude Adversarial Review — Stage 2c Plan (round 1)

**Reviewer:** Claude (independent subagent). **Date:** 2026-07-11.
**Artifact:** `docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md` (`a082a19`).
Verified every load-bearing claim against the codebase (migrations 0001–0016, both share routes, serveCloud html path, metadata store, VideoSchema, lib/client/api.ts, VideoMenu/VideoRow/NewPlaylistModal, both migrated test files, lib/share/ttl.ts, app/globals.css).

## BLOCKING
None. Core spine sound: `0017` is next free number; DROP+CREATE signature matches `0013:22`; grants re-applied; qualified `returning share_tokens.id into v_id` correct + needed (OUT column named `id`); `return query select v_id, p_expiry` valid; supabase-js returns `data` as array for a table fn so `data[0]` right (matches `claimVideoSlot` at supabase-metadata-store.ts:88); only 3 caller sites (route + 2 test files) — no missed caller; `resolveExpiry` already handles never/7/30.

## HIGH
**H1 — dead tokens `--text`/`--bg`/`--bg-elevated`.** `app/globals.css` defines `--surface-base/-raised/-overlay`, `--text-primary/-secondary/-muted`, `--border/-strong`, `--accent`, `--success`, `--warning`, `--danger`. The three named tokens don't exist; jest/jsdom can't catch invalid CSS vars → ships an unstyled modal. Doubly wrong because Task 5 says reuse `NewPlaylistModal`, which already uses the correct tokens. Same defect 2b flagged. **Fix:** `--bg`→`--surface-base`, `--bg-elevated`→`--surface-raised`, `--text`→`--text-primary`; add a "tokens that exist" guard.

## MEDIUM
**M1 — `role="menuitem"` in Task 6 sketch breaks the Task 6 `getByRole('link')` tests.** An `<a href>` with explicit `role="menuitem"` is not exposed as a `link`. Also diverges from existing `VideoMenu` markup (`<li role="none"><a className=…>`). **Fix:** drop `role="menuitem"`, wrap each new item in `<li role="none">`, keep tests on `getByRole('link')`.

**M2 — `summaryReady` not added to `stripComputed` — violates the `updatedAt` invariant the plan cites.** `stripComputed` (supabase-metadata-store.ts:14) strips `updatedAt` before every write to `videos.data` (guards upsertVideo:99, updateVideoFields:118, bulkUpdateVideoFields:134) so a readIndex-computed key never round-trips into jsonb. Task 2 adds `summaryReady` to the same mapping but never updates `stripComputed`. No current caller round-trips, so nothing breaks today, but it silently breaks the stated rule and risks a future write baking stale `summaryReady`. **Fix:** `Omit<T,'updatedAt'|'summaryReady'>` + destructure both; add a strip test mirroring the updatedAt one.

**M3 — `share-mint-route.test.ts` `beforeEach` default mock (line 19) returns a scalar → every non-overriding happy path becomes 404 after the route change.** New route `Array.isArray(data)?data[0]:null` → `null` for a scalar default → `!row` → 404. Plan Step 5 edits only the 201 test body, never the default. Also the snippet says `rpc.mockResolvedValue` but the file's variable is `mockRpc`. **Fix:** update line-19 default to `{ data: [{ id, expires_at }], error: null }`; correct `rpc`→`mockRpc`.

**M4 — reused modal skeleton's self focus-restore fights Task 7's restore.** `NewPlaylistModal` has `useEffect(… return () => returnFocusRef.current?.focus())` (17-21) capturing `document.activeElement` at mount. Task 7 restores via `menuTriggerRef.current?.focus()` in `onClose`. On close, the modal's unmount cleanup focuses the stale captured element, overriding the trigger → fails Task 7's `toHaveFocus()`. **Fix:** Task 5 must drop the self-restore cleanup; restoration owned solely by VideoRow.

## LOW
- **L1** `scope.playlistId` not type-guaranteed non-empty in cloud mode (addScopeParam throws on empty). Fine in practice; add a guard/note.
- **L2** revoke `{revoked:false}` (already-revoked/non-owned) treated as success — acceptable for 2c; add a one-line note.
- **L3** Task 1 Step 1's replacement drops the original row-exists/owner assertions (share-tokens-rpc.test.ts:26-28); Task 8 re-establishes isolation but keep them.

## Sound areas (verified)
- `VideoSchema` has no `.strict()` (the 3 strict sites are unrelated schemas); optional `summaryReady` leaves all parse fixtures green; `VideoMeta` untouched.
- Local path provably untouched (serveLocal → LocalMetadataStore, no artifacts → undefined); no non-owner leak.
- Migration return-type change, grants, qualified RETURNING, `data[0]` all correct.
- Cross-task interfaces line up; no placeholders.
- Global constraints §11 satisfied (session-client, no service role, merge_video_data untouched, no charging/guardrail change).

**Verdict:** needs changes before implementation — fix H1 + M1–M4; L-items optional.
