import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { runPhaseA } from '@/lib/serial-migrate-exec';
import { readIndex, writeIndex } from '@/lib/index-store';
import type { Video, PlaylistIndex } from '@/types';

function makeVideo(id: string, processedAt: string, summaryMd: string | null): Video {
  return {
    id,
    title: `Video ${id}`,
    youtubeUrl: `https://www.youtube.com/watch?v=${id}`,
    language: 'en',
    durationSeconds: 300,
    archived: false,
    ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
    overallScore: 3,
    summaryMd,
    summaryPdf: summaryMd ? `pdfs/${summaryMd.replace('.md', '.pdf')}` : null,
    deepDiveMd: null,
    deepDivePdf: null,
    processedAt,
  };
}

describe('runPhaseA', () => {
  let outputFolder: string;

  beforeEach(() => {
    // Must be under homedir — assertOutputFolder enforces this
    outputFolder = path.join(os.homedir(), `.tmp-serial-migrate-exec-${crypto.randomUUID()}`);
    fs.mkdirSync(outputFolder, { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(outputFolder, { recursive: true, force: true });
  });

  it('Phase A assigns serials to all file-bearing videos in one write and is idempotent', () => {
    // Seed index with 2 videos (summaryMd set, no serialNumber), processedAt ordered
    const index: PlaylistIndex = {
      playlistUrl: 'https://www.youtube.com/playlist?list=TEST',
      outputFolder,
      videos: [
        makeVideo('video1', new Date('2025-01-01').toISOString(), 'summary-1.md'),
        makeVideo('video2', new Date('2025-01-02').toISOString(), 'summary-2.md'),
      ],
    };
    writeIndex(outputFolder, index);

    // First run: should assign serials
    const r1 = runPhaseA(outputFolder);
    expect(r1.assigned).toBe(2);
    const after = readIndex(outputFolder).videos.map((v) => v.serialNumber).sort();
    expect(after).toEqual([1, 2]);

    // Second run: idempotent
    const r2 = runPhaseA(outputFolder);
    expect(r2.assigned).toBe(0);
  });
});
