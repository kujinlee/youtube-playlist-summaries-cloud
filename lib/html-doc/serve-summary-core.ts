import type { SupabaseClient } from '@supabase/supabase-js';
import { getStorageBundle, getPrincipalFromSession, type StorageBundle } from '@/lib/storage/resolve';
import { resolveOwnedPlaylistKey } from '@/lib/storage/serve-playlist';
import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import type { Principal } from '@/lib/storage/principal';
import type { Video } from '@/types';

export type LoadResult =
  | {
      ok: true;
      mdBytes: Buffer;
      mdKey: string;
      base: string;
      title?: string;
      principal: Principal;
      playlistId: string;
      video: Video;
      bundle: StorageBundle;
    }
  | { ok: false; status: number; error: string };

/**
 * Two-stage split of `serveCloud`'s gate→read→resolve→render core (app/api/html/[id]/route.ts),
 * split at the `resolveMagazineModel` boundary so both the HTML route (Task 7) and the PDF route
 * (Task 8) can share it while the `format=md` no-charge short-circuit survives (D4 money invariant:
 * the md path must read the blob and return WITHOUT ever calling resolveMagazineModel).
 *
 * Mirrors serveCloud lines ~45-83. Does NOT resolve/charge — that is stage 2 (resolveAndParse).
 * Note: assertVideoId is done by the CALLER route in param validation (before auth, preserving the
 * existing 400-before-401 ordering) — this helper does not repeat it.
 */
export async function loadSummaryForServe(
  supabase: SupabaseClient,
  a: { videoId: string; playlistId: string; userId: string },
): Promise<LoadResult> {
  const playlistKey = await resolveOwnedPlaylistKey(supabase, a.playlistId, a.userId); // owner-asserted (D6/D9)
  if (!playlistKey) return { ok: false, status: 404, error: 'not found' };

  const principal = getPrincipalFromSession({ userId: a.userId }, playlistKey);
  const bundle = getStorageBundle({ supabaseClient: supabase }); // session-scoped, RLS-enforced (D5)
  const index = await bundle.metadataStore.readIndex(principal);
  const video = index.videos.find((v) => v.id === a.videoId) as Video | undefined;
  if (!video) return { ok: false, status: 404, error: 'not found' };

  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
    .artifacts?.summaryMd;
  const status = artifact?.status;
  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };          // absent/unknown (B13)

  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
  // video.summaryMd — mirrors serveCloud's Codex H-2 fix (don't fetch a blob the artifact record
  // doesn't govern).
  const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
  if (!mdKey) return { ok: false, status: 404, error: 'not found' };

  // Task-2 guard: reject a corrupt/nested key BEFORE reading the blob (409, no blob fetch attempted).
  try {
    assertCloudSummaryMdKey(mdKey);
  } catch {
    return { ok: false, status: 409, error: 'corrupt summary key' };
  }

  const mdBytes = await bundle.blobStore.get(principal, mdKey);
  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' }; // promoted but blob lost (B13b)

  // IDENTITY COHERENCE (carried from serveCloud): `base` is the canonical, DB-persisted baseName,
  // derived deterministically from the SAME summaryMd key the model store is keyed on.
  const base = mdKey.replace(/\.md$/, '');

  // M1 (1F-c whole-branch review): coerce a non-string/blank title to undefined defensively.
  const rawTitle: unknown = (video as unknown as { title?: unknown }).title;
  const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;

  return { ok: true, mdBytes, mdKey, base, title, principal, playlistId: a.playlistId, video, bundle };
}

type OkLoad = Extract<LoadResult, { ok: true }>;

export type ResolveAndParseResult =
  | { ok: true; parsed: ReturnType<typeof parseSummaryMarkdown>; model: unknown; stale: boolean }
  | { ok: false; status: number; error: string };

/**
 * Stage 2: parse the markdown + resolve (and possibly charge for) the magazine model. Maps
 * `resolveMagazineModel`'s ResolveResult (lib/html-doc/serve-doc.ts:26) to HTTP codes. Error
 * strings below are copied VERBATIM from serveCloud (app/api/html/[id]/route.ts:101-105) — the
 * existing html-download integration tests assert these exact strings. Do NOT paraphrase.
 */
export async function resolveAndParse(
  supabase: SupabaseClient,
  load: OkLoad,
  signal?: AbortSignal,
): Promise<ResolveAndParseResult> {
  const parsed = parseSummaryMarkdown(load.mdBytes.toString('utf-8'));
  parsed.sourceMd = load.mdKey;

  const resolved = await resolveMagazineModel({
    supabaseClient: supabase,
    blobStore: load.bundle.blobStore,
    principal: load.principal,
    playlistId: load.playlistId,
    videoId: load.video.id,
    base: load.base,
    parsed,
    language: load.video.language, // Video.language is already the 'en'|'ko' enum (types/index.ts:51)
    signal,
  });

  switch (resolved.status) {
    case 'denied': return { ok: false, status: 404, error: 'not found' };                                          // generic, no leak
    case 'busy': return { ok: false, status: 503, error: 'generating, retry shortly' };                            // B6b
    case 'attempts_exhausted': return { ok: false, status: 503, error: 'temporarily unavailable, try later' };     // B7f
    case 'at_capacity': return { ok: false, status: 503, error: 'at capacity' };                                   // B6
    case 'over_budget': return { ok: false, status: 503, error: 'daily refresh budget reached, try tomorrow' };    // D6/G1
    case 'ok': return { ok: true, parsed, model: resolved.model, stale: resolved.stale === true };
  }
}
