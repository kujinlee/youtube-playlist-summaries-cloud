// tests/integration/serve-config-invariant.test.ts
import { adminClient } from './helpers/clients';

const svc = adminClient();
const SAFETY_FRACTION = 0.2;

// ORDER-SAFETY (Codex Critical #2): the full `test:integration --runInBand` suite shares ONE DB,
// and other files mutate the `guardrail_config` singleton without restoring it (e.g.
// serve-model-charge.test.ts sets daily_cap_cents to 3/6; helpers/clients.ts's
// `ensureGuardrailHeadroom` sets it to 1_000_000). Reading that dirty row here would make this
// invariant flake/false-green depending on run order.
//
// The fix is NOT a hardcoded restore (`update({ daily_cap_cents: 500, ... })`) — that would
// reintroduce the exact tautology this suite exists to avoid: if a future migration retunes a
// default, a hardcoded literal here would silently mask the drift instead of catching it.
//
// `exec_sql` (0004) looked like the natural way to run `UPDATE ... SET col = DEFAULT`, but it is
// READ-ONLY BY DESIGN: it wraps whatever SQL is passed in `select coalesce(jsonb_agg(t), '[]') from
// (<sql>) t`. Confirmed against the running local stack that this rejects both a bare UPDATE
// (invalid inside a FROM-subquery) and a writable CTE (`with upd as (update ... returning ...)
// select * from upd` fails with "WITH clause containing a data-modifying statement must be at the
// top level" once nested inside exec_sql's wrapper) — so a genuine write cannot go through it.
//
// Instead: read the column's live DEFAULT expression from the Postgres catalog
// (`information_schema.columns`) via exec_sql — a genuine SELECT, matching its documented
// read-only catalog-inspection purpose — then apply that value with a normal PostgREST
// `.update()`. This restore is simultaneously ORDER-SAFE (undoes any prior file's mutation) and
// DRIFT-PROOF (a future migration changing a column default is picked up automatically; nothing
// is hardcoded in this file).
async function readColumnDefaults(cols: string[]): Promise<Record<string, number>> {
  const list = cols.map((c) => `'${c}'`).join(',');
  const { data, error } = await svc.rpc('exec_sql', {
    sql: `select column_name, column_default from information_schema.columns
          where table_schema = 'public' and table_name = 'guardrail_config' and column_name in (${list})`,
  });
  if (error) throw error;
  const out: Record<string, number> = {};
  for (const row of data as { column_name: string; column_default: string | null }[]) {
    const n = row.column_default === null ? NaN : Number(row.column_default);
    if (!Number.isInteger(n)) {
      throw new Error(`guardrail_config.${row.column_name} has no plain-integer DEFAULT (got ${JSON.stringify(row.column_default)})`);
    }
    out[row.column_name] = n;
  }
  for (const c of cols) {
    if (!(c in out)) throw new Error(`information_schema.columns had no row for guardrail_config.${c}`);
  }
  return out;
}

// `quota_allowance.monthly` has NO column default (0011 seeds it via explicit `insert ...
// values (...)` literals, not a column DEFAULT), so there is no catalog value to read back the
// way `readColumnDefaults` does for `guardrail_config`. It also turned out NOT to be read-only
// elsewhere as originally assumed: `cost-guardrails.test.ts` repeatedly `.update()`s the
// (false,'summary') row (to 2/3/1) without restoring it, and `helpers/clients.ts`'s
// `ensureGuardrailHeadroom` sets BOTH the (true,'summary') and (false,'summary') rows to
// 100_000 — confirmed empirically: running this file after the full `--runInBand` suite read a
// dirty 100_000 and failed (100_000·5·6 = 3,000,000 ≫ 100). Restoring to the 0011 seed literals
// here is therefore required for order-safety; unlike the `guardrail_config` restore, this one
// IS a hardcoded literal because no DEFAULT-based drift-proof mechanism exists for seeded row
// data — a future change to these seed values is itself a migration edit a developer must touch,
// not a silent drift this restore could mask.
const QUOTA_SEED_MONTHLY = { anon: 2, registered: 20 } as const; // 0011: insert ...(true,'summary',2),(false,'summary',20)

beforeAll(async () => {
  const defaults = await readColumnDefaults([
    'daily_cap_cents', 'magazine_est_cents', 'max_serve_attempts', 'per_owner_serve_daily_cents',
  ]);
  const { error } = await svc.from('guardrail_config').update(defaults).eq('id', true);
  if (error) throw error;

  const { error: anonErr } = await svc.from('quota_allowance')
    .update({ monthly: QUOTA_SEED_MONTHLY.anon }).match({ is_anonymous: true, kind: 'summary' });
  if (anonErr) throw anonErr;
  const { error: regErr } = await svc.from('quota_allowance')
    .update({ monthly: QUOTA_SEED_MONTHLY.registered }).match({ is_anonymous: false, kind: 'summary' });
  if (regErr) throw regErr;
});

