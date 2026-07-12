'use client';

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useRouter } from 'next/navigation';
import { createShare, revokeShare, UnauthorizedError, type CreateShareResult, type ShareTtl } from '@/lib/client/api';

interface ShareDialogProps {
  playlistId: string;
  videoId: string;
  videoTitle: string;
  onClose: () => void;
}

export default function ShareDialog({ playlistId, videoId, videoTitle, onClose }: ShareDialogProps) {
  const router = useRouter();
  const [ttl, setTtl] = useState<ShareTtl>(30);
  const [share, setShare] = useState<CreateShareResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const ttlGroupRef = useRef<HTMLInputElement>(null);
  const inFlightRef = useRef(false);
  const copiedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    ttlGroupRef.current?.focus();
  }, []);

  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current) clearTimeout(copiedTimeoutRef.current);
    };
  }, []);

  const guardedClose = () => { if (!inFlightRef.current && !busy) onClose(); };

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

  async function handleCreate() {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await createShare(playlistId, videoId, ttl);
      setShare(result);
    } catch (err) {
      if (err instanceof UnauthorizedError) { router.replace('/login'); return; }
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.');
    } finally {
      inFlightRef.current = false;
      setBusy(false);
    }
  }

  async function handleRevoke() {
    if (inFlightRef.current || !share) return;
    inFlightRef.current = true;
    setBusy(true);
    setError(null);
    try {
      await revokeShare(share.id);
      setShare(null);
    } catch (err) {
      if (err instanceof UnauthorizedError) { router.replace('/login'); return; }
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.');
    } finally {
      inFlightRef.current = false;
      setBusy(false);
    }
  }

  async function handleCopy() {
    if (!share) return;
    const fullUrl = window.location.origin + share.url;
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      if (copiedTimeoutRef.current) clearTimeout(copiedTimeoutRef.current);
      copiedTimeoutRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      inputRef.current?.select();
    }
  }

  const fullUrl = share ? window.location.origin + share.url : '';

  // This is a fixed full-screen overlay. It is rendered from inside a <tbody> (VideoRow),
  // where a bare <div> is invalid DOM (hydration error). Portal it to <body> so it escapes
  // the table and nests validly.
  if (typeof document === 'undefined') return null;

  return createPortal(
    <div
      data-testid="share-dialog-backdrop"
      onClick={guardedClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,.4)]"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Share ${videoTitle}`}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
        className="w-[min(90vw,32rem)] rounded border border-[var(--border)] bg-[var(--surface-base)] p-4 text-[var(--text-primary)] shadow-lg"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-medium">Share &ldquo;{videoTitle}&rdquo;</h2>
          <button type="button" aria-label="Close" onClick={guardedClose} disabled={busy} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-50">✕</button>
        </div>

        <fieldset className="mb-3">
          <legend className="mb-1 text-sm text-[var(--text-muted)]">Link expires</legend>
          <div className="flex gap-3">
            <label className="flex items-center gap-1 text-sm">
              <input
                type="radio"
                name="share-ttl"
                value="7"
                checked={ttl === 7}
                onChange={() => setTtl(7)}
              />
              7d
            </label>
            <label className="flex items-center gap-1 text-sm">
              <input
                ref={ttlGroupRef}
                type="radio"
                name="share-ttl"
                value="30"
                checked={ttl === 30}
                onChange={() => setTtl(30)}
              />
              30d
            </label>
            <label className="flex items-center gap-1 text-sm">
              <input
                type="radio"
                name="share-ttl"
                value="never"
                checked={ttl === 'never'}
                onChange={() => setTtl('never')}
              />
              Never
            </label>
          </div>
        </fieldset>

        <div className="mb-2 flex gap-2">
          <input
            ref={inputRef}
            type="text"
            readOnly
            value={fullUrl}
            placeholder="No link yet"
            className="flex-1 rounded border border-[var(--border)] bg-[var(--surface-overlay)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
          />
          <button
            type="button"
            onClick={handleCopy}
            disabled={!share}
            className="rounded border border-[var(--border)] px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Copy
          </button>
        </div>

        <div aria-live="polite" className="mb-2 h-4 text-sm text-[var(--text-muted)]">
          {copied ? 'Copied ✓' : ''}
        </div>

        {error && (
          <p role="alert" className="mt-1 mb-2 text-sm text-[var(--danger)]">
            <span aria-hidden="true">⚠ </span>
            {error}
          </p>
        )}

        <div className="mt-3 flex justify-end gap-2">
          <button
            type="button"
            onClick={handleRevoke}
            disabled={!share || busy}
            className="rounded border border-[var(--border)] px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Revoke
          </button>
          <button
            type="button"
            onClick={handleCreate}
            disabled={busy}
            className="rounded border border-[var(--accent)] bg-[var(--accent)] px-3 py-1.5 text-sm text-[var(--surface-base)] disabled:opacity-50"
          >
            {busy ? 'Working…' : 'Create link'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
