import path from 'path';
import fs from 'fs';
import { assertOutputFolder, readIndex, updateVideoFields } from '../../../../lib/index-store';
import { extractQuickView } from '../../../../lib/gemini';
import { insertQuickViewCallout } from '../../../../lib/pipeline';
import { generatePdf } from '../../../../lib/pdf';
import type { ProgressEvent } from '../../../../types';

// Allow long-running backfills (182 videos × ~10s = ~30 min).
// Without this Next.js applies a short default timeout in production.
export const maxDuration = 1800; // 30 minutes

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const outputFolder = searchParams.get('outputFolder');

  if (!outputFolder) {
    return new Response(JSON.stringify({ error: 'outputFolder is required' }), { status: 400 });
  }

  try {
    assertOutputFolder(outputFolder);
  } catch {
    return new Response(JSON.stringify({ error: 'invalid outputFolder' }), { status: 400 });
  }

  const index = readIndex(outputFolder);
  const eligible = index.videos.filter(
    (v): v is typeof v & { summaryMd: string } => !!v.summaryMd && !v.tldr,
  );
  const total = eligible.length;

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      function emit(event: ProgressEvent) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
      }
      // SSE comment keeps the connection alive through long Gemini calls.
      // Proxies and browsers drop idle SSE connections after ~30–60s.
      function heartbeat() {
        controller.enqueue(encoder.encode(': keep-alive\n\n'));
      }

      emit({ type: 'start', total });

      let succeeded = 0;
      let failed = 0;

      for (let i = 0; i < eligible.length; i++) {
        const video = eligible[i]!;
        const current = i + 1;

        // Send a heartbeat before each video so the connection stays alive
        // even if the Gemini call takes close to the 60s timeout.
        heartbeat();

        try {
          const mdPath = path.join(outputFolder, video.summaryMd);
          const mdContent = await fs.promises.readFile(mdPath, 'utf-8');

          const { tldr, takeaways } = await extractQuickView(mdContent);
          const updatedContent = insertQuickViewCallout(mdContent, tldr, takeaways, video.tags ?? []);

          await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');

          // Update index before PDF so a PDF failure leaves a consistent state.
          // A retry will skip this video (tldr now present) and won't re-run Gemini.
          updateVideoFields(outputFolder, video.id, { tldr, takeaways });

          succeeded++;
          // Emit step immediately after the core work (Gemini + index) so the
          // progress bar advances without waiting for PDF generation.
          emit({ type: 'step', videoId: video.id, title: video.title, step: 'done', current, total });

          // PDF regeneration is secondary — report its failure separately so it
          // doesn't block progress or roll back the succeeded count.
          if (video.summaryPdf) {
            try {
              const pdfPath = path.join(outputFolder, video.summaryPdf);
              await generatePdf(updatedContent, pdfPath);
            } catch (pdfErr) {
              const log = pdfErr instanceof Error ? pdfErr.message : String(pdfErr);
              emit({ type: 'error', videoId: video.id, title: `${video.title} (PDF only)`, log });
            }
          }
        } catch (err) {
          failed++;
          const log = err instanceof Error ? err.message : String(err);
          emit({ type: 'error', videoId: video.id, title: video.title, log });
        }

        // Rate limiting: 200ms between Gemini calls (skip after last video)
        if (i < eligible.length - 1) {
          await new Promise<void>((resolve) => setTimeout(resolve, 200));
        }
      }

      emit({ type: 'done', total, succeeded, failed });
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',   // disable nginx/proxy buffering so events arrive in real-time
    },
  });
}
