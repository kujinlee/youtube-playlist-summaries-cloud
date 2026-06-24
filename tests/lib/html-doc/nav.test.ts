/** @jest-environment jsdom */
import {
  startSecFromTsUrl,
  digControl,
  wireDigLinks,
  scrollToHashSection,
  initDigControls,
} from '../../../lib/html-doc/nav';

describe('startSecFromTsUrl', () => {
  it('parses t=<sec>s', () => { expect(startSecFromTsUrl('https://y/watch?v=x&t=185s')).toBe(185); });
  it('parses t=0s', () => { expect(startSecFromTsUrl('https://y/watch?v=x&t=0s')).toBe(0); });
  it('returns null when absent/malformed', () => { expect(startSecFromTsUrl('https://y/watch?v=x')).toBeNull(); });
});

describe('digControl', () => {
  describe('summary-side (1-arg, POST-driven)', () => {
    it('emits class="dig", data-section, data-t, and "dig deeper" label', () => {
      const h = digControl(16);
      expect(h).toContain('class="dig"');
      expect(h).toContain('data-section="16"');
      expect(h).toContain('data-t="16"');
      expect(h).toContain('dig deeper');
    });
    it('does NOT emit data-type (not a cross-doc link)', () => {
      expect(digControl(16)).not.toContain('data-type=');
    });
    it('handles startSec=0 (presence-gated, not truthiness)', () => {
      const h = digControl(0);
      expect(h).toContain('data-section="0"');
      expect(h).toContain('data-t="0"');
    });
  });

  describe('deep-dive-side (2-arg "summary", cross-doc nav)', () => {
    it('builds a "↑ summary" control with data-type and data-t', () => {
      const h = digControl('summary', 0);
      expect(h).toContain('class="dig"');
      expect(h).toContain('data-type="summary"');
      expect(h).toContain('data-t="0"');
      expect(h).toContain('↑ summary');
    });
    it('carries the correct startSec in data-t', () => {
      expect(digControl('summary', 200)).toContain('data-t="200"');
    });
  });
});

describe('wireDigLinks', () => {
  it('rebuilds the href from the current URL, swapping type + setting #t, preserving outputFolder + id', () => {
    document.body.innerHTML = '<a class="dig" data-type="deep-dive" data-t="200">x</a>';
    wireDigLinks(document, { href: 'http://h/api/html/vid9?outputFolder=%2FU%2Ff&type=summary' });
    const href = document.querySelector('a.dig')!.getAttribute('href')!;
    expect(href).toContain('/api/html/vid9');           // id preserved in path
    expect(href).toContain('type=deep-dive');
    expect(href.endsWith('#t=200')).toBe(true);
    const u = new URL('http://h' + href);
    expect(u.searchParams.get('outputFolder')).toBe('/U/f'); // round-trips, no double-encode
  });

  it('does NOT touch summary-side a.dig that lack data-type (no type=undefined injected)', () => {
    document.body.innerHTML = '<a class="dig" data-section="135" data-t="135">dig deeper ▶</a>';
    wireDigLinks(document, { href: 'http://h/api/html/vid9?outputFolder=%2FU%2Ff&type=summary' });
    const el = document.querySelector('a.dig')!;
    const href = el.getAttribute('href');
    // href must remain unset (null) — wireDigLinks must leave summary-side controls alone
    expect(href).toBeNull();
    // Guard: the type=undefined corruption must not appear even if href were set
    expect(href ?? '').not.toContain('type=undefined');
  });
});

describe('scrollToHashSection', () => {
  beforeEach(() => {
    document.body.innerHTML = '<section data-start="0">a</section><section data-start="200">b</section>';
    (HTMLElement.prototype as any).scrollIntoView = jest.fn();
  });
  it('scrolls to the section with the greatest data-start <= t', () => {
    scrollToHashSection(document, { hash: '#t=210' });
    expect((document.querySelector('[data-start="200"]') as any).scrollIntoView).toHaveBeenCalled();
  });
  it('lands on the start=0 section for a small t', () => {
    scrollToHashSection(document, { hash: '#t=5' });
    expect((document.querySelector('[data-start="0"]') as any).scrollIntoView).toHaveBeenCalled();
  });
  it('does nothing without a #t hash', () => {
    scrollToHashSection(document, { hash: '' });
    expect((document.querySelector('[data-start="0"]') as any).scrollIntoView).not.toHaveBeenCalled();
  });
});

