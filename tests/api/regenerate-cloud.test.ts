jest.mock('../../lib/gemini');
jest.mock('../../lib/supabase/server');
// The route delegates the whole load to loadSummaryForServe, so THAT is the seam to mock —
// mocking resolveOwnedPlaylistKey/getStorageBundle would be mocking functions the route no
// longer calls directly.
jest.mock('../../lib/html-doc/serve-summary-core');
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({})) }));

import { POST } from '../../app/api/videos/[id]/regenerate/route';
import * as serverSupabase from '../../lib/supabase/server';
import * as serveCore from '../../lib/html-doc/serve-summary-core';
import * as gemini from '../../lib/gemini';

const PLAYLIST_ID = '11111111-2222-3333-4444-555555555555';
const VIDEO_ID = 'testVideoId1';
const MD = `---
video_id: testVideoId1
lang: EN
---

# T

**Channel:** C | **Duration:** 1:00 | **URL:** https://www.youtube.com/watch?v=testVideoId1

---

## 1. Intro

▶ [0:00–1:00](https://www.youtube.com/watch?v=testVideoId1&t=0s)

Clawcode.
`;

const mockPut = jest.fn();
const mockUpdateVideoFields = jest.fn();
const mockUpdateVideoAnnotations = jest.fn();
const mockRpc = jest.fn();

