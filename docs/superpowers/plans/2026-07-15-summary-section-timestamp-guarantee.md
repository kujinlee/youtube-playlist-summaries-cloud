# Summary Section-Timestamp Guarantee — Implementation Plan (v3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee every generated summary section (`## N.` and `## Conclusion`) carries a valid `▶ [start–end](url?t=Ns)` line, and that across the whole document the section `startSec` values are **unique and strictly increasing**, so every section is diggable and ask-AI-able without dig-key collisions.

**Architecture (v3):** Two layers in the shared generation path. **Layer 2** (score criterion in `generateSummary`'s bounded loop): a candidate is "timestamp-complete" only when **every section has a `▶` AND the section starts are strictly increasing + unique** — so a missing, duplicate, or out-of-order start triggers a re-roll within the existing budget. **Layer 3** (`ensureSectionTimestamps` finalizer): a **full-document normalizer** that assigns every section a unique, strictly-increasing integer `startSec` (keeping the model's real value when it fits, synthesizing otherwise) and **rewrites** any existing `▶` line whose start must change, inserting lines for sections that have none. It runs whenever the document is not already complete — including when every section already has a `▶` but two collide. `resolveTranscriptTokens` is **not touched** (dig unaffected).

**Tech Stack:** TypeScript, Jest + ts-jest. Gemini mocked at the `@google/generative-ai` SDK boundary. No new dependencies.

## Global Constraints

- **`startSec` IS the dig `sectionId`.** Dig blob key `dig/{base}/{sectionId}.r9.md` (`DIG_GENERATOR_VERSION=9`). In one persisted document every section's `startSec` MUST be **unique** and **strictly increasing** with section order — a collision cross-wires two sections' dig content. Tests assert this over the FULL parsed document (`parseSections(out)`), including `endSec > startSec` per section.
- **Existing `▶` starts are NOT unique by construction.** `resolveTranscriptTokens` keeps the LIS of *float* offsets but emits `startSec = Math.floor(offset)` (`transcript-timestamps.ts:156`), so two near-adjacent kept tokens can floor to the same integer → duplicate `startSec` even with every section present. Therefore Layer 2's criterion checks **uniqueness + monotonicity**, and Layer 3 must **rewrite** colliding existing `▶` lines — not merely insert missing ones. Rewriting a `startSec` at generation time is safe: no dig content exists yet.
- **`resolveTranscriptTokens` is NOT modified** (Layer 1 dropped, v1 review). Dig (`lib/job-queue/dig-handler.ts:112`, `lib/dig/dig-section.ts:64`) is byte-identical; its existing tests are the regression guard.
- **Money invariant.** Layer 3 is mechanical (zero Gemini cost). Layer 2 reuses the existing `MAX_SUMMARY_ATTEMPTS` (`lib/gemini-cost.ts`) + `TIMESTAMP_MISS_CAP=2` budget — the cap only *breaks* the loop, never extends it; the ceiling is unchanged. Honest framing: a video that previously early-returned with one un-timestamped/colliding section now re-rolls up to 2×; a call-count test pins it.
- **Checker == render parser.** The criterion and the finalizer derive every "does this section have a start / what is it?" from `parse.ts`'s real `parseSections` (`timeRange`), never a re-implemented `▶` regex — the guarantee cannot disagree with what the renderer gates on.
- **Mocking boundary.** Mock the Gemini SDK at `@google/generative-ai` (per `tests/lib/gemini.test.ts:16-31`). `generateJson` is a co-located export of `lib/gemini.ts` and cannot be mocked without also mocking `generateSummary`. No real API calls.
- **Forward-only.** No backfill.
- **`▶` format is canonical:** produced only by `timestampLine(startSec, endSec, videoId)` (`lib/transcript-timestamps.ts:30`). Never hand-format.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `lib/html-doc/parse.ts` (modify) | Export existing `parseSections` + `isFenceLine` (currently private). No logic change. | 1 |
| `lib/summary-section-timestamps.ts` (new) | `allocateSectionStarts` (pure allocator: unique, strictly-increasing, room-reserving), `sectionStartsComplete` (presence + uniqueness + monotonicity), `ensureSectionTimestamps` (full-document normalizer that rewrites + inserts `▶` lines). | 1, 2 |
| `lib/gemini.ts` (modify) | Layer 2 (score criterion → `sectionStartsComplete`) + Layer 3 wiring (run finalizer on the chosen summary); remove `hasTimestamp`/`warnTimestampMiss`; add synth warn. Migrate affected fixtures. | 3 |
| `tests/lib/gemini-section-timestamp-guarantee.test.ts` (new) | End-to-end regression through `generateSummary` (SDK-mocked); `tests/lib/` so `npm test` runs it (NOT `tests/integration/`). | 3, 4 |

