import { z } from 'zod';

/**
 * Payload contract for a `summary` job (spec §6). Producer-stable metadata only —
 * NO baseName (handler-derives from the reserved serial) and NO playlist/location
 * (those are identity coordinates on the job itself, never trusted from payload).
 */
export const IngestionPayloadSchema = z.object({
  youtubeUrl: z.string(),
  title: z.string(),
  channel: z.string().optional(),
  // `.finite().positive()` rejects NaN/Infinity/≤0 — otherwise a NaN durationSeconds slips past the
  // handler's `> MAX_DURATION_SECONDS` guard (NaN > MAX is false) and reaches transcribeViaGemini.
  durationSeconds: z.number().finite().positive(),
  playlistIndex: z.number().int().positive(), // 1-indexed (matches VideoSchema.playlistIndex and the local pipeline's i + 1)
  videoPublishedAt: z.string().datetime().optional(),
  addedToPlaylistAt: z.string().datetime().optional(),
});

export type IngestionPayload = z.infer<typeof IngestionPayloadSchema>;

/** Throws (zod ZodError) on a malformed/missing field — callers translate to NonRetryableError. */
export function parseIngestionPayload(payload: unknown): IngestionPayload {
  return IngestionPayloadSchema.parse(payload);
}
