// NOT RUN WITHOUT A LIVE STACK. global-setup.ts applies migrations and refuses to run if it cannot.
// A skipped money assertion reporting green is worse than a red one — do NOT add describe.skip here.
//
// ✅ EXECUTED 2026-08-24 against a live local stack: 7/7. (The header previously said these were
// unrun predictions — they are now measurements.)
//
// ⚠ SIGNATURES VERIFIED 2026-08-24 by opening helpers/clients.ts and helpers/seed.ts:
//   newUser() -> { user: { id }, email, password }        signInAs(email, password) -> { client, userId }
//   seedPlaylist(svc, ownerId) -> { playlistId, playlistKey }
//   seedPromotedVideo(svc, { ownerId, playlistId, ... }) -> { videoId, base }
//   seedSummaryBlob(svc, ownerId, playlistKey, base, md) -> void   — uploads at the EXACT key the
//   route reads, so do not hand-roll a blob.put + merge_video_data pair for it.
// ⚠ MOCK ONLY NEXT'S REQUEST PLUMBING, NEVER THE DATABASE. Measured 2026-08-24: without this the
// whole file failed 7/7 with `cookies() was called outside a request scope` — calling a route
// handler directly from jest gives it no Next request context, so `cookies()` throws before any
// assertion is reached and NOTHING about the correction path is exercised. The unit suite mocks
// next/headers for exactly this reason; the integration file inherited the omission.
//
// `createServerSupabase` is redirected to the REAL signed-in client for the seeded owner, so auth,
// RLS, the loader, the blob write and the ledger are all genuine. Only the cookie->client step is
// replaced, because that step is Next's, not ours.
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({})) }));
jest.mock('@/lib/supabase/server', () => ({
  ...jest.requireActual('@/lib/supabase/server'),
  createServerSupabase: jest.fn(() => currentOwnerClient),
}));

import type { SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';

/** The signed-in client the mocked createServerSupabase hands back. Set by seedCorrectable(). */
let currentOwnerClient: SupabaseClient;
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { POST } from '@/app/api/videos/[id]/regenerate/route';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';

jest.mock('@/lib/gemini', () => ({
  fixSummary: jest.fn(async (md: string) => ({
    text: md.replace('Clawcode', 'Claude Code'),
    usage: { promptTokens: 1000, outputTokens: 500 },
  })),
  extractQuickView: jest.fn(async () => ({ tldr: 'Corrected TL;DR.', takeaways: ['Corrected point'] })),
  assertCorrectionInputWithinCap: jest.fn(async () => {}),
  SUMMARY_MODEL: 'gemini-2.5-flash',
}));
import { fixSummary } from '@/lib/gemini';

const svc = adminClient();

const MD = `---
video_id: vvvvvvvvvvv
lang: EN
---

# T

**Channel:** C | **Duration:** 1:00 | **URL:** https://www.youtube.com/watch?v=vvvvvvvvvvv

---

## 1. Intro

▶ [0:00–1:00](https://www.youtube.com/watch?v=vvvvvvvvvvv&t=0s)

Clawcode is great.
`;

/** Seeds an owned playlist + promoted video and puts MD at the video's summaryMd key, so the route
 *  has a real body to read through the SAME principal it will write with. */
async function seedCorrectable() {
  const { user, email, password } = await newUser();
  const ownerId = user.id;
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId, base } = await seedPromotedVideo(svc, { ownerId, playlistId });
  await seedSummaryBlob(svc, ownerId, playlistKey, base, MD);
  await svc.rpc('merge_video_data', {
    p_playlist_id: playlistId, p_video_id: videoId, p_fields: { tags: ['ai', 'rag'] },
  });
  const { client } = await signInAs(email, password);
  currentOwnerClient = client;          // what the route will receive from createServerSupabase
  const principal = { id: ownerId, indexKey: playlistKey };
  const blob = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
  return { ownerId, email, password, client, playlistId, playlistKey, videoId, base, principal, blob, key: `${base}.md` };
}

