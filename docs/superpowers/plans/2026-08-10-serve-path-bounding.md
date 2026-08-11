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
| `lib/html-doc/serve-doc.ts` | calls the two wrappers; bounds both RPCs; retries settle once on the release path; maps a reserve timeout to `busy`. |
| `supabase/migrations/0024_lease_covers_serve.sql` | **new.** Raises the `lease_ttl_seconds` CHECK floor to `SERVE_FLOOR_SECONDS`. |
| `tests/lib/serve-budget.test.ts` | **new.** The sum, the bounds, the unit discipline. |
| `tests/lib/gemini-serve-budget.test.ts` | **new.** Wrapper behaviour + local path unaffected. |
| `tests/lib/html-doc/model-store.test.ts` | extend — the put race. |
| `tests/integration/serve-config-invariant.test.ts` | extend — the CHECK floor, plus its mutation. |
| `tests/integration/serve-doc-materialize.test.ts` | extend — refund survives, reserve timeout, settle retry. |

**Task order:** 1 → 2 → 3 → 4 → 5 → 6 → 7. Task 1 is a hard dependency for 5 and 6.

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

```ts
// tests/lib/gemini-serve-budget.test.ts
import { SERVE_BUDGET } from '@/lib/serve-budget';

jest.mock('@google/generative-ai');

describe('generateMagazineModelForServe', () => {
  it('makes at most SERVE_BUDGET.attempts generateContent calls', async () => {
    const generateContent = jest.fn(async () => { throw new Error('boom'); });
    mockModel({ generateContent });
    await expect(generateMagazineModelForServe(
      [{ title: 'A', prose: 'x' }], 'en', SERVE_BUDGET, { caps: SERVE_CAPS },
    )).rejects.toThrow();
    expect(generateContent).toHaveBeenCalledTimes(SERVE_BUDGET.attempts);  // 2, not 3
  });

  it('passes the serve per-attempt timeout, not REQUEST_TIMEOUT_MS', async () => {
    const generateContent = jest.fn(async (_p: unknown, o: { timeout?: number }) => {
      expect(o.timeout).toBe(SERVE_BUDGET.attemptTimeoutMs);   // 50_000
      return okResponse();
    });
    mockModel({ generateContent });
    await generateMagazineModelForServe([{ title: 'A', prose: 'x' }], 'en', SERVE_BUDGET, { caps: SERVE_CAPS });
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

```ts
// tests/lib/html-doc/model-store.test.ts — add
it('rejects when the put exceeds the timeout', async () => {
  const hanging: BlobStore = { ...stubStore, put: () => new Promise<void>(() => {}) } as never;
  await expect(
    writeModelEnvelopeWithin(20, principal, 'base', validEnvelope, hanging),
  ).rejects.toMatchObject({ name: 'TimeoutError' });   // identity, not "any error"
});

it('resolves normally when the put completes within the timeout', async () => {
  const put = jest.fn(async () => {});
  await writeModelEnvelopeWithin(5_000, principal, 'base', validEnvelope, { ...stubStore, put } as never);
  expect(put).toHaveBeenCalledTimes(1);
});

