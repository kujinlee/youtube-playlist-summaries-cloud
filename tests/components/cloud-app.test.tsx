/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useSearchParams } from 'next/navigation';
import CloudApp from '@/components/cloud/CloudApp';
import { listPlaylists, listVideos, setArchived, UnauthorizedError } from '@/lib/client/api';
import type { Video } from '@/types';

const replace = jest.fn();
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(),
  useRouter: () => ({ replace }),
}));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return {
    listPlaylists: jest.fn(),
    listVideos: jest.fn(),
    setArchived: jest.fn(),
    UnauthorizedError,
  };
});

jest.mock('@/lib/supabase/client', () => ({
  createClient: () => ({ auth: { signOut: jest.fn().mockResolvedValue({ error: null }) } }),
}));

const mockUseSearchParams = useSearchParams as jest.MockedFunction<typeof useSearchParams>;
const mockListPlaylists = listPlaylists as jest.MockedFunction<typeof listPlaylists>;
const mockListVideos = listVideos as jest.MockedFunction<typeof listVideos>;
const mockSetArchived = setArchived as jest.MockedFunction<typeof setArchived>;

function setSearchParams(query: string) {
  mockUseSearchParams.mockReturnValue(
    new URLSearchParams(query) as unknown as ReturnType<typeof useSearchParams>,
  );
}

const PLAYLIST_ID = '11111111-1111-1111-1111-111111111111';
const CLOUD_SCOPE = { mode: 'cloud' as const, playlistId: PLAYLIST_ID };
const SESSION = { userId: 'u1', email: 'you@email.com' };

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: 'vid1',
    title: 'Alpha video',
    youtubeUrl: 'https://youtu.be/vid1',
    language: 'en',
    durationSeconds: 100,
    archived: false,
    ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
    overallScore: 3,
    summaryMd: null,
    processedAt: '2026-01-01T00:00:00.000Z',
    ...overrides,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockListPlaylists.mockResolvedValue([]);
  setSearchParams('');
});

it('renders the header title and AccountMenu with the signed-in email', () => {
  render(<CloudApp session={SESSION} />);
  expect(screen.getByText('YouTube Playlist Summaries')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /you@email\.com/i })).toBeInTheDocument();
});

it('renders "Not signed in" and no AccountMenu when session is null', () => {
  render(<CloudApp session={null} />);
  expect(screen.getByText('Not signed in')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /you@email\.com/i })).not.toBeInTheDocument();
});

it('shows a pick-a-playlist empty state when ?playlist is absent, and never calls listVideos', async () => {
  render(<CloudApp session={SESSION} />);
  expect(await screen.findByText(/pick a playlist/i)).toBeInTheDocument();
  expect(mockListVideos).not.toHaveBeenCalled();
});

it('fetches videos via listVideos(cloudScope, …) and renders them when ?playlist is present', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  mockListVideos.mockResolvedValue({ videos: [makeVideo()], playlistUrl: '', playlistTitle: 'ML' });

  render(<CloudApp session={SESSION} />);

  expect(await screen.findByText('Alpha video')).toBeInTheDocument();
  expect(mockListVideos).toHaveBeenCalledWith(CLOUD_SCOPE, undefined);
});

it('shows "No videos here yet" when the selected playlist has zero videos', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  mockListVideos.mockResolvedValue({ videos: [], playlistUrl: '', playlistTitle: 'ML' });

  render(<CloudApp session={SESSION} />);

  expect(await screen.findByText(/no videos here yet/i)).toBeInTheDocument();
});

it('re-fetches via listVideos(cloudScope, newSort) when a column header is clicked', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  mockListVideos.mockResolvedValue({
    videos: [makeVideo(), makeVideo({ id: 'vid2', title: 'Beta video' })],
    playlistUrl: '',
    playlistTitle: 'ML',
  });

  render(<CloudApp session={SESSION} />);
  await screen.findByText('Alpha video');

  fireEvent.click(screen.getByRole('button', { name: /^Title/i }));

  await waitFor(() =>
    expect(mockListVideos).toHaveBeenCalledWith(CLOUD_SCOPE, { column: 'name', order: 'asc' }),
  );
});

it('onArchive calls setArchived(cloudScope, id, true) and marks the row archived', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  mockListVideos.mockResolvedValue({ videos: [makeVideo()], playlistUrl: '', playlistTitle: 'ML' });
  mockSetArchived.mockResolvedValue(undefined);

  render(<CloudApp session={SESSION} />);
  await screen.findByText('Alpha video');

  fireEvent.click(screen.getByRole('button', { name: 'Menu' }));
  fireEvent.click(screen.getByRole('button', { name: /^Archive$/i }));

  await waitFor(() => expect(mockSetArchived).toHaveBeenCalledWith(CLOUD_SCOPE, 'vid1', true));
});

it('redirects to /login when the initial listVideos rejects with UnauthorizedError', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  mockListVideos.mockRejectedValue(new UnauthorizedError('unauthorized'));

  render(<CloudApp session={SESSION} />);

  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
});

it('redirects to /login when setArchived rejects with UnauthorizedError', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  mockListVideos.mockResolvedValue({ videos: [makeVideo()], playlistUrl: '', playlistTitle: 'ML' });
  mockSetArchived.mockRejectedValue(new UnauthorizedError('unauthorized'));

  render(<CloudApp session={SESSION} />);
  await screen.findByText('Alpha video');

  fireEvent.click(screen.getByRole('button', { name: 'Menu' }));
  fireEvent.click(screen.getByRole('button', { name: /^Archive$/i }));

  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
});
