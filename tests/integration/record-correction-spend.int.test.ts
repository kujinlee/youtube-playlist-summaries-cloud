// NEEDS A LIVE POSTGRES. global-setup.ts applies migrations and refuses to run if it cannot.
// ⚠ SIGNATURES VERIFIED against tests/integration/helpers/clients.ts 2026-08-24:
//   newUser(): Promise<{ user: { id }, email, password }>   signInAs(email, password): Promise<{ client, userId }>
//   anonSession(): Promise<{ client, userId }>              — `userClient` does not exist
import { adminClient, newUser, signInAs, anonSession } from './helpers/clients';
import {
  correctionActualCents, MAX_SUMMARY_OUTPUT_TOKENS, PROMPT_SCHEMA_OVERHEAD_TOKENS,
} from '@/lib/gemini-cost';

const svc = adminClient();
const utcDay = () => new Date().toISOString().slice(0, 10);

const ledger = async () =>
  (await svc.from('spend_ledger').select('actual_cents').eq('day', utcDay()).maybeSingle()).data?.actual_cents ?? 0;

const cfg = async () => (await svc.from('guardrail_config')
  .select('correction_max_cents, correction_max_calls_per_owner_day').eq('id', true).single()).data!;

async function freshUserClient() {
  const { email, password } = await newUser();
  const { client, userId } = await signInAs(email, password);
  return { client, userId };
}

// spend_ledger is GLOBAL and shared with every other integration suite — 10+ files call
// ensureGuardrailHeadroom (helpers/clients.ts:45) precisely because it accumulates across a run.
// Restore what these tests move, or a later suite fails on a cap this file consumed.
let ledgerAtStart = 0;
beforeAll(async () => { ledgerAtStart = await ledger(); });
afterAll(async () => {
  await svc.from('spend_ledger').update({ actual_cents: ledgerAtStart }).eq('day', utcDay());
});

// ── THE FALSIFIER THAT MATTERS ────────────────────────────────────────────────────────────────
it('bounds ONE owner to N calls/day AND the global ledger to N x ceiling', async () => {
  const { correction_max_cents: ceiling, correction_max_calls_per_owner_day: N } = await cfg();
  const { client } = await freshUserClient();
  const before = await ledger();

  const results = [];
  for (let i = 0; i < N + 1; i++) {
    results.push((await client.rpc('record_correction_spend', { p_cents: ceiling })).error);
  }

  // HALF ONE: exactly N succeed, and the (N+1)th is refused by NAME.
  expect(results.slice(0, N).every((e) => e === null)).toBe(true);
  expect(results[N]?.message).toMatch(/owner daily correction limit \d+ reached/);

  // HALF TWO: the GLOBAL ledger moved by at most N x ceiling. This is the assertion the previous
  // design would have failed — it is what "one account cannot exhaust everyone's cap" means.
  expect(await ledger() - before).toBe(N * ceiling);
  expect(N * ceiling).toBeLessThan(500 / 2);   // and that is a minority of daily_cap_cents (0011:28)
});

it('a SECOND owner is unaffected by the first owner hitting the limit', async () => {
  const { correction_max_cents: ceiling, correction_max_calls_per_owner_day: N } = await cfg();
  const a = await freshUserClient();
  for (let i = 0; i < N + 1; i++) await a.client.rpc('record_correction_spend', { p_cents: ceiling });
  const b = await freshUserClient();
  const { error } = await b.client.rpc('record_correction_spend', { p_cents: 1 });
  expect(error).toBeNull();   // the bound is PER OWNER; A cannot deny B
});

// ── the per-call ceiling, still correct and still necessary ───────────────────────────────────
it('REJECTS a value above the ceiling — it does not silently clamp', async () => {
  const { correction_max_cents: ceiling } = await cfg();
  const before = await ledger();
  const { client } = await freshUserClient();
  const { error } = await client.rpc('record_correction_spend', { p_cents: ceiling + 1 });
  expect(error?.message).toMatch(/correction spend \d+ exceeds ceiling \d+/);
  expect(await ledger()).toBe(before);   // nothing written — not even a truncated amount
});

it('accepts exactly the ceiling — the boundary is inclusive', async () => {
  const { correction_max_cents: ceiling } = await cfg();
  const { client } = await freshUserClient();
  expect((await client.rpc('record_correction_spend', { p_cents: ceiling })).error).toBeNull();
});

it('rejects a negative amount — the ledger only moves one way', async () => {
  const { client } = await freshUserClient();
  const { error } = await client.rpc('record_correction_spend', { p_cents: -5 });
  expect(error?.message).toMatch(/correction spend -5 exceeds ceiling/);
});

it('rejects NULL rather than falling through to a not-null violation', async () => {
  const { client } = await freshUserClient();
  const { error } = await client.rpc('record_correction_spend', { p_cents: null });
  expect(error?.message).toMatch(/p_cents is required/);
});

it('anon cannot execute it', async () => {
  const { client } = await anonSession();
  expect((await client.rpc('record_correction_spend', { p_cents: 1 })).error).not.toBeNull();
});

// CAP SOUNDNESS. The ceiling is a config number; the caps it must cover are TypeScript constants,
// and nothing ties them together. Assert the tie mechanically rather than trusting whoever next
// changes MAX_SUMMARY_OUTPUT_TOKENS to remember this row exists.
it('the ceiling covers the worst case §5.1 can produce, and N x ceiling stays a minority of the cap', async () => {
  const { correction_max_cents: ceiling, correction_max_calls_per_owner_day: N } = await cfg();
  const worst = correctionActualCents({
    promptTokens: MAX_SUMMARY_OUTPUT_TOKENS + PROMPT_SCHEMA_OVERHEAD_TOKENS,
    outputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
  }) * 3;                                     // fixSummary retries twice (gemini.ts:473)
  expect(ceiling).toBeGreaterThanOrEqual(worst);
  const { data } = await svc.from('guardrail_config').select('daily_cap_cents').eq('id', true).single();
  expect(N * ceiling).toBeLessThan(data!.daily_cap_cents / 2);
});
