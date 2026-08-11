import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

// ── H-R6-1. THE SET WAS CLOSED; THE CLOSURE WAS NOT ENFORCED. ────────────────────────────────────
//
// Rounds 4, 5 and a coordinator sweep each found one more value spent inside the paid lease that
// nothing tied to the budget: the generation attempt count, the settle attempt count, the retry
// backoff. Round 6 enumerated the whole population and found no twelfth — and then measured that a
// twelfth CAN BE ADDED with every gate green:
//
//   1. a new brand + constant in serve-budget.ts, NOT added to SERVE_BOUNDED_MS
//   2. a new bounded helper taking that brand
//   3. one line calling it inside the lease
//
//   → `tsc --noEmit` exit 0, 263 suites / 2658 tests green, 30s of enforced work the floor does not
//     cover, and therefore the lease overrun that admits a second paid producer.
//
// The old guard could not see it: `serve-bounded-import-guard.test.ts` counts calls to the three
// functions ALREADY IN ITS TABLE, so a fourth bounded function is simply never searched for. Its
// comment claimed it pinned "the population", and a reviewer certified that claim in round 5. It
// pinned a population — of known call sites, not of bounded values.
//
// This file closes it from the other end, where the population actually lives: every branded budget
// must be SPENT IN THE ARITHMETIC that produces the floor. A new brand that nobody added to the sum
// fails here, which is the difference between "the set is closed today" and "the set cannot be
// opened".
//
// WHAT THIS GATE DOES NOT STOP, stated because four overclaimed comments have already been caught on
// this branch: a term written into the sum so as to contribute nothing — `+ 0 * SERVE_X` — satisfies
// every rule below. MEASURED: it passes. That is not closed, and it is not going to be: it is a
// deliberate act, not the drift these rules exist to catch, and a test that claimed to stop
// deliberate circumvention would be the fifth overclaim. The rules defend against a budget being
// FORGOTTEN, which is what actually happened three times here.

const LIB = join(process.cwd(), 'lib');
const SERVE_BUDGET_SRC = join(LIB, 'serve-budget.ts');

/** Every .ts under lib/, so a brand minted in ANOTHER file cannot escape the rules below. */
function libSources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    if (e.isDirectory()) return libSources(p);
    return e.isFile() && p.endsWith('.ts') ? [p] : [];
  });
}

/** Source with comments stripped, so prose can neither satisfy nor trip a rule. */
function codeOnly(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
}

/** The right-hand side of `export const NAME = …;`. */
function rhs(code: string, name: string): string {
  const at = code.indexOf(`export const ${name}`);
  expect({ name, found: at >= 0 }).toEqual({ name, found: true });
  const body = code.slice(code.indexOf('=', at) + 1, code.indexOf(';', at));
  expect(body.trim().length).toBeGreaterThan(0);
  return body;
}

/**
 * The EXPRESSIONS that spend budgets — not a line range.
 *
 * A first version of this took everything between two declarations, which is the same
 * green-gate-testing-the-wrong-thing shape this branch has now found seven times: most of the
 * constants are DECLARED inside that span, so every name matched its own declaration and the check
 * was vacuous. Caught by running mutant M5 against it rather than by reading it.
 *
 * Reading the two right-hand sides means a constant only counts as accounted for when it is
 * genuinely SPENT: summed into the enforced total, or folded into the derived backoff.
 */
function spendingExpressions(code: string): string {
  const sum = rhs(code, 'SERVE_BOUNDED_MS');
  const backoff = rhs(code, 'SERVE_BACKOFF_TOTAL_MS');
  // The sum must still look like a sum — a refactor that empties it must fail here, loudly.
  expect(sum).toContain('SERVE_RESERVE_RPC_TIMEOUT_MS');
  expect(sum).toContain('SERVE_PUT_TIMEOUT_MS');
  return `${sum}\n${backoff}`;
}

/**
 * Every `export const X = … as <Brand>;` — i.e. every SCALAR minted as spendable on the serve path.
 *
 * `ServeBudget` is excluded because it is the CARRIER, not a scalar: it fans several of these values
 * across a function boundary and has no duration of its own. Excluding it is not a loophole — the
 * test below asserts every one of its FIELDS is itself one of these branded scalars, so the carrier
 * cannot smuggle an unaccounted value across the boundary either.
 */
function brandedExports(code: string): string[] {
  return [...code.matchAll(/export\s+const\s+([A-Z0-9_]+)\s*=\s*[^;]*?\bas\s+(\w*(?:Budget|AttemptCount))\s*;/g)]
    .filter((m) => m[2] !== 'ServeBudget')
    .map((m) => m[1]);
}

