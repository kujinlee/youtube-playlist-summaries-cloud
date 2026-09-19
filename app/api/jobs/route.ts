import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { createServiceClient } from '@/lib/supabase/service';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { extractPlaylistId } from '@/lib/youtube';
import { enqueuePlaylist, PlaylistTooLargeError, AllEnqueueFailedError, PlaylistFetchError } from '@/lib/job-queue/producer';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
import { workerWakeFromEnv } from '@/lib/job-queue/worker-wake';
import { rollup } from '@/lib/job-queue/poll-client';
import { parseClientIp } from '@/lib/http/client-ip';
import { logError } from '@/lib/dev-logger';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// No verdict-specific retry value is available from `enqueue_preflight` (it returns only
// booleans) — 60s is a fixed, conservative default until the RPC surfaces a real retry hint.
const RETRY_AFTER_SECONDS = 60;

export async function POST(req: Request) {
  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  let playlistUrl: string;
  let indexKey: string;
  try {
    const body = await req.json();
    playlistUrl = body?.playlistUrl;
    if (typeof playlistUrl !== 'string' || !playlistUrl) return NextResponse.json({ error: 'missing playlistUrl' }, { status: 400 });
    indexKey = extractPlaylistId(playlistUrl); // throws → 400
  } catch { return NextResponse.json({ error: 'invalid playlist url' }, { status: 400 }); }

  if (!process.env.YOUTUBE_API_KEY) return NextResponse.json({ error: 'internal error' }, { status: 500 });

  const ownerId = user.id;
  const enqueueIp = parseClientIp(req);
  const enqueuer = new SupabaseEnqueuer(createServiceClient());

  try {
    const verdict = await enqueuer.preflight(enqueueIp, ownerId);
    if (verdict.velocityExceeded) {
      return NextResponse.json({ error: 'rate limited' }, {
        status: 429,
        headers: { 'Retry-After': String(RETRY_AFTER_SECONDS) },
      });
    }
    if (verdict.atCapacity) return NextResponse.json({ error: 'at capacity' }, { status: 503 });
    if (!verdict.admitted) return NextResponse.json({ error: 'forbidden' }, { status: 403 });

    const bundle = getStorageBundle({ supabaseClient: supabase });
    const principal = getPrincipalFromSession({ userId: ownerId }, indexKey);
    const result = await enqueuePlaylist(bundle, enqueuer, principal, playlistUrl, { ownerId, enqueueIp });
    return NextResponse.json({ ...result, challengeRequired: verdict.challengeRequired }, { status: 200 });
  } catch (e) {
    if (e instanceof PlaylistTooLargeError) return NextResponse.json({ error: 'playlist too large', limit: e.limit, found: e.found }, { status: 422 });
    if (e instanceof AllEnqueueFailedError) return NextResponse.json({ error: 'enqueue failed', playlistId: e.playlistId }, { status: 503 });
    if (e instanceof PlaylistFetchError) return NextResponse.json({ error: 'playlist fetch failed' }, { status: 502 });
    logError('jobs:enqueue', e);   // unexpected (not the 422/503/502 above) — surface before the generic 500
    return NextResponse.json({ error: 'internal error' }, { status: 500 });   // resolve/misconfig/unexpected
  }
}

export async function GET(req: Request) {
  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const playlistId = new URL(req.url).searchParams.get('playlistId');
  if (!playlistId) return NextResponse.json({ error: 'missing playlistId' }, { status: 400 });
  if (!UUID_RE.test(playlistId)) return NextResponse.json({ error: 'invalid playlistId' }, { status: 400 });

  try {
    const bundle = getStorageBundle({ supabaseClient: supabase });
    const jobs = await bundle.jobQueue!.listByPlaylist(playlistId);

    // ⭐ THE READ PATH IS ALSO A WAKE PATH, and it is what closes the one hole the enqueue-time poke
    // cannot (backlog #142; review r1 F4). A job can commit in the window after the worker has
    // decided its queue is drained and before the process has exited: the poke lands on a Machine
    // that is still running, so Fly Proxy starts nothing, and then the worker exits. Nothing else
    // recovers it — there is no cron and no second poker — so the job would wait for the next
    // unrelated enqueue by anyone, while the user watches a `queued` spinner with nothing red.
    //
    // Poking here fixes that generally rather than narrowly: it also covers a crashed worker, and
    // any future code path that creates work without going through `enqueue()`.
    //
    // ⚠ NOT AWAITED, so this cannot slow the poll down — a status poll must stay fast, and we need
    // no part of the reply. Suppression inside the shared wake (see `workerWakeFromEnv`) is what
    // stops a 2s poll loop from emitting a poke every 2s; it sends at most one per window.
    if (jobs.some((j) => j.status === 'queued')) void workerWakeFromEnv()();

    return NextResponse.json({ jobs, rollup: rollup(jobs) }, { status: 200 });
  } catch (err) {
    logError(`jobs:poll:${playlistId}`, err);   // never swallow: surface the real cause to console + dev-errors.log
    return NextResponse.json({ error: 'internal error' }, { status: 500 });
  }
}
