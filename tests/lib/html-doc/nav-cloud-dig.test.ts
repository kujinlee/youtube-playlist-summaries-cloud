/** @jest-environment jsdom */
import {
  applyCloudDigError, swapDugSection, pollUntilDug, startCloudDig,
  type CloudDigEnv, digCloudScript,
} from '../../../lib/html-doc/nav';

const PL = '11111111-1111-1111-1111-111111111111';

function envWith(fetchMock: jest.Mock, href = 'http://h/api/html/vid9?playlist=' + PL + '&type=dig-deeper'): CloudDigEnv {
  return { fetch: fetchMock as unknown as typeof fetch, now: () => 0, sleep: async () => {}, getPageHref: () => href, doc: document };
}
function trigger(sec: number): HTMLElement {
  document.body.innerHTML = `<div class="dg"><section data-start="${sec}" data-dug="false"><h2>x <a class="dig-trigger" data-section="${sec}">dig deeper ▶</a></h2></section></div>`;
  return document.querySelector('.dig-trigger') as HTMLElement;
}
const pageWith = (sec: number, body: string) =>
  ({ ok: true, text: async () => `<!doctype html><section data-start="${sec}" data-dug="true"><p>${body}</p></section>` });

it('applyCloudDigError sets error text/state and drops href', () => {
  const el = trigger(65); el.setAttribute('href', '#');
  applyCloudDigError(el, '⚠ retry');
  expect(el.textContent).toBe('⚠ retry');
  expect(el.dataset.state).toBe('error');
  expect(el.hasAttribute('href')).toBe(false);
});

it('swapDugSection replaces the section from a re-fetch of the page', async () => {
  const t = trigger(65);
  const fetchMock = jest.fn().mockResolvedValue(pageWith(65, 'DUG-PROSE'));
  await swapDugSection(65, envWith(fetchMock));
  expect(fetchMock).toHaveBeenCalledWith('http://h/api/html/vid9?playlist=' + PL + '&type=dig-deeper');
  expect(document.querySelector('[data-start="65"]')!.getAttribute('data-dug')).toBe('true');
  expect(document.body.textContent).toContain('DUG-PROSE');
  void t;
});

it('pollUntilDug returns true once the section id appears', async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [] }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [65] }) });
  const ok = await pollUntilDug(65, 'vid9', PL, envWith(fetchMock));
  expect(ok).toBe(true);
  expect(fetchMock).toHaveBeenCalledWith('/api/videos/vid9/dig-state?playlist=' + encodeURIComponent(PL));
});

it('pollUntilDug returns false after the deadline (never appears)', async () => {
  let clock = 0;
  const env: CloudDigEnv = { fetch: (jest.fn().mockResolvedValue({ ok: true, json: async () => ({ sectionIds: [] }) })) as unknown as typeof fetch,
    now: () => clock, sleep: async (ms) => { clock += ms + 1; }, getPageHref: () => 'http://h/x', doc: document };
  const ok = await pollUntilDug(65, 'vid9', PL, env);
  expect(ok).toBe(false); // clock passes 180000 ceiling
});

it('startCloudDig happy path: 202 → poll → swap', async () => {
  const t = trigger(65);
  const fetchMock = jest.fn()
    .mockResolvedValueOnce({ ok: true, status: 202, json: async () => ({ status: 'enqueued', jobId: 'j1', sectionId: 65 }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [65] }) })   // poll
    .mockResolvedValueOnce(pageWith(65, 'DUG-PROSE'));                                // re-fetch
  await startCloudDig(t, 'vid9', PL, envWith(fetchMock));
  expect((fetchMock.mock.calls[0][0] as string)).toBe('/api/videos/vid9/dig/65?playlist=' + encodeURIComponent(PL));
  expect((fetchMock.mock.calls[0][1] as any).method).toBe('POST');
  expect((fetchMock.mock.calls[0][1] as any).body).toBeUndefined();                  // no body
  expect(document.body.textContent).toContain('DUG-PROSE');
});

