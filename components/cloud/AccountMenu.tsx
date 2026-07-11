'use client';

/**
 * Stage 2a T14: cloud shell account menu. Renders the signed-in owner's email as a trigger
 * button; clicking opens a dropdown with the email (header) and a "Sign out" item.
 *
 * Dismissal (spec §10 — all three paths, one test block each in account-menu.test.tsx):
 *   (a) click outside the menu → closes, no action
 *   (b) Escape key → closes, no action
 *   (c) selecting "Sign out" → runs the sign-out action, then closes
 *
 * Sign-out uses the browser Supabase client (lib/supabase/client.ts) directly — this is a
 * client component, not a server action — then redirects to /login via useRouter().replace().
 */
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

export interface AccountMenuProps {
  email: string;
}

export default function AccountMenu({ email }: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Dismissal (a): click outside the menu box closes it.
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  // Dismissal (b): Escape key closes it.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  // Dismissal (c): selecting "Sign out" runs the action, then closes.
  async function handleSignOut() {
    setOpen(false);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace('/login');
  }

  return (
    <div ref={boxRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-1 rounded px-2 py-1.5 text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] hover:text-[var(--text-primary)]"
      >
        <span className="max-w-[16rem] truncate">{email}</span>
        <span aria-hidden="true">▾</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-20 mt-1 w-56 rounded-md border border-[var(--border)] bg-[var(--surface-overlay)] py-1 shadow-xl"
        >
          <div className="truncate border-b border-[var(--border)] px-4 py-2 text-sm text-[var(--text-secondary)]">
            {email}
          </div>
          <button
            type="button"
            role="menuitem"
            onClick={handleSignOut}
            className="block w-full px-4 py-2 text-left text-sm text-[var(--text-primary)] hover:bg-[var(--surface-raised)]"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
