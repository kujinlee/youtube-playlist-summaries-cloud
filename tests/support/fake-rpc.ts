/**
 * A chainable thenable standing in for a PostgrestFilterBuilder.
 *
 * Needed because production now calls `.abortSignal(signal)` before awaiting. A bare
 * `jest.fn(async () => ({data, error}))` has no `.abortSignal` and throws TypeError — which is
 * exactly how Task 6 would have broken the existing seam fakes.
 */
export function fakeRpcBuilder<T>(
  result: { data: T; error: unknown } | (() => Promise<{ data: T; error: unknown }>),
) {
  const settle = typeof result === 'function' ? result : async () => result;
  // `then` MUST match PromiseLike.then or the builder is not assignable to PromiseLike under
  // --strict (plan-review r2 Blocking).
  type Row = { data: T; error: unknown };
  const builder: PromiseLike<Row> & { abortSignal(s: AbortSignal): typeof builder } = {
    abortSignal(_s: AbortSignal) { return builder; },
    then<R1 = Row, R2 = never>(
      onOk?: ((v: Row) => R1 | PromiseLike<R1>) | null,
      onErr?: ((e: unknown) => R2 | PromiseLike<R2>) | null,
    ): PromiseLike<R1 | R2> {
      return settle().then(onOk, onErr);
    },
  };
  return builder;
}
