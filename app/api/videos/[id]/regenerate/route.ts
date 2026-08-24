import path from 'path';
import fs from 'fs';
import { NextResponse } from 'next/server';
import { assertVideoId } from '../../../../../lib/index-store';
import { getPrincipal, getStorageBundle } from '../../../../../lib/storage/resolve';
import { fixSummary, extractQuickView } from '../../../../../lib/gemini';
import { stripQuickViewCallout, insertQuickViewCallout } from '../../../../../lib/pipeline';
import { logError, errorSummary } from '../../../../../lib/dev-logger';
import { mdHash } from '../../../../../lib/cloud-sync/content-hash';
import type { Video } from '../../../../../types';
import { MAX_CORRECTIONS_CHARS } from '../../../../../lib/corrections/apply-core';
import { NonRetryableError } from '../../../../../lib/job-queue/errors';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '../../../../../lib/supabase/server';
import { loadSummaryForServe } from '../../../../../lib/html-doc/serve-summary-core';
import { applyCorrection, CORRECTION_CAPS } from '../../../../../lib/corrections/apply-core';

/** Bounds THE WORK, not THE REQUEST. Derived in spec §5.4 from three phases — a 10 s countTokens
 *  preflight plus two Gemini phases of 3 × 60 s + 1.2 s backoff each = 372.4 s — leaving ~48 s for
 *  the blob read, the blob write and the metadata RPC.
 *
 *  ⚠ NOTHING ON THIS DEPLOYMENT ENFORCES IT. Next's own docs call maxDuration an output annotation
 *  ("Deployment platforms CAN use maxDuration from the Next.js build output"), and this app ships
 *  `output: 'standalone'` (next.config.ts:11) running `node server.js` under Fly, where no adapter
 *  consumes it. Kept because it is correct-by-portability and free. */
export const maxDuration = 420;

type Params = { params: Promise<{ id: string }> };

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId);
}

