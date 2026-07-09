import { createClient, SupabaseClient } from '@supabase/supabase-js';

const url = () => process.env.NEXT_PUBLIC_SUPABASE_URL!;
const anon = () => process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const service = () => process.env.SUPABASE_SERVICE_ROLE_KEY!;

export function adminClient(): SupabaseClient {
  return createClient(url(), service(), { auth: { autoRefreshToken: false, persistSession: false } });
}

let seq = 0;
export async function newUser(): Promise<{ user: { id: string }; email: string; password: string }> {
  const email = `u${Date.now()}-${seq++}@example.test`;
  const password = 'test-password-123';
  const admin = adminClient();
  const { data, error } = await admin.auth.admin.createUser({ email, password, email_confirm: true });
  if (error || !data.user) throw error ?? new Error('createUser failed');
  return { user: { id: data.user.id }, email, password };
}

/** RLS-scoped client authenticated as a real user (anon key + user JWT). */
export async function signInAs(email: string, password: string): Promise<{ client: SupabaseClient; userId: string }> {
  const client = createClient(url(), anon(), { auth: { autoRefreshToken: false, persistSession: false } });
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error || !data.user) throw error ?? new Error('signIn failed');
  return { client, userId: data.user.id };
}

export async function anonSession(): Promise<{ client: SupabaseClient; userId: string }> {
  const client = createClient(url(), anon(), { auth: { autoRefreshToken: false, persistSession: false } });
  const { data, error } = await client.auth.signInAnonymously();
  if (error || !data.user) throw error ?? new Error('anon sign-in failed');
  return { client, userId: data.user.id };
}

/**
 * T13: `enqueue_job` (T2) now enforces PJ001 (monthly quota) / PJ002 (daily $ cap) / PJ003
 * (duration) INSIDE the RPC — checks the pre-T2 6-arg session-client RPC never ran. Integration
 * files migrated in T13 call the real `enqueue_job`/`SupabaseEnqueuer` a nontrivial number of
 * times and must not spuriously trip these guardrails just because an earlier-run file (e.g.
 * `cost-guardrails.test.ts`) left the singleton `guardrail_config`/`quota_allowance` rows pinned
 * to tight values. Call this at the top of any such file (`beforeAll`) to pin generous headroom
 * regardless of cross-file execution order.
 */
export async function ensureGuardrailHeadroom(svc: SupabaseClient): Promise<void> {
  await svc.from('guardrail_config').update({
    daily_cap_cents: 1_000_000, max_duration_seconds: 1800, summary_est_cents: 150,
  }).eq('id', true);
  await svc.from('quota_allowance').update({ monthly: 100_000 }).match({ is_anonymous: false, kind: 'summary' });
  await svc.from('quota_allowance').update({ monthly: 100_000 }).match({ is_anonymous: true, kind: 'summary' });
}
