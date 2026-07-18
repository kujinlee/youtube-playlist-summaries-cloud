# Stage 3 — Cloud Sync (M2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the single author a manual **Cloud Sync** command that reconciles their local research corpus with their own multi-tenant cloud tenant — two-class reconciliation (generated content by format/corrections-currency, human edits per-field newer-wins), additive + baseline-aware deletes, Supabase-Auth session, per-playlist manifest.

**Architecture:** A new `lib/cloud-sync/` module holds pure reconcile logic (`content-hash`, `reconcile-class-a`, `reconcile-class-b`, `companion`) plus stateful helpers (`manifest`, `registry`, `auth`) and an orchestrator (`sync-run`). Sync reads/writes through the **existing `MetadataStore`/`BlobStore` seams** — the *local* replica via `LocalFsMetadataStore`, the *cloud* replica via `SupabaseMetadataStore` constructed with the **user's Supabase session client** (never the service-role key — RLS enforces `owner_id = auth.uid()`). New per-video sync signals (`mdGeneratedAt`, `mdCorrectionsHash`, per-field `annotationsEditedAt`) are added to `VideoSchema` and stamped by the SQL RPCs (migration 0021) and the local store. A `scripts/cloud-sync.ts` CLI (mirroring `worker/main.ts`) is the trigger.

**Tech Stack:** TypeScript, Next.js (App Router), Zod, Supabase (Postgres + Auth + Storage), Jest (unit + `jest.integration.config.ts` for real local-Supabase), `ts-node` for the CLI.

Spec: `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md` (v10 CONVERGED). Section references below (§N) point into it.

## Global Constraints

Every task's requirements implicitly include this section. Values copied verbatim from the spec.

- **Money path — a sync copy NEVER charges.** An additive create (§5.6) is a pure metadata/doc copy: it must **never** route through the metered enqueue (`lib/job-queue/producer.ts`), never consume `spend_ledger`, never resurrect derived cache (HTML/PDF). No sync path may call the ingestion/dig producers. *Over-copy is safe; charging for a copy is the bug.*
- **No service-role key on the local machine (§6).** The CLI authenticates as the user (Supabase Auth session; anon key + user JWT). All cloud I/O is RLS-scoped to `auth.uid()`. `owner_id` is derived from the session, never client-supplied. This must not trip `scripts/check-service-confinement.ts` (`npm run check:confinement`).
- **`mdHash` is MD-body-only (§5.2):** bytes normalized to LF line endings + exactly one trailing newline + Unicode NFC, then SHA-256 hex. One shared impl (`lib/cloud-sync/content-hash.ts`), byte-identical across local-file and Postgres-`jsonb` backends. It is NOT over human fields.
- **`Video.summaryMd` is a blob KEY/filename (`\`${baseName}.md\``), NOT the MD body** (`lib/pipeline.ts:57,264`; cloud stores it in `artifacts.summaryMd.key`). The MD **body** must be read via `BlobStore.get(principal, video.summaryMd)` and *that* is hashed. **Never** call `mdHash(video.summaryMd)` — it would hash the filename. `mdHash` itself is a **manifest-baseline + in-flight** value; it is NOT persisted onto the `Video` record.
- **Sync-path writes carry the SOURCE timestamp, never `now()` (§5.1).** When sync applies a winning human value to the receiver, the receiver's `annotationsEditedAt` for that field is set to the **source's** timestamp (writers take an explicit timestamp on the sync path; the user-edit path still stamps `now()`).
- **Companion scalars are CARRIED verbatim, never re-derived (§4.1, R9).** `ratings` (5 values), `overallScore`, `videoType`, `audience`, `tags`, `tldr`, `takeaways` are copied from the sender's record with the winning MD — `reconstructVideo` must NEVER be used to rebuild them on the receiver (it would fabricate flat ratings and drop tldr/takeaways/tags).
- **Class A and Class B reconcile INDEPENDENTLY (§5).** A format upgrade never touches human fields; a human edit never touches the MD. **`corrections` reconciles FIRST** (§5.4) because it feeds Class-A corrections-currency (§5.3).
- **Additive + baseline-aware deletes only (§5.6).** Never propagate a delete (M2b tombstones). A baseline-less replica may resurrect (accepted R2).
- **New sync-signal fields are `.optional()`** — every existing record predates them; reads must be forward-tolerant. `ModelEnvelopeSchema` drops `.strict()` so a new-writer envelope never makes an old reader return null.
- **Next migration number = `0021`** (0020 is the latest).
- **Reconcile is pure + single-run.** Reconcile functions are pure (no I/O); orchestration is single-run, no concurrency, idempotent + resumable. Per-video errors are isolated.

## File Structure

**New files:**
- `lib/cloud-sync/content-hash.ts` — canonical MD-body-only `mdHash` (§5.2).
- `lib/cloud-sync/types.ts` — shared sync types: per-class signals, manifest baseline, reconcile decisions, run report.
- `lib/cloud-sync/reconcile-class-b.ts` — pure per-field clear-aware 3-way merge (§5.4). Runs first.
- `lib/cloud-sync/reconcile-class-a.ts` — pure currency→format→recency decision (§5.3).
- `lib/cloud-sync/companion.ts` — pure model-transfer decision (§4.2).
- `lib/cloud-sync/backfill.ts` — non-destructive legacy stamp backfill (§5.5).
- `lib/cloud-sync/manifest.ts` — per-playlist baseline + conflict log (§8).
- `lib/cloud-sync/registry.ts` — local playlist discovery + `playlist_key` derivation + union (§7.1, §7 step 1).
- `lib/cloud-sync/auth.ts` — Supabase-Auth session + token storage (§6).
- `lib/cloud-sync/sync-run.ts` — orchestrator (§7).
- `scripts/cloud-sync.ts` — CLI entrypoint (§9).
- `supabase/migrations/0021_cloud_sync_signals.sql` — RPC stamping changes (§5.7).
- Test files mirror each under `tests/lib/cloud-sync/*.test.ts` (unit) and `tests/integration/cloud-sync/*.int.test.ts` (integration).

**Modified files:**
- `types/index.ts` — `VideoSchema` += 3 optional signal groups.
- `lib/html-doc/model-store.ts` — `ModelEnvelopeSchema` += `sourceMdHash?`, drop `.strict()`.
- `lib/storage/metadata-store.ts` — `updateVideoAnnotations` signature += `corrections`; add optional sync-path timestamp param.
- `lib/storage/supabase/supabase-metadata-store.ts` — pass `corrections` + sync timestamp to RPC.
- `lib/storage/local/local-metadata-store.ts` + `lib/index-store.ts` — stamp per-field `annotationsEditedAt` and `mdGeneratedAt`/`mdCorrectionsHash`.
- `lib/pipeline.ts` — stamp `mdGeneratedAt`/`mdCorrectionsHash` on generation.
- `package.json` — `cloud-sync` script.

---

## Task 1: Canonical MD-body `mdHash`

**Files:**
- Create: `lib/cloud-sync/content-hash.ts`
- Test: `tests/lib/cloud-sync/content-hash.test.ts`

**Interfaces:**
- Consumes: nothing (Node `crypto`).
- Produces: `mdHash(md: string): string` — SHA-256 hex of the canonicalized MD body. `canonicalizeMd(md: string): string` — the normalization (exported for cross-backend golden tests).

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/content-hash.test.ts
import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';

describe('canonicalizeMd', () => {
  it('normalizes CRLF and CR to LF', () => {
    expect(canonicalizeMd('a\r\nb\rc')).toBe('a\nb\nc\n');
  });
  it('collapses trailing newlines to exactly one', () => {
    expect(canonicalizeMd('body\n\n\n')).toBe('body\n');
    expect(canonicalizeMd('body')).toBe('body\n');
  });
  it('applies Unicode NFC', () => {
    // "é" as combining sequence (U+0065 U+0301) → precomposed (U+00E9)
    expect(canonicalizeMd('é')).toBe('é\n');
  });
});

