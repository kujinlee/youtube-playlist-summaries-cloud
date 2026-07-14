// tests/api/backfill-titles-route.test.ts
//
// Unit coverage for POST /api/playlists/backfill-titles (Task 4, BUG-6 backfill).
// Behaviors covered here (see docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md Task 4):
//   1 — 401 unauthenticated
//   2 — 500 when YOUTUBE_API_KEY is unset
//   4 — null fetch result: row skipped (not updated), still counted in attempted
//   5 — per-row error isolation: one throwing row doesn't stop the others; route still 200
//   6 — row ceiling: at most 200 null-title rows are processed
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

it('caps processing at 200 null-title rows (runaway backstop)', async () => {
  const rows = Array.from({ length: 250 }, (_, i) => makePlaylist({ id: `row-${i}`, playlistKey: `list-${i}` }));
  mockBundle.metadataStore.listPlaylists = jest.fn(async () => rows);
  const res = await post();
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body).toEqual({ updated: 200, attempted: 200 });
  expect(mockFetchPlaylistTitleOrNull).toHaveBeenCalledTimes(200);
  expect(mockBundle.metadataStore.setPlaylistTitleIfNull).toHaveBeenCalledTimes(200);
});

it('filters out already-titled rows before the cap/backfill loop', async () => {
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
