import type { SupabaseClient } from '@supabase/supabase-js';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { readModelEnvelope, type ModelEnvelope } from '@/lib/html-doc/model-store';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { parseCloudDigSectionBlob, slideTokensToCaptions } from '@/lib/dig/cloud/parse-dig-section-blob';
import type { ParsedSummary } from '@/lib/html-doc/types';
import type { DugSection } from '@/lib/dig/companion-doc';

export type LoadDigResult =
  | { ok: true; summary: ParsedSummary; envelope: ModelEnvelope | null; dug: DugSection[]; base: string; title?: string; language: 'en' | 'ko' }
  | { ok: false; status: number; error: string };

/**
 * Load the merge inputs for a cloud dig serve. Reuses loadSummaryForServe for owner-assert +
 * status gate + canonical base — which does NOT charge — then reads the CACHED magazine model
 * (free) and the static per-section dig blobs. It must never touch resolveAndParse /
 * resolveMagazineModel / reserve_serve_model (spec §2 money invariant).
 */
export async function loadDigForServe(
  supabase: SupabaseClient,
  a: { videoId: string; playlistId: string; userId: string },
): Promise<LoadDigResult> {
  const load = await loadSummaryForServe(supabase, a);
  if (!load.ok) return load; // propagate {status, error} verbatim (404/503/409)

  const summary = parseSummaryMarkdown(load.mdBytes.toString('utf-8'));
  summary.sourceMd = load.mdKey;

  const envelope = await readModelEnvelope(load.principal, load.base, load.bundle.blobStore); // cached, free; null if absent

  const prefix = `dig/${load.base}/`;
  const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
  const keys = (await load.bundle.blobStore.list(load.principal, prefix)).filter((k) => k.endsWith(suffix));

  const dug: DugSection[] = [];
  for (const key of keys) {
    const bytes = await load.bundle.blobStore.get(load.principal, key);
    if (!bytes) continue; // listed-but-vanished race → skip
    try {
      const section = parseCloudDigSectionBlob(bytes);
      section.bodyMarkdown = slideTokensToCaptions(section.bodyMarkdown);
      dug.push(section);
    } catch {
      // Malformed/foreign blob → skip this section, never fail the whole doc (behavior 19).
    }
  }

  // Zero current-version digs is NOT a 404 for the interactive frontend: the dig doc is the surface
  // where a user opens (with every section un-dug) and triggers the first dig. The owner-assert +
  // promoted-status gate already ran in loadSummaryForServe above, so serving the merged doc with an
  // empty dug set (all sections render an un-dug `dig deeper ▶` trigger) is correct and safe. (The
  // read-only viewer's original zero→404 is superseded by the frontend slice; loadDigForServe has no
  // other caller. dig-state independently returns {sectionIds: []} for the same case.)
  return { ok: true, summary, envelope, dug, base: load.base, title: load.title, language: (load.video as { language: 'en' | 'ko' }).language };
}
