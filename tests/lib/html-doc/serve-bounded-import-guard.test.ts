import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Ordered by the spec (§5): "assert the serve route reaches the wrapper … A grep-style import guard
// is appropriate — the repo already uses one at tests/lib/share/import-guard.test.ts."
//
// ROUND-1 H1 measured what its absence cost: the serve call site could be reverted to the pre-fix
// 3×60s budget with tsc, 1786 unit tests and 59 integration tests all green.
//
// ROUND-2 H-R2-1 measured what fixing only THAT call site cost: `writeModelEnvelopeWithin`'s
// timeout could be changed to 120_000 — 245s of enforced work against a 161s floor — and all 2647
// tests stayed green, because the round-1 guard checked the IDENTIFIER and never the ARGUMENT.
//
// So this file asserts the CLASS, not the instance:
//
//   1. serve-doc.ts NAMES durations and counts; it never SPELLS them. The only numeric literals
//      permitted in its code are 0 and 1 (an array index and a loop bound). Every timeout, attempt
//      count and budget must arrive as an identifier from lib/serve-budget, whose own values are
//      asserted against the lease in tests/lib/serve-budget.test.ts.
//   2. Each bounded call site receives its OWN designated constant — not merely some constant.
//   3. The POPULATION of bounded call sites is pinned. Adding a fifth bounded call without
//      extending this table fails here, which is the difference between a class assertion and four
//      instance assertions. Round 2's lesson was that round 1 wrote the latter.

const root = process.cwd();
const SERVE_DOC = join(root, 'lib/html-doc/serve-doc.ts');

/** Source with comments and string/template literals removed, so prose cannot satisfy or trip a rule. */
function codeOnly(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/[^\n]*/g, '')
    .replace(/`(?:[^`\\]|\\.)*`/g, '``')
    .replace(/'(?:[^'\\]|\\.)*'/g, "''")
    .replace(/"(?:[^"\\]|\\.)*"/g, '""');
}

/** The full argument text of every call to `fn`, via a balanced-paren scan. */
function callArgs(code: string, fn: string): string[] {
  const out: string[] = [];
  const re = new RegExp(`\\b${fn}\\s*(?:<[^>]*>)?\\s*\\(`, 'g');
  let m: RegExpExecArray | null;
  while ((m = re.exec(code)) !== null) {
    let depth = 1;
    let i = m.index + m[0].length;
    const start = i;
    while (i < code.length && depth > 0) {
      if (code[i] === '(') depth++;
      else if (code[i] === ')') depth--;
      i++;
    }
    out.push(code.slice(start, i - 1));
  }
  return out;
}

/** Each bounded call reachable while the paid lease is held, and the constant it must be given. */
const BOUNDED_CALLS: Array<{ fn: string; calls: number; mustContain: string[] }> = [
  { fn: 'generateMagazineModelForServe', calls: 1, mustContain: ['SERVE_BUDGET'] },
  { fn: 'writeModelEnvelopeWithin', calls: 1, mustContain: ['SERVE_PUT_TIMEOUT_MS'] },
  // Two RPCs, and they must not be given each other's budget — hence both named here and each
  // asserted to appear exactly once across the call sites.
  { fn: 'callRpcBounded', calls: 2, mustContain: ['SERVE_RESERVE_RPC_TIMEOUT_MS', 'SERVE_SETTLE_RPC_TIMEOUT_MS'] },
];

/** The unbounded twin of each bounded call. Same job, no bound, invisible at the call site. */
const BANNED: Array<{ unbounded: RegExp; bounded: string; why: string }> = [
  {
    unbounded: /\bgenerateMagazineModel\b/,
    bounded: 'generateMagazineModelForServe',
    why: 'runs 3 attempts × 60s (GENERATE_JSON_RETRIES / REQUEST_TIMEOUT_MS) — 181.2s against a 161s lease floor',
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
    const offending = src.split('\n')
      .map((line, n) => ({ n: n + 1, line }))
      .filter(({ line }) => unbounded.test(line) && !line.trimStart().startsWith('//'));
    expect({ bounded, why, offending }).toEqual({ bounded, why, offending: [] });
  });

  // ── H-R2-1. The value, not just the identifier. ────────────────────────────────────────────
  it('spells no duration or count — every one arrives as a named serve-budget constant', () => {
    const code = codeOnly(readFileSync(SERVE_DOC, 'utf-8'));
    // 0 and 1 are an array index and a loop bound. Anything else in this file is a duration or an
    // attempt count, and both belong in lib/serve-budget.ts where the lease arithmetic can see them.
    const literals = [...code.matchAll(/(?<![\w.])(\d[\d_]*)(?![\w])/g)]
      .map((m) => m[1])
      .filter((n) => n !== '0' && n !== '1');
    expect(literals).toEqual([]);
  });

  it.each(BOUNDED_CALLS)('$fn is handed its own budget constant, at every call site', ({ fn, calls, mustContain }) => {
    const code = codeOnly(readFileSync(SERVE_DOC, 'utf-8'));
    const args = callArgs(code, fn);
    // Population first: a call site added without extending this table must fail here.
    expect({ fn, sites: args.length }).toEqual({ fn, sites: calls });
    for (const constant of mustContain) {
      const seen = args.filter((a) => a.includes(constant)).length;
      expect({ fn, constant, seen }).toEqual({ fn, constant, seen: 1 });
    }
  });

  it('does reference the bounded functions, so the guards above are not passing vacuously', () => {
    const src = readFileSync(SERVE_DOC, 'utf-8');
    for (const { bounded } of BANNED) expect(src).toContain(bounded);
  });
});
