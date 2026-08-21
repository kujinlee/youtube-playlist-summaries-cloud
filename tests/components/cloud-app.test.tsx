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

// ── backlog #55 — a video with no AI score yet is PENDING, not hidden ────────────────────────────
//
// The filter read `v.overallScore >= filters.minScore`, and `undefined >= 0` is FALSE, so an
// unscored video vanished at the "All scores" default while `VideoList`'s empty branch blamed the
// user's filters. Reachable on EVERY ingest: claimVideoSlot inserts the row before the summary
// exists (0007_storage_and_rpcs.sql:35 ← lib/pipeline.ts:235), so the window is exactly when
// IngestProgressBanner is promising the videos.
//
// These tests exist because nothing below the browser could see it: the routes never filter, so
// 2719 unit tests and 7 e2e rungs passed over it until backlog #44 first rendered the pane.

it('#55: a video with no overallScore is LISTED, not filtered away', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  const pending = makeVideo({ id: 'v-pending', title: 'Still summarising' });
  delete (pending as Partial<Video>).overallScore;       // the real shape of a claimed-but-unsummarised row
  mockListVideos.mockResolvedValue({ videos: [pending], playlistUrl: '', playlistTitle: 'ML' });

  render(<CloudApp session={SESSION} />);

  expect(await screen.findByText('Still summarising')).toBeInTheDocument();
  // and the misleading empty state must NOT be what the user sees
  expect(screen.queryByText(/no videos to show/i)).not.toBeInTheDocument();
});

it('#55: the unscored row renders an em-dash rather than an empty score cell', async () => {
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  const pending = makeVideo({ id: 'v-pending', title: 'Still summarising' });
  delete (pending as Partial<Video>).overallScore;
  mockListVideos.mockResolvedValue({ videos: [pending], playlistUrl: '', playlistTitle: 'ML' });

  render(<CloudApp session={SESSION} />);
  await screen.findByText('Still summarising');

  // A blank cell is indistinguishable from a rendering fault; "—" says "not yet" out loud.
  const overall = screen.getAllByLabelText('Overall').find((el) => el.tagName === 'TD');
  expect(overall).toHaveTextContent('—');
});

it('#55: a SCORED video is still filtered out when it is below an explicit minScore', async () => {
  // The guard on the guard: #55 must not turn the AI-score filter into a no-op. Only the ABSENT
  // case is exempt — a real score below the threshold still hides, exactly as before.
  setSearchParams(`playlist=${PLAYLIST_ID}`);
  mockListVideos.mockResolvedValue({
    videos: [makeVideo({ id: 'lo', title: 'Low score', overallScore: 3 })],
    playlistUrl: '', playlistTitle: 'ML',
  });

  render(<CloudApp session={SESSION} />);
  await screen.findByText('Low score');

  fireEvent.change(screen.getByLabelText(/ai score/i), { target: { value: '4' } });
  await waitFor(() => expect(screen.queryByText('Low score')).not.toBeInTheDocument());
});
