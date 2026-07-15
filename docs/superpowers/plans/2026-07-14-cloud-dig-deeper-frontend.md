# Cloud Dig-Deeper Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make cloud "Dig deeper" usable from the UI — a menu link opens the served dig doc, and per-section triggers inside that doc generate digs with poll-based (non-SSE) progress, mirroring the local UX.

**Architecture:** React adds only the menu doorway (`digHref` + a `VideoMenu` item). The interaction lives inside the server-rendered dig doc: a new **cloud-interactive** render mode re-enables the per-section `dig-trigger` markup and injects a **new** poll-based inline script (`digCloudScript`) *instead of* the local SSE `navScript`. The local `navScript` string is left untouched, so the local/off path stays byte-identical.

**Tech Stack:** Next.js 16 (App Router), React, TypeScript, jest + ts-jest, @testing-library/react (jsdom), real local Supabase for the integration test.

## Global Constraints

- **Byte-identical-when-off (load-bearing):** `lib/html-doc/render-dig-deeper.ts` and `lib/html-doc/nav.ts` are shared with the merged local path. Every change is **additive**; with the new `cloud` option absent (all existing callers), their output must be **byte-identical to today**. The local `NAV_SCRIPT` constant is **not edited** — the cloud script is a separate new constant.
- **Money invariant:** opening/serving the dig doc and polling `dig-state` never charge. Only `POST /dig/[sectionId]` spends, and that is the already-built, already-tested backend — untouched by this slice.
- **No live Gemini / no real network:** unit tests mock `fetch` (jsdom) and mock Supabase auth at the route boundary (`jest.mock('@/lib/supabase/server')` + `jest.mock('next/headers')`). Only the Task 6 integration test hits real local Supabase.
- **Poll parameters (exact):** timeout ceiling `180000` ms (~3 min); backoff starts `2000` ms, `+2000` per tick, capped at `10000` ms.
- **Test locations (jest `testMatch`):** unit/component tests go under `tests/lib/**`, `tests/api/**`, `tests/components/**`; the integration test goes under `tests/integration/**` (run by `jest.integration.config.ts`). Files elsewhere silently never run.
- **Cloud dig serve URL contract:** `GET /api/html/<videoId>?playlist=<uuid>&type=dig-deeper`. Trigger: `POST /api/videos/<videoId>/dig/<sectionId>?playlist=<uuid>` (no body). Poll: `GET /api/videos/<videoId>/dig-state?playlist=<uuid>`.
- **Shared-code re-review:** because Tasks 3 & 4 touch `lib/html-doc/*`, the whole-branch gate is a **mandatory dual adversarial re-review to convergence** (dev-process Iterative Re-Review), explicitly verifying byte-identity-when-off and the money invariant.
- **Anonymous handling:** the trigger is **pre-disabled** for anonymous users (rendered as a `<span>`, not a clickable `<a>`), AND the client surfaces the server's `403` as a fallback (defense-in-depth).

Spec: `docs/superpowers/specs/2026-07-14-cloud-dig-deeper-frontend-design.md` (§9 enumerated behaviors are the test contract).

---

## File Structure

| File | Responsibility | Shared? |
|---|---|---|
| `lib/client/api.ts` | add `digHref(playlistId, videoId)` | no |
| `components/VideoMenu.tsx` | add cloud `Dig deeper ↗` menu item, gated on `summaryReady` | no |
| `lib/html-doc/nav.ts` | **new** exported cloud-dig helpers (jsdom-tested) + **new** inline `DIG_CLOUD_SCRIPT` + `digCloudScript(nonce)` export; `NAV_SCRIPT` untouched | **yes** |
| `lib/html-doc/render-dig-deeper.ts` | add optional `cloud` arg → interactive mode (triggers on, expand-all/back-link off, anon-disabled trigger, inject `digCloudScript`) | **yes** |
| `app/api/html/[id]/route.ts` | cloud `dig-deeper` branch: drop `readOnly:true`, pass `cloud:{ playlistId, isAnonymous }` | no |
| `tests/integration/dig-serve-interactive.test.ts` | real-Supabase interactive-doc + no-charge integration test | no |

Task order: 1 → 2 depend only on `digHref`. Task 3 (nav cloud engine) produces `digCloudScript`, consumed by Task 4 (render wiring), consumed by Task 5 (route). Task 6 is the end-to-end integration test.

---

### Task 1: `digHref` client helper

**Files:**
- Modify: `lib/client/api.ts` (add after `pdfHref`, ~line 219)
- Test: `tests/lib/client/dig-href.test.ts`

**Interfaces:**
- Produces: `export function digHref(playlistId: string, videoId: string): string` → `/api/html/<enc videoId>?playlist=<playlistId>&type=dig-deeper`

- [ ] **Step 1: Write the failing test**

`tests/lib/client/dig-href.test.ts`:
```ts
import { digHref } from '@/lib/client/api';

it('builds the exact dig-deeper href with all params', () => {
  const u = new URL(digHref('11111111-1111-1111-1111-111111111111', 'vid 123'), 'https://a.test');
  expect(u.pathname).toBe('/api/html/vid%20123');            // encoded
  expect(u.searchParams.get('playlist')).toBe('11111111-1111-1111-1111-111111111111');
  expect(u.searchParams.get('type')).toBe('dig-deeper');
  expect(u.searchParams.has('outputFolder')).toBe(false);    // cloud contract: never outputFolder
  expect(u.searchParams.has('format')).toBe(false);
});

it('percent-encodes a path/query-injecting videoId (no injection)', () => {
  const u = new URL(digHref('11111111-1111-1111-1111-111111111111', 'vid/1?x=2#frag&y=z'), 'https://a.test');
  expect(u.pathname).toBe('/api/html/vid%2F1%3Fx%3D2%23frag%26y%3Dz');
  expect(u.hash).toBe('');
  expect([...u.searchParams.keys()].sort()).toEqual(['playlist', 'type']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest dig-href`
