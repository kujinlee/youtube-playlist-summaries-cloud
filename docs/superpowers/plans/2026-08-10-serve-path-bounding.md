# Serve-Path Bounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound every call the serve path makes while holding a paid `serve_model_charge` lease, and stop the lease from being configured shorter than that bounded work.

**Architecture:** No runtime deadline and no coordination protocol. Every external call gets a fixed timeout; those timeouts sum to a build-time constant (`SERVE_FLOOR_MS`); a Postgres CHECK constraint refuses any `lease_ttl_seconds` below that constant. The existing `serve_model_charge` lease remains the sole mechanism preventing a second paid producer — this plan does not touch it.

**Tech Stack:** TypeScript, Next.js, Jest (`ts-jest`), Supabase (`postgrest-js` 2.109.0, Storage), `@google/generative-ai`.

**Spec:** [`docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md`](../specs/2026-08-10-serve-path-deadline-design.md) at **v6**. Six review rounds; §7 carries the trail.

## Global Constraints

- **Node 22** — `AbortSignal.timeout` and `AbortSignal.any` are assumed available (`.github/workflows/ci.yml`).
- **The refund rule at `lib/html-doc/serve-doc.ts:130-132` must not change behaviour.** `classifyGeminiFailure(err, signal) === 'release' && !billing.metered` decides refunds. Two previous spec versions revoked this accidentally — once by rewriting it, once by bounding its transport. Any task that touches it must prove by test that a not-metered 429 still refunds.
- **`over-count is safe, under-count is the bug`** (`serve-doc.ts:107-110`). Where a failure mode forces a choice, keep the charge.
- **Serve-path-only.** Local generation (`lib/html-doc/generate.ts:40`) must keep `GENERATE_JSON_RETRIES` (3 attempts) and `REQUEST_TIMEOUT_MS` (60 s). Every task that changes a shared function asserts the local path is unaffected.
- **Optional parameters do not propagate** (`docs/process-checklists.md:64-68`). Where omitting a bound would silently restore the bug, the boundary gets a wrapper with a **required** parameter, never an optional field on an existing signature.
- **Mutation-check every guard** (`docs/process-checklists.md:76-81`): delete the guard → covering tests must go red → restore. Commit the fix before mutating.
- Branch `fix/serve-path-deadline` (already exists, spec committed). Branch + PR; **merging is a human gate**.

---

## File Structure

| File | Responsibility |
|---|---|
| `lib/serve-budget.ts` | **new.** Every timeout constant, the sum, and `SERVE_FLOOR_SECONDS`. Single home so the migration literal has one thing to be pinned against. Imports nothing from `lib/gemini.ts` to avoid a cycle — it re-declares nothing, it *owns* the serve-path numbers. |
| `lib/gemini.ts` | `assertMagazineInputWithinCap` gains a signal; `generateJson` gains `timeoutMs`; new `generateMagazineModelForServe` wrapper with a **required** budget. |
| `lib/html-doc/model-store.ts` | new `writeModelEnvelopeWithin` — required `timeoutMs`, races the `put`. |
| `lib/serve-rpc.ts` | **new.** `callRpcBounded` — a bounded RPC returning an honest `{ok:false, reason:'timeout'\|'error'}` union, so a timeout can never be read as success. |
| `lib/html-doc/serve-doc.ts` | calls the two wrappers; bounds both RPCs; retries settle once on the release path; maps a reserve timeout to `busy`; exports `SERVE_CAPS`. |
| `supabase/migrations/0024_lease_covers_serve.sql` | **new.** Raises the `lease_ttl_seconds` CHECK floor to `SERVE_FLOOR_SECONDS`. |
| `tests/lib/serve-budget.test.ts` | **new.** The sum, the bounds, the unit discipline. |
| `tests/lib/gemini-serve-budget.test.ts` | **new.** Wrapper behaviour + local path unaffected. |
| `tests/lib/serve-rpc.test.ts` | **new.** Timeout vs. returned-error, and that the request is actually aborted. |
| `tests/support/fake-rpc.ts` | **new.** A chainable thenable standing in for a PostgrestFilterBuilder. Existing bare `jest.fn(async …)` rpc fakes have no `.abortSignal` and would break. |
| `tests/lib/html-doc/serve-doc-mapping.test.ts` | **modify** — its `fakeSupabase` must return a builder (Task 6, Step 1). |
| `tests/lib/html-doc/read-model.test.ts` | **new.** Characterises the accepted residual. |
| `tests/lib/html-doc/model-store.test.ts` | extend — the put race. |
| `tests/integration/serve-config-invariant.test.ts` | extend — the CHECK floor, plus its mutation. |
| `tests/integration/serve-doc-materialize.test.ts` | extend — refund survives, reserve timeout, settle retry. |

**Task order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Task 1 is a hard dependency for 6 and 7; Task 5 is a
hard dependency for 6.

**Task 5 was added after the plan's first adversarial round.** The original Task 5 assumed
`.abortSignal()` made postgrest *throw* on timeout. It does not — it returns `{ error }` — so the
settle would have reported a refund it never applied. The bounded-RPC seam is now its own task with
its own tests, rather than four lines inside a wiring task.

---

### Task 1: The budget constants and their arithmetic

