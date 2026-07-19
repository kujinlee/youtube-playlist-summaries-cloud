# Round-2 Adversarial Re-Review: Stage 3 Cloud Sync M2a

Re-reviewed the revised plan against the round-1 findings, the v10 spec, and the real source files behind the claims.

## Blocking

None.

## High

### H1 — Task 6: equal-value Class-B shortcut drops timestamp-only human edits

Failure scenario: baseline has `corrections: "fix" @ t1`; local clears and re-types the same `"fix"` at `t3`; cloud still has `"fix" @ t1`. The spec says Class-B change detection is over the `(value, annotationsEditedAt)` pair and explicitly calls out same-value re-add as meaningful (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:168-175`). The revised implementation short-circuits on value equality alone and returns `winner: 'equal'` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1021-1027`), and the test now encodes that behavior (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:955-957`). `applyClassBWinners` only writes winner sides (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1901`), so the older replica never receives the newer timestamp. Future merges then compare against stale live timestamps, while the manifest may be advanced from `mergedHuman`, creating baseline/live drift.

Specific fix: when values are equal but timestamps differ, return a non-conflicting winner for the newer timestamp, or add an explicit timestamp-convergence action that writes the same value plus source `editedAt` to the older side. Keep `conflict:false`, but do not return `winner:'equal'` unless the `(value, editedAt)` pair is equal. Add tests for same-value re-add vs unchanged and both-cleared-with-different-clear-timestamps.

### H2 — Task 10: token write path chmods an unsafe parent before checking it

Failure scenario: `~/.config/youtube-playlist-summaries` already exists as mode `0777` and is owned by the current user. `makeFileTokenStore.write()` creates/chmods the directory and then calls `assertSafeParent` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1594-1599`). The `chmod(0700)` masks the exact pre-existing group/world-writable condition that §6 says must fail closed (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:235-240`). The read-side test catches unsafe parents (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1522-1530`), but the write path silently launders them.

Specific fix: on write, `stat` the existing parent before chmod. If it exists and is group/other-writable or foreign-owned, throw. Only create a missing parent with `0700`; after creation, verify ownership/mode. Add a write-path test where an existing `0777` parent causes `store.write()` to reject.

### H3 — Task 12: additive create still copies derived-cache metadata while only copying the MD blob

Failure scenario: cloud-only video has `summaryMd: "a.md"` and `summaryHtml: "htmls/a.html"` from a previous render. A fresh local hydrate runs `copyAdditiveVideo`; the plan says to write the receiver metadata via `to.upsertVideo(toP, video)` and only copy `video.summaryMd` bytes (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1902`). The real `Video` record includes cache pointers such as `summaryHtml`, `digDeeperHtml`, and MD fields (`types/index.ts:56-59`). The result is a receiver record advertising derived cache artifacts whose blobs were never copied. This violates the plan/spec money invariant: additive create must never resurrect derived cache (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:17`; `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:199-202`). T14 adds a test row for this (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2121`), but Task 12's executable helper contract contradicts it.

Specific fix: define `sanitizeAdditiveVideo(video)` in Task 12 and use that in `copyAdditiveVideo`: copy metadata/source fields and companion scalars, but clear `summaryHtml`, `digDeeperHtml`, PDF/cache artifact entries, and any other regenerable cache pointers before `upsertVideo`. The additive-cache test should assert the receiver record itself has those fields null/absent, not merely that blobs were not written.

## Medium

### M1 — Task 12: one-sided presence handling is still a comment before non-null assertions

