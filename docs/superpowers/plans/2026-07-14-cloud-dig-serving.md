# Cloud Dig Serving Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the per-section cloud dig blobs (PR #15) viewable — serve a merged skim+dig HTML doc at `type=dig-deeper` and add a cloud branch to the dig-state endpoint.

**Architecture:** Read-only. A cloud dig loader reuses `loadSummaryForServe` (owner-assert + gate + `base`, **without charging**), reads the cached magazine model for free, lists+parses the current-version `dig/{base}/{sectionId}.r{V}.md` blobs into `DugSection[]`, and feeds the existing `renderDigDeeperDoc` (extended with a static `readOnly` mode + nonce). Dig-state lists the same blobs.

**Tech Stack:** Next.js 16 App Router route handlers, Supabase (Storage + RLS), TypeScript, jest + ts-jest. Spec: `docs/superpowers/specs/2026-07-14-cloud-dig-serving-design.md`.

## Global Constraints

- **Money invariant:** the dig serve path must NEVER call `resolveMagazineModel` / `reserve_serve_model` / `resolveAndParse` / any generation. Serving dig = pure blob read + render. (Spec §2.)
- **No live Gemini** in any test — mock at the storage/RPC boundary.
- **Local paths untouched:** `renderDigDeeperDoc` with default args, and the local `html`/`dig-state` branches, stay byte-identical. Both new render args default off.
- **Version-aware:** only `.r{DIG_GENERATOR_VERSION}.md` blobs are read/listed; stale-version blobs are ignored.
- **Owner isolation:** all blob reads/lists go through the session-scoped, RLS-enforced `bundle.blobStore` for the authenticated principal.
- **`@/lib/*` path alias** works in app + tests (tsconfig + jest moduleNameMapper). Read `node_modules/next/dist/docs/` before touching route-handler conventions.
- **Verify tsc by exit code:** `npx tsc --noEmit; echo "EXIT=$?"` — never pipe through `tail && echo` (masks the exit code).

**Interfaces produced by this plan (names later tasks rely on):**
- T1: `parseCloudDigSectionBlob(bytes: Buffer): DugSection` and `slideTokensToCaptions(md: string): string` — `lib/dig/cloud/parse-dig-section-blob.ts`
- T2: `BlobStore.list(p: Principal, prefix: string): Promise<string[]>` (logical keys, relative to the owner root)
- T3: `loadDigForServe(supabase, {videoId, playlistId, userId}): Promise<LoadDigResult>` — `lib/dig/cloud/load-dig-for-serve.ts`
- T4: `renderDigDeeperDoc({ …, readOnly?: boolean, nonce?: string })` — extended in place

---

## Task 1: `parseCloudDigSectionBlob` + `slideTokensToCaptions`

Pure functions: parse one cloud dig blob into the existing `DugSection`, and rewrite unresolved slide tokens into caption placeholders.

**Files:**
- Create: `lib/dig/cloud/parse-dig-section-blob.ts`
- Test: `tests/lib/dig/cloud/parse-dig-section-blob.test.ts` (**must** live under `tests/lib/**` — `jest.config` `testMatch` only runs `tests/lib`, `tests/api`, `tests/scripts`, `tests/components`; a file at `tests/dig/…` silently never runs)

**Interfaces:**
- Consumes: `DugSection` (`lib/dig/companion-doc.ts:30`): `{ sectionId:number; startSec:number; title:string; bodyMarkdown:string; generatedAt:string; genVersion:number; slides?:… }`. Blob format written by `lib/dig/cloud/write-dig-section-blob.ts:29-43` (frontmatter fields `videoId, sectionId, startSec, title, language, sourceVideoUrl, generatedAt, genVersion, slides: []`; ints unquoted, `language` unquoted, strings double-quoted with `\\`/`\"` escaping; body follows the closing `---`).
- Produces: `parseCloudDigSectionBlob`, `slideTokensToCaptions`.

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/dig/cloud/parse-dig-section-blob.test.ts
import { parseCloudDigSectionBlob, slideTokensToCaptions } from '@/lib/dig/cloud/parse-dig-section-blob';

const BLOB = `---
videoId: "abc123"
sectionId: 65
startSec: 65
title: "The \\"Car Wreck\\" — part 1"
language: en
sourceVideoUrl: "https://youtu.be/abc123"
generatedAt: "2026-07-14T00:00:00.000Z"
genVersion: 3
slides: []
---
Body line one.

[[SLIDE:1:05|2:20|Self-attention heat-map]] then more prose.
`;

describe('parseCloudDigSectionBlob', () => {
  it('maps frontmatter + body to a DugSection', () => {
    const d = parseCloudDigSectionBlob(Buffer.from(BLOB, 'utf-8'));
    expect(d.sectionId).toBe(65);
    expect(d.startSec).toBe(65);
    expect(d.title).toBe('The "Car Wreck" — part 1'); // quote unescaped
    expect(d.generatedAt).toBe('2026-07-14T00:00:00.000Z');
    expect(d.genVersion).toBe(3);
    expect(d.bodyMarkdown).toContain('Body line one.');
    expect(d.bodyMarkdown).toContain('[[SLIDE:1:05|2:20|Self-attention heat-map]]'); // parse is faithful; token preserved
  });

  it('throws on a blob with no frontmatter', () => {
    expect(() => parseCloudDigSectionBlob(Buffer.from('no frontmatter here', 'utf-8'))).toThrow();
  });

  it('throws on a non-integer sectionId', () => {
    const bad = BLOB.replace('sectionId: 65', 'sectionId: not-a-number');
    expect(() => parseCloudDigSectionBlob(Buffer.from(bad, 'utf-8'))).toThrow();
  });

  it('round-trips a title with a literal backslash before a quote (escape-order guard)', () => {
    // writer (write-dig-section-blob.ts yamlScalar) escapes `\` → `\\` THEN `"` → `\"`.
    // Source title: A \ "B"  → on disk: title: "A \\ \"B\""  → parser must invert in reverse order.
    const wire = BLOB.replace('title: "The \\"Car Wreck\\" — part 1"', 'title: "A \\\\ \\"B\\""');
    const d = parseCloudDigSectionBlob(Buffer.from(wire, 'utf-8'));
    expect(d.title).toBe('A \\ "B"');
  });
});

