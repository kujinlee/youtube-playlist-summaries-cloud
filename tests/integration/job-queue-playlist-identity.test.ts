import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { randomUUID } from 'crypto';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

async function seedPlaylist(client: any, ownerId: string, key: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: key, playlist_url: `https://x/${key}` })
    .select('id').single();
  if (error) throw error; return data.id as string;
}

test('same (video,section,kind,version) under two playlists → two distinct jobs', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const plA = await seedPlaylist(client, userId, `A-${randomUUID()}`);
  const plB = await seedPlaylist(client, userId, `B-${randomUUID()}`);
  const vid = randomUUID();
  // T13: session-client enqueue_job (6-arg) is dropped — enqueue via the service client, owner explicit.
  const args = (pl: string) => ({
    p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
  });
  const a = await svc.rpc('enqueue_job', args(plA)); const b = await svc.rpc('enqueue_job', args(plB));
  expect(a.error).toBeNull(); expect(b.error).toBeNull();
  expect(a.data[0].job_id).not.toBe(b.data[0].job_id);
});

test('enqueue against another owner\'s playlist is rejected (composite FK: p_owner_id must own p_playlist_id)', async () => {
  const owner = await newUser(); const { client: oc, userId: oid } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(oc, oid, `V-${randomUUID()}`);
  const atk = await newUser();
  const res = await svc.rpc('enqueue_job', {
    p_owner_id: atk.user.id, p_playlist_id: victimPl, p_video_id: randomUUID(), p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
  });
  expect(res.error).not.toBeNull();
});
