import { digHref } from '@/lib/client/api';

it('builds the exact dig-deeper href with all params', () => {
  const u = new URL(digHref('11111111-1111-1111-1111-111111111111', 'vid 123'), 'https://a.test');
  expect(u.pathname).toBe('/api/html/vid%20123');            // encoded
  expect(u.searchParams.get('playlist')).toBe('11111111-1111-1111-1111-111111111111');
  expect(u.searchParams.get('type')).toBe('dig-deeper');
  expect(u.searchParams.has('outputFolder')).toBe(false);    // cloud contract: never outputFolder
  expect(u.searchParams.has('format')).toBe(false);
});

it('percent-encodes a path/query-injecting videoId (no injection)', () => {
  const u = new URL(digHref('11111111-1111-1111-1111-111111111111', 'vid/1?x=2#frag&y=z'), 'https://a.test');
  expect(u.pathname).toBe('/api/html/vid%2F1%3Fx%3D2%23frag%26y%3Dz');
  expect(u.hash).toBe('');
  expect([...u.searchParams.keys()].sort()).toEqual(['playlist', 'type']);
});