it('startCloudDig already-dug race: 200 ready → swap immediately, no poll', async () => {
  const t = trigger(65);
  const fetchMock = jest.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ status: 'ready', sectionId: 65 }) })
    .mockResolvedValueOnce(pageWith(65, 'DUG-PROSE'));
  await startCloudDig(t, 'vid9', PL, envWith(fetchMock));
  expect(fetchMock).toHaveBeenCalledTimes(2);            // POST + re-fetch, no dig-state poll
  expect(document.body.textContent).toContain('DUG-PROSE');
});

it('startCloudDig 403 → account message, no swap', async () => {
  const t = trigger(65);
  const fetchMock = jest.fn().mockResolvedValueOnce({ ok: false, status: 403, json: async () => ({ error: 'dig requires an account' }) });
  await startCloudDig(t, 'vid9', PL, envWith(fetchMock));
  expect(t.textContent).toBe('⚠ Create an account to dig deeper');
  expect(t.dataset.state).toBe('error');
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it('startCloudDig 429/503 → busy message', async () => {
  for (const status of [429, 503]) {
    const t = trigger(65);
    const fetchMock = jest.fn().mockResolvedValueOnce({ ok: false, status, json: async () => ({}) });
    await startCloudDig(t, 'vid9', PL, envWith(fetchMock));
    expect(t.textContent).toBe('⚠ busy — try later');
  }
});

it('startCloudDig poll timeout → retry message', async () => {
  const t = trigger(65);
  let clock = 0;
  const env: CloudDigEnv = {
    fetch: (jest.fn()
      .mockResolvedValueOnce({ ok: true, status: 202, json: async () => ({ status: 'enqueued', jobId: 'j' }) })
      .mockResolvedValue({ ok: true, json: async () => ({ sectionIds: [] }) })) as unknown as typeof fetch,
    now: () => clock, sleep: async (ms) => { clock += ms + 1; }, getPageHref: () => 'http://h/x', doc: document,
  };
  await startCloudDig(t, 'vid9', PL, env);
  expect(t.textContent).toBe('⚠ retry');
  expect(t.dataset.state).toBe('error');
});

it('startCloudDig sets loading copy synchronously before the first await', () => {
  const t = trigger(65);
  const fetchMock = jest.fn(() => new Promise<Response>(() => {}));   // never resolves
  void startCloudDig(t, 'vid9', PL, envWith(fetchMock));             // do NOT await
  expect(t.textContent).toBe('⏳ generating…');                      // set before any await (M2)
  expect(t.dataset.state).toBe('loading');
});

it('startCloudDig non-ok 404/409 → retry', async () => {
  for (const status of [404, 409]) {
    const t = trigger(65);
    const fetchMock = jest.fn().mockResolvedValueOnce({ ok: false, status, json: async () => ({}) });
    await startCloudDig(t, 'vid9', PL, envWith(fetchMock));
    expect(t.textContent).toBe('⚠ retry');
    expect(t.dataset.state).toBe('error');
  }
});

it('startCloudDig POST network reject → retry (behavior 12)', async () => {
  const t = trigger(65);
  const fetchMock = jest.fn().mockRejectedValueOnce(new Error('net down'));
  await startCloudDig(t, 'vid9', PL, envWith(fetchMock));
  expect(t.textContent).toBe('⚠ retry');
});

it('startCloudDig over-report: dig-state says dug but re-fetch section is NOT dug → retry (H2)', async () => {
  const t = trigger(65);
  const fetchMock = jest.fn()
    .mockResolvedValueOnce({ ok: true, status: 202, json: async () => ({ status: 'enqueued', jobId: 'j' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [65] }) })                 // poll claims dug
    .mockResolvedValueOnce({ ok: true, text: async () => '<!doctype html><section data-start="65" data-dug="false"></section>' }); // but not dug
  await startCloudDig(t, 'vid9', PL, envWith(fetchMock));
  expect(t.textContent).toBe('⚠ retry');                            // swap threw → error, not stuck ⏳
});

it('digCloudScript stamps the nonce and is not the local NAV_SCRIPT', () => {
  const s = digCloudScript('abc');
  expect(s.startsWith('<script nonce="abc">')).toBe(true);
  expect(s).toContain('dig-state?playlist=');       // poll path
  expect(s).not.toContain('EventSource');           // never SSE in cloud
});
