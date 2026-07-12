const PID = '11111111-1111-1111-1111-111111111111';
const validVideo = 'vid123';
const promotedSummaryMd = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;

let mockIndexVideos: any[];
let mockMdBytes: Buffer | null;
let mockResolve: any;
let mockBlobGet: jest.Mock;
let mockPlaylistKey: string | null;

// Mock header copied from tests/api/html-serve-cloud.test.ts:1-45 (adapted: no next/headers or
// supabase/server mocks needed since serve-summary-core takes a supabase client directly, not via
// cookies/createServerSupabase — those belong to the route layer, not this helper).
jest.mock('@/lib/storage/resolve', () => {
  const actual = jest.requireActual('@/lib/storage/resolve');
  return {
    ...actual,
    getStorageBundle: jest.fn((arg?: { supabaseClient?: unknown }) => {
      if (!arg || !arg.supabaseClient) throw new Error('getStorageBundle called without a session supabaseClient');
      return {
        metadataStore: { readIndex: async () => ({ videos: mockIndexVideos }) },
        blobStore: { get: mockBlobGet },
      };
    }),
    getPrincipalFromSession: () => ({ id: 'owner-1', indexKey: 'pk' }),
  };
});
jest.mock('@/lib/html-doc/serve-doc', () => ({ resolveMagazineModel: jest.fn(async () => mockResolve) }));
jest.mock('@/lib/storage/serve-playlist', () => ({ resolveOwnedPlaylistKey: async () => mockPlaylistKey }));

import { loadSummaryForServe, resolveAndParse } from '@/lib/html-doc/serve-summary-core';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
const mockResolveMagazineModel = resolveMagazineModel as jest.Mock;

const sessionClient = { __session: true } as any;

// Mirrors the worker row (summary-handler.ts:149-164): top-level summaryMd + language + the promoted artifact.
const promotedVideo = {
  id: validVideo, language: 'en', summaryMd: `${validVideo}.md`,
  artifacts: { summaryMd: { key: `${validVideo}.md`, status: 'promoted' } },
};

beforeEach(() => {
  mockIndexVideos = [promotedVideo];
  mockMdBytes = Buffer.from(promotedSummaryMd, 'utf-8');
  mockBlobGet = jest.fn(async () => mockMdBytes);
  mockResolve = { status: 'ok', model: { sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] } };
  mockPlaylistKey = 'pk';
  mockResolveMagazineModel.mockClear();
});

describe('loadSummaryForServe', () => {
  it('gates committed → 503', async () => {
    mockIndexVideos = [{ ...promotedVideo, artifacts: { summaryMd: { status: 'committed' } } }];
    const r = await loadSummaryForServe(sessionClient, { videoId: validVideo, playlistId: PID, userId: 'u' });
    expect(r).toMatchObject({ ok: false, status: 503, error: 'not ready, retry' }); // exact string — guards drift
  });

  it('unknown video → 404', async () => {
    mockIndexVideos = [];
    const r = await loadSummaryForServe(sessionClient, { videoId: validVideo, playlistId: PID, userId: 'u' });
    expect(r).toMatchObject({ ok: false, status: 404, error: 'not found' });
  });

  it('foreign/unowned playlist → 404', async () => {
    mockPlaylistKey = null;
    const r = await loadSummaryForServe(sessionClient, { videoId: validVideo, playlistId: PID, userId: 'u' });
    expect(r).toMatchObject({ ok: false, status: 404, error: 'not found' });
  });

  it('rejects a nested mdKey with 409 BEFORE reading the blob', async () => {
    mockIndexVideos = [{
      ...promotedVideo,
      artifacts: { summaryMd: { key: 'nested/foo.md', status: 'promoted' } },
    }];
    const r = await loadSummaryForServe(sessionClient, { videoId: validVideo, playlistId: PID, userId: 'u' });
    expect(r).toMatchObject({ ok: false, status: 409, error: 'corrupt summary key' });
    expect(mockBlobGet).not.toHaveBeenCalled();
  });

  it('promoted but blob missing → 409 repair needed', async () => {
    mockMdBytes = null;
    const r = await loadSummaryForServe(sessionClient, { videoId: validVideo, playlistId: PID, userId: 'u' });
    expect(r).toMatchObject({ ok: false, status: 409, error: 'repair needed' });
  });

  it('promoted → ok WITHOUT resolving the model', async () => {
    const r = await loadSummaryForServe(sessionClient, { videoId: validVideo, playlistId: PID, userId: 'u' });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.mdKey).toBe(`${validVideo}.md`);
      expect(r.mdBytes.toString('utf-8')).toBe(promotedSummaryMd);
      expect(r.base).toBe(validVideo);
    }
    expect(mockResolveMagazineModel).not.toHaveBeenCalled();
  });
});

describe('resolveAndParse', () => {
  async function okLoad() {
    const r = await loadSummaryForServe(sessionClient, { videoId: validVideo, playlistId: PID, userId: 'u' });
    if (!r.ok) throw new Error('setup: expected ok load');
    return r;
  }

  it('maps denied → 404', async () => {
    mockResolve = { status: 'denied' };
    const r = await resolveAndParse(sessionClient, await okLoad());
    expect(r).toMatchObject({ ok: false, status: 404, error: 'not found' });
  });

  it('maps busy → 503 "generating, retry shortly"', async () => {
    mockResolve = { status: 'busy' };
    const r = await resolveAndParse(sessionClient, await okLoad());
    expect(r).toMatchObject({ ok: false, status: 503, error: 'generating, retry shortly' });
  });

  it('maps attempts_exhausted → 503 "temporarily unavailable, try later"', async () => {
    mockResolve = { status: 'attempts_exhausted' };
    const r = await resolveAndParse(sessionClient, await okLoad());
    expect(r).toMatchObject({ ok: false, status: 503, error: 'temporarily unavailable, try later' });
  });

  it('maps at_capacity → 503 "at capacity"', async () => {
    mockResolve = { status: 'at_capacity' };
    const r = await resolveAndParse(sessionClient, await okLoad());
    expect(r).toMatchObject({ ok: false, status: 503, error: 'at capacity' });
  });

  it('maps over_budget → 503 "daily refresh budget reached, try tomorrow"', async () => {
    mockResolve = { status: 'over_budget' };
    const r = await resolveAndParse(sessionClient, await okLoad());
    expect(r).toMatchObject({ ok: false, status: 503, error: 'daily refresh budget reached, try tomorrow' });
  });

  it('maps ok → { ok:true, parsed, model, stale }', async () => {
    mockResolve = { status: 'ok', model: { sections: [] }, stale: true };
    const r = await resolveAndParse(sessionClient, await okLoad());
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.model).toEqual({ sections: [] });
      expect(r.stale).toBe(true);
      expect(r.parsed.sourceMd).toBe(`${validVideo}.md`);
    }
  });

  it('ok with no stale field → stale coerces to false', async () => {
    mockResolve = { status: 'ok', model: { sections: [] } };
    const r = await resolveAndParse(sessionClient, await okLoad());
    expect(r).toMatchObject({ ok: true, stale: false });
  });
});
