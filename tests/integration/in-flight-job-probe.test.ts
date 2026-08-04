// tests/integration/in-flight-job-probe.test.ts
//
// Backlog #17 guard, rows 10-13 — the parts of `supabaseInFlightJobProbe` that only a real `jobs`
// table can prove: which statuses count as pending, that an expired lease still counts, that every
// job kind counts, and that the probe is scoped to one playlist.
//
// These are exactly the decisions a unit test with a fake probe cannot check, and getting any of
// them wrong is silent: a too-narrow probe reopens the relocation window, a too-broad one blocks
// repair forever.

import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { supabaseInFlightJobProbe } from '@/lib/cloud-sync/in-flight-job';

const svc = adminClient();

async function seedPlaylist(client: ReturnType<typeof adminClient>, ownerId: string, key: string) {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: key, playlist_url: `https://youtube.com/playlist?list=${key}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

/** Insert a job row directly so the status can be set precisely (enqueue_job always starts queued). */
async function insertJob(opts: {
  ownerId: string; playlistId: string; videoId: string;
  status: string; jobKind?: string; leaseExpiresAt?: string; updatedAt?: string;
}) {
  const { error } = await svc.from('jobs').insert({
    owner_id: opts.ownerId, playlist_id: opts.playlistId, video_id: opts.videoId,
    section_id: -1, job_kind: opts.jobKind ?? 'summary', job_version: '3.3',
    status: opts.status, payload: { n: 1 },
    ...(opts.leaseExpiresAt ? { lease_expires_at: opts.leaseExpiresAt, locked_by: 'w1' } : {}),
    ...(opts.updatedAt ? { updated_at: opts.updatedAt } : {}),
  });
  if (error) throw error;
}

const minutesAgo = (n: number) => new Date(Date.now() - n * 60_000).toISOString();

describe('supabaseInFlightJobProbe against a live jobs table', () => {
  it('reports pending for queued and active, and NOT for terminal states', async () => {
    const u = await newUser();
    const { client, userId } = await signInAs(u.email, u.password);
    const key = `k-${randomUUID()}`;
    const pl = await seedPlaylist(svc, userId, key);
    const probe = supabaseInFlightJobProbe(client, userId);

    // Row 10 — only jobs that may still WRITE block a relocation. This is the COMPLETE status
    // domain from the CHECK constraint on `jobs`; enumerating it in full is the point, because a
    // status added later must force a decision here rather than defaulting to "does not block".
    const cases: Array<[string, boolean]> = [
      ['queued', true],
      ['active', true],
      ['completed', false],     // handler's writes returned before completion; already under old base
      // `failed` is transient: fail_job sets 'queued' with backoff while attempts remain
      // (0008:154-159), so a retryable job is caught as 'queued'. A row sitting at 'failed' threw
      // before completing, so anything it wrote it wrote already.
      ['failed', false],
      // dead_letter/cancelled block ONLY while recently swept (asserted separately below); these
      // rows are aged past the bound so this case exercises the not-recent branch.
      ['dead_letter', false],
      ['cancelled', false],
    ];
    for (const [status, expected] of cases) {
      const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
      await insertJob({ ownerId: userId, playlistId: pl, videoId, status, updatedAt: minutesAgo(60) });
      await expect(probe(key, videoId)).resolves.toEqual({ ok: true, inFlight: expected });
    }
  });

  // Codex adversarial review, Blocking #1. `sweep_expired_leases` (0008:167-181) moves an ACTIVE job
  // whose lease expired straight to dead_letter (attempts exhausted) or cancelled (cancel requested)
  // and clears the lease columns — while the worker that claimed it may still be inside its Gemini
  // call, holding the base it pinned. The row looks finished; the process is not.
  it('BLOCKS on a RECENTLY swept dead_letter/cancelled row — a worker may still be live', async () => {
    const u = await newUser();
    const { client, userId } = await signInAs(u.email, u.password);
    const key = `k-${randomUUID()}`;
    const pl = await seedPlaylist(svc, userId, key);
    const probe = supabaseInFlightJobProbe(client, userId);

    for (const status of ['dead_letter', 'cancelled']) {
      const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
      await insertJob({ ownerId: userId, playlistId: pl, videoId, status, updatedAt: minutesAgo(1) });
      await expect(probe(key, videoId)).resolves.toEqual({ ok: true, inFlight: true });
    }
  });

  // The other half, and it matters just as much: the block must EXPIRE. Without a bound, one
  // dead_letter row would stop a video's base ever being repaired — trading a narrow race for a
  // permanent stall. The bound is worker-runner.ts:45's wallClockMs (600_000), which caps how long
  // any worker can outlive its claim.
  it('STOPS blocking once a swept row is older than the worker wall-clock cap', async () => {
    const u = await newUser();
    const { client, userId } = await signInAs(u.email, u.password);
    const key = `k-${randomUUID()}`;
    const pl = await seedPlaylist(svc, userId, key);
    const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;

    // 11 minutes > the 10-minute cap, so no worker from that claim can still be running.
    await insertJob({
      ownerId: userId, playlistId: pl, videoId, status: 'dead_letter', updatedAt: minutesAgo(11),
    });

    await expect(supabaseInFlightJobProbe(client, userId)(key, videoId))
      .resolves.toEqual({ ok: true, inFlight: false });
  });

  it('still reports pending for an ACTIVE job whose lease has expired', async () => {
    const u = await newUser();
    const { client, userId } = await signInAs(u.email, u.password);
    const key = `k-${randomUUID()}`;
    const pl = await seedPlaylist(svc, userId, key);
    const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;

    // Row 11 — an expired lease means the worker probably died, NOT that the work is finished. The
    // reaper reclaims it and the retry writes, so this must still block.
    await insertJob({
      ownerId: userId, playlistId: pl, videoId, status: 'active',
      leaseExpiresAt: new Date(Date.now() - 60_000).toISOString(),
    });

    await expect(supabaseInFlightJobProbe(client, userId)(key, videoId))
      .resolves.toEqual({ ok: true, inFlight: true });
  });

  it('reports pending for a DIG job, not only a summary job', async () => {
    const u = await newUser();
    const { client, userId } = await signInAs(u.email, u.password);
    const key = `k-${randomUUID()}`;
    const pl = await seedPlaylist(svc, userId, key);
    const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;

    // Row 12 — dig-handler.ts:51-57 pins `base` before its own Gemini call, exactly like the summary
    // handler. A job_kind filter here would silently reopen the window for digs.
    await insertJob({ ownerId: userId, playlistId: pl, videoId, status: 'queued', jobKind: 'dig' });

    await expect(supabaseInFlightJobProbe(client, userId)(key, videoId))
      .resolves.toEqual({ ok: true, inFlight: true });
  });

  it('does NOT report pending for the same video under a different playlist', async () => {
    const u = await newUser();
    const { client, userId } = await signInAs(u.email, u.password);
    const keyA = `k-${randomUUID()}`;
    const keyB = `k-${randomUUID()}`;
    const plA = await seedPlaylist(svc, userId, keyA);
    await seedPlaylist(svc, userId, keyB);
    const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;

    // Row 13 — `base` is per-playlist (the serial is allocated per playlist), so playlist A's job
    // writes a different address and cannot collide with a relocation in playlist B. Blocking would
    // be a false positive that stalls repair for no benefit.
    await insertJob({ ownerId: userId, playlistId: plA, videoId, status: 'queued' });

    const probe = supabaseInFlightJobProbe(client, userId);
    await expect(probe(keyA, videoId)).resolves.toEqual({ ok: true, inFlight: true });
    await expect(probe(keyB, videoId)).resolves.toEqual({ ok: true, inFlight: false });
  });

  it('fails CLOSED when the playlist key cannot be resolved', async () => {
    const u = await newUser();
    const { client, userId } = await signInAs(u.email, u.password);

    // Reaching the probe means A3 is relocating a video that exists on cloud, so its playlist must
    // exist too. Not seeing it means our view is wrong — refuse rather than read a missing playlist
    // as "no jobs pending", which would let the relocation proceed unguarded.
    const res = await supabaseInFlightJobProbe(client, userId)(`k-${randomUUID()}`, 'vidmissing001');
    expect(res.ok).toBe(false);
  });

  // The owner predicate on the playlist lookup had ZERO coverage when first added: every other test
  // here uses a user JWT, where RLS already narrows playlists to the caller, so removing the
  // predicate left all 8 tests green. A guard that passes in both the buggy and the fixed world is
  // documentation, not a guard — so this exercises the one caller shape where it is load-bearing.
  //
  // `playlist_key` is unique only per OWNER (0001:17). Handed a service-role client, which sees
  // every tenant, a key-only lookup matches two rows; `maybeSingle()` then fails, or — worse, on a
  // single cross-tenant match — binds another tenant's playlist id and counts THEIR jobs.
  it('resolves the right tenant when the client can see every playlist (service role)', async () => {
    const a = await newUser();
    const b = await newUser();
    const { userId: aId } = await signInAs(a.email, a.password);
    const { userId: bId } = await signInAs(b.email, b.password);

    // The same playlist_key under two different owners — permitted by unique(owner_id, playlist_key).
    const sharedKey = `k-${randomUUID()}`;
    const plA = await seedPlaylist(svc, aId, sharedKey);
    await seedPlaylist(svc, bId, sharedKey);

    const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
    await insertJob({ ownerId: aId, playlistId: plA, videoId, status: 'queued' });

    // Scoped to A, the service-role probe must find A's pending job...
    await expect(supabaseInFlightJobProbe(svc, aId)(sharedKey, videoId))
      .resolves.toEqual({ ok: true, inFlight: true });
    // ...and scoped to B it must answer about B's playlist, which has no such job — not error out on
    // an ambiguous match, and not report A's job as B's.
    await expect(supabaseInFlightJobProbe(svc, bId)(sharedKey, videoId))
      .resolves.toEqual({ ok: true, inFlight: false });
  });

  it("cannot see another owner's job (RLS scopes the probe)", async () => {
    const a = await newUser();
    const b = await newUser();
    const { userId: aId } = await signInAs(a.email, a.password);
    const { client: bClient, userId: bId } = await signInAs(b.email, b.password);
    const key = `k-${randomUUID()}`;
    const pl = await seedPlaylist(svc, aId, key);
    const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
    await insertJob({ ownerId: aId, playlistId: pl, videoId, status: 'queued' });

    // B cannot resolve A's playlist at all, so the probe refuses rather than reporting a confident
    // "nothing pending" about a playlist it is not allowed to see.
    const res = await supabaseInFlightJobProbe(bClient, bId)(key, videoId);
    expect(res.ok).toBe(false);
  });
});
