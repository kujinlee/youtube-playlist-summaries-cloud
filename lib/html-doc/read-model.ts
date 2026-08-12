import type { MagazineModel } from './types';
import type { Principal } from '@/lib/storage/principal';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';
import { GENERATOR_VERSION } from './constants';
import { readModelEnvelope } from './model-store';

// GENERATE-FREE LEAF (spec D13/B18c): this module and its entire import graph must never
// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
// /s/[token] route therefore cannot pull in the charging code. Enforced by tests/lib/share/
// import-guard.test.ts (a jest grep guard; the repo has no ESLint).

export function sameTitles(
  envelope: { sourceSections: string[] },
  titles: string[],
): boolean {
  return envelope.sourceSections.length === titles.length &&
    envelope.sourceSections.every((t, i) => t === titles[i]);
}

export function isFresh(
  envelope: { sourceSections: string[]; generatorVersion?: string },
  titles: string[],
): boolean {
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
}

/** Read-only, generation-free: returns the cached model iff present AND fresh; otherwise
 *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call). */
export async function readFreshMagazineModel(args: {
  blobStore: ReadOnlyBlobStore;
  principal: Principal;
  base: string;
  titles: string[];
}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }> {
  const { blobStore, principal, base, titles } = args;
  const existing = await readModelEnvelope(principal, base, blobStore);
  if (existing && isFresh(existing, titles)) return { status: 'ok', model: existing.model };
  return { status: 'not_ready' };
}

/** Title-stable read (spec D5): returns the cached model iff the envelope exists AND its section
 *  titles match `titles` (generator version may differ — the version-bump case). Positionally
 *  coherent to render against current markdown. Never reserves/generates (pure blob read).
 *
 *  COVERAGE CHECK (added 2026-08-11, B4 review High-2): `sameTitles` compares `sourceSections` to
 *  `titles` and says NOTHING about `model.sections.length`. Nothing enforces the two agree —
 *  `ModelEnvelopeSchema` does not relate them and `writeModelEnvelope` does not check — so an
 *  envelope with two `sourceSections` and one model section passes `sameTitles`. `renderMagazineHtml`
 *  pairs by index and returns `''` for a missing model section (lib/html-doc/render.ts:84), so that
 *  envelope renders a **200 with a silently blank section**.
 *  `>=` rather than `===`: the requirement is that every PARSED section has a model section to pair
 *  with. Surplus model sections are simply never indexed, and rejecting them would refuse an
 *  otherwise-renderable document.
 *  Deliberately NOT added to `isFresh`: that governs the OWNER path, where refusing an envelope
 *  triggers a reserve-and-charge regeneration. Making a money path stricter is its own slice with
 *  its own review — this one only hardens the path B4 widened. */
export async function readTitleStableModel(args: {
  blobStore: ReadOnlyBlobStore;
  principal: Principal;
  base: string;
  titles: string[];
}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'none' }> {
  const { blobStore, principal, base, titles } = args;
  const existing = await readModelEnvelope(principal, base, blobStore);
  if (existing && sameTitles(existing, titles) && existing.model.sections.length >= titles.length) {
    return { status: 'ok', model: existing.model };
  }
  return { status: 'none' };
}
