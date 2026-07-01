# Title-Primary Playlist Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the playlist **title** the primary label in the Header (with a muted, clickable full URL beneath it), and move free-text URL paste behind a collapsible "+ Add by link" disclosure — while the recent/channel picker stays visible as a `▾` dropdown.

**Architecture:** Split the one-input `PlaylistPicker` into two focused pieces: a pick-only `▾ Recent` dropdown (recent + channel-browse, two-line rows) and a new `AddByLink` disclosure that owns the paste field. A new presentational `CurrentPlaylist` block renders the prominent title + muted URL anchor. Header keeps its existing `playlistUrl` state and resolve/Fetch/Sync machinery unchanged — both the dropdown pick and the paste field feed the same `playlistUrl`. A pure `playlistDisplayTitle` helper supplies the title-fallback chain.

**Tech Stack:** Next.js 16 (App Router, client components), React, TypeScript, Jest + ts-jest (SWC runner — no typecheck at test time), @testing-library/react, Playwright.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-01-title-primary-playlist-display-design.md`. Display-only — no change to playlist resolution, ingestion, the folder/slug scheme, the data model, or any API.
- Playlist identity stays `list=<id>` in `PlaylistOption.id` / stored `playlistUrl`. The muted URL is presentational for picker rows; for the current playlist it is a real navigable `<a href>`.
- Title fallback chain: explicit title → folder slug (from resolved `<root>/<slug>/raw` target) → `"Untitled playlist"` (matches `lib/playlists/recent-provider.ts:33`).
- Muted current-playlist URL anchor MUST be `target="_blank" rel="noopener noreferrer"` with a `title=` attribute (full URL on hover) and `truncate`.
- The paste field placeholder MUST contain the text `Paste a playlist URL` so the existing E2E selector `getByPlaceholder(/Paste a playlist URL/)` keeps resolving.
- Jest uses SWC (no typecheck); `npx tsc --noEmit` is the real type gate — run it before every commit and check its exit code explicitly (`; echo "exit: $?"`), never through a pipe (a pipe reports the last command's exit, masking tsc failures).
- Tokens (from spec `## UI Design`): current title `text-sm text-zinc-100` (drop the `▶` prefix); current URL `text-xs text-zinc-500` link `hover:underline truncate`; picker row title `text-sm text-zinc-200 truncate`; picker row URL `text-xs text-zinc-500 truncate`; "+ Add by link" toggle `text-xs text-zinc-400 hover:text-zinc-200`.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `lib/playlists/display-title.ts` | Pure title-fallback resolver | Create |
| `components/PlaylistPicker.tsx` | Pick-only `▾ Recent` dropdown (recent + channel browse), two-line rows | Rewrite (drop paste input; new props) |
| `components/ChannelPlaylistPanel.tsx` | Channel-browse modal — result rows go two-line | Modify (rows only) |
| `components/AddByLink.tsx` | Collapsible paste-URL disclosure (Escape/blur/auto-collapse) | Create |
| `components/CurrentPlaylist.tsx` | Prominent title + muted URL anchor block | Create |
| `components/Header.tsx` | Compose the three above; own `addByLinkOpen`; unchanged resolve/Fetch/Sync | Modify |
| `tests/lib/playlists/display-title.test.ts` | Unit tests for the helper | Create |
| `tests/components/PlaylistPicker.test.tsx` | Component tests (rewrite for new API) | Modify |
| `tests/components/ChannelPlaylistPanel.test.tsx` | Component tests for two-line rows | Create |
| `tests/components/AddByLink.test.tsx` | Component tests for the disclosure | Create |
| `tests/components/CurrentPlaylist.test.tsx` | Component tests for the block | Create |
| `tests/components/Header-picker.test.tsx` | Header integration tests (update) | Modify |
| `tests/e2e/playlist-picker.spec.ts` | E2E: pick via `▾`, add-by-link collapse, channel browse | Modify |

---

### Task 1: `playlistDisplayTitle` helper

**Files:**
- Create: `lib/playlists/display-title.ts`
- Test: `tests/lib/playlists/display-title.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `playlistDisplayTitle(title?: string, folderTarget?: string): string` — returns the trimmed `title` if non-empty; else the folder slug parsed from `folderTarget` (the `<slug>` segment of `<root>/<slug>/raw`, or the last segment if there is no `raw` leaf); else `"Untitled playlist"`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Explicit title wins | `title="건강"`, any target | `"건강"` |
| 2 | Title trimmed | `title="  Agentic AI  "` | `"Agentic AI"` |
| 3 | Whitespace title → fallback | `title="   "`, target `/a/b/건강/raw` | `"건강"` |
| 4 | Slug from `/raw` target | title empty, `/data/plugins/건강/raw` | `"건강"` |
| 5 | Slug from non-`/raw` target | title empty, `/data/plugins/건강` | `"건강"` |
| 6 | Trailing slash tolerated | title empty, `/data/plugins/건강/raw/` | `"건강"` |
| 7 | No title, no target | both absent | `"Untitled playlist"` |
| 8 | Empty-string target | title empty, `""` | `"Untitled playlist"` |

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/playlists/display-title.test.ts
import { playlistDisplayTitle } from '../../../lib/playlists/display-title';

describe('playlistDisplayTitle', () => {
  it('returns the explicit title when present', () => {
    expect(playlistDisplayTitle('건강', '/data/plugins/x/raw')).toBe('건강');
  });
  it('trims the title', () => {
    expect(playlistDisplayTitle('  Agentic AI  ')).toBe('Agentic AI');
  });
  it('falls back to the folder slug when the title is blank', () => {
    expect(playlistDisplayTitle('   ', '/data/plugins/건강/raw')).toBe('건강');
  });
  it('parses the slug from a canonical <slug>/raw target', () => {
    expect(playlistDisplayTitle(undefined, '/data/plugins/건강/raw')).toBe('건강');
  });
  it('uses the last segment when there is no raw leaf', () => {
    expect(playlistDisplayTitle(undefined, '/data/plugins/건강')).toBe('건강');
  });
  it('tolerates a trailing slash', () => {
    expect(playlistDisplayTitle(undefined, '/data/plugins/건강/raw/')).toBe('건강');
  });
  it('returns "Untitled playlist" with no title and no target', () => {
    expect(playlistDisplayTitle()).toBe('Untitled playlist');
  });
  it('returns "Untitled playlist" for an empty target', () => {
    expect(playlistDisplayTitle('', '')).toBe('Untitled playlist');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest display-title -v`
