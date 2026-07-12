# Cloud Dig-Deeper Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an authenticated cloud user trigger durable, charged-once generation of a **text-only**, per-section dig-deeper doc, produced by the worker and persisted as a per-section blob — no serving, frontend, slides, or dig PDF in this slice.

**Architecture:** A cloud branch on the existing dig trigger route authorizes with the session client (via `loadSummaryForServe`, which owner-asserts + gates on a committed summary and does **not** charge a magazine model), dedups on the current-version per-section blob, then enqueues a `{kind:'dig'}` job through the service-role `SupabaseEnqueuer` (charge-once). A new `makeDigHandler` runs in the worker beside `makeSummaryHandler` via a kind→handler dispatcher; it ports the local `digSection` core onto `BlobStore`/`MetadataStore`, skips slide capture, preserves `[[SLIDE:...]]` tokens, and writes one blob per section via staged→promote.

**Tech Stack:** Next.js App Router (vendored), Supabase (Postgres RPC + Storage), TypeScript, Jest + ts-jest, real-Supabase integration tests. Spec: `docs/superpowers/specs/2026-07-12-cloud-dig-generation-design.md`.

## Global Constraints

- **Money invariant:** dig is a durable Job, **charged once at enqueue** via `enqueue_job` (quota `dig`=5/month registered, **0 anon**; `dig_est_cents`=150; `dig_max_attempts`=1). It must **never** route through `resolveMagazineModel`/`reserve_serve_model`. No charge on dedup.
- **Two-client split:** session client (RLS) for auth + all tenant reads; service-role `SupabaseEnqueuer` for the enqueue RPC only. Never a service-role read of tenant data from the route.
- **Text-only:** run `generateDig`; **skip `resolveSlideTokens`**; preserve `[[SLIDE:...]]` tokens verbatim in the persisted doc; `slides: []` in frontmatter.
- **Per-section blobs:** one blob per dug section at `dig/{base}/{sectionId}.r{DIG_GENERATOR_VERSION}.md`, written via staged→promote. No shared mutable companion doc (eliminates the lost-update race by construction).
- **Idempotent + version-aware, no force:** current-version blob present → `200 ready`, no charge. Job `version` = `dig-${DIG_GENERATOR_VERSION}` so a version bump lands in a distinct `jobs_idem_active` slot and re-enqueues+charges. The handler **rejects `job.version !== digJobVersion()`** so a stale queued job cannot write a current-version blob it never paid for.
- **Completed-row-masks-missing-blob:** on `enqueue_job` returning `joined && status==='completed'` while the current-version blob was absent, re-check the blob → present ⇒ `200 ready`, absent ⇒ `409 repair` — never `202` for a job that will not run.
- **Anon dig = 0 → 403**, read from `profiles.is_anonymous` (authoritative), distinct from registered quota-exhausted → 429. Registered dig quota is **5 per month** (`usage_counters` keyed by `date_trunc('month')`), not per day.
- **Summary-gate status codes** (reusing `loadSummaryForServe`): finalizing (`committed`) → 503; absent/not-promoted → 404; blob lost → 409. There is no 409 "not committed".
- **Handler and trigger resolve the summary key identically** (`artifacts.summaryMd.key ?? summaryMd`, validated by `assertCloudSummaryMdKey`) so they never key different blobs.
- **400-before-401 ordering:** backend gate + all input validation return 400 before auth returns 401.
- **Mocking boundaries:** Gemini at `lib/gemini`; YouTube/transcript at `lib/transcript-source`; integration tests mock at the route/worker seam only.
- **Local path untouched:** `lib/dig/dig-section.ts`, the in-memory `job-registry`, and the `stream`/`dig-state` routes are not modified. The cloud work is additive.

---

## File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `supabase/migrations/0018_enqueue_dig.sql` | Create | `create or replace enqueue_job` with the kind guard relaxed to admit `'dig'`. |
| `lib/dig/cloud/dig-blob-key.ts` | Create | `digSectionKey(base, sectionId)` + `digJobVersion()` — the shared key/version contract used by both the trigger (dedup) and the handler (write). Single-component `base` guard. |
| `lib/dig/cloud/resolve-summary-key.ts` | Create | `resolveSummaryMdKey(video)` — `artifacts.summaryMd.key ?? summaryMd`, validated; the single rule both trigger and handler use to derive `base` (prevents divergence). |
| `lib/dig/cloud/write-dig-section-blob.ts` | Create | Serialize one section to the per-section doc format and write via staged→promote. |
| `lib/job-queue/dig-handler.ts` | Create | `makeDigHandler(serviceClient): JobHandler` — text-only handler: version guard → summary-key resolve → generate → write. |
| `lib/job-queue/dispatch.ts` | Create | `makeJobHandler({summary, dig})` — pure kind→handler dispatcher. |
| `worker/main.ts` | Modify | Register both handlers via the dispatcher. |
| `lib/job-queue/enqueuer.ts` | Modify | Widen `Enqueuer.enqueue` payload to `IngestionPayload \| DigJobPayload`. |
| `lib/dig/cloud/enqueue-dig-core.ts` | Create | Authorize + gate + section-validate + dedup + preflight + enqueue; returns `{status, body}`. |
| `lib/http/client-ip.ts` | Create | Extract `parseClientIp` (shared by the jobs route and the dig route). |
| `app/api/jobs/route.ts` | Modify | Use the extracted `parseClientIp`. |
| `app/api/videos/[id]/dig/[sectionId]/route.ts` | Modify | Add the `STORAGE_BACKEND==='supabase'` cloud branch. |
| `tests/integration/dig-cloud.test.ts` | Create | Round-trip, owner isolation, no-charge-on-dedup + mutation control, concurrency, version-aware. |

---

### Task 1: Enqueue-dig migration

**Files:**
- Create: `supabase/migrations/0018_enqueue_dig.sql`
- Test: `tests/integration/enqueue-dig.test.ts`

**Interfaces:**
- Consumes: the current `enqueue_job(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet) returns table(job_id uuid, status text, joined boolean)` defined in `0011_cost_guardrails.sql`.
- Produces: the same function, now accepting `p_job_kind = 'dig'`. No signature change.

- [ ] **Step 1: Write the failing integration test**

`tests/integration/enqueue-dig.test.ts` — uses the real local Supabase via the service client. Mirror the setup in `tests/integration/summary-handler.test.ts` (`adminClient`, `newUser`, `seedPlaylist`, `ensureGuardrailHeadroom`). Note: `ensureGuardrailHeadroom` is exported from `./helpers/clients` (NOT a `./helpers/guardrails` module — that does not exist).

```ts
import { adminClient, newUser, anonSession, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

const admin = adminClient();

async function enqueueDigRpc(ownerId: string, playlistId: string, videoId: string, sectionId: number) {
  return admin.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: sectionId,
    p_job_kind: 'dig', p_job_version: 'dig-9', p_payload: { durationSeconds: 600 }, p_enqueue_ip: null,
  });
}

describe('enqueue_job admits dig', () => {
  beforeAll(async () => { await ensureGuardrailHeadroom(admin); });

  it('enqueues a dig job and debits the dig quota', async () => {
    const { user } = await newUser();
    const { playlistId } = await seedPlaylist(admin, user.id);
    const { data, error } = await enqueueDigRpc(user.id, playlistId, 'vid-dig-1', 132);
    expect(error).toBeNull();
    expect(data![0].status).toBe('queued');
    const { data: uc } = await admin.from('usage_counters').select('used')
      .eq('owner_id', user.id).eq('kind', 'dig').single();
    expect(uc!.used).toBe(1);
  });

  it('a second identical enqueue joins (idempotent, no double charge)', async () => {
    const { user } = await newUser();
    const { playlistId } = await seedPlaylist(admin, user.id);
    await enqueueDigRpc(user.id, playlistId, 'vid-dig-2', 132);
    const { data } = await enqueueDigRpc(user.id, playlistId, 'vid-dig-2', 132);
    expect(data![0].joined).toBe(true);
    const { data: uc } = await admin.from('usage_counters').select('used')
      .eq('owner_id', user.id).eq('kind', 'dig').single();
    expect(uc!.used).toBe(1); // still 1 — join did not re-charge
  });

  it('anonymous user (dig allowance 0) is rejected with quota_exceeded (PJ001)', async () => {
    // `profiles.is_anonymous` is immutable (profiles_is_anonymous_immutable trigger) — you CANNOT
    // update it. Create a genuine anonymous user via the anon sign-up path so provisioning sets it.
    const { userId: anonId } = await anonSession();
    const { data: prof } = await admin.from('profiles').select('is_anonymous').eq('id', anonId).single();
    expect(prof!.is_anonymous).toBe(true); // guard: prove we really have an anon before asserting the reject
    const { playlistId } = await seedPlaylist(admin, anonId);
    const { error } = await enqueueDigRpc(anonId, playlistId, 'vid-dig-3', 132);
    expect(error?.code).toBe('PJ001');
  });
});
```

- [ ] **Step 2: Run it — confirm failure**

Run: `npx jest tests/integration/enqueue-dig.test.ts`
Expected: FAIL — the first test errors with `unsupported_job_kind` (dig rejected by the current guard).

- [ ] **Step 3: Write the migration**

Read the **full** `enqueue_job` body in `supabase/migrations/0011_cost_guardrails.sql` and reproduce it verbatim inside a `create or replace function enqueue_job(...)` in the new migration, changing **only** the kind-guard line. Old line (0011):

```sql
if p_job_kind <> 'summary' then raise exception 'unsupported_job_kind'; end if;   -- dig rejected until 1E-b-2
```

New line:

