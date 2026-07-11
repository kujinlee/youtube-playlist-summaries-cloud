/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginPage from '../../app/login/page';

const signInWithOAuth = jest.fn();

jest.mock('../../lib/supabase/client', () => ({
  createClient: () => ({ auth: { signInWithOAuth } }),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    signInWithOAuth.mockReset();
    signInWithOAuth.mockResolvedValue({ error: null });
  });

  it('renders "Continue with Google"', () => {
    render(<LoginPage />);
    expect(screen.getByText(/Continue with Google/i)).toBeInTheDocument();
  });

  it('calls signInWithOAuth with provider google and redirectTo ending in /auth/callback?next=/', async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByText(/Continue with Google/i));

    await waitFor(() => expect(signInWithOAuth).toHaveBeenCalledTimes(1));

    const arg = signInWithOAuth.mock.calls[0][0];
    expect(arg.provider).toBe('google');
    expect(arg.options.redirectTo).toMatch(/\/auth\/callback\?next=\/$/);
    expect(arg.options.redirectTo).toBe(`${window.location.origin}/auth/callback?next=/`);
  });

  it('shows an error message when signInWithOAuth resolves with an error', async () => {
    signInWithOAuth.mockResolvedValue({ error: { message: 'OAuth failed' } });
    render(<LoginPage />);
    fireEvent.click(screen.getByText(/Continue with Google/i));

    expect(await screen.findByText(/OAuth failed/i)).toBeInTheDocument();
  });
});