Expected: FAIL — `Cannot find module '../../../lib/playlists/display-title'`.

- [ ] **Step 3: Write the implementation**

```ts
// lib/playlists/display-title.ts
/**
 * Human-facing playlist title with a fallback chain.
 * Priority: explicit title → folder slug (from a resolved `<root>/<slug>/raw` target)
 * → "Untitled playlist". When the target ends in the canonical `/raw` leaf the slug is
 * its parent segment; otherwise it is the last path segment.
 */
export function playlistDisplayTitle(title?: string, folderTarget?: string): string {
  const t = (title ?? '').trim();
  if (t) return t;
  return folderSlug(folderTarget) || 'Untitled playlist';
}

function folderSlug(target?: string): string {
  if (!target) return '';
  const parts = target.split('/').filter(Boolean);
  if (parts.length === 0) return '';
  const last = parts[parts.length - 1];
  if (last === 'raw' && parts.length >= 2) return parts[parts.length - 2];
  return last;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest display-title -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Type-check + commit**

```bash
npx tsc --noEmit ; echo "tsc exit: $?"   # must be 0
git add lib/playlists/display-title.ts tests/lib/playlists/display-title.test.ts
git commit -m "feat: playlistDisplayTitle fallback helper (title → slug → Untitled)"
```

---

### Task 2: `PlaylistPicker` → pick-only `▾ Recent` dropdown with two-line rows

**Files:**
- Modify: `components/PlaylistPicker.tsx` (full rewrite)
- Test: `tests/components/PlaylistPicker.test.tsx` (rewrite)

**Interfaces:**
- Consumes: `PlaylistOption` from `lib/playlists/types` (`{ id, title, url, source, meta? }`); `GET /api/playlists/recent?root=<enc>` → `{ playlists: PlaylistOption[] }`.
- Produces: `PlaylistPicker(props: { root: string; onPick: (url: string) => void; onBrowseChannel: () => void; disabled?: boolean })`. **Breaking:** removes the `value` and `onChange` props (the paste field moves to `AddByLink`). Renders a `▾ Recent` `<button>` that toggles a dropdown; picking a row calls `onPick(option.url)`; the footer calls `onBrowseChannel()`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Opens on button click | click `▾ Recent` | dropdown appears, `loadRecent()` fetched |
| 2 | Rows are two-line | options loaded | each row shows `title` line + muted `url` line |
| 3 | Shows titles not ids | options loaded | `title` text present, `id` text absent |
| 4 | Pick calls onPick(url) | click a row | `onPick(option.url)`, dropdown closes |
| 5 | Option without url | option `url` empty/absent | title line only, no url line |
| 6 | Footer browses channel | click footer row | `onBrowseChannel()`, dropdown closes |
| 7 | Outside click closes | mousedown outside box | dropdown closes |
| 8 | Disabled | `disabled` true | toggle button disabled |
| 9 | No root | `root=""` | click opens dropdown but no fetch (guard) |

- [ ] **Step 1: Write the failing tests**

```tsx
// tests/components/PlaylistPicker.test.tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import PlaylistPicker from '../../components/PlaylistPicker';

const options = [
  { id: 'PLa', title: 'Building with Claude', url: 'https://youtube.com/playlist?list=PLa', source: 'recent', meta: { videoCount: 114 } },
  { id: 'PLn', title: 'No URL Playlist', url: '', source: 'recent', meta: {} },
];
beforeEach(() => { global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ playlists: options }) })) as unknown as typeof fetch; });

