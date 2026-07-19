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
session id: 019f75f9-eb24-75b3-a62a-0984cf902cba
--------
user
You are an adversarial WHOLE-BRANCH RE-REVIEWER (ROUND 4) for the Stage 3 Cloud Sync (M2a) branch `feat/stage3-cloud-sync`. HEAD is `3bc8cc7`.

Convergence trail (read the docs, they are the audit record):
- R1 `docs/reviews/whole-branch-cloud-sync-codex.md` → 1 Blocking + 2 High → fixed `32a164c`
- R2 `...-v2-rereview-{codex,claude}.md` → H-R2-1 (WB-H1 incomplete), H-R2-2 (regression from the WB-H2 fix), M-R2-2 → fixed `1f54c60`
- R3 `...-v3-rereview-{codex,claude}.md` → Codex returned CONVERGED (0 findings) but the Claude pass found **B1, Blocking** (reproduced in two forms) → fixed `3bc8cc7`

Read `git show 3bc8cc7` first.

**Calibration from R3, and it cuts both ways.** One reviewer declared convergence while a Blocking was live — so do not treat a quiet branch as a clean one, and interrogate what values MEAN (is `null` "absent" or "failed to load"?), not merely whether they are handled. Equally: three rounds of real fixes have landed, and if this round genuinely finds nothing, say so plainly. A clean round is the expected terminal state of this loop; manufacturing a marginal finding to appear diligent is itself a failure.

## Part A — verify the round-3 fix is GENUINELY fixed
**B1** — `lib/cloud-sync/sync-run.ts:510-511` now throws per-video when a record advertises `summaryMd` but its body did not load, on either side, before the corrections guard and before `reconcileClassA`.

VERIFY:
1. Does the guard cover EVERY consumer of a possibly-unreadable body, or only the two-sided reconcile path? Audit every other `readMdBody` / `blob.get` call in `lib/cloud-sync/*` — companion (`companion.ts`, `decideCompanion` / `sourceMdHash` comparison), `transferClassA`'s own reads, the manifest/backfill paths, `registry.ts`. Can a null-because-unreadable still be read as a semantic fact anywhere else (e.g. "the model was not generated from this MD" → deleting a companion model, or a Class-B/backfill decision)?
2. Is throwing the right response versus skipping? A record that PERMANENTLY advertises a `summaryMd` whose blob is genuinely gone (real storage drift, not transient) now errors on EVERY run forever and never advances a baseline. Trace what that does to delete-inference, to `report.errors` growth, and to a user's ability to ever complete a sync run. Is there a case where this new throw makes a previously-working sync fail?
3. Does the guard change behavior for the legitimate summary-less video (`summaryMd == null`) and the one-sided-hydration case (M-R2-2)? Both must still work. Confirm against the tests at `tests/integration/cloud-sync/e2e.int.test.ts`.
4. Are the two new B1 regression tests honest — do they fail for the RIGHT reason when the guard is removed, and do they assert across two runs?

## Part B — hunt for NEW defects, and for SIBLINGS of the B1 root cause
The B1 root cause is a **semantic conflation across a module boundary**: a value that means "absent" in one module is produced by a failure in another. Hunt for siblings of that shape anywhere on the sync path — not just for blobs. Candidates worth tracing: a swallowed error that yields a default/empty value which a caller then treats as fact (empty index vs failed read; absent manifest vs unreadable manifest; a missing record vs a failed query; `readIndex` on a store error; `''` vs absent playlist metadata).

Also re-verify, on the shipped state:
- Baseline-advance correctness on every branch; no advance without a durable write; every "seen" video gets one (delete-inference).
- Money-safety: no enqueue, no `spend_ledger`, no regenerable-cache resurrection; `needsRegen` report-only. Count any path that forces the USER to re-spend as a money finding.
- Atomicity: durable-before-advertise, manifest-after-commit.
- Idempotency across TWO runs on every branch — no oscillation, no laundering of an error into a false agreement.
- Cross-backend local-vs-Supabase semantic mismatches.
- RLS / no-service-role unchanged.

## Scope
SHIPPED state at HEAD. `lib/cloud-sync/*.ts`, `supabase/migrations/0021_*` + `0009_*`, `lib/storage/local/*`, `lib/storage/supabase/*`, `lib/html-doc/*`, `lib/dig/*`, tests under `tests/lib/cloud-sync/` and `tests/integration/cloud-sync/`. Spec: `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`.

KNOWN / DEFERRED — do NOT re-report unless you prove they mask a real bug: T14-M1, T14-M2, T5 coverage gaps, T4 automock comment; Claude-R2-M1 (stale non-`summaryMd` artifact pointers); Codex-R2-Medium (absent companion scalars); Claude-R3-M1 (`build-doc-html` deriving `base` from `digDeeperMd`). Do NOT report `tests/integration/reservation-release.test.ts` — pre-existing on a clean tree, tracked separately.

## Output
Per finding: severity (Blocking/High/Medium/Low), `file:line`, concrete failure scenario (inputs → wrong outcome), fix. Part A: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.

codex
I’ll use the diagnose/review path here: first read the exact HEAD fix and audit docs/tests, then trace the sync code for sibling semantic conflations before giving findings only if they hold up.
exec
/bin/bash -lc 'git show --stat --oneline --decorate 3bc8cc7 && git show --name-only --format=fuller 3bc8cc7' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
3bc8cc7 (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
 .../whole-branch-cloud-sync-v3-rereview-claude.md  |  207 +
 .../whole-branch-cloud-sync-v3-rereview-codex.md   | 4979 ++++++++++++++++++++
 lib/cloud-sync/sync-run.ts                         |   19 +
 lib/storage/supabase/supabase-blob-store.ts        |    8 +-
 tests/integration/cloud-sync/e2e.int.test.ts       |   76 +
 5 files changed, 5288 insertions(+), 1 deletion(-)
commit 3bc8cc7fd614b3377266313077f245ff44e903e5
Author:     Kujin Lee <kujinlee@gmail.com>
AuthorDate: Sat Jul 18 09:05:00 2026 -0700
Commit:     Kujin Lee <kujinlee@gmail.com>
CommitDate: Sat Jul 18 09:05:00 2026 -0700

    fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
    
    Round-3 dual re-review of 1f54c60. Codex returned CONVERGED (0 findings); the Claude
    pass found a Blocking, reproduced in two forms. Adjudicated against the code — the
    Blocking is real.
    
    B1 — readMdBody returns null for TWO different situations: the record advertises no
    summaryMd, or it advertises one whose bytes could not be READ. The backends disagree on
    which is which: the local blob store returns null only on ENOENT and throws otherwise,
    but SupabaseBlobStore.get is `if (error) return null` — it swallows EVERY failure
    (network, 5xx, timeout, RLS denial). deriveClassASignals maps a null body to
    mdHash: null, and reconcileClassA reads mdHash == null as "this side HAS NO MD"
    (reconcile-class-a.ts:21-23) — presence branches that return BEFORE the
    corrections-currency and never-downgrade-format ladder (:38-46).
    
    Consequences, both reproduced:
    - P1 (opened by the round-2 M-R2-2 narrowing): under an unresolved corrections conflict
      an unreadable cloud body meant the guard did not fire; the local body was copied over
      cloud's and a full-agreement baseline recorded — the exact destruction WB-B1 was filed
      to prevent, and silent (errors: []).
    - P2 (pre-existing, not a regression): with no corrections at all, a transient download
      error let a major-1 body overwrite a major-9 one, downgrading the format past the
      never-downgrade rule. Run 2 saw identical bodies, skipped, and the loss became
      permanent — recoverable only by paid regeneration.
    
    Fix: the two-sided counterpart of copyAdditiveVideo's existing WB-H1/H-R2-1 guard. If a
    record advertises summaryMd but its body did not load, throw per-video — caught by the
    existing handler, surfaced in report.errors, and advancing NO baseline, so the run heals
    once the body is readable. reconcileClassA's !lHas/!cHas branches now mean what they
    claim, so M-R2-2's additive-hydration intent is preserved exactly.
    
    Also corrects the misleading `// 404 → null` comment on SupabaseBlobStore.get. Comment
    only — the behavior is shared with already-merged read paths and is out of scope here.
    
    Deferred with owner: build-doc-html deriving `base` from digDeeperMd can serve a pre-sync
    summary in the dig view when replica keys diverge (Claude-R3-M1); prior R2 deferrals stand.
    
    Verification: tsc clean; 2421 unit / 245 suites; cloud-sync integration 37/37 (4 suites).
    Mutation-checked: removing the guard fails 2 of the new tests on the byte-preservation
    assertion, so they genuinely catch the defect.
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01EfbFViKSSM27WJ5dSchemY

docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md
lib/cloud-sync/sync-run.ts
lib/storage/supabase/supabase-blob-store.ts
tests/integration/cloud-sync/e2e.int.test.ts

codex
The commit is scoped: one guard in `sync-run.ts`, a Supabase blob-store comment, and two integration regressions. Next I’m reading the previous review record plus the actual sync/storage code so I can distinguish a real sibling defect from a known deferred issue.
exec
/bin/bash -lc 'git show --unified=80 -- lib/cloud-sync/sync-run.ts lib/storage/supabase/supabase-blob-store.ts tests/integration/cloud-sync/e2e.int.test.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
commit 3bc8cc7fd614b3377266313077f245ff44e903e5
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Sat Jul 18 09:05:00 2026 -0700

    fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
    
    Round-3 dual re-review of 1f54c60. Codex returned CONVERGED (0 findings); the Claude
    pass found a Blocking, reproduced in two forms. Adjudicated against the code — the
    Blocking is real.
    
    B1 — readMdBody returns null for TWO different situations: the record advertises no
    summaryMd, or it advertises one whose bytes could not be READ. The backends disagree on
    which is which: the local blob store returns null only on ENOENT and throws otherwise,
    but SupabaseBlobStore.get is `if (error) return null` — it swallows EVERY failure
    (network, 5xx, timeout, RLS denial). deriveClassASignals maps a null body to
    mdHash: null, and reconcileClassA reads mdHash == null as "this side HAS NO MD"
    (reconcile-class-a.ts:21-23) — presence branches that return BEFORE the
    corrections-currency and never-downgrade-format ladder (:38-46).
    
    Consequences, both reproduced:
    - P1 (opened by the round-2 M-R2-2 narrowing): under an unresolved corrections conflict
      an unreadable cloud body meant the guard did not fire; the local body was copied over
      cloud's and a full-agreement baseline recorded — the exact destruction WB-B1 was filed
      to prevent, and silent (errors: []).
    - P2 (pre-existing, not a regression): with no corrections at all, a transient download
      error let a major-1 body overwrite a major-9 one, downgrading the format past the
      never-downgrade rule. Run 2 saw identical bodies, skipped, and the loss became
      permanent — recoverable only by paid regeneration.
    
    Fix: the two-sided counterpart of copyAdditiveVideo's existing WB-H1/H-R2-1 guard. If a
    record advertises summaryMd but its body did not load, throw per-video — caught by the
    existing handler, surfaced in report.errors, and advancing NO baseline, so the run heals
    once the body is readable. reconcileClassA's !lHas/!cHas branches now mean what they
    claim, so M-R2-2's additive-hydration intent is preserved exactly.
    
    Also corrects the misleading `// 404 → null` comment on SupabaseBlobStore.get. Comment
    only — the behavior is shared with already-merged read paths and is out of scope here.
    
    Deferred with owner: build-doc-html deriving `base` from digDeeperMd can serve a pre-sync
    summary in the dig view when replica keys diverge (Claude-R3-M1); prior R2 deferrals stand.
    
    Verification: tsc clean; 2421 unit / 245 suites; cloud-sync integration 37/37 (4 suites).
    Mutation-checked: removing the guard fails 2 of the new tests on the byte-preservation
    assertion, so they genuinely catch the defect.
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01EfbFViKSSM27WJ5dSchemY

diff --git a/lib/cloud-sync/sync-run.ts b/lib/cloud-sync/sync-run.ts
index a031c2a..4db7994 100644
--- a/lib/cloud-sync/sync-run.ts
+++ b/lib/cloud-sync/sync-run.ts
@@ -414,134 +414,153 @@ export async function runSync(
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
     const manifest = await readManifest(dataRoot, key);
 
     for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
       try {
         const lv = await readVideo(deps.local, localP, id);
         const cv = await readVideo(deps.cloud, cloudP, id);
         const base = manifest.videos[id];
 
         // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
         //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
         if (!lv || !cv) {
           const present = (lv ?? cv)!;
           const presentIsLocal = lv != null;
           if (base) {
             report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
           } else {
             const from: Side = presentIsLocal ? localSide : cloudSide;
             const to: Side = presentIsLocal ? cloudSide : localSide;
             const body = await readMdBody(from.blob, from.p, present);
             await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
             report.created += 1; // reached only after the receiver row is confirmed
             await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
               deriveClassASignals(present, body), body ? mdHash(body) : null,
               deriveHumanSnapshot(present),
             ));
           }
           continue;
         }
 
         // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
         const localSnap = deriveHumanSnapshot(lv);
         const cloudSnap = deriveHumanSnapshot(cv);
         const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
         const applied = await applyClassBWinners({
           deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
         });
         report.mergedFields += applied.merged;
         report.conflictsLogged += applied.conflicts;
         const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
 
         // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
         //    Class B logs+skips, §5.5). Its value is NOT a settled winner, so it must NOT drive a
         //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
         //    and copy its MD body over the loser's (different-correction) body — DESTROYING the loser's
         //    corrected MD and recording a false agreement (sticky: the copied bodies then match forever).
         //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
         //    Class A (so the next run re-evaluates once the human resolves corrections). The video stays
         //    "seen" for delete-inference (baseline present).
         //
         //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
         //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
         //    behavior. Bodies are needed for hashing regardless — Behavior #1.
         const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
         const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
 
+        // ── B1 (round 3) — the two-sided counterpart of copyAdditiveVideo's WB-H1/H-R2-1 guard (:160).
+        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
+        //    or it advertises one whose bytes could not be READ. The backends disagree on which errors
+        //    are which: local get throws on anything but ENOENT, but the Supabase get is `if (error)
+        //    return null` — it swallows EVERY failure (network, 5xx, timeout, RLS denial), so on the
+        //    cloud side an ordinary transient download error is indistinguishable from "no MD".
+        //    deriveClassASignals maps a null body to mdHash: null, and reconcileClassA reads
+        //    mdHash == null as "this side HAS NO MD" (:21-23) — and those presence branches return
+        //    BEFORE the corrections-currency and never-downgrade-format ladder (:38-46). So an
+        //    unreadable body made the other replica's body get copied over it (destroying it) and
+        //    recorded a full-agreement baseline; run 2 then saw identical bodies and skipped, making
+        //    the loss permanent and recoverable only by paid regeneration.
+        //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
+        //    so the run heals by itself once the body is readable. With this guard reconcileClassA's
+        //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
+        //    which is exactly M-R2-2's "purely additive hydration", so its intent is preserved.
+        if (lv.summaryMd && la.mdHash == null) throw new Error(`local MD body unreadable for ${id}`);
+        if (cv.summaryMd && ca.mdHash == null) throw new Error(`cloud MD body unreadable for ${id}`);
+
         //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
         //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
         //    nothing can be destroyed and no false agreement about competing bodies is possible — so
         //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
         //    corrections). The corrections conflict is still logged by Class B and still flags
         //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
         const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
         if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
           report.needsRegen += 1;
           if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
           await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
           continue;
         }
 
         // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
         const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
         if (decision.needsRegen) report.needsRegen += 1;
 
         let winnerMdHash: string | null = null;
         let winnerSignals: ClassASignals = la;
         let winnerSide: Side | null = null;
         let loserSide: Side | null = null;
         let winnerVideo: Video = lv;
 
         if (decision.action === 'copyToCloud') {
           winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
           winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
           report.updatedCloud += 1;
         } else if (decision.action === 'copyToLocal') {
           winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
           winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
           report.updatedLocal += 1;
         } else {
           report.skippedIdentical += 1;
           winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
         }
 
         if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
           const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
           if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
         }
         if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
 
         // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
         //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
         await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
       } catch (e: any) {
         report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
       }
     }
   }
 
   return report;
 }
diff --git a/lib/storage/supabase/supabase-blob-store.ts b/lib/storage/supabase/supabase-blob-store.ts
index 7a415c2..6b70803 100644
--- a/lib/storage/supabase/supabase-blob-store.ts
+++ b/lib/storage/supabase/supabase-blob-store.ts
@@ -1,105 +1,111 @@
 import crypto from 'crypto';
 import type { SupabaseClient } from '@supabase/supabase-js';
 import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
 import { assertLogicalKey } from '@/lib/storage/blob-store';
 import type { Principal } from '@/lib/storage/principal';
 
 export class SupabaseBlobStore implements BlobStore {
   constructor(private client: SupabaseClient, private bucket: string) {}
 
   /** Server-side owner prefix — never a client absolute path. */
   private objectKey(p: Principal, key: string): string {
     assertLogicalKey(key);
     return `${p.id}/${p.indexKey}/${key}`;
   }
 
   private b() { return this.client.storage.from(this.bucket); }
 
   async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
     const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
     if (error) throw error;
   }
 
   async get(p: Principal, key: string): Promise<Buffer | null> {
     const { data, error } = await this.b().download(this.objectKey(p, key));
-    if (error) return null;   // 404 → null
+    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
+    // so a null here does NOT prove the object is absent. Callers that treat "no bytes" as a
+    // semantic fact (e.g. "this replica holds no MD") must corroborate it against the record that
+    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately
+    // left as-is: shared with already-merged read paths where absent-vs-unreadable is immaterial.
+    // Note the LOCAL blob store differs — it returns null only on ENOENT and throws otherwise.
+    if (error) return null;
     return Buffer.from(await data.arrayBuffer());
   }
 
   async exists(p: Principal, key: string): Promise<boolean> {
     return (await this.get(p, key)) !== null;
   }
 
   async delete(p: Principal, key: string): Promise<void> {
     const { error } = await this.b().remove([this.objectKey(p, key)]);
     if (error) throw error;
   }
 
   async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
     assertLogicalKey(key); // validate before building tempKey — reject '/absolute' before any upload
     const tempKey = `_staging/${crypto.randomUUID()}/${key}`; // per-attempt-unique (ports local-blob-store)
     await this.put(p, tempKey, bytes, contentType);
     return { principal: p, tempKey, finalKey: key };
   }
 
   async promote(ref: StagedRef): Promise<void> {
     const from = this.objectKey(ref.principal, ref.tempKey);
     const to = this.objectKey(ref.principal, ref.finalKey);
     // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
     if (await this.exists(ref.principal, ref.finalKey)) {
       await this.b().remove([from]).catch(() => {});
       return;
     }
     const { error } = await this.b().move(from, to);
     if (error) {
       // A concurrent promoter (worker job retry / re-run of the same MD key) may have won the race: destination-exists / source-missing.
       // Re-check the final; treat a present final as success, else rethrow.
       if (await this.exists(ref.principal, ref.finalKey)) {
         await this.b().remove([from]).catch(() => {});
         return;
       }
       throw error;
     }
   }
 
   async deletePrefix(p: Principal, prefix: string): Promise<void> {
     assertLogicalKey(prefix);
     const root = `${p.id}/${p.indexKey}/${prefix}`.replace(/\/$/, '');
     const objectPaths = await this.collectObjectPaths(root);
     for (let i = 0; i < objectPaths.length; i += 1000) {
       const batch = objectPaths.slice(i, i + 1000);
       const { error } = await this.b().remove(batch);
       if (error) throw error;
     }
   }
 
   async list(p: Principal, prefix: string): Promise<string[]> {
     assertLogicalKey(prefix);
     const ownerRoot = `${p.id}/${p.indexKey}/`;
     const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
     const full = await this.collectObjectPaths(dirPath); // returns full object paths (or [] if absent)
     return full.map((f) => f.slice(ownerRoot.length)); // strip owner root → logical key
   }
 
   /** Recursively walks a Supabase Storage "directory" (non-recursive `.list`, paginated at
    *  100/page) and returns every file's full object path. Folder entries surface with
    *  `id === null` and are descended into; file entries (`id !== null`) are collected. */
   private async collectObjectPaths(dirPath: string): Promise<string[]> {
     const paths: string[] = [];
     const limit = 100;
     let offset = 0;
     for (;;) {
       const { data, error } = await this.b().list(dirPath, { limit, offset });
       if (error) throw error;
       const entries = data ?? [];
       for (const entry of entries) {
         const entryPath = `${dirPath}/${entry.name}`;
         if (entry.id === null) {
           paths.push(...(await this.collectObjectPaths(entryPath)));
         } else {
           paths.push(entryPath);
         }
       }
       if (entries.length < limit) break;
       offset += limit;
     }
diff --git a/tests/integration/cloud-sync/e2e.int.test.ts b/tests/integration/cloud-sync/e2e.int.test.ts
index 6f12563..4c94efe 100644
--- a/tests/integration/cloud-sync/e2e.int.test.ts
+++ b/tests/integration/cloud-sync/e2e.int.test.ts
@@ -473,81 +473,157 @@ describe('cloud-sync §10 end-to-end scenarios', () => {
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
       summaryHtml: '<html>STALE rendered from the old local body</html>',
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
 
     const report = await runSync(ctx.syncDeps());
     expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
 
     const local = await localVideoRecord(ctx);
     expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body copied
   });
 
   // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
   //    regenerable render cache: it is the filename pointer to a PAID Gemini-generated dig-deeper
   //    markdown file (lib/dig/generate.ts). Nulling it on an ordinary Class-A transfer orphans the file
   //    on disk and makes the dig-state route / VideoMenu / build-doc-html / pdf-path all go dark —
   //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
   //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
   it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
     const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
     const digKey = 'paid-dig-deeper.md';
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
       summaryHtml: '<html>STALE rendered from the old local body</html>',
       digDeeperHtml: '<html>STALE dig render</html>',
       raw: { digDeeperMd: digKey },
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
 
     const report = await runSync(ctx.syncDeps());
     expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
 
     const local = await localVideoRecord(ctx);
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body landed
     expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
     expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
     expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
   });
 
   // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
   //    MD body). When the loser has NO MD at all, hydrating it is purely additive — nothing can be
   //    destroyed — so a backfilled corrections conflict must not strand the video with no MD forever
   //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
   it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
     const ctx = await makeOwnerContext();
     const bodyCloud = '# CloudOnly\n\nthe only MD body that exists\n';
     await seedLocalVideoFull(ctx, {
       summaryMd: null, // local row exists but holds NO MD → nothing to destroy
       corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
       docVersion: { major: 1, minor: 0 },
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // backfilled
       docVersion: { major: 1, minor: 0 },
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     const report = await runSync(ctx.syncDeps());
 
     expect(report.updatedLocal).toBeGreaterThanOrEqual(1);           // hydration ran
     expect(report.conflictsLogged).toBeGreaterThanOrEqual(1);        // corrections conflict still logged
     expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges
 
     // The cloud body is now on local, advertised promoted; both corrections still preserved.
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
     const local = await localVideoRecord(ctx);
     expect(local?.summaryMd).toBe(key(ctx));
     expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
     expect(local?.corrections).toBe('A');
     expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
   });
+
+  // ── B1 (round 3) — `mdHash == null` conflates "this side advertises NO MD" with "this side's MD
+  //    body could not be READ". The Supabase blob store returns null on EVERY error (network, 5xx,
+  //    timeout, RLS denial), not only 404, so an ordinary transient download failure is
+  //    indistinguishable from a summary-less video. reconcileClassA's presence branches (!lHas/!cHas)
+  //    fire BEFORE the corrections-currency and never-downgrade-format ladder, so the unreadable side
+  //    is treated as the empty side and the OTHER replica's body is copied over it — destroying it and
+  //    laundering the result into a full-agreement baseline. Both manifestations below must instead
+  //    surface a per-video error, preserve every byte, and advance NO baseline (so the run heals once
+  //    the body is readable). Each asserts across TWO runs: round 2's postmortem was that a
+  //    single-run assertion passed while the laundering bug was live.
+  it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
+    const ctx = await makeOwnerContext();
+    const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
+    await seedLocalVideoFull(ctx, {
+      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // backfilled (no per-field ts)
+      docVersion: { major: 1, minor: 0 },
+    });
+    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
+    // the buggy path read as "cloud has no MD" ⇒ the corrections guard did not fire ⇒ copyToCloud.
+    await seedCloudVideo(ctx, {
+      /* mdBody omitted → blob unreadable */
+      corrections: 'B', mdCorrectionsHash: mdHash('B'), docVersion: { major: 1, minor: 0 },
+    });
+    const spendBefore = await ctx.spendLedgerTotal();
+
+    for (const _run of [1, 2]) {
+      const report = await runSync(ctx.syncDeps());
+
+      // The failure is SURFACED, not silent (the buggy path reported errors: []).
+      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
+      expect(report.updatedCloud).toBe(0);
+      expect(report.updatedLocal).toBe(0);
+      // Local body byte-preserved; cloud body still absent (nothing was written over the gap).
+      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
+      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
+      // Both corrections preserved.
+      expect((await localVideoRecord(ctx))?.corrections).toBe('A');
+      expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
+      // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
+      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
+      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
+    }
+  });
+
+  it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
+    const ctx = await makeOwnerContext();
+    const bodyLocal = '# LocalOld\n\nlower-major local body\n';
+    // No corrections anywhere — this manifestation is NOT conflict-gated: the !cHas early return in
+    // reconcileClassA precedes the never-downgrade-format rule, so a transient download error let a
+    // major-1 body overwrite a major-9 one and recorded major 1 as the agreed baseline. Run 2 then saw
+    // identical bodies ⇒ skip ⇒ permanent, recoverable only by full (paid) regeneration.
+    await seedLocalVideoFull(ctx, {
+      mdBody: bodyLocal, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    await seedCloudVideo(ctx, {
+      /* mdBody omitted → blob unreadable */
+      docVersion: { major: 9, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    const spendBefore = await ctx.spendLedgerTotal();
+
+    for (const _run of [1, 2]) {
+      const report = await runSync(ctx.syncDeps());
+
+      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
+      expect(report.updatedCloud).toBe(0);
+      expect(report.updatedLocal).toBe(0);
+      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
+      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
+      // Format NOT downgraded on either side (the buggy path wrote cloud major 9 → 1).
+      expect((await cloudVideoRecord(ctx))?.docVersion?.major).toBe(9);
+      expect((await localVideoRecord(ctx))?.docVersion?.major).toBe(1);
+      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
+      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
+    }
+  });
 });

exec
/bin/bash -lc "rg -n \"readMdBody|blob\\.get|get\\(|summaryMd|sourceMdHash|needsRegen|spend_ledger|manifest|baseline|advance|readIndex|delete\" lib/cloud-sync lib/storage/local lib/storage/supabase lib/html-doc lib/dig tests/lib/cloud-sync tests/integration/cloud-sync docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/storage/local/local-blob-store.ts:18:  async get(p: Principal, key: string): Promise<Buffer | null> {
lib/storage/local/local-blob-store.ts:28:  async delete(p: Principal, key: string): Promise<void> {
lib/storage/local/local-blob-store.ts:47:  async deletePrefix(p: Principal, prefix: string): Promise<void> {
lib/html-doc/model-store.ts:22:    sourceMdHash: z.string().optional(),
lib/html-doc/model-store.ts:24:  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
lib/html-doc/model-store.ts:58:  const bytes = await blobStore.get(principal, MODEL_KEY(base));
lib/cloud-sync/companion.ts:5:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
lib/cloud-sync/companion.ts:13:  if (senderEnvelope && senderEnvelope.sourceMdHash === winnerMdHash) {
lib/cloud-sync/companion.ts:16:  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
tests/lib/cloud-sync/model-writer-hash.test.ts:4:// and asserts the persisted model envelope's sourceMdHash is the hash of the MD BODY that was
tests/lib/cloud-sync/model-writer-hash.test.ts:5:// fed to generation — NOT a hash of the sourceMd/summaryMd blob KEY (the filename). Guards
tests/lib/cloud-sync/model-writer-hash.test.ts:7:// matches, so every synced companion would be wrongly deleted (needless re-charge on serve).
tests/lib/cloud-sync/model-writer-hash.test.ts:24:// The MD body fed to generation (the whole file `runHtmlDoc` reads as `video.summaryMd`'s blob).
tests/lib/cloud-sync/model-writer-hash.test.ts:56:    overallScore: 4, summaryMd: 'a-title.md',
tests/lib/cloud-sync/model-writer-hash.test.ts:70:it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:81:  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
tests/lib/cloud-sync/model-writer-hash.test.ts:82:  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
tests/integration/cloud-sync/sync-run.int.test.ts:35:    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
tests/integration/cloud-sync/sync-run.int.test.ts:41:    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
tests/integration/cloud-sync/sync-run.int.test.ts:42:    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
tests/integration/cloud-sync/sync-run.int.test.ts:58:  it('does not advance the manifest baseline when the cloud promote is not verified (crash safety)', async () => {
tests/integration/cloud-sync/sync-run.int.test.ts:67:    // Behavior #10/#11: a partial transfer NEVER advances the manifest baseline.
tests/integration/cloud-sync/stamping.int.test.ts:94:      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
tests/lib/cloud-sync/local-stamping.test.ts:23:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
tests/lib/cloud-sync/local-stamping.test.ts:33:    const idx = await localMetadataStore.readIndex(p);
tests/lib/cloud-sync/local-stamping.test.ts:45:    const idx = await localMetadataStore.readIndex(p);
tests/lib/cloud-sync/local-stamping.test.ts:55:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:69:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:79:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:91:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
lib/dig/dig-section.ts:23:  const index = await store.readIndex(principal);
lib/dig/dig-section.ts:31:  const summaryMdName = video.summaryMd ?? `${videoId}.md`;
lib/dig/dig-section.ts:32:  const summaryMdPath = path.join(outputFolder, summaryMdName);
lib/dig/dig-section.ts:33:  const mdContent = await fs.readFile(summaryMdPath, 'utf8');
lib/dig/dig-section.ts:83:  const summaryBasename = path.basename(summaryMdName, '.md');
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:26:  **additive** create with **baseline-aware** delete-suppression. Manual trigger.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:28:  sync-back pipeline (§13), cross-replica tombstone deletes, background/auto-sync, true-conflict
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:33:backfill; Supabase-Auth login; per-playlist manifest; manual **Cloud Sync**.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:35:**Out of scope (M2a):** deep-dive/dig + slide images (M2b, §13); tombstone delete propagation; background
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:103:- `ModelEnvelope` gains an OPTIONAL **`sourceMdHash`** — an **MD-body-only** digest (§5.2), set going
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:105:- On a Class-A MD-transfer: ship the sender's model as a companion **iff** `sourceMdHash == mdHash(winning
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:106:  MD)`; else **delete the receiver's model blob** (→ lazy regen on the **owner's** next serve). A **shared
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:119:  envelope's `sourceMdHash`), `mdGeneratedAt` (UTC, a **tie-break only**, never a quality signal), and
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:135:  `now()`) — so the baseline records true authorship and later ties compare real edit times.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:159:| Present on only one side (never in this replica's baseline) | **copy** (hydrate / publish) |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:170:format**. Each reconciles **independently** against the manifest baseline (§8). **Absence is a value** (a
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:171:*clear*), not "never had" (round-v7 H-2), **and "changed vs baseline" is judged on the field's
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:173:`annotationsEditedAt` (the timestamp outlives the removed value, in both the live record and the manifest
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:174:baseline), and a **same-value re-add** (clear then re-type the same text) counts as *changed* because its
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:175:timestamp advanced — so it is tie-broken by newer-wins, not silently dropped. The table below reads "changed"
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:176:as "the `(value, annotationsEditedAt)` pair differs from baseline":
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:178:| Per-field state vs baseline | Action |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:181:| Only one side changed vs baseline (incl. a **clear** = baseline-present→absent) | take the changed side — **propagate the edit or the clear** |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:182:| **Both** changed vs baseline (different values, incl. one cleared) | newer **per-field `annotationsEditedAt`** wins + log (R1) |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:183:| No baseline (fresh device) + differ | newer per-field `annotationsEditedAt` wins + log |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:184:| Present one side, absent other, **no baseline** | copy (additive hydration) |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:187:cleared field is **not** resurrected (with a baseline, present-vs-absent is a real change → the clear
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:199:### 5.6 Presence & deletes — additive + baseline-aware (rounds 2–4)
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:200:- One-sided, never in this replica's baseline → additive **create** (a pure metadata/doc copy that **never**
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:201:  routes through the metered enqueue `lib/job-queue/producer.ts`, never consumes `spend_ledger`, never
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:203:- In this replica's baseline but **absent on the other side** → **remote delete**: do not re-create.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:204:- In this replica's baseline but **absent on this side** (this replica deleted it) → do not re-create
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:205:  locally, do not delete on the other (no propagation — M2b tombstones).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:206:- **Residual R2:** a replica with **no baseline** (fresh device / lost manifest) can't tell "deleted
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:207:  elsewhere" from "never seen" → may re-create (resurrect). Full delete-safety = M2b tombstones. No local
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:208:  delete-intent marker (round-2 H-A showed it has no sound lifecycle).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:215:- **`ModelEnvelopeSchema`:** add `sourceMdHash?: string` **and drop `.strict()`** (→ ignore unknown keys) so a
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:257:   unadvanced baseline; re-run heals. The **companion model** blob is best-effort, outside the MD's atomic
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:260:5. **Update the manifest (§8) strictly AFTER** the receiver commit is verified durable — verifying the
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:262:   human field `(value, annotationsEditedAt)` pairs. Never advance a baseline for a partial transfer.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:277:## 8. Sync state — per-playlist local manifest
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:279:One git-ignored file per playlist (`<data-root>/<playlist_key>/.cloud-sync-manifest.json`), recording per
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:280:`video_id` the last-synced baseline: **Class A** (`docVersion`, `mdGeneratedAt`, `mdCorrectionsHash`,
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:283:Written **only after** §7 step 5's verified commit. It is the "seen-before" record for §5.6 delete inference,
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:284:the Class-A tie baseline, and the Class-B 3-way-merge baseline. Lost/corrupt manifest degrades to a direct
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:285:compare (equal → skip; divergence → conflict-skip, never a destructive overwrite); only delete-detection and
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:312:  **cleared** field is **not** resurrected (baseline-aware clear propagates, round-v7 H-2); same-field-both-
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:318:  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:319:  reader (`.strict()` dropped) tolerates a `sourceMdHash`-bearing envelope.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:323:- **Union hydration / atomicity / deletes / auth:** empty-local→full-hydrate; promote-then-commit crash never
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:324:  advertises a hash for a missing blob nor advances the baseline; baseline-present remote-delete not
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:332:- **R2 — Baseline-less delete resurrection:** a fresh device / lost manifest may re-create a deleted entity;
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:333:  full delete-safety = M2b tombstones.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:372:4. **Model JSON = companion** (sync-transfer scoped, MD-only `sourceMdHash`, forward-tolerant schema, R5/R7).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:374:6. **Deletes: additive + baseline-aware**; resurrection on a baseline-less replica = R2; tombstones = M2b.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:375:7. **Per-playlist manifest**; every MD/human-field SQL writer restamps its timestamp (incl. `merge_video_data`).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:399:- Also deferred to M2b: cross-replica tombstone deletes, background/auto-sync, true-conflict loser-preservation;
tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
tests/integration/cloud-sync/e2e.int.test.ts:40:/** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
tests/integration/cloud-sync/e2e.int.test.ts:41:function baseline(classB: VideoBaseline['classB']): VideoBaseline {
tests/integration/cloud-sync/e2e.int.test.ts:91:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:129:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:130:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:139:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:188:  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
tests/integration/cloud-sync/e2e.int.test.ts:189:  it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:201:    await seedManifestBaseline(ctx, baseline({
tests/integration/cloud-sync/e2e.int.test.ts:224:    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
tests/integration/cloud-sync/e2e.int.test.ts:228:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:229:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:240:  // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
tests/integration/cloud-sync/e2e.int.test.ts:241:  it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:243:    // Cloud still holds the video; local deleted it; a baseline records they once agreed.
tests/integration/cloud-sync/e2e.int.test.ts:245:    await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));
tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:328:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:332:  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
tests/integration/cloud-sync/e2e.int.test.ts:333:  it('row 15: additive publish creates the cloud playlist+video; a re-run is not read as a delete', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:341:    expect(m1.videos[ctx.videoId]).toBeDefined();       // baseline written only after the row landed
tests/integration/cloud-sync/e2e.int.test.ts:344:    expect(r2.removed).toBe(0);                          // baseline present + BOTH sides present → not a delete
tests/integration/cloud-sync/e2e.int.test.ts:351:  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:361:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:363:    // Baseline not advanced; no charge.
tests/integration/cloud-sync/e2e.int.test.ts:368:  // ── Row 17 — fresh-device hydrate creates the local root (mkdir -p); re-run is not a delete.
tests/integration/cloud-sync/e2e.int.test.ts:369:  it('row 17: a fresh-device hydrate creates the local root, writes index+video+MD; re-run is not a delete', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:384:    expect(r2.removed).toBe(0); // the just-created local root is not mis-read as a delete
tests/integration/cloud-sync/e2e.int.test.ts:392:  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
tests/integration/cloud-sync/e2e.int.test.ts:411:    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:425:    // Second run — the baseline was NOT falsely advanced, so still no copy.
tests/integration/cloud-sync/e2e.int.test.ts:434:  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
tests/integration/cloud-sync/e2e.int.test.ts:435:  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
tests/integration/cloud-sync/e2e.int.test.ts:436:  //    promoted-but-blobless row + advanced the baseline. After the fix: per-video throw, no promoted
tests/integration/cloud-sync/e2e.int.test.ts:437:  //    receiver row, baseline NOT advanced (a re-run heals once the body is readable).
tests/integration/cloud-sync/e2e.int.test.ts:442:  //    below all passed while that bug was live; the run-2 baseline assertion is the real guard.
tests/integration/cloud-sync/e2e.int.test.ts:443:  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:445:    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
tests/integration/cloud-sync/e2e.int.test.ts:453:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:454:    // Baseline not advanced — the throw aborted before writeVideoBaseline.
tests/integration/cloud-sync/e2e.int.test.ts:457:    // Run 2 — still one-sided, so it must report the SAME error and still write no baseline. With a
tests/integration/cloud-sync/e2e.int.test.ts:462:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:523:  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
tests/integration/cloud-sync/e2e.int.test.ts:528:      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
tests/integration/cloud-sync/e2e.int.test.ts:542:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:548:    expect(local?.summaryMd).toBe(key(ctx));
tests/integration/cloud-sync/e2e.int.test.ts:549:    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:560:  //    laundering the result into a full-agreement baseline. Both manifestations below must instead
tests/integration/cloud-sync/e2e.int.test.ts:561:  //    surface a per-video error, preserve every byte, and advance NO baseline (so the run heals once
tests/integration/cloud-sync/e2e.int.test.ts:564:  it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:571:    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
tests/integration/cloud-sync/e2e.int.test.ts:592:      // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
tests/integration/cloud-sync/e2e.int.test.ts:598:  it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:601:    // No corrections anywhere — this manifestation is NOT conflict-gated: the !cHas early return in
tests/integration/cloud-sync/e2e.int.test.ts:603:    // major-1 body overwrite a major-9 one and recorded major 1 as the agreed baseline. Run 2 then saw
tests/lib/cloud-sync/reconcile-class-a.test.ts:5:  summaryMdKey: 'x.md', mdHash: 'h', docVersionMajor: 3, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
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
tests/lib/cloud-sync/reconcile-class-a.test.ts:52:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:53:      .toEqual({ action: 'copyToLocal', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:54:    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:55:      .toEqual({ action: 'copyToCloud', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:57:  it('one-sided hydrate of a corrections-STALE MD flags needsRegen (L2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:59:      .toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:62:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:63:      .toEqual({ action: 'skip', needsRegen: false });
lib/storage/supabase/consistency.ts:5:export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';
lib/storage/supabase/consistency.ts:7:const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];
lib/storage/supabase/consistency.ts:46: * Source kinds (summaryMd, slide, modelJson) require manual repair — they cannot
lib/storage/local/local-metadata-store.ts:10:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/local/local-metadata-store.ts:11:    return indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:14:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:23:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:55:      const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:67:  async deleteVideo(p: Principal, videoId: string): Promise<void> {
lib/storage/local/local-metadata-store.ts:68:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:76:  async deletePlaylist(): Promise<void> {
lib/storage/local/local-metadata-store.ts:77:    throw new Error('deletePlaylist is cloud-only (unsupported on the local backend)');
lib/storage/local/local-metadata-store.ts:82:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:107:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:142:    const idx = indexStore.readIndex(p.indexKey);
lib/cloud-sync/manifest.ts:1:// lib/cloud-sync/manifest.ts
lib/cloud-sync/manifest.ts:8:export function manifestPath(dataRoot: string, playlistKey: string): string {
lib/cloud-sync/manifest.ts:9:  return path.join(dataRoot, playlistKey, '.cloud-sync-manifest.json');
lib/cloud-sync/manifest.ts:17:    const raw = await fs.readFile(manifestPath(dataRoot, playlistKey), 'utf8');
lib/cloud-sync/manifest.ts:32:  dataRoot: string, playlistKey: string, videoId: string, baseline: VideoBaseline,
lib/cloud-sync/manifest.ts:35:  m.videos[videoId] = baseline;
lib/cloud-sync/manifest.ts:36:  await atomicWrite(manifestPath(dataRoot, playlistKey), JSON.stringify(m, null, 2));
tests/lib/cloud-sync/manifest.test.ts:1:// tests/lib/cloud-sync/manifest.test.ts
tests/lib/cloud-sync/manifest.test.ts:5:import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';
tests/lib/cloud-sync/manifest.test.ts:9:it('returns an empty manifest when the file is missing', async () => {
tests/lib/cloud-sync/manifest.test.ts:14:it('returns an empty manifest (no throw) on a corrupt file', async () => {
tests/lib/cloud-sync/manifest.test.ts:16:  await fs.mkdir(path.dirname(manifestPath(r, 'PL1')), { recursive: true });
tests/lib/cloud-sync/manifest.test.ts:17:  await fs.writeFile(manifestPath(r, 'PL1'), '{not json', 'utf8');
tests/lib/cloud-sync/manifest.test.ts:21:it('round-trips a written baseline', async () => {
tests/lib/cloud-sync/regenerate-stamp.test.ts:29:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/lib/cloud-sync/regenerate-stamp.test.ts:57:  summaryMd: SUMMARY_MD,
lib/dig/generate.ts:125:   *  the local dig-section path, which never reserves/releases a spend_ledger entry. */
tests/lib/cloud-sync/backfill.test.ts:8:  overallScore: 3, summaryMd: '001_title.md', processedAt: '2026-01-01T00:00:00.000Z', // KEY, not body
tests/lib/cloud-sync/backfill.test.ts:14:it('hashes the MD BODY, not the summaryMd key (Blocking ①)', () => {
tests/lib/cloud-sync/backfill.test.ts:18:  expect(s.summaryMdKey).toBe('001_title.md');
tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
tests/lib/cloud-sync/backfill.test.ts:31:  expect(s.summaryMdKey).toBeNull();
tests/lib/cloud-sync/companion.test.ts:4:const env = (sourceMdHash?: string): ModelEnvelope => ({
tests/lib/cloud-sync/companion.test.ts:7:  ...(sourceMdHash ? { sourceMdHash } : {}),
tests/lib/cloud-sync/companion.test.ts:13:it('deletes the receiver model when the envelope does not match', () => {
tests/lib/cloud-sync/companion.test.ts:15:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
tests/lib/cloud-sync/companion.test.ts:17:it('deletes when the legacy envelope lacks sourceMdHash', () => {
tests/lib/cloud-sync/companion.test.ts:19:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
tests/lib/cloud-sync/companion.test.ts:21:it('deletes when the sender has no model at all', () => {
tests/lib/cloud-sync/companion.test.ts:23:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
tests/lib/cloud-sync/schema.test.ts:8:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
tests/lib/cloud-sync/schema.test.ts:32:  it('accepts an optional sourceMdHash', () => {
tests/lib/cloud-sync/schema.test.ts:33:    expect(ModelEnvelopeSchema.parse({ ...env, sourceMdHash: 'deadbeef' }).sourceMdHash).toBe('deadbeef');
lib/storage/supabase/supabase-blob-store.ts:23:  async get(p: Principal, key: string): Promise<Buffer | null> {
lib/storage/supabase/supabase-blob-store.ts:36:    return (await this.get(p, key)) !== null;
lib/storage/supabase/supabase-blob-store.ts:39:  async delete(p: Principal, key: string): Promise<void> {
lib/storage/supabase/supabase-blob-store.ts:54:    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
lib/storage/supabase/supabase-blob-store.ts:71:  async deletePrefix(p: Principal, prefix: string): Promise<void> {
lib/html-doc/generate.ts:22:  const index = await store.readIndex(principal);
lib/html-doc/generate.ts:25:  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');
lib/html-doc/generate.ts:30:  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
lib/html-doc/generate.ts:32:    throw new Error(`source note not found on disk: ${video.summaryMd}`);
lib/html-doc/generate.ts:37:  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field
lib/html-doc/generate.ts:49:  const base = video.summaryMd.replace(/\.md$/, '');
lib/html-doc/generate.ts:51:    sourceMd: video.summaryMd,
lib/html-doc/generate.ts:56:    // Stage 3 (§4.2): hash the MD BODY (`md`, line ~33), NOT `sourceMd`/`video.summaryMd`
lib/html-doc/generate.ts:58:    // filename-hash would never match and every synced companion would be deleted.
lib/html-doc/generate.ts:59:    sourceMdHash: mdHash(md),
lib/html-doc/generate.ts:74:    await resolvedBlob.delete(principal, htmlFilename).catch(() => { /* ignore cleanup error */ });
lib/cloud-sync/registry.ts:12:    return u.searchParams.get('list');
lib/cloud-sync/registry.ts:26:      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:14://    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
lib/cloud-sync/sync-run.ts:15://    tuple is verified durable — stage → verify → promote → finalize → verify → baseline (F2).
lib/cloud-sync/sync-run.ts:32:} from './manifest';
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:58:/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
lib/cloud-sync/sync-run.ts:59:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
lib/cloud-sync/sync-run.ts:60:  if (!video.summaryMd) return null;
lib/cloud-sync/sync-run.ts:61:  const buf = await blob.get(p, video.summaryMd);
lib/cloud-sync/sync-run.ts:69:  const [l, c] = await Promise.all([local.readIndex(localP), cloud.readIndex(cloudP)]);
lib/cloud-sync/sync-run.ts:75:  const idx = await store.readIndex(p);
lib/cloud-sync/sync-run.ts:85: *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
lib/cloud-sync/sync-run.ts:106: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
lib/cloud-sync/sync-run.ts:117:  delete v.serialNumber;
lib/cloud-sync/sync-run.ts:118:  delete v.playlistIndex;
lib/cloud-sync/sync-run.ts:119:  delete v.removedFromPlaylist;
lib/cloud-sync/sync-run.ts:121:  delete v.updatedAt;
lib/cloud-sync/sync-run.ts:122:  delete v.summaryReady;
lib/cloud-sync/sync-run.ts:130: *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
lib/cloud-sync/sync-run.ts:136:  const idx = await to.readIndex(toP);
lib/cloud-sync/sync-run.ts:150:  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
lib/cloud-sync/sync-run.ts:151:  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
lib/cloud-sync/sync-run.ts:152:  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
lib/cloud-sync/sync-run.ts:157:  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
lib/cloud-sync/sync-run.ts:160:  if (video.summaryMd && mdBody == null) {
lib/cloud-sync/sync-run.ts:161:    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
lib/cloud-sync/sync-run.ts:167:  if (video.summaryMd && mdBody != null) {
lib/cloud-sync/sync-run.ts:169:    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
lib/cloud-sync/sync-run.ts:170:    const staged = await toBlob.get(toP, ref.tempKey);
lib/cloud-sync/sync-run.ts:184:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
lib/cloud-sync/sync-run.ts:186:    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
lib/cloud-sync/sync-run.ts:187:    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
lib/cloud-sync/sync-run.ts:188:    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
lib/cloud-sync/sync-run.ts:189:    delete sanitized.artifacts.summaryMd;
lib/cloud-sync/sync-run.ts:193:  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
lib/cloud-sync/sync-run.ts:194:  // (an update against an absent row silently no-ops; never advance a baseline for that).
lib/cloud-sync/sync-run.ts:195:  const after = await to.readIndex(toP);
lib/cloud-sync/sync-run.ts:201:  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
lib/cloud-sync/sync-run.ts:202:  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
lib/cloud-sync/sync-run.ts:204:    const art = (rec as any).artifacts?.summaryMd;
lib/cloud-sync/sync-run.ts:205:    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
lib/cloud-sync/sync-run.ts:206:      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
lib/cloud-sync/sync-run.ts:211:/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
lib/cloud-sync/sync-run.ts:212: *  side's values, so this is a true agreed baseline. */
lib/cloud-sync/sync-run.ts:213:function baselineFromOneSided(
lib/cloud-sync/sync-run.ts:274: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
lib/cloud-sync/sync-run.ts:275: *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
lib/cloud-sync/sync-run.ts:279:  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
lib/cloud-sync/sync-run.ts:280:  if (body == null || !winnerVideo.summaryMd) {
lib/cloud-sync/sync-run.ts:284:  const key = winnerVideo.summaryMd;
lib/cloud-sync/sync-run.ts:287:  const staged = await loser.blob.get(loser.p, ref.tempKey);
lib/cloud-sync/sync-run.ts:300:  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
lib/cloud-sync/sync-run.ts:304:    summaryMd: key,
lib/cloud-sync/sync-run.ts:320:    // readIndex reads falsy → forces re-render.
lib/cloud-sync/sync-run.ts:335:    artifacts: { summaryMd: { key, status: 'promoted' } },
lib/cloud-sync/sync-run.ts:343: *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
lib/cloud-sync/sync-run.ts:348:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:349:  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
lib/cloud-sync/sync-run.ts:356:  // deleteReceiverModel — best-effort; a missing model blob is not an error.
lib/cloud-sync/sync-run.ts:357:  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
lib/cloud-sync/sync-run.ts:361:/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
lib/cloud-sync/sync-run.ts:363: *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
lib/cloud-sync/sync-run.ts:364: *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
lib/cloud-sync/sync-run.ts:396:/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
lib/cloud-sync/sync-run.ts:397: *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
lib/cloud-sync/sync-run.ts:398: *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
lib/cloud-sync/sync-run.ts:400: *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:439:    const manifest = await readManifest(dataRoot, key);
lib/cloud-sync/sync-run.ts:445:        const base = manifest.videos[id];
lib/cloud-sync/sync-run.ts:447:        // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
lib/cloud-sync/sync-run.ts:453:            report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
lib/cloud-sync/sync-run.ts:457:            const body = await readMdBody(from.blob, from.p, present);
lib/cloud-sync/sync-run.ts:460:            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
lib/cloud-sync/sync-run.ts:484:        //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
lib/cloud-sync/sync-run.ts:486:        //    "seen" for delete-inference (baseline present).
lib/cloud-sync/sync-run.ts:491:        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
lib/cloud-sync/sync-run.ts:492:        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
lib/cloud-sync/sync-run.ts:495:        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
lib/cloud-sync/sync-run.ts:504:        //    recorded a full-agreement baseline; run 2 then saw identical bodies and skipped, making
lib/cloud-sync/sync-run.ts:506:        //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
lib/cloud-sync/sync-run.ts:508:        //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
lib/cloud-sync/sync-run.ts:510:        if (lv.summaryMd && la.mdHash == null) throw new Error(`local MD body unreadable for ${id}`);
lib/cloud-sync/sync-run.ts:511:        if (cv.summaryMd && ca.mdHash == null) throw new Error(`cloud MD body unreadable for ${id}`);
lib/cloud-sync/sync-run.ts:518:        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
lib/cloud-sync/sync-run.ts:521:          report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:529:        if (decision.needsRegen) report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:556:        // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
lib/cloud-sync/sync-run.ts:557:        //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
tests/lib/cloud-sync/reconcile-class-b.test.ts:17:  it('only local changed vs baseline → take local', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:20:  it('only cloud changed vs baseline → take cloud', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:23:  it('a clear on one side (present→absent vs baseline) propagates', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:30:  it('a same-value re-add (clear→retype same text, advanced ts) is NOT dropped (round-v8 M-1)', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:31:    // baseline present "x"@t1; local cleared@t2; cloud re-added same "x"@t3.
tests/lib/cloud-sync/reconcile-class-b.test.ts:32:    // cloud's (value,editedAt) differs from baseline (ts advanced) → cloud changed;
tests/lib/cloud-sync/reconcile-class-b.test.ts:36:  it('no baseline + differ → newer per-field editedAt wins', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:39:  it('present one side, absent other, no baseline → copy (additive)', () => {
lib/dig/slide-crop-cache.ts:20:  const prev = writeChains.get(cf) ?? Promise.resolve();
lib/dig/slides.ts:7: * Each token owns its own temp clip, which is always deleted in `finally` regardless
lib/dig/slides.ts:17: * - The temp clip is always deleted in `finally`.
lib/dig/slides.ts:182:      usedNames.delete(assetName);
lib/dig/slides.ts:198:      usedNames.delete(assetName); // failed capture: free the name
lib/storage/supabase/supabase-metadata-store.ts:9:// before any write to `videos.data`. readIndex() surfaces `updatedAt`
lib/storage/supabase/supabase-metadata-store.ts:11:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
lib/storage/supabase/supabase-metadata-store.ts:14:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
lib/storage/supabase/supabase-metadata-store.ts:27:  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
lib/storage/supabase/supabase-metadata-store.ts:29:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/supabase/supabase-metadata-store.ts:53:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
lib/storage/supabase/supabase-metadata-store.ts:54:            .artifacts?.summaryMd?.status === 'promoted',
lib/storage/supabase/supabase-metadata-store.ts:171:  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
lib/storage/supabase/supabase-metadata-store.ts:173:  async deleteVideo(p: Principal, videoId: string): Promise<void> {
lib/storage/supabase/supabase-metadata-store.ts:177:      .delete()
lib/storage/supabase/supabase-metadata-store.ts:279:  // deletePlaylist: hard-delete a playlist row owned by the caller (Task 8).
lib/storage/supabase/supabase-metadata-store.ts:283:  // effect — no separate cleanup calls here. A non-owner/nonexistent id deletes 0 rows
lib/storage/supabase/supabase-metadata-store.ts:286:  async deletePlaylist(p: Principal, playlistId: string): Promise<void> {
lib/storage/supabase/supabase-metadata-store.ts:289:    if (!ownerId) throw new Error('deletePlaylist: no authenticated user');
lib/storage/supabase/supabase-metadata-store.ts:293:      .delete()
lib/html-doc/ensure.ts:30:  const video = (await store.readIndex(principal)).videos.find((v) => v.id === videoId);
lib/html-doc/ensure.ts:32:  if (!video.summaryMd) throw new Error('no summary note for this video');
lib/html-doc/ensure.ts:35:  const base = video.summaryMd.replace(/\.md$/, '');
lib/cloud-sync/reconcile-class-b.ts:12:/** Changed vs baseline is over the (value, editedAt) PAIR, not value alone (§5.4). */
lib/cloud-sync/reconcile-class-b.ts:22:export function reconcileField(local: FieldState, cloud: FieldState, baseline: Baseline): FieldMerge {
lib/cloud-sync/reconcile-class-b.ts:26:  // and leave baseline/live timestamp drift (round-2 H1). Truly-equal pair → 'equal' (no write).
lib/cloud-sync/reconcile-class-b.ts:35:  const lChanged = changed(local, baseline);
lib/cloud-sync/reconcile-class-b.ts:36:  const cChanged = changed(cloud, baseline);
lib/cloud-sync/reconcile-class-b.ts:41:  // both changed (or neither vs an absent baseline but values differ) → newer per-field ts wins.
lib/cloud-sync/reconcile-class-b.ts:57:  baseline: VideoBaseline['classB'],
lib/cloud-sync/reconcile-class-b.ts:60:  for (const f of FIELDS) out[f] = reconcileField(local[f], cloud[f], baseline[f] ?? {});
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
lib/dig/companion-doc.ts:394:    const body = bodyMap.get(s.sectionId);
lib/dig/companion-doc.ts:524:  const prev = writeChains.get(digDeeperPath) ?? Promise.resolve();
lib/html-doc/build-doc-html.ts:73:  // Companion-path containment first, so it keeps independent 400 coverage before summaryMd derivation.
lib/html-doc/build-doc-html.ts:93:  } else if (video.summaryMd) {
lib/html-doc/build-doc-html.ts:94:    const sumRel = video.summaryMd;
lib/html-doc/build-doc-html.ts:102:  let summaryMdPath: string;
lib/html-doc/build-doc-html.ts:104:    summaryMdPath = assertIndexRelPathWithin(outputFolder, path.join(relDir, `${base}.md`));
lib/html-doc/build-doc-html.ts:110:  let summaryMdContent: string;
lib/html-doc/build-doc-html.ts:112:    summaryMdContent = fs.readFileSync(summaryMdPath, 'utf-8');
lib/html-doc/build-doc-html.ts:119:    parsed = parseSummaryMarkdown(summaryMdContent);
lib/html-doc/build-doc-html.ts:135:  const cropMap = await prepareSlideCropMap(dug, summaryMdPath);
lib/html-doc/build-doc-html.ts:142:      mdPath: summaryMdPath,
lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
lib/html-doc/rerender.ts:37:  const index = await store.readIndex(principal);
lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
lib/html-doc/rerender.ts:42:  const base = video.summaryMd.replace(/\.md$/, '');
lib/html-doc/rerender.ts:48:    // Fail closed on a crafted summaryMd that escapes the output folder. assertIndexRelPathWithin
lib/html-doc/rerender.ts:50:    assertIndexRelPathWithin(outputFolder, video.summaryMd, '.md');
lib/html-doc/rerender.ts:51:    const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
lib/html-doc/rerender.ts:64:  parsed.sourceMd = video.summaryMd;
lib/html-doc/rerender.ts:78:  summaryMd: string | null;
lib/html-doc/rerender.ts:101:  const index = await store.readIndex(principal);
lib/html-doc/rerender.ts:118:        summaryMd: video.summaryMd,
lib/html-doc/rerender.ts:126:      tally.details.push({ summaryMd: video.summaryMd, status: 'error', message: (err as Error).message });
lib/html-doc/serve-summary-core.ts:43:  const index = await bundle.metadataStore.readIndex(principal);
lib/html-doc/serve-summary-core.ts:47:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
lib/html-doc/serve-summary-core.ts:48:    .artifacts?.summaryMd;
lib/html-doc/serve-summary-core.ts:53:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
lib/html-doc/serve-summary-core.ts:54:  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
lib/html-doc/serve-summary-core.ts:56:  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
lib/html-doc/serve-summary-core.ts:66:  const mdBytes = await bundle.blobStore.get(principal, mdKey);
lib/html-doc/serve-summary-core.ts:70:  // derived deterministically from the SAME summaryMd key the model store is keyed on.
lib/html-doc/serve-summary-core.ts:114:    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
lib/cloud-sync/backfill.ts:5:// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
lib/cloud-sync/backfill.ts:6:// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
lib/cloud-sync/backfill.ts:10:    summaryMdKey: video.summaryMd ?? null,
lib/html-doc/batch.ts:21:  if (!video.summaryMd) return [];
lib/html-doc/batch.ts:24:    const md = await fs.readFile(path.join(outputFolder, video.summaryMd), 'utf8');
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
lib/html-doc/batch.ts:43:    const gv = versionById.get(s.sectionId);
lib/html-doc/batch.ts:57:  const index = await store.readIndex(principal);
lib/html-doc/batch.ts:63:    const v = byId.get(id);
lib/cloud-sync/types.ts:5:  summaryMdKey: string | null;    // the blob KEY (video.summaryMd) — NOT the body
lib/cloud-sync/types.ts:30:/** Manifest baseline for one video (§8). */
lib/dig/cloud/resolve-summary-key.ts:3:/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
lib/dig/cloud/resolve-summary-key.ts:4: *  falling back to the top-level `summaryMd` — validated via `assertCloudSummaryMdKey`. Returns
lib/dig/cloud/resolve-summary-key.ts:7: *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
lib/dig/cloud/resolve-summary-key.ts:9: *  top-level `summaryMd` fallback for videos with no artifact record. The dig TRIGGER owns that
lib/dig/cloud/resolve-summary-key.ts:13:  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
lib/dig/cloud/resolve-summary-key.ts:14:  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
lib/html-doc/nav.ts:16:  const outputFolder = new URLSearchParams(loc.search).get('outputFolder');
lib/html-doc/nav.ts:211:  var outputFolder=_sp.get('outputFolder');
lib/html-doc/nav.ts:216:  if(_sp.get('type')==='dig-deeper'){
lib/html-doc/nav.ts:348:        u2.searchParams.delete('dig');
lib/html-doc/nav.ts:360:        var digN=isPageshow?null:_sp.get('dig');
lib/html-doc/nav.ts:548:  var playlist=new URLSearchParams(location.search).get('playlist');
lib/dig/cloud/load-dig-for-serve.ts:38:    const bytes = await load.bundle.blobStore.get(load.principal, key);
lib/html-doc/eligibility.ts:7:  return !!v.summaryMd;
lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
lib/html-doc/eligibility.ts:19: *   A video with no summaryMd is never eligible (nothing to generate from).
lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
lib/html-doc/render-dig-deeper.ts:120:      const box = cropMap.get(absPath) ?? null;
lib/html-doc/serve-doc.ts:47:   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
lib/html-doc/serve-doc.ts:48:   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
lib/html-doc/serve-doc.ts:110:      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
lib/html-doc/dig-merge.ts:101:      const matched = dugBySectionId.get(startSec);
lib/html-doc/dig-merge.ts:135:      const existing = dugByTitle.get(d.title) ?? [];
lib/html-doc/dig-merge.ts:144:    const candidates = dugByTitle.get(ms.title);

exec
/bin/bash -lc 'ls -la docs/reviews && rg -n "B1|H-R2|WB-H|CONVERGED|Blocking|summaryMd|unreadable|null" docs/reviews/whole-branch-cloud-sync*.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
total 13688
drwxr-xr-x@ 496 kujinlee  staff    15872 Jul 18 09:05 .
drwxr-xr-x@  20 kujinlee  staff      640 Jul 17 19:09 ..
-rw-r--r--@   1 kujinlee  staff     4022 Jul  9 04:27 1d-live-gemini-gates.md
-rw-r--r--@   1 kujinlee  staff     4334 Jul  2 09:02 ask-gemini-launcher-plan-review.md
-rw-r--r--@   1 kujinlee  staff     2118 Jul  2 09:02 auto-pdf-export-review.md
-rw-r--r--@   1 kujinlee  staff     2977 Jul  2 09:02 batch-docs-phase-a-final-review.md
-rw-r--r--@   1 kujinlee  staff     3318 Jul  2 09:02 batch-docs-phase-b-final-review.md
-rw-r--r--@   1 kujinlee  staff     2633 Jul  2 09:02 branch-deep-dive-transcript-fallback-final-review.md
-rw-r--r--@   1 kujinlee  staff     3230 Jul  2 09:02 branch-dig-deeper-v2-review.md
-rw-r--r--@   1 kujinlee  staff     3757 Jul  2 09:02 branch-transcript-fallback-gemini-final-review.md
-rw-r--r--@   1 kujinlee  staff     7484 Jul  2 09:02 cloud-publishing-architecture-spec-codex.md
-rw-r--r--@   1 kujinlee  staff     3224 Jul 13 22:26 cloud-run-blockers-review.md
-rw-r--r--@   1 kujinlee  staff     9854 Jul  2 09:02 deep-dive-html-final-review.md
-rw-r--r--@   1 kujinlee  staff     9063 Jul  2 09:02 deep-dive-html-plan-review.md
-rw-r--r--@   1 kujinlee  staff    20740 Jul  2 09:02 deep-dive-html-spec-review.md
-rw-r--r--@   1 kujinlee  staff     1983 Jul  2 09:02 deep-dive-removal-codex.md
-rw-r--r--@   1 kujinlee  staff     2495 Jul  2 09:02 dig-captions-final-review.md
-rw-r--r--@   1 kujinlee  staff     3237 Jul  2 09:02 dig-deeper-render-polish-review.md
-rw-r--r--@   1 kujinlee  staff     2482 Jul  2 09:02 dig-expand-all-nonblocking-codex.md
-rw-r--r--@   1 kujinlee  staff     1791 Jul  2 09:02 dig-expand-all-nonblocking-review.md
-rw-r--r--@   1 kujinlee  staff     2647 Jul  2 09:02 dig-slide-size-control-final-review.md
-rw-r--r--@   1 kujinlee  staff     2178 Jul  2 09:02 dig-subheadings-final-review.md
-rw-r--r--@   1 kujinlee  staff     3311 Jul  2 09:02 final-dig-code-slide-as-image-review.md
-rw-r--r--@   1 kujinlee  staff     2969 Jul  2 09:02 final-dig-frame-capture-quality-review.md
-rw-r--r--@   1 kujinlee  staff     1482 Jul  2 09:02 final-doc-timestamp-gold-url-review.md
-rw-r--r--@   1 kujinlee  staff    13764 Jul  2 09:02 final-html-doc-review.md
-rw-r--r--@   1 kujinlee  staff     3457 Jul  2 09:02 final-resummarize-review.md
-rw-r--r--@   1 kujinlee  staff     5546 Jul  2 09:02 final-section-timestamps-codex.md
-rw-r--r--@   1 kujinlee  staff     3128 Jul  2 09:02 final-section-timestamps-review.md
-rw-r--r--@   1 kujinlee  staff     4598 Jul  2 09:02 final-summary-deepdive-review.md
-rw-r--r--@   1 kujinlee  staff     1699 Jul  2 09:02 final-sync-progress-print-export-review.md
-rw-r--r--@   1 kujinlee  staff     2955 Jul  2 09:02 fix-dig-drop-inline-citations-codex.md
-rw-r--r--@   1 kujinlee  staff     2849 Jul  2 09:02 fix-dig-drop-inline-citations-review.md
-rw-r--r--@   1 kujinlee  staff     2669 Jul  2 09:02 gemini-responseschema-codex.md
-rw-r--r--@   1 kujinlee  staff     2916 Jul  2 09:02 gemini-responseschema-review.md
-rw-r--r--@   1 kujinlee  staff    13706 Jul  2 09:02 lib-core-html-doc-review.md
-rw-r--r--@   1 kujinlee  staff     3626 Jul  2 09:02 list-columns-channel-duration-review.md
-rw-r--r--@   1 kujinlee  staff     2828 Jul  2 09:02 pdf-removal-codex.md
-rw-r--r--@   1 kujinlee  staff     6854 Jul 10 03:35 plan-1f-a-claude-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     7840 Jul 10 03:35 plan-1f-a-claude-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff    13464 Jul 10 03:35 plan-1f-a-claude.md
-rw-r--r--@   1 kujinlee  staff     5998 Jul 10 03:35 plan-1f-a-codex-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3579 Jul 10 03:35 plan-1f-a-codex-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff   368716 Jul 10 03:35 plan-1f-a-codex.md
-rw-r--r--@   1 kujinlee  staff     4075 Jul 10 08:25 plan-1f-b-claude.md
-rw-r--r--@   1 kujinlee  staff     7673 Jul 10 08:25 plan-1f-b-codex.md
-rw-r--r--@   1 kujinlee  staff     3843 Jul 10 14:48 plan-1f-c-claude.md
-rw-r--r--@   1 kujinlee  staff     2921 Jul 10 14:48 plan-1f-c-codex.md
-rw-r--r--@   1 kujinlee  staff     2725 Jul 10 18:29 plan-1g-claude.md
-rw-r--r--@   1 kujinlee  staff     2340 Jul 10 18:29 plan-1g-codex.md
-rw-r--r--@   1 kujinlee  staff     1863 Jul 10 18:29 plan-1g-round2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3258 Jul 11 07:33 plan-2a-claude.md
-rw-r--r--@   1 kujinlee  staff     2612 Jul 11 07:33 plan-2a-codex.md
-rw-r--r--@   1 kujinlee  staff     2306 Jul 11 15:29 plan-2b-cloud-ingest-codex-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     2191 Jul 11 15:29 plan-2b-cloud-ingest-codex-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     1831 Jul 11 15:29 plan-2b-cloud-ingest-codex-v4-rereview.md
-rw-r--r--@   1 kujinlee  staff     3995 Jul 11 15:29 plan-2b-cloud-ingest-codex.md
-rw-r--r--@   1 kujinlee  staff     4396 Jul 11 15:29 plan-2b-cloud-ingest-review.md
-rw-r--r--@   1 kujinlee  staff     2743 Jul 11 15:29 plan-2b-cloud-ingest-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     2703 Jul 11 15:29 plan-2b-cloud-ingest-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     2257 Jul 11 15:29 plan-2b-cloud-ingest-v4-rereview.md
-rw-r--r--@   1 kujinlee  staff     9433 Jul 11 17:37 plan-2c-cloud-doc-consumption-codex-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff    10532 Jul 11 17:37 plan-2c-cloud-doc-consumption-codex.md
-rw-r--r--@   1 kujinlee  staff     4762 Jul 11 17:37 plan-2c-cloud-doc-consumption-review.md
-rw-r--r--@   1 kujinlee  staff     3946 Jul 11 17:37 plan-2c-cloud-doc-consumption-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     4016 Jul  2 09:02 plan-auto-pdf-export-codex.md
-rw-r--r--@   1 kujinlee  staff     2666 Jul  2 09:02 plan-auto-pdf-export-plan-codex.md
-rw-r--r--@   1 kujinlee  staff     3031 Jul  2 09:02 plan-batch-docs-phase-a-codex.md
-rw-r--r--@   1 kujinlee  staff     2606 Jul  2 09:02 plan-batch-docs-phase-b-codex.md
-rw-r--r--@   1 kujinlee  staff     5270 Jul 15 06:48 plan-cloud-dig-deeper-frontend-v1-review.md
-rw-r--r--@   1 kujinlee  staff     4145 Jul 15 06:48 plan-cloud-dig-deeper-frontend-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3867 Jul 12 17:26 plan-cloud-dig-generation-codex-v2.md
-rw-r--r--@   1 kujinlee  staff     6264 Jul 12 17:26 plan-cloud-dig-generation-codex.md
-rw-r--r--@   1 kujinlee  staff     6683 Jul 14 17:56 plan-cloud-dig-serving-v1-review.md
-rw-r--r--@   1 kujinlee  staff     4756 Jul 14 17:56 plan-cloud-dig-serving-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     9660 Jul 12 05:08 plan-cloud-pdf-claude-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     6234 Jul 12 05:08 plan-cloud-pdf-claude-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff    15669 Jul 12 05:08 plan-cloud-pdf-claude.md
-rw-r--r--@   1 kujinlee  staff     1482 Jul 12 05:08 plan-cloud-pdf-codex-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     1007 Jul 12 05:08 plan-cloud-pdf-codex-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     5351 Jul 12 05:08 plan-cloud-pdf-codex.md
-rw-r--r--@   1 kujinlee  staff     5162 Jul 17 18:04 plan-cloud-sync-m2a-claude-r1.md
-rw-r--r--@   1 kujinlee  staff     4073 Jul 17 18:32 plan-cloud-sync-m2a-claude-r2.md
-rw-r--r--@   1 kujinlee  staff     4063 Jul 17 18:45 plan-cloud-sync-m2a-claude-r3.md
-rw-r--r--@   1 kujinlee  staff     2466 Jul 17 18:55 plan-cloud-sync-m2a-claude-r4.md
-rw-r--r--@   1 kujinlee  staff     3750 Jul 17 19:03 plan-cloud-sync-m2a-claude-r5.md
-rw-r--r--@   1 kujinlee  staff     3451 Jul 17 19:08 plan-cloud-sync-m2a-claude-r6.md
-rw-r--r--@   1 kujinlee  staff    12076 Jul 17 17:57 plan-cloud-sync-m2a-codex-r1.md
-rw-r--r--@   1 kujinlee  staff    10362 Jul 17 18:20 plan-cloud-sync-m2a-codex-r2.md
-rw-r--r--@   1 kujinlee  staff     8336 Jul 17 18:35 plan-cloud-sync-m2a-codex-r3.md
-rw-r--r--@   1 kujinlee  staff     7078 Jul 17 18:48 plan-cloud-sync-m2a-codex-r4.md
-rw-r--r--@   1 kujinlee  staff     6142 Jul 17 18:57 plan-cloud-sync-m2a-codex-r5.md
-rw-r--r--@   1 kujinlee  staff     5294 Jul 17 19:06 plan-cloud-sync-m2a-codex-r6.md
-rw-r--r--@   1 kujinlee  staff     5879 Jul  2 09:02 plan-darkmode-html-export-adversarial.md
-rw-r--r--@   1 kujinlee  staff     4628 Jul  2 09:02 plan-deep-dive-regeneration-review.md
-rw-r--r--@   1 kujinlee  staff     2465 Jul  2 09:02 plan-deep-dive-transcript-fallback-review.md
-rw-r--r--@   1 kujinlee  staff     2897 Jul  2 09:02 plan-deepdive-h3-timestamps-review.md
-rw-r--r--@   1 kujinlee  staff    14826 Jul  2 09:02 plan-dig-code-slide-as-image-review.md
-rw-r--r--@   1 kujinlee  staff     5645 Jul  2 09:02 plan-dig-deeper-screenshots-codex.md
-rw-r--r--@   1 kujinlee  staff     3808 Jul  2 09:02 plan-dig-deeper-v2-review.md
-rw-r--r--@   1 kujinlee  staff     2174 Jul  2 09:02 plan-dig-expand-all-nonblocking-codex.md
-rw-r--r--@   1 kujinlee  staff     2260 Jul  2 09:02 plan-dig-frame-capture-quality-review.md
-rw-r--r--@   1 kujinlee  staff     3091 Jul  2 09:02 plan-dig-image-sizing-codex.md
-rw-r--r--@   1 kujinlee  staff     2900 Jul  2 09:02 plan-dig-section-ask-ai-codex.md
-rw-r--r--@   1 kujinlee  staff     2182 Jul  2 09:02 plan-dig-section-subheadings-codex.md
-rw-r--r--@   1 kujinlee  staff     3257 Jul  2 09:02 plan-dig-slide-autocrop-codex.md
-rw-r--r--@   1 kujinlee  staff     3546 Jul  2 09:02 plan-dig-slide-captions-codex.md
-rw-r--r--@   1 kujinlee  staff     3696 Jul  2 09:02 plan-dig-slide-capture-fixes-review.md
-rw-r--r--@   1 kujinlee  staff     4761 Jul  2 09:02 plan-dig-slide-selectivity-review.md
-rw-r--r--@   1 kujinlee  staff     3318 Jul  2 09:02 plan-dig-slide-size-control-codex.md
-rw-r--r--@   1 kujinlee  staff     3513 Jul  2 09:02 plan-dig-window-capping-rev3-review.md
-rw-r--r--@   1 kujinlee  staff     3812 Jul  2 09:02 plan-dig-window-capping-review.md
-rw-r--r--@   1 kujinlee  staff     2678 Jul  2 09:02 plan-doc-timestamp-gold-url-codex.md
-rw-r--r--@   1 kujinlee  staff     5409 Jul  2 09:02 plan-html-doc-magazine-skim-codex.md
-rw-r--r--@   1 kujinlee  staff     1846 Jul  2 09:02 plan-lenient-timestamp-resolver-review.md
-rw-r--r--@   1 kujinlee  staff     5269 Jul  2 09:02 plan-persist-magazine-model-adversarial.md
-rw-r--r--@   1 kujinlee  staff     4528 Jul  2 09:02 plan-personal-review-codex.md
-rw-r--r--@   1 kujinlee  staff     2049 Jul  2 09:02 plan-playlist-index-current-position-review.md
-rw-r--r--@   1 kujinlee  staff     3552 Jul  2 09:02 plan-playlist-picker-codex.md
-rw-r--r--@   1 kujinlee  staff     3028 Jul  2 09:02 plan-pregenerate-summary-html-codex.md
-rw-r--r--@   1 kujinlee  staff     3204 Jul  2 09:02 plan-quick-reference-fallback-review.md
-rw-r--r--@   1 kujinlee  staff     5680 Jul  2 09:02 plan-quick-view-codex.md
-rw-r--r--@   1 kujinlee  staff     5418 Jul 17 08:26 plan-reservation-release-v1-claude.md
-rw-r--r--@   1 kujinlee  staff     3930 Jul 17 08:26 plan-reservation-release-v1-codex.md
-rw-r--r--@   1 kujinlee  staff     3046 Jul 17 08:26 plan-reservation-release-v2-claude.md
-rw-r--r--@   1 kujinlee  staff     2992 Jul 17 08:26 plan-reservation-release-v2-codex.md
-rw-r--r--@   1 kujinlee  staff     3437 Jul 17 08:26 plan-reservation-release-v3-claude.md
-rw-r--r--@   1 kujinlee  staff     2099 Jul 17 08:26 plan-reservation-release-v3-codex.md
-rw-r--r--@   1 kujinlee  staff     3137 Jul 17 08:26 plan-reservation-release-v4-claude.md
-rw-r--r--@   1 kujinlee  staff     1406 Jul 17 08:26 plan-reservation-release-v4-codex.md
-rw-r--r--@   1 kujinlee  staff     3460 Jul  2 09:02 plan-resummarize-codex.md
-rw-r--r--@   1 kujinlee  staff     4298 Jul  2 09:02 plan-section-timestamps-review.md
-rw-r--r--@   1 kujinlee  staff     3423 Jul  2 09:02 plan-serial-number-filename-prefix-review.md
-rw-r--r--@   1 kujinlee  staff     4573 Jul  2 11:02 plan-stage-1b-auth-rls-schema-codex.md
-rw-r--r--@   1 kujinlee  staff    12839 Jul  6 15:41 plan-stage-1c-supabase-adapters-codex.md
-rw-r--r--@   1 kujinlee  staff     2120 Jul  9 04:27 plan-stage-1d-claude-v2.md
-rw-r--r--@   1 kujinlee  staff     4270 Jul  9 04:27 plan-stage-1d-claude.md
-rw-r--r--@   1 kujinlee  staff     1278 Jul  9 04:27 plan-stage-1d-codex-v2.md
-rw-r--r--@   1 kujinlee  staff     3010 Jul  9 04:27 plan-stage-1d-codex.md
-rw-r--r--@   1 kujinlee  staff     2203 Jul  9 04:27 plan-stage-1d-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     3286 Jul  7 14:41 plan-stage-1e-a-claude-review.md
-rw-r--r--@   1 kujinlee  staff     2508 Jul  7 14:41 plan-stage-1e-a-codex.md
-rw-r--r--@   1 kujinlee  staff     5831 Jul  7 18:54 plan-stage-1e-b-claude-review.md
-rw-r--r--@   1 kujinlee  staff     2533 Jul  7 18:54 plan-stage-1e-b-codex.md
-rw-r--r--@   1 kujinlee  staff     6245 Jul  7 19:19 plan-stage-1e-b-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3531 Jul  8 12:29 plan-stage-1e-c-claude.md
-rw-r--r--@   1 kujinlee  staff     3188 Jul  8 12:29 plan-stage-1e-c-codex.md
-rw-r--r--@   1 kujinlee  staff     2737 Jul  8 12:29 plan-stage-1e-c-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3068 Jul  2 09:02 plan-summary-deepdive-codex.md
-rw-r--r--@   1 kujinlee  staff     3138 Jul  2 09:02 plan-summary-deepdive-navigation-review.md
-rw-r--r--@   1 kujinlee  staff     6799 Jul 15 12:20 plan-summary-section-timestamp-guarantee-v1-review.md
-rw-r--r--@   1 kujinlee  staff     4714 Jul 15 12:20 plan-summary-section-timestamp-guarantee-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     4104 Jul 15 12:20 plan-summary-section-timestamp-guarantee-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     3496 Jul 15 12:20 plan-summary-section-timestamp-guarantee-v4-rereview.md
-rw-r--r--@   1 kujinlee  staff     2027 Jul  2 09:02 plan-sync-progress-print-export-review.md
-rw-r--r--@   1 kujinlee  staff     4363 Jul  2 09:02 plan-timestamp-guard-audit-repair-review.md
-rw-r--r--@   1 kujinlee  staff     3915 Jul  2 09:02 plan-title-primary-playlist-display-codex.md
-rw-r--r--@   1 kujinlee  staff     5764 Jul  2 09:02 plan-transcript-fallback-gemini-review.md
-rw-r--r--@   1 kujinlee  staff     3102 Jul  2 09:02 playlist-picker-final-review.md
-rw-r--r--@   1 kujinlee  staff    19109 Jul 14 06:27 playlist-ux-plan-claude-review.md
-rw-r--r--@   1 kujinlee  staff    22805 Jul 14 06:27 playlist-ux-spec-claude-review.md
-rw-r--r--@   1 kujinlee  staff     5583 Jul 14 06:27 playlist-ux-whole-branch-review.md
-rw-r--r--@   1 kujinlee  staff     3354 Jul  2 09:02 pregenerate-summary-html-final-review.md
-rw-r--r--@   1 kujinlee  staff    18450 Jul 17 08:26 reservation-release-spec-v1-claude.md
-rw-r--r--@   1 kujinlee  staff   162905 Jul 17 08:26 reservation-release-spec-v1-codex.md
-rw-r--r--@   1 kujinlee  staff    15677 Jul 17 08:26 reservation-release-spec-v2-claude.md
-rw-r--r--@   1 kujinlee  staff     6483 Jul 17 08:26 reservation-release-spec-v2-codex.md
-rw-r--r--@   1 kujinlee  staff    13358 Jul 17 08:26 reservation-release-spec-v3-claude.md
-rw-r--r--@   1 kujinlee  staff     4507 Jul 17 08:26 reservation-release-spec-v3-codex.md
-rw-r--r--@   1 kujinlee  staff    12110 Jul 17 08:26 reservation-release-spec-v4-claude.md
-rw-r--r--@   1 kujinlee  staff     3186 Jul 17 08:26 reservation-release-spec-v4-codex.md
-rw-r--r--@   1 kujinlee  staff     7600 Jul 17 08:26 reservation-release-spec-v5-claude.md
-rw-r--r--@   1 kujinlee  staff     2737 Jul 17 08:26 reservation-release-spec-v5-codex.md
-rw-r--r--@   1 kujinlee  staff     7673 Jul 17 08:26 reservation-release-spec-v6-claude.md
-rw-r--r--@   1 kujinlee  staff     1685 Jul 17 08:26 reservation-release-spec-v6-codex.md
-rw-r--r--@   1 kujinlee  staff     6621 Jul 17 08:26 reservation-release-spec-v7-claude.md
-rw-r--r--@   1 kujinlee  staff     1462 Jul 17 08:26 reservation-release-spec-v7-codex.md
-rw-r--r--@   1 kujinlee  staff     4740 Jul  2 09:02 serial-number-filename-prefix-final-review.md
-rw-r--r--@   1 kujinlee  staff    22845 Jul 10 03:35 spec-1f-a-claude-adversarial-v1.md
-rw-r--r--@   1 kujinlee  staff    21277 Jul 10 03:35 spec-1f-a-claude-redteam-v1.md
-rw-r--r--@   1 kujinlee  staff    20982 Jul 10 03:35 spec-1f-a-claude-redteam-v2.md
-rw-r--r--@   1 kujinlee  staff    24960 Jul 10 03:35 spec-1f-a-claude-v3.md
-rw-r--r--@   1 kujinlee  staff    21216 Jul 10 03:35 spec-1f-a-claude-v4.md
-rw-r--r--@   1 kujinlee  staff    25453 Jul 10 03:35 spec-1f-a-claude-v5.md
-rw-r--r--@   1 kujinlee  staff    23462 Jul 10 03:35 spec-1f-a-claude-v6.md
-rw-r--r--@   1 kujinlee  staff    23182 Jul 10 03:35 spec-1f-a-claude-v7.md
-rw-r--r--@   1 kujinlee  staff    20850 Jul 10 03:35 spec-1f-a-claude-verify-v2.md
-rw-r--r--@   1 kujinlee  staff   321657 Jul 10 03:35 spec-1f-a-codex-v3.md
-rw-r--r--@   1 kujinlee  staff   177609 Jul 10 03:35 spec-1f-a-codex-v4.md
-rw-r--r--@   1 kujinlee  staff   255460 Jul 10 03:35 spec-1f-a-codex-v5.md
-rw-r--r--@   1 kujinlee  staff   195312 Jul 10 03:35 spec-1f-a-codex-v6.md
-rw-r--r--@   1 kujinlee  staff   156341 Jul 10 03:35 spec-1f-a-codex-v7.md
-rw-r--r--@   1 kujinlee  staff     6291 Jul 10 08:25 spec-1f-b-claude-v1.md
-rw-r--r--@   1 kujinlee  staff     5257 Jul 10 08:25 spec-1f-b-claude-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     4172 Jul 10 08:25 spec-1f-b-claude-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     5703 Jul 10 08:25 spec-1f-b-codex-v1.md
-rw-r--r--@   1 kujinlee  staff     9826 Jul 10 08:25 spec-1f-b-codex-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff    14011 Jul 10 08:25 spec-1f-b-codex-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     3777 Jul 10 14:48 spec-1f-c-claude-v1.md
-rw-r--r--@   1 kujinlee  staff     3084 Jul 10 14:48 spec-1f-c-claude-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     2529 Jul 10 14:48 spec-1f-c-claude-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     5803 Jul 10 14:48 spec-1f-c-codex-v1.md
-rw-r--r--@   1 kujinlee  staff     3050 Jul 10 14:48 spec-1f-c-codex-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     5755 Jul 10 14:48 spec-1f-c-codex-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     3308 Jul 10 18:29 spec-1g-claude-v1.md
-rw-r--r--@   1 kujinlee  staff     2807 Jul 10 18:29 spec-1g-codex-v1.md
-rw-r--r--@   1 kujinlee  staff     2473 Jul 10 18:29 spec-1g-round2-rereview.md
-rw-r--r--@   1 kujinlee  staff     5110 Jul 11 07:33 spec-2a-claude-v1.md
-rw-r--r--@   1 kujinlee  staff     5493 Jul 11 07:33 spec-2a-codex-v1.md
-rw-r--r--@   1 kujinlee  staff     3393 Jul 11 07:33 spec-2a-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3254 Jul 11 07:33 spec-2a-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     2623 Jul 11 07:33 spec-2a-v4-rereview.md
-rw-r--r--@   1 kujinlee  staff     8817 Jul 12 05:08 spec-cloud-pdf-atomicity.md
-rw-r--r--@   1 kujinlee  staff    10942 Jul 12 05:08 spec-cloud-pdf-claude-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     8127 Jul 12 05:08 spec-cloud-pdf-claude-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff    13808 Jul 12 05:08 spec-cloud-pdf-claude.md
-rw-r--r--@   1 kujinlee  staff     3556 Jul 12 05:08 spec-cloud-pdf-codex-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     1691 Jul 12 05:08 spec-cloud-pdf-codex-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     5855 Jul 12 05:08 spec-cloud-pdf-codex.md
-rw-r--r--@   1 kujinlee  staff     4441 Jul 12 05:08 spec-cloud-pdf-deploy-verification.md
-rw-r--r--@   1 kujinlee  staff     2525 Jul  2 09:02 spec-deep-dive-transcript-fallback-review.md
-rw-r--r--@   1 kujinlee  staff     3941 Jul  2 09:02 spec-deepdive-h3-timestamps-review.md
-rw-r--r--@   1 kujinlee  staff    16988 Jul  2 09:02 spec-dig-code-slide-as-image-review.md
-rw-r--r--@   1 kujinlee  staff    25408 Jul  2 09:02 spec-dig-deeper-in-place-expansion-review.md
-rw-r--r--@   1 kujinlee  staff     5963 Jul  2 09:02 spec-dig-deeper-screenshots-review.md
-rw-r--r--@   1 kujinlee  staff     8620 Jul  2 09:02 spec-dig-deeper-v2-review.md
-rw-r--r--@   1 kujinlee  staff     2308 Jul  2 09:02 spec-dig-doc-readability-codex.md
-rw-r--r--@   1 kujinlee  staff     3414 Jul  2 09:02 spec-dig-image-ask-ai-codex.md
-rw-r--r--@   1 kujinlee  staff     3583 Jul  2 09:02 spec-dig-slide-autocrop-codex.md
-rw-r--r--@   1 kujinlee  staff     3137 Jul  2 09:02 spec-dig-slide-selectivity-review.md
-rw-r--r--@   1 kujinlee  staff     3084 Jul  2 09:02 spec-dig-slide-size-control-codex.md
-rw-r--r--@   1 kujinlee  staff     4973 Jul  2 09:02 spec-lenient-timestamp-resolver-review.md
-rw-r--r--@   1 kujinlee  staff     4248 Jul  2 09:02 spec-personal-review-codex.md
-rw-r--r--@   1 kujinlee  staff     3242 Jul  2 09:02 spec-playlist-index-current-position-review.md
-rw-r--r--@   1 kujinlee  staff     4316 Jul  2 09:02 spec-playlist-picker-codex.md
-rw-r--r--@   1 kujinlee  staff     4179 Jul  2 09:02 spec-quick-reference-fallback-review.md
-rw-r--r--@   1 kujinlee  staff     3169 Jul  2 09:02 spec-serial-number-filename-prefix-review.md
-rw-r--r--@   1 kujinlee  staff     5500 Jul  9 04:27 spec-stage-1d-claude-review.md
-rw-r--r--@   1 kujinlee  staff     2329 Jul  9 04:27 spec-stage-1d-codex.md
-rw-r--r--@   1 kujinlee  staff     6385 Jul  9 04:27 spec-stage-1d-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     5108 Jul  9 04:27 spec-stage-1d-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     5945 Jul  9 04:27 spec-stage-1d-v4-rereview.md
-rw-r--r--@   1 kujinlee  staff     5722 Jul  9 04:27 spec-stage-1d-v5-rereview.md
-rw-r--r--@   1 kujinlee  staff     5148 Jul  9 04:27 spec-stage-1d-v6-rereview.md
-rw-r--r--@   1 kujinlee  staff     3606 Jul  9 04:27 spec-stage-1d-v7-rereview.md
-rw-r--r--@   1 kujinlee  staff     6315 Jul  7 16:17 spec-stage-1e-b-claude-review.md
-rw-r--r--@   1 kujinlee  staff     4735 Jul  7 16:17 spec-stage-1e-b-codex.md
-rw-r--r--@   1 kujinlee  staff     6981 Jul  7 17:07 spec-stage-1e-b-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     6134 Jul  8 12:29 spec-stage-1e-c-claude-review.md
-rw-r--r--@   1 kujinlee  staff     4227 Jul  8 12:29 spec-stage-1e-c-codex.md
-rw-r--r--@   1 kujinlee  staff     3719 Jul  8 12:29 spec-stage-1e-c-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3626 Jul  8 12:29 spec-stage-1e-c-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     4951 Jul  2 09:02 spec-summary-deepdive-navigation-review.md
-rw-r--r--@   1 kujinlee  staff     4826 Jul  2 09:02 spec-summary-deepdive-quality-codex.md
-rw-r--r--@   1 kujinlee  staff     2612 Jul  2 09:02 spec-sync-progress-print-export-review.md
-rw-r--r--@   1 kujinlee  staff     6623 Jul  2 09:02 spec-timestamp-guard-audit-repair-review.md
-rw-r--r--@   1 kujinlee  staff     2442 Jul  2 09:02 spec-transcript-fallback-gemini-review.md
-rw-r--r--@   1 kujinlee  staff     2413 Jul  2 09:02 stage-1a-metadata-store-seam-final-review.md
-rw-r--r--@   1 kujinlee  staff     3364 Jul  2 09:02 stage-1a-metadata-store-seam-plan-codex.md
-rw-r--r--@   1 kujinlee  staff     2399 Jul  2 10:42 stage-1b-auth-rls-schema-spec-codex-rereview.md
-rw-r--r--@   1 kujinlee  staff     4265 Jul  2 10:34 stage-1b-auth-rls-schema-spec-codex.md
-rw-r--r--@   1 kujinlee  staff    14235 Jul  6 15:41 stage-1c-supabase-adapters-spec-codex.md
-rw-r--r--@   1 kujinlee  staff     3884 Jul  7 14:41 stage-1e-a-durable-job-queue-spec-claude-review.md
-rw-r--r--@   1 kujinlee  staff     4060 Jul  7 14:41 stage-1e-a-durable-job-queue-spec-codex.md
-rw-r--r--@   1 kujinlee  staff     1441 Jul  2 09:02 summary-truncation-guard-codex.md
-rw-r--r--@   1 kujinlee  staff     1823 Jul  2 09:02 summary-truncation-guard-review.md
-rw-r--r--@   1 kujinlee  staff     2495 Jul  2 09:02 summary-truncation-resilience-spec-codex.md
-rw-r--r--@   1 kujinlee  staff     1891 Jul  2 09:02 summary-truncation-resilience-stage1-plan-codex.md
-rw-r--r--@   1 kujinlee  staff     2276 Jul  2 09:02 summary-truncation-resilience-stage1-review.md
-rw-r--r--@   1 kujinlee  staff     2047 Jul  2 09:02 summary-truncation-resilience-stage2-plan-codex.md
-rw-r--r--@   1 kujinlee  staff     2280 Jul  2 09:02 summary-truncation-resilience-stage2-review.md
-rw-r--r--@   1 kujinlee  staff     1881 Jul  2 09:02 summary-truncation-resilience-stage3-plan-codex.md
-rw-r--r--@   1 kujinlee  staff     1643 Jul  2 09:02 summary-truncation-resilience-stage3-review.md
-rw-r--r--@   1 kujinlee  staff     1214 Jul  2 18:20 task-1-deps-env-review.md
-rw-r--r--@   1 kujinlee  staff     3387 Jul  8 04:30 task-1-identity-rekey-codex.md
-rw-r--r--@   1 kujinlee  staff     3783 Jul  8 04:30 task-1-identity-rekey-review.md
-rw-r--r--@   1 kujinlee  staff     2379 Jul  2 09:02 task-10-api-routes-codex.md
-rw-r--r--@   1 kujinlee  staff     3080 Jul  2 09:02 task-10-api-routes-review.md
-rw-r--r--@   1 kujinlee  staff     3553 Jul  2 09:02 task-10-e2e-review.md
-rw-r--r--@   1 kujinlee  staff     1843 Jul  2 18:20 task-10-middleware-callback-review.md
-rw-r--r--@   1 kujinlee  staff     1873 Jul  2 09:02 task-11-header-codex.md
-rw-r--r--@   1 kujinlee  staff     2228 Jul  2 09:02 task-11-header-review.md
-rw-r--r--@   1 kujinlee  staff     2704 Jul  2 09:02 task-12-sort-bar-codex.md
-rw-r--r--@   1 kujinlee  staff     3279 Jul  2 09:02 task-12-sort-bar-review.md
-rw-r--r--@   1 kujinlee  staff  1075647 Jul 17 21:51 task-12-sync-run-behaviors-codex.md
-rw-r--r--@   1 kujinlee  staff     2550 Jul  2 09:02 task-13-video-menu-codex.md
-rw-r--r--@   1 kujinlee  staff     3568 Jul  2 09:02 task-13-video-menu-review.md
-rw-r--r--@   1 kujinlee  staff     2253 Jul  2 09:02 task-14-video-list-codex.md
-rw-r--r--@   1 kujinlee  staff     2231 Jul  2 09:02 task-14-video-list-review.md
-rw-r--r--@   1 kujinlee  staff     2614 Jul  2 09:02 task-15-deep-dive-overlay-codex.md
-rw-r--r--@   1 kujinlee  staff     2645 Jul  2 09:02 task-15-deep-dive-overlay-review.md
-rw-r--r--@   1 kujinlee  staff     3379 Jul  2 09:02 task-16-main-page-codex.md
-rw-r--r--@   1 kujinlee  staff     3352 Jul  2 09:02 task-16-main-page-review.md
-rw-r--r--@   1 kujinlee  staff     4049 Jul  2 09:02 task-17-behaviors-codex.md
-rw-r--r--@   1 kujinlee  staff     4190 Jul  2 09:02 task-17-e2e-codex.md
-rw-r--r--@   1 kujinlee  staff     1779 Jul  2 09:02 task-17-e2e-review.md
-rw-r--r--@   1 kujinlee  staff     2313 Jul  2 09:02 task-18-frontend-codex.md
-rw-r--r--@   1 kujinlee  staff     2859 Jul  2 09:02 task-18-frontend-review.md
-rw-r--r--@   1 kujinlee  staff     2428 Jul  9 04:27 task-1d-10-producer-buckets-review.md
-rw-r--r--@   1 kujinlee  staff     3698 Jul  9 04:27 task-1d-11-route-wiring-review.md
-rw-r--r--@   1 kujinlee  staff     2515 Jul  9 04:27 task-1d-12-cap-soundness-review.md
-rw-r--r--@   1 kujinlee  staff     2995 Jul  9 04:27 task-1d-13-live-gates-migration-review.md
-rw-r--r--@   1 kujinlee  staff     1705 Jul  9 04:27 task-1d-9-livebroadcastcontent-review.md
-rw-r--r--@   1 kujinlee  staff     2787 Jul 10 03:35 task-1f-a-1-reserve-rpc.md
-rw-r--r--@   1 kujinlee  staff     2132 Jul 10 03:35 task-1f-a-2-magazine-caps.md
-rw-r--r--@   1 kujinlee  staff     1889 Jul 10 03:35 task-1f-a-3-model-store.md
-rw-r--r--@   1 kujinlee  staff     2398 Jul 10 03:35 task-1f-a-4-blobstore-staging.md
-rw-r--r--@   1 kujinlee  staff     2954 Jul 10 03:35 task-1f-a-5-render-nonce.md
-rw-r--r--@   1 kujinlee  staff     3511 Jul 10 03:35 task-1f-a-6-materialize-helper.md
-rw-r--r--@   1 kujinlee  staff     4189 Jul 10 03:35 task-1f-a-7-serve-route.md
-rw-r--r--@   1 kujinlee  staff     3747 Jul 10 03:35 task-1f-a-8-config-invariant.md
-rw-r--r--@   1 kujinlee  staff     2263 Jul 10 08:25 task-1f-b-1-read-model-codex.md
-rw-r--r--@   1 kujinlee  staff     2511 Jul 10 08:25 task-1f-b-1-read-model-review.md
-rw-r--r--@   1 kujinlee  staff     3310 Jul 10 08:25 task-1f-b-2-migration-codex.md
-rw-r--r--@   1 kujinlee  staff     3016 Jul 10 08:25 task-1f-b-2-migration-review.md
-rw-r--r--@   1 kujinlee  staff     3080 Jul 10 08:25 task-1f-b-6-serve-lib-codex.md
-rw-r--r--@   1 kujinlee  staff     2405 Jul 10 08:25 task-1f-b-6-serve-lib-review.md
-rw-r--r--@   1 kujinlee  staff     3838 Jul 10 08:25 task-1f-b-7-serve-route-codex.md
-rw-r--r--@   1 kujinlee  staff     3384 Jul 10 08:25 task-1f-b-7-serve-route-review.md
-rw-r--r--@   1 kujinlee  staff     2035 Jul 10 14:48 task-1f-c-3-owner-route-codex.md
-rw-r--r--@   1 kujinlee  staff     2716 Jul 10 14:48 task-1f-c-3-owner-route-review.md
-rw-r--r--@   1 kujinlee  staff     2074 Jul 10 14:48 task-1f-c-4-share-route-codex.md
-rw-r--r--@   1 kujinlee  staff     3700 Jul 10 14:48 task-1f-c-4-share-route-review.md
-rw-r--r--@   1 kujinlee  staff     1774 Jul 10 18:29 task-1g-1-migration-codex.md
-rw-r--r--@   1 kujinlee  staff     2016 Jul 10 18:29 task-1g-1-migration-review.md
-rw-r--r--@   1 kujinlee  staff     2060 Jul 10 18:29 task-1g-2-serve-stale-codex.md
-rw-r--r--@   1 kujinlee  staff     2427 Jul 10 18:29 task-1g-2-serve-stale-review.md
-rw-r--r--@   1 kujinlee  staff     1719 Jul 10 18:29 task-1g-3-route-codex.md
-rw-r--r--@   1 kujinlee  staff     3969 Jul 10 18:29 task-1g-3-route-review.md
-rw-r--r--@   1 kujinlee  staff     1813 Jul  2 18:20 task-2-core-schema-review.md
-rw-r--r--@   1 kujinlee  staff     5483 Jul  8 04:30 task-2-persist-rpcs-codex.md
-rw-r--r--@   1 kujinlee  staff     3285 Jul  8 04:30 task-2-persist-rpcs-review.md
-rw-r--r--@   1 kujinlee  staff     1711 Jul 11 07:33 task-2a-1-updatedat-codex.md
-rw-r--r--@   1 kujinlee  staff     2285 Jul 11 07:33 task-2a-1-updatedat-review.md
-rw-r--r--@   1 kujinlee  staff     2006 Jul 11 07:33 task-2a-10-scope-client-review.md
-rw-r--r--@   1 kujinlee  staff     1333 Jul 11 07:33 task-2a-11-login-page-review.md
-rw-r--r--@   1 kujinlee  staff     1778 Jul 11 07:33 task-2a-12-page-dispatch-review.md
-rw-r--r--@   1 kujinlee  staff     1630 Jul 11 07:33 task-2a-13-sidebar-review.md
-rw-r--r--@   1 kujinlee  staff     1343 Jul 11 07:33 task-2a-14-account-menu-review.md
-rw-r--r--@   1 kujinlee  staff     2508 Jul 11 07:33 task-2a-15a-retarget-leaves-review.md
-rw-r--r--@   1 kujinlee  staff     2717 Jul 11 07:33 task-2a-15b-cloudapp-wiring-review.md
-rw-r--r--@   1 kujinlee  staff     2099 Jul 11 07:33 task-2a-2-local-updatedat-review.md
-rw-r--r--@   1 kujinlee  staff     2066 Jul 11 07:33 task-2a-3-listplaylists-review.md
-rw-r--r--@   1 kujinlee  staff     1621 Jul 11 07:33 task-2a-4-playlists-route-review.md
-rw-r--r--@   1 kujinlee  staff     1982 Jul 11 07:33 task-2a-5-videos-cloud-review.md
-rw-r--r--@   1 kujinlee  staff     1635 Jul 11 07:33 task-2a-6-quickview-cloud-review.md
-rw-r--r--@   1 kujinlee  staff     3749 Jul 11 07:33 task-2a-7-annotation-rpc-review.md
-rw-r--r--@   1 kujinlee  staff     1991 Jul 11 07:33 task-2a-8-archive-cloud-review.md
-rw-r--r--@   1 kujinlee  staff     2461 Jul 11 07:33 task-2a-9-middleware-review.md
-rw-r--r--@   1 kujinlee  staff     2182 Jul 11 15:29 task-2b-1-pollclient-codex.md
-rw-r--r--@   1 kujinlee  staff     1728 Jul 11 15:29 task-2b-1-pollclient-review.md
-rw-r--r--@   1 kujinlee  staff     2368 Jul 11 15:29 task-2b-1-pollclient-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     2246 Jul 11 15:29 task-2b-10-integration-review.md
-rw-r--r--@   1 kujinlee  staff     1489 Jul 11 15:29 task-2b-2-createingest-codex.md
-rw-r--r--@   1 kujinlee  staff     1790 Jul 11 15:29 task-2b-2-createingest-review.md
-rw-r--r--@   1 kujinlee  staff     1512 Jul 11 15:29 task-2b-2-createingest-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     1152 Jul 11 15:29 task-2b-3-getjobstatus-review.md
-rw-r--r--@   1 kujinlee  staff     1056 Jul 11 15:29 task-2b-5-summarynotice-review.md
-rw-r--r--@   1 kujinlee  staff     1486 Jul 11 15:29 task-2b-6-modal-codex.md
-rw-r--r--@   1 kujinlee  staff     2219 Jul 11 15:29 task-2b-6-modal-review.md
-rw-r--r--@   1 kujinlee  staff     1155 Jul 11 15:29 task-2b-6-modal-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     1519 Jul 11 15:29 task-2b-7-banner-codex.md
-rw-r--r--@   1 kujinlee  staff     1826 Jul 11 15:29 task-2b-7-banner-review.md
-rw-r--r--@   1 kujinlee  staff     1254 Jul 11 15:29 task-2b-7-banner-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     1322 Jul 11 15:29 task-2b-8-sidebar-review.md
-rw-r--r--@   1 kujinlee  staff     1883 Jul 11 15:29 task-2b-9-cloudapp-codex.md
-rw-r--r--@   1 kujinlee  staff     1986 Jul 11 15:29 task-2b-9-cloudapp-review.md
-rw-r--r--@   1 kujinlee  staff     1854 Jul 11 15:29 task-2b-9-cloudapp-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     1124 Jul 11 17:37 task-2c-1-share-id-codex.md
-rw-r--r--@   1 kujinlee  staff     2554 Jul 11 17:37 task-2c-1-share-id-review.md
-rw-r--r--@   1 kujinlee  staff      938 Jul 11 17:37 task-2c-2-summaryready-codex.md
-rw-r--r--@   1 kujinlee  staff     2188 Jul 11 17:37 task-2c-2-summaryready-review.md
-rw-r--r--@   1 kujinlee  staff      821 Jul 11 17:37 task-2c-3-summaryhref-review.md
-rw-r--r--@   1 kujinlee  staff      799 Jul 11 17:37 task-2c-4-share-seam-review.md
-rw-r--r--@   1 kujinlee  staff     3926 Jul 11 17:37 task-2c-5-sharedialog-codex.md
-rw-r--r--@   1 kujinlee  staff     2998 Jul 11 17:37 task-2c-5-sharedialog-review.md
-rw-r--r--@   1 kujinlee  staff     2465 Jul 11 17:37 task-2c-6-videomenu-codex.md
-rw-r--r--@   1 kujinlee  staff     1346 Jul 11 17:37 task-2c-6-videomenu-review.md
-rw-r--r--@   1 kujinlee  staff     1009 Jul 11 17:37 task-2c-7-videorow-codex.md
-rw-r--r--@   1 kujinlee  staff     1883 Jul 11 17:37 task-2c-7-videorow-review.md
-rw-r--r--@   1 kujinlee  staff      365 Jul 11 17:37 task-2c-8-integration-codex.md
-rw-r--r--@   1 kujinlee  staff     1414 Jul 11 17:37 task-2c-8-integration-review.md
-rw-r--r--@   1 kujinlee  staff     2893 Jul  2 09:02 task-3-index-store-codex.md
-rw-r--r--@   1 kujinlee  staff     2795 Jul  2 09:02 task-3-index-store-review.md
-rw-r--r--@   1 kujinlee  staff     1679 Jul  2 18:20 task-3-rls-policies-review.md
-rw-r--r--@   1 kujinlee  staff     2921 Jul  2 09:02 task-4-ensure-deepdive-review.md
-rw-r--r--@   1 kujinlee  staff     2225 Jul  2 18:20 task-4-provisioning-trigger-review.md
-rw-r--r--@   1 kujinlee  staff     3187 Jul  8 04:30 task-4-signal-threading-review.md
-rw-r--r--@   1 kujinlee  staff     1505 Jul  2 09:02 task-4-youtube-client-codex.md
-rw-r--r--@   1 kujinlee  staff     1699 Jul  2 09:02 task-4-youtube-client-review.md
-rw-r--r--@   1 kujinlee  staff     2158 Jul  2 18:20 task-5-client-factories-review.md
-rw-r--r--@   1 kujinlee  staff     4076 Jul  2 09:02 task-5-gemini-client-codex.md
-rw-r--r--@   1 kujinlee  staff     2790 Jul  2 09:02 task-5-gemini-client-review.md
-rw-r--r--@   1 kujinlee  staff     1009 Jul 10 03:35 task-5-render-nonce-codex.md
-rw-r--r--@   1 kujinlee  staff     4705 Jul 10 03:35 task-5-render-nonce-review.md
-rw-r--r--@   1 kujinlee  staff     3127 Jul  8 04:30 task-5-summarycore-review.md
-rw-r--r--@   1 kujinlee  staff     1916 Jul  2 18:20 task-6-confinement-scan-review.md
-rw-r--r--@   1 kujinlee  staff     3035 Jul  2 09:02 task-6-pdf-generator-codex.md
-rw-r--r--@   1 kujinlee  staff     1348 Jul  2 09:02 task-6-pdf-generator-review.md
-rw-r--r--@   1 kujinlee  staff     4204 Jul  8 04:30 task-6-runonce-review.md
-rw-r--r--@   1 kujinlee  staff     2227 Jul  2 09:02 task-7-archive-manager-codex.md
-rw-r--r--@   1 kujinlee  staff     1571 Jul  2 09:02 task-7-archive-manager-review.md
-rw-r--r--@   1 kujinlee  staff     1866 Jul  2 18:20 task-7-integration-harness-review.md
-rw-r--r--@   1 kujinlee  staff     4033 Jul  8 04:30 task-7-summary-handler-review.md
-rw-r--r--@   1 kujinlee  staff     2663 Jul  2 09:02 task-8-ingestion-pipeline-codex.md
-rw-r--r--@   1 kujinlee  staff     1792 Jul  2 09:02 task-8-ingestion-pipeline-review.md
-rw-r--r--@   1 kujinlee  staff     2012 Jul  2 18:20 task-8-rls-isolation-review.md
-rw-r--r--@   1 kujinlee  staff     3340 Jul  8 04:30 task-8-worker-main-review.md
-rw-r--r--@   1 kujinlee  staff     2355 Jul  2 09:02 task-9-deep-dive-codex.md
-rw-r--r--@   1 kujinlee  staff     2793 Jul  2 09:02 task-9-deep-dive-review.md
-rw-r--r--@   1 kujinlee  staff     2305 Jul  2 18:20 task-9-integrity-reorder-review.md
-rw-r--r--@   1 kujinlee  staff     3642 Jul  2 09:02 task-9-status-bar-view-link-review.md
-rw-r--r--@   1 kujinlee  staff     2366 Jul  2 09:02 task-ask-ai-sized-popup-codex.md
-rw-r--r--@   1 kujinlee  staff     2491 Jul  2 09:02 task-ask-gemini-review.md
-rw-r--r--@   1 kujinlee  staff     2762 Jul  2 09:02 task-autosuggest-removal-codex.md
-rw-r--r--@   1 kujinlee  staff     2405 Jul  2 09:02 task-autosuggest-removal-review.md
-rw-r--r--@   1 kujinlee  staff     1908 Jul 12 17:26 task-cloud-dig-1-review.md
-rw-r--r--@   1 kujinlee  staff     3382 Jul 12 17:26 task-cloud-dig-2-review.md
-rw-r--r--@   1 kujinlee  staff     5539 Jul 12 17:26 task-cloud-dig-3-review.md
-rw-r--r--@   1 kujinlee  staff     2500 Jul 12 17:26 task-cloud-dig-4-review.md
-rw-r--r--@   1 kujinlee  staff     4852 Jul 12 17:26 task-cloud-dig-5-review.md
-rw-r--r--@   1 kujinlee  staff     4037 Jul 12 17:26 task-cloud-dig-6-review.md
-rw-r--r--@   1 kujinlee  staff     3596 Jul 12 17:26 task-cloud-dig-7-review.md
-rw-r--r--@   1 kujinlee  staff     6968 Jul 12 17:26 task-cloud-dig-flash-review.md
-rw-r--r--@   1 kujinlee  staff     4409 Jul 12 05:08 task-cloud-pdf-1-codex.md
-rw-r--r--@   1 kujinlee  staff     4023 Jul 12 05:08 task-cloud-pdf-1-review.md
-rw-r--r--@   1 kujinlee  staff     1608 Jul 12 05:08 task-cloud-pdf-10-review.md
-rw-r--r--@   1 kujinlee  staff     3648 Jul 12 05:08 task-cloud-pdf-11-review.md
-rw-r--r--@   1 kujinlee  staff     2623 Jul 12 05:08 task-cloud-pdf-2-review.md
-rw-r--r--@   1 kujinlee  staff     2048 Jul 12 05:08 task-cloud-pdf-3-review.md
-rw-r--r--@   1 kujinlee  staff     1906 Jul 12 05:08 task-cloud-pdf-4-review.md
-rw-r--r--@   1 kujinlee  staff     3208 Jul 12 05:08 task-cloud-pdf-5-review.md
-rw-r--r--@   1 kujinlee  staff     2682 Jul 12 05:08 task-cloud-pdf-6-review.md
-rw-r--r--@   1 kujinlee  staff     1940 Jul 12 05:08 task-cloud-pdf-7-review.md
-rw-r--r--@   1 kujinlee  staff     3561 Jul 12 05:08 task-cloud-pdf-8-review.md
-rw-r--r--@   1 kujinlee  staff     1342 Jul 12 05:08 task-cloud-pdf-9-review.md
-rw-r--r--@   1 kujinlee  staff     3422 Jul  2 09:02 task-deep-dive-first-gen-and-busy-state-codex.md
-rw-r--r--@   1 kujinlee  staff     3678 Jul  2 09:02 task-deep-dive-first-gen-and-busy-state-review.md
-rw-r--r--@   1 kujinlee  staff     1200 Jul  2 09:02 task-dig-captions-t1-codex.md
-rw-r--r--@   1 kujinlee  staff     2234 Jul  2 09:02 task-dig-captions-t1-review.md
-rw-r--r--@   1 kujinlee  staff     1401 Jul  2 09:02 task-dig-captions-t2-codex.md
-rw-r--r--@   1 kujinlee  staff     1757 Jul  2 09:02 task-dig-captions-t2-review.md
-rw-r--r--@   1 kujinlee  staff      968 Jul  2 09:02 task-dig-captions-t3-codex.md
-rw-r--r--@   1 kujinlee  staff     1647 Jul  2 09:02 task-dig-captions-t3-review.md
-rw-r--r--@   1 kujinlee  staff     2678 Jul  2 09:02 task-dig-image-sizing-codex.md
-rw-r--r--@   1 kujinlee  staff     2343 Jul  2 09:02 task-dig-image-sizing-review.md
-rw-r--r--@   1 kujinlee  staff     2579 Jul  2 09:02 task-dig-section-ask-ai-codex.md
-rw-r--r--@   1 kujinlee  staff     1676 Jul  2 09:02 task-dig-section-ask-ai-review.md
-rw-r--r--@   1 kujinlee  staff     2126 Jul  2 09:02 task-dig-slide-size-control-t1-codex.md
-rw-r--r--@   1 kujinlee  staff     2241 Jul  2 09:02 task-dig-slide-size-control-t1-review.md
-rw-r--r--@   1 kujinlee  staff     2997 Jul  2 09:02 task-dig-slide-size-control-t2-codex.md
-rw-r--r--@   1 kujinlee  staff     2044 Jul  2 09:02 task-dig-slide-size-control-t2-review.md
-rw-r--r--@   1 kujinlee  staff     1633 Jul  2 09:02 task-dig-subheading-gold-style-codex.md
-rw-r--r--@   1 kujinlee  staff     2586 Jul  2 09:02 task-dig-subheading-gold-style-review.md
-rw-r--r--@   1 kujinlee  staff     1214 Jul  2 09:02 task-dig-subheadings-t1-codex.md
-rw-r--r--@   1 kujinlee  staff     1587 Jul  2 09:02 task-dig-subheadings-t1-review.md
-rw-r--r--@   1 kujinlee  staff      911 Jul  2 09:02 task-dig-subheadings-t2-codex.md
-rw-r--r--@   1 kujinlee  staff     1652 Jul  2 09:02 task-dig-subheadings-t2-review.md
-rw-r--r--@   1 kujinlee  staff     2554 Jul  2 09:02 task-features-ui-parity-codex.md
-rw-r--r--@   1 kujinlee  staff     2263 Jul  2 09:02 task-features-ui-parity-review.md
-rw-r--r--@   1 kujinlee  staff     1878 Jul  2 09:02 task-obsidian-vault-fix-codex.md
-rw-r--r--@   1 kujinlee  staff     2516 Jul  2 09:02 task-obsidian-vault-fix-review.md
-rw-r--r--@   1 kujinlee  staff     2557 Jul  2 09:02 task-orphaned-route-removal-codex.md
-rw-r--r--@   1 kujinlee  staff     1683 Jul  2 09:02 task-resolve-folder-backend-codex.md
-rw-r--r--@   1 kujinlee  staff     2170 Jul  2 09:02 task-resolve-folder-backend-review.md
-rw-r--r--@   1 kujinlee  staff     2380 Jul  2 09:02 task-serial-invariant-codex.md
-rw-r--r--@   1 kujinlee  staff     2003 Jul  2 09:02 task-serial-invariant-review.md
-rw-r--r--@   1 kujinlee  staff     4071 Jul 14 12:59 videos-list-observability-review.md
-rw-r--r--@   1 kujinlee  staff     4660 Jul 10 03:35 whole-branch-1f-a.md
-rw-r--r--@   1 kujinlee  staff     2332 Jul 10 08:25 whole-branch-1f-b-codex.md
-rw-r--r--@   1 kujinlee  staff     4353 Jul 10 08:25 whole-branch-1f-b.md
-rw-r--r--@   1 kujinlee  staff     4235 Jul 10 18:29 whole-branch-1g-review.md
-rw-r--r--@   1 kujinlee  staff     6652 Jul 11 07:33 whole-branch-2a-review.md
-rw-r--r--@   1 kujinlee  staff     3981 Jul 11 15:29 whole-branch-2b-review.md
-rw-r--r--@   1 kujinlee  staff      498 Jul 11 17:37 whole-branch-2c-codex.md
-rw-r--r--@   1 kujinlee  staff     3841 Jul 11 17:37 whole-branch-2c-review.md
-rw-r--r--@   1 kujinlee  staff     4826 Jul 15 06:48 whole-branch-cloud-dig-deeper-frontend-v1-review.md
-rw-r--r--@   1 kujinlee  staff     4034 Jul 15 06:48 whole-branch-cloud-dig-deeper-frontend-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     5272 Jul 14 17:56 whole-branch-cloud-dig-serving-review.md
-rw-r--r--@   1 kujinlee  staff     3979 Jul 12 05:08 whole-branch-cloud-pdf-review.md
-rw-r--r--@   1 kujinlee  staff   543517 Jul 17 22:50 whole-branch-cloud-sync-codex.md
-rw-r--r--@   1 kujinlee  staff    16974 Jul 18 08:37 whole-branch-cloud-sync-v2-rereview-claude.md
-rw-r--r--@   1 kujinlee  staff   238959 Jul 18 08:33 whole-branch-cloud-sync-v2-rereview-codex.md
-rw-r--r--@   1 kujinlee  staff    13883 Jul 18 08:56 whole-branch-cloud-sync-v3-rereview-claude.md
-rw-r--r--@   1 kujinlee  staff   345244 Jul 18 08:53 whole-branch-cloud-sync-v3-rereview-codex.md
-rw-r--r--@   1 kujinlee  staff    92482 Jul 18 09:05 whole-branch-cloud-sync-v4-rereview-codex.md
-rw-r--r--@   1 kujinlee  staff     6968 Jul 12 17:26 whole-branch-review.md
-rw-r--r--@   1 kujinlee  staff     5912 Jul  2 18:20 whole-branch-stage-1b-review.md
-rw-r--r--@   1 kujinlee  staff     3748 Jul  6 15:41 whole-branch-stage-1c-review.md
-rw-r--r--@   1 kujinlee  staff     3709 Jul  7 14:41 whole-branch-stage-1e-a-review.md
-rw-r--r--@   1 kujinlee  staff     2977 Jul  8 04:30 whole-branch-stage-1e-b-codex.md
-rw-r--r--@   1 kujinlee  staff     3729 Jul  8 04:30 whole-branch-stage-1e-b-review.md
-rw-r--r--@   1 kujinlee  staff     3861 Jul  8 04:30 whole-branch-stage-1e-b-v2-rereview.md
-rw-r--r--@   1 kujinlee  staff     3383 Jul  8 04:30 whole-branch-stage-1e-b-v3-rereview.md
-rw-r--r--@   1 kujinlee  staff     3511 Jul  8 04:30 whole-branch-stage-1e-b-v4-rereview.md
-rw-r--r--@   1 kujinlee  staff     3694 Jul 15 12:20 whole-branch-summary-section-timestamp-guarantee-review.md
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:12:Claude-R2-M1 (stale non-`summaryMd` artifact pointers), Codex-R2-Medium (absent companion scalars),
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:19:### H-R2-1 — validate the MD body BEFORE claiming the receiver slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:28:  run 2: `e2e.int.test.ts:452` asserts `await localVideoRecord(ctx)` is `null`. With the guard after
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:32:- **Later throws on the additive path still leave partial state**, but none reproduce the H-R2-1
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:34:  fire only when `mdBody != null`, i.e. the source body is READABLE — so on the next run the source
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:35:  side derives a non-null `mdHash`, `reconcileClassA:22` returns `copyToLocal`/`copyToCloud` and the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:42:- **Is the residual `mdBody != null` at `:167` dead?** Logically yes (given `:160`, `video.summaryMd`
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:43:  truthy ⇒ `mdBody != null`). It hides nothing: it is a narrowing guard whose only fallthrough is the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:47:### H-R2-2 — `digDeeperMd` preserved on `transferClassA`
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:66:destroying it. `digDeeperHtml: null` (`sync-run.ts:332`) is sufficient to force the re-merge —
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:69:`sanitizeAdditiveVideo` nulling `digDeeperMd` (`:111`) remains correct: on the additive path the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:76:### M-R2-2 — corrections guard narrowed to `la.mdHash != null && ca.mdHash != null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:77:**Verdict: NOT FIXED SAFELY — the narrowing predicate is wrong and reopens WB-B1. See B1.**
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:87:The defect is not the hoist — it is that `la.mdHash != null` was used as the test for "this side
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:88:holds an MD". It does not mean that. See B1.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:94:### B1 (BLOCKING) — `mdHash == null` conflates "has no MD" with "MD is unreadable", so an unreadable blob silently destroys the other replica's body and launders it into an agreed baseline
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:98:`readMdBody` returns `null` for *two* different situations: the record advertises no `summaryMd`, or
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:100:`get` is `if (error) return null`, which swallows **every** failure (network, 5xx, timeout, RLS
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:101:denial), not just 404. The additive path knows this and guards it explicitly (H-R2-1, `:160`). The
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:106:deleted; seeds a cloud row advertising `summaryMd` + a `promoted` artifact with no readable body):
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:108:**P1 — the WB-B1 destruction, back.** Local holds a corrected body with `corrections: 'A'`; cloud has
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:109:`corrections: 'B'`; both backfilled ⇒ unresolved conflict. Cloud body unreadable.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:115:`ca.mdHash == null` ⇒ the guard at `:501` does not fire ⇒ `reconcileClassA:23` (`!cHas`) ⇒
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:118:WB-B1 was filed to prevent — and it is silent (`errors: []`).
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:121:no corrections anywhere. Cloud body unreadable for one run:
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:133:**Why this is Blocking, not High:** silent, unrecoverable destruction of user content triggered by an
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:135:replicas agree. It also forces a full re-generation to recover — a money finding of the H-R2-2 class.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:141:if (lv.summaryMd && la.mdHash == null) throw new Error(`local MD body unreadable for ${id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:142:if (cv.summaryMd && ca.mdHash == null) throw new Error(`cloud MD body unreadable for ${id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:147:"purely additive hydration" is exactly "the loser advertises no `summaryMd`". Regression tests: the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:153:`transferClassA` writes the **winner's** `summaryMd` key onto the loser (`:304`). The two replicas'
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:160:After a `copyToLocal` transfer the local row holds `summaryMd: '007_slug.md'` (new body, written) but
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:162:`digDeeperMd` **in preference to** `summaryMd`, then reads `relDir/003_slug.md` (`:104,112`) — the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:166:`rerender.ts:42` and `ensure.ts:35` both derive `base` from `summaryMd`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:170:pre-`32a164c`; the H-R2-2 fix restored it rather than introducing it. Cleanest fix lives outside
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:171:sync: prefer `summaryMd` for `base` derivation in `build-doc-html`, using `digDeeperMd` only for the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:189:  paths: the H-R2-2 class is fixed; B1 is a new one and is counted as such above.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:194:  new one-sided-hydration branches. The only laundering path found is B1.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:197:  the now-two-field null set; both store JSON null, both read falsy. The `get`-swallows-errors
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:198:  asymmetry between the two backends is B1.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:204:**NOT CONVERGED** — 1 new Blocking (B1: unreadable-blob conflation destroys the other replica's MD
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:206:narrowing) plus 1 Medium. Part A: H-R2-1 genuinely fixed, H-R2-2 genuinely fixed, M-R2-2 fixed the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:207:stranding but with an unsafe predicate. Another round is required after B1.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:17:- R1 `docs/reviews/whole-branch-cloud-sync-codex.md` → 1 Blocking + 2 High → fixed `32a164c`
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:18:- R2 `...-v2-rereview-{codex,claude}.md` → H-R2-1 (WB-H1 incomplete), H-R2-2 (regression from the WB-H2 fix), M-R2-2 → fixed `1f54c60`
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:19:- R3 `...-v3-rereview-{codex,claude}.md` → Codex returned CONVERGED (0 findings) but the Claude pass found **B1, Blocking** (reproduced in two forms) → fixed `3bc8cc7`
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:23:**Calibration from R3, and it cuts both ways.** One reviewer declared convergence while a Blocking was live — so do not treat a quiet branch as a clean one, and interrogate what values MEAN (is `null` "absent" or "failed to load"?), not merely whether they are handled. Equally: three rounds of real fixes have landed, and if this round genuinely finds nothing, say so plainly. A clean round is the expected terminal state of this loop; manufacturing a marginal finding to appear diligent is itself a failure.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:26:**B1** — `lib/cloud-sync/sync-run.ts:510-511` now throws per-video when a record advertises `summaryMd` but its body did not load, on either side, before the corrections guard and before `reconcileClassA`.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:29:1. Does the guard cover EVERY consumer of a possibly-unreadable body, or only the two-sided reconcile path? Audit every other `readMdBody` / `blob.get` call in `lib/cloud-sync/*` — companion (`companion.ts`, `decideCompanion` / `sourceMdHash` comparison), `transferClassA`'s own reads, the manifest/backfill paths, `registry.ts`. Can a null-because-unreadable still be read as a semantic fact anywhere else (e.g. "the model was not generated from this MD" → deleting a companion model, or a Class-B/backfill decision)?
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:30:2. Is throwing the right response versus skipping? A record that PERMANENTLY advertises a `summaryMd` whose blob is genuinely gone (real storage drift, not transient) now errors on EVERY run forever and never advances a baseline. Trace what that does to delete-inference, to `report.errors` growth, and to a user's ability to ever complete a sync run. Is there a case where this new throw makes a previously-working sync fail?
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:31:3. Does the guard change behavior for the legitimate summary-less video (`summaryMd == null`) and the one-sided-hydration case (M-R2-2)? Both must still work. Confirm against the tests at `tests/integration/cloud-sync/e2e.int.test.ts`.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:32:4. Are the two new B1 regression tests honest — do they fail for the RIGHT reason when the guard is removed, and do they assert across two runs?
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:34:## Part B — hunt for NEW defects, and for SIBLINGS of the B1 root cause
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:35:The B1 root cause is a **semantic conflation across a module boundary**: a value that means "absent" in one module is produced by a failure in another. Hunt for siblings of that shape anywhere on the sync path — not just for blobs. Candidates worth tracing: a swallowed error that yields a default/empty value which a caller then treats as fact (empty index vs failed read; absent manifest vs unreadable manifest; a missing record vs a failed query; `readIndex` on a store error; `''` vs absent playlist metadata).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:48:KNOWN / DEFERRED — do NOT re-report unless you prove they mask a real bug: T14-M1, T14-M2, T5 coverage gaps, T4 automock comment; Claude-R2-M1 (stale non-`summaryMd` artifact pointers); Codex-R2-Medium (absent companion scalars); Claude-R3-M1 (`build-doc-html` deriving `base` from `digDeeperMd`). Do NOT report `tests/integration/reservation-release.test.ts` — pre-existing on a clean tree, tracked separately.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:51:Per finding: severity (Blocking/High/Medium/Low), `file:line`, concrete failure scenario (inputs → wrong outcome), fix. Part A: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:58:3bc8cc7 (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:71:    fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:73:    Round-3 dual re-review of 1f54c60. Codex returned CONVERGED (0 findings); the Claude
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:74:    pass found a Blocking, reproduced in two forms. Adjudicated against the code — the
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:75:    Blocking is real.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:77:    B1 — readMdBody returns null for TWO different situations: the record advertises no
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:78:    summaryMd, or it advertises one whose bytes could not be READ. The backends disagree on
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:79:    which is which: the local blob store returns null only on ENOENT and throws otherwise,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:80:    but SupabaseBlobStore.get is `if (error) return null` — it swallows EVERY failure
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:81:    (network, 5xx, timeout, RLS denial). deriveClassASignals maps a null body to
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:82:    mdHash: null, and reconcileClassA reads mdHash == null as "this side HAS NO MD"
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:88:      an unreadable cloud body meant the guard did not fire; the local body was copied over
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:89:      cloud's and a full-agreement baseline recorded — the exact destruction WB-B1 was filed
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:96:    Fix: the two-sided counterpart of copyAdditiveVideo's existing WB-H1/H-R2-1 guard. If a
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:97:    record advertises summaryMd but its body did not load, throw per-video — caught by the
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:102:    Also corrects the misleading `// 404 → null` comment on SupabaseBlobStore.get. Comment
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:130:    fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:132:    Round-3 dual re-review of 1f54c60. Codex returned CONVERGED (0 findings); the Claude
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:133:    pass found a Blocking, reproduced in two forms. Adjudicated against the code — the
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:134:    Blocking is real.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:136:    B1 — readMdBody returns null for TWO different situations: the record advertises no
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:137:    summaryMd, or it advertises one whose bytes could not be READ. The backends disagree on
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:138:    which is which: the local blob store returns null only on ENOENT and throws otherwise,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:139:    but SupabaseBlobStore.get is `if (error) return null` — it swallows EVERY failure
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:140:    (network, 5xx, timeout, RLS denial). deriveClassASignals maps a null body to
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:141:    mdHash: null, and reconcileClassA reads mdHash == null as "this side HAS NO MD"
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:147:      an unreadable cloud body meant the guard did not fire; the local body was copied over
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:148:      cloud's and a full-agreement baseline recorded — the exact destruction WB-B1 was filed
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:155:    Fix: the two-sided counterpart of copyAdditiveVideo's existing WB-H1/H-R2-1 guard. If a
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:156:    record advertises summaryMd but its body did not load, throw per-video — caught by the
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:161:    Also corrects the misleading `// 404 → null` comment on SupabaseBlobStore.get. Comment
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:213:         //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:216:           const presentIsLocal = lv != null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:226:               deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:244:         // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:259:+        // ── B1 (round 3) — the two-sided counterpart of copyAdditiveVideo's WB-H1/H-R2-1 guard (:160).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:260:+        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:263:+        //    return null` — it swallows EVERY failure (network, 5xx, timeout, RLS denial), so on the
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:265:+        //    deriveClassASignals maps a null body to mdHash: null, and reconcileClassA reads
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:266:+        //    mdHash == null as "this side HAS NO MD" (:21-23) — and those presence branches return
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:268:+        //    unreadable body made the other replica's body get copied over it (destroying it) and
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:273:+        //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:275:+        if (lv.summaryMd && la.mdHash == null) throw new Error(`local MD body unreadable for ${id}`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:276:+        if (cv.summaryMd && ca.mdHash == null) throw new Error(`cloud MD body unreadable for ${id}`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:285:         if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:292:         // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:296:         let winnerMdHash: string | null = null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:298:         let winnerSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:299:         let loserSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:359:   async get(p: Principal, key: string): Promise<Buffer | null> {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:361:-    if (error) return null;   // 404 → null
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:362:+    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:363:+    // so a null here does NOT prove the object is absent. Callers that treat "no bytes" as a
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:365:+    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:366:+    // left as-is: shared with already-merged read paths where absent-vs-unreadable is immaterial.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:367:+    // Note the LOCAL blob store differs — it returns null only on ENOENT and throws otherwise.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:368:+    if (error) return null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:373:     return (await this.get(p, key)) !== null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:429:    *  `id === null` and are descended into; file entries (`id !== null`) are collected. */
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:440:         if (entry.id === null) {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:466:     expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:470:   // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:475:   //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:476:   it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:496:     expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:497:     expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:498:     expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:501:   // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:509:       summaryMd: null, // local row exists but holds NO MD → nothing to destroy
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:529:     expect(local?.summaryMd).toBe(key(ctx));
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:530:     expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:535:+  // ── B1 (round 3) — `mdHash == null` conflates "this side advertises NO MD" with "this side's MD
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:536:+  //    body could not be READ". The Supabase blob store returns null on EVERY error (network, 5xx,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:539:+  //    fire BEFORE the corrections-currency and never-downgrade-format ladder, so the unreadable side
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:545:+  it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:552:+    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:555:+      /* mdBody omitted → blob unreadable */
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:573:+      // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:579:+  it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:590:+      /* mdBody omitted → blob unreadable */
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:613:/bin/bash -lc "rg -n \"readMdBody|blob\\.get|get\\(|summaryMd|sourceMdHash|needsRegen|spend_ledger|manifest|baseline|advance|readIndex|delete\" lib/cloud-sync lib/storage/local lib/storage/supabase lib/html-doc lib/dig tests/lib/cloud-sync tests/integration/cloud-sync docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:615:lib/storage/local/local-blob-store.ts:18:  async get(p: Principal, key: string): Promise<Buffer | null> {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:625:tests/lib/cloud-sync/model-writer-hash.test.ts:5:// fed to generation — NOT a hash of the sourceMd/summaryMd blob KEY (the filename). Guards
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:627:tests/lib/cloud-sync/model-writer-hash.test.ts:24:// The MD body fed to generation (the whole file `runHtmlDoc` reads as `video.summaryMd`'s blob).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:628:tests/lib/cloud-sync/model-writer-hash.test.ts:56:    overallScore: 4, summaryMd: 'a-title.md',
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:633:tests/integration/cloud-sync/sync-run.int.test.ts:41:    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:634:tests/integration/cloud-sync/sync-run.int.test.ts:42:    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:637:tests/integration/cloud-sync/stamping.int.test.ts:94:      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:638:tests/lib/cloud-sync/local-stamping.test.ts:23:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:646:lib/dig/dig-section.ts:31:  const summaryMdName = video.summaryMd ?? `${videoId}.md`;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:647:lib/dig/dig-section.ts:32:  const summaryMdPath = path.join(outputFolder, summaryMdName);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:648:lib/dig/dig-section.ts:33:  const mdContent = await fs.readFile(summaryMdPath, 'utf8');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:649:lib/dig/dig-section.ts:83:  const summaryBasename = path.basename(summaryMdName, '.md');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:682:docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:703:tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:706:tests/integration/cloud-sync/e2e.int.test.ts:91:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:720:tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:721:tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:722:tests/integration/cloud-sync/e2e.int.test.ts:328:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:728:tests/integration/cloud-sync/e2e.int.test.ts:361:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:736:tests/integration/cloud-sync/e2e.int.test.ts:434:  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:737:tests/integration/cloud-sync/e2e.int.test.ts:435:  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:741:tests/integration/cloud-sync/e2e.int.test.ts:443:  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:742:tests/integration/cloud-sync/e2e.int.test.ts:445:    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:743:tests/integration/cloud-sync/e2e.int.test.ts:453:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:746:tests/integration/cloud-sync/e2e.int.test.ts:462:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:748:tests/integration/cloud-sync/e2e.int.test.ts:528:      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:750:tests/integration/cloud-sync/e2e.int.test.ts:548:    expect(local?.summaryMd).toBe(key(ctx));
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:751:tests/integration/cloud-sync/e2e.int.test.ts:549:    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:754:tests/integration/cloud-sync/e2e.int.test.ts:564:  it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:755:tests/integration/cloud-sync/e2e.int.test.ts:571:    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:756:tests/integration/cloud-sync/e2e.int.test.ts:592:      // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:757:tests/integration/cloud-sync/e2e.int.test.ts:598:  it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:760:tests/lib/cloud-sync/reconcile-class-a.test.ts:5:  summaryMdKey: 'x.md', mdHash: 'h', docVersionMajor: 3, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:765:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:773:tests/lib/cloud-sync/reconcile-class-a.test.ts:52:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:775:tests/lib/cloud-sync/reconcile-class-a.test.ts:54:    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:778:tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:780:tests/lib/cloud-sync/reconcile-class-a.test.ts:62:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:782:lib/storage/supabase/consistency.ts:5:export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:783:lib/storage/supabase/consistency.ts:7:const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:784:lib/storage/supabase/consistency.ts:46: * Source kinds (summaryMd, slide, modelJson) require manual repair — they cannot
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:803:lib/cloud-sync/manifest.ts:36:  await atomicWrite(manifestPath(dataRoot, playlistKey), JSON.stringify(m, null, 2));
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:812:tests/lib/cloud-sync/regenerate-stamp.test.ts:57:  summaryMd: SUMMARY_MD,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:814:tests/lib/cloud-sync/backfill.test.ts:8:  overallScore: 3, summaryMd: '001_title.md', processedAt: '2026-01-01T00:00:00.000Z', // KEY, not body
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:815:tests/lib/cloud-sync/backfill.test.ts:14:it('hashes the MD BODY, not the summaryMd key (Blocking ①)', () => {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:816:tests/lib/cloud-sync/backfill.test.ts:18:  expect(s.summaryMdKey).toBe('001_title.md');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:817:tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:818:tests/lib/cloud-sync/backfill.test.ts:31:  expect(s.summaryMdKey).toBeNull();
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:827:tests/lib/cloud-sync/schema.test.ts:8:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:830:lib/storage/supabase/supabase-blob-store.ts:23:  async get(p: Principal, key: string): Promise<Buffer | null> {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:831:lib/storage/supabase/supabase-blob-store.ts:36:    return (await this.get(p, key)) !== null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:836:lib/html-doc/generate.ts:25:  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:837:lib/html-doc/generate.ts:30:  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:838:lib/html-doc/generate.ts:32:    throw new Error(`source note not found on disk: ${video.summaryMd}`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:839:lib/html-doc/generate.ts:37:  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:840:lib/html-doc/generate.ts:49:  const base = video.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:841:lib/html-doc/generate.ts:51:    sourceMd: video.summaryMd,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:842:lib/html-doc/generate.ts:56:    // Stage 3 (§4.2): hash the MD BODY (`md`, line ~33), NOT `sourceMd`/`video.summaryMd`
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:853:lib/cloud-sync/sync-run.ts:58:/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:854:lib/cloud-sync/sync-run.ts:59:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:855:lib/cloud-sync/sync-run.ts:60:  if (!video.summaryMd) return null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:856:lib/cloud-sync/sync-run.ts:61:  const buf = await blob.get(p, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:860:lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:861:lib/cloud-sync/sync-run.ts:106: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:862:lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:863:lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:871:lib/cloud-sync/sync-run.ts:150:  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:875:lib/cloud-sync/sync-run.ts:160:  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:876:lib/cloud-sync/sync-run.ts:161:    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:877:lib/cloud-sync/sync-run.ts:167:  if (video.summaryMd && mdBody != null) {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:878:lib/cloud-sync/sync-run.ts:169:    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:880:lib/cloud-sync/sync-run.ts:184:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:881:lib/cloud-sync/sync-run.ts:186:    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:882:lib/cloud-sync/sync-run.ts:187:    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:883:lib/cloud-sync/sync-run.ts:188:    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:884:lib/cloud-sync/sync-run.ts:189:    delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:888:lib/cloud-sync/sync-run.ts:201:  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:890:lib/cloud-sync/sync-run.ts:204:    const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:891:lib/cloud-sync/sync-run.ts:205:    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:892:lib/cloud-sync/sync-run.ts:206:      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:896:lib/cloud-sync/sync-run.ts:274: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:899:lib/cloud-sync/sync-run.ts:280:  if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:900:lib/cloud-sync/sync-run.ts:284:  const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:903:lib/cloud-sync/sync-run.ts:304:    summaryMd: key,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:905:lib/cloud-sync/sync-run.ts:335:    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:907:lib/cloud-sync/sync-run.ts:348:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:908:lib/cloud-sync/sync-run.ts:349:  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:914:lib/cloud-sync/sync-run.ts:396:/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:917:lib/cloud-sync/sync-run.ts:400: *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:929:lib/cloud-sync/sync-run.ts:495:        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:932:lib/cloud-sync/sync-run.ts:508:        //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:933:lib/cloud-sync/sync-run.ts:510:        if (lv.summaryMd && la.mdHash == null) throw new Error(`local MD body unreadable for ${id}`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:934:lib/cloud-sync/sync-run.ts:511:        if (cv.summaryMd && ca.mdHash == null) throw new Error(`cloud MD body unreadable for ${id}`);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:954:lib/storage/supabase/supabase-metadata-store.ts:11:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:955:lib/storage/supabase/supabase-metadata-store.ts:14:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:958:lib/storage/supabase/supabase-metadata-store.ts:53:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:959:lib/storage/supabase/supabase-metadata-store.ts:54:            .artifacts?.summaryMd?.status === 'promoted',
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:969:lib/html-doc/ensure.ts:32:  if (!video.summaryMd) throw new Error('no summary note for this video');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:970:lib/html-doc/ensure.ts:35:  const base = video.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:992:lib/html-doc/build-doc-html.ts:73:  // Companion-path containment first, so it keeps independent 400 coverage before summaryMd derivation.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:993:lib/html-doc/build-doc-html.ts:93:  } else if (video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:994:lib/html-doc/build-doc-html.ts:94:    const sumRel = video.summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:995:lib/html-doc/build-doc-html.ts:102:  let summaryMdPath: string;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:996:lib/html-doc/build-doc-html.ts:104:    summaryMdPath = assertIndexRelPathWithin(outputFolder, path.join(relDir, `${base}.md`));
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:997:lib/html-doc/build-doc-html.ts:110:  let summaryMdContent: string;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:998:lib/html-doc/build-doc-html.ts:112:    summaryMdContent = fs.readFileSync(summaryMdPath, 'utf-8');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:999:lib/html-doc/build-doc-html.ts:119:    parsed = parseSummaryMarkdown(summaryMdContent);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1000:lib/html-doc/build-doc-html.ts:135:  const cropMap = await prepareSlideCropMap(dug, summaryMdPath);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1001:lib/html-doc/build-doc-html.ts:142:      mdPath: summaryMdPath,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1002:lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1004:lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1005:lib/html-doc/rerender.ts:42:  const base = video.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1006:lib/html-doc/rerender.ts:48:    // Fail closed on a crafted summaryMd that escapes the output folder. assertIndexRelPathWithin
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1007:lib/html-doc/rerender.ts:50:    assertIndexRelPathWithin(outputFolder, video.summaryMd, '.md');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1008:lib/html-doc/rerender.ts:51:    const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1009:lib/html-doc/rerender.ts:64:  parsed.sourceMd = video.summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1010:lib/html-doc/rerender.ts:78:  summaryMd: string | null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1012:lib/html-doc/rerender.ts:118:        summaryMd: video.summaryMd,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1013:lib/html-doc/rerender.ts:126:      tally.details.push({ summaryMd: video.summaryMd, status: 'error', message: (err as Error).message });
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1015:lib/html-doc/serve-summary-core.ts:47:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1016:lib/html-doc/serve-summary-core.ts:48:    .artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1017:lib/html-doc/serve-summary-core.ts:53:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1018:lib/html-doc/serve-summary-core.ts:54:  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1019:lib/html-doc/serve-summary-core.ts:56:  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1021:lib/html-doc/serve-summary-core.ts:70:  // derived deterministically from the SAME summaryMd key the model store is keyed on.
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1023:lib/cloud-sync/backfill.ts:5:// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1024:lib/cloud-sync/backfill.ts:6:// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1025:lib/cloud-sync/backfill.ts:10:    summaryMdKey: video.summaryMd ?? null,
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1026:lib/html-doc/batch.ts:21:  if (!video.summaryMd) return [];
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1027:lib/html-doc/batch.ts:24:    const md = await fs.readFile(path.join(outputFolder, video.summaryMd), 'utf8');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1028:lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1032:lib/cloud-sync/types.ts:5:  summaryMdKey: string | null;    // the blob KEY (video.summaryMd) — NOT the body
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1034:lib/dig/cloud/resolve-summary-key.ts:3:/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1035:lib/dig/cloud/resolve-summary-key.ts:4: *  falling back to the top-level `summaryMd` — validated via `assertCloudSummaryMdKey`. Returns
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1036:lib/dig/cloud/resolve-summary-key.ts:7: *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1037:lib/dig/cloud/resolve-summary-key.ts:9: *  top-level `summaryMd` fallback for videos with no artifact record. The dig TRIGGER owns that
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1038:lib/dig/cloud/resolve-summary-key.ts:13:  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1039:lib/dig/cloud/resolve-summary-key.ts:14:  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1044:lib/html-doc/nav.ts:360:        var digN=isPageshow?null:_sp.get('dig');
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1047:lib/html-doc/eligibility.ts:7:  return !!v.summaryMd;
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1048:lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1049:lib/html-doc/eligibility.ts:19: *   A video with no summaryMd is never eligible (nothing to generate from).
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1050:lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md:1051:lib/html-doc/render-dig-deeper.ts:120:      const box = cropMap.get(absPath) ?? null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:17:- Round 1 (`docs/reviews/whole-branch-cloud-sync-codex.md`) → 1 Blocking + 2 High → fixed in `32a164c`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:18:- Round 2 (`docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md` and `-claude.md`) → confirmed WB-B1/WB-H2 fixed, found WB-H1 INCOMPLETE (H-R2-1) plus a REGRESSION introduced by the WB-H2 fix (H-R2-2) and a Medium (M-R2-2) → fixed in `1f54c60`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:23:1. **H-R2-1** — the unreadable-MD-body guard moved ABOVE `ensureReceiverSlot` in `copyAdditiveVideo` (`lib/cloud-sync/sync-run.ts`). VERIFY: is there now NO path that creates partial receiver state before a possible throw (consider `setPlaylistMeta` inside `ensureReceiverSlot`, the staged-blob put, and `claimVideoSlot`)? Does the two-run e2e assertion actually fail if the guard is moved back? Is the residual `if (video.summaryMd && mdBody != null)` condition at the staging block dead/redundant given the guard above, and if so does that redundancy hide anything?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:24:2. **H-R2-2** — `digDeeperMd: null` removed from `transferClassA`'s `completeTuple`. VERIFY: with `digDeeperMd` preserved but the MD BODY replaced by the winner's, is the retained dig doc now semantically stale in a way that misleads a consumer (`lib/html-doc/build-doc-html.ts:75,86`, `app/api/videos/[id]/dig-state/route.ts`, `lib/pdf/pdf-path.ts`)? Specifically: dig sections are anchored to summary section timestamps/anchors — if the winner MD has different sections, does merging the preserved dig produce wrong or orphaned anchors? Weigh that against the cost of destroying paid content. Is `digDeeperHtml: null` sufficient to force the re-merge? Is the additive path (`sanitizeAdditiveVideo`, which still nulls `digDeeperMd`) still correct given it targets a receiver with no existing row?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:25:3. **M-R2-2** — the corrections guard narrowed to `correctionsUnresolved && la.mdHash != null && ca.mdHash != null`, with `deriveClassASignals` hoisted above the guard. VERIFY: the hoist claims to be behavior-neutral because derivation is pure — confirm `readMdBody` has no side effects and that moving TWO blob reads earlier cannot change ordering/error behavior (e.g. a blob read that throws now aborts the video BEFORE the Class-B baseline would have been written — is that a behavior change, and is it the right one?). Confirm the WB-B1 intent still holds exactly for the both-have-MD case. Confirm the one-sided hydration case cannot destroy anything or record a false agreement.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:30:- Money-safety: no enqueue, no `spend_ledger` consumption, no regenerable-cache resurrection; `needsRegen` report-only. ALSO: any path that forces the USER to re-spend (the H-R2-2 class of bug) counts as a money finding.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:39:KNOWN-and-ACCEPTED / DEFERRED — do NOT re-report unless you prove they mask a real bug: T14-M1, T14-M2, T5 coverage gaps, T4 automock comment; Claude-R2-M1 (stale non-`summaryMd` artifact pointers on transfer); Codex-R2-Medium (absent/undefined companion scalars not explicitly cleared). Also do NOT report `tests/integration/reservation-release.test.ts` failures — verified pre-existing on a clean tree (local Supabase state pollution), tracked separately.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:42:Per finding: severity (Blocking/High/Medium/Low), `file:line`, concrete failure scenario (inputs → wrong outcome), fix. For Part A, state per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:64:Round 1 found 1 Blocking + 2 High. They were fixed in commit `32a164c` (the branch HEAD). Your job has TWO explicit parts:
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:67:1. **WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy.** Fix: in `runSync` (`lib/cloud-sync/sync-run.ts`), when `merges.corrections.winner === 'equal' && merges.corrections.conflict`, skip the Class-A copy entirely, count `needsRegen`, and write `buildCorrectionsUnresolvedBaseline` (carries the PREVIOUS classA baseline, or an honest `{docVersionMajor:0, mdGeneratedAt:null, mdCorrectionsHash:null, mdHash:null}` placeholder on first sync). VERIFY: is the guard placed BEFORE every write path (including the companion transfer and any archived/delete handling)? Does the `continue` skip anything that MUST still run (delete-inference "seen" marking, report counters, companion, archived sync)? Is `report.archivedNotSynced` incremented correctly and only there? Does the placeholder baseline (docVersionMajor 0) cause a wrong decision anywhere that DOES read the Class-A baseline — confirm reconcileClassA truly never reads it.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:68:2. **WB-H1 (High) — additive create could advertise `promoted` with no blob.** Fix: throw when `video.summaryMd` is set but `mdBody == null`; strip `sanitized.artifacts.summaryMd` when no blob was written; post-write verify that the receiver row advertises `status==='promoted'` at the right key. VERIFY: does the throw leave PARTIAL state (a bare receiver slot created by `ensureReceiverSlot`, a staged blob orphaned) that a later run mishandles? Is the summary-less video (summaryMd == null) path still correct? Does the strict post-write assert produce false failures on the local store (shallow-merge) vs the cloud store (`merge_video_data` deep-merge) — a cross-backend semantic mismatch?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:69:3. **WB-H2 (High) — two-sided transfer left stale rendered HTML.** Fix: `transferClassA` sets `summaryHtml/digDeeperHtml/digDeeperMd` to `null` in the update payload. VERIFY: does `merge_video_data` (migration 0021 / 0009) actually STORE a JSON null (invalidating) rather than treating null as "no change" and skipping the key — trace the RPC body. Same question for the local store's shallow merge. If null is dropped by either backend, the fix is cosmetic and the stale-HTML bug survives. Also: are there OTHER regenerable-cache fields that should have been nulled (compare against `sanitizeAdditiveVideo`'s strip list — any field it strips that transferClassA does not null is a gap), and does nulling `digDeeperMd` orphan or strand a dig-deeper blob / dig state?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:77:- Cross-backend (local vs Supabase) semantic mismatches — the round-1 `transferClassA` promote-vs-put bug is the archetype; the null-invalidation question above is a live candidate sibling.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:86:For each finding: severity (Blocking/High/Medium/Low), `file:line`, the concrete failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. For Part A, state explicitly per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:104://    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:150:/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:151:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:152:  if (!video.summaryMd) return null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:153:  const buf = await blob.get(p, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:154:  return buf ? buf.toString('utf8') : null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:165:/** Read one video record (or null if absent) from a store's index. */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:166:async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:168:  return idx.videos.find((v) => v.id === id) ?? null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:197: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:198: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:201:  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:202:  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:203:  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:204:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:206:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:221: *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:226:): Promise<{ position: number; serialNumber: number } | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:229:  if (idx.videos.some((v) => v.id === video.id)) return null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:240:  video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:245:  if (video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:246:    // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:250:    if (mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:251:      throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:254:    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:269:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:271:    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:272:    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:273:    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:274:    delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:285:  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:286:  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:289:    const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:290:    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:291:      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:299:  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:327:### WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:353:  write-only.** The `docVersionMajor: 0 / mdHash: null` placeholder is therefore inert; next run
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:359:### WB-H1 (High) — additive create could advertise `promoted` with no blob
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:363:throw on `summaryMd && mdBody == null` (158-160); strip a residual `artifacts.summaryMd` when no blob was
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:367:- **`summaryMd == null` path still correct.** `video.summaryMd` falsy → no throw, `wroteBlob` stays false →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:372:  `sanitized.artifacts` is a whole-object replace, so `artifacts.summaryMd` lands verbatim. Cloud:
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:379:### WB-H2 (High) — two-sided transfer left stale rendered HTML
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:383:I traced whether a JSON `null` actually persists on each backend, as instructed:
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:387:  (`:18-21`) that removes only `updatedAt`/`summaryReady` — **it does not drop nulls**. PostgREST
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:388:  serializes the JSON null through. In `merge_video_data`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:390:  `data || (p_fields - 'artifacts')`. Postgres `jsonb ||` **sets the key to JSON null** rather than
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:391:  dropping it (`'{"a":1}'::jsonb || '{"a":null}'::jsonb` → `{"a": null}`). Only `jsonb_strip_nulls`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:392:  drops nulls, and it is used in `persist_summary`, not here. **Null is stored.** ✅
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:395:  so `summaryHtml: null` overwrites — then `writeIndex` → `JSON.stringify`, which preserves `null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:398:  `lib/html-doc/ensure.ts:54` (`else if (!video.summaryHtml)`) both branch on falsiness, so a JSON null
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:404:  | `summaryHtml` | null | null (314) | ✅ match |
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:405:  | `digDeeperHtml` | null | null (315) | ✅ match |
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:406:  | `digDeeperMd` | null | null (316) | ❌ **wrong on this path** — Part B H1 |
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:407:  | `artifacts.*` except `summaryMd` | dropped (113-115) | **not cleared** (319) | see Part B M1 |
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:410:  The commit comment "Matches `sanitizeAdditiveVideo`, which already nulls these" is the flawed premise:
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:419:### H1 (High) — `transferClassA` nulls `digDeeperMd`, orphaning the loser's paid dig-deeper doc
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:433:4. `transferClassA(cloudSide, localSide, …)` sends `digDeeperMd: null` in `completeTuple` (316) →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:434:   `indexStore.updateVideoFields` shallow-spread → `index.json` now has `digDeeperMd: null`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:446:Note this is a **regression introduced by the WB-H2 fix** — before `32a164c` the field was not sent at all.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:448:**Fix:** delete the `digDeeperMd: null` line (316). Keep `summaryHtml: null` and `digDeeperHtml: null` —
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:450:stale it, and `lib/html-doc/eligibility.ts:23` (`!!v.summaryMd && !v.digDeeperMd`) plus
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:455:### M1 (Medium) — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:460:`artifacts: { summaryMd: … }` **preserves** every other key already on the loser row. Any non-`summaryMd`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:465:Today the practical blast radius is small — the artifacts map is dominated by `summaryMd`, and the
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:466:regenerable HTML is gated on the top-level `summaryHtml`, which *is* nulled. Hence Medium, not High. But
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:469:non-`summaryMd` keys explicitly or record the divergence as a deliberate, documented decision.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:471:### M2 (Medium) — the WB-B1 guard also blocks purely-additive (non-destructive) MD hydration
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:476:**Scenario:** cloud row has `summaryMd` + a promoted blob; the local row exists (so this is the two-sided
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:477:path, not the additive path) but has `summaryMd == null`; both sides carry a *backfilled* corrections
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:484:an MD body, i.e. `la.mdHash != null && ca.mdHash != null`), which preserves the WB-B1 fix's intent exactly
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:487:### L1 (Low) — the WB-H1 throw leaves a bare receiver slot; converges, but via a different code path
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:495:takes the two-sided path; `deriveClassASignals` on the bare row yields `mdHash: null`, so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:497:(`winner … has no MD body to copy`) while the cloud blob is still unreadable — then heals cleanly once it
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:511:  trigger. The WB-B1 e2e test asserts `spendLedgerTotal()` is unchanged across the run.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:524:  cloud vs shallow spread on local; null persistence on both). The only surviving mismatch is M1 above.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:528:- **Idempotency.** Ran each new branch twice mentally; WB-B1 is additionally covered by an explicit
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:533:**NOT CONVERGED** — 1 new High (H1: `digDeeperMd: null` destroys the local loser's paid dig-deeper doc, a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:534:regression introduced by the WB-H2 fix), plus 2 Mediums and 1 Low. Another round is required after H1 is
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:549:`lib/cloud-sync/backfill.ts:11`: `mdHash: mdBody != null ? mdHash(mdBody) : null`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:550:The premise of the scenario is that the cloud blob is UNREADABLE, so `readMdBody` returns null and the
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:551:cloud side hashes to `null` as well. Both sides null → `reconcile-class-a.ts:21`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:556:**High**, tracked as **H-R2-1**, and is being fixed by validating the MD body BEFORE
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:559:Lesson for round 3: the single-run WB-H1 e2e test passed while this bug was live. Assertions about
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:560:baseline/idempotency effects require running `runSync` TWICE — as the WB-B1 test already does.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:565:1f54c60 (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:576:    fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:579:    WB-B1 and WB-H2 genuinely fixed; WB-H1 was INCOMPLETE and WB-H2 introduced a regression.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:581:    H-R2-1 (High) — copyAdditiveVideo claimed the receiver slot BEFORE validating the MD
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:582:    body, so an unreadable source blob left a bare row behind on the throw. The next run
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:583:    then saw a two-sided video whose both sides derive mdHash === null, reconcileClassA
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:589:    H-R2-2 (High, regression from the WB-H2 fix) — transferClassA nulled digDeeperMd, which
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:595:    M-R2-2 (Medium) — the WB-B1 corrections guard skipped Class A unconditionally, stranding
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:599:    Deferred with owner: stale non-summaryMd artifact pointers on transfer; absent companion
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:617: /** Read one video record (or null if absent) from a store's index. */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:618: async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:620:   return idx.videos.find((v) => v.id === id) ?? null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:649:  *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:650:  *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:653:   v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:654:   v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:655:   v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:656:   // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:658:     v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:673:  *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:678: ): Promise<{ position: number; serialNumber: number } | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:681:   if (idx.videos.some((v) => v.id === video.id)) return null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:692:   video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:694:+  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:698:+  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:700:+  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:704:+  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:705:+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:711:-  if (video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:712:-    // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:716:-    if (mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:717:-      throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:719:+  if (video.summaryMd && mdBody != null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:721:     const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:736:     sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:738:     // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:739:     // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:740:     // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:741:     delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:752:   // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:753:   // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:756:     const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:757:     if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:758:       throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:766:   classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:826:  *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:832:   if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:836:   const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:856:     summaryMd: key,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:858:     mdGeneratedAt: wv.mdGeneratedAt ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:859:     mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:867:     // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:871:     // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:872:-    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:875:+    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:881:+    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:884:     summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:885:     digDeeperHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:886:-    digDeeperMd: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:889:     artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:902:   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:903:   const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:936:   winnerSignals: ClassASignals, winnerMdHash: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:950: /** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:954:  *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:962:       ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1002:         //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1005:           const presentIsLocal = lv != null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1015:               deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1033:         // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1056:+        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1066:+        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1070:         let winnerMdHash: string | null = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1072:         let winnerSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1073:         let loserSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1114:     expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1141:   // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1146:   it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1186:   // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1187:   //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1188:   //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1191:-  it('WB-H1: additive create with a promoted summaryMd but no blob throws; no promoted row, no baseline', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1192:+  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1194:+  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1197:+  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1199:     // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1205:-    // The local receiver must not advertise a promoted summaryMd (bare slot at most; no blob copied).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1207:-    expect(artifactsOf(local)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1210:+    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1219:+    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1223:   // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1225:   //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1226:   it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1242:     expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1246:+  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1251:+  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1252:+  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1272:+    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1273:+    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1274:+    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1277:+  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1285:+      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1305:+    expect(local?.summaryMd).toBe(key(ctx));
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1306:+    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1334:    12	//    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1380:    58	/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1381:    59	async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1382:    60	  if (!video.summaryMd) return null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1383:    61	  const buf = await blob.get(p, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1384:    62	  return buf ? buf.toString('utf8') : null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1395:    73	/** Read one video record (or null if absent) from a store's index. */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1396:    74	async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1398:    76	  return idx.videos.find((v) => v.id === id) ?? null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1427:   105	 *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1428:   106	 *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1431:   109	  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1432:   110	  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1433:   111	  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1434:   112	  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1436:   114	    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1451:   129	 *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1456:   134	): Promise<{ position: number; serialNumber: number } | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1459:   137	  if (idx.videos.some((v) => v.id === video.id)) return null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1470:   148	  video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1472:   150	  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1476:   154	  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1478:   156	  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1482:   160	  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1483:   161	    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1489:   167	  if (video.summaryMd && mdBody != null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1491:   169	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1506:   184	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1508:   186	    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1509:   187	    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1510:   188	    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1511:   189	    delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1522:   200	  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1523:   201	  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1526:   204	    const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1527:   205	    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1528:   206	      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1536:   214	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1596:   274	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1602:   280	  if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1606:   284	  const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1626:   304	    summaryMd: key,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1628:   306	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1629:   307	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1637:   315	    // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1641:   319	    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1644:   322	    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1650:   328	    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1653:   331	    summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1654:   332	    digDeeperHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1657:   335	    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1670:   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1671:   349	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1704:   382	  winnerSignals: ClassASignals, winnerMdHash: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1718:   396	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1722:   400	 *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1730:   408	      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1770:   448	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1773:   451	          const presentIsLocal = lv != null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1783:   461	              deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1801:   479	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1823:   501	        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1830:   508	        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1834:   512	        let winnerMdHash: string | null = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1836:   514	        let winnerSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1837:   515	        let loserSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1877:tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1879:tests/integration/cloud-sync/stamping.int.test.ts:94:      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1897:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:118:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1903:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:140:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1905:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:146:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1906:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:148:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1907:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:149:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1911:lib/storage/resolve.ts:24: *  CRITICAL (Codex Blocking): preserve the RAW outputFolder string — do NOT
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1915:tests/integration/cloud-sync/e2e.int.test.ts:32:const artifactsOf = (rec: { [k: string]: unknown } | null) =>
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1916:tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1918:tests/integration/cloud-sync/e2e.int.test.ts:43:    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1921:tests/integration/cloud-sync/e2e.int.test.ts:91:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1937:tests/integration/cloud-sync/e2e.int.test.ts:268:  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1941:tests/integration/cloud-sync/e2e.int.test.ts:280:    expect(local?.summaryHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1942:tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1947:tests/integration/cloud-sync/e2e.int.test.ts:328:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1948:tests/integration/cloud-sync/e2e.int.test.ts:361:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1950:tests/integration/cloud-sync/e2e.int.test.ts:393:  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1955:tests/integration/cloud-sync/e2e.int.test.ts:434:  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1956:tests/integration/cloud-sync/e2e.int.test.ts:435:  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1957:tests/integration/cloud-sync/e2e.int.test.ts:445:    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1958:tests/integration/cloud-sync/e2e.int.test.ts:453:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1959:tests/integration/cloud-sync/e2e.int.test.ts:462:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1960:tests/integration/cloud-sync/e2e.int.test.ts:468:  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1961:tests/integration/cloud-sync/e2e.int.test.ts:469:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1965:tests/integration/cloud-sync/e2e.int.test.ts:485:    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1966:tests/integration/cloud-sync/e2e.int.test.ts:489:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1968:tests/integration/cloud-sync/e2e.int.test.ts:494:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1969:tests/integration/cloud-sync/e2e.int.test.ts:495:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1975:tests/integration/cloud-sync/e2e.int.test.ts:515:    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1976:tests/integration/cloud-sync/e2e.int.test.ts:516:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1977:tests/integration/cloud-sync/e2e.int.test.ts:517:    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1983:tests/integration/cloud-sync/e2e.int.test.ts:549:    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1993:supabase/migrations/0021_cloud_sync_signals.sql:113:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2000:supabase/migrations/0021_cloud_sync_signals.sql:137:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2002:supabase/migrations/0021_cloud_sync_signals.sql:143:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2003:supabase/migrations/0021_cloud_sync_signals.sql:145:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2004:supabase/migrations/0021_cloud_sync_signals.sql:146:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2005:tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2008:lib/cloud-sync/types.ts:9:  mdCorrectionsHash: string | null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2009:lib/cloud-sync/types.ts:32:  classA: { docVersionMajor: number; mdGeneratedAt: string | null; mdCorrectionsHash: string | null; mdHash: string | null };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2012:lib/cloud-sync/backfill.ts:14:    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2017:lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2018:lib/cloud-sync/sync-run.ts:109:  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2019:lib/cloud-sync/sync-run.ts:110:  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2020:lib/cloud-sync/sync-run.ts:111:  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2021:lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2023:lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2025:lib/cloud-sync/sync-run.ts:184:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2027:lib/cloud-sync/sync-run.ts:189:    delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2029:lib/cloud-sync/sync-run.ts:204:    const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2032:lib/cloud-sync/sync-run.ts:307:    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2034:lib/cloud-sync/sync-run.ts:322:    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2037:lib/cloud-sync/sync-run.ts:331:    summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2038:lib/cloud-sync/sync-run.ts:332:    digDeeperHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2039:lib/cloud-sync/sync-run.ts:335:    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2043:lib/cloud-sync/sync-run.ts:408:      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2048:tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2050:lib/storage/local/local-metadata-store.ts:38:  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2058:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2074:tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2096:lib/dig/cloud/resolve-summary-key.ts:3:/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2097:lib/dig/cloud/resolve-summary-key.ts:7: *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2099:lib/dig/cloud/resolve-summary-key.ts:13:  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2100:lib/dig/cloud/resolve-summary-key.ts:14:  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2110:lib/dig/cloud/enqueue-dig-core.ts:16:  enqueueIp: string | null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2119:lib/storage/supabase/supabase-metadata-store.ts:11:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2120:lib/storage/supabase/supabase-metadata-store.ts:14:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2121:lib/storage/supabase/supabase-metadata-store.ts:53:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2122:lib/storage/supabase/supabase-metadata-store.ts:54:            .artifacts?.summaryMd?.status === 'promoted',
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2134:tests/lib/cloud-sync/regenerate-stamp.test.ts:6:// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2143:app/api/videos/[id]/regenerate/route.ts:86:      tldr, takeaways, summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2145:app/api/videos/[id]/regenerate/route.ts:95:      summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2158:lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2160:lib/html-doc/serve-doc.ts:57:  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2163:lib/html-doc/serve-doc.ts:64:  const row = (data as Array<{ status: string; release_token: string | null }> | null)?.[0];   // table-return → data[0]
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2165:lib/html-doc/serve-doc.ts:66:  const releaseToken = row?.release_token ?? null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2188:lib/html-doc/serve-summary-core.ts:47:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2189:lib/html-doc/serve-summary-core.ts:48:    .artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2190:lib/html-doc/serve-summary-core.ts:53:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2199:lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2200:lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2203:lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2204:lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2207:/bin/bash -lc 'git status --short && rg -n "H-R2-1|H-R2-2|M-R2-2|WB-H1|WB-H2|WB-B1|corrections conflict|digDeeperMd" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2215:tests/integration/cloud-sync/e2e.int.test.ts:388:  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2216:tests/integration/cloud-sync/e2e.int.test.ts:393:  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2217:tests/integration/cloud-sync/e2e.int.test.ts:433:  // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2218:tests/integration/cloud-sync/e2e.int.test.ts:438:  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2219:tests/integration/cloud-sync/e2e.int.test.ts:443:  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2220:tests/integration/cloud-sync/e2e.int.test.ts:466:  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2221:tests/integration/cloud-sync/e2e.int.test.ts:469:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2222:tests/integration/cloud-sync/e2e.int.test.ts:489:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2223:tests/integration/cloud-sync/e2e.int.test.ts:494:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2224:tests/integration/cloud-sync/e2e.int.test.ts:495:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2226:tests/integration/cloud-sync/e2e.int.test.ts:515:    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2227:tests/integration/cloud-sync/e2e.int.test.ts:516:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2228:tests/integration/cloud-sync/e2e.int.test.ts:517:    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2229:tests/integration/cloud-sync/e2e.int.test.ts:520:  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2348:    32	const artifactsOf = (rec: { [k: string]: unknown } | null) =>
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2349:    33	  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2359:    43	    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2407:    91	    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2526:   210	    expect(local?.personalNote == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2527:   211	    expect(cloud?.personalNote == null).toBe(true); // the clear propagated; 'old' not resurrected
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2573:   257	    const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2584:   268	  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2596:   280	    expect(local?.summaryHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2597:   281	    expect(local?.digDeeperHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2627:   311	    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2634:   318	    expect(local?.summaryMd == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2644:   328	    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2677:   361	    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2704:   388	  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2709:   393	  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2749:   433	  // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2750:   434	  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2751:   435	  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2754:   438	  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2756:   440	  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2759:   443	  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2761:   445	    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2769:   453	    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2778:   462	    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2782:   466	  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2784:   468	  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2785:   469	  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2801:   485	    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2805:   489	  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2810:   494	  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2811:   495	  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2831:   515	    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2832:   516	    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2833:   517	    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2836:   520	  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2844:   528	      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2864:   548	    expect(local?.summaryMd).toBe(key(ctx));
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2865:   549	    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2884:     9	const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2892:    17	  const lHas = local.mdHash != null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2893:    18	  const cHas = cloud.mdHash != null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2906:    31	  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2935:     5	// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2936:     6	// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2937:     7	export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2938:     8	  const hasReal = video.mdGeneratedAt != null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2940:    10	    summaryMdKey: video.summaryMd ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2941:    11	    mdHash: mdBody != null ? mdHash(mdBody) : null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2943:    13	    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2944:    14	    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3079:   112	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3080:   113	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3087:   120	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3100:   133	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3103:   136	           || jsonb_build_object('summaryMd', jsonb_build_object(
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3104:   137	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3110:   143	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3112:   145	                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3113:   146	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3164:    38	  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3206:    80	  // when currently absent/null in the JSON index; a no-op otherwise.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3298:    11	// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3301:    14	// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3340:    53	          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3341:    54	            .artifacts?.summaryMd?.status === 'promoted',
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3365:    78	        playlist_title: meta.playlistTitle ?? null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3489:   202	  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3505:   218	      .is('playlist_title', null)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3514:   227	  // by playlist_title (nulls last) then created_at — created_at MUST be in the select
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3522:   235	      .order('playlist_title', { nullsFirst: false })
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3530:Backend semantics line up for the fields at issue: cloud `merge_video_data` stores JSON nulls and deep-merges `artifacts`, while local shallow-spreads nulls. I’m checking whether any of that creates a round-3 finding rather than just leaving the accepted medium about non-`summaryMd` artifacts.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3552:    19	 *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3641:   108	    fs.writeFileSync(tmpPath, JSON.stringify(index, null, 2), 'utf-8');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3688:/bin/bash -lc 'rg -n "summaryMd|digDeeperMd|data-root|dig|M2a|out of scope|Stage 3|baseline|corrections" docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3750:254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3790:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3825:lib/cloud-sync/backfill.ts:7:export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3828:tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3843:lib/cloud-sync/sync-run.ts:59:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3853:lib/cloud-sync/sync-run.ts:461:              deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3866:I haven’t found a new Blocking/High so far. The only live concern is lower severity: the M-R2-2 regression test proves first-run hydration, but it does not assert second-run idempotency or manifest shape for that new branch. I’m deciding whether that is a defect or only a coverage gap.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3924:    55	    const cachedVersion = generatorMatch ? generatorMatch[1] : null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3942:    73	  // Companion-path containment first, so it keeps independent 400 coverage before summaryMd derivation.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3943:    74	  let digDeeperPath: string | null = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3962:    93	  } else if (video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3963:    94	    const sumRel = video.summaryMd;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3971:   102	  let summaryMdPath: string;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3973:   104	    summaryMdPath = assertIndexRelPathWithin(outputFolder, path.join(relDir, `${base}.md`));
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3979:   110	  let summaryMdContent: string;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3981:   112	    summaryMdContent = fs.readFileSync(summaryMdPath, 'utf-8');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3988:   119	    parsed = parseSummaryMarkdown(summaryMdContent);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3996:   127	  if (digDeeperPath !== null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4053:    10	 * - summary:    `pdfs/{basename(summaryMd) sans .md}.pdf`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4068:    25	    if (!video.summaryMd) throw new Error('no summary for this video');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4069:    26	    base = path.basename(video.summaryMd).replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4083:     7	 *   - startSec = section.timeRange?.startSec ?? null.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4084:     8	 *   - GIST trusted only if: envelope non-null AND sameTitles(parsedTitles, envelope.sourceSections)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4085:     9	 *     AND envelope.model.sections[i] exists → { lead, bullets }; otherwise gist = null (skeleton).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4104:    28	  numeral: string | null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4106:    30	  startSec: number | null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4107:    31	  gist: { lead: string; bullets: { text: string }[] } | null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4108:    32	  dug: { bodyMarkdown: string } | null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4130:    54	  envelope: ModelEnvelope | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4136:    60	  // If the envelope is absent or the section titles have drifted, all gists are null.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4138:    62	    envelope !== null && sameTitles(parsedTitles, envelope.sourceSections);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4162:    86	    const startSec = section.timeRange?.startSec ?? null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4165:    89	    let gist: MergedSection['gist'] = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4166:    90	    if (titlesAligned && envelope !== null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4174:    98	    let dug_: MergedSection['dug'] = null;
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4176:   100	    if (startSec !== null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4191:   115	      dug: dug_, // may be overwritten in step 2 pass below, but step-2 only fills null slots
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4218:   142	    if (ms.dug !== null) continue; // already matched in step 1
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4413:/bin/bash -lc 'npx jest tests/integration/cloud-sync/e2e.int.test.ts --runInBand -t "H-R2-1|H-R2-2|M-R2-2|WB-B1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4483:tests/lib/cloud-sync/auth.test.ts:11:    await expect(getAuthedClient(memStore(null))).rejects.toThrow(/cloud-sync login/);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4616:/bin/bash -lc "node -p \"JSON.stringify(require('./package.json').scripts,null,2)\"" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4641:/bin/bash -lc 'npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1|H-R2-2|M-R2-2|WB-B1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4645:> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1|H-R2-2|M-R2-2|WB-B1
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4651:Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1|H-R2-2|M-R2-2|WB-B1".
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4654:The targeted integration tests pass: 4 selected tests, 18 skipped in that file. To answer the specific “would it fail if moved back?” question, I’m doing a temporary mutation of `copyAdditiveVideo`, running the H-R2-1 test, then restoring the file.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4664:   video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4666:-  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4670:-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4672:-  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4676:-  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4677:-    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4687:+  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4688:+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4700:   video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4702:-  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4706:-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4708:-  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4712:-  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4713:-    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4723:+  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4724:+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4731:/bin/bash -lc 'npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4738:   video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4740:-  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4744:-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4746:-  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4750:-  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4751:-    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4761:+  if (video.summaryMd && mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4762:+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4771:> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4774:  ● cloud-sync §10 end-to-end scenarios › WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4784:      453 |     expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4794:Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1".
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4802:`sync-run.ts` is back to HEAD behavior. I’m doing one final targeted pass for worktree cleanliness and the restored H-R2-1 test.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4814:/bin/bash -lc 'git diff -- lib/cloud-sync/sync-run.ts && npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4818:> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4824:Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1".
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4836:tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4838:tests/integration/cloud-sync/e2e.int.test.ts:494:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4840:tests/integration/cloud-sync/e2e.int.test.ts:516:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4885:tests/lib/html-doc/build-doc-html.test.ts:36:    const r = await buildDocHtml(video({ summaryHtml: null }), dir, 'summary');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4891:tests/lib/html-doc/build-doc-html.test.ts:71:    const r = await buildDocHtml(video({ summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4902:The restored H-R2-1 test passes again. I’m running the cloud-sync integration subset now for the broader branch-level check, still excluding the known reservation-release suite.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4932:H-R2-1: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4933:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160) now throws before `ensureReceiverSlot` at line 164, so no `setPlaylistMeta`, staged blob write, `claimVideoSlot`, receiver row, or baseline can happen after an unreadable advertised MD body. The remaining `if (video.summaryMd && mdBody != null)` at line 167 is redundant after the guard, but harmless; it does not hide a path because the only alternative is a legitimate summary-less row. I temporarily moved the guard back and the H-R2-1 integration test failed on the bare local row assertion, then restored the file.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4935:H-R2-2: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4936:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:331) clears `summaryHtml` and `digDeeperHtml`, but no longer sends `digDeeperMd: null`. Preserving `digDeeperMd` can leave old dig sections matched or orphaned against a new summary via [lib/html-doc/dig-merge.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/dig-merge.ts:97), but that is a known M2a boundary: dig is out of scope, orphans are explicit, and destroying the pointer forces re-spend. `digDeeperHtml: null` is sufficient for the stale rendered artifact. `sanitizeAdditiveVideo` still correctly nulls `digDeeperMd` for a receiver with no existing row.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4939:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:491) derives signals before the narrowed guard, and [lib/cloud-sync/backfill.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/backfill.ts:7) is pure over the record plus supplied MD body. The hoist can surface blob-read errors earlier, but that is the right behavior: baseline must not advance if Class-A evidence is unreadable. The both-have-MD conflict path still takes the WB-B1 skip at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:501). The one-sided hydration path writes the copied MD only after `transferClassA` lands, preserves unresolved corrections in Class-B baseline, and continues to report `needsRegen`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4943:No new Blocking, High, Medium, or Low defects found in the reviewed scope.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4945:Checked baseline advancement, durable-before-advertise ordering, manifest-after-commit, money-safety, `needsRegen` report-only behavior, RLS/no-service-role usage, and local-vs-Supabase null/deep-merge semantics. The accepted stale non-`summaryMd` artifact-pointer medium remains accepted and was not re-reported.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4951:Temporary mutation of H-R2-1 failed as expected, then restored; `lib/cloud-sync/sync-run.ts` has no remaining diff.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4953:**CONVERGED**
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4958:H-R2-1: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4959:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160) now throws before `ensureReceiverSlot` at line 164, so no `setPlaylistMeta`, staged blob write, `claimVideoSlot`, receiver row, or baseline can happen after an unreadable advertised MD body. The remaining `if (video.summaryMd && mdBody != null)` at line 167 is redundant after the guard, but harmless; it does not hide a path because the only alternative is a legitimate summary-less row. I temporarily moved the guard back and the H-R2-1 integration test failed on the bare local row assertion, then restored the file.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4961:H-R2-2: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4962:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:331) clears `summaryHtml` and `digDeeperHtml`, but no longer sends `digDeeperMd: null`. Preserving `digDeeperMd` can leave old dig sections matched or orphaned against a new summary via [lib/html-doc/dig-merge.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/dig-merge.ts:97), but that is a known M2a boundary: dig is out of scope, orphans are explicit, and destroying the pointer forces re-spend. `digDeeperHtml: null` is sufficient for the stale rendered artifact. `sanitizeAdditiveVideo` still correctly nulls `digDeeperMd` for a receiver with no existing row.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4965:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:491) derives signals before the narrowed guard, and [lib/cloud-sync/backfill.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/backfill.ts:7) is pure over the record plus supplied MD body. The hoist can surface blob-read errors earlier, but that is the right behavior: baseline must not advance if Class-A evidence is unreadable. The both-have-MD conflict path still takes the WB-B1 skip at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:501). The one-sided hydration path writes the copied MD only after `transferClassA` lands, preserves unresolved corrections in Class-B baseline, and continues to report `needsRegen`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4969:No new Blocking, High, Medium, or Low defects found in the reviewed scope.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4971:Checked baseline advancement, durable-before-advertise ordering, manifest-after-commit, money-safety, `needsRegen` report-only behavior, RLS/no-service-role usage, and local-vs-Supabase null/deep-merge semantics. The accepted stale non-`summaryMd` artifact-pointer medium remains accepted and was not re-reported.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4977:Temporary mutation of H-R2-1 failed as expected, then restored; `lib/cloud-sync/sync-run.ts` has no remaining diff.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4979:**CONVERGED**
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:15:### WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:41:  write-only.** The `docVersionMajor: 0 / mdHash: null` placeholder is therefore inert; next run
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:47:### WB-H1 (High) — additive create could advertise `promoted` with no blob
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:51:throw on `summaryMd && mdBody == null` (158-160); strip a residual `artifacts.summaryMd` when no blob was
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:55:- **`summaryMd == null` path still correct.** `video.summaryMd` falsy → no throw, `wroteBlob` stays false →
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:60:  `sanitized.artifacts` is a whole-object replace, so `artifacts.summaryMd` lands verbatim. Cloud:
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:67:### WB-H2 (High) — two-sided transfer left stale rendered HTML
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:71:I traced whether a JSON `null` actually persists on each backend, as instructed:
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:75:  (`:18-21`) that removes only `updatedAt`/`summaryReady` — **it does not drop nulls**. PostgREST
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:76:  serializes the JSON null through. In `merge_video_data`
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:78:  `data || (p_fields - 'artifacts')`. Postgres `jsonb ||` **sets the key to JSON null** rather than
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:79:  dropping it (`'{"a":1}'::jsonb || '{"a":null}'::jsonb` → `{"a": null}`). Only `jsonb_strip_nulls`
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:80:  drops nulls, and it is used in `persist_summary`, not here. **Null is stored.** ✅
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:83:  so `summaryHtml: null` overwrites — then `writeIndex` → `JSON.stringify`, which preserves `null`
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:86:  `lib/html-doc/ensure.ts:54` (`else if (!video.summaryHtml)`) both branch on falsiness, so a JSON null
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:92:  | `summaryHtml` | null | null (314) | ✅ match |
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:93:  | `digDeeperHtml` | null | null (315) | ✅ match |
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:94:  | `digDeeperMd` | null | null (316) | ❌ **wrong on this path** — Part B H1 |
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:95:  | `artifacts.*` except `summaryMd` | dropped (113-115) | **not cleared** (319) | see Part B M1 |
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:98:  The commit comment "Matches `sanitizeAdditiveVideo`, which already nulls these" is the flawed premise:
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:107:### H1 (High) — `transferClassA` nulls `digDeeperMd`, orphaning the loser's paid dig-deeper doc
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:121:4. `transferClassA(cloudSide, localSide, …)` sends `digDeeperMd: null` in `completeTuple` (316) →
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:122:   `indexStore.updateVideoFields` shallow-spread → `index.json` now has `digDeeperMd: null`.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:134:Note this is a **regression introduced by the WB-H2 fix** — before `32a164c` the field was not sent at all.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:136:**Fix:** delete the `digDeeperMd: null` line (316). Keep `summaryHtml: null` and `digDeeperHtml: null` —
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:138:stale it, and `lib/html-doc/eligibility.ts:23` (`!!v.summaryMd && !v.digDeeperMd`) plus
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:143:### M1 (Medium) — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:148:`artifacts: { summaryMd: … }` **preserves** every other key already on the loser row. Any non-`summaryMd`
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:153:Today the practical blast radius is small — the artifacts map is dominated by `summaryMd`, and the
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:154:regenerable HTML is gated on the top-level `summaryHtml`, which *is* nulled. Hence Medium, not High. But
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:157:non-`summaryMd` keys explicitly or record the divergence as a deliberate, documented decision.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:159:### M2 (Medium) — the WB-B1 guard also blocks purely-additive (non-destructive) MD hydration
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:164:**Scenario:** cloud row has `summaryMd` + a promoted blob; the local row exists (so this is the two-sided
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:165:path, not the additive path) but has `summaryMd == null`; both sides carry a *backfilled* corrections
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:172:an MD body, i.e. `la.mdHash != null && ca.mdHash != null`), which preserves the WB-B1 fix's intent exactly
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:175:### L1 (Low) — the WB-H1 throw leaves a bare receiver slot; converges, but via a different code path
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:183:takes the two-sided path; `deriveClassASignals` on the bare row yields `mdHash: null`, so
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:185:(`winner … has no MD body to copy`) while the cloud blob is still unreadable — then heals cleanly once it
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:199:  trigger. The WB-B1 e2e test asserts `spendLedgerTotal()` is unchanged across the run.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:212:  cloud vs shallow spread on local; null persistence on both). The only surviving mismatch is M1 above.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:216:- **Idempotency.** Ran each new branch twice mentally; WB-B1 is additionally covered by an explicit
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:221:**NOT CONVERGED** — 1 new High (H1: `digDeeperMd: null` destroys the local loser's paid dig-deeper doc, a
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:222:regression introduced by the WB-H2 fix), plus 2 Mediums and 1 Low. Another round is required after H1 is
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:237:`lib/cloud-sync/backfill.ts:11`: `mdHash: mdBody != null ? mdHash(mdBody) : null`.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:238:The premise of the scenario is that the cloud blob is UNREADABLE, so `readMdBody` returns null and the
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:239:cloud side hashes to `null` as well. Both sides null → `reconcile-class-a.ts:21`
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:244:**High**, tracked as **H-R2-1**, and is being fixed by validating the MD body BEFORE
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:247:Lesson for round 3: the single-run WB-H1 e2e test passed while this bug was live. Assertions about
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:248:baseline/idempotency effects require running `runSync` TWICE — as the WB-B1 test already does.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:16:Round 1 found 1 Blocking + 2 High. They were fixed in commit `32a164c` (the branch HEAD). Your job has TWO explicit parts:
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:19:1. **WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy.** Fix: in `runSync` (`lib/cloud-sync/sync-run.ts`), when `merges.corrections.winner === 'equal' && merges.corrections.conflict`, skip the Class-A copy entirely, count `needsRegen`, and write `buildCorrectionsUnresolvedBaseline` (carries the PREVIOUS classA baseline, or an honest `{docVersionMajor:0, mdGeneratedAt:null, mdCorrectionsHash:null, mdHash:null}` placeholder on first sync). VERIFY: is the guard placed BEFORE every write path (including the companion transfer and any archived/delete handling)? Does the `continue` skip anything that MUST still run (delete-inference "seen" marking, report counters, companion, archived sync)? Is `report.archivedNotSynced` incremented correctly and only there? Does the placeholder baseline (docVersionMajor 0) cause a wrong decision anywhere that DOES read the Class-A baseline — confirm reconcileClassA truly never reads it.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:20:2. **WB-H1 (High) — additive create could advertise `promoted` with no blob.** Fix: throw when `video.summaryMd` is set but `mdBody == null`; strip `sanitized.artifacts.summaryMd` when no blob was written; post-write verify that the receiver row advertises `status==='promoted'` at the right key. VERIFY: does the throw leave PARTIAL state (a bare receiver slot created by `ensureReceiverSlot`, a staged blob orphaned) that a later run mishandles? Is the summary-less video (summaryMd == null) path still correct? Does the strict post-write assert produce false failures on the local store (shallow-merge) vs the cloud store (`merge_video_data` deep-merge) — a cross-backend semantic mismatch?
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:21:3. **WB-H2 (High) — two-sided transfer left stale rendered HTML.** Fix: `transferClassA` sets `summaryHtml/digDeeperHtml/digDeeperMd` to `null` in the update payload. VERIFY: does `merge_video_data` (migration 0021 / 0009) actually STORE a JSON null (invalidating) rather than treating null as "no change" and skipping the key — trace the RPC body. Same question for the local store's shallow merge. If null is dropped by either backend, the fix is cosmetic and the stale-HTML bug survives. Also: are there OTHER regenerable-cache fields that should have been nulled (compare against `sanitizeAdditiveVideo`'s strip list — any field it strips that transferClassA does not null is a gap), and does nulling `digDeeperMd` orphan or strand a dig-deeper blob / dig state?
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:29:- Cross-backend (local vs Supabase) semantic mismatches — the round-1 `transferClassA` promote-vs-put bug is the archetype; the null-invalidation question above is a live candidate sibling.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:38:For each finding: severity (Blocking/High/Medium/Low), `file:line`, the concrete failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. For Part A, state explicitly per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:56://    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:102:/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:103:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:104:  if (!video.summaryMd) return null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:105:  const buf = await blob.get(p, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:106:  return buf ? buf.toString('utf8') : null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:117:/** Read one video record (or null if absent) from a store's index. */
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:118:async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:120:  return idx.videos.find((v) => v.id === id) ?? null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:149: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:150: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:153:  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:154:  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:155:  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:156:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:158:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:173: *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:178:): Promise<{ position: number; serialNumber: number } | null> {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:181:  if (idx.videos.some((v) => v.id === video.id)) return null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:192:  video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:197:  if (video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:198:    // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:202:    if (mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:203:      throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:206:    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:221:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:223:    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:224:    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:225:    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:226:    delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:237:  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:238:  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:241:    const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:242:    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:243:      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:251:  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:311: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:317:  if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:321:  const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:346:    summaryMd: key,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:348:    mdGeneratedAt: wv.mdGeneratedAt ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:349:    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:357:    // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:361:    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:362:    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:363:    summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:364:    digDeeperHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:365:    digDeeperMd: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:368:    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:381:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:382:  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:415:  winnerSignals: ClassASignals, winnerMdHash: string | null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:429:/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:433: *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:441:      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:481:        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:484:          const presentIsLocal = lv != null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:494:              deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:512:        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:534:        let winnerMdHash: string | null = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:536:        let winnerSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:537:        let loserSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:590:lib/index-store.ts:19: *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:593:tests/e2e/html-doc.spec.ts:11://   - one video with summaryHtml: null (no docVersion)
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:594:tests/e2e/html-doc.spec.ts:13://   - one KO video with summaryHtml: null — used in KO round-trip test
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:595:tests/e2e/html-doc.spec.ts:38:    summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:602:tests/e2e/html-doc.spec.ts:193:  // Fixture: EN video with summaryHtml: null (not yet generated)
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:603:tests/e2e/html-doc.spec.ts:194:  const video = makeVideo({ id: 'vid-hd1', summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:604:tests/e2e/html-doc.spec.ts:230:  // Fixture: EN video with summaryHtml: null; transform stub returns error event
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:605:tests/e2e/html-doc.spec.ts:231:  const video = makeVideo({ id: 'vid-hd3', summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:606:tests/e2e/html-doc.spec.ts:253:  // The menu still shows "HTML doc" as a button (no file written — summaryHtml still null)
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:607:tests/e2e/html-doc.spec.ts:263:  // Fixture: KO video with summaryHtml: null
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:608:tests/e2e/html-doc.spec.ts:268:    summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:611:tests/e2e/batch-docs.spec.ts:10:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:612:tests/e2e/batch-docs.spec.ts:45:      videos: [v('a', { summaryHtml: 'a.html', docVersion: { major: 3, minor: 3 }, digDeeperMd: null })],
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:613:tests/components/VideoList.selection.test.tsx:19:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:614:tests/components/VideoList.selection.test.tsx:57:    v('a', { summaryHtml: null }),                                   // needs work
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:616:tests/components/VideoList.selection.test.tsx:68:  const videos = [v('a', { summaryHtml: null })];
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:648:lib/storage/local/local-metadata-store.ts:38:  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:670:tests/api/pdf-route.test.ts:25:    overallScore: 4, summaryMd: 'raw/275_x.md', summaryHtml: 'htmls/275_x.html',
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:691:lib/archive.ts:84:async function updateIndexIfKnown(principal: Principal, store: MetadataStore, videoId: string, fields: Partial<{ archived: boolean; summaryHtml: string | null }>): Promise<void> {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:692:lib/archive.ts:108:  await updateIndexIfKnown(principal, store, videoId, { archived: true, summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:693:lib/archive.ts:124:  await updateIndexIfKnown(principal, store, videoId, { archived: false, summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:697:tests/components/AskGeminiMenuItem.test.tsx:12:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z', ...extra,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:704:lib/cloud-sync/sync-run.ts:109:  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:705:lib/cloud-sync/sync-run.ts:110:  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:706:lib/cloud-sync/sync-run.ts:111:  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:717:lib/cloud-sync/sync-run.ts:312:    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:718:lib/cloud-sync/sync-run.ts:313:    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:719:lib/cloud-sync/sync-run.ts:314:    summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:720:lib/cloud-sync/sync-run.ts:315:    digDeeperHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:721:lib/cloud-sync/sync-run.ts:316:    digDeeperMd: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:749:tests/api/regenerate.test.ts:164:      expect.objectContaining({ summaryHtml: null }),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:750:tests/api/regenerate.test.ts:168:  it('includes summaryHtml: null in the JSON response on success', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:751:tests/api/regenerate.test.ts:172:    expect(body).toEqual(expect.objectContaining({ summaryHtml: null }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:752:lib/paths/assert-within.ts:10: * Use this before every read of an index-supplied relative path (summaryMd, digDeeperMd,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:763:tests/components/VideoMenu.test.tsx:73:  expect(screen.queryByText(/Save summary PDF/i)).toBeNull(); // summaryMd only, no summaryHtml
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:772:lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:773:lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:780:lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:781:lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:782:lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:783:tests/api/dig-state.test.ts:33:    digDeeperMd: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:784:tests/api/dig-state.test.ts:91:it('returns { sectionIds: [] } when digDeeperMd is null on the video', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:785:tests/api/dig-state.test.ts:92:  writeIndex(video({ digDeeperMd: null }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:791:tests/components/CorrectionsPanel.test.tsx:118:    it('calls onSuccess with tldr, takeaways, corrections, and summaryHtml:null on success', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:792:tests/components/CorrectionsPanel.test.tsx:125:        summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:797:tests/api/html-doc-pipeline.test.ts:60:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:798:tests/api/html-doc-pipeline.test.ts:106:  expect(before.status).toBe(404); // summaryHtml is null until generation runs
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:827:tests/api/dig-post.test.ts:99:  digDeeperMd: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:828:tests/api/dig-post.test.ts:100:  digDeeperHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:834:tests/integration/annotations-rpc.test.ts:144:  // (f) an existing merge_video_data write of summaryHtml:null still stores null
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:836:tests/integration/annotations-rpc.test.ts:146:  it('merge_video_data (unchanged) still stores an explicit null for summaryHtml', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:837:tests/integration/annotations-rpc.test.ts:153:    await store.updateVideoFields(p, videoId, { summaryHtml: null } as any);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:875:tests/integration/cloud-sync/e2e.int.test.ts:268:  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:879:tests/integration/cloud-sync/e2e.int.test.ts:280:    expect(local?.summaryHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:880:tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:884:tests/integration/cloud-sync/e2e.int.test.ts:455:  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:885:tests/integration/cloud-sync/e2e.int.test.ts:456:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:887:tests/integration/cloud-sync/e2e.int.test.ts:472:    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:894:tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:896:tests/api/html-serve.test.ts:25:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z', ...extra,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:902:tests/api/html-serve.test.ts:68:  writeIndex(video({ summaryHtml: null }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:906:tests/api/html-serve.test.ts:166:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:907:tests/api/html-serve.test.ts:176:it('dig-deeper B2: digDeeperMd null → skeleton 200 (all summary sections rendered)', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:908:tests/api/html-serve.test.ts:178:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:909:tests/api/html-serve.test.ts:189:  writeIndex(video({ summaryMd: 'wiki/nonexistent.md', digDeeperMd: null }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:910:tests/api/html-serve.test.ts:199:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:914:tests/api/html-serve.test.ts:244:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:917:tests/api/html-serve.test.ts:271:  // summaryMd is safe; digDeeperMd escapes → companion assertWithin fires → 400.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:920:tests/api/html-serve.test.ts:303:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:921:tests/api/html-serve.test.ts:314:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:922:tests/api/html-serve.test.ts:328:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:923:tests/api/html-serve.test.ts:343:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:924:tests/api/html-serve.test.ts:353:    writeIndex(video({ summaryHtml: 'htmls/missing.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:925:tests/api/html-serve.test.ts:361:  it('B6: null summaryHtml → 404', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:926:tests/api/html-serve.test.ts:362:    writeIndex(video({ summaryHtml: null }));
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:938:tests/integration/worker-persistence-rpcs.test.ts:59:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:940:tests/integration/worker-persistence-rpcs.test.ts:67:test('persist_summary preserves a sibling artifact kind (deepDiveMd) across a summaryMd status write', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:941:tests/integration/worker-persistence-rpcs.test.ts:71:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:945:tests/integration/worker-persistence-rpcs.test.ts:99:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'promoted' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:946:tests/integration/worker-persistence-rpcs.test.ts:100:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:948:tests/integration/worker-persistence-rpcs.test.ts:109:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:951:tests/integration/worker-persistence-rpcs.test.ts:130:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3 }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:955:tests/integration/worker-persistence-rpcs.test.ts:141:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3, ratings: { usefulness: 5 } }, p_artifact_status: 'promoted' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:960:tests/integration/worker-persistence-rpcs.test.ts:172:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_old.md' }, p_artifact_status: 'promoted' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:961:tests/integration/worker-persistence-rpcs.test.ts:175:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_new.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:981:tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:985:tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:990:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1004:tests/lib/html-doc/eligibility.test.ts:10:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1006:tests/lib/html-doc/eligibility.test.ts:21:    expect(summaryNeedsWork(v({ summaryHtml: null }))).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1009:tests/lib/html-doc/eligibility.test.ts:30:    expect(summaryNeedsWork(v({ summaryMd: null, summaryHtml: null }))).toBe(false);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1010:tests/lib/html-doc/eligibility.test.ts:36:    expect(videoNeedsBatchWork(v({ summaryHtml: null }), 'summary')).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1012:tests/lib/html-doc/eligibility.test.ts:40:    expect(videoNeedsBatchWork(v({ summaryHtml: 'h.html', docVersion: { major: 3, minor: 3 }, digDeeperMd: null }), 'summary-dig')).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1014:tests/lib/html-doc/eligibility.test.ts:42:    expect(videoNeedsBatchWork(v({ summaryMd: null, summaryHtml: null, digDeeperMd: null }), 'summary-dig')).toBe(false); // no summary → nothing
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1017:tests/lib/serial-invariant.test.ts:58:    const v = makeVideo({ serialNumber: 7, summaryMd: null, summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1020:tests/lib/serial-invariant.test.ts:70:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md', digDeeperMd: 'x-dig-deeper.md' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1028:tests/lib/html-doc/build-doc-html.test.ts:16:    overallScore: 4, summaryMd: 'a.md', summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1032:tests/lib/html-doc/build-doc-html.test.ts:36:    const r = await buildDocHtml(video({ summaryHtml: null }), dir, 'summary');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1042:tests/lib/html-doc/build-doc-html.test.ts:71:    const r = await buildDocHtml(video({ summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1043:tests/lib/html-doc/generate.test.ts:65:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1056:tests/lib/html-doc/rerender.test.ts:118:    writeIndex([baseVideo({ summaryHtml: null })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1057:tests/lib/html-doc/rerender.test.ts:181:    // video B: summaryMd + summaryHtml set but NO model → skipped-no-model
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1058:tests/lib/html-doc/rerender.test.ts:183:    const vidB = baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1059:tests/lib/html-doc/rerender.test.ts:198:    const vidC = baseVideo({ id: 'vidC', summaryMd: null, summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1060:tests/lib/html-doc/rerender.test.ts:211:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1061:tests/lib/html-doc/rerender.test.ts:224:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1063:tests/lib/html-doc/ensure.test.ts:49:    withVideo({ docVersion: { major: 3, minor: 3 }, summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1070:tests/lib/html-doc/batch.test.ts:33:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1071:tests/lib/html-doc/batch.test.ts:51:    indexWith([v('a', { summaryHtml: null }), v('b', { summaryHtml: 'b.html', docVersion: { major: 3, minor: 3 } })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1073:tests/lib/html-doc/batch.test.ts:130:    indexWith([v('x', { summaryHtml: null, summaryMd: 'x.md', digDeeperMd: null })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1074:tests/lib/html-doc/batch.test.ts:143:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1075:tests/lib/html-doc/batch.test.ts:154:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1076:tests/lib/html-doc/batch.test.ts:164:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md' })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1077:tests/lib/html-doc/batch.test.ts:173:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1078:tests/lib/html-doc/batch.test.ts:185:      v('bad', { summaryHtml: 'bad.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'bad.md', digDeeperMd: null }),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1079:tests/lib/html-doc/batch.test.ts:186:      v('ok', { summaryHtml: 'ok.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'ok.md', digDeeperMd: null }),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1081:tests/lib/ask-gemini.test.ts:13:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z', ...extra,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1082:tests/lib/index-store.test.ts:162:    updateVideoFields(dir, 'vid333333333', { summaryMd: 'vid333333333.md', digDeeperMd: 'vid333333333-dig-deeper.md' });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1091:HEAD is `32a164c`; the worktree has unrelated local modifications, so I’ll avoid treating those as branch changes. I’ve located the rewritten hot path; next I’m tracing the storage backends because the null and post-write semantics decide whether the fixes are real.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1132:    38	  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1174:    80	  // when currently absent/null in the JSON index; a no-op otherwise.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1271:   105	 *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1272:   106	 *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1275:   109	  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1276:   110	  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1277:   111	  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1278:   112	  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1280:   114	    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1295:   129	 *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1300:   134	): Promise<{ position: number; serialNumber: number } | null> {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1303:   137	  if (idx.videos.some((v) => v.id === video.id)) return null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1314:   148	  video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1319:   153	  if (video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1320:   154	    // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1324:   158	    if (mdBody == null) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1325:   159	      throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1328:   162	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1343:   177	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1345:   179	    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1346:   180	    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1347:   181	    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1348:   182	    delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1359:   193	  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1360:   194	  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1363:   197	    const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1364:   198	    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1365:   199	      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1373:   207	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1433:   267	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1439:   273	  if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1443:   277	  const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1463:   297	    summaryMd: key,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1465:   299	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1466:   300	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1474:   308	    // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1478:   312	    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1479:   313	    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1480:   314	    summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1481:   315	    digDeeperHtml: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1482:   316	    digDeeperMd: null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1485:   319	    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1498:   332	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1499:   333	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1532:   366	  winnerSignals: ClassASignals, winnerMdHash: string | null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1546:   380	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1550:   384	 *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1558:   392	      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1598:   432	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1601:   435	          const presentIsLocal = lv != null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1611:   445	              deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1629:   463	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1651:   485	        let winnerMdHash: string | null = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1653:   487	        let winnerSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1654:   488	        let loserSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1802:   112	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1803:   113	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1810:   120	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1823:   133	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1826:   136	           || jsonb_build_object('summaryMd', jsonb_build_object(
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1827:   137	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1833:   143	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1835:   145	                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1836:   146	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1860:    11	// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1863:    14	// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1902:    53	          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1903:    54	            .artifacts?.summaryMd?.status === 'promoted',
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1927:    78	        playlist_title: meta.playlistTitle ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2051:   202	  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2067:   218	      .is('playlist_title', null)
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2101:   117	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2102:   118	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2109:   125	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2120:   136	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2123:   139	           || jsonb_build_object('summaryMd', jsonb_build_object(
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2124:   140	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2130:   146	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2132:   148	                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2133:   149	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2218:    19	 *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2307:   108	    fs.writeFileSync(tmpPath, JSON.stringify(index, null, 2), 'utf-8');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2332:     9	const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2340:    17	  const lHas = local.mdHash != null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2341:    18	  const cHas = cloud.mdHash != null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2354:    31	  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2377:/bin/bash -lc 'rg -n "buildCorrectionsUnresolvedBaseline|correctionsUnresolved|additive: summaryMd present|did not advertise promoted|summaryHtml: null|digDeeperMd: null|digDeeperHtml: null|archivedNotSynced|needsRegen" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2388:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2401:tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2402:tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2403:tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2406:The backend trace is favorable for WB-H2 so far: `merge_video_data` uses `data || p_fields`, which preserves JSON nulls, and the local path writes `null` through the JSON index. I’m now looking for behavior holes around additive failures and baseline advancement rather than just matching comments.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2411:   361	    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2438:   388	  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2443:   393	  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2483:   433	  // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2484:   434	  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2485:   435	  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2488:   438	  it('WB-H1: additive create with a promoted summaryMd but no blob throws; no promoted row, no baseline', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2490:   440	    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2496:   446	    // The local receiver must not advertise a promoted summaryMd (bare slot at most; no blob copied).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2498:   448	    expect(artifactsOf(local)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2503:   453	  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2505:   455	  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2543:/bin/bash -lc 'rg -n "summaryMd present but MD body unreadable|did not advertise promoted|stale HTML|digDeeperHtml|summary-less|summaryMd == null|bare receiver|slot|promoted summaryMd" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2546:tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2549:tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2550:tests/integration/cloud-sync/e2e.int.test.ts:438:  it('WB-H1: additive create with a promoted summaryMd but no blob throws; no promoted row, no baseline', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2551:tests/integration/cloud-sync/e2e.int.test.ts:446:    // The local receiver must not advertise a promoted summaryMd (bare slot at most; no blob copied).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2565:supabase/migrations/0012_serve_model_charge.sql:44:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2567:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:117:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2568:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:118:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2573:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:140:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2574:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:146:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2575:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:148:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2576:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:149:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2578:supabase/migrations/0017_share_token_id_return.sql:23:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2579:supabase/migrations/0020_reservation_release.sql:204:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2585:supabase/migrations/0021_cloud_sync_signals.sql:112:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2586:supabase/migrations/0021_cloud_sync_signals.sql:113:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2591:supabase/migrations/0021_cloud_sync_signals.sql:137:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2592:supabase/migrations/0021_cloud_sync_signals.sql:143:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2593:supabase/migrations/0021_cloud_sync_signals.sql:145:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2594:supabase/migrations/0021_cloud_sync_signals.sql:146:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2615:supabase/migrations/0014_serve_owner_budget.sql:38:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2616:supabase/migrations/0013_share_tokens.sql:36:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2627:     5	// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2628:     6	// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2629:     7	export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2630:     8	  const hasReal = video.mdGeneratedAt != null;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2632:    10	    summaryMdKey: video.summaryMd ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2633:    11	    mdHash: mdBody != null ? mdHash(mdBody) : null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2635:    13	    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2636:    14	    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2698:   257	    const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2709:   268	  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2721:   280	    expect(local?.summaryHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2722:   281	    expect(local?.digDeeperHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2752:   311	    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2759:   318	    expect(local?.summaryMd == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2769:   328	    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2777:   453	  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2779:   455	  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2780:   456	  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2796:   472	    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2811:types/index.ts:82:  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2813:lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2814:lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2816:lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2817:lib/cloud-sync/sync-run.ts:177:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2819:lib/cloud-sync/sync-run.ts:182:    delete sanitized.artifacts.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2821:lib/cloud-sync/sync-run.ts:197:    const art = (rec as any).artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2822:lib/cloud-sync/sync-run.ts:319:    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2971:    56	  summaryMd: z.string().nullable(),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2972:    57	  summaryHtml: z.string().nullable().optional(),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2973:    58	  digDeeperMd: z.string().nullable().optional(),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2974:    59	  digDeeperHtml: z.string().nullable().optional(),
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2997:    82	  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3073:tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3074:tests/integration/cloud-sync/e2e.int.test.ts:388:  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3100:lib/cloud-sync/sync-run.ts:106: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3102:lib/cloud-sync/sync-run.ts:267: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3112:lib/cloud-sync/sync-run.ts:380:/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3114:lib/cloud-sync/sync-run.ts:384: *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3121:WB-B1: GENUINELY FIXED. The guard is before Class-A signal derivation, transfer, companion transfer, normal archived counter, and normal baseline advance in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:471). It still logs Class-B conflicts before the guard, increments `needsRegen`, increments `archivedNotSynced` only for archived divergence, writes a baseline so delete inference has seen the video, then continues. `reconcileClassA` takes only live `ClassASignals`, not manifest Class-A baselines, so the `{ docVersionMajor: 0, mdHash: null }` placeholder is not read by the Class-A decision code.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3123:WB-H1: INCOMPLETE. The promoted-without-blob advertisement is fixed for the first failing run: unreadable `summaryMd` throws before `upsertVideo`, and the post-write promoted artifact assertion is valid for both local replacement and Supabase direct row update. However, the throw happens after `ensureReceiverSlot`, leaving a bare receiver row that changes the next run’s branch classification. Finding below.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3125:WB-H2: GENUINELY FIXED. `transferClassA` writes `summaryHtml`, `digDeeperHtml`, and `digDeeperMd` as JSON/null fields in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:314). Supabase `merge_video_data` preserves those nulls via `data || (p_fields - 'artifacts')` in [0021_cloud_sync_signals.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:79); local shallow merge also persists nulls through `updateVideoFields`. The null list matches `sanitizeAdditiveVideo`’s regenerable top-level cache fields, and clearing `digDeeperMd` is consistent with M2a not syncing dig/deep-dive assets.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3132:Scenario: cloud-only video advertises `summaryMd`, but the MD blob is absent. Run 1 calls `ensureReceiverSlot` before the unreadable-body check, creating a bare local row, then throws at line 159 and does not write a baseline. Run 2 now sees both sides present, not an additive create. Since both MD body reads are null, `reconcileClassA` returns `skip`; `runSync` writes a manifest baseline at line 512 even though no receiver summary was ever durably copied and the source still advertises an unreadable summary. This masks the original corruption after one report and turns a failed additive copy into a false “seen/agreed no-MD” state.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3134:Fix: validate `video.summaryMd`/`mdBody` before `ensureReceiverSlot`, or wrap `copyAdditiveVideo` in rollback that deletes the claimed receiver slot and any staged/final blob if any later step fails. The baseline should not be able to advance from a bare receiver slot created by a failed additive copy.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3145:NOT CONVERGED.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3150:WB-B1: GENUINELY FIXED. The guard is before Class-A signal derivation, transfer, companion transfer, normal archived counter, and normal baseline advance in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:471). It still logs Class-B conflicts before the guard, increments `needsRegen`, increments `archivedNotSynced` only for archived divergence, writes a baseline so delete inference has seen the video, then continues. `reconcileClassA` takes only live `ClassASignals`, not manifest Class-A baselines, so the `{ docVersionMajor: 0, mdHash: null }` placeholder is not read by the Class-A decision code.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3152:WB-H1: INCOMPLETE. The promoted-without-blob advertisement is fixed for the first failing run: unreadable `summaryMd` throws before `upsertVideo`, and the post-write promoted artifact assertion is valid for both local replacement and Supabase direct row update. However, the throw happens after `ensureReceiverSlot`, leaving a bare receiver row that changes the next run’s branch classification. Finding below.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3154:WB-H2: GENUINELY FIXED. `transferClassA` writes `summaryHtml`, `digDeeperHtml`, and `digDeeperMd` as JSON/null fields in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:314). Supabase `merge_video_data` preserves those nulls via `data || (p_fields - 'artifacts')` in [0021_cloud_sync_signals.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:79); local shallow merge also persists nulls through `updateVideoFields`. The null list matches `sanitizeAdditiveVideo`’s regenerable top-level cache fields, and clearing `digDeeperMd` is consistent with M2a not syncing dig/deep-dive assets.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3161:Scenario: cloud-only video advertises `summaryMd`, but the MD blob is absent. Run 1 calls `ensureReceiverSlot` before the unreadable-body check, creating a bare local row, then throws at line 159 and does not write a baseline. Run 2 now sees both sides present, not an additive create. Since both MD body reads are null, `reconcileClassA` returns `skip`; `runSync` writes a manifest baseline at line 512 even though no receiver summary was ever durably copied and the source still advertises an unreadable summary. This masks the original corruption after one report and turns a failed additive copy into a false “seen/agreed no-MD” state.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3163:Fix: validate `video.summaryMd`/`mdBody` before `ensureReceiverSlot`, or wrap `copyAdditiveVideo` in rollback that deletes the claimed receiver slot and any staged/final blob if any later step fails. The baseline should not be able to advance from a bare receiver slot created by a failed additive copy.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3174:NOT CONVERGED.
docs/reviews/whole-branch-cloud-sync-codex.md:27:2. **mdHash is MD-BODY-only and CONSISTENT across tasks.** T1 canonicalizes (LF + one trailing newline + NFC). T4 stamps `sourceMdHash = mdHash(body)` at generate.ts + serve-doc.ts. T5 `deriveClassASignals` hashes the mdBody param. T8 `decideCompanion` compares `sourceMdHash === winnerMdHash`. T12 hashes bodies read via BlobStore. Verify NO path hashes `video.summaryMd` (the KEY/filename) instead of the body — a single key-hash anywhere breaks companion/reconcile equality.
docs/reviews/whole-branch-cloud-sync-codex.md:28:3. **ATOMICITY.** Manifest baseline written ONLY after the receiver tuple verifies durable. Blob durable BEFORE the record advertises `artifacts.summaryMd.status='promoted'`. Additive create verifies the receiver row exists (readIndex) before the baseline (cloud upsertVideo silently no-ops on an absent row → ensureReceiverSlot creates it). transferClassA's fix (put-overwrite the final key with verified staged bytes, then updateVideoFields) preserves durable-before-finalize. Crash before verify leaves the baseline unadvanced (re-run heals).
docs/reviews/whole-branch-cloud-sync-codex.md:30:5. **RECONCILE ORDER + correctness.** Class B FIRST (→ reconciledCorrectionsHash) THEN Class A. reconcileClassA priority: corrections-current > format(higher docVersionMajor, never downgrade) > recency; the mdHash-equal skip is EXACTLY (both-current) OR (both-stale + same-major), else fall through. One-sided videos resolved by the presence branch, never reach `deriveHumanSnapshot(null)` (NPE).
docs/reviews/whole-branch-cloud-sync-codex.md:33:8. **FORWARD-TOLERANCE.** New VideoSchema fields `.optional()`; ModelEnvelopeSchema dropped `.strict()` (an old reader must not null on a new-writer envelope).
docs/reviews/whole-branch-cloud-sync-codex.md:40:For each NEW finding: severity (Blocking/High/Medium/Low), file:line, the concrete cross-task failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. Triage the accepted-minors list: any that must be fixed before merge vs defer. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-codex.md:115:/bin/bash -lc 'rg -n "runSync|copyAdditiveVideo|transferClassA|applyClassBWinners|sanitizeAdditiveVideo|sourceMdHash|mdHash|summaryMd|spend_ledger|enqueue|producer|service_role|SERVICE|persist_summary|merge_video_data|update_video_annotations|claimVideoSlot|ensureReceiverSlot|buildBaseline|deriveHumanSnapshot|deriveClassASignals|decideCompanion|reconciledCorrectionsHash|promoted|updateVideoFields|upsertVideo|readIndex" lib supabase scripts tests types docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-codex.md:129:types/index.ts:56:  summaryMd: z.string().nullable(),
docs/reviews/whole-branch-cloud-sync-codex.md:131:types/index.ts:82:  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
docs/reviews/whole-branch-cloud-sync-codex.md:150:docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
docs/reviews/whole-branch-cloud-sync-codex.md:172:tests/components/VideoList.selection.test.tsx:18:    overallScore: 3, summaryMd: `${id}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:173:tests/components/VideoList.selection.test.tsx:49:it('CA2: a row with no summaryMd has a disabled checkbox', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:174:tests/components/VideoList.selection.test.tsx:50:  renderList({ ...baseProps, videos: [v('a', { summaryMd: null })] });
docs/reviews/whole-branch-cloud-sync-codex.md:175:tests/components/VideoList.selection.test.tsx:59:    v('c', { summaryMd: null }),                                     // not selectable
docs/reviews/whole-branch-cloud-sync-codex.md:176:tests/e2e/html-doc.spec.ts:37:    summaryMd: 'deep-dive-into-llms.md',
docs/reviews/whole-branch-cloud-sync-codex.md:177:lib/serial-migrate.ts:7:  'summaryMd',
docs/reviews/whole-branch-cloud-sync-codex.md:178:lib/serial-migrate.ts:33:    if (vid.summaryMd) {
docs/reviews/whole-branch-cloud-sync-codex.md:179:lib/serial-migrate.ts:34:      const base = vid.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:181:tests/components/VideoRow.test.tsx:44:  summaryMd: 'summary.md',
docs/reviews/whole-branch-cloud-sync-codex.md:182:tests/components/VideoRow.test.tsx:89:    renderRow({ summaryMd: 'base.md' }, { onResummarize });
docs/reviews/whole-branch-cloud-sync-codex.md:183:tests/components/VideoRow.test.tsx:267:        // summaryMd is 'summary.md' → strip .md → 'summary'
docs/reviews/whole-branch-cloud-sync-codex.md:184:scripts/rerender-html.ts:22:      console.log(`  skipped-drift:    ${d.summaryMd} (sections [${d.mdSections?.join(', ')}] ≠ model [${d.modelSections?.join(', ')}] — regenerate)`);
docs/reviews/whole-branch-cloud-sync-codex.md:185:scripts/rerender-html.ts:24:      console.log(`  skipped-no-model: ${d.summaryMd} (regenerate once to enable)`);
docs/reviews/whole-branch-cloud-sync-codex.md:186:scripts/rerender-html.ts:26:      console.log(`  skipped-no-md:    ${d.summaryMd} (.md missing on disk)`);
docs/reviews/whole-branch-cloud-sync-codex.md:187:scripts/rerender-html.ts:28:      console.log(`  skipped-unparse:  ${d.summaryMd} (.md has no sections — regenerate)`);
docs/reviews/whole-branch-cloud-sync-codex.md:188:scripts/rerender-html.ts:30:      console.log(`  error:            ${d.summaryMd} (${d.message})`);
docs/reviews/whole-branch-cloud-sync-codex.md:189:tests/e2e/dig-deeper.spec.ts:415:    const summaryMdRel = `${baseName}.md`;
docs/reviews/whole-branch-cloud-sync-codex.md:190:tests/e2e/dig-deeper.spec.ts:431:        summaryMd: summaryMdRel,
docs/reviews/whole-branch-cloud-sync-codex.md:191:tests/e2e/dig-deeper.spec.ts:440:    const summaryMd = [
docs/reviews/whole-branch-cloud-sync-codex.md:192:tests/e2e/dig-deeper.spec.ts:453:    fs.writeFileSync(path.join(tmpDir, summaryMdRel), summaryMd, 'utf-8');
docs/reviews/whole-branch-cloud-sync-codex.md:193:tests/e2e/dig-deeper.spec.ts:459:      sourceMd: summaryMdRel,
docs/reviews/whole-branch-cloud-sync-codex.md:194:tests/e2e/dig-deeper.spec.ts:477:    const parsed = parseMd(summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:195:tests/e2e/dig-deeper.spec.ts:478:    parsed.sourceMd = summaryMdRel;
docs/reviews/whole-branch-cloud-sync-codex.md:196:tests/components/PageIntegration.test.tsx:63:    summaryMd: 'summary.md',
docs/reviews/whole-branch-cloud-sync-codex.md:198:lib/share/serve.ts:44:  const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
docs/reviews/whole-branch-cloud-sync-codex.md:199:lib/share/serve.ts:45:    .artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:201:lib/share/serve.ts:47:  const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:204:tests/components/cloud-app.test.tsx:53:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:205:scripts/fix-duplicate-summaries.ts:7: * For each video in the index whose summaryMd ends with -2.md:
docs/reviews/whole-branch-cloud-sync-codex.md:206:scripts/fix-duplicate-summaries.ts:9: *   2. Update index entry: summaryMd → canonical name
docs/reviews/whole-branch-cloud-sync-codex.md:207:scripts/fix-duplicate-summaries.ts:20:  summaryMd?: string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:210:scripts/fix-duplicate-summaries.ts:53:    for (const [field, ext] of [['summaryMd', 'md']] as const) {
docs/reviews/whole-branch-cloud-sync-codex.md:214:tests/integration/delete-playlist-route.test.ts:61:    p_job_kind: kind, p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:217:tests/e2e/playlist-viewer.spec.ts:28:    summaryMd: 'summary',
docs/reviews/whole-branch-cloud-sync-codex.md:218:tests/e2e/playlist-viewer.spec.ts:262:    // summaryMd is 'summary' (no .md) → file param is 'summary', not the raw video id
docs/reviews/whole-branch-cloud-sync-codex.md:219:tests/e2e/playlist-viewer.spec.ts:337:      summaryMd: 'summary.md',
docs/reviews/whole-branch-cloud-sync-codex.md:220:tests/e2e/playlist-viewer.spec.ts:370:      summaryMd: 'summary.md',
docs/reviews/whole-branch-cloud-sync-codex.md:221:tests/e2e/playlist-viewer.spec.ts:398:      summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:222:tests/e2e/playlist-viewer.spec.ts:482:  test('backfill banner visible when videos have summaryMd but no tldr', async ({ page }) => {
docs/reviews/whole-branch-cloud-sync-codex.md:223:tests/e2e/playlist-viewer.spec.ts:483:    const video = makeVideo({ id: 'vid-bf1', summaryMd: 'summary.md' /* no tldr */ });
docs/reviews/whole-branch-cloud-sync-codex.md:224:tests/e2e/playlist-viewer.spec.ts:515:    const video = makeVideo({ id: 'vid-bf3', summaryMd: 'summary.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:225:tests/e2e/playlist-viewer.spec.ts:533:    const video = makeVideo({ id: 'vid-bf4', title: 'RAG Video', summaryMd: 'summary.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:226:tests/e2e/playlist-viewer.spec.ts:558:    const video = makeVideo({ id: 'vid-bf5', summaryMd: 'summary.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:227:tests/e2e/playlist-viewer.spec.ts:598:    const video = makeVideo({ id: 'vid-bf6', summaryMd: 'summary.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:228:tests/e2e/playlist-viewer.spec.ts:629:    const video = makeVideo({ id: 'vid-bf7', summaryMd: 'summary.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:238:tests/integration/blob-store.test.ts:36:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:240:tests/integration/blob-store.test.ts:163:test('writeArtifact: blob readable at final key + metadata artifacts.summaryMd.status === promoted', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:244:tests/integration/blob-store.test.ts:182:    kind: 'summaryMd',
docs/reviews/whole-branch-cloud-sync-codex.md:247:tests/integration/blob-store.test.ts:195:  expect(video.artifacts?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:248:tests/integration/blob-store.test.ts:196:  expect(video.artifacts?.summaryMd?.key).toBe('summaries/vidAAAAAAAA.md');
docs/reviews/whole-branch-cloud-sync-codex.md:249:tests/integration/blob-store.test.ts:205:  // summaryMd is a SOURCE kind → must not regenerate; must markRepair.
docs/reviews/whole-branch-cloud-sync-codex.md:250:tests/integration/blob-store.test.ts:207:    kind: 'summaryMd',
docs/reviews/whole-branch-cloud-sync-codex.md:252:tests/integration/metadata-store.test.ts:32:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:276:tests/integration/metadata-store.test.ts:181:    // write summaryMd artifact kind
docs/reviews/whole-branch-cloud-sync-codex.md:278:tests/integration/metadata-store.test.ts:183:      artifacts: { summaryMd: { key: 'a.md', status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:279:tests/integration/metadata-store.test.ts:185:    // write html artifact kind — must NOT clobber summaryMd
docs/reviews/whole-branch-cloud-sync-codex.md:284:tests/integration/metadata-store.test.ts:192:    expect(v.artifacts.summaryMd).toEqual({ key: 'a.md', status: 'promoted' });
docs/reviews/whole-branch-cloud-sync-codex.md:330:tests/integration/cancel-playlist-jobs.test.ts:15:    p_job_kind: jobKind, p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:348:tests/e2e/pdf-export.spec.ts:21:    summaryMd: 'deep-dive-into-llms.md',
docs/reviews/whole-branch-cloud-sync-codex.md:404:supabase/migrations/0012_serve_model_charge.sql:44:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:417:tests/integration/producer-roundtrip.test.ts:29:  const ctx = { ownerId: userId, enqueueIp: null };
docs/reviews/whole-branch-cloud-sync-codex.md:423:tests/integration/share-route.test.ts:228:  it('B12: token pointing at an un-promoted (committed) doc → 404', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:424:tests/integration/share-route.test.ts:247:  it('B13b: MD blob missing behind a promoted status → 404 (never 500)', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:425:tests/integration/share-route.test.ts:291:  it('B10b: video un-promoted (artifacts.summaryMd.status flipped away from promoted) between the initial resolve and the mandatory pre-response re-check → 404', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:427:tests/integration/share-route.test.ts:304:      // (D14/B10b) — the re-check reads `videos.data.artifacts.summaryMd.status` fresh, so this
docs/reviews/whole-branch-cloud-sync-codex.md:428:tests/integration/share-route.test.ts:312:        artifacts: { summaryMd: { key: `${base}.md`, status: 'committed' } },
docs/reviews/whole-branch-cloud-sync-codex.md:433:tests/integration/share-route.test.ts:505:        id: videoId, title: hostileTitle, language: 'en', summaryMd: `${base}.md`, docVersion: 1,
docs/reviews/whole-branch-cloud-sync-codex.md:434:tests/integration/share-route.test.ts:506:        artifacts: { summaryMd: { key: `${base}.md`, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:440:tests/e2e/batch-docs.spec.ts:9:    overallScore: 3, summaryMd: `${id}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:441:tests/e2e/batch-docs.spec.ts:60:  // Individually select video 'a' (its row checkbox is always enabled since it has summaryMd).
docs/reviews/whole-branch-cloud-sync-codex.md:459:supabase/migrations/0021_cloud_sync_signals.sql:112:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-codex.md:460:supabase/migrations/0021_cloud_sync_signals.sql:113:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-codex.md:461:supabase/migrations/0021_cloud_sync_signals.sql:133:      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
docs/reviews/whole-branch-cloud-sync-codex.md:462:supabase/migrations/0021_cloud_sync_signals.sql:136:           || jsonb_build_object('summaryMd', jsonb_build_object(
docs/reviews/whole-branch-cloud-sync-codex.md:463:supabase/migrations/0021_cloud_sync_signals.sql:137:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-codex.md:466:supabase/migrations/0021_cloud_sync_signals.sql:143:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:467:supabase/migrations/0021_cloud_sync_signals.sql:145:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-codex.md:468:supabase/migrations/0021_cloud_sync_signals.sql:146:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-codex.md:482:tests/components/AskGeminiMenuItem.test.tsx:11:    overallScore: 4, summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:485:tests/integration/jobs-poll-banner.test.ts:18:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:493:tests/components/VideoList.test.tsx:46:  summaryMd: 'summary.md',
docs/reviews/whole-branch-cloud-sync-codex.md:501:tests/components/video-menu-dig.test.tsx:15:  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:506:tests/integration/enqueue-dig.test.ts:15:    p_job_kind: 'dig', p_job_version: 'dig-9', p_payload: { durationSeconds: 600 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:520:tests/integration/job-queue-schema.test.ts:86:    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:523:tests/components/VideoMenu.test.tsx:16:  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:524:tests/components/VideoMenu.test.tsx:65:  renderMenu(<VideoMenu {...props} video={{ ...base, summaryMd: null } as any} />);
docs/reviews/whole-branch-cloud-sync-codex.md:525:tests/components/VideoMenu.test.tsx:73:  expect(screen.queryByText(/Save summary PDF/i)).toBeNull(); // summaryMd only, no summaryHtml
docs/reviews/whole-branch-cloud-sync-codex.md:540:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:117:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-codex.md:541:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:118:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-codex.md:542:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:136:      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
docs/reviews/whole-branch-cloud-sync-codex.md:543:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:139:           || jsonb_build_object('summaryMd', jsonb_build_object(
docs/reviews/whole-branch-cloud-sync-codex.md:544:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:140:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-codex.md:547:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:146:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:548:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:148:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-codex.md:549:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:149:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-codex.md:557:supabase/migrations/0014_serve_owner_budget.sql:38:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:583:tests/integration/cloud-sync/sync-run.int.test.ts:41:    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
docs/reviews/whole-branch-cloud-sync-codex.md:584:tests/integration/cloud-sync/sync-run.int.test.ts:42:    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
docs/reviews/whole-branch-cloud-sync-codex.md:644:tests/integration/job-queue-store.test.ts:29:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { n: 1, durationSeconds: 100 } as never);
docs/reviews/whole-branch-cloud-sync-codex.md:646:tests/integration/job-queue-store.test.ts:54:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { n: 1, durationSeconds: 100 } as never);
docs/reviews/whole-branch-cloud-sync-codex.md:648:tests/integration/job-queue-store.test.ts:77:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { durationSeconds: 100 } as never);
docs/reviews/whole-branch-cloud-sync-codex.md:653:tests/integration/job-queue-producer.test.ts:22:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null, ...over,
docs/reviews/whole-branch-cloud-sync-codex.md:682:supabase/migrations/0020_reservation_release.sql:204:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:690:tests/components/video-row-share-2c.test.tsx:47:    summaryMd: 'summary.md',
docs/reviews/whole-branch-cloud-sync-codex.md:691:tests/api/pdf-route.test.ts:25:    overallScore: 4, summaryMd: 'raw/275_x.md', summaryHtml: 'htmls/275_x.html',
docs/reviews/whole-branch-cloud-sync-codex.md:697:tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
docs/reviews/whole-branch-cloud-sync-codex.md:701:tests/integration/cloud-sync/e2e.int.test.ts:43:    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-codex.md:706:tests/integration/cloud-sync/e2e.int.test.ts:91:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:724:tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
docs/reviews/whole-branch-cloud-sync-codex.md:726:tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-codex.md:730:tests/integration/cloud-sync/e2e.int.test.ts:328:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:738:tests/integration/cloud-sync/e2e.int.test.ts:361:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:746:tests/integration/share-serve.test.ts:94:      data: { id: videoId, title: 'My Doc Title', language: 'en', summaryMd: 'v-titletest.md',
docs/reviews/whole-branch-cloud-sync-codex.md:747:tests/integration/share-serve.test.ts:95:              docVersion: 1, artifacts: { summaryMd: { key: 'v-titletest.md', status: 'promoted' } } },
docs/reviews/whole-branch-cloud-sync-codex.md:751:tests/integration/cancel-by-playlist.test.ts:18:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:752:supabase/migrations/0019_share_tokens_cascade.sql:42:-- the path. The `service_role` grant below is inert on its own: auth.uid() is null with no
docs/reviews/whole-branch-cloud-sync-codex.md:767:tests/integration/job-queue-playlist-identity.test.ts:22:    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:771:tests/integration/job-queue-playlist-identity.test.ts:35:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:799:tests/integration/annotations-rpc.test.ts:123:  // (e) non-allowlisted key in p_set (e.g. summaryMd) is NOT written
docs/reviews/whole-branch-cloud-sync-codex.md:800:tests/integration/annotations-rpc.test.ts:132:      p, videoId, { personalScore: 3, summaryMd: 'hacked.md' } as any, [],
docs/reviews/whole-branch-cloud-sync-codex.md:802:tests/integration/annotations-rpc.test.ts:139:    // summaryMd was already seeded (seedPromotedVideo sets it); assert the RPC's value
docs/reviews/whole-branch-cloud-sync-codex.md:803:tests/integration/annotations-rpc.test.ts:141:    expect(v.summaryMd).not.toBe('hacked.md');
docs/reviews/whole-branch-cloud-sync-codex.md:804:tests/integration/annotations-rpc.test.ts:144:  // (f) an existing merge_video_data write of summaryHtml:null still stores null
docs/reviews/whole-branch-cloud-sync-codex.md:806:tests/integration/annotations-rpc.test.ts:146:  it('merge_video_data (unchanged) still stores an explicit null for summaryHtml', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:807:tests/integration/annotations-rpc.test.ts:153:    await store.updateVideoFields(p, videoId, { summaryHtml: null } as any);
docs/reviews/whole-branch-cloud-sync-codex.md:814:supabase/migrations/0011_cost_guardrails.sql:31:  summary_max_attempts int not null default 1 check (summary_max_attempts >= 1),    -- billable executions/row; enqueue_job sets jobs.max_attempts. ≥1: else the guard test (est≥worst×attempts) is tautological at 0 while claim_next_job still bills once (round-4 H2)
docs/reviews/whole-branch-cloud-sync-codex.md:849:tests/integration/reservation-release.test.ts:58:// p_enqueue_ip:null, and a durationSeconds payload the duration guardrail (0018:42) requires.
docs/reviews/whole-branch-cloud-sync-codex.md:852:tests/integration/reservation-release.test.ts:62:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:857:tests/integration/reservation-release.test.ts:79:// tests — a later, unrelated enqueueAndLease(..., p_video_id: null) elsewhere in a long full-file
docs/reviews/whole-branch-cloud-sync-codex.md:919:tests/api/regenerate.test.ts:49:  summaryMd: SUMMARY_MD,
docs/reviews/whole-branch-cloud-sync-codex.md:920:tests/api/regenerate.test.ts:93:  it('returns 422 when video has no summaryMd', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:921:tests/api/regenerate.test.ts:96:      videos: [{ ...baseVideo, summaryMd: null }],
docs/reviews/whole-branch-cloud-sync-codex.md:926:supabase/migrations/0016_update_video_annotations.sql:6:--     non-allowlisted key in p_set (e.g. summaryMd) is silently dropped, never written.
docs/reviews/whole-branch-cloud-sync-codex.md:939:tests/integration/summary-handler.test.ts:122:  expect(data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:940:tests/integration/summary-handler.test.ts:125:  expect(data.summaryMd).toBe(`${baseName}.md`);
docs/reviews/whole-branch-cloud-sync-codex.md:941:tests/integration/summary-handler.test.ts:126:  expect(data.artifacts.summaryMd.key).toBe(`${baseName}.md`);
docs/reviews/whole-branch-cloud-sync-codex.md:942:tests/integration/summary-handler.test.ts:163:  expect(after.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:945:tests/integration/summary-handler.test.ts:272:  expect(midRow.data!.data.artifacts.summaryMd.status).toBe('committed');
docs/reviews/whole-branch-cloud-sync-codex.md:946:tests/integration/summary-handler.test.ts:284:  expect(finalRow.data!.data.artifacts.summaryMd.status).toBe('promoted'); // no orphan
docs/reviews/whole-branch-cloud-sync-codex.md:948:tests/integration/summary-handler.test.ts:288:  expect(finalRow.data!.data.summaryMd).toBe(`${baseName}.md`);
docs/reviews/whole-branch-cloud-sync-codex.md:949:tests/integration/summary-handler.test.ts:373:    expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:951:lib/timestamp-audit.ts:39:    if (v.summaryMd) {
docs/reviews/whole-branch-cloud-sync-codex.md:952:lib/timestamp-audit.ts:41:      classify(summaries, folder, v.id, v.summaryMd, ver.major, CURRENT_DOC_VERSION.major);
docs/reviews/whole-branch-cloud-sync-codex.md:963:tests/integration/dig-cloud.test.ts:74:      videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
docs/reviews/whole-branch-cloud-sync-codex.md:968:tests/integration/dig-cloud.test.ts:98:      videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
docs/reviews/whole-branch-cloud-sync-codex.md:971:tests/integration/dig-cloud.test.ts:115:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
docs/reviews/whole-branch-cloud-sync-codex.md:977:tests/integration/dig-cloud.test.ts:131:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
docs/reviews/whole-branch-cloud-sync-codex.md:978:tests/integration/dig-cloud.test.ts:147:      const r = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: sec, enqueueIp: null });
docs/reviews/whole-branch-cloud-sync-codex.md:981:tests/integration/dig-cloud.test.ts:171:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
docs/reviews/whole-branch-cloud-sync-codex.md:983:tests/integration/dig-cloud.test.ts:184:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
docs/reviews/whole-branch-cloud-sync-codex.md:986:tests/integration/dig-cloud.test.ts:192:    const call = () => enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
docs/reviews/whole-branch-cloud-sync-codex.md:1000:tests/integration/cloud-sync/stamping.int.test.ts:94:      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
docs/reviews/whole-branch-cloud-sync-codex.md:1004:tests/integration/delete-playlist-store.test.ts:39:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:1032:tests/integration/jobs-producer-polling.test.ts:27:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
docs/reviews/whole-branch-cloud-sync-codex.md:1042:tests/integration/worker-persistence-rpcs.test.ts:55:test('status-only persist preserves the prior summaryMd key', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1043:tests/integration/worker-persistence-rpcs.test.ts:59:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-codex.md:1045:tests/integration/worker-persistence-rpcs.test.ts:62:  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1046:tests/integration/worker-persistence-rpcs.test.ts:63:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:1047:tests/integration/worker-persistence-rpcs.test.ts:67:test('persist_summary preserves a sibling artifact kind (deepDiveMd) across a summaryMd status write', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1048:tests/integration/worker-persistence-rpcs.test.ts:71:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-codex.md:1051:tests/integration/worker-persistence-rpcs.test.ts:90:  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1052:tests/integration/worker-persistence-rpcs.test.ts:91:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:1054:tests/integration/worker-persistence-rpcs.test.ts:99:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'promoted' });
docs/reviews/whole-branch-cloud-sync-codex.md:1055:tests/integration/worker-persistence-rpcs.test.ts:100:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-codex.md:1056:tests/integration/worker-persistence-rpcs.test.ts:102:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:1058:tests/integration/worker-persistence-rpcs.test.ts:109:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-codex.md:1061:tests/integration/worker-persistence-rpcs.test.ts:123:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:1063:tests/integration/worker-persistence-rpcs.test.ts:130:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3 }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-codex.md:1066:tests/integration/worker-persistence-rpcs.test.ts:141:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3, ratings: { usefulness: 5 } }, p_artifact_status: 'promoted' });
docs/reviews/whole-branch-cloud-sync-codex.md:1067:tests/integration/worker-persistence-rpcs.test.ts:147:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:1068:tests/integration/worker-persistence-rpcs.test.ts:150:test('a status-only persist preserves existing summary-owned fields (language/ratings/docVersion), not just summaryMd', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1069:tests/integration/worker-persistence-rpcs.test.ts:155:  const full = { id: vid, summaryMd: '1_t.md', language: 'en', ratings: { usefulness: 4 }, overallScore: 4, docVersion: { major: 3, minor: 3 } };
docs/reviews/whole-branch-cloud-sync-codex.md:1072:tests/integration/worker-persistence-rpcs.test.ts:165:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:1074:tests/integration/worker-persistence-rpcs.test.ts:172:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_old.md' }, p_artifact_status: 'promoted' });
docs/reviews/whole-branch-cloud-sync-codex.md:1076:tests/integration/worker-persistence-rpcs.test.ts:175:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_new.md' }, p_artifact_status: 'committed' });
docs/reviews/whole-branch-cloud-sync-codex.md:1077:tests/integration/worker-persistence-rpcs.test.ts:177:  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_new.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1078:tests/integration/worker-persistence-rpcs.test.ts:178:  expect(row.data!.data.artifacts.summaryMd.status).toBe('committed');
docs/reviews/whole-branch-cloud-sync-codex.md:1084:lib/summary-audit.ts:23:    if (!v.summaryMd) continue;
docs/reviews/whole-branch-cloud-sync-codex.md:1085:lib/summary-audit.ts:26:    // `summaryMd` is index-controlled; a corrupt/hand-edited entry could contain `../`. Only accept
docs/reviews/whole-branch-cloud-sync-codex.md:1086:lib/summary-audit.ts:33:    // Validate the raw summaryMd first — a `../` here is an unsafe (traversal) index entry. Only
docs/reviews/whole-branch-cloud-sync-codex.md:1087:lib/summary-audit.ts:37:    const direct = contained(v.summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:1088:lib/summary-audit.ts:42:    const candidates = [direct, contained(path.join('archived', v.summaryMd))]
docs/reviews/whole-branch-cloud-sync-codex.md:1092:tests/components/video-menu-cloud-2c.test.tsx:20:  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:1096:tests/integration/cancel-job-rpc.test.ts:18:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null });
docs/reviews/whole-branch-cloud-sync-codex.md:1101:tests/api/dig-state.test.ts:32:    summaryMd: 'test-video.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1105:tests/integration/worker-main.test.ts:31:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { hi: 1, durationSeconds: 100 } as never);
docs/reviews/whole-branch-cloud-sync-codex.md:1113:tests/integration/job-queue-worker.test.ts:19:    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null, ...over });
docs/reviews/whole-branch-cloud-sync-codex.md:1130:supabase/migrations/0013_share_tokens.sql:36:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:1146:tests/integration/helpers/cloud.ts:244:    summaryMd: `${base}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:1151:tests/integration/helpers/cloud.ts:286:// blob and set video.summaryMd to the KEY they wrote.
docs/reviews/whole-branch-cloud-sync-codex.md:1152:tests/integration/helpers/cloud.ts:294:  /** Blob KEY (video.summaryMd). Default `${videoId}.md`. `null` = summary-less video (no blob). */
docs/reviews/whole-branch-cloud-sync-codex.md:1153:tests/integration/helpers/cloud.ts:295:  summaryMd?: string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:1154:tests/integration/helpers/cloud.ts:296:  /** MD BODY written to the blob at the summaryMd key. Omit to skip the blob write. */
docs/reviews/whole-branch-cloud-sync-codex.md:1156:tests/integration/helpers/cloud.ts:317:  /** Extra artifacts.* pointers MERGED alongside summaryMd (e.g. a summaryPdf that must be dropped). */
docs/reviews/whole-branch-cloud-sync-codex.md:1158:tests/integration/helpers/cloud.ts:343:  const summaryMd = f.summaryMd === undefined ? `${videoId}.md` : f.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1159:tests/integration/helpers/cloud.ts:344:  const base = summaryMd ? summaryMd.replace(/\.md$/, '') : null;
docs/reviews/whole-branch-cloud-sync-codex.md:1160:tests/integration/helpers/cloud.ts:354:    summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1161:tests/integration/helpers/cloud.ts:374:            ...(base ? { summaryMd: { key: `${base}.md`, status: f.status ?? 'promoted' } } : {}),
docs/reviews/whole-branch-cloud-sync-codex.md:1162:tests/integration/helpers/cloud.ts:403:  const summaryMd = data.summaryMd as string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:1163:tests/integration/helpers/cloud.ts:404:  if (summaryMd && f.mdBody != null) {
docs/reviews/whole-branch-cloud-sync-codex.md:1164:tests/integration/helpers/cloud.ts:405:    await seedSummaryBlob(svc, ctx.userId, ctx.playlistKey, summaryMd.replace(/\.md$/, ''), f.mdBody);
docs/reviews/whole-branch-cloud-sync-codex.md:1167:tests/integration/helpers/cloud.ts:420:  const summaryMd = data.summaryMd as string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:1168:tests/integration/helpers/cloud.ts:421:  if (summaryMd && f.mdBody != null) {
docs/reviews/whole-branch-cloud-sync-codex.md:1169:tests/integration/helpers/cloud.ts:422:    await ctx.localBlob.put(lp, summaryMd, Buffer.from(f.mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-codex.md:1175:tests/integration/helpers/seed.ts:20: *  with the top-level `summaryMd`/`language`/`serialNumber` the route reads AND
docs/reviews/whole-branch-cloud-sync-codex.md:1176:tests/integration/helpers/seed.ts:21: *  `artifacts.summaryMd.{key,status}` the reserve RPC + route status-gate read. Defaults to
docs/reviews/whole-branch-cloud-sync-codex.md:1180:tests/integration/helpers/seed.ts:41:      summaryMd: `${base}.md`,                    // top-level key the route get()s (summary-handler.ts:157)
docs/reviews/whole-branch-cloud-sync-codex.md:1181:tests/integration/helpers/seed.ts:43:      artifacts: { summaryMd: { key: `${base}.md`, status } },
docs/reviews/whole-branch-cloud-sync-codex.md:1185:supabase/migrations/0017_share_token_id_return.sql:23:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:1193:tests/integration/job-queue-runner.test.ts:30:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { hi: 1, durationSeconds: 100 } as never);
docs/reviews/whole-branch-cloud-sync-codex.md:1195:tests/integration/job-queue-runner.test.ts:53:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { durationSeconds: 100 } as never);
docs/reviews/whole-branch-cloud-sync-codex.md:1198:tests/api/pdf-serve-cloud.test.ts:51:// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
docs/reviews/whole-branch-cloud-sync-codex.md:1199:tests/api/pdf-serve-cloud.test.ts:52:const promotedVideo = { id: validVideo, language: 'en', summaryMd: `${validVideo}.md`, artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } } };
docs/reviews/whole-branch-cloud-sync-codex.md:1202:tests/api/pdf-serve-cloud.test.ts:117:  mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
docs/reviews/whole-branch-cloud-sync-codex.md:1203:tests/api/pdf-serve-cloud.test.ts:128:it('lost md blob (promoted but blob null) → 409', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1210:tests/api/html-doc-pipeline.test.ts:59:    overallScore: 4, summaryMd: 'ko-video.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1245:tests/api/videos.test.ts:21:    summaryMd: `${id}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:1247:lib/pipeline.ts:42:  summaryMd: string;
docs/reviews/whole-branch-cloud-sync-codex.md:1248:lib/pipeline.ts:58:  return { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent: result.mdContent, summaryMd: `${baseName}.md` };
docs/reviews/whole-branch-cloud-sync-codex.md:1249:lib/pipeline.ts:104:  const summaryMd = file;
docs/reviews/whole-branch-cloud-sync-codex.md:1250:lib/pipeline.ts:120:    summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1258:lib/pipeline.ts:265:        summaryMd: `${baseName}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:1267:tests/api/html-serve.test.ts:24:    overallScore: 4, summaryMd: 'a.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1268:tests/api/html-serve.test.ts:166:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
docs/reviews/whole-branch-cloud-sync-codex.md:1269:tests/api/html-serve.test.ts:178:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
docs/reviews/whole-branch-cloud-sync-codex.md:1270:tests/api/html-serve.test.ts:188:  // summaryMd points to a file that does not exist on disk
docs/reviews/whole-branch-cloud-sync-codex.md:1271:tests/api/html-serve.test.ts:189:  writeIndex(video({ summaryMd: 'wiki/nonexistent.md', digDeeperMd: null }));
docs/reviews/whole-branch-cloud-sync-codex.md:1272:tests/api/html-serve.test.ts:199:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
docs/reviews/whole-branch-cloud-sync-codex.md:1273:tests/api/html-serve.test.ts:213:    summaryMd: 'wiki/video.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1274:tests/api/html-serve.test.ts:244:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
docs/reviews/whole-branch-cloud-sync-codex.md:1275:tests/api/html-serve.test.ts:257:    summaryMd: summaryRel,
docs/reviews/whole-branch-cloud-sync-codex.md:1276:tests/api/html-serve.test.ts:269:  // The route now checks digDeeperPath containment BEFORE deriving summaryMdPath,
docs/reviews/whole-branch-cloud-sync-codex.md:1277:tests/api/html-serve.test.ts:271:  // summaryMd is safe; digDeeperMd escapes → companion assertWithin fires → 400.
docs/reviews/whole-branch-cloud-sync-codex.md:1278:tests/api/html-serve.test.ts:274:    summaryMd: summaryRel,                         // safe: wiki/video.md → stays inside dir
docs/reviews/whole-branch-cloud-sync-codex.md:1279:tests/api/html-serve.test.ts:303:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-codex.md:1280:tests/api/html-serve.test.ts:314:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-codex.md:1281:tests/api/html-serve.test.ts:328:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-codex.md:1282:tests/api/html-serve.test.ts:343:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-codex.md:1283:tests/api/html-serve.test.ts:353:    writeIndex(video({ summaryHtml: 'htmls/missing.html', summaryMd: 'wiki/a.md' }));
docs/reviews/whole-branch-cloud-sync-codex.md:1285:tests/api/review.test.ts:54:  it('deletes personalScore when null is sent (passes undefined to updateVideoFields)', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1289:tests/integration/quickview-route-cloud.test.ts:81:      data: { id: videoId, serialNumber: 1, language: 'en', summaryMd: `${videoId}.md`, docVersion: 1,
docs/reviews/whole-branch-cloud-sync-codex.md:1290:tests/integration/quickview-route-cloud.test.ts:82:              artifacts: { summaryMd: { key: `${videoId}.md`, status: 'promoted' } }, tldr: 'x' },
docs/reviews/whole-branch-cloud-sync-codex.md:1291:tests/integration/quickview-route-cloud.test.ts:90:  it('owned video WITH summaryMd && tldr → { tldr, takeaways, tags }', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1292:tests/integration/quickview-route-cloud.test.ts:96:        id: videoId, serialNumber: 1, language: 'en', summaryMd: `${videoId}.md`, docVersion: 1,
docs/reviews/whole-branch-cloud-sync-codex.md:1293:tests/integration/quickview-route-cloud.test.ts:97:        artifacts: { summaryMd: { key: `${videoId}.md`, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:1294:tests/integration/quickview-route-cloud.test.ts:114:  it('owned video missing summaryMd → 404 (availability gate)', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1295:tests/integration/quickview-route-cloud.test.ts:119:      data: { id: videoId, serialNumber: 1, language: 'en', docVersion: 1, tldr: 'has tldr but no summaryMd' },
docs/reviews/whole-branch-cloud-sync-codex.md:1296:tests/integration/quickview-route-cloud.test.ts:132:    // seedPromotedVideo's default data has summaryMd but no tldr.
docs/reviews/whole-branch-cloud-sync-codex.md:1298:tests/api/quick-view.test.ts:47:  it('returns 404 when video has no summaryMd', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1299:tests/api/quick-view.test.ts:50:      videos: [{ id: VIDEO_ID, summaryMd: null, tldr: undefined } as any],
docs/reviews/whole-branch-cloud-sync-codex.md:1300:tests/api/quick-view.test.ts:56:  it('returns 404 when video has summaryMd but no tldr', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1301:tests/api/quick-view.test.ts:59:      videos: [{ id: VIDEO_ID, summaryMd: 'test.md', tldr: undefined } as any],
docs/reviews/whole-branch-cloud-sync-codex.md:1302:tests/api/quick-view.test.ts:70:        summaryMd: 'test.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1303:tests/api/quick-view.test.ts:89:      videos: [{ id: VIDEO_ID, summaryMd: 'test.md', tldr: 'This video explains X.' } as any],
docs/reviews/whole-branch-cloud-sync-codex.md:1310:tests/api/backfill.test.ts:41:  summaryMd: 'test.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1313:tests/api/dig-post.test.ts:98:  summaryMd: 'test-video.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1318:lib/dig/dig-section.ts:31:  const summaryMdName = video.summaryMd ?? `${videoId}.md`;
docs/reviews/whole-branch-cloud-sync-codex.md:1319:lib/dig/dig-section.ts:32:  const summaryMdPath = path.join(outputFolder, summaryMdName);
docs/reviews/whole-branch-cloud-sync-codex.md:1320:lib/dig/dig-section.ts:33:  const mdContent = await fs.readFile(summaryMdPath, 'utf8');
docs/reviews/whole-branch-cloud-sync-codex.md:1321:lib/dig/dig-section.ts:83:  const summaryBasename = path.basename(summaryMdName, '.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1325:tests/api/serve-summary-core.test.ts:37:// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
docs/reviews/whole-branch-cloud-sync-codex.md:1327:tests/api/serve-summary-core.test.ts:39:  id: validVideo, language: 'en', summaryMd: `${validVideo}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:1328:tests/api/serve-summary-core.test.ts:40:  artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:1331:tests/api/serve-summary-core.test.ts:54:    mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
docs/reviews/whole-branch-cloud-sync-codex.md:1333:tests/api/serve-summary-core.test.ts:74:      artifacts: { summaryMd: { key: 'nested/foo.md', status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:1339:tests/api/html-serve-cloud.test.ts:48:// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
docs/reviews/whole-branch-cloud-sync-codex.md:1340:tests/api/html-serve-cloud.test.ts:49:const promotedVideo = { id: validVideo, language: 'en', summaryMd: `${validVideo}.md`, artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } } };
docs/reviews/whole-branch-cloud-sync-codex.md:1343:tests/api/html-serve-cloud.test.ts:93:  mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
docs/reviews/whole-branch-cloud-sync-codex.md:1344:tests/api/html-serve-cloud.test.ts:97:  mockIndexVideos = [{ id: validVideo, language: 'en', summaryMd: null }];
docs/reviews/whole-branch-cloud-sync-codex.md:1345:tests/api/html-serve-cloud.test.ts:100:it('B13b: promoted but MD blob null → repair-needed 409', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1347:tests/api/html-serve-cloud.test.ts:133:    summaryMd: '0001_intro.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1348:tests/api/html-serve-cloud.test.ts:134:    artifacts: { summaryMd: { key: '0001_intro.md', status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:1351:lib/serial-migrate-exec.ts:126:      if (op.field === 'summaryMd') mdNewName = path.basename(op.to);
docs/reviews/whole-branch-cloud-sync-codex.md:1354:lib/archive.ts:23:  for (const relPath of [video.summaryMd]) {
docs/reviews/whole-branch-cloud-sync-codex.md:1356:lib/archive.ts:71:  for (const md of [video.summaryMd]) {
docs/reviews/whole-branch-cloud-sync-codex.md:1358:tests/scripts/backfill-serial-prefix.test.ts:9:function makeVideo(id: string, processedAt: string, summaryMd: string | null) {
docs/reviews/whole-branch-cloud-sync-codex.md:1359:tests/scripts/backfill-serial-prefix.test.ts:19:    summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1360:tests/scripts/backfill-serial-prefix.test.ts:38:    // Seed temp index with one video whose summaryMd is set and NO serialNumber
docs/reviews/whole-branch-cloud-sync-codex.md:1371:lib/cloud-sync/sync-run.ts:58:/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
docs/reviews/whole-branch-cloud-sync-codex.md:1372:lib/cloud-sync/sync-run.ts:60:  if (!video.summaryMd) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:1373:lib/cloud-sync/sync-run.ts:61:  const buf = await blob.get(p, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:1377:lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-codex.md:1378:lib/cloud-sync/sync-run.ts:106: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-codex.md:1380:lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-codex.md:1381:lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-codex.md:1391:lib/cloud-sync/sync-run.ts:153:  if (video.summaryMd && mdBody != null) {
docs/reviews/whole-branch-cloud-sync-codex.md:1393:lib/cloud-sync/sync-run.ts:155:    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-codex.md:1396:lib/cloud-sync/sync-run.ts:170:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-codex.md:1399:lib/cloud-sync/sync-run.ts:185:  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-codex.md:1404:lib/cloud-sync/sync-run.ts:245: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-codex.md:1407:lib/cloud-sync/sync-run.ts:251:  if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-codex.md:1410:lib/cloud-sync/sync-run.ts:255:  const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1415:lib/cloud-sync/sync-run.ts:275:    summaryMd: key,
docs/reviews/whole-branch-cloud-sync-codex.md:1418:lib/cloud-sync/sync-run.ts:288:    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:1421:lib/cloud-sync/sync-run.ts:301:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:1422:lib/cloud-sync/sync-run.ts:302:  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:1428:lib/cloud-sync/sync-run.ts:378:        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-codex.md:1430:lib/cloud-sync/sync-run.ts:391:              deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-codex.md:1447:lib/cloud-sync/backfill.ts:5:// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
docs/reviews/whole-branch-cloud-sync-codex.md:1448:lib/cloud-sync/backfill.ts:6:// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-codex.md:1449:lib/cloud-sync/backfill.ts:7:export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
docs/reviews/whole-branch-cloud-sync-codex.md:1450:lib/cloud-sync/backfill.ts:10:    summaryMdKey: video.summaryMd ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:1451:lib/cloud-sync/backfill.ts:11:    mdHash: mdBody != null ? mdHash(mdBody) : null,
docs/reviews/whole-branch-cloud-sync-codex.md:1455:lib/job-queue/enqueuer.ts:10:  enqueueIp: string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:1471:lib/job-queue/summary-handler.ts:85:    const existingArtifacts = (existing as unknown as { artifacts?: { summaryMd?: { status?: string } } } | null)?.artifacts;
docs/reviews/whole-branch-cloud-sync-codex.md:1472:lib/job-queue/summary-handler.ts:87:      existingArtifacts?.summaryMd?.status === 'promoted' &&
docs/reviews/whole-branch-cloud-sync-codex.md:1473:lib/job-queue/summary-handler.ts:130:          // GUARDED: delete ONLY a row that is still the bare reservation (`data.summaryMd is null`), so a
docs/reviews/whole-branch-cloud-sync-codex.md:1475:lib/job-queue/summary-handler.ts:134:            .is('data->>summaryMd', null);
docs/reviews/whole-branch-cloud-sync-codex.md:1476:lib/job-queue/summary-handler.ts:157:      summaryMd: `${baseName}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:1481:lib/cloud-sync/reconcile-class-a.ts:17:  const lHas = local.mdHash != null;
docs/reviews/whole-branch-cloud-sync-codex.md:1482:lib/cloud-sync/reconcile-class-a.ts:18:  const cHas = cloud.mdHash != null;
docs/reviews/whole-branch-cloud-sync-codex.md:1487:lib/cloud-sync/types.ts:5:  summaryMdKey: string | null;    // the blob KEY (video.summaryMd) — NOT the body
docs/reviews/whole-branch-cloud-sync-codex.md:1488:lib/cloud-sync/types.ts:6:  mdHash: string | null;          // SHA-256 of the MD BODY (read from the blob by the caller); null when no MD
docs/reviews/whole-branch-cloud-sync-codex.md:1489:lib/cloud-sync/types.ts:32:  classA: { docVersionMajor: number; mdGeneratedAt: string | null; mdCorrectionsHash: string | null; mdHash: string | null };
docs/reviews/whole-branch-cloud-sync-codex.md:1491:lib/job-queue/dig-handler.ts:53:    // SAME summary-key rule as the trigger's loadSummaryForServe (artifacts.summaryMd.key ??
docs/reviews/whole-branch-cloud-sync-codex.md:1492:lib/job-queue/dig-handler.ts:54:    // summaryMd, validated) — guarantees the handler writes the exact base the trigger deduped on.
docs/reviews/whole-branch-cloud-sync-codex.md:1494:lib/dig/cloud/resolve-summary-key.ts:3:/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
docs/reviews/whole-branch-cloud-sync-codex.md:1495:lib/dig/cloud/resolve-summary-key.ts:4: *  falling back to the top-level `summaryMd` — validated via `assertCloudSummaryMdKey`. Returns
docs/reviews/whole-branch-cloud-sync-codex.md:1496:lib/dig/cloud/resolve-summary-key.ts:7: *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
docs/reviews/whole-branch-cloud-sync-codex.md:1497:lib/dig/cloud/resolve-summary-key.ts:9: *  top-level `summaryMd` fallback for videos with no artifact record. The dig TRIGGER owns that
docs/reviews/whole-branch-cloud-sync-codex.md:1500:lib/dig/cloud/resolve-summary-key.ts:13:  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
docs/reviews/whole-branch-cloud-sync-codex.md:1501:lib/dig/cloud/resolve-summary-key.ts:14:  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
docs/reviews/whole-branch-cloud-sync-codex.md:1522:lib/paths/assert-within.ts:10: * Use this before every read of an index-supplied relative path (summaryMd, digDeeperMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1525:lib/timestamp-repair.ts:23:    const rel = v?.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1526:lib/html-doc/build-doc-html.ts:73:  // Companion-path containment first, so it keeps independent 400 coverage before summaryMd derivation.
docs/reviews/whole-branch-cloud-sync-codex.md:1527:lib/html-doc/build-doc-html.ts:93:  } else if (video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-codex.md:1528:lib/html-doc/build-doc-html.ts:94:    const sumRel = video.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1529:lib/html-doc/build-doc-html.ts:102:  let summaryMdPath: string;
docs/reviews/whole-branch-cloud-sync-codex.md:1530:lib/html-doc/build-doc-html.ts:104:    summaryMdPath = assertIndexRelPathWithin(outputFolder, path.join(relDir, `${base}.md`));
docs/reviews/whole-branch-cloud-sync-codex.md:1531:lib/html-doc/build-doc-html.ts:110:  let summaryMdContent: string;
docs/reviews/whole-branch-cloud-sync-codex.md:1532:lib/html-doc/build-doc-html.ts:112:    summaryMdContent = fs.readFileSync(summaryMdPath, 'utf-8');
docs/reviews/whole-branch-cloud-sync-codex.md:1533:lib/html-doc/build-doc-html.ts:119:    parsed = parseSummaryMarkdown(summaryMdContent);
docs/reviews/whole-branch-cloud-sync-codex.md:1534:lib/html-doc/build-doc-html.ts:135:  const cropMap = await prepareSlideCropMap(dug, summaryMdPath);
docs/reviews/whole-branch-cloud-sync-codex.md:1535:lib/html-doc/build-doc-html.ts:142:      mdPath: summaryMdPath,
docs/reviews/whole-branch-cloud-sync-codex.md:1538:lib/dig/cloud/enqueue-dig-core.ts:16:  enqueueIp: string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:1548:lib/serial-assign.ts:10:    .filter((v) => v.summaryMd != null && v.serialNumber == null)
docs/reviews/whole-branch-cloud-sync-codex.md:1549:lib/pdf/pdf-path.ts:10: * - summary:    `pdfs/{basename(summaryMd) sans .md}.pdf`
docs/reviews/whole-branch-cloud-sync-codex.md:1550:lib/pdf/pdf-path.ts:25:    if (!video.summaryMd) throw new Error('no summary for this video');
docs/reviews/whole-branch-cloud-sync-codex.md:1551:lib/pdf/pdf-path.ts:26:    base = path.basename(video.summaryMd).replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:1554:lib/html-doc/generate.ts:25:  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');
docs/reviews/whole-branch-cloud-sync-codex.md:1555:lib/html-doc/generate.ts:30:  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:1556:lib/html-doc/generate.ts:32:    throw new Error(`source note not found on disk: ${video.summaryMd}`);
docs/reviews/whole-branch-cloud-sync-codex.md:1557:lib/html-doc/generate.ts:37:  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field
docs/reviews/whole-branch-cloud-sync-codex.md:1558:lib/html-doc/generate.ts:49:  const base = video.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:1559:lib/html-doc/generate.ts:51:    sourceMd: video.summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1560:lib/html-doc/generate.ts:56:    // Stage 3 (§4.2): hash the MD BODY (`md`, line ~33), NOT `sourceMd`/`video.summaryMd`
docs/reviews/whole-branch-cloud-sync-codex.md:1564:lib/html-doc/eligibility.ts:7:  return !!v.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1565:lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
docs/reviews/whole-branch-cloud-sync-codex.md:1566:lib/html-doc/eligibility.ts:19: *   A video with no summaryMd is never eligible (nothing to generate from).
docs/reviews/whole-branch-cloud-sync-codex.md:1567:lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
docs/reviews/whole-branch-cloud-sync-codex.md:1568:lib/html-doc/batch.ts:21:  if (!video.summaryMd) return [];
docs/reviews/whole-branch-cloud-sync-codex.md:1569:lib/html-doc/batch.ts:24:    const md = await fs.readFile(path.join(outputFolder, video.summaryMd), 'utf8');
docs/reviews/whole-branch-cloud-sync-codex.md:1570:lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
docs/reviews/whole-branch-cloud-sync-codex.md:1574:lib/html-doc/ensure.ts:32:  if (!video.summaryMd) throw new Error('no summary note for this video');
docs/reviews/whole-branch-cloud-sync-codex.md:1575:lib/html-doc/ensure.ts:35:  const base = video.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:1579:lib/html-doc/serve-summary-core.ts:47:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
docs/reviews/whole-branch-cloud-sync-codex.md:1580:lib/html-doc/serve-summary-core.ts:48:    .artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1581:lib/html-doc/serve-summary-core.ts:51:  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)
docs/reviews/whole-branch-cloud-sync-codex.md:1582:lib/html-doc/serve-summary-core.ts:53:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
docs/reviews/whole-branch-cloud-sync-codex.md:1583:lib/html-doc/serve-summary-core.ts:54:  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
docs/reviews/whole-branch-cloud-sync-codex.md:1584:lib/html-doc/serve-summary-core.ts:56:  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1585:lib/html-doc/serve-summary-core.ts:67:  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)
docs/reviews/whole-branch-cloud-sync-codex.md:1586:lib/html-doc/serve-summary-core.ts:70:  // derived deterministically from the SAME summaryMd key the model store is keyed on.
docs/reviews/whole-branch-cloud-sync-codex.md:1593:lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
docs/reviews/whole-branch-cloud-sync-codex.md:1595:lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
docs/reviews/whole-branch-cloud-sync-codex.md:1596:lib/html-doc/rerender.ts:42:  const base = video.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:1597:lib/html-doc/rerender.ts:48:    // Fail closed on a crafted summaryMd that escapes the output folder. assertIndexRelPathWithin
docs/reviews/whole-branch-cloud-sync-codex.md:1598:lib/html-doc/rerender.ts:50:    assertIndexRelPathWithin(outputFolder, video.summaryMd, '.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1599:lib/html-doc/rerender.ts:51:    const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:1600:lib/html-doc/rerender.ts:64:  parsed.sourceMd = video.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:1601:lib/html-doc/rerender.ts:78:  summaryMd: string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:1603:lib/html-doc/rerender.ts:118:        summaryMd: video.summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1604:lib/html-doc/rerender.ts:126:      tally.details.push({ summaryMd: video.summaryMd, status: 'error', message: (err as Error).message });
docs/reviews/whole-branch-cloud-sync-codex.md:1606:tests/lib/job-queue/dig-handler.test.ts:54:  // artifacts.summaryMd.key is the authoritative key (top-level summaryMd is a fallback) — the handler
docs/reviews/whole-branch-cloud-sync-codex.md:1607:tests/lib/job-queue/dig-handler.test.ts:56:  (readVideo as jest.Mock).mockResolvedValue({ id: 'vid1', title: 'Vid One', youtubeUrl: 'https://youtu.be/vid1', language: 'en', durationSeconds: 600, summaryMd: '0007_intro.md', artifacts: { summaryMd: { key: '0007_intro.md', status: 'promoted' } } });
docs/reviews/whole-branch-cloud-sync-codex.md:1608:tests/lib/job-queue/dig-handler.test.ts:187:    (freshReadVideo as jest.Mock).mockResolvedValue({ id: 'vid1', title: 'Vid One', youtubeUrl: 'https://youtu.be/vid1', language: 'en', durationSeconds: 600, summaryMd: '0007_intro.md', artifacts: { summaryMd: { key: '0007_intro.md', status: 'promoted' } } });
docs/reviews/whole-branch-cloud-sync-codex.md:1612:tests/lib/format-ingest-summary.test.ts:6:    expect(formatIngestSummary({ ...base, enqueued: 42 })).toEqual({ line: 'Queued 42', challengeLine: null });
docs/reviews/whole-branch-cloud-sync-codex.md:1620:tests/lib/job-queue/producer-title.test.ts:15:const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: null };
docs/reviews/whole-branch-cloud-sync-codex.md:1637:tests/lib/serial-assign.test.ts:7:  overallScore: 3, summaryMd: 's.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1638:tests/lib/serial-assign.test.ts:25:      v({ id: 'nofile', summaryMd: null }),        // no file → excluded
docs/reviews/whole-branch-cloud-sync-codex.md:1640:tests/lib/serial-invariant.test.ts:16:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:1641:tests/lib/serial-invariant.test.ts:27:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1642:tests/lib/serial-invariant.test.ts:32:    const v = makeVideo({ serialNumber: 7, summaryMd: 'x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1643:tests/lib/serial-invariant.test.ts:34:      { id: 'vid', serial: 7, field: 'summaryMd', value: 'x.md', expected: '007_x.md', reason: 'prefix' },
docs/reviews/whole-branch-cloud-sync-codex.md:1644:tests/lib/serial-invariant.test.ts:39:    const v = makeVideo({ serialNumber: 7, summaryMd: '002_x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1645:tests/lib/serial-invariant.test.ts:42:    expect(out[0]).toMatchObject({ field: 'summaryMd', reason: 'prefix', expected: '007_x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1646:tests/lib/serial-invariant.test.ts:46:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1647:tests/lib/serial-invariant.test.ts:48:      { id: 'vid', serial: 7, field: 'summaryMd', value: '007_x.md', expected: '007_x.md', reason: 'missing' },
docs/reviews/whole-branch-cloud-sync-codex.md:1648:tests/lib/serial-invariant.test.ts:53:    const v = makeVideo({ serialNumber: undefined, summaryMd: 'x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1649:tests/lib/serial-invariant.test.ts:58:    const v = makeVideo({ serialNumber: 7, summaryMd: null, summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-codex.md:1650:tests/lib/serial-invariant.test.ts:70:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md', digDeeperMd: 'x-dig-deeper.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1651:tests/lib/serial-invariant.test.ts:77:    const v = makeVideo({ serialNumber: 7, summaryMd: 'x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1652:tests/lib/serial-invariant.test.ts:84:    const clean = makeVideo({ id: 'a', serialNumber: 1, summaryMd: '001_a.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1653:tests/lib/serial-invariant.test.ts:85:    const dirty = makeVideo({ id: 'b', serialNumber: 2, summaryMd: 'b.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1654:tests/lib/serial-invariant.test.ts:88:    expect(out[0]).toMatchObject({ id: 'b', field: 'summaryMd', reason: 'prefix' });
docs/reviews/whole-branch-cloud-sync-codex.md:1655:tests/lib/serial-invariant.test.ts:91:  it('checks every nullable path field, not just summaryMd', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1656:tests/lib/serial-invariant.test.ts:107:      summaryMd: 'a.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1657:tests/lib/serial-invariant.test.ts:121:    const v = makeVideo({ serialNumber: 0, summaryMd: 'x.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1658:tests/lib/serial-invariant.test.ts:124:      { id: 'vid', serial: 0, field: 'summaryMd', value: 'x.md', expected: '000_x.md', reason: 'prefix' },
docs/reviews/whole-branch-cloud-sync-codex.md:1659:tests/lib/types.test.ts:8:    overallScore: 3, summaryMd: 'a.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1660:tests/lib/types.test.ts:29:    overallScore: 3, summaryMd: 'a.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1664:tests/lib/pipeline.test.ts:71:    summaryMd: `001_video-${id}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:1668:tests/lib/pipeline.test.ts:243:      expect.objectContaining({ serialNumber: 1, summaryMd: '001_hello-world.md' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1669:tests/lib/pipeline.test.ts:261:      expect.objectContaining({ serialNumber: 42, summaryMd: '042_hello-world.md' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1670:tests/lib/pipeline.test.ts:276:        summaryMd: '001_hello-world.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1672:tests/lib/pipeline.test.ts:308:      expect.objectContaining({ id: 'vid1', serialNumber: 1, summaryMd: '001_alpha-video.md' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1673:tests/lib/pipeline.test.ts:312:      expect.objectContaining({ id: 'vid2', serialNumber: 2, summaryMd: '002_beta-video.md' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1674:tests/lib/pipeline.test.ts:330:        summaryMd: '001_hello-world-2.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1685:tests/lib/pipeline.test.ts:1046:  it('sets summaryMd to the filename', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1686:tests/lib/pipeline.test.ts:1048:    expect(video!.summaryMd).toBe('001_test-video-title.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1687:tests/lib/pipeline.test.ts:1263:    expect(result.summaryMd).toBe('my-base.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1688:tests/lib/pipeline.test.ts:1284:    expect(result.summaryMd).toBe('trunc.md'); // non-blocking — doc still written
docs/reviews/whole-branch-cloud-sync-codex.md:1690:tests/lib/summary-audit.test.ts:10:  const summaryMd = `${base}.md`;
docs/reviews/whole-branch-cloud-sync-codex.md:1691:tests/lib/summary-audit.test.ts:12:    fs.writeFileSync(path.join(dir, summaryMd), `## 1. A\n▶ [0:00–1:00](u)\n${body}`);
docs/reviews/whole-branch-cloud-sync-codex.md:1692:tests/lib/summary-audit.test.ts:14:  return { id, serialNumber, summaryMd };
docs/reviews/whole-branch-cloud-sync-codex.md:1693:tests/lib/summary-audit.test.ts:44:  // archived video: summaryMd base name unchanged, file lives under archived/
docs/reviews/whole-branch-cloud-sync-codex.md:1694:tests/lib/summary-audit.test.ts:46:  const videos = [{ id: 'arch', serialNumber: 5, summaryMd: '005_arch.md', archived: true }];
docs/reviews/whole-branch-cloud-sync-codex.md:1695:tests/lib/summary-audit.test.ts:56:  const videos = [{ id: 'orph', serialNumber: 6, summaryMd: '006_orph.md', archived: true }];
docs/reviews/whole-branch-cloud-sync-codex.md:1696:tests/lib/summary-audit.test.ts:64:it('rejects a summaryMd that escapes the corpus root (path traversal) without reading it', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1697:tests/lib/summary-audit.test.ts:68:  const videos = [{ id: 'evil', serialNumber: 9, summaryMd: `../${path.basename(outside)}` }];
docs/reviews/whole-branch-cloud-sync-codex.md:1698:tests/lib/summary-audit.test.ts:77:it('skips videos without a summaryMd and returns an empty suspect list for a clean corpus', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1699:tests/lib/summary-audit.test.ts:79:    { id: 'nosum', serialNumber: 1 },                            // no summaryMd → not counted
docs/reviews/whole-branch-cloud-sync-codex.md:1704:tests/lib/cloud-sync/model-writer-hash.test.ts:5:// fed to generation — NOT a hash of the sourceMd/summaryMd blob KEY (the filename). Guards
docs/reviews/whole-branch-cloud-sync-codex.md:1707:tests/lib/cloud-sync/model-writer-hash.test.ts:24:// The MD body fed to generation (the whole file `runHtmlDoc` reads as `video.summaryMd`'s blob).
docs/reviews/whole-branch-cloud-sync-codex.md:1708:tests/lib/cloud-sync/model-writer-hash.test.ts:56:    overallScore: 4, summaryMd: 'a-title.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1713:tests/lib/archive.test.ts:30:    summaryMd: `${SLUG}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:1714:tests/lib/archive.test.ts:53:  it('moves summaryMd to archived/', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1732:tests/lib/cloud-sync/reconcile-class-a.test.ts:5:  summaryMdKey: 'x.md', mdHash: 'h', docVersionMajor: 3, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:1737:tests/lib/cloud-sync/reconcile-class-a.test.ts:19:  it('mdHash equal but one current, one stale → current wins, NOT skip (Blocking ③ scenario 1)', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1739:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1754:tests/lib/cloud-sync/reconcile-class-a.test.ts:52:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:1755:tests/lib/cloud-sync/reconcile-class-a.test.ts:54:    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:1756:tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:1757:tests/lib/cloud-sync/reconcile-class-a.test.ts:62:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:1759:tests/lib/serial-migrate-normalization.test.ts:18:function makeVideo(id: string, processedAt: string, summaryMd: string | null, serialNumber?: number): Video {
docs/reviews/whole-branch-cloud-sync-codex.md:1760:tests/lib/serial-migrate-normalization.test.ts:28:    summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1769:tests/lib/cloud-sync/companion.test.ts:22:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: null }))
docs/reviews/whole-branch-cloud-sync-codex.md:1770:tests/lib/cloud-sync/schema.test.ts:8:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:1774:tests/lib/serial-migrate-exec.test.ts:9:function makeVideo(id: string, processedAt: string, summaryMd: string | null): Video {
docs/reviews/whole-branch-cloud-sync-codex.md:1775:tests/lib/serial-migrate-exec.test.ts:19:    summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:1776:tests/lib/serial-migrate-exec.test.ts:38:    // Seed index with 2 videos (summaryMd set, no serialNumber), processedAt ordered
docs/reviews/whole-branch-cloud-sync-codex.md:1778:tests/lib/serial-migrate-exec.test.ts:95:      summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:1779:tests/lib/serial-migrate-exec.test.ts:102:    // Seed: video with serialNumber:1, summaryMd:'alpha.md'
docs/reviews/whole-branch-cloud-sync-codex.md:1780:tests/lib/serial-migrate-exec.test.ts:107:        summaryMd: 'alpha.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1781:tests/lib/serial-migrate-exec.test.ts:121:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1782:tests/lib/serial-migrate-exec.test.ts:130:        summaryMd: 'alpha.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1783:tests/lib/serial-migrate-exec.test.ts:150:        summaryMd: 'alpha.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1784:tests/lib/serial-migrate-exec.test.ts:168:        summaryMd: 'alpha.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1785:tests/lib/serial-migrate-exec.test.ts:178:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1786:tests/lib/serial-migrate-exec.test.ts:187:        summaryMd: 'alpha.md',      }),
docs/reviews/whole-branch-cloud-sync-codex.md:1787:tests/lib/serial-migrate-exec.test.ts:212:        summaryMd: 'alpha.md',        archived: true,
docs/reviews/whole-branch-cloud-sync-codex.md:1788:tests/lib/serial-migrate-exec.test.ts:225:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1790:tests/lib/serial-migrate-exec.test.ts:236:        summaryMd: 'alpha.md',      }),
docs/reviews/whole-branch-cloud-sync-codex.md:1791:tests/lib/serial-migrate-exec.test.ts:248:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1868:tests/lib/index-store-updated-at.test.ts:20:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:1881:tests/lib/archive-html.test.ts:23:    overallScore: 4, summaryMd: 'a.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1884:tests/lib/cloud-sync/backfill.test.ts:8:  overallScore: 3, summaryMd: '001_title.md', processedAt: '2026-01-01T00:00:00.000Z', // KEY, not body
docs/reviews/whole-branch-cloud-sync-codex.md:1885:tests/lib/cloud-sync/backfill.test.ts:14:it('hashes the MD BODY, not the summaryMd key (Blocking ①)', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1889:tests/lib/cloud-sync/backfill.test.ts:18:  expect(s.summaryMdKey).toBe('001_title.md');
docs/reviews/whole-branch-cloud-sync-codex.md:1891:tests/lib/cloud-sync/backfill.test.ts:28:it('mdHash is null when there is no MD body', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1892:tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
docs/reviews/whole-branch-cloud-sync-codex.md:1894:tests/lib/cloud-sync/backfill.test.ts:31:  expect(s.summaryMdKey).toBeNull();
docs/reviews/whole-branch-cloud-sync-codex.md:1897:tests/lib/cloud-sync/local-stamping.test.ts:23:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:1911:tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-codex.md:1915:tests/lib/pdf/pdf-path.test.ts:9:    expect(pdfRelPath(v({ summaryMd: 'raw/275_google-okf.md' }), 'summary')).toBe('pdfs/275_google-okf.pdf');
docs/reviews/whole-branch-cloud-sync-codex.md:1916:tests/lib/pdf/pdf-path.test.ts:13:    expect(pdfRelPath(v({ summaryMd: '001_intro.md' }), 'summary')).toBe('pdfs/001_intro.pdf');
docs/reviews/whole-branch-cloud-sync-codex.md:1917:tests/lib/pdf/pdf-path.test.ts:22:  it('summary without summaryMd throws', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1918:tests/lib/pdf/pdf-path.test.ts:27:    expect(() => pdfRelPath(v({ summaryMd: 'raw/x.md' }), 'dig-deeper')).toThrow();
docs/reviews/whole-branch-cloud-sync-codex.md:1920:tests/lib/timestamp-audit.test.ts:21:      { id: 'a', summaryMd: 'a.md', docVersion: { major: 3, minor: 3 } },          // current, ▶ → withTs
docs/reviews/whole-branch-cloud-sync-codex.md:1921:tests/lib/timestamp-audit.test.ts:22:      { id: 'b', summaryMd: 'b.md', docVersion: { major: 2, minor: 0 } },          // old, no ▶ → wouldRegen
docs/reviews/whole-branch-cloud-sync-codex.md:1922:tests/lib/timestamp-audit.test.ts:23:      { id: 'c', summaryMd: 'c.md', docVersion: { major: 3, minor: 0 } },          // current, no ▶ → stuck
docs/reviews/whole-branch-cloud-sync-codex.md:1923:tests/lib/timestamp-audit.test.ts:24:      { id: 'd', summaryMd: 'd.md' },                                              // absent ver, no ▶ → wouldRegen
docs/reviews/whole-branch-cloud-sync-codex.md:1924:tests/lib/timestamp-audit.test.ts:25:      { id: 'e', summaryMd: 'e.md', docVersion: { major: 3, minor: 0 } },          // file missing → mdMissing
docs/reviews/whole-branch-cloud-sync-codex.md:1926:tests/lib/cloud-sync/regenerate-stamp.test.ts:6:// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
docs/reviews/whole-branch-cloud-sync-codex.md:1930:tests/lib/cloud-sync/regenerate-stamp.test.ts:57:  summaryMd: SUMMARY_MD,
docs/reviews/whole-branch-cloud-sync-codex.md:1939:tests/lib/serial-migrate.test.ts:7:  overallScore: 3, summaryMd: 's.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1940:tests/lib/serial-migrate.test.ts:13:    v({ id: 'a', processedAt: '2026-01-01T00:00:00.000Z', summaryMd: 'alpha.md' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1941:tests/lib/serial-migrate.test.ts:17:  expect(ops).toContainEqual({ field: 'summaryMd', from: 'alpha.md', to: '001_alpha.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1942:tests/lib/serial-migrate.test.ts:22:  const { perVideo } = planMigration([v({ id: 'a', serialNumber: 1, summaryMd: '001_alpha.md' })]);
docs/reviews/whole-branch-cloud-sync-codex.md:1943:tests/lib/serial-migrate.test.ts:23:  expect(perVideo[0].renames.find((o) => o.field === 'summaryMd')).toBeUndefined();
docs/reviews/whole-branch-cloud-sync-codex.md:1944:tests/lib/serial-migrate.test.ts:29:    v({ id: 'new', summaryMd: 'n.md', processedAt: '2026-02-01T00:00:00.000Z' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1945:tests/lib/serial-migrate.test.ts:39:      summaryMd: 'foo.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1946:tests/lib/serial-migrate.test.ts:45:  expect(renames).toContainEqual({ field: 'summaryMd', from: 'foo.md', to: '005_foo.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:1947:tests/lib/dig/dig-section.test.ts:29:const video = { id: 'v', title: 'T', youtubeUrl: 'https://youtu.be/v', durationSeconds: 600, language: 'en', summaryMd: 'v.md' };
docs/reviews/whole-branch-cloud-sync-codex.md:1955:tests/lib/html-doc/rerender.test.ts:60:    overallScore: 4, summaryMd: 'a-title.md',
docs/reviews/whole-branch-cloud-sync-codex.md:1956:tests/lib/html-doc/rerender.test.ts:111:  it('skips when the video has no summaryMd', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1957:tests/lib/html-doc/rerender.test.ts:112:    writeIndex([baseVideo({ summaryMd: null })]);
docs/reviews/whole-branch-cloud-sync-codex.md:1958:tests/lib/html-doc/rerender.test.ts:181:    // video B: summaryMd + summaryHtml set but NO model → skipped-no-model
docs/reviews/whole-branch-cloud-sync-codex.md:1959:tests/lib/html-doc/rerender.test.ts:183:    const vidB = baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' });
docs/reviews/whole-branch-cloud-sync-codex.md:1960:tests/lib/html-doc/rerender.test.ts:191:        expect.objectContaining({ summaryMd: 'a-title.md', status: 'rerendered' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1961:tests/lib/html-doc/rerender.test.ts:192:        expect.objectContaining({ summaryMd: 'b-title.md', status: 'skipped-no-model' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1962:tests/lib/html-doc/rerender.test.ts:198:    const vidC = baseVideo({ id: 'vidC', summaryMd: null, summaryHtml: null });
docs/reviews/whole-branch-cloud-sync-codex.md:1963:tests/lib/html-doc/rerender.test.ts:211:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
docs/reviews/whole-branch-cloud-sync-codex.md:1964:tests/lib/html-doc/rerender.test.ts:224:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
docs/reviews/whole-branch-cloud-sync-codex.md:1965:tests/lib/html-doc/rerender.test.ts:239:        expect.objectContaining({ summaryMd: 'a-title.md', status: 'error', message: expect.stringMatching(/disk full/) }),
docs/reviews/whole-branch-cloud-sync-codex.md:1966:tests/lib/html-doc/rerender.test.ts:240:        expect.objectContaining({ summaryMd: 'b-title.md', status: 'rerendered' }),
docs/reviews/whole-branch-cloud-sync-codex.md:1971:tests/lib/supabase-metadata-store-summary-ready.test.ts:90:            summaryMd: 'hello',
docs/reviews/whole-branch-cloud-sync-codex.md:1972:tests/lib/supabase-metadata-store-summary-ready.test.ts:92:            artifacts: { summaryMd: { status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:1973:tests/lib/supabase-metadata-store-summary-ready.test.ts:106:            summaryMd: 'hello',
docs/reviews/whole-branch-cloud-sync-codex.md:1974:tests/lib/supabase-metadata-store-summary-ready.test.ts:108:            artifacts: { summaryMd: { status: 'committed' } },
docs/reviews/whole-branch-cloud-sync-codex.md:1975:tests/lib/supabase-metadata-store-summary-ready.test.ts:122:            summaryMd: 'hello',
docs/reviews/whole-branch-cloud-sync-codex.md:2013:tests/lib/dig/cloud/enqueue-dig-core.test.ts:25:const base = { supabase: {} as any, enqueuer: enqueuer as any, userId: 'u1', isAnonymous: false, videoId: 'vid1', playlistId: 'pl', sectionId: 132, enqueueIp: null };
docs/reviews/whole-branch-cloud-sync-codex.md:2019:tests/lib/dig/cloud/enqueue-dig-core.test.ts:35:    { ownerId: 'u1', enqueueIp: null },
docs/reviews/whole-branch-cloud-sync-codex.md:2048:tests/lib/dig/cloud/resolve-summary-key.test.ts:4:  it('prefers artifacts.summaryMd.key over the top-level summaryMd fallback', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:2049:tests/lib/dig/cloud/resolve-summary-key.test.ts:5:    const video = { summaryMd: '0001_old.md', artifacts: { summaryMd: { key: '0001_new.md' } } };
docs/reviews/whole-branch-cloud-sync-codex.md:2050:tests/lib/dig/cloud/resolve-summary-key.test.ts:9:  it('falls back to the top-level summaryMd when the artifact key is absent', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:2051:tests/lib/dig/cloud/resolve-summary-key.test.ts:10:    const video = { summaryMd: '0001_old.md' };
docs/reviews/whole-branch-cloud-sync-codex.md:2052:tests/lib/dig/cloud/resolve-summary-key.test.ts:15:    const video = { summaryMd: null };
docs/reviews/whole-branch-cloud-sync-codex.md:2053:tests/lib/dig/cloud/resolve-summary-key.test.ts:20:    const video = { summaryMd: 'nested/foo.md' };
docs/reviews/whole-branch-cloud-sync-codex.md:2058:tests/lib/html-doc/generate.test.ts:64:    overallScore: 4, summaryMd: 'a-title.md',
docs/reviews/whole-branch-cloud-sync-codex.md:2059:tests/lib/html-doc/generate.test.ts:106:it('throws when summaryMd is missing', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:2060:tests/lib/html-doc/generate.test.ts:107:  writeIndex([{ ...baseVideo(), summaryMd: null }]);
docs/reviews/whole-branch-cloud-sync-codex.md:2061:tests/lib/html-doc/generate.test.ts:108:  await expect(runHtmlDoc(VIDEO_ID, dir, () => {})).rejects.toThrow(/source note|summaryMd/i);
docs/reviews/whole-branch-cloud-sync-codex.md:2062:tests/lib/video-schema.test.ts:13:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:2063:tests/lib/video-schema.test.ts:64:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:2069:tests/lib/html-doc/eligibility.test.ts:9:    overallScore: 3, summaryMd: '1_t.md',
docs/reviews/whole-branch-cloud-sync-codex.md:2070:tests/lib/html-doc/eligibility.test.ts:16:  it('selectable iff summaryMd present', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:2071:tests/lib/html-doc/eligibility.test.ts:17:    expect(summarySelectable(v({ summaryMd: '1_t.md' }))).toBe(true);
docs/reviews/whole-branch-cloud-sync-codex.md:2072:tests/lib/html-doc/eligibility.test.ts:18:    expect(summarySelectable(v({ summaryMd: null }))).toBe(false);
docs/reviews/whole-branch-cloud-sync-codex.md:2073:tests/lib/html-doc/eligibility.test.ts:29:  it('no work when no summaryMd (nothing to generate from)', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:2074:tests/lib/html-doc/eligibility.test.ts:30:    expect(summaryNeedsWork(v({ summaryMd: null, summaryHtml: null }))).toBe(false);
docs/reviews/whole-branch-cloud-sync-codex.md:2075:tests/lib/html-doc/eligibility.test.ts:42:    expect(videoNeedsBatchWork(v({ summaryMd: null, summaryHtml: null, digDeeperMd: null }), 'summary-dig')).toBe(false); // no summary → nothing
docs/reviews/whole-branch-cloud-sync-codex.md:2080:tests/lib/index-store.test.ts:21:    summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:2085:tests/lib/index-store.test.ts:75:    expect(v.summaryMd).toBeNull();
docs/reviews/whole-branch-cloud-sync-codex.md:2097:tests/lib/index-store.test.ts:159:    const video = makeVideo({ id: 'vid333333333', summaryMd: null });
docs/reviews/whole-branch-cloud-sync-codex.md:2099:tests/lib/index-store.test.ts:162:    updateVideoFields(dir, 'vid333333333', { summaryMd: 'vid333333333.md', digDeeperMd: 'vid333333333-dig-deeper.md' });
docs/reviews/whole-branch-cloud-sync-codex.md:2101:tests/lib/index-store.test.ts:165:    expect(result.videos[0].summaryMd).toBe('vid333333333.md');
docs/reviews/whole-branch-cloud-sync-codex.md:2105:tests/lib/index-store.test.ts:188:    expect(() => updateVideoFields(dir, 'vid444444444', { summaryMd: 'x.md' })).toThrow('Video not found');
docs/reviews/whole-branch-cloud-sync-codex.md:2110:tests/lib/producer.test.ts:18:const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: null };
docs/reviews/whole-branch-cloud-sync-codex.md:2158:tests/lib/html-doc/ensure.test.ts:18:  overallScore: 3, summaryMd: 'base.md',
docs/reviews/whole-branch-cloud-sync-codex.md:2159:tests/lib/html-doc/ensure.test.ts:28:    language: 'en', ratings: videoBase.ratings, overallScore: 4, tags: ['t'], summaryMd: 'base.md', mdContent: '#',
docs/reviews/whole-branch-cloud-sync-codex.md:2162:tests/lib/html-doc/ensure.test.ts:81:  it('throws 422-style error when the video has no summaryMd', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:2163:tests/lib/html-doc/ensure.test.ts:82:    withVideo({ summaryMd: null });
docs/reviews/whole-branch-cloud-sync-codex.md:2165:tests/lib/ask-gemini.test.ts:12:    overallScore: 4, summaryMd: null,
docs/reviews/whole-branch-cloud-sync-codex.md:2168:lib/storage/supabase/consistency.ts:5:export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';
docs/reviews/whole-branch-cloud-sync-codex.md:2169:lib/storage/supabase/consistency.ts:7:const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];
docs/reviews/whole-branch-cloud-sync-codex.md:2174:lib/storage/supabase/consistency.ts:46: * Source kinds (summaryMd, slide, modelJson) require manual repair — they cannot
docs/reviews/whole-branch-cloud-sync-codex.md:2178:lib/storage/supabase/supabase-metadata-store.ts:11:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
docs/reviews/whole-branch-cloud-sync-codex.md:2179:lib/storage/supabase/supabase-metadata-store.ts:14:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
docs/reviews/whole-branch-cloud-sync-codex.md:2182:lib/storage/supabase/supabase-metadata-store.ts:53:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
docs/reviews/whole-branch-cloud-sync-codex.md:2183:lib/storage/supabase/supabase-metadata-store.ts:54:            .artifacts?.summaryMd?.status === 'promoted',
docs/reviews/whole-branch-cloud-sync-codex.md:2196:tests/lib/storage/consistency.test.ts:15:  test.each<ArtifactKind>(['summaryMd', 'slide', 'modelJson'])('%s is a source kind', (k) => {
docs/reviews/whole-branch-cloud-sync-codex.md:2205:tests/lib/storage/consistency.test.ts:111:      kind: 'summaryMd',
docs/reviews/whole-branch-cloud-sync-codex.md:2211:tests/lib/storage/consistency.test.ts:157:      kind: 'summaryMd',
docs/reviews/whole-branch-cloud-sync-codex.md:2212:tests/lib/storage/consistency.test.ts:196:    const result = await resolveMissing({ kind: 'summaryMd', regenerate, markRepair });
docs/reviews/whole-branch-cloud-sync-codex.md:2232:tests/lib/storage/supabase-metadata-store.test.ts:326:    await store.updateVideoFields(p, 'vid1', { summaryMd: 'hello' } as any);
docs/reviews/whole-branch-cloud-sync-codex.md:2234:tests/lib/storage/supabase-metadata-store.test.ts:331:    expect((rpc!.args as any).p_fields).toEqual({ summaryMd: 'hello' });
docs/reviews/whole-branch-cloud-sync-codex.md:2238:tests/lib/storage/supabase-metadata-store.test.ts:361:      { videoId: 'vid1', fields: { summaryMd: 'a' } as any },
docs/reviews/whole-branch-cloud-sync-codex.md:2239:tests/lib/storage/supabase-metadata-store.test.ts:362:      { videoId: 'vid2', fields: { summaryMd: 'b' } as any },
docs/reviews/whole-branch-cloud-sync-codex.md:2241:tests/lib/storage/supabase-metadata-store.test.ts:369:      { video_id: 'vid1', fields: { summaryMd: 'a' } },
docs/reviews/whole-branch-cloud-sync-codex.md:2242:tests/lib/storage/supabase-metadata-store.test.ts:370:      { video_id: 'vid2', fields: { summaryMd: 'b' } },
docs/reviews/whole-branch-cloud-sync-codex.md:2244:tests/lib/storage/supabase-metadata-store.test.ts:390:      { videoId: 'vid1', fields: { summaryMd: 'a', updatedAt: '2026-01-01T00:00:00Z' } as any },
docs/reviews/whole-branch-cloud-sync-codex.md:2245:tests/lib/storage/supabase-metadata-store.test.ts:391:      { videoId: 'vid2', fields: { summaryMd: 'b', updatedAt: '2026-01-02T00:00:00Z' } as any },
docs/reviews/whole-branch-cloud-sync-codex.md:2247:tests/lib/storage/supabase-metadata-store.test.ts:398:      { video_id: 'vid1', fields: { summaryMd: 'a' } },
docs/reviews/whole-branch-cloud-sync-codex.md:2248:tests/lib/storage/supabase-metadata-store.test.ts:399:      { video_id: 'vid2', fields: { summaryMd: 'b' } },
docs/reviews/whole-branch-cloud-sync-codex.md:2265:lib/storage/worker-persistence.ts:17: *  the row's data and stamps the summaryMd artifact status. */
docs/reviews/whole-branch-cloud-sync-codex.md:2269:tests/lib/html-doc/batch.test.ts:32:    overallScore: 3, summaryMd: `${id}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:2270:tests/lib/html-doc/batch.test.ts:130:    indexWith([v('x', { summaryHtml: null, summaryMd: 'x.md', digDeeperMd: null })]);
docs/reviews/whole-branch-cloud-sync-codex.md:2271:tests/lib/html-doc/batch.test.ts:143:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' })]);
docs/reviews/whole-branch-cloud-sync-codex.md:2272:tests/lib/html-doc/batch.test.ts:154:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
docs/reviews/whole-branch-cloud-sync-codex.md:2273:tests/lib/html-doc/batch.test.ts:164:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md' })]);
docs/reviews/whole-branch-cloud-sync-codex.md:2274:tests/lib/html-doc/batch.test.ts:173:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
docs/reviews/whole-branch-cloud-sync-codex.md:2275:tests/lib/html-doc/batch.test.ts:185:      v('bad', { summaryHtml: 'bad.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'bad.md', digDeeperMd: null }),
docs/reviews/whole-branch-cloud-sync-codex.md:2276:tests/lib/html-doc/batch.test.ts:186:      v('ok', { summaryHtml: 'ok.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'ok.md', digDeeperMd: null }),
docs/reviews/whole-branch-cloud-sync-codex.md:2277:tests/lib/html-doc/build-doc-html.test.ts:16:    overallScore: 4, summaryMd: 'a.md', summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-codex.md:2278:tests/lib/html-doc/build-doc-html.test.ts:71:    const r = await buildDocHtml(video({ summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');
docs/reviews/whole-branch-cloud-sync-codex.md:2359:const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');
docs/reviews/whole-branch-cloud-sync-codex.md:2367:  const lHas = local.mdHash != null;
docs/reviews/whole-branch-cloud-sync-codex.md:2368:  const cHas = cloud.mdHash != null;
docs/reviews/whole-branch-cloud-sync-codex.md:2381:  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
docs/reviews/whole-branch-cloud-sync-codex.md:2417://    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
docs/reviews/whole-branch-cloud-sync-codex.md:2463:/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
docs/reviews/whole-branch-cloud-sync-codex.md:2464:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:2465:  if (!video.summaryMd) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:2466:  const buf = await blob.get(p, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:2467:  return buf ? buf.toString('utf8') : null;
docs/reviews/whole-branch-cloud-sync-codex.md:2478:/** Read one video record (or null if absent) from a store's index. */
docs/reviews/whole-branch-cloud-sync-codex.md:2479:async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:2481:  return idx.videos.find((v) => v.id === id) ?? null;
docs/reviews/whole-branch-cloud-sync-codex.md:2510: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-codex.md:2511: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-codex.md:2514:  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-codex.md:2515:  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-codex.md:2516:  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-codex.md:2517:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-codex.md:2519:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-codex.md:2534: *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
docs/reviews/whole-branch-cloud-sync-codex.md:2539:): Promise<{ position: number; serialNumber: number } | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:2542:  if (idx.videos.some((v) => v.id === video.id)) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:2553:  video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-codex.md:2558:  if (video.summaryMd && mdBody != null) {
docs/reviews/whole-branch-cloud-sync-codex.md:2560:    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-codex.md:2575:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-codex.md:2590:  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-codex.md:2650: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-codex.md:2656:  if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-codex.md:2660:  const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:2679:  senderEnvelope: ModelEnvelope | null;
docs/reviews/whole-branch-cloud-sync-codex.md:2709:    summaryMd: key,
docs/reviews/whole-branch-cloud-sync-codex.md:2711:    mdGeneratedAt: wv.mdGeneratedAt ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:2712:    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:2722:    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:2735:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:2736:  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:2754:  winnerSignals: ClassASignals, winnerMdHash: string | null,
docs/reviews/whole-branch-cloud-sync-codex.md:2812:        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-codex.md:2815:          const presentIsLocal = lv != null;
docs/reviews/whole-branch-cloud-sync-codex.md:2825:              deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-codex.md:2849:        let winnerMdHash: string | null = null;
docs/reviews/whole-branch-cloud-sync-codex.md:2851:        let winnerSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-codex.md:2852:        let loserSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-codex.md:2893:// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
docs/reviews/whole-branch-cloud-sync-codex.md:2894:// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-codex.md:2895:export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
docs/reviews/whole-branch-cloud-sync-codex.md:2896:  const hasReal = video.mdGeneratedAt != null;
docs/reviews/whole-branch-cloud-sync-codex.md:2898:    summaryMdKey: video.summaryMd ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:2899:    mdHash: mdBody != null ? mdHash(mdBody) : null,
docs/reviews/whole-branch-cloud-sync-codex.md:2901:    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:2902:    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:2961:  await atomicWrite(manifestPath(dataRoot, playlistKey), JSON.stringify(m, null, 2));
docs/reviews/whole-branch-cloud-sync-codex.md:3007:  summaryMdKey: string | null;    // the blob KEY (video.summaryMd) — NOT the body
docs/reviews/whole-branch-cloud-sync-codex.md:3008:  mdHash: string | null;          // SHA-256 of the MD BODY (read from the blob by the caller); null when no MD
docs/reviews/whole-branch-cloud-sync-codex.md:3010:  mdGeneratedAt: string | null;   // tie-break only
docs/reviews/whole-branch-cloud-sync-codex.md:3011:  mdCorrectionsHash: string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:3034:  classA: { docVersionMajor: number; mdGeneratedAt: string | null; mdCorrectionsHash: string | null; mdHash: string | null };
docs/reviews/whole-branch-cloud-sync-codex.md:3067:  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');
docs/reviews/whole-branch-cloud-sync-codex.md:3072:  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:3074:    throw new Error(`source note not found on disk: ${video.summaryMd}`);
docs/reviews/whole-branch-cloud-sync-codex.md:3079:  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field
docs/reviews/whole-branch-cloud-sync-codex.md:3091:  const base = video.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:3093:    sourceMd: video.summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:3098:    // Stage 3 (§4.2): hash the MD BODY (`md`, line ~33), NOT `sourceMd`/`video.summaryMd`
docs/reviews/whole-branch-cloud-sync-codex.md:3181:  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
docs/reviews/whole-branch-cloud-sync-codex.md:3188:  const row = (data as Array<{ status: string; release_token: string | null }> | null)?.[0];   // table-return → data[0]
docs/reviews/whole-branch-cloud-sync-codex.md:3190:  const releaseToken = row?.release_token ?? null;
docs/reviews/whole-branch-cloud-sync-codex.md:3275:  // must not make an old reader's readModelEnvelope return null (§5.7 round-5 M-2).
docs/reviews/whole-branch-cloud-sync-codex.md:3283:  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
docs/reviews/whole-branch-cloud-sync-codex.md:3302:/** Read + validate. Returns null if absent, unparseable, or schema-invalid. */
docs/reviews/whole-branch-cloud-sync-codex.md:3307:): Promise<ModelEnvelope | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:3309:  if (!bytes) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:3315:    return null;
docs/reviews/whole-branch-cloud-sync-codex.md:3320:    return null;
docs/reviews/whole-branch-cloud-sync-codex.md:3374:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
docs/reviews/whole-branch-cloud-sync-codex.md:3375:    .artifacts?.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:3377:  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-codex.md:3378:  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)
docs/reviews/whole-branch-cloud-sync-codex.md:3380:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
docs/reviews/whole-branch-cloud-sync-codex.md:3381:  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
docs/reviews/whole-branch-cloud-sync-codex.md:3383:  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:3394:  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)
docs/reviews/whole-branch-cloud-sync-codex.md:3397:  // derived deterministically from the SAME summaryMd key the model store is keyed on.
docs/reviews/whole-branch-cloud-sync-codex.md:3497:  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
docs/reviews/whole-branch-cloud-sync-codex.md:3539:  // when currently absent/null in the JSON index; a no-op otherwise.
docs/reviews/whole-branch-cloud-sync-codex.md:3639: *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
docs/reviews/whole-branch-cloud-sync-codex.md:3728:    fs.writeFileSync(tmpPath, JSON.stringify(index, null, 2), 'utf-8');
docs/reviews/whole-branch-cloud-sync-codex.md:3781:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
docs/reviews/whole-branch-cloud-sync-codex.md:3784:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
docs/reviews/whole-branch-cloud-sync-codex.md:3823:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
docs/reviews/whole-branch-cloud-sync-codex.md:3824:            .artifacts?.summaryMd?.status === 'promoted',
docs/reviews/whole-branch-cloud-sync-codex.md:3848:        playlist_title: meta.playlistTitle ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:3972:  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
docs/reviews/whole-branch-cloud-sync-codex.md:3988:      .is('playlist_title', null)
docs/reviews/whole-branch-cloud-sync-codex.md:3997:  // by playlist_title (nulls last) then created_at — created_at MUST be in the select
docs/reviews/whole-branch-cloud-sync-codex.md:4005:      .order('playlist_title', { nullsFirst: false })
docs/reviews/whole-branch-cloud-sync-codex.md:4073:  private async playlistId(p: Principal): Promise<string | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:4080:    return data?.id ?? null;
docs/reviews/whole-branch-cloud-sync-codex.md:4102:  playlistTitle: string | null;
docs/reviews/whole-branch-cloud-sync-codex.md:4122:   *  ONLY when the row's title is currently null/absent, so it never clobbers a title a
docs/reviews/whole-branch-cloud-sync-codex.md:4127:  /** Cloud-only: list all playlists owned by ownerId, ordered by title (nulls last) then
docs/reviews/whole-branch-cloud-sync-codex.md:4288:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-codex.md:4289:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-codex.md:4296:      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
docs/reviews/whole-branch-cloud-sync-codex.md:4309:      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
docs/reviews/whole-branch-cloud-sync-codex.md:4312:           || jsonb_build_object('summaryMd', jsonb_build_object(
docs/reviews/whole-branch-cloud-sync-codex.md:4313:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-codex.md:4319:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:4321:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-codex.md:4322:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-codex.md:4339:alter table jobs add column playlist_id uuid not null;
docs/reviews/whole-branch-cloud-sync-codex.md:4357:  if auth.uid() is null then raise exception 'not authenticated'; end if;
docs/reviews/whole-branch-cloud-sync-codex.md:4367:    if v_id is not null then return query select v_id, 'queued'::text, false; return; end if;
docs/reviews/whole-branch-cloud-sync-codex.md:4373:    if v_id is not null then
docs/reviews/whole-branch-cloud-sync-codex.md:4409:    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
docs/reviews/whole-branch-cloud-sync-codex.md:4423:  if v_serial is not null then return v_serial; end if;
docs/reviews/whole-branch-cloud-sync-codex.md:4452:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
docs/reviews/whole-branch-cloud-sync-codex.md:4453:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
docs/reviews/whole-branch-cloud-sync-codex.md:4460:      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
docs/reviews/whole-branch-cloud-sync-codex.md:4471:      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
docs/reviews/whole-branch-cloud-sync-codex.md:4474:           || jsonb_build_object('summaryMd', jsonb_build_object(
docs/reviews/whole-branch-cloud-sync-codex.md:4475:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
docs/reviews/whole-branch-cloud-sync-codex.md:4481:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:4483:                                 and v.data->'artifacts'->'summaryMd'->>'key'
docs/reviews/whole-branch-cloud-sync-codex.md:4484:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
docs/reviews/whole-branch-cloud-sync-codex.md:4503:--     non-allowlisted key in p_set (e.g. summaryMd) is silently dropped, never written.
docs/reviews/whole-branch-cloud-sync-codex.md:4545:  day           date        not null,
docs/reviews/whole-branch-cloud-sync-codex.md:4546:  kind          text        not null,   -- e.g. 'release_underflow'
docs/reviews/whole-branch-cloud-sync-codex.md:4547:  expected_amt  int         not null,
docs/reviews/whole-branch-cloud-sync-codex.md:4549:  at            timestamptz not null default now()
docs/reviews/whole-branch-cloud-sync-codex.md:4561:-- direction this whole reserve→release slice exists to prevent. `not null default false` so
docs/reviews/whole-branch-cloud-sync-codex.md:4563:alter table jobs add column ever_metered boolean not null default false;
docs/reviews/whole-branch-cloud-sync-codex.md:4586:  if not found then return null; end if;            -- lost lease
docs/reviews/whole-branch-cloud-sync-codex.md:4595:       locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now(),
docs/reviews/whole-branch-cloud-sync-codex.md:4650:  -- (whole-branch round-2 H-R2-1) → KEEP. attempts=0 subsumes not v_ever_metered; both kept defensively.
docs/reviews/whole-branch-cloud-sync-codex.md:4689:                                                   -- requeue that may have billed (round-2 H-R2-1) → excluded
docs/reviews/whole-branch-cloud-sync-codex.md:4711:alter table serve_model_charge add column reserved_cents int not null default 0 check (reserved_cents >= 0);
docs/reviews/whole-branch-cloud-sync-codex.md:4731:  v_token uuid;                                    -- null unless we reserve
docs/reviews/whole-branch-cloud-sync-codex.md:4733:  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;
docs/reviews/whole-branch-cloud-sync-codex.md:4735:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
docs/reviews/whole-branch-cloud-sync-codex.md:4740:    return query select 'denied'::text, null::uuid; return;
docs/reviews/whole-branch-cloud-sync-codex.md:4797:  summaryMd: string;
docs/reviews/whole-branch-cloud-sync-codex.md:4813:  return { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent: result.mdContent, summaryMd: `${baseName}.md` };
docs/reviews/whole-branch-cloud-sync-codex.md:4816:export function parseFrontmatterField(content: string, key: string): string | null {
docs/reviews/whole-branch-cloud-sync-codex.md:4818:  return match?.[1]?.trim() ?? null;
docs/reviews/whole-branch-cloud-sync-codex.md:4828:export function reconstructVideo(content: string, file: string, mdPath: string): Video | null {
docs/reviews/whole-branch-cloud-sync-codex.md:4830:  if (!videoId) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:4859:  const summaryMd = file;
docs/reviews/whole-branch-cloud-sync-codex.md:4875:    summaryMd,
docs/reviews/whole-branch-cloud-sync-codex.md:4948:  const playlistId = (() => { try { return new URL(playlistUrl).searchParams.get('list'); } catch { return null; } })();
docs/reviews/whole-branch-cloud-sync-codex.md:5020:        summaryMd: `${baseName}.md`,
docs/reviews/whole-branch-cloud-sync-codex.md:5135:  summaryMd: z.string().nullable(),
docs/reviews/whole-branch-cloud-sync-codex.md:5136:  summaryHtml: z.string().nullable().optional(),
docs/reviews/whole-branch-cloud-sync-codex.md:5137:  digDeeperMd: z.string().nullable().optional(),
docs/reviews/whole-branch-cloud-sync-codex.md:5138:  digDeeperHtml: z.string().nullable().optional(),
docs/reviews/whole-branch-cloud-sync-codex.md:5161:  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
docs/reviews/whole-branch-cloud-sync-codex.md:5278:  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
docs/reviews/whole-branch-cloud-sync-codex.md:5306:  if (!video.summaryMd) {
docs/reviews/whole-branch-cloud-sync-codex.md:5311:    const mdPath = path.join(outputFolder, video.summaryMd);
docs/reviews/whole-branch-cloud-sync-codex.md:5333:    // Stage 3 (§5.1/§5.7, former-Blocking §5.3): stamp this regenerated MD as
docs/reviews/whole-branch-cloud-sync-codex.md:5348:      tldr, takeaways, summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-codex.md:5357:      summaryHtml: null,
docs/reviews/whole-branch-cloud-sync-codex.md:5436:  console.log(JSON.stringify(report, null, 2));
docs/reviews/whole-branch-cloud-sync-codex.md:5449:function resolveImport(fromFile: string, spec: string): string | null {
docs/reviews/whole-branch-cloud-sync-codex.md:5454:  else return null;                               // bare package import — not our code
docs/reviews/whole-branch-cloud-sync-codex.md:5461:  return null;
docs/reviews/whole-branch-cloud-sync-codex.md:5569:// GENERATE-FREE LEAF (spec D13/B18c): this module and its entire import graph must never
docs/reviews/whole-branch-cloud-sync-codex.md:5665:   129	 *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
docs/reviews/whole-branch-cloud-sync-codex.md:5670:   134	): Promise<{ position: number; serialNumber: number } | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:5673:   137	  if (idx.videos.some((v) => v.id === video.id)) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:5684:   148	  video: Video, mdBody: string | null,
docs/reviews/whole-branch-cloud-sync-codex.md:5689:   153	  if (video.summaryMd && mdBody != null) {
docs/reviews/whole-branch-cloud-sync-codex.md:5691:   155	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
docs/reviews/whole-branch-cloud-sync-codex.md:5706:   170	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
docs/reviews/whole-branch-cloud-sync-codex.md:5721:   185	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
docs/reviews/whole-branch-cloud-sync-codex.md:5778:   301	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
docs/reviews/whole-branch-cloud-sync-codex.md:5779:   302	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
docs/reviews/whole-branch-cloud-sync-codex.md:5797:   320	  winnerSignals: ClassASignals, winnerMdHash: string | null,
docs/reviews/whole-branch-cloud-sync-codex.md:5855:   378	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
docs/reviews/whole-branch-cloud-sync-codex.md:5858:   381	          const presentIsLocal = lv != null;
docs/reviews/whole-branch-cloud-sync-codex.md:5868:   391	              deriveClassASignals(present, body), body ? mdHash(body) : null,
docs/reviews/whole-branch-cloud-sync-codex.md:5892:   415	        let winnerMdHash: string | null = null;
docs/reviews/whole-branch-cloud-sync-codex.md:5894:   417	        let winnerSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-codex.md:5895:   418	        let loserSide: Side | null = null;
docs/reviews/whole-branch-cloud-sync-codex.md:5937:   105	 *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
docs/reviews/whole-branch-cloud-sync-codex.md:5938:   106	 *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
docs/reviews/whole-branch-cloud-sync-codex.md:5941:   109	  v.summaryHtml = null;
docs/reviews/whole-branch-cloud-sync-codex.md:5942:   110	  v.digDeeperHtml = null;
docs/reviews/whole-branch-cloud-sync-codex.md:5943:   111	  v.digDeeperMd = null;
docs/reviews/whole-branch-cloud-sync-codex.md:5944:   112	  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
docs/reviews/whole-branch-cloud-sync-codex.md:5946:   114	    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
docs/reviews/whole-branch-cloud-sync-codex.md:5961:   245	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
docs/reviews/whole-branch-cloud-sync-codex.md:5967:   251	  if (body == null || !winnerVideo.summaryMd) {
docs/reviews/whole-branch-cloud-sync-codex.md:5971:   255	  const key = winnerVideo.summaryMd;
docs/reviews/whole-branch-cloud-sync-codex.md:5991:   275	    summaryMd: key,
docs/reviews/whole-branch-cloud-sync-codex.md:5993:   277	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:5994:   278	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
docs/reviews/whole-branch-cloud-sync-codex.md:6004:   288	    artifacts: { summaryMd: { key, status: 'promoted' } },
docs/reviews/whole-branch-cloud-sync-codex.md:6189:// fed to generation — NOT a hash of the sourceMd/summaryMd blob KEY (the filename). Guards
docs/reviews/whole-branch-cloud-sync-codex.md:6208:// The MD body fed to generation (the whole file `runHtmlDoc` reads as `video.summaryMd`'s blob).
docs/reviews/whole-branch-cloud-sync-codex.md:6231:    JSON.stringify({ playlistUrl: 'https://x.test/p', outputFolder: dir, videos }, null, 2),
docs/reviews/whole-branch-cloud-sync-codex.md:6240:    overallScore: 4, summaryMd: 'a-title.md',
docs/reviews/whole-branch-cloud-sync-codex.md:6241:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:6285:const roStore: ReadOnlyBlobStore = { get: async () => null };
docs/reviews/whole-branch-cloud-sync-codex.md:6317:    mockReadModelEnvelope.mockResolvedValue(null);
docs/reviews/whole-branch-cloud-sync-codex.md:6352:    mockReadModelEnvelope.mockResolvedValue(null);
docs/reviews/whole-branch-cloud-sync-codex.md:6361:describe('B18c — read-model.ts is a generate-free leaf', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:6373:  /** Resolve an import specifier to a file path, or null for a bare npm package
docs/reviews/whole-branch-cloud-sync-codex.md:6375:  function resolveSpecifier(spec: string, fromFile: string): string | null {
docs/reviews/whole-branch-cloud-sync-codex.md:6378:    return null;
docs/reviews/whole-branch-cloud-sync-codex.md:6381:  function resolveToFile(base: string): string | null {
docs/reviews/whole-branch-cloud-sync-codex.md:6385:    return null;
docs/reviews/whole-branch-cloud-sync-codex.md:6442:/bin/bash -lc "rg -n \"mdHash\\(["'^'"\\n]*(summaryMd|sourceMd|key|filename|file)\" lib tests scripts app types" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-codex.md:6473:  async get(p: Principal, key: string): Promise<Buffer | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:6475:    if (error) return null;   // 404 → null
docs/reviews/whole-branch-cloud-sync-codex.md:6480:    return (await this.get(p, key)) !== null;
docs/reviews/whole-branch-cloud-sync-codex.md:6536:   *  `id === null` and are descended into; file entries (`id !== null`) are collected. */
docs/reviews/whole-branch-cloud-sync-codex.md:6547:        if (entry.id === null) {
docs/reviews/whole-branch-cloud-sync-codex.md:6580:  async get(p: Principal, key: string): Promise<Buffer | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:6582:    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
docs/reviews/whole-branch-cloud-sync-codex.md:6648:  get(p: Principal, key: string): Promise<Buffer | null>;
docs/reviews/whole-branch-cloud-sync-codex.md:6675:/bin/bash -lc "sed -n '1,360p' tests/lib/cloud-sync/sync-run.test.ts 2>/dev/null || true; sed -n '1,360p' tests/integration/cloud-sync/sync-run.int.test.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-codex.md:6715:    // bytes to the local replica (a wrong cloud Principal would read null → empty receiver).
docs/reviews/whole-branch-cloud-sync-codex.md:6717:    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
docs/reviews/whole-branch-cloud-sync-codex.md:6718:    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
docs/reviews/whole-branch-cloud-sync-codex.md:6752:/bin/bash -lc 'rg -n "artifacts|summaryMd|modelJson|sourceMdHash|summaryReady" docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-codex.md:6759:254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
docs/reviews/whole-branch-cloud-sync-codex.md:6764:/bin/bash -lc 'rg -n "copyAdditiveVideo|missing.*blob|shareNeedsOwnerServe|deleteReceiverModel|companion|promoted.*blob|summaryMd.*null|baseline" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-codex.md:6768:tests/lib/cloud-sync/reconcile-class-a.test.ts:52:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:6769:tests/lib/cloud-sync/reconcile-class-a.test.ts:54:    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:6770:tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:6771:tests/lib/cloud-sync/reconcile-class-a.test.ts:62:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
docs/reviews/whole-branch-cloud-sync-codex.md:6773:tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
docs/reviews/whole-branch-cloud-sync-codex.md:6788:tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
docs/reviews/whole-branch-cloud-sync-codex.md:6789:tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-codex.md:6808:tests/lib/cloud-sync/schema.test.ts:8:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:6809:tests/lib/cloud-sync/local-stamping.test.ts:23:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
docs/reviews/whole-branch-cloud-sync-codex.md:6810:tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
docs/reviews/whole-branch-cloud-sync-codex.md:6846:const artifactsOf = (rec: { [k: string]: unknown } | null) =>
docs/reviews/whole-branch-cloud-sync-codex.md:6847:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
docs/reviews/whole-branch-cloud-sync-codex.md:6857:    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
docs/reviews/whole-branch-cloud-sync-codex.md:6905:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:7024:    expect(local?.personalNote == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-codex.md:7025:    expect(cloud?.personalNote == null).toBe(true); // the clear propagated; 'old' not resurrected
docs/reviews/whole-branch-cloud-sync-codex.md:7071:    const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
docs/reviews/whole-branch-cloud-sync-codex.md:7082:  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
docs/reviews/whole-branch-cloud-sync-codex.md:7094:    expect(local?.summaryHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-codex.md:7095:    expect(local?.digDeeperHtml == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-codex.md:7125:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
docs/reviews/whole-branch-cloud-sync-codex.md:7132:    expect(local?.summaryMd == null).toBe(true);
docs/reviews/whole-branch-cloud-sync-codex.md:7142:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:7175:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
docs/reviews/whole-branch-cloud-sync-codex.md:7215:  read(): Promise<string | null>;
docs/reviews/whole-branch-cloud-sync-codex.md:7246:        if (e?.code === 'ENOENT') return null; // no dir yet → no token
docs/reviews/whole-branch-cloud-sync-codex.md:7252:        return (await fs.readFile(file, 'utf8')).trim() || null;
docs/reviews/whole-branch-cloud-sync-codex.md:7254:        if (e?.code === 'ENOENT') return null;
docs/reviews/whole-branch-cloud-sync-codex.md:7295:export async function loadSession(store: TokenStore = fileTokenStore): Promise<Session | null> {
docs/reviews/whole-branch-cloud-sync-codex.md:7297:  if (!refresh) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:7300:  if (error || !data.session) return null;
docs/reviews/whole-branch-cloud-sync-codex.md:7349: *  CRITICAL (Codex Blocking): preserve the RAW outputFolder string — do NOT
docs/reviews/whole-branch-cloud-sync-codex.md:7418:export function getPrincipalFromSession(session: { userId: string | null }, indexKey: string): Principal {
docs/reviews/whole-branch-cloud-sync-codex.md:7462:1. **Blocking**: `lib/cloud-sync/sync-run.ts:407`
docs/reviews/whole-branch-cloud-sync-codex.md:7474:   Scenario: source video has `summaryMd` and `artifacts.summaryMd.status='promoted'`, but the source blob read returns `null` due to storage drift/corruption/RLS miss. `copyAdditiveVideo` skips the blob write because `mdBody == null`, but `sanitizeAdditiveVideo` preserves the sender’s `artifacts.summaryMd`. The receiver row is upserted with a promoted artifact pointing at a missing blob, then the caller writes a baseline.
docs/reviews/whole-branch-cloud-sync-codex.md:7476:   Fix: if `video.summaryMd` is present and `mdBody == null`, either throw and do not advance the baseline, or explicitly clear `summaryMd` and `artifacts.summaryMd` before writing. The post-write verify must check the advertised artifact tuple, not just row presence.
docs/reviews/whole-branch-cloud-sync-codex.md:7492:I also checked the service-role confinement script and targeted cloud-sync tests; they pass. I found no key-hash use of `mdHash(video.summaryMd)` in shipped source.
docs/reviews/whole-branch-cloud-sync-codex.md:7494:**NOT CONVERGED**
docs/reviews/whole-branch-cloud-sync-codex.md:7499:1. **Blocking**: `lib/cloud-sync/sync-run.ts:407`
docs/reviews/whole-branch-cloud-sync-codex.md:7511:   Scenario: source video has `summaryMd` and `artifacts.summaryMd.status='promoted'`, but the source blob read returns `null` due to storage drift/corruption/RLS miss. `copyAdditiveVideo` skips the blob write because `mdBody == null`, but `sanitizeAdditiveVideo` preserves the sender’s `artifacts.summaryMd`. The receiver row is upserted with a promoted artifact pointing at a missing blob, then the caller writes a baseline.
docs/reviews/whole-branch-cloud-sync-codex.md:7513:   Fix: if `video.summaryMd` is present and `mdBody == null`, either throw and do not advance the baseline, or explicitly clear `summaryMd` and `artifacts.summaryMd` before writing. The post-write verify must check the advertised artifact tuple, not just row presence.
docs/reviews/whole-branch-cloud-sync-codex.md:7529:I also checked the service-role confinement script and targeted cloud-sync tests; they pass. I found no key-hash use of `mdHash(video.summaryMd)` in shipped source.
docs/reviews/whole-branch-cloud-sync-codex.md:7531:**NOT CONVERGED**

codex
The broad grep is noisy, but the important signal is narrow: `readMdBody` is only used inside `sync-run.ts`; other blob reads are model/html/dig serving paths rather than sync decisions. I’m now opening the sync modules and storage adapters line-numbered so the final review can cite exact branches.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '1,620p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// lib/cloud-sync/sync-run.ts
     2	//
     3	// Stage 3 Cloud Sync (§7) — the sync-run orchestrator. Composes the reconcile primitives (T1/T5–T9,
     4	// T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
     5	// cloud, one playlist at a time, under an authenticated USER session (never service-role).
     6	//
     7	// Invariants (any violation = money/data bug):
     8	//  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
     9	//    cache (summaryHtml/dig/PDF) copied.
    10	//  - Cloud Principal.id = deps.ownerId (= auth.uid()): Supabase Storage RLS (0007) requires the
    11	//    first object-path segment to equal auth.uid(); the metadata RPCs are owner_id = auth.uid()
    12	//    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
    13	//  - Transfers finalize the receiver record via updateVideoFields (SyncDeps exposes no raw client,
    14	//    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
    15	//    tuple is verified durable — stage → verify → promote → finalize → verify → baseline (F2).
    16	//  - Class B is reconciled BEFORE Class A (Class A consumes the reconciled corrections hash);
    17	//    a Class-B loser write is asserted to have landed (found:true) or it throws (F3).
    18	
    19	import { promises as fs } from 'fs';
    20	import path from 'path';
    21	import type { MetadataStore } from '@/lib/storage/metadata-store';
    22	import type { BlobStore } from '@/lib/storage/blob-store';
    23	import type { Principal } from '@/lib/storage/principal';
    24	import { localPrincipal } from '@/lib/storage/principal';
    25	import type { Video } from '@/types';
    26	import { deriveClassASignals, deriveHumanSnapshot } from './backfill';
    27	import { reconcileHuman, type FieldMerge } from './reconcile-class-b';
    28	import { reconcileClassA } from './reconcile-class-a';
    29	import { decideCompanion } from './companion';
    30	import {
    31	  readManifest, writeVideoBaseline, appendConflict, resetConflictDedup,
    32	} from './manifest';
    33	import { discoverLocalPlaylists, unionPlaylistKeys, type LocalPlaylist } from './registry';
    34	import { mdHash } from './content-hash';
    35	import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
    36	import type { PlaylistSummary } from '@/lib/storage/metadata-store';
    37	import type { ClassASignals, HumanField, HumanSnapshot, VideoBaseline } from './types';
    38	
    39	export interface SyncDeps {
    40	  local: MetadataStore; cloud: MetadataStore;
    41	  localBlob: BlobStore; cloudBlob: BlobStore;
    42	  dataRoots: string[]; ownerId: string;
    43	}
    44	
    45	export interface SyncReport {
    46	  created: number; updatedLocal: number; updatedCloud: number; skippedIdentical: number;
    47	  mergedFields: number; conflictsLogged: number; removed: number;
    48	  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
    49	  errors: { videoId: string; message: string }[];
    50	}
    51	
    52	const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
    53	const EMPTY_CLASSB = {} as VideoBaseline['classB'];
    54	
    55	/** One replica's write surface for a video (store + its principal + its blob store). */
    56	interface Side { store: MetadataStore; p: Principal; blob: BlobStore; }
    57	
    58	/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
    59	async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
    60	  if (!video.summaryMd) return null;
    61	  const buf = await blob.get(p, video.summaryMd);
    62	  return buf ? buf.toString('utf8') : null;
    63	}
    64	
    65	/** Union of video ids across both replicas' indexes. */
    66	async function enumerateVideoIds(
    67	  local: MetadataStore, cloud: MetadataStore, localP: Principal, cloudP: Principal,
    68	): Promise<string[]> {
    69	  const [l, c] = await Promise.all([local.readIndex(localP), cloud.readIndex(cloudP)]);
    70	  return [...new Set([...l.videos.map((v) => v.id), ...c.videos.map((v) => v.id)])];
    71	}
    72	
    73	/** Read one video record (or null if absent) from a store's index. */
    74	async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
    75	  const idx = await store.readIndex(p);
    76	  return idx.videos.find((v) => v.id === id) ?? null;
    77	}
    78	
    79	/** Deterministic local root for a cloud-only playlist (fresh-device hydrate target). */
    80	function hydrationRoot(dataRoots: string[], key: string): string {
    81	  return path.join(dataRoots[0], key);
    82	}
    83	
    84	/** mkdir -p the playlist's local root BEFORE any local read/write (round-5 H1). On a fresh device a
    85	 *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
    86	 *  the empty-index sentinel only when the dir exists but the file is absent), and setPlaylistMeta/
    87	 *  writeIndex ENOENT into a missing parent. */
    88	async function ensureHydrationRoot(dataRoot: string): Promise<void> {
    89	  await fs.mkdir(dataRoot, { recursive: true });
    90	}
    91	
    92	/** Resolve the playlist url/title for `key` from whichever registry holds it. */
    93	function playlistMetaFor(
    94	  key: string, localPlaylists: LocalPlaylist[], cloudSummaries: PlaylistSummary[],
    95	): { playlistUrl: string; playlistTitle?: string } {
    96	  const lp = localPlaylists.find((l) => l.playlistKey === key);
    97	  if (lp) return { playlistUrl: lp.playlistUrl };
    98	  const cp = cloudSummaries.find((c) => c.playlistKey === key);
    99	  if (cp) return { playlistUrl: cp.playlistUrl, ...(cp.playlistTitle ? { playlistTitle: cp.playlistTitle } : {}) };
   100	  return { playlistUrl: '' };
   101	}
   102	
   103	/** Behavior #3 (money-safe) — strip regenerable cache + out-of-scope pointers so the receiver never
   104	 *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
   105	 *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
   106	 *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
   107	function sanitizeAdditiveVideo(video: Video): Video {
   108	  const v: any = { ...video };
   109	  v.summaryHtml = null;
   110	  v.digDeeperHtml = null;
   111	  v.digDeeperMd = null;
   112	  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
   113	  if (v.artifacts && typeof v.artifacts === 'object') {
   114	    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
   115	  }
   116	  // Replica-local ordering is NOT synced (§4.1) — the receiver's claim supplies its own.
   117	  delete v.serialNumber;
   118	  delete v.playlistIndex;
   119	  delete v.removedFromPlaylist;
   120	  // DB-computed read-only fields must never round-trip into a write.
   121	  delete v.updatedAt;
   122	  delete v.summaryReady;
   123	  return v as Video;
   124	}
   125	
   126	/** round-4 H1 — create the receiver playlist + reservation row BEFORE any receiver write. The cloud
   127	 *  upsertVideo/updateVideoFields are bare UPDATEs of a row pre-created by claimVideoSlot: they
   128	 *  silently affect 0 rows (no throw) on an absent row, so an additive create must claim the slot
   129	 *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
   130	 *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
   131	async function ensureReceiverSlot(
   132	  to: MetadataStore, toP: Principal,
   133	  playlistMeta: { playlistUrl: string; playlistTitle?: string }, video: Video,
   134	): Promise<{ position: number; serialNumber: number } | null> {
   135	  await to.setPlaylistMeta(toP, playlistMeta);
   136	  const idx = await to.readIndex(toP);
   137	  if (idx.videos.some((v) => v.id === video.id)) return null;
   138	  return to.claimVideoSlot(toP, video.id);
   139	}
   140	
   141	/** Behavior #3 (money-safe) — additive create of a one-sided video onto the receiver. Order:
   142	 *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
   143	 *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
   144	 *  never copies regenerable cache. */
   145	async function copyAdditiveVideo(
   146	  to: MetadataStore, toP: Principal, toBlob: BlobStore,
   147	  playlistMeta: { playlistUrl: string; playlistTitle?: string },
   148	  video: Video, mdBody: string | null,
   149	): Promise<void> {
   150	  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
   151	  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
   152	  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
   153	  // strand the receiver with a servable-looking row backed by nothing.
   154	  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
   155	  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
   156	  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
   157	  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
   158	  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
   159	  // partial state is ever created, so there is nothing to roll back.
   160	  if (video.summaryMd && mdBody == null) {
   161	    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
   162	  }
   163	
   164	  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
   165	
   166	  let wroteBlob = false;
   167	  if (video.summaryMd && mdBody != null) {
   168	    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
   169	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
   170	    const staged = await toBlob.get(toP, ref.tempKey);
   171	    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
   172	      throw new Error(`additive staged MD verify failed for ${video.id}`);
   173	    }
   174	    await toBlob.promote(ref);
   175	    wroteBlob = true;
   176	  }
   177	
   178	  const sanitized: any = sanitizeAdditiveVideo(video);
   179	  if (slot) {
   180	    sanitized.serialNumber = slot.serialNumber;
   181	    sanitized.playlistIndex = slot.position + 1;
   182	  }
   183	  if (wroteBlob) {
   184	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
   185	  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
   186	    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
   187	    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
   188	    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
   189	    delete sanitized.artifacts.summaryMd;
   190	  }
   191	  await to.upsertVideo(toP, sanitized as Video);
   192	
   193	  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
   194	  // (an update against an absent row silently no-ops; never advance a baseline for that).
   195	  const after = await to.readIndex(toP);
   196	  const rec = after.videos.find((v) => v.id === video.id);
   197	  if (!rec) {
   198	    throw new Error(`additive create did not persist receiver row for ${video.id}`);
   199	  }
   200	  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
   201	  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
   202	  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
   203	  if (wroteBlob) {
   204	    const art = (rec as any).artifacts?.summaryMd;
   205	    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
   206	      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
   207	    }
   208	  }
   209	}
   210	
   211	/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
   212	 *  side's values, so this is a true agreed baseline. */
   213	function baselineFromOneSided(
   214	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
   215	): VideoBaseline {
   216	  const classB = {} as VideoBaseline['classB'];
   217	  for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
   218	  return {
   219	    classA: {
   220	      docVersionMajor: classA.docVersionMajor,
   221	      mdGeneratedAt: classA.mdGeneratedAt,
   222	      mdCorrectionsHash: classA.mdCorrectionsHash,
   223	      mdHash: mdHashVal,
   224	    },
   225	    classB,
   226	  };
   227	}
   228	
   229	/** Behaviors #12 + F3 — apply each Class-B winner to the LOSER side, carrying the SOURCE timestamp
   230	 *  (never now()). A conflict is logged and, when the merge picked no winner (winner==='equal'), the
   231	 *  loser value is skipped (not written). Every write MUST land (found:true) or it throws — a no-op
   232	 *  write on an absent row would let buildBaseline record a false agreement. */
   233	async function applyClassBWinners(args: {
   234	  deps: SyncDeps; localP: Principal; cloudP: Principal; videoId: string;
   235	  merges: Record<HumanField, FieldMerge>; localSnap: HumanSnapshot; cloudSnap: HumanSnapshot;
   236	  dataRoot: string; key: string;
   237	}): Promise<{ merged: number; conflicts: number }> {
   238	  const { deps, localP, cloudP, videoId, merges, localSnap, cloudSnap, dataRoot, key } = args;
   239	  let merged = 0;
   240	  let conflicts = 0;
   241	
   242	  for (const f of FIELDS) {
   243	    const m = merges[f];
   244	    if (m.conflict) {
   245	      await appendConflict(dataRoot, key, {
   246	        video_id: videoId, class: 'B', field: f,
   247	        valueL: localSnap[f].value, valueR: cloudSnap[f].value,
   248	        reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
   249	      });
   250	      conflicts += 1;
   251	    }
   252	    if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write
   253	
   254	    // winner is on one side → the OTHER (loser) side receives the winning value.
   255	    const target: Side = m.winner === 'local'
   256	      ? { store: deps.cloud, p: cloudP, blob: deps.cloudBlob }
   257	      : { store: deps.local, p: localP, blob: deps.localBlob };
   258	    const set: Record<string, string | number> = {};
   259	    const clear: HumanField[] = [];
   260	    if (m.value === undefined) clear.push(f);
   261	    else set[f] = m.value;
   262	
   263	    const { found } = await target.store.updateVideoAnnotations(
   264	      target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
   265	    );
   266	    if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
   267	    merged += 1;
   268	  }
   269	  return { merged, conflicts };
   270	}
   271	
   272	/** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
   273	 *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
   274	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
   275	 *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
   276	async function transferClassA(
   277	  winner: Side, loser: Side, winnerVideo: Video, videoId: string,
   278	): Promise<{ mdHash: string; verified: boolean }> {
   279	  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   280	  if (body == null || !winnerVideo.summaryMd) {
   281	    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   282	  }
   283	  const h = mdHash(body);
   284	  const key = winnerVideo.summaryMd;
   285	
   286	  const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   287	  const staged = await loser.blob.get(loser.p, ref.tempKey);
   288	  if (!staged || mdHash(staged.toString('utf8')) !== h) {
   289	    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   290	  }
   291	  // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   292	  // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   293	  // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   294	  // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   295	  // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   296	  // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   297	  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   298	  // (below) advertises promoted only after this resolves.
   299	  await loser.blob.put(loser.p, key, staged, 'text/markdown');
   300	  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
   301	
   302	  const wv: any = winnerVideo;
   303	  const completeTuple: any = {
   304	    summaryMd: key,
   305	    docVersion: wv.docVersion,
   306	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
   307	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
   308	    ratings: wv.ratings,
   309	    overallScore: wv.overallScore,
   310	    videoType: wv.videoType,
   311	    audience: wv.audience,
   312	    tags: wv.tags,
   313	    tldr: wv.tldr,
   314	    takeaways: wv.takeaways,
   315	    // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
   316	    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
   317	    // the serve path (buildDocHtml/ensureHtmlDoc) checks generator-version, NOT MD-body freshness, so a
   318	    // same-format prose change (the recency-tiebreak case) would serve stale HTML indefinitely (§5.1
   319	    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
   320	    // readIndex reads falsy → forces re-render.
   321	    //
   322	    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
   323	    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
   324	    // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
   325	    // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
   326	    // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
   327	    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
   328	    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
   329	    // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
   330	    // whereas transferClassA PATCHES a row that already holds its own state.
   331	    summaryHtml: null,
   332	    digDeeperHtml: null,
   333	    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
   334	    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
   335	    artifacts: { summaryMd: { key, status: 'promoted' } },
   336	  };
   337	  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
   338	
   339	  return { mdHash: h, verified: true };
   340	}
   341	
   342	/** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
   343	 *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
   344	 *  that the owner must re-serve to regenerate the share model. */
   345	async function companionTransfer(
   346	  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
   347	): Promise<{ shareNeedsOwnerServe: boolean }> {
   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   349	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   350	  const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
   351	  const decision = decideCompanion({ winnerMdHash, senderEnvelope });
   352	  if (decision.kind === 'ship') {
   353	    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
   354	    return { shareNeedsOwnerServe: false };
   355	  }
   356	  // deleteReceiverModel — best-effort; a missing model blob is not an error.
   357	  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   358	  return { shareNeedsOwnerServe: true };
   359	}
   360	
   361	/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
   362	 *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
   363	 *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
   364	 *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
   365	 *  recording the winner there would be a false agreement → next-run silent overwrite). */
   366	function buildClassBBaseline(
   367	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   368	): VideoBaseline['classB'] {
   369	  const classB = {} as VideoBaseline['classB'];
   370	  for (const f of FIELDS) {
   371	    const m = merges[f];
   372	    if (m.winner === 'equal' && m.conflict) {
   373	      classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
   374	    } else {
   375	      classB[f] = { value: m.value, editedAt: m.editedAt };
   376	    }
   377	  }
   378	  return classB;
   379	}
   380	
   381	function buildBaseline(
   382	  winnerSignals: ClassASignals, winnerMdHash: string | null,
   383	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   384	): VideoBaseline {
   385	  return {
   386	    classA: {
   387	      docVersionMajor: winnerSignals.docVersionMajor,
   388	      mdGeneratedAt: winnerSignals.mdGeneratedAt,
   389	      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
   390	      mdHash: winnerMdHash,
   391	    },
   392	    classB: buildClassBBaseline(merges, previousBaseline),
   393	  };
   394	}
   395	
   396	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
   397	 *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
   398	 *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
   399	 *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
   400	 *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
   401	 *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
   402	 *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
   403	function buildCorrectionsUnresolvedBaseline(
   404	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   405	): VideoBaseline {
   406	  return {
   407	    classA: previousBaseline?.classA
   408	      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
   409	    classB: buildClassBBaseline(merges, previousBaseline),
   410	  };
   411	}
   412	
   413	export async function runSync(
   414	  deps: SyncDeps, opts: { playlistKey?: string } = {},
   415	): Promise<SyncReport> {
   416	  resetConflictDedup();
   417	  const report: SyncReport = {
   418	    created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
   419	    mergedFields: 0, conflictsLogged: 0, removed: 0,
   420	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   421	  };
   422	
   423	  const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   424	  const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   425	  const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   426	  let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   427	  if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
   428	
   429	  for (const key of keys) {
   430	    const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
   431	      ?? hydrationRoot(deps.dataRoots, key);
   432	    await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
   433	
   434	    const localP = localPrincipal(dataRoot);
   435	    const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
   436	    const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
   437	    const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
   438	    const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
   439	    const manifest = await readManifest(dataRoot, key);
   440	
   441	    for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
   442	      try {
   443	        const lv = await readVideo(deps.local, localP, id);
   444	        const cv = await readVideo(deps.cloud, cloudP, id);
   445	        const base = manifest.videos[id];
   446	
   447	        // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
   448	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
   449	        if (!lv || !cv) {
   450	          const present = (lv ?? cv)!;
   451	          const presentIsLocal = lv != null;
   452	          if (base) {
   453	            report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
   454	          } else {
   455	            const from: Side = presentIsLocal ? localSide : cloudSide;
   456	            const to: Side = presentIsLocal ? cloudSide : localSide;
   457	            const body = await readMdBody(from.blob, from.p, present);
   458	            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
   459	            report.created += 1; // reached only after the receiver row is confirmed
   460	            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
   461	              deriveClassASignals(present, body), body ? mdHash(body) : null,
   462	              deriveHumanSnapshot(present),
   463	            ));
   464	          }
   465	          continue;
   466	        }
   467	
   468	        // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
   469	        const localSnap = deriveHumanSnapshot(lv);
   470	        const cloudSnap = deriveHumanSnapshot(cv);
   471	        const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
   472	        const applied = await applyClassBWinners({
   473	          deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
   474	        });
   475	        report.mergedFields += applied.merged;
   476	        report.conflictsLogged += applied.conflicts;
   477	        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
   478	
   479	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
   480	        //    Class B logs+skips, §5.5). Its value is NOT a settled winner, so it must NOT drive a
   481	        //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
   482	        //    and copy its MD body over the loser's (different-correction) body — DESTROYING the loser's
   483	        //    corrected MD and recording a false agreement (sticky: the copied bodies then match forever).
   484	        //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
   485	        //    Class A (so the next run re-evaluates once the human resolves corrections). The video stays
   486	        //    "seen" for delete-inference (baseline present).
   487	        //
   488	        //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
   489	        //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
   490	        //    behavior. Bodies are needed for hashing regardless — Behavior #1.
   491	        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
   492	        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
   493	
   494	        // ── B1 (round 3) — the two-sided counterpart of copyAdditiveVideo's WB-H1/H-R2-1 guard (:160).
   495	        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
   496	        //    or it advertises one whose bytes could not be READ. The backends disagree on which errors
   497	        //    are which: local get throws on anything but ENOENT, but the Supabase get is `if (error)
   498	        //    return null` — it swallows EVERY failure (network, 5xx, timeout, RLS denial), so on the
   499	        //    cloud side an ordinary transient download error is indistinguishable from "no MD".
   500	        //    deriveClassASignals maps a null body to mdHash: null, and reconcileClassA reads
   501	        //    mdHash == null as "this side HAS NO MD" (:21-23) — and those presence branches return
   502	        //    BEFORE the corrections-currency and never-downgrade-format ladder (:38-46). So an
   503	        //    unreadable body made the other replica's body get copied over it (destroying it) and
   504	        //    recorded a full-agreement baseline; run 2 then saw identical bodies and skipped, making
   505	        //    the loss permanent and recoverable only by paid regeneration.
   506	        //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
   507	        //    so the run heals by itself once the body is readable. With this guard reconcileClassA's
   508	        //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
   509	        //    which is exactly M-R2-2's "purely additive hydration", so its intent is preserved.
   510	        if (lv.summaryMd && la.mdHash == null) throw new Error(`local MD body unreadable for ${id}`);
   511	        if (cv.summaryMd && ca.mdHash == null) throw new Error(`cloud MD body unreadable for ${id}`);
   512	
   513	        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
   514	        //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
   515	        //    nothing can be destroyed and no false agreement about competing bodies is possible — so
   516	        //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
   517	        //    corrections). The corrections conflict is still logged by Class B and still flags
   518	        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
   519	        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
   520	        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
   521	          report.needsRegen += 1;
   522	          if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   523	          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
   524	          continue;
   525	        }
   526	
   527	        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
   528	        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
   529	        if (decision.needsRegen) report.needsRegen += 1;
   530	
   531	        let winnerMdHash: string | null = null;
   532	        let winnerSignals: ClassASignals = la;
   533	        let winnerSide: Side | null = null;
   534	        let loserSide: Side | null = null;
   535	        let winnerVideo: Video = lv;
   536	
   537	        if (decision.action === 'copyToCloud') {
   538	          winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
   539	          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
   540	          report.updatedCloud += 1;
   541	        } else if (decision.action === 'copyToLocal') {
   542	          winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
   543	          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
   544	          report.updatedLocal += 1;
   545	        } else {
   546	          report.skippedIdentical += 1;
   547	          winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
   548	        }
   549	
   550	        if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
   551	          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
   552	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
   553	        }
   554	        if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   555	
   556	        // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
   557	        //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
   558	        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
   559	      } catch (e: any) {
   560	        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
   561	      }
   562	    }
   563	  }
   564	
   565	  return report;
   566	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/companion.ts lib/cloud-sync/reconcile-class-a.ts lib/cloud-sync/reconcile-class-b.ts lib/cloud-sync/backfill.ts lib/cloud-sync/manifest.ts lib/cloud-sync/types.ts | sed -n '1,500p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc "nl -ba lib/storage/local/local-metadata-store.ts lib/storage/local/local-blob-store.ts lib/storage/supabase/supabase-metadata-store.ts lib/storage/supabase/supabase-blob-store.ts | sed -n '1,520p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

codex
The line-numbered multi-file command hit a BSD `nl` usage limit, so I’m splitting those reads. The first full `sync-run.ts` pass shows the B1 guard sits after both side bodies are read and before both the unresolved-corrections skip and `reconcileClassA`, which is the critical ordering.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/companion.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { ModelEnvelope } from '@/lib/html-doc/model-store';
     2	
     3	export type CompanionAction =
     4	  | { kind: 'ship'; envelope: ModelEnvelope }
     5	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };
     6	
     7	/** Ship the sender's model iff it was generated from the winning MD (§4.2). */
     8	export function decideCompanion(args: {
     9	  winnerMdHash: string;
    10	  senderEnvelope: ModelEnvelope | null;
    11	}): CompanionAction {
    12	  const { winnerMdHash, senderEnvelope } = args;
    13	  if (senderEnvelope && senderEnvelope.sourceMdHash === winnerMdHash) {
    14	    return { kind: 'ship', envelope: senderEnvelope };
    15	  }
    16	  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
    17	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/reconcile-class-a.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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

exec
/bin/bash -lc "nl -ba lib/cloud-sync/reconcile-class-b.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
/bin/bash -lc "nl -ba lib/cloud-sync/backfill.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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

exec
/bin/bash -lc "nl -ba lib/cloud-sync/registry.ts | sed -n '1,240p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import { promises as fs } from 'fs';
     2	import path from 'path';
     3	import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
     4	import { localPrincipal } from '@/lib/storage/principal';
     5	
     6	export interface LocalPlaylist { playlistKey: string; dataRoot: string; playlistUrl: string; }
     7	
     8	export function playlistKeyFromUrl(url: string): string | null {
     9	  if (!url) return null;
    10	  try {
    11	    const u = new URL(url);
    12	    return u.searchParams.get('list');
    13	  } catch { return null; }
    14	}
    15	
    16	/** Scan each data root's subdirectories for a playlist-index.json and derive its key. */
    17	export async function discoverLocalPlaylists(dataRoots: string[]): Promise<LocalPlaylist[]> {
    18	  const byKey = new Map<string, LocalPlaylist>();
    19	  for (const root of dataRoots) {
    20	    let entries: string[] = [];
    21	    try { entries = await fs.readdir(root); } catch { continue; }
    22	    for (const dir of entries) {
    23	      const candidate = path.join(root, dir);
    24	      const dataRoot = await resolveRootShape(candidate); // handles <dir> and <dir>/raw
    25	      if (!dataRoot) continue;
    26	      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
    27	      const key = playlistKeyFromUrl(idx.playlistUrl);
    28	      if (!key) continue;
    29	      if (!byKey.has(key)) byKey.set(key, { playlistKey: key, dataRoot, playlistUrl: idx.playlistUrl });
    30	    }
    31	  }
    32	  return [...byKey.values()];
    33	}
    34	
    35	async function resolveRootShape(candidate: string): Promise<string | null> {
    36	  for (const p of [candidate, path.join(candidate, 'raw')]) {
    37	    try { await fs.access(path.join(p, 'playlist-index.json')); return p; } catch { /* try next */ }
    38	  }
    39	  return null;
    40	}
    41	
    42	export function unionPlaylistKeys(local: LocalPlaylist[], cloudKeys: string[]): string[] {
    43	  return [...new Set([...local.map((l) => l.playlistKey), ...cloudKeys])];
    44	}

exec
/bin/bash -lc "nl -ba lib/html-doc/model-store.ts | sed -n '1,160p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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

exec
/bin/bash -lc "nl -ba lib/cloud-sync/manifest.ts | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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
    20	  } catch { /* missing or corrupt → degrade (§8) */ }
    21	  return { version: 1, videos: {} };
    22	}
    23	
    24	async function atomicWrite(file: string, data: string): Promise<void> {
    25	  await fs.mkdir(path.dirname(file), { recursive: true });
    26	  const tmp = `${file}.tmp-${process.pid}`;
    27	  await fs.writeFile(tmp, data, 'utf8');
    28	  await fs.rename(tmp, file);
    29	}
    30	
    31	export async function writeVideoBaseline(
    32	  dataRoot: string, playlistKey: string, videoId: string, baseline: VideoBaseline,
    33	): Promise<void> {
    34	  const m = await readManifest(dataRoot, playlistKey);
    35	  m.videos[videoId] = baseline;
    36	  await atomicWrite(manifestPath(dataRoot, playlistKey), JSON.stringify(m, null, 2));
    37	}
    38	
    39	const seenConflicts = new Set<string>();
    40	export interface ConflictEntry {
    41	  video_id: string; class: 'A' | 'B'; field?: string;
    42	  valueL?: unknown; valueR?: unknown; reason: string;
    43	}
    44	export async function appendConflict(dataRoot: string, playlistKey: string, e: ConflictEntry): Promise<void> {
    45	  // Include playlistKey so the same (video_id, class, field, valueL, valueR) in two playlists
    46	  // within one run is not collapsed to a single entry (L3).
    47	  const key = `${playlistKey}|${e.video_id}|${e.class}|${e.field ?? ''}|${JSON.stringify(e.valueL)}|${JSON.stringify(e.valueR)}`;
    48	  if (seenConflicts.has(key)) return;
    49	  seenConflicts.add(key);
    50	  const file = conflictPath(dataRoot, playlistKey);
    51	  await fs.mkdir(path.dirname(file), { recursive: true });
    52	  await fs.appendFile(file, `${JSON.stringify(e)}\n`, 'utf8');
    53	}
    54	/** Reset the per-run de-dup cache at the start of a sync run. */
    55	export function resetConflictDedup(): void { seenConflicts.clear(); }

exec
/bin/bash -lc "nl -ba lib/storage/blob-store.ts lib/storage/metadata-store.ts | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc "nl -ba lib/storage/local/local-metadata-store.ts | sed -n '1,360p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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

exec
/bin/bash -lc "nl -ba lib/storage/supabase/supabase-metadata-store.ts | sed -n '1,380p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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

exec
/bin/bash -lc "nl -ba lib/storage/supabase/supabase-blob-store.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import crypto from 'crypto';
     2	import type { SupabaseClient } from '@supabase/supabase-js';
     3	import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
     4	import { assertLogicalKey } from '@/lib/storage/blob-store';
     5	import type { Principal } from '@/lib/storage/principal';
     6	
     7	export class SupabaseBlobStore implements BlobStore {
     8	  constructor(private client: SupabaseClient, private bucket: string) {}
     9	
    10	  /** Server-side owner prefix — never a client absolute path. */
    11	  private objectKey(p: Principal, key: string): string {
    12	    assertLogicalKey(key);
    13	    return `${p.id}/${p.indexKey}/${key}`;
    14	  }
    15	
    16	  private b() { return this.client.storage.from(this.bucket); }
    17	
    18	  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    19	    const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
    20	    if (error) throw error;
    21	  }
    22	
    23	  async get(p: Principal, key: string): Promise<Buffer | null> {
    24	    const { data, error } = await this.b().download(this.objectKey(p, key));
    25	    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
    26	    // so a null here does NOT prove the object is absent. Callers that treat "no bytes" as a
    27	    // semantic fact (e.g. "this replica holds no MD") must corroborate it against the record that
    28	    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately
    29	    // left as-is: shared with already-merged read paths where absent-vs-unreadable is immaterial.
    30	    // Note the LOCAL blob store differs — it returns null only on ENOENT and throws otherwise.
    31	    if (error) return null;
    32	    return Buffer.from(await data.arrayBuffer());
    33	  }
    34	
    35	  async exists(p: Principal, key: string): Promise<boolean> {
    36	    return (await this.get(p, key)) !== null;
    37	  }
    38	
    39	  async delete(p: Principal, key: string): Promise<void> {
    40	    const { error } = await this.b().remove([this.objectKey(p, key)]);
    41	    if (error) throw error;
    42	  }
    43	
    44	  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    45	    assertLogicalKey(key); // validate before building tempKey — reject '/absolute' before any upload
    46	    const tempKey = `_staging/${crypto.randomUUID()}/${key}`; // per-attempt-unique (ports local-blob-store)
    47	    await this.put(p, tempKey, bytes, contentType);
    48	    return { principal: p, tempKey, finalKey: key };
    49	  }
    50	
    51	  async promote(ref: StagedRef): Promise<void> {
    52	    const from = this.objectKey(ref.principal, ref.tempKey);
    53	    const to = this.objectKey(ref.principal, ref.finalKey);
    54	    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    55	    if (await this.exists(ref.principal, ref.finalKey)) {
    56	      await this.b().remove([from]).catch(() => {});
    57	      return;
    58	    }
    59	    const { error } = await this.b().move(from, to);
    60	    if (error) {
    61	      // A concurrent promoter (worker job retry / re-run of the same MD key) may have won the race: destination-exists / source-missing.
    62	      // Re-check the final; treat a present final as success, else rethrow.
    63	      if (await this.exists(ref.principal, ref.finalKey)) {
    64	        await this.b().remove([from]).catch(() => {});
    65	        return;
    66	      }
    67	      throw error;
    68	    }
    69	  }
    70	
    71	  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    72	    assertLogicalKey(prefix);
    73	    const root = `${p.id}/${p.indexKey}/${prefix}`.replace(/\/$/, '');
    74	    const objectPaths = await this.collectObjectPaths(root);
    75	    for (let i = 0; i < objectPaths.length; i += 1000) {
    76	      const batch = objectPaths.slice(i, i + 1000);
    77	      const { error } = await this.b().remove(batch);
    78	      if (error) throw error;
    79	    }
    80	  }
    81	
    82	  async list(p: Principal, prefix: string): Promise<string[]> {
    83	    assertLogicalKey(prefix);
    84	    const ownerRoot = `${p.id}/${p.indexKey}/`;
    85	    const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
    86	    const full = await this.collectObjectPaths(dirPath); // returns full object paths (or [] if absent)
    87	    return full.map((f) => f.slice(ownerRoot.length)); // strip owner root → logical key
    88	  }
    89	
    90	  /** Recursively walks a Supabase Storage "directory" (non-recursive `.list`, paginated at
    91	   *  100/page) and returns every file's full object path. Folder entries surface with
    92	   *  `id === null` and are descended into; file entries (`id !== null`) are collected. */
    93	  private async collectObjectPaths(dirPath: string): Promise<string[]> {
    94	    const paths: string[] = [];
    95	    const limit = 100;
    96	    let offset = 0;
    97	    for (;;) {
    98	      const { data, error } = await this.b().list(dirPath, { limit, offset });
    99	      if (error) throw error;
   100	      const entries = data ?? [];
   101	      for (const entry of entries) {
   102	        const entryPath = `${dirPath}/${entry.name}`;
   103	        if (entry.id === null) {
   104	          paths.push(...(await this.collectObjectPaths(entryPath)));
   105	        } else {
   106	          paths.push(entryPath);
   107	        }
   108	      }
   109	      if (entries.length < limit) break;
   110	      offset += limit;
   111	    }
   112	    return paths;
   113	  }
   114	}

exec
/bin/bash -lc "nl -ba lib/storage/local/local-blob-store.ts | sed -n '1,160p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import fs from 'fs'; import path from 'path'; import crypto from 'crypto';
     2	import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
     3	import { assertLogicalKey } from '@/lib/storage/blob-store';
     4	import type { Principal } from '@/lib/storage/principal';
     5	
     6	/** Byte-for-byte the current -data layout: physical path = join(indexKey, key). */
     7	export class LocalFsBlobStore implements BlobStore {
     8	  private abs(p: Principal, key: string): string { assertLogicalKey(key); return path.join(p.indexKey, key); }
     9	
    10	  // contentType unused locally but required by the BlobStore interface (cloud impls will use it)
    11	  async put(p: Principal, key: string, bytes: Buffer, _contentType: string): Promise<void> {
    12	    const dest = this.abs(p, key); fs.mkdirSync(path.dirname(dest), { recursive: true });
    13	    const tmp = dest + '.' + crypto.randomUUID() + '.tmp';
    14	    try { fs.writeFileSync(tmp, bytes); fs.renameSync(tmp, dest); }
    15	    catch (e) { try { fs.unlinkSync(tmp); } catch {} throw e; }
    16	  }
    17	
    18	  async get(p: Principal, key: string): Promise<Buffer | null> {
    19	    try { return fs.readFileSync(this.abs(p, key)); }
    20	    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
    21	  }
    22	
    23	  async exists(p: Principal, key: string): Promise<boolean> {
    24	    try { fs.statSync(this.abs(p, key)); return true; }
    25	    catch (e: any) { if (e.code === 'ENOENT') return false; throw e; }
    26	  }
    27	
    28	  async delete(p: Principal, key: string): Promise<void> {
    29	    try { fs.unlinkSync(this.abs(p, key)); } catch (e: any) { if (e.code !== 'ENOENT') throw e; }
    30	  }
    31	
    32	  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    33	    assertLogicalKey(key);  // validate before building tempKey — a leading '/' on key wouldn't appear on tempKey
    34	    const tempKey = `_staging/${crypto.randomUUID()}/${key}`;
    35	    await this.put(p, tempKey, bytes, contentType);
    36	    return { principal: p, tempKey, finalKey: key };
    37	  }
    38	
    39	  async promote(ref: StagedRef): Promise<void> {
    40	    const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
    41	    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
    42	    fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
    43	  }
    44	
    45	  // '' → path.join(indexKey, '') === indexKey, i.e. the playlist's own index dir (intended
    46	  // target, not above it). force:true makes an absent path a no-op (ENOENT-safe).
    47	  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    48	    assertLogicalKey(prefix);
    49	    await fs.promises.rm(path.join(p.indexKey, prefix), { recursive: true, force: true });
    50	  }
    51	
    52	  async list(p: Principal, prefix: string): Promise<string[]> {
    53	    assertLogicalKey(prefix);
    54	    const root = path.join(p.indexKey, prefix);
    55	    let entries: string[];
    56	    try {
    57	      entries = await fs.promises.readdir(root, { recursive: true }) as string[];
    58	    } catch (e) {
    59	      if ((e as NodeJS.ErrnoException).code === 'ENOENT') return [];
    60	      throw e;
    61	    }
    62	    const out: string[] = [];
    63	    for (const rel of entries) {
    64	      const full = path.join(root, rel);
    65	      if ((await fs.promises.stat(full)).isFile()) {
    66	        out.push(path.posix.join(prefix.replace(/\/$/, ''), rel.split(path.sep).join('/')));
    67	      }
    68	    }
    69	    return out;
    70	  }
    71	}
    72	
    73	export const localBlobStore = new LocalFsBlobStore();

exec
/bin/bash -lc "nl -ba supabase/migrations/0021_* | sed -n '1,360p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
/bin/bash -lc "ls supabase/migrations/*0009* supabase/migrations/*0021* 2>/dev/null && nl -ba supabase/migrations/0009_* | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql
supabase/migrations/0021_cloud_sync_signals.sql
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

exec
/bin/bash -lc 'rg -n "service_role|SUPABASE_SERVICE|spend_ledger|enqueue|producer|reserve|persist_summary|needsRegen|summaryHtml|digDeeperHtml|digDeeperMd" lib/cloud-sync lib/storage/local lib/storage/supabase lib/html-doc lib/dig tests/lib/cloud-sync tests/integration/cloud-sync supabase/migrations/0009_* supabase/migrations/0021_*' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
supabase/migrations/0021_cloud_sync_signals.sql:12:--     defaulted function. (persist_summary keeps its 5-arg signature unchanged → no drop needed.)
supabase/migrations/0021_cloud_sync_signals.sql:72:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0021_cloud_sync_signals.sql:93:grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;
supabase/migrations/0021_cloud_sync_signals.sql:95:-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
supabase/migrations/0021_cloud_sync_signals.sql:99:create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0021_cloud_sync_signals.sql:103:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0021_cloud_sync_signals.sql:106:  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
supabase/migrations/0021_cloud_sync_signals.sql:108:  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
supabase/migrations/0021_cloud_sync_signals.sql:121:           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
supabase/migrations/0021_cloud_sync_signals.sql:138:                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
supabase/migrations/0021_cloud_sync_signals.sql:152:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0021_cloud_sync_signals.sql:154:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0021_cloud_sync_signals.sql:155:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:15:drop function enqueue_job(text,int,text,text,jsonb);
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:16:create function enqueue_job(
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:25:    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:40:        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:45:revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:53:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:60:grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:67:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:79:create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:83:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:90:    raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', p_playlist_id, p_video_id;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:101:revoke all on function reserve_video_slot(uuid,uuid,text) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:102:grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:104:create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:108:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:111:  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:113:  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:126:           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:141:                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:155:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:157:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:158:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
tests/integration/cloud-sync/e2e.int.test.ts:10:// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
tests/integration/cloud-sync/e2e.int.test.ts:129:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:130:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:139:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:228:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:229:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:268:  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
tests/integration/cloud-sync/e2e.int.test.ts:269:  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:273:      summaryHtml: '<html>cached</html>',
tests/integration/cloud-sync/e2e.int.test.ts:274:      digDeeperHtml: '<html>dig</html>',
tests/integration/cloud-sync/e2e.int.test.ts:280:    expect(local?.summaryHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:285:  // ── Row 12 — a backfilled Class-B conflict is preserved across TWO runs (§5.5, round-3 H2).
tests/integration/cloud-sync/e2e.int.test.ts:392:  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
tests/integration/cloud-sync/e2e.int.test.ts:393:  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:411:    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:421:    // Both corrections preserved (neither overwritten).
tests/integration/cloud-sync/e2e.int.test.ts:435:  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
tests/integration/cloud-sync/e2e.int.test.ts:468:  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
tests/integration/cloud-sync/e2e.int.test.ts:469:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:475:      summaryHtml: '<html>STALE rendered from the old local body</html>',
tests/integration/cloud-sync/e2e.int.test.ts:485:    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
tests/integration/cloud-sync/e2e.int.test.ts:489:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
tests/integration/cloud-sync/e2e.int.test.ts:493:  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
tests/integration/cloud-sync/e2e.int.test.ts:494:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
tests/integration/cloud-sync/e2e.int.test.ts:495:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:502:      summaryHtml: '<html>STALE rendered from the old local body</html>',
tests/integration/cloud-sync/e2e.int.test.ts:503:      digDeeperHtml: '<html>STALE dig render</html>',
tests/integration/cloud-sync/e2e.int.test.ts:504:      raw: { digDeeperMd: digKey },
tests/integration/cloud-sync/e2e.int.test.ts:515:    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:516:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:517:    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
tests/integration/cloud-sync/e2e.int.test.ts:523:  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
tests/integration/cloud-sync/e2e.int.test.ts:542:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:545:    // The cloud body is now on local, advertised promoted; both corrections still preserved.
tests/integration/cloud-sync/e2e.int.test.ts:561:  //    surface a per-video error, preserve every byte, and advance NO baseline (so the run heals once
tests/integration/cloud-sync/e2e.int.test.ts:586:      // Local body byte-preserved; cloud body still absent (nothing was written over the gap).
tests/integration/cloud-sync/e2e.int.test.ts:589:      // Both corrections preserved.
lib/dig/dig-section.ts:104:  // Step 11: Update index with digDeeperMd (HTML is rendered fresh by GET)
lib/dig/dig-section.ts:106:    digDeeperMd: digDeeperFilename,
lib/storage/local/local-metadata-store.ts:26:    // reserve the slot with a minimal valid Video; real data arrives via upsertVideo
lib/storage/local/local-metadata-store.ts:38:  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
tests/integration/cloud-sync/stamping.int.test.ts:6:// persist_summary's mdGeneratedAt/mdCorrectionsHash passthrough.
tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
tests/integration/cloud-sync/stamping.int.test.ts:90:  it('persist_summary stamps mdGeneratedAt + mdCorrectionsHash', async () => {
lib/storage/supabase/supabase-job-queue.ts:21:   * on the caller's session client — this method MUST NOT be called on a service_role-constructed
lib/storage/supabase/supabase-job-queue.ts:22:   * SupabaseJobQueue (service_role bypasses RLS and would leak cross-owner rows).
lib/dig/generate.ts:125:   *  the local dig-section path, which never reserves/releases a spend_ledger entry. */
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
lib/cloud-sync/sync-run.ts:14://    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:104: *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
lib/cloud-sync/sync-run.ts:109:  v.summaryHtml = null;
lib/cloud-sync/sync-run.ts:110:  v.digDeeperHtml = null;
lib/cloud-sync/sync-run.ts:111:  v.digDeeperMd = null;
lib/cloud-sync/sync-run.ts:143: *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
lib/cloud-sync/sync-run.ts:297:  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
lib/cloud-sync/sync-run.ts:316:    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
lib/cloud-sync/sync-run.ts:322:    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
lib/cloud-sync/sync-run.ts:323:    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
lib/cloud-sync/sync-run.ts:327:    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
lib/cloud-sync/sync-run.ts:331:    summaryHtml: null,
lib/cloud-sync/sync-run.ts:332:    digDeeperHtml: null,
lib/cloud-sync/sync-run.ts:398: *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
lib/cloud-sync/sync-run.ts:402: *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:509:        //    which is exactly M-R2-2's "purely additive hydration", so its intent is preserved.
lib/cloud-sync/sync-run.ts:518:        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
lib/cloud-sync/sync-run.ts:521:          report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:529:        if (decision.needsRegen) report.needsRegen += 1;
lib/html-doc/generate.ts:48:  // re-render is gated on summaryHtml (set only on full success), and a retry overwrites it atomically.
lib/html-doc/generate.ts:72:    await store.updateVideoFields(principal, videoId, { summaryHtml: htmlFilename });
tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
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
lib/html-doc/ensure.ts:16: * cheap re-render; no HTML yet → full build; already current → nothing. Leaves summaryHtml + docVersion
lib/html-doc/ensure.ts:54:  } else if (!video.summaryHtml) {
lib/html-doc/read-model.ts:28: *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call). */
lib/html-doc/read-model.ts:43: *  coherent to render against current markdown. Never reserves/generates (pure blob read). */
lib/storage/supabase/supabase-metadata-store.ts:171:  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
tests/lib/cloud-sync/regenerate-stamp.test.ts:5:// that persists refreshed tldr/takeaways/summaryHtml — also stamps mdGeneratedAt and
tests/lib/cloud-sync/import-guard.test.ts:34:    /SUPABASE_SERVICE_ROLE_KEY/,        // literal env var name — any reference
tests/lib/cloud-sync/import-guard.test.ts:36:    /createServiceClient\s*\(/,         // the service_role client constructor
tests/lib/cloud-sync/import-guard.test.ts:37:    importOf('@/lib/supabase/service'), // module that builds the service_role client
tests/lib/cloud-sync/import-guard.test.ts:57:        src: `const key = process.env.SUPABASE_SERVICE_ROLE_KEY;`,
tests/lib/cloud-sync/import-guard.test.ts:58:        re: /SUPABASE_SERVICE_ROLE_KEY/,
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
lib/html-doc/serve-doc.ts:57:  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
lib/html-doc/serve-doc.ts:59:  // Absent / drifted / stale-version → materialize under the reserve RPC.
lib/html-doc/serve-doc.ts:60:  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
lib/html-doc/serve-doc.ts:65:  const reserveStatus = row?.status;
lib/html-doc/serve-doc.ts:67:  switch (reserveStatus) {
lib/html-doc/serve-doc.ts:83:    case 'reserved': break;
lib/html-doc/serve-doc.ts:84:    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
lib/html-doc/serve-doc.ts:90:  // (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).
lib/dig/cloud/resolve-summary-key.ts:10: *  gate: it enqueues a dig job only when `loadSummaryForServe` reports the summary promoted, so by
lib/html-doc/parse.ts:45:  // preserved verbatim in prose. The first chunk (before any ##) is preamble — discarded.
lib/html-doc/parse.ts:79:      // OUTSIDE a fence — fenced content is preserved verbatim.
lib/dig/companion-doc.ts:6: * frontmatter entry in place; all other sections are preserved.
lib/dig/companion-doc.ts:510: * - Preserves all other sections.
lib/html-doc/dig-merge.ts:181:  // Preserve deterministic order: pre-orphans (extras from step-1 build) come last,
lib/dig/cloud/dig-blob-key.ts:5: *  distinct jobs_idem_active slot (which includes job_version), permitting a legit re-enqueue. */
lib/html-doc/nav.ts:531:  try { data = (await resp.json()) as { status?: string }; } catch { /* treat as enqueued */ }
lib/dig/cloud/load-dig-for-serve.ts:18: * resolveMagazineModel / reserve_serve_model (spec §2 money invariant).
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
lib/html-doc/build-doc-html.ts:41:    const htmlFile = video.summaryHtml;
lib/html-doc/build-doc-html.ts:43:    // Preserve the stronger htmls/*.html guard (regex + htmlDir containment).
lib/html-doc/build-doc-html.ts:75:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:77:      digDeeperPath = assertIndexRelPathWithin(outputFolder, video.digDeeperMd);
lib/html-doc/build-doc-html.ts:86:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:87:    const digRel = video.digDeeperMd;
lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };

codex
I’m checking the database adapter and migrations against the sync invariants now. The main backend asymmetry that matters for B1 is confirmed: metadata reads throw on query errors, while Supabase blob `get` returns `null` for any download error, so only blob-body callers need extra semantic checks.
exec
/bin/bash -lc "nl -ba tests/integration/cloud-sync/e2e.int.test.ts | sed -n '1,660p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// tests/integration/cloud-sync/e2e.int.test.ts
     2	//
     3	// Stage 3 Cloud Sync (§10), Task 14 — the end-to-end keystone. One `it(...)` per §10 scenario,
     4	// driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
     5	// USER session (never service-role). Where Task 12 proved the additive hydrate path, rows 1/2/7
     6	// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
     7	// MD bodies — the winner-copy path the Task-12 tests never exercised.
     8	//
     9	// Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
    10	// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
    11	import { promises as fs } from 'fs';
    12	import os from 'os';
    13	import path from 'path';
    14	import { randomUUID } from 'crypto';
    15	import {
    16	  makeOwnerContext, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
    17	  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, type Ctx,
    18	} from '@/tests/integration/helpers/cloud';
    19	import { runSync } from '@/lib/cloud-sync/sync-run';
    20	import { mdHash } from '@/lib/cloud-sync/content-hash';
    21	import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
    22	import type { VideoBaseline } from '@/lib/cloud-sync/types';
    23	
    24	afterAll(async () => {
    25	  const home = os.homedir();
    26	  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
    27	  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
    28	});
    29	
    30	const key = (ctx: Ctx) => `${ctx.videoId}.md`;
    31	/** `artifacts` lives in the videos.data jsonb but is not on the Video Zod type — read it via a cast. */
    32	const artifactsOf = (rec: { [k: string]: unknown } | null) =>
    33	  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
    34	/** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
    35	const bodyHash = (b: string) => mdHash(b);
    36	/** mdCorrectionsHash value that makes a side "corrections-current" when NO corrections exist:
    37	 *  reconciledCorrectionsHash === mdHash(String(undefined ?? '')) === mdHash(''). */
    38	const H_NO_CORRECTIONS = mdHash('');
    39	
    40	/** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
    41	function baseline(classB: VideoBaseline['classB']): VideoBaseline {
    42	  return {
    43	    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
    44	    classB,
    45	  };
    46	}
    47	const EMPTY_CLASSB = {
    48	  personalNote: { value: undefined, editedAt: undefined },
    49	  personalScore: { value: undefined, editedAt: undefined },
    50	  corrections: { value: undefined, editedAt: undefined },
    51	} as VideoBaseline['classB'];
    52	
    53	describe('cloud-sync §10 end-to-end scenarios', () => {
    54	  // ── Row 1 — Class-A anti-recency: higher-major MD beats a NEWER-timestamp lower-major MD.
    55	  //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
    56	  it('row 1: higher-major MD beats a newer lower-major (format beats recency); receiver copies it', async () => {
    57	    const ctx = await makeOwnerContext();
    58	    const bodyHi = '# HiMajor\n\nformat-3 content\n';   // local, docVersion.major=3, OLD timestamp
    59	    const bodyLo = '# LoMajor\n\nformat-1 content\n';   // cloud, docVersion.major=1, NEWER timestamp
    60	    const winnerRatings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 };
    61	    await seedLocalVideoFull(ctx, {
    62	      mdBody: bodyHi, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2020-01-01T00:00:00.000Z',
    63	      mdCorrectionsHash: H_NO_CORRECTIONS, ratings: winnerRatings, overallScore: 3,
    64	      tldr: 'the-tldr', takeaways: ['a', 'b'], tags: ['x', 'y'],
    65	    });
    66	    await seedCloudVideo(ctx, {
    67	      mdBody: bodyLo, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2026-06-01T00:00:00.000Z',
    68	      mdCorrectionsHash: H_NO_CORRECTIONS,
    69	    });
    70	    const spendBefore = await ctx.spendLedgerTotal();
    71	
    72	    const report = await runSync(ctx.syncDeps());
    73	
    74	    expect(report.updatedCloud).toBeGreaterThanOrEqual(1);
    75	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges
    76	
    77	    // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
    78	    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
    79	    expect(cloudBody).not.toBeNull();
    80	    expect(cloudBody!.toString('utf8')).toBe(bodyHi);
    81	    expect(bodyHash(cloudBody!.toString('utf8'))).toBe(bodyHash(bodyHi));
    82	
    83	    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
    84	    const cloud = await cloudVideoRecord(ctx);
    85	    expect(cloud?.docVersion?.major).toBe(3);
    86	    expect(cloud?.ratings).toEqual(winnerRatings);
    87	    expect(cloud?.overallScore).toBe(3);
    88	    expect(cloud?.tldr).toBe('the-tldr');
    89	    expect(cloud?.takeaways).toEqual(['a', 'b']);
    90	    expect(cloud?.tags).toEqual(['x', 'y']);
    91	    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
    92	  });
    93	
    94	  // ── Row 2 — corrections-current lower-major MD survives over a corrections-STALE higher-major MD.
    95	  //    Currency beats format → the corrections-current body lands on BOTH sides.
    96	  //    Winner is the CLOUD side here → copyToLocal, exercising the local-overwrite transfer direction.
    97	  it('row 2: corrections-current lower-major beats stale higher-major (currency beats format)', async () => {
    98	    const ctx = await makeOwnerContext();
    99	    const bodyCurrent = '# CurrentCorrections\n\nlower-major but corrections-current\n'; // cloud (winner)
   100	    const bodyStale = '# StaleHiMajor\n\nhigher-major but corrections-stale\n';          // local (loser)
   101	    const winnerRatings = { usefulness: 5, depth: 3, originality: 2, recency: 4, completeness: 1 };
   102	    const editedAt = '2025-06-01T00:00:00.000Z';
   103	    await seedCloudVideo(ctx, {
   104	      mdBody: bodyCurrent, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2025-01-01T00:00:00.000Z',
   105	      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
   106	      mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
   107	      ratings: winnerRatings, tldr: 'keep-me', takeaways: ['k1'], tags: ['t1'],
   108	    });
   109	    await seedLocalVideoFull(ctx, {
   110	      mdBody: bodyStale, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
   111	      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
   112	      mdCorrectionsHash: mdHash('fix-v1'),  // STALE: MD was generated against an older corrections
   113	    });
   114	
   115	    const report = await runSync(ctx.syncDeps());
   116	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
   117	
   118	    // The corrections-current (lower-major) body is now on both sides; docVersion downgraded to it.
   119	    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
   120	    const localBody = await localBlobBytes(ctx, key(ctx));
   121	    expect(cloudBody!.toString('utf8')).toBe(bodyCurrent);   // winner side unchanged
   122	    expect(localBody!.toString('utf8')).toBe(bodyCurrent);   // loser overwritten with the winner body
   123	    const local = await localVideoRecord(ctx);
   124	    expect(local?.docVersion?.major).toBe(1);
   125	    expect(local?.ratings).toEqual(winnerRatings);
   126	    expect(local?.tldr).toBe('keep-me');
   127	  });
   128	
   129	  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
   130	  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
   131	    const ctx = await makeOwnerContext();
   132	    const body = '# StaleBoth\n\nidentical stale content\n';
   133	    const staleHash = mdHash('stale-corrections'); // != mdHash('') → both sides corrections-stale
   134	    await seedLocalVideoFull(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
   135	    await seedCloudVideo(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
   136	
   137	    const report = await runSync(ctx.syncDeps());
   138	
   139	    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
   140	    expect(report.skippedIdentical).toBeGreaterThanOrEqual(1);
   141	    // MD unchanged on both sides.
   142	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
   143	    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
   144	  });
   145	
   146	  // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
   147	  it('row 4: carries the 5 real ratings + tldr/takeaways/tags verbatim (not reconstructed)', async () => {
   148	    const ctx = await makeOwnerContext();
   149	    const ratings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 }; // NON-flat
   150	    await seedCloudVideo(ctx, {
   151	      mdBody: '# S\n\nbody\n', ratings, overallScore: 3,
   152	      tldr: 'the tldr', takeaways: ['t1', 't2'], tags: ['x', 'y'], docVersion: { major: 3, minor: 3 },
   153	    });
   154	
   155	    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
   156	    const local = await localVideoRecord(ctx);
   157	    expect(local?.ratings).toEqual(ratings);
   158	    expect(local?.overallScore).toBe(3);
   159	    expect(local?.tldr).toBe('the tldr');
   160	    expect(local?.takeaways).toEqual(['t1', 't2']);
   161	    expect(local?.tags).toEqual(['x', 'y']);
   162	  });
   163	
   164	  // ── Row 5 — Class-B: a note edit on local + a score edit on cloud → BOTH survive on both sides.
   165	  it('row 5: independent Class-B edits (note local, score cloud) both survive', async () => {
   166	    const ctx = await makeOwnerContext();
   167	    const body = '# Same\n\nidentical current MD\n';
   168	    await seedLocalVideoFull(ctx, {
   169	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   170	      personalNote: 'mynote', annotationsEditedAt: { personalNote: '2026-03-01T00:00:00.000Z' },
   171	    });
   172	    await seedCloudVideo(ctx, {
   173	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   174	      personalScore: 4, annotationsEditedAt: { personalScore: '2026-03-02T00:00:00.000Z' },
   175	    });
   176	
   177	    const report = await runSync(ctx.syncDeps());
   178	    expect(report.mergedFields).toBeGreaterThanOrEqual(2);
   179	
   180	    const local = await localVideoRecord(ctx);
   181	    const cloud = await cloudVideoRecord(ctx);
   182	    expect(local?.personalNote).toBe('mynote');
   183	    expect(local?.personalScore).toBe(4);
   184	    expect(cloud?.personalNote).toBe('mynote');
   185	    expect(cloud?.personalScore).toBe(4);
   186	  });
   187	
   188	  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
   189	  it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
   190	    const ctx = await makeOwnerContext();
   191	    const body = '# Same6\n\nidentical current MD\n';
   192	    // Local cleared personalNote (value gone, but a NEWER edit timestamp); cloud still holds the old value.
   193	    await seedLocalVideoFull(ctx, {
   194	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   195	      annotationsEditedAt: { personalNote: '2026-05-02T00:00:00.000Z' }, // cleared: no personalNote value
   196	    });
   197	    await seedCloudVideo(ctx, {
   198	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   199	      personalNote: 'old', annotationsEditedAt: { personalNote: '2026-05-01T00:00:00.000Z' },
   200	    });
   201	    await seedManifestBaseline(ctx, baseline({
   202	      ...EMPTY_CLASSB,
   203	      personalNote: { value: 'old', editedAt: '2026-05-01T00:00:00.000Z' },
   204	    }));
   205	
   206	    await runSync(ctx.syncDeps());
   207	
   208	    const local = await localVideoRecord(ctx);
   209	    const cloud = await cloudVideoRecord(ctx);
   210	    expect(local?.personalNote == null).toBe(true);
   211	    expect(cloud?.personalNote == null).toBe(true); // the clear propagated; 'old' not resurrected
   212	  });
   213	
   214	  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
   215	  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
   216	    const ctx = await makeOwnerContext();
   217	    await seedLocalVideoFull(ctx, {
   218	      mdBody: '# Winner7\n\nformat-2\n', docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   219	    });
   220	    await seedCloudVideo(ctx, {
   221	      mdBody: '# Loser7\n\nformat-1\n', docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   222	    });
   223	
   224	    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
   225	    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
   226	  });
   227	
   228	  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
   229	  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
   230	    const ctx = await makeOwnerContext();
   231	    await seedCloudVideo(ctx, { mdBody: '# Free\n\nno charge\n' });
   232	    const spendBefore = await ctx.spendLedgerTotal();
   233	
   234	    const report = await runSync(ctx.syncDeps());
   235	
   236	    expect(report.created).toBeGreaterThanOrEqual(1);
   237	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   238	  });
   239	
   240	  // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
   241	  it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
   242	    const ctx = await makeOwnerContext();
   243	    // Cloud still holds the video; local deleted it; a baseline records they once agreed.
   244	    await seedCloudVideo(ctx, { mdBody: '# Deleted\n\ngone locally\n' });
   245	    await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));
   246	
   247	    const report = await runSync(ctx.syncDeps());
   248	
   249	    expect(report.removed).toBeGreaterThanOrEqual(1);
   250	    expect(await localVideoRecord(ctx)).toBeNull();          // not re-hydrated
   251	    expect(await cloudVideoRecord(ctx)).not.toBeNull();      // present side untouched (no propagation, M2b)
   252	    expect(report.created).toBe(0);
   253	  });
   254	
   255	  // ── Row 10 — no-session refusal + a client-forged owner_id is RLS-rejected.
   256	  it('row 10: getAuthedClient throws with no session; a forged owner_id is RLS-rejected', async () => {
   257	    const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
   258	    await expect(getAuthedClient(emptyStore)).rejects.toBeInstanceOf(NoSessionError);
   259	
   260	    const ctx = await makeOwnerContext();
   261	    const { error } = await ctx.userClient.from('playlists').insert({
   262	      owner_id: randomUUID(), // NOT auth.uid() → RLS with-check rejects
   263	      playlist_key: `k-${randomUUID()}`, playlist_url: 'https://x/forged',
   264	    });
   265	    expect(error).toBeTruthy();
   266	  });
   267	
   268	  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
   269	  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
   270	    const ctx = await makeOwnerContext();
   271	    await seedCloudVideo(ctx, {
   272	      mdBody: '# Cached\n\nhas cache\n',
   273	      summaryHtml: '<html>cached</html>',
   274	      digDeeperHtml: '<html>dig</html>',
   275	      extraArtifacts: { summaryPdf: { key: 'p.pdf', status: 'promoted' } },
   276	    });
   277	
   278	    await runSync(ctx.syncDeps());
   279	    const local = await localVideoRecord(ctx);
   280	    expect(local?.summaryHtml == null).toBe(true);
   281	    expect(local?.digDeeperHtml == null).toBe(true);
   282	    expect(artifactsOf(local)?.summaryPdf).toBeUndefined();
   283	  });
   284	
   285	  // ── Row 12 — a backfilled Class-B conflict is preserved across TWO runs (§5.5, round-3 H2).
   286	  it('row 12: backfilled divergent note logs+skips on both runs; neither side overwritten', async () => {
   287	    const ctx = await makeOwnerContext();
   288	    const body = '# Same12\n\nidentical current MD\n';
   289	    // Both sides carry a DIFFERENT personalNote with NO per-field timestamp → both backfilled.
   290	    await seedLocalVideoFull(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-local' });
   291	    await seedCloudVideo(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-cloud' });
   292	
   293	    const r1 = await runSync(ctx.syncDeps());
   294	    expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
   295	    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local');
   296	    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
   297	    const m1 = await ctx.readManifest();
   298	    expect((m1.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();
   299	
   300	    const r2 = await runSync(ctx.syncDeps());
   301	    expect(r2.conflictsLogged).toBeGreaterThanOrEqual(1); // re-logs (not silently skipped)
   302	    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local'); // still not overwritten
   303	    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
   304	    const m2 = await ctx.readManifest();
   305	    expect((m2.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();
   306	  });
   307	
   308	  // ── Row 13 — additive create of a summary-less video: metadata copied, no blob put, no throw.
   309	  it('row 13: additive create of a summary-less video copies metadata with no blob write', async () => {
   310	    const ctx = await makeOwnerContext();
   311	    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
   312	
   313	    const report = await runSync(ctx.syncDeps());
   314	    expect(report.errors).toEqual([]);
   315	    expect(report.created).toBeGreaterThanOrEqual(1);
   316	    const local = await localVideoRecord(ctx);
   317	    expect(local).not.toBeNull();
   318	    expect(local?.summaryMd == null).toBe(true);
   319	  });
   320	
   321	  // ── Row 14 — additive PUBLISH is servable: cloud row advertises promoted → summaryReady true.
   322	  it('row 14: additive publish sets promoted status → summaryReady true on the cloud', async () => {
   323	    const ctx = await makeOwnerContext();
   324	    await seedLocalVideoFull(ctx, { mdBody: '# Published\n\nservable\n' }); // local-only → publishes to cloud
   325	
   326	    await runSync(ctx.syncDeps());
   327	    const cloud = await cloudVideoRecord(ctx);
   328	    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
   329	    expect(cloud?.summaryReady).toBe(true);
   330	  });
   331	
   332	  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
   333	  it('row 15: additive publish creates the cloud playlist+video; a re-run is not read as a delete', async () => {
   334	    const ctx = await makeOwnerContext();
   335	    await seedLocalVideoFull(ctx, { mdBody: '# Create15\n\ncreated on cloud\n' });
   336	
   337	    const r1 = await runSync(ctx.syncDeps());
   338	    expect(r1.created).toBeGreaterThanOrEqual(1);
   339	    expect(await cloudVideoRecord(ctx)).not.toBeNull(); // receiver row created (not a silent no-op)
   340	    const m1 = await ctx.readManifest();
   341	    expect(m1.videos[ctx.videoId]).toBeDefined();       // baseline written only after the row landed
   342	
   343	    const r2 = await runSync(ctx.syncDeps());
   344	    expect(r2.removed).toBe(0);                          // baseline present + BOTH sides present → not a delete
   345	    expect(r2.created).toBe(0);
   346	    expect(await cloudVideoRecord(ctx)).not.toBeNull();
   347	    expect(await localVideoRecord(ctx)).not.toBeNull();
   348	  });
   349	
   350	  // ── Row 16 — promoted status never precedes a durable blob (blob promote fails mid-publish).
   351	  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
   352	    const ctx = await makeOwnerContext();
   353	    await seedLocalVideoFull(ctx, { mdBody: '# Crash16\n\npromote fails\n' });
   354	    const spendBefore = await ctx.spendLedgerTotal();
   355	
   356	    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
   357	
   358	    expect(report.errors.length).toBeGreaterThanOrEqual(1);
   359	    // No cloud row advertises promoted without a durable MD blob.
   360	    const cloud = await cloudVideoRecord(ctx);
   361	    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
   362	    expect(cloud?.summaryReady).toBeFalsy();
   363	    // Baseline not advanced; no charge.
   364	    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   365	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   366	  });
   367	
   368	  // ── Row 17 — fresh-device hydrate creates the local root (mkdir -p); re-run is not a delete.
   369	  it('row 17: a fresh-device hydrate creates the local root, writes index+video+MD; re-run is not a delete', async () => {
   370	    const ctx = await makeOwnerContext();
   371	    await seedCloudVideo(ctx, { mdBody: '# Fresh\n\nhydrated to a new device\n' });
   372	
   373	    // The per-playlist local root must NOT exist yet, or the ensureHydrationRoot mkdir path goes untested.
   374	    await expect(fs.access(ctx.playlistDataRoot)).rejects.toBeDefined();
   375	
   376	    const r1 = await runSync(ctx.syncDeps());
   377	    expect(r1.created).toBeGreaterThanOrEqual(1);
   378	    await expect(fs.access(path.join(ctx.playlistDataRoot, 'playlist-index.json'))).resolves.toBeUndefined();
   379	    const local = await localVideoRecord(ctx);
   380	    expect(local).not.toBeNull();
   381	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toContain('# Fresh');
   382	
   383	    const r2 = await runSync(ctx.syncDeps());
   384	    expect(r2.removed).toBe(0); // the just-created local root is not mis-read as a delete
   385	    expect(await localVideoRecord(ctx)).not.toBeNull();
   386	  });
   387	
   388	  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
   389	  //    Both sides changed corrections (backfilled, no per-field ts) → Class B logs+skips. The buggy
   390	  //    path fed local's corrections value into reconciledCorrectionsHash → local looked
   391	  //    corrections-current, cloud stale → copyToCloud OVERWROTE cloud's (different-correction) MD body.
   392	  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
   393	  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
   394	    const ctx = await makeOwnerContext();
   395	    const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
   396	    const bodyCloud = '# CloudCorrB\n\nMD generated for correction B\n';
   397	    await seedLocalVideoFull(ctx, {
   398	      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
   399	      docVersion: { major: 1, minor: 0 },
   400	    });
   401	    await seedCloudVideo(ctx, {
   402	      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // no annotationsEditedAt → backfilled
   403	      docVersion: { major: 1, minor: 0 },
   404	    });
   405	    const spendBefore = await ctx.spendLedgerTotal();
   406	
   407	    const r1 = await runSync(ctx.syncDeps());
   408	
   409	    expect(r1.updatedCloud).toBe(0);            // no Class-A copy in either direction
   410	    expect(r1.updatedLocal).toBe(0);
   411	    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
   412	    expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
   413	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   414	
   415	    // Both MD blobs untouched — each still equals its own pre-sync body, and the two DIFFER.
   416	    const l1 = (await localBlobBytes(ctx, key(ctx)))!.toString('utf8');
   417	    const c1 = (await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8');
   418	    expect(l1).toBe(bodyLocal);
   419	    expect(c1).toBe(bodyCloud);
   420	    expect(l1).not.toBe(c1);
   421	    // Both corrections preserved (neither overwritten).
   422	    expect((await localVideoRecord(ctx))?.corrections).toBe('A');
   423	    expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
   424	
   425	    // Second run — the baseline was NOT falsely advanced, so still no copy.
   426	    const r2 = await runSync(ctx.syncDeps());
   427	    expect(r2.updatedCloud).toBe(0);
   428	    expect(r2.updatedLocal).toBe(0);
   429	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
   430	    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   431	  });
   432	
   433	  // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
   434	  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
   435	  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
   436	  //    promoted-but-blobless row + advanced the baseline. After the fix: per-video throw, no promoted
   437	  //    receiver row, baseline NOT advanced (a re-run heals once the body is readable).
   438	  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
   439	  //    otherwise run 1 leaves a BARE receiver row, run 2 sees a two-sided video whose BOTH sides derive
   440	  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
   441	  //    laundering the corruption into a false "seen and agreed no-MD" state. The single-run assertions
   442	  //    below all passed while that bug was live; the run-2 baseline assertion is the real guard.
   443	  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
   444	    const ctx = await makeOwnerContext();
   445	    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
   446	    await seedCloudVideo(ctx, { /* mdBody omitted → blob absent */ });
   447	
   448	    const report = await runSync(ctx.syncDeps());
   449	
   450	    expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
   451	    // No partial state at all: the guard runs before ensureReceiverSlot, so there is no receiver row.
   452	    expect(await localVideoRecord(ctx)).toBeNull();
   453	    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
   454	    // Baseline not advanced — the throw aborted before writeVideoBaseline.
   455	    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   456	
   457	    // Run 2 — still one-sided, so it must report the SAME error and still write no baseline. With a
   458	    // bare row present it would instead take the two-sided path and silently record agreement.
   459	    const r2 = await runSync(ctx.syncDeps());
   460	    expect(r2.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
   461	    expect(await localVideoRecord(ctx)).toBeNull();
   462	    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
   463	    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   464	  });
   465	
   466	  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
   467	  //    wins (cloud higher-major, both corrections-current) and overwrites local's MD body; local's
   468	  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
   469	  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
   470	    const ctx = await makeOwnerContext();
   471	    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
   472	    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
   473	    await seedLocalVideoFull(ctx, {
   474	      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   475	      summaryHtml: '<html>STALE rendered from the old local body</html>',
   476	    });
   477	    await seedCloudVideo(ctx, {
   478	      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   479	    });
   480	
   481	    const report = await runSync(ctx.syncDeps());
   482	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
   483	
   484	    const local = await localVideoRecord(ctx);
   485	    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
   486	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body copied
   487	  });
   488	
   489	  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
   490	  //    regenerable render cache: it is the filename pointer to a PAID Gemini-generated dig-deeper
   491	  //    markdown file (lib/dig/generate.ts). Nulling it on an ordinary Class-A transfer orphans the file
   492	  //    on disk and makes the dig-state route / VideoMenu / build-doc-html / pdf-path all go dark —
   493	  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
   494	  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
   495	  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
   496	    const ctx = await makeOwnerContext();
   497	    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
   498	    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
   499	    const digKey = 'paid-dig-deeper.md';
   500	    await seedLocalVideoFull(ctx, {
   501	      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   502	      summaryHtml: '<html>STALE rendered from the old local body</html>',
   503	      digDeeperHtml: '<html>STALE dig render</html>',
   504	      raw: { digDeeperMd: digKey },
   505	    });
   506	    await seedCloudVideo(ctx, {
   507	      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   508	    });
   509	
   510	    const report = await runSync(ctx.syncDeps());
   511	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
   512	
   513	    const local = await localVideoRecord(ctx);
   514	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body landed
   515	    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
   516	    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
   517	    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
   518	  });
   519	
   520	  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
   521	  //    MD body). When the loser has NO MD at all, hydrating it is purely additive — nothing can be
   522	  //    destroyed — so a backfilled corrections conflict must not strand the video with no MD forever
   523	  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
   524	  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
   525	    const ctx = await makeOwnerContext();
   526	    const bodyCloud = '# CloudOnly\n\nthe only MD body that exists\n';
   527	    await seedLocalVideoFull(ctx, {
   528	      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
   529	      corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
   530	      docVersion: { major: 1, minor: 0 },
   531	    });
   532	    await seedCloudVideo(ctx, {
   533	      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // backfilled
   534	      docVersion: { major: 1, minor: 0 },
   535	    });
   536	    const spendBefore = await ctx.spendLedgerTotal();
   537	
   538	    const report = await runSync(ctx.syncDeps());
   539	
   540	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);           // hydration ran
   541	    expect(report.conflictsLogged).toBeGreaterThanOrEqual(1);        // corrections conflict still logged
   542	    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
   543	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges
   544	
   545	    // The cloud body is now on local, advertised promoted; both corrections still preserved.
   546	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   547	    const local = await localVideoRecord(ctx);
   548	    expect(local?.summaryMd).toBe(key(ctx));
   549	    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
   550	    expect(local?.corrections).toBe('A');
   551	    expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
   552	  });
   553	
   554	  // ── B1 (round 3) — `mdHash == null` conflates "this side advertises NO MD" with "this side's MD
   555	  //    body could not be READ". The Supabase blob store returns null on EVERY error (network, 5xx,
   556	  //    timeout, RLS denial), not only 404, so an ordinary transient download failure is
   557	  //    indistinguishable from a summary-less video. reconcileClassA's presence branches (!lHas/!cHas)
   558	  //    fire BEFORE the corrections-currency and never-downgrade-format ladder, so the unreadable side
   559	  //    is treated as the empty side and the OTHER replica's body is copied over it — destroying it and
   560	  //    laundering the result into a full-agreement baseline. Both manifestations below must instead
   561	  //    surface a per-video error, preserve every byte, and advance NO baseline (so the run heals once
   562	  //    the body is readable). Each asserts across TWO runs: round 2's postmortem was that a
   563	  //    single-run assertion passed while the laundering bug was live.
   564	  it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
   565	    const ctx = await makeOwnerContext();
   566	    const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
   567	    await seedLocalVideoFull(ctx, {
   568	      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // backfilled (no per-field ts)
   569	      docVersion: { major: 1, minor: 0 },
   570	    });
   571	    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
   572	    // the buggy path read as "cloud has no MD" ⇒ the corrections guard did not fire ⇒ copyToCloud.
   573	    await seedCloudVideo(ctx, {
   574	      /* mdBody omitted → blob unreadable */
   575	      corrections: 'B', mdCorrectionsHash: mdHash('B'), docVersion: { major: 1, minor: 0 },
   576	    });
   577	    const spendBefore = await ctx.spendLedgerTotal();
   578	
   579	    for (const _run of [1, 2]) {
   580	      const report = await runSync(ctx.syncDeps());
   581	
   582	      // The failure is SURFACED, not silent (the buggy path reported errors: []).
   583	      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
   584	      expect(report.updatedCloud).toBe(0);
   585	      expect(report.updatedLocal).toBe(0);
   586	      // Local body byte-preserved; cloud body still absent (nothing was written over the gap).
   587	      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
   588	      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
   589	      // Both corrections preserved.
   590	      expect((await localVideoRecord(ctx))?.corrections).toBe('A');
   591	      expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
   592	      // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
   593	      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   594	      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
   595	    }
   596	  });
   597	
   598	  it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
   599	    const ctx = await makeOwnerContext();
   600	    const bodyLocal = '# LocalOld\n\nlower-major local body\n';
   601	    // No corrections anywhere — this manifestation is NOT conflict-gated: the !cHas early return in
   602	    // reconcileClassA precedes the never-downgrade-format rule, so a transient download error let a
   603	    // major-1 body overwrite a major-9 one and recorded major 1 as the agreed baseline. Run 2 then saw
   604	    // identical bodies ⇒ skip ⇒ permanent, recoverable only by full (paid) regeneration.
   605	    await seedLocalVideoFull(ctx, {
   606	      mdBody: bodyLocal, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   607	    });
   608	    await seedCloudVideo(ctx, {
   609	      /* mdBody omitted → blob unreadable */
   610	      docVersion: { major: 9, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   611	    });
   612	    const spendBefore = await ctx.spendLedgerTotal();
   613	
   614	    for (const _run of [1, 2]) {
   615	      const report = await runSync(ctx.syncDeps());
   616	
   617	      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
   618	      expect(report.updatedCloud).toBe(0);
   619	      expect(report.updatedLocal).toBe(0);
   620	      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
   621	      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
   622	      // Format NOT downgraded on either side (the buggy path wrote cloud major 9 → 1).
   623	      expect((await cloudVideoRecord(ctx))?.docVersion?.major).toBe(9);
   624	      expect((await localVideoRecord(ctx))?.docVersion?.major).toBe(1);
   625	      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   626	      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
   627	    }
   628	  });
   629	});

exec
/bin/bash -lc "rg -n \"function seed|const seed|makeOwnerContext|cloudBlobBytes|localBlobBytes|spendLedgerTotal|readManifest\" tests/integration/cloud-sync -g '*.ts'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "rg -n \"readMdBody|blob\\.get\\(|readModelEnvelope|decideCompanion|mdHash\\(|writeVideoBaseline|appendConflict|catch \\{|return null|return \\[\\]|emptyPlaylistIndex\" lib/cloud-sync lib/storage/local lib/storage/supabase tests/lib/cloud-sync tests/integration/cloud-sync -g '*.ts'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/cloud-sync/sync-run.int.test.ts:14:import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/sync-run.int.test.ts:25:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/sync-run.int.test.ts:27:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/sync-run.int.test.ts:33:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/sync-run.int.test.ts:48:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/sync-run.int.test.ts:59:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/sync-run.int.test.ts:61:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/sync-run.int.test.ts:68:    const m = await ctx.readManifest();
tests/integration/cloud-sync/sync-run.int.test.ts:71:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:9:// Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
tests/integration/cloud-sync/e2e.int.test.ts:16:  makeOwnerContext, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
tests/integration/cloud-sync/e2e.int.test.ts:17:  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, type Ctx,
tests/integration/cloud-sync/e2e.int.test.ts:57:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:70:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:75:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges
tests/integration/cloud-sync/e2e.int.test.ts:78:    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
tests/integration/cloud-sync/e2e.int.test.ts:98:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:119:    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
tests/integration/cloud-sync/e2e.int.test.ts:120:    const localBody = await localBlobBytes(ctx, key(ctx));
tests/integration/cloud-sync/e2e.int.test.ts:131:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:142:    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
tests/integration/cloud-sync/e2e.int.test.ts:143:    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
tests/integration/cloud-sync/e2e.int.test.ts:148:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:166:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:190:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:216:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:230:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:232:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:237:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:242:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:260:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:270:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:287:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:297:    const m1 = await ctx.readManifest();
tests/integration/cloud-sync/e2e.int.test.ts:304:    const m2 = await ctx.readManifest();
tests/integration/cloud-sync/e2e.int.test.ts:310:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:323:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:334:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:340:    const m1 = await ctx.readManifest();
tests/integration/cloud-sync/e2e.int.test.ts:352:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:354:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:364:    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:365:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:370:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:381:    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toContain('# Fresh');
tests/integration/cloud-sync/e2e.int.test.ts:394:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:405:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:413:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:416:    const l1 = (await localBlobBytes(ctx, key(ctx)))!.toString('utf8');
tests/integration/cloud-sync/e2e.int.test.ts:417:    const c1 = (await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8');
tests/integration/cloud-sync/e2e.int.test.ts:429:    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
tests/integration/cloud-sync/e2e.int.test.ts:430:    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
tests/integration/cloud-sync/e2e.int.test.ts:444:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:455:    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:463:    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:470:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:486:    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body copied
tests/integration/cloud-sync/e2e.int.test.ts:496:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:514:    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body landed
tests/integration/cloud-sync/e2e.int.test.ts:525:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:536:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:543:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges
tests/integration/cloud-sync/e2e.int.test.ts:546:    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
tests/integration/cloud-sync/e2e.int.test.ts:565:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:577:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:587:      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
tests/integration/cloud-sync/e2e.int.test.ts:588:      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
tests/integration/cloud-sync/e2e.int.test.ts:593:      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:594:      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
tests/integration/cloud-sync/e2e.int.test.ts:599:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/e2e.int.test.ts:612:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:620:      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
tests/integration/cloud-sync/e2e.int.test.ts:621:      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
tests/integration/cloud-sync/e2e.int.test.ts:625:      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:626:      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
tests/integration/cloud-sync/cloud-stamping.int.test.ts:7:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/cloud-stamping.int.test.ts:12:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/cloud-stamping.int.test.ts:22:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/cloud-stamping.int.test.ts:32:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/stamping.int.test.ts:10:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/stamping.int.test.ts:14:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/stamping.int.test.ts:30:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/stamping.int.test.ts:42:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/stamping.int.test.ts:54:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/stamping.int.test.ts:70:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/stamping.int.test.ts:81:    const ctx = await makeOwnerContext();
tests/integration/cloud-sync/stamping.int.test.ts:91:    const ctx = await makeOwnerContext();

 succeeded in 0ms:
tests/integration/cloud-sync/e2e.int.test.ts:35:const bodyHash = (b: string) => mdHash(b);
tests/integration/cloud-sync/e2e.int.test.ts:37: *  reconciledCorrectionsHash === mdHash(String(undefined ?? '')) === mdHash(''). */
tests/integration/cloud-sync/e2e.int.test.ts:38:const H_NO_CORRECTIONS = mdHash('');
tests/integration/cloud-sync/e2e.int.test.ts:106:      mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
tests/integration/cloud-sync/e2e.int.test.ts:112:      mdCorrectionsHash: mdHash('fix-v1'),  // STALE: MD was generated against an older corrections
tests/integration/cloud-sync/e2e.int.test.ts:133:    const staleHash = mdHash('stale-corrections'); // != mdHash('') → both sides corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:398:      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
tests/integration/cloud-sync/e2e.int.test.ts:402:      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // no annotationsEditedAt → backfilled
tests/integration/cloud-sync/e2e.int.test.ts:435:  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
tests/integration/cloud-sync/e2e.int.test.ts:454:    // Baseline not advanced — the throw aborted before writeVideoBaseline.
tests/integration/cloud-sync/e2e.int.test.ts:529:      corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
tests/integration/cloud-sync/e2e.int.test.ts:533:      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // backfilled
tests/integration/cloud-sync/e2e.int.test.ts:568:      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // backfilled (no per-field ts)
tests/integration/cloud-sync/e2e.int.test.ts:571:    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
tests/integration/cloud-sync/e2e.int.test.ts:575:      corrections: 'B', mdCorrectionsHash: mdHash('B'), docVersion: { major: 1, minor: 0 },
lib/storage/supabase/supabase-job-queue.ts:13:    if (!data) return null;
lib/storage/supabase/supabase-job-queue.ts:60:    if (!data || data.length === 0) return null;
lib/cloud-sync/auth.ts:41:        if (e?.code === 'ENOENT') return null; // no dir yet → no token
lib/cloud-sync/auth.ts:49:        if (e?.code === 'ENOENT') return null;
lib/cloud-sync/auth.ts:92:  if (!refresh) return null;
lib/cloud-sync/auth.ts:95:  if (error || !data.session) return null;
lib/storage/local/local-blob-store.ts:15:    catch (e) { try { fs.unlinkSync(tmp); } catch {} throw e; }
lib/storage/local/local-blob-store.ts:20:    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
lib/storage/local/local-blob-store.ts:59:      if ((e as NodeJS.ErrnoException).code === 'ENOENT') return [];
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion } from '@/lib/cloud-sync/companion';
tests/lib/cloud-sync/companion.test.ts:11:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h1') })).toMatchObject({ kind: 'ship' });
tests/lib/cloud-sync/companion.test.ts:14:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h2') }))
tests/lib/cloud-sync/companion.test.ts:18:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env(undefined) }))
tests/lib/cloud-sync/companion.test.ts:22:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: null }))
lib/storage/supabase/supabase-blob-store.ts:25:    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
lib/storage/supabase/supabase-blob-store.ts:31:    if (error) return null;
lib/cloud-sync/companion.ts:8:export function decideCompanion(args: {
tests/lib/cloud-sync/content-hash.test.ts:20:    const h = mdHash('# Title\n\nbody\n');
tests/lib/cloud-sync/content-hash.test.ts:22:    expect(mdHash('# Title\n\nbody\n')).toBe(h);
tests/lib/cloud-sync/content-hash.test.ts:26:    expect(mdHash('# T\r\n\r\nbody\r\n\r\n')).toBe(mdHash('# T\n\nbody\n'));
tests/lib/cloud-sync/content-hash.test.ts:29:    expect(mdHash('a\n')).not.toBe(mdHash('b\n'));
lib/storage/supabase/supabase-metadata-store.ts:5:import { emptyPlaylistIndex } from '@/lib/storage/empty-index';
lib/storage/supabase/supabase-metadata-store.ts:27:  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
lib/storage/supabase/supabase-metadata-store.ts:36:    if (!pl) return emptyPlaylistIndex(p);
lib/cloud-sync/manifest.ts:20:  } catch { /* missing or corrupt → degrade (§8) */ }
lib/cloud-sync/manifest.ts:31:export async function writeVideoBaseline(
lib/cloud-sync/manifest.ts:44:export async function appendConflict(dataRoot: string, playlistKey: string, e: ConflictEntry): Promise<void> {
tests/lib/cloud-sync/import-guard.test.ts:9:  if (!existsSync(dir)) return [];
lib/cloud-sync/sync-run.ts:29:import { decideCompanion } from './companion';
lib/cloud-sync/sync-run.ts:31:  readManifest, writeVideoBaseline, appendConflict, resetConflictDedup,
lib/cloud-sync/sync-run.ts:35:import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
lib/cloud-sync/sync-run.ts:59:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
lib/cloud-sync/sync-run.ts:60:  if (!video.summaryMd) return null;
lib/cloud-sync/sync-run.ts:61:  const buf = await blob.get(p, video.summaryMd);
lib/cloud-sync/sync-run.ts:137:  if (idx.videos.some((v) => v.id === video.id)) return null;
lib/cloud-sync/sync-run.ts:171:    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
lib/cloud-sync/sync-run.ts:245:      await appendConflict(dataRoot, key, {
lib/cloud-sync/sync-run.ts:279:  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
lib/cloud-sync/sync-run.ts:283:  const h = mdHash(body);
lib/cloud-sync/sync-run.ts:287:  const staged = await loser.blob.get(loser.p, ref.tempKey);
lib/cloud-sync/sync-run.ts:288:  if (!staged || mdHash(staged.toString('utf8')) !== h) {
lib/cloud-sync/sync-run.ts:350:  const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
lib/cloud-sync/sync-run.ts:351:  const decision = decideCompanion({ winnerMdHash, senderEnvelope });
lib/cloud-sync/sync-run.ts:357:  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
lib/cloud-sync/sync-run.ts:457:            const body = await readMdBody(from.blob, from.p, present);
lib/cloud-sync/sync-run.ts:460:            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
lib/cloud-sync/sync-run.ts:461:              deriveClassASignals(present, body), body ? mdHash(body) : null,
lib/cloud-sync/sync-run.ts:477:        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
lib/cloud-sync/sync-run.ts:491:        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
lib/cloud-sync/sync-run.ts:492:        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
lib/cloud-sync/sync-run.ts:495:        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
lib/cloud-sync/sync-run.ts:498:        //    return null` — it swallows EVERY failure (network, 5xx, timeout, RLS denial), so on the
lib/cloud-sync/sync-run.ts:523:          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
lib/cloud-sync/sync-run.ts:558:        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
lib/cloud-sync/registry.ts:9:  if (!url) return null;
lib/cloud-sync/registry.ts:13:  } catch { return null; }
lib/cloud-sync/registry.ts:21:    try { entries = await fs.readdir(root); } catch { continue; }
lib/cloud-sync/registry.ts:37:    try { await fs.access(path.join(p, 'playlist-index.json')); return p; } catch { /* try next */ }
lib/cloud-sync/registry.ts:39:  return null;
lib/cloud-sync/backfill.ts:11:    mdHash: mdBody != null ? mdHash(mdBody) : null,
tests/lib/cloud-sync/model-writer-hash.test.ts:6:// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
tests/lib/cloud-sync/model-writer-hash.test.ts:14:import { readModelEnvelope } from '../../../lib/html-doc/model-store';
tests/lib/cloud-sync/model-writer-hash.test.ts:70:it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:79:  const env = await readModelEnvelope(principal, 'a-title');
tests/lib/cloud-sync/model-writer-hash.test.ts:81:  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
tests/lib/cloud-sync/model-writer-hash.test.ts:82:  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
tests/lib/cloud-sync/manifest.test.ts:5:import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';
tests/lib/cloud-sync/manifest.test.ts:25:  await writeVideoBaseline(r, 'PL1', 'v1', base as any);
tests/lib/cloud-sync/manifest.test.ts:32:  await appendConflict(r, 'PL1', e);
tests/lib/cloud-sync/manifest.test.ts:33:  await appendConflict(r, 'PL1', e);
lib/cloud-sync/content-hash.ts:16:export function mdHash(md: string): string {
tests/lib/cloud-sync/regenerate-stamp.test.ts:6:// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
tests/lib/cloud-sync/regenerate-stamp.test.ts:92:        mdCorrectionsHash: mdHash('fix name'),
tests/lib/cloud-sync/regenerate-stamp.test.ts:104:        mdCorrectionsHash: mdHash('old corrections'),
tests/lib/cloud-sync/regenerate-stamp.test.ts:116:        mdCorrectionsHash: mdHash(''),
tests/lib/cloud-sync/backfill.test.ts:16:  expect(s.mdHash).toBe(mdHash(BODY));
tests/lib/cloud-sync/backfill.test.ts:17:  expect(s.mdHash).not.toBe(mdHash('001_title.md')); // must NOT hash the filename

exec
/bin/bash -lc "nl -ba tests/integration/helpers/cloud.ts | sed -n '1,360p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// tests/integration/helpers/cloud.ts
     2	//
     3	// Shared integration harness for Stage 3 Cloud Sync (Tasks 3, 4, 12, 14). Reuses the existing
     4	// owner/session/seed helpers (clients.ts, seed.ts) — does not reinvent auth or seeding.
     5	//
     6	// Task 3/4 use: makeOwnerContext, seedVideo, ctx.rpc, ctx.readVideoData, ctx.persistSummary.
     7	// Task 12 (sync-run) adds the real bodies for: seedLocalPlaylist, ctx.syncDeps({failCloudPromote?}),
     8	// ctx.readManifest, plus the local-store handles (ctx.local, ctx.localBlob, ctx.localPrincipal).
     9	
    10	import { promises as fs } from 'fs';
    11	import os from 'os';
    12	import path from 'path';
    13	import { randomUUID } from 'crypto';
    14	import type { SupabaseClient } from '@supabase/supabase-js';
    15	import { newUser, signInAs } from './clients';
    16	import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './seed';
    17	import type { Principal } from '@/lib/storage/principal';
    18	import { localPrincipal } from '@/lib/storage/principal';
    19	import type { MetadataStore } from '@/lib/storage/metadata-store';
    20	import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
    21	import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
    22	import { localBlobStore } from '@/lib/storage/local/local-blob-store';
    23	import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
    24	import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
    25	import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
    26	import { readManifest as readManifestFile, writeVideoBaseline } from '@/lib/cloud-sync/manifest';
    27	import type { SyncDeps } from '@/lib/cloud-sync/sync-run';
    28	import type { VideoBaseline } from '@/lib/cloud-sync/types';
    29	import type { Video } from '@/types';
    30	
    31	export interface SeedLocalPlaylistOpts {
    32	  /** Two-sided: also seed a matching LOCAL video carrying this human note, so it publishes to cloud. */
    33	  localNote?: { value: string; editedAt: string };
    34	  /** Crash-safety: seed a LOCAL-ONLY video (no cloud video) so the sync PUBLISHES it to cloud —
    35	   *  the direction whose durability gate is the Supabase staged→promote (faultable via failCloudPromote). */
    36	  publishToCloud?: boolean;
    37	}
    38	
    39	export interface Ctx {
    40	  readonly userId: string;
    41	  /** RLS-scoped client (anon key + user JWT) — the ONLY client the code-under-test uses. */
    42	  readonly userClient: SupabaseClient;
    43	  /** { id: userId, indexKey: playlistKey } — indexKey is populated by seedVideo() once a
    44	   *  playlist exists (mirrors annotations-rpc.test.ts:31). Empty indexKey before any seed. */
    45	  principal: Principal;
    46	
    47	  // ---- Task 12 sync-run fixture state (populated by seedLocalPlaylist) ----
    48	  playlistId: string;          // cloud playlist UUID (empty until a cloud playlist is seeded)
    49	  playlistKey: string;         // shared playlist_key (also the YouTube list-id in the url)
    50	  videoId: string;             // the (short, local-index-valid) video id under test
    51	  tempDataRoot: string;        // the ROOT dir passed as deps.dataRoots[0]
    52	  playlistDataRoot: string;    // the per-playlist dir runSync resolves for this key
    53	  local: MetadataStore;        // local metadata store singleton
    54	  localBlob: BlobStore;        // local blob store singleton
    55	  localPrincipal: Principal;   // localPrincipal(playlistDataRoot)
    56	  cloudPrincipal: Principal;   // { id: userId, indexKey: playlistKey }
    57	
    58	  rpc(name: string, args: Record<string, unknown>): Promise<unknown>;
    59	  readVideoData(playlistId: string, videoId: string): Promise<any>;
    60	  persistSummary(
    61	    playlistId: string, videoId: string, video: Record<string, unknown>, status: string,
    62	  ): Promise<void>;
    63	  /** Build the SyncDeps for a runSync() call. failCloudPromote wraps the cloud blob store so its
    64	   *  promote() throws AFTER staging (crash-safety fault injection). Cloud stores use the USER
    65	   *  session client (RLS-scoped) — never service-role — the money/RLS invariant. */
    66	  syncDeps(opts?: { failCloudPromote?: boolean }): SyncDeps;
    67	  /** Read the sync manifest runSync wrote for this ctx's playlist. */
    68	  readManifest(): Promise<{ version: 1; videos: Record<string, unknown> }>;
    69	  /** Sum of reserved_cents + actual_cents across spend_ledger (money-safety assertions).
    70	   *  spend_ledger is GLOBAL (one row per UTC day, NO owner_id) → whole-table total; money-safety
    71	   *  tests assert via a before/after DELTA. Reads via the service-role admin client because
    72	   *  spend_ledger grants NO client access. */
    73	  spendLedgerTotal(): Promise<number>;
    74	}
    75	
    76	/** Creates an authenticated owner (RLS-scoped session client) — the shared entry point for
    77	 *  every cloud-sync integration test. */
    78	export async function makeOwnerContext(): Promise<Ctx> {
    79	  const u = await newUser();
    80	  const { client: userClient, userId } = await signInAs(u.email, u.password);
    81	
    82	  const ctx: Ctx = {
    83	    userId,
    84	    userClient,
    85	    principal: { id: userId, indexKey: '' },
    86	
    87	    // sync-run fixture state — placeholders until seedLocalPlaylist populates them
    88	    playlistId: '',
    89	    playlistKey: '',
    90	    videoId: '',
    91	    tempDataRoot: '',
    92	    playlistDataRoot: '',
    93	    local: localMetadataStore,
    94	    localBlob: localBlobStore,
    95	    localPrincipal: localPrincipal(''),
    96	    cloudPrincipal: { id: userId, indexKey: '' },
    97	
    98	    async rpc(name: string, args: Record<string, unknown>): Promise<unknown> {
    99	      const { data, error } = await userClient.rpc(name, args);
   100	      if (error) throw error;
   101	      return data;
   102	    },
   103	
   104	    async readVideoData(playlistId: string, videoId: string): Promise<any> {
   105	      const { data, error } = await userClient
   106	        .from('videos')
   107	        .select('data')
   108	        .eq('playlist_id', playlistId)
   109	        .eq('video_id', videoId)
   110	        .single();
   111	      if (error) throw error;
   112	      return data!.data;
   113	    },
   114	
   115	    async persistSummary(
   116	      playlistId: string, videoId: string, video: Record<string, unknown>, status: string,
   117	    ): Promise<void> {
   118	      const { error } = await userClient.rpc('persist_summary', {
   119	        p_owner_id: userId,
   120	        p_playlist_id: playlistId,
   121	        p_video_id: videoId,
   122	        p_video: video,
   123	        p_artifact_status: status,
   124	      });
   125	      if (error) throw error;
   126	    },
   127	
   128	    syncDeps(opts: { failCloudPromote?: boolean } = {}): SyncDeps {
   129	      const cloud = new SupabaseMetadataStore(userClient);
   130	      let cloudBlob: BlobStore = new SupabaseBlobStore(userClient, ARTIFACTS_BUCKET);
   131	      if (opts.failCloudPromote) cloudBlob = new FailPromoteBlobStore(cloudBlob);
   132	      return {
   133	        local: localMetadataStore,
   134	        cloud,
   135	        localBlob: localBlobStore,
   136	        cloudBlob,
   137	        dataRoots: [ctx.tempDataRoot],
   138	        ownerId: userId, // MUST be auth.uid() — the RLS/storage-path owner segment
   139	      };
   140	    },
   141	
   142	    async readManifest(): Promise<{ version: 1; videos: Record<string, unknown> }> {
   143	      return readManifestFile(ctx.playlistDataRoot, ctx.playlistKey);
   144	    },
   145	
   146	    async spendLedgerTotal(): Promise<number> {
   147	      const { adminClient } = await import('./clients');
   148	      const { data, error } = await adminClient()
   149	        .from('spend_ledger').select('reserved_cents,actual_cents');
   150	      if (error) throw error;
   151	      return (data ?? []).reduce(
   152	        (sum, r) => sum + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0,
   153	      );
   154	    },
   155	  };
   156	  return ctx;
   157	}
   158	
   159	/** Wraps a BlobStore so promote() throws AFTER staging succeeded — the crash-safety fault:
   160	 *  a partially-transferred blob whose promote never lands must NOT advance the manifest baseline. */
   161	class FailPromoteBlobStore implements BlobStore {
   162	  constructor(private inner: BlobStore) {}
   163	  put(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.put(p, key, bytes, ct); }
   164	  get(p: Principal, key: string) { return this.inner.get(p, key); }
   165	  exists(p: Principal, key: string) { return this.inner.exists(p, key); }
   166	  delete(p: Principal, key: string) { return this.inner.delete(p, key); }
   167	  putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
   168	  async promote(_ref: StagedRef): Promise<void> { throw new Error('injected cloud promote failure'); }
   169	  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
   170	  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
   171	}
   172	
   173	/** Seeds the fixture for a sync-run test and populates ctx's sync state. Default: a CLOUD playlist
   174	 *  with one promoted-summary video, local replica empty (hydrate). `localNote` additionally seeds a
   175	 *  matching LOCAL video with that note (two-sided publish). `publishToCloud` seeds a LOCAL-ONLY video
   176	 *  (no cloud video) so the sync publishes local→cloud (crash-safety direction). */
   177	export async function seedLocalPlaylist(
   178	  ctx: Ctx, opts: SeedLocalPlaylistOpts = {},
   179	): Promise<{ playlistId?: string; playlistKey: string; videoId: string }> {
   180	  const { adminClient } = await import('./clients');
   181	  const svc = adminClient();
   182	
   183	  const key = `k-${randomUUID()}`;
   184	  const url = `https://www.youtube.com/playlist?list=${key}`;
   185	  // VIDEO_ID_RE caps local video ids at 20 chars of [A-Za-z0-9_-]; a full uuid is too long.
   186	  const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
   187	  const base = videoId;
   188	  const md = `# Summary ${videoId}\n\nBody paragraph for the sync fixture.\n`;
   189	
   190	  ctx.playlistKey = key;
   191	  ctx.videoId = videoId;
   192	  ctx.tempDataRoot = await fs.mkdtemp(path.join(os.homedir(), '.cs-syncrun-'));
   193	  ctx.playlistDataRoot = path.join(ctx.tempDataRoot, key);
   194	  ctx.localPrincipal = localPrincipal(ctx.playlistDataRoot);
   195	  ctx.cloudPrincipal = { id: ctx.userId, indexKey: key };
   196	
   197	  if (opts.publishToCloud) {
   198	    // Local-only video → sync publishes it to cloud. No cloud playlist/video seeded;
   199	    // ensureReceiverSlot creates the cloud playlist row during the run.
   200	    await seedLocalVideo(ctx, { videoId, base, md });
   201	    return { playlistKey: key, videoId };
   202	  }
   203	
   204	  // Cloud playlist + one promoted-summary video (hydrate source / two-sided cloud side).
   205	  const { data: pl, error } = await svc
   206	    .from('playlists')
   207	    .insert({ owner_id: ctx.userId, playlist_key: key, playlist_url: url })
   208	    .select('id')
   209	    .single();
   210	  if (error) throw error;
   211	  ctx.playlistId = pl!.id as string;
   212	
   213	  await seedPromotedVideo(svc, { ownerId: ctx.userId, playlistId: ctx.playlistId, videoId, base });
   214	  await seedSummaryBlob(svc, ctx.userId, key, base, md);
   215	
   216	  if (opts.localNote) {
   217	    await seedLocalVideo(ctx, { videoId, base, md, note: opts.localNote });
   218	  }
   219	
   220	  return { playlistId: ctx.playlistId, playlistKey: key, videoId };
   221	}
   222	
   223	/** Seeds a LOCAL playlist dir under tempDataRoot with one video (+ optional note) and its MD blob,
   224	 *  so discoverLocalPlaylists finds it and Class-A sees an identical MD body (skip, no transfer). */
   225	async function seedLocalVideo(
   226	  ctx: Ctx,
   227	  args: { videoId: string; base: string; md: string; note?: { value: string; editedAt: string } },
   228	): Promise<void> {
   229	  const { videoId, base, md, note } = args;
   230	  const lp = ctx.localPrincipal;
   231	  await fs.mkdir(ctx.playlistDataRoot, { recursive: true });
   232	  await ctx.local.setPlaylistMeta(lp, { playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}` });
   233	  await ctx.local.claimVideoSlot(lp, videoId);
   234	
   235	  const video = {
   236	    id: videoId,
   237	    title: videoId,
   238	    youtubeUrl: `https://youtu.be/${videoId}`,
   239	    language: 'en',
   240	    durationSeconds: 600,
   241	    archived: false,
   242	    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
   243	    overallScore: 4,
   244	    summaryMd: `${base}.md`,
   245	    processedAt: '2026-01-01T00:00:00.000Z',
   246	    docVersion: { major: 1, minor: 0 },
   247	    ...(note
   248	      ? { personalNote: note.value, annotationsEditedAt: { personalNote: note.editedAt } }
   249	      : {}),
   250	  } as unknown as Video;
   251	
   252	  await ctx.local.upsertVideo(lp, video);
   253	  await ctx.localBlob.put(lp, `${base}.md`, Buffer.from(md, 'utf8'), 'text/markdown');
   254	}
   255	
   256	/** Seeds a playlist + a promoted video owned by ctx.userId (via admin client, setup only).
   257	 *  `overrides` are merged into the seeded video's `data` (e.g. a pre-existing personalNote). */
   258	export async function seedVideo(
   259	  ctx: Ctx,
   260	  overrides?: Record<string, unknown>,
   261	): Promise<{ playlistId: string; videoId: string; playlistKey: string }> {
   262	  const { adminClient } = await import('./clients');
   263	  const svc = adminClient();
   264	  const { playlistId, playlistKey } = await seedPlaylist(svc, ctx.userId);
   265	  const { videoId } = await seedPromotedVideo(svc, { ownerId: ctx.userId, playlistId });
   266	  ctx.principal = { id: ctx.userId, indexKey: playlistKey };
   267	
   268	  if (overrides && Object.keys(overrides).length > 0) {
   269	    const { data: row, error: readErr } = await svc
   270	      .from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
   271	    if (readErr) throw readErr;
   272	    const { error: updErr } = await svc
   273	      .from('videos').update({ data: { ...(row!.data as object), ...overrides } })
   274	      .eq('playlist_id', playlistId).eq('video_id', videoId);
   275	    if (updErr) throw updErr;
   276	  }
   277	
   278	  return { playlistId, videoId, playlistKey };
   279	}
   280	
   281	// ─────────────────────────────────────────────────────────────────────────────
   282	// Task 14 (§10 end-to-end) harness extensions. Two-sided + full-field seeding so
   283	// the e2e scenarios can drive the divergent-MD Class-A COPY path (transferClassA
   284	// + companionTransfer), not just the additive hydrate path (copyAdditiveVideo).
   285	// seedCloudVideo/seedLocalVideoFull each write the MD BODY to their replica's
   286	// blob and set video.summaryMd to the KEY they wrote.
   287	// ─────────────────────────────────────────────────────────────────────────────
   288	
   289	export interface SeedFields {
   290	  videoId?: string;
   291	  position?: number;
   292	  title?: string;
   293	  archived?: boolean;
   294	  /** Blob KEY (video.summaryMd). Default `${videoId}.md`. `null` = summary-less video (no blob). */
   295	  summaryMd?: string | null;
   296	  /** MD BODY written to the blob at the summaryMd key. Omit to skip the blob write. */
   297	  mdBody?: string;
   298	  ratings?: Record<string, number>;
   299	  overallScore?: number;
   300	  tldr?: string;
   301	  takeaways?: string[];
   302	  tags?: string[];
   303	  videoType?: string;
   304	  audience?: string;
   305	  docVersion?: { major: number; minor: number };
   306	  mdGeneratedAt?: string;
   307	  mdCorrectionsHash?: string;
   308	  processedAt?: string;
   309	  personalNote?: string;
   310	  personalScore?: number;
   311	  corrections?: string;
   312	  annotationsEditedAt?: Record<string, string>;
   313	  status?: 'promoted' | 'committed';
   314	  /** Regenerable-cache pointers (must NOT be copied by an additive create — §5.6). */
   315	  summaryHtml?: string;
   316	  digDeeperHtml?: string;
   317	  /** Extra artifacts.* pointers MERGED alongside summaryMd (e.g. a summaryPdf that must be dropped). */
   318	  extraArtifacts?: Record<string, unknown>;
   319	  /** Extra top-level data keys merged last. */
   320	  raw?: Record<string, unknown>;
   321	}
   322	
   323	const FLAT_RATINGS = { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 };
   324	
   325	/** Assigns the shared sync fixture identity (key, videoId, temp root, principals) exactly once,
   326	 *  so seedCloudVideo + seedLocalVideoFull compose onto the SAME playlist/video (two-sided). */
   327	export async function prepareSyncCtx(ctx: Ctx): Promise<void> {
   328	  if (ctx.playlistKey) return;
   329	  const key = `k-${randomUUID()}`;
   330	  // VIDEO_ID_RE caps local video ids at 20 chars of [A-Za-z0-9_-]; a full uuid is too long.
   331	  const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
   332	  ctx.playlistKey = key;
   333	  ctx.videoId = videoId;
   334	  ctx.tempDataRoot = await fs.mkdtemp(path.join(os.homedir(), '.cs-syncrun-'));
   335	  ctx.playlistDataRoot = path.join(ctx.tempDataRoot, key);
   336	  ctx.localPrincipal = localPrincipal(ctx.playlistDataRoot);
   337	  ctx.cloudPrincipal = { id: ctx.userId, indexKey: key };
   338	}
   339	
   340	/** Build the `videos.data` jsonb / local Video record from the requested fields. Shape mirrors the
   341	 *  worker's promoted-video shape (seed.ts) but with full control over the Class-A/companion signals. */
   342	function buildVideoData(videoId: string, f: SeedFields): Record<string, unknown> {
   343	  const summaryMd = f.summaryMd === undefined ? `${videoId}.md` : f.summaryMd;
   344	  const base = summaryMd ? summaryMd.replace(/\.md$/, '') : null;
   345	  return {
   346	    id: videoId,
   347	    title: f.title ?? videoId,
   348	    youtubeUrl: `https://youtu.be/${videoId}`,
   349	    language: 'en',
   350	    durationSeconds: 600,
   351	    archived: f.archived ?? false,
   352	    ratings: f.ratings ?? FLAT_RATINGS,
   353	    overallScore: f.overallScore ?? 4,
   354	    summaryMd,
   355	    processedAt: f.processedAt ?? '2026-01-01T00:00:00.000Z',
   356	    serialNumber: f.position ?? 1,
   357	    ...(f.docVersion ? { docVersion: f.docVersion } : {}),
   358	    ...(f.mdGeneratedAt ? { mdGeneratedAt: f.mdGeneratedAt } : {}),
   359	    ...(f.mdCorrectionsHash ? { mdCorrectionsHash: f.mdCorrectionsHash } : {}),
   360	    ...(f.videoType ? { videoType: f.videoType } : {}),

exec
/bin/bash -lc "nl -ba tests/integration/helpers/cloud.ts | sed -n '340,520p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   340	/** Build the `videos.data` jsonb / local Video record from the requested fields. Shape mirrors the
   341	 *  worker's promoted-video shape (seed.ts) but with full control over the Class-A/companion signals. */
   342	function buildVideoData(videoId: string, f: SeedFields): Record<string, unknown> {
   343	  const summaryMd = f.summaryMd === undefined ? `${videoId}.md` : f.summaryMd;
   344	  const base = summaryMd ? summaryMd.replace(/\.md$/, '') : null;
   345	  return {
   346	    id: videoId,
   347	    title: f.title ?? videoId,
   348	    youtubeUrl: `https://youtu.be/${videoId}`,
   349	    language: 'en',
   350	    durationSeconds: 600,
   351	    archived: f.archived ?? false,
   352	    ratings: f.ratings ?? FLAT_RATINGS,
   353	    overallScore: f.overallScore ?? 4,
   354	    summaryMd,
   355	    processedAt: f.processedAt ?? '2026-01-01T00:00:00.000Z',
   356	    serialNumber: f.position ?? 1,
   357	    ...(f.docVersion ? { docVersion: f.docVersion } : {}),
   358	    ...(f.mdGeneratedAt ? { mdGeneratedAt: f.mdGeneratedAt } : {}),
   359	    ...(f.mdCorrectionsHash ? { mdCorrectionsHash: f.mdCorrectionsHash } : {}),
   360	    ...(f.videoType ? { videoType: f.videoType } : {}),
   361	    ...(f.audience ? { audience: f.audience } : {}),
   362	    ...(f.tags ? { tags: f.tags } : {}),
   363	    ...(f.tldr ? { tldr: f.tldr } : {}),
   364	    ...(f.takeaways ? { takeaways: f.takeaways } : {}),
   365	    ...(f.personalNote !== undefined ? { personalNote: f.personalNote } : {}),
   366	    ...(f.personalScore !== undefined ? { personalScore: f.personalScore } : {}),
   367	    ...(f.corrections !== undefined ? { corrections: f.corrections } : {}),
   368	    ...(f.annotationsEditedAt ? { annotationsEditedAt: f.annotationsEditedAt } : {}),
   369	    ...(f.summaryHtml !== undefined ? { summaryHtml: f.summaryHtml } : {}),
   370	    ...(f.digDeeperHtml !== undefined ? { digDeeperHtml: f.digDeeperHtml } : {}),
   371	    ...(base || f.extraArtifacts
   372	      ? {
   373	          artifacts: {
   374	            ...(base ? { summaryMd: { key: `${base}.md`, status: f.status ?? 'promoted' } } : {}),
   375	            ...(f.extraArtifacts ?? {}),
   376	          },
   377	        }
   378	      : {}),
   379	    ...(f.raw ?? {}),
   380	  };
   381	}
   382	
   383	/** Seed the CLOUD side (playlist row created on first call) with a full-field video + MD blob. */
   384	export async function seedCloudVideo(ctx: Ctx, f: SeedFields = {}): Promise<void> {
   385	  await prepareSyncCtx(ctx);
   386	  const { adminClient } = await import('./clients');
   387	  const svc = adminClient();
   388	  if (!ctx.playlistId) {
   389	    const url = `https://www.youtube.com/playlist?list=${ctx.playlistKey}`;
   390	    const { data: pl, error } = await svc.from('playlists')
   391	      .insert({ owner_id: ctx.userId, playlist_key: ctx.playlistKey, playlist_url: url })
   392	      .select('id').single();
   393	    if (error) throw error;
   394	    ctx.playlistId = pl!.id as string;
   395	  }
   396	  const videoId = f.videoId ?? ctx.videoId;
   397	  const data = buildVideoData(videoId, f);
   398	  const { error: vErr } = await svc.from('videos').insert({
   399	    playlist_id: ctx.playlistId, owner_id: ctx.userId, video_id: videoId,
   400	    position: f.position ?? 1, data,
   401	  });
   402	  if (vErr) throw vErr;
   403	  const summaryMd = data.summaryMd as string | null;
   404	  if (summaryMd && f.mdBody != null) {
   405	    await seedSummaryBlob(svc, ctx.userId, ctx.playlistKey, summaryMd.replace(/\.md$/, ''), f.mdBody);
   406	  }
   407	}
   408	
   409	/** Seed the LOCAL side (FS replica) with a full-field video + MD blob (mirrors seedLocalVideo but
   410	 *  with full Class-A/companion control). Idempotently creates the local playlist dir + index. */
   411	export async function seedLocalVideoFull(ctx: Ctx, f: SeedFields = {}): Promise<void> {
   412	  await prepareSyncCtx(ctx);
   413	  const lp = ctx.localPrincipal;
   414	  const videoId = f.videoId ?? ctx.videoId;
   415	  await fs.mkdir(ctx.playlistDataRoot, { recursive: true });
   416	  await ctx.local.setPlaylistMeta(lp, { playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}` });
   417	  await ctx.local.claimVideoSlot(lp, videoId);
   418	  const data = buildVideoData(videoId, f);
   419	  await ctx.local.upsertVideo(lp, data as unknown as Video);
   420	  const summaryMd = data.summaryMd as string | null;
   421	  if (summaryMd && f.mdBody != null) {
   422	    await ctx.localBlob.put(lp, summaryMd, Buffer.from(f.mdBody, 'utf8'), 'text/markdown');
   423	  }
   424	}
   425	
   426	/** Seed a manifest baseline for ctx.videoId (drives baseline-aware Class-B + baseline-present
   427	 *  delete scenarios). Writes to the SAME manifest path runSync + ctx.readManifest resolve. */
   428	export async function seedManifestBaseline(ctx: Ctx, baseline: VideoBaseline): Promise<void> {
   429	  await writeVideoBaseline(ctx.playlistDataRoot, ctx.playlistKey, ctx.videoId, baseline);
   430	}
   431	
   432	/** Read ctx.videoId's record from the cloud replica (RLS-scoped user session — never service-role). */
   433	export async function cloudVideoRecord(ctx: Ctx): Promise<Video | null> {
   434	  const idx = await new SupabaseMetadataStore(ctx.userClient).readIndex(ctx.cloudPrincipal);
   435	  return idx.videos.find((v) => v.id === ctx.videoId) ?? null;
   436	}
   437	/** Read ctx.videoId's record from the local FS replica. */
   438	export async function localVideoRecord(ctx: Ctx): Promise<Video | null> {
   439	  const idx = await ctx.local.readIndex(ctx.localPrincipal);
   440	  return idx.videos.find((v) => v.id === ctx.videoId) ?? null;
   441	}
   442	/** Read a blob body off the cloud replica (RLS-scoped user session). */
   443	export async function cloudBlobBytes(ctx: Ctx, key: string): Promise<Buffer | null> {
   444	  return new SupabaseBlobStore(ctx.userClient, ARTIFACTS_BUCKET).get(ctx.cloudPrincipal, key);
   445	}
   446	/** Read a blob body off the local FS replica. */
   447	export async function localBlobBytes(ctx: Ctx, key: string): Promise<Buffer | null> {
   448	  return ctx.localBlob.get(ctx.localPrincipal, key);
   449	}

codex
The new B1 tests are structurally honest: `seedCloudVideo` defaults `summaryMd` and promoted `artifacts.summaryMd`, but skips the blob when `mdBody` is omitted, exactly exercising “advertised but unreadable.” They also loop two `runSync` calls and assert no baseline on both.
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
/bin/bash -lc "rg -n \"cloud-sync|integration\" package.json vitest.config.* jest.config.* tests -g '*.ts' -g '*.json'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 exited 2 in 0ms:
rg: vitest.config.*: No such file or directory (os error 2)
package.json:18:    "test:integration": "jest --config jest.integration.config.ts --runInBand",
package.json:22:    "cloud-sync": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/cloud-sync.ts"
tests/integration/middleware-2a.test.ts:3:// This file lives under tests/integration/ per the task brief's required path, but — like
tests/e2e/cloud-library.spec.ts:9: *   - Per-route integration tests against a REAL Supabase stack with `signInAs`
tests/e2e/cloud-library.spec.ts:10: *     (tests/integration/{playlists-route,videos-route-cloud,quickview-route-cloud,
tests/e2e/cloud-library.spec.ts:21: *      client (mirror tests/integration/helpers/seed.ts), sign in via Supabase to obtain
tests/integration/metadata-store.test.ts:1:// tests/integration/metadata-store.test.ts
tests/integration/metadata-store.test.ts:4:// Run via: npm run test:integration -- metadata-store
tests/integration/metadata-store.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/metadata-store.test.ts:21: *  validation — integration tests focus on store behaviour, not type fidelity. */
tests/integration/metadata-store.test.ts:38:describe('SupabaseMetadataStore integration', () => {
tests/integration/gemini-magazine-live.test.ts:9: * mirroring tests/integration/gemini-live-gates.test.ts.
tests/api/delete-playlist-route.test.ts:10:// and 6 (second delete ⇒ 404) are covered by the integration test
tests/api/delete-playlist-route.test.ts:11:// (tests/integration/delete-playlist-route.test.ts) against real local Supabase/RLS.
tests/integration/backfill-titles-route.test.ts:1:// tests/integration/backfill-titles-route.test.ts
tests/integration/backfill-titles-route.test.ts:4:// Supabase stack. Auth plumbing mocked exactly like tests/integration/playlists-route.test.ts
tests/integration/backfill-titles-route.test.ts:19:// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.
tests/integration/delete-playlist-route.test.ts:1:// tests/integration/delete-playlist-route.test.ts
tests/integration/delete-playlist-route.test.ts:4:// tests/integration/archive-route-cloud.test.ts: mock ONLY the next/headers +
tests/integration/delete-playlist-route.test.ts:27:// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
tests/integration/schema.test.ts:1:// tests/integration/schema.test.ts
tests/integration/share-summary-2c.test.ts:1:// tests/integration/share-summary-2c.test.ts
tests/integration/share-summary-2c.test.ts:3:// Stage 2c Task 8 — real-Supabase integration guard proving:
tests/integration/share-summary-2c.test.ts:9:// Run: npx supabase db reset && npm run test:integration -- share-summary-2c --runInBand
tests/integration/share-summary-2c.test.ts:27:describe('share-summary-2c integration', () => {
tests/integration/enqueue-dig.test.ts:1:// tests/integration/enqueue-dig.test.ts
tests/integration/enqueue-dig.test.ts:5:// service client — mirrors the setup in tests/integration/summary-handler.test.ts.
tests/integration/serve-config-invariant.test.ts:1:// tests/integration/serve-config-invariant.test.ts
tests/integration/serve-config-invariant.test.ts:7:// ORDER-SAFETY (Codex Critical #2): the full `test:integration --runInBand` suite shares ONE DB,
tests/integration/pdf-cloud.test.ts:1:// tests/integration/pdf-cloud.test.ts
tests/integration/pdf-cloud.test.ts:5:// tests could only mock. Mirrors tests/integration/html-download.test.ts's auth-plumbing pattern:
tests/integration/pdf-cloud.test.ts:56:// hoisted above these declarations) — same pattern as tests/integration/html-download.test.ts.
tests/integration/serve-model-charge.test.ts:1:// tests/integration/serve-model-charge.test.ts
tests/integration/blob-store.test.ts:1:// tests/integration/blob-store.test.ts
tests/integration/blob-store.test.ts:5:// Run via: npm run test:integration -- blob-store
tests/integration/blob-store.test.ts:6:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/blob-store.test.ts:25: *  validation — integration tests focus on store behaviour, not type fidelity. */
tests/integration/concurrency.test.ts:1:// tests/integration/concurrency.test.ts
tests/integration/concurrency.test.ts:5:// Run via: npm run test:integration -- concurrency
tests/integration/reservation-release.test.ts:502:    // guards against another integration file having mutated the shared guardrail_config singleton
tests/integration/reservation-release.test.ts:561:    // default, but guards against another integration file having mutated the shared singleton.
tests/integration/storage-policy.test.ts:1:// tests/integration/storage-policy.test.ts
tests/integration/cloud-sync/sync-run.int.test.ts:1:// tests/integration/cloud-sync/sync-run.int.test.ts
tests/integration/cloud-sync/sync-run.int.test.ts:3:// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
tests/integration/cloud-sync/sync-run.int.test.ts:14:import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/sync-run.int.test.ts:15:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/serve-doc-materialize.test.ts:33:// ── Owner-budget helpers (mirrors tests/integration/serve-owner-budget.test.ts — see that file's
tests/integration/backfill-titles.test.ts:1:// tests/integration/backfill-titles.test.ts
tests/integration/backfill-titles.test.ts:4:// live local Supabase stack. Run via: npm run test:integration -- backfill-titles
tests/integration/backfill-titles.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/backfill-titles.test.ts:20:describe('setPlaylistTitleIfNull integration', () => {
tests/integration/video-updated-at.test.ts:1:// tests/integration/video-updated-at.test.ts
tests/integration/rls-isolation.test.ts:1:// tests/integration/rls-isolation.test.ts
tests/integration/summary-handler.test.ts:1:// tests/integration/summary-handler.test.ts
tests/integration/summary-handler.test.ts:8:// Run via: npm run test:integration -- summary-handler
tests/integration/summary-handler.test.ts:9:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/cloud-sync/e2e.int.test.ts:1:// tests/integration/cloud-sync/e2e.int.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:18:} from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/e2e.int.test.ts:19:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/e2e.int.test.ts:20:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/integration/cloud-sync/e2e.int.test.ts:21:import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
tests/integration/cloud-sync/e2e.int.test.ts:22:import type { VideoBaseline } from '@/lib/cloud-sync/types';
tests/integration/cloud-sync/e2e.int.test.ts:53:describe('cloud-sync §10 end-to-end scenarios', () => {
tests/integration/cost-guardrails.test.ts:1:// tests/integration/cost-guardrails.test.ts
tests/integration/cost-guardrails.test.ts:284:  // this test/file) — with the full integration suite creating real auth users across many
tests/integration/quickview-route-cloud.test.ts:1:// tests/integration/quickview-route-cloud.test.ts
tests/integration/quickview-route-cloud.test.ts:4:// stack. Mirrors tests/integration/videos-route-cloud.test.ts (Task 5): mock ONLY the
tests/integration/quickview-route-cloud.test.ts:15:// hoisted above this declaration) — same pattern as tests/integration/videos-route-cloud.test.ts.
tests/integration/job-queue-producer.test.ts:1:// tests/integration/job-queue-producer.test.ts
tests/integration/provisioning.test.ts:1:// tests/integration/provisioning.test.ts
tests/integration/videos-route-cloud.test.ts:1:// tests/integration/videos-route-cloud.test.ts
tests/integration/videos-route-cloud.test.ts:9:// tests/integration/playlists-route.test.ts.
tests/integration/videos-route-cloud.test.ts:17:// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.
tests/integration/cloud-sync/cloud-stamping.int.test.ts:1:// tests/integration/cloud-sync/cloud-stamping.int.test.ts
tests/integration/cloud-sync/cloud-stamping.int.test.ts:7:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/dig-serve-interactive.test.ts:1:// tests/integration/dig-serve-interactive.test.ts
tests/integration/dig-serve-interactive.test.ts:3:// Task 6 (cloud dig-deeper frontend slice): REAL local-Supabase integration proof that the
tests/integration/dig-serve-interactive.test.ts:7:// tests/integration/archive-route-cloud.test.ts (mock next/headers + @/lib/supabase/server
tests/integration/dig-serve-interactive.test.ts:9:// blob-seeding pattern from tests/integration/dig-cloud.test.ts (writeDigSectionBlob writer,
tests/integration/dig-serve-interactive.test.ts:22:// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
tests/integration/dig-serve-interactive.test.ts:58:describe('cloud dig-deeper serve (integration, real DB) — interactive + no-charge', () => {
tests/integration/job-queue-store.test.ts:1:// tests/integration/job-queue-store.test.ts
tests/integration/cloud-sync/stamping.int.test.ts:1:// tests/integration/cloud-sync/stamping.int.test.ts
tests/integration/cloud-sync/stamping.int.test.ts:8:// Runs against local Supabase (jest.integration.config.ts). Uses the shared integration
tests/integration/cloud-sync/stamping.int.test.ts:10:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/playlists-route.test.ts:1:// tests/integration/playlists-route.test.ts
tests/integration/playlists-route.test.ts:8:// metadataStore.listPlaylists) runs for real. Same pattern as tests/integration/html-download.test.ts.
tests/integration/playlists-route.test.ts:18:// hoisted above this declaration) — same pattern as tests/integration/html-download.test.ts.
tests/integration/gemini-live-gates.test.ts:3: * (Stage 1D). These are NOT part of the normal CI/integration run — they make real, billed
tests/integration/annotations-rpc.test.ts:1:// tests/integration/annotations-rpc.test.ts
tests/integration/annotations-rpc.test.ts:4:// REAL local Supabase stack. Run via: npm run test:integration -- annotations-rpc
tests/integration/annotations-rpc.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/worker-storage-bundle.test.ts:1:// tests/integration/worker-storage-bundle.test.ts
tests/integration/html-download.test.ts:1:// tests/integration/html-download.test.ts
tests/integration/html-download.test.ts:24:// hoisted above this declaration) — same pattern as tests/integration/share-route.test.ts.
tests/integration/html-download.test.ts:90:// ── Stage 1G / Task 3 owner-budget helpers — replicated from tests/integration/serve-owner-budget.test.ts
tests/integration/supabase-blob-delete-prefix.test.ts:1:// tests/integration/supabase-blob-delete-prefix.test.ts
tests/integration/supabase-blob-delete-prefix.test.ts:7:// Run via: npm run test:integration -- supabase-blob-delete-prefix
tests/integration/supabase-blob-delete-prefix.test.ts:8:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/worker-main.test.ts:36:    // integration test files (e.g. job-queue-producer.test.ts intentionally leaves some
tests/integration/helpers/cloud.ts:1:// tests/integration/helpers/cloud.ts
tests/integration/helpers/cloud.ts:3:// Shared integration harness for Stage 3 Cloud Sync (Tasks 3, 4, 12, 14). Reuses the existing
tests/integration/helpers/cloud.ts:26:import { readManifest as readManifestFile, writeVideoBaseline } from '@/lib/cloud-sync/manifest';
tests/integration/helpers/cloud.ts:27:import type { SyncDeps } from '@/lib/cloud-sync/sync-run';
tests/integration/helpers/cloud.ts:28:import type { VideoBaseline } from '@/lib/cloud-sync/types';
tests/integration/helpers/cloud.ts:77: *  every cloud-sync integration test. */
tests/integration/cap-soundness.test.ts:1:// tests/integration/cap-soundness.test.ts
tests/integration/dig-cloud.test.ts:1:// tests/integration/dig-cloud.test.ts
tests/integration/dig-cloud.test.ts:3:// Task 7 (cloud dig-deeper generation slice): end-to-end integration against a REAL local
tests/integration/dig-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/pdf-cloud.test.ts for owner-isolation + spend
tests/integration/dig-cloud.test.ts:5:// mutation-control, and tests/integration/summary-handler.test.ts for the direct-handler blob
tests/integration/dig-cloud.test.ts:42:  // dig is the FIRST integration path that goes through enqueue_preflight — pin its admission
tests/integration/dig-cloud.test.ts:66:describe('dig-cloud (integration, real DB)', () => {
tests/integration/worker-persistence-rpcs.test.ts:1:// tests/integration/worker-persistence-rpcs.test.ts
tests/integration/serve-owner-budget.test.ts:1:// tests/integration/serve-owner-budget.test.ts
tests/integration/pdf-put-atomicity.test.ts:1:// tests/integration/pdf-put-atomicity.test.ts
tests/integration/pdf-put-atomicity.test.ts:32:// when STORAGE_BACKEND==='supabase' — same pattern as sibling *-cloud integration tests.
tests/integration/helpers/seed.ts:1:// tests/integration/helpers/seed.ts
tests/integration/list-playlists.test.ts:1:// tests/integration/list-playlists.test.ts
tests/integration/archive-route-cloud.test.ts:1:// tests/integration/archive-route-cloud.test.ts
tests/integration/archive-route-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/review-route-cloud.test.ts (Task 7): mock
tests/integration/archive-route-cloud.test.ts:17:// hoisted above this declaration) — same pattern as tests/integration/review-route-cloud.test.ts.
tests/integration/review-route-cloud.test.ts:1:// tests/integration/review-route-cloud.test.ts
tests/integration/review-route-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/quickview-route-cloud.test.ts (Task 6): mock
tests/integration/review-route-cloud.test.ts:16:// hoisted above this declaration) — same pattern as tests/integration/quickview-route-cloud.test.ts.
tests/integration/worker-runner-runtime.test.ts:13:// tests/integration/job-queue-worker.test.ts and job-queue-runner.test.ts.
tests/lib/cloud-sync/auth-file-store.test.ts:4:import { makeFileTokenStore } from '@/lib/cloud-sync/auth';
tests/lib/cloud-sync/cli.test.ts:1:import { parseArgs } from '@/scripts/cloud-sync';
tests/lib/cloud-sync/reconcile-class-a.test.ts:1:import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';
tests/lib/cloud-sync/reconcile-class-a.test.ts:2:import type { ClassASignals } from '@/lib/cloud-sync/types';
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion } from '@/lib/cloud-sync/companion';
tests/lib/cloud-sync/reconcile-class-b.test.ts:1:import { reconcileField } from '@/lib/cloud-sync/reconcile-class-b';
tests/api/backfill-titles-route.test.ts:19:// Behaviors 3 and 7 (real backfill + owner isolation) are covered by the integration test
tests/api/backfill-titles-route.test.ts:20:// (tests/integration/backfill-titles-route.test.ts) against real local Supabase/RLS.
tests/lib/dig/slide-crop.integration.test.ts:1:// tests/lib/dig/slide-crop.integration.test.ts
tests/lib/dig/slide-crop.integration.test.ts:7:describe('ffmpeg profile (integration — real ffmpeg)', () => {
tests/api/dig-cloud-route.test.ts:6: * and tests/components (verified — no tests/app pattern exists). tests/integration is a SEPARATE
tests/api/dig-cloud-route.test.ts:7: * jest project (jest.integration.config.ts) that runs against a real local Supabase stack, which
tests/lib/cloud-sync/registry.test.ts:1:import { playlistKeyFromUrl, unionPlaylistKeys } from '@/lib/cloud-sync/registry';
tests/lib/cloud-sync/import-guard.test.ts:5:// cloud-sync source would be skipped and the guard would pass vacuously). Assert the scan is
tests/lib/cloud-sync/import-guard.test.ts:17:const cloudSyncSources = walk(join(root, 'lib/cloud-sync')).filter((f) => existsSync(f));
tests/lib/cloud-sync/import-guard.test.ts:27:describe('Task 10 (§6) — cloud-sync auth never reaches the service-role key', () => {
tests/lib/cloud-sync/import-guard.test.ts:40:  it('scans a non-empty set of cloud-sync sources', () => {
tests/lib/cloud-sync/import-guard.test.ts:42:    expect(cloudSyncSources.some((f) => f.endsWith('lib/cloud-sync/auth.ts'))).toBe(true);
tests/lib/cloud-sync/regenerate-stamp.test.ts:1:// tests/lib/cloud-sync/regenerate-stamp.test.ts
tests/lib/cloud-sync/regenerate-stamp.test.ts:27:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/cloud-sync/manifest.test.ts:1:// tests/lib/cloud-sync/manifest.test.ts
tests/lib/cloud-sync/manifest.test.ts:5:import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';
tests/lib/cloud-sync/manifest.test.ts:34:  const log = await fs.readFile(path.join(r, 'PL1', '.cloud-sync-conflicts.log'), 'utf8');
tests/lib/cloud-sync/backfill.test.ts:1:import { deriveClassASignals, deriveHumanSnapshot } from '@/lib/cloud-sync/backfill';
tests/lib/cloud-sync/backfill.test.ts:2:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/lib/cloud-sync/local-stamping.test.ts:1:// tests/lib/cloud-sync/local-stamping.test.ts
tests/lib/cloud-sync/auth.test.ts:1:import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
tests/lib/cloud-sync/auth.test.ts:11:    await expect(getAuthedClient(memStore(null))).rejects.toThrow(/cloud-sync login/);
tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
tests/lib/pipeline-async.test.ts:83:describe('B2: runIngestion awaits every store call (delayed-store integration)', () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:1:// tests/lib/cloud-sync/model-writer-hash.test.ts
tests/lib/cloud-sync/model-writer-hash.test.ts:16:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/storage/supabase-job-queue-cancel-playlist.test.ts:8: * in supabase-job-queue.ts). Owner-guard/cascade behavior is covered by the integration
tests/lib/storage/supabase-job-queue-cancel-playlist.test.ts:9: * suite (tests/integration/cancel-playlist-jobs.test.ts, delete-playlist-store.test.ts).
tests/lib/html-doc/serve-doc-mapping.test.ts:2:// Unlike tests/integration/serve-doc-materialize.test.ts, these do NOT hit a real Supabase project:

exec
/bin/bash -lc 'git status --short && git branch --show-current && git rev-parse --short HEAD' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
 M docs/local-validation-findings.md
 M supabase/config.toml
?? .codex-tasks/
?? docs/reviews/task-12-sync-run-behaviors-codex.md
?? docs/reviews/whole-branch-cloud-sync-v4-rereview-codex.md
?? scratchpad/
feat/stage3-cloud-sync
3bc8cc7

codex
One residual weakness I’m testing mentally is row disappearance between the initial read and a later two-sided finalize, since `transferClassA` does not re-read the receiver after `updateVideoFields`. That looks like a concurrency edge rather than a shipped deterministic branch failure; I’m not treating it as a convergence blocker unless I can tie it to a concrete normal-run path.
exec
/bin/bash -lc 'npm test -- --runInBand tests/lib/cloud-sync && npm run test:integration -- cloud-sync/e2e.int.test.ts --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 20569ms:

> youtube-playlist-summaries@0.1.0 test
> jest --runInBand tests/lib/cloud-sync


Test Suites: 15 passed, 15 total
Tests:       85 passed, 85 total
Snapshots:   0 total
Time:        4.849 s, estimated 11 s
Ran all test suites matching tests/lib/cloud-sync.

> youtube-playlist-summaries@0.1.0 test:integration
> jest --config jest.integration.config.ts --runInBand cloud-sync/e2e.int.test.ts --runInBand

Test Suites: 1 passed, 1 total
Tests:       24 passed, 24 total
Snapshots:   0 total
Time:        9.76 s, estimated 11 s
Ran all test suites matching cloud-sync/e2e.int.test.ts.

codex
Targeted tests pass: 15 cloud-sync unit suites and the cloud-sync e2e integration file, including the B1 two-run regressions. I’m doing one last pass over the review trail for known/deferred boundaries so I don’t re-report an already-adjudicated issue.
exec
/bin/bash -lc 'rg -n "''^#|Blocking|High|Medium|Low|CONVERGED|NOT CONVERGED|B1|H-R2|M-R2|DEFER|Deferred|KNOWN" docs/reviews/whole-branch-cloud-sync-codex.md docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:1:# Whole-branch re-review (ROUND 3, Claude adversarial) — `feat/stage3-cloud-sync`
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:12:Claude-R2-M1 (stale non-`summaryMd` artifact pointers), Codex-R2-Medium (absent companion scalars),
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:17:## Part A — are the round-2 fixes genuinely fixed?
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:19:### H-R2-1 — validate the MD body BEFORE claiming the receiver slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:32:- **Later throws on the additive path still leave partial state**, but none reproduce the H-R2-1
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:47:### H-R2-2 — `digDeeperMd` preserved on `transferClassA`
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:76:### M-R2-2 — corrections guard narrowed to `la.mdHash != null && ca.mdHash != null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:77:**Verdict: NOT FIXED SAFELY — the narrowing predicate is wrong and reopens WB-B1. See B1.**
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:88:holds an MD". It does not mean that. See B1.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:92:## Part B — new findings
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:94:### B1 (BLOCKING) — `mdHash == null` conflates "has no MD" with "MD is unreadable", so an unreadable blob silently destroys the other replica's body and launders it into an agreed baseline
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:101:denial), not just 404. The additive path knows this and guards it explicitly (H-R2-1, `:160`). The
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:102:two-sided path has **no equivalent guard**, and M-R2-2 has now routed the corrections-conflict case
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:108:**P1 — the WB-B1 destruction, back.** Local holds a corrected body with `corrections: 'A'`; cloud has
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:118:WB-B1 was filed to prevent — and it is silent (`errors: []`).
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:133:**Why this is Blocking, not High:** silent, unrecoverable destruction of user content triggered by an
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:135:replicas agree. It also forces a full re-generation to recover — a money finding of the H-R2-2 class.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:136:P2 predates round 2 (it is not a regression); **P1 is newly introduced by M-R2-2**.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:146:mean what they claim: the side genuinely advertises no MD. M-R2-2's intent survives intact, because
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:150:### M1 (Medium) — with `digDeeperMd` preserved, the dig-deeper view renders the PRE-SYNC summary when the two replicas' MD keys differ
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:168:Medium, not High: no data is lost, dig is out of scope for M2a (spec §line 35), it requires diverged
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:170:pre-`32a164c`; the H-R2-2 fix restored it rather than introducing it. Cleanest fix lives outside
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:176:## Checked and clean
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:189:  paths: the H-R2-2 class is fixed; B1 is a new one and is counted as such above.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:194:  new one-sided-hydration branches. The only laundering path found is B1.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:198:  asymmetry between the two backends is B1.
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:204:**NOT CONVERGED** — 1 new Blocking (B1: unreadable-blob conflation destroys the other replica's MD
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:205:and records a false agreement; reproduced in two forms, one of them newly opened by the M-R2-2
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:206:narrowing) plus 1 Medium. Part A: H-R2-1 genuinely fixed, H-R2-2 genuinely fixed, M-R2-2 fixed the
docs/reviews/whole-branch-cloud-sync-v3-rereview-claude.md:207:stranding but with an unsafe predicate. Another round is required after B1.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:1:# Whole-branch re-review (ROUND 2, Claude adversarial) — `feat/stage3-cloud-sync`
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:13:## Part A — verification of the round-1 fixes
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:15:### WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:47:### WB-H1 (High) — additive create could advertise `promoted` with no blob
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:48:**Verdict: GENUINELY FIXED** (with one Low on residual partial state, below).
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:65:- **Partial state after the throw** — see Part B L1. It is self-healing; not a High.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:67:### WB-H2 (High) — two-sided transfer left stale rendered HTML
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:69:Part B **H1** (new High).**
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:105:## Part B — new findings
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:107:### H1 (High) — `transferClassA` nulls `digDeeperMd`, orphaning the loser's paid dig-deeper doc
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:143:### M1 (Medium) — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:154:regenerable HTML is gated on the top-level `summaryHtml`, which *is* nulled. Hence Medium, not High. But
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:159:### M2 (Medium) — the WB-B1 guard also blocks purely-additive (non-destructive) MD hydration
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:171:correctness bug — Medium. Consider narrowing the guard to the genuinely destructive case (both sides have
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:172:an MD body, i.e. `la.mdHash != null && ca.mdHash != null`), which preserves the WB-B1 fix's intent exactly
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:175:### L1 (Low) — the WB-H1 throw leaves a bare receiver slot; converges, but via a different code path
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:195:## Items explicitly checked and found clean
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:199:  trigger. The WB-B1 e2e test asserts `spendLedgerTotal()` is unchanged across the run.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:216:- **Idempotency.** Ran each new branch twice mentally; WB-B1 is additionally covered by an explicit
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:221:**NOT CONVERGED** — 1 new High (H1: `digDeeperMd: null` destroys the local loser's paid dig-deeper doc, a
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:222:regression introduced by the WB-H2 fix), plus 2 Mediums and 1 Low. Another round is required after H1 is
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:227:## Coordinator adjudication (post-review, 2026-07-18)
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:230:Codex rated it **High**; this review rated it **L1 (Low)**. I adjudicated against the code.
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:244:**High**, tracked as **H-R2-1**, and is being fixed by validating the MD body BEFORE
docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md:248:baseline/idempotency effects require running `runSync` TWICE — as the WB-B1 test already does.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:16:Round 1 found 1 Blocking + 2 High. They were fixed in commit `32a164c` (the branch HEAD). Your job has TWO explicit parts:
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:18:## Part A — verify each round-1 fix is GENUINELY fixed, not reworded
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:19:1. **WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy.** Fix: in `runSync` (`lib/cloud-sync/sync-run.ts`), when `merges.corrections.winner === 'equal' && merges.corrections.conflict`, skip the Class-A copy entirely, count `needsRegen`, and write `buildCorrectionsUnresolvedBaseline` (carries the PREVIOUS classA baseline, or an honest `{docVersionMajor:0, mdGeneratedAt:null, mdCorrectionsHash:null, mdHash:null}` placeholder on first sync). VERIFY: is the guard placed BEFORE every write path (including the companion transfer and any archived/delete handling)? Does the `continue` skip anything that MUST still run (delete-inference "seen" marking, report counters, companion, archived sync)? Is `report.archivedNotSynced` incremented correctly and only there? Does the placeholder baseline (docVersionMajor 0) cause a wrong decision anywhere that DOES read the Class-A baseline — confirm reconcileClassA truly never reads it.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:20:2. **WB-H1 (High) — additive create could advertise `promoted` with no blob.** Fix: throw when `video.summaryMd` is set but `mdBody == null`; strip `sanitized.artifacts.summaryMd` when no blob was written; post-write verify that the receiver row advertises `status==='promoted'` at the right key. VERIFY: does the throw leave PARTIAL state (a bare receiver slot created by `ensureReceiverSlot`, a staged blob orphaned) that a later run mishandles? Is the summary-less video (summaryMd == null) path still correct? Does the strict post-write assert produce false failures on the local store (shallow-merge) vs the cloud store (`merge_video_data` deep-merge) — a cross-backend semantic mismatch?
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:21:3. **WB-H2 (High) — two-sided transfer left stale rendered HTML.** Fix: `transferClassA` sets `summaryHtml/digDeeperHtml/digDeeperMd` to `null` in the update payload. VERIFY: does `merge_video_data` (migration 0021 / 0009) actually STORE a JSON null (invalidating) rather than treating null as "no change" and skipping the key — trace the RPC body. Same question for the local store's shallow merge. If null is dropped by either backend, the fix is cosmetic and the stale-HTML bug survives. Also: are there OTHER regenerable-cache fields that should have been nulled (compare against `sanitizeAdditiveVideo`'s strip list — any field it strips that transferClassA does not null is a gap), and does nulling `digDeeperMd` orphan or strand a dig-deeper blob / dig state?
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:23:## Part B — hunt for NEW defects the fixes introduced or exposed
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:32:## Scope
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:35:KNOWN-and-ACCEPTED (do NOT re-report unless you show they mask a real bug): T14-M1 (put→updateVideoFields two non-txn writes, self-healing), T14-M2 (no failCloudPut fault test for two-sided transfer), T5 test-coverage gaps, T4 automock comment inaccuracy.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:37:## Output
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:38:For each finding: severity (Blocking/High/Medium/Low), `file:line`, the concrete failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. For Part A, state explicitly per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:429:/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:512:        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:990:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1546:   380	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:1629:   463	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2354:    31	  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2388:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2438:   388	  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2443:   393	  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:2628:     6	// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3074:tests/integration/cloud-sync/e2e.int.test.ts:388:  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3112:lib/cloud-sync/sync-run.ts:380:/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3121:WB-B1: GENUINELY FIXED. The guard is before Class-A signal derivation, transfer, companion transfer, normal archived counter, and normal baseline advance in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:471). It still logs Class-B conflicts before the guard, increments `needsRegen`, increments `archivedNotSynced` only for archived divergence, writes a baseline so delete inference has seen the video, then continues. `reconcileClassA` takes only live `ClassASignals`, not manifest Class-A baselines, so the `{ docVersionMajor: 0, mdHash: null }` placeholder is not read by the Class-A decision code.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3129:High: partial additive failure creates a receiver slot, then a later run can falsely baseline a video whose source MD blob is still missing.  
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3136:Medium: Class-A transfer does not clear absent companion scalars, so stale loser metadata can survive beside the winner MD.  
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3145:NOT CONVERGED.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3150:WB-B1: GENUINELY FIXED. The guard is before Class-A signal derivation, transfer, companion transfer, normal archived counter, and normal baseline advance in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:471). It still logs Class-B conflicts before the guard, increments `needsRegen`, increments `archivedNotSynced` only for archived divergence, writes a baseline so delete inference has seen the video, then continues. `reconcileClassA` takes only live `ClassASignals`, not manifest Class-A baselines, so the `{ docVersionMajor: 0, mdHash: null }` placeholder is not read by the Class-A decision code.
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3158:High: partial additive failure creates a receiver slot, then a later run can falsely baseline a video whose source MD blob is still missing.  
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3165:Medium: Class-A transfer does not clear absent companion scalars, so stale loser metadata can survive beside the winner MD.  
docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md:3174:NOT CONVERGED.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:17:- Round 1 (`docs/reviews/whole-branch-cloud-sync-codex.md`) → 1 Blocking + 2 High → fixed in `32a164c`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:18:- Round 2 (`docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md` and `-claude.md`) → confirmed WB-B1/WB-H2 fixed, found WB-H1 INCOMPLETE (H-R2-1) plus a REGRESSION introduced by the WB-H2 fix (H-R2-2) and a Medium (M-R2-2) → fixed in `1f54c60`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:22:## Part A — verify each round-2 fix is GENUINELY fixed, not reworded
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:23:1. **H-R2-1** — the unreadable-MD-body guard moved ABOVE `ensureReceiverSlot` in `copyAdditiveVideo` (`lib/cloud-sync/sync-run.ts`). VERIFY: is there now NO path that creates partial receiver state before a possible throw (consider `setPlaylistMeta` inside `ensureReceiverSlot`, the staged-blob put, and `claimVideoSlot`)? Does the two-run e2e assertion actually fail if the guard is moved back? Is the residual `if (video.summaryMd && mdBody != null)` condition at the staging block dead/redundant given the guard above, and if so does that redundancy hide anything?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:24:2. **H-R2-2** — `digDeeperMd: null` removed from `transferClassA`'s `completeTuple`. VERIFY: with `digDeeperMd` preserved but the MD BODY replaced by the winner's, is the retained dig doc now semantically stale in a way that misleads a consumer (`lib/html-doc/build-doc-html.ts:75,86`, `app/api/videos/[id]/dig-state/route.ts`, `lib/pdf/pdf-path.ts`)? Specifically: dig sections are anchored to summary section timestamps/anchors — if the winner MD has different sections, does merging the preserved dig produce wrong or orphaned anchors? Weigh that against the cost of destroying paid content. Is `digDeeperHtml: null` sufficient to force the re-merge? Is the additive path (`sanitizeAdditiveVideo`, which still nulls `digDeeperMd`) still correct given it targets a receiver with no existing row?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:25:3. **M-R2-2** — the corrections guard narrowed to `correctionsUnresolved && la.mdHash != null && ca.mdHash != null`, with `deriveClassASignals` hoisted above the guard. VERIFY: the hoist claims to be behavior-neutral because derivation is pure — confirm `readMdBody` has no side effects and that moving TWO blob reads earlier cannot change ordering/error behavior (e.g. a blob read that throws now aborts the video BEFORE the Class-B baseline would have been written — is that a behavior change, and is it the right one?). Confirm the WB-B1 intent still holds exactly for the both-have-MD case. Confirm the one-sided hydration case cannot destroy anything or record a false agreement.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:27:## Part B — hunt for NEW defects the round-2 fixes introduced or exposed
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:30:- Money-safety: no enqueue, no `spend_ledger` consumption, no regenerable-cache resurrection; `needsRegen` report-only. ALSO: any path that forces the USER to re-spend (the H-R2-2 class of bug) counts as a money finding.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:36:## Scope
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:39:KNOWN-and-ACCEPTED / DEFERRED — do NOT re-report unless you prove they mask a real bug: T14-M1, T14-M2, T5 coverage gaps, T4 automock comment; Claude-R2-M1 (stale non-`summaryMd` artifact pointers on transfer); Codex-R2-Medium (absent/undefined companion scalars not explicitly cleared). Also do NOT report `tests/integration/reservation-release.test.ts` failures — verified pre-existing on a clean tree (local Supabase state pollution), tracked separately.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:41:## Output
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:42:Per finding: severity (Blocking/High/Medium/Low), `file:line`, concrete failure scenario (inputs → wrong outcome), fix. For Part A, state per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:64:Round 1 found 1 Blocking + 2 High. They were fixed in commit `32a164c` (the branch HEAD). Your job has TWO explicit parts:
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:66:## Part A — verify each round-1 fix is GENUINELY fixed, not reworded
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:67:1. **WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy.** Fix: in `runSync` (`lib/cloud-sync/sync-run.ts`), when `merges.corrections.winner === 'equal' && merges.corrections.conflict`, skip the Class-A copy entirely, count `needsRegen`, and write `buildCorrectionsUnresolvedBaseline` (carries the PREVIOUS classA baseline, or an honest `{docVersionMajor:0, mdGeneratedAt:null, mdCorrectionsHash:null, mdHash:null}` placeholder on first sync). VERIFY: is the guard placed BEFORE every write path (including the companion transfer and any archived/delete handling)? Does the `continue` skip anything that MUST still run (delete-inference "seen" marking, report counters, companion, archived sync)? Is `report.archivedNotSynced` incremented correctly and only there? Does the placeholder baseline (docVersionMajor 0) cause a wrong decision anywhere that DOES read the Class-A baseline — confirm reconcileClassA truly never reads it.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:68:2. **WB-H1 (High) — additive create could advertise `promoted` with no blob.** Fix: throw when `video.summaryMd` is set but `mdBody == null`; strip `sanitized.artifacts.summaryMd` when no blob was written; post-write verify that the receiver row advertises `status==='promoted'` at the right key. VERIFY: does the throw leave PARTIAL state (a bare receiver slot created by `ensureReceiverSlot`, a staged blob orphaned) that a later run mishandles? Is the summary-less video (summaryMd == null) path still correct? Does the strict post-write assert produce false failures on the local store (shallow-merge) vs the cloud store (`merge_video_data` deep-merge) — a cross-backend semantic mismatch?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:69:3. **WB-H2 (High) — two-sided transfer left stale rendered HTML.** Fix: `transferClassA` sets `summaryHtml/digDeeperHtml/digDeeperMd` to `null` in the update payload. VERIFY: does `merge_video_data` (migration 0021 / 0009) actually STORE a JSON null (invalidating) rather than treating null as "no change" and skipping the key — trace the RPC body. Same question for the local store's shallow merge. If null is dropped by either backend, the fix is cosmetic and the stale-HTML bug survives. Also: are there OTHER regenerable-cache fields that should have been nulled (compare against `sanitizeAdditiveVideo`'s strip list — any field it strips that transferClassA does not null is a gap), and does nulling `digDeeperMd` orphan or strand a dig-deeper blob / dig state?
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:71:## Part B — hunt for NEW defects the fixes introduced or exposed
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:80:## Scope
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:83:KNOWN-and-ACCEPTED (do NOT re-report unless you show they mask a real bug): T14-M1 (put→updateVideoFields two non-txn writes, self-healing), T14-M2 (no failCloudPut fault test for two-sided transfer), T5 test-coverage gaps, T4 automock comment inaccuracy.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:85:## Output
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:86:For each finding: severity (Blocking/High/Medium/Low), `file:line`, the concrete failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. For Part A, state explicitly per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:313:# Whole-branch re-review (ROUND 2, Claude adversarial) — `feat/stage3-cloud-sync`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:325:## Part A — verification of the round-1 fixes
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:327:### WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:359:### WB-H1 (High) — additive create could advertise `promoted` with no blob
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:360:**Verdict: GENUINELY FIXED** (with one Low on residual partial state, below).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:377:- **Partial state after the throw** — see Part B L1. It is self-healing; not a High.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:379:### WB-H2 (High) — two-sided transfer left stale rendered HTML
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:381:Part B **H1** (new High).**
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:417:## Part B — new findings
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:419:### H1 (High) — `transferClassA` nulls `digDeeperMd`, orphaning the loser's paid dig-deeper doc
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:455:### M1 (Medium) — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:466:regenerable HTML is gated on the top-level `summaryHtml`, which *is* nulled. Hence Medium, not High. But
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:471:### M2 (Medium) — the WB-B1 guard also blocks purely-additive (non-destructive) MD hydration
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:483:correctness bug — Medium. Consider narrowing the guard to the genuinely destructive case (both sides have
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:484:an MD body, i.e. `la.mdHash != null && ca.mdHash != null`), which preserves the WB-B1 fix's intent exactly
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:487:### L1 (Low) — the WB-H1 throw leaves a bare receiver slot; converges, but via a different code path
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:507:## Items explicitly checked and found clean
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:511:  trigger. The WB-B1 e2e test asserts `spendLedgerTotal()` is unchanged across the run.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:528:- **Idempotency.** Ran each new branch twice mentally; WB-B1 is additionally covered by an explicit
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:533:**NOT CONVERGED** — 1 new High (H1: `digDeeperMd: null` destroys the local loser's paid dig-deeper doc, a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:534:regression introduced by the WB-H2 fix), plus 2 Mediums and 1 Low. Another round is required after H1 is
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:539:## Coordinator adjudication (post-review, 2026-07-18)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:542:Codex rated it **High**; this review rated it **L1 (Low)**. I adjudicated against the code.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:556:**High**, tracked as **H-R2-1**, and is being fixed by validating the MD body BEFORE
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:560:baseline/idempotency effects require running `runSync` TWICE — as the WB-B1 test already does.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:565:1f54c60 (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:576:    fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:579:    WB-B1 and WB-H2 genuinely fixed; WB-H1 was INCOMPLETE and WB-H2 introduced a regression.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:581:    H-R2-1 (High) — copyAdditiveVideo claimed the receiver slot BEFORE validating the MD
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:589:    H-R2-2 (High, regression from the WB-H2 fix) — transferClassA nulled digDeeperMd, which
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:595:    M-R2-2 (Medium) — the WB-B1 corrections guard skipped Class A unconditionally, stranding
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:599:    Deferred with owner: stale non-summaryMd artifact pointers on transfer; absent companion
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:698:+  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:875:+    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:950: /** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1033:         // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1048:+        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1066:+        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1141:   // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1146:   it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1192:+  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1197:+  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1246:+  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1252:+  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1277:+  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1281:+  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1476:   154	  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1644:   322	    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1718:   396	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1801:   479	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1816:   494	        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1830:   508	        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1911:lib/storage/resolve.ts:24: *  CRITICAL (Codex Blocking): preserve the RAW outputFolder string — do NOT
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1950:tests/integration/cloud-sync/e2e.int.test.ts:393:  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1966:tests/integration/cloud-sync/e2e.int.test.ts:489:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:1969:tests/integration/cloud-sync/e2e.int.test.ts:495:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2034:lib/cloud-sync/sync-run.ts:322:    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2058:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2105:lib/pdf/pdf-concurrency.ts:20:/** Acquire a slot or throw PdfBusyError; release ONLY IF acquired, in finally (round-3 Low). */
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2134:tests/lib/cloud-sync/regenerate-stamp.test.ts:6:// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2160:lib/html-doc/serve-doc.ts:57:  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2207:/bin/bash -lc 'git status --short && rg -n "H-R2-1|H-R2-2|M-R2-2|WB-H1|WB-H2|WB-B1|corrections conflict|digDeeperMd" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2215:tests/integration/cloud-sync/e2e.int.test.ts:388:  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2216:tests/integration/cloud-sync/e2e.int.test.ts:393:  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2218:tests/integration/cloud-sync/e2e.int.test.ts:438:  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2219:tests/integration/cloud-sync/e2e.int.test.ts:443:  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2222:tests/integration/cloud-sync/e2e.int.test.ts:489:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2224:tests/integration/cloud-sync/e2e.int.test.ts:495:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2229:tests/integration/cloud-sync/e2e.int.test.ts:520:  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2231:tests/integration/cloud-sync/e2e.int.test.ts:524:  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2704:   388	  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2709:   393	  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2754:   438	  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2759:   443	  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2805:   489	  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2811:   495	  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2836:   520	  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2840:   524	  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2906:    31	  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:2936:     6	// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3790:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:3866:I haven’t found a new Blocking/High so far. The only live concern is lower severity: the M-R2-2 regression test proves first-run hydration, but it does not assert second-run idempotency or manifest shape for that new branch. I’m deciding whether that is a defect or only a coverage gap.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4413:/bin/bash -lc 'npx jest tests/integration/cloud-sync/e2e.int.test.ts --runInBand -t "H-R2-1|H-R2-2|M-R2-2|WB-B1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4641:/bin/bash -lc 'npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1|H-R2-2|M-R2-2|WB-B1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4645:> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1|H-R2-2|M-R2-2|WB-B1
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4651:Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1|H-R2-2|M-R2-2|WB-B1".
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4654:The targeted integration tests pass: 4 selected tests, 18 skipped in that file. To answer the specific “would it fail if moved back?” question, I’m doing a temporary mutation of `copyAdditiveVideo`, running the H-R2-1 test, then restoring the file.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4670:-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4706:-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4731:/bin/bash -lc 'npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4744:-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4771:> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4774:  ● cloud-sync §10 end-to-end scenarios › WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4794:Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1".
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4802:`sync-run.ts` is back to HEAD behavior. I’m doing one final targeted pass for worktree cleanliness and the restored H-R2-1 test.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4814:/bin/bash -lc 'git diff -- lib/cloud-sync/sync-run.ts && npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4818:> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4824:Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1".
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4902:The restored H-R2-1 test passes again. I’m running the cloud-sync integration subset now for the broader branch-level check, still excluding the known reservation-release suite.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4932:H-R2-1: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4933:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160) now throws before `ensureReceiverSlot` at line 164, so no `setPlaylistMeta`, staged blob write, `claimVideoSlot`, receiver row, or baseline can happen after an unreadable advertised MD body. The remaining `if (video.summaryMd && mdBody != null)` at line 167 is redundant after the guard, but harmless; it does not hide a path because the only alternative is a legitimate summary-less row. I temporarily moved the guard back and the H-R2-1 integration test failed on the bare local row assertion, then restored the file.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4935:H-R2-2: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4938:M-R2-2: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4939:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:491) derives signals before the narrowed guard, and [lib/cloud-sync/backfill.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/backfill.ts:7) is pure over the record plus supplied MD body. The hoist can surface blob-read errors earlier, but that is the right behavior: baseline must not advance if Class-A evidence is unreadable. The both-have-MD conflict path still takes the WB-B1 skip at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:501). The one-sided hydration path writes the copied MD only after `transferClassA` lands, preserves unresolved corrections in Class-B baseline, and continues to report `needsRegen`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4943:No new Blocking, High, Medium, or Low defects found in the reviewed scope.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4951:Temporary mutation of H-R2-1 failed as expected, then restored; `lib/cloud-sync/sync-run.ts` has no remaining diff.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4953:**CONVERGED**
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4958:H-R2-1: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4959:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160) now throws before `ensureReceiverSlot` at line 164, so no `setPlaylistMeta`, staged blob write, `claimVideoSlot`, receiver row, or baseline can happen after an unreadable advertised MD body. The remaining `if (video.summaryMd && mdBody != null)` at line 167 is redundant after the guard, but harmless; it does not hide a path because the only alternative is a legitimate summary-less row. I temporarily moved the guard back and the H-R2-1 integration test failed on the bare local row assertion, then restored the file.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4961:H-R2-2: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4964:M-R2-2: **GENUINELY FIXED**  
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4965:Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:491) derives signals before the narrowed guard, and [lib/cloud-sync/backfill.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/backfill.ts:7) is pure over the record plus supplied MD body. The hoist can surface blob-read errors earlier, but that is the right behavior: baseline must not advance if Class-A evidence is unreadable. The both-have-MD conflict path still takes the WB-B1 skip at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:501). The one-sided hydration path writes the copied MD only after `transferClassA` lands, preserves unresolved corrections in Class-B baseline, and continues to report `needsRegen`.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4969:No new Blocking, High, Medium, or Low defects found in the reviewed scope.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4977:Temporary mutation of H-R2-1 failed as expected, then restored; `lib/cloud-sync/sync-run.ts` has no remaining diff.
docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md:4979:**CONVERGED**
docs/reviews/whole-branch-cloud-sync-codex.md:16:## Scope
docs/reviews/whole-branch-cloud-sync-codex.md:25:## The invariants to verify hold END-TO-END (across tasks, on the shipped code)
docs/reviews/whole-branch-cloud-sync-codex.md:35:## Also
docs/reviews/whole-branch-cloud-sync-codex.md:37:- Consider these KNOWN-and-ACCEPTED minors (do NOT re-report unless you find they mask a real bug): T12-M2 (copyAdditiveVideo post-write verify checks row presence not payload), T14-M1 (put→updateVideoFields two non-txn writes, self-healing), T14-M2 (no failCloudPut fault test for two-sided transfer), T5 test-coverage gaps, T4 automock comment inaccuracy.
docs/reviews/whole-branch-cloud-sync-codex.md:39:## Output
docs/reviews/whole-branch-cloud-sync-codex.md:40:For each NEW finding: severity (Blocking/High/Medium/Low), file:line, the concrete cross-task failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. Triage the accepted-minors list: any that must be fixed before merge vs defer. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
docs/reviews/whole-branch-cloud-sync-codex.md:423:tests/integration/share-route.test.ts:228:  it('B12: token pointing at an un-promoted (committed) doc → 404', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:424:tests/integration/share-route.test.ts:247:  it('B13b: MD blob missing behind a promoted status → 404 (never 500)', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:425:tests/integration/share-route.test.ts:291:  it('B10b: video un-promoted (artifacts.summaryMd.status flipped away from promoted) between the initial resolve and the mandatory pre-response re-check → 404', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:427:tests/integration/share-route.test.ts:304:      // (D14/B10b) — the re-check reads `videos.data.artifacts.summaryMd.status` fresh, so this
docs/reviews/whole-branch-cloud-sync-codex.md:1345:tests/api/html-serve-cloud.test.ts:100:it('B13b: promoted but MD blob null → repair-needed 409', async () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1448:lib/cloud-sync/backfill.ts:6:// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-codex.md:1581:lib/html-doc/serve-summary-core.ts:51:  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)
docs/reviews/whole-branch-cloud-sync-codex.md:1585:lib/html-doc/serve-summary-core.ts:67:  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)
docs/reviews/whole-branch-cloud-sync-codex.md:1705:tests/lib/cloud-sync/model-writer-hash.test.ts:6:// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
docs/reviews/whole-branch-cloud-sync-codex.md:1737:tests/lib/cloud-sync/reconcile-class-a.test.ts:19:  it('mdHash equal but one current, one stale → current wins, NOT skip (Blocking ③ scenario 1)', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1739:tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1885:tests/lib/cloud-sync/backfill.test.ts:14:it('hashes the MD BODY, not the summaryMd key (Blocking ①)', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:1926:tests/lib/cloud-sync/regenerate-stamp.test.ts:6:// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
docs/reviews/whole-branch-cloud-sync-codex.md:2143:tests/lib/producer.test.ts:115:  expect(failedEntry).toEqual({ videoId: 'v1', error: 'enqueue failed' });   // review High — no raw error leak
docs/reviews/whole-branch-cloud-sync-codex.md:2381:  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
docs/reviews/whole-branch-cloud-sync-codex.md:2894:// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
docs/reviews/whole-branch-cloud-sync-codex.md:3181:  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
docs/reviews/whole-branch-cloud-sync-codex.md:3377:  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
docs/reviews/whole-branch-cloud-sync-codex.md:3378:  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)
docs/reviews/whole-branch-cloud-sync-codex.md:3394:  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)
docs/reviews/whole-branch-cloud-sync-codex.md:4650:  -- (whole-branch round-2 H-R2-1) → KEEP. attempts=0 subsumes not v_ever_metered; both kept defensively.
docs/reviews/whole-branch-cloud-sync-codex.md:4689:                                                   -- requeue that may have billed (round-2 H-R2-1) → excluded
docs/reviews/whole-branch-cloud-sync-codex.md:4833:  const language = langRaw?.toLowerCase() === 'ko' ? 'ko' : 'en';
docs/reviews/whole-branch-cloud-sync-codex.md:5333:    // Stage 3 (§5.1/§5.7, former-Blocking §5.3): stamp this regenerated MD as
docs/reviews/whole-branch-cloud-sync-codex.md:5569:// GENERATE-FREE LEAF (spec D13/B18c): this module and its entire import graph must never
docs/reviews/whole-branch-cloud-sync-codex.md:6190:// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
docs/reviews/whole-branch-cloud-sync-codex.md:6215:# A Title
docs/reviews/whole-branch-cloud-sync-codex.md:6221:## 1. First
docs/reviews/whole-branch-cloud-sync-codex.md:6224:## Conclusion
docs/reviews/whole-branch-cloud-sync-codex.md:6361:describe('B18c — read-model.ts is a generate-free leaf', () => {
docs/reviews/whole-branch-cloud-sync-codex.md:6444:tests/lib/cloud-sync/model-writer-hash.test.ts:6:// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
docs/reviews/whole-branch-cloud-sync-codex.md:7349: *  CRITICAL (Codex Blocking): preserve the RAW outputFolder string — do NOT
docs/reviews/whole-branch-cloud-sync-codex.md:7462:1. **Blocking**: `lib/cloud-sync/sync-run.ts:407`
docs/reviews/whole-branch-cloud-sync-codex.md:7470:2. **High**: `lib/cloud-sync/sync-run.ts:112`, `lib/cloud-sync/sync-run.ts:164`, `lib/cloud-sync/sync-run.ts:169`
docs/reviews/whole-branch-cloud-sync-codex.md:7478:3. **Medium**: `lib/html-doc/read-model.ts:20`, `lib/html-doc/read-model.ts:37`, `lib/html-doc/read-model.ts:52`
docs/reviews/whole-branch-cloud-sync-codex.md:7494:**NOT CONVERGED**
docs/reviews/whole-branch-cloud-sync-codex.md:7499:1. **Blocking**: `lib/cloud-sync/sync-run.ts:407`
docs/reviews/whole-branch-cloud-sync-codex.md:7507:2. **High**: `lib/cloud-sync/sync-run.ts:112`, `lib/cloud-sync/sync-run.ts:164`, `lib/cloud-sync/sync-run.ts:169`
docs/reviews/whole-branch-cloud-sync-codex.md:7515:3. **Medium**: `lib/html-doc/read-model.ts:20`, `lib/html-doc/read-model.ts:37`, `lib/html-doc/read-model.ts:52`
docs/reviews/whole-branch-cloud-sync-codex.md:7531:**NOT CONVERGED**

exec
/bin/bash -lc 'git log --oneline --decorate --max-count=8 && git show --stat --oneline 32a164c 1f54c60 3bc8cc7' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
3bc8cc7 (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
1f54c60 fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
32a164c fix(cloud-sync): whole-branch review — corrections-conflict no destructive copy, additive promoted-without-blob guard, transfer HTML-cache invalidation (WB-B1/H1/H2)
255b80e test(cloud-sync): end-to-end §10 scenarios (anti-recency, carried scalars, money-safety, deletes)
83065d5 feat(cloud-sync): cloud-sync CLI (sync/login/logout) (§9)
4cf2730 feat(cloud-sync): sync-run orchestration — two-class reconcile, atomic transfer, manifest-after-commit (§7)
15ba0ed feat(cloud-sync): local playlist discovery + key derivation + union (§7.1)
c98b294 feat(cloud-sync): Supabase-Auth session + fail-closed token store + confinement coverage (§6)
32a164c fix(cloud-sync): whole-branch review — corrections-conflict no destructive copy, additive promoted-without-blob guard, transfer HTML-cache invalidation (WB-B1/H1/H2)
 lib/cloud-sync/sync-run.ts                   | 82 ++++++++++++++++++++++++--
 tests/integration/cloud-sync/e2e.int.test.ts | 88 ++++++++++++++++++++++++++++
 2 files changed, 164 insertions(+), 6 deletions(-)
1f54c60 fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
 docs/reviews/whole-branch-cloud-sync-codex.md      | 7531 ++++++++++++++++++++
 .../whole-branch-cloud-sync-v2-rereview-claude.md  |  248 +
 .../whole-branch-cloud-sync-v2-rereview-codex.md   | 3174 +++++++++
 lib/cloud-sync/sync-run.ts                         |   55 +-
 tests/integration/cloud-sync/e2e.int.test.ts       |   86 +-
 5 files changed, 11076 insertions(+), 18 deletions(-)
3bc8cc7 fix(cloud-sync): round-3 whole-branch re-review — an unreadable MD body must not read as "no MD" (B1, Blocking)
 .../whole-branch-cloud-sync-v3-rereview-claude.md  |  207 +
 .../whole-branch-cloud-sync-v3-rereview-codex.md   | 4979 ++++++++++++++++++++
 lib/cloud-sync/sync-run.ts                         |   19 +
 lib/storage/supabase/supabase-blob-store.ts        |    8 +-
 tests/integration/cloud-sync/e2e.int.test.ts       |   76 +
 5 files changed, 5288 insertions(+), 1 deletion(-)

exec
/bin/bash -lc 'rg -n "cloud-sync|runSync|readMdBody|copyAdditiveVideo|transferClassA|companionTransfer|readModelEnvelope|SupabaseBlobStore|LocalFsBlobStore|readManifest|writeVideoBaseline|merge_video_data|update_video_annotations|persist_summary|sourceMdHash" lib tests/integration/cloud-sync tests/lib/cloud-sync supabase/migrations/0021_* supabase/migrations/0009_*' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:104:create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:116:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:155:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:157:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:158:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
supabase/migrations/0021_cloud_sync_signals.sql:6:--     update_video_annotations / merge_video_data with `create or replace` would create a
supabase/migrations/0021_cloud_sync_signals.sql:12:--     defaulted function. (persist_summary keeps its 5-arg signature unchanged → no drop needed.)
supabase/migrations/0021_cloud_sync_signals.sql:13:drop function if exists update_video_annotations(uuid, text, jsonb, text[]);
supabase/migrations/0021_cloud_sync_signals.sql:14:drop function if exists merge_video_data(uuid, text, jsonb);
supabase/migrations/0021_cloud_sync_signals.sql:16:-- (1) update_video_annotations: add corrections to the allowlist; stamp per-field
supabase/migrations/0021_cloud_sync_signals.sql:19:create or replace function update_video_annotations(
supabase/migrations/0021_cloud_sync_signals.sql:57:revoke all on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) from public;
supabase/migrations/0021_cloud_sync_signals.sql:58:grant execute on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) to authenticated;
supabase/migrations/0021_cloud_sync_signals.sql:60:-- (2) merge_video_data: conditional annotationsEditedAt restamp when a Class-B key is
supabase/migrations/0021_cloud_sync_signals.sql:62:create or replace function merge_video_data(
supabase/migrations/0021_cloud_sync_signals.sql:92:revoke all on function merge_video_data(uuid, text, jsonb, timestamptz) from public;
supabase/migrations/0021_cloud_sync_signals.sql:93:grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;
supabase/migrations/0021_cloud_sync_signals.sql:95:-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
supabase/migrations/0021_cloud_sync_signals.sql:99:create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0021_cloud_sync_signals.sql:111:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0021_cloud_sync_signals.sql:152:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0021_cloud_sync_signals.sql:154:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0021_cloud_sync_signals.sql:155:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
tests/lib/cloud-sync/auth-file-store.test.ts:4:import { makeFileTokenStore } from '@/lib/cloud-sync/auth';
tests/integration/cloud-sync/sync-run.int.test.ts:1:// tests/integration/cloud-sync/sync-run.int.test.ts
tests/integration/cloud-sync/sync-run.int.test.ts:3:// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
tests/integration/cloud-sync/sync-run.int.test.ts:15:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/sync-run.int.test.ts:23:describe('runSync (§7)', () => {
tests/integration/cloud-sync/sync-run.int.test.ts:29:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:51:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:63:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cloud-sync/sync-run.int.test.ts:68:    const m = await ctx.readManifest();
tests/lib/cloud-sync/cli.test.ts:1:import { parseArgs } from '@/scripts/cloud-sync';
tests/lib/cloud-sync/reconcile-class-a.test.ts:1:import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';
tests/lib/cloud-sync/reconcile-class-a.test.ts:2:import type { ClassASignals } from '@/lib/cloud-sync/types';
tests/lib/cloud-sync/local-stamping.test.ts:1:// tests/lib/cloud-sync/local-stamping.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:1:// tests/integration/cloud-sync/e2e.int.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:4:// driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
tests/integration/cloud-sync/e2e.int.test.ts:6:// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
tests/integration/cloud-sync/e2e.int.test.ts:19:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/e2e.int.test.ts:20:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/integration/cloud-sync/e2e.int.test.ts:21:import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
tests/integration/cloud-sync/e2e.int.test.ts:22:import type { VideoBaseline } from '@/lib/cloud-sync/types';
tests/integration/cloud-sync/e2e.int.test.ts:53:describe('cloud-sync §10 end-to-end scenarios', () => {
tests/integration/cloud-sync/e2e.int.test.ts:55:  //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
tests/integration/cloud-sync/e2e.int.test.ts:72:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:77:    // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
tests/integration/cloud-sync/e2e.int.test.ts:115:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:137:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:155:    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
tests/integration/cloud-sync/e2e.int.test.ts:177:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:206:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:224:    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
tests/integration/cloud-sync/e2e.int.test.ts:234:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:247:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:278:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:293:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:297:    const m1 = await ctx.readManifest();
tests/integration/cloud-sync/e2e.int.test.ts:300:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:304:    const m2 = await ctx.readManifest();
tests/integration/cloud-sync/e2e.int.test.ts:313:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:326:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:337:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:340:    const m1 = await ctx.readManifest();
tests/integration/cloud-sync/e2e.int.test.ts:343:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:356:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cloud-sync/e2e.int.test.ts:364:    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:376:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:383:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:407:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:426:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:435:  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
tests/integration/cloud-sync/e2e.int.test.ts:440:  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
tests/integration/cloud-sync/e2e.int.test.ts:448:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:454:    // Baseline not advanced — the throw aborted before writeVideoBaseline.
tests/integration/cloud-sync/e2e.int.test.ts:455:    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:459:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:463:    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:481:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:510:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:538:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:571:    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
tests/integration/cloud-sync/e2e.int.test.ts:580:      const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:593:      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:615:      const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:625:      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
tests/lib/cloud-sync/registry.test.ts:1:import { playlistKeyFromUrl, unionPlaylistKeys } from '@/lib/cloud-sync/registry';
tests/lib/cloud-sync/model-writer-hash.test.ts:1:// tests/lib/cloud-sync/model-writer-hash.test.ts
tests/lib/cloud-sync/model-writer-hash.test.ts:4:// and asserts the persisted model envelope's sourceMdHash is the hash of the MD BODY that was
tests/lib/cloud-sync/model-writer-hash.test.ts:14:import { readModelEnvelope } from '../../../lib/html-doc/model-store';
tests/lib/cloud-sync/model-writer-hash.test.ts:16:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/cloud-sync/model-writer-hash.test.ts:70:it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:79:  const env = await readModelEnvelope(principal, 'a-title');
tests/lib/cloud-sync/model-writer-hash.test.ts:81:  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
tests/lib/cloud-sync/model-writer-hash.test.ts:82:  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion } from '@/lib/cloud-sync/companion';
tests/lib/cloud-sync/companion.test.ts:4:const env = (sourceMdHash?: string): ModelEnvelope => ({
tests/lib/cloud-sync/companion.test.ts:7:  ...(sourceMdHash ? { sourceMdHash } : {}),
tests/lib/cloud-sync/companion.test.ts:17:it('deletes when the legacy envelope lacks sourceMdHash', () => {
tests/integration/cloud-sync/cloud-stamping.int.test.ts:1:// tests/integration/cloud-sync/cloud-stamping.int.test.ts
tests/integration/cloud-sync/cloud-stamping.int.test.ts:6:// `opts.editedAt` through to update_video_annotations.
tests/integration/cloud-sync/cloud-stamping.int.test.ts:21:  it('cloud store forwards opts.editedAt through updateVideoFields (merge_video_data)', async () => {
tests/lib/cloud-sync/auth.test.ts:1:import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
tests/lib/cloud-sync/auth.test.ts:11:    await expect(getAuthedClient(memStore(null))).rejects.toThrow(/cloud-sync login/);
tests/lib/cloud-sync/manifest.test.ts:1:// tests/lib/cloud-sync/manifest.test.ts
tests/lib/cloud-sync/manifest.test.ts:5:import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';
tests/lib/cloud-sync/manifest.test.ts:11:  expect(await readManifest(r, 'PL1')).toEqual({ version: 1, videos: {} });
tests/lib/cloud-sync/manifest.test.ts:18:  expect(await readManifest(r, 'PL1')).toEqual({ version: 1, videos: {} });
tests/lib/cloud-sync/manifest.test.ts:25:  await writeVideoBaseline(r, 'PL1', 'v1', base as any);
tests/lib/cloud-sync/manifest.test.ts:26:  expect((await readManifest(r, 'PL1')).videos.v1).toEqual(base);
tests/lib/cloud-sync/manifest.test.ts:34:  const log = await fs.readFile(path.join(r, 'PL1', '.cloud-sync-conflicts.log'), 'utf8');
tests/lib/cloud-sync/regenerate-stamp.test.ts:1:// tests/lib/cloud-sync/regenerate-stamp.test.ts
tests/lib/cloud-sync/regenerate-stamp.test.ts:27:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
tests/lib/cloud-sync/reconcile-class-b.test.ts:1:import { reconcileField } from '@/lib/cloud-sync/reconcile-class-b';
tests/integration/cloud-sync/stamping.int.test.ts:1:// tests/integration/cloud-sync/stamping.int.test.ts
tests/integration/cloud-sync/stamping.int.test.ts:4:// behavior: per-field annotationsEditedAt on update_video_annotations/merge_video_data,
tests/integration/cloud-sync/stamping.int.test.ts:6:// persist_summary's mdGeneratedAt/mdCorrectionsHash passthrough.
tests/integration/cloud-sync/stamping.int.test.ts:13:  it('update_video_annotations stamps only the changed Class-B field, not archived', async () => {
tests/integration/cloud-sync/stamping.int.test.ts:16:    await ctx.rpc('update_video_annotations', {
tests/integration/cloud-sync/stamping.int.test.ts:32:    await ctx.rpc('update_video_annotations', {
tests/integration/cloud-sync/stamping.int.test.ts:44:    await ctx.rpc('update_video_annotations', {
tests/integration/cloud-sync/stamping.int.test.ts:58:    await ctx.rpc('update_video_annotations', {
tests/integration/cloud-sync/stamping.int.test.ts:64:    // Same for merge_video_data's 3-key call:
tests/integration/cloud-sync/stamping.int.test.ts:65:    await ctx.rpc('merge_video_data', { p_playlist_id: playlistId, p_video_id: videoId, p_fields: { corrections: 'z' } });
tests/integration/cloud-sync/stamping.int.test.ts:72:    await ctx.rpc('update_video_annotations', {
tests/integration/cloud-sync/stamping.int.test.ts:80:  it('merge_video_data does NOT stamp annotationsEditedAt for a non-Class-B (MD-finalize) write', async () => {
tests/integration/cloud-sync/stamping.int.test.ts:83:    await ctx.rpc('merge_video_data', {
tests/integration/cloud-sync/stamping.int.test.ts:90:  it('persist_summary stamps mdGeneratedAt + mdCorrectionsHash', async () => {
tests/lib/cloud-sync/import-guard.test.ts:5:// cloud-sync source would be skipped and the guard would pass vacuously). Assert the scan is
tests/lib/cloud-sync/import-guard.test.ts:17:const cloudSyncSources = walk(join(root, 'lib/cloud-sync')).filter((f) => existsSync(f));
tests/lib/cloud-sync/import-guard.test.ts:27:describe('Task 10 (§6) — cloud-sync auth never reaches the service-role key', () => {
tests/lib/cloud-sync/import-guard.test.ts:40:  it('scans a non-empty set of cloud-sync sources', () => {
tests/lib/cloud-sync/import-guard.test.ts:42:    expect(cloudSyncSources.some((f) => f.endsWith('lib/cloud-sync/auth.ts'))).toBe(true);
tests/lib/cloud-sync/backfill.test.ts:1:import { deriveClassASignals, deriveHumanSnapshot } from '@/lib/cloud-sync/backfill';
tests/lib/cloud-sync/backfill.test.ts:2:import { mdHash } from '@/lib/cloud-sync/content-hash';
lib/html-doc/rerender.ts:6:import { readModelEnvelope } from './model-store';
lib/html-doc/rerender.ts:43:  const envelope = await readModelEnvelope(principal, base, resolvedBlob);
lib/html-doc/model-store.ts:22:    sourceMdHash: z.string().optional(),
lib/html-doc/model-store.ts:24:  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
lib/html-doc/model-store.ts:25:  // must not make an old reader's readModelEnvelope return null (§5.7 round-5 M-2).
lib/html-doc/model-store.ts:53:export async function readModelEnvelope(
tests/lib/cloud-sync/schema.test.ts:32:  it('accepts an optional sourceMdHash', () => {
tests/lib/cloud-sync/schema.test.ts:33:    expect(ModelEnvelopeSchema.parse({ ...env, sourceMdHash: 'deadbeef' }).sourceMdHash).toBe('deadbeef');
lib/cloud-sync/auth.ts:6:  constructor() { super('Not signed in to cloud. Run: cloud-sync login'); this.name = 'NoSessionError'; }
lib/cloud-sync/auth.ts:75:  return path.join(home, '.config', 'youtube-playlist-summaries', 'cloud-sync-token');
lib/html-doc/build-doc-html.ts:7:import { readModelEnvelope } from './model-store';
lib/html-doc/build-doc-html.ts:124:  const envelope = await readModelEnvelope(getPrincipal(outputFolder), base);
lib/cloud-sync/sync-run.ts:1:// lib/cloud-sync/sync-run.ts
lib/cloud-sync/sync-run.ts:4:// T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
lib/cloud-sync/sync-run.ts:14://    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
lib/cloud-sync/sync-run.ts:31:  readManifest, writeVideoBaseline, appendConflict, resetConflictDedup,
lib/cloud-sync/sync-run.ts:35:import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
lib/cloud-sync/sync-run.ts:59:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
lib/cloud-sync/sync-run.ts:145:async function copyAdditiveVideo(
lib/cloud-sync/sync-run.ts:157:  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
lib/cloud-sync/sync-run.ts:276:async function transferClassA(
lib/cloud-sync/sync-run.ts:279:  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
lib/cloud-sync/sync-run.ts:281:    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
lib/cloud-sync/sync-run.ts:289:    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
lib/cloud-sync/sync-run.ts:292:  // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
lib/cloud-sync/sync-run.ts:319:    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
lib/cloud-sync/sync-run.ts:330:    // whereas transferClassA PATCHES a row that already holds its own state.
lib/cloud-sync/sync-run.ts:333:    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
lib/cloud-sync/sync-run.ts:345:async function companionTransfer(
lib/cloud-sync/sync-run.ts:350:  const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
lib/cloud-sync/sync-run.ts:413:export async function runSync(
lib/cloud-sync/sync-run.ts:439:    const manifest = await readManifest(dataRoot, key);
lib/cloud-sync/sync-run.ts:457:            const body = await readMdBody(from.blob, from.p, present);
lib/cloud-sync/sync-run.ts:458:            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
lib/cloud-sync/sync-run.ts:460:            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
lib/cloud-sync/sync-run.ts:491:        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
lib/cloud-sync/sync-run.ts:492:        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
lib/cloud-sync/sync-run.ts:494:        // ── B1 (round 3) — the two-sided counterpart of copyAdditiveVideo's WB-H1/H-R2-1 guard (:160).
lib/cloud-sync/sync-run.ts:495:        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
lib/cloud-sync/sync-run.ts:523:          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
lib/cloud-sync/sync-run.ts:539:          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
lib/cloud-sync/sync-run.ts:543:          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
lib/cloud-sync/sync-run.ts:551:          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
lib/cloud-sync/sync-run.ts:558:        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
lib/cloud-sync/companion.ts:13:  if (senderEnvelope && senderEnvelope.sourceMdHash === winnerMdHash) {
lib/html-doc/generate.ts:7:import { mdHash } from '@/lib/cloud-sync/content-hash';
lib/html-doc/generate.ts:59:    sourceMdHash: mdHash(md),
lib/html-doc/generate.ts:67:  // Atomic write via resolvedBlob (LocalFsBlobStore uses temp+rename; cloud impls upload directly).
lib/html-doc/serve-summary-core.ts:114:    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
lib/storage/resolve.ts:9:import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
lib/storage/resolve.ts:59:      blobStore: new SupabaseBlobStore(ctx.supabaseClient, ARTIFACTS_BUCKET),
lib/storage/resolve.ts:82:    blobStore: new SupabaseBlobStore(serviceClient, ARTIFACTS_BUCKET),
lib/cloud-sync/manifest.ts:1:// lib/cloud-sync/manifest.ts
lib/cloud-sync/manifest.ts:9:  return path.join(dataRoot, playlistKey, '.cloud-sync-manifest.json');
lib/cloud-sync/manifest.ts:12:  return path.join(dataRoot, playlistKey, '.cloud-sync-conflicts.log');
lib/cloud-sync/manifest.ts:15:export async function readManifest(dataRoot: string, playlistKey: string): Promise<Manifest> {
lib/cloud-sync/manifest.ts:31:export async function writeVideoBaseline(
lib/cloud-sync/manifest.ts:34:  const m = await readManifest(dataRoot, playlistKey);
lib/pdf/generate-doc-pdf.ts:15: * - The rendered PDF bytes are written atomically via blobStore (LocalFsBlobStore uses temp+rename;
lib/html-doc/read-model.ts:5:import { readModelEnvelope } from './model-store';
lib/html-doc/read-model.ts:36:  const existing = await readModelEnvelope(principal, base, blobStore);
lib/html-doc/read-model.ts:51:  const existing = await readModelEnvelope(principal, base, blobStore);
lib/html-doc/serve-doc.ts:7:import { mdHash } from '@/lib/cloud-sync/content-hash';
lib/html-doc/serve-doc.ts:47:   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
lib/html-doc/serve-doc.ts:48:   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
lib/html-doc/serve-doc.ts:110:      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
lib/job-queue/summary-handler.ts:167:    // don't start the irreversible blob/persist sequence. (Full lease-fencing of persist_summary is
lib/storage/metadata-store.ts:43:   *  owner_id = auth.uid() guard server-side, in SQL (update_video_annotations RPC) —
lib/storage/metadata-store.ts:44:   *  this is a distinct write path from updateVideoFields/merge_video_data, which is
lib/pipeline.ts:17:import { mdHash } from './cloud-sync/content-hash';
lib/storage/local/local-blob-store.ts:7:export class LocalFsBlobStore implements BlobStore {
lib/storage/local/local-blob-store.ts:73:export const localBlobStore = new LocalFsBlobStore();
lib/storage/worker-persistence.ts:16:/** Thin wrapper over the persist_summary RPC (Task 2). Merges `video` into
lib/storage/worker-persistence.ts:22:  const { error } = await client.rpc('persist_summary', {
lib/storage/supabase/supabase-blob-store.ts:7:export class SupabaseBlobStore implements BlobStore {
lib/storage/supabase/supabase-blob-store.ts:28:    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately
lib/storage/supabase/supabase-metadata-store.ts:118:  // Stage 3 (§5.1/§5.7): merge_video_data (0021) stamps annotationsEditedAt server-side
lib/storage/supabase/supabase-metadata-store.ts:130:    const { error } = await this.client.rpc('merge_video_data', {
lib/storage/supabase/supabase-metadata-store.ts:148:    const { error } = await this.client.rpc('merge_video_data_bulk', {
lib/storage/supabase/supabase-metadata-store.ts:248:  // updateVideoAnnotations: distinct write path from updateVideoFields/merge_video_data
lib/storage/supabase/supabase-metadata-store.ts:250:  // the owner_id = auth.uid() guard are enforced IN SQL by update_video_annotations — this
lib/storage/supabase/supabase-metadata-store.ts:267:    const { data, error } = await this.client.rpc('update_video_annotations', {
lib/dig/cloud/load-dig-for-serve.ts:4:import { readModelEnvelope, type ModelEnvelope } from '@/lib/html-doc/model-store';
lib/dig/cloud/load-dig-for-serve.ts:30:  const envelope = await readModelEnvelope(load.principal, load.base, load.bundle.blobStore); // cached, free; null if absent

exec
/bin/bash -lc 'npm run test:integration -- cloud-sync --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 17023ms:

> youtube-playlist-summaries@0.1.0 test:integration
> jest --config jest.integration.config.ts --runInBand cloud-sync --runInBand


Test Suites: 4 passed, 4 total
Tests:       37 passed, 37 total
Snapshots:   0 total
Time:        13.917 s, estimated 15 s
Ran all test suites matching cloud-sync.

codex
Part A: **GENUINELY FIXED**

Evidence:
- The new guard at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:510) covers the two-sided path after both MD bodies are read and before:
  - unresolved corrections guard
  - `reconcileClassA`
  - `transferClassA`
  - companion model transfer
  - baseline advance
- The one-sided/additive path was already guarded at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160), before receiver slot creation.
- `transferClassA` only reads the winner body after `reconcileClassA`; with the new guard, a winner that advertises `summaryMd` but whose body is unreadable cannot reach it.
- `companionTransfer` only runs after a successful Class-A transfer and uses an already-computed `winnerMdHash`, so unreadable MD cannot be reinterpreted there as “no model source.”
- Legitimate `summaryMd == null` still works: the guard is keyed on `video.summaryMd && mdHash == null`, so true summary-less videos pass.
- M-R2-2 still works: a real one-sided MD hydration with the other side `summaryMd == null` is not blocked.

Throwing is the right response for this fix. A permanently missing advertised blob will produce a per-video `report.errors` entry every run, but `runSync` catches per video and continues processing the rest. More importantly, it does not write a false baseline, does not infer agreement, and does not overwrite the other side. The user can repair by restoring the blob, clearing the stale `summaryMd`, or regenerating intentionally.

The two new B1 regression tests are honest. They seed a row that advertises promoted `summaryMd` while omitting the blob, assert byte preservation, assert no baseline, and repeat across two runs. Removing the guard would fail on the intended destructive-copy/laundering assertions.

Part B: no new Blocking/High/Medium/Low findings found in the reviewed scope.

Verification run:
- `npm test -- --runInBand tests/lib/cloud-sync` → 15 suites / 85 tests passed
- `npm run test:integration -- cloud-sync --runInBand` → 4 suites / 37 tests passed

**CONVERGED**
tokens used
147,924
Part A: **GENUINELY FIXED**

Evidence:
- The new guard at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:510) covers the two-sided path after both MD bodies are read and before:
  - unresolved corrections guard
  - `reconcileClassA`
  - `transferClassA`
  - companion model transfer
  - baseline advance
- The one-sided/additive path was already guarded at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160), before receiver slot creation.
- `transferClassA` only reads the winner body after `reconcileClassA`; with the new guard, a winner that advertises `summaryMd` but whose body is unreadable cannot reach it.
- `companionTransfer` only runs after a successful Class-A transfer and uses an already-computed `winnerMdHash`, so unreadable MD cannot be reinterpreted there as “no model source.”
- Legitimate `summaryMd == null` still works: the guard is keyed on `video.summaryMd && mdHash == null`, so true summary-less videos pass.
- M-R2-2 still works: a real one-sided MD hydration with the other side `summaryMd == null` is not blocked.

Throwing is the right response for this fix. A permanently missing advertised blob will produce a per-video `report.errors` entry every run, but `runSync` catches per video and continues processing the rest. More importantly, it does not write a false baseline, does not infer agreement, and does not overwrite the other side. The user can repair by restoring the blob, clearing the stale `summaryMd`, or regenerating intentionally.

The two new B1 regression tests are honest. They seed a row that advertises promoted `summaryMd` while omitting the blob, assert byte preservation, assert no baseline, and repeat across two runs. Removing the guard would fail on the intended destructive-copy/laundering assertions.

Part B: no new Blocking/High/Medium/Low findings found in the reviewed scope.

Verification run:
- `npm test -- --runInBand tests/lib/cloud-sync` → 15 suites / 85 tests passed
- `npm run test:integration -- cloud-sync --runInBand` → 4 suites / 37 tests passed

**CONVERGED**
