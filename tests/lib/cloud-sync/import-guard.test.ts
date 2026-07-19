import { readFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';

// Filesystem walk — NOT `git ls-files` (which sees only tracked files, so a new-but-uncommitted
// cloud-sync source would be skipped and the guard would pass vacuously). Assert the scan is
// non-empty so an empty/broken scan (e.g. a renamed directory) fails loudly instead of silently
// passing with zero files checked.
function walk(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return e.isFile() && p.endsWith('.ts') && !p.endsWith('.test.ts') ? [p] : [];
  });
}
const root = process.cwd();
const cloudSyncSources = walk(join(root, 'lib/cloud-sync')).filter((f) => existsSync(f));

// Matches BOTH named imports (`import { x } from '<mod>'`) and bare side-effect imports
// (`import '<mod>'`) — the `import`/`from` keyword must directly precede the quoted specifier so a
// mid-string or commented-out module path doesn't false-trip it. An optional `(?:/[^'"]*)?` before
// the closing quote also catches subpath imports (e.g. `@/lib/supabase/service/foo`) so a forbidden
// module can't be smuggled in through a deeper path.
const importOf = (mod: string) =>
  new RegExp(`(?:from|import)\\s*\\(?['"]${mod.replace(/[/-]/g, '\\$&')}(?:/[^'"]*)?['"]`);

describe('Task 10 (§6) — cloud-sync auth never reaches the service-role key', () => {
  // The "no service-role key on the local machine" guarantee only holds if the sync code (a) never
  // imports the service client module (`@/lib/supabase/service`), (b) never calls the service-role
  // accessor (`getServiceRoleKey`) or the client constructor (`createServiceClient`), and (c) never
  // references the raw env var name — any of these would defeat getAuthedClient's anon-key-only
  // construction.
  const forbidden = [
    /SUPABASE_SERVICE_ROLE_KEY/,        // literal env var name — any reference
    /getServiceRoleKey\s*\(/,           // the service-role key accessor
    /createServiceClient\s*\(/,         // the service_role client constructor
    importOf('@/lib/supabase/service'), // module that builds the service_role client
  ];

  it('scans a non-empty set of cloud-sync sources', () => {
    expect(cloudSyncSources.length).toBeGreaterThan(0);
    expect(cloudSyncSources.some((f) => f.endsWith('lib/cloud-sync/auth.ts'))).toBe(true);
  });

  it.each(cloudSyncSources)('%s imports/calls nothing that reaches the service-role key', (file) => {
    const src = readFileSync(file, 'utf-8');
    for (const re of forbidden) expect(src).not.toMatch(re);
  });

  // PLANTED NEGATIVE CONTROLS: prove the forbid-patterns actually catch a service-role reference in
  // each of its forms — not just that they happen to miss the real (clean) files above. A guard
  // that vacuously passes because its pattern is too narrow is worse than no guard.
  describe('planted violations are caught by the matcher (proves the guard is non-vacuous)', () => {
    const cases: Array<{ label: string; src: string; re: RegExp }> = [
      {
        label: 'raw env var reference',
        src: `const key = process.env.SUPABASE_SERVICE_ROLE_KEY;`,
        re: /SUPABASE_SERVICE_ROLE_KEY/,
      },
      {
        label: 'getServiceRoleKey() call',
        src: `import { getServiceRoleKey } from '@/lib/supabase/env';\nconst k = getServiceRoleKey();`,
        re: /getServiceRoleKey\s*\(/,
      },
      {
        label: 'createServiceClient() call',
        src: `import { createServiceClient } from '@/lib/supabase/service';\nconst c = createServiceClient();`,
        re: /createServiceClient\s*\(/,
      },
      {
        label: '@/lib/supabase/service named import',
        src: `import { createServiceClient } from '@/lib/supabase/service';`,
        re: importOf('@/lib/supabase/service'),
      },
      {
        label: '@/lib/supabase/service bare side-effect import',
        src: `import '@/lib/supabase/service';`,
        re: importOf('@/lib/supabase/service'),
      },
      {
        label: '@/lib/supabase/service subpath import',
        src: `import { foo } from '@/lib/supabase/service/foo';`,
        re: importOf('@/lib/supabase/service'),
      },
    ];
    it.each(cases)('$label is flagged', ({ src, re }) => {
      expect(src).toMatch(re);
    });
  });
});
