import { generateJson } from '@/lib/gemini';
import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import { z } from 'zod';

const Schema = { parse: (x: unknown) => z.object({ ok: z.boolean() }).parse(x) };

function modelThatMetersThenFails() {
  let call = 0;
  return {
    generateContent: jest.fn(async () => {
      call++;
      if (call === 1) return { response: { text: () => 'not json' } };   // body received → metered, then parse throws
      throw new GoogleGenerativeAIFetchError('overloaded', 503, 'x');      // retry → 503
    }),
  } as any;
}

describe('billing latch set at the model.generateContent primitive', () => {
  it('flips metered=true on a received body even though generateJson ultimately THROWS 503', async () => {
    const billing: BillingLatch = { metered: false };
    await expect(
      generateJson(modelThatMetersThenFails(), 'p', Schema, 'summary', 1, 0, { billing }),
    ).rejects.toBeTruthy();
    expect(billing.metered).toBe(true);                  // 3e: the throw path did not skip the set-point
  });

  it('leaves metered=false when the first-and-only attempt rejects pre-body with 503', async () => {
    const billing: BillingLatch = { metered: false };
    const model = { generateContent: jest.fn(async () => { throw new GoogleGenerativeAIFetchError('x', 503, 'x'); }) } as any;
    await expect(generateJson(model, 'p', Schema, 'summary', 0, 0, { billing })).rejects.toBeTruthy();
    expect(billing.metered).toBe(false);                 // behavior 2b: clean 503 → releasable
  });
});