describe('mdHash', () => {
  it('is stable, hex, 64 chars', () => {
    const h = mdHash('# Title\n\nbody\n');
    expect(h).toMatch(/^[0-9a-f]{64}$/);
    expect(mdHash('# Title\n\nbody\n')).toBe(h);
  });
  it('is invariant to line-ending and trailing-newline differences (cross-backend equality)', () => {
    // Local file may store CRLF + trailing blank line; Postgres jsonb may store LF only.
    expect(mdHash('# T\r\n\r\nbody\r\n\r\n')).toBe(mdHash('# T\n\nbody\n'));
  });
  it('differs when the body content differs', () => {
    expect(mdHash('a\n')).not.toBe(mdHash('b\n'));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest content-hash`
Expected: FAIL — cannot find module `@/lib/cloud-sync/content-hash`.

- [ ] **Step 3: Write minimal implementation**

```ts
// lib/cloud-sync/content-hash.ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest content-hash`
Expected: PASS (7 assertions).

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/content-hash.ts tests/lib/cloud-sync/content-hash.test.ts
git commit -m "feat(cloud-sync): canonical MD-body mdHash (§5.2)"
```

---

## Task 2: Sync-signal schema fields + forward-tolerant envelope

**Files:**
- Modify: `types/index.ts:47-86` (`VideoSchema`)
- Modify: `lib/html-doc/model-store.ts:14-22` (`ModelEnvelopeSchema`)
- Modify: `lib/storage/metadata-store.ts:16-62` (`updateVideoAnnotations` signature)
- Create: `lib/cloud-sync/types.ts`
- Test: `tests/lib/cloud-sync/schema.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `VideoSchema` gains `mdGeneratedAt?: string (datetime)`, `mdCorrectionsHash?: string`, `annotationsEditedAt?: { personalNote?: string; personalScore?: string; corrections?: string }` (all datetimes).
  - `ModelEnvelope` gains `sourceMdHash?: string`; schema is non-strict.
  - `MetadataStore.updateVideoAnnotations(p, videoId, set, clear, opts?)` where `set` is `Partial<Pick<Video,'personalScore'|'personalNote'|'archived'|'corrections'>>`, `clear` is `('personalScore'|'personalNote'|'corrections')[]`, and `opts?: { editedAt?: string }` (sync-path source timestamp).
  - `lib/cloud-sync/types.ts` exports the shared types used across tasks (see Step 3).

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/schema.test.ts
import { VideoSchema } from '@/types';
import { ModelEnvelopeSchema } from '@/lib/html-doc/model-store';

const baseVideo = {
  id: 'v1', title: 'T', youtubeUrl: 'https://youtu.be/v1', language: 'en',
  durationSeconds: 1, archived: false,
  ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
};

describe('VideoSchema sync signals', () => {
  it('accepts the new optional signal fields', () => {
    const v = VideoSchema.parse({
      ...baseVideo,
      mdGeneratedAt: '2026-07-17T00:00:00.000Z',
      mdCorrectionsHash: 'abc',
      annotationsEditedAt: { personalNote: '2026-07-17T00:00:00.000Z' },
    });
    expect(v.mdCorrectionsHash).toBe('abc');
    expect(v.annotationsEditedAt?.personalNote).toBeDefined();
  });
  it('still parses a legacy record with none of them', () => {
    expect(() => VideoSchema.parse(baseVideo)).not.toThrow();
  });
});

describe('ModelEnvelopeSchema forward tolerance', () => {
  const env = {
    sourceMd: 'x', generatedAt: '2026-07-17', sourceSections: ['A'],
    model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
  };
  it('accepts an optional sourceMdHash', () => {
    expect(ModelEnvelopeSchema.parse({ ...env, sourceMdHash: 'deadbeef' }).sourceMdHash).toBe('deadbeef');
  });
  it('ignores an unknown future key instead of failing (no .strict())', () => {
    expect(() => ModelEnvelopeSchema.parse({ ...env, futureKey: 1 })).not.toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest cloud-sync/schema`
Expected: FAIL — `mdCorrectionsHash` unknown / `.strict()` rejects `futureKey`.

- [ ] **Step 3: Write minimal implementation**

In `types/index.ts`, inside `VideoSchema` (after `summaryReady`, before the closing `});`):

```ts
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
```

In `lib/html-doc/model-store.ts`, change the envelope schema (§4.2, §5.7):

```ts
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
```

In `lib/storage/metadata-store.ts`, widen `updateVideoAnnotations`:

```ts
  updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
    clear: ('personalScore' | 'personalNote' | 'corrections')[],
    opts?: { editedAt?: string },
  ): Promise<{ found: boolean }>;
```

Create `lib/cloud-sync/types.ts`:

```ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest cloud-sync/schema`
Expected: PASS.

Also run the type-checker to confirm the `updateVideoAnnotations` widening didn't break existing callers (the local/cloud impls are updated in Task 4; a `Partial<Pick<…>>` widening + new optional param is source-compatible with existing call sites):

Run: `npx tsc --noEmit`
Expected: no new errors from `types/index.ts` / `model-store.ts` (impl signature mismatches, if any, are fixed in Task 4 — if tsc flags the two impls not yet matching the widened interface, that is expected and closed in Task 4).

- [ ] **Step 5: Commit**

```bash
git add types/index.ts lib/html-doc/model-store.ts lib/storage/metadata-store.ts lib/cloud-sync/types.ts tests/lib/cloud-sync/schema.test.ts
git commit -m "feat(cloud-sync): sync-signal schema fields + forward-tolerant ModelEnvelope (§5.1,§5.7)"
```

---

## Task 3: Migration 0021 — stamping RPCs

**Files:**
- Create: `supabase/migrations/0021_cloud_sync_signals.sql`
- Test: `tests/integration/cloud-sync/stamping.int.test.ts`

**Interfaces:**
- Consumes: existing `update_video_annotations` (0016), `merge_video_data` (0007), `persist_summary` (0009).
- Produces (new SQL behavior, called by Task 4's store layer):
  - `update_video_annotations(p_playlist_id, p_video_id, p_set, p_clear, p_edited_at timestamptz DEFAULT now())` — allowlist now `{personalScore, personalNote, corrections, archived}`; for each **Class-B** key set or cleared (`personalScore`/`personalNote`/`corrections`, NOT `archived`), stamp `data.annotationsEditedAt.<field> = p_edited_at`. An `archived`-only write stamps nothing.
  - `merge_video_data(p_playlist_id, p_video_id, p_fields, p_edited_at timestamptz DEFAULT now())` — if `p_fields` contains a Class-B key, stamp that field's `annotationsEditedAt`; otherwise leave `annotationsEditedAt` untouched (§5.7 conditional restamp).
  - `persist_summary(...)` — additionally re-applies `mdGeneratedAt` + `mdCorrectionsHash` from `p_video` (§5.7).

Migration RPCs are `create or replace` (idempotent redeploy) and keep their existing auth guards verbatim.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/cloud-sync/stamping.int.test.ts
// Runs against local Supabase (jest.integration.config.ts). Uses the shared
// integration harness to create an owner session + a playlist + a video row.
import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';

describe('0021 stamping RPCs', () => {
  it('update_video_annotations stamps only the changed Class-B field, not archived', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_set: { personalNote: 'hi', archived: true }, p_clear: [],
      p_edited_at: '2026-07-17T10:00:00.000Z',
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.annotationsEditedAt?.personalNote).toBe('2026-07-17T10:00:00.000Z');
    expect(row.annotationsEditedAt?.personalScore).toBeUndefined();
    expect(row.annotationsEditedAt?.corrections).toBeUndefined();
    expect(row.personalNote).toBe('hi');
    expect(row.archived).toBe(true);
  });

  it('a clear stamps the timestamp while removing the value', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx, { personalNote: 'old' });
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId, p_set: {}, p_clear: ['personalNote'],
      p_edited_at: '2026-07-17T11:00:00.000Z',
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.personalNote).toBeUndefined();
    expect(row.annotationsEditedAt?.personalNote).toBe('2026-07-17T11:00:00.000Z');
  });

  it('corrections is now allowlisted (was dropped) and stamps its own timestamp', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_set: { corrections: 'fix name' }, p_clear: [], p_edited_at: '2026-07-17T12:00:00.000Z',
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.corrections).toBe('fix name');
    expect(row.annotationsEditedAt?.corrections).toBe('2026-07-17T12:00:00.000Z');
  });

  it('resolves the 4-key call (no p_edited_at) unambiguously — no PGRST203 overload (Blocking ④)', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    // Call EXACTLY as SupabaseMetadataStore does today — WITHOUT p_edited_at. Must not error
    // with "could not choose the best candidate function"; must stamp with now().
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId, p_set: { personalNote: 'x' }, p_clear: [],
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.personalNote).toBe('x');
    expect(row.annotationsEditedAt?.personalNote).toBeDefined();
    // Same for merge_video_data's 3-key call:
    await ctx.rpc('merge_video_data', { p_playlist_id: playlistId, p_video_id: videoId, p_fields: { corrections: 'z' } });
    expect((await ctx.readVideoData(playlistId, videoId)).annotationsEditedAt?.corrections).toBeDefined();
  });

  it('an archived-only write leaves annotationsEditedAt absent (Medium — no empty {}) ', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId, p_set: { archived: true }, p_clear: [],
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.annotationsEditedAt).toBeUndefined();
    expect(row.archived).toBe(true);
  });

  it('merge_video_data does NOT stamp annotationsEditedAt for a non-Class-B (MD-finalize) write', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('merge_video_data', {
      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.annotationsEditedAt).toBeUndefined();
  });

  it('persist_summary stamps mdGeneratedAt + mdCorrectionsHash', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.persistSummary(playlistId, videoId, {
      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4, docVersion: { major: 3, minor: 3 }, processedAt: '2026-07-17T13:00:00.000Z',
    }, 'committed');
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.mdGeneratedAt).toBe('2026-07-17T13:00:00.000Z');
    expect(row.mdCorrectionsHash).toBe('h1');
  });
});
```

> **Build the shared integration harness FIRST (consumed by Tasks 3, 4, 12, 14 — Medium M3).** Create `tests/integration/helpers/cloud.ts` as a THIN wrapper over the existing integration harness (the reservation-release and cloud-doc suites already stand up an owner session + playlist + video against local Supabase — reuse their setup; do not fork it). It must expose, with concrete signatures:
> - `makeOwnerContext(): Promise<Ctx>` — an authenticated owner + a `userClient` (RLS-scoped, NOT service-role) + `ctx.principal`/`ctx.localPrincipal`.
> - `seedVideo(ctx, overrides?): Promise<{ playlistId; videoId }>` and `seedLocalPlaylist(ctx, opts?)` / `seedCloudVideo(ctx, video)`.
> - `ctx.rpc(name, args)`, `ctx.readVideoData(playlistId, videoId)`, `ctx.persistSummary(playlistId, videoId, video, status)`, `ctx.readManifest()`.
> - `ctx.spendLedgerTotal(): Promise<number>` — sum of `spend_ledger` for the owner (money-safety assertions).
> - `ctx.syncDeps(opts?: { failCloudPromote?: boolean }): SyncDeps` — builds the `SyncDeps` for `runSync` with the **user-session** cloud store; when `failCloudPromote` is set, wraps the cloud blob so its promote throws AFTER staging (the crash-safety fault-injection seam for Behavior #11). This wrapper is the ONLY fault-injection mechanism the plan relies on — implement it here, once.
>
> Name Task 3's covering file `tests/integration/cloud-sync/stamping.int.test.ts`.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- cloud-sync/stamping`
Expected: FAIL — `p_edited_at` param unknown / `corrections` not allowlisted / `annotationsEditedAt` never written / `mdGeneratedAt` absent.

- [ ] **Step 3: Write the migration**

```sql
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

-- (3) persist_summary: SAME 5-arg signature (no drop needed). Copy the EXACT current body
--     from 0009 and add ONLY the two keys below to the summary-owned jsonb_build_object.
--     Do NOT retype the body from memory — the shown snippet is a DIFF, not the whole function.
--
--   create or replace function persist_summary(
--     p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text
--   ) ...  -- everything from 0009 stays verbatim: the ownership guard, the
--          -- `jsonb_strip_nulls(jsonb_build_object('language',...,'docVersion',...))`,
--          -- the artifacts.summaryMd.status promotion-preservation CASE, `updated_at = now()`,
--          -- and the row-count raise. ONLY add these two entries to that jsonb_build_object:
--             'mdGeneratedAt', p_video->'mdGeneratedAt',
--             'mdCorrectionsHash', p_video->'mdCorrectionsHash'
```

> **Implementer — CRITICAL (do not drop clauses):** `git show HEAD:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql` and copy the `persist_summary` body **verbatim**, then insert only the two `mdGeneratedAt`/`mdCorrectionsHash` keys. The plan does NOT reprint the full body precisely to avoid an implementer copying a paraphrase that silently drops the ownership guard, the status-promotion `case`, or the row-count raise. Likewise diff the new `update_video_annotations` (vs 0016) and `merge_video_data` (vs 0007) so no existing clause is lost.

- [ ] **Step 4: Apply the migration + run the test**

Run:
```bash
npx supabase migration up   # or the project's local-migration command in docs/deploy.md
npm run test:integration -- cloud-sync/stamping
```
Expected: PASS (5 cases).

- [ ] **Step 5: Guard against a regression in existing RPC callers**

Run: `npm run test:integration -- persist_summary annotations`
Expected: existing summary/annotation integration tests still PASS (the added params default to `now()`, existing callers unaffected).

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/0021_cloud_sync_signals.sql tests/integration/cloud-sync/stamping.int.test.ts
git commit -m "feat(cloud-sync): migration 0021 — per-field annotation stamping + corrections allowlist + md signals (§5.7)"
```

---

## Task 4: Store-layer stamping (both backends) + local pipeline

**Files:**
- Modify: `lib/storage/supabase/supabase-metadata-store.ts` (`updateVideoAnnotations`, `updateVideoFields`)
- Modify: `lib/storage/local/local-metadata-store.ts` + `lib/index-store.ts` (`updateVideoAnnotations`, `updateVideoFields`, `upsertVideo`)
- Modify: `lib/pipeline.ts:260-278` (stamp `mdGeneratedAt`/`mdCorrectionsHash = mdHash('')` on first generation)
- Modify: `app/api/videos/[id]/regenerate/route.ts:64-71` (stamp `mdGeneratedAt`/`mdCorrectionsHash` on the corrected write — Blocking)
- Modify: `lib/html-doc/generate.ts:49-55` (+ any serve-time model writer) — set `sourceMdHash: mdHash(sourceMd)` in the envelope (High)
- Test: `tests/lib/cloud-sync/local-stamping.test.ts`, `tests/lib/cloud-sync/regenerate-stamp.test.ts`, `tests/lib/cloud-sync/model-writer-hash.test.ts`, `tests/integration/cloud-sync/cloud-stamping.int.test.ts`

**Interfaces:**
- Consumes: `mdHash` (Task 1), migration RPCs (Task 3), the widened `updateVideoAnnotations` signature (Task 2).
- Produces: both `MetadataStore` impls stamp per-field `annotationsEditedAt` (user path → `now()`, sync path → `opts.editedAt`), pass `corrections` through, and stamp `mdGeneratedAt`/`mdCorrectionsHash` when a summary MD is persisted. `lib/pipeline.ts` sets `mdGeneratedAt = new Date().toISOString()` and `mdCorrectionsHash = mdHash-of-corrections` at generation.

> **Design note (sync-path timestamp):** the local store must mirror the cloud RPC semantics. On the **user-edit path** (existing callers, no `opts`), stamp `annotationsEditedAt.<field> = new Date().toISOString()`. On the **sync path** (`opts.editedAt` provided), write that exact string. `mdCorrectionsHash` is `mdHash(corrections ?? '')` — the digest of the corrections string the MD was generated from (empty-string hash when no corrections), NOT the MD hash.

- [ ] **Step 1: Write the failing test (local)**

```ts
// tests/lib/cloud-sync/local-stamping.test.ts
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { Video } from '@/types';

async function tmpRoot(): Promise<string> {
  return fs.mkdtemp(path.join(os.tmpdir(), 'cs-local-'));
}
const v = (id: string): Video => ({
  id, title: 'T', youtubeUrl: `https://youtu.be/${id}`, language: 'en', durationSeconds: 1,
  archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
});

describe('local per-field annotation stamping', () => {
  it('stamps only the edited field on the user path', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoAnnotations(p, 'a', { personalNote: 'hi' }, []);
    const idx = await localMetadataStore.readIndex(p);
    const rec = idx.videos.find((x) => x.id === 'a')!;
    expect(rec.annotationsEditedAt?.personalNote).toBeDefined();
    expect(rec.annotationsEditedAt?.personalScore).toBeUndefined();
  });

  it('writes the SOURCE timestamp on the sync path (opts.editedAt), not now()', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoAnnotations(p, 'a', { personalNote: 'hi' }, [], { editedAt: '2020-01-01T00:00:00.000Z' });
    const idx = await localMetadataStore.readIndex(p);
    expect(idx.videos.find((x) => x.id === 'a')!.annotationsEditedAt?.personalNote).toBe('2020-01-01T00:00:00.000Z');
  });

  it('a clear stamps the timestamp and removes the value', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, { ...v('a'), personalNote: 'old' });
    await localMetadataStore.updateVideoAnnotations(p, 'a', {}, ['personalNote'], { editedAt: '2021-01-01T00:00:00.000Z' });
    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
    expect(rec.personalNote).toBeUndefined();
    expect(rec.annotationsEditedAt?.personalNote).toBe('2021-01-01T00:00:00.000Z');
  });

  // PRODUCTION PATH: local personalNote/corrections edits flow through updateVideoFields
  // (the review + regenerate routes), NOT updateVideoAnnotations (shape-parity only —
  // local-metadata-store.ts:62-66). This is where the stamp must actually live.
  it('updateVideoFields stamps annotationsEditedAt for a Class-B field (corrections)', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoFields(p, 'a', { corrections: 'fix' });
    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
    expect(rec.corrections).toBe('fix');
    expect(rec.annotationsEditedAt?.corrections).toBeDefined();
  });
  it('updateVideoFields does NOT stamp annotationsEditedAt for a non-Class-B field', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
    expect(rec.annotationsEditedAt).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/local-stamping`
Expected: FAIL — `annotationsEditedAt` not written / clear not stamped.

- [ ] **Step 3: Implement**

`lib/index-store.ts` — add a per-field stamping helper and use it in `updateVideoAnnotations` and `updateVideoFields` (when a Class-B key is present). Sketch (adapt to the file's actual read-modify-write shape):

```ts
const CLASS_B = ['personalNote', 'personalScore', 'corrections'] as const;

function stampAnnotations(
  video: Video,
  changed: readonly ('personalNote' | 'personalScore' | 'corrections')[],
  editedAt: string,
): Video {
  if (changed.length === 0) return video;
  const at = { ...(video.annotationsEditedAt ?? {}) };
  for (const f of changed) at[f] = editedAt;
  return { ...video, annotationsEditedAt: at };
}
```

In the local `updateVideoAnnotations(p, videoId, set, clear, opts?)`:
- compute `editedAt = opts?.editedAt ?? new Date().toISOString()`;
- apply `set`/`clear` to the record (existing logic), also handling `corrections` now;
- collect the Class-B keys touched (in `set` or `clear`), call `stampAnnotations`;
- write the record back through the atomic index write.

In `updateVideoFields(p, id, fields, opts?)`: if `fields` contains a Class-B key (e.g. a `corrections` write from the regenerate route), stamp those fields with `opts?.editedAt ?? now()`. **Do NOT** stamp for a non-Class-B field write (MD-finalize / `summaryHtml: null` / `tldr`).

**(a) First-generation stamp** — `lib/pipeline.ts`, where the `Video` is built for `upsertVideo` (around line 260–278), add:

```ts
import { mdHash } from '@/lib/cloud-sync/content-hash';
// ...
const video: Video = {
  // ...existing fields, docVersion: CURRENT_DOC_VERSION, processedAt: ...
  mdGeneratedAt: new Date().toISOString(),
  mdCorrectionsHash: mdHash(''),   // a first-generation MD reflects EMPTY corrections
};
```
A first-generation MD has no corrections applied, so `mdCorrectionsHash = mdHash('')`. This is deterministic and matches the compare path (Task 7 compares against `mdHash(reconciledCorrections)`; when no corrections exist, both sides are `mdHash('')` = current).

**(b) Regenerate/fix stamp (Blocking — §5.3 depends on it)** — `app/api/videos/[id]/regenerate/route.ts` is the ONLY path that *applies* corrections into the MD (`fixSummary`, line ~60), yet today it never stamps the currency signals. After it writes the corrected MD (`fs.promises.writeFile(mdPath, updatedContent)`, ~line 68) and calls `store.updateVideoFields(principal, videoId, { tldr, takeaways, summaryHtml: null })` (~line 71), **extend that same `updateVideoFields` call** to also stamp:

```ts
await store.updateVideoFields(principal, videoId, {
  tldr, takeaways, summaryHtml: null,
  mdGeneratedAt: new Date().toISOString(),
  mdCorrectionsHash: mdHash(trimmedCorrections ?? ''),  // digest of the corrections THIS MD was fixed from
});
```
(For the empty-corrections clear branch at `route.ts:56-57`, `trimmedCorrections` is `undefined` → `mdHash('')`.) Without this, a corrected MD is judged **corrections-stale forever** and a stale higher-format uncorrected MD from the other replica can overwrite it — the exact hazard §5.3 exists to prevent. Note: `updateVideoFields` here writes MD-currency fields, NOT a Class-B field, so it must **not** bump `annotationsEditedAt` (the separate earlier `updateVideoFields({ corrections })` at line 55 is the Class-B write that stamps `annotationsEditedAt.corrections`).

**(c) Model-envelope `sourceMdHash` stamp (High — else every companion is deleted)** — every writer of a `ModelEnvelope` must set `sourceMdHash: mdHash(sourceMdBody)` so `decideCompanion` (Task 8) recognizes a valid companion instead of treating it as legacy and deleting it (→ needless re-charge on serve). Add it wherever `writeModelEnvelope` is called with a freshly built envelope — primarily `lib/html-doc/generate.ts` (~line 49-55, which already has the source MD in scope as `sourceMd`) and any serve-time model generation. Set `sourceMdHash: mdHash(sourceMd)` in the envelope object.

**(d) Class-B stamping in the store layer.** Local: `index-store.ts`/`local-metadata-store.ts` `updateVideoAnnotations` AND `updateVideoFields` stamp per-field `annotationsEditedAt` when a Class-B key (`personalNote`/`personalScore`/`corrections`) is set or cleared (user path → `now()`, sync path → `opts.editedAt`), and NOT for a non-Class-B field write. Cloud: `supabase-metadata-store.ts.updateVideoAnnotations` passes `corrections` in `p_set`/`p_clear` and forwards `p_edited_at: opts?.editedAt`; `updateVideoFields` (→ `merge_video_data`) forwards `p_edited_at` when present.

- [ ] **Step 4: Run local test to verify pass**

Run: `npx jest cloud-sync/local-stamping`
Expected: PASS.

- [ ] **Step 4b: Regenerate-route + model-writer stamping tests**

```ts
// tests/lib/cloud-sync/regenerate-stamp.test.ts
// Drive the regenerate route (or its extracted persist helper) with a corrections string and
// assert the persisted record is corrections-CURRENT: mdCorrectionsHash === mdHash(corrections).
import { mdHash } from '@/lib/cloud-sync/content-hash';
// ...set up a local playlist + video with an existing summaryMd, POST corrections='fix name'...
it('a regenerated MD is stamped corrections-current', async () => {
  // after the regenerate call:
  const rec = /* read the video */;
  expect(rec.mdCorrectionsHash).toBe(mdHash('fix name'));
  expect(rec.mdGeneratedAt).toBeDefined();
});
```

```ts
// tests/lib/cloud-sync/model-writer-hash.test.ts
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { writeModelEnvelope, readModelEnvelope } from '@/lib/html-doc/model-store';
it('a freshly written model envelope carries sourceMdHash = mdHash(sourceMd)', async () => {
  // build an envelope via the real generation path (or writeModelEnvelope with sourceMd),
  // read it back, assert:
  const env = /* read back */;
  expect(env!.sourceMdHash).toBe(mdHash(env!.sourceMd));
});
```

Run: `npx jest cloud-sync/regenerate-stamp cloud-sync/model-writer-hash`
Expected: PASS. (These guard Blocking ② and High ⑤ — the two "stamp is never written" gaps.)

- [ ] **Step 5: Write + run the cloud integration mirror**

```ts
// tests/integration/cloud-sync/cloud-stamping.int.test.ts
import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';

it('cloud store forwards corrections + sync timestamp through the RPC', async () => {
  const ctx = await makeOwnerContext();
  const { playlistId, videoId } = await seedVideo(ctx);
  const store = new SupabaseMetadataStore(ctx.userClient); // user-session client, RLS-scoped
  await store.updateVideoAnnotations(ctx.principal, videoId, { corrections: 'fix' }, [], { editedAt: '2019-05-05T00:00:00.000Z' });
  const row = await ctx.readVideoData(playlistId, videoId);
  expect(row.corrections).toBe('fix');
  expect(row.annotationsEditedAt?.corrections).toBe('2019-05-05T00:00:00.000Z');
});
```

Run: `npm run test:integration -- cloud-sync/cloud-stamping`
Expected: PASS. Then the full stamping suite: `npm run test:integration -- cloud-sync/stamping cloud-sync/cloud-stamping`.

- [ ] **Step 6: Full unit suite + commit**

Run: `npm test` (confirm no regressions in existing annotation/pipeline tests).
```bash
git add lib/storage/supabase/supabase-metadata-store.ts lib/storage/local/local-metadata-store.ts lib/index-store.ts lib/pipeline.ts app/api/videos/[id]/regenerate/route.ts lib/html-doc/generate.ts tests/lib/cloud-sync/local-stamping.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts tests/lib/cloud-sync/model-writer-hash.test.ts tests/integration/cloud-sync/cloud-stamping.int.test.ts
git commit -m "feat(cloud-sync): store-layer + regenerate + model-writer stamping (mdCorrectionsHash, sourceMdHash) (§5.1,§5.7,§4.2)"
```

---

## Task 5: Non-destructive legacy backfill

**Files:**
- Create: `lib/cloud-sync/backfill.ts`
- Test: `tests/lib/cloud-sync/backfill.test.ts`

**Interfaces:**
- Consumes: `ClassASignals`, `HumanSnapshot`, `FieldState` (Task 2), `mdHash` (Task 1).
- Produces:
  - `deriveClassASignals(video: Video, mdBody: string | null): ClassASignals` — computes `mdHash` from the **MD body** the caller read from the blob (NOT from `video.summaryMd`, which is a key); marks `backfilled: true` and uses `processedAt` for `mdGeneratedAt` when `mdGeneratedAt` is absent.
  - `deriveHumanSnapshot(video: Video): HumanSnapshot` — per-field `(value, editedAt, backfilled)`, using `updatedAt` (or `processedAt`) as a provisional per-field timestamp flagged `backfilled: true` when `annotationsEditedAt.<field>` is absent.

Backfill is **read-side only** — it never writes provisional values into a record; it produces the in-memory signal snapshot the reconcile consumes, so a backfilled timestamp can be treated as non-load-bearing (§5.5).

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/backfill.test.ts
import { deriveClassASignals, deriveHumanSnapshot } from '@/lib/cloud-sync/backfill';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import type { Video } from '@/types';

const legacy: Video = {
  id: 'a', title: 'T', youtubeUrl: 'https://youtu.be/a', language: 'en', durationSeconds: 1,
  archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: '001_title.md', processedAt: '2026-01-01T00:00:00.000Z', // KEY, not body
  personalNote: 'note', updatedAt: '2026-02-02T00:00:00.000Z',
  // no mdGeneratedAt / mdCorrectionsHash / annotationsEditedAt
};
const BODY = '# S\n\nbody\n';

it('hashes the MD BODY, not the summaryMd key (Blocking ①)', () => {
  const s = deriveClassASignals(legacy, BODY);
  expect(s.mdHash).toBe(mdHash(BODY));
  expect(s.mdHash).not.toBe(mdHash('001_title.md')); // must NOT hash the filename
  expect(s.summaryMdKey).toBe('001_title.md');
});

it('backfills mdGeneratedAt from processedAt and flags it', () => {
  const s = deriveClassASignals(legacy, BODY);
  expect(s.mdGeneratedAt).toBe('2026-01-01T00:00:00.000Z');
  expect(s.backfilled).toBe(true);
  expect(s.docVersionMajor).toBe(1); // absent docVersion ⇒ pre-feature major 1
});

it('mdHash is null when there is no MD body', () => {
  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
  expect(s.mdHash).toBeNull();
  expect(s.summaryMdKey).toBeNull();
});

it('uses real signals (not backfilled) when present', () => {
  const s = deriveClassASignals({ ...legacy, mdGeneratedAt: '2026-03-03T00:00:00.000Z', mdCorrectionsHash: 'h', docVersion: { major: 3, minor: 3 } }, BODY);
  expect(s.backfilled).toBe(false);
  expect(s.mdGeneratedAt).toBe('2026-03-03T00:00:00.000Z');
  expect(s.docVersionMajor).toBe(3);
});

it('backfills a present human field with a provisional flagged timestamp', () => {
  const snap = deriveHumanSnapshot(legacy);
  expect(snap.personalNote.value).toBe('note');
  expect(snap.personalNote.editedAt).toBe('2026-02-02T00:00:00.000Z');
  expect(snap.personalNote.backfilled).toBe(true);
  expect(snap.personalScore.value).toBeUndefined();
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/backfill`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
// lib/cloud-sync/backfill.ts
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
```

- [ ] **Step 4: Run to verify pass**

Run: `npx jest cloud-sync/backfill`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/backfill.ts tests/lib/cloud-sync/backfill.test.ts
git commit -m "feat(cloud-sync): non-destructive legacy signal backfill (§5.5)"
```

---

## Task 6: Class B — per-field clear-aware 3-way merge (runs first)

**Files:**
- Create: `lib/cloud-sync/reconcile-class-b.ts`
- Test: `tests/lib/cloud-sync/reconcile-class-b.test.ts`

**Interfaces:**
- Consumes: `FieldState`, `HumanField`, `HumanSnapshot`, `VideoBaseline` (Task 2).
- Produces:
  - `reconcileField(local: FieldState, cloud: FieldState, baseline: { value?: string|number; editedAt?: string }): FieldMerge`
  - `type FieldMerge = { winner: 'local' | 'cloud' | 'equal'; value: string | number | undefined; editedAt: string | undefined; conflict: boolean }`
  - `reconcileHuman(local: HumanSnapshot, cloud: HumanSnapshot, baseline: VideoBaseline['classB']): Record<HumanField, FieldMerge>`
- The decision is over the **`(value, editedAt)` pair vs baseline** (§5.4): a same-value re-add with an advanced timestamp counts as *changed*. A backfilled-timestamp both-changed conflict resolves to **skip (no write) + conflict:true** (§5.5), never a destructive overwrite.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/reconcile-class-b.test.ts
import { reconcileField } from '@/lib/cloud-sync/reconcile-class-b';

const F = (value: string | number | undefined, editedAt?: string, backfilled = false) => ({ value, editedAt, backfilled });
const B = (value?: string | number, editedAt?: string) => ({ value, editedAt });

describe('reconcileField (§5.4)', () => {
  it('L == C → no action', () => {
    expect(reconcileField(F('x', 't1'), F('x', 't1'), B('x', 't1'))).toMatchObject({ winner: 'equal', value: 'x', conflict: false });
  });
  it('equal values but different timestamps → no conflict (M5)', () => {
    expect(reconcileField(F('note', 't3'), F('note', 't2'), B('old', 't1'))).toMatchObject({ winner: 'equal', value: 'note', conflict: false });
  });
  it('only local changed vs baseline → take local', () => {
    expect(reconcileField(F('new', 't2'), F('old', 't1'), B('old', 't1'))).toMatchObject({ winner: 'local', value: 'new', conflict: false });
  });
  it('only cloud changed vs baseline → take cloud', () => {
    expect(reconcileField(F('old', 't1'), F('new', 't2'), B('old', 't1'))).toMatchObject({ winner: 'cloud', value: 'new' });
  });
  it('a clear on one side (present→absent vs baseline) propagates', () => {
    expect(reconcileField(F(undefined, 't2'), F('x', 't1'), B('x', 't1'))).toMatchObject({ winner: 'local', value: undefined, conflict: false });
  });
  it('both changed to different values → newer per-field editedAt wins + conflict', () => {
    expect(reconcileField(F('L', 't3'), F('C', 't2'), B('base', 't1'))).toMatchObject({ winner: 'local', value: 'L', conflict: true });
    expect(reconcileField(F('L', 't2'), F('C', 't3'), B('base', 't1'))).toMatchObject({ winner: 'cloud', value: 'C', conflict: true });
  });
  it('a same-value re-add (clear→retype same text, advanced ts) is NOT dropped (round-v8 M-1)', () => {
    // baseline present "x"@t1; local cleared@t2; cloud re-added same "x"@t3.
    // cloud's (value,editedAt) differs from baseline (ts advanced) → cloud changed;
    // local also changed (clear). Both changed → newer wins = cloud's re-add.
    expect(reconcileField(F(undefined, 't2'), F('x', 't3'), B('x', 't1'))).toMatchObject({ winner: 'cloud', value: 'x', conflict: true });
  });
  it('no baseline + differ → newer per-field editedAt wins', () => {
    expect(reconcileField(F('L', 't2'), F('C', 't1'), B(undefined, undefined))).toMatchObject({ winner: 'local', value: 'L' });
  });
  it('present one side, absent other, no baseline → copy (additive)', () => {
    expect(reconcileField(F('L', 't1'), F(undefined, undefined), B(undefined, undefined))).toMatchObject({ winner: 'local', value: 'L', conflict: false });
  });
  it('both changed but a side is backfilled → conflict skip (no destructive overwrite, §5.5)', () => {
    const r = reconcileField(F('L', 't2', true), F('C', 't3'), B('base', 't1'));
    expect(r.conflict).toBe(true);
    expect(r.winner).toBe('equal'); // 'equal' == no write applied
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/reconcile-class-b`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
// lib/cloud-sync/reconcile-class-b.ts
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
  // Equal VALUES agree (§5.4 row 1 "L == C → no action") even if their timestamps differ —
  // never flag a conflict for a field both sides hold identically. Keep the newer editedAt (M5).
  if (local.value === cloud.value) {
    const editedAt = newer(local.editedAt, cloud.editedAt) ? local.editedAt : cloud.editedAt;
    return { winner: 'equal', value: local.value, editedAt, conflict: false };
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
```

> **Note:** the "both changed, additive-copy when one side absent + no baseline" row is covered by the `!lChanged && cChanged`/`lChanged && !cChanged` branches once a truly-absent field with no baseline is treated as `changed === false`. Verify the "present one side, absent other, no baseline → copy" test drives the single-sided branch (absent side has `value: undefined, editedAt: undefined` → `changed === false` vs empty baseline).

- [ ] **Step 4: Run to verify pass**

Run: `npx jest cloud-sync/reconcile-class-b`
Expected: PASS (10 cases).

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/reconcile-class-b.ts tests/lib/cloud-sync/reconcile-class-b.test.ts
git commit -m "feat(cloud-sync): Class-B per-field clear-aware 3-way merge (§5.4)"
```

---

## Task 7: Class A — corrections-currency → format → recency

**Files:**
- Create: `lib/cloud-sync/reconcile-class-a.ts`
- Test: `tests/lib/cloud-sync/reconcile-class-a.test.ts`

**Interfaces:**
- Consumes: `ClassASignals` (Task 2), `mdHash` (Task 1). Takes the **reconciled `corrections` value** (from Task 6's result) so it can compute corrections-currency.
- Produces:
  - `reconcileClassA(args: { local: ClassASignals; cloud: ClassASignals; reconciledCorrectionsHash: string }): ClassADecision`
  - `type ClassADecision = { action: 'skip' | 'copyToLocal' | 'copyToCloud'; needsRegen: boolean }`
- Priority (§5.3): **corrections-current > format(`docVersionMajor`, higher wins, never downgrade) > recency-tiebreak(`mdGeneratedAt`)**. Evaluate corrections-currency FIRST so an `mdHash`-equal skip never hides a stale summary (round-v8 H-1). An MD is corrections-current iff `mdCorrectionsHash === reconciledCorrectionsHash`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/reconcile-class-a.test.ts
import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';
import type { ClassASignals } from '@/lib/cloud-sync/types';

const S = (o: Partial<ClassASignals>): ClassASignals => ({
  summaryMdKey: 'x.md', mdHash: 'h', docVersionMajor: 3, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
  mdCorrectionsHash: 'C', backfilled: false, ...o,
});
const CUR = 'C'; // reconciled corrections hash

describe('reconcileClassA (§5.3)', () => {
  it('mdHash equal + both corrections-current → skip', () => {
    expect(reconcileClassA({ local: S({ mdHash: 'h' }), cloud: S({ mdHash: 'h' }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'skip', needsRegen: false });
  });
  it('mdHash equal but BOTH stale vs reconciled corrections → skip but needsRegen (round-v8 H-1)', () => {
    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'skip', needsRegen: true });
  });
  it('mdHash equal but one current, one stale → current wins, NOT skip (Blocking ③ scenario 1)', () => {
    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: CUR }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'copyToCloud', needsRegen: false }); // local current tuple → cloud
  });
  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 2 }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 3 }), reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true });
  });
  it('one corrections-current, other stale → current wins even if stale side has higher format', () => {
    const local = S({ mdCorrectionsHash: CUR, docVersionMajor: 2, mdHash: 'hl' });
    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local (current) overwrites cloud
  });
  it('both current, different major → higher major wins (never downgrade)', () => {
    const local = S({ docVersionMajor: 2, mdHash: 'hl' });
    const cloud = S({ docVersionMajor: 3, mdHash: 'hc' });
    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToLocal', needsRegen: false }); // cloud (major 3) → local
  });
  it('both current, same major, different mdHash → newer mdGeneratedAt unifies', () => {
    const local = S({ mdHash: 'hl', mdGeneratedAt: '2026-05-05T00:00:00.000Z' });
    const cloud = S({ mdHash: 'hc', mdGeneratedAt: '2026-02-02T00:00:00.000Z' });
    expect(reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local newer → cloud converges
  });
  it('neither current (both stale) → keep higher-major, flag needsRegen', () => {
    const local = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 2, mdHash: 'hl' });
    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
    const r = reconcileClassA({ local, cloud, reconciledCorrectionsHash: CUR });
    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true }); // cloud higher major → local, but stale
  });
  it('present only one side (current) → copy, no needsRegen (hydrate/publish)', () => {
    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc' }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToLocal', needsRegen: false });
    expect(reconcileClassA({ local: S({ mdHash: 'hl' }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToCloud', needsRegen: false });
  });
  it('one-sided hydrate of a corrections-STALE MD flags needsRegen (L2)', () => {
    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'copyToLocal', needsRegen: true });
  });
  it('neither side has an MD → skip', () => {
    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ summaryMdKey: null, mdHash: null }), reconciledCorrectionsHash: CUR }))
      .toEqual({ action: 'skip', needsRegen: false });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/reconcile-class-a`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
// lib/cloud-sync/reconcile-class-a.ts
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
```

- [ ] **Step 4: Run to verify pass**

Run: `npx jest cloud-sync/reconcile-class-a`
Expected: PASS (9 cases).

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/reconcile-class-a.ts tests/lib/cloud-sync/reconcile-class-a.test.ts
git commit -m "feat(cloud-sync): Class-A currency→format→recency reconcile (§5.3)"
```

---

## Task 8: Model companion transfer decision

**Files:**
- Create: `lib/cloud-sync/companion.ts`
- Test: `tests/lib/cloud-sync/companion.test.ts`

**Interfaces:**
- Consumes: `ModelEnvelope` (Task 2), `mdHash` (Task 1).
- Produces:
  - `decideCompanion(args: { winnerMdHash: string; senderEnvelope: ModelEnvelope | null }): CompanionAction`
  - `type CompanionAction = { kind: 'ship'; envelope: ModelEnvelope } | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }`
- Rule (§4.2): ship the sender's model **iff** `senderEnvelope.sourceMdHash === winnerMdHash`; else instruct the receiver to delete its model blob (→ lazy regen on owner's next serve) and report `share_needs_owner_serve`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/companion.test.ts
import { decideCompanion } from '@/lib/cloud-sync/companion';
import type { ModelEnvelope } from '@/lib/html-doc/model-store';

const env = (sourceMdHash?: string): ModelEnvelope => ({
  sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
  model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
  ...(sourceMdHash ? { sourceMdHash } : {}),
});

it('ships when the envelope matches the winning MD', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h1') })).toMatchObject({ kind: 'ship' });
});
it('deletes the receiver model when the envelope does not match', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env('h2') }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
it('deletes when the legacy envelope lacks sourceMdHash', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: env(undefined) }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
it('deletes when the sender has no model at all', () => {
  expect(decideCompanion({ winnerMdHash: 'h1', senderEnvelope: null }))
    .toEqual({ kind: 'deleteReceiverModel', shareNeedsOwnerServe: true });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/companion`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
// lib/cloud-sync/companion.ts
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
```

- [ ] **Step 4: Run to verify pass**

Run: `npx jest cloud-sync/companion`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/companion.ts tests/lib/cloud-sync/companion.test.ts
git commit -m "feat(cloud-sync): model companion transfer decision (§4.2)"
```

---

## Task 9: Per-playlist manifest + conflict log

**Files:**
- Create: `lib/cloud-sync/manifest.ts`
- Test: `tests/lib/cloud-sync/manifest.test.ts`

**Interfaces:**
- Consumes: `VideoBaseline`, `HumanField` (Task 2).
- Produces:
  - `manifestPath(dataRoot: string, playlistKey: string): string` → `<dataRoot>/<playlistKey>/.cloud-sync-manifest.json`
  - `readManifest(dataRoot, playlistKey): Promise<Manifest>` — `{ version: 1; videos: Record<videoId, VideoBaseline> }`; a missing/corrupt file returns `{ version: 1, videos: {} }` (degrade to direct-compare, never throw).
  - `writeVideoBaseline(dataRoot, playlistKey, videoId, baseline): Promise<void>` — atomic tmp+rename; called ONLY after §7 step 5's verified commit.
  - `appendConflict(dataRoot, playlistKey, entry): Promise<void>` — JSON-lines to `.cloud-sync-conflicts.log`, **de-duplicated** by `(video_id, class, field, valueL, valueR)` within a run (§8.1).

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/manifest.test.ts
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';

async function root() { return fs.mkdtemp(path.join(os.tmpdir(), 'cs-man-')); }

it('returns an empty manifest when the file is missing', async () => {
  const r = await root();
  expect(await readManifest(r, 'PL1')).toEqual({ version: 1, videos: {} });
});

it('returns an empty manifest (no throw) on a corrupt file', async () => {
  const r = await root();
  await fs.mkdir(path.dirname(manifestPath(r, 'PL1')), { recursive: true });
  await fs.writeFile(manifestPath(r, 'PL1'), '{not json', 'utf8');
  expect(await readManifest(r, 'PL1')).toEqual({ version: 1, videos: {} });
});

it('round-trips a written baseline', async () => {
  const r = await root();
  const base = { classA: { docVersionMajor: 3, mdGeneratedAt: 't', mdCorrectionsHash: 'c', mdHash: 'h' },
                 classB: { personalNote: { value: 'n', editedAt: 't1' }, personalScore: { value: undefined, editedAt: undefined }, corrections: { value: undefined, editedAt: undefined } } };
  await writeVideoBaseline(r, 'PL1', 'v1', base as any);
  expect((await readManifest(r, 'PL1')).videos.v1).toEqual(base);
});

it('de-duplicates a repeated conflict within a run', async () => {
  const r = await root();
  const e = { video_id: 'v1', class: 'B' as const, field: 'personalNote', valueL: 'a', valueR: 'b', reason: 'both-changed' };
  await appendConflict(r, 'PL1', e);
  await appendConflict(r, 'PL1', e);
  const log = await fs.readFile(path.join(r, 'PL1', '.cloud-sync-conflicts.log'), 'utf8');
  expect(log.trim().split('\n')).toHaveLength(1);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/manifest`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
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
```

> **Note:** the module-level `seenConflicts` set is per-process; `resetConflictDedup()` is called by `sync-run` at the top of each run (Task 12). In tests each case uses a fresh entry so dedup persistence across cases is harmless; the dedup test asserts within one process.

- [ ] **Step 4: Run to verify pass**

Run: `npx jest cloud-sync/manifest`
Expected: PASS.

- [ ] **Step 5: Add manifest + conflict files to gitignore + commit**

Confirm `.cloud-sync-manifest.json` and `.cloud-sync-conflicts.log` are covered by `.gitignore` (add a pattern if not — they are per-replica local state, §8). Then:
```bash
git add lib/cloud-sync/manifest.ts tests/lib/cloud-sync/manifest.test.ts .gitignore
git commit -m "feat(cloud-sync): per-playlist manifest + de-duplicated conflict log (§8)"
```

---

## Task 10: Supabase-Auth session + token storage

**Files:**
- Create: `lib/cloud-sync/auth.ts`
- Modify: `scripts/check-service-confinement.ts` (add `scripts/` to `collectEntrypoints()`)
- Test: `tests/lib/cloud-sync/auth.test.ts`, `tests/lib/cloud-sync/auth-file-store.test.ts`, `tests/lib/cloud-sync/import-guard.test.ts`

**Interfaces:**
- Consumes: `@supabase/supabase-js` `createClient`; env `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Produces:
  - `loadSession(store?: TokenStore): Promise<Session | null>` — reads the persisted refresh token, exchanges it, returns an authenticated session; `null` if none.
  - `getAuthedClient(store?: TokenStore): Promise<SupabaseClient>` — a user-session (RLS-scoped) client; **throws `NoSessionError`** (with a `cloud-sync login` hint) when unauthenticated.
  - `signIn(email, password, store?): Promise<void>` — interactive login; persists the refresh token.
  - `signOut(store?): Promise<void>` — clears the persisted token.
  - `interface TokenStore { read(): Promise<string | null>; write(token: string): Promise<void>; clear(): Promise<void> }` and a default `fileTokenStore` (mode-600, parent-dir + broad-perms check, gitignored path).
- **Never** uses the service-role key. `getAuthedClient` must construct the client with the **anon** key only.

> **Design note:** OS-keychain storage is preferred (§6) but optional in M2a — ship the file-fallback `TokenStore` (mode 600, parent-dir ownership check, fail-closed on group/other perms) as the default, and leave a documented seam (`TokenStore` interface) for a keychain impl. The test targets an **injectable in-memory `TokenStore`** so it runs without real Supabase or the filesystem; the file-store's permission logic gets one focused unit test.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/auth.test.ts
import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';

function memStore(initial: string | null = null): TokenStore {
  let t = initial;
  return { read: async () => t, write: async (x) => { t = x; }, clear: async () => { t = null; } };
}

describe('getAuthedClient', () => {
  it('throws NoSessionError with a login hint when no token is stored', async () => {
    await expect(getAuthedClient(memStore(null))).rejects.toBeInstanceOf(NoSessionError);
    await expect(getAuthedClient(memStore(null))).rejects.toThrow(/cloud-sync login/);
  });
});
```

Plus a focused file-store permission test:

```ts
// tests/lib/cloud-sync/auth-file-store.test.ts
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { makeFileTokenStore } from '@/lib/cloud-sync/auth';

it('writes the token file with mode 600', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'cs-tok-'));
  const store = makeFileTokenStore(path.join(dir, 'token'));
  await store.write('abc');
  const st = await fs.stat(path.join(dir, 'token'));
  expect(st.mode & 0o777).toBe(0o600);
  expect(await store.read()).toBe('abc');
});

it('refuses to read a world/group-readable token file (fail-closed)', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'cs-tok-'));
  const sub = path.join(dir, 'store');
  await fs.mkdir(sub, { mode: 0o700 });
  const file = path.join(sub, 'token');
  await fs.writeFile(file, 'abc', { mode: 0o644 });
  const store = makeFileTokenStore(file);
  await expect(store.read()).rejects.toThrow(/permission/i);
});

it('refuses to read when the parent directory is group/other-writable (High ⑥)', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'cs-tok-'));
  const sub = path.join(dir, 'store');
  await fs.mkdir(sub, { mode: 0o777 });
  await fs.chmod(sub, 0o777);
  await fs.writeFile(path.join(sub, 'token'), 'abc', { mode: 0o600 });
  const store = makeFileTokenStore(path.join(sub, 'token'));
  await expect(store.read()).rejects.toThrow(/group\/other-writable|not owned/i);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/auth`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
// lib/cloud-sync/auth.ts
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
      await fs.mkdir(dir, { recursive: true, mode: 0o700 });
      await fs.chmod(dir, 0o700);          // tighten even if the dir pre-existed
      await assertSafeParent(file);        // fail closed if a foreign/broad ancestor remains
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
```

> **Confinement (Medium M2):** `scripts/check-service-confinement.ts` currently walks only `app/`, `pages/`, `worker/`, `middleware.ts` — **NOT** `scripts/` or `lib/cloud-sync/`. A stray service-role import in the sync code would pass undetected, making the "no service-role on local" assurance vacuous. This task must **close that gap**: extend `collectEntrypoints()` to include `scripts/cloud-sync.ts` (so its `lib/cloud-sync/*` import graph is walked), **and/or** add a jest import-guard `tests/lib/cloud-sync/import-guard.test.ts` (mirror `tests/lib/share/import-guard.test.ts`) that fails if `lib/cloud-sync/**` or `scripts/cloud-sync.ts` transitively imports the service-role key.

- [ ] **Step 4: Run to verify pass + extend the confinement guard**

Run: `npx jest cloud-sync/auth`
Expected: PASS.
Then close the confinement gap (per the note): extend `collectEntrypoints()` in `scripts/check-service-confinement.ts` to include `scripts/`, and/or add `tests/lib/cloud-sync/import-guard.test.ts`. Run `npm run check:confinement` → clean, and confirm the new guard *fails* if a service-role import is deliberately introduced into the sync code (then revert).

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/auth.ts scripts/check-service-confinement.ts tests/lib/cloud-sync/auth.test.ts tests/lib/cloud-sync/auth-file-store.test.ts tests/lib/cloud-sync/import-guard.test.ts
git commit -m "feat(cloud-sync): Supabase-Auth session + fail-closed token store + confinement coverage (§6)"
```

---

## Task 11: Local playlist registry, key derivation + union

**Files:**
- Create: `lib/cloud-sync/registry.ts`
- Test: `tests/lib/cloud-sync/registry.test.ts`

**Interfaces:**
- Consumes: `LocalFsMetadataStore` (`readIndex`, `setPlaylistMeta`), `MetadataStore.listPlaylists` (cloud), `localPrincipal`.
- Produces:
  - `playlistKeyFromUrl(url: string): string | null` — extract the YouTube `list=` id from a playlist URL.
  - `discoverLocalPlaylists(dataRoots: string[]): Promise<LocalPlaylist[]>` where `LocalPlaylist = { playlistKey: string; dataRoot: string; playlistUrl: string }` — scan each root, read `playlist-index.json`, derive `playlistKey` from the stored `playlistUrl` (backfill), de-duplicate by `playlistKey` (mapping `<root>/<dir>` and `<root>/<dir>/raw` to one key).
  - `unionPlaylistKeys(local: LocalPlaylist[], cloudKeys: string[]): string[]` — the §7 step 1 union.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/registry.test.ts
import { playlistKeyFromUrl, unionPlaylistKeys } from '@/lib/cloud-sync/registry';

describe('playlistKeyFromUrl', () => {
  it('extracts list id from a playlist url', () => {
    expect(playlistKeyFromUrl('https://www.youtube.com/playlist?list=PLabc123')).toBe('PLabc123');
  });
  it('extracts from a watch url with a list param', () => {
    expect(playlistKeyFromUrl('https://www.youtube.com/watch?v=x&list=PLxyz')).toBe('PLxyz');
  });
  it('returns null when there is no list param', () => {
    expect(playlistKeyFromUrl('https://youtu.be/x')).toBeNull();
    expect(playlistKeyFromUrl('')).toBeNull();
  });
});

describe('unionPlaylistKeys', () => {
  it('unions local and cloud keys without duplicates', () => {
    const local = [{ playlistKey: 'A', dataRoot: '/a', playlistUrl: 'u' }, { playlistKey: 'B', dataRoot: '/b', playlistUrl: 'u' }];
    expect(unionPlaylistKeys(local as any, ['B', 'C']).sort()).toEqual(['A', 'B', 'C']);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/registry`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
// lib/cloud-sync/registry.ts
import { promises as fs } from 'fs';
import path from 'path';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

export interface LocalPlaylist { playlistKey: string; dataRoot: string; playlistUrl: string; }

export function playlistKeyFromUrl(url: string): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.searchParams.get('list');
  } catch { return null; }
}

