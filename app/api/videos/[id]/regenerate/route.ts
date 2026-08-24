import { handleRegenerate } from '@/lib/corrections/regenerate-handlers';

/** Bounds THE WORK, not THE REQUEST. Derived in spec §5.4 from three phases — a 10 s countTokens
 *  preflight plus two Gemini phases of 3 × 60 s + 1.2 s backoff each = 372.4 s — leaving ~48 s for
 *  the blob read, the blob write and the metadata RPC.
 *
 *  ⚠ NOTHING ON THIS DEPLOYMENT ENFORCES IT. Next's own docs call maxDuration an output annotation,
 *  and this app ships `output: 'standalone'` running `node server.js` under Fly, where no adapter
 *  consumes it. Kept because it is correct-by-portability and free. */
export const maxDuration = 420;

type Params = { params: Promise<{ id: string }> };

/** Thin by design. The local/cloud fork, the backend read and the UUID check all live in lib now —
 *  three open architecture findings that slice A had pushed past their baseline. */
export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  return handleRegenerate(request, videoId);
}
