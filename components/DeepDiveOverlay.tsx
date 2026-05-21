'use client';

import { useEffect, useRef, useState } from 'react';
import type { ProgressEvent } from '@/types';

interface DeepDiveOverlayProps {
  videoId: string;
  jobId: string;
  onClose: () => void;
}

type OverlayState =
  | { status: 'running'; progress: number; step: string }
  | { status: 'done' }
  | { status: 'error'; message: string; log: string };

const LOG_PANEL_ID = 'deep-dive-log-panel';

export default function DeepDiveOverlay({ videoId, jobId, onClose }: DeepDiveOverlayProps) {
  const [state, setState] = useState<OverlayState>({ status: 'running', progress: 0, step: '' });
  const [logsOpen, setLogsOpen] = useState(false);
  const priorFocusRef = useRef<Element | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  // Capture focus target for restoration on close
  useEffect(() => {
    priorFocusRef.current = document.activeElement;
    const firstFocusable = dialogRef.current?.querySelector<HTMLElement>('button, [tabindex]');
    firstFocusable?.focus();
    return () => {
      (priorFocusRef.current as HTMLElement | null)?.focus();
    };
  }, []);

  useEffect(() => {
    // Reset UI state for each new job
    setState({ status: 'running', progress: 0, step: '' });
    setLogsOpen(false);

    const url = `/api/videos/${encodeURIComponent(videoId)}/deep-dive/stream?jobId=${encodeURIComponent(jobId)}`;
    const es = new EventSource(url);
    let terminal = false;

    es.onmessage = (event: MessageEvent) => {
      if (terminal) return;

      let data: ProgressEvent;
      try {
        data = JSON.parse(event.data) as ProgressEvent;
      } catch {
        return;
      }

      if (data.type === 'step') {
        const progress =
          data.current != null && data.total != null
            ? Math.min(100, Math.round((data.current / data.total) * 100))
            : 0;
        setState({ status: 'running', progress, step: data.step });
      } else if (data.type === 'done') {
        terminal = true;
        setState({ status: 'done' });
        es.close();
      } else if (data.type === 'error') {
        terminal = true;
        setState({ status: 'error', message: data.log, log: data.log });
        es.close();
      }
    };

    es.onerror = () => {
      if (terminal) return;
      terminal = true;
      setState({ status: 'error', message: 'Connection lost. Please try again.', log: '' });
      es.close();
    };

    return () => {
      terminal = true;
      es.close();
    };
  }, [videoId, jobId]);

  const progress = state.status === 'running' ? state.progress : state.status === 'done' ? 100 : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Deep Dive Progress"
        className="w-full max-w-lg rounded-xl bg-zinc-900 border border-zinc-800 p-6 shadow-2xl mx-4"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-zinc-100">Deep Dive</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-100 text-lg leading-none px-1"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Progress bar */}
        <div
          className="h-2 bg-zinc-700 rounded-full overflow-hidden mb-3"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full bg-blue-600 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        {state.status === 'running' && state.step && (
          <p className="text-xs text-zinc-400">{state.step}</p>
        )}

        {state.status === 'done' && (
          <p role="status" className="text-xs text-green-400">✓ Done</p>
        )}

        {state.status === 'error' && (
          <div className="space-y-2">
            <p role="alert" className="text-xs text-red-400 flex items-start gap-1">
              <span aria-hidden="true">⚠</span> {state.message}
            </p>
            <button
              type="button"
              aria-expanded={logsOpen}
              aria-controls={LOG_PANEL_ID}
              onClick={() => setLogsOpen((prev) => !prev)}
              className="text-xs text-zinc-400 hover:text-zinc-100 underline"
            >
              {logsOpen ? 'Hide Logs' : 'Show Logs'}
            </button>
            {logsOpen && (
              <section id={LOG_PANEL_ID} aria-label="Logs">
                <pre className="text-xs text-zinc-400 bg-zinc-800 rounded p-3 overflow-auto max-h-40">
                  {state.log}
                </pre>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