```sql
if p_job_kind not in ('summary','dig') then raise exception 'unsupported_job_kind'; end if;
```

Migration header + tail:

```sql
-- 0018_enqueue_dig.sql
-- Admit job_kind='dig' in enqueue_job. The dig quota (quota_allowance dig rows),
-- dig_est_cents, and dig_max_attempts config, plus the section_id/job_kind/job_version
-- idempotency index (jobs_idem_active), already exist (0008 + 0011). This migration only
-- relaxes the one-line kind guard; the est/attempts dispatch (case p_job_kind ... 'dig' ...)
-- is already present in the 0011 body and is preserved verbatim.
create or replace function enqueue_job(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int,
  p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
  -- ... verbatim 0011 body, with ONLY the kind-guard line changed as above ...
$$;
revoke all on function enqueue_job(uuid, uuid, text, int, text, text, jsonb, inet) from public, anon, authenticated;
grant execute on function enqueue_job(uuid, uuid, text, int, text, text, jsonb, inet) to service_role;
```

**Verification step inside this task (do before Step 4):** confirm the live `jobs_idem_active` unique index columns match `enqueue_job`'s `ON CONFLICT` target. Run `grep -n "jobs_idem_active\|on conflict" supabase/migrations/*.sql`. Both are (verified in round-1 review) `(owner_id, playlist_id, video_id, section_id, job_kind, job_version)` with the partial predicate `where status in ('queued','active','completed')` — the `playlist_id` column was added by `0009_job_playlist_identity_and_worker_persistence.sql`. Reproduce the `ON CONFLICT` list **exactly** as it appears in the 0011 body; do not alter the column set. If your grep shows a different live set, stop and reconcile before proceeding.

- [ ] **Step 4: Apply the migration + run the test**

