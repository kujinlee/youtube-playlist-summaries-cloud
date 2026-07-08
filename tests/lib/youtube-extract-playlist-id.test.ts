import { extractPlaylistId } from '@/lib/youtube';

it('extracts the list id from a playlist url', () => {
  expect(extractPlaylistId('https://www.youtube.com/playlist?list=PLabc123')).toBe('PLabc123');
});
it('throws when no list param is present', () => {
  expect(() => extractPlaylistId('https://www.youtube.com/watch?v=abc')).toThrow();
});
it('throws on a malformed url', () => {
  expect(() => extractPlaylistId('not a url')).toThrow();
});
