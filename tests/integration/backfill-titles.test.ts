// tests/integration/backfill-titles.test.ts
//
// Integration coverage for MetadataStore.setPlaylistTitleIfNull (Task 3, BUG-6) against a
// live local Supabase stack. Run via: npm run test:integration -- backfill-titles
// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).

import { newUser, signInAs } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import type { Principal } from '@/lib/storage/principal';

// id is unused in cloud mode; RLS derives owner from the JWT's auth.uid().
const P: Principal = { id: '', indexKey: 'listBackfill' };

async function storeForNewUser(): Promise<SupabaseMetadataStore> {
  const u = await newUser();
  const { client } = await signInAs(u.email, u.password);
  return new SupabaseMetadataStore(client);
}

describe('setPlaylistTitleIfNull integration', () => {
  test('titled row: no-op — returns {updated:false}, title unchanged', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, {
      playlistUrl: 'https://youtube.com/playlist?list=listBackfill',
      playlistTitle: 'Already Titled',
    });

    const result = await store.setPlaylistTitleIfNull(P, 'Should Not Apply');
    expect(result).toEqual({ updated: false });

    const idx = await store.readIndex(P);
    expect(idx.playlistTitle).toBe('Already Titled');
  });

  test('null-title row: fills the title — returns {updated:true}, title set', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, {
      playlistUrl: 'https://youtube.com/playlist?list=listBackfill',
      // playlistTitle omitted — row created with playlist_title = null
    });

    const result = await store.setPlaylistTitleIfNull(P, 'Backfilled Title');
    expect(result).toEqual({ updated: true });

    const idx = await store.readIndex(P);
    expect(idx.playlistTitle).toBe('Backfilled Title');
  });

  test('owner isolation: setPlaylistTitleIfNull never fills another owner\'s row', async () => {
    const storeA = await storeForNewUser();
    await storeA.setPlaylistMeta(P, {
      playlistUrl: 'https://youtube.com/playlist?list=listBackfill',
      // null title
    });

    const storeB = await storeForNewUser();
    // B has no row at all for this playlist_key (owner-scoped) — the conditional update
    // matches zero rows under B's ownership, so it must not touch A's row.
    const resultB = await storeB.setPlaylistTitleIfNull(P, 'B Attempted Title');
    expect(resultB).toEqual({ updated: false });

    const idxA = await storeA.readIndex(P);
    expect(idxA.playlistTitle).toBeUndefined();
  });
});
