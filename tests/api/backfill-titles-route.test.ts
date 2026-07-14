// tests/api/backfill-titles-route.test.ts
//
// Unit coverage for POST /api/playlists/backfill-titles (Task 4, BUG-6 backfill).
// Behaviors covered here (see docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md Task 4):
//   1 — 401 unauthenticated
//   2 — 500 when YOUTUBE_API_KEY is unset
//   4 — null fetch result: row skipped (not updated), still counted in attempted
//   5 — per-row error isolation: one throwing row doesn't stop the others; route still 200
//   6 — no prefix starvation: ALL of the owner's null-title rows are processed per call (the
//       once-per-session + per-user sidebar guard is the real bound on call frequency, not a
//       row slice). A BACKFILL_SANITY_MAX defensive abuse ceiling only kicks in past 1000
//       null-title rows in one owner — see behavior 6b.
//   6b — sanity ceiling: past BACKFILL_SANITY_MAX null-title rows, processing is capped and a
//       console.warn is emitted (abuse backstop, not the normal-case behavior).
//   6c — no prefix starvation regression test: several early null-title rows are permanently
//       unfillable (fetch → null) while a later row IS fillable; the later row must still get
//       its title filled in the same call.
//   8 — non-supabase backend ⇒ 501 (backend/config mistake, NOT "not found")
// Behaviors 3 and 7 (real backfill + owner isolation) are covered by the integration test
// (tests/integration/backfill-titles-route.test.ts) against real local Supabase/RLS.

let mockGetUser: jest.Mock;
let mockBundle: any;
let mockFetchPlaylistTitleOrNull: jest.Mock;

jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn(() => ({ auth: { getUser: mockGetUser } })) }));
jest.mock('@/lib/storage/resolve', () => ({
  ...jest.requireActual('@/lib/storage/resolve'),
  getStorageBundle: jest.fn(() => mockBundle),
}));
jest.mock('@/lib/youtube', () => ({
  fetchPlaylistTitleOrNull: jest.fn((...args: unknown[]) => mockFetchPlaylistTitleOrNull(...args)),
}));

import { POST } from '@/app/api/playlists/backfill-titles/route';

function makePlaylist(overrides: Partial<{ id: string; playlistKey: string; playlistUrl: string; playlistTitle: string | null; createdAt: string }> = {}) {
  return {
    id: overrides.id ?? 'row-1',
    playlistKey: overrides.playlistKey ?? 'listA',
    playlistUrl: overrides.playlistUrl ?? 'https://youtube.com/playlist?list=listA',
    playlistTitle: overrides.playlistTitle ?? null,
    createdAt: overrides.createdAt ?? '2026-01-01T00:00:00.000Z',
  };
}

const post = () => POST();

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  process.env.YOUTUBE_API_KEY = 'test-key';
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockFetchPlaylistTitleOrNull = jest.fn(async () => 'Fetched Title');
  mockBundle = {
    metadataStore: {
      listPlaylists: jest.fn(async () => [makePlaylist()]),
      setPlaylistTitleIfNull: jest.fn(async () => ({ updated: true })),
    },
  };
});

it('401 when unauthenticated', async () => {
  mockGetUser = jest.fn(async () => ({ data: { user: null } }));
  const res = await post();
  expect(res.status).toBe(401);
  expect(mockBundle.metadataStore.listPlaylists).not.toHaveBeenCalled();
});

it('500 when YOUTUBE_API_KEY is unset', async () => {
  delete process.env.YOUTUBE_API_KEY;
  const res = await post();
  expect(res.status).toBe(500);
  expect(mockBundle.metadataStore.listPlaylists).not.toHaveBeenCalled();
});

it('skips a row whose fetch returns null: not updated, still attempted', async () => {
  mockFetchPlaylistTitleOrNull = jest.fn(async () => null);
  const res = await post();
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ updated: 0, attempted: 1 });
  expect(mockBundle.metadataStore.setPlaylistTitleIfNull).not.toHaveBeenCalled();
});

