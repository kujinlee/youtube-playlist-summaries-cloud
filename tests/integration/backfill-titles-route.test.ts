// tests/integration/backfill-titles-route.test.ts
//
// POST /api/playlists/backfill-titles (Task 4, BUG-6 backfill) against a REAL local
// Supabase stack. Auth plumbing mocked exactly like tests/integration/playlists-route.test.ts
// (next/headers + @/lib/supabase/server → a real signed-in session client); RLS, listPlaylists,
// and setPlaylistTitleIfNull all run for real. `lib/youtube` is mocked (no real YouTube calls in
// tests) to return a deterministic title keyed off the playlist_key.
//
// Covers behaviors 3 (backfills null rows, counts correctly) and 7 (owner isolation — another
// owner's null-title rows are never touched). Behaviors 1,2,4,5,6 are unit-tested in
// tests/api/backfill-titles-route.test.ts.
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

jest.mock('@/lib/youtube', () => ({
  fetchPlaylistTitleOrNull: jest.fn(async (playlistId: string) => `Real Title for ${playlistId}`),
}));

import { POST } from '@/app/api/playlists/backfill-titles/route';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
const priorApiKey = process.env.YOUTUBE_API_KEY;
beforeAll(() => {
  process.env.STORAGE_BACKEND = 'supabase';
  process.env.YOUTUBE_API_KEY = 'test-key';
});
afterAll(() => {
  if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend;
  if (priorApiKey === undefined) delete process.env.YOUTUBE_API_KEY; else process.env.YOUTUBE_API_KEY = priorApiKey;
});

function anonClient(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } });
}

async function titleOf(playlistId: string): Promise<string | null> {
  const { data, error } = await svc.from('playlists').select('playlist_title').eq('id', playlistId).single();
  if (error) throw error;
  return data!.playlist_title as string | null;
}

describe('POST /api/playlists/backfill-titles (cloud)', () => {
  it('unauthenticated → 401', async () => {
    mockClient = anonClient();
    const res = await POST();
    expect(res.status).toBe(401);
  });

  it('backfills only the caller\'s own null-title rows, leaves titled rows untouched, and counts correctly', async () => {
    const owner = await newUser();
    const untitled1 = await seedPlaylist(svc, owner.user.id);
    const untitled2 = await seedPlaylist(svc, owner.user.id);
    const alreadyTitled = await seedPlaylist(svc, owner.user.id);
    await svc.from('playlists').update({ playlist_title: 'Pre-existing Title' }).eq('id', alreadyTitled.playlistId);

    const { client } = await signInAs(owner.email, owner.password);
    mockClient = client;

    const res = await POST();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ updated: 2, attempted: 2 });

    expect(await titleOf(untitled1.playlistId)).toBe(`Real Title for ${untitled1.playlistKey}`);
    expect(await titleOf(untitled2.playlistId)).toBe(`Real Title for ${untitled2.playlistKey}`);
    expect(await titleOf(alreadyTitled.playlistId)).toBe('Pre-existing Title'); // not clobbered, not counted
  });

  it("owner isolation: another owner's null-title rows are never touched by this call", async () => {
    const owner = await newUser();
    const other = await newUser();
    const otherUntitled = await seedPlaylist(svc, other.user.id);

    // owner has nothing to backfill; call still succeeds with zero counts and does not
    // touch other's row.
    const { client } = await signInAs(owner.email, owner.password);
    mockClient = client;

    const res = await POST();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ updated: 0, attempted: 0 });

    expect(await titleOf(otherUntitled.playlistId)).toBeNull();
  });
});