Failure scenario: a video is present only in cloud and absent locally. The behavior table says additive-create/delete handling happens first (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1789-1797`), but the orchestration snippet leaves that as `// ...` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1937-1938`) and then immediately calls `deriveHumanSnapshot(lv!)`, `readMdBody(..., lv!)`, and `deriveClassASignals(lv!, ...)` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1940-1947`). If implemented literally, the first hydrate/publish case throws before additive copy. The note at `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1971` says to implement the block fully, but it does not give executable branch structure.

Specific fix: replace the presence comment with explicit code-level branches:
`if (!lv || !cv) { handle baseline-aware delete/additive create; write verified baseline if created; continue; }`
Only run Class B/Class A after both `lv` and `cv` are non-null. Add a test that would fail on the current non-null assertion path.

## Low

None beyond the prior Low items marked in the closure audit below.

## Round-1 Closure Audit

- Codex B1 / mdHash from `summaryMd` key: closed. Task 5 now takes `deriveClassASignals(video, mdBody)` and hashes the body (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:812-813`); Task 12 adds `readMdBody` using `BlobStore.get` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1889-1894`). Source confirms `summaryMd` is a key written separately from MD bytes (`lib/pipeline.ts:56-57`, `lib/pipeline.ts:264-266`).
- Codex B2 / regenerate not stamping currency: closed. Task 4 explicitly edits `app/api/videos/[id]/regenerate/route.ts` to stamp `mdGeneratedAt` and `mdCorrectionsHash = mdHash(trimmedCorrections ?? '')` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:721-730`). Source confirms that route is the current corrected-MD writer (`app/api/videos/[id]/regenerate/route.ts:60-71`).
- Codex B3 / equal-mdHash skip bypassing currency/format: closed. Task 7 skips only for both-current or both-stale+same-major and otherwise falls through to currency/format (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1195-1212`).
- Codex H1 / RPC overload ambiguity: closed. Migration 0021 drops old `update_video_annotations` and `merge_video_data` signatures before creating defaulted signatures (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:454-463`), matching the old signatures in `supabase/migrations/0016_update_video_annotations.sql:13-15` and `supabase/migrations/0007_storage_and_rpcs.sql:81-82`.
- Codex H2 / `sourceMdHash` never written: closed. Task 4 now requires every model writer, primarily `lib/html-doc/generate.ts`, to set `sourceMdHash: mdHash(sourceMd)` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:732`). Source confirms `generate.ts` is a real envelope writer (`lib/html-doc/generate.ts:49-55`).
- Codex H3 / token parent-dir fail-closed: partially fixed, re-filed as H2. Read-side checks exist, but write-side chmod masks unsafe existing parents.
- Codex M1 / Task 12 placeholder: partially fixed. The plan now has helper contracts, behaviors, and an RLS note (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1785-1807`, `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1897-1911`), but one-sided orchestration remains comment-plus-non-null assertions, re-filed as M1.
- Codex M2 / archived-only creates empty `annotationsEditedAt`: closed. SQL now guards `jsonb_set` behind `v_stamp <> '{}'::jsonb` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:494-501`).
- Codex L1 / `mdHash` accidentally persisted on `Video`: closed in the plan. Global constraints and `buildBaseline` now state `mdHash` is manifest/in-flight only (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:20`, `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1910`).
- Claude B1: same as Codex B2, closed.
- Claude B2: same as Codex H1, closed.
- Claude H1: partially fixed; see Codex M1 closure and re-filed M1.
- Claude M1 / `persist_summary` dropped guard risk: closed. Revised plan shows only a diff and instructs copying the 0009 body verbatim (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:542-556`), preserving the real ownership guard (`supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:108-110`).
- Claude M2 / confinement misses scripts/cloud-sync: closed. Task 10 requires extending confinement/import guards to include sync code (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1645-1651`).
- Claude M3 / integration harness undesigned: closed. Task 3 now specifies the shared harness and fault-injection seam (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:433-439`) and Task 12 consumes it (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1850`).
- Claude M4 / local production `updateVideoFields` stamping untested: closed. Task 4 adds explicit `updateVideoFields({ corrections })` and non-Class-B tests (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:651-672`).
- Claude M5 / equal-value different timestamp conflict: partially fixed but regressed. The spurious conflict is gone, but the new value-only `winner:'equal'` short-circuit loses timestamp edits; re-filed as H1.
- Claude L1: same as Codex M2, closed.
- Claude L2 / one-sided stale hydrate needsRegen false: closed. Task 7 one-sided branches set `needsRegen: !current(...)` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1186-1189`).
- Claude L3 / conflict dedup omits playlistKey: closed. Task 9 includes `playlistKey` in the dedup key (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1425-1429`).
- Claude L4 / no additive-cache test: partially fixed. T14 adds a scenario (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2121`), but Task 12's helper contract still copies the whole `Video`; re-filed as H3.

## Verdict

NOT CONVERGED
