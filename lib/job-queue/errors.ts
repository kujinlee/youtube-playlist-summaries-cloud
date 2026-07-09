export class NonRetryableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NonRetryableError';
  }
}

export class QuotaExceededError extends Error {
  constructor(message = 'quota_exceeded') {
    super(message);
    this.name = 'QuotaExceededError';
  }
}

export class DailyCapError extends Error {
  constructor(message = 'daily_cap_exceeded') {
    super(message);
    this.name = 'DailyCapError';
  }
}

export class VideoTooLongError extends Error {
  constructor(message = 'too_long') {
    super(message);
    this.name = 'VideoTooLongError';
  }
}

/**
 * Maps a Postgres error's SQLSTATE (as surfaced by supabase-js) to a typed
 * guardrail error. PJ001/PJ002/PJ003 are the enqueue_job guardrail codes
 * (quota / daily cap / duration backstop). Any other code — including a
 * missing/null/undefined input — is returned UNCHANGED (same reference):
 * callers rely on `===` identity to detect "not a guardrail error, rethrow
 * as-is." Return type is `unknown` because a Supabase/PG error object is not
 * necessarily an `Error` instance.
 */
export function mapEnqueueError(pgError: { code?: string } | null | undefined): unknown {
  switch (pgError?.code) {
    case 'PJ001':
      return new QuotaExceededError();
    case 'PJ002':
      return new DailyCapError();
    case 'PJ003':
      return new VideoTooLongError();
    default:
      return pgError;
  }
}
