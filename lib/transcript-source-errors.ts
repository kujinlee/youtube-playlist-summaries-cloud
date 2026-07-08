/**
 * Deterministic no-source error: thrown by resolveTranscriptSegments only when BOTH captions
 * and the Gemini fallback returned zero segments (as opposed to throwing/timing out). This is a
 * permanent condition — retrying resolveTranscriptSegments again won't produce a transcript — so
 * callers (e.g. the cloud worker) can distinguish it from a transient failure worth retrying.
 */
export class PermanentTranscriptError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'PermanentTranscriptError';
  }
}
