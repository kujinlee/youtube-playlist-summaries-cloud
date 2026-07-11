/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NewPlaylistModal } from '@/components/cloud/NewPlaylistModal';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace, push: jest.fn() }) }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  class IngestError extends Error { constructor(public status: number, public info: any = {}) { super('e'); } }
  return { createIngest: jest.fn(), ingestErrorMessage: (e: any) => `msg-${e.status}`, UnauthorizedError, IngestError };
});
import { createIngest, IngestError } from '@/lib/client/api';
const createIngestMock = createIngest as jest.MockedFunction<typeof createIngest>;

const okResult = (playlistId: string | null) => ({
  playlistId, jobs: [], challengeRequired: false,
  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
});

beforeEach(() => jest.clearAllMocks());

function fillAndSubmit(url = 'https://youtube.com/playlist?list=X') {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: url } });
  fireEvent.click(screen.getByRole('button', { name: /add/i }));
}

describe('NewPlaylistModal', () => {
  it('submits the URL and calls onSuccess with a non-null playlistId', async () => {
    createIngestMock.mockResolvedValue(okResult('p-uuid') as any);
    const onSuccess = jest.fn();
    render(<NewPlaylistModal onClose={() => {}} onSuccess={onSuccess} />);
    fillAndSubmit();
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(expect.objectContaining({ playlistId: 'p-uuid' })));
    expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=X');
  });

  it('stays open with a message when playlistId is null', async () => {
    createIngestMock.mockResolvedValue(okResult(null) as any);
    const onSuccess = jest.fn();
    render(<NewPlaylistModal onClose={() => {}} onSuccess={onSuccess} />);
    fillAndSubmit();
    expect(await screen.findByText('No videos could be ingested from that playlist.')).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows inline error on IngestError and stays open', async () => {
    createIngestMock.mockRejectedValue(new IngestError(422, { limit: 50, found: 80 }));
    render(<NewPlaylistModal onClose={() => {}} onSuccess={() => {}} />);
    fillAndSubmit();
    expect(await screen.findByRole('alert')).toHaveTextContent('msg-422');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('redirects to /login on UnauthorizedError', async () => {
    const { UnauthorizedError } = jest.requireMock('@/lib/client/api');
    createIngestMock.mockRejectedValue(new UnauthorizedError('x'));
    render(<NewPlaylistModal onClose={() => {}} onSuccess={() => {}} />);
    fillAndSubmit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });

  it('closes via ✕, Cancel, Escape, and backdrop when not submitting', () => {
    const onClose = jest.fn();
    render(<NewPlaylistModal onClose={onClose} onSuccess={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('modal-backdrop'));
    expect(onClose).toHaveBeenCalledTimes(4);
  });

  it('disables ALL dismissal paths while submitting', async () => {
    let resolve!: (v: any) => void;
    createIngestMock.mockReturnValue(new Promise((r) => { resolve = r; }) as any);
    const onClose = jest.fn();
    render(<NewPlaylistModal onClose={onClose} onSuccess={() => {}} />);
    fillAndSubmit();
    await waitFor(() => expect(screen.getByRole('button', { name: /add/i })).toBeDisabled());
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('modal-backdrop'));
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).not.toHaveBeenCalled();
    resolve(okResult('p'));
  });

  it('traps focus: Tab from the last focusable wraps to the first', () => {
    render(<NewPlaylistModal onClose={() => {}} onSuccess={() => {}} />);
    const dialog = screen.getByRole('dialog');
    const focusables = dialog.querySelectorAll<HTMLElement>('button, input, [href], textarea, select');
    const last = focusables[focusables.length - 1];
    last.focus();
    fireEvent.keyDown(dialog, { key: 'Tab' });
    expect(document.activeElement).toBe(focusables[0]);
  });
});
