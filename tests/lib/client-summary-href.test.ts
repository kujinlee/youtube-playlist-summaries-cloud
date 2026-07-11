import { summaryHref } from '@/lib/client/api';

const PID = '11111111-1111-1111-1111-111111111111';
const VID = 'abc123XYZ_0';

test('view link: playlist + type only, new-tab target', () => {
  const url = new URL(summaryHref(PID, VID), 'https://app.test');
  expect(url.pathname).toBe(`/api/html/${VID}`);
  expect(url.searchParams.get('playlist')).toBe(PID);
  expect(url.searchParams.get('type')).toBe('summary');
  expect(url.searchParams.get('format')).toBeNull();
  expect(url.searchParams.get('download')).toBeNull();
});

test('download markdown: format=md & download=1', () => {
  const url = new URL(summaryHref(PID, VID, { format: 'md', download: true }), 'https://app.test');
  expect(url.searchParams.get('playlist')).toBe(PID);
  expect(url.searchParams.get('type')).toBe('summary');
  expect(url.searchParams.get('format')).toBe('md');
  expect(url.searchParams.get('download')).toBe('1');
});

test('download html: format=html & download=1', () => {
  const url = new URL(summaryHref(PID, VID, { format: 'html', download: true }), 'https://app.test');
  expect(url.searchParams.get('format')).toBe('html');
  expect(url.searchParams.get('download')).toBe('1');
  expect(url.searchParams.get('type')).toBe('summary');
  expect(url.searchParams.get('playlist')).toBe(PID);
});

test('videoId with reserved chars is percent-encoded in the path', () => {
  // proves encodeURIComponent(videoId) is actually load-bearing
  const href = summaryHref(PID, 'a/b?c#d', { format: 'md', download: true });
  expect(href.startsWith('/api/html/a%2Fb%3Fc%23d?')).toBe(true);
  const url = new URL(href, 'https://app.test');
  expect(url.pathname).toBe('/api/html/a%2Fb%3Fc%23d');
  expect(url.searchParams.get('format')).toBe('md');   // query intact, not swallowed by the '?'
});
