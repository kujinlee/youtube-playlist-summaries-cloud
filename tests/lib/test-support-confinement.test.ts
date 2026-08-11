import { readFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';

// `tests/support/budget.ts` mints branded budgets — including a whole `ServeBudget` via
// `serveBudgetWith`. That is a SECOND mint of a brand whose entire value is that production has only
// one (round-7 review M-R7-2). Nothing structural stops a lib/ module importing it, and if one did,
// every compile-time guarantee the brands provide would be available to production code by the back
// door.
//
// Checked rather than trusted, for the same reason the population gate books its spend rather than
// scanning for it.

const ROOT = process.cwd();
const PRODUCTION_ROOTS = ['lib', 'app', 'worker', 'scripts'];

function walk(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return e.isFile() && (p.endsWith('.ts') || p.endsWith('.tsx')) ? [p] : [];
  });
}

describe('test-only budget minters never reach production code', () => {
  const sources = PRODUCTION_ROOTS.flatMap((r) => walk(join(ROOT, r)));

  it('scans a real tree — not passing vacuously', () => {
    expect(sources.length).toBeGreaterThan(50);
  });

  it('no production file imports from tests/', () => {
    const offenders = sources
      .map((f) => ({ file: f.replace(`${ROOT}/`, ''), src: readFileSync(f, 'utf-8') }))
      .filter(({ src }) => /from\s*'[^']*tests\/support\//.test(src) || /from\s*'[^']*\btests\//.test(src))
      .map(({ file }) => file);
    expect(offenders).toEqual([]);
  });

  it('no production file names the budget minters', () => {
    const minters = /\b(serveBudgetWith|putBudget|reserveRpcBudget|settleRpcBudget)\b/;
    const offenders = sources
      .map((f) => ({ file: f.replace(`${ROOT}/`, ''), src: readFileSync(f, 'utf-8') }))
      .filter(({ src }) => minters.test(src))
      .map(({ file }) => file);
    expect(offenders).toEqual([]);
  });
});