**Files:**
- Create: `lib/serve-budget.ts`
- Test: `tests/lib/serve-budget.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `SERVE_RESERVE_RPC_TIMEOUT_MS`, `SERVE_COUNT_TOKENS_TIMEOUT_MS`, `SERVE_ATTEMPT_TIMEOUT_MS`, `SERVE_ATTEMPTS`, `SERVE_BACKOFF_TOTAL_MS`, `SERVE_PUT_TIMEOUT_MS`, `SERVE_SETTLE_RPC_TIMEOUT_MS`, `SERVE_MARGIN_MS`, `SERVE_BOUNDED_MS`, `SERVE_FLOOR_MS`, `SERVE_FLOOR_SECONDS`, and the type `ServeBudget`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/serve-budget.test.ts
import {
  SERVE_RESERVE_RPC_TIMEOUT_MS, SERVE_COUNT_TOKENS_TIMEOUT_MS, SERVE_ATTEMPT_TIMEOUT_MS,
  SERVE_ATTEMPTS, SERVE_BACKOFF_TOTAL_MS, SERVE_PUT_TIMEOUT_MS, SERVE_SETTLE_RPC_TIMEOUT_MS,
  SERVE_MARGIN_MS, SERVE_BOUNDED_MS, SERVE_FLOOR_MS, SERVE_FLOOR_SECONDS,
} from '@/lib/serve-budget';

// The shipped default from supabase/migrations/0012_serve_model_charge.sql:22.
const SHIPPED_LEASE_TTL_SECONDS = 180;

describe('serve budget', () => {
  it('SERVE_BOUNDED_MS is exactly the sum of the enforced terms', () => {
    expect(SERVE_BOUNDED_MS).toBe(
      SERVE_RESERVE_RPC_TIMEOUT_MS
      + SERVE_COUNT_TOKENS_TIMEOUT_MS
      + SERVE_ATTEMPTS * SERVE_ATTEMPT_TIMEOUT_MS
      + SERVE_BACKOFF_TOTAL_MS
      + SERVE_PUT_TIMEOUT_MS
      + SERVE_SETTLE_RPC_TIMEOUT_MS,
    );
  });

  it('the floor adds the unbounded-work margin on top of the enforced sum', () => {
    expect(SERVE_FLOOR_MS).toBe(SERVE_BOUNDED_MS + SERVE_MARGIN_MS);
  });

  // ceil, never floor: we must never declare less time than we need.
  it('SERVE_FLOOR_SECONDS rounds UP from milliseconds', () => {
    expect(SERVE_FLOOR_SECONDS).toBe(Math.ceil(SERVE_FLOOR_MS / 1000));
  });

  // This is the assertion that would have caught the live defect: today's serve path
  // is 181_200ms against a 180_000ms lease.
  it('the floor fits inside the shipped lease default', () => {
    expect(SERVE_FLOOR_SECONDS).toBeLessThanOrEqual(SHIPPED_LEASE_TTL_SECONDS);
  });

  it('backoff matches generateJson: one 400ms gap between two attempts', () => {
    // gemini.ts:267 — baseDelayMs * 2**attempt, baseDelayMs = 400, gaps = SERVE_ATTEMPTS - 1
    let expected = 0;
    for (let i = 0; i < SERVE_ATTEMPTS - 1; i++) expected += 400 * 2 ** i;
    expect(SERVE_BACKOFF_TOTAL_MS).toBe(expected);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest serve-budget -v`
Expected: FAIL — `Cannot find module '@/lib/serve-budget'`

- [ ] **Step 3: Write minimal implementation**

```ts
// lib/serve-budget.ts
/**
 * The serve path's time budget, as a STATIC sum.
 *
 * Every constant below except SERVE_MARGIN_MS corresponds to a timeout the code actually
 * applies. That is the whole design: a term that is only *added* is not a bound, and the
 * spec's round-5 Blocking was exactly such a term (see the spec, §3.2).
 *
 * SERVE_MARGIN_MS is the one exception and is labelled an assumption, not a budget: it covers
 * work no timeout can bound (JS scheduling, GC, JSON.parse, Zod, mdHash, client construction,
 * TLS setup).
 *
 * Deliberately imports nothing. lib/gemini.ts's REQUEST_TIMEOUT_MS is the LOCAL path's
 * per-attempt timeout and stays 60s; the serve path has its own, and conflating them is how
 * the local path would silently inherit a serve-only change.
 */

/** One round trip to Postgres. PROVISIONAL — revise from observed p99. */
export const SERVE_RESERVE_RPC_TIMEOUT_MS = 5_000;
/** Gemini countTokens preflight. PROVISIONAL — never measured; revise from observed p99. */
export const SERVE_COUNT_TOKENS_TIMEOUT_MS = 10_000;
/** Per generateContent attempt on the SERVE path only (local keeps REQUEST_TIMEOUT_MS = 60s). */
export const SERVE_ATTEMPT_TIMEOUT_MS = 50_000;
/** Attempts on the serve path. 3 does not fit the lease — that is the defect being fixed. */
export const SERVE_ATTEMPTS = 2;
/** generateJson backoff: 400 * 2**n summed over (SERVE_ATTEMPTS - 1) gaps (gemini.ts:267). */
export const SERVE_BACKOFF_TOTAL_MS = 400;
/** One small-JSON upload. PROVISIONAL — revise from observed p99. */
export const SERVE_PUT_TIMEOUT_MS = 15_000;
/** One round trip to Postgres. PROVISIONAL — revise from observed p99. */
export const SERVE_SETTLE_RPC_TIMEOUT_MS = 5_000;

/**
 * ASSUMPTION, not a bound. ~13% of the bounded budget for unmodelled local work.
 * REVISE UPWARD on any observed lease expiry the bounded terms cannot explain.
 */
export const SERVE_MARGIN_MS = 20_000;

export const SERVE_BOUNDED_MS =
  SERVE_RESERVE_RPC_TIMEOUT_MS
  + SERVE_COUNT_TOKENS_TIMEOUT_MS
  + SERVE_ATTEMPTS * SERVE_ATTEMPT_TIMEOUT_MS
  + SERVE_BACKOFF_TOTAL_MS
  + SERVE_PUT_TIMEOUT_MS
  + SERVE_SETTLE_RPC_TIMEOUT_MS;

export const SERVE_FLOOR_MS = SERVE_BOUNDED_MS + SERVE_MARGIN_MS;

/** Ceil, never floor — we must never declare less time than we need. Pinned by migration 0024. */
export const SERVE_FLOOR_SECONDS = Math.ceil(SERVE_FLOOR_MS / 1000);

/** Passed as a REQUIRED argument across the serve boundary so it cannot be forgotten. */
export interface ServeBudget {
  attempts: number;
  attemptTimeoutMs: number;
  countTokensTimeoutMs: number;
}

export const SERVE_BUDGET: ServeBudget = {
  attempts: SERVE_ATTEMPTS,
  attemptTimeoutMs: SERVE_ATTEMPT_TIMEOUT_MS,
  countTokensTimeoutMs: SERVE_COUNT_TOKENS_TIMEOUT_MS,
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest serve-budget -v`
Expected: PASS (5 tests). `SERVE_BOUNDED_MS` = 135_400, `SERVE_FLOOR_MS` = 155_400, `SERVE_FLOOR_SECONDS` = 156.

- [ ] **Step 5: Commit**

```bash
git add lib/serve-budget.ts tests/lib/serve-budget.test.ts
git commit -m "feat(#46): the serve path's budget as one static sum

Every term except SERVE_MARGIN_MS is a timeout the code will actually apply.
The margin is labelled an assumption because nothing can time out GC, parse
or scheduling — and a term that is only added is not a bound."
```

---

### Task 2: Bound `countTokens`

**Files:**
- Modify: `lib/gemini.ts:72-88` (`assertMagazineInputWithinCap`)
- Test: `tests/lib/gemini-magazine-caps.test.ts` (exists — extend)

**Interfaces:**
- Consumes: Task 1's `SERVE_COUNT_TOKENS_TIMEOUT_MS` (via the caller, not imported here).
- Produces: `assertMagazineInputWithinCap(model, prompt, generationConfig, caps, opts?: { signal?: AbortSignal; timeoutMs?: number })`.

