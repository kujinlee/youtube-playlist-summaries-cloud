Reading additional input from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019f73c3-29b2-7a32-90b7-9e73fed5cfaa
--------
user
You are an adversarial WHOLE-BRANCH reviewer for the Stage 3 Cloud Sync (M2a) feature branch `feat/stage3-cloud-sync`. All 14 implementation tasks are committed and each passed an independent per-task review. Your job now: hunt for CROSS-TASK defects the per-task reviews could NOT see (invariants that span task boundaries), with a bias toward money-safety, atomicity, RLS/no-service-role, and schema/migration correctness. Do NOT re-litigate settled per-task decisions; surface only genuine defects.

## Scope
The 16 implementation commits are `00f3643..255b80e` (HEAD). Review the SHIPPED code (final state), not intermediate commits. Key files:
- `lib/cloud-sync/*.ts` (content-hash, types, backfill, reconcile-class-a, reconcile-class-b, companion, manifest, registry, auth, sync-run)
- `supabase/migrations/0021_cloud_sync_signals.sql`
- `lib/storage/local/local-metadata-store.ts`, `lib/index-store.ts`, `lib/storage/supabase/supabase-metadata-store.ts`, `lib/html-doc/generate.ts`, `lib/html-doc/serve-doc.ts`, `lib/html-doc/serve-summary-core.ts`, `lib/pipeline.ts`, `app/api/videos/[id]/regenerate/route.ts`, `types/index.ts`, `lib/html-doc/model-store.ts`
- `scripts/cloud-sync.ts`, `scripts/check-service-confinement.ts`
- Tests: `tests/lib/cloud-sync/*`, `tests/integration/cloud-sync/*`, `tests/integration/helpers/cloud.ts`
- The design spec (authoritative): `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`

## The invariants to verify hold END-TO-END (across tasks, on the shipped code)
1. **MONEY — a sync copy NEVER charges.** Trace EVERY write path in `runSync` (additive create `copyAdditiveVideo`, two-sided `transferClassA`, Class-B `applyClassBWinners`, companion): none may import/call `lib/job-queue/producer.ts` or any enqueue, consume `spend_ledger`, or resurrect regenerable cache (summaryHtml/dig/PDF). `sanitizeAdditiveVideo` must strip regenerable cache + replica-local ordering but keep Class-A scalars/md-signals/human-fields/annotationsEditedAt. Confirm the reservation→release money path (spend_ledger, already-merged) is NOT regressed by the store-layer changes (T4 touched supabase-metadata-store / local-metadata-store / merge_video_data via 0021).
2. **mdHash is MD-BODY-only and CONSISTENT across tasks.** T1 canonicalizes (LF + one trailing newline + NFC). T4 stamps `sourceMdHash = mdHash(body)` at generate.ts + serve-doc.ts. T5 `deriveClassASignals` hashes the mdBody param. T8 `decideCompanion` compares `sourceMdHash === winnerMdHash`. T12 hashes bodies read via BlobStore. Verify NO path hashes `video.summaryMd` (the KEY/filename) instead of the body — a single key-hash anywhere breaks companion/reconcile equality.
3. **ATOMICITY.** Manifest baseline written ONLY after the receiver tuple verifies durable. Blob durable BEFORE the record advertises `artifacts.summaryMd.status='promoted'`. Additive create verifies the receiver row exists (readIndex) before the baseline (cloud upsertVideo silently no-ops on an absent row → ensureReceiverSlot creates it). transferClassA's fix (put-overwrite the final key with verified staged bytes, then updateVideoFields) preserves durable-before-finalize. Crash before verify leaves the baseline unadvanced (re-run heals).
4. **buildBaseline no-write conflict.** For a Class-B `winner==='equal' && conflict` (backfilled both-changed), carry `previousBaseline` UNCHANGED — advancing to the winner's value is a false agreement that silently overwrites the human value next run (§5.5). Baseline advances for every reconciled two-sided video including skip.
5. **RECONCILE ORDER + correctness.** Class B FIRST (→ reconciledCorrectionsHash) THEN Class A. reconcileClassA priority: corrections-current > format(higher docVersionMajor, never downgrade) > recency; the mdHash-equal skip is EXACTLY (both-current) OR (both-stale + same-major), else fall through. One-sided videos resolved by the presence branch, never reach `deriveHumanSnapshot(null)` (NPE).
6. **NO SERVICE-ROLE on the sync path.** All cloud I/O under the authenticated user session (anon key + JWT), RLS `owner_id=auth.uid()`. `cloudP.id = deps.ownerId` (= auth.uid()), NOT a literal. The import-guard (`tests/lib/cloud-sync/import-guard.test.ts`) + `check-service-confinement.ts` (walks lib/cloud-sync + scripts) must make this non-vacuous. `scripts/cloud-sync.ts` must not transitively import the service-role key.
7. **MIGRATION 0021.** drop-first before recreate (PGRST203 overload avoidance); grants preserved (merge_video_data→authenticated+service_role, update_video_annotations→authenticated, persist_summary→authenticated+service_role); persist_summary body VERBATIM from 0009 + only the 2 md-signal keys; per-field annotationsEditedAt stamping; the RPCs callable under the authenticated user JWT.
8. **FORWARD-TOLERANCE.** New VideoSchema fields `.optional()`; ModelEnvelopeSchema dropped `.strict()` (an old reader must not null on a new-writer envelope).

## Also
- Hunt for any place a cross-backend semantic mismatch (local vs Supabase store/blob) causes wrong behavior — the transferClassA promote-vs-put bug (already fixed) is the archetype; look for siblings (e.g. does `claimVideoSlot`/`upsertVideo`/`merge_video_data` behave differently local vs cloud in a way the orchestrator mishandles?).
- Consider these KNOWN-and-ACCEPTED minors (do NOT re-report unless you find they mask a real bug): T12-M2 (copyAdditiveVideo post-write verify checks row presence not payload), T14-M1 (put→updateVideoFields two non-txn writes, self-healing), T14-M2 (no failCloudPut fault test for two-sided transfer), T5 test-coverage gaps, T4 automock comment inaccuracy.

## Output
For each NEW finding: severity (Blocking/High/Medium/Low), file:line, the concrete cross-task failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. Triage the accepted-minors list: any that must be fixed before merge vs defer. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.
codex
I’ll review the final branch state against the cross-task invariants, focusing on shipped code paths rather than individual commit history. I’ll start by mapping the sync orchestrator, stores, migration, and guard tests so findings can be tied to concrete end-to-end failures.
exec
/bin/bash -lc 'rg --files lib/cloud-sync supabase/migrations tests/lib/cloud-sync tests/integration/cloud-sync tests/integration/helpers scripts | sort' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/cloud-sync/auth.ts
lib/cloud-sync/backfill.ts
lib/cloud-sync/companion.ts
lib/cloud-sync/content-hash.ts
lib/cloud-sync/manifest.ts
lib/cloud-sync/reconcile-class-a.ts
lib/cloud-sync/reconcile-class-b.ts
lib/cloud-sync/registry.ts
lib/cloud-sync/sync-run.ts
lib/cloud-sync/types.ts
scripts/audit-summaries.ts
scripts/audit-timestamps.ts
scripts/backfill-playlist-titles.ts
scripts/backfill-serial-prefix.ts
scripts/check-service-confinement.ts
scripts/cloud-sync.ts
scripts/codex-frontier-model.py
scripts/fix-duplicate-summaries.ts
scripts/regen-skills-doc.py
scripts/regen-skills-doc.sh
scripts/repair-timestamps.ts
scripts/rerender-html.ts
scripts/session-skill-report.py
scripts/verify-gemini-release.ts
supabase/migrations/0001_core_schema.sql
supabase/migrations/0002_rls_policies.sql
supabase/migrations/0003_provisioning.sql
supabase/migrations/0004_test_exec_sql.sql
supabase/migrations/0005_reorder_helper.sql
supabase/migrations/0006_grants.sql
supabase/migrations/0007_storage_and_rpcs.sql
supabase/migrations/0008_jobs_queue.sql
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql
supabase/migrations/0010_cancel_job_rowcount.sql
supabase/migrations/0011_cost_guardrails.sql
supabase/migrations/0012_serve_model_charge.sql
supabase/migrations/0013_share_tokens.sql
supabase/migrations/0014_serve_owner_budget.sql
supabase/migrations/0015_video_updated_at_trigger.sql
supabase/migrations/0016_update_video_annotations.sql
supabase/migrations/0017_share_token_id_return.sql
supabase/migrations/0018_enqueue_dig.sql
supabase/migrations/0019_share_tokens_cascade.sql
supabase/migrations/0020_reservation_release.sql
supabase/migrations/0021_cloud_sync_signals.sql
tests/integration/cloud-sync/cloud-stamping.int.test.ts
tests/integration/cloud-sync/e2e.int.test.ts
tests/integration/cloud-sync/stamping.int.test.ts
tests/integration/cloud-sync/sync-run.int.test.ts
tests/integration/helpers/clients.ts
tests/integration/helpers/cloud.ts
tests/integration/helpers/seed.ts
tests/lib/cloud-sync/auth-file-store.test.ts
tests/lib/cloud-sync/auth.test.ts
tests/lib/cloud-sync/backfill.test.ts
tests/lib/cloud-sync/cli.test.ts
tests/lib/cloud-sync/companion.test.ts
tests/lib/cloud-sync/content-hash.test.ts
tests/lib/cloud-sync/import-guard.test.ts
tests/lib/cloud-sync/local-stamping.test.ts
tests/lib/cloud-sync/manifest.test.ts
tests/lib/cloud-sync/model-writer-hash.test.ts
tests/lib/cloud-sync/reconcile-class-a.test.ts
tests/lib/cloud-sync/reconcile-class-b.test.ts
tests/lib/cloud-sync/regenerate-stamp.test.ts
tests/lib/cloud-sync/registry.test.ts
tests/lib/cloud-sync/schema.test.ts

exec
/bin/bash -lc 'rg -n "runSync|copyAdditiveVideo|transferClassA|applyClassBWinners|sanitizeAdditiveVideo|sourceMdHash|mdHash|summaryMd|spend_ledger|enqueue|producer|service_role|SERVICE|persist_summary|merge_video_data|update_video_annotations|claimVideoSlot|ensureReceiverSlot|buildBaseline|deriveHumanSnapshot|deriveClassASignals|decideCompanion|reconciledCorrectionsHash|promoted|updateVideoFields|upsertVideo|readIndex" lib supabase scripts tests types docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'git status --short && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
 M docs/local-validation-findings.md
 M supabase/config.toml
?? .codex-tasks/
?? docs/reviews/task-12-sync-run-behaviors-codex.md
?? docs/reviews/whole-branch-cloud-sync-codex.md
?? scratchpad/
feat/stage3-cloud-sync
255b80efb8e5b1755d592e66cf33b4f3e41e6c32

 succeeded in 0ms:
types/index.ts:56:  summaryMd: z.string().nullable(),
types/index.ts:76:  // Cloud-only (Stage 2a Task 1): sourced from videos.updated_at (readIndex), never persisted
types/index.ts:82:  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:91:  `update_video_annotations`, `app/api/videos/[id]/archive/route.ts`); because the two are entangled on one
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:103:- `ModelEnvelope` gains an OPTIONAL **`sourceMdHash`** — an **MD-body-only** digest (§5.2), set going
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:105:- On a Class-A MD-transfer: ship the sender's model as a companion **iff** `sourceMdHash == mdHash(winning
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:118:- **Class A:** `docVersion.major` (format — the decider), `mdHash` (the MD-body-only §5.2 digest = the
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:119:  envelope's `sourceMdHash`), `mdGeneratedAt` (UTC, a **tie-break only**, never a quality signal), and
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:127:- **Stamping:** `mdGeneratedAt` + `mdCorrectionsHash` on MD generation (`persist_summary` `0009`; local
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:129:  (`update_video_annotations` `0016`; `merge_video_data`/`updateVideoFields` for `corrections` — **conditional
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:137:### 5.2 Canonical `mdHash` (rounds 1–3, 5)
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:138:`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:150:Evaluate **corrections-currency first**, so the `mdHash`-equal skip never hides a stale summary (round-v8 H-1):
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:154:| `mdHash` equal **and** (both corrections-current, or both equally stale-and-format-equal) | **skip** — but if **both are stale** vs the reconciled corrections, still **flag `needs_regen`** (identical stale MDs must not bypass the R8 report) |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:157:| Both corrections-current, same `major`, `mdHash` differs (equivalent LLM variants) | **unify** — newer `mdGeneratedAt` wins; copy so the prose **converges** (intention-respecting tie-break, not a quality claim; avoids undoing a deliberate re-generation) |
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:201:  routes through the metered enqueue `lib/job-queue/producer.ts`, never consumes `spend_ledger`, never
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:215:- **`ModelEnvelopeSchema`:** add `sourceMdHash?: string` **and drop `.strict()`** (→ ignore unknown keys) so a
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:218:- **`update_video_annotations` (`0016`) allowlist → `{personalScore, personalNote, corrections, archived}`** —
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:224:- **`merge_video_data` restamp is CONDITIONAL** on a Class-B key in the patch (it is a blind generic merge also
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:227:- **`persist_summary` / local `pipeline.ts`** stamp `mdGeneratedAt` + `mdCorrectionsHash` on generation, and
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:251:4. **Class A MD transfer is per-video atomic**, aligned with the existing staged→committed→promoted protocol
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:256:   Metadata never advertises the new `mdHash` until the MD is promoted; a crash leaves staged objects + an
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:261:   **whole Class-A tuple** (`mdHash` + `mdCorrectionsHash` + `docVersion`), not `mdHash` alone, plus the
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:281:receiver-observed `mdHash`) and **Class B** (the last-synced `corrections`/`personalNote`/`personalScore`
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:305:  (round-v7 Codex-H1); neither-current → `needs_regen` (R8), **including identical stale MDs** (`mdHash`
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:309:  receiver (round-v8 B-1, `reconstructVideo` would corrupt them); `mdHash` cross-backend fixtures; a
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:310:  human-field edit does **not** change `mdHash`.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:319:  reader (`.strict()` dropped) tolerates a `sourceMdHash`-bearing envelope.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:322:  `merge_video_data` MD-finalize does NOT bump it — round-v7 L-1); membership writers do not.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:325:  re-created; re-creation never calls the metered enqueue; no-session refusal; client `owner_id` rejected.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:372:4. **Model JSON = companion** (sync-transfer scoped, MD-only `sourceMdHash`, forward-tolerant schema, R5/R7).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:375:7. **Per-playlist manifest**; every MD/human-field SQL writer restamps its timestamp (incl. `merge_video_data`).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:397:  (local is the only legal producer) — the "asset-bearing side wins" tie-break resolves to local; cloud→local
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:402:  companion scalar independently of its MD, so the `mdHash`-equal skip safely implies matching scalars — if
scripts/check-service-confinement.ts:83:/** Stage 1D (H-B, reviewed): the two-client split requires the enqueue route to build the
scripts/check-service-confinement.ts:84: *  service-role `Enqueuer` (`enqueue`/`preflight` are service_role-only RPC grants as of
scripts/check-service-confinement.ts:89: *  per spec, the ONLY other) deliberately authorized `service_role` entrypoint — there is no
scripts/check-service-confinement.ts:94: *  it builds `SupabaseEnqueuer(createServiceClient())` for the enqueue RPC ONLY, mirroring
scripts/check-service-confinement.ts:96: *  through the SESSION client (RLS), never the service client — see enqueue-dig-core.ts. */
scripts/check-service-confinement.ts:97:const ALLOWED_SERVICE_IMPORTERS = [
scripts/check-service-confinement.ts:106:    .filter((e) => !ALLOWED_SERVICE_IMPORTERS.includes(path.resolve(e)));
scripts/check-service-confinement.ts:115:  console.log('service_role confinement OK');
tests/components/VideoList.selection.test.tsx:18:    overallScore: 3, summaryMd: `${id}.md`,
tests/components/VideoList.selection.test.tsx:49:it('CA2: a row with no summaryMd has a disabled checkbox', () => {
tests/components/VideoList.selection.test.tsx:50:  renderList({ ...baseProps, videos: [v('a', { summaryMd: null })] });
tests/components/VideoList.selection.test.tsx:59:    v('c', { summaryMd: null }),                                     // not selectable
tests/e2e/html-doc.spec.ts:37:    summaryMd: 'deep-dive-into-llms.md',
lib/serial-migrate.ts:7:  'summaryMd',
lib/serial-migrate.ts:33:    if (vid.summaryMd) {
lib/serial-migrate.ts:34:      const base = vid.summaryMd.replace(/\.md$/, '');
supabase/config.toml:20:# `postgres` are reachable through the Data API roles (`anon`, `authenticated`, `service_role`)
tests/components/VideoRow.test.tsx:44:  summaryMd: 'summary.md',
tests/components/VideoRow.test.tsx:89:    renderRow({ summaryMd: 'base.md' }, { onResummarize });
tests/components/VideoRow.test.tsx:267:        // summaryMd is 'summary.md' → strip .md → 'summary'
scripts/rerender-html.ts:22:      console.log(`  skipped-drift:    ${d.summaryMd} (sections [${d.mdSections?.join(', ')}] ≠ model [${d.modelSections?.join(', ')}] — regenerate)`);
scripts/rerender-html.ts:24:      console.log(`  skipped-no-model: ${d.summaryMd} (regenerate once to enable)`);
scripts/rerender-html.ts:26:      console.log(`  skipped-no-md:    ${d.summaryMd} (.md missing on disk)`);
scripts/rerender-html.ts:28:      console.log(`  skipped-unparse:  ${d.summaryMd} (.md has no sections — regenerate)`);
scripts/rerender-html.ts:30:      console.log(`  error:            ${d.summaryMd} (${d.message})`);
tests/e2e/dig-deeper.spec.ts:415:    const summaryMdRel = `${baseName}.md`;
tests/e2e/dig-deeper.spec.ts:431:        summaryMd: summaryMdRel,
tests/e2e/dig-deeper.spec.ts:440:    const summaryMd = [
tests/e2e/dig-deeper.spec.ts:453:    fs.writeFileSync(path.join(tmpDir, summaryMdRel), summaryMd, 'utf-8');
tests/e2e/dig-deeper.spec.ts:459:      sourceMd: summaryMdRel,
tests/e2e/dig-deeper.spec.ts:477:    const parsed = parseMd(summaryMd);
tests/e2e/dig-deeper.spec.ts:478:    parsed.sourceMd = summaryMdRel;
tests/components/PageIntegration.test.tsx:63:    summaryMd: 'summary.md',
lib/share/serve.ts:12: *  coarse `denied` for every invalid/expired/revoked/unknown/unpromoted case. */
lib/share/serve.ts:44:  const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
lib/share/serve.ts:45:    .artifacts?.summaryMd;
lib/share/serve.ts:46:  if (artifact?.status !== 'promoted') return denied;
lib/share/serve.ts:47:  const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
supabase/migrations/0010_cancel_job_rowcount.sql:4:-- for enqueue_job). DROP also drops the old grants — re-issue them below.
supabase/migrations/0010_cancel_job_rowcount.sql:22:grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
tests/components/cloud-app.test.tsx:53:    summaryMd: null,
scripts/fix-duplicate-summaries.ts:7: * For each video in the index whose summaryMd ends with -2.md:
scripts/fix-duplicate-summaries.ts:9: *   2. Update index entry: summaryMd → canonical name
scripts/fix-duplicate-summaries.ts:20:  summaryMd?: string | null;
scripts/fix-duplicate-summaries.ts:29:function readIndex(folder: string): PlaylistIndex {
scripts/fix-duplicate-summaries.ts:47:  const index = readIndex(folder);
scripts/fix-duplicate-summaries.ts:53:    for (const [field, ext] of [['summaryMd', 'md']] as const) {
tests/integration/delete-playlist-route.test.ts:57:// enqueue_job is the 8-arg service-role-only RPC (0018): owner id explicit.
tests/integration/delete-playlist-route.test.ts:58:function enqueueJob(ownerId: string, playlistId: string, videoId: string, kind: 'summary' | 'dig') {
tests/integration/delete-playlist-route.test.ts:59:  return svc.rpc('enqueue_job', {
tests/integration/delete-playlist-route.test.ts:61:    p_job_kind: kind, p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/delete-playlist-route.test.ts:113:    const summaryJobRes = await enqueueJob(userId, playlistId, `v-${randomUUID()}`, 'summary');
tests/integration/delete-playlist-route.test.ts:115:    const digJobRes = await enqueueJob(userId, playlistId, `v-${randomUUID()}`, 'dig');
tests/e2e/playlist-viewer.spec.ts:28:    summaryMd: 'summary',
tests/e2e/playlist-viewer.spec.ts:262:    // summaryMd is 'summary' (no .md) → file param is 'summary', not the raw video id
tests/e2e/playlist-viewer.spec.ts:337:      summaryMd: 'summary.md',
tests/e2e/playlist-viewer.spec.ts:370:      summaryMd: 'summary.md',
tests/e2e/playlist-viewer.spec.ts:398:      summaryMd: null,
tests/e2e/playlist-viewer.spec.ts:482:  test('backfill banner visible when videos have summaryMd but no tldr', async ({ page }) => {
tests/e2e/playlist-viewer.spec.ts:483:    const video = makeVideo({ id: 'vid-bf1', summaryMd: 'summary.md' /* no tldr */ });
tests/e2e/playlist-viewer.spec.ts:515:    const video = makeVideo({ id: 'vid-bf3', summaryMd: 'summary.md' });
tests/e2e/playlist-viewer.spec.ts:533:    const video = makeVideo({ id: 'vid-bf4', title: 'RAG Video', summaryMd: 'summary.md' });
tests/e2e/playlist-viewer.spec.ts:558:    const video = makeVideo({ id: 'vid-bf5', summaryMd: 'summary.md' });
tests/e2e/playlist-viewer.spec.ts:598:    const video = makeVideo({ id: 'vid-bf6', summaryMd: 'summary.md' });
tests/e2e/playlist-viewer.spec.ts:629:    const video = makeVideo({ id: 'vid-bf7', summaryMd: 'summary.md' });
tests/components/client-api-ingest.test.tsx:14:  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
supabase/migrations/0006_grants.sql:3:-- the Data API roles (anon, authenticated, service_role) on new public tables. RLS only
supabase/migrations/0006_grants.sql:9:-- service_role: has BYPASSRLS (the trusted worker path, spec §5.4 — writes with owner_id
supabase/migrations/0006_grants.sql:16:grant select, insert, update, delete on public.profiles  to anon, authenticated, service_role;
supabase/migrations/0006_grants.sql:17:grant select, insert, update, delete on public.playlists to anon, authenticated, service_role;
supabase/migrations/0006_grants.sql:18:grant select, insert, update, delete on public.videos    to anon, authenticated, service_role;
scripts/backfill-serial-prefix.ts:3:import { readIndex } from '../lib/index-store';
scripts/backfill-serial-prefix.ts:8:  const { assignments, perVideo } = planMigration(readIndex(outputFolder).videos);
tests/integration/blob-store.test.ts:24:/** Minimal video stub accepted by upsertVideo; uses `as any` to skip schema
tests/integration/blob-store.test.ts:36:    summaryMd: null,
tests/integration/blob-store.test.ts:142:test('promote idempotent: second call with final already promoted → no throw, final readable', async () => {
tests/integration/blob-store.test.ts:163:test('writeArtifact: blob readable at final key + metadata artifacts.summaryMd.status === promoted', async () => {
tests/integration/blob-store.test.ts:173:  await meta.claimVideoSlot(p, 'vidAAAAAAAA');
tests/integration/blob-store.test.ts:174:  await meta.upsertVideo(p, makeVideo('vidAAAAAAAA', 1) as any);
tests/integration/blob-store.test.ts:176:  // writeArtifact: putStaged → verify temp → updateVideoFields(committed) → promote → updateVideoFields(promoted).
tests/integration/blob-store.test.ts:182:    kind: 'summaryMd',
tests/integration/blob-store.test.ts:192:  // Metadata must reflect promoted status.
tests/integration/blob-store.test.ts:193:  const idx = await meta.readIndex(p);
tests/integration/blob-store.test.ts:195:  expect(video.artifacts?.summaryMd?.status).toBe('promoted');
tests/integration/blob-store.test.ts:196:  expect(video.artifacts?.summaryMd?.key).toBe('summaries/vidAAAAAAAA.md');
tests/integration/blob-store.test.ts:205:  // summaryMd is a SOURCE kind → must not regenerate; must markRepair.
tests/integration/blob-store.test.ts:207:    kind: 'summaryMd',
tests/integration/metadata-store.test.ts:20:/** Minimal video stub accepted by upsertVideo; uses `as any` to skip schema
tests/integration/metadata-store.test.ts:32:    summaryMd: null,
tests/integration/metadata-store.test.ts:42:    await expect(store.readIndex(P)).resolves.toEqual({
tests/integration/metadata-store.test.ts:50:  test('setPlaylistMeta create then update; readIndex reflects both writes', async () => {
tests/integration/metadata-store.test.ts:56:    let idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:66:    idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:70:  // 3. claimVideoSlot allocates sequential slots; upsertVideo fills row; readIndex round-trips
tests/integration/metadata-store.test.ts:71:  test('claimVideoSlot allocates position+serial sequentially; readIndex returns videos in order', async () => {
tests/integration/metadata-store.test.ts:75:    const slotA = await store.claimVideoSlot(P, 'vidAAAAAAAA');
tests/integration/metadata-store.test.ts:78:    const slotB = await store.claimVideoSlot(P, 'vidBBBBBBBB');
tests/integration/metadata-store.test.ts:81:    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);
tests/integration/metadata-store.test.ts:82:    await store.upsertVideo(P, makeVideo('vidBBBBBBBB', 2) as any);
tests/integration/metadata-store.test.ts:84:    const idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:93:    await store.claimVideoSlot(P, 'vid1');
tests/integration/metadata-store.test.ts:94:    await store.claimVideoSlot(P, 'vid2');
tests/integration/metadata-store.test.ts:95:    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
tests/integration/metadata-store.test.ts:96:    await store.upsertVideo(P, makeVideo('vid2', 2) as any);
tests/integration/metadata-store.test.ts:117:    const idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:142:    await store.claimVideoSlot(P, 'vidAAAAAAAA');
tests/integration/metadata-store.test.ts:143:    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);
tests/integration/metadata-store.test.ts:156:    // merge_video_data does a plain shallow merge (no special write-once guard at the DB
tests/integration/metadata-store.test.ts:158:    const cur = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:168:    const after = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:178:    await store.claimVideoSlot(P, 'vidAAAAAAAA');
tests/integration/metadata-store.test.ts:179:    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);
tests/integration/metadata-store.test.ts:181:    // write summaryMd artifact kind
tests/integration/metadata-store.test.ts:182:    await store.updateVideoFields(P, 'vidAAAAAAAA', {
tests/integration/metadata-store.test.ts:183:      artifacts: { summaryMd: { key: 'a.md', status: 'promoted' } },
tests/integration/metadata-store.test.ts:185:    // write html artifact kind — must NOT clobber summaryMd
tests/integration/metadata-store.test.ts:186:    await store.updateVideoFields(P, 'vidAAAAAAAA', {
tests/integration/metadata-store.test.ts:187:      artifacts: { html: { key: 'a.html', status: 'promoted' } },
tests/integration/metadata-store.test.ts:190:    const v = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:191:    // deep-merge in merge_video_data must preserve both keys
tests/integration/metadata-store.test.ts:192:    expect(v.artifacts.summaryMd).toEqual({ key: 'a.md', status: 'promoted' });
tests/integration/metadata-store.test.ts:193:    expect(v.artifacts.html).toEqual({ key: 'a.html', status: 'promoted' });
tests/integration/metadata-store.test.ts:200:    await store.claimVideoSlot(P, 'vid1');
tests/integration/metadata-store.test.ts:201:    await store.claimVideoSlot(P, 'vid2');
tests/integration/metadata-store.test.ts:202:    await store.claimVideoSlot(P, 'vid3');
tests/integration/metadata-store.test.ts:203:    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
tests/integration/metadata-store.test.ts:204:    await store.upsertVideo(P, makeVideo('vid2', 2) as any);
tests/integration/metadata-store.test.ts:205:    await store.upsertVideo(P, makeVideo('vid3', 3) as any);
tests/integration/metadata-store.test.ts:209:    let idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:219:    idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:231:    await store.claimVideoSlot(P, 'vid1');
tests/integration/metadata-store.test.ts:232:    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
tests/integration/metadata-store.test.ts:235:    await store.updateVideoFields(P, 'vid1', { archived: true } as any);
tests/integration/metadata-store.test.ts:237:    const before = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:244:    const after = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:252:    await store.claimVideoSlot(P, 'vid1');
tests/integration/metadata-store.test.ts:253:    await store.claimVideoSlot(P, 'vid2');
tests/integration/metadata-store.test.ts:254:    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
tests/integration/metadata-store.test.ts:255:    await store.upsertVideo(P, makeVideo('vid2', 2) as any);
tests/integration/metadata-store.test.ts:260:    const idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:271:    await store.claimVideoSlot(P, 'vid1');
tests/integration/metadata-store.test.ts:272:    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
tests/integration/metadata-store.test.ts:276:    const removed = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:282:    const restored = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:290:    await store.claimVideoSlot(P, 'vid1');
tests/integration/metadata-store.test.ts:291:    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
tests/integration/metadata-store.test.ts:295:    const first = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:301:    const second = (await store.readIndex(P)).videos[0] as any;
tests/integration/metadata-store.test.ts:307:  test('deleteVideo removes the row; readIndex no longer contains it', async () => {
tests/integration/metadata-store.test.ts:310:    await store.claimVideoSlot(P, 'vidAAAAAAAA');
tests/integration/metadata-store.test.ts:311:    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);
tests/integration/metadata-store.test.ts:313:    let idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:318:    idx = await store.readIndex(P);
tests/integration/metadata-store.test.ts:327:    await storeA.claimVideoSlot(P, 'vidAAAAAAAA');
tests/integration/metadata-store.test.ts:328:    await storeA.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);
tests/integration/metadata-store.test.ts:332:    const idxB = await storeB.readIndex(P);
tests/integration/metadata-store.test.ts:337:    const idxBAfterSeed = await storeB.readIndex(P);
tests/integration/metadata-store.test.ts:341:    const idxAFinal = await storeA.readIndex(P);
tests/integration/metadata-store.test.ts:345:  // 10. claimVideoSlot idempotent re-claim (ON CONFLICT DO NOTHING)
tests/integration/metadata-store.test.ts:346:  test('claimVideoSlot idempotent re-claim: returns next-slot values; exactly one row persists', async () => {
tests/integration/metadata-store.test.ts:355:    const first = await store.claimVideoSlot(P, 'vidAAAAAAAA');
tests/integration/metadata-store.test.ts:359:    const reClaim = await store.claimVideoSlot(P, 'vidAAAAAAAA');
tests/integration/metadata-store.test.ts:366:    const idx = await store.readIndex(P);
tests/integration/cancel-playlist-jobs.test.ts:11:// enqueue_job is the 8-arg service-role-only RPC (0018): owner id explicit.
tests/integration/cancel-playlist-jobs.test.ts:12:function enqueue(ownerId: string, playlistId: string, videoId: string, jobKind: 'summary' | 'dig') {
tests/integration/cancel-playlist-jobs.test.ts:13:  return svc.rpc('enqueue_job', {
tests/integration/cancel-playlist-jobs.test.ts:15:    p_job_kind: jobKind, p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/cancel-playlist-jobs.test.ts:23:  const summaryJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'summary')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:24:  const digJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'dig')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:44:  const job = (await enqueue(owner.user.id, playlistId, `v-${randomUUID()}`, 'summary')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:59:  const completedJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'summary')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:60:  const failedJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'dig')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:61:  const deadLetterJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'summary')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:62:  const cancelledJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'dig')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:89:  const summaryJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'summary')).data[0];
tests/integration/cancel-playlist-jobs.test.ts:90:  const digJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'dig')).data[0];
tests/integration/share-summary-2c.test.ts:6://   3. SupabaseMetadataStore.readIndex's `summaryReady` DTO reflection under real RLS
tests/integration/share-summary-2c.test.ts:7://      (promoted → true; committed/artifacts-absent → false)
tests/integration/share-summary-2c.test.ts:21:async function seedDoc(ownerId: string, status?: 'promoted' | 'committed') {
tests/integration/share-summary-2c.test.ts:91:  test('summaryReady reflection via SupabaseMetadataStore.readIndex under real RLS', async () => {
tests/integration/share-summary-2c.test.ts:94:    const { playlistId, playlistKey, videoId: promotedId } = await seedDoc(u.user.id, 'promoted');
tests/integration/share-summary-2c.test.ts:108:    const idx = await store.readIndex(p);
tests/integration/share-summary-2c.test.ts:109:    const promotedVideo = idx.videos.find((v) => v.id === promotedId);
tests/integration/share-summary-2c.test.ts:112:    expect(promotedVideo?.summaryReady).toBe(true);
tests/e2e/pdf-export.spec.ts:21:    summaryMd: 'deep-dive-into-llms.md',
supabase/migrations/0018_enqueue_dig.sql:1:-- 0018_enqueue_dig.sql
supabase/migrations/0018_enqueue_dig.sql:2:-- Admit job_kind='dig' in enqueue_job. The dig quota (quota_allowance dig rows),
supabase/migrations/0018_enqueue_dig.sql:7:create or replace function enqueue_job(
supabase/migrations/0018_enqueue_dig.sql:9:  p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet
supabase/migrations/0018_enqueue_dig.sql:17:  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
supabase/migrations/0018_enqueue_dig.sql:18:  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
supabase/migrations/0018_enqueue_dig.sql:28:    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
supabase/migrations/0018_enqueue_dig.sql:32:    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload, enqueue_ip, max_attempts)
supabase/migrations/0018_enqueue_dig.sql:33:    values (p_owner_id, p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload, p_enqueue_ip, v_maxatt)
supabase/migrations/0018_enqueue_dig.sql:61:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0018_enqueue_dig.sql:62:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0018_enqueue_dig.sql:79:        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;
supabase/migrations/0018_enqueue_dig.sql:86:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
supabase/migrations/0018_enqueue_dig.sql:87:grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;
tests/integration/video-updated-at.test.ts:4:// `updated_at` on EVERY row update — not just the RPC paths (merge_video_data,
tests/integration/video-updated-at.test.ts:5:// merge_video_data_bulk, reconcile_membership) that already set it explicitly.
tests/integration/video-updated-at.test.ts:6:// The gap this closes: SupabaseMetadataStore.upsertVideo() does a direct
tests/integration/video-updated-at.test.ts:11:// asserts `updated_at` advances each time, then asserts `readIndex` (the
tests/integration/video-updated-at.test.ts:39:it('trigger bumps videos.updated_at on the merge_video_data RPC path AND the direct upsertVideo(.update) path; readIndex surfaces it as Video.updatedAt', async () => {
tests/integration/video-updated-at.test.ts:49:  // --- Path 1: updateVideoFields → merge_video_data RPC (already sets updated_at explicitly;
tests/integration/video-updated-at.test.ts:52:  await bundle.metadataStore.updateVideoFields(principal, videoId, { title: 'Updated via RPC' });
tests/integration/video-updated-at.test.ts:56:  // --- Path 2: upsertVideo → direct `.update({ data })` with NO updated_at in the payload.
tests/integration/video-updated-at.test.ts:62:  await bundle.metadataStore.upsertVideo(principal, row!.data as unknown as Video);
tests/integration/video-updated-at.test.ts:66:  // --- readIndex surfaces the column as Video.updatedAt, matching the DB value exactly. ---
tests/integration/video-updated-at.test.ts:67:  const index = await bundle.metadataStore.readIndex(principal);
tests/integration/schema.test.ts:11:                              'usage_counters','spend_ledger','quota_allowance','guardrail_config')
tests/integration/schema.test.ts:24:      { relname: 'spend_ledger', relrowsecurity: true, relforcerowsecurity: true },
tests/integration/schema.test.ts:65:  it('defines ZERO policies on the service-role-only tables spend_ledger and guardrail_config (1D-1)', async () => {
tests/integration/schema.test.ts:66:    // Whole-schema net: these two tables have no client grant at all (service_role only), so a
tests/integration/schema.test.ts:72:              and tablename in ('spend_ledger','guardrail_config')
tests/integration/schema.test.ts:94:    // write-injection hole (attacker enqueues a job citing another owner's playlist UUID).
tests/integration/schema.test.ts:109:    // INCLUDE/predicate but not the unique key, or if the predicate diverged from enqueue_job's.
tests/components/new-playlist-modal.test.tsx:18:  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
tests/integration/serve-model-charge.test.ts:7:/** Task-1 convenience: playlist + promoted video in one call (RPC needs only the DB row). */
tests/integration/serve-model-charge.test.ts:16:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-model-charge.test.ts:34:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:45:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:61:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:104:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:105:  expect(led ?? []).toEqual([]); // the spend_ledger insert (step 5) rolled back with the claim — no row for the day
tests/integration/serve-model-charge.test.ts:108:it('denies a foreign or unpromoted doc via direct RPC (no charge, no leak)', async () => {
tests/integration/serve-model-charge.test.ts:115:  // owned but only 'committed' (not promoted) — seeded via the shared helper with status:'committed':
tests/integration/serve-model-charge.test.ts:119:  const { data: unpromotedRows } = await oc.rpc('reserve_serve_model', { p_playlist_id: pl2, p_video_id: vCommitted });
tests/integration/serve-model-charge.test.ts:120:  expect(unpromotedRows![0].status).toBe('denied');
tests/integration/serve-model-charge.test.ts:121:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:131:// ---- Grant / RLS lockdown (the marker table is service_role-only + force-RLS; the RPC is the
tests/integration/serve-model-charge.test.ts:196:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:211:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:235:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:251:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
supabase/migrations/0012_serve_model_charge.sql:5:-- 1. Lease/charge marker. force-RLS + service_role-only grants (mirrors spend_ledger, 0011):
supabase/migrations/0012_serve_model_charge.sql:17:grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
supabase/migrations/0012_serve_model_charge.sql:25:--    service_role-only tables while being callable by a session client. auth.uid() is derived
supabase/migrations/0012_serve_model_charge.sql:35:  v_promoted boolean;
supabase/migrations/0012_serve_model_charge.sql:43:  -- Verify (playlist, video) owned by v_owner AND summary promoted. Else coarse 'denied' (no leak).
supabase/migrations/0012_serve_model_charge.sql:44:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0012_serve_model_charge.sql:45:    into v_promoted
supabase/migrations/0012_serve_model_charge.sql:48:  if v_promoted is distinct from true then
supabase/migrations/0012_serve_model_charge.sql:84:      -- 5. Charge THIS attempt against the daily cap (conditional-UPDATE arbiter, as enqueue_job/0011).
supabase/migrations/0012_serve_model_charge.sql:85:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0012_serve_model_charge.sql:86:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
tests/integration/producer-roundtrip.test.ts:7:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
tests/integration/producer-roundtrip.test.ts:8:import { enqueuePlaylist } from '@/lib/job-queue/producer';
tests/integration/producer-roundtrip.test.ts:18:// T13: producer.enqueuePlaylist moved from a 3-arg (bundle, principal, url) signature that
tests/integration/producer-roundtrip.test.ts:19:// enqueued through the session-client `bundle.jobQueue` to a 5-arg (bundle, enqueuer, principal,
tests/integration/producer-roundtrip.test.ts:20:// url, ctx) signature that enqueues through a service-role `Enqueuer` — the two-client split
tests/integration/producer-roundtrip.test.ts:22:test('producer fans out real jobs (via the service-role Enqueuer) that are then pollable via listByPlaylist', async () => {
tests/integration/producer-roundtrip.test.ts:28:  const enqueuer = new SupabaseEnqueuer(svc);
tests/integration/producer-roundtrip.test.ts:29:  const ctx = { ownerId: userId, enqueueIp: null };
tests/integration/producer-roundtrip.test.ts:30:  const res = await enqueuePlaylist(bundle, enqueuer, { id: userId, indexKey: key }, url, ctx);
tests/integration/producer-roundtrip.test.ts:32:    enqueued: 2, joined: 0, skipped: 1, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0,
tests/integration/share-route.test.ts:52:async function seedDoc(ownerId: string, status: 'promoted' | 'committed' = 'promoted', title?: string) {
tests/integration/share-route.test.ts:107:    const { data: ledger } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/share-route.test.ts:127:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/share-route.test.ts:228:  it('B12: token pointing at an un-promoted (committed) doc → 404', async () => {
tests/integration/share-route.test.ts:247:  it('B13b: MD blob missing behind a promoted status → 404 (never 500)', async () => {
tests/integration/share-route.test.ts:291:  it('B10b: video un-promoted (artifacts.summaryMd.status flipped away from promoted) between the initial resolve and the mandatory pre-response re-check → 404', async () => {
tests/integration/share-route.test.ts:302:      // Instead of revoking the token, flip the video's promotion status away from 'promoted'
tests/integration/share-route.test.ts:304:      // (D14/B10b) — the re-check reads `videos.data.artifacts.summaryMd.status` fresh, so this
tests/integration/share-route.test.ts:312:        artifacts: { summaryMd: { key: `${base}.md`, status: 'committed' } },
tests/integration/share-route.test.ts:346:    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id, 'promoted', 'My Doc Title');
tests/integration/share-route.test.ts:375:    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id, 'promoted', 'My Doc Title');
tests/integration/share-route.test.ts:463:  it('C12: format=md, MD blob missing behind a promoted status → 404 (never 500)', async () => {
tests/integration/share-route.test.ts:482:    const { playlistId, videoId } = await seedDoc(a.user.id); // A's promoted doc
tests/integration/share-route.test.ts:505:        id: videoId, title: hostileTitle, language: 'en', summaryMd: `${base}.md`, docVersion: 1,
tests/integration/share-route.test.ts:506:        artifacts: { summaryMd: { key: `${base}.md`, status: 'promoted' } },
tests/integration/concurrency.test.ts:13:test('concurrent claimVideoSlot on one playlist yields distinct positions + serials', async () => {
tests/integration/concurrency.test.ts:26:  const slots = await Promise.all(ids.map((id) => s.claimVideoSlot(P, id)));
tests/integration/concurrency.test.ts:35:  const idx = await s.readIndex(P);
tests/components/cloud-app-ingest.test.tsx:26:const result = (over: any = {}) => ({ playlistId: 'p-uuid', jobs: [], challengeRequired: false, counts: { enqueued: 3, joined: 0, skipped: 3, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 }, ...over });
tests/integration/exec-sql-guard.test.ts:3:describe('exec_sql is service_role-only', () => {
tests/e2e/batch-docs.spec.ts:9:    overallScore: 3, summaryMd: `${id}.md`,
tests/e2e/batch-docs.spec.ts:60:  // Individually select video 'a' (its row checkbox is always enabled since it has summaryMd).
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
supabase/migrations/0021_cloud_sync_signals.sql:72:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0021_cloud_sync_signals.sql:92:revoke all on function merge_video_data(uuid, text, jsonb, timestamptz) from public;
supabase/migrations/0021_cloud_sync_signals.sql:93:grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;
supabase/migrations/0021_cloud_sync_signals.sql:95:-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
supabase/migrations/0021_cloud_sync_signals.sql:99:create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0021_cloud_sync_signals.sql:103:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0021_cloud_sync_signals.sql:111:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0021_cloud_sync_signals.sql:112:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
supabase/migrations/0021_cloud_sync_signals.sql:113:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
supabase/migrations/0021_cloud_sync_signals.sql:133:      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
supabase/migrations/0021_cloud_sync_signals.sql:136:           || jsonb_build_object('summaryMd', jsonb_build_object(
supabase/migrations/0021_cloud_sync_signals.sql:137:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
supabase/migrations/0021_cloud_sync_signals.sql:138:                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
supabase/migrations/0021_cloud_sync_signals.sql:141:                -- promoted artifact for a blob that has not been promoted yet).
supabase/migrations/0021_cloud_sync_signals.sql:143:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
supabase/migrations/0021_cloud_sync_signals.sql:145:                                 and v.data->'artifacts'->'summaryMd'->>'key'
supabase/migrations/0021_cloud_sync_signals.sql:146:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
supabase/migrations/0021_cloud_sync_signals.sql:147:                              then 'promoted'
supabase/migrations/0021_cloud_sync_signals.sql:152:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0021_cloud_sync_signals.sql:154:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0021_cloud_sync_signals.sql:155:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
scripts/cloud-sync.ts:4:// Supabase client into runSync() so a developer/operator can pull cloud changes into their local
scripts/cloud-sync.ts:17:import { runSync, type SyncDeps } from '@/lib/cloud-sync/sync-run';
scripts/cloud-sync.ts:68:  const report = await runSync(deps, args.playlistKey ? { playlistKey: args.playlistKey } : {});
tests/integration/html-serve-isolation.test.ts:15:/** Seed an owner + one promoted doc (DB row via helper + the MD blob at {owner}/{key}/{base}.md). */
tests/integration/html-serve-isolation.test.ts:25:  // resolveOwnedPlaylistKey (owner-assert) and readIndex (video-row RLS). It does NOT call GET, so it
tests/integration/html-serve-isolation.test.ts:34:    .metadataStore.readIndex({ id: a.user.id, indexKey: aDoc.playlistKey });
tests/integration/html-serve-isolation.test.ts:42:    .metadataStore.readIndex({ id: anonId, indexKey: anonDoc.playlistKey });
tests/integration/html-serve-isolation.test.ts:58:    .metadataStore.readIndex({ id: b.user.id, indexKey: aDoc.playlistKey });
tests/integration/html-serve-isolation.test.ts:63:    .metadataStore.readIndex({ id: a.user.id, indexKey: bDoc.playlistKey });
tests/components/AskGeminiMenuItem.test.tsx:11:    overallScore: 4, summaryMd: null,
tests/integration/jobs-poll-banner.test.ts:15:function enqueue(ownerId: string, pl: string, vid: string) {
tests/integration/jobs-poll-banner.test.ts:16:  return svc.rpc('enqueue_job', {
tests/integration/jobs-poll-banner.test.ts:18:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/jobs-poll-banner.test.ts:25:  const e1 = await enqueue(userId, pl, 'vid-a'); expect(e1.error).toBeNull();
tests/integration/jobs-poll-banner.test.ts:26:  const e2 = await enqueue(userId, pl, 'vid-b'); expect(e2.error).toBeNull();
tests/integration/jobs-poll-banner.test.ts:47:  const enq = await enqueue(userId, pl, 'vid-a'); expect(enq.error).toBeNull();
tests/integration/setup.ts:12:// `supabase status -o env` emits API_URL / ANON_KEY / SERVICE_ROLE_KEY, but the clients
tests/integration/setup.ts:13:// read the NEXT_PUBLIC_SUPABASE_* / SUPABASE_SERVICE_ROLE_KEY names. Alias the raw names
tests/integration/setup.ts:18:process.env.SUPABASE_SERVICE_ROLE_KEY ||= process.env.SERVICE_ROLE_KEY ?? '';
tests/integration/setup.ts:23:  !process.env.SUPABASE_SERVICE_ROLE_KEY
tests/components/VideoList.test.tsx:46:  summaryMd: 'summary.md',
supabase/migrations/0015_video_updated_at_trigger.sql:3:-- Closes the gap where SupabaseMetadataStore.upsertVideo() does a direct
supabase/migrations/0015_video_updated_at_trigger.sql:6:-- update — idempotent alongside the RPCs (merge_video_data,
supabase/migrations/0015_video_updated_at_trigger.sql:7:-- merge_video_data_bulk, reconcile_membership) that already set it explicitly
tests/integration/share-tokens-rpc.test.ts:15:  it('create_share_token stores a row for an owned+promoted doc and returns expires_at', async () => {
tests/integration/share-tokens-rpc.test.ts:63:  it('create_share_token denies an owned-but-unpromoted doc (B2 promoted branch) and inserts nothing', async () => {
tests/integration/share-tokens-rpc.test.ts:71:    expect(error).not.toBeNull(); // owned but not promoted → still denied
tests/integration/share-tokens-rpc.test.ts:109:  it('the share_tokens CHECK constraint backstops the hash format even for service_role direct inserts', async () => {
tests/components/video-menu-dig.test.tsx:15:  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
tests/integration/enqueue-dig.test.ts:1:// tests/integration/enqueue-dig.test.ts
tests/integration/enqueue-dig.test.ts:3:// Task 1 (cloud dig-deeper generation slice): confirms enqueue_job admits
tests/integration/enqueue-dig.test.ts:12:async function enqueueDigRpc(ownerId: string, playlistId: string, videoId: string, sectionId: number) {
tests/integration/enqueue-dig.test.ts:13:  return admin.rpc('enqueue_job', {
tests/integration/enqueue-dig.test.ts:15:    p_job_kind: 'dig', p_job_version: 'dig-9', p_payload: { durationSeconds: 600 }, p_enqueue_ip: null,
tests/integration/enqueue-dig.test.ts:19:describe('enqueue_job admits dig', () => {
tests/integration/enqueue-dig.test.ts:22:  it('enqueues a dig job and debits the dig quota', async () => {
tests/integration/enqueue-dig.test.ts:25:    const { data, error } = await enqueueDigRpc(user.id, playlistId, 'vid-dig-1', 132);
tests/integration/enqueue-dig.test.ts:33:  it('a second identical enqueue joins (idempotent, no double charge)', async () => {
tests/integration/enqueue-dig.test.ts:36:    await enqueueDigRpc(user.id, playlistId, 'vid-dig-2', 132);
tests/integration/enqueue-dig.test.ts:37:    const { data } = await enqueueDigRpc(user.id, playlistId, 'vid-dig-2', 132);
tests/integration/enqueue-dig.test.ts:51:    const { error } = await enqueueDigRpc(anonId, playlistId, 'vid-dig-3', 132);
lib/client/api.ts:7:import type { ProducerCounts, JobFanoutResult } from '@/lib/job-queue/producer';
tests/integration/archive-route-cloud.test.ts:7:// resolveOwnedPlaylistKey, metadataStore.updateVideoAnnotations → update_video_annotations
tests/integration/job-queue-schema.test.ts:15:// T13: T2 revoked INSERT on `jobs` from anon/authenticated entirely (enqueue_job moved to an
tests/integration/job-queue-schema.test.ts:56:test('a producer cannot directly update a job (no update grant)', async () => {
tests/integration/job-queue-schema.test.ts:67:  // Security property: a producer's direct update must NOT change the job. PostgREST's exact
tests/integration/job-queue-schema.test.ts:79:test('idempotency index blocks a second live job for the same work target (enqueue_job joins, no duplicate row)', async () => {
tests/integration/job-queue-schema.test.ts:86:    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/job-queue-schema.test.ts:88:  const first = await svc.rpc('enqueue_job', args);
tests/integration/job-queue-schema.test.ts:90:  const second = await svc.rpc('enqueue_job', args);
tests/components/VideoMenu.test.tsx:16:  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
tests/components/VideoMenu.test.tsx:65:  renderMenu(<VideoMenu {...props} video={{ ...base, summaryMd: null } as any} />);
tests/components/VideoMenu.test.tsx:73:  expect(screen.queryByText(/Save summary PDF/i)).toBeNull(); // summaryMd only, no summaryHtml
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:15:drop function enqueue_job(text,int,text,text,jsonb);
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:16:create function enqueue_job(
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:25:    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:40:        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:45:revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:53:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:60:grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:67:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:83:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:102:grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:104:create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:108:  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:116:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:117:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:118:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:136:      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:139:           || jsonb_build_object('summaryMd', jsonb_build_object(
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:140:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:141:                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:144:                -- promoted artifact for a blob that has not been promoted yet).
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:146:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:148:                                 and v.data->'artifacts'->'summaryMd'->>'key'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:149:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:150:                              then 'promoted'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:155:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:157:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:158:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
supabase/migrations/0014_serve_owner_budget.sql:5:-- 1. Per-owner counter (analog of spend_ledger). force-RLS + service_role-only (no client policy).
supabase/migrations/0014_serve_owner_budget.sql:13:grant select, insert, update, delete on serve_owner_budget to service_role;
supabase/migrations/0014_serve_owner_budget.sql:30:  v_promoted boolean;
supabase/migrations/0014_serve_owner_budget.sql:38:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0014_serve_owner_budget.sql:39:    into v_promoted
supabase/migrations/0014_serve_owner_budget.sql:42:  if v_promoted is distinct from true then
supabase/migrations/0014_serve_owner_budget.sql:73:      --     Over-budget owners fail here without ever locking the global spend_ledger money row.
supabase/migrations/0014_serve_owner_budget.sql:81:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0014_serve_owner_budget.sql:82:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0014_serve_owner_budget.sql:110:grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
tests/components/ingest-summary-notice.test.tsx:5:const base = { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 };
tests/components/ingest-summary-notice.test.tsx:10:    render(<IngestSummaryNotice result={result({ counts: { enqueued: 42, skipped: 3 } })} onDismiss={() => {}} />);
tests/components/ingest-summary-notice.test.tsx:14:    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 }, challengeRequired: true })} onDismiss={() => {}} />);
tests/components/ingest-summary-notice.test.tsx:18:    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 } })} onDismiss={() => {}} />);
tests/components/ingest-summary-notice.test.tsx:23:    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 } })} onDismiss={onDismiss} />);
lib/client/format-ingest-summary.ts:1:import type { ProducerCounts } from '@/lib/job-queue/producer';
lib/client/format-ingest-summary.ts:8:  const parts: string[] = [`Queued ${counts.enqueued}`];
tests/integration/backfill-titles.test.ts:31:    const idx = await store.readIndex(P);
tests/integration/backfill-titles.test.ts:45:    const idx = await store.readIndex(P);
tests/integration/backfill-titles.test.ts:62:    const idxA = await storeA.readIndex(P);
tests/integration/worker-runner-runtime.test.ts:25:    enqueue: jest.fn(),
tests/integration/cloud-sync/sync-run.int.test.ts:3:// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
tests/integration/cloud-sync/sync-run.int.test.ts:8://     a hydrate copies the real MD bytes. F2: transfers finalize via updateVideoFields. F3:
tests/integration/cloud-sync/sync-run.int.test.ts:9://     applyClassBWinners throws on a no-row write. Crash-safety uses a local→cloud publish so the
tests/integration/cloud-sync/sync-run.int.test.ts:15:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/sync-run.int.test.ts:23:describe('runSync (§7)', () => {
tests/integration/cloud-sync/sync-run.int.test.ts:26:    await seedLocalPlaylist(ctx); // cloud has 1 promoted-summary video, local empty
tests/integration/cloud-sync/sync-run.int.test.ts:29:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:35:    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
tests/integration/cloud-sync/sync-run.int.test.ts:41:    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
tests/integration/cloud-sync/sync-run.int.test.ts:42:    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
tests/integration/cloud-sync/sync-run.int.test.ts:51:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:63:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cost-guardrails.test.ts:4:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
tests/integration/cost-guardrails.test.ts:9:// --- Task 2 helpers (server-mediated enqueue: service_role only) ---
tests/integration/cost-guardrails.test.ts:20:  return svc.rpc('enqueue_job', {
tests/integration/cost-guardrails.test.ts:22:    p_job_kind: kind, p_job_version: '1.0', p_payload: p, p_enqueue_ip: ip,
tests/integration/cost-guardrails.test.ts:41:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01'); // clear all ledger days
tests/integration/cost-guardrails.test.ts:70:it('lets an owner read only their own usage_counters and denies spend_ledger/guardrail_config reads', async () => {
tests/integration/cost-guardrails.test.ts:78:  const led = await sa.from('spend_ledger').select('*'); // no client grant → error, not []
tests/integration/cost-guardrails.test.ts:90:// ============================ Task 2: enqueue_job rework ============================
tests/integration/cost-guardrails.test.ts:104:it('a JOIN (idempotent re-enqueue) does NOT re-debit quota', async () => {
tests/integration/cost-guardrails.test.ts:129:it('same-owner parallel distinct-video enqueues admit exactly the allowance (atomic UPDATE…WHERE used<allow)', async () => {
tests/integration/cost-guardrails.test.ts:139:  await svc.from('guardrail_config').update({ daily_cap_cents: 5000 }).eq('id', true); // isolate the allowance (5 enqueues) from the global daily cap
tests/integration/cost-guardrails.test.ts:207:  const before = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
tests/integration/cost-guardrails.test.ts:210:  const after = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
tests/integration/cost-guardrails.test.ts:224:it('rejects enqueue when p_owner_id does not own p_playlist_id (composite FK)', async () => {
tests/integration/cost-guardrails.test.ts:233:it('denies a client session enqueue via BOTH signatures and a direct jobs insert', async () => {
tests/integration/cost-guardrails.test.ts:237:  const r8 = await sa.rpc('enqueue_job', {
tests/integration/cost-guardrails.test.ts:239:    p_job_kind: 'summary', p_job_version: '1.0', p_payload: payload(100), p_enqueue_ip: '1.2.3.4',
tests/integration/cost-guardrails.test.ts:242:  const r6 = await sa.rpc('enqueue_job', {
tests/integration/cost-guardrails.test.ts:254:// ============================ Task 3: enqueue_preflight (advisory gate) ============================
tests/integration/cost-guardrails.test.ts:263:  const r = await svc.rpc('enqueue_preflight', { p_ip: '9.9.9.9', p_owner_id: owner });
tests/integration/cost-guardrails.test.ts:277:  const r = await svc.rpc('enqueue_preflight', { p_ip: '5.5.5.5', p_owner_id: owner });
tests/integration/cost-guardrails.test.ts:292:  const within = await svc.rpc('enqueue_preflight', { p_ip: '1.1.1.1', p_owner_id: reg });
tests/integration/cost-guardrails.test.ts:297:  const capped = await svc.rpc('enqueue_preflight', { p_ip: '1.1.1.2', p_owner_id: reg });
tests/integration/cost-guardrails.test.ts:302:  const anonRow = await svc.rpc('enqueue_preflight', { p_ip: '1.1.1.3', p_owner_id: anonId });
tests/integration/cost-guardrails.test.ts:307:it('denies a client-session call to enqueue_preflight (execute revoked)', async () => {
tests/integration/cost-guardrails.test.ts:310:  const r = await sa.rpc('enqueue_preflight', { p_ip: '1.2.3.4', p_owner_id: a.user.id });
tests/integration/cost-guardrails.test.ts:318:  const enqueuer = new SupabaseEnqueuer(svc);
tests/integration/cost-guardrails.test.ts:320:  it('enqueue() returns a jobId and joined:false for a fresh (playlist, video) pair', async () => {
tests/integration/cost-guardrails.test.ts:323:    const result = await enqueuer.enqueue(
tests/integration/cost-guardrails.test.ts:324:      { ownerId: owner, enqueueIp: '1.2.3.4' },
tests/integration/cost-guardrails.test.ts:333:  it('enqueue() throws QuotaExceededError once the monthly allowance is exhausted', async () => {
tests/integration/cost-guardrails.test.ts:337:    await enqueuer.enqueue(
tests/integration/cost-guardrails.test.ts:338:      { ownerId: owner, enqueueIp: '1.2.3.4' },
tests/integration/cost-guardrails.test.ts:343:      enqueuer.enqueue(
tests/integration/cost-guardrails.test.ts:344:        { ownerId: owner, enqueueIp: '1.2.3.4' },
tests/integration/cost-guardrails.test.ts:353:    const verdict = await enqueuer.preflight('1.2.3.4', owner);
tests/integration/cost-guardrails.test.ts:362:    const cfg = await enqueuer.getGuardrailConfig();
supabase/migrations/0007_storage_and_rpcs.sql:7:-- storage.objects RLS: first path segment must equal auth.uid(); service_role full access.
supabase/migrations/0007_storage_and_rpcs.sql:17:  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');
supabase/migrations/0007_storage_and_rpcs.sql:26:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
supabase/migrations/0007_storage_and_rpcs.sql:44:grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:56:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0007_storage_and_rpcs.sql:74:grant execute on function reconcile_membership(uuid, text[]) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:76:-- merge_video_data: owner-guarded jsonb field merge. ARTIFACTS-AWARE (F6): the top-level
supabase/migrations/0007_storage_and_rpcs.sql:81:create function merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)
supabase/migrations/0007_storage_and_rpcs.sql:85:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0007_storage_and_rpcs.sql:97:revoke all on function merge_video_data(uuid, text, jsonb) from public;
supabase/migrations/0007_storage_and_rpcs.sql:98:grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:100:-- merge_video_data_bulk: apply merge_video_data semantics to many videos in ONE transaction.
supabase/migrations/0007_storage_and_rpcs.sql:102:create function merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)
supabase/migrations/0007_storage_and_rpcs.sql:107:    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
supabase/migrations/0007_storage_and_rpcs.sql:121:revoke all on function merge_video_data_bulk(uuid, jsonb) from public;
supabase/migrations/0007_storage_and_rpcs.sql:122:grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;
tests/integration/job-queue-store.test.ts:5:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
tests/integration/job-queue-store.test.ts:20:test('enqueue → claim(video) → complete round-trip through the store', async () => {
tests/integration/job-queue-store.test.ts:27:  // T13: SupabaseJobQueue.enqueue is dropped — enqueue via the service-role SupabaseEnqueuer.
tests/integration/job-queue-store.test.ts:28:  const enqueuer = new SupabaseEnqueuer(adminClient());
tests/integration/job-queue-store.test.ts:29:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { n: 1, durationSeconds: 100 } as never);
tests/integration/job-queue-store.test.ts:53:  const enqueuer = new SupabaseEnqueuer(adminClient());
tests/integration/job-queue-store.test.ts:54:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { n: 1, durationSeconds: 100 } as never);
tests/integration/job-queue-store.test.ts:76:  const enqueuer = new SupabaseEnqueuer(adminClient());
tests/integration/job-queue-store.test.ts:77:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { durationSeconds: 100 } as never);
tests/integration/job-queue-producer.test.ts:1:// tests/integration/job-queue-producer.test.ts
tests/integration/job-queue-producer.test.ts:16:// T13: session-client enqueue_job (6-arg) is dropped — enqueue via the service client with the
tests/integration/job-queue-producer.test.ts:19:function enqueue(ownerId: string, playlistId: string, videoId: string, over: Record<string, unknown> = {}) {
tests/integration/job-queue-producer.test.ts:20:  return svc.rpc('enqueue_job', {
tests/integration/job-queue-producer.test.ts:22:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null, ...over,
tests/integration/job-queue-producer.test.ts:26:test('enqueue creates a queued job; same live key joins it', async () => {
tests/integration/job-queue-producer.test.ts:30:  const first = await enqueue(userId, pl, vid);
tests/integration/job-queue-producer.test.ts:34:  const second = await enqueue(userId, pl, vid);
tests/integration/job-queue-producer.test.ts:39:test('a completed job is joined (not re-run) on re-enqueue of the same version', async () => {
tests/integration/job-queue-producer.test.ts:43:  const j = (await enqueue(userId, pl, vid)).data[0];
tests/integration/job-queue-producer.test.ts:44:  await adminClient().from('jobs').update({ status: 'completed' }).eq('id', j.job_id); // service_role sets terminal
tests/integration/job-queue-producer.test.ts:45:  const again = await enqueue(userId, pl, vid);
tests/integration/job-queue-producer.test.ts:55:  const j = (await enqueue(userId, pl, vid)).data[0];
tests/integration/job-queue-producer.test.ts:57:  const fresh = await enqueue(userId, pl, vid);
tests/integration/job-queue-producer.test.ts:69:  const ja = (await enqueue(aid, plA, vid)).data[0];
tests/integration/job-queue-producer.test.ts:70:  const jb = (await enqueue(bid, plB, vid)).data[0];
tests/integration/job-queue-producer.test.ts:75:test('concurrent enqueue of the same key yields exactly one live job', async () => {
tests/integration/job-queue-producer.test.ts:79:  const [r1, r2] = await Promise.all([enqueue(userId, pl, vid), enqueue(userId, pl, vid)]);
tests/integration/job-queue-producer.test.ts:91:  const first = await enqueue(userId, pl, vid, { p_payload: { model: 'old', durationSeconds: 100 } });
tests/integration/job-queue-producer.test.ts:92:  const second = await enqueue(userId, pl, vid, { p_payload: { model: 'new', durationSeconds: 100 } });
tests/integration/job-queue-producer.test.ts:99:test('anon can enqueue its own job', async () => {
tests/integration/job-queue-producer.test.ts:102:  const r = await enqueue(s.userId, pl, randomUUID());
tests/integration/job-queue-producer.test.ts:112:  const j = (await enqueue(aid, pl, randomUUID())).data[0];
supabase/migrations/0020_reservation_release.sql:2:-- Reserve→release lifecycle for spend_ledger. Money path — see
supabase/migrations/0020_reservation_release.sql:9:-- Locked down exactly like spend_ledger (0011:17-18): force RLS + NO policy blocks
supabase/migrations/0020_reservation_release.sql:10:-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
supabase/migrations/0020_reservation_release.sql:22:grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger
supabase/migrations/0020_reservation_release.sql:49:  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
supabase/migrations/0020_reservation_release.sql:80:    update spend_ledger
supabase/migrations/0020_reservation_release.sql:94:grant execute on function fail_job(uuid,text,uuid,text,boolean,boolean,boolean) to service_role;
supabase/migrations/0020_reservation_release.sql:121:    update spend_ledger set reserved_cents = reserved_cents - v_old_amt, updated_at = now()
supabase/migrations/0020_reservation_release.sql:164:    update spend_ledger sl
supabase/migrations/0020_reservation_release.sql:195:  v_promoted boolean;
supabase/migrations/0020_reservation_release.sql:204:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0020_reservation_release.sql:205:    into v_promoted
supabase/migrations/0020_reservation_release.sql:208:  if v_promoted is distinct from true then
supabase/migrations/0020_reservation_release.sql:243:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0020_reservation_release.sql:244:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0020_reservation_release.sql:267:-- released=true also guarded-decrement serve_owner_budget + spend_ledger by magazine_est_cents.
supabase/migrations/0020_reservation_release.sql:290:    update spend_ledger set reserved_cents = reserved_cents - v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0020_reservation_release.sql:295:                'settle_serve_model spend_ledger '||p_token::text, now());
tests/components/video-row-share-2c.test.tsx:47:    summaryMd: 'summary.md',
tests/api/pdf-route.test.ts:25:    overallScore: 4, summaryMd: 'raw/275_x.md', summaryHtml: 'htmls/275_x.html',
tests/integration/cloud-sync/e2e.int.test.ts:4:// driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
tests/integration/cloud-sync/e2e.int.test.ts:6:// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
tests/integration/cloud-sync/e2e.int.test.ts:10:// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
tests/integration/cloud-sync/e2e.int.test.ts:19:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/e2e.int.test.ts:20:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
tests/integration/cloud-sync/e2e.int.test.ts:35:const bodyHash = (b: string) => mdHash(b);
tests/integration/cloud-sync/e2e.int.test.ts:37: *  reconciledCorrectionsHash === mdHash(String(undefined ?? '')) === mdHash(''). */
tests/integration/cloud-sync/e2e.int.test.ts:38:const H_NO_CORRECTIONS = mdHash('');
tests/integration/cloud-sync/e2e.int.test.ts:43:    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
tests/integration/cloud-sync/e2e.int.test.ts:55:  //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
tests/integration/cloud-sync/e2e.int.test.ts:72:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:77:    // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
tests/integration/cloud-sync/e2e.int.test.ts:83:    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
tests/integration/cloud-sync/e2e.int.test.ts:91:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:106:      mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
tests/integration/cloud-sync/e2e.int.test.ts:112:      mdCorrectionsHash: mdHash('fix-v1'),  // STALE: MD was generated against an older corrections
tests/integration/cloud-sync/e2e.int.test.ts:115:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:133:    const staleHash = mdHash('stale-corrections'); // != mdHash('') → both sides corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:137:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:155:    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
tests/integration/cloud-sync/e2e.int.test.ts:177:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:206:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:224:    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
tests/integration/cloud-sync/e2e.int.test.ts:228:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:229:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:234:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:247:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:275:      extraArtifacts: { summaryPdf: { key: 'p.pdf', status: 'promoted' } },
tests/integration/cloud-sync/e2e.int.test.ts:278:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:293:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:300:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
tests/integration/cloud-sync/e2e.int.test.ts:313:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:321:  // ── Row 14 — additive PUBLISH is servable: cloud row advertises promoted → summaryReady true.
tests/integration/cloud-sync/e2e.int.test.ts:322:  it('row 14: additive publish sets promoted status → summaryReady true on the cloud', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:326:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:328:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:332:  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
tests/integration/cloud-sync/e2e.int.test.ts:337:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:343:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:350:  // ── Row 16 — promoted status never precedes a durable blob (blob promote fails mid-publish).
tests/integration/cloud-sync/e2e.int.test.ts:351:  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:356:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cloud-sync/e2e.int.test.ts:359:    // No cloud row advertises promoted without a durable MD blob.
tests/integration/cloud-sync/e2e.int.test.ts:361:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:376:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:383:    const r2 = await runSync(ctx.syncDeps());
tests/integration/share-serve.test.ts:9:/** Seed an owned promoted doc; returns coordinates incl. the real base (seedPromotedVideo keys
tests/integration/share-serve.test.ts:10: *  the MD as `${base}.md`). Pass status:'committed' for the un-promoted case. */
tests/integration/share-serve.test.ts:11:async function seedDoc(ownerId: string, status: 'promoted' | 'committed' = 'promoted') {
tests/integration/share-serve.test.ts:36:  // fine (it genuinely exists and is promoted), so the test would fail instead of accidentally
tests/integration/share-serve.test.ts:51:  it('denies when the summary is no longer promoted', async () => {
tests/integration/share-serve.test.ts:94:      data: { id: videoId, title: 'My Doc Title', language: 'en', summaryMd: 'v-titletest.md',
tests/integration/share-serve.test.ts:95:              docVersion: 1, artifacts: { summaryMd: { key: 'v-titletest.md', status: 'promoted' } } },
tests/integration/cancel-by-playlist.test.ts:13:// T13: enqueue_job moved to an 8-arg service-role-only RPC (p_owner_id explicit, client execute
tests/integration/cancel-by-playlist.test.ts:14:// grant revoked) — enqueue via the service client with the enqueuing owner's id.
tests/integration/cancel-by-playlist.test.ts:16:  return svc.rpc('enqueue_job', {
tests/integration/cancel-by-playlist.test.ts:18:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
supabase/migrations/0019_share_tokens_cascade.sql:42:-- the path. The `service_role` grant below is inert on its own: auth.uid() is null with no
supabase/migrations/0019_share_tokens_cascade.sql:43:-- end-user JWT, so a bare service_role caller cancels 0 rows (owner_id = auth.uid() never
supabase/migrations/0019_share_tokens_cascade.sql:60:grant execute on function request_cancel_playlist_jobs(uuid) to authenticated, service_role;
tests/integration/html-download.test.ts:50:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/html-download.test.ts:54:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/html-download.test.ts:68:async function seedDoc(ownerId: string, title: string, status: 'promoted' | 'committed' = 'promoted') {
tests/integration/html-download.test.ts:74:/** Seed an owner + promoted doc + MD blob, sign in as the owner, and arm the route's mocked
tests/integration/html-download.test.ts:122:  it('C2: owner GET format=md&download=1 → 200 text/markdown, attachment filename="<base>.md"; no reserve_serve_model call; spend_ledger unchanged', async () => {
tests/integration/html-download.test.ts:125:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:134:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:143:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:152:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:219:  it('C6: owner GET format=md when the MD blob is missing behind promoted → 409 repair needed', async () => {
tests/integration/html-download.test.ts:222:    // deliberately no seedSummaryBlob call — the MD blob is missing behind the 'promoted' status.
tests/integration/job-queue-playlist-identity.test.ts:19:  // T13: session-client enqueue_job (6-arg) is dropped — enqueue via the service client, owner explicit.
tests/integration/job-queue-playlist-identity.test.ts:22:    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/job-queue-playlist-identity.test.ts:24:  const a = await svc.rpc('enqueue_job', args(plA)); const b = await svc.rpc('enqueue_job', args(plB));
tests/integration/job-queue-playlist-identity.test.ts:29:test('enqueue against another owner\'s playlist is rejected (composite FK: p_owner_id must own p_playlist_id)', async () => {
tests/integration/job-queue-playlist-identity.test.ts:33:  const res = await svc.rpc('enqueue_job', {
tests/integration/job-queue-playlist-identity.test.ts:35:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
tests/api/jobs-route-guardrails.test.ts:11:jest.mock('@/lib/job-queue/producer', () => ({
tests/api/jobs-route-guardrails.test.ts:12:  ...jest.requireActual('@/lib/job-queue/producer'),
tests/api/jobs-route-guardrails.test.ts:13:  enqueuePlaylist: jest.fn(),
tests/api/jobs-route-guardrails.test.ts:18:jest.mock('@/lib/job-queue/enqueuer', () => ({
tests/api/jobs-route-guardrails.test.ts:25:import * as producer from '@/lib/job-queue/producer';
tests/api/jobs-route-guardrails.test.ts:27:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
tests/api/jobs-route-guardrails.test.ts:29:const enqueueMock = jest.mocked(producer.enqueuePlaylist);
tests/api/jobs-route-guardrails.test.ts:32:  enqueued: 1, joined: 1, skipped: 1, failed: 1, quotaBlocked: 1, capBlocked: 1, tooLong: 1,
tests/api/jobs-route-guardrails.test.ts:44:  enqueueMock.mockResolvedValue({
tests/api/jobs-route-guardrails.test.ts:94:  expect(enqueueMock).toHaveBeenCalledWith(
tests/api/jobs-route-guardrails.test.ts:96:    { ownerId: 'owner-1', enqueueIp: '9.9.9.9' },
tests/api/jobs-route-guardrails.test.ts:103:  expect(enqueueMock).toHaveBeenCalledWith(
tests/api/jobs-route-guardrails.test.ts:105:    { ownerId: 'owner-1', enqueueIp: '1.1.1.1' },
tests/integration/pdf-cloud.test.ts:20://    and spend_ledger is unchanged — proven against a mutation control (same request shape, no
tests/integration/pdf-cloud.test.ts:212:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/pdf-cloud.test.ts:216:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/pdf-cloud.test.ts:238:/** Seed an owner + promoted doc + MD blob, sign in as the owner, and arm the route's mocked
tests/integration/pdf-cloud.test.ts:319:  it('money: fresh model -> PDF request makes NO reserve_serve_model RPC on EITHER a cache-MISS or a genuine cache-HIT; spend_ledger unchanged', async () => {
tests/integration/pdf-cloud.test.ts:323:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/pdf-cloud.test.ts:347:      const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/annotations-rpc.test.ts:3:// Integration suite for the update_video_annotations RPC (Stage 2a Task 7) against a
tests/integration/annotations-rpc.test.ts:7:// This RPC is a DISTINCT write path from merge_video_data (unchanged): it allowlists
tests/integration/annotations-rpc.test.ts:24:describe('update_video_annotations RPC (via SupabaseMetadataStore.updateVideoAnnotations)', () => {
tests/integration/annotations-rpc.test.ts:35:    let idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:40:    idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:57:    const idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:112:    const { data, error } = await bClient.rpc('update_video_annotations', {
tests/integration/annotations-rpc.test.ts:123:  // (e) non-allowlisted key in p_set (e.g. summaryMd) is NOT written
tests/integration/annotations-rpc.test.ts:132:      p, videoId, { personalScore: 3, summaryMd: 'hacked.md' } as any, [],
tests/integration/annotations-rpc.test.ts:136:    const idx = await store.readIndex(p);
tests/integration/annotations-rpc.test.ts:139:    // summaryMd was already seeded (seedPromotedVideo sets it); assert the RPC's value
tests/integration/annotations-rpc.test.ts:141:    expect(v.summaryMd).not.toBe('hacked.md');
tests/integration/annotations-rpc.test.ts:144:  // (f) an existing merge_video_data write of summaryHtml:null still stores null
tests/integration/annotations-rpc.test.ts:145:  // (regression guard: merge_video_data itself is UNCHANGED by this migration).
tests/integration/annotations-rpc.test.ts:146:  it('merge_video_data (unchanged) still stores an explicit null for summaryHtml', async () => {
tests/integration/annotations-rpc.test.ts:153:    await store.updateVideoFields(p, videoId, { summaryHtml: null } as any);
tests/integration/annotations-rpc.test.ts:155:    const idx = await store.readIndex(p);
supabase/migrations/0011_cost_guardrails.sql:10:grant select, insert, update, delete on usage_counters to service_role;
supabase/migrations/0011_cost_guardrails.sql:12:create table spend_ledger (                                          -- global, one row per UTC day
supabase/migrations/0011_cost_guardrails.sql:17:alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
supabase/migrations/0011_cost_guardrails.sql:18:grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)
supabase/migrations/0011_cost_guardrails.sql:25:grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
supabase/migrations/0011_cost_guardrails.sql:31:  summary_max_attempts int not null default 1 check (summary_max_attempts >= 1),    -- billable executions/row; enqueue_job sets jobs.max_attempts. ≥1: else the guard test (est≥worst×attempts) is tautological at 0 while claim_next_job still bills once (round-4 H2)
supabase/migrations/0011_cost_guardrails.sql:38:grant select, insert, update, delete on guardrail_config to service_role;   -- no client access
supabase/migrations/0011_cost_guardrails.sql:41:alter table jobs add column enqueue_ip inet;                         -- server-provided (trusted); per-IP velocity
supabase/migrations/0011_cost_guardrails.sql:43:create index jobs_velocity on jobs (enqueue_ip, created_at);
supabase/migrations/0011_cost_guardrails.sql:46:-- enqueue_job rework — server-mediated, atomic money kill-switch (spec §4).
supabase/migrations/0011_cost_guardrails.sql:48:-- and replaces it with an 8-arg service_role-only RPC that adds trusted p_owner_id
supabase/migrations/0011_cost_guardrails.sql:49:-- + p_enqueue_ip and folds in the atomic quota debit / daily reserve / duration
supabase/migrations/0011_cost_guardrails.sql:50:-- backstop. Every `auth.uid()` becomes `p_owner_id` (under service_role auth.uid()
supabase/migrations/0011_cost_guardrails.sql:54:drop function if exists enqueue_job(uuid,text,int,text,text,jsonb);   -- the LIVE 0009 6-arg signature
supabase/migrations/0011_cost_guardrails.sql:58:create function enqueue_job(
supabase/migrations/0011_cost_guardrails.sql:60:  p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet
supabase/migrations/0011_cost_guardrails.sql:68:  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
supabase/migrations/0011_cost_guardrails.sql:69:  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
supabase/migrations/0011_cost_guardrails.sql:79:    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
supabase/migrations/0011_cost_guardrails.sql:83:    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload, enqueue_ip, max_attempts)
supabase/migrations/0011_cost_guardrails.sql:84:    values (p_owner_id, p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload, p_enqueue_ip, v_maxatt)
supabase/migrations/0011_cost_guardrails.sql:112:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0011_cost_guardrails.sql:113:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0011_cost_guardrails.sql:130:        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;
supabase/migrations/0011_cost_guardrails.sql:137:revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
supabase/migrations/0011_cost_guardrails.sql:138:grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;
supabase/migrations/0011_cost_guardrails.sql:141:-- enqueue_preflight — ADVISORY, service_role-only gate (spec §5). Four
supabase/migrations/0011_cost_guardrails.sql:144:-- enqueue_job; this gate is abuse-hardening only (velocity/ceiling/queue-depth).
supabase/migrations/0011_cost_guardrails.sql:147:create function enqueue_preflight(p_ip inet, p_owner_id uuid)
supabase/migrations/0011_cost_guardrails.sql:156:  if auth.role() <> 'service_role' then raise exception 'enqueue_preflight: server only'; end if;
supabase/migrations/0011_cost_guardrails.sql:164:  -- Per-IP hourly job count (uses the jobs_velocity index: enqueue_ip, created_at).
supabase/migrations/0011_cost_guardrails.sql:166:    where enqueue_ip = p_ip and created_at > now() - interval '1 hour';
supabase/migrations/0011_cost_guardrails.sql:188:    from spend_ledger where day = v_day;
supabase/migrations/0011_cost_guardrails.sql:195:revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
supabase/migrations/0011_cost_guardrails.sql:196:grant execute on function enqueue_preflight(inet,uuid) to service_role;
tests/integration/reservation-release.test.ts:5:// pattern of looking up the job row rather than threading ids through enqueueSummary's void return).
tests/integration/reservation-release.test.ts:11:// R2-H2: this serial suite enqueues many 150¢ summary jobs and deliberately leaves KEEP/back-dated
tests/integration/reservation-release.test.ts:22:  // ledger_audit and spend_ledger rows scoped by day. A far-past FIXED date can never collide
tests/integration/reservation-release.test.ts:26:  it('service_role can insert and read ledger_audit', async () => {
tests/integration/reservation-release.test.ts:56:// Canonical enqueue helper — the REAL 8-arg enqueue_job signature (mirrors cancel-job-rpc.test.ts:17).
tests/integration/reservation-release.test.ts:58:// p_enqueue_ip:null, and a durationSeconds payload the duration guardrail (0018:42) requires.
tests/integration/reservation-release.test.ts:59:export async function enqueueSummary(ownerId: string, playlistId: string, videoId: string) {
tests/integration/reservation-release.test.ts:60:  const { error } = await adminClient().rpc('enqueue_job', {
tests/integration/reservation-release.test.ts:62:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/reservation-release.test.ts:64:  if (error) throw error;   // 150¢ reserved on today's spend_ledger
tests/integration/reservation-release.test.ts:68:async function enqueueAndLease(ownerId: string, playlistId: string, videoId = 'vid-t2') {
tests/integration/reservation-release.test.ts:69:  await enqueueSummary(ownerId, playlistId, videoId);
tests/integration/reservation-release.test.ts:77:// Same as enqueueAndLease but scopes the claim to THIS videoId. Task 13's tests requeue a job
tests/integration/reservation-release.test.ts:79:// tests — a later, unrelated enqueueAndLease(..., p_video_id: null) elsewhere in a long full-file
tests/integration/reservation-release.test.ts:80:// run could otherwise race-claim that leftover requeued job instead of the one it just enqueued.
tests/integration/reservation-release.test.ts:81:async function enqueueAndLeaseVideo(ownerId: string, playlistId: string, videoId: string) {
tests/integration/reservation-release.test.ts:82:  await enqueueSummary(ownerId, playlistId, videoId);
tests/integration/reservation-release.test.ts:91:  const { data } = await adminClient().from('spend_ledger').select('reserved_cents').eq('day', day).maybeSingle();
tests/integration/reservation-release.test.ts:100:    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId);
tests/integration/reservation-release.test.ts:117:    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2b');
tests/integration/reservation-release.test.ts:133:    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2c');
tests/integration/reservation-release.test.ts:148:    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2d');
tests/integration/reservation-release.test.ts:151:    await adminClient().from('spend_ledger').update({ reserved_cents: 10 }).eq('day', day);
tests/integration/reservation-release.test.ts:167:    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2e');
tests/integration/reservation-release.test.ts:171:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
tests/integration/reservation-release.test.ts:185:    await enqueueSummary(u.user.id, playlistId, 'vid-t3');
tests/integration/reservation-release.test.ts:197:    await enqueueSummary(u.user.id, playlistId, 'vid-t3b');
tests/integration/reservation-release.test.ts:213:    await enqueueSummary(u.user.id, playlistId, 'vid-t3c');
tests/integration/reservation-release.test.ts:228:    await enqueueSummary(u.user.id, playlistId, 'vid-t3d');
tests/integration/reservation-release.test.ts:232:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
tests/integration/reservation-release.test.ts:246:    await enqueueSummary(u.user.id, playlistId, 'vid-t14-b2');
tests/integration/reservation-release.test.ts:268:    for (const v of ['vid-t4a', 'vid-t4b']) await enqueueSummary(u.user.id, playlistId, v);
tests/integration/reservation-release.test.ts:274:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
tests/integration/reservation-release.test.ts:287:    await enqueueSummary(u.user.id, playlistId, 'vid-t4c');
tests/integration/reservation-release.test.ts:303:    for (const v of ['vid-t4d', 'vid-t4e']) await enqueueSummary(u.user.id, playlistId, v);
tests/integration/reservation-release.test.ts:309:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 10 });
tests/integration/reservation-release.test.ts:335:    for (const v of ['vid-t14-b4a', 'vid-t14-b4b']) await enqueueSummary(u.user.id, playlistId, v);
tests/integration/reservation-release.test.ts:364:    // NOTE: spend_ledger is a single row PER DAY shared by every test in this file (Tasks 1-4 leave
tests/integration/reservation-release.test.ts:366:    // freshly-created owner's row is genuinely isolated — asserted absolutely. spend_ledger uses a
tests/integration/reservation-release.test.ts:379:    expect(await ledgerFor(day)).toBe(ledgerBefore);            // spend_ledger -=6 (back to baseline)
tests/integration/reservation-release.test.ts:434:    const { jobId: jobId1, leaseToken: lt1 } = await enqueueAndLease(u1.user.id, pl1, 'vid-t12-5a');
tests/integration/reservation-release.test.ts:449:    const { jobId: jobId2, leaseToken: lt2 } = await enqueueAndLease(u2.user.id, pl2, 'vid-t12-5b');
tests/integration/reservation-release.test.ts:463:    const { jobId } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-7');
tests/integration/reservation-release.test.ts:476:    expect(await ledgerFor(day)).toBe(before);           // reaper touches jobs, never spend_ledger — KEEP
tests/integration/reservation-release.test.ts:482:    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-10');
tests/integration/reservation-release.test.ts:527:  it('behavior 23: retry-keep path is reachable — one enqueue reserves once, even across a KEEP retry', async () => {
tests/integration/reservation-release.test.ts:530:    // re-claim itself does NOT add a second reservation (claim_next_job never touches spend_ledger).
tests/integration/reservation-release.test.ts:533:    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-23');
tests/integration/reservation-release.test.ts:551:    expect(await ledgerFor(day)).toBe(before);                  // one enqueue, one reservation — still unchanged
tests/integration/reservation-release.test.ts:598:    const { jobId } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-25');
tests/integration/reservation-release.test.ts:610:    expect(await ledgerFor(day)).toBe(before);              // spend_ledger unchanged — accepted §2.4b residual (KEPT forever, no reaper release)
tests/integration/reservation-release.test.ts:622:    // Deterministic baseline: this file's shared "today" spend_ledger row accumulates residue
tests/integration/reservation-release.test.ts:625:    await svc.from('spend_ledger').update({ reserved_cents: 0 }).eq('day', day);
tests/integration/reservation-release.test.ts:631:      for (const v of vids) await enqueueSummary(u.user.id, playlistId, v);
tests/integration/reservation-release.test.ts:634:      // a 4th enqueue → PJ002 (cap full); the whole guardrail transaction rolls back, no partial job
tests/integration/reservation-release.test.ts:635:      await expect(enqueueSummary(u.user.id, playlistId, 'vid-t12-26d')).rejects.toMatchObject({ code: 'PJ002' });
tests/integration/reservation-release.test.ts:651:      // cap re-opened: a fresh enqueue now ADMITS again — the §1 outage self-DoS is closed
tests/integration/reservation-release.test.ts:652:      await expect(enqueueSummary(u.user.id, playlistId, 'vid-t12-26e')).resolves.toBeUndefined();
tests/integration/reservation-release.test.ts:672:    const { jobId: meteredJobId, leaseToken: meteredLease } = await enqueueAndLeaseVideo(u.user.id, playlistId, 'vid-t13a-metered');
tests/integration/reservation-release.test.ts:683:    await enqueueSummary(u.user.id, playlistId, 'vid-t13a-plain');
tests/integration/reservation-release.test.ts:706:      const { jobId, leaseToken: lease1 } = await enqueueAndLeaseVideo(u.user.id, playlistId, 'vid-t13b');
tests/integration/reservation-release.test.ts:742:    const { jobId, leaseToken } = await enqueueAndLeaseVideo(u.user.id, playlistId, 'vid-t13e');
tests/integration/reservation-release.test.ts:758:    const { jobId: meteredJobId, leaseToken: meteredLease } = await enqueueAndLeaseVideo(u.user.id, playlistId, 'vid-t13c-metered');
tests/integration/reservation-release.test.ts:767:    await enqueueSummary(u.user.id, playlistId, 'vid-t13c-plain');
tests/integration/serve-owner-budget.test.ts:21:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-owner-budget.test.ts:41:  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
tests/integration/serve-owner-budget.test.ts:58:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-owner-budget.test.ts:156:it('P17: an authenticated session can still reserve (writes to service_role-only tables succeed)', async () => {
tests/integration/serve-owner-budget.test.ts:176:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-owner-budget.test.ts:204://      serve_owner_budget is service_role-only + force-RLS with no client policy; the RPC's internal
tests/integration/cloud-sync/cloud-stamping.int.test.ts:6:// `opts.editedAt` through to update_video_annotations.
tests/integration/cloud-sync/cloud-stamping.int.test.ts:21:  it('cloud store forwards opts.editedAt through updateVideoFields (merge_video_data)', async () => {
tests/integration/cloud-sync/cloud-stamping.int.test.ts:25:    await store.updateVideoFields(ctx.principal, videoId, { corrections: 'fixed via regenerate' }, { editedAt: '2018-03-03T00:00:00.000Z' });
tests/api/regenerate.test.ts:21:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/regenerate.test.ts:24:const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
tests/api/regenerate.test.ts:49:  summaryMd: SUMMARY_MD,
tests/api/regenerate.test.ts:93:  it('returns 422 when video has no summaryMd', async () => {
tests/api/regenerate.test.ts:96:      videos: [{ ...baseVideo, summaryMd: null }],
tests/api/regenerate.test.ts:121:    // updateVideoFields for corrections should be called before fixSummary
supabase/migrations/0016_update_video_annotations.sql:1:-- supabase/migrations/0016_update_video_annotations.sql
supabase/migrations/0016_update_video_annotations.sql:3:-- update_video_annotations: owner-guarded personal-annotation writer (Stage 2a Task 7).
supabase/migrations/0016_update_video_annotations.sql:4:-- Distinct from merge_video_data (UNCHANGED, left untouched by this migration):
supabase/migrations/0016_update_video_annotations.sql:6:--     non-allowlisted key in p_set (e.g. summaryMd) is silently dropped, never written.
supabase/migrations/0016_update_video_annotations.sql:8:--     parameter and no service_role bypass. SECURITY INVOKER + RLS both apply; this
supabase/migrations/0016_update_video_annotations.sql:13:create function update_video_annotations(
supabase/migrations/0016_update_video_annotations.sql:29:revoke all on function update_video_annotations(uuid, text, jsonb, text[]) from public;
supabase/migrations/0016_update_video_annotations.sql:30:grant execute on function update_video_annotations(uuid, text, jsonb, text[]) to authenticated;
tests/integration/dig-serve-interactive.test.ts:81:    const { data: before } = await admin.from('spend_ledger').select('amount_cents');
tests/integration/dig-serve-interactive.test.ts:89:    const { data: after } = await admin.from('spend_ledger').select('amount_cents');
tests/integration/serve-doc-materialize.test.ts:24:// Shared helper — inserts owner_id (NOT NULL + composite FK) + the worker's promoted `data` shape,
tests/integration/serve-doc-materialize.test.ts:25:// so the reserve RPC sees an owned+promoted doc. resolveMagazineModel operates on `parsed` directly,
tests/integration/serve-doc-materialize.test.ts:42:  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
tests/integration/serve-doc-materialize.test.ts:49:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-doc-materialize.test.ts:270:// release rule). beforeEach fully clears spend_ledger/serve_owner_budget/serve_model_charge, so any
tests/integration/summary-handler.test.ts:104:test('(a) happy path: Video row persisted + promoted + blob present', async () => {
tests/integration/summary-handler.test.ts:122:  expect(data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/summary-handler.test.ts:125:  expect(data.summaryMd).toBe(`${baseName}.md`);
tests/integration/summary-handler.test.ts:126:  expect(data.artifacts.summaryMd.key).toBe(`${baseName}.md`);
tests/integration/summary-handler.test.ts:163:  expect(after.data!.data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/summary-handler.test.ts:198:// (i) doc-version mismatch → NonRetryableError, Gemini not called. A job enqueued at a doc
tests/integration/summary-handler.test.ts:255://     deterministic key, promotes cleanly, Gemini called again (nothing was promoted).
tests/integration/summary-handler.test.ts:272:  expect(midRow.data!.data.artifacts.summaryMd.status).toBe('committed');
tests/integration/summary-handler.test.ts:284:  expect(finalRow.data!.data.artifacts.summaryMd.status).toBe('promoted'); // no orphan
tests/integration/summary-handler.test.ts:285:  expect(generateSummary).toHaveBeenCalledTimes(2); // skip did NOT fire — nothing was promoted
tests/integration/summary-handler.test.ts:288:  expect(finalRow.data!.data.summaryMd).toBe(`${baseName}.md`);
tests/integration/summary-handler.test.ts:373:    expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
lib/timestamp-audit.ts:36:  const { videos } = await store.readIndex(principal);
lib/timestamp-audit.ts:39:    if (v.summaryMd) {
lib/timestamp-audit.ts:41:      classify(summaries, folder, v.id, v.summaryMd, ver.major, CURRENT_DOC_VERSION.major);
tests/integration/dig-cloud.test.ts:10:// Proves: enqueue -> handler -> per-section blob round-trip (tokens preserved); owner isolation
tests/integration/dig-cloud.test.ts:11:// (non-owner -> 404, no enqueue); no-charge-on-dedup + its mutation control (charge DOES happen
tests/integration/dig-cloud.test.ts:15:// 409, never a phantom 202); and atomic same-section concurrent enqueue charges exactly once.
tests/integration/dig-cloud.test.ts:22:import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
tests/integration/dig-cloud.test.ts:23:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
tests/integration/dig-cloud.test.ts:42:  // dig is the FIRST integration path that goes through enqueue_preflight — pin its admission
tests/integration/dig-cloud.test.ts:54:  await admin.from('spend_ledger').delete().neq('day', '1970-01-01');
tests/integration/dig-cloud.test.ts:67:  it('enqueue → handler → per-section blob round-trip (tokens preserved)', async () => {
tests/integration/dig-cloud.test.ts:72:    const res = await enqueueDig({
tests/integration/dig-cloud.test.ts:73:      supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false,
tests/integration/dig-cloud.test.ts:74:      videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
tests/integration/dig-cloud.test.ts:90:  it('a non-owner cannot trigger dig on another user\'s video (404, no enqueue)', async () => {
tests/integration/dig-cloud.test.ts:95:    const spy = jest.spyOn(SupabaseEnqueuer.prototype, 'enqueue');
tests/integration/dig-cloud.test.ts:96:    const res = await enqueueDig({
tests/integration/dig-cloud.test.ts:97:      supabase: otherClient, enqueuer: new SupabaseEnqueuer(admin), userId: other.user.id, isAnonymous: false,
tests/integration/dig-cloud.test.ts:98:      videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
tests/integration/dig-cloud.test.ts:105:  it('dedup: blob present → 200 ready, NO enqueue rpc, ledger + usage unchanged', async () => {
tests/integration/dig-cloud.test.ts:114:    const { data: slBefore } = await admin.from('spend_ledger').select('*'); // spend_ledger is global-by-day
tests/integration/dig-cloud.test.ts:115:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
tests/integration/dig-cloud.test.ts:117:    expect(rpcSpy.mock.calls.filter((c) => c[0] === 'enqueue_job').length).toBe(0);
tests/integration/dig-cloud.test.ts:120:    // The dedup (200-ready) path must also leave the global spend_ledger untouched — a spurious
tests/integration/dig-cloud.test.ts:121:    // ledger write bypassing usage_counters/enqueue_job would otherwise slip past the checks above.
tests/integration/dig-cloud.test.ts:122:    const { data: slAfter } = await admin.from('spend_ledger').select('*');
tests/integration/dig-cloud.test.ts:127:  it('mutation control: NO pre-seeded blob → 202, enqueue_job called once, dig usage +1', async () => {
tests/integration/dig-cloud.test.ts:131:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
tests/integration/dig-cloud.test.ts:147:      const r = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: sec, enqueueIp: null });
tests/integration/dig-cloud.test.ts:159:  it('version bump re-enqueues + charges: an OLD completed dig row + old blob does NOT dedup the current version', async () => {
tests/integration/dig-cloud.test.ts:165:    // from a fresh enqueue (202 + used=1), passing for the wrong reason. Throw so the precondition
tests/integration/dig-cloud.test.ts:171:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
tests/integration/dig-cloud.test.ts:172:    expect(res.status).toBe(202); // current-version slot free → enqueued
tests/integration/dig-cloud.test.ts:184:    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
tests/integration/dig-cloud.test.ts:185:    expect(res.status).toBe(409); // enqueue_job JOINs the completed row; blob still absent → repair
tests/integration/dig-cloud.test.ts:188:  it('concurrent SAME-section enqueue charges exactly once (atomic INSERT-or-JOIN)', async () => {
tests/integration/dig-cloud.test.ts:192:    const call = () => enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
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
tests/integration/cloud-sync/stamping.int.test.ts:94:      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
tests/integration/delete-playlist-store.test.ts:35:// enqueue_job is the 8-arg service-role-only RPC (0018): owner id explicit.
tests/integration/delete-playlist-store.test.ts:36:function enqueueJob(ownerId: string, playlistId: string, videoId: string) {
tests/integration/delete-playlist-store.test.ts:37:  return svc.rpc('enqueue_job', {
tests/integration/delete-playlist-store.test.ts:39:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/delete-playlist-store.test.ts:48:  const jobRes = await enqueueJob(userId, playlistId, `v-${randomUUID()}`);
tests/integration/delete-playlist-store.test.ts:74:  const jobRes = await enqueueJob(ownerAId, playlistId, `v-${randomUUID()}`);
supabase/migrations/0008_jobs_queue.sql:38:-- producers: read + insert only (NEVER direct update/delete — lifecycle is RPC-only)
supabase/migrations/0008_jobs_queue.sql:40:grant select, insert, update, delete on public.jobs to service_role;
supabase/migrations/0008_jobs_queue.sql:42:-- enqueue: atomic insert-or-join over live+completed states (table aliased to avoid the
supabase/migrations/0008_jobs_queue.sql:44:create function enqueue_job(
supabase/migrations/0008_jobs_queue.sql:53:    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
supabase/migrations/0008_jobs_queue.sql:70:        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;  -- spec §9.2
supabase/migrations/0008_jobs_queue.sql:77:revoke all on function enqueue_job(text,int,text,text,jsonb) from public;
supabase/migrations/0008_jobs_queue.sql:78:grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
supabase/migrations/0008_jobs_queue.sql:80:-- cancel: SECURITY DEFINER because producers have no direct update grant. Explicit owner guard.
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
tests/integration/jobs-producer-polling.test.ts:14:// T13: session-client enqueue_job (6-arg) is dropped. `summary` jobs go through the real
tests/integration/jobs-producer-polling.test.ts:15:// enqueue_job (service-role, owner explicit); `dig` is rejected by enqueue_job entirely in 1D
tests/integration/jobs-producer-polling.test.ts:18:function enqueue(ownerId: string, pl: string, vid: string, kind: 'summary' | 'dig' = 'summary') {
tests/integration/jobs-producer-polling.test.ts:25:  return svc.rpc('enqueue_job', {
tests/integration/jobs-producer-polling.test.ts:27:    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
tests/integration/jobs-producer-polling.test.ts:34:  const e1 = await enqueue(userId, pl, 'vid-a'); expect(e1.error).toBeNull();
tests/integration/jobs-producer-polling.test.ts:35:  const e2 = await enqueue(userId, pl, 'vid-b'); expect(e2.error).toBeNull();
tests/integration/jobs-producer-polling.test.ts:36:  const e3 = await enqueue(userId, pl, 'vid-a', 'dig'); expect(e3.error).toBeNull();   // must be excluded (job_kind)
tests/integration/jobs-producer-polling.test.ts:40:  const e4 = await enqueue(userId, pl2, 'vid-other'); expect(e4.error).toBeNull();
tests/integration/jobs-producer-polling.test.ts:75:  const enq = await enqueue(userId, pl, 'vid-a');
tests/integration/jobs-producer-polling.test.ts:79:  // failed enqueue would make the isolation assertion pass vacuously.
tests/integration/jobs-producer-polling.test.ts:95:  const first = await enqueue(userId, pl, 'vid-retry');
tests/integration/jobs-producer-polling.test.ts:103:  const second = await enqueue(userId, pl, 'vid-retry');
tests/integration/jobs-producer-polling.test.ts:118:  const enq = await enqueue(userId, pl, 'vid-a');
tests/integration/worker-persistence-rpcs.test.ts:55:test('status-only persist preserves the prior summaryMd key', async () => {
tests/integration/worker-persistence-rpcs.test.ts:59:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:60:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:62:  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
tests/integration/worker-persistence-rpcs.test.ts:63:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/worker-persistence-rpcs.test.ts:67:test('persist_summary preserves a sibling artifact kind (deepDiveMd) across a summaryMd status write', async () => {
tests/integration/worker-persistence-rpcs.test.ts:71:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:74:  // deep-dive artifact) so we can assert persist_summary never touches other artifact kinds.
tests/integration/worker-persistence-rpcs.test.ts:86:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:90:  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
tests/integration/worker-persistence-rpcs.test.ts:91:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/worker-persistence-rpcs.test.ts:94:test('persist_summary status is monotonic — a committed write never downgrades a promoted artifact', async () => {
tests/integration/worker-persistence-rpcs.test.ts:99:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:100:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:102:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/worker-persistence-rpcs.test.ts:105:test('persist_summary preserves operational fields owned by other features (archived) against the stale payload', async () => {
tests/integration/worker-persistence-rpcs.test.ts:109:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:117:  // The job's enqueue-time snapshot still carries archived:false — must NOT revert the row.
tests/integration/worker-persistence-rpcs.test.ts:118:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T', archived: false }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:123:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/worker-persistence-rpcs.test.ts:126:test('persist_summary preserves ALL concurrent non-summary state (membership order + other-feature fields) against the stale payload', async () => {
tests/integration/worker-persistence-rpcs.test.ts:130:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3 }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:132:  // A concurrent writer (reconcile_membership / merge_video_data / dig pipeline) reorders the video
tests/integration/worker-persistence-rpcs.test.ts:139:  // The stale enqueue-time payload still carries playlistIndex:3 and no digDeeperMd — persist_summary
tests/integration/worker-persistence-rpcs.test.ts:141:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3, ratings: { usefulness: 5 } }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:147:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/worker-persistence-rpcs.test.ts:150:test('a status-only persist preserves existing summary-owned fields (language/ratings/docVersion), not just summaryMd', async () => {
tests/integration/worker-persistence-rpcs.test.ts:155:  const full = { id: vid, summaryMd: '1_t.md', language: 'en', ratings: { usefulness: 4 }, overallScore: 4, docVersion: { major: 3, minor: 3 } };
tests/integration/worker-persistence-rpcs.test.ts:156:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: full, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:159:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:165:  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
tests/integration/worker-persistence-rpcs.test.ts:168:test('persist_summary monotonic status is KEY-SCOPED — a committed write with a NEW key is allowed through', async () => {
tests/integration/worker-persistence-rpcs.test.ts:172:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_old.md' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:174:  // key's promoted status (else the row would claim a promoted artifact for an un-promoted blob).
tests/integration/worker-persistence-rpcs.test.ts:175:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_new.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:177:  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_new.md');
tests/integration/worker-persistence-rpcs.test.ts:178:  expect(row.data!.data.artifacts.summaryMd.status).toBe('committed');
tests/integration/worker-persistence-rpcs.test.ts:192:test('persist_summary raises when there is no video row', async () => {
tests/integration/worker-persistence-rpcs.test.ts:195:  const res = await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:211:test('persist_summary rejects an owner mismatch', async () => {
tests/integration/worker-persistence-rpcs.test.ts:218:  const res = await admin.rpc('persist_summary', { p_owner_id: aid, p_playlist_id: victimPl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
lib/summary-audit.ts:19:  const { videos } = await store.readIndex(principal);
lib/summary-audit.ts:23:    if (!v.summaryMd) continue;
lib/summary-audit.ts:26:    // `summaryMd` is index-controlled; a corrupt/hand-edited entry could contain `../`. Only accept
lib/summary-audit.ts:33:    // Validate the raw summaryMd first — a `../` here is an unsafe (traversal) index entry. Only
lib/summary-audit.ts:37:    const direct = contained(v.summaryMd);
lib/summary-audit.ts:42:    const candidates = [direct, contained(path.join('archived', v.summaryMd))]
supabase/migrations/0004_test_exec_sql.sql:2:-- Read-only catalog inspection for the integration suite. Granted to service_role ONLY.
supabase/migrations/0004_test_exec_sql.sql:11:grant execute on function exec_sql(text) to service_role;
tests/integration/videos-route-cloud.test.ts:8:// resolveOwnedPlaylistKey, metadataStore.readIndex) runs for real. Same pattern as
tests/components/video-menu-cloud-2c.test.tsx:20:  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
tests/integration/cancel-job-rpc.test.ts:14:// T13: session-client enqueue_job (6-arg) is dropped; enqueue via the service client with the
tests/integration/cancel-job-rpc.test.ts:16:function enqueue(ownerId: string, pl: string, vid: string) {
tests/integration/cancel-job-rpc.test.ts:17:  return svc.rpc('enqueue_job', { p_owner_id: ownerId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1,
tests/integration/cancel-job-rpc.test.ts:18:    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null });
tests/integration/cancel-job-rpc.test.ts:24:  const j = (await enqueue(userId, pl, randomUUID())).data[0];
tests/integration/cancel-job-rpc.test.ts:36:  const j = (await enqueue(userId, pl, randomUUID())).data[0];
tests/integration/cancel-job-rpc.test.ts:49:  const j = (await enqueue(userId, pl, randomUUID())).data[0];
tests/integration/cancel-job-rpc.test.ts:62:  const j = (await enqueue(userId, pl, randomUUID())).data[0];
tests/api/dig-state.test.ts:32:    summaryMd: 'test-video.md',
tests/integration/worker-main.test.ts:4:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
tests/integration/worker-main.test.ts:29:  // T13: SupabaseJobQueue.enqueue is dropped — enqueue via the service-role SupabaseEnqueuer.
tests/integration/worker-main.test.ts:30:  const enqueuer = new SupabaseEnqueuer(adminClient());
tests/integration/worker-main.test.ts:31:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { hi: 1, durationSeconds: 100 } as never);
tests/integration/worker-main.test.ts:36:    // integration test files (e.g. job-queue-producer.test.ts intentionally leaves some
tests/integration/helpers/clients.ts:5:const service = () => process.env.SUPABASE_SERVICE_ROLE_KEY!;
tests/integration/helpers/clients.ts:37: * T13: `enqueue_job` (T2) now enforces PJ001 (monthly quota) / PJ002 (daily $ cap) / PJ003
tests/integration/helpers/clients.ts:39: * files migrated in T13 call the real `enqueue_job`/`SupabaseEnqueuer` a nontrivial number of
tests/integration/job-queue-worker.test.ts:8:// T13: session-client enqueue_job (6-arg) is dropped — enqueue via the service client with the
tests/integration/job-queue-worker.test.ts:10:async function enqueueScoped(videoId: string, over: Record<string, unknown> = {}) {
tests/integration/job-queue-worker.test.ts:17:  const r = await admin().rpc('enqueue_job', {
tests/integration/job-queue-worker.test.ts:19:    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null, ...over });
tests/integration/job-queue-worker.test.ts:26:  const vid = randomUUID(); await enqueueScoped(vid);
tests/integration/job-queue-worker.test.ts:36:  const vid = randomUUID(); const id = await enqueueScoped(vid);
tests/integration/job-queue-worker.test.ts:47:  const vid = randomUUID(); const id = await enqueueScoped(vid);
tests/integration/job-queue-worker.test.ts:48:  // T13: enqueue_job now stamps max_attempts from guardrail_config.summary_max_attempts (default
tests/integration/job-queue-worker.test.ts:67:  const vid = randomUUID(); const id = await enqueueScoped(vid);
tests/integration/job-queue-worker.test.ts:87:  // T13: enqueue_job now rejects any p_job_kind other than 'summary' (unsupported_job_kind) —
tests/integration/job-queue-worker.test.ts:90:  await enqueueScoped(vid); await enqueueScoped(vid, { p_section_id: 5 }); // 2 live jobs, same video
tests/integration/job-queue-worker.test.ts:98:  const vid = randomUUID(); const id = await enqueueScoped(vid);
tests/integration/job-queue-worker.test.ts:112:  const vid = randomUUID(); const id = await enqueueScoped(vid);
tests/integration/job-queue-worker.test.ts:114:  // a second claim + non-retryable fail → 'failed'); enqueue_job's default max_attempts (1, from
tests/integration/job-queue-worker.test.ts:135:  const vid = randomUUID(); const id = await enqueueScoped(vid);
tests/integration/job-queue-worker.test.ts:143:test('claim requires service_role', async () => {
supabase/migrations/0013_share_tokens.sql:2:-- Stage 1F-b share tokens (spec §4.1/§4.2). force-RLS + service_role-only grants (mirrors
supabase/migrations/0013_share_tokens.sql:18:grant select, insert, update, delete on share_tokens to service_role;  -- no anon/authenticated policy
supabase/migrations/0013_share_tokens.sql:21:-- Ownership + promoted predicate helper (inlined; same shape as reserve_serve_model, 0012:44-47).
supabase/migrations/0013_share_tokens.sql:27:  v_promoted boolean;
supabase/migrations/0013_share_tokens.sql:36:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0013_share_tokens.sql:37:    into v_promoted
supabase/migrations/0013_share_tokens.sql:40:  if v_promoted is distinct from true then
supabase/migrations/0013_share_tokens.sql:41:    raise exception 'create_share_token: denied';  -- not owned or not promoted → coarse 404
tests/integration/helpers/cloud.ts:52:  playlistDataRoot: string;    // the per-playlist dir runSync resolves for this key
tests/integration/helpers/cloud.ts:63:  /** Build the SyncDeps for a runSync() call. failCloudPromote wraps the cloud blob store so its
tests/integration/helpers/cloud.ts:67:  /** Read the sync manifest runSync wrote for this ctx's playlist. */
tests/integration/helpers/cloud.ts:69:  /** Sum of reserved_cents + actual_cents across spend_ledger (money-safety assertions).
tests/integration/helpers/cloud.ts:70:   *  spend_ledger is GLOBAL (one row per UTC day, NO owner_id) → whole-table total; money-safety
tests/integration/helpers/cloud.ts:72:   *  spend_ledger grants NO client access. */
tests/integration/helpers/cloud.ts:118:      const { error } = await userClient.rpc('persist_summary', {
tests/integration/helpers/cloud.ts:149:        .from('spend_ledger').select('reserved_cents,actual_cents');
tests/integration/helpers/cloud.ts:174: *  with one promoted-summary video, local replica empty (hydrate). `localNote` additionally seeds a
tests/integration/helpers/cloud.ts:199:    // ensureReceiverSlot creates the cloud playlist row during the run.
tests/integration/helpers/cloud.ts:204:  // Cloud playlist + one promoted-summary video (hydrate source / two-sided cloud side).
tests/integration/helpers/cloud.ts:233:  await ctx.local.claimVideoSlot(lp, videoId);
tests/integration/helpers/cloud.ts:244:    summaryMd: `${base}.md`,
tests/integration/helpers/cloud.ts:252:  await ctx.local.upsertVideo(lp, video);
tests/integration/helpers/cloud.ts:256:/** Seeds a playlist + a promoted video owned by ctx.userId (via admin client, setup only).
tests/integration/helpers/cloud.ts:283:// the e2e scenarios can drive the divergent-MD Class-A COPY path (transferClassA
tests/integration/helpers/cloud.ts:284:// + companionTransfer), not just the additive hydrate path (copyAdditiveVideo).
tests/integration/helpers/cloud.ts:286:// blob and set video.summaryMd to the KEY they wrote.
tests/integration/helpers/cloud.ts:294:  /** Blob KEY (video.summaryMd). Default `${videoId}.md`. `null` = summary-less video (no blob). */
tests/integration/helpers/cloud.ts:295:  summaryMd?: string | null;
tests/integration/helpers/cloud.ts:296:  /** MD BODY written to the blob at the summaryMd key. Omit to skip the blob write. */
tests/integration/helpers/cloud.ts:313:  status?: 'promoted' | 'committed';
tests/integration/helpers/cloud.ts:317:  /** Extra artifacts.* pointers MERGED alongside summaryMd (e.g. a summaryPdf that must be dropped). */
tests/integration/helpers/cloud.ts:341: *  worker's promoted-video shape (seed.ts) but with full control over the Class-A/companion signals. */
tests/integration/helpers/cloud.ts:343:  const summaryMd = f.summaryMd === undefined ? `${videoId}.md` : f.summaryMd;
tests/integration/helpers/cloud.ts:344:  const base = summaryMd ? summaryMd.replace(/\.md$/, '') : null;
tests/integration/helpers/cloud.ts:354:    summaryMd,
tests/integration/helpers/cloud.ts:374:            ...(base ? { summaryMd: { key: `${base}.md`, status: f.status ?? 'promoted' } } : {}),
tests/integration/helpers/cloud.ts:403:  const summaryMd = data.summaryMd as string | null;
tests/integration/helpers/cloud.ts:404:  if (summaryMd && f.mdBody != null) {
tests/integration/helpers/cloud.ts:405:    await seedSummaryBlob(svc, ctx.userId, ctx.playlistKey, summaryMd.replace(/\.md$/, ''), f.mdBody);
tests/integration/helpers/cloud.ts:417:  await ctx.local.claimVideoSlot(lp, videoId);
tests/integration/helpers/cloud.ts:419:  await ctx.local.upsertVideo(lp, data as unknown as Video);
tests/integration/helpers/cloud.ts:420:  const summaryMd = data.summaryMd as string | null;
tests/integration/helpers/cloud.ts:421:  if (summaryMd && f.mdBody != null) {
tests/integration/helpers/cloud.ts:422:    await ctx.localBlob.put(lp, summaryMd, Buffer.from(f.mdBody, 'utf8'), 'text/markdown');
tests/integration/helpers/cloud.ts:427: *  delete scenarios). Writes to the SAME manifest path runSync + ctx.readManifest resolve. */
tests/integration/helpers/cloud.ts:434:  const idx = await new SupabaseMetadataStore(ctx.userClient).readIndex(ctx.cloudPrincipal);
tests/integration/helpers/cloud.ts:439:  const idx = await ctx.local.readIndex(ctx.localPrincipal);
tests/integration/helpers/seed.ts:18:/** Insert a video row MIRRORING the worker's promoted shape (summary-handler.ts:149-164 +
tests/integration/helpers/seed.ts:19: *  persist_summary 0009). Sets top-level owner_id (NOT NULL + composite FK) and a `data` jsonb
tests/integration/helpers/seed.ts:20: *  with the top-level `summaryMd`/`language`/`serialNumber` the route reads AND
tests/integration/helpers/seed.ts:21: *  `artifacts.summaryMd.{key,status}` the reserve RPC + route status-gate read. Defaults to
tests/integration/helpers/seed.ts:22: *  `status:'promoted'`; pass `status:'committed'` for the finalizing-window / unpromoted cases. */
tests/integration/helpers/seed.ts:26:          status?: 'promoted' | 'committed'; position?: number; title?: string;
tests/integration/helpers/seed.ts:31:  const status = opts.status ?? 'promoted';
tests/integration/helpers/seed.ts:41:      summaryMd: `${base}.md`,                    // top-level key the route get()s (summary-handler.ts:157)
tests/integration/helpers/seed.ts:43:      artifacts: { summaryMd: { key: `${base}.md`, status } },
tests/integration/helpers/seed.ts:44:      // Task 7 (cloud dig): enqueueDig reads load.video.durationSeconds (NULL trips enqueue_job's
supabase/migrations/0017_share_token_id_return.sql:6:-- grant to authenticated is re-applied below. Ownership/hash/TTL/promoted logic is unchanged.
supabase/migrations/0017_share_token_id_return.sql:14:  v_promoted boolean;
supabase/migrations/0017_share_token_id_return.sql:23:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0017_share_token_id_return.sql:24:    into v_promoted
supabase/migrations/0017_share_token_id_return.sql:27:  if v_promoted is distinct from true then
supabase/migrations/0017_share_token_id_return.sql:28:    raise exception 'create_share_token: denied';  -- not owned or not promoted → coarse 404
tests/integration/review-route-cloud.test.ts:7:// resolveOwnedPlaylistKey, metadataStore.updateVideoAnnotations → update_video_annotations
tests/integration/job-queue-runner.test.ts:4:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
tests/integration/job-queue-runner.test.ts:28:  // T13: SupabaseJobQueue.enqueue is dropped — enqueue via the service-role SupabaseEnqueuer.
tests/integration/job-queue-runner.test.ts:29:  const enqueuer = new SupabaseEnqueuer(adminClient());
tests/integration/job-queue-runner.test.ts:30:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { hi: 1, durationSeconds: 100 } as never);
tests/integration/job-queue-runner.test.ts:52:  const enqueuer = new SupabaseEnqueuer(adminClient());
tests/integration/job-queue-runner.test.ts:53:  const enq = await enqueuer.enqueue({ ownerId: userId, enqueueIp: null }, key(pl, vid), { durationSeconds: 100 } as never);
tests/api/pdf-serve-cloud.test.ts:3:const promotedSummaryMd = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;
tests/api/pdf-serve-cloud.test.ts:24:        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
tests/api/pdf-serve-cloud.test.ts:51:// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
tests/api/pdf-serve-cloud.test.ts:52:const promotedVideo = { id: validVideo, language: 'en', summaryMd: `${validVideo}.md`, artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } } };
tests/api/pdf-serve-cloud.test.ts:57:  mockIndexVideos = [promotedVideo];
tests/api/pdf-serve-cloud.test.ts:58:  mockMdBytes = Buffer.from(promotedSummaryMd, 'utf-8');
tests/api/pdf-serve-cloud.test.ts:117:  mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
tests/api/pdf-serve-cloud.test.ts:128:it('lost md blob (promoted but blob null) → 409', async () => {
lib/index-store.ts:13:// updateVideoAnnotations and updateVideoFields so both write paths stamp identically.
lib/index-store.ts:81:export function readIndex(outputFolder: string): PlaylistIndex {
lib/index-store.ts:116:export function upsertVideo(outputFolder: string, video: Video): void {
lib/index-store.ts:119:  const index = readIndex(outputFolder);
lib/index-store.ts:132:export function updateVideoFields(outputFolder: string, id: string, fields: Partial<Video>): void {
lib/index-store.ts:135:  const index = readIndex(outputFolder);
tests/api/html-doc-pipeline.test.ts:59:    overallScore: 4, summaryMd: 'ko-video.md',
tests/api/jobs-route.test.ts:11:jest.mock('@/lib/job-queue/producer', () => ({
tests/api/jobs-route.test.ts:12:  ...jest.requireActual('@/lib/job-queue/producer'),
tests/api/jobs-route.test.ts:13:  enqueuePlaylist: jest.fn(),
tests/api/jobs-route.test.ts:18:jest.mock('@/lib/job-queue/enqueuer', () => ({
tests/api/jobs-route.test.ts:25:import * as producer from '@/lib/job-queue/producer';
tests/api/jobs-route.test.ts:26:import { PlaylistTooLargeError, AllEnqueueFailedError } from '@/lib/job-queue/producer';
tests/api/jobs-route.test.ts:28:const enqueueMock = jest.mocked(producer.enqueuePlaylist);
tests/api/jobs-route.test.ts:38:  // exercising the pre-existing auth/body/producer-error-mapping behavior unchanged.
tests/api/jobs-route.test.ts:47:it('POST returns 200 with the producer result', async () => {
tests/api/jobs-route.test.ts:48:  const producerResult = {
tests/api/jobs-route.test.ts:50:    counts: { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
tests/api/jobs-route.test.ts:52:  enqueueMock.mockResolvedValueOnce(producerResult);
tests/api/jobs-route.test.ts:55:  expect(await res.json()).toEqual({ ...producerResult, challengeRequired: false });
tests/api/jobs-route.test.ts:68:it('POST maps producer errors: 422 / 503', async () => {
tests/api/jobs-route.test.ts:69:  enqueueMock.mockRejectedValueOnce(new PlaylistTooLargeError(50, 88));
tests/api/jobs-route.test.ts:74:  enqueueMock.mockRejectedValueOnce(new AllEnqueueFailedError('pl'));
tests/api/jobs-route.test.ts:89:  const { PlaylistFetchError } = await import('@/lib/job-queue/producer');
tests/api/jobs-route.test.ts:90:  enqueueMock.mockRejectedValueOnce(new PlaylistFetchError('quota exceeded'));
tests/api/dig-cloud-route.test.ts:16:jest.mock('@/lib/job-queue/enqueuer', () => ({ SupabaseEnqueuer: jest.fn(() => ({})) }));
tests/api/dig-cloud-route.test.ts:17:jest.mock('@/lib/dig/cloud/enqueue-dig-core', () => ({ enqueueDig: jest.fn() }));
tests/api/dig-cloud-route.test.ts:21:import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
tests/api/dig-cloud-route.test.ts:72:it('delegates to enqueueDig and serializes its result', async () => {
tests/api/dig-cloud-route.test.ts:74:  (enqueueDig as jest.Mock).mockResolvedValue({ status: 202, body: { status: 'enqueued', jobId: 'j', sectionId: 132 } });
tests/api/dig-cloud-route.test.ts:77:  expect(await res.json()).toEqual({ status: 'enqueued', jobId: 'j', sectionId: 132 });
tests/api/dig-cloud-route.test.ts:78:  expect(enqueueDig).toHaveBeenCalledWith(expect.objectContaining({
tests/api/dig-cloud-route.test.ts:83:it('delegates to enqueueDig with isAnonymous: true for an anonymous profile, and surfaces its 403', async () => {
tests/api/dig-cloud-route.test.ts:85:  (enqueueDig as jest.Mock).mockResolvedValue({ status: 403, body: { error: 'dig requires an account' } });
tests/api/dig-cloud-route.test.ts:88:  expect(enqueueDig).toHaveBeenCalledWith(expect.objectContaining({ isAnonymous: true }));
tests/api/dig-cloud-route.test.ts:99:  (enqueueDig as jest.Mock).mockResolvedValue({ status: 403, body: { error: 'dig requires an account' } });
tests/api/dig-cloud-route.test.ts:101:  expect(enqueueDig).toHaveBeenCalledWith(expect.objectContaining({ isAnonymous: true }));
tests/api/dig-cloud-route.test.ts:105:// Requirement carried from the Task 5 review: EVERY 429 from enqueueDig (rate-limited OR
tests/api/dig-cloud-route.test.ts:107:it('429 from enqueueDig carries Retry-After: 60', async () => {
tests/api/dig-cloud-route.test.ts:109:  (enqueueDig as jest.Mock).mockResolvedValue({ status: 429, body: { error: 'rate limited' } });
tests/api/videos.test.ts:7:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/videos.test.ts:21:    summaryMd: `${id}.md`,
lib/pipeline.ts:17:import { mdHash } from './cloud-sync/content-hash';
lib/pipeline.ts:42:  summaryMd: string;
lib/pipeline.ts:58:  return { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent: result.mdContent, summaryMd: `${baseName}.md` };
lib/pipeline.ts:104:  const summaryMd = file;
lib/pipeline.ts:120:    summaryMd,
lib/pipeline.ts:132:  const index = await store.readIndex(principal);
lib/pipeline.ts:153:        await store.upsertVideo(principal, video);
lib/pipeline.ts:204:  const alreadyIndexed = new Set((await store.readIndex(principal)).videos.map((v) => v.id));
lib/pipeline.ts:221:    // Tracks whether claimVideoSlot reserved a stub for this video in this run.
lib/pipeline.ts:222:    // Set to false again once upsertVideo commits the full record — after that point
lib/pipeline.ts:235:      const { serialNumber } = await store.claimVideoSlot(principal, meta.videoId);
lib/pipeline.ts:262:        // serialNumber from claimVideoSlot must be threaded through — upsertVideo does a
lib/pipeline.ts:265:        summaryMd: `${baseName}.md`,
lib/pipeline.ts:268:        // Stage 3 (§5.1): a first-generation MD reflects EMPTY corrections — mdHash('')
lib/pipeline.ts:270:        // mdHash(reconciledCorrections), which is mdHash('') when no corrections exist).
lib/pipeline.ts:272:        mdCorrectionsHash: mdHash(''),
lib/pipeline.ts:284:      await store.upsertVideo(principal, video);
lib/pipeline.ts:326:  const afterReconcile = await store.readIndex(principal);
tests/api/html-dig-serve.test.ts:9:// and tests/lib/dig/cloud/enqueue-dig-core.test.ts precedent. All assertions are identical to the brief;
tests/api/html-dig-serve.test.ts:74:it('propagates a loader 404 (e.g. video not found / not promoted) verbatim', async () => {
tests/api/html-dig-serve.test.ts:117:it('zero-dug promoted video: serves 200 interactive (all sections un-dug triggers), NOT 404', async () => {
tests/api/html-serve.test.ts:24:    overallScore: 4, summaryMd: 'a.md',
tests/api/html-serve.test.ts:166:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
tests/api/html-serve.test.ts:178:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
tests/api/html-serve.test.ts:188:  // summaryMd points to a file that does not exist on disk
tests/api/html-serve.test.ts:189:  writeIndex(video({ summaryMd: 'wiki/nonexistent.md', digDeeperMd: null }));
tests/api/html-serve.test.ts:199:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
tests/api/html-serve.test.ts:213:    summaryMd: 'wiki/video.md',
tests/api/html-serve.test.ts:244:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
tests/api/html-serve.test.ts:257:    summaryMd: summaryRel,
tests/api/html-serve.test.ts:269:  // The route now checks digDeeperPath containment BEFORE deriving summaryMdPath,
tests/api/html-serve.test.ts:271:  // summaryMd is safe; digDeeperMd escapes → companion assertWithin fires → 400.
tests/api/html-serve.test.ts:274:    summaryMd: summaryRel,                         // safe: wiki/video.md → stays inside dir
tests/api/html-serve.test.ts:303:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:314:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:328:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:343:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:353:    writeIndex(video({ summaryHtml: 'htmls/missing.html', summaryMd: 'wiki/a.md' }));
tests/api/review.test.ts:6:const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
tests/api/review.test.ts:54:  it('deletes personalScore when null is sent (passes undefined to updateVideoFields)', async () => {
tests/api/review.test.ts:60:  it('deletes personalNote when empty string is sent (passes undefined to updateVideoFields)', async () => {
tests/api/review.test.ts:130:  it('returns 500 when updateVideoFields throws a non-not-found error', async () => {
tests/integration/quickview-route-cloud.test.ts:7:// resolveOwnedPlaylistKey, metadataStore.readIndex) runs for real.
tests/integration/quickview-route-cloud.test.ts:81:      data: { id: videoId, serialNumber: 1, language: 'en', summaryMd: `${videoId}.md`, docVersion: 1,
tests/integration/quickview-route-cloud.test.ts:82:              artifacts: { summaryMd: { key: `${videoId}.md`, status: 'promoted' } }, tldr: 'x' },
tests/integration/quickview-route-cloud.test.ts:90:  it('owned video WITH summaryMd && tldr → { tldr, takeaways, tags }', async () => {
tests/integration/quickview-route-cloud.test.ts:96:        id: videoId, serialNumber: 1, language: 'en', summaryMd: `${videoId}.md`, docVersion: 1,
tests/integration/quickview-route-cloud.test.ts:97:        artifacts: { summaryMd: { key: `${videoId}.md`, status: 'promoted' } },
tests/integration/quickview-route-cloud.test.ts:114:  it('owned video missing summaryMd → 404 (availability gate)', async () => {
tests/integration/quickview-route-cloud.test.ts:119:      data: { id: videoId, serialNumber: 1, language: 'en', docVersion: 1, tldr: 'has tldr but no summaryMd' },
tests/integration/quickview-route-cloud.test.ts:132:    // seedPromotedVideo's default data has summaryMd but no tldr.
tests/api/quick-view.test.ts:6:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/quick-view.test.ts:47:  it('returns 404 when video has no summaryMd', async () => {
tests/api/quick-view.test.ts:50:      videos: [{ id: VIDEO_ID, summaryMd: null, tldr: undefined } as any],
tests/api/quick-view.test.ts:56:  it('returns 404 when video has summaryMd but no tldr', async () => {
tests/api/quick-view.test.ts:59:      videos: [{ id: VIDEO_ID, summaryMd: 'test.md', tldr: undefined } as any],
tests/api/quick-view.test.ts:70:        summaryMd: 'test.md',
tests/api/quick-view.test.ts:89:      videos: [{ id: VIDEO_ID, summaryMd: 'test.md', tldr: 'This video explains X.' } as any],
tests/api/dig-state-cloud.test.ts:56:it('propagates the summary gate: 404 not-owner / unpromoted / unknown video', async () => {
supabase/migrations/0005_reorder_helper.sql:13:       and (owner_id = auth.uid() or auth.role() = 'service_role')
supabase/migrations/0005_reorder_helper.sql:24:-- Codex H7: not callable by anon/PUBLIC by default; only authenticated + service_role.
supabase/migrations/0005_reorder_helper.sql:26:grant execute on function reorder_videos(uuid, jsonb) to authenticated, service_role;
tests/api/backfill.test.ts:28:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/backfill.test.ts:30:const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
tests/api/backfill.test.ts:41:  summaryMd: 'test.md',
tests/api/dig-post.test.ts:70:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/api/dig-post.test.ts:71:const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
tests/api/dig-post.test.ts:98:  summaryMd: 'test-video.md',
tests/api/dig-post.test.ts:222:  it('calls readIndex with outputFolder', async () => {
tests/api/dig-post.test.ts:306:  it('calls updateVideoFields with digDeeperMd only (no digDeeperHtml stamp)', async () => {
tests/api/share-mint-route.test.ts:61:  it('404 (coarse) when the RPC raises (unowned/unpromoted/bounds)', async () => {
lib/dig/dig-section.ts:23:  const index = await store.readIndex(principal);
lib/dig/dig-section.ts:31:  const summaryMdName = video.summaryMd ?? `${videoId}.md`;
lib/dig/dig-section.ts:32:  const summaryMdPath = path.join(outputFolder, summaryMdName);
lib/dig/dig-section.ts:33:  const mdContent = await fs.readFile(summaryMdPath, 'utf8');
lib/dig/dig-section.ts:83:  const summaryBasename = path.basename(summaryMdName, '.md');
lib/dig/dig-section.ts:105:  await store.updateVideoFields(principal, videoId, {
tests/api/serve-summary-core.test.ts:3:const promotedSummaryMd = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;
tests/api/serve-summary-core.test.ts:21:        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
tests/api/serve-summary-core.test.ts:37:// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
tests/api/serve-summary-core.test.ts:38:const promotedVideo = {
tests/api/serve-summary-core.test.ts:39:  id: validVideo, language: 'en', summaryMd: `${validVideo}.md`,
tests/api/serve-summary-core.test.ts:40:  artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } },
tests/api/serve-summary-core.test.ts:44:  mockIndexVideos = [promotedVideo];
tests/api/serve-summary-core.test.ts:45:  mockMdBytes = Buffer.from(promotedSummaryMd, 'utf-8');
tests/api/serve-summary-core.test.ts:54:    mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
tests/api/serve-summary-core.test.ts:73:      ...promotedVideo,
tests/api/serve-summary-core.test.ts:74:      artifacts: { summaryMd: { key: 'nested/foo.md', status: 'promoted' } },
tests/api/serve-summary-core.test.ts:81:  it('promoted but blob missing → 409 repair needed', async () => {
tests/api/serve-summary-core.test.ts:87:  it('promoted → ok WITHOUT resolving the model', async () => {
tests/api/serve-summary-core.test.ts:92:      expect(r.mdBytes.toString('utf-8')).toBe(promotedSummaryMd);
tests/api/html-serve-cloud.test.ts:3:const promotedSummaryMd = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;
tests/api/html-serve-cloud.test.ts:26:        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
tests/api/html-serve-cloud.test.ts:48:// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
tests/api/html-serve-cloud.test.ts:49:const promotedVideo = { id: validVideo, language: 'en', summaryMd: `${validVideo}.md`, artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } } };
tests/api/html-serve-cloud.test.ts:54:  mockIndexVideos = [promotedVideo];
tests/api/html-serve-cloud.test.ts:55:  mockMdBytes = Buffer.from(promotedSummaryMd, 'utf-8');
tests/api/html-serve-cloud.test.ts:93:  mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
tests/api/html-serve-cloud.test.ts:97:  mockIndexVideos = [{ id: validVideo, language: 'en', summaryMd: null }];
tests/api/html-serve-cloud.test.ts:100:it('B13b: promoted but MD blob null → repair-needed 409', async () => {
tests/api/html-serve-cloud.test.ts:125:it('money coherence: base is derived from the promoted MD key, not videoId, while videoId is passed through unchanged', async () => {
tests/api/html-serve-cloud.test.ts:133:    summaryMd: '0001_intro.md',
tests/api/html-serve-cloud.test.ts:134:    artifacts: { summaryMd: { key: '0001_intro.md', status: 'promoted' } },
lib/serial-migrate-exec.ts:11:  const index = await store.readIndex(principal);
lib/serial-migrate-exec.ts:71:  const index = await store.readIndex(principal);
lib/serial-migrate-exec.ts:126:      if (op.field === 'summaryMd') mdNewName = path.basename(op.to);
lib/serial-migrate-exec.ts:146:    if (Object.keys(fieldUpdates).length > 0) await store.updateVideoFields(principal, plan.id, fieldUpdates);
lib/archive.ts:16:  const index = await store.readIndex(principal);
lib/archive.ts:23:  for (const relPath of [video.summaryMd]) {
lib/archive.ts:66:  const index = await store.readIndex(principal);
lib/archive.ts:71:  for (const md of [video.summaryMd]) {
lib/archive.ts:86:    await store.updateVideoFields(principal, videoId, fields);
tests/scripts/backfill-serial-prefix.test.ts:9:function makeVideo(id: string, processedAt: string, summaryMd: string | null) {
tests/scripts/backfill-serial-prefix.test.ts:19:    summaryMd,
tests/scripts/backfill-serial-prefix.test.ts:38:    // Seed temp index with one video whose summaryMd is set and NO serialNumber
lib/dig/generate.ts:125:   *  the local dig-section path, which never reserves/releases a spend_ledger entry. */
lib/cloud-sync/registry.ts:26:      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
lib/job-queue/video-meta-to-payload.ts:10:// parseIngestionPayload's z.string().datetime() reject it and throw, 500-ing the whole producer
lib/cloud-sync/sync-run.ts:4:// T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:13://  - Transfers finalize the receiver record via updateVideoFields (SyncDeps exposes no raw client,
lib/cloud-sync/sync-run.ts:14://    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
lib/cloud-sync/sync-run.ts:26:import { deriveClassASignals, deriveHumanSnapshot } from './backfill';
lib/cloud-sync/sync-run.ts:29:import { decideCompanion } from './companion';
lib/cloud-sync/sync-run.ts:34:import { mdHash } from './content-hash';
lib/cloud-sync/sync-run.ts:58:/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
lib/cloud-sync/sync-run.ts:60:  if (!video.summaryMd) return null;
lib/cloud-sync/sync-run.ts:61:  const buf = await blob.get(p, video.summaryMd);
lib/cloud-sync/sync-run.ts:69:  const [l, c] = await Promise.all([local.readIndex(localP), cloud.readIndex(cloudP)]);
lib/cloud-sync/sync-run.ts:75:  const idx = await store.readIndex(p);
lib/cloud-sync/sync-run.ts:85: *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
lib/cloud-sync/sync-run.ts:106: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
lib/cloud-sync/sync-run.ts:107:function sanitizeAdditiveVideo(video: Video): Video {
lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
lib/cloud-sync/sync-run.ts:127: *  upsertVideo/updateVideoFields are bare UPDATEs of a row pre-created by claimVideoSlot: they
lib/cloud-sync/sync-run.ts:130: *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
lib/cloud-sync/sync-run.ts:131:async function ensureReceiverSlot(
lib/cloud-sync/sync-run.ts:136:  const idx = await to.readIndex(toP);
lib/cloud-sync/sync-run.ts:138:  return to.claimVideoSlot(toP, video.id);
lib/cloud-sync/sync-run.ts:142: *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
lib/cloud-sync/sync-run.ts:143: *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
lib/cloud-sync/sync-run.ts:145:async function copyAdditiveVideo(
lib/cloud-sync/sync-run.ts:150:  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
lib/cloud-sync/sync-run.ts:153:  if (video.summaryMd && mdBody != null) {
lib/cloud-sync/sync-run.ts:154:    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
lib/cloud-sync/sync-run.ts:155:    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
lib/cloud-sync/sync-run.ts:157:    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
lib/cloud-sync/sync-run.ts:164:  const sanitized: any = sanitizeAdditiveVideo(video);
lib/cloud-sync/sync-run.ts:170:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
lib/cloud-sync/sync-run.ts:172:  await to.upsertVideo(toP, sanitized as Video);
lib/cloud-sync/sync-run.ts:176:  const after = await to.readIndex(toP);
lib/cloud-sync/sync-run.ts:185:  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
lib/cloud-sync/sync-run.ts:194:      mdHash: mdHashVal,
lib/cloud-sync/sync-run.ts:203: *  write on an absent row would let buildBaseline record a false agreement. */
lib/cloud-sync/sync-run.ts:204:async function applyClassBWinners(args: {
lib/cloud-sync/sync-run.ts:244: *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
lib/cloud-sync/sync-run.ts:245: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
lib/cloud-sync/sync-run.ts:247:async function transferClassA(
lib/cloud-sync/sync-run.ts:249:): Promise<{ mdHash: string; verified: boolean }> {
lib/cloud-sync/sync-run.ts:251:  if (body == null || !winnerVideo.summaryMd) {
lib/cloud-sync/sync-run.ts:252:    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
lib/cloud-sync/sync-run.ts:254:  const h = mdHash(body);
lib/cloud-sync/sync-run.ts:255:  const key = winnerVideo.summaryMd;
lib/cloud-sync/sync-run.ts:259:  if (!staged || mdHash(staged.toString('utf8')) !== h) {
lib/cloud-sync/sync-run.ts:260:    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
lib/cloud-sync/sync-run.ts:268:  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
lib/cloud-sync/sync-run.ts:269:  // (below) advertises promoted only after this resolves.
lib/cloud-sync/sync-run.ts:275:    summaryMd: key,
lib/cloud-sync/sync-run.ts:286:    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
lib/cloud-sync/sync-run.ts:287:    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
lib/cloud-sync/sync-run.ts:288:    artifacts: { summaryMd: { key, status: 'promoted' } },
lib/cloud-sync/sync-run.ts:290:  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
lib/cloud-sync/sync-run.ts:292:  return { mdHash: h, verified: true };
lib/cloud-sync/sync-run.ts:301:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:302:  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
lib/cloud-sync/sync-run.ts:304:  const decision = decideCompanion({ winnerMdHash, senderEnvelope });
lib/cloud-sync/sync-run.ts:315: *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
lib/cloud-sync/sync-run.ts:319:function buildBaseline(
lib/cloud-sync/sync-run.ts:337:      mdHash: winnerMdHash,
lib/cloud-sync/sync-run.ts:343:export async function runSync(
lib/cloud-sync/sync-run.ts:378:        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
lib/cloud-sync/sync-run.ts:388:            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
lib/cloud-sync/sync-run.ts:391:              deriveClassASignals(present, body), body ? mdHash(body) : null,
lib/cloud-sync/sync-run.ts:392:              deriveHumanSnapshot(present),
lib/cloud-sync/sync-run.ts:399:        const localSnap = deriveHumanSnapshot(lv);
lib/cloud-sync/sync-run.ts:400:        const cloudSnap = deriveHumanSnapshot(cv);
lib/cloud-sync/sync-run.ts:402:        const applied = await applyClassBWinners({
lib/cloud-sync/sync-run.ts:407:        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
lib/cloud-sync/sync-run.ts:410:        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
lib/cloud-sync/sync-run.ts:411:        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
lib/cloud-sync/sync-run.ts:412:        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
lib/cloud-sync/sync-run.ts:423:          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
lib/cloud-sync/sync-run.ts:427:          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
lib/cloud-sync/sync-run.ts:431:          winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
lib/cloud-sync/sync-run.ts:442:        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
lib/cloud-sync/companion.ts:8:export function decideCompanion(args: {
lib/cloud-sync/companion.ts:13:  if (senderEnvelope && senderEnvelope.sourceMdHash === winnerMdHash) {
lib/playlists/backfill-titles.ts:32:    try { index = await store.readIndex(p); } catch { failed.push(folder); continue; }
lib/cloud-sync/backfill.ts:3:import { mdHash } from './content-hash';
lib/cloud-sync/backfill.ts:5:// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
lib/cloud-sync/backfill.ts:6:// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
lib/cloud-sync/backfill.ts:7:export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
lib/cloud-sync/backfill.ts:10:    summaryMdKey: video.summaryMd ?? null,
lib/cloud-sync/backfill.ts:11:    mdHash: mdBody != null ? mdHash(mdBody) : null,
lib/cloud-sync/backfill.ts:21:export function deriveHumanSnapshot(video: Video): HumanSnapshot {
lib/job-queue/enqueuer.ts:6:/** Owner/IP context threaded through the service-role enqueue path so
lib/job-queue/enqueuer.ts:7: * `enqueue_job` can enforce per-owner quota/cap without a session client. */
lib/job-queue/enqueuer.ts:10:  enqueueIp: string | null;
lib/job-queue/enqueuer.ts:13:/** Result of `enqueue_preflight` — an advisory gate checked before fan-out. */
lib/job-queue/enqueuer.ts:21:/** Guardrail config values the producer/handler need to read (subset). */
lib/job-queue/enqueuer.ts:26:export interface DigJobPayload { durationSeconds: number; } // enqueue_job reads only durationSeconds (PJ003 backstop)
lib/job-queue/enqueuer.ts:29: * Service-role enqueue/preflight surface. Deliberately has NO read/list/status
lib/job-queue/enqueuer.ts:31: * enqueue+preflight) forbids a tenant-read path from ever running under
lib/job-queue/enqueuer.ts:35:  enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload | DigJobPayload): Promise<EnqueueResult>;
lib/job-queue/enqueuer.ts:41: * Service-role `Enqueuer`: wires `enqueue_job`/`enqueue_preflight` (both service-role-only
lib/job-queue/enqueuer.ts:49:  async enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload | DigJobPayload): Promise<EnqueueResult> {
lib/job-queue/enqueuer.ts:50:    const { data, error } = await this.serviceClient.rpc('enqueue_job', {
lib/job-queue/enqueuer.ts:52:      p_job_kind: key.kind, p_job_version: key.version, p_payload: payload, p_enqueue_ip: ctx.enqueueIp,
lib/job-queue/enqueuer.ts:60:    const { data, error } = await this.serviceClient.rpc('enqueue_preflight', { p_ip: ip, p_owner_id: ownerId });
lib/job-queue/summary-handler.ts:39:/** Live guardrail duration cap — the value the producer pre-block and enqueue_job PJ003 also read. */
lib/job-queue/summary-handler.ts:63:    // Defense-in-depth behind enqueue_job's PJ003 guardrail: re-read the LIVE duration cap and
lib/job-queue/summary-handler.ts:65:    // last of the three coupled sites: producer pre-block, PJ003, this handler guard).
lib/job-queue/summary-handler.ts:82:    // is already promoted at the current doc version. `artifacts` lives on the DB `data`
lib/job-queue/summary-handler.ts:85:    const existingArtifacts = (existing as unknown as { artifacts?: { summaryMd?: { status?: string } } } | null)?.artifacts;
lib/job-queue/summary-handler.ts:87:      existingArtifacts?.summaryMd?.status === 'promoted' &&
lib/job-queue/summary-handler.ts:130:          // GUARDED: delete ONLY a row that is still the bare reservation (`data.summaryMd is null`), so a
lib/job-queue/summary-handler.ts:131:          // concurrent worker that reclaimed this job and already wrote/promoted a summary is never deleted.
lib/job-queue/summary-handler.ts:134:            .is('data->>summaryMd', null);
lib/job-queue/summary-handler.ts:157:      summaryMd: `${baseName}.md`,
lib/job-queue/summary-handler.ts:167:    // don't start the irreversible blob/persist sequence. (Full lease-fencing of persist_summary is
lib/job-queue/summary-handler.ts:179:    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, video, 'promoted');
lib/cloud-sync/reconcile-class-a.ts:14:  reconciledCorrectionsHash: string;
lib/cloud-sync/reconcile-class-a.ts:16:  const { local, cloud, reconciledCorrectionsHash: cur } = args;
lib/cloud-sync/reconcile-class-a.ts:17:  const lHas = local.mdHash != null;
lib/cloud-sync/reconcile-class-a.ts:18:  const cHas = cloud.mdHash != null;
lib/cloud-sync/reconcile-class-a.ts:32:  if (local.mdHash === cloud.mdHash) {
lib/cloud-sync/reconcile-class-a.ts:48:  // same major, different mdHash → recency-tiebreak (unify prose)
lib/html-doc/model-store.ts:22:    sourceMdHash: z.string().optional(),
lib/html-doc/model-store.ts:24:  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
lib/cloud-sync/types.ts:5:  summaryMdKey: string | null;    // the blob KEY (video.summaryMd) — NOT the body
lib/cloud-sync/types.ts:6:  mdHash: string | null;          // SHA-256 of the MD BODY (read from the blob by the caller); null when no MD
lib/cloud-sync/types.ts:32:  classA: { docVersionMajor: number; mdGeneratedAt: string | null; mdCorrectionsHash: string | null; mdHash: string | null };
lib/cloud-sync/content-hash.ts:16:export function mdHash(md: string): string {
lib/job-queue/dig-handler.ts:53:    // SAME summary-key rule as the trigger's loadSummaryForServe (artifacts.summaryMd.key ??
lib/job-queue/dig-handler.ts:54:    // summaryMd, validated) — guarantees the handler writes the exact base the trigger deduped on.
lib/job-queue/errors.ts:31: * guardrail error. PJ001/PJ002/PJ003 are the enqueue_job guardrail codes
lib/dig/cloud/resolve-summary-key.ts:3:/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
lib/dig/cloud/resolve-summary-key.ts:4: *  falling back to the top-level `summaryMd` — validated via `assertCloudSummaryMdKey`. Returns
lib/dig/cloud/resolve-summary-key.ts:7: *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
lib/dig/cloud/resolve-summary-key.ts:9: *  top-level `summaryMd` fallback for videos with no artifact record. The dig TRIGGER owns that
lib/dig/cloud/resolve-summary-key.ts:10: *  gate: it enqueues a dig job only when `loadSummaryForServe` reports the summary promoted, so by
lib/dig/cloud/resolve-summary-key.ts:11: *  the time this worker runs, the summary is already promoted. */
lib/dig/cloud/resolve-summary-key.ts:13:  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
lib/dig/cloud/resolve-summary-key.ts:14:  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
lib/job-queue/producer.ts:8:import type { Enqueuer, EnqueueCtx } from '@/lib/job-queue/enqueuer';
lib/job-queue/producer.ts:18:  constructor(public playlistId: string) { super('all enqueue attempts failed'); }
lib/job-queue/producer.ts:33:  enqueued: number; joined: number; skipped: number; failed: number;
lib/job-queue/producer.ts:41:export async function enqueuePlaylist(
lib/job-queue/producer.ts:42:  sessionBundle: StorageBundle, enqueuer: Enqueuer, principal: Principal, playlistUrl: string, ctx: EnqueueCtx,
lib/job-queue/producer.ts:57:  // enqueueable item with its ORIGINAL VideoMeta by POSITION here, while that alignment is
lib/job-queue/producer.ts:62:  const enqueueable: { vm: VideoMeta; videoId: string; ok: any }[] = [];
lib/job-queue/producer.ts:65:    if ('ok' in m) enqueueable.push({ vm: videos[i], videoId: m.videoId, ok: m.ok });
lib/job-queue/producer.ts:69:  if (enqueueable.length === 0) {
lib/job-queue/producer.ts:72:      counts: { enqueued: 0, joined: 0, skipped: skips.length, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
lib/job-queue/producer.ts:76:  const { maxDurationSeconds } = await enqueuer.getGuardrailConfig();
lib/job-queue/producer.ts:80:  for (const item of enqueueable) {
lib/job-queue/producer.ts:107:      const { jobId, status, joined: didJoin } = await enqueuer.enqueue(
lib/job-queue/producer.ts:129:        // PJ003 backstop firing inside the RPC (duration passed the producer's own check,
lib/job-queue/producer.ts:137:      console.error(`enqueuePlaylist: enqueue failed for video ${videoId}`, e);
lib/job-queue/producer.ts:138:      results.push({ videoId, error: 'enqueue failed' });
lib/job-queue/producer.ts:144:    enqueued: created, joined, skipped: skips.length, failed,
lib/job-queue/producer.ts:150:  // behavior, not a failure to surface as a 503), including MIXED cases where nothing enqueued
tests/lib/pipeline-async.test.ts:37:    const idx = await store.readIndex(principal);
tests/lib/pipeline-async.test.ts:42:    const pendingPromise = store.readIndex(principal);
lib/paths/assert-within.ts:10: * Use this before every read of an index-supplied relative path (summaryMd, digDeeperMd,
lib/timestamp-repair.ts:17:// batch (and in unit tests, where ensure* is mocked, readIndex on a synthetic folder will throw).
lib/timestamp-repair.ts:22:    const v = (await store.readIndex(principal)).videos.find((x) => x.id === id);
lib/timestamp-repair.ts:23:    const rel = v?.summaryMd;
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
lib/dig/cloud/enqueue-dig-core.ts:56:    // blob: a concurrent worker may have just promoted it (→ ready), else the blob was lost (→ repair).
lib/dig/cloud/enqueue-dig-core.ts:63:    return { status: 202, body: { status: 'enqueued', jobId: res.jobId, sectionId: deps.sectionId } };
lib/serial-assign.ts:10:    .filter((v) => v.summaryMd != null && v.serialNumber == null)
lib/pdf/pdf-path.ts:10: * - summary:    `pdfs/{basename(summaryMd) sans .md}.pdf`
lib/pdf/pdf-path.ts:25:    if (!video.summaryMd) throw new Error('no summary for this video');
lib/pdf/pdf-path.ts:26:    base = path.basename(video.summaryMd).replace(/\.md$/, '');
lib/html-doc/generate.ts:7:import { mdHash } from '@/lib/cloud-sync/content-hash';
lib/html-doc/generate.ts:22:  const index = await store.readIndex(principal);
lib/html-doc/generate.ts:25:  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');
lib/html-doc/generate.ts:30:  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
lib/html-doc/generate.ts:32:    throw new Error(`source note not found on disk: ${video.summaryMd}`);
lib/html-doc/generate.ts:37:  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field
lib/html-doc/generate.ts:49:  const base = video.summaryMd.replace(/\.md$/, '');
lib/html-doc/generate.ts:51:    sourceMd: video.summaryMd,
lib/html-doc/generate.ts:56:    // Stage 3 (§4.2): hash the MD BODY (`md`, line ~33), NOT `sourceMd`/`video.summaryMd`
lib/html-doc/generate.ts:57:    // (the blob key/filename) — decideCompanion (Task 8) compares against mdHash(body); a
lib/html-doc/generate.ts:59:    sourceMdHash: mdHash(md),
lib/html-doc/generate.ts:72:    await store.updateVideoFields(principal, videoId, { summaryHtml: htmlFilename });
lib/html-doc/eligibility.ts:7:  return !!v.summaryMd;
lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
lib/html-doc/eligibility.ts:19: *   A video with no summaryMd is never eligible (nothing to generate from).
lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
lib/html-doc/batch.ts:21:  if (!video.summaryMd) return [];
lib/html-doc/batch.ts:24:    const md = await fs.readFile(path.join(outputFolder, video.summaryMd), 'utf8');
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
lib/html-doc/batch.ts:57:  const index = await store.readIndex(principal);
lib/html-doc/nav.ts:531:  try { data = (await resp.json()) as { status?: string }; } catch { /* treat as enqueued */ }
lib/html-doc/ensure.ts:30:  const video = (await store.readIndex(principal)).videos.find((v) => v.id === videoId);
lib/html-doc/ensure.ts:32:  if (!video.summaryMd) throw new Error('no summary note for this video');
lib/html-doc/ensure.ts:35:  const base = video.summaryMd.replace(/\.md$/, '');
lib/html-doc/ensure.ts:47:    await store.updateVideoFields(principal, videoId, {
lib/html-doc/ensure.ts:66:  await store.updateVideoFields(principal, videoId, { docVersion: current });
lib/html-doc/serve-summary-core.ts:43:  const index = await bundle.metadataStore.readIndex(principal);
lib/html-doc/serve-summary-core.ts:47:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
lib/html-doc/serve-summary-core.ts:48:    .artifacts?.summaryMd;
lib/html-doc/serve-summary-core.ts:51:  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)
lib/html-doc/serve-summary-core.ts:53:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
lib/html-doc/serve-summary-core.ts:54:  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
lib/html-doc/serve-summary-core.ts:56:  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
lib/html-doc/serve-summary-core.ts:67:  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)
lib/html-doc/serve-summary-core.ts:70:  // derived deterministically from the SAME summaryMd key the model store is keyed on.
lib/html-doc/serve-summary-core.ts:114:    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
lib/html-doc/serve-doc.ts:7:import { mdHash } from '@/lib/cloud-sync/content-hash';
lib/html-doc/serve-doc.ts:47:   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
lib/html-doc/serve-doc.ts:48:   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
lib/html-doc/serve-doc.ts:110:      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
lib/dig/cloud/load-dig-for-serve.ts:51:  // promoted-status gate already ran in loadSummaryForServe above, so serving the merged doc with an
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
lib/supabase/service.ts:5:/** service_role client with BYPASSRLS. Server-only; never import from client/route code
tests/lib/job-queue/dig-handler.test.ts:54:  // artifacts.summaryMd.key is the authoritative key (top-level summaryMd is a fallback) — the handler
tests/lib/job-queue/dig-handler.test.ts:56:  (readVideo as jest.Mock).mockResolvedValue({ id: 'vid1', title: 'Vid One', youtubeUrl: 'https://youtu.be/vid1', language: 'en', durationSeconds: 600, summaryMd: '0007_intro.md', artifacts: { summaryMd: { key: '0007_intro.md', status: 'promoted' } } });
tests/lib/job-queue/dig-handler.test.ts:187:    (freshReadVideo as jest.Mock).mockResolvedValue({ id: 'vid1', title: 'Vid One', youtubeUrl: 'https://youtu.be/vid1', language: 'en', durationSeconds: 600, summaryMd: '0007_intro.md', artifacts: { summaryMd: { key: '0007_intro.md', status: 'promoted' } } });
lib/dig/cloud/dig-blob-key.ts:5: *  distinct jobs_idem_active slot (which includes job_version), permitting a legit re-enqueue. */
tests/lib/format-ingest-summary.test.ts:2:const base = { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 };
tests/lib/format-ingest-summary.test.ts:5:  it('base case — only enqueued', () => {
tests/lib/format-ingest-summary.test.ts:6:    expect(formatIngestSummary({ ...base, enqueued: 42 })).toEqual({ line: 'Queued 42', challengeLine: null });
tests/lib/format-ingest-summary.test.ts:9:    expect(formatIngestSummary({ enqueued: 42, joined: 1, skipped: 3, tooLong: 2, quotaBlocked: 4, capBlocked: 5, failed: 6 }).line).toBe(
tests/lib/format-ingest-summary.test.ts:13:    expect(formatIngestSummary({ ...base, enqueued: 5, skipped: 2 }).line).toBe('Queued 5 · 2 skipped (no captions)');
tests/lib/format-ingest-summary.test.ts:16:    expect(formatIngestSummary({ ...base, enqueued: 1 }, true).line).toBe('Queued 1 · 0 blocked (daily cap reached)');
tests/lib/format-ingest-summary.test.ts:19:    const line = formatIngestSummary({ ...base, enqueued: 1, capBlocked: 3 }, true).line;
tests/lib/format-ingest-summary.test.ts:27:    expect(formatIngestSummary({ ...base, enqueued: 1 }, false, true).challengeLine).toBe("You're adding playlists quickly.");
tests/lib/job-queue/producer-title.test.ts:7:import { enqueuePlaylist } from '@/lib/job-queue/producer';
tests/lib/job-queue/producer-title.test.ts:9:import type { Enqueuer, EnqueueCtx, PreflightVerdict, GuardrailConfigView } from '@/lib/job-queue/enqueuer';
tests/lib/job-queue/producer-title.test.ts:15:const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: null };
tests/lib/job-queue/producer-title.test.ts:21:/** Fake bundle+enqueuer, mirroring tests/lib/producer.test.ts's fakeEnqueuer, plus a
tests/lib/job-queue/producer-title.test.ts:23:function fakeEnqueuer(enqueueImpl: Enqueuer['enqueue']) {
tests/lib/job-queue/producer-title.test.ts:27:  const enqueue = jest.fn(enqueueImpl);
tests/lib/job-queue/producer-title.test.ts:28:  const enqueuer: Enqueuer = {
tests/lib/job-queue/producer-title.test.ts:29:    enqueue,
tests/lib/job-queue/producer-title.test.ts:35:  return { bundle, enqueuer, resolvePlaylistId, setPlaylistMeta, enqueue, order };
tests/lib/job-queue/producer-title.test.ts:43:  const { bundle, enqueuer, setPlaylistMeta, order } = fakeEnqueuer(async () => {
tests/lib/job-queue/producer-title.test.ts:44:    order.push('enqueue');
tests/lib/job-queue/producer-title.test.ts:48:  await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/job-queue/producer-title.test.ts:59:  const { bundle, enqueuer, setPlaylistMeta } = fakeEnqueuer(async () =>
tests/lib/job-queue/producer-title.test.ts:62:  await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/job-queue/producer-title.test.ts:70:  const { bundle, enqueuer, setPlaylistMeta } = fakeEnqueuer(async () =>
tests/lib/job-queue/producer-title.test.ts:73:  const result = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/job-queue/producer-title.test.ts:76:  expect(result.counts.enqueued).toBe(1);
tests/lib/job-queue/producer-title.test.ts:82:  const { bundle, enqueuer, resolvePlaylistId, setPlaylistMeta } = fakeEnqueuer(async () =>
tests/lib/job-queue/producer-title.test.ts:85:  const result = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/serial-assign.test.ts:7:  overallScore: 3, summaryMd: 's.md',
tests/lib/serial-assign.test.ts:25:      v({ id: 'nofile', summaryMd: null }),        // no file → excluded
lib/supabase/env.ts:16:  return required('SUPABASE_SERVICE_ROLE_KEY');
tests/lib/serial-invariant.test.ts:16:    summaryMd: null,
tests/lib/serial-invariant.test.ts:27:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md' });
tests/lib/serial-invariant.test.ts:32:    const v = makeVideo({ serialNumber: 7, summaryMd: 'x.md' });
tests/lib/serial-invariant.test.ts:34:      { id: 'vid', serial: 7, field: 'summaryMd', value: 'x.md', expected: '007_x.md', reason: 'prefix' },
tests/lib/serial-invariant.test.ts:39:    const v = makeVideo({ serialNumber: 7, summaryMd: '002_x.md' });
tests/lib/serial-invariant.test.ts:42:    expect(out[0]).toMatchObject({ field: 'summaryMd', reason: 'prefix', expected: '007_x.md' });
tests/lib/serial-invariant.test.ts:46:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md' });
tests/lib/serial-invariant.test.ts:48:      { id: 'vid', serial: 7, field: 'summaryMd', value: '007_x.md', expected: '007_x.md', reason: 'missing' },
tests/lib/serial-invariant.test.ts:53:    const v = makeVideo({ serialNumber: undefined, summaryMd: 'x.md' });
tests/lib/serial-invariant.test.ts:58:    const v = makeVideo({ serialNumber: 7, summaryMd: null, summaryHtml: null });
tests/lib/serial-invariant.test.ts:70:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md', digDeeperMd: 'x-dig-deeper.md' });
tests/lib/serial-invariant.test.ts:77:    const v = makeVideo({ serialNumber: 7, summaryMd: 'x.md' });
tests/lib/serial-invariant.test.ts:84:    const clean = makeVideo({ id: 'a', serialNumber: 1, summaryMd: '001_a.md' });
tests/lib/serial-invariant.test.ts:85:    const dirty = makeVideo({ id: 'b', serialNumber: 2, summaryMd: 'b.md' });
tests/lib/serial-invariant.test.ts:88:    expect(out[0]).toMatchObject({ id: 'b', field: 'summaryMd', reason: 'prefix' });
tests/lib/serial-invariant.test.ts:91:  it('checks every nullable path field, not just summaryMd', () => {
tests/lib/serial-invariant.test.ts:107:      summaryMd: 'a.md',
tests/lib/serial-invariant.test.ts:121:    const v = makeVideo({ serialNumber: 0, summaryMd: 'x.md' });
tests/lib/serial-invariant.test.ts:124:      { id: 'vid', serial: 0, field: 'summaryMd', value: 'x.md', expected: '000_x.md', reason: 'prefix' },
tests/lib/types.test.ts:8:    overallScore: 3, summaryMd: 'a.md',
tests/lib/types.test.ts:29:    overallScore: 3, summaryMd: 'a.md',
tests/lib/pipeline.test.ts:25:const mockUpsertVideo = jest.mocked(indexStore.upsertVideo);
tests/lib/pipeline.test.ts:26:const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
tests/lib/pipeline.test.ts:28:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/lib/pipeline.test.ts:71:    summaryMd: `001_video-${id}.md`,
tests/lib/pipeline.test.ts:131:    // claimVideoSlot runs before writeSummaryDoc (transcript fetch); vid1 gets a slot stub
tests/lib/pipeline.test.ts:139:    // RED → GREEN: claimVideoSlot writes a stub; if writeSummaryDoc throws, deleteVideo must remove it
tests/lib/pipeline.test.ts:172:    // claimVideoSlot stub + full upsert = 2 calls per video → 4 total
tests/lib/pipeline.test.ts:243:      expect.objectContaining({ serialNumber: 1, summaryMd: '001_hello-world.md' }),
tests/lib/pipeline.test.ts:261:      expect.objectContaining({ serialNumber: 42, summaryMd: '042_hello-world.md' }),
tests/lib/pipeline.test.ts:276:        summaryMd: '001_hello-world.md',
tests/lib/pipeline.test.ts:282:    // Arrange: stateful in-memory store so the second readIndex call sees the first upserted video.
tests/lib/pipeline.test.ts:308:      expect.objectContaining({ id: 'vid1', serialNumber: 1, summaryMd: '001_alpha-video.md' }),
tests/lib/pipeline.test.ts:312:      expect.objectContaining({ id: 'vid2', serialNumber: 2, summaryMd: '002_beta-video.md' }),
tests/lib/pipeline.test.ts:330:        summaryMd: '001_hello-world-2.md',
tests/lib/pipeline.test.ts:405:    // archive/unarchive now goes through reconcilePlaylistMembership → indexStore.updateVideoFields
tests/lib/pipeline.test.ts:438:    // Returning to the playlist: reconcile calls updateVideoFields (not upsertVideo)
tests/lib/pipeline.test.ts:477:    // Already-indexed: upsertVideo not called; playlistIndex stamped via bulkUpdateVideoFields
tests/lib/pipeline.test.ts:518:    // claimVideoSlot stub + full upsert = 2 calls for vid1; second occurrence skipped entirely
tests/lib/pipeline.test.ts:614:    // vid2 must not have been processed; vid1 got claimVideoSlot stub + full upsert = 2 calls
tests/lib/pipeline.test.ts:731:      // b is the only new video; upsertVideo called once for it with playlistIndex=2 (position), not 1 (new-index)
tests/lib/pipeline.test.ts:755:  // playlistIndex/date stamps now go through bulkUpdateVideoFields → indexStore.updateVideoFields.
tests/lib/pipeline.test.ts:756:  // Returns the fields from the LAST updateVideoFields call for the given videoId.
tests/lib/pipeline.test.ts:795:      // reconcile calls updateVideoFields (not upsertVideo) to un-archive
tests/lib/pipeline.test.ts:812:      // reconcile must NOT have called updateVideoFields with archived:false (it's in-playlist, not removedFromPlaylist)
tests/lib/pipeline.test.ts:1046:  it('sets summaryMd to the filename', () => {
tests/lib/pipeline.test.ts:1048:    expect(video!.summaryMd).toBe('001_test-video-title.md');
tests/lib/pipeline.test.ts:1263:    expect(result.summaryMd).toBe('my-base.md');
tests/lib/pipeline.test.ts:1284:    expect(result.summaryMd).toBe('trunc.md'); // non-blocking — doc still written
tests/lib/summary-audit.test.ts:6:// readIndex enforces outputFolder under $HOME, so the temp dir must live there.
tests/lib/summary-audit.test.ts:10:  const summaryMd = `${base}.md`;
tests/lib/summary-audit.test.ts:12:    fs.writeFileSync(path.join(dir, summaryMd), `## 1. A\n▶ [0:00–1:00](u)\n${body}`);
tests/lib/summary-audit.test.ts:14:  return { id, serialNumber, summaryMd };
tests/lib/summary-audit.test.ts:44:  // archived video: summaryMd base name unchanged, file lives under archived/
tests/lib/summary-audit.test.ts:46:  const videos = [{ id: 'arch', serialNumber: 5, summaryMd: '005_arch.md', archived: true }];
tests/lib/summary-audit.test.ts:56:  const videos = [{ id: 'orph', serialNumber: 6, summaryMd: '006_orph.md', archived: true }];
tests/lib/summary-audit.test.ts:64:it('rejects a summaryMd that escapes the corpus root (path traversal) without reading it', async () => {
tests/lib/summary-audit.test.ts:68:  const videos = [{ id: 'evil', serialNumber: 9, summaryMd: `../${path.basename(outside)}` }];
tests/lib/summary-audit.test.ts:77:it('skips videos without a summaryMd and returns an empty suspect list for a clean corpus', async () => {
tests/lib/summary-audit.test.ts:79:    { id: 'nosum', serialNumber: 1 },                            // no summaryMd → not counted
tests/lib/pipeline-playlist-title.test.ts:10:import { readIndex } from '../../lib/index-store';
tests/lib/pipeline-playlist-title.test.ts:27:  expect(readIndex(dir).playlistTitle).toBe('Building with Claude');
tests/lib/pipeline-playlist-title.test.ts:33:  expect(readIndex(dir).playlistTitle).toBeUndefined();
tests/lib/cloud-sync/model-writer-hash.test.ts:4:// and asserts the persisted model envelope's sourceMdHash is the hash of the MD BODY that was
tests/lib/cloud-sync/model-writer-hash.test.ts:5:// fed to generation — NOT a hash of the sourceMd/summaryMd blob KEY (the filename). Guards
tests/lib/cloud-sync/model-writer-hash.test.ts:6:// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
tests/lib/cloud-sync/model-writer-hash.test.ts:16:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/cloud-sync/model-writer-hash.test.ts:24:// The MD body fed to generation (the whole file `runHtmlDoc` reads as `video.summaryMd`'s blob).
tests/lib/cloud-sync/model-writer-hash.test.ts:56:    overallScore: 4, summaryMd: 'a-title.md',
tests/lib/cloud-sync/model-writer-hash.test.ts:70:it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:81:  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
tests/lib/cloud-sync/model-writer-hash.test.ts:82:  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
tests/lib/archive.test.ts:2:import { upsertVideo, readIndex } from '../../lib/index-store';
tests/lib/archive.test.ts:30:    summaryMd: `${SLUG}.md`,
tests/lib/archive.test.ts:53:  it('moves summaryMd to archived/', async () => {
tests/lib/archive.test.ts:54:    upsertVideo(outputFolder, makeVideo(VIDEO_ID));
tests/lib/archive.test.ts:66:    upsertVideo(outputFolder, makeVideo(VIDEO_ID));
tests/lib/archive.test.ts:76:    upsertVideo(outputFolder, makeVideo(VIDEO_ID));
tests/lib/archive.test.ts:81:    const index = readIndex(outputFolder);
tests/lib/archive.test.ts:86:    upsertVideo(outputFolder, makeVideo(VIDEO_ID));
tests/lib/archive.test.ts:95:    // No upsertVideo — videoId unknown to index; getFilePairs returns []
tests/lib/archive.test.ts:116:    upsertVideo(outputFolder, makeVideo(VIDEO_ID));
tests/lib/archive.test.ts:127:    upsertVideo(outputFolder, makeVideo(VIDEO_ID, true));
tests/lib/archive.test.ts:134:    const index = readIndex(outputFolder);
tests/lib/archive.test.ts:139:    upsertVideo(outputFolder, makeVideo(VIDEO_ID, true));
tests/lib/archive.test.ts:149:    // No upsertVideo — videoId unknown to index
tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
tests/lib/cloud-sync/content-hash.test.ts:18:describe('mdHash', () => {
tests/lib/cloud-sync/content-hash.test.ts:20:    const h = mdHash('# Title\n\nbody\n');
tests/lib/cloud-sync/content-hash.test.ts:22:    expect(mdHash('# Title\n\nbody\n')).toBe(h);
tests/lib/cloud-sync/content-hash.test.ts:26:    expect(mdHash('# T\r\n\r\nbody\r\n\r\n')).toBe(mdHash('# T\n\nbody\n'));
tests/lib/cloud-sync/content-hash.test.ts:29:    expect(mdHash('a\n')).not.toBe(mdHash('b\n'));
tests/lib/cloud-sync/reconcile-class-a.test.ts:5:  summaryMdKey: 'x.md', mdHash: 'h', docVersionMajor: 3, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
tests/lib/cloud-sync/reconcile-class-a.test.ts:11:  it('mdHash equal + both corrections-current → skip', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:12:    expect(reconcileClassA({ local: S({ mdHash: 'h' }), cloud: S({ mdHash: 'h' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:15:  it('mdHash equal but BOTH stale vs reconciled corrections → skip but needsRegen (round-v8 H-1)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:16:    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
tests/lib/cloud-sync/reconcile-class-a.test.ts:19:  it('mdHash equal but one current, one stale → current wins, NOT skip (Blocking ③ scenario 1)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:20:    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: CUR }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:24:    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 2 }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 3 }), reconciledCorrectionsHash: CUR });
tests/lib/cloud-sync/reconcile-class-a.test.ts:28:    const local = S({ mdCorrectionsHash: CUR, docVersionMajor: 2, mdHash: 'hl' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:29:    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:30:    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:34:    const local = S({ docVersionMajor: 2, mdHash: 'hl' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:35:    const cloud = S({ docVersionMajor: 3, mdHash: 'hc' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:36:    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:39:  it('both current, same major, different mdHash → newer mdGeneratedAt unifies', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:40:    const local = S({ mdHash: 'hl', mdGeneratedAt: '2026-05-05T00:00:00.000Z' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:41:    const cloud = S({ mdHash: 'hc', mdGeneratedAt: '2026-02-02T00:00:00.000Z' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:42:    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:46:    const local = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 2, mdHash: 'hl' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:47:    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:48:    const r = reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR });
tests/lib/cloud-sync/reconcile-class-a.test.ts:52:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:54:    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:62:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
tests/lib/serial-migrate-normalization.test.ts:11:import { readIndex, writeIndex } from '@/lib/index-store';
tests/lib/serial-migrate-normalization.test.ts:18:function makeVideo(id: string, processedAt: string, summaryMd: string | null, serialNumber?: number): Video {
tests/lib/serial-migrate-normalization.test.ts:28:    summaryMd,
tests/lib/cloud-sync/manifest.test.ts:23:  const base = { classA: { docVersionMajor: 3, mdGeneratedAt: 't', mdCorrectionsHash: 'c', mdHash: 'h' },
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion } from '@/lib/cloud-sync/companion';
tests/lib/cloud-sync/companion.test.ts:4:const env = (sourceMdHash?: string): ModelEnvelope => ({
tests/lib/cloud-sync/companion.test.ts:7:  ...(sourceMdHash ? { sourceMdHash } : {}),
tests/lib/cloud-sync/companion.test.ts:11:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h1') })).toMatchObject({ kind: 'ship' });
tests/lib/cloud-sync/companion.test.ts:14:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h2') }))
tests/lib/cloud-sync/companion.test.ts:17:it('deletes when the legacy envelope lacks sourceMdHash', () => {
tests/lib/cloud-sync/companion.test.ts:18:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env(undefined) }))
tests/lib/cloud-sync/companion.test.ts:22:  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: null }))
tests/lib/cloud-sync/schema.test.ts:8:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
tests/lib/cloud-sync/schema.test.ts:32:  it('accepts an optional sourceMdHash', () => {
tests/lib/cloud-sync/schema.test.ts:33:    expect(ModelEnvelopeSchema.parse({ ...env, sourceMdHash: 'deadbeef' }).sourceMdHash).toBe('deadbeef');
tests/lib/serial-migrate-exec.test.ts:6:import { readIndex, writeIndex } from '@/lib/index-store';
tests/lib/serial-migrate-exec.test.ts:9:function makeVideo(id: string, processedAt: string, summaryMd: string | null): Video {
tests/lib/serial-migrate-exec.test.ts:19:    summaryMd,
tests/lib/serial-migrate-exec.test.ts:38:    // Seed index with 2 videos (summaryMd set, no serialNumber), processedAt ordered
tests/lib/serial-migrate-exec.test.ts:52:    const after = readIndex(outputFolder).videos.map((v) => v.serialNumber).sort();
tests/lib/serial-migrate-exec.test.ts:95:      summaryMd: null,
tests/lib/serial-migrate-exec.test.ts:102:    // Seed: video with serialNumber:1, summaryMd:'alpha.md'
tests/lib/serial-migrate-exec.test.ts:107:        summaryMd: 'alpha.md',
tests/lib/serial-migrate-exec.test.ts:121:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
tests/lib/serial-migrate-exec.test.ts:130:        summaryMd: 'alpha.md',
tests/lib/serial-migrate-exec.test.ts:150:        summaryMd: 'alpha.md',
tests/lib/serial-migrate-exec.test.ts:168:        summaryMd: 'alpha.md',
tests/lib/serial-migrate-exec.test.ts:178:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
tests/lib/serial-migrate-exec.test.ts:187:        summaryMd: 'alpha.md',      }),
tests/lib/serial-migrate-exec.test.ts:212:        summaryMd: 'alpha.md',        archived: true,
tests/lib/serial-migrate-exec.test.ts:225:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
tests/lib/serial-migrate-exec.test.ts:231:    // (simulating a crash between rename and updateVideoFields)
tests/lib/serial-migrate-exec.test.ts:236:        summaryMd: 'alpha.md',      }),
tests/lib/serial-migrate-exec.test.ts:248:    expect(readIndex(outputFolder).videos[0].summaryMd).toBe('001_alpha.md');
lib/storage/resolve.ts:68: *  service_role worker must resolve the playlist by its UUID and assert
tests/lib/producer-guardrails.test.ts:2:import type { Enqueuer, EnqueueCtx, PreflightVerdict, GuardrailConfigView } from '@/lib/job-queue/enqueuer';
tests/lib/producer-guardrails.test.ts:9:import { enqueuePlaylist, AllEnqueueFailedError } from '@/lib/job-queue/producer';
tests/lib/producer-guardrails.test.ts:15:const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: '1.2.3.4' };
tests/lib/producer-guardrails.test.ts:24:/** Fake Enqueuer implementing the full interface; enqueueImpl drives .enqueue's behavior. */
tests/lib/producer-guardrails.test.ts:25:function fakeEnqueuer(enqueueImpl: (ctx: EnqueueCtx, key: any, payload: any) => Promise<any>): {
tests/lib/producer-guardrails.test.ts:26:  bundle: any; enqueuer: Enqueuer; resolvePlaylistId: jest.Mock; enqueue: jest.Mock;
tests/lib/producer-guardrails.test.ts:29:  const enqueue = jest.fn(enqueueImpl);
tests/lib/producer-guardrails.test.ts:30:  const enqueuer: Enqueuer = {
tests/lib/producer-guardrails.test.ts:31:    enqueue,
tests/lib/producer-guardrails.test.ts:37:  return { bundle, enqueuer, resolvePlaylistId, enqueue };
tests/lib/producer-guardrails.test.ts:42:it('blocks an over-duration video as too_long, never calling enqueue for it', async () => {
tests/lib/producer-guardrails.test.ts:44:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer-guardrails.test.ts:45:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:48:  expect(enqueue).not.toHaveBeenCalled();
tests/lib/producer-guardrails.test.ts:49:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer-guardrails.test.ts:53:it('blocks a live-broadcast video as too_long, never calling enqueue for it', async () => {
tests/lib/producer-guardrails.test.ts:55:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer-guardrails.test.ts:56:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:59:  expect(enqueue).not.toHaveBeenCalled();
tests/lib/producer-guardrails.test.ts:62:it('blocks an upcoming-broadcast video as too_long, never calling enqueue for it', async () => {
tests/lib/producer-guardrails.test.ts:64:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer-guardrails.test.ts:65:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:68:  expect(enqueue).not.toHaveBeenCalled();
tests/lib/producer-guardrails.test.ts:76:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer-guardrails.test.ts:77:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:79:  expect(r.counts.enqueued).toBe(2);
tests/lib/producer-guardrails.test.ts:80:  expect(enqueue).toHaveBeenCalledTimes(2);
tests/lib/producer-guardrails.test.ts:83:it('quota exhausts mid-list: per-video quota_exceeded, remaining videos still attempt enqueue', async () => {
tests/lib/producer-guardrails.test.ts:85:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async (_ctx, key) => {
tests/lib/producer-guardrails.test.ts:89:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:91:  expect(r.counts.enqueued).toBe(2);
tests/lib/producer-guardrails.test.ts:93:  expect(enqueue).toHaveBeenCalledTimes(3); // v3 still attempted after v2's quota block
tests/lib/producer-guardrails.test.ts:94:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer-guardrails.test.ts:100:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async (_ctx, key) => {
tests/lib/producer-guardrails.test.ts:104:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:106:  expect(r.counts.enqueued).toBe(1); // v1
tests/lib/producer-guardrails.test.ts:111:  expect(enqueue).toHaveBeenCalledTimes(2); // v1, v2 — v3/v4 never attempted (cap short-circuits)
tests/lib/producer-guardrails.test.ts:112:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer-guardrails.test.ts:116:it('enqueue receives ctx {ownerId, enqueueIp}', async () => {
tests/lib/producer-guardrails.test.ts:118:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer-guardrails.test.ts:119:  await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:120:  expect(enqueue).toHaveBeenCalledWith(
tests/lib/producer-guardrails.test.ts:121:    { ownerId: 'owner-1', enqueueIp: '1.2.3.4' },
tests/lib/producer-guardrails.test.ts:127:it('PJ003 backstop firing inside the RPC (duration passes producer check) counts toward tooLong', async () => {
tests/lib/producer-guardrails.test.ts:129:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => { throw new VideoTooLongError(); });
tests/lib/producer-guardrails.test.ts:130:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:131:  expect(enqueue).toHaveBeenCalledTimes(1); // producer's own check let it through
tests/lib/producer-guardrails.test.ts:134:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer-guardrails.test.ts:140:    meta('v-new'),                                              // enqueued
tests/lib/producer-guardrails.test.ts:148:  const { bundle, enqueuer } = fakeEnqueuer(async (_ctx, key) => {
tests/lib/producer-guardrails.test.ts:154:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:155:  const { enqueued, joined, skipped, failed, quotaBlocked, capBlocked, tooLong } = r.counts;
tests/lib/producer-guardrails.test.ts:156:  expect(enqueued + joined + skipped + failed + quotaBlocked + capBlocked + tooLong).toBe(7);
tests/lib/producer-guardrails.test.ts:157:  expect(enqueued).toBe(1);
tests/lib/producer-guardrails.test.ts:166:it('does not throw AllEnqueueFailedError when every enqueueable item is guardrail-blocked (not errored)', async () => {
tests/lib/producer-guardrails.test.ts:168:  const { bundle, enqueuer } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer-guardrails.test.ts:169:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:182:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer-guardrails.test.ts:183:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:185:  expect(enqueue).not.toHaveBeenCalled();
tests/lib/producer-guardrails.test.ts:188:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer-guardrails.test.ts:194:it('does NOT throw AllEnqueueFailedError when nothing enqueued but the mix is quota-blocked + genuinely-errored', async () => {
tests/lib/producer-guardrails.test.ts:196:  const { bundle, enqueuer } = fakeEnqueuer(async (_ctx, key) => {
tests/lib/producer-guardrails.test.ts:200:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:203:  expect(r.counts.enqueued).toBe(0);
tests/lib/producer-guardrails.test.ts:205:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer-guardrails.test.ts:209:it('does NOT throw AllEnqueueFailedError when every enqueueable item is quota-blocked (zero generic errors)', async () => {
tests/lib/producer-guardrails.test.ts:211:  const { bundle, enqueuer } = fakeEnqueuer(async () => { throw new QuotaExceededError(); });
tests/lib/producer-guardrails.test.ts:212:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer-guardrails.test.ts:215:  expect(r.counts.enqueued).toBe(0);
tests/lib/producer-guardrails.test.ts:217:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer-guardrails.test.ts:221:it('still throws AllEnqueueFailedError when every enqueue attempt is a genuine error (no guardrail blocks at all)', async () => {
tests/lib/producer-guardrails.test.ts:223:  const { bundle, enqueuer } = fakeEnqueuer(async () => { throw new Error('boom'); });
tests/lib/producer-guardrails.test.ts:224:  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toThrow(AllEnqueueFailedError);
tests/lib/index-store-updated-at.test.ts:5:import { readIndex, updateVideoFields, upsertVideo } from '../../lib/index-store';
tests/lib/index-store-updated-at.test.ts:20:    summaryMd: null,
tests/lib/index-store-updated-at.test.ts:29:describe('updateVideoFields stamps updatedAt on the single mutated video', () => {
tests/lib/index-store-updated-at.test.ts:36:    upsertVideo(dir, touched);
tests/lib/index-store-updated-at.test.ts:37:    upsertVideo(dir, sibling);
tests/lib/index-store-updated-at.test.ts:39:    const before = readIndex(dir);
tests/lib/index-store-updated-at.test.ts:43:    updateVideoFields(dir, 'vidTOUCHED01', { personalScore: 4 });
tests/lib/index-store-updated-at.test.ts:45:    const result = readIndex(dir);
tests/lib/index-store-updated-at.test.ts:62:describe('upsertVideo stamps updatedAt on the single mutated video', () => {
tests/lib/index-store-updated-at.test.ts:68:    upsertVideo(dir, sibling);
tests/lib/index-store-updated-at.test.ts:70:    const before = readIndex(dir);
tests/lib/index-store-updated-at.test.ts:75:    upsertVideo(dir, touched);
tests/lib/index-store-updated-at.test.ts:77:    const result = readIndex(dir);
tests/lib/index-store-updated-at.test.ts:84:    // N3 (load-bearing): the sibling written by an earlier, separate upsertVideo
tests/lib/archive-html.test.ts:23:    overallScore: 4, summaryMd: 'a.md',
tests/lib/cloud-sync/backfill.test.ts:1:import { deriveClassASignals, deriveHumanSnapshot } from '@/lib/cloud-sync/backfill';
tests/lib/cloud-sync/backfill.test.ts:2:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/lib/cloud-sync/backfill.test.ts:8:  overallScore: 3, summaryMd: '001_title.md', processedAt: '2026-01-01T00:00:00.000Z', // KEY, not body
tests/lib/cloud-sync/backfill.test.ts:14:it('hashes the MD BODY, not the summaryMd key (Blocking ①)', () => {
tests/lib/cloud-sync/backfill.test.ts:15:  const s = deriveClassASignals(legacy, BODY);
tests/lib/cloud-sync/backfill.test.ts:16:  expect(s.mdHash).toBe(mdHash(BODY));
tests/lib/cloud-sync/backfill.test.ts:17:  expect(s.mdHash).not.toBe(mdHash('001_title.md')); // must NOT hash the filename
tests/lib/cloud-sync/backfill.test.ts:18:  expect(s.summaryMdKey).toBe('001_title.md');
tests/lib/cloud-sync/backfill.test.ts:22:  const s = deriveClassASignals(legacy, BODY);
tests/lib/cloud-sync/backfill.test.ts:28:it('mdHash is null when there is no MD body', () => {
tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
tests/lib/cloud-sync/backfill.test.ts:30:  expect(s.mdHash).toBeNull();
tests/lib/cloud-sync/backfill.test.ts:31:  expect(s.summaryMdKey).toBeNull();
tests/lib/cloud-sync/backfill.test.ts:35:  const s = deriveClassASignals({ ...legacy, mdGeneratedAt: '2026-03-03T00:00:00.000Z', mdCorrectionsHash: 'h', docVersion: { major: 3, minor: 3 } }, BODY);
tests/lib/cloud-sync/backfill.test.ts:42:  const snap = deriveHumanSnapshot(legacy);
tests/lib/cloud-sync/local-stamping.test.ts:23:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
tests/lib/cloud-sync/local-stamping.test.ts:31:    await localMetadataStore.upsertVideo(p, v('a'));
tests/lib/cloud-sync/local-stamping.test.ts:33:    const idx = await localMetadataStore.readIndex(p);
tests/lib/cloud-sync/local-stamping.test.ts:43:    await localMetadataStore.upsertVideo(p, v('a'));
tests/lib/cloud-sync/local-stamping.test.ts:45:    const idx = await localMetadataStore.readIndex(p);
tests/lib/cloud-sync/local-stamping.test.ts:53:    await localMetadataStore.upsertVideo(p, { ...v('a'), personalNote: 'old' });
tests/lib/cloud-sync/local-stamping.test.ts:55:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:60:  // PRODUCTION PATH: local personalNote/corrections edits flow through updateVideoFields
tests/lib/cloud-sync/local-stamping.test.ts:63:  it('updateVideoFields stamps annotationsEditedAt for a Class-B field (corrections)', async () => {
tests/lib/cloud-sync/local-stamping.test.ts:67:    await localMetadataStore.upsertVideo(p, v('a'));
tests/lib/cloud-sync/local-stamping.test.ts:68:    await localMetadataStore.updateVideoFields(p, 'a', { corrections: 'fix' });
tests/lib/cloud-sync/local-stamping.test.ts:69:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:73:  it('updateVideoFields does NOT stamp annotationsEditedAt for a non-Class-B field', async () => {
tests/lib/cloud-sync/local-stamping.test.ts:77:    await localMetadataStore.upsertVideo(p, v('a'));
tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
tests/lib/cloud-sync/local-stamping.test.ts:79:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/cloud-sync/local-stamping.test.ts:89:    await localMetadataStore.upsertVideo(p, v('a'));
tests/lib/cloud-sync/local-stamping.test.ts:91:    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
tests/lib/pdf/pdf-path.test.ts:9:    expect(pdfRelPath(v({ summaryMd: 'raw/275_google-okf.md' }), 'summary')).toBe('pdfs/275_google-okf.pdf');
tests/lib/pdf/pdf-path.test.ts:13:    expect(pdfRelPath(v({ summaryMd: '001_intro.md' }), 'summary')).toBe('pdfs/001_intro.pdf');
tests/lib/pdf/pdf-path.test.ts:22:  it('summary without summaryMd throws', () => {
tests/lib/pdf/pdf-path.test.ts:27:    expect(() => pdfRelPath(v({ summaryMd: 'raw/x.md' }), 'dig-deeper')).toThrow();
tests/lib/timestamp-audit.test.ts:6:// MUST root the temp dir under $HOME — auditTimestamps → readIndex → assertOutputFolder
tests/lib/timestamp-audit.test.ts:21:      { id: 'a', summaryMd: 'a.md', docVersion: { major: 3, minor: 3 } },          // current, ▶ → withTs
tests/lib/timestamp-audit.test.ts:22:      { id: 'b', summaryMd: 'b.md', docVersion: { major: 2, minor: 0 } },          // old, no ▶ → wouldRegen
tests/lib/timestamp-audit.test.ts:23:      { id: 'c', summaryMd: 'c.md', docVersion: { major: 3, minor: 0 } },          // current, no ▶ → stuck
tests/lib/timestamp-audit.test.ts:24:      { id: 'd', summaryMd: 'd.md' },                                              // absent ver, no ▶ → wouldRegen
tests/lib/timestamp-audit.test.ts:25:      { id: 'e', summaryMd: 'e.md', docVersion: { major: 3, minor: 0 } },          // file missing → mdMissing
tests/lib/cloud-sync/regenerate-stamp.test.ts:4:// tests/api/regenerate.test.ts) and asserts the SECOND updateVideoFields call — the one
tests/lib/cloud-sync/regenerate-stamp.test.ts:6:// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
tests/lib/cloud-sync/regenerate-stamp.test.ts:27:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/cloud-sync/regenerate-stamp.test.ts:29:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/lib/cloud-sync/regenerate-stamp.test.ts:32:const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
tests/lib/cloud-sync/regenerate-stamp.test.ts:57:  summaryMd: SUMMARY_MD,
tests/lib/cloud-sync/regenerate-stamp.test.ts:92:        mdCorrectionsHash: mdHash('fix name'),
tests/lib/cloud-sync/regenerate-stamp.test.ts:104:        mdCorrectionsHash: mdHash('old corrections'),
tests/lib/cloud-sync/regenerate-stamp.test.ts:116:        mdCorrectionsHash: mdHash(''),
tests/lib/cloud-sync/import-guard.test.ts:34:    /SUPABASE_SERVICE_ROLE_KEY/,        // literal env var name — any reference
tests/lib/cloud-sync/import-guard.test.ts:36:    /createServiceClient\s*\(/,         // the service_role client constructor
tests/lib/cloud-sync/import-guard.test.ts:37:    importOf('@/lib/supabase/service'), // module that builds the service_role client
tests/lib/cloud-sync/import-guard.test.ts:57:        src: `const key = process.env.SUPABASE_SERVICE_ROLE_KEY;`,
tests/lib/cloud-sync/import-guard.test.ts:58:        re: /SUPABASE_SERVICE_ROLE_KEY/,
tests/lib/serial-migrate.test.ts:7:  overallScore: 3, summaryMd: 's.md',
tests/lib/serial-migrate.test.ts:13:    v({ id: 'a', processedAt: '2026-01-01T00:00:00.000Z', summaryMd: 'alpha.md' }),
tests/lib/serial-migrate.test.ts:17:  expect(ops).toContainEqual({ field: 'summaryMd', from: 'alpha.md', to: '001_alpha.md' });
tests/lib/serial-migrate.test.ts:22:  const { perVideo } = planMigration([v({ id: 'a', serialNumber: 1, summaryMd: '001_alpha.md' })]);
tests/lib/serial-migrate.test.ts:23:  expect(perVideo[0].renames.find((o) => o.field === 'summaryMd')).toBeUndefined();
tests/lib/serial-migrate.test.ts:29:    v({ id: 'new', summaryMd: 'n.md', processedAt: '2026-02-01T00:00:00.000Z' }),
tests/lib/serial-migrate.test.ts:39:      summaryMd: 'foo.md',
tests/lib/serial-migrate.test.ts:45:  expect(renames).toContainEqual({ field: 'summaryMd', from: 'foo.md', to: '005_foo.md' });
tests/lib/dig/dig-section.test.ts:29:const video = { id: 'v', title: 'T', youtubeUrl: 'https://youtu.be/v', durationSeconds: 600, language: 'en', summaryMd: 'v.md' };
tests/lib/dig/dig-section.test.ts:32:  jest.mocked(indexStore.readIndex).mockReturnValue({ playlistUrl: '', outputFolder: OF, videos: [video] } as any);
tests/lib/dig/dig-section.test.ts:33:  jest.mocked(indexStore.updateVideoFields).mockImplementation(() => {});
tests/lib/dig/dig-section.test.ts:49:  expect(jest.mocked(indexStore.updateVideoFields)).toHaveBeenCalledWith(OF, 'v', { digDeeperMd: 'v-dig-deeper.md' });
lib/storage/local/local-blob-store.ts:41:    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
tests/lib/html-doc/nav-cloud-dig.test.ts:57:    .mockResolvedValueOnce({ ok: true, status: 202, json: async () => ({ status: 'enqueued', jobId: 'j1', sectionId: 65 }) })
tests/lib/html-doc/nav-cloud-dig.test.ts:100:      .mockResolvedValueOnce({ ok: true, status: 202, json: async () => ({ status: 'enqueued', jobId: 'j' }) })
tests/lib/html-doc/nav-cloud-dig.test.ts:137:    .mockResolvedValueOnce({ ok: true, status: 202, json: async () => ({ status: 'enqueued', jobId: 'j' }) })
tests/lib/html-doc/rerender.test.ts:60:    overallScore: 4, summaryMd: 'a-title.md',
tests/lib/html-doc/rerender.test.ts:111:  it('skips when the video has no summaryMd', async () => {
tests/lib/html-doc/rerender.test.ts:112:    writeIndex([baseVideo({ summaryMd: null })]);
tests/lib/html-doc/rerender.test.ts:181:    // video B: summaryMd + summaryHtml set but NO model → skipped-no-model
tests/lib/html-doc/rerender.test.ts:183:    const vidB = baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' });
tests/lib/html-doc/rerender.test.ts:191:        expect.objectContaining({ summaryMd: 'a-title.md', status: 'rerendered' }),
tests/lib/html-doc/rerender.test.ts:192:        expect.objectContaining({ summaryMd: 'b-title.md', status: 'skipped-no-model' }),
tests/lib/html-doc/rerender.test.ts:198:    const vidC = baseVideo({ id: 'vidC', summaryMd: null, summaryHtml: null });
tests/lib/html-doc/rerender.test.ts:211:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
tests/lib/html-doc/rerender.test.ts:224:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
tests/lib/html-doc/rerender.test.ts:239:        expect.objectContaining({ summaryMd: 'a-title.md', status: 'error', message: expect.stringMatching(/disk full/) }),
tests/lib/html-doc/rerender.test.ts:240:        expect.objectContaining({ summaryMd: 'b-title.md', status: 'rerendered' }),
tests/lib/supabase-metadata-store-summary-ready.test.ts:8:// not exported). Only the readIndex path (playlists.maybeSingle +
tests/lib/supabase-metadata-store-summary-ready.test.ts:73:// readIndex — summaryReady derivation
tests/lib/supabase-metadata-store-summary-ready.test.ts:75:describe('readIndex — summaryReady derivation', () => {
tests/lib/supabase-metadata-store-summary-ready.test.ts:76:  test('derives true for promoted, false for committed, false for artifacts-absent', async () => {
tests/lib/supabase-metadata-store-summary-ready.test.ts:90:            summaryMd: 'hello',
tests/lib/supabase-metadata-store-summary-ready.test.ts:92:            artifacts: { summaryMd: { status: 'promoted' } },
tests/lib/supabase-metadata-store-summary-ready.test.ts:106:            summaryMd: 'hello',
tests/lib/supabase-metadata-store-summary-ready.test.ts:108:            artifacts: { summaryMd: { status: 'committed' } },
tests/lib/supabase-metadata-store-summary-ready.test.ts:122:            summaryMd: 'hello',
tests/lib/supabase-metadata-store-summary-ready.test.ts:131:    const index = await store.readIndex(p);
tests/lib/storage/local-metadata-store.test.ts:17:test('readIndex on an empty folder returns the empty index shape', async () => {
tests/lib/storage/local-metadata-store.test.ts:19:  await expect(store.readIndex(p)).resolves.toEqual({ playlistUrl: '', outputFolder: p.indexKey, videos: [] });
tests/lib/storage/local-metadata-store.test.ts:22:test('claimVideoSlot appends position (0-based) and serialNumber (1-based)', async () => {
tests/lib/storage/local-metadata-store.test.ts:25:  const a = await store.claimVideoSlot(p, 'vid00000001');
tests/lib/storage/local-metadata-store.test.ts:26:  const b = await store.claimVideoSlot(p, 'vid00000002');
tests/lib/storage/local-metadata-store.test.ts:33:  await store.claimVideoSlot(p, 'vid00000001');
tests/lib/storage/local-metadata-store.test.ts:34:  await store.upsertVideo(p, { id: 'vid00000001', youtubeUrl: 'https://youtu.be/vid00000001' } as any);
tests/lib/storage/local-metadata-store.test.ts:36:  const idx = await store.readIndex(p);
tests/lib/storage/local-metadata-store.test.ts:42:  await store.claimVideoSlot(p, 'vid00000001');
tests/lib/storage/local-metadata-store.test.ts:43:  await store.upsertVideo(p, { id: 'vid00000001', youtubeUrl: 'https://youtu.be/vid00000001', archived: true, removedFromPlaylist: true } as any);
tests/lib/storage/local-metadata-store.test.ts:45:  const idx = await store.readIndex(p);
lib/storage/local/local-metadata-store.ts:10:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/local/local-metadata-store.ts:11:    return indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:14:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:22:  async claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }> {
lib/storage/local/local-metadata-store.ts:23:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:26:    // reserve the slot with a minimal valid Video; real data arrives via upsertVideo
lib/storage/local/local-metadata-store.ts:27:    indexStore.upsertVideo(p.indexKey, { id: videoId, serialNumber } as Video);
lib/storage/local/local-metadata-store.ts:30:  async upsertVideo(p: Principal, video: Video): Promise<void> {
lib/storage/local/local-metadata-store.ts:31:    indexStore.upsertVideo(p.indexKey, video);
lib/storage/local/local-metadata-store.ts:40:  async updateVideoFields(
lib/storage/local/local-metadata-store.ts:55:      const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:62:    indexStore.updateVideoFields(p.indexKey, id, toWrite);
lib/storage/local/local-metadata-store.ts:65:    for (const { videoId, fields } of patches) indexStore.updateVideoFields(p.indexKey, videoId, fields);
lib/storage/local/local-metadata-store.ts:68:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:82:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:91:  // branch is unchanged and still calls updateVideoFields directly). Allowlist applied
lib/storage/local/local-metadata-store.ts:93:  // dropped by JSON.stringify on write, matching updateVideoFields' existing clear-by-
lib/storage/local/local-metadata-store.ts:107:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:136:    indexStore.updateVideoFields(p.indexKey, videoId, fields);
lib/storage/local/local-metadata-store.ts:142:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:149:        indexStore.updateVideoFields(p.indexKey, v.id, { archived: true, removedFromPlaylist: true } as Partial<Video>);
lib/storage/local/local-metadata-store.ts:151:        indexStore.updateVideoFields(p.indexKey, v.id, { archived: false, removedFromPlaylist: false } as Partial<Video>);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:2:import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
tests/lib/dig/cloud/enqueue-dig-core.test.ts:20:const enqueuer = {
tests/lib/dig/cloud/enqueue-dig-core.test.ts:22:  enqueue: jest.fn(async () => ({ jobId: 'job1', status: 'queued', joined: false })),
tests/lib/dig/cloud/enqueue-dig-core.test.ts:25:const base = { supabase: {} as any, enqueuer: enqueuer as any, userId: 'u1', isAnonymous: false, videoId: 'vid1', playlistId: 'pl', sectionId: 132, enqueueIp: null };
tests/lib/dig/cloud/enqueue-dig-core.test.ts:28:it('202 enqueued when absent (charges once)', async () => {
tests/lib/dig/cloud/enqueue-dig-core.test.ts:30:  const r = await enqueueDig(base);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:32:  expect(r.body).toEqual({ status: 'enqueued', jobId: 'job1', sectionId: 132 });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:33:  expect(enqueuer.enqueue).toHaveBeenCalledTimes(1); // charges exactly once (not zero, not twice)
tests/lib/dig/cloud/enqueue-dig-core.test.ts:34:  expect(enqueuer.enqueue).toHaveBeenCalledWith(
tests/lib/dig/cloud/enqueue-dig-core.test.ts:35:    { ownerId: 'u1', enqueueIp: null },
tests/lib/dig/cloud/enqueue-dig-core.test.ts:40:it('200 ready when the current-version blob exists (no enqueue, no charge)', async () => {
tests/lib/dig/cloud/enqueue-dig-core.test.ts:42:  const r = await enqueueDig(base);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:45:  expect(enqueuer.enqueue).not.toHaveBeenCalled();
tests/lib/dig/cloud/enqueue-dig-core.test.ts:47:it('403 for an anonymous user (never reads/enqueues)', async () => {
tests/lib/dig/cloud/enqueue-dig-core.test.ts:48:  const r = await enqueueDig({ ...base, isAnonymous: true });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:52:  expect(enqueuer.preflight).not.toHaveBeenCalled();
tests/lib/dig/cloud/enqueue-dig-core.test.ts:53:  expect(enqueuer.enqueue).not.toHaveBeenCalled();
tests/lib/dig/cloud/enqueue-dig-core.test.ts:57:  expect((await enqueueDig(base)).status).toBe(404);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:61:  expect((await enqueueDig({ ...base, sectionId: 999 })).status).toBe(404);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:65:  enqueuer.enqueue.mockRejectedValueOnce(new QuotaExceededError());
tests/lib/dig/cloud/enqueue-dig-core.test.ts:66:  expect((await enqueueDig(base)).status).toBe(429);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:67:  enqueuer.enqueue.mockRejectedValueOnce(new DailyCapError());
tests/lib/dig/cloud/enqueue-dig-core.test.ts:68:  expect((await enqueueDig(base)).status).toBe(503);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:69:  enqueuer.enqueue.mockRejectedValueOnce(new VideoTooLongError());
tests/lib/dig/cloud/enqueue-dig-core.test.ts:70:  expect((await enqueueDig(base)).status).toBe(400);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:74:  enqueuer.preflight.mockResolvedValueOnce({ admitted: true, atCapacity: false, velocityExceeded: true, challengeRequired: false });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:75:  expect((await enqueueDig(base)).status).toBe(429);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:76:  enqueuer.preflight.mockResolvedValueOnce({ admitted: true, atCapacity: true, velocityExceeded: false, challengeRequired: false });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:77:  expect((await enqueueDig(base)).status).toBe(503);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:78:  enqueuer.preflight.mockResolvedValueOnce({ admitted: false, atCapacity: false, velocityExceeded: false, challengeRequired: false });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:79:  expect((await enqueueDig(base)).status).toBe(403);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:82:  const exists = jest.fn(async () => false); // absent at dedup AND at the post-enqueue re-check
tests/lib/dig/cloud/enqueue-dig-core.test.ts:84:  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jc', status: 'completed', joined: true });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:85:  const r = await enqueueDig(base);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:98:  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jc', status: 'completed', joined: true });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:99:  const r = await enqueueDig(base);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:105:  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jq', status: 'queued', joined: true });
tests/lib/dig/cloud/enqueue-dig-core.test.ts:106:  expect((await enqueueDig(base)).status).toBe(202);
tests/lib/dig/cloud/resolve-summary-key.test.ts:4:  it('prefers artifacts.summaryMd.key over the top-level summaryMd fallback', () => {
tests/lib/dig/cloud/resolve-summary-key.test.ts:5:    const video = { summaryMd: '0001_old.md', artifacts: { summaryMd: { key: '0001_new.md' } } };
tests/lib/dig/cloud/resolve-summary-key.test.ts:9:  it('falls back to the top-level summaryMd when the artifact key is absent', () => {
tests/lib/dig/cloud/resolve-summary-key.test.ts:10:    const video = { summaryMd: '0001_old.md' };
tests/lib/dig/cloud/resolve-summary-key.test.ts:15:    const video = { summaryMd: null };
tests/lib/dig/cloud/resolve-summary-key.test.ts:20:    const video = { summaryMd: 'nested/foo.md' };
tests/lib/html-doc/generate.test.ts:7:import { updateVideoFields } from '../../../lib/index-store';
tests/lib/html-doc/generate.test.ts:13:// Wrap index-store so updateVideoFields calls through by default but can be forced to throw.
tests/lib/html-doc/generate.test.ts:16:  return { __esModule: true, ...actual, updateVideoFields: jest.fn(actual.updateVideoFields) };
tests/lib/html-doc/generate.test.ts:19:const mockUpdate = updateVideoFields as jest.Mock;
tests/lib/html-doc/generate.test.ts:64:    overallScore: 4, summaryMd: 'a-title.md',
tests/lib/html-doc/generate.test.ts:106:it('throws when summaryMd is missing', async () => {
tests/lib/html-doc/generate.test.ts:107:  writeIndex([{ ...baseVideo(), summaryMd: null }]);
tests/lib/html-doc/generate.test.ts:108:  await expect(runHtmlDoc(VIDEO_ID, dir, () => {})).rejects.toThrow(/source note|summaryMd/i);
tests/lib/video-schema.test.ts:13:    summaryMd: null,
tests/lib/video-schema.test.ts:64:    summaryMd: null,
tests/lib/storage/delayed-async-fake.ts:5: * e.g. `store.readIndex(p)` and immediately accesses `.videos` on the result (which is a
tests/lib/storage/delayed-async-fake.ts:17:    readIndex: (p) => wrap(() => inner.readIndex(p)),
tests/lib/storage/delayed-async-fake.ts:19:    claimVideoSlot: (p, v) => wrap(() => inner.claimVideoSlot(p, v)),
tests/lib/storage/delayed-async-fake.ts:20:    upsertVideo: (p, v) => wrap(() => inner.upsertVideo(p, v)),
tests/lib/storage/delayed-async-fake.ts:21:    updateVideoFields: (p, i, f) => wrap(() => inner.updateVideoFields(p, i, f)),
tests/lib/html-doc/eligibility.test.ts:9:    overallScore: 3, summaryMd: '1_t.md',
tests/lib/html-doc/eligibility.test.ts:16:  it('selectable iff summaryMd present', () => {
tests/lib/html-doc/eligibility.test.ts:17:    expect(summarySelectable(v({ summaryMd: '1_t.md' }))).toBe(true);
tests/lib/html-doc/eligibility.test.ts:18:    expect(summarySelectable(v({ summaryMd: null }))).toBe(false);
tests/lib/html-doc/eligibility.test.ts:29:  it('no work when no summaryMd (nothing to generate from)', () => {
tests/lib/html-doc/eligibility.test.ts:30:    expect(summaryNeedsWork(v({ summaryMd: null, summaryHtml: null }))).toBe(false);
tests/lib/html-doc/eligibility.test.ts:42:    expect(videoNeedsBatchWork(v({ summaryMd: null, summaryHtml: null, digDeeperMd: null }), 'summary-dig')).toBe(false); // no summary → nothing
tests/lib/supabase/service-guard.test.ts:7:    process.env.SUPABASE_SERVICE_ROLE_KEY = 'svc-123';
tests/lib/supabase/service-guard.test.ts:15:    delete process.env.SUPABASE_SERVICE_ROLE_KEY;
tests/lib/supabase/service-guard.test.ts:18:    expect(() => createServiceClient()).toThrow(/SUPABASE_SERVICE_ROLE_KEY/);
tests/lib/index-store.test.ts:5:import { readIndex, updateVideoFields, upsertVideo, writeIndex } from '../../lib/index-store';
tests/lib/index-store.test.ts:21:    summaryMd: null,
tests/lib/index-store.test.ts:30:describe('readIndex', () => {
tests/lib/index-store.test.ts:35:    const result = readIndex(dir);
tests/lib/index-store.test.ts:42:    expect(() => readIndex('/etc')).toThrow(expect.objectContaining({ statusCode: 400 }));
tests/lib/index-store.test.ts:66:    const result = readIndex(dir);
tests/lib/index-store.test.ts:75:    expect(v.summaryMd).toBeNull();
tests/lib/index-store.test.ts:80:describe('writeIndex + readIndex', () => {
tests/lib/index-store.test.ts:92:    const result = readIndex(dir);
tests/lib/index-store.test.ts:98:describe('upsertVideo', () => {
tests/lib/index-store.test.ts:104:    upsertVideo(dir, video);
tests/lib/index-store.test.ts:106:    const result = readIndex(dir);
tests/lib/index-store.test.ts:108:    // updatedAt is stamped dynamically by upsertVideo (Stage 2a) — match all
tests/lib/index-store.test.ts:121:    upsertVideo(dir, original);
tests/lib/index-store.test.ts:122:    upsertVideo(dir, updated);
tests/lib/index-store.test.ts:124:    const result = readIndex(dir);
tests/lib/index-store.test.ts:133:    expect(() => upsertVideo(dir, makeVideo({ id: '../passwd' }))).toThrow(
tests/lib/index-store.test.ts:154:describe('updateVideoFields', () => {
tests/lib/index-store.test.ts:159:    const video = makeVideo({ id: 'vid333333333', summaryMd: null });
tests/lib/index-store.test.ts:160:    upsertVideo(dir, video);
tests/lib/index-store.test.ts:162:    updateVideoFields(dir, 'vid333333333', { summaryMd: 'vid333333333.md', digDeeperMd: 'vid333333333-dig-deeper.md' });
tests/lib/index-store.test.ts:164:    const result = readIndex(dir);
tests/lib/index-store.test.ts:165:    expect(result.videos[0].summaryMd).toBe('vid333333333.md');
tests/lib/index-store.test.ts:176:    upsertVideo(dir, video);
tests/lib/index-store.test.ts:178:    updateVideoFields(dir, 'vid555555555', { id: 'vid999999999' } as Partial<Video>);
tests/lib/index-store.test.ts:180:    const result = readIndex(dir);
tests/lib/index-store.test.ts:188:    expect(() => updateVideoFields(dir, 'vid444444444', { summaryMd: 'x.md' })).toThrow('Video not found');
tests/lib/index-store.test.ts:195:    expect(() => updateVideoFields(dir, '../passwd', {})).toThrow(
tests/lib/producer.test.ts:4:  // T2: producer now also calls fetchPlaylistTitleOrNull after resolvePlaylistId. Stub it here
tests/lib/producer.test.ts:11:import { enqueuePlaylist, PlaylistTooLargeError, AllEnqueueFailedError, MAX_VIDEOS_PER_ENQUEUE } from '@/lib/job-queue/producer';
tests/lib/producer.test.ts:13:import type { Enqueuer, EnqueueCtx, PreflightVerdict, GuardrailConfigView } from '@/lib/job-queue/enqueuer';
tests/lib/producer.test.ts:18:const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: null };
tests/lib/producer.test.ts:26:function fakeEnqueuer(enqueueImpl: Enqueuer['enqueue']) {
tests/lib/producer.test.ts:28:  const enqueue = jest.fn(enqueueImpl);
tests/lib/producer.test.ts:29:  const enqueuer: Enqueuer = {
tests/lib/producer.test.ts:30:    enqueue,
tests/lib/producer.test.ts:36:  return { bundle, enqueuer, resolvePlaylistId, enqueue };
tests/lib/producer.test.ts:42:  const { bundle, enqueuer, resolvePlaylistId } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer.test.ts:43:  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toBeInstanceOf(PlaylistTooLargeError);
tests/lib/producer.test.ts:50:  const { bundle, enqueuer, resolvePlaylistId } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer.test.ts:51:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer.test.ts:52:  expect(r.playlistId).toBeNull(); expect(r.counts.enqueued).toBe(0);
tests/lib/producer.test.ts:56:  const r2 = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer.test.ts:61:it('fans out, counts disjointly, and joined does not count as enqueued', async () => {
tests/lib/producer.test.ts:63:  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async (_ctx: any, key: any) =>
tests/lib/producer.test.ts:65:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer.test.ts:67:  expect(r.counts).toEqual({ enqueued: 1, joined: 1, skipped: 1, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
tests/lib/producer.test.ts:68:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer.test.ts:70:  expect(enqueue).toHaveBeenCalledWith(
tests/lib/producer.test.ts:76:it('throws AllEnqueueFailedError when every enqueue fails', async () => {
tests/lib/producer.test.ts:78:  const { bundle, enqueuer } = fakeEnqueuer(async () => { throw new Error('db down'); });
tests/lib/producer.test.ts:79:  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toBeInstanceOf(AllEnqueueFailedError);
tests/lib/producer.test.ts:82:  const { bundle: bundle2, enqueuer: enqueuer2 } = fakeEnqueuer(async () => { throw new Error('db down'); });
tests/lib/producer.test.ts:84:  try { await enqueuePlaylist(bundle2, enqueuer2, principal, URL_, ctx); } catch (e) { caught = e; }
tests/lib/producer.test.ts:90:    meta('v-new'),       // will be newly enqueued (joined:false)
tests/lib/producer.test.ts:93:    meta('v-fail'),       // enqueue throws -> failed
tests/lib/producer.test.ts:95:  const { bundle, enqueuer } = fakeEnqueuer(async (_ctx: any, key: any) => {
tests/lib/producer.test.ts:100:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer.test.ts:101:  expect(r.counts).toEqual({ enqueued: 1, joined: 1, skipped: 1, failed: 1, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
tests/lib/producer.test.ts:102:  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
tests/lib/producer.test.ts:106:it('best-effort: one failed enqueue does not stop the rest', async () => {
tests/lib/producer.test.ts:108:  const { bundle, enqueuer } = fakeEnqueuer(async (_ctx: any, key: any) => {
tests/lib/producer.test.ts:112:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer.test.ts:113:  expect(r.counts).toEqual({ enqueued: 1, joined: 0, skipped: 0, failed: 1, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
tests/lib/producer.test.ts:115:  expect(failedEntry).toEqual({ videoId: 'v1', error: 'enqueue failed' });   // review High — no raw error leak
tests/lib/producer.test.ts:120:  const { bundle, enqueuer } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'completed', joined: true }));
tests/lib/producer.test.ts:121:  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
tests/lib/producer.test.ts:122:  expect(r.counts).toEqual({ enqueued: 0, joined: 2, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
tests/lib/producer.test.ts:125:it('resolvePlaylistId failure aborts before any enqueue', async () => {   // review L2
tests/lib/producer.test.ts:127:  const enqueue = jest.fn();
tests/lib/producer.test.ts:128:  const enqueuer: Enqueuer = {
tests/lib/producer.test.ts:129:    enqueue,
tests/lib/producer.test.ts:135:  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toThrow('db');
tests/lib/producer.test.ts:136:  expect(enqueue).not.toHaveBeenCalled();
tests/lib/producer.test.ts:141:  const { bundle, enqueuer } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
tests/lib/producer.test.ts:142:  const { PlaylistFetchError } = await import('@/lib/job-queue/producer');
tests/lib/producer.test.ts:143:  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toBeInstanceOf(PlaylistFetchError);
lib/storage/supabase/supabase-job-queue.ts:21:   * on the caller's session client — this method MUST NOT be called on a service_role-constructed
lib/storage/supabase/supabase-job-queue.ts:22:   * SupabaseJobQueue (service_role bypasses RLS and would leak cross-owner rows).
tests/lib/html-doc/ensure.test.ts:18:  overallScore: 3, summaryMd: 'base.md',
tests/lib/html-doc/ensure.test.ts:28:    language: 'en', ratings: videoBase.ratings, overallScore: 4, tags: ['t'], summaryMd: 'base.md', mdContent: '#',
tests/lib/html-doc/ensure.test.ts:32:  (indexStore.readIndex as jest.Mock).mockReturnValue({ videos: [{ ...videoBase, ...v }] });
tests/lib/html-doc/ensure.test.ts:42:    const patches = (indexStore.updateVideoFields as jest.Mock).mock.calls.map((c) => c[2]);
tests/lib/html-doc/ensure.test.ts:81:  it('throws 422-style error when the video has no summaryMd', async () => {
tests/lib/html-doc/ensure.test.ts:82:    withVideo({ summaryMd: null });
tests/lib/html-doc/ensure.test.ts:105:    const patches = (indexStore.updateVideoFields as jest.Mock).mock.calls.map((c) => c[2]);
tests/lib/ask-gemini.test.ts:12:    overallScore: 4, summaryMd: null,
lib/storage/empty-index.ts:4:/** The exact shape lib/index-store.readIndex returns for an absent index file,
lib/storage/blob-store.ts:3:export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';
lib/storage/supabase/consistency.ts:5:export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';
lib/storage/supabase/consistency.ts:7:const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];
lib/storage/supabase/consistency.ts:15: * Sequence: putStaged → verify temp exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)
lib/storage/supabase/consistency.ts:33:  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
lib/storage/supabase/consistency.ts:39:  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
lib/storage/supabase/consistency.ts:40:    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
lib/storage/supabase/consistency.ts:46: * Source kinds (summaryMd, slide, modelJson) require manual repair — they cannot
tests/lib/supabase/confinement.test.ts:5:describe('service_role confinement', () => {
tests/lib/supabase/confinement.test.ts:9:    // check-service-confinement.ts ALLOWED_SERVICE_IMPORTERS). Everything else must still
lib/storage/supabase/supabase-metadata-store.ts:9:// before any write to `videos.data`. readIndex() surfaces `updatedAt`
lib/storage/supabase/supabase-metadata-store.ts:11:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
lib/storage/supabase/supabase-metadata-store.ts:14:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
lib/storage/supabase/supabase-metadata-store.ts:27:  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
lib/storage/supabase/supabase-metadata-store.ts:29:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/supabase/supabase-metadata-store.ts:53:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
lib/storage/supabase/supabase-metadata-store.ts:54:            .artifacts?.summaryMd?.status === 'promoted',
lib/storage/supabase/supabase-metadata-store.ts:86:  // claimVideoSlot: RPC appends a reservation row and returns position + serial.
lib/storage/supabase/supabase-metadata-store.ts:88:  async claimVideoSlot(
lib/storage/supabase/supabase-metadata-store.ts:103:  // upsertVideo: UPDATE the reservation row already created by claimVideoSlot.
lib/storage/supabase/supabase-metadata-store.ts:105:  async upsertVideo(p: Principal, video: Video): Promise<void> {
lib/storage/supabase/supabase-metadata-store.ts:116:  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
lib/storage/supabase/supabase-metadata-store.ts:118:  // Stage 3 (§5.1/§5.7): merge_video_data (0021) stamps annotationsEditedAt server-side
lib/storage/supabase/supabase-metadata-store.ts:123:  async updateVideoFields(
lib/storage/supabase/supabase-metadata-store.ts:130:    const { error } = await this.client.rpc('merge_video_data', {
lib/storage/supabase/supabase-metadata-store.ts:148:    const { error } = await this.client.rpc('merge_video_data_bulk', {
lib/storage/supabase/supabase-metadata-store.ts:248:  // updateVideoAnnotations: distinct write path from updateVideoFields/merge_video_data
lib/storage/supabase/supabase-metadata-store.ts:250:  // the owner_id = auth.uid() guard are enforced IN SQL by update_video_annotations — this
lib/storage/supabase/supabase-metadata-store.ts:267:    const { data, error } = await this.client.rpc('update_video_annotations', {
tests/lib/storage/consistency.test.ts:15:  test.each<ArtifactKind>(['summaryMd', 'slide', 'modelJson'])('%s is a source kind', (k) => {
tests/lib/storage/consistency.test.ts:63: * Creates a mock MetadataStore that records updateVideoFields calls in order.
tests/lib/storage/consistency.test.ts:69:  const meta: Pick<MetadataStore, 'updateVideoFields'> = {
tests/lib/storage/consistency.test.ts:70:    async updateVideoFields(_p, id, fields) {
tests/lib/storage/consistency.test.ts:73:      order.push(`updateVideoFields(${id},${statusStr})`);
tests/lib/storage/consistency.test.ts:85:  test('follows ordered sequence: putStaged → exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)', async () => {
tests/lib/storage/consistency.test.ts:94:    const origUpdateVideoFields = meta.updateVideoFields.bind(meta);
tests/lib/storage/consistency.test.ts:99:    meta.updateVideoFields = async (...args) => {
tests/lib/storage/consistency.test.ts:102:      combined.push(`updateVideoFields(${status?.status ?? '?'})`);
tests/lib/storage/consistency.test.ts:111:      kind: 'summaryMd',
tests/lib/storage/consistency.test.ts:120:      'updateVideoFields(committed)',
tests/lib/storage/consistency.test.ts:122:      'updateVideoFields(promoted)',
tests/lib/storage/consistency.test.ts:126:  test('passes correct key and status to updateVideoFields', async () => {
tests/lib/storage/consistency.test.ts:142:    const [committed, promoted] = calls;
tests/lib/storage/consistency.test.ts:145:    expect((promoted.fields as any).artifacts.slide.status).toBe('promoted');
tests/lib/storage/consistency.test.ts:157:      kind: 'summaryMd',
tests/lib/storage/consistency.test.ts:196:    const result = await resolveMissing({ kind: 'summaryMd', regenerate, markRepair });
tests/lib/storage/supabase-metadata-store.test.ts:155:// readIndex
tests/lib/storage/supabase-metadata-store.test.ts:157:describe('readIndex', () => {
tests/lib/storage/supabase-metadata-store.test.ts:161:    const idx = await store.readIndex(p);
tests/lib/storage/supabase-metadata-store.test.ts:173:    const idx = await store.readIndex(p);
tests/lib/storage/supabase-metadata-store.test.ts:190:    const idx = await store.readIndex(p);
tests/lib/storage/supabase-metadata-store.test.ts:240:// claimVideoSlot
tests/lib/storage/supabase-metadata-store.test.ts:242:describe('claimVideoSlot', () => {
tests/lib/storage/supabase-metadata-store.test.ts:249:    const result = await store.claimVideoSlot(p, 'vid1');
tests/lib/storage/supabase-metadata-store.test.ts:260:    await expect(store.claimVideoSlot(p, 'vid1')).rejects.toThrow('playlist not found');
tests/lib/storage/supabase-metadata-store.test.ts:265:// upsertVideo
tests/lib/storage/supabase-metadata-store.test.ts:267:describe('upsertVideo', () => {
tests/lib/storage/supabase-metadata-store.test.ts:274:    await store.upsertVideo(p, video);
tests/lib/storage/supabase-metadata-store.test.ts:289:    // Simulates a Video sourced from readIndex(), which surfaces updatedAt.
tests/lib/storage/supabase-metadata-store.test.ts:291:    await store.upsertVideo(p, video);
tests/lib/storage/supabase-metadata-store.test.ts:304:    // Simulates a Video sourced from readIndex(), which surfaces both
tests/lib/storage/supabase-metadata-store.test.ts:307:    await store.upsertVideo(p, video);
tests/lib/storage/supabase-metadata-store.test.ts:318:// updateVideoFields
tests/lib/storage/supabase-metadata-store.test.ts:320:describe('updateVideoFields', () => {
tests/lib/storage/supabase-metadata-store.test.ts:321:  test('calls merge_video_data RPC with correct args', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:326:    await store.updateVideoFields(p, 'vid1', { summaryMd: 'hello' } as any);
tests/lib/storage/supabase-metadata-store.test.ts:327:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data');
tests/lib/storage/supabase-metadata-store.test.ts:331:    expect((rpc!.args as any).p_fields).toEqual({ summaryMd: 'hello' });
tests/lib/storage/supabase-metadata-store.test.ts:339:    await store.updateVideoFields(p, 'vid1', {
tests/lib/storage/supabase-metadata-store.test.ts:343:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data');
tests/lib/storage/supabase-metadata-store.test.ts:355:  test('calls merge_video_data_bulk with mapped { video_id, fields } shape', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:361:      { videoId: 'vid1', fields: { summaryMd: 'a' } as any },
tests/lib/storage/supabase-metadata-store.test.ts:362:      { videoId: 'vid2', fields: { summaryMd: 'b' } as any },
tests/lib/storage/supabase-metadata-store.test.ts:365:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
tests/lib/storage/supabase-metadata-store.test.ts:369:      { video_id: 'vid1', fields: { summaryMd: 'a' } },
tests/lib/storage/supabase-metadata-store.test.ts:370:      { video_id: 'vid2', fields: { summaryMd: 'b' } },
tests/lib/storage/supabase-metadata-store.test.ts:380:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
tests/lib/storage/supabase-metadata-store.test.ts:390:      { videoId: 'vid1', fields: { summaryMd: 'a', updatedAt: '2026-01-01T00:00:00Z' } as any },
tests/lib/storage/supabase-metadata-store.test.ts:391:      { videoId: 'vid2', fields: { summaryMd: 'b', updatedAt: '2026-01-02T00:00:00Z' } as any },
tests/lib/storage/supabase-metadata-store.test.ts:394:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
tests/lib/storage/supabase-metadata-store.test.ts:398:      { video_id: 'vid1', fields: { summaryMd: 'a' } },
tests/lib/storage/supabase-metadata-store.test.ts:399:      { video_id: 'vid2', fields: { summaryMd: 'b' } },
tests/lib/storage/supabase-metadata-store.test.ts:525:  test('readIndex throws when playlist query fails', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:528:    await expect(store.readIndex(p)).rejects.toThrow('DB error');
tests/lib/storage/supabase-metadata-store.test.ts:531:  test('claimVideoSlot throws on RPC error', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:537:    await expect(store.claimVideoSlot(p, 'vid1')).rejects.toThrow('rpc failed');
tests/lib/supabase/env.test.ts:27:    delete process.env.SUPABASE_SERVICE_ROLE_KEY;
tests/lib/supabase/env.test.ts:28:    expect(() => getServiceRoleKey()).toThrow(/SUPABASE_SERVICE_ROLE_KEY/);
tests/lib/supabase/env.test.ts:31:  it('getServiceRoleKey returns the key when SUPABASE_SERVICE_ROLE_KEY is set', () => {
tests/lib/supabase/env.test.ts:32:    process.env.SUPABASE_SERVICE_ROLE_KEY = 'svc-abc';
lib/storage/metadata-store.ts:17:  readIndex(p: Principal): Promise<PlaylistIndex>;
lib/storage/metadata-store.ts:19:  claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }>;
lib/storage/metadata-store.ts:20:  upsertVideo(p: Principal, video: Video): Promise<void>;
lib/storage/metadata-store.ts:21:  updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
lib/storage/metadata-store.ts:25:   *  Used to roll back a claimVideoSlot reservation when pipeline processing fails. */
lib/storage/metadata-store.ts:43:   *  owner_id = auth.uid() guard server-side, in SQL (update_video_annotations RPC) —
lib/storage/metadata-store.ts:44:   *  this is a distinct write path from updateVideoFields/merge_video_data, which is
lib/storage/worker-persistence.ts:16:/** Thin wrapper over the persist_summary RPC (Task 2). Merges `video` into
lib/storage/worker-persistence.ts:17: *  the row's data and stamps the summaryMd artifact status. */
lib/storage/worker-persistence.ts:20:  video: Partial<Video>, status: 'committed' | 'promoted',
lib/storage/worker-persistence.ts:22:  const { error } = await client.rpc('persist_summary', {
tests/lib/html-doc/batch.test.ts:20:const mockReadIndex = jest.mocked(indexStore.readIndex);
tests/lib/html-doc/batch.test.ts:32:    overallScore: 3, summaryMd: `${id}.md`,
tests/lib/html-doc/batch.test.ts:130:    indexWith([v('x', { summaryHtml: null, summaryMd: 'x.md', digDeeperMd: null })]);
tests/lib/html-doc/batch.test.ts:143:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' })]);
tests/lib/html-doc/batch.test.ts:154:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
tests/lib/html-doc/batch.test.ts:164:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md' })]);
tests/lib/html-doc/batch.test.ts:173:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
tests/lib/html-doc/batch.test.ts:185:      v('bad', { summaryHtml: 'bad.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'bad.md', digDeeperMd: null }),
tests/lib/html-doc/batch.test.ts:186:      v('ok', { summaryHtml: 'ok.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'ok.md', digDeeperMd: null }),
tests/lib/html-doc/build-doc-html.test.ts:16:    overallScore: 4, summaryMd: 'a.md', summaryHtml: null,
tests/lib/html-doc/build-doc-html.test.ts:71:    const r = await buildDocHtml(video({ summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');

codex
The branch has unrelated dirty files, so I’ll leave those alone and treat `255b80e` as the review target. The initial search is broad; next I’m narrowing to the implementation files and migration body where cross-task assumptions actually meet.
exec
/bin/bash -lc "sed -n '1,300p' lib/cloud-sync/reconcile-class-b.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "sed -n '1,260p' lib/cloud-sync/reconcile-class-a.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { FieldState, HumanField, HumanSnapshot, VideoBaseline } from './types';

export interface FieldMerge {
  winner: 'local' | 'cloud' | 'equal';
  value: string | number | undefined;
  editedAt: string | undefined;
  conflict: boolean;
}

type Baseline = { value?: string | number; editedAt?: string };

/** Changed vs baseline is over the (value, editedAt) PAIR, not value alone (§5.4). */
function changed(side: FieldState, base: Baseline): boolean {
  return side.value !== base.value || side.editedAt !== base.editedAt;
}

function newer(a: string | undefined, b: string | undefined): boolean {
  // returns true when a is strictly newer than b; undefined sorts oldest
  return (a ?? '') > (b ?? '');
}

export function reconcileField(local: FieldState, cloud: FieldState, baseline: Baseline): FieldMerge {
  // Equal VALUES never conflict (§5.4 row 1). But if their per-field timestamps differ, CONVERGE:
  // return the newer-timestamp side as a NON-conflicting winner so the older side's editedAt is
  // written forward and both replicas end identical — returning 'equal' here would skip the write
  // and leave baseline/live timestamp drift (round-2 H1). Truly-equal pair → 'equal' (no write).
  if (local.value === cloud.value) {
    if (local.editedAt === cloud.editedAt) {
      return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: false };
    }
    return newer(local.editedAt, cloud.editedAt)
      ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false }
      : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };
  }
  const lChanged = changed(local, baseline);
  const cChanged = changed(cloud, baseline);

  if (lChanged && !cChanged) return { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false };
  if (cChanged && !lChanged) return { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };

  // both changed (or neither vs an absent baseline but values differ) → newer per-field ts wins.
  // A backfilled timestamp must never drive a destructive overwrite (§5.5) → conflict skip.
  if (local.backfilled || cloud.backfilled) {
    return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: true };
  }
  const localWins = newer(local.editedAt, cloud.editedAt);
  return localWins
    ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: true }
    : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: true };
}

const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];

export function reconcileHuman(
  local: HumanSnapshot,
  cloud: HumanSnapshot,
  baseline: VideoBaseline['classB'],
): Record<HumanField, FieldMerge> {
  const out = {} as Record<HumanField, FieldMerge>;
  for (const f of FIELDS) out[f] = reconcileField(local[f], cloud[f], baseline[f] ?? {});
  return out;
}

 succeeded in 0ms:
import type { ClassASignals } from './types';

export interface ClassADecision {
  action: 'skip' | 'copyToLocal' | 'copyToCloud';
  needsRegen: boolean;
}

const current = (s: ClassASignals, cur: string): boolean => s.mdCorrectionsHash === cur;
const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');

export function reconcileClassA(args: {
  local: ClassASignals;
  cloud: ClassASignals;
  reconciledCorrectionsHash: string;
}): ClassADecision {
  const { local, cloud, reconciledCorrectionsHash: cur } = args;
  const lHas = local.mdHash != null;
  const cHas = cloud.mdHash != null;

  // Presence (§5.6 one-sided copy) — flag needsRegen when the SOLE MD is corrections-stale (R8, L2)
  if (!lHas && !cHas) return { action: 'skip', needsRegen: false };
  if (!lHas) return { action: 'copyToLocal', needsRegen: !current(cloud, cur) };
  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };

  const lCur = current(local, cur);
  const cCur = current(cloud, cur);
  const bothStale = !lCur && !cCur;

  // Equal MD bodies: skip ONLY when both corrections-current, OR both stale AND same format.
  // If currency OR format disagrees (even with identical bytes), fall through so the winning
  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
  if (local.mdHash === cloud.mdHash) {
    if (lCur && cCur) return { action: 'skip', needsRegen: false };
    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
    // else: fall through to currency/format below.
  }

  // corrections-currency FIRST (a stale MD never overwrites a corrections-current one)
  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
  if (cCur && !lCur) return { action: 'copyToLocal', needsRegen: false };

  // format (never downgrade)
  if (local.docVersionMajor !== cloud.docVersionMajor) {
    const winnerIsCloud = cloud.docVersionMajor > local.docVersionMajor;
    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
  }

  // same major, different mdHash → recency-tiebreak (unify prose)
  const winnerIsLocal = newer(local.mdGeneratedAt, cloud.mdGeneratedAt);
  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
}

exec
/bin/bash -lc "sed -n '1,260p' lib/cloud-sync/sync-run.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
import { decideCompanion } from './companion';
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

/** Resolve the playlist url/title for `key` from whichever registry holds it. */
function playlistMetaFor(
  key: string, localPlaylists: LocalPlaylist[], cloudSummaries: PlaylistSummary[],
): { playlistUrl: string; playlistTitle?: string } {
  const lp = localPlaylists.find((l) => l.playlistKey === key);
  if (lp) return { playlistUrl: lp.playlistUrl };
  const cp = cloudSummaries.find((c) => c.playlistKey === key);
  if (cp) return { playlistUrl: cp.playlistUrl, ...(cp.playlistTitle ? { playlistTitle: cp.playlistTitle } : {}) };
  return { playlistUrl: '' };
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
  await to.setPlaylistMeta(toP, playlistMeta);
  const idx = await to.readIndex(toP);
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
  }
  await to.upsertVideo(toP, sanitized as Video);

  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
  // (an update against an absent row silently no-ops; never advance a baseline for that).
  const after = await to.readIndex(toP);
  if (!after.videos.some((v) => v.id === video.id)) {
    throw new Error(`additive create did not persist receiver row for ${video.id}`);
  }
}

/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
 *  side's values, so this is a true agreed baseline. */
function baselineFromOneSided(
  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
): VideoBaseline {
  const classB = {} as VideoBaseline['classB'];
  for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
  return {
    classA: {
      docVersionMajor: classA.docVersionMajor,
      mdGeneratedAt: classA.mdGeneratedAt,
      mdCorrectionsHash: classA.mdCorrectionsHash,
      mdHash: mdHashVal,
    },
    classB,
  };
}

/** Behaviors #12 + F3 — apply each Class-B winner to the LOSER side, carrying the SOURCE timestamp
 *  (never now()). A conflict is logged and, when the merge picked no winner (winner==='equal'), the
 *  loser value is skipped (not written). Every write MUST land (found:true) or it throws — a no-op
 *  write on an absent row would let buildBaseline record a false agreement. */
async function applyClassBWinners(args: {
  deps: SyncDeps; localP: Principal; cloudP: Principal; videoId: string;
  merges: Record<HumanField, FieldMerge>; localSnap: HumanSnapshot; cloudSnap: HumanSnapshot;
  dataRoot: string; key: string;
}): Promise<{ merged: number; conflicts: number }> {
  const { deps, localP, cloudP, videoId, merges, localSnap, cloudSnap, dataRoot, key } = args;
  let merged = 0;
  let conflicts = 0;

  for (const f of FIELDS) {
    const m = merges[f];
    if (m.conflict) {
      await appendConflict(dataRoot, key, {
        video_id: videoId, class: 'B', field: f,
        valueL: localSnap[f].value, valueR: cloudSnap[f].value,
        reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
      });
      conflicts += 1;
    }
    if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write

    // winner is on one side → the OTHER (loser) side receives the winning value.
    const target: Side = m.winner === 'local'
      ? { store: deps.cloud, p: cloudP, blob: deps.cloudBlob }
      : { store: deps.local, p: localP, blob: deps.localBlob };
    const set: Record<string, string | number> = {};
    const clear: HumanField[] = [];
    if (m.value === undefined) clear.push(f);
    else set[f] = m.value;

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

exec
/bin/bash -lc "sed -n '1,260p' lib/cloud-sync/companion.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { ModelEnvelope } from '@/lib/html-doc/model-store';

export type CompanionAction =
  | { kind: 'ship'; envelope: ModelEnvelope }
  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true };

/** Ship the sender's model iff it was generated from the winning MD (§4.2). */
export function decideCompanion(args: {
  winnerMdHash: string;
  senderEnvelope: ModelEnvelope | null;
}): CompanionAction {
  const { winnerMdHash, senderEnvelope } = args;
  if (senderEnvelope && senderEnvelope.sourceMdHash === winnerMdHash) {
    return { kind: 'ship', envelope: senderEnvelope };
  }
  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
}

codex
The main orchestrator has the expected guardrails in comments and several verify-after-write checks. I’m going to inspect the remaining half of `sync-run.ts` now, because baseline advancement and companion handling are where an otherwise correct transfer can still become unsafe. 

exec
/bin/bash -lc "sed -n '260,620p' lib/cloud-sync/sync-run.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
    artifacts: { summaryMd: { key, status: 'promoted' } },
  };
  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);

  return { mdHash: h, verified: true };
}

/** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
 *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
 *  that the owner must re-serve to regenerate the share model. */
async function companionTransfer(
  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
): Promise<{ shareNeedsOwnerServe: boolean }> {
  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
  const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
  const decision = decideCompanion({ winnerMdHash, senderEnvelope });
  if (decision.kind === 'ship') {
    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
    return { shareNeedsOwnerServe: false };
  }
  // deleteReceiverModel — best-effort; a missing model blob is not an error.
  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
  return { shareNeedsOwnerServe: true };
}

/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
 *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
 *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
 *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
 *  recording the winner there would be a false agreement → next-run silent overwrite). */
function buildBaseline(
  winnerSignals: ClassASignals, winnerMdHash: string | null,
  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
): VideoBaseline {
  const classB = {} as VideoBaseline['classB'];
  for (const f of FIELDS) {
    const m = merges[f];
    if (m.winner === 'equal' && m.conflict) {
      classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
    } else {
      classB[f] = { value: m.value, editedAt: m.editedAt };
    }
  }
  return {
    classA: {
      docVersionMajor: winnerSignals.docVersionMajor,
      mdGeneratedAt: winnerSignals.mdGeneratedAt,
      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
      mdHash: winnerMdHash,
    },
    classB,
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

        // ── Class A (needs the MD bodies for hashing — Behavior #1).
        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
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

exec
/bin/bash -lc "sed -n '1,260p' lib/cloud-sync/backfill.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { Video } from '@/types';
import type { ClassASignals, HumanSnapshot, HumanField, FieldState } from './types';
import { mdHash } from './content-hash';

// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
  const hasReal = video.mdGeneratedAt != null;
  return {
    summaryMdKey: video.summaryMd ?? null,
    mdHash: mdBody != null ? mdHash(mdBody) : null,
    docVersionMajor: video.docVersion?.major ?? 1,
    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
    backfilled: !hasReal,
  };
}

const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];

export function deriveHumanSnapshot(video: Video): HumanSnapshot {
  const provisional = video.updatedAt ?? video.processedAt;
  const out = {} as HumanSnapshot;
  for (const f of FIELDS) {
    const value = video[f] as string | number | undefined;
    const real = video.annotationsEditedAt?.[f];
    const state: FieldState<string | number> = value === undefined && real === undefined
      ? { value: undefined, editedAt: undefined, backfilled: false }
      : { value, editedAt: real ?? provisional, backfilled: real === undefined };
    out[f] = state;
  }
  return out;
}

exec
/bin/bash -lc "sed -n '1,320p' lib/cloud-sync/manifest.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
// lib/cloud-sync/manifest.ts
import { promises as fs } from 'fs';
import path from 'path';
import type { VideoBaseline } from './types';

export interface Manifest { version: 1; videos: Record<string, VideoBaseline>; }

export function manifestPath(dataRoot: string, playlistKey: string): string {
  return path.join(dataRoot, playlistKey, '.cloud-sync-manifest.json');
}
function conflictPath(dataRoot: string, playlistKey: string): string {
  return path.join(dataRoot, playlistKey, '.cloud-sync-conflicts.log');
}

export async function readManifest(dataRoot: string, playlistKey: string): Promise<Manifest> {
  try {
    const raw = await fs.readFile(manifestPath(dataRoot, playlistKey), 'utf8');
    const parsed = JSON.parse(raw);
    if (parsed && parsed.version === 1 && parsed.videos) return parsed as Manifest;
  } catch { /* missing or corrupt → degrade (§8) */ }
  return { version: 1, videos: {} };
}

async function atomicWrite(file: string, data: string): Promise<void> {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp-${process.pid}`;
  await fs.writeFile(tmp, data, 'utf8');
  await fs.rename(tmp, file);
}

export async function writeVideoBaseline(
  dataRoot: string, playlistKey: string, videoId: string, baseline: VideoBaseline,
): Promise<void> {
  const m = await readManifest(dataRoot, playlistKey);
  m.videos[videoId] = baseline;
  await atomicWrite(manifestPath(dataRoot, playlistKey), JSON.stringify(m, null, 2));
}

const seenConflicts = new Set<string>();
export interface ConflictEntry {
  video_id: string; class: 'A' | 'B'; field?: string;
  valueL?: unknown; valueR?: unknown; reason: string;
}
export async function appendConflict(dataRoot: string, playlistKey: string, e: ConflictEntry): Promise<void> {
  // Include playlistKey so the same (video_id, class, field, valueL, valueR) in two playlists
  // within one run is not collapsed to a single entry (L3).
  const key = `${playlistKey}|${e.video_id}|${e.class}|${e.field ?? ''}|${JSON.stringify(e.valueL)}|${JSON.stringify(e.valueR)}`;
  if (seenConflicts.has(key)) return;
  seenConflicts.add(key);
  const file = conflictPath(dataRoot, playlistKey);
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.appendFile(file, `${JSON.stringify(e)}\n`, 'utf8');
}
/** Reset the per-run de-dup cache at the start of a sync run. */
export function resetConflictDedup(): void { seenConflicts.clear(); }

exec
/bin/bash -lc "sed -n '1,220p' lib/cloud-sync/content-hash.ts && sed -n '1,240p' lib/cloud-sync/types.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import { createHash } from 'crypto';

/**
 * Canonical MD-body normalization for cross-backend hashing (§5.2):
 * LF line endings + exactly one trailing newline + Unicode NFC.
 * Local-file storage (may carry CRLF / trailing blank lines) and Postgres
 * jsonb storage (LF only) must produce byte-identical output here.
 */
export function canonicalizeMd(md: string): string {
  const lf = md.replace(/\r\n?/g, '\n');
  const trimmed = lf.replace(/\n+$/, '');
  return `${trimmed.normalize('NFC')}\n`;
}

/** SHA-256 hex of the canonicalized MD body (§5.2). NOT over human fields. */
export function mdHash(md: string): string {
  return createHash('sha256').update(canonicalizeMd(md), 'utf8').digest('hex');
}
import type { Video } from '@/types';

/** The generated-content (Class A) signals for one video on one replica (§5.1). */
export interface ClassASignals {
  summaryMdKey: string | null;    // the blob KEY (video.summaryMd) — NOT the body
  mdHash: string | null;          // SHA-256 of the MD BODY (read from the blob by the caller); null when no MD
  docVersionMajor: number;        // 1 when docVersion absent (pre-feature)
  mdGeneratedAt: string | null;   // tie-break only
  mdCorrectionsHash: string | null;
  backfilled: boolean;            // mdGeneratedAt is provisional (§5.5)
}

/** The companion scalars carried verbatim with a winning MD (§4.1). */
export type CompanionScalars = Pick<
  Video,
  'ratings' | 'overallScore' | 'videoType' | 'audience' | 'tags' | 'tldr' | 'takeaways'
>;

export type HumanField = 'personalNote' | 'personalScore' | 'corrections';

/** One human field's (value, per-field timestamp) state (§5.4). Absence-as-value: value===undefined is a clear. */
export interface FieldState<T = string | number> {
  value: T | undefined;
  editedAt: string | undefined;   // per-field annotationsEditedAt
  backfilled: boolean;            // editedAt is provisional (§5.5)
}

export type HumanSnapshot = Record<HumanField, FieldState<string | number>>;

/** Manifest baseline for one video (§8). */
export interface VideoBaseline {
  classA: { docVersionMajor: number; mdGeneratedAt: string | null; mdCorrectionsHash: string | null; mdHash: string | null };
  classB: Record<HumanField, { value: string | number | undefined; editedAt: string | undefined }>;
}

codex
So far, the Class-B no-write conflict baseline rule is implemented as specified, and one-sided videos exit before two-sided reconciliation. I’m checking the model/hash writers and storage stores next, because consistency issues there can make the orchestrator compare the right values against the wrong underlying bytes.
exec
/bin/bash -lc "sed -n '1,260p' lib/html-doc/generate.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import { assertVideoId } from '../index-store';
import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
import { generateMagazineModel } from '../gemini';
import { parseSummaryMarkdown } from './parse';
import { renderMagazineHtml, GENERATOR_VERSION } from './render';
import { writeModelEnvelope } from './model-store';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { ProgressEvent } from '../../types';

export async function runHtmlDoc(
  videoId: string,
  outputFolder: string,
  onProgress: (event: ProgressEvent) => void,
  blobStore?: BlobStore,
): Promise<void> {
  const principal = getPrincipal(outputFolder);
  const { metadataStore: store, blobStore: bundleBlob } = getStorageBundle();
  const resolvedBlob = blobStore ?? bundleBlob;
  assertVideoId(videoId);

  const index = await store.readIndex(principal);
  const video = index.videos.find((v) => v.id === videoId);
  if (!video) throw new Error(`Video not found in index: ${videoId}`);
  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');

  onProgress({ type: 'start' });
  onProgress({ type: 'step', videoId, step: 'Reading summary…', current: 1, total: 3 });

  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
  if (!mdBytes) {
    throw new Error(`source note not found on disk: ${video.summaryMd}`);
  }
  const md = mdBytes.toString('utf-8');

  const parsed = parseSummaryMarkdown(md);
  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field

  onProgress({ type: 'step', videoId, step: 'Transforming to skim view…', current: 2, total: 3 });
  const model = await generateMagazineModel(
    parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
    video.language,
  );

  // Persist the model so future style changes can re-render offline (no Gemini). `sourceSections`
  // captures the section titles the model was built against — the re-render drift guard.
  // A later HTML/index failure may leave this model as an orphan; that's intentional and harmless —
  // re-render is gated on summaryHtml (set only on full success), and a retry overwrites it atomically.
  const base = video.summaryMd.replace(/\.md$/, '');
  await writeModelEnvelope(principal, base, {
    sourceMd: video.summaryMd,
    generatedAt: new Date().toISOString(),
    sourceSections: parsed.sections.map((s) => s.title),
    generatorVersion: GENERATOR_VERSION,
    model,
    // Stage 3 (§4.2): hash the MD BODY (`md`, line ~33), NOT `sourceMd`/`video.summaryMd`
    // (the blob key/filename) — decideCompanion (Task 8) compares against mdHash(body); a
    // filename-hash would never match and every synced companion would be deleted.
    sourceMdHash: mdHash(md),
  }, resolvedBlob);

  onProgress({ type: 'step', videoId, step: 'Rendering HTML…', current: 3, total: 3 });
  const html = renderMagazineHtml(parsed, model);

  const htmlFilename = `htmls/${base}.html`;

  // Atomic write via resolvedBlob (LocalFsBlobStore uses temp+rename; cloud impls upload directly).
  // Codex HIGH: if the index update fails, remove the just-written file so we don't leave an
  // orphan HTML the index doesn't reference (keeps cache ↔ index consistent).
  await resolvedBlob.put(principal, htmlFilename, Buffer.from(html, 'utf-8'), 'text/html');
  try {
    await store.updateVideoFields(principal, videoId, { summaryHtml: htmlFilename });
  } catch (err) {
    await resolvedBlob.delete(principal, htmlFilename).catch(() => { /* ignore cleanup error */ });
    throw err;
  }
  onProgress({ type: 'done' });
}

exec
/bin/bash -lc "sed -n '1,240p' lib/html-doc/serve-doc.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import type { ParsedSummary, MagazineModel } from './types';
import { GENERATOR_VERSION } from './constants';
import { writeModelEnvelope } from './model-store';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { readFreshMagazineModel, readTitleStableModel } from './read-model';
import { generateMagazineModel } from '@/lib/gemini';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';
import { classifyGeminiFailure, releaseGateOpen } from '@/lib/gemini-failure';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import {
  MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS, MAX_MAGAZINE_INPUT_TOKENS, MAX_MAGAZINE_OUTPUT_TOKENS,
} from '@/lib/gemini-cost';

/** Serve-side caps for the paid magazine transform (only the magazine fields are load-bearing;
 *  the rest satisfy the CloudGeminiCaps type). */
const SERVE_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
  magazineInputTokens: MAX_MAGAZINE_INPUT_TOKENS,
  magazineOutputTokens: MAX_MAGAZINE_OUTPUT_TOKENS,
};

export type ResolveResult =
  | { status: 'ok'; model: MagazineModel; stale?: boolean }
  | { status: 'busy' }
  | { status: 'attempts_exhausted' }
  | { status: 'at_capacity' }
  | { status: 'over_budget' }
  | { status: 'denied' };

export async function resolveMagazineModel(args: {
  supabaseClient: SupabaseClient;
  blobStore: BlobStore;
  principal: Principal;
  playlistId: string;
  videoId: string;
  base: string;
  parsed: ParsedSummary;
  language: 'en' | 'ko';
  /** Stage 3 (§4.2): the MD BODY this model is generated from (NOT the blob key) — hashed
   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
   *  real production caller (serve-summary-core.ts) always supplies it. */
  mdBody?: string;
  signal?: AbortSignal;
}): Promise<ResolveResult> {
  const { supabaseClient, blobStore, principal, playlistId, videoId, base, parsed, language, mdBody, signal } = args;
  const titles = parsed.sections.map((s) => s.title);

  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve

  // Absent / drifted / stale-version → materialize under the reserve RPC.
  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
    p_playlist_id: playlistId, p_video_id: videoId,
  });
  if (error) throw error;
  const row = (data as Array<{ status: string; release_token: string | null }> | null)?.[0];   // table-return → data[0]
  const reserveStatus = row?.status;
  const releaseToken = row?.release_token ?? null;
  switch (reserveStatus) {
    case 'denied': return { status: 'denied' };
    case 'in_flight': {
      // Single-flight: another attempt holds the lease. Serve the model if it landed meanwhile, else busy.
      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
      return now.status === 'ok' ? now : { status: 'busy' };
    }
    case 'attempts_exhausted': return { status: 'attempts_exhausted' };
    case 'at_capacity': return { status: 'at_capacity' };
    case 'owner_over_budget': {
      // Spec D5: serve the title-stable stale rendering instead of failing; else 503.
      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
      return staleRead.status === 'ok'
        ? { status: 'ok', model: staleRead.model, stale: true }
        : { status: 'over_budget' };
    }
    case 'reserved': break;
    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
  }

  // We hold the lease and this attempt was charged. Generate → upsert (overwrite) → serve.
  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
  // regenerated model on drift / version-bump must OVERWRITE the stale blob so the doc self-heals
  // (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).
  // On a terminal outcome (success or throw) we settle the reservation via settle_serve_model: success
  // keeps the charge (released=false) and clears the per-attempt token; a throw refunds ONLY a
  // positively-not-metered class-A failure under an open gate — same rule as the generation worker-runner
  // (Task 10). Anything else (metered, non-class-A, gate closed) keeps the charge — over-count is safe,
  // under-count is the bug.
  const billing: BillingLatch = { metered: false };
  try {
    const model = await generateMagazineModel(
      parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
      language,
      { caps: SERVE_CAPS, signal, billing },
    );
    await writeModelEnvelope(principal, base, {
      sourceMd: parsed.sourceMd ?? `${base}.md`,
      generatedAt: new Date().toISOString(),
      sourceSections: titles,
      generatorVersion: GENERATOR_VERSION,
      model,
      // Hash the MD BODY, not the key — see the `mdBody` param doc above (§4.2).
      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
    }, blobStore);
    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: false });
    return { status: 'ok', model };
  } catch (err) {
    // Same rule as generation: refund only a positively-not-metered class-A failure.
    const released = releaseGateOpen()
      && classifyGeminiFailure(err, signal) === 'release'
      && !billing.metered;
    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: released });
    throw err;
  }
}

exec
/bin/bash -lc "sed -n '1,260p' lib/html-doc/model-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import { z } from 'zod';
import { MagazineModelSchema } from './types';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import type { BlobStore, ReadOnlyBlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

/**
 * The persisted summary-model file: the Gemini transform output plus provenance.
 * `sourceSections` is the section titles the model was built against — the drift guard the
 * re-render path compares the current .md's section titles against.
 * `generatorVersion` is optional so pre-1F-a local envelopes (written before this field existed)
 * still parse; the cloud freshness gate requires it to `=== GENERATOR_VERSION`.
 */
export const ModelEnvelopeSchema = z
  .object({
    sourceMd: z.string().min(1),
    generatedAt: z.string().min(1),
    sourceSections: z.array(z.string()),
    generatorVersion: z.string().min(1).optional(),
    model: MagazineModelSchema,
    // Stage 3 (§4.2): MD-body-only digest of the MD this model was generated from.
    sourceMdHash: z.string().optional(),
  });
  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
  // must not make an old reader's readModelEnvelope return null (§5.7 round-5 M-2).

export type ModelEnvelope = z.infer<typeof ModelEnvelopeSchema>;

const MODEL_KEY = (base: string) => `models/${base}.json`;

function serialize(envelope: ModelEnvelope): Buffer {
  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
}

/**
 * The single model writer for BOTH the local generate path and the cloud serve path.
 * `put` maps to Supabase `upload(upsert:true)` (atomic per object), so a re-generated model on
 * drift / `generatorVersion` bump OVERWRITES the prior blob — the cache self-heals rather than
 * getting stuck on a stale envelope. (The staged→promote protocol is create-if-absent and stays
 * on the BlobStore for the worker's multi-blob MD commit — it is NOT used for the model.)
 */
export async function writeModelEnvelope(
  principal: Principal,
  base: string,
  envelope: ModelEnvelope,
  blobStore: BlobStore = localBlobStore,
): Promise<void> {
  await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
}

/** Read + validate. Returns null if absent, unparseable, or schema-invalid. */
export async function readModelEnvelope(
  principal: Principal,
  base: string,
  blobStore: ReadOnlyBlobStore = localBlobStore,
): Promise<ModelEnvelope | null> {
  const bytes = await blobStore.get(principal, MODEL_KEY(base));
  if (!bytes) return null;
  let json: unknown;
  try {
    json = JSON.parse(bytes.toString('utf-8'));
  } catch {
    console.warn(`[model-store] malformed JSON in models/${base}.json — ignoring`);
    return null;
  }
  const parsed = ModelEnvelopeSchema.safeParse(json);
  if (!parsed.success) {
    console.warn(`[model-store] models/${base}.json failed schema validation — ignoring`);
    return null;
  }
  return parsed.data;
}

exec
/bin/bash -lc "sed -n '1,260p' lib/html-doc/serve-summary-core.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { SupabaseClient } from '@supabase/supabase-js';
import { getStorageBundle, getPrincipalFromSession, type StorageBundle } from '@/lib/storage/resolve';
import { resolveOwnedPlaylistKey } from '@/lib/storage/serve-playlist';
import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import type { Principal } from '@/lib/storage/principal';
import type { Video } from '@/types';

export type LoadResult =
  | {
      ok: true;
      mdBytes: Buffer;
      mdKey: string;
      base: string;
      title?: string;
      principal: Principal;
      playlistId: string;
      video: Video;
      bundle: StorageBundle;
    }
  | { ok: false; status: number; error: string };

/**
 * Two-stage split of `serveCloud`'s gate→read→resolve→render core (app/api/html/[id]/route.ts),
 * split at the `resolveMagazineModel` boundary so both the HTML route (Task 7) and the PDF route
 * (Task 8) can share it while the `format=md` no-charge short-circuit survives (D4 money invariant:
 * the md path must read the blob and return WITHOUT ever calling resolveMagazineModel).
 *
 * Mirrors serveCloud lines ~45-83. Does NOT resolve/charge — that is stage 2 (resolveAndParse).
 * Note: assertVideoId is done by the CALLER route in param validation (before auth, preserving the
 * existing 400-before-401 ordering) — this helper does not repeat it.
 */
export async function loadSummaryForServe(
  supabase: SupabaseClient,
  a: { videoId: string; playlistId: string; userId: string },
): Promise<LoadResult> {
  const playlistKey = await resolveOwnedPlaylistKey(supabase, a.playlistId, a.userId); // owner-asserted (D6/D9)
  if (!playlistKey) return { ok: false, status: 404, error: 'not found' };

  const principal = getPrincipalFromSession({ userId: a.userId }, playlistKey);
  const bundle = getStorageBundle({ supabaseClient: supabase }); // session-scoped, RLS-enforced (D5)
  const index = await bundle.metadataStore.readIndex(principal);
  const video = index.videos.find((v) => v.id === a.videoId) as Video | undefined;
  if (!video) return { ok: false, status: 404, error: 'not found' };

  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
    .artifacts?.summaryMd;
  const status = artifact?.status;
  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)

  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
  // doesn't govern).
  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
  if (!mdKey) return { ok: false, status: 404, error: 'not found' };

  // Task-2 guard: reject a corrupt/nested key BEFORE reading the blob (409, no blob fetch attempted).
  try {
    assertCloudSummaryMdKey(mdKey);
  } catch {
    return { ok: false, status: 409, error: 'corrupt summary key' };
  }

  const mdBytes = await bundle.blobStore.get(principal, mdKey);
  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)

  // IDENTITY COHERENCE (carried from serveCloud): `base` is the canonical, DB-persisted baseName,
  // derived deterministically from the SAME summaryMd key the model store is keyed on.
  const base = mdKey.replace(/\.md$/, '');

  // M1 (1F-c whole-branch review): coerce a non-string/blank title to undefined defensively.
  const rawTitle: unknown = (video as unknown as { title?: unknown }).title;
  const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;

  return { ok: true, mdBytes, mdKey, base, title, principal, playlistId: a.playlistId, video, bundle };
}

type OkLoad = Extract<LoadResult, { ok: true }>;

// The resolved magazine model, typed straight off resolveMagazineModel's `ok` arm so Task 7/8
// consumers get the real MagazineModel contract instead of `unknown`. (Task-6 review Minor.)
type ResolvedModel = Extract<Awaited<ReturnType<typeof resolveMagazineModel>>, { status: 'ok' }>['model'];

export type ResolveAndParseResult =
  | { ok: true; parsed: ReturnType<typeof parseSummaryMarkdown>; model: ResolvedModel; stale: boolean }
  | { ok: false; status: number; error: string };

/**
 * Stage 2: parse the markdown + resolve (and possibly charge for) the magazine model. Maps
 * `resolveMagazineModel`'s ResolveResult (lib/html-doc/serve-doc.ts:26) to HTTP codes. Error
 * strings below are copied VERBATIM from serveCloud (app/api/html/[id]/route.ts:101-105) — the
 * existing html-download integration tests assert these exact strings. Do NOT paraphrase.
 */
export async function resolveAndParse(
  supabase: SupabaseClient,
  load: OkLoad,
  signal?: AbortSignal,
): Promise<ResolveAndParseResult> {
  const mdBody = load.mdBytes.toString('utf-8');
  const parsed = parseSummaryMarkdown(mdBody);
  parsed.sourceMd = load.mdKey;

  const resolved = await resolveMagazineModel({
    supabaseClient: supabase,
    blobStore: load.bundle.blobStore,
    principal: load.principal,
    playlistId: load.playlistId,
    videoId: load.video.id,
    base: load.base,
    parsed,
    language: load.video.language, // Video.language is already the 'en'|'ko' enum (types/index.ts:51)
    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
    signal,
  });

  switch (resolved.status) {
    case 'denied': return { ok: false, status: 404, error: 'not found' };                                          // generic, no leak
    case 'busy': return { ok: false, status: 503, error: 'generating, retry shortly' };                            // B6b
    case 'attempts_exhausted': return { ok: false, status: 503, error: 'temporarily unavailable, try later' };     // B7f
    case 'at_capacity': return { ok: false, status: 503, error: 'at capacity' };                                   // B6
    case 'over_budget': return { ok: false, status: 503, error: 'daily refresh budget reached, try tomorrow' };    // D6/G1
    case 'ok': return { ok: true, parsed, model: resolved.model, stale: resolved.stale === true };
  }
}

codex
The source model writers all hash the markdown body, not the key, including both local generation and cloud serve materialization. I’m moving into store semantics now, especially `upsertVideo`, annotation stamping, and RPC shape.
exec
/bin/bash -lc "sed -n '1,340p' lib/storage/local/local-metadata-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import * as indexStore from '@/lib/index-store';
import { nextSerial } from '@/lib/serial-assign';

/** Behavior-preserving local impl. Sync index-store calls wrapped in resolved Promises;
 *  the new transactional methods replicate today's pipeline logic against the JSON file. */
export class LocalFsMetadataStore implements MetadataStore {
  async readIndex(p: Principal): Promise<PlaylistIndex> {
    return indexStore.readIndex(p.indexKey);
  }
  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
    const idx = indexStore.readIndex(p.indexKey);
    indexStore.writeIndex(p.indexKey, {
      ...idx,
      playlistUrl: meta.playlistUrl,
      outputFolder: p.indexKey,
      ...(meta.playlistTitle ? { playlistTitle: meta.playlistTitle } : {}),
    });
  }
  async claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }> {
    const idx = indexStore.readIndex(p.indexKey);
    const position = idx.videos.length;
    const serialNumber = nextSerial(idx.videos);
    // reserve the slot with a minimal valid Video; real data arrives via upsertVideo
    indexStore.upsertVideo(p.indexKey, { id: videoId, serialNumber } as Video);
    return { position, serialNumber };
  }
  async upsertVideo(p: Principal, video: Video): Promise<void> {
    indexStore.upsertVideo(p.indexKey, video);
  }
  // Stage 3 (§5.1/§5.7): the PRODUCTION Class-B write path (review + regenerate routes call
  // this, not updateVideoAnnotations — see the allowlist-parity note below). When `fields`
  // carries a Class-B key (set or explicit clear via `undefined`), stamp
  // `annotationsEditedAt.<field>` — user path (no opts) → now(), sync path (opts.editedAt)
  // → the caller-supplied source timestamp. A non-Class-B write (e.g. MD-finalize /
  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
  // NOT bump annotationsEditedAt — those are separate, non-human-edit signals.
  async updateVideoFields(
    p: Principal,
    id: string,
    fields: Partial<Video>,
    opts?: { editedAt?: string },
  ): Promise<void> {
    // NOTE: filters inline against the CLASS_B_ANNOTATION_KEYS constant (not
    // indexStore.classBKeysIn) — callers that `jest.mock('lib/index-store')` (auto-mock,
    // no factory) replace every FUNCTION export with a bare jest.fn(), but a plain array
    // constant survives untouched, so this stays correct under that mocking pattern too.
    const changed = Object.keys(fields).filter((k): k is indexStore.ClassBAnnotationKey =>
      (indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k),
    );
    let toWrite: Partial<Video> = fields;
    if (changed.length > 0) {
      const idx = indexStore.readIndex(p.indexKey);
      const existing = idx.videos.find((v) => v.id === id);
      const editedAt = opts?.editedAt ?? new Date().toISOString();
      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing?.annotationsEditedAt ?? {}) };
      for (const k of changed) at[k] = editedAt;
      toWrite = { ...fields, annotationsEditedAt: at };
    }
    indexStore.updateVideoFields(p.indexKey, id, toWrite);
  }
  async bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void> {
    for (const { videoId, fields } of patches) indexStore.updateVideoFields(p.indexKey, videoId, fields);
  }
  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    const idx = indexStore.readIndex(p.indexKey);
    const filtered = idx.videos.filter((v) => v.id !== videoId);
    if (filtered.length === idx.videos.length) return; // id not present — no-op
    indexStore.writeIndex(p.indexKey, { ...idx, videos: filtered });
  }
  async resolvePlaylistId(): Promise<string> {
    throw new Error('resolvePlaylistId is cloud-only (unsupported on the local backend)');
  }
  async deletePlaylist(): Promise<void> {
    throw new Error('deletePlaylist is cloud-only (unsupported on the local backend)');
  }
  // Local parity for the cloud conditional update (Task 3): fills playlistTitle only
  // when currently absent/null in the JSON index; a no-op otherwise.
  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
    const idx = indexStore.readIndex(p.indexKey);
    if (idx.playlistTitle) return { updated: false };
    indexStore.writeIndex(p.indexKey, { ...idx, playlistTitle: title });
    return { updated: true };
  }
  async listPlaylists(): Promise<PlaylistSummary[]> {
    throw new Error('listPlaylists is cloud-only');
  }
  // Interface-shape parity only — not on a local runtime path (the local review route
  // branch is unchanged and still calls updateVideoFields directly). Allowlist applied
  // in-process (the cloud impl enforces it server-side, in SQL); `undefined` values are
  // dropped by JSON.stringify on write, matching updateVideoFields' existing clear-by-
  // undefined convention (see app/api/videos/[id]/review/route.ts serveLocal).
  //
  // Stage 3 (§5.1/§5.7, round-2 N3): this IS the sync loser-write path for a Class-B field
  // (e.g. corrections) — the allowlist widened to include 'corrections' (was silently
  // dropped), and a set/clear of any Class-B key stamps annotationsEditedAt: user path (no
  // opts) → now(), sync path (opts.editedAt) → the caller-supplied source timestamp.
  async updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
    clear: ('personalScore' | 'personalNote' | 'corrections')[],
    opts?: { editedAt?: string },
  ): Promise<{ found: boolean }> {
    const idx = indexStore.readIndex(p.indexKey);
    const existing = idx.videos.find((v) => v.id === videoId);
    if (!existing) return { found: false };

    const allow = new Set(['personalScore', 'personalNote', 'archived', 'corrections']);
    const fields: Partial<Video> = {};
    const changed: indexStore.ClassBAnnotationKey[] = [];
    for (const [k, v] of Object.entries(set)) {
      if (allow.has(k)) {
        (fields as Record<string, unknown>)[k] = v;
        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
          changed.push(k as indexStore.ClassBAnnotationKey);
        }
      }
    }
    for (const k of clear) {
      if (allow.has(k)) {
        (fields as Record<string, unknown>)[k] = undefined;
        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
          changed.push(k as indexStore.ClassBAnnotationKey);
        }
      }
    }
    if (changed.length > 0) {
      const editedAt = opts?.editedAt ?? new Date().toISOString();
      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing.annotationsEditedAt ?? {}) };
      for (const k of changed) at[k] = editedAt;
      fields.annotationsEditedAt = at;
    }
    indexStore.updateVideoFields(p.indexKey, videoId, fields);
    return { found: true };
  }

  async reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void> {
    const present = new Set(currentPlaylistIds);
    const idx = indexStore.readIndex(p.indexKey);
    for (const v of idx.videos) {
      const inPlaylist = present.has(v.id);
      // Mirror original pipeline logic: only touch videos whose archive state should change.
      // A video with removedFromPlaylist=true that is still absent was already handled on a
      // prior sync (or the user manually un-archived it) — leave it untouched.
      if (!inPlaylist && !v.removedFromPlaylist) {
        indexStore.updateVideoFields(p.indexKey, v.id, { archived: true, removedFromPlaylist: true } as Partial<Video>);
      } else if (inPlaylist && v.removedFromPlaylist) {
        indexStore.updateVideoFields(p.indexKey, v.id, { archived: false, removedFromPlaylist: false } as Partial<Video>);
      }
    }
  }
}

export const localMetadataStore = new LocalFsMetadataStore();

exec
/bin/bash -lc "sed -n '1,300p' lib/index-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import type { PlaylistIndex, Video } from '../types';

const INDEX_FILE = 'playlist-index.json';
const VIDEO_ID_RE = /^[A-Za-z0-9_-]{1,20}$/;

// Stage 3 Cloud Sync (§5.1/§5.7): Class-B ("human-edited") annotation fields — a set or a
// clear of any of these stamps `annotationsEditedAt.<field>` (user path → now(), sync path
// → the caller-supplied source timestamp). Shared by LocalFsMetadataStore's
// updateVideoAnnotations and updateVideoFields so both write paths stamp identically.
export const CLASS_B_ANNOTATION_KEYS = ['personalNote', 'personalScore', 'corrections'] as const;
export type ClassBAnnotationKey = (typeof CLASS_B_ANNOTATION_KEYS)[number];

/** Class-B keys present as OWN properties of `fields` (set to a value OR explicitly
 *  cleared via `undefined`) — i.e. the keys that must stamp annotationsEditedAt. A key
 *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
 *  "changed" and must not trigger a stamp. */
export function classBKeysIn(fields: Partial<Video>): ClassBAnnotationKey[] {
  return Object.keys(fields).filter((k): k is ClassBAnnotationKey =>
    (CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k),
  );
}

// Fields retired by the PDF-generation removal (summaryPdf/deepDivePdf) and the
// deep-dive removal (deepDiveMd/deepDiveHtml/deepDiveVersion). Index files written
// before those efforts still carry these keys; strip them on read so the API never
// re-serves dangling references to deleted files.
const RETIRED_VIDEO_KEYS = [
  'summaryPdf',
  'deepDiveMd',
  'deepDiveHtml',
  'deepDivePdf',
  'deepDiveVersion',
] as const;

function stripRetiredKeys(index: PlaylistIndex): PlaylistIndex {
  for (const video of index.videos ?? []) {
    for (const key of RETIRED_VIDEO_KEYS) {
      delete (video as Record<string, unknown>)[key];
    }
  }
  return index;
}

export function assertOutputFolder(outputFolder: string): void {
  const resolved = path.resolve(outputFolder);
  const home = os.homedir();
  const withinHome = (p: string) => p === home || p.startsWith(home + path.sep);

  if (!withinHome(resolved)) {
    throw Object.assign(new Error(`outputFolder outside home directory: ${resolved}`), { statusCode: 400 });
  }

  // Also check the real path to catch symlinks that point outside home
  try {
    const real = fs.realpathSync.native(resolved);
    if (!withinHome(real)) {
      throw Object.assign(new Error(`outputFolder resolves outside home directory via symlink: ${real}`), { statusCode: 400 });
    }
  } catch (err: unknown) {
    const nodeErr = err as NodeJS.ErrnoException;
    if ((nodeErr as any).statusCode === 400) throw err;
    // ENOENT means path doesn't exist yet — no symlink to follow, trust resolved path
    if (nodeErr.code !== 'ENOENT') throw err;
  }
}

export function assertVideoId(id: string): void {
  if (!VIDEO_ID_RE.test(id)) {
    throw Object.assign(new Error(`invalid videoId: ${id}`), { statusCode: 400 });
  }
}

function indexPath(outputFolder: string): string {
  return path.join(outputFolder, INDEX_FILE);
}

export function readIndex(outputFolder: string): PlaylistIndex {
  assertOutputFolder(outputFolder);
  const filePath = indexPath(outputFolder);
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    return stripRetiredKeys(JSON.parse(raw) as PlaylistIndex);
  } catch (err: unknown) {
    const nodeErr = err as NodeJS.ErrnoException;
    if (nodeErr.code === 'ENOENT') {
      // Distinguish missing file from missing directory
      try { fs.lstatSync(outputFolder); } catch {
        throw Object.assign(new Error(`Output folder does not exist: ${outputFolder}`), { statusCode: 400, cause: err });
      }
      return { playlistUrl: '', outputFolder, videos: [] };
    }
    throw Object.assign(new Error(`Failed to read ${filePath}: ${nodeErr.message}`), { cause: err });
  }
}

export function writeIndex(outputFolder: string, index: PlaylistIndex): void {
  assertOutputFolder(outputFolder);
  for (const video of index.videos) {
    assertVideoId(video.id);
  }
  const filePath = indexPath(outputFolder);
  const tmpPath = filePath + '.' + crypto.randomUUID() + '.tmp';
  try {
    fs.writeFileSync(tmpPath, JSON.stringify(index, null, 2), 'utf-8');
    fs.renameSync(tmpPath, filePath);
  } catch (err) {
    try { fs.unlinkSync(tmpPath); } catch { /* ignore cleanup error */ }
    throw err;
  }
}

export function upsertVideo(outputFolder: string, video: Video): void {
  assertOutputFolder(outputFolder);
  assertVideoId(video.id);
  const index = readIndex(outputFolder);
  const i = index.videos.findIndex((v) => v.id === video.id);
  // Stamp only the single mutated video — never touch writeIndex, which
  // rewrites the whole playlist file and would re-stamp every sibling video.
  const stamped: Video = { ...video, updatedAt: new Date().toISOString() };
  if (i === -1) {
    index.videos.push(stamped);
  } else {
    index.videos[i] = stamped;
  }
  writeIndex(outputFolder, index);
}

export function updateVideoFields(outputFolder: string, id: string, fields: Partial<Video>): void {
  assertOutputFolder(outputFolder);
  assertVideoId(id);
  const index = readIndex(outputFolder);
  const i = index.videos.findIndex((v) => v.id === id);
  if (i === -1) {
    throw new Error(`Video not found in index: ${id}`);
  }
  // Exclude id from fields — callers must not change a video's identity
  const { id: _discarded, ...safeFields } = fields;
  // Stamp only the single mutated video — never touch writeIndex, which
  // rewrites the whole playlist file and would re-stamp every sibling video.
  index.videos[i] = { ...index.videos[i], ...safeFields, updatedAt: new Date().toISOString() };
  writeIndex(outputFolder, index);
}

exec
/bin/bash -lc "sed -n '1,360p' lib/storage/supabase/supabase-metadata-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import { emptyPlaylistIndex } from '@/lib/storage/empty-index';

// ---------------------------------------------------------------------------
// stripComputed: drop the DB-computed `updatedAt` and `summaryReady` keys
// before any write to `videos.data`. readIndex() surfaces `updatedAt`
// (sourced from the `updated_at` column/trigger) and `summaryReady` (derived
// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
// object for read consumers; neither must ever round-trip back into the
// jsonb payload on a write — `updatedAt`'s source of truth is the column/
// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
// itself, so persisting a stale derived boolean would let it drift from the
// artifact it's supposed to reflect.
// ---------------------------------------------------------------------------
function stripComputed<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
  return rest;
}

export class SupabaseMetadataStore implements MetadataStore {
  constructor(private client: SupabaseClient) {}

  // ---------------------------------------------------------------------------
  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
  // ---------------------------------------------------------------------------
  async readIndex(p: Principal): Promise<PlaylistIndex> {
    const { data: pl, error: plErr } = await this.client
      .from('playlists')
      .select('id, playlist_url, playlist_title')
      .eq('playlist_key', p.indexKey)
      .maybeSingle();
    if (plErr) throw plErr;
    if (!pl) return emptyPlaylistIndex(p);

    const { data: rows, error: vErr } = await this.client
      .from('videos')
      .select('data, updated_at')
      .eq('playlist_id', pl.id)
      .order('position', { ascending: true });
    if (vErr) throw vErr;

    return {
      playlistUrl: pl.playlist_url,
      outputFolder: p.indexKey,
      ...(pl.playlist_title ? { playlistTitle: pl.playlist_title } : {}),
      videos: (rows ?? []).map((r) => ({
        ...(r.data as Video),
        updatedAt: r.updated_at as string,
        summaryReady:
          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
            .artifacts?.summaryMd?.status === 'promoted',
      })),
    };
  }

  // ---------------------------------------------------------------------------
  // setPlaylistMeta: upsert on (owner_id, playlist_key).
  // owner_id has NO column default (NOT NULL in schema); must be supplied from
  // the caller's JWT via auth.getUser(). The RLS with-check enforces
  // owner_id = auth.uid() — passing any other value is rejected by the DB.
  // ---------------------------------------------------------------------------
  async setPlaylistMeta(
    p: Principal,
    meta: { playlistUrl: string; playlistTitle?: string },
  ): Promise<void> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('setPlaylistMeta: no authenticated user');

    const { error } = await this.client.from('playlists').upsert(
      {
        owner_id: ownerId,
        playlist_key: p.indexKey,
        playlist_url: meta.playlistUrl,
        playlist_title: meta.playlistTitle ?? null,
      },
      { onConflict: 'owner_id,playlist_key' },
    );
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // claimVideoSlot: RPC appends a reservation row and returns position + serial.
  // ---------------------------------------------------------------------------
  async claimVideoSlot(
    p: Principal,
    videoId: string,
  ): Promise<{ position: number; serialNumber: number }> {
    const id = await this.requirePlaylistId(p);
    const { data, error } = await this.client.rpc('claim_video_slot', {
      p_playlist_id: id,
      p_video_id: videoId,
    });
    if (error) throw error;
    const row = Array.isArray(data) ? data[0] : data;
    return { position: row.position, serialNumber: row.serial_number };
  }

  // ---------------------------------------------------------------------------
  // upsertVideo: UPDATE the reservation row already created by claimVideoSlot.
  // ---------------------------------------------------------------------------
  async upsertVideo(p: Principal, video: Video): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client
      .from('videos')
      .update({ data: stripComputed(video) })
      .eq('playlist_id', id)
      .eq('video_id', video.id);
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
  // modify-write races; deep-merges the `artifacts` sub-object).
  // Stage 3 (§5.1/§5.7): merge_video_data (0021) stamps annotationsEditedAt server-side
  // when p_fields carries a Class-B key (personalNote/personalScore/corrections) — this
  // just needs to forward the caller's sync-path timestamp (opts.editedAt) as p_edited_at
  // when present; the RPC defaults to now() for the user-edit path when omitted.
  // ---------------------------------------------------------------------------
  async updateVideoFields(
    p: Principal,
    videoId: string,
    fields: Partial<Video>,
    opts?: { editedAt?: string },
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('merge_video_data', {
      p_playlist_id: id,
      p_video_id: videoId,
      p_fields: stripComputed(fields),
      ...(opts?.editedAt ? { p_edited_at: opts.editedAt } : {}),
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // bulkUpdateVideoFields: same merge semantics in one transaction.
  // p_patches shape must match the RPC: [{ video_id, fields }].
  // ---------------------------------------------------------------------------
  async bulkUpdateVideoFields(
    p: Principal,
    patches: { videoId: string; fields: Partial<Video> }[],
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('merge_video_data_bulk', {
      p_playlist_id: id,
      p_patches: patches.map((x) => ({ video_id: x.videoId, fields: stripComputed(x.fields) })),
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // reconcilePlaylistMembership: archive/restore by membership in one txn.
  // ---------------------------------------------------------------------------
  async reconcilePlaylistMembership(
    p: Principal,
    currentPlaylistIds: string[],
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('reconcile_membership', {
      p_playlist_id: id,
      p_present: currentPlaylistIds,
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
  // ---------------------------------------------------------------------------
  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client
      .from('videos')
      .delete()
      .eq('playlist_id', id)
      .eq('video_id', videoId);
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // resolvePlaylistId: upsert the (owner, playlist_key) row and return its id
  // atomically. Owner-correct by construction (the upserted row carries
  // owner_id); never a playlist_key-only select.
  // ---------------------------------------------------------------------------
  async resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('resolvePlaylistId: no authenticated user');
    const { data, error } = await this.client.from('playlists')
      .upsert({ owner_id: ownerId, playlist_key: p.indexKey, playlist_url: playlistUrl },
        { onConflict: 'owner_id,playlist_key' })
      .select('id').single();
    if (error) throw error;
    return data.id as string;
  }

  // ---------------------------------------------------------------------------
  // setPlaylistTitleIfNull: conditional update — fills playlist_title ONLY when it is
  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
  // clobbered. Scoped by owner_id (from auth.getUser, mirroring setPlaylistMeta) and
  // playlist_key (p.indexKey) — no separate listId param. `.select('id')` on the update
  // lets us derive `updated` from whether a row actually matched (and was updated), not
  // just whether the statement ran — a no-op conditional update returns an empty array.
  // ---------------------------------------------------------------------------
  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('setPlaylistTitleIfNull: no authenticated user');

    const { data, error } = await this.client
      .from('playlists')
      .update({ playlist_title: title })
      .eq('owner_id', ownerId)
      .eq('playlist_key', p.indexKey)
      .is('playlist_title', null)
      .select('id');
    if (error) throw error;
    return { updated: (data?.length ?? 0) > 0 };
  }

  // ---------------------------------------------------------------------------
  // listPlaylists: cloud-only. Session client + RLS (owner_id = auth.uid()) already
  // scopes this, but the explicit .eq('owner_id', ownerId) is defense-in-depth. Ordered
  // by playlist_title (nulls last) then created_at — created_at MUST be in the select
  // since it is both an ORDER BY column and part of the returned PlaylistSummary.
  // ---------------------------------------------------------------------------
  async listPlaylists(ownerId: string): Promise<PlaylistSummary[]> {
    const { data, error } = await this.client
      .from('playlists')
      .select('id, playlist_key, playlist_url, playlist_title, created_at')
      .eq('owner_id', ownerId)
      .order('playlist_title', { nullsFirst: false })
      .order('created_at');
    if (error) throw error;
    return (data ?? []).map((r) => ({
      id: r.id,
      playlistKey: r.playlist_key,
      playlistUrl: r.playlist_url,
      playlistTitle: r.playlist_title,
      createdAt: r.created_at,
    }));
  }

  // ---------------------------------------------------------------------------
  // updateVideoAnnotations: distinct write path from updateVideoFields/merge_video_data
  // (unchanged). The allowlist ({personalScore, personalNote, corrections, archived}) and
  // the owner_id = auth.uid() guard are enforced IN SQL by update_video_annotations — this
  // is the sole caller-facing surface for personal-annotation writes; no p_owner is
  // ever sent. The RPC returns an integer row-count; > 0 means the row existed and was
  // updated under the caller's ownership.
  // Stage 3 (§5.1/§5.7): 'corrections' is now allowlisted server-side (0021), and the RPC
  // stamps annotationsEditedAt per Class-B field touched. `opts.editedAt` forwards the
  // sync-path source timestamp as p_edited_at; omitted on the user-edit path so the RPC's
  // `default now()` applies.
  // ---------------------------------------------------------------------------
  async updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
    clear: ('personalScore' | 'personalNote' | 'corrections')[],
    opts?: { editedAt?: string },
  ): Promise<{ found: boolean }> {
    const id = await this.requirePlaylistId(p);
    const { data, error } = await this.client.rpc('update_video_annotations', {
      p_playlist_id: id,
      p_video_id: videoId,
      p_set: set,
      p_clear: clear,
      ...(opts?.editedAt ? { p_edited_at: opts.editedAt } : {}),
    });
    if (error) throw error;
    return { found: (data ?? 0) > 0 };
  }

  // ---------------------------------------------------------------------------
  // deletePlaylist: hard-delete a playlist row owned by the caller (Task 8).
  // RLS already scopes DELETE to owner_id = auth.uid(); the explicit .eq('owner_id')
  // is defense-in-depth, matching listPlaylists/setPlaylistTitleIfNull convention.
  // T6's cascade FKs (0019) remove the playlist's videos/jobs/share_tokens as a side
  // effect — no separate cleanup calls here. A non-owner/nonexistent id deletes 0 rows
  // without erroring.
  // ---------------------------------------------------------------------------
  async deletePlaylist(p: Principal, playlistId: string): Promise<void> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('deletePlaylist: no authenticated user');

    const { error } = await this.client
      .from('playlists')
      .delete()
      .eq('id', playlistId)
      .eq('owner_id', ownerId);
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private async playlistId(p: Principal): Promise<string | null> {
    const { data, error } = await this.client
      .from('playlists')
      .select('id')
      .eq('playlist_key', p.indexKey)
      .maybeSingle();
    if (error) throw error;
    return data?.id ?? null;
  }

  private async requirePlaylistId(p: Principal): Promise<string> {
    const id = await this.playlistId(p);
    if (!id) throw new Error(`playlist not found for indexKey=${p.indexKey}`);
    return id;
  }
}

exec
/bin/bash -lc "sed -n '1,220p' lib/storage/metadata-store.ts && sed -n '1,220p' lib/storage/principal.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';

/** Cloud-only row shape for MetadataStore.listPlaylists — one entry per playlist owned
 *  by a given user (createdAt sourced from the playlists.created_at column). */
export interface PlaylistSummary {
  id: string;
  playlistKey: string;
  playlistUrl: string;
  playlistTitle: string | null;
  createdAt: string;
}

/** Read/write access to a principal's playlist index + video records.
 *  Local impl delegates to lib/index-store; cloud impl (later) is Postgres. */
export interface MetadataStore {
  readIndex(p: Principal): Promise<PlaylistIndex>;
  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
  claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }>;
  upsertVideo(p: Principal, video: Video): Promise<void>;
  updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
  bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void>;
  reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void>;
  /** Remove a video stub from the index. No-op if the id is not present.
   *  Used to roll back a claimVideoSlot reservation when pipeline processing fails. */
  deleteVideo(p: Principal, videoId: string): Promise<void>;
  /** Cloud-only: resolve (owner, playlist_key) to the playlists.id UUID, creating the row if absent. */
  resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string>;
  /** Conditional title fill (BUG-6 backfill, Task 3/4): sets `playlist_title` to `title`
   *  ONLY when the row's title is currently null/absent, so it never clobbers a title a
   *  concurrent ingest just wrote. Scoped on `p.indexKey` (the playlist_key) — no separate
   *  listId param. Returns whether a row was actually updated (not merely attempted), so
   *  callers (the backfill route) can count real persists, not no-op conditional updates. */
  setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }>;
  /** Cloud-only: list all playlists owned by ownerId, ordered by title (nulls last) then
   *  created_at. Local impl throws — the local sidebar is not rendered in 2a and the
   *  filesystem-backed equivalent (listRecentPlaylists) needs a filesystem root, not an
   *  ownerId, and returns a different shape. */
  listPlaylists(ownerId: string): Promise<PlaylistSummary[]>;
  /** Owner-guarded personal-annotation write (Task 7). `set` supplies allowlisted
   *  ({personalScore, personalNote, archived}) values to merge in; `clear` lists
   *  allowlisted keys to remove. The cloud impl enforces the allowlist AND the
   *  owner_id = auth.uid() guard server-side, in SQL (update_video_annotations RPC) —
   *  this is a distinct write path from updateVideoFields/merge_video_data, which is
   *  left unchanged. Returns { found: true } iff a row existed for (playlistId, videoId)
   *  under the caller's ownership, regardless of whether the sliced payload was empty;
   *  callers 404 on found:false. */
  updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
    clear: ('personalScore' | 'personalNote' | 'corrections')[],
    opts?: { editedAt?: string },
  ): Promise<{ found: boolean }>;
  /** Cloud-only: hard-delete a playlist row owned by the caller (Task 8). RLS already
   *  scopes this to `owner_id = auth.uid()`; the explicit owner_id predicate in the
   *  cloud impl is defense-in-depth, not the sole guard. T6's cascade FKs remove the
   *  playlist's videos/jobs/share_tokens as a side effect — no separate cleanup calls
   *  are made here. A non-owner id (or an id that does not exist) deletes 0 rows and
   *  throws nothing — the caller's own data is untouched either way. Local impl
   *  throws — the delete UI is cloud-only (spec §B6). */
  deletePlaylist(p: Principal, playlistId: string): Promise<void>;
}
/** Identifies whose data a storage operation targets, and which index.
 *  `id`: local = the fixed sentinel; cloud = the owner user id (auth.uid()).
 *  `indexKey`: the index selector — local = the on-disk data root (path);
 *  cloud = the playlist key (e.g. the YouTube list-id) selecting one index. */
export interface Principal {
  readonly id: string;
  readonly indexKey: string;   // local: on-disk data root; cloud: playlist_key (YouTube list-id)
}

export const LOCAL_PRINCIPAL_ID = 'local';

export function localPrincipal(indexKey: string): Principal {
  return { id: LOCAL_PRINCIPAL_ID, indexKey };
}

codex
Local and cloud stores mostly align, with one important difference already compensated for: cloud `upsertVideo` is update-only and can no-op, while local can insert. The orchestrator’s receiver-slot and post-write read are intended to close that gap; I’m checking the SQL now to see whether RPC behavior matches those assumptions. 

exec
/bin/bash -lc "sed -n '1,420p' supabase/migrations/0021_cloud_sync_signals.sql" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
-- supabase/migrations/0021_cloud_sync_signals.sql
-- Stage 3 Cloud Sync (§5.7): per-field annotationsEditedAt stamping, corrections
-- allowlisting, conditional merge restamp, and mdGeneratedAt/mdCorrectionsHash on persist.

-- (0) DROP the old signatures FIRST. Adding a defaulted `p_edited_at` parameter to
--     update_video_annotations / merge_video_data with `create or replace` would create a
--     NEW overload and LEAVE the old 4-arg / 3-arg functions in place. A caller that omits
--     p_edited_at (e.g. SupabaseMetadataStore.updateVideoAnnotations' 4-key rpc call) would
--     then match BOTH overloads → PostgREST error PGRST203 "could not choose the best
--     candidate function" → the live Archive button + annotation/field writes break. Dropping
--     the old signatures makes the 3/4-key call resolve unambiguously to the single surviving
--     defaulted function. (persist_summary keeps its 5-arg signature unchanged → no drop needed.)
drop function if exists update_video_annotations(uuid, text, jsonb, text[]);
drop function if exists merge_video_data(uuid, text, jsonb);

-- (1) update_video_annotations: add corrections to the allowlist; stamp per-field
--     annotationsEditedAt for each Class-B field set OR cleared; accept an explicit
--     sync-path timestamp (defaults to now() for the user-edit path).
create or replace function update_video_annotations(
  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[],
  p_edited_at timestamptz default now()
) returns integer language plpgsql security invoker set search_path = public as $$
declare
  allow text[] := array['personalScore','personalNote','corrections','archived'];
  classb text[] := array['personalScore','personalNote','corrections'];
  v_set jsonb := '{}'::jsonb;
  v_stamp jsonb := '{}'::jsonb;
  v_clear text[] := '{}';
  k text; n integer;
  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
begin
  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    if k = any(allow) then
      v_set := v_set || jsonb_build_object(k, p_set->k);
      if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    end if;
  end loop;
  -- clears: only allowlisted; each Class-B clear stamps its timestamp
  select coalesce(array_agg(c),'{}') into v_clear
    from unnest(coalesce(p_clear,'{}')) c where c = any(allow);
  foreach k in array v_clear loop
    if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
  end loop;

  -- Only touch annotationsEditedAt when there IS a Class-B stamp; an archived-only
  -- (or empty) write must not create an empty annotationsEditedAt:{} (§4.1 "archived-only
  -- write restamps nothing").
  update videos
     set data = case when v_stamp <> '{}'::jsonb
                  then jsonb_set((data || v_set) - v_clear, '{annotationsEditedAt}',
                         coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp, true)
                  else (data || v_set) - v_clear end
   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) from public;
grant execute on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) to authenticated;

-- (2) merge_video_data: conditional annotationsEditedAt restamp when a Class-B key is
--     present in the patch (a bare MD-finalize / artifact / membership write must NOT bump it).
create or replace function merge_video_data(
  p_playlist_id uuid, p_video_id text, p_fields jsonb,
  p_edited_at timestamptz default now()
) returns void language plpgsql security invoker set search_path = public as $$
declare
  classb text[] := array['personalScore','personalNote','corrections'];
  v_stamp jsonb := '{}'::jsonb; k text;
  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  foreach k in array classb loop
    if p_fields ? k then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
  end loop;

  update videos set
    data = (data || (p_fields - 'artifacts'))
      || case when p_fields ? 'artifacts'
           then jsonb_build_object('artifacts',
                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
           else '{}'::jsonb end
      || case when v_stamp <> '{}'::jsonb
           then jsonb_build_object('annotationsEditedAt',
                  coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp)
           else '{}'::jsonb end,
    updated_at = now()
   where playlist_id = p_playlist_id and video_id = p_video_id;
end $$;
revoke all on function merge_video_data(uuid, text, jsonb, timestamptz) from public;
grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;

-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
--     (git show HEAD:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql)
--     with ONLY two additional keys added to the summary-owned jsonb_build_object:
--     'mdGeneratedAt' and 'mdCorrectionsHash' (§5.7).
create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
  returns void language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
  update videos v set
    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
                                                              --     state AND never drop existing summary fields on a
                                                              --     status-only persist (p_video omits them)
      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
           'ratings', p_video->'ratings',
           'overallScore', p_video->'overallScore',
           'processedAt', p_video->'processedAt',
           'videoType', p_video->'videoType',
           'audience', p_video->'audience',
           'tags', p_video->'tags',
           'tldr', p_video->'tldr',
           'takeaways', p_video->'takeaways',
           'docVersion', p_video->'docVersion',
           'mdGeneratedAt', p_video->'mdGeneratedAt',
           'mdCorrectionsHash', p_video->'mdCorrectionsHash'))
      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
      || jsonb_build_object('artifacts',
           coalesce(v.data->'artifacts', '{}'::jsonb)
           || jsonb_build_object('summaryMd', jsonb_build_object(
                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
                -- that IS in committed state, so it must be allowed through (else the row would claim a
                -- promoted artifact for a blob that has not been promoted yet).
                'status', case
                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
                                 and p_artifact_status = 'committed'
                                 and v.data->'artifacts'->'summaryMd'->>'key'
                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
                              then 'promoted'
                            else p_artifact_status end))),
    updated_at = now()
   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
  get diagnostics v_count = row_count;
  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
end $$;
revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;

exec
/bin/bash -lc "sed -n '1,260p' supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
-- 0009: 1E-b — job-identity playlist coordinate + worker columns/RPCs.
-- jobs is created fresh by 0008 on every `db reset` (empty at this point) → safe re-key.

alter table jobs add column playlist_id uuid not null;
alter table jobs add constraint jobs_playlist_owner_fk
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;
alter table jobs add column progress_phase text
  check (progress_phase in ('transcribing','summarizing','writing'));

drop index jobs_idem_active;
create unique index jobs_idem_active
  on jobs (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed');

drop function enqueue_job(text,int,text,text,jsonb);
create function enqueue_job(
  p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare v_id uuid; v_status text; v_payload jsonb; v_tries int := 0;
begin
  if auth.uid() is null then raise exception 'not authenticated'; end if;
  loop
    v_tries := v_tries + 1;
    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload)
    values (auth.uid(), p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
      where j.status in ('queued','active','completed')
      do nothing
    returning id into v_id;
    if v_id is not null then return query select v_id, 'queued'::text, false; return; end if;
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = auth.uid() and j.playlist_id = p_playlist_id and j.video_id = p_video_id
        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
      return query select v_id, v_status, true; return;
    end if;
  end loop;
end $$;
revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;

-- set_progress_phase: lease-fenced advisory phase write (keeps lifecycle writes RPC-only).
create function set_progress_phase(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_phase text)
  returns boolean language plpgsql security invoker set search_path = public as $$
declare v_ok boolean;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  update jobs set progress_phase = p_phase, updated_at = now()
    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
  get diagnostics v_ok = row_count;
  return v_ok > 0;
end $$;
revoke all on function set_progress_phase(uuid,text,uuid,text) from public;
grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;

-- crash-reclaim now backs off (resolves 1E-a deferred Minor #2), mirroring fail_job.
create or replace function sweep_expired_leases() returns int
  language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  with expired as (select id from jobs where status = 'active' and lease_expires_at < now() for update skip locked)
  update jobs j set
    status = case when j.cancel_requested then 'cancelled'
                  when j.attempts >= j.max_attempts then 'dead_letter' else 'queued' end,
    run_after = case when j.cancel_requested or j.attempts >= j.max_attempts then j.run_after
                     else now() + make_interval(secs => (10 * power(4, least(greatest(j.attempts - 1, 0), 15)))::bigint) end,
    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  from expired e where j.id = e.id;
  get diagnostics v_count = row_count; return v_count;
end $$;

create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
  returns int language plpgsql security invoker set search_path = public as $$
declare v_serial int; v_pos int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id for update;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  if v_serial is not null then return v_serial; end if;
  if exists (select 1 from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id) then
    raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', p_playlist_id, p_video_id;
  end if;
  select coalesce(max(v.position) + 1, 0), coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial from videos v where v.playlist_id = p_playlist_id;
  insert into videos (playlist_id, owner_id, video_id, position, data)
    values (p_playlist_id, p_owner_id, p_video_id, v_pos, jsonb_build_object('id', p_video_id, 'serialNumber', v_serial))
    on conflict (playlist_id, video_id) do nothing;
  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  return v_serial;
end $$;
revoke all on function reserve_video_slot(uuid,uuid,text) from public;
grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;

create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
  returns void language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
  update videos v set
    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
                                                              --     state AND never drop existing summary fields on a
                                                              --     status-only persist (p_video omits them)
      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
           'ratings', p_video->'ratings',
           'overallScore', p_video->'overallScore',
           'processedAt', p_video->'processedAt',
           'videoType', p_video->'videoType',
           'audience', p_video->'audience',
           'tags', p_video->'tags',
           'tldr', p_video->'tldr',
           'takeaways', p_video->'takeaways',
           'docVersion', p_video->'docVersion'))
      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
      || jsonb_build_object('artifacts',
           coalesce(v.data->'artifacts', '{}'::jsonb)
           || jsonb_build_object('summaryMd', jsonb_build_object(
                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
                -- that IS in committed state, so it must be allowed through (else the row would claim a
                -- promoted artifact for a blob that has not been promoted yet).
                'status', case
                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
                                 and p_artifact_status = 'committed'
                                 and v.data->'artifacts'->'summaryMd'->>'key'
                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
                              then 'promoted'
                            else p_artifact_status end))),
    updated_at = now()
   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
  get diagnostics v_count = row_count;
  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
end $$;
revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;

exec
/bin/bash -lc "sed -n '1,240p' supabase/migrations/0016_update_video_annotations.sql" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
-- supabase/migrations/0016_update_video_annotations.sql

-- update_video_annotations: owner-guarded personal-annotation writer (Stage 2a Task 7).
-- Distinct from merge_video_data (UNCHANGED, left untouched by this migration):
--   * Allowlists the writable keys IN SQL ({personalScore, personalNote, archived}) — a
--     non-allowlisted key in p_set (e.g. summaryMd) is silently dropped, never written.
--   * Owner is derived ONLY from auth.uid() in the WHERE clause — there is no p_owner
--     parameter and no service_role bypass. SECURITY INVOKER + RLS both apply; this
--     function is the sole write path for personal annotations.
--   * The UPDATE always runs (even when the sliced p_set/p_clear are empty), so
--     row_count reflects row existence/ownership — callers use the returned count to
--     distinguish "no such video / not yours" (0) from "written" (>0) and 404 on 0.
create function update_video_annotations(
  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[]
) returns integer language plpgsql security invoker set search_path = public as $$
declare
  allow text[] := array['personalScore','personalNote','archived'];
  v_set jsonb := '{}'::jsonb; k text; n integer;
begin
  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    if k = any(allow) then v_set := v_set || jsonb_build_object(k, p_set->k); end if;
  end loop;
  update videos
     set data = (data || v_set) - (select coalesce(array_agg(c),'{}') from unnest(coalesce(p_clear,'{}')) c where c = any(allow))
   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function update_video_annotations(uuid, text, jsonb, text[]) from public;
grant execute on function update_video_annotations(uuid, text, jsonb, text[]) to authenticated;

exec
/bin/bash -lc "sed -n '1,220p' supabase/migrations/0020_reservation_release.sql" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
-- 0020_reservation_release.sql
-- Reserve→release lifecycle for spend_ledger. Money path — see
-- docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md (v7).
-- Built up across plan Tasks 1–5. Order matters: ledger_audit (this task) must precede
-- every function that inserts into it (Tasks 2–5).

-- ── Task 1: ledger_audit ────────────────────────────────────────────────────
-- In-band invariant-violation signal for a guarded decrement that would go negative.
-- Locked down exactly like spend_ledger (0011:17-18): force RLS + NO policy blocks
-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
-- NOT bypass table GRANTs, so the explicit grant below is required, not optional.
create table ledger_audit (
  id            bigint generated always as identity primary key,
  day           date        not null,
  kind          text        not null,   -- e.g. 'release_underflow'
  expected_amt  int         not null,
  note          text,
  at            timestamptz not null default now()
);
alter table ledger_audit enable row level security;
alter table ledger_audit force  row level security;   -- no policies → no session-client access at all
grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger

-- ── Task 13 / H1: durable per-JOB "ever billed" flag ─────────────────────────
-- The worker's billing latch (worker-runner.ts's `billing.metered`) is per-ATTEMPT — it resets
-- every runOnce — but the reservation (jobs.reserved_cents) is per-JOB, reused across retries.
-- Without a durable flag, a job that meters real spend on attempt-1 then hits a retryable
-- failure and requeues FORGETS it billed; a later release path (fail_job at exhaustion, or a
-- cancel of the requeued job) would refund the reservation anyway — an UNDER-COUNT, the one
-- direction this whole reserve→release slice exists to prevent. `not null default false` so
-- every existing/never-metered job keeps its current release behavior unchanged.
alter table jobs add column ever_metered boolean not null default false;

-- ── Task 2: fail_job — DROP+recreate 6-arg with spend-aware release ──────────
-- Adding p_billable_succeeded changes the arg count (5→6). A bare create-or-replace would
-- leave the 5-arg overload alongside → the adapter's named-arg call resolves ambiguously
-- (the BUG-1 footgun). So DROP the 5-arg version, recreate, and re-grant the 6-arg signature.
drop function fail_job(uuid,text,uuid,text,boolean);

create function fail_job(
    p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text,
    p_retryable boolean, p_billable_succeeded boolean default true,  -- default TRUE = conservative KEEP
    p_metered boolean default false)   -- Task 13/H1: THIS attempt's billing latch, OR-persisted below
  returns text language plpgsql security invoker set search_path = public as $$
declare
  v_attempts int; v_max int; v_cancel boolean; v_new text; v_backoff bigint;
  v_created_at timestamptz; v_reserved int; v_ever_metered boolean;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  select attempts, max_attempts, cancel_requested, created_at, reserved_cents, ever_metered
    into v_attempts, v_max, v_cancel, v_created_at, v_reserved, v_ever_metered
    from jobs
    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active'
    for update;
  if not found then return null; end if;            -- lost lease
  if v_cancel then v_new := 'cancelled';
  elsif not p_retryable then v_new := 'failed';
  elsif v_attempts >= v_max then v_new := 'dead_letter';
  else v_new := 'queued';
  end if;
  v_backoff := (10 * power(4, least(greatest(v_attempts - 1, 0), 15)))::bigint;
  update jobs set status = v_new, error = p_error,
       run_after = case when v_new = 'queued' then now() + make_interval(secs => v_backoff) else run_after end,
       locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now(),
       -- Task 13/H1: persist metering EVEN on the KEEP-requeue path — a metered attempt-1 that
       -- retries must not let attempt-2 (or a cancel while queued) forget it already billed.
       ever_metered = jobs.ever_metered or p_metered
  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';

  -- Spend-aware release: only a genuine terminal fail that never billed on THIS attempt (via
  -- p_billable_succeeded) AND never billed on ANY prior attempt (v_ever_metered — the PRE-update,
  -- durable JOB-scoped signal; Task 13/H1). NOT 'queued' (retry reuses the reservation —
  -- behavior 6). Inside the status='active' single-writer fence → exactly-once.
  if not p_billable_succeeded
     and not v_ever_metered
     and not p_metered                                   -- defend the CURRENT attempt's meter too (belt-and-suspenders
                                                          -- vs a contradictory p_metered=true+billable=false call — pure KEEP, never releases)
     and v_new in ('failed','dead_letter','cancelled')
     and v_reserved > 0 then
    update spend_ledger
       set reserved_cents = reserved_cents - v_reserved, updated_at = now()
     where day = (v_created_at at time zone 'utc')::date
       and reserved_cents >= v_reserved;                -- guarded decrement, never silent clamp
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values ((v_created_at at time zone 'utc')::date, 'release_underflow', v_reserved,
                'fail_job '||p_job_id::text, now());
    end if;
    update jobs set reserved_cents = 0 where id = p_job_id;   -- belt-and-suspenders (fence is primary)
  end if;
  return v_new;
end $$;
revoke all on function fail_job(uuid,text,uuid,text,boolean,boolean,boolean) from public;
grant execute on function fail_job(uuid,text,uuid,text,boolean,boolean,boolean) to service_role;

-- ── Task 3: request_cancel_job — procedural, releases a genuine queued cancel ─
-- Same signature (uuid → int) so create-or-replace preserves grants. Procedural because we
-- must (a) pre-read OLD reserved_cents before zeroing (PG<18 RETURNING is post-update),
-- (b) audit underflow, (c) return 1 for BOTH a queued cancel and an active flag-set (H-4).
create or replace function request_cancel_job(p_job_id uuid) returns int
  language plpgsql security definer set search_path = public as $$
declare v_old_status text; v_old_amt int; v_day date; v_ever_metered boolean; v_attempts int;
begin
  select status, reserved_cents, (created_at at time zone 'utc')::date, ever_metered, attempts
    into v_old_status, v_old_amt, v_day, v_ever_metered, v_attempts
    from jobs
   where id = p_job_id and owner_id = auth.uid() and status in ('queued','active')
   for update;                                       -- serialize vs claim_next_job's skip-locked claim
  if not found then return 0; end if;                -- terminal / foreign / missing
  update jobs
     set cancel_requested = true,
         status         = case when v_old_status = 'queued' then 'cancelled' else status end,
         reserved_cents = case when v_old_status = 'queued' then 0 else reserved_cents end,
         updated_at     = now()
   where id = p_job_id;
  -- RELEASE only a genuine queued→cancelled that was NEVER CLAIMED (attempts=0 ⟹ never metered, so
  -- provably safe to release). A queued job with attempts>=1 is a reaper requeue of an attempt that
  -- may have billed but whose in-memory latch was lost before fail_job could persist ever_metered
  -- (whole-branch round-2 H-R2-1) → KEEP. attempts=0 subsumes not v_ever_metered; both kept defensively.
  if v_old_status = 'queued' and v_old_amt > 0 and not v_ever_metered and v_attempts = 0 then
    update spend_ledger set reserved_cents = reserved_cents - v_old_amt, updated_at = now()
     where day = v_day and reserved_cents >= v_old_amt;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_old_amt, 'request_cancel_job '||p_job_id::text, now());
    end if;
  end if;
  return 1;                                           -- cancellation requested (queued OR active) — H-4
end $$;

-- ── Task 4: request_cancel_playlist_jobs — set-based multi-day release ────────
-- Same signature → create-or-replace (grants + search_path=public,pg_temp preserved).
-- One data-modifying CTE: flag ALL non-terminal jobs (H-2), release only the queued subset
-- grouped per reserve-day (H-3 per-day audit), return jobs-flagged count (H-4).
create or replace function request_cancel_playlist_jobs(p_playlist_id uuid) returns int
  language plpgsql security definer set search_path = public, pg_temp as $$
declare v_n int;
begin
  -- Note: a data-modifying WITH must be the top-level statement (Postgres forbids
  -- `return (with ... )` — that nests it as a scalar subquery). `... into v_n` keeps
  -- the CTE chain top-level while still capturing the H-4 count.
  with pre as (                                  -- ALL non-terminal jobs of the playlist, under lock
    select id, status as old_status, reserved_cents as old_amt, ever_metered, attempts,
           (created_at at time zone 'utc')::date as reserve_day
      from public.jobs                           -- schema-qualified (0019 search_path-hijack hardening — L1)
     where playlist_id = p_playlist_id and owner_id = auth.uid() and status in ('queued','active')
     for update),
  upd as (                                       -- H-2: flag ALL; flip+zero only the queued subset
    update public.jobs j
       set cancel_requested = true,
           status         = case when pre.old_status = 'queued' then 'cancelled' else j.status end,
           reserved_cents = case when pre.old_status = 'queued' then 0 else j.reserved_cents end,
           updated_at     = now()
      from pre where j.id = pre.id
     returning j.id),
  per_day as (                                   -- queued-only, NEVER-CLAIMED (attempts=0) OLD amounts,
                                                   -- grouped by reserve-day. attempts>=1 queued = reaper
                                                   -- requeue that may have billed (round-2 H-R2-1) → excluded
                                                   -- from release sum; `upd` still flags/cancels it, release vetoed.
    select reserve_day, sum(old_amt) as amt
      from pre where old_status = 'queued' and old_amt > 0 and not ever_metered and attempts = 0
     group by reserve_day),
  dec as (                                       -- guarded per-day decrement; RETURNING credited days
    update spend_ledger sl
       set reserved_cents = sl.reserved_cents - per_day.amt, updated_at = now()
      from per_day
     where sl.day = per_day.reserve_day and sl.reserved_cents >= per_day.amt
     returning sl.day),
  aud as (                                       -- H-3: audit every per_day with no successful decrement
    insert into ledger_audit(day, kind, expected_amt, note, at)
    select pd.reserve_day, 'release_underflow', pd.amt,
           'request_cancel_playlist_jobs '||p_playlist_id::text, now()
      from per_day pd
     where pd.reserve_day not in (select day from dec))
  select count(*)::int into v_n from upd;          -- H-4: jobs flagged (queued + active)
  return v_n;
end $$;

-- ── Task 5: serve token + settle ─────────────────────────────────────────────
alter table serve_model_charge add column reserved_cents int not null default 0 check (reserved_cents >= 0);
alter table serve_model_charge add column release_token uuid;   -- current in-flight reservation's one-time secret

-- reserve_serve_model: return type changes (text → table) → DROP+recreate+re-grant.
-- Body identical to 0014 except it now also mints a release_token on the 'reserved' branch.
drop function reserve_serve_model(uuid, text);

create function reserve_serve_model(p_playlist_id uuid, p_video_id text)
  returns table(status text, release_token uuid)
  language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cfg guardrail_config;
  v_doc_key text;
  v_day date;
  v_promoted boolean;
  v_claimed int;
  v_existing int;
  v_lease_live boolean;
  v_result text;
  v_token uuid;                                    -- null unless we reserve
begin
  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;

  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    into v_promoted
    from videos v join playlists p on p.id = v.playlist_id
    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
  if v_promoted is distinct from true then
    return query select 'denied'::text, null::uuid; return;
  end if;

  select * into v_cfg from guardrail_config where id = true;
  v_doc_key := p_playlist_id::text || '/' || p_video_id;
  v_day := (now() at time zone 'utc')::date;

  begin
    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    on conflict (owner_id, doc_key, day) do update
      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),

exec
/bin/bash -lc "sed -n '1,320p' lib/pipeline.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import fs from 'fs';
import path from 'path';
import { fetchPlaylistVideos, fetchPlaylistTitle } from './youtube';
import { generateSummary, extractQuickView } from './gemini';
import { resolveTranscriptSegments } from './transcript-source';
import { assertVideoId } from './index-store';
import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
import { localPrincipal } from '@/lib/storage/principal';
import type { BlobStore } from '@/lib/storage/blob-store';
import { slugify } from './slugify';
import { applySerial, padSerial } from './serial-filename';
import type { ProgressEvent, Video, VideoMeta, RatingValue, VideoType, Audience, GeminiSummaryResponse } from '../types';
import { CURRENT_DOC_VERSION } from './doc-version';
import { runHtmlDoc } from './html-doc/generate';
import { formatDuration } from './format-duration';
import { summaryCore } from './ingestion/summary-core';
import { mdHash } from './cloud-sync/content-hash';

const VALID_VIDEO_TYPES: VideoType[] = ['Tutorial', 'Analysis', 'Case Study', 'Framework', 'Demo', 'Interview'];
const VALID_AUDIENCES: Audience[] = ['Beginner', 'Intermediate', 'Advanced'];

export interface SummaryDocInput {
  videoId: string;
  title: string;
  youtubeUrl: string;
  channel?: string;
  durationSeconds: number;
  outputFolder: string;
  baseName: string;
  blobStore?: BlobStore;
}
export interface SummaryDocResult {
  language: 'en' | 'ko';
  ratings: GeminiSummaryResponse['ratings'];
  overallScore: number;
  videoType?: VideoType;
  audience?: Audience;
  tags?: string[];
  tldr?: string;
  takeaways?: string[];
  mdContent: string;
  summaryMd: string;
}

/**
 * Fetch transcript → generateSummary (emits ▶ timestamps) → build the summary .md → write it at
 * <baseName>.md. Shared by ingestion (new slug) and re-summarize (existing baseName).
 */
export async function writeSummaryDoc(input: SummaryDocInput): Promise<SummaryDocResult> {
  const { videoId, title, youtubeUrl, channel, durationSeconds, outputFolder, baseName, blobStore = getStorageBundle().blobStore } = input;
  const result = await summaryCore(
    { videoId, title, youtubeUrl, channel, durationSeconds, baseName },
    { resolveTranscriptSegments, generateSummary, extractQuickView },
  );
  const { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways } = result.geminiFields;

  await blobStore.put(localPrincipal(outputFolder), `${baseName}.md`, Buffer.from(result.mdContent, 'utf-8'), 'text/markdown');
  return { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent: result.mdContent, summaryMd: `${baseName}.md` };
}

export function parseFrontmatterField(content: string, key: string): string | null {
  const match = content.match(new RegExp(`^${key}:\\s*"?([^"\\n]*)"?\\s*$`, 'm'));
  return match?.[1]?.trim() ?? null;
}

function parseDurationString(dur: string): number {
  const parts = dur.split(':').map(Number);
  if (parts.length === 2) return (parts[0] ?? 0) * 60 + (parts[1] ?? 0);
  if (parts.length === 3) return (parts[0] ?? 0) * 3600 + (parts[1] ?? 0) * 60 + (parts[2] ?? 0);
  return 0;
}

export function reconstructVideo(content: string, file: string, mdPath: string): Video | null {
  const videoId = parseFrontmatterField(content, 'video_id');
  if (!videoId) return null;

  const langRaw = parseFrontmatterField(content, 'lang');
  const language = langRaw?.toLowerCase() === 'ko' ? 'ko' : 'en';

  const scoreRaw = parseFrontmatterField(content, 'score');
  const overallScore = parseFloat(scoreRaw ?? '3') || 3;
  const rRaw = Math.max(1, Math.min(5, Math.round(overallScore)));
  const r = rRaw as RatingValue;
  const ratings = { usefulness: r, depth: r, originality: r, recency: r, completeness: r };

  const urlMatch = content.match(/\*\*URL:\*\*\s*(https?:\/\/\S+)/);
  const youtubeUrl = urlMatch?.[1] ?? `https://www.youtube.com/watch?v=${videoId}`;

  const durMatch = content.match(/\*\*Duration:\*\*\s*([\d:]+)/);
  const durationSeconds = durMatch ? parseDurationString(durMatch[1]) : 0;

  const titleMatch = content.match(/^#\s+(.+)$/m);
  const title = titleMatch?.[1]?.trim() ?? file.replace(/\.md$/, '');

  const videoTypeRaw = parseFrontmatterField(content, 'type');
  const audienceRaw = parseFrontmatterField(content, 'audience');
  const channelRaw = parseFrontmatterField(content, 'channel');

  const videoType = VALID_VIDEO_TYPES.includes(videoTypeRaw as VideoType)
    ? (videoTypeRaw as VideoType) : undefined;
  const audience = VALID_AUDIENCES.includes(audienceRaw as Audience)
    ? (audienceRaw as Audience) : undefined;

  const summaryMd = file;

  const serialMatch = file.match(/^(\d+)_/);
  const serialNumber = serialMatch ? parseInt(serialMatch[1], 10) : undefined;

  const processedAt = fs.statSync(mdPath).mtime.toISOString();

  return {
    id: videoId,
    title,
    youtubeUrl,
    language,
    durationSeconds,
    archived: false,
    ratings,
    overallScore,
    summaryMd,
    processedAt,
    ...(videoType !== undefined && { videoType }),
    ...(audience !== undefined && { audience }),
    ...(channelRaw ? { channel: channelRaw } : {}),
    ...(serialNumber !== undefined && { serialNumber }),
  };
}

export async function recoverOrphanedVideos(outputFolder: string): Promise<void> {
  const principal = getPrincipal(outputFolder);
  const { metadataStore: store } = getStorageBundle();
  const index = await store.readIndex(principal);
  const indexedIds = new Set(index.videos.map((v) => v.id));

  let files: string[];
  try {
    files = fs.readdirSync(outputFolder).filter(
      (f) => f.endsWith('.md') && !f.includes('-deep-dive'),
    );
  } catch {
    return;
  }

  for (const file of files) {
    const mdPath = path.join(outputFolder, file);
    try {
      const content = fs.readFileSync(mdPath, 'utf-8');
      const videoId = parseFrontmatterField(content, 'video_id');
      if (!videoId || indexedIds.has(videoId)) continue;

      const video = reconstructVideo(content, file, mdPath);
      if (video) {
        await store.upsertVideo(principal, video);
        indexedIds.add(videoId);
      }
    } catch {
      // Skip files that can't be parsed or indexed
    }
  }
}

export { slugify };

// formatDuration lives in its own pure module so client components can import it
// without pulling pipeline's server-only deps; re-exported here for existing importers.
export { formatDuration };


// Quick Reference callout transforms moved to the pure `lib/quick-view-callout.ts`
// (no fs/storage deps) so `summaryCore` and the cloud worker can use them without
// dragging in pipeline.ts's server-only graph. Re-exported here so existing callers
// that import them from `@/lib/pipeline` (regenerate + quick-view backfill routes) keep working.
export { stripQuickViewCallout, insertQuickViewCallout } from './quick-view-callout';

export async function runIngestion(
  playlistUrl: string,
  outputFolder: string,
  onProgress: (event: ProgressEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  // Check cheap env guard before I/O-bound assertOutputFolder
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) throw new Error('YOUTUBE_API_KEY is not set');

  const principal = getPrincipal(outputFolder);
  const { metadataStore: store } = getStorageBundle();
  fs.mkdirSync(outputFolder, { recursive: true });

  const metas = await fetchPlaylistVideos(playlistUrl, apiKey);

  // Stamp playlistUrl + human title into the index before processing. Title fetch
  // degrades to OMITTED on failure (network/auth/quota) — never persists a bare id.
  const playlistId = (() => { try { return new URL(playlistUrl).searchParams.get('list'); } catch { return null; } })();
  let playlistTitle: string | undefined;
  if (playlistId) {
    try { playlistTitle = await fetchPlaylistTitle(playlistId, apiKey); } catch { playlistTitle = undefined; }
  }
  await store.setPlaylistMeta(principal, { playlistUrl, playlistTitle });

  // Recover any .md files written in a prior interrupted run before processing new videos.
  await recoverOrphanedVideos(outputFolder);

  // Build the set of already-indexed IDs so we can skip re-processing them.
  const alreadyIndexed = new Set((await store.readIndex(principal)).videos.map((v) => v.id));

  // Progress is over NEW (not-yet-indexed) distinct videos only — skips are instant and
  // must not inflate the bar. playlistPos (below) stays the true playlist position.
  const newTotal = new Set(metas.filter((m) => !alreadyIndexed.has(m.videoId)).map((m) => m.videoId)).size;
  let newIndex = 0;

  onProgress({ type: 'start', total: newTotal });

  for (let i = 0; i < metas.length; i++) {
    // Check cancellation between videos — after any current video finishes cleanly.
    if (signal?.aborted) {
      onProgress({ type: 'cancelled' });
      return;
    }
    const meta = metas[i];
    const playlistPos = i + 1;
    // Tracks whether claimVideoSlot reserved a stub for this video in this run.
    // Set to false again once upsertVideo commits the full record — after that point
    // the video is fully indexed and must NOT be deleted on failure.
    let slotReservedThisRun = false;
    try {
      assertVideoId(meta.videoId); // defense-in-depth before any path construction

      if (alreadyIndexed.has(meta.videoId)) {
        continue;
      }

      newIndex += 1;

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Fetching transcript…', current: newIndex, total: newTotal });
      const { serialNumber } = await store.claimVideoSlot(principal, meta.videoId);
      slotReservedThisRun = true;
      const slug = slugify(meta.title);
      let baseSlug = slug;
      let counter = 2;
      // serialNumber makes filenames unique; collision suffix kept for slug readability only.
      while (fs.existsSync(path.join(outputFolder, applySerial(`${baseSlug}.md`, serialNumber)))) {
        baseSlug = `${slug}-${counter}`;
        counter++;
      }
      const baseName = `${padSerial(serialNumber)}_${baseSlug}`;
      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Generating summary…', current: newIndex, total: newTotal });
      const { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways } =
        await writeSummaryDoc({
          videoId: meta.videoId, title: meta.title, youtubeUrl: meta.youtubeUrl,
          channel: meta.channelTitle, durationSeconds: meta.durationSeconds, outputFolder, baseName,
        });

      const video: Video = {
        id: meta.videoId,
        title: meta.title,
        youtubeUrl: meta.youtubeUrl,
        language,
        durationSeconds: meta.durationSeconds,
        archived: false,
        ratings,
        overallScore,
        // serialNumber from claimVideoSlot must be threaded through — upsertVideo does a
        // full-replacement write, so omitting it here would silently erase the reserved serial.
        serialNumber,
        summaryMd: `${baseName}.md`,
        processedAt: new Date().toISOString(),
        docVersion: CURRENT_DOC_VERSION,
        // Stage 3 (§5.1): a first-generation MD reflects EMPTY corrections — mdHash('')
        // is deterministic and matches the compare path (Task 7 compares against
        // mdHash(reconciledCorrections), which is mdHash('') when no corrections exist).
        mdGeneratedAt: new Date().toISOString(),
        mdCorrectionsHash: mdHash(''),
        playlistIndex: playlistPos,
        ...(videoType !== undefined && { videoType }),
        ...(audience !== undefined && { audience }),
        ...(meta.channelTitle !== undefined && { channel: meta.channelTitle }),
        ...(tags !== undefined && { tags }),
        ...(tldr !== undefined && { tldr }),
        ...(takeaways !== undefined && { takeaways }),
        ...(meta.videoPublishedAt !== undefined && { videoPublishedAt: meta.videoPublishedAt }),
        ...(meta.addedToPlaylistAt !== undefined && { addedToPlaylistAt: meta.addedToPlaylistAt }),
      };
      // Index updated immediately after md write
      await store.upsertVideo(principal, video);
      // Mark as processed so within-run duplicates (same video appearing twice in the playlist) are skipped.
      alreadyIndexed.add(meta.videoId);
      slotReservedThisRun = false; // fully committed — nothing to roll back

      // Pre-generate the summary HTML doc so it opens instantly (no on-demand Gemini wait).
      // Best-effort: the .md is already written and the video already upserted, so a transform
      // failure must never fail the video or abort the batch — it just defers HTML to on-demand.
      // No-op onProgress keeps runHtmlDoc's own events off the ingest stream. Opt out with
      // PREGEN_SUMMARY_HTML=off (mirrors DIG_CROP=off).
      if (process.env.PREGEN_SUMMARY_HTML !== 'off') {
        onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Generating HTML doc…', current: newIndex, total: newTotal });
        try {
          await runHtmlDoc(meta.videoId, outputFolder, () => {});
        } catch (err) {
          // Best-effort: defer to on-demand. Log with videoId so the deferred SSE step is
          // correlatable to a cause (the underlying Gemini failure also logs upstream).
          console.warn(`[pregen-html] deferred for ${meta.videoId}: ${err instanceof Error ? err.message : String(err)}`);
          onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'HTML doc deferred (will generate on open)', current: newIndex, total: newTotal });
        }
      }

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Saved', current: newIndex, total: newTotal });
    } catch (err) {
      // Roll back the reserved stub so the video is retried on the next sync.
      // Best-effort: a delete failure must not shadow the original error.
      if (slotReservedThisRun) {
        try { await store.deleteVideo(principal, meta.videoId); } catch { /* ignore */ }
      }
      const log = err instanceof Error ? err.message : String(err);
      onProgress({ type: 'error', videoId: meta.videoId, title: meta.title, log });
    }
  }

  // Reconcile removedFromPlaylist: auto-archive on removal, clear flag if video returns.
  await store.reconcilePlaylistMembership(principal, metas.map((m) => m.videoId));


exec
/bin/bash -lc "sed -n '1,220p' types/index.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import { z } from 'zod';

// --- Rating value: integer 1–5 ---
export const RatingValueSchema = z.union([
  z.literal(1), z.literal(2), z.literal(3), z.literal(4), z.literal(5),
]);
export type RatingValue = z.infer<typeof RatingValueSchema>;

// --- Ratings ---
export const RatingsSchema = z.object({
  usefulness: RatingValueSchema,
  depth: RatingValueSchema,
  originality: RatingValueSchema,
  recency: RatingValueSchema,
  completeness: RatingValueSchema,
});
export type Ratings = z.infer<typeof RatingsSchema>;

// --- VideoType and Audience: Gemini-classified fields ---
export const VideoTypeSchema = z.enum([
  'Tutorial', 'Analysis', 'Case Study', 'Framework', 'Demo', 'Interview',
]);
export type VideoType = z.infer<typeof VideoTypeSchema>;

export const AudienceSchema = z.enum(['Beginner', 'Intermediate', 'Advanced']);
export type Audience = z.infer<typeof AudienceSchema>;

// --- VideoMeta: intermediate shape from YouTube API, before ratings/summary exist ---
export const VideoMetaSchema = z.object({
  videoId: z.string(), // YouTube video ID (not the playlist item ID)
  title: z.string(),
  youtubeUrl: z.string().url(),
  durationSeconds: z.number().int().nonnegative(),
  channelTitle: z.string().optional(),
  videoPublishedAt: z.string().datetime().optional(),
  addedToPlaylistAt: z.string().datetime().optional(),
  liveBroadcastContent: z.string().optional(),
});
export type VideoMeta = z.infer<typeof VideoMetaSchema>;

export const DocVersionSchema = z.object({
  major: z.number().int().nonnegative(),
  minor: z.number().int().nonnegative(),
});

// --- Video: one entry in playlist-index.json ---
export const VideoSchema = z.object({
  id: z.string(),
  title: z.string(),
  youtubeUrl: z.string().url(),
  language: z.enum(['en', 'ko']),
  durationSeconds: z.number().int().nonnegative(),
  archived: z.boolean(),
  ratings: RatingsSchema,
  overallScore: z.number().min(1).max(5), // average of 5 ratings, may be fractional
  summaryMd: z.string().nullable(),
  summaryHtml: z.string().nullable().optional(),
  digDeeperMd: z.string().nullable().optional(),
  digDeeperHtml: z.string().nullable().optional(),
  processedAt: z.string().datetime(),
  videoType: VideoTypeSchema.optional(),
  audience: AudienceSchema.optional(),
  channel: z.string().optional(),
  tags: z.array(z.string()).optional(),
  removedFromPlaylist: z.boolean().optional(),
  playlistIndex: z.number().int().positive().optional(),
  serialNumber: z.number().int().positive().optional(),
  videoPublishedAt: z.string().datetime().optional(),
  addedToPlaylistAt: z.string().datetime().optional(),
  personalScore: z.number().int().min(1).max(5).optional(),
  personalNote: z.string().max(500).optional(),
  tldr: z.string().optional(),
  takeaways: z.array(z.string()).optional(),
  corrections: z.string().optional(),
  docVersion: DocVersionSchema.optional(), // absent ⇒ pre-feature {1,0}; stamped to CURRENT_DOC_VERSION on (re)generation
  // Cloud-only (Stage 2a Task 1): sourced from videos.updated_at (readIndex), never persisted
  // in the local FS JSON, so it must stay optional for back-compat. `{ offset: true }` is
  // required (not just `Z`) because PostgREST serializes timestamptz as e.g.
  // "2026-07-11T01:12:57.796832+00:00" — an offset suffix, not "Z" — so the default
  // Z-only datetime() would reject every real DB-sourced value.
  updatedAt: z.string().datetime({ offset: true }).optional(),
  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
  // Optional → the local path never sets it (same back-compat pattern as updatedAt). Gates the
  // cloud View/Download/Share menu items; the serving route enforces the same predicate server-side.
  summaryReady: z.boolean().optional(),
  // Stage 3 Cloud Sync (§5.1): generated-MD signals — stamped on (re)generation.
  mdGeneratedAt: z.string().datetime({ offset: true }).optional(),
  mdCorrectionsHash: z.string().optional(),
  // Per-field human-edit timestamps (§5.1). A clear stamps the timestamp while removing the value.
  annotationsEditedAt: z
    .object({
      personalNote: z.string().datetime({ offset: true }).optional(),
      personalScore: z.string().datetime({ offset: true }).optional(),
      corrections: z.string().datetime({ offset: true }).optional(),
    })
    .optional(),
});
export type Video = z.infer<typeof VideoSchema>;

// --- PlaylistIndex: root of playlist-index.json ---
export const PlaylistIndexSchema = z.object({
  playlistUrl: z.union([z.string().url(), z.literal('')]),   // '' = absent-index sentinel (empty read)
  playlistTitle: z.string().optional(),
  outputFolder: z.string(),
  videos: z.array(VideoSchema),
});
export type PlaylistIndex = z.infer<typeof PlaylistIndexSchema>;

// --- ProgressEvent: discriminated union for SSE events ---
export const ProgressEventSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('start'),
    total: z.number().int().nonnegative().optional(),
    log: z.string().optional(),
  }),
  z.object({
    type: z.literal('step'),
    videoId: z.string().optional(),
    title: z.string().optional(),
    step: z.string(),
    current: z.number().int().positive().optional(),
    total: z.number().int().positive().optional(),
  }),
  z.object({
    type: z.literal('done'),
    current: z.number().int().positive().optional(),
    total: z.number().int().nonnegative().optional(),
    succeeded: z.number().int().nonnegative().optional(),
    failed: z.number().int().nonnegative().optional(),
    log: z.string().optional(), // optional terminal detail, e.g. the saved PDF filename
  }),
  z.object({
    type: z.literal('error'),
    videoId: z.string().optional(),
    title: z.string().optional(),
    log: z.string(),
  }),
  z.object({
    type: z.literal('cancelled'),
  }),
]);
export type ProgressEvent = z.infer<typeof ProgressEventSchema>;
export type ProgressEventType = ProgressEvent['type'];

// --- Gemini response type for generateSummary ---
export interface GeminiSummaryResponse {
  summary: string;
  ratings: Ratings;
  overallScore: number;
  videoType?: VideoType;
  audience?: Audience;
  tags?: string[];
  tldr?: string;
  takeaways?: string[];
}

// --- Filter state for client-side filtering ---
export interface FilterState {
  searchText: string;
  language: 'all' | 'en' | 'ko';
  videoType: 'all' | VideoType;
  audience: 'all' | Audience;
  minScore: number;
  minPersonalScore: number;  // 0 = no filter; 1–5 = minimum personal score; unscored shown dimmed
}
export const FILTER_DEFAULTS: FilterState = {
  searchText: '',
  language: 'all',
  videoType: 'all',
  audience: 'all',
  minScore: 0,
  minPersonalScore: 0,
};

// --- Sort types for GET /api/videos ---
type RatingSortColumn = keyof Ratings;
// 'overall' maps to Video.overallScore; all others map directly to Ratings fields.
export type SortColumn = 'name' | 'overall' | RatingSortColumn | 'language' | 'videoType' | 'audience' | 'serialNumber' | 'videoPublishedAt' | 'addedToPlaylistAt' | 'personalScore' | 'channel' | 'durationSeconds';
export type SortOrder = 'asc' | 'desc';

exec
/bin/bash -lc "sed -n '1,260p' app/api/videos/[id]/regenerate/route.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import path from 'path';
import fs from 'fs';
import { NextResponse } from 'next/server';
import { assertVideoId } from '../../../../../lib/index-store';
import { getPrincipal, getStorageBundle } from '../../../../../lib/storage/resolve';
import { fixSummary, extractQuickView } from '../../../../../lib/gemini';
import { stripQuickViewCallout, insertQuickViewCallout } from '../../../../../lib/pipeline';
import { logError, errorSummary } from '../../../../../lib/dev-logger';
import { mdHash } from '../../../../../lib/cloud-sync/content-hash';

type Params = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  const outputFolder = body?.outputFolder;
  const corrections = body?.corrections;

  if (!outputFolder || typeof outputFolder !== 'string') {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
  }

  let principal;
  try {
    principal = getPrincipal(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  const { metadataStore: store } = getStorageBundle();
  const index = await store.readIndex(principal);
  const video = index.videos.find((v) => v.id === videoId);

  if (!video) {
    return NextResponse.json({ error: 'video not found' }, { status: 404 });
  }

  if (!video.summaryMd) {
    return NextResponse.json({ error: 'no summary file for this video' }, { status: 422 });
  }

  try {
    const mdPath = path.join(outputFolder, video.summaryMd);
    let mdContent = await fs.promises.readFile(mdPath, 'utf-8');

    // Save corrections to index before the Gemini call so a subsequent
    // page-refresh shows the latest corrections even if Gemini fails.
    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    if (trimmedCorrections) {
      await store.updateVideoFields(principal, videoId, { corrections: trimmedCorrections });
    } else if (corrections === '') {
      await store.updateVideoFields(principal, videoId, { corrections: undefined });
    }

    // Apply text corrections if provided (works on prose only — callout is stripped first)
    const stripped = stripQuickViewCallout(mdContent);
    const fixed = trimmedCorrections ? await fixSummary(stripped, trimmedCorrections) : stripped;

    // Re-extract tldr/takeaways from corrected content and re-insert callout
    const { tldr, takeaways } = await extractQuickView(fixed);
    const updatedContent = insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? []);

    await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');

    // Stage 3 (§5.1/§5.7, former-Blocking §5.3): stamp this regenerated MD as
    // corrections-current. The corrections THIS MD now reflects mirrors the conditional
    // update above: param non-empty → trimmedCorrections; param === '' → cleared to '';
    // param absent/whitespace-only (neither branch fires) → the UNCHANGED stored value —
    // a bare regenerate keeps prior corrections baked in, so stamping mdHash('') there
    // would wrongly mark a still-corrected MD as stale.
    const effectiveCorrections = trimmedCorrections
      ? trimmedCorrections
      : corrections === '' ? '' : (video.corrections ?? '');

    // Update index with refreshed quick-view data; clear stale HTML cache. NOTE: this write
    // carries MD-currency fields, not a Class-B key, so it must NOT bump annotationsEditedAt
    // (the earlier updateVideoFields({ corrections }) call above is the Class-B write that
    // stamps annotationsEditedAt.corrections).
    await store.updateVideoFields(principal, videoId, {
      tldr, takeaways, summaryHtml: null,
      mdGeneratedAt: new Date().toISOString(),
      mdCorrectionsHash: mdHash(effectiveCorrections),
    });

    return NextResponse.json({
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
  } catch (err) {
    logError(`regenerate:${videoId}`, err);
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  }
}

exec
/bin/bash -lc "sed -n '1,260p' scripts/cloud-sync.ts && sed -n '1,180p' scripts/check-service-confinement.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
// scripts/cloud-sync.ts
//
// Stage 3 Cloud Sync (§9) — the local CLI entrypoint. Wires the authenticated USER-session
// Supabase client into runSync() so a developer/operator can pull cloud changes into their local
// replica (and vice versa) without ever touching the service-role key. `login`/`logout` manage a
// long-lived refresh token via lib/cloud-sync/auth's file-backed TokenStore; `sync` (the default)
// reconciles every union playlist, or one via `--playlist <key>`.
//
// Data-root convention: this project's LOCAL playlist roots are NOT an env var — they are
// lib/settings-store.ts's settings.json (`baseOutputFolder` when set, the parent directory that
// holds every playlist subfolder; falling back to the single-playlist `outputFolder`, which itself
// falls back to the OUTPUT_FOLDER env var when settings.json is absent). This mirrors exactly what
// app/api/resolve-folder/route.ts reads, and what lib/cloud-sync/registry.ts's
// discoverLocalPlaylists() expects: a root whose subdirectories are playlist folders. An optional
// CLOUD_SYNC_DATA_ROOTS override (colon-separated) is supported for scripting/testing convenience.
import { getAuthedClient, signIn, signOut, NoSessionError } from '@/lib/cloud-sync/auth';
import { runSync, type SyncDeps } from '@/lib/cloud-sync/sync-run';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { readSettings } from '@/lib/settings-store';

export interface ParsedArgs { cmd: 'sync' | 'login' | 'logout'; playlistKey?: string; }

export function parseArgs(argv: string[]): ParsedArgs {
  if (argv[0] === 'login') return { cmd: 'login' };
  if (argv[0] === 'logout') return { cmd: 'logout' };
  const i = argv.indexOf('--playlist');
  return i >= 0 && argv[i + 1] ? { cmd: 'sync', playlistKey: argv[i + 1] } : { cmd: 'sync' };
}

/** Real local data-root convention (see file header): settings.json's baseOutputFolder/
 *  outputFolder — NOT a DATA_ROOT env var, which does not exist anywhere else in this codebase. */
function resolveDataRoots(): string[] {
  const override = process.env.CLOUD_SYNC_DATA_ROOTS;
  if (override) return override.split(':').filter(Boolean);
  const settings = readSettings();
  const root = settings.baseOutputFolder || settings.outputFolder;
  return root ? [root] : [];
}

export async function main(argv: string[]): Promise<number> {
  const args = parseArgs(argv);
  if (args.cmd === 'login') {
    const [email, password] = [process.env.CLOUD_SYNC_EMAIL, process.env.CLOUD_SYNC_PASSWORD];
    if (!email || !password) { console.error('Set CLOUD_SYNC_EMAIL and CLOUD_SYNC_PASSWORD to log in.'); return 1; }
    await signIn(email, password); console.log('Signed in.'); return 0;
  }
  if (args.cmd === 'logout') { await signOut(); console.log('Signed out.'); return 0; }

  let client;
  try { client = await getAuthedClient(); }
  catch (e) { if (e instanceof NoSessionError) { console.error(e.message); return 1; } throw e; }

  const { data } = await client.auth.getUser();
  const ownerId = data.user!.id;
  const dataRoots = resolveDataRoots();

  const deps: SyncDeps = {
    local: localMetadataStore,
    cloud: new SupabaseMetadataStore(client),
    localBlob: localBlobStore,
    cloudBlob: new SupabaseBlobStore(client, ARTIFACTS_BUCKET),
    dataRoots, ownerId,
  };
  const report = await runSync(deps, args.playlistKey ? { playlistKey: args.playlistKey } : {});
  console.log(JSON.stringify(report, null, 2));
  return report.errors.length ? 2 : 0;
}

if (require.main === module) {
  main(process.argv.slice(2)).then((code) => process.exit(code)).catch((e) => { console.error(e); process.exit(1); });
}
import fs from 'fs';
import path from 'path';

const ROOT = process.cwd();
const TARGET = path.join(ROOT, 'lib/supabase/service.ts');

function resolveImport(fromFile: string, spec: string): string | null {
  let base: string;
  if (spec.startsWith('@/')) base = path.join(ROOT, spec.slice(2));
  else if (spec.startsWith('.')) base = path.resolve(path.dirname(fromFile), spec);
  else if (path.isAbsolute(spec)) base = spec;   // absolute path (e.g. from test fixtures)
  else return null;                               // bare package import — not our code
  const candidates = base.endsWith('.ts') || base.endsWith('.tsx')
    ? [base]
    : ['.ts', '.tsx', '.js', '/index.ts', '/index.tsx'].map((e) => base + e);
  for (const cand of candidates) {
    if (fs.existsSync(cand) && fs.statSync(cand).isFile()) return cand;
  }
  return null;
}

/** Codex H3: match named/default/namespace `from` imports, bare SIDE-EFFECT imports
 *  (`import 'x'`), re-exports (`export ... from 'x'`), and dynamic `import('x')`. */
export function extractImportSpecifiers(src: string): string[] {
  const out: string[] = [];
  const patterns = [
    /(?:import|export)\s[^;'"]*?from\s*['"]([^'"]+)['"]/g, // import/export ... from '...'
    /import\s*['"]([^'"]+)['"]/g,                          // side-effect: import '...'
    /import\(\s*['"]([^'"]+)['"]\s*\)/g,                   // dynamic import('...')
    /require\(\s*['"]([^'"]+)['"]\s*\)/g,                  // require('...')
  ];
  for (const re of patterns) for (let m; (m = re.exec(src)); ) out.push(m[1]);
  return out;
}

export function reachesService(entry: string): boolean {
  const seen = new Set<string>();
  const stack = [entry];
  while (stack.length) {
    const f = stack.pop()!;
    if (seen.has(f)) continue;
    seen.add(f);
    if (path.resolve(f) === TARGET) return true;
    if (!fs.existsSync(f)) continue;
    for (const spec of extractImportSpecifiers(fs.readFileSync(f, 'utf8'))) {
      const r = resolveImport(f, spec);
      if (r) stack.push(r);
    }
  }
  return false;
}

function walk(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return /\.(ts|tsx)$/.test(e.name) ? [p] : [];
  });
}

/** Codex H2: every user-facing entry — not just app/**. */
export function collectEntrypoints(): string[] {
  const entries = [
    ...walk(path.join(ROOT, 'app')),
    ...walk(path.join(ROOT, 'pages')),
    ...walk(path.join(ROOT, 'worker')),
    // Task 10 (§6): the local cloud-sync CLI is a user-facing entrypoint whose whole point is to
    // hold NO service-role key. `scripts/` was previously unwalked, so a stray service-role import
    // there (or transitively via lib/cloud-sync/*) would pass undetected — making that guarantee
    // vacuous. Walk lib/cloud-sync/ directly (it exists now) and every scripts/*.ts file — `walk()`
    // only ever returns files that already exist on disk, so this naturally tolerates
    // `scripts/cloud-sync.ts` not existing yet (it lands in Task 13) without hardcoding its path or
    // crashing `npm run check:confinement` today; it auto-covers the file once it's created.
    ...walk(path.join(ROOT, 'lib/cloud-sync')),
    ...walk(path.join(ROOT, 'scripts')),
  ];
  const mw = path.join(ROOT, 'middleware.ts');
  if (fs.existsSync(mw)) entries.push(mw);
  return entries;
}

/** Stage 1D (H-B, reviewed): the two-client split requires the enqueue route to build the
 *  service-role `Enqueuer` (`enqueue`/`preflight` are service_role-only RPC grants as of
 *  migration 0011 — anon/authenticated execute was revoked). This is one deliberately
 *  authorized entrypoint; everything else must still be unreachable.
 *
 *  Stage 1F-b (spec D4/D16): the anonymous `/s/[token]` share-serve route is the second (and,
 *  per spec, the ONLY other) deliberately authorized `service_role` entrypoint — there is no
 *  session to scope RLS by for an anonymous visitor, so it uses a runtime `get`-only blob-store
 *  wrapper plus `getShareServeContext`'s explicit confused-deputy guard instead of RLS.
 *
 *  Task 6 (cloud dig trigger): the dig route is the third deliberately authorized entrypoint —
 *  it builds `SupabaseEnqueuer(createServiceClient())` for the enqueue RPC ONLY, mirroring
 *  app/api/jobs/route.ts's two-client split. The `profiles.is_anonymous` tenant read still goes
 *  through the SESSION client (RLS), never the service client — see enqueue-dig-core.ts. */
const ALLOWED_SERVICE_IMPORTERS = [
  path.join(ROOT, 'app/api/jobs/route.ts'),
  path.join(ROOT, 'app/s/[token]/route.ts'),
  path.join(ROOT, 'app/api/videos/[id]/dig/[sectionId]/route.ts'),
];

export function findServiceImporters(): string[] {
  return collectEntrypoints()
    .filter((e) => path.resolve(e) !== TARGET && reachesService(e))
    .filter((e) => !ALLOWED_SERVICE_IMPORTERS.includes(path.resolve(e)));
}

if (require.main === module) {
  const violators = findServiceImporters();
  if (violators.length) {
    console.error('service.ts reachable from a user-facing entrypoint:\n' + violators.join('\n'));
    process.exit(1);
  }
  console.log('service_role confinement OK');
}

exec
/bin/bash -lc "sed -n '1,260p' lib/html-doc/read-model.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { MagazineModel } from './types';
import type { Principal } from '@/lib/storage/principal';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';
import { GENERATOR_VERSION } from './constants';
import { readModelEnvelope } from './model-store';

// GENERATE-FREE LEAF (spec D13/B18c): this module and its entire import graph must never
// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
// /s/[token] route therefore cannot pull in the charging code. Enforced by tests/lib/share/
// import-guard.test.ts (a jest grep guard; the repo has no ESLint).

export function sameTitles(
  envelope: { sourceSections: string[] },
  titles: string[],
): boolean {
  return envelope.sourceSections.length === titles.length &&
    envelope.sourceSections.every((t, i) => t === titles[i]);
}

export function isFresh(
  envelope: { sourceSections: string[]; generatorVersion?: string },
  titles: string[],
): boolean {
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
}

/** Read-only, generation-free: returns the cached model iff present AND fresh; otherwise
 *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call). */
export async function readFreshMagazineModel(args: {
  blobStore: ReadOnlyBlobStore;
  principal: Principal;
  base: string;
  titles: string[];
}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }> {
  const { blobStore, principal, base, titles } = args;
  const existing = await readModelEnvelope(principal, base, blobStore);
  if (existing && isFresh(existing, titles)) return { status: 'ok', model: existing.model };
  return { status: 'not_ready' };
}

/** Title-stable read (spec D5): returns the cached model iff the envelope exists AND its section
 *  titles match `titles` (generator version may differ — the version-bump case). Positionally
 *  coherent to render against current markdown. Never reserves/generates (pure blob read). */
export async function readTitleStableModel(args: {
  blobStore: ReadOnlyBlobStore;
  principal: Principal;
  base: string;
  titles: string[];
}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'none' }> {
  const { blobStore, principal, base, titles } = args;
  const existing = await readModelEnvelope(principal, base, blobStore);
  if (existing && sameTitles(existing, titles)) return { status: 'ok', model: existing.model };
  return { status: 'none' };
}

exec
/bin/bash -lc 'rg -n "sourceMdHash|readFreshMagazineModel|readTitleStableModel" lib/html-doc tests/lib tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/html-doc/model-store.ts:22:    sourceMdHash: z.string().optional(),
lib/html-doc/model-store.ts:24:  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
lib/html-doc/generate.ts:59:    sourceMdHash: mdHash(md),
lib/html-doc/read-model.ts:29:export async function readFreshMagazineModel(args: {
lib/html-doc/read-model.ts:44:export async function readTitleStableModel(args: {
lib/html-doc/serve-summary-core.ts:114:    mdBody, // Stage 3 (§4.2): hashed into sourceMdHash on a fresh materialize, not the key.
lib/html-doc/serve-doc.ts:8:import { readFreshMagazineModel, readTitleStableModel } from './read-model';
lib/html-doc/serve-doc.ts:47:   *  into the envelope's sourceMdHash on a fresh materialize. Optional for back-compat with
lib/html-doc/serve-doc.ts:48:   *  callers that pre-date this signal (sourceMdHash is an optional envelope field); the
lib/html-doc/serve-doc.ts:56:  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:71:      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:78:      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
lib/html-doc/serve-doc.ts:110:      ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
tests/lib/html-doc/read-model.test.ts:7:import { readFreshMagazineModel, isFresh, sameTitles, readTitleStableModel } from '@/lib/html-doc/read-model';
tests/lib/html-doc/read-model.test.ts:37:describe('readFreshMagazineModel', () => {
tests/lib/html-doc/read-model.test.ts:42:    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:51:    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:57:    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:70:describe('readTitleStableModel', () => {
tests/lib/html-doc/read-model.test.ts:75:    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:81:    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/html-doc/read-model.test.ts:86:    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
tests/lib/cloud-sync/companion.test.ts:4:const env = (sourceMdHash?: string): ModelEnvelope => ({
tests/lib/cloud-sync/companion.test.ts:7:  ...(sourceMdHash ? { sourceMdHash } : {}),
tests/lib/cloud-sync/companion.test.ts:17:it('deletes when the legacy envelope lacks sourceMdHash', () => {
tests/lib/cloud-sync/schema.test.ts:32:  it('accepts an optional sourceMdHash', () => {
tests/lib/cloud-sync/schema.test.ts:33:    expect(ModelEnvelopeSchema.parse({ ...env, sourceMdHash: 'deadbeef' }).sourceMdHash).toBe('deadbeef');
tests/lib/cloud-sync/model-writer-hash.test.ts:4:// and asserts the persisted model envelope's sourceMdHash is the hash of the MD BODY that was
tests/lib/cloud-sync/model-writer-hash.test.ts:70:it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:81:  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
tests/lib/cloud-sync/model-writer-hash.test.ts:82:  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)

exec
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '120,240p;300,430p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
   150	  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
   151	
   152	  let wroteBlob = false;
   153	  if (video.summaryMd && mdBody != null) {
   154	    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
   155	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
   156	    const staged = await toBlob.get(toP, ref.tempKey);
   157	    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
   158	      throw new Error(`additive staged MD verify failed for ${video.id}`);
   159	    }
   160	    await toBlob.promote(ref);
   161	    wroteBlob = true;
   162	  }
   163	
   164	  const sanitized: any = sanitizeAdditiveVideo(video);
   165	  if (slot) {
   166	    sanitized.serialNumber = slot.serialNumber;
   167	    sanitized.playlistIndex = slot.position + 1;
   168	  }
   169	  if (wroteBlob) {
   170	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
   171	  }
   172	  await to.upsertVideo(toP, sanitized as Video);
   173	
   174	  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
   175	  // (an update against an absent row silently no-ops; never advance a baseline for that).
   176	  const after = await to.readIndex(toP);
   177	  if (!after.videos.some((v) => v.id === video.id)) {
   178	    throw new Error(`additive create did not persist receiver row for ${video.id}`);
   179	  }
   180	}
   181	
   182	/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
   183	 *  side's values, so this is a true agreed baseline. */
   184	function baselineFromOneSided(
   185	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
   186	): VideoBaseline {
   187	  const classB = {} as VideoBaseline['classB'];
   188	  for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
   189	  return {
   190	    classA: {
   191	      docVersionMajor: classA.docVersionMajor,
   192	      mdGeneratedAt: classA.mdGeneratedAt,
   193	      mdCorrectionsHash: classA.mdCorrectionsHash,
   194	      mdHash: mdHashVal,
   195	    },
   196	    classB,
   197	  };
   198	}
   199	
   200	/** Behaviors #12 + F3 — apply each Class-B winner to the LOSER side, carrying the SOURCE timestamp
   201	 *  (never now()). A conflict is logged and, when the merge picked no winner (winner==='equal'), the
   202	 *  loser value is skipped (not written). Every write MUST land (found:true) or it throws — a no-op
   203	 *  write on an absent row would let buildBaseline record a false agreement. */
   204	async function applyClassBWinners(args: {
   205	  deps: SyncDeps; localP: Principal; cloudP: Principal; videoId: string;
   206	  merges: Record<HumanField, FieldMerge>; localSnap: HumanSnapshot; cloudSnap: HumanSnapshot;
   207	  dataRoot: string; key: string;
   208	}): Promise<{ merged: number; conflicts: number }> {
   209	  const { deps, localP, cloudP, videoId, merges, localSnap, cloudSnap, dataRoot, key } = args;
   210	  let merged = 0;
   211	  let conflicts = 0;
   212	
   213	  for (const f of FIELDS) {
   214	    const m = merges[f];
   215	    if (m.conflict) {
   216	      await appendConflict(dataRoot, key, {
   217	        video_id: videoId, class: 'B', field: f,
   218	        valueL: localSnap[f].value, valueR: cloudSnap[f].value,
   219	        reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
   220	      });
   221	      conflicts += 1;
   222	    }
   223	    if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write
   224	
   225	    // winner is on one side → the OTHER (loser) side receives the winning value.
   226	    const target: Side = m.winner === 'local'
   227	      ? { store: deps.cloud, p: cloudP, blob: deps.cloudBlob }
   228	      : { store: deps.local, p: localP, blob: deps.localBlob };
   229	    const set: Record<string, string | number> = {};
   230	    const clear: HumanField[] = [];
   231	    if (m.value === undefined) clear.push(f);
   232	    else set[f] = m.value;
   233	
   234	    const { found } = await target.store.updateVideoAnnotations(
   235	      target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
   236	    );
   237	    if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
   238	    merged += 1;
   239	  }
   240	  return { merged, conflicts };
   300	): Promise<{ shareNeedsOwnerServe: boolean }> {
   301	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   302	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   303	  const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
   304	  const decision = decideCompanion({ winnerMdHash, senderEnvelope });
   305	  if (decision.kind === 'ship') {
   306	    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
   307	    return { shareNeedsOwnerServe: false };
   308	  }
   309	  // deleteReceiverModel — best-effort; a missing model blob is not an error.
   310	  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   311	  return { shareNeedsOwnerServe: true };
   312	}
   313	
   314	/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
   315	 *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
   316	 *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
   317	 *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
   318	 *  recording the winner there would be a false agreement → next-run silent overwrite). */
   319	function buildBaseline(
   320	  winnerSignals: ClassASignals, winnerMdHash: string | null,
   321	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   322	): VideoBaseline {
   323	  const classB = {} as VideoBaseline['classB'];
   324	  for (const f of FIELDS) {
   325	    const m = merges[f];
   326	    if (m.winner === 'equal' && m.conflict) {
   327	      classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
   328	    } else {
   329	      classB[f] = { value: m.value, editedAt: m.editedAt };
   330	    }
   331	  }
   332	  return {
   333	    classA: {
   334	      docVersionMajor: winnerSignals.docVersionMajor,
   335	      mdGeneratedAt: winnerSignals.mdGeneratedAt,
   336	      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
   337	      mdHash: winnerMdHash,
   338	    },
   339	    classB,
   340	  };
   341	}
   342	
   343	export async function runSync(
   344	  deps: SyncDeps, opts: { playlistKey?: string } = {},
   345	): Promise<SyncReport> {
   346	  resetConflictDedup();
   347	  const report: SyncReport = {
   348	    created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
   349	    mergedFields: 0, conflictsLogged: 0, removed: 0,
   350	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   351	  };
   352	
   353	  const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   354	  const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   355	  const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   356	  let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   357	  if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
   358	
   359	  for (const key of keys) {
   360	    const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
   361	      ?? hydrationRoot(deps.dataRoots, key);
   362	    await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
   363	
   364	    const localP = localPrincipal(dataRoot);
   365	    const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
   366	    const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
   367	    const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
   368	    const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
   369	    const manifest = await readManifest(dataRoot, key);
   370	
   371	    for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
   372	      try {
   373	        const lv = await readVideo(deps.local, localP, id);
   374	        const cv = await readVideo(deps.cloud, cloudP, id);
   375	        const base = manifest.videos[id];
   376	
   377	        // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
   378	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
   379	        if (!lv || !cv) {
   380	          const present = (lv ?? cv)!;
   381	          const presentIsLocal = lv != null;
   382	          if (base) {
   383	            report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
   384	          } else {
   385	            const from: Side = presentIsLocal ? localSide : cloudSide;
   386	            const to: Side = presentIsLocal ? cloudSide : localSide;
   387	            const body = await readMdBody(from.blob, from.p, present);
   388	            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
   389	            report.created += 1; // reached only after the receiver row is confirmed
   390	            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
   391	              deriveClassASignals(present, body), body ? mdHash(body) : null,
   392	              deriveHumanSnapshot(present),
   393	            ));
   394	          }
   395	          continue;
   396	        }
   397	
   398	        // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
   399	        const localSnap = deriveHumanSnapshot(lv);
   400	        const cloudSnap = deriveHumanSnapshot(cv);
   401	        const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
   402	        const applied = await applyClassBWinners({
   403	          deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
   404	        });
   405	        report.mergedFields += applied.merged;
   406	        report.conflictsLogged += applied.conflicts;
   407	        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
   408	
   409	        // ── Class A (needs the MD bodies for hashing — Behavior #1).
   410	        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
   411	        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
   412	        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
   413	        if (decision.needsRegen) report.needsRegen += 1;
   414	
   415	        let winnerMdHash: string | null = null;
   416	        let winnerSignals: ClassASignals = la;
   417	        let winnerSide: Side | null = null;
   418	        let loserSide: Side | null = null;
   419	        let winnerVideo: Video = lv;
   420	
   421	        if (decision.action === 'copyToCloud') {
   422	          winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
   423	          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
   424	          report.updatedCloud += 1;
   425	        } else if (decision.action === 'copyToLocal') {
   426	          winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
   427	          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
   428	          report.updatedLocal += 1;
   429	        } else {
   430	          report.skippedIdentical += 1;

exec
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '80,123p;240,299p;421,455p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
   240	  return { merged, conflicts };
   241	}
   242	
   243	/** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
   244	 *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
   245	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
   246	 *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
   247	async function transferClassA(
   248	  winner: Side, loser: Side, winnerVideo: Video, videoId: string,
   249	): Promise<{ mdHash: string; verified: boolean }> {
   250	  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   251	  if (body == null || !winnerVideo.summaryMd) {
   252	    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   253	  }
   254	  const h = mdHash(body);
   255	  const key = winnerVideo.summaryMd;
   256	
   257	  const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   258	  const staged = await loser.blob.get(loser.p, ref.tempKey);
   259	  if (!staged || mdHash(staged.toString('utf8')) !== h) {
   260	    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   261	  }
   262	  // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   263	  // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   264	  // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   265	  // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   266	  // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   267	  // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   268	  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   269	  // (below) advertises promoted only after this resolves.
   270	  await loser.blob.put(loser.p, key, staged, 'text/markdown');
   271	  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
   272	
   273	  const wv: any = winnerVideo;
   274	  const completeTuple: any = {
   275	    summaryMd: key,
   276	    docVersion: wv.docVersion,
   277	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
   278	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
   279	    ratings: wv.ratings,
   280	    overallScore: wv.overallScore,
   281	    videoType: wv.videoType,
   282	    audience: wv.audience,
   283	    tags: wv.tags,
   284	    tldr: wv.tldr,
   285	    takeaways: wv.takeaways,
   286	    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
   287	    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
   288	    artifacts: { summaryMd: { key, status: 'promoted' } },
   289	  };
   290	  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
   291	
   292	  return { mdHash: h, verified: true };
   293	}
   294	
   295	/** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
   296	 *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
   297	 *  that the owner must re-serve to regenerate the share model. */
   298	async function companionTransfer(
   299	  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
   421	        if (decision.action === 'copyToCloud') {
   422	          winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
   423	          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
   424	          report.updatedCloud += 1;
   425	        } else if (decision.action === 'copyToLocal') {
   426	          winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
   427	          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
   428	          report.updatedLocal += 1;
   429	        } else {
   430	          report.skippedIdentical += 1;
   431	          winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
   432	        }
   433	
   434	        if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
   435	          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
   436	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
   437	        }
   438	        if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   439	
   440	        // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
   441	        //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
   442	        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
   443	      } catch (e: any) {
   444	        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
   445	      }
   446	    }
   447	  }
   448	
   449	  return report;
   450	}

exec
/bin/bash -lc "nl -ba lib/html-doc/read-model.ts | sed -n '20,62p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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

codex
I found a candidate around companion freshness: the sync path can correctly decide “do not ship this model,” but serving still treats models as fresh without checking `sourceMdHash`. I’m validating that against the guards/tests so I don’t report something that is already intentionally covered elsewhere.
exec
/bin/bash -lc 'npm test -- --runInBand tests/lib/cloud-sync/import-guard.test.ts tests/lib/cloud-sync/content-hash.test.ts tests/lib/cloud-sync/schema.test.ts tests/lib/cloud-sync/reconcile-class-a.test.ts tests/lib/cloud-sync/reconcile-class-b.test.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'npx tsx scripts/check-service-confinement.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "sed -n '1,240p' tests/lib/cloud-sync/import-guard.test.ts && sed -n '1,220p' tests/lib/cloud-sync/model-writer-hash.test.ts && sed -n '1,180p' tests/lib/html-doc/read-model.test.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import { readFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';

// Filesystem walk — NOT `git ls-files` (which sees only tracked files, so a new-but-uncommitted
// cloud-sync source would be skipped and the guard would pass vacuously). Assert the scan is
// non-empty so an empty/broken scan (e.g. a renamed directory) fails loudly instead of silently
// passing with zero files checked.
function walk(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return e.isFile() && p.endsWith('.ts') && !p.endsWith('.test.ts') ? [p] : [];
  });
}
const root = process.cwd();
const cloudSyncSources = walk(join(root, 'lib/cloud-sync')).filter((f) => existsSync(f));

// Matches BOTH named imports (`import { x } from '<mod>'`) and bare side-effect imports
// (`import '<mod>'`) — the `import`/`from` keyword must directly precede the quoted specifier so a
// mid-string or commented-out module path doesn't false-trip it. An optional `(?:/[^'"]*)?` before
// the closing quote also catches subpath imports (e.g. `@/lib/supabase/service/foo`) so a forbidden
// module can't be smuggled in through a deeper path.
const importOf = (mod: string) =>
  new RegExp(`(?:from|import)\\s*\\(?['"]${mod.replace(/[/-]/g, '\\$&')}(?:/[^'"]*)?['"]`);

describe('Task 10 (§6) — cloud-sync auth never reaches the service-role key', () => {
  // The "no service-role key on the local machine" guarantee only holds if the sync code (a) never
  // imports the service client module (`@/lib/supabase/service`), (b) never calls the service-role
  // accessor (`getServiceRoleKey`) or the client constructor (`createServiceClient`), and (c) never
  // references the raw env var name — any of these would defeat getAuthedClient's anon-key-only
  // construction.
  const forbidden = [
    /SUPABASE_SERVICE_ROLE_KEY/,        // literal env var name — any reference
    /getServiceRoleKey\s*\(/,           // the service-role key accessor
    /createServiceClient\s*\(/,         // the service_role client constructor
    importOf('@/lib/supabase/service'), // module that builds the service_role client
  ];

  it('scans a non-empty set of cloud-sync sources', () => {
    expect(cloudSyncSources.length).toBeGreaterThan(0);
    expect(cloudSyncSources.some((f) => f.endsWith('lib/cloud-sync/auth.ts'))).toBe(true);
  });

  it.each(cloudSyncSources)('%s imports/calls nothing that reaches the service-role key', (file) => {
    const src = readFileSync(file, 'utf-8');
    for (const re of forbidden) expect(src).not.toMatch(re);
  });

  // PLANTED NEGATIVE CONTROLS: prove the forbid-patterns actually catch a service-role reference in
  // each of its forms — not just that they happen to miss the real (clean) files above. A guard
  // that vacuously passes because its pattern is too narrow is worse than no guard.
  describe('planted violations are caught by the matcher (proves the guard is non-vacuous)', () => {
    const cases: Array<{ label: string; src: string; re: RegExp }> = [
      {
        label: 'raw env var reference',
        src: `const key = process.env.SUPABASE_SERVICE_ROLE_KEY;`,
        re: /SUPABASE_SERVICE_ROLE_KEY/,
      },
      {
        label: 'getServiceRoleKey() call',
        src: `import { getServiceRoleKey } from '@/lib/supabase/env';\nconst k = getServiceRoleKey();`,
        re: /getServiceRoleKey\s*\(/,
      },
      {
        label: 'createServiceClient() call',
        src: `import { createServiceClient } from '@/lib/supabase/service';\nconst c = createServiceClient();`,
        re: /createServiceClient\s*\(/,
      },
      {
        label: '@/lib/supabase/service named import',
        src: `import { createServiceClient } from '@/lib/supabase/service';`,
        re: importOf('@/lib/supabase/service'),
      },
      {
        label: '@/lib/supabase/service bare side-effect import',
        src: `import '@/lib/supabase/service';`,
        re: importOf('@/lib/supabase/service'),
      },
      {
        label: '@/lib/supabase/service subpath import',
        src: `import { foo } from '@/lib/supabase/service/foo';`,
        re: importOf('@/lib/supabase/service'),
      },
    ];
    it.each(cases)('$label is flagged', ({ src, re }) => {
      expect(src).toMatch(re);
    });
  });
});
// tests/lib/cloud-sync/model-writer-hash.test.ts
//
// Drives the REAL generation path (runHtmlDoc, mirroring tests/lib/html-doc/generate.test.ts)
// and asserts the persisted model envelope's sourceMdHash is the hash of the MD BODY that was
// fed to generation — NOT a hash of the sourceMd/summaryMd blob KEY (the filename). Guards
// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
// matches, so every synced companion would be wrongly deleted (needless re-charge on serve).
import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { runHtmlDoc } from '../../../lib/html-doc/generate';
import * as gemini from '../../../lib/gemini';
import { readModelEnvelope } from '../../../lib/html-doc/model-store';
import { localPrincipal } from '@/lib/storage/principal';
import { mdHash } from '../../../lib/cloud-sync/content-hash';

jest.mock('../../../lib/gemini');
const mockTransform = gemini.generateMagazineModel as jest.Mock;

let dir: string;
const VIDEO_ID = 'vid12345';

// The MD body fed to generation (the whole file `runHtmlDoc` reads as `video.summaryMd`'s blob).
const BODY = `---
video_id: "vid12345"
lang: EN
score: 4
---

# A Title

**Channel:** Chan | **Duration:** 1:00 | **URL:** https://youtu.be/x

---

## 1. First
First section prose.
---
## Conclusion
Wrap up.
`;

function writeIndex(videos: unknown[]) {
  fs.writeFileSync(
    path.join(dir, 'playlist-index.json'),
    JSON.stringify({ playlistUrl: 'https://x.test/p', outputFolder: dir, videos }, null, 2),
  );
}

function baseVideo() {
  return {
    id: VIDEO_ID, title: 'A Title', youtubeUrl: 'https://youtu.be/x', language: 'en',
    durationSeconds: 60, archived: false,
    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
    overallScore: 4, summaryMd: 'a-title.md',
    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  dir = path.join(os.homedir(), `.tmp-modelhash-test-${crypto.randomUUID()}`);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'a-title.md'), BODY);
  writeIndex([baseVideo()]);
});
afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

it('a freshly written model envelope carries sourceMdHash = mdHash(MD BODY)', async () => {
  mockTransform.mockResolvedValueOnce({
    sections: [
      { lead: 'Lead one.', bullets: [{ label: 'L', text: 't' }, { label: 'M', text: 'u' }, { label: 'N', text: 'v' }] },
    ],
  });
  await runHtmlDoc(VIDEO_ID, dir, () => {});

  const principal = localPrincipal(dir);
  const env = await readModelEnvelope(principal, 'a-title');
  expect(env).not.toBeNull();
  expect(env!.sourceMdHash).toBe(mdHash(BODY));            // hashes the BODY
  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
});
// NOTE on mocking technique: the plan's Step 1 draft used `jest.spyOn(modelStore, 'readModelEnvelope')`
// (a namespace-import spy). That throws `TypeError: Cannot redefine property` under this repo's
// SWC-compiled Jest transform (repro'd against the pre-existing, unmodified model-store.ts — not
// something this task introduced; no test in the repo uses that pattern). The repo's established
// convention for mocking a sibling lib module (see tests/lib/html-doc/serve-doc-mapping.test.ts) is a
// full `jest.mock(..., () => ({...}))` factory, used below. Assertions/interfaces are unchanged.
import { readFreshMagazineModel, isFresh, sameTitles, readTitleStableModel } from '@/lib/html-doc/read-model';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';

jest.mock('@/lib/html-doc/model-store', () => ({ readModelEnvelope: jest.fn() }));
import { readModelEnvelope } from '@/lib/html-doc/model-store';
const mockReadModelEnvelope = readModelEnvelope as jest.Mock;

const principal = { id: 'owner-1', indexKey: 'pl-key' };
const fakeModel = { title: 'T', dek: 'd', sections: [] } as any;
const titles = ['A', 'B'];
const roStore: ReadOnlyBlobStore = { get: async () => null };

function envelope(over: Partial<any> = {}) {
  return { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A', 'B'],
    generatorVersion: GENERATOR_VERSION, model: fakeModel, ...over };
}

describe('isFresh', () => {
  it('true when titles match and version matches', () => {
    expect(isFresh(envelope(), titles)).toBe(true);
  });
  it('false when a title differs', () => {
    expect(isFresh(envelope({ sourceSections: ['A', 'C'] }), titles)).toBe(false);
  });
  it('false when generatorVersion differs', () => {
    expect(isFresh(envelope({ generatorVersion: 'old' }), titles)).toBe(false);
  });
});

describe('readFreshMagazineModel', () => {
  afterEach(() => mockReadModelEnvelope.mockReset());

  it('returns ok with the model when a fresh envelope exists', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope());
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'ok', model: fakeModel });
    // Arg-passthrough: prove the helper forwards (principal, base, blobStore) unchanged
    // rather than swallowing or reordering them (the mock otherwise hides this).
    expect(mockReadModelEnvelope).toHaveBeenCalledWith(principal, 'b', roStore);
  });

  it('returns not_ready when the envelope is absent', async () => {
    mockReadModelEnvelope.mockResolvedValue(null);
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });

  it('returns not_ready when the envelope is stale (version bump)', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope({ generatorVersion: 'old' }));
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });
});

describe('sameTitles', () => {
  it('true iff same length and same order', () => {
    expect(sameTitles(envelope(), titles)).toBe(true);                       // ['A','B'] === ['A','B']
    expect(sameTitles(envelope({ sourceSections: ['B', 'A'] }), titles)).toBe(false);
    expect(sameTitles(envelope({ sourceSections: ['A'] }), titles)).toBe(false);
  });
});

describe('readTitleStableModel', () => {
  afterEach(() => mockReadModelEnvelope.mockReset());

  it('ok with the model when the envelope exists and titles match — version ignored (stale ok)', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope({ generatorVersion: 'OLD' })); // stale VERSION, same titles
    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'ok', model: fakeModel });
    expect(mockReadModelEnvelope).toHaveBeenCalledWith(principal, 'b', roStore);
  });
  it('none when titles drifted (positional mis-pair would occur → refuse)', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope({ sourceSections: ['X', 'B'], generatorVersion: 'OLD' }));
    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'none' });
  });
  it('none when no envelope', async () => {
    mockReadModelEnvelope.mockResolvedValue(null);
    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'none' });
  });
});

import { readFileSync, existsSync, statSync } from 'fs';
import { join, dirname, basename } from 'path';

describe('B18c — read-model.ts is a generate-free leaf', () => {
  // Matches `import ... from '<spec>'`, `export ... from '<spec>'` (incl. `import type` /
  // `export type`), and side-effect `import '<spec>'`. Character classes match across
  // newlines, so multi-line named-import blocks are covered too.
  const IMPORT_SPEC_RE =
    /(?:import|export)\s+(?:type\s+)?[^'";]*?from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"]/g;

  // Forbidden if the resolved path OR the raw specifier contains any of these as a substring —
  // deliberately broad so a subpath import (e.g. `@/lib/gemini/foo`) is still caught.
  const FORBIDDEN = ['@/lib/gemini', '@/lib/gemini-cost', 'serve-doc', 'reserve_serve_model'];
  const isForbidden = (spec: string) => FORBIDDEN.some((bad) => spec.includes(bad));

  /** Resolve an import specifier to a file path, or null for a bare npm package
   *  (which cannot be one of this app's own gemini/serve-doc modules by definition). */
  function resolveSpecifier(spec: string, fromFile: string): string | null {
    if (spec.startsWith('.')) return join(dirname(fromFile), spec);
    if (spec.startsWith('@/')) return join(process.cwd(), spec.slice(2));
    return null;
  }

  function resolveToFile(base: string): string | null {
    for (const candidate of [base, `${base}.ts`, `${base}.tsx`, join(base, 'index.ts')]) {
      if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
    }
    return null;
  }

  it('the entire transitive import graph never reaches gemini/gemini-cost/serve-doc', () => {
    const root = join(process.cwd(), 'lib/html-doc/read-model.ts');
    const visitedFiles = new Set<string>(); // cycle guard + traversal evidence
    const allSpecifiers: string[] = [];

    function walk(file: string) {
      if (visitedFiles.has(file)) return; // guard against import cycles
      visitedFiles.add(file);
      const src = readFileSync(file, 'utf-8');
      for (const m of src.matchAll(IMPORT_SPEC_RE)) {
        const spec = m[1] ?? m[2];
        if (!spec) continue;
        allSpecifiers.push(spec);
        const resolvedBase = resolveSpecifier(spec, file);
        if (!resolvedBase) continue; // bare npm package — nothing further to walk
        const resolved = resolveToFile(resolvedBase);
        if (resolved) walk(resolved);
      }
    }

    walk(root);

    // No specifier anywhere in the reachable graph names a forbidden module...
    for (const spec of allSpecifiers) expect(isForbidden(spec)).toBe(false);
    // ...and no resolved file path in the reachable graph is one either (catches the case
    // where a forbidden module is reached via a relative path that doesn't textually
    // contain the `@/lib/gemini` alias, e.g. a deep `../../gemini` relative import).
    for (const file of visitedFiles) expect(isForbidden(file)).toBe(false);

    // Sanity check: the traversal must be non-trivial. A walker broken by a regex or
    // resolution bug could silently visit only `read-model.ts` itself and pass vacuously —
    // assert it actually descended into both of read-model.ts's real dependencies.
    const visitedBasenames = [...visitedFiles].map((f) => basename(f));
    expect(visitedBasenames).toEqual(expect.arrayContaining(['model-store.ts', 'constants.ts']));
    expect(visitedFiles.size).toBeGreaterThanOrEqual(3);
  });
});

 succeeded in 2829ms:
service_role confinement OK

 succeeded in 4204ms:

> youtube-playlist-summaries@0.1.0 test
> jest --runInBand tests/lib/cloud-sync/import-guard.test.ts tests/lib/cloud-sync/content-hash.test.ts tests/lib/cloud-sync/schema.test.ts tests/lib/cloud-sync/reconcile-class-a.test.ts tests/lib/cloud-sync/reconcile-class-b.test.ts


Test Suites: 5 passed, 5 total
Tests:       49 passed, 49 total
Snapshots:   0 total
Time:        1.011 s, estimated 3 s
Ran all test suites matching tests/lib/cloud-sync/import-guard.test.ts|tests/lib/cloud-sync/content-hash.test.ts|tests/lib/cloud-sync/schema.test.ts|tests/lib/cloud-sync/reconcile-class-a.test.ts|tests/lib/cloud-sync/reconcile-class-b.test.ts.

exec
/bin/bash -lc "rg -n \"mdHash\\(["'^'"\\n]*(summaryMd|sourceMd|key|filename|file)\" lib tests scripts app types" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/lib/cloud-sync/model-writer-hash.test.ts:6:// former-High ⑤: decideCompanion (Task 8) compares against mdHash(body); a filename-hash never
tests/lib/cloud-sync/model-writer-hash.test.ts:82:  expect(env!.sourceMdHash).not.toBe(mdHash(env!.sourceMd)); // NOT the filename/key (guards N1)
tests/lib/cloud-sync/backfill.test.ts:17:  expect(s.mdHash).not.toBe(mdHash('001_title.md')); // must NOT hash the filename

exec
/bin/bash -lc "sed -n '1,300p' lib/storage/supabase/supabase-blob-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
    if (error) return null;   // 404 → null
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
    return paths;
  }
}

exec
/bin/bash -lc "sed -n '1,300p' lib/storage/local/local-blob-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import fs from 'fs'; import path from 'path'; import crypto from 'crypto';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

/** Byte-for-byte the current -data layout: physical path = join(indexKey, key). */
export class LocalFsBlobStore implements BlobStore {
  private abs(p: Principal, key: string): string { assertLogicalKey(key); return path.join(p.indexKey, key); }

  // contentType unused locally but required by the BlobStore interface (cloud impls will use it)
  async put(p: Principal, key: string, bytes: Buffer, _contentType: string): Promise<void> {
    const dest = this.abs(p, key); fs.mkdirSync(path.dirname(dest), { recursive: true });
    const tmp = dest + '.' + crypto.randomUUID() + '.tmp';
    try { fs.writeFileSync(tmp, bytes); fs.renameSync(tmp, dest); }
    catch (e) { try { fs.unlinkSync(tmp); } catch {} throw e; }
  }

  async get(p: Principal, key: string): Promise<Buffer | null> {
    try { return fs.readFileSync(this.abs(p, key)); }
    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
  }

  async exists(p: Principal, key: string): Promise<boolean> {
    try { fs.statSync(this.abs(p, key)); return true; }
    catch (e: any) { if (e.code === 'ENOENT') return false; throw e; }
  }

  async delete(p: Principal, key: string): Promise<void> {
    try { fs.unlinkSync(this.abs(p, key)); } catch (e: any) { if (e.code !== 'ENOENT') throw e; }
  }

  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    assertLogicalKey(key);  // validate before building tempKey — a leading '/' on key wouldn't appear on tempKey
    const tempKey = `_staging/${crypto.randomUUID()}/${key}`;
    await this.put(p, tempKey, bytes, contentType);
    return { principal: p, tempKey, finalKey: key };
  }

  async promote(ref: StagedRef): Promise<void> {
    const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
    fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
  }

  // '' → path.join(indexKey, '') === indexKey, i.e. the playlist's own index dir (intended
  // target, not above it). force:true makes an absent path a no-op (ENOENT-safe).
  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    assertLogicalKey(prefix);
    await fs.promises.rm(path.join(p.indexKey, prefix), { recursive: true, force: true });
  }

  async list(p: Principal, prefix: string): Promise<string[]> {
    assertLogicalKey(prefix);
    const root = path.join(p.indexKey, prefix);
    let entries: string[];
    try {
      entries = await fs.promises.readdir(root, { recursive: true }) as string[];
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === 'ENOENT') return [];
      throw e;
    }
    const out: string[] = [];
    for (const rel of entries) {
      const full = path.join(root, rel);
      if ((await fs.promises.stat(full)).isFile()) {
        out.push(path.posix.join(prefix.replace(/\/$/, ''), rel.split(path.sep).join('/')));
      }
    }
    return out;
  }
}

export const localBlobStore = new LocalFsBlobStore();

exec
/bin/bash -lc "sed -n '1,220p' lib/storage/blob-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { Principal } from '@/lib/storage/principal';

export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';

export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }

export interface BlobStore {
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;
  /** Recursively delete every object under a logical prefix. Best-effort/idempotent —
   *  an absent prefix is not an error. `prefix === ''` targets the whole playlist root
   *  (`<owner>/<indexKey>/`), not above it. */
  deletePrefix(p: Principal, prefix: string): Promise<void>;
  /** List logical keys (relative to the owner root) under a prefix. Absent prefix → []. */
  list(p: Principal, prefix: string): Promise<string[]>;
}

/** A read-only view of a BlobStore — exactly the `get` method. The share serve path
 *  passes a runtime `{ get: store.get.bind(store) }` wrapper so write methods are
 *  unreachable at runtime, not merely hidden by the type (spec D16). */
export type ReadOnlyBlobStore = Pick<BlobStore, 'get'>;

export function assertLogicalKey(key: string): void {
  if (key.startsWith('/') || key.split('/').includes('..') || key.includes('\0')) {
    throw Object.assign(new Error(`invalid blob key: ${key}`), { statusCode: 400 });
  }
}

codex
The confinement checks pass, and the hash-writing tests cover the key-vs-body invariant for writers. The remaining risk is not the hash computation itself, but places that advertise or reuse cached artifacts without proving the corresponding body/model is still valid.
exec
/bin/bash -lc "sed -n '1,360p' tests/lib/cloud-sync/sync-run.test.ts 2>/dev/null || true; sed -n '1,360p' tests/integration/cloud-sync/sync-run.int.test.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
// tests/integration/cloud-sync/sync-run.int.test.ts
//
// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
// FS ↔ local Supabase under an authenticated USER session (never service-role). Focuses on
// end-to-end wiring + atomicity + money-safety (the reconcile branches are unit-tested upstream).
//
// F1: cloud Principal uses deps.ownerId (= auth.uid()) so Supabase Storage RLS accepts the path and
//     a hydrate copies the real MD bytes. F2: transfers finalize via updateVideoFields. F3:
//     applyClassBWinners throws on a no-row write. Crash-safety uses a local→cloud publish so the
//     Supabase staged→promote (the faultable durability gate) is on the critical path.
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
import { runSync } from '@/lib/cloud-sync/sync-run';

afterAll(async () => {
  const home = os.homedir();
  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
});

describe('runSync (§7)', () => {
  it('hydrates an empty local replica from a cloud-only video (additive create, no charge)', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx); // cloud has 1 promoted-summary video, local empty
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps());

    expect(report.created).toBeGreaterThanOrEqual(1);
    // money-safety: a sync copy NEVER charges
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);

    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
    expect(localIdx.videos.length).toBeGreaterThanOrEqual(1);

    // F1: the hydrate read the cloud MD off `<ownerId>/<playlistKey>/<key>` and copied NON-NULL
    // bytes to the local replica (a wrong cloud Principal would read null → empty receiver).
    const hydrated = localIdx.videos.find((v) => v.id === ctx.videoId)!;
    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
    expect(localBody).not.toBeNull();
    expect(localBody!.toString('utf8')).toContain(`# Summary ${ctx.videoId}`);
  });

  it('publishes a local-only human note to the cloud with the source timestamp', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx, { localNote: { value: 'mine', editedAt: '2026-04-04T00:00:00.000Z' } });

    await runSync(ctx.syncDeps());

    const row = await ctx.readVideoData(ctx.playlistId, ctx.videoId);
    expect(row.personalNote).toBe('mine');
    expect(row.annotationsEditedAt?.personalNote).toBe('2026-04-04T00:00:00.000Z');
  });

  it('does not advance the manifest baseline when the cloud promote is not verified (crash safety)', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx, { publishToCloud: true }); // local-only video → publishes to cloud
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));

    // The transfer threw at promote → per-video error captured, run did not abort.
    expect(report.errors.length).toBeGreaterThanOrEqual(1);
    // Behavior #10/#11: a partial transfer NEVER advances the manifest baseline.
    const m = await ctx.readManifest();
    expect(m.videos[ctx.videoId]).toBeUndefined();
    // still no charge
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
  });
});

exec
/bin/bash -lc 'rg -n "artifacts|summaryMd|modelJson|sourceMdHash|summaryReady" docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
89:  `summaryReady`. **`archived` is replica-local in M2a but stays fully writable** — it has *two* semantics
103:- `ModelEnvelope` gains an OPTIONAL **`sourceMdHash`** — an **MD-body-only** digest (§5.2), set going
105:- On a Class-A MD-transfer: ship the sender's model as a companion **iff** `sourceMdHash == mdHash(winning
119:  envelope's `sourceMdHash`), `mdGeneratedAt` (UTC, a **tie-break only**, never a quality signal), and
215:- **`ModelEnvelopeSchema`:** add `sourceMdHash?: string` **and drop `.strict()`** (→ ignore unknown keys) so a
254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
319:  reader (`.strict()` dropped) tolerates a `sourceMdHash`-bearing envelope.
372:4. **Model JSON = companion** (sync-transfer scoped, MD-only `sourceMdHash`, forward-tolerant schema, R5/R7).

exec
/bin/bash -lc 'rg -n "copyAdditiveVideo|missing.*blob|shareNeedsOwnerServe|deleteReceiverModel|companion|promoted.*blob|summaryMd.*null|baseline" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/cloud-sync/sync-run.int.test.ts:58:  it('does not advance the manifest baseline when the cloud promote is not verified (crash safety)', async () => {
tests/integration/cloud-sync/sync-run.int.test.ts:67:    // Behavior #10/#11: a partial transfer NEVER advances the manifest baseline.
tests/lib/cloud-sync/reconcile-class-a.test.ts:52:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:54:    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:62:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
tests/integration/cloud-sync/e2e.int.test.ts:6:// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
tests/integration/cloud-sync/e2e.int.test.ts:40:/** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
tests/integration/cloud-sync/e2e.int.test.ts:41:function baseline(classB: VideoBaseline['classB']): VideoBaseline {
tests/integration/cloud-sync/e2e.int.test.ts:83:    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
tests/integration/cloud-sync/e2e.int.test.ts:146:  // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
tests/integration/cloud-sync/e2e.int.test.ts:188:  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
tests/integration/cloud-sync/e2e.int.test.ts:189:  it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:201:    await seedManifestBaseline(ctx, baseline({
tests/integration/cloud-sync/e2e.int.test.ts:215:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:224:    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
tests/integration/cloud-sync/e2e.int.test.ts:225:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:240:  // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
tests/integration/cloud-sync/e2e.int.test.ts:241:  it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:243:    // Cloud still holds the video; local deleted it; a baseline records they once agreed.
tests/integration/cloud-sync/e2e.int.test.ts:245:    await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));
tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:341:    expect(m1.videos[ctx.videoId]).toBeDefined();       // baseline written only after the row landed
tests/integration/cloud-sync/e2e.int.test.ts:344:    expect(r2.removed).toBe(0);                          // baseline present + BOTH sides present → not a delete
tests/integration/cloud-sync/e2e.int.test.ts:350:  // ── Row 16 — promoted status never precedes a durable blob (blob promote fails mid-publish).
tests/integration/cloud-sync/e2e.int.test.ts:351:  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:359:    // No cloud row advertises promoted without a durable MD blob.
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion } from '@/lib/cloud-sync/companion';
tests/lib/cloud-sync/companion.test.ts:15:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
tests/lib/cloud-sync/companion.test.ts:19:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
tests/lib/cloud-sync/companion.test.ts:23:    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
tests/lib/cloud-sync/reconcile-class-b.test.ts:17:  it('only local changed vs baseline → take local', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:20:  it('only cloud changed vs baseline → take cloud', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:23:  it('a clear on one side (present→absent vs baseline) propagates', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:31:    // baseline present "x"@t1; local cleared@t2; cloud re-added same "x"@t3.
tests/lib/cloud-sync/reconcile-class-b.test.ts:32:    // cloud's (value,editedAt) differs from baseline (ts advanced) → cloud changed;
tests/lib/cloud-sync/reconcile-class-b.test.ts:36:  it('no baseline + differ → newer per-field editedAt wins', () => {
tests/lib/cloud-sync/reconcile-class-b.test.ts:39:  it('present one side, absent other, no baseline → copy (additive)', () => {
tests/lib/cloud-sync/model-writer-hash.test.ts:7:// matches, so every synced companion would be wrongly deleted (needless re-charge on serve).
tests/lib/cloud-sync/manifest.test.ts:21:it('round-trips a written baseline', async () => {
tests/lib/cloud-sync/schema.test.ts:8:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
tests/lib/cloud-sync/local-stamping.test.ts:23:  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);

exec
/bin/bash -lc "sed -n '1,390p' tests/integration/cloud-sync/e2e.int.test.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
  makeOwnerContext, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, type Ctx,
} from '@/tests/integration/helpers/cloud';
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

    // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
    expect(cloudBody).not.toBeNull();
    expect(cloudBody!.toString('utf8')).toBe(bodyHi);
    expect(bodyHash(cloudBody!.toString('utf8'))).toBe(bodyHash(bodyHi));

    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
    const cloud = await cloudVideoRecord(ctx);
    expect(cloud?.docVersion?.major).toBe(3);
    expect(cloud?.ratings).toEqual(winnerRatings);
    expect(cloud?.overallScore).toBe(3);
    expect(cloud?.tldr).toBe('the-tldr');
    expect(cloud?.takeaways).toEqual(['a', 'b']);
    expect(cloud?.tags).toEqual(['x', 'y']);
    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
  });

  // ── Row 2 — corrections-current lower-major MD survives over a corrections-STALE higher-major MD.
  //    Currency beats format → the corrections-current body lands on BOTH sides.
  //    Winner is the CLOUD side here → copyToLocal, exercising the local-overwrite transfer direction.
  it('row 2: corrections-current lower-major beats stale higher-major (currency beats format)', async () => {
    const ctx = await makeOwnerContext();
    const bodyCurrent = '# CurrentCorrections\n\nlower-major but corrections-current\n'; // cloud (winner)
    const bodyStale = '# StaleHiMajor\n\nhigher-major but corrections-stale\n';          // local (loser)
    const winnerRatings = { usefulness: 5, depth: 3, originality: 2, recency: 4, completeness: 1 };
    const editedAt = '2025-06-01T00:00:00.000Z';
    await seedCloudVideo(ctx, {
      mdBody: bodyCurrent, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2025-01-01T00:00:00.000Z',
      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
      mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
      ratings: winnerRatings, tldr: 'keep-me', takeaways: ['k1'], tags: ['t1'],
    });
    await seedLocalVideoFull(ctx, {
      mdBody: bodyStale, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
      mdCorrectionsHash: mdHash('fix-v1'),  // STALE: MD was generated against an older corrections
    });

    const report = await runSync(ctx.syncDeps());
    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);

    // The corrections-current (lower-major) body is now on both sides; docVersion downgraded to it.
    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
    const localBody = await localBlobBytes(ctx, key(ctx));
    expect(cloudBody!.toString('utf8')).toBe(bodyCurrent);   // winner side unchanged
    expect(localBody!.toString('utf8')).toBe(bodyCurrent);   // loser overwritten with the winner body
    const local = await localVideoRecord(ctx);
    expect(local?.docVersion?.major).toBe(1);
    expect(local?.ratings).toEqual(winnerRatings);
    expect(local?.tldr).toBe('keep-me');
  });

  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
    const ctx = await makeOwnerContext();
    const body = '# StaleBoth\n\nidentical stale content\n';
    const staleHash = mdHash('stale-corrections'); // != mdHash('') → both sides corrections-stale
    await seedLocalVideoFull(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
    await seedCloudVideo(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });

    const report = await runSync(ctx.syncDeps());

    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
    expect(report.skippedIdentical).toBeGreaterThanOrEqual(1);
    // MD unchanged on both sides.
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
  });

  // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
  it('row 4: carries the 5 real ratings + tldr/takeaways/tags verbatim (not reconstructed)', async () => {
    const ctx = await makeOwnerContext();
    const ratings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 }; // NON-flat
    await seedCloudVideo(ctx, {
      mdBody: '# S\n\nbody\n', ratings, overallScore: 3,
      tldr: 'the tldr', takeaways: ['t1', 't2'], tags: ['x', 'y'], docVersion: { major: 3, minor: 3 },
    });

    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
    const local = await localVideoRecord(ctx);
    expect(local?.ratings).toEqual(ratings);
    expect(local?.overallScore).toBe(3);
    expect(local?.tldr).toBe('the tldr');
    expect(local?.takeaways).toEqual(['t1', 't2']);
    expect(local?.tags).toEqual(['x', 'y']);
  });

  // ── Row 5 — Class-B: a note edit on local + a score edit on cloud → BOTH survive on both sides.
  it('row 5: independent Class-B edits (note local, score cloud) both survive', async () => {
    const ctx = await makeOwnerContext();
    const body = '# Same\n\nidentical current MD\n';
    await seedLocalVideoFull(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      personalNote: 'mynote', annotationsEditedAt: { personalNote: '2026-03-01T00:00:00.000Z' },
    });
    await seedCloudVideo(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      personalScore: 4, annotationsEditedAt: { personalScore: '2026-03-02T00:00:00.000Z' },
    });

    const report = await runSync(ctx.syncDeps());
    expect(report.mergedFields).toBeGreaterThanOrEqual(2);

    const local = await localVideoRecord(ctx);
    const cloud = await cloudVideoRecord(ctx);
    expect(local?.personalNote).toBe('mynote');
    expect(local?.personalScore).toBe(4);
    expect(cloud?.personalNote).toBe('mynote');
    expect(cloud?.personalScore).toBe(4);
  });

  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
  it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
    const ctx = await makeOwnerContext();
    const body = '# Same6\n\nidentical current MD\n';
    // Local cleared personalNote (value gone, but a NEWER edit timestamp); cloud still holds the old value.
    await seedLocalVideoFull(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      annotationsEditedAt: { personalNote: '2026-05-02T00:00:00.000Z' }, // cleared: no personalNote value
    });
    await seedCloudVideo(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      personalNote: 'old', annotationsEditedAt: { personalNote: '2026-05-01T00:00:00.000Z' },
    });
    await seedManifestBaseline(ctx, baseline({
      ...EMPTY_CLASSB,
      personalNote: { value: 'old', editedAt: '2026-05-01T00:00:00.000Z' },
    }));

    await runSync(ctx.syncDeps());

    const local = await localVideoRecord(ctx);
    const cloud = await cloudVideoRecord(ctx);
    expect(local?.personalNote == null).toBe(true);
    expect(cloud?.personalNote == null).toBe(true); // the clear propagated; 'old' not resurrected
  });

  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, {
      mdBody: '# Winner7\n\nformat-2\n', docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    await seedCloudVideo(ctx, {
      mdBody: '# Loser7\n\nformat-1\n', docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });

    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
  });

  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, { mdBody: '# Free\n\nno charge\n' });
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps());

    expect(report.created).toBeGreaterThanOrEqual(1);
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
  });

  // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
  it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
    const ctx = await makeOwnerContext();
    // Cloud still holds the video; local deleted it; a baseline records they once agreed.
    await seedCloudVideo(ctx, { mdBody: '# Deleted\n\ngone locally\n' });
    await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));

    const report = await runSync(ctx.syncDeps());

    expect(report.removed).toBeGreaterThanOrEqual(1);
    expect(await localVideoRecord(ctx)).toBeNull();          // not re-hydrated
    expect(await cloudVideoRecord(ctx)).not.toBeNull();      // present side untouched (no propagation, M2b)
    expect(report.created).toBe(0);
  });

  // ── Row 10 — no-session refusal + a client-forged owner_id is RLS-rejected.
  it('row 10: getAuthedClient throws with no session; a forged owner_id is RLS-rejected', async () => {
    const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
    await expect(getAuthedClient(emptyStore)).rejects.toBeInstanceOf(NoSessionError);

    const ctx = await makeOwnerContext();
    const { error } = await ctx.userClient.from('playlists').insert({
      owner_id: randomUUID(), // NOT auth.uid() → RLS with-check rejects
      playlist_key: `k-${randomUUID()}`, playlist_url: 'https://x/forged',
    });
    expect(error).toBeTruthy();
  });

  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, {
      mdBody: '# Cached\n\nhas cache\n',
      summaryHtml: '<html>cached</html>',
      digDeeperHtml: '<html>dig</html>',
      extraArtifacts: { summaryPdf: { key: 'p.pdf', status: 'promoted' } },
    });

    await runSync(ctx.syncDeps());
    const local = await localVideoRecord(ctx);
    expect(local?.summaryHtml == null).toBe(true);
    expect(local?.digDeeperHtml == null).toBe(true);
    expect(artifactsOf(local)?.summaryPdf).toBeUndefined();
  });

  // ── Row 12 — a backfilled Class-B conflict is preserved across TWO runs (§5.5, round-3 H2).
  it('row 12: backfilled divergent note logs+skips on both runs; neither side overwritten', async () => {
    const ctx = await makeOwnerContext();
    const body = '# Same12\n\nidentical current MD\n';
    // Both sides carry a DIFFERENT personalNote with NO per-field timestamp → both backfilled.
    await seedLocalVideoFull(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-local' });
    await seedCloudVideo(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-cloud' });

    const r1 = await runSync(ctx.syncDeps());
    expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local');
    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
    const m1 = await ctx.readManifest();
    expect((m1.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();

    const r2 = await runSync(ctx.syncDeps());
    expect(r2.conflictsLogged).toBeGreaterThanOrEqual(1); // re-logs (not silently skipped)
    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local'); // still not overwritten
    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
    const m2 = await ctx.readManifest();
    expect((m2.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();
  });

  // ── Row 13 — additive create of a summary-less video: metadata copied, no blob put, no throw.
  it('row 13: additive create of a summary-less video copies metadata with no blob write', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });

    const report = await runSync(ctx.syncDeps());
    expect(report.errors).toEqual([]);
    expect(report.created).toBeGreaterThanOrEqual(1);
    const local = await localVideoRecord(ctx);
    expect(local).not.toBeNull();
    expect(local?.summaryMd == null).toBe(true);
  });

  // ── Row 14 — additive PUBLISH is servable: cloud row advertises promoted → summaryReady true.
  it('row 14: additive publish sets promoted status → summaryReady true on the cloud', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, { mdBody: '# Published\n\nservable\n' }); // local-only → publishes to cloud

    await runSync(ctx.syncDeps());
    const cloud = await cloudVideoRecord(ctx);
    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
    expect(cloud?.summaryReady).toBe(true);
  });

  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
  it('row 15: additive publish creates the cloud playlist+video; a re-run is not read as a delete', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, { mdBody: '# Create15\n\ncreated on cloud\n' });

    const r1 = await runSync(ctx.syncDeps());
    expect(r1.created).toBeGreaterThanOrEqual(1);
    expect(await cloudVideoRecord(ctx)).not.toBeNull(); // receiver row created (not a silent no-op)
    const m1 = await ctx.readManifest();
    expect(m1.videos[ctx.videoId]).toBeDefined();       // baseline written only after the row landed

    const r2 = await runSync(ctx.syncDeps());
    expect(r2.removed).toBe(0);                          // baseline present + BOTH sides present → not a delete
    expect(r2.created).toBe(0);
    expect(await cloudVideoRecord(ctx)).not.toBeNull();
    expect(await localVideoRecord(ctx)).not.toBeNull();
  });

  // ── Row 16 — promoted status never precedes a durable blob (blob promote fails mid-publish).
  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, { mdBody: '# Crash16\n\npromote fails\n' });
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));

    expect(report.errors.length).toBeGreaterThanOrEqual(1);
    // No cloud row advertises promoted without a durable MD blob.
    const cloud = await cloudVideoRecord(ctx);
    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
    expect(cloud?.summaryReady).toBeFalsy();
    // Baseline not advanced; no charge.
    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
  });

  // ── Row 17 — fresh-device hydrate creates the local root (mkdir -p); re-run is not a delete.
  it('row 17: a fresh-device hydrate creates the local root, writes index+video+MD; re-run is not a delete', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, { mdBody: '# Fresh\n\nhydrated to a new device\n' });

    // The per-playlist local root must NOT exist yet, or the ensureHydrationRoot mkdir path goes untested.
    await expect(fs.access(ctx.playlistDataRoot)).rejects.toBeDefined();

    const r1 = await runSync(ctx.syncDeps());
    expect(r1.created).toBeGreaterThanOrEqual(1);
    await expect(fs.access(path.join(ctx.playlistDataRoot, 'playlist-index.json'))).resolves.toBeUndefined();
    const local = await localVideoRecord(ctx);
    expect(local).not.toBeNull();
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toContain('# Fresh');

    const r2 = await runSync(ctx.syncDeps());
    expect(r2.removed).toBe(0); // the just-created local root is not mis-read as a delete
    expect(await localVideoRecord(ctx)).not.toBeNull();
  });
});

exec
/bin/bash -lc "sed -n '1,300p' lib/cloud-sync/auth.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import { promises as fs } from 'fs';
import path from 'path';
import { createClient, type SupabaseClient, type Session } from '@supabase/supabase-js';

export class NoSessionError extends Error {
  constructor() { super('Not signed in to cloud. Run: cloud-sync login'); this.name = 'NoSessionError'; }
}

export interface TokenStore {
  read(): Promise<string | null>;
  write(token: string): Promise<void>;
  clear(): Promise<void>;
}

function anonClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) throw new Error('NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY not set');
  return createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } });
}

/** Fail-closed check on the token's parent directory: reject group/other-writable, require
 *  ownership by the current uid where the platform exposes it (§6). */
async function assertSafeParent(file: string): Promise<void> {
  const dir = path.dirname(file);
  const st = await fs.stat(dir); // throws ENOENT if the dir does not exist
  if (st.mode & 0o022) {
    throw new Error(`refusing: token dir ${dir} is group/other-writable (mode ${(st.mode & 0o777).toString(8)}); tighten to 0700`);
  }
  if (typeof process.getuid === 'function' && st.uid !== process.getuid()) {
    throw new Error(`refusing: token dir ${dir} not owned by the current user`);
  }
}

export function makeFileTokenStore(file: string): TokenStore {
  return {
    async read() {
      try {
        await assertSafeParent(file);
      } catch (e: any) {
        if (e?.code === 'ENOENT') return null; // no dir yet → no token
        throw e;                               // broad/foreign parent → fail closed
      }
      try {
        const st = await fs.stat(file);
        if (st.mode & 0o077) throw new Error(`refusing to read ${file}: permission too broad (mode ${(st.mode & 0o777).toString(8)})`);
        return (await fs.readFile(file, 'utf8')).trim() || null;
      } catch (e: any) {
        if (e?.code === 'ENOENT') return null;
        throw e;
      }
    },
    async write(token: string) {
      const dir = path.dirname(file);
      // Check an EXISTING parent BEFORE touching it — a chmod-then-check would launder a
      // pre-existing group/world-writable or foreign-owned dir (round-2 H2). Only self-heal
      // a dir we create ourselves.
      let exists = true;
      try { await assertSafeParent(file); }
      catch (e: any) { if (e?.code === 'ENOENT') exists = false; else throw e; } // unsafe existing → throw
      if (!exists) {
        await fs.mkdir(dir, { recursive: true, mode: 0o700 });
        await fs.chmod(dir, 0o700);
        await assertSafeParent(file); // verify the just-created dir is safe
      }
      await fs.writeFile(file, token, { mode: 0o600 });
      await fs.chmod(file, 0o600);
    },
    async clear() { await fs.rm(file, { force: true }); },
  };
}

function defaultTokenPath(): string {
  const home = process.env.HOME || process.env.USERPROFILE || '.';
  return path.join(home, '.config', 'youtube-playlist-summaries', 'cloud-sync-token');
}
export const fileTokenStore = makeFileTokenStore(defaultTokenPath());

export async function signIn(email: string, password: string, store: TokenStore = fileTokenStore): Promise<void> {
  const c = anonClient();
  const { data, error } = await c.auth.signInWithPassword({ email, password });
  if (error || !data.session) throw new Error(`sign-in failed: ${error?.message ?? 'no session'}`);
  await store.write(data.session.refresh_token);
}

export async function signOut(store: TokenStore = fileTokenStore): Promise<void> {
  await store.clear();
}

export async function loadSession(store: TokenStore = fileTokenStore): Promise<Session | null> {
  const refresh = await store.read();
  if (!refresh) return null;
  const c = anonClient();
  const { data, error } = await c.auth.refreshSession({ refresh_token: refresh });
  if (error || !data.session) return null;
  await store.write(data.session.refresh_token); // rotate
  return data.session;
}

export async function getAuthedClient(store: TokenStore = fileTokenStore): Promise<SupabaseClient> {
  const session = await loadSession(store);
  if (!session) throw new NoSessionError();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  return createClient(url, anon, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${session.access_token}` } },
  });
}

exec
/bin/bash -lc 'rg -n "job-queue/producer|enqueuePlaylist|enqueue|spend_ledger|reserve_serve_model|settle_serve_model|reserve_video_slot|persist_summary" lib/cloud-sync scripts/cloud-sync.ts lib/storage/local/local-metadata-store.ts lib/index-store.ts lib/storage/supabase/supabase-metadata-store.ts lib/html-doc/model-store.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:14://    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
lib/cloud-sync/sync-run.ts:143: *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,

exec
/bin/bash -lc "sed -n '1,300p' lib/storage/resolve.ts && sed -n '1,220p' lib/supabase/client.ts && sed -n '1,180p' lib/supabase/env.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { JobQueue } from '@/lib/storage/job-queue';
import { localPrincipal, type Principal } from '@/lib/storage/principal';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { validateStorageEnv, ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { assertOutputFolder } from '@/lib/index-store';

export interface StorageBundle {
  metadataStore: MetadataStore;
  blobStore: BlobStore;
  jobQueue?: JobQueue; // cloud-only; undefined for the local bundle
}

const LOCAL_BUNDLE: StorageBundle = { metadataStore: localMetadataStore as MetadataStore, blobStore: localBlobStore as BlobStore };

/** Resolve a request's outputFolder into a Principal, running the local
 *  home-dir containment guard (behavior identical to today's assertOutputFolder).
 *  CRITICAL (Codex Blocking): preserve the RAW outputFolder string — do NOT
 *  path.resolve it. index-store uses the raw string for the index file path;
 *  assertOutputFolder resolves only internally for its guard check. Resolving
 *  here would change the persisted index.outputFolder value and the arguments
 *  observed by existing mocked-function assertions. */
export function getPrincipal(outputFolder: string): Principal {
  assertOutputFolder(outputFolder); // guards; resolves internally, returns void
  const indexKey = outputFolder;    // raw string preserved; renamed for Principal field clarity
  return localPrincipal(indexKey);
}

/**
 * @deprecated Use getStorageBundle() instead, which co-selects a matched
 *   {metadataStore, blobStore} pair from STORAGE_BACKEND. Calling this shim
 *   and resolving blobStore independently risks mixing local and cloud stores.
 */
export function getMetadataStore(): MetadataStore {
  return localMetadataStore;
}

/** Return a co-selected StorageBundle {metadataStore, blobStore, jobQueue?} from
 *  STORAGE_BACKEND. Never mixes local and cloud stores.
 *  - 'local' (default): returns the local singletons; jobQueue is undefined
 *    (the local backend has no job queue in Stage 1E-a).
 *  - 'supabase': validates env (fail-fast), requires ctx.supabaseClient (routes
 *    are not wired in Stage 1C — passing no client throws), then returns
 *    Supabase impls including a SupabaseJobQueue. */
export function getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): StorageBundle {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'local') return LOCAL_BUNDLE; // jobQueue stays undefined
  if (backend === 'supabase') {
    validateStorageEnv(); // fail-fast on missing env
    if (!ctx?.supabaseClient) throw new Error('supabase backend requires an authenticated client (routes not wired in 1C)');
    return {
      metadataStore: new SupabaseMetadataStore(ctx.supabaseClient),
      blobStore: new SupabaseBlobStore(ctx.supabaseClient, ARTIFACTS_BUCKET),
      jobQueue: new SupabaseJobQueue(ctx.supabaseClient),
    };
  }
  throw new Error(`unknown STORAGE_BACKEND: ${backend}`);
}

/** Resolve a worker-facing storage bundle for a (ownerId, playlistId) pair.
 *  UUID-BOUND ON PURPOSE: playlist_key is unique PER OWNER, not globally, so a
 *  service_role worker must resolve the playlist by its UUID and assert
 *  ownership explicitly here — never look the row up by playlist_key (that
 *  path could silently return another owner's row when keys collide). */
export async function getWorkerStorageBundle(
  serviceClient: SupabaseClient, ownerId: string, playlistId: string,
): Promise<{ blobStore: BlobStore; principal: Principal; ownerId: string; playlistId: string }> {
  validateStorageEnv();
  const { data, error } = await serviceClient
    .from('playlists').select('playlist_key, owner_id').eq('id', playlistId).maybeSingle();
  if (error) throw error;
  if (!data || data.owner_id !== ownerId) {
    throw new Error(`getWorkerStorageBundle: playlist ${playlistId} not owned by ${ownerId}`);
  }
  return {
    blobStore: new SupabaseBlobStore(serviceClient, ARTIFACTS_BUCKET),
    principal: { id: ownerId, indexKey: data.playlist_key },
    ownerId,
    playlistId,
  };
}

/** Derive a Principal from a session. Hard-fails if the Supabase backend is
 *  active but the session has no userId — the caller must not proceed without
 *  an authenticated user in cloud mode.
 *  Routes use getPrincipal(outputFolder) in Stage 1C (local-principal path only). */
export function getPrincipalFromSession(session: { userId: string | null }, indexKey: string): Principal {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') {
    if (!session.userId) throw new Error('supabase backend: no authenticated session for principal');
    return { id: session.userId, indexKey };
  }
  return localPrincipal(indexKey);
}
'use client';
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  // These MUST be referenced statically (not via a `process.env[name]` helper):
  // Next.js only inlines NEXT_PUBLIC_* into the client bundle for literal
  // `process.env.NEXT_PUBLIC_*` references. A computed key resolves to undefined
  // in the browser. Server-side clients use getSupabaseEnv()/process.env[name],
  // which is correct there because process.env is populated at runtime.
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url) throw new Error('Missing required env var: NEXT_PUBLIC_SUPABASE_URL');
  if (!anonKey) throw new Error('Missing required env var: NEXT_PUBLIC_SUPABASE_ANON_KEY');
  return createBrowserClient(url, anonKey);
}
function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

export function getSupabaseEnv(): { url: string; anonKey: string } {
  return {
    url: required('NEXT_PUBLIC_SUPABASE_URL'),
    anonKey: required('NEXT_PUBLIC_SUPABASE_ANON_KEY'),
  };
}

/** Server-only. Never call from client code. */
export function getServiceRoleKey(): string {
  return required('SUPABASE_SERVICE_ROLE_KEY');
}

codex
**Findings**

1. **Blocking**: `lib/cloud-sync/sync-run.ts:407`
   
   Unresolved `corrections` conflicts still feed Class A as if there were an agreed correction value.

   Scenario: local has `corrections="A"` with MD stamped `mdCorrectionsHash=mdHash("A")`; cloud has `corrections="B"` with MD stamped `mdCorrectionsHash=mdHash("B")`; both timestamps are backfilled, so Class B logs/skips the conflict. `reconciledCorrectionsHash` is then computed from `merges.corrections.value`, which is the local value from the no-write conflict. Class A now sees local as current and cloud as stale, copies local MD to cloud, while cloud still keeps `corrections="B"`. Result: cloud advertises an MD generated for correction A next to human correction B, and the manifest advances Class A around an unresolved Class-B conflict.

   Fix: when `merges.corrections.winner === 'equal' && merges.corrections.conflict`, do not run normal Class-A currency reconciliation against an invented hash. Preserve prior Class-A baseline or mark needs-regen/conflict until corrections actually converge.

2. **High**: `lib/cloud-sync/sync-run.ts:112`, `lib/cloud-sync/sync-run.ts:164`, `lib/cloud-sync/sync-run.ts:169`
   
   Additive copy can advertise a promoted summary whose blob was never copied.

   Scenario: source video has `summaryMd` and `artifacts.summaryMd.status='promoted'`, but the source blob read returns `null` due to storage drift/corruption/RLS miss. `copyAdditiveVideo` skips the blob write because `mdBody == null`, but `sanitizeAdditiveVideo` preserves the sender’s `artifacts.summaryMd`. The receiver row is upserted with a promoted artifact pointing at a missing blob, then the caller writes a baseline.

   Fix: if `video.summaryMd` is present and `mdBody == null`, either throw and do not advance the baseline, or explicitly clear `summaryMd` and `artifacts.summaryMd` before writing. The post-write verify must check the advertised artifact tuple, not just row presence.

3. **Medium**: `lib/html-doc/read-model.ts:20`, `lib/html-doc/read-model.ts:37`, `lib/html-doc/read-model.ts:52`
   
   Serve-side model freshness ignores `sourceMdHash`, so sync’s companion invalidation can be bypassed.

   Scenario: Class-A transfer decides not to ship the sender model because `sourceMdHash !== winnerMdHash`, and attempts to delete the receiver model. If that best-effort delete fails, or a stale same-base model remains, owner serve/share serve calls `readFreshMagazineModel`, which only checks section titles and generator version. Same headings + same generator version returns stale model as fresh even though the envelope was generated from a different MD body.

   Fix: pass current `mdBody`/`mdHash` into freshness checks where available and require either no `sourceMdHash` legacy fallback policy or `sourceMdHash === mdHash(currentMdBody)`. At minimum, owner serve must not consider a hash-mismatched envelope fresh.

**Accepted Minors Triage**

`T12-M2` should be upgraded before merge because row-presence-only verification masks finding 2. It needs artifact/key/status/blob verification when an additive row advertises `promoted`.

`T14-M1`, `T14-M2`, `T5` coverage gaps, and the automock comment can remain deferred unless you choose to broaden the fix tests while touching the same paths.

I also checked the service-role confinement script and targeted cloud-sync tests; they pass. I found no key-hash use of `mdHash(video.summaryMd)` in shipped source.

**NOT CONVERGED**
tokens used
108,774
**Findings**

1. **Blocking**: `lib/cloud-sync/sync-run.ts:407`
   
   Unresolved `corrections` conflicts still feed Class A as if there were an agreed correction value.

   Scenario: local has `corrections="A"` with MD stamped `mdCorrectionsHash=mdHash("A")`; cloud has `corrections="B"` with MD stamped `mdCorrectionsHash=mdHash("B")`; both timestamps are backfilled, so Class B logs/skips the conflict. `reconciledCorrectionsHash` is then computed from `merges.corrections.value`, which is the local value from the no-write conflict. Class A now sees local as current and cloud as stale, copies local MD to cloud, while cloud still keeps `corrections="B"`. Result: cloud advertises an MD generated for correction A next to human correction B, and the manifest advances Class A around an unresolved Class-B conflict.

   Fix: when `merges.corrections.winner === 'equal' && merges.corrections.conflict`, do not run normal Class-A currency reconciliation against an invented hash. Preserve prior Class-A baseline or mark needs-regen/conflict until corrections actually converge.

2. **High**: `lib/cloud-sync/sync-run.ts:112`, `lib/cloud-sync/sync-run.ts:164`, `lib/cloud-sync/sync-run.ts:169`
   
   Additive copy can advertise a promoted summary whose blob was never copied.

   Scenario: source video has `summaryMd` and `artifacts.summaryMd.status='promoted'`, but the source blob read returns `null` due to storage drift/corruption/RLS miss. `copyAdditiveVideo` skips the blob write because `mdBody == null`, but `sanitizeAdditiveVideo` preserves the sender’s `artifacts.summaryMd`. The receiver row is upserted with a promoted artifact pointing at a missing blob, then the caller writes a baseline.

   Fix: if `video.summaryMd` is present and `mdBody == null`, either throw and do not advance the baseline, or explicitly clear `summaryMd` and `artifacts.summaryMd` before writing. The post-write verify must check the advertised artifact tuple, not just row presence.

3. **Medium**: `lib/html-doc/read-model.ts:20`, `lib/html-doc/read-model.ts:37`, `lib/html-doc/read-model.ts:52`
   
   Serve-side model freshness ignores `sourceMdHash`, so sync’s companion invalidation can be bypassed.

   Scenario: Class-A transfer decides not to ship the sender model because `sourceMdHash !== winnerMdHash`, and attempts to delete the receiver model. If that best-effort delete fails, or a stale same-base model remains, owner serve/share serve calls `readFreshMagazineModel`, which only checks section titles and generator version. Same headings + same generator version returns stale model as fresh even though the envelope was generated from a different MD body.

   Fix: pass current `mdBody`/`mdHash` into freshness checks where available and require either no `sourceMdHash` legacy fallback policy or `sourceMdHash === mdHash(currentMdBody)`. At minimum, owner serve must not consider a hash-mismatched envelope fresh.

**Accepted Minors Triage**

`T12-M2` should be upgraded before merge because row-presence-only verification masks finding 2. It needs artifact/key/status/blob verification when an additive row advertises `promoted`.

`T14-M1`, `T14-M2`, `T5` coverage gaps, and the automock comment can remain deferred unless you choose to broaden the fix tests while touching the same paths.

I also checked the service-role confinement script and targeted cloud-sync tests; they pass. I found no key-hash use of `mdHash(video.summaryMd)` in shipped source.

**NOT CONVERGED**
