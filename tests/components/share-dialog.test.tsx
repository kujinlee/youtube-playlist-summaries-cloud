/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor, act, cleanup } from '@testing-library/react';
import ShareDialog from '@/components/cloud/ShareDialog';
import { createShare, revokeShare, UnauthorizedError, type CreateShareResult } from '@/lib/client/api';

// NOTE: this codebase's `lib/client/api` module compiles named exports as non-configurable
// getters (Next's SWC ESM->CJS transform), so `jest.spyOn(realModule, 'fn')` throws
// "Cannot redefine property" — every other component test in tests/components/ mocks this
// module via a `jest.mock` factory instead (see new-playlist-modal.test.tsx, cloud-app.test.tsx).
// Mirror that convention here rather than spying on the real module.
const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return {
    createShare: jest.fn(),
    revokeShare: jest.fn(),
    UnauthorizedError,
  };
});

const createShareMock = createShare as jest.MockedFunction<typeof createShare>;
const revokeShareMock = revokeShare as jest.MockedFunction<typeof revokeShare>;

const baseProps = { playlistId: 'p1', videoId: 'v1', videoTitle: 'How Transformers Work', onClose: jest.fn() };

beforeEach(() => {
  createShareMock.mockReset();
  revokeShareMock.mockReset();
  replace.mockReset();
  baseProps.onClose = jest.fn();
});

test('before create: shows "No link yet" + Create link; default TTL 30d selected', () => {
  render(<ShareDialog {...baseProps} />);
  expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  expect(screen.getByRole('radio', { name: /30d/i })).toBeChecked();
  expect(screen.getByRole('button', { name: /create link/i })).toBeEnabled();
});

test('create success: URL populated, Copy + Revoke enabled, stays open', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(screen.getByDisplayValue(/\/s\/tok$/)).toBeInTheDocument());
  expect(createShareMock).toHaveBeenCalledWith('p1', 'v1', 30);
  expect(screen.getByRole('button', { name: /copy/i })).toBeEnabled();
  expect(screen.getByRole('button', { name: /revoke/i })).toBeEnabled();
  expect(baseProps.onClose).not.toHaveBeenCalled();
});

test('TTL Never → createShare called with "never"', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('radio', { name: /never/i }));
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(createShareMock).toHaveBeenCalledWith('p1', 'v1', 'never'));
});

test('create error → inline role=alert, stays open', async () => {
  createShareMock.mockRejectedValue(new Error('bad request'));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/bad request/i));
  expect(baseProps.onClose).not.toHaveBeenCalled();
});

test('create 401 → router.replace(/login)', async () => {
  createShareMock.mockRejectedValue(new UnauthorizedError('unauthorized'));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
});

test('copy success → clipboard write + "Copied" live region', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  const writeText = jest.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /copy/i }));
  fireEvent.click(screen.getByRole('button', { name: /copy/i }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining('/s/tok')));
  await waitFor(() => expect(screen.getByText(/copied/i)).toBeInTheDocument());
});

test('copy failure → falls back to selecting URL text, no throw', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  const writeText = jest.fn().mockRejectedValue(new Error('denied'));
  Object.assign(navigator, { clipboard: { writeText } });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /copy/i }));
  const input = screen.getByDisplayValue(/\/s\/tok$/) as HTMLInputElement;
  const select = jest.spyOn(input, 'select');
  fireEvent.click(screen.getByRole('button', { name: /copy/i }));
  await waitFor(() => expect(select).toHaveBeenCalled());
});

test('revoke success → clears held share, back to "No link yet"', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  revokeShareMock.mockResolvedValue({ revoked: true });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));
  await waitFor(() => expect(revokeShareMock).toHaveBeenCalledWith('s1'));
  await waitFor(() => expect(screen.queryByDisplayValue(/\/s\/tok$/)).not.toBeInTheDocument());
});

test('revoke 401 → router.replace(/login)', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  revokeShareMock.mockRejectedValue(new UnauthorizedError('unauthorized'));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));
  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
});

test('revoke error → inline role=alert, stays open', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  revokeShareMock.mockRejectedValue(new Error('revoke failed'));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/revoke failed/i));
  expect(baseProps.onClose).not.toHaveBeenCalled();
});

