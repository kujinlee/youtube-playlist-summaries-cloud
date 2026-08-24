// NEEDS A LIVE POSTGRES. global-setup.ts applies migrations and refuses to run if it cannot.
// ⚠ SIGNATURES VERIFIED against tests/integration/helpers/clients.ts 2026-08-24:
//   newUser(): Promise<{ user: { id }, email, password }>   signInAs(email, password): Promise<{ client, userId }>
//   anonSession(): Promise<{ client, userId }>              — `userClient` does not exist
// ✅ EXECUTED 2026-08-24 against a live local stack: 9/9, plus all three step-5/6 mutations caught.
import { createClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
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

// ── THE FALSIFIER THAT MATTERS, IN TWO INDEPENDENT TESTS ──────────────────────────────────────
//
// ⚠ THESE WERE ONE TEST, AND THAT HID THE HALF THAT MATTERS. Measured 2026-08-24 by running the
// plan's own step-5 mutation (delete `where correction_spend.calls < v_max_calls`): the combined
// test failed on the REJECTION assertion — the (N+1)th call now succeeds, so `results[N]` is null
// and `.message` is undefined — and jest stops at the first failing expect. THE LEDGER ASSERTION
// WAS NEVER EVALUATED. The plan says in as many words that if only the rejection half fails, the
// test is not proving containment; that is exactly what happened, so the containment claim was
// resting on a line the mutation never reached. Split, neither half can mask the other.
async function exhaustOneOwner() {
  const { correction_max_cents: ceiling, correction_max_calls_per_owner_day: N } = await cfg();
  const { client } = await freshUserClient();
  const before = await ledger();
  const errors = [];
  for (let i = 0; i < N + 1; i++) {
    errors.push((await client.rpc('record_correction_spend', { p_cents: ceiling })).error);
  }
  return { ceiling, N, before, errors };
}

it('HALF ONE — exactly N calls succeed and the (N+1)th is refused BY NAME', async () => {
  const { N, errors } = await exhaustOneOwner();
  expect(errors.slice(0, N).every((e) => e === null)).toBe(true);
  expect(errors[N]?.message).toMatch(/owner daily correction limit \d+ reached/);
});

it('HALF TWO — the GLOBAL ledger moves by at most N x ceiling, a minority of the daily cap', async () => {
  // This is what "one account cannot exhaust everyone's cap" MEANS, and it is the assertion the
  // pre-(b′) design would have failed. It must be reachable independently of HALF ONE.
  const { ceiling, N, before } = await exhaustOneOwner();
  expect(await ledger() - before).toBe(N * ceiling);
  const { data } = await svc.from('guardrail_config').select('daily_cap_cents').eq('id', true).single();
  expect(N * ceiling).toBeLessThan(data!.daily_cap_cents / 2);
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

it('the anon ROLE cannot execute it', async () => {
  // ⚠ NOT `anonSession()`. MEASURED 2026-08-24: that helper calls signInAnonymously(), which mints a
  // REAL Supabase user whose Postgres role is `authenticated` — so it is granted EXECUTE, correctly,
  // and the assertion failed while the migration was right. `anon` the POSTGRES ROLE and `anon` the
  // anonymously-signed-in USER are different things sharing a word.
  //
  // What `revoke ... from anon` governs is the role, which you reach by using the anon key with NO
  // session at all. Verified independently in the catalog:
  //   has_function_privilege('anon', 'record_correction_spend(int)', 'EXECUTE') = false
  //   has_function_privilege('authenticated', …)                               = true
  //
  // That an anonymously-signed-in ACCOUNT can call this is the residual §5.2 states and accepts:
  // it reaches parity with reserve_serve_model, which grants anon deliberately. Closing it is
  // slice C.
  const client = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );
  const { error } = await client.rpc('record_correction_spend', { p_cents: 1 });
  expect(error).not.toBeNull();
  expect(error!.message).toMatch(/permission denied|not find the function/i);
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
