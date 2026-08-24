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

type Params = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  const outputFolder = body?.outputFolder;
  const corrections = body?.corrections;

  if (!outputFolder || typeof outputFolder !== 'string') {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
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
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
  } catch (err) {
    logError(`regenerate:${videoId}`, err);
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  }
}
