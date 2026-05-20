import crypto from 'crypto';
import { NextResponse } from 'next/server';
import { assertOutputFolder } from '../../../lib/index-store';
import { runIngestion } from '../../../lib/pipeline';
import { createJob, deleteJob } from '../../../lib/job-registry';
import type { ProgressEvent } from '../../../types';

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const playlistUrl = body?.playlistUrl;
  const outputFolder = body?.outputFolder;

  if (!playlistUrl) return NextResponse.json({ error: 'playlistUrl is required' }, { status: 400 });
  if (!outputFolder) return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });

  try {
    assertOutputFolder(outputFolder);
  } catch {
    return NextResponse.json({ error: 'invalid outputFolder' }, { status: 400 });
  }

  const jobId = crypto.randomUUID();
  const emitter = createJob(jobId);
  let finished = false;

  // Start pipeline in background; do not await
  runIngestion(playlistUrl, outputFolder, (event: ProgressEvent) => {
    emitter.emit('progress', event);
    if (event.type === 'done' || event.type === 'error') {
      finished = true;
      deleteJob(jobId);
    }
  }).catch((err) => {
    if (finished) return;
    finished = true;
    emitter.emit('progress', { type: 'error', log: err instanceof Error ? err.message : String(err) });
    deleteJob(jobId);
  });

  return NextResponse.json({ jobId });
}
