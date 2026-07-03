import * as os from 'os';
import * as path from 'path';
import { getPrincipal, getMetadataStore } from '@/lib/storage/resolve';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';

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
