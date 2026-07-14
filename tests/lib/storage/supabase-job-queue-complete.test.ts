import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import type { SupabaseClient } from '@supabase/supabase-js';

/**
 * BUG-1 regression (local-validation-findings.md). A job handler that returns nothing yields
 * `result === undefined`. supabase-js sends rpc params as `JSON.stringify(params)`, which DROPS
 * undefined-valued keys — so `p_result: undefined` vanishes from the request body and PostgREST
 * receives only 3 params, cannot resolve the 4-arg `complete_job(p_job_id, p_worker_id,
 * p_lease_token, p_result)`, and returns PGRST202. The whole worker pipeline then fails at the
 * finish line despite doing all the work. `complete()` must send a JSON-preservable `p_result`.
 */
describe('SupabaseJobQueue.complete — p_result survives JSON serialization', () => {
  function fakeClient() {
    const calls: Array<{ fn: string; params: Record<string, unknown> }> = [];
    const client = {
      rpc: (fn: string, params: Record<string, unknown>) => {
        calls.push({ fn, params });
        return Promise.resolve({ data: true, error: null });
      },
    } as unknown as SupabaseClient;
    return { client, calls };
  }

  it('sends p_result as a value that survives JSON.stringify when the handler returned undefined', async () => {
    const { client, calls } = fakeClient();
    const q = new SupabaseJobQueue(client);

    await q.complete('job-1', 'w1', 'lease-1', undefined);

    expect(calls[0].fn).toBe('complete_job');
    // Faithful to supabase-js: it POSTs JSON.stringify(params); undefined-valued keys are dropped.
    // p_result must still be present in the serialized body, or PostgREST 404s the 4-arg function.
    const body = JSON.parse(JSON.stringify(calls[0].params));
    expect('p_result' in body).toBe(true);
    expect(body.p_result).toBeNull();
  });

  it('passes a real handler result through unchanged', async () => {
    const { client, calls } = fakeClient();
    const q = new SupabaseJobQueue(client);

    await q.complete('job-2', 'w1', 'lease-2', { ok: true });

    const body = JSON.parse(JSON.stringify(calls[0].params));
    expect(body.p_result).toEqual({ ok: true });
  });
});
