'use client';

/**
 * playlist-sidebar-ux T10: full hard-delete confirm modal. Modeled on NewPlaylistModal
 * (focus trap, Escape-to-close, returnFocus, submit guard via a ref) — see
 * components/cloud/NewPlaylistModal.tsx and docs/superpowers/specs/
 * 2026-07-13-playlist-sidebar-ux-design.md §B7 (Overlay Dismissal table).
 *
 * All four dismissal paths (Cancel, Escape, backdrop click, ✕) are gated on `!deleting` —
 * mid-delete they are no-ops so the user can't dismiss (and lose track of) an in-flight
 * irreversible delete. The parent owns "is this dialog open" state and unmounts this
 * component from `onClose`/`onDeleted`; this component does not close itself.
 */
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { deletePlaylist, UnauthorizedError } from '@/lib/client/api';

export interface DeletePlaylistDialogProps {
  playlistId: string;
  playlistTitle: string;
  onClose: () => void;
  onDeleted: () => void;
}

export function DeletePlaylistDialog({ playlistId, playlistTitle, onClose, onDeleted }: DeletePlaylistDialogProps) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const deletingRef = useRef(false);

  useEffect(() => {
    returnFocusRef.current = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    return () => returnFocusRef.current?.focus();
  }, []);

  const guardedClose = () => { if (!deleting) onClose(); };

  const focusables = () =>
    Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], textarea, select') ?? []);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') { guardedClose(); return; }
    if (e.key !== 'Tab') return;
    const els = focusables();
    if (els.length === 0) return;
    const first = els[0];
    const last = els[els.length - 1];
    const active = document.activeElement as HTMLElement;
    if (e.shiftKey && active === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
  }

  async function handleDelete() {
    if (deletingRef.current) return;
    deletingRef.current = true;
    setDeleting(true);
    setError(null);
    try {
      await deletePlaylist(playlistId);
      onDeleted();
    } catch (err) {
      if (err instanceof UnauthorizedError) { router.replace('/login'); return; }
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.');
      deletingRef.current = false;
      setDeleting(false);
    }
  }

  return (
    <div
      data-testid="delete-modal-backdrop"
      onClick={guardedClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,.4)]"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Delete playlist ${playlistTitle}`}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
        className="w-[min(90vw,32rem)] rounded border border-[var(--border)] bg-[var(--surface-base)] p-4 text-[var(--text-primary)] shadow-lg"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-medium">Delete playlist</h2>
          <button
            type="button"
            aria-label="Close"
            onClick={guardedClose}
            disabled={deleting}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-50"
          >
            ✕
          </button>
        </div>
        <p className="text-sm text-[var(--text-primary)]">
          Delete &quot;{playlistTitle}&quot;? This permanently removes the playlist, all its
          summaries, PDFs, and any share links. This cannot be undone.
        </p>
        {error && (
          <p role="alert" className="mt-2 text-sm text-[var(--danger)]">
            <span aria-hidden="true">⚠ </span>
            {error}
          </p>
        )}
        <div className="mt-3 flex justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={guardedClose}
            disabled={deleting}
            className="rounded border border-[var(--border)] px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="rounded border border-[var(--danger)] bg-[var(--danger)] px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            {deleting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
