import path from 'path';
import fs from 'fs';
import { NextResponse } from 'next/server';
import { assertVideoId } from '../../../../../lib/index-store';
import { getPrincipal, getStorageBundle } from '../../../../../lib/storage/resolve';
import { fixSummary, extractQuickView } from '../../../../../lib/gemini';
import { stripQuickViewCallout, insertQuickViewCallout } from '../../../../../lib/pipeline';
import { logError, errorSummary } from '../../../../../lib/dev-logger';
import { mdHash } from '../../../../../lib/cloud-sync/content-hash';

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

    // Save corrections to index before the Gemini call so a subsequent
    // page-refresh shows the latest corrections even if Gemini fails.
    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    if (trimmedCorrections) {
      await store.updateVideoFields(principal, videoId, { corrections: trimmedCorrections });
    } else if (corrections === '') {
      await store.updateVideoFields(principal, videoId, { corrections: undefined });
    }

    // Apply text corrections if provided (works on prose only — callout is stripped first)
    const stripped = stripQuickViewCallout(mdContent);
    const fixed = trimmedCorrections ? await fixSummary(stripped, trimmedCorrections) : stripped;

    // Re-extract tldr/takeaways from corrected content and re-insert callout
    const { tldr, takeaways } = await extractQuickView(fixed);
    const updatedContent = insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? []);

    await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');

    // Stage 3 (§5.1/§5.7, former-Blocking §5.3): stamp this regenerated MD as
    // corrections-current. The corrections THIS MD now reflects mirrors the conditional
    // update above: param non-empty → trimmedCorrections; param === '' → cleared to '';
    // param absent/whitespace-only (neither branch fires) → the UNCHANGED stored value —
    // a bare regenerate keeps prior corrections baked in, so stamping mdHash('') there
    // would wrongly mark a still-corrected MD as stale.
    const effectiveCorrections = trimmedCorrections
      ? trimmedCorrections
      : corrections === '' ? '' : (video.corrections ?? '');

    // Update index with refreshed quick-view data; clear stale HTML cache. NOTE: this write
    // carries MD-currency fields, not a Class-B key, so it must NOT bump annotationsEditedAt
    // (the earlier updateVideoFields({ corrections }) call above is the Class-B write that
    // stamps annotationsEditedAt.corrections).
    await store.updateVideoFields(principal, videoId, {
      tldr, takeaways, summaryHtml: null,
      mdGeneratedAt: new Date().toISOString(),
      mdCorrectionsHash: mdHash(effectiveCorrections),
    });

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
