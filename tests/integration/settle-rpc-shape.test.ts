// The premise `settleBounded`'s money decision rests on: what does a settle_serve_model call
// actually put in `data`?
//
// WHY THIS FILE EXISTS. Round-1 review H3 established that `settle_serve_model` `returns boolean`
// and answers false for a no-op, and that reading transport success as "settled" silently swallowed
// failed refunds. The fix compares `out.data === true`. That comparison is only correct if a
// SUCCESSFUL settle really arrives as the JavaScript boolean `true` — a claim about how PostgREST
// and supabase-js marshal a scalar-returning function, which had never been measured.
//
// THE EXISTING MONEY PIN CANNOT CATCH THIS. serve-doc-materialize.test.ts asserts the LEDGERS return
// to zero, and the database applies the refund correctly regardless of how the reply is shaped. If
// `data` were, say, `[{ settle_serve_model: true }]`, the ledgers would still balance, that test
// would still pass, and production would log "REFUND NOT APPLIED" on every successful refund while
// `settleBounded` reported failure. A green assertion on the ledger is not evidence about the reply.
//
// So this measures the reply itself, against a real database, and pins both answers.
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

const svc = adminClient();

// The whole integration suite shares one guardrail_config singleton and one spend_ledger day, so a
// file that reserves for real hits `at_capacity` purely from earlier files' spend. Measured: without
// this, reserve returned 'at_capacity' and these tests failed for a reason unrelated to what they
// assert.
beforeAll(async () => { await ensureGuardrailHeadroom(svc); });

async function seededOwner() {
  const u = await newUser();
  const { playlistId } = await seedPlaylist(svc, u.user.id);
  const { videoId } = await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId });
  const { client } = await signInAs(u.email, u.password);
  return { client, ownerId: u.user.id, playlistId, videoId };
}

/** Reserve for real, so the token is one the database actually minted. */
async function reserveFor(client: ReturnType<typeof adminClient>, playlistId: string, videoId: string) {
  const { data, error } = await client.rpc('reserve_serve_model', {
    p_playlist_id: playlistId, p_video_id: videoId,
  });
  expect(error).toBeNull();
  const row = (data as Array<{ status: string; release_token: string | null }>)[0];
  expect(row.status).toBe('reserved');
  expect(row.release_token).toBeTruthy();
  return row.release_token as string;
}

describe('settle_serve_model reply shape — the premise settleBounded reads', () => {
  it('a SUCCESSFUL settle arrives as the boolean true, not an array or an object', async () => {
    const { client, playlistId, videoId } = await seededOwner();
    const token = await reserveFor(client, playlistId, videoId);

    const { data, error } = await client.rpc('settle_serve_model', {
      p_token: token, p_released: false,
    });

    expect(error).toBeNull();
    // The exact comparison lib/html-doc/serve-doc.ts makes. Asserted as an identity, not a
    // truthiness check: `[{...}]` and `'true'` are both truthy and both would break the code.
    expect(data).toBe(true);
    expect(data === true).toBe(true);
  });

  it('a REFUSED settle (stale token) arrives as the boolean false, with NO error', async () => {
    const { client, playlistId, videoId } = await seededOwner();
    const token = await reserveFor(client, playlistId, videoId);
    // Settle once — this consumes the token (`release_token = null`).
    expect((await client.rpc('settle_serve_model', { p_token: token, p_released: false })).data).toBe(true);

    // Second settle with the now-stale token: the DB no-ops.
    const { data, error } = await client.rpc('settle_serve_model', {
      p_token: token, p_released: false,
    });

    // THE WHOLE POINT OF H3: refusal is reported in `data`, NOT as an error. Anything reading only
    // `error` — as the code did before round 1 — sees a success here.
    expect(error).toBeNull();
    expect(data).toBe(false);
  });

  // ── Migration 0025. The reason `indeterminate` stopped being unfalsifiable. ─────────────────
  // Three review rounds each produced a High on the settle signal, and each refined the vocabulary
  // of the report rather than adding the missing fact: there was no durable record that a settle
  // applied. ledger_audit held only the `release_underflow` exception, and serve_model_charge's
  // token is overwritten by the next reserve — so after the lease window nothing could answer
  // "did my settle land?". These assert the witness exists and is keyed by the token, which is what
  // makes the operator instruction in the `indeterminate` log a query someone can actually run.
  it('a SUCCESSFUL settle leaves a durable, token-keyed witness in ledger_audit', async () => {
    const { client, playlistId, videoId } = await seededOwner();
    const token = await reserveFor(client, playlistId, videoId);
    expect((await client.rpc('settle_serve_model', { p_token: token, p_released: false })).data).toBe(true);

    const { data, error } = await svc.from('ledger_audit')
      .select('kind, expected_amt, note').eq('kind', 'serve_settle').like('note', `${token}:%`);
    expect(error).toBeNull();
    expect(data).toEqual([{ kind: 'serve_settle', expected_amt: 0, note: `${token}:false` }]);
  });

  it('a REFUSED settle leaves NO witness — absence is the answer, not ambiguity', async () => {
    const { client } = await seededOwner();
    const token = '11111111-2222-3333-4444-555555555555';
    expect((await client.rpc('settle_serve_model', { p_token: token, p_released: true })).data).toBe(false);

    const { data } = await svc.from('ledger_audit')
      .select('kind').eq('kind', 'serve_settle').like('note', `${token}:%`);
    // The witness is written past the `not found` gate, so a row exists IF AND ONLY IF this token
    // settled. That biconditional is the whole property — without it, an empty result would be
    // consistent with both outcomes, which is exactly the round-3 finding.
    expect(data).toEqual([]);
  });

  it('a REFUND records the refunded amount, so the row is self-describing without a join', async () => {
    const { client, playlistId, videoId } = await seededOwner();
    const token = await reserveFor(client, playlistId, videoId);
    expect((await client.rpc('settle_serve_model', { p_token: token, p_released: true })).data).toBe(true);

    const { data } = await svc.from('ledger_audit')
      .select('expected_amt, note').eq('kind', 'serve_settle').like('note', `${token}:%`);
    expect(data).toHaveLength(1);
    expect(data![0].note).toBe(`${token}:true`);
    expect(data![0].expected_amt).toBeGreaterThan(0);   // the magazine estimate that was returned
  });

  it('a settle for a token that never existed is refused the same way, not raised', async () => {
    const { client } = await seededOwner();
    const { data, error } = await client.rpc('settle_serve_model', {
      p_token: '00000000-0000-0000-0000-000000000000', p_released: true,
    });
    expect(error).toBeNull();
    expect(data).toBe(false);
  });
});
