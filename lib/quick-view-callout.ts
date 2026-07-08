/**
 * Pure string transforms for the Quick Reference callout block, extracted from
 * `lib/pipeline.ts` so the store-agnostic `summaryCore` (and the cloud worker that
 * imports it) can use them WITHOUT pulling in pipeline.ts's server-only dependency
 * graph (`fs`, storage, html-doc). No storage/fs imports live here — keep it that way.
 */

/**
 * Remove an existing Quick Reference callout block from markdown content.
 * Reverses `insertQuickViewCallout` so the callout can be re-generated
 * after corrections are applied. Returns content unchanged if no callout
 * is present or the format is unexpected.
 */
export function stripQuickViewCallout(mdContent: string): string {
  const START_MARKER = '\n\n> [!summary] Quick Reference';
  const END_MARKER = '\n\n---\n';
  const startIdx = mdContent.indexOf(START_MARKER);
  if (startIdx === -1) return mdContent; // no callout present
  const endIdx = mdContent.indexOf(END_MARKER, startIdx);
  if (endIdx === -1) return mdContent; // malformed — leave unchanged
  return mdContent.slice(0, startIdx) + mdContent.slice(endIdx);
}

export function insertQuickViewCallout(
  mdContent: string,
  tldr: string,
  takeaways: string[],
  tags: string[],
): string {
  // Idempotency guard: don't insert if callout already present
  if (mdContent.includes('> [!summary] Quick Reference')) return mdContent;

  // Find first "\n\n---\n" — the divider between metadata line and summary body
  const dividerIdx = mdContent.indexOf('\n\n---\n');
  if (dividerIdx === -1) return mdContent; // unexpected format, leave unchanged

  const lines = [
    '',
    '> [!summary] Quick Reference',
    `> **TL;DR:** ${tldr}`,
    '>',
    '> **Key Takeaways:**',
    ...takeaways.map((t) => `> - ${t}`),
  ];
  if (tags.length > 0) {
    lines.push('>');
    lines.push(`> **Concepts:** ${tags.join(' · ')}`);
  }

  return mdContent.slice(0, dividerIdx) + '\n' + lines.join('\n') + mdContent.slice(dividerIdx);
}
