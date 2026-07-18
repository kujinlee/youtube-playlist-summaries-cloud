Reading prompt from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019f7626-e7b7-70a1-9915-5531b29c5032
--------
user
You are an adversarial WHOLE-BRANCH RE-REVIEWER (ROUND 6) for Stage 3 Cloud Sync (M2a), branch `feat/stage3-cloud-sync`. HEAD is `12c850d`.

Trail: R1 `32a164c` (1 Blocking + 2 High) → R2 `1f54c60` (2 High, one a regression from R1's fix) → R3 `3bc8cc7` (1 Blocking) → R4 `66fe6e5` (3 High, one a regression from R3's fix) → R5 `12c850d` (1 High — found by BOTH reviewers independently — plus dead-code removal and a Low). Reviews: `docs/reviews/whole-branch-cloud-sync{,-v2,-v3,-v4,-v5}-rereview-{codex,claude}.md`.

Read `git show 12c850d` first.

**Calibration — read this carefully.** Five rounds have landed real fixes. The severity trend is now decreasing and R5's single High was found independently by both reviewers, which suggests the surface is nearly exhausted. Two failure modes are equally bad here:
- Declaring CONVERGED while a real defect is live. R3 and R4 both had a reviewer do exactly that.
- Manufacturing a marginal finding to look diligent. That costs a real fix cycle, and in this branch every fix round has had roughly a one-in-two chance of introducing a new defect.
If you find nothing, say so plainly and stop. A clean round is the expected terminal state of this loop.

## Part A — verify the round-5 fixes
R5 restructured `decideCompanion` (`lib/cloud-sync/companion.ts`) to take BOTH sides as `ModelRead` tri-states:
1. sender envelope matching `winnerMdHash` → ship
2. else receiver envelope matching `winnerMdHash` → noop, `shareNeedsOwnerServe: false`
3. else delete ONLY when the receiver envelope has a `sourceMdHash` that is present (provably stale); everything else (absent / legacy no-hash / unprovable read) → noop with `shareNeedsOwnerServe: true`

VERIFY:
- Is the matrix exhaustive and correct for every (sender × receiver) combination? Walk all 9. Is there a combination where it ships or deletes something it should not, or keeps something that is provably wrong?
- `provablyStale` is `receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash !== undefined` — note this deletes whenever the receiver has ANY sourceMdHash, having already excluded the matching case at step 2. Confirm that is right, and that a receiver envelope whose `sourceMdHash` matches but whose `sourceSections`/`generatorVersion` are stale is handled sanely by the serve path.
- Does `readReceiverModel` (or however sync-run reads the receiver side) correctly map the receiver's null through `provesAbsence`? A receiver read that is unprovable must NOT delete.
- `shareNeedsOwnerServe` is now carried on `noop`. Confirm it preserves the pre-existing row-7 contract (`tests/integration/cloud-sync/e2e.int.test.ts:236`) and does not now OVER-report — trace how often `noop + true` fires in ordinary syncs (e.g. every video where neither side has a model) and say whether the counter remains meaningful to a user.
- H3 layer 3 was REMOVED and `ensureReceiverSlot` restored to `setPlaylistMeta`-then-`readIndex`. Confirm that ordering is correct on BOTH backends (on local, does `setPlaylistMeta` create the index file that `readIndex` then reads? is the row-exists check still authoritative?).
- L-R5-2: `playlistMetaFor` now prefers the CLOUD title. Confirm no case where that loses a legitimately newer local title.

## Part B — new defects
Re-verify on the shipped state, and hunt for anything the R5 restructure introduced or exposed:
- Baseline-advance correctness on every branch; no advance without a durable write; every "seen" video gets one.
- Money-safety: no enqueue, no `spend_ledger`, no regenerable-cache resurrection; `needsRegen` report-only; and any path that forces the USER to re-spend counts as a money finding (that is what H1 and H-R5-1 both were).
- Atomicity: durable-before-advertise, manifest-after-commit.
- Idempotency reasoned across TWO runs on every branch.
- Cross-backend local-vs-Supabase semantic mismatches.
- RLS / no-service-role unchanged.
- Any remaining "a value meaning absent is also what a failure produces" instance NOT already deferred. Note `readManifest` (`lib/cloud-sync/manifest.ts`) is DEFERRED by decision — spec §8 specifies degrade-on-corrupt and the direction is safe. Do not re-file it.

## Known / deferred — do NOT re-report unless you prove one masks a real bug
T14-M1, T14-M2, T5 coverage gaps, T4 automock comment; Claude-R2-M1 (stale non-`summaryMd` artifact pointers); Codex-R2-Medium (absent companion scalars); Claude-R3-M1 (`build-doc-html` base from `digDeeperMd`); L-R5-3 (`readManifest` degrade-on-corrupt). Do NOT report `tests/integration/reservation-release.test.ts` — pre-existing on a clean tree.

Minor known nit, already logged, no need to re-file: a comment in `companion.ts`/`sync-run.ts` cites "§10 row 7" as if it were in the design spec; the numbered row 7 actually lives in the PLAN (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2213`) and its wording is about a deleted model, while the implemented+tested contract is "no matching model".

## Scope
SHIPPED state at HEAD. `lib/cloud-sync/*.ts`, `lib/storage/**`, `supabase/migrations/0021_*` + `0009_*`, `lib/html-doc/*`, `lib/dig/*`, tests under `tests/lib/cloud-sync/` and `tests/integration/cloud-sync/`. Spec: `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`. Plan: `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md`.

## Output
Per finding: severity, `file:line`, concrete input→wrong-outcome scenario, fix. Part A: GENUINELY FIXED / INCOMPLETE / NOT FIXED per item with evidence. End with **CONVERGED** or **NOT CONVERGED**.

codex
I’ll start by reading the shipped diff at `12c850d`, then trace the companion decision paths and sync-run call sites before looking for fresh branch-level defects.
exec
/bin/bash -lc 'git show --stat --oneline --decorate --no-renames 12c850d && git show --no-ext-diff --unified=80 --no-renames 12c850d -- lib/cloud-sync/companion.ts lib/cloud-sync/sync-run.ts tests/lib/cloud-sync/companion.test.ts tests/integration/cloud-sync/e2e.int.test.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
12c850d (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-5 whole-branch re-review — key the companion decision to the RECEIVER, drop dead layer, cloud title precedence (H-R5-1/L-R5-2)
 .../whole-branch-cloud-sync-v5-rereview-claude.md  |   241 +
 .../whole-branch-cloud-sync-v5-rereview-codex.md   | 14637 +++++++++++++++++++
 lib/cloud-sync/companion.ts                        |    92 +-
 lib/cloud-sync/manifest.ts                         |    11 +-
 lib/cloud-sync/sync-run.ts                         |    77 +-
 tests/integration/cloud-sync/e2e.int.test.ts       |   172 +-
 tests/integration/helpers/cloud.ts                 |     4 +
 tests/lib/cloud-sync/companion.test.ts             |   101 +-
 8 files changed, 15248 insertions(+), 87 deletions(-)
commit 12c850d34dd8488184ba16233676250bc412d50c
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Sat Jul 18 09:53:04 2026 -0700

    fix(cloud-sync): round-5 whole-branch re-review — key the companion decision to the RECEIVER, drop dead layer, cloud title precedence (H-R5-1/L-R5-2)
    
    Round-5 dual re-review of 66fe6e5. BOTH reviewers independently found the same High — the
    first time they have agreed, after R3/R4 where one cleared a path the other found broken.
    
    H-R5-1 (High) — round 4 made the SENDER model read honest (provesAbsence tri-state) but left
    the whole decision keyed to it, which was wrong in both directions:
      (a) `unknown` → noop KEPT a provably-stale receiver model, and the claimed safety net does
          not exist: isFresh (lib/html-doc/read-model.ts) compares section TITLES and
          generatorVersion, never sourceMdHash, so a prose-only MD change — exactly the
          recency-tiebreak case — is served as fresh indefinitely. `unknown` is also the COMMON
          outcome, since a cloud video never HTML-served has no model blob and Supabase cannot
          prove that 404.
      (b) `none` → delete DESTROYED receiver models that were still valid, because the receiver
          was never consulted.
    The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
    independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT
    is definitively stale, no ambiguity involved. decideCompanion now takes both sides as
    tri-states: ship a matching sender envelope; keep a receiver model that matches the winner;
    delete only on PROOF of staleness; keep legacy (no sourceMdHash) and unprovable reads. Money
    rule: a possibly-stale cache is recoverable, a deleted paid artifact is not.
    
    shareNeedsOwnerServe is now carried on `noop` too — it is a separate axis from the blob
    action, and conflating the two is what produced this finding. The report flag preserves the
    pre-existing row-7 contract (e2e.int.test.ts:236, "no matching model flags
    shareNeedsOwnerServe"); under-reporting is the harmful direction since the flag spends nothing.
    
    H3 layer 3 REMOVED as dead code, not as cleanup: both reviewers independently failed to
    construct an input reaching it, and my mutation test (deleting it) failed ZERO tests. Layers 1
    and 2 are what actually fix H3 and they are covered. A comment records why, so it is not
    re-added — dead defense-in-depth reads as load-bearing and hides which layer holds.
    
    L-R5-2 (Low) — playlistMetaFor now prefers the CLOUD title. Titles have no LWW timestamp, so
    this is fixed precedence: the cloud row is maintained by ingest and backfill-titles (both from
    the live YouTube API), whereas a local index title is whatever was captured when that folder
    was last summarized. Preferring local let a stale title overwrite a fresher one.
    
    L-R5-3 (readManifest swallows unreadable as absent → can resurrect a deleted video) is
    DEFERRED with a comment naming spec §8: degrade-on-corrupt is specified and the direction is
    the safe one. Recorded so the next reviewer does not re-file it.
    
    Verification: tsc clean; 2445 unit / 245 suites; cloud-sync integration 44/44 (4 suites).
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01EfbFViKSSM27WJ5dSchemY

diff --git a/lib/cloud-sync/companion.ts b/lib/cloud-sync/companion.ts
index 17d7022..87d5fb1 100644
--- a/lib/cloud-sync/companion.ts
+++ b/lib/cloud-sync/companion.ts
@@ -1,39 +1,93 @@
 import type { ModelEnvelope } from '@/lib/html-doc/model-store';
 
-/** H1 (round 4) — the result of reading the SENDER's model, as a TRI-state.
+/** H1 (round 4) — the result of reading ONE side's model, as a TRI-state.
  *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
- *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean the sender has
- *  nothing shippable (the receiver's model is now stale and should go); the third means we simply
- *  do not know, and acting on it destroys a paid artifact. Which of those a null is depends on the
- *  backend — see BlobStore.provesAbsence — so the caller resolves it and hands the answer here. */
-export type SenderModelRead =
+ *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean that side has
+ *  nothing usable; the third means we simply do not know, and acting on it destroys a paid artifact.
+ *  Which of those a null is depends on the backend — see BlobStore.provesAbsence — so the caller
+ *  resolves it and hands the answer here.
+ *
+ *  H-R5-1 (round 5) — this is now read for BOTH sides, hence the neutral name. */
+export type ModelRead =
   | { kind: 'envelope'; envelope: ModelEnvelope }
-  | { kind: 'none' }      // the sender PROVABLY has no usable model
+  | { kind: 'none' }      // that side PROVABLY has no usable model
   | { kind: 'unknown' };  // the read failed in a way that cannot prove absence
 
+/** @deprecated round-4 name, kept so the tri-state reads naturally at the sender call site. */
+export type SenderModelRead = ModelRead;
+
+/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
+ *  axis from the blob action and conflating the two is what produced this finding. The action answers
+ *  "what do we do to the receiver's blob?"; the flag is a report-only count of shares that cannot
+ *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
+ *  there is nothing to delete and yet the share IS unready — noop + true. */
 export type CompanionAction =
   | { kind: 'ship'; envelope: ModelEnvelope }
   | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
-  | { kind: 'noop' };
+  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
 
-/** Ship the sender's model iff it was generated from the winning MD (§4.2).
+/** Ship the sender's model iff it was generated from the winning MD (§4.2); otherwise decide the
+ *  receiver's fate from the RECEIVER's own envelope.
  *
- *  H1 (round 4) — `unknown` is a NO-OP, not a delete. Deleting the receiver's model costs a paid
- *  Gemini magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
+ *  H1 (round 4) — `unknown` must not delete. Deleting the receiver's model costs a paid Gemini
+ *  magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
  *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
  *  silent and sticky: it does not throw, so the caller advances the manifest baseline, and the next
- *  run's Class-A reconcile returns 'skip' and never revisits the companion step. Keeping a possibly
- *  stale receiver model is the cheap side of that trade — a model is only ever a cache, and the
- *  serve path's sourceSections drift guard (lib/html-doc/read-model.ts) rejects a mismatched one
- *  for free. */
+ *  run's Class-A reconcile returns 'skip' and never revisits the companion step.
+ *
+ *  H-R5-1 (round 5) — round 4 made the SENDER read honest but left the whole decision keyed to it,
+ *  which was wrong in both directions:
+ *   (a) `unknown` → noop KEPT a provably-stale receiver model. The claimed safety net does not
+ *       exist: the serve path's drift guard (lib/html-doc/read-model.ts) compares section TITLES and
+ *       generatorVersion, never sourceMdHash, so a prose-only MD change — precisely the
+ *       recency-tiebreak case — is served as fresh forever (dig-deeper merges the cached envelope
+ *       without regenerating). And `unknown` is the COMMON outcome: a cloud video that was never
+ *       HTML-served has no model blob, and the Supabase backend cannot prove that 404.
+ *   (b) `none` → delete DESTROYED receiver models that were still valid, since the receiver was
+ *       never consulted.
+ *  The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
+ *  independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT is
+ *  definitively stale — its backing body no longer exists — with no ambiguity involved. So the
+ *  sender read now decides only whether a REPLACEMENT can be shipped, and everything else is keyed
+ *  to the receiver. Deleting a provably-stale model is not a money loss; deleting a matching one is.
+ */
 export function decideCompanion(args: {
   winnerMdHash: string;
-  senderModel: SenderModelRead;
+  senderModel: ModelRead;
+  receiverModel: ModelRead;
 }): CompanionAction {
-  const { winnerMdHash, senderModel } = args;
-  if (senderModel.kind === 'unknown') return { kind: 'noop' };
+  const { winnerMdHash, senderModel, receiverModel } = args;
+
+  // 1. The sender holds a model built from the winning MD → ship it (it supersedes whatever the
+  //    receiver has, so the receiver's own state does not matter here).
   if (senderModel.kind === 'envelope' && senderModel.envelope.sourceMdHash === winnerMdHash) {
     return { kind: 'ship', envelope: senderModel.envelope };
   }
-  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
+
+  // 2. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
+  //    still valid. Do not destroy a paid artifact, and the share renders, so report nothing.
+  if (receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash === winnerMdHash) {
+    return { kind: 'noop', shareNeedsOwnerServe: false };
+  }
+
+  // 3. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
+  //
+  //  - DELETE the blob only on PROOF. A receiver envelope whose sourceMdHash is present and differs
+  //    is definitively stale — its backing body no longer exists — and needs no sender read to
+  //    establish. Everything else is unprovable: `none`/`unknown` say nothing about a model we never
+  //    read, and a legacy pre-1F-a envelope predates sourceMdHash entirely (the field is .optional()
+  //    in model-store.ts), so it cannot be checked. Fail-safe-for-money: KEEP those. A possibly-stale
+  //    cache is recoverable — any regeneration overwrites it, and the existing sourceSections /
+  //    generatorVersion drift guard still catches the common legacy drift — but a deleted paid
+  //    artifact costs a Gemini transform to rebuild.
+  //
+  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
+  //    not render until you re-serve." It spends nothing and destroys nothing, so the harmful
+  //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
+  //    receiver of a copyToCloud is always the Supabase store, which can never return `none`, so
+  //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
+  const provablyStale = receiverModel.kind === 'envelope'
+    && receiverModel.envelope.sourceMdHash !== undefined;
+  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
+  return { kind: 'noop', shareNeedsOwnerServe: true };
 }
diff --git a/lib/cloud-sync/sync-run.ts b/lib/cloud-sync/sync-run.ts
index 3713981..c400a19 100644
--- a/lib/cloud-sync/sync-run.ts
+++ b/lib/cloud-sync/sync-run.ts
@@ -1,237 +1,252 @@
 // lib/cloud-sync/sync-run.ts
 //
 // Stage 3 Cloud Sync (§7) — the sync-run orchestrator. Composes the reconcile primitives (T1/T5–T9,
 // T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
 // cloud, one playlist at a time, under an authenticated USER session (never service-role).
 //
 // Invariants (any violation = money/data bug):
 //  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
 //    cache (summaryHtml/dig/PDF) copied.
 //  - Cloud Principal.id = deps.ownerId (= auth.uid()): Supabase Storage RLS (0007) requires the
 //    first object-path segment to equal auth.uid(); the metadata RPCs are owner_id = auth.uid()
 //    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
 //  - Transfers finalize the receiver record via updateVideoFields (SyncDeps exposes no raw client,
 //    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
 //    tuple is verified durable — stage → verify → promote → finalize → verify → baseline (F2).
 //  - Class B is reconciled BEFORE Class A (Class A consumes the reconciled corrections hash);
 //    a Class-B loser write is asserted to have landed (found:true) or it throws (F3).
 
 import { promises as fs } from 'fs';
 import path from 'path';
 import type { MetadataStore } from '@/lib/storage/metadata-store';
 import type { BlobStore } from '@/lib/storage/blob-store';
 import type { Principal } from '@/lib/storage/principal';
 import { localPrincipal } from '@/lib/storage/principal';
 import type { Video } from '@/types';
 import { deriveClassASignals, deriveHumanSnapshot } from './backfill';
 import { reconcileHuman, type FieldMerge } from './reconcile-class-b';
 import { reconcileClassA } from './reconcile-class-a';
-import { decideCompanion, type SenderModelRead } from './companion';
+import { decideCompanion, type ModelRead } from './companion';
 import {
   readManifest, writeVideoBaseline, appendConflict, resetConflictDedup,
 } from './manifest';
 import { discoverLocalPlaylists, unionPlaylistKeys, type LocalPlaylist } from './registry';
 import { mdHash } from './content-hash';
 import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
 import type { PlaylistSummary } from '@/lib/storage/metadata-store';
 import type { ClassASignals, HumanField, HumanSnapshot, VideoBaseline } from './types';
 
 export interface SyncDeps {
   local: MetadataStore; cloud: MetadataStore;
   localBlob: BlobStore; cloudBlob: BlobStore;
   dataRoots: string[]; ownerId: string;
 }
 
 export interface SyncReport {
   created: number; updatedLocal: number; updatedCloud: number; skippedIdentical: number;
   mergedFields: number; conflictsLogged: number; removed: number;
   shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
   errors: { videoId: string; message: string }[];
 }
 
 const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
 const EMPTY_CLASSB = {} as VideoBaseline['classB'];
 
 /** One replica's write surface for a video (store + its principal + its blob store). */
 interface Side { store: MetadataStore; p: Principal; blob: BlobStore; }
 
 /** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
 async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
   if (!video.summaryMd) return null;
   const buf = await blob.get(p, video.summaryMd);
   return buf ? buf.toString('utf8') : null;
 }
 
 /** Union of video ids across both replicas' indexes. */
 async function enumerateVideoIds(
   local: MetadataStore, cloud: MetadataStore, localP: Principal, cloudP: Principal,
 ): Promise<string[]> {
   const [l, c] = await Promise.all([local.readIndex(localP), cloud.readIndex(cloudP)]);
   return [...new Set([...l.videos.map((v) => v.id), ...c.videos.map((v) => v.id)])];
 }
 
 /** Read one video record (or null if absent) from a store's index. */
 async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
   const idx = await store.readIndex(p);
   return idx.videos.find((v) => v.id === id) ?? null;
 }
 
 /** Deterministic local root for a cloud-only playlist (fresh-device hydrate target). */
 function hydrationRoot(dataRoots: string[], key: string): string {
   return path.join(dataRoots[0], key);
 }
 
 /** mkdir -p the playlist's local root BEFORE any local read/write (round-5 H1). On a fresh device a
  *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
  *  the empty-index sentinel only when the dir exists but the file is absent), and setPlaylistMeta/
  *  writeIndex ENOENT into a missing parent. */
 async function ensureHydrationRoot(dataRoot: string): Promise<void> {
   await fs.mkdir(dataRoot, { recursive: true });
 }
 
 /** Resolve the playlist url/title for `key` from whichever registry holds it.
  *
  *  H3 (round 4) — this MERGES the two registries rather than returning the first hit. It used to
  *  return the local entry's `{ playlistUrl }` alone whenever the playlist existed locally, and
  *  LocalPlaylist carried no title at all, so the cloud branch that does carry one was unreachable
  *  for every playlist present in both replicas. ensureReceiverSlot then handed that title-less meta
  *  to setPlaylistMeta, whose Supabase impl upserts `playlist_title: meta.playlistTitle ?? null` —
  *  wiping the cloud row's title on every sync carrying any local-only video. URL still prefers the
- *  local entry (it is the replica whose folder we are actually syncing); the title falls back to
- *  the other side so a replica that has one always supplies it. */
+ *  local entry (it is the replica whose folder we are actually syncing).
+ *
+ *  L-R5-2 (round 5) — the TITLE prefers the CLOUD entry. Titles have no LWW timestamp, so this is a
+ *  fixed precedence, not a merge; the cloud row is the one the ingest and backfill-titles paths
+ *  maintain (both write it from the live YouTube API), whereas a local playlist-index.json title is
+ *  whatever was captured when that folder was last summarized and can be arbitrarily old. Preferring
+ *  local meant a stale local title overwrote a fresher cloud one on every additive local→cloud
+ *  create. Each side still falls back to the other, so a replica that has the only title supplies
+ *  it — a sync can fill a title or refresh it from the cloud, never clear it. */
 function playlistMetaFor(
   key: string, localPlaylists: LocalPlaylist[], cloudSummaries: PlaylistSummary[],
 ): { playlistUrl: string; playlistTitle?: string } {
   const lp = localPlaylists.find((l) => l.playlistKey === key);
   const cp = cloudSummaries.find((c) => c.playlistKey === key);
   const playlistUrl = lp?.playlistUrl ?? cp?.playlistUrl ?? '';
-  const playlistTitle = lp?.playlistTitle ?? cp?.playlistTitle ?? undefined;
+  const playlistTitle = cp?.playlistTitle ?? lp?.playlistTitle ?? undefined;
   return { playlistUrl, ...(playlistTitle ? { playlistTitle } : {}) };
 }
 
 /** Behavior #3 (money-safe) — strip regenerable cache + out-of-scope pointers so the receiver never
  *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
  *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
  *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
 function sanitizeAdditiveVideo(video: Video): Video {
   const v: any = { ...video };
   v.summaryHtml = null;
   v.digDeeperHtml = null;
   v.digDeeperMd = null;
   // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
   if (v.artifacts && typeof v.artifacts === 'object') {
     v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
   }
   // Replica-local ordering is NOT synced (§4.1) — the receiver's claim supplies its own.
   delete v.serialNumber;
   delete v.playlistIndex;
   delete v.removedFromPlaylist;
   // DB-computed read-only fields must never round-trip into a write.
   delete v.updatedAt;
   delete v.summaryReady;
   return v as Video;
 }
 
 /** round-4 H1 — create the receiver playlist + reservation row BEFORE any receiver write. The cloud
  *  upsertVideo/updateVideoFields are bare UPDATEs of a row pre-created by claimVideoSlot: they
  *  silently affect 0 rows (no throw) on an absent row, so an additive create must claim the slot
  *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
  *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
 async function ensureReceiverSlot(
   to: MetadataStore, toP: Principal,
   playlistMeta: { playlistUrl: string; playlistTitle?: string }, video: Video,
 ): Promise<{ position: number; serialNumber: number } | null> {
-  // H3 (round 4) — read BEFORE the write, and carry the receiver's OWN title forward when the meta
-  // supplies none, so a sync can only ever FILL a title, never clear one. The upsert always writes
+  // H3 (round 4) — a sync must never CLEAR the receiver's playlist title. The upsert always writes
   // the playlist_title column (`meta.playlistTitle ?? null`), so simply omitting the title here
-  // would still NULL it — the never-clobber primitive setPlaylistTitleIfNull cannot undo that,
-  // because on this path there is no title left to restore it from. readIndex is safe before the
-  // row exists (both impls return the empty-index sentinel for an absent playlist), and
-  // setPlaylistMeta only touches the playlists row, so this same snapshot is still authoritative
-  // for the video-exists check below — no second round trip.
-  const idx = await to.readIndex(toP);
-  const playlistTitle = playlistMeta.playlistTitle ?? idx.playlistTitle;
+  // would NULL it, and the never-clobber primitive setPlaylistTitleIfNull cannot undo that.
+  // The fix lives in the two layers that feed this call: LocalPlaylist now carries playlistTitle
+  // (registry.ts), and playlistMetaFor MERGES both registries instead of returning the first hit —
+  // so whenever either replica knows the title, `playlistMeta.playlistTitle` carries it here.
+  //
+  // Round 5 — a third layer used to sit here: readIndex BEFORE the write, then
+  // `playlistMeta.playlistTitle ?? idx.playlistTitle` to carry the receiver's own title forward.
+  // It was REMOVED as unreachable, not as cleanup: both reviewers independently failed to construct
+  // an input where playlistMetaFor yields no title but the receiver row has one (zero-video cloud
+  // playlists still appear in listPlaylists with their title; local playlists are discovered from
+  // playlist-index.json, the same file readIndex reads; opts.playlistKey is filtered through the
+  // union), and deleting it failed ZERO tests under mutation. Do not re-add it without an input
+  // that reaches it — dead defense-in-depth reads as load-bearing and hides which layer actually
+  // holds. setPlaylistMeta runs first again: it only touches the playlists row (never the video
+  // set), and on the local backend it creates the index file that readIndex then reads.
   await to.setPlaylistMeta(toP, {
     playlistUrl: playlistMeta.playlistUrl,
-    ...(playlistTitle ? { playlistTitle } : {}),
+    ...(playlistMeta.playlistTitle ? { playlistTitle: playlistMeta.playlistTitle } : {}),
   });
+  const idx = await to.readIndex(toP);
   if (idx.videos.some((v) => v.id === video.id)) return null;
   return to.claimVideoSlot(toP, video.id);
 }
 
 /** Behavior #3 (money-safe) — additive create of a one-sided video onto the receiver. Order:
  *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
  *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
  *  never copies regenerable cache. */
 async function copyAdditiveVideo(
   to: MetadataStore, toP: Principal, toBlob: BlobStore,
   playlistMeta: { playlistUrl: string; playlistTitle?: string },
   video: Video, mdBody: string | null,
 ): Promise<void> {
   // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
   // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
   // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
   // strand the receiver with a servable-looking row backed by nothing.
   // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
   // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
   // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
   // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
   // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
   // partial state is ever created, so there is nothing to roll back.
   if (video.summaryMd && mdBody == null) {
     throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
   }
 
   const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
 
   let wroteBlob = false;
   if (video.summaryMd && mdBody != null) {
     // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
     const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
     const staged = await toBlob.get(toP, ref.tempKey);
     if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
       throw new Error(`additive staged MD verify failed for ${video.id}`);
     }
     await toBlob.promote(ref);
     wroteBlob = true;
   }
 
   const sanitized: any = sanitizeAdditiveVideo(video);
   if (slot) {
     sanitized.serialNumber = slot.serialNumber;
     sanitized.playlistIndex = slot.position + 1;
   }
   if (wroteBlob) {
     sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
   } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
     // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
     // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
     // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
     delete sanitized.artifacts.summaryMd;
   }
   await to.upsertVideo(toP, sanitized as Video);
 
   // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
   // (an update against an absent row silently no-ops; never advance a baseline for that).
   const after = await to.readIndex(toP);
   const rec = after.videos.find((v) => v.id === video.id);
   if (!rec) {
     throw new Error(`additive create did not persist receiver row for ${video.id}`);
   }
   // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
   // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
   // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
   if (wroteBlob) {
     const art = (rec as any).artifacts?.summaryMd;
     if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
       throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
     }
   }
 }
 
 /** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
  *  side's values, so this is a true agreed baseline. */
 function baselineFromOneSided(
   classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
 ): VideoBaseline {
   const classB = {} as VideoBaseline['classB'];
@@ -284,192 +299,200 @@ async function applyClassBWinners(args: {
     const { found } = await target.store.updateVideoAnnotations(
       target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
     );
     if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
     merged += 1;
   }
   return { merged, conflicts };
 }
 
 /** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
  *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
  *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
  *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
 async function transferClassA(
   winner: Side, loser: Side, winnerVideo: Video, videoId: string,
 ): Promise<{ mdHash: string; verified: boolean }> {
   const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   if (body == null || !winnerVideo.summaryMd) {
     throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   }
   const h = mdHash(body);
   const key = winnerVideo.summaryMd;
 
   const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   const staged = await loser.blob.get(loser.p, ref.tempKey);
   if (!staged || mdHash(staged.toString('utf8')) !== h) {
     throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   }
   // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   // (below) advertises promoted only after this resolves.
   await loser.blob.put(loser.p, key, staged, 'text/markdown');
   await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
 
   const wv: any = winnerVideo;
   const completeTuple: any = {
     summaryMd: key,
     docVersion: wv.docVersion,
     mdGeneratedAt: wv.mdGeneratedAt ?? null,
     mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
     ratings: wv.ratings,
     overallScore: wv.overallScore,
     videoType: wv.videoType,
     audience: wv.audience,
     tags: wv.tags,
     tldr: wv.tldr,
     takeaways: wv.takeaways,
     // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
     // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
     // the serve path (buildDocHtml/ensureHtmlDoc) checks generator-version, NOT MD-body freshness, so a
     // same-format prose change (the recency-tiebreak case) would serve stale HTML indefinitely (§5.1
     // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
     // readIndex reads falsy → forces re-render.
     //
     // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
     // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
     // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
     // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
     // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
     // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
     // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
     // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
     // whereas transferClassA PATCHES a row that already holds its own state.
     summaryHtml: null,
     digDeeperHtml: null,
     // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
     // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
     artifacts: { summaryMd: { key, status: 'promoted' } },
   };
   await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
 
   return { mdHash: h, verified: true };
 }
 
 /** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
- *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
- *  that the owner must re-serve to regenerate the share model. */
+ *  MD; otherwise delete the loser's model (best-effort, OUTSIDE the atomic commit) and flag that the
+ *  owner must re-serve — but ONLY when that model proves itself stale (H-R5-1). */
 async function companionTransfer(
   winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
 ): Promise<{ shareNeedsOwnerServe: boolean }> {
   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   const base = winnerVideo.summaryMd.replace(/\.md$/, '');
-  const decision = decideCompanion({ winnerMdHash, senderModel: await readSenderModel(winner, base) });
+  // H-R5-1 (round 5) — read BOTH sides. The sender read says whether a replacement can be shipped;
+  // only the RECEIVER's own envelope can prove the receiver's model stale (see decideCompanion).
+  const [senderModel, receiverModel] = await Promise.all([
+    readModelSide(winner, base), readModelSide(loser, base),
+  ]);
+  const decision = decideCompanion({ winnerMdHash, senderModel, receiverModel });
   if (decision.kind === 'ship') {
     await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
     return { shareNeedsOwnerServe: false };
   }
-  // H1 (round 4) — the sender read could not prove anything: leave the receiver's model alone and
-  // do NOT report shareNeedsOwnerServe (nothing is known to be stale about the share).
-  if (decision.kind === 'noop') return { shareNeedsOwnerServe: false };
+  // H1 (round 4) / H-R5-1 (round 5) — nothing shippable and the receiver's model is not PROVABLY
+  // stale: leave the blob alone. The report flag is decided separately (§10 row 7 counts a share
+  // with no model even though there is nothing to delete).
+  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
   // deleteReceiverModel — best-effort; a missing model blob is not an error.
   try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   return { shareNeedsOwnerServe: true };
 }
 
 /** H1 (round 4) — resolve `readModelEnvelope`'s single null into the tri-state decideCompanion needs.
  *  A null means absent, corrupt, or unreadable; only a backend that can prove absence
  *  (BlobStore.provesAbsence — the local FS store, whose get is ENOENT-only) lets us tell those
  *  apart. On such a backend a null is definitive either way: the model is genuinely missing, or its
- *  bytes were read and rejected — both mean the sender has nothing shippable, so the receiver's now
- *  stale model is correctly dropped. On the Supabase backend the same null may be a transient 5xx /
- *  timeout / RLS denial, so it proves nothing and must not drive a destructive delete. A backend
- *  that does not declare the capability is treated as unable to prove absence. */
-async function readSenderModel(sender: Side, base: string): Promise<SenderModelRead> {
-  const envelope = await readModelEnvelope(sender.p, base, sender.blob);
+ *  bytes were read and rejected — both mean that side has nothing usable. On the Supabase backend
+ *  the same null may be a transient 5xx / timeout / RLS denial, so it proves nothing and must not
+ *  drive a destructive delete. A backend that does not declare the capability is treated as unable
+ *  to prove absence.
+ *  H-R5-1 (round 5) — used for the RECEIVER too (hence the neutral name): a receiver `unknown` must
+ *  not be read as "no model", and a receiver `none` leaves nothing to delete. */
+async function readModelSide(side: Side, base: string): Promise<ModelRead> {
+  const envelope = await readModelEnvelope(side.p, base, side.blob);
   if (envelope) return { kind: 'envelope', envelope };
-  return sender.blob.provesAbsence ? { kind: 'none' } : { kind: 'unknown' };
+  return side.blob.provesAbsence ? { kind: 'none' } : { kind: 'unknown' };
 }
 
 /** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
  *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
  *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
  *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
  *  recording the winner there would be a false agreement → next-run silent overwrite). */
 function buildClassBBaseline(
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline['classB'] {
   const classB = {} as VideoBaseline['classB'];
   for (const f of FIELDS) {
     const m = merges[f];
     if (m.winner === 'equal' && m.conflict) {
       classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
     } else {
       classB[f] = { value: m.value, editedAt: m.editedAt };
     }
   }
   return classB;
 }
 
 function buildBaseline(
   winnerSignals: ClassASignals, winnerMdHash: string | null,
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline {
   return {
     classA: {
       docVersionMajor: winnerSignals.docVersionMajor,
       mdGeneratedAt: winnerSignals.mdGeneratedAt,
       mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
       mdHash: winnerMdHash,
     },
     classB: buildClassBBaseline(merges, previousBaseline),
   };
 }
 
 /** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
  *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
  *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
  *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
  *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
  *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
  *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
 function buildCorrectionsUnresolvedBaseline(
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline {
   return {
     classA: previousBaseline?.classA
       ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
     classB: buildClassBBaseline(merges, previousBaseline),
   };
 }
 
 export async function runSync(
   deps: SyncDeps, opts: { playlistKey?: string } = {},
 ): Promise<SyncReport> {
   resetConflictDedup();
   const report: SyncReport = {
     created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
     mergedFields: 0, conflictsLogged: 0, removed: 0,
     shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   };
 
   const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
 
   for (const key of keys) {
     const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
       ?? hydrationRoot(deps.dataRoots, key);
     await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
 
     const localP = localPrincipal(dataRoot);
     const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
     const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
     const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
     const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
diff --git a/tests/integration/cloud-sync/e2e.int.test.ts b/tests/integration/cloud-sync/e2e.int.test.ts
index 707450f..748488d 100644
--- a/tests/integration/cloud-sync/e2e.int.test.ts
+++ b/tests/integration/cloud-sync/e2e.int.test.ts
@@ -1,97 +1,97 @@
 // tests/integration/cloud-sync/e2e.int.test.ts
 //
 // Stage 3 Cloud Sync (§10), Task 14 — the end-to-end keystone. One `it(...)` per §10 scenario,
 // driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
 // USER session (never service-role). Where Task 12 proved the additive hydrate path, rows 1/2/7
 // here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
 // MD bodies — the winner-copy path the Task-12 tests never exercised.
 //
 // Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
 // is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
 import { promises as fs } from 'fs';
 import os from 'os';
 import path from 'path';
 import { randomUUID } from 'crypto';
 import {
   makeOwnerContext, prepareSyncCtx, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
-  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, type Ctx,
+  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, putCloudBlob, type Ctx,
 } from '@/tests/integration/helpers/cloud';
 import { adminClient } from '@/tests/integration/helpers/clients';
 import { runSync } from '@/lib/cloud-sync/sync-run';
 import { mdHash } from '@/lib/cloud-sync/content-hash';
 import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
 import type { VideoBaseline } from '@/lib/cloud-sync/types';
 
 afterAll(async () => {
   const home = os.homedir();
   const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
   await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
 });
 
 const key = (ctx: Ctx) => `${ctx.videoId}.md`;
 /** `artifacts` lives in the videos.data jsonb but is not on the Video Zod type — read it via a cast. */
 const artifactsOf = (rec: { [k: string]: unknown } | null) =>
   (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
 /** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
 const bodyHash = (b: string) => mdHash(b);
 /** mdCorrectionsHash value that makes a side "corrections-current" when NO corrections exist:
  *  reconciledCorrectionsHash === mdHash(String(undefined ?? '')) === mdHash(''). */
 const H_NO_CORRECTIONS = mdHash('');
 /** The companion model blob key for this ctx's summary (models/<base>.json, base = summaryMd sans .md). */
 const modelKey = (ctx: Ctx) => `models/${ctx.videoId}.json`;
 /** A schema-valid ModelEnvelope (ModelEnvelopeSchema) whose sourceMdHash is caller-supplied. */
 const modelEnvelope = (sourceMdHash: string) => ({
   sourceMd: 'seed.md', generatedAt: '2026-01-01T00:00:00.000Z', sourceSections: ['A'],
   model: {
     sections: [{
       lead: 'lead',
       bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }],
     }],
   },
   sourceMdHash,
 });
 /** Read the cloud playlist row's title (admin client — assertion only, not a code path). */
 async function cloudPlaylistTitle(ctx: Ctx): Promise<string | null> {
   const { data, error } = await adminClient()
     .from('playlists').select('playlist_title').eq('playlist_key', ctx.playlistKey).single();
   if (error) throw error;
   return (data as { playlist_title: string | null }).playlist_title;
 }
 
 /** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
 function baseline(classB: VideoBaseline['classB']): VideoBaseline {
   return {
     classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
     classB,
   };
 }
 const EMPTY_CLASSB = {
   personalNote: { value: undefined, editedAt: undefined },
   personalScore: { value: undefined, editedAt: undefined },
   corrections: { value: undefined, editedAt: undefined },
 } as VideoBaseline['classB'];
 
 describe('cloud-sync §10 end-to-end scenarios', () => {
   // ── Row 1 — Class-A anti-recency: higher-major MD beats a NEWER-timestamp lower-major MD.
   //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
   it('row 1: higher-major MD beats a newer lower-major (format beats recency); receiver copies it', async () => {
     const ctx = await makeOwnerContext();
     const bodyHi = '# HiMajor\n\nformat-3 content\n';   // local, docVersion.major=3, OLD timestamp
     const bodyLo = '# LoMajor\n\nformat-1 content\n';   // cloud, docVersion.major=1, NEWER timestamp
     const winnerRatings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 };
     await seedLocalVideoFull(ctx, {
       mdBody: bodyHi, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2020-01-01T00:00:00.000Z',
       mdCorrectionsHash: H_NO_CORRECTIONS, ratings: winnerRatings, overallScore: 3,
       tldr: 'the-tldr', takeaways: ['a', 'b'], tags: ['x', 'y'],
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyLo, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2026-06-01T00:00:00.000Z',
       mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     const report = await runSync(ctx.syncDeps());
 
     expect(report.updatedCloud).toBeGreaterThanOrEqual(1);
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges
 
@@ -580,192 +580,340 @@ describe('cloud-sync §10 end-to-end scenarios', () => {
   //    is treated as the empty side and the OTHER replica's body is copied over it — destroying it and
   //    laundering the result into a full-agreement baseline. Both manifestations below must instead
   //    surface a per-video error, preserve every byte, and advance NO baseline (so the run heals once
   //    the body is readable). Each asserts across TWO runs: round 2's postmortem was that a
   //    single-run assertion passed while the laundering bug was live.
   it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // backfilled (no per-field ts)
       docVersion: { major: 1, minor: 0 },
     });
     // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
     // the buggy path read as "cloud has no MD" ⇒ the corrections guard did not fire ⇒ copyToCloud.
     await seedCloudVideo(ctx, {
       /* mdBody omitted → blob unreadable */
       corrections: 'B', mdCorrectionsHash: mdHash('B'), docVersion: { major: 1, minor: 0 },
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     for (const _run of [1, 2]) {
       const report = await runSync(ctx.syncDeps());
 
       // The failure is SURFACED, not silent (the buggy path reported errors: []).
       expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
       expect(report.updatedCloud).toBe(0);
       expect(report.updatedLocal).toBe(0);
       // Local body byte-preserved; cloud body still absent (nothing was written over the gap).
       expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
       expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
       // Both corrections preserved.
       expect((await localVideoRecord(ctx))?.corrections).toBe('A');
       expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
       // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
       expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
       expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
     }
   });
 
   it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocal = '# LocalOld\n\nlower-major local body\n';
     // No corrections anywhere — this manifestation is NOT conflict-gated: the !cHas early return in
     // reconcileClassA precedes the never-downgrade-format rule, so a transient download error let a
     // major-1 body overwrite a major-9 one and recorded major 1 as the agreed baseline. Run 2 then saw
     // identical bodies ⇒ skip ⇒ permanent, recoverable only by full (paid) regeneration.
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocal, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     await seedCloudVideo(ctx, {
       /* mdBody omitted → blob unreadable */
       docVersion: { major: 9, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     for (const _run of [1, 2]) {
       const report = await runSync(ctx.syncDeps());
 
       expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
       expect(report.updatedCloud).toBe(0);
       expect(report.updatedLocal).toBe(0);
       expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
       expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
       // Format NOT downgraded on either side (the buggy path wrote cloud major 9 → 1).
       expect((await cloudVideoRecord(ctx))?.docVersion?.major).toBe(9);
       expect((await localVideoRecord(ctx))?.docVersion?.major).toBe(1);
       expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
       expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
     }
   });
 
   // ── H1 (round 4) — the B1 conflation one module over, driving a DELETE. companionTransfer read
   //    the SENDER's model envelope and mapped null to deleteReceiverModel. On a copyToLocal transfer
   //    the sender is the CLOUD, whose blob get swallows every failure into null, so a transient
   //    download error is indistinguishable from "the sender has no model" — and the RECEIVER's
   //    (local) model was deleted for it. That is a money bug, not a cache nit: the only way back is
   //    runHtmlDoc → generateMagazineModel, a PAID Gemini transform. It was also sticky — the delete
   //    does not throw, so the baseline advanced, run 2 saw equal hashes and returned 'skip', and
   //    companionTransfer never ran again.
   //    Here the cloud sender genuinely has no model, which on the Supabase backend is EXACTLY the
-  //    unreadable case at the byte level — absence is unprovable, so the local model must survive.
-  //    (Row 7 covers the mirror direction, where the LOCAL sender's ENOENT does prove absence and
-  //    the delete is still correct.)
-  it('H1: an unprovable cloud model read leaves the local model intact and flags no owner-serve (2 runs)', async () => {
+  //    unreadable case at the byte level — absence is unprovable.
+  //
+  //    H-R5-1 (round 5) — round 4 keyed the WHOLE decision to that sender read, which was wrong in
+  //    both directions, so the three rows below replace the single round-4 row. The sender read now
+  //    decides only whether a REPLACEMENT can be shipped; the receiver's own sourceMdHash decides
+  //    its fate, and it decides it exactly (we hold winnerMdHash). Rows (i) and (ii) share the
+  //    identical unprovable-cloud-sender setup and differ ONLY in the receiver's sourceMdHash,
+  //    which is the whole point: the sender read is not the thing that answers the question.
+  //    (Row 7 covers the mirror direction, where the LOCAL sender's ENOENT proves absence.)
+
+  // (i) The round-4 defect: `unknown` → noop KEPT a model whose backing body was just overwritten.
+  //     Nothing catches it downstream — the serve path's drift guard compares section TITLES and
+  //     generatorVersion, never sourceMdHash, so a prose-only change (headings identical, which is
+  //     exactly the recency-tiebreak case) renders stale Gemini prose as current forever, and
+  //     dig-deeper never regenerates. Its staleness needs no sender read to establish.
+  it('H-R5-1(i): an unprovable sender read still DELETES a provably-stale receiver model (2 runs)', async () => {
+    const ctx = await makeOwnerContext();
+    // Same section titles, different prose — the drift guard cannot see the difference.
+    const bodyLocalOld = '# Shared Title\n\nthe OLD prose the local model was built from\n';
+    const bodyCloudWin = '# Shared Title\n\nthe NEW prose that wins on format major\n';
+    await seedLocalVideoFull(ctx, {
+      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    await seedCloudVideo(ctx, {
+      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    // Receiver (local) model was built from the OLD body; sender (cloud) holds no model at all.
+    await ctx.localBlob.put(
+      ctx.localPrincipal, modelKey(ctx),
+      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalOld)))}\n`, 'utf8'), 'application/json',
+    );
+    const spendBefore = await ctx.spendLedgerTotal();
+
+    const r1 = await runSync(ctx.syncDeps());
+
+    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);            // the Class-A transfer ran
+    expect(await localBlobBytes(ctx, modelKey(ctx))).toBeNull();  // provably stale → deleted
+    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
+    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);       // the delete itself never charges
+
+    // Run 2 — hashes now agree → reconcileClassA 'skip' → companionTransfer never runs again. The
+    // stickiness that would have made a WRONG decision permanent must not resurrect the model.
+    const r2 = await runSync(ctx.syncDeps());
+    expect(r2.shareNeedsOwnerServe).toBe(0);
+    expect(await localBlobBytes(ctx, modelKey(ctx))).toBeNull();
+    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
+  });
+
+  // (ii) The round-4 money bug, preserved: the receiver's model was built from the very body that
+  //      just won, so it is still valid. An unprovable sender read must not cost the owner a paid
+  //      Gemini magazine transform to rebuild what it already has.
+  it('H-R5-1(ii): an unprovable sender read PRESERVES a receiver model that matches the winner (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocalOld = '# LocalOld\n\nlower-major local body\n';
     const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
-    // The local (receiver) replica holds a model; the cloud (sender/winner) holds none.
-    const envelope = modelEnvelope(bodyHash(bodyLocalOld));
+    // Receiver (local) model already matches the WINNING cloud body; sender (cloud) holds no model.
+    const envelope = modelEnvelope(bodyHash(bodyCloudWin));
     await ctx.localBlob.put(
       ctx.localPrincipal, modelKey(ctx),
       Buffer.from(`${JSON.stringify(envelope)}\n`, 'utf8'), 'application/json',
     );
     const spendBefore = await ctx.spendLedgerTotal();
 
     const r1 = await runSync(ctx.syncDeps());
 
-    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);          // the Class-A transfer still ran
-    expect(r1.shareNeedsOwnerServe).toBe(0);                    // no false "share is stale" signal
-    expect(await localBlobBytes(ctx, modelKey(ctx))).not.toBeNull(); // receiver model NOT deleted
+    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);
+    const kept = await localBlobBytes(ctx, modelKey(ctx));
+    expect(kept).not.toBeNull();                                     // paid artifact survives
+    expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyCloudWin));
+    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
 
-    // Run 2 — hashes now agree so reconcileClassA returns 'skip' and companionTransfer never runs
-    // again. That is precisely what made the deletion permanent, so the model must STILL be there.
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.shareNeedsOwnerServe).toBe(0);
     expect(await localBlobBytes(ctx, modelKey(ctx))).not.toBeNull();
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   });
 
+  // (iii) The other half of round 4's conflation, on the backend that CAN prove absence. A local
+  //       sender null also covers corrupt/schema-invalid (readModelEnvelope parses and validates),
+  //       which round 4 mapped to `none` → delete. But "the sender's envelope is garbage" says
+  //       nothing about the receiver's, and here the cloud receiver's matches the winning body
+  //       exactly. Deleting it would burn reserve_serve_model → spend_ledger to rebuild.
+  it('H-R5-1(iii): a CORRUPT local sender envelope preserves a matching cloud receiver model (2 runs)', async () => {
+    const ctx = await makeOwnerContext();
+    const bodyLocalWin = '# LocalWin\n\nhigher-major local body\n';
+    const bodyCloudOld = '# CloudOld\n\nlower-major cloud body\n';
+    await seedLocalVideoFull(ctx, {
+      mdBody: bodyLocalWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    await seedCloudVideo(ctx, {
+      mdBody: bodyCloudOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    // Sender (local) envelope is unparseable → readModelEnvelope null on a provesAbsence backend.
+    await ctx.localBlob.put(
+      ctx.localPrincipal, modelKey(ctx), Buffer.from('{not json at all', 'utf8'), 'application/json',
+    );
+    // Receiver (cloud) model matches the WINNING local body → still valid, must survive.
+    await putCloudBlob(
+      ctx, modelKey(ctx),
+      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin)))}\n`, 'utf8'), 'application/json',
+    );
+    const spendBefore = await ctx.spendLedgerTotal();
+
+    const r1 = await runSync(ctx.syncDeps());
+
+    expect(r1.updatedCloud).toBeGreaterThanOrEqual(1);
+    const kept = await cloudBlobBytes(ctx, modelKey(ctx));
+    expect(kept).not.toBeNull();
+    expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyLocalWin));
+    expect(r1.shareNeedsOwnerServe).toBe(0);
+    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
+
+    const r2 = await runSync(ctx.syncDeps());
+    expect(r2.shareNeedsOwnerServe).toBe(0);
+    expect(await cloudBlobBytes(ctx, modelKey(ctx))).not.toBeNull();
+    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
+  });
+
   // ── H2 (round 4) — the B1 guard was over-broad on the LOCAL side. B1 exists because the Supabase
   //    backend cannot tell absent from unreadable; the local backend CAN (LocalFsBlobStore.get
   //    returns null ONLY on ENOENT and rethrows every other errno), so a local record advertising a
   //    summaryMd whose body reads back null PROVES the file is gone — a user who moved the .md by
   //    hand, or a generation that crashed between the index write and the blob write.
   //    Before the guard this healed for free (!lHas → copyToLocal → the dangling pointer is
   //    repaired, purely additive). The guard made it throw on EVERY run, forever, never advancing a
   //    baseline, with no exit but hand-editing playlist-index.json or paying to regenerate content
   //    sitting intact in the cloud. Fail-closed must be scoped to the backend that needs it.
   it('H2: a genuinely-absent local MD blob is hydrated from the cloud, not stranded (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyCloud = '# CloudHasIt\n\nthe body the local record lost\n';
     // Local ADVERTISES summaryMd (+ a promoted artifact) but mdBody is omitted → the blob is
     // genuinely absent on a backend that proves absence.
     await seedLocalVideoFull(ctx, {
       docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloud, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     const r1 = await runSync(ctx.syncDeps());
 
     expect(r1.errors).toEqual([]);                       // no permanent per-run failure
     expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);   // additive hydration ran
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
     const local = await localVideoRecord(ctx);
     expect(local?.summaryMd).toBe(key(ctx));
     expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // healed without any regeneration
 
     // Run 2 — the dangling pointer is repaired, so the sides simply agree.
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.errors).toEqual([]);
     expect(r2.updatedLocal).toBe(0);
     expect(r2.skippedIdentical).toBeGreaterThanOrEqual(1);
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   });
 
   // ── H3 (round 4) — a local-only video wiped the cloud playlist's title on every sync.
   //    playlistMetaFor checked the local registry FIRST and returned { playlistUrl } with no title
   //    (LocalPlaylist never carried one), the cloud-registry branch that does carry a title being
   //    unreachable whenever the playlist also exists locally. ensureReceiverSlot then called
   //    setPlaylistMeta unconditionally, and the Supabase upsert writes
   //    `playlist_title: meta.playlistTitle ?? null` — an explicit NULL. Recurs on every sync that
   //    carries any local-only video (the ordinary case); recovery needs the backfill-titles route
   //    plus a YouTube API key.
   it('H3: an additive publish of a local-only video preserves the cloud playlist title (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     await prepareSyncCtx(ctx);
     const title = 'Deep Learning Lectures';
     // Cloud playlist row carries a title (as lib/job-queue/producer.ts sets it at enqueue) and holds
     // NO videos; the local replica has a title-less index with one video → additive publish to cloud.
     const { data: pl, error } = await adminClient().from('playlists').insert({
       owner_id: ctx.userId,
       playlist_key: ctx.playlistKey,
       playlist_url: `https://www.youtube.com/playlist?list=${ctx.playlistKey}`,
       playlist_title: title,
     }).select('id').single();
     if (error) throw error;
     ctx.playlistId = (pl as { id: string }).id;
     await seedLocalVideoFull(ctx, { mdBody: '# LocalOnly\n\njust summarized locally\n' });
     expect(await cloudPlaylistTitle(ctx)).toBe(title); // fixture precondition
 
     const r1 = await runSync(ctx.syncDeps());
 
     expect(r1.created).toBeGreaterThanOrEqual(1);        // the additive publish ran
     expect(await cloudVideoRecord(ctx)).not.toBeNull();
     expect(await cloudPlaylistTitle(ctx)).toBe(title);   // title NOT cleared
 
     // Run 2 — ensureReceiverSlot's setPlaylistMeta fires on every run, so once is not enough.
     await runSync(ctx.syncDeps());
     expect(await cloudPlaylistTitle(ctx)).toBe(title);
   });
+
+  // ── L-R5-2 (round 5) — H3 stopped a sync CLEARING the cloud title, but not OVERWRITING it.
+  //    playlistMetaFor preferred `lp?.playlistTitle`, so a local playlist-index.json title — whatever
+  //    was captured when that folder was last summarized — clobbered the cloud row's on every
+  //    additive local→cloud create. Titles carry no LWW timestamp, so precedence is fixed: the cloud
+  //    row wins, because it is the one the ingest and backfill-titles paths keep current from the
+  //    live YouTube API. Recurs on every sync and recovery needs backfill-titles + an API key.
+  it('L-R5-2: a stale local playlist title does NOT overwrite a fresher cloud title (2 runs)', async () => {
+    const ctx = await makeOwnerContext();
+    await prepareSyncCtx(ctx);
+    const cloudTitle = 'Deep Learning Lectures (2026 edition)';
+    const staleLocalTitle = 'Deep Learning Lectures';
+    const { data: pl, error } = await adminClient().from('playlists').insert({
+      owner_id: ctx.userId,
+      playlist_key: ctx.playlistKey,
+      playlist_url: `https://www.youtube.com/playlist?list=${ctx.playlistKey}`,
+      playlist_title: cloudTitle,
+    }).select('id').single();
+    if (error) throw error;
+    ctx.playlistId = (pl as { id: string }).id;
+    await seedLocalVideoFull(ctx, { mdBody: '# LocalOnly\n\njust summarized locally\n' });
+    // The local index carries an OLD title for the same playlist (renamed on YouTube since).
+    await ctx.local.setPlaylistMeta(ctx.localPrincipal, {
+      playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}`,
+      playlistTitle: staleLocalTitle,
+    });
+
+    const r1 = await runSync(ctx.syncDeps());
+
+    expect(r1.created).toBeGreaterThanOrEqual(1);              // the additive publish ran
+    expect(await cloudPlaylistTitle(ctx)).toBe(cloudTitle);    // cloud title NOT overwritten
+    await runSync(ctx.syncDeps());
+    expect(await cloudPlaylistTitle(ctx)).toBe(cloudTitle);
+  });
+
+  // The other half of the precedence: with no cloud title, the local one still FILLS it, so
+  // preferring the cloud never costs a playlist its only title.
+  it('L-R5-2: a local title still fills a cloud playlist that has none', async () => {
+    const ctx = await makeOwnerContext();
+    await prepareSyncCtx(ctx);
+    const localTitle = 'Locally Named Playlist';
+    const { data: pl, error } = await adminClient().from('playlists').insert({
+      owner_id: ctx.userId,
+      playlist_key: ctx.playlistKey,
+      playlist_url: `https://www.youtube.com/playlist?list=${ctx.playlistKey}`,
+    }).select('id').single();
+    if (error) throw error;
+    ctx.playlistId = (pl as { id: string }).id;
+    await seedLocalVideoFull(ctx, { mdBody: '# LocalOnly\n\njust summarized locally\n' });
+    await ctx.local.setPlaylistMeta(ctx.localPrincipal, {
+      playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}`,
+      playlistTitle: localTitle,
+    });
+    expect(await cloudPlaylistTitle(ctx)).toBeNull(); // fixture precondition
+
+    await runSync(ctx.syncDeps());
+
+    expect(await cloudPlaylistTitle(ctx)).toBe(localTitle);
+  });
 });
diff --git a/tests/lib/cloud-sync/companion.test.ts b/tests/lib/cloud-sync/companion.test.ts
index 9cc2bac..fc8f9e2 100644
--- a/tests/lib/cloud-sync/companion.test.ts
+++ b/tests/lib/cloud-sync/companion.test.ts
@@ -1,41 +1,86 @@
-import { decideCompanion } from '@/lib/cloud-sync/companion';
+import { decideCompanion, type ModelRead } from '@/lib/cloud-sync/companion';
 import type { ModelEnvelope } from '@/lib/html-doc/model-store';
 
 const env = (sourceMdHash?: string): ModelEnvelope => ({
   sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
   model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
   ...(sourceMdHash ? { sourceMdHash } : {}),
 });
+const envelope = (h?: string): ModelRead => ({ kind: 'envelope', envelope: env(h) });
+const decide = (senderModel: ModelRead, receiverModel: ModelRead) =>
+  decideCompanion({ winnerMdHash: 'h1', senderModel, receiverModel });
 
-it('ships when the envelope matches the winning MD', () => {
-  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'envelope', envelope: env('h1') } }))
-    .toMatchObject({ kind: 'ship' });
-});
-it('deletes the receiver model when the envelope does not match', () => {
-  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'envelope', envelope: env('h2') } }))
-    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
-});
-it('deletes when the legacy envelope lacks sourceMdHash', () => {
-  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'envelope', envelope: env(undefined) } }))
-    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
+const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
+/** Keep the receiver's blob. `flag` is the SEPARATE report-only axis (§10 row 7). */
+const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
+
+// ── Rule 1 — the sender has a model built from the WINNING md: ship it, whatever the receiver holds.
+describe('sender ships', () => {
+  it.each<[string, ModelRead]>([
+    ['receiver absent', { kind: 'none' }],
+    ['receiver unreadable', { kind: 'unknown' }],
+    ['receiver stale', envelope('h2')],
+    ['receiver already current', envelope('h1')],
+  ])('ships a matching sender envelope (%s)', (_label, receiver) => {
+    expect(decide(envelope('h1'), receiver)).toMatchObject({ kind: 'ship' });
+  });
 });
-it('deletes when the sender PROVABLY has no model at all', () => {
-  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'none' } }))
-    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
+
+// ── H-R5-1 (round 5) — rules 2/3. The sender read answers "can a replacement be shipped?"; it does
+//    NOT answer "is the receiver's model stale?". Only the RECEIVER's own sourceMdHash answers that,
+//    and it answers it exactly. So every non-ship sender state funnels into the same receiver-keyed
+//    decision — `unknown` is no longer a decision of its own, and `none` no longer deletes blind.
+describe('receiver-keyed decision (every non-shipping sender state)', () => {
+  const nonShippingSenders: [string, ModelRead][] = [
+    ['sender provably has none', { kind: 'none' }],
+    ['sender read is unprovable', { kind: 'unknown' }],
+    ['sender envelope does not match the winner', envelope('h2')],
+    ['sender envelope is legacy (no sourceMdHash)', envelope(undefined)],
+  ];
+
+  describe.each(nonShippingSenders)('%s', (_label, sender) => {
+    it('DELETES a receiver model whose sourceMdHash provably differs from the winner', () => {
+      expect(decide(sender, envelope('h2'))).toEqual(DELETE);
+    });
+    it('KEEPS a receiver model whose sourceMdHash matches the winner (still valid — paid artifact)', () => {
+      expect(decide(sender, envelope('h1'))).toEqual(KEEP(false));
+    });
+    it('touches nothing when the receiver PROVABLY has no model, but still counts the unready share', () => {
+      // §10 row 7 — nothing to delete, yet the share cannot render until the owner re-serves. The
+      // blob action and the report flag are separate axes.
+      expect(decide(sender, { kind: 'none' })).toEqual(KEEP(true));
+    });
+    it('KEEPS but still counts when the receiver read itself could not prove absence', () => {
+      // Unprovable, so the DELETE must not fire — but the flag costs nothing and under-reporting
+      // is what strands an anon visitor on a not-ready share.
+      expect(decide(sender, { kind: 'unknown' })).toEqual(KEEP(true));
+    });
+    it('KEEPS but still counts a legacy receiver envelope with no sourceMdHash', () => {
+      expect(decide(sender, envelope(undefined))).toEqual(KEEP(true));
+    });
+  });
 });
 
-// ── H1 (round 4) — the third state. A sender read that could not PROVE the model is absent
-//    (a Supabase get swallows network/5xx/timeout/RLS into the same null as a 404) must NOT be
-//    read as "the sender has no model": deleting the receiver's model on that signal destroys a
-//    cache whose only recovery is a PAID Gemini magazine transform. No-op instead — the receiver
-//    keeps its (possibly stale) model, which the serve path's sourceSections drift guard rejects
-//    for free if it no longer matches.
-it('no-ops when the sender model could not be read (absence unprovable)', () => {
-  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'unknown' } }))
-    .toEqual({ kind: 'noop' });
+// ── The report flag on the SHIP branch: the receiver ends up holding a model built from the
+//    winning MD, so the share renders and nothing is owed.
+it('never flags owner-serve when a model was shipped', () => {
+  for (const r of [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope('h1')] as ModelRead[]) {
+    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
+  }
 });
-it('no-ops on unknown even when a matching hash would otherwise ship', () => {
-  // There is no envelope to ship — `unknown` carries no bytes at all, so the only safe action is
-  // to leave BOTH sides exactly as they are.
-  expect(decideCompanion({ winnerMdHash: 'h1', senderModel: { kind: 'unknown' } }).kind).toBe('noop');
+
+// ── The money invariant, stated once as its own assertion: the ONLY input that deletes is a receiver
+//    envelope carrying a sourceMdHash that differs from the winner's. Everything else keeps.
+it('deletes only on a proven receiver-side mismatch', () => {
+  const senders: ModelRead[] = [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope(undefined), envelope('h1')];
+  const receivers: ModelRead[] = [{ kind: 'none' }, { kind: 'unknown' }, envelope('h1'), envelope(undefined), envelope('h2')];
+  for (const s of senders) {
+    for (const r of receivers) {
+      const deleted = decideCompanion({ winnerMdHash: 'h1', senderModel: s, receiverModel: r }).kind === 'deleteReceiverModel';
+      const senderShips = s.kind === 'envelope' && s.envelope.sourceMdHash === 'h1';
+      const receiverProvablyStale = r.kind === 'envelope' && r.envelope.sourceMdHash !== undefined
+        && r.envelope.sourceMdHash !== 'h1';
+      expect(deleted).toBe(!senderShips && receiverProvablyStale);
+    }
+  }
 });

exec
/bin/bash -lc 'git status --short && rg -n "decideCompanion|readReceiverModel|shareNeedsOwnerServe|ensureReceiverSlot|playlistMetaFor|provablyStale|readIndex|setPlaylistMeta" lib tests docs/superpowers -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
 M docs/local-validation-findings.md
 M supabase/config.toml
?? .codex-tasks/
?? docs/reviews/task-12-sync-run-behaviors-codex.md
?? docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md
?? scratchpad/
docs/superpowers/plans/2026-06-17-persist-magazine-model.md:501:import { assertOutputFolder, assertVideoId, readIndex } from '../index-store';
docs/superpowers/plans/2026-06-17-persist-magazine-model.md:527:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-17-persist-magazine-model.md:667:  const index = readIndex(outputFolder);
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:64:  readIndex(p: Principal): Promise<PlaylistIndex>;
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:65:  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:96:| `readIndex` | Resolve playlist by `(owner_id, playlist_key)`; `SELECT … FROM videos WHERE playlist_id=$1 ORDER BY position`; reassemble. **No playlist row → `emptyPlaylistIndex(principal)`** (§3.3). |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:97:| `setPlaylistMeta` | `INSERT … ON CONFLICT (owner_id, playlist_key) DO UPDATE SET playlist_url=EXCLUDED.playlist_url, playlist_title=COALESCE(EXCLUDED.playlist_title, playlists.playlist_title)`. |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:108:Local `index-store.readIndex` returns `{ playlistUrl: '', outputFolder, videos: [] }` for an absent file — but `PlaylistIndexSchema.playlistUrl` is `z.string().url()`, which **rejects `''`**. Resolution:
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:118:`pipeline:417` maps over videos **preserving array order**, updating only the three jsonb fields → it is a **bulk field update**, not a reorder → `bulkUpdateVideoFields`. The UI sorts client-side, so `readIndex` must return **insertion order** (parity with local).
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:124:| `pipeline.ts:284` | `writeIndex({…playlistUrl, playlistTitle})` | `await setPlaylistMeta({ playlistUrl, playlistTitle })` |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:125:| `playlists/backfill-titles.ts:36` | `writeIndex({…playlistTitle})` | `await setPlaylistMeta({ playlistUrl, playlistTitle })` (threads existing `playlistUrl`) |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:126:| `pipeline.ts:317` (serial alloc) + `:358` (new upsert) | `nextSerial(readIndex().videos)` then `upsertVideo` | `await claimVideoSlot(videoId)` → build video with returned `serial` → `await upsertVideo` |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:207:| **Integration** (local Supabase stack, 1B harness, `--runInBand`) | Real Postgres + Storage with injected JWT. Cloud CRUD; `claimVideoSlot`/`reconcilePlaylistMembership`/`bulkUpdateVideoFields`; **RLS isolation** for rows **and** blobs (cross-user read/write/list/move/delete denial, F9); empty-read parity; owner-scoped keys; `setPlaylistMeta` create-then-update. |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:227:| 1 | `readIndex`, no playlist row | `emptyPlaylistIndex(principal)` (shape parity; schema accepts `playlistUrl:''`). |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:234:| 8 | `setPlaylistMeta` first then second call | INSERT then UPDATE; `playlist_url` NOT NULL satisfied both times. |
docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md:260:- **Q1** (backfill-titles `playlistUrl` threading): resolved — `setPlaylistMeta` threads the existing `playlistUrl` (read from the index backfill already loads) to satisfy the `NOT NULL` column on the ON-CONFLICT insert. Secondary to F8 per Codex.
docs/superpowers/plans/2026-06-09-html-doc-magazine-skim.md:15:- Path/id guards: `assertOutputFolder`, `assertVideoId`; index I/O: `readIndex`, `updateVideoFields` (atomic via tmp+rename) in `lib/index-store.ts`.
docs/superpowers/plans/2026-06-09-html-doc-magazine-skim.md:939:import { assertOutputFolder, assertVideoId, readIndex, updateVideoFields } from '../index-store';
docs/superpowers/plans/2026-06-09-html-doc-magazine-skim.md:953:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-09-html-doc-magazine-skim.md:1412:import { assertOutputFolder, assertVideoId, readIndex } from '../../../../lib/index-store';
docs/superpowers/plans/2026-06-09-html-doc-magazine-skim.md:1439:    const index = readIndex(outputFolder);
docs/superpowers/specs/2026-06-09-deep-dive-html-export-design.md:106:2. Serve route: validate → `readIndex` → deep-dive branch → `base = deepDiveMd` minus `.md`.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:623:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:626:    const idx = await localMetadataStore.readIndex(p);
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:635:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:638:    const idx = await localMetadataStore.readIndex(p);
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:645:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:648:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:659:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:662:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:669:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:672:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:681:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:684:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:757:**(c) Model-envelope `sourceMdHash` stamp (High — else every companion is deleted)** — every writer of a `ModelEnvelope` must set `sourceMdHash = mdHash(MD-BODY)` so `decideCompanion` (Task 8) recognizes a valid companion instead of treating it as legacy and deleting it (→ needless re-charge on serve). **CRITICAL — hash the BODY, not the key:** in `lib/html-doc/generate.ts` the MD **body** is the local variable `md` (line 33: `const md = mdBytes.toString('utf-8')`), whereas `sourceMd` / `video.summaryMd` (lines 36, 50) is the blob **key/filename**. Set `sourceMdHash: mdHash(md)` — NOT `mdHash(sourceMd)`, which would hash `"001_title.md"` and reintroduce Blocking ① in the companion path (`decideCompanion` compares against `mdHash(body)`, so a filename-hash never matches → every synced companion deleted). Apply the same at every other `writeModelEnvelope` site (read the body bytes there and hash those).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1279:  - `decideCompanion(args: { winnerMdHash: string; senderEnvelope: ModelEnvelope | null }): CompanionAction`
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1280:  - `type CompanionAction = { kind: 'ship'; envelope: ModelEnvelope } | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }`
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1287:import { decideCompanion } from '@/lib/cloud-sync/companion';
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1297:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h1') })).toMatchObject({ kind: 'ship' });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1300:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h2') }))
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1301:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1304:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env(undefined) }))
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1305:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1308:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: null }))
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1309:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1326:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1329:export function decideCompanion(args: {
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1337:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1722:- Consumes: `LocalFsMetadataStore` (`readIndex`, `setPlaylistMeta`), `MetadataStore.listPlaylists` (cloud), `localPrincipal`.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1789:      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1831:- Consumes: everything above — `deriveClassASignals`/`deriveHumanSnapshot` (T5), `reconcileHuman` (T6), `reconcileClassA` (T7), `decideCompanion` (T8), `readManifest`/`writeVideoBaseline`/`appendConflict`/`resetConflictDedup` (T9), `discoverLocalPlaylists`/`unionPlaylistKeys` (T11), `mdHash` (T1), and the two `MetadataStore` impls + `BlobStore`s.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1835:  - `SyncReport = { created; updatedLocal; updatedCloud; skippedIdentical; mergedFields; conflictsLogged; removed; shareNeedsOwnerServe; needsRegen; archivedNotSynced; errors }` (all counters, plus per-video error list).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1844:| 3 | Additive create (money-safe) | video present one side, not in baseline | `ensureReceiverSlot` first (create playlist+reservation row — cloud `upsertVideo` only UPDATEs); MD blob written+verified BEFORE `promoted` status; verify receiver row exists BEFORE writing the baseline; **never** call the metered producer/enqueuer; `report.created++` |
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1846:| 5 | Companion ship/delete | after a Class-A copy | `decideCompanion`: ship envelope (`cloudBlob/localBlob.put` model) OR delete receiver model blob + `report.shareNeedsOwnerServe++` |
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1878:    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1924:import { decideCompanion } from './companion';
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1938:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1952:- **`enumerateVideoIds(local, cloud, localP, cloudP): Promise<string[]>`** — union of `video_id`s from `local.readIndex(localP)` and `cloud.readIndex(cloudP)`.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1954:- **`ensureHydrationRoot(dataRoot: string): Promise<void>`** (round-5 H1 — REQUIRED before ANY local read/write for a playlist) — `await fs.mkdir(dataRoot, { recursive: true })`. On a fresh device a cloud-only playlist's local root does not exist yet; local `indexStore.readIndex` throws `"Output folder does not exist"` when the **directory** is missing (`index-store.ts:70-78`), and local `setPlaylistMeta`/`writeIndex` throw `ENOENT` writing into a missing parent (`index-store.ts:83-96`). Creating the directory first makes `readIndex` return the empty-index sentinel (dir exists, file absent → `{ videos: [] }`) and lets `setPlaylistMeta` write the initial `playlist-index.json`. `runSync` calls this at the top of the per-playlist loop (before `readManifest`/`enumerateVideoIds`), so the cloud→local hydrate direction (spec §7 fresh-device pull, Behavior #8) works. The cloud backend needs no equivalent (its `readIndex` returns an empty index for an absent playlist and `setPlaylistMeta` is a DB upsert).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1956:- **`sanitizeAdditiveVideo(video: Video): Video`** (Behavior #3, money-safe — round-2 H3) — returns a copy of the record with **all regenerable-cache and out-of-scope pointers cleared** so the receiver never advertises artifacts whose blobs were not copied: set `summaryHtml`, `digDeeperHtml`, `digDeeperMd` to `null`/absent, and drop every `artifacts.*` entry EXCEPT `artifacts.summaryMd`. Also drop the sender's replica-local ordering (`position`, `serialNumber`, `playlistIndex`, `removedFromPlaylist`) — the receiver's `ensureReceiverSlot` claim supplies these (§4.1). **Keep** identity, Class-A scalars (`ratings`/`overallScore`/`videoType`/`audience`/`tags`/`tldr`/`takeaways`), `summaryMd` (the MD key), the md signals (`mdGeneratedAt`/`mdCorrectionsHash`), the human fields (`personalNote`/`personalScore`/`corrections`), **and their per-field `annotationsEditedAt`** (round-4 L5 — carrying the real edit timestamps means the next sync of this now-two-sided video sees the receiver as non-backfilled, avoiding needless convergence churn).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1957:- **`playlistMetaFor(key, localPlaylists, cloudSummaries): { playlistUrl: string; playlistTitle?: string }`** — resolve the playlist's URL/title for `key` from the local registry entry (`LocalPlaylist.playlistUrl`) or the cloud `PlaylistSummary` (`playlistUrl`/`playlistTitle`), whichever holds it — used by `ensureReceiverSlot` to create the receiver playlist row.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1958:- **`ensureReceiverSlot(to: MetadataStore, toP: Principal, playlistMeta, video: Video): Promise<{ position: number; serialNumber: number } | null>`** (round-4 H1 — REQUIRED before any receiver write) — the cloud `upsertVideo` is a bare `UPDATE` of a row pre-created by `claimVideoSlot` (`supabase-metadata-store.ts:104-113`): an update of a non-existent playlist/video row **silently affects 0 rows and does not throw**. So additive create MUST first create the receiver rows: (1) ensure the playlist exists — `to.setPlaylistMeta(toP, { playlistUrl, playlistTitle })` (idempotent upsert on `owner_id,playlist_key`); (2) if `to.readIndex(toP)` does NOT already contain `video.id`, `return await to.claimVideoSlot(toP, video.id)` to create the reservation row; if the row already exists, return `null`. (`claim_video_slot` inserts with `on conflict (playlist_id, video_id) do nothing` — a repeat call on an existing row yields no/uninformative `position`/`serialNumber`, so guard the claim behind the readIndex-absence check to only claim a genuinely new slot; single-run/no-concurrency makes the absence check authoritative.) Backend-uniform (local `setPlaylistMeta`/`claimVideoSlot` also exist). **The claimed `{ position, serialNumber }` are the RECEIVER's replica-local ordering (§4.1 — `position`/`serialNumber`/`playlistIndex` are replica-local, NOT synced); `copyAdditiveVideo` sets them on the sanitized record instead of carrying the sender's.** Without this, a local-only playlist/video published to cloud no-ops and the MD blob is orphaned.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1960:  1. `const slot = await ensureReceiverSlot(to, toP, playlistMeta, video)` — the receiver playlist+video row now exists; `slot` (if non-null) is the receiver's replica-local `{position, serialNumber}`.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1963:  4. **Verify** `to.readIndex(toP)` now contains `video.id` — the caller writes the baseline ONLY after this confirms the receiver row exists (round-4 H1 — never advance a manifest baseline for a copy that silently no-op'd).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1974:- **`companionTransfer(deps, winnerSide, loserSide, winnerMdHash, video): Promise<{ shareNeedsOwnerServe: boolean }>`** (Behavior #5) — read the winner's `ModelEnvelope` (`readModelEnvelope`), call `decideCompanion({ winnerMdHash, senderEnvelope })`; on `ship` write the envelope to the loser's blob; on `deleteReceiverModel` delete the loser's model blob (best-effort, OUTSIDE the atomic commit) and return `shareNeedsOwnerServe:true`.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1983:    mergedFields: 0, conflictsLogged: 0, removed: 0, shareNeedsOwnerServe: 0, needsRegen: 0,
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2019:            // listPlaylists PlaylistSummary) — needed so ensureReceiverSlot can create the playlist row.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2020:            const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2051:          if ((await companionTransfer(/* winner→loser */)).shareNeedsOwnerServe) report.shareNeedsOwnerServe++;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2067:The `readVideo`, `enumerateVideoIds`, `EMPTY_CLASSB`, and presence/delete block are straightforward given `readIndex`; implement them fully (no `// ...` left in the shipped code). The transfer helper is the one place that must name and reuse the real `consistency.ts` staged→promote primitives — verify them under a user session (see the RLS note above).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2213:| 7 | Synced+shared, model deleted → anon share not-ready until owner serve, counted | `report.shareNeedsOwnerServe >= 1` |
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2221:| 15 | Additive publish CREATES the receiver row (not silent no-op) | local-only playlist+video published to a cloud with no such playlist | after sync, `cloud.readIndex` contains the playlist + video (ensureReceiverSlot ran); baseline written only after that; re-run does NOT read it as a delete (round-4 H1) |
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2240:  const local = (await ctx.local.readIndex(ctx.localPrincipal)).videos.find((v) => v.id === ctx.videoId)!;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2313:- **High (Codex H1):** additive publish never created the receiver cloud row → silent no-op → orphaned blob + false baseline → next-run mis-read as delete. Fixed: **`ensureReceiverSlot`** (idempotent `setPlaylistMeta` + guarded `claimVideoSlot`) creates the receiver playlist+video row first; `copyAdditiveVideo` **verifies `readIndex` contains the video before the baseline is written**; receiver-claimed `position`/`serialNumber` used (replica-local §4.1). T14 rows 15/16.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2323:- **High (both):** a fresh-device cloud→local hydrate throws because nothing creates the local root directory before local `readIndex`/`setPlaylistMeta` touch it (`index-store.ts:70-78,83-96`) — breaking the spec §7 fresh-device pull. Fixed: **`ensureHydrationRoot(dataRoot)`** (`mkdir -p`) called at the top of the per-playlist loop, before `readManifest`/`enumerateVideoIds`. T14 row 17 requires a genuinely non-existent root so the mkdir path is actually exercised (both reviewers warned a pre-created harness dir would mask it).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2324:- **Low:** `claimVideoSlot` wording corrected (`on conflict do nothing`, guard still correct — Codex L1); `ensureReceiverSlot`-returns-null fallback documented (keep receiver's existing ordering — Claude L1).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2326:Both reviewers verified clean: presence-branch tuple direction, `playlistMetaFor` both directions, `baselineFromOneSided`, counter semantics, money path, `readManifest` degrade-on-missing-root. This was a concrete agreed one-line fix, not a design fork — no human decision required.
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:36:  readIndex(p: Principal): Promise<PlaylistIndex>;
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:37:  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:177:/** The exact shape lib/index-store.readIndex returns for an absent index file,
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:210:Reference — current local reconcile/serial logic to preserve: `lib/pipeline.ts:388-398` (membership archive/restore), `lib/pipeline.ts:317` (`nextSerial(readIndex().videos)`), `lib/serial-*.ts` (`nextSerial`).
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:223:test('readIndex on an empty folder returns the empty index shape', async () => {
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:225:  await expect(store.readIndex(p)).resolves.toEqual({ playlistUrl: '', outputFolder: p.indexKey, videos: [] });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:230:  await store.setPlaylistMeta(p, { playlistUrl: 'https://youtube.com/playlist?list=X' });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:242:  const idx = await store.readIndex(p);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:251:  const idx = await store.readIndex(p);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:270:  readIndex(p: Principal): Promise<PlaylistIndex>;
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:271:  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:292:  async readIndex(p: Principal): Promise<PlaylistIndex> {
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:293:    return indexStore.readIndex(p.indexKey);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:295:  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:296:    const idx = indexStore.readIndex(p.indexKey);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:305:    const idx = indexStore.readIndex(p.indexKey);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:323:    const idx = indexStore.readIndex(p.indexKey);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:368:- Every `store.readIndex(principal)` → `await store.readIndex(principal)`; propagate `async` up each call chain.
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:369:- `store.writeIndex(principal, {...existing, playlistUrl, outputFolder, ...title})` (`pipeline:284`, `backfill-titles:36`) → `await store.setPlaylistMeta(principal, { playlistUrl, playlistTitle })`. In `backfill-titles`, read `playlistUrl` from the already-loaded index and pass it.
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:390:    readIndex: (p) => wrap(() => inner.readIndex(p)),
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:391:    setPlaylistMeta: (p, m) => wrap(() => inner.setPlaylistMeta(p, m)),
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:426:  const idx = readIndexFromDisk(outputFolder);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:434:  await runPipeline(/* args */); const first = readIndexFromDisk(outputFolder).videos.length;
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:435:  await runPipeline(/* same args */); const second = readIndexFromDisk(outputFolder).videos.length;
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:730:>   readIndex = NI as MetadataStore['readIndex'];
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:731:>   setPlaylistMeta = NI as MetadataStore['setPlaylistMeta'];
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:923:test('readIndex returns emptyPlaylistIndex when no playlist row', async () => {
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:926:  const idx = await store.readIndex(localPrincipal('listX'));
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:938:test('setPlaylistMeta upserts on (owner_id, playlist_key)', async () => { /* ... */ });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:961:  async readIndex(p: Principal): Promise<PlaylistIndex> {
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:975:  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1176:Setup per test: `newUser()` → `signInAs()` → `new SupabaseMetadataStore(client)`; seed a playlist via `setPlaylistMeta`.
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1193:  await expect(s.readIndex(P)).resolves.toEqual({ playlistUrl: '', outputFolder: 'listX', videos: [] });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1196:test('setPlaylistMeta create then update; claimVideoSlot allocates position+serial; readIndex round-trips', async () => {
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1198:  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX', playlistTitle: 'T' });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1202:  const idx = await s.readIndex(P);
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1211:  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1217:  const cur = (await s.readIndex(P)).videos[0];
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1219:  const after = (await s.readIndex(P)).videos[0];
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1227:  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1232:  const v = (await s.readIndex(P)).videos[0] as any;
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1241:  await a.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1244:  await expect(b.readIndex(P)).resolves.toEqual({ playlistUrl: '', outputFolder: 'listX', videos: [] }); // B sees nothing
docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md:1338:  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listConc' });
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:320:- Consumes: `readIndex` (`lib/index-store`), `CURRENT_DOC_VERSION`, `CURRENT_DEEP_DIVE_VERSION`, `fs`, `path`.
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:330:// MUST root the temp dir under $HOME — auditTimestamps → readIndex → assertOutputFolder
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:383:import { readIndex } from './index-store';
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:415:  const { videos } = readIndex(folder);
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:498:- Consumes: `auditTimestamps`, `countLeadingTimestamps` (Task 3); `ensureHtmlDoc` (forced), `ensureDeepDiveHtml` (forced) (Task 2); `readIndex` (re-read md path after re-gen).
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:549:(Note the `ensureHtmlDoc` call passes `undefined` for `current` so the default `CURRENT_DOC_VERSION` applies; `true` is `force`. `readIndex` is intentionally NOT mocked — `tsCount` (Step 3) catches its throw on the synthetic folder `'f'` and returns 0, so the run-path tests reach the mocked `ensure*` calls and assert on them, not on before/after deltas.)
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:558:import { readIndex } from './index-store';
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:573:// batch (and in unit tests, where ensure* is mocked, readIndex on a synthetic folder will throw).
docs/superpowers/plans/2026-06-23-timestamp-guard-audit-repair.md:576:    const v = readIndex(folder).videos.find((x) => x.id === id);
docs/superpowers/plans/2026-06-30-summary-truncation-resilience-stage1.md:229:- Consumes: `readIndex` (index-store), `checkSummaryCompleteness` (Task 1).
docs/superpowers/plans/2026-06-30-summary-truncation-resilience-stage1.md:249:- [ ] **Step 3: Implement** (`lib/summary-audit.ts`) — iterate `readIndex(folder).videos`; for each with `summaryMd`, read the file (missing → suspect `reason:'md-missing'`), else run `checkSummaryCompleteness`; push suspects. **Serial from the index record (`v.serialNumber`), NOT filename** (Codex BLOCKING). Never throws per-file.
docs/superpowers/plans/2026-06-30-summary-truncation-resilience-stage1.md:254:import { readIndex } from './index-store';
docs/superpowers/plans/2026-06-30-summary-truncation-resilience-stage1.md:263:  const { videos } = readIndex(folder);
docs/superpowers/plans/2026-06-09-deep-dive-html-export.md:350:import { assertOutputFolder, assertVideoId, readIndex } from '../index-store';
docs/superpowers/plans/2026-06-09-deep-dive-html-export.md:362:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-09-deep-dive-html-export.md:513:import { assertOutputFolder, assertVideoId, readIndex } from '../../../../lib/index-store';
docs/superpowers/plans/2026-06-09-deep-dive-html-export.md:544:    const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-09-deep-dive-html-export.md:770:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:17:- **`assertOutputFolder` / `assertVideoId` stay** as shared local validation primitives (they are inherently local-FS/format guards). Only the four data-access functions (`readIndex`, `writeIndex`, `upsertVideo`, `updateVideoFields`) move behind the contract.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:39:**Out of scope for Part 1 — `scripts/`:** `scripts/backfill-serial-prefix.ts` **does** call `readIndex` directly (Codex correction — it is a data-access consumer, not guard-only). Scripts cannot use the `@/*` alias at runtime (they run via ts-node with relative imports), so rerouting them requires a relative-import strategy for `lib/storage/*`. Defer all of `scripts/` to a dedicated follow-up task; Part 1 covers only `app/` + `lib/` runtime consumers. The Task 8 completeness check whitelists `scripts/` accordingly.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:119:- Produces: `interface MetadataStore` with methods `readIndex(p: Principal): PlaylistIndex`, `writeIndex(p: Principal, index: PlaylistIndex): void`, `upsertVideo(p: Principal, video: Video): void`, `updateVideoFields(p: Principal, id: string, fields: Partial<Video>): void`.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:131:  readIndex(principal: Principal): PlaylistIndex;
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:159:- Consumes: `MetadataStore` (Task 2), `Principal` (Task 1), and `readIndex`/`writeIndex`/`upsertVideo`/`updateVideoFields` from `@/lib/index-store`.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:172:import { readIndex } from '@/lib/index-store';
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:190:it('writeIndex then readIndex round-trips through the store', () => {
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:196:  expect(localMetadataStore.readIndex(p).videos).toHaveLength(1);
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:199:it('upsertVideo is observable via direct index-store readIndex (byte-identical persistence)', () => {
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:201:  const viaDirect = readIndex(TEST_DIR); // same file the store wrote
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:207:  const v = localMetadataStore.readIndex(p).videos.find((x) => x.id === 'vid00000002');
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:229:  readIndex(principal: Principal): PlaylistIndex {
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:230:    return indexStore.readIndex(principal.outputFolder);
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:271:**Note:** centralizing the guard in `getPrincipal` preserves today's behavior — consumers currently call `assertOutputFolder(of)` then `readIndex(of)`; after rerouting they call `getPrincipal(of)` (which guards) then `store.readIndex(principal)`.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:359:**Canonical transformation** (apply to each `readIndex`/`writeIndex`/`upsertVideo`/`updateVideoFields` call; leave `assertOutputFolder`/`assertVideoId` imports and calls untouched):
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:363:import { assertOutputFolder, assertVideoId, upsertVideo, readIndex, writeIndex } from '@/lib/index-store';
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:366:const index = readIndex(outputFolder);
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:376:const index = store.readIndex(principal);
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:385:Replace its `upsertVideo`/`readIndex`/`writeIndex` calls per the canonical transform. `pipeline.ts` receives `outputFolder` and already calls `assertOutputFolder` — replace that call with `const principal = getPrincipal(outputFolder)` and thread `principal` + `getMetadataStore()` through the ingestion loop. Keep `assertVideoId` calls as-is.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:389:`archiveVideo`/`unarchiveVideo` receive `outputFolder`. Replace their `readIndex`/`updateVideoFields` (via `updateIndexIfKnown`) calls with the store. `updateIndexIfKnown` becomes: `getMetadataStore().updateVideoFields(getPrincipal(outputFolder), videoId, fields)` — but resolve the principal once at the top of each exported function and pass it down to the helpers to avoid repeated guard calls. Keep all path-containment logic and `assertOutputFolder`/`assertVideoId` intact.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:393:Replace its `readIndex`/`updateVideoFields` calls with the store (`getPrincipal(outputFolder)` at entry, then `store.readIndex(principal)` / `store.updateVideoFields(principal, id, fields)`).
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:420:Apply the **canonical transformation from Task 5** to each file's `readIndex`/`writeIndex`/`updateVideoFields` calls. Per-file specifics (imported symbols to reroute, from the consumer map):
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:422:- [ ] **Step 1: html-doc modules** — `generate.ts` (`readIndex`, `updateVideoFields`), `ensure.ts` (`readIndex`, `updateVideoFields`), `batch.ts` (`readIndex`), `rerender.ts` (`readIndex`). Each already calls `assertOutputFolder`/`assertVideoId`; replace the guard call with `getPrincipal` and thread the principal + store.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:424:- [ ] **Step 2: migration/backfill** — `serial-migrate-exec.ts` (`readIndex`, `writeIndex`, `updateVideoFields`): `getPrincipal(outputFolder)` at entry, thread the principal. **`backfill-titles.ts` is per-child-folder, NOT per-root (Codex High):** it receives `root` and iterates discovered playlist folders, doing `readIndex(folder)`/`writeIndex(folder, …)` per child. Keep the entry guard on `root` if present, but build a **separate principal per discovered `folder`** immediately before each access: `const p = getPrincipal(folder); const idx = store.readIndex(p); …; store.writeIndex(p, idx);` inside the iteration. Do **not** hoist one `root` principal across children.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:426:- [ ] **Step 3: read-only audits** — `timestamp-repair.ts`, `timestamp-audit.ts`, `summary-audit.ts` (each `readIndex` only). Per the single rule, use `getPrincipal(folder)` + `getMetadataStore().readIndex(principal)` (the added home-dir guard is idempotent and never triggers in practice, and is forward-consistent — see the Single-rule note in Task 5; do **not** use bare `localPrincipal`).
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:453:Apply the **canonical transformation** to each route's `readIndex`/`updateVideoFields` calls. Each route currently does `assertOutputFolder(outputFolder)` (+ `assertVideoId(id)`) then `readIndex(outputFolder)`; convert the `assertOutputFolder` call into `const principal = getPrincipal(outputFolder)`, keep `assertVideoId(id)`, and use `getMetadataStore()` for data access.
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:457:- [ ] **Step 1: Reroute the read-only routes** — `html/[id]`, `videos/route`, `videos/[id]/pdf`, `videos/[id]/dig-state`, `videos/[id]/quick-view` (each `readIndex` only, plus their existing `assertVideoId`).
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:459:- [ ] **Step 2: Reroute the read+write routes** — `videos/[id]/regenerate` (`readIndex` + `updateVideoFields`), `videos/[id]/review` (`updateVideoFields`), `quick-view/backfill` (`readIndex` + `updateVideoFields`).
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:464:Expected: PASS — unchanged counts. (Tests that `jest.mock('../../lib/index-store')` still work because the local store delegates to those same mocked functions; if any test mocked `readIndex` directly and asserts the route called it, it still passes since the store forwards to it. If a test breaks because it mocked at the wrong layer, update the mock to target `@/lib/storage/resolve`'s `getMetadataStore` — see note below.)
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:486:Run: `rg -n "\b(readIndex|writeIndex|upsertVideo|updateVideoFields)\b" app lib`
docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:519:**Type consistency:** `Principal { id, outputFolder }`, `MetadataStore.readIndex/writeIndex/upsertVideo/updateVideoFields`, `getPrincipal`/`getMetadataStore`, `localPrincipal`, `localMetadataStore` used identically across Tasks 1–7. `PlaylistIndex`/`Video` sourced from `@/types` (verified exported). ✓
docs/superpowers/specs/2026-06-23-playlist-index-current-position-design.md:47:Unit test the re-stamp pass (the `videosWithIndex` mapping at `pipeline.ts:387-393`). **Mocking boundary:** mock `lib/youtube` (`fetchPlaylistVideos`) AND `lib/index-store` (`readIndex`/`writeIndex`/`upsertVideo`) — the re-stamp pass reads `readIndex(outputFolder)`, so the stale `playlistIndex` must be seeded through `index-store`, and the seeded video must be already-indexed so it is skipped in the main loop and corrected **only** by the re-stamp pass (the proof we're testing the right path). Follow the existing pattern at `tests/lib/pipeline.test.ts:369`.
docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md:82:- Consumes: `fetchPlaylistTitleOrNull` (T1), `extractPlaylistId` (already imported), `metadataStore.setPlaylistMeta`.
docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md:88:| 1 | Persists real title | fetch returns "My List" | `setPlaylistMeta(principal,{playlistUrl, playlistTitle:'My List'})` called |
docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md:89:| 2 | No fake title on miss | fetch returns null | `setPlaylistMeta` NOT called (row stays null) |
docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md:94:- [ ] **Step 1:** Write failing tests. Arrange `enqueuePlaylist` with mocked `sessionBundle.metadataStore` (`resolvePlaylistId` returns an id, `setPlaylistMeta` a spy), mocked enqueuer, and `lib/youtube` (`fetchPlaylistTitleOrNull` variants), `YOUTUBE_API_KEY` set. Assert the spy per behaviors 1–3.
docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md:96:- [ ] **Step 3:** Implement the §A1 block: `try { const listId = extractPlaylistId(playlistUrl); const t = await fetchPlaylistTitleOrNull(listId, apiKey); if (t) await sessionBundle.metadataStore.setPlaylistMeta(principal, { playlistUrl, playlistTitle: t }); } catch { /* leave null */ }` placed immediately after the `resolvePlaylistId` call.
docs/superpowers/plans/2026-07-08-stage-1e-c-progress-polling.md:636:In `lib/storage/supabase/supabase-metadata-store.ts`, add (near the existing `setPlaylistMeta`):
docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:50:| D15 | **Confused-deputy guard:** resolve the doc by the **global** `playlist_id AND owner_id` (never `readIndex`, which keys on per-owner-unique `playlist_key`), and **assert the resolved `owner_id` equals the token row's**. | Mirrors `getWorkerStorageBundle` (`resolve.ts:71`). The `videos(playlist_id, owner_id)` composite FK (`0001`) already forbids a video's owner differing from its playlist's — the assert is belt-and-suspenders. |
docs/superpowers/plans/2026-06-30-playlist-picker.md:170:import { readIndex } from '../../lib/index-store';
docs/superpowers/plans/2026-06-30-playlist-picker.md:180:  expect(readIndex(dir).playlistTitle).toBe('Building with Claude');
docs/superpowers/plans/2026-06-30-playlist-picker.md:186:  expect(readIndex(dir).playlistTitle).toBeUndefined();
docs/superpowers/plans/2026-06-30-playlist-picker.md:209:  const existing = readIndex(outputFolder);
docs/superpowers/plans/2026-06-30-playlist-picker.md:731:- Consumes: `readIndex`/`writeIndex`/`assertOutputFolder` (`lib/index-store.ts`), `fetchPlaylistTitle` (`lib/youtube.ts`).
docs/superpowers/plans/2026-06-30-playlist-picker.md:777:import { readIndex, writeIndex, assertOutputFolder } from '../index-store';
docs/superpowers/plans/2026-06-30-playlist-picker.md:803:    try { index = readIndex(folder); } catch { failed.push(folder); continue; }
docs/superpowers/plans/2026-06-30-playlist-picker.md:857:The route currently ends: `return NextResponse.json({ videos, playlistUrl: index.playlistUrl });`. The test file already `jest.mock('../../lib/index-store')` and exposes `mockReadIndex = jest.mocked(indexStore.readIndex)`.
docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:77:| D6 | **Ownership via RLS + an explicit `owner_id === auth.uid()` assert on the *playlist* row** (during `playlistId → playlist_key` resolution). **No video-row owner assert** — `readIndex` returns only the `data` jsonb, which carries no `owner_id`, so a video-level assert is not implementable; RLS is the video-level backstop. | The playlist-level assert is implementable and cheap; RLS is the real per-row enforcement on the session path. |
docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:109:   session-scoped, RLS-enforced. `metadataStore.readIndex(principal)` → find video by
docs/superpowers/plans/2026-05-28-pdf-subfolder.md:351:function readIndex(folder: string): { videos: Array<{ summaryPdf?: string | null; deepDivePdf?: string | null }> } {
docs/superpowers/plans/2026-05-28-pdf-subfolder.md:369:    expect(readIndex(dir).videos[0].summaryPdf).toBe('pdfs/my-video.pdf');
docs/superpowers/plans/2026-05-28-pdf-subfolder.md:379:    expect(readIndex(dir).videos[0].deepDivePdf).toBe('pdfs/my-video-deep-dive.pdf');
docs/superpowers/plans/2026-05-28-pdf-subfolder.md:391:    expect(readIndex(dir).videos[0].summaryPdf).toBe('pdfs/my-video.pdf');
docs/superpowers/plans/2026-05-28-pdf-subfolder.md:401:    expect(readIndex(dir).videos[0].summaryPdf).toBe('pdfs/ghost.pdf');
docs/superpowers/plans/2026-06-20-deep-dive-version-aware-regeneration.md:390:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-20-deep-dive-version-aware-regeneration.md:558:import { assertOutputFolder, assertVideoId, readIndex, updateVideoFields } from '../index-store';
docs/superpowers/plans/2026-06-20-deep-dive-version-aware-regeneration.md:575:  const video = readIndex(outputFolder).videos.find((v) => v.id === videoId);
docs/superpowers/plans/2026-07-01-auto-pdf-export.md:428:import { assertOutputFolder, assertVideoId, readIndex } from '.../lib/index-store';
docs/superpowers/plans/2026-07-01-auto-pdf-export.md:439:// 400 unless 'summary'|'dig-deeper'; readIndex + find video → 404 if absent.
docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md:116:| A4 | `GET /api/videos` cloud branch | `app/api/videos/route.ts` | Refactor to serveLocal/serveCloud. Cloud: `?playlist=<uuid>` → `readIndex` → reuse `sortVideos`. **Skip** `recoverOrphanedVideos` (filesystem). Validate `sortColumn` (existing whitelist) **and** `sortOrder ∈ {asc,desc}` (default `asc`). Reject `outputFolder` param in cloud (400). |
docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md:117:| A5 | `GET /api/videos/[id]/quick-view` cloud branch | `app/api/videos/[id]/quick-view/route.ts` | Cloud: `?playlist=<uuid>` → `readIndex` → the one video's `{ tldr, takeaways, tags }`. **Match the local availability gate: 404 unless `video.summaryMd && video.tldr`** (parity with `quick-view route:27`). |
docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md:174:  - **`readIndex` surfaces it:** select `updated_at` and map it into the returned `Video.updatedAt` (today `readIndex` selects only `data`, `supabase-metadata-store.ts:22`). Add `updatedAt?: string` to `VideoSchema`.
docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md:190:`listPlaylists`, `readIndex`-backed reads, and the review/archive writes run on the **session** client only (RLS-scoped, `owner_id = auth.uid()`), with `resolveOwnedPlaylistKey` asserting ownership. Rationale: `playlist_key` is unique only **per owner** (`resolve.ts:66` warns service-role workers must resolve by UUID). Passing a service client to `SupabaseMetadataStore` for these paths would bypass RLS and could cross owners on a colliding `playlist_key`. Acceptance: documented invariant + a cross-owner-denial test per route (§12).
docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md:39:**Files:** Create `supabase/migrations/0015_video_updated_at_trigger.sql`; Modify `types/index.ts`, `lib/storage/supabase/supabase-metadata-store.ts` (`readIndex`); Test `tests/integration/video-updated-at.test.ts`, `tests/lib/types.test.ts`.
docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md:40:**Interfaces — Produces:** `Video.updatedAt?: string` (ISO); `readIndex` populates it from the DB column.
docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md:41:- [ ] **Step 1 (RED):** `tests/integration/video-updated-at.test.ts` (set `STORAGE_BACKEND='supabase'` in `beforeAll`, seed via admin client): after a `merge_video_data` write AND a direct `.update({data})` (upsert path, no explicit `updated_at`), assert `videos.updated_at` advanced both times; and `readIndex` returns `video.updatedAt === updated_at`.
docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md:53:- [ ] **Step 4:** `readIndex`: change videos select `.select('data')` → `.select('data, updated_at')`; map `{ ...(r.data as Video), updatedAt: r.updated_at }`. Add `updatedAt: z.string().datetime().optional()` to `VideoSchema`.
docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md:98:- [ ] **Step 3:** Refactor into `serveLocal(request)` (current body verbatim) and `serveCloud(request)`. Cloud follows the Global-Constraints route flow (getUser → UUID_RE → resolveOwnedPlaylistKey → getPrincipalFromSession → getStorageBundle) → `readIndex` → reuse `sortVideos` (validate `sortColumn` via the existing whitelist AND `sortOrder ∈ {asc,desc}`) → return `{ videos, playlistUrl: index.playlistUrl, playlistTitle: index.playlistTitle }`. Do NOT call `recoverOrphanedVideos`. Reject `outputFolder` (400).
docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md:105:- [ ] **Step 3:** Cloud branch (full route flow) → `readIndex` → find the video → apply `summaryMd && tldr` gate (404 else the three fields).
docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md:39:| Title persist fn: `setPlaylistMeta(p, {playlistUrl, playlistTitle?})` upsert on `(owner_id, playlist_key)` | `supabase-metadata-store.ts:65` |
docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md:93:  if (playlistTitle) await sessionBundle.metadataStore.setPlaylistMeta(principal, { playlistUrl, playlistTitle });
docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md:100:- `setPlaylistMeta` upserts on `(owner_id, playlist_key)`, so it updates the row `resolvePlaylistId`
docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md:120:**Conditional persist (review M-race, Codex M2 + Claude M1):** do **not** use the `setPlaylistMeta`
docs/superpowers/specs/2026-07-02-stage-1b-auth-rls-schema-design.md:25:**Prerequisite for 1C, NOT 1B (Codex re-review, new):** the `MetadataStore` contract is currently **synchronous** (`readIndex(principal): PlaylistIndex`), which suited the local `fs.readFileSync` store but a **networked Supabase adapter cannot honor**. Before 1C, a dedicated task must **async-ify the seam**: `MetadataStore` methods return `Promise`, `LocalFsMetadataStore` wraps its sync calls, and the ~20 consumers `await`. This does not block 1B (schema + auth), but §5.5's semantics below describe the *async* adapter behavior. Flagged here so 1C is not attempted on a sync interface.
docs/superpowers/specs/2026-07-02-stage-1b-auth-rls-schema-design.md:151:- **`readIndex(principal)`** → select the `playlists` row `(owner_id=principal.id, playlist_key=principal.outputFolder)` + its `videos` `ORDER BY position`; assemble `{ playlistUrl, playlistTitle, outputFolder: principal.outputFolder, videos: rows.map(r=>r.data) }`. **If no playlist row exists → return exactly `{ playlistUrl: '', outputFolder: principal.outputFolder, videos: [] }`** — byte-identical to the local store's ENOENT branch (`lib/index-store.ts`), which returns `playlistUrl: ''` and **does not Zod-validate on read**. The cloud store likewise does not `PlaylistIndexSchema.parse()` on read, so the empty `playlistUrl` is fine (Codex H1 re-review: the schema's `.url()` is never applied on the read path — parity with local). Never null, never throws for absent.
docs/superpowers/specs/2026-07-14-cloud-dig-serving-design.md:80:Cloud branch: `?playlist={uuid}` required (UUID-validated) → auth (`getUser`, 401 anon) → `assertVideoId` → owner-assert + gate (reuse the same `resolveOwnedPlaylistKey` + `readIndex` + `base` derivation as the loader; factor the shared prefix out of Unit A so both use it) → list `dig/{base}/` current-version blobs → `{ sectionIds: number[] }` sorted **ascending** by `startSec` (== sectionId). Zero dug → `{ sectionIds: [] }` (**200**, not 404 — lets the frontend distinguish "nothing dug" from an error).
docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md:72:- **Stage 1 — `loadSummaryForServe(...)`** (gate + read): auth → owner playlist → readIndex →
docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md:175:   `resolveOwnedPlaylistKey` → null → **404**; `readIndex` (session-client, RLS), find video →
docs/superpowers/specs/2026-06-23-summary-deepdive-navigation-design.md:23:- `hasDeepDive`/`hasSummary` come from the render driver (which has the `Video` from `readIndex`): pass `!!video.deepDiveMd` / `!!video.summaryMd`.
tests/api/regenerate.test.ts:21:const mockReadIndex = jest.mocked(indexStore.readIndex);
docs/superpowers/plans/2026-05-28-date-columns.md:403:  const afterReconcile = readIndex(outputFolder);
lib/timestamp-audit.ts:36:  const { videos } = await store.readIndex(principal);
docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:18:- **Confused-deputy guard (D15):** resolve the doc by global `playlist_id AND owner_id` (never `readIndex`, which keys on per-owner-unique `playlist_key`) and assert the resolved `owner_id` equals the token row's. Copy `getWorkerStorageBundle` (`lib/storage/resolve.ts:71`).
lib/summary-audit.ts:19:  const { videos } = await store.readIndex(principal);
tests/lib/index-store.test.ts:5:import { readIndex, updateVideoFields, upsertVideo, writeIndex } from '../../lib/index-store';
tests/lib/index-store.test.ts:30:describe('readIndex', () => {
tests/lib/index-store.test.ts:35:    const result = readIndex(dir);
tests/lib/index-store.test.ts:42:    expect(() => readIndex('/etc')).toThrow(expect.objectContaining({ statusCode: 400 }));
tests/lib/index-store.test.ts:66:    const result = readIndex(dir);
tests/lib/index-store.test.ts:80:describe('writeIndex + readIndex', () => {
tests/lib/index-store.test.ts:92:    const result = readIndex(dir);
tests/lib/index-store.test.ts:106:    const result = readIndex(dir);
tests/lib/index-store.test.ts:124:    const result = readIndex(dir);
tests/lib/index-store.test.ts:164:    const result = readIndex(dir);
tests/lib/index-store.test.ts:180:    const result = readIndex(dir);
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:25:1. `summaryReady?: boolean` — derived, added to the shared `VideoSchema` as `.optional()` and populated **only** in the cloud store mapping (`SupabaseMetadataStore.readIndex`); local path never sets it. (Task 2)
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:36:- `lib/storage/supabase/supabase-metadata-store.ts` *(modify)* — derive `summaryReady` in `readIndex` mapping.
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:234:- Modify: `lib/storage/supabase/supabase-metadata-store.ts` — `readIndex` mapping (~`:45`) AND `stripComputed` (~`:14`)
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:238:- Consumes: `VideoSchema` / `type Video` (`types/index.ts:47-83`); `readIndex` mapping in `SupabaseMetadataStore` (`lib/storage/supabase/supabase-metadata-store.ts:25-47`), which already derives the cloud-only `updatedAt` at `:45`.
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:241:**Context the brief cannot know:** `artifacts` is NOT a typed field on `VideoSchema` — it lives only in the DB `videos.data` jsonb and is read via ad-hoc casts (`app/api/html/[id]/route.ts:55`, `lib/share/serve.ts:44`). The canonical readiness predicate `artifacts.summaryMd.status === 'promoted'` is used at those sites + `lib/job-queue/summary-handler.ts:87`. `BlobStatus` = `'pending' | 'committed' | 'promoted' | 'repair_needed'` (`lib/storage/blob-store.ts:3`). serveLocal (`app/api/videos/route.ts:94-128`) and serveCloud (`:134-176`) are separate functions but share the `Video` type via `sortVideos`; the local store (`LocalMetadataStore.readIndex`) has no `artifacts`, so making the field `.optional()` and deriving it only cloud-side leaves local `undefined` — identical to the `updatedAt` precedent.
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:243:**Invariant to preserve (Claude M2 — REQUIRED):** `summaryReady` is a **read-computed** key exactly like `updatedAt` — derived from the DB row on read, never a source-of-truth field in `videos.data`. `stripComputed<T>(v)` (`supabase-metadata-store.ts:14`) strips `updatedAt` before **every** write to `videos.data` (it guards `upsertVideo`, `updateVideoFields`, `bulkUpdateVideoFields`) precisely so a read-surfaced computed key can never round-trip into the jsonb. `summaryReady` **must be added to `stripComputed`** too. No current caller round-trips a `readIndex`-sourced `Video` back to a write, so nothing breaks today — but omitting it silently breaks the stated invariant and risks a future write baking a stale `summaryReady` into `videos.data` (where the serving route would then read a lie). This is a required step, not optional polish.
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:247:Create `tests/lib/supabase-metadata-store-summary-ready.test.ts`. Mock the Supabase client's row fetch so `readIndex` maps three rows — promoted, committed, and artifacts-absent — and assert the derived flag:
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:251:// Use the file's existing test-client mocking pattern (mirror tests already covering readIndex,
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:258:// ...wire rows into the mocked client, call store.readIndex(principal)...
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:264:> **Implementer note:** reuse the exact client-mock helper already used by the sibling `readIndex` tests in this directory; do not invent a new mocking style. The `data` objects must be valid `Video` shapes so any Zod parse in the path passes — copy a fixture from an existing store test.
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:323:- [ ] **Step 7: Migrate existing exact-shape `readIndex` assertions (Codex R2-H2 — REQUIRED)**
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:338:Update every exact-shape `readIndex` assertion the grep finds the same way (add `summaryReady: false`, or `true` if that fixture's `data.artifacts.summaryMd.status === 'promoted'`). Do NOT weaken a `toEqual` to `toMatchObject` to dodge it — the point is that the shape genuinely changed.
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:1055:- Consumes: the real Supabase test harness (`signInAs` / session-client helpers used by existing `tests/integration/share-tokens-rpc.test.ts` and the 2b `jobs-poll-banner.test.ts`); `SupabaseMetadataStore.readIndex` (Task 2); `create_share_token` / `revoke_share_token` RPCs via each user's session client.
docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:1061:3. **`summaryReady` reflection:** through `SupabaseMetadataStore.readIndex` for owner A, a video whose `artifacts.summaryMd.status === 'promoted'` yields `summaryReady === true`; a `committed` (or artifacts-absent) video yields `summaryReady === false`.
tests/lib/pipeline-playlist-title.test.ts:10:import { readIndex } from '../../lib/index-store';
tests/lib/pipeline-playlist-title.test.ts:27:  expect(readIndex(dir).playlistTitle).toBe('Building with Claude');
tests/lib/pipeline-playlist-title.test.ts:33:  expect(readIndex(dir).playlistTitle).toBeUndefined();
docs/superpowers/plans/2026-06-24-section-dig-deeper-screenshots.md:523:> **B-3 note:** a plain write→read round-trip will NOT fail before the change — `readIndex` does `JSON.parse` with no Zod parse, so unknown fields already survive. The RED test must exercise **`VideoSchema.parse(...)`** (or `PlaylistIndexSchema.parse`) directly, so the field is dropped/typed only after it's added to the schema.
tests/lib/serial-migrate-normalization.test.ts:11:import { readIndex, writeIndex } from '@/lib/index-store';
lib/index-store.ts:81:export function readIndex(outputFolder: string): PlaylistIndex {
lib/index-store.ts:119:  const index = readIndex(outputFolder);
lib/index-store.ts:135:  const index = readIndex(outputFolder);
tests/api/serve-summary-core.test.ts:21:        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
docs/superpowers/plans/2026-07-14-cloud-dig-serving.md:858:**Design note (review v1 H2/H3/M1):** the cloud branch **reuses `loadSummaryForServe`** rather than hand-coding owner-assert + `readIndex` + `base = mdKey.replace(/\.md$/,'')`. This (a) applies the SAME gate as the html serve path — spec §3 Unit C's "owner-assert **+ gate**" — so dig-state 503s while the summary finalizes and 404s an unknown/unpromoted video instead of leaking `200 []`; (b) guarantees `base` agreement with T3 (both use `load.base`), eliminating the divergence risk; (c) avoids the duplicate `getStorageBundle` import and the un-imported `NextResponse` (keep the file's existing `new Response(...)` idiom). Cost: one extra owner-scoped mdBytes read per dig-state call — acceptable (no frontend polls this endpoint in this slice; the poller is the deferred frontend slice).
tests/lib/job-queue/producer-title.test.ts:22: *  setPlaylistMeta spy and a shared call-order log so we can assert ordering (behavior 4). */
tests/lib/job-queue/producer-title.test.ts:26:  const setPlaylistMeta = jest.fn(async () => { order.push('setPlaylistMeta'); });
tests/lib/job-queue/producer-title.test.ts:34:  const bundle = { metadataStore: { resolvePlaylistId, setPlaylistMeta } } as any;
tests/lib/job-queue/producer-title.test.ts:35:  return { bundle, enqueuer, resolvePlaylistId, setPlaylistMeta, enqueue, order };
tests/lib/job-queue/producer-title.test.ts:43:  const { bundle, enqueuer, setPlaylistMeta, order } = fakeEnqueuer(async () => {
tests/lib/job-queue/producer-title.test.ts:51:  expect(setPlaylistMeta).toHaveBeenCalledWith(principal, { playlistUrl: URL_, playlistTitle: 'My List' });
tests/lib/job-queue/producer-title.test.ts:53:  expect(order.indexOf('resolve')).toBeLessThan(order.indexOf('setPlaylistMeta'));
tests/lib/job-queue/producer-title.test.ts:59:  const { bundle, enqueuer, setPlaylistMeta } = fakeEnqueuer(async () =>
tests/lib/job-queue/producer-title.test.ts:64:  expect(setPlaylistMeta).not.toHaveBeenCalled();
tests/lib/job-queue/producer-title.test.ts:70:  const { bundle, enqueuer, setPlaylistMeta } = fakeEnqueuer(async () =>
tests/lib/job-queue/producer-title.test.ts:77:  expect(setPlaylistMeta).not.toHaveBeenCalled();
tests/lib/job-queue/producer-title.test.ts:82:  const { bundle, enqueuer, resolvePlaylistId, setPlaylistMeta } = fakeEnqueuer(async () =>
tests/lib/job-queue/producer-title.test.ts:90:  expect(setPlaylistMeta).not.toHaveBeenCalled();
tests/api/quick-view.test.ts:6:const mockReadIndex = jest.mocked(indexStore.readIndex);
docs/superpowers/plans/2026-06-18-resummarize-with-timestamps.md:277:  (indexStore.readIndex as jest.Mock).mockReturnValue({ videos: [{ ...videoBase, ...v }] });
docs/superpowers/plans/2026-06-18-resummarize-with-timestamps.md:334:import { assertOutputFolder, assertVideoId, readIndex, updateVideoFields } from '../index-store';
docs/superpowers/plans/2026-06-18-resummarize-with-timestamps.md:358:  const video = readIndex(outputFolder).videos.find((v) => v.id === videoId);
docs/superpowers/plans/2026-05-29-quick-view.md:434:    const index = readIndex(outputFolder);
docs/superpowers/plans/2026-05-29-quick-view.md:614:const mockReadIndex = jest.mocked(indexStore.readIndex);
docs/superpowers/plans/2026-05-29-quick-view.md:720:import { assertOutputFolder, assertVideoId, readIndex } from '../../../../../lib/index-store';
docs/superpowers/plans/2026-05-29-quick-view.md:740:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-05-29-quick-view.md:801:const mockReadIndex = jest.mocked(indexStore.readIndex);
docs/superpowers/plans/2026-05-29-quick-view.md:922:import { assertOutputFolder, readIndex, updateVideoFields } from '../../../../lib/index-store';
docs/superpowers/plans/2026-05-29-quick-view.md:942:  const index = readIndex(outputFolder);
lib/dig/dig-section.ts:23:  const index = await store.readIndex(principal);
tests/lib/summary-audit.test.ts:6:// readIndex enforces outputFolder under $HOME, so the temp dir must live there.
docs/superpowers/plans/2026-07-11-cloud-summary-pdf.md:52:  `jest.mock('@/lib/storage/resolve')` (returns `{ metadataStore:{readIndex}, blobStore:{get:
docs/superpowers/plans/2026-07-11-cloud-summary-pdf.md:439:  playlist → readIndex → gate `summaryMd.status` → select mdKey → **`assertCloudSummaryMdKey`** →
docs/superpowers/plans/2026-07-11-cloud-summary-pdf.md:495:  const index = await bundle.metadataStore.readIndex(principal);
tests/lib/pipeline.test.ts:28:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/lib/pipeline.test.ts:282:    // Arrange: stateful in-memory store so the second readIndex call sees the first upserted video.
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion, type ModelRead } from '@/lib/cloud-sync/companion';
tests/lib/cloud-sync/companion.test.ts:11:  decideCompanion({ winnerMdHash: 'h1', senderModel, receiverModel });
tests/lib/cloud-sync/companion.test.ts:13:const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
tests/lib/cloud-sync/companion.test.ts:15:const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
tests/lib/cloud-sync/companion.test.ts:68:    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
tests/lib/cloud-sync/companion.test.ts:79:      const deleted = decideCompanion({ winnerMdHash: 'h1', senderModel: s, receiverModel: r }).kind === 'deleteReceiverModel';
tests/lib/serial-migrate-exec.test.ts:6:import { readIndex, writeIndex } from '@/lib/index-store';
tests/lib/serial-migrate-exec.test.ts:52:    const after = readIndex(outputFolder).videos.map((v) => v.serialNumber).sort();
tests/lib/serial-migrate-exec.test.ts:121:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
tests/lib/serial-migrate-exec.test.ts:178:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
tests/lib/serial-migrate-exec.test.ts:225:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
tests/lib/serial-migrate-exec.test.ts:248:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
tests/integration/blob-store.test.ts:172:  await meta.setPlaylistMeta(p, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/blob-store.test.ts:193:  const idx = await meta.readIndex(p);
tests/lib/producer.test.ts:7:  // bundle.metadataStore (no setPlaylistMeta here) is never touched.
tests/lib/cloud-sync/registry.test.ts:20://    so LocalPlaylist could never carry one. playlistMetaFor checks the local registry first, so a
tests/lib/cloud-sync/registry.test.ts:22://    setPlaylistMeta upsert writes as an explicit NULL, wiping the cloud row's title.
tests/api/html-serve-cloud.test.ts:26:        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
docs/superpowers/plans/2026-06-29-batch-docs-phase-a.md:49:- Consumes: `ensureHtmlDoc(videoId, outputFolder, onProgress) : Promise<void>` (`lib/html-doc/ensure.ts`); `readIndex(outputFolder)` (`lib/index-store`); `isOlder`, `CURRENT_DOC_VERSION` (`lib/doc-version`); `assertOutputFolder`, `assertVideoId` (`lib/index-store`); `ProgressEvent` (`types`).
docs/superpowers/plans/2026-06-29-batch-docs-phase-a.md:135:const mockReadIndex = jest.mocked(indexStore.readIndex);
docs/superpowers/plans/2026-06-29-batch-docs-phase-a.md:240:import { assertOutputFolder, assertVideoId, readIndex } from '../index-store';
docs/superpowers/plans/2026-06-29-batch-docs-phase-a.md:262:  const index = readIndex(outputFolder);
tests/integration/video-updated-at.test.ts:11:// asserts `updated_at` advances each time, then asserts `readIndex` (the
tests/integration/video-updated-at.test.ts:39:it('trigger bumps videos.updated_at on the merge_video_data RPC path AND the direct upsertVideo(.update) path; readIndex surfaces it as Video.updatedAt', async () => {
tests/integration/video-updated-at.test.ts:66:  // --- readIndex surfaces the column as Video.updatedAt, matching the DB value exactly. ---
tests/integration/video-updated-at.test.ts:67:  const index = await bundle.metadataStore.readIndex(principal);
tests/integration/backfill-titles.test.ts:23:    await store.setPlaylistMeta(P, {
tests/integration/backfill-titles.test.ts:31:    const idx = await store.readIndex(P);
tests/integration/backfill-titles.test.ts:37:    await store.setPlaylistMeta(P, {
tests/integration/backfill-titles.test.ts:45:    const idx = await store.readIndex(P);
tests/integration/backfill-titles.test.ts:51:    await storeA.setPlaylistMeta(P, {
tests/integration/backfill-titles.test.ts:62:    const idxA = await storeA.readIndex(P);
tests/lib/archive.test.ts:2:import { upsertVideo, readIndex } from '../../lib/index-store';
tests/lib/archive.test.ts:81:    const index = readIndex(outputFolder);
tests/lib/archive.test.ts:134:    const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-22-sync-progress-print-export.md:180:(Wire the index/playlist fixtures the same way the existing pipeline tests do — seed `readIndex` with the already-indexed id and `fetchPlaylistVideos` with the playlist metas.)
tests/lib/pipeline-async.test.ts:37:    const idx = await store.readIndex(principal);
tests/lib/pipeline-async.test.ts:42:    const pendingPromise = store.readIndex(principal);
tests/lib/index-store-updated-at.test.ts:5:import { readIndex, updateVideoFields, upsertVideo } from '../../lib/index-store';
tests/lib/index-store-updated-at.test.ts:39:    const before = readIndex(dir);
tests/lib/index-store-updated-at.test.ts:45:    const result = readIndex(dir);
tests/lib/index-store-updated-at.test.ts:70:    const before = readIndex(dir);
tests/lib/index-store-updated-at.test.ts:77:    const result = readIndex(dir);
tests/lib/cloud-sync/regenerate-stamp.test.ts:29:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/pdf-serve-cloud.test.ts:24:        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
tests/lib/html-doc/batch.test.ts:20:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/lib/cloud-sync/model-writer-hash.test.ts:6:// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
docs/superpowers/plans/2026-06-29-batch-docs-phase-b-dig.md:83:  jest.mocked(indexStore.readIndex).mockReturnValue({ playlistUrl: '', outputFolder: OF, videos: [video] } as any);
docs/superpowers/plans/2026-06-29-batch-docs-phase-b-dig.md:127:import { readIndex, updateVideoFields } from '@/lib/index-store';
docs/superpowers/plans/2026-06-29-batch-docs-phase-b-dig.md:151:In `app/api/videos/[id]/dig/[sectionId]/route.ts`: delete the local `runDigPipeline` function (lines 82-177); add `import { digSection } from '@/lib/dig/dig-section';`; change the call site `runDigPipeline(videoId, sectionIdInt, outputFolder, signal, …)` → `digSection(videoId, sectionIdInt, outputFolder, signal, …)`. Remove now-unused imports from the route (path, fs, parseSummaryMarkdown, resolveTranscriptSegments, windowForSection, generateDig, DIG_GENERATOR_VERSION, resolveTranscriptTokens, resolveSlideTokens, upsertDugSection, readIndex, updateVideoFields) — keep only what the POST handler still uses (crypto, NextResponse, assertOutputFolder, assertVideoId, job-registry fns, logError/errorSummary, ProgressEvent).
docs/superpowers/plans/2026-06-29-batch-docs-phase-b-dig.md:281:import { assertOutputFolder, assertVideoId, readIndex } from '../index-store';
docs/superpowers/plans/2026-06-29-batch-docs-phase-b-dig.md:333:  const index = readIndex(outputFolder);
tests/lib/html-doc/ensure.test.ts:32:  (indexStore.readIndex as jest.Mock).mockReturnValue({ videos: [{ ...videoBase, ...v }] });
tests/integration/annotations-rpc.test.ts:35:    let idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:40:    idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:57:    const idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:136:    const idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:155:    const idx = await store.readIndex(p);
tests/lib/cloud-sync/local-stamping.test.ts:30:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
tests/lib/cloud-sync/local-stamping.test.ts:33:    const idx = await localMetadataStore.readIndex(p);
tests/lib/cloud-sync/local-stamping.test.ts:42:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
tests/lib/cloud-sync/local-stamping.test.ts:45:    const idx = await localMetadataStore.readIndex(p);
tests/lib/cloud-sync/local-stamping.test.ts:52:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
tests/lib/cloud-sync/local-stamping.test.ts:55:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:66:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
tests/lib/cloud-sync/local-stamping.test.ts:69:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:76:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
tests/lib/cloud-sync/local-stamping.test.ts:79:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:88:    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
tests/lib/cloud-sync/local-stamping.test.ts:91:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/api/dig-post.test.ts:70:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/dig-post.test.ts:222:  it('calls readIndex with outputFolder', async () => {
tests/integration/helpers/cloud.ts:202:    // ensureReceiverSlot creates the cloud playlist row during the run.
tests/integration/helpers/cloud.ts:235:  await ctx.local.setPlaylistMeta(lp, { playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}` });
tests/integration/helpers/cloud.ts:419:  await ctx.local.setPlaylistMeta(lp, { playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}` });
tests/integration/helpers/cloud.ts:437:  const idx = await new SupabaseMetadataStore(ctx.userClient).readIndex(ctx.cloudPrincipal);
tests/integration/helpers/cloud.ts:442:  const idx = await ctx.local.readIndex(ctx.localPrincipal);
tests/lib/timestamp-audit.test.ts:6:// MUST root the temp dir under $HOME — auditTimestamps → readIndex → assertOutputFolder
tests/lib/supabase-metadata-store-summary-ready.test.ts:8:// not exported). Only the readIndex path (playlists.maybeSingle +
tests/lib/supabase-metadata-store-summary-ready.test.ts:73:// readIndex — summaryReady derivation
tests/lib/supabase-metadata-store-summary-ready.test.ts:75:describe('readIndex — summaryReady derivation', () => {
tests/lib/supabase-metadata-store-summary-ready.test.ts:131:    const index = await store.readIndex(p);
tests/lib/storage/supabase-metadata-store.test.ts:155:// readIndex
tests/lib/storage/supabase-metadata-store.test.ts:157:describe('readIndex', () => {
tests/lib/storage/supabase-metadata-store.test.ts:161:    const idx = await store.readIndex(p);
tests/lib/storage/supabase-metadata-store.test.ts:173:    const idx = await store.readIndex(p);
tests/lib/storage/supabase-metadata-store.test.ts:190:    const idx = await store.readIndex(p);
tests/lib/storage/supabase-metadata-store.test.ts:196:// setPlaylistMeta
tests/lib/storage/supabase-metadata-store.test.ts:198:describe('setPlaylistMeta', () => {
tests/lib/storage/supabase-metadata-store.test.ts:202:    await store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list', playlistTitle: 'T' });
tests/lib/storage/supabase-metadata-store.test.ts:215:    await store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list' });
tests/lib/storage/supabase-metadata-store.test.ts:224:    await store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list' });
tests/lib/storage/supabase-metadata-store.test.ts:235:    await expect(store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list' })).rejects.toThrow('no authenticated user');
tests/lib/storage/supabase-metadata-store.test.ts:289:    // Simulates a Video sourced from readIndex(), which surfaces updatedAt.
tests/lib/storage/supabase-metadata-store.test.ts:304:    // Simulates a Video sourced from readIndex(), which surfaces both
tests/lib/storage/supabase-metadata-store.test.ts:525:  test('readIndex throws when playlist query fails', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:528:    await expect(store.readIndex(p)).rejects.toThrow('DB error');
tests/lib/dig/dig-section.test.ts:32:  jest.mocked(indexStore.readIndex).mockReturnValue({ playlistUrl: '', outputFolder: OF, videos: [video] } as any);
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:1754:- Consumes: `createServerSupabase(cookieStore)` + `cookies()` (pattern from `app/api/jobs/route.ts:32-34`), `supabase.auth.getUser()`, `getStorageBundle({ supabaseClient })`, `getPrincipalFromSession({ userId }, playlist_key)`, `metadataStore.readIndex(principal)`, `resolveMagazineModel` (Task 6), `parseSummaryMarkdown`, `renderMagazineHtml(parsed, model, { nonce, dig: false })`, `generateNonce`/`buildSummaryCsp` (Task 5), `assertVideoId`, `buildDocHtml`/`getPrincipal` (local path, unchanged).
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:1793:        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:1943:    const index = await bundle.metadataStore.readIndex(principal);
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2007:    const index = await getStorageBundle().metadataStore.readIndex(principal);
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2075:`getStorageBundle({ supabaseClient }).metadataStore.readIndex` (the video-row RLS backstop) — with real
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2098:  // resolveOwnedPlaylistKey (owner-assert) and readIndex (video-row RLS). It does NOT call GET, so it
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2107:    .metadataStore.readIndex({ id: a.user.id, indexKey: aDoc.playlistKey });
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2115:    .metadataStore.readIndex({ id: anonId, indexKey: anonDoc.playlistKey });
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2131:    .metadataStore.readIndex({ id: b.user.id, indexKey: aDoc.playlistKey });
docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2136:    .metadataStore.readIndex({ id: a.user.id, indexKey: bDoc.playlistKey });
tests/integration/html-serve-isolation.test.ts:25:  // resolveOwnedPlaylistKey (owner-assert) and readIndex (video-row RLS). It does NOT call GET, so it
tests/integration/html-serve-isolation.test.ts:34:    .metadataStore.readIndex({ id: a.user.id, indexKey: aDoc.playlistKey });
tests/integration/html-serve-isolation.test.ts:42:    .metadataStore.readIndex({ id: anonId, indexKey: anonDoc.playlistKey });
tests/integration/html-serve-isolation.test.ts:58:    .metadataStore.readIndex({ id: b.user.id, indexKey: aDoc.playlistKey });
tests/integration/html-serve-isolation.test.ts:63:    .metadataStore.readIndex({ id: a.user.id, indexKey: bDoc.playlistKey });
tests/api/backfill.test.ts:28:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/videos.test.ts:7:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/lib/storage/delayed-async-fake.ts:5: * e.g. `store.readIndex(p)` and immediately accesses `.videos` on the result (which is a
tests/lib/storage/delayed-async-fake.ts:17:    readIndex: (p) => wrap(() => inner.readIndex(p)),
tests/lib/storage/delayed-async-fake.ts:18:    setPlaylistMeta: (p, m) => wrap(() => inner.setPlaylistMeta(p, m)),
lib/serial-migrate-exec.ts:11:  const index = await store.readIndex(principal);
lib/serial-migrate-exec.ts:71:  const index = await store.readIndex(principal);
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:270:- Consumes: `nextSerial` (Task 3), `applySerial`/`padSerial` (Task 2), `readIndex`/`upsertVideo` (`lib/index-store`).
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:273:**Note:** compute the serial from a fresh `readIndex(outputFolder)` immediately before building `baseName` (the prefix must be on the filename before `writeSummaryDoc` writes it). The loop is sequential and `upsertVideo` updates the index each iteration, so `max+1` increments correctly within a run. Cross-process concurrency is the documented residual race (spec §5.1) — do not add locking.
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:310:const serial = nextSerial(readIndex(outputFolder).videos);
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:614:- Consumes: `readIndex`/`writeIndex` (`lib/index-store`), `planMigration` (Task 8).
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:625:  const after = readIndex(outputFolder).videos.map((v) => v.serialNumber).sort();
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:638:import { readIndex, writeIndex } from './index-store';
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:642:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:672:- Consumes: `planMigration` (Task 8), `updateVideoFields`/`readIndex` (`lib/index-store`), `rewriteSourceMdMeta`/`rewriteEnvelopeSourceMd` (Task 7).
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:687:  expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:719:  expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:728:  expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md'); // index converged
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:760:  const index = readIndex(outputFolder);
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:850:- Consumes: `planMigration` (Task 8), `runPhaseA`/`runPhaseB` (Tasks 9-10), `readIndex`.
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:875:import { readIndex } from '../lib/index-store';
docs/superpowers/plans/2026-06-25-serial-number-filename-prefix.md:880:  const { assignments, perVideo } = planMigration(readIndex(outputFolder).videos);
lib/archive.ts:16:  const index = await store.readIndex(principal);
lib/archive.ts:66:  const index = await store.readIndex(principal);
tests/integration/videos-route-cloud.test.ts:8:// resolveOwnedPlaylistKey, metadataStore.readIndex) runs for real. Same pattern as
tests/lib/storage/local-metadata-store.test.ts:17:test('readIndex on an empty folder returns the empty index shape', async () => {
tests/lib/storage/local-metadata-store.test.ts:19:  await expect(store.readIndex(p)).resolves.toEqual({ playlistUrl: '', outputFolder: p.indexKey, videos: [] });
tests/lib/storage/local-metadata-store.test.ts:24:  await store.setPlaylistMeta(p, { playlistUrl: 'https://youtube.com/playlist?list=X' });
tests/lib/storage/local-metadata-store.test.ts:36:  const idx = await store.readIndex(p);
tests/lib/storage/local-metadata-store.test.ts:45:  const idx = await store.readIndex(p);
lib/pipeline.ts:132:  const index = await store.readIndex(principal);
lib/pipeline.ts:198:  await store.setPlaylistMeta(principal, { playlistUrl, playlistTitle });
lib/pipeline.ts:204:  const alreadyIndexed = new Set((await store.readIndex(principal)).videos.map((v) => v.id));
lib/pipeline.ts:326:  const afterReconcile = await store.readIndex(principal);
tests/integration/quickview-route-cloud.test.ts:7:// resolveOwnedPlaylistKey, metadataStore.readIndex) runs for real.
tests/integration/metadata-store.test.ts:42:    await expect(store.readIndex(P)).resolves.toEqual({
tests/integration/metadata-store.test.ts:49:  // 2. setPlaylistMeta create then update
tests/integration/metadata-store.test.ts:50:  test('setPlaylistMeta create then update; readIndex reflects both writes', async () => {
tests/integration/metadata-store.test.ts:52:    await store.setPlaylistMeta(P, {
tests/integration/metadata-store.test.ts:56:    let idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:62:    await store.setPlaylistMeta(P, {
tests/integration/metadata-store.test.ts:66:    idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:70:  // 3. claimVideoSlot allocates sequential slots; upsertVideo fills row; readIndex round-trips
tests/integration/metadata-store.test.ts:71:  test('claimVideoSlot allocates position+serial sequentially; readIndex returns videos in order', async () => {
tests/integration/metadata-store.test.ts:73:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:84:    const idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:92:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:117:    const idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:134:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:141:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:158:    const cur = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:168:    const after = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:177:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:190:    const v = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:199:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:209:    let idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:219:    idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:230:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:237:    const before = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:244:    const after = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:251:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:260:    const idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:270:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:276:    const removed = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:282:    const restored = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:289:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:295:    const first = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:301:    const second = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:307:  test('deleteVideo removes the row; readIndex no longer contains it', async () => {
tests/integration/metadata-store.test.ts:309:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:313:    let idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:318:    idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:326:    await storeA.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:332:    const idxB = await storeB.readIndex(P);
tests/integration/metadata-store.test.ts:335:    // B's setPlaylistMeta creates its own playlist (not A's) — B cannot read A's
tests/integration/metadata-store.test.ts:336:    await storeB.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:337:    const idxBAfterSeed = await storeB.readIndex(P);
tests/integration/metadata-store.test.ts:341:    const idxAFinal = await storeA.readIndex(P);
tests/integration/metadata-store.test.ts:353:    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
tests/integration/metadata-store.test.ts:366:    const idx = await store.readIndex(P);
lib/html-doc/generate.ts:22:  const index = await store.readIndex(principal);
lib/html-doc/generate.ts:57:    // (the blob key/filename) — decideCompanion (Task 8) compares against mdHash(body); a
tests/integration/concurrency.test.ts:20:  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listConc' });
tests/integration/concurrency.test.ts:35:  const idx = await s.readIndex(P);
lib/cloud-sync/sync-run.ts:29:import { decideCompanion, type ModelRead } from './companion';
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:69:  const [l, c] = await Promise.all([local.readIndex(localP), cloud.readIndex(cloudP)]);
lib/cloud-sync/sync-run.ts:75:  const idx = await store.readIndex(p);
lib/cloud-sync/sync-run.ts:85: *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
lib/cloud-sync/sync-run.ts:86: *  the empty-index sentinel only when the dir exists but the file is absent), and setPlaylistMeta/
lib/cloud-sync/sync-run.ts:97: *  for every playlist present in both replicas. ensureReceiverSlot then handed that title-less meta
lib/cloud-sync/sync-run.ts:98: *  to setPlaylistMeta, whose Supabase impl upserts `playlist_title: meta.playlistTitle ?? null` —
lib/cloud-sync/sync-run.ts:109:function playlistMetaFor(
lib/cloud-sync/sync-run.ts:146: *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
lib/cloud-sync/sync-run.ts:147:async function ensureReceiverSlot(
lib/cloud-sync/sync-run.ts:155:  // (registry.ts), and playlistMetaFor MERGES both registries instead of returning the first hit —
lib/cloud-sync/sync-run.ts:158:  // Round 5 — a third layer used to sit here: readIndex BEFORE the write, then
lib/cloud-sync/sync-run.ts:161:  // an input where playlistMetaFor yields no title but the receiver row has one (zero-video cloud
lib/cloud-sync/sync-run.ts:163:  // playlist-index.json, the same file readIndex reads; opts.playlistKey is filtered through the
lib/cloud-sync/sync-run.ts:166:  // holds. setPlaylistMeta runs first again: it only touches the playlists row (never the video
lib/cloud-sync/sync-run.ts:167:  // set), and on the local backend it creates the index file that readIndex then reads.
lib/cloud-sync/sync-run.ts:168:  await to.setPlaylistMeta(toP, {
lib/cloud-sync/sync-run.ts:172:  const idx = await to.readIndex(toP);
lib/cloud-sync/sync-run.ts:178: *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
lib/cloud-sync/sync-run.ts:190:  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
lib/cloud-sync/sync-run.ts:200:  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
lib/cloud-sync/sync-run.ts:231:  const after = await to.readIndex(toP);
lib/cloud-sync/sync-run.ts:356:    // readIndex reads falsy → forces re-render.
lib/cloud-sync/sync-run.ts:383:): Promise<{ shareNeedsOwnerServe: boolean }> {
lib/cloud-sync/sync-run.ts:384:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:387:  // only the RECEIVER's own envelope can prove the receiver's model stale (see decideCompanion).
lib/cloud-sync/sync-run.ts:391:  const decision = decideCompanion({ winnerMdHash, senderModel, receiverModel });
lib/cloud-sync/sync-run.ts:394:    return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:399:  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
lib/cloud-sync/sync-run.ts:402:  return { shareNeedsOwnerServe: true };
lib/cloud-sync/sync-run.ts:405:/** H1 (round 4) — resolve `readModelEnvelope`'s single null into the tri-state decideCompanion needs.
lib/cloud-sync/sync-run.ts:480:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:498:    const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
lib/cloud-sync/sync-run.ts:626:          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
lib/cloud-sync/companion.ts:19:/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
lib/cloud-sync/companion.ts:26:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
lib/cloud-sync/companion.ts:27:  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
lib/cloud-sync/companion.ts:54:export function decideCompanion(args: {
lib/cloud-sync/companion.ts:70:    return { kind: 'noop', shareNeedsOwnerServe: false };
lib/cloud-sync/companion.ts:84:  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
lib/cloud-sync/companion.ts:89:  const provablyStale = receiverModel.kind === 'envelope'
lib/cloud-sync/companion.ts:91:  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
lib/cloud-sync/companion.ts:92:  return { kind: 'noop', shareNeedsOwnerServe: true };
lib/html-doc/serve-summary-core.ts:43:  const index = await bundle.metadataStore.readIndex(principal);
lib/playlists/backfill-titles.ts:32:    try { index = await store.readIndex(p); } catch { failed.push(folder); continue; }
lib/playlists/backfill-titles.ts:38:      await store.setPlaylistMeta(p, { playlistUrl: index.playlistUrl ?? '', playlistTitle });
lib/html-doc/ensure.ts:30:  const video = (await store.readIndex(principal)).videos.find((v) => v.id === videoId);
lib/timestamp-repair.ts:17:// batch (and in unit tests, where ensure* is mocked, readIndex on a synthetic folder will throw).
lib/timestamp-repair.ts:22:    const v = (await store.readIndex(principal)).videos.find((x) => x.id === id);
lib/html-doc/rerender.ts:37:  const index = await store.readIndex(principal);
lib/html-doc/rerender.ts:101:  const index = await store.readIndex(principal);
lib/cloud-sync/registry.ts:6:/** H3 (round 4) — `playlistTitle` is carried because playlistMetaFor resolves the local registry
lib/cloud-sync/registry.ts:8: *  the cloud setPlaylistMeta upsert writes as an explicit NULL. Optional: a local index legitimately
lib/cloud-sync/registry.ts:32:      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
lib/storage/empty-index.ts:4:/** The exact shape lib/index-store.readIndex returns for an absent index file,
lib/html-doc/batch.ts:57:  const index = await store.readIndex(principal);
tests/integration/cloud-sync/sync-run.int.test.ts:35:    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
lib/job-queue/producer.ts:97:    if (t) await sessionBundle.metadataStore.setPlaylistMeta(principal, { playlistUrl, playlistTitle: t });
lib/storage/metadata-store.ts:17:  readIndex(p: Principal): Promise<PlaylistIndex>;
lib/storage/metadata-store.ts:18:  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
tests/integration/share-summary-2c.test.ts:6://   3. SupabaseMetadataStore.readIndex's `summaryReady` DTO reflection under real RLS
tests/integration/share-summary-2c.test.ts:91:  test('summaryReady reflection via SupabaseMetadataStore.readIndex under real RLS', async () => {
tests/integration/share-summary-2c.test.ts:108:    const idx = await store.readIndex(p);
tests/integration/cloud-sync/e2e.int.test.ts:236:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:246:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:353:  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
tests/integration/cloud-sync/e2e.int.test.ts:459:  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
tests/integration/cloud-sync/e2e.int.test.ts:472:    // No partial state at all: the guard runs before ensureReceiverSlot, so there is no receiver row.
tests/integration/cloud-sync/e2e.int.test.ts:697:    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
tests/integration/cloud-sync/e2e.int.test.ts:703:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:735:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
tests/integration/cloud-sync/e2e.int.test.ts:739:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:776:    expect(r1.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:780:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:826:  //    playlistMetaFor checked the local registry FIRST and returned { playlistUrl } with no title
tests/integration/cloud-sync/e2e.int.test.ts:828:  //    unreachable whenever the playlist also exists locally. ensureReceiverSlot then called
tests/integration/cloud-sync/e2e.int.test.ts:829:  //    setPlaylistMeta unconditionally, and the Supabase upsert writes
tests/integration/cloud-sync/e2e.int.test.ts:856:    // Run 2 — ensureReceiverSlot's setPlaylistMeta fires on every run, so once is not enough.
tests/integration/cloud-sync/e2e.int.test.ts:862:  //    playlistMetaFor preferred `lp?.playlistTitle`, so a local playlist-index.json title — whatever
tests/integration/cloud-sync/e2e.int.test.ts:882:    await ctx.local.setPlaylistMeta(ctx.localPrincipal, {
tests/integration/cloud-sync/e2e.int.test.ts:909:    await ctx.local.setPlaylistMeta(ctx.localPrincipal, {
lib/storage/local/local-metadata-store.ts:10:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/local/local-metadata-store.ts:11:    return indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:13:  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
lib/storage/local/local-metadata-store.ts:14:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:23:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:55:      const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:68:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:82:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:107:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:142:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/supabase/supabase-metadata-store.ts:9:// before any write to `videos.data`. readIndex() surfaces `updatedAt`
lib/storage/supabase/supabase-metadata-store.ts:27:  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
lib/storage/supabase/supabase-metadata-store.ts:29:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/supabase/supabase-metadata-store.ts:60:  // setPlaylistMeta: upsert on (owner_id, playlist_key).
lib/storage/supabase/supabase-metadata-store.ts:65:  async setPlaylistMeta(
lib/storage/supabase/supabase-metadata-store.ts:71:    if (!ownerId) throw new Error('setPlaylistMeta: no authenticated user');
lib/storage/supabase/supabase-metadata-store.ts:202:  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
lib/storage/supabase/supabase-metadata-store.ts:203:  // clobbered. Scoped by owner_id (from auth.getUser, mirroring setPlaylistMeta) and

codex
The R5 diff is large mostly because review docs were committed; the code changes are concentrated in companion decisioning, sync-run metadata/title handling, and the manifest comment. I’m narrowing now to the exact shipped code paths rather than the full diff.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/companion.ts | sed -n '1,140p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { ModelEnvelope } from '@/lib/html-doc/model-store';
     2	
     3	/** H1 (round 4) — the result of reading ONE side's model, as a TRI-state.
     4	 *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
     5	 *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean that side has
     6	 *  nothing usable; the third means we simply do not know, and acting on it destroys a paid artifact.
     7	 *  Which of those a null is depends on the backend — see BlobStore.provesAbsence — so the caller
     8	 *  resolves it and hands the answer here.
     9	 *
    10	 *  H-R5-1 (round 5) — this is now read for BOTH sides, hence the neutral name. */
    11	export type ModelRead =
    12	  | { kind: 'envelope'; envelope: ModelEnvelope }
    13	  | { kind: 'none' }      // that side PROVABLY has no usable model
    14	  | { kind: 'unknown' };  // the read failed in a way that cannot prove absence
    15	
    16	/** @deprecated round-4 name, kept so the tri-state reads naturally at the sender call site. */
    17	export type SenderModelRead = ModelRead;
    18	
    19	/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
    20	 *  axis from the blob action and conflating the two is what produced this finding. The action answers
    21	 *  "what do we do to the receiver's blob?"; the flag is a report-only count of shares that cannot
    22	 *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
    23	 *  there is nothing to delete and yet the share IS unready — noop + true. */
    24	export type CompanionAction =
    25	  | { kind: 'ship'; envelope: ModelEnvelope }
    26	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
    27	  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
    28	
    29	/** Ship the sender's model iff it was generated from the winning MD (§4.2); otherwise decide the
    30	 *  receiver's fate from the RECEIVER's own envelope.
    31	 *
    32	 *  H1 (round 4) — `unknown` must not delete. Deleting the receiver's model costs a paid Gemini
    33	 *  magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
    34	 *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
    35	 *  silent and sticky: it does not throw, so the caller advances the manifest baseline, and the next
    36	 *  run's Class-A reconcile returns 'skip' and never revisits the companion step.
    37	 *
    38	 *  H-R5-1 (round 5) — round 4 made the SENDER read honest but left the whole decision keyed to it,
    39	 *  which was wrong in both directions:
    40	 *   (a) `unknown` → noop KEPT a provably-stale receiver model. The claimed safety net does not
    41	 *       exist: the serve path's drift guard (lib/html-doc/read-model.ts) compares section TITLES and
    42	 *       generatorVersion, never sourceMdHash, so a prose-only MD change — precisely the
    43	 *       recency-tiebreak case — is served as fresh forever (dig-deeper merges the cached envelope
    44	 *       without regenerating). And `unknown` is the COMMON outcome: a cloud video that was never
    45	 *       HTML-served has no model blob, and the Supabase backend cannot prove that 404.
    46	 *   (b) `none` → delete DESTROYED receiver models that were still valid, since the receiver was
    47	 *       never consulted.
    48	 *  The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
    49	 *  independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT is
    50	 *  definitively stale — its backing body no longer exists — with no ambiguity involved. So the
    51	 *  sender read now decides only whether a REPLACEMENT can be shipped, and everything else is keyed
    52	 *  to the receiver. Deleting a provably-stale model is not a money loss; deleting a matching one is.
    53	 */
    54	export function decideCompanion(args: {
    55	  winnerMdHash: string;
    56	  senderModel: ModelRead;
    57	  receiverModel: ModelRead;
    58	}): CompanionAction {
    59	  const { winnerMdHash, senderModel, receiverModel } = args;
    60	
    61	  // 1. The sender holds a model built from the winning MD → ship it (it supersedes whatever the
    62	  //    receiver has, so the receiver's own state does not matter here).
    63	  if (senderModel.kind === 'envelope' && senderModel.envelope.sourceMdHash === winnerMdHash) {
    64	    return { kind: 'ship', envelope: senderModel.envelope };
    65	  }
    66	
    67	  // 2. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
    68	  //    still valid. Do not destroy a paid artifact, and the share renders, so report nothing.
    69	  if (receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash === winnerMdHash) {
    70	    return { kind: 'noop', shareNeedsOwnerServe: false };
    71	  }
    72	
    73	  // 3. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
    74	  //
    75	  //  - DELETE the blob only on PROOF. A receiver envelope whose sourceMdHash is present and differs
    76	  //    is definitively stale — its backing body no longer exists — and needs no sender read to
    77	  //    establish. Everything else is unprovable: `none`/`unknown` say nothing about a model we never
    78	  //    read, and a legacy pre-1F-a envelope predates sourceMdHash entirely (the field is .optional()
    79	  //    in model-store.ts), so it cannot be checked. Fail-safe-for-money: KEEP those. A possibly-stale
    80	  //    cache is recoverable — any regeneration overwrites it, and the existing sourceSections /
    81	  //    generatorVersion drift guard still catches the common legacy drift — but a deleted paid
    82	  //    artifact costs a Gemini transform to rebuild.
    83	  //
    84	  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
    85	  //    not render until you re-serve." It spends nothing and destroys nothing, so the harmful
    86	  //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
    87	  //    receiver of a copyToCloud is always the Supabase store, which can never return `none`, so
    88	  //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
    89	  const provablyStale = receiverModel.kind === 'envelope'
    90	    && receiverModel.envelope.sourceMdHash !== undefined;
    91	  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
    92	  return { kind: 'noop', shareNeedsOwnerServe: true };
    93	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '90,245p' && nl -ba lib/cloud-sync/sync-run.ts | sed -n '330,430p' && nl -ba lib/cloud-sync/sync-run.ts | sed -n '430,680p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    90	}
    91	
    92	/** Resolve the playlist url/title for `key` from whichever registry holds it.
    93	 *
    94	 *  H3 (round 4) — this MERGES the two registries rather than returning the first hit. It used to
    95	 *  return the local entry's `{ playlistUrl }` alone whenever the playlist existed locally, and
    96	 *  LocalPlaylist carried no title at all, so the cloud branch that does carry one was unreachable
    97	 *  for every playlist present in both replicas. ensureReceiverSlot then handed that title-less meta
    98	 *  to setPlaylistMeta, whose Supabase impl upserts `playlist_title: meta.playlistTitle ?? null` —
    99	 *  wiping the cloud row's title on every sync carrying any local-only video. URL still prefers the
   100	 *  local entry (it is the replica whose folder we are actually syncing).
   101	 *
   102	 *  L-R5-2 (round 5) — the TITLE prefers the CLOUD entry. Titles have no LWW timestamp, so this is a
   103	 *  fixed precedence, not a merge; the cloud row is the one the ingest and backfill-titles paths
   104	 *  maintain (both write it from the live YouTube API), whereas a local playlist-index.json title is
   105	 *  whatever was captured when that folder was last summarized and can be arbitrarily old. Preferring
   106	 *  local meant a stale local title overwrote a fresher cloud one on every additive local→cloud
   107	 *  create. Each side still falls back to the other, so a replica that has the only title supplies
   108	 *  it — a sync can fill a title or refresh it from the cloud, never clear it. */
   109	function playlistMetaFor(
   110	  key: string, localPlaylists: LocalPlaylist[], cloudSummaries: PlaylistSummary[],
   111	): { playlistUrl: string; playlistTitle?: string } {
   112	  const lp = localPlaylists.find((l) => l.playlistKey === key);
   113	  const cp = cloudSummaries.find((c) => c.playlistKey === key);
   114	  const playlistUrl = lp?.playlistUrl ?? cp?.playlistUrl ?? '';
   115	  const playlistTitle = cp?.playlistTitle ?? lp?.playlistTitle ?? undefined;
   116	  return { playlistUrl, ...(playlistTitle ? { playlistTitle } : {}) };
   117	}
   118	
   119	/** Behavior #3 (money-safe) — strip regenerable cache + out-of-scope pointers so the receiver never
   120	 *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
   121	 *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
   122	 *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
   123	function sanitizeAdditiveVideo(video: Video): Video {
   124	  const v: any = { ...video };
   125	  v.summaryHtml = null;
   126	  v.digDeeperHtml = null;
   127	  v.digDeeperMd = null;
   128	  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
   129	  if (v.artifacts && typeof v.artifacts === 'object') {
   130	    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
   131	  }
   132	  // Replica-local ordering is NOT synced (§4.1) — the receiver's claim supplies its own.
   133	  delete v.serialNumber;
   134	  delete v.playlistIndex;
   135	  delete v.removedFromPlaylist;
   136	  // DB-computed read-only fields must never round-trip into a write.
   137	  delete v.updatedAt;
   138	  delete v.summaryReady;
   139	  return v as Video;
   140	}
   141	
   142	/** round-4 H1 — create the receiver playlist + reservation row BEFORE any receiver write. The cloud
   143	 *  upsertVideo/updateVideoFields are bare UPDATEs of a row pre-created by claimVideoSlot: they
   144	 *  silently affect 0 rows (no throw) on an absent row, so an additive create must claim the slot
   145	 *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
   146	 *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
   147	async function ensureReceiverSlot(
   148	  to: MetadataStore, toP: Principal,
   149	  playlistMeta: { playlistUrl: string; playlistTitle?: string }, video: Video,
   150	): Promise<{ position: number; serialNumber: number } | null> {
   151	  // H3 (round 4) — a sync must never CLEAR the receiver's playlist title. The upsert always writes
   152	  // the playlist_title column (`meta.playlistTitle ?? null`), so simply omitting the title here
   153	  // would NULL it, and the never-clobber primitive setPlaylistTitleIfNull cannot undo that.
   154	  // The fix lives in the two layers that feed this call: LocalPlaylist now carries playlistTitle
   155	  // (registry.ts), and playlistMetaFor MERGES both registries instead of returning the first hit —
   156	  // so whenever either replica knows the title, `playlistMeta.playlistTitle` carries it here.
   157	  //
   158	  // Round 5 — a third layer used to sit here: readIndex BEFORE the write, then
   159	  // `playlistMeta.playlistTitle ?? idx.playlistTitle` to carry the receiver's own title forward.
   160	  // It was REMOVED as unreachable, not as cleanup: both reviewers independently failed to construct
   161	  // an input where playlistMetaFor yields no title but the receiver row has one (zero-video cloud
   162	  // playlists still appear in listPlaylists with their title; local playlists are discovered from
   163	  // playlist-index.json, the same file readIndex reads; opts.playlistKey is filtered through the
   164	  // union), and deleting it failed ZERO tests under mutation. Do not re-add it without an input
   165	  // that reaches it — dead defense-in-depth reads as load-bearing and hides which layer actually
   166	  // holds. setPlaylistMeta runs first again: it only touches the playlists row (never the video
   167	  // set), and on the local backend it creates the index file that readIndex then reads.
   168	  await to.setPlaylistMeta(toP, {
   169	    playlistUrl: playlistMeta.playlistUrl,
   170	    ...(playlistMeta.playlistTitle ? { playlistTitle: playlistMeta.playlistTitle } : {}),
   171	  });
   172	  const idx = await to.readIndex(toP);
   173	  if (idx.videos.some((v) => v.id === video.id)) return null;
   174	  return to.claimVideoSlot(toP, video.id);
   175	}
   176	
   177	/** Behavior #3 (money-safe) — additive create of a one-sided video onto the receiver. Order:
   178	 *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
   179	 *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
   180	 *  never copies regenerable cache. */
   181	async function copyAdditiveVideo(
   182	  to: MetadataStore, toP: Principal, toBlob: BlobStore,
   183	  playlistMeta: { playlistUrl: string; playlistTitle?: string },
   184	  video: Video, mdBody: string | null,
   185	): Promise<void> {
   186	  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
   187	  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
   188	  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
   189	  // strand the receiver with a servable-looking row backed by nothing.
   190	  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
   191	  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
   192	  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
   193	  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
   194	  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
   195	  // partial state is ever created, so there is nothing to roll back.
   196	  if (video.summaryMd && mdBody == null) {
   197	    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
   198	  }
   199	
   200	  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
   201	
   202	  let wroteBlob = false;
   203	  if (video.summaryMd && mdBody != null) {
   204	    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
   205	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
   206	    const staged = await toBlob.get(toP, ref.tempKey);
   207	    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
   208	      throw new Error(`additive staged MD verify failed for ${video.id}`);
   209	    }
   210	    await toBlob.promote(ref);
   211	    wroteBlob = true;
   212	  }
   213	
   214	  const sanitized: any = sanitizeAdditiveVideo(video);
   215	  if (slot) {
   216	    sanitized.serialNumber = slot.serialNumber;
   217	    sanitized.playlistIndex = slot.position + 1;
   218	  }
   219	  if (wroteBlob) {
   220	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
   221	  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
   222	    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
   223	    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
   224	    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
   225	    delete sanitized.artifacts.summaryMd;
   226	  }
   227	  await to.upsertVideo(toP, sanitized as Video);
   228	
   229	  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
   230	  // (an update against an absent row silently no-ops; never advance a baseline for that).
   231	  const after = await to.readIndex(toP);
   232	  const rec = after.videos.find((v) => v.id === video.id);
   233	  if (!rec) {
   234	    throw new Error(`additive create did not persist receiver row for ${video.id}`);
   235	  }
   236	  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
   237	  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
   238	  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
   239	  if (wroteBlob) {
   240	    const art = (rec as any).artifacts?.summaryMd;
   241	    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
   242	      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
   243	    }
   244	  }
   245	}
   330	  // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   331	  // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   332	  // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   333	  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   334	  // (below) advertises promoted only after this resolves.
   335	  await loser.blob.put(loser.p, key, staged, 'text/markdown');
   336	  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
   337	
   338	  const wv: any = winnerVideo;
   339	  const completeTuple: any = {
   340	    summaryMd: key,
   341	    docVersion: wv.docVersion,
   342	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
   343	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
   344	    ratings: wv.ratings,
   345	    overallScore: wv.overallScore,
   346	    videoType: wv.videoType,
   347	    audience: wv.audience,
   348	    tags: wv.tags,
   349	    tldr: wv.tldr,
   350	    takeaways: wv.takeaways,
   351	    // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
   352	    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
   353	    // the serve path (buildDocHtml/ensureHtmlDoc) checks generator-version, NOT MD-body freshness, so a
   354	    // same-format prose change (the recency-tiebreak case) would serve stale HTML indefinitely (§5.1
   355	    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
   356	    // readIndex reads falsy → forces re-render.
   357	    //
   358	    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
   359	    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
   360	    // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
   361	    // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
   362	    // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
   363	    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
   364	    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
   365	    // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
   366	    // whereas transferClassA PATCHES a row that already holds its own state.
   367	    summaryHtml: null,
   368	    digDeeperHtml: null,
   369	    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
   370	    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
   371	    artifacts: { summaryMd: { key, status: 'promoted' } },
   372	  };
   373	  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
   374	
   375	  return { mdHash: h, verified: true };
   376	}
   377	
   378	/** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
   379	 *  MD; otherwise delete the loser's model (best-effort, OUTSIDE the atomic commit) and flag that the
   380	 *  owner must re-serve — but ONLY when that model proves itself stale (H-R5-1). */
   381	async function companionTransfer(
   382	  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
   383	): Promise<{ shareNeedsOwnerServe: boolean }> {
   384	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   385	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   386	  // H-R5-1 (round 5) — read BOTH sides. The sender read says whether a replacement can be shipped;
   387	  // only the RECEIVER's own envelope can prove the receiver's model stale (see decideCompanion).
   388	  const [senderModel, receiverModel] = await Promise.all([
   389	    readModelSide(winner, base), readModelSide(loser, base),
   390	  ]);
   391	  const decision = decideCompanion({ winnerMdHash, senderModel, receiverModel });
   392	  if (decision.kind === 'ship') {
   393	    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
   394	    return { shareNeedsOwnerServe: false };
   395	  }
   396	  // H1 (round 4) / H-R5-1 (round 5) — nothing shippable and the receiver's model is not PROVABLY
   397	  // stale: leave the blob alone. The report flag is decided separately (§10 row 7 counts a share
   398	  // with no model even though there is nothing to delete).
   399	  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
   400	  // deleteReceiverModel — best-effort; a missing model blob is not an error.
   401	  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   402	  return { shareNeedsOwnerServe: true };
   403	}
   404	
   405	/** H1 (round 4) — resolve `readModelEnvelope`'s single null into the tri-state decideCompanion needs.
   406	 *  A null means absent, corrupt, or unreadable; only a backend that can prove absence
   407	 *  (BlobStore.provesAbsence — the local FS store, whose get is ENOENT-only) lets us tell those
   408	 *  apart. On such a backend a null is definitive either way: the model is genuinely missing, or its
   409	 *  bytes were read and rejected — both mean that side has nothing usable. On the Supabase backend
   410	 *  the same null may be a transient 5xx / timeout / RLS denial, so it proves nothing and must not
   411	 *  drive a destructive delete. A backend that does not declare the capability is treated as unable
   412	 *  to prove absence.
   413	 *  H-R5-1 (round 5) — used for the RECEIVER too (hence the neutral name): a receiver `unknown` must
   414	 *  not be read as "no model", and a receiver `none` leaves nothing to delete. */
   415	async function readModelSide(side: Side, base: string): Promise<ModelRead> {
   416	  const envelope = await readModelEnvelope(side.p, base, side.blob);
   417	  if (envelope) return { kind: 'envelope', envelope };
   418	  return side.blob.provesAbsence ? { kind: 'none' } : { kind: 'unknown' };
   419	}
   420	
   421	/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
   422	 *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
   423	 *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
   424	 *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
   425	 *  recording the winner there would be a false agreement → next-run silent overwrite). */
   426	function buildClassBBaseline(
   427	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   428	): VideoBaseline['classB'] {
   429	  const classB = {} as VideoBaseline['classB'];
   430	  for (const f of FIELDS) {
   430	  for (const f of FIELDS) {
   431	    const m = merges[f];
   432	    if (m.winner === 'equal' && m.conflict) {
   433	      classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
   434	    } else {
   435	      classB[f] = { value: m.value, editedAt: m.editedAt };
   436	    }
   437	  }
   438	  return classB;
   439	}
   440	
   441	function buildBaseline(
   442	  winnerSignals: ClassASignals, winnerMdHash: string | null,
   443	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   444	): VideoBaseline {
   445	  return {
   446	    classA: {
   447	      docVersionMajor: winnerSignals.docVersionMajor,
   448	      mdGeneratedAt: winnerSignals.mdGeneratedAt,
   449	      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
   450	      mdHash: winnerMdHash,
   451	    },
   452	    classB: buildClassBBaseline(merges, previousBaseline),
   453	  };
   454	}
   455	
   456	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
   457	 *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
   458	 *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
   459	 *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
   460	 *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
   461	 *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
   462	 *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
   463	function buildCorrectionsUnresolvedBaseline(
   464	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   465	): VideoBaseline {
   466	  return {
   467	    classA: previousBaseline?.classA
   468	      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
   469	    classB: buildClassBBaseline(merges, previousBaseline),
   470	  };
   471	}
   472	
   473	export async function runSync(
   474	  deps: SyncDeps, opts: { playlistKey?: string } = {},
   475	): Promise<SyncReport> {
   476	  resetConflictDedup();
   477	  const report: SyncReport = {
   478	    created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
   479	    mergedFields: 0, conflictsLogged: 0, removed: 0,
   480	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   481	  };
   482	
   483	  const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   484	  const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   485	  const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   486	  let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   487	  if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
   488	
   489	  for (const key of keys) {
   490	    const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
   491	      ?? hydrationRoot(deps.dataRoots, key);
   492	    await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
   493	
   494	    const localP = localPrincipal(dataRoot);
   495	    const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
   496	    const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
   497	    const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
   498	    const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
   499	    const manifest = await readManifest(dataRoot, key);
   500	
   501	    for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
   502	      try {
   503	        const lv = await readVideo(deps.local, localP, id);
   504	        const cv = await readVideo(deps.cloud, cloudP, id);
   505	        const base = manifest.videos[id];
   506	
   507	        // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
   508	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
   509	        if (!lv || !cv) {
   510	          const present = (lv ?? cv)!;
   511	          const presentIsLocal = lv != null;
   512	          if (base) {
   513	            report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
   514	          } else {
   515	            const from: Side = presentIsLocal ? localSide : cloudSide;
   516	            const to: Side = presentIsLocal ? cloudSide : localSide;
   517	            const body = await readMdBody(from.blob, from.p, present);
   518	            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
   519	            report.created += 1; // reached only after the receiver row is confirmed
   520	            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
   521	              deriveClassASignals(present, body), body ? mdHash(body) : null,
   522	              deriveHumanSnapshot(present),
   523	            ));
   524	          }
   525	          continue;
   526	        }
   527	
   528	        // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
   529	        const localSnap = deriveHumanSnapshot(lv);
   530	        const cloudSnap = deriveHumanSnapshot(cv);
   531	        const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
   532	        const applied = await applyClassBWinners({
   533	          deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
   534	        });
   535	        report.mergedFields += applied.merged;
   536	        report.conflictsLogged += applied.conflicts;
   537	        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
   538	
   539	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
   540	        //    Class B logs+skips, §5.5). Its value is NOT a settled winner, so it must NOT drive a
   541	        //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
   542	        //    and copy its MD body over the loser's (different-correction) body — DESTROYING the loser's
   543	        //    corrected MD and recording a false agreement (sticky: the copied bodies then match forever).
   544	        //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
   545	        //    Class A (so the next run re-evaluates once the human resolves corrections). The video stays
   546	        //    "seen" for delete-inference (baseline present).
   547	        //
   548	        //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
   549	        //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
   550	        //    behavior. Bodies are needed for hashing regardless — Behavior #1.
   551	        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
   552	        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
   553	
   554	        // ── B1 (round 3) — the two-sided counterpart of copyAdditiveVideo's WB-H1/H-R2-1 guard (:160).
   555	        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
   556	        //    or it advertises one whose bytes could not be READ. The backends disagree on which errors
   557	        //    are which: local get throws on anything but ENOENT, but the Supabase get is `if (error)
   558	        //    return null` — it swallows EVERY failure (network, 5xx, timeout, RLS denial), so on the
   559	        //    cloud side an ordinary transient download error is indistinguishable from "no MD".
   560	        //    deriveClassASignals maps a null body to mdHash: null, and reconcileClassA reads
   561	        //    mdHash == null as "this side HAS NO MD" (:21-23) — and those presence branches return
   562	        //    BEFORE the corrections-currency and never-downgrade-format ladder (:38-46). So an
   563	        //    unreadable body made the other replica's body get copied over it (destroying it) and
   564	        //    recorded a full-agreement baseline; run 2 then saw identical bodies and skipped, making
   565	        //    the loss permanent and recoverable only by paid regeneration.
   566	        //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
   567	        //    so the run heals by itself once the body is readable. With this guard reconcileClassA's
   568	        //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
   569	        //    which is exactly M-R2-2's "purely additive hydration", so its intent is preserved.
   570	        //    H2 (round 4) — the guard is scoped to the backend that actually needs it. It exists
   571	        //    ONLY because one backend cannot tell absent from unreadable, so only that backend
   572	        //    should pay for it (BlobStore.provesAbsence). On the local FS store a null body IS
   573	        //    proof the file is gone — the user moved or deleted the .md by hand, or a generation
   574	        //    crashed between the index write and the blob write — and that case heals for free:
   575	        //    !lHas → copyToLocal writes the cloud's intact body over the dangling pointer, purely
   576	        //    additive, nothing to destroy. Throwing there stranded the video on EVERY run forever,
   577	        //    never advancing a baseline, with no exit but hand-editing playlist-index.json or
   578	        //    paying to regenerate content sitting intact in the cloud — re-introducing exactly the
   579	        //    stranding M-R2-2 removed. The cloud side stays fail-closed, unchanged.
   580	        if (lv.summaryMd && la.mdHash == null && !deps.localBlob.provesAbsence) {
   581	          throw new Error(`local MD body unreadable for ${id}`);
   582	        }
   583	        if (cv.summaryMd && ca.mdHash == null && !deps.cloudBlob.provesAbsence) {
   584	          throw new Error(`cloud MD body unreadable for ${id}`);
   585	        }
   586	
   587	        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
   588	        //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
   589	        //    nothing can be destroyed and no false agreement about competing bodies is possible — so
   590	        //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
   591	        //    corrections). The corrections conflict is still logged by Class B and still flags
   592	        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
   593	        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
   594	        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
   595	          report.needsRegen += 1;
   596	          if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   597	          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
   598	          continue;
   599	        }
   600	
   601	        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
   602	        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
   603	        if (decision.needsRegen) report.needsRegen += 1;
   604	
   605	        let winnerMdHash: string | null = null;
   606	        let winnerSignals: ClassASignals = la;
   607	        let winnerSide: Side | null = null;
   608	        let loserSide: Side | null = null;
   609	        let winnerVideo: Video = lv;
   610	
   611	        if (decision.action === 'copyToCloud') {
   612	          winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
   613	          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
   614	          report.updatedCloud += 1;
   615	        } else if (decision.action === 'copyToLocal') {
   616	          winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
   617	          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
   618	          report.updatedLocal += 1;
   619	        } else {
   620	          report.skippedIdentical += 1;
   621	          winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
   622	        }
   623	
   624	        if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
   625	          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
   626	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
   627	        }
   628	        if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   629	
   630	        // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
   631	        //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
   632	        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
   633	      } catch (e: any) {
   634	        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
   635	      }
   636	    }
   637	  }
   638	
   639	  return report;
   640	}

exec
/bin/bash -lc "nl -ba lib/storage/blob-store.ts && nl -ba lib/storage/local/local-metadata-store.ts | sed -n '1,190p' && nl -ba lib/storage/supabase/supabase-metadata-store.ts | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { Principal } from '@/lib/storage/principal';
     2	
     3	export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';
     4	
     5	export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }
     6	
     7	export interface BlobStore {
     8	  /** True iff a `null` from `get` (or `false` from `exists`) PROVES the object does not exist —
     9	   *  i.e. the backend distinguishes "absent" from "could not be read". The local FS store returns
    10	   *  null only on ENOENT and rethrows every other errno, so it proves absence; the Supabase store
    11	   *  swallows network/5xx/timeout/RLS failures into the same null, so it cannot.
    12	   *
    13	   *  Read it before treating "no bytes" as a semantic fact ("this replica holds no MD", "this
    14	   *  sender has no model"): on a backend that cannot prove absence, acting on that reading
    15	   *  destroys data on a transient blip (see the B1 and H1 guards in lib/cloud-sync/sync-run.ts).
    16	   *  Optional, and absent means FALSE — an unknown backend is assumed unable to prove absence, so
    17	   *  callers stay fail-closed by default. */
    18	  readonly provesAbsence?: boolean;
    19	  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
    20	  get(p: Principal, key: string): Promise<Buffer | null>;
    21	  exists(p: Principal, key: string): Promise<boolean>;
    22	  delete(p: Principal, key: string): Promise<void>;
    23	  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
    24	  promote(ref: StagedRef): Promise<void>;
    25	  /** Recursively delete every object under a logical prefix. Best-effort/idempotent —
    26	   *  an absent prefix is not an error. `prefix === ''` targets the whole playlist root
    27	   *  (`<owner>/<indexKey>/`), not above it. */
    28	  deletePrefix(p: Principal, prefix: string): Promise<void>;
    29	  /** List logical keys (relative to the owner root) under a prefix. Absent prefix → []. */
    30	  list(p: Principal, prefix: string): Promise<string[]>;
    31	}
    32	
    33	/** A read-only view of a BlobStore — exactly the `get` method. The share serve path
    34	 *  passes a runtime `{ get: store.get.bind(store) }` wrapper so write methods are
    35	 *  unreachable at runtime, not merely hidden by the type (spec D16). */
    36	export type ReadOnlyBlobStore = Pick<BlobStore, 'get'>;
    37	
    38	export function assertLogicalKey(key: string): void {
    39	  if (key.startsWith('/') || key.split('/').includes('..') || key.includes('\0')) {
    40	    throw Object.assign(new Error(`invalid blob key: ${key}`), { statusCode: 400 });
    41	  }
    42	}
     1	import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
     2	import type { Principal } from '@/lib/storage/principal';
     3	import type { PlaylistIndex, Video } from '@/types';
     4	import * as indexStore from '@/lib/index-store';
     5	import { nextSerial } from '@/lib/serial-assign';
     6	
     7	/** Behavior-preserving local impl. Sync index-store calls wrapped in resolved Promises;
     8	 *  the new transactional methods replicate today's pipeline logic against the JSON file. */
     9	export class LocalFsMetadataStore implements MetadataStore {
    10	  async readIndex(p: Principal): Promise<PlaylistIndex> {
    11	    return indexStore.readIndex(p.indexKey);
    12	  }
    13	  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
    14	    const idx = indexStore.readIndex(p.indexKey);
    15	    indexStore.writeIndex(p.indexKey, {
    16	      ...idx,
    17	      playlistUrl: meta.playlistUrl,
    18	      outputFolder: p.indexKey,
    19	      ...(meta.playlistTitle ? { playlistTitle: meta.playlistTitle } : {}),
    20	    });
    21	  }
    22	  async claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }> {
    23	    const idx = indexStore.readIndex(p.indexKey);
    24	    const position = idx.videos.length;
    25	    const serialNumber = nextSerial(idx.videos);
    26	    // reserve the slot with a minimal valid Video; real data arrives via upsertVideo
    27	    indexStore.upsertVideo(p.indexKey, { id: videoId, serialNumber } as Video);
    28	    return { position, serialNumber };
    29	  }
    30	  async upsertVideo(p: Principal, video: Video): Promise<void> {
    31	    indexStore.upsertVideo(p.indexKey, video);
    32	  }
    33	  // Stage 3 (§5.1/§5.7): the PRODUCTION Class-B write path (review + regenerate routes call
    34	  // this, not updateVideoAnnotations — see the allowlist-parity note below). When `fields`
    35	  // carries a Class-B key (set or explicit clear via `undefined`), stamp
    36	  // `annotationsEditedAt.<field>` — user path (no opts) → now(), sync path (opts.editedAt)
    37	  // → the caller-supplied source timestamp. A non-Class-B write (e.g. MD-finalize /
    38	  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
    39	  // NOT bump annotationsEditedAt — those are separate, non-human-edit signals.
    40	  async updateVideoFields(
    41	    p: Principal,
    42	    id: string,
    43	    fields: Partial<Video>,
    44	    opts?: { editedAt?: string },
    45	  ): Promise<void> {
    46	    // NOTE: filters inline against the CLASS_B_ANNOTATION_KEYS constant (not
    47	    // indexStore.classBKeysIn) — callers that `jest.mock('lib/index-store')` (auto-mock,
    48	    // no factory) replace every FUNCTION export with a bare jest.fn(), but a plain array
    49	    // constant survives untouched, so this stays correct under that mocking pattern too.
    50	    const changed = Object.keys(fields).filter((k): k is indexStore.ClassBAnnotationKey =>
    51	      (indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k),
    52	    );
    53	    let toWrite: Partial<Video> = fields;
    54	    if (changed.length > 0) {
    55	      const idx = indexStore.readIndex(p.indexKey);
    56	      const existing = idx.videos.find((v) => v.id === id);
    57	      const editedAt = opts?.editedAt ?? new Date().toISOString();
    58	      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing?.annotationsEditedAt ?? {}) };
    59	      for (const k of changed) at[k] = editedAt;
    60	      toWrite = { ...fields, annotationsEditedAt: at };
    61	    }
    62	    indexStore.updateVideoFields(p.indexKey, id, toWrite);
    63	  }
    64	  async bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void> {
    65	    for (const { videoId, fields } of patches) indexStore.updateVideoFields(p.indexKey, videoId, fields);
    66	  }
    67	  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    68	    const idx = indexStore.readIndex(p.indexKey);
    69	    const filtered = idx.videos.filter((v) => v.id !== videoId);
    70	    if (filtered.length === idx.videos.length) return; // id not present — no-op
    71	    indexStore.writeIndex(p.indexKey, { ...idx, videos: filtered });
    72	  }
    73	  async resolvePlaylistId(): Promise<string> {
    74	    throw new Error('resolvePlaylistId is cloud-only (unsupported on the local backend)');
    75	  }
    76	  async deletePlaylist(): Promise<void> {
    77	    throw new Error('deletePlaylist is cloud-only (unsupported on the local backend)');
    78	  }
    79	  // Local parity for the cloud conditional update (Task 3): fills playlistTitle only
    80	  // when currently absent/null in the JSON index; a no-op otherwise.
    81	  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
    82	    const idx = indexStore.readIndex(p.indexKey);
    83	    if (idx.playlistTitle) return { updated: false };
    84	    indexStore.writeIndex(p.indexKey, { ...idx, playlistTitle: title });
    85	    return { updated: true };
    86	  }
    87	  async listPlaylists(): Promise<PlaylistSummary[]> {
    88	    throw new Error('listPlaylists is cloud-only');
    89	  }
    90	  // Interface-shape parity only — not on a local runtime path (the local review route
    91	  // branch is unchanged and still calls updateVideoFields directly). Allowlist applied
    92	  // in-process (the cloud impl enforces it server-side, in SQL); `undefined` values are
    93	  // dropped by JSON.stringify on write, matching updateVideoFields' existing clear-by-
    94	  // undefined convention (see app/api/videos/[id]/review/route.ts serveLocal).
    95	  //
    96	  // Stage 3 (§5.1/§5.7, round-2 N3): this IS the sync loser-write path for a Class-B field
    97	  // (e.g. corrections) — the allowlist widened to include 'corrections' (was silently
    98	  // dropped), and a set/clear of any Class-B key stamps annotationsEditedAt: user path (no
    99	  // opts) → now(), sync path (opts.editedAt) → the caller-supplied source timestamp.
   100	  async updateVideoAnnotations(
   101	    p: Principal,
   102	    videoId: string,
   103	    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
   104	    clear: ('personalScore' | 'personalNote' | 'corrections')[],
   105	    opts?: { editedAt?: string },
   106	  ): Promise<{ found: boolean }> {
   107	    const idx = indexStore.readIndex(p.indexKey);
   108	    const existing = idx.videos.find((v) => v.id === videoId);
   109	    if (!existing) return { found: false };
   110	
   111	    const allow = new Set(['personalScore', 'personalNote', 'archived', 'corrections']);
   112	    const fields: Partial<Video> = {};
   113	    const changed: indexStore.ClassBAnnotationKey[] = [];
   114	    for (const [k, v] of Object.entries(set)) {
   115	      if (allow.has(k)) {
   116	        (fields as Record<string, unknown>)[k] = v;
   117	        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
   118	          changed.push(k as indexStore.ClassBAnnotationKey);
   119	        }
   120	      }
   121	    }
   122	    for (const k of clear) {
   123	      if (allow.has(k)) {
   124	        (fields as Record<string, unknown>)[k] = undefined;
   125	        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
   126	          changed.push(k as indexStore.ClassBAnnotationKey);
   127	        }
   128	      }
   129	    }
   130	    if (changed.length > 0) {
   131	      const editedAt = opts?.editedAt ?? new Date().toISOString();
   132	      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing.annotationsEditedAt ?? {}) };
   133	      for (const k of changed) at[k] = editedAt;
   134	      fields.annotationsEditedAt = at;
   135	    }
   136	    indexStore.updateVideoFields(p.indexKey, videoId, fields);
   137	    return { found: true };
   138	  }
   139	
   140	  async reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void> {
   141	    const present = new Set(currentPlaylistIds);
   142	    const idx = indexStore.readIndex(p.indexKey);
   143	    for (const v of idx.videos) {
   144	      const inPlaylist = present.has(v.id);
   145	      // Mirror original pipeline logic: only touch videos whose archive state should change.
   146	      // A video with removedFromPlaylist=true that is still absent was already handled on a
   147	      // prior sync (or the user manually un-archived it) — leave it untouched.
   148	      if (!inPlaylist && !v.removedFromPlaylist) {
   149	        indexStore.updateVideoFields(p.indexKey, v.id, { archived: true, removedFromPlaylist: true } as Partial<Video>);
   150	      } else if (inPlaylist && v.removedFromPlaylist) {
   151	        indexStore.updateVideoFields(p.indexKey, v.id, { archived: false, removedFromPlaylist: false } as Partial<Video>);
   152	      }
   153	    }
   154	  }
   155	}
   156	
   157	export const localMetadataStore = new LocalFsMetadataStore();
     1	import type { SupabaseClient } from '@supabase/supabase-js';
     2	import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
     3	import type { Principal } from '@/lib/storage/principal';
     4	import type { PlaylistIndex, Video } from '@/types';
     5	import { emptyPlaylistIndex } from '@/lib/storage/empty-index';
     6	
     7	// ---------------------------------------------------------------------------
     8	// stripComputed: drop the DB-computed `updatedAt` and `summaryReady` keys
     9	// before any write to `videos.data`. readIndex() surfaces `updatedAt`
    10	// (sourced from the `updated_at` column/trigger) and `summaryReady` (derived
    11	// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
    12	// object for read consumers; neither must ever round-trip back into the
    13	// jsonb payload on a write — `updatedAt`'s source of truth is the column/
    14	// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
    15	// itself, so persisting a stale derived boolean would let it drift from the
    16	// artifact it's supposed to reflect.
    17	// ---------------------------------------------------------------------------
    18	function stripComputed<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
    19	  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
    20	  return rest;
    21	}
    22	
    23	export class SupabaseMetadataStore implements MetadataStore {
    24	  constructor(private client: SupabaseClient) {}
    25	
    26	  // ---------------------------------------------------------------------------
    27	  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
    28	  // ---------------------------------------------------------------------------
    29	  async readIndex(p: Principal): Promise<PlaylistIndex> {
    30	    const { data: pl, error: plErr } = await this.client
    31	      .from('playlists')
    32	      .select('id, playlist_url, playlist_title')
    33	      .eq('playlist_key', p.indexKey)
    34	      .maybeSingle();
    35	    if (plErr) throw plErr;
    36	    if (!pl) return emptyPlaylistIndex(p);
    37	
    38	    const { data: rows, error: vErr } = await this.client
    39	      .from('videos')
    40	      .select('data, updated_at')
    41	      .eq('playlist_id', pl.id)
    42	      .order('position', { ascending: true });
    43	    if (vErr) throw vErr;
    44	
    45	    return {
    46	      playlistUrl: pl.playlist_url,
    47	      outputFolder: p.indexKey,
    48	      ...(pl.playlist_title ? { playlistTitle: pl.playlist_title } : {}),
    49	      videos: (rows ?? []).map((r) => ({
    50	        ...(r.data as Video),
    51	        updatedAt: r.updated_at as string,
    52	        summaryReady:
    53	          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
    54	            .artifacts?.summaryMd?.status === 'promoted',
    55	      })),
    56	    };
    57	  }
    58	
    59	  // ---------------------------------------------------------------------------
    60	  // setPlaylistMeta: upsert on (owner_id, playlist_key).
    61	  // owner_id has NO column default (NOT NULL in schema); must be supplied from
    62	  // the caller's JWT via auth.getUser(). The RLS with-check enforces
    63	  // owner_id = auth.uid() — passing any other value is rejected by the DB.
    64	  // ---------------------------------------------------------------------------
    65	  async setPlaylistMeta(
    66	    p: Principal,
    67	    meta: { playlistUrl: string; playlistTitle?: string },
    68	  ): Promise<void> {
    69	    const { data: userData } = await this.client.auth.getUser();
    70	    const ownerId = userData?.user?.id;
    71	    if (!ownerId) throw new Error('setPlaylistMeta: no authenticated user');
    72	
    73	    const { error } = await this.client.from('playlists').upsert(
    74	      {
    75	        owner_id: ownerId,
    76	        playlist_key: p.indexKey,
    77	        playlist_url: meta.playlistUrl,
    78	        playlist_title: meta.playlistTitle ?? null,
    79	      },
    80	      { onConflict: 'owner_id,playlist_key' },
    81	    );
    82	    if (error) throw error;
    83	  }
    84	
    85	  // ---------------------------------------------------------------------------
    86	  // claimVideoSlot: RPC appends a reservation row and returns position + serial.
    87	  // ---------------------------------------------------------------------------
    88	  async claimVideoSlot(
    89	    p: Principal,
    90	    videoId: string,
    91	  ): Promise<{ position: number; serialNumber: number }> {
    92	    const id = await this.requirePlaylistId(p);
    93	    const { data, error } = await this.client.rpc('claim_video_slot', {
    94	      p_playlist_id: id,
    95	      p_video_id: videoId,
    96	    });
    97	    if (error) throw error;
    98	    const row = Array.isArray(data) ? data[0] : data;
    99	    return { position: row.position, serialNumber: row.serial_number };
   100	  }
   101	
   102	  // ---------------------------------------------------------------------------
   103	  // upsertVideo: UPDATE the reservation row already created by claimVideoSlot.
   104	  // ---------------------------------------------------------------------------
   105	  async upsertVideo(p: Principal, video: Video): Promise<void> {
   106	    const id = await this.requirePlaylistId(p);
   107	    const { error } = await this.client
   108	      .from('videos')
   109	      .update({ data: stripComputed(video) })
   110	      .eq('playlist_id', id)
   111	      .eq('video_id', video.id);
   112	    if (error) throw error;
   113	  }
   114	
   115	  // ---------------------------------------------------------------------------
   116	  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
   117	  // modify-write races; deep-merges the `artifacts` sub-object).
   118	  // Stage 3 (§5.1/§5.7): merge_video_data (0021) stamps annotationsEditedAt server-side
   119	  // when p_fields carries a Class-B key (personalNote/personalScore/corrections) — this
   120	  // just needs to forward the caller's sync-path timestamp (opts.editedAt) as p_edited_at
   121	  // when present; the RPC defaults to now() for the user-edit path when omitted.
   122	  // ---------------------------------------------------------------------------
   123	  async updateVideoFields(
   124	    p: Principal,
   125	    videoId: string,
   126	    fields: Partial<Video>,
   127	    opts?: { editedAt?: string },
   128	  ): Promise<void> {
   129	    const id = await this.requirePlaylistId(p);
   130	    const { error } = await this.client.rpc('merge_video_data', {
   131	      p_playlist_id: id,
   132	      p_video_id: videoId,
   133	      p_fields: stripComputed(fields),
   134	      ...(opts?.editedAt ? { p_edited_at: opts.editedAt } : {}),
   135	    });
   136	    if (error) throw error;
   137	  }
   138	
   139	  // ---------------------------------------------------------------------------
   140	  // bulkUpdateVideoFields: same merge semantics in one transaction.
   141	  // p_patches shape must match the RPC: [{ video_id, fields }].
   142	  // ---------------------------------------------------------------------------
   143	  async bulkUpdateVideoFields(
   144	    p: Principal,
   145	    patches: { videoId: string; fields: Partial<Video> }[],
   146	  ): Promise<void> {
   147	    const id = await this.requirePlaylistId(p);
   148	    const { error } = await this.client.rpc('merge_video_data_bulk', {
   149	      p_playlist_id: id,
   150	      p_patches: patches.map((x) => ({ video_id: x.videoId, fields: stripComputed(x.fields) })),
   151	    });
   152	    if (error) throw error;
   153	  }
   154	
   155	  // ---------------------------------------------------------------------------
   156	  // reconcilePlaylistMembership: archive/restore by membership in one txn.
   157	  // ---------------------------------------------------------------------------
   158	  async reconcilePlaylistMembership(
   159	    p: Principal,
   160	    currentPlaylistIds: string[],
   161	  ): Promise<void> {
   162	    const id = await this.requirePlaylistId(p);
   163	    const { error } = await this.client.rpc('reconcile_membership', {
   164	      p_playlist_id: id,
   165	      p_present: currentPlaylistIds,
   166	    });
   167	    if (error) throw error;
   168	  }
   169	
   170	  // ---------------------------------------------------------------------------
   171	  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
   172	  // ---------------------------------------------------------------------------
   173	  async deleteVideo(p: Principal, videoId: string): Promise<void> {
   174	    const id = await this.requirePlaylistId(p);
   175	    const { error } = await this.client
   176	      .from('videos')
   177	      .delete()
   178	      .eq('playlist_id', id)
   179	      .eq('video_id', videoId);
   180	    if (error) throw error;
   181	  }
   182	
   183	  // ---------------------------------------------------------------------------
   184	  // resolvePlaylistId: upsert the (owner, playlist_key) row and return its id
   185	  // atomically. Owner-correct by construction (the upserted row carries
   186	  // owner_id); never a playlist_key-only select.
   187	  // ---------------------------------------------------------------------------
   188	  async resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string> {
   189	    const { data: userData } = await this.client.auth.getUser();
   190	    const ownerId = userData?.user?.id;
   191	    if (!ownerId) throw new Error('resolvePlaylistId: no authenticated user');
   192	    const { data, error } = await this.client.from('playlists')
   193	      .upsert({ owner_id: ownerId, playlist_key: p.indexKey, playlist_url: playlistUrl },
   194	        { onConflict: 'owner_id,playlist_key' })
   195	      .select('id').single();
   196	    if (error) throw error;
   197	    return data.id as string;
   198	  }
   199	
   200	  // ---------------------------------------------------------------------------
   201	  // setPlaylistTitleIfNull: conditional update — fills playlist_title ONLY when it is
   202	  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
   203	  // clobbered. Scoped by owner_id (from auth.getUser, mirroring setPlaylistMeta) and
   204	  // playlist_key (p.indexKey) — no separate listId param. `.select('id')` on the update
   205	  // lets us derive `updated` from whether a row actually matched (and was updated), not
   206	  // just whether the statement ran — a no-op conditional update returns an empty array.
   207	  // ---------------------------------------------------------------------------
   208	  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
   209	    const { data: userData } = await this.client.auth.getUser();
   210	    const ownerId = userData?.user?.id;
   211	    if (!ownerId) throw new Error('setPlaylistTitleIfNull: no authenticated user');
   212	
   213	    const { data, error } = await this.client
   214	      .from('playlists')
   215	      .update({ playlist_title: title })
   216	      .eq('owner_id', ownerId)
   217	      .eq('playlist_key', p.indexKey)
   218	      .is('playlist_title', null)
   219	      .select('id');
   220	    if (error) throw error;
   221	    return { updated: (data?.length ?? 0) > 0 };
   222	  }
   223	
   224	  // ---------------------------------------------------------------------------
   225	  // listPlaylists: cloud-only. Session client + RLS (owner_id = auth.uid()) already
   226	  // scopes this, but the explicit .eq('owner_id', ownerId) is defense-in-depth. Ordered
   227	  // by playlist_title (nulls last) then created_at — created_at MUST be in the select
   228	  // since it is both an ORDER BY column and part of the returned PlaylistSummary.
   229	  // ---------------------------------------------------------------------------
   230	  async listPlaylists(ownerId: string): Promise<PlaylistSummary[]> {
   231	    const { data, error } = await this.client
   232	      .from('playlists')
   233	      .select('id, playlist_key, playlist_url, playlist_title, created_at')
   234	      .eq('owner_id', ownerId)
   235	      .order('playlist_title', { nullsFirst: false })
   236	      .order('created_at');
   237	    if (error) throw error;
   238	    return (data ?? []).map((r) => ({
   239	      id: r.id,
   240	      playlistKey: r.playlist_key,
   241	      playlistUrl: r.playlist_url,
   242	      playlistTitle: r.playlist_title,
   243	      createdAt: r.created_at,
   244	    }));
   245	  }
   246	
   247	  // ---------------------------------------------------------------------------
   248	  // updateVideoAnnotations: distinct write path from updateVideoFields/merge_video_data
   249	  // (unchanged). The allowlist ({personalScore, personalNote, corrections, archived}) and
   250	  // the owner_id = auth.uid() guard are enforced IN SQL by update_video_annotations — this
   251	  // is the sole caller-facing surface for personal-annotation writes; no p_owner is
   252	  // ever sent. The RPC returns an integer row-count; > 0 means the row existed and was
   253	  // updated under the caller's ownership.
   254	  // Stage 3 (§5.1/§5.7): 'corrections' is now allowlisted server-side (0021), and the RPC
   255	  // stamps annotationsEditedAt per Class-B field touched. `opts.editedAt` forwards the
   256	  // sync-path source timestamp as p_edited_at; omitted on the user-edit path so the RPC's
   257	  // `default now()` applies.
   258	  // ---------------------------------------------------------------------------
   259	  async updateVideoAnnotations(
   260	    p: Principal,

codex
The companion matrix itself is easy to enumerate: sender match always ships; otherwise the receiver match keeps without flag; receiver hashed mismatch deletes; receiver none/unknown/legacy keeps and flags. I’m now checking whether the inputs into that matrix have the promised meanings on both stores.
exec
/bin/bash -lc "nl -ba lib/storage/supabase/supabase-metadata-store.ts | sed -n '260,420p' && nl -ba lib/storage/local/local-blob-store.ts | sed -n '1,220p' && nl -ba lib/storage/supabase/supabase-blob-store.ts | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   260	    p: Principal,
   261	    videoId: string,
   262	    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
   263	    clear: ('personalScore' | 'personalNote' | 'corrections')[],
   264	    opts?: { editedAt?: string },
   265	  ): Promise<{ found: boolean }> {
   266	    const id = await this.requirePlaylistId(p);
   267	    const { data, error } = await this.client.rpc('update_video_annotations', {
   268	      p_playlist_id: id,
   269	      p_video_id: videoId,
   270	      p_set: set,
   271	      p_clear: clear,
   272	      ...(opts?.editedAt ? { p_edited_at: opts.editedAt } : {}),
   273	    });
   274	    if (error) throw error;
   275	    return { found: (data ?? 0) > 0 };
   276	  }
   277	
   278	  // ---------------------------------------------------------------------------
   279	  // deletePlaylist: hard-delete a playlist row owned by the caller (Task 8).
   280	  // RLS already scopes DELETE to owner_id = auth.uid(); the explicit .eq('owner_id')
   281	  // is defense-in-depth, matching listPlaylists/setPlaylistTitleIfNull convention.
   282	  // T6's cascade FKs (0019) remove the playlist's videos/jobs/share_tokens as a side
   283	  // effect — no separate cleanup calls here. A non-owner/nonexistent id deletes 0 rows
   284	  // without erroring.
   285	  // ---------------------------------------------------------------------------
   286	  async deletePlaylist(p: Principal, playlistId: string): Promise<void> {
   287	    const { data: userData } = await this.client.auth.getUser();
   288	    const ownerId = userData?.user?.id;
   289	    if (!ownerId) throw new Error('deletePlaylist: no authenticated user');
   290	
   291	    const { error } = await this.client
   292	      .from('playlists')
   293	      .delete()
   294	      .eq('id', playlistId)
   295	      .eq('owner_id', ownerId);
   296	    if (error) throw error;
   297	  }
   298	
   299	  // ---------------------------------------------------------------------------
   300	  // Helpers
   301	  // ---------------------------------------------------------------------------
   302	
   303	  private async playlistId(p: Principal): Promise<string | null> {
   304	    const { data, error } = await this.client
   305	      .from('playlists')
   306	      .select('id')
   307	      .eq('playlist_key', p.indexKey)
   308	      .maybeSingle();
   309	    if (error) throw error;
   310	    return data?.id ?? null;
   311	  }
   312	
   313	  private async requirePlaylistId(p: Principal): Promise<string> {
   314	    const id = await this.playlistId(p);
   315	    if (!id) throw new Error(`playlist not found for indexKey=${p.indexKey}`);
   316	    return id;
   317	  }
   318	}
     1	import fs from 'fs'; import path from 'path'; import crypto from 'crypto';
     2	import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
     3	import { assertLogicalKey } from '@/lib/storage/blob-store';
     4	import type { Principal } from '@/lib/storage/principal';
     5	
     6	/** Byte-for-byte the current -data layout: physical path = join(indexKey, key). */
     7	export class LocalFsBlobStore implements BlobStore {
     8	  /** get/exists below return null/false ONLY on ENOENT and rethrow every other errno, so a null
     9	   *  here genuinely means the object is not there. */
    10	  readonly provesAbsence = true;
    11	
    12	  private abs(p: Principal, key: string): string { assertLogicalKey(key); return path.join(p.indexKey, key); }
    13	
    14	  // contentType unused locally but required by the BlobStore interface (cloud impls will use it)
    15	  async put(p: Principal, key: string, bytes: Buffer, _contentType: string): Promise<void> {
    16	    const dest = this.abs(p, key); fs.mkdirSync(path.dirname(dest), { recursive: true });
    17	    const tmp = dest + '.' + crypto.randomUUID() + '.tmp';
    18	    try { fs.writeFileSync(tmp, bytes); fs.renameSync(tmp, dest); }
    19	    catch (e) { try { fs.unlinkSync(tmp); } catch {} throw e; }
    20	  }
    21	
    22	  async get(p: Principal, key: string): Promise<Buffer | null> {
    23	    try { return fs.readFileSync(this.abs(p, key)); }
    24	    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
    25	  }
    26	
    27	  async exists(p: Principal, key: string): Promise<boolean> {
    28	    try { fs.statSync(this.abs(p, key)); return true; }
    29	    catch (e: any) { if (e.code === 'ENOENT') return false; throw e; }
    30	  }
    31	
    32	  async delete(p: Principal, key: string): Promise<void> {
    33	    try { fs.unlinkSync(this.abs(p, key)); } catch (e: any) { if (e.code !== 'ENOENT') throw e; }
    34	  }
    35	
    36	  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    37	    assertLogicalKey(key);  // validate before building tempKey — a leading '/' on key wouldn't appear on tempKey
    38	    const tempKey = `_staging/${crypto.randomUUID()}/${key}`;
    39	    await this.put(p, tempKey, bytes, contentType);
    40	    return { principal: p, tempKey, finalKey: key };
    41	  }
    42	
    43	  async promote(ref: StagedRef): Promise<void> {
    44	    const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
    45	    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
    46	    fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
    47	  }
    48	
    49	  // '' → path.join(indexKey, '') === indexKey, i.e. the playlist's own index dir (intended
    50	  // target, not above it). force:true makes an absent path a no-op (ENOENT-safe).
    51	  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    52	    assertLogicalKey(prefix);
    53	    await fs.promises.rm(path.join(p.indexKey, prefix), { recursive: true, force: true });
    54	  }
    55	
    56	  async list(p: Principal, prefix: string): Promise<string[]> {
    57	    assertLogicalKey(prefix);
    58	    const root = path.join(p.indexKey, prefix);
    59	    let entries: string[];
    60	    try {
    61	      entries = await fs.promises.readdir(root, { recursive: true }) as string[];
    62	    } catch (e) {
    63	      if ((e as NodeJS.ErrnoException).code === 'ENOENT') return [];
    64	      throw e;
    65	    }
    66	    const out: string[] = [];
    67	    for (const rel of entries) {
    68	      const full = path.join(root, rel);
    69	      if ((await fs.promises.stat(full)).isFile()) {
    70	        out.push(path.posix.join(prefix.replace(/\/$/, ''), rel.split(path.sep).join('/')));
    71	      }
    72	    }
    73	    return out;
    74	  }
    75	}
    76	
    77	export const localBlobStore = new LocalFsBlobStore();
     1	import crypto from 'crypto';
     2	import type { SupabaseClient } from '@supabase/supabase-js';
     3	import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
     4	import { assertLogicalKey } from '@/lib/storage/blob-store';
     5	import type { Principal } from '@/lib/storage/principal';
     6	
     7	export class SupabaseBlobStore implements BlobStore {
     8	  /** `get` swallows EVERY download failure into null (see the note on it below) and `exists` is
     9	   *  defined in terms of `get`, so this backend can never prove an object is absent. */
    10	  readonly provesAbsence = false;
    11	
    12	  constructor(private client: SupabaseClient, private bucket: string) {}
    13	
    14	  /** Server-side owner prefix — never a client absolute path. */
    15	  private objectKey(p: Principal, key: string): string {
    16	    assertLogicalKey(key);
    17	    return `${p.id}/${p.indexKey}/${key}`;
    18	  }
    19	
    20	  private b() { return this.client.storage.from(this.bucket); }
    21	
    22	  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    23	    const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
    24	    if (error) throw error;
    25	  }
    26	
    27	  async get(p: Principal, key: string): Promise<Buffer | null> {
    28	    const { data, error } = await this.b().download(this.objectKey(p, key));
    29	    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
    30	    // so a null here does NOT prove the object is absent. Callers that treat "no bytes" as a
    31	    // semantic fact (e.g. "this replica holds no MD") must corroborate it against the record that
    32	    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately
    33	    // left as-is: shared with already-merged read paths where absent-vs-unreadable is immaterial.
    34	    // Note the LOCAL blob store differs — it returns null only on ENOENT and throws otherwise.
    35	    if (error) return null;
    36	    return Buffer.from(await data.arrayBuffer());
    37	  }
    38	
    39	  async exists(p: Principal, key: string): Promise<boolean> {
    40	    return (await this.get(p, key)) !== null;
    41	  }
    42	
    43	  async delete(p: Principal, key: string): Promise<void> {
    44	    const { error } = await this.b().remove([this.objectKey(p, key)]);
    45	    if (error) throw error;
    46	  }
    47	
    48	  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    49	    assertLogicalKey(key); // validate before building tempKey — reject '/absolute' before any upload
    50	    const tempKey = `_staging/${crypto.randomUUID()}/${key}`; // per-attempt-unique (ports local-blob-store)
    51	    await this.put(p, tempKey, bytes, contentType);
    52	    return { principal: p, tempKey, finalKey: key };
    53	  }
    54	
    55	  async promote(ref: StagedRef): Promise<void> {
    56	    const from = this.objectKey(ref.principal, ref.tempKey);
    57	    const to = this.objectKey(ref.principal, ref.finalKey);
    58	    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    59	    if (await this.exists(ref.principal, ref.finalKey)) {
    60	      await this.b().remove([from]).catch(() => {});
    61	      return;
    62	    }
    63	    const { error } = await this.b().move(from, to);
    64	    if (error) {
    65	      // A concurrent promoter (worker job retry / re-run of the same MD key) may have won the race: destination-exists / source-missing.
    66	      // Re-check the final; treat a present final as success, else rethrow.
    67	      if (await this.exists(ref.principal, ref.finalKey)) {
    68	        await this.b().remove([from]).catch(() => {});
    69	        return;
    70	      }
    71	      throw error;
    72	    }
    73	  }
    74	
    75	  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    76	    assertLogicalKey(prefix);
    77	    const root = `${p.id}/${p.indexKey}/${prefix}`.replace(/\/$/, '');
    78	    const objectPaths = await this.collectObjectPaths(root);
    79	    for (let i = 0; i < objectPaths.length; i += 1000) {
    80	      const batch = objectPaths.slice(i, i + 1000);
    81	      const { error } = await this.b().remove(batch);
    82	      if (error) throw error;
    83	    }
    84	  }
    85	
    86	  async list(p: Principal, prefix: string): Promise<string[]> {
    87	    assertLogicalKey(prefix);
    88	    const ownerRoot = `${p.id}/${p.indexKey}/`;
    89	    const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
    90	    const full = await this.collectObjectPaths(dirPath); // returns full object paths (or [] if absent)
    91	    return full.map((f) => f.slice(ownerRoot.length)); // strip owner root → logical key
    92	  }
    93	
    94	  /** Recursively walks a Supabase Storage "directory" (non-recursive `.list`, paginated at
    95	   *  100/page) and returns every file's full object path. Folder entries surface with
    96	   *  `id === null` and are descended into; file entries (`id !== null`) are collected. */
    97	  private async collectObjectPaths(dirPath: string): Promise<string[]> {
    98	    const paths: string[] = [];
    99	    const limit = 100;
   100	    let offset = 0;
   101	    for (;;) {
   102	      const { data, error } = await this.b().list(dirPath, { limit, offset });
   103	      if (error) throw error;
   104	      const entries = data ?? [];
   105	      for (const entry of entries) {
   106	        const entryPath = `${dirPath}/${entry.name}`;
   107	        if (entry.id === null) {
   108	          paths.push(...(await this.collectObjectPaths(entryPath)));
   109	        } else {
   110	          paths.push(entryPath);
   111	        }
   112	      }
   113	      if (entries.length < limit) break;
   114	      offset += limit;
   115	    }
   116	    return paths;
   117	  }
   118	}

exec
/bin/bash -lc "nl -ba lib/html-doc/model-store.ts | sed -n '1,220p' && nl -ba lib/html-doc/read-model.ts | sed -n '1,240p' && nl -ba lib/html-doc/serve-summary-core.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import { z } from 'zod';
     2	import { MagazineModelSchema } from './types';
     3	import { localBlobStore } from '@/lib/storage/local/local-blob-store';
     4	import type { BlobStore, ReadOnlyBlobStore } from '@/lib/storage/blob-store';
     5	import type { Principal } from '@/lib/storage/principal';
     6	
     7	/**
     8	 * The persisted summary-model file: the Gemini transform output plus provenance.
     9	 * `sourceSections` is the section titles the model was built against — the drift guard the
    10	 * re-render path compares the current .md's section titles against.
    11	 * `generatorVersion` is optional so pre-1F-a local envelopes (written before this field existed)
    12	 * still parse; the cloud freshness gate requires it to `=== GENERATOR_VERSION`.
    13	 */
    14	export const ModelEnvelopeSchema = z
    15	  .object({
    16	    sourceMd: z.string().min(1),
    17	    generatedAt: z.string().min(1),
    18	    sourceSections: z.array(z.string()),
    19	    generatorVersion: z.string().min(1).optional(),
    20	    model: MagazineModelSchema,
    21	    // Stage 3 (§4.2): MD-body-only digest of the MD this model was generated from.
    22	    sourceMdHash: z.string().optional(),
    23	  });
    24	  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
    25	  // must not make an old reader's readModelEnvelope return null (§5.7 round-5 M-2).
    26	
    27	export type ModelEnvelope = z.infer<typeof ModelEnvelopeSchema>;
    28	
    29	const MODEL_KEY = (base: string) => `models/${base}.json`;
    30	
    31	function serialize(envelope: ModelEnvelope): Buffer {
    32	  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
    33	  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
    34	}
    35	
    36	/**
    37	 * The single model writer for BOTH the local generate path and the cloud serve path.
    38	 * `put` maps to Supabase `upload(upsert:true)` (atomic per object), so a re-generated model on
    39	 * drift / `generatorVersion` bump OVERWRITES the prior blob — the cache self-heals rather than
    40	 * getting stuck on a stale envelope. (The staged→promote protocol is create-if-absent and stays
    41	 * on the BlobStore for the worker's multi-blob MD commit — it is NOT used for the model.)
    42	 */
    43	export async function writeModelEnvelope(
    44	  principal: Principal,
    45	  base: string,
    46	  envelope: ModelEnvelope,
    47	  blobStore: BlobStore = localBlobStore,
    48	): Promise<void> {
    49	  await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
    50	}
    51	
    52	/** Read + validate. Returns null if absent, unparseable, or schema-invalid. */
    53	export async function readModelEnvelope(
    54	  principal: Principal,
    55	  base: string,
    56	  blobStore: ReadOnlyBlobStore = localBlobStore,
    57	): Promise<ModelEnvelope | null> {
    58	  const bytes = await blobStore.get(principal, MODEL_KEY(base));
    59	  if (!bytes) return null;
    60	  let json: unknown;
    61	  try {
    62	    json = JSON.parse(bytes.toString('utf-8'));
    63	  } catch {
    64	    console.warn(`[model-store] malformed JSON in models/${base}.json — ignoring`);
    65	    return null;
    66	  }
    67	  const parsed = ModelEnvelopeSchema.safeParse(json);
    68	  if (!parsed.success) {
    69	    console.warn(`[model-store] models/${base}.json failed schema validation — ignoring`);
    70	    return null;
    71	  }
    72	  return parsed.data;
    73	}
     1	import type { MagazineModel } from './types';
     2	import type { Principal } from '@/lib/storage/principal';
     3	import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';
     4	import { GENERATOR_VERSION } from './constants';
     5	import { readModelEnvelope } from './model-store';
     6	
     7	// GENERATE-FREE LEAF (spec D13/B18c): this module and its entire import graph must never
     8	// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
     9	// /s/[token] route therefore cannot pull in the charging code. Enforced by tests/lib/share/
    10	// import-guard.test.ts (a jest grep guard; the repo has no ESLint).
    11	
    12	export function sameTitles(
    13	  envelope: { sourceSections: string[] },
    14	  titles: string[],
    15	): boolean {
    16	  return envelope.sourceSections.length === titles.length &&
    17	    envelope.sourceSections.every((t, i) => t === titles[i]);
    18	}
    19	
    20	export function isFresh(
    21	  envelope: { sourceSections: string[]; generatorVersion?: string },
    22	  titles: string[],
    23	): boolean {
    24	  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
    25	}
    26	
    27	/** Read-only, generation-free: returns the cached model iff present AND fresh; otherwise
    28	 *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call). */
    29	export async function readFreshMagazineModel(args: {
    30	  blobStore: ReadOnlyBlobStore;
    31	  principal: Principal;
    32	  base: string;
    33	  titles: string[];
    34	}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }> {
    35	  const { blobStore, principal, base, titles } = args;
    36	  const existing = await readModelEnvelope(principal, base, blobStore);
    37	  if (existing && isFresh(existing, titles)) return { status: 'ok', model: existing.model };
    38	  return { status: 'not_ready' };
    39	}
    40	
    41	/** Title-stable read (spec D5): returns the cached model iff the envelope exists AND its section
    42	 *  titles match `titles` (generator version may differ — the version-bump case). Positionally
    43	 *  coherent to render against current markdown. Never reserves/generates (pure blob read). */
    44	export async function readTitleStableModel(args: {
    45	  blobStore: ReadOnlyBlobStore;
    46	  principal: Principal;
    47	  base: string;
    48	  titles: string[];
    49	}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'none' }> {
    50	  const { blobStore, principal, base, titles } = args;
    51	  const existing = await readModelEnvelope(principal, base, blobStore);
    52	  if (existing && sameTitles(existing, titles)) return { status: 'ok', model: existing.model };
    53	  return { status: 'none' };
    54	}
     1	import type { SupabaseClient } from '@supabase/supabase-js';
     2	import { getStorageBundle, getPrincipalFromSession, type StorageBundle } from '@/lib/storage/resolve';
     3	import { resolveOwnedPlaylistKey } from '@/lib/storage/serve-playlist';
     4	import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
     5	import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
     6	import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
     7	import type { Principal } from '@/lib/storage/principal';
     8	import type { Video } from '@/types';
     9	
    10	export type LoadResult =
    11	  | {
    12	      ok: true;
    13	      mdBytes: Buffer;
    14	      mdKey: string;
    15	      base: string;
    16	      title?: string;
    17	      principal: Principal;
    18	      playlistId: string;
    19	      video: Video;
    20	      bundle: StorageBundle;
    21	    }
    22	  | { ok: false; status: number; error: string };
    23	
    24	/**
    25	 * Two-stage split of `serveCloud`'s gate→read→resolve→render core (app/api/html/[id]/route.ts),
    26	 * split at the `resolveMagazineModel` boundary so both the HTML route (Task 7) and the PDF route
    27	 * (Task 8) can share it while the `format=md` no-charge short-circuit survives (D4 money invariant:
    28	 * the md path must read the blob and return WITHOUT ever calling resolveMagazineModel).
    29	 *
    30	 * Mirrors serveCloud lines ~45-83. Does NOT resolve/charge — that is stage 2 (resolveAndParse).
    31	 * Note: assertVideoId is done by the CALLER route in param validation (before auth, preserving the
    32	 * existing 400-before-401 ordering) — this helper does not repeat it.
    33	 */
    34	export async function loadSummaryForServe(
    35	  supabase: SupabaseClient,
    36	  a: { videoId: string; playlistId: string; userId: string },
    37	): Promise<LoadResult> {
    38	  const playlistKey = await resolveOwnedPlaylistKey(supabase, a.playlistId, a.userId); // owner-asserted (D6/D9)
    39	  if (!playlistKey) return { ok: false, status: 404, error: 'not found' };
    40	
    41	  const principal = getPrincipalFromSession({ userId: a.userId }, playlistKey);
    42	  const bundle = getStorageBundle({ supabaseClient: supabase }); // session-scoped, RLS-enforced (D5)
    43	  const index = await bundle.metadataStore.readIndex(principal);
    44	  const video = index.videos.find((v) => v.id === a.videoId) as Video | undefined;
    45	  if (!video) return { ok: false, status: 404, error: 'not found' };
    46	
    47	  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
    48	    .artifacts?.summaryMd;
    49	  const status = artifact?.status;
    50	  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
    51	  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)
    52	
    53	  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
    54	  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
    55	  // doesn't govern).
    56	  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
    57	  if (!mdKey) return { ok: false, status: 404, error: 'not found' };
    58	
    59	  // Task-2 guard: reject a corrupt/nested key BEFORE reading the blob (409, no blob fetch attempted).
    60	  try {
    61	    assertCloudSummaryMdKey(mdKey);
    62	  } catch {
    63	    return { ok: false, status: 409, error: 'corrupt summary key' };
    64	  }
    65	
    66	  const mdBytes = await bundle.blobStore.get(principal, mdKey);
    67	  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)
    68	
    69	  // IDENTITY COHERENCE (carried from serveCloud): `base` is the canonical, DB-persisted baseName,
    70	  // derived deterministically from the SAME summaryMd key the model store is keyed on.
    71	  const base = mdKey.replace(/\.md$/, '');
    72	
    73	  // M1 (1F-c whole-branch review): coerce a non-string/blank title to undefined defensively.
    74	  const rawTitle: unknown = (video as unknown as { title?: unknown }).title;
    75	  const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;
    76	
    77	  return { ok: true, mdBytes, mdKey, base, title, principal, playlistId: a.playlistId, video, bundle };
    78	}
    79	
    80	type OkLoad = Extract<LoadResult, { ok: true }>;
    81	
    82	// The resolved magazine model, typed straight off resolveMagazineModel's `ok` arm so Task 7/8
    83	// consumers get the real MagazineModel contract instead of `unknown`. (Task-6 review Minor.)
    84	type ResolvedModel = Extract<Awaited<ReturnType<typeof resolveMagazineModel>>, { status: 'ok' }>['model'];
    85	
    86	export type ResolveAndParseResult =
    87	  | { ok: true; parsed: ReturnType<typeof parseSummaryMarkdown>; model: ResolvedModel; stale: boolean }
    88	  | { ok: false; status: number; error: string };
    89	
    90	/**
    91	 * Stage 2: parse the markdown + resolve (and possibly charge for) the magazine model. Maps
    92	 * `resolveMagazineModel`'s ResolveResult (lib/html-doc/serve-doc.ts:26) to HTTP codes. Error
    93	 * strings below are copied VERBATIM from serveCloud (app/api/html/[id]/route.ts:101-105) — the
    94	 * existing html-download integration tests assert these exact strings. Do NOT paraphrase.
    95	 */
    96	export async function resolveAndParse(
    97	  supabase: SupabaseClient,
    98	  load: OkLoad,
    99	  signal?: AbortSignal,
   100	): Promise<ResolveAndParseResult> {
   101	  const mdBody = load.mdBytes.toString('utf-8');
   102	  const parsed = parseSummaryMarkdown(mdBody);
   103	  parsed.sourceMd = load.mdKey;
   104	
   105	  const resolved = await resolveMagazineModel({
   106	    supabaseClient: supabase,
   107	    blobStore: load.bundle.blobStore,
   108	    principal: load.principal,
   109	    playlistId: load.playlistId,
   110	    videoId: load.video.id,
   111	    base: load.base,
   112	    parsed,
   113	    language: load.video.language, // Video.language is already the 'en'|'ko' enum (types/index.ts:51)
   114	    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
   115	    signal,
   116	  });
   117	
   118	  switch (resolved.status) {
   119	    case 'denied': return { ok: false, status: 404, error: 'not found' };                                          // generic, no leak
   120	    case 'busy': return { ok: false, status: 503, error: 'generating, retry shortly' };                            // B6b
   121	    case 'attempts_exhausted': return { ok: false, status: 503, error: 'temporarily unavailable, try later' };     // B7f
   122	    case 'at_capacity': return { ok: false, status: 503, error: 'at capacity' };                                   // B6
   123	    case 'over_budget': return { ok: false, status: 503, error: 'daily refresh budget reached, try tomorrow' };    // D6/G1
   124	    case 'ok': return { ok: true, parsed, model: resolved.model, stale: resolved.stale === true };
   125	  }
   126	}

exec
/bin/bash -lc "nl -ba lib/index-store.ts | sed -n '1,180p' && nl -ba lib/cloud-sync/registry.ts | sed -n '1,120p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import crypto from 'crypto';
     2	import fs from 'fs';
     3	import os from 'os';
     4	import path from 'path';
     5	import type { PlaylistIndex, Video } from '../types';
     6	
     7	const INDEX_FILE = 'playlist-index.json';
     8	const VIDEO_ID_RE = /^[A-Za-z0-9_-]{1,20}$/;
     9	
    10	// Stage 3 Cloud Sync (§5.1/§5.7): Class-B ("human-edited") annotation fields — a set or a
    11	// clear of any of these stamps `annotationsEditedAt.<field>` (user path → now(), sync path
    12	// → the caller-supplied source timestamp). Shared by LocalFsMetadataStore's
    13	// updateVideoAnnotations and updateVideoFields so both write paths stamp identically.
    14	export const CLASS_B_ANNOTATION_KEYS = ['personalNote', 'personalScore', 'corrections'] as const;
    15	export type ClassBAnnotationKey = (typeof CLASS_B_ANNOTATION_KEYS)[number];
    16	
    17	/** Class-B keys present as OWN properties of `fields` (set to a value OR explicitly
    18	 *  cleared via `undefined`) — i.e. the keys that must stamp annotationsEditedAt. A key
    19	 *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
    20	 *  "changed" and must not trigger a stamp. */
    21	export function classBKeysIn(fields: Partial<Video>): ClassBAnnotationKey[] {
    22	  return Object.keys(fields).filter((k): k is ClassBAnnotationKey =>
    23	    (CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k),
    24	  );
    25	}
    26	
    27	// Fields retired by the PDF-generation removal (summaryPdf/deepDivePdf) and the
    28	// deep-dive removal (deepDiveMd/deepDiveHtml/deepDiveVersion). Index files written
    29	// before those efforts still carry these keys; strip them on read so the API never
    30	// re-serves dangling references to deleted files.
    31	const RETIRED_VIDEO_KEYS = [
    32	  'summaryPdf',
    33	  'deepDiveMd',
    34	  'deepDiveHtml',
    35	  'deepDivePdf',
    36	  'deepDiveVersion',
    37	] as const;
    38	
    39	function stripRetiredKeys(index: PlaylistIndex): PlaylistIndex {
    40	  for (const video of index.videos ?? []) {
    41	    for (const key of RETIRED_VIDEO_KEYS) {
    42	      delete (video as Record<string, unknown>)[key];
    43	    }
    44	  }
    45	  return index;
    46	}
    47	
    48	export function assertOutputFolder(outputFolder: string): void {
    49	  const resolved = path.resolve(outputFolder);
    50	  const home = os.homedir();
    51	  const withinHome = (p: string) => p === home || p.startsWith(home + path.sep);
    52	
    53	  if (!withinHome(resolved)) {
    54	    throw Object.assign(new Error(`outputFolder outside home directory: ${resolved}`), { statusCode: 400 });
    55	  }
    56	
    57	  // Also check the real path to catch symlinks that point outside home
    58	  try {
    59	    const real = fs.realpathSync.native(resolved);
    60	    if (!withinHome(real)) {
    61	      throw Object.assign(new Error(`outputFolder resolves outside home directory via symlink: ${real}`), { statusCode: 400 });
    62	    }
    63	  } catch (err: unknown) {
    64	    const nodeErr = err as NodeJS.ErrnoException;
    65	    if ((nodeErr as any).statusCode === 400) throw err;
    66	    // ENOENT means path doesn't exist yet — no symlink to follow, trust resolved path
    67	    if (nodeErr.code !== 'ENOENT') throw err;
    68	  }
    69	}
    70	
    71	export function assertVideoId(id: string): void {
    72	  if (!VIDEO_ID_RE.test(id)) {
    73	    throw Object.assign(new Error(`invalid videoId: ${id}`), { statusCode: 400 });
    74	  }
    75	}
    76	
    77	function indexPath(outputFolder: string): string {
    78	  return path.join(outputFolder, INDEX_FILE);
    79	}
    80	
    81	export function readIndex(outputFolder: string): PlaylistIndex {
    82	  assertOutputFolder(outputFolder);
    83	  const filePath = indexPath(outputFolder);
    84	  try {
    85	    const raw = fs.readFileSync(filePath, 'utf-8');
    86	    return stripRetiredKeys(JSON.parse(raw) as PlaylistIndex);
    87	  } catch (err: unknown) {
    88	    const nodeErr = err as NodeJS.ErrnoException;
    89	    if (nodeErr.code === 'ENOENT') {
    90	      // Distinguish missing file from missing directory
    91	      try { fs.lstatSync(outputFolder); } catch {
    92	        throw Object.assign(new Error(`Output folder does not exist: ${outputFolder}`), { statusCode: 400, cause: err });
    93	      }
    94	      return { playlistUrl: '', outputFolder, videos: [] };
    95	    }
    96	    throw Object.assign(new Error(`Failed to read ${filePath}: ${nodeErr.message}`), { cause: err });
    97	  }
    98	}
    99	
   100	export function writeIndex(outputFolder: string, index: PlaylistIndex): void {
   101	  assertOutputFolder(outputFolder);
   102	  for (const video of index.videos) {
   103	    assertVideoId(video.id);
   104	  }
   105	  const filePath = indexPath(outputFolder);
   106	  const tmpPath = filePath + '.' + crypto.randomUUID() + '.tmp';
   107	  try {
   108	    fs.writeFileSync(tmpPath, JSON.stringify(index, null, 2), 'utf-8');
   109	    fs.renameSync(tmpPath, filePath);
   110	  } catch (err) {
   111	    try { fs.unlinkSync(tmpPath); } catch { /* ignore cleanup error */ }
   112	    throw err;
   113	  }
   114	}
   115	
   116	export function upsertVideo(outputFolder: string, video: Video): void {
   117	  assertOutputFolder(outputFolder);
   118	  assertVideoId(video.id);
   119	  const index = readIndex(outputFolder);
   120	  const i = index.videos.findIndex((v) => v.id === video.id);
   121	  // Stamp only the single mutated video — never touch writeIndex, which
   122	  // rewrites the whole playlist file and would re-stamp every sibling video.
   123	  const stamped: Video = { ...video, updatedAt: new Date().toISOString() };
   124	  if (i === -1) {
   125	    index.videos.push(stamped);
   126	  } else {
   127	    index.videos[i] = stamped;
   128	  }
   129	  writeIndex(outputFolder, index);
   130	}
   131	
   132	export function updateVideoFields(outputFolder: string, id: string, fields: Partial<Video>): void {
   133	  assertOutputFolder(outputFolder);
   134	  assertVideoId(id);
   135	  const index = readIndex(outputFolder);
   136	  const i = index.videos.findIndex((v) => v.id === id);
   137	  if (i === -1) {
   138	    throw new Error(`Video not found in index: ${id}`);
   139	  }
   140	  // Exclude id from fields — callers must not change a video's identity
   141	  const { id: _discarded, ...safeFields } = fields;
   142	  // Stamp only the single mutated video — never touch writeIndex, which
   143	  // rewrites the whole playlist file and would re-stamp every sibling video.
   144	  index.videos[i] = { ...index.videos[i], ...safeFields, updatedAt: new Date().toISOString() };
   145	  writeIndex(outputFolder, index);
   146	}
     1	import { promises as fs } from 'fs';
     2	import path from 'path';
     3	import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
     4	import { localPrincipal } from '@/lib/storage/principal';
     5	
     6	/** H3 (round 4) — `playlistTitle` is carried because playlistMetaFor resolves the local registry
     7	 *  first; without it, a playlist present in BOTH replicas always produced a title-less meta, which
     8	 *  the cloud setPlaylistMeta upsert writes as an explicit NULL. Optional: a local index legitimately
     9	 *  may have no title (it is only set by the ingest/backfill paths). */
    10	export interface LocalPlaylist {
    11	  playlistKey: string; dataRoot: string; playlistUrl: string; playlistTitle?: string;
    12	}
    13	
    14	export function playlistKeyFromUrl(url: string): string | null {
    15	  if (!url) return null;
    16	  try {
    17	    const u = new URL(url);
    18	    return u.searchParams.get('list');
    19	  } catch { return null; }
    20	}
    21	
    22	/** Scan each data root's subdirectories for a playlist-index.json and derive its key. */
    23	export async function discoverLocalPlaylists(dataRoots: string[]): Promise<LocalPlaylist[]> {
    24	  const byKey = new Map<string, LocalPlaylist>();
    25	  for (const root of dataRoots) {
    26	    let entries: string[] = [];
    27	    try { entries = await fs.readdir(root); } catch { continue; }
    28	    for (const dir of entries) {
    29	      const candidate = path.join(root, dir);
    30	      const dataRoot = await resolveRootShape(candidate); // handles <dir> and <dir>/raw
    31	      if (!dataRoot) continue;
    32	      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
    33	      const key = playlistKeyFromUrl(idx.playlistUrl);
    34	      if (!key) continue;
    35	      if (!byKey.has(key)) {
    36	        byKey.set(key, {
    37	          playlistKey: key, dataRoot, playlistUrl: idx.playlistUrl,
    38	          ...(idx.playlistTitle ? { playlistTitle: idx.playlistTitle } : {}),
    39	        });
    40	      }
    41	    }
    42	  }
    43	  return [...byKey.values()];
    44	}
    45	
    46	async function resolveRootShape(candidate: string): Promise<string | null> {
    47	  for (const p of [candidate, path.join(candidate, 'raw')]) {
    48	    try { await fs.access(path.join(p, 'playlist-index.json')); return p; } catch { /* try next */ }
    49	  }
    50	  return null;
    51	}
    52	
    53	export function unionPlaylistKeys(local: LocalPlaylist[], cloudKeys: string[]): string[] {
    54	  return [...new Set([...local.map((l) => l.playlistKey), ...cloudKeys])];
    55	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '245,330p' && nl -ba lib/cloud-sync/reconcile-class-a.ts | sed -n '1,180p' && nl -ba lib/cloud-sync/reconcile-class-b.ts | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   245	}
   246	
   247	/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
   248	 *  side's values, so this is a true agreed baseline. */
   249	function baselineFromOneSided(
   250	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
   251	): VideoBaseline {
   252	  const classB = {} as VideoBaseline['classB'];
   253	  for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
   254	  return {
   255	    classA: {
   256	      docVersionMajor: classA.docVersionMajor,
   257	      mdGeneratedAt: classA.mdGeneratedAt,
   258	      mdCorrectionsHash: classA.mdCorrectionsHash,
   259	      mdHash: mdHashVal,
   260	    },
   261	    classB,
   262	  };
   263	}
   264	
   265	/** Behaviors #12 + F3 — apply each Class-B winner to the LOSER side, carrying the SOURCE timestamp
   266	 *  (never now()). A conflict is logged and, when the merge picked no winner (winner==='equal'), the
   267	 *  loser value is skipped (not written). Every write MUST land (found:true) or it throws — a no-op
   268	 *  write on an absent row would let buildBaseline record a false agreement. */
   269	async function applyClassBWinners(args: {
   270	  deps: SyncDeps; localP: Principal; cloudP: Principal; videoId: string;
   271	  merges: Record<HumanField, FieldMerge>; localSnap: HumanSnapshot; cloudSnap: HumanSnapshot;
   272	  dataRoot: string; key: string;
   273	}): Promise<{ merged: number; conflicts: number }> {
   274	  const { deps, localP, cloudP, videoId, merges, localSnap, cloudSnap, dataRoot, key } = args;
   275	  let merged = 0;
   276	  let conflicts = 0;
   277	
   278	  for (const f of FIELDS) {
   279	    const m = merges[f];
   280	    if (m.conflict) {
   281	      await appendConflict(dataRoot, key, {
   282	        video_id: videoId, class: 'B', field: f,
   283	        valueL: localSnap[f].value, valueR: cloudSnap[f].value,
   284	        reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
   285	      });
   286	      conflicts += 1;
   287	    }
   288	    if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write
   289	
   290	    // winner is on one side → the OTHER (loser) side receives the winning value.
   291	    const target: Side = m.winner === 'local'
   292	      ? { store: deps.cloud, p: cloudP, blob: deps.cloudBlob }
   293	      : { store: deps.local, p: localP, blob: deps.localBlob };
   294	    const set: Record<string, string | number> = {};
   295	    const clear: HumanField[] = [];
   296	    if (m.value === undefined) clear.push(f);
   297	    else set[f] = m.value;
   298	
   299	    const { found } = await target.store.updateVideoAnnotations(
   300	      target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
   301	    );
   302	    if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
   303	    merged += 1;
   304	  }
   305	  return { merged, conflicts };
   306	}
   307	
   308	/** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
   309	 *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
   310	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
   311	 *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
   312	async function transferClassA(
   313	  winner: Side, loser: Side, winnerVideo: Video, videoId: string,
   314	): Promise<{ mdHash: string; verified: boolean }> {
   315	  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   316	  if (body == null || !winnerVideo.summaryMd) {
   317	    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   318	  }
   319	  const h = mdHash(body);
   320	  const key = winnerVideo.summaryMd;
   321	
   322	  const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   323	  const staged = await loser.blob.get(loser.p, ref.tempKey);
   324	  if (!staged || mdHash(staged.toString('utf8')) !== h) {
   325	    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   326	  }
   327	  // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   328	  // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   329	  // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   330	  // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
     1	import type { ClassASignals } from './types';
     2	
     3	export interface ClassADecision {
     4	  action: 'skip' | 'copyToLocal' | 'copyToCloud';
     5	  needsRegen: boolean;
     6	}
     7	
     8	const current = (s: ClassASignals, cur: string): boolean => s.mdCorrectionsHash === cur;
     9	const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');
    10	
    11	export function reconcileClassA(args: {
    12	  local: ClassASignals;
    13	  cloud: ClassASignals;
    14	  reconciledCorrectionsHash: string;
    15	}): ClassADecision {
    16	  const { local, cloud, reconciledCorrectionsHash: cur } = args;
    17	  const lHas = local.mdHash != null;
    18	  const cHas = cloud.mdHash != null;
    19	
    20	  // Presence (§5.6 one-sided copy) — flag needsRegen when the SOLE MD is corrections-stale (R8, L2)
    21	  if (!lHas && !cHas) return { action: 'skip', needsRegen: false };
    22	  if (!lHas) return { action: 'copyToLocal', needsRegen: !current(cloud, cur) };
    23	  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };
    24	
    25	  const lCur = current(local, cur);
    26	  const cCur = current(cloud, cur);
    27	  const bothStale = !lCur && !cCur;
    28	
    29	  // Equal MD bodies: skip ONLY when both corrections-current, OR both stale AND same format.
    30	  // If currency OR format disagrees (even with identical bytes), fall through so the winning
    31	  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
    32	  if (local.mdHash === cloud.mdHash) {
    33	    if (lCur && cCur) return { action: 'skip', needsRegen: false };
    34	    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
    35	    // else: fall through to currency/format below.
    36	  }
    37	
    38	  // corrections-currency FIRST (a stale MD never overwrites a corrections-current one)
    39	  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
    40	  if (cCur && !lCur) return { action: 'copyToLocal', needsRegen: false };
    41	
    42	  // format (never downgrade)
    43	  if (local.docVersionMajor !== cloud.docVersionMajor) {
    44	    const winnerIsCloud = cloud.docVersionMajor > local.docVersionMajor;
    45	    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
    46	  }
    47	
    48	  // same major, different mdHash → recency-tiebreak (unify prose)
    49	  const winnerIsLocal = newer(local.mdGeneratedAt, cloud.mdGeneratedAt);
    50	  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
    51	}
     1	import type { FieldState, HumanField, HumanSnapshot, VideoBaseline } from './types';
     2	
     3	export interface FieldMerge {
     4	  winner: 'local' | 'cloud' | 'equal';
     5	  value: string | number | undefined;
     6	  editedAt: string | undefined;
     7	  conflict: boolean;
     8	}
     9	
    10	type Baseline = { value?: string | number; editedAt?: string };
    11	
    12	/** Changed vs baseline is over the (value, editedAt) PAIR, not value alone (§5.4). */
    13	function changed(side: FieldState, base: Baseline): boolean {
    14	  return side.value !== base.value || side.editedAt !== base.editedAt;
    15	}
    16	
    17	function newer(a: string | undefined, b: string | undefined): boolean {
    18	  // returns true when a is strictly newer than b; undefined sorts oldest
    19	  return (a ?? '') > (b ?? '');
    20	}
    21	
    22	export function reconcileField(local: FieldState, cloud: FieldState, baseline: Baseline): FieldMerge {
    23	  // Equal VALUES never conflict (§5.4 row 1). But if their per-field timestamps differ, CONVERGE:
    24	  // return the newer-timestamp side as a NON-conflicting winner so the older side's editedAt is
    25	  // written forward and both replicas end identical — returning 'equal' here would skip the write
    26	  // and leave baseline/live timestamp drift (round-2 H1). Truly-equal pair → 'equal' (no write).
    27	  if (local.value === cloud.value) {
    28	    if (local.editedAt === cloud.editedAt) {
    29	      return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: false };
    30	    }
    31	    return newer(local.editedAt, cloud.editedAt)
    32	      ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false }
    33	      : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };
    34	  }
    35	  const lChanged = changed(local, baseline);
    36	  const cChanged = changed(cloud, baseline);
    37	
    38	  if (lChanged && !cChanged) return { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false };
    39	  if (cChanged && !lChanged) return { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };
    40	
    41	  // both changed (or neither vs an absent baseline but values differ) → newer per-field ts wins.
    42	  // A backfilled timestamp must never drive a destructive overwrite (§5.5) → conflict skip.
    43	  if (local.backfilled || cloud.backfilled) {
    44	    return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: true };
    45	  }
    46	  const localWins = newer(local.editedAt, cloud.editedAt);
    47	  return localWins
    48	    ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: true }
    49	    : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: true };
    50	}
    51	
    52	const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
    53	
    54	export function reconcileHuman(
    55	  local: HumanSnapshot,
    56	  cloud: HumanSnapshot,
    57	  baseline: VideoBaseline['classB'],
    58	): Record<HumanField, FieldMerge> {
    59	  const out = {} as Record<HumanField, FieldMerge>;
    60	  for (const f of FIELDS) out[f] = reconcileField(local[f], cloud[f], baseline[f] ?? {});
    61	  return out;
    62	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/manifest.ts | sed -n '1,240p' && nl -ba lib/cloud-sync/backfill.ts | sed -n '1,200p' && rg -n \"spend_ledger|reserve_serve_model|enqueue|producer|needsRegen|summaryHtml|digDeeper|artifacts\" lib/cloud-sync lib/storage lib/html-doc lib/dig tests/lib/cloud-sync tests/integration/cloud-sync -S" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// lib/cloud-sync/manifest.ts
     2	import { promises as fs } from 'fs';
     3	import path from 'path';
     4	import type { VideoBaseline } from './types';
     5	
     6	export interface Manifest { version: 1; videos: Record<string, VideoBaseline>; }
     7	
     8	export function manifestPath(dataRoot: string, playlistKey: string): string {
     9	  return path.join(dataRoot, playlistKey, '.cloud-sync-manifest.json');
    10	}
    11	function conflictPath(dataRoot: string, playlistKey: string): string {
    12	  return path.join(dataRoot, playlistKey, '.cloud-sync-conflicts.log');
    13	}
    14	
    15	export async function readManifest(dataRoot: string, playlistKey: string): Promise<Manifest> {
    16	  try {
    17	    const raw = await fs.readFile(manifestPath(dataRoot, playlistKey), 'utf8');
    18	    const parsed = JSON.parse(raw);
    19	    if (parsed && parsed.version === 1 && parsed.videos) return parsed as Manifest;
    20	  } catch {
    21	    // DELIBERATE, and spec-sanctioned — §8 specifies degrade-on-corrupt for the manifest.
    22	    // L-R5-3 (round 5, ACCEPTED not fixed): this catch also swallows an UNREADABLE manifest
    23	    // (EACCES/EIO) as an absent one, and with no baseline sync-run reads a one-sided video as a new
    24	    // additive create rather than a delete — so a video deleted on one replica can be copied back.
    25	    // That is the SAFE direction (resurrect, never delete) and the manifest is a derived cache that
    26	    // rebuilds itself on the next run; failing closed here would strand every video in the playlist.
    27	    // Reviewers: this is the same `catch → default` shape as B1/H1/H2, but unlike those it is the
    28	    // intended §8 behavior — please do not re-file it.
    29	  }
    30	  return { version: 1, videos: {} };
    31	}
    32	
    33	async function atomicWrite(file: string, data: string): Promise<void> {
    34	  await fs.mkdir(path.dirname(file), { recursive: true });
    35	  const tmp = `${file}.tmp-${process.pid}`;
    36	  await fs.writeFile(tmp, data, 'utf8');
    37	  await fs.rename(tmp, file);
    38	}
    39	
    40	export async function writeVideoBaseline(
    41	  dataRoot: string, playlistKey: string, videoId: string, baseline: VideoBaseline,
    42	): Promise<void> {
    43	  const m = await readManifest(dataRoot, playlistKey);
    44	  m.videos[videoId] = baseline;
    45	  await atomicWrite(manifestPath(dataRoot, playlistKey), JSON.stringify(m, null, 2));
    46	}
    47	
    48	const seenConflicts = new Set<string>();
    49	export interface ConflictEntry {
    50	  video_id: string; class: 'A' | 'B'; field?: string;
    51	  valueL?: unknown; valueR?: unknown; reason: string;
    52	}
    53	export async function appendConflict(dataRoot: string, playlistKey: string, e: ConflictEntry): Promise<void> {
    54	  // Include playlistKey so the same (video_id, class, field, valueL, valueR) in two playlists
    55	  // within one run is not collapsed to a single entry (L3).
    56	  const key = `${playlistKey}|${e.video_id}|${e.class}|${e.field ?? ''}|${JSON.stringify(e.valueL)}|${JSON.stringify(e.valueR)}`;
    57	  if (seenConflicts.has(key)) return;
    58	  seenConflicts.add(key);
    59	  const file = conflictPath(dataRoot, playlistKey);
    60	  await fs.mkdir(path.dirname(file), { recursive: true });
    61	  await fs.appendFile(file, `${JSON.stringify(e)}\n`, 'utf8');
    62	}
    63	/** Reset the per-run de-dup cache at the start of a sync run. */
    64	export function resetConflictDedup(): void { seenConflicts.clear(); }
     1	import type { Video } from '@/types';
     2	import type { ClassASignals, HumanSnapshot, HumanField, FieldState } from './types';
     3	import { mdHash } from './content-hash';
     4	
     5	// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
     6	// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
     7	export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
     8	  const hasReal = video.mdGeneratedAt != null;
     9	  return {
    10	    summaryMdKey: video.summaryMd ?? null,
    11	    mdHash: mdBody != null ? mdHash(mdBody) : null,
    12	    docVersionMajor: video.docVersion?.major ?? 1,
    13	    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
    14	    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
    15	    backfilled: !hasReal,
    16	  };
    17	}
    18	
    19	const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
    20	
    21	export function deriveHumanSnapshot(video: Video): HumanSnapshot {
    22	  const provisional = video.updatedAt ?? video.processedAt;
    23	  const out = {} as HumanSnapshot;
    24	  for (const f of FIELDS) {
    25	    const value = video[f] as string | number | undefined;
    26	    const real = video.annotationsEditedAt?.[f];
    27	    const state: FieldState<string | number> = value === undefined && real === undefined
    28	      ? { value: undefined, editedAt: undefined, backfilled: false }
    29	      : { value, editedAt: real ?? provisional, backfilled: real === undefined };
    30	    out[f] = state;
    31	  }
    32	  return out;
    33	}
lib/cloud-sync/companion.ts:34: *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
lib/dig/dig-section.ts:84:  const digDeeperFilename = `${summaryBasename}-dig-deeper.md`;
lib/dig/dig-section.ts:85:  const digDeeperPath = path.join(outputFolder, digDeeperFilename);
lib/dig/dig-section.ts:88:    digDeeperPath,
lib/dig/dig-section.ts:104:  // Step 11: Update index with digDeeperMd (HTML is rendered fresh by GET)
lib/dig/dig-section.ts:106:    digDeeperMd: digDeeperFilename,
tests/integration/cloud-sync/e2e.int.test.ts:10:// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
tests/integration/cloud-sync/e2e.int.test.ts:32:/** `artifacts` lives in the videos.data jsonb but is not on the Video Zod type — read it via a cast. */
tests/integration/cloud-sync/e2e.int.test.ts:33:const artifactsOf = (rec: { [k: string]: unknown } | null) =>
tests/integration/cloud-sync/e2e.int.test.ts:34:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
tests/integration/cloud-sync/e2e.int.test.ts:112:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:150:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:151:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:160:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:249:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:250:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:289:  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
tests/integration/cloud-sync/e2e.int.test.ts:290:  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:294:      summaryHtml: '<html>cached</html>',
tests/integration/cloud-sync/e2e.int.test.ts:295:      digDeeperHtml: '<html>dig</html>',
tests/integration/cloud-sync/e2e.int.test.ts:301:    expect(local?.summaryHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:302:    expect(local?.digDeeperHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:303:    expect(artifactsOf(local)?.summaryPdf).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:349:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:382:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:413:  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
tests/integration/cloud-sync/e2e.int.test.ts:432:    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:455:  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
tests/integration/cloud-sync/e2e.int.test.ts:466:    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
tests/integration/cloud-sync/e2e.int.test.ts:474:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:483:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:489:  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
tests/integration/cloud-sync/e2e.int.test.ts:490:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:496:      summaryHtml: '<html>STALE rendered from the old local body</html>',
tests/integration/cloud-sync/e2e.int.test.ts:506:    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
tests/integration/cloud-sync/e2e.int.test.ts:510:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
tests/integration/cloud-sync/e2e.int.test.ts:514:  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
tests/integration/cloud-sync/e2e.int.test.ts:515:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
tests/integration/cloud-sync/e2e.int.test.ts:516:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:523:      summaryHtml: '<html>STALE rendered from the old local body</html>',
tests/integration/cloud-sync/e2e.int.test.ts:524:      digDeeperHtml: '<html>STALE dig render</html>',
tests/integration/cloud-sync/e2e.int.test.ts:525:      raw: { digDeeperMd: digKey },
tests/integration/cloud-sync/e2e.int.test.ts:536:    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:537:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:538:    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
tests/integration/cloud-sync/e2e.int.test.ts:544:  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
tests/integration/cloud-sync/e2e.int.test.ts:563:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:570:    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:748:  //       exactly. Deleting it would burn reserve_serve_model → spend_ledger to rebuild.
tests/integration/cloud-sync/e2e.int.test.ts:814:    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:837:    // Cloud playlist row carries a title (as lib/job-queue/producer.ts sets it at enqueue) and holds
lib/html-doc/generate.ts:48:  // re-render is gated on summaryHtml (set only on full success), and a retry overwrites it atomically.
lib/html-doc/generate.ts:72:    await store.updateVideoFields(principal, videoId, { summaryHtml: htmlFilename });
lib/dig/generate.ts:125:   *  the local dig-section path, which never reserves/releases a spend_ledger entry. */
lib/html-doc/ensure.ts:16: * cheap re-render; no HTML yet → full build; already current → nothing. Leaves summaryHtml + docVersion
lib/html-doc/ensure.ts:54:  } else if (!video.summaryHtml) {
tests/lib/cloud-sync/reconcile-class-a.test.ts:13:      .toEqual({ action: 'skip', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:15:  it('mdHash equal but BOTH stale vs reconciled corrections → skip but needsRegen (round-v8 H-1)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:17:    expect(r).toEqual({ action: 'skip', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:21:    expect(r).toEqual({ action: 'copyToCloud', needsRegen: false }); // local current tuple → cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:25:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:31:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local (current) overwrites cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:37:      .toEqual({ action: 'copyToLocal', needsRegen: false }); // cloud (major 3) → local
tests/lib/cloud-sync/reconcile-class-a.test.ts:43:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local newer → cloud converges
tests/lib/cloud-sync/reconcile-class-a.test.ts:45:  it('neither current (both stale) → keep higher-major, flag needsRegen', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:49:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true }); // cloud higher major → local, but stale
tests/lib/cloud-sync/reconcile-class-a.test.ts:51:  it('present only one side (current) → copy, no needsRegen (hydrate/publish)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:53:      .toEqual({ action: 'copyToLocal', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:55:      .toEqual({ action: 'copyToCloud', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:57:  it('one-sided hydrate of a corrections-STALE MD flags needsRegen (L2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:59:      .toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:63:      .toEqual({ action: 'skip', needsRegen: false });
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:9://    cache (summaryHtml/dig/PDF) copied.
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:120: *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
lib/cloud-sync/sync-run.ts:121: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
lib/cloud-sync/sync-run.ts:125:  v.summaryHtml = null;
lib/cloud-sync/sync-run.ts:126:  v.digDeeperHtml = null;
lib/cloud-sync/sync-run.ts:127:  v.digDeeperMd = null;
lib/cloud-sync/sync-run.ts:128:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
lib/cloud-sync/sync-run.ts:129:  if (v.artifacts && typeof v.artifacts === 'object') {
lib/cloud-sync/sync-run.ts:130:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
lib/cloud-sync/sync-run.ts:179: *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
lib/cloud-sync/sync-run.ts:220:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
lib/cloud-sync/sync-run.ts:221:  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
lib/cloud-sync/sync-run.ts:225:    delete sanitized.artifacts.summaryMd;
lib/cloud-sync/sync-run.ts:238:  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
lib/cloud-sync/sync-run.ts:240:    const art = (rec as any).artifacts?.summaryMd;
lib/cloud-sync/sync-run.ts:352:    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
lib/cloud-sync/sync-run.ts:358:    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
lib/cloud-sync/sync-run.ts:359:    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
lib/cloud-sync/sync-run.ts:363:    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
lib/cloud-sync/sync-run.ts:367:    summaryHtml: null,
lib/cloud-sync/sync-run.ts:368:    digDeeperHtml: null,
lib/cloud-sync/sync-run.ts:371:    artifacts: { summaryMd: { key, status: 'promoted' } },
lib/cloud-sync/sync-run.ts:480:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:592:        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
lib/cloud-sync/sync-run.ts:595:          report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:603:        if (decision.needsRegen) report.needsRegen += 1;
tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
tests/integration/cloud-sync/stamping.int.test.ts:94:      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
lib/cloud-sync/reconcile-class-a.ts:5:  needsRegen: boolean;
lib/cloud-sync/reconcile-class-a.ts:20:  // Presence (§5.6 one-sided copy) — flag needsRegen when the SOLE MD is corrections-stale (R8, L2)
lib/cloud-sync/reconcile-class-a.ts:21:  if (!lHas && !cHas) return { action: 'skip', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:22:  if (!lHas) return { action: 'copyToLocal', needsRegen: !current(cloud, cur) };
lib/cloud-sync/reconcile-class-a.ts:23:  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };
lib/cloud-sync/reconcile-class-a.ts:33:    if (lCur && cCur) return { action: 'skip', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:34:    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
lib/cloud-sync/reconcile-class-a.ts:39:  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:40:  if (cCur && !lCur) return { action: 'copyToLocal', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:45:    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
lib/cloud-sync/reconcile-class-a.ts:50:  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
lib/storage/local/local-metadata-store.ts:38:  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
lib/dig/cloud/resolve-summary-key.ts:3:/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
lib/dig/cloud/resolve-summary-key.ts:7: *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
lib/dig/cloud/resolve-summary-key.ts:10: *  gate: it enqueues a dig job only when `loadSummaryForServe` reports the summary promoted, so by
lib/dig/cloud/resolve-summary-key.ts:13:  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
lib/dig/cloud/resolve-summary-key.ts:14:  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
lib/dig/cloud/enqueue-dig-core.ts:5:import type { Enqueuer } from '@/lib/job-queue/enqueuer';
lib/dig/cloud/enqueue-dig-core.ts:10:  enqueuer: Enqueuer;         // service-role — enqueue RPC only
lib/dig/cloud/enqueue-dig-core.ts:16:  enqueueIp: string | null;
lib/dig/cloud/enqueue-dig-core.ts:22: *  magazine model), validate the section, dedup on the current-version blob, preflight, enqueue.
lib/dig/cloud/enqueue-dig-core.ts:23: *  Charge happens once, inside enqueue_job, only on a fresh enqueue. */
lib/dig/cloud/enqueue-dig-core.ts:24:export async function enqueueDig(deps: EnqueueDigDeps): Promise<EnqueueDigResult> {
lib/dig/cloud/enqueue-dig-core.ts:37:  // Dedup authority = the current-version blob. Present → done, no enqueue, no charge.
lib/dig/cloud/enqueue-dig-core.ts:43:  const verdict = await deps.enqueuer.preflight(deps.enqueueIp, deps.userId);
lib/dig/cloud/enqueue-dig-core.ts:49:    const res = await deps.enqueuer.enqueue(
lib/dig/cloud/enqueue-dig-core.ts:50:      { ownerId: deps.userId, enqueueIp: deps.enqueueIp },
lib/dig/cloud/enqueue-dig-core.ts:63:    return { status: 202, body: { status: 'enqueued', jobId: res.jobId, sectionId: deps.sectionId } };
tests/lib/cloud-sync/regenerate-stamp.test.ts:5:// that persists refreshed tldr/takeaways/summaryHtml — also stamps mdGeneratedAt and
tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
lib/dig/cloud/dig-blob-key.ts:5: *  distinct jobs_idem_active slot (which includes job_version), permitting a legit re-enqueue. */
lib/storage/supabase/consistency.ts:34:    artifacts: { [opts.kind]: { key: opts.key, status: 'committed' } },
lib/storage/supabase/consistency.ts:40:    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
lib/dig/cloud/load-dig-for-serve.ts:18: * resolveMagazineModel / reserve_serve_model (spec §2 money invariant).
lib/html-doc/build-doc-html.ts:41:    const htmlFile = video.summaryHtml;
lib/html-doc/build-doc-html.ts:74:  let digDeeperPath: string | null = null;
lib/html-doc/build-doc-html.ts:75:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:77:      digDeeperPath = assertIndexRelPathWithin(outputFolder, video.digDeeperMd);
lib/html-doc/build-doc-html.ts:86:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:87:    const digRel = video.digDeeperMd;
lib/html-doc/build-doc-html.ts:127:  if (digDeeperPath !== null) {
lib/html-doc/build-doc-html.ts:129:      dug = parseDugSections(fs.readFileSync(digDeeperPath, 'utf8'));
lib/dig/companion-doc.ts:465: * Serializes writes per digDeeperPath so that concurrent digs of different
lib/dig/companion-doc.ts:477:  digDeeperPath: string;
lib/dig/companion-doc.ts:484:  const { digDeeperPath, videoTitle, videoId, language, sourceVideoUrl, section } = opts;
lib/dig/companion-doc.ts:486:  let doc = await readCompanionDoc(digDeeperPath);
lib/dig/companion-doc.ts:502:  await atomicWrite(digDeeperPath, content);
lib/dig/companion-doc.ts:506: * Upsert one dug section into the companion doc at `digDeeperPath`.
lib/dig/companion-doc.ts:516:  digDeeperPath: string;
lib/dig/companion-doc.ts:523:  const { digDeeperPath } = opts;
lib/dig/companion-doc.ts:524:  const prev = writeChains.get(digDeeperPath) ?? Promise.resolve();
lib/dig/companion-doc.ts:526:  writeChains.set(digDeeperPath, next.catch(() => {}));
lib/dig/companion-doc.ts:532: * of the companion doc at `digDeeperPath`.
lib/dig/companion-doc.ts:536:export async function readDugSectionIds(digDeeperPath: string): Promise<number[]> {
lib/dig/companion-doc.ts:537:  const doc = await readCompanionDoc(digDeeperPath);
lib/html-doc/serve-doc.ts:60:  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
lib/html-doc/serve-doc.ts:84:    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
lib/html-doc/serve-summary-core.ts:47:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
lib/html-doc/serve-summary-core.ts:48:    .artifacts?.summaryMd;
lib/html-doc/serve-summary-core.ts:53:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
lib/storage/supabase/supabase-metadata-store.ts:11:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
lib/storage/supabase/supabase-metadata-store.ts:14:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
lib/storage/supabase/supabase-metadata-store.ts:53:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
lib/storage/supabase/supabase-metadata-store.ts:54:            .artifacts?.summaryMd?.status === 'promoted',
lib/storage/supabase/supabase-metadata-store.ts:116:  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
lib/storage/supabase/supabase-metadata-store.ts:117:  // modify-write races; deep-merges the `artifacts` sub-object).
lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
lib/html-doc/nav.ts:30:function digDeeperHref(videoId: string, outputFolder: string, startSec: number): string {
lib/html-doc/nav.ts:53:  el.setAttribute('href', digDeeperHref(videoId, outputFolder, startSec));
lib/html-doc/nav.ts:531:  try { data = (await resp.json()) as { status?: string }; } catch { /* treat as enqueued */ }

codex
So far I do not see over-reporting from `noop + true` on ordinary no-op syncs: `companionTransfer` is only called after a Class-A copy, not after `skip`, and additive one-sided creates also do not call it. The counter is therefore tied to changed MD transfers whose receiver lacks a matching model, not every video without a model.
exec
/bin/bash -lc "nl -ba supabase/migrations/0021_sync_annotations_and_artifacts.sql | sed -n '1,260p' && nl -ba supabase/migrations/0009_storage_rls.sql | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'rg -n "copyToCloud|copyToLocal|shareNeedsOwnerServe|baseline|writeVideoBaseline|manifest|deleteReceiverModel|readModelSide|playlist title|title" tests/lib/cloud-sync tests/integration/cloud-sync -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
nl: supabase/migrations/0021_sync_annotations_and_artifacts.sql: No such file or directory
nl: supabase/migrations/0009_storage_rls.sql: No such file or directory

 succeeded in 0ms:
tests/integration/cloud-sync/sync-run.int.test.ts:58:  it('does not advance the manifest baseline when the cloud promote is not verified (crash safety)', async () => {
tests/integration/cloud-sync/sync-run.int.test.ts:67:    // Behavior #10/#11: a partial transfer NEVER advances the manifest baseline.
tests/integration/cloud-sync/e2e.int.test.ts:53:/** Read the cloud playlist row's title (admin client — assertion only, not a code path). */
tests/integration/cloud-sync/e2e.int.test.ts:56:    .from('playlists').select('playlist_title').eq('playlist_key', ctx.playlistKey).single();
tests/integration/cloud-sync/e2e.int.test.ts:58:  return (data as { playlist_title: string | null }).playlist_title;
tests/integration/cloud-sync/e2e.int.test.ts:61:/** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
tests/integration/cloud-sync/e2e.int.test.ts:62:function baseline(classB: VideoBaseline['classB']): VideoBaseline {
tests/integration/cloud-sync/e2e.int.test.ts:76:  //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
tests/integration/cloud-sync/e2e.int.test.ts:117:  //    Winner is the CLOUD side here → copyToLocal, exercising the local-overwrite transfer direction.
tests/integration/cloud-sync/e2e.int.test.ts:209:  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
tests/integration/cloud-sync/e2e.int.test.ts:210:  it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:222:    await seedManifestBaseline(ctx, baseline({
tests/integration/cloud-sync/e2e.int.test.ts:236:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:245:    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
tests/integration/cloud-sync/e2e.int.test.ts:246:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:261:  // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
tests/integration/cloud-sync/e2e.int.test.ts:262:  it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:264:    // Cloud still holds the video; local deleted it; a baseline records they once agreed.
tests/integration/cloud-sync/e2e.int.test.ts:266:    await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));
tests/integration/cloud-sync/e2e.int.test.ts:362:    expect(m1.videos[ctx.videoId]).toBeDefined();       // baseline written only after the row landed
tests/integration/cloud-sync/e2e.int.test.ts:365:    expect(r2.removed).toBe(0);                          // baseline present + BOTH sides present → not a delete
tests/integration/cloud-sync/e2e.int.test.ts:372:  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:412:  //    corrections-current, cloud stale → copyToCloud OVERWROTE cloud's (different-correction) MD body.
tests/integration/cloud-sync/e2e.int.test.ts:446:    // Second run — the baseline was NOT falsely advanced, so still no copy.
tests/integration/cloud-sync/e2e.int.test.ts:457:  //    promoted-but-blobless row + advanced the baseline. After the fix: per-video throw, no promoted
tests/integration/cloud-sync/e2e.int.test.ts:458:  //    receiver row, baseline NOT advanced (a re-run heals once the body is readable).
tests/integration/cloud-sync/e2e.int.test.ts:463:  //    below all passed while that bug was live; the run-2 baseline assertion is the real guard.
tests/integration/cloud-sync/e2e.int.test.ts:464:  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:475:    // Baseline not advanced — the throw aborted before writeVideoBaseline.
tests/integration/cloud-sync/e2e.int.test.ts:478:    // Run 2 — still one-sided, so it must report the SAME error and still write no baseline. With a
tests/integration/cloud-sync/e2e.int.test.ts:487:  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
tests/integration/cloud-sync/e2e.int.test.ts:490:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:516:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:581:  //    laundering the result into a full-agreement baseline. Both manifestations below must instead
tests/integration/cloud-sync/e2e.int.test.ts:582:  //    surface a per-video error, preserve every byte, and advance NO baseline (so the run heals once
tests/integration/cloud-sync/e2e.int.test.ts:585:  it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:593:    // the buggy path read as "cloud has no MD" ⇒ the corrections guard did not fire ⇒ copyToCloud.
tests/integration/cloud-sync/e2e.int.test.ts:613:      // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
tests/integration/cloud-sync/e2e.int.test.ts:619:  it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:622:    // No corrections anywhere — this manifestation is NOT conflict-gated: the !cHas early return in
tests/integration/cloud-sync/e2e.int.test.ts:624:    // major-1 body overwrite a major-9 one and recorded major 1 as the agreed baseline. Run 2 then saw
tests/integration/cloud-sync/e2e.int.test.ts:652:  //    the SENDER's model envelope and mapped null to deleteReceiverModel. On a copyToLocal transfer
tests/integration/cloud-sync/e2e.int.test.ts:657:  //    does not throw, so the baseline advanced, run 2 saw equal hashes and returned 'skip', and
tests/integration/cloud-sync/e2e.int.test.ts:677:    // Same section titles, different prose — the drift guard cannot see the difference.
tests/integration/cloud-sync/e2e.int.test.ts:697:    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
tests/integration/cloud-sync/e2e.int.test.ts:703:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:735:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
tests/integration/cloud-sync/e2e.int.test.ts:739:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:776:    expect(r1.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:780:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:790:  //    Before the guard this healed for free (!lHas → copyToLocal → the dangling pointer is
tests/integration/cloud-sync/e2e.int.test.ts:792:  //    baseline, with no exit but hand-editing playlist-index.json or paying to regenerate content
tests/integration/cloud-sync/e2e.int.test.ts:825:  // ── H3 (round 4) — a local-only video wiped the cloud playlist's title on every sync.
tests/integration/cloud-sync/e2e.int.test.ts:826:  //    playlistMetaFor checked the local registry FIRST and returned { playlistUrl } with no title
tests/integration/cloud-sync/e2e.int.test.ts:827:  //    (LocalPlaylist never carried one), the cloud-registry branch that does carry a title being
tests/integration/cloud-sync/e2e.int.test.ts:830:  //    `playlist_title: meta.playlistTitle ?? null` — an explicit NULL. Recurs on every sync that
tests/integration/cloud-sync/e2e.int.test.ts:831:  //    carries any local-only video (the ordinary case); recovery needs the backfill-titles route
tests/integration/cloud-sync/e2e.int.test.ts:833:  it('H3: an additive publish of a local-only video preserves the cloud playlist title (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:836:    const title = 'Deep Learning Lectures';
tests/integration/cloud-sync/e2e.int.test.ts:837:    // Cloud playlist row carries a title (as lib/job-queue/producer.ts sets it at enqueue) and holds
tests/integration/cloud-sync/e2e.int.test.ts:838:    // NO videos; the local replica has a title-less index with one video → additive publish to cloud.
tests/integration/cloud-sync/e2e.int.test.ts:843:      playlist_title: title,
tests/integration/cloud-sync/e2e.int.test.ts:848:    expect(await cloudPlaylistTitle(ctx)).toBe(title); // fixture precondition
tests/integration/cloud-sync/e2e.int.test.ts:854:    expect(await cloudPlaylistTitle(ctx)).toBe(title);   // title NOT cleared
tests/integration/cloud-sync/e2e.int.test.ts:858:    expect(await cloudPlaylistTitle(ctx)).toBe(title);
tests/integration/cloud-sync/e2e.int.test.ts:861:  // ── L-R5-2 (round 5) — H3 stopped a sync CLEARING the cloud title, but not OVERWRITING it.
tests/integration/cloud-sync/e2e.int.test.ts:862:  //    playlistMetaFor preferred `lp?.playlistTitle`, so a local playlist-index.json title — whatever
tests/integration/cloud-sync/e2e.int.test.ts:865:  //    row wins, because it is the one the ingest and backfill-titles paths keep current from the
tests/integration/cloud-sync/e2e.int.test.ts:866:  //    live YouTube API. Recurs on every sync and recovery needs backfill-titles + an API key.
tests/integration/cloud-sync/e2e.int.test.ts:867:  it('L-R5-2: a stale local playlist title does NOT overwrite a fresher cloud title (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:876:      playlist_title: cloudTitle,
tests/integration/cloud-sync/e2e.int.test.ts:881:    // The local index carries an OLD title for the same playlist (renamed on YouTube since).
tests/integration/cloud-sync/e2e.int.test.ts:890:    expect(await cloudPlaylistTitle(ctx)).toBe(cloudTitle);    // cloud title NOT overwritten
tests/integration/cloud-sync/e2e.int.test.ts:895:  // The other half of the precedence: with no cloud title, the local one still FILLS it, so
tests/integration/cloud-sync/e2e.int.test.ts:896:  // preferring the cloud never costs a playlist its only title.
tests/integration/cloud-sync/e2e.int.test.ts:897:  it('L-R5-2: a local title still fills a cloud playlist that has none', async () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:21:    expect(r).toEqual({ action: 'copyToCloud', needsRegen: false }); // local current tuple → cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:25:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:31:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local (current) overwrites cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:37:      .toEqual({ action: 'copyToLocal', needsRegen: false }); // cloud (major 3) → local
tests/lib/cloud-sync/reconcile-class-a.test.ts:43:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local newer → cloud converges
tests/lib/cloud-sync/reconcile-class-a.test.ts:49:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true }); // cloud higher major → local, but stale
tests/lib/cloud-sync/reconcile-class-a.test.ts:53:      .toEqual({ action: 'copyToLocal', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:55:      .toEqual({ action: 'copyToCloud', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:59:      .toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/companion.test.ts:13:const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
tests/lib/cloud-sync/companion.test.ts:15:const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
tests/lib/cloud-sync/companion.test.ts:68:    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
tests/lib/cloud-sync/companion.test.ts:79:      const deleted = decideCompanion({ winnerMdHash: 'h1', senderModel: s, receiverModel: r }).kind === 'deleteReceiverModel';
tests/lib/cloud-sync/regenerate-stamp.test.ts:56:  title: 'Test Video',
tests/lib/cloud-sync/model-writer-hash.test.ts:53:    id: VIDEO_ID, title: 'A Title', youtubeUrl: 'https://youtu.be/x', language: 'en',
tests/lib/cloud-sync/model-writer-hash.test.ts:56:    overallScore: 4, summaryMd: 'a-title.md',
tests/lib/cloud-sync/model-writer-hash.test.ts:65:  fs.writeFileSync(path.join(dir, 'a-title.md'), BODY);
tests/lib/cloud-sync/model-writer-hash.test.ts:79:  const env = await readModelEnvelope(principal, 'a-title');
tests/lib/cloud-sync/schema.test.ts:5:  id: 'v1', title: 'T', youtubeUrl: 'https://youtu.be/v1', language: 'en',
tests/lib/cloud-sync/reconcile-class-b.test.ts:17:  it('only local changed vs baseline → take local', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:20:  it('only cloud changed vs baseline → take cloud', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:23:  it('a clear on one side (present→absent vs baseline) propagates', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:31:    // baseline present "x"@t1; local cleared@t2; cloud re-added same "x"@t3.
tests/lib/cloud-sync/reconcile-class-b.test.ts:32:    // cloud's (value,editedAt) differs from baseline (ts advanced) → cloud changed;
tests/lib/cloud-sync/reconcile-class-b.test.ts:36:  it('no baseline + differ → newer per-field editedAt wins', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:39:  it('present one side, absent other, no baseline → copy (additive)', () => {
tests/lib/cloud-sync/registry.test.ts:21://    playlist present in BOTH replicas always resolved to a title-less meta — which the cloud
tests/lib/cloud-sync/registry.test.ts:22://    setPlaylistMeta upsert writes as an explicit NULL, wiping the cloud row's title.
tests/lib/cloud-sync/registry.test.ts:37:      playlistUrl: 'https://www.youtube.com/playlist?list=PLtitled',
tests/lib/cloud-sync/registry.test.ts:46:    expect(found[0].playlistKey).toBe('PLtitled');
tests/lib/cloud-sync/registry.test.ts:52:      playlistUrl: 'https://www.youtube.com/playlist?list=PLuntitled',
tests/lib/cloud-sync/local-stamping.test.ts:21:  id, title: 'T', youtubeUrl: `https://youtu.be/${id}`, language: 'en', durationSeconds: 1,
tests/lib/cloud-sync/manifest.test.ts:1:// tests/lib/cloud-sync/manifest.test.ts
tests/lib/cloud-sync/manifest.test.ts:5:import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';
tests/lib/cloud-sync/manifest.test.ts:9:it('returns an empty manifest when the file is missing', async () => {
tests/lib/cloud-sync/manifest.test.ts:14:it('returns an empty manifest (no throw) on a corrupt file', async () => {
tests/lib/cloud-sync/manifest.test.ts:16:  await fs.mkdir(path.dirname(manifestPath(r, 'PL1')), { recursive: true });
tests/lib/cloud-sync/manifest.test.ts:17:  await fs.writeFile(manifestPath(r, 'PL1'), '{not json', 'utf8');
tests/lib/cloud-sync/manifest.test.ts:21:it('round-trips a written baseline', async () => {
tests/lib/cloud-sync/manifest.test.ts:25:  await writeVideoBaseline(r, 'PL1', 'v1', base as any);
tests/lib/cloud-sync/backfill.test.ts:6:  id: 'a', title: 'T', youtubeUrl: 'https://youtu.be/a', language: 'en', durationSeconds: 1,
tests/lib/cloud-sync/backfill.test.ts:8:  overallScore: 3, summaryMd: '001_title.md', processedAt: '2026-01-01T00:00:00.000Z', // KEY, not body
tests/lib/cloud-sync/backfill.test.ts:17:  expect(s.mdHash).not.toBe(mdHash('001_title.md')); // must NOT hash the filename
tests/lib/cloud-sync/backfill.test.ts:18:  expect(s.summaryMdKey).toBe('001_title.md');

exec
/bin/bash -lc 'git show --name-only --format= 12c850d' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
docs/reviews/whole-branch-cloud-sync-v5-rereview-claude.md
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md
lib/cloud-sync/companion.ts
lib/cloud-sync/manifest.ts
lib/cloud-sync/sync-run.ts
tests/integration/cloud-sync/e2e.int.test.ts
tests/integration/helpers/cloud.ts
tests/lib/cloud-sync/companion.test.ts

codex
One migration path read used stale filenames; I’ll correct that by listing the migrations and then inspect the actual `0009` and `0021` files for storage RLS and JSON merge semantics.
exec
/bin/bash -lc "rg --files supabase/migrations | sort | rg '0009|0021'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql
supabase/migrations/0021_cloud_sync_signals.sql

exec
/bin/bash -lc 'rg -n "create or replace function (merge_video_data|merge_video_data_bulk|update_video_annotations|claim_video_slot|reserve_serve_model)|policy|storage.objects|spend_ledger|service_role" supabase/migrations -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
supabase/migrations/0010_cancel_job_rowcount.sql:22:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
supabase/migrations/0019_share_tokens_cascade.sql:28:-- policy — the same mechanism already relied on for videos/jobs.
supabase/migrations/0019_share_tokens_cascade.sql:42:-- the path. The `service_role` grant below is inert on its own: auth.uid() is null with no
supabase/migrations/0019_share_tokens_cascade.sql:43:-- end-user JWT, so a bare service_role caller cancels 0 rows (owner_id = auth.uid() never
supabase/migrations/0019_share_tokens_cascade.sql:60:grant execute on function request_cancel_playlist_jobs(uuid) to authenticated, service_role;
supabase/migrations/0016_update_video_annotations.sql:8:--     parameter and no service_role bypass. SECURITY INVOKER + RLS both apply; this
supabase/migrations/0011_cost_guardrails.sql:8:create policy usage_counters_owner_read on usage_counters for select using (owner_id = auth.uid());
supabase/migrations/0011_cost_guardrails.sql:10:grant select, insert, update, delete on usage_counters to service_role;
supabase/migrations/0011_cost_guardrails.sql:12:create table spend_ledger (                                          -- global, one row per UTC day
supabase/migrations/0011_cost_guardrails.sql:17:alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
supabase/migrations/0011_cost_guardrails.sql:18:grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)
supabase/migrations/0011_cost_guardrails.sql:24:create policy quota_allowance_read on quota_allowance for select using (true);   -- allowances are not secret → UI shows "X of N" (Claude-L3)
supabase/migrations/0011_cost_guardrails.sql:25:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
supabase/migrations/0011_cost_guardrails.sql:38:grant select, insert, update, delete on guardrail_config to service_role;   -- no client access
supabase/migrations/0011_cost_guardrails.sql:48:-- and replaces it with an 8-arg service_role-only RPC that adds trusted p_owner_id
supabase/migrations/0011_cost_guardrails.sql:50:-- backstop. Every `auth.uid()` becomes `p_owner_id` (under service_role auth.uid()
supabase/migrations/0011_cost_guardrails.sql:68:  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
supabase/migrations/0011_cost_guardrails.sql:69:  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
supabase/migrations/0011_cost_guardrails.sql:112:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0011_cost_guardrails.sql:113:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0011_cost_guardrails.sql:138:grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;
supabase/migrations/0011_cost_guardrails.sql:141:-- enqueue_preflight — ADVISORY, service_role-only gate (spec §5). Four
supabase/migrations/0011_cost_guardrails.sql:156:  if auth.role() <> 'service_role' then raise exception 'enqueue_preflight: server only'; end if;
supabase/migrations/0011_cost_guardrails.sql:188:    from spend_ledger where day = v_day;
supabase/migrations/0011_cost_guardrails.sql:196:grant execute on function enqueue_preflight(inet,uuid) to service_role;
supabase/migrations/0002_rls_policies.sql:2:create policy profiles_self  on profiles  for all
supabase/migrations/0002_rls_policies.sql:4:create policy playlists_owner on playlists for all
supabase/migrations/0002_rls_policies.sql:6:create policy videos_owner    on videos    for all
supabase/migrations/0012_serve_model_charge.sql:5:-- 1. Lease/charge marker. force-RLS + service_role-only grants (mirrors spend_ledger, 0011):
supabase/migrations/0012_serve_model_charge.sql:17:grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
supabase/migrations/0012_serve_model_charge.sql:25:--    service_role-only tables while being callable by a session client. auth.uid() is derived
supabase/migrations/0012_serve_model_charge.sql:85:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0012_serve_model_charge.sql:86:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:53:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:60:grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:67:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:83:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:102:grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:108:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:158:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
supabase/migrations/0018_enqueue_dig.sql:17:  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
supabase/migrations/0018_enqueue_dig.sql:18:  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
supabase/migrations/0018_enqueue_dig.sql:61:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0018_enqueue_dig.sql:62:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0018_enqueue_dig.sql:87:grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;
supabase/migrations/0004_test_exec_sql.sql:2:-- Read-only catalog inspection for the integration suite. Granted to service_role ONLY.
supabase/migrations/0004_test_exec_sql.sql:11:grant execute on function exec_sql(text) to service_role;
supabase/migrations/0013_share_tokens.sql:2:-- Stage 1F-b share tokens (spec §4.1/§4.2). force-RLS + service_role-only grants (mirrors
supabase/migrations/0013_share_tokens.sql:18:grant select, insert, update, delete on share_tokens to service_role;  -- no anon/authenticated policy
supabase/migrations/0021_cloud_sync_signals.sql:19:create or replace function update_video_annotations(
supabase/migrations/0021_cloud_sync_signals.sql:62:create or replace function merge_video_data(
supabase/migrations/0021_cloud_sync_signals.sql:72:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0021_cloud_sync_signals.sql:93:grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;
supabase/migrations/0021_cloud_sync_signals.sql:103:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0021_cloud_sync_signals.sql:155:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:7:-- storage.objects RLS: first path segment must equal auth.uid(); service_role full access.
supabase/migrations/0007_storage_and_rpcs.sql:12:create policy "artifacts_owner_rw" on storage.objects
supabase/migrations/0007_storage_and_rpcs.sql:16:create policy "artifacts_service_all" on storage.objects
supabase/migrations/0007_storage_and_rpcs.sql:17:  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');
supabase/migrations/0007_storage_and_rpcs.sql:26:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
supabase/migrations/0007_storage_and_rpcs.sql:44:grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:56:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0007_storage_and_rpcs.sql:74:grant execute on function reconcile_membership(uuid, text[]) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:85:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0007_storage_and_rpcs.sql:98:grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:107:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0007_storage_and_rpcs.sql:122:grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;
supabase/migrations/0008_jobs_queue.sql:35:create policy jobs_owner on jobs for all
supabase/migrations/0008_jobs_queue.sql:40:grant select, insert, update, delete on public.jobs to service_role;
supabase/migrations/0008_jobs_queue.sql:78:grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
supabase/migrations/0008_jobs_queue.sql:92:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
supabase/migrations/0008_jobs_queue.sql:94:-- worker RPCs (service_role only): lease fencing on locked_by + lease_token + status='active'
supabase/migrations/0008_jobs_queue.sql:100:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0008_jobs_queue.sql:113:grant execute on function claim_next_job(text,int,text) to service_role;
supabase/migrations/0008_jobs_queue.sql:119:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0008_jobs_queue.sql:126:grant execute on function heartbeat_job(uuid,text,uuid,int) to service_role;
supabase/migrations/0008_jobs_queue.sql:132:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0008_jobs_queue.sql:141:grant execute on function complete_job(uuid,text,uuid,jsonb) to service_role;
supabase/migrations/0008_jobs_queue.sql:147:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0008_jobs_queue.sql:165:grant execute on function fail_job(uuid,text,uuid,text,boolean) to service_role;
supabase/migrations/0008_jobs_queue.sql:171:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0008_jobs_queue.sql:188:grant execute on function sweep_expired_leases() to service_role;
supabase/migrations/0006_grants.sql:3:-- the Data API roles (anon, authenticated, service_role) on new public tables. RLS only
supabase/migrations/0006_grants.sql:9:-- service_role: has BYPASSRLS (the trusted worker path, spec §5.4 — writes with owner_id
supabase/migrations/0006_grants.sql:16:grant select, insert, update, delete on public.profiles  to anon, authenticated, service_role;
supabase/migrations/0006_grants.sql:17:grant select, insert, update, delete on public.playlists to anon, authenticated, service_role;
supabase/migrations/0006_grants.sql:18:grant select, insert, update, delete on public.videos    to anon, authenticated, service_role;
supabase/migrations/0005_reorder_helper.sql:13:       and (owner_id = auth.uid() or auth.role() = 'service_role')
supabase/migrations/0005_reorder_helper.sql:24:-- Codex H7: not callable by anon/PUBLIC by default; only authenticated + service_role.
supabase/migrations/0005_reorder_helper.sql:26:grant execute on function reorder_videos(uuid, jsonb) to authenticated, service_role;
supabase/migrations/0014_serve_owner_budget.sql:5:-- 1. Per-owner counter (analog of spend_ledger). force-RLS + service_role-only (no client policy).
supabase/migrations/0014_serve_owner_budget.sql:13:grant select, insert, update, delete on serve_owner_budget to service_role;
supabase/migrations/0014_serve_owner_budget.sql:22:create or replace function reserve_serve_model(p_playlist_id uuid, p_video_id text)
supabase/migrations/0014_serve_owner_budget.sql:73:      --     Over-budget owners fail here without ever locking the global spend_ledger money row.
supabase/migrations/0014_serve_owner_budget.sql:81:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0014_serve_owner_budget.sql:82:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0014_serve_owner_budget.sql:110:grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
supabase/migrations/0020_reservation_release.sql:2:-- Reserve→release lifecycle for spend_ledger. Money path — see
supabase/migrations/0020_reservation_release.sql:9:-- Locked down exactly like spend_ledger (0011:17-18): force RLS + NO policy blocks
supabase/migrations/0020_reservation_release.sql:10:-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
supabase/migrations/0020_reservation_release.sql:22:grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger
supabase/migrations/0020_reservation_release.sql:49:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0020_reservation_release.sql:80:    update spend_ledger
supabase/migrations/0020_reservation_release.sql:94:grant execute on function fail_job(uuid,text,uuid,text,boolean,boolean,boolean) to service_role;
supabase/migrations/0020_reservation_release.sql:121:    update spend_ledger set reserved_cents = reserved_cents - v_old_amt, updated_at = now()
supabase/migrations/0020_reservation_release.sql:164:    update spend_ledger sl
supabase/migrations/0020_reservation_release.sql:243:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0020_reservation_release.sql:244:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0020_reservation_release.sql:267:-- released=true also guarded-decrement serve_owner_budget + spend_ledger by magazine_est_cents.
supabase/migrations/0020_reservation_release.sql:290:    update spend_ledger set reserved_cents = reserved_cents - v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0020_reservation_release.sql:295:                'settle_serve_model spend_ledger '||p_token::text, now());

codex
The actual storage RLS is in `0007`, not `0009`; `0009` is older job persistence. I’ll still include `0009` in scope, but the owner-path sync storage policy to verify is `0007_storage_and_rpcs.sql`.
exec
/bin/bash -lc "nl -ba supabase/migrations/0007_storage_and_rpcs.sql | sed -n '1,150p' && nl -ba supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql | sed -n '1,180p' && nl -ba supabase/migrations/0021_cloud_sync_signals.sql | sed -n '1,190p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- supabase/migrations/0007_storage_and_rpcs.sql
     2	
     3	-- Private bucket for all artifacts.
     4	insert into storage.buckets (id, name, public) values ('artifacts', 'artifacts', false)
     5	  on conflict (id) do nothing;
     6	
     7	-- storage.objects RLS: first path segment must equal auth.uid(); service_role full access.
     8	-- name is like '<owner_id>/<playlist_key>/<key>'. split_part(name,'/',1) = owner segment.
     9	-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
    10	-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
    11	-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
    12	create policy "artifacts_owner_rw" on storage.objects
    13	  for all to authenticated, anon
    14	  using (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text)
    15	  with check (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text);
    16	create policy "artifacts_service_all" on storage.objects
    17	  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');
    18	
    19	-- claim_video_slot: append a reservation row under a playlist row-lock; returns position + serial.
    20	create function claim_video_slot(p_playlist_id uuid, p_video_id text)
    21	  returns table("position" int, serial_number int)
    22	  language plpgsql security invoker set search_path = public as $$
    23	declare v_pos int; v_serial int;
    24	begin
    25	  perform 1 from playlists
    26	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
    27	    for update;
    28	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
    29	
    30	  select coalesce(max(v.position) + 1, 0),
    31	         coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    32	    into v_pos, v_serial
    33	    from videos v where v.playlist_id = p_playlist_id;
    34	
    35	  insert into videos (playlist_id, owner_id, video_id, position, data)
    36	    select p_playlist_id, pl.owner_id, p_video_id, v_pos,
    37	           jsonb_build_object('id', p_video_id, 'serialNumber', v_serial)
    38	      from playlists pl where pl.id = p_playlist_id
    39	    on conflict (playlist_id, video_id) do nothing;   -- idempotent claim
    40	
    41	  return query select v_pos, v_serial;
    42	end $$;
    43	revoke all on function claim_video_slot(uuid, text) from public;
    44	grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;
    45	
    46	-- reconcile_membership: single-transaction archive/restore by playlist membership.
    47	-- Sticky three-way logic mirrors local reconcilePlaylistMembership:
    48	--   absent + not-yet-removed  → set archived=true, removedFromPlaylist=true
    49	--   present + was-removed     → set archived=false, removedFromPlaylist=false
    50	--   otherwise                 → leave untouched (preserves manual archive state)
    51	-- coalesce(..., false) treats a missing removedFromPlaylist key the same as false.
    52	create function reconcile_membership(p_playlist_id uuid, p_present text[])
    53	  returns void language plpgsql security invoker set search_path = public as $$
    54	begin
    55	  perform 1 from playlists
    56	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
    57	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
    58	
    59	  -- archive newly-absent videos that weren't already marked removed
    60	  update videos
    61	    set data = data || '{"archived":true,"removedFromPlaylist":true}'::jsonb, updated_at = now()
    62	    where playlist_id = p_playlist_id
    63	      and not (video_id = any(p_present))
    64	      and coalesce((data->>'removedFromPlaylist')::boolean, false) = false;
    65	
    66	  -- restore videos that have returned to the playlist
    67	  update videos
    68	    set data = data || '{"archived":false,"removedFromPlaylist":false}'::jsonb, updated_at = now()
    69	    where playlist_id = p_playlist_id
    70	      and (video_id = any(p_present))
    71	      and coalesce((data->>'removedFromPlaylist')::boolean, false) = true;
    72	end $$;
    73	revoke all on function reconcile_membership(uuid, text[]) from public;
    74	grant execute on function reconcile_membership(uuid, text[]) to authenticated, service_role;
    75	
    76	-- merge_video_data: owner-guarded jsonb field merge. ARTIFACTS-AWARE (F6): the top-level
    77	-- `artifacts` object is deep-merged one level (so writing one artifact kind never clobbers
    78	-- sibling kinds); every other key is a plain shallow merge. Write-once fields (videoPublishedAt/
    79	-- addedToPlaylistAt) are preserved by the caller passing the already-`??`-guarded value (F2b);
    80	-- the accompanying integration test (Task 11) proves re-sync does not overwrite them.
    81	create function merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)
    82	  returns void language plpgsql security invoker set search_path = public as $$
    83	begin
    84	  perform 1 from playlists
    85	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
    86	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
    87	
    88	  update videos set
    89	    data = (data || (p_fields - 'artifacts'))
    90	      || case when p_fields ? 'artifacts'
    91	           then jsonb_build_object('artifacts',
    92	                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
    93	           else '{}'::jsonb end,
    94	    updated_at = now()
    95	   where playlist_id = p_playlist_id and video_id = p_video_id;
    96	end $$;
    97	revoke all on function merge_video_data(uuid, text, jsonb) from public;
    98	grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;
    99	
   100	-- merge_video_data_bulk: apply merge_video_data semantics to many videos in ONE transaction.
   101	-- p_patches = jsonb array of { "video_id": text, "fields": jsonb }.
   102	create function merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)
   103	  returns void language plpgsql security invoker set search_path = public as $$
   104	declare it jsonb;
   105	begin
   106	  perform 1 from playlists
   107	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
   108	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
   109	
   110	  for it in select * from jsonb_array_elements(p_patches) loop
   111	    update videos set
   112	      data = (data || ((it->'fields') - 'artifacts'))
   113	        || case when (it->'fields') ? 'artifacts'
   114	             then jsonb_build_object('artifacts',
   115	                    coalesce(data->'artifacts', '{}'::jsonb) || ((it->'fields')->'artifacts'))
   116	             else '{}'::jsonb end,
   117	      updated_at = now()
   118	     where playlist_id = p_playlist_id and video_id = it->>'video_id';
   119	  end loop;
   120	end $$;
   121	revoke all on function merge_video_data_bulk(uuid, jsonb) from public;
   122	grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;
     1	-- 0009: 1E-b — job-identity playlist coordinate + worker columns/RPCs.
     2	-- jobs is created fresh by 0008 on every `db reset` (empty at this point) → safe re-key.
     3	
     4	alter table jobs add column playlist_id uuid not null;
     5	alter table jobs add constraint jobs_playlist_owner_fk
     6	  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;
     7	alter table jobs add column progress_phase text
     8	  check (progress_phase in ('transcribing','summarizing','writing'));
     9	
    10	drop index jobs_idem_active;
    11	create unique index jobs_idem_active
    12	  on jobs (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
    13	  where status in ('queued','active','completed');
    14	
    15	drop function enqueue_job(text,int,text,text,jsonb);
    16	create function enqueue_job(
    17	  p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
    18	) returns table(job_id uuid, status text, joined boolean)
    19	  language plpgsql security invoker set search_path = public as $$
    20	declare v_id uuid; v_status text; v_payload jsonb; v_tries int := 0;
    21	begin
    22	  if auth.uid() is null then raise exception 'not authenticated'; end if;
    23	  loop
    24	    v_tries := v_tries + 1;
    25	    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    26	    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload)
    27	    values (auth.uid(), p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    28	    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
    29	      where j.status in ('queued','active','completed')
    30	      do nothing
    31	    returning id into v_id;
    32	    if v_id is not null then return query select v_id, 'queued'::text, false; return; end if;
    33	    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
    34	      where j.owner_id = auth.uid() and j.playlist_id = p_playlist_id and j.video_id = p_video_id
    35	        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
    36	        and j.status in ('queued','active','completed')
    37	      limit 1;
    38	    if v_id is not null then
    39	      if v_payload is distinct from p_payload then
    40	        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
    41	      return query select v_id, v_status, true; return;
    42	    end if;
    43	  end loop;
    44	end $$;
    45	revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
    46	grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
    47	
    48	-- set_progress_phase: lease-fenced advisory phase write (keeps lifecycle writes RPC-only).
    49	create function set_progress_phase(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_phase text)
    50	  returns boolean language plpgsql security invoker set search_path = public as $$
    51	declare v_ok boolean;
    52	begin
    53	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
    54	  update jobs set progress_phase = p_phase, updated_at = now()
    55	    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
    56	  get diagnostics v_ok = row_count;
    57	  return v_ok > 0;
    58	end $$;
    59	revoke all on function set_progress_phase(uuid,text,uuid,text) from public;
    60	grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;
    61	
    62	-- crash-reclaim now backs off (resolves 1E-a deferred Minor #2), mirroring fail_job.
    63	create or replace function sweep_expired_leases() returns int
    64	  language plpgsql security invoker set search_path = public as $$
    65	declare v_count int;
    66	begin
    67	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
    68	  with expired as (select id from jobs where status = 'active' and lease_expires_at < now() for update skip locked)
    69	  update jobs j set
    70	    status = case when j.cancel_requested then 'cancelled'
    71	                  when j.attempts >= j.max_attempts then 'dead_letter' else 'queued' end,
    72	    run_after = case when j.cancel_requested or j.attempts >= j.max_attempts then j.run_after
    73	                     else now() + make_interval(secs => (10 * power(4, least(greatest(j.attempts - 1, 0), 15)))::bigint) end,
    74	    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
    75	  from expired e where j.id = e.id;
    76	  get diagnostics v_count = row_count; return v_count;
    77	end $$;
    78	
    79	create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
    80	  returns int language plpgsql security invoker set search_path = public as $$
    81	declare v_serial int; v_pos int;
    82	begin
    83	  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
    84	  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id for update;
    85	  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
    86	  select (v.data->>'serialNumber')::int into v_serial
    87	    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
    88	  if v_serial is not null then return v_serial; end if;
    89	  if exists (select 1 from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id) then
    90	    raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', p_playlist_id, p_video_id;
    91	  end if;
    92	  select coalesce(max(v.position) + 1, 0), coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    93	    into v_pos, v_serial from videos v where v.playlist_id = p_playlist_id;
    94	  insert into videos (playlist_id, owner_id, video_id, position, data)
    95	    values (p_playlist_id, p_owner_id, p_video_id, v_pos, jsonb_build_object('id', p_video_id, 'serialNumber', v_serial))
    96	    on conflict (playlist_id, video_id) do nothing;
    97	  select (v.data->>'serialNumber')::int into v_serial
    98	    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
    99	  return v_serial;
   100	end $$;
   101	revoke all on function reserve_video_slot(uuid,uuid,text) from public;
   102	grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;
   103	
   104	create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
   105	  returns void language plpgsql security invoker set search_path = public as $$
   106	declare v_count int;
   107	begin
   108	  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
   109	  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
   110	  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
   111	  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
   112	  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
   113	  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
   114	  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
   115	  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
   116	  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
   117	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
   118	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
   119	  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
   120	  update videos v set
   121	    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
   122	      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
   123	                                                              --     state AND never drop existing summary fields on a
   124	                                                              --     status-only persist (p_video omits them)
   125	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
   126	           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
   127	           'ratings', p_video->'ratings',
   128	           'overallScore', p_video->'overallScore',
   129	           'processedAt', p_video->'processedAt',
   130	           'videoType', p_video->'videoType',
   131	           'audience', p_video->'audience',
   132	           'tags', p_video->'tags',
   133	           'tldr', p_video->'tldr',
   134	           'takeaways', p_video->'takeaways',
   135	           'docVersion', p_video->'docVersion'))
   136	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
   137	      || jsonb_build_object('artifacts',
   138	           coalesce(v.data->'artifacts', '{}'::jsonb)
   139	           || jsonb_build_object('summaryMd', jsonb_build_object(
   140	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
   141	                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
   142	                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
   143	                -- that IS in committed state, so it must be allowed through (else the row would claim a
   144	                -- promoted artifact for a blob that has not been promoted yet).
   145	                'status', case
   146	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
   147	                                 and p_artifact_status = 'committed'
   148	                                 and v.data->'artifacts'->'summaryMd'->>'key'
   149	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
   150	                              then 'promoted'
   151	                            else p_artifact_status end))),
   152	    updated_at = now()
   153	   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
   154	  get diagnostics v_count = row_count;
   155	  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
   156	end $$;
   157	revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
   158	grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
     1	-- supabase/migrations/0021_cloud_sync_signals.sql
     2	-- Stage 3 Cloud Sync (§5.7): per-field annotationsEditedAt stamping, corrections
     3	-- allowlisting, conditional merge restamp, and mdGeneratedAt/mdCorrectionsHash on persist.
     4	
     5	-- (0) DROP the old signatures FIRST. Adding a defaulted `p_edited_at` parameter to
     6	--     update_video_annotations / merge_video_data with `create or replace` would create a
     7	--     NEW overload and LEAVE the old 4-arg / 3-arg functions in place. A caller that omits
     8	--     p_edited_at (e.g. SupabaseMetadataStore.updateVideoAnnotations' 4-key rpc call) would
     9	--     then match BOTH overloads → PostgREST error PGRST203 "could not choose the best
    10	--     candidate function" → the live Archive button + annotation/field writes break. Dropping
    11	--     the old signatures makes the 3/4-key call resolve unambiguously to the single surviving
    12	--     defaulted function. (persist_summary keeps its 5-arg signature unchanged → no drop needed.)
    13	drop function if exists update_video_annotations(uuid, text, jsonb, text[]);
    14	drop function if exists merge_video_data(uuid, text, jsonb);
    15	
    16	-- (1) update_video_annotations: add corrections to the allowlist; stamp per-field
    17	--     annotationsEditedAt for each Class-B field set OR cleared; accept an explicit
    18	--     sync-path timestamp (defaults to now() for the user-edit path).
    19	create or replace function update_video_annotations(
    20	  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[],
    21	  p_edited_at timestamptz default now()
    22	) returns integer language plpgsql security invoker set search_path = public as $$
    23	declare
    24	  allow text[] := array['personalScore','personalNote','corrections','archived'];
    25	  classb text[] := array['personalScore','personalNote','corrections'];
    26	  v_set jsonb := '{}'::jsonb;
    27	  v_stamp jsonb := '{}'::jsonb;
    28	  v_clear text[] := '{}';
    29	  k text; n integer;
    30	  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
    31	begin
    32	  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    33	    if k = any(allow) then
    34	      v_set := v_set || jsonb_build_object(k, p_set->k);
    35	      if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    36	    end if;
    37	  end loop;
    38	  -- clears: only allowlisted; each Class-B clear stamps its timestamp
    39	  select coalesce(array_agg(c),'{}') into v_clear
    40	    from unnest(coalesce(p_clear,'{}')) c where c = any(allow);
    41	  foreach k in array v_clear loop
    42	    if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    43	  end loop;
    44	
    45	  -- Only touch annotationsEditedAt when there IS a Class-B stamp; an archived-only
    46	  -- (or empty) write must not create an empty annotationsEditedAt:{} (§4.1 "archived-only
    47	  -- write restamps nothing").
    48	  update videos
    49	     set data = case when v_stamp <> '{}'::jsonb
    50	                  then jsonb_set((data || v_set) - v_clear, '{annotationsEditedAt}',
    51	                         coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp, true)
    52	                  else (data || v_set) - v_clear end
    53	   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
    54	  get diagnostics n = row_count;
    55	  return n;
    56	end $$;
    57	revoke all on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) from public;
    58	grant execute on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) to authenticated;
    59	
    60	-- (2) merge_video_data: conditional annotationsEditedAt restamp when a Class-B key is
    61	--     present in the patch (a bare MD-finalize / artifact / membership write must NOT bump it).
    62	create or replace function merge_video_data(
    63	  p_playlist_id uuid, p_video_id text, p_fields jsonb,
    64	  p_edited_at timestamptz default now()
    65	) returns void language plpgsql security invoker set search_path = public as $$
    66	declare
    67	  classb text[] := array['personalScore','personalNote','corrections'];
    68	  v_stamp jsonb := '{}'::jsonb; k text;
    69	  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
    70	begin
    71	  perform 1 from playlists
    72	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
    73	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
    74	
    75	  foreach k in array classb loop
    76	    if p_fields ? k then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    77	  end loop;
    78	
    79	  update videos set
    80	    data = (data || (p_fields - 'artifacts'))
    81	      || case when p_fields ? 'artifacts'
    82	           then jsonb_build_object('artifacts',
    83	                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
    84	           else '{}'::jsonb end
    85	      || case when v_stamp <> '{}'::jsonb
    86	           then jsonb_build_object('annotationsEditedAt',
    87	                  coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp)
    88	           else '{}'::jsonb end,
    89	    updated_at = now()
    90	   where playlist_id = p_playlist_id and video_id = p_video_id;
    91	end $$;
    92	revoke all on function merge_video_data(uuid, text, jsonb, timestamptz) from public;
    93	grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;
    94	
    95	-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
    96	--     (git show HEAD:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql)
    97	--     with ONLY two additional keys added to the summary-owned jsonb_build_object:
    98	--     'mdGeneratedAt' and 'mdCorrectionsHash' (§5.7).
    99	create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
   100	  returns void language plpgsql security invoker set search_path = public as $$
   101	declare v_count int;
   102	begin
   103	  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
   104	  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
   105	  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
   106	  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
   107	  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
   108	  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
   109	  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
   110	  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
   111	  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
   112	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
   113	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
   114	  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
   115	  update videos v set
   116	    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
   117	      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
   118	                                                              --     state AND never drop existing summary fields on a
   119	                                                              --     status-only persist (p_video omits them)
   120	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
   121	           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
   122	           'ratings', p_video->'ratings',
   123	           'overallScore', p_video->'overallScore',
   124	           'processedAt', p_video->'processedAt',
   125	           'videoType', p_video->'videoType',
   126	           'audience', p_video->'audience',
   127	           'tags', p_video->'tags',
   128	           'tldr', p_video->'tldr',
   129	           'takeaways', p_video->'takeaways',
   130	           'docVersion', p_video->'docVersion',
   131	           'mdGeneratedAt', p_video->'mdGeneratedAt',
   132	           'mdCorrectionsHash', p_video->'mdCorrectionsHash'))
   133	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
   134	      || jsonb_build_object('artifacts',
   135	           coalesce(v.data->'artifacts', '{}'::jsonb)
   136	           || jsonb_build_object('summaryMd', jsonb_build_object(
   137	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
   138	                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
   139	                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
   140	                -- that IS in committed state, so it must be allowed through (else the row would claim a
   141	                -- promoted artifact for a blob that has not been promoted yet).
   142	                'status', case
   143	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
   144	                                 and p_artifact_status = 'committed'
   145	                                 and v.data->'artifacts'->'summaryMd'->>'key'
   146	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
   147	                              then 'promoted'
   148	                            else p_artifact_status end))),
   149	    updated_at = now()
   150	   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
   151	  get diagnostics v_count = row_count;
   152	  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
   153	end $$;
   154	revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
   155	grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;

exec
/bin/bash -lc 'rg -n "runSync|cloud-sync|syncDeps|spendLedger|spend_ledger|enqueue_job|reserve_serve_model" tests/integration/helpers tests/integration/cloud-sync lib -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/cloud-sync/sync-run.int.test.ts:1:// tests/integration/cloud-sync/sync-run.int.test.ts
tests/integration/cloud-sync/sync-run.int.test.ts:3:// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
tests/integration/cloud-sync/sync-run.int.test.ts:15:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/sync-run.int.test.ts:23:describe('runSync (§7)', () => {
tests/integration/cloud-sync/sync-run.int.test.ts:27:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/sync-run.int.test.ts:29:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:33:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/sync-run.int.test.ts:51:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:61:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/sync-run.int.test.ts:63:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cloud-sync/sync-run.int.test.ts:71:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/helpers/cloud.ts:7:// Task 12 (sync-run) adds the real bodies for: seedLocalPlaylist, ctx.syncDeps({failCloudPromote?}),
tests/integration/helpers/cloud.ts:26:import { readManifest as readManifestFile, writeVideoBaseline } from '@/lib/cloud-sync/manifest';
tests/integration/helpers/cloud.ts:27:import type { SyncDeps } from '@/lib/cloud-sync/sync-run';
tests/integration/helpers/cloud.ts:28:import type { VideoBaseline } from '@/lib/cloud-sync/types';
tests/integration/helpers/cloud.ts:52:  playlistDataRoot: string;    // the per-playlist dir runSync resolves for this key
tests/integration/helpers/cloud.ts:63:  /** Build the SyncDeps for a runSync() call. failCloudPromote wraps the cloud blob store so its
tests/integration/helpers/cloud.ts:66:  syncDeps(opts?: { failCloudPromote?: boolean }): SyncDeps;
tests/integration/helpers/cloud.ts:67:  /** Read the sync manifest runSync wrote for this ctx's playlist. */
tests/integration/helpers/cloud.ts:69:  /** Sum of reserved_cents + actual_cents across spend_ledger (money-safety assertions).
tests/integration/helpers/cloud.ts:70:   *  spend_ledger is GLOBAL (one row per UTC day, NO owner_id) → whole-table total; money-safety
tests/integration/helpers/cloud.ts:72:   *  spend_ledger grants NO client access. */
tests/integration/helpers/cloud.ts:73:  spendLedgerTotal(): Promise<number>;
tests/integration/helpers/cloud.ts:77: *  every cloud-sync integration test. */
tests/integration/helpers/cloud.ts:128:    syncDeps(opts: { failCloudPromote?: boolean } = {}): SyncDeps {
tests/integration/helpers/cloud.ts:146:    async spendLedgerTotal(): Promise<number> {
tests/integration/helpers/cloud.ts:149:        .from('spend_ledger').select('reserved_cents,actual_cents');
tests/integration/helpers/cloud.ts:430: *  delete scenarios). Writes to the SAME manifest path runSync + ctx.readManifest resolve. */
tests/integration/helpers/seed.ts:44:      // Task 7 (cloud dig): enqueueDig reads load.video.durationSeconds (NULL trips enqueue_job's
tests/integration/cloud-sync/e2e.int.test.ts:1:// tests/integration/cloud-sync/e2e.int.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:4:// driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
tests/integration/cloud-sync/e2e.int.test.ts:9:// Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
tests/integration/cloud-sync/e2e.int.test.ts:20:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/e2e.int.test.ts:21:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/integration/cloud-sync/e2e.int.test.ts:22:import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
tests/integration/cloud-sync/e2e.int.test.ts:23:import type { VideoBaseline } from '@/lib/cloud-sync/types';
tests/integration/cloud-sync/e2e.int.test.ts:74:describe('cloud-sync §10 end-to-end scenarios', () => {
tests/integration/cloud-sync/e2e.int.test.ts:91:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:93:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:96:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges
tests/integration/cloud-sync/e2e.int.test.ts:136:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:158:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:176:    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
tests/integration/cloud-sync/e2e.int.test.ts:198:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:227:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:245:    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
tests/integration/cloud-sync/e2e.int.test.ts:249:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:250:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:253:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:255:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:258:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:268:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:299:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:314:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:321:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:334:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:347:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:358:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:364:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:375:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:377:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cloud-sync/e2e.int.test.ts:386:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:397:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:404:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:426:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:428:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:434:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:447:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:461:  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
tests/integration/cloud-sync/e2e.int.test.ts:469:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:480:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:502:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:531:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:557:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:559:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:564:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges
tests/integration/cloud-sync/e2e.int.test.ts:598:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:601:      const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:615:      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
tests/integration/cloud-sync/e2e.int.test.ts:633:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:636:      const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:647:      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
tests/integration/cloud-sync/e2e.int.test.ts:691:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:693:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:698:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);       // the delete itself never charges
tests/integration/cloud-sync/e2e.int.test.ts:702:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:705:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:727:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:729:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:736:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:738:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:741:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:748:  //       exactly. Deleting it would burn reserve_serve_model → spend_ledger to rebuild.
tests/integration/cloud-sync/e2e.int.test.ts:768:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:770:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:777:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:779:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:782:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:805:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:807:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:815:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // healed without any regeneration
tests/integration/cloud-sync/e2e.int.test.ts:818:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:850:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:857:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:887:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:891:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:915:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/stamping.int.test.ts:1:// tests/integration/cloud-sync/stamping.int.test.ts
tests/integration/helpers/clients.ts:37: * T13: `enqueue_job` (T2) now enforces PJ001 (monthly quota) / PJ002 (daily $ cap) / PJ003
tests/integration/helpers/clients.ts:39: * files migrated in T13 call the real `enqueue_job`/`SupabaseEnqueuer` a nontrivial number of
tests/integration/cloud-sync/cloud-stamping.int.test.ts:1:// tests/integration/cloud-sync/cloud-stamping.int.test.ts
lib/html-doc/generate.ts:7:import { mdHash } from '@/lib/cloud-sync/content-hash';
lib/pipeline.ts:17:import { mdHash } from './cloud-sync/content-hash';
lib/dig/generate.ts:125:   *  the local dig-section path, which never reserves/releases a spend_ledger entry. */
lib/cloud-sync/auth.ts:6:  constructor() { super('Not signed in to cloud. Run: cloud-sync login'); this.name = 'NoSessionError'; }
lib/cloud-sync/auth.ts:75:  return path.join(home, '.config', 'youtube-playlist-summaries', 'cloud-sync-token');
lib/html-doc/serve-doc.ts:7:import { mdHash } from '@/lib/cloud-sync/content-hash';
lib/html-doc/serve-doc.ts:60:  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
lib/html-doc/serve-doc.ts:84:    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
lib/cloud-sync/companion.ts:34: *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
lib/job-queue/enqueuer.ts:7: * `enqueue_job` can enforce per-owner quota/cap without a session client. */
lib/job-queue/enqueuer.ts:26:export interface DigJobPayload { durationSeconds: number; } // enqueue_job reads only durationSeconds (PJ003 backstop)
lib/job-queue/enqueuer.ts:41: * Service-role `Enqueuer`: wires `enqueue_job`/`enqueue_preflight` (both service-role-only
lib/job-queue/enqueuer.ts:50:    const { data, error } = await this.serviceClient.rpc('enqueue_job', {
lib/cloud-sync/manifest.ts:1:// lib/cloud-sync/manifest.ts
lib/cloud-sync/manifest.ts:9:  return path.join(dataRoot, playlistKey, '.cloud-sync-manifest.json');
lib/cloud-sync/manifest.ts:12:  return path.join(dataRoot, playlistKey, '.cloud-sync-conflicts.log');
lib/storage/blob-store.ts:15:   *  destroys data on a transient blip (see the B1 and H1 guards in lib/cloud-sync/sync-run.ts).
lib/dig/cloud/enqueue-dig-core.ts:23: *  Charge happens once, inside enqueue_job, only on a fresh enqueue. */
lib/dig/cloud/load-dig-for-serve.ts:18: * resolveMagazineModel / reserve_serve_model (spec §2 money invariant).
lib/job-queue/errors.ts:31: * guardrail error. PJ001/PJ002/PJ003 are the enqueue_job guardrail codes
lib/cloud-sync/sync-run.ts:1:// lib/cloud-sync/sync-run.ts
lib/cloud-sync/sync-run.ts:4:// T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:193:  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
lib/cloud-sync/sync-run.ts:473:export async function runSync(
lib/job-queue/summary-handler.ts:39:/** Live guardrail duration cap — the value the producer pre-block and enqueue_job PJ003 also read. */
lib/job-queue/summary-handler.ts:63:    // Defense-in-depth behind enqueue_job's PJ003 guardrail: re-read the LIVE duration cap and
lib/storage/supabase/supabase-blob-store.ts:32:    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately

codex
A possible edge worth checking is not just hash freshness but render freshness: `decideCompanion` ships a sender envelope on `sourceMdHash` alone. I’m tracing `resolveMagazineModel` to see whether an old generator version or stale section list affects anonymous readiness and whether that should alter reporting.
exec
/bin/bash -lc "nl -ba lib/html-doc/serve-doc.ts | sed -n '1,170p' && rg -n \"readFreshMagazineModel|readTitleStableModel|writeModelEnvelope|sourceMdHash|GENERATOR_VERSION\" lib/html-doc lib -S" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { SupabaseClient } from '@supabase/supabase-js';
     2	import type { BlobStore } from '@/lib/storage/blob-store';
     3	import type { Principal } from '@/lib/storage/principal';
     4	import type { ParsedSummary, MagazineModel } from './types';
     5	import { GENERATOR_VERSION } from './constants';
     6	import { writeModelEnvelope } from './model-store';
     7	import { mdHash } from '@/lib/cloud-sync/content-hash';
     8	import { readFreshMagazineModel, readTitleStableModel } from './read-model';
     9	import { generateMagazineModel } from '@/lib/gemini';
    10	import type { CloudGeminiCaps } from '@/lib/gemini-cost';
    11	import { classifyGeminiFailure, releaseGateOpen } from '@/lib/gemini-failure';
    12	import type { BillingLatch } from '@/lib/job-queue/billing-latch';
    13	import {
    14	  MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
    15	  MAX_SUMMARY_OUTPUT_TOKENS, MAX_MAGAZINE_INPUT_TOKENS, MAX_MAGAZINE_OUTPUT_TOKENS,
    16	} from '@/lib/gemini-cost';
    17	
    18	/** Serve-side caps for the paid magazine transform (only the magazine fields are load-bearing;
    19	 *  the rest satisfy the CloudGeminiCaps type). */
    20	const SERVE_CAPS: CloudGeminiCaps = {
    21	  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
    22	  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
    23	  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
    24	  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
    25	  magazineInputTokens: MAX_MAGAZINE_INPUT_TOKENS,
    26	  magazineOutputTokens: MAX_MAGAZINE_OUTPUT_TOKENS,
    27	};
    28	
    29	export type ResolveResult =
    30	  | { status: 'ok'; model: MagazineModel; stale?: boolean }
    31	  | { status: 'busy' }
    32	  | { status: 'attempts_exhausted' }
    33	  | { status: 'at_capacity' }
    34	  | { status: 'over_budget' }
    35	  | { status: 'denied' };
    36	
    37	export async function resolveMagazineModel(args: {
    38	  supabaseClient: SupabaseClient;
    39	  blobStore: BlobStore;
    40	  principal: Principal;
    41	  playlistId: string;
    42	  videoId: string;
    43	  base: string;
    44	  parsed: ParsedSummary;
    45	  language: 'en' | 'ko';
    46	  /** Stage 3 (§4.2): the MD BODY this model is generated from (NOT the blob key) — hashed
    47	   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
    48	   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
    49	   *  real production caller (serve-summary-core.ts) always supplies it. */
    50	  mdBody?: string;
    51	  signal?: AbortSignal;
    52	}): Promise<ResolveResult> {
    53	  const { supabaseClient, blobStore, principal, playlistId, videoId, base, parsed, language, mdBody, signal } = args;
    54	  const titles = parsed.sections.map((s) => s.title);
    55	
    56	  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
    57	  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
    58	
    59	  // Absent / drifted / stale-version → materialize under the reserve RPC.
    60	  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
    61	    p_playlist_id: playlistId, p_video_id: videoId,
    62	  });
    63	  if (error) throw error;
    64	  const row = (data as Array<{ status: string; release_token: string | null }> | null)?.[0];   // table-return → data[0]
    65	  const reserveStatus = row?.status;
    66	  const releaseToken = row?.release_token ?? null;
    67	  switch (reserveStatus) {
    68	    case 'denied': return { status: 'denied' };
    69	    case 'in_flight': {
    70	      // Single-flight: another attempt holds the lease. Serve the model if it landed meanwhile, else busy.
    71	      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
    72	      return now.status === 'ok' ? now : { status: 'busy' };
    73	    }
    74	    case 'attempts_exhausted': return { status: 'attempts_exhausted' };
    75	    case 'at_capacity': return { status: 'at_capacity' };
    76	    case 'owner_over_budget': {
    77	      // Spec D5: serve the title-stable stale rendering instead of failing; else 503.
    78	      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
    79	      return staleRead.status === 'ok'
    80	        ? { status: 'ok', model: staleRead.model, stale: true }
    81	        : { status: 'over_budget' };
    82	    }
    83	    case 'reserved': break;
    84	    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
    85	  }
    86	
    87	  // We hold the lease and this attempt was charged. Generate → upsert (overwrite) → serve.
    88	  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
    89	  // regenerated model on drift / version-bump must OVERWRITE the stale blob so the doc self-heals
    90	  // (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).
    91	  // On a terminal outcome (success or throw) we settle the reservation via settle_serve_model: success
    92	  // keeps the charge (released=false) and clears the per-attempt token; a throw refunds ONLY a
    93	  // positively-not-metered class-A failure under an open gate — same rule as the generation worker-runner
    94	  // (Task 10). Anything else (metered, non-class-A, gate closed) keeps the charge — over-count is safe,
    95	  // under-count is the bug.
    96	  const billing: BillingLatch = { metered: false };
    97	  try {
    98	    const model = await generateMagazineModel(
    99	      parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
   100	      language,
   101	      { caps: SERVE_CAPS, signal, billing },
   102	    );
   103	    await writeModelEnvelope(principal, base, {
   104	      sourceMd: parsed.sourceMd ?? `${base}.md`,
   105	      generatedAt: new Date().toISOString(),
   106	      sourceSections: titles,
   107	      generatorVersion: GENERATOR_VERSION,
   108	      model,
   109	      // Hash the MD BODY, not the key — see the `mdBody` param doc above (§4.2).
   110	      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
   111	    }, blobStore);
   112	    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: false });
   113	    return { status: 'ok', model };
   114	  } catch (err) {
   115	    // Same rule as generation: refund only a positively-not-metered class-A failure.
   116	    const released = releaseGateOpen()
   117	      && classifyGeminiFailure(err, signal) === 'release'
   118	      && !billing.metered;
   119	    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: released });
   120	    throw err;
   121	  }
   122	}
lib/html-doc/model-store.ts:12: * still parse; the cloud freshness gate requires it to `=== GENERATOR_VERSION`.
lib/html-doc/model-store.ts:22:    sourceMdHash: z.string().optional(),
lib/html-doc/model-store.ts:24:  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
lib/html-doc/model-store.ts:43:export async function writeModelEnvelope(
lib/html-doc/render.ts:8:import { GENERATOR_VERSION } from './constants';
lib/html-doc/render.ts:9:export { GENERATOR_VERSION };
lib/html-doc/render.ts:113:${share ? '' : `<meta name="generator" content="${GENERATOR_VERSION}">
lib/html-doc/generate.ts:5:import { renderMagazineHtml, GENERATOR_VERSION } from './render';
lib/html-doc/generate.ts:6:import { writeModelEnvelope } from './model-store';
lib/html-doc/generate.ts:50:  await writeModelEnvelope(principal, base, {
lib/html-doc/generate.ts:54:    generatorVersion: GENERATOR_VERSION,
lib/html-doc/generate.ts:59:    sourceMdHash: mdHash(md),
lib/html-doc/read-model.ts:4:import { GENERATOR_VERSION } from './constants';
lib/html-doc/read-model.ts:24:  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
lib/html-doc/read-model.ts:29:export async function readFreshMagazineModel(args: {
lib/html-doc/read-model.ts:44:export async function readTitleStableModel(args: {
lib/html-doc/serve-doc.ts:5:import { GENERATOR_VERSION } from './constants';
lib/html-doc/serve-doc.ts:6:import { writeModelEnvelope } from './model-store';
lib/html-doc/serve-doc.ts:8:import { readFreshMagazineModel, readTitleStableModel } from './read-model';
lib/html-doc/serve-doc.ts:47:   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
lib/html-doc/serve-doc.ts:48:   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
lib/html-doc/serve-doc.ts:56:  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:71:      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:78:      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:88:  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
lib/html-doc/serve-doc.ts:103:    await writeModelEnvelope(principal, base, {
lib/html-doc/serve-doc.ts:107:      generatorVersion: GENERATOR_VERSION,
lib/html-doc/serve-doc.ts:110:      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
lib/html-doc/batch.ts:10:import { DIG_GENERATOR_VERSION } from '../dig/generate';
lib/html-doc/batch.ts:44:    return gv === undefined || gv < DIG_GENERATOR_VERSION;
lib/html-doc/constants.ts:5:export const GENERATOR_VERSION = 'magazine-skim v2';
lib/html-doc/serve-summary-core.ts:114:    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
lib/html-doc/dig-merge.ts:22:import { DIG_GENERATOR_VERSION } from '../dig/generate';
lib/html-doc/dig-merge.ts:104:        isStale_ = matched.genVersion < DIG_GENERATOR_VERSION;
lib/html-doc/dig-merge.ts:154:    ms.isStale = matched.genVersion < DIG_GENERATOR_VERSION;
lib/dig/dig-section.ts:7:import { generateDig, DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/dig-section.ts:99:      genVersion: DIG_GENERATOR_VERSION,
lib/html-doc/build-doc-html.ts:5:import { GENERATOR_VERSION } from './render';
lib/html-doc/build-doc-html.ts:56:    if (cachedVersion === GENERATOR_VERSION) return { ok: true, html: cachedHtml };
lib/dig/generate.ts:15:export const DIG_GENERATOR_VERSION = 9;
lib/dig/generate.ts:54: * Note: inline [[TS:i]] transcript citations were removed (DIG_GENERATOR_VERSION 8). Gemini
lib/dig/cloud/dig-blob-key.ts:1:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/cloud/dig-blob-key.ts:4:/** job_version for a cloud dig job — encodes DIG_GENERATOR_VERSION so a bump lands in a
lib/dig/cloud/dig-blob-key.ts:7:  return `dig-${DIG_GENERATOR_VERSION}`;
lib/dig/cloud/dig-blob-key.ts:22:  const key = `dig/${base}/${sectionId}.r${DIG_GENERATOR_VERSION}.md`;
lib/dig/cloud/load-dig-for-serve.ts:5:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/cloud/load-dig-for-serve.ts:33:  const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
lib/dig/cloud/write-dig-section-blob.ts:3:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/cloud/write-dig-section-blob.ts:38:    `genVersion: ${DIG_GENERATOR_VERSION}`,
lib/cloud-sync/companion.ts:42: *       generatorVersion, never sourceMdHash, so a prose-only MD change — precisely the
lib/cloud-sync/companion.ts:49: *  independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT is
lib/cloud-sync/companion.ts:63:  if (senderModel.kind === 'envelope' && senderModel.envelope.sourceMdHash === winnerMdHash) {
lib/cloud-sync/companion.ts:69:  if (receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash === winnerMdHash) {
lib/cloud-sync/companion.ts:75:  //  - DELETE the blob only on PROOF. A receiver envelope whose sourceMdHash is present and differs
lib/cloud-sync/companion.ts:78:  //    read, and a legacy pre-1F-a envelope predates sourceMdHash entirely (the field is .optional()
lib/cloud-sync/companion.ts:90:    && receiverModel.envelope.sourceMdHash !== undefined;
lib/cloud-sync/sync-run.ts:35:import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
lib/cloud-sync/sync-run.ts:393:    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
lib/html-doc/read-model.ts:4:import { GENERATOR_VERSION } from './constants';
lib/html-doc/read-model.ts:24:  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
lib/html-doc/read-model.ts:29:export async function readFreshMagazineModel(args: {
lib/html-doc/read-model.ts:44:export async function readTitleStableModel(args: {
lib/html-doc/model-store.ts:12: * still parse; the cloud freshness gate requires it to `=== GENERATOR_VERSION`.
lib/html-doc/model-store.ts:22:    sourceMdHash: z.string().optional(),
lib/html-doc/model-store.ts:24:  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
lib/html-doc/model-store.ts:43:export async function writeModelEnvelope(
lib/html-doc/serve-summary-core.ts:114:    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
lib/html-doc/build-doc-html.ts:5:import { GENERATOR_VERSION } from './render';
lib/html-doc/build-doc-html.ts:56:    if (cachedVersion === GENERATOR_VERSION) return { ok: true, html: cachedHtml };
lib/html-doc/serve-doc.ts:5:import { GENERATOR_VERSION } from './constants';
lib/html-doc/serve-doc.ts:6:import { writeModelEnvelope } from './model-store';
lib/html-doc/serve-doc.ts:8:import { readFreshMagazineModel, readTitleStableModel } from './read-model';
lib/html-doc/serve-doc.ts:47:   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
lib/html-doc/serve-doc.ts:48:   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
lib/html-doc/serve-doc.ts:56:  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:71:      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:78:      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:88:  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
lib/html-doc/serve-doc.ts:103:    await writeModelEnvelope(principal, base, {
lib/html-doc/serve-doc.ts:107:      generatorVersion: GENERATOR_VERSION,
lib/html-doc/serve-doc.ts:110:      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
lib/html-doc/constants.ts:5:export const GENERATOR_VERSION = 'magazine-skim v2';
lib/html-doc/batch.ts:10:import { DIG_GENERATOR_VERSION } from '../dig/generate';
lib/html-doc/batch.ts:44:    return gv === undefined || gv < DIG_GENERATOR_VERSION;
lib/job-queue/dig-handler.ts:45:    // DIG_GENERATOR_VERSION must NOT write a current-version blob it never paid for.
lib/html-doc/dig-merge.ts:22:import { DIG_GENERATOR_VERSION } from '../dig/generate';
lib/html-doc/dig-merge.ts:104:        isStale_ = matched.genVersion < DIG_GENERATOR_VERSION;
lib/html-doc/dig-merge.ts:154:    ms.isStale = matched.genVersion < DIG_GENERATOR_VERSION;
lib/html-doc/render.ts:8:import { GENERATOR_VERSION } from './constants';
lib/html-doc/render.ts:9:export { GENERATOR_VERSION };
lib/html-doc/render.ts:113:${share ? '' : `<meta name="generator" content="${GENERATOR_VERSION}">
lib/html-doc/generate.ts:5:import { renderMagazineHtml, GENERATOR_VERSION } from './render';
lib/html-doc/generate.ts:6:import { writeModelEnvelope } from './model-store';
lib/html-doc/generate.ts:50:  await writeModelEnvelope(principal, base, {
lib/html-doc/generate.ts:54:    generatorVersion: GENERATOR_VERSION,
lib/html-doc/generate.ts:59:    sourceMdHash: mdHash(md),

exec
/bin/bash -lc 'rg -n "generatorVersion|sourceSections|sourceMdHash|modelEnvelope|readFreshMagazineModel|title-stable|stale" tests/lib tests/integration -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/video-updated-at.test.ts:8:// trigger exists that path leaves `updated_at` stale.
tests/integration/video-updated-at.test.ts:57:  // Before the trigger exists, this leaves updated_at stale at t1. ---
tests/integration/share-route.test.ts:81:      sourceSections: ['Intro'],
tests/integration/share-route.test.ts:82:      generatorVersion: GENERATOR_VERSION,
tests/integration/share-route.test.ts:169:  it('B8: valid token, materialized model is STALE (wrong generatorVersion) → 503 not-ready (never 200, never a charge)', async () => {
tests/integration/share-route.test.ts:173:    // Materialize a model envelope that exists but is stale — wrong generatorVersion, so
tests/integration/share-route.test.ts:183:        sourceSections: ['Intro'],
tests/integration/share-route.test.ts:184:        generatorVersion: 'stale-vX', // deliberately mismatched — must NOT equal GENERATOR_VERSION
tests/integration/html-download.test.ts:50:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/html-download.test.ts:230:  // ── Stage 1G / Task 3: owner route wiring of ResolveResult.over_budget / .stale (spec D6) ──
tests/integration/html-download.test.ts:242:    expect(res.headers.get('x-magazine-stale')).toBeNull();
tests/integration/html-download.test.ts:245:  it('P5: owner over budget, title-stable model exists → 200 rendered magazine, X-Magazine-Stale: 1', async () => {
tests/integration/html-download.test.ts:254:      sourceSections: titles,          // title-stable: same titles as the current MD
tests/integration/html-download.test.ts:255:      generatorVersion: 'OLD',         // NOT current GENERATOR_VERSION → not fresh, but title-stable
tests/integration/html-download.test.ts:256:      model: { sections: [{ lead: 'old-stale-lead', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] },
tests/integration/html-download.test.ts:265:    expect(res.headers.get('x-magazine-stale')).toBe('1');
tests/integration/html-download.test.ts:267:    expect(body).toContain('old-stale-lead'); // proves the served body is the STALE cached model, not a 503/regen
tests/integration/html-download.test.ts:279:      sourceSections: titles,
tests/integration/html-download.test.ts:280:      generatorVersion: GENERATOR_VERSION, // FRESH — matches current version
tests/integration/html-download.test.ts:290:    expect(res.headers.get('x-magazine-stale')).toBeNull();
tests/integration/html-download.test.ts:308:    expect(res.headers.get('x-magazine-stale')).toBeNull();
tests/integration/summary-handler.test.ts:199://     version the worker no longer speaks must fail fast, not run a stale pipeline.
tests/integration/jobs-producer-polling.test.ts:91:  // collapse these to a single row — the newest — not surface both (stale `failed` + new `queued`).
tests/integration/jobs-producer-polling.test.ts:112:  expect(retryRows[0].status).toBe('queued'); // the NEW row wins, not the stale `failed` one
tests/integration/pdf-cloud.test.ts:212:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/pdf-cloud.test.ts:255: *  MD) so resolveMagazineModel's readFreshMagazineModel short-circuits: NO Gemini call, NO
tests/integration/pdf-cloud.test.ts:263:    sourceSections: titles,
tests/integration/pdf-cloud.test.ts:264:    generatorVersion: GENERATOR_VERSION,
tests/integration/worker-persistence-rpcs.test.ts:98:  // Promote first, then a stale worker / retry re-persists the same key as 'committed'.
tests/integration/worker-persistence-rpcs.test.ts:105:test('persist_summary preserves operational fields owned by other features (archived) against the stale payload', async () => {
tests/integration/worker-persistence-rpcs.test.ts:126:test('persist_summary preserves ALL concurrent non-summary state (membership order + other-feature fields) against the stale payload', async () => {
tests/integration/worker-persistence-rpcs.test.ts:139:  // The stale enqueue-time payload still carries playlistIndex:3 and no digDeeperMd — persist_summary
tests/integration/worker-persistence-rpcs.test.ts:144:  expect(row.data!.data.playlistIndex).toBe(9);        // membership order NOT reverted to the stale 3
tests/integration/job-queue-worker.test.ts:35:test('heartbeat extends the lease for the current owner and rejects a stale token', async () => {
tests/integration/job-queue-worker.test.ts:41:  const stale = await admin().rpc('heartbeat_job', {
tests/integration/job-queue-worker.test.ts:43:  expect(stale.data).toBe(false);
tests/integration/job-queue-worker.test.ts:46:test('a stale lease token cannot complete a reclaimed job (fencing)', async () => {
tests/integration/job-queue-worker.test.ts:58:  const staleDone = await admin().rpc('complete_job', {
tests/integration/job-queue-worker.test.ts:60:  expect(staleDone.data).toBe(false);
tests/integration/job-queue-worker.test.ts:66:test('a stale lease token cannot fail a reclaimed job (fencing)', async () => {
tests/integration/job-queue-worker.test.ts:76:  const staleFail = await admin().rpc('fail_job', {
tests/integration/job-queue-worker.test.ts:78:  expect(staleFail.data).toBeNull();                       // w1 lost the lease
tests/integration/job-queue-worker.test.ts:80:  expect(row.data!.status).toBe('active');                  // stale call did NOT change status
tests/integration/serve-doc-materialize.test.ts:68:  expect(env?.generatorVersion).toBeDefined(); // upserted + cached
tests/integration/serve-doc-materialize.test.ts:107:it('re-materializes on drift (sourceSections mismatch) — B3', async () => {
tests/integration/serve-doc-materialize.test.ts:114:  const drifted = parsed(); drifted.sections[0].title = 'Renamed'; // titles now differ from the cached sourceSections
tests/integration/serve-doc-materialize.test.ts:121:it('re-materializes on a STALE generatorVersion even when sourceSections match (F6 — version gate)', async () => {
tests/integration/serve-doc-materialize.test.ts:127:  // Seed a cached envelope whose sourceSections MATCH the current parse (NO title drift) but whose
tests/integration/serve-doc-materialize.test.ts:128:  // generatorVersion is stale (guaranteed ≠ current via the `-STALE` suffix). ONLY the version check can
tests/integration/serve-doc-materialize.test.ts:134:    sourceSections: p.sections.map((s) => s.title),
tests/integration/serve-doc-materialize.test.ts:135:    generatorVersion: `${GENERATOR_VERSION}-STALE`,
tests/integration/serve-doc-materialize.test.ts:140:  expect(generateMagazineModel).toHaveBeenCalledTimes(1);         // stale version → REGENERATED, not served from cache
tests/integration/serve-doc-materialize.test.ts:141:  // The returned model is the freshly-generated one (mock lead 'L'), NOT the seeded stale model (lead 'old').
tests/integration/serve-doc-materialize.test.ts:143:  // Persistence proof (Option A): writeModelEnvelope upserts (plain `put`), so the stale blob was
tests/integration/serve-doc-materialize.test.ts:148:  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION);
tests/integration/serve-doc-materialize.test.ts:175:  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION); // valid envelope now persisted, overwriting the corrupt blob
tests/integration/serve-doc-materialize.test.ts:179:// ── Stage 1G / G1 Task 2: owner_over_budget → title-stable serve-stale (spec D5) ──
tests/integration/serve-doc-materialize.test.ts:180:const staleModel = { sections: [{ lead: 'old', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] };
tests/integration/serve-doc-materialize.test.ts:182:it('P5: over budget + title-stable model → { ok, stale:true }, no charge', async () => {
tests/integration/serve-doc-materialize.test.ts:190:    sourceSections: p.sections.map((s) => s.title), generatorVersion: 'OLD', model: staleModel,
tests/integration/serve-doc-materialize.test.ts:195:  expect(res).toEqual({ status: 'ok', model: expect.anything(), stale: true });
tests/integration/serve-doc-materialize.test.ts:212:it('P6b: over budget + titles DRIFTED → { over_budget } (not stale — avoids positional mis-pair)', async () => {
tests/integration/serve-doc-materialize.test.ts:220:    sourceSections: ['Something Else'], generatorVersion: 'OLD', model: staleModel, // deliberately mismatched titles
tests/integration/serve-doc-materialize.test.ts:236:    sourceSections: p.sections.map((s) => s.title), generatorVersion: GENERATOR_VERSION, // FRESH — matches current version
tests/integration/serve-doc-materialize.test.ts:242:  expect(res).toEqual({ status: 'ok', model: expect.anything() }); // no `stale` — fresh path (readFreshMagazineModel short-circuit)
tests/integration/serve-doc-materialize.test.ts:243:  expect((res as { stale?: boolean }).stale).toBeUndefined();
tests/integration/serve-doc-materialize.test.ts:248:it('P13: stale served over budget; recovers to fresh (no stale) once under budget', async () => {
tests/integration/serve-doc-materialize.test.ts:256:    sourceSections: p.sections.map((s) => s.title), generatorVersion: 'OLD', model: staleModel,
tests/integration/serve-doc-materialize.test.ts:259:  const stale = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
tests/integration/serve-doc-materialize.test.ts:260:  expect(stale).toMatchObject({ status: 'ok', stale: true });
tests/integration/serve-doc-materialize.test.ts:261:  // Clear today's over-budget state, leaving the stale envelope in place.
tests/integration/serve-doc-materialize.test.ts:265:  expect((fresh as { stale?: boolean }).stale).toBeUndefined(); // re-materialized to current version, not stale
tests/integration/serve-doc-materialize.test.ts:266:  if (fresh.status === 'ok') expect(fresh.model.sections[0].lead).toBe('L'); // freshly-generated (mock), not the stale 'old' model
tests/lib/serial-migrate-normalization.test.ts:116:      // mean a pass generated spurious renames (e.g. re-reading a stale index).
tests/lib/model-store-cloud.test.ts:7:  sourceMd: 'a.md', generatedAt: '2026-07-09T00:00:00.000Z', sourceSections: ['A'],
tests/lib/model-store-cloud.test.ts:8:  generatorVersion: 'magazine-skim v2',
tests/lib/model-store-cloud.test.ts:33:it('schema accepts generatorVersion', () => {
tests/lib/model-store-cloud.test.ts:42:  expect(read?.generatorVersion).toBe('magazine-skim v2');
tests/lib/model-store-cloud.test.ts:49:  await writeModelEnvelope(P, 'a', { ...envelope, generatorVersion: 'magazine-skim v3' }, store); // overwrites
tests/lib/model-store-cloud.test.ts:51:  expect(read?.generatorVersion).toBe('magazine-skim v3'); // last write wins (upsert)
tests/lib/serial-migrate-exec.test.ts:229:  it('repairs a stale index field when the file was already renamed by a crashed run', async () => {
tests/lib/html-doc/__snapshots__/render-dig-deeper.golden.test.ts.snap:275:        // Refresh (stale dug → re-dig in place) — must be before .dig-trigger check
tests/lib/html-doc/eligibility.test.ts:35:  it('summary mode: needs work iff summary missing/stale', () => {
tests/lib/html-doc/generate.test.ts:140:  expect(envelope.sourceSections).toEqual(['First', 'Conclusion']);
tests/lib/html-doc/rerender.test.ts:44:function envelope(model = MODEL, sourceSections = SECTIONS) {
tests/lib/html-doc/rerender.test.ts:45:  return { sourceMd: 'a-title.md', generatedAt: 'now', sourceSections, model };
tests/lib/html-doc/rerender.test.ts:210:    await writeModelEnvelope(localPrincipal(dir), 'b-title', { sourceMd: 'b-title.md', generatedAt: 'now', sourceSections: ['x'], model: MODEL });
tests/lib/html-doc/dig-merge.test.ts:44:function makeEnvelope(sourceSections: string[], modelSections: { lead: string; bullets: { label: string; text: string }[] }[]): ModelEnvelope {
tests/lib/html-doc/dig-merge.test.ts:48:    sourceSections,
tests/lib/html-doc/dig-merge.test.ts:348:  it('returns gist=null for all sections when titles do not match sourceSections', () => {
tests/lib/html-doc/dig-merge.test.ts:384:    // But sourceSections must match summaryTitles — if they match, model.sections length
tests/lib/html-doc/dig-merge.test.ts:386:    // For this test: sourceSections matches, but we'll use a model with fewer sections
tests/lib/html-doc/dig-merge.test.ts:388:    // Actually: sameTitles compares parsedTitles vs sourceSections, not model.sections.
tests/lib/html-doc/dig-merge.test.ts:389:    // If sourceSections matches but model.sections is shorter, overflow sections get null.
tests/lib/html-doc/dig-merge.test.ts:393:    // Manually construct envelope where sourceSections matches but model.sections is shorter
tests/lib/html-doc/dig-merge.test.ts:397:      sourceSections: summaryTitles, // matches all 4 summary titles
tests/lib/html-doc/dig-merge.test.ts:428:      sourceSections: ['Only Section'],
tests/lib/html-doc/dig-merge.test.ts:582:  it('marks a matched section stale when its genVersion < current', () => {
tests/lib/html-doc/dig-merge.test.ts:600:  it('treats a zero genVersion as stale (legacy doc)', () => {
tests/lib/html-doc/dig-merge.test.ts:609:  it('non-dug sections are never stale', () => {
tests/lib/html-doc/dig-merge.test.ts:616:  it('marks a title-matched section stale when genVersion < current', () => {
tests/lib/html-doc/ensure.test.ts:55:  it('minor-stale with cached model → cheap re-render (no Gemini), stamp', async () => {
tests/lib/html-doc/ensure.test.ts:72:  it('{3,0} stored is now minor-stale → cheap re-render (not re-summarize)', async () => {
tests/lib/html-doc/ensure.test.ts:87:  // branch (unlike the nearby minor-stale test, which injects current: {2,1} to force the cheap re-render).
tests/lib/html-doc/ensure.test.ts:88:  it('major-stale ({2,0}) with cached model → deletes models/<base>.json so fuller bullets regenerate, calls writeSummaryDoc, does NOT call reRenderSummaryHtml', async () => {
tests/lib/html-doc/read-model.test.ts:7:import { readFreshMagazineModel, isFresh, sameTitles, readTitleStableModel } from '@/lib/html-doc/read-model';
tests/lib/html-doc/read-model.test.ts:21:  return { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A', 'B'],
tests/lib/html-doc/read-model.test.ts:22:    generatorVersion: GENERATOR_VERSION, model: fakeModel, ...over };
tests/lib/html-doc/read-model.test.ts:30:    expect(isFresh(envelope({ sourceSections: ['A', 'C'] }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:32:  it('false when generatorVersion differs', () => {
tests/lib/html-doc/read-model.test.ts:33:    expect(isFresh(envelope({ generatorVersion: 'old' }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:37:describe('readFreshMagazineModel', () => {
tests/lib/html-doc/read-model.test.ts:42:    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:51:    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:55:  it('returns not_ready when the envelope is stale (version bump)', async () => {
tests/lib/html-doc/read-model.test.ts:56:    mockReadModelEnvelope.mockResolvedValue(envelope({ generatorVersion: 'old' }));
tests/lib/html-doc/read-model.test.ts:57:    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:65:    expect(sameTitles(envelope({ sourceSections: ['B', 'A'] }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:66:    expect(sameTitles(envelope({ sourceSections: ['A'] }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:73:  it('ok with the model when the envelope exists and titles match — version ignored (stale ok)', async () => {
tests/lib/html-doc/read-model.test.ts:74:    mockReadModelEnvelope.mockResolvedValue(envelope({ generatorVersion: 'OLD' })); // stale VERSION, same titles
tests/lib/html-doc/read-model.test.ts:80:    mockReadModelEnvelope.mockResolvedValue(envelope({ sourceSections: ['X', 'B'], generatorVersion: 'OLD' }));
tests/lib/html-doc/render-dig-deeper.cloud.test.ts:23:  // Force a stale dug section: genVersion below current ⇒ mergeDigDoc marks it stale.
tests/lib/html-doc/render-dig-deeper.cloud.test.ts:24:  const staleDug = [{ sectionId: 65, startSec: 65, title: 'A', bodyMarkdown: 'b', generatedAt: 'g', genVersion: 1, slides: [] }] as never;
tests/lib/html-doc/render-dig-deeper.cloud.test.ts:25:  const html = renderDigDeeperDoc({ ...base, dug: staleDug, nonce: 'n1', cloud: { playlistId: 'p1', isAnonymous: false } });
tests/lib/html-doc/render-dig-deeper.test.ts:459:    sourceSections: ['Introduction', 'Main Content'],
tests/lib/html-doc/render-dig-deeper.test.ts:637:        sourceSections: ['Conclusion'],
tests/lib/html-doc/render-dig-deeper.test.ts:980:  describe('Behavior 10 — .dig-refresh control on stale dug sections', () => {
tests/lib/html-doc/render-dig-deeper.test.ts:988:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:989:      const html = renderDigDeeperDoc({ summary, envelope: null, dug: [staleDug], mdPath, videoId: 'vid123' });
tests/lib/html-doc/render-dig-deeper.test.ts:995:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:996:      const html = renderDigDeeperDoc({ summary, envelope: null, dug: [staleDug], mdPath, videoId: 'vid123' });
tests/lib/html-doc/render-dig-deeper.test.ts:1017:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:1018:      const html = renderDigDeeperDoc({ summary, envelope: null, dug: [staleDug], mdPath, videoId: 'vid123' });
tests/lib/html-doc/render-dig-deeper.test.ts:1027:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:1028:      const html = renderDigDeeperDoc({ summary, envelope: null, dug: [staleDug], mdPath, videoId: 'vid123' });
tests/lib/job-queue/dig-handler.test.ts:124:it('rejects a stale-version job (job.version != current) as NonRetryableError, no generation', async () => {
tests/lib/job-queue/dig-handler.test.ts:125:  const staleJob = { ...job, version: 'dig-0' };
tests/lib/job-queue/dig-handler.test.ts:126:  await expect(makeDigHandler({} as any)(staleJob as any, ctx as any)).rejects.toBeInstanceOf(NonRetryableError);
tests/lib/html-doc/render-share.test.ts:6:  sections: [{ title: 'S1', prose: 'p', timestamp: null }], sourceSectionsRaw: [],
tests/integration/cloud-sync/e2e.int.test.ts:42:/** A schema-valid ModelEnvelope (ModelEnvelopeSchema) whose sourceMdHash is caller-supplied. */
tests/integration/cloud-sync/e2e.int.test.ts:43:const modelEnvelope = (sourceMdHash: string) => ({
tests/integration/cloud-sync/e2e.int.test.ts:44:  sourceMd: 'seed.md', generatedAt: '2026-01-01T00:00:00.000Z', sourceSections: ['A'],
tests/integration/cloud-sync/e2e.int.test.ts:51:  sourceMdHash,
tests/integration/cloud-sync/e2e.int.test.ts:118:  it('row 2: corrections-current lower-major beats stale higher-major (currency beats format)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:121:    const bodyStale = '# StaleHiMajor\n\nhigher-major but corrections-stale\n';          // local (loser)
tests/integration/cloud-sync/e2e.int.test.ts:150:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:151:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:153:    const body = '# StaleBoth\n\nidentical stale content\n';
tests/integration/cloud-sync/e2e.int.test.ts:154:    const staleHash = mdHash('stale-corrections'); // != mdHash('') → both sides corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:155:    await seedLocalVideoFull(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
tests/integration/cloud-sync/e2e.int.test.ts:156:    await seedCloudVideo(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
tests/integration/cloud-sync/e2e.int.test.ts:209:  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
tests/integration/cloud-sync/e2e.int.test.ts:412:  //    corrections-current, cloud stale → copyToCloud OVERWROTE cloud's (different-correction) MD body.
tests/integration/cloud-sync/e2e.int.test.ts:487:  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
tests/integration/cloud-sync/e2e.int.test.ts:490:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:492:    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
tests/integration/cloud-sync/e2e.int.test.ts:506:    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
tests/integration/cloud-sync/e2e.int.test.ts:518:    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
tests/integration/cloud-sync/e2e.int.test.ts:563:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:664:  //    decides only whether a REPLACEMENT can be shipped; the receiver's own sourceMdHash decides
tests/integration/cloud-sync/e2e.int.test.ts:666:  //    identical unprovable-cloud-sender setup and differ ONLY in the receiver's sourceMdHash,
tests/integration/cloud-sync/e2e.int.test.ts:672:  //     generatorVersion, never sourceMdHash, so a prose-only change (headings identical, which is
tests/integration/cloud-sync/e2e.int.test.ts:673:  //     exactly the recency-tiebreak case) renders stale Gemini prose as current forever, and
tests/integration/cloud-sync/e2e.int.test.ts:674:  //     dig-deeper never regenerates. Its staleness needs no sender read to establish.
tests/integration/cloud-sync/e2e.int.test.ts:675:  it('H-R5-1(i): an unprovable sender read still DELETES a provably-stale receiver model (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:689:      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalOld)))}\n`, 'utf8'), 'application/json',
tests/integration/cloud-sync/e2e.int.test.ts:696:    expect(await localBlobBytes(ctx, modelKey(ctx))).toBeNull();  // provably stale → deleted
tests/integration/cloud-sync/e2e.int.test.ts:722:    const envelope = modelEnvelope(bodyHash(bodyCloudWin));
tests/integration/cloud-sync/e2e.int.test.ts:734:    expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyCloudWin));
tests/integration/cloud-sync/e2e.int.test.ts:735:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
tests/integration/cloud-sync/e2e.int.test.ts:766:      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin)))}\n`, 'utf8'), 'application/json',
tests/integration/cloud-sync/e2e.int.test.ts:775:    expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyLocalWin));
tests/integration/cloud-sync/e2e.int.test.ts:867:  it('L-R5-2: a stale local playlist title does NOT overwrite a fresher cloud title (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:871:    const staleLocalTitle = 'Deep Learning Lectures';
tests/integration/cloud-sync/e2e.int.test.ts:884:      playlistTitle: staleLocalTitle,
tests/lib/html-doc/serve-doc-mapping.test.ts:60:    sourceSections: ['Intro'], // must match parsed().sections titles for isFresh() to accept it
tests/lib/html-doc/serve-doc-mapping.test.ts:61:    generatorVersion: GENERATOR_VERSION,
tests/lib/html-doc/model-store.test.ts:15:  sourceSections: ['The Foundation'],
tests/lib/html-doc/model-store.test.ts:65:    const bad = { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['s'], model: { sections: [{ lead: 'l', bullets: [] }] } };
tests/lib/html-doc/model-store.test.ts:74:      sourceMd: 'a-title.md', generatedAt: 'now', sourceSections: ['s'],
tests/lib/html-doc/file-response.test.ts:54:  it('staleMarker sets X-Magazine-Stale on html; absent by default', () => {
tests/lib/html-doc/file-response.test.ts:55:    const on = fileResponse('<html>', { kind: 'html', download: false, base: 'b', cache: 'private, no-store', csp: 'x', staleMarker: true });
tests/lib/html-doc/file-response.test.ts:60:  it('staleMarker is ignored on kind:"md" (html-only invariant enforced in code, not just by caller)', () => {
tests/lib/html-doc/file-response.test.ts:61:    const r = fileResponse('# hi', { kind: 'md', download: false, base: 'b', cache: 'no-store', staleMarker: true });
tests/lib/dig/slides.test.ts:430:test('prunes stale sectionId-* assets after writing the new set', async () => {
tests/lib/dig/slides.test.ts:433:  fs.writeFileSync(path.join(dir, '160-999-1000.jpg'), 'old'); // stale orphan, same section
tests/lib/dig/slides.test.ts:438:  expect(fs.existsSync(path.join(dir, '160-999-1000.jpg'))).toBe(false); // stale pruned
tests/lib/dig/slides.test.ts:452:test('legit zero-token re-dig prunes stale assets (M3)', async () => {
tests/lib/dig/slides.test.ts:455:  fs.writeFileSync(path.join(dir, '160-5-9.jpg'), 'stale');
tests/lib/dig/cloud/load-dig-for-serve.test.ts:101:    // Only a stale-version blob exists → zero CURRENT-version digs. The interactive dig doc must
tests/lib/dig/cloud/load-dig-for-serve.test.ts:104:    const bundle = fakeBundle({ [`dig/base/65.r${V - 1}.md`]: digBlob(65) }); // stale version only
tests/lib/pipeline.test.ts:764:    it('re-derives a stale in-playlist index to its current position', async () => {
tests/lib/pipeline.test.ts:765:      const stale = makeIndexedVideo('vidA', { playlistIndex: 1 }); // frozen at 1
tests/lib/pipeline.test.ts:767:      mockReadIndex.mockReturnValue({ playlistUrl: PLAYLIST_URL, outputFolder, videos: [...others, stale] });
tests/lib/cloud-sync/reconcile-class-a.test.ts:15:  it('mdHash equal but BOTH stale vs reconciled corrections → skip but needsRegen (round-v8 H-1)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:19:  it('mdHash equal but one current, one stale → current wins, NOT skip (Blocking ③ scenario 1)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:27:  it('one corrections-current, other stale → current wins even if stale side has higher format', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:45:  it('neither current (both stale) → keep higher-major, flag needsRegen', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:49:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true }); // cloud higher major → local, but stale
tests/lib/cloud-sync/regenerate-stamp.test.ts:7:// corrected MD that is never marked corrections-current is judged stale forever.
tests/lib/cloud-sync/companion.test.ts:4:const env = (sourceMdHash?: string): ModelEnvelope => ({
tests/lib/cloud-sync/companion.test.ts:5:  sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
tests/lib/cloud-sync/companion.test.ts:7:  ...(sourceMdHash ? { sourceMdHash } : {}),
tests/lib/cloud-sync/companion.test.ts:22:    ['receiver stale', envelope('h2')],
tests/lib/cloud-sync/companion.test.ts:30://    NOT answer "is the receiver's model stale?". Only the RECEIVER's own sourceMdHash answers that,
tests/lib/cloud-sync/companion.test.ts:38:    ['sender envelope is legacy (no sourceMdHash)', envelope(undefined)],
tests/lib/cloud-sync/companion.test.ts:42:    it('DELETES a receiver model whose sourceMdHash provably differs from the winner', () => {
tests/lib/cloud-sync/companion.test.ts:45:    it('KEEPS a receiver model whose sourceMdHash matches the winner (still valid — paid artifact)', () => {
tests/lib/cloud-sync/companion.test.ts:58:    it('KEEPS but still counts a legacy receiver envelope with no sourceMdHash', () => {
tests/lib/cloud-sync/companion.test.ts:73://    envelope carrying a sourceMdHash that differs from the winner's. Everything else keeps.
tests/lib/cloud-sync/companion.test.ts:80:      const senderShips = s.kind === 'envelope' && s.envelope.sourceMdHash === 'h1';
tests/lib/cloud-sync/companion.test.ts:81:      const receiverProvablyStale = r.kind === 'envelope' && r.envelope.sourceMdHash !== undefined
tests/lib/cloud-sync/companion.test.ts:82:        && r.envelope.sourceMdHash !== 'h1';
tests/lib/cloud-sync/model-writer-hash.test.ts:4:// and asserts the persisted model envelope's sourceMdHash is the hash of the MD BODY that was
tests/lib/cloud-sync/model-writer-hash.test.ts:70:it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:81:  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
tests/lib/cloud-sync/model-writer-hash.test.ts:82:  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
tests/lib/cloud-sync/schema.test.ts:29:    sourceMd: 'x', generatedAt: '2026-07-17', sourceSections: ['A'],
tests/lib/cloud-sync/schema.test.ts:32:  it('accepts an optional sourceMdHash', () => {
tests/lib/cloud-sync/schema.test.ts:33:    expect(ModelEnvelopeSchema.parse({ ...env, sourceMdHash: 'deadbeef' }).sourceMdHash).toBe('deadbeef');

codex
The generator-version edge does not produce a destructive sync action, but it can affect the report’s meaning. I’m checking the anonymous share route contract now, because `shareNeedsOwnerServe` is supposed to be user-facing readiness rather than cache provenance only.
exec
/bin/bash -lc 'rg -n "share|readFreshMagazineModel|readTitleStableModel|resolveAndParse|not_ready|not-ready|X-Magazine-Stale|anonymous" app lib/html-doc tests/integration/share-route.test.ts -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/share-route.test.ts:4:import { generateShareToken, hashShareToken } from '@/lib/share/token';
tests/integration/share-route.test.ts:14:    throw new Error('generateMagazineModel must NEVER be called on the anonymous share path');
tests/integration/share-route.test.ts:32:jest.mock('@/lib/share/serve', () => {
tests/integration/share-route.test.ts:33:  const actual = jest.requireActual('@/lib/share/serve');
tests/integration/share-route.test.ts:62:  const { error } = await svc.from('share_tokens').insert({
tests/integration/share-route.test.ts:97:describe('share-route', () => {
tests/integration/share-route.test.ts:120:    // on the share path, regardless of which branch (200/404/503) the request took.
tests/integration/share-route.test.ts:133:    // reserve_serve_model (5a) — since that RPC is never called on the share path (asserted in
tests/integration/share-route.test.ts:134:    // afterEach below), no share owner should have gained/changed a serve_owner_budget row either.
tests/integration/share-route.test.ts:155:    expect(html).not.toContain(`${base}.md`); // B22 — no owner-structure leak on the share doc
tests/integration/share-route.test.ts:158:  it('B7: valid token, model absent (never generated) → 503 not-ready', async () => {
tests/integration/share-route.test.ts:169:  it('B8: valid token, materialized model is STALE (wrong generatorVersion) → 503 not-ready (never 200, never a charge)', async () => {
tests/integration/share-route.test.ts:282:      await svc.from('share_tokens').update({ revoked_at: new Date().toISOString() }).eq('token_hash', hashShareToken(tok));
tests/integration/share-route.test.ts:328:  it('C7: share GET (no format/download), live token → 200 html view regression w/ nosniff, no Content-Disposition', async () => {
tests/integration/share-route.test.ts:373:  it('C9: format=html&download=1, live token, fresh model → 200 html attachment; share-mode strip; never charges', async () => {
tests/integration/share-route.test.ts:389:    expect(html).not.toContain(`${base}.md`); // share-mode strip — no owner-structure/MD-key leak
tests/integration/share-route.test.ts:390:    expect(generateMagazineModel).not.toHaveBeenCalled(); // share html path never generates — freshness only
tests/integration/share-route.test.ts:454:      await svc.from('share_tokens').update({ revoked_at: new Date().toISOString() }).eq('token_hash', hashShareToken(tok));
tests/integration/share-route.test.ts:473:  it('C16: cross-owner isolation — a share_token row claiming owner B for A\'s playlist is now DB-rejected (0019 composite FK); D15 stays as defense-in-depth', async () => {
tests/integration/share-route.test.ts:475:    // directly insertable and caught only by the app-level D15 guard (lib/share/serve.ts) at
tests/integration/share-route.test.ts:476:    // request time. 0019's composite FK share_tokens(playlist_id, owner_id) ->
tests/integration/share-route.test.ts:496:  it('C21: hostile title (quote/CRLF) in a share doc → header not injected on md download', async () => {
lib/html-doc/render.ts:13:// render.ts has `meta` between `ink` and `rule`; spread the shared pre/post around it.
lib/html-doc/render.ts:59:  opts: { nonce?: string; dig?: boolean; share?: boolean } = {},
lib/html-doc/render.ts:63:  const share = opts.share ?? false;
lib/html-doc/render.ts:106:  const footerSource = (!share && sourceMd) ? ` <code>${esc(sourceMd)}</code>` : '';
lib/html-doc/render.ts:113:${share ? '' : `<meta name="generator" content="${GENERATOR_VERSION}">
lib/html-doc/file-response.ts:2:// import guard can scan it and the share route's use of it cannot smuggle in charging code.
lib/html-doc/file-response.ts:47:  if (opts.staleMarker && opts.kind === 'html') headers['X-Magazine-Stale'] = '1';
lib/html-doc/serve-summary-core.ts:27: * (Task 8) can share it while the `format=md` no-charge short-circuit survives (D4 money invariant:
lib/html-doc/serve-summary-core.ts:30: * Mirrors serveCloud lines ~45-83. Does NOT resolve/charge — that is stage 2 (resolveAndParse).
lib/html-doc/serve-summary-core.ts:96:export async function resolveAndParse(
lib/html-doc/nav.ts:542:// Selector uses `a.dig-trigger[data-section]` so the anonymous pre-disabled <span> is inert.
lib/html-doc/read-model.ts:8:// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
lib/html-doc/read-model.ts:9:// /s/[token] route therefore cannot pull in the charging code. Enforced by tests/lib/share/
lib/html-doc/read-model.ts:28: *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call). */
lib/html-doc/read-model.ts:29:export async function readFreshMagazineModel(args: {
lib/html-doc/read-model.ts:34:}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }> {
lib/html-doc/read-model.ts:38:  return { status: 'not_ready' };
lib/html-doc/read-model.ts:44:export async function readTitleStableModel(args: {
lib/html-doc/serve-doc.ts:8:import { readFreshMagazineModel, readTitleStableModel } from './read-model';
lib/html-doc/serve-doc.ts:56:  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:71:      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:78:      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
lib/html-doc/csp.ts:28: * exactly `connect-src 'self'` (same-origin only) and nothing else. The static summary/share docs
lib/html-doc/dig-merge.ts:164:  // raw dug array) so that a sectionId shared by two inputs that both go
app/api/share/[id]/revoke/route.ts:10:  const { data: revoked, error } = await supabase.rpc('revoke_share_token', { p_id: id });
app/api/share/route.ts:3:import { generateShareToken } from '@/lib/share/token';
app/api/share/route.ts:4:import { resolveExpiry } from '@/lib/share/ttl';
app/api/share/route.ts:21:  const { data, error } = await supabase.rpc('create_share_token', {
app/s/[token]/route.ts:4:import { getShareServeContext } from '@/lib/share/serve';
app/s/[token]/route.ts:5:import { readFreshMagazineModel } from '@/lib/html-doc/read-model';
app/s/[token]/route.ts:12:// MONEY GUARD (spec B18b, enforced by tests/lib/share/import-guard.test.ts): this module must not
app/s/[token]/route.ts:18:// valid-but-not-ready token could otherwise outlive the model being materialized, and a cached
app/s/[token]/route.ts:19:// 404 could leak token-existence timing via a shared/browser cache.
app/s/[token]/route.ts:62:    // parseSummaryMarkdown/readFreshMagazineModel — must NOT resolve a model or charge.
app/s/[token]/route.ts:81:  const model = await readFreshMagazineModel({ blobStore: readOnly, principal, base, titles });
app/s/[token]/route.ts:89:  const html = renderMagazineHtml(parsed, model.model, { nonce, dig: false, share: true });
app/api/playlists/[id]/route.ts:16://   4. DB delete (commit point) — cascades videos/jobs/share_tokens via the 0019 FKs
app/api/playlists/[id]/route.ts:73:    // Commit point: DB delete cascades videos/jobs/share_tokens (0019 FKs).
app/api/videos/route.ts:36:      // shared nulls-last tail, not first — uniform with every other column.
app/api/videos/route.ts:44:      // the shared tail); present-but-unrecognized → rank 0 (as before).
app/api/share/revoke-all/route.ts:12:  const { data: count, error } = await supabase.rpc('revoke_all_share_tokens', {
app/api/share/revoke-all/route.ts:15:  if (error) { logError('share:revoke-all', error); return json({ error: 'internal error' }, 500); }
app/api/pdf/[id]/route.ts:5:import { loadSummaryForServe, resolveAndParse } from '@/lib/html-doc/serve-summary-core';
app/api/pdf/[id]/route.ts:48:    const r = await resolveAndParse(supabase, load, request.signal);
app/api/pdf/[id]/route.ts:74:    if (r.stale) headers['X-Magazine-Stale'] = '1';
app/api/html/[id]/route.ts:7:import { loadSummaryForServe, resolveAndParse } from '@/lib/html-doc/serve-summary-core';
app/api/html/[id]/route.ts:53:      // Authoritative anon status = profiles.is_anonymous, read fail-closed — the SAME source and
app/api/html/[id]/route.ts:55:      // user.is_anonymous (not reliably populated here). A null/errored profile ⇒ treat as anonymous.
app/api/html/[id]/route.ts:56:      const { data: profile } = await supabase.from('profiles').select('is_anonymous').eq('id', user.id).single();
app/api/html/[id]/route.ts:60:        cloud: { playlistId, isAnonymous: profile?.is_anonymous !== false },
app/api/html/[id]/route.ts:76:      // D4 money invariant: short-circuits BEFORE resolveAndParse/resolveMagazineModel — must NOT
app/api/html/[id]/route.ts:84:    const r = await resolveAndParse(supabase, load, request.signal);
app/api/html/[id]/route.ts:92:      staleMarker: r.stale === true, // D6: serve-stale-over-budget flags X-Magazine-Stale
app/api/videos/[id]/dig/[sectionId]/route.ts:47:    // Authoritative anon status = profiles.is_anonymous (the SAME column enqueue_job checks at
app/api/videos/[id]/dig/[sectionId]/route.ts:49:    // trust user.is_anonymous — it is not guaranteed to be populated in this project's auth config.
app/api/videos/[id]/dig/[sectionId]/route.ts:50:    // Fail CLOSED: only an explicit is_anonymous===false grants registered access. A null/errored
app/api/videos/[id]/dig/[sectionId]/route.ts:51:    // profile read (RLS denial, missing row, transient error) must be treated as anonymous (→ 403),
app/api/videos/[id]/dig/[sectionId]/route.ts:53:    const { data: profile } = await supabase.from('profiles').select('is_anonymous').eq('id', user.id).single();
app/api/videos/[id]/dig/[sectionId]/route.ts:61:      userId: user.id, isAnonymous: profile?.is_anonymous !== false,

exec
/bin/bash -lc "nl -ba tests/integration/share-route.test.ts | sed -n '130,210p' && rg -n \"shareNeedsOwnerServe|row 7|anon|anonymous|not-ready|not ready\" docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md docs/reviews -S" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   130	    expect(ledgerAfter ?? []).toEqual(ledgerBefore); // byte-identical row sets — no charge ever landed
   131	    expect(chargeAfter ?? []).toEqual(chargeBefore);
   132	    // Stage 1G / G1 Task 2 (P11): the per-owner serve budget is only ever touched by
   133	    // reserve_serve_model (5a) — since that RPC is never called on the share path (asserted in
   134	    // afterEach below), no share owner should have gained/changed a serve_owner_budget row either.
   135	    expect(ownerBudgetAfter ?? []).toEqual(ownerBudgetBefore);
   136	    expect(generateMagazineModel).not.toHaveBeenCalled(); // zero generation calls across the whole block
   137	    rpcSpy.mockRestore();
   138	  });
   139	
   140	  it('B6: valid token + fresh model → 200 html; headers; body has summary, not the MD key', async () => {
   141	    const u = await newUser();
   142	    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
   143	    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
   144	    await seedFreshModel(u.user.id, playlistKey, base);
   145	    const token = await mintDirect(u.user.id, playlistId, videoId);
   146	
   147	    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
   148	    expect(res.status).toBe(200);
   149	    expect(res.headers.get('Content-Type')).toMatch(/text\/html/);
   150	    expect(res.headers.get('Cache-Control')).toBe('no-store');
   151	    expect(res.headers.get('Referrer-Policy')).toBe('no-referrer');
   152	    expect(res.headers.get('Content-Security-Policy')).toMatch(/nonce-/);
   153	    const html = await res.text();
   154	    expect(html).toContain('Intro');
   155	    expect(html).not.toContain(`${base}.md`); // B22 — no owner-structure leak on the share doc
   156	  });
   157	
   158	  it('B7: valid token, model absent (never generated) → 503 not-ready', async () => {
   159	    const u = await newUser();
   160	    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
   161	    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
   162	    // Deliberately no writeModelEnvelope call — model absent.
   163	    const token = await mintDirect(u.user.id, playlistId, videoId);
   164	
   165	    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
   166	    expect(res.status).toBe(503);
   167	  });
   168	
   169	  it('B8: valid token, materialized model is STALE (wrong generatorVersion) → 503 not-ready (never 200, never a charge)', async () => {
   170	    const u = await newUser();
   171	    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
   172	    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
   173	    // Materialize a model envelope that exists but is stale — wrong generatorVersion, so
   174	    // isFresh() (lib/html-doc/read-model.ts) must reject it just like the absent case above.
   175	    const serviceStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
   176	    const principal = { id: u.user.id, indexKey: playlistKey };
   177	    await writeModelEnvelope(
   178	      principal,
   179	      base,
   180	      {
   181	        sourceMd: `${base}.md`,
   182	        generatedAt: new Date().toISOString(),
   183	        sourceSections: ['Intro'],
   184	        generatorVersion: 'stale-vX', // deliberately mismatched — must NOT equal GENERATOR_VERSION
   185	        model: {
   186	          sections: [
   187	            { lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] },
   188	          ],
   189	        },
   190	      },
   191	      serviceStore,
   192	    );
   193	    const token = await mintDirect(u.user.id, playlistId, videoId);
   194	
   195	    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
   196	    expect(res.status).toBe(503);
   197	  });
   198	
   199	  it('B9: expired token → 404 (coarse)', async () => {
   200	    const u = await newUser();
   201	    const { playlistId, videoId } = await seedDoc(u.user.id);
   202	    const token = await mintDirect(u.user.id, playlistId, videoId, {
   203	      expires_at: new Date(Date.now() - 864e5).toISOString(),
   204	    });
   205	
   206	    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
   207	    expect(res.status).toBe(404);
   208	  });
   209	
   210	  it('B10: revoked token → 404 (coarse)', async () => {
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:107:  (anonymous)** view of that specific video is not-ready until the owner serves (the share route is
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:137:### 5.2 Canonical `mdHash` (rounds 1–3, 5)
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:138:`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:318:  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:340:- **R7 — Synced+shared video:** its anonymous share is not-ready until an owner serve (the share route is
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:20:- **No service-role key on the local machine (§6).** The CLI authenticates as the user (Supabase Auth session; anon key + user JWT). All cloud I/O is RLS-scoped to `auth.uid()`. `owner_id` is derived from the session, never client-supplied. This must not trip `scripts/check-service-confinement.ts` (`npm run check:confinement`).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:34:- `lib/cloud-sync/content-hash.ts` — canonical MD-body-only `mdHash` (§5.2).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:59:## Task 1: Canonical MD-body `mdHash`
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:67:- Produces: `mdHash(md: string): string` — SHA-256 hex of the canonicalized MD body. `canonicalizeMd(md: string): string` — the normalization (exported for cross-backend golden tests).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:73:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:75:describe('canonicalizeMd', () => {
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:77:    expect(canonicalizeMd('a\r\nb\rc')).toBe('a\nb\nc\n');
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:80:    expect(canonicalizeMd('body\n\n\n')).toBe('body\n');
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:81:    expect(canonicalizeMd('body')).toBe('body\n');
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:85:    expect(canonicalizeMd('é')).toBe('é\n');
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:117: * Canonical MD-body normalization for cross-backend hashing (§5.2):
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:122:export function canonicalizeMd(md: string): string {
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:128:/** SHA-256 hex of the canonicalized MD body (§5.2). NOT over human fields. */
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:130:  return createHash('sha256').update(canonicalizeMd(md), 'utf8').digest('hex');
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:143:git commit -m "feat(cloud-sync): canonical MD-body mdHash (§5.2)"
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1280:  - `type CompanionAction = { kind: 'ship'; envelope: ModelEnvelope } | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }`
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1301:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1305:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1309:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1326:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1337:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1507:- **Never** uses the service-role key. `getAuthedClient` must construct the client with the **anon** key only.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1601:function anonClient(): SupabaseClient {
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1603:  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1604:  if (!url || !anon) throw new Error('NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY not set');
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1605:  return createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } });
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1666:  const c = anonClient();
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1679:  const c = anonClient();
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1690:  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1691:  return createClient(url, anon, {
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1835:  - `SyncReport = { created; updatedLocal; updatedCloud; skippedIdentical; mergedFields; conflictsLogged; removed; shareNeedsOwnerServe; needsRegen; archivedNotSynced; errors }` (all counters, plus per-video error list).
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1846:| 5 | Companion ship/delete | after a Class-A copy | `decideCompanion`: ship envelope (`cloudBlob/localBlob.put` model) OR delete receiver model blob + `report.shareNeedsOwnerServe++` |
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1938:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1974:- **`companionTransfer(deps, winnerSide, loserSide, winnerMdHash, video): Promise<{ shareNeedsOwnerServe: boolean }>`** (Behavior #5) — read the winner's `ModelEnvelope` (`readModelEnvelope`), call `decideCompanion({ winnerMdHash, senderEnvelope })`; on `ship` write the envelope to the loser's blob; on `deleteReceiverModel` delete the loser's model blob (best-effort, OUTSIDE the atomic commit) and return `shareNeedsOwnerServe:true`.
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1983:    mergedFields: 0, conflictsLogged: 0, removed: 0, shareNeedsOwnerServe: 0, needsRegen: 0,
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2051:          if ((await companionTransfer(/* winner→loser */)).shareNeedsOwnerServe) report.shareNeedsOwnerServe++;
docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2213:| 7 | Synced+shared, model deleted → anon share not-ready until owner serve, counted | `report.shareNeedsOwnerServe >= 1` |
docs/reviews/plan-stage-1b-auth-rls-schema-codex.md:13:- **B1 — Google OAuth E2E deferred, but spec §8 makes it a 1B success criterion.** Spec §§4/8 require "Google and anonymous sign-in both yield a session and profiles row"; the plan defers Google E2E to deploy. → Fix by adding a concrete 1B verification for the Google/OAuth provisioning + callback path, or amend the approved spec to scope real-Google verification to deploy. **[Decision surfaced to user — see resolution.]**
docs/reviews/plan-stage-1b-auth-rls-schema-codex.md:14:- **B2 — Anonymous auth likely fails locally: `signInAnonymously()` requires `config.toml` opt-in.** Plan runs `supabase init` but never enables anonymous sign-ins. Tasks 1/7/9 depend on `anonSession()`. → Fix: set `[auth] enable_anonymous_sign_ins = true` (+ local email-confirm settings) in `supabase/config.toml`; smoke-test `anonSession()` after `db reset`.
docs/reviews/plan-stage-1b-auth-rls-schema-codex.md:18:- **H1 — Anon-allowed auto-provision not implemented.** Spec §4: anon-allowed paths "auto-provision an anonymous session on first use." Task 10 only classifies `/try` and redirects authenticated routes. → Add middleware logic + test that mints an anonymous session on first visit to an anon-allowed route.
docs/reviews/plan-stage-1b-auth-rls-schema-codex.md:29:- **M2 — No negative test that `anon`/`authenticated` cannot execute `exec_sql`.** → Add integration assertions that anon-key and user-JWT clients get permission errors.
docs/reviews/task-1-deps-env-review.md:7:All Task 1 deliverables present: deps (`@supabase/supabase-js`, `@supabase/ssr`, `server-only`), `test:integration` script, `supabase/config.toml` (via `supabase init@2.109.0`), `lib/supabase/env.ts`, `.env.test.local.example`, `tests/lib/supabase/env.test.ts`. `enable_anonymous_sign_ins=true` + `enable_confirmations=false` confirmed. Additive-only respected; no scope creep. `getSupabaseEnv`/`getServiceRoleKey` throw naming the missing var. 4/4 tests green; `tsc --noEmit` clean.
docs/reviews/spec-dig-code-slide-as-image-review.md:46:After the prompt flip, the first assertion must become a RED test (`expect(p()).not.toMatch(/transcribe[^.]*code block/i)` or equivalent). The second may stay green. The spec's Testing table (row 7) says "Update any fixtures/assertions that encoded 'code → fence'", but the wording is vague — it does not name `tests/lib/dig/generate.test.ts:197-198` or the exact rewrite. The plan must name this file and line explicitly to avoid a subtle error: an implementer who runs the suite before touching the test will get a false-red that looks like a real failure, or worse, will mark the old assertion as passing after changing the prompt and not notice the semantic inversion.
docs/reviews/task-4-provisioning-trigger-review.md:1:# Task 4 Review — Provisioning trigger + is_anonymous guard (0003_provisioning.sql)
docs/reviews/task-4-provisioning-trigger-review.md:10:4. **is_anonymous source:** `coalesce(new.is_anonymous, false)` — Google (null)→false, anon→true.
docs/reviews/task-4-provisioning-trigger-review.md:13:7. **Tests:** (a) email signup via `newUser`/`admin.createUser` (same auth.users path as Google) → one row is_anonymous=false; (b) anon → true via real RLS path; (c) `pg_proc.prosecdef` asserts DEFINER; (d) client flip rejected with matching message.
docs/reviews/task-4-provisioning-trigger-review.md:18:- **M1 (FIXED):** `guard_is_anonymous` trigger target `before update on profiles` unqualified → qualified to `public.profiles` for consistency (worked already via default search_path).
docs/reviews/whole-branch-1f-b-codex.md:6:No Blocking or High findings. The anonymous share path is money-path-bounded, service-role-isolated, and I do not see a 1F-a owner-serving regression.
docs/reviews/whole-branch-1f-b-codex.md:18:- [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:35) + [supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:11): a corrupted promoted `artifacts.summaryMd.key` such as `../x.md` will make `assertLogicalKey()` throw during the anonymous blob read, and the share route has no catch around that read. That turns malformed persisted metadata into a 500 instead of the intended coarse denial. It is not a cross-tenant read because the blob store rejects the key before download, but it weakens the “coarse 404 / never 500 for bad promoted source material” story. Fix: validate `mdKey` in `getShareServeContext()` and return `denied` on invalid logical keys, or catch `statusCode === 400` around the share route’s blob reads and return `notFound()`.
docs/reviews/whole-branch-1f-b-codex.md:25:Auth boundary: mint/revoke use `createServerSupabase` session clients and definer RPCs; anonymous serve is the only new direct service-role route. Token hash is consistently lowercase 64-char hex across token helper, migration, RPCs, and route tests.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:28:2. else receiver envelope matching `winnerMdHash` → noop, `shareNeedsOwnerServe: false`
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:29:3. else delete ONLY when the receiver envelope has a `sourceMdHash` that is present (provably stale); everything else (absent / legacy no-hash / unprovable read) → noop with `shareNeedsOwnerServe: true`
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:35:- `shareNeedsOwnerServe` is now carried on `noop`. Confirm it preserves the pre-existing row-7 contract (`tests/integration/cloud-sync/e2e.int.test.ts:236`) and does not now OVER-report — trace how often `noop + true` fires in ordinary syncs (e.g. every video where neither side has a model) and say whether the counter remains meaningful to a user.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:52:Minor known nit, already logged, no need to re-file: a comment in `companion.ts`/`sync-run.ts` cites "§10 row 7" as if it were in the design spec; the numbered row 7 actually lives in the PLAN (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2213`) and its wording is about a deleted model, while the implemented+tested contract is "no matching model".
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:101:    shareNeedsOwnerServe is now carried on `noop` too — it is a separate axis from the blob
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:104:    shareNeedsOwnerServe"); under-reporting is the harmful direction since the flag spends nothing.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:155:+/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:158:+ *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:162:   | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:164:+  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:213:-  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:218:+    return { kind: 'noop', shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:232:+  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:234:+  //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:236:+  //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:239:+  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:240:+  return { kind: 'noop', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:295:   shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:600: ): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:601:   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:612:     return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:615:-  // do NOT report shareNeedsOwnerServe (nothing is known to be stale about the share).
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:616:-  if (decision.kind === 'noop') return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:618:+  // stale: leave the blob alone. The report flag is decided separately (§10 row 7 counts a share
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:620:+  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:623:   return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:708:     shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:767: /** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:952:+    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:958:+    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:989:-    expect(r1.shareNeedsOwnerServe).toBe(0);                    // no false "share is stale" signal
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:995:+    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1001:     expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1038:+    expect(r1.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1042:+    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1206:-    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1210:-    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1211:+const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1212:+/** Keep the receiver's blob. `flag` is the SEPARATE report-only axis (§10 row 7). */
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1213:+const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1228:-    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1250:+      // §10 row 7 — nothing to delete, yet the share cannot render until the owner re-serves. The
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1256:+      // is what strands an anon visitor on a not-ready share.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1278:+    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1303:/bin/bash -lc 'git status --short && rg -n "decideCompanion|readReceiverModel|shareNeedsOwnerServe|ensureReceiverSlot|playlistMetaFor|provablyStale|readIndex|setPlaylistMeta" lib tests docs/superpowers -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1347:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1280:  - `type CompanionAction = { kind: 'ship'; envelope: ModelEnvelope } | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }`
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1351:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1301:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1353:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1305:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1355:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1309:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1356:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1326:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1358:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1337:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1362:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1835:  - `SyncReport = { created; updatedLocal; updatedCloud; skippedIdentical; mergedFields; conflictsLogged; removed; shareNeedsOwnerServe; needsRegen; archivedNotSynced; errors }` (all counters, plus per-video error list).
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1364:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1846:| 5 | Companion ship/delete | after a Class-A copy | `decideCompanion`: ship envelope (`cloudBlob/localBlob.put` model) OR delete receiver model blob + `report.shareNeedsOwnerServe++` |
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1367:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1938:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1375:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1974:- **`companionTransfer(deps, winnerSide, loserSide, winnerMdHash, video): Promise<{ shareNeedsOwnerServe: boolean }>`** (Behavior #5) — read the winner's `ModelEnvelope` (`readModelEnvelope`), call `decideCompanion({ winnerMdHash, senderEnvelope })`; on `ship` write the envelope to the loser's blob; on `deleteReceiverModel` delete the loser's model blob (best-effort, OUTSIDE the atomic commit) and return `shareNeedsOwnerServe:true`.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1376:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1983:    mergedFields: 0, conflictsLogged: 0, removed: 0, shareNeedsOwnerServe: 0, needsRegen: 0,
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1379:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2051:          if ((await companionTransfer(/* winner→loser */)).shareNeedsOwnerServe) report.shareNeedsOwnerServe++;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1381:docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2213:| 7 | Synced+shared, model deleted → anon share not-ready until owner serve, counted | `report.shareNeedsOwnerServe >= 1` |
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1464:docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:359:**Canonical transformation** (apply to each `readIndex`/`writeIndex`/`upsertVideo`/`updateVideoFields` call; leave `assertOutputFolder`/`assertVideoId` imports and calls untouched):
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1468:docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:385:Replace its `upsertVideo`/`readIndex`/`writeIndex` calls per the canonical transform. `pipeline.ts` receives `outputFolder` and already calls `assertOutputFolder` — replace that call with `const principal = getPrincipal(outputFolder)` and thread `principal` + `getMetadataStore()` through the ingestion loop. Keep `assertVideoId` calls as-is.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1471:docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:420:Apply the **canonical transformation from Task 5** to each file's `readIndex`/`writeIndex`/`updateVideoFields` calls. Per-file specifics (imported symbols to reroute, from the consumer map):
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1475:docs/superpowers/plans/2026-07-02-stage-1a-metadata-store-seam.md:453:Apply the **canonical transformation** to each route's `readIndex`/`updateVideoFields` calls. Each route currently does `assertOutputFolder(outputFolder)` (+ `assertVideoId(id)`) then `readIndex(outputFolder)`; convert the `assertOutputFolder` call into `const principal = getPrincipal(outputFolder)`, keep `assertVideoId(id)`, and use `getMetadataStore()` for data access.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1525:docs/superpowers/specs/2026-07-14-cloud-dig-serving-design.md:80:Cloud branch: `?playlist={uuid}` required (UUID-validated) → auth (`getUser`, 401 anon) → `assertVideoId` → owner-assert + gate (reuse the same `resolveOwnedPlaylistKey` + `readIndex` + `base` derivation as the loader; factor the shared prefix out of Unit A so both use it) → list `dig/{base}/` current-version blobs → `{ sectionIds: number[] }` sorted **ascending** by `startSec` (== sectionId). Zero dug → `{ sectionIds: [] }` (**200**, not 404 — lets the frontend distinguish "nothing dug" from an error).
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1549:docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:241:**Context the brief cannot know:** `artifacts` is NOT a typed field on `VideoSchema` — it lives only in the DB `videos.data` jsonb and is read via ad-hoc casts (`app/api/html/[id]/route.ts:55`, `lib/share/serve.ts:44`). The canonical readiness predicate `artifacts.summaryMd.status === 'promoted'` is used at those sites + `lib/job-queue/summary-handler.ts:87`. `BlobStatus` = `'pending' | 'committed' | 'promoted' | 'repair_needed'` (`lib/storage/blob-store.ts:3`). serveLocal (`app/api/videos/route.ts:94-128`) and serveCloud (`:134-176`) are separate functions but share the `Video` type via `sortVideos`; the local store (`LocalMetadataStore.readIndex`) has no `artifacts`, so making the field `.optional()` and deriving it only cloud-side leaves local `undefined` — identical to the `updatedAt` precedent.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1602:tests/lib/cloud-sync/companion.test.ts:13:const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1603:tests/lib/cloud-sync/companion.test.ts:15:const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1604:tests/lib/cloud-sync/companion.test.ts:68:    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1705:docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md:2115:    .metadataStore.readIndex({ id: anonId, indexKey: anonDoc.playlistKey });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1710:tests/integration/html-serve-isolation.test.ts:42:    .metadataStore.readIndex({ id: anonId, indexKey: anonDoc.playlistKey });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1798:lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1821:lib/cloud-sync/sync-run.ts:383:): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1822:lib/cloud-sync/sync-run.ts:384:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1825:lib/cloud-sync/sync-run.ts:394:    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1826:lib/cloud-sync/sync-run.ts:399:  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1827:lib/cloud-sync/sync-run.ts:402:  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1829:lib/cloud-sync/sync-run.ts:480:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1831:lib/cloud-sync/sync-run.ts:626:          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1832:lib/cloud-sync/companion.ts:19:/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1833:lib/cloud-sync/companion.ts:26:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1834:lib/cloud-sync/companion.ts:27:  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1836:lib/cloud-sync/companion.ts:70:    return { kind: 'noop', shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1837:lib/cloud-sync/companion.ts:84:  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1839:lib/cloud-sync/companion.ts:91:  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1840:lib/cloud-sync/companion.ts:92:  return { kind: 'noop', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1861:tests/integration/cloud-sync/e2e.int.test.ts:236:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1862:tests/integration/cloud-sync/e2e.int.test.ts:246:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1866:tests/integration/cloud-sync/e2e.int.test.ts:697:    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1867:tests/integration/cloud-sync/e2e.int.test.ts:703:    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1868:tests/integration/cloud-sync/e2e.int.test.ts:735:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1869:tests/integration/cloud-sync/e2e.int.test.ts:739:    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1870:tests/integration/cloud-sync/e2e.int.test.ts:776:    expect(r1.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1871:tests/integration/cloud-sync/e2e.int.test.ts:780:    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1921:    19	/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1924:    22	 *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1928:    26	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1929:    27	  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1972:    70	    return { kind: 'noop', shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1986:    84	  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1988:    86	  //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1990:    88	  //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1993:    91	  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:1994:    92	  return { kind: 'noop', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2209:   383	): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2210:   384	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2220:   394	    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2223:   397	  // stale: leave the blob alone. The report flag is decided separately (§10 row 7 counts a share
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2225:   399	  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2228:   402	  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2307:   480	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:2453:   626	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:3275:     8	// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:3371:    50	  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:3390:    69	  // IDENTITY COHERENCE (carried from serveCloud): `base` is the canonical, DB-persisted baseName,
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4032:lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4054:lib/cloud-sync/sync-run.ts:480:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4141:/bin/bash -lc 'rg -n "copyToCloud|copyToLocal|shareNeedsOwnerServe|baseline|writeVideoBaseline|manifest|deleteReceiverModel|readModelSide|playlist title|title" tests/lib/cloud-sync tests/integration/cloud-sync -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4159:tests/integration/cloud-sync/e2e.int.test.ts:236:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4161:tests/integration/cloud-sync/e2e.int.test.ts:246:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4191:tests/integration/cloud-sync/e2e.int.test.ts:697:    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4192:tests/integration/cloud-sync/e2e.int.test.ts:703:    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4193:tests/integration/cloud-sync/e2e.int.test.ts:735:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4194:tests/integration/cloud-sync/e2e.int.test.ts:739:    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4195:tests/integration/cloud-sync/e2e.int.test.ts:776:    expect(r1.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4196:tests/integration/cloud-sync/e2e.int.test.ts:780:    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4232:tests/lib/cloud-sync/companion.test.ts:13:const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4233:tests/lib/cloud-sync/companion.test.ts:15:const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4234:tests/lib/cloud-sync/companion.test.ts:68:    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4291:supabase/migrations/0010_cancel_job_rowcount.sql:22:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4303:supabase/migrations/0011_cost_guardrails.sql:25:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4320:supabase/migrations/0012_serve_model_charge.sql:17:grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4324:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4340:supabase/migrations/0013_share_tokens.sql:18:grant select, insert, update, delete on share_tokens to service_role;  -- no anon/authenticated policy
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4361:supabase/migrations/0008_jobs_queue.sql:78:grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4362:supabase/migrations/0008_jobs_queue.sql:92:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4374:supabase/migrations/0006_grants.sql:3:-- the Data API roles (anon, authenticated, service_role) on new public tables. RLS only
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4376:supabase/migrations/0006_grants.sql:16:grant select, insert, update, delete on public.profiles  to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4377:supabase/migrations/0006_grants.sql:17:grant select, insert, update, delete on public.playlists to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4378:supabase/migrations/0006_grants.sql:18:grant select, insert, update, delete on public.videos    to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4380:supabase/migrations/0005_reorder_helper.sql:24:-- Codex H7: not callable by anon/PUBLIC by default; only authenticated + service_role.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4388:supabase/migrations/0014_serve_owner_budget.sql:110:grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4391:supabase/migrations/0020_reservation_release.sql:10:-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4417:     9	-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4418:    10	-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4419:    11	-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4421:    13	  for all to authenticated, anon
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4576:    46	grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:4989:A possible edge worth checking is not just hash freshness but render freshness: `decideCompanion` ships a sender envelope on `sourceMdHash` alone. I’m tracing `resolveMagazineModel` to see whether an old generator version or stale section list affects anonymous readiness and whether that should alter reporting.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5219:tests/integration/share-route.test.ts:169:  it('B8: valid token, materialized model is STALE (wrong generatorVersion) → 503 not-ready (never 200, never a charge)', async () => {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5385:tests/integration/cloud-sync/e2e.int.test.ts:735:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5439:The generator-version edge does not produce a destructive sync action, but it can affect the report’s meaning. I’m checking the anonymous share route contract now, because `shareNeedsOwnerServe` is supposed to be user-facing readiness rather than cache provenance only.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5441:/bin/bash -lc 'rg -n "share|readFreshMagazineModel|readTitleStableModel|resolveAndParse|not_ready|not-ready|X-Magazine-Stale|anonymous" app lib/html-doc tests/integration/share-route.test.ts -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5444:tests/integration/share-route.test.ts:14:    throw new Error('generateMagazineModel must NEVER be called on the anonymous share path');
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5453:tests/integration/share-route.test.ts:158:  it('B7: valid token, model absent (never generated) → 503 not-ready', async () => {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5454:tests/integration/share-route.test.ts:169:  it('B8: valid token, materialized model is STALE (wrong generatorVersion) → 503 not-ready (never 200, never a charge)', async () => {
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5475:lib/html-doc/nav.ts:542:// Selector uses `a.dig-trigger[data-section]` so the anonymous pre-disabled <span> is inert.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5476:lib/html-doc/read-model.ts:8:// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5496:app/s/[token]/route.ts:18:// valid-but-not-ready token could otherwise outlive the model being materialized, and a cached
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5511:app/api/html/[id]/route.ts:53:      // Authoritative anon status = profiles.is_anonymous, read fail-closed — the SAME source and
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5512:app/api/html/[id]/route.ts:55:      // user.is_anonymous (not reliably populated here). A null/errored profile ⇒ treat as anonymous.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5513:app/api/html/[id]/route.ts:56:      const { data: profile } = await supabase.from('profiles').select('is_anonymous').eq('id', user.id).single();
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5514:app/api/html/[id]/route.ts:60:        cloud: { playlistId, isAnonymous: profile?.is_anonymous !== false },
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5518:app/api/videos/[id]/dig/[sectionId]/route.ts:47:    // Authoritative anon status = profiles.is_anonymous (the SAME column enqueue_job checks at
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5519:app/api/videos/[id]/dig/[sectionId]/route.ts:49:    // trust user.is_anonymous — it is not guaranteed to be populated in this project's auth config.
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5520:app/api/videos/[id]/dig/[sectionId]/route.ts:50:    // Fail CLOSED: only an explicit is_anonymous===false grants registered access. A null/errored
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5521:app/api/videos/[id]/dig/[sectionId]/route.ts:51:    // profile read (RLS denial, missing row, transient error) must be treated as anonymous (→ 403),
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5522:app/api/videos/[id]/dig/[sectionId]/route.ts:53:    const { data: profile } = await supabase.from('profiles').select('is_anonymous').eq('id', user.id).single();
docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md:5523:app/api/videos/[id]/dig/[sectionId]/route.ts:61:      userId: user.id, isAnonymous: profile?.is_anonymous !== false,
docs/reviews/stage-1b-auth-rls-schema-spec-codex-rereview.md:12:- **[Blocking] Trigger security context (was B2-partial).** `handle_new_user` must be `SECURITY DEFINER` (owned by a privileged role, `set search_path=''`) or its insert into RLS-protected `profiles` fails / aborts signup. → v3 §4: SECURITY DEFINER, `is_anonymous` from `new.is_anonymous`, failure behavior, both-provider tests.
docs/reviews/spec-2a-claude-v1.md:6:- **B1 — `middleware.ts` already exists (Stage 1F-b), spec says "New".** Real file auto-provisions anon sessions for anon-allowed routes (`middleware.ts:18-22`), redirects unauth `authenticated` routes to `/` not `/login` (`:33-35`), returns JSON 401 for `/api/*` (`:25-31`), matcher not env-guarded (`:40`), unconditionally calls `getSupabaseEnv()` which throws on missing vars (`env.ts`). Spec's "no-op in local mode" is false → local 500s. A naive "redirect app routes to /login" would convert `/api` 401s to 302s and break every fetch. **Fix:** treat middleware as existing-to-extend; enumerate `route-categories.ts` model; add local-mode short-circuit on `STORAGE_BACKEND !== 'supabase'`; preserve anon-provision branch.
docs/reviews/spec-2a-claude-v1.md:25:- **L3** — `/s/*` (share, anon) falls through to `authenticated` in `classifyRoute`; any route-categories edit must not break it.
docs/reviews/task-1f-b-2-migration-review.md:8:- D9/B23: `force` RLS + `service_role`-only DML, no anon/authenticated policy. D7/B5c TTL bound verbatim (+1h grace). D6/B24 hash CHECK on table + RPC; list returns no hash. Grants complete; correctly grants to `authenticated` only (not `anon`) — management is owner-only.
docs/reviews/task-1f-b-2-migration-review.md:24:- Did not run the live integration suite (RED→GREEN evidence in the implementer's report/commit). `signInAs` assumed to yield an anon-key + user-JWT `authenticated` session (required for the RLS tests to be meaningful).
docs/reviews/task-cloud-pdf-11-review.md:6:**Claude — Approved.** Traced every seam to real code: RPC spy is on `SupabaseClient.prototype.rpc` (real prototype method, not re-assignable instance prop) with real Postgres underneath; fresh-model seeding imports the live `GENERATOR_VERSION` + `sourceSections` from the same parser → matches `isFresh` exactly; mutation control entangled with `res.status` (can't pass on a broken reserve); round-trip cache key independently re-derived; owner isolation via real anon-key 2nd session; AsyncLocalStorage threads per-request clients correctly. Minor: H1 test lacked explicit overlap widening.
docs/reviews/whole-branch-summary-section-timestamp-guarantee-review.md:15:- **Medium (Codex): off-prompt literal-`▶` with a wrong `videoId` bypasses canonicalization.** A doc already `sectionStartsComplete` but carrying a model-authored literal `▶` line (the prompt asks for `[[TS]]` tokens, never `▶`, so this is off-contract) with a wrong-video URL keeps that URL. Dig still works (startSec correct from `t=`); cosmetic link issue only. **Accepted** — same class scoped out in the round-4 plan review (narrow-the-claim). The suggested "always canonicalize on hasSegments" fix was weighed in round 4 and declined (churns converged code for a near-impossible input). Deferred; owner: this slice's future maintenance.
docs/reviews/spec-1g-codex-v1.md:6:- **R1/§6 — `create or replace` must restate the full function attributes.** If 0014's replacement omits `security definer set search_path = public`, the RPC reverts to SECURITY INVOKER → writes to force-RLS/no-policy tables (`serve_model_charge`, `spend_ledger`, new `serve_owner_budget`) fail → owner HTML materialization → RPC error → route 500. Grants/ownership DO survive a same-signature replace, but the definer/search_path attributes are part of the definition. Fix: 0014 restates the complete header (`create or replace … returns text language plpgsql security definer set search_path = public as $$…$$`) + restate `revoke all … / grant execute … to authenticated, anon` for auditability. Do NOT `drop function`.
docs/reviews/spec-1f-a-claude-redteam-v2.md:18:### B-1 — The serve-side daily-cap gate is INFEASIBLE on the mandated session/anon client, and the only two fixes are both explicitly foreclosed by the spec (§4.2 "no migration" + D5 "never service-role"). [INTENT/DESIGN + CORRECTNESS]
docs/reviews/spec-1f-a-claude-redteam-v2.md:20:**Claim attacked:** D5 ("session/anon-scoped client; **never service-role**"), D10 / §4.1 step 5 / §4.2
docs/reviews/spec-1f-a-claude-redteam-v2.md:34:`spend_ledger` and `guardrail_config` have **RLS forced** and **NO policy for `authenticated`/`anon`** —
docs/reviews/spec-1f-a-claude-redteam-v2.md:39:**Therefore, on the serve path with a session/anon client (D5):**
docs/reviews/spec-1f-a-claude-redteam-v2.md:50:  service-confinement gate that B20 exists to test. A `service_role` key on a public GET route (anon-
docs/reviews/spec-1f-a-claude-redteam-v2.md:53:  `authenticated, anon`, that internally checks+reserves against `spend_ledger` while *called by the
docs/reviews/spec-1f-a-claude-redteam-v2.md:63:(check + atomic reserve, see H-2), grant it to `authenticated, anon`, and **retract §4.2's "no migration"**
docs/reviews/spec-1f-a-claude-redteam-v2.md:96:   (velocity is enqueue-only, `enqueue_preflight`), a single anon owner can reload a stuck/failing doc
docs/reviews/spec-1f-a-claude-redteam-v2.md:107:only materialize your own quota-bounded docs (2 for anon, 20 registered)" bound holds only if each doc
docs/reviews/spec-1f-a-claude-redteam-v2.md:223:a session client — `storage.objects` policy `artifacts_owner_rw` is `for all to authenticated, anon` with
docs/reviews/spec-1f-a-claude-redteam-v2.md:237:  owner; a foreign/absent `playlistId` yields no row ⇒ identical 404 (no existence leak, B10); the anon
docs/reviews/spec-1f-a-claude-redteam-v2.md:238:  *session* uid is a real `auth.uid()`, so the `anon` storage policy isolates it identically (B9). This is
docs/reviews/spec-1f-a-claude-redteam-v2.md:270:1. **Resolve B-1:** specify a `SECURITY DEFINER` serve-reservation RPC granted to `authenticated, anon`
docs/reviews/plan-stage-1d-claude-v2.md:6:B1 drop-correct-signature (exact 0009 `enqueue_job(uuid,text,int,text,text,jsonb)` match; create-order safe; both 6-arg & 8-arg client calls tested denied); helper signatures; `anonSession→is_anonymous=true` (via `0003 handle_new_user` `coalesce(is_anonymous,false)`); beforeEach/getGuardrailConfig/SupabaseJobQueue.enqueue-removal/jobs_velocity/failed-formula/schema-policies/§8-cases/`p_*`/`mapEnqueueError`; T12 independent recompute (~115¢, `150 ≥ 115`); disjoint-sum holds; `liveBroadcastContent` source = `videos.list` (correct).
docs/reviews/plan-stage-1d-claude-v2.md:11:- **H3 — T3 `admitted` inverts the spec ceiling.** Plan applied `max_free_users` to anon + admitted all registered; spec §5/parent = ceiling on **registered**. *Fix: `admitted = is_anonymous OR registered_rank ≤ max_free_users` + a test.*
docs/reviews/whole-branch-1f-a.md:13:- **Auth boundary:** service_role off the serve path — `createServerSupabase` uses the anon key, route builds the bundle from that session client (B20 test throws otherwise), `check:confinement` confirms the route never imports `service.ts`; the only elevated surface is the `SECURITY DEFINER` reserve RPC (owner from `auth.uid()` internally, re-verifies owned+`promoted` before money). Owner isolation via RLS + explicit playlist-row owner assert; UUID→400 before any DB call.
docs/reviews/whole-branch-1f-a.md:30:L1 registered-residual bound (per-owner serve budget / anon-account controls); L3 staging-blob GC; T8 quota mutators canonical restore; T4-a/T4-b/T6/T7-a nice-to-have test strengthening.
docs/reviews/task-5-client-factories-review.md:7:Three factories present: `client.ts` (browser/anon), `server.ts` (RLS-scoped, cookie-bound, never service_role), `service.ts` (`import 'server-only'` literal line 1 + runtime `window` guard + missing-key guard). Additive-only, no scope creep (no middleware/routes/migrations). Full suite 1493/1493; `tsc --noEmit` clean. Deferred Minor from Task 1 closed: `getServiceRoleKey` positive test added.
docs/reviews/task-5-client-factories-review.md:10:1. **`getServiceRoleKey()` reordered before `getSupabaseEnv()` in `service.ts`** — correct: the missing-key guard test sets URL but not anon key, so the original order would throw about the wrong var. Both runtime guards (window defined; key absent) verified passing.
docs/reviews/spec-stage-1d-codex.md:6:- **B1 — Preflight gates bypassable by direct `enqueue_job`.** `enqueue_job` is granted to `anon`/`authenticated`, so a caller invokes it directly (or churns anon accounts), skipping `enqueue_preflight` → no hard per-IP velocity / `max_free_users` / queue-depth / CAPTCHA signal; only quota + daily-cap (which are in `enqueue_job`) apply. Per-IP velocity can't work in a client-callable RPC (client controls `p_enqueue_ip`). *Fix: move hard gates into `enqueue_job`, or revoke client execute and enqueue only via a trusted server path.* (Money is still bounded by the daily cap in `enqueue_job`; this is a fairness/availability + defense-in-depth hole.)
docs/reviews/spec-1g-claude-v1.md:8:- **H2 (= Codex Blocking) — `create or replace` risk is SECURITY DEFINER + search_path, not grants.** Grants/ownership survive a same-signature replace; the killer is omitting `security definer`/`set search_path` → SECURITY INVOKER → force-RLS blocks the service_role-only writes → every serve breaks. Fix: mandate the full header verbatim + a test asserting `pg_proc.prosecdef=true`, `proconfig` has `search_path=public`, anon/authenticated can execute.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:131:(`companionTransfer` additionally deleted the receiver's model envelope, `shareNeedsOwnerServe: 1`).
docs/reviews/task-1f-a-7-serve-route.md:15:- **B20 confinement REAL:** route imports only session/anon-scoped helpers; `reachesService(route)===false`; NOT in `ALLOWED_SERVICE_IMPORTERS`; `check:confinement` → "service_role confinement OK"; the route test's `getStorageBundle` mock throws on a bare (service-role) call and asserts the exact `createServerSupabase` return was passed.
docs/reviews/task-1f-a-7-serve-route.md:18:- **Owner isolation (B9/B10):** RLS + explicit `owner_id===auth.uid()` assert; integration `html-serve-isolation` 2/2 on real DB (own registered+anon 200; foreign 404 both directions).
docs/reviews/plan-cloud-pdf-claude-v3-rereview.md:40:- **`loadSummaryForServe` gate strings vs route.ts (T7 characterization surface):** committed → 503 `not ready, retry` (plan 499 = route.ts:57 ✅); not-promoted / absent / missing-mdKey → 404 `not found` (plan 500,502 = route.ts:58,64 ✅); lost md blob → 409 `repair needed` (plan 505 = route.ts:66 ✅, pinned only by status at html-download C6 :227). No drift. html-serve-cloud asserts these purely by status (91/95/99) — all satisfied.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:140:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:901: ): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:902:   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:908:     return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:912:   return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:974:     shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1091:           if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1370:    48	  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1669:   347	): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1670:   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1676:   354	    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1680:   358	  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1742:   420	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1855:   533	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1889:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2015:lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2044:lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2150:app/api/videos/[id]/dig/[sectionId]/route.ts:47:    // Authoritative anon status = profiles.is_anonymous (the SAME column enqueue_job checks at
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2350:    34	/** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2530:   214	  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2531:   215	  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2541:   225	    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3714:138:`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3842:lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3849:lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4480:tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4788:      at Object.<anonymous> (tests/integration/cloud-sync/e2e.int.test.ts:452:41)
docs/reviews/whole-branch-stage-1e-b-v3-rereview.md:22:This is the canonical `base || existing-wins || re-apply-owned-subset` form. Verified against all cases: first-time (metadata+summary from payload), re-persist with concurrent metadata change (all non-summary preserved, summary updated), status-only (existing summary preserved), keyed persist (summary updated).
docs/reviews/task-5-gemini-client-review.md:44:*Fix:* Added `overallScore: number` to `GeminiSummaryResponse` in `types/index.ts`; `SummaryResult` interface removed, `GeminiSummaryResponse` used as the canonical return type.
docs/reviews/playlist-ux-plan-claude-review.md:29:  authenticated, anon using (split_part(name,'/',1)=auth.uid())` (`0007:12-15`), so a session-client
docs/reviews/reservation-release-spec-v1-codex.md:98:    46	grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/reservation-release-spec-v1-codex.md:251:    39	grant select, insert on public.jobs to anon, authenticated;
docs/reviews/reservation-release-spec-v1-codex.md:290:    78	grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/reservation-release-spec-v1-codex.md:304:    92	grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/reservation-release-spec-v1-codex.md:510:   108	- New RPC **`release_serve_model(p_playlist_id uuid, p_video_id text)`** (SECURITY DEFINER, `auth.uid()`-derived owner, mirroring `reserve_serve_model`'s definer/search_path attributes verbatim; grants: `authenticated, anon`). It credits back **one** `magazine_est_cents` bounded by the marker:
docs/reviews/reservation-release-spec-v1-codex.md:603:    14	  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/reservation-release-spec-v1-codex.md:639:    50	      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/reservation-release-spec-v1-codex.md:640:    51	      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/reservation-release-spec-v1-codex.md:675:    86	revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/reservation-release-spec-v1-codex.md:689:     9	grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/reservation-release-spec-v1-codex.md:700:    20	create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/reservation-release-spec-v1-codex.md:701:    21	  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/reservation-release-spec-v1-codex.md:705:    25	grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/reservation-release-spec-v1-codex.md:727:    47	-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/reservation-release-spec-v1-codex.md:736:    56	revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/reservation-release-spec-v1-codex.md:745:    65	  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/reservation-release-spec-v1-codex.md:781:   101	      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/reservation-release-spec-v1-codex.md:782:   102	      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/reservation-release-spec-v1-codex.md:817:   137	revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/reservation-release-spec-v1-codex.md:832:   152	  v_anon boolean; v_owner_created timestamptz;
docs/reviews/reservation-release-spec-v1-codex.md:841:   161	  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/reservation-release-spec-v1-codex.md:842:   162	  if v_anon is null then raise exception 'unknown owner'; end if;
docs/reviews/reservation-release-spec-v1-codex.md:849:   169	  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
docs/reviews/reservation-release-spec-v1-codex.md:852:   172	  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
docs/reviews/reservation-release-spec-v1-codex.md:853:   173	  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
docs/reviews/reservation-release-spec-v1-codex.md:855:   175	  if v_anon then
docs/reviews/reservation-release-spec-v1-codex.md:859:   179	      where p2.is_anonymous = false
docs/reviews/reservation-release-spec-v1-codex.md:875:   195	revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/reservation-release-spec-v1-codex.md:902:    22	grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/reservation-release-spec-v1-codex.md:923:    17	grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
docs/reviews/reservation-release-spec-v1-codex.md:1006:   100	grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;  -- owner derived internally
docs/reviews/reservation-release-spec-v1-codex.md:1109:    99	grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;
docs/reviews/reservation-release-spec-v1-codex.md:1120:   110	grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
docs/reviews/reservation-release-spec-v1-codex.md:1386:supabase/migrations/0012_serve_model_charge.sql:17:grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
docs/reviews/spec-1f-a-claude-v4.md:56:### M-2 — Marker table `serve_model_charge` grant/RLS lockdown is not stated; because the reserve RPC is granted to `anon, authenticated`, a client-writable marker table would allow pre-seeding a *foreign* owner's `(owner,doc,day)` marker → that owner's doc returns `already_charged` → 503, a cross-tenant availability brick — CORRECTNESS · **NEW table in v4** · v3-traceback: none (new surface)
docs/reviews/spec-1f-a-claude-v4.md:58:**Where:** §4.2 ("a marker table `serve_model_charge(owner_id, doc_key, day)` … the RPC owns it; never owner-writable jsonb"). The spec says the RPC owns it but does not state the table's grants/RLS the way 0011 does for `spend_ledger` (`grant … to service_role` only, `enable/force row level security`, **no** anon/authenticated grant — 0011:17–18). "never owner-writable jsonb" rules out the *old* jsonb-marker idea but does not pin the new table's grants.
docs/reviews/spec-1f-a-claude-v4.md:60:**Scenario:** if the migration grants `insert` on `serve_model_charge` to `authenticated`/`anon` (or forgets to force RLS), a client `INSERT`s a marker with a *victim's* `owner_id` and a real `doc_key`. The victim's next view → `already_charged` → model absent → 503 "generating" for the rest of the day. Cross-tenant DoS, no cost to the attacker.
docs/reviews/spec-1f-a-claude-v4.md:64:**Fix:** State in §4.2 that `serve_model_charge` has RLS enabled+forced, **no** `insert/update/delete` grant to `anon/authenticated` (writes only via the `SECURITY DEFINER` RPC), mirroring `spend_ledger`. Add a confinement test: a direct client `INSERT`/`UPDATE`/`DELETE` on `serve_model_charge` is rejected.
docs/reviews/spec-1f-a-claude-v4.md:82:### L-3 — `reserve_serve_model`'s tri-state result lets any anon caller probe global daily-spend state (`at_capacity` leaks "day is over budget") — CORRECTNESS/nit · v3-traceback: Claude-v3 L-3, unchanged
docs/reviews/task-2b-10-integration-review.md:6:Two real users; B reads via B's session client (anon key + user JWT, NOT service_role) through `SupabaseJobQueue.listByPlaylist` → real Postgres RLS path. Positive control (`ca` sees total≥1) guards against a false-negative from a broken seed. If RLS were dropped, B's query returns A's row (total=1≠0) → test fails. Service_role only seeds. Same mechanism as the accepted sibling `jobs-producer-polling` RLS test.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:92:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:380:): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:381:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:387:    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:391:  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:453:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:555:          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:701:lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:725:lib/cloud-sync/sync-run.ts:404:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1497:   331	): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1498:   332	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1504:   338	    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1508:   342	  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1570:   404	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1672:   506	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/plan-summary-section-timestamp-guarantee-v3-rereview.md:18:→ **v4 fix:** finalizer canonicalizes every section's line to `timestampLine(starts[idx], endFor(idx), videoId)` where `endFor = starts[idx+1]` (or `max(videoDuration, starts[idx]+1)` for last); keep only byte-identical lines (still a no-op for good docs). `sectionStartsComplete` also checks `endSec > startSec`. Test fixtures use real `timestampLine` labels.
docs/reviews/plan-summary-section-timestamp-guarantee-v3-rereview.md:29:Round 3: 0 Blocking, 1 High (endSec) + minor. The endSec fix is contained (finalizer end-canonicalization). → v4, then a focused round-4 re-review scoped to the endSec canonicalization + allocator minimal-bump.
docs/reviews/whole-branch-stage-1b-review.md:8:- **B1 — missing table GRANTs (the central cross-file gap).** Migrations create `profiles`/`playlists`/`videos` with forced RLS + owner policies but issue **zero** table-level GRANTs. The pinned CLI (2.109.0) default `auto_expose_new_tables` is unset → new `public` tables are NOT exposed to the Data API roles without explicit grants. RLS only *filters* rows a role already has base access to; without the GRANT, a user-JWT request returns `42501 permission denied`, not `data: []`. **The entire user-JWT integration suite would be red on first run** — the deferral was masking a real failure. (Ironically `exec-sql-guard.test.ts` correctly expects permission-denied; the core-table tests assume success — same mechanism, opposite expected outcomes.) → **RESOLVED**: `0006_grants.sql` grants CRUD to `anon, authenticated` (RLS still confines to `owner_id = auth.uid()`); GRANT is idempotent so it's safe even if a local image ships the legacy auto-grant seed.
docs/reviews/whole-branch-stage-1b-review.md:12:- **H2** — the anon guest `/try` write path (1C) needs the grant too; 0006 grants `anon` so 1C doesn't reopen the convention. Spec §5.4 updated to make the grant part of the reusable convention.
docs/reviews/whole-branch-stage-1b-review.md:20:- L1 policy-presence hard-codes 3 rows (fine for 1B); L2 middleware anon-provision returns before re-reading user (behaviorally fine); L3 empty-read parity constrains 1C `readIndex` (correctly deferred, target shape verified in `lib/index-store.ts`).
docs/reviews/whole-branch-stage-1b-review.md:26:- **Spec §8:** met or explicitly+correctly deferred (Google live redirect; async MetadataStore 1C prereq; anon-TTL + exec_sql pre-public gates). Only silently-unmet item was M1 (now fixed).
docs/reviews/whole-branch-stage-1b-review.md:32:3. Spec §10 pre-public gates: anon-TTL + `exec_sql` removal + Google live redirect (M2).
docs/reviews/whole-branch-stage-1b-review.md:43:2. **service_role grant gap (same class as B1)** — the no-auto-expose default withholds grants from **all three** Data API roles; the review's B1 fix granted only `anon`+`authenticated`. `service_role` has BYPASSRLS but that does **not** bypass table GRANTs, so the admin client got permission-denied on `profiles`. `0006_grants.sql` now grants `service_role` too. (Confinement is enforced by `service.ts` + the scan, not by withholding DB grants.)
docs/reviews/whole-branch-stage-1b-review.md:47:**Verdict: READY TO MERGE — integration green confirmed on a real stack.** Remaining items are the documented pre-public gates (spec §10: drop `exec_sql`, anon TTL) and the 1C prerequisite (async-ify `MetadataStore`).
docs/reviews/task-1f-b-7-serve-route-review.md:1:# Claude Task Review — 1F-b Task 7 (anon /s/[token] route + money proof + guards)
docs/reviews/task-1f-b-7-serve-route-review.md:15:Traced all 9 paths (valid/expired/revoked/unknown/malformed/not-ready/MD-missing/corrupt/in-flight-revoke): none reach a charging RPC/generator. Route imports no serve-doc/gemini/gemini-cost; getShareServeContext is select-only; readFreshMagazineModel = one blob read + pure isFresh. Spy is real: `rpc` on `SupabaseClient.prototype`, `createServiceClient()` returns an instance inheriting it → the spy intercepts the route's own client. `afterEach` asserts no `reserve_serve_model` after every case; `afterAll` byte-compares full ledger row sets + asserts zero `generateMagazineModel`. Three legs (runtime spy + static grep B18b + graph-walk B18c).
docs/reviews/task-1f-b-7-serve-route-review.md:24:- Denial/notReady responses omit `no-store`/Referrer-Policy — a cached 503 not-ready could outlive materialization. Low-risk (owner route same), hardened.
docs/reviews/plan-stage-1e-a-codex.md:8:1. **Producer can bypass the lifecycle via direct table writes.** Owner RLS + `grant update,delete … to authenticated` lets a user `.from('jobs').update({status:'completed', result:{fake}})` — faking completion without the worker, and tampering `attempts`/`lease_token`. **Fix:** grant only `select,insert` to anon/authenticated; `update,delete` to `service_role` only; make `request_cancel_job` `security definer` with an explicit owner check.
docs/reviews/plan-stage-1e-a-codex.md:18:1. **`owner_id` omits `references profiles(id)`** (spec §4). **Fix:** restore FK unless orphan jobs are explicitly wanted. [Resolved: anon HAS a profiles row via the 0003 trigger → FK restored.]
docs/reviews/plan-stage-1e-a-claude-review.md:19:4. **`owner_id` FK to `profiles` silently dropped** (spec §4; anchors 1D quota FK) and not listed in Deviations. **Fix:** restore or explicitly justify. [Resolved: FK restored — anon has a profiles row.]
docs/reviews/plan-stage-1e-a-claude-review.md:29:- `anonSession()` → real principal, role `authenticated`, non-null `auth.uid()` → passes the enqueue guard/grant/with-check.
docs/reviews/whole-branch-cloud-sync-v5-rereview-claude.md:14:`sender.blob.provesAbsence`, and `sync-run.ts:378` returns `shareNeedsOwnerServe: false` on noop.
docs/reviews/spec-1f-a-claude-verify-v2.md:12:**Headline verdict:** The pivot genuinely dissolves the v1 backfill / heal / coupling / recompute Blocker-cluster — that part is sound and well-reasoned. But it **relocated the money-path onto a session/anon client that has no authority to touch the daily-cap ledger**, and the spec never adds the DB surface that relocation requires. So the daily-cap gate (D10 / §4.2 / B6 / Success-Criterion 3) is **not implementable as written** — a new Blocker the pivot introduced. The single genuinely-good-news feasibility answer: the session/anon client *can* write+promote its own model blob (storage RLS allows it), so the lazy-materialize persistence itself is sound.
docs/reviews/spec-1f-a-claude-verify-v2.md:20:| 1 | Can the session/anon client WRITE + promote the model blob? | **PASS** | `0007` policy `artifacts_owner_rw` is `for all to authenticated, anon using/with check (split_part(name,'/',1) = auth.uid()::text)`. Blob key is `{owner_id}/{playlist_key}/…` with `owner_id = auth.uid()`, so INSERT/UPDATE/DELETE + `move` (promote) all satisfy the owner-prefix check. Anon has a real `auth.uid()`. The persistence half of the lazy design works. |
docs/reviews/spec-1f-a-claude-verify-v2.md:21:| 2 | Can the session client reserve against the daily cap? | **FAIL → Blocking (B-1)** | `spend_ledger` grants only `service_role`, `force row level security`, **no owner policy** → owner role denied all access. The only writer/reader are `enqueue_job` / `enqueue_preflight`, both `security invoker`, both gated `if auth.role() <> 'service_role' then raise`, both granted service_role-only. **No SECURITY DEFINER RPC callable by authenticated/anon touches `spend_ledger` or `guardrail_config`.** |
docs/reviews/spec-1f-a-claude-verify-v2.md:30:### B-1 — The daily-cap reservation (D10 / §4.2 / B6) is NOT implementable by the session/anon serve client; D5 (no service_role) and D10 (reserve against the daily cap) are mutually unsatisfiable with the current DB surface — CORRECTNESS (feasibility) · **NEW, introduced by the pivot**
docs/reviews/spec-1f-a-claude-verify-v2.md:34:The v1 money-path lived on the **enqueue/worker path**, where a `service_role` client already exists and `enqueue_job` (service_role-only, security-invoker) does the atomic daily-cap reserve. The pivot **moves the paid call to the serve path** and simultaneously mandates (D5) that the serve path use a **session/anon client, never service_role**. But the daily-cap machinery is reachable *only* by service_role:
docs/reviews/spec-1f-a-claude-verify-v2.md:36:1. `spend_ledger`: `grant select, insert, update, delete … to service_role` and **nothing to anon/authenticated**; `enable` + `force row level security` with **no owner policy** ⇒ the owner/anon role can neither read nor write it. A session-client `update spend_ledger …` returns zero rows / permission-denied.
docs/reviews/spec-1f-a-claude-verify-v2.md:37:2. `enqueue_job` (the existing reserve logic, `0011:111-115`): `language plpgsql security invoker`, first statement `if auth.role() <> 'service_role' then raise 'server only'`, and `grant execute … to service_role` only (explicitly `revoke … from anon, authenticated`). A session client calling it raises.
docs/reviews/spec-1f-a-claude-verify-v2.md:41:So **every** primitive D10 depends on — read the cap, read the fixed estimate, atomically reserve — is closed to the session/anon client. §4.2's "reserve a fixed approximate per-model estimate against the daily cap (`spend_ledger`)" and B6's "day over budget → 503; no Gemini call" describe an operation the serve principal **has no grant to perform**. As written, the money kill-switch on the serve path either does nothing (silently skipped) or 500s — and if it's silently skipped, the paid Gemini call runs **ungated by any daily cap**, which is precisely the invariant Stage 1D exists to guarantee.
docs/reviews/spec-1f-a-claude-verify-v2.md:43:The spec does not acknowledge that a **new SECURITY DEFINER RPC** (callable by `authenticated, anon`, running as definer to bypass RLS on `spend_ledger`/`guardrail_config`, doing check-and-reserve atomically) is *required* to make D10 real. §4.2 even asserts "the Stage 1D … guard are UNCHANGED … no migration," which is false: a serve-side reservation needs new DB surface (a migration + a new RPC + its GRANT). This is the load-bearing dependency of the whole lazy money-path and it is missing.
docs/reviews/spec-1f-a-claude-verify-v2.md:45:**Fix (needs a decision + design):** Add an explicit `reserve_serve_spend(p_est_cents int)` (or similar) SECURITY DEFINER RPC that (a) reads `guardrail_config` for the cap, (b) does the same atomic `insert … on conflict do nothing` + guarded `update spend_ledger set reserved = reserved + est where reserved+actual+est <= cap` as `enqueue_job:111-115`, (c) is granted to `authenticated, anon`, (d) returns admitted/at-capacity. State the migration. Then **re-review it under the money-path trigger** — because handing owner-role clients a lever on the *global* ledger is itself a new attack surface (see H-1). Until this exists, B6 is untestable and Success-Criterion 3 ("the daily-cap gate refuses model generation when the day is over budget") cannot hold.
docs/reviews/spec-1f-a-claude-verify-v2.md:51:### H-1 — The obvious fix for B-1 (an owner/anon-callable reserve RPC) is a new money-path attack surface: any client can drive the GLOBAL daily-cap ledger → cheap DoS on the kill-switch; the spec neither designs nor guards it — INTENT/DESIGN · **NEW**
docs/reviews/spec-1f-a-claude-verify-v2.md:55:Once a `reserve_serve_spend`-style RPC is granted to `authenticated, anon`, **every serve request** can move `spend_ledger.reserved_cents`, which is the *global, all-owners* dollar kill-switch. Combined with D10's explicit **"no per-account quota debit"** on the serve path, there is **no per-owner bound** on how many reservations one principal can drive. Attack: an owner (or anon-churned uids) hammers `GET /api/html/{their-own-doc}` with cache-busting so the model keeps re-materializing (or targets docs whose model is absent/drift), each request reserving the fixed estimate, quickly exhausting the day's `daily_cap_cents` → **every other owner's serve materialization 503s "at capacity."** The serve reservation, like 1D's, is **never released and never reconciled**, so even *failed* materializations permanently inflate `reserved_cents` toward the cap. This is a denial-of-service on the money kill-switch itself, reachable by unprivileged clients — a materially different threat model than 1D's enqueue path (which is service_role-mediated *and* per-account quota-debited).
docs/reviews/spec-1f-a-claude-verify-v2.md:137:The pivot is the right call and genuinely closes the v1 Blocker-cluster. But it introduced **one new Blocker (B-1): the daily-cap money-gate cannot be enforced by the session/anon serve client** — `spend_ledger`, `enqueue_job`, `enqueue_preflight`, and `guardrail_config` are all service_role-only, and the spec adds no owner-callable reserve RPC while D5 forbids service_role. Fixing it requires new DB surface (a SECURITY DEFINER reserve RPC + migration), which then needs its own money-path re-review (H-1: owner-driven global-ledger DoS). Two more genuine gaps the pivot glossed: model-store helpers are local-principal-bound and non-staged (H-2), and MD-blob repair-needed behind a promoted status 500s (M-1). Do **not** treat convergence as reached: B-1 is a fresh Blocking, so another dual round is mandatory per dev-process.
docs/reviews/spec-stage-1e-b-claude-review.md:21:3. **M3 — Existing 1E-a enqueue tests FK-violate; fixture change broader than stated.** Every enqueue test (`job-queue-producer/worker/store/runner/rls`) uses `randomUUID()` video, no playlist. Composite FK forces a real per-owner playlists row seeded into each fixture; anon guest enqueue now needs an anon-owned playlists row.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:185:     shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:317:           if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:621:lib/cloud-sync/companion.ts:5:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:623:lib/cloud-sync/companion.ts:16:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:693:docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:318:  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:822:tests/lib/cloud-sync/companion.test.ts:15:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:824:tests/lib/cloud-sync/companion.test.ts:19:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:826:tests/lib/cloud-sync/companion.test.ts:23:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:852:lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:907:lib/cloud-sync/sync-run.ts:348:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:918:lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1781:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:907:lib/cloud-sync/sync-run.ts:348:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1999:docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:902:   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:2094:docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1670:   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:2489:docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:381:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:2663:docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1498:   332	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:2797:docs/reviews/whole-branch-cloud-sync-codex.md:27:2. **mdHash is MD-BODY-only and CONSISTENT across tasks.** T1 canonicalizes (LF + one trailing newline + NFC). T4 stamps `sourceMdHash = mdHash(body)` at generate.ts + serve-doc.ts. T5 `deriveClassASignals` hashes the mdBody param. T8 `decideCompanion` compares `sourceMdHash === winnerMdHash`. T12 hashes bodies read via BlobStore. Verify NO path hashes `video.summaryMd` (the KEY/filename) instead of the body — a single key-hash anywhere breaks companion/reconcile equality.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:2835:docs/reviews/whole-branch-cloud-sync-codex.md:206:scripts/fix-duplicate-summaries.ts:9: *   2. Update index entry: summaryMd → canonical name
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3100:docs/reviews/whole-branch-cloud-sync-codex.md:1421:lib/cloud-sync/sync-run.ts:301:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3408:docs/reviews/whole-branch-cloud-sync-codex.md:2735:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3450:docs/reviews/whole-branch-cloud-sync-codex.md:3377:  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3549:docs/reviews/whole-branch-cloud-sync-codex.md:5778:   301	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3601:docs/reviews/whole-branch-cloud-sync-codex.md:6764:/bin/bash -lc 'rg -n "copyAdditiveVideo|missing.*blob|shareNeedsOwnerServe|deleteReceiverModel|companion|promoted.*blob|summaryMd.*null|baseline" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3698:    48	  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3997:   347	): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3998:   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4004:   354	    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4008:   358	  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4070:   420	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4202:   552	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4239:     5	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4250:    16	  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:5488:    46	grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:5623:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:5709:lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:5724:lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:5833:    34	/** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:6013:   214	  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:6014:   215	  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:6024:   225	    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:6660:    41	  /** RLS-scoped client (anon key + user JWT) — the ONLY client the code-under-test uses. */
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:7316:tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:7611:docs/reviews/whole-branch-cloud-sync-codex.md:3377:  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:7781:tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
docs/reviews/task-cloud-dig-5-review.md:24:- (Codex Low) anon test asserts `preflight` AND `enqueue` untouched — the 403 must precede ALL service-role work, not just the tenant read.
docs/reviews/plan-stage-1d-codex-v2.md:6:- **New-RPC grants omit explicit revocation.** T2/T3 only `grant execute to service_role`; repo precedent (`0009:45`, `0010:21`) does `revoke all … from public` first. Incomplete "service-role-only" fix; can false-green "any error" tests. *Fix (v3): `revoke all on function … from public, anon, authenticated;` + tests assert `42501`.*
docs/reviews/spec-2a-v2-rereview.md:18:- **N-Codex — `/s/*` regression wording contradiction.** §12 required anon `/s/*` "still reachable" but §2/§14 freeze its (authenticated) classification. **Fix (v3):** §12 now tests only that the `/login` `PUBLIC_EXACT` edit does not change `/s`/`/try` classification; `/s` gating explicitly out of scope.
docs/reviews/spec-2a-v2-rereview.md:22:- **N5 (Claude)** — anon session satisfies the cloud `/` gate (empty library, no leak). Documented §3.2 rule 3.
docs/reviews/plan-stage-1d-codex.md:15:- **H5 (T2)** — omits required §8 cases: UTC-month rollover, same-owner parallel distinct-video quota race, anon vs registered allowance, swept expired lease at `attempts=1` → `dead_letter`. *Fix: add them.*
docs/reviews/task-2a-7-annotation-rpc-review.md:9:- **`revoke all from public` + `grant execute to authenticated`** with exact signature (`0016:23-24`) — anon cannot execute; stricter than `merge_video_data` (no `service_role`).
docs/reviews/reservation-release-spec-v1-claude.md:19:**Where:** spec §6, lines 108 (`grants: authenticated, anon`) and 128 (caller calls
docs/reviews/reservation-release-spec-v1-claude.md:24:session credentials and MUST be granted `authenticated/anon` — which means PostgREST
docs/reviews/reservation-release-spec-v1-claude.md:55:  anon/authenticated). This closes the hole with a one-line grant change but requires
docs/reviews/reservation-release-spec-v1-claude.md:62:  vector before this is mergeable. Currently §6 grants anon/authenticated with no
docs/reviews/reservation-release-spec-v1-claude.md:281:1. **B1** — `release_serve_model` granted to anon/authenticated is a client-callable
docs/reviews/task-1f-a-1-reserve-rpc.md:7:**Claude task-review — Approved.** Spec ✅: owner from `auth.uid()` internal (never a param); promoted-gate before any money; per-attempt charge inside the generating branch only; exactly-K bound (`attempt_count < max_serve_attempts`); cap arbiter **byte-identical** to `enqueue_job` (0011); savepoint/PJ004 rolls back claim+charge together; force-RLS + service_role-only grants; RPC `security definer set search_path=public` granted `authenticated, anon`; seed helper mirrors the worker row. Strengths: RLS-lockdown test non-vacuous (`.select()`-chained 0-rows + service-read exact fields + `relforcerowsecurity=true`); K-boundary is a real two-racer `Promise.all` asserting committed post-state. **Important:** `at_capacity`-on-*reclaim* rollback path (B7c) untested (only fresh-insert covered).
docs/reviews/task-1f-a-1-reserve-rpc.md:19:- **→ Task 8 (#22):** ENFORCE/TEST the config invariant `MAX_OWNED·K·est ≤ cap·SAFETY_FRACTION` — anon bound (2 docs) asserted hard; registered residual recorded as explicitly deferred to 1G. Do **not** rely on comments (Codex Important).
docs/reviews/whole-branch-2c-review.md:8:- **`promoted` readiness predicate coherent across all 3 enforcement points:** client gate `VideoMenu` (`video.summaryReady===true`, derived at supabase-metadata-store.ts:54), owner serve route `app/api/html/[id]/route.ts:57-58` (committed→503/!promoted→404), share-create RPC `0017` (`v_promoted is distinct from true`→404). A gated action can only fire when promoted; every server path serves exactly promoted. No ready-action-that-404s, no gated-action-that-fires-when-not-ready.
docs/reviews/spec-1f-a-codex-v5.md:107:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v5.md:111:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v5.md:116:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` reserve RPC with an exact idempotent transaction (Option A-lite);** see §4.2 for the algorithm. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned before touching money. Returns coarse `reserved | already_charged | at_capacity`. **Only `reserved` triggers generation** — `already_charged` never regenerates (503-retry), which **single-flights** the paid call. Model call honors `CLOUD_CAPS`; fixed `magazine_est_cents`; no quota debit; reconcile deferred. | `unique(owner,doc,day)` + `ON CONFLICT` makes reserve+dedup+abuse-bound atomic; internal `auth.uid()` blocks forged-owner/ledger-probe via direct PostgREST; only-`reserved`-generates bounds paid *Gemini calls* (not just charges — the v3 gap both reviewers caught). Keeps serve-side gen under the hard daily kill-switch while staying approximate. |
docs/reviews/spec-1f-a-codex-v5.md:136:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v5.md:148:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v5.md:216:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v5.md:323:- SECURITY DEFINER reserve_serve_model(p_playlist_id, p_video_id) granted authenticated,anon:
docs/reviews/spec-1f-a-codex-v5.md:412:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v5.md:416:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v5.md:421:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` reserve RPC with an exact idempotent transaction (Option A-lite);** see §4.2 for the algorithm. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned before touching money. Returns coarse `reserved | already_charged | at_capacity`. **Only `reserved` triggers generation** — `already_charged` never regenerates (503-retry), which **single-flights** the paid call. Model call honors `CLOUD_CAPS`; fixed `magazine_est_cents`; no quota debit; reconcile deferred. | `unique(owner,doc,day)` + `ON CONFLICT` makes reserve+dedup+abuse-bound atomic; internal `auth.uid()` blocks forged-owner/ledger-probe via direct PostgREST; only-`reserved`-generates bounds paid *Gemini calls* (not just charges — the v3 gap both reviewers caught). Keeps serve-side gen under the hard daily kill-switch while staying approximate. |
docs/reviews/spec-1f-a-codex-v5.md:441:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v5.md:453:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v5.md:513:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v5.md:623:### M-2 — Marker table `serve_model_charge` grant/RLS lockdown is not stated; because the reserve RPC is granted to `anon, authenticated`, a client-writable marker table would allow pre-seeding a *foreign* owner's `(owner,doc,day)` marker → that owner's doc returns `already_charged` → 503, a cross-tenant availability brick — CORRECTNESS · **NEW table in v4** · v3-traceback: none (new surface)
docs/reviews/spec-1f-a-codex-v5.md:625:**Where:** §4.2 ("a marker table `serve_model_charge(owner_id, doc_key, day)` … the RPC owns it; never owner-writable jsonb"). The spec says the RPC owns it but does not state the table's grants/RLS the way 0011 does for `spend_ledger` (`grant … to service_role` only, `enable/force row level security`, **no** anon/authenticated grant — 0011:17–18). "never owner-writable jsonb" rules out the *old* jsonb-marker idea but does not pin the new table's grants.
docs/reviews/spec-1f-a-codex-v5.md:627:**Scenario:** if the migration grants `insert` on `serve_model_charge` to `authenticated`/`anon` (or forgets to force RLS), a client `INSERT`s a marker with a *victim's* `owner_id` and a real `doc_key`. The victim's next view → `already_charged` → model absent → 503 "generating" for the rest of the day. Cross-tenant DoS, no cost to the attacker.
docs/reviews/spec-1f-a-codex-v5.md:631:**Fix:** State in §4.2 that `serve_model_charge` has RLS enabled+forced, **no** `insert/update/delete` grant to `anon/authenticated` (writes only via the `SECURITY DEFINER` RPC), mirroring `spend_ledger`. Add a confinement test: a direct client `INSERT`/`UPDATE`/`DELETE` on `serve_model_charge` is rejected.
docs/reviews/spec-1f-a-codex-v5.md:649:### L-3 — `reserve_serve_model`'s tri-state result lets any anon caller probe global daily-spend state (`at_capacity` leaks "day is over budget") — CORRECTNESS/nit · v3-traceback: Claude-v3 L-3, unchanged
docs/reviews/spec-1f-a-codex-v5.md:695:- **Quota / Allowance** — the per-**account**, per-**job kind**, per-**month** ceiling on how many Jobs an owner may create (e.g. anon: 2 summary/mo, 0 dig; registered: N summary + 5 dig/mo). Consumed by an **atomic debit** inside the enqueue transaction (`usage_counters`, keyed by month so it refills implicitly). It bounds *per-user* volume; distinct from the **daily cap**, which bounds *global dollars*.
docs/reviews/spec-1f-a-codex-v5.md:698:- **Velocity limit** — a per-**IP** rate cap (Jobs/hour from one client IP) that bounds the anonymous-uid churn (clear cookies → fresh anon uid → fresh tiny quota) that per-account quota cannot catch. Enforced in the advisory **preflight**, not the authoritative debit.
docs/reviews/spec-1f-a-codex-v5.md:699:- **Tier** — the binary **anon vs registered** distinction (`profiles.is_anonymous`, set at provisioning and immutable) that selects the quota allowances. Stage 1 has no richer tier/role model.
docs/reviews/spec-1f-a-codex-v5.md:706:- **Principal** — the identity a storage operation acts on behalf of, plus the selector for which index it targets. Every storage operation takes an explicit Principal; there is no ownerless path. Locally it is a fixed single-user sentinel; in the cloud it is the authenticated (or anonymous) user.
docs/reviews/spec-1f-a-codex-v5.md:766:grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/spec-1f-a-codex-v5.md:777:create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/spec-1f-a-codex-v5.md:778:  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/spec-1f-a-codex-v5.md:782:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/spec-1f-a-codex-v5.md:804:-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/spec-1f-a-codex-v5.md:813:revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/spec-1f-a-codex-v5.md:822:  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/spec-1f-a-codex-v5.md:858:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v5.md:859:      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/spec-1f-a-codex-v5.md:894:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v5.md:909:  v_anon boolean; v_owner_created timestamptz;
docs/reviews/spec-1f-a-codex-v5.md:918:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v5.md:919:  if v_anon is null then raise exception 'unknown owner'; end if;
docs/reviews/spec-1f-a-codex-v5.md:926:  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
docs/reviews/spec-1f-a-codex-v5.md:929:  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
docs/reviews/spec-1f-a-codex-v5.md:930:  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
docs/reviews/spec-1f-a-codex-v5.md:932:  if v_anon then
docs/reviews/spec-1f-a-codex-v5.md:936:      where p2.is_anonymous = false
docs/reviews/spec-1f-a-codex-v5.md:952:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v5.md:1293:| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v5.md:1296:| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v5.md:1314:  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v5.md:1356:- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v5.md:1364:   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v5.md:1961:supabase/migrations/0011_cost_guardrails.sql:101:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v5.md:1968:supabase/migrations/0011_cost_guardrails.sql:161:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v5.md:2613:  is_anonymous boolean not null default false,
docs/reviews/spec-1f-a-codex-v5.md:2825:   271	| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v5.md:2828:   274	| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v5.md:2846:   292	  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v5.md:2888:   334	- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v5.md:2896:   342	   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v5.md:3036:   175	    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/task-1d-12-cap-soundness-review.md:15:Only 4 integration files touch `guardrail_config`: schema (read-only), cost-guardrails (beforeEach resets the 3 relied-on cols to defaults; no body-level mutation of them), summary-handler (mutates max_duration_seconds in try/finally with restore), cap-soundness (read-only). Under `--runInBand` with no custom sequencer, the live row is always canonical when cap-soundness runs. A `beforeAll` pin would defeat the test's purpose (validate the LIVE config) and duplicate the migration's source-of-truth → NOT recommended.
docs/reviews/whole-branch-cloud-dig-deeper-frontend-v1-review.md:32:- **Anon parity:** serve + POST both read `profiles.is_anonymous !== false`; pre-disabled `<span>` (no `data-section`) is inert against the `a.dig-trigger[data-section]` delegate.
docs/reviews/task-1f-a-8-config-invariant.md:7:**Claude — Approved.** Verified spec-compliant verbatim: reads live cost config, hard anon bound, tested registered-deferral, correct real columns, correct `SAFETY_FRACTION` direction. Flagged the cross-file `guardrail_config` mutation hazard as real-but-fix-belongs-elsewhere (warned a naive self-reset would be tautological).
docs/reviews/task-1f-a-8-config-invariant.md:14:1. **C1:** doc counts read from `quota_allowance.monthly` (anon/registered), positive-integer-guarded.
docs/reviews/task-1f-a-8-config-invariant.md:15:2. **C2:** `beforeAll` restores `guardrail_config` from live `information_schema.columns` DEFAULTs (drift-proof) — order-safety **proven** against simulated dirty rows (`6/8/4`); RED **proven** (raising the true column default to 30 → anon test fails 300>100, revert → green). (`exec_sql` is read-only, so the restore reads catalog defaults + applies via UPDATE.)
docs/reviews/task-1f-a-8-config-invariant.md:24:Make quota fully drift-proof by having the mutating files (`cost-guardrails.test.ts`, `helpers/clients.ts`, `serve-model-charge.test.ts`) RESTORE `guardrail_config`/`quota_allowance` after mutating (or add a canonical seed source), so Task 8 can read LIVE quota with no self-reset. This also fixes the broader integration-suite config-singleton hygiene.
docs/reviews/spec-1f-a-claude-v5.md:12:**Headline verdict:** v5 genuinely closes three of the four round-4 findings — the at_capacity path now returns a status while voiding the marker (M-1 FIXED via savepoint/DELETE), the marker table is force-RLS + service_role-only-write so a client cannot forge a cross-tenant marker (M-2 FIXED), the definer verifies an **owned + promoted** summary before touching money (Codex-v4 promoted-in-definer FIXED), and the CSP gains `frame-ancestors`/`form-action 'none'` (L-2 FIXED). The v4 Claude H-1 brick is *addressed in spirit* by `release_serve_model`. **But the v4 H-1 fix itself introduces one new Blocking hole: `release_serve_model` is an unguarded, directly-callable, unbounded lever that voids the reserve idempotency.** Because the serve path runs on the session client (D5), release must be granted to `authenticated, anon`, so a direct PostgREST caller can loop `reserve → release → reserve → release …` on a **single owned, promoted doc**: each `reserve` adds `magazine_est` to the global `reserved_cents` (release deliberately does **not** reverse it), the marker is deleted each cycle so the next `reserve` is a fresh charge, and ~`daily_cap/est` cheap RPC-pairs drive the **global** daily cap to `at_capacity` for **all tenants** — **spending zero real Gemini dollars**. This converts round-4's *accepted* "an honest failing loop trips the cap at real spend" into a **free, instant, repeatable global availability DoS** on the money kill-switch, reachable by any anon guest with one promoted doc. The reserve-idempotency doc-count bound that v4 relied on to close the H-1/H-2 DoS is defeated by the release lever, and the spec does not acknowledge it. **Not converged — one more round to bound release/re-reserve per `(owner,doc,day)`.**
docs/reviews/spec-1f-a-claude-v5.md:31:**Where:** §4.1 step 5 ("a small definer `release_serve_model(p_playlist_id, p_video_id)` **deletes the marker** for `(auth.uid(), doc, today)` … it does **not** reverse the ledger reservation — the spent estimate stays counted, conservative"); D5 (serve path is on the **session client**, never service_role); §4.2 (reserve granted to `authenticated, anon`). Because the serve route runs on the session/anon client, `release_serve_model` — like `reserve_serve_model` — must be granted to `authenticated, anon` to be callable from the route, so it is reachable by a **direct PostgREST call**, exactly the surface the whole A-lite design is built to defend against.
docs/reviews/spec-1f-a-claude-v5.md:33:**Why the v4 doc-count bound fails.** v4 closed the global-cap DoS by arguing the marker/charge space is the caller's **owned + promoted** doc set, which is quota-bounded (anon: 2 summary/mo), so a caller can drive at most `(owned-promoted-docs × est)` into the ledger per day, and reserve is idempotent per `(owner,doc,day)` so a reload-loop cannot re-charge the same doc. **`release_serve_model` deletes the marker**, which is precisely the row that enforces that idempotency. After a delete, the next `reserve` for the same doc finds no conflict → fresh `INSERT` → charges `est` again. So the per-`(owner,doc,day)` cap of **one** charge becomes **unbounded** charges.
docs/reviews/spec-1f-a-claude-v5.md:42:**Why this is worse than the risk v4 accepted.** v4 explicitly accepted that a persistently-failing *honest* reload-loop trips the cap ("→ at_capacity for all — the kill-switch working"): but in that path **each retry actually calls Gemini** — the ledger climb reflects **real dollars spent**, the cap trips at a real `$5`, and each retry costs the attacker real generation latency. B-1 trips the identical global outage at **`$0` platform spend, instantly, for free, repeatable every day**, with no generation at all. The kill-switch is meant to stop the platform bleeding money; B-1 lets any anon user blow the global fuse without the platform spending a cent — pure denial, not cost control. This is a money-path/availability regression introduced by the exact change the round was for, so it blocks convergence.
docs/reviews/spec-1f-a-claude-v5.md:44:**Why Blocking (not High).** It is directly reachable by an anonymous caller, defeats the stage's central safety mechanism (Success-Criterion 3: "refuses generation when the day is over budget, idempotent per `(owner,doc,UTC-day)`, reload-loops don't re-charge" — B-1 makes reload-loops re-charge without bound), and resurrects a DoS two prior rounds were spent closing. The intent to *bound* re-reservation is not stated anywhere; release is described as an unconditional delete.
docs/reviews/spec-1f-a-claude-v5.md:49:- If the team decides B-1 is within the already-accepted "any owner can blow the global fuse" risk and wants to defer real hardening to **1G** (anon-abuse controls — CAPTCHA/rate-limit, explicitly scoped there in §9), then the spec **must explicitly acknowledge** that `release_serve_model` widens the free-DoS surface beyond the honest-loop case and record it as a deferred, owner-assigned risk — it currently claims the loop is "bounded by the daily cap" as if that were acceptable, without noting the `$0`-spend amplification. Silent is not an option for a money-path change.
docs/reviews/spec-1f-a-claude-v5.md:69:**Where:** `reserve_serve_model` has a numbered 5-step exact transaction in §4.2; `release_serve_model` appears only inline in §4.1 step 5 ("a small definer … deletes the marker for `(auth.uid(), doc, today)`"). Unspecified: (a) its grant (must be `authenticated, anon` to be callable on the session client — the crux of B-1, and worth stating explicitly so the DoS surface is visible in review); (b) whether it derives owner from `auth.uid()` internally and takes owner as never-a-param (§4.1 implies yes — "`(auth.uid(), doc, today)`" — good, but it is not pinned the way reserve step 1 is); (c) that it verifies nothing about ownership/promoted (it doesn't need to — the DELETE is `auth.uid()`-scoped so a foreign/absent doc is a harmless no-op — but this should be stated so a reviewer can see it is not a cross-tenant lever); (d) the explicit invariant "**never** touches `spend_ledger`/`usage_counters`" (ledger-not-reversed is stated; quota-untouched is implied since reserve does no quota debit).
docs/reviews/spec-1f-a-claude-v5.md:73:**Fix:** Give `release_serve_model` its own numbered exact-transaction block in §4.2 (owner from `auth.uid()`, `auth.uid()`-scoped DELETE, ledger/quota untouched, grant `authenticated, anon`, chosen bound from B-1), and a confinement test that a direct client cannot use it to escape the per-`(owner,doc,day)` charge bound.
docs/reviews/spec-1f-a-claude-v5.md:81:**Fix:** Enumerate the reserve-denial-mid-serve branch: reserve returning a generic denial (or a distinct "not-promoted-now" signal) → serve maps to **503 "not ready, retry"** (same as step-4 `committed`), never 404/500. Add a behavior row.
docs/reviews/spec-1f-a-claude-v5.md:118:v5 **genuinely fixes three of the four round-4 findings** (at_capacity status/rollback M-1, marker lockdown M-2, promoted-in-definer) and the CSP nit, and *addresses* the H-1 brick for the honest-failure path. **But the H-1 fix introduces a new Blocking hole (B-1): `release_serve_model` is an unguarded, directly-callable, unbounded lever** — because the serve path is on the session client, release must be granted to `authenticated, anon`, so a direct caller loops `reserve→release` on one owned promoted doc to drive the **global** daily cap to `at_capacity` for all tenants at **`$0` real spend**, defeating the reserve-idempotency doc-count bound that v4 relied on to close the global-cap DoS. Two Mediums pin the new surface (M-1 client-abort may never fire release, re-bricking the *main* H-1 case; M-2 release lacks the §4.2 exact-transaction/grant treatment reserve got) and one Medium is a reserve/serve promoted-check TOCTOU with an unmapped denial branch.
docs/reviews/spec-stage-1e-b-v2-rereview.md:41:- **Anon enqueue** satisfies the FK with a seeded anon-owned playlist row (provisioning trigger + grants exist).
docs/reviews/plan-cloud-dig-deeper-frontend-v2-rereview.md:14:| B1 | isAnonymous ← `profiles.is_anonymous` fail-closed | GENUINE (supabase+user in scope; mockAuth widening safe) | GENUINE (traced all 4 pre-existing tests still pass; null-row test real) |
docs/reviews/plan-cloud-dig-deeper-frontend-v2-rereview.md:21:Both independently re-confirmed the load-bearing invariants: **byte-identity when `cloud` undefined** (every touched expression collapses to today's output; the stale-section golden pins the one non-obvious case), **`NAV_SCRIPT` untouched** (separate `DIG_CLOUD_SCRIPT` + diff guard), **money invariant** (dig branch = `loadDigForServe` + render + `fileResponse`; the added `profiles` read is a free select; dig-state is blob-presence only; T6 asserts `spend_ledger` unchanged across serve + poll), **anon defense-in-depth** (inert `<span>` + server 403 fallback), and **all §9 behaviors 1–15 have a test**.
docs/reviews/plan-cloud-dig-deeper-frontend-v2-rereview.md:29:- **L (Codex):** plan `mockAuth` comment falsely said "undefined ⇒ null row ⇒ fail-closed anon" (helper returns `is_anonymous:false`). **Applied:** corrected — undefined defaults to registered for back-compat; the dedicated null-row test exercises fail-closed.
docs/reviews/plan-cloud-dig-generation-codex-v2.md:23:5. **H3 anon via profiles** — `profiles_self` RLS (`for all using (id = auth.uid())`) + select grant
docs/reviews/plan-cloud-dig-generation-codex-v2.md:24:   to `authenticated` → the session client can read its own `is_anonymous`; no 500. ✓
docs/reviews/plan-cloud-dig-generation-codex-v2.md:34:- **MEDIUM (Codex) — anon test can't set `is_anonymous`.** `profiles_is_anonymous_immutable` trigger
docs/reviews/plan-cloud-dig-generation-codex-v2.md:35:  rejects `profiles.update({is_anonymous})`. **Fix:** Task 1 uses `anonSession()` + asserts the row is
docs/reviews/plan-cloud-dig-generation-codex-v2.md:36:  anon.
docs/reviews/whole-branch-review.md:15:**Genuine strengths:** per-section-blob model eliminates the lost-update race by construction; §9.2 completed-row re-check prevents a phantom 202; fail-closed anon gate + "prove the anon is real" test discipline are correct for a money path.
docs/reviews/spec-1f-b-codex-v3-rereview.md:46:Fix: specify anonymous behavior for promoted-but-missing or unparsable MD, ideally coarse `404` or `503 not ready`, with no 500 leak.
docs/reviews/task-cloud-dig-6-review.md:11:Verified in-diff: 400-before-401 ordering (all validation before `cookies()`/`createServerSupabase`); two-client split (session client → auth + `profiles.is_anonymous` RLS read; service-role → enqueue RPC only, no tenant read); `parseClientIp` byte-for-byte identical to the deleted copy (ingest import-swap only, unchanged); local branch untouched (`await params` hoisted once; cloud branch reads URL+headers, never `request.json()`); `Retry-After:60` on 429 + `challengeRequired` deliberate omission both present with origin comments; `EnqueueDigDeps` matches the route's call field-for-field.
docs/reviews/task-cloud-dig-6-review.md:23:The anon gate failed **open**: `isAnonymous: profile?.is_anonymous === true` meant a null/errored `profiles` read (RLS denial, missing row, transient error → `profile===null`) yielded `false` → an anonymous user treated as **registered**, bypassing the dig=0 → 403 gate. **Fixed fail-CLOSED:** `profile?.is_anonymous !== false` — only an explicit `false` grants registered access; `true`/`null`/`undefined` → anon → 403. Backed by a profile-null test asserting `isAnonymous: true`.
docs/reviews/task-cloud-dig-6-review.md:29:Added: anonymous-path delegation test (`isAnonymous:true`), profile-null fail-safe test, whitespace + negative-integer `sectionId` 400 tests, invalid-videoId before-auth test, and the missing `createServerSupabase not called` assertion on invalid-playlist. dig-cloud-route 5→11 tests.
docs/reviews/plan-1f-b-codex.md:38:  **Fix:** wrap/spy the service client factory or `SupabaseClient.prototype.rpc`, and assert zero `.rpc('reserve_serve_model', ...)` plus unchanged `spend_ledger`/`serve_model_charge` across valid, not-ready, stale, missing/corrupt MD, revoked, expired, unknown, and unpromoted cases.
docs/reviews/spec-1f-a-codex-v7.md:50:> RPC** (removes the v5 instant anon-DoS lever). **v7 adds the `K`-attempt bound** both round-6 reviewers
docs/reviews/spec-1f-a-codex-v7.md:115:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v7.md:119:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v7.md:124:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping abuse to `K·est·(owned docs)` ≪ daily cap. Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
docs/reviews/spec-1f-a-codex-v7.md:144:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v7.md:156:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v7.md:191:       anon-callable release lever exists → the v5 instant DoS is gone.**
docs/reviews/spec-1f-a-codex-v7.md:228:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v7.md:265:  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
docs/reviews/spec-1f-a-codex-v7.md:310:**Reviewer mandate:** (1) confirm the v5 Blocking (B-1, the anon-callable `release_serve_model` → free/instant/repeatable $0 global-cap DoS) is *genuinely* gone, not reworded; (2) hunt for any NEW hole the lease redesign introduces; (3) verify the two invariants — (a) no anon-callable release, (b) charge-per-attempt keeps the daily cap the true bound and CANNOT net-to-zero.
docs/reviews/spec-1f-a-codex-v7.md:317:**Headline verdict.** v6 **genuinely closes the v5 Blocking.** There is no `release_serve_model` RPC anywhere in v6; the only money-touching serve RPC is `reserve_serve_model`, and the marker table stays force-RLS + `service_role`-only-write, so **no anon-callable lever can delete/void a marker.** The v5 instant/free/single-doc/infinitely-repeatable ledger drain is unreachable — the per-`(owner,doc,day)` charge can only be repeated after the lease **expires** (`LEASE_TTL ≈ 180 s`), which is server-set and not client-shortenable. Invariant (a): **PASS.** Invariant (b): the ledger is **monotonic** — there is no decrement anywhere in v6, so it **cannot net-to-zero**, and the conditional-UPDATE arbiter keeps total spend ≤ `daily_cap`; **PASS.** The two Postgres-semantics questions the mandate raised (the `ON CONFLICT DO UPDATE … WHERE … RETURNING (xmax=0)` discriminator, and the lease-boundary double-reclaim) both resolve **correctly** (see "Claims that HOLD"). The cap-refusal rollback of a *reclaim* is also sound **provided the savepoint encloses step 4** (it does per the spec text; see L-1 for the test-phrasing gap).
docs/reviews/spec-1f-a-codex-v7.md:327:| **B-1 (Blocking): `release_serve_model` is an anon-callable, unbounded lever — `reserve→release` loop on one owned promoted doc drives the GLOBAL cap to `at_capacity` for all tenants at $0 real spend, instant, repeatable** | v6 **deletes the release RPC entirely.** Recovery = the lease **expires** (`LEASE_TTL`); the next view **reclaims** (`ON CONFLICT DO UPDATE … WHERE lease_expires_at < now()`) and re-charges. No client-callable void of any marker exists. | **FIXED — genuinely.** The specific lever (delete-the-marker) is gone; idempotency can only be "reset" by real wall-clock time (`≥ TTL`), which is not a client lever. See H-1 for the residual the *new* mechanism opens. |
docs/reviews/spec-1f-a-codex-v7.md:351:3. If `20 × est ≥ daily_cap` the cap trips in one round; otherwise wait `LEASE_TTL` (~180 s), re-view all 20 (leases expired → reclaim → 20 more charges), repeat. `daily_cap/est` charges trip the global cap in `⌈(cap/est)/20⌉ × TTL` — a few minutes for a registered user, ~50 min for a 2-doc anon.
docs/reviews/spec-1f-a-codex-v7.md:358:- **Alternative — accept + defer, but correct the spec.** If the team accepts the rate-limited single-user drain as within the shared-cap risk already scoped to **1G** (anon-abuse controls / rate-limiting, §9), then §4.1/§3 D10 **must** (a) drop the "each reclaim = a real Gemini call, never a $0 drain" framing — replace it with the true bound: "the charge commits at reserve, before generation, so a charge can cost ~$0 real Gemini; the actual bounds are the `LEASE_TTL` rate-limit per doc and the owner's promoted-doc count, and total spend ≤ `daily_cap`"; and (b) record "a single owner can drive the whole shared daily cap → serve-side outage for all tenants" as an explicit, owner-assigned **deferred 1G risk**. Silent over-claiming is not acceptable for a money-path spec.
docs/reviews/spec-1f-a-codex-v7.md:383:**Why Medium:** no cost leak (denial → no charge), narrow window, but an unmapped RPC return in the money path is exactly what surfaces as a 500. **Fix:** enumerate it — reserve denial mid-serve → **503 "not ready, retry"** (same as the step-4 `committed` case), never 404/500; add a behavior row. (If reserve `RAISE`s the denial, the route must catch and map it, not bubble a 500.)
docs/reviews/spec-1f-a-codex-v7.md:411:- **No anon-callable release lever (invariant a).** No `release_serve_model` exists; the marker table is force-RLS + `service_role`-only-write; a client cannot delete/void a marker. The v5 instant/free/single-doc/repeatable $0 drain is **unreachable**. Idempotency can only be re-armed by real wall-clock (`≥ TTL`), which is server-set. **B7d confirmed.**
docs/reviews/spec-1f-a-codex-v7.md:423:**v6 genuinely closes the v5 Blocking** (invariant a: no anon-callable release; invariant b: monotonic ledger, cannot net-to-zero, cap is the true bound). The lease's Postgres semantics are correct — the `RETURNING`-row (not `xmax`) is the load-bearing single-flight signal, the boundary double-reclaim serializes to one generator, and the cap-refused-reclaim rollback restores the prior expired lease (no global brick).
docs/reviews/spec-1f-a-codex-v7.md:445:ADVERSARIAL spec reviewer — v6 CONFIRMING round. v5 had one Blocking (a free anon global-cap DoS via the release RPC). v6 replaces it with a LEASE-based single-flight and NO release RPC (user decision A+). Verify the DoS is genuinely gone and hunt for any NEW hole the lease design introduces. Concrete; find problems.
docs/reviews/spec-1f-a-codex-v7.md:451:- reserve RPC (SECURITY DEFINER, granted authenticated,anon): (1) v_owner:=auth.uid(); (2) verify owned + promoted summary; (3) doc_key/day; (4) INSERT ... (lease_expires_at=now()+LEASE_TTL) ON CONFLICT (owner,doc,day) DO UPDATE SET lease_expires_at=now()+LEASE_TTL WHERE serve_model_charge.lease_expires_at < now() RETURNING (xmax=0) AS inserted -> no row => in_flight (no charge); row => generator; (5) charge via conditional-UPDATE daily-cap arbiter; 0 rows => sub-block/EXCEPTION rolls back the lease claim => at_capacity. CHARGE EVERY ATTEMPT (first + each lease-reclaim). NO release RPC. On failure/abort: do nothing; lease expires (~180s); next view reclaims + regenerates + recharges.
docs/reviews/spec-1f-a-codex-v7.md:453:VERIFY: (a) is the v5 release-lever DoS genuinely gone (no anon-callable release exists)? (b) does charge-per-attempt keep the daily cap the true bound (a reload-loop on a failing doc climbs reserved_cents until at_capacity — bounded — and CANNOT net-to-zero)?
docs/reviews/spec-1f-a-codex-v7.md:477:> RPC** — which removes the v5 anon-DoS lever entirely. Needs one confirming review round (edge: an
docs/reviews/spec-1f-a-codex-v7.md:541:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v7.md:545:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v7.md:550:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned **and `promoted`** before touching money. Claims a short **generation lease** on the `serve_model_charge` marker and **charges `magazine_est_cents` per attempt**; returns coarse `reserved | in_flight | at_capacity`. **No release RPC** — a failed/aborted attempt just lets the lease expire; the next view reclaims + re-charges. No quota debit; reconcile deferred. | The lease makes generation single-flight (`in_flight` blocks a concurrent second call); charge-per-attempt keeps the **daily cap** the true bound on Gemini spend; **removing the release lever** closes the v5 $0-DoS. `auth.uid()`-internal + promoted-check blocks direct-PostgREST abuse. Keeps serve-side gen under the hard kill-switch while staying approximate. |
docs/reviews/spec-1f-a-codex-v7.md:570:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v7.md:582:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v7.md:612:       never the instant $0 ledger-drain of a release lever. **No anon-callable release
docs/reviews/spec-1f-a-codex-v7.md:648:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v7.md:680:  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
docs/reviews/spec-1f-a-codex-v7.md:717:- **Quota / Allowance** — the per-**account**, per-**job kind**, per-**month** ceiling on how many Jobs an owner may create (e.g. anon: 2 summary/mo, 0 dig; registered: N summary + 5 dig/mo). Consumed by an **atomic debit** inside the enqueue transaction (`usage_counters`, keyed by month so it refills implicitly). It bounds *per-user* volume; distinct from the **daily cap**, which bounds *global dollars*.
docs/reviews/spec-1f-a-codex-v7.md:720:- **Velocity limit** — a per-**IP** rate cap (Jobs/hour from one client IP) that bounds the anonymous-uid churn (clear cookies → fresh anon uid → fresh tiny quota) that per-account quota cannot catch. Enforced in the advisory **preflight**, not the authoritative debit.
docs/reviews/spec-1f-a-codex-v7.md:721:- **Tier** — the binary **anon vs registered** distinction (`profiles.is_anonymous`, set at provisioning and immutable) that selects the quota allowances. Stage 1 has no richer tier/role model.
docs/reviews/spec-1f-a-codex-v7.md:728:- **Principal** — the identity a storage operation acts on behalf of, plus the selector for which index it targets. Every storage operation takes an explicit Principal; there is no ownerless path. Locally it is a fixed single-user sentinel; in the cloud it is the authenticated (or anonymous) user.
docs/reviews/spec-1f-a-codex-v7.md:817:| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
docs/reviews/spec-1f-a-codex-v7.md:822:| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v7.md:825:| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v7.md:843:  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v7.md:885:- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v7.md:893:   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v7.md:978:grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/spec-1f-a-codex-v7.md:989:create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/spec-1f-a-codex-v7.md:990:  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/spec-1f-a-codex-v7.md:994:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/spec-1f-a-codex-v7.md:1016:-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/spec-1f-a-codex-v7.md:1025:revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/spec-1f-a-codex-v7.md:1034:  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/spec-1f-a-codex-v7.md:1070:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v7.md:1071:      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/spec-1f-a-codex-v7.md:1106:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v7.md:1121:  v_anon boolean; v_owner_created timestamptz;
docs/reviews/spec-1f-a-codex-v7.md:1130:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v7.md:1131:  if v_anon is null then raise exception 'unknown owner'; end if;
docs/reviews/spec-1f-a-codex-v7.md:1138:  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
docs/reviews/spec-1f-a-codex-v7.md:1141:  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
docs/reviews/spec-1f-a-codex-v7.md:1142:  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
docs/reviews/spec-1f-a-codex-v7.md:1144:  if v_anon then
docs/reviews/spec-1f-a-codex-v7.md:1148:      where p2.is_anonymous = false
docs/reviews/spec-1f-a-codex-v7.md:1164:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v7.md:1172:7:> RPC** (removes the v5 instant anon-DoS lever). **v7 adds the `K`-attempt bound** both round-6 reviewers
docs/reviews/spec-1f-a-codex-v7.md:1174:81:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping abuse to `K·est·(owned docs)` ≪ daily cap. Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
docs/reviews/spec-1f-a-codex-v7.md:1217:295:| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
docs/reviews/spec-1f-a-codex-v7.md:1240:   295	| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
docs/reviews/spec-1f-a-codex-v7.md:1245:   300	| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v7.md:1248:   303	| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v7.md:1266:   321	  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v7.md:1284:    76	| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v7.md:1289:    81	| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping abuse to `K·est·(owned docs)` ≪ daily cap. Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
docs/reviews/spec-1f-a-codex-v7.md:1309:   101	1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v7.md:1321:   113	   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v7.md:1356:   148	       anon-callable release lever exists → the v5 instant DoS is gone.**
docs/reviews/spec-1f-a-codex-v7.md:1393:   185	    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v7.md:1430:   222	  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
docs/reviews/spec-1f-a-codex-v7.md:1463:   363	- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v7.md:1471:   371	   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v7.md:1511:   371	   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-c-codex-v1.md:15:  Spec D10 says extend B18b/B18c so share MD reaches no charging code, but the current guard scans only `app/s`, `lib/share`, and [lib/html-doc/read-model.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/share/import-guard.test.ts:16). The proposed `lib/html-doc/file-response.ts` is imported by the anonymous share route but would not be scanned.  
docs/reviews/plan-1f-a-codex-v2-rereview.md:44:The revised integration test drives real `resolveOwnedPlaylistKey` / `readIndex` RLS points for registered/anon/foreign users (useful, no longer prose). But it does not actually call `GET` or assert HTTP 200/404; it asserts "route would proceed."
docs/reviews/task-2c-6-videomenu-review.md:5:**Implementation (both reviewers: spec-compliant, 0 impl findings):** four items in cloud branch only; local mode byte-unchanged; View `<a target=_blank rel=noopener>`, Download MD/HTML `<a download>` via summaryHref with every param, Share `<button>` onShare?()+onClose(); NO role="menuitem" (getByRole('link') works); not-ready → `<span aria-disabled title="Finalizing…">` (no link, Share no-op); onShare?:()=>void on VideoMenuProps; real --text-muted token; no service_role/DB; no unrelated edits.
docs/reviews/task-2c-6-videomenu-review.md:7:**Codex R1 (test gaps, Medium×2 + Low):** not-ready test only covered View (not Download MD/HTML/Share); local-mode test only asserted 2 of 4 absent; ready Share test didn't assert onClose. **Controller verified against the actual test file — Codex correct; Claude's higher-level read missed the gaps (dual review earned its keep on test completeness).**
docs/reviews/task-2c-6-videomenu-review.md:9:**Fix 79b9a75:** not-ready loops all 4 (aria-disabled+title+no-link, Share not-a-button+no-op); local-mode asserts all 4 absent; ready test asserts onClose. **R2 Codex CONVERGED** (VideoMenu unchanged, no new defect/vacuous assertion).
docs/reviews/reservation-release-spec-v2-claude.md:83:**Direction:** `enable + force row level security`, `grant insert (+ select) to service_role` only, no anon/authenticated policy (mirror `spend_ledger`); confirm definer functions (owner postgres, BYPASSRLS) can insert; state the audit insert must never fail the terminal write.
docs/reviews/reservation-release-spec-v2-claude.md:101:**Where:** §6 lines 149-155 vs §5 line 94. Real `reserve_serve_model` returns scalar `text` (`0014:22-24`), granted `authenticated, anon`, destructured as scalar in `serve-doc.ts:52-56`. Carrying a token → composite/record return → `DROP FUNCTION` + recreate + re-grant + update the `serve-doc.ts` call site to read `{status, token}`. Security is fine (token server-held, unforgeable); this is a mechanics gap. **Direction:** specify the DROP+recreate, new return shape (`returns table(status text, release_token uuid)`), grant re-issue, and the destructure change.
docs/reviews/task-2a-9-middleware-review.md:6:Verified OK: local no-op before `getSupabaseEnv()`; `/api/*` JSON 401 fires BEFORE the page→`/login` redirect (`middleware.ts:42` before `:51`); no `/login` loop; cloud-only `/` override (classifyRoute `/` stays public); `/try` anon-provision + `/s` classification preserved; callback `/library`→`/` (no caller relied on old default); the `middleware-api-401` test change forces cloud mode without weakening. Ran middleware-2a 14/14, auth-callback 3/3.
docs/reviews/task-2a-9-middleware-review.md:12:- **M2 (awareness → whole-branch/backlog):** `/s/[token]` (anonymous share) is `authenticated`-classified, so logged-out share recipients are redirected (target shifted `/`→`/login`). Pre-existing + spec-declared out-of-scope (design.md:54,333); T9 doesn't change classification. **Verify shared links open for logged-out recipients before launch.**
docs/reviews/task-2a-9-middleware-review.md:13:- **M3 (awareness → T11/whole-branch):** an anon user (via `/try`) counts as `user`, so `/login`→`/` — an anon user can't reach Google sign-in to upgrade. Per-spec (N5 + authed-/login→/). Primary signup (no session) reaches `/login` fine; only the anon-then-upgrade path is gapped.
docs/reviews/spec-stage-1d-v2-rereview.md:30:RESOLVED: Codex-B1/Claude-H2 (bypass via client enqueue → service-role-only + REVOKE + `auth.role()` guard); Codex-B2/Claude-H1/H3-sweep/Codex-H3 (release-on-failure/cancel/sweep → never-release); Codex-H4/Claude-M1 (dig enqueuable → reject `job_kind<>'summary'`); Codex-M5 (SQLSTATE collision → PT001/PT002); Codex-M6/Claude-M5 (IP through type layer → `{ownerId,enqueueIp}` context); Codex-L7/Claude-M2 (session-TZ month → UTC); Claude-M3 (velocity wording → coarse); Claude-M4 (disjoint sum → corrected `failed`); Claude-L3 (quota_allowance read grant); Claude-M6 (anon lockout → accepted/tunable).
docs/reviews/spec-1f-a-codex-v4.md:20:- SECURITY DEFINER reserve_serve_model(p_playlist_id, p_video_id) granted authenticated,anon:
docs/reviews/spec-1f-a-codex-v4.md:109:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v4.md:113:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v4.md:118:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` reserve RPC with an exact idempotent transaction (Option A-lite);** see §4.2 for the algorithm. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned before touching money. Returns coarse `reserved | already_charged | at_capacity`. **Only `reserved` triggers generation** — `already_charged` never regenerates (503-retry), which **single-flights** the paid call. Model call honors `CLOUD_CAPS`; fixed `magazine_est_cents`; no quota debit; reconcile deferred. | `unique(owner,doc,day)` + `ON CONFLICT` makes reserve+dedup+abuse-bound atomic; internal `auth.uid()` blocks forged-owner/ledger-probe via direct PostgREST; only-`reserved`-generates bounds paid *Gemini calls* (not just charges — the v3 gap both reviewers caught). Keeps serve-side gen under the hard daily kill-switch while staying approximate. |
docs/reviews/spec-1f-a-codex-v4.md:138:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v4.md:150:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v4.md:210:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v4.md:297:| B7b | Forged/foreign doc via direct RPC | authed/anon calls `reserve_serve_model` with a doc they don't own | definer derives owner from `auth.uid()` + verifies ownership → generic denial; no charge, no existence leak |
docs/reviews/spec-1f-a-codex-v4.md:300:| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v4.md:303:| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v4.md:329:- **Quota / Allowance** — the per-**account**, per-**job kind**, per-**month** ceiling on how many Jobs an owner may create (e.g. anon: 2 summary/mo, 0 dig; registered: N summary + 5 dig/mo). Consumed by an **atomic debit** inside the enqueue transaction (`usage_counters`, keyed by month so it refills implicitly). It bounds *per-user* volume; distinct from the **daily cap**, which bounds *global dollars*.
docs/reviews/spec-1f-a-codex-v4.md:332:- **Velocity limit** — a per-**IP** rate cap (Jobs/hour from one client IP) that bounds the anonymous-uid churn (clear cookies → fresh anon uid → fresh tiny quota) that per-account quota cannot catch. Enforced in the advisory **preflight**, not the authoritative debit.
docs/reviews/spec-1f-a-codex-v4.md:333:- **Tier** — the binary **anon vs registered** distinction (`profiles.is_anonymous`, set at provisioning and immutable) that selects the quota allowances. Stage 1 has no richer tier/role model.
docs/reviews/spec-1f-a-codex-v4.md:340:- **Principal** — the identity a storage operation acts on behalf of, plus the selector for which index it targets. Every storage operation takes an explicit Principal; there is no ownerless path. Locally it is a fixed single-user sentinel; in the cloud it is the authenticated (or anonymous) user.
docs/reviews/spec-1f-a-codex-v4.md:414:DESIGN CONTEXT: Stage 1F-a serves the summary rendered-HTML-doc from Supabase storage over a session/anon client (service_role forbidden). It renders on-serve and LAZILY materializes the magazine model on view (version/drift-gated). v3's key new element is Option A-lite for serve-side spend: ONE atomic, idempotent-per-(owner,doc,UTC-day) SECURITY DEFINER reserve RPC granted to authenticated,anon that (a) refuses over the daily cap, (b) is idempotent per (owner,doc,day) so reload-loops return "already charged", (c) reserves a fixed approximate estimate; backed by a per-(owner,doc,day) charge marker the RPC owns. Worker/enqueue_job UNCHANGED.
docs/reviews/spec-1f-a-codex-v4.md:418:2. SECURITY DEFINER leak. The RPC is granted to authenticated,anon and runs privileged over spend_ledger/guardrail_config. Can a caller pass a forged owner_id/doc to charge or read another owner's ledger, or probe the global cap state? Must it derive owner_id from auth.uid() internally (not a param)? Does the spec say so?
docs/reviews/spec-1f-a-codex-v4.md:421:5. Anything else: local render regression risk, drift-guard gaps, CSP completeness (default-src none / connect-src), storage write feasibility for anon.
docs/reviews/spec-1f-a-codex-v4.md:627:**Headline verdict:** The v3 pivot to the A-lite `SECURITY DEFINER` RPC **genuinely dissolves the v2 Blocker** (the money-gate is now *reachable* by the session/anon client, and the "no migration" claim is retracted). But the new RPC has a **fresh Blocking hole**: the per-`(owner,doc,day)` idempotency bounds the **charge** but not the **Gemini call** — after a failed generate, every same-day reload re-invokes Gemini *uncharged*, and because `actual_cents` is never reconciled the daily-cap ledger cannot see that spend. So the daily cap does **not** bound actual dollars — defeating the exact invariant A-lite exists to provide (and the whole reason A-lite was chosen over Option D). Plus two Highs: the anon-granted definer's owner/doc trust model is unspecified (v2 H-1 global-cap DoS is **not** actually closed for direct RPC callers), and the "single conditional UPDATE" framing mis-describes a construct that must touch **two** tables (marker + ledger) with a specific arbiter + rollback ordering. **Not converged — another round is mandatory.**
docs/reviews/spec-1f-a-codex-v4.md:636:| 2 | SECURITY DEFINER owner/doc trust | **FAIL → High H-1** | Spec never says `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the doc is a real *owned* artifact. A direct anon RPC call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS persists. |
docs/reviews/spec-1f-a-codex-v4.md:659:Concurrency makes it worse without even needing failure: two tabs on one un-materialized doc → one charge, **two** Gemini calls (attack #1); N tabs → N calls, 1 charge. An anon owner (2-doc quota) can hold open dozens of concurrent requests per doc and/or reload a reliably-failing doc all day — **unbounded per-day Gemini spend, cap never moves.** §8 trigger-1 explicitly tells the reviewer to verify "the per-`(owner,doc,day)` idempotency genuinely bounds a reload-loop / concurrent miss (no unbounded re-charge)." It bounds re-*charge*; it does **not** bound re-*spend*. This is the hole.
docs/reviews/spec-1f-a-codex-v4.md:672:### H-1 — The RPC is granted to `authenticated, anon` and callable **directly** (PostgREST), but the spec never states that `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the `doc` is a real OWNED artifact; a direct call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS is NOT actually closed — INTENT/DESIGN · **NEW / carryover** · v2-traceback: redteam-H-1, verify-H-1 (claimed fixed by idempotency; the fix has a hole)
docs/reviews/spec-1f-a-codex-v4.md:674:**Where:** spec D10 ("granted to `authenticated, anon`"; "a principal reserves at most once per **owned** doc/day; **owned-doc-count is quota-bounded** → no ledger-lever DoS"), §4.2, §4.1 step 5 (verification lives in the serve *code*, before the RPC call — step 4 reads status/ownership, step 5 calls the RPC). Compare `enqueue_job` (`0011:69-70`): trusts `p_owner_id` **only because** it is `service_role`-gated (`if auth.role() <> 'service_role' then raise`) — a trusted server passes the resolved owner.
docs/reviews/spec-1f-a-codex-v4.md:676:Two unstated, load-bearing requirements for an **anon-granted** `SECURITY DEFINER` RPC:
docs/reviews/spec-1f-a-codex-v4.md:678:1. **Owner must be `auth.uid()`, never a caller param.** A definer runs privileged and bypasses RLS. `enqueue_job` can accept `p_owner_id` because no untrusted caller can reach it (service_role-only). The A-lite RPC is reachable by any anon/authenticated caller, so if it accepts an owner parameter, a caller can attribute charges/markers to arbitrary owners. The spec is silent on this. It **must** state `v_owner := auth.uid()` internally and ignore/reject any caller-supplied owner.
docs/reviews/spec-1f-a-codex-v4.md:680:2. **The definer itself must verify the `doc` is a real, owned, promoted artifact — the serve-code check in step 4 does NOT protect a direct RPC call.** D10's entire abuse-bound rests on "owned-doc-count is quota-bounded." But that premise holds only if the marker set is bounded to real owned docs. The serve route (§4.1) does verify the doc (reads the index, asserts `promoted`) *before* step 5 — but the RPC is a directly-invocable PostgREST endpoint granted to anon. An attacker skips the route entirely and calls the RPC with `doc = "x1", "x2", … "xN"` — each a fresh `(owner, doc, day)` → each **reserves `est` against the GLOBAL ledger** → the daily cap drains to zero → **every other owner's serve materialization 503s "at capacity."** The idempotency marker does not stop this: idempotency is *per doc*, and `doc` is attacker-chosen and unbounded. So v2 H-1 (owner-driven global-cap DoS) is **re-opened**, not closed — the "quota-bounded" claim is asserted without the mechanism that would make it true.
docs/reviews/spec-1f-a-codex-v4.md:682:**Fix (needs a decision + design):** State in D10/§4.2 that the definer (i) sets owner from `auth.uid()` internally; (ii) **validates `(owner, playlist, video)` against the caller's own real, promoted summary artifact inside the function** (or accepts only a server-signed/opaque doc handle it can re-derive), so the marker set is genuinely quota-bounded; and (iii) rejects a call for a doc the caller does not own. Without (ii) the "no ledger-lever DoS" claim is unsubstantiated. (Borderline Blocking — a single anon client can deny the money kill-switch to all tenants; kept at High only because the *intent* to bound by owned docs is stated, just not mechanized.)
docs/reviews/spec-1f-a-codex-v4.md:731:### L-3 — The RPC's tri-state result ("reserved" / "already charged" / "at capacity") lets any anon caller probe the GLOBAL daily-spend state — CORRECTNESS/nit
docs/reviews/spec-1f-a-codex-v4.md:740:| **daily-cap infeasible on session client** (verify-B-1 / redteam-B-1, Blocking) | D10 + §4.2: new `SECURITY DEFINER` RPC granted to `authenticated, anon`, touching `spend_ledger`/`guardrail_config` only inside the definer; **"no migration" explicitly retracted** ("this slice DOES include a small, self-contained migration"). | **FIXED (mechanism now exists & reachable)** — but the mechanism introduces B-1 (charge-once/generate-many) + H-1 (owner/doc trust) + H-2 (construct mis-stated). Feasibility dissolved; soundness not. |
docs/reviews/spec-1f-a-codex-v4.md:756:- **Blob write/promote as a session client is feasible** (`artifacts_owner_rw` `for all to authenticated, anon`, key is server-constructed `{auth.uid()}/{playlist_key}/…`, `promote` stays under the owner prefix). Don't drag service-role onto the blob path.
docs/reviews/spec-1f-a-codex-v4.md:757:- **Cross-owner / unauth isolation holds** (RLS `playlists_owner`/`videos_owner` + storage first-segment `= auth.uid()`; foreign/absent `playlistId` → identical 404; anon session uid is a real `auth.uid()`).
docs/reviews/spec-1f-a-codex-v4.md:765:The v3 A-lite RPC **fixes the v2 Blocker's feasibility** (the money-gate is now reachable by the session/anon client and the "no migration" error is retracted) and cleanly closes the ledger-reserve race for distinct docs. But it introduces **one new Blocking (B-1): the daily cap no longer bounds actual Gemini dollars** — the per-`(owner,doc,day)` idempotency dedups the charge while leaving generate calls unbounded (concurrent first-views fire N calls for one charge; failed-generate reloads re-call Gemini uncharged all day), and reconcile-off means the ledger never sees it. Two Highs compound it: the anon-granted definer's owner/doc trust model is unspecified so v2's global-cap DoS is **not** actually closed for direct RPC callers (H-1), and "single conditional UPDATE" mis-describes a two-table construct whose dedup arbiter (`INSERT … ON CONFLICT DO NOTHING RETURNING` on a UNIQUE `(owner,doc,day)` marker) + insert-then-reserve-then-rollback ordering is left unstated and is racy as written (H-2).
docs/reviews/spec-1f-a-codex-v4.md:791:  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v4.md:833:- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v4.md:841:   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v4.md:866:grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/spec-1f-a-codex-v4.md:877:create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/spec-1f-a-codex-v4.md:878:  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/spec-1f-a-codex-v4.md:882:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/spec-1f-a-codex-v4.md:904:-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/spec-1f-a-codex-v4.md:913:revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/spec-1f-a-codex-v4.md:922:  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/spec-1f-a-codex-v4.md:958:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v4.md:959:      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/spec-1f-a-codex-v4.md:994:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v4.md:1009:  v_anon boolean; v_owner_created timestamptz;
docs/reviews/spec-1f-a-codex-v4.md:1018:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v4.md:1019:  if v_anon is null then raise exception 'unknown owner'; end if;
docs/reviews/spec-1f-a-codex-v4.md:1026:  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
docs/reviews/spec-1f-a-codex-v4.md:1029:  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
docs/reviews/spec-1f-a-codex-v4.md:1030:  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
docs/reviews/spec-1f-a-codex-v4.md:1032:  if v_anon then
docs/reviews/spec-1f-a-codex-v4.md:1036:      where p2.is_anonymous = false
docs/reviews/spec-1f-a-codex-v4.md:1052:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v4.md:1077:supabase/migrations/0011_cost_guardrails.sql:137:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v4.md:1087:supabase/migrations/0008_jobs_queue.sql:78:grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/spec-1f-a-codex-v4.md:1093:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/spec-1f-a-codex-v4.md:1403:supabase/migrations/0011_cost_guardrails.sql:101:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v4.md:1410:supabase/migrations/0011_cost_guardrails.sql:161:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v4.md:1473:   254	| B7b | Forged/foreign doc via direct RPC | authed/anon calls `reserve_serve_model` with a doc they don't own | definer derives owner from `auth.uid()` + verifies ownership → generic denial; no charge, no existence leak |
docs/reviews/spec-1f-a-codex-v4.md:1476:   257	| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v4.md:1479:   260	| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v4.md:1497:   278	  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v4.md:1539:   320	- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v4.md:1547:   328	   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v4.md:1577:    95	1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v4.md:1589:   107	   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v4.md:1649:   167	    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v4.md:1725:     9	grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/spec-1f-a-codex-v4.md:1736:    20	create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/spec-1f-a-codex-v4.md:1737:    21	  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/spec-1f-a-codex-v4.md:1741:    25	grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/spec-1f-a-codex-v4.md:1763:    47	-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/spec-1f-a-codex-v4.md:1772:    56	revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/spec-1f-a-codex-v4.md:1781:    65	  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/spec-1f-a-codex-v4.md:1817:   101	      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v4.md:1818:   102	      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/spec-1f-a-codex-v4.md:1853:   137	revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v4.md:2016:   Scenario: `reserve_serve_model` is granted to `anon, authenticated`. It verifies only `(playlist, video)` ownership, not that `artifacts.summaryMd.status === promoted` and the doc is actually servable. A caller can bypass `/api/html`, call the RPC for owned-but-unmaterialized/unpromoted video rows, and drain the global ledger without any possible model generation.
docs/reviews/spec-1f-a-codex-v4.md:2081:   Scenario: `reserve_serve_model` is granted to `anon, authenticated`. It verifies only `(playlist, video)` ownership, not that `artifacts.summaryMd.status === promoted` and the doc is actually servable. A caller can bypass `/api/html`, call the RPC for owned-but-unmaterialized/unpromoted video rows, and drain the global ledger without any possible model generation.
docs/reviews/task-cloud-pdf-10-review.md:8:- Ready → `<a target="_blank" rel="noopener noreferrer" onClick={onClose} className={itemClass}>`; not-ready → disabled `<span aria-disabled title="Finalizing…" className={mutedItemClass}>`.
docs/reviews/spec-1f-a-codex-v3.md:23:DESIGN CONTEXT: Stage 1F-a serves the summary rendered-HTML-doc from Supabase storage over a session/anon client (service_role forbidden). It renders on-serve and LAZILY materializes the magazine model on view (version/drift-gated). v3's key new element is Option A-lite for serve-side spend: ONE atomic, idempotent-per-(owner,doc,UTC-day) SECURITY DEFINER reserve RPC granted to authenticated,anon that (a) refuses over the daily cap, (b) is idempotent per (owner,doc,day) so reload-loops return "already charged", (c) reserves a fixed approximate estimate; backed by a per-(owner,doc,day) charge marker the RPC owns. Worker/enqueue_job UNCHANGED.
docs/reviews/spec-1f-a-codex-v3.md:27:2. SECURITY DEFINER leak. The RPC is granted to authenticated,anon and runs privileged over spend_ledger/guardrail_config. Can a caller pass a forged owner_id/doc to charge or read another owner's ledger, or probe the global cap state? Must it derive owner_id from auth.uid() internally (not a param)? Does the spec say so?
docs/reviews/spec-1f-a-codex-v3.md:30:5. Anything else: local render regression risk, drift-guard gaps, CSP completeness (default-src none / connect-src), storage write feasibility for anon.
docs/reviews/spec-1f-a-codex-v3.md:226:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v3.md:230:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v3.md:235:| D10 | **Serve-side spend governance = one atomic, idempotent-per-`(owner,doc,day)` `SECURITY DEFINER` reserve RPC (Option A-lite).** The RPC (granted to `authenticated, anon`), in a **single conditional UPDATE**: (a) refuses if the **daily cap** is over budget (→ 503 "at capacity"); (b) is **idempotent per `(owner_id, doc, UTC-day)`** — a repeat within the day returns "already charged" and does **not** re-reserve; (c) else reserves a **fixed approximate per-model estimate**. The model call honors `CLOUD_CAPS`. **No** per-account quota debit; **no** reconcile (over-reserve-on-failure is acceptable/conservative). | The per-`(owner,doc,day)` idempotency does three jobs at once — reserve, **dedup** (a reload-loop returns "already charged," no re-charge), and **abuse-bound** (a principal reserves at most once per owned doc/day; owned-doc-count is quota-bounded → no ledger-lever DoS). Keeps serve-side generation under the hard daily kill-switch (1D's principle) while staying approximate/simple (1D's posture). `SECURITY DEFINER` lets the session client invoke it without direct ledger grants, preserving D5. |
docs/reviews/spec-1f-a-codex-v3.md:255:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v3.md:267:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v3.md:310:  function granted to `authenticated, anon` that, in a **single conditional UPDATE**
docs/reviews/spec-1f-a-codex-v3.md:382:| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v3.md:385:| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v3.md:402:  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v3.md:446:- **Quota / Allowance** — the per-**account**, per-**job kind**, per-**month** ceiling on how many Jobs an owner may create (e.g. anon: 2 summary/mo, 0 dig; registered: N summary + 5 dig/mo). Consumed by an **atomic debit** inside the enqueue transaction (`usage_counters`, keyed by month so it refills implicitly). It bounds *per-user* volume; distinct from the **daily cap**, which bounds *global dollars*.
docs/reviews/spec-1f-a-codex-v3.md:449:- **Velocity limit** — a per-**IP** rate cap (Jobs/hour from one client IP) that bounds the anonymous-uid churn (clear cookies → fresh anon uid → fresh tiny quota) that per-account quota cannot catch. Enforced in the advisory **preflight**, not the authoritative debit.
docs/reviews/spec-1f-a-codex-v3.md:450:- **Tier** — the binary **anon vs registered** distinction (`profiles.is_anonymous`, set at provisioning and immutable) that selects the quota allowances. Stage 1 has no richer tier/role model.
docs/reviews/spec-1f-a-codex-v3.md:457:- **Principal** — the identity a storage operation acts on behalf of, plus the selector for which index it targets. Every storage operation takes an explicit Principal; there is no ownerless path. Locally it is a fixed single-user sentinel; in the cloud it is the authenticated (or anonymous) user.
docs/reviews/spec-1f-a-codex-v3.md:576:B9b says "missing model **behind a promoted summary** ⇒ repair-needed" — distinct from a plain 404. But steps 3-4 only do blob GETs; they never read `artifacts.summaryMd.status`. Without reading it, the serve path cannot distinguish (a) promoted-summary + missing-model (repair-needed / 409-class) from (b) a video that was never summarized / is mid-flight. The two must not collapse. **Fix:** make step 3/4 read `artifacts.summaryMd.status` from the row and gate the repair-needed vs 404 vs not-ready branches on it. This is the same missing read as H-2; spell it out as a first-class serve input.
docs/reviews/spec-1f-a-codex-v3.md:626:- **Invariant #2 (no cross-owner/unauth read) holds** *for the session-client path*: RLS `playlists_owner`/`videos_owner` (`0002`) + `storage.objects` first-segment == `auth.uid()` (`0007`) confine every row and blob read to the owner; a foreign/absent `playlistId` yields no row → identical 404 (no existence leak); the anon *session* uid is a real `auth.uid()` so the `anon` role in the storage policy is isolated identically; the blob key is server-constructed `{owner_id}/{playlist_key}/{key}` with `assertLogicalKey` rejecting `..`/leading-`/`/null, so no path traversal. The residual risks are *reliance on RLS* (M-4) and the *non-implementable* explicit video-row assert (H-1) — the guarantee itself is sound as long as the session client is used throughout and RLS stays enabled.
docs/reviews/spec-1f-a-codex-v3.md:896:**Headline verdict:** The pivot genuinely dissolves the v1 backfill / heal / coupling / recompute Blocker-cluster — that part is sound and well-reasoned. But it **relocated the money-path onto a session/anon client that has no authority to touch the daily-cap ledger**, and the spec never adds the DB surface that relocation requires. So the daily-cap gate (D10 / §4.2 / B6 / Success-Criterion 3) is **not implementable as written** — a new Blocker the pivot introduced. The single genuinely-good-news feasibility answer: the session/anon client *can* write+promote its own model blob (storage RLS allows it), so the lazy-materialize persistence itself is sound.
docs/reviews/spec-1f-a-codex-v3.md:904:| 1 | Can the session/anon client WRITE + promote the model blob? | **PASS** | `0007` policy `artifacts_owner_rw` is `for all to authenticated, anon using/with check (split_part(name,'/',1) = auth.uid()::text)`. Blob key is `{owner_id}/{playlist_key}/…` with `owner_id = auth.uid()`, so INSERT/UPDATE/DELETE + `move` (promote) all satisfy the owner-prefix check. Anon has a real `auth.uid()`. The persistence half of the lazy design works. |
docs/reviews/spec-1f-a-codex-v3.md:905:| 2 | Can the session client reserve against the daily cap? | **FAIL → Blocking (B-1)** | `spend_ledger` grants only `service_role`, `force row level security`, **no owner policy** → owner role denied all access. The only writer/reader are `enqueue_job` / `enqueue_preflight`, both `security invoker`, both gated `if auth.role() <> 'service_role' then raise`, both granted service_role-only. **No SECURITY DEFINER RPC callable by authenticated/anon touches `spend_ledger` or `guardrail_config`.** |
docs/reviews/spec-1f-a-codex-v3.md:914:### B-1 — The daily-cap reservation (D10 / §4.2 / B6) is NOT implementable by the session/anon serve client; D5 (no service_role) and D10 (reserve against the daily cap) are mutually unsatisfiable with the current DB surface — CORRECTNESS (feasibility) · **NEW, introduced by the pivot**
docs/reviews/spec-1f-a-codex-v3.md:918:The v1 money-path lived on the **enqueue/worker path**, where a `service_role` client already exists and `enqueue_job` (service_role-only, security-invoker) does the atomic daily-cap reserve. The pivot **moves the paid call to the serve path** and simultaneously mandates (D5) that the serve path use a **session/anon client, never service_role**. But the daily-cap machinery is reachable *only* by service_role:
docs/reviews/spec-1f-a-codex-v3.md:920:1. `spend_ledger`: `grant select, insert, update, delete … to service_role` and **nothing to anon/authenticated**; `enable` + `force row level security` with **no owner policy** ⇒ the owner/anon role can neither read nor write it. A session-client `update spend_ledger …` returns zero rows / permission-denied.
docs/reviews/spec-1f-a-codex-v3.md:921:2. `enqueue_job` (the existing reserve logic, `0011:111-115`): `language plpgsql security invoker`, first statement `if auth.role() <> 'service_role' then raise 'server only'`, and `grant execute … to service_role` only (explicitly `revoke … from anon, authenticated`). A session client calling it raises.
docs/reviews/spec-1f-a-codex-v3.md:925:So **every** primitive D10 depends on — read the cap, read the fixed estimate, atomically reserve — is closed to the session/anon client. §4.2's "reserve a fixed approximate per-model estimate against the daily cap (`spend_ledger`)" and B6's "day over budget → 503; no Gemini call" describe an operation the serve principal **has no grant to perform**. As written, the money kill-switch on the serve path either does nothing (silently skipped) or 500s — and if it's silently skipped, the paid Gemini call runs **ungated by any daily cap**, which is precisely the invariant Stage 1D exists to guarantee.
docs/reviews/spec-1f-a-codex-v3.md:927:The spec does not acknowledge that a **new SECURITY DEFINER RPC** (callable by `authenticated, anon`, running as definer to bypass RLS on `spend_ledger`/`guardrail_config`, doing check-and-reserve atomically) is *required* to make D10 real. §4.2 even asserts "the Stage 1D … guard are UNCHANGED … no migration," which is false: a serve-side reservation needs new DB surface (a migration + a new RPC + its GRANT). This is the load-bearing dependency of the whole lazy money-path and it is missing.
docs/reviews/spec-1f-a-codex-v3.md:929:**Fix (needs a decision + design):** Add an explicit `reserve_serve_spend(p_est_cents int)` (or similar) SECURITY DEFINER RPC that (a) reads `guardrail_config` for the cap, (b) does the same atomic `insert … on conflict do nothing` + guarded `update spend_ledger set reserved = reserved + est where reserved+actual+est <= cap` as `enqueue_job:111-115`, (c) is granted to `authenticated, anon`, (d) returns admitted/at-capacity. State the migration. Then **re-review it under the money-path trigger** — because handing owner-role clients a lever on the *global* ledger is itself a new attack surface (see H-1). Until this exists, B6 is untestable and Success-Criterion 3 ("the daily-cap gate refuses model generation when the day is over budget") cannot hold.
docs/reviews/spec-1f-a-codex-v3.md:935:### H-1 — The obvious fix for B-1 (an owner/anon-callable reserve RPC) is a new money-path attack surface: any client can drive the GLOBAL daily-cap ledger → cheap DoS on the kill-switch; the spec neither designs nor guards it — INTENT/DESIGN · **NEW**
docs/reviews/spec-1f-a-codex-v3.md:939:Once a `reserve_serve_spend`-style RPC is granted to `authenticated, anon`, **every serve request** can move `spend_ledger.reserved_cents`, which is the *global, all-owners* dollar kill-switch. Combined with D10's explicit **"no per-account quota debit"** on the serve path, there is **no per-owner bound** on how many reservations one principal can drive. Attack: an owner (or anon-churned uids) hammers `GET /api/html/{their-own-doc}` with cache-busting so the model keeps re-materializing (or targets docs whose model is absent/drift), each request reserving the fixed estimate, quickly exhausting the day's `daily_cap_cents` → **every other owner's serve materialization 503s "at capacity."** The serve reservation, like 1D's, is **never released and never reconciled**, so even *failed* materializations permanently inflate `reserved_cents` toward the cap. This is a denial-of-service on the money kill-switch itself, reachable by unprivileged clients — a materially different threat model than 1D's enqueue path (which is service_role-mediated *and* per-account quota-debited).
docs/reviews/spec-1f-a-codex-v3.md:1021:The pivot is the right call and genuinely closes the v1 Blocker-cluster. But it introduced **one new Blocker (B-1): the daily-cap money-gate cannot be enforced by the session/anon serve client** — `spend_ledger`, `enqueue_job`, `enqueue_preflight`, and `guardrail_config` are all service_role-only, and the spec adds no owner-callable reserve RPC while D5 forbids service_role. Fixing it requires new DB surface (a SECURITY DEFINER reserve RPC + migration), which then needs its own money-path re-review (H-1: owner-driven global-ledger DoS). Two more genuine gaps the pivot glossed: model-store helpers are local-principal-bound and non-staged (H-2), and MD-blob repair-needed behind a promoted status 500s (M-1). Do **not** treat convergence as reached: B-1 is a fresh Blocking, so another dual round is mandatory per dev-process.
docs/reviews/spec-1f-a-codex-v3.md:1043:### B-1 — The serve-side daily-cap gate is INFEASIBLE on the mandated session/anon client, and the only two fixes are both explicitly foreclosed by the spec (§4.2 "no migration" + D5 "never service-role"). [INTENT/DESIGN + CORRECTNESS]
docs/reviews/spec-1f-a-codex-v3.md:1045:**Claim attacked:** D5 ("session/anon-scoped client; **never service-role**"), D10 / §4.1 step 5 / §4.2
docs/reviews/spec-1f-a-codex-v3.md:1059:`spend_ledger` and `guardrail_config` have **RLS forced** and **NO policy for `authenticated`/`anon`** —
docs/reviews/spec-1f-a-codex-v3.md:1064:**Therefore, on the serve path with a session/anon client (D5):**
docs/reviews/spec-1f-a-codex-v3.md:1075:  service-confinement gate that B20 exists to test. A `service_role` key on a public GET route (anon-
docs/reviews/spec-1f-a-codex-v3.md:1078:  `authenticated, anon`, that internally checks+reserves against `spend_ledger` while *called by the
docs/reviews/spec-1f-a-codex-v3.md:1088:(check + atomic reserve, see H-2), grant it to `authenticated, anon`, and **retract §4.2's "no migration"**
docs/reviews/spec-1f-a-codex-v3.md:1121:   (velocity is enqueue-only, `enqueue_preflight`), a single anon owner can reload a stuck/failing doc
docs/reviews/spec-1f-a-codex-v3.md:1132:only materialize your own quota-bounded docs (2 for anon, 20 registered)" bound holds only if each doc
docs/reviews/spec-1f-a-codex-v3.md:1248:a session client — `storage.objects` policy `artifacts_owner_rw` is `for all to authenticated, anon` with
docs/reviews/spec-1f-a-codex-v3.md:1262:  owner; a foreign/absent `playlistId` yields no row ⇒ identical 404 (no existence leak, B10); the anon
docs/reviews/spec-1f-a-codex-v3.md:1263:  *session* uid is a real `auth.uid()`, so the `anon` storage policy isolates it identically (B9). This is
docs/reviews/spec-1f-a-codex-v3.md:1295:1. **Resolve B-1:** specify a `SECURITY DEFINER` serve-reservation RPC granted to `authenticated, anon`
docs/reviews/spec-1f-a-codex-v3.md:1337:- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v3.md:1345:   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v3.md:2413:supabase/migrations/0010_cancel_job_rowcount.sql:22:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/spec-1f-a-codex-v3.md:2419:supabase/migrations/0008_jobs_queue.sql:78:grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/spec-1f-a-codex-v3.md:2421:supabase/migrations/0008_jobs_queue.sql:92:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/spec-1f-a-codex-v3.md:2464:supabase/migrations/0011_cost_guardrails.sql:137:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v3.md:2478:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/spec-1f-a-codex-v3.md:2500:grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/spec-1f-a-codex-v3.md:2511:create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/spec-1f-a-codex-v3.md:2512:  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/spec-1f-a-codex-v3.md:2516:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/spec-1f-a-codex-v3.md:2538:-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/spec-1f-a-codex-v3.md:2547:revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/spec-1f-a-codex-v3.md:2556:  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/spec-1f-a-codex-v3.md:2592:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v3.md:2593:      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/spec-1f-a-codex-v3.md:2628:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v3.md:2643:  v_anon boolean; v_owner_created timestamptz;
docs/reviews/spec-1f-a-codex-v3.md:2652:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v3.md:2653:  if v_anon is null then raise exception 'unknown owner'; end if;
docs/reviews/spec-1f-a-codex-v3.md:2660:  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
docs/reviews/spec-1f-a-codex-v3.md:2663:  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
docs/reviews/spec-1f-a-codex-v3.md:2664:  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
docs/reviews/spec-1f-a-codex-v3.md:2666:  if v_anon then
docs/reviews/spec-1f-a-codex-v3.md:2670:      where p2.is_anonymous = false
docs/reviews/spec-1f-a-codex-v3.md:2686:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v3.md:2734:-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
docs/reviews/spec-1f-a-codex-v3.md:2735:-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
docs/reviews/spec-1f-a-codex-v3.md:2736:-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
docs/reviews/spec-1f-a-codex-v3.md:2738:  for all to authenticated, anon
docs/reviews/spec-1f-a-codex-v3.md:2851:  is_anonymous boolean not null default false,
docs/reviews/spec-1f-a-codex-v3.md:3425:    66	| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v3.md:3429:    70	| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v3.md:3434:    75	| D10 | **Serve-side spend governance = one atomic, idempotent-per-`(owner,doc,day)` `SECURITY DEFINER` reserve RPC (Option A-lite).** The RPC (granted to `authenticated, anon`), in a **single conditional UPDATE**: (a) refuses if the **daily cap** is over budget (→ 503 "at capacity"); (b) is **idempotent per `(owner_id, doc, UTC-day)`** — a repeat within the day returns "already charged" and does **not** re-reserve; (c) else reserves a **fixed approximate per-model estimate**. The model call honors `CLOUD_CAPS`. **No** per-account quota debit; **no** reconcile (over-reserve-on-failure is acceptable/conservative). | The per-`(owner,doc,day)` idempotency does three jobs at once — reserve, **dedup** (a reload-loop returns "already charged," no re-charge), and **abuse-bound** (a principal reserves at most once per owned doc/day; owned-doc-count is quota-bounded → no ledger-lever DoS). Keeps serve-side generation under the hard daily kill-switch (1D's principle) while staying approximate/simple (1D's posture). `SECURITY DEFINER` lets the session client invoke it without direct ledger grants, preserving D5. |
docs/reviews/spec-1f-a-codex-v3.md:3454:    95	1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v3.md:3466:   107	   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v3.md:3509:   150	  function granted to `authenticated, anon` that, in a **single conditional UPDATE**
docs/reviews/spec-1f-a-codex-v3.md:3586:   222	| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v3.md:3589:   225	| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v3.md:3606:   242	  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v3.md:3648:   284	- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v3.md:3656:   292	   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v3.md:3683:    20	create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/spec-1f-a-codex-v3.md:3684:    21	  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/spec-1f-a-codex-v3.md:3688:    25	grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/spec-1f-a-codex-v3.md:3710:    47	-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/spec-1f-a-codex-v3.md:3719:    56	revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/spec-1f-a-codex-v3.md:3728:    65	  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/spec-1f-a-codex-v3.md:3764:   101	      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v3.md:3765:   102	      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/spec-1f-a-codex-v3.md:4051:     9	-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
docs/reviews/spec-1f-a-codex-v3.md:4052:    10	-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
docs/reviews/spec-1f-a-codex-v3.md:4053:    11	-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
docs/reviews/spec-1f-a-codex-v3.md:4055:    13	  for all to authenticated, anon
docs/reviews/spec-1f-a-codex-v3.md:4151:**Failure scenario:** The spec says the RPC is for `(owner, doc, UTC-day)` but does not say whether `owner_id` is derived internally from `auth.uid()` or accepted as a parameter. If caller can pass `owner_id`/doc, an authenticated/anon user can:
docs/reviews/spec-1f-a-codex-v3.md:4285:**Failure scenario:** The spec says the RPC is for `(owner, doc, UTC-day)` but does not say whether `owner_id` is derived internally from `auth.uid()` or accepted as a parameter. If caller can pass `owner_id`/doc, an authenticated/anon user can:
docs/reviews/whole-branch-cloud-sync-v4-rereview-claude.md:85:3. `:357` the **local** model blob is deleted; `shareNeedsOwnerServe` is incremented (a false
docs/reviews/whole-branch-cloud-sync-v4-rereview-claude.md:108:(leave the receiver's model alone, do not increment `shareNeedsOwnerServe`) rather than deleting.
docs/reviews/plan-summary-section-timestamp-guarantee-v4-rereview.md:9:- **End-canonicalization repairs overlap:** `[## A ▶208–369, ## B missing, ## C ▶369–1000]` → allocator `[208,288,369]`; A **rewritten** to `208–288` (end = B's start, overlap gone), B inserted `288–369`, C `369–1000` byte-identical → kept. `parseSections(out)`: unique, strictly increasing, all `endSec > startSec`.
docs/reviews/plan-summary-section-timestamp-guarantee-v4-rereview.md:10:- **Byte-identity — no false negatives (Claude, proven):** both `resolveTranscriptTokens` (`parse.ts:179`) and the finalizer build lines via the *same* `timestampLine(start,end,videoId)`, and the *same* `videoId` flows to both in `generateSummary` (`gemini.ts:356` and `:491`). `timestampLine` pins `(start,end)` injectively (URL `t=${start}s` + `formatTimestamp` label), so `lines[slot] === canonical` ⟺ start & end both unchanged. A stale/overlapping end is always a byte-difference → always rewritten; a good line is always kept.
docs/reviews/plan-summary-section-timestamp-guarantee-v4-rereview.md:17:- **Medium (Codex): plan over-claimed "canonicalize doc-wide."** The fast-path returns early on `sectionStartsComplete` (checks `end>start`, not `end==next-start`), so an already-complete doc with overlapping ends from an off-prompt **literal** `▶` isn't canonicalized. Cosmetic (startSec uniqueness holds), and the pipeline never emits literal `▶` (model emits `[[TS]]` tokens; `resolveTranscriptTokens` produces canonical ends). → **Applied:** narrowed the plan's stated guarantee + added a round-4 scope note (this case is out of scope).
docs/reviews/plan-summary-section-timestamp-guarantee-v4-rereview.md:18:- **Low (both): test `videoId` mismatch** (`L` used `'v'`, finalizer called with `'vid'`) left the `===canonical → keep` branch uncovered in the incomplete path (production is fine). → **Applied:** `L` now uses `'vid'`.
docs/reviews/plan-summary-section-timestamp-guarantee-v4-rereview.md:19:- **Low (Claude): the `endSec>startSec` clause is redundant-but-defensive** for the current wiring — kept as cheap insurance against a future non-canonical producer.
docs/reviews/spec-dig-slide-autocrop-codex.md:35:**M2 — "walk markdown for asset refs" underspecified.** Regex can diverge from markdown-it. Use token parsing with the same containment rules; dedupe by canonical absolute path.
docs/reviews/task-cloud-pdf-6-review.md:6:Verified non-vacuously: **money invariant holds** — `loadSummaryForServe` has zero `resolveMagazineModel` reference; the `'promoted → ok WITHOUT resolving'` test asserts it's never called. **Error strings byte-match** `serveCloud` (route.ts:100-106) char-for-char, each with a dedicated test. **Gate matches** (committed→503 'not ready, retry'; non-promoted→404; mdKey `artifact?.key ?? video.summaryMd`; null blob→409 'repair needed'). **assertCloudSummaryMdKey before blobStore.get**; confirmed via grep this helper is its FIRST caller (route.ts doesn't call it yet) → safe for existing `${padSerial}_${slugify}.md` keys. **Bundle built once**, session-client (mock throws without it). `language` parity with route.ts:98.
docs/reviews/task-8-rls-isolation-review.md:7:1. **Seed proves real rows exist:** `seedPlaylistWithVideos` inserts via A's anon+JWT client and asserts `e1`/`e2` null → B's empty result is proof RLS hid real rows, not that seeding failed.
docs/reviews/task-8-rls-isolation-review.md:8:2. **Real RLS path:** all seeding + assertions use `signInAs` (anon key + user JWT); `adminClient` used only in `newUser` (createUser) — the permitted scope. No assertion uses BYPASSRLS.
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:25:1. **H1** — `decideCompanion` now takes a tri-state `SenderModelRead`; `unknown` ⇒ `{kind:'noop'}` (leave the receiver's model, do NOT set `shareNeedsOwnerServe`). VERIFY: is `readSenderModel` (`sync-run.ts`) correct in mapping a null envelope to `none` only when `sender.blob.provesAbsence`? On the LOCAL sender a null can also mean **corrupt/schema-invalid** (readModelEnvelope parses + validates) — is deleting the receiver's model right in that case, or should corrupt be distinguished from absent too? Does `noop` leave any inconsistency (receiver keeps a model whose `sourceMdHash` no longer matches the winning MD — trace the serve path's drift guard and say whether that is safe)?
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:307:    report shareNeedsOwnerServe. Proven-absent still deletes — correct on the local sender.
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:440:+3. `:357` the **local** model blob is deleted; `shareNeedsOwnerServe` is incremented (a false
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:463:+(leave the receiver's model alone, do not increment `shareNeedsOwnerServe`) rather than deleting.
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:795:+     shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:927:+           if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1231:+lib/cloud-sync/companion.ts:5:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1233:+lib/cloud-sync/companion.ts:16:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1303:+docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:318:  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1432:+tests/lib/cloud-sync/companion.test.ts:15:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1434:+tests/lib/cloud-sync/companion.test.ts:19:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1436:+tests/lib/cloud-sync/companion.test.ts:23:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1462:+lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1517:+lib/cloud-sync/sync-run.ts:348:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1528:+lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:2391:+docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:907:lib/cloud-sync/sync-run.ts:348:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:2609:+docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:902:   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:2704:+docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1670:   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:3099:+docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:381:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:3273:+docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1498:   332	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:3407:+docs/reviews/whole-branch-cloud-sync-codex.md:27:2. **mdHash is MD-BODY-only and CONSISTENT across tasks.** T1 canonicalizes (LF + one trailing newline + NFC). T4 stamps `sourceMdHash = mdHash(body)` at generate.ts + serve-doc.ts. T5 `deriveClassASignals` hashes the mdBody param. T8 `decideCompanion` compares `sourceMdHash === winnerMdHash`. T12 hashes bodies read via BlobStore. Verify NO path hashes `video.summaryMd` (the KEY/filename) instead of the body — a single key-hash anywhere breaks companion/reconcile equality.
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:3445:+docs/reviews/whole-branch-cloud-sync-codex.md:206:scripts/fix-duplicate-summaries.ts:9: *   2. Update index entry: summaryMd → canonical name
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:3710:+docs/reviews/whole-branch-cloud-sync-codex.md:1421:lib/cloud-sync/sync-run.ts:301:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4018:+docs/reviews/whole-branch-cloud-sync-codex.md:2735:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4060:+docs/reviews/whole-branch-cloud-sync-codex.md:3377:  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4159:+docs/reviews/whole-branch-cloud-sync-codex.md:5778:   301	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4211:+docs/reviews/whole-branch-cloud-sync-codex.md:6764:/bin/bash -lc 'rg -n "copyAdditiveVideo|missing.*blob|shareNeedsOwnerServe|deleteReceiverModel|companion|promoted.*blob|summaryMd.*null|baseline" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4308:+    48	  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4607:+   347	): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4608:+   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4614:+   354	    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4618:+   358	  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4680:+   420	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4812:+   552	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4849:+     5	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4860:+    16	  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6098:+    46	grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6233:+supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6319:+lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6334:+lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6443:+    34	/** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6623:+   214	  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6624:+   215	  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:6634:+   225	    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:7270:+    41	  /** RLS-scoped client (anon key + user JWT) — the ONLY client the code-under-test uses. */
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:7926:+tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8221:+docs/reviews/whole-branch-cloud-sync-codex.md:3377:  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8391:+tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8631:-  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8632:+  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8659:   return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8759: ): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8760:   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8767:     return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8770:+  // do NOT report shareNeedsOwnerServe (nothing is known to be stale about the share).
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8771:+  if (decision.kind === 'noop') return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8774:   return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8952:+    expect(r1.shareNeedsOwnerServe).toBe(0);                    // no false "share is stale" signal
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8959:+    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9069:     .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9074:     .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9080:     .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9216:    48	  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9536:   368	): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9537:   369	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9542:   374	    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9545:   377	  // do NOT report shareNeedsOwnerServe (nothing is known to be stale about the share).
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9546:   378	  if (decision.kind === 'noop') return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9549:   381	  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9625:   457	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9771:   603	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9805:    16	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9827:    38	  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:10731:     8	// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11109:supabase/migrations/0018_enqueue_dig.sql:86:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11146:supabase/migrations/0012_serve_model_charge.sql:100:grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;  -- owner derived internally
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11157:supabase/migrations/0005_reorder_helper.sql:25:revoke all on function reorder_videos(uuid, jsonb) from public, anon;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11167:supabase/migrations/0011_cost_guardrails.sql:137:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11181:supabase/migrations/0014_serve_owner_budget.sql:99:grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11185:supabase/migrations/0014_serve_owner_budget.sql:110:grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11191:supabase/migrations/0008_jobs_queue.sql:78:grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11246:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11285:supabase/migrations/0020_reservation_release.sql:264:grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11289:supabase/migrations/0003_provisioning.sql:6:  values (new.id, coalesce(new.is_anonymous, false));
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11362:/bin/bash -lc 'rg -n "B1|H1|H2|H3|unreadable|absent local|cloud MD body unreadable|playlist title|model intact|shareNeedsOwnerServe" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11366:tests/integration/cloud-sync/e2e.int.test.ts:236:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11367:tests/integration/cloud-sync/e2e.int.test.ts:246:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11389:tests/integration/cloud-sync/e2e.int.test.ts:684:    expect(r1.shareNeedsOwnerServe).toBe(0);                    // no false "share is stale" signal
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11390:tests/integration/cloud-sync/e2e.int.test.ts:691:    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11397:tests/lib/cloud-sync/companion.test.ts:16:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11398:tests/lib/cloud-sync/companion.test.ts:20:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11399:tests/lib/cloud-sync/companion.test.ts:24:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11761:    46	grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12028:   684	    expect(r1.shareNeedsOwnerServe).toBe(0);                    // no false "share is stale" signal
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12035:   691	    expect(r2.shareNeedsOwnerServe).toBe(0);
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12180:     4	 * Canonical MD-body normalization for cross-backend hashing (§5.2):
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12185:     9	export function canonicalizeMd(md: string): string {
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12191:    15	/** SHA-256 hex of the canonicalized MD body (§5.2). NOT over human fields. */
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12193:    17	  return createHash('sha256').update(canonicalizeMd(md), 'utf8').digest('hex');
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12462:   107	  (anonymous)** view of that specific video is not-ready until the owner serves (the share route is
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12492:   137	### 5.2 Canonical `mdHash` (rounds 1–3, 5)
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12493:   138	`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12702:docs/reviews/whole-branch-cloud-sync-v4-rereview-claude.md:85:3. `:357` the **local** model blob is deleted; `shareNeedsOwnerServe` is incremented (a false
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12727:docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:131:(`companionTransfer` additionally deleted the receiver's model envelope, `shareNeedsOwnerServe: 1`).
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12798:docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:318:  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12854:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:621:lib/cloud-sync/companion.ts:5:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12855:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:623:lib/cloud-sync/companion.ts:16:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12895:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:693:docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:318:  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12953:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:822:tests/lib/cloud-sync/companion.test.ts:15:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12955:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:824:tests/lib/cloud-sync/companion.test.ts:19:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:12957:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:826:tests/lib/cloud-sync/companion.test.ts:23:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13106:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:3601:docs/reviews/whole-branch-cloud-sync-codex.md:6764:/bin/bash -lc 'rg -n "copyAdditiveVideo|missing.*blob|shareNeedsOwnerServe|deleteReceiverModel|companion|promoted.*blob|summaryMd.*null|baseline" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13153:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4239:     5	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13154:docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:4250:    16	  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13334:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:25:1. **H1** — `decideCompanion` now takes a tri-state `SenderModelRead`; `unknown` ⇒ `{kind:'noop'}` (leave the receiver's model, do NOT set `shareNeedsOwnerServe`). VERIFY: is `readSenderModel` (`sync-run.ts`) correct in mapping a null envelope to `none` only when `sender.blob.provesAbsence`? On the LOCAL sender a null can also mean **corrupt/schema-invalid** (readModelEnvelope parses + validates) — is deleting the receiver's model right in that case, or should corrupt be distinguished from absent too? Does `noop` leave any inconsistency (receiver keeps a model whose `sourceMdHash` no longer matches the winning MD — trace the serve path's drift guard and say whether that is safe)?
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13352:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:307:    report shareNeedsOwnerServe. Proven-absent still deletes — correct on the local sender.
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13361:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:440:+3. `:357` the **local** model blob is deleted; `shareNeedsOwnerServe` is incremented (a false
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13412:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1231:+lib/cloud-sync/companion.ts:5:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13413:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1233:+lib/cloud-sync/companion.ts:16:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13453:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1303:+docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:318:  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13511:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1432:+tests/lib/cloud-sync/companion.test.ts:15:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13513:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1434:+tests/lib/cloud-sync/companion.test.ts:19:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13515:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:1436:+tests/lib/cloud-sync/companion.test.ts:23:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13664:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4211:+docs/reviews/whole-branch-cloud-sync-codex.md:6764:/bin/bash -lc 'rg -n "copyAdditiveVideo|missing.*blob|shareNeedsOwnerServe|deleteReceiverModel|companion|promoted.*blob|summaryMd.*null|baseline" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13711:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4849:+     5	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13712:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:4860:+    16	  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13893:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8631:-  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13894:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8632:+  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13898:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:8659:   return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13919:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9069:     .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13921:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9074:     .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13924:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9080:     .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13973:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9805:    16	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:13977:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:9827:    38	  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:14021:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11397:tests/lib/cloud-sync/companion.test.ts:16:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:14022:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11398:tests/lib/cloud-sync/companion.test.ts:20:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:14023:docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:11399:tests/lib/cloud-sync/companion.test.ts:24:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:14542:     9	-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:14543:    10	-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:14544:    11	-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
docs/reviews/whole-branch-cloud-sync-v5-rereview-codex.md:14546:    13	  for all to authenticated, anon
docs/reviews/spec-1f-a-claude-v7.md:14:**Two caveats keep this from being a clean rubber-stamp, both Medium.** (i) The spec's D10 rationale claims abuse is bounded to `K·est·(owned docs) ≪ daily cap` — that inequality holds robustly for **anon** (2 docs; anon can no longer trip the cap alone — a real win over v6) but is **not provably true for a registered free user at the full 20-doc quota**: `K·est·20 = 100·est`, which reaches/exceeds the `500¢` cap for any realistic `est` (≥5¢). So the v6-H-1 single-owner availability drain is **substantially narrowed, not eliminated**, for the top tier, and the "≪ daily cap" claim is over-stated (M-1). (ii) The M-1 staging fix lives at the wrong layer and leaves a residual concurrent-`promote` race that still 500s the loser on the Supabase backend (M-2/M-3 below). None of these are Blocking/High; they are refinements + a rationale correction. **Converged, modulo pinning `K·est·max_docs < daily_cap` and the putStaged/promote implementation contract.**
docs/reviews/spec-1f-a-claude-v7.md:22:| **H-1 (High): charge-per-attempt + TTL-reclaim removed v4's per-doc/day idempotency → a single owner drives the whole shared cap to `at_capacity` (global outage), each charge ≈$0 real Gemini (abort-after-reserve)** | New `attempt_count` on `serve_model_charge` + `K` (`guardrail_config`); step-4 `DO UPDATE … WHERE lease_expires_at<now() AND attempt_count<K`, incrementing per reclaim; `≥K` → `attempts_exhausted`. Caps one `(owner,doc,day)` at `K` charges. | **CORE CLOSED** — the *unbounded* charge path is gone (exactly `K` per doc/day, verified below). **Residual (M-1):** `K·est·(max owned docs)` is not `≪ cap` for a registered 20-doc user, so the single-owner *availability* drain is narrowed but not eliminated; the "≪ daily cap" rationale over-claims. Downgraded High→Medium (strictly weaker than v6, anon fully bounded, real-quota-gated, self-heals daily). |
docs/reviews/spec-1f-a-claude-v7.md:32:### M-1 — The D10 abuse bound `K·est·(owned docs) ≪ daily cap` is **not provably true for a registered free user at the 20-doc quota** (`100·est ≥ 500¢` for any realistic `est`): the v6-H-1 single-owner shared-cap *availability* drain is narrowed, not eliminated, and the spec's "trivially under the cap" rationale over-claims — INTENT/DESIGN · residual of v6-H-1 (High→Medium: strictly weaker than v6; anon fully bounded; real-quota-gated; self-heals daily)
docs/reviews/spec-1f-a-claude-v7.md:38:**Why this is Medium, not a resurrected High.** It is materially weaker than v6 on every axis: (i) **anon is now fully bounded** — `K·est·2 = 10·est`; at `est≤50¢` that's `≤500¢`, so an anon guest can **no longer trip the cap alone** (the exact actor v6-H-1's scenario centered on — genuine progress); (ii) each abuse charge requires an **owned promoted doc**, which cost real monthly quota + real Gemini to create (a registered attacker must first legitimately generate 20 summaries, admitted under `max_free_users`); (iii) it is **hard-bounded to `K`/doc/day** and **self-heals** next UTC day; (iv) the platform's **real** spend is still `≤ daily_cap` (this is availability, not cost). It is exactly the "shared-cap single-user drain" already scoped to **1G** (anon/user-abuse controls, §9). So it does not mandate another redesign round — but the **rationale is wrong** and must not ship as "trivially under the cap."
docs/reviews/spec-1f-a-claude-v7.md:68:**Where:** §4.1 step 4 maps `summaryMd.status===committed` → **503 "not ready, retry"**; §4.2 step 2 re-reads `promoted` inside the definer and returns coarse **`denied`** if not, which §4.1 step 5 maps → **404**. If a resummarize demotes between the route's step-4 read and the reserve's step-2 read, the same underlying "mid-refinalize" condition yields **503 via step 4** but **404 via reserve-denied** depending on timing. 404 tells the client "gone" (no retry) for a state that is actually transient.
docs/reviews/spec-1f-a-claude-v7.md:93:- **Invariants (a)/(b) from v6 still hold.** No release RPC exists; marker table stays force-RLS + `service_role`-only-write → no anon-callable void of a marker (a). The ledger has no decrement anywhere → monotonic within a UTC day, cannot net-to-zero; conditional `UPDATE … WHERE reserved+actual+est<=daily_cap` keeps total real spend ≤ cap (b). `K` narrows *who* can consume the cap and *how much per doc*; it does not touch the total-spend bound.
docs/reviews/spec-1f-a-claude-v7.md:104:- **M-1 (INTENT):** the D10 `K·est·(owned docs) ≪ daily cap` claim is **false for a registered 20-doc user** (`100·est ≥ 500¢`) — the single-owner *availability* drain is narrowed (anon fully bounded — a real win) but not eliminated. Pin `K·est·max_docs < daily_cap` **or** correct the rationale and record it as an accepted 1G-deferred risk.
docs/reviews/plan-stage-1c-supabase-adapters-codex.md:59:### 5. Storage RLS — anon Access and List Operations (Medium)
docs/reviews/plan-stage-1c-supabase-adapters-codex.md:65:**(a) `anon` access:** The policy grants `for all to authenticated, anon`. When a user is not signed in, `auth.uid()` is null, so `split_part(...) = null` is `UNKNOWN` (not true), denying writes. This is safe but the `anon` grant is noise if the app never supports anonymous sessions — remove it or document why it is intentional.
docs/reviews/plan-stage-1c-supabase-adapters-codex.md:145:| 5 | Storage RLS anon grant + list untested | Medium | T8, T12 | plan:717 |
docs/reviews/plan-stage-1c-supabase-adapters-codex.md:164:- Finding 5: Remove `anon` from the RLS policy or document intent; add a list-isolation test.
docs/reviews/spec-1f-a-claude-v3.md:12:**Headline verdict:** The v3 pivot to the A-lite `SECURITY DEFINER` RPC **genuinely dissolves the v2 Blocker** (the money-gate is now *reachable* by the session/anon client, and the "no migration" claim is retracted). But the new RPC has a **fresh Blocking hole**: the per-`(owner,doc,day)` idempotency bounds the **charge** but not the **Gemini call** — after a failed generate, every same-day reload re-invokes Gemini *uncharged*, and because `actual_cents` is never reconciled the daily-cap ledger cannot see that spend. So the daily cap does **not** bound actual dollars — defeating the exact invariant A-lite exists to provide (and the whole reason A-lite was chosen over Option D). Plus two Highs: the anon-granted definer's owner/doc trust model is unspecified (v2 H-1 global-cap DoS is **not** actually closed for direct RPC callers), and the "single conditional UPDATE" framing mis-describes a construct that must touch **two** tables (marker + ledger) with a specific arbiter + rollback ordering. **Not converged — another round is mandatory.**
docs/reviews/spec-1f-a-claude-v3.md:21:| 2 | SECURITY DEFINER owner/doc trust | **FAIL → High H-1** | Spec never says `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the doc is a real *owned* artifact. A direct anon RPC call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS persists. |
docs/reviews/spec-1f-a-claude-v3.md:44:Concurrency makes it worse without even needing failure: two tabs on one un-materialized doc → one charge, **two** Gemini calls (attack #1); N tabs → N calls, 1 charge. An anon owner (2-doc quota) can hold open dozens of concurrent requests per doc and/or reload a reliably-failing doc all day — **unbounded per-day Gemini spend, cap never moves.** §8 trigger-1 explicitly tells the reviewer to verify "the per-`(owner,doc,day)` idempotency genuinely bounds a reload-loop / concurrent miss (no unbounded re-charge)." It bounds re-*charge*; it does **not** bound re-*spend*. This is the hole.
docs/reviews/spec-1f-a-claude-v3.md:57:### H-1 — The RPC is granted to `authenticated, anon` and callable **directly** (PostgREST), but the spec never states that `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the `doc` is a real OWNED artifact; a direct call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS is NOT actually closed — INTENT/DESIGN · **NEW / carryover** · v2-traceback: redteam-H-1, verify-H-1 (claimed fixed by idempotency; the fix has a hole)
docs/reviews/spec-1f-a-claude-v3.md:59:**Where:** spec D10 ("granted to `authenticated, anon`"; "a principal reserves at most once per **owned** doc/day; **owned-doc-count is quota-bounded** → no ledger-lever DoS"), §4.2, §4.1 step 5 (verification lives in the serve *code*, before the RPC call — step 4 reads status/ownership, step 5 calls the RPC). Compare `enqueue_job` (`0011:69-70`): trusts `p_owner_id` **only because** it is `service_role`-gated (`if auth.role() <> 'service_role' then raise`) — a trusted server passes the resolved owner.
docs/reviews/spec-1f-a-claude-v3.md:61:Two unstated, load-bearing requirements for an **anon-granted** `SECURITY DEFINER` RPC:
docs/reviews/spec-1f-a-claude-v3.md:63:1. **Owner must be `auth.uid()`, never a caller param.** A definer runs privileged and bypasses RLS. `enqueue_job` can accept `p_owner_id` because no untrusted caller can reach it (service_role-only). The A-lite RPC is reachable by any anon/authenticated caller, so if it accepts an owner parameter, a caller can attribute charges/markers to arbitrary owners. The spec is silent on this. It **must** state `v_owner := auth.uid()` internally and ignore/reject any caller-supplied owner.
docs/reviews/spec-1f-a-claude-v3.md:65:2. **The definer itself must verify the `doc` is a real, owned, promoted artifact — the serve-code check in step 4 does NOT protect a direct RPC call.** D10's entire abuse-bound rests on "owned-doc-count is quota-bounded." But that premise holds only if the marker set is bounded to real owned docs. The serve route (§4.1) does verify the doc (reads the index, asserts `promoted`) *before* step 5 — but the RPC is a directly-invocable PostgREST endpoint granted to anon. An attacker skips the route entirely and calls the RPC with `doc = "x1", "x2", … "xN"` — each a fresh `(owner, doc, day)` → each **reserves `est` against the GLOBAL ledger** → the daily cap drains to zero → **every other owner's serve materialization 503s "at capacity."** The idempotency marker does not stop this: idempotency is *per doc*, and `doc` is attacker-chosen and unbounded. So v2 H-1 (owner-driven global-cap DoS) is **re-opened**, not closed — the "quota-bounded" claim is asserted without the mechanism that would make it true.
docs/reviews/spec-1f-a-claude-v3.md:67:**Fix (needs a decision + design):** State in D10/§4.2 that the definer (i) sets owner from `auth.uid()` internally; (ii) **validates `(owner, playlist, video)` against the caller's own real, promoted summary artifact inside the function** (or accepts only a server-signed/opaque doc handle it can re-derive), so the marker set is genuinely quota-bounded; and (iii) rejects a call for a doc the caller does not own. Without (ii) the "no ledger-lever DoS" claim is unsubstantiated. (Borderline Blocking — a single anon client can deny the money kill-switch to all tenants; kept at High only because the *intent* to bound by owned docs is stated, just not mechanized.)
docs/reviews/spec-1f-a-claude-v3.md:116:### L-3 — The RPC's tri-state result ("reserved" / "already charged" / "at capacity") lets any anon caller probe the GLOBAL daily-spend state — CORRECTNESS/nit
docs/reviews/spec-1f-a-claude-v3.md:125:| **daily-cap infeasible on session client** (verify-B-1 / redteam-B-1, Blocking) | D10 + §4.2: new `SECURITY DEFINER` RPC granted to `authenticated, anon`, touching `spend_ledger`/`guardrail_config` only inside the definer; **"no migration" explicitly retracted** ("this slice DOES include a small, self-contained migration"). | **FIXED (mechanism now exists & reachable)** — but the mechanism introduces B-1 (charge-once/generate-many) + H-1 (owner/doc trust) + H-2 (construct mis-stated). Feasibility dissolved; soundness not. |
docs/reviews/spec-1f-a-claude-v3.md:141:- **Blob write/promote as a session client is feasible** (`artifacts_owner_rw` `for all to authenticated, anon`, key is server-constructed `{auth.uid()}/{playlist_key}/…`, `promote` stays under the owner prefix). Don't drag service-role onto the blob path.
docs/reviews/spec-1f-a-claude-v3.md:142:- **Cross-owner / unauth isolation holds** (RLS `playlists_owner`/`videos_owner` + storage first-segment `= auth.uid()`; foreign/absent `playlistId` → identical 404; anon session uid is a real `auth.uid()`).
docs/reviews/spec-1f-a-claude-v3.md:150:The v3 A-lite RPC **fixes the v2 Blocker's feasibility** (the money-gate is now reachable by the session/anon client and the "no migration" error is retracted) and cleanly closes the ledger-reserve race for distinct docs. But it introduces **one new Blocking (B-1): the daily cap no longer bounds actual Gemini dollars** — the per-`(owner,doc,day)` idempotency dedups the charge while leaving generate calls unbounded (concurrent first-views fire N calls for one charge; failed-generate reloads re-call Gemini uncharged all day), and reconcile-off means the ledger never sees it. Two Highs compound it: the anon-granted definer's owner/doc trust model is unspecified so v2's global-cap DoS is **not** actually closed for direct RPC callers (H-1), and "single conditional UPDATE" mis-describes a two-table construct whose dedup arbiter (`INSERT … ON CONFLICT DO NOTHING RETURNING` on a UNIQUE `(owner,doc,day)` marker) + insert-then-reserve-then-rollback ordering is left unstated and is racy as written (H-2).
docs/reviews/task-1f-b-7-serve-route-codex.md:1:# Codex Adversarial Review — 1F-b Task 7 (anon /s/[token] route + money proof + guards)
docs/reviews/task-1f-b-7-serve-route-codex.md:7:For the committed route as written: the anonymous path does not import `serve-doc`, `gemini`, or `gemini-cost`; it calls `readFreshMagazineModel`, not `resolveMagazineModel`; it has no `.rpc(...)`; and the runtime money test’s `SupabaseClient.prototype.rpc` spy should intercept the route’s internally-created Supabase client. Confinement is not broadly weakened: the service-role allowlist is exact-path scoped to `app/api/jobs/route.ts` and `app/s/[token]/route.ts`. Isolation also holds in the current code: context resolution is owner-scoped and the blob store passed downstream is a runtime `{ get }` wrapper.
docs/reviews/task-1f-b-7-serve-route-codex.md:23:No evidence of a current money leak: valid, denial, not-ready, missing/corrupt MD, and in-flight revoke paths do not reach charging code. The main gaps are future-proofing of the static import guard and missing route-level coverage for stale-model and in-flight un-promote.
docs/reviews/stage-1e-a-durable-job-queue-spec-codex.md:10:2. **RLS does not authorize its own enqueue/cancel writes.** `SELECT`-only policy + `SECURITY INVOKER` insert → denied (convention 0002 is `for all ... with check`). Also parent §7 requires **anonymous guest jobs**, but spec grants only `authenticated` (0006 convention is `anon, authenticated, service_role`). **Fix:** `FOR SELECT` + `FOR INSERT WITH CHECK (owner_id=auth.uid())` + owner-scoped update for cancel; grant `anon` where guest enqueue is required.
docs/reviews/plan-2a-claude.md:14:- **M1 — T7 migration omits `revoke … from public; grant execute … to authenticated`** (`0007:43,73,97,121`; no blanket default-privilege revoke). Grant-less → **anon/public gets EXECUTE**; T7's §8 RLS review will flag it. Add the hardening to 0016.
docs/reviews/plan-1f-a-claude.md:167:  granted `authenticated, anon`; owner derived internally; no `release_serve_model` (v5 DoS absent).
docs/reviews/plan-1f-a-claude.md:169:  `K=5`, `daily_cap=500`; anon `2·5·6 = 60 ≤ 500·0.2 = 100`; registered residual documented as
docs/reviews/plan-stage-1d-claude.md:6:- **B1 (CRITICAL) — T2 drops the WRONG `enqueue_job` signature; the bypass stays OPEN.** `0009:15` already dropped the 0008 5-arg fn and created a **6-arg** `enqueue_job(uuid,text,int,text,text,jsonb)` still `grant execute to anon, authenticated` (0009:45-46). The plan's `drop ... (text,int,text,text,jsonb)` targets a non-existent signature (no-op) and the new **8-arg** fn is a different overload → **two overloads coexist; the 6-arg one stays client-callable** with no quota/reserve/duration/`max_attempts`. T2's bypass test only checks the 8-arg call → false green. *Fix: `drop function if exists enqueue_job(uuid,text,int,text,text,jsonb);` (the 0009 sig, removing its grants); add a test that the 6-arg client call is denied/absent.*
docs/reviews/task-1g-1-migration-codex.md:8:- Definer/search_path restated verbatim; no `drop function`; execute grants restated for authenticated, anon.
docs/reviews/task-1g-1-migration-codex.md:10:- serve_owner_budget schema correct: PK(owner_id,day), FK profiles on-delete-cascade, force-RLS, service-role-only grant, no anon/authenticated policy.
docs/reviews/task-1g-1-migration-codex.md:14:- **`serve-owner-budget.test.ts` lacks a direct client-lockdown negative-control for the new table.** A future migration accidentally granting `authenticated`/`anon` access (or a permissive policy) wouldn't be caught — current tests read/write via the service client only, and RPC success only proves definer writes work. Fix: mirror the existing `serve_model_charge` lockdown test — session-client select returns [], insert errors, update/delete affect no rows, service snapshot unchanged, catalog confirms `relforcerowsecurity = true`.
docs/reviews/cloud-publishing-architecture-spec-codex.md:12:- **B1 — RLS asserted, not specified (§7).** Doesn't define which tables are tenant-owned, which routes use anon/authenticated/service-role clients, or how worker writes avoid bypassing isolation. One missed service-role read on a list/browse/share path leaks another tenant's library. → Require a schema/policy matrix: every table, owner column, RLS forced status, allowed roles, CRUD policies, and which server paths may use service-role.
docs/reviews/cloud-publishing-architecture-spec-codex.md:20:- **H1 — Object-key namespacing insufficient (§7).** Keys from titles/ids/filenames without canonicalization → traversal / key confusion across the shared bucket. → Server-only canonical keys `user_id/document_id/version/type`; reject `..`, slashes in user-derived segments, Unicode confusables, absolute-path-like keys.
docs/reviews/cloud-publishing-architecture-spec-codex.md:22:- **H3 — Anonymous identity undecided (§7).** "cookie+IP (+optional anon session)" leaves the riskiest entrypoint's identity semantics open; cookie/IP metering trivially reset. → Make Supabase anonymous auth mandatory for guests; bind usage to anon uid + rate-limit dims; abuse controls for cookie clearing / IP rotation / account churn.
docs/reviews/task-9-integrity-reorder-review.md:1:# Task 9 Review — Integrity / deferrable reorder / anon isolation (0005 + integrity.test.ts)
docs/reviews/task-9-integrity-reorder-review.md:7:1. **reorder_videos security (Codex H7):** `security invoker` (caller RLS applies); ownership guard `if not exists (… owner_id=auth.uid() or auth.role()='service_role') then raise`; `revoke all … from public, anon`; `grant execute … to authenticated, service_role`. All four present — no SECURITY DEFINER, no security regression.
docs/reviews/task-9-integrity-reorder-review.md:9:3. **Integrity CHECK tests:** mismatched id AND missing id both inserted via owner's anon+JWT client → error asserted.
docs/reviews/task-9-integrity-reorder-review.md:10:4. **Anon isolation valid:** the other user's playlist is created via a real client; anon sees only its own row, not the other's.
docs/reviews/task-9-integrity-reorder-review.md:17:- **Important I2 (FIXED):** anon-isolation test now asserts the anon insert succeeded (`anonInsert.error` null) — closes a potential vacuous pass where both `mine` and `cross` could be empty.
docs/reviews/whole-branch-cloud-dig-deeper-frontend-v2-rereview.md:18:- Owner-assert + promoted-status gate still enforced upstream: `loadSummaryForServe` runs first and `if (!load.ok) return load` short-circuits — zero-dug 200 only reachable for an owned, promoted video; anon still gets pre-disabled `<span>` triggers (profiles fail-closed, after the loader).
docs/reviews/whole-branch-cloud-dig-deeper-frontend-v2-rereview.md:19:- `renderDigDeeperDoc({dug:[]})` → every section un-dug trigger (or anon span); no crash.
docs/reviews/whole-branch-cloud-dig-deeper-frontend-v2-rereview.md:24:- **Fix interaction / anon leak:** none. Zero-dug + owner → first-dig POST permitted; zero-dug + anon → disabled spans (not `a.dig-trigger`) → no fetch, no charge. Fail-closed profile path tested.
docs/reviews/whole-branch-cloud-dig-deeper-frontend-v2-rereview.md:26:- **Round-1 clean items hold:** the fix commit touched only csp.ts/route.ts/load-dig-for-serve.ts + tests — `nav.ts` (NAV_SCRIPT/DIG_CLOUD_SCRIPT) and `render-dig-deeper.ts` untouched → byte-identity, poll termination, inline↔helper parity, anon inert span all unchanged. Money invariant intact (zero-dug path does strictly *less* free I/O than the tested non-zero serve; render pure; integration asserts `spend_ledger` unchanged).
docs/reviews/task-2c-8-integration-review.md:5:**Claude (Spec ✅ / Quality Approved) — ran live + MUTATION-tested:** patched revoke_share_token to drop the owner filter → owner-isolation test FAILS (Expected false, Received true); restored → green. Proves non-vacuous. Behaviors: (1) create_share_token→{id,expires_at}, revoke→true, second revoke→false, error null; (2) owner isolation via a REAL second anon-key session client (signInAs userB, distinct auth.uid(), NOT service_role) → revoke of A's id →false; (3) summaryReady reflection via readIndex through per-user session client (real RLS) promoted→true / committed→false. Test-only (local diff empty); real 0013/0017 RPCs; reuses existing harness (adminClient/newUser/signInAs/seed). Live: share-summary-2c 3/3; full integration 334 pass/2 skip; tsc 0.
docs/reviews/spec-stage-1d-claude-review.md:19:- **M6 — Charge-on-failure + never-refund-quota + anon allowance=2 locks anon out after two transient failures with zero output** — harsh for a "validation demo," and (in the original release-money model) asymmetric. *Fix: confirm intended; consider refunding quota on infra-terminal (dead_letter/cancelled) or raise anon allowance.*
docs/reviews/spec-1f-b-claude-v1.md:9:- **Money invariant correct as-specified.** `resolveMagazineModel` DOES charge/generate (`serve-doc.ts:58` reserve RPC, `:80` generate). Share §4.3-step-4 uses `readModelEnvelope` + freshness gate + "not-ready, no generation" — touches neither reserve, Gemini, nor `spend_ledger`. D2/B18 hold as-specified (see H1 fragility).
docs/reviews/spec-1f-b-claude-v1.md:11:- **RLS/grants sound.** force-RLS + service_role-only mirrors `serve_model_charge` (`0012:15-17`); anon guests run in `authenticated` role so mint/revoke/list grants are correct.
docs/reviews/spec-1f-b-claude-v1.md:17:- **H1 — "never charges" is one careless import from breaking; no reusable read-only helper exists.** An implementer wiring the share route to `resolveMagazineModel` (charges `serve-doc.ts:58,80`) converts an anonymous route into an owner-money-spending one. §4.3 is prose with no structural guard. Compounding: `isFresh` is private (`serve-doc.ts:32`), forcing freshness-logic duplication that can drift. **Fix:** extract exported `readFreshModel(principal, base, blobStore, titles): MagazineModel | null` (readModelEnvelope + isFresh, no RPC/generate); both paths call it; export `isFresh`; spec forbids importing `resolveMagazineModel`/`reserve_serve_model`/`generateMagazineModel` in the share module; B18 asserts zero reserve calls + import grep/lint guard.
docs/reviews/spec-1f-b-claude-v1.md:22:- **M2 — a `GENERATOR_VERSION` bump silently breaks every live link until the owner re-views.** `isFresh` false → "not-ready" (B8) and D3 forbids generation → link broken indefinitely with no signal. **Fix:** acknowledge in §9, or heal-at-mint (owner-charged re-materialize).
docs/reviews/spec-1f-b-claude-v1.md:31:- **L4 — orphaned token rows** on un-promote/delete (404 at serve, fine); anon guest-owner reap cascades tokens, silently killing links.
docs/reviews/spec-1f-b-claude-v1.md:35:No Blocking; spec threads around the charging code and isolation/RLS is sound and matches merged precedent. **H1 is the finding to close before planning** (exported read-only helper + forbidden charging imports + zero-reserve assertion). H2 and M1 next. Re-review triggers (capability grant, anonymous access, second service_role surface, money-adjacent) mean these fixes warrant a re-review round.
docs/reviews/plan-playlist-picker-codex.md:54:selection, asserts the POST body carries the selected canonical URL.
docs/reviews/task-7-integration-harness-review.md:8:1. **`exec_sql` security:** `security definer` + `set search_path = ''`; `revoke all from public, anon, authenticated`; `grant execute to service_role` ONLY (not broader). Deliberate service_role-gated escape hatch.
docs/reviews/task-7-integration-harness-review.md:10:3. **`helpers/clients.ts`:** `adminClient` uses service key; `newUser` → `auth.admin.createUser({email_confirm:true})`; `signInAs` returns an **anon-key + user-JWT** client (real RLS path, NOT service) — satisfies Codex M4; `anonSession` → `signInAnonymously`.
docs/reviews/task-7-integration-harness-review.md:12:5. **`exec-sql-guard.test.ts`:** asserts BOTH user-JWT and anon clients error on `exec_sql`.
docs/reviews/task-7-integration-harness-review.md:17:1. **`setup.ts` guard omitted `NEXT_PUBLIC_SUPABASE_ANON_KEY`** (needed by `signInAs`/`anonSession`) → a hand-edited `.env.test.local` with a blank anon key would fail deep in a test, not at setup. → **FIXED**: added to the fail-fast condition.
docs/reviews/plan-1f-a-codex.md:29:   - grants: is the marker table service_role-only + force-RLS, and is reserve_serve_model granted authenticated,anon and owner-derived from auth.uid()?
docs/reviews/plan-1f-a-codex.md:30:2. **Test validity (TDD).** Do the RED tests actually fail for the RIGHT reason and assert real behavior (not vacuous/tautological)? Do they cover each cited behavior (B1-B21)? Any test that would pass against an empty implementation? Are integration tests correctly using the service client for setup and the session/anon client for the assertion (isolation)? Do serve E2E tests mock at the API/route level and gemini at lib boundary per dev-process?
docs/reviews/plan-1f-a-codex.md:44:This file is the canonical source for the workflow. It lives in the project repo so the process is reproducible by anyone who clones it.
docs/reviews/plan-1f-a-codex.md:305:**Architecture:** The serve route builds a **session/anon Supabase client** (never service_role), resolves `playlistId → playlist_key` with an owner assert, reads the summary MD blob under RLS, and renders on-serve. The magazine model is read from a principal-aware model store; on absence/drift the route calls `reserve_serve_model` (a definer RPC that leases single-flight, charges `magazine_est_cents` per attempt against the daily cap, and bounds attempts to `K` per `(owner,doc,UTC-day)`), then generates under output caps and stages→promotes the model. Rendered HTML carries a strict nonce CSP and `Cache-Control: private, no-store`. Shared render code (`render.ts`/`theme.ts`/`nav.ts`) gains an optional nonce so the local static-file path stays behaviorally identical.
docs/reviews/plan-1f-a-codex.md:313:- **Access is owner-scoped, any tier.** A Principal views only artifacts under its own `auth.uid()`; anon and registered owners use the identical code path (D1). Cross-owner viewing is 1F-b.
docs/reviews/plan-1f-a-codex.md:314:- **Session/anon Supabase client only on the serve path — NEVER service_role** (D5). The storage bundle is built from the session client; the confinement test (B20) enforces this.
docs/reviews/plan-1f-a-codex.md:317:- **Config invariant (pin before merge):** choose `K` (`max_serve_attempts`) and `magazine_est_cents` so `MAX_OWNED_PROMOTED_DOCS · K · magazine_est_cents ≤ daily_cap_cents · SAFETY_FRACTION` (SAFETY_FRACTION = 0.2). The anon bound (2 docs) is asserted hard; the registered residual is deferred to 1G (§4.2, §9).
docs/reviews/plan-1f-a-codex.md:363:  - RPC `reserve_serve_model(p_playlist_id uuid, p_video_id text) returns text` (`reserved | in_flight | attempts_exhausted | at_capacity | denied`), `security definer`, granted `authenticated, anon`.
docs/reviews/plan-1f-a-codex.md:372:import { adminClient, newUser, signInAs, anonSession } from './helpers/clients';
docs/reviews/plan-1f-a-codex.md:465:it('has no anon-callable release RPC', async () => {
docs/reviews/plan-1f-a-codex.md:466:  const { client } = await anonSession();
docs/reviews/plan-1f-a-codex.md:496:grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
docs/reviews/plan-1f-a-codex.md:634:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/plan-1f-a-codex.md:638:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/plan-1f-a-codex.md:643:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping per-account abuse to `K·est·(quota docs)` — negligible for anon (2 docs), a bounded *fraction* of the cap for a registered account (residual deferred to 1G, §9). Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
docs/reviews/plan-1f-a-codex.md:663:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/plan-1f-a-codex.md:675:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/plan-1f-a-codex.md:709:       per-account abuse ≤ `K·est·(quota docs)` — **negligible for anon** (2 docs); a
docs/reviews/plan-1f-a-codex.md:712:       abuse controls (§9). **No anon-callable release lever exists → the v5 instant DoS is
docs/reviews/plan-1f-a-codex.md:755:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/plan-1f-a-codex.md:792:  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
docs/reviews/plan-1f-a-codex.md:859:grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;  -- owner derived internally
docs/reviews/plan-1f-a-codex.md:1243:| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
docs/reviews/plan-1f-a-codex.md:1244:| B7e | Direct reclaim-loop can't trip the global cap at $0 | attacker loops `reserve_serve_model` on an owned doc without generating | `K`-cap → ≤ `K·est` per doc/day, ≤ `K·est·(quota docs)` per account — **anon fully bounded** (2 docs); a registered account's residual is a bounded *fraction* of cap (attributable, deferred to 1G) |
docs/reviews/plan-1f-a-codex.md:1248:| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/plan-1f-a-codex.md:1251:| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/plan-1f-a-codex.md:1269:  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/plan-1f-a-codex.md:1311:- **1G:** anon-abuse controls (CAPTCHA / rate-limit on anon sign-in) + **serve-side
docs/reviews/plan-1f-a-codex.md:1312:  per-account velocity/abuse controls** — the `K`-attempt bound closes the anon
docs/reviews/plan-1f-a-codex.md:1323:   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/plan-1f-a-codex.md:1331:   most `K`; anon fully bounded, registered residual deferred to 1G), needs no per-account
docs/reviews/plan-1f-a-codex.md:1349:grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/plan-1f-a-codex.md:1360:create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/plan-1f-a-codex.md:1361:  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/plan-1f-a-codex.md:1365:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/plan-1f-a-codex.md:1387:-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/plan-1f-a-codex.md:1396:revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/plan-1f-a-codex.md:1405:  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/plan-1f-a-codex.md:1441:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/plan-1f-a-codex.md:1442:      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/plan-1f-a-codex.md:1477:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/plan-1f-a-codex.md:1492:  v_anon boolean; v_owner_created timestamptz;
docs/reviews/plan-1f-a-codex.md:1501:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/plan-1f-a-codex.md:1502:  if v_anon is null then raise exception 'unknown owner'; end if;
docs/reviews/plan-1f-a-codex.md:1509:  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
docs/reviews/plan-1f-a-codex.md:1512:  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
docs/reviews/plan-1f-a-codex.md:1513:  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
docs/reviews/plan-1f-a-codex.md:1515:  if v_anon then
docs/reviews/plan-1f-a-codex.md:1519:      where p2.is_anonymous = false
docs/reviews/plan-1f-a-codex.md:1535:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/plan-1f-a-codex.md:2534:    if (status === 'committed') return json({ error: 'not ready, retry' }, 503); // finalizing window (B12)
docs/reviews/plan-1f-a-codex.md:2645:- Consumes: `guardrail_config` columns `daily_cap_cents`, `magazine_est_cents`, `max_serve_attempts` (Task 1); the anon summary quota (`quota_allowance` `is_anonymous=true, kind='summary'` → 2, from `0011`).
docs/reviews/plan-1f-a-codex.md:2656:const MAX_OWNED_PROMOTED_DOCS_ANON = 2; // anon summary quota (0011); the fully-bounded case asserted hard
docs/reviews/plan-1f-a-codex.md:2662:it('anon reclaim-loop worst case is within the daily-cap safety fraction (§4.2)', async () => {
docs/reviews/plan-1f-a-codex.md:2699:git commit -m "test(1f-a): serve-side config-invariant soundness (anon bounded; registered deferred to 1G)"
docs/reviews/plan-1f-a-codex.md:2748:| D1 owner-scoped any tier | 7 (auth.uid path, anon identical); 6/7 isolation tests |
docs/reviews/plan-1f-a-codex.md:2977:lib/supabase/server.ts:12:  return createServerClient(url, anonKey, {
docs/reviews/plan-1f-a-codex.md:3119:tests/integration/job-queue-producer.test.ts:3:import { adminClient, newUser, signInAs, anonSession, ensureGuardrailHeadroom } from './helpers/clients';
docs/reviews/plan-1f-a-codex.md:3145:tests/integration/integrity.test.ts:1:import { newUser, signInAs, anonSession } from './helpers/clients';
docs/reviews/plan-1f-a-codex.md:3159:tests/integration/cost-guardrails.test.ts:3:import { adminClient, anonSession, newUser, signInAs } from './helpers/clients';
docs/reviews/plan-1f-a-codex.md:3613:  const { url, anonKey } = getSupabaseEnv();
docs/reviews/plan-1f-a-codex.md:3614:  return createServerClient(url, anonKey, {
docs/reviews/plan-1f-a-codex.md:3717:const anon = () => process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
docs/reviews/plan-1f-a-codex.md:3734:/** RLS-scoped client authenticated as a real user (anon key + user JWT). */
docs/reviews/plan-1f-a-codex.md:3736:  const client = createClient(url(), anon(), { auth: { autoRefreshToken: false, persistSession: false } });
docs/reviews/plan-1f-a-codex.md:3742:export async function anonSession(): Promise<{ client: SupabaseClient; userId: string }> {
docs/reviews/plan-1f-a-codex.md:3743:  const client = createClient(url(), anon(), { auth: { autoRefreshToken: false, persistSession: false } });
docs/reviews/plan-1f-a-codex.md:3745:  if (error || !data.user) throw error ?? new Error('anon sign-in failed');
docs/reviews/plan-1f-a-codex.md:3762:  await svc.from('quota_allowance').update({ monthly: 100_000 }).match({ is_anonymous: false, kind: 'summary' });
docs/reviews/plan-1f-a-codex.md:3763:  await svc.from('quota_allowance').update({ monthly: 100_000 }).match({ is_anonymous: true, kind: 'summary' });
docs/reviews/plan-1f-a-codex.md:3844: *  migration 0011 — anon/authenticated execute was revoked). This is the ONE deliberately
docs/reviews/plan-1f-a-codex.md:4140:docs/reviews/spec-1f-a-claude-redteam-v2.md:53:  `authenticated, anon`, that internally checks+reserves against `spend_ledger` while *called by the
docs/reviews/plan-1f-a-codex.md:4141:docs/reviews/spec-1f-a-claude-redteam-v2.md:63:(check + atomic reserve, see H-2), grant it to `authenticated, anon`, and **retract §4.2's "no migration"**
docs/reviews/plan-1f-a-codex.md:4175:docs/reviews/spec-1f-a-claude-v3.md:12:**Headline verdict:** The v3 pivot to the A-lite `SECURITY DEFINER` RPC **genuinely dissolves the v2 Blocker** (the money-gate is now *reachable* by the session/anon client, and the "no migration" claim is retracted). But the new RPC has a **fresh Blocking hole**: the per-`(owner,doc,day)` idempotency bounds the **charge** but not the **Gemini call** — after a failed generate, every same-day reload re-invokes Gemini *uncharged*, and because `actual_cents` is never reconciled the daily-cap ledger cannot see that spend. So the daily cap does **not** bound actual dollars — defeating the exact invariant A-lite exists to provide (and the whole reason A-lite was chosen over Option D). Plus two Highs: the anon-granted definer's owner/doc trust model is unspecified (v2 H-1 global-cap DoS is **not** actually closed for direct RPC callers), and the "single conditional UPDATE" framing mis-describes a construct that must touch **two** tables (marker + ledger) with a specific arbiter + rollback ordering. **Not converged — another round is mandatory.**
docs/reviews/plan-1f-a-codex.md:4177:docs/reviews/spec-1f-a-claude-v3.md:21:| 2 | SECURITY DEFINER owner/doc trust | **FAIL → High H-1** | Spec never says `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the doc is a real *owned* artifact. A direct anon RPC call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS persists. |
docs/reviews/plan-1f-a-codex.md:4191:docs/reviews/spec-1f-a-claude-v3.md:57:### H-1 — The RPC is granted to `authenticated, anon` and callable **directly** (PostgREST), but the spec never states that `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the `doc` is a real OWNED artifact; a direct call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS is NOT actually closed — INTENT/DESIGN · **NEW / carryover** · v2-traceback: redteam-H-1, verify-H-1 (claimed fixed by idempotency; the fix has a hole)
docs/reviews/plan-1f-a-codex.md:4192:docs/reviews/spec-1f-a-claude-v3.md:59:**Where:** spec D10 ("granted to `authenticated, anon`"; "a principal reserves at most once per **owned** doc/day; **owned-doc-count is quota-bounded** → no ledger-lever DoS"), §4.2, §4.1 step 5 (verification lives in the serve *code*, before the RPC call — step 4 reads status/ownership, step 5 calls the RPC). Compare `enqueue_job` (`0011:69-70`): trusts `p_owner_id` **only because** it is `service_role`-gated (`if auth.role() <> 'service_role' then raise`) — a trusted server passes the resolved owner.
docs/reviews/plan-1f-a-codex.md:4193:docs/reviews/spec-1f-a-claude-v3.md:65:2. **The definer itself must verify the `doc` is a real, owned, promoted artifact — the serve-code check in step 4 does NOT protect a direct RPC call.** D10's entire abuse-bound rests on "owned-doc-count is quota-bounded." But that premise holds only if the marker set is bounded to real owned docs. The serve route (§4.1) does verify the doc (reads the index, asserts `promoted`) *before* step 5 — but the RPC is a directly-invocable PostgREST endpoint granted to anon. An attacker skips the route entirely and calls the RPC with `doc = "x1", "x2", … "xN"` — each a fresh `(owner, doc, day)` → each **reserves `est` against the GLOBAL ledger** → the daily cap drains to zero → **every other owner's serve materialization 503s "at capacity."** The idempotency marker does not stop this: idempotency is *per doc*, and `doc` is attacker-chosen and unbounded. So v2 H-1 (owner-driven global-cap DoS) is **re-opened**, not closed — the "quota-bounded" claim is asserted without the mechanism that would make it true.
docs/reviews/plan-1f-a-codex.md:4194:docs/reviews/spec-1f-a-claude-v3.md:67:**Fix (needs a decision + design):** State in D10/§4.2 that the definer (i) sets owner from `auth.uid()` internally; (ii) **validates `(owner, playlist, video)` against the caller's own real, promoted summary artifact inside the function** (or accepts only a server-signed/opaque doc handle it can re-derive), so the marker set is genuinely quota-bounded; and (iii) rejects a call for a doc the caller does not own. Without (ii) the "no ledger-lever DoS" claim is unsubstantiated. (Borderline Blocking — a single anon client can deny the money kill-switch to all tenants; kept at High only because the *intent* to bound by owned docs is stated, just not mechanized.)
docs/reviews/plan-1f-a-codex.md:4207:docs/reviews/spec-1f-a-claude-v3.md:116:### L-3 — The RPC's tri-state result ("reserved" / "already charged" / "at capacity") lets any anon caller probe the GLOBAL daily-spend state — CORRECTNESS/nit
docs/reviews/plan-1f-a-codex.md:4210:docs/reviews/spec-1f-a-claude-v3.md:125:| **daily-cap infeasible on session client** (verify-B-1 / redteam-B-1, Blocking) | D10 + §4.2: new `SECURITY DEFINER` RPC granted to `authenticated, anon`, touching `spend_ledger`/`guardrail_config` only inside the definer; **"no migration" explicitly retracted** ("this slice DOES include a small, self-contained migration"). | **FIXED (mechanism now exists & reachable)** — but the mechanism introduces B-1 (charge-once/generate-many) + H-1 (owner/doc trust) + H-2 (construct mis-stated). Feasibility dissolved; soundness not. |
docs/reviews/plan-1f-a-codex.md:4216:docs/reviews/spec-1f-a-claude-v3.md:150:The v3 A-lite RPC **fixes the v2 Blocker's feasibility** (the money-gate is now reachable by the session/anon client and the "no migration" error is retracted) and cleanly closes the ledger-reserve race for distinct docs. But it introduces **one new Blocking (B-1): the daily cap no longer bounds actual Gemini dollars** — the per-`(owner,doc,day)` idempotency dedups the charge while leaving generate calls unbounded (concurrent first-views fire N calls for one charge; failed-generate reloads re-call Gemini uncharged all day), and reconcile-off means the ledger never sees it. Two Highs compound it: the anon-granted definer's owner/doc trust model is unspecified so v2's global-cap DoS is **not** actually closed for direct RPC callers (H-1), and "single conditional UPDATE" mis-describes a two-table construct whose dedup arbiter (`INSERT … ON CONFLICT DO NOTHING RETURNING` on a UNIQUE `(owner,doc,day)` marker) + insert-then-reserve-then-rollback ordering is left unstated and is racy as written (H-2).
docs/reviews/plan-1f-a-codex.md:4224:docs/reviews/spec-1f-a-claude-v7.md:14:**Two caveats keep this from being a clean rubber-stamp, both Medium.** (i) The spec's D10 rationale claims abuse is bounded to `K·est·(owned docs) ≪ daily cap` — that inequality holds robustly for **anon** (2 docs; anon can no longer trip the cap alone — a real win over v6) but is **not provably true for a registered free user at the full 20-doc quota**: `K·est·20 = 100·est`, which reaches/exceeds the `500¢` cap for any realistic `est` (≥5¢). So the v6-H-1 single-owner availability drain is **substantially narrowed, not eliminated**, for the top tier, and the "≪ daily cap" claim is over-stated (M-1). (ii) The M-1 staging fix lives at the wrong layer and leaves a residual concurrent-`promote` race that still 500s the loser on the Supabase backend (M-2/M-3 below). None of these are Blocking/High; they are refinements + a rationale correction. **Converged, modulo pinning `K·est·max_docs < daily_cap` and the putStaged/promote implementation contract.**
docs/reviews/plan-1f-a-codex.md:4225:docs/reviews/spec-1f-a-claude-v7.md:22:| **H-1 (High): charge-per-attempt + TTL-reclaim removed v4's per-doc/day idempotency → a single owner drives the whole shared cap to `at_capacity` (global outage), each charge ≈$0 real Gemini (abort-after-reserve)** | New `attempt_count` on `serve_model_charge` + `K` (`guardrail_config`); step-4 `DO UPDATE … WHERE lease_expires_at<now() AND attempt_count<K`, incrementing per reclaim; `≥K` → `attempts_exhausted`. Caps one `(owner,doc,day)` at `K` charges. | **CORE CLOSED** — the *unbounded* charge path is gone (exactly `K` per doc/day, verified below). **Residual (M-1):** `K·est·(max owned docs)` is not `≪ cap` for a registered 20-doc user, so the single-owner *availability* drain is narrowed but not eliminated; the "≪ daily cap" rationale over-claims. Downgraded High→Medium (strictly weaker than v6, anon fully bounded, real-quota-gated, self-heals daily). |
docs/reviews/plan-1f-a-codex.md:4228:docs/reviews/spec-1f-a-claude-v7.md:32:### M-1 — The D10 abuse bound `K·est·(owned docs) ≪ daily cap` is **not provably true for a registered free user at the 20-doc quota** (`100·est ≥ 500¢` for any realistic `est`): the v6-H-1 single-owner shared-cap *availability* drain is narrowed, not eliminated, and the spec's "trivially under the cap" rationale over-claims — INTENT/DESIGN · residual of v6-H-1 (High→Medium: strictly weaker than v6; anon fully bounded; real-quota-gated; self-heals daily)
docs/reviews/plan-1f-a-codex.md:4231:docs/reviews/spec-1f-a-claude-v7.md:38:**Why this is Medium, not a resurrected High.** It is materially weaker than v6 on every axis: (i) **anon is now fully bounded** — `K·est·2 = 10·est`; at `est≤50¢` that's `≤500¢`, so an anon guest can **no longer trip the cap alone** (the exact actor v6-H-1's scenario centered on — genuine progress); (ii) each abuse charge requires an **owned promoted doc**, which cost real monthly quota + real Gemini to create (a registered attacker must first legitimately generate 20 summaries, admitted under `max_free_users`); (iii) it is **hard-bounded to `K`/doc/day** and **self-heals** next UTC day; (iv) the platform's **real** spend is still `≤ daily_cap` (this is availability, not cost). It is exactly the "shared-cap single-user drain" already scoped to **1G** (anon/user-abuse controls, §9). So it does not mandate another redesign round — but the **rationale is wrong** and must not ship as "trivially under the cap."
docs/reviews/plan-1f-a-codex.md:4238:docs/reviews/spec-1f-a-claude-v7.md:68:**Where:** §4.1 step 4 maps `summaryMd.status===committed` → **503 "not ready, retry"**; §4.2 step 2 re-reads `promoted` inside the definer and returns coarse **`denied`** if not, which §4.1 step 5 maps → **404**. If a resummarize demotes between the route's step-4 read and the reserve's step-2 read, the same underlying "mid-refinalize" condition yields **503 via step 4** but **404 via reserve-denied** depending on timing. 404 tells the client "gone" (no retry) for a state that is actually transient.
docs/reviews/plan-1f-a-codex.md:4250:docs/reviews/spec-1f-a-claude-v7.md:93:- **Invariants (a)/(b) from v6 still hold.** No release RPC exists; marker table stays force-RLS + `service_role`-only-write → no anon-callable void of a marker (a). The ledger has no decrement anywhere → monotonic within a UTC day, cannot net-to-zero; conditional `UPDATE … WHERE reserved+actual+est<=daily_cap` keeps total real spend ≤ cap (b). `K` narrows *who* can consume the cap and *how much per doc*; it does not touch the total-spend bound.
docs/reviews/plan-1f-a-codex.md:4277:docs/reviews/spec-1f-a-claude-v4.md:56:### M-2 — Marker table `serve_model_charge` grant/RLS lockdown is not stated; because the reserve RPC is granted to `anon, authenticated`, a client-writable marker table would allow pre-seeding a *foreign* owner's `(owner,doc,day)` marker → that owner's doc returns `already_charged` → 503, a cross-tenant availability brick — CORRECTNESS · **NEW table in v4** · v3-traceback: none (new surface)
docs/reviews/plan-1f-a-codex.md:4278:docs/reviews/spec-1f-a-claude-v4.md:60:**Scenario:** if the migration grants `insert` on `serve_model_charge` to `authenticated`/`anon` (or forgets to force RLS), a client `INSERT`s a marker with a *victim's* `owner_id` and a real `doc_key`. The victim's next view → `already_charged` → model absent → 503 "generating" for the rest of the day. Cross-tenant DoS, no cost to the attacker.
docs/reviews/plan-1f-a-codex.md:4284:docs/reviews/spec-1f-a-claude-v4.md:82:### L-3 — `reserve_serve_model`'s tri-state result lets any anon caller probe global daily-spend state (`at_capacity` leaks "day is over budget") — CORRECTNESS/nit · v3-traceback: Claude-v3 L-3, unchanged
docs/reviews/plan-1f-a-codex.md:4292:docs/reviews/spec-1f-a-claude-v6.md:5:**Reviewer mandate:** (1) confirm the v5 Blocking (B-1, the anon-callable `release_serve_model` → free/instant/repeatable $0 global-cap DoS) is *genuinely* gone, not reworded; (2) hunt for any NEW hole the lease redesign introduces; (3) verify the two invariants — (a) no anon-callable release, (b) charge-per-attempt keeps the daily cap the true bound and CANNOT net-to-zero.
docs/reviews/plan-1f-a-codex.md:4294:docs/reviews/spec-1f-a-claude-v6.md:12:**Headline verdict.** v6 **genuinely closes the v5 Blocking.** There is no `release_serve_model` RPC anywhere in v6; the only money-touching serve RPC is `reserve_serve_model`, and the marker table stays force-RLS + `service_role`-only-write, so **no anon-callable lever can delete/void a marker.** The v5 instant/free/single-doc/infinitely-repeatable ledger drain is unreachable — the per-`(owner,doc,day)` charge can only be repeated after the lease **expires** (`LEASE_TTL ≈ 180 s`), which is server-set and not client-shortenable. Invariant (a): **PASS.** Invariant (b): the ledger is **monotonic** — there is no decrement anywhere in v6, so it **cannot net-to-zero**, and the conditional-UPDATE arbiter keeps total spend ≤ `daily_cap`; **PASS.** The two Postgres-semantics questions the mandate raised (the `ON CONFLICT DO UPDATE … WHERE … RETURNING (xmax=0)` discriminator, and the lease-boundary double-reclaim) both resolve **correctly** (see "Claims that HOLD"). The cap-refusal rollback of a *reclaim* is also sound **provided the savepoint encloses step 4** (it does per the spec text; see L-1 for the test-phrasing gap).
docs/reviews/plan-1f-a-codex.md:4296:docs/reviews/spec-1f-a-claude-v6.md:22:| **B-1 (Blocking): `release_serve_model` is an anon-callable, unbounded lever — `reserve→release` loop on one owned promoted doc drives the GLOBAL cap to `at_capacity` for all tenants at $0 real spend, instant, repeatable** | v6 **deletes the release RPC entirely.** Recovery = the lease **expires** (`LEASE_TTL`); the next view **reclaims** (`ON CONFLICT DO UPDATE … WHERE lease_expires_at < now()`) and re-charges. No client-callable void of any marker exists. | **FIXED — genuinely.** The specific lever (delete-the-marker) is gone; idempotency can only be "reset" by real wall-clock time (`≥ TTL`), which is not a client lever. See H-1 for the residual the *new* mechanism opens. |
docs/reviews/plan-1f-a-codex.md:4308:docs/reviews/spec-1f-a-claude-v6.md:53:- **Alternative — accept + defer, but correct the spec.** If the team accepts the rate-limited single-user drain as within the shared-cap risk already scoped to **1G** (anon-abuse controls / rate-limiting, §9), then §4.1/§3 D10 **must** (a) drop the "each reclaim = a real Gemini call, never a $0 drain" framing — replace it with the true bound: "the charge commits at reserve, before generation, so a charge can cost ~$0 real Gemini; the actual bounds are the `LEASE_TTL` rate-limit per doc and the owner's promoted-doc count, and total spend ≤ `daily_cap`"; and (b) record "a single owner can drive the whole shared daily cap → serve-side outage for all tenants" as an explicit, owner-assigned **deferred 1G risk**. Silent over-claiming is not acceptable for a money-path spec.
docs/reviews/plan-1f-a-codex.md:4316:docs/reviews/spec-1f-a-claude-v6.md:78:**Why Medium:** no cost leak (denial → no charge), narrow window, but an unmapped RPC return in the money path is exactly what surfaces as a 500. **Fix:** enumerate it — reserve denial mid-serve → **503 "not ready, retry"** (same as the step-4 `committed` case), never 404/500; add a behavior row. (If reserve `RAISE`s the denial, the route must catch and map it, not bubble a 500.)
docs/reviews/plan-1f-a-codex.md:4319:docs/reviews/spec-1f-a-claude-v6.md:106:- **No anon-callable release lever (invariant a).** No `release_serve_model` exists; the marker table is force-RLS + `service_role`-only-write; a client cannot delete/void a marker. The v5 instant/free/single-doc/repeatable $0 drain is **unreachable**. Idempotency can only be re-armed by real wall-clock (`≥ TTL`), which is server-set. **B7d confirmed.**
docs/reviews/plan-1f-a-codex.md:4324:docs/reviews/spec-1f-a-claude-v6.md:118:**v6 genuinely closes the v5 Blocking** (invariant a: no anon-callable release; invariant b: monotonic ledger, cannot net-to-zero, cap is the true bound). The lease's Postgres semantics are correct — the `RETURNING`-row (not `xmax`) is the load-bearing single-flight signal, the boundary double-reclaim serializes to one generator, and the cap-refused-reclaim rollback restores the prior expired lease (no global brick).
docs/reviews/plan-1f-a-codex.md:4331:docs/reviews/spec-1f-a-claude-v5.md:12:**Headline verdict:** v5 genuinely closes three of the four round-4 findings — the at_capacity path now returns a status while voiding the marker (M-1 FIXED via savepoint/DELETE), the marker table is force-RLS + service_role-only-write so a client cannot forge a cross-tenant marker (M-2 FIXED), the definer verifies an **owned + promoted** summary before touching money (Codex-v4 promoted-in-definer FIXED), and the CSP gains `frame-ancestors`/`form-action 'none'` (L-2 FIXED). The v4 Claude H-1 brick is *addressed in spirit* by `release_serve_model`. **But the v4 H-1 fix itself introduces one new Blocking hole: `release_serve_model` is an unguarded, directly-callable, unbounded lever that voids the reserve idempotency.** Because the serve path runs on the session client (D5), release must be granted to `authenticated, anon`, so a direct PostgREST caller can loop `reserve → release → reserve → release …` on a **single owned, promoted doc**: each `reserve` adds `magazine_est` to the global `reserved_cents` (release deliberately does **not** reverse it), the marker is deleted each cycle so the next `reserve` is a fresh charge, and ~`daily_cap/est` cheap RPC-pairs drive the **global** daily cap to `at_capacity` for **all tenants** — **spending zero real Gemini dollars**. This converts round-4's *accepted* "an honest failing loop trips the cap at real spend" into a **free, instant, repeatable global availability DoS** on the money kill-switch, reachable by any anon guest with one promoted doc. The reserve-idempotency doc-count bound that v4 relied on to close the H-1/H-2 DoS is defeated by the release lever, and the spec does not acknowledge it. **Not converged — one more round to bound release/re-reserve per `(owner,doc,day)`.**
docs/reviews/plan-1f-a-codex.md:4702:  is_anonymous boolean not null default false,
docs/reviews/plan-1f-a-codex.md:4813:   The isolation “test” is prose only. This is one of the main auth/RLS success criteria, and the route-level test is fully mocked, so a fresh subagent could ship no real owner/anon/foreign integration proof.  
docs/reviews/plan-1f-a-codex.md:4814:   **Fix:** replace the prose block with real integration test code that seeds owner A/B and anon owner docs, calls the actual resolver/route path where feasible, and asserts own anon 200 plus foreign 404 under session clients.
docs/reviews/plan-1f-a-codex.md:4831:   The SQL sketch says `serve_model_charge` is service-role-only + FORCE RLS and `reserve_serve_model` is granted to `authenticated, anon`, but tests do not verify direct authenticated/anon table access is denied or that anon can execute the RPC with `auth.uid()` derived internally. A grant/RLS regression could pass most behavior tests.  
docs/reviews/plan-1f-a-codex.md:4832:   **Fix:** add integration assertions: session clients cannot select/insert/update/delete `serve_model_charge`; anon/authenticated can execute `reserve_serve_model`; service role can inspect cleanup state.
docs/reviews/plan-1f-a-codex.md:4876:   The isolation “test” is prose only. This is one of the main auth/RLS success criteria, and the route-level test is fully mocked, so a fresh subagent could ship no real owner/anon/foreign integration proof.  
docs/reviews/plan-1f-a-codex.md:4877:   **Fix:** replace the prose block with real integration test code that seeds owner A/B and anon owner docs, calls the actual resolver/route path where feasible, and asserts own anon 200 plus foreign 404 under session clients.
docs/reviews/plan-1f-a-codex.md:4894:   The SQL sketch says `serve_model_charge` is service-role-only + FORCE RLS and `reserve_serve_model` is granted to `authenticated, anon`, but tests do not verify direct authenticated/anon table access is denied or that anon can execute the RPC with `auth.uid()` derived internally. A grant/RLS regression could pass most behavior tests.  
docs/reviews/plan-1f-a-codex.md:4895:   **Fix:** add integration assertions: session clients cannot select/insert/update/delete `serve_model_charge`; anon/authenticated can execute `reserve_serve_model`; service role can inspect cleanup state.
docs/reviews/playlist-ux-spec-claude-review.md:114:Confirmed the gap is real: `SupabaseJobQueue.listByPlaylist` (`supabase-job-queue.ts:28`) filters `.eq('job_kind','summary')`, so the existing route cancel misses `dig`. The new `request_cancel_playlist_jobs` (§B4) is correct SQL: `security definer set search_path = public`; **no `job_kind` filter** (all kinds); `where playlist_id = p_playlist_id and owner_id = auth.uid() and status in ('queued','active')` — owner-guarded, terminal statuses (completed/failed/cancelled/dead_letter) untouched, queued→cancelled / active→flagged, mirroring `request_cancel_job` (`0010`); `revoke all … from public` + `grant execute … to authenticated, service_role` (drops `anon` vs `0010` — least-privilege, and the delete route is authenticated-only, so correct). No injection surface (single uuid param, no dynamic SQL). See the cancel × cascade × worker trace below — no worker error path.
docs/reviews/whole-branch-cloud-sync-codex.md:27:2. **mdHash is MD-BODY-only and CONSISTENT across tasks.** T1 canonicalizes (LF + one trailing newline + NFC). T4 stamps `sourceMdHash = mdHash(body)` at generate.ts + serve-doc.ts. T5 `deriveClassASignals` hashes the mdBody param. T8 `decideCompanion` compares `sourceMdHash === winnerMdHash`. T12 hashes bodies read via BlobStore. Verify NO path hashes `video.summaryMd` (the KEY/filename) instead of the body — a single key-hash anywhere breaks companion/reconcile equality.
docs/reviews/whole-branch-cloud-sync-codex.md:31:6. **NO SERVICE-ROLE on the sync path.** All cloud I/O under the authenticated user session (anon key + JWT), RLS `owner_id=auth.uid()`. `cloudP.id = deps.ownerId` (= auth.uid()), NOT a literal. The import-guard (`tests/lib/cloud-sync/import-guard.test.ts`) + `check-service-confinement.ts` (walks lib/cloud-sync + scripts) must make this non-vacuous. `scripts/cloud-sync.ts` must not transitively import the service-role key.
docs/reviews/whole-branch-cloud-sync-codex.md:139:docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:137:### 5.2 Canonical `mdHash` (rounds 1–3, 5)
docs/reviews/whole-branch-cloud-sync-codex.md:140:docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:138:`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
docs/reviews/whole-branch-cloud-sync-codex.md:180:supabase/config.toml:20:# `postgres` are reachable through the Data API roles (`anon`, `authenticated`, `service_role`)
docs/reviews/whole-branch-cloud-sync-codex.md:203:supabase/migrations/0010_cancel_job_rowcount.sql:22:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:206:scripts/fix-duplicate-summaries.ts:9: *   2. Update index entry: summaryMd → canonical name
docs/reviews/whole-branch-cloud-sync-codex.md:230:supabase/migrations/0006_grants.sql:3:-- the Data API roles (anon, authenticated, service_role) on new public tables. RLS only
docs/reviews/whole-branch-cloud-sync-codex.md:232:supabase/migrations/0006_grants.sql:16:grant select, insert, update, delete on public.profiles  to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:233:supabase/migrations/0006_grants.sql:17:grant select, insert, update, delete on public.playlists to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:234:supabase/migrations/0006_grants.sql:18:grant select, insert, update, delete on public.videos    to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:361:supabase/migrations/0018_enqueue_dig.sql:86:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/whole-branch-cloud-sync-codex.md:400:supabase/migrations/0012_serve_model_charge.sql:17:grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
docs/reviews/whole-branch-cloud-sync-codex.md:479:tests/integration/html-serve-isolation.test.ts:42:    .metadataStore.readIndex({ id: anonId, indexKey: anonDoc.playlistKey });
docs/reviews/whole-branch-cloud-sync-codex.md:513:tests/integration/enqueue-dig.test.ts:51:    const { error } = await enqueueDigRpc(anonId, playlistId, 'vid-dig-3', 132);
docs/reviews/whole-branch-cloud-sync-codex.md:516:tests/integration/job-queue-schema.test.ts:15:// T13: T2 revoked INSERT on `jobs` from anon/authenticated entirely (enqueue_job moved to an
docs/reviews/whole-branch-cloud-sync-codex.md:531:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:563:supabase/migrations/0014_serve_owner_budget.sql:110:grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:610:tests/integration/cost-guardrails.test.ts:302:  const anonRow = await svc.rpc('enqueue_preflight', { p_ip: '1.1.1.3', p_owner_id: anonId });
docs/reviews/whole-branch-cloud-sync-codex.md:669:tests/integration/job-queue-producer.test.ts:99:test('anon can enqueue its own job', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:674:supabase/migrations/0020_reservation_release.sql:10:-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
docs/reviews/whole-branch-cloud-sync-codex.md:813:supabase/migrations/0011_cost_guardrails.sql:25:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:833:supabase/migrations/0011_cost_guardrails.sql:137:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/whole-branch-cloud-sync-codex.md:842:supabase/migrations/0011_cost_guardrails.sql:195:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/whole-branch-cloud-sync-codex.md:848:tests/integration/reservation-release.test.ts:56:// Canonical enqueue helper — the REAL 8-arg enqueue_job signature (mirrors cancel-job-rpc.test.ts:17).
docs/reviews/whole-branch-cloud-sync-codex.md:1014:supabase/migrations/0008_jobs_queue.sql:78:grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:1016:supabase/migrations/0008_jobs_queue.sql:92:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:1127:supabase/migrations/0013_share_tokens.sql:18:grant select, insert, update, delete on share_tokens to service_role;  -- no anon/authenticated policy
docs/reviews/whole-branch-cloud-sync-codex.md:1236:tests/api/dig-cloud-route.test.ts:83:it('delegates to enqueueDig with isAnonymous: true for an anonymous profile, and surfaces its 403', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1306:supabase/migrations/0005_reorder_helper.sql:24:-- Codex H7: not callable by anon/PUBLIC by default; only authenticated + service_role.
docs/reviews/whole-branch-cloud-sync-codex.md:1421:lib/cloud-sync/sync-run.ts:301:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:1726:tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
docs/reviews/whole-branch-cloud-sync-codex.md:2023:tests/lib/dig/cloud/enqueue-dig-core.test.ts:47:it('403 for an anonymous user (never reads/enqueues)', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:2453:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
docs/reviews/whole-branch-cloud-sync-codex.md:2674:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-codex.md:2685:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-codex.md:2734:): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-codex.md:2735:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:2741:    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:2745:  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-codex.md:2784:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-codex.md:2870:          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-codex.md:2988: * Canonical MD-body normalization for cross-backend hashing (§5.2):
docs/reviews/whole-branch-cloud-sync-codex.md:2993:export function canonicalizeMd(md: string): string {
docs/reviews/whole-branch-cloud-sync-codex.md:2999:/** SHA-256 hex of the canonicalized MD body (§5.2). NOT over human fields. */
docs/reviews/whole-branch-cloud-sync-codex.md:3001:  return createHash('sha256').update(canonicalizeMd(md), 'utf8').digest('hex');
docs/reviews/whole-branch-cloud-sync-codex.md:3377:  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-codex.md:3396:  // IDENTITY COHERENCE (carried from serveCloud): `base` is the canonical, DB-persisted baseName,
docs/reviews/whole-branch-cloud-sync-codex.md:4381:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
docs/reviews/whole-branch-cloud-sync-codex.md:4541:-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
docs/reviews/whole-branch-cloud-sync-codex.md:5527: *  migration 0011 — anon/authenticated execute was revoked). This is one deliberately
docs/reviews/whole-branch-cloud-sync-codex.md:5530: *  Stage 1F-b (spec D4/D16): the anonymous `/s/[token]` share-serve route is the second (and,
docs/reviews/whole-branch-cloud-sync-codex.md:5532: *  session to scope RLS by for an anonymous visitor, so it uses a runtime `get`-only blob-store
docs/reviews/whole-branch-cloud-sync-codex.md:5537: *  app/api/jobs/route.ts's two-client split. The `profiles.is_anonymous` tenant read still goes
docs/reviews/whole-branch-cloud-sync-codex.md:5570:// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
docs/reviews/whole-branch-cloud-sync-codex.md:5777:   300	): Promise<{ shareNeedsOwnerServe: boolean }> {
docs/reviews/whole-branch-cloud-sync-codex.md:5778:   301	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:5784:   307	    return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:5788:   311	  return { shareNeedsOwnerServe: true };
docs/reviews/whole-branch-cloud-sync-codex.md:5827:   350	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
docs/reviews/whole-branch-cloud-sync-codex.md:6031:   436	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
docs/reviews/whole-branch-cloud-sync-codex.md:6125:  // references the raw env var name — any of these would defeat getAuthedClient's anon-key-only
docs/reviews/whole-branch-cloud-sync-codex.md:6764:/bin/bash -lc 'rg -n "copyAdditiveVideo|missing.*blob|shareNeedsOwnerServe|deleteReceiverModel|companion|promoted.*blob|summaryMd.*null|baseline" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-codex.md:6781:tests/integration/cloud-sync/e2e.int.test.ts:215:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:6783:tests/integration/cloud-sync/e2e.int.test.ts:225:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-codex.md:6796:tests/lib/cloud-sync/companion.test.ts:15:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-codex.md:6797:tests/lib/cloud-sync/companion.test.ts:19:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-codex.md:6798:tests/lib/cloud-sync/companion.test.ts:23:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
docs/reviews/whole-branch-cloud-sync-codex.md:6848:/** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
docs/reviews/whole-branch-cloud-sync-codex.md:7028:  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
docs/reviews/whole-branch-cloud-sync-codex.md:7029:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:7039:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
docs/reviews/whole-branch-cloud-sync-codex.md:7220:function anonClient(): SupabaseClient {
docs/reviews/whole-branch-cloud-sync-codex.md:7222:  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
docs/reviews/whole-branch-cloud-sync-codex.md:7223:  if (!url || !anon) throw new Error('NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY not set');
docs/reviews/whole-branch-cloud-sync-codex.md:7224:  return createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } });
docs/reviews/whole-branch-cloud-sync-codex.md:7285:  const c = anonClient();
docs/reviews/whole-branch-cloud-sync-codex.md:7298:  const c = anonClient();
docs/reviews/whole-branch-cloud-sync-codex.md:7309:  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
docs/reviews/whole-branch-cloud-sync-codex.md:7310:  return createClient(url, anon, {
docs/reviews/whole-branch-cloud-sync-codex.md:7436:  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
docs/reviews/whole-branch-cloud-sync-codex.md:7438:  if (!anonKey) throw new Error('Missing required env var: NEXT_PUBLIC_SUPABASE_ANON_KEY');
docs/reviews/whole-branch-cloud-sync-codex.md:7439:  return createBrowserClient(url, anonKey);
docs/reviews/whole-branch-cloud-sync-codex.md:7447:export function getSupabaseEnv(): { url: string; anonKey: string } {
docs/reviews/whole-branch-cloud-sync-codex.md:7450:    anonKey: required('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
docs/reviews/spec-1f-a-codex-v6.md:14:ADVERSARIAL spec reviewer — v6 CONFIRMING round. v5 had one Blocking (a free anon global-cap DoS via the release RPC). v6 replaces it with a LEASE-based single-flight and NO release RPC (user decision A+). Verify the DoS is genuinely gone and hunt for any NEW hole the lease design introduces. Concrete; find problems.
docs/reviews/spec-1f-a-codex-v6.md:20:- reserve RPC (SECURITY DEFINER, granted authenticated,anon): (1) v_owner:=auth.uid(); (2) verify owned + promoted summary; (3) doc_key/day; (4) INSERT ... (lease_expires_at=now()+LEASE_TTL) ON CONFLICT (owner,doc,day) DO UPDATE SET lease_expires_at=now()+LEASE_TTL WHERE serve_model_charge.lease_expires_at < now() RETURNING (xmax=0) AS inserted -> no row => in_flight (no charge); row => generator; (5) charge via conditional-UPDATE daily-cap arbiter; 0 rows => sub-block/EXCEPTION rolls back the lease claim => at_capacity. CHARGE EVERY ATTEMPT (first + each lease-reclaim). NO release RPC. On failure/abort: do nothing; lease expires (~180s); next view reclaims + regenerates + recharges.
docs/reviews/spec-1f-a-codex-v6.md:22:VERIFY: (a) is the v5 release-lever DoS genuinely gone (no anon-callable release exists)? (b) does charge-per-attempt keep the daily cap the true bound (a reload-loop on a failing doc climbs reserved_cents until at_capacity — bounded — and CANNOT net-to-zero)?
docs/reviews/spec-1f-a-codex-v6.md:46:> RPC** — which removes the v5 anon-DoS lever entirely. Needs one confirming review round (edge: an
docs/reviews/spec-1f-a-codex-v6.md:110:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v6.md:114:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v6.md:119:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned **and `promoted`** before touching money. Claims a short **generation lease** on the `serve_model_charge` marker and **charges `magazine_est_cents` per attempt**; returns coarse `reserved | in_flight | at_capacity`. **No release RPC** — a failed/aborted attempt just lets the lease expire; the next view reclaims + re-charges. No quota debit; reconcile deferred. | The lease makes generation single-flight (`in_flight` blocks a concurrent second call); charge-per-attempt keeps the **daily cap** the true bound on Gemini spend; **removing the release lever** closes the v5 $0-DoS. `auth.uid()`-internal + promoted-check blocks direct-PostgREST abuse. Keeps serve-side gen under the hard kill-switch while staying approximate. |
docs/reviews/spec-1f-a-codex-v6.md:139:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v6.md:151:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v6.md:181:       never the instant $0 ledger-drain of a release lever. **No anon-callable release
docs/reviews/spec-1f-a-codex-v6.md:217:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v6.md:249:  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
docs/reviews/spec-1f-a-codex-v6.md:313:**Headline verdict:** v5 genuinely closes three of the four round-4 findings — the at_capacity path now returns a status while voiding the marker (M-1 FIXED via savepoint/DELETE), the marker table is force-RLS + service_role-only-write so a client cannot forge a cross-tenant marker (M-2 FIXED), the definer verifies an **owned + promoted** summary before touching money (Codex-v4 promoted-in-definer FIXED), and the CSP gains `frame-ancestors`/`form-action 'none'` (L-2 FIXED). The v4 Claude H-1 brick is *addressed in spirit* by `release_serve_model`. **But the v4 H-1 fix itself introduces one new Blocking hole: `release_serve_model` is an unguarded, directly-callable, unbounded lever that voids the reserve idempotency.** Because the serve path runs on the session client (D5), release must be granted to `authenticated, anon`, so a direct PostgREST caller can loop `reserve → release → reserve → release …` on a **single owned, promoted doc**: each `reserve` adds `magazine_est` to the global `reserved_cents` (release deliberately does **not** reverse it), the marker is deleted each cycle so the next `reserve` is a fresh charge, and ~`daily_cap/est` cheap RPC-pairs drive the **global** daily cap to `at_capacity` for **all tenants** — **spending zero real Gemini dollars**. This converts round-4's *accepted* "an honest failing loop trips the cap at real spend" into a **free, instant, repeatable global availability DoS** on the money kill-switch, reachable by any anon guest with one promoted doc. The reserve-idempotency doc-count bound that v4 relied on to close the H-1/H-2 DoS is defeated by the release lever, and the spec does not acknowledge it. **Not converged — one more round to bound release/re-reserve per `(owner,doc,day)`.**
docs/reviews/spec-1f-a-codex-v6.md:332:**Where:** §4.1 step 5 ("a small definer `release_serve_model(p_playlist_id, p_video_id)` **deletes the marker** for `(auth.uid(), doc, today)` … it does **not** reverse the ledger reservation — the spent estimate stays counted, conservative"); D5 (serve path is on the **session client**, never service_role); §4.2 (reserve granted to `authenticated, anon`). Because the serve route runs on the session/anon client, `release_serve_model` — like `reserve_serve_model` — must be granted to `authenticated, anon` to be callable from the route, so it is reachable by a **direct PostgREST call**, exactly the surface the whole A-lite design is built to defend against.
docs/reviews/spec-1f-a-codex-v6.md:334:**Why the v4 doc-count bound fails.** v4 closed the global-cap DoS by arguing the marker/charge space is the caller's **owned + promoted** doc set, which is quota-bounded (anon: 2 summary/mo), so a caller can drive at most `(owned-promoted-docs × est)` into the ledger per day, and reserve is idempotent per `(owner,doc,day)` so a reload-loop cannot re-charge the same doc. **`release_serve_model` deletes the marker**, which is precisely the row that enforces that idempotency. After a delete, the next `reserve` for the same doc finds no conflict → fresh `INSERT` → charges `est` again. So the per-`(owner,doc,day)` cap of **one** charge becomes **unbounded** charges.
docs/reviews/spec-1f-a-codex-v6.md:343:**Why this is worse than the risk v4 accepted.** v4 explicitly accepted that a persistently-failing *honest* reload-loop trips the cap ("→ at_capacity for all — the kill-switch working"): but in that path **each retry actually calls Gemini** — the ledger climb reflects **real dollars spent**, the cap trips at a real `$5`, and each retry costs the attacker real generation latency. B-1 trips the identical global outage at **`$0` platform spend, instantly, for free, repeatable every day**, with no generation at all. The kill-switch is meant to stop the platform bleeding money; B-1 lets any anon user blow the global fuse without the platform spending a cent — pure denial, not cost control. This is a money-path/availability regression introduced by the exact change the round was for, so it blocks convergence.
docs/reviews/spec-1f-a-codex-v6.md:345:**Why Blocking (not High).** It is directly reachable by an anonymous caller, defeats the stage's central safety mechanism (Success-Criterion 3: "refuses generation when the day is over budget, idempotent per `(owner,doc,UTC-day)`, reload-loops don't re-charge" — B-1 makes reload-loops re-charge without bound), and resurrects a DoS two prior rounds were spent closing. The intent to *bound* re-reservation is not stated anywhere; release is described as an unconditional delete.
docs/reviews/spec-1f-a-codex-v6.md:350:- If the team decides B-1 is within the already-accepted "any owner can blow the global fuse" risk and wants to defer real hardening to **1G** (anon-abuse controls — CAPTCHA/rate-limit, explicitly scoped there in §9), then the spec **must explicitly acknowledge** that `release_serve_model` widens the free-DoS surface beyond the honest-loop case and record it as a deferred, owner-assigned risk — it currently claims the loop is "bounded by the daily cap" as if that were acceptable, without noting the `$0`-spend amplification. Silent is not an option for a money-path change.
docs/reviews/spec-1f-a-codex-v6.md:370:**Where:** `reserve_serve_model` has a numbered 5-step exact transaction in §4.2; `release_serve_model` appears only inline in §4.1 step 5 ("a small definer … deletes the marker for `(auth.uid(), doc, today)`"). Unspecified: (a) its grant (must be `authenticated, anon` to be callable on the session client — the crux of B-1, and worth stating explicitly so the DoS surface is visible in review); (b) whether it derives owner from `auth.uid()` internally and takes owner as never-a-param (§4.1 implies yes — "`(auth.uid(), doc, today)`" — good, but it is not pinned the way reserve step 1 is); (c) that it verifies nothing about ownership/promoted (it doesn't need to — the DELETE is `auth.uid()`-scoped so a foreign/absent doc is a harmless no-op — but this should be stated so a reviewer can see it is not a cross-tenant lever); (d) the explicit invariant "**never** touches `spend_ledger`/`usage_counters`" (ledger-not-reversed is stated; quota-untouched is implied since reserve does no quota debit).
docs/reviews/spec-1f-a-codex-v6.md:374:**Fix:** Give `release_serve_model` its own numbered exact-transaction block in §4.2 (owner from `auth.uid()`, `auth.uid()`-scoped DELETE, ledger/quota untouched, grant `authenticated, anon`, chosen bound from B-1), and a confinement test that a direct client cannot use it to escape the per-`(owner,doc,day)` charge bound.
docs/reviews/spec-1f-a-codex-v6.md:382:**Fix:** Enumerate the reserve-denial-mid-serve branch: reserve returning a generic denial (or a distinct "not-promoted-now" signal) → serve maps to **503 "not ready, retry"** (same as step-4 `committed`), never 404/500. Add a behavior row.
docs/reviews/spec-1f-a-codex-v6.md:419:v5 **genuinely fixes three of the four round-4 findings** (at_capacity status/rollback M-1, marker lockdown M-2, promoted-in-definer) and the CSP nit, and *addresses* the H-1 brick for the honest-failure path. **But the H-1 fix introduces a new Blocking hole (B-1): `release_serve_model` is an unguarded, directly-callable, unbounded lever** — because the serve path is on the session client, release must be granted to `authenticated, anon`, so a direct caller loops `reserve→release` on one owned promoted doc to drive the **global** daily cap to `at_capacity` for all tenants at **`$0` real spend**, defeating the reserve-idempotency doc-count bound that v4 relied on to close the global-cap DoS. Two Mediums pin the new surface (M-1 client-abort may never fire release, re-bricking the *main* H-1 case; M-2 release lacks the §4.2 exact-transaction/grant treatment reserve got) and one Medium is a reserve/serve promoted-check TOCTOU with an unmapped denial branch.
docs/reviews/spec-1f-a-codex-v6.md:447:- **Quota / Allowance** — the per-**account**, per-**job kind**, per-**month** ceiling on how many Jobs an owner may create (e.g. anon: 2 summary/mo, 0 dig; registered: N summary + 5 dig/mo). Consumed by an **atomic debit** inside the enqueue transaction (`usage_counters`, keyed by month so it refills implicitly). It bounds *per-user* volume; distinct from the **daily cap**, which bounds *global dollars*.
docs/reviews/spec-1f-a-codex-v6.md:450:- **Velocity limit** — a per-**IP** rate cap (Jobs/hour from one client IP) that bounds the anonymous-uid churn (clear cookies → fresh anon uid → fresh tiny quota) that per-account quota cannot catch. Enforced in the advisory **preflight**, not the authoritative debit.
docs/reviews/spec-1f-a-codex-v6.md:451:- **Tier** — the binary **anon vs registered** distinction (`profiles.is_anonymous`, set at provisioning and immutable) that selects the quota allowances. Stage 1 has no richer tier/role model.
docs/reviews/spec-1f-a-codex-v6.md:458:- **Principal** — the identity a storage operation acts on behalf of, plus the selector for which index it targets. Every storage operation takes an explicit Principal; there is no ownerless path. Locally it is a fixed single-user sentinel; in the cloud it is the authenticated (or anonymous) user.
docs/reviews/spec-1f-a-codex-v6.md:616:| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
docs/reviews/spec-1f-a-codex-v6.md:620:| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
docs/reviews/spec-1f-a-codex-v6.md:625:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` reserve RPC with an exact idempotent transaction (Option A-lite);** see §4.2 for the algorithm. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned before touching money. Returns coarse `reserved | already_charged | at_capacity`. **Only `reserved` triggers generation** — `already_charged` never regenerates (503-retry), which **single-flights** the paid call. Model call honors `CLOUD_CAPS`; fixed `magazine_est_cents`; no quota debit; reconcile deferred. | `unique(owner,doc,day)` + `ON CONFLICT` makes reserve+dedup+abuse-bound atomic; internal `auth.uid()` blocks forged-owner/ledger-probe via direct PostgREST; only-`reserved`-generates bounds paid *Gemini calls* (not just charges — the v3 gap both reviewers caught). Keeps serve-side gen under the hard daily kill-switch while staying approximate. |
docs/reviews/spec-1f-a-codex-v6.md:645:1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
docs/reviews/spec-1f-a-codex-v6.md:657:   - status `committed`/finalizing → **503** "not ready, retry" (a normal
docs/reviews/spec-1f-a-codex-v6.md:725:    granted to `authenticated, anon`, whose **exact transaction** is:
docs/reviews/spec-1f-a-codex-v6.md:782:grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
docs/reviews/spec-1f-a-codex-v6.md:793:create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
docs/reviews/spec-1f-a-codex-v6.md:794:  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
docs/reviews/spec-1f-a-codex-v6.md:798:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
docs/reviews/spec-1f-a-codex-v6.md:820:-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
docs/reviews/spec-1f-a-codex-v6.md:829:revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
docs/reviews/spec-1f-a-codex-v6.md:838:  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
docs/reviews/spec-1f-a-codex-v6.md:874:      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v6.md:875:      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
docs/reviews/spec-1f-a-codex-v6.md:910:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v6.md:925:  v_anon boolean; v_owner_created timestamptz;
docs/reviews/spec-1f-a-codex-v6.md:934:  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
docs/reviews/spec-1f-a-codex-v6.md:935:  if v_anon is null then raise exception 'unknown owner'; end if;
docs/reviews/spec-1f-a-codex-v6.md:942:  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
docs/reviews/spec-1f-a-codex-v6.md:945:  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
docs/reviews/spec-1f-a-codex-v6.md:946:  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
docs/reviews/spec-1f-a-codex-v6.md:948:  if v_anon then
docs/reviews/spec-1f-a-codex-v6.md:952:      where p2.is_anonymous = false
docs/reviews/spec-1f-a-codex-v6.md:968:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
docs/reviews/spec-1f-a-codex-v6.md:1001:| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
docs/reviews/spec-1f-a-codex-v6.md:1003:| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
docs/reviews/spec-1f-a-codex-v6.md:1006:| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
docs/reviews/spec-1f-a-codex-v6.md:1024:  B8–B9 (owner/anon), B12–B15 (status + param codes).
docs/reviews/spec-1f-a-codex-v6.md:1066:- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
docs/reviews/spec-1f-a-codex-v6.md:1074:   by its owner (any tier, incl. the anon guest who made it), rendered as the
docs/reviews/spec-1f-a-codex-v6.md:1896:-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
docs/reviews/spec-1f-a-codex-v6.md:1897:-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
docs/reviews/spec-1f-a-codex-v6.md:1898:-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
docs/reviews/spec-1f-a-codex-v6.md:1900:  for all to authenticated, anon
docs/reviews/spec-1f-a-codex-v6.md:2077:/bin/bash -lc 'rg -n "D10|lease|reserve_serve_model|No anon-callable|B7d|B6b|Cap refused|On generation failure|putStaged|stage|daily cap bounds" docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/spec-1f-a-codex-v6.md:2082:80:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned **and `promoted`** before touching money. Claims a short **generation lease** on the `serve_model_charge` marker and **charges `magazine_est_cents` per attempt**; returns coarse `reserved | in_flight | at_capacity`. **No release RPC** — a failed/aborted attempt just lets the lease expire; the next view reclaims + re-charges. No quota debit; reconcile deferred. | The lease makes generation single-flight (`in_flight` blocks a concurrent second call); charge-per-attempt keeps the **daily cap** the true bound on Gemini spend; **removing the release lever** closes the v5 $0-DoS. `auth.uid()`-internal + promoted-check blocks direct-PostgREST abuse. Keeps serve-side gen under the hard kill-switch while staying approximate. |
docs/reviews/spec-1f-a-codex-v6.md:2092:142:       never the instant $0 ledger-drain of a release lever. **No anon-callable release
docs/reviews/spec-1f-a-codex-v6.md:2108:210:  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
docs/reviews/spec-1f-a-codex-v6.md:2114:283:| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
docs/reviews/spec-1f-a-codex-v6.md:2172:Scenario: anon owner with one promoted doc calls `reserve_serve_model(D)` directly, receives `reserved`, but never calls the HTML route or Gemini. After `LEASE_TTL` expires, they call it again. Each reclaim charges `magazine_est_cents`; no release RPC is needed. This cannot exceed the daily cap, but it can still trip the global cap at `$0` real Gemini spend at roughly `LEASE_TTL * ceil(daily_cap / magazine_est)` per doc.
docs/reviews/spec-1f-a-codex-v6.md:2174:This is not the v5 instant `reserve → release` DoS; that specific lever is gone. But v6 has a slower charge-only fuse-blow because the anon-callable reserve RPC cannot prove a charged attempt actually ran generation.
docs/reviews/spec-1f-a-codex-v6.md:2223:Scenario: anon owner with one promoted doc calls `reserve_serve_model(D)` directly, receives `reserved`, but never calls the HTML route or Gemini. After `LEASE_TTL` expires, they call it again. Each reclaim charges `magazine_est_cents`; no release RPC is needed. This cannot exceed the daily cap, but it can still trip the global cap at `$0` real Gemini spend at roughly `LEASE_TTL * ceil(daily_cap / magazine_est)` per doc.
docs/reviews/spec-1f-a-codex-v6.md:2225:This is not the v5 instant `reserve → release` DoS; that specific lever is gone. But v6 has a slower charge-only fuse-blow because the anon-callable reserve RPC cannot prove a charged attempt actually ran generation.
docs/reviews/task-1f-b-2-migration-codex.md:9:None. The migration’s core security boundary holds: `share_tokens` is force-RLS, no anon/authenticated table grants or policies are added, DML is service-role-only, and all four RPCs are `SECURITY DEFINER set search_path = public` with `auth.uid()`-derived owner checks.
docs/reviews/whole-branch-1f-b.md:13:1. **Money bounded (central invariant).** The anon lifecycle `route → getShareServeContext → readFreshMagazineModel` has NO reachable edge to `reserve_serve_model` / `generateMagazineModel` / `spend_ledger` / `serve_model_charge`. `route.ts` makes no `.rpc` call; `serve.ts` is `.select()`-only; `read-model.ts` is a genuine generate-free leaf (returns `not_ready`→503 on absent/stale). Enforced by three independent legs: runtime `SupabaseClient.prototype.rpc` spy + byte-compared ledger snapshots across every branch (B18), static grep guard with planted subpath negative-controls (B18b), transitive import-graph walk (B18c).
docs/reviews/whole-branch-1f-b.md:22:- **Low (Codex) — FIXED before PR:** a corrupted persisted `artifacts.summaryMd.key` (e.g. `../x.md`) made `assertLogicalKey` throw during the anon blob read with no catch → 500 instead of coarse 404. Fixed: catch statusCode-400 (bad key) → `notFound()`, rethrow genuine infra errors. (share-route 12/12 still green after fix.)
docs/reviews/whole-branch-1f-b.md:29:- Spec §9 pre-existing 1G follow-ups still stand: anonymous-route rate-limit / HTML cache; GENERATOR_VERSION-bump staleness heal-at-mint; orphaned token-row GC; token-entropy-at-DB (owner-self-harm) residual.
docs/reviews/whole-branch-stage-1e-a-review.md:10:the load-bearing anon→profiles FK claim.
docs/reviews/whole-branch-stage-1e-a-review.md:18:- anon FK: 0003 trigger inserts a `profiles` row per `auth.users` insert → `owner_id references profiles(id)` holds for anonymous enqueue.
docs/reviews/reservation-release-spec-v2-codex.md:54:**Direction:** define table DDL, RLS posture, grants, and whether audit failure should ever abort. Recommended: service-role-readable only, no anon/authenticated grants, insertable by definer owner, and drop the claim that it survives transaction rollback.
docs/reviews/whole-branch-2a-review.md:12:- **Claude → READY, 0 Blocking/0 High; 1 Medium:** anonymous (`/try`) users are locked out of `/login` — the `/login`→`/` redirect fires for any user incl. anon, so an anon can't upgrade to a real account (open-signup product gap). **→ FIXED:** gate the redirect on `user && !user.is_anonymous` + test. (Claude missed the leaf-401 gap Codex caught — reconciled: Codex's finding governs, controller-verified.)
docs/reviews/whole-branch-2a-review.md:26:5. **Auth flow coherent:** middleware local-no-op short-circuit; `/login` public; cloud `/` gated → `/login`; `/api/*` JSON 401 before page-redirect; anon-provision + `/s`/`/try` preserved; callback `/library`→`/`; `/login` OAuth → callback `?next=/`. 401 from any cloud fetch (incl. sidebar) → `router.replace('/login')`.
docs/reviews/whole-branch-2a-review.md:30:- **`/s/[token]` anonymous share links** are `authenticated`-classified, so a logged-out share recipient is redirected to `/login` — i.e. **shared links may not open for logged-out users**. This is **pre-existing** and the spec explicitly declared `/s` gating out of scope (§2), and 2a does not change its classification — but it touches the already-shipped share feature. **Verify shared links work for anonymous recipients before launch** (likely needs `/s` added to the public/anon route category — a small follow-up).
docs/reviews/whole-branch-2a-review.md:38:**READY to merge.** Formal Codex + Claude whole-branch dual review complete; the one High (leaf-401) + one Medium (anon-`/login`) were fixed (commit `2ed1b2a`), and the `/s` anon-share bug fixed (commit `2957e24`). All money/RLS/isolation/local-preservation invariants verified across the 16 tasks by both passes. Post-fix: `tsc` 0, `npm test` 174 suites / 1879 tests. Remaining items are accepted backlog (cloud E2E harness; minor nits) — none block merge.
docs/reviews/plan-1f-a-claude-v2-rereview.md:16:| 3 | Grant/RLS lockdown tests | **CONFIRMED-FIXED** (but see Codex H-1 — vacuous update/delete) | force-RLS + service_role-only + no client policy; asserts session SELECT→`[]`, INSERT→error, svc row intact; anon CAN exec RPC; attacker `auth.uid()≠owner` → `denied`, no charge. |
docs/reviews/plan-1f-a-claude-v2-rereview.md:45:Task ordering/interfaces (`generateMagazineModel(sections,language,{caps,signal})`, `generateJson` 7-arg opts, `getStorageBundle({supabaseClient})` throws without it, `ResolveResult` exhaustive switch, status names consistent Task 1↔6↔7) — all tsc-compile at their commit **except HIGH-1/HIGH-2**. Integration tests use `svc` for SETUP + session/anon for ASSERTION; serve E2E mocks at route level, gemini at lib boundary; RPC tests hit a real reset DB. Confinement chain clean; live `check:confinement` OK.
docs/reviews/stage-1b-auth-rls-schema-spec-codex.md:10:- **B2 — Profile provisioning hand-waved → first-write race (§4/§5).** `owner_id` FKs `profiles` but no authoritative creation path. → `handle_new_user` trigger `after insert on auth.users` creates the `profiles` row (sets `is_anonymous`); single source, runs before any app write.
docs/reviews/stage-1b-auth-rls-schema-spec-codex.md:25:- **M2 — Middleware/session vague (§3/§4).** → Define route categories (public / anon-allowed / authenticated), callback cookie exchange, and how server components + route handlers get the refreshed session.
docs/reviews/stage-1b-auth-rls-schema-spec-codex.md:27:- **M4 — Test client role (§7).** → Data ops use the **anon key + the user's JWT**; admin API only for user creation.
docs/reviews/stage-1b-auth-rls-schema-spec-codex.md:30:- **L1 — `is_anonymous` user-writable (§5).** → Trigger-set; a `BEFORE UPDATE` guard prevents client changes; app never trusts a client-set value.
docs/reviews/stage-1b-auth-rls-schema-spec-codex.md:34:All Blocking/High addressed in spec v2; Mediums/Lows folded in. User decisions applied: list-id key, anon-upgrade out of scope, plain SQL migrations.
docs/reviews/plan-stage-1e-b-v2-rereview.md:26:- **Tasks 1–2 green:** `SupabaseJobQueue.enqueue` is the only non-test caller; all raw `enqueue()/enqueueScoped()` helpers + adapter callers enumerated in Task 1, each seeding a playlist; anon path feasible (anon session runs as `authenticated` with a real uid).
docs/reviews/reservation-release-spec-v3-claude.md:85:| H4 (`ledger_audit` RLS/grants + "insert cannot raise") | **Genuinely closed** for paths that insert (`fail_job`=service_role BYPASSRLS+grant; `settle_serve_model`=definer/postgres). Identity insert needs no sequence grant; force-RLS-no-policy blocks anon/authenticated. Airtight *for paths that can insert* (cancel paths can't — H-3). |
docs/reviews/task-1d-13-live-gates-migration-review.md:13:- **Denial tests preserved/strengthened:** canonical deny test (cost-guardrails.test.ts:231-250, all 3 vectors) UNTOUCHED. "insert for another owner" → now asserts exact `42501` grant revocation (stronger than the old WITH-CHECK). Cross-owner enqueue rejection covered by composite-FK `23503`. Idempotency legitimately re-expressed via RPC ON CONFLICT join (raw insert revoked).
docs/reviews/spec-1f-a-claude-v6.md:5:**Reviewer mandate:** (1) confirm the v5 Blocking (B-1, the anon-callable `release_serve_model` → free/instant/repeatable $0 global-cap DoS) is *genuinely* gone, not reworded; (2) hunt for any NEW hole the lease redesign introduces; (3) verify the two invariants — (a) no anon-callable release, (b) charge-per-attempt keeps the daily cap the true bound and CANNOT net-to-zero.
docs/reviews/spec-1f-a-claude-v6.md:12:**Headline verdict.** v6 **genuinely closes the v5 Blocking.** There is no `release_serve_model` RPC anywhere in v6; the only money-touching serve RPC is `reserve_serve_model`, and the marker table stays force-RLS + `service_role`-only-write, so **no anon-callable lever can delete/void a marker.** The v5 instant/free/single-doc/infinitely-repeatable ledger drain is unreachable — the per-`(owner,doc,day)` charge can only be repeated after the lease **expires** (`LEASE_TTL ≈ 180 s`), which is server-set and not client-shortenable. Invariant (a): **PASS.** Invariant (b): the ledger is **monotonic** — there is no decrement anywhere in v6, so it **cannot net-to-zero**, and the conditional-UPDATE arbiter keeps total spend ≤ `daily_cap`; **PASS.** The two Postgres-semantics questions the mandate raised (the `ON CONFLICT DO UPDATE … WHERE … RETURNING (xmax=0)` discriminator, and the lease-boundary double-reclaim) both resolve **correctly** (see "Claims that HOLD"). The cap-refusal rollback of a *reclaim* is also sound **provided the savepoint encloses step 4** (it does per the spec text; see L-1 for the test-phrasing gap).
docs/reviews/spec-1f-a-claude-v6.md:22:| **B-1 (Blocking): `release_serve_model` is an anon-callable, unbounded lever — `reserve→release` loop on one owned promoted doc drives the GLOBAL cap to `at_capacity` for all tenants at $0 real spend, instant, repeatable** | v6 **deletes the release RPC entirely.** Recovery = the lease **expires** (`LEASE_TTL`); the next view **reclaims** (`ON CONFLICT DO UPDATE … WHERE lease_expires_at < now()`) and re-charges. No client-callable void of any marker exists. | **FIXED — genuinely.** The specific lever (delete-the-marker) is gone; idempotency can only be "reset" by real wall-clock time (`≥ TTL`), which is not a client lever. See H-1 for the residual the *new* mechanism opens. |
docs/reviews/spec-1f-a-claude-v6.md:46:3. If `20 × est ≥ daily_cap` the cap trips in one round; otherwise wait `LEASE_TTL` (~180 s), re-view all 20 (leases expired → reclaim → 20 more charges), repeat. `daily_cap/est` charges trip the global cap in `⌈(cap/est)/20⌉ × TTL` — a few minutes for a registered user, ~50 min for a 2-doc anon.
docs/reviews/spec-1f-a-claude-v6.md:53:- **Alternative — accept + defer, but correct the spec.** If the team accepts the rate-limited single-user drain as within the shared-cap risk already scoped to **1G** (anon-abuse controls / rate-limiting, §9), then §4.1/§3 D10 **must** (a) drop the "each reclaim = a real Gemini call, never a $0 drain" framing — replace it with the true bound: "the charge commits at reserve, before generation, so a charge can cost ~$0 real Gemini; the actual bounds are the `LEASE_TTL` rate-limit per doc and the owner's promoted-doc count, and total spend ≤ `daily_cap`"; and (b) record "a single owner can drive the whole shared daily cap → serve-side outage for all tenants" as an explicit, owner-assigned **deferred 1G risk**. Silent over-claiming is not acceptable for a money-path spec.
docs/reviews/spec-1f-a-claude-v6.md:78:**Why Medium:** no cost leak (denial → no charge), narrow window, but an unmapped RPC return in the money path is exactly what surfaces as a 500. **Fix:** enumerate it — reserve denial mid-serve → **503 "not ready, retry"** (same as the step-4 `committed` case), never 404/500; add a behavior row. (If reserve `RAISE`s the denial, the route must catch and map it, not bubble a 500.)
docs/reviews/spec-1f-a-claude-v6.md:106:- **No anon-callable release lever (invariant a).** No `release_serve_model` exists; the marker table is force-RLS + `service_role`-only-write; a client cannot delete/void a marker. The v5 instant/free/single-doc/repeatable $0 drain is **unreachable**. Idempotency can only be re-armed by real wall-clock (`≥ TTL`), which is server-set. **B7d confirmed.**
docs/reviews/spec-1f-a-claude-v6.md:118:**v6 genuinely closes the v5 Blocking** (invariant a: no anon-callable release; invariant b: monotonic ledger, cannot net-to-zero, cap is the true bound). The lease's Postgres semantics are correct — the `RETURNING`-row (not `xmax`) is the load-bearing single-flight signal, the boundary double-reclaim serializes to one generator, and the cap-refused-reclaim rollback restores the prior expired lease (no global brick).
docs/reviews/plan-cloud-dig-deeper-frontend-v1-review.md:5:**Reviewers:** Codex (gpt-5.5, via coordinator) + independent Claude subagent — both adversarial, scoped to byte-identity-when-off, money invariant, poll correctness, anon handling, test validity, coverage.
docs/reviews/plan-cloud-dig-deeper-frontend-v1-review.md:16:| B1 | **Blocking** (both reviewers, + independently confirmed by coordinator) | Task 5 resolved `isAnonymous` from `user.is_anonymous` — unreliable AND fail-open. Anon pre-disable would silently never fire (behavior 7 / D3 violated); both its tests were vacuous. | POST route `app/api/videos/[id]/dig/[sectionId]/route.ts:47-61` has an explicit comment forbidding `user.is_anonymous`, reads `profiles.is_anonymous` fail-closed (`!== false`). | Task 5 now reads `profiles.is_anonymous` fail-closed (mirrors POST); `mockAuth` widened to stub `.from`; added a null-row fail-closed test. Spec §7.1 updated. |
docs/reviews/plan-cloud-dig-deeper-frontend-v1-review.md:29:**Cleared by both (no defect):** render byte-identity when `cloud` absent (`(readOnly||cloud)`, `cloud?.isAnonymous`, `nav` ternary all collapse identically); `NAV_SCRIPT` untouched (separate constant); money invariant (serve/poll are read-only, no `reserve_serve_model`/generation reachable, no auto-trigger on open); test paths under `testMatch`; delegate selector `a.dig-trigger[data-section]` excludes the anon `<span>`; poll terminates.
docs/reviews/spec-stage-1d-v4-rereview.md:21:- **M2 — `MAX_TRANSCRIBE_OUTPUT_TOKENS` converts some legit dense transcriptions into charged dead-letters (Claude).** ≤30-min fast-speech video whose transcript JSON exceeds 32 768 out → `MAX_TOKENS` → all 3 passes throw → `max_attempts=1` dead-letters, quota+reservation charged, no output; compounds anon lockout (open-q #4). *Fix: size the cap against the worst real 30-min transcript; document the failure mode in open-q #4.*
docs/reviews/task-10-middleware-callback-review.md:7:Classifier (public / anon-allowed / authenticated) + `needsAnonProvision`; session-refresh middleware with anon auto-provision on anon-allowed (Codex H1) and authenticated→`/` redirect; OAuth callback with code-exchange, error→`/auth/auth-error` (Codex M4), and `noStore()` Cache-Control (Task 5 carry-forward). Installed Next.js v15 matched the plan (`cookies()` async, `NextResponse` APIs). Additive only. Full suite 1505/1505; tsc clean; `check:confinement` OK.
docs/reviews/task-cloud-dig-1-review.md:8:- Anon test genuine: `anonSession()` (real `signInAnonymously()`) + asserts `is_anonymous===true` before PJ001. Idempotent-join asserts `usage_counters.used` stays 1 (real no-double-charge).
docs/reviews/task-cloud-dig-1-review.md:13:No reproduction drift beyond the guard; ON CONFLICT matches index; signature/grants intact; tests assert quota debit / no-double-charge / genuine anon; `cost-guardrails` edit preserves unsupported-kind coverage.
docs/reviews/spec-1f-a-claude-redteam-v1.md:68:B9b says "missing model **behind a promoted summary** ⇒ repair-needed" — distinct from a plain 404. But steps 3-4 only do blob GETs; they never read `artifacts.summaryMd.status`. Without reading it, the serve path cannot distinguish (a) promoted-summary + missing-model (repair-needed / 409-class) from (b) a video that was never summarized / is mid-flight. The two must not collapse. **Fix:** make step 3/4 read `artifacts.summaryMd.status` from the row and gate the repair-needed vs 404 vs not-ready branches on it. This is the same missing read as H-2; spell it out as a first-class serve input.
docs/reviews/spec-1f-a-claude-redteam-v1.md:118:- **Invariant #2 (no cross-owner/unauth read) holds** *for the session-client path*: RLS `playlists_owner`/`videos_owner` (`0002`) + `storage.objects` first-segment == `auth.uid()` (`0007`) confine every row and blob read to the owner; a foreign/absent `playlistId` yields no row → identical 404 (no existence leak); the anon *session* uid is a real `auth.uid()` so the `anon` role in the storage policy is isolated identically; the blob key is server-constructed `{owner_id}/{playlist_key}/{key}` with `assertLogicalKey` rejecting `..`/leading-`/`/null, so no path traversal. The residual risks are *reliance on RLS* (M-4) and the *non-implementable* explicit video-row assert (H-1) — the guarantee itself is sound as long as the session client is used throughout and RLS stays enabled.
docs/reviews/spec-1g-round2-rereview.md:7:- **Blocking/H2 (definer):** GENUINE. §6/D3 mandate full `security definer set search_path = public` verbatim + restated grants + no `drop function`; P17 asserts `prosecdef` + `proconfig search_path` + anon/auth executable-with-writes-succeeding (a true end-to-end proof — fails if it silently reverts to INVOKER).
docs/reviews/plan-cloud-dig-generation-codex.md:16:- **H3 (Codex High / Claude Med) — Anon detection via `user.is_anonymous`.** If `getUser()` doesn't surface it, a genuine anon → `isAnonymous=false` → RPC PJ001 → **429** not spec **403**. Authoritative source is `profiles.is_anonymous` (read by `enqueue_job` itself). Fix: derive anon from `profiles.is_anonymous` via the session client.

exec
/bin/bash -lc "nl -ba docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md | sed -n '90,120p' && nl -ba docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md | sed -n '300,350p' && nl -ba docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md | sed -n '2200,2220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    90	  (membership-archive via `reconcile_membership` `0007:60-71`, and a *manual* Archive toggle written via
    91	  `update_video_annotations`, `app/api/videos/[id]/archive/route.ts`); because the two are entangled on one
    92	  field, M2a does **not** sync `archived` (avoids the membership flip-flop) but must **keep it in the
    93	  annotation-writer allowlist** so the manual Archive button keeps working (round-v8 H-1). Cleanly
    94	  separating manual-archive (a syncable human preference) from membership-archive is **M2b**.
    95	- **Regenerable cache (never synced):** HTML, PDF (deterministic re-render from MD + model).
    96	
    97	### 4.2 Model JSON companion — sync-transfer only, serve path UNCHANGED (rounds 2–6)
    98	Model JSON is a **non-deterministic, `GENERATOR_VERSION`-axed, charged, self-healing cache** (Gemini
    99	transform; lazily regenerated on serve — `lib/html-doc/model-store.ts`, `read-model.ts`). It is **never**
   100	hash-compared. Its freshness is handled **only at sync-transfer**, leaving the serve path (`isFresh`,
   101	`readTitleStableModel`, the share route, the over-budget fallback) **unchanged** — because a global gate
   102	change would re-charge the whole corpus and dark-serve every share (round-4 BLK-1).
   103	- `ModelEnvelope` gains an OPTIONAL **`sourceMdHash`** — an **MD-body-only** digest (§5.2), set going
   104	  forward; the schema is **forward-tolerant** (old readers ignore the new key). Legacy envelopes lack it.
   105	- On a Class-A MD-transfer: ship the sender's model as a companion **iff** `sourceMdHash == mdHash(winning
   106	  MD)`; else **delete the receiver's model blob** (→ lazy regen on the **owner's** next serve). A **shared
   107	  (anonymous)** view of that specific video is not-ready until the owner serves (the share route is
   108	  generation-free — residual **R7**); sync reports these as `share_needs_owner_serve` (§7 step 6).
   109	
   110	---
   111	
   112	## 5. Reconcile model — two independent per-video reconciles
   113	
   114	Each video reconciles its **Class A** and **Class B** state **independently**: a format upgrade to the MD
   115	never touches the human fields, and a human-field edit never touches the MD. This is the core v7 change.
   116	
   117	### 5.1 Signals (per class)
   118	- **Class A:** `docVersion.major` (format — the decider), `mdHash` (the MD-body-only §5.2 digest = the
   119	  envelope's `sourceMdHash`), `mdGeneratedAt` (UTC, a **tie-break only**, never a quality signal), and
   120	  **`mdCorrectionsHash`** — the §5.2 hash of the `corrections` value this MD was generated/fixed from, for
   300	
   301	## 10. Testing
   302	- Boundary: mock cloud at the `MetadataStore`/`BlobStore` seam; integration = real local FS ↔ local-Supabase.
   303	- **Class A (corrections-currency + format):** higher-major wins over a newer-timestamp lower-major
   304	  (anti-recency); **a stale higher-major MD does NOT overwrite a corrections-current lower-major MD**
   305	  (round-v7 Codex-H1); neither-current → `needs_regen` (R8), **including identical stale MDs** (`mdHash`
   306	  equal must still flag `needs_regen` — round-v8 Codex-H1); same-major-different-prose unifies to the more
   307	  recent (both converge, no churn); **companion scalars (`ratings`/`tldr`/`tags`/…) are CARRIED verbatim with
   308	  the winning MD, NOT re-derived** — assert the 5 real ratings + tldr/takeaways/tags land intact on the
   309	  receiver (round-v8 B-1, `reconstructVideo` would corrupt them); `mdHash` cross-backend fixtures; a
   310	  human-field edit does **not** change `mdHash`.
   311	- **Class B (per-field merge):** a note edit on local + a score edit on cloud → **both survive**; a
   312	  **cleared** field is **not** resurrected (baseline-aware clear propagates, round-v7 H-2); same-field-both-
   313	  changed → newer **per-field** `annotationsEditedAt` wins (the B1 regression: an unrelated later field edit
   314	  must NOT flip a same-field tie); a **same-value re-add** (clear→re-type same text, newer ts) is NOT dropped
   315	  (round-v8 M-1, "changed" = `(value, ts)` pair); sync-applied write carries the **source's** timestamp, not
   316	  `now()` (H1); the **manual Archive button still writes** `archived` (allowlist keeps it — round-v8 H-1).
   317	- **Companion/serve (rounds 3–5):** non-synced legacy model still serves as today (no re-charge, share
   318	  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
   319	  reader (`.strict()` dropped) tolerates a `sourceMdHash`-bearing envelope.
   320	- **Stamping:** every MD-writer stamps `mdGeneratedAt`+`mdCorrectionsHash`; a human-field writer restamps
   321	  **only the changed field's** `annotationsEditedAt` and **only when a Class-B key is present** (a bare
   322	  `merge_video_data` MD-finalize does NOT bump it — round-v7 L-1); membership writers do not.
   323	- **Union hydration / atomicity / deletes / auth:** empty-local→full-hydrate; promote-then-commit crash never
   324	  advertises a hash for a missing blob nor advances the baseline; baseline-present remote-delete not
   325	  re-created; re-creation never calls the metered enqueue; no-session refusal; client `owner_id` rejected.
   326	
   327	---
   328	
   329	## 11. Accepted residuals (M2a)
   330	- **R1 — Class-B same-field concurrent edit:** newer **per-field** `annotationsEditedAt` wins; loser logged
   331	  (§8.1); loser-preservation is M2b. (Class A has no analogous loss — its variants are equivalent.)
   332	- **R2 — Baseline-less delete resurrection:** a fresh device / lost manifest may re-create a deleted entity;
   333	  full delete-safety = M2b tombstones.
   334	- **R3 — Replica-local conflict log** (§8.1); cross-replica surfacing is M2b.
   335	- **R4 — Clock skew (now minor):** only a Class-A same-format tie-break and a Class-B same-field tie lean on
   336	  clocks; the former is harmless (equivalent variants), the latter rare + logged. Format and 3-way merge
   337	  carry the real decisions, so skew is far less load-bearing than in the old single-class model.
   338	- **R5 — Companion re-charge, scoped to synced videos:** a synced MD with no verifiable-matching companion →
   339	  receiver regenerates the model on next serve (existing lazy path); bounded to synced videos, never the fleet.
   340	- **R7 — Synced+shared video:** its anonymous share is not-ready until an owner serve (the share route is
   341	  generation-free); scoped to synced+shared videos only; reported as `share_needs_owner_serve`.
   342	- **R8 — `needs_regen` (corrections/format skew):** if no replica has an MD reflecting the current
   343	  `corrections` at the top format (e.g. corrections applied on an older-code replica), sync keeps the best
   344	  available MD (corrections-current if any, else the highest format) but flags `needs_regen` — the summary is
   345	  the best that exists until the author regenerates on a top-format replica (which re-applies the surviving
   346	  `corrections`). Sync never fabricates a corrected MD; nothing is lost (the instruction survives, §5.4).
   347	- **R9 — Orphan-recovered scalars are lower-fidelity (round-v9).** A record rebuilt by `recoverOrphanedVideos`
   348	  (`reconstructVideo`, MD survived but the index was lost) carries flattened `ratings` + absent `tldr`/
   349	  `takeaways`/`tags` — the best derivable from the MD alone. If such a record wins Class A, sync carries those
   350	  lower-fidelity scalars (MD-consistent, not corrupt); a regenerate restores full fidelity. Rare + recoverable
  2200	**Interfaces:**
  2201	- Consumes: `runSync` + the full stack. No new production code — this task is coverage for the spec's §10 scenarios not already asserted in Tasks 3/4/12.
  2202	
  2203	**Enumerated scenarios (one test block each — §10):**
  2204	
  2205	| # | Scenario | Assertion |
  2206	|---|---|---|
  2207	| 1 | Class-A anti-recency: higher-major beats newer-timestamp lower-major | receiver ends with the higher-major MD |
  2208	| 2 | Stale higher-major does NOT overwrite corrections-current lower-major | corrections-current MD survives on both sides |
  2209	| 3 | Neither corrections-current (incl. identical stale MDs) → `needsRegen` counted | `report.needsRegen >= 1`, MD unchanged |
  2210	| 4 | Companion scalars carried verbatim (5 real ratings + tldr/takeaways/tags land) | receiver record's `ratings`/`tldr`/`takeaways`/`tags` == sender's, NOT reconstructed |
  2211	| 5 | Class-B: note edit local + score edit cloud → both survive | both fields present post-sync |
  2212	| 6 | Class-B cleared field not resurrected (baseline-aware) | cleared field stays absent |
  2213	| 7 | Synced+shared, model deleted → anon share not-ready until owner serve, counted | `report.shareNeedsOwnerServe >= 1` |
  2214	| 8 | Additive create never calls the metered enqueue | `spend_ledger` unchanged (assert total) |
  2215	| 9 | Baseline-present remote-delete not re-created | video absent locally after sync, `report.removed` counts it |
  2216	| 10 | No-session refusal / client `owner_id` rejected | `getAuthedClient` throws; RLS rejects a forged owner |
  2217	| 11 | Additive create excludes regenerable cache | copied receiver record has `summaryHtml`/PDF null/absent (§5.6) |
  2218	| 12 | Backfilled Class-B conflict preserved across TWO runs | legacy divergent `personalNote` (both backfilled); run sync **twice** | both runs log+skip; NEITHER side overwritten; baseline not falsely advanced (round-3 H2, §5.5) |
  2219	| 13 | Additive create of a summary-less video | one-sided video with `summaryMd = null` | metadata copied; no blob `put`; no throw (round-3 M-R3-1) |
  2220	| 14 | Additive PUBLISH is servable | local→cloud additive create of a promoted summary | cloud row has `artifacts.summaryMd.status = 'promoted'` → `summaryReady` true (round-3 L-R3-3) |

exec
/bin/bash -lc "nl -ba app/s/[token]/route.ts | sed -n '1,115p' && nl -ba lib/share/serve.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import { createServiceClient } from '@/lib/supabase/service';
     2	import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
     3	import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
     4	import { getShareServeContext } from '@/lib/share/serve';
     5	import { readFreshMagazineModel } from '@/lib/html-doc/read-model';
     6	import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
     7	import { renderMagazineHtml } from '@/lib/html-doc/render';
     8	import { generateNonce, buildSummaryCsp } from '@/lib/html-doc/csp';
     9	import { fileResponse } from '@/lib/html-doc/file-response';
    10	import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';
    11	
    12	// MONEY GUARD (spec B18b, enforced by tests/lib/share/import-guard.test.ts): this module must not
    13	// import the charging/serve-doc modules and must never call the reserve RPC. (Do NOT name the
    14	// forbidden symbols here — the guard greps this file's raw text for them.)
    15	
    16	const TOKEN_RE = /^[A-Za-z0-9_-]{43}$/; // 32-byte base64url
    17	// Both denial responses carry no-store/no-referrer too (Claude Minor): a cached 503 for a
    18	// valid-but-not-ready token could otherwise outlive the model being materialized, and a cached
    19	// 404 could leak token-existence timing via a shared/browser cache.
    20	const DENIAL_HEADERS = { 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' };
    21	const notFound = () => new Response(JSON.stringify({ error: 'not found' }), { status: 404, headers: DENIAL_HEADERS });
    22	const notReady = () => new Response(JSON.stringify({ error: 'not ready, retry shortly' }), { status: 503, headers: DENIAL_HEADERS });
    23	const notFound400 = () => new Response(JSON.stringify({ error: 'invalid format' }), { status: 400, headers: DENIAL_HEADERS });
    24	
    25	export async function GET(_req: Request, { params }: { params: Promise<{ token: string }> }) {
    26	  // format/download are parsed and validated FIRST — token-independent (no oracle): a bad `format`
    27	  // on a malformed token must 400 without ever reaching TOKEN_RE/DB, so it can't leak
    28	  // token-existence timing (D12/B-L2). `getAll` (not `.get`) so a duplicate ?format=… param can't
    29	  // bypass validation via the first value (the owner route shipped exactly this bypass — Codex
    30	  // Medium — fixed here from the start).
    31	  const { searchParams } = new URL(_req.url);
    32	  const formatValues = searchParams.getAll('format');
    33	  const format = formatValues.length === 0 ? 'html' : formatValues[0];
    34	  if (formatValues.length > 1 || (format !== 'html' && format !== 'md')) return notFound400();
    35	  const download = searchParams.get('download') === '1';
    36	
    37	  const { token } = await params;
    38	  if (!TOKEN_RE.test(token)) return notFound(); // malformed → before any DB call (B11)
    39	
    40	  const svc = createServiceClient();
    41	  const ctx = await getShareServeContext(svc, token);
    42	  if ('status' in ctx) return notFound(); // denied — expired/revoked/unknown/unpromoted (B9/B10/B12/B13)
    43	
    44	  const fullStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
    45	  const readOnly: ReadOnlyBlobStore = { get: fullStore.get.bind(fullStore) }; // runtime get-only (D16)
    46	  const principal = { id: ctx.ownerId, indexKey: ctx.playlistKey };
    47	
    48	  let mdBytes;
    49	  try {
    50	    mdBytes = await readOnly.get(principal, ctx.mdKey);
    51	  } catch (err) {
    52	    // Corrupt persisted mdKey (e.g. a path-traversal key) makes the store's assertLogicalKey throw
    53	    // (statusCode 400). Coarse 404, never a 500 leak (B13b). A genuine infra error (no 400) still
    54	    // surfaces as 500 rather than being masked as "not found".
    55	    if ((err as { statusCode?: number }).statusCode === 400) return notFound();
    56	    throw err;
    57	  }
    58	  if (!mdBytes) return notFound(); // MD lost behind promoted (B13b)
    59	
    60	  if (format === 'md') {
    61	    // D4 money invariant: short-circuits AFTER the mdBytes read/bad-key catch but BEFORE
    62	    // parseSummaryMarkdown/readFreshMagazineModel — must NOT resolve a model or charge.
    63	    // D12/B10b: still runs the SAME mandatory pre-response re-check the html path runs, so a
    64	    // revoke/un-promote landing between the initial resolve (above) and this response is caught —
    65	    // read-only, never charges.
    66	    const recheck = await getShareServeContext(svc, token);
    67	    if ('status' in recheck) return notFound();
    68	    return fileResponse(mdBytes, {
    69	      kind: 'md', download, base: ctx.mdKey.replace(/\.md$/, ''), title: ctx.title,
    70	      cache: 'no-store', referrerPolicy: 'no-referrer', // helper adds nosniff; inline md → text/plain
    71	    });
    72	  }
    73	
    74	  let parsed;
    75	  try { parsed = parseSummaryMarkdown(mdBytes.toString('utf-8')); }
    76	  catch { return notFound(); } // corrupt/unparsable MD → coarse 404, never 500 (B13b)
    77	  parsed.sourceMd = ctx.mdKey;
    78	  const base = ctx.mdKey.replace(/\.md$/, '');
    79	  const titles = parsed.sections.map((s) => s.title);
    80	
    81	  const model = await readFreshMagazineModel({ blobStore: readOnly, principal, base, titles });
    82	  if (model.status !== 'ok') return notReady(); // absent/stale — NO generation (B7/B8)
    83	
    84	  // Mandatory pre-response re-check: closes revoke/un-promote-before-final-check (D14/B10b).
    85	  const recheck = await getShareServeContext(svc, token);
    86	  if ('status' in recheck) return notFound();
    87	
    88	  const nonce = generateNonce();
    89	  const html = renderMagazineHtml(parsed, model.model, { nonce, dig: false, share: true });
    90	  return fileResponse(html, {
    91	    kind: 'html', download, base: ctx.mdKey.replace(/\.md$/, ''), title: ctx.title,
    92	    cache: 'no-store', csp: buildSummaryCsp(nonce), referrerPolicy: 'no-referrer',
    93	  });
    94	}
     1	import type { SupabaseClient } from '@supabase/supabase-js';
     2	import { hashShareToken } from './token';
     3	
     4	export type ShareServeContext = {
     5	  ownerId: string; playlistKey: string; playlistId: string; videoId: string; mdKey: string;
     6	  title?: string;
     7	};
     8	
     9	/** Validate a bearer token and resolve the one doc it authorizes, guarded against
    10	 *  confused-deputy: the playlist is resolved by (id, owner_id) from the token row and the
    11	 *  resolved owner is re-asserted (spec D15). Read-only; performs no blob reads. Returns a
    12	 *  coarse `denied` for every invalid/expired/revoked/unknown/unpromoted case. */
    13	export async function getShareServeContext(
    14	  serviceClient: SupabaseClient, token: string,
    15	): Promise<ShareServeContext | { status: 'denied' }> {
    16	  const denied = { status: 'denied' as const };
    17	  const hash = hashShareToken(token);
    18	
    19	  const { data: tok, error: tokErr } = await serviceClient
    20	    .from('share_tokens').select('owner_id, playlist_id, video_id, expires_at, revoked_at')
    21	    .eq('token_hash', hash).maybeSingle();
    22	  if (tokErr) throw tokErr;
    23	  if (!tok) return denied;
    24	  if (tok.revoked_at) return denied;
    25	  if (tok.expires_at) {
    26	    const expiresAtMs = new Date(tok.expires_at).getTime();
    27	    // Fail CLOSED: an unparseable expires_at (NaN) must deny, not be treated as live.
    28	    if (Number.isNaN(expiresAtMs) || expiresAtMs <= Date.now()) return denied;
    29	  }
    30	
    31	  // Resolve by the GLOBAL (id, owner_id) — never by playlist_key — AND re-assert the owner (D15).
    32	  const { data: pl, error: plErr } = await serviceClient
    33	    .from('playlists').select('playlist_key, owner_id')
    34	    .eq('id', tok.playlist_id).eq('owner_id', tok.owner_id).maybeSingle();
    35	  if (plErr) throw plErr;
    36	  if (!pl || pl.owner_id !== tok.owner_id) return denied; // confused-deputy guard (D15)
    37	
    38	  const { data: vid, error: vidErr } = await serviceClient
    39	    .from('videos').select('data, owner_id')
    40	    .eq('playlist_id', tok.playlist_id).eq('video_id', tok.video_id).eq('owner_id', tok.owner_id).maybeSingle();
    41	  if (vidErr) throw vidErr;
    42	  if (!vid || vid.owner_id !== tok.owner_id) return denied;
    43	
    44	  const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
    45	    .artifacts?.summaryMd;
    46	  if (artifact?.status !== 'promoted') return denied;
    47	  const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
    48	  if (!mdKey) return denied;
    49	
    50	  const rawTitle = (vid.data as { title?: unknown }).title;
    51	  const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;
    52	
    53	  return { ownerId: tok.owner_id, playlistKey: pl.playlist_key, playlistId: tok.playlist_id,
    54	           videoId: tok.video_id, mdKey, title };
    55	}

codex
I found one real edge, and it is not just reporting: rule 1 can overwrite a receiver’s already-current model with a sender envelope that only matches the MD hash but is stale by `GENERATOR_VERSION`. I’m checking it against the spec wording now so the final finding is concrete rather than speculative.
exec
/bin/bash -lc 'npm test -- --runTestsByPath tests/lib/cloud-sync/companion.test.ts --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'npm test -- --runTestsByPath tests/integration/share-route.test.ts --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 exited 1 in 3012ms:

> youtube-playlist-summaries@0.1.0 test
> jest --runTestsByPath tests/integration/share-route.test.ts --runInBand

No tests found, exiting with code 1
Run with `--passWithNoTests` to exit with code 0
No files found in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud.
Make sure Jest's configuration does not exclude this directory.
To set up Jest, make sure a package.json file exists.
Jest Documentation: https://jestjs.io/docs/configuration
Files: "tests/integration/share-route.test.ts"

 succeeded in 3574ms:

> youtube-playlist-summaries@0.1.0 test
> jest --runTestsByPath tests/lib/cloud-sync/companion.test.ts --runInBand

Test Suites: 1 passed, 1 total
Tests:       26 passed, 26 total
Snapshots:   0 total
Time:        0.362 s, estimated 1 s
Ran all test suites within paths "tests/lib/cloud-sync/companion.test.ts".

codex
The companion unit suite passes as-is. The share-route file is outside the default Jest match for `npm test`, so that direct `--runTestsByPath` invocation reports “No tests found”; I’m not treating that as a product failure.
exec
/bin/bash -lc 'cat package.json' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
{
  "name": "youtube-playlist-summaries",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:e2e": "playwright test",
    "rerender-html": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/rerender-html.ts",
    "audit-timestamps": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/audit-timestamps.ts",
    "audit-summaries": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/audit-summaries.ts",
    "repair-timestamps": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/repair-timestamps.ts",
    "backfill-serial": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/backfill-serial-prefix.ts",
    "backfill-playlist-titles": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/backfill-playlist-titles.ts",
    "test:integration": "jest --config jest.integration.config.ts --runInBand",
    "check:confinement": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/check-service-confinement.ts",
    "worker": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register worker/main.ts",
    "verify:gemini-release": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/verify-gemini-release.ts",
    "cloud-sync": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/cloud-sync.ts"
  },
  "dependencies": {
    "@google/generative-ai": "^0.24.1",
    "@supabase/ssr": "^0.12.0",
    "@supabase/supabase-js": "^2.109.0",
    "googleapis": "^171.4.0",
    "markdown-it": "^14.2.0",
    "next": "16.2.6",
    "playwright": "^1.60.0",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "server-only": "^0.0.1",
    "youtube-transcript": "^1.3.1",
    "zod": "^4.4.3"
  },
  "devDependencies": {
    "@playwright/test": "^1.60.0",
    "@tailwindcss/postcss": "^4",
    "@testing-library/dom": "^10.4.1",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/jest": "^30.0.0",
    "@types/markdown-it": "^14.1.2",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "jest": "^30.4.2",
    "jest-environment-jsdom": "^30.4.1",
    "tailwindcss": "^4",
    "ts-jest": "^29.4.9",
    "ts-node": "^10.9.2",
    "tsconfig-paths": "^4.2.0",
    "typescript": "^5"
  }
}

exec
/bin/bash -lc 'rg -n "test:integration|testMatch|integration" jest.config.* package.json -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
package.json:18:    "test:integration": "jest --config jest.integration.config.ts --runInBand",
jest.config.ts:11:  testMatch: [

codex
I have enough to finalize: R5’s main stale-receiver deletion fix is real, but rule ordering still permits a stale sender model to replace a fresh receiver model when both claim the winning MD hash. That is a paid-artifact regression class, so this round is not converged.
codex
**Finding**
High — [lib/cloud-sync/companion.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:63)

`decideCompanion` lets a sender model overwrite the receiver solely because `senderModel.envelope.sourceMdHash === winnerMdHash`, before checking whether the receiver already has an equally hash-matching, render-fresh model.

Concrete scenario:

- Winning MD hash is `H`.
- Sender has `models/base.json` with `sourceMdHash: H`, but `generatorVersion: "OLD"`.
- Receiver has `models/base.json` with `sourceMdHash: H`, current `generatorVersion`, and matching `sourceSections`.
- Class-A transfer runs, then `companionTransfer` calls `decideCompanion`.
- Rule 1 returns `ship`; [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:392) writes the stale sender envelope over the fresh receiver envelope.
- Anonymous share readiness regresses: [read-model.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/read-model.ts:20) requires current `GENERATOR_VERSION`, and [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:81) returns 503 when the model is stale.
- Owner recovery goes through `resolveMagazineModel` and `reserve_serve_model`, so this destroys a paid/current artifact and forces re-spend.

Fix: do not treat `sourceMdHash` alone as sufficient to overwrite a receiver model. Prefer a receiver model that is already fresh for the winning MD, or make `ModelRead` carry freshness against the winning parsed titles plus `GENERATOR_VERSION`; ship only a fresh sender model. At minimum, if both sender and receiver match `winnerMdHash`, keep the receiver instead of overwriting it blindly.

**Part A**
- 9-way matrix: Incomplete. The intended hash tri-state matrix is exhaustive, but the sender-match row is too broad because it supersedes a better receiver model.
- `provablyStale`: Genuinely fixed for hashed mismatches after the receiver-match exclusion. It correctly does not delete absent/legacy/unprovable reads. But hash-match with stale `generatorVersion` is not “share ready”; serve rejects it.
- Receiver null mapping: Genuinely fixed. `readModelSide` maps local null to `none` via `provesAbsence=true`, Supabase null to `unknown`, so unprovable receiver reads do not delete.
- `shareNeedsOwnerServe` on noop: Mostly fixed and not over-reporting ordinary syncs. `noop + true` only fires inside `companionTransfer`, which only runs after a Class-A copy, not for every skipped video with no model. But it under-reports the stale-version hash-match case above.
- H3 layer 3 removal / `ensureReceiverSlot`: Genuinely fixed. `setPlaylistMeta` before `readIndex` is correct: local creates/updates `playlist-index.json` before reading it; Supabase upserts the playlist row before reading videos; the row-exists check remains authoritative in this single-run model.
- L-R5-2 cloud title precedence: Genuinely fixed under the branch’s chosen no-title-timestamp model. Cloud title wins when both exist; local still fills when cloud lacks a title.

**Part B**
No additional branch-level findings beyond the High above. Baseline advancement remains durable-after-write on the reviewed paths, sync does not enqueue or touch `spend_ledger`, regenerable caches are not copied, and RLS/service-role posture is unchanged in the scoped files.

Verification run:
- `npm test -- --runTestsByPath tests/lib/cloud-sync/companion.test.ts --runInBand` passed.
- Direct `npm test -- --runTestsByPath tests/integration/share-route.test.ts --runInBand` found no tests because integration tests use `jest.integration.config.ts`.

**NOT CONVERGED**
tokens used
136,372
**Finding**
High — [lib/cloud-sync/companion.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:63)

`decideCompanion` lets a sender model overwrite the receiver solely because `senderModel.envelope.sourceMdHash === winnerMdHash`, before checking whether the receiver already has an equally hash-matching, render-fresh model.

Concrete scenario:

- Winning MD hash is `H`.
- Sender has `models/base.json` with `sourceMdHash: H`, but `generatorVersion: "OLD"`.
- Receiver has `models/base.json` with `sourceMdHash: H`, current `generatorVersion`, and matching `sourceSections`.
- Class-A transfer runs, then `companionTransfer` calls `decideCompanion`.
- Rule 1 returns `ship`; [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:392) writes the stale sender envelope over the fresh receiver envelope.
- Anonymous share readiness regresses: [read-model.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/read-model.ts:20) requires current `GENERATOR_VERSION`, and [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:81) returns 503 when the model is stale.
- Owner recovery goes through `resolveMagazineModel` and `reserve_serve_model`, so this destroys a paid/current artifact and forces re-spend.

Fix: do not treat `sourceMdHash` alone as sufficient to overwrite a receiver model. Prefer a receiver model that is already fresh for the winning MD, or make `ModelRead` carry freshness against the winning parsed titles plus `GENERATOR_VERSION`; ship only a fresh sender model. At minimum, if both sender and receiver match `winnerMdHash`, keep the receiver instead of overwriting it blindly.

**Part A**
- 9-way matrix: Incomplete. The intended hash tri-state matrix is exhaustive, but the sender-match row is too broad because it supersedes a better receiver model.
- `provablyStale`: Genuinely fixed for hashed mismatches after the receiver-match exclusion. It correctly does not delete absent/legacy/unprovable reads. But hash-match with stale `generatorVersion` is not “share ready”; serve rejects it.
- Receiver null mapping: Genuinely fixed. `readModelSide` maps local null to `none` via `provesAbsence=true`, Supabase null to `unknown`, so unprovable receiver reads do not delete.
- `shareNeedsOwnerServe` on noop: Mostly fixed and not over-reporting ordinary syncs. `noop + true` only fires inside `companionTransfer`, which only runs after a Class-A copy, not for every skipped video with no model. But it under-reports the stale-version hash-match case above.
- H3 layer 3 removal / `ensureReceiverSlot`: Genuinely fixed. `setPlaylistMeta` before `readIndex` is correct: local creates/updates `playlist-index.json` before reading it; Supabase upserts the playlist row before reading videos; the row-exists check remains authoritative in this single-run model.
- L-R5-2 cloud title precedence: Genuinely fixed under the branch’s chosen no-title-timestamp model. Cloud title wins when both exist; local still fills when cloud lacks a title.

**Part B**
No additional branch-level findings beyond the High above. Baseline advancement remains durable-after-write on the reviewed paths, sync does not enqueue or touch `spend_ledger`, regenerable caches are not copied, and RLS/service-role posture is unchanged in the scoped files.

Verification run:
- `npm test -- --runTestsByPath tests/lib/cloud-sync/companion.test.ts --runInBand` passed.
- Direct `npm test -- --runTestsByPath tests/integration/share-route.test.ts --runInBand` found no tests because integration tests use `jest.integration.config.ts`.

**NOT CONVERGED**
