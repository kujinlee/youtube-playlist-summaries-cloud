/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DevLoginForm } from '@/components/DevLoginForm';

const signInWithPassword = jest.fn();
const hardNavigate = jest.fn();

jest.mock('@/lib/supabase/client', () => ({
  createClient: () => ({ auth: { signInWithPassword } }),
}));
jest.mock('@/lib/navigate', () => ({ hardNavigate: (to: string) => hardNavigate(to) }));

describe('DevLoginForm', () => {
  const assign = hardNavigate; // the hard-nav seam (mocked)
  beforeEach(() => {
    signInWithPassword.mockReset().mockResolvedValue({ error: null });
    hardNavigate.mockReset();
  });

  it('submits the entered email+password and hard-navigates to / on success', async () => {
    render(<DevLoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'sync-test@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pw123' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() =>
      expect(signInWithPassword).toHaveBeenCalledWith({ email: 'sync-test@example.com', password: 'pw123' }),
    );
    await waitFor(() => expect(assign).toHaveBeenCalledWith('/'));
  });

  it('shows the error message and does NOT navigate when sign-in fails', async () => {
    signInWithPassword.mockResolvedValue({ error: { message: 'Invalid login credentials' } });
    render(<DevLoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'x@y.z' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'bad' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText(/Invalid login credentials/i)).toBeInTheDocument();
    expect(assign).not.toHaveBeenCalled();
  });

  it('disables the submit button while the sign-in request is in flight (no double-submit)', async () => {
    let resolve: (v: { error: null }) => void = () => {};
    signInWithPassword.mockReturnValue(new Promise((r) => { resolve = r; }));
    render(<DevLoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.c' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pw' } });
    const button = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(button);

    await waitFor(() => expect(button).toBeDisabled());   // pending state during flight
    resolve({ error: null });                              // let it finish
  });
});
