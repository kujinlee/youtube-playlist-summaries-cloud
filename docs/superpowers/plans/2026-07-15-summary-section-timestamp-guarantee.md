# Summary Section-Timestamp Guarantee — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee every generated summary section (`## N.` and `## Conclusion`) carries a valid `▶ [start–end](url?t=Ns)` line with a unique, strictly-increasing `startSec`, so every section is diggable and ask-AI-able.

**Architecture:** Three ordered layers in the shared generation path (local pipeline + cloud worker). **Layer 1** (opt-in in `resolveTranscriptTokens`, summary path only): a section's own-line `[[TS]]` token dropped by the strictly-increasing LIS is kept and resolved with a clamped `startSec` instead of deleted. **Layer 2** (in `generateSummary`'s bounded loop): the timestamp score criterion becomes per-section ("every section has a `▶`") instead of doc-wide ("≥1 `▶`"), so an omitted-token section triggers a re-roll within the existing budget. **Layer 3** (finalizer): after the loop, any section still missing a `▶` gets one synthesized by interpolating between neighbors. Cheapest layer wins; a section fixed early never reaches a later layer.

**Tech Stack:** TypeScript, Jest + ts-jest. Gemini mocked at the `lib/gemini.ts` boundary. No new dependencies.

## Global Constraints

- **`startSec` IS the dig `sectionId`.** The dig blob key is `dig/{base}/{sectionId}.r9.md` (`DIG_GENERATOR_VERSION=9`). Every section's `startSec` in a doc MUST be **unique** and **strictly increasing** with section order — a collision cross-wires two sections' dig content. This is the hard invariant behind every clamp/interpolation choice.
- **Blast radius — dig output byte-identical.** `resolveTranscriptTokens` (`lib/transcript-timestamps.ts`) is shared with dig generation (`lib/job-queue/dig-handler.ts:112`, `lib/dig/dig-section.ts:64`, which pass a 4th `videoDuration` arg). The Layer-1 change MUST be **opt-in** (new option, default off) so every existing caller — all dig callers — is byte-identical. A golden test locks this.
- **Money invariant.** Layers 1 and 3 are mechanical (zero Gemini cost). Layer 2 adds **no new uncapped spend** — it reuses the existing `MAX_SUMMARY_ATTEMPTS` budget (`lib/gemini-cost.ts`) and `TIMESTAMP_MISS_CAP=2`; it only changes *when* a re-roll is warranted.
- **Mocking boundary.** Mock Gemini at `lib/gemini.ts`. No real API calls in unit or integration tests.
- **Forward-only.** No backfill of already-shipped summaries.
- **Section definition.** "Section" = a `## ` heading in the generated body as split by `parseSummaryMarkdown` (`lib/html-doc/parse.ts`, fence-aware). Covers numbered `## N.` sections and `## Conclusion`. The Quick Reference callout `summaryCore` appends after generation is NOT a generated section.
- **`▶` line format is canonical.** Produced only by `timestampLine(startSec, endSec, videoId)` (`lib/transcript-timestamps.ts:30`) = `▶ [m:ss–m:ss](https://www.youtube.com/watch?v=ID&t=Ns)`. Never hand-format.

### Design note for the adversarial review (must engage)

Layer 1 modifies the shared, already-merged `resolveTranscriptTokens`. Its **only** runtime benefit over relying on Layer 3 alone is avoiding up to `TIMESTAMP_MISS_CAP` (2) re-rolls for the "emitted-but-out-of-order token" case — a one-time ≤2 Gemini-call saving per affected video (summaries are generated once, then cached). The cost is touching sensitive shared code + a mandatory dig byte-identity guard + iterative dual re-review. The spec (approved) includes Layer 1 with that guard. **The review should explicitly weigh whether Layer 1 earns its blast radius, or whether Layers 2+3 alone suffice.** If the review concludes Layer 1 is not worth it, Task 3 is dropped and Task 4 stops passing the opt-in flag — Layers 2+3 still deliver the full guarantee (case (a) then costs ≤2 capped re-rolls before Layer 3 injects).

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `lib/interval-math.ts` (new) | Dependency-free integer-interval primitives (`interpolateStart`, `spreadStarts`). Imported by both `transcript-timestamps.ts` and `summary-section-timestamps.ts` — kept separate to avoid a circular import between them. | 1 |
| `lib/summary-section-timestamps.ts` (new) | Per-section timestamp detection + the Layer-3 injection finalizer. Imports `interval-math` and `timestampLine`. No I/O, no Gemini. | 1, 2 |
| `lib/transcript-timestamps.ts` (modify) | Layer 1: opt-in `keepAllOwnLineTokens` so summary heading tokens dropped by the LIS are kept + clamped, not deleted. Dig callers unchanged. | 3 |
| `lib/gemini.ts` (modify) | Layer 2 (per-section score criterion in the bounded loop) + Layer 3 wiring (call `resolveTranscriptTokens` with the opt-in flag; run `ensureSectionTimestamps` on the chosen summary); update warns. | 4 |
| `tests/integration/summary-section-timestamps.test.ts` (new) | End-to-end through `summaryCore` with mocked Gemini reproducing a dropped section. | 5 |

---

## Task 1: Pure helpers — interval primitives (`interval-math.ts`) + per-section detection

**Files:**
- Create: `lib/interval-math.ts` (primitives) and `lib/summary-section-timestamps.ts` (detection)
- Test: `tests/lib/interval-math.test.ts` and `tests/lib/summary-section-timestamps.test.ts`

