// app/api/playlists/[id]/route.ts
//
// DELETE /api/playlists/[id] — full hard-delete of a cloud playlist (Task 9). Cloud-only.
// Orchestrates the pieces built in T6 (cancel RPC + cascade FK), T7 (BlobStore.deletePrefix),
// and T8 (MetadataStore.deletePlaylist + JobQueue.requestCancelPlaylist):
//
//   0. non-supabase backend ⇒ 501 (backend/config mistake, NOT "not found" — never swallowed
//      by the client's 404→resolve idempotency)
//   1. auth (401 if no session)
//   1b. malformed (non-UUID) id ⇒ 404 (mirrors app/api/videos/[id]/archive/route.ts's UUID_RE
//      guard) — before the pre-delete read, so a garbage id never reaches the DB
//   2. pre-delete read — this is where the "real" 404 comes from (NOT the delete rowcount); also
//      captures playlist_key BEFORE the DB delete, for the blob Principal (Global Constraints,
//      spec §B5/D5)
//   3. best-effort job cancel (all kinds) — a cancel-RPC failure must not block the delete
//   4. DB delete (commit point) — cascades videos/jobs/share_tokens via the 0019 FKs
//   5. best-effort blob prefix delete — a failure here still returns 200 (invisible orphans
//      accepted, §D5)
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { logError } from '@/lib/dev-logger';

const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status });

type Params = { params: Promise<{ id: string }> };

// Mirrors app/api/videos/[id]/archive/route.ts's UUID_RE guard. A malformed id is never a real
// row, so treat it as "not found" (404) instead of letting it fall through to the DB read and a
// generic 500.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function DELETE(_request: Request, { params }: Params): Promise<Response> {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  // review fix: 501 (not 404) — a non-supabase backend is a backend/config mistake that did NOT
  // delete anything, so the client's 404→resolve idempotency (lib/client/api.ts deletePlaylist)
  // must never swallow it as "already gone".
  if (backend !== 'supabase') return json({ error: 'unsupported' }, 501);

  const { id } = await params;

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  // review fix: validate id as a UUID BEFORE the pre-delete read — a garbage id is "not found",
  // not a DB-error-shaped 500.
  if (!UUID_RE.test(id)) return json({ error: 'not found' }, 404);

  try {
    // Pre-delete read (404 source, NOT the delete rowcount — a delete on a foreign/missing id
    // is a 0-row no-op, not an error). RLS confines this to the caller's own rows. Also
    // captures playlist_key BEFORE the DB delete, for the blob Principal below.
    const { data: row, error: readError } = await supabase
      .from('playlists').select('id, playlist_key').eq('id', id).maybeSingle();
    if (readError) throw readError;
    if (!row) return json({ error: 'not found' }, 404);

    const principal = getPrincipalFromSession({ userId: user.id }, row.playlist_key as string);
    const bundle = getStorageBundle({ supabaseClient: supabase });
    const queue = bundle.jobQueue; // optional on StorageBundle; the cloud branch guarantees it
    if (!queue) return json({ error: 'unsupported' }, 500);

    // Best-effort cancel-first (all kinds, via request_cancel_playlist_jobs): a failure here
    // must not block the delete — the cascade below removes the job rows regardless.
    try {
      await queue.requestCancelPlaylist(id);
    } catch (e) {
      console.error(`DELETE /api/playlists/${id}: cancel-first failed (continuing)`, e);
    }

    // Commit point: DB delete cascades videos/jobs/share_tokens (0019 FKs).
    await bundle.metadataStore.deletePlaylist(principal, id);

    // Best-effort blob cleanup AFTER the DB delete — a failure here still returns 200
    // (invisible orphans accepted, spec §D5).
    try {
      await bundle.blobStore.deletePrefix(principal, '');
    } catch (e) {
      console.error(`DELETE /api/playlists/${id}: blob cleanup failed (invisible orphan accepted)`, e);
    }

    return json({ deleted: true }, 200);
  } catch (err) {
    logError(`playlists:delete:${id}`, err);   // never swallow the delete's real failure
    return json({ error: 'internal error' }, 500);
  }
}
