// tests/integration/serve-config-invariant.test.ts
import { adminClient } from './helpers/clients';

const svc = adminClient();
const SAFETY_FRACTION = 0.2;
const MAX_OWNED_PROMOTED_DOCS_ANON = 2; // anon summary quota (0011); the fully-bounded case asserted hard

// NO beforeEach mutation — this suite pins the MIGRATION DEFAULTS after `db reset`. Setting the values
// here then asserting them would be tautological (Codex High-1): it would pass even if 0012's defaults
// were wrong, which is exactly what this invariant exists to catch. The suite must run against a freshly
// reset DB (Step 2/4 do `npx supabase db reset` first) so it reads the real 0012 defaults untouched.

it('the 0012 MIGRATION DEFAULTS satisfy the anon config invariant (§4.2) — read, do not set', async () => {
  const { data: cfg } = await svc.from('guardrail_config')
    .select('daily_cap_cents, magazine_est_cents, max_serve_attempts').single();
  // These are the reset-DB defaults (magazine_est_cents=6, max_serve_attempts=5, daily_cap_cents=500),
  // NOT values this test wrote. If a future migration retunes them past the bound, this fails.
  const worst = MAX_OWNED_PROMOTED_DOCS_ANON * cfg!.max_serve_attempts * cfg!.magazine_est_cents; // 2·5·6 = 60
  const bound = cfg!.daily_cap_cents * SAFETY_FRACTION;                                            // 500·0.2 = 100
  expect(worst).toBeLessThanOrEqual(bound);
});

it('documents the registered residual as deferred to 1G (NOT asserted as bounded)', async () => {
  // A registered account (summary quota 20) reclaim-loop = 20·5·6 = 600 > 100. This is the
  // attributable, bounded-fraction residual explicitly deferred to 1G per spec §9 — recorded here
  // (reading the same defaults) so the convergence trail shows it is known-and-accepted, not overlooked.
  const REGISTERED_DOCS = 20;
  const { data: cfg } = await svc.from('guardrail_config').select('daily_cap_cents, magazine_est_cents, max_serve_attempts').single();
  const registeredWorst = REGISTERED_DOCS * cfg!.max_serve_attempts * cfg!.magazine_est_cents;
  expect(registeredWorst).toBeGreaterThan(cfg!.daily_cap_cents * SAFETY_FRACTION); // deferred to 1G
});

it('(optional) a representative TUNED tuple also satisfies the invariant — this test MAY set values', async () => {
  // Separate from the defaults test: here mutation is legitimate because we are checking a hypothetical
  // retune, not the shipped defaults. Restore afterwards so no cross-file leakage.
  const { data: before } = await svc.from('guardrail_config').select('daily_cap_cents, magazine_est_cents, max_serve_attempts').single();
  await svc.from('guardrail_config').update({ daily_cap_cents: 800, magazine_est_cents: 8, max_serve_attempts: 4 }).eq('id', true);
  const { data: cfg } = await svc.from('guardrail_config').select('daily_cap_cents, magazine_est_cents, max_serve_attempts').single();
  expect(MAX_OWNED_PROMOTED_DOCS_ANON * cfg!.max_serve_attempts * cfg!.magazine_est_cents)
    .toBeLessThanOrEqual(cfg!.daily_cap_cents * SAFETY_FRACTION);
  await svc.from('guardrail_config').update(before!).eq('id', true);
});
