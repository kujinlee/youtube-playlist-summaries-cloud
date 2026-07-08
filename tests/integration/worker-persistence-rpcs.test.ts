// tests/integration/worker-persistence-rpcs.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
jest.setTimeout(20_000);

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

test('reserve_video_slot is idempotent sequentially', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  const a = await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  const b = await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  expect(a.error).toBeNull(); expect(b.error).toBeNull(); expect(a.data).toBe(b.data);
  expect(typeof a.data).toBe('number'); expect(a.data).toBeGreaterThan(0);
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.serialNumber).toBe(a.data);
});

test('reserve_video_slot is idempotent under concurrency', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  const [a, b] = await Promise.all([
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid }),
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid }),
  ]);
  expect(a.error).toBeNull(); expect(b.error).toBeNull(); expect(a.data).toBe(b.data);
  expect(typeof a.data).toBe('number'); expect(a.data).toBeGreaterThan(0);
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.serialNumber).toBe(a.data);
});

test('reserve_video_slot allocates distinct serials/positions for distinct videos under concurrency', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId);
  const vidA = randomUUID(); const vidB = randomUUID(); const admin = adminClient();
  const [a, b] = await Promise.all([
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vidA }),
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vidB }),
  ]);
  expect(a.error).toBeNull(); expect(b.error).toBeNull();
  expect(typeof a.data).toBe('number'); expect(a.data).toBeGreaterThan(0);
  expect(typeof b.data).toBe('number'); expect(b.data).toBeGreaterThan(0);
  expect(a.data).not.toBe(b.data);
  const rowA = await admin.from('videos').select('position').eq('playlist_id', pl).eq('video_id', vidA).single();
  const rowB = await admin.from('videos').select('position').eq('playlist_id', pl).eq('video_id', vidB).single();
  expect(rowA.data!.position).not.toBe(rowB.data!.position);
});

test('status-only persist preserves the prior summaryMd key', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
  expect(row.data!.data.title).toBe('T');
});

test('persist_summary preserves a sibling artifact kind (deepDiveMd) across a summaryMd status write', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });

  // Seed a sibling artifact kind directly onto the row (simulating a concurrently-persisted
  // deep-dive artifact) so we can assert persist_summary never touches other artifact kinds.
  const before = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  const seededData = {
    ...before.data!.data,
    artifacts: {
      ...before.data!.data.artifacts,
      deepDiveMd: { key: 'dd.md', status: 'committed' },
    },
  };
  const seed = await admin.from('videos').update({ data: seededData }).eq('playlist_id', pl).eq('video_id', vid);
  expect(seed.error).toBeNull();

  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });

  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.artifacts.deepDiveMd).toEqual({ key: 'dd.md', status: 'committed' });
  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
});

test('persist_summary status is monotonic — a committed write never downgrades a promoted artifact', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  // Promote first, then a stale worker / retry re-persists the same key as 'committed'.
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'promoted' });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
});

test('persist_summary preserves operational fields owned by other features (archived) against the stale payload', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });

  // A concurrent membership reconciliation archives the video directly on the row.
  const before = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  const archivedData = { ...before.data!.data, archived: true };
  const seed = await admin.from('videos').update({ data: archivedData }).eq('playlist_id', pl).eq('video_id', vid);
  expect(seed.error).toBeNull();

  // The job's enqueue-time snapshot still carries archived:false — must NOT revert the row.
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T', archived: false }, p_artifact_status: 'promoted' });

  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.archived).toBe(true);
  expect(row.data!.data.title).toBe('T');
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
});

