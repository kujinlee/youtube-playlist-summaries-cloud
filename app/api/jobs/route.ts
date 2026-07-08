import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { extractPlaylistId } from '@/lib/youtube';
import { enqueuePlaylist, PlaylistTooLargeError, AllEnqueueFailedError, PlaylistFetchError } from '@/lib/job-queue/producer';
import { rollup } from '@/lib/job-queue/poll-client';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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

  try {
    const bundle = getStorageBundle({ supabaseClient: supabase });
    const principal = getPrincipalFromSession({ userId: user.id }, indexKey);
    const result = await enqueuePlaylist(bundle, principal, playlistUrl);
    return NextResponse.json(result, { status: 200 });
  } catch (e) {
    if (e instanceof PlaylistTooLargeError) return NextResponse.json({ error: 'playlist too large', limit: e.limit, found: e.found }, { status: 422 });
    if (e instanceof AllEnqueueFailedError) return NextResponse.json({ error: 'enqueue failed', playlistId: e.playlistId }, { status: 503 });
    if (e instanceof PlaylistFetchError) return NextResponse.json({ error: 'playlist fetch failed' }, { status: 502 });
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
    return NextResponse.json({ jobs, rollup: rollup(jobs) }, { status: 200 });
  } catch {
    return NextResponse.json({ error: 'internal error' }, { status: 500 });
  }
}