// Codex Important #3: guard every value used in the arithmetic BEFORE computing the invariant, so
// a bad grant/RLS/typo/null fails loud (a thrown assertion) instead of silently NaN-passing
// (NaN comparisons are always false, and `toBeLessThanOrEqual`/`toBeGreaterThan` against NaN can
// hide a broken read rather than surface it).
function assertPositiveInt(value: unknown, label: string): number {
  expect(typeof value).toBe('number');
  const n = value as number;
  expect(Number.isInteger(n)).toBe(true);
  expect(n).toBeGreaterThan(0);
  return n;
}

async function readGuardrailConfig() {
  const { data, error } = await svc.from('guardrail_config')
    .select('daily_cap_cents, magazine_est_cents, max_serve_attempts, per_owner_serve_daily_cents').single();
  expect(error).toBeNull();
  expect(data).toBeTruthy();
  return {
    dailyCapCents: assertPositiveInt(data!.daily_cap_cents, 'guardrail_config.daily_cap_cents'),
    magazineEstCents: assertPositiveInt(data!.magazine_est_cents, 'guardrail_config.magazine_est_cents'),
    maxServeAttempts: assertPositiveInt(data!.max_serve_attempts, 'guardrail_config.max_serve_attempts'),
    perOwnerServeDailyCents: assertPositiveInt(data!.per_owner_serve_daily_cents, 'guardrail_config.per_owner_serve_daily_cents'),
  };
}

// Codex Critical #1: read the doc-count operands from `quota_allowance` (0011) rather than
// inlining 2 / 20 as magic numbers in the arithmetic. NOTE: because the beforeAll restores
// `quota_allowance` to the seed literals (2 / 20) for order-safety, this test does NOT catch a
// future quota-SEED drift (the restore masks it) — unlike the `guardrail_config` cost operands,
// which ARE drift-proof via information_schema column DEFAULTs. Making quota fully drift-proof
// requires the mutating files to restore it (or a canonical seed source) so this test can read
// LIVE quota with no self-reset. Tracked as a follow-up (Codex Task-8 re-check: SHIP-WITH-FOLLOWUP).
async function readQuotaMonthly(isAnonymous: boolean): Promise<number> {
  const { data, error } = await svc.from('quota_allowance')
    .select('monthly').match({ is_anonymous: isAnonymous, kind: 'summary' }).single();
  expect(error).toBeNull();
  expect(data).toBeTruthy();
  return assertPositiveInt(data!.monthly, `quota_allowance(is_anonymous=${isAnonymous},kind=summary).monthly`);
}

it('the 0012 MIGRATION DEFAULTS satisfy the anon config invariant (§4.2)', async () => {
  const anonDocs = await readQuotaMonthly(true);                // quota_allowance seed (0011): 2
  const { dailyCapCents, magazineEstCents, maxServeAttempts } = await readGuardrailConfig();
  const worst = anonDocs * maxServeAttempts * magazineEstCents;  // 2·5·6 = 60 against the reset-DB defaults
  const bound = dailyCapCents * SAFETY_FRACTION;                 // 500·0.2 = 100
  expect(worst).toBeLessThanOrEqual(bound);
});

it('1G per-owner serve cap bounds the registered residual within the safety fraction (§4.2)', async () => {
  // Pre-1G, a registered account (summary quota 20) reclaim-loop was unbounded across the month:
  // 20·5·6 = 600 > 100, the residual spec §9 flagged. 1G (migration 0014) added a per-owner DAILY
  // serve cap (`per_owner_serve_daily_cents`, default 60) so a single owner's per-day serve spend
  // can no longer exceed that value regardless of monthly quota. The live-config invariant is now
  // that this per-owner daily residual sits within the same bounded fraction of the global cap the
  // anon case satisfies — reading live config so a future retune of either column is caught, not
  // masked. (The pre-1G worst figure is asserted too, as the motivation this cap resolves.)
  const registeredDocs = await readQuotaMonthly(false);           // quota_allowance seed (0011): 20
  const { dailyCapCents, magazineEstCents, maxServeAttempts, perOwnerServeDailyCents } = await readGuardrailConfig();
  const preCapWorst = registeredDocs * maxServeAttempts * magazineEstCents;
  const bound = dailyCapCents * SAFETY_FRACTION;                  // 500·0.2 = 100
  expect(preCapWorst).toBeGreaterThan(bound);                    // 600 > 100 — the residual 1G exists to bound
  expect(perOwnerServeDailyCents).toBeLessThanOrEqual(bound);    // 60 <= 100 — now bounded by the per-owner daily cap
});