// ── initDigControls — EventSource mock ───────────────────────────────────────
type ESHandler = ((event: MessageEvent) => void) | null;
type ESErrorHandler = ((event: Event) => void) | null;

interface MockESInstance {
  url: string;
  onmessage: ESHandler;
  onerror: ESErrorHandler;
  close: jest.Mock;
  emitMessage: (data: object) => void;
  emitError: () => void;
}

let lastES: MockESInstance | null = null;

class MockEventSource {
  url: string;
  onmessage: ESHandler = null;
  onerror: ESErrorHandler = null;
  close = jest.fn();

  constructor(url: string) {
    this.url = url;
    lastES = this as unknown as MockESInstance;
  }

  emitMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }

  emitError() {
    this.onerror?.(new Event('error'));
  }
}

/** Flush all pending microtasks (Promise resolution chains). */
async function flushMicrotasks(): Promise<void> {
  // 8 ticks: enough for fetch → .json() → .then(jobId) → new EventSource
  for (let i = 0; i < 8; i++) await Promise.resolve();
}

// ── test helpers ─────────────────────────────────────────────────────────────
const VIDEO_ID = 'vid42';
const OUTPUT_FOLDER = '/Users/test/vault/playlist';
const ENC_FOLDER = encodeURIComponent(OUTPUT_FOLDER);
const LOC = {
  pathname: `/api/html/${VIDEO_ID}`,
  search: `?outputFolder=${ENC_FOLDER}&type=summary`,
};

function makeDoc(sectionsHTML: string): Document {
  const d = document.implementation.createHTMLDocument('test');
  d.body.innerHTML = sectionsHTML;
  return d;
}

function twoControls(): Document {
  return makeDoc(`
    <a class="dig" data-section="0" data-t="0">dig deeper ▶</a>
    <a class="dig" data-section="200" data-t="200">dig deeper ▶</a>
  `);
}

// ── Behavior 1: dug on load ──────────────────────────────────────────────────
describe('initDigControls — B1: dug on load', () => {
  beforeEach(() => {
    lastES = null;
    Object.defineProperty(window, 'EventSource', { writable: true, value: MockEventSource });
  });

  it('renders "view detail ↓" with ALL link params for each sectionId in dig-state', async () => {
    const doc = twoControls();
    global.fetch = jest.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sectionIds: [0, 200] }),
    } as any);

    await initDigControls(doc, LOC);

    const controls = doc.querySelectorAll('a.dig') as NodeListOf<HTMLAnchorElement>;
    for (const ctrl of controls) {
      const href = ctrl.getAttribute('href')!;
      expect(href).toBeTruthy();
      // Must contain all required params
      const u = new URL('http://host' + href);
      expect(u.pathname).toBe(`/api/html/${VIDEO_ID}`);
      expect(u.searchParams.get('outputFolder')).toBe(OUTPUT_FOLDER);
      expect(u.searchParams.get('type')).toBe('dig-deeper');
      // Fragment must match the section's startSec
      const sec = Number(ctrl.dataset.section);
      expect(u.hash).toBe(`#t=${sec}`);
      expect(ctrl.textContent).toContain('view detail');
    }
  });

  it('only marks controls whose sectionId is in dig-state; others remain "dig deeper ▶"', async () => {
    const doc = twoControls();
    global.fetch = jest.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sectionIds: [200] }),  // only section 200 is dug
    } as any);

    await initDigControls(doc, LOC);

    const [ctrl0, ctrl200] = Array.from(doc.querySelectorAll('a.dig')) as HTMLAnchorElement[];
    expect(ctrl0.textContent).toContain('dig deeper');
    expect(ctrl0.getAttribute('href')).toBeNull();

    expect(ctrl200.textContent).toContain('view detail');
    expect(ctrl200.getAttribute('href')).toBeTruthy();
  });
});

