'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createIngest, ingestErrorMessage, IngestError, UnauthorizedError, type IngestResult } from '@/lib/client/api';

export function NewPlaylistModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: (result: IngestResult) => void }) {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    returnFocusRef.current = document.activeElement as HTMLElement | null;
    inputRef.current?.focus();
    return () => returnFocusRef.current?.focus();
  }, []);

  const guardedClose = () => { if (!submitting) onClose(); };

  const focusables = () =>
    Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), [href], textarea, select') ?? []);

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

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const result = await createIngest(url);
      if (result.playlistId === null) {
        setError('No videos could be ingested from that playlist.');
        submittingRef.current = false;
        setSubmitting(false);
        return;
      }
      onSuccess(result);
    } catch (err) {
      if (err instanceof UnauthorizedError) { router.replace('/login'); return; }
      setError(err instanceof IngestError ? ingestErrorMessage(err) : 'Something went wrong. Try again.');
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <div data-testid="modal-backdrop" onClick={guardedClose} className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,.4)]">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="New playlist"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
        className="w-[min(90vw,32rem)] rounded border border-[var(--border)] bg-[var(--surface-base)] p-4 text-[var(--text-primary)] shadow-lg"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-medium">New playlist</h2>
          <button type="button" aria-label="Close" onClick={guardedClose} disabled={submitting} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-50">✕</button>
        </div>
        <form onSubmit={submit}>
          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/playlist?list=…"
            className="w-full rounded border border-[var(--border)] bg-[var(--surface-base)] px-2 py-1.5 text-sm"
          />
          {error && (
            <p role="alert" className="mt-2 text-sm text-[var(--danger)]">
              <span aria-hidden="true">⚠ </span>
              {error}
            </p>
          )}
          <div className="mt-3 flex justify-end gap-2">
            <button type="button" onClick={guardedClose} disabled={submitting} className="rounded border border-[var(--border)] px-3 py-1.5 text-sm disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={submitting} className="rounded border border-[var(--accent)] bg-[var(--accent)] px-3 py-1.5 text-sm text-[var(--surface-base)] disabled:opacity-50">
              {submitting ? 'Adding…' : 'Add ▸'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
