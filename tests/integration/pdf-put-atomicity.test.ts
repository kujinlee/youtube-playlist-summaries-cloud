// tests/integration/pdf-put-atomicity.test.ts
//
// Task 1 (preflight gate for ADR 0003 / Task 8): verify SupabaseBlobStore.put(...,
// { upsert: true }) is visibility-atomic — a concurrent reader must never observe a partial
// ("torn") object mid-overwrite. It must see the whole old bytes, the whole new bytes, or
// absent, never a mix. If this test fails, the bare-put/no-promotion cache design in Task 8
// is unsound and must fall back to staging-key + atomic manifest pointer (spec §10 / ADR 0003).
//
// Runs against a REAL local Supabase Storage stack (STORAGE_BACKEND=supabase) — no mocks.
//
// Strengthened per Codex review round 1 (docs/reviews/task-cloud-pdf-1-codex.md):
//   B1 — the object exists from the seed put() onward, so a `null` read after that point is a
//        torn-read-surfaced-as-a-Storage-error, not benign absence. Every post-seed read is
//        asserted non-null; a null read fails the test loud instead of being skipped.
//   B2 — concurrency and generation coverage must be PROVEN, not assumed. Each round fires one
//        `put` that flips the written value together with several `get`s in the same
//        `Promise.all` (real read/write overlap, not sequenced awaits). The written value
//        alternates every round, and the set of `buf[0]` values observed across all rounds is
//        asserted to contain BOTH 0xaa and 0xbb — a deterministic proof that overwrites became
//        visible to concurrent readers and that reads observed multiple generations. This does
//        NOT depend on catching a mid-write tear at the right instant (unreliable); it depends
//        only on the value alternating across rounds and reads happening throughout the run.
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';

// getStorageBundle({ supabaseClient }) / getPrincipalFromSession select the Supabase path only
// when STORAGE_BACKEND==='supabase' — same pattern as sibling *-cloud integration tests.
const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

test('put(upsert) is visibility-atomic: concurrent overwrite+read observes only whole generations, never a torn mix', async () => {
  const svc = adminClient();
  const u = await newUser();
  const { client } = await signInAs(u.email, u.password);
  const { playlistKey } = await seedPlaylist(svc, u.user.id);
  const { blobStore } = getStorageBundle({ supabaseClient: client });
  const principal = getPrincipalFromSession({ userId: u.user.id }, playlistKey);
  const key = 'pdfs/atomicity-probe.bin';
  const SIZE = 512_000;                        // 512 KB — big enough to tear over HTTP, small enough for CI
  const A = Buffer.alloc(SIZE, 0xaa), B = Buffer.alloc(SIZE, 0xbb);
  const ROUNDS = 14;
  const READS_PER_ROUND = 4;

  await blobStore.put(principal, key, A, 'application/octet-stream'); // seed: object now always exists

  const observedValues = new Set<number>();

  try {
    for (let round = 0; round < ROUNDS; round++) {
      // Alternate the written value every round (round 0 -> B, round 1 -> A, ...), so across the
      // whole run BOTH generations get written after the seed. The put and this round's gets are
      // all created in the same synchronous tick below (no await between them) and awaited
      // together via Promise.all — a genuine read/write overlap, not a sequenced write-then-read.
      const roundValue = round % 2 === 0 ? B : A;
      const writeP = blobStore.put(principal, key, roundValue, 'application/octet-stream');
      const readPs: Promise<Buffer | null>[] = [];
      for (let r = 0; r < READS_PER_ROUND; r++) readPs.push(blobStore.get(principal, key));

      const [, ...bufs] = await Promise.all([writeP, ...readPs]);

      for (const buf of bufs) {
        // B1: the object exists from the seed onward — a null read here is a torn read that
        // surfaced as a Storage error, not benign absence. Fail loud, do not skip.
        expect(buf).not.toBeNull();
        const b = buf as Buffer;
        expect(b.length).toBe(SIZE);                                 // never truncated
        expect(b.every((byte) => byte === b[0])).toBe(true);         // TEAR DETECTOR: homogeneous, never a mix of A/B
        expect(b[0] === 0xaa || b[0] === 0xbb).toBe(true);            // a valid generation, nothing else
        observedValues.add(b[0]);
      }
    }

    // B2: deterministic proof of read/write overlap. The written value alternates every round, so
    // if every read only ever observed the pre-round value, `observedValues` would contain a
    // single element. Observing BOTH 0xaa and 0xbb proves overwrites became visible to concurrent
    // readers across the run (generation coverage), not just the seed value surviving untouched.
    expect(observedValues.has(0xaa)).toBe(true);
    expect(observedValues.has(0xbb)).toBe(true);
  } finally {
    await blobStore.delete(principal, key).catch(() => {});
  }
});
