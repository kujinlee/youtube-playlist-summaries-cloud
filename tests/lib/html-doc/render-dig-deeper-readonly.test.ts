import { renderDigDeeperDoc } from '@/lib/html-doc/render-dig-deeper';
import type { ParsedSummary } from '@/lib/html-doc/types';
import type { DugSection } from '@/lib/dig/companion-doc';

const summary: ParsedSummary = {
  title: 'T', channel: 'C', duration: '1:00', url: null, lang: 'EN', videoId: 'v', tldr: null, takeaways: [],
  sections: [
    { numeral: '1', title: 'Alpha', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: '1:05–2:00', url: 'https://youtu.be/v?t=65s' } },
    { numeral: '2', title: 'Beta', prose: 'p', timeRange: { startSec: 200, endSec: 260, label: '3:20–4:20', url: 'https://youtu.be/v?t=200s' } },
  ],
  sourceMd: 'base.md',
};
const dug: DugSection[] = [
  { sectionId: 65, startSec: 65, title: 'Alpha', bodyMarkdown: 'deep alpha', generatedAt: '2026-07-14T00:00:00Z', genVersion: 3, slides: [] },
];
const base = { summary, envelope: null, dug, mdPath: 'base.md', videoId: 'v', language: 'en' as const };

describe('renderDigDeeperDoc readOnly + nonce', () => {
  it('default render keeps interactive controls and emits no nonce', () => {
    const html = renderDigDeeperDoc(base);
    expect(html).toContain('class="dig-trigger"');   // Beta is un-dug → trigger MARKUP present
    expect(html).toContain('class="dg-expand-all"');  // expand-all button markup present
    expect(html).toContain('dig-trigger[data-section]'); // navScript engine present
    expect(html).not.toContain('nonce=');             // no CSP nonce by default
  });

  it('added params default to a no-op (guards behavior 24 — local output unchanged)', () => {
    // Proves readOnly/nonce OFF is byte-for-byte identical to omitting them entirely, so the
    // const→function + nonceAttr(undefined) threading cannot perturb the local path.
    expect(renderDigDeeperDoc(base)).toBe(renderDigDeeperDoc({ ...base, readOnly: false, nonce: undefined }));
  });

  it('readOnly omits every nav-coupled control, dialog, and the navScript engine', () => {
    const html = renderDigDeeperDoc({ ...base, readOnly: true });
    // element/attribute markers — NOT bare class tokens (those live in kept CSS)
    for (const marker of [
      'class="dig-trigger"', 'class="dig-refresh"', 'class="dig-toggle"',
      'class="dg-expand-all"', 'id="_dg-ea-dlg"', 'data-type="summary"', // summary back-link
      'dig-trigger[data-section]',  // navScript IIFE body (generation engine) — nav-only string
    ]) {
      expect(html).not.toContain(marker);
    }
    expect(html).toContain('deep alpha'); // dug content still rendered statically
  });

  it('readOnly keeps self-contained controls AND their scripts', () => {
    const html = renderDigDeeperDoc({ ...base, readOnly: true });
    // control markup (element-specific)
    expect(html).toContain('id="_dg-zoom"');        // slide-zoom overlay
    expect(html).toContain('class="ask-ai"');        // Ask-AI anchor
    expect(html).toContain('class="dg-size-range"'); // size control
    expect(html).toContain('class="dg-caps-toggle"');// captions control
    // and the scripts that drive them (IIFE bodies — prove the <script> wasn't dropped)
    expect(html).toContain("getElementById('_dg-zoom')");      // zoomScript
    expect(html).toContain("querySelector('.dg-size-range')");  // sizeScript
    expect(html).toContain("querySelector('.dg-caps-toggle')"); // captionsScript
  });

  it('with a nonce, every <script> and <style> carries it', () => {
    const html = renderDigDeeperDoc({ ...base, readOnly: true, nonce: 'N0NCE' });
    const scripts = html.match(/<script[^>]*>/g) ?? [];
    const styles = html.match(/<style[^>]*>/g) ?? [];
    expect(scripts.length).toBeGreaterThan(0);
    expect(styles.length).toBeGreaterThan(0);
    for (const tag of [...scripts, ...styles]) expect(tag).toContain('nonce="N0NCE"');
  });
});
