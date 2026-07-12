# Claude Task Review — Stage 2c Task 2 (summaryReady DTO field)

**Reviewer:** Claude (independent subagent). **Diff:** `cf850bb..70e4461`. **Date:** 2026-07-11.
**Verdict: Spec ✅ · Quality Approved.** §12 read-model change — reviewed adversarially; independently re-ran store suites (24 pass) + grepped beyond the report's pattern.

- **Schema:** `types/index.ts:85` `summaryReady: z.boolean().optional()` after `updatedAt`; `VideoSchema` has no `.strict()` → absent-field fixtures parse, stale jsonb keys not rejected.
- **Cloud derivation:** `supabase-metadata-store.ts:52-54` `=== 'promoted'` → concrete `false` for committed/absent, `true` only for promoted; appended AFTER `...(r.data as Video)` so derived value wins over any stale value. Reaches serveCloud via `PlaylistIndex`. **No non-owner leak** — `.select('data, updated_at').eq('playlist_id', pl.id)` unchanged, nothing widened.
- **stripComputed:** `Omit<T,'updatedAt'|'summaryReady'>` + destructures both; guards all three write paths (upsertVideo/updateVideoFields/bulkUpdateVideoFields). Strip test (`:273-289`) asserts `not.toHaveProperty` for BOTH + `toEqual({id:'vid1'})`.
- **Exact-shape migration:** independently grepped — `:159` migrated to `summaryReady:false` for both fixtures, `toEqual` retained (not weakened), concrete `false` (not undefined). `:259` write-path `toEqual(video)` unaffected (no computed keys in fixture). `videos-route-cloud`/`videos.test.ts` assert `.map(v=>v.title/.id)`, immune. No missed site.
- **Local path:** `LocalFsMetadataStore.readIndex` untouched → `summaryReady` stays `undefined` locally.
- **RED genuine:** `Expected true, Received undefined` pre-impl; derivation test distinguishes true/false/false — would fail on `undefined` or blanket `false`.

Non-blocking notes: new test at brief-specified path `tests/lib/supabase-metadata-store-summary-ready.test.ts`; mock helper duplicated (brief-sanctioned, not exported). Nothing extra; merge_video_data unchanged; session-client only.

⚠️ Cannot verify from diff: full 1957 regression + tsc clean (report-only; implementer reported green, Codex ran store suites green).

**Spec ✅ · Quality Approved.**
