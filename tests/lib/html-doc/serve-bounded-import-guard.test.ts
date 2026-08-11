import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Ordered by the spec (§5): "assert the serve route reaches the wrapper … A grep-style import guard
// is appropriate — the repo already uses one at tests/lib/share/import-guard.test.ts." It was never
// written, and round-1 review H1 measured what that cost: the serve call site could be reverted to
// the pre-fix 3×60s configuration with tsc, 1786 unit tests and 59 integration tests all green.
//
// The sibling test in serve-doc-mapping.test.ts asserts the budget VALUE reaching the wrapper. This
// asserts something that test cannot: that the UNBOUNDED TWIN of each bounded call is not reachable
// from the lease-holding path at all. Both functions in each pair do the same job; only one of each
// has a bound, and the difference is invisible at the call site.
//
// Word boundaries do the discriminating: `\bgenerateMagazineModel\b` does NOT match
// `generateMagazineModelForServe` (a word character follows "Model"), and likewise
// `\bwriteModelEnvelope\b` does not match `writeModelEnvelopeWithin`.

const root = process.cwd();
const SERVE_DOC = join(root, 'lib/html-doc/serve-doc.ts');

/** Each pair: the unbounded function, and the bounded one that must be used instead. */
const BANNED: Array<{ unbounded: RegExp; bounded: string; why: string }> = [
  {
    unbounded: /\bgenerateMagazineModel\b/,
    bounded: 'generateMagazineModelForServe',
    why: 'runs 3 attempts × 60s (GENERATE_JSON_RETRIES / REQUEST_TIMEOUT_MS) — 181.2s against a lease floor of 161s',
  },
  {
    unbounded: /\bwriteModelEnvelope\b/,
    bounded: 'writeModelEnvelopeWithin',
    why: 'awaits the Supabase upload with no bound at all',
  },
];

describe('serve-doc holds a paid lease, so every call it makes must be the BOUNDED one', () => {
  // A guard that silently scans nothing passes vacuously — the failure mode this repo has measured
  // repeatedly. Prove the target exists and was read before asserting anything about its contents.
  it('reads the file it claims to guard', () => {
    expect(existsSync(SERVE_DOC)).toBe(true);
    expect(readFileSync(SERVE_DOC, 'utf-8').length).toBeGreaterThan(0);
  });

  it.each(BANNED)('never references $bounded\'s unbounded twin', ({ unbounded, bounded, why }) => {
    const src = readFileSync(SERVE_DOC, 'utf-8');
    // Report the offending line, not just a boolean — a guard that fails without saying where
    // costs the next reader the same investigation.
    const offending = src.split('\n')
      .map((line, i) => ({ n: i + 1, line }))
      .filter(({ line }) => unbounded.test(line) && !line.trimStart().startsWith('//'));
    expect({ bounded, why, offending }).toEqual({ bounded, why, offending: [] });
  });

  it('does reference the bounded functions, so the guard above is not passing vacuously', () => {
    const src = readFileSync(SERVE_DOC, 'utf-8');
    for (const { bounded } of BANNED) expect(src).toContain(bounded);
  });
});
