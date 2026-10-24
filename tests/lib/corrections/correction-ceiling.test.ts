// Backlog #62, round 2 (Codex High). A press is recorded in ONE record_correction_spend call, and
// 0026 REJECTS — whole — any call above `correction_max_cents`. So the ceiling must cover the most a
// press can cost, or a press is silently recorded as nothing. Round 1 split an over-ceiling press
// across calls instead; each chunk spent one of the owner's daily call slots, and at calls = N-1 a
// [3,3,1] press recorded 3¢ (reproduced on local Postgres). That split is deleted; this is what
// replaces it — a red test on the change that would have needed it.
//
// What it derives from, all of it the REAL source:
//   attempts per press   FIX_SUMMARY_RETRIES + 1   (lib/gemini.ts — the fixSummary loop bound)
//   cost per attempt     CORRECTION_WORST_ATTEMPT_CENTS   (apply-core.ts — CORRECTION_CAPS bound,
//                        and also what an unmeasured or aborted attempt is charged)
//   the ceiling          the `default` 0026 declares for guardrail_config.correction_max_cents
//
// ⚠ The ceiling is a CONFIG ROW, so an operator UPDATE on a live database is outside what a unit
// test can see. The live value is asserted against the same product in
// tests/integration/record-correction-spend.int.test.ts ("the ceiling covers the worst case").
// Here, any migration that sets the value other than 0026's default makes this file red until it is
// taught to read it — refusing to guess is the point.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { FIX_SUMMARY_RETRIES } from '@/lib/gemini';
import { CORRECTION_WORST_ATTEMPT_CENTS } from '@/lib/corrections/apply-core';

const MIGRATIONS = join(process.cwd(), 'supabase', 'migrations');
const files = readdirSync(MIGRATIONS).filter((f) => f.endsWith('.sql')).sort();
const sqlOf = (f: string) => readFileSync(join(MIGRATIONS, f), 'utf-8').replace(/--[^\n]*/g, '');

function declaredCeiling(): number {
  const declarations = files.flatMap((f) =>
    [...sqlOf(f).matchAll(/add\s+column\s+correction_max_cents\s+int\s+not\s+null\s+default\s+(\d+)/gi)]
      .map((m) => ({ f, cents: Number(m[1]) })));
  expect(declarations.map((d) => d.f)).toEqual(['0026_record_correction_spend.sql']);
  return declarations[0].cents;
}

describe('0026\'s per-call ceiling covers the most one press can cost', () => {
  it('scans a real migration set — the read is not silently empty', () => {
    expect(files.length).toBeGreaterThan(20);
  });

  it('no migration other than 0026 SETS the ceiling — else this test must be taught to read it', () => {
    const setters = files.filter((f) =>
      /(update\s+guardrail_config[^;]*correction_max_cents|alter\s+column\s+correction_max_cents|insert\s+into\s+guardrail_config[^;]*correction_max_cents)/i
        .test(sqlOf(f)));
    expect(setters).toEqual([]);
  });

  it('worst press = attempts × worst attempt, and the ceiling is at least that', () => {
    const attempts = FIX_SUMMARY_RETRIES + 1;
    const worstPress = attempts * CORRECTION_WORST_ATTEMPT_CENTS;
    expect(declaredCeiling()).toBeGreaterThanOrEqual(worstPress);
  });
});