---

## Task 1: Export the parser + `allocateSectionStarts` + `sectionStartsComplete`

**Files:**
- Modify: `lib/html-doc/parse.ts` (add `export` to `parseSections` and `isFenceLine`)
- Create: `lib/summary-section-timestamps.ts`
- Test: `tests/lib/summary-section-timestamps.test.ts`

**Interfaces produced:**
- `allocateSectionStarts(known: (number|null)[], firstStart: number, videoDuration: number): number[]`
- `sectionStartsComplete(markdown: string): boolean`
- (re-export) `parseSections`, `isFenceLine` from `lib/html-doc/parse.ts`

**`allocateSectionStarts` contract:** returns `n` integers, one per section, **strictly increasing** (hence unique). Keeps `known[i]` when it fits strictly after the previous assigned value and leaves room for the remaining sections below `videoDuration`; otherwise synthesizes a value (toward the next known anchor for spacing) clamped into the valid window. Guarantees `out[i] < out[i+1]` and, when `videoDuration > n + firstStart`, `out[n-1] < videoDuration`. In the pathological case (fewer seconds than sections) it stays strictly increasing (`prev+1`) even if that exceeds `videoDuration`.

- [ ] **Step 1: Write the failing tests for `allocateSectionStarts`**

```ts
// tests/lib/summary-section-timestamps.test.ts
import { allocateSectionStarts, sectionStartsComplete } from '@/lib/summary-section-timestamps';

const strictlyIncreasing = (a: number[]) => a.every((v, i) => i === 0 || v > a[i - 1]);

describe('allocateSectionStarts', () => {
  const D = 1000; // videoDuration

  it('all-known-good → returned unchanged (byte-identity in the common case)', () => {
    expect(allocateSectionStarts([100, 200, 300], 0, D)).toEqual([100, 200, 300]);
  });

  it('missing middle → synthesized strictly between neighbors', () => {
    const r = allocateSectionStarts([208, null, 369], 0, D);
    expect(r[0]).toBe(208); expect(r[2]).toBe(369);
    expect(r[1]).toBeGreaterThan(208); expect(r[1]).toBeLessThan(369);
    expect(strictlyIncreasing(r)).toBe(true);
  });

  it('duplicate known (floor collision) → the later one is reassigned upward, unique', () => {
    const r = allocateSectionStarts([100, 100, 400], 0, D);
    expect(r[0]).toBe(100);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(3);
  });

  it('non-monotonic known → later value reassigned to restore strict increase', () => {
    const r = allocateSectionStarts([100, 50, 200], 0, D);
    expect(strictlyIncreasing(r)).toBe(true);
  });

  it('tight gap: [100, missing, 101] → the colliding known 101 is bumped, all unique', () => {
    const r = allocateSectionStarts([100, null, 101], 0, D);
    expect(r[0]).toBe(100);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(3);
  });

  it('first missing → bounded at/after firstStart; last missing → below videoDuration', () => {
    const first = allocateSectionStarts([null, 400], 0, D);
    expect(first[0]).toBeGreaterThanOrEqual(0); expect(first[0]).toBeLessThan(400);
    const last = allocateSectionStarts([100, null], 0, D);
    expect(last[1]).toBeGreaterThan(100); expect(last[1]).toBeLessThan(D);
  });

  it('all missing → strictly increasing, unique, within (firstStart, videoDuration)', () => {
    const r = allocateSectionStarts([null, null, null], 0, D);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(3);
    expect(r[r.length - 1]).toBeLessThan(D);
  });

  it('pathological (more sections than seconds) stays strictly increasing + unique', () => {
    const r = allocateSectionStarts([null, null, null, null], 0, 2);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(4);
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest summary-section-timestamps`
Expected: FAIL — `Cannot find module '@/lib/summary-section-timestamps'`.

- [ ] **Step 3: Implement `allocateSectionStarts`**