/** Scan each data root's subdirectories for a playlist-index.json and derive its key. */
export async function discoverLocalPlaylists(dataRoots: string[]): Promise<LocalPlaylist[]> {
  const byKey = new Map<string, LocalPlaylist>();
  for (const root of dataRoots) {
    let entries: string[] = [];
    try { entries = await fs.readdir(root); } catch { continue; }
    for (const dir of entries) {
      const candidate = path.join(root, dir);
      const dataRoot = await resolveRootShape(candidate); // handles <dir> and <dir>/raw
      if (!dataRoot) continue;
      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
      const key = playlistKeyFromUrl(idx.playlistUrl);
      if (!key) continue;
      if (!byKey.has(key)) byKey.set(key, { playlistKey: key, dataRoot, playlistUrl: idx.playlistUrl });
    }
  }
  return [...byKey.values()];
}

async function resolveRootShape(candidate: string): Promise<string | null> {
  for (const p of [candidate, path.join(candidate, 'raw')]) {
    try { await fs.access(path.join(p, 'playlist-index.json')); return p; } catch { /* try next */ }
  }
  return null;
}

export function unionPlaylistKeys(local: LocalPlaylist[], cloudKeys: string[]): string[] {
  return [...new Set([...local.map((l) => l.playlistKey), ...cloudKeys])];
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npx jest cloud-sync/registry`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/registry.ts tests/lib/cloud-sync/registry.test.ts
git commit -m "feat(cloud-sync): local playlist discovery + key derivation + union (§7.1)"
```

---

## Task 12: Sync-run orchestration

**Files:**
- Create: `lib/cloud-sync/sync-run.ts`
- Test: `tests/integration/cloud-sync/sync-run.int.test.ts`

**Interfaces:**
- Consumes: everything above — `deriveClassASignals`/`deriveHumanSnapshot` (T5), `reconcileHuman` (T6), `reconcileClassA` (T7), `decideCompanion` (T8), `readManifest`/`writeVideoBaseline`/`appendConflict`/`resetConflictDedup` (T9), `discoverLocalPlaylists`/`unionPlaylistKeys` (T11), `mdHash` (T1), and the two `MetadataStore` impls + `BlobStore`s.
- Produces:
  - `runSync(deps: SyncDeps, opts?: { playlistKey?: string }): Promise<SyncReport>`
  - `SyncDeps = { local: MetadataStore; cloud: MetadataStore; localBlob: BlobStore; cloudBlob: BlobStore; dataRoots: string[]; ownerId: string }`
  - `SyncReport = { created; updatedLocal; updatedCloud; skippedIdentical; mergedFields; conflictsLogged; removed; shareNeedsOwnerServe; needsRegen; archivedNotSynced; errors }` (all counters, plus per-video error list).
- **Order per video (§5, §7 step 3):** Class B FIRST (produces reconciled `corrections` → `reconciledCorrectionsHash = mdHash(corrections)`), THEN Class A (consumes it). Atomic Class-A transfer per §7 step 4 (stage→verify→promote→finalize the complete tuple + carried scalars), manifest write AFTER verified commit (§7 step 5). A per-video error is caught, counted, and does not abort the run.

**Enumerated Behaviors (contract for tests — required per the Per-Task Checklist for an async, multi-error-path task):**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Read MD body for hashing | any video with `summaryMd` | `readMdBody(store, blob, p, video)` = `blob.get(p, video.summaryMd)` decoded UTF-8; `null` if `summaryMd` null |
| 2 | Class B before Class A | every video | `reconcileHuman` runs, its winners applied, `reconciledCorrectionsHash` computed, THEN `reconcileClassA` |
| 3 | Additive create (money-safe) | video present one side, not in baseline | copy metadata + MD blob via `BlobStore.put`; **never** call the metered producer/enqueuer; `report.created++` |
| 4 | Class-A copy transfer | `reconcileClassA` → `copyTo*` | `transferClassA`: stage winner MD → verify → promote → finalize receiver record (complete tuple + carried scalars) in one update; then `writeVideoBaseline` |
| 5 | Companion ship/delete | after a Class-A copy | `decideCompanion`: ship envelope (`cloudBlob/localBlob.put` model) OR delete receiver model blob + `report.shareNeedsOwnerServe++` |
| 6 | needs_regen report | `reconcileClassA.needsRegen` | `report.needsRegen++`; MD left as the best-available; never fabricate a corrected MD |
| 7 | Baseline-aware remote delete | in baseline, absent other side | do not re-create; `report.removed++`; do not delete the other side |
| 8 | Baseline-less resurrection (R2) | no baseline, present one side | additive create (accepted resurrection) |
| 9 | `archived` divergence | sides' `archived` differ | `report.archivedNotSynced++`; do NOT sync `archived` (R10) |
| 10 | Manifest only after verified commit | Class-A transfer | `writeVideoBaseline` runs only after the receiver tuple verifies durable; a crash before verify leaves baseline unadvanced |
| 11 | stage-fail / promote-fail / finalize-fail | fault at any transfer step | per-video error caught → `report.errors.push`; baseline NOT advanced; staged objects may remain (re-run heals) |
| 12 | Conflict logged (Class B) | `FieldMerge.conflict` | `appendConflict`; `report.conflictsLogged++`; loser value skipped (not written) |
| 13 | Per-video isolation | any one video throws | run continues; other videos still reconcile |

**RLS under a user session (must be verified, not assumed):** the existing staged→committed→promoted plumbing (`consistency.ts`, `summary-handler.ts`) runs in the **worker under the service-role key**. Sync runs under the **authenticated user session** (Task 10). Before reusing that plumbing, confirm each RPC/table it touches (`persist_summary`, blob `put`/promote, `merge_video_data`) is callable under `authenticated` with `owner_id = auth.uid()` — they are `security invoker` with `owner_id = auth.uid() or auth.role() = 'service_role'` guards, so they should work, but the transfer helper must pass the **user-session** stores, and an integration test must exercise the promote/finalize path under a real user JWT (not service role). If any step requires service role, that is a blocker to surface — do NOT smuggle the service-role key onto the local machine.

> This is the integration keystone. Its test runs against real local FS ↔ local Supabase under a **user session**. Because it composes already-unit-tested pure functions, the integration test focuses on **end-to-end wiring + atomicity + money-safety**, not re-testing each reconcile branch.

**Codex behaviors review (required):** because this task is an async multi-error-path state machine, run a Codex adversarial review of the Enumerated Behaviors table above *before writing the transfer/finalize code* (per the project's Behaviors adversarial review rule). Save to `docs/reviews/task-12-sync-run-behaviors-codex.md`.

- [ ] **Step 1: Write the failing integration test**

```ts
// tests/integration/cloud-sync/sync-run.int.test.ts
import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
import { runSync } from '@/lib/cloud-sync/sync-run';

describe('runSync (§7)', () => {
  it('hydrates an empty local replica from a cloud-only video (additive create, no charge)', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId } = await seedLocalPlaylist(ctx); // cloud has 1 promoted-summary video, local empty
    const spendBefore = await ctx.spendLedgerTotal();
    const report = await runSync(ctx.syncDeps());
    expect(report.created).toBeGreaterThanOrEqual(1);
    // money-safety: a sync copy never charges
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
    expect(localIdx.videos.length).toBeGreaterThanOrEqual(1);
  });

  it('publishes a local-only human note to the cloud with the source timestamp', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx, { localNote: { value: 'mine', editedAt: '2026-04-04T00:00:00.000Z' } });
    await runSync(ctx.syncDeps());
    const row = await ctx.readVideoData(ctx.playlistId, ctx.videoId);
    expect(row.personalNote).toBe('mine');
    expect(row.annotationsEditedAt?.personalNote).toBe('2026-04-04T00:00:00.000Z');
  });

  it('does not advance the manifest baseline when the transfer is not verified (crash safety)', async () => {
    // Inject a cloudBlob whose promote throws after staging; assert baseline unchanged + staged object present.
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx);
    const deps = ctx.syncDeps({ failCloudPromote: true });
    await runSync(deps).catch(() => {});
    const m = await ctx.readManifest();
    expect(m.videos[ctx.videoId]).toBeUndefined(); // never advanced for a partial transfer
  });
});
```

> **Implementer:** extend the integration harness (`tests/integration/helpers/cloud.ts`) with `seedLocalPlaylist`, `spendLedgerTotal`, `syncDeps({failCloudPromote?})`, `readManifest`. Reuse the existing staged→committed→promoted plumbing (`consistency.ts`, `summary-handler.ts`) for the atomic transfer rather than inventing a new one.

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:integration -- cloud-sync/sync-run`
Expected: FAIL — `runSync` missing.

- [ ] **Step 3: Implement**

Implement `runSync` plus the named helpers below. Types and the reconcile calls are real; the transfer helper's body reuses the existing staged→promote primitives (name them explicitly, do not reinvent).

```ts
// lib/cloud-sync/sync-run.ts
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import { localPrincipal } from '@/lib/storage/principal';
import type { Video } from '@/types';
import { deriveClassASignals, deriveHumanSnapshot } from './backfill';
import { reconcileHuman, type FieldMerge } from './reconcile-class-b';
import { reconcileClassA } from './reconcile-class-a';
import { decideCompanion } from './companion';
import { readManifest, writeVideoBaseline, appendConflict, resetConflictDedup } from './manifest';
import { discoverLocalPlaylists, unionPlaylistKeys } from './registry';
import { mdHash } from './content-hash';
import type { ClassASignals, HumanField, VideoBaseline } from './types';

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

/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY). */
async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
  if (!video.summaryMd) return null;
  const buf = await blob.get(p, video.summaryMd);
  return buf ? buf.toString('utf8') : null;
}
```

Then implement these helpers (contracts — the implementer writes the bodies against the real primitives named):

- **`enumerateVideoIds(local, cloud, localP, cloudP): Promise<string[]>`** — union of `video_id`s from `local.readIndex(localP)` and `cloud.readIndex(cloudP)`.
- **`hydrationRoot(dataRoots, key): string`** — for a cloud-only playlist, a deterministic local root named by `key` (`path.join(dataRoots[0], key)`).
- **`applyClassBWinners(deps, side, principal, videoId, merges): Promise<number>`** — for each `HumanField` whose `FieldMerge.winner` targets `side` (the loser side gets the write), call `store.updateVideoAnnotations(principal, videoId, set, clear, { editedAt: merge.editedAt })` — set when `value !== undefined`, clear when `undefined`; **carry the source timestamp** (`merge.editedAt`), never `now()`. Returns count of fields written (→ `report.mergedFields`). Log `conflict:true` merges via `appendConflict` (→ `report.conflictsLogged`).
- **`copyAdditiveVideo(deps, from, to, fromP, toP, video, mdBody): Promise<void>`** (Behavior #3, money-safe) — write the video record to the receiver via `to.upsertVideo(toP, video)` (metadata) and `to.<blob>.put(toP, video.summaryMd, Buffer.from(mdBody))` for the MD. **Never** import or call `lib/job-queue/producer.ts` or any enqueue; **never** write `summaryHtml`/PDF (regenerable cache — §5.6). Carries the companion scalars because it copies the whole `Video`.
- **`transferClassA(deps, winnerSide, loserSide, ...): Promise<{ mdHash: string; verified: boolean }>`** (Behaviors #4, #10, #11) — the atomic path:
  1. read the winner MD body; compute `mdHash(body)`.
  2. **stage** the MD to the loser's blob under an idempotency key, reusing the existing staged→committed→promoted protocol in `lib/storage/supabase/consistency.ts` (cloud loser) or the local blob's atomic put (local loser). Name the exact functions used.
  3. **verify** the staged object is readable and hashes to the expected `mdHash`.
  4. **promote**, then **finalize** the receiver `Video` record in ONE update carrying the complete tuple: `summaryMd` (key) + artifact status, `docVersion`, `mdGeneratedAt`, `mdCorrectionsHash`, and all 7 carried companion scalars (`ratings`,`overallScore`,`videoType`,`audience`,`tags`,`tldr`,`takeaways`) copied verbatim from the winner's `Video`. For the cloud loser this is `persist_summary` (which now stamps the md signals — Task 3); for local it is the index write.
  5. return `{ mdHash, verified }`. On any fault, throw — the caller records the error and does NOT advance the baseline.
- **`companionTransfer(deps, winnerSide, loserSide, winnerMdHash, video): Promise<{ shareNeedsOwnerServe: boolean }>`** (Behavior #5) — read the winner's `ModelEnvelope` (`readModelEnvelope`), call `decideCompanion({ winnerMdHash, senderEnvelope })`; on `ship` write the envelope to the loser's blob; on `deleteReceiverModel` delete the loser's model blob (best-effort, OUTSIDE the atomic commit) and return `shareNeedsOwnerServe:true`.
- **`buildBaseline(winnerSignals: ClassASignals, winnerMdHash, mergedHuman): VideoBaseline`** — the manifest baseline written by `writeVideoBaseline` AFTER the transfer verifies (Behavior #10). `mdHash` lives here (manifest), NOT on the `Video` record (Low finding).

`runSync` orchestration:

```ts
export async function runSync(deps: SyncDeps, opts: { playlistKey?: string } = {}): Promise<SyncReport> {
  resetConflictDedup();
  const report: SyncReport = { created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
    mergedFields: 0, conflictsLogged: 0, removed: 0, shareNeedsOwnerServe: 0, needsRegen: 0,
    archivedNotSynced: 0, errors: [] };
  const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
  const cloudKeys = (await deps.cloud.listPlaylists(deps.ownerId)).map((p) => p.playlistKey);
  let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
  if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);

  for (const key of keys) {
    const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot ?? hydrationRoot(deps.dataRoots, key);
    const localP = localPrincipal(dataRoot);
    const cloudP: Principal = { id: 'cloud', indexKey: key }; // resolve via the cloud store's principal convention
    const manifest = await readManifest(dataRoot, key);

    for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
      try {
        const lv = await readVideo(deps.local, localP, id);   // Video | null
        const cv = await readVideo(deps.cloud, cloudP, id);
        const base = manifest.videos[id];

        // Presence / deletes (Behaviors #3,#7,#8) — handle one-sided-with-baseline as delete, else additive.
        // ... (see presence rules §5.6; increments report.created / report.removed) ...

        // 1) Class B FIRST
        const merges = reconcileHuman(deriveHumanSnapshot(lv!), deriveHumanSnapshot(cv!), base?.classB ?? EMPTY_CLASSB);
        report.mergedFields += await applyClassBWinners(/* to loser sides */);
        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));

        // 2) Class A (needs MD bodies for hashing — Behavior #1)
        const la = deriveClassASignals(lv!, await readMdBody(deps.localBlob, localP, lv!));
        const ca = deriveClassASignals(cv!, await readMdBody(deps.cloudBlob, cloudP, cv!));
        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
        if (decision.needsRegen) report.needsRegen++;
        let winnerMdHash: string | null = null;
        if (decision.action === 'copyToCloud') { winnerMdHash = (await transferClassA(/* winner=local, loser=cloud */)).mdHash; report.updatedCloud++; }
        else if (decision.action === 'copyToLocal') { winnerMdHash = (await transferClassA(/* winner=cloud, loser=local */)).mdHash; report.updatedLocal++; }
        else report.skippedIdentical++;

        if (winnerMdHash) {
          if ((await companionTransfer(/* ... */)).shareNeedsOwnerServe) report.shareNeedsOwnerServe++;
        }
        if ((lv?.archived ?? false) !== (cv?.archived ?? false)) report.archivedNotSynced++;

        // 3) Manifest AFTER verified commit (Behavior #10)
        await writeVideoBaseline(dataRoot, key, id, buildBaseline(/* winner signals, winnerMdHash, merges */));
      } catch (e: any) {
        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11,#13
      }
    }
  }
  return report;
}
```

The `readVideo`, `enumerateVideoIds`, `EMPTY_CLASSB`, and presence/delete block are straightforward given `readIndex`; implement them fully (no `// ...` left in the shipped code). The transfer helper is the one place that must name and reuse the real `consistency.ts` staged→promote primitives — verify them under a user session (see the RLS note above).

