import { loadDigForServe } from '@/lib/dig/cloud/load-dig-for-serve';
import * as serveCore from '@/lib/html-doc/serve-summary-core';
import * as serveDoc from '@/lib/html-doc/serve-doc';
import * as modelStore from '@/lib/html-doc/model-store';
import * as digGen from '@/lib/dig/generate';
import * as gemini from '@/lib/gemini';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';

// Automock (not jest.spyOn) — this project's Next/SWC jest transform emits non-configurable
// named-export bindings for these lib modules, so `jest.spyOn(namespace, 'fn')` throws
// "Cannot redefine property" (verified: fails even on a single first-call spy, in isolation,
// for every one of these five exports). jest.mock() replaces the module wholesale at require
// time instead of trying to redefine a live binding, which works reliably across repeated
// tests. Semantics are unchanged: each test still selects its own mock behavior per function.
jest.mock('@/lib/html-doc/serve-summary-core');
jest.mock('@/lib/html-doc/serve-doc');
jest.mock('@/lib/dig/generate');
jest.mock('@/lib/gemini');
jest.mock('@/lib/html-doc/model-store');

const V = DIG_GENERATOR_VERSION;
const SUMMARY_MD = `# T\n\n**Channel:** C | **Duration:** 1:00\n\n## 1. Alpha\n▶ [1:05–2:00](https://youtu.be/x?t=65s)\nprose one.\n`;
function digBlob(sectionId: number): Buffer {
  return Buffer.from(`---\nvideoId: "v"\nsectionId: ${sectionId}\nstartSec: ${sectionId}\ntitle: "Alpha"\nlanguage: en\nsourceVideoUrl: "https://youtu.be/v"\ngeneratedAt: "2026-07-14T00:00:00.000Z"\ngenVersion: ${V}\nslides: []\n---\ndeep dive body [[SLIDE:1:05|2:00|Cap]]\n`, 'utf-8');
}

function fakeBundle(blobs: Record<string, Buffer>) {
  return {
    blobStore: {
      list: jest.fn(async (_p: unknown, prefix: string) => Object.keys(blobs).filter((k) => k.startsWith(prefix))),
      get: jest.fn(async (_p: unknown, key: string) => blobs[key] ?? null),
    },
  };
}

function mockLoadOk(bundle: ReturnType<typeof fakeBundle>) {
  (serveCore.loadSummaryForServe as jest.Mock).mockResolvedValue({
    ok: true, mdBytes: Buffer.from(SUMMARY_MD), mdKey: 'base.md', base: 'base', title: 'T',
    principal: { id: 'o', indexKey: 'k' } as never, playlistId: 'pl', video: { id: 'v', language: 'en' } as never, bundle: bundle as never,
  } as never);
}

