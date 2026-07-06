// tests/integration/storage-policy.test.ts
import { adminClient } from './helpers/clients';
test('artifacts bucket exists and is private', async () => {
  const { data } = await adminClient().storage.getBucket('artifacts');
  expect(data?.public).toBe(false);
});
