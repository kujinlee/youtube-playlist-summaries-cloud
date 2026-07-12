// tests/integration/pdf-put-atomicity.test.ts
//
// Task 1 (preflight gate for ADR 0003 / Task 8): verify SupabaseBlobStore.put(...,
// { upsert: true }) is visibility-atomic — a concurrent reader must never observe a partial
// ("torn") object mid-overwrite. It must see the whole old bytes, the whole new bytes, or
// absent, never a mix. If this test fails, the bare-put/no-promotion cache design in Task 8
// is unsound and must fall back to staging-key + atomic manifest pointer (spec §10 / ADR 0003).
//
// Runs against a REAL local Supabase Storage stack (STORAGE_BACKEND=supabase) — no mocks.
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';

// getStorageBundle({ supabaseClient }) / getPrincipalFromSession select the Supabase path only
// when STORAGE_BACKEND==='supabase' — same pattern as sibling *-cloud integration tests.
const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

test('put(upsert) is visibility-atomic: concurrent overwrite+read never yields a partial object', async () => {
  const svc = adminClient();
  const u = await newUser();
  const { client } = await signInAs(u.email, u.password);
  const { playlistKey } = await seedPlaylist(svc, u.user.id);
  const { blobStore } = getStorageBundle({ supabaseClient: client });
  const principal = getPrincipalFromSession({ userId: u.user.id }, playlistKey);
  const key = 'pdfs/atomicity-probe.bin';
  const SIZE = 512_000;                       // 512 KB — big enough to tear, small enough for CI
  const A = Buffer.alloc(SIZE, 0xaa), B = Buffer.alloc(SIZE, 0xbb);

  await blobStore.put(principal, key, A, 'application/octet-stream');
  const reads: Promise<Buffer | null>[] = [], writes: Promise<void>[] = [];
  for (let i = 0; i < 8; i++) {
    writes.push(blobStore.put(principal, key, i % 2 ? A : B, 'application/octet-stream'));
    reads.push(blobStore.get(principal, key));
  }
  await Promise.all(writes);
  for (const buf of await Promise.all(reads)) {
    if (buf === null) continue;                       // absent is fine; never partial
    expect(buf.length).toBe(SIZE);
    expect(buf.every((byte) => byte === buf[0])).toBe(true);   // homogeneous → whole A or whole B
    expect(buf[0] === 0xaa || buf[0] === 0xbb).toBe(true);
  }
  await blobStore.delete(principal, key);
});