Run: `npx supabase db reset` (or the project's migration-apply command), then `npx jest tests/integration/enqueue-dig.test.ts`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0018_enqueue_dig.sql tests/integration/enqueue-dig.test.ts
git commit -m "feat(cloud-dig): admit job_kind=dig in enqueue_job (0018)"
```

---

### Task 2: Per-section blob key + writer

**Files:**
- Create: `lib/dig/cloud/dig-blob-key.ts`
- Create: `lib/dig/cloud/write-dig-section-blob.ts`
- Test: `tests/lib/dig/cloud/dig-blob-key.test.ts`, `tests/lib/dig/cloud/write-dig-section-blob.test.ts`

**Interfaces:**
- Consumes: `DIG_GENERATOR_VERSION` (exported from `lib/dig/generate.ts`), `assertLogicalKey` (`lib/storage/blob-store.ts`), `BlobStore`, `Principal`.
- Produces:
  - `digSectionKey(base: string, sectionId: number): string`
  - `digJobVersion(): string`
  - `writeDigSectionBlob(input: DigSectionBlobInput): Promise<string>` (returns the final key)

- [ ] **Step 1: Write the failing key tests**

`tests/lib/dig/cloud/dig-blob-key.test.ts`:

```ts
import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';

it('key shape: dig/{base}/{sectionId}.r{V}.md', () => {
  expect(digSectionKey('0007_intro', 132)).toBe(`dig/0007_intro/132.r${DIG_GENERATOR_VERSION}.md`);
});
it('job version encodes the dig generator version', () => {
  expect(digJobVersion()).toBe(`dig-${DIG_GENERATOR_VERSION}`);
});
it.each([['neg', -1], ['float', 1.5], ['nan', NaN]])('rejects a non-nonneg-int sectionId: %s', (_l, bad) => {
  expect(() => digSectionKey('b', bad as number)).toThrow(/invalid dig sectionId/);
});
it.each([['slash', 'a/b'], ['parent', '..'], ['nul', 'a\0b']])('rejects an unsafe base: %s', (_l, bad) => {
  expect(() => digSectionKey(bad, 1)).toThrow();
});
```

- [ ] **Step 2: Run — confirm failure**

Run: `npx jest dig-blob-key`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the key module**

`lib/dig/cloud/dig-blob-key.ts`:

```ts
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { assertLogicalKey } from '@/lib/storage/blob-store';

/** job_version for a cloud dig job — encodes DIG_GENERATOR_VERSION so a bump lands in a
 *  distinct jobs_idem_active slot (which includes job_version), permitting a legit re-enqueue. */
export function digJobVersion(): string {
  return `dig-${DIG_GENERATOR_VERSION}`;
}

/** Per-section dig blob key. One blob per section ⇒ concurrent digs of different sections
 *  never write the same object (no lost update). The `.r{V}` segment makes a version bump
 *  produce a fresh key, so a stale-version blob is simply absent at the current key. */
export function digSectionKey(base: string, sectionId: number): string {
  if (!Number.isInteger(sectionId) || sectionId < 0) {
    throw Object.assign(new Error(`invalid dig sectionId: ${sectionId}`), { statusCode: 400 });
  }
  // `base` MUST be a single path component. assertLogicalKey does NOT reject an interior '/', so
  // `dig/a/b/1.r9.md` would slip past it — guard the base explicitly here.
  if (base.length === 0 || /[/\\\0]/.test(base) || base === '.' || base === '..') {
    throw Object.assign(new Error(`invalid dig base: ${base}`), { statusCode: 400 });
  }
  const key = `dig/${base}/${sectionId}.r${DIG_GENERATOR_VERSION}.md`;
  assertLogicalKey(key); // belt-and-suspenders: leading '/', '..' segment, '\0'
  return key;
}
```

- [ ] **Step 4: Run key tests — confirm pass**

Run: `npx jest dig-blob-key`
Expected: PASS.

- [ ] **Step 5: Write the failing writer test**

`tests/lib/dig/cloud/write-dig-section-blob.test.ts`:

```ts
import { writeDigSectionBlob } from '@/lib/dig/cloud/write-dig-section-blob';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import type { StagedRef } from '@/lib/storage/blob-store';

function fakeBlobStore() {
  const calls: string[] = [];
  const staged = new Map<string, Buffer>();
  return {
    calls,
    put: jest.fn(),
    get: jest.fn(),
    delete: jest.fn(),
    exists: jest.fn(async (_p: unknown, k: string) => { calls.push(`exists:${k}`); return staged.has(k); }),
    putStaged: jest.fn(async (principal: unknown, key: string, bytes: Buffer): Promise<StagedRef> => {
      const tempKey = `${key}.staging`; staged.set(tempKey, bytes); calls.push(`putStaged:${key}`);
      return { principal: principal as any, tempKey, finalKey: key };
    }),
    promote: jest.fn(async (ref: StagedRef) => { calls.push(`promote:${ref.finalKey}`); }),
  };
}

const principal = { id: 'u1', indexKey: 'PLxyz' };

it('writes the per-section doc via staged→promote and returns the key', async () => {
  const bs = fakeBlobStore();
  const key = await writeDigSectionBlob({
    blobStore: bs as any, principal, base: '0007_intro', videoId: 'vid1', sectionId: 132,
    startSec: 132, title: 'Encoder attention', language: 'en',
    sourceVideoUrl: 'https://youtu.be/vid1?t=132',
    bodyMarkdown: 'Prose. [[SLIDE:2:12|2:20|heat-map]] More prose.\n', generatedAt: '2026-07-12T18:04:11.522Z',
  });
  expect(key).toBe(`dig/0007_intro/132.r${DIG_GENERATOR_VERSION}.md`);
  // staged before promote, and exists() verified the staged blob between them
  expect(bs.calls).toEqual([
    `putStaged:${key}`, `exists:${key}.staging`, `promote:${key}`,
  ]);
  const written = (bs.putStaged.mock.calls[0][2] as Buffer).toString('utf-8');
  expect(written).toContain('slides: []');
  expect(written).toContain(`genVersion: ${DIG_GENERATOR_VERSION}`);
  expect(written).toContain('sectionId: 132');
  expect(written).toContain('[[SLIDE:2:12|2:20|heat-map]]'); // token preserved verbatim, NOT resolved/stripped
});

it('throws if the staged upload cannot be verified (no promote)', async () => {
  const bs = fakeBlobStore();
  bs.exists = jest.fn(async () => false);
  await expect(writeDigSectionBlob({
    blobStore: bs as any, principal, base: 'b', videoId: 'v', sectionId: 1, startSec: 1,
    title: 't', language: 'en', sourceVideoUrl: 'u', bodyMarkdown: 'x', generatedAt: 'now',
  })).rejects.toThrow(/staged dig upload not verified/);
  expect(bs.promote).not.toHaveBeenCalled();
});
```

- [ ] **Step 6: Run — confirm failure**

Run: `npx jest write-dig-section-blob`
Expected: FAIL — module not found.

- [ ] **Step 7: Implement the writer**

`lib/dig/cloud/write-dig-section-blob.ts`:

```ts
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { digSectionKey } from '@/lib/dig/cloud/dig-blob-key';

export interface DigSectionBlobInput {
  blobStore: BlobStore;
  principal: Principal;
  base: string;
  videoId: string;
  sectionId: number;
  startSec: number;
  title: string;
  language: 'en' | 'ko';
  sourceVideoUrl: string;
  bodyMarkdown: string; // generateDig output after resolveTranscriptTokens; slide tokens PRESERVED
  generatedAt: string;  // ISO-8601
}

/** YAML double-quoted scalar — safe for titles/URLs containing ':' or quotes. */
function yamlScalar(s: string): string {
  return `"${s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

/** Serialize one dug section as a self-describing per-section doc and write it via staged→promote.
 *  `slides: []` and inline unresolved [[SLIDE:...]] tokens — the text-only slice defers slide
 *  resolution losslessly to a later slice. */
export async function writeDigSectionBlob(input: DigSectionBlobInput): Promise<string> {
  const frontmatter = [
    '---',
    `videoId: ${yamlScalar(input.videoId)}`,
    `sectionId: ${input.sectionId}`,
    `startSec: ${input.startSec}`,
    `title: ${yamlScalar(input.title)}`,
    `language: ${input.language}`,
    `sourceVideoUrl: ${yamlScalar(input.sourceVideoUrl)}`,
    `generatedAt: ${yamlScalar(input.generatedAt)}`,
    `genVersion: ${DIG_GENERATOR_VERSION}`,
    'slides: []',
    '---',
    '',
  ].join('\n');
  const doc = `${frontmatter}${input.bodyMarkdown.trimEnd()}\n`;

  const key = digSectionKey(input.base, input.sectionId);
  const ref = await input.blobStore.putStaged(input.principal, key, Buffer.from(doc, 'utf-8'), 'text/markdown');
  if (!(await input.blobStore.exists(input.principal, ref.tempKey))) {
    throw new Error('staged dig upload not verified');
  }
  await input.blobStore.promote(ref);
  return key;
}
```

- [ ] **Step 8: Run writer tests — confirm pass**

Run: `npx jest write-dig-section-blob`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add lib/dig/cloud/dig-blob-key.ts lib/dig/cloud/write-dig-section-blob.ts tests/lib/dig/cloud/
git commit -m "feat(cloud-dig): per-section blob key + staged→promote writer (text-only, tokens preserved)"
```

---

### Task 3: Dig worker handler

**Files:**
- Create: `lib/dig/cloud/resolve-summary-key.ts`
- Create: `lib/job-queue/dig-handler.ts`
- Test: `tests/lib/dig/cloud/resolve-summary-key.test.ts`, `tests/lib/job-queue/dig-handler.test.ts`

**Interfaces:**
- Consumes: `JobHandler`, `HandlerCtx` (`lib/job-queue/handler-context.ts`); `LeasedJob` (`lib/storage/job-queue.ts`); `getWorkerStorageBundle` (`lib/storage/resolve.ts` → `{blobStore, principal}`); `readVideo(client, playlistId, videoId): Promise<Video|null>` (`lib/storage/worker-persistence.ts` — return retains the raw `artifacts` jsonb, accessed via cast as `summary-handler.ts:85` does); `parseSummaryMarkdown` (`lib/html-doc/parse.ts`); `resolveTranscriptSegments` (`lib/transcript-source.ts`); `PermanentTranscriptError` (`lib/transcript-source-errors.ts`); `windowForSection` (`lib/dig/section-window.ts`); `generateDig` (`lib/dig/generate.ts`); `resolveTranscriptTokens` (`lib/transcript-timestamps.ts`); `writeDigSectionBlob`, `digJobVersion` (Task 2); `assertCloudSummaryMdKey` (`lib/html-doc/assert-cloud-summary-md-key.ts`); `NonRetryableError` (`lib/job-queue/errors.ts`).
- Produces: `resolveSummaryMdKey(video): string | null`; `makeDigHandler(serviceClient: SupabaseClient): JobHandler`.

- [ ] **Step 1: Write the failing test**

`tests/lib/job-queue/dig-handler.test.ts` — mock the storage + gemini + transcript boundaries; assert the handler reads the section, generates, and writes the per-section blob with tokens preserved.

```ts
jest.mock('@/lib/storage/resolve', () => ({ getWorkerStorageBundle: jest.fn() }));
jest.mock('@/lib/storage/worker-persistence', () => ({ readVideo: jest.fn() }));
jest.mock('@/lib/transcript-source', () => ({ resolveTranscriptSegments: jest.fn() }));
jest.mock('@/lib/dig/generate', () => ({
  ...jest.requireActual('@/lib/dig/generate'),
  generateDig: jest.fn(),
}));

import { makeDigHandler } from '@/lib/job-queue/dig-handler';
import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { readVideo } from '@/lib/storage/worker-persistence';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
import { generateDig, DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import { NonRetryableError } from '@/lib/job-queue/errors';

const put = new Map<string, Buffer>();
const blobStore = {
  put: jest.fn(), get: jest.fn(), delete: jest.fn(),
  exists: jest.fn(async (_p: unknown, k: string) => put.has(k)),
  putStaged: jest.fn(async (p: unknown, key: string, bytes: Buffer) => { put.set(`${key}.staging`, bytes); return { principal: p, tempKey: `${key}.staging`, finalKey: key }; }),
  promote: jest.fn(async (ref: any) => { put.set(ref.finalKey, put.get(ref.tempKey)!); }),
};
const principal = { id: 'owner1', indexKey: 'PLk' };
const ctx = { isCancelled: async () => false, signal: new AbortController().signal, setPhase: jest.fn(async () => {}) };
const job = { id: 'j1', ownerId: 'owner1', playlistId: 'pl-uuid', videoId: 'vid1', sectionId: 132, kind: 'dig', version: `dig-${DIG_GENERATOR_VERSION}`, payload: { durationSeconds: 600 }, attempts: 0, leaseToken: 'lt' };

// Real summary-section format: a `▶ [M:SS–M:SS](url?t=<sec>s)` line (en-dash range, trailing `s`).
// parseSummaryMarkdown is NOT mocked, so fixtures MUST parse — see lib/html-doc/parse.ts:16,23,32.
const SUMMARY_MD = `# Title

## 1. Intro
▶ [0:00–2:12](https://youtu.be/vid1?t=0s)
Intro prose.

## 2. Encoder
▶ [2:12–2:20](https://youtu.be/vid1?t=132s)
Encoder prose.
`;

beforeEach(() => {
  put.clear();
  (getWorkerStorageBundle as jest.Mock).mockResolvedValue({ blobStore, principal, ownerId: 'owner1', playlistId: 'pl-uuid' });
  // artifacts.summaryMd.key is the authoritative key (top-level summaryMd is a fallback) — the handler
  // must resolve base the SAME way loadSummaryForServe does (H1).
  (readVideo as jest.Mock).mockResolvedValue({ id: 'vid1', title: 'Vid One', youtubeUrl: 'https://youtu.be/vid1', language: 'en', durationSeconds: 600, summaryMd: '0007_intro.md', artifacts: { summaryMd: { key: '0007_intro.md', status: 'promoted' } } });
  blobStore.get.mockResolvedValue(Buffer.from(SUMMARY_MD, 'utf-8'));
  (resolveTranscriptSegments as jest.Mock).mockResolvedValue({ segments: [{ text: 'hi', offset: 132, duration: 5 }], source: 'captions' });
  (generateDig as jest.Mock).mockResolvedValue('Dig prose. [[SLIDE:2:12|2:20|cap]] End.');
});

it('generates the section dig and writes the per-section blob with tokens preserved', async () => {
  await makeDigHandler({} as any)(job as any, ctx as any);
  const key = digSectionKey('0007_intro', 132);
  expect(put.has(key)).toBe(true);
  const body = put.get(key)!.toString('utf-8');
  expect(body).toContain('sectionId: 132');
  expect(body).toContain('slides: []');
  expect(body).toContain('[[SLIDE:2:12|2:20|cap]]'); // preserved, NOT resolved
  expect(ctx.setPhase).toHaveBeenCalledWith('transcribing');
  expect(ctx.setPhase).toHaveBeenCalledWith('writing');
});

it('throws NonRetryableError when the section is not in the summary', async () => {
  const badJob = { ...job, sectionId: 999 };
  await expect(makeDigHandler({} as any)(badJob as any, ctx as any)).rejects.toBeInstanceOf(NonRetryableError);
});

it('a real PermanentTranscriptError is rethrown as NonRetryableError (so the runner does not retry/re-charge)', async () => {
  const { PermanentTranscriptError } = jest.requireActual('@/lib/transcript-source-errors');
  (resolveTranscriptSegments as jest.Mock).mockRejectedValue(new PermanentTranscriptError('no transcript'));
  const err = await makeDigHandler({} as any)(job as any, ctx as any).catch((e) => e);
  expect(err).toBeInstanceOf(NonRetryableError); // NOT the raw PermanentTranscriptError (worker-runner.ts:64 only treats NonRetryableError as non-retryable)
  expect(blobStore.promote).not.toHaveBeenCalled();
});

it('rejects a stale-version job (job.version != current) as NonRetryableError, no generation', async () => {
  const staleJob = { ...job, version: 'dig-0' };
  await expect(makeDigHandler({} as any)(staleJob as any, ctx as any)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateDig as jest.Mock).not.toHaveBeenCalled();
  expect(blobStore.promote).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run — confirm failure**

Run: `npx jest dig-handler`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the handler**

`lib/job-queue/dig-handler.ts`. For the transcript caps: read `lib/job-queue/summary-handler.ts` and reuse the identical `CLOUD_CAPS` — if it is exported, import it; otherwise replicate its exact construction from `lib/gemini-cost` in this module. Pass `{ signal: ctx.signal, caps }` to `resolveTranscriptSegments`, matching the summary path.

```ts
import type { SupabaseClient } from '@supabase/supabase-js';
import type { JobHandler } from '@/lib/job-queue/handler-context';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { PermanentTranscriptError } from '@/lib/transcript-source-errors';
import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { readVideo } from '@/lib/storage/worker-persistence';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
import { windowForSection } from '@/lib/dig/section-window';
import { generateDig } from '@/lib/dig/generate';
import { resolveTranscriptTokens } from '@/lib/transcript-timestamps';
import { resolveSummaryMdKey } from '@/lib/dig/cloud/resolve-summary-key';
import { digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import { writeDigSectionBlob } from '@/lib/dig/cloud/write-dig-section-blob';
// CLOUD_CAPS: reuse summary-handler's caps (see Step 3 note — import if exported, else replicate).

export function makeDigHandler(serviceClient: SupabaseClient): JobHandler {
  return async (job, ctx) => {
    if (job.kind !== 'dig') throw new NonRetryableError(`dig handler received kind=${job.kind}`);
    // Version guard (mirror summary-handler.ts:74-76): a job charged under a different
    // DIG_GENERATOR_VERSION must NOT write a current-version blob it never paid for.
    if (job.version !== digJobVersion()) {
      throw new NonRetryableError(`dig job version ${job.version} != worker ${digJobVersion()}`);
    }
    const sectionId = job.sectionId;

    const video = await readVideo(serviceClient, job.playlistId, job.videoId);
    if (!video) throw new NonRetryableError('video not found');
    // SAME summary-key rule as the trigger's loadSummaryForServe (artifacts.summaryMd.key ??
    // summaryMd, validated) — guarantees the handler writes the exact base the trigger deduped on.
    const mdKey = resolveSummaryMdKey(video);
    if (!mdKey) throw new NonRetryableError('summary not available for dig');
    const base = mdKey.replace(/\.md$/, '');

    const bundle = await getWorkerStorageBundle(serviceClient, job.ownerId, job.playlistId);

    const mdBytes = await bundle.blobStore.get(bundle.principal, mdKey);
    if (!mdBytes) throw new NonRetryableError('summary blob missing');
    const parsed = parseSummaryMarkdown(mdBytes.toString('utf-8'));
    const section = parsed.sections.find((s) => s.timeRange?.startSec === sectionId);
    if (!section) throw new NonRetryableError(`section ${sectionId} not found`);

    await ctx.setPhase('transcribing');
    let segments;
    try {
      ({ segments } = await resolveTranscriptSegments(
        job.videoId, video.youtubeUrl, video.durationSeconds, { signal: ctx.signal, caps: CLOUD_CAPS },
      ));
    } catch (e) {
      // A permanent no-transcript is provably non-retryable — map it so the runner fails immediately
      // instead of retrying (and re-charging Gemini). Mirrors summary-handler.ts:126-136.
      if (e instanceof PermanentTranscriptError) {
        throw new NonRetryableError(`transcript permanently unavailable for ${job.videoId}: ${e.message}`);
      }
      throw e; // transient / AbortError → let the runner classify + retry
    }

    const window = windowForSection(section, parsed.sections, segments, video.durationSeconds);
    if (!window) throw new NonRetryableError(`section ${sectionId} has no timeRange`);

    await ctx.setPhase('summarizing');
    const raw = await generateDig(window, job.videoId, video.language);
    const withTs = resolveTranscriptTokens(raw, segments, job.videoId, video.durationSeconds);
    // resolveSlideTokens intentionally SKIPPED — text-only slice; [[SLIDE:...]] tokens preserved verbatim.

    if (ctx.signal.aborted) throw new DOMException('worker signal aborted before dig write', 'AbortError');
    await ctx.setPhase('writing');
    const key = await writeDigSectionBlob({
      blobStore: bundle.blobStore, principal: bundle.principal, base,
      videoId: job.videoId, sectionId, startSec: window.startSec,
      title: section.title, language: video.language,
      sourceVideoUrl: video.youtubeUrl, bodyMarkdown: withTs,
      generatedAt: new Date().toISOString(),
    });
    return { key };
  };
}
```

**Also create `lib/dig/cloud/resolve-summary-key.ts`** (the single summary-key rule, so the handler and trigger can never diverge — H1):

```ts
import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';

/** The authoritative summary md key for a video: the artifact record's key, falling back to the
 *  top-level `summaryMd` — the EXACT rule loadSummaryForServe uses (serve-summary-core.ts:56).
 *  Returns null when absent or when the key fails the single-component guard. */
export function resolveSummaryMdKey(video: unknown): string | null {
  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
  if (!key) return null;
  try { assertCloudSummaryMdKey(key); } catch { return null; }
  return key;
}
```

Add a focused test `tests/lib/dig/cloud/resolve-summary-key.test.ts`: prefers `artifacts.summaryMd.key` over top-level `summaryMd`; falls back to `summaryMd` when the artifact key is absent; returns `null` for a missing key and for a corrupt (`nested/foo.md`) key.

- [ ] **Step 4: Run — confirm pass**

Run: `npx jest dig-handler resolve-summary-key`
Expected: PASS (handler happy path + section-missing + real-PermanentTranscriptError→NonRetryableError + stale-version guard; helper prefers artifact key, falls back, rejects corrupt/absent).

- [ ] **Step 5: Commit**

```bash
git add lib/dig/cloud/resolve-summary-key.ts lib/job-queue/dig-handler.ts tests/lib/dig/cloud/resolve-summary-key.test.ts tests/lib/job-queue/dig-handler.test.ts
git commit -m "feat(cloud-dig): makeDigHandler — version guard, shared summary-key, transcript-error wrap, text-only write"
```

---

### Task 4: Worker kind→handler dispatch

**Files:**
- Create: `lib/job-queue/dispatch.ts`
- Modify: `worker/main.ts`
- Test: `tests/lib/job-queue/dispatch.test.ts`

**Interfaces:**
- Consumes: `JobHandler` (`lib/job-queue/handler-context.ts`), `NonRetryableError`.
- Produces: `makeJobHandler(handlers: { summary: JobHandler; dig: JobHandler }): JobHandler`.

- [ ] **Step 1: Write the failing test**

`tests/lib/job-queue/dispatch.test.ts`:

```ts
import { makeJobHandler } from '@/lib/job-queue/dispatch';

const ctx = { isCancelled: async () => false, signal: new AbortController().signal, setPhase: async () => {} };
const mkJob = (kind: string) => ({ id: 'j', ownerId: 'o', playlistId: 'p', videoId: 'v', sectionId: -1, kind, version: 'x', payload: {}, attempts: 0, leaseToken: 't' });

it('routes by job.kind', async () => {
  const summary = jest.fn(async () => 'S');
  const dig = jest.fn(async () => 'D');
  const h = makeJobHandler({ summary, dig });
  expect(await h(mkJob('summary') as any, ctx as any)).toBe('S');
  expect(await h(mkJob('dig') as any, ctx as any)).toBe('D');
  expect(summary).toHaveBeenCalledTimes(1);
  expect(dig).toHaveBeenCalledTimes(1);
});

it('throws NonRetryableError for an unknown kind', async () => {
  const h = makeJobHandler({ summary: jest.fn(), dig: jest.fn() });
  await expect(h(mkJob('bogus') as any, ctx as any)).rejects.toThrow(/no handler for kind/);
});
```

- [ ] **Step 2: Run — confirm failure**

Run: `npx jest dispatch`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the dispatcher**

`lib/job-queue/dispatch.ts`:

```ts
import type { JobHandler } from '@/lib/job-queue/handler-context';
import type { JobKind } from '@/lib/storage/job-queue';
import { NonRetryableError } from '@/lib/job-queue/errors';

/** Pure kind→handler dispatch. A single JobHandler the worker loop can register, that fans
 *  a leased job to the right handler by kind. Unknown kinds are non-retryable (bad data, not
 *  a transient failure) so the runner dead-letters instead of looping. */
export function makeJobHandler(handlers: Record<JobKind, JobHandler>): JobHandler {
  return (job, ctx) => {
    const h = handlers[job.kind];
    if (!h) throw new NonRetryableError(`no handler for kind ${job.kind}`);
    return h(job, ctx);
  };
}
```

- [ ] **Step 4: Run — confirm pass**

Run: `npx jest dispatch`
Expected: PASS.

- [ ] **Step 5: Wire it into the worker**

In `worker/main.ts`, replace the single-handler construction:

```ts
// before:
// const handler = makeSummaryHandler(client);
// after:
import { makeDigHandler } from '@/lib/job-queue/dig-handler';
import { makeJobHandler } from '@/lib/job-queue/dispatch';
...
const handler = makeJobHandler({
  summary: makeSummaryHandler(client),
  dig: makeDigHandler(client),
});
```

Leave `runWorkerLoop({ queue, handler, ... })` unchanged.

- [ ] **Step 6: Run the worker + job-queue suites — confirm no summary regression**

Run: `npx jest dispatch summary-handler job-queue worker`
Expected: PASS (summary path unchanged).

- [ ] **Step 7: Commit**

```bash
git add lib/job-queue/dispatch.ts worker/main.ts tests/lib/job-queue/dispatch.test.ts
git commit -m "feat(cloud-dig): worker kind→handler dispatch (summary + dig)"
```

---

### Task 5: Enqueue-dig core

**Files:**
- Modify: `lib/job-queue/enqueuer.ts` (widen `enqueue` payload type)
- Create: `lib/dig/cloud/enqueue-dig-core.ts`
- Test: `tests/lib/dig/cloud/enqueue-dig-core.test.ts`

**Interfaces:**
- Consumes: `loadSummaryForServe` (`lib/html-doc/serve-summary-core.ts`) → `{ ok, mdBytes, base, principal, bundle, video, ... } | { ok:false, status, error }`; `parseSummaryMarkdown`; `digSectionKey`, `digJobVersion` (Task 2); `Enqueuer` (`lib/job-queue/enqueuer.ts`); `QuotaExceededError`, `DailyCapError`, `VideoTooLongError` (`lib/job-queue/errors.ts`).
- Produces:
  - `DigJobPayload = { durationSeconds: number }`
  - `enqueueDig(deps: EnqueueDigDeps): Promise<{ status: number; body: Record<string, unknown> }>`

- [ ] **Step 1: Widen the enqueuer payload type**

In `lib/job-queue/enqueuer.ts`, add a dig payload type and widen `Enqueuer.enqueue`:

```ts
export interface DigJobPayload { durationSeconds: number; } // enqueue_job reads only durationSeconds (PJ003 backstop)

export interface Enqueuer {
  enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload | DigJobPayload): Promise<EnqueueResult>;
  preflight(ip: string | null, ownerId: string): Promise<PreflightVerdict>;
  getGuardrailConfig(): Promise<GuardrailConfigView>;
}
```

`SupabaseEnqueuer.enqueue`'s body is unchanged (it passes `payload` straight through as jsonb). Update its method signature's `payload` param type to `IngestionPayload | DigJobPayload` to match the interface.

- [ ] **Step 2: Write the failing core tests**

`tests/lib/dig/cloud/enqueue-dig-core.test.ts` — mock `loadSummaryForServe`; supply a fake enqueuer + a fake blobStore/bundle. Cover every branch.

```ts
jest.mock('@/lib/html-doc/serve-summary-core', () => ({ loadSummaryForServe: jest.fn() }));
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { QuotaExceededError, DailyCapError, VideoTooLongError } from '@/lib/job-queue/errors';
import { digSectionKey } from '@/lib/dig/cloud/dig-blob-key';

const SUMMARY_MD = `# T

## 2. Encoder
▶ [2:12–2:20](https://youtu.be/vid1?t=132s)
Prose.
`;
const okLoad = (existsResult: boolean, existsFn?: jest.Mock) => ({
  ok: true, mdBytes: Buffer.from(SUMMARY_MD, 'utf-8'), base: '0007_intro',
  principal: { id: 'u1', indexKey: 'PLk' },
  bundle: { blobStore: { exists: existsFn ?? jest.fn(async () => existsResult) } },
  video: { id: 'vid1', durationSeconds: 600, youtubeUrl: 'https://youtu.be/vid1', title: 'T', language: 'en' },
  playlistId: 'pl', mdKey: '0007_intro.md',
});
const enqueuer = {
  preflight: jest.fn(async () => ({ admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false })),
  enqueue: jest.fn(async () => ({ jobId: 'job1', status: 'queued', joined: false })),
  getGuardrailConfig: jest.fn(),
};
const base = { supabase: {} as any, enqueuer: enqueuer as any, userId: 'u1', isAnonymous: false, videoId: 'vid1', playlistId: 'pl', sectionId: 132, enqueueIp: null };
beforeEach(() => jest.clearAllMocks());

it('202 enqueued when absent (charges once)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  const r = await enqueueDig(base);
  expect(r.status).toBe(202);
  expect(r.body).toEqual({ status: 'enqueued', jobId: 'job1', sectionId: 132 });
  expect(enqueuer.enqueue).toHaveBeenCalledWith(
    { ownerId: 'u1', enqueueIp: null },
    expect.objectContaining({ kind: 'dig', sectionId: 132, version: expect.stringMatching(/^dig-/) }),
    { durationSeconds: 600 },
  );
});
it('200 ready when the current-version blob exists (no enqueue, no charge)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(true));
  const r = await enqueueDig(base);
  expect(r.status).toBe(200);
  expect(r.body).toEqual({ status: 'ready', sectionId: 132 });
  expect(enqueuer.enqueue).not.toHaveBeenCalled();
});
it('403 for an anonymous user (never reads/enqueues)', async () => {
  const r = await enqueueDig({ ...base, isAnonymous: true });
  expect(r.status).toBe(403);
  expect(loadSummaryForServe).not.toHaveBeenCalled();
});
it('propagates loadSummaryForServe failure status (404/503/409)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue({ ok: false, status: 404, error: 'not found' });
  expect((await enqueueDig(base)).status).toBe(404);
});
it('404 when the section is not in the summary', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  expect((await enqueueDig({ ...base, sectionId: 999 })).status).toBe(404);
});
it('maps guardrail errors: quota→429, cap→503, too_long→400', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  enqueuer.enqueue.mockRejectedValueOnce(new QuotaExceededError());
  expect((await enqueueDig(base)).status).toBe(429);
  enqueuer.enqueue.mockRejectedValueOnce(new DailyCapError());
  expect((await enqueueDig(base)).status).toBe(503);
  enqueuer.enqueue.mockRejectedValueOnce(new VideoTooLongError());
  expect((await enqueueDig(base)).status).toBe(400);
});
it('maps preflight verdicts: velocity→429, capacity→503, !admitted→403', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  enqueuer.preflight.mockResolvedValueOnce({ admitted: true, atCapacity: false, velocityExceeded: true, challengeRequired: false });
  expect((await enqueueDig(base)).status).toBe(429);
  enqueuer.preflight.mockResolvedValueOnce({ admitted: true, atCapacity: true, velocityExceeded: false, challengeRequired: false });
  expect((await enqueueDig(base)).status).toBe(503);
  enqueuer.preflight.mockResolvedValueOnce({ admitted: false, atCapacity: false, velocityExceeded: false, challengeRequired: false });
  expect((await enqueueDig(base)).status).toBe(403);
});
it('joined a COMPLETED row but the blob is still absent → 409 repair, NOT 202 (§9.2)', async () => {
  const exists = jest.fn(async () => false); // absent at dedup AND at the post-enqueue re-check
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false, exists));
  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jc', status: 'completed', joined: true });
  const r = await enqueueDig(base);
  expect(r.status).toBe(409);
  expect(exists).toHaveBeenCalledTimes(2); // dedup + re-check
});
it('joined a COMPLETED row and the blob is now present (concurrent promote) → 200 ready', async () => {
  let calls = 0;
  const exists = jest.fn(async () => (calls++ === 0 ? false : true)); // miss at dedup, hit on re-check
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false, exists));
  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jc', status: 'completed', joined: true });
  const r = await enqueueDig(base);
  expect(r.status).toBe(200);
  expect(r.body).toEqual({ status: 'ready', sectionId: 132 });
});
it('joined a live queued/active row → 202 (normal in-flight join, no re-check needed)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jq', status: 'queued', joined: true });
  expect((await enqueueDig(base)).status).toBe(202);
});
```

- [ ] **Step 3: Run — confirm failure**

Run: `npx jest enqueue-dig-core`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement the core**

`lib/dig/cloud/enqueue-dig-core.ts`:

```ts
import type { SupabaseClient } from '@supabase/supabase-js';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import type { Enqueuer } from '@/lib/job-queue/enqueuer';
import { QuotaExceededError, DailyCapError, VideoTooLongError } from '@/lib/job-queue/errors';

export interface EnqueueDigDeps {
  supabase: SupabaseClient;   // session client — auth + tenant reads (RLS)
  enqueuer: Enqueuer;         // service-role — enqueue RPC only
  userId: string;
  isAnonymous: boolean;
  videoId: string;
  playlistId: string;
  sectionId: number;
  enqueueIp: string | null;
}

export interface EnqueueDigResult { status: number; body: Record<string, unknown>; }

/** Cloud dig trigger core: authorize + gate (via loadSummaryForServe, which does NOT charge a
 *  magazine model), validate the section, dedup on the current-version blob, preflight, enqueue.
 *  Charge happens once, inside enqueue_job, only on a fresh enqueue. */
export async function enqueueDig(deps: EnqueueDigDeps): Promise<EnqueueDigResult> {
  // Anon dig allowance is 0 → 403, distinct from a registered user's quota-exhausted 429.
  if (deps.isAnonymous) return { status: 403, body: { error: 'dig requires an account' } };

  const load = await loadSummaryForServe(deps.supabase, {
    videoId: deps.videoId, playlistId: deps.playlistId, userId: deps.userId,
  });
  if (!load.ok) return { status: load.status, body: { error: load.error } };

  const parsed = parseSummaryMarkdown(load.mdBytes.toString('utf-8'));
  const section = parsed.sections.find((s) => s.timeRange?.startSec === deps.sectionId);
  if (!section) return { status: 404, body: { error: 'section not found' } };

  // Dedup authority = the current-version blob. Present → done, no enqueue, no charge.
  const key = digSectionKey(load.base, deps.sectionId);
  if (await load.bundle.blobStore.exists(load.principal, key)) {
    return { status: 200, body: { status: 'ready', sectionId: deps.sectionId } };
  }

  const verdict = await deps.enqueuer.preflight(deps.enqueueIp, deps.userId);
  if (verdict.velocityExceeded) return { status: 429, body: { error: 'rate limited' } };
  if (verdict.atCapacity) return { status: 503, body: { error: 'at capacity' } };
  if (!verdict.admitted) return { status: 403, body: { error: 'forbidden' } };

  try {
    const res = await deps.enqueuer.enqueue(
      { ownerId: deps.userId, enqueueIp: deps.enqueueIp },
      { playlistId: deps.playlistId, videoId: deps.videoId, sectionId: deps.sectionId, kind: 'dig', version: digJobVersion() },
      { durationSeconds: load.video.durationSeconds },
    );
    // §9.2: the idempotency index includes 'completed'. If we joined a completed row while the
    // current-version blob was absent above, do NOT promise a job that will never run. Re-check the
    // blob: a concurrent worker may have just promoted it (→ ready), else the blob was lost (→ repair).
    if (res.joined && res.status === 'completed') {
      if (await load.bundle.blobStore.exists(load.principal, key)) {
        return { status: 200, body: { status: 'ready', sectionId: deps.sectionId } };
      }
      return { status: 409, body: { error: 'repair needed', sectionId: deps.sectionId } };
    }
    return { status: 202, body: { status: 'enqueued', jobId: res.jobId, sectionId: deps.sectionId } };
  } catch (e) {
    if (e instanceof QuotaExceededError) return { status: 429, body: { error: 'quota exceeded' } };
    if (e instanceof DailyCapError) return { status: 503, body: { error: 'at capacity' } };
    if (e instanceof VideoTooLongError) return { status: 400, body: { error: 'video too long' } };
    throw e;
  }
}
```

- [ ] **Step 5: Run — confirm pass + no enqueuer regression**

Run: `npx jest enqueue-dig-core enqueuer`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/job-queue/enqueuer.ts lib/dig/cloud/enqueue-dig-core.ts tests/lib/dig/cloud/enqueue-dig-core.test.ts
git commit -m "feat(cloud-dig): enqueue-dig core (authorize→dedup→preflight→charge-once)"
```

---

### Task 6: Cloud dig trigger route branch

**Files:**
- Create: `lib/http/client-ip.ts`
- Modify: `app/api/jobs/route.ts` (use the extracted helper)
- Modify: `app/api/videos/[id]/dig/[sectionId]/route.ts`
- Test: `tests/app/api/videos/dig-cloud-route.test.ts`

**Interfaces:**
- Consumes: `createServerSupabase` (`lib/supabase/server`), `createServiceClient` (`lib/supabase/service`), `SupabaseEnqueuer` (`lib/job-queue/enqueuer`), `assertVideoId` (existing import in the route), `enqueueDig` (Task 5).
- Produces: `parseClientIp(req: Request): string | null`; a `STORAGE_BACKEND==='supabase'` branch on `POST`.

- [ ] **Step 1: Extract `parseClientIp`**

`lib/http/client-ip.ts` — move the exact function from `app/api/jobs/route.ts` (verbatim), then import it in both routes.

```ts
/** `Fly-Client-IP` is set by Fly.io's edge and cannot be spoofed past the proxy; XFF's first
 *  hop is the original client when present. Prefer Fly's header, fall back to XFF[0]. */
export function parseClientIp(req: Request): string | null {
  const fly = req.headers.get('fly-client-ip');
  if (fly) return fly;
  const xff = req.headers.get('x-forwarded-for');
  if (xff) { const first = xff.split(',')[0]?.trim(); if (first) return first; }
  return null;
}
```

In `app/api/jobs/route.ts`, delete the local `parseClientIp` and `import { parseClientIp } from '@/lib/http/client-ip';`.

- [ ] **Step 2: Write the failing route test**

`tests/app/api/videos/dig-cloud-route.test.ts` — mock `next/headers`, `@/lib/supabase/server`, `@/lib/supabase/service`, `@/lib/job-queue/enqueuer` (SupabaseEnqueuer), and `@/lib/dig/cloud/enqueue-dig-core` (assert the route wires params → enqueueDig and serializes `{status, body}`). Set `STORAGE_BACKEND='supabase'` in `beforeAll`.

```ts
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({})) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn() }));
jest.mock('@/lib/supabase/service', () => ({ createServiceClient: jest.fn(() => ({})) }));
jest.mock('@/lib/job-queue/enqueuer', () => ({ SupabaseEnqueuer: jest.fn(() => ({})) }));
jest.mock('@/lib/dig/cloud/enqueue-dig-core', () => ({ enqueueDig: jest.fn() }));

import { POST } from '@/app/api/videos/[id]/dig/[sectionId]/route';
import { createServerSupabase } from '@/lib/supabase/server';
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';

const UUID = '11111111-1111-1111-1111-111111111111';
// The route reads profiles.is_anonymous via supabase.from(...).select().eq().single(), so the mock
// client must expose both auth.getUser and a from() chain returning { is_anonymous }.
const authed = (isAnon = false) => ({
  auth: { getUser: async () => ({ data: { user: { id: 'u1' } } }) },
  from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: { is_anonymous: isAnon } }) }) }) }),
});
const req = (url: string) => new Request(url, { method: 'POST' });
const params = (id: string, sectionId: string) => ({ params: Promise.resolve({ id, sectionId }) });

beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { delete process.env.STORAGE_BACKEND; });
beforeEach(() => jest.clearAllMocks());

it('400 before auth when outputFolder is present', async () => {
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}&outputFolder=`), params('vid1', '132') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('400 on non-integer sectionId, before auth', async () => {
  const res = await POST(req(`https://x/api/videos/vid1/dig/abc?playlist=${UUID}`), params('vid1', 'abc') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('400 on missing/invalid playlist uuid, before auth', async () => {
  const res = await POST(req('https://x/api/videos/vid1/dig/132?playlist=nope'), params('vid1', '132') as any);
  expect(res.status).toBe(400);
});
it('401 when unauthenticated', async () => {
  (createServerSupabase as jest.Mock).mockReturnValue({ auth: { getUser: async () => ({ data: { user: null } }) } });
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}`), params('vid1', '132') as any);
  expect(res.status).toBe(401);
});
it('delegates to enqueueDig and serializes its result', async () => {
  (createServerSupabase as jest.Mock).mockReturnValue(authed());
  (enqueueDig as jest.Mock).mockResolvedValue({ status: 202, body: { status: 'enqueued', jobId: 'j', sectionId: 132 } });
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}`), params('vid1', '132') as any);
  expect(res.status).toBe(202);
  expect(await res.json()).toEqual({ status: 'enqueued', jobId: 'j', sectionId: 132 });
  expect(enqueueDig).toHaveBeenCalledWith(expect.objectContaining({
    userId: 'u1', isAnonymous: false, videoId: 'vid1', playlistId: UUID, sectionId: 132,
  }));
});
```

- [ ] **Step 3: Run — confirm failure**

Run: `npx jest dig-cloud-route`
Expected: FAIL — no supabase branch yet (local branch tries to read `outputFolder` from JSON body and behaves differently).

- [ ] **Step 4: Add the cloud branch**

At the very top of `POST` in `app/api/videos/[id]/dig/[sectionId]/route.ts`, before the existing local logic, add the backend branch. Keep the existing local body unchanged below it.

```ts
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { createServiceClient } from '@/lib/supabase/service';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
import { parseClientIp } from '@/lib/http/client-ip';
import { cookies } from 'next/headers';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

