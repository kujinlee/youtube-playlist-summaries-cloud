import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
const json = (b: unknown, s: number) => new Response(JSON.stringify(b), { status: s });

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);
  const { data: revoked, error } = await supabase.rpc('revoke_share_token', { p_id: id });
  if (error) return json({ error: 'internal error' }, 500);
  return json({ revoked }, 200);
}
