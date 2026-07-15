/** @jest-environment jsdom */
import { render, screen } from '@testing-library/react';
import VideoMenu from '../../components/VideoMenu';
import { ScopeProvider, type Scope } from '@/lib/client/scope';

const PID = '11111111-1111-1111-1111-111111111111';
const CLOUD_SCOPE: Scope = { mode: 'cloud', playlistId: PID };
const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/o', baseOutputFolder: '/o' };
const renderCloud = (ui: React.ReactElement) => render(<ScopeProvider scope={CLOUD_SCOPE}>{ui}</ScopeProvider>);
const renderLocal = (ui: React.ReactElement) => render(<ScopeProvider scope={LOCAL_SCOPE}>{ui}</ScopeProvider>);

const video = {
  id: 'vid11111111', title: 'T', youtubeUrl: 'https://youtu.be/x', language: 'en',
  durationSeconds: 5, archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
};
const baseProps = { outputFolder: '/o', baseOutputFolder: '/o', onArchive() {}, onEditCorrections() {}, onGenerateHtml() {}, onClose() {}, busy: false };

test('cloud + summaryReady: Dig deeper link has exact href, new tab', () => {
  renderCloud(<VideoMenu {...baseProps} video={{ ...video, summaryReady: true } as any} />);
  const link = screen.getByRole('link', { name: /dig deeper/i });
  expect(link).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=dig-deeper`);
  expect(link).toHaveAttribute('target', '_blank');
  expect(link).toHaveAttribute('rel', 'noopener noreferrer');
});

test('cloud + NOT ready: Dig deeper is disabled span, no link', () => {
  renderCloud(<VideoMenu {...baseProps} video={{ ...video, summaryReady: false } as any} />);
  const el = screen.getByText(/dig deeper/i);
  expect(el).toHaveAttribute('aria-disabled', 'true');
  expect(el).toHaveAttribute('title', 'Finalizing…');
  expect(screen.queryByRole('link', { name: /dig deeper/i })).not.toBeInTheDocument();
});

test('local scope: no Dig deeper item at all', () => {
  renderLocal(<VideoMenu {...baseProps} video={{ ...video, summaryReady: true } as any} />);
  expect(screen.queryByText(/dig deeper/i)).not.toBeInTheDocument();
});
