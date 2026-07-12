import { pdfHref } from '@/lib/client/api';

it('builds the exact pdf href with all params', () => {
  const u = new URL(pdfHref('11111111-1111-1111-1111-111111111111', 'vid 123'), 'https://a.test');
  expect(u.pathname).toBe('/api/pdf/vid%20123');   // encoded
  expect(u.searchParams.get('playlist')).toBe('11111111-1111-1111-1111-111111111111');
  expect(u.searchParams.get('type')).toBe('summary');
});

it('percent-encodes a videoId containing path/query-injecting chars (no injection)', () => {
  const u = new URL(pdfHref('11111111-1111-1111-1111-111111111111', 'vid/1?x=2#frag&y=z'), 'https://a.test');
  // the whole id stays inside a single path segment — no extra path, no injected query/hash
  expect(u.pathname).toBe('/api/pdf/vid%2F1%3Fx%3D2%23frag%26y%3Dz');
  expect(u.hash).toBe('');                                  // '#frag' did not leak into the fragment
  expect([...u.searchParams.keys()].sort()).toEqual(['playlist', 'type']); // no injected 'x'/'y' params
  expect(u.searchParams.get('type')).toBe('summary');
});