function post(body: Record<string, unknown>, qs = `?playlist=${PLAYLIST_ID}`) {
  return POST(
    new Request(`http://localhost/api/videos/${VIDEO_ID}/regenerate${qs}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
    { params: Promise.resolve({ id: VIDEO_ID }) },
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  jest.mocked(serverSupabase.createServerSupabase).mockReturnValue({
    auth: { getUser: async () => ({ data: { user: { id: 'owner-1' } } }) },
    rpc: mockRpc,
  } as never);
  mockRpc.mockResolvedValue({ error: null });
  mockPut.mockResolvedValue(undefined);
  mockUpdateVideoAnnotations.mockResolvedValue({ found: true });
  jest.mocked(serveCore.loadSummaryForServe).mockResolvedValue({
    ok: true,
    mdBytes: Buffer.from(MD, 'utf-8'),
    mdKey: 'a.md',
    base: 'a',
    title: 'T',
    principal: { id: 'owner-1', indexKey: 'pl-key' },
    playlistId: PLAYLIST_ID,
    video: { id: VIDEO_ID, summaryMd: 'a.md', tags: ['ai'] },
    bundle: {
      metadataStore: {
        updateVideoFields: mockUpdateVideoFields,
        updateVideoAnnotations: mockUpdateVideoAnnotations,
      },
      blobStore: { put: mockPut },
    },
  } as never);
  jest.mocked(gemini.fixSummary).mockResolvedValue({
    text: MD.replace('Clawcode', 'Claude Code'),
    usage: { promptTokens: 10_000, outputTokens: 4_000 },
  });
  jest.mocked(gemini.extractQuickView).mockResolvedValue({ tldr: 'New.', takeaways: ['P'] });
});

afterEach(() => { delete process.env.STORAGE_BACKEND; });

describe('regenerate — cloud branch', () => {
  it('401s when there is no authenticated user', async () => {
    jest.mocked(serverSupabase.createServerSupabase).mockReturnValue({
      auth: { getUser: async () => ({ data: { user: null } }) },
    } as never);
    expect((await post({ corrections: 'fix' })).status).toBe(401);
  });

  it('400s when playlist is not a UUID', async () => {
    expect((await post({ corrections: 'fix' }, '?playlist=nope')).status).toBe(400);
  });

  it('does not reach the loader when the playlist is not a UUID', async () => {
    // Beyond the plan: the guard exists to refuse BEFORE any DB call. A status-only assertion
    // would pass on an implementation that validated after loading.
    await post({ corrections: 'fix' }, '?playlist=nope');
    expect(jest.mocked(serveCore.loadSummaryForServe)).not.toHaveBeenCalled();
  });

  it('400s when outputFolder is sent in cloud mode', async () => {
    const res = await post({ corrections: 'fix', outputFolder: '/tmp/out' });
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe('outputFolder not valid on this backend');
  });

  it('rejects over-length corrections before the loader runs', async () => {
    const res = await post({ corrections: 'x'.repeat(1001) });
    expect(res.status).toBe(400);
    expect((await res.json()).code).toBe('corrections-too-long');
    expect(jest.mocked(serveCore.loadSummaryForServe)).not.toHaveBeenCalled();
  });

  // The loader owns owner-resolution, the artifact status gate, key validation and the blob read.
  // These cases assert the route SURFACES its verdict rather than re-deciding — a route that
  // hand-rolled the load would pass the 404 and silently drop the other three.
  it.each([
    ['not owned',                    { ok: false, status: 404, error: 'not found' },        404],
    ['artifact still committed',     { ok: false, status: 503, error: 'not ready, retry' }, 503],
    ['artifact not promoted',        { ok: false, status: 404, error: 'not found' },        404],
    ['corrupt summary key',          { ok: false, status: 409, error: 'corrupt summary key' }, 409],
    ['blob unreadable',              { ok: false, status: 409, error: 'repair needed' },    409],
  ])('surfaces the loader verdict for %s, and never calls Gemini', async (_label, verdict, status) => {
    jest.mocked(serveCore.loadSummaryForServe).mockResolvedValue(verdict as never);
    const res = await post({ corrections: 'fix' });
    expect(res.status).toBe(status);
    expect(jest.mocked(gemini.fixSummary)).not.toHaveBeenCalled();
    expect(mockPut).not.toHaveBeenCalled();
  });

  it('writes the corrected body with blobStore.put — never putStaged/promote', async () => {
    await post({ corrections: 'fix Clawcode' });
    expect(mockPut).toHaveBeenCalledTimes(1);
    const [, key, bytes] = mockPut.mock.calls[0];
    expect(key).toBe('a.md');
    expect(bytes.toString('utf-8')).toContain('Claude Code');
  });

  it('writes to the loader mdKey, not video.summaryMd', async () => {
    // Beyond the plan. The loader PREFERS artifacts.summaryMd.key and falls back to the top-level
    // field, so the two can differ — and writing to the wrong one targets a blob the artifact
    // record does not govern. With both equal to 'a.md' in the happy fixture, the assertion above
    // cannot tell them apart.
    jest.mocked(serveCore.loadSummaryForServe).mockResolvedValue({
      ok: true,
      mdBytes: Buffer.from(MD, 'utf-8'),
      mdKey: 'governed-by-the-artifact.md',
      base: 'a', title: 'T',
      principal: { id: 'owner-1', indexKey: 'pl-key' },
      playlistId: PLAYLIST_ID,
      video: { id: VIDEO_ID, summaryMd: 'stale-top-level-field.md', tags: ['ai'] },
      bundle: {
        metadataStore: { updateVideoFields: mockUpdateVideoFields, updateVideoAnnotations: mockUpdateVideoAnnotations },
        blobStore: { put: mockPut },
      },
    } as never);
    await post({ corrections: 'fix Clawcode' });
    expect(mockPut.mock.calls[0][1]).toBe('governed-by-the-artifact.md');
  });

  it('returns applied for a real correction and no-corrections for a bare press', async () => {
    expect((await (await post({ corrections: 'fix X' })).json()).outcome).toBe('applied');
    expect((await (await post({})).json()).outcome).toBe('no-corrections');
  });

  it('does not write the blob on a bare press', async () => {
    await post({});
    expect(mockPut).not.toHaveBeenCalled();
  });

  it('caps the paid call — passes a CloudGeminiCaps OBJECT, not undefined', async () => {
    // Beyond the plan, and the reason is gemini.ts:41: withCaps decides whether to cap AT ALL from
    // its second argument, so an uncapped cloud call reads correct in a diff.
    await post({ corrections: 'fix X' });
    const opts = jest.mocked(gemini.fixSummary).mock.calls[0][2];
    expect(opts.caps).toEqual(expect.objectContaining({ summaryOutputTokens: expect.any(Number) }));
  });

  it('413s when the preflight refuses the document', async () => {
    const { NonRetryableError } = jest.requireActual('../../lib/job-queue/errors');
    jest.mocked(gemini.fixSummary).mockRejectedValue(
      new NonRetryableError('correction input 9000 tokens exceeds cap 8192'),
    );
    const res = await post({ corrections: 'fix X' });
    expect(res.status).toBe(413);
    expect((await res.json()).code).toBe('summary-too-large');
  });
});

describe('spend recording (spec §5.2)', () => {
  it('records the measured cents after a successful correction', async () => {
    await post({ corrections: 'fix Clawcode' });
    // beforeEach mocks usage { promptTokens: 10_000, outputTokens: 4_000 } -> 2c
    expect(mockRpc).toHaveBeenCalledWith('record_correction_spend', { p_cents: 2 });
  });

  it('records the spend AFTER the blob write, never before', async () => {
    // Beyond the plan. Post-hoc means post-hoc: recording before the write would book spend for a
    // correction that might not become durable. Call order is the only thing that shows it.
    await post({ corrections: 'fix Clawcode' });
    expect(mockPut.mock.invocationCallOrder[0]).toBeLessThan(mockRpc.mock.invocationCallOrder[0]);
  });

  // ⚠ THE TITLE OF THIS TEST USED TO SAY "no correction, no spend". THAT WAS FALSE.
  // extractQuickView is a paid Gemini call (lib/gemini.ts:425) and §3 requires it on every press,
  // so a bare press DOES spend — slice A simply cannot see it. What this asserts is the narrow true
  // thing: no CORRECTION spend is recorded.
  it('records no CORRECTION spend on a bare press (the quick-view call is unmeasured, not free)', async () => {
    await post({});
    expect(mockRpc).not.toHaveBeenCalledWith('record_correction_spend', expect.anything());
    expect(jest.mocked(gemini.extractQuickView)).toHaveBeenCalledTimes(1);   // it DID run, and it DID cost
  });

  it('does not record 0 when usage was unmeasured', async () => {
    jest.mocked(gemini.fixSummary).mockResolvedValue({ text: MD, usage: null });
    await post({ corrections: 'fix X' });
    expect(mockRpc).not.toHaveBeenCalledWith('record_correction_spend', expect.anything());
  });

  it('still returns 200 when the ledger write fails — the correction landed', async () => {
    mockRpc.mockResolvedValue({ error: { message: 'ceiling exceeded' } });
    const res = await post({ corrections: 'fix X' });
    expect(res.status).toBe(200);
    expect((await res.json()).outcome).toBe('applied');
  });

  it('still returns 200 when the owner hit their daily bound', async () => {
    mockRpc.mockResolvedValue({ error: { message: 'owner daily correction limit 8 reached' } });
    const res = await post({ corrections: 'fix X' });
    expect(res.status).toBe(200);   // the correction happened; only the bookkeeping was refused
  });
});
