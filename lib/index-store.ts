import fs from 'fs';
import path from 'path';
import type { PlaylistIndex, Video } from '../types';

const INDEX_FILE = 'playlist-index.json';

function indexPath(outputFolder: string): string {
  return path.join(outputFolder, INDEX_FILE);
}

export function readIndex(outputFolder: string): PlaylistIndex {
  const filePath = indexPath(outputFolder);
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(raw) as PlaylistIndex;
  } catch (err: unknown) {
    if ((err as NodeJS.ErrnoException).code === 'ENOENT') {
      return { playlistUrl: '', outputFolder, videos: [] };
    }
    throw err;
  }
}

export function writeIndex(outputFolder: string, index: PlaylistIndex): void {
  const filePath = indexPath(outputFolder);
  const tmpPath = filePath + '.tmp';
  fs.writeFileSync(tmpPath, JSON.stringify(index, null, 2), 'utf-8');
  fs.renameSync(tmpPath, filePath);
}

export function upsertVideo(outputFolder: string, video: Video): void {
  const index = readIndex(outputFolder);
  const i = index.videos.findIndex((v) => v.id === video.id);
  if (i === -1) {
    index.videos.push(video);
  } else {
    index.videos[i] = video;
  }
  writeIndex(outputFolder, index);
}

export function updateVideoFields(outputFolder: string, id: string, fields: Partial<Video>): void {
  const index = readIndex(outputFolder);
  const i = index.videos.findIndex((v) => v.id === id);
  if (i === -1) return;
  index.videos[i] = { ...index.videos[i], ...fields };
  writeIndex(outputFolder, index);
}