Expected: FAIL — `digHref is not a function` (not exported yet).

- [ ] **Step 3: Implement**

In `lib/client/api.ts`, immediately after the `pdfHref` function:
```ts
/** Builds the serveCloud dig-deeper-doc URL (interactive per-section digging). Mirrors summaryHref/pdfHref. */
export function digHref(playlistId: string, videoId: string): string {
  const params = new URLSearchParams();
  params.set('playlist', playlistId);
  params.set('type', 'dig-deeper');
  return `/api/html/${encodeURIComponent(videoId)}?${params.toString()}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest dig-href`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/client/api.ts tests/lib/client/dig-href.test.ts
git commit -m "feat(dig-fe): digHref client helper for cloud dig-deeper doc"
```

---

### Task 2: `VideoMenu` cloud "Dig deeper ↗" item

**Files:**
- Modify: `components/VideoMenu.tsx` (import `digHref`; add one `<li>` inside the cloud block, after the "Share…" `<li>` ~line 120)
- Test: `tests/components/video-menu-dig.test.tsx`

**Interfaces:**
- Consumes: `digHref(playlistId, videoId)` (Task 1); `video.summaryReady: boolean`; `scope.playlistId` via `useScope()`.
- Produces: an enabled `<a href={digHref(pid, video.id)} target="_blank">Dig deeper ↗</a>` when `summaryReady===true`; a disabled `<span aria-disabled title="Finalizing…">` otherwise; **absent** in local scope.

- [ ] **Step 1: Write the failing test**

`tests/components/video-menu-dig.test.tsx` (harness copied from `tests/components/video-menu-cloud-2c.test.tsx`):
```tsx
/** @jest-environment jsdom */
import { render, screen } from '@testing-library/react';
import VideoMenu from '../../components/VideoMenu';
import { ScopeProvider, type Scope } from '@/lib/client/scope';

const PID = '11111111-1111-1111-1111-111111111111';
const CLOUD_SCOPE: Scope = { mode: 'cloud', playlistId: PID };
const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/o', baseOutputFolder: '/o' };
const renderCloud = (ui: React.ReactElement) => render(<ScopeProvider scope={CLOUD_SCOPE}>{ui}</ScopeProvider>);
const renderLocal = (ui: React.ReactElement) => render(<ScopeProvider scope={LOCAL_SCOPE}>{ui}</ScopeProvider>);

const video = {
  id: 'vid11111111', title: 'T', youtubeUrl: 'https://youtu.be/x', language: 'en',
  durationSeconds: 5, archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
};
const baseProps = { outputFolder: '/o', baseOutputFolder: '/o', onArchive() {}, onEditCorrections() {}, onGenerateHtml() {}, onClose() {}, busy: false };

test('cloud + summaryReady: Dig deeper link has exact href, new tab', () => {
  renderCloud(<VideoMenu {...baseProps} video={{ ...video, summaryReady: true } as any} />);
  const link = screen.getByRole('link', { name: /dig deeper/i });
  expect(link).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=dig-deeper`);
  expect(link).toHaveAttribute('target', '_blank');
  expect(link).toHaveAttribute('rel', 'noopener noreferrer');
});

test('cloud + NOT ready: Dig deeper is disabled span, no link', () => {
  renderCloud(<VideoMenu {...baseProps} video={{ ...video, summaryReady: false } as any} />);
  const el = screen.getByText(/dig deeper/i);
  expect(el).toHaveAttribute('aria-disabled', 'true');
  expect(el).toHaveAttribute('title', 'Finalizing…');
  expect(screen.queryByRole('link', { name: /dig deeper/i })).not.toBeInTheDocument();
});

