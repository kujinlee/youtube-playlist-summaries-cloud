import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { digSectionKey } from '@/lib/dig/cloud/dig-blob-key';

export interface DigSectionBlobInput {
  blobStore: BlobStore;
  principal: Principal;
  base: string;
  videoId: string;
  sectionId: number;
  startSec: number;
  title: string;
  language: 'en' | 'ko';
  sourceVideoUrl: string;
  bodyMarkdown: string; // generateDig output after resolveTranscriptTokens; slide tokens PRESERVED
  generatedAt: string;  // ISO-8601
}

/** YAML double-quoted scalar — safe for titles/URLs containing ':' or quotes. */
function yamlScalar(s: string): string {
  return `"${s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

/** Serialize one dug section as a self-describing per-section doc and write it via staged→promote.
 *  `slides: []` and inline unresolved [[SLIDE:...]] tokens — the text-only slice defers slide
 *  resolution losslessly to a later slice. */
export async function writeDigSectionBlob(input: DigSectionBlobInput): Promise<string> {
  const frontmatter = [
    '---',
    `videoId: ${yamlScalar(input.videoId)}`,
    `sectionId: ${input.sectionId}`,
    `startSec: ${input.startSec}`,
    `title: ${yamlScalar(input.title)}`,
    `language: ${input.language}`,
    `sourceVideoUrl: ${yamlScalar(input.sourceVideoUrl)}`,
    `generatedAt: ${yamlScalar(input.generatedAt)}`,
    `genVersion: ${DIG_GENERATOR_VERSION}`,
    'slides: []',
    '---',
    '',
  ].join('\n');
  const doc = `${frontmatter}${input.bodyMarkdown.trimEnd()}\n`;

  const key = digSectionKey(input.base, input.sectionId);
  const ref = await input.blobStore.putStaged(input.principal, key, Buffer.from(doc, 'utf-8'), 'text/markdown');
  if (!(await input.blobStore.exists(input.principal, ref.tempKey))) {
    throw new Error('staged dig upload not verified');
  }
  await input.blobStore.promote(ref);
  return key;
}
