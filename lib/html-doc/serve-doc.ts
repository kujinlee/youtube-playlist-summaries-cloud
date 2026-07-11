import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import type { ParsedSummary, MagazineModel } from './types';
import { GENERATOR_VERSION } from './constants';
import { writeModelEnvelope } from './model-store';
import { readFreshMagazineModel, readTitleStableModel } from './read-model';
import { generateMagazineModel } from '@/lib/gemini';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';
import {
  MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS, MAX_MAGAZINE_INPUT_TOKENS, MAX_MAGAZINE_OUTPUT_TOKENS,
} from '@/lib/gemini-cost';

/** Serve-side caps for the paid magazine transform (only the magazine fields are load-bearing;
 *  the rest satisfy the CloudGeminiCaps type). */
const SERVE_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
  magazineInputTokens: MAX_MAGAZINE_INPUT_TOKENS,
  magazineOutputTokens: MAX_MAGAZINE_OUTPUT_TOKENS,
};

export type ResolveResult =
  | { status: 'ok'; model: MagazineModel; stale?: boolean }
  | { status: 'busy' }
  | { status: 'attempts_exhausted' }
  | { status: 'at_capacity' }
  | { status: 'over_budget' }
  | { status: 'denied' };

export async function resolveMagazineModel(args: {
  supabaseClient: SupabaseClient;
  blobStore: BlobStore;
  principal: Principal;
  playlistId: string;
  videoId: string;
  base: string;
  parsed: ParsedSummary;
  language: 'en' | 'ko';
  signal?: AbortSignal;
}): Promise<ResolveResult> {
  const { supabaseClient, blobStore, principal, playlistId, videoId, base, parsed, language, signal } = args;
  const titles = parsed.sections.map((s) => s.title);

  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve

  // Absent / drifted / stale-version → materialize under the reserve RPC.
  const { data: reserveStatus, error } = await supabaseClient.rpc('reserve_serve_model', {
    p_playlist_id: playlistId, p_video_id: videoId,
  });
  if (error) throw error;
  switch (reserveStatus) {
    case 'denied': return { status: 'denied' };
    case 'in_flight': {
      // Single-flight: another attempt holds the lease. Serve the model if it landed meanwhile, else busy.
      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
      return now.status === 'ok' ? now : { status: 'busy' };
    }
    case 'attempts_exhausted': return { status: 'attempts_exhausted' };
    case 'at_capacity': return { status: 'at_capacity' };
    case 'owner_over_budget': {
      // Spec D5: serve the title-stable stale rendering instead of failing; else 503.
      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
      return staleRead.status === 'ok'
        ? { status: 'ok', model: staleRead.model, stale: true }
        : { status: 'over_budget' };
    }
    case 'reserved': break;
    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
  }

  // We hold the lease and this attempt was charged. Generate → upsert (overwrite) → serve.
  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
  // regenerated model on drift / version-bump must OVERWRITE the stale blob so the doc self-heals
  // (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).
  // On failure/abort do NOTHING (no release RPC): the lease expires and the next view reclaims (≤ K).
  const model = await generateMagazineModel(
    parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
    language,
    { caps: SERVE_CAPS, signal },
  );
  await writeModelEnvelope(principal, base, {
    sourceMd: parsed.sourceMd ?? `${base}.md`,
    generatedAt: new Date().toISOString(),
    sourceSections: titles,
    generatorVersion: GENERATOR_VERSION,
    model,
  }, blobStore);
  return { status: 'ok', model };
}
