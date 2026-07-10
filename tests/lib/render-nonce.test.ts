import { renderMagazineHtml } from '@/lib/html-doc/render';
import { buildSummaryCsp, generateNonce } from '@/lib/html-doc/csp';
import type { ParsedSummary, MagazineModel } from '@/lib/html-doc/types';

const parsed: ParsedSummary = {
  title: 'T', channel: 'C', duration: '1:00', url: null, lang: 'EN', videoId: 'vid',
  tldr: 'This video x', takeaways: ['a'],
  sections: [{ numeral: '1', title: 'Intro', prose: 'p', timeRange: { startSec: 5, endSec: 9, label: '0:05', url: 'https://y?t=5s' } }],
  sourceMd: 'a.md',
};
const model: MagazineModel = { sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] };

it('local render (no opts): no nonce attributes, dig controls present, print button works via listener', () => {
  const html = renderMagazineHtml(parsed, model);
  expect(html).not.toContain('nonce=');
  expect(html).toContain('dig deeper'); // dig control present (dig defaults true)
  expect(html).not.toContain('onclick="window.print()"'); // D11: inline onclick removed for BOTH paths
  expect(html).toContain('print-btn'); // button still present
  // NOTE: repo targets ES2017, so the dotAll `s` flag is unavailable; `[\s\S]*` gives the same
  // newline-spanning match the brief's `/…/s` intended, and compiles under `tsc --noEmit`.
  // Require the actual D11 wiring form (addEventListener('click' ... window.print()) — a bare
  // window.print() anywhere in the doc must NOT satisfy this assertion.
  expect(html).toMatch(/addEventListener\('click'[^)]*\)[\s\S]*window\.print\(\)/); // listener wires print via addEventListener
});

it('cloud render ({nonce, dig:false}): every inline script/style carries the SAME nonce; no dig controls', () => {
  const n = 'TESTNONCE==';
  const html = renderMagazineHtml(parsed, model, { nonce: n, dig: false });
  const scriptOpens = html.match(/<script[^>]*>/g) ?? [];
  expect(scriptOpens.length).toBeGreaterThan(0);
  for (const tag of scriptOpens) expect(tag).toContain(`nonce="${n}"`);
  expect(html).toMatch(new RegExp(`<style nonce="${n}">`));
  expect(html).not.toContain('dig deeper'); // D12/B19: dig controls suppressed
});

it('the FOUC head theme script is nonce-coherent under the strict CSP', () => {
  const n = 'ABC123==';
  const html = renderMagazineHtml(parsed, model, { nonce: n, dig: false });
  expect(html).toMatch(new RegExp(`<script nonce="${n}">\\(function\\(\\)\\{try\\{var t=localStorage`));
});

it('buildSummaryCsp has no unsafe-* and locks img/frame/form/base/object', () => {
  const csp = buildSummaryCsp('N==');
  expect(csp).toContain("default-src 'none'");
  expect(csp).toContain("script-src 'nonce-N=='");
  expect(csp).toContain("style-src 'nonce-N=='");
  expect(csp).toContain("img-src 'none'");
  expect(csp).toContain("base-uri 'none'");
  expect(csp).toContain("object-src 'none'");
  expect(csp).toContain("frame-ancestors 'none'");
  expect(csp).toContain("form-action 'none'");
  expect(csp).not.toMatch(/unsafe-(inline|eval|hashes)/);
});

it('generateNonce yields ≥128-bit base64, distinct per call', () => {
  const a = generateNonce(), b = generateNonce();
  expect(a).not.toBe(b);
  expect(Buffer.from(a, 'base64').length).toBeGreaterThanOrEqual(16);
});