describe('slideTokensToCaptions', () => {
  it('rewrites [[SLIDE:start|end|caption]] to a caption placeholder', () => {
    const out = slideTokensToCaptions('a [[SLIDE:1:05|2:20|Heat map]] b');
    expect(out).not.toContain('[[SLIDE');
    expect(out).toContain('🖼');
    expect(out).toContain('Heat map');
  });

  it('drops a token with an empty caption entirely', () => {
    const out = slideTokensToCaptions('a [[SLIDE:1:05|2:20|]] b');
    expect(out).not.toContain('[[SLIDE');
    expect(out).not.toContain('🖼');
  });

  it('leaves text with no tokens unchanged', () => {
    expect(slideTokensToCaptions('plain body')).toBe('plain body');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest parse-dig-section-blob`
Expected: the suite is **found and runs** (file is under `tests/lib/**`), then FAILs — "Cannot find module '@/lib/dig/cloud/parse-dig-section-blob'". (If jest prints "No tests found", the file is mis-located — fix the path before proceeding; a not-found suite is not a RED.)

- [ ] **Step 3: Implement**

```ts
// lib/dig/cloud/parse-dig-section-blob.ts
import type { DugSection } from '@/lib/dig/companion-doc';

/** Match [[SLIDE:start|end|caption]] — caption is the 3rd, possibly-empty field. */
const SLIDE_TOKEN_RE = /\[\[SLIDE:[^\]|]*\|[^\]|]*\|([^\]]*)\]\]/g;

/**
 * Rewrite each unresolved slide token into a caption-only placeholder (slide capture is a
 * later slice). A muted blockquote note keeps the caption (already generated/paid for) and
 * needs no shared CSS or html:true. An empty caption drops the token entirely.
 */
export function slideTokensToCaptions(md: string): string {
  return md.replace(SLIDE_TOKEN_RE, (_m, caption: string) => {
    const cap = caption.trim();
    return cap ? `\n\n> 🖼 *${cap}*\n\n` : '';
  });
}

function unquoteYamlScalar(raw: string): string {
  // Inverse of write-dig-section-blob.ts yamlScalar: strip surrounding quotes, unescape \" and \\.
  const inner = raw.replace(/^"|"$/g, '');
  return inner.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
}

/** Parse one cloud dig blob (frontmatter + markdown body) into a DugSection. Throws on a
 *  malformed/foreign blob — the caller skips that one section rather than failing the doc. */
export function parseCloudDigSectionBlob(bytes: Buffer): DugSection {
  const text = bytes.toString('utf-8').replace(/\r\n/g, '\n');
  const m = text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) throw new Error('dig blob: missing frontmatter');
  const [, fm, body] = m;

  const intField = (key: string): number => {
    const mm = fm.match(new RegExp(`^${key}:\\s*(-?\\d+)\\s*$`, 'm'));
    if (!mm) throw new Error(`dig blob: missing/invalid int field ${key}`);
    return parseInt(mm[1], 10);
  };
  const strField = (key: string): string => {
    const mm = fm.match(new RegExp(`^${key}:\\s*(".*")\\s*$`, 'm'));
    if (!mm) throw new Error(`dig blob: missing string field ${key}`);
    return unquoteYamlScalar(mm[1]);
  };

  return {
    sectionId: intField('sectionId'),
    startSec: intField('startSec'),
    title: strField('title'),
    bodyMarkdown: body.replace(/^\n+/, '').trimEnd(),
    generatedAt: strField('generatedAt'),
    genVersion: intField('genVersion'),
    slides: [], // text-only slice: frontmatter is always `slides: []`
  };
}
```

- [ ] **Step 4: Run tests — confirm pass**

Run: `npx jest parse-dig-section-blob` → PASS.

- [ ] **Step 5: tsc + commit**

```bash
npx tsc --noEmit; echo "EXIT=$?"   # expect EXIT=0
git add lib/dig/cloud/parse-dig-section-blob.ts tests/lib/dig/cloud/parse-dig-section-blob.test.ts
git commit -m "feat(cloud-dig-serving): parse cloud dig blob → DugSection + slide-token captions"
```

---

## Task 2: `BlobStore.list(prefix)` primitive

Enumerate dug sections without a stored index (spec §3 Unit A note). Add a `list` returning **logical keys** (relative to the owner root `<id>/<indexKey>/`).

**Files:**
- Modify: `lib/storage/blob-store.ts` (add `list` to the `BlobStore` interface)
- Modify: `lib/storage/supabase/supabase-blob-store.ts` (implement via the existing `collectObjectPaths`)
- Modify: `lib/storage/local/local-blob-store.ts` (implement via `fs`)
- Test: `tests/lib/storage/blob-store-list.test.ts` (under `tests/lib/**` so `testMatch` runs it)

**Interfaces:**
- Consumes: `Principal` (`{id, indexKey}`), `assertLogicalKey` (`lib/storage/blob-store.ts`), the private `collectObjectPaths(dirPath)` (`supabase-blob-store.ts:78`).
- Produces: `list(p: Principal, prefix: string): Promise<string[]>` — logical keys under `prefix` (e.g. `dig/base/65.r3.md`), empty array if the prefix is absent.

- [ ] **Step 1: Write the failing test (local store as the concrete impl)**

```ts
// tests/lib/storage/blob-store-list.test.ts
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import type { Principal } from '@/lib/storage/principal';
import fs from 'fs';
import os from 'os';
import path from 'path';

describe('localBlobStore.list', () => {
  let dir: string;
  let p: Principal;
  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), 'bloblist-'));
    p = { id: 'owner', indexKey: dir } as Principal;
  });
  afterEach(() => fs.rmSync(dir, { recursive: true, force: true }));

  it('returns logical keys under a prefix', async () => {
    await localBlobStore.put(p, 'dig/base/65.r3.md', Buffer.from('a'), 'text/markdown');
    await localBlobStore.put(p, 'dig/base/120.r3.md', Buffer.from('b'), 'text/markdown');
    await localBlobStore.put(p, 'models/base.json', Buffer.from('{}'), 'application/json');
    const keys = await localBlobStore.list(p, 'dig/base/');
    expect(keys.sort()).toEqual(['dig/base/120.r3.md', 'dig/base/65.r3.md']);
  });

  it('returns [] for an absent prefix', async () => {
    expect(await localBlobStore.list(p, 'dig/nope/')).toEqual([]);
  });
});

// The production path — the tenant-isolation seam (spec §11.2: cross-tenant enumeration is the
// worst-case leak). Mock Supabase Storage `.list`; assert enumeration is scoped to THIS owner's
// root and the returned keys are logical (owner root fully stripped, never leaked).
describe('SupabaseBlobStore.list (owner-scoped)', () => {
  function fakeClient(entriesByDir: Record<string, Array<{ name: string; id: string | null }>>) {
    const list = jest.fn(async (dirPath: string) => ({ data: entriesByDir[dirPath] ?? [], error: null }));
    return { client: { storage: { from: () => ({ list }) } }, list };
  }

  it('lists under the owner root, recurses folders, returns logical keys only', async () => {
    const p = { id: 'owner1', indexKey: 'pl-key' } as Principal;
    const root = 'owner1/pl-key/dig/base';
    const { client, list } = fakeClient({
      [root]: [{ name: '65.r9.md', id: 'f1' }, { name: 'nested', id: null }], // folder → recurse
      [`${root}/nested`]: [{ name: '120.r9.md', id: 'f2' }],
    });
    const store = new SupabaseBlobStore(client as never, 'artifacts');
    const keys = await store.list(p, 'dig/base/');
    expect(keys.sort()).toEqual(['dig/base/65.r9.md', 'dig/base/nested/120.r9.md']); // owner root stripped
    expect(list).toHaveBeenCalledWith('owner1/pl-key/dig/base', expect.anything()); // scoped to this owner
    for (const k of keys) expect(k.startsWith('owner1/')).toBe(false); // no owner id leaks into a logical key
  });

  it('returns [] for an absent prefix (every dir empty)', async () => {
    const p = { id: 'o', indexKey: 'k' } as Principal;
    const { client } = fakeClient({});
    const store = new SupabaseBlobStore(client as never, 'artifacts');
    expect(await store.list(p, 'dig/nope/')).toEqual([]);
  });
});
```

> Pagination (`collectObjectPaths`' 100/page offset loop) is already exercised by the existing `deletePrefix` supabase tests — `list` reuses the same private walker, so these tests target the new owner-root strip, not re-cover pagination.

- [ ] **Step 2: Run — verify fail**

Run: `npx jest blob-store-list` → the suite is found and runs, then FAILs ("list is not a function" for both local and supabase). If jest says "No tests found", the path is wrong — fix before proceeding.

- [ ] **Step 3: Add to the interface**

```ts
// lib/storage/blob-store.ts — add to interface BlobStore, after deletePrefix:
  /** List logical keys (relative to the owner root) under a prefix. Absent prefix → []. */
  list(p: Principal, prefix: string): Promise<string[]>;
