/**
 * A Supabase RPC call with a bounded WAIT and an honest outcome.
 *
 * Deliberately does NOT inspect postgrest's error shape to detect a timeout. Two independent
 * reasons, both verified against the installed client:
 *
 *  1. With `shouldThrowOnError=false` (its default) an aborted fetch is CAUGHT and RETURNED as
 *     `{ success:false, error, data:null }` — never thrown. A `try/catch` around
 *     `.abortSignal(...)` is dead code, and a caller reading only the catch would report a settle
 *     that never happened.
 *  2. Its abort special-case tests `name === 'AbortError' || code === 'ABORT_ERR'`, while
 *     `AbortSignal.timeout()` aborts with a `TimeoutError`. Our own timeouts would not even match
 *     the branch meant for them.
 *
 * Racing our own timer keeps the verdict ours, independent of both.
 *
 * The union mirrors BlobRead (`lib/storage/blob-store.ts:10-13`): a caller must not be able to
 * collapse "timed out" into "returned an error" — they have different money consequences.
 */
export type RpcOutcome<T> =
  | { ok: true; data: T }
  | { ok: false; reason: 'timeout' }
  | { ok: false; reason: 'error'; cause: unknown };

export async function callRpcBounded<T>(
  make: (signal: AbortSignal) => PromiseLike<{ data: T; error: unknown }>,
  timeoutMs: number,
  label: string,
): Promise<RpcOutcome<T>> {
  const ctrl = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const expiry = new Promise<{ kind: 'timeout' }>((resolve) => {
    timer = setTimeout(() => { ctrl.abort(); resolve({ kind: 'timeout' }); }, timeoutMs);
  });
  try {
    // `make` is invoked inside the try AND its rejection is folded into the union: a synchronous
    // throw or a rejected builder must not escape as an exception, or the `!ok` callers miss it
    // entirely (plan-review r2 High).
    const attempt = (async () => {
      try {
        return { kind: 'settled' as const, r: await make(ctrl.signal) };
      } catch (cause) {
        return { kind: 'threw' as const, cause };
      }
    })();
    const raced = await Promise.race([attempt, expiry]);
    if (raced.kind === 'threw') return { ok: false, reason: 'error', cause: raced.cause };
    if (raced.kind === 'timeout') {
      console.warn(`[serve-rpc] ${label} exceeded ${timeoutMs}ms`);
      return { ok: false, reason: 'timeout' };
    }
    if (raced.r.error) return { ok: false, reason: 'error', cause: raced.r.error };
    return { ok: true, data: raced.r.data };
  } finally {
    if (timer) clearTimeout(timer);   // else the timer holds the event loop open
  }
}
