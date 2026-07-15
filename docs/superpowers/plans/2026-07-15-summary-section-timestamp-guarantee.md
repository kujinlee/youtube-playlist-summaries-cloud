# Summary Section-Timestamp Guarantee — Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee every generated summary section (`## N.` and `## Conclusion`) carries a valid `▶ [start–end](url?t=Ns)` line with a unique, strictly-increasing `startSec`, so every section is diggable and ask-AI-able.

**Architecture (v2 — Layer 1 dropped per dual review):** Two layers in the shared generation path (local pipeline + cloud worker). **Layer 2** (in `generateSummary`'s bounded loop): the timestamp score criterion becomes per-section ("every section has a `▶`") instead of doc-wide ("≥1 `▶`"), so a section that lost or omitted its `[[TS]]` token triggers a re-roll within the existing `MAX_SUMMARY_ATTEMPTS`/`TIMESTAMP_MISS_CAP` budget. **Layer 3** (finalizer, `ensureSectionTimestamps`): after the loop, any section still missing a `▶` gets one synthesized by interpolating a unique, strictly-increasing `startSec` between neighbors. `resolveTranscriptTokens` is **not touched** (dig unaffected).

**Tech Stack:** TypeScript, Jest + ts-jest. Gemini mocked at the `@google/generative-ai` SDK boundary. No new dependencies.

## Global Constraints

- **`startSec` IS the dig `sectionId`.** Dig blob key `dig/{base}/{sectionId}.r9.md` (`DIG_GENERATOR_VERSION=9`). Every section's `startSec` in one doc MUST be **unique** and **strictly increasing** with section order — a collision cross-wires two sections' dig content. This is the hard invariant behind every interpolation choice; tests assert it over the FULL set (existing + synthesized starts), and every synthesized start MUST land strictly inside `(prevStart, nextStart)`.
- **`resolveTranscriptTokens` is NOT modified.** Layer 1 was dropped (v1 review, unanimous). Because the only source of `▶` lines remains that function's strictly-increasing LIS, existing `▶` starts are unique + increasing by construction; the finalizer only *adds* the missing ones. Dig (`lib/job-queue/dig-handler.ts:112`, `lib/dig/dig-section.ts:64`) is unaffected — its existing tests are the regression guard.
- **Money invariant.** Layer 3 is mechanical (zero Gemini cost). Layer 2 reuses the existing `MAX_SUMMARY_ATTEMPTS` (`lib/gemini-cost.ts`) + `TIMESTAMP_MISS_CAP=2` budget. **Honest framing:** for a video where the model omits/misorders exactly one section token, *expected* successful attempts rises from 1 → up to 2 (ceiling unchanged at `MAX_SUMMARY_ATTEMPTS`). A call-count test pins this.
- **Checker must equal the render parser.** The per-section check and the finalizer both derive "does this section have a timestamp?" from `parse.ts`'s real `parseSections` (`timeRange !== null`), never a re-implemented regex — so the guarantee can't disagree with what the renderer gates on.
- **Mocking boundary.** Mock the Gemini SDK at `@google/generative-ai` (per `tests/lib/gemini.test.ts:16-31`). `generateJson` is a co-located export of `lib/gemini.ts` and cannot be mocked without also mocking `generateSummary`. No real API calls.
- **Forward-only.** No backfill of already-shipped summaries.
- **Section definition.** A `## ` heading in the generated body as split by `parseSections` (fence-aware, drops pure `---` dividers). Covers `## N.` and `## Conclusion`. The Quick Reference callout `summaryCore` appends after generation is not a generated section.
- **`▶` format is canonical:** produced only by `timestampLine(startSec, endSec, videoId)` (`lib/transcript-timestamps.ts:30`). Never hand-format.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `lib/interval-math.ts` (new) | `spreadStarts(lo, hi, count)` — `count` distinct, strictly-increasing integers **strictly inside** `(lo, hi)`. Dependency-free. | 1 |
| `lib/html-doc/parse.ts` (modify) | Export the existing `parseSections` and `isFenceLine` (currently module-private) so the checker/finalizer reuse the real parser instead of re-implementing it. No logic change. | 1 |
| `lib/summary-section-timestamps.ts` (new) | `everySectionHasTimestamp` (Layer 2 criterion) + `ensureSectionTimestamps` (Layer 3 finalizer). Both built on `parseSections` + `spreadStarts` + `timestampLine`. | 2 |
| `lib/gemini.ts` (modify) | Layer 2 (per-section score criterion) + Layer 3 wiring (run `ensureSectionTimestamps` on the chosen summary); remove `hasTimestamp`/`warnTimestampMiss`; add synth warn; update the 3 affected tests. | 3 |
| `tests/lib/gemini-section-timestamp-guarantee.test.ts` (new) | End-to-end regression through `generateSummary` with the SDK mocked (reproduces dropped + omitted sections). Homed under `tests/lib/` so `npm test` runs it (NOT `tests/integration/`, which needs a live Supabase stack). | 4 |

---

## Task 1: `spreadStarts` primitive + export the real parser

**Files:**
- Create: `lib/interval-math.ts`
- Modify: `lib/html-doc/parse.ts` (add `export` to `parseSections` and `isFenceLine` — no logic change)
- Test: `tests/lib/interval-math.test.ts`

**Interfaces:**
- Produces: `spreadStarts(lo: number, hi: number, count: number): number[]`
- Produces (re-export): `export function parseSections(...)`, `export function isFenceLine(...)` from `lib/html-doc/parse.ts`.

**`spreadStarts` contract:** returns `count` distinct integers, strictly increasing, each **strictly inside `(lo, hi)`** (so a synthesized start never equals an anchor at `lo` or `hi`). Precondition `hi - lo - 1 >= count` is guaranteed by the caller (real section anchors are minutes/hundreds-of-seconds apart). In the pathological no-room case the result stays strictly-increasing + unique (dig-key safety is load-bearing) but may reach `hi-1`; the caller (`ensureSectionTimestamps`, Task 2) detects and warns.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/interval-math.test.ts
import { spreadStarts } from '@/lib/interval-math';

describe('spreadStarts', () => {
  it('returns `count` distinct strictly-increasing ints STRICTLY inside (lo, hi)', () => {
    const r = spreadStarts(0, 100, 3);
    expect(r).toHaveLength(3);
    for (const v of r) { expect(v).toBeGreaterThan(0); expect(v).toBeLessThan(100); }
    expect(r[0]).toBeLessThan(r[1]);
    expect(r[1]).toBeLessThan(r[2]);
  });

  it('single gap lands strictly inside and near the midpoint', () => {
    const [v] = spreadStarts(208, 369, 1);
    expect(v).toBeGreaterThan(208);
    expect(v).toBeLessThan(369);
  });

  it('never returns a value equal to or past the upper anchor (B1 regression)', () => {
    // The v1 bug: spreadStarts(10,12,5) -> [11,12,13,14,15]. hi=12 must never appear, nor >12.
    const r = spreadStarts(10, 12, 5);
    for (const v of r) expect(v).toBeLessThan(12);       // strictly < hi
    // strictly increasing + unique still hold even when room is insufficient
    const sorted = [...r].sort((a, b) => a - b);
    expect(r).toEqual(sorted);
    expect(new Set(r).size).toBe(r.length);
  });

  it('single tight gap (100,101,1) does NOT collide with the anchor 101 (B1 regression)', () => {
    const [v] = spreadStarts(100, 101, 1);
    expect(v).toBeLessThan(101);   // must NOT be 101 (the next section start)
    expect(v).toBeGreaterThan(100);
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest interval-math`
Expected: FAIL — `Cannot find module '@/lib/interval-math'`.

- [ ] **Step 3: Implement `spreadStarts`**

```ts
// lib/interval-math.ts

/**
 * `count` distinct, strictly-increasing integers, each STRICTLY inside the open interval (lo, hi).
 * Even spacing. Because every result is strictly < hi and strictly > lo, a synthesized value can
 * never equal an anchor at lo or hi — the property that keeps synthesized section starts from
 * colliding with real ones (dig-key uniqueness).
 *
 * Precondition (guaranteed by callers): hi - lo - 1 >= count. Real section anchors are far apart,
 * so this holds. In the pathological no-room case the result stays strictly-increasing + unique
 * (load-bearing) but may reach hi-1; ensureSectionTimestamps (Task 2) verifies the full-document
 * invariant afterward and warns if a degenerate input forced a boundary hit.
 */
export function spreadStarts(lo: number, hi: number, count: number): number[] {
  const out: number[] = [];
  let prev = lo;
  for (let k = 1; k <= count; k++) {
    // even target inside (lo, hi)
    const target = lo + Math.round((k * (hi - lo)) / (count + 1));
    let v = target;
    if (v <= prev) v = prev + 1;   // strict increase + uniqueness
    if (v >= hi) v = hi - 1;        // hard exclusive upper bound — never touch/exceed the anchor
    if (v <= prev) v = prev + 1;    // if the clamp collapsed it (no room), keep strictly increasing
    out.push(v);
    prev = v;
  }
  return out;
}
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest interval-math`
Expected: PASS. (In the no-room `spreadStarts(10,12,5)` case the values are `[11, …]` strictly-increasing unique and all `< 12` up to the point room runs out; the assertion `< hi` holds because the final `v = hi - 1` clamp caps at 11 and the strict-increase fallback only advances when room exists — see Step 5 note.)

> **Note for the implementer:** verify the `spreadStarts(10,12,5)` case actually satisfies "all `< 12`". With `lo=10, hi=12`: only integer strictly inside is `11`. The contract cannot return 5 distinct ints `< 12` — this is the impossible-room case. Make the test assert the *reachable* guarantee: values are strictly increasing, unique, and **the first `min(count, hi-lo-1)` are `< hi`**; document that beyond that the input is degenerate (unreachable for real anchors). Adjust the Step-1 test's `spreadStarts(10,12,5)` block to assert `expect(r[0]).toBe(11)` and that the full-document guard in Task 2 (not this primitive) owns the degenerate policy. **Do not let this primitive silently emit a value ≥ hi in any case that has room.**

- [ ] **Step 5: Export the real parser (no logic change)**

In `lib/html-doc/parse.ts`, add `export` to the two currently-private declarations:
```ts
export function isFenceLine(line: string): boolean {   // was: function isFenceLine
  return /^\s*(```|~~~)/.test(line);
}
```
```ts
export function parseSections(body: string): ParsedSection[] {   // was: function parseSections
```
No other change. `ParsedSection` (`lib/html-doc/types.ts`) is `{ numeral: string | null; title: string; prose: string; timeRange: SectionTimeRange | null }`; `SectionTimeRange` is `{ startSec: number; endSec: number; label: string; url: string }`.

- [ ] **Step 6: Run the existing parse tests — no regression**

Run: `npx jest parse`
Expected: PASS (export-only change).

- [ ] **Step 7: Commit**

```bash
git add lib/interval-math.ts tests/lib/interval-math.test.ts lib/html-doc/parse.ts
git commit -m "feat(summary-ts): spreadStarts primitive (strictly-inside interval) + export parseSections/isFenceLine"
```

---

## Task 2: `everySectionHasTimestamp` + `ensureSectionTimestamps` (the finalizer authority)

**Files:**
- Create: `lib/summary-section-timestamps.ts`
- Test: `tests/lib/summary-section-timestamps.test.ts`

**Interfaces:**
- Consumes: `parseSections`, `isFenceLine` (`lib/html-doc/parse.ts`); `spreadStarts` (`lib/interval-math.ts`); `timestampLine` (`lib/transcript-timestamps.ts`).
- Produces:
  - `everySectionHasTimestamp(markdown: string): boolean`
  - `ensureSectionTimestamps(markdown: string, videoId: string, bounds: { firstStart: number; videoDuration: number }): string`

**`everySectionHasTimestamp`:** `parseSections(md)` then `sections.length > 0 && sections.every(s => s.timeRange !== null)`. Uses the render parser's own truth, so it can never disagree with the renderer (fixes v1 B4/H1/L6).

**`ensureSectionTimestamps` (Layer 3, the single authority for the invariant):** for every section with `timeRange === null`, insert a `▶` line immediately after its heading. Synthesized `startSec` is allocated left→right so the FULL document sequence (existing + synthesized) is unique + strictly increasing: known starts anchor; a run of missing sections between anchors `lo`/`hi` is filled by `spreadStarts(lo, hi, m)` (strictly inside, so no collision with anchors). `firstStart` bounds a leading run; `videoDuration` bounds a trailing run. Each inserted line's `endSec` = the next section's start (existing or synthesized) or `videoDuration`. A fully-timestamped doc is returned unchanged. After building, assert the full set is strictly increasing + unique; warn `[summary-section-ts-degenerate]` if a pathological tiny-gap input forced a violation (never for real anchors).

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/summary-section-timestamps.test.ts
import { everySectionHasTimestamp, ensureSectionTimestamps } from '@/lib/summary-section-timestamps';
import { parseSections } from '@/lib/html-doc/parse';

const TS = (n: number) => `▶ [0:00–0:00](https://www.youtube.com/watch?v=vid&t=${n}s)`;
const startsOf = (md: string) => parseSections(md).map((s) => s.timeRange?.startSec ?? null);
const bounds = { firstStart: 0, videoDuration: 1000 };

describe('everySectionHasTimestamp (via the real parser)', () => {
  it('true only when every section has a resolvable ▶', () => {
    expect(everySectionHasTimestamp(['## 1. A', TS(10), 'a', '', '## Conclusion', TS(30), 'c'].join('\n'))).toBe(true);
    expect(everySectionHasTimestamp(['## 1. A', TS(10), 'a', '', '## 2. B', 'b'].join('\n'))).toBe(false);
  });

  it('agrees with the render parser on a malformed ▶ URL (v1 B4)', () => {
    // parse.ts requires https?:// — a bad URL yields timeRange:null, so the section is "missing".
    const md = ['## 1. A', '▶ [bad](not-a-url?t=10s)', 'prose'].join('\n');
    expect(parseSections(md)[0].timeRange).toBeNull();
    expect(everySectionHasTimestamp(md)).toBe(false);
  });

  it('agrees with the render parser when a --- divider precedes the ▶ (v1 H1)', () => {
    const md = ['## 1. A', '', '---', '', TS(10), 'prose'].join('\n'); // parse.ts drops --- → sees ▶
    expect(parseSections(md)[0].timeRange?.startSec).toBe(10);
    expect(everySectionHasTimestamp(md)).toBe(true);
  });
});

describe('ensureSectionTimestamps', () => {
  it('idempotent no-op when every section already has a ▶', () => {
    const md = ['## 1. A', TS(10), 'a', '', '## Conclusion', TS(30), 'c'].join('\n');
    expect(ensureSectionTimestamps(md, 'vid', bounds)).toBe(md);
  });

  it('middle section missing → synthesized start strictly between neighbors, full set unique+increasing', () => {
    const md = ['## 1. A', TS(208), 'a', '', '## 2. B', 'b', '', '## 3. C', TS(369), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', bounds);
    expect(everySectionHasTimestamp(out)).toBe(true);
    const s = startsOf(out) as number[];
    expect(s[0]).toBe(208); expect(s[2]).toBe(369);
    expect(s[1]).toBeGreaterThan(208); expect(s[1]).toBeLessThan(369); // strictly inside
    expect(out).toContain(TS(208)); expect(out).toContain(TS(369));    // existing lines untouched
  });

  it('first section missing → bounded by firstStart; last/Conclusion missing → bounded by videoDuration', () => {
    const first = ensureSectionTimestamps(['## 1. A', 'a', '', '## 2. B', TS(400), 'b'].join('\n'), 'vid', bounds);
    const fs = startsOf(first) as number[];
    expect(fs[0]).toBeGreaterThanOrEqual(0); expect(fs[0]).toBeLessThan(400);
    const last = ensureSectionTimestamps(['## 1. A', TS(100), 'a', '', '## Conclusion', 'c'].join('\n'), 'vid', bounds);
    const ls = startsOf(last) as number[];
    expect(ls[1]).toBeGreaterThan(100); expect(ls[1]).toBeLessThan(1000);
  });

  it('multiple consecutive missing → all distinct, strictly increasing, full set unique (dig-key safety)', () => {
    const md = ['## 1. A', TS(100), 'a', '', '## 2. B', 'b', '', '## 3. C', 'c', '', '## 4. D', TS(500), 'd'].join('\n');
    const s = startsOf(ensureSectionTimestamps(md, 'vid', bounds)) as number[];
    for (let i = 1; i < s.length; i++) expect(s[i]).toBeGreaterThan(s[i - 1]);
    expect(new Set(s).size).toBe(s.length);
    expect(s[1]).toBeGreaterThan(100); expect(s[2]).toBeLessThan(500);
  });

  it('all sections missing (no known anchors) → firstStart..videoDuration span, unique+increasing', () => {
    const md = ['## 1. A', 'a', '', '## 2. B', 'b', '', '## Conclusion', 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', bounds);
    expect(everySectionHasTimestamp(out)).toBe(true);
    const s = startsOf(out) as number[];
    for (let i = 1; i < s.length; i++) expect(s[i]).toBeGreaterThan(s[i - 1]);
    expect(new Set(s).size).toBe(s.length);
  });

  it('inserted ▶ end = next section start (or duration for the last); end > start always', () => {
    const md = ['## 1. A', TS(208), 'a', '', '## 2. B', 'b', '', '## 3. C', TS(369), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', bounds);
    // section 2's start ∈ (208,369) and its end = 369 (next start) → start < end
    const m = out.match(/t=(\d+)s/g)!.map((x) => Number(x.match(/\d+/)![0]));
    expect(m).toContain(208); expect(m).toContain(369);
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest summary-section-timestamps`
Expected: FAIL — `Cannot find module '@/lib/summary-section-timestamps'`.

- [ ] **Step 3: Implement the module**

```ts
// lib/summary-section-timestamps.ts
import { parseSections, isFenceLine } from './html-doc/parse';
import { spreadStarts } from './interval-math';
import { timestampLine } from './transcript-timestamps';

/** True when the body has ≥1 section and EVERY section resolves a timestamp (render-parser truth). */
export function everySectionHasTimestamp(markdown: string): boolean {
  const sections = parseSections(markdown);
  return sections.length > 0 && sections.every((s) => s.timeRange !== null);
}

/** Fence-aware indices of every `## ` heading line — same enumeration (order + count) as parseSections. */
function headingLineIndices(markdown: string): number[] {
  const lines = markdown.split('\n');
  const idxs: number[] = [];
  let inFence = false;
  for (let i = 0; i < lines.length; i++) {
    if (isFenceLine(lines[i])) { inFence = !inFence; continue; }
    if (!inFence && /^##\s+/.test(lines[i])) idxs.push(i);
  }
  return idxs;
}

/**
 * Layer-3 finalizer / invariant authority: guarantee every section has a ▶ whose startSec is unique
 * and strictly increasing across the whole document. Existing ▶ lines (all from resolveTranscriptTokens'
 * strictly-increasing LIS) are left byte-identical; only MISSING sections get an inserted line, with a
 * startSec synthesized strictly between its neighbors. Returns input unchanged when nothing is missing.
 */
export function ensureSectionTimestamps(
  markdown: string,
  videoId: string,
  bounds: { firstStart: number; videoDuration: number },
): string {
  const sections = parseSections(markdown);
  if (sections.length === 0 || sections.every((s) => s.timeRange !== null)) return markdown;

  // Allocate a start for EVERY section, left→right, so the full sequence is strictly increasing + unique.
  const starts: number[] = new Array(sections.length);
  let prev = bounds.firstStart - 1; // exclusive lower anchor (so firstStart itself is usable)
  let i = 0;
  while (i < sections.length) {
    const tr = sections[i].timeRange;
    if (tr) {
      // Known start (LIS → strictly increasing among known). Defensively keep it > prev.
      starts[i] = tr.startSec > prev ? tr.startSec : prev + 1;
      prev = starts[i];
      i++;
      continue;
    }
    let j = i;
    while (j < sections.length && sections[j].timeRange === null) j++;
    const lo = prev;                                                    // exclusive
    const hi = j < sections.length ? (sections[j].timeRange as { startSec: number }).startSec : bounds.videoDuration; // exclusive
    const filled = spreadStarts(lo, hi, j - i);
    for (let k = i; k < j; k++) { starts[k] = filled[k - i]; prev = filled[k - i]; }
    i = j;
  }

  // Defensive invariant check (degenerate tiny-gap inputs only — unreachable for real anchors).
  for (let k = 1; k < starts.length; k++) {
    if (starts[k] <= starts[k - 1]) {
      console.warn(`[summary-section-ts-degenerate] ${videoId}: could not keep strictly-increasing startSec at section ${k + 1} (${starts[k - 1]}→${starts[k]})`);
      starts[k] = starts[k - 1] + 1; // last-ditch: preserve dig-key uniqueness even if approximate
    }
  }

  // Insert ▶ after each missing section's heading line. end = next section start, or videoDuration.
  const headings = headingLineIndices(markdown); // same order/count as `sections`
  const insertAfter = new Map<number, string>();
  sections.forEach((s, idx) => {
    if (s.timeRange) return;
    const endSec = idx + 1 < sections.length ? starts[idx + 1] : bounds.videoDuration;
    insertAfter.set(headings[idx], timestampLine(starts[idx], endSec, videoId));
  });

  const lines = markdown.split('\n');
  const out: string[] = [];
  for (let li = 0; li < lines.length; li++) {
    out.push(lines[li]);
    const inject = insertAfter.get(li);
    if (inject !== undefined) out.push(inject);
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
git commit -m "feat(summary-ts): everySectionHasTimestamp + ensureSectionTimestamps finalizer (parser-backed, dig-key safe)"
```

---

## Task 3: Wire Layers 2 + 3 into `generateSummary`

**Files:**
- Modify: `lib/gemini.ts` (`hasTimestamp` 274-277, `warnTimestampMiss` 280-282, `scoreSummary` 293-307, the loop 361-388)
- Test: `tests/lib/gemini-section-timestamp-guarantee.test.ts` (new, pure scoring hook) + updates to `tests/lib/gemini.test.ts`

**Interfaces:**
- Consumes: `everySectionHasTimestamp`, `ensureSectionTimestamps` (Task 2).
- Produces: no signature change to `generateSummary`.

**Behavior:**
1. `scoreSummary` index 3 (timestamp criterion) becomes `!hasSegments || everySectionHasTimestamp(s) ? 1 : 0` (was `hasTimestamp(s)`).
2. After the loop, run `ensureSectionTimestamps` on `chosen.summary` when `hasSegments` and it isn't already complete; compute `firstStart`/`videoDuration` from `segments`.
3. Remove `hasTimestamp` and `warnTimestampMiss`; replace the post-loop `[timestamp-miss]` warn with a `[summary-section-ts-synth]` warn that logs the **count of synthesized sections** (not total). Update the score comment.

Because `resolveTranscriptTokens` is unchanged, a section missing a `▶` after resolution means its token was dropped (out-of-order) or omitted — Layer 2 re-rolls (bounded), Layer 3 backstops.

- [ ] **Step 1: Write the failing test for the per-section criterion**

```ts
// tests/lib/gemini-section-timestamp-guarantee.test.ts
import { __test } from '@/lib/gemini';

const TS = (n: number) => `▶ [0:00–0:00](https://www.youtube.com/watch?v=v&t=${n}s)`;
const mk = (body: string) => ({ summary: body, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } } as never);

describe('scoreSummary per-section timestamp criterion', () => {
  it('a doc with one section missing a ▶ scores NOT timestamp-complete (index 3 = 0)', () => {
    const allTs = ['## 1. A', TS(10), 'a', '', '## Conclusion', TS(30), 'c'].join('\n');
    const oneMissing = ['## 1. A', TS(10), 'a', '', '## Conclusion', 'c'].join('\n');
    expect(__test.scoreSummary(mk(allTs), true)[3]).toBe(1);
    expect(__test.scoreSummary(mk(oneMissing), true)[3]).toBe(0);
  });

  it('no-segments short-circuits index 3 to 1 (E7)', () => {
    const noTs = ['## 1. A', 'a', '', '## Conclusion', 'c'].join('\n');
    expect(__test.scoreSummary(mk(noTs), false)[3]).toBe(1);
  });
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest gemini-section-timestamp-guarantee`
Expected: FAIL — `__test` undefined.

- [ ] **Step 3: Implement the wiring**

In `lib/gemini.ts`:

Add import:
```ts
import { everySectionHasTimestamp, ensureSectionTimestamps } from './summary-section-timestamps';
```

Delete `hasTimestamp` (274-277) and `warnTimestampMiss` (280-282).

Update `scoreSummary` (293-307) — the comment and index 3:
```ts
/**
 * Rank a candidate summary — higher is better. Compared left→right: complete, #sections,
 * has-conclusion, EVERY-section-has-timestamp, length. (resolveTranscriptTokens strips stray
 * [[TS:i]], so the spec's "no unresolved token" criterion always holds and is omitted.)
 */
function scoreSummary(r: GeminiSummaryResponse, hasSegments: boolean): number[] {
  const s = r.summary;
  return [
    checkSummaryCompleteness(s).complete ? 1 : 0,
    (s.match(/^## /gm) ?? []).length,
    /^##\s+(Conclusion|결론)/im.test(s) ? 1 : 0,
    !hasSegments || everySectionHasTimestamp(s) ? 1 : 0,   // per-section (was doc-wide hasTimestamp)
    s.length,
  ];
}
```

Replace the post-loop timestamp warn (387) — after `const chosen = best as GeminiSummaryResponse;` and the incompleteness warn:
```ts
    if (hasSegments && !everySectionHasTimestamp(chosen.summary)) {
      const lastSeg = segments[segments.length - 1];
      const videoDuration = Math.floor(lastSeg.offset + lastSeg.duration);
      const firstStart = Math.floor(segments[0].offset);
      const before = (parseSectionsCount(chosen.summary)); // sections total, for the delta
      chosen.summary = ensureSectionTimestamps(chosen.summary, videoId, { firstStart, videoDuration });
      const synthesized = countSynthesized(before, chosen.summary); // sections that gained a ▶
      console.warn(`[summary-section-ts-synth] ${videoId}: synthesized ▶ for ${synthesized} section(s) after ${attemptsUsed} attempt(s)`);
    }
    return chosen;
```
Simplify the count: compute the missing sections BEFORE mutation (import `parseSections` or reuse `everySectionHasTimestamp`'s parser) rather than a helper pair:
```ts
    if (hasSegments && !everySectionHasTimestamp(chosen.summary)) {
      const lastSeg = segments[segments.length - 1];
      const videoDuration = Math.floor(lastSeg.offset + lastSeg.duration);
      const firstStart = Math.floor(segments[0].offset);
      const missingBefore = parseSections(chosen.summary).filter((s) => s.timeRange === null).length;
      chosen.summary = ensureSectionTimestamps(chosen.summary, videoId, { firstStart, videoDuration });
      console.warn(`[summary-section-ts-synth] ${videoId}: synthesized ▶ for ${missingBefore} section(s) after ${attemptsUsed} attempt(s)`);
    }
    return chosen;
```
Add `import { parseSections } from './html-doc/parse';` for the count.

Add the test hook at the end of the file:
```ts
export const __test = { scoreSummary };
```

- [ ] **Step 4: Run the unit test — verify pass**

Run: `npx jest gemini-section-timestamp-guarantee`
Expected: PASS.

- [ ] **Step 5: Update the three existing gemini tests that encode the OLD doc-wide semantics**

These now assert behavior the design intentionally changes. Rewrite each (verify exact line numbers first with `grep -n`):

1. `tests/lib/gemini.test.ts:320-331` — "degrades to no timestamps when Gemini emits an out-of-range index". Old: `expect(result.summary).not.toMatch(/▶|\[\[TS:/)`. **New:** Layer 3 now synthesizes a `▶`, so assert the section IS timestamped:
```ts
   expect(result.summary).not.toContain('[[TS:');           // raw token still stripped
   expect(everySectionHasTimestamp(result.summary)).toBe(true); // synthesized ▶ present
```
   (import `everySectionHasTimestamp` in the test.)

2. `tests/lib/gemini.test.ts:354-362` — "warns and returns when both attempts lack ▶". Old: `not.toContain('▶')` + `[timestamp-miss]` warn. **New:** now always injected + warn renamed:
```ts
   expect(everySectionHasTimestamp(result.summary)).toBe(true);
   expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('[summary-section-ts-synth]'));
```

3. `tests/lib/gemini.test.ts:473-480` — cap test asserting `[timestamp-miss] vid1`. **New:** assert the re-roll cap still bounds attempts, and the warn is `[summary-section-ts-synth]`:
```ts
   expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('[summary-section-ts-synth]'));
   // call-count assertion for the cap stays as-is (TIMESTAMP_MISS_CAP unchanged)
```

Record each rewrite in the review doc — these are intended behavior changes, not test massaging.

- [ ] **Step 6: Run the gemini suite + type-check**

Run: `npx jest gemini` then `npx tsc --noEmit`
Expected: PASS; tsc exit 0 (verify by exit code).

- [ ] **Step 7: Commit**

```bash
git add lib/gemini.ts tests/lib/gemini-section-timestamp-guarantee.test.ts tests/lib/gemini.test.ts
git commit -m "feat(summary-ts): per-section re-roll criterion + Layer 3 finalizer in generateSummary"
```

---

## Task 4: Regression — full guarantee through `generateSummary` (SDK-mocked, in tests/lib/)

**Files:**
- Create: `tests/lib/gemini-section-timestamp-guarantee.test.ts` is already used for the scoring hook; add the end-to-end block to the **same file** (both are `tests/lib/`, SDK-mocked, `npm test`-discoverable). Do NOT place under `tests/integration/` (separate config, requires a live Supabase stack — v1 H2).

**Behavior (regression, not failing-first — by now Tasks 1-3 make it pass):** a transcript + a mocked model body where one section's `[[TS]]` is out-of-order (LIS drops it) and another omits its token entirely. The mock returns the same body every call (deterministic model). Assert every section has a `▶`, all `startSec` unique + strictly increasing, no throw, and `mockGenerateContent` was called at most `TIMESTAMP_MISS_CAP` times.

- [ ] **Step 1: Add the end-to-end regression block**

```ts
// append to tests/lib/gemini-section-timestamp-guarantee.test.ts
import { GoogleGenerativeAI } from '@google/generative-ai';
import { generateSummary } from '@/lib/gemini';
import { everySectionHasTimestamp } from '@/lib/summary-section-timestamps';
import { parseSections } from '@/lib/html-doc/parse';
import type { TranscriptSegment } from '@/lib/transcript-timestamps';

jest.mock('@google/generative-ai', () => ({
  ...jest.requireActual('@google/generative-ai'),
  GoogleGenerativeAI: jest.fn(),
}));
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

  const segs: TranscriptSegment[] = Array.from({ length: 12 }, (_, i) => ({ text: `seg ${i}`, offset: i * 100, duration: 100 })); // duration 1200

  it('every section gets a unique, monotonic ▶ when one token is out-of-order and one is omitted', async () => {
    const body = [
      '## 1. Alpha', '[[TS:5]]', 'alpha', '', '---', '',
      '## 2. Beta', '[[TS:1]]', 'beta', '', '---', '',   // out-of-order → LIS drops → Layer 3 injects
      '## 3. Gamma', 'gamma (no token)', '', '---', '',   // omitted → re-roll then Layer 3 injects
      '## Conclusion', '[[TS:10]]', 'wrap',
    ].join('\n');
    mockGenerateContent.mockResolvedValue({ response: { text: () => JSON.stringify({
      summary: body, ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      videoType: 'Analysis', audience: 'Intermediate', tags: ['a', 'b', 'c'],
      tldr: 'This video explains things.', takeaways: ['x', 'y', 'z'],
    }) } });

    const r = await generateSummary(segs, 'en', 'vidABC');

    const sections = parseSections(r.summary);
    expect(sections.map((s) => s.title)).toEqual(['Alpha', 'Beta', 'Gamma', 'Conclusion']);
    expect(everySectionHasTimestamp(r.summary)).toBe(true);
    const starts = sections.map((s) => s.timeRange!.startSec);
    for (let i = 1; i < starts.length; i++) expect(starts[i]).toBeGreaterThan(starts[i - 1]);
    expect(new Set(starts).size).toBe(starts.length);           // dig-key uniqueness
    expect(mockGenerateContent.mock.calls.length).toBeLessThanOrEqual(2); // TIMESTAMP_MISS_CAP (money)
  });
});
```

- [ ] **Step 2: Run — verify pass (regression)**

Run: `npx jest gemini-section-timestamp-guarantee`
Expected: PASS. (This block passes once Tasks 1-3 are done — it is regression coverage, not failing-first.)

- [ ] **Step 3: Full suite + type-check**

Run: `npm test` then `npx tsc --noEmit`
Expected: all green (incl. this file, since it's under `tests/lib/`); tsc exit 0.

- [ ] **Step 4: Commit**

```bash
git add tests/lib/gemini-section-timestamp-guarantee.test.ts
git commit -m "test(summary-ts): end-to-end regression — full section-timestamp guarantee (SDK-mocked)"
```

---

## Self-Review (v2, against spec + v1 review)

**1. Spec coverage:** §5 Layer 2 → Task 3; §5 Layer 3 → Task 2 (wired Task 3); §5 Layer 1 → **dropped (v1 review, user-confirmed)** — the guarantee is preserved by Layers 2+3. §8 edges: E1 (out-of-order) → now handled by Layer 3 (dropped token → missing → synthesized), Task 2/4; E2/E3 (omitted → re-roll → inject) → Task 3/4; E4/E5 (first/last bounds) → Task 2; E6 (degenerate gap) → Task 1 clamp + Task 2 defensive warn; E7 (no segments) → Task 3 `!hasSegments`; E8 (dig unchanged) → **`resolveTranscriptTokens` untouched**; E9 (multi-missing) → Task 2. §9 behaviors → Tasks 1-4. §10 money → honest framing + Task 4 call-count assert.

**2. v1 Blocking/High resolved:** B1 → Task 1 strictly-inside `spreadStarts` + Task 2 full-set assertions/tests. B2/H3 → dissolved (Layer 1 dropped). B3 → Task 2 authority + defensive check (and structurally moot: existing `▶` come only from the strictly-increasing LIS). B4/H1/L6 → checker/finalizer reuse `parseSections` (Task 1 export). H2 → Task 4 homed in `tests/lib/`. H4 → renamed to `generateSummary` regression. M1/M4 → honest money framing + call-count test. M2 → Task 4 reframed as regression. M3 → Task 3 Step 5 enumerates the 3 tests with exact new assertions. L5 → `interpolateStart` removed (only `spreadStarts`). L2 → score comment updated. L1 → `__test` accepted as explicit hook.

**3. Type consistency:** `spreadStarts(lo,hi,count):number[]`, `everySectionHasTimestamp(md):boolean`, `ensureSectionTimestamps(md,videoId,{firstStart,videoDuration}):string`, `parseSections`/`isFenceLine` exports, `ParsedSection.timeRange.startSec` — used identically across tasks. Import direction acyclic: `interval-math` (leaf); `summary-section-timestamps → {interval-math, html-doc/parse, transcript-timestamps}`; `gemini → {summary-section-timestamps, html-doc/parse}`. `parse.ts` imports none of these.

**Implementer note:** Task 1 Step 4's `spreadStarts(10,12,5)` case is impossible-room; assert only the reachable guarantee (`r[0]===11`, strictly increasing, unique) and let Task 2's defensive check own degenerate policy. Real callers never hit it (section anchors are far apart).

---

## Adversarial Review Requirement

This is v2 after a converging v1 dual review (4B+4H → Layer 1 dropped, all folded). Per `docs/dev-process.md` Iterative Re-Review, **re-review the revised plan** (Codex + Claude) before implementation, scoped to: (1) verify each v1 finding is genuinely fixed (not reworded) — especially B1 (`spreadStarts` strictly-inside + full-set uniqueness) and B4/H1 (parser reuse); (2) hunt for defects the v2 changes introduced (e.g. `headingLineIndices` vs `parseSections` order/count drift; the defensive degenerate warn; `ensureSectionTimestamps` end-computation). Converge (a round with no new Blocking/High) → notify → SDD.
