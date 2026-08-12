/**
 * THE MONEY-PROTECTING ASSERTION FOR backlog #34.
 *
 * `resolveMagazineModel` decides whether to pay for a magazine model by asking storage whether the
 * cached one is there. On Supabase that answer is NOT proof: an object hidden by row-level security
 * returns the byte-identical 404 to one that never existed, so `tryGet` reports `absent` and the
 * money guard does not fire. Measured against hosted Supabase on 2026-08-11 (M1.4 gate B3): calling
 * `resolveMagazineModel` directly with the owner policy dropped re-reserved and re-generated a model
 * that was sitting in the bucket — spend 6c -> 12c, attempt_count 1 -> 2, a second live Gemini call.
 *
 * The application is nevertheless safe, and THIS is why: the only caller reaches the charging code
 * through `loadSummaryForServe`, which reads the summary markdown with the same session-scoped store
 * and the same principal, and FAILS CLOSED at 409 "repair needed" when that read comes back empty
 * (lib/html-doc/serve-summary-core.ts:66-67). Both keys live under `${id}/${indexKey}/` and the
 * storage policy grants on the first path segment alone (0007_storage_and_rpcs.sql:14), so a
 * permissions fault kills the markdown read first and the request ends before any reserve.
 *
 * That protection was ACCIDENTAL — an ordering property no signature required, no comment mentioned
 * and no test pinned, while the blob store's own comment claimed a 404 "IS provable absence". This
 * test makes it enforced. If someone later makes the markdown read tolerant of an empty result, the
 * double charge becomes reachable, and this goes red.
 *
 * WHEN THIS GOES RED: do not relax it. Find out what now reaches the reserve without proving the
 * folder is readable.
 */
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';

jest.mock('@/lib/gemini', () => {
  const generateMagazineModel = jest.fn(async () => {
    throw new Error('generateMagazineModel must NEVER be reached when the markdown is unreadable');
  });
  return {
    generateMagazineModel,
    generateMagazineModelForServe: jest.fn(() => generateMagazineModel()),
  };
});
import { generateMagazineModel } from '@/lib/gemini';

// getStorageBundle({ supabaseClient }) selects the Supabase stores only when
// STORAGE_BACKEND === 'supabase'; without this the load reads the LOCAL fs store and this test
// would assert nothing about the cloud path (repo convention — see html-serve-isolation.test.ts).
const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => {
  if (priorBackend === undefined) delete process.env.STORAGE_BACKEND;
  else process.env.STORAGE_BACKEND = priorBackend;
});

const svc = adminClient();
const MD = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;

async function spendTotal(): Promise<number> {
  const { data } = await svc.from('spend_ledger').select('reserved_cents, actual_cents');
  return (data ?? []).reduce(
    (n, r: { reserved_cents: number | null; actual_cents: number | null }) =>
      n + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0,
  );
}

it('an unreadable summary markdown ends the serve at 409 and cannot reach the charging code', async () => {
  const u = await newUser();
  const { playlistId, playlistKey } = await seedPlaylist(svc, u.user.id);
  const { videoId, base } = await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId });
  const { client } = await signInAs(u.email, u.password);

  // Control: with the markdown present the load SUCCEEDS. Without this the assertion below could
  // pass because the fixture was broken in some unrelated way — a 409 for the wrong reason is not
  // evidence that the short-circuit works.
  await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
  const healthy = await loadSummaryForServe(client, { videoId, playlistId, userId: u.user.id });
  expect(healthy.ok).toBe(true);

  const spendBefore = await spendTotal();
  const { data: chargeBefore } = await svc.from('serve_model_charge')
    .select('attempt_count').eq('owner_id', u.user.id);

  // Now make the markdown unreadable. Deleting the object reproduces exactly what the owner's
  // client observes when a policy denies it: `get` returns null either way — that collapsing is the
  // whole defect, and it is what makes this a faithful stand-in for the RLS fault measured in B3.
  await svc.storage.from('artifacts').remove([`${u.user.id}/${playlistKey}/${base}.md`]);

  const load = await loadSummaryForServe(client, { videoId, playlistId, userId: u.user.id });

  expect(load.ok).toBe(false);
  // 409 specifically, NOT merely "some error": a 404 here would mean the video was not resolved at
  // all, and the test would be passing without ever exercising the markdown read.
  expect((load as { status: number }).status).toBe(409);
  expect((load as { error: string }).error).toBe('repair needed');

  // The money assertions. Nothing downstream ran, so nothing was reserved, charged or generated.
  expect(generateMagazineModel).not.toHaveBeenCalled();
  expect(await spendTotal()).toBe(spendBefore);
  const { data: chargeAfter } = await svc.from('serve_model_charge')
    .select('attempt_count').eq('owner_id', u.user.id);
  expect(chargeAfter ?? []).toEqual(chargeBefore ?? []);
});
