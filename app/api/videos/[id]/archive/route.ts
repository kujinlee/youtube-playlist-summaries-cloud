import { NextResponse } from 'next/server';
import { assertOutputFolder, assertVideoId } from '../../../../../lib/index-store';
import { archiveVideo, unarchiveVideo } from '../../../../../lib/archive';

type Params = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const body = await request.json().catch(() => null);
  const outputFolder = body?.outputFolder;
  const action = body?.action;

  if (!outputFolder) return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  if (action !== 'archive' && action !== 'unarchive') {
    return NextResponse.json({ error: 'action must be archive or unarchive' }, { status: 400 });
  }

  try {
    assertOutputFolder(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  if (action === 'archive') {
    await archiveVideo(outputFolder, videoId);
  } else {
    await unarchiveVideo(outputFolder, videoId);
  }

  return NextResponse.json({ ok: true });
}
