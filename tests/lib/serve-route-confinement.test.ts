import path from 'path';
import { collectEntrypoints, reachesService, findServiceImporters } from '@/scripts/check-service-confinement';

const ROUTE = path.join(process.cwd(), 'app/api/html/[id]/route.ts');

it('the serve route is scanned as an entrypoint', () => {
  expect(collectEntrypoints().map((e) => path.resolve(e))).toContain(path.resolve(ROUTE));
});
it('the serve route does NOT reach lib/supabase/service.ts (session client only — B20)', () => {
  expect(reachesService(ROUTE)).toBe(false);
});
it('the serve route is NOT in the service-role allowlist and is not a violator', () => {
  expect(findServiceImporters().map((e) => path.resolve(e))).not.toContain(path.resolve(ROUTE));
});
