// Node-env test (no jsdom directive): calls the async server component as a function and
// asserts the notFound() gate. Lives in tests/components/ because the jest testMatch covers
// tests/components/**/*.test.tsx (not tests/app/**).
const notFound = jest.fn(() => { throw new Error('NEXT_NOT_FOUND'); });
jest.mock('next/navigation', () => ({ notFound: () => notFound() }));
// stub the client form so this node-env test has no browser deps
jest.mock('@/components/DevLoginForm', () => ({ DevLoginForm: () => null }));

import DevLoginPage from '@/app/dev-login/page';

const prior = { flag: process.env.DEV_LOGIN_ENABLED, url: process.env.NEXT_PUBLIC_SUPABASE_URL };
function setEnv(flag: string | undefined, url: string | undefined) {
  if (flag === undefined) delete process.env.DEV_LOGIN_ENABLED; else process.env.DEV_LOGIN_ENABLED = flag;
  if (url === undefined) delete process.env.NEXT_PUBLIC_SUPABASE_URL; else process.env.NEXT_PUBLIC_SUPABASE_URL = url;
}
beforeEach(() => { jest.clearAllMocks(); setEnv(undefined, undefined); }); // gate closed by default
afterEach(() => setEnv(prior.flag, prior.url));

describe('GET /dev-login gate', () => {
  it('404s when the flag is unset (production state), even with a local URL', async () => {
    setEnv(undefined, 'http://127.0.0.1:54321');
    await expect(DevLoginPage()).rejects.toThrow('NEXT_NOT_FOUND');
    expect(notFound).toHaveBeenCalledTimes(1);
  });

  it('404s when the flag is set but the URL is prod-like (defense-in-depth)', async () => {
    setEnv('true', 'https://uykwcybxqgewmbltroxf.supabase.co');
    await expect(DevLoginPage()).rejects.toThrow('NEXT_NOT_FOUND');
    expect(notFound).toHaveBeenCalledTimes(1);
  });

  it('renders (does NOT 404) when flag set AND URL local', async () => {
    setEnv('true', 'http://127.0.0.1:54321');
    const el = await DevLoginPage();
    expect(notFound).not.toHaveBeenCalled();
    expect(el).toBeTruthy();
  });
});