async function serveLocal(request: Request, videoId: string): Promise<Response> {

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  const outputFolder = body?.outputFolder;
  const corrections = body?.corrections;

  if (!outputFolder || typeof outputFolder !== 'string') {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
  }

  // Corrections are the ONLY unbounded input to a paid call on this route. The 1,000 limit lives in
  // the browser (CorrectionsPanel.tsx:105) and §5.3 concedes any authenticated client can reach this
  // handler, so enforce it where it binds. Code points, not UTF-16 units — see MAX_CORRECTIONS_CHARS.
  if (typeof corrections === 'string' && [...corrections].length > MAX_CORRECTIONS_CHARS) {
    return NextResponse.json(
      { error: `corrections must be ${MAX_CORRECTIONS_CHARS} characters or fewer`, code: 'corrections-too-long' },
      { status: 400 },
    );
  }

  let principal;
  try {
    principal = getPrincipal(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  const { metadataStore: store } = getStorageBundle();
  const index = await store.readIndex(principal);
  const video = index.videos.find((v) => v.id === videoId);

  if (!video) {
    return NextResponse.json({ error: 'video not found' }, { status: 404 });
  }

  if (!video.summaryMd) {
    return NextResponse.json({ error: 'no summary file for this video' }, { status: 422 });
  }

  try {
    const mdPath = path.join(outputFolder, video.summaryMd);
    let mdContent = await fs.promises.readFile(mdPath, 'utf-8');

    // Save corrections BEFORE the Gemini call so a page refresh shows the latest text even if
    // Gemini fails.
    //
    // updateVideoAnnotations, not updateVideoFields (spec §4.1). Two reasons:
    //  - `updateVideoFields(p, id, { corrections: undefined })` is a NO-OP on Supabase — `undefined`
    //    is dropped by JSON serialization before merge_video_data ever sees it, after which the
    //    route stamped mdHash('') over a row that still held corrections.
    //  - the RPC enforces the allowlist and `owner_id = auth.uid()` in SQL, and returns { found }.
    //
    // READ BEFORE WRITE, and issue NO CALL when nothing changed. Both backends stamp
    // annotationsEditedAt for every Class-B key set OR cleared (0021:33-43;
    // local-metadata-store.ts:139-159), so "only when it changed" cannot live in the store. A no-op
    // press must not beat a real remote edit in Class-B reconciliation — including the
    // clear-an-already-empty case, which would otherwise stamp an edit that did not happen.
    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    const storedCorrections = video.corrections ?? '';
    if (trimmedCorrections && trimmedCorrections !== storedCorrections) {
      const { found } = await store.updateVideoAnnotations(
        principal, videoId, { corrections: trimmedCorrections }, [],
      );
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    } else if (corrections === '' && storedCorrections !== '') {
      const { found } = await store.updateVideoAnnotations(principal, videoId, {}, ['corrections']);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    }

    // Apply text corrections if provided (works on prose only — callout is stripped first)
    const stripped = stripQuickViewCallout(mdContent);
    const fixed = trimmedCorrections
      ? (await fixSummary(stripped, trimmedCorrections, { signal: request.signal })).text
      : stripped;

    // Re-extract tldr/takeaways from corrected content and re-insert callout
    const { tldr, takeaways } = await extractQuickView(fixed);
    const updatedContent = insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? []);

    // WRITE ONLY WHEN A CORRECTION WAS APPLIED (spec §2, round-5 Blocking). On a bare press
    // `fixed === stripped`, so the prose is unchanged — but `extractQuickView` above is a
    // non-deterministic LLM call and `insertQuickViewCallout` splices its output into the hashed
    // region, so writing would move `mdHash(body)`. Under §2's option (e) that invalidates the
    // magazine model and books a ~6¢ regeneration for a press that applied nothing. Measured: the
    // callout sits in the preamble `parseSections` discards (parse.ts:45-47), so it can change no
    // input the model is built from — the regeneration would recompute an identical result.
    if (trimmedCorrections) {
      await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');
    }

    // Stage 3 (§5.1/§5.7) + spec §4.3. Stamp corrections-currency ONLY when fixSummary actually ran,
    // and stamp it against the REQUEST's corrections — the quantity that was applied.
    //
    // The old rule (`:77-79`) fell back to the STORED value on a bare press, which flipped a
    // corrections-stale row to current with no Gemini call. `mdCorrectionsHash` is the sole input to
    // reconcileClassA's currency predicate (reconcile-class-a.ts:8), and sync-run.ts:358 writes
    // `corrections` without touching the body, so one bare press permanently discarded a pending
    // correction. Omitting the field preserves whatever the row already claimed.
    //
    // An explicit clear still stamps mdHash('') — unchanged, imperfect (the body may still carry
    // previously applied corrections) and out of scope for slice A.
    //
    // NOTE: this write carries MD-currency fields, not a Class-B key, so it must NOT bump
    // annotationsEditedAt (the earlier updateVideoFields({ corrections }) call above is the
    // Class-B write that stamps annotationsEditedAt.corrections).
    const patch: Partial<Video> = { tldr, takeaways, summaryHtml: null };
    if (trimmedCorrections) {
      patch.mdGeneratedAt = new Date().toISOString();   // the body DID change
      patch.mdCorrectionsHash = mdHash(trimmedCorrections);
    } else if (corrections === '') {
      patch.mdCorrectionsHash = mdHash('');
    }

    await store.updateVideoFields(principal, videoId, patch);

    return NextResponse.json({
      outcome: trimmedCorrections ? 'applied' : 'no-corrections',
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
  } catch (err) {
    logError(`regenerate:${videoId}`, err);
    // The preflight refusal is a CLIENT-side fact about this document, not a server fault: the
    // summary is larger than the correction cap can accept and no retry will change that. A 500
    // would tell the user to try again forever. Matched on the NonRetryableError class AND the
    // message prefix that assertCorrectionInputWithinCap emits, so an unrelated NonRetryableError
    // from elsewhere in the graph still reports 500.
    if (err instanceof NonRetryableError && err.message.startsWith('correction input ')) {
      return NextResponse.json(
        { error: 'This summary is too long to correct', code: 'summary-too-large' },
        { status: 413 },
      );
    }
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  }
}

async function serveCloud(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) {
    return NextResponse.json({ error: 'invalid playlist' }, { status: 400 }); // before any DB call
  }

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  if (body && 'outputFolder' in body) {
    return NextResponse.json({ error: 'outputFolder not valid on this backend' }, { status: 400 });
  }
  const corrections = body?.corrections;
  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
  }
  if (typeof corrections === 'string' && [...corrections].length > MAX_CORRECTIONS_CHARS) {
    return NextResponse.json(
      { error: `corrections must be ${MAX_CORRECTIONS_CHARS} characters or fewer`, code: 'corrections-too-long' },
      { status: 400 },
    );
  }

  // EVERYTHING BELOW IS INSIDE THE TRY. On the local branch `getStorageBundle()` sits OUTSIDE it,
  // so a missing client 500s instead of returning an error.
  try {
    // ⚠ CALL THE EXISTING LOADER — DO NOT HAND-ROLL THIS. An earlier draft transcribed the auth
    // skeleton from `review/route.ts:106-152` and reproduced only the owner check and the blob
    // read. `review/route.ts` writes annotations and never touches a blob, so it carries none of
    // the guards a blob read needs. `loadSummaryForServe` (serve-summary-core.ts:34) is the read
    // path, and it does ALL of this in one call:
    //
    //   resolveOwnedPlaylistKey → 404      getPrincipalFromSession + getStorageBundle
    //   readIndex + video lookup → 404     artifacts.summaryMd.status === 'committed' → 503
    //   status !== 'promoted' → 404        key = artifact.key ?? video.summaryMd, else 404
    //   assertCloudSummaryMdKey → 409      blobStore.get → null → 409 'repair needed'
    //
    // The status gate is the one a hand-rolled version drops, and it matters MORE here than on the
    // serve path: correcting a `committed` artifact writes to a blob a worker promotion is still
    // finalizing. The `!mdBytes` → 409 guard is also its (blobStore.get collapses RLS denials and
    // transport faults into the same null as a genuine 404, blob-store.ts:57-66 — treating null as
    // "no content" would hand Gemini an empty string and overwrite a real document).
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return NextResponse.json({ error: load.error }, { status: load.status });

    const { principal, bundle, video, mdKey, mdBytes } = load;
    const { metadataStore: store, blobStore } = bundle;
    const mdContent = mdBytes.toString('utf-8');

    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    const storedCorrections = video.corrections ?? '';
    if (trimmedCorrections && trimmedCorrections !== storedCorrections) {
      const { found } = await store.updateVideoAnnotations(principal, videoId, { corrections: trimmedCorrections }, []);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    } else if (corrections === '' && storedCorrections !== '') {
      const { found } = await store.updateVideoAnnotations(principal, videoId, {}, ['corrections']);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    }

    let tldr: string;
    let takeaways: string[];

    if (trimmedCorrections) {
      const applied = await applyCorrection({
        md: mdContent,
        corrections: trimmedCorrections,
        tags: video.tags ?? [],
        signal: request.signal,
        caps: CORRECTION_CAPS,
      });
      tldr = applied.tldr;
      takeaways = applied.takeaways;
      // `put`, NEVER writeArtifact. writeArtifact goes putStaged → promote, and promote is
      // create-if-absent (supabase-blob-store.ts:120-123): the key never changes on a correction, so
      // the final object always exists and the corrected body would be silently discarded while the
      // row was stamped `promoted`. That is backlog #22, and it applies to slice A too.
      // `mdKey` from loadSummaryForServe, NOT `video.summaryMd`: the loader prefers
      // `artifacts.summaryMd.key` and falls back to the top-level field, so writing to
      // `video.summaryMd` could target a blob the artifact record does not govern.
      await blobStore.put(principal, mdKey, Buffer.from(applied.content, 'utf-8'), 'text/markdown');

      // Record ACTUAL spend, after the call returned (spec §5.2). Post-hoc, not pre-authorised:
      // the guardrails see this on the NEXT decision, which is the accepted trade.
      //
      // ⚠ A FAILED RECORDING MUST NOT FAIL THE REQUEST. The money is already spent and the corrected
      // body is already durable in storage; a 500 here would report failure for work that landed and
      // invite the user to press again — paying twice to fix a bookkeeping error. That includes
      // hitting the per-owner daily bound: the correction still happened and the user still gets it.
      // Log loudly instead. Same rule as the envelope-invalidation failure the spec settled in §2.
      if (applied.actualCents != null) {
        const { error: spendError } = await supabase.rpc('record_correction_spend', {
          p_cents: applied.actualCents,
        });
        if (spendError) {
          console.error(
            `[correction-spend] FAILED to record owner=${principal.id} video=${videoId} `
            + `cents=${applied.actualCents}: ${spendError.message}`,
          );
        }
      } else {
        // null is "the SDK reported no usage", NOT "free" (Task 5). Recording 0 would be a lie the
        // ledger cannot distinguish from a genuinely free call.
        console.warn(`[correction-spend] UNMEASURED owner=${principal.id} video=${videoId}`);
      }
    } else {
      // Bare press or explicit clear: quick-view still refreshes (spec §3), but NOTHING is written to
      // the blob — the prose did not change and a rewritten callout would move the body hash, which
      // under §2 option (e) books a ~6¢ magazine regeneration for a press that applied nothing.
      const qv = await extractQuickView(stripQuickViewCallout(mdContent), CORRECTION_CAPS);
      tldr = qv.tldr;
      takeaways = qv.takeaways;
    }

    const patch: Partial<Video> = { tldr, takeaways, summaryHtml: null };
    if (trimmedCorrections) {
      patch.mdGeneratedAt = new Date().toISOString();
      patch.mdCorrectionsHash = mdHash(trimmedCorrections);
    } else if (corrections === '') {
      patch.mdCorrectionsHash = mdHash('');
    }
    await store.updateVideoFields(principal, videoId, patch);

    return NextResponse.json({
      outcome: trimmedCorrections ? 'applied' : 'no-corrections',
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
  } catch (err) {
    logError(`regenerate:cloud:${videoId}`, err);
    if (err instanceof NonRetryableError && err.message.startsWith('correction input ')) {
      return NextResponse.json(
        { error: 'This summary is too long to correct', code: 'summary-too-large' },
        { status: 413 },
      );
    }
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  }
}
