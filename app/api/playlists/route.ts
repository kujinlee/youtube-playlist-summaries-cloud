import { cookies } from 'next/headers';
import { assertOutputFolder } from '@/lib/index-store';
import { listRecentPlaylists } from '@/lib/playlists/recent-provider';
import { getStorageBundle } from '@/lib/storage/resolve';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';

const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status });

export async function GET(request: Request) {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud();
  return serveLocal(request);
}

async function serveCloud(): Promise<Response> {
  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  const playlists = await getStorageBundle({ supabaseClient: supabase }).metadataStore.listPlaylists(user.id);
  return Response.json({ playlists });
}

// LOCAL path: delegate directly to listRecentPlaylists(root) — do NOT go through the store's
// listPlaylists, which is cloud-only (throws on the local metadata store). Pattern mirrors the
// existing app/api/playlists/recent/route.ts.
function serveLocal(request: Request): Response {
  const root = new URL(request.url).searchParams.get('root');
  if (!root) return json({ error: 'root is required' }, 400);
  try {
    assertOutputFolder(root); // within-home + realpath guard
    return Response.json({ playlists: listRecentPlaylists(root) });
  } catch {
    return json({ error: 'invalid root' }, 400);
  }
}
