/** @jest-environment jsdom */
/**
 * Stage: playlist-sidebar-ux T10. Sidebar trash button + confirm-modal wiring. See
 * docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md Task 10 Enumerated Behaviors
 * (#1, #7 nav) and docs/superpowers/specs/...-design.md §B7.
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { useSearchParams } from 'next/navigation';
import { listPlaylists, backfillPlaylistTitles, deletePlaylist, UnauthorizedError } from '@/lib/client/api';
import PlaylistSidebar from '@/components/cloud/PlaylistSidebar';
import type { PlaylistSummary } from '@/lib/storage/metadata-store';

const replace = jest.fn();
const push = jest.fn();
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(),
  useRouter: () => ({ replace, push }),
}));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return {
    listPlaylists: jest.fn(),
    backfillPlaylistTitles: jest.fn(),
    deletePlaylist: jest.fn(),
    UnauthorizedError,
  };
});

const mockListPlaylists = listPlaylists as jest.MockedFunction<typeof listPlaylists>;
const mockBackfill = backfillPlaylistTitles as jest.MockedFunction<typeof backfillPlaylistTitles>;
const mockDeletePlaylist = deletePlaylist as jest.MockedFunction<typeof deletePlaylist>;
const mockUseSearchParams = useSearchParams as jest.MockedFunction<typeof useSearchParams>;

function setSearchParams(query: string) {
  mockUseSearchParams.mockReturnValue(
    new URLSearchParams(query) as unknown as ReturnType<typeof useSearchParams>,
  );
}

const p1: PlaylistSummary = {
  id: 'p1-uuid',
  playlistKey: 'PL1',
  playlistUrl: 'https://youtube.com/playlist?list=PL1',
  playlistTitle: 'ML Talks',
  createdAt: '2026-01-01T00:00:00Z',
};

const p2: PlaylistSummary = {
  id: 'p2-uuid',
  playlistKey: 'PL2',
  playlistUrl: 'https://youtube.com/playlist?list=PL2',
  playlistTitle: null,
  createdAt: '2026-01-02T00:00:00Z',
};

beforeEach(() => {
  jest.clearAllMocks();
  sessionStorage.clear();
  setSearchParams('');
  mockBackfill.mockResolvedValue({ updated: 0, attempted: 0 });
});

it('trash button is a sibling of the row Link, not nested inside it', async () => {
  mockListPlaylists.mockResolvedValue([p1]);
  render(<PlaylistSidebar userId="user-a" />);
  const trash = await screen.findByRole('button', { name: 'Delete playlist ML Talks' });
  expect(trash.closest('a')).toBeNull();
  const li = trash.closest('li')!;
  expect(within(li).getByRole('link', { name: 'ML Talks' })).toBeInTheDocument();
});

// Behavior 1: trash click opens modal WITHOUT navigating.
it('trash click opens the confirm modal; the row link never receives the click', async () => {
  mockListPlaylists.mockResolvedValue([p1]);
  render(<PlaylistSidebar userId="user-a" />);
  const trash = await screen.findByRole('button', { name: 'Delete playlist ML Talks' });
  const link = screen.getByRole('link', { name: 'ML Talks' });
  const linkClickSpy = jest.fn();
  link.addEventListener('click', linkClickSpy);

  fireEvent.click(trash);

  expect(linkClickSpy).not.toHaveBeenCalled();
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(within(screen.getByRole('dialog')).getByText(/ML Talks/)).toBeInTheDocument();
});

it('opens the modal for the correct row when multiple playlists exist (null-title fixture too)', async () => {
  mockListPlaylists.mockResolvedValue([p1, p2]);
  render(<PlaylistSidebar userId="user-a" />);
  const trash2 = await screen.findByRole('button', { name: 'Delete playlist Untitled playlist' });

  fireEvent.click(trash2);

  const dialog = screen.getByRole('dialog');
  expect(within(dialog).getByText(/Untitled playlist/)).toBeInTheDocument();
});

it('Cancel in the modal closes it without deleting', async () => {
  mockListPlaylists.mockResolvedValue([p1]);
  render(<PlaylistSidebar userId="user-a" />);
  fireEvent.click(await screen.findByRole('button', { name: 'Delete playlist ML Talks' }));

  fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(mockDeletePlaylist).not.toHaveBeenCalled();
});

// Behavior 7 (non-active): success closes modal, refetches, does NOT navigate.
it('delete success for a NON-active playlist: modal closes, list refetched, no navigation', async () => {
  setSearchParams(''); // no active playlist
  mockListPlaylists.mockResolvedValueOnce([p1]).mockResolvedValueOnce([]);
  mockDeletePlaylist.mockResolvedValue(undefined);
  render(<PlaylistSidebar userId="user-a" />);
  fireEvent.click(await screen.findByRole('button', { name: 'Delete playlist ML Talks' }));

  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }));

  await waitFor(() => expect(mockDeletePlaylist).toHaveBeenCalledWith('p1-uuid'));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  await waitFor(() => expect(mockListPlaylists).toHaveBeenCalledTimes(2));
  expect(push).not.toHaveBeenCalled();
});

// Behavior 7 (active): success navigates to "/" with no ?playlist param.
it('delete success for the ACTIVE playlist: navigates to "/" (no ?playlist param)', async () => {
  setSearchParams('playlist=p1-uuid');
  mockListPlaylists.mockResolvedValueOnce([p1]).mockResolvedValueOnce([]);
  mockDeletePlaylist.mockResolvedValue(undefined);
  render(<PlaylistSidebar userId="user-a" />);
  fireEvent.click(await screen.findByRole('button', { name: 'Delete playlist ML Talks' }));

  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }));

  await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
});

// Behavior 8: error keeps the modal open with an inline error; list not refetched.
it('delete error: modal stays open with inline error, list not refetched, no navigation', async () => {
  mockListPlaylists.mockResolvedValue([p1]);
  mockDeletePlaylist.mockRejectedValue(new Error('server error'));
  render(<PlaylistSidebar userId="user-a" />);
  fireEvent.click(await screen.findByRole('button', { name: 'Delete playlist ML Talks' }));

  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }));

  expect(await screen.findByRole('alert')).toHaveTextContent('server error');
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(mockListPlaylists).toHaveBeenCalledTimes(1);
  expect(push).not.toHaveBeenCalled();
});
