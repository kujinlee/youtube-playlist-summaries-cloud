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
}
export type PollResult =
  | { done: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { timedOut: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { failed: true; error: string };

export async function pollUntilTerminal(
  fetchRows: () => Promise<PlaylistJobRow[]>, opts: PollOptions = {},
): Promise<PollResult> {
  const intervalMs = opts.intervalMs ?? 2000;
  const maxIntervalMs = opts.maxIntervalMs ?? 10000;
  const timeoutMs = opts.timeoutMs ?? 10 * 60_000;
  const maxErrors = opts.maxConsecutiveErrors ?? 5;
  const sleep = opts.sleep ?? ((ms) => new Promise<void>((r) => setTimeout(r, ms)));
  const now = opts.now ?? (() => Date.now());
  const start = now();
  let delay = intervalMs; let errors = 0; let lastRows: PlaylistJobRow[] = [];
  for (;;) {
    try {
      lastRows = await fetchRows(); errors = 0;
      const r = rollup(lastRows);
      if (r.terminal) return { done: true, rollup: r, rows: lastRows };
    } catch (e) {
      if (++errors >= maxErrors) return { failed: true, error: String(e) };
    }
    if (now() - start >= timeoutMs) return { timedOut: true, rollup: rollup(lastRows), rows: lastRows };
    await sleep(delay);
    delay = Math.min(delay * 2, maxIntervalMs);
  }
}
