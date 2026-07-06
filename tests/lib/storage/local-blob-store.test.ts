import fs from 'fs'; import os from 'os'; import path from 'path';
import { LocalFsBlobStore } from '@/lib/storage/local/local-blob-store';
import { localPrincipal } from '@/lib/storage/principal';

const store = new LocalFsBlobStore();
const p = () => localPrincipal(fs.mkdtempSync(path.join(os.tmpdir(), 'lbs-')));

afterEach(() => {
  // clean up any lbs- dirs left under tmpdir by this test run
  const dirs = fs.readdirSync(os.tmpdir()).filter(d => d.startsWith('lbs-'));
  for (const d of dirs) fs.rmSync(path.join(os.tmpdir(), d), { recursive: true, force: true });
});

test('put then get round-trips; get on absent key is null', async () => {
  const pr = p();
  await store.put(pr, 'a/b.md', Buffer.from('hi'), 'text/markdown');
  expect((await store.get(pr, 'a/b.md'))?.toString()).toBe('hi');
  expect(await store.get(pr, 'missing.md')).toBeNull();
});

test('put writes atomically under indexKey (byte-for-byte layout)', async () => {
  const pr = p();
  await store.put(pr, 'models/x.json', Buffer.from('{}'), 'application/json');
  expect(fs.existsSync(path.join(pr.indexKey, 'models/x.json'))).toBe(true);
});

test('putStaged + promote makes the final key readable', async () => {
  const pr = p();
  const ref = await store.putStaged(pr, 'out.html', Buffer.from('<x>'), 'text/html');
  expect(await store.get(pr, 'out.html')).toBeNull();     // not visible before promote
  await store.promote(ref);
  expect((await store.get(pr, 'out.html'))?.toString()).toBe('<x>');
});

test('rejects traversal keys — put', async () => {
  await expect(store.put(p(), '../escape', Buffer.from('x'), 'text/plain')).rejects.toThrow();
  await expect(store.put(p(), '/absolute', Buffer.from('x'), 'text/plain')).rejects.toThrow();
  await expect(store.put(p(), 'a/../../etc', Buffer.from('x'), 'text/plain')).rejects.toThrow();
});

test('rejects traversal keys — putStaged', async () => {
  await expect(store.putStaged(p(), '../escape', Buffer.from('x'), 'text/plain')).rejects.toThrow();
  await expect(store.putStaged(p(), '/absolute', Buffer.from('x'), 'text/plain')).rejects.toThrow();
  await expect(store.putStaged(p(), 'a/../../etc', Buffer.from('x'), 'text/plain')).rejects.toThrow();
});
