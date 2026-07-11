/** @jest-environment jsdom */
import { render, screen, waitFor, act } from '@testing-library/react';
import { IngestProgressBanner } from '@/components/cloud/IngestProgressBanner';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return { getJobStatus: jest.fn(), UnauthorizedError };
});
import { getJobStatus, UnauthorizedError } from '@/lib/client/api';
import type { JobStatus, PlaylistJobRow } from '@/lib/storage/job-queue';
import type { Rollup } from '@/lib/job-queue/poll-client';
const getJobStatusMock = getJobStatus as jest.MockedFunction<typeof getJobStatus>;

const TERMINAL = ['completed', 'failed', 'dead_letter', 'cancelled'];
const roll = (over: any) => ({ queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false, ...over });
// Build REAL job rows from bucket counts. The banner polls via
// getJobStatus(...).then(r => r.jobs), and pollUntilTerminal RECOMPUTES rollup from
// those rows — so jobs must match the rollup or terminal is never reached (R2 Blocking).
// Typed as PlaylistJobRow[] (status cast to JobStatus) to satisfy the typed mock (R3 High).
const jobsFrom = (r: any): PlaylistJobRow[] => {
  const statuses: string[] = ([] as string[]).concat(
    Array(r.queued).fill('queued'), Array(r.active).fill('active'),
    Array(r.completed).fill('completed'), Array(r.failed).fill('failed'),
    Array(r.dead_letter).fill('dead_letter'), Array(r.cancelled).fill('cancelled'));
  return statuses.map((s, i) => ({ jobId: `j${i}`, videoId: `v${i}`, status: s as JobStatus, progressPhase: null, attempts: 0, error: null }));
};
// Derive total+terminal from the rows so probe (.rollup) and poll (rollup(jobs)) always agree (R3 Low).
const status = (over: any): { jobs: PlaylistJobRow[]; rollup: Rollup } => {
  const r = roll(over);
  const jobs = jobsFrom(r);
  r.total = jobs.length;
  r.terminal = jobs.length > 0 && jobs.every((j) => TERMINAL.includes(j.status));
  return { jobs, rollup: r as Rollup };
};

beforeEach(() => jest.clearAllMocks());
afterEach(() => jest.useRealTimers()); // unconditional restore — a throwing fake-timer test can't leak frozen time (R3 Medium)

describe('IngestProgressBanner', () => {
  it('stays hidden when the probe is empty (total 0)', async () => {
    getJobStatusMock.mockResolvedValue(status({ total: 0 }));
    const { container } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it('stays hidden when the probe is already terminal', async () => {
    getJobStatusMock.mockResolvedValue(status({ total: 1, completed: 1, terminal: true }));
    const { container } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it('redirects to /login when the probe is unauthorized', async () => {
    getJobStatusMock.mockRejectedValue(new UnauthorizedError('x'));
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });

  // Observable transient render: use fake timers + a never-terminal poll so the
  // 'progress' commit is not coalesced with a terminal one (R2 High #2).
  it('renders "N of M" and a progressbar while non-terminal', async () => {
    jest.useFakeTimers();
    getJobStatusMock.mockResolvedValue(status({ total: 2, active: 2 })); // never terminal
    const { unmount } = render(<IngestProgressBanner playlistId="p" />);
    await act(async () => {}); // flush probe + first poll microtasks; loop then parks on the fake timer
    expect(screen.getByText(/Ingesting 0 of 2/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    unmount();             // abort the parked poll loop before restoring timers
    jest.clearAllTimers(); // afterEach() restores real timers unconditionally (R3 Low)
  });

  // Stable terminal state only (poll #1 is immediately terminal → no sleep → fast under real timers).
  it('resolves to complete and fires parent onProgress on advance', async () => {
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 2, queued: 1, active: 1 })) // probe (live)
      .mockResolvedValue(status({ total: 2, completed: 2 }));            // poll → all-terminal rows
    const onProgress = jest.fn();
    render(<IngestProgressBanner playlistId="p" onProgress={onProgress} />);
    await waitFor(() => expect(screen.getByText(/Ingest complete/)).toBeInTheDocument());
    expect(onProgress).toHaveBeenCalled(); // done count advanced 0 → 2
  });

  it('fires parent onProgress only on strict advances (not regressions or repeats)', async () => {
    jest.useFakeTimers();
    const onProgress = jest.fn();
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 3, completed: 1, active: 2 })) // probe → baseline done=1
      .mockResolvedValueOnce(status({ total: 3, completed: 2, active: 1 })) // poll1 advance 1→2 → FIRE
      .mockResolvedValueOnce(status({ total: 3, completed: 1, active: 2 })) // poll2 regress 2→1 → no fire
      .mockResolvedValueOnce(status({ total: 3, completed: 2, active: 1 })) // poll3 repeat →2 (==max) → no fire
      .mockResolvedValue(status({ total: 3, completed: 3 }));               // poll4 terminal 2→3 → FIRE
    const { unmount } = render(<IngestProgressBanner playlistId="p" onProgress={onProgress} />);
    await act(async () => {});                                        // probe + poll1 (immediate)
    await act(async () => { await jest.advanceTimersByTimeAsync(2000); }); // poll2
    await act(async () => { await jest.advanceTimersByTimeAsync(4000); }); // poll3
    await act(async () => { await jest.advanceTimersByTimeAsync(8000); }); // poll4 terminal
    expect(onProgress).toHaveBeenCalledTimes(2);
    unmount();
    jest.clearAllTimers();
  });

  it('shows mixed state when terminal with failures', async () => {
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 3, active: 3 }))            // probe (live)
      .mockResolvedValue(status({ total: 3, completed: 2, failed: 1 })); // poll → terminal, mixed
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(screen.getByText(/2 done · 1 failed/)).toBeInTheDocument());
  });

  it('redirects to /login when polling hits 401 (isFatal)', async () => {
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 2, active: 2 }))   // probe (live)
      .mockRejectedValue(new UnauthorizedError('x'));           // poll → fatal
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });

  it('shows give-up only after a live probe, on repeated poll failures', async () => {
    jest.useFakeTimers();
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 2, active: 2 })) // probe live
      .mockRejectedValue(new Error('net'));                   // all polls fail
    render(<IngestProgressBanner playlistId="p" />);
    await screen.findByText(/Ingesting 0 of 2/);
    await act(async () => { await jest.advanceTimersByTimeAsync(60000); }); // exhaust 5 retries w/ backoff
    expect(await screen.findByText(/Lost connection to progress updates/)).toBeInTheDocument();
    jest.useRealTimers();
  });

  it('stops polling the old playlist after unmount (no leaked loop)', async () => {
    getJobStatusMock.mockResolvedValue(status({ total: 2, active: 2 }));
    const { unmount } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalled());
    unmount();
    const callsAtUnmount = getJobStatusMock.mock.calls.length;
    await new Promise((r) => setTimeout(r, 50));
    expect(getJobStatusMock.mock.calls.length).toBe(callsAtUnmount); // no further fetches
  });
});
