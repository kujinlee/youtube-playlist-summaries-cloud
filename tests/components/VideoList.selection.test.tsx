/** @jest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import VideoList from '../../components/VideoList';
import type { Video } from '../../types';
import { ScopeProvider, type Scope } from '../../lib/client/scope';

function v(id: string, over: Partial<Video> = {}): Video {
  return {
    id, title: `T${id}`, youtubeUrl: `https://youtu.be/${id}`, language: 'en', durationSeconds: 1,
    archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
    overallScore: 3, summaryMd: `${id}.md`,
    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
    ...over,
  } as Video;
}

const baseProps = {
  outputFolder: '/p', baseOutputFolder: '/p', showArchive: true,
  onArchive: () => {}, onGenerateHtml: () => {},
  selected: new Set<string>(), onToggleSelect: () => {}, onSelectAllNeeding: () => {},
};

const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/p', baseOutputFolder: '/p' };

// VideoList renders real VideoRow rows here (not mocked), whose leaf components
// (StarRating/NoteCell/VideoQuickView) call useScope() — every render needs a ScopeProvider.
function renderList(props: React.ComponentProps<typeof VideoList>) {
  return render(
    <ScopeProvider scope={LOCAL_SCOPE}>
      <VideoList {...props} />
    </ScopeProvider>,
  );
}

it('CA1: clicking a row checkbox calls onToggleSelect with the videoId', () => {
  const onToggleSelect = jest.fn();
  renderList({ ...baseProps, videos: [v('a')], onToggleSelect });
  fireEvent.click(screen.getByLabelText('Select Ta'));
  expect(onToggleSelect).toHaveBeenCalledWith('a');
});

it('CA2: a row with no summaryMd has a disabled checkbox', () => {
  renderList({ ...baseProps, videos: [v('a', { summaryMd: null })] });
  expect(screen.getByLabelText('Select Ta')).toBeDisabled();
});

it('CA3: header select-all calls onSelectAllNeeding with only missing/stale visible rows', () => {
  const onSelectAllNeeding = jest.fn();
  const videos = [
    v('a', { summaryHtml: null }),                                   // needs work
    v('b', { summaryHtml: 'b.html', docVersion: { major: 3, minor: 3 } }), // current
    v('c', { summaryMd: null }),                                     // not selectable
  ];
  renderList({ ...baseProps, videos, onSelectAllNeeding });
  fireEvent.click(screen.getByLabelText('Select all needing generation'));
  const arg = onSelectAllNeeding.mock.calls[0][0] as Video[];
  expect(arg.map((x) => x.id)).toEqual(['a']);
});

it('CA1: header checkbox is checked when all needing rows are selected', () => {
  const videos = [v('a', { summaryHtml: null })];
  renderList({ ...baseProps, videos, selected: new Set(['a']) });
  expect(screen.getByLabelText('Select all needing generation')).toBeChecked();
});

it('H3: a row in the active batch has a disabled checkbox', () => {
  renderList({ ...baseProps, videos: [v('a')], activeBatchVideoIds: new Set(['a']) });
  expect(screen.getByLabelText('Select Ta')).toBeDisabled();
});
