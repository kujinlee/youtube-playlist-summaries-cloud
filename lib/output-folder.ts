import fs from 'fs';
import path from 'path';
import { slugify } from './slugify';
import { fetchPlaylistTitle } from './youtube';

/** Thrown when the playlist URL is missing/invalid (maps to HTTP 400). */
export class InvalidPlaylistUrlError extends Error {}

/** Extract the `list=` playlist id from a YouTube playlist URL, or null. */
function extractPlaylistId(url: string): string | null {
  try {
    return new URL(url).searchParams.get('list');
  } catch {
    return null;
  }
}

/**
 * Find an existing playlist folder under `root` whose stored index.playlistUrl
 * has the same `list=` id. Returns the directory that holds the index (the write
 * target): `<root>/<dir>/raw` for the nested layout, `<root>/<dir>` for flat.
 * Matching by id (not folder name) is what lets regeneration find a playlist
 * regardless of how its folder was named.
 */
function findExistingPlaylistFolder(root: string, playlistId: string): string | null {
  if (!fs.existsSync(root)) return null;
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(root, { withFileTypes: true });
  } catch {
    return null;
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const dir = path.join(root, entry.name);
    for (const candidate of [path.join(dir, 'raw'), dir]) {
      const idxPath = path.join(candidate, 'playlist-index.json');
      if (!fs.existsSync(idxPath)) continue;
      try {
        const parsed = JSON.parse(fs.readFileSync(idxPath, 'utf-8')) as { playlistUrl?: string };
        const storedId = extractPlaylistId(parsed.playlistUrl ?? '');
        if (storedId && storedId === playlistId) return candidate;
      } catch {
        // unreadable / corrupt index — skip this candidate
      }
    }
  }
  return null;
}

/**
 * Resolve the output folder for a playlist URL, anchored at `root` (the data root).
 * Existing playlists resolve to their on-disk folder (by playlist id); a brand-new
 * playlist resolves to `<root>/<slugify(title)>/raw` (slugging the id when no API key).
 */
export async function resolveOutputFolder(
  playlistUrl: string,
  root: string,
  apiKey: string | undefined,
): Promise<string> {
  const playlistId = extractPlaylistId(playlistUrl);
  if (!playlistId) {
    throw new InvalidPlaylistUrlError('playlist URL has no ?list= id');
  }
  const existing = findExistingPlaylistFolder(root, playlistId);
  if (existing) return existing;
  // New playlist → name the folder from the title. A failed title fetch
  // (network/auth/quota) degrades gracefully to an id-based slug rather than
  // failing the whole resolve.
  let title = playlistId;
  if (apiKey) {
    try {
      title = await fetchPlaylistTitle(playlistId, apiKey);
    } catch {
      // keep the id fallback
    }
  }
  const slug = slugify(title) || slugify(playlistId) || playlistId;
  return path.join(root, slug, 'raw');
}

/**
 * True when `dir` is a playlist folder — it directly holds a playlist-index.json
 * (flat layout) or a raw/playlist-index.json (nested layout).
 */
function isPlaylistFolder(dir: string): boolean {
  return (
    fs.existsSync(path.join(dir, 'playlist-index.json')) ||
    fs.existsSync(path.join(dir, 'raw', 'playlist-index.json'))
  );
}

/**
 * Reduce a folder path to the data ROOT (the parent that holds playlist folders).
 *
 * The header's folder field is meant to hold the root; if the user points it at a
 * playlist sub-folder (`<root>/<slug>` or `<root>/<slug>/raw`) we snap it back up:
 *   1. drop a trailing `/raw`
 *   2. if the result is itself a playlist folder, go up one level
 *
 * A path that is already the root (no own index, no raw/ index) is returned unchanged,
 * as is any unrelated folder.
 */
export function normalizeToRoot(folderPath: string): string {
  let p = folderPath.replace(/\/+$/, '') || '/';
  // Only strip a trailing `/raw` when it's actually a playlist's raw dir (holds an
  // index) — never when `raw` happens to be the data root itself.
  if (path.basename(p) === 'raw' && fs.existsSync(path.join(p, 'playlist-index.json'))) {
    p = path.dirname(p);
  }
  if (isPlaylistFolder(p)) {
    p = path.dirname(p);
  }
  return p || '/';
}
