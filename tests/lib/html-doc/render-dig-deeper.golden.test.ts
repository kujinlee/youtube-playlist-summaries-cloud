import { renderDigDeeperDoc } from '@/lib/html-doc/render-dig-deeper';

// One dug + one un-dug section, deterministic nonce → covers trigger, toggle, top-bar, scripts.
const summary = {
  title: 'T',
  sections: [
    { numeral: '1', title: 'A', prose: 'pa', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
    { numeral: '2', title: 'B', prose: 'pb', timeRange: { startSec: 120, endSec: 200, label: 'l', url: 'https://youtu.be/v?t=120s' } },
  ],
} as never;
const dug = [{ sectionId: 65, startSec: 65, title: 'A', bodyMarkdown: 'body', generatedAt: 'g', genVersion: 3, slides: [] }] as never;

it('local dig doc output is byte-stable (golden)', () => {
  const html = renderDigDeeperDoc({ summary, envelope: null, dug, mdPath: 'base.md', videoId: 'vid9', language: 'en', nonce: 'n1' });
  expect(html).toMatchSnapshot();
});