function press(videoId: string, playlistId: string, body: Record<string, unknown>) {
  return POST(
    new Request(`http://localhost/api/videos/${videoId}/regenerate?playlist=${playlistId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
    { params: Promise.resolve({ id: videoId }) },
  );
}

beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });

// ⚠ WITHOUT THIS, `expect(fixSummary).not.toHaveBeenCalled()` MEASURES THE WHOLE FILE'S HISTORY.
// Measured 2026-08-24: the bare-press row failed with "Received number of calls: 3" — the three
// corrections applied by the tests ABOVE it. Both remaining failures were this, and neither said
// anything about the behaviour under test. `clearAllMocks` clears usage data only; the
// implementations from the jest.mock factory survive (that would be `resetAllMocks`).
beforeEach(() => { jest.clearAllMocks(); });
afterAll(() => { delete process.env.STORAGE_BACKEND; });

it('§7 cloud correction works — the stored blob holds the corrected text, not the original', async () => {
  const s = await seedCorrectable();
  const res = await press(s.videoId, s.playlistId, { corrections: 'Clawcode -> Claude Code' });
  expect(res.status).toBe(200);
  const stored = (await s.blob.get(s.principal, s.key))!.toString('utf-8');
  expect(stored).toContain('Claude Code');
  expect(stored).not.toContain('Clawcode is great');
});

it('§7 and the card — tldr, takeaways AND the Concepts line reflect the corrected document', async () => {
  const s = await seedCorrectable();
  await press(s.videoId, s.playlistId, { corrections: 'Clawcode -> Claude Code' });
  const { data } = await svc.from('videos').select('data').eq('video_id', s.videoId).single();
  expect(data!.data.tldr).toBe('Corrected TL;DR.');
  expect(data!.data.takeaways).toEqual(['Corrected point']);
  const stored = (await s.blob.get(s.principal, s.key))!.toString('utf-8');
  expect(stored).toContain('> **Concepts:** ai · rag');
});

it('§7 clearing works on Supabase — corrections are absent afterwards', async () => {
  // The defect this row exists for: updateVideoFields({ corrections: undefined }) reached
  // merge_video_data as {} because JSON drops undefined, so the clear was a silent no-op on this
  // backend only. Asserting on the LOCAL store would have proved nothing about it.
  const s = await seedCorrectable();
  await press(s.videoId, s.playlistId, { corrections: 'something' });
  await press(s.videoId, s.playlistId, { corrections: '' });
  const { data } = await svc.from('videos').select('data').eq('video_id', s.videoId).single();
  expect(data!.data.corrections).toBeUndefined();
});

it('§7 clearing an ALREADY-EMPTY field issues no call, so annotationsEditedAt does not move', async () => {
  const s = await seedCorrectable();
  const before = (await svc.from('videos').select('data').eq('video_id', s.videoId).single()).data!.data;
  await press(s.videoId, s.playlistId, { corrections: '' });
  const after = (await svc.from('videos').select('data').eq('video_id', s.videoId).single()).data!.data;
  expect(after.annotationsEditedAt).toEqual(before.annotationsEditedAt);
});

it('§7 a BARE press writes no blob and stamps no currency', async () => {
  const s = await seedCorrectable();
  const bodyBefore = (await s.blob.get(s.principal, s.key))!.toString('utf-8');
  const before = (await svc.from('videos').select('data').eq('video_id', s.videoId).single()).data!.data;

  await press(s.videoId, s.playlistId, {});   // bare press: no corrections key at all

  const bodyAfter = (await s.blob.get(s.principal, s.key))!.toString('utf-8');
  const after = (await svc.from('videos').select('data').eq('video_id', s.videoId).single()).data!.data;
  expect(bodyAfter).toBe(bodyBefore);                                  // byte-identical
  expect(after.mdCorrectionsHash).toEqual(before.mdCorrectionsHash);   // currency claim unmoved
  expect(after.mdGeneratedAt).toEqual(before.mdGeneratedAt);
  expect(fixSummary).not.toHaveBeenCalled();
});

it('§7 an oversized corrections field never reaches Gemini — 400, and no Gemini call', async () => {
  const s = await seedCorrectable();
  const res = await press(s.videoId, s.playlistId, { corrections: 'x'.repeat(1001) });
  expect(res.status).toBe(400);
  expect((await res.json()).code).toBe('corrections-too-long');
  expect(fixSummary).not.toHaveBeenCalled();
});

it('§7 the correction records spend, bounded — the ledger moves by the measured amount', async () => {
  const day = new Date().toISOString().slice(0, 10);
  const readLedger = async () =>
    (await svc.from('spend_ledger').select('actual_cents').eq('day', day).maybeSingle()).data?.actual_cents ?? 0;
  const s = await seedCorrectable();
  const before = await readLedger();
  await press(s.videoId, s.playlistId, { corrections: 'Clawcode -> Claude Code' });
  // usage { 1000, 500 } -> ceil((1000*30 + 500*250)/1e6) = ceil(0.155) = 1c
  expect(await readLedger() - before).toBe(1);
});
