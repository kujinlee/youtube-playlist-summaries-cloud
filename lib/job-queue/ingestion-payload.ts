import { z } from 'zod';

/**
 * Payload contract for a `summary` job (spec §6). Producer-stable metadata only —
 * NO baseName (handler-derives from the reserved serial) and NO playlist/location
 * (those are identity coordinates on the job itself, never trusted from payload).
 */
export const IngestionPayloadSchema = z.object({
  youtubeUrl: z.string(),
  title: z.string(),
  channel: z.string(),
  durationSeconds: z.number(),
  playlistIndex: z.number(),
  videoPublishedAt: z.string(),
  addedToPlaylistAt: z.string(),
});

export type IngestionPayload = z.infer<typeof IngestionPayloadSchema>;

/** Throws (zod ZodError) on a malformed/missing field — callers translate to NonRetryableError. */
export function parseIngestionPayload(payload: unknown): IngestionPayload {
  return IngestionPayloadSchema.parse(payload);
}
