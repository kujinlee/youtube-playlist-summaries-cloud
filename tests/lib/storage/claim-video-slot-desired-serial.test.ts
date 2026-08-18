/**
 * `claimVideoSlot(p, videoId, desiredSerial?)` — the adapter contract.
 *
 * Behaviors table rows 9–14, docs/superpowers/plans/2026-07-31-serial-coherence-sync.md.
 *
 * WHY THIS PARAMETER EXISTS: `base` — the address of every derived blob (`models/<base>.json`,
 * `dig/<base>/<sectionId>.r<V>.md`) — is `<serial>_<slug>`. Cloud-sync copies the sender's
 * `summaryMd` KEY verbatim while letting the receiver allocate its own serial, so the receiver row
 * ends up saying `serialNumber: 7` next to a file named `003_alpha.md` and every dig blob under
 * `dig/003_alpha/` is silently orphaned. The receiver has to be able to ASK for a specific serial.
 *
 * The absence of the argument is meaningful and is NOT the same as passing a value: "no preference,
 * allocate one" (row 11, the legacy-sender case), which is exactly today's behavior.
 */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { Video } from '@/types';

const store = new LocalFsMetadataStore();
// assertOutputFolder requires the path to sit inside $HOME (macOS os.tmpdir() resolves outside it).
//
// ⛔ DELETE WHAT YOU CREATED — never sweep $HOME by prefix. This file was the VICTIM of that bug
// (local-metadata-store.test.ts swept `lms-`, which matches this file's `lms-serial-`), and it
// carried the same latent bug itself: sweeping `lms-serial-` would eat any future `lms-serial-…`
// test's live directories. Fixed on both sides, because fixing only the collision leaves the class.
const created: string[] = [];
function tmp() {
  const dir = fs.mkdtempSync(path.join(os.homedir(), 'lms-serial-'));
  created.push(dir);
  return dir;
}
afterEach(() => {
  while (created.length) fs.rmSync(created.pop()!, { recursive: true, force: true });
});

