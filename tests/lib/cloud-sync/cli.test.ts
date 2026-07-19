import { parseArgs } from '@/scripts/cloud-sync';

it('defaults to sync over all playlists', () => {
  expect(parseArgs([])).toEqual({ cmd: 'sync' });
});
it('parses a single-playlist sync', () => {
  expect(parseArgs(['--playlist', 'PLabc'])).toEqual({ cmd: 'sync', playlistKey: 'PLabc' });
});
it('parses login and logout', () => {
  expect(parseArgs(['login'])).toEqual({ cmd: 'login' });
  expect(parseArgs(['logout'])).toEqual({ cmd: 'logout' });
});
