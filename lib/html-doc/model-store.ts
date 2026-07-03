import { z } from 'zod';
import { MagazineModelSchema } from './types';
import { localPrincipal } from '@/lib/storage/principal';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import type { BlobStore } from '@/lib/storage/blob-store';

/**
 * The persisted summary-model file: the Gemini transform output plus provenance.
 * `sourceSections` is the section titles the model was built against — the drift guard the
 * re-render path compares the current .md's section titles against.
 */
export const ModelEnvelopeSchema = z
  .object({
    sourceMd: z.string().min(1),
    generatedAt: z.string().min(1),
    sourceSections: z.array(z.string()),
    model: MagazineModelSchema,
  })
  .strict();

export type ModelEnvelope = z.infer<typeof ModelEnvelopeSchema>;

const MODEL_KEY = (base: string) => `models/${base}.json`;

/**
 * Atomically write the envelope to models/<base>.json via blobStore. Validated on write:
 * an invalid model throws here rather than producing a file the reader would reject.
 */
export async function writeModelEnvelope(
  outputFolder: string,
  base: string,
  envelope: ModelEnvelope,
  blobStore: BlobStore = localBlobStore,
): Promise<void> {
  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
  const bytes = Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
  await blobStore.put(localPrincipal(outputFolder), MODEL_KEY(base), bytes, 'application/json');
}

/** Read + validate the envelope. Returns null if absent, unparseable, or schema-invalid. */
export async function readModelEnvelope(
  outputFolder: string,
  base: string,
  blobStore: BlobStore = localBlobStore,
): Promise<ModelEnvelope | null> {
  const bytes = await blobStore.get(localPrincipal(outputFolder), MODEL_KEY(base));
  if (!bytes) return null; // absent — not an error
  let json: unknown;
  try {
    json = JSON.parse(bytes.toString('utf-8'));
  } catch {
    console.warn(`[model-store] malformed JSON in models/${base}.json — ignoring`);
    return null;
  }
  const parsed = ModelEnvelopeSchema.safeParse(json);
  if (!parsed.success) {
    console.warn(`[model-store] models/${base}.json failed schema validation — ignoring`);
    return null;
  }
  return parsed.data;
}
