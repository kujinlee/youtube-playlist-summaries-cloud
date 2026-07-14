/** @jest-environment jsdom */
/**
 * Stage: playlist-sidebar-ux T10. Confirm-delete modal — modeled on NewPlaylistModal
 * (tests/components/new-playlist-modal.test.tsx: focus trap, Esc, returnFocus, submit
 * guard). See docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md Task 10
 * Enumerated Behaviors (#2-#9) and docs/superpowers/specs/...-design.md §B7 Overlay
 * Dismissal table.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DeletePlaylistDialog } from '@/components/cloud/DeletePlaylistDialog';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace, push: jest.fn() }) }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return { deletePlaylist: jest.fn(), UnauthorizedError };
});
import { deletePlaylist, UnauthorizedError } from '@/lib/client/api';
const deletePlaylistMock = deletePlaylist as jest.MockedFunction<typeof deletePlaylist>;

beforeEach(() => jest.clearAllMocks());

function clickDelete() {
  fireEvent.click(screen.getByRole('button', { name: /^delete$/i }));
}

describe('DeletePlaylistDialog', () => {
  // Behavior 9: copy shows the playlist title + "cannot be undone".
  it('shows the playlist title and "cannot be undone" copy', () => {
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={() => {}} onDeleted={() => {}} />);
    expect(screen.getByText(/ML Talks/)).toBeInTheDocument();
    expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument();
  });

  // Behaviors 2-5: each dismissal path closes without deleting.
  it('closes via Cancel, Escape, backdrop, and ✕ when not deleting — no delete call', () => {
    const onClose = jest.fn();
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={onClose} onDeleted={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('delete-modal-backdrop'));
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(4);
    expect(deletePlaylistMock).not.toHaveBeenCalled();
  });

  it('Cancel returns focus to the previously focused trigger element', () => {
    const trigger = document.createElement('button');
    document.body.appendChild(trigger);
    trigger.focus();
    const onClose = jest.fn(() => unmount());
    const { unmount } = render(
      <DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={onClose} onDeleted={() => {}} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(document.activeElement).toBe(trigger);
    document.body.removeChild(trigger);
  });

  // Behavior 6: all dismissal paths are no-ops while deleting.
  it('disables ALL dismissal paths while deleting', async () => {
    let resolve!: () => void;
    deletePlaylistMock.mockReturnValue(new Promise((r) => { resolve = r as () => void; }));
    const onClose = jest.fn();
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={onClose} onDeleted={() => {}} />);
    clickDelete();
    await waitFor(() => expect(screen.getByRole('button', { name: /deleting/i })).toBeDisabled());
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('delete-modal-backdrop'));
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
    resolve();
  });

  // Behavior 7: success closes and calls onDeleted.
  it('on success: shows "Deleting…" then calls onDeleted with the playlist id', async () => {
    deletePlaylistMock.mockResolvedValue(undefined);
    const onDeleted = jest.fn();
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={() => {}} onDeleted={onDeleted} />);
    clickDelete();
    expect(await screen.findByRole('button', { name: /deleting/i })).toBeInTheDocument();
    await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
    expect(deletePlaylistMock).toHaveBeenCalledWith('p1');
  });

  // Behavior 8: error keeps modal open, inline error, buttons re-enabled.
  it('on error: inline error shown, modal stays open, buttons re-enabled', async () => {
    deletePlaylistMock.mockRejectedValue(new Error('boom'));
    const onDeleted = jest.fn();
    const onClose = jest.fn();
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={onClose} onDeleted={onDeleted} />);
    clickDelete();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
    expect(onDeleted).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeEnabled();
  });

  it('redirects to /login on UnauthorizedError instead of showing an inline error', async () => {
    const { UnauthorizedError: MockUnauthorized } = jest.requireMock('@/lib/client/api');
    deletePlaylistMock.mockRejectedValue(new MockUnauthorized('x'));
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={() => {}} onDeleted={() => {}} />);
    clickDelete();
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });

  it('guards against double-submit — two rapid Delete clicks call deletePlaylist once', () => {
    let resolve!: () => void;
    deletePlaylistMock.mockReturnValue(new Promise((r) => { resolve = r as () => void; }));
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={() => {}} onDeleted={() => {}} />);
    const deleteButton = screen.getByRole('button', { name: /^delete$/i });
    fireEvent.click(deleteButton);
    fireEvent.click(deleteButton);
    expect(deletePlaylistMock).toHaveBeenCalledTimes(1);
    resolve();
  });

  it('traps focus: Tab from the last focusable wraps to the first', () => {
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={() => {}} onDeleted={() => {}} />);
    const dialog = screen.getByRole('dialog');
    const focusables = dialog.querySelectorAll<HTMLElement>('button:not([disabled]), [href], textarea, select');
    const last = focusables[focusables.length - 1];
    last.focus();
    fireEvent.keyDown(dialog, { key: 'Tab' });
    expect(document.activeElement).toBe(focusables[0]);
  });

  it('default focus is on Cancel when the dialog opens', () => {
    render(<DeletePlaylistDialog playlistId="p1" playlistTitle="ML Talks" onClose={() => {}} onDeleted={() => {}} />);
    expect(document.activeElement).toBe(screen.getByRole('button', { name: /cancel/i }));
  });
});
