import { localPrincipal, LOCAL_PRINCIPAL_ID } from '@/lib/storage/principal';

test('localPrincipal carries the raw indexKey and the local sentinel id', () => {
  const p = localPrincipal('/Users/me/data/playlist');
  expect(p.id).toBe(LOCAL_PRINCIPAL_ID);
  expect(p.indexKey).toBe('/Users/me/data/playlist');
});

test('LOCAL_PRINCIPAL_ID is the string "local"', () => {
  expect(LOCAL_PRINCIPAL_ID).toBe('local');
});
