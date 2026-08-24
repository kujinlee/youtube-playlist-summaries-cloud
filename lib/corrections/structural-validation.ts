import { parseSections } from '@/lib/html-doc/parse';

/** Why the post-correction document was rejected. Named so a negative test can assert WHICH
 *  failure it provoked rather than "any error" (a test that catches any error passes on a typo). */
export type StructuralFailureReason =
  | 'missing-frontmatter'
  | 'missing-h1'
  | 'section-count'
  | 'section-title'
  | 'section-timestamp';

export class StructuralValidationError extends Error {
  readonly reason: StructuralFailureReason;
  constructor(reason: StructuralFailureReason, message: string) {
    super(message);
    this.name = 'StructuralValidationError';
    this.reason = reason;
  }
}

/**
 * Throw unless `after` has the SAME structure as `before`: identical H2 sequence (count, order and
 * exact text, including the leading ordinal), identical `▶` `(startSec, endSec)` tuples, and an H1
 * plus frontmatter still present.
 *
 * NO REPAIR, deliberately. `generateSummary` repairs (`ensureSectionTimestamps`, gemini.ts:391-403)
 * because it authored the structure. A correction did not: a structural change means the model
 * disobeyed its prompt (`gemini.ts:480` — "do NOT add, remove, or restructure any sections"), and the
 * result is discarded rather than patched up.
 *
 * `before` is the PRE-correction document AFTER the quick-view callout has been stripped, so both
 * sides are compared in the same shape.
 */
export function assertStructurePreserved(before: string, after: string): void {
  if (!after.startsWith('---\n')) {
    throw new StructuralValidationError(
      'missing-frontmatter',
      'corrected document does not start with a YAML frontmatter delimiter',
    );
  }
  if (!/^#\s+\S/m.test(after)) {
    throw new StructuralValidationError('missing-h1', 'corrected document has no H1 heading');
  }

  const a = parseSections(before);
  const b = parseSections(after);

  if (a.length !== b.length) {
    throw new StructuralValidationError(
      'section-count',
      `corrected document has ${b.length} sections, expected ${a.length}`,
    );
  }

  for (let i = 0; i < a.length; i++) {
    if (a[i].numeral !== b[i].numeral || a[i].title !== b[i].title) {
      throw new StructuralValidationError(
        'section-title',
        `section ${i} heading changed: "${a[i].numeral ?? ''} ${a[i].title}" → "${b[i].numeral ?? ''} ${b[i].title}"`,
      );
    }
    const ta = a[i].timeRange ?? null;
    const tb = b[i].timeRange ?? null;
    if ((ta === null) !== (tb === null)) {
      throw new StructuralValidationError(
        'section-timestamp',
        `section ${i} ▶ timestamp ${ta === null ? 'appeared' : 'disappeared'}`,
      );
    }
    if (ta !== null && tb !== null && (ta.startSec !== tb.startSec || ta.endSec !== tb.endSec)) {
      throw new StructuralValidationError(
        'section-timestamp',
        `section ${i} ▶ tuple changed: (${ta.startSec},${ta.endSec}) → (${tb.startSec},${tb.endSec})`,
      );
    }
  }
}