test('dismissal: ✕/Close, Escape, backdrop all call onClose', () => {
  // Three independent dismissal mechanisms are exercised in one test block; each render() must be
  // torn down before the next (RTL's automatic afterEach cleanup only runs between `test()` blocks,
  // not between renders within the same block), otherwise stale dialogs from earlier renders make
  // getByRole('dialog') ambiguous.
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /close/i }));
  expect(baseProps.onClose).toHaveBeenCalledTimes(1);
  cleanup();

  baseProps.onClose = jest.fn();
  render(<ShareDialog {...baseProps} />);
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(baseProps.onClose).toHaveBeenCalledTimes(1);
  cleanup();

  baseProps.onClose = jest.fn();
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByTestId('share-dialog-backdrop'));
  expect(baseProps.onClose).toHaveBeenCalledTimes(1);
});

test('backdrop + Escape are inert while create is in flight', async () => {
  let resolve!: (v: CreateShareResult) => void;
  createShareMock.mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  // in flight now:
  fireEvent.click(screen.getByTestId('share-dialog-backdrop'));
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(baseProps.onClose).not.toHaveBeenCalled();
  await act(async () => { resolve({ id: 's1', token: 't', url: '/s/t', expiresAt: null }); });
});

test('TTL 7d → createShare called with 7', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('radio', { name: /7d/i }));
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(createShareMock).toHaveBeenCalledWith('p1', 'v1', 7));
});

test('rapid double-click Create fires createShare exactly once (synchronous in-flight guard)', async () => {
  let resolve!: (v: CreateShareResult) => void;
  createShareMock.mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  const btn = screen.getByRole('button', { name: /create link/i });
  fireEvent.click(btn);
  fireEvent.click(btn);   // second click while first is pending
  expect(createShareMock).toHaveBeenCalledTimes(1);
  await act(async () => { resolve({ id: 's1', token: 't', url: '/s/t', expiresAt: null }); });
});

test('rapid double-click Revoke fires revokeShare exactly once', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  let resolve!: (v: { revoked: boolean }) => void;
  revokeShareMock.mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  const rb = screen.getByRole('button', { name: /revoke/i });
  fireEvent.click(rb);
  fireEvent.click(rb);
  expect(revokeShareMock).toHaveBeenCalledTimes(1);
  await act(async () => { resolve({ revoked: true }); });
});

test('backdrop + Escape are inert while REVOKE is in flight', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  let resolve!: (v: { revoked: boolean }) => void;
  revokeShareMock.mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));   // revoke pending
  fireEvent.click(screen.getByTestId('share-dialog-backdrop'));
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(baseProps.onClose).not.toHaveBeenCalled();
  await act(async () => { resolve({ revoked: true }); });
});

test('a11y: initial focus lands in the dialog; Tab from the last focusable wraps to the first', () => {
  // The trap is a manual keydown handler (mirroring NewPlaylistModal:29-41): it only wraps when
  // document.activeElement === last (Tab) or === first (Shift+Tab). jsdom does NOT move focus on a
  // Tab keydown by itself, so the test must FOCUS the last element first to exercise the wrap branch —
  // otherwise the handler is a no-op and the assertion is vacuous.
  render(<ShareDialog {...baseProps} />);
  const dialog = screen.getByRole('dialog');
  expect(dialog.contains(document.activeElement)).toBe(true);        // initial focus inside dialog
  // Use the EXACT selector the trap handler uses (copy from NewPlaylistModal:25 into ShareDialog),
  // so the test's first/last match the handler's — including the `:not([disabled])` exclusion, since
  // Copy/Revoke render disabled before Create and would otherwise skew last (Codex R3 finding):
  const SEL = 'button:not([disabled]), input:not([disabled]), [href], textarea, select';
  const focusables = Array.from(dialog.querySelectorAll<HTMLElement>(SEL));
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  last.focus();
  fireEvent.keyDown(dialog, { key: 'Tab' });
  expect(document.activeElement).toBe(first);                        // wrapped to first (not <body>)
});

test('revoke no-op ({revoked:false}) still clears the held share (acceptable for 2c)', async () => {
  createShareMock.mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  revokeShareMock.mockResolvedValue({ revoked: false });  // already-revoked / non-owned
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));
  await waitFor(() => expect(screen.queryByDisplayValue(/\/s\/tok$/)).not.toBeInTheDocument());
});