test('persist_summary preserves ALL concurrent non-summary state (membership order + other-feature fields) against the stale payload', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3 }, p_artifact_status: 'committed' });

  // A concurrent writer (reconcile_membership / merge_video_data / dig pipeline) reorders the video
  // and writes an other-feature field while the summary job is mid-flight.
  const before = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  const updated = { ...before.data!.data, playlistIndex: 9, digDeeperMd: 'dd.md' };
  const seed = await admin.from('videos').update({ data: updated }).eq('playlist_id', pl).eq('video_id', vid);
  expect(seed.error).toBeNull();

  // The stale enqueue-time payload still carries playlistIndex:3 and no digDeeperMd — persist_summary
  // must update ONLY summary-owned fields (ratings) and leave everything else untouched.
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3, ratings: { usefulness: 5 } }, p_artifact_status: 'promoted' });

  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.playlistIndex).toBe(9);        // membership order NOT reverted to the stale 3
  expect(row.data!.data.digDeeperMd).toBe('dd.md');    // other-feature field preserved
  expect(row.data!.data.ratings).toEqual({ usefulness: 5 }); // summary-owned field DID update
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
});

test('a status-only persist preserves existing summary-owned fields (language/ratings/docVersion), not just summaryMd', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  // Full summary persist populates the summary-owned fields.
  const full = { id: vid, summaryMd: '1_t.md', language: 'en', ratings: { usefulness: 4 }, overallScore: 4, docVersion: { major: 3, minor: 3 } };
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: full, p_artifact_status: 'committed' });
  // A status-only persist (p_video lacks summary fields) must NOT erase them — dropping docVersion
  // would defeat the handler's idempotency skip.
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.language).toBe('en');
  expect(row.data!.data.ratings).toEqual({ usefulness: 4 });
  expect(row.data!.data.overallScore).toBe(4);
  expect(row.data!.data.docVersion).toEqual({ major: 3, minor: 3 });
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
});

test('persist_summary monotonic status is KEY-SCOPED — a committed write with a NEW key is allowed through', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_old.md' }, p_artifact_status: 'promoted' });
  // A DIFFERENT key is a genuinely new artifact in committed state — it must NOT inherit the old
  // key's promoted status (else the row would claim a promoted artifact for an un-promoted blob).
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_new.md' }, p_artifact_status: 'committed' });
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_new.md');
  expect(row.data!.data.artifacts.summaryMd.status).toBe('committed');
});

test('reserve_video_slot raises for an existing row that has no serialNumber (invariant)', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  // Insert a raw videos row with no serialNumber in data (violates the reserve invariant).
  const ins = await admin.from('videos').insert({ playlist_id: pl, owner_id: userId, video_id: vid, position: 0, data: { id: vid } });
  expect(ins.error).toBeNull();
  const res = await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  expect(res.error).not.toBeNull();
  expect(res.data).toBeNull();
});

test('persist_summary raises when there is no video row', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  const res = await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
  expect(res.error).not.toBeNull();
});

test('reserve_video_slot rejects an owner mismatch', async () => {
  const owner = await newUser(); const { client: oc, userId: oid } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(oc, oid);
  const atk = await newUser(); const { userId: aid } = await signInAs(atk.email, atk.password);
  const admin = adminClient();
  const vid = randomUUID();
  const res = await admin.rpc('reserve_video_slot', { p_owner_id: aid, p_playlist_id: victimPl, p_video_id: vid });
  expect(res.error).not.toBeNull();
  const row = await admin.from('videos').select('id').eq('playlist_id', victimPl).eq('video_id', vid).maybeSingle();
  expect(row.data).toBeNull();
});

test('persist_summary rejects an owner mismatch', async () => {
  const owner = await newUser(); const { client: oc, userId: oid } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(oc, oid);
  const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: oid, p_playlist_id: victimPl, p_video_id: vid });
  const before = await admin.from('videos').select('data').eq('playlist_id', victimPl).eq('video_id', vid).single();
  const atk = await newUser(); const { userId: aid } = await signInAs(atk.email, atk.password);
  const res = await admin.rpc('persist_summary', { p_owner_id: aid, p_playlist_id: victimPl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
  expect(res.error).not.toBeNull();
  const after = await admin.from('videos').select('data').eq('playlist_id', victimPl).eq('video_id', vid).single();
  expect(after.data!.data).toEqual(before.data!.data);
});
