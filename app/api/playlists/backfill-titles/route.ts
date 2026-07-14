// app/api/playlists/backfill-titles/route.ts
//
// POST /api/playlists/backfill-titles (Task 4, BUG-6 backfill).
//
// Cloud-only. Fills real YouTube titles for the caller's own playlists that were ingested
// before BUG-6 was fixed (title == list-id, i.e. still null in the store's schema). Bounded
// to BACKFILL_MAX_PER_CALL rows per call as a runaway backstop — the sidebar (Task 5) fires
// this once per session per user, so a large backlog drains over a few sessions rather than
// blocking one request.
import { cookies } from 'next/headers';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { fetchPlaylistTitleOrNull } from '@/lib/youtube';

const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status });

// Runaway backstop (behavior 6): at most this many null-title rows processed per call.
const BACKFILL_MAX_PER_CALL = 200;

export async function POST() {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend !== 'supabase') return json({ error: 'unsupported' }, 404);

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) return json({ error: 'YOUTUBE_API_KEY is not configured' }, 500);

  const store = getStorageBundle({ supabaseClient: supabase }).metadataStore;
  const playlists = await store.listPlaylists(user.id);
  const untitled = playlists.filter((p) => p.playlistTitle == null).slice(0, BACKFILL_MAX_PER_CALL);

  let updated = 0;
  let attempted = 0;
  for (const p of untitled) {
    const principal = getPrincipalFromSession({ userId: user.id }, p.playlistKey);
    try {
      const title = await fetchPlaylistTitleOrNull(p.playlistKey, apiKey);
      if (title) {
        const { updated: didUpdate } = await store.setPlaylistTitleIfNull(principal, title);
        if (didUpdate) updated++;
      }
    } catch {
      // Per-row isolation (behavior 5): one row's fetch/store failure must not abort the batch.
    }
    attempted++;
  }

  return json({ updated, attempted }, 200);
}