test('local scope: no Dig deeper item at all', () => {
  renderLocal(<VideoMenu {...baseProps} video={{ ...video, summaryReady: true } as any} />);
  expect(screen.queryByText(/dig deeper/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest video-menu-dig`
Expected: FAIL — no element matching `/dig deeper/i`.

- [ ] **Step 3: Implement**

In `components/VideoMenu.tsx`, add the `digHref` import to the existing `@/lib/client/api` import (alongside `summaryHref`, `pdfHref`). Then inside the cloud block `<>...</>`, immediately after the "Share…" `<li role="none">…</li>` (the last item before the closing `</>` ~line 120), add:
```tsx
            <li role="none">
              {ready ? (
                <a href={digHref(pid, video.id)} onClick={onClose} target="_blank" rel="noopener noreferrer" className={itemClass}>
                  Dig deeper ↗
                </a>
              ) : (
                <span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>Dig deeper ↗</span>
              )}
            </li>
```
(If `digHref` is not already imported, extend the existing import: `import { summaryHref, pdfHref, digHref } from '@/lib/client/api';` — match the file's current import spelling.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest video-menu-dig video-menu-cloud-2c VideoMenu`
Expected: PASS — new tests green; existing menu tests unaffected (item is additive).

- [ ] **Step 5: Commit**

```bash
git add components/VideoMenu.tsx tests/components/video-menu-dig.test.tsx
git commit -m "feat(dig-fe): cloud VideoMenu 'Dig deeper' item gated on summaryReady"
```

---

### Task 3: `nav.ts` cloud poll engine (helpers + inline script)

Add jsdom-tested cloud-dig helper functions AND a new inline `DIG_CLOUD_SCRIPT` that mirrors them (same pattern as the existing `applyDug*` helpers ↔ `NAV_SCRIPT`). **Do not edit `NAV_SCRIPT`.**

**Files:**
- Modify: `lib/html-doc/nav.ts` (append new exports; add `DIG_CLOUD_SCRIPT` + `digCloudScript` near `navScript`)
- Test: `tests/lib/html-doc/nav-cloud-dig.test.ts`

**Interfaces:**
- Produces:
  - `interface CloudDigEnv { fetch: typeof fetch; now: () => number; sleep: (ms: number) => Promise<void>; getPageHref: () => string; doc: Document }`
  - `applyCloudDigError(el: HTMLElement, msg: string): void`
  - `swapDugSection(sec: number, env: CloudDigEnv): Promise<void>`
  - `pollUntilDug(sec: number, videoId: string, playlist: string, env: CloudDigEnv): Promise<boolean>`
  - `startCloudDig(trigger: HTMLElement, videoId: string, playlist: string, env: CloudDigEnv): Promise<void>`
  - `digCloudScript(nonce?: string): string` (consumed by Task 4)

- [ ] **Step 1: Write the failing tests**

`tests/lib/html-doc/nav-cloud-dig.test.ts`:
```ts
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
```

- [ ] **Step 1b: Write the SHIPPED-inline-script execution test (H3/M4 — tests the string that actually ships)**

The TS helpers above are the tested mirror, but the browser runs `DIG_CLOUD_SCRIPT`. This test **executes** that inline string in jsdom so a broken POST URL, missing status branch, or broken toggle in the shipped code is caught (behaviors 9, 14, 15). It avoids the poll-timer path (the TS helper tests cover polling) by using the `200 ready` and error branches, which need no timers.

`tests/lib/html-doc/nav-cloud-dig-inline.test.ts`:
```ts
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest nav-cloud-dig`
Expected: FAIL — the new exports are not defined.

- [ ] **Step 3: Implement the helpers**

Append to `lib/html-doc/nav.ts` (after the existing exports, before `NAV_SCRIPT` is fine; keep `NAV_SCRIPT` unchanged):
```ts
// ── Cloud dig-deeper: poll-based trigger engine ──────────────────────────────
// Cloud dig runs on a separate worker (no in-process job registry), so there is
// no SSE. The trigger POSTs (no body), then polls dig-state until the section's
// blob appears, then re-fetches the page and swaps the section in place — the
// same DOM-swap as the local SSE 'done' handler. DRIFT WARNING: DIG_CLOUD_SCRIPT
// below duplicates these helpers in inline ES5 and must be kept in sync. The inline
// string IS smoke-executed in jsdom (nav-cloud-dig-inline.test.ts), but that covers
// only the ready/error/toggle paths — the poll-timer path is verified only via the
// TS mirror, so keep the two in sync by hand.
export interface CloudDigEnv {
  fetch: typeof fetch;
  now: () => number;
  sleep: (ms: number) => Promise<void>;
  getPageHref: () => string;
  doc: Document;
}

/** Cloud dig timing (see plan Global Constraints). */
const CLOUD_DIG_TIMEOUT_MS = 180000;
const CLOUD_DIG_POLL_START_MS = 2000;
const CLOUD_DIG_POLL_STEP_MS = 2000;
const CLOUD_DIG_POLL_MAX_MS = 10000;

/** Set a trigger to the error state (message + data-state + drop href). */
export function applyCloudDigError(el: HTMLElement, msg: string): void {
  el.textContent = msg;
  el.dataset.state = 'error';
  el.removeAttribute('href');
}

/**
 * Re-fetch the current page and replace the [data-start=sec] <section> in place.
 * Throws if the re-fetched section is missing or NOT actually dug (data-dug!=="true").
 * This guards against dig-state over-reporting (blob malformed/vanished): without the
 * check, a swap would silently no-op and the trigger would stay stuck at ⏳ (H2).
 */
export async function swapDugSection(sec: number, env: CloudDigEnv): Promise<void> {
  const res = await env.fetch(env.getPageHref());
  const html = await res.text();
  const fresh = new DOMParser().parseFromString(html, 'text/html').querySelector(`[data-start="${sec}"]`);
  const cur = env.doc.querySelector(`[data-start="${sec}"]`);
  if (!fresh || fresh.getAttribute('data-dug') !== 'true' || !cur || !cur.parentNode) {
    throw new Error('dig section not present/dug after generation');
  }
  cur.parentNode.replaceChild(env.doc.adoptNode(fresh), cur);
}

/**
 * Poll dig-state until `sec` is present, or the timeout ceiling elapses.
 * The deadline is checked AFTER each sleep so no fetch fires past the ceiling (M1).
 */
export async function pollUntilDug(sec: number, videoId: string, playlist: string, env: CloudDigEnv): Promise<boolean> {
  const deadline = env.now() + CLOUD_DIG_TIMEOUT_MS;
  let delay = CLOUD_DIG_POLL_START_MS;
  for (;;) {
    await env.sleep(delay);
    if (env.now() > deadline) return false;
    let ids: number[] = [];
    try {
      const r = await env.fetch(`/api/videos/${videoId}/dig-state?playlist=${encodeURIComponent(playlist)}`);
      if (r.ok) ids = ((await r.json()) as { sectionIds?: number[] }).sectionIds ?? [];
    } catch { /* keep polling */ }
    if (ids.includes(sec)) return true;
    delay = Math.min(delay + CLOUD_DIG_POLL_STEP_MS, CLOUD_DIG_POLL_MAX_MS);
  }
}

/** Full cloud dig flow for one trigger: POST → (ready | poll) → swap; maps errors to trigger text. */
export async function startCloudDig(trigger: HTMLElement, videoId: string, playlist: string, env: CloudDigEnv): Promise<void> {
  const sec = Number(trigger.dataset.section);
  trigger.textContent = '⏳ generating…';   // spec §4/§7 loading copy (M2)
  trigger.dataset.state = 'loading';
  trigger.removeAttribute('href');
  let resp: Response;
  try {
    resp = await env.fetch(`/api/videos/${videoId}/dig/${sec}?playlist=${encodeURIComponent(playlist)}`, { method: 'POST' });
  } catch { applyCloudDigError(trigger, '⚠ retry'); return; }
  if (resp.status === 403) { applyCloudDigError(trigger, '⚠ Create an account to dig deeper'); return; }
  if (resp.status === 429 || resp.status === 503) { applyCloudDigError(trigger, '⚠ busy — try later'); return; }
  if (!resp.ok) { applyCloudDigError(trigger, '⚠ retry'); return; }
  let data: { status?: string } = {};
  try { data = (await resp.json()) as { status?: string }; } catch { /* treat as enqueued */ }
  if (data.status === 'ready') {
    try { await swapDugSection(sec, env); } catch { applyCloudDigError(trigger, '⚠ retry'); }
    return;
  }
  const done = await pollUntilDug(sec, videoId, playlist, env);
  if (!done) { applyCloudDigError(trigger, '⚠ retry'); return; }
  try { await swapDugSection(sec, env); } catch { applyCloudDigError(trigger, '⚠ retry'); }
}
```

- [ ] **Step 4: Implement the inline `DIG_CLOUD_SCRIPT` + `digCloudScript`**

Add near the existing `navScript` (do **not** modify `NAV_SCRIPT`):
```ts
// Inline ES5 mirror of the cloud dig helpers above (the browser can't import the module).
// Selector uses `a.dig-trigger[data-section]` so the anonymous pre-disabled <span> is inert.
const DIG_CLOUD_SCRIPT = `<script>
(function(){
  var _dg=document.querySelector('.dg');
  if(!_dg)return;
  var videoId=location.pathname.split('/')[3];
  var playlist=new URLSearchParams(location.search).get('playlist');
  if(!videoId||!playlist)return;
  function _err(el,msg){el.textContent=msg;el.dataset.state='error';el.removeAttribute('href');}
  function _swap(sec){
    return fetch(location.href).then(function(res){return res.text();}).then(function(html){
      var fd=new DOMParser().parseFromString(html,'text/html');
      var fresh=fd.querySelector('[data-start="'+sec+'"]');
      var cur=document.querySelector('[data-start="'+sec+'"]');
      if(!fresh||fresh.getAttribute('data-dug')!=='true'||!cur||!cur.parentNode){throw new Error('not dug');}
      cur.parentNode.replaceChild(document.adoptNode(fresh),cur);
    });
  }
  function _poll(sec,trigger){
    var deadline=Date.now()+180000;var delay=2000;
    function tick(){
      if(Date.now()>deadline){_err(trigger,'\\u26a0 retry');return;}
      fetch('/api/videos/'+videoId+'/dig-state?playlist='+encodeURIComponent(playlist))
        .then(function(r){return r.ok?r.json():{sectionIds:[]};})
        .then(function(d){
          var ids=(d&&d.sectionIds)||[];
          if(ids.indexOf(sec)>=0){_swap(sec).catch(function(){_err(trigger,'\\u26a0 retry');});}
          else{delay=Math.min(delay+2000,10000);setTimeout(tick,delay);}
        })
        .catch(function(){delay=Math.min(delay+2000,10000);setTimeout(tick,delay);});
    }
    setTimeout(tick,delay);
  }
  function _start(trigger){
    var sec=+trigger.dataset.section;
    trigger.textContent='\\u23f3 generating\\u2026';trigger.dataset.state='loading';trigger.removeAttribute('href');
    fetch('/api/videos/'+videoId+'/dig/'+sec+'?playlist='+encodeURIComponent(playlist),{method:'POST'})
      .then(function(r){
        if(r.status===403){_err(trigger,'\\u26a0 Create an account to dig deeper');return null;}
        if(r.status===429||r.status===503){_err(trigger,'\\u26a0 busy \\u2014 try later');return null;}
        if(!r.ok){_err(trigger,'\\u26a0 retry');return null;}
        return r.json().catch(function(){return {};});
      })
      .then(function(d){
        if(d===null)return;
        if(d&&d.status==='ready'){_swap(sec).catch(function(){_err(trigger,'\\u26a0 retry');});return;}
        _poll(sec,trigger);
      })
      .catch(function(){_err(trigger,'\\u26a0 retry');});
  }
  _dg.addEventListener('click',function(e){
    var tog=(e.target.closest?e.target.closest('.dig-toggle'):null);
    if(tog){e.preventDefault();var s=tog.closest('section');if(s){s.classList.toggle('show-gist');tog.textContent=s.classList.contains('show-gist')?'show dig deeper \\u25b6':'show summary \\u2303';}return;}
    var trig=(e.target.closest?e.target.closest('a.dig-trigger[data-section]'):null);
    if(!trig)return;
    e.preventDefault();
    if(trig.dataset.state==='loading')return;
    _start(trig);
  });
})();
</script>`;

/** Cloud dig-deeper inline engine (poll-based). Injected in place of navScript for the cloud interactive doc. */
export function digCloudScript(nonce?: string): string {
  return nonce ? DIG_CLOUD_SCRIPT.replace('<script>', `<script nonce="${nonce}">`) : DIG_CLOUD_SCRIPT;
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx jest nav-cloud-dig nav`
Expected: PASS — new cloud tests green AND the existing `nav.test.ts` still green (proves `NAV_SCRIPT` and the summary-side helpers are untouched).

- [ ] **Step 6: Verify `NAV_SCRIPT` byte-identity (no accidental edit)**

Run: `git diff lib/html-doc/nav.ts | grep -E '^[-+].*NAV_SCRIPT|^-' | head`
Expected: only **added** lines (all diff hunks are `+`); no `-` line inside the `NAV_SCRIPT` constant. If any existing line changed, revert it — the local path must stay byte-identical.

- [ ] **Step 7: Commit**

```bash
git add lib/html-doc/nav.ts tests/lib/html-doc/nav-cloud-dig.test.ts tests/lib/html-doc/nav-cloud-dig-inline.test.ts
git commit -m "feat(dig-fe): cloud poll-based dig engine in nav.ts (NAV_SCRIPT untouched)"
```

---

### Task 4: `render-dig-deeper.ts` cloud-interactive mode

Add an optional `cloud` arg. When present: emit per-section triggers (anon → disabled span), omit expand-all + summary back-link + expand-all dialogs, and inject `digCloudScript` instead of `navScript`. Absent → byte-identical.

**Files:**
- Modify: `lib/html-doc/render-dig-deeper.ts` (args type + destructure; `summaryLink`/`expandAllBtn`/`dialogs`/`nav` gates; per-section `control`; import `digCloudScript`)
- Test: `tests/lib/html-doc/render-dig-deeper.cloud.test.ts`

**Interfaces:**
- Consumes: `digCloudScript(nonce)` (Task 3).
- Produces: `renderDigDeeperDoc({ ..., cloud?: { playlistId: string; isAnonymous: boolean } })`. When `cloud` set: un-dug sections with a startSec render `<a class="dig-trigger" data-section="N">` (registered) or `<span class="dig-trigger" aria-disabled="true" title="Create an account to dig deeper">` (anonymous); the doc contains `digCloudScript` and **no** `.dg-expand-all`, **no** SSE `navScript`.

- [ ] **Step 1: Write the failing tests**

`tests/lib/html-doc/render-dig-deeper.cloud.test.ts`:
```ts
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
```

- [ ] **Step 1b: Capture a pre-change byte golden of the LOCAL render (M3 — true pre/post guard)**

The equality test above only proves the new arg is a no-op relative to itself; it can't catch an unrelated byte change to the local output. Capture a golden from the **current, unedited** `render-dig-deeper.ts`, commit it, and the Step-3 change must keep matching it.

`tests/lib/html-doc/render-dig-deeper.golden.test.ts`:
```ts
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
```
Run against the **unchanged** renderer to write the snapshot, then commit it:
```bash
npx jest render-dig-deeper.golden   # creates __snapshots__/render-dig-deeper.golden.test.ts.snap from current code
git add tests/lib/html-doc/render-dig-deeper.golden.test.ts tests/lib/html-doc/__snapshots__/render-dig-deeper.golden.test.ts.snap
git commit -m "test(dig-fe): byte golden of local dig render (pre-change baseline)"
```
The golden must be captured **before** the Step-3 edit; if you have already edited `render-dig-deeper.ts`, `git stash` it first.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest render-dig-deeper.cloud`
Expected: FAIL — `cloud` arg has no effect yet (interactive triggers/cloud script absent). (`render-dig-deeper.golden` PASSES — it pins current output.)

- [ ] **Step 3: Implement**

In `lib/html-doc/render-dig-deeper.ts`:

1. Add the import (with the existing `nav` imports):
```ts
import { navScript, digCloudScript } from './nav';
```
(Match the file's current import of `navScript` — extend it to also import `digCloudScript`.)

2. Extend the args type and destructure (add `cloud`):
```ts
export function renderDigDeeperDoc(args: {
  summary: ParsedSummary;
  envelope: ModelEnvelope | null;
  dug: DugSection[];
  mdPath: string;
  videoId: string;
  language?: 'en' | 'ko';
  cropMap?: Map<string, CropBox | null>;
  readOnly?: boolean;
  nonce?: string;
  cloud?: { playlistId: string; isAnonymous: boolean };
}): string {
  const {
    summary, envelope, dug, mdPath, videoId, language = 'en', cropMap = new Map<string, CropBox | null>(),
    readOnly = false, nonce, cloud,
  } = args;
```

3. Gate the top-bar back-link and expand-all off in cloud (change the two lines):
```ts
  const summaryLink = (readOnly || cloud) ? '' : (firstStartSec !== null
    ? digControl('summary', firstStartSec)
    : `<a class="dig" data-type="summary">↑ summary</a>`);
  const expandAllBtn = (readOnly || cloud) ? '' : `<button class="dg-expand-all">⤢ expand all</button>`;
```

4. Per-section control — inside the existing `if (!readOnly)` block, (a) suppress the stale `dig-refresh` control in cloud (the cloud script has no refresh handler and cloud only lists current-version digs, so a `↻ outdated` link would be dead), and (b) make the un-dug trigger anonymous-aware. Change the `if (isDug) { … } else if (startSec !== null) { … }` body to:
```ts
      if (isDug) {
        control = ` <a class="dig-toggle">show summary ⌃</a>`;
        if (ms.isStale && startSec !== null && !cloud) {
          control += ` <a class="dig-refresh" data-section="${startSec}">↻ outdated</a>`;
        }
      } else if (startSec !== null) {
        control = cloud?.isAnonymous
          ? ` <span class="dig-trigger" aria-disabled="true" title="Create an account to dig deeper">dig deeper ▶</span>`
          : ` <a class="dig-trigger" data-section="${startSec}">dig deeper ▶</a>`;
      }
```
(With `cloud` absent, `!cloud` is `true` and `cloud?.isAnonymous` is `undefined` → both branches are byte-identical to today.)

5. Gate the dialogs + choose the script (change the two lines near the end):
```ts
  const dialogs = (readOnly || cloud) ? '' : expandAllDialogs;
  const nav = cloud ? digCloudScript(nonce) : (readOnly ? '' : navScript(nonce));
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest render-dig-deeper`
Expected: PASS — new cloud tests green; the **golden snapshot still matches** (proves the local output is byte-unchanged); AND all existing `render-dig-deeper*` tests (including `render-dig-deeper-readonly`) still green. If the golden snapshot fails, the change altered local output — fix the change, do **not** re-record the snapshot.

- [ ] **Step 5: Commit**

```bash
git add lib/html-doc/render-dig-deeper.ts tests/lib/html-doc/render-dig-deeper.cloud.test.ts
git commit -m "feat(dig-fe): cloud-interactive render mode (triggers+poll script, anon-disabled, off=byte-identical)"
```

---

### Task 5: `app/api/html/[id]/route.ts` cloud dig-deeper interactive branch

Stop rendering the cloud dig doc read-only; render it interactive with the playlist + anonymous flag.

**Files:**
- Modify: `app/api/html/[id]/route.ts` (the `type === 'dig-deeper'` cloud branch — the `renderDigDeeperDoc({...})` call)
- Test: `tests/api/html-dig-serve.test.ts` (add interactive assertions; re-pin any obsolete read-only assertion)

**Interfaces:**
- Consumes: `renderDigDeeperDoc({ ..., cloud })` (Task 4); `user` from `supabase.auth.getUser()` and `profiles.is_anonymous` read via the same `supabase` client (both already available in the branch).

**Critical — `isAnonymous` source (Blocking B1):** the serve route must resolve `isAnonymous` from **`profiles.is_anonymous`, fail-closed**, exactly as the cloud dig **POST** route does (`app/api/videos/[id]/dig/[sectionId]/route.ts:47-61`), whose in-code comment says: *"Do NOT trust `user.is_anonymous` — it is not guaranteed to be populated in this project's auth config. Fail CLOSED: only an explicit `is_anonymous===false` grants registered access."* Using `user.is_anonymous` would make the pre-disable silently never fire. Because the route now calls `supabase.from('profiles')`, the test `mockAuth` must be widened to stub `.from` (see Step 1).

- [ ] **Step 1: Widen `mockAuth`, then write the failing tests**

First widen the existing `mockAuth` helper in `tests/api/html-dig-serve.test.ts` so the client also stubs the profiles read (the current helper only stubs `auth.getUser`; once the route reads `.from`, every dig test — including the pre-existing ones — needs it or the route 500s). Replace the helper:
```ts
// isAnon: profiles.is_anonymous value returned for a signed-in user. Undefined defaults to false
// (registered) so pre-existing tests that call mockAuth({id:'u'}) keep working; the dedicated
// null-row test below exercises the route's real fail-closed path separately.
function mockAuth(user: { id: string } | null, isAnon?: boolean) {
  (createServerSupabase as jest.Mock).mockReturnValue({
    auth: { getUser: async () => ({ data: { user } }) },
    from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: user ? { is_anonymous: isAnon ?? false } : null }) }) }) }),
  });
}
```
This is backward-compatible: the pre-existing tests call `mockAuth({ id: 'u' })` → `isAnon` undefined → `{ is_anonymous: false }` → registered (their assertions are unaffected). Then add:
```ts
it('renders the cloud dig doc INTERACTIVE (trigger + poll engine, no SSE)', async () => {
  mockAuth({ id: 'u' }, false); // registered
  (loadDigForServe as jest.Mock).mockResolvedValue({
    ok: true,
    summary: { title: 'T', sections: [
      { numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
      { numeral: '2', title: 'B', prose: 'q', timeRange: { startSec: 120, endSec: 200, label: 'l', url: 'https://youtu.be/v?t=120s' } },
    ] } as never,
    envelope: null, dug: [{ sectionId: 65, startSec: 65, title: 'A', bodyMarkdown: 'body', generatedAt: 'g', genVersion: 3, slides: [] }] as never,
    base: 'base', title: 'T', language: 'en',
  } as never);
  const res = await GET(new Request(url()), params);
  const html = await res.text();
  expect(res.status).toBe(200);
  expect(html).toContain('<a class="dig-trigger" data-section="120">'); // un-dug section 2 is clickable
  expect(html).toContain('dig-state?playlist=');                        // cloud poll engine injected
  expect(html).not.toContain('EventSource');                            // not the local SSE script
});

it('anonymous user (profiles.is_anonymous=true): dig triggers are pre-disabled spans', async () => {
  mockAuth({ id: 'u' }, true); // anonymous per profiles
  (loadDigForServe as jest.Mock).mockResolvedValue({
    ok: true,
    summary: { title: 'T', sections: [
      { numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
    ] } as never,
    envelope: null, dug: [] as never, base: 'base', title: 'T', language: 'en',
  } as never);
  const html = await (await GET(new Request(url()), params)).text();
  expect(html).toContain('aria-disabled="true" title="Create an account to dig deeper"');
  expect(html).not.toContain('<a class="dig-trigger" data-section="65">');
});

it('unresolved profile (null row) fails CLOSED → triggers pre-disabled', async () => {
  // user present but profiles read returns null → treated as anonymous (fail-closed).
  (createServerSupabase as jest.Mock).mockReturnValue({
    auth: { getUser: async () => ({ data: { user: { id: 'u' } } }) },
    from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: null }) }) }) }),
  });
  (loadDigForServe as jest.Mock).mockResolvedValue({
    ok: true,
    summary: { title: 'T', sections: [
      { numeral: '1', title: 'A', prose: 'p', timeRange: { startSec: 65, endSec: 120, label: 'l', url: 'https://youtu.be/v?t=65s' } },
    ] } as never,
    envelope: null, dug: [] as never, base: 'base', title: 'T', language: 'en',
  } as never);
  const html = await (await GET(new Request(url()), params)).text();
  expect(html).toContain('aria-disabled="true" title="Create an account to dig deeper"'); // fail-closed
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest html-dig-serve`
Expected: FAIL on the two new tests — the branch still passes `readOnly: true`, so `dig-trigger` / `dig-state?playlist=` are absent and `EventSource` never appears. Existing tests still pass.

- [ ] **Step 3: Implement**

In `app/api/html/[id]/route.ts`, in the `type === 'dig-deeper'` branch: first resolve `isAnonymous` from `profiles.is_anonymous` (fail-closed, mirroring the POST route), then replace the `renderDigDeeperDoc({...})` call (currently passing `readOnly: true`) so it passes `cloud` instead. Use the SAME `supabase` client the branch already created via `createServerSupabase` (the one it called `.auth.getUser()` on) and the `user` from that call:
```ts
    // Authoritative anon status = profiles.is_anonymous, read fail-closed — the SAME source and
    // semantics the cloud dig POST route uses (dig/[sectionId]/route.ts:47-61). Do NOT trust
    // user.is_anonymous (not reliably populated here). A null/errored profile ⇒ treat as anonymous.
    const { data: profile } = await supabase.from('profiles').select('is_anonymous').eq('id', user.id).single();
    const html = renderDigDeeperDoc({
      summary: load.summary,
      envelope: load.envelope,
      dug: load.dug,
      nonce,
      videoId,
      language: load.language,
      mdPath: `${load.base}.md`,
      cloud: { playlistId, isAnonymous: profile?.is_anonymous !== false },
    });
