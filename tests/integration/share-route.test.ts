import { SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed'; // EXISTING helpers
import { generateShareToken, hashShareToken } from '@/lib/share/token';
import { writeModelEnvelope, MODEL_KEY } from '@/lib/html-doc/model-store';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';

// The route builds its OWN service client internally (createServiceClient()), so the money-proof
// spy below targets the SupabaseClient PROTOTYPE, not an injected instance (B18).
jest.mock('@/lib/gemini', () => {
  const generateMagazineModel = jest.fn(async () => {
    throw new Error('generateMagazineModel must NEVER be called on the anonymous share path');
  });
  return {
    generateMagazineModel,
    // The serve path calls the WRAPPER (#46), so the negative guard has to live behind it too —
    // otherwise this file would "pass" on a TypeError from an undefined export rather than on the
    // assertion it was written to make.
    generateMagazineModelForServe: jest.fn(() => generateMagazineModel()),
  };
});
import { generateMagazineModel } from '@/lib/gemini';

// B10b needs to interject BETWEEN the route's two internal getShareServeContext calls (the initial
// resolve and the mandatory pre-response re-check). `jest.spyOn(moduleNamespace, 'fn')` fails here
// with "Cannot redefine property" — this repo's Next.js/SWC jest transform emits non-configurable
// getter-backed exports for live-binding fidelity, so property-redefinition-based spies don't work
// on module namespaces (this is a runtime constraint of the toolchain, not a design choice).
// `jest.mock` swaps the whole module object instead of redefining a property, so it works regardless.
// (Names below are prefixed `mock` per babel-plugin-jest-hoist's static-analysis whitelist — the
// jest.mock factory is hoisted above these declarations, so only `mock*`-prefixed out-of-scope
// bindings are permitted, and only nested closures invoked later actually read them.)
let mockGlobalCallCount = 0;
let mockArmedAtCount = 0;
let mockOnSecondCallSinceArm: ((token: string) => Promise<void>) | null = null;

jest.mock('@/lib/share/serve', () => {
  const actual = jest.requireActual('@/lib/share/serve');
  return {
    __esModule: true,
    ...actual,
    getShareServeContext: jest.fn(async (client: unknown, tok: string) => {
      mockGlobalCallCount += 1;
      const sinceArm = mockGlobalCallCount - mockArmedAtCount;
      if (sinceArm === 2 && mockOnSecondCallSinceArm) await mockOnSecondCallSinceArm(tok);
      return actual.getShareServeContext(client, tok);
    }),
  };
});

import { GET } from '@/app/s/[token]/route';

const svc = adminClient();
const MD = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;
const CORRUPT_MD = 'not a valid markdown doc at all — no ## headings, so the parser throws.';

async function seedDoc(ownerId: string, status: 'promoted' | 'committed' = 'promoted', title?: string) {
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId, base } = await seedPromotedVideo(svc, { ownerId, playlistId, status, title });
  return { playlistId, playlistKey, videoId, base };
}

async function mintDirect(
  ownerId: string, playlistId: string, videoId: string, over: Record<string, unknown> = {},
): Promise<string> {
  const { token, tokenHash } = generateShareToken(); // token: 43-char base64url (returned to caller); tokenHash: 64-char hex (stored in TEXT column)
  const { error } = await svc.from('share_tokens').insert({
    token_hash: tokenHash, owner_id: ownerId, playlist_id: playlistId, video_id: videoId,
    expires_at: new Date(Date.now() + 864e5).toISOString(), ...over,
  });
  if (error) throw error;
  return token;
}

/** Seed a fresh model envelope via writeModelEnvelope through a full service-role SupabaseBlobStore
 *  (Task 1/6 leaf reused read-side; write-side still needs the full store). */
