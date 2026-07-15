/**
 * @jest-environment jsdom
 * @jest-environment-options {"url": "http://h/api/html/vid9?playlist=11111111-1111-1111-1111-111111111111&type=dig-deeper"}
 */
import { digCloudScript } from '../../../lib/html-doc/nav';

const PL = '11111111-1111-1111-1111-111111111111';
const flush = () => new Promise((r) => setTimeout(r, 0));

function boot(): void {
  // Extract and run the IIFE body of the SHIPPED inline script (strip the <script> wrapper).
  const body = digCloudScript().replace(/^<script>/, '').replace(/<\/script>$/, '');
  // eslint-disable-next-line no-new-func
  new Function(body)();
}

beforeEach(() => { (global as unknown as { fetch: jest.Mock }).fetch = jest.fn(); });

it('shipped inline: click un-dug trigger → POST (no body) → 200 ready → swap in place', async () => {
  document.body.innerHTML =
    '<div class="dg"><section data-start="65" data-dug="false"><h2>x <a class="dig-trigger" data-section="65">dig deeper ▶</a></h2></section></div>';
  const fetchMock = (global as unknown as { fetch: jest.Mock }).fetch;
  fetchMock
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ status: 'ready', sectionId: 65 }) })
    .mockResolvedValueOnce({ ok: true, text: async () => '<!doctype html><section data-start="65" data-dug="true"><p>DUG-INLINE</p></section>' });
  boot();
  (document.querySelector('.dig-trigger') as HTMLElement).click();
  await flush(); await flush();
  expect(fetchMock.mock.calls[0][0]).toBe('/api/videos/vid9/dig/65?playlist=' + encodeURIComponent(PL));
  expect(fetchMock.mock.calls[0][1].method).toBe('POST');
  expect(fetchMock.mock.calls[0][1].body).toBeUndefined();     // no body
  expect(document.body.textContent).toContain('DUG-INLINE');   // swapped
});

it('shipped inline: 429 → busy message, and a second click re-POSTs (behavior 14)', async () => {
  document.body.innerHTML =
    '<div class="dg"><section data-start="65" data-dug="false"><h2>x <a class="dig-trigger" data-section="65">dig deeper ▶</a></h2></section></div>';
  const fetchMock = (global as unknown as { fetch: jest.Mock }).fetch;
  fetchMock.mockResolvedValue({ ok: false, status: 429, json: async () => ({}) });
  boot();
  const trig = document.querySelector('.dig-trigger') as HTMLElement;
  trig.click(); await flush();
  expect(trig.textContent).toBe('⚠ busy — try later');
  trig.click(); await flush();                                 // re-POST from error state
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it('shipped inline: click .dig-toggle flips show-gist and label (behavior 15, zero fetch)', () => {
  document.body.innerHTML =
    '<div class="dg"><section data-start="65" data-dug="true"><h2>x <a class="dig-toggle">show summary ⌃</a></h2></section></div>';
  boot();
  const toggle = document.querySelector('.dig-toggle') as HTMLElement;
  const section = document.querySelector('section')!;
  toggle.click();
  expect(section.classList.contains('show-gist')).toBe(true);
  expect(toggle.textContent).toBe('show dig deeper ▶');
  expect((global as unknown as { fetch: jest.Mock }).fetch).not.toHaveBeenCalled();
});
