import fs from 'fs';
import path from 'path';
import { assertOutputFolder } from '../index-store';
import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
import { fetchPlaylistTitle } from '../youtube';

function extractId(url: string): string | null {
  try { return new URL(url).searchParams.get('list'); } catch { return null; }
}

// Folders holding an index: <root>/<dir>/raw or <root>/<dir> (flat), excluding archived
function playlistFolders(root: string): string[] {
  let entries: fs.Dirent[];
  try { entries = fs.readdirSync(root, { withFileTypes: true }); } catch { return []; }
  const out: string[] = [];
  for (const e of entries) {
    if (!e.isDirectory() || e.name === 'archived') continue;
    for (const c of [path.join(root, e.name, 'raw'), path.join(root, e.name)]) {
      if (fs.existsSync(path.join(c, 'playlist-index.json'))) { out.push(c); break; }
    }
  }
  return out;
}

export async function backfillPlaylistTitles(root: string, apiKey: string): Promise<{ updated: string[]; skipped: string[]; failed: string[] }> {
  assertOutputFolder(root); // within-home guard at the entry point
  const { metadataStore: store } = getStorageBundle();
  const updated: string[] = [], skipped: string[] = [], failed: string[] = [];
  for (const folder of playlistFolders(root)) {
    const p = getPrincipal(folder); // separate principal per discovered child folder
    let index;
    try { index = await store.readIndex(p); } catch { failed.push(folder); continue; }
    if (index.playlistTitle) { skipped.push(folder); continue; }
    const id = extractId(index.playlistUrl ?? '');
    if (!id) { failed.push(folder); continue; }
    try {
      const playlistTitle = await fetchPlaylistTitle(id, apiKey);
      await store.setPlaylistMeta(p, { playlistUrl: index.playlistUrl ?? '', playlistTitle });
      updated.push(folder);
    }
    catch { failed.push(folder); }
  }
  return { updated, skipped, failed };
}
