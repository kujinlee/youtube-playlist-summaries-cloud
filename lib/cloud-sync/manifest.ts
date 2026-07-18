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
  } catch {
    // DELIBERATE, and spec-sanctioned — §8 specifies degrade-on-corrupt for the manifest.
    // L-R5-3 (round 5, ACCEPTED not fixed): this catch also swallows an UNREADABLE manifest
    // (EACCES/EIO) as an absent one, and with no baseline sync-run reads a one-sided video as a new
    // additive create rather than a delete — so a video deleted on one replica can be copied back.
    // That is the SAFE direction (resurrect, never delete) and the manifest is a derived cache that
    // rebuilds itself on the next run; failing closed here would strand every video in the playlist.
    // Reviewers: this is the same `catch → default` shape as B1/H1/H2, but unlike those it is the
    // intended §8 behavior — please do not re-file it.
  }
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
