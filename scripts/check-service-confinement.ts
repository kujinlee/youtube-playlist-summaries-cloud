import fs from 'fs';
import path from 'path';

const ROOT = process.cwd();
const TARGET = path.join(ROOT, 'lib/supabase/service.ts');

function resolveImport(fromFile: string, spec: string): string | null {
  let base: string;
  if (spec.startsWith('@/')) base = path.join(ROOT, spec.slice(2));
  else if (spec.startsWith('.')) base = path.resolve(path.dirname(fromFile), spec);
  else if (path.isAbsolute(spec)) base = spec;   // absolute path (e.g. from test fixtures)
  else return null;                               // bare package import — not our code
  const candidates = base.endsWith('.ts') || base.endsWith('.tsx')
    ? [base]
    : ['.ts', '.tsx', '.js', '/index.ts', '/index.tsx'].map((e) => base + e);
  for (const cand of candidates) {
    if (fs.existsSync(cand) && fs.statSync(cand).isFile()) return cand;
  }
  return null;
}

/** Codex H3: match named/default/namespace `from` imports, bare SIDE-EFFECT imports
 *  (`import 'x'`), re-exports (`export ... from 'x'`), and dynamic `import('x')`. */
export function extractImportSpecifiers(src: string): string[] {
  const out: string[] = [];
  const patterns = [
    /(?:import|export)\s[^;'"]*?from\s*['"]([^'"]+)['"]/g, // import/export ... from '...'
    /import\s*['"]([^'"]+)['"]/g,                          // side-effect: import '...'
    /import\(\s*['"]([^'"]+)['"]\s*\)/g,                   // dynamic import('...')
    /require\(\s*['"]([^'"]+)['"]\s*\)/g,                  // require('...')
  ];
  for (const re of patterns) for (let m; (m = re.exec(src)); ) out.push(m[1]);
  return out;
}

export function reachesService(entry: string): boolean {
  const seen = new Set<string>();
  const stack = [entry];
  while (stack.length) {
    const f = stack.pop()!;
    if (seen.has(f)) continue;
    seen.add(f);
    if (path.resolve(f) === TARGET) return true;
    if (!fs.existsSync(f)) continue;
    for (const spec of extractImportSpecifiers(fs.readFileSync(f, 'utf8'))) {
      const r = resolveImport(f, spec);
      if (r) stack.push(r);
    }
  }
  return false;
}

function walk(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return /\.(ts|tsx)$/.test(e.name) ? [p] : [];
  });
}

/** Codex H2: every user-facing entry — not just app/**. */
export function collectEntrypoints(): string[] {
  const entries = [
    ...walk(path.join(ROOT, 'app')),
    ...walk(path.join(ROOT, 'pages')),
    ...walk(path.join(ROOT, 'worker')),
  ];
  const mw = path.join(ROOT, 'middleware.ts');
  if (fs.existsSync(mw)) entries.push(mw);
  return entries;
}

/** Stage 1D (H-B, reviewed): the two-client split requires the enqueue route to build the
 *  service-role `Enqueuer` (`enqueue`/`preflight` are service_role-only RPC grants as of
 *  migration 0011 — anon/authenticated execute was revoked). This is one deliberately
 *  authorized entrypoint; everything else must still be unreachable.
 *
 *  Stage 1F-b (spec D4/D16): the anonymous `/s/[token]` share-serve route is the second (and,
 *  per spec, the ONLY other) deliberately authorized `service_role` entrypoint — there is no
 *  session to scope RLS by for an anonymous visitor, so it uses a runtime `get`-only blob-store
 *  wrapper plus `getShareServeContext`'s explicit confused-deputy guard instead of RLS. */
const ALLOWED_SERVICE_IMPORTERS = [
  path.join(ROOT, 'app/api/jobs/route.ts'),
  path.join(ROOT, 'app/s/[token]/route.ts'),
];

export function findServiceImporters(): string[] {
  return collectEntrypoints()
    .filter((e) => path.resolve(e) !== TARGET && reachesService(e))
    .filter((e) => !ALLOWED_SERVICE_IMPORTERS.includes(path.resolve(e)));
}

if (require.main === module) {
  const violators = findServiceImporters();
  if (violators.length) {
    console.error('service.ts reachable from a user-facing entrypoint:\n' + violators.join('\n'));
    process.exit(1);
  }
  console.log('service_role confinement OK');
}
