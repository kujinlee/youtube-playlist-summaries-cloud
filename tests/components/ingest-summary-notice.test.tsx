/** @jest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import { IngestSummaryNotice } from '@/components/cloud/IngestSummaryNotice';

const base = { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 };
const result = (over: any = {}) => ({ playlistId: 'p', jobs: [], challengeRequired: false, counts: { ...base, ...over.counts }, ...over });

describe('IngestSummaryNotice', () => {
  it('renders the bucket line', () => {
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 42, skipped: 3 } })} onDismiss={() => {}} />);
    expect(screen.getByText(/Queued 42 · 3 skipped \(no captions\)/)).toBeInTheDocument();
  });
  it('renders the soft challenge line when challengeRequired', () => {
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 }, challengeRequired: true })} onDismiss={() => {}} />);
    expect(screen.getByText("You're adding playlists quickly.")).toBeInTheDocument();
  });
  it('omits the challenge line otherwise', () => {
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 } })} onDismiss={() => {}} />);
    expect(screen.queryByText("You're adding playlists quickly.")).not.toBeInTheDocument();
  });
  it('calls onDismiss when ✕ clicked', () => {
    const onDismiss = jest.fn();
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 } })} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