describe('loadDigForServe', () => {
  afterEach(() => jest.resetAllMocks());

  it('returns merged inputs and NEVER charges', async () => {
    const bundle = fakeBundle({ [`dig/base/65.r${V}.md`]: digBlob(65) });
    mockLoadOk(bundle);
    (modelStore.readModelEnvelope as jest.Mock).mockResolvedValue(null);
    // Money invariant — mock EVERY charge-capable / generation entry point so the assertion is
    // direct, not an indirect proxy through the fake bundle. resolveMagazineModel is the ONLY
    // charging function (serve-doc.ts:52 rpc('reserve_serve_model')); the rest must also never run.
    // FAIL-CLOSED (.mockRejectedValue): a regression that reached generateDig/generateMagazineModel
    // would run the real generation (live Gemini) before the assertion fires, violating the
    // "No live Gemini in any test" constraint. Rejecting makes any accidental call abort instantly
    // with no real work.
    const resolveMag = (serveDoc.resolveMagazineModel as jest.Mock).mockRejectedValue(new Error('money path reached'));
    const resolveAndParse = (serveCore.resolveAndParse as jest.Mock).mockRejectedValue(new Error('money path reached'));
    const generateDig = (digGen.generateDig as jest.Mock).mockRejectedValue(new Error('generation reached'));
    const generateMag = (gemini.generateMagazineModel as jest.Mock).mockRejectedValue(new Error('generation reached'));
    const rpc = jest.fn();
    const r = await loadDigForServe({ rpc } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.dug).toHaveLength(1);
      expect(r.dug[0].sectionId).toBe(65);
      expect(r.dug[0].bodyMarkdown).toContain('🖼');       // slide→caption applied
      expect(r.dug[0].bodyMarkdown).not.toContain('[[SLIDE');
      expect(r.language).toBe('en');
    }
    expect(rpc).not.toHaveBeenCalled();                     // no RPC (the concrete charge signal)
    expect(resolveMag).not.toHaveBeenCalled();              // the charging fn — never entered
    expect(resolveAndParse).not.toHaveBeenCalled();
    expect(generateDig).not.toHaveBeenCalled();
    expect(generateMag).not.toHaveBeenCalled();
  });

  it('positive control: the money guard actually fires (a real reserve WOULD trip rpc)', async () => {
    // Prove the guard is not vacuous: drive resolveMagazineModel directly with a bundle whose
    // model blob is absent (cache miss) and confirm it reaches rpc('reserve_serve_model'). This is
    // the exact call loadDigForServe must never make — if this control ever stops tripping rpc, the
    // "not.toHaveBeenCalled()" assertions above are meaningless and must be re-derived.
    // Return an UNHANDLED reserve status so resolveMagazineModel's switch hits `default: throw`
    // (serve-doc.ts:73) immediately AFTER the rpc call and BEFORE any generation — guarantees no
    // live Gemini in this control while still proving the reserve RPC was reached.
    const rpc = jest.fn(async () => ({ data: '__unhandled_status__', error: null }));
    const blob = { get: jest.fn(async () => null), put: jest.fn(async () => {}) };
    // Bypass the file-level jest.mock('@/lib/html-doc/serve-doc') to get the REAL implementation —
    // this control exists specifically to prove what the real function does.
    const { resolveMagazineModel: realResolveMagazineModel } =
      jest.requireActual('@/lib/html-doc/serve-doc') as typeof serveDoc;
    await realResolveMagazineModel({
      supabaseClient: { rpc } as never, blobStore: blob as never,
      principal: { id: 'o', indexKey: 'k' } as never, playlistId: 'pl', videoId: 'v', base: 'base',
      parsed: { title: 'T', sections: [] } as never, language: 'en',
    }).catch(() => {}); // the default-throw is expected; we only assert the reserve was attempted
    expect(rpc).toHaveBeenCalledWith('reserve_serve_model', expect.anything());
  });

  it('serves ok with an EMPTY dug set when there are no current-version dig blobs (interactive entry: open to start digging)', async () => {
    // Only a stale-version blob exists → zero CURRENT-version digs. The interactive dig doc must
    // still serve (all sections render an un-dug trigger) rather than 404 — the owner/status gate
    // already passed in loadSummaryForServe. (Superseded the read-only viewer's old zero→404.)
    const bundle = fakeBundle({ [`dig/base/65.r${V - 1}.md`]: digBlob(65) }); // stale version only
    mockLoadOk(bundle);
    (modelStore.readModelEnvelope as jest.Mock).mockResolvedValue(null);
    const r = await loadDigForServe({ rpc: jest.fn() } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r.ok).toBe(true);
    if (r.ok) { expect(r.dug).toEqual([]); expect(r.base).toBe('base'); }
  });

  it('skips a malformed blob but still renders the rest', async () => {
    const bundle = fakeBundle({
      [`dig/base/65.r${V}.md`]: digBlob(65),
      [`dig/base/120.r${V}.md`]: Buffer.from('garbage, no frontmatter'),
    });
    mockLoadOk(bundle);
    (modelStore.readModelEnvelope as jest.Mock).mockResolvedValue(null);
    const r = await loadDigForServe({ rpc: jest.fn() } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.dug.map((d) => d.sectionId)).toEqual([65]);
  });

  it('propagates a loadSummaryForServe failure verbatim', async () => {
    (serveCore.loadSummaryForServe as jest.Mock).mockResolvedValue({ ok: false, status: 404, error: 'not found' } as never);
    const r = await loadDigForServe({ rpc: jest.fn() } as never, { videoId: 'v', playlistId: 'pl', userId: 'u' });
    expect(r).toEqual({ ok: false, status: 404, error: 'not found' });
  });
});
