// tests/integration/concurrency.test.ts
//
// Proves claim_video_slot serializes concurrent appends via its playlist row-lock
// (SELECT … FOR UPDATE). Fire N concurrent calls; assert distinct positions + serials.
// Run via: npm run test:integration -- concurrency

import { newUser, signInAs } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import type { Principal } from '@/lib/storage/principal';

const N = 10;

test('concurrent claimVideoSlot on one playlist yields distinct positions + serials', async () => {
  const u = await newUser();
  const { client } = await signInAs(u.email, u.password);
  const s = new SupabaseMetadataStore(client);

  // id is unused; RLS derives owner from the JWT's auth.uid()
  const P: Principal = { id: '', indexKey: 'listConc' };
  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listConc' });

  const ids = Array.from({ length: N }, (_, i) => `vid${String(i).padStart(8, '0')}`);

  // Fire all N claims concurrently — the FOR UPDATE in claim_video_slot must
  // serialize them so no two slots share a position or serialNumber.
  const slots = await Promise.all(ids.map((id) => s.claimVideoSlot(P, id)));

  const serials = slots.map((x) => x.serialNumber).sort((a, b) => a - b);
  expect(new Set(serials).size).toBe(N);    // no duplicate serials

  // A6a — `position` is no longer returned by claimVideoSlot, so read the COLUMN to keep asserting
  // it. Deliberately not dropped: serial uniqueness and position uniqueness fail for different
  // reasons. `position` is protected by videos_playlist_position_uniq (0001:38), but serialNumber
  // lives in the `data` jsonb with NO constraint behind it — the row-lock is the only thing
  // preventing a duplicate, which is exactly what this test exists to prove.
  const { data: rows, error } = await client
    .from('videos').select('position').order('position', { ascending: true });
  expect(error).toBeNull();
  const positions = (rows ?? []).map((r) => r.position as number);
  expect(positions).toEqual(Array.from({ length: N }, (_, i) => i));  // 0..N-1, no gaps or dupes

  // All N reservation rows must be persisted
  const idx = await s.readIndex(P);
  expect(idx.videos).toHaveLength(N);
}, 30_000);
