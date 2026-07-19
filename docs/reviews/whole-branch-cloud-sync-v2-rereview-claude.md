# Whole-branch re-review (ROUND 2, Claude adversarial) — `feat/stage3-cloud-sync`

Scope: shipped state at HEAD `32a164c`. Read-only review. Authoritative spec:
`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`.

Test baseline at HEAD: `npx jest tests/lib/cloud-sync tests/integration/cloud-sync` →
**15 suites / 85 tests passed**.

Known-and-accepted (not re-reported): T14-M1, T14-M2, T5 coverage gaps, T4 automock comment.

---

## Part A — verification of the round-1 fixes

### WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy
**Verdict: GENUINELY FIXED.**

Guard at `lib/cloud-sync/sync-run.ts:471-477`.

- **Precision of the trigger.** `merges.corrections.winner === 'equal' && merges.corrections.conflict`
  is reachable from exactly one place: `lib/cloud-sync/reconcile-class-b.ts:43-45`, which is guarded by
  `local.value !== cloud.value` (line 27 returns early on equal values, always with `conflict: false`).
  So the guard cannot false-fire on identical corrections. Correct.
- **Is the guard before every write path?** Yes. The `continue` at line 476 precedes `deriveClassASignals`
  (480-481), `reconcileClassA` (482), both `transferClassA` calls (493, 497) and `companionTransfer` (505).
  There is no other write surface between line 461 and the end of the loop body. `applyClassBWinners`
  (456) runs *before* the guard, which is correct and intentional — Class B is a separate class and a
  `winner === 'equal'` field is skipped inside `applyClassBWinners` at line 245 anyway.
- **Does `continue` skip anything that must still run?**
  - Delete-inference "seen" marking: preserved — `writeVideoBaseline` runs at line 475, so `manifest.videos[id]`
    exists next run and the video is not mis-inferred as a delete. ✅
  - Archived reporting: explicitly re-added at line 474 (mirrors line 508). ✅
  - Companion transfer: correctly skipped — no MD moved, so the loser's model is not stale. ✅
  - Report counters: `skippedIdentical` is not incremented. That is defensible (nothing was compared),
    and no consumer branches on it (`app/.../cloud-sync` CLI only prints). Not a defect.
- **Does the first-sync placeholder baseline mislead a consumer?** No. I grepped every reader of
  `VideoBaseline.classA`: the only references are the three *writers* in `sync-run.ts` (207-217, 370-375,
  391-392) and the type declaration at `lib/cloud-sync/types.ts:32`. `reconcileClassA`
  (`lib/cloud-sync/reconcile-class-a.ts:11-15`) takes only `{local, cloud, reconciledCorrectionsHash}` —
  no baseline parameter. `reconcileHuman` consumes only `base?.classB`. **The Class-A baseline is
  write-only.** The `docVersionMajor: 0 / mdHash: null` placeholder is therefore inert; next run
  re-derives from the live bodies. The code comment at 384-386 is accurate.
- **Idempotency:** second run re-derives the same conflict → same skip → same baseline. The e2e test at
  `tests/integration/cloud-sync/e2e.int.test.ts:392-437` asserts exactly this across two runs, including
  that both MD blobs and both `corrections` values are byte-preserved and `spendLedgerTotal` is unchanged.

### WB-H1 (High) — additive create could advertise `promoted` with no blob
**Verdict: GENUINELY FIXED** (with one Low on residual partial state, below).

`lib/cloud-sync/sync-run.ts:153-201`. Three layers, all real:
throw on `summaryMd && mdBody == null` (158-160); strip a residual `artifacts.summaryMd` when no blob was
written (178-183); post-write assert that the persisted row advertises `status === 'promoted'` at the
**right key** (196-201).

- **`summaryMd == null` path still correct.** `video.summaryMd` falsy → no throw, `wroteBlob` stays false →
  the `else if` strips any residual pointer → row lands with no summary artifact. Row 13 (summary-less
  video) behaves as specified.
- **Does the strict post-write assert behave differently across backends?** No — and this is the
  right shape for both. Local: `LocalFsMetadataStore.upsertVideo` → `indexStore.upsertVideo`, and
  `sanitized.artifacts` is a whole-object replace, so `artifacts.summaryMd` lands verbatim. Cloud:
  `upsertVideo` goes through `.update({ data: stripComputed(video) })`
  (`lib/storage/supabase/supabase-metadata-store.ts:109`) — a **whole-`data` replace**, not
  `merge_video_data`, so there is no deep-merge asymmetry on this path. The assert reads back via
  `readIndex` on both, so it verifies the *persisted* representation either way. ✅
