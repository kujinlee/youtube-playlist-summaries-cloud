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
