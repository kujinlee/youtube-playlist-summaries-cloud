# Header Redesign — Design Spec

**Date:** 2026-05-27
**Status:** Approved
**Scope:** `components/Header.tsx`, new `app/api/pick-folder/route.ts`, minor changes to `app/page.tsx`

---

## Problem Statement

The current single-row header has four issues:

1. The Playlist URL input uses `flex-1` and consumes most of the horizontal space, leaving the Output Folder field too narrow (`w-52`, 208 px) to display a full path.
2. The Output Folder field is text-only — there is no way to open a native folder picker; the user must type or paste a path.
3. There is no folder-first workflow. If the user picks an existing output folder, the app has no way to pre-populate the playlist URL from that folder's metadata.
4. The Sync button uses a low-contrast ghost style (`border-zinc-700`, `text-zinc-400`) and is easy to miss.

---

## Layout

### Structure

Two rows inside the existing `<header>` element.

**Row 1 — Output location**

```
[ Full-width folder path input ] [ 📂 Browse ] [ ↻ Sync (green) ]
```

**Row 2 — Playlist URL**

```
[ Full-width playlist URL input ] [ Fetch & Summarize ]
```

Both inputs use `flex-1` so they expand to fill the available width.
No fixed widths on either input field.

### Sync button style

- Enabled: `bg-green-900 text-green-300 border border-green-700 hover:bg-green-800`
- Disabled: same classes with `opacity-40 cursor-not-allowed`

This replaces the current ghost style (`border-zinc-700 text-zinc-400`).

---

## Interaction Flows

### Flow 1 — Re-ingest existing folder (folder-first)

1. User clicks **📂 Browse** → native macOS Finder dialog opens (via server-side `osascript`).
2. User selects a folder that already contains `playlist-index.json`.
3. The app calls `/api/videos?outputFolder=<path>`; the response includes `playlistUrl`.
4. The Playlist URL field auto-populates with the value from the index (displayed in blue/muted to indicate it was auto-filled, editable).
5. **↻ Sync** is enabled. User clicks it to re-ingest.

### Flow 2 — New playlist, URL first (auto-slug folder)

1. User pastes a YouTube playlist URL into the Playlist URL field.
2. Existing debounced logic calls `/api/playlist-info?url=…` → derives a slug from the playlist title.
3. Folder field auto-fills with `baseOutputFolder / slug` (displayed in blue to indicate auto-fill, editable).
4. User may edit the folder or accept it.
5. User clicks **Fetch & Summarize**.

### Flow 3 — New playlist, custom folder name

1. User types a folder path directly, or clicks **📂 Browse** and picks a folder with no `playlist-index.json`.
2. Playlist URL field remains empty (shows placeholder). ↻ Sync is disabled.
3. User pastes the playlist URL.
4. **Fetch & Summarize** unlocks. User clicks it.

---

## Browse Button — `GET /api/pick-folder`

### Why not `showDirectoryPicker()`

The browser's Web File System Access API (`showDirectoryPicker()`) does not expose the absolute path of the selected directory (sandboxed for security). It returns a `FileSystemDirectoryHandle` with only the folder name.

### Solution: server-side macOS dialog

A new API route opens a native Finder folder picker via AppleScript and returns the real POSIX path.

**Route:** `GET /api/pick-folder`

**Server implementation (safe argument array — no shell injection):**

```ts
import { execFileSync } from 'child_process';
import { NextResponse } from 'next/server';

export async function GET() {
  if (process.platform !== 'darwin') {
    return NextResponse.json({ error: 'Folder picker only supported on macOS' }, { status: 501 });
  }
  try {
    const raw = execFileSync(
      'osascript',
      ['-e', 'POSIX path of (choose folder with prompt "Select output folder:")'],
      { timeout: 60_000 },
    ).toString().trim();
    // osascript appends a trailing slash — normalise
    const folderPath = raw.endsWith('/') ? raw.slice(0, -1) : raw;
    return NextResponse.json({ folderPath });
  } catch {
    // User cancelled the dialog (exit code 1) or osascript unavailable
    return NextResponse.json({ cancelled: true });
  }
}
```

**Client behaviour:**
- Click Browse → `fetch('/api/pick-folder')`.
- If `{ folderPath }`: set folder input + trigger folder-change side-effects (metadata lookup).
- If `{ cancelled: true }` or network error: silently ignore (no state change).
- On non-macOS: Browse button is hidden via client-side check (`navigator.platform.includes('Mac')`) — no network call needed.

---

## Playlist URL Auto-fill from Folder Metadata

When the folder input value changes (via Browse, typing, or settings load), `page.tsx` already calls `fetchVideos(folder, …)`, and the `/api/videos` response already includes `playlistUrl`. `currentPlaylistUrl` is already tracked in page state.

**Change:** pass `currentPlaylistUrl` as a new prop to `<Header>`. Header uses it to auto-fill the URL field under a controlled condition.

**Auto-fill rule:**
- A ref `urlEditedByUser` (default `false`) tracks whether the user has typed in the URL input since the last folder change.
- Resets to `false` on: Browse success, folder `onChange`.
- Sets to `true` on: any URL input `onChange` event.
- A `useEffect` watching `currentPlaylistUrl` sets the URL field *only when* `urlEditedByUser.current === false` and `currentPlaylistUrl` is non-empty.

This ensures: browsing to an existing folder auto-fills the URL; but if the user has already typed a URL, the auto-fill never overwrites their input.

---

## Sync Button Enable Rules

