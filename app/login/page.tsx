'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { isLocalSupabaseUrl } from '@/lib/supabase/is-local-url';

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  // Client-side, cosmetic discovery link. The real gate is server-side (/dev-login → 404 in
  // prod); if this ever showed in prod it would merely point at a 404.
  const showDevLink = isLocalSupabaseUrl(process.env.NEXT_PUBLIC_SUPABASE_URL);

  async function handleSignIn() {
    setError(null);
    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback?next=/` },
    });
    if (signInError) {
      setError(signInError.message ?? 'Sign-in failed. Please try again.');
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm text-center">
        <h1 className="text-2xl font-semibold text-zinc-50">YouTube Playlist Summaries</h1>
        <p className="mt-2 text-sm text-zinc-400">Sign in to view and manage your playlist summaries.</p>
        <button
          type="button"
          onClick={handleSignIn}
          className="mt-8 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
        >
          Continue with Google
        </button>
        {error && (
          <p role="alert" className="mt-4 text-sm text-red-400">
            {error}
          </p>
        )}
        {showDevLink && (
          <a href="/dev-login" className="mt-6 inline-block text-xs text-zinc-500 underline hover:text-zinc-300">
            Local dev sign-in
          </a>
        )}
      </div>
    </div>
  );
}
