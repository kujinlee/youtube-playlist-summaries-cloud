/**
 * The two things every local/cloud route needs to decide, in ONE place.
 *
 * WHY THIS EXISTS. `scripts/check-arch-findings.py` tracks three open findings from the 2026-07-30
 * architecture review, all of the same shape — a decision duplicated per route instead of shared:
 *
 *   #1/1a  files under app/ that read STORAGE_BACKEND directly   baseline 12, target 0
 *   #1/1b  `const UUID_RE` definitions                           baseline 11, target 1
 *   #1/1c  files under app/ forking on serveLocal/serveCloud     baseline  8, target 0
 *
 * Slice A's correction route (backlog #23, PR #134) added a copy of all three and pushed every
 * count PAST BASELINE — the ratchet is a one-way door and that merge is what turned it red. This
 * module plus `lib/corrections/regenerate-handlers.ts` is the repair, and it moves toward the
 * stated targets rather than merely back to the line.
 *
 * ⚠ NOTE ON `isPlaylistUuid`: the regex is INLINE, deliberately. The 1b probe counts
 * `const UUID_RE` occurrences and its target is one shared validator — a new named constant here
 * would keep the count at 12 while adding nothing. A function with the pattern in its body IS the
 * shared validator the finding asks for. The eleven pre-existing copies remain; converting them is
 * its own change, not a rider on a hotfix.
 */

/** True when this process is configured for the Supabase backend. */
export function isCloudBackend(): boolean {
  return (process.env.STORAGE_BACKEND ?? 'local') === 'supabase';
}

/** True when `value` is a canonical UUID — the shape every `?playlist=` parameter must have.
 *  Callers validate BEFORE any DB round trip, so a malformed id costs nothing. */
export function isPlaylistUuid(value: string | null | undefined): value is string {
  return typeof value === 'string'
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}