**Interfaces:**
- Consumes: `timestampLine` from `lib/transcript-timestamps.ts` (used by Task 2's finalizer; imported into `summary-section-timestamps.ts`).
- Produces:
  - `lib/interval-math.ts`: `interpolateStart(lo: number, hi: number): number`, `spreadStarts(lo: number, hi: number, count: number): number[]`
  - `lib/summary-section-timestamps.ts`: `interface SectionInfo { numeral: string | null; title: string; headingLineIndex: number; hasTimestamp: boolean; startSec: number | null }`, `findSections(markdown: string): SectionInfo[]`, `everySectionHasTimestamp(markdown: string): boolean`

**Why the split:** `transcript-timestamps.ts` (Task 3) needs `spreadStarts`, and `summary-section-timestamps.ts` needs `timestampLine` from `transcript-timestamps.ts`. Putting the primitives in a third dependency-free module (`interval-math.ts`) keeps all imports one-directional (`summary-section-timestamps → {interval-math, transcript-timestamps}`, `transcript-timestamps → interval-math`) — no cycle.

- [ ] **Step 1: Write the failing test for the interval primitives**

```ts
// tests/lib/interval-math.test.ts
import { interpolateStart, spreadStarts } from '@/lib/interval-math';

describe('interpolateStart', () => {
  it('returns the integer midpoint strictly inside (lo, hi)', () => {
    expect(interpolateStart(208, 369)).toBe(288); // 208 + floor(161/2)=208+80
    expect(interpolateStart(0, 10)).toBe(5);
  });
  it('degenerate gap (<2 apart, no integer strictly between) falls back to lo+1', () => {
    expect(interpolateStart(100, 101)).toBe(101); // pathological; unique vs lo preserved
    expect(interpolateStart(100, 100)).toBe(101);
  });
});

describe('spreadStarts', () => {
  it('produces `count` distinct strictly-increasing ints inside (lo, hi)', () => {
    const r = spreadStarts(0, 100, 3);
    expect(r).toHaveLength(3);
    expect(r[0]).toBeGreaterThan(0);
    expect(r[2]).toBeLessThan(100);
    expect(r[0]).toBeLessThan(r[1]);
    expect(r[1]).toBeLessThan(r[2]);
  });
  it('single gap equals the midpoint', () => {
    expect(spreadStarts(208, 369, 1)).toEqual([288]);
  });
  it('degenerate: too many for the interval still stays strictly increasing + unique', () => {
    const r = spreadStarts(10, 12, 5); // no room; must still be unique & increasing
    const sorted = [...r].sort((a, b) => a - b);
    expect(r).toEqual(sorted);
    expect(new Set(r).size).toBe(r.length);
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest interval-math`
Expected: FAIL — `Cannot find module '@/lib/interval-math'`.

- [ ] **Step 3: Implement the primitives**

```ts
// lib/interval-math.ts

/**
 * Integer strictly between lo and hi, as close to the midpoint as possible. Degenerate
 * (hi - lo < 2 → no integer strictly between): returns lo + 1, preserving uniqueness vs lo.
 * Callers needing several distinct values use spreadStarts.
 */
export function interpolateStart(lo: number, hi: number): number {
  const mid = lo + Math.floor((hi - lo) / 2);
  return mid > lo ? mid : lo + 1;
}

/**
 * `count` distinct, strictly-increasing integers in the open interval (lo, hi), spread as evenly as
 * possible. Strict increase + uniqueness are GUARANTEED even in the degenerate case (interval too
 * small): the fallback marches lo+1, lo+2, … which may reach/exceed hi (pathological — real section
 * gaps are minutes). Uniqueness is the load-bearing property (dig-key safety); even spacing is best-effort.
 */
export function spreadStarts(lo: number, hi: number, count: number): number[] {
  const out: number[] = [];
  const step = (hi - lo) / (count + 1);
  let prev = lo;
  for (let k = 1; k <= count; k++) {
    let v = Math.floor(lo + k * step);
    if (v <= prev) v = prev + 1; // enforce strict increase + uniqueness
    out.push(v);
    prev = v;
  }
  return out;
}
```

- [ ] **Step 4: Run the primitive tests — verify they pass**

Run: `npx jest interval-math`
Expected: PASS for the `interpolateStart` and `spreadStarts` blocks.

- [ ] **Step 5: Write the failing test for section detection**

```ts
// tests/lib/summary-section-timestamps.test.ts
import { findSections, everySectionHasTimestamp } from '@/lib/summary-section-timestamps';

const TS = (n: number) => `▶ [0:00–0:00](https://www.youtube.com/watch?v=vid&t=${n}s)`;

describe('findSections / everySectionHasTimestamp', () => {
  it('detects each ## section and whether a ▶ line immediately follows', () => {
    const md = [
      '## 1. Alpha', TS(10), 'prose a', '', '---', '',
      '## 2. Beta', 'prose b (NO timestamp)', '', '---', '',
      '## Conclusion', TS(30), 'wrap',
    ].join('\n');
    const s = findSections(md);
    expect(s.map((x) => x.title)).toEqual(['Alpha', 'Beta', 'Conclusion']);
    expect(s.map((x) => x.hasTimestamp)).toEqual([true, false, true]);
    expect(s[0].startSec).toBe(10);
    expect(s[1].startSec).toBeNull();
    expect(s[0].numeral).toBe('1');
    expect(s[2].numeral).toBeNull();
    expect(everySectionHasTimestamp(md)).toBe(false);
  });

  it('a fully-timestamped doc reports complete', () => {
    const md = ['## 1. Alpha', TS(10), 'a', '', '## Conclusion', TS(30), 'c'].join('\n');
    expect(everySectionHasTimestamp(md)).toBe(true);
  });

  it('ignores ## lines inside fenced code blocks', () => {
    const md = ['## 1. Alpha', TS(10), 'a', '', '```', '## not a heading', '```'].join('\n');
    expect(findSections(md).map((x) => x.title)).toEqual(['Alpha']);
    expect(everySectionHasTimestamp(md)).toBe(true);
  });
});
```

- [ ] **Step 6: Run it — verify it fails**

Run: `npx jest summary-section-timestamps`
Expected: FAIL — `findSections is not a function`.

- [ ] **Step 7: Implement section detection**

```ts
// lib/summary-section-timestamps.ts  (detection lives here; the Task-2 finalizer is appended below)

const FENCE = /^\s*(```|~~~)/;               // matches parse.ts / transcript-timestamps.ts
const HEADING = /^##\s+(.*)$/;
const ORDINAL = /^(\d+)\.\s+(.*)$/;          // "1. Title" → numeral + title
const TS_LINE = /^▶\s+\[/;                   // a resolved timestamp line
const T_PARAM = /[?&]t=(\d+)s/;              // startSec inside the ▶ url

export interface SectionInfo {
  numeral: string | null;
  title: string;
  headingLineIndex: number;
  hasTimestamp: boolean;
  startSec: number | null;
}

/**
 * Fence-aware scan of a summary body. One SectionInfo per `## ` heading (outside fences). A section
 * "has a timestamp" when the FIRST non-blank line after its heading (before the next `## ` or end)
 * is a `▶ [..](..t=Ns)` line — mirroring parse.ts:extractTimeRange, which only accepts the timestamp
 * as the section's first non-blank prose line.
 */
export function findSections(markdown: string): SectionInfo[] {
  const lines = markdown.split('\n');
  const out: SectionInfo[] = [];
  let inFence = false;
  let cur: SectionInfo | null = null;
  let sawBody = false; // seen a non-blank line in the current section yet?

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (FENCE.test(line)) { inFence = !inFence; sawBody = true; continue; }
    if (inFence) { sawBody = true; continue; }

    const h = line.match(HEADING);
    if (h) {
      if (cur) out.push(cur);
      const headingText = h[1].trim();
      const ord = headingText.match(ORDINAL);
      cur = {
        numeral: ord ? ord[1] : null,
        title: ord ? ord[2].trim() : headingText,
        headingLineIndex: i,
        hasTimestamp: false,
        startSec: null,
      };
      sawBody = false;
      continue;
    }

    if (cur && !sawBody && line.trim() !== '') {
      // first non-blank line of the section
      sawBody = true;
      if (TS_LINE.test(line)) {
        cur.hasTimestamp = true;
        const t = line.match(T_PARAM);
        cur.startSec = t ? parseInt(t[1], 10) : null;
      }
    }
  }
  if (cur) out.push(cur);
  return out;
}

export function everySectionHasTimestamp(markdown: string): boolean {
  const s = findSections(markdown);
  return s.length > 0 && s.every((x) => x.hasTimestamp);
}
```

- [ ] **Step 8: Run all Task-1 tests — verify pass**

Run: `npx jest interval-math summary-section-timestamps`
Expected: PASS (both files, all blocks).

- [ ] **Step 9: Commit**

```bash
git add lib/interval-math.ts tests/lib/interval-math.test.ts lib/summary-section-timestamps.ts tests/lib/summary-section-timestamps.test.ts
git commit -m "feat(summary-ts): interval-math primitives + per-section timestamp detection"
```

---

## Task 2: Layer 3 finalizer — `ensureSectionTimestamps`

**Files:**
- Modify: `lib/summary-section-timestamps.ts` (append)
- Test: `tests/lib/summary-section-timestamps.test.ts` (append)

**Interfaces:**
- Consumes: `findSections`, `spreadStarts` (Task 1); `timestampLine` (`lib/transcript-timestamps.ts`).
- Produces: `ensureSectionTimestamps(markdown: string, videoId: string, bounds: { firstStart: number; videoDuration: number }): string`

**Behavior (spec §5 Layer 3, §8 E3/E4/E5/E9, §9 #7–#10, #12):** For every section lacking a `▶`, insert one immediately after its heading line. The new `startSec` is interpolated strictly between the nearest *known* neighbor starts (a section that already has a `▶`), with `firstStart` (transcript start) as the lower bound before the first known start and `videoDuration` as the upper bound after the last. Consecutive missing sections between the same two anchors are spread to distinct increasing values. Each inserted line's `endSec` = the next section's start (known or interpolated), or `videoDuration` for the last. Existing `▶` lines are never touched. A fully-timestamped doc is returned unchanged (idempotent).

- [ ] **Step 1: Write the failing tests**

```ts
// append to tests/lib/summary-section-timestamps.test.ts
import { ensureSectionTimestamps } from '@/lib/summary-section-timestamps';

const startsOf = (md: string) =>
  findSections(md).map((s) => s.startSec);

describe('ensureSectionTimestamps', () => {
  const bounds = { firstStart: 0, videoDuration: 1000 };

  it('idempotent no-op when every section already has a ▶', () => {
    const md = ['## 1. A', TS(10), 'a', '', '## Conclusion', TS(30), 'c'].join('\n');
    expect(ensureSectionTimestamps(md, 'vid', bounds)).toBe(md);
  });

  it('injects a midpoint ▶ for a middle section missing one (the 9nh8 case)', () => {
    const md = ['## 1. A', TS(208), 'a', '', '## 2. B', 'b', '', '## 3. C', TS(369), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', bounds);
    expect(everySectionHasTimestamp(out)).toBe(true);
    expect(startsOf(out)).toEqual([208, 288, 369]); // 288 = midpoint(208,369)
    // existing lines preserved verbatim
    expect(out).toContain(TS(208));
    expect(out).toContain(TS(369));
  });

  it('first section missing → interpolates from firstStart bound', () => {
    const md = ['## 1. A', 'a', '', '## 2. B', TS(400), 'b'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', { firstStart: 0, videoDuration: 1000 });
    const starts = startsOf(out);
    expect(starts[0]).toBeGreaterThanOrEqual(0);
    expect(starts[0]).toBeLessThan(400);
    expect(starts[1]).toBe(400);
    expect(everySectionHasTimestamp(out)).toBe(true);
  });

  it('last/Conclusion missing → interpolates up to videoDuration', () => {
    const md = ['## 1. A', TS(100), 'a', '', '## Conclusion', 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', { firstStart: 0, videoDuration: 1000 });
    const starts = startsOf(out);
    expect(starts[1]).toBeGreaterThan(100);
    expect(starts[1]).toBeLessThan(1000);
    expect(everySectionHasTimestamp(out)).toBe(true);
  });

  it('multiple consecutive missing sections get distinct increasing starts', () => {
    const md = ['## 1. A', TS(100), 'a', '', '## 2. B', 'b', '', '## 3. C', 'c', '', '## 4. D', TS(500), 'd'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', bounds);
    const starts = startsOf(out) as number[];
    expect(everySectionHasTimestamp(out)).toBe(true);
    for (let i = 1; i < starts.length; i++) expect(starts[i]).toBeGreaterThan(starts[i - 1]); // strict increase
    expect(new Set(starts).size).toBe(starts.length); // unique (dig-key safety)
  });

  it('inserted ▶ end = next section start (or duration for the last)', () => {
    const md = ['## 1. A', TS(208), 'a', '', '## 2. B', 'b', '', '## 3. C', TS(369), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', bounds);
    // section 2 start=288, end=369 → its ▶ label spans to 6:09
    expect(out).toContain('t=288s');
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest summary-section-timestamps`
Expected: FAIL — `ensureSectionTimestamps is not a function`.

- [ ] **Step 3: Implement `ensureSectionTimestamps`**

First add the imports at the top of `lib/summary-section-timestamps.ts`:
```ts
import { spreadStarts } from './interval-math';
import { timestampLine } from './transcript-timestamps';
```

Then append the finalizer:
```ts
// append to lib/summary-section-timestamps.ts

/**
 * Layer-3 finalizer: guarantee every section has a ▶ by synthesizing one for any that lacks it.
 * A synthesized startSec is interpolated strictly between the nearest KNOWN neighbor starts (sections
 * that already carry a ▶), bounded by `firstStart` (before the first known) and `videoDuration`
 * (after the last). Consecutive missing sections between the same anchors are spread to distinct,
 * strictly-increasing values (dig-key uniqueness). Existing ▶ lines are left byte-identical.
 * Returns the input unchanged when nothing is missing.
 */
export function ensureSectionTimestamps(
  markdown: string,
  videoId: string,
  bounds: { firstStart: number; videoDuration: number },
): string {
  const sections = findSections(markdown);
  if (sections.length === 0 || sections.every((s) => s.hasTimestamp)) return markdown;

  // 1. Resolve a start for EVERY section, left→right, filling gaps between known anchors.
  const starts: number[] = new Array(sections.length);
  let i = 0;
  let prevKnown = bounds.firstStart - 1; // exclusive lower anchor; -1 so firstStart itself is usable
  while (i < sections.length) {
    if (sections[i].hasTimestamp) {
      starts[i] = sections[i].startSec as number;
      prevKnown = starts[i];
      i++;
      continue;
    }
    // gap: [i .. j) consecutive missing sections until the next known (or end)
    let j = i;
    while (j < sections.length && !sections[j].hasTimestamp) j++;
    const lo = prevKnown;                                   // exclusive
    const hi = j < sections.length ? (sections[j].startSec as number) : bounds.videoDuration; // exclusive
    const filled = spreadStarts(lo, hi, j - i);
    for (let k = i; k < j; k++) starts[k] = filled[k - i];
    prevKnown = starts[j - 1];
    i = j;
  }

  // 2. Rebuild the doc, inserting a ▶ line after each missing section's heading.
  //    end = next section's start, or videoDuration for the last section.
  const lines = markdown.split('\n');
  const insertAfter = new Map<number, string>();
  sections.forEach((s, idx) => {
    if (s.hasTimestamp) return;
    const endSec = idx + 1 < sections.length ? starts[idx + 1] : bounds.videoDuration;
    insertAfter.set(s.headingLineIndex, timestampLine(starts[idx], endSec, videoId));
  });

  const out: string[] = [];
  for (let li = 0; li < lines.length; li++) {
    out.push(lines[li]);
    const inject = insertAfter.get(li);
    if (inject !== undefined) out.push(inject);
  }
  return out.join('\n');
}
```

- [ ] **Step 4: Run Task-2 tests — verify pass**

Run: `npx jest summary-section-timestamps`
Expected: PASS (all blocks including Task 1).

- [ ] **Step 5: Commit**

```bash
git add lib/summary-section-timestamps.ts tests/lib/summary-section-timestamps.test.ts
git commit -m "feat(summary-ts): Layer 3 ensureSectionTimestamps finalizer (interpolate missing sections)"
```

---

## Task 3: Layer 1 — opt-in keep+clamp in `resolveTranscriptTokens` (dig byte-identical)

**Files:**
- Modify: `lib/transcript-timestamps.ts:101-185`
- Test: `tests/lib/transcript-timestamps.test.ts` (append; file exists)

**Interfaces:**
- Consumes: `spreadStarts` (Task 1).
- Produces: new optional 5th parameter on `resolveTranscriptTokens`:
  `resolveTranscriptTokens(markdown, segments, videoId, videoDuration_param?, opts?: { keepAllOwnLineTokens?: boolean }): string`
  When `opts.keepAllOwnLineTokens === true`, every own-line `[[TS]]` token that the LIS drops (out-of-order or invalid index) is kept and rewritten to a `▶` line with a clamped start (between kept-neighbor starts, bounded by first segment offset and `videoDuration`), instead of having its line deleted. Default `false` → **byte-identical** to today for all existing (dig) callers.

**Note:** on the summary path every own-line token sits under a `## ` heading (the prompt emits them only there), so "keep all own-line tokens" == "keep all section tokens". Dig callers never set the flag → their inline-citation LIS behavior is unchanged.

- [ ] **Step 1: Write the failing test — kept+clamped tokens (summary opt-in) AND dig byte-identity**

```ts
// append to tests/lib/transcript-timestamps.test.ts
import { resolveTranscriptTokens } from '@/lib/transcript-timestamps';

describe('resolveTranscriptTokens keepAllOwnLineTokens (Layer 1)', () => {
  // segments: index → offset seconds
  const segs = Array.from({ length: 10 }, (_, i) => ({ text: `s${i}`, offset: i * 100, duration: 100 }));
  // duration = 1000. Tokens for 3 headings: idx 2 (200), idx 2 again out-of-order? Use an out-of-order case:
  const md = ['## 1. A', '[[TS:2]]', 'a', '## 2. B', '[[TS:1]]', 'b', '## 3. C', '[[TS:5]]', 'c'].join('\n');
  // Offsets in doc order: 200, 100, 500. LIS of strictly-increasing = [200,500] → token for B (100) is dropped today.

  it('DEFAULT (no opts): out-of-order token line is deleted (unchanged legacy behavior)', () => {
    const out = resolveTranscriptTokens(md, segs, 'vid'); // 3-arg legacy call
    expect(out).toContain('t=200s');
    expect(out).toContain('t=500s');
    expect(out).not.toMatch(/t=100s/);         // B dropped
    expect(out).not.toContain('[[TS:');         // no raw token leaks
  });

  it('keepAllOwnLineTokens: B is KEPT with a clamped start between 200 and 500, monotonic + unique', () => {
    const out = resolveTranscriptTokens(md, segs, 'vid', undefined, { keepAllOwnLineTokens: true });
    // every heading now has a ▶
    const starts = [...out.matchAll(/t=(\d+)s/g)].map((m) => Number(m[1]));
    expect(starts).toHaveLength(3);
    for (let i = 1; i < starts.length; i++) expect(starts[i]).toBeGreaterThan(starts[i - 1]); // strict increase
    expect(new Set(starts).size).toBe(3);       // unique
    expect(starts[0]).toBe(200);
    expect(starts[2]).toBe(500);
    expect(starts[1]).toBeGreaterThan(200);
    expect(starts[1]).toBeLessThan(500);
    expect(out).not.toContain('[[TS:');
  });
});
```

- [ ] **Step 2: Write the dig byte-identity golden test**

```ts
// append to tests/lib/transcript-timestamps.test.ts
describe('resolveTranscriptTokens dig-path byte-identity (blast-radius guard)', () => {
  const segs = Array.from({ length: 6 }, (_, i) => ({ text: `s${i}`, offset: i * 60, duration: 60 }));
  // A representative dig body: inline + own-line tokens, some out-of-order, a fenced block.
  const digMd = [
    'Some prose [[TS:1]] with an inline token that must be stripped.',
    '[[TS:0]]',           // own-line, out of order vs next
    '[[TS:3]]',
    '```', '[[TS:2]] fenced verbatim', '```',
    '[[TS:5]]',
  ].join('\n');

  it('4-arg dig call is unchanged by the new param (default off)', () => {
    // Capture output with the CURRENT (pre-change) call shape; after implementing the opt-in flag
    // this MUST remain identical because dig never sets keepAllOwnLineTokens.
    const out = resolveTranscriptTokens(digMd, segs, 'vid', 360);
    expect(out).toMatchSnapshot('dig-resolve-golden');
  });
});
```

- [ ] **Step 3: Run both — verify state**

Run: `npx jest transcript-timestamps`
Expected: the `keepAllOwnLineTokens` "kept+clamped" test FAILS (flag not implemented; output ignores the 5th arg so B is still dropped). The DEFAULT and dig-golden tests PASS (they capture current behavior — the golden snapshot is written now, pre-change).

- [ ] **Step 4: Implement the opt-in keep+clamp**

Modify `resolveTranscriptTokens` (`lib/transcript-timestamps.ts:101`). Add the param and, after the existing LIS `keptMap` block, fill the non-kept own-line tokens when the flag is set. Then Pass 2 emits a `▶` for those too.

```ts
// signature (line ~101)
export function resolveTranscriptTokens(
  markdown: string,
  segments: TranscriptSegment[],
  videoId: string | null,
  videoDuration_param?: number,
  opts?: { keepAllOwnLineTokens?: boolean },
): string {
```

Add `import { spreadStarts } from './interval-math';` at the top (dependency-free primitive — no cycle with `summary-section-timestamps.ts`).

After the existing `keptMap` population block (after line ~162, still inside `if (globalOk)` is fine, or right after it) add:

```ts
  // Layer 1 (opt-in, summary path): keep every own-line token the LIS dropped, resolving it to a
  // clamped start strictly between its kept neighbors (bounded by first offset and videoDuration),
  // so no section token is ever deleted. Default off → dig callers are byte-identical.
  if (globalOk && opts?.keepAllOwnLineTokens && kept < N) {
    const firstOffset = Math.floor(segments[0].offset);
    // walk tokens in document order; fill runs of non-kept tokens between kept anchors
    let idx = 0;
    let prevStart = firstOffset - 1; // exclusive lower anchor
    while (idx < tokens.length) {
      const anchored = keptMap.get(tokens[idx].lineIndex);
      if (anchored) { prevStart = anchored.start; idx++; continue; }
      let j = idx;
      while (j < tokens.length && !keptMap.has(tokens[j].lineIndex)) j++;
      const lo = prevStart;
      const hi = j < tokens.length ? (keptMap.get(tokens[j].lineIndex) as { start: number }).start : videoDuration;
      const filled = spreadStarts(lo, hi, j - idx);
      for (let k = idx; k < j; k++) {
        const start = filled[k - idx];
        const end = (k + 1 < tokens.length)
          ? (keptMap.get(tokens[k + 1].lineIndex)?.start ?? filled[k + 1 - idx] ?? videoDuration)
          : videoDuration;
        keptMap.set(tokens[k].lineIndex, { start, end });
      }
      prevStart = keptMap.get(tokens[j - 1].lineIndex)!.start;
      idx = j;
    }
  }
```

Pass 2 (line ~177-179) is unchanged in shape — `keptMap.get(i)` now also returns the clamped entries, so those token lines emit a `▶` instead of `null`. No other edit needed there.

**Important:** the `console.warn` "kept X of N" (lines 164-170) should not fire misleadingly when the flag kept everything. Guard it:

```ts
  if (N > 0) {
    const effectivelyKept = keptMap.size;               // includes clamped when flag on
    if (!globalOk || effectivelyKept === 0) {
      console.warn(`resolveTranscriptTokens: dropped all ${N} timestamp tokens (invalid indices or missing videoId/segments)`);
    } else if (effectivelyKept < N) {
      console.warn(`resolveTranscriptTokens: kept ${effectivelyKept} of ${N} timestamp tokens (dropped ${N - effectivelyKept} out-of-range/out-of-order)`);
    }
  }
```

(Replace the `kept`-based comparison at lines 164-170 with `keptMap.size`. When the flag is off, `keptMap.size === kept`, so the message is byte-identical for dig callers.)

- [ ] **Step 5: Run — verify all pass, dig golden unchanged**

Run: `npx jest transcript-timestamps`
Expected: PASS — kept+clamped test passes; DEFAULT test still passes; **dig golden snapshot matches (byte-identical)**. If the golden fails, the dig path was altered — STOP and fix the guard before proceeding.

- [ ] **Step 6: Run the dig handler/section tests — confirm no regression**

Run: `npx jest dig`
Expected: PASS (dig callers pass no flag → unchanged).

- [ ] **Step 7: Commit**

```bash
git add lib/transcript-timestamps.ts tests/lib/transcript-timestamps.test.ts tests/lib/__snapshots__/transcript-timestamps.test.ts.snap
git commit -m "feat(summary-ts): Layer 1 opt-in keepAllOwnLineTokens in resolveTranscriptTokens (dig byte-identical)"
```

---

## Task 4: Wire Layers 2 + 3 into `generateSummary`

**Files:**
- Modify: `lib/gemini.ts:274-388`
- Test: `tests/lib/gemini-timestamp-guarantee.test.ts` (new — tests the pure scoring/finalizer wiring without a live model)

**Interfaces:**
- Consumes: `everySectionHasTimestamp`, `ensureSectionTimestamps` (Tasks 1-2); `resolveTranscriptTokens` opt-in flag (Task 3).
- Produces: no signature change to `generateSummary`; behavior change only.

**Behavior:**
1. `attempt()` calls `resolveTranscriptTokens(parsed.summary, segments, videoId, undefined, { keepAllOwnLineTokens: true })` (Layer 1 active on the summary path).
2. `scoreSummary`'s timestamp criterion becomes per-section: `!hasSegments || everySectionHasTimestamp(s) ? 1 : 0` (was `hasTimestamp(s)`).
3. After the loop, before returning, run `ensureSectionTimestamps` on the chosen summary (Layer 3) when `hasSegments`, using `firstStart`/`videoDuration` derived from `segments`. Replace the doc-wide `warnTimestampMiss` with a per-section synth warn.

Because Layer 1 fixes the out-of-order case in `attempt()`, a section still missing a `▶` after resolution means the model omitted its token entirely — exactly the case a re-roll can help, and that Layer 3 backstops.

- [ ] **Step 1: Write the failing test for the per-section score criterion**

```ts
// tests/lib/gemini-timestamp-guarantee.test.ts
import { __test } from '@/lib/gemini';

// scoreSummary is not exported today; expose it (and the finalizer wiring) via a __test hook (Step 3).
describe('scoreSummary per-section timestamp criterion', () => {
  const TS = (n: number) => `▶ [0:00–0:00](https://www.youtube.com/watch?v=v&t=${n}s)`;
  const complete = (body: string) => body; // helper for readability

  it('a doc with ONE section missing a ▶ scores NOT timestamp-complete', () => {
    const allTs = ['## 1. A', TS(10), 'a', '', '## Conclusion', TS(30), 'c'].join('\n');
    const oneMissing = ['## 1. A', TS(10), 'a', '', '## Conclusion', 'c'].join('\n');
    const rAll = { summary: allTs, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } } as never;
    const rMiss = { summary: oneMissing, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } } as never;
    expect(__test.scoreSummary(rAll, true)[3]).toBe(1);
    expect(__test.scoreSummary(rMiss, true)[3]).toBe(0); // was 1 under the all-or-nothing check
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest gemini-timestamp-guarantee`
Expected: FAIL — `__test` (or `__test.scoreSummary`) undefined.

- [ ] **Step 3: Implement the wiring**

In `lib/gemini.ts`:

Add imports:
```ts
import { everySectionHasTimestamp, ensureSectionTimestamps } from './summary-section-timestamps';
```

Change `attempt()` (line 356) to activate Layer 1:
```ts
    const summary = resolveTranscriptTokens(parsed.summary, segments, videoId, undefined, { keepAllOwnLineTokens: true });
```

Change `scoreSummary` (line 298-307) timestamp criterion (index 3):
```ts
function scoreSummary(r: GeminiSummaryResponse, hasSegments: boolean): number[] {
  const s = r.summary;
  return [
    checkSummaryCompleteness(s).complete ? 1 : 0,
    (s.match(/^## /gm) ?? []).length,
    /^##\s+(Conclusion|결론)/im.test(s) ? 1 : 0,
    !hasSegments || everySectionHasTimestamp(s) ? 1 : 0,   // per-section, not doc-wide
    s.length,
  ];
}
```

Replace the post-loop timestamp warn (line 387) with the Layer-3 finalizer + synth warn. After `const chosen = best as GeminiSummaryResponse;` and the incompleteness warn block:

```ts
    if (hasSegments) {
      const lastSeg = segments[segments.length - 1];
      const videoDuration = Math.floor(lastSeg.offset + lastSeg.duration);
      const firstStart = Math.floor(segments[0].offset);
      const before = everySectionHasTimestamp(chosen.summary);
      if (!before) {
        chosen.summary = ensureSectionTimestamps(chosen.summary, videoId, { firstStart, videoDuration });
        const missing = (chosen.summary.match(/^## /gm) ?? []).length; // sections total (for the warn)
        console.warn(`[summary-section-ts-synth] ${videoId}: synthesized ▶ for section(s) missing a token after ${attemptsUsed} attempt(s); sections=${missing}`);
      }
    }
    return chosen;
```

Remove the now-unused `warnTimestampMiss` (line 280-282) and `hasTimestamp` (line 274-277) **only if** no other reference remains (grep first — `scoreSummary` was the sole caller of `hasTimestamp`; the post-loop line was the sole caller of `warnTimestampMiss`). Leave `TIMESTAMP_MISS_CAP` and the loop as-is (its `hasTs = score[3] === 1` now means "every section timestamped"; the cap still bounds deterministic omitted-token re-rolls).

Add the test hook at the end of the file:
```ts
export const __test = { scoreSummary };
```

- [ ] **Step 4: Run the unit test — verify pass**

Run: `npx jest gemini-timestamp-guarantee`
Expected: PASS.

- [ ] **Step 5: Run the existing gemini tests — no regression**

Run: `npx jest gemini`
Expected: PASS. If any test asserted the old doc-wide `hasTimestamp` semantics or the `[timestamp-miss]` warn string, update it to the per-section criterion / `[summary-section-ts-synth]` warn — these are intended behavior changes; note each in the review doc.

- [ ] **Step 6: Type-check**

Run: `npx tsc --noEmit` (verify exit 0 by exit code, not piped output)
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add lib/gemini.ts tests/lib/gemini-timestamp-guarantee.test.ts
git commit -m "feat(summary-ts): Layer 2 per-section re-roll criterion + Layer 3 finalizer in generateSummary"
```

---

## Task 5: Integration — full guarantee through `summaryCore` (mocked Gemini)

**Files:**
- Create: `tests/integration/summary-section-timestamps.test.ts`

**Interfaces:**
- Consumes: the real `generateSummary` (`lib/gemini.ts`) with the Gemini **SDK** mocked at `@google/generative-ai` — the exact boundary `tests/lib/gemini.test.ts:16-31` uses (`generateJson` is a co-located export of `lib/gemini.ts`, so it can't be jest-mocked without also mocking `generateSummary`; mock the SDK instead). Layers 1-3 all run for real against the stubbed model body.

**Behavior (spec §9 #11, #12):** a transcript + a mocked model body where one `## ` section's `[[TS]]` token is out-of-order (LIS drops it → Layer 1 keeps+clamps) and another omits its token entirely (→ Layer 2 re-rolls to `TIMESTAMP_MISS_CAP`, then Layer 3 injects). The mock returns the same body every call (a deterministic model). Assert the returned summary has a `▶` for **every** section, all `startSec` unique + strictly increasing, no exception.

- [ ] **Step 1: Write the failing integration test**

```ts
// tests/integration/summary-section-timestamps.test.ts
import { GoogleGenerativeAI } from '@google/generative-ai';
import { generateSummary } from '@/lib/gemini';
import { findSections, everySectionHasTimestamp } from '@/lib/summary-section-timestamps';
import type { TranscriptSegment } from '@/lib/transcript-timestamps';

// Mock the Gemini SDK — the same boundary tests/lib/gemini.test.ts uses.
jest.mock('@google/generative-ai', () => ({
  ...jest.requireActual('@google/generative-ai'),
  GoogleGenerativeAI: jest.fn(),
}));

const mockGenerateContent = jest.fn();
const mockGetGenerativeModel = jest.fn();

beforeEach(() => {
  jest.resetAllMocks();
  mockGetGenerativeModel.mockReturnValue({ generateContent: mockGenerateContent });
  (GoogleGenerativeAI as jest.Mock).mockImplementation(() => ({ getGenerativeModel: mockGetGenerativeModel }));
  process.env.GEMINI_API_KEY = 'test-api-key';
});
afterEach(() => { delete process.env.GEMINI_API_KEY; });

// 12 segments, offsets 0,100,…,1100; videoDuration = 1100 + 100 = 1200.
const segs: TranscriptSegment[] = Array.from({ length: 12 }, (_, i) => ({ text: `seg ${i}`, offset: i * 100, duration: 100 }));

it('every section ends up with a unique, monotonic ▶ when one token is out-of-order and one is omitted', async () => {
  // Alpha idx5→500, Beta idx1→100 (out-of-order, LIS drops → Layer 1 clamps), Gamma no token
  // (→ Layer 2 re-roll ×TIMESTAMP_MISS_CAP → Layer 3 injects), Conclusion idx10→1000.
  const body = [
    '## 1. Alpha', '[[TS:5]]', 'alpha prose', '', '---', '',
    '## 2. Beta', '[[TS:1]]', 'beta prose', '', '---', '',
    '## 3. Gamma', 'gamma prose (no token)', '', '---', '',
    '## Conclusion', '[[TS:10]]', 'wrap',
  ].join('\n');
  mockGenerateContent.mockResolvedValue({
    response: { text: () => JSON.stringify({
      summary: body,
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      videoType: 'Analysis', audience: 'Intermediate', tags: ['a', 'b', 'c'],
      tldr: 'This video explains things.', takeaways: ['x', 'y', 'z'],
    }) },
  });

  const r = await generateSummary(segs, 'en', 'vidABC');

  const sections = findSections(r.summary);
  expect(sections.map((s) => s.title)).toEqual(['Alpha', 'Beta', 'Gamma', 'Conclusion']);
  expect(everySectionHasTimestamp(r.summary)).toBe(true);                 // total coverage (§9 #10/#11)
  const starts = sections.map((s) => s.startSec as number);
  for (let i = 1; i < starts.length; i++) expect(starts[i]).toBeGreaterThan(starts[i - 1]); // strict increase
  expect(new Set(starts).size).toBe(starts.length);                       // unique (dig-key safety)
});
```

- [ ] **Step 2: Run it — verify it fails for the right reason**

Run: `npx jest tests/integration/summary-section-timestamps`
Expected: FAIL — `everySectionHasTimestamp(r.summary)` is `false` (Gamma has no `▶`) once Tasks 1-4 are in place the finalizer fills it. Confirm the failure is the missing-timestamp assertion, not a mock-wiring error (if `GoogleGenerativeAI` isn't invoked, the SDK mock path is wrong).

- [ ] **Step 3: (only if red for the wrong reason) fix the mock wiring**

If the failure is a wiring error rather than the timestamp assertion, align the mock with `tests/lib/gemini.test.ts:16-31` exactly (same `GoogleGenerativeAI`/`getGenerativeModel`/`generateContent` shape). Do not switch to mocking `generateJson` — it is co-located with `generateSummary` in `lib/gemini.ts`.

- [ ] **Step 4: Run — verify pass**

Run: `npx jest tests/integration/summary-section-timestamps`
Expected: PASS — every section timestamped, unique + monotonic. `mockGenerateContent` was called up to `TIMESTAMP_MISS_CAP` (2) times (Gamma's omitted token is deterministic).

- [ ] **Step 5: Full suite + type-check**

Run: `npm test` then `npx tsc --noEmit`
Expected: all green; tsc exit 0. Fix any test that encoded the old doc-wide timestamp semantics (intended change — record in the review doc).

- [ ] **Step 6: Commit**

```bash
git add tests/integration/summary-section-timestamps.test.ts
git commit -m "test(summary-ts): integration — full section-timestamp guarantee through generateSummary"
```

---

## Self-Review (completed against the spec)

**1. Spec coverage:**
- §5 Layer 1 → Task 3 (opt-in keep+clamp). §5 Layer 2 → Task 4 (per-section criterion). §5 Layer 3 → Task 2 (`ensureSectionTimestamps`) wired in Task 4. §5 blast-radius guard → Task 3 dig golden. ✅
- §8 edges: E1 (out-of-order kept) → Task 3; E2/E3 (omitted → re-roll → inject) → Tasks 4-5; E4/E5 (first/last bounds) → Task 2; E6 (degenerate gap) → Task 1 `spreadStarts` degenerate test; E7 (no segments) → `!hasSegments` short-circuit preserved (Task 4); E8 (dig unchanged) → Task 3 golden; E9 (multi-missing) → Task 2 multi-missing test. ✅
- §9 behaviors 1-12 → covered across Tasks 1-5 (see each task's tests). ✅
- §10 money → Task 4 reuses the existing loop/budget; Layers 1,3 mechanical. ✅

**2. Placeholder scan:** Task 5 now mocks the real `@google/generative-ai` SDK boundary (verified against `tests/lib/gemini.test.ts:16-31`); no guessed module paths remain. No `TBD`/`add error handling`/bare "similar to" left.

**3. Type consistency:** `interpolateStart`, `spreadStarts` (in `lib/interval-math.ts`), `SectionInfo`, `findSections`, `everySectionHasTimestamp`, `ensureSectionTimestamps(markdown, videoId, {firstStart, videoDuration})`, and the `resolveTranscriptTokens(..., opts?: { keepAllOwnLineTokens?: boolean })` signature are used identically in every referencing task. Import direction is one-way (`summary-section-timestamps → {interval-math, transcript-timestamps}`, `transcript-timestamps → interval-math`) — no cycle. `ensureSectionTimestamps` mutates `chosen.summary` (a `string` field) in Task 4 — consistent with its `string` return.

**Known follow-through for implementers:** Task 4 may require updating pre-existing gemini tests that asserted the old doc-wide `hasTimestamp`/`[timestamp-miss]` semantics — this is an intended behavior change; record each touched test in the review doc.

---

## Adversarial Review Requirement

This slice modifies **shared, already-merged** code (`resolveTranscriptTokens`, used by both summary and dig) and touches identity/uniqueness (`startSec` = dig `sectionId`). Per `docs/dev-process.md` → Adversarial Review → Iterative Re-Review, **dual review (Codex + Claude) to convergence is mandatory**, and must explicitly engage:
1. The **Design note** trade-off above (does Layer 1 earn its blast radius?).
2. **Dig byte-identity** (Task 3 golden) — the highest-risk regression surface.
3. **Uniqueness/monotonicity** of synthesized `startSec` under multi-missing and degenerate-gap inputs (dig-key collision is the failure mode).
4. Whether the per-section criterion + `TIMESTAMP_MISS_CAP` interaction can cause unwanted extra re-rolls (money).
