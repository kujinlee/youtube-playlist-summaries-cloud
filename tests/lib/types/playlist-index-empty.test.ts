import { PlaylistIndexSchema } from '@/types';

test('PlaylistIndexSchema accepts empty string playlistUrl for absent-index sentinel', () => {
  expect(() =>
    PlaylistIndexSchema.parse({ playlistUrl: '', outputFolder: '/x', videos: [] })
  ).not.toThrow();
});
