# Dig Slide Vertical Auto-Crop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trim the dead vertical band above each dark-themed slide's heading (and the near-black band below its lowest content) at render time, as a non-destructive CSS display-crop, with the lightbox always showing the full original.

**Architecture:** A pure `computeTrim` over two ffmpeg row-brightness profiles (top@120 anchors the bright heading, bottom@40 trims only near-black so dim content incl. footer survives). An async `prepareSlideCropMap` runs in the API route (`renderDigDeeperDoc` stays synchronous) and passes a `Map<absPath, CropBox|null>` into the renderer, whose image rule emits a `<figure>` cover-crop wrapper sized from the slide's **native dimensions**. Results are cached in a per-deck sidecar keyed by file size+mtime+algoVersion.

**Tech Stack:** TypeScript, Next.js, markdown-it, ffmpeg/ffprobe CLIs (already required), Jest+ts-jest (SWC transform), Playwright.

**Design spec:** `docs/superpowers/specs/2026-06-28-dig-slide-autocrop-design.md`
**Adversarial reviews (addressed):** `docs/reviews/spec-dig-slide-autocrop-codex.md`, `docs/reviews/plan-dig-slide-autocrop-codex.md`

## Global Constraints

- **No new npm dependency.** Use `ffmpeg`/`ffprobe` CLIs via `node:child_process` (project pattern; jimp/sharp deliberately absent).
- **Render-only.** No `DIG_GENERATOR_VERSION`/`doc-version` bump, no re-dig, no asset mutation.
- **Non-destructive.** Crop is CSS display-only; the lightbox `<img>` must have no `.dig-slide-crop` ancestor and carry the original data URI.
- **Fail-closed.** Any detection error (ffmpeg/ffprobe failure, length mismatch, malformed cache) → `null` (uncropped render). A crop failure must never throw out of the render path.
- **Spike-locked constants:** `THR_TOP=120`, `THR_BOT=40`, `CONTENT_FRAC=0.004`, `PAD_FRAC=0.015`, `MIN_RETAIN=0.30`, `MIN_TRIM=0.04`, `ALGO_VERSION=1`. `DIG_CROP` env defaults ON; `DIG_CROP=off` disables.
- **Test locations (Jest `testMatch` only sees `tests/**`):** unit/integration tests go under `tests/lib/dig/` and `tests/lib/html-doc/`; E2E under `tests/e2e/` (Playwright `testDir: ./tests/e2e`). New library code stays under `lib/dig/`.
- **Mock the ffmpeg boundary in unit tests;** the single Task-2 integration test invokes real ffmpeg against a committed PNG fixture.
- **Backslashes in this plan's ffmpeg `geq` strings are literal** (single argv via `execFile`, no shell) — type them exactly.

---

### Task 1: `computeTrim` pure function + types + constants

**Files:**
- Create: `lib/dig/slide-crop.ts`
- Test: `tests/lib/dig/slide-crop.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `export interface Trim { trimTop: number; trimBot: number }` (fractions of height ∈ [0,1))
  - `export interface CropBox extends Trim { width: number; height: number }` (native px; produced in Task 2)
  - `export interface ComputeOpts { contentFrac?: number; padFrac?: number; minRetain?: number; minTrim?: number }`
  - `export function computeTrim(topProfile: number[], botProfile: number[], opts?: ComputeOpts): Trim | null`
  - `export const ALGO_VERSION = 1`, `export const THR_TOP = 120`, `export const THR_BOT = 40`

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/dig/slide-crop.test.ts
import { computeTrim } from '../../../lib/dig/slide-crop';

// Build a height-H profile where rows in [from,to) have the given bright fraction.
const prof = (H: number, bands: Array<[number, number, number]>): number[] => {
  const a = new Array(H).fill(0);
  for (const [from, to, frac] of bands) for (let i = from; i < to; i++) a[i] = frac;
  return a;
};

describe('computeTrim', () => {
  const H = 720;

  it('letterboxed bright-heading slide → trims top dead band, keeps content+footer', () => {
    const top = prof(H, [[200, 230, 0.1], [300, 460, 0.2]]);
    const bot = prof(H, [[200, 690, 0.2]]);
    const box = computeTrim(top, bot)!;
    expect(box).not.toBeNull();
    expect(box.trimTop).toBeGreaterThan(0.2);   // ~28% above heading removed
    expect(box.trimTop).toBeLessThan(0.3);
    expect(box.trimBot).toBeLessThan(0.06);      // only near-black below footer
  });

  it('heading flush at top, content to bottom → no/near-zero trim (under MIN_TRIM) → null', () => {
    const top = prof(H, [[2, 30, 0.2], [300, 700, 0.2]]); // bright from row 2
    const bot = prof(H, [[2, 718, 0.2]]);                 // content to near-bottom
    expect(computeTrim(top, bot)).toBeNull();             // pad makes trim < MIN_TRIM
  });

  it('all-dim slide (nothing above THR_TOP) → null', () => {
    expect(computeTrim(prof(H, []), prof(H, [[100, 600, 0.2]]))).toBeNull();
  });

  it('retained band below MIN_RETAIN → null', () => {
    expect(computeTrim(prof(H, [[350, 360, 0.1]]), prof(H, [[350, 360, 0.1]]))).toBeNull();
  });

  it('total trim below MIN_TRIM → null', () => {
    expect(computeTrim(prof(H, [[5, 715, 0.2]]), prof(H, [[5, 715, 0.2]]))).toBeNull();
  });

  it('REGRESSION (160-214-222): dim card content below last bright row is NOT cut', () => {
    const top = prof(H, [[180, 210, 0.1], [300, 430, 0.2]]);
    const bot = prof(H, [[180, 470, 0.2], [660, 695, 0.05]]); // descriptions to 470, footer 660-695
    const box = computeTrim(top, bot)!;
    expect((1 - box.trimBot) * H).toBeGreaterThan(470);  // bottom anchored below the descriptions
  });

  it('mismatched profile lengths → null', () => {
    expect(computeTrim([0, 0, 0], [0, 0])).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest slide-crop.test -t computeTrim`
