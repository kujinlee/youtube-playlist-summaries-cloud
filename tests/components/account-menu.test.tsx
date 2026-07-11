/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AccountMenu from '@/components/cloud/AccountMenu';

const replace = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
}));

const signOut = jest.fn();
jest.mock('@/lib/supabase/client', () => ({
  createClient: () => ({ auth: { signOut } }),
}));

const EMAIL = 'you@email.com';

beforeEach(() => {
  jest.clearAllMocks();
  signOut.mockResolvedValue({ error: null });
});

function openMenu() {
  fireEvent.click(screen.getByRole('button', { name: new RegExp(EMAIL) }));
}

it('shows the trigger button with the signed-in email', () => {
  render(<AccountMenu email={EMAIL} />);
  expect(screen.getByRole('button', { name: new RegExp(EMAIL) })).toBeInTheDocument();
});

it('clicking the trigger opens the dropdown with the email and "Sign out"', () => {
  render(<AccountMenu email={EMAIL} />);
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();

  openMenu();

  expect(screen.getByRole('menu')).toBeInTheDocument();
  expect(screen.getByRole('menuitem', { name: /sign out/i })).toBeInTheDocument();
  // Email appears both in the trigger and the dropdown header.
  expect(screen.getAllByText(EMAIL).length).toBeGreaterThanOrEqual(2);
});

// ── Dismissal path (a): click outside ────────────────────────────────────────
it('click outside the menu closes it without calling signOut', () => {
  render(
    <div>
      <div data-testid="outside">outside</div>
      <AccountMenu email={EMAIL} />
    </div>,
  );
  openMenu();
  expect(screen.getByRole('menu')).toBeInTheDocument();

  fireEvent.mouseDown(screen.getByTestId('outside'));

  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  expect(signOut).not.toHaveBeenCalled();
  expect(replace).not.toHaveBeenCalled();
});

// ── Dismissal path (b): Escape key ───────────────────────────────────────────
it('pressing Escape closes the menu without calling signOut', () => {
  render(<AccountMenu email={EMAIL} />);
  openMenu();
  expect(screen.getByRole('menu')).toBeInTheDocument();

  fireEvent.keyDown(window, { key: 'Escape' });

  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  expect(signOut).not.toHaveBeenCalled();
  expect(replace).not.toHaveBeenCalled();
});

// ── Dismissal path (c): selecting "Sign out" ─────────────────────────────────
it('selecting "Sign out" calls signOut(), redirects to /login, and closes the menu', async () => {
  render(<AccountMenu email={EMAIL} />);
  openMenu();

  fireEvent.click(screen.getByRole('menuitem', { name: /sign out/i }));

  await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
});
