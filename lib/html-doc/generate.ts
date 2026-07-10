import { assertVideoId } from '../index-store';
import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
import { generateMagazineModel } from '../gemini';
import { parseSummaryMarkdown } from './parse';
import { renderMagazineHtml, GENERATOR_VERSION } from './render';
import { writeModelEnvelope } from './model-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { ProgressEvent } from '../../types';

export async function runHtmlDoc(
  videoId: string,
  outputFolder: string,
  onProgress: (event: ProgressEvent) => void,
  blobStore?: BlobStore,
): Promise<void> {
  const principal = getPrincipal(outputFolder);
  const { metadataStore: store, blobStore: bundleBlob } = getStorageBundle();
  const resolvedBlob = blobStore ?? bundleBlob;
  assertVideoId(videoId);

  const index = await store.readIndex(principal);
  const video = index.videos.find((v) => v.id === videoId);
  if (!video) throw new Error(`Video not found in index: ${videoId}`);
  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');

  onProgress({ type: 'start' });
  onProgress({ type: 'step', videoId, step: 'Reading summary…', current: 1, total: 3 });

  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
  if (!mdBytes) {
    throw new Error(`source note not found on disk: ${video.summaryMd}`);
  }
  const md = mdBytes.toString('utf-8');

  const parsed = parseSummaryMarkdown(md);
  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field

  onProgress({ type: 'step', videoId, step: 'Transforming to skim view…', current: 2, total: 3 });
  const model = await generateMagazineModel(
    parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
    video.language,
  );

  // Persist the model so future style changes can re-render offline (no Gemini). `sourceSections`
  // captures the section titles the model was built against — the re-render drift guard.
  // A later HTML/index failure may leave this model as an orphan; that's intentional and harmless —
  // re-render is gated on summaryHtml (set only on full success), and a retry overwrites it atomically.
  const base = video.summaryMd.replace(/\.md$/, '');
  await writeModelEnvelope(principal, base, {
    sourceMd: video.summaryMd,
    generatedAt: new Date().toISOString(),
    sourceSections: parsed.sections.map((s) => s.title),
    generatorVersion: GENERATOR_VERSION,
    model,
  }, resolvedBlob);

  onProgress({ type: 'step', videoId, step: 'Rendering HTML…', current: 3, total: 3 });
  const html = renderMagazineHtml(parsed, model);

  const htmlFilename = `htmls/${base}.html`;

  // Atomic write via resolvedBlob (LocalFsBlobStore uses temp+rename; cloud impls upload directly).
  // Codex HIGH: if the index update fails, remove the just-written file so we don't leave an
  // orphan HTML the index doesn't reference (keeps cache ↔ index consistent).
  await resolvedBlob.put(principal, htmlFilename, Buffer.from(html, 'utf-8'), 'text/html');
  try {
    await store.updateVideoFields(principal, videoId, { summaryHtml: htmlFilename });
  } catch (err) {
    await resolvedBlob.delete(principal, htmlFilename).catch(() => { /* ignore cleanup error */ });
    throw err;
  }
  onProgress({ type: 'done' });
}
