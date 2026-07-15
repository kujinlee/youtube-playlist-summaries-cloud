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
