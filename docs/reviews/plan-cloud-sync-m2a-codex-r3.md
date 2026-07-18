# Round-3 Adversarial Re-Review: Stage 3 Cloud Sync M2a

Re-reviewed v3 against the round-2 findings, the v10 spec, and the real source files the plan cites.

## Round-2 Closure Audit

- N1 / `sourceMdHash` hashes filename instead of MD body: mostly closed, but see M1. The executable T4(c) instruction now correctly says `sourceMdHash: mdHash(md)` where real `lib/html-doc/generate.ts:33` has the MD body, while `video.summaryMd` is the key (`lib/html-doc/generate.ts:29-36`, `lib/pipeline.ts:56-57`, `lib/pipeline.ts:264`). The new test asserts `mdHash(BODY)` and `not mdHash(env.sourceMd)` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:780-785`). However the T4 file list still says `mdHash(sourceMd)`.
- H1 / Class-B equal-value timestamp drift: closed for the named case. `reconcileField` now returns the newer-timestamp side as a non-conflicting winner when values match but timestamps differ, and reserves `winner:'equal'` for true `(value, editedAt)` equality (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1045-1057`). The tests cover both true equality and timestamp convergence (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:972-981`). `applyClassBWinners` is specified to write each winner to the loser with the source timestamp (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1948`). New baseline hazard below is separate.
- H2 / token write chmod-launders unsafe parent: closed. `assertSafeParent` throws `ENOENT` for a missing parent and throws for unsafe existing parents (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1604-1613`). `write()` checks before touching an existing parent and only chmods a directory it just created (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1633-1645`). The write-path 0777-parent test is present (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1562-1569`).
- H3 / additive create copies derived cache pointers: closed in intent, with one new wiring bug below. `sanitizeAdditiveVideo` now clears `summaryHtml`, `digDeeperHtml`, `digDeeperMd`, and all `artifacts.*` except `artifacts.summaryMd` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1949`). That is complete against current `VideoSchema` top-level cache fields (`types/index.ts:56-59`) and the cloud-only artifact shape surfaced by `SupabaseMetadataStore.readIndex` (`lib/storage/supabase/supabase-metadata-store.ts:49-55`).
- N2 / T12 one-sided presence NPE: closed for the null deref. The orchestration now has explicit `if (!lv || !cv) { ... continue; }` before any `lv`/`cv` two-sided dereference (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1985-2004`). It handles baseline-present as delete-suppression and baseline-less as additive create. New additive-copy tuple bug below.
- N3 / local `updateVideoAnnotations` drops `corrections`: closed. T4(d) explicitly widens the local allowlist and adds a source-timestamp test (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:674-685`, `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:753`), matching the current source gap (`lib/storage/local/local-metadata-store.ts:67-84`).
- N4 / `buildBaseline` underspecified for skip: partially closed. The helper now says it records agreed post-reconcile state and advances on `skip` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1958`, `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2028-2029`). But it still lacks enough information to avoid advancing unresolved Class-B skip-conflicts; see H2.
- N5 / bare regenerate stamps empty corrections hash: closed. T4(b) now computes `effectiveCorrections` from the stored value when the param is absent and stamps `mdHash(effectiveCorrections)` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:737-747`). Real source confirms bare regenerate currently strips the callout and does not call `fixSummary` when no correction param is provided (`app/api/videos/[id]/regenerate/route.ts:53-66`), so the plan's "confirm if future behavior changes" note is appropriate.

## Blocking

None.

## High

### H1 - Task 12: additive create has no receiver blob store, so MD copy cannot be implemented correctly

Failure scenario: cloud-only video hydrates to local. The presence branch destructures `from`, `fromP`, `fromBlob`, `to`, and `toP` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1994-1998`), then calls `copyAdditiveVideo(deps, from, to, fromP, toP, present, body)`. But the helper contract needs to write the MD body to the receiver blob store and only says `to.<blob>.put(...)` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1950`). `to` is a `MetadataStore`, not a blob store (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1924-1927`; real `BlobStore.put` is separate in `lib/storage/blob-store.ts:7-13`). A literal implementation either does not compile or guesses receiver blob selection from `deps`, which is exactly where wrong-direction silent copies happen.

Specific fix: make the tuple and helper signature carry both blob stores explicitly:
`const [from, fromP, fromBlob, to, toP, toBlob] = presentIsLocal ? [deps.local, localP, deps.localBlob, deps.cloud, cloudP, deps.cloudBlob] : [deps.cloud, cloudP, deps.cloudBlob, deps.local, localP, deps.localBlob];`
Then call `copyAdditiveVideo(deps, from, to, fromP, toP, toBlob, present, body ?? '')`, and have the helper use `toBlob.put(toP, video.summaryMd, ...)`. Add an assertion in the additive hydrate/publish tests that the receiver blob store, not the sender, contains the copied MD.

### H2 - Task 12: unresolved backfilled Class-B conflicts can advance the manifest and become destructive next run

Failure scenario: a legacy/backfilled field differs on both sides: local `personalNote="L"` with backfilled timestamp, cloud `personalNote="C"` with a real timestamp, baseline `"base"`. T6 correctly returns `winner:'equal', conflict:true` for backfilled both-changed conflicts so no value is overwritten (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1007-1011`, `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1064-1068`), matching the spec's "conflict -> skip + log, never overwrite" rule (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:193-196`). But T12 still always calls `writeVideoBaseline(... buildBaseline(winnerSignals, winnerMdHash, merges))` after the video, even when a Class-B field was unresolved (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2028-2029`). `buildBaseline` receives only `mergedHuman`, not the old baseline or both live snapshots (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1958`), so an implementer will likely persist `merges.personalNote.value` as the new "agreed" baseline even though the replicas still differ. On the next sync, the side matching that advanced baseline is treated as unchanged and the other side as changed, causing the previously skipped conflict to overwrite data.

Specific fix: represent unresolved Class-B fields separately. Either do not advance the baseline for any video with `merge.conflict && merge.winner === 'equal'`, or change `buildBaseline` to take `previousBaseline`, local snapshot, cloud snapshot, and merge results, and preserve the previous baseline for unresolved fields. Add a two-run regression test: backfilled both-changed conflict logs/skips on run 1 and still logs/skips, without overwriting either side, on run 2.

## Medium

### M1 - Task 4: the file list still instructs the old `mdHash(sourceMd)` bug

Failure scenario: a worker follows the T4 file list before the detailed subsection. It says to modify `lib/html-doc/generate.ts:49-55` and "set `sourceMdHash: mdHash(sourceMd)`" (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:586-588`). In the real source, `sourceMd` / `video.summaryMd` is the key and `md` is the body (`lib/html-doc/generate.ts:29-36`, `lib/html-doc/generate.ts:49-55`). The detailed T4(c) section and test contradict this correctly, but the plan still contains a direct instruction for the round-2 N1 bug.

Specific fix: change the T4 file-list bullet to `sourceMdHash: mdHash(md)` or `mdHash(MD body)` and mention that `sourceMd` is only provenance/key material.

## Low

None.

## Verdict

NOT CONVERGED
