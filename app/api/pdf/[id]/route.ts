import fs from 'fs';
import path from 'path';
import { assertOutputFolder, assertVideoId, readIndex } from '../../../../lib/index-store';

type Params = { params: Promise<{ id: string }> };

export async function GET(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const { searchParams } = new URL(request.url);
  const outputFolder = searchParams.get('outputFolder');

  if (!outputFolder) {
    return new Response(JSON.stringify({ error: 'outputFolder is required' }), { status: 400 });
  }

  try {
    assertOutputFolder(outputFolder);
    assertVideoId(videoId);
  } catch {
    return new Response(JSON.stringify({ error: 'invalid request' }), { status: 400 });
  }

  let pdfFile: string | null | undefined;
  try {
    const index = readIndex(outputFolder);
    const video = index.videos.find((v) => v.id === videoId);
    if (!video) {
      return new Response(JSON.stringify({ error: 'video not found' }), { status: 404 });
    }
    const type = searchParams.get('type') ?? 'summary';
    pdfFile = type === 'deep-dive' ? video.deepDivePdf : video.summaryPdf;
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e.statusCode === 400) {
      return new Response(JSON.stringify({ error: e.message }), { status: 400 });
    }
    throw err;
  }

  if (!pdfFile) {
    return new Response(JSON.stringify({ error: 'pdf not available' }), { status: 404 });
  }

  const pdfPath = path.join(outputFolder, pdfFile);
  try {
    const buffer = fs.readFileSync(pdfPath);
    return new Response(buffer, { headers: { 'Content-Type': 'application/pdf' } });
  } catch {
    return new Response(JSON.stringify({ error: 'file not found' }), { status: 404 });
  }
}