// ── Behavior 2: dig-state fetch failure → fail-open ─────────────────────────
describe('initDigControls — B2: dig-state fetch fails → fail-open', () => {
  it('leaves controls as "dig deeper ▶" when fetch rejects', async () => {
    const doc = twoControls();
    global.fetch = jest.fn().mockRejectedValueOnce(new Error('network'));

    await initDigControls(doc, LOC);

    const controls = doc.querySelectorAll('a.dig') as NodeListOf<HTMLAnchorElement>;
    for (const ctrl of controls) {
      expect(ctrl.textContent).toContain('dig deeper');
      expect(ctrl.getAttribute('href')).toBeNull();
    }
  });

  it('leaves controls as "dig deeper ▶" when fetch returns non-ok', async () => {
    const doc = twoControls();
    global.fetch = jest.fn().mockResolvedValueOnce({ ok: false, json: async () => ({}) } as any);

    await initDigControls(doc, LOC);

    const controls = doc.querySelectorAll('a.dig') as NodeListOf<HTMLAnchorElement>;
    for (const ctrl of controls) {
      expect(ctrl.textContent).toContain('dig deeper');
    }
  });
});

// ── Behavior 3: not-dug click → POST then EventSource, shows ⏳ ─────────────
describe('initDigControls — B3: not-dug click → POST + EventSource + ⏳', () => {
  beforeEach(() => {
    lastES = null;
    Object.defineProperty(window, 'EventSource', { writable: true, value: MockEventSource });
  });

  it('issues POST (not GET) with outputFolder in body and shows ⏳', async () => {
    const doc = makeDoc('<a class="dig" data-section="100" data-t="100">dig deeper ▶</a>');
    global.fetch = jest.fn()
      // dig-state returns empty (nothing dug)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [] }) } as any)
      // POST dig returns jobId
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: 'job-1' }) } as any);

    await initDigControls(doc, LOC);

    const ctrl = doc.querySelector('a.dig') as HTMLAnchorElement;
    ctrl.click();

    // Allow microtasks to settle
    await flushMicrotasks();

    // Verify POST was called (second fetch call)
    const calls = (global.fetch as jest.Mock).mock.calls;
    const postCall = calls[1];
    expect(postCall).toBeTruthy();
    const [url, opts] = postCall;
    expect(url).toContain(`/api/videos/${VIDEO_ID}/dig/100`);
    expect(opts.method).toBe('POST');
    const body = JSON.parse(opts.body);
    expect(body.outputFolder).toBe(OUTPUT_FOLDER);

    // Control should show ⏳ and be disabled
    expect(ctrl.textContent).toContain('⏳');
    // aria-disabled or pointer-events — we check the data-state attribute
    expect(ctrl.dataset.state).toBe('loading');
  });

  it('opens EventSource on stream URL with jobId after POST', async () => {
    const doc = makeDoc('<a class="dig" data-section="100" data-t="100">dig deeper ▶</a>');
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [] }) } as any)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: 'job-abc' }) } as any);

    await initDigControls(doc, LOC);
    const ctrl = doc.querySelector('a.dig') as HTMLAnchorElement;
    ctrl.click();

    await flushMicrotasks();

    expect(lastES).toBeTruthy();
    expect(lastES!.url).toContain(`/api/videos/${VIDEO_ID}/dig/100/stream`);
    expect(lastES!.url).toContain('jobId=job-abc');
  });
});

// ── Behavior 4: stream done → "view detail ↓" ───────────────────────────────
describe('initDigControls — B4: stream done → "view detail ↓"', () => {
  beforeEach(() => {
    lastES = null;
    Object.defineProperty(window, 'EventSource', { writable: true, value: MockEventSource });
  });

  it('changes control to "view detail ↓" with all params on done event', async () => {
    const doc = makeDoc('<a class="dig" data-section="100" data-t="100">dig deeper ▶</a>');
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [] }) } as any)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: 'job-2' }) } as any);

    await initDigControls(doc, LOC);
    const ctrl = doc.querySelector('a.dig') as HTMLAnchorElement;
    ctrl.click();

    await flushMicrotasks();

    lastES!.emitMessage({ type: 'done' });

    expect(ctrl.textContent).toContain('view detail');
    const href = ctrl.getAttribute('href')!;
    const u = new URL('http://host' + href);
    expect(u.pathname).toBe(`/api/html/${VIDEO_ID}`);
    expect(u.searchParams.get('outputFolder')).toBe(OUTPUT_FOLDER);
    expect(u.searchParams.get('type')).toBe('dig-deeper');
    expect(u.hash).toBe('#t=100');
  });
});

