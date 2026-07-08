import { randomUUID } from 'crypto';
import { newUser, signInAs, adminClient } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';

test('resolvePlaylistId creates then returns the same id (idempotent, owner-scoped)', async () => {
  const a = await newUser(); const { client: ca, userId: aid } = await signInAs(a.email, a.password);
  const key = `PL-${randomUUID()}`;
  const url = `https://www.youtube.com/playlist?list=${key}`;
  const store = new SupabaseMetadataStore(ca);
  const id1 = await store.resolvePlaylistId({ id: aid, indexKey: key }, url);
  const id2 = await store.resolvePlaylistId({ id: aid, indexKey: key }, url);
  expect(id1).toBe(id2);
  const row = await adminClient().from('playlists').select('playlist_url,owner_id').eq('id', id1).single();
  expect(row.data!.playlist_url).toBe(url);
  expect(row.data!.owner_id).toBe(aid);

  const b = await newUser(); const { client: cb, userId: bid } = await signInAs(b.email, b.password);
  const idB = await new SupabaseMetadataStore(cb).resolvePlaylistId({ id: bid, indexKey: key }, url);
  expect(idB).not.toBe(id1);   // same playlist_key, different owner → different row
});