// Match the EXISTING route's signature exactly (route.ts:13) — do not introduce a second binding.
// If the current route is `POST(request: Request, { params }: { params: Promise<{ id: string; sectionId: string }> })`,
// keep that shape; adapt the destructuring so both branches read the same videoId/sectionId.
export async function POST(request: Request, { params }: { params: Promise<{ id: string; sectionId: string }> }) {
  const { id: videoId, sectionId: sectionIdRaw } = await params;

  if ((process.env.STORAGE_BACKEND ?? 'local') === 'supabase') {
    const url = new URL(request.url);
    // 400-before-401 validation
    if (url.searchParams.has('outputFolder')) return json({ error: 'outputFolder not valid on this backend' }, 400);
    const sectionId = Number(sectionIdRaw);
    if (!Number.isInteger(sectionId) || sectionId < 0) return json({ error: 'invalid sectionId' }, 400);
    const playlistId = url.searchParams.get('playlist');
    if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400);
    try { assertVideoId(videoId); } catch { return json({ error: 'invalid videoId' }, 400); }

    const cookieStore = (await cookies()) as unknown as CookieStore;
    const supabase = createServerSupabase(cookieStore);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return json({ error: 'authentication required' }, 401);

    // Authoritative anon status = profiles.is_anonymous (the SAME column enqueue_job checks at
    // 0011:101), read via the session client under RLS (a user may read their own profile). Do NOT
    // trust user.is_anonymous — it is not guaranteed to be populated in this project's auth config.
    const { data: profile } = await supabase.from('profiles').select('is_anonymous').eq('id', user.id).single();

    const result = await enqueueDig({
      supabase, enqueuer: new SupabaseEnqueuer(createServiceClient()),
      userId: user.id, isAnonymous: profile?.is_anonymous === true,
      videoId, playlistId, sectionId, enqueueIp: parseClientIp(request),
    });
    return json(result.body, result.status);
  }

  // ---- existing local branch (unchanged) ----
  // ... current in-memory job-registry logic ...
}
```

If the existing local `POST` reads `videoId`/`sectionId` differently, adapt the destructuring so both branches see the same values; do not change local behavior.

- [ ] **Step 5: Run route + local dig route tests — confirm pass, no local regression**

Run: `npx jest dig-cloud-route dig`
Expected: PASS (cloud branch green; existing local dig route tests unaffected).

- [ ] **Step 6: Commit**

```bash
git add lib/http/client-ip.ts app/api/jobs/route.ts app/api/videos/[id]/dig/[sectionId]/route.ts tests/app/api/videos/dig-cloud-route.test.ts
git commit -m "feat(cloud-dig): cloud trigger branch on POST dig route + shared parseClientIp"
```

---

### Task 7: Integration — round-trip, isolation, money, concurrency

**Files:**
- Create: `tests/integration/dig-cloud.test.ts`

**Interfaces:**
- Consumes: everything above, plus integration helpers `adminClient`, `newUser`, `signInAs` (`tests/integration/helpers/clients.ts`); `seedPlaylist`, `seedPromotedVideo`, `seedSummaryBlob` (`tests/integration/helpers/seed.ts`); `ensureGuardrailHeadroom`; `SupabaseBlobStore`; `makeDigHandler`; `enqueueDig`; `SupabaseEnqueuer`; `digSectionKey`, `digJobVersion`.

Mirror `tests/integration/pdf-cloud.test.ts` for owner-isolation + spend mutation-control, and `tests/integration/summary-handler.test.ts` for the direct-handler blob round-trip. Mock only `@/lib/gemini` and `@/lib/transcript-source`; everything else real.

- [ ] **Step 0: Extend `seedPromotedVideo` to persist `durationSeconds` and `youtubeUrl`**

The real `seedPromotedVideo` (`tests/integration/helpers/seed.ts`) writes `data` WITHOUT `durationSeconds` or `youtubeUrl`. But `enqueueDig` reads `load.video.durationSeconds` (→ `enqueue_job` PJ003 backstop reads `payload.durationSeconds`; NULL → **400**, breaking every 202-expecting test) and the handler reads `video.youtubeUrl`. Add both to the helper's `opts` and `data` with defaults, keeping existing callers working:

```ts
// in seedPromotedVideo opts:  durationSeconds?: number; youtubeUrl?: string;
// in the inserted `data` object, alongside language/summaryMd:
durationSeconds: opts.durationSeconds ?? 600,
youtubeUrl: opts.youtubeUrl ?? `https://youtu.be/${videoId}`,
```

Run the existing suites that use `seedPromotedVideo` (`npx jest pdf-cloud html`) to confirm the two added fields don't disturb them.

- [ ] **Step 1: Write the round-trip test**

A summary must exist first (dig sources sections from it). Seed a promoted video + its summary blob (with a real section at `startSec=132`), then enqueue a dig via `enqueueDig` (charge-once), then run `makeDigHandler` directly against a leased-shaped job, then assert the per-section blob.

```ts
import { SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { makeDigHandler } from '@/lib/job-queue/dig-handler';
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';

jest.mock('@/lib/gemini');
jest.mock('@/lib/transcript-source');
import { resolveTranscriptSegments } from '@/lib/transcript-source';
import { generateDig } from '@/lib/dig/generate';
jest.mock('@/lib/dig/generate', () => ({ ...jest.requireActual('@/lib/dig/generate'), generateDig: jest.fn() }));

const admin = adminClient();
// Real parseable section format (▶, en-dash range, trailing `s`) — parseSummaryMarkdown is real here.
const SUMMARY_MD = `# T\n\n## 2. Encoder\n▶ [2:12–2:20](https://youtu.be/VID?t=132s)\nProse.\n`;
const digCtx = () => ({ isCancelled: async () => false, signal: new AbortController().signal, setPhase: async () => {} });

beforeAll(async () => {
  process.env.STORAGE_BACKEND = 'supabase';
  await ensureGuardrailHeadroom(admin);
  // dig is the FIRST integration path that goes through enqueue_preflight — pin its admission
  // ceilings generously so cross-file accumulation of registered users / queued jobs on the shared
  // local Postgres cannot flake the 202-expecting tests (see cost-guardrails.test.ts:283-288).
  await admin.from('guardrail_config').update({ max_free_users: 10_000_000, max_queue_depth: 10_000_000 }).eq('id', true);
  // raise registered dig quota so back-to-back digs in one owner don't hit the 5/month cap.
  await admin.from('quota_allowance').update({ monthly: 100_000 }).eq('is_anonymous', false).eq('kind', 'dig');
});
afterAll(() => { delete process.env.STORAGE_BACKEND; });
beforeEach(async () => {
  (resolveTranscriptSegments as jest.Mock).mockResolvedValue({ segments: [{ text: 'x', offset: 132, duration: 5 }], source: 'captions' });
  (generateDig as jest.Mock).mockResolvedValue('Dig prose. [[SLIDE:2:12|2:20|cap]] End.');
  // clear money tables so charge assertions are deterministic (mirror pdf-cloud.test.ts)
  await admin.from('spend_ledger').delete().neq('day', '1970-01-01');
  await admin.from('usage_counters').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
});

async function seedVideoWithSummary(ownerId: string) {
  const { playlistId, playlistKey } = await seedPlaylist(admin, ownerId);
  const base = '0007_intro';
  await seedPromotedVideo(admin, { ownerId, playlistId, videoId: 'VID', base, title: 'T' });
  await seedSummaryBlob(admin, ownerId, playlistKey, base, SUMMARY_MD);
  return { playlistId, playlistKey, base };
}

it('enqueue → handler → per-section blob round-trip (tokens preserved)', async () => {
  const { user, email, password } = await newUser();
  const { client } = await signInAs(email, password);
  const { playlistId, playlistKey, base } = await seedVideoWithSummary(user.id);

  const res = await enqueueDig({
    supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false,
    videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
  });
  expect(res.status).toBe(202);

  await makeDigHandler(admin)(
    { id: (res.body as any).jobId, ownerId: user.id, playlistId, videoId: 'VID', sectionId: 132, kind: 'dig', version: digJobVersion(), payload: { durationSeconds: 600 }, attempts: 0, leaseToken: 'lt' } as any,
    digCtx() as any,
  );

  const blob = new SupabaseBlobStore(admin, 'artifacts');
  const principal = { id: user.id, indexKey: playlistKey };
  const body = (await blob.get(principal, digSectionKey(base, 132)))!.toString('utf-8');
  expect(body).toContain('sectionId: 132');
  expect(body).toContain('[[SLIDE:2:12|2:20|cap]]');
});
```

- [ ] **Step 2: Owner isolation**

```ts
it('a non-owner cannot trigger dig on another user\'s video (404, no enqueue)', async () => {
  const owner = await newUser();
  const { playlistId } = await seedVideoWithSummary(owner.user.id);
  const other = await newUser();
  const { client: otherClient } = await signInAs(other.email, other.password);
  const spy = jest.spyOn(SupabaseEnqueuer.prototype, 'enqueue');
  const res = await enqueueDig({
    supabase: otherClient, enqueuer: new SupabaseEnqueuer(admin), userId: other.user.id, isAnonymous: false,
    videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
  });
  expect(res.status).toBe(404);
  expect(spy).not.toHaveBeenCalled();
  spy.mockRestore();
});
```

- [ ] **Step 3: No-charge-on-dedup + mutation control**

```ts
it('dedup: blob present → 200 ready, NO enqueue rpc, ledger + usage unchanged', async () => {
  const { user, email, password } = await newUser();
  const { client } = await signInAs(email, password);
  const { playlistId, playlistKey, base } = await seedVideoWithSummary(user.id);
  // pre-seed the current-version dig blob
  await new SupabaseBlobStore(admin, 'artifacts').put({ id: user.id, indexKey: playlistKey }, digSectionKey(base, 132), Buffer.from('---\n---\nx\n'), 'text/markdown');

  const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc'); // explicit target (matches pdf-cloud.test.ts)
  const { data: ucBefore } = await admin.from('usage_counters').select('*').eq('owner_id', user.id);
  const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
  expect(res.status).toBe(200);
  expect(rpcSpy.mock.calls.filter((c) => c[0] === 'enqueue_job').length).toBe(0);
  const { data: ucAfter } = await admin.from('usage_counters').select('*').eq('owner_id', user.id);
  expect(ucAfter ?? []).toEqual(ucBefore ?? []);
  rpcSpy.mockRestore();
});

it('mutation control: NO pre-seeded blob → 202, enqueue_job called once, dig usage +1', async () => {
  const { user, email, password } = await newUser();
  const { client } = await signInAs(email, password);
  const { playlistId } = await seedVideoWithSummary(user.id);
  const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
  expect(res.status).toBe(202);
  const { data: uc } = await admin.from('usage_counters').select('used').eq('owner_id', user.id).eq('kind', 'dig').single();
  expect(uc!.used).toBe(1);
});
```

- [ ] **Step 4: Concurrency — two sections of one video both land**

Seed a summary with two sections (`startSec` 0 and 132). Enqueue + run dig for both concurrently; assert both per-section blobs exist and neither clobbers the other.

```ts
it('concurrent dig of two sections of one video: both blobs land intact', async () => {
  const { user, email, password } = await newUser();
  const { client } = await signInAs(email, password);
  const TWO = `# T\n\n## 1. Intro\n▶ [0:00–2:12](https://youtu.be/VID?t=0s)\nIntro.\n\n## 2. Encoder\n▶ [2:12–2:20](https://youtu.be/VID?t=132s)\nEnc.\n`;
  const { playlistId, playlistKey } = await seedPlaylist(admin, user.id).then(async (pl) => {
    await seedPromotedVideo(admin, { ownerId: user.id, playlistId: pl.playlistId, videoId: 'VID', base: '0007_intro', title: 'T' });
    await seedSummaryBlob(admin, user.id, pl.playlistKey, '0007_intro', TWO);
    return pl;
  });
  const run = async (sec: number) => {
    const r = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: sec, enqueueIp: null });
    await makeDigHandler(admin)({ id: (r.body as any).jobId, ownerId: user.id, playlistId, videoId: 'VID', sectionId: sec, kind: 'dig', version: digJobVersion(), payload: { durationSeconds: 600 }, attempts: 0, leaseToken: 'lt' } as any, digCtx() as any);
  };
  await Promise.all([run(0), run(132)]);
  const blob = new SupabaseBlobStore(admin, 'artifacts');
  const p = { id: user.id, indexKey: playlistKey };
  expect(await blob.exists(p, digSectionKey('0007_intro', 0))).toBe(true);
  expect(await blob.exists(p, digSectionKey('0007_intro', 132))).toBe(true);
});
```

- [ ] **Step 5: Version-aware + completed-row-masks-blob (idempotency/version/§9.2 proofs)**

Inserting `jobs` rows directly: include every NOT-NULL column the live `jobs` schema (0008/0009) requires without a default — at minimum `owner_id, playlist_id, video_id, section_id, job_kind, job_version, status, payload, max_attempts`. Verify against the migration before writing.

```ts
it('version bump re-enqueues + charges: an OLD completed dig row + old blob does NOT dedup the current version', async () => {
  const { user, email, password } = await newUser();
  const { client } = await signInAs(email, password);
  const { playlistId, playlistKey, base } = await seedVideoWithSummary(user.id);
  await admin.from('jobs').insert({ owner_id: user.id, playlist_id: playlistId, video_id: 'VID', section_id: 132, job_kind: 'dig', job_version: 'dig-0', status: 'completed', payload: {}, max_attempts: 1 });
  const olderKey = digSectionKey(base, 132).replace(/\.r\d+\.md$/, '.r0.md');
  await new SupabaseBlobStore(admin, 'artifacts').put({ id: user.id, indexKey: playlistKey }, olderKey, Buffer.from('old'), 'text/markdown');
  const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
  expect(res.status).toBe(202); // current-version slot free → enqueued
  const { data: uc } = await admin.from('usage_counters').select('used').eq('owner_id', user.id).eq('kind', 'dig').single();
  expect(uc!.used).toBe(1); // charged once for the new version
});

