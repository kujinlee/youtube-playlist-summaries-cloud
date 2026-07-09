import fs from 'fs';
import path from 'path';
import { findServiceImporters, extractImportSpecifiers } from '@/scripts/check-service-confinement';

describe('service_role confinement', () => {
  it('no UNAUTHORIZED user-facing Next entrypoint transitively imports lib/supabase/service.ts', () => {
    // Stage 1D (H-B): app/api/jobs/route.ts is now the one deliberately authorized
    // service-role entrypoint (it builds the two-client split's service `Enqueuer` — see
    // check-service-confinement.ts ALLOWED_SERVICE_IMPORTERS). Everything else must still
    // be unreachable.
    expect(findServiceImporters()).toEqual([]);   // app/**, middleware.ts, pages/** minus the allowlist
  });

  it('app/api/jobs/route.ts (the Stage 1D allowlisted entrypoint) does reach service.ts', () => {
    const { reachesService } = require('@/scripts/check-service-confinement');
    const entry = path.join(process.cwd(), 'app/api/jobs/route.ts');
    expect(reachesService(entry)).toBe(true);
  });

  it('extractImportSpecifiers catches side-effect + re-export imports (Codex H3)', () => {
    const src = [
      `import '@/lib/supabase/service';`,               // side-effect import
      `export { createServiceClient } from './service';`, // re-export
      `const x = await import('@/lib/supabase/service');`, // dynamic
      `import { a } from '@/lib/supabase/env';`,          // named
    ].join('\n');
    const specs = extractImportSpecifiers(src);
    expect(specs).toEqual(
      expect.arrayContaining(['@/lib/supabase/service', './service', '@/lib/supabase/service', '@/lib/supabase/env']),
    );
  });

  it('detects a planted violation reaching service.ts through a side-effect import', () => {
    const dir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'confine-'));
    const entry = path.join(dir, 'evil.ts');
    fs.writeFileSync(entry, `import '${path.join(process.cwd(), 'lib/supabase/service')}';\n`);
    // reach() is exported for this fixture check
    const { reachesService } = require('@/scripts/check-service-confinement');
    expect(reachesService(entry)).toBe(true);
  });

  it('detects @/ alias style side-effect import violation in repo fixture', () => {
    const { reachesService } = require('@/scripts/check-service-confinement');
    const fixtureFile = path.join(process.cwd(), 'app/__confinement_fixture__.ts');
    try {
      fs.writeFileSync(fixtureFile, `import '@/lib/supabase/service';\n`);
      expect(reachesService(fixtureFile)).toBe(true);
    } finally {
      if (fs.existsSync(fixtureFile)) {
        fs.unlinkSync(fixtureFile);
      }
    }
  });
});
