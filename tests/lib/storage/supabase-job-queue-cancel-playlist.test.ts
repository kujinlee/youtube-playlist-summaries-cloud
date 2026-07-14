import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import type { SupabaseClient } from '@supabase/supabase-js';

/**
 * Task 8: requestCancelPlaylist — typed wrapper over the `request_cancel_playlist_jobs`
 * RPC (0019, Task 6). The RPC self-guards on owner_id = auth.uid() server-side; this test
 * only asserts the wrapper's RPC name/args/return shape (matches requestCancel's pattern
 * in supabase-job-queue.ts). Owner-guard/cascade behavior is covered by the integration
 * suite (tests/integration/cancel-playlist-jobs.test.ts, delete-playlist-store.test.ts).
 */
describe('SupabaseJobQueue.requestCancelPlaylist', () => {
  function fakeClient(data: unknown = 3, error: unknown = null) {
    const calls: Array<{ fn: string; params: Record<string, unknown> }> = [];
    const client = {
      rpc: (fn: string, params: Record<string, unknown>) => {
        calls.push({ fn, params });
        return Promise.resolve({ data, error });
      },
    } as unknown as SupabaseClient;
    return { client, calls };
  }

  it('calls request_cancel_playlist_jobs with p_playlist_id and returns { cancelled }', async () => {
    const { client, calls } = fakeClient(3);
    const q = new SupabaseJobQueue(client);

    const result = await q.requestCancelPlaylist('pl-id-1');

    expect(calls).toHaveLength(1);
    expect(calls[0].fn).toBe('request_cancel_playlist_jobs');
    expect(calls[0].params).toEqual({ p_playlist_id: 'pl-id-1' });
    expect(result).toEqual({ cancelled: 3 });
  });

  it('coalesces a null RPC result to { cancelled: 0 }', async () => {
    const { client } = fakeClient(null);
    const q = new SupabaseJobQueue(client);

    const result = await q.requestCancelPlaylist('pl-id-2');

    expect(result).toEqual({ cancelled: 0 });
  });

  it('throws on RPC error', async () => {
    const { client } = fakeClient(null, new Error('rpc failed'));
    const q = new SupabaseJobQueue(client);

    await expect(q.requestCancelPlaylist('pl-id-3')).rejects.toThrow('rpc failed');
  });
});
