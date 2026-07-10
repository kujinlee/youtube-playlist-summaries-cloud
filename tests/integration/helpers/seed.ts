// tests/integration/helpers/seed.ts
import { randomUUID } from 'crypto';
import type { SupabaseClient } from '@supabase/supabase-js';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';

/** Create an owned playlist row; returns its UUID id + playlist_key (the principal.indexKey). */
export async function seedPlaylist(
  svc: SupabaseClient, ownerId: string,
): Promise<{ playlistId: string; playlistKey: string }> {
  const playlistKey = `k-${randomUUID()}`;
  const { data, error } = await svc.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: playlistKey, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return { playlistId: data!.id as string, playlistKey };
}

/** Insert a video row MIRRORING the worker's promoted shape (summary-handler.ts:149-164 +
 *  persist_summary 0009). Sets top-level owner_id (NOT NULL + composite FK) and a `data` jsonb
 *  with the top-level `summaryMd`/`language`/`serialNumber` the route reads AND
 *  `artifacts.summaryMd.{key,status}` the reserve RPC + route status-gate read. Defaults to
 *  `status:'promoted'`; pass `status:'committed'` for the finalizing-window / unpromoted cases. */
export async function seedPromotedVideo(
  svc: SupabaseClient,
  opts: { ownerId: string; playlistId: string; videoId?: string; base?: string;
          status?: 'promoted' | 'committed'; position?: number },
): Promise<{ videoId: string; base: string }> {
  const videoId = opts.videoId ?? `v-${randomUUID()}`;
  const base = opts.base ?? videoId;
  const status = opts.status ?? 'promoted';
  const { error } = await svc.from('videos').insert({
    playlist_id: opts.playlistId,
    owner_id: opts.ownerId,                       // NOT NULL + composite FK (playlist_id, owner_id)
    video_id: videoId,
    position: opts.position ?? 1,
    data: {
      id: videoId,
      serialNumber: opts.position ?? 1,
      language: 'en',                             // route passes video.language to resolveMagazineModel
      summaryMd: `${base}.md`,                    // top-level key the route get()s (summary-handler.ts:157)
      docVersion: 1,
      artifacts: { summaryMd: { key: `${base}.md`, status } },
    },
  });
  if (error) throw error;
  return { videoId, base };
}

/** Upload the summary MD blob to {owner}/{playlist_key}/{base}.md — the exact key the route get()s
 *  (SupabaseBlobStore objectKey = `${p.id}/${p.indexKey}/${key}`). Needed only by Tasks 6/7 (the
 *  reserve RPC in Task 1 reads DB status only, not the blob). */
export async function seedSummaryBlob(
  svc: SupabaseClient, ownerId: string, playlistKey: string, base: string, md: string,
): Promise<void> {
  const { error } = await svc.storage.from(ARTIFACTS_BUCKET)
    .upload(`${ownerId}/${playlistKey}/${base}.md`, Buffer.from(md, 'utf-8'),
            { contentType: 'text/markdown', upsert: true });
  if (error) throw error;
}
