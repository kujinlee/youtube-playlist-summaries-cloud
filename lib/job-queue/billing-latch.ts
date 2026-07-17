/**
 * Job-scoped positive metering signal. Flips to true the instant ANY billable Gemini call
 * returns a response body (proof-of-meter). Set at the model.generateContent primitive so it
 * fires even when the surrounding function later throws. Job is the maximal scope for a
 * reservation, so this is terminal-correct. See design spec §3.1.
 */
export interface BillingLatch {
  metered: boolean;
}
