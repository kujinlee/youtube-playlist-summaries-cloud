import { promises as fs } from 'fs';
import path from 'path';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

export interface LocalPlaylist { playlistKey: string; dataRoot: string; playlistUrl: string; }

export function playlistKeyFromUrl(url: string): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.searchParams.get('list');
  } catch { return null; }
}

/** Scan each data root's subdirectories for a playlist-index.json and derive its key. */
export async function discoverLocalPlaylists(dataRoots: string[]): Promise<LocalPlaylist[]> {
  const byKey = new Map<string, LocalPlaylist>();
  for (const root of dataRoots) {
    let entries: string[] = [];
    try { entries = await fs.readdir(root); } catch { continue; }
    for (const dir of entries) {
      const candidate = path.join(root, dir);
      const dataRoot = await resolveRootShape(candidate); // handles <dir> and <dir>/raw
      if (!dataRoot) continue;
      const idx = await localMetadataStore.readIndex(localPrincipal(dataRoot));
      const key = playlistKeyFromUrl(idx.playlistUrl);
      if (!key) continue;
      if (!byKey.has(key)) byKey.set(key, { playlistKey: key, dataRoot, playlistUrl: idx.playlistUrl });
    }
  }
  return [...byKey.values()];
}

async function resolveRootShape(candidate: string): Promise<string | null> {
  for (const p of [candidate, path.join(candidate, 'raw')]) {
    try { await fs.access(path.join(p, 'playlist-index.json')); return p; } catch { /* try next */ }
  }
  return null;
}

export function unionPlaylistKeys(local: LocalPlaylist[], cloudKeys: string[]): string[] {
  return [...new Set([...local.map((l) => l.playlistKey), ...cloudKeys])];
}
