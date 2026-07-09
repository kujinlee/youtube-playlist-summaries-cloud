import { perRunWorstCents, SUMMARY_MAX_PASSES, TRANSCRIBE_MAX_PASSES } from '../../lib/gemini-cost';
import { SUMMARY_MODEL } from '../../lib/gemini';

describe('gemini-cost', () => {
  test('perRunWorstCents(1800s) lands in the sound-margin range [110,130]', () => {
    const cents = perRunWorstCents({ maxDurationSeconds: 1800 });
    expect(cents).toBeGreaterThanOrEqual(110);
    expect(cents).toBeLessThanOrEqual(130);
  });

  test('pass-count constants', () => {
    expect(SUMMARY_MAX_PASSES).toBe(12);
    expect(TRANSCRIBE_MAX_PASSES).toBe(3);
  });

  test('resolved SUMMARY_MODEL equals priced model with env unset', () => {
    expect(SUMMARY_MODEL).toBe('gemini-2.5-flash');
  });
});