it('completed CURRENT-version job row but blob absent → 409 repair, never a phantom 202 (§9.2)', async () => {
  const { user, email, password } = await newUser();
  const { client } = await signInAs(email, password);
  const { playlistId } = await seedVideoWithSummary(user.id);
  await admin.from('jobs').insert({ owner_id: user.id, playlist_id: playlistId, video_id: 'VID', section_id: 132, job_kind: 'dig', job_version: digJobVersion(), status: 'completed', payload: {}, max_attempts: 1 });
  const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
  expect(res.status).toBe(409); // enqueue_job JOINs the completed row; blob still absent → repair
});

it('concurrent SAME-section enqueue charges exactly once (atomic INSERT-or-JOIN)', async () => {
  const { user, email, password } = await newUser();
  const { client } = await signInAs(email, password);
  const { playlistId } = await seedVideoWithSummary(user.id);
  const call = () => enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
  const [a, b] = await Promise.all([call(), call()]);
  expect(a.status).toBe(202);
  expect(b.status).toBe(202);
  const { data: uc } = await admin.from('usage_counters').select('used').eq('owner_id', user.id).eq('kind', 'dig').single();
  expect(uc!.used).toBe(1); // one INSERT (charge) + one JOIN (no charge)
});
```

- [ ] **Step 6: Run the integration suite**

Run: `npx jest tests/integration/dig-cloud.test.ts`
Expected: PASS (round-trip, owner isolation, no-charge-dedup + mutation control, concurrency, version-bump-charge, completed-row-repair, same-section-single-charge). The rpc spy targets `SupabaseClient.prototype` (matching `pdf-cloud.test.ts`).

- [ ] **Step 7: Full suite + typecheck, then commit**

Run: `npx tsc --noEmit && npm test`
Expected: green (2 pre-existing integration skips are acceptable).

```bash
git add tests/integration/dig-cloud.test.ts
git commit -m "test(cloud-dig): integration — round-trip, isolation, no-charge-on-dedup + mutation control, concurrency, version-aware"
```

---

## Self-Review (author checklist — completed)

**1. Spec coverage:**
- §3 in-scope items 1–4 → Tasks 1, 6, 3+4, 2 respectively. ✓
- §5 trigger contract (all response rows) → Task 5 core + Task 6 route + Task 7 integration. ✓
- §6 worker handler steps → Task 3. ✓
- §7 output file format (key + frontmatter + token preservation) → Task 2. ✓
- §8 concurrency (per-section blobs) → Task 2 key design + Task 7 Step 4 proof. ✓
- §9 charging/idempotency/version → Task 1 (RPC), Task 2 (`digJobVersion`/version-in-key), Task 5 (dedup + charge mapping), Task 7 Steps 3/5. ✓
- §9.1 idempotency-vs-version → resolved: `version = dig-${DIG_GENERATOR_VERSION}` (distinct `jobs_idem_active` slot per version) + blob-is-dedup-authority; Task 1 Step 3 verifies the index/ON CONFLICT match. ✓
- §11 behaviors 1–21 → covered across Task 5 unit + Task 6 route + Task 7 integration (rows 11a–c summary-gate = Task 5 passthrough of `loadSummaryForServe`; row 15 transcript-absent = Task 3 real-error test; row 16 crash-before-promote = staged→promote in Task 2/3; row 17 concurrency + row 21 version-bump = Task 7 Step 4/5; row 18 token preservation = Tasks 2/3/7; row 19 stale-version = Task 3 guard test; row 20 completed-row-mask = Task 5 + Task 7 §9.2 tests). ✓
- §13 "summary check must not charge a magazine model" → satisfied by using `loadSummaryForServe` (which stops before `resolveMagazineModel`), asserted structurally in Task 5. ✓

**2. Placeholder scan:** The only intentional "…" is the verbatim-copy instruction in Task 1 Step 3 (reproduce the 0011 `enqueue_job` body, change one named line) — a precise transcription against a named source, not a vague placeholder. Task 3 Step 3 names the exact source (`summary-handler.ts` `CLOUD_CAPS`) to reuse for caps. No TODO/TBD/"handle errors" placeholders.

**3. Type consistency:** `digSectionKey`/`digJobVersion` (Task 2) are consumed identically in Tasks 3, 5, 7. `EnqueueDigDeps`/`enqueueDig` return `{status, body}` consumed verbatim by Task 6. `JobKey`/`DigJobPayload`/`EnqueueResult` match the widened enqueuer signature. `makeDigHandler(serviceClient): JobHandler` matches the dispatcher's `Record<JobKind, JobHandler>` in Task 4. ✓

## Round-1 dual-review dispositions (Codex + Claude → `docs/reviews/plan-cloud-dig-generation-codex.md`)
All Blocking/High/Medium addressed in this revision:
- **B1 (fixtures unparseable)** → all summary fixtures use the real `▶ [M:SS–M:SS](…?t=<sec>s)` format.
- **B2 (completed row masks missing blob)** → `enqueueDig` re-checks the blob on `joined && completed` → 200/409, never a phantom 202 (Task 5 + Task 7 tests).
- **B3 (stale-version job)** → handler version guard `job.version !== digJobVersion()` (Task 3 + test).
- **H1 (base divergence)** → shared `resolveSummaryMdKey`; handler and trigger key the same blob (Task 3).
- **H2 (transcript error not non-retryable)** → handler wraps `PermanentTranscriptError`→`NonRetryableError`; test uses the real class asserting `NonRetryableError` (Task 3).
- **H3/anon** → anon read from `profiles.is_anonymous` in the route, not `user.is_anonymous` (Task 6).
- **M1** import path fixed; **M2** `digSectionKey` base guard; **M3/M4** version/mask/concurrency tests strengthened; **M5** spec status codes corrected (503/404/409).
- **L1** migration verify wording pinned to the exact live index columns; **L2** quota relabeled 5/month; **L3** phase reuse noted; **L4** rpc spy → `SupabaseClient.prototype`.

## Round-2 re-review dispositions — CONVERGED (`docs/reviews/plan-cloud-dig-generation-codex-v2.md`)
Both reviewers (Codex + Claude) independently confirmed **0 new Blocking / 0 new High in production code** and verified all 7 round-1 fixes are genuinely correct against real code (completed-join returns `status='completed'`; `digJobVersion()` shared both sides; `readVideo` retains raw `artifacts` — H1 truly fixed; the transcript catch does not swallow `AbortError`; `profiles_self` RLS permits own-row read — H3 works; base guard + fixtures parse correctly). Convergence gate met. Remaining findings were all in the **Task 7 integration harness** and are fixed here:
- **(High, deterministic) `seedPromotedVideo` omitted `durationSeconds`/`youtubeUrl`** → null `durationSeconds` tripped `enqueue_job` PJ003 → 400 on every 202-expecting test. Fixed: Task 7 Step 0 extends the helper.
- **(Medium) anon test used `profiles.update({is_anonymous})`** — blocked by the immutable trigger → not a real anon. Fixed: uses `anonSession()` + asserts `is_anonymous`.
- **(Medium) preflight ceilings unpinned** — dig is the first integration path through `enqueue_preflight`; Fixed: `beforeAll` pins `max_free_users`/`max_queue_depth` + dig quota.
- **(Low) Task 6 param binding** aligned to the existing `POST(request, { params })` signature; **(Low) stale "5/day"** → 5/month.

## Deferred with rationale (recorded for later slices)
- **L5 (abort not threaded into `generateDig`)** — bounded by `dig_max_attempts=1` + `generateDig`'s own 60s timeout, and the blob is abort-safe (staged→promote after the abort check). Threading a signal into `generateDig`/`callGeminiRest` touches shared local dig code; deferred to a hardening pass.
- **L6 (GC vs completed-job row)** — a future GC slice that deletes a dig blob MUST delete the completed job row too, or it recreates the §9.2 mask. Recorded as a constraint for the GC slice.

## Still to confirm during implementation (named source, not a placeholder)
- Task 1 Step 3: verify no line other than the kind guard changed and the est/attempts dig dispatch is preserved (diff against the 0011 body).
- Task 3 caps reuse: confirm `gemini-2.5-pro` is not rejected by a `PRICED_MODEL`-style guard and that `CLOUD_CAPS` token limits suit the dig prompt.
- Task 5/6: confirm the session client can read its own `profiles.is_anonymous` under RLS (add the anon path to the integration suite if in doubt).