- **Partial state after the throw** — see Part B L1. It is self-healing; not a High.

### WB-H2 (High) — two-sided transfer left stale rendered HTML
**Verdict: FIXED for `summaryHtml`/`digDeeperHtml`, but the fix OVERREACHES on `digDeeperMd` → see
Part B **H1** (new High).**

I traced whether a JSON `null` actually persists on each backend, as instructed:

- **Cloud.** `transferClassA` → `loser.store.updateVideoFields` →
  `supabase-metadata-store.ts:123-137` → `stripComputed(fields)`, which is a destructuring rest
  (`:18-21`) that removes only `updatedAt`/`summaryReady` — **it does not drop nulls**. PostgREST
  serializes the JSON null through. In `merge_video_data`
  (`supabase/migrations/0021_cloud_sync_signals.sql`), the first term is
  `data || (p_fields - 'artifacts')`. Postgres `jsonb ||` **sets the key to JSON null** rather than
  dropping it (`'{"a":1}'::jsonb || '{"a":null}'::jsonb` → `{"a": null}`). Only `jsonb_strip_nulls`
  drops nulls, and it is used in `persist_summary`, not here. **Null is stored.** ✅
- **Local.** `LocalFsMetadataStore.updateVideoFields` → `indexStore.updateVideoFields`
  (`lib/index-store.ts:132-146`), which does `{ ...index.videos[i], ...safeFields }` — a shallow spread,
  so `summaryHtml: null` overwrites — then `writeIndex` → `JSON.stringify`, which preserves `null`
  (only `undefined` is dropped). **Null is stored.** ✅
- **Consumers read it as falsy.** `lib/html-doc/eligibility.ts:12` (`!v.summaryHtml`) and
  `lib/html-doc/ensure.ts:54` (`else if (!video.summaryHtml)`) both branch on falsiness, so a JSON null
  forces a full re-render. The fix is **not** cosmetic. ✅
- **Comparison against `sanitizeAdditiveVideo`'s strip list** (`sync-run.ts:107-124`), as instructed:

  | field | `sanitizeAdditiveVideo` | `transferClassA` | assessment |
  |---|---|---|---|
  | `summaryHtml` | null | null (314) | ✅ match |
  | `digDeeperHtml` | null | null (315) | ✅ match |
  | `digDeeperMd` | null | null (316) | ❌ **wrong on this path** — Part B H1 |
  | `artifacts.*` except `summaryMd` | dropped (113-115) | **not cleared** (319) | see Part B M1 |
  | `serialNumber`/`playlistIndex`/`removedFromPlaylist` | deleted | not sent | ✅ correct (replica-local) |

  The commit comment "Matches `sanitizeAdditiveVideo`, which already nulls these" is the flawed premise:
  `sanitizeAdditiveVideo` shapes a record for a receiver that has **no row yet** (nothing to destroy),
  while `transferClassA` patches a receiver row that **already holds its own state**. The two are not
  interchangeable, and `digDeeperMd` is where that difference bites.

---

## Part B — new findings

### H1 (High) — `transferClassA` nulls `digDeeperMd`, orphaning the loser's paid dig-deeper doc
**`lib/cloud-sync/sync-run.ts:316`**

