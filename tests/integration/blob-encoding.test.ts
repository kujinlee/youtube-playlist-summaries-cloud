// Backlog #36, plan T2 — the encoder wired into SupabaseBlobStore, against a live LOCAL Supabase
// stack. Behaviors 6, 7, 11, 13.
// Run via: npm run test:integration -- blob-encoding
// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { newUser, signInAs } from './helpers/clients';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { Principal } from '@/lib/storage/principal';
import type { BlobStore } from '@/lib/storage/blob-store';
import { isLocalSupabaseUrl } from '@/lib/supabase/is-local-url';

jest.setTimeout(20_000);

// PROD GUARD, in two independent parts.
//
//  (a) ABSENT is a FAILURE, not a pass. `NEXT_PUBLIC_SUPABASE_URL` is the name setup.ts actually
//      sets; `SUPABASE_URL` is set by nothing in this repo.
//  (b) LOCAL is decided by PARSED HOST, never by a string prefix. A prefix test such as
//      /^https?:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/ MEASURABLY passes
//      `https://localhost:54321@project.supabase.co` — userinfo before the `@` — whose real
//      hostname is `project.supabase.co`. `isLocalSupabaseUrl` (lib/supabase/is-local-url.ts:7)
//      already parses host-exact and fail-closed; it was written for the dev-login gate (#13).
beforeAll(() => {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!url) throw new Error('NEXT_PUBLIC_SUPABASE_URL is unset — treat this as NOT RUN, never as safe');
  if (!isLocalSupabaseUrl(url)) throw new Error(`refusing to run against a non-local stack: ${url}`);
});

let blob: BlobStore;
let P: Principal;
let LOCAL_P: Principal;
const tmpRoots: string[] = [];

beforeEach(async () => {
  // A fresh isolated user per test, JWT-scoped — the idiom at tests/integration/blob-store.test.ts.
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  blob = new SupabaseBlobStore(client, 'artifacts');
  P = { id: userId, indexKey: `k-${userId.slice(0, 8)}` } as Principal;
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'blob-encoding-'));
  tmpRoots.push(dir);
  LOCAL_P = localPrincipal(dir);
});

// Clean up: the local dirs here, and every remote object under each test's playlist root. The
// per-test user is disposable, but the objects are not — deletePrefix('') is the store's own sweep.
afterEach(async () => {
  try { await blob.deletePrefix(P, ''); } catch { /* a test may already have swept it */ }
});
afterAll(async () => {
  await Promise.all(tmpRoots.map((d) => fs.rm(d, { recursive: true, force: true })));
});

const KOREAN = '003_한국어.md';

it('behavior 6 — put then get round-trips a Korean key', async () => {
  await blob.put(P, KOREAN, Buffer.from('hi', 'utf8'), 'text/markdown');
  expect((await blob.get(P, KOREAN))!.toString('utf8')).toBe('hi');
});

it('behavior 7 — putStaged then promote lands a Korean key correctly', async () => {
  const ref = await blob.putStaged(P, KOREAN, Buffer.from('body', 'utf8'), 'text/markdown');
  await blob.promote(ref);
  expect((await blob.get(P, KOREAN))!.toString('utf8')).toBe('body');
});

it('behavior 11 — deletePrefix("") removes everything under the playlist root', async () => {
  await blob.put(P, KOREAN, Buffer.from('x', 'utf8'), 'text/markdown');
  await blob.deletePrefix(P, '');
  expect(await blob.get(P, KOREAN)).toBeNull();
});

it('behavior 13 — the local and in-memory adapters are IDENTITY', async () => {
  for (const store of [localBlobStore, new InMemoryBlobStore()]) {
    await store.put(LOCAL_P, KOREAN, Buffer.from('x', 'utf8'), 'text/markdown');
    expect(await store.list(LOCAL_P, '')).toContain(KOREAN);
  }
});