```
Remove the `readOnly: true` property. Match the actual in-file names for the client (`supabase`) and user (`user`) if they differ. Everything else in the branch (the `format` guard, `loadDigForServe`, `fileResponse`, CSP, error mapping) is unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest html-dig-serve html-serve-cloud`
Expected: PASS. If any pre-existing assertion pinned the read-only contract (e.g. asserted the served dig doc does **not** contain `dig-trigger` or navScript), re-pin it to the interactive contract — that assertion was pinning behaviour this slice intentionally changes (analogous to the B14 re-pin in the serving slice). Do not delete coverage; update it to assert the new interactive output.

- [ ] **Step 5: Full suite + tsc**

Run: `npm test` then `npx tsc --noEmit; echo "tsc exit=$?"`
Expected: full suite green; `tsc exit=0`.

- [ ] **Step 6: Commit**

```bash
git add app/api/html/[id]/route.ts tests/api/html-dig-serve.test.ts
git commit -m "feat(dig-fe): serve cloud dig doc interactive (playlist + isAnonymous), drop readOnly"
```

---

### Task 6: Real-Supabase interactive-doc integration test

End-to-end proof against real local Supabase: seed a promoted video + one dig blob, GET `type=dig-deeper`, assert the doc is interactive (trigger + poll engine, nonced CSP) and that opening it charges nothing (`spend_ledger` unchanged). This closes the serve-path integration-test gap the serving slice noted.

