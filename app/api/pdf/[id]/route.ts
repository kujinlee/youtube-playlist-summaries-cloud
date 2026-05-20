import fs from 'fs';
import path from 'path';
import { assertOutputFolder, assertVideoId } from '../../../../lib/index-store';

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

  const pdfPath = path.join(outputFolder, `${videoId}.pdf`);

  try {
    const buffer = fs.readFileSync(pdfPath);
    return new Response(buffer, {
      headers: { 'Content-Type': 'application/pdf' },
    });
  } catch {
    return new Response(JSON.stringify({ error: 'file not found' }), { status: 404 });
  }
}
