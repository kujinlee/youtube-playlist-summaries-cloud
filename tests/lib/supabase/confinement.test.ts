import fs from 'fs';
import path from 'path';
import { findServiceImporters, extractImportSpecifiers } from '@/scripts/check-service-confinement';

describe('service_role confinement', () => {
  it('no user-facing Next entrypoint transitively imports lib/supabase/service.ts', () => {
    expect(findServiceImporters()).toEqual([]);   // app/**, middleware.ts, pages/**
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
});
