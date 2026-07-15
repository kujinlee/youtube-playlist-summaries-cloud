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
    } else if (k !== null && k < lower) {
      s = lower;                                    // known value only too low (collision/non-monotonic) → minimal bump to prev+1
    } else {
      // missing, or known above the room ceiling: synthesize toward the next known anchor
      let nextK: number | null = null;
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

/** True when the body has ≥1 section, EVERY section resolves a timestamp, the starts are strictly
 *  increasing (hence unique), and every range is well-formed (end > start). Uses the render parser's
 *  own truth (parseSections.timeRange), so it can never disagree with the renderer. */
export function sectionStartsComplete(markdown: string): boolean {
  const sections = parseSections(markdown);
  if (sections.length === 0) return false;
  let prev = -Infinity;
  for (const s of sections) {
    if (!s.timeRange) return false;
    if (s.timeRange.startSec <= prev) return false;
    if (s.timeRange.endSec <= s.timeRange.startSec) return false;
    prev = s.timeRange.startSec;
  }
  return true;
}

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
  // Belt-and-suspenders: allocateSectionStarts is proven strictly-increasing, so this never fires;
  // it is a cheap guard against a future allocator regression. Do NOT write a test expecting it.
  for (let i = 1; i < starts.length; i++) if (starts[i] <= starts[i - 1]) starts[i] = starts[i - 1] + 1;

  const layout = sectionLayout(markdown); // same order/count as `sections`
  const lines = markdown.split('\n');
  const replace = new Map<number, string>();     // existing ▶ slot line → canonical line
  const insertAfter = new Map<number, string>(); // heading line → inserted canonical line
  // Canonicalize EVERY section's ▶ to timestampLine(start, end) where end = next section's start (or,
  // for the last section, max(videoDuration, start+1) so end > start even in the pathological regime).
  // A line already byte-identical to its canonical form is left untouched (idempotent no-op for good
  // docs); any other — missing, colliding, malformed, OR merely stale-end after a neighbor moved — is
  // rewritten/inserted. This is what fixes the "kept line keeps a stale/overlapping end" defect.
  sections.forEach((s, idx) => {
    const endSec = idx + 1 < sections.length
      ? starts[idx + 1]
      : Math.max(bounds.videoDuration, starts[idx] + 1);
    const canonical = timestampLine(starts[idx], endSec, videoId);
    const slot = layout[idx].tsLine;
    if (slot !== null && lines[slot] === canonical) return;   // already canonical → keep byte-identical
    if (slot !== null) replace.set(slot, canonical);          // rewrite (start and/or end changed, or malformed)
    else insertAfter.set(layout[idx].headingLine, canonical); // no ▶ present → insert after heading
  });

  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    out.push(replace.has(i) ? (replace.get(i) as string) : lines[i]);
    if (insertAfter.has(i)) out.push(insertAfter.get(i) as string);
  }
  return out.join('\n');
}