`digDeeperMd` is not a regenerable render cache — on the local backend it is the **filename pointer to a
Gemini-generated dig-deeper markdown file**, written by `lib/dig/dig-section.ts:104-106`, produced by
`lib/dig/generate.ts` against `gemini-2.5-pro` (`generate.ts:23`, and note `:115` — "Local dig (no opts)
stays on gemini-2.5-pro"). It is **paid content**. `summaryHtml` and `digDeeperHtml` are free re-renders;
`digDeeperMd` is not.

**Scenario (concrete):**
1. A user digs several sections locally → `index.json` has `digDeeperMd: "foo-dig-deeper.md"` and the file
   exists on disk.
2. The same video is regenerated in the cloud at a higher `docVersion.major` (an ordinary, expected event).
3. `reconcileClassA` (`reconcile-class-a.ts:43-46`, format axis, "never downgrade") returns `copyToLocal`.
4. `transferClassA(cloudSide, localSide, …)` sends `digDeeperMd: null` in `completeTuple` (316) →
   `indexStore.updateVideoFields` shallow-spread → `index.json` now has `digDeeperMd: null`.

**Wrong outcome:** every consumer of the local dig doc goes dark while the file sits orphaned on disk —
`app/api/videos/[id]/dig-state/route.ts:92-93` returns "no dig", `components/VideoMenu.tsx:174`
(`!cloudMode && video.digDeeperMd`) hides the menu entry, `lib/html-doc/build-doc-html.ts:75,86` stops
merging it, `lib/pdf/pdf-path.ts:19` throws `no dig-deeper doc for this video`. To recover, the user must
re-dig → **fresh Gemini spend for content they already paid for**. Recovery is not automatic: nothing in
the sync path ever re-derives `digDeeperMd` from the filesystem.

This also violates scope: the spec puts dig **out of scope for M2a** (`§ line 35`, "Out of scope (M2a):
deep-dive/dig + slide images (M2b, §13)"). Sync must leave dig state untouched, not destroy it.

Note this is a **regression introduced by the WB-H2 fix** — before `32a164c` the field was not sent at all.

**Fix:** delete the `digDeeperMd: null` line (316). Keep `summaryHtml: null` and `digDeeperHtml: null` —
those are correct: `digDeeperHtml` is the *rendered merge* of summary + dig, so a summary-body change does
stale it, and `lib/html-doc/eligibility.ts:23` (`!!v.summaryMd && !v.digDeeperMd`) plus
`build-doc-html.ts:86` re-render it for free **from the preserved `digDeeperMd`**. Add a regression test —
there is currently zero coverage: `grep -rn digDeeperMd tests/lib/cloud-sync tests/integration/cloud-sync`
returns nothing.

### M1 (Medium) — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
**`lib/cloud-sync/sync-run.ts:319`**

`merge_video_data` deep-merges `artifacts` by design
(`0021_cloud_sync_signals.sql`: `coalesce(data->'artifacts','{}') || (p_fields->'artifacts')`), so sending
`artifacts: { summaryMd: … }` **preserves** every other key already on the loser row. Any non-`summaryMd`
artifact the loser holds (written via `lib/storage/supabase/consistency.ts:34,40`, whose `opts.kind` is
generic) survives a transfer that replaced the MD body it was derived from.
`sanitizeAdditiveVideo:113-115` drops exactly these; `transferClassA` does not.

Today the practical blast radius is small — the artifacts map is dominated by `summaryMd`, and the
regenerable HTML is gated on the top-level `summaryHtml`, which *is* nulled. Hence Medium, not High. But
the asymmetry with `sanitizeAdditiveVideo` is unintentional and will become a real staleness bug as soon
as a second artifact kind (pdf/slide/modelJson) is populated on the cloud path. Either clear the
non-`summaryMd` keys explicitly or record the divergence as a deliberate, documented decision.

### M2 (Medium) — the WB-B1 guard also blocks purely-additive (non-destructive) MD hydration
**`lib/cloud-sync/sync-run.ts:471-477`**

The guard skips Class A **unconditionally**, including the sub-case where the loser has no MD at all.

**Scenario:** cloud row has `summaryMd` + a promoted blob; the local row exists (so this is the two-sided
path, not the additive path) but has `summaryMd == null`; both sides carry a *backfilled* corrections
conflict (legacy records, per §5.5). Pre-fix, `reconcileClassA:22` (`if (!lHas) return copyToLocal`) would
hydrate local. Post-fix the video is skipped every run, forever, until a human edits corrections on one
side to produce a real `annotationsEditedAt`.

Nothing is destroyed and `needsRegen` is reported each run, so this is safe-but-stuck rather than a
correctness bug — Medium. Consider narrowing the guard to the genuinely destructive case (both sides have
an MD body, i.e. `la.mdHash != null && ca.mdHash != null`), which preserves the WB-B1 fix's intent exactly
while letting one-sided hydration through.

### L1 (Low) — the WB-H1 throw leaves a bare receiver slot; converges, but via a different code path
**`lib/cloud-sync/sync-run.ts:150` then `158-160`**

`ensureReceiverSlot` runs (150) *before* the new throw (158), so `claimVideoSlot` has already inserted a
minimal row (`local-metadata-store.ts:27`: `{ id: videoId, serialNumber } as Video`). The throw is caught
at 513-515, no baseline is written.

I traced the next run and it **does not corrupt anything**: both sides now read as present, so the video
takes the two-sided path; `deriveClassASignals` on the bare row yields `mdHash: null`, so
`reconcile-class-a.ts:22` returns `copyToLocal`, and `transferClassA:273-275` throws again
(`winner … has no MD body to copy`) while the cloud blob is still unreadable — then heals cleanly once it
is. No zod validation runs on `readIndex` (`lib/index-store.ts:81-98` is a bare `JSON.parse`), so the bare
row does not poison the index read. Delete-inference is safe (both sides present, no baseline).

Residual cosmetic effects only: `report.created` is never incremented for this video (it heals via the
two-sided path), and a permanently-missing cloud blob produces one `report.errors` entry per run — which
is the desired surfacing. Worth a comment at 158 noting the deliberate slot-then-throw ordering.

---

## Items explicitly checked and found clean

- **Money-safety.** No `enqueue`/producer import, no `spend_ledger` touch, no reserve/release anywhere in
  `lib/cloud-sync/*`. `needsRegen` is written only to `report.needsRegen` (483, 473) and never read as a
  trigger. The WB-B1 e2e test asserts `spendLedgerTotal()` is unchanged across the run.
  *(H1 above is a money finding of a different kind — it forces the user to re-spend, rather than the sync
  spending itself.)*
- **Baseline-advance across all four branches.** additive (444-447, after the row-existence + promoted
  asserts), transfer (512, after `transferClassA` resolves), skip (512, N4), corrections-unresolved (475).
  Every advance is preceded by a durable write or a verified no-op. No branch advances a baseline for an
  unwritten change, and every "seen" video gets a baseline, so no spurious delete inference.
- **Durable-before-advertise.** `transferClassA:279-292` stages → verifies the hash → `put`s the verified
  bytes at the final key (with the documented rationale for `put` over `promote`, given
  `SupabaseBlobStore.promote` is create-if-absent) → only then `updateVideoFields` advertises `promoted`.
  Manifest strictly after. Unchanged and still correct.
- **Cross-backend semantics.** Checked the three write paths that differ (`upsertVideo` = whole-`data`
  replace on cloud vs object replace on local; `updateVideoFields` = `merge_video_data` deep-merge on
  cloud vs shallow spread on local; null persistence on both). The only surviving mismatch is M1 above.
- **RLS / no service-role.** `SyncDeps` exposes no raw client; `cloudP.id = deps.ownerId` (419);
  `merge_video_data` and `update_video_annotations` are `security invoker` with `auth.uid()` guards.
  Unchanged by `32a164c`.
- **Idempotency.** Ran each new branch twice mentally; WB-B1 is additionally covered by an explicit
  two-run assertion in the e2e test. No oscillation, no sticky false agreement.

---

**NOT CONVERGED** — 1 new High (H1: `digDeeperMd: null` destroys the local loser's paid dig-deeper doc, a
regression introduced by the WB-H2 fix), plus 2 Mediums and 1 Low. Another round is required after H1 is
fixed.

---

## Coordinator adjudication (post-review, 2026-07-18)

The two round-2 reviewers DISAGREED on the severity of the additive slot-ordering defect:
Codex rated it **High**; this review rated it **L1 (Low)**. I adjudicated against the code.

**Codex is correct; L1 above is WRONG and is superseded.**

L1 reasons that on run 2 the video takes `reconcile-class-a.ts:22` (`if (!lHas) return copyToLocal`)
and throws again in `transferClassA`. That requires `cHas === true`. It is not: `deriveClassASignals`
derives `mdHash` from the **MD body**, not the key —
`lib/cloud-sync/backfill.ts:11`: `mdHash: mdBody != null ? mdHash(mdBody) : null`.
The premise of the scenario is that the cloud blob is UNREADABLE, so `readMdBody` returns null and the
cloud side hashes to `null` as well. Both sides null → `reconcile-class-a.ts:21`
(`if (!lHas && !cHas) return { action: 'skip' }`) → `runSync` WRITES a manifest baseline (~:512).

Net effect: the corruption is surfaced in `report.errors` exactly once, then laundered into a false
"seen and agreed no-MD" baseline — the video is thereafter treated as reconciled. That is a
**High**, tracked as **H-R2-1**, and is being fixed by validating the MD body BEFORE
`ensureReceiverSlot` claims the slot (no partial state → nothing to roll back).

Lesson for round 3: the single-run WB-H1 e2e test passed while this bug was live. Assertions about
baseline/idempotency effects require running `runSync` TWICE — as the WB-B1 test already does.