```ts
// lib/summary-section-timestamps.ts
import { parseSections, isFenceLine } from './html-doc/parse';
import { timestampLine } from './transcript-timestamps';

/**
 * Assign a unique, strictly-increasing integer startSec to every section. `known[i]` is the section's
 * existing (floored) startSec, or null if it has no resolvable ▶. A known value is kept when it fits
 * strictly after the previous assigned value AND leaves room (1s each) for the remaining sections below
 * videoDuration; otherwise a value is synthesized toward the next known anchor and clamped into the
 * valid window [lower, hi]. Because every out[i] >= prev+1, the result is strictly increasing and unique.
 * Pathological input (fewer seconds than sections) still returns strictly-increasing unique values.
 */
export function allocateSectionStarts(
  known: (number | null)[],
  firstStart: number,
  videoDuration: number,
): number[] {
  const n = known.length;
  const out: number[] = new Array(n);
  let prev = firstStart - 1; // exclusive lower anchor → first section may take firstStart
  for (let i = 0; i < n; i++) {
    const lower = prev + 1;
    const upper = videoDuration - 1 - (n - 1 - i); // reserve 1s for each remaining section, stay < duration
    const hi = Math.max(lower, upper);             // never below lower (pathological clamp)
    const k = known[i];
    let s: number;
    if (k !== null && k >= lower && k <= hi) {
      s = k;                                        // keep the model's real timestamp
    } else {
      let nextK: number | null = null;             // nearest following known start, for spacing
      for (let j = i + 1; j < n; j++) if (known[j] !== null) { nextK = known[j]; break; }
      const ceil = nextK !== null && nextK - 1 < hi ? Math.max(lower, nextK - 1) : hi;
      const target = lower + Math.floor((ceil - lower) / 2);
      s = Math.min(Math.max(target, lower), hi);
    }
    out[i] = s;
    prev = s;
  }
  return out;
}
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest summary-section-timestamps`
Expected: PASS (the `allocateSectionStarts` block).

- [ ] **Step 5: Export the parser (no logic change)**

In `lib/html-doc/parse.ts` add `export` to the two private declarations (no other change):
```ts
export function isFenceLine(line: string): boolean {   // was: function isFenceLine
```
```ts
export function parseSections(body: string): ParsedSection[] {   // was: function parseSections
```
`ParsedSection` (`lib/html-doc/types.ts`) = `{ numeral: string|null; title: string; prose: string; timeRange: SectionTimeRange|null }`; `SectionTimeRange` = `{ startSec: number; endSec: number; label: string; url: string }`.

- [ ] **Step 6: Write the failing test for `sectionStartsComplete`, then implement**

