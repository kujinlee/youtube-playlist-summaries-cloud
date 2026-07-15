import { renderDigDeeperDoc } from '@/lib/html-doc/render-dig-deeper';

const summary = {
  title: 'T',
  sections: [
    { numeral: '1', title: 'A', prose: 'pa', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
    { numeral: '2', title: 'B', prose: 'pb', timeRange: { startSec: 120, endSec: 200, label: 'l', url: 'https://youtu.be/v?t=120s' } },
  ],
} as never;
const base = { summary, envelope: null, dug: [] as never, mdPath: 'base.md', videoId: 'vid9', language: 'en' as const };

it('cloud registered: emits interactive triggers + cloud script, no expand-all / no SSE', () => {
  const html = renderDigDeeperDoc({ ...base, nonce: 'n1', cloud: { playlistId: 'p1', isAnonymous: false } });
  expect(html).toContain('<a class="dig-trigger" data-section="65">');   // clickable trigger
  expect(html).toContain('dig-state?playlist=');                          // cloud poll engine present
  expect(html).not.toContain('class="dg-expand-all"');                   // expand-all BUTTON omitted (D4) — NOT the bare token (it lives in kept CSS)
  expect(html).not.toContain('⤢ expand all');                            // expand-all label omitted
  expect(html).not.toContain('EventSource');                             // never SSE
  expect(html).not.toContain('data-type="summary"');                    // no summary back-link
});

it('cloud: a STALE dug section emits NO dig-refresh control (cloud has no force-refresh)', () => {
  // Force a stale dug section: genVersion below current ⇒ mergeDigDoc marks it stale.
  const staleDug = [{ sectionId: 65, startSec: 65, title: 'A', bodyMarkdown: 'b', generatedAt: 'g', genVersion: 1, slides: [] }] as never;
  const html = renderDigDeeperDoc({ ...base, dug: staleDug, nonce: 'n1', cloud: { playlistId: 'p1', isAnonymous: false } });
  expect(html).not.toContain('class="dig-refresh"');   // dead control avoided (H1/M1); local still renders it
});

it('cloud anonymous: trigger pre-disabled as a span (not a link)', () => {
  const html = renderDigDeeperDoc({ ...base, nonce: 'n1', cloud: { playlistId: 'p1', isAnonymous: true } });
  expect(html).toContain('<span class="dig-trigger" aria-disabled="true" title="Create an account to dig deeper">');
  expect(html).not.toContain('<a class="dig-trigger" data-section="65">');
});

it('off path is byte-identical to readOnly:false with no cloud arg', () => {
  const withArg = renderDigDeeperDoc({ ...base, nonce: 'n1' });
  const explicitReadonlyFalse = renderDigDeeperDoc({ ...base, nonce: 'n1', readOnly: false });
  expect(withArg).toBe(explicitReadonlyFalse);                           // cloud absent ⇒ no behavior change
  expect(withArg).toContain('EventSource');                             // local path still SSE
});
