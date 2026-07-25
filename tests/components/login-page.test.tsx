/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginPage from '../../app/login/page';

const signInWithOAuth = jest.fn();

jest.mock('../../lib/supabase/client', () => ({
  createClient: () => ({ auth: { signInWithOAuth } }),
}));

describe('LoginPage', () => {
  const priorUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  beforeEach(() => {
    signInWithOAuth.mockReset();
    signInWithOAuth.mockResolvedValue({ error: null });
    delete process.env.NEXT_PUBLIC_SUPABASE_URL; // deterministic default: dev link hidden
  });
  afterEach(() => {
    if (priorUrl === undefined) delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    else process.env.NEXT_PUBLIC_SUPABASE_URL = priorUrl;
  });

  it('shows a "Local dev sign-in" link to /dev-login when the Supabase URL is local', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://127.0.0.1:54321';
    render(<LoginPage />);
    expect(screen.getByRole('link', { name: /dev sign-in/i })).toHaveAttribute('href', '/dev-login');
  });

  it('hides the dev link when the Supabase URL is prod-like', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://uykwcybxqgewmbltroxf.supabase.co';
    render(<LoginPage />);
    expect(screen.queryByRole('link', { name: /dev sign-in/i })).toBeNull();
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