```ts
// append to tests/lib/summary-section-timestamps.test.ts
const TS = (a: number, b: number) => `▶ [0:00–0:00](https://www.youtube.com/watch?v=v&t=${a}s)`; // b unused label
describe('sectionStartsComplete', () => {
  it('true only when every section has a ▶ AND starts are strictly increasing + unique', () => {
    expect(sectionStartsComplete(['## 1. A', TS(10), 'a', '', '## Conclusion', TS(30), 'c'].join('\n'))).toBe(true);
    expect(sectionStartsComplete(['## 1. A', TS(10), 'a', '', '## 2. B', 'b'].join('\n'))).toBe(false);        // missing
    expect(sectionStartsComplete(['## 1. A', TS(10), 'a', '', '## 2. B', TS(10), 'b'].join('\n'))).toBe(false); // duplicate
    expect(sectionStartsComplete(['## 1. A', TS(30), 'a', '', '## 2. B', TS(10), 'b'].join('\n'))).toBe(false); // out of order
  });
  it('malformed ▶ URL counts as missing (render-parser truth)', () => {
    expect(sectionStartsComplete(['## 1. A', '▶ [x](not-a-url?t=10s)', 'a'].join('\n'))).toBe(false);
  });
});
```

```ts
// append to lib/summary-section-timestamps.ts
/** True when the body has ≥1 section, EVERY section resolves a timestamp, and the starts are strictly
 *  increasing (hence unique). Uses the render parser's own truth (parseSections.timeRange). */
export function sectionStartsComplete(markdown: string): boolean {
  const sections = parseSections(markdown);
  if (sections.length === 0) return false;
  let prev = -Infinity;
  for (const s of sections) {
    if (s.timeRange === null) return false;
    if (s.timeRange.startSec <= prev) return false;
    prev = s.timeRange.startSec;
  }
  return true;
}
```

- [ ] **Step 7: Run all Task-1 tests + existing parse tests**

Run: `npx jest summary-section-timestamps parse`
Expected: PASS (export-only parse change; new module green).

- [ ] **Step 8: Commit**

```bash
git add lib/summary-section-timestamps.ts tests/lib/summary-section-timestamps.test.ts lib/html-doc/parse.ts
git commit -m "feat(summary-ts): allocateSectionStarts + sectionStartsComplete + export parseSections/isFenceLine"
```

---

## Task 2: `ensureSectionTimestamps` — full-document normalizer (rewrites + inserts)

**Files:**
- Modify: `lib/summary-section-timestamps.ts` (append)
- Test: `tests/lib/summary-section-timestamps.test.ts` (append)

**Interface produced:** `ensureSectionTimestamps(markdown: string, videoId: string, bounds: { firstStart: number; videoDuration: number }): string`

**Behavior:** If `sectionStartsComplete(markdown)` → return unchanged (byte-identical fast path). Else: compute `known[]` from `parseSections`, run `allocateSectionStarts`, then for each section whose assigned start differs from its existing one (or that has no/malformed `▶` line) **rewrite or insert** its `▶` line (`end` = next section's assigned start, or `videoDuration` for the last). Existing well-formed lines whose start is unchanged are left byte-identical. The `▶`-line location per section is found with the SAME fence-aware, `---`-dropping, first-non-blank-body-line rule the render parser uses (so a malformed `▶` is *replaced*, never duplicated).

- [ ] **Step 1: Write the failing tests**

```ts
// append to tests/lib/summary-section-timestamps.test.ts
import { ensureSectionTimestamps } from '@/lib/summary-section-timestamps';
import { parseSections } from '@/lib/html-doc/parse';

const T = (n: number) => `▶ [0:00–0:00](https://www.youtube.com/watch?v=vid&t=${n}s)`;
const startsOf = (md: string) => parseSections(md).map((s) => s.timeRange?.startSec ?? null);
const B = { firstStart: 0, videoDuration: 1000 };
const uniqueIncreasing = (md: string) => {
  const s = startsOf(md) as number[];
  return s.every((v, i) => v !== null) && s.every((v, i) => i === 0 || v > s[i - 1]) && new Set(s).size === s.length;
};

describe('ensureSectionTimestamps', () => {
  it('idempotent no-op when already complete (unique + increasing)', () => {
    const md = ['## 1. A', T(10), 'a', '', '## Conclusion', T(30), 'c'].join('\n');
    expect(ensureSectionTimestamps(md, 'vid', B)).toBe(md);
  });

  it('missing middle → inserts a ▶ strictly between neighbors; full doc unique+increasing', () => {
    const md = ['## 1. A', T(208), 'a', '', '## 2. B', 'b', '', '## 3. C', T(369), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    const s = startsOf(out) as number[];
    expect(s[0]).toBe(208); expect(s[2]).toBe(369); expect(s[1]).toBeGreaterThan(208); expect(s[1]).toBeLessThan(369);
    expect(out).toContain(T(208));   // unchanged existing line preserved
  });

  it('DUPLICATE existing ▶ (floor collision) → REWRITES the later line, no insert (R2-H1)', () => {
    const md = ['## 1. A', T(100), 'a', '', '## 2. B', T(100), 'b', '', '## 3. C', T(400), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);          // no more duplicate 100
    expect((out.match(/^▶/gm) ?? []).length).toBe(3);  // exactly one ▶ per section (rewrote, not added)
  });

  it('tight gap [100, missing, 101] → known 101 rewritten upward, all unique (R2-B1)', () => {
    const md = ['## 1. A', T(100), 'a', '', '## 2. B', 'b', '', '## 3. C', T(101), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    expect((out.match(/^▶/gm) ?? []).length).toBe(3);
  });

  it('malformed existing ▶ → REPLACED in place, not duplicated', () => {
    const md = ['## 1. A', '▶ [x](not-a-url?t=10s)', 'a', '', '## Conclusion', T(300), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    expect((out.match(/^▶/gm) ?? []).length).toBe(2);  // replaced the malformed one, not added a 2nd
  });

  it('every inserted/rewritten section has endSec > startSec (R2-M2)', () => {
    const md = ['## 1. A', T(208), 'a', '', '## 2. B', 'b', '', '## 3. C', T(369), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    for (const s of parseSections(out)) expect(s.timeRange!.endSec).toBeGreaterThan(s.timeRange!.startSec);
  });

  it('--- divider before the ▶ is respected (render-parser parity)', () => {
    const md = ['## 1. A', '', '---', '', T(10), 'a', '', '## Conclusion', 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    expect(out).toContain(T(10)); // the pre-existing (post---) ▶ was recognized, not treated as missing
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest summary-section-timestamps`
Expected: FAIL — `ensureSectionTimestamps is not a function`.

- [ ] **Step 3: Implement the finalizer**

```ts
// append to lib/summary-section-timestamps.ts

/** Per-section layout matching parseSections exactly: heading line index + the index of the section's
 *  "timestamp slot" line (the first non-blank, non-`---` body line IF it starts with ▶ — well-formed or
 *  not, mirroring parse.ts:extractTimeRange), else null. Same order/count as parseSections. */
function sectionLayout(markdown: string): { headingLine: number; tsLine: number | null }[] {
  const lines = markdown.split('\n');
  const layout: { headingLine: number; tsLine: number | null }[] = [];
  let inFence = false;
  let cur: { headingLine: number; tsLine: number | null } | null = null;
  let sawBody = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (isFenceLine(line)) { inFence = !inFence; if (cur) sawBody = true; continue; }
    if (inFence) { if (cur) sawBody = true; continue; }
    if (/^##\s+/.test(line)) { if (cur) layout.push(cur); cur = { headingLine: i, tsLine: null }; sawBody = false; continue; }
    if (cur && !sawBody) {
      if (/^-{3,}\s*$/.test(line)) continue;   // parse.ts drops pure-dash dividers before the first body line
      if (line.trim() === '') continue;         // skip blanks
      sawBody = true;
      if (line.trimStart().startsWith('▶')) cur.tsLine = i; // the timestamp slot (parse.ts consumes it well-formed or not)
    }
  }
  if (cur) layout.push(cur);
  return layout;
}

/**
 * Full-document normalizer (Layer 3). Guarantees every section has a ▶ whose startSec is unique and
 * strictly increasing across the whole document. Keeps well-formed lines whose start is unchanged
 * (byte-identical); REWRITES existing ▶ lines whose start must change (e.g. floor collisions) and
 * INSERTS lines for sections with none. Returns input unchanged when already complete.
 */
export function ensureSectionTimestamps(
  markdown: string,
  videoId: string,
  bounds: { firstStart: number; videoDuration: number },
): string {
  if (sectionStartsComplete(markdown)) return markdown;

  const sections = parseSections(markdown);
  if (sections.length === 0) return markdown;

  const known = sections.map((s) => (s.timeRange ? s.timeRange.startSec : null));
  const starts = allocateSectionStarts(known, bounds.firstStart, bounds.videoDuration);
  // defensive: allocator already guarantees strict increase; assert + warn if a pathological input slipped.
  for (let i = 1; i < starts.length; i++) {
    if (starts[i] <= starts[i - 1]) {
      console.warn(`[summary-section-ts-degenerate] ${videoId}: non-increasing start at section ${i + 1}`);
      starts[i] = starts[i - 1] + 1;
    }
  }

  const layout = sectionLayout(markdown); // same order/count as `sections`
  const replace = new Map<number, string>();     // lineIndex → rewritten ▶ line
  const insertAfter = new Map<number, string>(); // headingLineIndex → inserted ▶ line
  sections.forEach((s, idx) => {
    const unchanged = known[idx] !== null && known[idx] === starts[idx] && layout[idx].tsLine !== null;
    if (unchanged) return; // well-formed, correct, keep byte-identical
    const endSec = idx + 1 < sections.length ? starts[idx + 1] : bounds.videoDuration;
    const line = timestampLine(starts[idx], endSec, videoId);
    if (layout[idx].tsLine !== null) replace.set(layout[idx].tsLine as number, line); // replace existing slot
    else insertAfter.set(layout[idx].headingLine, line);                              // insert (none present)
  });

  const lines = markdown.split('\n');
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    out.push(replace.has(i) ? (replace.get(i) as string) : lines[i]);
    if (insertAfter.has(i)) out.push(insertAfter.get(i) as string);
  }
  return out.join('\n');
}
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest summary-section-timestamps`
Expected: PASS (all blocks).

- [ ] **Step 5: Commit**

```bash
git add lib/summary-section-timestamps.ts tests/lib/summary-section-timestamps.test.ts
git commit -m "feat(summary-ts): ensureSectionTimestamps full-doc normalizer (rewrites colliding ▶, inserts missing)"
```

---

## Task 3: Wire Layers 2 + 3 into `generateSummary` (+ migrate affected fixtures)

**Files:**
- Modify: `lib/gemini.ts` (`hasTimestamp` 274-277, `warnTimestampMiss` 280-282, `scoreSummary` 293-307, loop 361-388)
- Test: `tests/lib/gemini-section-timestamp-guarantee.test.ts` (new, scoring hook) + migrate fixtures in `tests/lib/gemini.test.ts` and `tests/lib/gemini-response-schema.test.ts`

**Interfaces:** consumes `sectionStartsComplete`, `ensureSectionTimestamps`, `parseSections` (Tasks 1-2). No `generateSummary` signature change.

**Behavior:**
1. `scoreSummary` index 3 → `!hasSegments || sectionStartsComplete(s) ? 1 : 0` (was `hasTimestamp(s)`).
2. After the loop, when `hasSegments && !sectionStartsComplete(chosen.summary)`, run `ensureSectionTimestamps` on `chosen.summary` with `firstStart`/`videoDuration` from `segments`; log `[summary-section-ts-synth]` with the count of sections that lacked/collided a start (computed before mutation).
3. Delete `hasTimestamp` + `warnTimestampMiss`; update the score comment.

- [ ] **Step 1: Write the failing scoring-hook test**

```ts
// tests/lib/gemini-section-timestamp-guarantee.test.ts
import { __test } from '@/lib/gemini';
const TS = (n: number) => `▶ [0:00–0:00](https://www.youtube.com/watch?v=v&t=${n}s)`;
const mk = (body: string) => ({ summary: body, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } } as never);

describe('scoreSummary uniqueness+monotonic timestamp criterion', () => {
  it('index 3 = 0 for missing, duplicate, or out-of-order starts; 1 only when unique+increasing', () => {
    expect(__test.scoreSummary(mk(['## 1. A', TS(10), 'a', '', '## C', TS(30), 'c'].join('\n')), true)[3]).toBe(1);
    expect(__test.scoreSummary(mk(['## 1. A', TS(10), 'a', '', '## C', 'c'].join('\n')), true)[3]).toBe(0);       // missing
    expect(__test.scoreSummary(mk(['## 1. A', TS(10), 'a', '', '## C', TS(10), 'c'].join('\n')), true)[3]).toBe(0); // duplicate
  });
  it('no-segments short-circuits index 3 to 1 (E7)', () => {
    expect(__test.scoreSummary(mk(['## 1. A', 'a', '', '## C', 'c'].join('\n')), false)[3]).toBe(1);
  });
});
```

- [ ] **Step 2: Run — verify it fails** (`npx jest gemini-section-timestamp-guarantee` → `__test` undefined).

- [ ] **Step 3: Implement the wiring in `lib/gemini.ts`**

Add: `import { sectionStartsComplete, ensureSectionTimestamps } from './summary-section-timestamps';` and `import { parseSections } from './html-doc/parse';`

Delete `hasTimestamp` (274-277) and `warnTimestampMiss` (280-282).

`scoreSummary` (293-307) — comment + index 3:
```ts
/** Rank a candidate — complete, #sections, has-conclusion, section-starts-unique-and-increasing, length. */
function scoreSummary(r: GeminiSummaryResponse, hasSegments: boolean): number[] {
  const s = r.summary;
  return [
    checkSummaryCompleteness(s).complete ? 1 : 0,
    (s.match(/^## /gm) ?? []).length,
    /^##\s+(Conclusion|결론)/im.test(s) ? 1 : 0,
    !hasSegments || sectionStartsComplete(s) ? 1 : 0,   // per-section presence + uniqueness + monotonicity
    s.length,
  ];
}
```

Post-loop (replace the `warnTimestampMiss` line 387), after the incompleteness warn:
```ts
    if (hasSegments && !sectionStartsComplete(chosen.summary)) {
      const lastSeg = segments[segments.length - 1];
      const videoDuration = Math.floor(lastSeg.offset + lastSeg.duration);
      const firstStart = Math.floor(segments[0].offset);
      const parsed = parseSections(chosen.summary);
      let prev = -Infinity, bad = 0;
      for (const s of parsed) { const v = s.timeRange?.startSec ?? null; if (v === null || v <= prev) bad++; else prev = v; }
      chosen.summary = ensureSectionTimestamps(chosen.summary, videoId, { firstStart, videoDuration });
      console.warn(`[summary-section-ts-synth] ${videoId}: normalized ${bad} section start(s) after ${attemptsUsed} attempt(s)`);
    }
    return chosen;
```

Add at end of file: `export const __test = { scoreSummary };`

- [ ] **Step 4: Run the scoring test — verify pass** (`npx jest gemini-section-timestamp-guarantee`).

- [ ] **Step 5: Migrate ALL affected `generateSummary` fixtures (comprehensive audit)**

The new per-section criterion makes a fixture "incomplete" whenever a `##` section (given segments) lacks a resolvable, uniquely-increasing `▶`, which drives extra re-rolls that exhaust queued mock responses or invert `▶` assertions. Precedent: `docs/reviews/summary-truncation-resilience-stage2-plan-codex.md` (migrate all `generateSummary` fixtures to complete markdown). Audit `tests/lib/gemini.test.ts` and `tests/lib/gemini-response-schema.test.ts` for every `generateSummary` call; for each fixture whose summary content is **incidental**, make it timestamp-complete (a `[[TS:i]]` under each `## ` incl. Conclusion, with matching segments) OR call with no segments. Then fix the tests that assert the OLD semantics:

1. `tests/lib/gemini.test.ts:320-331` ("out-of-range index → no timestamps"). Old `not.toMatch(/▶|\[\[TS:/)`. **New:** Layer 3 now synthesizes → `expect(result.summary).not.toContain('[[TS:')` and `expect(sectionStartsComplete(result.summary)).toBe(true)` (import it).
2. `tests/lib/gemini.test.ts:354-362` ("both attempts lack ▶"). Old `not.toContain('▶')` + `[timestamp-miss]`. **New:** `expect(sectionStartsComplete(result.summary)).toBe(true)` + `expect(warn).toHaveBeenCalledWith(expect.stringContaining('[summary-section-ts-synth]'))`.
3. `tests/lib/gemini.test.ts:366-375` (asserts `warn.not.toHaveBeenCalledWith('[timestamp-miss]')`). **New:** update the string to `[summary-section-ts-synth]` (else the assertion is vacuous — R2-L3).
4. `tests/lib/gemini.test.ts:473-480` (cap test, asserts `[timestamp-miss] vid1`). **New:** `[summary-section-ts-synth]`; keep the `toHaveBeenCalledTimes(2)` cap assertion.
5. `tests/lib/gemini-response-schema.test.ts:~23,55` (single `mockResolvedValueOnce`, Conclusion lacks a `[[TS]]`). **New:** either give it two segments + a `[[TS:1]]` under Conclusion, or invoke with no segments if timestamp behavior is irrelevant to that test. (Codex R2 High.)

Grep to confirm none missed: `grep -rn "timestamp-miss\|hasTimestamp\|not\.toContain('▶')\|not\.toMatch(/▶" tests/`.

- [ ] **Step 6: Run gemini suite + type-check** (`npx jest gemini` then `npx tsc --noEmit`, verify exit 0). Fix any remaining fixture that runs out of queued responses.

- [ ] **Step 7: Commit**

```bash
git add lib/gemini.ts tests/lib/gemini-section-timestamp-guarantee.test.ts tests/lib/gemini.test.ts tests/lib/gemini-response-schema.test.ts
git commit -m "feat(summary-ts): per-section uniqueness criterion + Layer 3 finalizer in generateSummary; migrate fixtures"
```

---

## Task 4: End-to-end regression through `generateSummary` (SDK-mocked, tests/lib/)

**Files:** append an end-to-end block to `tests/lib/gemini-section-timestamp-guarantee.test.ts` (same file; `tests/lib/`, SDK-mocked, `npm test`-discoverable — NOT `tests/integration/`).

**Behavior (regression):** a transcript + a mocked body where one section's token is out-of-order (LIS drops → missing) and another omits its token; deterministic mock (same body each call). Assert every section has a `▶`, all `startSec` unique + strictly increasing, `endSec > startSec`, no throw, and `mockGenerateContent` called ≤ `TIMESTAMP_MISS_CAP`.

- [ ] **Step 1: Add the end-to-end block**

```ts
// append to tests/lib/gemini-section-timestamp-guarantee.test.ts
import { GoogleGenerativeAI } from '@google/generative-ai';
import { generateSummary } from '@/lib/gemini';
import { parseSections } from '@/lib/html-doc/parse';
import { sectionStartsComplete } from '@/lib/summary-section-timestamps';
import type { TranscriptSegment } from '@/lib/transcript-timestamps';

jest.mock('@google/generative-ai', () => ({ ...jest.requireActual('@google/generative-ai'), GoogleGenerativeAI: jest.fn() }));
const mockGenerateContent = jest.fn();
const mockGetGenerativeModel = jest.fn();

describe('generateSummary end-to-end section-timestamp guarantee', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockGetGenerativeModel.mockReturnValue({ generateContent: mockGenerateContent });
    (GoogleGenerativeAI as jest.Mock).mockImplementation(() => ({ getGenerativeModel: mockGetGenerativeModel }));
    process.env.GEMINI_API_KEY = 'test-api-key';
  });
  afterEach(() => { delete process.env.GEMINI_API_KEY; });

  const segs: TranscriptSegment[] = Array.from({ length: 12 }, (_, i) => ({ text: `seg ${i}`, offset: i * 100, duration: 100 }));

  it('every section gets a unique, monotonic ▶ (out-of-order + omitted tokens)', async () => {
    const body = [
      '## 1. Alpha', '[[TS:5]]', 'alpha', '', '---', '',
      '## 2. Beta', '[[TS:1]]', 'beta', '', '---', '',   // out-of-order → LIS drops → normalizer synthesizes
      '## 3. Gamma', 'gamma (no token)', '', '---', '',   // omitted → re-roll then synthesize
      '## Conclusion', '[[TS:10]]', 'wrap',
    ].join('\n');
    mockGenerateContent.mockResolvedValue({ response: { text: () => JSON.stringify({
      summary: body, ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      videoType: 'Analysis', audience: 'Intermediate', tags: ['a', 'b', 'c'], tldr: 'This video explains things.', takeaways: ['x', 'y', 'z'],
    }) } });

    const r = await generateSummary(segs, 'en', 'vidABC');

    const sections = parseSections(r.summary);
    expect(sections.map((s) => s.title)).toEqual(['Alpha', 'Beta', 'Gamma', 'Conclusion']);
    expect(sectionStartsComplete(r.summary)).toBe(true);
    const starts = sections.map((s) => s.timeRange!.startSec);
    for (let i = 1; i < starts.length; i++) expect(starts[i]).toBeGreaterThan(starts[i - 1]);
    expect(new Set(starts).size).toBe(starts.length);
    for (const s of sections) expect(s.timeRange!.endSec).toBeGreaterThan(s.timeRange!.startSec);
    expect(mockGenerateContent.mock.calls.length).toBeLessThanOrEqual(2); // TIMESTAMP_MISS_CAP (money)
  });
});
```

- [ ] **Step 2: Run — verify pass (regression)** (`npx jest gemini-section-timestamp-guarantee`).

- [ ] **Step 3: Full suite + type-check** (`npm test`; `npx tsc --noEmit` exit 0). This file is under `tests/lib/` so `npm test` includes it.

- [ ] **Step 4: Commit**

```bash
git add tests/lib/gemini-section-timestamp-guarantee.test.ts
git commit -m "test(summary-ts): end-to-end regression — unique/monotonic section ▶ guarantee (SDK-mocked)"
```

---

## Self-Review (v3, against spec + v1/v2 reviews)

**Spec coverage:** invariant (unique + strictly-increasing startSec) → Task 1 `allocateSectionStarts` + Task 2 finalizer, asserted over `parseSections(out)`. Layer 2 → Task 3 `sectionStartsComplete` criterion. Layer 3 → Task 2. Layer 1 dropped (spec addendum). E7 (no segments) → Task 3 `!hasSegments`. E8 (dig) → `resolveTranscriptTokens` untouched. Money → Task 3 honest framing + Task 4 call-count.

**v2 findings resolved:** R2-B1 → `spreadStarts` deleted; allocator never emits `>= hi`; the finalizer **rewrites** the colliding known line (tight-gap test). R2-H1 (floor collision) → `sectionStartsComplete` checks uniqueness → re-roll, and the finalizer rewrites duplicates even when all present (duplicate-`▶` test). R2-M1 → finalizer rewrites existing lines. Codex-High → comprehensive fixture audit incl. `gemini-response-schema.test.ts`. R2-M2 → `endSec > startSec` test. R2-L3 → `:366-375` string updated. R2-L4 / Codex-M → spec addendum. Unsatisfiable `spreadStarts(100,101,1)` test → gone (allocator tests assert achievable contracts). Codex-Low (heading count) → `sectionLayout` shares `parseSections`' enumeration; a `layout[idx]`/`sections[idx]` positional mismatch is structurally impossible (same walk).

**Type consistency:** `allocateSectionStarts(known,firstStart,videoDuration):number[]`, `sectionStartsComplete(md):boolean`, `ensureSectionTimestamps(md,videoId,{firstStart,videoDuration}):string`, `sectionLayout` internal, `parseSections`/`isFenceLine` exports — consistent across tasks. Acyclic imports: `summary-section-timestamps → {html-doc/parse, transcript-timestamps}`; `gemini → {summary-section-timestamps, html-doc/parse}`; `parse.ts` imports neither.

---

## Adversarial Review Requirement

v3 after two converging rounds (v1: 4B+4H → drop Layer 1; v2: 2B+1H → full-doc normalizer). Per `docs/dev-process.md` Iterative Re-Review, **re-review v3** (Codex + Claude): (1) verify R2-B1/R2-H1/R2-M1 are genuinely fixed — the allocator never collides, the finalizer actually rewrites colliding/malformed existing lines, `sectionStartsComplete` catches floor-collisions; (2) hunt new defects — `sectionLayout` vs `parseSections` order/count parity (esp. malformed-`▶`, `---`, EOF, fence, heading-with-no-body), the `replace`/`insertAfter` rebuild, `endSec` correctness when adjacent sections are rewritten, and the fixture migration's completeness. Converge (no new Blocking/High) → notify → SDD.
