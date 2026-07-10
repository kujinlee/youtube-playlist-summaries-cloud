import { readFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';

// Filesystem walk — NOT `git ls-files` (which sees only tracked files, so a new-but-uncommitted
// share source would be skipped and the guard would pass vacuously). Assert the scan is non-empty
// and includes the route, so an empty/broken scan fails loudly.
function walk(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return e.isFile() && p.endsWith('.ts') && !p.endsWith('.test.ts') ? [p] : [];
  });
}
const root = process.cwd();
const shareSources = [
  ...walk(join(root, 'app/s')),
  ...walk(join(root, 'lib/share')),
  join(root, 'lib/html-doc/read-model.ts'),
].filter((f) => existsSync(f));

// Matches BOTH named imports (`import { x } from '<mod>'`) and bare side-effect imports
// (`import '<mod>'`) — the `import`/`from` keyword must directly precede the quoted specifier so a
// mid-string or commented-out module path doesn't false-trip it.
const importOf = (mod: string) => new RegExp(`(?:from|import)\\s*\\(?['"]${mod.replace(/[/-]/g, '\\$&')}['"]`);

describe('B18b — share sources never reach the charging code', () => {
  // Scoped to import/call syntax (not bare identifiers) so a comment can't false-trip the guard.
  const forbidden = [
    /from ['"][^'"]*\/serve-doc['"]/, /import\s*\(?['"][^'"]*\/serve-doc['"]/,
    importOf('@/lib/gemini'), importOf('@/lib/gemini-cost'),
    /resolveMagazineModel\s*\(/, /generateMagazineModel\s*\(/, /reserve_serve_model/, /\.rpc\s*\(/,
  ];
  it('scans a non-empty set including the serve route', () => {
    expect(shareSources.length).toBeGreaterThan(0);
    expect(shareSources.some((f) => f.endsWith('app/s/[token]/route.ts'))).toBe(true);
  });
  it.each(shareSources)('%s imports/calls nothing that charges', (file) => {
    const src = readFileSync(file, 'utf-8');
    for (const re of forbidden) expect(src).not.toMatch(re);
  });
});
