'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getJobStatus, UnauthorizedError } from '@/lib/client/api';
import { pollUntilTerminal, type Rollup } from '@/lib/job-queue/poll-client';

const POLL_INTERVAL_MS = 2000;
const POLL_MAX_INTERVAL_MS = 10000;

type BannerState =
  | { kind: 'hidden' }
  | { kind: 'progress'; completed: number; total: number }
  | { kind: 'done'; total: number }
  | { kind: 'mixed'; completed: number; failed: number }
  | { kind: 'gaveup' };

const doneCount = (r: Rollup) => r.completed + r.failed + r.dead_letter;

export function IngestProgressBanner({ playlistId, onProgress }: { playlistId: string; onProgress?: () => void }) {
  const router = useRouter();
  const [state, setState] = useState<BannerState>({ kind: 'hidden' });
  const [dismissed, setDismissed] = useState(false);
  // Hold the latest onProgress in a ref so a poll advance always calls the CURRENT parent
  // callback — the effect below captures only playlistId (R2 Medium). Assign during render,
  // not in a passive effect, so no poll callback can fire against a stale value (R3 Medium).
  const onProgressRef = useRef(onProgress);
  onProgressRef.current = onProgress;

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    let lastFired = -1;
    setState({ kind: 'hidden' });
    setDismissed(false);

    const fireIfAdvanced = (r: Rollup) => {
      const d = doneCount(r);
      if (d > lastFired) { lastFired = d; try { onProgressRef.current?.(); } catch { /* isolate */ } }
    };

    (async () => {
      // Probe once: decide visibility + surface auth before entering the poll loop.
      let first;
      try {
        first = await getJobStatus(playlistId);
      } catch (err) {
        if (err instanceof UnauthorizedError) { if (!cancelled) router.replace('/login'); return; }
        return; // transient probe failure, never showed → stay hidden
      }
      if (cancelled) return;
      if (first.rollup.total === 0 || first.rollup.terminal) return; // nothing to track
      setState({ kind: 'progress', completed: first.rollup.completed, total: first.rollup.total });
      lastFired = doneCount(first.rollup);

      const result = await pollUntilTerminal(
        () => getJobStatus(playlistId).then((r) => r.jobs),
        {
          intervalMs: POLL_INTERVAL_MS,
          maxIntervalMs: POLL_MAX_INTERVAL_MS,
          maxConsecutiveErrors: 5,
          signal: controller.signal,
          isFatal: (e) => e instanceof UnauthorizedError,
          onProgress: ({ rollup }) => {
            if (cancelled || rollup.terminal) return;
            setState({ kind: 'progress', completed: rollup.completed, total: rollup.total });
            fireIfAdvanced(rollup);
          },
        },
      );
      if (cancelled || 'aborted' in result) return;
      if ('failed' in result) {
        if (result.fatal) { router.replace('/login'); return; }
        setState({ kind: 'gaveup' });
        return;
      }
      if ('timedOut' in result) { setState({ kind: 'gaveup' }); return; } // 10-min cap → give-up (spec §6)
      const r = result.rollup; // done (all rows terminal)
      fireIfAdvanced(r);
      const failed = r.failed + r.dead_letter;
      setState(failed > 0 ? { kind: 'mixed', completed: r.completed, failed } : { kind: 'done', total: r.total });
    })();

    return () => { cancelled = true; controller.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playlistId]);

  if (dismissed || state.kind === 'hidden') return null;

  const dismiss = (
    <button type="button" aria-label="Dismiss progress" onClick={() => setDismissed(true)} className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)]">✕</button>
  );

  if (state.kind === 'progress') {
    const { completed, total } = state;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    return (
      <div className="flex items-center gap-3 border-b border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-[var(--text-primary)]">
        <span aria-hidden="true">⟳</span>
        <span>Ingesting {completed} of {total}…</span>
        <div role="progressbar" aria-valuenow={completed} aria-valuemin={0} aria-valuemax={total} className="h-1.5 flex-1 rounded bg-[var(--border)]">
          <div className="h-full rounded bg-[var(--accent)]" style={{ width: `${pct}%` }} />
        </div>
        {dismiss}
      </div>
    );
  }

  const text =
    state.kind === 'done' ? `✓ Ingest complete — ${state.total} videos`
    : state.kind === 'mixed' ? `⚠ ${state.completed} done · ${state.failed} failed`
    : '⚠ Lost connection to progress updates — reload to retry.';
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-[var(--text-primary)]">
      <span>{text}</span>
      {dismiss}
    </div>
  );
}