Expected: FAIL — "Cannot find module '../../../lib/dig/slide-crop'".

- [ ] **Step 3: Write the implementation**

```ts
// lib/dig/slide-crop.ts
export interface Trim { trimTop: number; trimBot: number }
export interface CropBox extends Trim { width: number; height: number }
export interface ComputeOpts { contentFrac?: number; padFrac?: number; minRetain?: number; minTrim?: number }

export const ALGO_VERSION = 1;
export const THR_TOP = 120;            // anchor on the bright heading
export const THR_BOT = 40;             // trim only near-pure-black
const CONTENT_FRAC = 0.004;            // row is "content" if >0.4% of pixels bright
const PAD_FRAC = 0.015;                // padding above/below the content band
const MIN_RETAIN = 0.30;               // kept band < 30% of H → no-op
const MIN_TRIM = 0.04;                 // total trim < 4% → no-op

/**
 * Derive a vertical trim from two per-row bright-fraction profiles.
 * topProfile (high threshold) locates the first bright row; botProfile
 * (low threshold) locates the last non-black row, so dim content/footer survive.
 * Returns trim fractions of height, or null (no-op) when uncertain.
 */
export function computeTrim(
  topProfile: number[],
  botProfile: number[],
  opts: ComputeOpts = {},
): Trim | null {
  const contentFrac = opts.contentFrac ?? CONTENT_FRAC;
  const padFrac = opts.padFrac ?? PAD_FRAC;
  const minRetain = opts.minRetain ?? MIN_RETAIN;
  const minTrim = opts.minTrim ?? MIN_TRIM;

  const H = topProfile.length;
  if (H === 0 || botProfile.length !== H) return null;

  let t = topProfile.findIndex((f) => f > contentFrac);
  if (t < 0) return null;                                   // nothing bright → no-op

  let b = -1;
  for (let i = H - 1; i >= 0; i--) { if (botProfile[i] > contentFrac) { b = i; break; } }
  if (b < 0) return null;

  const pad = Math.round(padFrac * H);
  t = Math.max(0, t - pad);
  b = Math.min(H - 1, b + pad);

  const keepH = b - t + 1;
  if (keepH / H < minRetain) return null;                   // suspect → no-op

  const trimTop = t / H;
  const trimBot = (H - 1 - b) / H;
  if (trimTop + trimBot < minTrim) return null;             // not worth it → no-op

  return { trimTop, trimBot };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest slide-crop.test -t computeTrim`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/dig/slide-crop.ts tests/lib/dig/slide-crop.test.ts
git commit -m "feat(dig): computeTrim pure vertical-crop logic (TDD)"
```

---

### Task 2: ffmpeg/ffprobe wrappers + `resolveCropBox` (fail-closed, native dims)

**Files:**
- Modify: `lib/dig/slide-crop.ts` (append wrappers)
- Test: `tests/lib/dig/slide-crop.integration.test.ts` (real ffmpeg)
- Create fixture: `tests/lib/dig/__fixtures__/letterbox.png`

**Interfaces:**
- Consumes: `computeTrim`, `CropBox`, `THR_TOP`, `THR_BOT` (Task 1).
- Produces:
  - `export async function imageDims(assetPath: string): Promise<{ width: number; height: number }>`
  - `export async function profileRows(assetPath: string, threshold: number): Promise<number[]>`
  - `export async function resolveCropBox(assetPath: string): Promise<CropBox | null>` (Trim + native width/height; needed by the renderer's aspect-ratio)

- [ ] **Step 1: Create the fixture (committed PNG, 1280×720: black bands top/bottom, white bar, gray block)**

```bash
mkdir -p tests/lib/dig/__fixtures__
ffmpeg -y -f lavfi -i color=c=black:s=1280x720 \
  -vf "drawbox=x=300:y=200:w=680:h=20:color=white:t=fill,drawbox=x=300:y=300:w=680:h=160:color=gray:t=fill" \
  -frames:v 1 tests/lib/dig/__fixtures__/letterbox.png