**Files:**
- Create: `tests/integration/dig-serve-interactive.test.ts`

**Interfaces:**
- Consumes the integration harness: `seedPlaylist`, `seedPromotedVideo`, `seedSummaryBlob`, the dig-blob writer used by the generation tests (`writeDigSectionBlob` or equivalent), `adminClient`/`newUser`/`signInAs`, and the `createServerSupabase`/`next/headers` route mocks used by the other files in `tests/integration/`. Match the exact import paths and helper names already present in `tests/integration/` (read a sibling file such as the dig-generation or share integration test first).

- [ ] **Step 1: Write the test**

`tests/integration/dig-serve-interactive.test.ts` (adapt helper names to the sibling integration files):
```ts
import { GET as htmlGET } from '@/app/api/html/[id]/route';
// + integration harness imports (seedPlaylist, seedPromotedVideo, seedSummaryBlob, dig-blob writer,
//   newUser, signInAs, adminClient) — copy the exact names/paths from a sibling tests/integration file.

const VIDEO_ID = 'digIntgVid01';   // ≤20 chars, matches assertVideoId /^[A-Za-z0-9_-]{1,20}$/

it('serves an interactive cloud dig doc and charges nothing', async () => {
  const user = await newUser();
  const { playlistId } = await seedPlaylist(user);
  await seedPromotedVideo(user, playlistId, VIDEO_ID);       // summaryReady/promoted summary blob
  await seedSummaryBlob(user, playlistId, VIDEO_ID);         // if separate from seedPromotedVideo in the harness
  // writeDigSectionBlob MUST write at the current DIG_GENERATOR_VERSION → key dig/{base}/65.r{V}.md,
  // the version dig-state/route.ts filters on. If it writes an older version, loadDigForServe treats
  // the section as un-dug (renders a trigger, not DUG-PROSE) and this test fails. Confirm the helper
  // stamps DIG_GENERATOR_VERSION (that is how the generation writer produces it).
  await writeDigSectionBlob(user, playlistId, VIDEO_ID, 65, '# Dug\n\nDUG-PROSE');  // one current-version dig blob

  const before = await adminClient.from('spend_ledger').select('amount_cents');
  signInAs(user);
  const res = await htmlGET(
    new Request(`http://x/api/html/${VIDEO_ID}?playlist=${playlistId}&type=dig-deeper`),
    { params: Promise.resolve({ id: VIDEO_ID }) },
  );
  const html = await res.text();
  // Also poll dig-state (the interactive doc's progress mechanism) — it must be charge-free too (L1).
  const { GET: digStateGET } = await import('@/app/api/videos/[id]/dig-state/route');
  const stateRes = await digStateGET(
    new Request(`http://x/api/videos/${VIDEO_ID}/dig-state?playlist=${playlistId}`),
    { params: Promise.resolve({ id: VIDEO_ID }) },
  );
  const after = await adminClient.from('spend_ledger').select('amount_cents');

  expect(res.status).toBe(200);
  expect(res.headers.get('Content-Security-Policy')).toContain("script-src 'nonce-");
  expect(html).toContain('DUG-PROSE');                       // dug section rendered
  expect(html).toContain('dig-state?playlist=');             // cloud poll engine present (interactive)
  expect(html).not.toContain('EventSource');                 // not the local SSE script
  expect((await stateRes.json()).sectionIds).toContain(65);  // dig-state sees the dug section
  const sum = (rows: { amount_cents: number }[]) => rows.reduce((a, r) => a + r.amount_cents, 0);
  expect(sum(after.data ?? [])).toBe(sum(before.data ?? [])); // opening the doc AND polling charged nothing
});
```
(Adjust the `dig-state` GET's second-arg shape to match how the sibling integration tests invoke route handlers, if different.)

- [ ] **Step 2: Run it**

Run: `npm run test:integration -- dig-serve-interactive`
Expected: PASS. If it fails on a seed/helper name, reconcile against the sibling integration file's exports (do not invent helpers). If a section id > 20 chars or a videoId > 20 chars is used, `assertVideoId` returns 400 — keep ids short.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/dig-serve-interactive.test.ts
git commit -m "test(dig-fe): integration — interactive cloud dig doc renders and charges nothing"
```

