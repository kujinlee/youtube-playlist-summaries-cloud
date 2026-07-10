/** Bumped whenever the magazine model's shape or generation prompt changes, so a
 *  cached model that predates the change is treated as stale (isFresh → false).
 *  Lives in its own leaf module so the freshness helper (read-model.ts) does not
 *  pull in the full renderer graph. render.ts re-exports it for back-compat. */
export const GENERATOR_VERSION = 'magazine-skim v2';
