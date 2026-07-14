import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { getStorageBundle } from '@/lib/storage/resolve';
import { TERMINAL_STATUSES } from '@/lib/job-queue/poll-client';
import { logError } from '@/lib/dev-logger';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(req: Request) {
  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const hasJob = body?.jobId !== undefined;
  const hasPlaylist = body?.playlistId !== undefined;
  if (hasJob === hasPlaylist) return NextResponse.json({ error: 'provide exactly one of jobId or playlistId' }, { status: 400 });
  const value = hasJob ? body.jobId : body.playlistId;
  if (!UUID_RE.test(value)) return NextResponse.json({ error: 'invalid uuid' }, { status: 400 });

  try {
    const bundle = getStorageBundle({ supabaseClient: supabase });
    const queue = bundle.jobQueue!;
    if (hasJob) {
      const { requested } = await queue.requestCancel(value);
      return NextResponse.json({ requested }, { status: 200 });
    }
    const rows = await queue.listByPlaylist(value);
    let requested = 0;
    for (const r of rows) {
      if (!TERMINAL_STATUSES.includes(r.status)) requested += (await queue.requestCancel(r.jobId)).requested;
    }
    return NextResponse.json({ requested }, { status: 200 });
  } catch (err) {
    logError('jobs:cancel', err);   // never swallow the cancel RPC's real failure
    return NextResponse.json({ error: 'internal error' }, { status: 500 });
  }
}
