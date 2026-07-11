/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const push = jest.fn();
const replace = jest.fn();
let searchParamsValue = new URLSearchParams('');
const setSearchParams = (v: string) => (searchParamsValue = new URLSearchParams(v));
jest.mock('next/navigation', () => ({ useRouter: () => ({ push, replace }), useSearchParams: () => searchParamsValue }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  class IngestError extends Error { constructor(public status: number, public info: any = {}) { super('e'); } }
  return {
    listPlaylists: jest.fn().mockResolvedValue([]),
    listVideos: jest.fn().mockResolvedValue({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'X' }),
    createIngest: jest.fn(),
    getJobStatus: jest.fn().mockResolvedValue({ jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } }),
    ingestErrorMessage: (e: any) => `msg-${e.status}`,
    IngestError, UnauthorizedError,
  };
});
import CloudApp from '@/components/cloud/CloudApp';
import { createIngest } from '@/lib/client/api';
const createIngestMock = createIngest as jest.MockedFunction<typeof createIngest>;

const result = (over: any = {}) => ({ playlistId: 'p-uuid', jobs: [], challengeRequired: false, counts: { enqueued: 3, joined: 0, skipped: 3, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 }, ...over });
beforeEach(() => { jest.clearAllMocks(); setSearchParams(''); });

async function openAndSubmit() {
  fireEvent.click(await screen.findByRole('button', { name: /new playlist/i }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://youtube.com/playlist?list=X' } });
  fireEvent.click(screen.getByRole('button', { name: /add/i }));
}

it('opens the modal from the sidebar and navigates on success', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/?playlist=p-uuid'));
});

it('shows the summary notice on the target playlist page (cross-playlist nav does not wipe it)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=other');          // currently viewing a DIFFERENT playlist
  const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/?playlist=p-uuid'));
  setSearchParams('playlist=p-uuid');          // navigation resolves
  rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/Queued 3 · 3 skipped/)).toBeInTheDocument();
});

it('Refresh re-POSTs the playlistUrl and does not navigate', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=p-uuid');
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled()); // enabled once listVideos loaded playlistUrl
  fireEvent.click(refresh);
  await waitFor(() => expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=X'));
  expect(push).not.toHaveBeenCalled();
});

it('drops a stale listVideos response so Refresh uses the current playlist url (R3 High)', async () => {
  // Playlist A's listVideos is slow; navigate to B; A resolves LATE with A's url.
  // The sequence guard must drop A so Refresh re-POSTs B, never A.
  const { listVideos } = jest.requireMock('@/lib/client/api');
  let resolveA!: (v: any) => void;
  (listVideos as jest.Mock)
    .mockReturnValueOnce(new Promise((r) => { resolveA = r; }))                                                // A (slow)
    .mockResolvedValue({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=B', playlistTitle: 'B' }); // B
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=A');
  const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  setSearchParams('playlist=B');
  rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />); // B mounts, bumps reqSeq
  resolveA({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=A', playlistTitle: 'A' }); // stale → dropped
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled());
  fireEvent.click(refresh);
  await waitFor(() => expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=B'));
  expect(createIngestMock).not.toHaveBeenCalledWith('https://youtube.com/playlist?list=A');
});
