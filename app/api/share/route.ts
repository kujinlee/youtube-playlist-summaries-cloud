import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { generateShareToken } from '@/lib/share/token';
import { resolveExpiry } from '@/lib/share/ttl';

const json = (b: unknown, s: number) => new Response(JSON.stringify(b), { status: s });

export async function POST(request: Request) {
  const body = await request.json().catch(() => null) as
    | { playlistId?: string; videoId?: string; ttlDays?: number | 'never' } | null;
  if (!body?.playlistId || !body?.videoId) return json({ error: 'bad request' }, 400);

  const expiry = resolveExpiry(body.ttlDays);
  if (!expiry.ok) return json({ error: 'invalid ttlDays' }, 400);

  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  const { token, tokenHash } = generateShareToken();
  const { data: expiresAt, error } = await supabase.rpc('create_share_token', {
    p_playlist_id: body.playlistId, p_video_id: body.videoId,
    p_expiry: expiry.expiresAt ? expiry.expiresAt.toISOString() : null,
    p_token_hash: tokenHash,
  });
  if (error) return json({ error: 'not found' }, 404); // coarse — unowned/unpromoted/bounds
  return json({ token, url: `/s/${token}`, expiresAt }, 201);
}
