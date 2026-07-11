/** @jest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import VideoMenu from '../../components/VideoMenu';
import { ScopeProvider, type Scope } from '@/lib/client/scope';

const PID = '11111111-1111-1111-1111-111111111111';
const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/o', baseOutputFolder: '/o' };
const CLOUD_SCOPE: Scope = { mode: 'cloud', playlistId: PID };

function renderCloud(ui: React.ReactElement) {
  return render(<ScopeProvider scope={CLOUD_SCOPE}>{ui}</ScopeProvider>);
}
function renderLocal(ui: React.ReactElement) {
  return render(<ScopeProvider scope={LOCAL_SCOPE}>{ui}</ScopeProvider>);
}

const video = {
  id: 'vid11111111', title: 'T', youtubeUrl: 'https://youtu.be/x', language: 'en',
  durationSeconds: 5, archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
};

const baseProps = { outputFolder: '/o', baseOutputFolder: '/o', onArchive() {}, onEditCorrections() {}, onGenerateHtml() {}, onClose() {}, busy: false };
const cloudProps = { ...baseProps };
const localProps = { ...baseProps };

let onShare: jest.Mock;

beforeEach(() => {
  onShare = jest.fn();
});

test('cloud + summaryReady: View/Download/Share render with exact hrefs', () => {
  renderCloud(<VideoMenu {...cloudProps} video={{ ...video, summaryReady: true } as any} onShare={onShare} />);
  const view = screen.getByRole('link', { name: /view summary/i });
  expect(view).toHaveAttribute('target', '_blank');
  expect(view).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=summary`);

  const md = screen.getByRole('link', { name: /download markdown/i });
  expect(md).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=summary&format=md&download=1`);
  expect(md).toHaveAttribute('download');

  const html = screen.getByRole('link', { name: /download html/i });
  expect(html).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=summary&format=html&download=1`);
  expect(html).toHaveAttribute('download');

  fireEvent.click(screen.getByRole('button', { name: /share/i }));
  expect(onShare).toHaveBeenCalledTimes(1);
});

test('cloud + NOT ready: the four items are disabled with "Finalizing…" and no href', () => {
  renderCloud(<VideoMenu {...cloudProps} video={{ ...video, summaryReady: false } as any} onShare={onShare} />);
  const view = screen.getByText(/view summary/i);
  expect(view).toHaveAttribute('aria-disabled', 'true');
  expect(view).toHaveAttribute('title', 'Finalizing…');
  expect(screen.queryByRole('link', { name: /view summary/i })).not.toBeInTheDocument();
  // Share disabled → clicking does nothing
  const share = screen.getByText(/share/i);
  fireEvent.click(share);
  expect(onShare).not.toHaveBeenCalled();
});

test('local mode: 2c items absent, existing menu unchanged', () => {
  renderLocal(<VideoMenu {...localProps} video={{ ...video, summaryReady: undefined } as any} />);
  expect(screen.queryByText(/view summary/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/download markdown/i)).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: /watch on youtube/i })).toBeInTheDocument();
});
