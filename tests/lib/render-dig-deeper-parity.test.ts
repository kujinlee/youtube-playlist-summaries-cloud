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

/** Inject rendered HTML and execute every inline <script> (binds listeners), but do NOT click yet. */
function renderAndBind(html: string): jest.Mock {
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
  return printSpy;
}

/**
 * Prove the CLICK — not merely script execution/load — causes window.print():
 * assert 0 calls right after binding (before any click), then click #print-btn,
 * then assert exactly 1 call. Catches both a non-binding listener (stays 0 after
 * click) and a load-time/other-path print (already >0 before click).
 */
function drivePrintAssertingClickCausesPrint(html: string): void {
  const printSpy = renderAndBind(html);
  expect(printSpy).toHaveBeenCalledTimes(0);
  (document.getElementById('print-btn') as HTMLButtonElement)?.click();
  expect(printSpy).toHaveBeenCalledTimes(1);
}

it('B18/B21: the LOCAL summary print button actually fires window.print() via click, not load', () => {
  drivePrintAssertingClickCausesPrint(renderMagazineHtml(parsed, model));
});

it('B21: the LOCAL dig-deeper print button still fires window.print() via click after the shared refactor', () => {
  // renderDigDeeperDoc(args) — a minimal 1-section fixture; the print button + listener must survive.
  const html = renderDigDeeperDoc({
    summary: parsed, envelope: null, dug: [], mdPath: 'a.md', videoId: 'vid', language: 'en',
  });
  drivePrintAssertingClickCausesPrint(html);
});
