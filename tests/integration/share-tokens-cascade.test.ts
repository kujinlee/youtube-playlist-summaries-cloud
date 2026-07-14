// Task 6 (0019_share_tokens_cascade.sql). Behaviors 1-3 from the plan's Enumerated Behaviors
// table: (1) orphan-cleanup is defensive/untestable directly — covered here only as "the
// constraint exists" (a clean ALTER implies the pre-cleanup DELETE ran without error); (2)
// cascade on delete; (3) cross-owner integrity via the composite (playlist_id, owner_id) FK.
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

const svc = adminClient();

function hexHash(): string {
  return randomUUID().replace(/-/g, '').padEnd(64, '0');
}

async function seedShareToken(ownerId: string, playlistId: string): Promise<string> {
  const { data, error } = await svc.from('share_tokens').insert({
    token_hash: hexHash(),
    owner_id: ownerId,
    playlist_id: playlistId,
    video_id: `v-${randomUUID()}`,
  }).select('id').single();
  if (error) throw error;
  return data!.id as string;
}

test('behavior 1: share_tokens_playlist_owner_fk constraint exists, composite, ON DELETE CASCADE (0019 applied cleanly)', async () => {
  // A clean ALTER (this constraint existing at all) implies the pre-ALTER orphan-cleanup
  // DELETE ran without error — the only signal available for that defensive, untestable step.
  const { data, error } = await svc.rpc('exec_sql', {
    sql: `select pg_get_constraintdef(oid) as def from pg_constraint
          where conname = 'share_tokens_playlist_owner_fk' and conrelid = 'public.share_tokens'::regclass`,
  });
  expect(error).toBeNull();
  expect(data).toHaveLength(1);
  expect(data[0].def).toMatch(
    /FOREIGN KEY \(playlist_id, owner_id\) REFERENCES (?:public\.)?playlists\(id, owner_id\) ON DELETE CASCADE/,
  );
});

test('behavior 2: deleting a playlist cascades to its share_tokens', async () => {
  const u = await newUser();
  const { client: owner, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(svc, userId);
  const tokenId = await seedShareToken(userId, playlistId);

  const del = await owner.from('playlists').delete().eq('id', playlistId);
  expect(del.error).toBeNull();

  const { data: rows } = await svc.from('share_tokens').select('id').eq('id', tokenId);
  expect(rows).toHaveLength(0);
});

test('behavior 3: cross-owner integrity — a share_token owner_id must match its playlist owner_id', async () => {
  const owner = await newUser();
  const other = await newUser();
  const { playlistId } = await seedPlaylist(svc, owner.user.id);

  // owner_id (other.user.id) does NOT match playlists.owner_id for playlistId → FK violation.
  const { error } = await svc.from('share_tokens').insert({
    token_hash: hexHash(),
    owner_id: other.user.id,
    playlist_id: playlistId,
    video_id: `v-${randomUUID()}`,
  });
  expect(error).not.toBeNull();
});