// ── Behavior 5: job error event → ⚠ retry ───────────────────────────────────
describe('initDigControls — B5: stream error event → ⚠ retry', () => {
  beforeEach(() => {
    lastES = null;
    Object.defineProperty(window, 'EventSource', { writable: true, value: MockEventSource });
  });

  it('shows ⚠ retry when stream emits {type:"error"}', async () => {
    const doc = makeDoc('<a class="dig" data-section="100" data-t="100">dig deeper ▶</a>');
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [] }) } as any)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: 'job-3' }) } as any);

    await initDigControls(doc, LOC);
    const ctrl = doc.querySelector('a.dig') as HTMLAnchorElement;
    ctrl.click();

    await flushMicrotasks();

    lastES!.emitMessage({ type: 'error', message: 'failed' });

    expect(ctrl.textContent).toContain('⚠');
    expect(ctrl.dataset.state).toBe('error');
    expect(lastES!.close).toHaveBeenCalled();
  });
});

// ── Behavior 6: EventSource transport error → ⚠ retry ───────────────────────
describe('initDigControls — B6: EventSource transport onerror → ⚠ retry', () => {
  beforeEach(() => {
    lastES = null;
    Object.defineProperty(window, 'EventSource', { writable: true, value: MockEventSource });
  });

  it('shows ⚠ retry when onerror fires (transport error, not a job event)', async () => {
    const doc = makeDoc('<a class="dig" data-section="100" data-t="100">dig deeper ▶</a>');
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [] }) } as any)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: 'job-4' }) } as any);

    await initDigControls(doc, LOC);
    const ctrl = doc.querySelector('a.dig') as HTMLAnchorElement;
    ctrl.click();

    await flushMicrotasks();

    lastES!.emitError();

    expect(ctrl.textContent).toContain('⚠');
    expect(ctrl.dataset.state).toBe('error');
    expect(lastES!.close).toHaveBeenCalled();
  });
});

// ── Behavior 7: double-click while loading → ignored ────────────────────────
describe('initDigControls — B7: double-click while loading → no second POST', () => {
  beforeEach(() => {
    lastES = null;
    Object.defineProperty(window, 'EventSource', { writable: true, value: MockEventSource });
  });

  it('ignores the second click while ⏳ loading (no second POST)', async () => {
    const doc = makeDoc('<a class="dig" data-section="100" data-t="100">dig deeper ▶</a>');
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [] }) } as any)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: 'job-5' }) } as any);

    await initDigControls(doc, LOC);
    const ctrl = doc.querySelector('a.dig') as HTMLAnchorElement;
    ctrl.click();

    await flushMicrotasks();

    // Second click while loading
    ctrl.click();
    await Promise.resolve();

    // fetch should have been called exactly twice: once for dig-state, once for POST
    const calls = (global.fetch as jest.Mock).mock.calls;
    expect(calls.length).toBe(2);
  });
});

// ── Behavior 8: force re-dig on a dug control ────────────────────────────────
describe('initDigControls — B8: force re-dig → POST with force:true', () => {
  beforeEach(() => {
    lastES = null;
    Object.defineProperty(window, 'EventSource', { writable: true, value: MockEventSource });
  });

  it('POSTs with force:true when ↻ (force) button on a dug control is clicked', async () => {
    const doc = makeDoc('<a class="dig" data-section="200" data-t="200">dig deeper ▶</a>');
    global.fetch = jest.fn()
      // dig-state: section 200 is already dug
      .mockResolvedValueOnce({ ok: true, json: async () => ({ sectionIds: [200] }) } as any)
      // force POST
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: 'job-6' }) } as any);

    await initDigControls(doc, LOC);

    // After load, the control should show "view detail ↓" with a force button
    const ctrl = doc.querySelector('a.dig') as HTMLAnchorElement;
    expect(ctrl.textContent).toContain('view detail');

    // Click the force re-dig button (↻) embedded in the control
    const forceBtn = doc.querySelector('[data-force-section]') as HTMLElement | null;
    expect(forceBtn).toBeTruthy();
    forceBtn!.click();

    await flushMicrotasks();

    const calls = (global.fetch as jest.Mock).mock.calls;
    const postCall = calls[1];
    expect(postCall).toBeTruthy();
    const [url, opts] = postCall;
    expect(url).toContain(`/api/videos/${VIDEO_ID}/dig/200`);
    expect(opts.method).toBe('POST');
    const body = JSON.parse(opts.body);
    expect(body.outputFolder).toBe(OUTPUT_FOLDER);
    expect(body.force).toBe(true);
  });
});