- [ ] **Step 4: Run to verify pass**

Run: `npm run test:integration -- cloud-sync/sync-run`
Expected: PASS (3 cases).

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/sync-run.ts tests/integration/cloud-sync/sync-run.int.test.ts tests/integration/helpers/cloud.ts
git commit -m "feat(cloud-sync): sync-run orchestration — two-class reconcile, atomic transfer, manifest-after-commit (§7)"
```

---

## Task 13: `cloud-sync` CLI command

**Files:**
- Create: `scripts/cloud-sync.ts`
- Modify: `package.json` (scripts)
- Test: `tests/lib/cloud-sync/cli.test.ts`

**Interfaces:**
- Consumes: `getAuthedClient`/`signIn`/`signOut` (T10), `runSync` (T12), `SupabaseMetadataStore` (user-session client), `localMetadataStore`, blob stores.
- Produces:
  - `parseArgs(argv: string[]): { cmd: 'sync' | 'login' | 'logout'; playlistKey?: string }` (exported, unit-tested).
  - `main(argv): Promise<number>` — exit code; wires `getAuthedClient` → builds `SyncDeps` with the user-session cloud store → `runSync` → prints the report. `login`/`logout` manage the token. `require.main === module` guard mirrors `worker/main.ts`.
- npm script: `"cloud-sync": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/cloud-sync.ts"`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/cloud-sync/cli.test.ts
import { parseArgs } from '@/scripts/cloud-sync';