```

- [ ] **Step 2: Write the failing integration test**

```ts
// tests/lib/dig/slide-crop.integration.test.ts
import path from 'node:path';
import { imageDims, profileRows, resolveCropBox, THR_TOP } from '../../../lib/dig/slide-crop';

const FIX = path.join(__dirname, '__fixtures__', 'letterbox.png');

describe('ffmpeg profile (integration — real ffmpeg)', () => {
  it('imageDims returns 1280×720', async () => {
    expect(await imageDims(FIX)).toEqual({ width: 1280, height: 720 });
  });

  it('profileRows length === height, separates white bar from black bands', async () => {
    const rows = await profileRows(FIX, THR_TOP);
    expect(rows.length).toBe(720);
    expect(rows[0]).toBe(0);                                  // black top
    expect(Math.max(...rows.slice(200, 220))).toBeGreaterThan(0); // white bar registers
  });

  it('resolveCropBox crops the dead bands and carries native dims', async () => {
    const box = await resolveCropBox(FIX);
    expect(box).not.toBeNull();
    expect(box!.width).toBe(1280);
    expect(box!.height).toBe(720);
    expect(box!.trimTop).toBeGreaterThan(0.1);
  });

  it('resolveCropBox returns null on a missing/garbage path (fail-closed)', async () => {
    expect(await resolveCropBox('/no/such/file.png')).toBeNull();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npx jest slide-crop.integration`
Expected: FAIL — `imageDims is not a function`.

- [ ] **Step 4: Implement the wrappers**

```ts
// append to lib/dig/slide-crop.ts
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

/** Native pixel dimensions via ffprobe. Throws on failure (callers fail closed). */
export async function imageDims(assetPath: string): Promise<{ width: number; height: number }> {
  const { stdout } = await execFileAsync('ffprobe', [
    '-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', assetPath,
  ]);
  const [w, h] = String(stdout).trim().split('x').map((n) => parseInt(n, 10));
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
    throw new Error(`imageDims: bad output "${stdout}"`);
  }
  return { width: w, height: h };
}

/** Per-row fraction (0..1) of pixels brighter than `threshold`, length = image height. */
export async function profileRows(assetPath: string, threshold: number): Promise<number[]> {
  const vf =
    `format=gray,geq=lum='if(gte(lum(X\\,Y)\\,${threshold})\\,255\\,0)',scale=1:ih:flags=area`;
  const { stdout } = await execFileAsync('ffmpeg', [
    '-v', 'error', '-i', assetPath, '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'gray', '-',
  ], { encoding: 'buffer', maxBuffer: 1 << 24 });
  return Array.from(stdout as Buffer).map((v) => v / 255);
}

/** Resolve a crop box for one asset. Fail-closed: any error or length mismatch → null. */
export async function resolveCropBox(assetPath: string): Promise<CropBox | null> {
  let dims: { width: number; height: number };
  try { dims = await imageDims(assetPath); } catch { return null; }
  let top: number[];
  let bot: number[];
  try {
    [top, bot] = await Promise.all([
      profileRows(assetPath, THR_TOP),
      profileRows(assetPath, THR_BOT),
    ]);
  } catch { return null; }
  if (top.length !== dims.height || bot.length !== dims.height) return null;  // M1: fail closed
  const trim = computeTrim(top, bot);
  return trim ? { ...trim, width: dims.width, height: dims.height } : null;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npx jest slide-crop.integration`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add lib/dig/slide-crop.ts tests/lib/dig/slide-crop.integration.test.ts tests/lib/dig/__fixtures__/letterbox.png
git commit -m "feat(dig): ffmpeg row-profile + resolveCropBox with native dims (fail-closed)"
```

---

### Task 3: Sidecar cache (`lookupOrComputeBox`) — size+mtime key, atomic write, per-path mutex

**Files:**
- Create: `lib/dig/slide-crop-cache.ts`
- Test: `tests/lib/dig/slide-crop-cache.test.ts`

**Interfaces:**
- Consumes: `CropBox`, `ALGO_VERSION`, `resolveCropBox` (Tasks 1–2).
- Produces:
  - `export type CropResult = CropBox | null | 'missing'`
  - `export async function lookupOrComputeBox(assetPath: string, resolve?: (p: string) => Promise<CropBox | null>): Promise<CropResult>` (`resolve` injectable for tests; defaults to `resolveCropBox`).

**Concurrency note (PM1):** the per-path promise chain serializes writes within ONE Node process; `writeFile`-temp + atomic `rename` prevents torn JSON across processes. A cross-process race can drop one entry (last rename wins) — the only consequence is a **recompute** on the next render (deterministic, ~tens of ms). This is acceptable; no inter-process lock (YAGNI). Covered by the "rebuilds on malformed JSON" + idempotency tests below.

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/dig/slide-crop-cache.test.ts
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { lookupOrComputeBox } from '../../../lib/dig/slide-crop-cache';

const box = { trimTop: 0.2, trimBot: 0.05, width: 1280, height: 720 };
const mkAsset = (dir: string, name: string, bytes = 'x') => {
  const p = path.join(dir, name); fs.writeFileSync(p, bytes); return p;
};

describe('lookupOrComputeBox', () => {
  let dir: string;
  beforeEach(() => { dir = fs.mkdtempSync(path.join(os.tmpdir(), 'crop-')); });
  afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

  it('computes once, then serves from cache', async () => {
    const asset = mkAsset(dir, '0-1-2.jpg');
    const resolve = jest.fn().mockResolvedValue(box);
    expect(await lookupOrComputeBox(asset, resolve)).toEqual(box);
    expect(await lookupOrComputeBox(asset, resolve)).toEqual(box);
    expect(resolve).toHaveBeenCalledTimes(1);
    expect(fs.existsSync(path.join(dir, '.crop-cache.json'))).toBe(true);
  });

  it('recomputes when the file changes under the same name (H1 guard)', async () => {
    const asset = mkAsset(dir, '0-1-2.jpg', 'aaa');
    const resolve = jest.fn()
      .mockResolvedValueOnce(box)
      .mockResolvedValueOnce({ ...box, trimTop: 0.3 });
    await lookupOrComputeBox(asset, resolve);
    fs.writeFileSync(asset, 'bbbbbb');
    expect(await lookupOrComputeBox(asset, resolve)).toEqual({ ...box, trimTop: 0.3 });
    expect(resolve).toHaveBeenCalledTimes(2);
  });

  it('caches a null (no-op) result so it is not recomputed', async () => {
    const asset = mkAsset(dir, '0-1-2.jpg');
    const resolve = jest.fn().mockResolvedValue(null);
    await lookupOrComputeBox(asset, resolve);
    await lookupOrComputeBox(asset, resolve);
    expect(resolve).toHaveBeenCalledTimes(1);
  });

  it('returns "missing" for an absent file and writes no cache entry (M3)', async () => {
    const resolve = jest.fn();
    expect(await lookupOrComputeBox(path.join(dir, 'gone.jpg'), resolve)).toBe('missing');
    expect(resolve).not.toHaveBeenCalled();
    expect(fs.existsSync(path.join(dir, '.crop-cache.json'))).toBe(false);
  });

  it('rebuilds on malformed cache JSON instead of throwing', async () => {
    const asset = mkAsset(dir, '0-1-2.jpg');
    fs.writeFileSync(path.join(dir, '.crop-cache.json'), '{ not json');
    const resolve = jest.fn().mockResolvedValue(box);
    expect(await lookupOrComputeBox(asset, resolve)).toEqual(box);
  });

  it('serializes concurrent writes without losing entries', async () => {
    const a1 = mkAsset(dir, '0-1-2.jpg');
    const a2 = mkAsset(dir, '0-3-4.jpg');
    const resolve = jest.fn().mockResolvedValue(box);
    await Promise.all([lookupOrComputeBox(a1, resolve), lookupOrComputeBox(a2, resolve)]);
    const cache = JSON.parse(fs.readFileSync(path.join(dir, '.crop-cache.json'), 'utf8'));
    expect(Object.keys(cache).sort()).toEqual(['0-1-2.jpg', '0-3-4.jpg']);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest slide-crop-cache`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the cache**

```ts
// lib/dig/slide-crop-cache.ts
import fs from 'node:fs';
import path from 'node:path';
import { ALGO_VERSION, resolveCropBox, type CropBox } from './slide-crop';

export type CropResult = CropBox | null | 'missing';

interface CacheEntry { algoVersion: number; size: number; mtimeMs: number; box: CropBox | null }
type CacheFile = Record<string, CacheEntry>;

const writeChains = new Map<string, Promise<void>>();   // per-cache-file serialization
const cachePath = (assetDir: string) => path.join(assetDir, '.crop-cache.json');

function readCache(cf: string): CacheFile {
  try { return JSON.parse(fs.readFileSync(cf, 'utf8')) as CacheFile; }
  catch { return {}; }                                  // missing OR malformed → rebuild
}

function writeEntry(cf: string, name: string, entry: CacheEntry): Promise<void> {
  const prev = writeChains.get(cf) ?? Promise.resolve();
  const next = prev.catch(() => {}).then(() => {
    const cache = readCache(cf);
    cache[name] = entry;
    const tmp = `${cf}.${process.pid}.tmp`;
    try {
      fs.writeFileSync(tmp, JSON.stringify(cache));
      fs.renameSync(tmp, cf);                           // atomic commit
    } catch (e) {
      try { fs.unlinkSync(tmp); } catch { /* ignore */ }
      console.warn('[dig-crop-cache] write failed:', (e as Error).message);
    }
  });
  writeChains.set(cf, next);
  return next;
}

/**
 * Resolve a crop box for `assetPath`, memoized in the per-deck sidecar.
 * 'missing' when the file is absent (caller renders a placeholder).
 * `resolve` injectable for tests; defaults to resolveCropBox.
 */
export async function lookupOrComputeBox(
  assetPath: string,
  resolve: (p: string) => Promise<CropBox | null> = resolveCropBox,
): Promise<CropResult> {
  let st: fs.Stats;
  try { st = fs.statSync(assetPath); } catch { return 'missing'; }

  const dir = path.dirname(assetPath);
  const name = path.basename(assetPath);
  const cf = cachePath(dir);

  const hit = readCache(cf)[name];
  if (hit && hit.algoVersion === ALGO_VERSION && hit.size === st.size && hit.mtimeMs === st.mtimeMs) {
    return hit.box;
  }
  const box = await resolve(assetPath);
  await writeEntry(cf, name, { algoVersion: ALGO_VERSION, size: st.size, mtimeMs: st.mtimeMs, box });
  return box;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest slide-crop-cache`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/dig/slide-crop-cache.ts tests/lib/dig/slide-crop-cache.test.ts
git commit -m "feat(dig): slide-crop sidecar cache (size+mtime key, atomic, serialized)"
```

---

### Task 4: `prepareSlideCropMap` — collect asset refs (markdown-it tokens), dedupe, resolve

**Files:**
- Create: `lib/dig/slide-crop-map.ts`
- Test: `tests/lib/dig/slide-crop-map.test.ts`

**Interfaces:**
- Consumes: `lookupOrComputeBox`/`CropResult` (Task 3), `CropBox` (Task 1), `DugSection` (`lib/dig/companion-doc`, `bodyMarkdown: string`).
- Produces: `export async function prepareSlideCropMap(dug: DugSection[], mdPath: string, lookup?: (p: string) => Promise<CropResult>): Promise<Map<string, CropBox | null>>` (key = resolved abs path; missing omitted; empty when `DIG_CROP=off`).

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/dig/slide-crop-map.test.ts
import path from 'node:path';
import { prepareSlideCropMap } from '../../../lib/dig/slide-crop-map';
import type { DugSection } from '../../../lib/dig/companion-doc';

const mdPath = '/data/deck/raw/275_x-dig-deeper.md';
const docDir = path.dirname(mdPath);
const sec = (bodyMarkdown: string): DugSection =>
  ({ sectionId: 0, title: 't', genVersion: 8, bodyMarkdown } as unknown as DugSection);
const box = { trimTop: 0.2, trimBot: 0.05, width: 1280, height: 720 };

describe('prepareSlideCropMap', () => {
  it('collects assets/ refs, resolves to abs paths, dedupes', async () => {
    const dug = [
      sec('text ![a](assets/v/0-1-2.jpg) more ![dup](assets/v/0-1-2.jpg)'),
      sec('![b](assets/v/0-3-4.jpg)'),
    ];
    const lookup = jest.fn().mockResolvedValue(box);
    const map = await prepareSlideCropMap(dug, mdPath, lookup);
    expect(new Set(map.keys())).toEqual(new Set([
      path.resolve(docDir, 'assets/v/0-1-2.jpg'),
      path.resolve(docDir, 'assets/v/0-3-4.jpg'),
    ]));
    expect(lookup).toHaveBeenCalledTimes(2);
  });

  it('ignores external URLs and path-traversal refs', async () => {
    const dug = [sec('![x](https://e.com/i.png) ![bad](assets/../../etc/passwd)')];
    const lookup = jest.fn().mockResolvedValue(null);
    const map = await prepareSlideCropMap(dug, mdPath, lookup);
    expect(map.size).toBe(0);
    expect(lookup).not.toHaveBeenCalled();
  });

  it('omits missing assets from the map', async () => {
    const lookup = jest.fn().mockResolvedValue('missing');
    const map = await prepareSlideCropMap([sec('![m](assets/v/gone.jpg)')], mdPath, lookup);
    expect(map.size).toBe(0);
  });

  it('returns an empty map when DIG_CROP=off', async () => {
    const prev = process.env.DIG_CROP;
    process.env.DIG_CROP = 'off';
    try {
      const lookup = jest.fn().mockResolvedValue(box);
      const map = await prepareSlideCropMap([sec('![a](assets/v/0-1-2.jpg)')], mdPath, lookup);
      expect(map.size).toBe(0);
      expect(lookup).not.toHaveBeenCalled();
    } finally { process.env.DIG_CROP = prev; }
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest slide-crop-map`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```ts
// lib/dig/slide-crop-map.ts
import path from 'node:path';
import MarkdownIt from 'markdown-it';
import type Token from 'markdown-it/lib/token.mjs';
import type { DugSection } from './companion-doc';
import { lookupOrComputeBox, type CropResult } from './slide-crop-cache';
import type { CropBox } from './slide-crop';

function collectImageSrcs(tokens: Token[], out: string[] = []): string[] {
  for (const tok of tokens) {
    if (tok.type === 'image') { const src = tok.attrGet('src'); if (src) out.push(src); }
    if (tok.children) collectImageSrcs(tok.children, out);
  }
  return out;
}

/**
 * Build the render-time crop map. Mirrors the renderer's inlining rule:
 * only `assets/…` refs resolving inside `<docDir>/assets`. Key = resolved
 * absolute path; missing files omitted. Empty map when DIG_CROP=off.
 */
export async function prepareSlideCropMap(
  dug: DugSection[],
  mdPath: string,
  lookup: (p: string) => Promise<CropResult> = lookupOrComputeBox,
): Promise<Map<string, CropBox | null>> {
  const map = new Map<string, CropBox | null>();
  if (process.env.DIG_CROP === 'off') return map;

  const docDir = path.dirname(mdPath);
  const assetsRoot = path.resolve(docDir, 'assets');
  const md = new MarkdownIt({ html: false });

  const absPaths = new Set<string>();
  for (const section of dug) {
    for (const src of collectImageSrcs(md.parse(section.bodyMarkdown ?? '', {}))) {
      if (!src.startsWith('assets/')) continue;
      const abs = path.resolve(docDir, src);
      if (!abs.startsWith(assetsRoot + path.sep)) continue;   // containment (matches renderer)
      absPaths.add(abs);
    }
  }

  await Promise.all([...absPaths].map(async (abs) => {
    const r = await lookup(abs);
    if (r !== 'missing') map.set(abs, r);
  }));
  return map;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest slide-crop-map`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/dig/slide-crop-map.ts tests/lib/dig/slide-crop-map.test.ts
git commit -m "feat(dig): prepareSlideCropMap — token-walk asset refs → crop map"
```

---

### Task 5: Render integration — native-dim `<figure>` cover-crop + CSS + route wiring

**Files:**
- Modify: `lib/html-doc/render-dig-deeper.ts` (`buildRenderer` sig + image rule ~94-126; `DIG_DOC_CSS` ~135; `renderDigDeeperDoc` sig + destructure ~172-181; call site ~181)
- Modify: `app/api/html/[id]/route.ts` (~195)
- Test: `tests/lib/html-doc/render-dig-deeper.crop.test.ts`

**Interfaces:**
- Consumes: `prepareSlideCropMap` (Task 4), `CropBox` (Task 1).
- Produces: `renderDigDeeperDoc(args)` gains **optional** `cropMap?: Map<string, CropBox | null>` (defaults to `new Map()` → no crop; this keeps all 47 existing call sites compiling unchanged — PH1).

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/html-doc/render-dig-deeper.crop.test.ts
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { renderDigDeeperDoc } from '../../../lib/html-doc/render-dig-deeper';
import type { CropBox } from '../../../lib/dig/slide-crop';

function makeDoc() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'digdoc-'));
  fs.mkdirSync(path.join(dir, 'assets', 'v'), { recursive: true });
  const assetAbs = path.join(dir, 'assets', 'v', '0-1-2.jpg');
  fs.writeFileSync(assetAbs, Buffer.from([0xff, 0xd8, 0xff, 0xd9]));
  return { mdPath: path.join(dir, 'x-dig-deeper.md'), assetAbs };
}

const baseArgs = (mdPath: string, cropMap: Map<string, CropBox | null>) => ({
  summary: { title: 'T', sections: [] } as any,
  envelope: null,
  dug: [{ sectionId: 0, title: 'S', genVersion: 8, bodyMarkdown: '![a](assets/v/0-1-2.jpg)' }] as any,
  mdPath, videoId: 'v', language: 'en' as const, cropMap,
});

describe('renderDigDeeperDoc crop wrapper', () => {
  it('wraps a slide using NATIVE-dim aspect-ratio + object-position', () => {
    const { mdPath, assetAbs } = makeDoc();
    const box: CropBox = { trimTop: 0.25, trimBot: 0.05, width: 1280, height: 720 };
    const html = renderDigDeeperDoc(baseArgs(mdPath, new Map([[assetAbs, box]])));
    expect(html).toContain('class="dig-slide-crop"');
    // keepFrac=0.70 → keepH=504 → aspect 1280/504; object-position 0 83.3%
    expect(html).toMatch(/aspect-ratio:\s*1280\s*\/\s*504/);
    expect(html).toMatch(/object-position:\s*0 83\.3%/);
    expect(html).toContain('<img class="dig-slide"');
  });

  it('renders a plain dig-slide img (no wrapper) when box is null', () => {
    const { mdPath, assetAbs } = makeDoc();
    const html = renderDigDeeperDoc(baseArgs(mdPath, new Map([[assetAbs, null]])));
    expect(html).not.toContain('dig-slide-crop');
    expect(html).toContain('<img class="dig-slide"');
  });

  it('renders plain img when cropMap omitted entirely (default new Map)', () => {
    const { mdPath } = makeDoc();
    const args = baseArgs(mdPath, new Map());
    delete (args as any).cropMap;
    const html = renderDigDeeperDoc(args);
    expect(html).not.toContain('dig-slide-crop');
  });

  it('CSS contract overrides the bare-img cap and scopes cursor to the img', () => {
    const { mdPath, assetAbs } = makeDoc();
    const box: CropBox = { trimTop: 0.25, trimBot: 0.05, width: 1280, height: 720 };
    const html = renderDigDeeperDoc(baseArgs(mdPath, new Map([[assetAbs, box]])));
    expect(html).toMatch(/\.dig-slide-crop\s*>\s*img\.dig-slide\{[^}]*object-fit:cover/);
    expect(html).toMatch(/\.dig-slide-crop\s*>\s*img\.dig-slide\{[^}]*max-height:none/);
    expect(html).toMatch(/\.dig-slide-crop\s*>\s*img\.dig-slide\{[^}]*cursor:zoom-in/);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest render-dig-deeper.crop`
Expected: FAIL — no `dig-slide-crop` in output.

- [ ] **Step 3: Thread `cropMap` into `buildRenderer` and emit the native-dim wrapper**

In `lib/html-doc/render-dig-deeper.ts`:

(a) Add an import near the existing `import type { DugSection }` (line 13):
```ts
import type { CropBox } from '../dig/slide-crop';
```

(b) Change `buildRenderer` (line 87) to take the map:
```ts
function buildRenderer(mdPath: string, cropMap: Map<string, CropBox | null>): MarkdownIt {
```

(c) Replace the success branch of the image rule (the `const b64 = …; return <img …>` at lines 118-119) — keep the containment check (109) and missing-file placeholder (116) exactly:
```ts
      const b64 = data.toString('base64');
      const box = cropMap.get(absPath) ?? null;
      if (box) {
        const keepFrac = 1 - box.trimTop - box.trimBot;
        const keepH = box.height * keepFrac;
        const posPct = (box.trimTop / (box.trimTop + box.trimBot)) * 100;
        const capPx = Math.round(360 * box.width / keepH);   // cap displayed height ≈360px
        const figStyle = `aspect-ratio:${box.width} / ${Math.round(keepH)};width:min(100%,${capPx}px)`;
        return `<figure class="dig-slide-crop" style="${figStyle}">` +
               `<img class="dig-slide" style="object-position:0 ${posPct.toFixed(1)}%" ` +
               `src="data:image/jpeg;base64,${b64}" alt="${esc(altAttr)}"></figure>`;
      }
      return `<img class="dig-slide" src="data:image/jpeg;base64,${b64}" alt="${esc(altAttr)}">`;
```

(d) `renderDigDeeperDoc` args type (172-179): add `cropMap?: Map<string, CropBox | null>;`. Destructure (180) with default:
```ts
  const { summary, envelope, dug, mdPath, videoId, language = 'en', cropMap = new Map<string, CropBox | null>() } = args;
```

(e) Call site (line 181):
```ts
  const renderer = buildRenderer(mdPath, cropMap);
```

- [ ] **Step 4: Add the CSS contract (cursor scoped to the img — PL2)**

In `DIG_DOC_CSS`, immediately after the existing `.dg img.dig-slide{…}` rule (line 135), add:
```ts
.dg figure.dig-slide-crop{display:block;overflow:hidden;margin:2em auto;max-width:100%;border:1px solid var(--rule);border-radius:6px}
.dg figure.dig-slide-crop>img.dig-slide{display:block;width:100%;height:100%;max-height:none;margin:0;border:0;border-radius:0;object-fit:cover;cursor:zoom-in}
```
(The bare `.dg img.dig-slide` rule still applies to un-cropped slides; the wrapped img overrides it. `cursor:zoom-in` is only on the img — the lightbox handler at ~line 310 fires on `img.dig-slide`.)

- [ ] **Step 5: Wire the route**

In `app/api/html/[id]/route.ts`, add the import and build the map before the dig-deeper render (replace line 195):
```ts
import { prepareSlideCropMap } from '../../../../lib/dig/slide-crop-map';
// …in the dig-deeper branch, replacing line 195:
    const cropMap = await prepareSlideCropMap(dug, summaryMdPath);
    return serveHtml(renderDigDeeperDoc({ summary: parsed, envelope, dug, mdPath: summaryMdPath, videoId, language: video.language, cropMap }));
```

- [ ] **Step 6: Run crop tests + full render-dig-deeper suite**

Run: `npx jest render-dig-deeper`
Expected: PASS — new crop tests green; the 31 existing tests still green (they omit `cropMap` → default empty map → unchanged output).

- [ ] **Step 7: Typecheck (jest uses SWC; tsc is the real gate)**

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add lib/html-doc/render-dig-deeper.ts tests/lib/html-doc/render-dig-deeper.crop.test.ts "app/api/html/[id]/route.ts"
git commit -m "feat(dig): non-destructive CSS crop wrapper (native dims) + route wiring"
```

---

### Task 6: E2E — cropped in flow, full original on zoom (L1)

**Files:**
- Create: `tests/e2e/dig-slide-crop.spec.ts` (Playwright `testDir: ./tests/e2e`)

**Pattern:** Mirror `tests/e2e/dig-deeper.spec.ts` — it builds the page HTML by calling `renderDigDeeperDoc(...)` and fulfilling the route with `page.route(...)`. Here we pass a deterministic `cropMap` so one slide is cropped.

**Interfaces:**
- Consumes: `renderDigDeeperDoc` + `CropBox` (relative imports, not `@/` — see the note atop the existing spec).

- [ ] **Step 1: Write the E2E spec**

```ts
// tests/e2e/dig-slide-crop.spec.ts
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { expect, test } from '@playwright/test';
import { renderDigDeeperDoc } from '../../lib/html-doc/render-dig-deeper';
import type { CropBox } from '../../lib/dig/slide-crop';

// 1×1 white JPEG (same minimal fixture style as dig-deeper.spec.ts).
const B64 = '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKwAB/9k=';

function buildHtml(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dig-crop-e2e-'));
  fs.mkdirSync(path.join(dir, 'assets', 'v'), { recursive: true });
  const assetAbs = path.join(dir, 'assets', 'v', '0-1-2.jpg');
  fs.writeFileSync(assetAbs, Buffer.from(B64, 'base64'));
  const cropMap = new Map<string, CropBox | null>([[assetAbs, { trimTop: 0.25, trimBot: 0.05, width: 1280, height: 720 }]]);
  return renderDigDeeperDoc({
    summary: { title: 'Crop Test', sections: [] } as any,
    envelope: null,
    dug: [{ sectionId: 0, title: 'S', genVersion: 8, bodyMarkdown: '![a](assets/v/0-1-2.jpg)' }] as any,
    mdPath: path.join(dir, 'x-dig-deeper.md'),
    videoId: 'v', language: 'en', cropMap,
  });
}

test.beforeEach(async ({ page }) => {
  const html = buildHtml();
  await page.route('**/crop-fixture', (route) => route.fulfill({ contentType: 'text/html', body: html }));
  await page.goto('http://localhost/crop-fixture');
});

test('cropped slide shows a crop wrapper in flow', async ({ page }) => {
  const fig = page.locator('figure.dig-slide-crop').first();
  await expect(fig).toBeVisible();
  await expect(fig).toHaveCSS('overflow', 'hidden');
  await expect(fig.locator('img.dig-slide')).toHaveCSS('object-fit', 'cover');
});

test('clicking a cropped slide opens the lightbox with the FULL uncropped original (L1)', async ({ page }) => {
  const inFlow = page.locator('figure.dig-slide-crop img.dig-slide').first();
  const src = await inFlow.getAttribute('src');
  await inFlow.click();
  const zoom = page.locator('.dg-zoom[data-open] img');
  await expect(zoom).toBeVisible();
  await expect(zoom).toHaveAttribute('src', src!);
  expect(await zoom.evaluate((el) => !!el.closest('.dig-slide-crop'))).toBe(false);
});
```

- [ ] **Step 2: Run the E2E spec**

Run: `npx playwright test dig-slide-crop`
Expected: PASS (2 tests). If the page.route host pattern needs adjustment, mirror exactly how `dig-deeper.spec.ts` fulfills its route.

- [ ] **Step 3: Full suite + typecheck before final commit**

Run: `npm test && npx tsc --noEmit`
Expected: all green, no type errors.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/dig-slide-crop.spec.ts
git commit -m "test(dig): E2E — crop wrapper in flow + full original on zoom (L1)"
```

---

## Self-Review

**Spec coverage:** units 1/2/3 → Tasks 1,2,5 ✓; detection params → Task 1 ✓; caching (H1 size+mtime, H2 atomic+mutex, M3 missing≠no-op, PM1 cross-process documented) → Task 3 ✓; render integration (B2 async map, M2 token walk, B1/PB1 native-dim figure CSS, L3 alt, PL2 cursor) → Tasks 4,5 ✓; `DIG_CROP` default ON + `off` switch → Task 4 + Global Constraints ✓; fail-closed M1 → Task 2 ✓; testing table incl. 160-214-222 regression + heading-flush (PL1) + L1 → Tasks 1,5,6 ✓.

**Placeholder scan:** No TBD/TODO; full code in every code step. E2E host pattern has a single explicit "mirror dig-deeper.spec.ts if needed" note (Step 2), grounded in the confirmed existing pattern.

**Type consistency:** `Trim{trimTop,trimBot}` (computeTrim out) vs `CropBox extends Trim {width,height}` (resolveCropBox out, renderer in) used consistently across Tasks 1-6. `CropResult = CropBox|null|'missing'` (Task 3) consumed by Task 4. `cropMap?: Map<string,CropBox|null>` identical in renderer + route. All producer/consumer signatures match.

**Codex plan-review items:** PB1 (native-dim aspect-ratio) ✓ Task 5; PB2 (test paths under tests/) ✓ all tasks; PH1 (optional cropMap, 47 sites untouched) ✓ Task 5; PH2 (tests/e2e path) ✓ Task 6; PM1 (cross-process documented) ✓ Task 3; PM2 (dim-derived width cap) ✓ Task 5; PM3 (concrete E2E fixture) ✓ Task 6; PL1 (heading-flush test) ✓ Task 1; PL2 (cursor on img) ✓ Task 5.