| Condition | Sync state |
|---|---|
| Playlist URL field is non-empty (from metadata or typed) | ✅ Enabled |
| Playlist URL field is empty | ⛔ Disabled |
| Ingest or Sync is currently running | ⛔ Disabled (both buttons) |

`syncEnabled` is computed in `page.tsx` as `!!currentPlaylistUrl`. This is extended to also be `true` when the URL field in Header has a value (even if `currentPlaylistUrl` in page state hasn't caught up yet). Simplest approach: Header computes its own `canSync = playlistUrl.trim() !== '' && !disabled` and uses that for the Sync button, independent of the `syncEnabled` prop.

---

## Component Changes

### `components/Header.tsx`

| Change | Detail |
|---|---|
| Layout | Single flex row → two flex rows inside `<form>` |
| Browse button | New button next to folder input; hidden on non-macOS via `navigator.platform`; calls `GET /api/pick-folder`; sets folder on success; resets `urlEditedByUser` |
| Sync style | Replace ghost style with green enabled / green-dimmed disabled |
| Sync enable logic | `canSync = playlistUrl.trim() !== '' && !disabled` (computed locally; `syncEnabled` prop removed) |
| `onSync` signature | Changed to `(folder: string, playlistUrl: string) => void`; Header passes its own URL state |
| URL auto-fill | `useEffect` on `currentPlaylistUrl` prop; applies only when `!urlEditedByUser.current` |
| `urlEditedByUser` ref | `useRef<boolean>(false)` — manages auto-fill gating |
| New prop | `currentPlaylistUrl?: string` |

### `app/page.tsx`

- Add `currentPlaylistUrl={currentPlaylistUrl}` to the `<Header>` JSX.
- Update `onSync` signature from `(folder: string) => void` to `(folder: string, playlistUrl: string) => void`. Header now passes its own URL state so `handleSync` in page.tsx no longer depends on `currentPlaylistUrl` from page state: `const handleSync = useCallback((folder, url) => handleIngest(url, folder), [handleIngest])`.
- The `syncEnabled` prop on `<Header>` is removed — Header computes `canSync` locally.

### `app/api/pick-folder/route.ts`

- New file. `GET` handler using `execFileSync('osascript', […])`. Returns `{ folderPath }` or `{ cancelled: true }`. 501 on non-macOS.

---

## URL Contracts

| Component | Endpoint | Full URL |
|---|---|---|
| Browse button | `GET /api/pick-folder` | `/api/pick-folder` (no params) |

---

## Overlay / Dismissal

No new overlays or modals. The Finder dialog is native OS — dismissed by the OS, not by the app.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| User cancels Finder dialog | `{ cancelled: true }` → no state change, no error shown |
| `osascript` times out (60 s) | catch block → `{ cancelled: true }` → no state change |
| Non-macOS platform | Browse button hidden via `navigator.platform` check at render — no server call |
| `/api/pick-folder` network error | silently ignored, folder input unchanged |
| Folder has no `playlist-index.json` | URL field stays empty, Sync stays disabled |

---

## Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Two-row layout renders | Component mount | Row 1: folder input + Browse + Sync; Row 2: URL input + Fetch & Summarize |
| 2 | Browse opens folder picker | Click Browse (macOS) | `GET /api/pick-folder` called; on success folder input updates |
| 3 | Browse cancel → no change | User dismisses dialog | Folder input unchanged, no error |
| 4 | Browse hidden on non-macOS | `navigator.platform` not Mac at render | Browse button not rendered |
| 5 | URL auto-fills from metadata | `currentPlaylistUrl` changes, `urlEditedByUser=false` | URL field set to `currentPlaylistUrl` |
| 6 | Auto-fill blocked after manual edit | User types in URL field then folder changes | URL field not overwritten |
| 7 | Auto-fill resets on Browse success | Browse returns new folder | `urlEditedByUser` reset to `false`; next metadata load can auto-fill |
| 8 | Folder auto-slugs from URL | User pastes playlist URL | Existing debounced `/api/playlist-info` flow fills folder with `base/slug` |
| 9 | Sync enabled when URL present | URL field non-empty | Sync button green, clickable |
| 10 | Sync disabled when URL empty | URL field empty | Sync button green-dimmed, `disabled` |
| 11 | Sync disabled during ingest | `disabled=true` prop | Both Sync and Fetch & Summarize disabled |
| 12 | Fetch & Summarize disabled when URL empty | URL field empty | Button disabled |
| 13 | `currentPlaylistUrl` passed to Header | `page.tsx` render | Header receives prop; URL field reflects it on folder change |

---

## Testing

| Layer | What to test |
|---|---|
| **Unit** | `GET /api/pick-folder`: success path (mock execFileSync), cancelled path, non-macOS 501 |
| **Component** | Two-row layout; Browse triggers fetch; URL auto-fills on `currentPlaylistUrl` prop change; auto-fill blocked after manual URL edit; Sync green when enabled; Sync disabled when URL empty; both disabled during ingest |
| **E2E** | Flow 1: mock `/api/pick-folder` + existing folder metadata → Sync; Flow 2: paste URL → auto-slug folder → Fetch & Summarize; Browse cancel → no state change |

---

## Out of Scope

- Windows / Linux folder picker (Browse button hidden on non-macOS; user types path).
- Persisting `baseOutputFolder` as a visible setting field in the header (remains an invisible setting, updated automatically when ingest completes).
- Any changes to the progress bar, filter bar, cancel button, or video list.
