import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { discoverLocalPlaylists, playlistKeyFromUrl, unionPlaylistKeys } from '@/lib/cloud-sync/registry';

describe('playlistKeyFromUrl', () => {
  it('extracts list id from a playlist url', () => {
    expect(playlistKeyFromUrl('https://www.youtube.com/playlist?list=PLabc123')).toBe('PLabc123');
  });
  it('extracts from a watch url with a list param', () => {
    expect(playlistKeyFromUrl('https://www.youtube.com/watch?v=x&list=PLxyz')).toBe('PLxyz');
  });
  it('returns null when there is no list param', () => {
    expect(playlistKeyFromUrl('https://youtu.be/x')).toBeNull();
    expect(playlistKeyFromUrl('')).toBeNull();
  });
});

// ── H3 (round 4) — discoverLocalPlaylists read the full index and DISCARDED idx.playlistTitle,
//    so LocalPlaylist could never carry one. playlistMetaFor checks the local registry first, so a
//    playlist present in BOTH replicas always resolved to a title-less meta — which the cloud
//    setPlaylistMeta upsert writes as an explicit NULL, wiping the cloud row's title.
describe('discoverLocalPlaylists', () => {
  let root: string;
  // index-store rejects any outputFolder outside the home directory, so the fixture root must
  // live under $HOME (same constraint the cloud-sync integration harness works around).
  beforeEach(async () => { root = await fs.mkdtemp(path.join(os.homedir(), '.cs-registry-')); });
  afterEach(async () => { await fs.rm(root, { recursive: true, force: true }); });

  async function writeIndex(dir: string, index: Record<string, unknown>): Promise<void> {
    await fs.mkdir(path.join(root, dir), { recursive: true });
    await fs.writeFile(path.join(root, dir, 'playlist-index.json'), JSON.stringify(index), 'utf8');
  }

  it('carries playlistTitle through from the index', async () => {
    await writeIndex('p1', {
      playlistUrl: 'https://www.youtube.com/playlist?list=PLtitled',
      playlistTitle: 'Deep Learning Lectures',
      outputFolder: 'p1',
      videos: [],
    });

    const found = await discoverLocalPlaylists([root]);

    expect(found).toHaveLength(1);
    expect(found[0].playlistKey).toBe('PLtitled');
    expect(found[0].playlistTitle).toBe('Deep Learning Lectures');
  });

  it('leaves playlistTitle undefined when the index has none', async () => {
    await writeIndex('p2', {
      playlistUrl: 'https://www.youtube.com/playlist?list=PLuntitled',
      outputFolder: 'p2',
      videos: [],
    });

    const found = await discoverLocalPlaylists([root]);

    expect(found).toHaveLength(1);
    expect(found[0].playlistTitle).toBeUndefined();
  });
});

describe('unionPlaylistKeys', () => {
  it('unions local and cloud keys without duplicates', () => {
    const local = [{ playlistKey: 'A', dataRoot: '/a', playlistUrl: 'u' }, { playlistKey: 'B', dataRoot: '/b', playlistUrl: 'u' }];
    expect(unionPlaylistKeys(local as any, ['B', 'C']).sort()).toEqual(['A', 'B', 'C']);
  });
});
