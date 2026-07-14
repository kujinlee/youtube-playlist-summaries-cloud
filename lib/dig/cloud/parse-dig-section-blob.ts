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
