/** @jest-environment jsdom */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import VideoRow from '@/components/VideoRow';
import type { Video } from '@/types';
import { ScopeProvider, type Scope } from '@/lib/client/scope';
import * as api from '@/lib/client/api';

// StarRating/NoteCell/VideoQuickView call useRouter() (redirect to /login on UnauthorizedError) —
// every render needs an app-router context, which jsdom doesn't provide.
jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: jest.fn() }),
}));

// This codebase's `lib/client/api` module compiles named exports as non-configurable getters
// (Next's SWC ESM->CJS transform), so `jest.spyOn(realModule, 'fn')` throws "Cannot redefine
// property" — mock the module via a jest.mock factory instead (see share-dialog.test.tsx). Keep
// every other export real (summaryHref is used synchronously by VideoMenu to build hrefs; the
// row also renders StarRating/NoteCell/VideoQuickView, which import saveAnnotation/getQuickView
// from the same module) and override only createShare, which this test needs to control.
jest.mock('@/lib/client/api', () => ({
  ...jest.requireActual('@/lib/client/api'),
  createShare: jest.fn(),
}));

const createShareMock = api.createShare as jest.MockedFunction<typeof api.createShare>;

const PID = '11111111-1111-1111-1111-111111111111';
const CLOUD_SCOPE: Scope = { mode: 'cloud', playlistId: PID };

function renderCloudRow(overrides: Partial<Video> = {}) {
  const video: Video = {
    id: 'abc123',
    title: 'Test Video Title',
    youtubeUrl: 'https://www.youtube.com/watch?v=abc123',
    language: 'en',
    durationSeconds: 300,
    archived: false,
    ratings: {
      usefulness: 4,
      depth: 3,
      originality: 5,
      recency: 2,
      completeness: 3,
    },
    overallScore: 3.4,
    summaryMd: 'summary.md',
    processedAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
  return render(
    <ScopeProvider scope={CLOUD_SCOPE}>
      <table>
        <tbody>
          <VideoRow
            video={video}
            rank={1}
            dimUnscored={false}
            onArchive={jest.fn()}
            onGenerateHtml={jest.fn()}
            onAnnotationChange={jest.fn()}
          />
        </tbody>
      </table>
    </ScopeProvider>,
  );
}

beforeEach(() => {
  createShareMock.mockReset();
});

test('cloud: Share… opens ShareDialog; closing restores focus to the ☰ trigger', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  renderCloudRow({ summaryReady: true } as Partial<Video>);

  fireEvent.click(screen.getByRole('button', { name: /menu/i })); // open ☰
  fireEvent.click(screen.getByRole('button', { name: /share/i })); // Share…
  expect(await screen.findByRole('dialog')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /close/i }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(screen.getByRole('button', { name: /menu/i })).toHaveFocus(); // focus restored
});
