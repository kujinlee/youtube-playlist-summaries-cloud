import { getJob } from '../../../../../../lib/job-registry';
import type { ProgressEvent } from '../../../../../../types';

type Params = { params: Promise<{ id: string }> };

export async function GET(request: Request, _ctx: Params) {
  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get('jobId');

  if (!jobId) {
    return new Response(JSON.stringify({ error: 'jobId is required' }), { status: 400 });
  }

  const emitter = getJob(jobId);
  if (!emitter) {
    return new Response(JSON.stringify({ error: 'job not found' }), { status: 404 });
  }

  let onProgress: ((event: ProgressEvent) => void) | null = null;
  const stream = new ReadableStream({
    start(controller) {
      onProgress = (event: ProgressEvent) => {
        controller.enqueue(`data: ${JSON.stringify(event)}\n\n`);
        if (event.type === 'done' || event.type === 'error') {
          emitter.removeListener('progress', onProgress!);
          controller.close();
        }
      };
      emitter.on('progress', onProgress);
    },
    cancel() {
      if (onProgress) emitter.removeListener('progress', onProgress);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  });
}