describe('claimVideoSlot — desired serial (local adapter)', () => {
  // Row 9 — the whole point. A receiver that is told which serial the sender used must be able to
  // reproduce it, or the `base` it derives cannot match the `summaryMd` key it was handed.
  it('adopts the desired serial when no sibling holds it', async () => {
    const p = localPrincipal(tmp());
    await store.claimVideoSlot(p, 'vid00000001');            // takes serial 1
    await store.claimVideoSlot(p, 'vid00000002');            // takes serial 2

    const slot = await store.claimVideoSlot(p, 'vid00000009', 9);

    expect(slot.serialNumber).toBe(9);
    const idx = await store.readIndex(p);
    expect(idx.videos.find((v) => v.id === 'vid00000009')?.serialNumber).toBe(9);
  });

  // Row 9 — adoption must not disturb the allocator. A later no-preference claim allocates from the
  // high-water mark, so it cannot collide with the serial that was just adopted.
  it('advances the high-water mark so a later allocation cannot collide', async () => {
    const p = localPrincipal(tmp());
    await store.claimVideoSlot(p, 'vid00000001', 9);

    const next = await store.claimVideoSlot(p, 'vid00000002');

    expect(next.serialNumber).toBe(10);
  });

  // Row 10 — the adapter does NOT resolve a collision by silently substituting. It allocates a fresh
  // serial and reports it; deciding what that means (abort the video) is the caller's job, and the
  // caller can only make that decision because the returned value is the truth.
  it('does not adopt an occupied serial — allocates from the high-water mark instead', async () => {
    const p = localPrincipal(tmp());
    await store.claimVideoSlot(p, 'vid00000001');            // holds serial 1

    const slot = await store.claimVideoSlot(p, 'vid00000002', 1);

    expect(slot.serialNumber).toBe(2);
    const idx = await store.readIndex(p);
    expect(idx.videos.find((v) => v.id === 'vid00000001')?.serialNumber).toBe(1); // untouched
  });

  // Row 11 — omitting the argument keeps today's behavior exactly. A legacy sender row with no
  // serialNumber must not become an error.
  it('allocates max+1 when no serial is desired', async () => {
    const p = localPrincipal(tmp());
    await store.claimVideoSlot(p, 'vid00000001', 5);

    expect((await store.claimVideoSlot(p, 'vid00000002')).serialNumber).toBe(6);
  });

  // Row 12 — the persisted value is the truth. Today this returns a freshly COMPUTED serial the row
  // does not have, AND destroys the row: indexStore.upsertVideo is a full replacement, so the stub
  // `{id, serialNumber}` overwrites title, summaryMd, ratings — everything.
  it('returns the PERSISTED serial for a video already in the index, and never rewrites the row', async () => {
    const p = localPrincipal(tmp());
    await store.claimVideoSlot(p, 'vid00000001', 3);
    await store.upsertVideo(p, {
      id: 'vid00000001', serialNumber: 3, title: 'Kept', summaryMd: '003_kept.md',
    } as Video);

    const again = await store.claimVideoSlot(p, 'vid00000001', 8);

    expect(again.serialNumber).toBe(3);
    const rec = (await store.readIndex(p)).videos.find((v) => v.id === 'vid00000001');
    expect(rec?.title).toBe('Kept');
    expect(rec?.summaryMd).toBe('003_kept.md');
  });

  // Row 13 — reject, do not silently fall back. A caller that computed a nonsense serial has a bug;
  // quietly allocating a different one hands it a receiver row whose base does not match its key,
  // which is the exact failure this whole slice removes.
  it.each([0, -1, 1.5, NaN, Infinity])('rejects the invalid desired serial %p before writing anything', async (bad) => {
    const p = localPrincipal(tmp());

    await expect(store.claimVideoSlot(p, 'vid00000001', bad)).rejects.toThrow(/serial/i);
    expect((await store.readIndex(p)).videos).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Supabase adapter — the argument must actually REACH the RPC, and validation must happen before
// any round-trip. The RPC's own resolution (under the playlist row-lock, rows 12/14) is asserted in
// tests/integration/metadata-store.test.ts against a live stack; here we assert the wiring.
// ---------------------------------------------------------------------------
describe('claimVideoSlot — desired serial (Supabase adapter wiring)', () => {
  function mockClient(rpcRow: { position: number; serial_number: number }) {
    const rpcCalls: { fn: string; args: Record<string, unknown> }[] = [];
    const client = {
      rpc: async (fn: string, args: Record<string, unknown>) => {
        rpcCalls.push({ fn, args });
        if (fn === 'claim_video_slot') return { data: [rpcRow], error: null };
        return { data: null, error: null };
      },
      from: () => ({
        select: () => ({
          eq: () => ({ maybeSingle: async () => ({ data: { id: 'pl-uuid' }, error: null }) }),
        }),
      }),
    } as any;
    return { client, rpcCalls };
  }

  const P = { id: 'owner-uuid', indexKey: 'PLxxxxxxxx' };

  it('forwards the desired serial to the RPC', async () => {
    const { client, rpcCalls } = mockClient({ position: 0, serial_number: 9 });
    const s = new SupabaseMetadataStore(client);

    const slot = await s.claimVideoSlot(P, 'vid00000009', 9);

    expect(slot.serialNumber).toBe(9);
    expect(rpcCalls.find((c) => c.fn === 'claim_video_slot')?.args).toMatchObject({
      p_video_id: 'vid00000009', p_desired_serial: 9,
    });
  });

  // Absence is meaningful: null tells the RPC "no preference". It must not become 0 or undefined,
  // either of which changes what the SQL does.
  it('sends p_desired_serial: null when no serial is desired', async () => {
    const { client, rpcCalls } = mockClient({ position: 0, serial_number: 1 });
    const s = new SupabaseMetadataStore(client);

    await s.claimVideoSlot(P, 'vid00000001');

    expect(rpcCalls.find((c) => c.fn === 'claim_video_slot')?.args).toMatchObject({ p_desired_serial: null });
  });

  it('rejects an invalid desired serial WITHOUT calling the RPC', async () => {
    const { client, rpcCalls } = mockClient({ position: 0, serial_number: 1 });
    const s = new SupabaseMetadataStore(client);

    await expect(s.claimVideoSlot(P, 'vid00000001', 0)).rejects.toThrow(/serial/i);
    expect(rpcCalls.filter((c) => c.fn === 'claim_video_slot')).toHaveLength(0);
  });
});
