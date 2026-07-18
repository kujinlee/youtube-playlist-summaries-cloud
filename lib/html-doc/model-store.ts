import { z } from 'zod';
import { MagazineModelSchema } from './types';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import type { BlobStore, ReadOnlyBlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

/**
 * The persisted summary-model file: the Gemini transform output plus provenance.
 * `sourceSections` is the section titles the model was built against — the drift guard the
 * re-render path compares the current .md's section titles against.
 * `generatorVersion` is optional so pre-1F-a local envelopes (written before this field existed)
 * still parse; the cloud freshness gate requires it to `=== GENERATOR_VERSION`.
 */
export const ModelEnvelopeSchema = z
  .object({
    sourceMd: z.string().min(1),
    generatedAt: z.string().min(1),
    sourceSections: z.array(z.string()),
    generatorVersion: z.string().min(1).optional(),
    model: MagazineModelSchema,
    // Stage 3 (§4.2): MD-body-only digest of the MD this model was generated from.
    sourceMdHash: z.string().optional(),
  });
  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
  // must not make an old reader's readModelEnvelope return null (§5.7 round-5 M-2).

export type ModelEnvelope = z.infer<typeof ModelEnvelopeSchema>;

const MODEL_KEY = (base: string) => `models/${base}.json`;

function serialize(envelope: ModelEnvelope): Buffer {
  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
}

/**
 * The single model writer for BOTH the local generate path and the cloud serve path.
 * `put` maps to Supabase `upload(upsert:true)` (atomic per object), so a re-generated model on
 * drift / `generatorVersion` bump OVERWRITES the prior blob — the cache self-heals rather than
 * getting stuck on a stale envelope. (The staged→promote protocol is create-if-absent and stays
 * on the BlobStore for the worker's multi-blob MD commit — it is NOT used for the model.)
 */
export async function writeModelEnvelope(
  principal: Principal,
  base: string,
  envelope: ModelEnvelope,
  blobStore: BlobStore = localBlobStore,
): Promise<void> {
  await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
}

/** Read + validate. Returns null if absent, unparseable, or schema-invalid. */
export async function readModelEnvelope(
  principal: Principal,
  base: string,
  blobStore: ReadOnlyBlobStore = localBlobStore,
): Promise<ModelEnvelope | null> {
  const bytes = await blobStore.get(principal, MODEL_KEY(base));
  if (!bytes) return null;
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