---

## Post-implementation gate

After Task 6, before any push/merge (human gate):

- [ ] Full suite green (`npm test`) + `npx tsc --noEmit` exit 0.
- [ ] **Whole-branch dual adversarial review to convergence** (Codex + Claude, independent) — **mandatory** because `lib/html-doc/*` shared code changed. Explicitly verify: (a) `NAV_SCRIPT` and the off/local render path are **byte-identical** to pre-branch; (b) the **money invariant** holds (serving/opening/polling never charge; only the pre-existing POST spends); (c) the anonymous pre-disable + `403` fallback both hold; (d) the poll timeout ceiling prevents an unbounded poll. Save rounds to `docs/reviews/`.
- [ ] Address all Blocking/High; re-review until a round returns none new.
- [ ] Notify the human (PushNotification) at convergence; push/PR/merge remains the human gate.

---

## Self-Review

**Spec coverage:** §3 D1 → Tasks 3–5 (interactive doc); D2 (no confirm) → Task 3 flow has no confirm; D3 (anon pre-disable + 403) → Task 4 (span) + Task 5 (profiles fail-closed source, 3 tests incl. null-row) + Task 3 (403 message); D4 (no expand-all) → Task 4 gates the expand-all button off + Task 3 script has no expand-all. §4 non-blocking → per-section trigger only, no overlay. §5 URL contracts → Tasks 1 (menu href), 3 (POST/poll/re-fetch). §6 states/dismissal → Task 3 error map + toggle. §7 mechanics → Tasks 3–5. §9 behaviors 1–15 → covered: 1 (T1), 2–4 (T2), 5–6 (T4 incl. golden + stale-refresh), 7 (T4/T5), 8–9 (T3 helper + T3 inline execution), 10 (T3), 11 (T3 429/503), 12 (T3 404/409 + network-reject + over-report swap-throw), 13 (T3 timeout), 14 (T3 inline re-POST after 429), 15 (T3 inline toggle). §10 testing → Tasks per-file + T6 integration (serve + dig-state no-charge). §11 files → all five + integration. **No gaps.**

**Placeholder scan:** every code step contains complete code; no TBD/"handle errors"/"similar to". Poll constants are exact. The one deliberate "adapt to sibling" is Task 6's harness import names — unavoidable (the integration harness names live in that suite) and bounded by "read a sibling file; do not invent helpers."

**Type consistency:** `CloudDigEnv`, `startCloudDig`, `swapDugSection`, `pollUntilDug`, `applyCloudDigError`, `digCloudScript` names identical across Tasks 3–4. `cloud: { playlistId: string; isAnonymous: boolean }` identical across Tasks 4–5. `digHref(playlistId, videoId)` identical across Tasks 1–2.
