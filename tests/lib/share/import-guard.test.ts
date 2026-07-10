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
  join(root, 'lib/html-doc/file-response.ts'),   // 1F-c: share md/html downloads route through this
].filter((f) => existsSync(f));

// Matches BOTH named imports (`import { x } from '<mod>'`) and bare side-effect imports
// (`import '<mod>'`) — the `import`/`from` keyword must directly precede the quoted specifier so a
// mid-string or commented-out module path doesn't false-trip it. An optional `(?:/[^'"]*)?` before
// the closing quote also catches subpath imports (e.g. `@/lib/gemini/foo`) so a forbidden module
// can't be smuggled in through a deeper path (Codex Medium).
const importOf = (mod: string) =>
  new RegExp(`(?:from|import)\\s*\\(?['"]${mod.replace(/[/-]/g, '\\$&')}(?:/[^'"]*)?['"]`);

describe('B18b — share sources never reach the charging code', () => {
  // Scoped to import/call syntax (not bare identifiers) so a comment can't false-trip the guard.
  const forbidden = [
    /from ['"][^'"]*\/serve-doc(?:\/[^'"]*)?['"]/, /import\s*\(?['"][^'"]*\/serve-doc(?:\/[^'"]*)?['"]/,
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

  it('file-response.ts is a dependency-free leaf (no @/ imports, any form)', () => {
    const src = readFileSync(join(root, 'lib/html-doc/file-response.ts'), 'utf-8');
    // Any @/ import: `from '@/…'`, bare `import '@/…'`, dynamic `import('@/…')`, `require('@/…')`.
    // The file legitimately imports nothing from '@/', so a bare literal match is both sufficient
    // and precise (it does not appear in any string/comment in this leaf).
    expect(src).not.toMatch(/['"]@\//);
  });

  // PLANTED NEGATIVE CONTROLS (Codex Medium): prove the widened regexes actually catch a named
  // import, a bare side-effect import, AND a subpath import of each forbidden module — not just
  // that they happen to miss the real (clean) files above. A guard that vacuously passes because
  // its pattern is too narrow is worse than no guard.
  describe('planted violations are caught by the matcher (proves the widened regex works)', () => {
    const cases: Array<{ label: string; src: string; re: RegExp }> = [
      // @/lib/gemini
      { label: '@/lib/gemini named import', src: `import { generateMagazineModel } from '@/lib/gemini';`, re: importOf('@/lib/gemini') },
      { label: '@/lib/gemini bare side-effect import', src: `import '@/lib/gemini';`, re: importOf('@/lib/gemini') },
      { label: '@/lib/gemini subpath import', src: `import { foo } from '@/lib/gemini/foo';`, re: importOf('@/lib/gemini') },
      // @/lib/gemini-cost
      { label: '@/lib/gemini-cost named import', src: `import { perRunWorstCents } from '@/lib/gemini-cost';`, re: importOf('@/lib/gemini-cost') },
      { label: '@/lib/gemini-cost bare side-effect import', src: `import '@/lib/gemini-cost';`, re: importOf('@/lib/gemini-cost') },
      { label: '@/lib/gemini-cost subpath import', src: `import { foo } from '@/lib/gemini-cost/foo';`, re: importOf('@/lib/gemini-cost') },
      // serve-doc
      { label: 'serve-doc named import (from)', src: `import { resolveMagazineModel } from '@/lib/serve-doc';`, re: /from ['"][^'"]*\/serve-doc(?:\/[^'"]*)?['"]/ },
      { label: 'serve-doc bare side-effect import', src: `import '@/lib/serve-doc';`, re: /import\s*\(?['"][^'"]*\/serve-doc(?:\/[^'"]*)?['"]/ },
      { label: 'serve-doc subpath import (from)', src: `import { resolveMagazineModel } from '@/lib/serve-doc/internal';`, re: /from ['"][^'"]*\/serve-doc(?:\/[^'"]*)?['"]/ },
      { label: 'serve-doc subpath bare side-effect import', src: `import '@/lib/serve-doc/internal';`, re: /import\s*\(?['"][^'"]*\/serve-doc(?:\/[^'"]*)?['"]/ },
    ];
    it.each(cases)('$label is flagged', ({ src, re }) => {
      expect(src).toMatch(re);
    });
  });
});
