import { pdfHref } from '@/lib/client/api';

it('builds the exact pdf href with all params', () => {
  const u = new URL(pdfHref('11111111-1111-1111-1111-111111111111', 'vid 123'), 'https://a.test');
  expect(u.pathname).toBe('/api/pdf/vid%20123');   // encoded
  expect(u.searchParams.get('playlist')).toBe('11111111-1111-1111-1111-111111111111');
  expect(u.searchParams.get('type')).toBe('summary');
});
