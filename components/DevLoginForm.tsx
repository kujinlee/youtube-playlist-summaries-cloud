'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { hardNavigate } from '@/lib/navigate';

export function DevLoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    if (signInError) {
      setError(signInError.message ?? 'Sign-in failed. Please try again.');
      setPending(false);
      return;
    }
    // Hard navigation (full round-trip) so middleware/server read the freshly-written
    // session cookie on the next request — a soft nav may not surface it (round-1 M1).
    hardNavigate('/');
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm text-center">
        <h1 className="text-2xl font-semibold text-zinc-50">Local dev sign-in</h1>
        <p className="mt-2 text-sm text-zinc-400">Email/password login — local Supabase only.</p>

        <label htmlFor="dev-email" className="sr-only">Email</label>
        <input
          id="dev-email" type="email" autoComplete="username" required value={email}
          onChange={(e) => setEmail(e.target.value)} placeholder="Email"
          className="mt-6 w-full rounded-md bg-zinc-900 px-4 py-2 text-sm text-zinc-50 outline-none ring-1 ring-zinc-700 focus:ring-blue-500"
        />
        <label htmlFor="dev-password" className="sr-only">Password</label>
        <input
          id="dev-password" type="password" autoComplete="current-password" required value={password}
          onChange={(e) => setPassword(e.target.value)} placeholder="Password"
          className="mt-3 w-full rounded-md bg-zinc-900 px-4 py-2 text-sm text-zinc-50 outline-none ring-1 ring-zinc-700 focus:ring-blue-500"
        />
        <button
          type="submit" disabled={pending}
          className="mt-6 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          {pending ? 'Signing in…' : 'Sign in'}
        </button>
        {error && (
          <p role="alert" className="mt-4 text-sm text-red-400">{error}</p>
        )}
      </form>
    </div>
  );
}
