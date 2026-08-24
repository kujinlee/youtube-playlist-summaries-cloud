import {
  assertStructurePreserved,
  StructuralValidationError,
} from '@/lib/corrections/structural-validation';

// ⚠ THIS IS THE REAL DOCUMENT SHAPE, not an invented one — assembled per
// lib/ingestion/summary-core.ts:101-116: frontmatter (tags list, QUOTED video_id, lang uppercase,
// score) / blank / H1 / blank / meta line / blank / `---` / blank / body. An earlier draft used an
// unquoted `video_id` and no tags block; the parser tolerates both (parse.ts:5 strips optional
// quotes), so the tests would have passed against a document that this pipeline never produces.
const DOC = `---
tags:
  - video-summary
  - en
video_id: "abc12345678"
lang: EN
score: 4.2
---

# A Title

**Channel:** Ch | **Duration:** 10:00 | **URL:** https://www.youtube.com/watch?v=abc12345678

---

## 1. Intro

▶ [0:00–5:00](https://www.youtube.com/watch?v=abc12345678&t=0s)

Original prose one.

---

## Conclusion

▶ [5:00–10:00](https://www.youtube.com/watch?v=abc12345678&t=300s)

Original prose two.
`;

describe('assertStructurePreserved', () => {
  it('accepts a prose-only rewrite', () => {
    const after = DOC.replace('Original prose one.', 'Corrected prose one.');
    expect(() => assertStructurePreserved(DOC, after)).not.toThrow();
  });

  it('rejects a renamed H2 with reason section-title', () => {
    const after = DOC.replace('## 1. Intro', '## 1. Introduction');
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-title' }));
  });

  // The ordinal is part of the heading's identity, not decoration: `parseSections` splits it into
  // `numeral` (parse.ts:52-54), so a comparison that comfortably passes on `title` alone lets a
  // renumbering through. Added 2026-08-24 after a mutation that dropped the `numeral` conjunct
  // survived all seven of the plan's tests — the plan's own gate line for this task is "the
  // comparison is inexact".
  it('rejects a renumbered H2 with reason section-title', () => {
    const after = DOC.replace('## 1. Intro', '## 2. Intro');
    expect(after).not.toEqual(DOC);
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-title' }));
  });

  it('rejects a dropped section with reason section-count', () => {
    const after = DOC.slice(0, DOC.indexOf('## Conclusion'));
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-count' }));
  });

  it('rejects a moved ▶ start second with reason section-timestamp', () => {
    const after = DOC.replace('&t=300s', '&t=301s');
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-timestamp' }));
  });

  /**
   * MEASURED IN PRODUCTION 2026-08-24, on the first successful live correction (release v9). The
   * model applied the requested fix AND silently corrupted one character of a `▶` URL:
   *
   *     before  ▶ [9:23–13:23](https://www.youtube.com/watch?v=E3U-AquW5hs&t=563s)
   *     after   ▶ [9:23–13:23](https://www.youtube.com=watch?v=E3U-AquW5hs&t=563s)
   *
   * **The validator accepted it and the broken link is durable in a paid document.** `startSec` is
   * parsed out of `&t=563s` and `endSec` out of the `[9:23–13:23]` label; both survived, so the two
   * fields the guard compared were identical while the line around them was not.
   *
   * Backlog #23 specifies this validator as "H2 sequence + `▶` tuples **byte-identical** pre/post".
   * The implementation compared two PARSED NUMBERS instead — correct about the tuple it named,
   * blind to the rest of the line it claimed to guard. `label` and `url` were already on the parsed
   * shape (parse.ts:39), so the fix is to compare what was always there.
   */
  it('rejects a corrupted ▶ URL whose parsed seconds are UNCHANGED — the prod case', () => {
    const after = DOC.replace('www.youtube.com/watch?v=abc12345678&t=300s',
                              'www.youtube.com=watch?v=abc12345678&t=300s');
    expect(after).not.toEqual(DOC);
    // Both seconds are untouched: t=300s still parses to 300, the label still says 5:00–10:00.
    // Nothing but a byte comparison of the line can see this.
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-timestamp' }));
  });

  it('rejects a reworded ▶ LABEL whose seconds still parse the same', () => {
    // `endSec` comes from splitting the label on the en dash, so `5:00–10:00` → `5:00 – 10:00`
    // parses to the same numbers while the rendered text differs.
    const after = DOC.replace('[5:00–10:00]', '[5:00 – 10:00]');
    expect(after).not.toEqual(DOC);
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-timestamp' }));
  });

  it('still accepts a document whose ▶ lines are untouched', () => {
    // The guard against over-tightening: the prose rewrite above must keep passing, and does,
    // because nothing on the ▶ line changed.
    const after = DOC.replace('Original prose two.', 'Corrected prose two.');
    expect(() => assertStructurePreserved(DOC, after)).not.toThrow();
  });

  it('rejects a dropped H1 with reason missing-h1', () => {
    const after = DOC.replace('# A Title\n', '');
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'missing-h1' }));
  });

  it('rejects dropped frontmatter with reason missing-frontmatter', () => {
    // Slice at the H1 rather than pattern-matching the frontmatter. The plan shipped a regex
    // (`/^---\nvideo_id: abc12345678\n…/`) describing an EARLIER, three-line frontmatter; DOC was
    // later upgraded to the real shape and the regex was not, so it matched nothing, `after` was
    // DOC unchanged, and the test compared the document to itself — a negative test that would
    // have passed against almost any implementation. Measured 2026-08-24.
    const after = DOC.slice(DOC.indexOf('# A Title'));
    // The fixture must actually mutate: a masked mutation is indistinguishable from a passing guard.
    expect(after.startsWith('---')).toBe(false);
    expect(after).not.toEqual(DOC);
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'missing-frontmatter' }));
  });

  it('throws StructuralValidationError, not a bare Error', () => {
    const after = DOC.replace('## 1. Intro', '## 1. Introduction');
    expect(() => assertStructurePreserved(DOC, after)).toThrow(StructuralValidationError);
  });
});