it('defaults to sync over all playlists', () => {
  expect(parseArgs([])).toEqual({ cmd: 'sync' });
});
it('parses a single-playlist sync', () => {
  expect(parseArgs(['--playlist', 'PLabc'])).toEqual({ cmd: 'sync', playlistKey: 'PLabc' });
});
it('parses login and logout', () => {
  expect(parseArgs(['login'])).toEqual({ cmd: 'login' });
  expect(parseArgs(['logout'])).toEqual({ cmd: 'logout' });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest cloud-sync/cli`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```ts
// scripts/cloud-sync.ts
import { getAuthedClient, signIn, signOut, NoSessionError } from '@/lib/cloud-sync/auth';
import { runSync, type SyncDeps } from '@/lib/cloud-sync/sync-run';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';

export interface ParsedArgs { cmd: 'sync' | 'login' | 'logout'; playlistKey?: string; }

export function parseArgs(argv: string[]): ParsedArgs {
  if (argv[0] === 'login') return { cmd: 'login' };
  if (argv[0] === 'logout') return { cmd: 'logout' };
  const i = argv.indexOf('--playlist');
  return i >= 0 && argv[i + 1] ? { cmd: 'sync', playlistKey: argv[i + 1] } : { cmd: 'sync' };
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
  const dataRoots = (process.env.CLOUD_SYNC_DATA_ROOTS ?? process.env.DATA_ROOT ?? '').split(':').filter(Boolean);

  const deps: SyncDeps = {
    local: localMetadataStore,
    cloud: new SupabaseMetadataStore(client),
    localBlob: localBlobStore,
    cloudBlob: new SupabaseBlobStore(client),
    dataRoots, ownerId,
  };
  const report = await runSync(deps, args.playlistKey ? { playlistKey: args.playlistKey } : {});
  console.log(JSON.stringify(report, null, 2));
  return report.errors.length ? 2 : 0;
}

if (require.main === module) {
  main(process.argv.slice(2)).then((code) => process.exit(code)).catch((e) => { console.error(e); process.exit(1); });
}
```

> **Implementer:** confirm the real constructor names/exports for `SupabaseMetadataStore`/`SupabaseBlobStore` (Explore report §2 gives file paths). If they are singletons rather than classes taking a client, add a factory that binds the user-session client (the key requirement: the cloud store is bound to the RLS-scoped client, never service-role). Confirm the data-root env convention against `worker/main.ts` / `validateStorageEnv()`.

- [ ] **Step 4: Run to verify pass + wire the script**

Add to `package.json` scripts:
```json
"cloud-sync": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/cloud-sync.ts"
```
Run: `npx jest cloud-sync/cli` → PASS. Then a smoke invocation (no session) exits 1 with the login hint:
`npm run cloud-sync` → prints "Run: cloud-sync login", exit 1.

- [ ] **Step 5: Commit**

```bash
git add scripts/cloud-sync.ts package.json tests/lib/cloud-sync/cli.test.ts
git commit -m "feat(cloud-sync): cloud-sync CLI (sync/login/logout) (§9)"
```

---

## Task 14: End-to-end integration scenarios

**Files:**
- Create: `tests/integration/cloud-sync/e2e.int.test.ts`
- Modify: `tests/integration/helpers/cloud.ts` (as needed)

**Interfaces:**
- Consumes: `runSync` + the full stack. No new production code — this task is coverage for the spec's §10 scenarios not already asserted in Tasks 3/4/12.

**Enumerated scenarios (one test block each — §10):**

| # | Scenario | Assertion |
|---|---|---|
| 1 | Class-A anti-recency: higher-major beats newer-timestamp lower-major | receiver ends with the higher-major MD |
| 2 | Stale higher-major does NOT overwrite corrections-current lower-major | corrections-current MD survives on both sides |
| 3 | Neither corrections-current (incl. identical stale MDs) → `needsRegen` counted | `report.needsRegen >= 1`, MD unchanged |
| 4 | Companion scalars carried verbatim (5 real ratings + tldr/takeaways/tags land) | receiver record's `ratings`/`tldr`/`takeaways`/`tags` == sender's, NOT reconstructed |
| 5 | Class-B: note edit local + score edit cloud → both survive | both fields present post-sync |
| 6 | Class-B cleared field not resurrected (baseline-aware) | cleared field stays absent |
| 7 | Synced+shared, model deleted → anon share not-ready until owner serve, counted | `report.shareNeedsOwnerServe >= 1` |
| 8 | Additive create never calls the metered enqueue | `spend_ledger` unchanged (assert total) |
| 9 | Baseline-present remote-delete not re-created | video absent locally after sync, `report.removed` counts it |
| 10 | No-session refusal / client `owner_id` rejected | `getAuthedClient` throws; RLS rejects a forged owner |
| 11 | Additive create excludes regenerable cache | copied receiver record has `summaryHtml`/PDF null/absent (§5.6) |

- [ ] **Step 1: Write the failing tests**

Author one `it(...)` per row above using the harness. Example (row 4, the round-v8 B-1 regression guard):

```ts
it('carries the 5 real ratings + tldr/takeaways/tags verbatim (not reconstructed)', async () => {
  const ctx = await makeOwnerContext();
  // seedCloudVideo writes mdBody to the blob and sets video.summaryMd to the KEY it wrote.
  await seedCloudVideo(ctx, {
    summaryMd: '001_s.md', mdBody: '# S\n\nbody\n',
    ratings: { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 }, // deliberately NON-flat
    overallScore: 3, tldr: 'the tldr', takeaways: ['t1', 't2'], tags: ['x', 'y'],
    docVersion: { major: 3, minor: 3 },
  });
  await runSync(ctx.syncDeps()); // hydrate empty local from cloud
  const local = (await ctx.local.readIndex(ctx.localPrincipal)).videos.find((v) => v.id === ctx.videoId)!;
  expect(local.ratings).toEqual({ usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 });
  expect(local.tldr).toBe('the tldr');
  expect(local.takeaways).toEqual(['t1', 't2']);
  expect(local.tags).toEqual(['x', 'y']);
});
```

- [ ] **Step 2: Run to verify they fail (or pass where already wired)**

Run: `npm run test:integration -- cloud-sync/e2e`
Expected: initially FAIL for any scenario whose wiring is incomplete.

- [ ] **Step 3: Fix wiring gaps surfaced by the scenarios**

Any failing scenario reveals a real gap in Task 12's orchestration (e.g. scalars not carried, delete not honored). Fix in `sync-run.ts` (not in the test). Re-run.

- [ ] **Step 4: Full suite**

Run: `npm test && npm run test:integration -- cloud-sync`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/cloud-sync/e2e.int.test.ts tests/integration/helpers/cloud.ts
git commit -m "test(cloud-sync): end-to-end §10 scenarios (anti-recency, carried scalars, money-safety, deletes)"
```

---

## Self-Review (run after the plan is complete, before dispatch)

**Spec coverage** — every spec section maps to a task:
- §4.1 field classification → T2 (schema), T4 (stamps), T12 (carried scalars in transfer). §4.2 companion → T2 (`sourceMdHash`), T8, T12.
- §5.1 signals/stamping → T3, T4. §5.2 mdHash → T1. §5.3 Class A → T7. §5.4 Class B → T6. §5.5 backfill → T5. §5.6 deletes → T12 (+ T14 row 9). §5.7 migrations → T2, T3, T4.
- §6 auth → T10. §7 run/atomicity → T12; §7.1 discovery → T11. §8 manifest/conflict log → T9. §9 trigger → T13. §10 testing → distributed across T1–T14 (T14 the keystone). §11 residuals → documented, not code. §13 M2b → out of scope.

**Global-constraint coverage:** money-safety (T12/T14 row 8), no service-role (T10/T13 + `check:confinement`), sync-source-timestamp (T3/T4/T12 row 2), carried scalars (T12/T14 row 4), independent + corrections-first ordering (T12 order), forward-tolerant optionals (T2).

**Type consistency:** `ClassASignals`/`HumanSnapshot`/`FieldState`/`VideoBaseline` defined in T2 (`lib/cloud-sync/types.ts`), consumed unchanged by T5–T12. `updateVideoAnnotations` widened once in T2, implemented in T4, called in T12. `mdHash` signature stable from T1.

**Open implementer seams (documented, not placeholders):** the integration harness helpers are now fully specified in Task 3's build-first note (incl. the `failCloudPromote` fault-injection seam); the exact `SupabaseMetadataStore`/`SupabaseBlobStore` construction with a user-session client (T13 note); the data-root env convention (mirror `worker/main.ts`); and the one genuine unknown that must be *verified during T12*, not assumed — whether the `consistency.ts` staged→promote primitives work under an `authenticated` session (RLS note in T12); if they require service role, that is a blocker to surface, never a reason to place the service-role key locally.

## Round-1 review dispositions (2026-07-17)

Dual adversarial review (Codex + independent Claude) of the v1 plan — both **NOT CONVERGED**, strongly corroborating. All Blocking/High/Medium addressed in this revision; reviews saved to `docs/reviews/plan-cloud-sync-m2a-{codex,claude}-r1.md`.

- **Blocking:** ① `mdHash` from the `summaryMd` KEY not the body → T5 `deriveClassASignals(video, mdBody)`, orchestrator reads blob body. ② regenerate route never stamps `mdCorrectionsHash` → T4 edits `regenerate/route.ts`. ③ T7 `mdHash`-equal skip bypasses currency/format → skip only if both-current OR both-stale+same-major. ④ RPC `create or replace` adds an overload (PGRST203) → T3 `drop function` old signatures first.
- **High:** ⑤ `sourceMdHash` never written → T4 stamps model writers. ⑥ token store parent-dir fail-closed → T10 `assertSafeParent`. ⑦ T12 placeholder → concrete helper contracts + Enumerated Behaviors table + RLS-under-authenticated note + required Codex behaviors review.
- **Medium:** persist_summary guard preserved (T3 shows a diff, not a divergent body); `check:confinement` extended to `scripts/`/`lib/cloud-sync/` (T10); harness helpers fully specified incl. fault-injection (T3); T4 tests the production `updateVideoFields` path; Class-B equal-value/diff-ts no longer conflicts (T6); `archived`-only write no empty `{}` (T3).
- **Low:** `mdHash` is manifest-baseline-only, not persisted on the record (T12/Global Constraints); one-sided hydrate of a stale MD flags `needsRegen` (T7); conflict dedup key includes `playlistKey` (T9); additive-excludes-cache test added (T14 row 11).

---

## Execution Handoff

Plan complete. Per the project's Conditional-AFK dev-process, the plan gate is **dual adversarial review to convergence** (Codex + Claude, independent) — not a human ack. On convergence I notify and proceed to **subagent-driven-development**; the only human gate on this branch is the final **merge** (§ Phase 5). The dual review of this plan runs next.
