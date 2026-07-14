// app/api/playlists/[id]/route.ts
//
// DELETE /api/playlists/[id] — full hard-delete of a cloud playlist (Task 9). Cloud-only.
// Orchestrates the pieces built in T6 (cancel RPC + cascade FK), T7 (BlobStore.deletePrefix),
// and T8 (MetadataStore.deletePlaylist + JobQueue.requestCancelPlaylist):
//
//   1. auth (401 if no session)
//   2. pre-delete read — this is where 404 comes from (NOT the delete rowcount); also
//      captures playlist_key BEFORE the DB delete, for the blob Principal (Global Constraints,
//      spec §B5/D5)
//   3. best-effort job cancel (all kinds) — a cancel-RPC failure must not block the delete
//   4. DB delete (commit point) — cascades videos/jobs/share_tokens via the 0019 FKs
//   5. best-effort blob prefix delete — a failure here still returns 200 (invisible orphans
//      accepted, §D5)
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';

const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status });

type Params = { params: Promise<{ id: string }> };

export async function DELETE(_request: Request, { params }: Params): Promise<Response> {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend !== 'supabase') return json({ error: 'unsupported' }, 404); // local backend: no delete route

  const { id } = await params;

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

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
  } catch {
    return json({ error: 'internal error' }, 500);
  }
}