it('still validates the envelope before writing', async () => {
  const put = jest.fn(async () => {});
  await expect(
    writeModelEnvelopeWithin(5_000, principal, 'base', { ...validEnvelope, sourceMd: '' } as never,
      { ...stubStore, put } as never),
  ).rejects.toThrow();
  expect(put).not.toHaveBeenCalled();   // fail loud BEFORE the write, as writeModelEnvelope does
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

### Task 5: Bound both RPCs, retry the refund, wire the wrappers

**Files:**
- Modify: `lib/html-doc/serve-doc.ts:74-77` (reserve), `:112-125` (the two wrappers), `:126`, `:133` (settle)
- Test: `tests/integration/serve-doc-materialize.test.ts` (exists — extend)

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: no new exports; `resolveMagazineModel`'s existing return union is unchanged (a reserve timeout maps onto the existing `busy`).

**The constraint that governs this task:** the refund at `:130-132` must keep working. A settle that times out on the **release** path leaves the refund unapplied — an over-count. Retry once; do not silently report success.

- [ ] **Step 1: Write the failing tests**

```ts
// tests/integration/serve-doc-materialize.test.ts — add

it('a not-metered 429 still refunds (the rule two spec versions broke)', async () => {
  const settle = jest.fn(async () => ({ data: true, error: null }));
  await runServeWithGeminiFailure(new GeminiHttpError(429), { settle });
  expect(settle).toHaveBeenCalledWith('settle_serve_model',
    expect.objectContaining({ p_released: true }));
});

it('retries the settle ONCE when the release-path settle times out', async () => {
  let calls = 0;
  const settle = jest.fn(async () => {
    calls++;
    if (calls === 1) throw new DOMException('timeout', 'TimeoutError');
    return { data: true, error: null };
  });
  await runServeWithGeminiFailure(new GeminiHttpError(429), { settle });
  expect(calls).toBe(2);
});

it('keeps the charge (over-count) when BOTH release settles fail', async () => {
  const settle = jest.fn(async () => { throw new DOMException('timeout', 'TimeoutError'); });
  const res = await runServeWithGeminiFailure(new GeminiHttpError(429), { settle });
  expect(settle).toHaveBeenCalledTimes(2);
  expect(res.refundConfirmed).toBe(false);   // must NOT report a refund it could not apply
});

it('a reserve timeout returns busy and makes no Gemini call', async () => {
  const generateContent = jest.fn();
  const rpc = jest.fn(async () => { throw new DOMException('timeout', 'TimeoutError'); });
  const res = await runServe({ rpc, generateContent });
  expect(res.status).toBe('busy');
  expect(generateContent).not.toHaveBeenCalled();   // the empty-paid-lease state: charged, no producer
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest tests/integration/serve-doc-materialize -v`
Expected: FAIL — no retry (settle called once), and the reserve timeout propagates instead of returning `busy`.

- [ ] **Step 3: Write minimal implementation**

```ts
// lib/html-doc/serve-doc.ts — reserve, bounded
let reserved;
try {
  reserved = await supabaseClient
    .rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId })
    .abortSignal(AbortSignal.timeout(SERVE_RESERVE_RPC_TIMEOUT_MS));
} catch (err) {
  // A timeout does NOT roll the transaction back. What may exist now is an EMPTY PAID LEASE:
  // charged, an attempt burned, and no producer. Retries before expiry see in_flight although
  // nobody is generating. Loud, because that state is an infrastructure alarm, not a user error.
  console.error('[serve-model] reserve timed out — possible empty paid lease', err);
  return { status: 'busy' };
}
const { data, error } = reserved;
```

```ts
// lib/html-doc/serve-doc.ts — the two wrappers
const model = await generateMagazineModelForServe(
  parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
  language,
  SERVE_BUDGET,                                   // required — cannot be omitted
  { caps: SERVE_CAPS, signal, billing },
);
await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, { /* unchanged */ }, blobStore);
```

```ts
// lib/html-doc/serve-doc.ts — settle, bounded, retried once on the RELEASE path only
async function settleBounded(
  supabaseClient: SupabaseClient, token: string, released: boolean,
): Promise<boolean> {
  const attempts = released ? 2 : 1;   // an unapplied refund is real money; a lost keep is not
  for (let i = 0; i < attempts; i++) {
    try {
      await supabaseClient
        .rpc('settle_serve_model', { p_token: token, p_released: released })
        .abortSignal(AbortSignal.timeout(SERVE_SETTLE_RPC_TIMEOUT_MS));
      return true;
    } catch (err) {
      console.warn(`[serve-model] settle attempt ${i + 1}/${attempts} failed`, err);
    }
  }
  return false;   // caller must NOT claim a refund it could not apply
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest tests/integration/serve-doc-materialize -v`
Expected: PASS (4 new + existing refund tests).

- [ ] **Step 5: Mutation-check the retry**

Change `attempts` to `1` unconditionally.
Run: `npx jest tests/integration/serve-doc-materialize -v`
Expected: RED on the retry test. Restore.

- [ ] **Step 6: Full suite + typecheck**

Run: `npx tsc --noEmit && npm test`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add lib/html-doc/serve-doc.ts tests/integration/serve-doc-materialize.test.ts
git commit -m "feat(#46): bound both RPCs; retry the refund; name the empty-paid-lease state

Bounding the settle is not free: on the release path a timeout leaves the
refund unapplied, so it retries once and never reports a refund it could not
apply. A rule can be preserved verbatim and still stop working when you bound
the mechanism that carries it out."
```

---

### Task 6: The CHECK floor and its anti-drift pin

**Files:**
- Create: `supabase/migrations/0024_lease_covers_serve.sql`
- Test: `tests/integration/serve-config-invariant.test.ts` (exists — extend)

**Interfaces:**
- Consumes: `SERVE_FLOOR_SECONDS` (Task 1) = **156**.
- Produces: constraint `guardrail_config_lease_ttl_covers_serve`.

**Before writing the migration:** read the existing constraint's generated name — it is inline and unnamed at `0012:22`, so Postgres assigned it.

```sql
select conname from pg_constraint
 where conrelid = 'guardrail_config'::regclass and contype = 'c'
   and pg_get_constraintdef(oid) ilike '%lease_ttl_seconds%';
```

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/serve-config-invariant.test.ts — add
it('refuses a lease shorter than the serve path can finish in', async () => {
  await expect(
    admin.from('guardrail_config').update({ lease_ttl_seconds: 30 }).eq('id', true),
  ).resolves.toMatchObject({ error: expect.objectContaining({ code: '23514' }) });  // check_violation
});

it('accepts exactly the floor', async () => {
  const { error } = await admin.from('guardrail_config')
    .update({ lease_ttl_seconds: SERVE_FLOOR_SECONDS }).eq('id', true);
  expect(error).toBeNull();
  await admin.from('guardrail_config').update({ lease_ttl_seconds: 180 }).eq('id', true);  // restore
});

// A migration literal cannot import a TypeScript constant, so this assertion is the ONLY thing
// between a tuned constant and a floor that no longer covers the work.
it('the migration literal equals SERVE_FLOOR_SECONDS', () => {
  const sql = readFileSync('supabase/migrations/0024_lease_covers_serve.sql', 'utf-8');
  const m = sql.match(/lease_ttl_seconds\s*>=\s*(\d+)/);
  expect(m).not.toBeNull();
  expect(Number(m![1])).toBe(SERVE_FLOOR_SECONDS);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest tests/integration/serve-config-invariant -v`
Expected: FAIL — `lease_ttl_seconds = 30` is accepted (today's floor is 1), and the migration file does not exist.

- [ ] **Step 3: Write the migration**

```sql
-- supabase/migrations/0024_lease_covers_serve.sql
-- The serve path's bounded work is a static sum (lib/serve-budget.ts). This constraint makes the
-- inequality "the work fits the lease" true at CONFIGURATION time, once, for every request
-- forever — rather than discovered per request. See the spec §3.3.
--
-- 156 = SERVE_FLOOR_SECONDS = ceil((135_400 enforced + 20_000 margin) / 1000).
-- Pinned by tests/integration/serve-config-invariant.test.ts — a literal here cannot import it.
--
-- The old floor was `>= 1`: a one-second lease was legal, which is why the app could never assume
-- the lease covered its work.

do $$
declare v_name text;
begin
  select conname into v_name from pg_constraint
   where conrelid = 'guardrail_config'::regclass and contype = 'c'
     and pg_get_constraintdef(oid) ilike '%lease_ttl_seconds%';
  if v_name is not null then
    execute format('alter table guardrail_config drop constraint %I', v_name);
  end if;
end $$;

alter table guardrail_config
  add constraint guardrail_config_lease_ttl_covers_serve check (lease_ttl_seconds >= 156);
```

- [ ] **Step 4: Apply and run tests**

Run: `npx supabase db reset && npx jest tests/integration/serve-config-invariant -v`
Expected: PASS (3 new).

- [ ] **Step 5: Mutation-check the constraint**

Change `>= 156` to `>= 1`, re-apply, re-run.
Expected: RED on the "refuses a lease shorter" test. Restore and re-apply.

- [ ] **Step 6: Run the schema gates**

Run: `./scripts/check-schema-gates.sh`
Expected: all six green.

- [ ] **Step 7: Commit**

```bash
git add supabase/migrations/0024_lease_covers_serve.sql tests/integration/serve-config-invariant.test.ts
git commit -m "feat(#46): the DB refuses a lease it cannot cover

One line replaces the six mechanisms three review rounds spent negotiating the
same fact per request. The old floor was >= 1."
```

---

### Task 7: Pin the accepted residual

**Files:**
- Test: `tests/lib/html-doc/read-model.test.ts` (create if absent)

**Interfaces:** consumes nothing; produces nothing. This task adds only a characterisation test.

**Why this exists:** §3.5.1 accepts that a late `put` can overwrite a newer model and be served indefinitely, because `isFresh` (`lib/html-doc/read-model.ts:20-24`) compares titles and `generatorVersion` but **not** `sourceMdHash`. A residual with no test is indistinguishable from an oversight. This test documents the gap and goes **red** the day someone makes `isFresh` hash-aware — putting the spec's reasoning in front of them instead of making them rediscover it.

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
    // Documents the accepted residual: a late put that overwrites a newer model is served
    // indefinitely when the section titles did not change (the common case for a prose edit).
    // The fix is content addressing — backlog #25 / task #39 — NOT a change here.
    //
    // WHEN THIS GOES RED: someone made isFresh hash-aware. That is a MONEY decision (a
    // prose-only edit would then force a paid regeneration), so read the spec's §3.5.1 before
    // deleting this test.
    expect(isFresh(stale, ['A', 'B'])).toBe(true);
  });

  it('detects drift when a title changes', () => {
    const e = { sourceSections: ['A', 'B'], generatorVersion: GENERATOR_VERSION };
    expect(isFresh(e, ['A', 'CHANGED'])).toBe(false);
  });

  it('detects a generator-version bump', () => {
    const e = { sourceSections: ['A'], generatorVersion: 'v-old' };
    expect(isFresh(e, ['A'])).toBe(false);
  });
});
```

- [ ] **Step 2: Run the test**

Run: `npx jest read-model -v`
Expected: PASS immediately — this is a characterisation test of existing behaviour, not a change. If test 1 fails, `isFresh` already reads the hash and §3.5.1's premise is wrong: stop and re-read the spec.

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
| §3.1 bound reserve + settle RPCs | 5 |
| §3.1 required-parameter serve wrapper | 3 |
| §3.2 the budget constants and their sum | 1 |
| §3.3 the CHECK floor + anti-drift pin | 6 |
| §3.5.1 accepted residual | 7 |
| §4.1 settle retry on the release path | 5 |
| §4 reserve timeout → `busy`, empty paid lease | 5 |
| §5 every bounded term aborts | 2, 4, 5 |
| §5 refund decision AND outcome | 5 |
| §5 mutation coverage | 3, 5, 6 |
| §6 deploy ordering | final verification |

No spec section is unclaimed.