async function seedFreshModel(ownerId: string, playlistKey: string, base: string): Promise<void> {
  const serviceStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
  const principal = { id: ownerId, indexKey: playlistKey };
  await writeModelEnvelope(
    principal,
    base,
    {
      sourceMd: `${base}.md`,
      generatedAt: new Date().toISOString(),
      sourceSections: ['Intro'],
      generatorVersion: GENERATOR_VERSION,
      model: {
        sections: [
          { lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] },
        ],
      },
    },
    serviceStore,
  );
}

function invoke(token: string) {
  return { params: Promise.resolve({ token }) };
}

describe('share-route', () => {
  let rpcSpy: jest.SpyInstance;
  let ledgerBefore: unknown[];
  let chargeBefore: unknown[];
  let ownerBudgetBefore: unknown[];

  beforeAll(async () => {
    // .order() keeps the byte-compare snapshot below order-deterministic (Codex/Claude cosmetic fix)
    // — without it, two `select('*')` calls over the same rows are not guaranteed to come back in
    // the same order, which could make the afterAll toEqual flaky/false-negative.
    const { data: ledger } = await svc.from('spend_ledger').select('*').order('day');
    const { data: charge } = await svc.from('serve_model_charge').select('*').order('owner_id').order('doc_key').order('day');
    const { data: ownerBudget } = await svc.from('serve_owner_budget').select('*').order('owner_id').order('day');
    ledgerBefore = ledger ?? [];
    chargeBefore = charge ?? [];
    ownerBudgetBefore = ownerBudget ?? [];
    // Spy on the PROTOTYPE — the route constructs its own service client per request, so an
    // injected-instance spy would never see the calls the route itself makes.
    rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc');
  });

  afterEach(() => {
    // Money invariant, asserted after EVERY case in this file: reserve_serve_model is never called
    // on the share path, regardless of which branch (200/404/503) the request took.
    for (const call of rpcSpy.mock.calls) {
      expect(call[0]).not.toBe('reserve_serve_model');
    }
  });

  afterAll(async () => {
    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
    const { data: chargeAfter } = await svc.from('serve_model_charge').select('*').order('owner_id').order('doc_key').order('day');
    const { data: ownerBudgetAfter } = await svc.from('serve_owner_budget').select('*').order('owner_id').order('day');
    expect(ledgerAfter ?? []).toEqual(ledgerBefore); // byte-identical row sets — no charge ever landed
    expect(chargeAfter ?? []).toEqual(chargeBefore);
    // Stage 1G / G1 Task 2 (P11): the per-owner serve budget is only ever touched by
    // reserve_serve_model (5a) — since that RPC is never called on the share path (asserted in
    // afterEach below), no share owner should have gained/changed a serve_owner_budget row either.
    expect(ownerBudgetAfter ?? []).toEqual(ownerBudgetBefore);
    expect(generateMagazineModel).not.toHaveBeenCalled(); // zero generation calls across the whole block
    rpcSpy.mockRestore();
  });

  it('B6: valid token + fresh model → 200 html; headers; body has summary, not the MD key', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    await seedFreshModel(u.user.id, playlistKey, base);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toMatch(/text\/html/);
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    expect(res.headers.get('Referrer-Policy')).toBe('no-referrer');
    expect(res.headers.get('Content-Security-Policy')).toMatch(/nonce-/);
    const html = await res.text();
    expect(html).toContain('Intro');
    expect(html).not.toContain(`${base}.md`); // B22 — no owner-structure leak on the share doc
  });

  it('B7: valid token, model absent (never generated) → 503 not-ready', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    // Deliberately no writeModelEnvelope call — model absent.
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(503);
  });

  // ── B8 REVERSED BY PRODUCT DECISION 2026-08-11 (M1.4 item B4): TOLERATE version skew.
  // This case asserted 503 from Stage 1F-b until that decision. The spec row said "not ready;
  // heals after owner next views" — but the heal is OWNER-dependent, so a share link to a doc
  // its owner never revisits stayed broken after every GENERATOR_VERSION bump, and skew is the
  // normal state during a rolling deploy. The structural guarantee does NOT come from
  // GENERATOR_VERSION: readModelEnvelope safeParses every envelope against the CURRENT
  // ModelEnvelopeSchema and returns null on mismatch (model-store.ts), and MagazineModelSchema
  // is .strict() — so a model whose SHAPE changed still fails closed (B8c below). What
  // tolerating admits is only the PROMPT-change half of GENERATOR_VERSION: same structure,
  // older prose. Titles still gate positional coherence (B8b below).
  it('B8: valid token, model is version-SKEWED but title-stable → 200 rendered (tolerate; still never a charge)', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    const serviceStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
    const principal = { id: u.user.id, indexKey: playlistKey };
    await writeModelEnvelope(
      principal,
      base,
      {
        sourceMd: `${base}.md`,
        generatedAt: new Date().toISOString(),
        sourceSections: ['Intro'],          // titles MATCH the MD — positionally coherent
        generatorVersion: 'stale-vX',       // deliberately mismatched — must NOT equal GENERATOR_VERSION
        model: {
          sections: [
            { lead: 'LEAD-FROM-SKEWED-MODEL', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] },
          ],
        },
      },
      serviceStore,
    );
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(200);
    // Assert the SKEWED model is what got rendered — a 200 alone would also pass if the route
    // had somehow regenerated, which is the one thing this path must never do.
    expect(await res.text()).toContain('LEAD-FROM-SKEWED-MODEL');
  });

  it('B8b: version-skewed AND titles drifted → 503 (positional mis-pair must still fail closed)', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    const serviceStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
    const principal = { id: u.user.id, indexKey: playlistKey };
    await writeModelEnvelope(
      principal,
      base,
      {
        sourceMd: `${base}.md`,
        generatedAt: new Date().toISOString(),
        sourceSections: ['A DIFFERENT SECTION'], // drifted — the model no longer pairs with the MD
        generatorVersion: 'stale-vX',
        model: {
          sections: [
            { lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] },
          ],
        },
      },
      serviceStore,
    );
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(503);
  });

  it('B8c: envelope whose MODEL SHAPE is invalid under the current schema → 503 (zod is the structural gate, not the version string)', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    const serviceStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
    const principal = { id: u.user.id, indexKey: playlistKey };
    // Written as RAW BYTES on purpose: writeModelEnvelope validates before writing, so an
    // invalid envelope cannot be produced through it. This is the shape-change case that
    // tolerating version skew must NOT admit — `bullets: []` violates MagazineSectionSchema's
    // min(3), exactly as a real model-shape change would.
    await serviceStore.put(
      principal,
      MODEL_KEY(base),
      Buffer.from(JSON.stringify({
        sourceMd: `${base}.md`,
        generatedAt: new Date().toISOString(),
        sourceSections: ['Intro'],
        generatorVersion: 'stale-vX',
        model: { sections: [{ lead: 'L', bullets: [] }] },
      }), 'utf-8'),
      'application/json',
    );
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(503);
  });

  it('B8d: envelope covers FEWER sections than the markdown → 503 (never a 200 with a blank section)', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    // Two sections in the MD, but the model will carry only one.
    const TWO_SECTION_MD = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n\n## 2. Second\nmore\n`;
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, TWO_SECTION_MD);
    const serviceStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
    const principal = { id: u.user.id, indexKey: playlistKey };
    // `sourceSections` MATCHES the parsed titles, so sameTitles() accepts — the mismatch is between
    // sourceSections and model.sections, which no schema relates. renderMagazineHtml pairs by index
    // and returns '' for a missing model section (render.ts:84), so without the coverage check in
    // readTitleStableModel this served a 200 with section 2 silently blank.
    await writeModelEnvelope(
      principal,
      base,
      {
        sourceMd: `${base}.md`,
        generatedAt: new Date().toISOString(),
        sourceSections: ['Intro', 'Second'],
        generatorVersion: GENERATOR_VERSION, // fresh — so this is NOT about version skew
        model: {
          sections: [
            { lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] },
          ],
        },
      },
      serviceStore,
    );
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(503);
  });

  it('B9: expired token → 404 (coarse)', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId, {
      expires_at: new Date(Date.now() - 864e5).toISOString(),
    });

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
  });

  it('B10: revoked token → 404 (coarse)', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId, {
      revoked_at: new Date().toISOString(),
    });

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
  });

  it('B12: unknown token (never minted) → 404 (coarse)', async () => {
    const token = generateShareToken().token;

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
  });

  it('B12: token pointing at an un-promoted (committed) doc → 404', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id, 'committed');
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
  });

  it('B11: malformed token shape → 404 before any DB call', async () => {
    const fromSpy = jest.spyOn(SupabaseClient.prototype, 'from');
    const before = fromSpy.mock.calls.length;

    const res = await GET(new Request('http://localhost/s/short'), invoke('short'));
    expect(res.status).toBe(404);
    expect(fromSpy.mock.calls.length).toBe(before); // no DB table access happened at all
    fromSpy.mockRestore();
  });

  it('B13b: MD blob missing behind a promoted status → 404 (never 500)', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);
    // Deliberately no seedSummaryBlob call — the MD blob is missing.
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
  });

  it('B13b: corrupt MD (parse throws) → 404 (never 500)', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, CORRUPT_MD);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
  });

  it('B10b: revoke lands between the initial resolve and the mandatory pre-response re-check → 404', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    await seedFreshModel(u.user.id, playlistKey, base);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    // Arm relative to the CURRENT global call count so prior tests' calls don't shift the target —
    // "2 calls since arming" is always this request's own [initial resolve, pre-response re-check].
    mockArmedAtCount = mockGlobalCallCount;
    let hookFired = false;
    mockOnSecondCallSinceArm = async (tok) => {
      hookFired = true;
      // Land the revoke strictly between the route's first resolve and its mandatory
      // pre-response re-check (D14/B10b), before the re-check itself observes the row.
      await svc.from('share_tokens').update({ revoked_at: new Date().toISOString() }).eq('token_hash', hashShareToken(tok));
    };

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
    expect(hookFired).toBe(true); // proves the mandatory second (pre-response) re-check ran and caught it
    mockOnSecondCallSinceArm = null;
  });

  it('B10b: video un-promoted (artifacts.summaryMd.status flipped away from promoted) between the initial resolve and the mandatory pre-response re-check → 404', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    await seedFreshModel(u.user.id, playlistKey, base);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    mockArmedAtCount = mockGlobalCallCount;
    let hookFired = false;
    mockOnSecondCallSinceArm = async () => {
      hookFired = true;
      // Instead of revoking the token, flip the video's promotion status away from 'promoted'
      // strictly between the route's first resolve and its mandatory pre-response re-check
      // (D14/B10b) — the re-check reads `videos.data.artifacts.summaryMd.status` fresh, so this
      // must ALSO be caught even though the token row itself never changes.
      const { data: vid, error: vidErr } = await svc
        .from('videos').select('data')
        .eq('playlist_id', playlistId).eq('video_id', videoId).eq('owner_id', u.user.id).single();
      if (vidErr) throw vidErr;
      const nextData = {
        ...(vid!.data as Record<string, unknown>),
        artifacts: { summaryMd: { key: `${base}.md`, status: 'committed' } },
      };
      const { error: updErr } = await svc
        .from('videos').update({ data: nextData })
        .eq('playlist_id', playlistId).eq('video_id', videoId).eq('owner_id', u.user.id);
      if (updErr) throw updErr;
    };

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(404);
    expect(hookFired).toBe(true); // proves the mandatory second (pre-response) re-check ran and caught the un-promote
    mockOnSecondCallSinceArm = null;
  });

  // ---- 1F-c: format/download + MD branch (with re-check) + money proof ----------------------

  it('C7: share GET (no format/download), live token → 200 html view regression w/ nosniff, no Content-Disposition', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    await seedFreshModel(u.user.id, playlistKey, base);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}`), invoke(token));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toMatch(/text\/html/);
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    expect(res.headers.get('Referrer-Policy')).toBe('no-referrer');
    expect(res.headers.get('X-Content-Type-Options')).toBe('nosniff'); // NEW
    expect(res.headers.get('Content-Disposition')).toBeNull();
  });

  it('C8: format=md&download=1, live token → 200 text/markdown attachment filename+filename*; never charges', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id, 'promoted', 'My Doc Title');
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}?format=md&download=1`), invoke(token));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toMatch(/text\/markdown/);
    expect(res.headers.get('X-Content-Type-Options')).toBe('nosniff');
    expect(res.headers.get('Content-Disposition')).toBe(
      `attachment; filename="${base}.md"; filename*=UTF-8''My%20Doc%20Title.md`,
    );
    expect(generateMagazineModel).not.toHaveBeenCalled(); // D4 — md path never generates/charges
  });

  it('C8b: format=md (no download), live token → 200 text/plain; charset=utf-8, nosniff', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}?format=md`), invoke(token));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('text/plain; charset=utf-8');
    expect(res.headers.get('X-Content-Type-Options')).toBe('nosniff');
    expect(res.headers.get('Content-Disposition')).toBeNull();
  });

  it('C9: format=html&download=1, live token, fresh model → 200 html attachment; share-mode strip; never charges', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id, 'promoted', 'My Doc Title');
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    await seedFreshModel(u.user.id, playlistKey, base);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}?format=html&download=1`), invoke(token));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toMatch(/text\/html/);
    expect(res.headers.get('X-Content-Type-Options')).toBe('nosniff');
    expect(res.headers.get('Content-Disposition')).toBe(
      `attachment; filename="${base}.html"; filename*=UTF-8''My%20Doc%20Title.html`,
    );
    const html = await res.text();
    expect(html).toContain('Intro');
    expect(html).not.toContain(`${base}.md`); // share-mode strip — no owner-structure/MD-key leak
    expect(generateMagazineModel).not.toHaveBeenCalled(); // share html path never generates — freshness only
  });

  it('C5s: format=pdf → 400 for a valid token AND for a malformed token (format validated before TOKEN_RE — no oracle)', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res1 = await GET(new Request(`http://localhost/s/${token}?format=pdf`), invoke(token));
    expect(res1.status).toBe(400);

    const fromSpy = jest.spyOn(SupabaseClient.prototype, 'from');
    const before = fromSpy.mock.calls.length;
    const res2 = await GET(new Request('http://localhost/s/short?format=pdf'), invoke('short'));
    expect(res2.status).toBe(400);
    expect(fromSpy.mock.calls.length).toBe(before); // no DB call — format checked before token shape
    fromSpy.mockRestore();
  });

  it('C5b: duplicate format params (e.g. format=html&format=pdf) → 400, not the first value', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res1 = await GET(new Request(`http://localhost/s/${token}?format=html&format=pdf`), invoke(token));
    expect(res1.status).toBe(400);
    const res2 = await GET(new Request(`http://localhost/s/${token}?format=md&format=pdf`), invoke(token));
    expect(res2.status).toBe(400);
  });

  it('C11: expired/revoked/unknown token, format=md → coarse 404 before blob read', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);

    const expiredToken = await mintDirect(u.user.id, playlistId, videoId, {
      expires_at: new Date(Date.now() - 864e5).toISOString(),
    });
    let res = await GET(new Request(`http://localhost/s/${expiredToken}?format=md`), invoke(expiredToken));
    expect(res.status).toBe(404);

    const revokedToken = await mintDirect(u.user.id, playlistId, videoId, {
      revoked_at: new Date().toISOString(),
    });
    res = await GET(new Request(`http://localhost/s/${revokedToken}?format=md`), invoke(revokedToken));
    expect(res.status).toBe(404);

    const unknownToken = generateShareToken().token;
    res = await GET(new Request(`http://localhost/s/${unknownToken}?format=md`), invoke(unknownToken));
    expect(res.status).toBe(404);
  });

  it('C11b: revoke lands between the initial resolve and the MD branch re-check → 404 (D12)', async () => {
    const u = await newUser();
    const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    // Same "2 calls since arm" hook as B10b above — for the md branch this is exactly
    // [initial resolve, md-branch re-check] since the md path never reaches the html branch's
    // separate re-check.
    mockArmedAtCount = mockGlobalCallCount;
    let hookFired = false;
    mockOnSecondCallSinceArm = async (tok) => {
      hookFired = true;
      await svc.from('share_tokens').update({ revoked_at: new Date().toISOString() }).eq('token_hash', hashShareToken(tok));
    };

    const res = await GET(new Request(`http://localhost/s/${token}?format=md`), invoke(token));
    expect(res.status).toBe(404);
    expect(hookFired).toBe(true); // proves the md branch's own re-check ran and caught the revoke
    mockOnSecondCallSinceArm = null;
  });

  it('C12: format=md, MD blob missing behind a promoted status → 404 (never 500)', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);
    // Deliberately no seedSummaryBlob call — the MD blob is missing.
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}?format=md`), invoke(token));
    expect(res.status).toBe(404);
  });

  it('C16: cross-owner isolation — a share_token row claiming owner B for A\'s playlist is now DB-rejected (0019 composite FK); D15 stays as defense-in-depth', async () => {
    // Pre-0019 this confused-deputy row (token owner_id=B, coords resolve to A's doc) was
    // directly insertable and caught only by the app-level D15 guard (lib/share/serve.ts) at
    // request time. 0019's composite FK share_tokens(playlist_id, owner_id) ->
    // playlists(id, owner_id) now makes such a row structurally impossible to insert — the DB
    // rejects it at the source, before any request can ever be served against it. D15 remains
    // in place as defense-in-depth for any other path that might construct an inconsistent row.
    const a = await newUser();
    const b = await newUser();
    const { playlistId, videoId } = await seedDoc(a.user.id); // A's promoted doc

    // mintDirect throws the raw PostgrestError object (not an Error instance), which
    // `.rejects.toThrow()` cannot reliably match — assert on the rejection directly instead.
    let caught: unknown;
    try {
      await mintDirect(b.user.id, playlistId, videoId); // B "owns" the token row, A owns the coords
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeDefined();
    expect((caught as { code?: string }).code).toBe('23503'); // foreign_key_violation
  });

  it('C21: hostile title (quote/CRLF) in a share doc → header not injected on md download', async () => {
    const u = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, u.user.id);
    const videoId = 'v-hostile21';
    const base = videoId;
    const hostileTitle = 'a"\r\nb;c';
    const { error } = await svc.from('videos').insert({
      playlist_id: playlistId, owner_id: u.user.id, video_id: videoId, position: 1,
      data: {
        id: videoId, title: hostileTitle, language: 'en', summaryMd: `${base}.md`, docVersion: 1,
        artifacts: { summaryMd: { key: `${base}.md`, status: 'promoted' } },
      },
    });
    if (error) throw error;
    await seedSummaryBlob(svc, u.user.id, playlistKey, base, MD);
    const token = await mintDirect(u.user.id, playlistId, videoId);

    const res = await GET(new Request(`http://localhost/s/${token}?format=md&download=1`), invoke(token));
    expect(res.status).toBe(200);
    const cd = res.headers.get('Content-Disposition')!;
    expect(cd).not.toMatch(/[\r\n]/);
    expect(cd).toContain(`filename="${base}.md"`); // ascii half is the base key, never the raw title
    expect(cd).toContain('%0D%0A'); // CR/LF percent-encoded in filename*, never literal
    expect(res.headers.get('X-Content-Type-Options')).toBe('nosniff');
  });
});