/**
 * Deliberately NOT branded, with the reason. A brand means "this is spent inside the lease"; these
 * are not, and saying so here is what keeps the rule above meaningful rather than something to be
 * worked around.
 */
const UNBRANDED_BY_DESIGN: Record<string, string> = {
  SERVE_MARGIN_MS: 'an ASSUMPTION about unmodelled work, not a timeout the code applies',
  SERVE_BACKOFF_TOTAL_MS: 'derived from SERVE_BACKOFF_BASE_MS; the base is the branded, spendable one',
  SERVE_BOUNDED_MS: 'the sum itself',
  SERVE_FLOOR_MS: 'the sum plus the margin',
  SERVE_FLOOR_SECONDS: 'the migration-facing floor',
  SERVE_BUDGET: 'the CARRIER of branded scalars, asserted field-by-field below',
};

describe('the population of lease-spent budgets is CLOSED, and closure is enforced', () => {
  const code = codeOnly(readFileSync(SERVE_BUDGET_SRC, 'utf-8'));

  // ── EVASION A, found by attacking this gate rather than reading it. ─────────────────────────
  // The first version of these rules scanned serve-budget.ts alone, so a maintainer adding
  // `lib/serve-verify-budget.ts` with its own `as VerifyBudget` constant walked straight through —
  // and putting a new subsystem's budget in a new file is what someone would actually do. The brand
  // TYPE lives in serve-budget.ts, so any file minting one is minting a lease-spent value, and the
  // rule has to follow the brand rather than the filename.
  it('NO OTHER FILE under lib/ mints a budget brand — serve-budget.ts is the only mint', () => {
    const offenders = libSources(LIB)
      .filter((f) => f !== SERVE_BUDGET_SRC)
      .map((f) => ({ file: f.replace(`${process.cwd()}/`, ''), src: codeOnly(readFileSync(f, 'utf-8')) }))
      .filter(({ src }) => /\bas\s+\w*(?:Budget|AttemptCount)\s*[;,)]/.test(src))
      .map(({ file }) => file);
    // If a new budget legitimately belongs elsewhere, the sum has to move with it — which is the
    // conversation this failure is meant to force.
    expect(offenders).toEqual([]);
  });

  it('scans a real tree — the lib/ walk is not silently empty', () => {
    const all = libSources(LIB);
    expect(all.length).toBeGreaterThan(20);
    expect(all).toContain(SERVE_BUDGET_SRC);
  });

  it('finds a non-trivial set of branded budgets — the scan is not passing vacuously', () => {
    // A guard that silently matches nothing is the failure mode this repo keeps measuring.
    expect(brandedExports(code).length).toBeGreaterThanOrEqual(7);
  });

  it('EVERY branded budget is spent in the arithmetic that produces the floor', () => {
    const spending = spendingExpressions(code);
    const unaccounted = brandedExports(code).filter((name) => !spending.includes(name));
    // A branded constant absent from the sum is a duration the lease does not cover. That is the
    // twelfth-call defect, caught at the place a twelfth call must first declare itself.
    expect(unaccounted).toEqual([]);
  });

  it('the CARRIER cannot smuggle a value across the boundary — every ServeBudget field is a branded scalar', () => {
    // ServeBudget is the one thing that crosses into lib/gemini.ts, so a field of it that is not one
    // of the accounted scalars would be a duration spent inside the lease and summed nowhere —
    // exactly the shape rounds 4-6 kept finding, wearing the carrier as a disguise.
    const literal = code.slice(code.indexOf('export const SERVE_BUDGET'));
    const body = literal.slice(literal.indexOf('{'), literal.indexOf('})') + 1);
    const assigned = [...body.matchAll(/:\s*([A-Z0-9_]+)\s*,/g)].map((m) => m[1]);
    expect(assigned.length).toBeGreaterThanOrEqual(4);       // not passing vacuously
    const accounted = new Set(brandedExports(code));
    expect(assigned.filter((name) => !accounted.has(name))).toEqual([]);
  });

  it('every UNBRANDED export is unbranded ON PURPOSE, with the reason written down', () => {
    const allExports = [...code.matchAll(/export\s+const\s+([A-Z0-9_]+)\s*=/g)].map((m) => m[1]);
    const branded = new Set(brandedExports(code));
    const unexplained = allExports
      .filter((name) => !branded.has(name))
      .filter((name) => !(name in UNBRANDED_BY_DESIGN));
    // Forces the OTHER direction too: a new plain-number constant cannot appear here without
    // someone stating why it is not spent inside the lease.
    expect(unexplained).toEqual([]);
  });
});
