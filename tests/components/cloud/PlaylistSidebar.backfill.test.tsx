/** @jest-environment jsdom */
/**
 * Stage: playlist-sidebar-ux T5. Covers the sidebar's auto-backfill trigger — fires the
 * bounded backfill route (T4) at most once per session per user when the loaded playlist
 * list contains a null title, then re-fetches. See docs/superpowers/plans/
 * 2026-07-13-playlist-sidebar-ux.md Task 5 Enumerated Behaviors (#1-#7).
 */
import { render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { useSearchParams } from 'next/navigation';
import { listPlaylists, backfillPlaylistTitles, UnauthorizedError } from '@/lib/client/api';
import PlaylistSidebar from '@/components/cloud/PlaylistSidebar';
import type { PlaylistSummary } from '@/lib/storage/metadata-store';

const replace = jest.fn();
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(),
  useRouter: () => ({ replace }),
}));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return {
    listPlaylists: jest.fn(),
    backfillPlaylistTitles: jest.fn(),
    UnauthorizedError,
  };
});

const mockListPlaylists = listPlaylists as jest.MockedFunction<typeof listPlaylists>;
const mockBackfill = backfillPlaylistTitles as jest.MockedFunction<typeof backfillPlaylistTitles>;
const mockUseSearchParams = useSearchParams as jest.MockedFunction<typeof useSearchParams>;

function setSearchParams(query: string) {
  mockUseSearchParams.mockReturnValue(
    new URLSearchParams(query) as unknown as ReturnType<typeof useSearchParams>,
  );
}

const untitled: PlaylistSummary = {
  id: 'p1-uuid',
  playlistKey: 'PL1',
  playlistUrl: 'https://youtube.com/playlist?list=PL1',
  playlistTitle: null,
  createdAt: '2026-01-01T00:00:00Z',
};

const titled: PlaylistSummary = {
  id: 'p2-uuid',
  playlistKey: 'PL2',
  playlistUrl: 'https://youtube.com/playlist?list=PL2',
  playlistTitle: 'ML Talks',
  createdAt: '2026-01-02T00:00:00Z',
};

beforeEach(() => {
  jest.clearAllMocks();
  setSearchParams('');
  sessionStorage.clear();
});

it('behavior 1: fires one backfill POST and refetches when a null title is present', async () => {
  mockListPlaylists.mockResolvedValueOnce([untitled]).mockResolvedValueOnce([titled]);
  mockBackfill.mockResolvedValue({ updated: 1, attempted: 1 });

  render(<PlaylistSidebar userId="user-a" />);

  await waitFor(() => expect(mockBackfill).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(mockListPlaylists).toHaveBeenCalledTimes(2));
  expect(await screen.findByText('ML Talks')).toBeInTheDocument();
});

it('behavior 2: does NOT loop when the post-backfill refetch still has null titles', async () => {
  mockListPlaylists.mockResolvedValue([untitled]); // every call returns a null-title row
  mockBackfill.mockResolvedValue({ updated: 0, attempted: 1 });

  render(<PlaylistSidebar userId="user-a" />);

  await waitFor(() => expect(mockListPlaylists).toHaveBeenCalledTimes(2));
  // give any further microtask/effect chains a chance to (wrongly) fire again
  await new Promise((r) => setTimeout(r, 20));
  expect(mockBackfill).toHaveBeenCalledTimes(1);
  expect(mockListPlaylists).toHaveBeenCalledTimes(2);
});

it('behavior 3: skips backfill entirely when no title is null', async () => {
  mockListPlaylists.mockResolvedValue([titled]);

  render(<PlaylistSidebar userId="user-a" />);

  await screen.findByText('ML Talks');
  expect(mockBackfill).not.toHaveBeenCalled();
  expect(mockListPlaylists).toHaveBeenCalledTimes(1);
});

it('behavior 4: skips when the per-user sessionStorage flag is already set', async () => {
  sessionStorage.setItem('backfilledTitles:user-a', '1');
  mockListPlaylists.mockResolvedValue([untitled]);

  render(<PlaylistSidebar userId="user-a" />);

  await screen.findByText('Untitled playlist');
  expect(mockBackfill).not.toHaveBeenCalled();
  expect(mockListPlaylists).toHaveBeenCalledTimes(1);
});

it('behavior 5: distinct userIds use distinct sessionStorage keys, both eligible', async () => {
  mockListPlaylists.mockResolvedValue([untitled]);
  mockBackfill.mockResolvedValue({ updated: 0, attempted: 1 });

  const { unmount } = render(<PlaylistSidebar userId="user-a" />);
  await waitFor(() => expect(mockBackfill).toHaveBeenCalledTimes(1));
  unmount();

  render(<PlaylistSidebar userId="user-b" />);
  await waitFor(() => expect(mockBackfill).toHaveBeenCalledTimes(2));

  expect(sessionStorage.getItem('backfilledTitles:user-a')).not.toBeNull();
  expect(sessionStorage.getItem('backfilledTitles:user-b')).not.toBeNull();
});

it('behavior 6: StrictMode double-invoke still fires backfill exactly once', async () => {
  mockListPlaylists.mockResolvedValue([untitled]);
  mockBackfill.mockResolvedValue({ updated: 0, attempted: 1 });

  render(
    <StrictMode>
      <PlaylistSidebar userId="user-a" />
    </StrictMode>,
  );

  await waitFor(() => expect(mockBackfill).toHaveBeenCalledTimes(1));
  await new Promise((r) => setTimeout(r, 20));
  expect(mockBackfill).toHaveBeenCalledTimes(1);
});

it('behavior 7: userId === null is a no-op (no per-user key, unauthenticated)', async () => {
  mockListPlaylists.mockResolvedValue([untitled]);

  render(<PlaylistSidebar userId={null} />);

  await screen.findByText('Untitled playlist');
  expect(mockBackfill).not.toHaveBeenCalled();
  expect(mockListPlaylists).toHaveBeenCalledTimes(1);
});

// Guard against accidental regressions to the pre-existing unauthorized redirect path.
it('still redirects to /login when the initial listPlaylists rejects with UnauthorizedError', async () => {
  mockListPlaylists.mockRejectedValue(new UnauthorizedError('unauthorized'));

  render(<PlaylistSidebar userId="user-a" />);

  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  expect(mockBackfill).not.toHaveBeenCalled();
});