```

- [ ] **Step 4: Implement — local**

```ts
// lib/storage/local/local-blob-store.ts — add method (uses the existing `fs`/`path` imports):
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
```

- [ ] **Step 5: Implement — supabase**

```ts
// lib/storage/supabase/supabase-blob-store.ts — add method; reuse collectObjectPaths:
  async list(p: Principal, prefix: string): Promise<string[]> {
    assertLogicalKey(prefix);
    const ownerRoot = `${p.id}/${p.indexKey}/`;
    const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
    const full = await this.collectObjectPaths(dirPath); // returns full object paths (or [] if absent)
    return full.map((f) => f.slice(ownerRoot.length)); // strip owner root → logical key
  }
```

> `collectObjectPaths` already returns `[]` when the directory is absent (the paginated `.list` yields no entries). Keep it `private` — `list` is the public seam.

- [ ] **Step 6: Run tests + full suite + tsc + commit**

```bash
npx jest blob-store-list                 # PASS
npx jest storage                          # no regressions in storage tests
npx tsc --noEmit; echo "EXIT=$?"          # EXIT=0
git add lib/storage/blob-store.ts lib/storage/local/local-blob-store.ts lib/storage/supabase/supabase-blob-store.ts tests/lib/storage/blob-store-list.test.ts
git commit -m "feat(cloud-dig-serving): BlobStore.list(prefix) → logical keys (local + supabase)"
```

---

## Task 3: `loadDigForServe` core

Owner-assert + gate + `base` via `loadSummaryForServe` (no charge), parse summary skeleton, read cached model (free), list+parse current-version dig blobs, apply slide→caption, zero→404.

**Files:**
- Create: `lib/dig/cloud/load-dig-for-serve.ts`
- Test: `tests/lib/dig/cloud/load-dig-for-serve.test.ts` (under `tests/lib/**`)

**Interfaces:**
- Consumes: `loadSummaryForServe` (`lib/html-doc/serve-summary-core.ts:34`) — returns `{ok:true, mdBytes, mdKey, base, title, principal, video, bundle}` or `{ok:false, status, error}`; `parseSummaryMarkdown` (`lib/html-doc/parse.ts:118`); `readModelEnvelope(principal, base, blobStore)` (`lib/html-doc/model-store.ts:50`); `DIG_GENERATOR_VERSION` (`@/lib/dig/generate`); T1 `parseCloudDigSectionBlob`/`slideTokensToCaptions`; T2 `blobStore.list`.
- Produces: `loadDigForServe(supabase, {videoId, playlistId, userId})` and `type LoadDigResult`.

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/dig/cloud/load-dig-for-serve.test.ts
import { loadDigForServe } from '@/lib/dig/cloud/load-dig-for-serve';
import * as serveCore from '@/lib/html-doc/serve-summary-core';
import * as serveDoc from '@/lib/html-doc/serve-doc';
import * as modelStore from '@/lib/html-doc/model-store';
import * as digGen from '@/lib/dig/generate';
import * as gemini from '@/lib/gemini';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';

const V = DIG_GENERATOR_VERSION;
const SUMMARY_MD = `# T\n\n**Channel:** C | **Duration:** 1:00\n\n## 1. Alpha\n▶ [1:05–2:00](https://youtu.be/x?t=65s)\nprose one.\n`;
function digBlob(sectionId: number): Buffer {
  return Buffer.from(`---\nvideoId: "v"\nsectionId: ${sectionId}\nstartSec: ${sectionId}\ntitle: "Alpha"\nlanguage: en\nsourceVideoUrl: "https://youtu.be/v"\ngeneratedAt: "2026-07-14T00:00:00.000Z"\ngenVersion: ${V}\nslides: []\n---\ndeep dive body [[SLIDE:1:05|2:00|Cap]]\n`, 'utf-8');
}

function fakeBundle(blobs: Record<string, Buffer>) {
  return {
    blobStore: {
      list: jest.fn(async (_p: unknown, prefix: string) => Object.keys(blobs).filter((k) => k.startsWith(prefix))),
      get: jest.fn(async (_p: unknown, key: string) => blobs[key] ?? null),
    },
  };
}

function mockLoadOk(bundle: ReturnType<typeof fakeBundle>) {
  jest.spyOn(serveCore, 'loadSummaryForServe').mockResolvedValue({
    ok: true, mdBytes: Buffer.from(SUMMARY_MD), mdKey: 'base.md', base: 'base', title: 'T',
    principal: { id: 'o', indexKey: 'k' } as never, playlistId: 'pl', video: { id: 'v', language: 'en' } as never, bundle: bundle as never,
  } as never);
}

describe('loadDigForServe', () => {
  afterEach(() => jest.restoreAllMocks());

  it('returns merged inputs and NEVER charges', async () => {
    const bundle = fakeBundle({ [`dig/base/65.r${V}.md`]: digBlob(65) });
    mockLoadOk(bundle);
    jest.spyOn(modelStore, 'readModelEnvelope').mockResolvedValue(null);
    // Money invariant — spy on EVERY charge-capable / generation entry point so the assertion is
    // direct, not an indirect proxy through the fake bundle. resolveMagazineModel is the ONLY
    // charging function (serve-doc.ts:52 rpc('reserve_serve_model')); the rest must also never run.
    const resolveMag = jest.spyOn(serveDoc, 'resolveMagazineModel');
    const resolveAndParse = jest.spyOn(serveCore, 'resolveAndParse');
    const generateDig = jest.spyOn(digGen, 'generateDig');
    const generateMag = jest.spyOn(gemini, 'generateMagazineModel');
    const rpc = jest.fn();
    const r = await loadDigForServe({ rpc } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.dug).toHaveLength(1);
      expect(r.dug[0].sectionId).toBe(65);
      expect(r.dug[0].bodyMarkdown).toContain('🖼');       // slide→caption applied
      expect(r.dug[0].bodyMarkdown).not.toContain('[[SLIDE');
      expect(r.language).toBe('en');
    }
    expect(rpc).not.toHaveBeenCalled();                     // no RPC (the concrete charge signal)
    expect(resolveMag).not.toHaveBeenCalled();              // the charging fn — never entered
    expect(resolveAndParse).not.toHaveBeenCalled();
    expect(generateDig).not.toHaveBeenCalled();
    expect(generateMag).not.toHaveBeenCalled();
  });

  it('positive control: the money guard actually fires (a real reserve WOULD trip rpc)', async () => {
    // Prove the guard is not vacuous: drive resolveMagazineModel directly with a bundle whose
    // model blob is absent (cache miss) and confirm it reaches rpc('reserve_serve_model'). This is
    // the exact call loadDigForServe must never make — if this control ever stops tripping rpc, the
    // "not.toHaveBeenCalled()" assertions above are meaningless and must be re-derived.
    // Return an UNHANDLED reserve status so resolveMagazineModel's switch hits `default: throw`
    // (serve-doc.ts:73) immediately AFTER the rpc call and BEFORE any generation — guarantees no
    // live Gemini in this control while still proving the reserve RPC was reached.
    const rpc = jest.fn(async () => ({ data: '__unhandled_status__', error: null }));
    const blob = { get: jest.fn(async () => null), put: jest.fn(async () => {}) };
    await serveDoc.resolveMagazineModel({
      supabaseClient: { rpc } as never, blobStore: blob as never,
      principal: { id: 'o', indexKey: 'k' } as never, playlistId: 'pl', videoId: 'v', base: 'base',
      parsed: { title: 'T', sections: [] } as never, language: 'en',
    }).catch(() => {}); // the default-throw is expected; we only assert the reserve was attempted
    expect(rpc).toHaveBeenCalledWith('reserve_serve_model', expect.anything());
  });

  it('404s when there are no current-version dig blobs', async () => {
    const bundle = fakeBundle({ [`dig/base/65.r${V - 1}.md`]: digBlob(65) }); // stale version only
    mockLoadOk(bundle);
    jest.spyOn(modelStore, 'readModelEnvelope').mockResolvedValue(null);
    const r = await loadDigForServe({ rpc: jest.fn() } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r).toEqual({ ok: false, status: 404, error: 'not found' });
  });

  it('skips a malformed blob but still renders the rest', async () => {
    const bundle = fakeBundle({
      [`dig/base/65.r${V}.md`]: digBlob(65),
      [`dig/base/120.r${V}.md`]: Buffer.from('garbage, no frontmatter'),
    });
    mockLoadOk(bundle);
    jest.spyOn(modelStore, 'readModelEnvelope').mockResolvedValue(null);
    const r = await loadDigForServe({ rpc: jest.fn() } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.dug.map((d) => d.sectionId)).toEqual([65]);
  });

  it('propagates a loadSummaryForServe failure verbatim', async () => {
    jest.spyOn(serveCore, 'loadSummaryForServe').mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
    const r = await loadDigForServe({ rpc: jest.fn() } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r).toEqual({ ok: false, status: 404, error: 'not found' });
  });
});
```

- [ ] **Step 2: Run — verify fail**

Run: `npx jest load-dig-for-serve` → FAIL (module not found).

- [ ] **Step 3: Implement**

```ts
// lib/dig/cloud/load-dig-for-serve.ts
import type { SupabaseClient } from '@supabase/supabase-js';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { readModelEnvelope, type ModelEnvelope } from '@/lib/html-doc/model-store';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { parseCloudDigSectionBlob, slideTokensToCaptions } from '@/lib/dig/cloud/parse-dig-section-blob';
import type { ParsedSummary } from '@/lib/html-doc/types';
import type { DugSection } from '@/lib/dig/companion-doc';

export type LoadDigResult =
  | { ok: true; summary: ParsedSummary; envelope: ModelEnvelope | null; dug: DugSection[]; base: string; title?: string; language: 'en' | 'ko' }
  | { ok: false; status: number; error: string };

/**
 * Load the merge inputs for a cloud dig serve. Reuses loadSummaryForServe for owner-assert +
 * status gate + canonical base — which does NOT charge — then reads the CACHED magazine model
 * (free) and the static per-section dig blobs. It must never touch resolveAndParse /
 * resolveMagazineModel / reserve_serve_model (spec §2 money invariant).
 */
