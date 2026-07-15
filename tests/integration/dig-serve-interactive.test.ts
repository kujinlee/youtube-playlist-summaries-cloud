// tests/integration/dig-serve-interactive.test.ts
//
// Task 6 (cloud dig-deeper frontend slice): REAL local-Supabase integration proof that the
// served cloud dig doc is interactive (nonced CSP + cloud poll engine, not the local SSE
// script) AND that opening it (html GET) plus polling its progress (dig-state GET) charges
// nothing — the money invariant for the serve path. Mirrors the auth-mock pattern from
// tests/integration/archive-route-cloud.test.ts (mock next/headers + @/lib/supabase/server
// only; everything else — RLS, real Postgres, real Supabase Storage — runs for real) and the
// blob-seeding pattern from tests/integration/dig-cloud.test.ts (writeDigSectionBlob writer,
// SupabaseBlobStore, sectionId === summary section's timeRange.startSec).

import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { writeDigSectionBlob } from '@/lib/dig/cloud/write-dig-section-blob';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { SupabaseClient } from '@supabase/supabase-js';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

import { GET as htmlGET } from '@/app/api/html/[id]/route';
import { GET as digStateGET } from '@/app/api/videos/[id]/dig-state/route';

const admin = adminClient();
const VIDEO_ID = 'digIntgVid01'; // <=20 chars, matches assertVideoId /^[A-Za-z0-9_-]{1,20}$/
// Real parseable section format (▶, en-dash range, trailing `s`) — same shape as dig-cloud.test.ts.
const SUMMARY_MD = `# T\n\n## 2. Encoder\n▶ [2:12–2:20](https://youtu.be/VID?t=132s)\nProse.\n`;
const SECTION_START_SEC = 132; // must equal the dig blob's sectionId/startSec (dig-merge.ts step-1 match)

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function htmlReq(videoId: string, qs: string): Request {
  return new Request(`http://localhost/api/html/${videoId}${qs ? `?${qs}` : ''}`);
}
function callHtml(videoId: string, qs: string) {
  return htmlGET(htmlReq(videoId, qs), { params: Promise.resolve({ id: videoId }) });
}
function digStateReq(videoId: string, qs: string): Request {
  return new Request(`http://localhost/api/videos/${videoId}/dig-state${qs ? `?${qs}` : ''}`);
}
function callDigState(videoId: string, qs: string) {
  return digStateGET(digStateReq(videoId, qs), { params: Promise.resolve({ id: videoId }) });
}

function sumLedger(rows: { amount_cents: number }[] | null): number {
  return (rows ?? []).reduce((a, r) => a + r.amount_cents, 0);
}

describe('cloud dig-deeper serve (integration, real DB) — interactive + no-charge', () => {
  it('serves an interactive cloud dig doc and charges nothing across serve + dig-state poll', async () => {
    const { user, email, password } = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(admin, user.id);
    const { videoId, base } = await seedPromotedVideo(admin, {
      ownerId: user.id, playlistId, videoId: VIDEO_ID, title: 'T',
    });
    await seedSummaryBlob(admin, user.id, playlistKey, base, SUMMARY_MD);

    // Write one CURRENT-version dig blob directly via the production writer (it stamps
    // DIG_GENERATOR_VERSION itself — do not hand-roll the frontmatter/version).
    const blobStore = new SupabaseBlobStore(admin, ARTIFACTS_BUCKET);
    const principal = { id: user.id, indexKey: playlistKey };
    await writeDigSectionBlob({
      blobStore, principal, base, videoId,
      sectionId: SECTION_START_SEC, startSec: SECTION_START_SEC,
      title: 'Encoder', language: 'en', sourceVideoUrl: `https://youtu.be/${videoId}`,
      bodyMarkdown: 'DUG-PROSE', generatedAt: new Date().toISOString(),
    });

    const { client } = await signInAs(email, password);
    mockClient = client;

    const { data: before } = await admin.from('spend_ledger').select('amount_cents');

    const res = await callHtml(videoId, `playlist=${playlistId}&type=dig-deeper`);
    const html = await res.text();

    const stateRes = await callDigState(videoId, `playlist=${playlistId}`);
    const stateBody = await stateRes.json();

    const { data: after } = await admin.from('spend_ledger').select('amount_cents');

    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Security-Policy')).toContain("script-src 'nonce-");
    expect(html).toContain('DUG-PROSE');           // dug section rendered
    expect(html).toContain('dig-state?playlist='); // cloud poll engine present (interactive)
    expect(html).not.toContain('EventSource');     // not the local SSE script

    expect(stateRes.status).toBe(200);
    expect(stateBody.sectionIds).toContain(SECTION_START_SEC);

    expect(sumLedger(after)).toBe(sumLedger(before)); // opening the doc AND polling charged nothing
  });
});
