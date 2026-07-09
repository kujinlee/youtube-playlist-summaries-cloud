import { QuotaExceededError, DailyCapError, VideoTooLongError, mapEnqueueError } from '@/lib/job-queue/errors';

describe('mapEnqueueError', () => {
  it('maps PJ001 to QuotaExceededError', () => {
    const result = mapEnqueueError({ code: 'PJ001' });
    expect(result).toBeInstanceOf(QuotaExceededError);
  });

  it('maps PJ002 to DailyCapError', () => {
    const result = mapEnqueueError({ code: 'PJ002' });
    expect(result).toBeInstanceOf(DailyCapError);
  });

  it('maps PJ003 to VideoTooLongError', () => {
    const result = mapEnqueueError({ code: 'PJ003' });
    expect(result).toBeInstanceOf(VideoTooLongError);
  });

  it('returns the same object (identity) for an unrecognized code', () => {
    const input = { code: '23505' };
    const result = mapEnqueueError(input);
    expect(result).toBe(input);
  });

  it('returns null unchanged', () => {
    expect(mapEnqueueError(null)).toBe(null);
  });

  it('returns undefined unchanged', () => {
    expect(mapEnqueueError(undefined)).toBe(undefined);
  });

  it('passes through an object with no code unchanged', () => {
    const input = {};
    expect(mapEnqueueError(input)).toBe(input);
  });
});