export async function loadDigForServe(
  supabase: SupabaseClient,
  a: { videoId: string; playlistId: string; userId: string },
): Promise<LoadDigResult> {
  const load = await loadSummaryForServe(supabase, a);
  if (!load.ok) return load; // propagate {status, error} verbatim (404/503/409)

  const summary = parseSummaryMarkdown(load.mdBytes.toString('utf-8'));
  summary.sourceMd = load.mdKey;

  const envelope = await readModelEnvelope(load.principal, load.base, load.bundle.blobStore); // cached, free; null if absent

  const prefix = `dig/${load.base}/`;
  const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
  const keys = (await load.bundle.blobStore.list(load.principal, prefix)).filter((k) => k.endsWith(suffix));

  const dug: DugSection[] = [];
  for (const key of keys) {
    const bytes = await load.bundle.blobStore.get(load.principal, key);
    if (!bytes) continue; // listed-but-vanished race → skip
    try {
      const section = parseCloudDigSectionBlob(bytes);
      section.bodyMarkdown = slideTokensToCaptions(section.bodyMarkdown);
      dug.push(section);
    } catch {
      // Malformed/foreign blob → skip this section, never fail the whole doc (behavior 19).
    }
  }

  if (dug.length === 0) return { ok: false, status: 404, error: 'not found' };

  return { ok: true, summary, envelope, dug, base: load.base, title: load.title, language: (load.video as { language: 'en' | 'ko' }).language };
}
```

- [ ] **Step 4: Run tests — confirm pass**

Run: `npx jest load-dig-for-serve` → PASS (including the `rpc` never-called assertion).

- [ ] **Step 5: tsc + commit**

```bash
npx tsc --noEmit; echo "EXIT=$?"   # EXIT=0
git add lib/dig/cloud/load-dig-for-serve.ts tests/lib/dig/cloud/load-dig-for-serve.test.ts
git commit -m "feat(cloud-dig-serving): loadDigForServe core — no-charge merge inputs, version-filtered, zero→404"
```

---

## Task 4: `renderDigDeeperDoc` `readOnly` + `nonce`

Add a static read-only mode and CSP nonce to the shared renderer; both default off → local byte-identical.

**Files:**
- Modify: `lib/html-doc/render-dig-deeper.ts` (args + partition + nonce threading; `SIZE_HEAD_SCRIPT`/`CAPTIONS_HEAD_SCRIPT` → functions taking `nonce`)
- Test: `tests/lib/html-doc/render-dig-deeper-readonly.test.ts` (under `tests/lib/**`; a mislocated file silently matches the *existing* `render-dig-deeper*` suite and passes green while the new assertions never run)

**Marker discipline (critical — see review v1 B2/H1):** `DIG_DOC_CSS` emits every control's class name (`.dig-trigger`, `.dg-expand-all`, `#_dg-ea-dlg`, `.ask-ai`, `.dg-size-range`, `.dg-caps-toggle`) unconditionally in the `<style>` block, which `readOnly` keeps. So a whole-HTML `not.toContain('dig-trigger')` can NEVER pass a correct impl, and a `toContain('ask-ai')` is satisfied by CSS even if the control was wrongly dropped. **Every presence/absence assertion must target element/attribute markup, not the bare class token:** `class="dig-trigger"`, `id="_dg-ea-dlg"`, `data-type="summary"`, `dig-trigger[data-section]` (a navScript-only string), etc. This mirrors the existing suite's documented workaround (`render-dig-deeper.test.ts` asserts `not.toContain('class="dig-refresh"')`).

**Interfaces:**
- Consumes (already nonce-capable): `themeHeadScript(nonce?)`, `themeToggleScript(nonce?)`, `printListenerScript(nonce?)`, `nonceAttr(nonce?)` (`lib/html-doc/theme.ts`), `navScript(nonce?)` (`lib/html-doc/nav.ts:446`).
- Produces: `renderDigDeeperDoc({ summary, envelope, dug, mdPath, videoId, language?, cropMap?, readOnly?, nonce? })`.

**Partition rule (readOnly:true):** omit everything that needs `navScript` — the topbar `summaryLink` + `expand all` button, the per-section `dig-trigger`/`dig-refresh`/`dig-toggle` controls, the `expandAllDialogs` markup, and the `navScript()` call. Keep theme, print, slide-zoom, Ask-AI, size, captions (all self-contained). Thread `nonce` to every emitted `<script>`/`<style>`.

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/html-doc/render-dig-deeper-readonly.test.ts
import { renderDigDeeperDoc } from '@/lib/html-doc/render-dig-deeper';
import type { ParsedSummary } from '@/lib/html-doc/types';
import type { DugSection } from '@/lib/dig/companion-doc';

const summary: ParsedSummary = {
  title: 'T', channel: 'C', duration: '1:00', url: null, lang: 'EN', videoId: 'v', tldr: null, takeaways: [],
  sections: [
    { numeral: '1', title: 'Alpha', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: '1:05–2:00', url: 'https://youtu.be/v?t=65s' } },
    { numeral: '2', title: 'Beta', prose: 'p', timeRange: { startSec: 200, endSec: 260, label: '3:20–4:20', url: 'https://youtu.be/v?t=200s' } },
  ],
  sourceMd: 'base.md',
};
const dug: DugSection[] = [
  { sectionId: 65, startSec: 65, title: 'Alpha', bodyMarkdown: 'deep alpha', generatedAt: '2026-07-14T00:00:00Z', genVersion: 3, slides: [] },
];
const base = { summary, envelope: null, dug, mdPath: 'base.md', videoId: 'v', language: 'en' as const };

describe('renderDigDeeperDoc readOnly + nonce', () => {
  it('default render keeps interactive controls and emits no nonce', () => {
    const html = renderDigDeeperDoc(base);
    expect(html).toContain('class="dig-trigger"');   // Beta is un-dug → trigger MARKUP present
    expect(html).toContain('class="dg-expand-all"');  // expand-all button markup present
    expect(html).toContain('dig-trigger[data-section]'); // navScript engine present
    expect(html).not.toContain('nonce=');             // no CSP nonce by default
  });

  it('added params default to a no-op (guards behavior 24 — local output unchanged)', () => {
    // Proves readOnly/nonce OFF is byte-for-byte identical to omitting them entirely, so the
    // const→function + nonceAttr(undefined) threading cannot perturb the local path.
    expect(renderDigDeeperDoc(base)).toBe(renderDigDeeperDoc({ ...base, readOnly: false, nonce: undefined }));
  });

  it('readOnly omits every nav-coupled control, dialog, and the navScript engine', () => {
    const html = renderDigDeeperDoc({ ...base, readOnly: true });
    // element/attribute markers — NOT bare class tokens (those live in kept CSS)
    for (const marker of [
      'class="dig-trigger"', 'class="dig-refresh"', 'class="dig-toggle"',
      'class="dg-expand-all"', 'id="_dg-ea-dlg"', 'data-type="summary"', // summary back-link
      'dig-trigger[data-section]',  // navScript IIFE body (generation engine) — nav-only string
    ]) {
      expect(html).not.toContain(marker);
    }
    expect(html).toContain('deep alpha'); // dug content still rendered statically
  });

  it('readOnly keeps self-contained controls AND their scripts', () => {
    const html = renderDigDeeperDoc({ ...base, readOnly: true });
    // control markup (element-specific)
    expect(html).toContain('id="_dg-zoom"');        // slide-zoom overlay
    expect(html).toContain('class="ask-ai"');        // Ask-AI anchor
    expect(html).toContain('class="dg-size-range"'); // size control
    expect(html).toContain('class="dg-caps-toggle"');// captions control
    // and the scripts that drive them (IIFE bodies — prove the <script> wasn't dropped)
    expect(html).toContain("getElementById('_dg-zoom')");      // zoomScript
    expect(html).toContain("querySelector('.dg-size-range')");  // sizeScript
    expect(html).toContain("querySelector('.dg-caps-toggle')"); // captionsScript
  });

  it('with a nonce, every <script> and <style> carries it', () => {
    const html = renderDigDeeperDoc({ ...base, readOnly: true, nonce: 'N0NCE' });
    const scripts = html.match(/<script[^>]*>/g) ?? [];
    const styles = html.match(/<style[^>]*>/g) ?? [];
    expect(scripts.length).toBeGreaterThan(0);
    expect(styles.length).toBeGreaterThan(0);
    for (const tag of [...scripts, ...styles]) expect(tag).toContain('nonce="N0NCE"');
  });
});
```

> The `getElementById('_dg-zoom')` / `querySelector('.dg-size-range')` / `querySelector('.dg-caps-toggle')` strings are the exact IIFE bodies at `render-dig-deeper.ts:365,425,442` — verify they still read that way when implementing, and adjust the literal if the source differs (the point is a script-body marker, not the exact bytes).

- [ ] **Step 2: Run — verify fail**

Run: `npx jest render-dig-deeper-readonly` → suite is found and runs, then FAILs (readOnly/nonce not honored; the readOnly-omit and nonce assertions fail). The no-op-equality test may pass already (params ignored today) — that is fine; it is a regression guard for the implementation step, not a RED signal.

- [ ] **Step 3: Implement — args + partition + nonce**

Add `readOnly?: boolean; nonce?: string;` to the args type and destructure `readOnly = false, nonce`. Then:

```ts
// topBar (render-dig-deeper.ts ~251-261): gate nav-coupled pieces
const summaryLink = readOnly ? '' : (firstStartSec !== null ? digControl('summary', firstStartSec) : `<a class="dig" data-type="summary">↑ summary</a>`);
const expandAllBtn = readOnly ? '' : `<button class="dg-expand-all">⤢ expand all</button>`;
const topBar = `<div class="dg-topbar">${summaryLink} ${expandAllBtn} ${wholeAsk} ${sizeControl} ${capsControl}</div>`;

// per-section control (~280-288): only emit triggers/toggle when NOT readOnly
let control = '';
if (!readOnly) {
  if (isDug) {
    control = ` <a class="dig-toggle">show summary ⌃</a>`;
    if (ms.isStale && startSec !== null) control += ` <a class="dig-refresh" data-section="${startSec}">↻ outdated</a>`;
  } else if (startSec !== null) {
    control = ` <a class="dig-trigger" data-section="${startSec}">dig deeper ▶</a>`;
  }
}
// Ask-AI (self-contained) stays for both modes:
if (startSec !== null) {
  const endSec = sections.slice(i + 1).find((s) => s.startSec !== null)?.startSec ?? null;
  control += ` ${askAi(buildSectionPrompt(videoUrl, startSec, endSec, language), '💬 ask AI')}`;
}

// markup + scripts (~478-479): gate expandAllDialogs + navScript
const dialogs = readOnly ? '' : expandAllDialogs;
const nav = readOnly ? '' : navScript(nonce);
// (in the returned template) — dialogs replaces ${expandAllDialogs}; nav replaces ${navScript()}
```

Thread `nonce` through the head + tail scripts and `<style>`:

```ts
// head:
${themeHeadScript(nonce)}
${sizeHeadScript(nonce)}       // was SIZE_HEAD_SCRIPT const → function
${captionsHeadScript(nonce)}  // was CAPTIONS_HEAD_SCRIPT const → function
<style${nonceAttr(nonce)}>${themeStyleBlock(LIGHT, DARK)}${STRUCTURAL_CSS}${NAV_CSS}${DIG_DOC_CSS}</style>
// tail:
${nav}${themeToggleScript(nonce)}${printListenerScript(nonce)}${zoomScript}${askAiScript}${sizeScript}${captionsScript}
```

Add `${nonceAttr(nonce)}` to the opening tag of each inline `<script>` built in the function (`zoomScript`, `askAiScript`, `sizeScript`, `captionsScript`) — change `` `<script>(function(){…` `` to `` `<script${nonceAttr(nonce)}>(function(){…` ``, body unchanged.

Convert the two module-level head consts (`SIZE_HEAD_SCRIPT` at `render-dig-deeper.ts:201`, `CAPTIONS_HEAD_SCRIPT` at `:210`) into functions that take `nonce`. Mechanical: rename `const SIZE_HEAD_SCRIPT = \`<script>…\`` → `function sizeHeadScript(nonce?: string) { return \`<script${nonceAttr(nonce)}>…\`; }`, keeping the **exact existing script body** between the `<script…>` and `</script>` verbatim; same for `CAPTIONS_HEAD_SCRIPT` → `captionsHeadScript(nonce)`. Update the two call sites in the head template to `${sizeHeadScript(nonce)}` / `${captionsHeadScript(nonce)}`. (Only the opening `<script>` tag gains `${nonceAttr(nonce)}`; the IIFE body is untouched.)

- [ ] **Step 4: Run new tests + the existing render-dig-deeper suite (regression)**

```bash
npx jest render-dig-deeper           # new readOnly tests + ALL existing render-dig-deeper tests PASS
```
Expected: PASS. Behavior 24 (local unchanged) is guarded two ways: (a) the new no-op-equality test proves `readOnly:false/nonce:undefined` is byte-identical to omitting the params; (b) the existing comprehensive `render-dig-deeper*` suite (markup + CSS + script assertions) runs against the default path and catches gross regressions. This is not a full pre/post byte snapshot — if strict byte-identity vs the pre-slice output is later required, add a saved reference-render fixture; for this slice (a) + (b) is the gate.

- [ ] **Step 5: tsc + commit**

```bash
npx tsc --noEmit; echo "EXIT=$?"   # EXIT=0
git add lib/html-doc/render-dig-deeper.ts tests/lib/html-doc/render-dig-deeper-readonly.test.ts
git commit -m "feat(cloud-dig-serving): renderDigDeeperDoc readOnly static mode + CSP nonce (local byte-identical default)"
```

---

## Task 5: html route `type=dig-deeper` cloud branch

Wire the loader + renderer into `serveCloud`, under the summary CSP, html-only.

**Files:**
- Modify: `app/api/html/[id]/route.ts` (`serveCloud`)
- Test: `tests/api/html-dig-serve.test.ts` (or extend the existing html serve test)

**Interfaces:**
- Consumes: T3 `loadDigForServe`, T4 `renderDigDeeperDoc({readOnly:true, nonce})`, `generateNonce`/`buildSummaryCsp` (`lib/html-doc/csp.ts`), `fileResponse` (`lib/html-doc/file-response.ts`).

- [ ] **Step 1: Write the failing tests** (mock `loadDigForServe`, auth, at the route level)

```ts
// tests/api/html-dig-serve.test.ts
// The cloud html route awaits cookies() from next/headers — MUST mock it or the route throws
// before reaching the behavior (every existing cloud route test does this; see tests/api/dig-cloud-route.test.ts:13).
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));

import { GET } from '@/app/api/html/[id]/route';
import * as loader from '@/lib/dig/cloud/load-dig-for-serve';
import * as serveCore from '@/lib/html-doc/serve-summary-core';
import * as supa from '@/lib/supabase/server';

const OLD = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { process.env.STORAGE_BACKEND = OLD; });
afterEach(() => jest.restoreAllMocks());

function mockAuth(user: { id: string } | null) {
  jest.spyOn(supa, 'createServerSupabase').mockReturnValue({ auth: { getUser: async () => ({ data: { user } }) } } as never);
}
const PL = '0d6f76b5-a1ec-4616-aa74-ad8cd4d7e660';
const url = (extra = '') => `http://x/api/html/v?playlist=${PL}&type=dig-deeper${extra}`;
const params = { params: Promise.resolve({ id: 'v' }) };

it('serves dig html with the summary CSP', async () => {
  mockAuth({ id: 'u' });
  jest.spyOn(loader, 'loadDigForServe').mockResolvedValue({
    ok: true, summary: { title: 'T', sections: [{ numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } }] } as never,
    envelope: null, dug: [{ sectionId: 65, startSec: 65, title: 'A', bodyMarkdown: 'body', generatedAt: 'g', genVersion: 3, slides: [] }] as never,
    base: 'base', title: 'T', language: 'en',
  } as never);
  const res = await GET(new Request(url()), params);
  expect(res.status).toBe(200);
  expect(res.headers.get('Content-Type')).toContain('text/html');
  expect(res.headers.get('Content-Security-Policy')).toContain("script-src 'nonce-");
  expect(await res.text()).toContain('body');
});

it('401 for an anonymous request', async () => {
  mockAuth(null);
  const res = await GET(new Request(url()), params);
  expect(res.status).toBe(401);
});

it('rejects format=md on dig with 400', async () => {
  mockAuth({ id: 'u' });
  const res = await GET(new Request(url('&format=md')), params);
  expect(res.status).toBe(400);
});

it('propagates loader 404 (no dig content)', async () => {
  mockAuth({ id: 'u' });
  jest.spyOn(loader, 'loadDigForServe').mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
  const res = await GET(new Request(url()), params);
  expect(res.status).toBe(404);
});

it('still serves summary — reaches the summary branch, not the type gate (regression)', async () => {
  mockAuth({ id: 'u' });
  // Mock the summary loader so the summary branch resolves deterministically. Without this the real
  // resolveOwnedPlaylistKey runs against the bare auth mock (no `.from`) → TypeError → 500, and the
  // assertion would pass for the WRONG reason. A 404 here proves control reached loadSummaryForServe
  // (the summary branch), i.e. the type gate did NOT reject type=summary with a 400.
  const loadSpy = jest.spyOn(serveCore, 'loadSummaryForServe').mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
  const res = await GET(new Request(`http://x/api/html/v?playlist=${PL}&type=summary`), params);
  expect(res.status).toBe(404);
  expect(loadSpy).toHaveBeenCalled();          // summary branch entered
  expect(res.status).not.toBe(400);            // not the unsupported-type gate
});
```

- [ ] **Step 2: Run — verify fail**

Run: `npx jest html-dig-serve` → FAIL (dig type still 400 at `route.ts:29`).

- [ ] **Step 3: Implement — branch in `serveCloud`**

Replace the `type` gate at `route.ts:28-29` and add a dig branch after the auth block (`route.ts:41`). Show the new shape:

```ts
// after: const type = searchParams.get('type');
if (type !== 'summary' && type !== 'dig-deeper') return json({ error: 'unsupported or missing type' }, 400);
// ...unchanged: outputFolder guard (already above), playlist UUID, assertVideoId, auth → user...

// after `if (!user) return json(...401)`:
if (type === 'dig-deeper') {
  // Dig is html-only this slice (no single dig .md).
  if (searchParams.getAll('format').some((f) => f !== 'html')) return json({ error: 'invalid format' }, 400);
  try {
    const load = await loadDigForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return json({ error: load.error }, load.status);
    const nonce = generateNonce();
    const html = renderDigDeeperDoc({
      summary: load.summary, envelope: load.envelope, dug: load.dug,
      readOnly: true, nonce, videoId, language: load.language, mdPath: `${load.base}.md`,
    });
    return fileResponse(html, { kind: 'html', download, base: load.base, title: load.title, cache: 'private, no-store', csp: buildSummaryCsp(nonce) });
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) return json({ error: e.message }, 400);
    logError('html:dig-serve', err);
    return json({ error: 'internal error' }, 500);
  }
}
// ...unchanged summary flow (format/md handling, loadSummaryForServe, resolveAndParse, renderMagazineHtml)...
```

Add imports at the top of the file: `import { loadDigForServe } from '@/lib/dig/cloud/load-dig-for-serve';` and `import { renderDigDeeperDoc } from '@/lib/html-doc/render-dig-deeper';`. `download` is the already-parsed `searchParams.get('download') === '1'`.

> Placement: the `format=md` short-circuit for summary must stay AFTER this dig branch so `type=dig-deeper&format=md` is rejected here, never reaching the summary md path.

- [ ] **Step 4: Run new tests + full html route suite + tsc + commit**

```bash
npx jest html                        # dig + summary regression PASS
npx tsc --noEmit; echo "EXIT=$?"     # EXIT=0
git add app/api/html/\[id\]/route.ts tests/api/html-dig-serve.test.ts
git commit -m "feat(cloud-dig-serving): serve cloud dig HTML at type=dig-deeper (readOnly render, summary CSP, html-only)"
```

---

## Task 6: cloud dig-state branch

Add a `supabase` branch to the dig-state route listing dug section ids.

**Files:**
- Modify: `app/api/videos/[id]/dig-state/route.ts`
- Test: `tests/api/dig-state-cloud.test.ts`

**Interfaces:**
- Consumes: `loadSummaryForServe` (`lib/html-doc/serve-summary-core.ts`) — reused wholesale for owner-assert **+ the same status gate as the html loader** (committed→503, !promoted→404, not-owner→404) + canonical `{base, principal, bundle}`; `assertVideoId` (`lib/index-store.ts`); `createServerSupabase`/`CookieStore` (`lib/supabase/server`), `cookies` (`next/headers`); T2 `blobStore.list`; `DIG_GENERATOR_VERSION`.

**Design note (review v1 H2/H3/M1):** the cloud branch **reuses `loadSummaryForServe`** rather than hand-coding owner-assert + `readIndex` + `base = mdKey.replace(/\.md$/,'')`. This (a) applies the SAME gate as the html serve path — spec §3 Unit C's "owner-assert **+ gate**" — so dig-state 503s while the summary finalizes and 404s an unknown/unpromoted video instead of leaking `200 []`; (b) guarantees `base` agreement with T3 (both use `load.base`), eliminating the divergence risk; (c) avoids the duplicate `getStorageBundle` import and the un-imported `NextResponse` (keep the file's existing `new Response(...)` idiom). Cost: one extra owner-scoped mdBytes read per dig-state call — acceptable (no frontend polls this endpoint in this slice; the poller is the deferred frontend slice).

- [ ] **Step 1: Write the failing tests**

```ts
// tests/api/dig-state-cloud.test.ts
// Cloud branch awaits cookies() — mock next/headers (repo convention).
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));

import { GET } from '@/app/api/videos/[id]/dig-state/route';
import * as serveCore from '@/lib/html-doc/serve-summary-core';
import * as supa from '@/lib/supabase/server';
import { DIG_GENERATOR_VERSION as V } from '@/lib/dig/generate';

const OLD = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { process.env.STORAGE_BACKEND = OLD; });
afterEach(() => jest.restoreAllMocks());

const PL = '0d6f76b5-a1ec-4616-aa74-ad8cd4d7e660';
const params = { params: Promise.resolve({ id: 'v' }) };
function mockAuth(user: { id: string } | null) {
  jest.spyOn(supa, 'createServerSupabase').mockReturnValue({ auth: { getUser: async () => ({ data: { user } }) } } as never);
}
// loadSummaryForServe is reused wholesale — mock its OK result (gate passed) with a fake bundle.
function mockLoadOk(base: string, keys: string[]) {
  jest.spyOn(serveCore, 'loadSummaryForServe').mockResolvedValue({
    ok: true, base, mdBytes: Buffer.from('#'), mdKey: `${base}.md`, title: 'T',
    principal: { id: 'o', indexKey: 'k' } as never, playlistId: PL, video: { id: 'v', language: 'en' } as never,
    bundle: { blobStore: { list: async (_p: unknown, prefix: string) => keys.filter((k) => k.startsWith(prefix)) } } as never,
  } as never);
}

it('lists dug section ids ascending, excluding stale versions', async () => {
  mockAuth({ id: 'u' });
  mockLoadOk('base', [`dig/base/200.r${V}.md`, `dig/base/65.r${V}.md`, `dig/base/9.r${V - 1}.md`]);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ sectionIds: [65, 200] }); // stale r{V-1} excluded, sorted asc
});

it('returns {sectionIds:[]} when nothing is dug (200, not 404)', async () => {
  mockAuth({ id: 'u' });
  mockLoadOk('base', []);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ sectionIds: [] });
});

it('propagates the summary gate: 404 not-owner / unpromoted / unknown video', async () => {
  mockAuth({ id: 'u' });
  jest.spyOn(serveCore, 'loadSummaryForServe').mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(404);
});

it('propagates the summary gate: 503 while the summary is finalizing (committed)', async () => {
  mockAuth({ id: 'u' });
  jest.spyOn(serveCore, 'loadSummaryForServe').mockResolvedValue({ ok: false, status: 503, error: 'not ready, retry' } as never);
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(503);
});

it('401 for anon (before any loader call)', async () => {
  mockAuth(null);
  const spy = jest.spyOn(serveCore, 'loadSummaryForServe');
  const res = await GET(new Request(`http://x/api/videos/v/dig-state?playlist=${PL}`), params);
  expect(res.status).toBe(401);
  expect(spy).not.toHaveBeenCalled();
});

it('400 for a non-UUID playlist (before auth)', async () => {
  mockAuth({ id: 'u' });
  const res = await GET(new Request('http://x/api/videos/v/dig-state?playlist=not-a-uuid'), params);
  expect(res.status).toBe(400);
});
```

- [ ] **Step 2: Run — verify fail**

Run: `npx jest dig-state-cloud` → the suite is found and runs, then FAILs (route is local-only; supabase requests hit the `outputFolder` guard → 400).

- [ ] **Step 3: Implement — dispatch + cloud branch (reusing `loadSummaryForServe`)**

Rename the existing `GET` body to `serveLocal(request, videoId)` (verbatim — the `outputFolder`/`getPrincipal`/`readDugSectionIds` path is unchanged) and add a backend dispatch + a cloud branch that reuses `loadSummaryForServe` for the gate. Keep the file's existing `new Response(JSON.stringify(...))` idiom — do **not** import `NextResponse`, and do **not** re-import `getStorageBundle` (the existing relative import stays for `serveLocal`).

```ts
// app/api/videos/[id]/dig-state/route.ts — ADD these imports (existing imports stay for serveLocal):
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { cookies } from 'next/headers';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

export async function GET(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId); // existing body, renamed, unchanged
}

async function serveCloud(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);
  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400);
  try { assertVideoId(videoId); } catch { return json({ error: 'invalid videoId' }, 400); }

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  // Reuse the html loader's owner-assert + status gate (committed→503, !promoted→404, not-owner→404)
  // and canonical base — identical to loadDigForServe (T3), so both endpoints agree on dig/{base}/.
  const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
  if (!load.ok) return json({ error: load.error }, load.status);

  const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
  const keys = await load.bundle.blobStore.list(load.principal, `dig/${load.base}/`);
  const sectionIds = keys
    .filter((k) => k.endsWith(suffix))                       // current version only (behavior 11)
    .map((k) => k.match(/\/(\d+)\.r\d+\.md$/))
    .filter((m): m is RegExpMatchArray => m !== null)
    .map((m) => parseInt(m[1], 10))
    .sort((a, b) => a - b);                                  // ascending by sectionId (== startSec)
  return json({ sectionIds }, 200);
}
```

> `sectionIds` filters to the current-version suffix, extracts the integer id, and sorts ascending (behaviors 16/17/11). `assertVideoId` and `Params` are already imported by the existing file; add only the four new imports above. A zero-length `keys` (promoted summary, nothing dug) yields `{ sectionIds: [] }` at 200 — behavior 17. An unknown/unpromoted/foreign video never reaches the list: `loadSummaryForServe` returns `!ok` and the gate status is propagated (404/503).

- [ ] **Step 4: Run new tests + full dig-state suite (local regression) + tsc**

```bash
npx jest dig-state                   # cloud + existing local dig-state tests PASS
npx tsc --noEmit; echo "EXIT=$?"     # EXIT=0
```

- [ ] **Step 5: Full suite + commit**

```bash
npm test                             # whole suite green before commit
git add app/api/videos/\[id\]/dig-state/route.ts tests/api/dig-state-cloud.test.ts
git commit -m "feat(cloud-dig-serving): cloud dig-state branch — list current-version dug section ids"
```

---

## Enumerated Behaviors → Task Coverage (traceability)

| Spec behavior | Task |
|---|---|
| 1 serve merged doc | T5 |
| 2 no charge | T3 (rpc-never-called), reinforced T5 |
| 3 anon 401 / 4 not-owner 404 | T5 (401), T3 propagates 404 |
| 5 no dig content 404 | T3, T5 |
| 6 finalizing 503 / 7 unpromoted 404 / 8 corrupt 409 | T3 (serve) + T6 (dig-state) — both propagate from `loadSummaryForServe` |
| 9 model cached / 10 model absent degrade | T3 (`readModelEnvelope` null path) |
| 11 stale version ignored | T3 (serve), T6 (dig-state) |
| 12 slide token → caption | T1, applied T3 |
| 13 format=md → 400 / 14 outputFolder → 400 / 15 bad id | T5 |
| 16 dig-state asc / 17 empty → [] / 18 not-owner 404 | T6 (18 + finalizing/unpromoted via the reused gate) |
| 19 malformed blob skipped | T1 (throws), T3 (catch/skip) |
| 20 local untouched | T4 (default render), T5/T6 (backend dispatch) |
| 21–24 readOnly omits/keeps/nonce/byte-identical | T4 |

---

## Deferred / forward-looking notes

- **CSP + future slide capture (review v1 L2):** `buildSummaryCsp` is `img-src 'none'` + `style-src 'nonce-…'` (no `unsafe-inline` for style *attributes*). Correct for THIS slice — slides become caption text (no `<img>`), and readOnly emits no inline `style="…"` (dialogs omitted, no `cropMap`). But the future **slide-capture** slice will emit data-URI `<img>` (blocked by `img-src 'none'`) and inline `style="…"` on `.dig-slide-crop` (a nonce does not whitelist style attributes). That slice must plan a CSP change or refactor crop styling to classes. Flagged here so it is not discovered at implementation time.

## Execution / Review

After all tasks: whole-branch dual adversarial review (Claude + Codex) to convergence, focused on the money invariant (no charge reachable from dig serve), owner isolation on `blobStore.list`, the `renderDigDeeperDoc` shared-code change (local byte-identical), and version-awareness. Then `superpowers:finishing-a-development-branch` (push → PR → merge is a human gate).
