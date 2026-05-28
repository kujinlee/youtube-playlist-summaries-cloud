import { NextResponse } from 'next/server';
import { cancelJob } from '../../../../lib/job-registry';

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const jobId = body?.jobId;

  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  const cancelled = cancelJob(jobId);
  if (!cancelled) {
    return NextResponse.json({ error: 'Job not found' }, { status: 404 });
  }

  return NextResponse.json({ ok: true });
}
