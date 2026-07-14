// app/api/playlists/backfill-titles/route.ts
//
// POST /api/playlists/backfill-titles (Task 4, BUG-6 backfill).
//
// Cloud-only. Fills real YouTube titles for the caller's own playlists that were ingested
// before BUG-6 was fixed (title == list-id, i.e. still null in the store's schema).
//
// review fix (whole-branch, starvation): process ALL of the caller's null-title rows in one
// call, not a fixed-size prefix slice. The naturally-bounded set here is the owner's own
// null-title playlists — the sidebar (Task 5) already bounds *call frequency* to once per
// session per user, which is the real backstop against repeated work. A prefix slice (e.g.
// "first 200") is actively harmful: if those first N rows are permanently unfillable (their
// YouTube playlist was deleted/made private, so fetchPlaylistTitleOrNull keeps returning
// null), the SAME first N rows get re-selected every session forever, and any fillable row
// sitting at position N+1 is never attempted — a permanent starvation bug that breaks the
// "drains over sessions" contract. BACKFILL_SANITY_MAX below is kept only as a defensive
// abuse ceiling (a single owner with a pathological number of null-title rows), not as the
// normal-case bound.
import { cookies } from 'next/headers';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { fetchPlaylistTitleOrNull } from '@/lib/youtube';

const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status });

// Defensive abuse ceiling only — NOT a per-call processing target. Any realistic (or even
// near-pathological, ≤1000) backlog of null-title rows for one owner is processed in full so
// a fillable row is never starved behind unfillable ones (see comment above). Only past this
// ceiling do we cap and log, since something has gone very wrong (e.g. an ingest bug bulk
// creating null-title rows).
const BACKFILL_SANITY_MAX = 1000;

export async function POST() {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  // review fix: 501 (not 404) — a non-supabase backend is a backend/config mistake, not "this
  // resource doesn't exist" — matches the delete route's fix (app/api/playlists/[id]/route.ts).
  if (backend !== 'supabase') return json({ error: 'unsupported' }, 501);

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) return json({ error: 'YOUTUBE_API_KEY is not configured' }, 500);

  const store = getStorageBundle({ supabaseClient: supabase }).metadataStore;
  const playlists = await store.listPlaylists(user.id);
  let untitled = playlists.filter((p) => p.playlistTitle == null);
  if (untitled.length > BACKFILL_SANITY_MAX) {
    console.warn(
      `backfill-titles: owner ${user.id} has ${untitled.length} null-title rows, exceeding ` +
        `the BACKFILL_SANITY_MAX abuse ceiling (${BACKFILL_SANITY_MAX}); processing only the ` +
        `first ${BACKFILL_SANITY_MAX} this call.`,
    );
    untitled = untitled.slice(0, BACKFILL_SANITY_MAX);
  }

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
