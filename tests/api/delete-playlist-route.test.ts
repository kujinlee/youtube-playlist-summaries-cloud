// tests/api/delete-playlist-route.test.ts
//
// Unit coverage for DELETE /api/playlists/[id] (Task 9, full hard-delete route).
// Behaviors covered here (see docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md Task 9):
//   4 — blob-cleanup failure ⇒ still 200 {deleted:true} (invisible orphans accepted, §D5)
//   5 — the playlist row READ happens before the DB delete, and the Principal passed to
//       blobStore.deletePrefix has indexKey === the captured playlist_key
//   7 — cloud-only: local backend ⇒ 501/unsupported (a backend/config mistake, not "not found")
// Behaviors 1 (401), 2 (404 not owned/missing), 3 (happy-path order against real DB/blobs),
// and 6 (second delete ⇒ 404) are covered by the integration test
// (tests/integration/delete-playlist-route.test.ts) against real local Supabase/RLS.

let mockGetUser: jest.Mock;
let mockMaybeSingle: jest.Mock;
let mockBundle: any;
let mockClient: any;

jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn(() => mockClient) }));
jest.mock('@/lib/storage/resolve', () => ({
  ...jest.requireActual('@/lib/storage/resolve'),
  getStorageBundle: jest.fn(() => mockBundle),
}));

import { DELETE } from '@/app/api/playlists/[id]/route';

const PLAYLIST_ID = '11111111-1111-1111-1111-111111111111';
const PLAYLIST_KEY = 'listX-key';

// Records the order operations were invoked in, so behavior 5 (read-before-delete) can be
// asserted without depending on implementation internals beyond call order.
let callOrder: string[];

function makeClient(row: { id: string; playlist_key: string } | null) {
  mockMaybeSingle = jest.fn(async () => {
    callOrder.push('read');
    return { data: row, error: null };
  });
  return {
    auth: { getUser: mockGetUser },
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        eq: jest.fn(() => ({
          maybeSingle: mockMaybeSingle,
        })),
      })),
    })),
  };
}

const del = (id: string) =>
  DELETE(new Request(`http://x/api/playlists/${id}`, { method: 'DELETE' }) as any, {
    params: Promise.resolve({ id }),
  });

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  callOrder = [];
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockClient = makeClient({ id: PLAYLIST_ID, playlist_key: PLAYLIST_KEY });
  mockBundle = {
    jobQueue: {
      requestCancelPlaylist: jest.fn(async () => {
        callOrder.push('cancel');
        return { cancelled: 0 };
      }),
    },
    metadataStore: {
      deletePlaylist: jest.fn(async () => {
        callOrder.push('delete');
      }),
    },
    blobStore: {
      deletePrefix: jest.fn(async (..._args: unknown[]) => {
        callOrder.push('blob');
      }),
    },
  };
});

it('behavior 4: blob-cleanup failure still returns 200 {deleted:true}', async () => {
  mockBundle.blobStore.deletePrefix = jest.fn(async () => { throw new Error('storage backend exploded'); });
  const res = await del(PLAYLIST_ID);
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ deleted: true });
  expect(mockBundle.metadataStore.deletePlaylist).toHaveBeenCalledTimes(1);
});

it('behavior 5: the row read happens before the DB delete, before blob cleanup, after cancel-first', async () => {
  const res = await del(PLAYLIST_ID);
  expect(res.status).toBe(200);
  expect(callOrder.indexOf('read')).toBeLessThan(callOrder.indexOf('delete'));
  expect(callOrder.indexOf('delete')).toBeLessThan(callOrder.indexOf('blob'));
  // review fix: the named "cancel-first" step must actually run before the DB delete, not just
  // be recorded in callOrder with its position unchecked.
  expect(callOrder.indexOf('cancel')).toBeLessThan(callOrder.indexOf('delete'));
});

it('behavior 5: the Principal passed to deletePrefix has indexKey === the captured playlist_key', async () => {
  await del(PLAYLIST_ID);
  expect(mockBundle.blobStore.deletePrefix).toHaveBeenCalledWith(
    expect.objectContaining({ indexKey: PLAYLIST_KEY }),
    '',
  );
});

it('behavior 5: the Principal passed to metadataStore.deletePlaylist also has indexKey === playlist_key', async () => {
  await del(PLAYLIST_ID);
  expect(mockBundle.metadataStore.deletePlaylist).toHaveBeenCalledWith(
    expect.objectContaining({ indexKey: PLAYLIST_KEY }),
    PLAYLIST_ID,
  );
});

it('behavior 7: local backend ⇒ 501 unsupported (before any auth/DB call)', async () => {
  // review fix: a non-supabase backend is a backend/config mistake, NOT "not found" — 501 so the
  // client's 404→resolve idempotency (lib/client/api.ts deletePlaylist) never swallows it.
  process.env.STORAGE_BACKEND = 'local';
  const res = await del(PLAYLIST_ID);
  expect(res.status).toBe(501);
  expect(await res.json()).toEqual({ error: 'unsupported' });
  expect(mockGetUser).not.toHaveBeenCalled();
});

it('review fix: malformed (non-UUID) id ⇒ 404 before the pre-delete read, nothing deleted', async () => {
  const res = await del('not-a-uuid');
  expect(res.status).toBe(404);
  expect(await res.json()).toEqual({ error: 'not found' });
  expect(mockMaybeSingle).not.toHaveBeenCalled();
  expect(mockBundle.metadataStore.deletePlaylist).not.toHaveBeenCalled();
});

it('cancel-first failure does not block the DB delete or the 200 response', async () => {
  mockBundle.jobQueue.requestCancelPlaylist = jest.fn(async () => { throw new Error('rpc down'); });
  const res = await del(PLAYLIST_ID);
  expect(res.status).toBe(200);
  expect(mockBundle.metadataStore.deletePlaylist).toHaveBeenCalledTimes(1);
});
