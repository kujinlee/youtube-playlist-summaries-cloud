import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { makeFileTokenStore } from '@/lib/cloud-sync/auth';

it('writes the token file with mode 600', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'cs-tok-'));
  const store = makeFileTokenStore(path.join(dir, 'token'));
  await store.write('abc');
  const st = await fs.stat(path.join(dir, 'token'));
  expect(st.mode & 0o777).toBe(0o600);
  expect(await store.read()).toBe('abc');
});

it('refuses to read a world/group-readable token file (fail-closed)', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'cs-tok-'));
  const sub = path.join(dir, 'store');
  await fs.mkdir(sub, { mode: 0o700 });
  const file = path.join(sub, 'token');
  await fs.writeFile(file, 'abc', { mode: 0o644 });
  const store = makeFileTokenStore(file);
  await expect(store.read()).rejects.toThrow(/permission/i);
});

it('refuses to read when the parent directory is group/other-writable (High ⑥)', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'cs-tok-'));
  const sub = path.join(dir, 'store');
  await fs.mkdir(sub, { mode: 0o777 });
  await fs.chmod(sub, 0o777);
  await fs.writeFile(path.join(sub, 'token'), 'abc', { mode: 0o600 });
  const store = makeFileTokenStore(path.join(sub, 'token'));
  await expect(store.read()).rejects.toThrow(/group\/other-writable|not owned/i);
});

it('refuses to WRITE into a pre-existing group/other-writable parent — no chmod laundering (round-2 H2)', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'cs-tok-'));
  const sub = path.join(dir, 'store');
  await fs.mkdir(sub, { mode: 0o777 });
  await fs.chmod(sub, 0o777);
  const store = makeFileTokenStore(path.join(sub, 'token'));
  await expect(store.write('abc')).rejects.toThrow(/group\/other-writable|not owned/i);
});