it('opens the dropdown on button click and shows titles (not ids)', async () => {
  render(<PlaylistPicker root="/home/x/data" onPick={() => {}} onBrowseChannel={() => {}} />);
  fireEvent.click(screen.getByRole('button', { name: /Recent/ }));
  expect(await screen.findByText('Building with Claude')).toBeInTheDocument();
  expect(screen.queryByText('PLa')).not.toBeInTheDocument();
});
it('renders each option as title + muted URL line', async () => {
  render(<PlaylistPicker root="/home/x/data" onPick={() => {}} onBrowseChannel={() => {}} />);
  fireEvent.click(screen.getByRole('button', { name: /Recent/ }));
  expect(await screen.findByText('Building with Claude')).toBeInTheDocument();
  expect(screen.getByText('https://youtube.com/playlist?list=PLa')).toBeInTheDocument();
});
it('an option without a url renders the title only', async () => {
  render(<PlaylistPicker root="/home/x/data" onPick={() => {}} onBrowseChannel={() => {}} />);
  fireEvent.click(screen.getByRole('button', { name: /Recent/ }));
  expect(await screen.findByText('No URL Playlist')).toBeInTheDocument();
  // exactly one muted url line (from the first option only)
  expect(screen.getAllByText(/youtube\.com\/playlist/).length).toBe(1);
});
it('selecting an option calls onPick with the url', async () => {
  const onPick = jest.fn();
  render(<PlaylistPicker root="/home/x/data" onPick={onPick} onBrowseChannel={() => {}} />);
  fireEvent.click(screen.getByRole('button', { name: /Recent/ }));
  fireEvent.click(await screen.findByText('Building with Claude'));
  expect(onPick).toHaveBeenCalledWith('https://youtube.com/playlist?list=PLa');
});
it('footer row triggers onBrowseChannel', async () => {
  const onBrowseChannel = jest.fn();
  render(<PlaylistPicker root="/home/x/data" onPick={() => {}} onBrowseChannel={onBrowseChannel} />);
  fireEvent.click(screen.getByRole('button', { name: /Recent/ }));
  fireEvent.click(await screen.findByText(/Browse a channel/i));
  expect(onBrowseChannel).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest PlaylistPicker -v`
Expected: FAIL — old component still renders a textbox with `value`/`onChange`; no `▾ Recent` button role, url line assertions fail.

- [ ] **Step 3: Rewrite the component**

```tsx
// components/PlaylistPicker.tsx
'use client';
import { useEffect, useRef, useState } from 'react';
import type { PlaylistOption } from '../lib/playlists/types';

type Props = {
  root: string;
  onPick: (url: string) => void;
  onBrowseChannel: () => void;
  disabled?: boolean;
};

export default function PlaylistPicker({ root, onPick, onBrowseChannel, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<PlaylistOption[]>([]);
  const boxRef = useRef<HTMLDivElement>(null);

  async function loadRecent() {
    if (!root) return;
    try {
      const res = await fetch(`/api/playlists/recent?root=${encodeURIComponent(root)}`);
      if (!res.ok) return;
      setOptions(((await res.json()).playlists ?? []) as PlaylistOption[]);
    } catch { /* leave options empty */ }
  }

  useEffect(() => {
    function onDocClick(e: MouseEvent) { if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  function toggle() {
    setOpen((o) => {
      const next = !o;
      if (next) loadRecent();
      return next;
    });
  }

  return (
    <div ref={boxRef} className="relative shrink-0">
      <button
        type="button" disabled={disabled} onClick={toggle} aria-expanded={open}
        className="rounded bg-zinc-800 border border-zinc-700 hover:border-zinc-500 disabled:opacity-40 disabled:cursor-not-allowed px-3 py-2 text-sm text-zinc-300 transition-colors whitespace-nowrap"
      >
        ▾ Recent
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-80 rounded border border-zinc-700 bg-zinc-900 shadow-lg">
          {options.length > 0 && <div className="px-3 py-1 text-[10px] uppercase tracking-wide text-zinc-500">Recent</div>}
          {options.map((o) => (
            <button key={o.id} type="button" onClick={() => { onPick(o.url); setOpen(false); }}
              className="flex w-full flex-col items-start px-3 py-2 text-left hover:bg-zinc-800">
              <span className="w-full truncate text-sm text-zinc-200">{o.title}</span>
              {o.url && <span className="w-full truncate text-xs text-zinc-500" title={o.url}>{o.url}</span>}
            </button>
          ))}
          <div className="border-t border-zinc-800" />
          <button type="button" onClick={() => { onBrowseChannel(); setOpen(false); }}
            className="flex w-full items-center px-3 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-800">
            🔍 Browse a channel&apos;s playlists…
          </button>
        </div>
      )}
    </div>
  );
}
```

Note: the per-row `videoCount` badge is intentionally dropped — the spec redesigned rows to title + muted URL only.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest PlaylistPicker -v`
Expected: PASS (5 tests). (Header still references old props → its file won't compile in the app, but jest/SWC won't typecheck; Header is fixed in Task 5. Do NOT run the full suite yet — `Header-picker.test.tsx` is updated in Task 5.)

- [ ] **Step 5: Commit**

```bash
git add components/PlaylistPicker.tsx tests/components/PlaylistPicker.test.tsx
git commit -m "feat: PlaylistPicker → pick-only ▾ Recent dropdown with two-line rows"
```

---

### Task 2b: `ChannelPlaylistPanel` two-line rows

**Files:**
- Modify: `components/ChannelPlaylistPanel.tsx` (result rows only)
- Test: `tests/components/ChannelPlaylistPanel.test.tsx`

**Interfaces:**
- Consumes: `PlaylistOption` from `lib/playlists/types`; `GET /api/playlists/channel?handle=<enc>` → `{ channelTitle, playlists: PlaylistOption[] }`.
- Produces: unchanged component API (`{ onSelect, onClose }`); result rows now render `title` + muted `url` line (mirrors Task 2), replacing the title + `videoCount` layout.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Result rows two-line | channel search returns playlists | each row shows `title` line + muted `url` line |
| 2 | Option without url | result `url` empty | title line only, no url line |
| 3 | Pick still works | click a result row | `onSelect(option.url)` then `onClose()` |

- [ ] **Step 1: Write the failing tests**

```tsx
// tests/components/ChannelPlaylistPanel.test.tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChannelPlaylistPanel from '../../components/ChannelPlaylistPanel';

const body = { channelTitle: 'Anthropic', playlists: [
  { id: 'PLc', title: 'Research Talks', url: 'https://youtube.com/playlist?list=PLc', source: 'channel', meta: { videoCount: 31 } },
] };
beforeEach(() => { global.fetch = jest.fn(async () => ({ ok: true, status: 200, json: async () => body })) as unknown as typeof fetch; });

async function search() {
  render(<ChannelPlaylistPanel onSelect={jest.fn()} onClose={jest.fn()} />);
  fireEvent.change(screen.getByPlaceholderText(/@channel/), { target: { value: '@Anthropic' } });
  fireEvent.click(screen.getByText('Go'));
  await screen.findByText('Research Talks');
}

it('renders result rows as title + muted URL line', async () => {
  await search();
  expect(screen.getByText('Research Talks')).toBeInTheDocument();
  expect(screen.getByText('https://youtube.com/playlist?list=PLc')).toBeInTheDocument();
});
it('picking a result calls onSelect with the url and closes', async () => {
  const onSelect = jest.fn(); const onClose = jest.fn();
  render(<ChannelPlaylistPanel onSelect={onSelect} onClose={onClose} />);
  fireEvent.change(screen.getByPlaceholderText(/@channel/), { target: { value: '@Anthropic' } });
  fireEvent.click(screen.getByText('Go'));
  fireEvent.click(await screen.findByText('Research Talks'));
  expect(onSelect).toHaveBeenCalledWith('https://youtube.com/playlist?list=PLc');
  expect(onClose).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest ChannelPlaylistPanel -v`
Expected: FAIL — the muted URL line assertion fails (rows currently show title + `31 videos`).

- [ ] **Step 3: Update the result-row markup**

Replace the results `.map` block (lines 68–73) in `components/ChannelPlaylistPanel.tsx`:

```tsx
              {results.map((o) => (
                <button key={o.id} type="button" onClick={() => { onSelect(o.url); onClose(); }}
                  className="flex w-full items-center justify-between px-2 py-2 text-left text-sm hover:bg-zinc-800">
                  <span className="truncate">{o.title}</span>
                  {o.meta?.videoCount != null && <span className="ml-2 shrink-0 text-xs text-zinc-500">{o.meta.videoCount} videos</span>}
                </button>
              ))}
```

with:

```tsx
              {results.map((o) => (
                <button key={o.id} type="button" onClick={() => { onSelect(o.url); onClose(); }}
                  className="flex w-full flex-col items-start px-2 py-2 text-left hover:bg-zinc-800">
                  <span className="w-full truncate text-sm text-zinc-100">{o.title}</span>
                  {o.url && <span className="w-full truncate text-xs text-zinc-500" title={o.url}>{o.url}</span>}
                </button>
              ))}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest ChannelPlaylistPanel -v`
Expected: PASS.

- [ ] **Step 5: Type-check + commit**

```bash
npx tsc --noEmit ; echo "tsc exit: $?"   # must be 0
git add components/ChannelPlaylistPanel.tsx tests/components/ChannelPlaylistPanel.test.tsx
git commit -m "feat: ChannelPlaylistPanel result rows → title + muted URL"
```

---

### Task 3: `AddByLink` disclosure

**Files:**
- Create: `components/AddByLink.tsx`
- Test: `tests/components/AddByLink.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `AddByLink(props: { value: string; onChange: (v: string) => void; open: boolean; onOpenChange: (open: boolean) => void; disabled?: boolean; currentUrl?: string })`. Controlled disclosure: renders a `+ Add by link` toggle; when `open`, renders the paste `<input>` (auto-focused). Escape → `onOpenChange(false)`. Blur → `onOpenChange(false)` only if the trimmed value is empty or equals the trimmed `currentUrl` (never traps a half-typed new URL). Toggle click flips `onOpenChange(!open)`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Collapsed by default | `open=false` | toggle visible, no input |
| 2 | Toggle opens | click toggle when `open=false` | `onOpenChange(true)` |
| 3 | Toggle closes | click toggle when `open=true` | `onOpenChange(false)` |
| 4 | Input shown when open | `open=true` | input with placeholder containing `Paste a playlist URL` |
| 5 | Auto-focus on open | `open` becomes true | input is `document.activeElement` |
| 6 | Typing propagates | change input | `onChange(newValue)` |
| 7 | Escape collapses | Escape keydown in input | `onOpenChange(false)`, default prevented |
| 8 | Blur empty collapses | blur, `value=""` | `onOpenChange(false)` |
| 9 | Blur unchanged collapses | blur, `value===currentUrl` | `onOpenChange(false)` |
| 10 | Blur new value stays | blur, `value` set & `!==currentUrl` | `onOpenChange` NOT called |
| 11 | Disabled | `disabled=true` | toggle + input disabled |

- [ ] **Step 1: Write the failing tests**

```tsx
// tests/components/AddByLink.test.tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import AddByLink from '../../components/AddByLink';

const base = { value: '', onChange: () => {}, open: false, onOpenChange: () => {} };

it('is collapsed by default (toggle, no input)', () => {
  render(<AddByLink {...base} />);
  expect(screen.getByRole('button', { name: /Add by link/ })).toBeInTheDocument();
  expect(screen.queryByPlaceholderText(/Paste a playlist URL/)).toBeNull();
});
it('toggle opens when closed', () => {
  const onOpenChange = jest.fn();
  render(<AddByLink {...base} onOpenChange={onOpenChange} />);
  fireEvent.click(screen.getByRole('button', { name: /Add by link/ }));
  expect(onOpenChange).toHaveBeenCalledWith(true);
});
it('toggle closes when open', () => {
  const onOpenChange = jest.fn();
  render(<AddByLink {...base} open onOpenChange={onOpenChange} />);
  fireEvent.click(screen.getByRole('button', { name: /Add by link/ }));
  expect(onOpenChange).toHaveBeenCalledWith(false);
});
it('shows and auto-focuses the input when open', () => {
  render(<AddByLink {...base} open />);
  const input = screen.getByPlaceholderText(/Paste a playlist URL/);
  expect(input).toBeInTheDocument();
  expect(document.activeElement).toBe(input);
});
it('propagates typing', () => {
  const onChange = jest.fn();
  render(<AddByLink {...base} open onChange={onChange} />);
  fireEvent.change(screen.getByPlaceholderText(/Paste a playlist URL/), { target: { value: 'https://youtube.com/playlist?list=PLx' } });
  expect(onChange).toHaveBeenCalledWith('https://youtube.com/playlist?list=PLx');
});
it('Escape collapses', () => {
  const onOpenChange = jest.fn();
  render(<AddByLink {...base} open onOpenChange={onOpenChange} />);
  fireEvent.keyDown(screen.getByPlaceholderText(/Paste a playlist URL/), { key: 'Escape' });
  expect(onOpenChange).toHaveBeenCalledWith(false);
});
it('blur collapses when empty', () => {
  const onOpenChange = jest.fn();
  render(<AddByLink {...base} open value="" onOpenChange={onOpenChange} />);
  fireEvent.blur(screen.getByPlaceholderText(/Paste a playlist URL/));
  expect(onOpenChange).toHaveBeenCalledWith(false);
});
it('blur collapses when value equals the current url', () => {
  const onOpenChange = jest.fn();
  render(<AddByLink {...base} open value="https://youtube.com/playlist?list=PLc" currentUrl="https://youtube.com/playlist?list=PLc" onOpenChange={onOpenChange} />);
  fireEvent.blur(screen.getByPlaceholderText(/Paste a playlist URL/));
  expect(onOpenChange).toHaveBeenCalledWith(false);
});
it('blur keeps open for a new half-typed url', () => {
  const onOpenChange = jest.fn();
  render(<AddByLink {...base} open value="https://youtube.com/playlist?list=PLnew" currentUrl="" onOpenChange={onOpenChange} />);
  fireEvent.blur(screen.getByPlaceholderText(/Paste a playlist URL/));
  expect(onOpenChange).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest AddByLink -v`
Expected: FAIL — `Cannot find module '../../components/AddByLink'`.

- [ ] **Step 3: Write the component**

```tsx
// components/AddByLink.tsx
'use client';
import { useEffect, useRef } from 'react';

type Props = {
  value: string;
  onChange: (v: string) => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  disabled?: boolean;
  /** The active playlist URL; blur with an empty or unchanged field collapses. */
  currentUrl?: string;
};

export default function AddByLink({ value, onChange, open, onOpenChange, disabled, currentUrl }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') { e.preventDefault(); onOpenChange(false); }
  }
  function onBlur() {
    const v = value.trim();
    if (v === '' || v === (currentUrl ?? '').trim()) onOpenChange(false);
  }

  return (
    <div className="flex-1">
      <button
        type="button" disabled={disabled} aria-expanded={open}
        onClick={() => onOpenChange(!open)}
        className="text-xs text-zinc-400 hover:text-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        + Add by link
      </button>
      {open && (
        <input
          ref={inputRef} type="text" value={value} disabled={disabled}
          placeholder="Paste a playlist URL…"
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={onBlur}
          className="mt-1 w-full rounded bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest AddByLink -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Type-check + commit**

```bash
npx tsc --noEmit ; echo "tsc exit: $?"   # must be 0
git add components/AddByLink.tsx tests/components/AddByLink.test.tsx
git commit -m "feat: AddByLink disclosure (Escape/blur/toggle collapse)"
```

---

### Task 4: `CurrentPlaylist` block

**Files:**
- Create: `components/CurrentPlaylist.tsx`
- Test: `tests/components/CurrentPlaylist.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `CurrentPlaylist(props: { title: string; url?: string })`. Renders a prominent title line; when `url` is present, a muted `<a href={url} target="_blank" rel="noopener noreferrer" title={url}>` beneath it. When `url` is absent, no anchor.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Renders title | `title="건강"` | title text present |
| 2 | URL anchor when present | `url` set | `<a>` with `href=url`, `target=_blank`, `rel` has `noopener` + `noreferrer` |
| 3 | URL in title attr | `url` set | anchor `title` attribute equals url |
| 4 | No anchor when url absent | `url` undefined | no `link` role |

- [ ] **Step 1: Write the failing tests**

```tsx
// tests/components/CurrentPlaylist.test.tsx
/** @jest-environment jsdom */
import { render, screen } from '@testing-library/react';
import CurrentPlaylist from '../../components/CurrentPlaylist';

it('renders the title', () => {
  render(<CurrentPlaylist title="건강" />);
  expect(screen.getByText('건강')).toBeInTheDocument();
});
it('renders a muted URL anchor opening YouTube in a new tab', () => {
  const url = 'https://youtube.com/playlist?list=PL837';
  render(<CurrentPlaylist title="건강" url={url} />);
  const link = screen.getByRole('link');
  expect(link).toHaveAttribute('href', url);
  expect(link).toHaveAttribute('target', '_blank');
  expect(link.getAttribute('rel')).toContain('noopener');
  expect(link.getAttribute('rel')).toContain('noreferrer');
  expect(link).toHaveAttribute('title', url);
});
it('omits the anchor when no url is given', () => {
  render(<CurrentPlaylist title="건강" />);
  expect(screen.queryByRole('link')).toBeNull();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest CurrentPlaylist -v`
Expected: FAIL — `Cannot find module '../../components/CurrentPlaylist'`.

- [ ] **Step 3: Write the component**

```tsx
// components/CurrentPlaylist.tsx
type Props = { title: string; url?: string };

export default function CurrentPlaylist({ title, url }: Props) {
  return (
    <div className="pl-1">
      <p className="truncate text-sm text-zinc-100">{title}</p>
      {url && (
        <a
          href={url} target="_blank" rel="noopener noreferrer" title={url}
          className="block truncate text-xs text-zinc-500 hover:underline"
        >
          {url}
        </a>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest CurrentPlaylist -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Type-check + commit**

```bash
npx tsc --noEmit ; echo "tsc exit: $?"   # must be 0
git add components/CurrentPlaylist.tsx tests/components/CurrentPlaylist.test.tsx
git commit -m "feat: CurrentPlaylist block (prominent title + muted URL anchor)"
```

---

### Task 5: Wire the three pieces into `Header`

> **Behaviors adversarial review (conditional):** this task has multiple interacting async paths (empty-state auto-open, auto-collapse on resolve, pick vs paste both feeding `playlistUrl`). After enumerating behaviors and before writing tests, run a Codex (or Claude-fallback) adversarial review of the behaviors table.

**Files:**
- Modify: `components/Header.tsx`
- Test: `tests/components/Header-picker.test.tsx`

**Interfaces:**
- Consumes: `playlistDisplayTitle` (Task 1); `PlaylistPicker` new API `{ root, onPick, onBrowseChannel, disabled }` (Task 2); `AddByLink` `{ value, onChange, open, onOpenChange, disabled, currentUrl }` (Task 3); `CurrentPlaylist` `{ title, url? }` (Task 4).
- Produces: unchanged Header props (`HeaderProps`), unchanged resolve/Fetch/Sync behavior. Internal additions: `addByLinkOpen` state, `emptyInitRef`, `hasCurrentPlaylist`, `displayTitle`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Prominent title (no ▶) | `currentPlaylistTitle` set | title text shown; no `▶` prefix |
| 2 | Muted URL anchor | `currentPlaylistUrl` set | `<a href>` link rendered near the title |
| 3 | Title fallback | `currentPlaylistUrl` set, title empty, no target | shows `Untitled playlist` + URL |
| 4 | Block hidden when fresh | no title AND no url | no `CurrentPlaylist` block |
| 5 | Empty state opens disclosure | mount with no title/url | `+ Add by link` input visible |
| 6 | Non-empty state collapsed | mount with a title | input hidden until toggled |
| 7 | Toggle reveals input | click `+ Add by link` | paste input appears |
| 8 | Channel panel via dropdown | click `▾ Recent` → `Browse a channel` | channel panel opens |
| 9 | Auto-collapse on resolve | paste URL → resolve success | disclosure collapses (`onResolvedTarget` fired) |
| 10 | Pick feeds playlistUrl | pick from `▾ Recent` | `playlistUrl` set → resolve runs (Fetch enables) |

- [ ] **Step 1: Update the Header tests (RED)**

Replace the contents of `tests/components/Header-picker.test.tsx` with:

```tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import Header from '../../components/Header';

function mockFetch(overrides: Record<string, unknown> = {}) {
  global.fetch = jest.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/api/playlists/recent')) return { ok: true, json: async () => ({ playlists: [] }) } as Response;
    if (url.includes('/api/resolve-folder')) return { ok: true, json: async () => ({ root: '/home/x/data', outputFolder: '/home/x/data/a/raw' }) } as Response;
    return { ok: true, json: async () => ({}) } as Response;
  }) as unknown as typeof fetch;
  return overrides;
}
beforeEach(() => { mockFetch(); });

it('renders the current playlist title prominently (no ▶ caption)', () => {
  render(<Header defaultBaseOutputFolder="/home/x/data" defaultOutputFolder="/home/x/data/a/raw"
    currentPlaylistTitle="Building with Claude" onIngest={() => {}} />);
  expect(screen.getByText('Building with Claude')).toBeInTheDocument();
  expect(screen.queryByText(/▶/)).toBeNull();
});

it('renders a clickable muted URL for the current playlist', () => {
  render(<Header defaultBaseOutputFolder="/home/x/data" defaultOutputFolder="/home/x/data/a/raw"
    currentPlaylistTitle="건강" currentPlaylistUrl="https://youtube.com/playlist?list=PL837" onIngest={() => {}} />);
  const link = screen.getByRole('link', { name: /playlist\?list=PL837/ });
  expect(link).toHaveAttribute('href', 'https://youtube.com/playlist?list=PL837');
  expect(link).toHaveAttribute('target', '_blank');
});

it('empty state starts with the add-by-link input expanded', () => {
  render(<Header defaultBaseOutputFolder="/home/x/data" defaultOutputFolder="/home/x/data/a/raw" onIngest={() => {}} />);
  expect(screen.getByPlaceholderText(/Paste a playlist URL/)).toBeInTheDocument();
});

it('non-empty state hides the input until the toggle is clicked', () => {
  render(<Header defaultBaseOutputFolder="/home/x/data" defaultOutputFolder="/home/x/data/a/raw"
    currentPlaylistTitle="건강" onIngest={() => {}} />);
  expect(screen.queryByPlaceholderText(/Paste a playlist URL/)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /Add by link/ }));
  expect(screen.getByPlaceholderText(/Paste a playlist URL/)).toBeInTheDocument();
});

it('opens the channel panel from the ▾ Recent dropdown', async () => {
  render(<Header defaultBaseOutputFolder="/home/x/data" defaultOutputFolder="/home/x/data/a/raw"
    currentPlaylistTitle="건강" onIngest={() => {}} />);
  fireEvent.click(screen.getByRole('button', { name: /Recent/ }));
  fireEvent.click(await screen.findByText(/Browse a channel/i));
  expect(await screen.findByText(/Browse channel playlists/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest Header-picker -v`
Expected: FAIL — old Header still renders `▶` caption + always-visible input, and `PlaylistPicker` is called with removed props.

- [ ] **Step 3: Edit `components/Header.tsx` — imports**

Add to the imports block (after line 5):

```tsx
import AddByLink from './AddByLink';
import CurrentPlaylist from './CurrentPlaylist';
import { playlistDisplayTitle } from '../lib/playlists/display-title';
```

- [ ] **Step 4: Add disclosure state**

After line 48 (`const [isMac, setIsMac] = useState(false);`), add:

```tsx
  const [addByLinkOpen, setAddByLinkOpen] = useState(false);
  // opens the disclosure exactly once when we settle into the empty (no-playlist) state
  const emptyInitRef = useRef(false);
```

- [ ] **Step 5: Add the empty-state open effect**

After the auto-fill effect that ends at line 80 (`}, [currentPlaylistUrl]);`), add:

```tsx
  const hasCurrentPlaylist = !!currentPlaylistTitle || !!currentPlaylistUrl;
  // Empty state (no playlist yet) → start with the add-by-link field expanded, once.
  useEffect(() => {
    if (!hasCurrentPlaylist && !emptyInitRef.current) {
      emptyInitRef.current = true;
      setAddByLinkOpen(true);
    }
  }, [hasCurrentPlaylist]);
```

- [ ] **Step 6: Auto-collapse on a successful resolve**

In the resolve effect, replace line 116:

```tsx
        if (data.outputFolder) onResolvedTarget?.(data.outputFolder);
```

with:

```tsx
        if (data.outputFolder) {
          onResolvedTarget?.(data.outputFolder);
          setAddByLinkOpen(false); // a successful switch collapses the add-by-link disclosure
        }
```

- [ ] **Step 7: Compute the display title**

After line 209 (`const canAct = isFresh && !disabled;`), add:

```tsx
  const displayTitle = playlistDisplayTitle(currentPlaylistTitle, target ?? undefined);
```

- [ ] **Step 8: Replace the caption line**

Replace line 262:

```tsx
        {currentPlaylistTitle && <p className="text-xs text-zinc-400 pl-1">▶ {currentPlaylistTitle}</p>}
```

with:

```tsx
        {hasCurrentPlaylist && <CurrentPlaylist title={displayTitle} url={currentPlaylistUrl} />}
```

- [ ] **Step 9: Replace Row 2 (picker + input + Fetch)**

Replace the Row 2 block (lines 264–281) with:

```tsx
        {/* Row 2: Recent picker + Add-by-link + Fetch & Summarize */}
        <div className="flex gap-2 items-center">
          <PlaylistPicker
            root={trimRoot}
            onPick={applyPickedUrl}
            onBrowseChannel={() => setChannelPanelOpen(true)}
            disabled={disabled}
          />
          <AddByLink
            value={playlistUrl}
            onChange={handleUrlChange}
            open={addByLinkOpen}
            onOpenChange={setAddByLinkOpen}
            disabled={disabled}
            currentUrl={currentPlaylistUrl}
          />
          <button
            type="submit"
            disabled={!canAct}
            className="rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-colors whitespace-nowrap"
          >
            Fetch &amp; Summarize
          </button>
        </div>
```

- [ ] **Step 10: Run the Header tests**

Run: `npx jest Header-picker -v`
Expected: PASS (5 tests).

- [ ] **Step 11: Type-check + full suite**

```bash
npx tsc --noEmit ; echo "tsc exit: $?"   # must be 0
npx jest ; echo "jest exit: $?"          # full suite green, no regressions
```
Expected: tsc exit 0; all jest suites pass.

- [ ] **Step 12: Commit**

```bash
git add components/Header.tsx tests/components/Header-picker.test.tsx
git commit -m "feat: title-primary Header — CurrentPlaylist block + AddByLink disclosure"
```

---

### Task 6: E2E — pick via `▾`, add-by-link collapse, channel browse

**Files:**
- Modify: `tests/e2e/playlist-picker.spec.ts`

**Interfaces:**
- Consumes: the running app on `/` (Playwright `reuseExistingServer`). Routes stubbed: `/api/settings`, `/api/videos`, `/api/playlists/recent`, `/api/playlists/channel`, `/api/resolve-folder`, `/api/ingest`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Pick a recent | click `▾ Recent` → row | Fetch enables → ingest POST carries the picked `playlistUrl` |
| 2 | Add-by-link collapses on resolve | open `+ Add by link` → fill URL | disclosure auto-collapses (input hidden) |
| 3 | Channel browse via dropdown | `▾ Recent` → `Browse a channel` → Go → pick | picked URL lands in `playlistUrl` (visible when disclosure reopened) |

- [ ] **Step 1: Rewrite the spec file**

```ts
// tests/e2e/playlist-picker.spec.ts
import { test, expect } from '@playwright/test';

const PLA = 'https://youtube.com/playlist?list=PLa';

test('pick a recent playlist enables Fetch and ingests the picked URL', async ({ page }) => {
  await page.route('**/api/settings**', (r) => r.fulfill({ json: { outputFolder: '/home/x/data/a/raw', baseOutputFolder: '/home/x/data' } }));
  await page.route('**/api/videos**', (r) => r.fulfill({ json: { videos: [], playlistUrl: '', playlistTitle: '' } }));
  await page.route('**/api/playlists/recent**', (r) => r.fulfill({ json: { playlists: [
    { id: 'PLa', title: 'Building with Claude', url: PLA, source: 'recent', meta: { videoCount: 114 } },
    { id: 'PLb', title: 'No Title Playlist', url: 'https://youtube.com/playlist?list=PLb', source: 'recent', meta: {} },
  ] } }));
  await page.route('**/api/resolve-folder**', (r) => r.fulfill({ json: { root: '/home/x/data', outputFolder: '/home/x/data/a/raw' } }));
  let ingestBody: Record<string, unknown> | null = null;
  await page.route('**/api/ingest', async (r) => { ingestBody = r.request().postDataJSON(); await r.fulfill({ json: { jobId: 'j1' } }); });

  await page.goto('/');
  await expect(page.getByPlaceholder(/Root output folder/)).toHaveValue('/home/x/data', { timeout: 5000 });
  await page.getByRole('button', { name: /Recent/ }).click();
  await expect(page.getByText('Building with Claude')).toBeVisible({ timeout: 5000 });
  await page.getByText('Building with Claude').click();

  const fetchBtn = page.getByRole('button', { name: /Fetch & Summarize/ });
  await expect(fetchBtn).toBeEnabled({ timeout: 3000 });
  await fetchBtn.click();
  await expect.poll(() => ingestBody?.playlistUrl, { timeout: 5000 }).toBe(PLA);
});

test('add-by-link auto-collapses after a URL resolves', async ({ page }) => {
  await page.route('**/api/settings**', (r) => r.fulfill({ json: { outputFolder: '/home/x/data/a/raw', baseOutputFolder: '/home/x/data' } }));
  await page.route('**/api/videos**', (r) => r.fulfill({ json: { videos: [], playlistUrl: '', playlistTitle: '' } }));
  await page.route('**/api/playlists/recent**', (r) => r.fulfill({ json: { playlists: [] } }));
  await page.route('**/api/resolve-folder**', (r) => r.fulfill({ json: { root: '/home/x/data', outputFolder: '/home/x/data/a/raw' } }));

  await page.goto('/');
  await expect(page.getByPlaceholder(/Root output folder/)).toHaveValue('/home/x/data', { timeout: 5000 });
  // Empty state → disclosure already open. Fill the paste field.
  const input = page.getByPlaceholder(/Paste a playlist URL/);
  await expect(input).toBeVisible({ timeout: 5000 });
  await input.fill(PLA);
  // Successful resolve → onResolvedTarget → disclosure collapses.
  await expect(input).toBeHidden({ timeout: 5000 });
});

test('browse a channel and pick a playlist sets the URL', async ({ page }) => {
  await page.route('**/api/settings**', (r) => r.fulfill({ json: { outputFolder: '/home/x/data/a/raw', baseOutputFolder: '/home/x/data' } }));
  await page.route('**/api/videos**', (r) => r.fulfill({ json: { videos: [], playlistUrl: '', playlistTitle: '' } }));
  await page.route('**/api/playlists/recent**', (r) => r.fulfill({ json: { playlists: [] } }));
  await page.route('**/api/playlists/channel**', (r) => r.fulfill({ json: { channelTitle: 'Anthropic', playlists: [
    { id: 'PLc', title: 'Research Talks', url: 'https://youtube.com/playlist?list=PLc', source: 'channel', meta: { videoCount: 31 } },
  ] } }));
  // Fail resolve so the disclosure does NOT auto-collapse — we reopen it to read the value.
  await page.route('**/api/resolve-folder**', (r) => r.fulfill({ status: 400, json: {} }));

  await page.goto('/');
  await expect(page.getByPlaceholder(/Root output folder/)).toHaveValue('/home/x/data', { timeout: 5000 });
  await page.getByRole('button', { name: /Recent/ }).click();
  await page.getByText(/Browse a channel/i).click();
  await page.getByPlaceholder(/@channel/).fill('@Anthropic');
  await page.getByText('Go').click();
  await page.getByText('Research Talks').click();
  // Reopen the disclosure and confirm the picked URL populated playlistUrl.
  await page.getByRole('button', { name: /Add by link/ }).click();
  await expect(page.getByPlaceholder(/Paste a playlist URL/)).toHaveValue('https://youtube.com/playlist?list=PLc');
});
```

- [ ] **Step 2: Run the E2E spec**

Run: `npx playwright test playlist-picker`
Expected: 3 tests pass. (If the dev server isn't running, Playwright starts it per `playwright.config`.)

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/playlist-picker.spec.ts
git commit -m "test(e2e): title-primary picker — ▾ Recent pick, add-by-link collapse, channel browse"
```

---

## Verification (Phase 4)

Enumerate as a `TaskCreate` list before clicking:
1. Current playlist shows prominent title + muted URL; clicking the URL opens YouTube in a new tab.
2. Title fallback: view a playlist with no persisted title → shows folder slug (not `list=` id).
3. Empty state (fresh root, no playlist) → `+ Add by link` starts expanded.
4. `+ Add by link` toggle reveals/hides the paste field; Escape collapses; blur on empty collapses.
5. Paste a valid URL → resolves → disclosure auto-collapses; Fetch enables.
6. `▾ Recent` lists recent playlists two-line (title + URL); picking one switches the view.
7. `▾ Recent → Browse a channel` opens the channel panel; picking a playlist populates the URL.

Screenshots → `.screenshots/`, deleted after verification.

## Self-Review

- **Spec coverage:** title-primary display (Task 4/5), muted clickable URL (Task 4), `+ Add by link` disclosure with Escape/blur/auto-collapse (Task 3/5), empty-state expanded (Task 5), title fallback (Task 1/5), two-line recent-picker rows (Task 2), two-line channel-panel rows (Task 2b) — all spec sections mapped, no gaps.
- **Placeholder scan:** none — every step has concrete code/commands.
- **Type consistency:** `playlistDisplayTitle(title?, folderTarget?)` used identically in Task 1 and Task 5; `PlaylistPicker`/`AddByLink`/`CurrentPlaylist` prop shapes match between their defining task and Task 5's usage; the two-line row markup is identical between Task 2 and Task 2b.
