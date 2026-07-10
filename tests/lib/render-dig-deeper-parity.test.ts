/** @jest-environment jsdom */
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { renderDigDeeperDoc } from '@/lib/html-doc/render-dig-deeper';
import type { ParsedSummary, MagazineModel } from '@/lib/html-doc/types';

const parsed: ParsedSummary = {
  title: 'T', channel: 'C', duration: '1:00', url: null, lang: 'EN', videoId: 'vid',
  tldr: 'This video x', takeaways: ['a'],
  sections: [{ numeral: '1', title: 'Intro', prose: 'p', timeRange: { startSec: 5, endSec: 9, label: '0:05', url: 'https://y?t=5s' } }],
  sourceMd: 'a.md',
};
const model: MagazineModel = { sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] };

/** Inject rendered HTML, execute every inline <script>, then click #print-btn and assert window.print fired. */
function drivePrint(html: string): number {
  document.documentElement.innerHTML = html.replace(/^[\s\S]*?<body[^>]*>/i, '').replace(/<\/body>[\s\S]*$/i, '');
  const printSpy = jest.fn();
  (window as unknown as { print: () => void }).print = printSpy;
  for (const s of Array.from(document.querySelectorAll('script'))) {
    if (!s.textContent) continue;
    // Isolate each inline <script> exec, mirroring the browser (F10): a throwing dig-deeper script
    // (zoom/askAi/captions/size touch DOM/APIs jsdom lacks) must NOT abort the remaining scripts, or the
    // print listener would never bind and the test would fail for the wrong reason.
    try { new Function(s.textContent)(); } catch { /* per-script isolation, like a real browser */ }
  }
  (document.getElementById('print-btn') as HTMLButtonElement)?.click();
  return printSpy.mock.calls.length;
}

it('B18/B21: the LOCAL summary print button actually fires window.print()', () => {
  expect(drivePrint(renderMagazineHtml(parsed, model))).toBeGreaterThan(0);
});

it('B21: the LOCAL dig-deeper print button still fires window.print() after the shared refactor', () => {
  // renderDigDeeperDoc(args) — a minimal 1-section fixture; the print button + listener must survive.
  const html = renderDigDeeperDoc({
    summary: parsed, envelope: null, dug: [], mdPath: 'a.md', videoId: 'vid', language: 'en',
  });
  expect(drivePrint(html)).toBeGreaterThan(0);
});
