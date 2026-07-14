import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { logError } from '@/lib/dev-logger';
const json = (b: unknown, s: number) => new Response(JSON.stringify(b), { status: s });

export async function POST(request: Request) {
  const body = await request.json().catch(() => null) as { playlistId?: string; videoId?: string } | null;
  if (!body?.playlistId || !body?.videoId) return json({ error: 'bad request' }, 400);
  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);
  const { data: count, error } = await supabase.rpc('revoke_all_share_tokens', {
    p_playlist_id: body.playlistId, p_video_id: body.videoId,
  });
  if (error) { logError('share:revoke-all', error); return json({ error: 'internal error' }, 500); }
  return json({ count }, 200);
}
