import { playlistKeyFromUrl, unionPlaylistKeys } from '@/lib/cloud-sync/registry';

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

describe('unionPlaylistKeys', () => {
  it('unions local and cloud keys without duplicates', () => {
    const local = [{ playlistKey: 'A', dataRoot: '/a', playlistUrl: 'u' }, { playlistKey: 'B', dataRoot: '/b', playlistUrl: 'u' }];
    expect(unionPlaylistKeys(local as any, ['B', 'C']).sort()).toEqual(['A', 'B', 'C']);
  });
});
