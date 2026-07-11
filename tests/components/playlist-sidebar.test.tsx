/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useSearchParams } from 'next/navigation';
import { listPlaylists, UnauthorizedError } from '@/lib/client/api';
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
    UnauthorizedError,
  };
});

const mockListPlaylists = listPlaylists as jest.MockedFunction<typeof listPlaylists>;
const mockUseSearchParams = useSearchParams as jest.MockedFunction<typeof useSearchParams>;

function setSearchParams(query: string) {
  mockUseSearchParams.mockReturnValue(
    new URLSearchParams(query) as unknown as ReturnType<typeof useSearchParams>,
  );
}

const playlists: PlaylistSummary[] = [
  {
    id: 'p1-uuid',
    playlistKey: 'PL1',
    playlistUrl: 'https://youtube.com/playlist?list=PL1',
    playlistTitle: 'ML Talks',
    createdAt: '2026-01-01T00:00:00Z',
  },
  {
    id: 'p2-uuid',
    playlistKey: 'PL2',
    playlistUrl: 'https://youtube.com/playlist?list=PL2',
    playlistTitle: null,
    createdAt: '2026-01-02T00:00:00Z',
  },
];

beforeEach(() => {
  jest.clearAllMocks();
  global.fetch = jest.fn();
  setSearchParams('');
});

it('renders playlist titles fetched via apiClient.listPlaylists', async () => {
  mockListPlaylists.mockResolvedValue(playlists);
  render(<PlaylistSidebar />);
  expect(await screen.findByText('ML Talks')).toBeInTheDocument();
  expect(mockListPlaylists).toHaveBeenCalledTimes(1);
});

it('falls back to "Untitled playlist" when playlistTitle is null', async () => {
  mockListPlaylists.mockResolvedValue(playlists);
  render(<PlaylistSidebar />);
  expect(await screen.findByText('Untitled playlist')).toBeInTheDocument();
});

it('a playlist link has href exactly "/?playlist=<uuid>" (spec §9 URL contract)', async () => {
  mockListPlaylists.mockResolvedValue(playlists);
  render(<PlaylistSidebar />);
  const link = await screen.findByRole('link', { name: 'ML Talks' });
  expect(link).toHaveAttribute('href', '/?playlist=p1-uuid');
  const link2 = screen.getByRole('link', { name: 'Untitled playlist' });
  expect(link2).toHaveAttribute('href', '/?playlist=p2-uuid');
});

it('marks the item matching ?playlist as the active item', async () => {
  setSearchParams('playlist=p2-uuid');
  mockListPlaylists.mockResolvedValue(playlists);
  render(<PlaylistSidebar />);
  const activeLink = await screen.findByRole('link', { name: 'Untitled playlist' });
  expect(activeLink).toHaveAttribute('aria-current', 'page');
  const inactiveLink = screen.getByRole('link', { name: 'ML Talks' });
  expect(inactiveLink).not.toHaveAttribute('aria-current');
});

it('redirects to /login when listPlaylists rejects with UnauthorizedError, and shows no inline error', async () => {
  mockListPlaylists.mockRejectedValue(new UnauthorizedError('unauthorized'));
  render(<PlaylistSidebar />);

  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  expect(screen.queryByText('unauthorized')).not.toBeInTheDocument();
  expect(screen.queryByText('Failed to load playlists.')).not.toBeInTheDocument();
});

it('shows an onboarding empty state when there are no playlists', async () => {
  mockListPlaylists.mockResolvedValue([]);
  render(<PlaylistSidebar />);
  expect(await screen.findByText(/no playlists yet/i)).toBeInTheDocument();
});

it('"+ New playlist" is disabled and clicking it makes no listPlaylists/fetch call', async () => {
  mockListPlaylists.mockResolvedValue(playlists);
  render(<PlaylistSidebar />);
  await screen.findByText('ML Talks');
  expect(mockListPlaylists).toHaveBeenCalledTimes(1);

  const newButton = screen.getByRole('button', { name: /new playlist/i });
  expect(newButton).toBeDisabled();
  fireEvent.click(newButton);

  expect(mockListPlaylists).toHaveBeenCalledTimes(1);
  expect(global.fetch).not.toHaveBeenCalled();
});

it('"+ New playlist" still renders (disabled) in the empty state', async () => {
  mockListPlaylists.mockResolvedValue([]);
  render(<PlaylistSidebar />);
  await screen.findByText(/no playlists yet/i);
  const newButton = screen.getByRole('button', { name: /new playlist/i });
  expect(newButton).toBeDisabled();
});
