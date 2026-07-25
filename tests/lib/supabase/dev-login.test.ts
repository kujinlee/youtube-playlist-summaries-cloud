import { devLoginEnabled } from '@/lib/supabase/dev-login';

const prior = { flag: process.env.DEV_LOGIN_ENABLED, url: process.env.NEXT_PUBLIC_SUPABASE_URL };
function setEnv(flag: string | undefined, url: string | undefined) {
  if (flag === undefined) delete process.env.DEV_LOGIN_ENABLED; else process.env.DEV_LOGIN_ENABLED = flag;
  if (url === undefined) delete process.env.NEXT_PUBLIC_SUPABASE_URL; else process.env.NEXT_PUBLIC_SUPABASE_URL = url;
}
beforeEach(() => setEnv(undefined, undefined));   // deterministic default: gate closed, no ambient dependency
afterEach(() => setEnv(prior.flag, prior.url));

describe('devLoginEnabled', () => {
  it('false when the flag is unset (production state)', () => {
    setEnv(undefined, 'http://127.0.0.1:54321');
    expect(devLoginEnabled()).toBe(false);
  });
  it('false when the flag is set but the URL is not local (defense-in-depth)', () => {
    setEnv('true', 'https://uykwcybxqgewmbltroxf.supabase.co');
    expect(devLoginEnabled()).toBe(false);
  });
  it('false when the flag is truthy-but-not-exactly "true"', () => {
    setEnv('1', 'http://127.0.0.1:54321');
    expect(devLoginEnabled()).toBe(false);
    setEnv('yes', 'http://127.0.0.1:54321');
    expect(devLoginEnabled()).toBe(false);
  });
  it('true only when flag === "true" AND the URL is local', () => {
    setEnv('true', 'http://127.0.0.1:54321');
    expect(devLoginEnabled()).toBe(true);
    setEnv('true', 'http://localhost:54321');
    expect(devLoginEnabled()).toBe(true);
  });
});
