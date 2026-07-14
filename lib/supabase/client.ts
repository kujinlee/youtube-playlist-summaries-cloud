'use client';
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  // These MUST be referenced statically (not via a `process.env[name]` helper):
  // Next.js only inlines NEXT_PUBLIC_* into the client bundle for literal
  // `process.env.NEXT_PUBLIC_*` references. A computed key resolves to undefined
  // in the browser. Server-side clients use getSupabaseEnv()/process.env[name],
  // which is correct there because process.env is populated at runtime.
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url) throw new Error('Missing required env var: NEXT_PUBLIC_SUPABASE_URL');
  if (!anonKey) throw new Error('Missing required env var: NEXT_PUBLIC_SUPABASE_ANON_KEY');
  return createBrowserClient(url, anonKey);
}
