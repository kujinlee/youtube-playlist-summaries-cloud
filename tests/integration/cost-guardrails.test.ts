// tests/integration/cost-guardrails.test.ts
import { adminClient, newUser, signInAs } from './helpers/clients';

const svc = adminClient();

beforeEach(async () => {
  await svc.from('jobs').delete().neq('id', '00000000-0000-0000-0000-000000000000'); // clear accumulated jobs (velocity/queue-depth counts) — round-2 L1
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01'); // clear all ledger days
  await svc.from('usage_counters').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, summary_est_cents: 150, dig_est_cents: 150, // reset EVERY column — round-2 L
    summary_max_attempts: 1, dig_max_attempts: 1, max_duration_seconds: 1800, velocity_per_ip_hourly: 15,
    max_queue_depth: 200, max_free_users: 100, captcha_soft_threshold: 5,
  }).eq('id', true);
  await svc.from('quota_allowance').update({ monthly: 20 }).match({ is_anonymous: false, kind: 'summary' });
  await svc.from('quota_allowance').update({ monthly: 5 }).match({ is_anonymous: false, kind: 'dig' }); // all 4 allowance rows
  await svc.from('quota_allowance').update({ monthly: 0 }).match({ is_anonymous: true, kind: 'dig' });
  await svc.from('quota_allowance').update({ monthly: 2 }).match({ is_anonymous: true, kind: 'summary' });
});

it('seeds quota_allowance and the singleton guardrail_config', async () => {
  const { data: allow } = await svc.from('quota_allowance').select('*');
  // Assert the FULL 4-row seed set (order-independent) AND the exact row count — a missing
  // or extra row would otherwise go unasserted, since `.update().match(missingRow)` in
  // beforeEach is a silent 0-row no-op that can't surface a dropped seed row.
  expect(allow).toHaveLength(4);
  expect(allow).toEqual(expect.arrayContaining([
    { is_anonymous: false, kind: 'summary', monthly: 20 },
    { is_anonymous: false, kind: 'dig', monthly: 5 },
    { is_anonymous: true, kind: 'summary', monthly: 2 },
    { is_anonymous: true, kind: 'dig', monthly: 0 },
  ]));
  const { data: cfg } = await svc.from('guardrail_config').select('*').single();
  expect(cfg).toMatchObject({ daily_cap_cents: 500, summary_est_cents: 150, summary_max_attempts: 1, max_duration_seconds: 1800 });
});

it('lets an owner read only their own usage_counters and denies spend_ledger/guardrail_config reads', async () => {
  const a = await newUser(); const b = await newUser();
  await svc.from('usage_counters').insert([
    { owner_id: a.user.id, kind: 'summary', period_start: '2026-07-01', used: 1 },
    { owner_id: b.user.id, kind: 'summary', period_start: '2026-07-01', used: 1 }]);
  const { client: sa } = await signInAs(a.email, a.password);
  const { data: mine } = await sa.from('usage_counters').select('owner_id');
  expect(mine).toEqual([{ owner_id: a.user.id }]);
  const led = await sa.from('spend_ledger').select('*'); // no client grant → error, not []
  expect(led.error).toBeTruthy();
  const g = await sa.from('guardrail_config').select('*');
  expect(g.error).toBeTruthy();
});

it('rejects client writes to guardrail_config and usage_counters', async () => {
  const a = await newUser(); const { client: sa } = await signInAs(a.email, a.password);
  expect((await sa.from('guardrail_config').update({ daily_cap_cents: 999999 }).eq('id', true)).error).toBeTruthy();
  expect((await sa.from('usage_counters').insert({ owner_id: a.user.id, kind: 'summary', period_start: '2026-07-01', used: 999 })).error).toBeTruthy();
});
