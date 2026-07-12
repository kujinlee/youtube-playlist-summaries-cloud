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
//   B2 — concurrency and generation coverage are exercised explicitly. Each round fires one
//        `put` that flips the written value together with several `get`s created in the same
//        synchronous tick and awaited via one `Promise.all` — client-level concurrent dispatch
//        (reads in flight alongside the write), not sequenced write-then-read. The real atomicity
//        oracle is the per-read homogeneity check (below): it runs on every read under that
//        concurrent dispatch and never observes a torn mix. The written value alternates every
//        round and the set of observed `buf[0]` values is asserted to contain BOTH 0xaa and 0xbb
//        — this proves overwrites propagate to concurrent readers (fresh post-seed writes become
//        visible, not just the seed surviving), i.e. generation coverage. It does NOT by itself
//        prove any single read's server-side processing overlapped a write's commit window — that
//        is unobservable from the client, and because each round's pre-value also alternates, both
//        generations would appear from alternation alone.
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
  const SIZE = 512_000;                        // 512 KB — a pragmatic probe size (large enough a non-atomic backend could plausibly expose a partial read over HTTP; not a proof of tear-ability), small enough for CI
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

    // B2: generation coverage — overwrites propagate to concurrent readers. Observing BOTH 0xaa
    // and 0xbb proves reads saw fresh post-seed overwrites (not just the seed value frozen in
    // place), and that the tear detector above ran against multiple generations. It does NOT by
    // itself prove any single read overlapped its round's in-flight write: each round's pre-value
    // also alternates, so both generations would appear from alternation alone. The atomicity
    // guarantee comes from the per-read homogeneity assertion never failing under the concurrent
    // dispatch above, not from this set check. Server-side visibility overlap is unobservable from
    // the client (see docs/reviews/spec-cloud-pdf-atomicity.md "Precisely what this proves").
    expect(observedValues.has(0xaa)).toBe(true);
    expect(observedValues.has(0xbb)).toBe(true);
  } finally {
    await blobStore.delete(principal, key).catch(() => {});
  }
});
