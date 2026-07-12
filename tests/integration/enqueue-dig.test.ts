// tests/integration/enqueue-dig.test.ts
//
// Task 1 (cloud dig-deeper generation slice): confirms enqueue_job admits
// job_kind='dig' after migration 0018. Uses the real local Supabase via the
// service client — mirrors the setup in tests/integration/summary-handler.test.ts.

import { adminClient, newUser, anonSession, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

const admin = adminClient();

async function enqueueDigRpc(ownerId: string, playlistId: string, videoId: string, sectionId: number) {
  return admin.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: sectionId,
    p_job_kind: 'dig', p_job_version: 'dig-9', p_payload: { durationSeconds: 600 }, p_enqueue_ip: null,
  });
}

describe('enqueue_job admits dig', () => {
  beforeAll(async () => { await ensureGuardrailHeadroom(admin); });

  it('enqueues a dig job and debits the dig quota', async () => {
    const { user } = await newUser();
    const { playlistId } = await seedPlaylist(admin, user.id);
    const { data, error } = await enqueueDigRpc(user.id, playlistId, 'vid-dig-1', 132);
    expect(error).toBeNull();
    expect(data![0].status).toBe('queued');
    const { data: uc } = await admin.from('usage_counters').select('used')
      .eq('owner_id', user.id).eq('kind', 'dig').single();
    expect(uc!.used).toBe(1);
  });

  it('a second identical enqueue joins (idempotent, no double charge)', async () => {
    const { user } = await newUser();
    const { playlistId } = await seedPlaylist(admin, user.id);
    await enqueueDigRpc(user.id, playlistId, 'vid-dig-2', 132);
    const { data } = await enqueueDigRpc(user.id, playlistId, 'vid-dig-2', 132);
    expect(data![0].joined).toBe(true);
    const { data: uc } = await admin.from('usage_counters').select('used')
      .eq('owner_id', user.id).eq('kind', 'dig').single();
    expect(uc!.used).toBe(1); // still 1 — join did not re-charge
  });

  it('anonymous user (dig allowance 0) is rejected with quota_exceeded (PJ001)', async () => {
    // `profiles.is_anonymous` is immutable (profiles_is_anonymous_immutable trigger) — you CANNOT
    // update it. Create a genuine anonymous user via the anon sign-up path so provisioning sets it.
    const { userId: anonId } = await anonSession();
    const { data: prof } = await admin.from('profiles').select('is_anonymous').eq('id', anonId).single();
    expect(prof!.is_anonymous).toBe(true); // guard: prove we really have an anon before asserting the reject
    const { playlistId } = await seedPlaylist(admin, anonId);
    const { error } = await enqueueDigRpc(anonId, playlistId, 'vid-dig-3', 132);
    expect(error?.code).toBe('PJ001');
  });
});
