import { emptyPlaylistIndex } from '@/lib/storage/empty-index';
import { localPrincipal } from '@/lib/storage/principal';
import { PlaylistIndexSchema } from '@/types';

test('emptyPlaylistIndex is a schema-valid empty index carrying indexKey as outputFolder', () => {
  const idx = emptyPlaylistIndex(localPrincipal('/data/pl'));
  expect(idx).toEqual({ playlistUrl: '', outputFolder: '/data/pl', videos: [] });
  expect(() => PlaylistIndexSchema.parse(idx)).not.toThrow();   // '' must be accepted
});
