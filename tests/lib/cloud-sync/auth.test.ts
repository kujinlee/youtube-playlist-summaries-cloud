import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';

function memStore(initial: string | null = null): TokenStore {
  let t = initial;
  return { read: async () => t, write: async (x) => { t = x; }, clear: async () => { t = null; } };
}

describe('getAuthedClient', () => {
  it('throws NoSessionError with a login hint when no token is stored', async () => {
    await expect(getAuthedClient(memStore(null))).rejects.toBeInstanceOf(NoSessionError);
    await expect(getAuthedClient(memStore(null))).rejects.toThrow(/cloud-sync login/);
  });
});