it('isolates a per-row fetch error: other rows still processed, route still 200', async () => {
  mockBundle.metadataStore.listPlaylists = jest.fn(async () => [
    makePlaylist({ id: 'row-1', playlistKey: 'listA' }),
    makePlaylist({ id: 'row-2', playlistKey: 'listB' }),
  ]);
  mockFetchPlaylistTitleOrNull = jest.fn(async (playlistId: string) => {
    if (playlistId === 'listA') throw new Error('YouTube API exploded');
    return 'Good Title';
  });
  const res = await post();
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ updated: 1, attempted: 2 });
  expect(mockBundle.metadataStore.setPlaylistTitleIfNull).toHaveBeenCalledTimes(1);
  expect(mockBundle.metadataStore.setPlaylistTitleIfNull).toHaveBeenCalledWith(
    expect.objectContaining({ indexKey: 'listB' }),
    'Good Title',
  );
});

it('behavior 6: processes ALL null-title rows in one call, not just the first 200 (no prefix starvation)', async () => {
  const rows = Array.from({ length: 250 }, (_, i) => makePlaylist({ id: `row-${i}`, playlistKey: `list-${i}` }));
  mockBundle.metadataStore.listPlaylists = jest.fn(async () => rows);
  const res = await post();
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ updated: 250, attempted: 250 });
  expect(mockFetchPlaylistTitleOrNull).toHaveBeenCalledTimes(250);
  expect(mockBundle.metadataStore.setPlaylistTitleIfNull).toHaveBeenCalledTimes(250);
});

it('behavior 6b: past the BACKFILL_SANITY_MAX abuse ceiling, processing is capped and a warning is logged', async () => {
  const rows = Array.from({ length: 1250 }, (_, i) => makePlaylist({ id: `row-${i}`, playlistKey: `list-${i}` }));
  mockBundle.metadataStore.listPlaylists = jest.fn(async () => rows);
  const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
  const res = await post();
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ updated: 1000, attempted: 1000 });
  expect(mockFetchPlaylistTitleOrNull).toHaveBeenCalledTimes(1000);
  expect(warnSpy).toHaveBeenCalledTimes(1);
  warnSpy.mockRestore();
});

it('behavior 6c: no prefix starvation — a later fillable row is not starved behind early unfillable rows', async () => {
  // First 5 null-title rows are permanently unfillable (deleted/private YouTube list ⇒ null).
  // A 6th row, later in the list, IS fillable. With a naive slice(0, N) cap that only ever
  // re-selects the first N rows, this row would never be attempted across sessions.
  const unfillable = Array.from({ length: 5 }, (_, i) => makePlaylist({ id: `dead-${i}`, playlistKey: `dead-${i}` }));
  const fillable = makePlaylist({ id: 'row-fillable', playlistKey: 'list-fillable' });
  mockBundle.metadataStore.listPlaylists = jest.fn(async () => [...unfillable, fillable]);
  mockFetchPlaylistTitleOrNull = jest.fn(async (playlistId: string) =>
    playlistId === 'list-fillable' ? 'Fillable Title' : null,
  );

  const res = await post();
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ updated: 1, attempted: 6 });
  expect(mockFetchPlaylistTitleOrNull).toHaveBeenCalledWith('list-fillable', 'test-key');
  expect(mockBundle.metadataStore.setPlaylistTitleIfNull).toHaveBeenCalledTimes(1);
  expect(mockBundle.metadataStore.setPlaylistTitleIfNull).toHaveBeenCalledWith(
    expect.objectContaining({ indexKey: 'list-fillable' }),
    'Fillable Title',
  );
});

it('filters out already-titled rows before the backfill loop', async () => {
  mockBundle.metadataStore.listPlaylists = jest.fn(async () => [
    makePlaylist({ id: 'row-1', playlistKey: 'listA', playlistTitle: 'Already Titled' }),
    makePlaylist({ id: 'row-2', playlistKey: 'listB', playlistTitle: null }),
  ]);
  const res = await post();
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ updated: 1, attempted: 1 });
  expect(mockFetchPlaylistTitleOrNull).toHaveBeenCalledTimes(1);
  expect(mockFetchPlaylistTitleOrNull).toHaveBeenCalledWith('listB', 'test-key');
});

it('behavior 8: non-supabase backend ⇒ 501 unsupported (before any auth/DB call)', async () => {
  // review fix: a non-supabase backend is a backend/config mistake, NOT "not found" — 501
  // (matching the delete route's fix), so a misconfiguration doesn't read as "nothing to do".
  process.env.STORAGE_BACKEND = 'local';
  const res = await post();
  expect(res.status).toBe(501);
  expect(await res.json()).toEqual({ error: 'unsupported' });
  expect(mockGetUser).not.toHaveBeenCalled();
  expect(mockBundle.metadataStore.listPlaylists).not.toHaveBeenCalled();
});
