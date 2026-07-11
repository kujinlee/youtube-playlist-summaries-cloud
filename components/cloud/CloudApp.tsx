'use client';

/**
 * Stage 2a T12: cloud shell skeleton. `app/page.tsx` renders this in cloud mode
 * (`STORAGE_BACKEND=supabase`) with the RSC-read session. Fleshed out in T13–T15
 * (sidebar/library, ScopeProvider wiring, playlist detail view).
 */
export interface CloudAppProps {
  session: { userId: string; email: string } | null;
}

export default function CloudApp({ session }: CloudAppProps) {
  return (
    <main className="min-h-screen bg-[var(--surface-base)] text-[var(--text-primary)]">
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--surface-raised)]">
        <h1 className="text-lg font-semibold">YouTube Playlist Summaries</h1>
        <span className="text-sm text-[var(--text-secondary)]">
          {session ? session.email : 'Not signed in'}
        </span>
      </header>
      <section aria-label="Cloud library" className="px-6 py-12 text-center text-[var(--text-muted)]">
        <p>Cloud library coming soon.</p>
      </section>
    </main>
  );
}
