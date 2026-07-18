// lib/cloud-sync/manifest.ts
import { promises as fs } from 'fs';
import path from 'path';
import type { VideoBaseline } from './types';

export interface Manifest { version: 1; videos: Record<string, VideoBaseline>; }

export function manifestPath(dataRoot: string, playlistKey: string): string {
  return path.join(dataRoot, playlistKey, '.cloud-sync-manifest.json');
}
function conflictPath(dataRoot: string, playlistKey: string): string {
  return path.join(dataRoot, playlistKey, '.cloud-sync-conflicts.log');
}

export async function readManifest(dataRoot: string, playlistKey: string): Promise<Manifest> {
  try {
    const raw = await fs.readFile(manifestPath(dataRoot, playlistKey), 'utf8');
    const parsed = JSON.parse(raw);
    if (parsed && parsed.version === 1 && parsed.videos) return parsed as Manifest;
  } catch { /* missing or corrupt → degrade (§8) */ }
  return { version: 1, videos: {} };
}

async function atomicWrite(file: string, data: string): Promise<void> {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp-${process.pid}`;
  await fs.writeFile(tmp, data, 'utf8');
  await fs.rename(tmp, file);
}

export async function writeVideoBaseline(
  dataRoot: string, playlistKey: string, videoId: string, baseline: VideoBaseline,
): Promise<void> {
  const m = await readManifest(dataRoot, playlistKey);
  m.videos[videoId] = baseline;
  await atomicWrite(manifestPath(dataRoot, playlistKey), JSON.stringify(m, null, 2));
}

const seenConflicts = new Set<string>();
export interface ConflictEntry {
  video_id: string; class: 'A' | 'B'; field?: string;
  valueL?: unknown; valueR?: unknown; reason: string;
}
export async function appendConflict(dataRoot: string, playlistKey: string, e: ConflictEntry): Promise<void> {
  // Include playlistKey so the same (video_id, class, field, valueL, valueR) in two playlists
  // within one run is not collapsed to a single entry (L3).
  const key = `${playlistKey}|${e.video_id}|${e.class}|${e.field ?? ''}|${JSON.stringify(e.valueL)}|${JSON.stringify(e.valueR)}`;
  if (seenConflicts.has(key)) return;
  seenConflicts.add(key);
  const file = conflictPath(dataRoot, playlistKey);
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.appendFile(file, `${JSON.stringify(e)}\n`, 'utf8');
}
/** Reset the per-run de-dup cache at the start of a sync run. */
export function resetConflictDedup(): void { seenConflicts.clear(); }
