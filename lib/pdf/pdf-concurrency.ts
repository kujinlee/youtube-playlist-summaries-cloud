// Parse then clamp SEPARATELY: `parseInt('0') || 3` would turn an explicit `0` into 3 (defeating the
// floor). Default to 3 only when the env is absent/unparseable; otherwise clamp to a floor of 1 so
// `PDF_MAX_CONCURRENCY=0` (or negative) means "minimum 1 render", never a silent capacity inflation.
// (Task-4 dual review: Codex Medium.)
const parsedMaxConcurrency = parseInt(process.env.PDF_MAX_CONCURRENCY ?? '3', 10);
export const PDF_MAX_CONCURRENCY = Number.isNaN(parsedMaxConcurrency) ? 3 : Math.max(1, parsedMaxConcurrency);
export class PdfBusyError extends Error { statusCode = 503; constructor() { super('PDF renderer busy'); this.name = 'PdfBusyError'; } }

const inFlight = new Map<string, Promise<unknown>>();
/** Collapse concurrent same-key work into one call; ALWAYS delete the entry on settle (round-2 High). */
export function runSingleFlight<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = inFlight.get(key) as Promise<T> | undefined;
  if (existing) return existing;
  const p = (async () => fn())();
  inFlight.set(key, p);
  return p.finally(() => { inFlight.delete(key); }) as Promise<T>;
}

let active = 0;
/** Acquire a slot or throw PdfBusyError; release ONLY IF acquired, in finally (round-3 Low). */
export async function withPdfSlot<T>(fn: () => Promise<T>): Promise<T> {
  if (active >= PDF_MAX_CONCURRENCY) throw new PdfBusyError();
  active++;
  try { return await fn(); } finally { active--; }
}
