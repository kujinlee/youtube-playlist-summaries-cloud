import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import type { Principal } from '@/lib/storage/principal';

const P: Principal = { id: 'o1', indexKey: 'pk1' };

function fakeClient(over: Partial<{ upload: any; download: any; remove: any; move: any }> = {}) {
  const bucket = {
    upload: over.upload ?? jest.fn().mockResolvedValue({ error: null }),
    download: over.download ?? jest.fn().mockResolvedValue({ data: null, error: { message: 'not found' } }),
    remove: over.remove ?? jest.fn().mockResolvedValue({ error: null }),
    move: over.move ?? jest.fn().mockResolvedValue({ error: null }),
  };
  return { bucket, client: { storage: { from: () => bucket } } as any };
}

it('putStaged uses a uuid-prefixed temp key (per-attempt-unique)', async () => {
  const { bucket, client } = fakeClient();
  const store = new SupabaseBlobStore(client, 'artifacts');
  const ref = await store.putStaged(P, 'models/a.json', Buffer.from('x'), 'application/json');
  expect(ref.tempKey).toMatch(/^_staging\/[0-9a-f-]{36}\/models\/a\.json$/);
  expect(ref.tempKey).not.toBe('_staging/models/a.json'); // NOT the old deterministic key
});

it('promote treats destination-already-exists as success (final present, move error swallowed)', async () => {
  const download = jest.fn().mockResolvedValue({ data: { arrayBuffer: async () => new ArrayBuffer(1) }, error: null }); // final exists
  const move = jest.fn().mockResolvedValue({ error: { message: 'The resource already exists' } });
  const remove = jest.fn().mockResolvedValue({ error: null });
  const { client } = fakeClient({ download, move, remove });
  const store = new SupabaseBlobStore(client, 'artifacts');
  await expect(store.promote({ principal: P, tempKey: '_staging/u/models/a.json', finalKey: 'models/a.json' })).resolves.toBeUndefined();
});

it('promote rethrows when move fails AND the final is genuinely absent', async () => {
  const download = jest.fn().mockResolvedValue({ data: null, error: { message: 'not found' } }); // final absent
  const move = jest.fn().mockResolvedValue({ error: { message: 'network' } });
  const { client } = fakeClient({ download, move });
  const store = new SupabaseBlobStore(client, 'artifacts');
  await expect(store.promote({ principal: P, tempKey: '_staging/u/models/a.json', finalKey: 'models/a.json' })).rejects.toBeTruthy();
});

it('promote resolves on a concurrent worker-retry race: final ABSENT on precheck, move FAILS, final PRESENT on recheck (F5)', async () => {
  // The real race the post-error recheck exists for (WORKER MD path — the only staged→promote consumer):
  // precheck sees no final (so we attempt the move), a concurrent promoter — a re-dispatched/retried
  // summary job promoting the same MD key — wins (move → destination-exists/source-missing error), and the
  // recheck now sees the final present → promote() must RESOLVE, not throw. A buggy impl with only the precheck
  // and no post-error recheck would throw here (the earlier two tests both pass without the recheck).
  const download = jest.fn()
    .mockResolvedValueOnce({ data: null, error: { message: 'not found' } })                       // precheck: absent
    .mockResolvedValue({ data: { arrayBuffer: async () => new ArrayBuffer(1) }, error: null });   // recheck: present
  const move = jest.fn().mockResolvedValue({ error: { message: 'The resource already exists' } }); // racer won
  const remove = jest.fn().mockResolvedValue({ error: null });
  const { client } = fakeClient({ download, move, remove });
  const store = new SupabaseBlobStore(client, 'artifacts');
  await expect(store.promote({ principal: P, tempKey: '_staging/u/models/a.json', finalKey: 'models/a.json' })).resolves.toBeUndefined();
  expect(move).toHaveBeenCalledTimes(1); // attempted the move, then swallowed the race error after the recheck
});
