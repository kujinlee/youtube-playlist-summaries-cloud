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

  const positions = slots.map((x) => x.position).sort((a, b) => a - b);
  const serials = slots.map((x) => x.serialNumber).sort((a, b) => a - b);

  expect(new Set(positions).size).toBe(N);  // no duplicate positions
  expect(new Set(serials).size).toBe(N);    // no duplicate serials

  // All N reservation rows must be persisted
  const idx = await s.readIndex(P);
  expect(idx.videos).toHaveLength(N);
}, 30_000);
