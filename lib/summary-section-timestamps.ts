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
