/**
 * Full-page ("hard") navigation. Kept as a one-line seam so components can trigger a real
 * browser navigation and tests can mock it — jsdom's `window.location` is non-configurable
 * and its `assign` is read-only, so it cannot be spied directly.
 */
export function hardNavigate(to: string): void {
  window.location.assign(to);
}