**Note on the optional here:** `timeoutMs` is optional *at this level* because `assertMagazineInputWithinCap` is an internal helper reached only through `generateMagazineModel`. The **required** boundary is Task 3's wrapper. Do not add a required param here — it would force the local path to supply a serve number.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/gemini-magazine-caps.test.ts — add to the existing describe
it('passes an abort signal and timeout to countTokens', async () => {
  const seen: Array<{ signal?: AbortSignal; timeout?: number }> = [];
  const model = {
    countTokens: jest.fn(async (_req: unknown, opts?: { signal?: AbortSignal; timeout?: number }) => {
      seen.push({ signal: opts?.signal, timeout: opts?.timeout });
      return { totalTokens: 10 };
    }),
  };
  const ctrl = new AbortController();
  await assertMagazineInputWithinCap(
    model as never, 'prompt', {}, { magazineInputTokens: 100 } as never,
    { signal: ctrl.signal, timeoutMs: 1234 },
  );
  expect(seen[0].signal).toBe(ctrl.signal);
  expect(seen[0].timeout).toBe(1234);
});

it('rejects with AbortError when the signal is already aborted', async () => {
  const model = {
    countTokens: jest.fn(async (_r: unknown, opts?: { signal?: AbortSignal }) => {
      if (opts?.signal?.aborted) throw new DOMException('aborted', 'AbortError');
      return { totalTokens: 10 };
    }),
  };
  // Assert the error IDENTITY, not that "something threw" — a test accepting any error
  // passes on a typo.
  await expect(assertMagazineInputWithinCap(
    model as never, 'p', {}, { magazineInputTokens: 100 } as never,
    { signal: AbortSignal.abort() },
  )).rejects.toMatchObject({ name: 'AbortError' });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest gemini-magazine-caps -v`
Expected: FAIL — the 5th argument is not accepted / `seen[0].signal` is `undefined`.

- [ ] **Step 3: Write minimal implementation**

```ts
// lib/gemini.ts — replace the signature and the countTokens call
export async function assertMagazineInputWithinCap(
  model: Pick<GenerativeModel, 'countTokens'>,
  prompt: string,
  generationConfig: GenerationConfig,
  caps: CloudGeminiCaps,
  opts?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<void> {
  const cap = caps.magazineInputTokens;
  if (cap == null) {
    throw new NonRetryableError('cloud magazine caps missing magazineInputTokens');
  }
  // SingleRequestOptions (generative-ai.d.ts:1297-1306) carries both signal and timeout.
  const { totalTokens } = await model.countTokens(
    {
      generateContentRequest: {
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig,
      },
    },
    { ...(opts?.signal ? { signal: opts.signal } : {}), ...(opts?.timeoutMs ? { timeout: opts.timeoutMs } : {}) },
  );
  if (totalTokens > cap) {
    throw new NonRetryableError(`magazine input ${totalTokens} tokens exceeds cap ${cap}`);
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest gemini-magazine-caps gemini-caps -v`
Expected: PASS, including the pre-existing cap tests (the new param is optional, so existing callers compile).

- [ ] **Step 5: Run the full unit suite**

Run: `npm test`
Expected: no regressions.

- [ ] **Step 6: Commit**

```bash
git add lib/gemini.ts tests/lib/gemini-magazine-caps.test.ts
git commit -m "feat(#46): give the countTokens preflight a signal and a timeout

It was the one call on the serve path with no bound at all, while the retry
loop around it was already fully abortable."
```

---

### Task 3: The serve wrapper with a REQUIRED budget

**Files:**
- Modify: `lib/gemini.ts:246-253` (`generateJson` — add `timeoutMs`), `lib/gemini.ts:499-505` (add the wrapper below `generateMagazineModel`)
- Create: `tests/lib/gemini-serve-budget.test.ts`

**Interfaces:**
- Consumes: `ServeBudget`, `SERVE_BUDGET` (Task 1); `assertMagazineInputWithinCap` opts (Task 2).
- Produces: `generateMagazineModelForServe(sections, language, budget: ServeBudget, opts?): Promise<MagazineModel>` and `generateJson(model, prompt, schema, label, retries?, baseDelayMs?, opts?, timeoutMs?)`.

**Why a wrapper and not an optional field:** an optional `opts.serve?` lets the serve caller keep its current argument list, compile clean, and run 3 attempts at 60 s while the CHECK floor assumes 2 at 50 s — the floor would be wrong in the one configuration nobody tested. `docs/process-checklists.md:64-68`: required, not optional.

- [ ] **Step 1: Write the failing test**

**All helpers used below are defined in this block or imported.** An earlier draft referenced
`mockModel`, `okResponse` and `SERVE_CAPS` without defining them, and `SERVE_CAPS` is a *private*
const at `lib/html-doc/serve-doc.ts:20` — the test could not have compiled (plan-review r1 High).
Task 6 exports it; until then this file builds its own caps.

```ts
// tests/lib/gemini-serve-budget.test.ts
import { GoogleGenerativeAI } from '@google/generative-ai';
import { generateMagazineModel, generateMagazineModelForServe } from '@/lib/gemini';
import { SERVE_BUDGET } from '@/lib/serve-budget';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';   // NOT @/lib/gemini-caps — that module does not exist

jest.mock('@google/generative-ai');

// Mirrors serve-doc.ts:20. Local to this file so the test does not depend on Task 6's export.
const TEST_CAPS: CloudGeminiCaps = { magazineInputTokens: 100_000, magazineOutputTokens: 8_000 } as CloudGeminiCaps;

/** One valid magazine JSON response body. */
// MagazineModelSchema requires 3-7 bullets. One bullet fails Zod and the test would throw for the
// wrong reason. Mirrors the fixtures in serve-doc-mapping.test.ts:15-17.
const okResponse = () => ({
  response: {
    text: () => JSON.stringify({
      sections: [{ lead: 'L', bullets: [
        { label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' },
      ] }],
    }),
  },
});

/** Point the mocked SDK at a model whose generateContent/countTokens we control. */
function mockModel(m: { generateContent: jest.Mock; countTokens?: jest.Mock }) {
  const countTokens = m.countTokens ?? jest.fn(async () => ({ totalTokens: 10 }));
  (GoogleGenerativeAI as unknown as jest.Mock).mockImplementation(() => ({
    getGenerativeModel: () => ({ ...m, countTokens }),
  }));
}

describe('generateMagazineModelForServe', () => {
  it('makes at most SERVE_BUDGET.attempts generateContent calls', async () => {
    const generateContent = jest.fn(async () => { throw new Error('boom'); });
    mockModel({ generateContent });
    await expect(generateMagazineModelForServe(
      [{ title: 'A', prose: 'x' }], 'en', SERVE_BUDGET, { caps: TEST_CAPS },
    )).rejects.toThrow();
    expect(generateContent).toHaveBeenCalledTimes(SERVE_BUDGET.attempts);  // 2, not 3
  });

  it('passes the serve per-attempt timeout, not REQUEST_TIMEOUT_MS', async () => {
    const generateContent = jest.fn(async (_p: unknown, o: { timeout?: number }) => {
      expect(o.timeout).toBe(SERVE_BUDGET.attemptTimeoutMs);   // 50_000
      return okResponse();
    });
    mockModel({ generateContent });
    await generateMagazineModelForServe([{ title: 'A', prose: 'x' }], 'en', SERVE_BUDGET, { caps: TEST_CAPS });
    expect(generateContent).toHaveBeenCalled();
  });

  // The regression this whole task exists to prevent — and it is SILENT without this test.
  it('leaves the LOCAL path on 3 attempts at REQUEST_TIMEOUT_MS', async () => {
    const generateContent = jest.fn(async (_p: unknown, o: { timeout?: number }) => {
      expect(o.timeout).toBe(60_000);
      throw new Error('boom');
    });
    mockModel({ generateContent });
    await expect(generateMagazineModel(
      [{ title: 'A', prose: 'x' }], 'en', {},          // no budget — the local call shape
    )).rejects.toThrow();
    expect(generateContent).toHaveBeenCalledTimes(3);  // GENERATE_JSON_RETRIES + 1
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest gemini-serve-budget -v`
Expected: FAIL — `generateMagazineModelForServe is not a function`.

- [ ] **Step 3: Write minimal implementation**

```ts
// lib/gemini.ts — generateJson gains a timeout override (optional here: its default IS the
// existing behaviour for every existing caller)
export async function generateJson<T>(
  model: GenerativeModel,
  prompt: string,
  schema: { parse: (x: unknown) => T },
  label: string,
  retries = GENERATE_JSON_RETRIES,
  baseDelayMs = 400,
  opts?: { signal?: AbortSignal; billing?: BillingLatch },
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
  // ... unchanged loop, except:
  //   const result = await model.generateContent(prompt, { timeout: timeoutMs, signal: opts?.signal });
}
```

```ts
// lib/gemini.ts — the serve boundary. `budget` is REQUIRED and positional: omitting it
// cannot compile, which is the entire point (round-6 H1).
export async function generateMagazineModelForServe(
  sections: Array<{ title: string; prose: string }>,
  language: 'en' | 'ko',
  budget: ServeBudget,
  opts?: { caps?: CloudGeminiCaps; signal?: AbortSignal; billing?: BillingLatch },
): Promise<MagazineModel> {
  return generateMagazineModel(sections, language, opts, budget);
}
```

```ts
// lib/gemini.ts — generateMagazineModel gains an internal 4th param. NOT exported as the
// serve entry point; the local caller (html-doc/generate.ts:40) omits it and is unchanged.
export async function generateMagazineModel(
  sections: Array<{ title: string; prose: string }>,
  language: 'en' | 'ko',
  opts?: { caps?: CloudGeminiCaps; signal?: AbortSignal; billing?: BillingLatch },
  budget?: ServeBudget,
): Promise<MagazineModel> {
  // ... unchanged until the try block:
  try {
    if (caps) {
      await assertMagazineInputWithinCap(model, prompt, generationConfig, caps, {
        signal: opts?.signal,
        ...(budget ? { timeoutMs: budget.countTokensTimeoutMs } : {}),
      });
    }
    const parsed = await generateJson(
      model, prompt, MagazineModelSchema, 'magazine',
      budget ? budget.attempts - 1 : undefined,   // `retries`, so attempts - 1
      undefined,
      opts,
      budget ? budget.attemptTimeoutMs : undefined,
    );
    // ... unchanged
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest gemini-serve-budget gemini -v`
Expected: PASS, all three, including the local-path guard.

- [ ] **Step 5: Mutation-check the boundary**

Temporarily change `generateMagazineModelForServe` to drop the budget (`return generateMagazineModel(sections, language, opts)`).
Run: `npx jest gemini-serve-budget -v`
Expected: RED on both serve tests. Restore.

- [ ] **Step 6: Commit**

```bash
git add lib/gemini.ts tests/lib/gemini-serve-budget.test.ts
git commit -m "feat(#46): a serve entry point whose budget cannot be forgotten

An optional opts.serve? would compile at the serve call site unchanged and run
3x60s while the lease floor assumes 2x50s — wrong in the one configuration
nobody tests. Required and positional, so omission is a compile error."
```

---

### Task 4: Bound the model upload

**Files:**
- Modify: `lib/html-doc/model-store.ts:45-52`
- Test: `tests/lib/html-doc/model-store.test.ts` (exists — extend)

**Interfaces:**
- Consumes: `SERVE_PUT_TIMEOUT_MS` (Task 1, via the caller).
- Produces: `writeModelEnvelopeWithin(timeoutMs: number, principal, base, envelope, blobStore?): Promise<void>`.

**What this does NOT do:** it does not cancel the upload. `SupabaseBlobStore.put` maps to Storage `upload(..., {upsert:true})` with no signal (`lib/storage/supabase/supabase-blob-store.ts:22-24`). The race bounds our **wait**. The spec's §3.5 residual — a late upload overwriting a newer model — follows from that and is **accepted**; do not try to fix it here.

- [ ] **Step 1: Write the failing test**

**Use the fixtures this file already has.** `[VERIFIED: tests/lib/html-doc/model-store.test.ts:12]`
it defines `ENVELOPE`, `principal`, `BASE` and `fakeBlobStore` — an earlier draft invented
`validEnvelope` and `stubStore`, which do not exist (plan-review r1 Medium).

`fakeBlobStore` is **local to one existing test**, not a shared fixture (plan-review r2 Medium — my
`[VERIFIED]` tag on it was wrong). Build one the same way that test does
(`tests/lib/html-doc/model-store.test.ts:84`), preserving `localBlobStore`'s prototype:

```ts
// tests/lib/html-doc/model-store.test.ts — add, reusing ENVELOPE / principal / BASE
const storeWith = (put: BlobStore['put']) =>
  Object.assign(Object.create(Object.getPrototypeOf(localBlobStore)), localBlobStore, { put }) as typeof localBlobStore;

it('rejects with TimeoutError when the put exceeds the budget', async () => {
  const hanging = storeWith(() => new Promise<void>(() => {}));
  await expect(
    writeModelEnvelopeWithin(20, principal, BASE, ENVELOPE, hanging),
  ).rejects.toMatchObject({ name: 'TimeoutError' });   // identity, not "any error"
});

it('resolves normally when the put completes within the budget', async () => {
  const put = jest.fn(async () => {});
  await writeModelEnvelopeWithin(5_000, principal, BASE, ENVELOPE, storeWith(put));
  expect(put).toHaveBeenCalledTimes(1);
});

it('validates the envelope BEFORE writing', async () => {
  const put = jest.fn(async () => {});
  await expect(
    writeModelEnvelopeWithin(5_000, principal, BASE, { ...ENVELOPE, sourceMd: '' } as never, storeWith(put)),
  ).rejects.toThrow();
  expect(put).not.toHaveBeenCalled();   // fail loud before any write, as writeModelEnvelope does
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest model-store -v`
Expected: FAIL — `writeModelEnvelopeWithin is not a function`.

- [ ] **Step 3: Write minimal implementation**

```ts
// lib/html-doc/model-store.ts
/**
 * writeModelEnvelope with a bounded WAIT.
 *
 * This does NOT cancel the upload — SupabaseBlobStore.put has no signal. A put that times out
 * here may still land later and overwrite a newer model. That residual is ACCEPTED and its fix
 * belongs to the render-addressing slice (backlog #25 / task #39). See the spec §3.5.1.
 *
 * `timeoutMs` is REQUIRED: an optional one would let the serve caller silently restore the
 * unbounded await this task exists to remove.
 */
export async function writeModelEnvelopeWithin(
  timeoutMs: number,
  principal: Principal,
  base: string,
  envelope: ModelEnvelope,
  blobStore: BlobStore = localBlobStore,
): Promise<void> {
  const bytes = serialize(envelope);          // validates first — fail loud before any write
  let timer: ReturnType<typeof setTimeout> | undefined;
  const expiry = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(
      () => reject(new DOMException(`model put exceeded ${timeoutMs}ms`, 'TimeoutError')),
      timeoutMs,
    );
  });
  try {
    await Promise.race([
      blobStore.put(principal, MODEL_KEY(base), bytes, 'application/json'),
      expiry,
    ]);
  } finally {
    if (timer) clearTimeout(timer);           // else the timer holds the event loop open
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest model-store -v`
Expected: PASS (3 new + existing).

- [ ] **Step 5: Commit**

```bash
git add lib/html-doc/model-store.ts tests/lib/html-doc/model-store.test.ts
git commit -m "feat(#46): bound the model upload's WAIT, and say that it is only the wait

Supabase upload takes no signal, so the race cannot cancel it. The late-write
residual that follows is accepted and routed to the addressing slice."
```

---

### Task 5: A bounded-RPC seam that does not depend on how the client reports aborts

**Files:**
- Create: `lib/serve-rpc.ts`
- Create: `tests/lib/serve-rpc.test.ts`
- Create: `tests/support/fake-rpc.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `RpcOutcome<T>`, `callRpcBounded(make, timeoutMs, label)`, and the test helper `fakeRpcBuilder(result)`.

**Why this task exists (plan-review r1 Blocking).** The first draft of this plan wrapped
`supabaseClient.rpc(...).abortSignal(...)` in a `try/catch`. That is wrong:
`[VERIFIED: node_modules/@supabase/postgrest-js/dist/index.mjs:145, :326, :345-362]` —
`shouldThrowOnError` is `false` by default, and an aborted fetch is **caught and returned** as
`{ error }`, never thrown. So the `catch` would be dead code, and `settleBounded` would return
`true` for a settle that never happened — reporting a refund it did not apply.

There is a second trap underneath: `AbortSignal.timeout()` aborts with a **`TimeoutError`**, while
postgrest's abort branch (`:345`) tests for `AbortError` / `ABORT_ERR`. Our own timeouts would not
even match its abort special-case.

**So this seam never inspects the client's error shape.** It races its own timer, and returns an
honest union — the same `{ ok: false; reason }` idiom the codebase already uses for `BlobRead`
(`lib/storage/blob-store.ts:10-13`), for the same reason: a caller must not be able to confuse
"timed out" with "the RPC returned an error".

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/serve-rpc.test.ts
import { callRpcBounded } from '@/lib/serve-rpc';
import { fakeRpcBuilder } from '../support/fake-rpc';

describe('callRpcBounded', () => {
  it('returns ok with the data when the call settles in time', async () => {
    const out = await callRpcBounded(
      (s) => fakeRpcBuilder({ data: [{ status: 'reserved' }], error: null }).abortSignal(s),
      1_000, 'reserve');
    expect(out).toEqual({ ok: true, data: [{ status: 'reserved' }] });
  });

  // The case the first plan draft got wrong: postgrest RETURNS the abort, it does not throw.
  it('reports timeout when the call outlives the budget, even though the client never throws', async () => {
    const out = await callRpcBounded(
      (s) => fakeRpcBuilder(() => new Promise(() => {})).abortSignal(s),
      20, 'settle');
    expect(out).toEqual({ ok: false, reason: 'timeout' });
  });

  it('distinguishes a returned RPC error from a timeout', async () => {
    const cause = { message: 'boom', code: 'P0001' };
    const out = await callRpcBounded(
      (s) => fakeRpcBuilder({ data: null, error: cause }).abortSignal(s), 1_000, 'reserve');
    expect(out).toEqual({ ok: false, reason: 'error', cause });
  });

  it('aborts the underlying request on timeout so it does not leak', async () => {
    let seen: AbortSignal | undefined;
    await callRpcBounded((s) => { seen = s; return fakeRpcBuilder(() => new Promise(() => {})).abortSignal(s); },
      20, 'settle');
    expect(seen!.aborted).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest serve-rpc -v`
Expected: FAIL — `Cannot find module '@/lib/serve-rpc'`.

- [ ] **Step 3: Write the implementation and the shared fake**

```ts
// lib/serve-rpc.ts
/**
 * A Supabase RPC call with a bounded WAIT and an honest outcome.
 *
 * Deliberately does NOT inspect postgrest's error shape to detect a timeout. With
 * shouldThrowOnError=false (its default) an aborted fetch is returned as `{ error }`, and our
 * AbortSignal.timeout produces a TimeoutError that postgrest's own abort branch does not
 * special-case. Racing our own timer keeps the outcome ours.
 *
 * The union mirrors BlobRead (lib/storage/blob-store.ts:10-13): a caller must not be able to
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
    // throw or a rejected builder must not escape as an exception, or Task 6's `!ok` callers miss
    // it entirely (plan-review r2 High).
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
```

```ts
// tests/support/fake-rpc.ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest serve-rpc -v`
Expected: PASS (4).

- [ ] **Step 5: Mutation-check the timeout branch**

Delete the `expiry` entry from the `Promise.race` array.
Run: `npx jest serve-rpc -v` → Expected: RED (the timeout test hangs to jest's own timeout). Restore.

- [ ] **Step 6: Commit**

```bash
git add lib/serve-rpc.ts tests/lib/serve-rpc.test.ts tests/support/fake-rpc.ts
git commit -m "feat(#46): a bounded RPC seam that owns its own timeout verdict

postgrest returns aborts as {error} rather than throwing, and our
AbortSignal.timeout produces a TimeoutError its abort branch does not match.
Racing our own timer makes the outcome independent of both."
```

---

### Task 6: Wire the serve path — both RPCs, the refund retry, the two wrappers

**Files:**
- Modify: `lib/html-doc/serve-doc.ts:20` (export `SERVE_CAPS`), `:74-77` (reserve), `:112-125` (wrappers), `:126`, `:133` (settle)
- Modify: `tests/lib/html-doc/serve-doc-mapping.test.ts:30-33` — **`fakeSupabase` must return a chainable builder**
- Test: `tests/integration/serve-doc-materialize.test.ts` (exists — extend)

**Interfaces:**
- Consumes: `SERVE_BUDGET`, `SERVE_*_TIMEOUT_MS` (Task 1); `generateMagazineModelForServe` (Task 3); `writeModelEnvelopeWithin` (Task 4); `callRpcBounded` (Task 5); `fakeRpcBuilder` (Task 5).
- Produces: `SERVE_CAPS` becomes an export (Task 3's tests need it). `ResolveResult` is **unchanged** — a reserve timeout maps onto the existing `busy`.

**Existing fakes break without this task's edit (plan-review r1 Blocking).**
`[VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:30-33]` `fakeSupabase` returns
`rpc: jest.fn(async () => ({ data, error }))` — a bare promise with no `.abortSignal`. Once
production chains `.abortSignal(...)`, every one of those tests throws `TypeError`. Upgrading them
is part of this task, not a follow-up.

- [ ] **Step 1: Upgrade the existing seam fake FIRST, and watch the suite stay green**

```ts
// tests/lib/html-doc/serve-doc-mapping.test.ts — replace fakeSupabase
import { fakeRpcBuilder } from '../../support/fake-rpc';

function fakeSupabase(rpcData: string): SupabaseClient {
  return {
    rpc: jest.fn(() => fakeRpcBuilder({ data: [{ status: rpcData, release_token: null }], error: null })),
  } as unknown as SupabaseClient;
}
```

Run: `npx jest serve-doc-mapping -v`
Expected: PASS — a thenable still awaits identically, so this is green *before* production changes.
Doing it first means a later failure is unambiguously the production change, not the fake.

- [ ] **Step 2: Extend BOTH Gemini module mocks (plan-review r2 Blocking)**

`[VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:14-18]` and
`[VERIFIED: tests/integration/serve-doc-materialize.test.ts:11-15]` both do
`jest.mock('@/lib/gemini', () => ({ generateMagazineModel: jest.fn(...) }))` — **only that symbol**.
The moment production calls `generateMagazineModelForServe`, both files get `undefined` from the mock
and fail with a TypeError. Add the wrapper to each factory, delegating so the existing assertions on
`generateMagazineModel` keep working:

```ts
jest.mock('@/lib/gemini', () => {
  const generateMagazineModel = jest.fn(async (sections: Array<{ title: string }>) => ({
    sections: sections.map(() => ({ lead: 'GEN', bullets: [
      { label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' },
    ] })),
  }));
  return {
    generateMagazineModel,
    // The serve wrapper delegates, so tests that assert on generateMagazineModel still see the call.
    generateMagazineModelForServe: jest.fn((sections, language, _budget, opts) =>
      generateMagazineModel(sections, language, opts)),
  };
});
import { generateMagazineModel, generateMagazineModelForServe } from '@/lib/gemini';
```

Run: `npx jest serve-doc-mapping -v` → still green (nothing calls the wrapper yet).

- [ ] **Step 3: Write the failing tests — in the UNIT file, not the integration file**

**Correcting the plan's earlier structure (plan-review r2 Blocking).** There is **no `runServe`
harness**; `[VERIFIED: tests/integration/serve-doc-materialize.test.ts:1-40]` that file calls
`resolveMagazineModel({...})` directly against **real seeded Supabase clients**. You cannot make a
real RPC time out on demand there. The timeout and retry tests belong in
`tests/lib/html-doc/serve-doc-mapping.test.ts`, whose `fakeSupabase` we control.

```ts
// tests/lib/html-doc/serve-doc-mapping.test.ts — add. `principal`, `parsed`, and the fake blob
// store already exist in this file (see its header); reuse them.
import { fakeRpcBuilder } from '../../support/fake-rpc';

/** A fake whose reserve/settle behaviour is scripted per RPC name. */
function scriptedSupabase(script: (fn: string) => ReturnType<typeof fakeRpcBuilder>): SupabaseClient {
  return { rpc: jest.fn((fn: string) => script(fn)) } as unknown as SupabaseClient;
}
const reserved = () =>
  fakeRpcBuilder({ data: [{ status: 'reserved', release_token: 'tok' }], error: null });

it('a reserve TIMEOUT returns busy and makes no Gemini call', async () => {
  const client = scriptedSupabase(() => fakeRpcBuilder(() => new Promise(() => {})));
  const res = await resolveMagazineModel({ supabaseClient: client, /* …existing args… */ });
  expect(res.status).toBe('busy');
  // The empty-paid-lease state: charged, an attempt burned, and NO producer.
  expect(generateMagazineModelForServe).not.toHaveBeenCalled();
});

it('a reserve ERROR still throws, exactly as today', async () => {
  const client = scriptedSupabase(() => fakeRpcBuilder({ data: null, error: { message: 'nope' } }));
  await expect(resolveMagazineModel({ supabaseClient: client, /* … */ }))
    .rejects.toMatchObject({ message: 'nope' });
});

it('retries the settle ONCE when the release-path settle times out', async () => {
  let settles = 0;
  const client = scriptedSupabase((fn) => {
    if (fn === 'reserve_serve_model') return reserved();
    settles++;
    return settles === 1 ? fakeRpcBuilder(() => new Promise(() => {}))
                         : fakeRpcBuilder({ data: true, error: null });
  });
  (generateMagazineModelForServe as jest.Mock).mockImplementationOnce(async () => {
    throw new GoogleGenerativeAIFetchError('overloaded', 503, 'Service Unavailable');
  });
  process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';   // else releaseGateOpen() is false
  await expect(resolveMagazineModel({ supabaseClient: client, /* … */ })).rejects.toThrow();
  expect(settles).toBe(2);
});

it('does NOT retry the settle on the kept path', async () => {
  let settles = 0;
  const client = scriptedSupabase((fn) => {
    if (fn === 'reserve_serve_model') return reserved();
    settles++;
    return fakeRpcBuilder(() => new Promise(() => {}));   // hangs every time
  });
  await resolveMagazineModel({ supabaseClient: client, /* … */ });   // success -> released=false
  expect(settles).toBe(1);   // a lost keep is benign; only a lost refund is money
});
```

**The 429-refund regression pin already exists — do not write a new one.**
`[VERIFIED: tests/integration/serve-doc-materialize.test.ts:278-303]` *"serve class-A throw refunds
both ledgers (gate on, not metered)"* asserts both ledgers return to 0 against a **real** database. It
sets `CLOUD_GEMINI_RELEASE_VERIFIED = 'true'` and throws `GoogleGenerativeAIFetchError(503)` — note
both details; an earlier draft of this plan used a nonexistent `GeminiHttpError` and omitted the gate,
so it would have asserted a refund that `releaseGateOpen()` forbids. **That existing test passing
unchanged is this task's acceptance criterion for the money rule.**

- [ ] **Step 3: Run tests to verify they fail**

Run: `npx jest tests/integration/serve-doc-materialize -v`
Expected: FAIL — no retry (one settle), and the reserve timeout hangs rather than returning `busy`.

- [ ] **Step 4: Write the implementation**

```ts
// lib/html-doc/serve-doc.ts:20 — SERVE_CAPS becomes an export (Task 3's tests import it)
export const SERVE_CAPS: CloudGeminiCaps = { /* unchanged */ };
```

```ts
// lib/html-doc/serve-doc.ts — reserve
const reserve = await callRpcBounded(
  (signal) => supabaseClient
    .rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId })
    .abortSignal(signal),
  SERVE_RESERVE_RPC_TIMEOUT_MS, 'reserve_serve_model',
);
if (!reserve.ok) {
  if (reserve.reason === 'error') throw reserve.cause;   // unchanged from `if (error) throw error`
  // TIMEOUT. The transaction is NOT rolled back, so what may exist now is an EMPTY PAID LEASE:
  // charged, an attempt burned, no producer. Retries before expiry see in_flight although nobody
  // is generating. Loud, because that is an infrastructure alarm, not a user error.
  console.error('[serve-model] reserve timed out — possible empty paid lease');
  return { status: 'busy' };
}
const row = (reserve.data as Array<{ status: string; release_token: string | null }> | null)?.[0];
```

```ts
// lib/html-doc/serve-doc.ts — the two wrappers, inside the existing try
const model = await generateMagazineModelForServe(
  parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
  language,
  SERVE_BUDGET,                                   // REQUIRED — cannot be omitted
  { caps: SERVE_CAPS, signal, billing },
);
await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, { /* unchanged fields */ }, blobStore);
```

```ts
// lib/html-doc/serve-doc.ts — settle. Replaces BOTH call sites (:126 and :133).
async function settleBounded(
  supabaseClient: SupabaseClient, token: string, released: boolean,
): Promise<boolean> {
  // An unapplied REFUND is real money left on the ledger; a lost KEEP is already correct.
  const attempts = released ? 2 : 1;
  for (let i = 0; i < attempts; i++) {
    const out = await callRpcBounded(
      (signal) => supabaseClient
        .rpc('settle_serve_model', { p_token: token, p_released: released })
        .abortSignal(signal),
      SERVE_SETTLE_RPC_TIMEOUT_MS, `settle_serve_model(released=${released})`,
    );
    if (out.ok) return true;
    console.warn(`[serve-model] settle attempt ${i + 1}/${attempts} failed: ${out.reason}`);
  }
  return false;   // caller must NOT claim a refund it could not apply
}
```

The two call sites keep their existing `if (releaseToken)` guard and the existing `released`
computation at `:130-132` — **do not touch that expression**; it is the refund rule.

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx jest tests/integration/serve-doc-materialize serve-doc-mapping -v`
Expected: PASS — 5 new, plus the pre-existing refund and mapping tests.

- [ ] **Step 6: Mutation-check the retry and the timeout branch**

1. `const attempts = 1;` unconditionally → the retry test must go RED. Restore.
2. Change the reserve timeout branch to `throw new Error('x')` → the `busy` test must go RED. Restore.

- [ ] **Step 7: Full suite + typecheck**

Run: `npx tsc --noEmit && npm test`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add lib/html-doc/serve-doc.ts tests/integration/serve-doc-materialize.test.ts tests/lib/html-doc/serve-doc-mapping.test.ts
git commit -m "feat(#46): bound both RPCs; retry the refund; name the empty-paid-lease state

Bounding the settle is not free: on the release path a timeout leaves the
refund unapplied, so it retries once and never reports a refund it could not
apply. A rule can be preserved verbatim and still stop working when you bound
the mechanism that carries it out."
```

---

### Task 7: The CHECK floor and its anti-drift pin

**Files:**
- Create: `supabase/migrations/0024_lease_covers_serve.sql`
- Test: `tests/integration/serve-config-invariant.test.ts` (exists — extend)

**Interfaces:**
- Consumes: `SERVE_FLOOR_SECONDS` (Task 1) = **156**.
- Produces: constraint `guardrail_config_lease_ttl_covers_serve`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/serve-config-invariant.test.ts — add
import { readFileSync } from 'node:fs';
import { SERVE_FLOOR_SECONDS } from '@/lib/serve-budget';

// This file uses `svc`, not `admin` (plan-review r2 High), and its header warns that the whole
// integration suite shares ONE guardrail_config row and other files mutate it. So: read the current
// value, and restore THAT — never hardcode 180, which would be the tautology this file exists to
// avoid.
it('refuses a lease shorter than the serve path can finish in', async () => {
  const { error } = await svc.from('guardrail_config')
    .update({ lease_ttl_seconds: 30 }).eq('id', true);
  expect(error).toMatchObject({ code: '23514' });        // check_violation
});

it('accepts exactly the floor, then restores whatever was there', async () => {
  const { data: before } = await svc.from('guardrail_config')
    .select('lease_ttl_seconds').eq('id', true).single();
  expect((await svc.from('guardrail_config')
    .update({ lease_ttl_seconds: SERVE_FLOOR_SECONDS }).eq('id', true)).error).toBeNull();
  expect((await svc.from('guardrail_config')
    .update({ lease_ttl_seconds: before!.lease_ttl_seconds }).eq('id', true)).error).toBeNull();
});

// A migration literal cannot import a TypeScript constant, so this is the ONLY thing between a
// tuned constant and a floor that no longer covers the work.
it('the migration literal equals SERVE_FLOOR_SECONDS', () => {
  const sql = readFileSync('supabase/migrations/0024_lease_covers_serve.sql', 'utf-8');
  const m = sql.match(/lease_ttl_seconds\s*>=\s*(\d+)\s*\)/);
  expect(m).not.toBeNull();
  expect(Number(m![1])).toBe(SERVE_FLOOR_SECONDS);
});
```

`svc` is the service-role client this file already builds (`serve-config-invariant.test.ts:3`) — reuse it.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest tests/integration/serve-config-invariant -v`
Expected: FAIL — `30` is accepted (today's floor is `>= 1`) and the migration file is absent.

- [ ] **Step 3: Write the migration**

```sql
-- supabase/migrations/0024_lease_covers_serve.sql
-- The serve path's bounded work is a static sum (lib/serve-budget.ts). This constraint makes
-- "the work fits the lease" true at CONFIGURATION time, once, for every request forever —
-- rather than negotiated per request. See the spec §3.3.
--
-- 156 = SERVE_FLOOR_SECONDS = ceil((135_400 enforced + 20_000 margin) / 1000).
-- Pinned by tests/integration/serve-config-invariant.test.ts — a literal here cannot import it.
--
-- The old floor was `>= 1`: a one-second lease was legal, which is why the app could never
-- assume the lease covered its work.

do $$
declare
  v_name text;
  v_count int;
begin
  -- Drop EVERY check constraint mentioning lease_ttl_seconds, not just the first. An earlier
  -- draft used `select conname into v_name`, which silently takes one row and would raise
  -- TOO_MANY_ROWS on a partially-applied schema (plan-review r1 Medium).
  select count(*) into v_count from pg_constraint
   where conrelid = 'guardrail_config'::regclass and contype = 'c'
     and pg_get_constraintdef(oid) ilike '%lease_ttl_seconds%';
  if v_count > 1 then
    raise warning 'dropping % pre-existing lease_ttl_seconds check constraints', v_count;
  end if;
  for v_name in
    select conname from pg_constraint
     where conrelid = 'guardrail_config'::regclass and contype = 'c'
       and pg_get_constraintdef(oid) ilike '%lease_ttl_seconds%'
  loop
    execute format('alter table guardrail_config drop constraint %I', v_name);
  end loop;
end $$;

-- Idempotent: the loop above removes our own constraint if the migration is re-applied.
alter table guardrail_config
  add constraint guardrail_config_lease_ttl_covers_serve check (lease_ttl_seconds >= 156);
```

- [ ] **Step 4: Apply and run tests**

Run: `npx supabase db reset && npx jest tests/integration/serve-config-invariant -v`
Expected: PASS (3).

**Ordering note:** `db reset` wipes data other integration tests seed. Run this task's tests
immediately after the reset, then re-run the full integration suite in Step 6 rather than assuming
earlier state survived.

- [ ] **Step 5: Mutation-check the constraint**

Change `>= 156` to `>= 1`, re-apply, re-run → the "refuses a lease shorter" test must go RED.
Restore and re-apply.

- [ ] **Step 6: Schema gates + full integration suite**

Run: `./scripts/check-schema-gates.sh && npm run test:integration`
Expected: six gates green; integration suite green (run it twice without a reset — a suite green
only on its first run counts as red, `process-checklists.md:139-144`).

- [ ] **Step 7: Commit**

```bash
git add supabase/migrations/0024_lease_covers_serve.sql tests/integration/serve-config-invariant.test.ts
git commit -m "feat(#46): the DB refuses a lease it cannot cover

One line replaces the six mechanisms three review rounds spent negotiating the
same fact per request. The old floor was >= 1."
```

---

### Task 8: Pin the accepted residual

**Files:**
- Create: `tests/lib/html-doc/read-model.test.ts` (if absent — check first)

**Interfaces:** consumes nothing; produces nothing. A characterisation test only.

**Why:** §3.5.1 accepts that a late `put` can overwrite a newer model and be served indefinitely,
because `isFresh` (`lib/html-doc/read-model.ts:20-24`) compares titles and `generatorVersion` but
**not** `sourceMdHash`. A residual with no test is indistinguishable from an oversight.

- [ ] **Step 1: Write the characterisation test**

```ts
// tests/lib/html-doc/read-model.test.ts
import { isFresh } from '@/lib/html-doc/read-model';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';

describe('isFresh — KNOWN GAP, accepted in the serve-bounding spec §3.5.1', () => {
  it('treats an envelope with a STALE sourceMdHash as fresh when titles match', () => {
    const stale = {
      sourceSections: ['A', 'B'],
      generatorVersion: GENERATOR_VERSION,
      sourceMdHash: 'hash-of-OLD-markdown',
    };
    // The accepted residual: a late put that overwrites a newer model is served indefinitely
    // when the section titles did not change (the common case for a prose-only edit). The fix
    // is content addressing — backlog #25 / task #39 — NOT a change here.
    //
    // WHEN THIS GOES RED: someone made isFresh hash-aware. That is a MONEY decision (prose-only
    // edits would then force paid regeneration), so read the spec's §3.5.1 before deleting it.
    expect(isFresh(stale, ['A', 'B'])).toBe(true);
  });

  it('detects drift when a title changes', () => {
    expect(isFresh({ sourceSections: ['A', 'B'], generatorVersion: GENERATOR_VERSION },
      ['A', 'CHANGED'])).toBe(false);
  });

  it('detects a generator-version bump', () => {
    expect(isFresh({ sourceSections: ['A'], generatorVersion: 'v-old' }, ['A'])).toBe(false);
  });
});
```

- [ ] **Step 2: Run the test**

Run: `npx jest read-model -v`
Expected: PASS immediately — this characterises existing behaviour. **If test 1 fails, `isFresh`
already reads the hash and §3.5.1's premise is wrong: stop and re-read the spec.**

- [ ] **Step 3: Commit**

```bash
git add tests/lib/html-doc/read-model.test.ts
git commit -m "test(#46): pin the accepted late-write residual so it cannot be mistaken for an oversight

isFresh compares titles and generatorVersion, never sourceMdHash. Accepted by
decision; the fix is content addressing (backlog #25). This test goes red the
day someone changes that, with the reasoning attached."
```

---

## Final verification (before the PR)

- [ ] `npx tsc --noEmit` — clean
- [ ] `npm test` — full unit suite green
- [ ] `npm run test:integration` — needs a live Supabase stack (not in CI; `dev-process.md:142`)
- [ ] `./scripts/check-schema-gates.sh` — all six
- [ ] `python3 scripts/check-docs.py`
- [ ] **Deploy precondition (§6):** read `lease_ttl_seconds` in every environment. If any is below **156**, raise it *before* 0024 is applied or the migration fails on a live database. `[unverified]` — production's value has not been read this session, and per the compaction memory note the doc is not evidence.
- [ ] Whole-branch dual adversarial review (Codex + Claude) to convergence
- [ ] Open the PR, notify, **do not merge** — merging is a human gate

## Spec coverage self-review

| Spec section | Task |
|---|---|
| §3.1 bound `countTokens` | 2 |
| §3.1 bound `generateContent` / attempts | 3 |
| §3.1 bound `put` | 4 |
| §3.1 bound reserve + settle RPCs | 5, 6 |
| §3.1 required-parameter serve wrapper | 3 |
| §3.2 the budget constants and their sum | 1 |
| §3.3 the CHECK floor + anti-drift pin | 7 |
| §3.5.1 accepted residual | 8 |
| §4.1 settle retry on the release path | 6 |
| §4 reserve timeout → `busy`, empty paid lease | 6 |
| §5 every bounded term aborts | 2, 5, 6 — **Task 4 bounds the WAIT, not the upload** (§3.4); the plan does not claim otherwise |
| §5 refund decision AND outcome | 6 |
| §5 mutation coverage | 3, 5, 6, 7 |
| §6 deploy ordering | final verification |

No spec section is unclaimed.
