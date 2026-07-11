'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);

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
      </div>
    </div>
  );
}
