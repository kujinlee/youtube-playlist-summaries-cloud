import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';

// R2-H2: this serial suite enqueues many 150¢ summary jobs and deliberately leaves KEEP/back-dated
// reservations on today's ledger. Pin a generous daily_cap so cumulative reservations never trip
// PJ002 daily_cap_exceeded. Cap-SPECIFIC tests (behavior 16 "cap re-opens", behavior 26) set their
// OWN low daily_cap_cents inside the test and reset it after — see Task 12.
beforeAll(async () => { await ensureGuardrailHeadroom(adminClient()); });

describe('reservation-release: ledger_audit lockdown (Task 1)', () => {
  it('service_role can insert and read ledger_audit', async () => {
    const svc = adminClient();
    const day = '2026-07-16';
    const { error: insErr } = await svc
      .from('ledger_audit')
      .insert({ day, kind: 'release_underflow', expected_amt: 150, note: 't1' });
    expect(insErr).toBeNull();
    const { data, error } = await svc
      .from('ledger_audit')
      .select('kind, expected_amt')
      .eq('note', 't1');
    expect(error).toBeNull();
    expect(data).toEqual([{ kind: 'release_underflow', expected_amt: 150 }]);
  });

  it('a session client (authenticated) cannot read or write ledger_audit', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const read = await session.from('ledger_audit').select('*');
    // authenticated has NEITHER grant NOR policy → PostgREST returns permission-denied (42501).
    // Accept either an error OR zero rows — both prove the row is not exposed. (Do NOT swallow the
    // error with `data ?? []` — that would pass even if the surface were wrong; L2.)
    expect(read.error != null || (read.data ?? []).length === 0).toBe(true);
    const { error } = await session
      .from('ledger_audit')
      .insert({ day: '2026-07-16', kind: 'x', expected_amt: 1 });
    expect(error).not.toBeNull();                 // no grant → 42501 permission denied
  });
});
