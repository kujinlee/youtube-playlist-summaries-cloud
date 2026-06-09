import fs from 'fs';
import { normalizeToRoot } from '../../lib/output-folder';

jest.mock('fs');
const mockExists = fs.existsSync as jest.Mock;

// existsSync returns true only for the listed absolute paths
function existsFor(paths: string[]) {
  const set = new Set(paths);
  mockExists.mockImplementation((p: string) => set.has(p));
}

describe('normalizeToRoot', () => {
  beforeEach(() => jest.clearAllMocks());

  it('returns the data root unchanged (no index, no raw/)', () => {
    existsFor([]);
    expect(normalizeToRoot('/d')).toBe('/d');
  });

  it('strips a trailing /raw and goes up to the root', () => {
    existsFor(['/d/slug/raw/playlist-index.json']);
    expect(normalizeToRoot('/d/slug/raw')).toBe('/d');
  });

  it('goes up from a flat playlist folder (own playlist-index.json)', () => {
    existsFor(['/d/slug/playlist-index.json']);
    expect(normalizeToRoot('/d/slug')).toBe('/d');
  });

  it('goes up from a nested playlist folder (raw/ subdir index)', () => {
    existsFor(['/d/slug/raw/playlist-index.json']);
    expect(normalizeToRoot('/d/slug')).toBe('/d');
  });

  it('leaves an unrelated folder untouched (no index anywhere)', () => {
    existsFor([]);
    expect(normalizeToRoot('/some/random/dir')).toBe('/some/random/dir');
  });

  it('normalizes trailing slashes before resolving', () => {
    existsFor(['/d/slug/raw/playlist-index.json']);
    expect(normalizeToRoot('/d/slug/raw/')).toBe('/d');
  });

  it("leaves a data root literally named 'raw' unchanged (no index inside)", () => {
    existsFor([]); // /data/raw is the root, holds no playlist-index.json
    expect(normalizeToRoot('/data/raw')).toBe('/data/raw');
  });

  it("returns '/' for '/' without climbing below root", () => {
    existsFor([]);
    expect(normalizeToRoot('/')).toBe('/');
  });
});
