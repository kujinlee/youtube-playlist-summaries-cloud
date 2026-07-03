import * as os from 'os';
import * as path from 'path';
import { getPrincipal, getMetadataStore, getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';

afterEach(() => {
  delete process.env.STORAGE_BACKEND;
  delete process.env.NEXT_PUBLIC_SUPABASE_URL;
  delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
});

it('getPrincipal accepts a folder under home and preserves the RAW indexKey string', () => {
  const dir = path.join(os.homedir(), '.test-resolve-ok');
  const p = getPrincipal(dir);
  expect(p.id).toBe('local');
  // MUST be the raw string, NOT path.resolve(dir): index-store uses the raw
  // indexKey for the file path; resolving here would change persisted
  // values and break mocked-arg assertions. (Codex Blocking)
  expect(p.indexKey).toBe(dir);
});

it('getPrincipal rejects a folder outside home (guard preserved)', () => {
  expect(() => getPrincipal('/etc')).toThrow();
});

it('getMetadataStore returns the local store implementation', () => {
  expect(getMetadataStore()).toBeInstanceOf(LocalFsMetadataStore);
});

test('defaults to the local bundle', () => {
  const { metadataStore, blobStore } = getStorageBundle();
  expect(metadataStore).toBeInstanceOf(LocalFsMetadataStore);
  expect(blobStore).toBeDefined();
});

test('supabase backend without a client throws (routes not wired in 1C)', () => {
  process.env.STORAGE_BACKEND = 'supabase';
  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://x'; process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'k';
  expect(() => getStorageBundle()).toThrow(/authenticated client/);
});

test('supabase backend with missing env fails fast', () => {
  process.env.STORAGE_BACKEND = 'supabase';
  delete process.env.NEXT_PUBLIC_SUPABASE_URL;
  expect(() => getStorageBundle({ supabaseClient: {} as any })).toThrow(/Missing required env/);
});

test('getPrincipalFromSession hard-fails when cloud backend but no session', () => {
  process.env.STORAGE_BACKEND = 'supabase';
  expect(() => getPrincipalFromSession({ userId: null }, 'listX')).toThrow(/no authenticated/i);
});
