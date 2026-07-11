import type { PlaylistJobRow, JobStatus } from '@/lib/storage/job-queue';

export const TERMINAL_STATUSES: JobStatus[] = ['completed', 'failed', 'dead_letter', 'cancelled'];

export interface Rollup {
  queued: number; active: number; completed: number;
  failed: number; dead_letter: number; cancelled: number;
  total: number; terminal: boolean;
}
export function rollup(rows: PlaylistJobRow[]): Rollup {
  const c = { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0 };
  for (const r of rows) c[r.status] += 1;
  const total = rows.length;
  const terminal = total > 0 && rows.every((r) => TERMINAL_STATUSES.includes(r.status));
  return { ...c, total, terminal };
}

export interface PollOptions {
  intervalMs?: number; maxIntervalMs?: number; timeoutMs?: number;
  maxConsecutiveErrors?: number;
  sleep?: (ms: number) => Promise<void>;
  now?: () => number;
  onProgress?: (snapshot: { rollup: Rollup; rows: PlaylistJobRow[] }) => void; // after each successful fetch, incl. terminal; isolated (throwing does not affect polling)
  isFatal?: (err: unknown) => boolean;  // if true for a fetch error → stop immediately, do NOT retry
  signal?: AbortSignal;                 // when aborted → stop; resolves { aborted: true }
}
export type PollResult =
  | { done: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { timedOut: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { failed: true; error: string; fatal?: boolean }  // fatal:true when isFatal matched
  | { aborted: true };                                 // signal aborted

export async function pollUntilTerminal(
  fetchRows: () => Promise<PlaylistJobRow[]>,
  opts: PollOptions = {},
): Promise<PollResult> {
  const intervalMs = opts.intervalMs ?? 2000;
  const maxIntervalMs = opts.maxIntervalMs ?? 10000;
  const timeoutMs = opts.timeoutMs ?? 10 * 60_000;
  const maxConsecutiveErrors = opts.maxConsecutiveErrors ?? 5;
  const sleep = opts.sleep ?? ((ms) => new Promise<void>((r) => setTimeout(r, ms)));
  const now = opts.now ?? (() => Date.now());

  const start = now();
  let delay = intervalMs;
  let errors = 0;
  let lastRows: PlaylistJobRow[] = [];

  for (;;) {
    if (opts.signal?.aborted) return { aborted: true };
    if (now() - start >= timeoutMs) return { timedOut: true, rollup: rollup(lastRows), rows: lastRows };

    let rows: PlaylistJobRow[];
    try {
      rows = await fetchRows();
    } catch (err) {
      if (opts.isFatal?.(err)) return { failed: true, error: String(err), fatal: true };
      errors += 1;
      if (errors >= maxConsecutiveErrors) return { failed: true, error: String(err) };
      if (opts.signal?.aborted) return { aborted: true };
      await sleep(delay);
      delay = Math.min(delay * 2, maxIntervalMs);
      continue;
    }

    lastRows = rows;
    errors = 0;
    const r = rollup(rows);
    // Isolated: a throwing onProgress must not be miscounted as a fetch failure.
    try { opts.onProgress?.({ rollup: r, rows }); } catch { /* swallow callback error */ }
    if (r.terminal) return { done: true, rollup: r, rows };

    if (opts.signal?.aborted) return { aborted: true };
    await sleep(delay);
    delay = Math.min(delay * 2, maxIntervalMs);
  }
}
