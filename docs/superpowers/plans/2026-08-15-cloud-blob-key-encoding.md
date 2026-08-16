# Cloud Blob Key Encoding Implementation Plan (backlog #36)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a video with a title in any language be stored **and served** from the cloud, without changing vault filenames and without migrating anything already in the bucket.

**Architecture:** Two independent halves. (1) **The encoder** — `SupabaseBlobStore` maps a *logical* Unicode key to a *physical* ASCII one at the storage seam, so Storage's ASCII-only rule stops reaching the rest of the app. (2) **The servability guard** — one predicate, `isServableSummaryKey`, installed at points that *dominate* every writer rather than at a list of call sites: `videoDataPayload()` for cloud row writes, `serialize()` for model envelopes.

**Tech Stack:** TypeScript, Next.js, Supabase (Postgres + Storage), Zod, **Jest 30 + ts-jest** (`jest.config.ts`; integration runs under `jest.integration.config.ts --runInBand`), Playwright.

**Spec:** [`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md`](../specs/2026-08-14-cloud-blob-key-encoding-design.md) **v21**, approved 2026-08-15 after 18 dual adversarial review rounds. Section references below (§3.2, §3.5.1b …) point into it. **Read the spec section named in a task before starting that task.**

---

## Global Constraints

Every task's requirements implicitly include this section. Values are copied verbatim from the spec.

- **`SAFE = /^[A-Za-z0-9._-]+$/`**, **`LIMIT = 255`** (measured Storage ceiling, per path *segment*). §3.2
- **Hash the logical segment as `utf16le`, never `utf8`.** Node maps every unpaired surrogate to U+FFFD, so two different lone surrogates would hash identically. §3.2
- **The servability bound is `> 3 && <= 131` CODE POINTS**, not UTF-16 units. §3.4
- **Never write a literal control or bidi character into a source file or a test fixture — use escapes.**
  This spec shipped that defect four times, and **this plan shipped it a fifth time in Task 4's own
  fixture list, three hundred lines below the constraint forbidding it.** Stating the rule does not
  enforce it. **Before every commit, run:**
  ```bash
  python3 -c "import sys,unicodedata as u; [sys.exit(f'literal control/bidi char at line {s.count(chr(10),0,i)+1}') for p in sys.argv[1:] for s in [open(p,encoding='utf8').read()] for i,c in enumerate(s) if u.category(c) in ('Cc','Cf') and c!=chr(10)]" <files>
  ```
  Conversely **never write `\u`-style escapes in prose**; round-17 L3 found that inverse error.
- **Fixtures with two normalization forms are built with `.normalize('NFC')` / `.normalize('NFD')`, never as two source literals.**
- **Node 22+** is required (`String.prototype.isWellFormed`, Unicode property escapes). CI runs Node 22.
- **No migration.** §4's gate ran against prod on 2026-08-14: 19 objects, 0 rows outside `SAFE`. Nothing in this plan rewrites an existing object key.
- **Decision ① — the vault wins.** Local filenames keep their Unicode. **No guard is ever installed on the local path.** A guard that refuses to write a name *into the vault* is the inverse of this decision and caused round-16 B1.
- **`scripts/check-producer-enumeration.py` must exit 0** after any task that edits §3.5.1b.
- **Run the full ratchet set before declaring a task done, FAIL-FAST — never `|| echo`:**
  ```bash
  set -e
  for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do
    python3 "scripts/$c.py"
  done
  ```
  *(Round-1 M2: the first draft wrote `python3 scripts/$c.py || echo "RED: $c"`, which exits 0 whatever
  happens because `echo` succeeds — `portable-practices.md` §2, written into the plan three days after
  documenting it.)*
- **⛔ EVERY code snippet below was verified against the repo at plan-v2 time.** The v1 plan was written
  from the spec alone and **not one snippet was checked against the code it would live in**: it named a
  test runner the repo does not have, dropped the owner prefix from `objectKey`, called a method that
  does not exist, and invoked seven helpers nobody had written. If you find a snippet that does not
  compile, that is a plan defect — **stop and fix the plan**, do not improvise around it.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `lib/storage/supabase/encode-segment.ts` | **new** — the pure logical→physical segment encoder | T1 |
| `lib/storage/supabase/supabase-blob-store.ts` | wire the encoder into `objectKey`, `list`, `deletePrefix` | T2 |
| `lib/slugify.ts` | one-line orphaned-surrogate repair | T3 |
| `lib/html-doc/assert-cloud-summary-md-key.ts` | replace the allowlist with `isServableSummaryKey` | T4 |
| `lib/share/serve.ts` | the guard moves *inside* `getShareServeContext` | T5 |
| `lib/storage/blob-store.ts` + 3 adapters | **new primitive** `promoteIfAbsent` | T6 |
| `lib/html-doc/model-store.ts` | `ModelEnvelopeWriteSchema`; `serialize` enforces it | T7 |
| `lib/cloud-sync/sync-run.ts` (`companionTransfer`) | the `videoId` ownership credential | T8 |
| `lib/storage/supabase/supabase-metadata-store.ts` | `stripComputed` → **`videoDataPayload`** + the seam refusal | T9 |
| `lib/job-queue/summary-handler.ts` | the mint guard, before the Gemini call | T10 |
| `lib/cloud-sync/sync-run.ts` (additive caller) | the adopt guard, in the caller, above `:626` | T11 |
| `lib/cloud-sync/reconcile-serial.ts` | the four-cell relocate/refuse/skip table | T12 |
| `scripts/check-encoder-gate-sql.py` | **new** — behavior 20: the §4 SQL predicate derives from the encoder | T13 |

**Ordering rationale. T0 comes first — seven helpers and one production function that every later task's tests assume do not exist yet (round-1 H1/H2).** Then T1–T5 are independent and unblock everything. T6–T8 are the model/blob primitives. **T9 must land before T10–T12**, because those three are all *placements* whose refusal semantics depend on the seam existing. T12 is last of the guards because round-18 B1 was precisely a T12/T9 interaction.

---

## Task 0: The test infrastructure every later task assumes

**Round-1 H1 + H2.** The v1 plan's tests invoked **seven helpers that do not exist** and asserted a
production function that does not exist. An engineer executing literally hits this on Task 1 Step 1.
**Counted over `tests/`, `lib/`, `scripts/`, `app/`, `components/` with `python3` + `os.walk`** — and
counted twice, because the first pattern missed class methods and produced a false negative on
`collectObjectPaths`:

| Symbol | Status |
|---|---|
| `putBudget` | ✅ `tests/support/budget.ts` |
| `seedVideo` | ✅ `tests/integration/helpers/cloud.ts` |
| `storeWith` | ✅ `tests/lib/html-doc/model-store.test.ts` (local to that file) |
| `readVideo`, `runSync`, `applySerial`, `assertLogicalKey`, `localPrincipal`, `collectObjectPaths` | ✅ production |
| `fakeStoreHolding`, `callWith`, `ingestLocal`, `spyStore`, `ledgerTotal`, `mintShareToken`, `seedEnvelope` | ❌ **do not exist** |
| **`canonicallyEqualName`** | ❌ **does not exist** — it is in the SPEC only, and T13 tests it |

**Files:**
- Create: `lib/cloud-sync/canonically-equal-name.ts`, `tests/support/blob-fakes.ts`,
  `tests/support/cloud-fixtures.ts`
- Test: `tests/lib/cloud-sync/canonically-equal-name.test.ts`

**Interfaces — Produces:** `canonicallyEqualName(a: string | null, b: string): boolean`;
`fakeStoreHolding(keys: string[]): BlobStore`; `spyStore(onGet: jest.Mock): BlobStore`;
`callWith(method, fields)`; `ledgerTotal(): Promise<number>`; `mintShareToken(): Promise<string>`;
`seedEnvelope(base, envelope)`; `ingestLocal({title})`. **Every later task consumes these.**

- [ ] **Step 1: Write the failing test for `canonicallyEqualName` (behaviors 18i, 18k)**

```ts
it('behavior 18i — NFC and NFD forms of one name are EQUAL', () => {
  expect(canonicallyEqualName('café.md'.normalize('NFC'), 'café.md'.normalize('NFD'))).toBe(true);
});

it('behavior 18i — a PROPER SUBSET: fullwidth A is NOT an alias of A', () => {
  expect(canonicallyEqualName('Ａ.md', 'A.md')).toBe(false);
});

it('behavior 18k — a null left side is FALSE, so a loser with no summaryMd takes the probe branch', () => {
  expect(canonicallyEqualName(null, 'a.md')).toBe(false);
});
```

- [ ] **Step 2: Run it — `npx jest tests/lib/cloud-sync/canonically-equal-name.test.ts`.** Expect
      FAIL, module not found.

- [ ] **Step 3: Implement it**

```ts
/** Is `stored` the same NAME as `wanted` under the volume's alias relation?
 *
 *  A PROPER SUBSET of that relation, deliberately: NFC/NFD are aliases on APFS, fullwidth and
 *  compatibility forms are NOT. Widening this to NFKC would make `Ａ.md` and `A.md` equal and let a
 *  Class-A transfer overwrite a DIFFERENT video's artifact (spec behavior 18i).
 *
 *  `null` is false, never true: a loser row that advertises no key has not claimed this address, so
 *  it must take the probe-and-refuse branch rather than the overwrite branch (18k). */
export function canonicallyEqualName(stored: string | null | undefined, wanted: string): boolean {
  if (typeof stored !== 'string') return false;
  return stored.normalize('NFC') === wanted.normalize('NFC');
}
```

- [ ] **Step 4: Run it — expect PASS, 3 tests.**

- [ ] **Step 5: Write the shared fakes, and make each one FAIL LOUD rather than silently pass**

```ts
// tests/support/blob-fakes.ts
/** A BlobStore fake that already holds `keys`. Every method not needed by the test under
 *  construction THROWS — a fake that silently returns undefined turns a real defect into a
 *  passing test, which is the failure mode portable-practices §2 records. */
export function fakeStoreHolding(keys: string[]): BlobStore { /* … */ }

/** Records every `get` on the SENDER side. Behavior 26f asserts a NEGATIVE — that no read
 *  happened — so this must distinguish "not called" from "called and returned nothing". */
export function spyStore(onGet: jest.Mock): BlobStore { /* … */ }
```

- [ ] **Step 6: Write the cloud fixtures** (`callWith`, `ledgerTotal`, `mintShareToken`,
      `seedEnvelope`, `ingestLocal`) in `tests/support/cloud-fixtures.ts`, built on the existing
      `seedVideo` (`tests/integration/helpers/cloud.ts`). `ledgerTotal` must read the ledger through
      the same path production does — a hand-summed fixture would assert the test's arithmetic, not
      the app's.

- [ ] **Step 7: Run the whole suite — `npm test` — and commit**

```bash
git add lib/cloud-sync/canonically-equal-name.ts tests/support/ tests/lib/cloud-sync/
git commit -m "feat(#36): canonicallyEqualName and the shared test fakes (behaviors 18i, 18k)"
```

---

## Task 1: The segment encoder

**Spec:** §3.2. **Behaviors:** 1, 2, 3, 4, 5.

**Files:**
- Create: `lib/storage/supabase/encode-segment.ts`
- Test: `tests/lib/storage/encode-segment.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `encodeSegment(s: string): string`, `SAFE: RegExp`, `LIMIT: number` — all consumed by T2 and T13.

- [ ] **Step 1: Write the failing test**

```ts
import { encodeSegment, SAFE, LIMIT } from '@/lib/storage/supabase/encode-segment';

describe('encodeSegment', () => {
  it('behavior 1 — a SAFE segment within LIMIT is byte-identical', () => {
    expect(encodeSegment('003_intro-part2.md')).toBe('003_intro-part2.md');
  });

  it('passes an empty segment through, so a trailing slash survives', () => {
    expect(encodeSegment('')).toBe('');
  });

  it('behavior 2 — a non-ASCII segment becomes an ASCII physical key', () => {
    const out = encodeSegment('003_한국어.md');   // Korean, escaped deliberately
    expect(out).toMatch(/^[A-Za-z0-9._=-]+$/);
    expect(out).toContain('=h');
    expect(out.endsWith('.md')).toBe(true);
  });

  it('behavior 3 — NFC and NFD forms encode DIFFERENTLY', () => {
    const nfc = 'café.md'.normalize('NFC');
    const nfd = 'café.md'.normalize('NFD');
    expect(nfc).not.toBe(nfd);
    expect(encodeSegment(nfc)).not.toBe(encodeSegment(nfd));
  });

  it('behavior 4 — identity and hash branches are DISJOINT: `=` is not in SAFE', () => {
    expect(SAFE.test('a=b')).toBe(false);
    expect(encodeSegment('한.md')).toContain('=');
  });

  it('behavior 4 — the hash branch is deterministic', () => {
    expect(encodeSegment('한.md')).toBe(encodeSegment('한.md'));
  });

  it('behavior 5 — every encoded segment is at most 65 characters', () => {
    const long = '한'.repeat(400) + '.md';
    expect(encodeSegment(long).length).toBeLessThanOrEqual(65);
  });

  it('behavior 5 — an over-LIMIT ASCII segment is hashed, not passed through', () => {
    const long = 'a'.repeat(LIMIT + 1);
    expect(encodeSegment(long)).not.toBe(long);
    expect(encodeSegment(long)).toContain('=h');
  });

  it('hashes utf16le, so two DIFFERENT lone surrogates differ', () => {
    // The reason §3.2 chose utf16le: utf8 maps both to U+FFFD and they collide.
    expect(encodeSegment('x\uD840.md')).not.toBe(encodeSegment('x\uD850.md'));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest tests/lib/storage/encode-segment.test.ts`
Expected: FAIL — `Cannot find module '@/lib/storage/supabase/encode-segment'`

- [ ] **Step 3: Write the implementation**

```ts
import { createHash } from 'crypto';

/** The physical alphabet Supabase Storage accepts, measured in §2.1. */
export const SAFE = /^[A-Za-z0-9._-]+$/;
/** Measured Storage ceiling, per path SEGMENT and not per path (§2.2, premise P2). */
export const LIMIT = 255;

const HEAD = /^[A-Za-z0-9._-]+/;
const EXT = /\.[A-Za-z0-9]{1,8}$/;

/**
 * Map ONE logical path segment to a physical one. Total, deterministic, never inverted —
 * `list()` re-attaches the caller's logical prefix instead (§3.3), which is what makes a
 * one-way hash legal here.
 *
 * utf16le, NOT utf8: Node maps every unpaired surrogate to U+FFFD on the way to a utf8
 * buffer, so two DIFFERENT lone surrogates would hash to the same physical key and one
 * video's blob would overwrite another's. Reachable because `slugify`'s slice cuts UTF-16
 * code units (§3.2, and see T3 which repairs the producer).
 */
export function encodeSegment(s: string): string {
  if (s === '') return '';
  if (SAFE.test(s) && s.length <= LIMIT) return s;
  const head = (HEAD.exec(s)?.[0] ?? '').slice(0, 32);
  const ext = EXT.exec(s)?.[0] ?? '';
  const digest = createHash('sha256').update(Buffer.from(s, 'utf16le')).digest('base64url');
  return `${head}=h${digest.slice(0, 22)}${ext}`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest tests/lib/storage/encode-segment.test.ts`
Expected: PASS, 9 tests.

- [ ] **Step 5: Add the property test**

```ts
it('behavior 1 + 5 — property sweep over the codepoint space', () => {
  // ⚠ Round-1 L2: a stride SAMPLES, it does not cover. Say so rather than calling it
  // "the codepoint space" — this visits ~1.6% of it. Behavior 17e and 27 use stride 1 / 0x20
  // where completeness is the claim; this one is a smoke sweep and is labelled as one.
  for (let cp = 0; cp <= 0x10ffff; cp += 0x40) {
    if (cp >= 0xd800 && cp <= 0xdfff) continue;
    const seg = `003_x${String.fromCodePoint(cp)}.md`;
    const out = encodeSegment(seg);
    // The PHYSICAL alphabet is SAFE plus `=`, the hash-branch marker. Testing `SAFE.test(out)`
    // here contradicts behavior 4 two tests above — `=` is excluded from SAFE ON PURPOSE, so
    // the assertion fails on 100% of non-ASCII iterations after a CORRECT implementation.
    // (Round-1: both halves found this; measured false on node 22 before it was accepted.)
    expect(out).toMatch(/^[A-Za-z0-9._=-]+$/);
    expect(out.length).toBeLessThanOrEqual(65);
  }
});
```

Run: `npx jest tests/lib/storage/encode-segment.test.ts`
Expected: PASS, 10 tests.

- [ ] **Step 6: Commit**

```bash
git add lib/storage/supabase/encode-segment.ts tests/lib/storage/encode-segment.test.ts
git commit -m "feat(#36): the logical-to-physical segment encoder (spec 3.2, behaviors 1-5)"
```

---

## Task 2: Wire the encoder into `SupabaseBlobStore`

**Spec:** §3.1, §3.3. **Behaviors:** 6, 7, 8, 9, 10, 11, 12, 13.

**Files:**
- Modify: `lib/storage/supabase/supabase-blob-store.ts` (`objectKey`, `list`, `deletePrefix`)
- Test: `tests/integration/blob-encoding.test.ts`, `tests/lib/storage/blob-store-list.test.ts`

**Interfaces:**
- Consumes: `encodeSegment`, `SAFE` from T1.
- Produces: no new exports. `SupabaseBlobStore`'s public surface is unchanged — every method still speaks **logical** keys. This is the property T4–T12 rely on.

- [ ] **Step 1: Write the failing unit test for `list()`**

```ts
describe('SupabaseBlobStore.list — prefix re-attachment (spec 3.3)', () => {
  it('behavior 8 + 12 — returns LOGICAL keys, and a trailing slash is optional', async () => {
    const base = '003_한국어';
    const store = fakeStoreHolding([`dig/${base}/s1.r2.md`]);
    expect(await store.list(P, `dig/${base}/`)).toEqual([`dig/${base}/s1.r2.md`]);
    expect(await store.list(P, `dig/${base}`)).toEqual([`dig/${base}/s1.r2.md`]);
  });

  it('behavior 9 — throws when a physical REMAINDER segment cannot be named', async () => {
    const store = fakeStoreHolding(['dig/003_x/lost=hABCDEFGHIJKLMNOPQRSTUV.md']);
    await expect(store.list(P, 'dig/003_x/')).rejects.toThrow(/cannot be mapped back/i);
  });

  it("behavior 10 — does NOT throw when the CALLER's own prefix contains `=`", async () => {
    // The marker guard applies to the physical REMAINDER only. Applying it to the caller's
    // prefix strands a video on every run.
    const store = fakeStoreHolding(['dig/003_a=b/s1.r2.md']);
    await expect(store.list(P, 'dig/003_a=b/')).resolves.toEqual(['dig/003_a=b/s1.r2.md']);
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx jest tests/lib/storage/blob-store-list.test.ts`
Expected: FAIL — `list` currently returns physical keys for the Korean base.

- [ ] **Step 3: Modify the REAL `objectKey` and `list` — read them first**

⛔ **Round-1 B2/B3.** The v1 plan wrote both of these from scratch and got both wrong: it dropped
`p.id` (the **owner** prefix — a tenancy break, not a typo), dropped the `assertLogicalKey` traversal
guard, invented a method called `rawList`, and sliced by the wrong offset. **These are edits to
existing methods. This is what is there today:**

```ts
// lib/storage/supabase/supabase-blob-store.ts:15-18 — VERBATIM, today
private objectKey(p: Principal, key: string): string {
  assertLogicalKey(key);                          // traversal guard — KEEP
  return `${p.id}/${p.indexKey}/${key}`;          // p.id is the OWNER — KEEP
}

// :140-146 — VERBATIM, today
async list(p: Principal, prefix: string): Promise<string[]> {
  assertLogicalKey(prefix);
  const ownerRoot = `${p.id}/${p.indexKey}/`;
  const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
  const full = await this.collectObjectPaths(dirPath);   // a PRIVATE METHOD on this class, :132
  return full.map((f) => f.slice(ownerRoot.length));     // strips the OWNER ROOT, not the prefix
}
```

**The change is one line in each.** `objectKey` encodes the key's segments; `list` encodes the prefix
it searches under and re-attaches the caller's logical prefix to what comes back:

```ts
private objectKey(p: Principal, key: string): string {
  assertLogicalKey(key);
  const physical = key.split('/').map(encodeSegment).join('/');   // <- the only new line
  return `${p.id}/${p.indexKey}/${physical}`;
}

async list(p: Principal, prefix: string): Promise<string[]> {
  assertLogicalKey(prefix);
  const norm = prefix === '' || prefix.endsWith('/') ? prefix : `${prefix}/`;
  const ownerRoot = `${p.id}/${p.indexKey}/`;
  const physicalPrefix = norm.split('/').map(encodeSegment).join('/');   // <- new
  const dirPath = `${ownerRoot}${physicalPrefix}`.replace(/\/$/, '');
  const full = await this.collectObjectPaths(dirPath);
  return full.map((f) => {
    const remainder = f.slice(ownerRoot.length + physicalPrefix.length);  // <- the LEAF only
    // The `=h` marker guard applies to the REMAINDER ONLY — never the caller's own prefix, or a
    // logical key legitimately containing `=` strands a video every run (behavior 10, spec 3.3).
    if (remainder.split('/').some((seg) => seg.includes('=h'))) {
      throw new Error(
        `list: physical segment ${JSON.stringify(remainder)} cannot be mapped back to a logical `
        + `key. The caller supplies the prefix; leaves must be SAFE (spec 3.3, premise P4).`,
      );
    }
    return norm + remainder;                       // re-attach the caller's LOGICAL prefix
  });
}
```

**`deletePrefix` (`:129`) also builds a physical path and must encode too** — round-1 M5: the v1 plan
listed it as a file to modify and then no step modified it. Read it and apply the same one-line change.

- [ ] **Step 4: Run the unit tests**

Run: `npx jest tests/lib/storage/blob-store-list.test.ts`
Expected: PASS, 3 tests.

- [ ] **Step 5: Write the integration tests (needs local Supabase)**

```ts
const KOREAN = '003_한국어.md';

it('behavior 6 — put then get round-trips a Korean key', async () => {
  await blob.put(P, KOREAN, Buffer.from('hi', 'utf8'), 'text/markdown');
  expect((await blob.get(P, KOREAN))!.toString('utf8')).toBe('hi');
});

it('behavior 7 — putStaged then promote lands a Korean key correctly', async () => {
  const ref = await blob.putStaged(P, KOREAN, Buffer.from('body', 'utf8'), 'text/markdown');
  await blob.promote(ref);
  expect((await blob.get(P, KOREAN))!.toString('utf8')).toBe('body');
});

it('behavior 11 — deletePrefix("") removes everything under the playlist root', async () => {
  await blob.put(P, KOREAN, Buffer.from('x', 'utf8'), 'text/markdown');
  await blob.deletePrefix(P, '');
  expect(await blob.get(P, KOREAN)).toBeNull();
});

it('behavior 13 — the local and in-memory adapters are IDENTITY', async () => {
  for (const store of [localBlobStore, new InMemoryBlobStore()]) {
    await store.put(LOCAL_P, KOREAN, Buffer.from('x', 'utf8'), 'text/markdown');
    expect(await store.list(LOCAL_P, '')).toContain(KOREAN);
  }
});
```

Assert `process.env.SUPABASE_URL` contains `127.0.0.1` or `localhost` in `beforeAll` and **throw otherwise**. Clean up every object created.

- [ ] **Step 6: Run and commit**

```bash
npx jest tests/integration/blob-encoding.test.ts
git add lib/storage/supabase/supabase-blob-store.ts tests/
git commit -m "feat(#36): encode at the storage seam; list re-attaches the logical prefix (behaviors 6-13)"
```

---

## Task 3: `slugify` drops an orphaned surrogate half

**Spec:** §3.7 and the round-12 H1 box in §3.2. **Behaviors:** 16b.

**Why this is a defect repair, not a naming change:** those titles *today* produce mojibake vault filenames — APFS returns `003_x�.md` for a key written as `003_x\uD840.md`, and two different lone surrogates collapse onto one file, silently destroying one video's content. Measured. This removes a broken output nobody wants. It is **not** backlog #46 (the NFKC slice), which changes *readable* names and needs its own migration argument.

**Files:**
- Modify: `lib/slugify.ts`
- Test: `tests/lib/slugify.test.ts`

**Interfaces:**
- Consumes: nothing. Produces: `slugify`'s output is now guaranteed well-formed UTF-16 — T4's predicate and T10's mint guard both rely on this.

- [ ] **Step 1: Write the failing test**

```ts
it('behavior 16b — never returns ill-formed UTF-16', () => {
  // An astral letter straddling the 60-unit slice boundary leaves an orphaned half.
  const title = 'a'.repeat(59) + '\u{20000}';   // 59 BMP + 1 astral = 61 UTF-16 units
  expect(slugify(title).isWellFormed()).toBe(true);
});

it('behavior 16b — property sweep: no codepoint produces an ill-formed slug', () => {
  for (let cp = 0x10000; cp <= 0x10ffff; cp += 0x800) {
    for (const pad of [58, 59, 60]) {
      expect(slugify('a'.repeat(pad) + String.fromCodePoint(cp)).isWellFormed()).toBe(true);
    }
  }
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx jest tests/lib/slugify.test.ts -t 'ill-formed'`
Expected: FAIL — `expected false to be true`

- [ ] **Step 3: Apply the one-line repair**

```ts
// .slice(0, 60) cuts UTF-16 code units and can split a surrogate pair. Node then encodes the
// orphaned half as U+FFFD on the way to a filesystem path, so the vault filename becomes
// mojibake AND two different lone surrogates collapse onto one file (MEASURED on APFS).
const s = /* …existing pipeline… */.slice(0, 60);
return s.isWellFormed() ? s : s.slice(0, -1);   // drop the orphaned half
```

- [ ] **Step 4: Run and verify**

Run: `npx jest tests/lib/slugify.test.ts`
Expected: PASS. Then run the whole unit suite — `slugify` is widely used: `npx jest tests/lib`

- [ ] **Step 5: Commit**

```bash
git add lib/slugify.ts tests/lib/slugify.test.ts
git commit -m "fix(#36): slugify drops an orphaned surrogate half (spec 3.7, behavior 16b)"
```

---

## Task 4: Replace the allowlist with `isServableSummaryKey`

**Spec:** §3.4. **Behaviors:** 16c, 17, 17b, 17d, 17e, 24.

**The whole fix, in one sentence:** the old guard allowlists `[\p{L}\p{N}_-]` while its own docstring says the requirement is *"a single path component"*. Those are different, and the difference is what destroys a Korean-titled paid summary.

**Files:**
- Modify: `lib/html-doc/assert-cloud-summary-md-key.ts`
- Test: `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: **`isServableSummaryKey(key: string): boolean`** — the predicate T5, T9, T10, T11, T12 all install. `assertCloudSummaryMdKey(mdKey: string): void` keeps its name and throwing contract so its three existing consumers (`serve-summary-core.ts:61`, `resolve-summary-key.ts:16`, `pdf-render-version.ts`) are unchanged.

- [ ] **Step 1: Write the failing test**

```ts
import { isServableSummaryKey } from '@/lib/html-doc/assert-cloud-summary-md-key';

describe('isServableSummaryKey', () => {
  it('behavior 14/15/16/23 — ACCEPTS what the old allowlist destroyed', () => {
    for (const k of [
      '003_한국어.md',            // Korean
      ('003_café.md').normalize('NFD'),  // NFD accented Latin
      '003_hello world.md',                   // a space
      '003_\u{1F600}.md',                     // emoji
      '003_lesson-⒈.md',                 // DIGIT ONE FULL STOP — the round-11 B1 class
      '003_\u{1F100}.md',
    ]) expect(isServableSummaryKey(k)).toBe(true);
  });

  it('behavior 17 — REJECTS everything that is not a single path component', () => {
    for (const k of [
      'nested/foo.md', '003_a%2fb.md', '003_a／b.md',   // separators, in every form
      '℀.md',                                          // NFKC-folds to `a/c`
      '001_a．．b.md', '001_a..b.md',               // traversal-shaped
      '003_x\u0007.md', '003_x\u0085.md',              // C0 (BEL) and C1 (NEL) — ESCAPES ONLY
      '003_x\u202E.md',                                  // RIGHT-TO-LEFT OVERRIDE
      '003_' + 'a'.repeat(200) + '.md',                     // over-long
    ]) expect(isServableSummaryKey(k)).toBe(false);
  });

  it('behavior 16c — rejects ILL-FORMED UTF-16', () => {
    expect(isServableSummaryKey('003_x\uD840.md')).toBe(false);
  });

  it('behavior 17d — inspects the NAME, not name + ".md"', () => {
    // `⒈` NFKC-folds to `1.`; gluing `.md` on manufactures a `..` that is in neither piece.
    expect(isServableSummaryKey('003_lesson-⒈.md')).toBe(true);
    expect(isServableSummaryKey('003_lesson-1..md')).toBe(true);
  });

  it('behavior 17b — the bound did NOT narrow: 129, 130 and 131 are ACCEPTED', () => {
    for (const n of [129, 130, 131]) {
      expect(isServableSummaryKey('a'.repeat(n - 3) + '.md')).toBe(true);
    }
    expect(isServableSummaryKey('a'.repeat(129) + '.md')).toBe(false);   // 132
  });

  it('behavior 24 — the bound counts CODE POINTS, not UTF-16 units', () => {
    const key = '\u{20000}'.repeat(64) + '.md';   // 67 code points, 131 UTF-16 units
    expect([...key].length).toBe(67);
    expect(isServableSummaryKey(key)).toBe(true);
  });

  it('behavior 17e — every Bidi_Control code point is rejected, DERIVED not counted', () => {
    for (let cp = 0; cp <= 0x10ffff; cp++) {
      if (cp >= 0xd800 && cp <= 0xdfff) continue;
      const ch = String.fromCodePoint(cp);
      if (/\p{Bidi_Control}/u.test(ch)) {
        expect(isServableSummaryKey(`003_x${ch}.md`)).toBe(false);
      }
    }
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx jest tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`
Expected: FAIL — the Korean and space cases are rejected by the current allowlist.

- [ ] **Step 3: Implement the predicate**

```ts
export function isServableSummaryKey(key: string): boolean {
  if (!key.endsWith('.md')) return false;
  // CODE POINTS, not UTF-16 units — the guard this replaces counts code points (it is a /u
  // regex) and this predicate's whole subject is non-ASCII keys. 131 = that guard's ceiling.
  const cp = [...key];
  if (cp.length <= 3 || cp.length > 131) return false;
  // A lone surrogate does not survive the local filesystem: Node encodes it as U+FFFD, the
  // vault filename becomes mojibake, and two DIFFERENT lone surrogates collapse onto one file.
  if (!key.isWellFormed()) return false;

  // Inspect the NAME, NEVER the glued key: folding `name + '.md'` manufactures a `..` at the
  // joint out of one legal character (`⒈` is DIGIT ONE FULL STOP — it folds to `1.`).
  const name = key.slice(0, -3);
  // Raw form AND compatibility-folded form. `℀` folds to `a/c`, `＼` to a backslash.
  // A hand-typed homoglyph denylist cannot be complete; NFKC closes that class.
  for (const s of [name, name.normalize('NFKC')]) {
    if (s === '' || s === '.' || s === '..') return false;
    if (s.includes('/') || s.includes('\\')) return false;
    if (s.includes('..')) return false;
    if (/[\x00-\x1f\x7f-\x9f]/.test(s)) return false;          // C0 + DEL + C1
    if (/%2f|%5c/i.test(s)) return false;                      // percent-encoded separators
    if (/\p{Bidi_Control}/u.test(s)) return false;             // the PROPERTY, not a hand list
  }
  return true;
}

export function assertCloudSummaryMdKey(mdKey: string): void {
  if (typeof mdKey !== 'string' || !isServableSummaryKey(mdKey)) {
    // ⚠ Round-1 M1: READ the current implementation before rewriting this. It attaches
    // `statusCode: 409`, and 22 existing assertions depend on it. The plan claimed "the throwing
    // contract is unchanged" while dropping the property that makes it a 409 instead of a 500.
    const err = new Error(`not a servable summary key: ${JSON.stringify(mdKey)}`);
    (err as Error & { statusCode?: number }).statusCode = 409;
    throw err;
  }
}
```

- [ ] **Step 4: Run and verify**

Run: **`npm test`** — the WHOLE unit suite, not `tests/lib/html-doc/` (round-1 M7: this predicate has three consumers and 22 existing assertions; a slice narrower than the blast radius is not a verification). Expected: PASS. The existing `assert-cloud-summary-md-key.test.ts` cases must still pass — if one now fails, it was asserting the *allowlist*, not the requirement; update it and say so in the commit.

- [ ] **Step 5: Add the cross-derivation property test (behavior 27)**

```ts
it('behavior 27 — NO slugify output fails the predicate, over the whole codepoint space', () => {
  // The cross-derivation 3.4 and 3.5 each ASSUMED and neither checked.
  for (let cp = 0; cp <= 0x10ffff; cp += 0x20) {
    if (cp >= 0xd800 && cp <= 0xdfff) continue;
    const ch = String.fromCodePoint(cp);
    for (const title of [ch, `a${ch}`, `${ch}a`, 'a'.repeat(59) + ch]) {
      const key = `${String(1).padStart(3, '0')}_${slugify(title)}.md`;
      if (slugify(title) === '') continue;      // empty slug is a separate, handled case
      expect(isServableSummaryKey(key)).toBe(true);
    }
  }
});
```

- [ ] **Step 6: Commit**

```bash
git add lib/html-doc/assert-cloud-summary-md-key.ts tests/
git commit -m "feat(#36): isServableSummaryKey asserts single-path-component, not ASCII (behaviors 16c,17,17b,17d,17e,24,27)"
```

---

## Task 5: The share guard moves inside `getShareServeContext`

**Spec:** §3.4. **Behaviors:** 21. **§3.5.1b row 6.**

The share path builds `base` at **two** places (`route.ts:69` and `:78`). Guarding both is enumeration; guarding the one function that produces `mdKey` covers them **by construction**.

**Files:**
- Modify: `lib/share/serve.ts` (after the `mdKey` assignment at `:47`)
- Test: `tests/integration/share-route.test.ts`

**Interfaces:**
- Consumes: `isServableSummaryKey` from T4.
- Produces: `getShareServeContext` may now return `{ status: 'denied' }` for a promoted-but-unservable key.

- [ ] **Step 1: Write the failing test**

```ts
it('behavior 21 — a promoted but UNSERVABLE mdKey is denied, from inside the context helper', async () => {
  await seedVideo({ summaryMd: 'nested/evil.md',
                    artifacts: { summaryMd: { key: 'nested/evil.md', status: 'promoted' } } });
  const token = await mintShareToken();
  expect(await getShareServeContext(svc, token)).toEqual({ status: 'denied' });
});

it('behavior 21 — a Korean key is NOT denied', async () => {
  await seedVideo({ summaryMd: '003_한국어.md',
                    artifacts: { summaryMd: { key: '003_한국어.md', status: 'promoted' } } });
  const ctx = await getShareServeContext(svc, await mintShareToken());
  expect('mdKey' in ctx && ctx.mdKey).toBe('003_한국어.md');
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx jest tests/integration/share-route.test.ts -t 'behavior 21'`
Expected: FAIL — the first case returns a context instead of `denied`.

- [ ] **Step 3: Implement**

```ts
// lib/share/serve.ts, immediately after the existing `if (!mdKey) return denied;`
//
// §3.5.1b row 6: `mdKey` has TWO producers — `artifact?.key` (taken first) and the top-level
// `summaryMd` fallback. This guard is provenance-BLIND: both arms are refused identically,
// and it tests exactly the value the serve path goes on to consume.
if (!isServableSummaryKey(mdKey)) return denied;
```

- [ ] **Step 4: Run and verify**

Run: `npx jest tests/integration/share-route.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/share/serve.ts tests/integration/share-route.test.ts
git commit -m "feat(#36): the share guard lives inside getShareServeContext, covering both base derivations (behavior 21)"
```

---

## Task 6: `promoteIfAbsent` on the BlobStore seam

**Spec:** §3.6.2. **Behaviors:** 18d, 18d2, 18d3, 18d4, 18d5, 18f.

**Files:**
- Modify: `lib/storage/blob-store.ts` (interface), `local/local-blob-store.ts`, `supabase/supabase-blob-store.ts`, `in-memory-blob-store.ts`, plus every test decorator and fault-injection wrapper.
- Test: `tests/lib/storage/blob-store-contract.test.ts` (the shared contract suite — run against **all three** adapters)

**Interfaces:**
- Consumes: nothing.
- Produces: **`promoteIfAbsent(ref: StagedRef): Promise<void>`** — create-if-absent, used by T13's additive path. **`promote` is unchanged** (behavior 18d4) and keeps its existing callers.

- [ ] **Step 1: Write the failing contract test**

```ts
// Runs against localBlobStore, InMemoryBlobStore and SupabaseBlobStore — one describe.each.
it('behavior 18d — leaves an existing occupant BYTE-IDENTICAL', async () => {
  await store.put(P, KEY, Buffer.from('occupant', 'utf8'), 'text/markdown');
  const ref = await store.putStaged(P, KEY, Buffer.from('newcomer', 'utf8'), 'text/markdown');
  await store.promoteIfAbsent(ref);
  expect((await store.get(P, KEY))!.toString('utf8')).toBe('occupant');
});

it('behavior 18d2 — RESOLVES rather than throwing on an existing final, and removes the staging tree', async () => {
  await store.put(P, KEY, Buffer.from('occupant', 'utf8'), 'text/markdown');
  const ref = await store.putStaged(P, KEY, Buffer.from('x', 'utf8'), 'text/markdown');
  await expect(store.promoteIfAbsent(ref)).resolves.toBeUndefined();
  expect(await store.get(P, ref.tempKey)).toBeNull();
  expect(await store.list(P, '_staging/')).toEqual([]);      // the WHOLE tree, not just the file
});

it('behavior 18d3 — creates missing parents, and leaves no _staging tree, on a NESTED key', async () => {
  // Nested deliberately: a plain rmdir here is ENOTEMPTY on exactly the branch this tests.
  const nested = `dig/003_base/s1.r2.md`;
  const ref = await store.putStaged(P, nested, Buffer.from('body', 'utf8'), 'text/markdown');
  await store.promoteIfAbsent(ref);
  expect((await store.get(P, nested))!.toString('utf8')).toBe('body');
  expect(await store.list(P, '_staging/')).toEqual([]);
});

it('behavior 18d4 — `promote` is UNCHANGED: it still overwrites', async () => {
  await store.put(P, KEY, Buffer.from('old', 'utf8'), 'text/markdown');
  const ref = await store.putStaged(P, KEY, Buffer.from('new', 'utf8'), 'text/markdown');
  await store.promote(ref);
  expect((await store.get(P, KEY))!.toString('utf8')).toBe('new');
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest tests/lib/storage/blob-store-contract.test.ts`
Expected: FAIL — `store.promoteIfAbsent is not a function`

- [ ] **Step 3: Add the interface method and the local implementation**

```ts
// lib/storage/blob-store.ts
export interface BlobStore extends ReadOnlyBlobStore {
  /** Create-if-absent finalize. Resolves (never throws) when the final already exists, and
   *  removes the staging tree either way. `promote` is the overwrite form and is unchanged. */
  promoteIfAbsent(ref: StagedRef): Promise<void>;
}
```

```ts
// lib/storage/local/local-blob-store.ts
async promoteIfAbsent(ref: StagedRef): Promise<void> {
  const final = this.abs(ref.principal, ref.finalKey);   // NOT ref.key — StagedRef is
  //   { principal, tempKey, finalKey } (blob-store.ts:5). Round-1 Blocking: the v1 plan wrote
  //   ref.key and would have failed tsc on the first line an engineer typed.
  mkdirSync(dirname(final), { recursive: true });          // 18d3
  try {
    linkSync(this.abs(ref.principal, ref.tempKey), final); // atomic create-if-absent
  } catch (e: any) {
    if (e?.code !== 'EEXIST') throw e;                     // 18d2: EEXIST RESOLVES
  } finally {
    rmSync(this.stagingRoot(ref), { recursive: true, force: true });  // 18f: the whole tree
  }
}
```

- [ ] **Step 4: Implement on Supabase and in-memory**

Supabase: `upload()` without `upsert` returns HTTP **409** when the object exists — treat 409 as success, rethrow anything else. In-memory: `if (!this.map.has(k)) this.map.set(k, bytes)`.

- [ ] **Step 5: Run the contract suite against all three, then the whole suite**

Run: `npx jest tests/lib/storage/ && npx jest`
Expected: PASS. **Behavior 18d5** — if any `BlobStore` implementer (including test decorators and the object fake) does not implement or forward `promoteIfAbsent`, `tsc` will say so. Fix each, and for every fault-injection wrapper state in a comment whether its injected fault applies.

- [ ] **Step 6: Commit**

```bash
git add lib/storage/ tests/lib/storage/
git commit -m "feat(#36): promoteIfAbsent on the BlobStore seam, all three adapters (behaviors 18d-18f)"
```

---

## Task 7: `ModelEnvelopeWriteSchema` — `videoId` required at the write side

**Spec:** §3.6.4. **Behaviors:** 18j5, 18j5b, 18j8. **§3.5.1b row 7.**

**The rule is attached to `serialize()`, not to a writer name.** There are two exported writers and a repo tripwire *forbids* merging them; v17 attached the requirement to one and the cloud serve path — the writer that spends money — compiled unchanged.

⚠ **Rollout cost, counted:** **41 call sites** (3 production + 38 test) across **11 files**, roughly **20** distinct envelope literals, because fixtures are shared (`rerender.test.ts` has 14 calls and 2 literals). Expect `tsc` to go red in all 41 the moment step 3 lands. That is the mechanism working.

**Files:**
- Modify: `lib/html-doc/model-store.ts`; then `generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464`; then the 8 test files.
- Test: `tests/lib/html-doc/model-store.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `ModelEnvelopeWriteSchema`, `type ModelEnvelopeWrite = ModelEnvelope & { videoId: string }`. Both writers now take `ModelEnvelopeWrite`. `ModelEnvelopeSchema` (read) is **unchanged** — `videoId` stays optional there.

- [ ] **Step 1: Write the failing test**

```ts
it('behavior 18j5 — an envelope without videoId cannot be SERIALIZED, via either writer', async () => {
  const bad = { ...ENVELOPE } as any;   // no videoId
  await expect(writeModelEnvelope(P, 'a', bad, store)).rejects.toThrow(/videoId/);
  await expect(writeModelEnvelopeWithin(putBudget(5000), P, 'a', bad, store)).rejects.toThrow(/videoId/);
});

it('behavior 18j5 — asserted through the SERVE writer specifically', async () => {
  // serve-doc.ts calls writeModelEnvelopeWithin; a repo tripwire forbids it calling the other.
  const put = jest.fn();
  await expect(
    writeModelEnvelopeWithin(putBudget(5000), P, 'a', { ...ENVELOPE } as any, storeWith(put)),
  ).rejects.toThrow(/videoId/);
  expect(put).not.toHaveBeenCalled();      // fail loud BEFORE any write
});

it('behavior 18j5b — READING a legacy envelope with no videoId still succeeds', async () => {
  await store.put(P, MODEL_KEY('a'), Buffer.from(JSON.stringify(ENVELOPE)), 'application/json');
  const got = await readModelEnvelope(P, 'a', store);
  expect(got).not.toBeNull();
  expect(got!.videoId).toBeUndefined();    // the 7 legacy prod envelopes must still parse
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest tests/lib/html-doc/model-store.test.ts`
Expected: FAIL — no rejection; `videoId` is not required anywhere yet.

- [ ] **Step 3: Implement**

```ts
/** READ side — unchanged. `videoId` optional so the 7 legacy prod envelopes still parse. */
export const ModelEnvelopeSchema = z.object({ /* …existing… */ videoId: z.string().optional() });

/** WRITE side. Attached to the TYPE `serialize` consumes, so any writer — present or future —
 *  must supply it to reach the bytes. Two exported writers funnel through `serialize`, and
 *  tests/lib/html-doc/serve-bounded-import-guard.test.ts FORBIDS collapsing them. */
export const ModelEnvelopeWriteSchema = ModelEnvelopeSchema.extend({ videoId: z.string().min(1) });
export type ModelEnvelopeWrite = z.infer<typeof ModelEnvelopeWriteSchema>;

function serialize(envelope: ModelEnvelopeWrite): Buffer {
  ModelEnvelopeWriteSchema.parse(envelope);   // fail loud, BEFORE any write
  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
}
```

Change both writers' `envelope` parameter type to `ModelEnvelopeWrite`.

- [ ] **Step 4: Run `tsc` and fix all 41 call sites**

Run: `npx tsc --noEmit`
Expected: ~41 errors. Production sources for the value, all verified in scope: `generate.ts` — `runHtmlDoc(videoId, …)`, its first parameter. `serve-doc.ts` — `videoId` is an explicit param of `resolveMagazineModel`. `sync-run.ts:464` — **stamp the RECEIVER's** `videoId` (`winnerVideo.id`, in scope at `:445`), never ship the sender's envelope verbatim.

- [ ] **Step 5: Add behavior 18j8**

```ts
it('behavior 18j8 — a LOCAL serial migration preserves videoId through the JSON round-trip', () => {
  const before = JSON.stringify({ ...ENVELOPE, videoId: 'dQw4w9WgXcQ', sourceMd: 'old.md' });
  const after = JSON.parse(rewriteEnvelopeSourceMd(before, 'new.md'));
  expect(after.sourceMd).toBe('new.md');
  expect(after.videoId).toBe('dQw4w9WgXcQ');   // unknown-field preservation is why this bypass is safe
});
```

- [ ] **Step 6: Run everything and commit**

```bash
npx tsc --noEmit && npx jest
git add lib/html-doc/ lib/cloud-sync/sync-run.ts tests/
git commit -m "feat(#36): videoId required at the model WRITE schema, enforced in serialize (behaviors 18j5,18j5b,18j8)"
```

---

## Task 8: The `videoId` ownership credential in `companionTransfer`

**Spec:** §3.6.4. **Behaviors:** 18j, 18j2, 18j3, 18j4, 18j6, 18j7.

**Why an ID and not a name:** round-13 H1 measured `sourceMd` **stale by construction** — `reconcileCloudBase` byte-copies the envelope and never rewrites it. `videoId` cannot go stale, because nothing in the answer moves.

**Files:**
- Modify: `lib/cloud-sync/sync-run.ts` (`companionTransfer`, around `:441-475`)
- Test: `tests/integration/cloud-sync-companion.test.ts`

**Interfaces:**
- Consumes: `ModelEnvelopeWrite` from T7.
- Produces: no new exports. `companionTransfer` keeps its **never-throws** contract.

- [ ] **Step 1: Write the failing tests**

```ts
it('behavior 18j — REFUSES ship/delete when the envelope videoId differs from the row, and RETURNS an error', async () => {
  const res = await companionTransfer(/* receiver envelope videoId: 'OTHER' , row: 'dQw4…' */);
  expect(res.shareNeedsOwnerServe).toBe(true);
  expect(res.error).toMatch(/envelope videoId/);
  expect(loserBlob.delete).not.toHaveBeenCalled();     // the paid model survives
});

it('behavior 18j — never THROWS, so the caller still advances the baseline', async () => {
  await expect(companionTransfer(/* mismatched */)).resolves.toBeDefined();
});

it('behavior 18j2 — SHIPS when the receiver read is `none` or `unknown`', async () => {
  for (const read of ['none', 'unknown'] as const) {
    expect((await companionTransfer(/* receiver: read */)).shipped).toBe(true);
  }
});

it('behavior 18j4 — a LEGACY envelope with no videoId proceeds, and sourceMd is NOT consulted', async () => {
  const res = await companionTransfer(/* receiver envelope: no videoId, sourceMd: 'wrong.md' */);
  expect(res.shipped).toBe(true);
});

it('behavior 18j6 — the ship STAMPS the receiver videoId; it never downgrades one that had it', async () => {
  await companionTransfer(/* sender envelope: NO videoId (written by generate.ts) */);
  const written = await readModelEnvelope(receiverP, base, receiverBlob);
  expect(written!.videoId).toBe(ROW_VIDEO_ID);
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx jest tests/integration/cloud-sync-companion.test.ts`
Expected: FAIL — no `videoId` check exists.

- [ ] **Step 3: Implement the four-outcome table**

```ts
// §3.6.4. Stated per OUTCOME, and the refusal RETURNS — companionTransfer's docstring is
// explicit that every companion write is best-effort and NEVER throws (M-R6-1): a throw is
// caught per-video at :812 and SKIPS writeVideoBaseline, so the run errors forever.
// ⚠ Round-1 H3: the refusal must gate BOTH the ship AND the delete at :475. Placing it in the
// ship arm alone leaves `loser.blob.delete(MODEL_KEY(base))` reachable — which destroys the paid
// model the credential exists to protect, and makes 18j's own assertion unsatisfiable.
// Use decideCompanion's ALREADY-READ envelope; do not re-read with readModelEnvelope, which
// collapses absent / unreadable / schema-invalid into one null (blob-store.ts:27-37 documents
// exactly that on the Supabase backend) and would invent an ownership claim from a failed read.
const envelope = decision.receiverEnvelope;   // 'none' | 'unknown' | ModelEnvelope
if (envelope !== 'none' && envelope !== 'unknown'
    && envelope.videoId && envelope.videoId !== winnerVideo.id) {
  return { shareNeedsOwnerServe: true,
           error: `companion refused: envelope videoId ${envelope.videoId}, row ${winnerVideo.id}` };
}
// no videoId (legacy)  -> proceed. Do NOT fall back to sourceMd: round-13 H1 measured it stale
//                         by construction, so the fallback reintroduces the defect for exactly
//                         the envelopes least able to survive it.
// absent / unreadable  -> readModelEnvelope returns null; no ownership claim is invented.
await writeModelEnvelope(loser.p, base, { ...decision.envelope, videoId: winnerVideo.id }, loser.blob);
```

- [ ] **Step 4: Add behavior 18j3 and 18j7**

```ts
it('behavior 18j3 + 18j7 — after a cloud base relocation the ship still succeeds, and the COPIED envelope keeps the same videoId', async () => {
  await seedEnvelope(oldBase, { videoId: 'dQw4w9WgXcQ' });
  await reconcileCloudBase({ /* relocate oldBase -> newBase */ });
  const copied = await readModelEnvelope(cloudP, newBase, cloudBlob);
  expect(copied!.videoId).toBe('dQw4w9WgXcQ');   // preserved by the COPY, not the write schema
  expect((await companionTransfer(/* … */)).shipped).toBe(true);
});
```

- [ ] **Step 5: Run and commit**

```bash
npx jest tests/integration/cloud-sync-companion.test.ts
git add lib/cloud-sync/sync-run.ts tests/
git commit -m "feat(#36): videoId is the model-ownership credential, replacing stale-by-construction sourceMd (behaviors 18j-18j7)"
```

---

## Task 9: `videoDataPayload` — the metadata seam refuses an unservable advertisement

**Spec:** §3.5.1, §3.5.1b **row 1**. **Behaviors:** 26c, 26c2, 26c3, 26c4.

**⚠ T10, T11 and T12 all depend on this task. Land it first.** Round-18 B1 was exactly a T12/T9 interaction: a placement that let a write through while the seam still refused it.

**The rename is load-bearing, not cosmetic.** `stripComputed` reads as optional hygiene, so a future writer skipping it looks harmless. `videoDataPayload` reads as *the* way to build the payload.

**Files:**
- Modify: `lib/storage/supabase/supabase-metadata-store.ts` (`:19`, and the three call sites `:119`, `:143`, `:160`)
- Test: `tests/integration/metadata-seam.test.ts`

**Interfaces:**
- Consumes: `isServableSummaryKey` from T4.
- Produces: no new exports — `videoDataPayload` is **module-private**, which is the entire point. It is the one function every write to `videos.data` through this adapter passes through, so a fourth adapter method added later is covered **by construction**.

- [ ] **Step 1: Write the failing tests**

```ts
it.each(['upsertVideo', 'updateVideoFields', 'bulkUpdateVideoFields'] as const)(
  'behaviors 26c + 26c2 — %s REFUSES a patch advertising an unservable key', async (method) => {
    await expect(callWith(method, {
      summaryMd: 'nested/evil.md',
      artifacts: { summaryMd: { key: 'nested/evil.md', status: 'promoted' } },
    })).rejects.toThrow(/not a servable summary key/);
  });

it('behavior 26c — a Korean key is ACCEPTED', async () => {
  await expect(callWith('updateVideoFields', {
    summaryMd: '003_한국어.md',
    artifacts: { summaryMd: { key: '003_한국어.md', status: 'promoted' } },
  })).resolves.toBeUndefined();
});

it('behavior 26c3 — transferClassA on copyToCloud is refused; on copyToLocal it is NOT', async () => {
  // The LOCAL store has no seam guard, correctly, per 3.4 and decision (1). A test written
  // against copyToLocal would pass VACUOUSLY, which is why this row names the direction.
  await expect(runSync({ direction: 'copyToCloud', key: 'nested/evil.md' })).rejects.toThrow();
  await expect(runSync({ direction: 'copyToLocal', key: 'nested/evil.md' })).resolves.toBeDefined();
});

it('behavior 26c4 — after a transferClassA refusal the loser row still points at its OLD key', async () => {
  const before = await readVideo(cloud, cloudP, ID);
  await runSync({ direction: 'copyToCloud', key: 'nested/evil.md' }).catch(() => {});
  expect((await readVideo(cloud, cloudP, ID))!.summaryMd).toBe(before!.summaryMd);
  // The accepted residual is an ORPHAN blob at the unservable key, not a lost artifact.
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx jest tests/integration/metadata-seam.test.ts`
Expected: FAIL — every patch is accepted today.

- [ ] **Step 3: Rename and add the refusal**

```ts
/**
 * The ONE function that builds what lands in `videos.data` through this adapter. All three
 * data-writing methods pass their payload through it and nothing else calls it, so the
 * entrance count stops mattering — a fourth method added later is covered by construction.
 *
 * Renamed from `stripComputed` deliberately (round-15 M1): a name that says "optional
 * hygiene" invites a future writer to skip it, and skipping this one is a money-path defect.
 */
function videoDataPayload<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
  const patch = v as { summaryMd?: unknown; artifacts?: { summaryMd?: { key?: unknown; status?: unknown } } };
  // ⚠ DECIDED at round 1 (Codex M1). The spec's rule is "`summaryMd` OR
  // `artifacts.summaryMd.status = 'promoted'`". The v1 plan guarded `artifacts.summaryMd.key`
  // REGARDLESS of status, which is STRICTER than specified and would refuse a legitimate
  // non-advertising repair state. Guard the top-level key always; guard the artifact key only when
  // it is being promoted. **A guard stricter than its spec is still a guard nobody agreed to.**
  const advertised = [
    patch.summaryMd,
    patch.artifacts?.summaryMd?.status === 'promoted' ? patch.artifacts?.summaryMd?.key : undefined,
  ].filter((k): k is string => typeof k === 'string');
  for (const key of advertised) {
    if (!isServableSummaryKey(key)) {
      throw new Error(`not a servable summary key: ${JSON.stringify(key)} — refused at the metadata seam`);
    }
  }
  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
  return rest;
}
```

Replace all three call sites (`:119`, `:143`, `:160`).

- [ ] **Step 4: Run and verify, then re-run the producer check**

```bash
npx jest tests/integration/metadata-seam.test.ts && npx jest
python3 scripts/check-producer-enumeration.py
```
Expected: tests PASS, producer check exit 0.

- [ ] **Step 5: Commit**

```bash
git add lib/storage/supabase/supabase-metadata-store.ts tests/
git commit -m "feat(#36): videoDataPayload is the metadata seam and refuses an unservable advertisement (behaviors 26c-26c4)"
```

---

## Task 10: The mint guard — refuse before the money moves

**Spec:** §3.5.1 placement 1, §3.5.1b **row 2**. **Behaviors:** 25.

**Files:**
- Modify: `lib/job-queue/summary-handler.ts` (between `:95` `reserveVideoSlot` and `:101` the Gemini call)
- Test: `tests/integration/summary-handler-guard.test.ts`

**Interfaces:** Consumes `isServableSummaryKey` (T4). Produces nothing.

- [ ] **Step 1: Write the failing test**

```ts
it('behavior 25 — the mint refuses an unservable key BEFORE the Gemini call, so no money moves', async () => {
  const gemini = jest.fn();
  await expect(runSummaryJob({ title: 'x'.repeat(400), gemini })).rejects.toThrow(/servable/);
  expect(gemini).not.toHaveBeenCalled();
  expect(await ledgerTotal()).toBe(0);           // the whole point of this placement
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx jest tests/integration/summary-handler-guard.test.ts`
Expected: FAIL — Gemini was called.

- [ ] **Step 3: Implement**

```ts
// summary-handler.ts, immediately after `const baseName = …` at :96.
// AFTER reserveVideoSlot and BEFORE the Gemini call: a refusal here costs NO MONEY, which is
// why this placement stays outside the seam. The cost is a consumed serial and a dead-letter
// retry — accepted, and stated in 3.5.
if (!isServableSummaryKey(`${baseName}.md`)) {
  throw new Error(
    `refusing to mint an unservable summary key: ${JSON.stringify(`${baseName}.md`)}. `
    + `Rename the video title or file a bug — no Gemini call was made.`,
  );
}
```

- [ ] **Step 4: Run and verify**

Run: `npx jest tests/integration/summary-handler-guard.test.ts`
Expected: PASS. **Note:** after T3 and T4, no `slugify` output can reach this branch (behavior 27 proves it) — this is a **backstop**, and the assertion that the §3.4/§3.5 cross-derivation still holds. It goes red if either side moves.

- [ ] **Step 5: Commit**

```bash
git add lib/job-queue/summary-handler.ts tests/
git commit -m "feat(#36): the mint refuses an unservable key before the paid call (behavior 25)"
```

---

## Task 11: The adopt guard — in the CALLER, above the sender read

**Spec:** §3.5.1 placement 3, §3.5.1b **row 4**. **Behaviors:** 26, 26b, 26e, 26f.

⚠ **`copyAdditiveVideo` cannot tell which side it is on.** Its signature is `(to: MetadataStore, toP: Principal, toBlob: BlobStore, …)` — `MetadataStore` is an interface both stores satisfy. A guard inside it applies in **both** directions or sniffs the concrete type, and applying it on `copyToLocal` strands a paid cloud artifact (round-16 B1). **The guard goes in the caller**, where `presentIsLocal` already exists.

**Files:**
- Modify: `lib/cloud-sync/sync-run.ts` at `:624-627`, **above** the `readMdBody` at `:626`
- Test: `tests/integration/cloud-sync-adopt.test.ts`

**Interfaces:** Consumes `isServableSummaryKey` (T4). Produces nothing.

- [ ] **Step 1: Write the failing tests**

```ts
it('behavior 26 — local->cloud adopt of an unservable key REFUSES, creates no receiver row, and names the repair', async () => {
  await expect(runSync({ local: { summaryMd: 'nested/evil.md' }, cloud: null })).rejects.toThrow(/rename/i);
  expect(await readVideo(cloud, cloudP, ID)).toBeNull();     // no bare row
});

it('behavior 26e — cloud->local hydration of an unservable key SUCCEEDS', async () => {
  // The vault is NOT guarded (3.4, decision (1)). Without this row the round-16 B1 regression
  // is invisible, because behavior 26 alone passes whichever direction it is written against.
  await runSync({ local: null, cloud: { summaryMd: 'nested/evil.md' } });
  expect(await localBlob.get(localP, 'nested/evil.md')).not.toBeNull();
});

it('behavior 26f — the guard runs ABOVE the sender read: no `get` on the sender blob store', async () => {
  const senderGet = jest.fn();
  await runSync({ local: { summaryMd: 'nested/evil.md' }, cloud: null,
                  localBlob: spyStore(senderGet) }).catch(() => {});
  expect(senderGet).not.toHaveBeenCalled();
});

it('behavior 26b — the refusal SURVIVES a second run; it is not routed around', async () => {
  await runSync({ … }).catch(() => {});
  await expect(runSync({ … })).rejects.toThrow();            // identical, forever
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx jest tests/integration/cloud-sync-adopt.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement in the caller**

```ts
// sync-run.ts, replacing :624-627. The direction is known HERE and nowhere downstream.
const from: Side = presentIsLocal ? localSide : cloudSide;
const to: Side = presentIsLocal ? cloudSide : localSide;
// The receiver is the CLOUD only when the present side is local. Guard before the sender read
// (behavior 26f) and before ensureReceiverSlot's durable insert (round-13 H2) — refusing here
// is strictly earlier than either, so no receiver row and no staged blob can exist.
if (presentIsLocal && present.summaryMd && !isServableSummaryKey(present.summaryMd)) {
  throw new Error(
    `cannot sync ${present.id} to the cloud: the vault filename `
    + `${JSON.stringify(present.summaryMd)} is not a servable key. `
    + `RENAME THE FILE in your vault to a single path component, then re-run sync.`,
  );
}
const body = await readMdBody(from.blob, from.p, present);
await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
```

- [ ] **Step 4: Run and verify**

Run: `npx jest tests/integration/cloud-sync-adopt.test.ts && npx jest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/sync-run.ts tests/
git commit -m "feat(#36): the adopt guard is scoped to the cloud receiver, in the caller (behaviors 26,26b,26e,26f)"
```

---

## Task 12: `reconcileCloudBase` — the four-cell relocate / refuse / skip table

**Spec:** §3.5.1 placement 2, §3.5.1b **row 3**. **Behaviors:** 26d, 26d2, 26d3, 26d4.

⚠ **This task is where rounds 17 and 18 both put a Blocking. Read §3.5.1 placement 2 in full before starting.** `newBase` has **TWO** producers (a ternary at `reconcile-serial.ts:152-154`), and this function writes its row **through the seam** (T9) at `:324`. A guard here that merely *permits* a write the seam then refuses copies every paid blob and fails anyway.

**Files:**
- Modify: `lib/cloud-sync/reconcile-serial.ts` (the `SerialReconcileResult` union at `:69-81`; the guard before the copy phase at `~:197`)
- Test: `tests/lib/cloud-sync/reconcile-serial.test.ts`

**Interfaces:**
- Consumes: `isServableSummaryKey` (T4).
- Produces: two new `SerialReconcileResult` variants — `{ ok: false; reason: 'unservable-base'; key: string; origin: 'vault-filename' | 'cloud-key' }` and `{ ok: true; action: 'skipped-unservable' }`.

- [ ] **Step 1: Write the failing tests — one per cell**

```ts
it('behavior 26d — servable -> UNSERVABLE: REFUSED in memory, nothing copied, old base intact', async () => {
  const res = await reconcileCloudBase({ /* old: servable, new: unservable */ });
  expect(res).toMatchObject({ ok: false, reason: 'unservable-base', origin: 'vault-filename' });
  expect(cloudBlob.copy).not.toHaveBeenCalled();
  expect(await cloudBlob.get(cloudP, `${oldBase}.md`)).not.toBeNull();
});

it('behavior 26d2 — unservable -> unservable: SKIPPED, and copyToLocal then hydrates', async () => {
  const res = await reconcileCloudBase({ /* local: serial but NO summaryMd; cloud: unservable */ });
  expect(res).toEqual({ ok: true, action: 'skipped-unservable' });
  expect(cloudBlob.copy).not.toHaveBeenCalled();        // no copy
  expect(cloudStore.updateVideoFields).not.toHaveBeenCalled();   // and NO seam write
  const report = await runSync({ /* same fixture */ });
  expect(report.errors).toContainEqual(expect.objectContaining({ videoId: ID }));  // visible
  expect(await localBlob.get(localP, cloudKey)).not.toBeNull();  // the paid summary is recovered
});

it('behavior 26d3 — arm B still REFUSES when the old base was servable', async () => {
  // A servable cloud key whose renumbering by applySerial pushes it past 131 code points.
  const res = await reconcileCloudBase({ /* cloud: 128 ASCII + .md, local serial widens it */ });
  expect(res).toMatchObject({ ok: false, reason: 'unservable-base', origin: 'cloud-key' });
  expect(res.origin).toBe('cloud-key');   // NOT 'vault-filename' — there is no vault file here
});

it('behavior 26d4 — unservable -> SERVABLE: RELOCATES. A genuine repair', async () => {
  const res = await reconcileCloudBase({ /* old: unservable, new: servable */ });
  expect(res).toMatchObject({ ok: true, action: 'relocated' });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx jest tests/lib/cloud-sync/reconcile-serial.test.ts`
Expected: FAIL — no such variants.

- [ ] **Step 3: Extend the union and implement the table**

```ts
export type SerialReconcileResult =
  | { ok: true; action: 'agreed' }
  | { ok: true; action: 'skipped-unservable' }            // NEW — 26d2
  | { ok: true; action: 'relocated'; from: string; to: string; copied: number; cleanupFailures: number }
  | { ok: false; reason: 'unservable-base'; key: string; origin: 'vault-filename' | 'cloud-key' }  // NEW
  | /* …the ten existing refusal variants, unchanged… */;
```

```ts
// Placed with the existing target-occupied / unsupported-artifacts refusals, BEFORE the copy
// phase, so nothing is copied and nothing is deleted.
//
// `origin` is derived from the SAME predicate the ternary at :152 branches on — TRUTHINESS,
// not nullishness. `summaryMd: ''` takes arm B in the code, and a nullish test would report
// 'vault-filename' for a video that has no vault file (round-18 L1).
const origin = localVideo.summaryMd ? 'vault-filename' : 'cloud-key';
const oldServable = isServableSummaryKey(`${oldBase}.md`);
const newServable = isServableSummaryKey(`${newBase}.md`);

if (!newServable) {
  if (oldServable) {
    // Protect a WORKING advertisement from being relocated into unreachability.
    return { ok: false, reason: 'unservable-base', key: `${newBase}.md`, origin };
  }
  // Both unservable: relocating buys nothing (the old key was already unreachable) and costs
  // everything — the seam at :324 would refuse the row AFTER every paid blob had been copied,
  // and the throw would stop reconcileClassA -> copyToLocal from ever hydrating the artifact.
  // SKIP, visibly. Round-18 B1.
  return { ok: true, action: 'skipped-unservable' };
}
// unservable -> servable falls through and RELOCATES: a genuine repair, and the seam accepts it.
```

In `sync-run.ts`, add the explicit refusal branch (round-16 M1 — the generic tail cannot name a repair) and make `skipped-unservable` push to `report.errors` rather than throwing:

```ts
if (rec.ok && rec.action === 'skipped-unservable') {
  // ⚠ Round-1 H4: this arm returns ok:true, so the caller ADVANCES THE BASELINE and run 2 sees an
  // agreed video — the divergence would be reported once and then be permanently silent, which is
  // worse than never reporting it. The report entry must therefore be emitted from a state the
  // baseline does not erase: re-derive it each run from the row itself (cloud summaryMd unservable
  // AND local has none), not from this branch having been taken.
  report.errors.push({ videoId: id, message:
    `base relocation skipped: both the current and target keys are unservable, so the serials `
    + `stay diverged. The summary is still reachable locally; the cloud key needs a manual repair.` });
} else if (!rec.ok && rec.reason === 'unservable-base') {
  throw new Error(rec.origin === 'vault-filename'
    ? `base reconciliation refused for ${id}: rename the vault file ${rec.key} to a servable single path component, then re-run sync`
    : `base reconciliation refused for ${id}: the cloud key ${rec.key} cannot be relocated — it is unservable and has no local counterpart to rename`);
}
```

- [ ] **Step 4: Run all four cells, then the whole suite**

Run: `npx jest tests/lib/cloud-sync/ && npx jest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/cloud-sync/reconcile-serial.ts lib/cloud-sync/sync-run.ts tests/
git commit -m "feat(#36): reconcileCloudBase relocates, refuses or SKIPS per the four-cell table (behaviors 26d-26d4)"
```

---

## Task 13: The additive-create protocol, and the §4 gate derivation

**Spec:** §3.6.2. **Behaviors:** 18, 18b, 18c, 18c2, 18e, 18g, 18h, 18i, 18k, 19, 20.

**Files:**
- Modify: `lib/cloud-sync/sync-run.ts` (`copyAdditiveVideo`, `transferClassA`)
- Create: `scripts/check-encoder-gate-sql.py`
- Test: `tests/integration/cloud-sync-additive.test.ts`

**Interfaces:** Consumes `promoteIfAbsent` (T6), `isServableSummaryKey` (T4). Produces nothing new.

- [ ] **Step 1: Write the failing tests**

```ts
it('behavior 18 — occupant is BYTE-IDENTICAL under the aliasing form: SUCCEEDS, file untouched', async () => {
  // The crash-resume case. Refusing here stalls the video forever.
  await seed(NFC_KEY, 'body');
  await expect(copyAdditiveVideo(/* same bytes, NFD form of the key */)).resolves.toBeUndefined();
  expect(await readdirNames()).toContain(NFC_KEY);        // the STORED name is preserved
});

it('behavior 18b/18c — occupant has DIFFERENT bytes: REFUSES, occupant intact', async () => {
  await seed(KEY, 'occupant');
  await expect(copyAdditiveVideo(/* different bytes */)).rejects.toThrow();
  expect((await blob.get(P, KEY))!.toString('utf8')).toBe('occupant');
});

it('behavior 18c2 — a read-back of `absent` REFUSES: that is a fault, not a resume', async () => {
  await expect(copyAdditiveVideo(/* read-back returns absent */)).rejects.toThrow();
});

it('behavior 19 — an UNREADABLE read is treated as OCCUPIED', async () => {
  await expect(copyAdditiveVideo(/* read-back throws */)).rejects.toThrow();
});

it('behavior 18i — canonicallyEqualName is a PROPER SUBSET of the volume alias relation', () => {
  expect(canonicallyEqualName('café.md'.normalize('NFC'), 'café.md'.normalize('NFD'))).toBe(true);
  expect(canonicallyEqualName('Ａ.md', 'A.md')).toBe(false);   // fullwidth A is NOT an alias
});

it('behavior 18k — canonicallyEqualName(null, key) is FALSE, so a loser with no summaryMd probes', () => {
  expect(canonicallyEqualName(null, 'a.md')).toBe(false);
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx jest tests/integration/cloud-sync-additive.test.ts`
Expected: FAIL — today's code overwrites unconditionally.

- [ ] **Step 3: Implement the ADDITIVE protocol**

`putStaged` → **verify the read-back hash** → `promoteIfAbsent` → read back and classify: **equal** →
success; **different** → refuse; **absent** → refuse (a fault, not a resume); **unreadable** → treat
as occupied, refuse (behavior 19 — an unreadable read is never absence).

- [ ] **Step 4: Implement the CLASS-A LOSER-RECORD GUARD — behaviors 18g / 18h**

⛔ **Round-1 Blocking.** The v1 plan named 18g/18h and gave **no step for them**. `transferClassA`
does not even take the loser's video, and today's code overwrites the destination unconditionally:

```ts
// lib/cloud-sync/sync-run.ts:371-372 — the signature TODAY. No loserVideo.
async function transferClassA(
  winner: Side, loser: Side, winnerVideo: Video, videoId: string,
): Promise<{ mdHash: string; verified: boolean }> {
// :394 — and it writes, unconditionally:
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

**Without this guard a Class-A transfer writes the winner's body over an address the loser's row does
not claim — destroying a paid artifact.** §3.6.2 R3. Three edits:

```ts
// 1. The signature gains the loser's record.
async function transferClassA(
  winner: Side, loser: Side, winnerVideo: Video, videoId: string, loserVideo: Video | null,
): Promise<{ mdHash: string; verified: boolean }> {

// 2. Before the write at :394 — only the NON-OWNED branch probes.
if (!canonicallyEqualName(loserVideo?.summaryMd ?? null, key)) {
  // The loser's row does not claim this address. `tryGet`, never `get`: on Supabase a null from
  // `get` is absent-OR-denied-OR-network, and treating that as "free to overwrite" is how a paid
  // artifact dies. `unreadable` counts as OCCUPIED (behavior 19).
  const dest = await loser.blob.tryGet(loser.p, key);
  if (dest.ok || dest.reason === 'unreadable') {
    throw new Error(
      `transferClassA: ${videoId} would overwrite ${JSON.stringify(key)} on the loser, whose row `
      + `claims ${JSON.stringify(loserVideo?.summaryMd ?? null)}. Refusing.`,
    );
  }
}
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

```ts
// 3. BOTH call sites pass it — the loser's video is the opposite side's record.
// :782  copyToCloud → transferClassA(localSide, cloudSide, lv, id, cv)
// :793  copyToLocal → transferClassA(cloudSide, localSide, cv, id, lv)
```

- [ ] **Step 5: Assert both branches**

```ts
it('behavior 18g — the loser row NAMES this address: overwrites', async () => {
  await expect(transferClassA(winner, loser, wv, ID, { ...lv, summaryMd: KEY })).resolves.toBeDefined();
});

it('behavior 18h — loser row names a DIFFERENT address, destination OCCUPIED: REFUSES', async () => {
  await seed(KEY, 'someone else');
  await expect(transferClassA(winner, loser, wv, ID, { ...lv, summaryMd: 'other.md' })).rejects.toThrow(/Refusing/);
  expect((await blob.get(P, KEY))!.toString('utf8')).toBe('someone else');
});

it('behavior 18h — loser row names a DIFFERENT address, destination UNOCCUPIED: WRITES', async () => {
  await expect(transferClassA(winner, loser, wv, ID, { ...lv, summaryMd: 'other.md' })).resolves.toBeDefined();
});

it('behavior 19 — an UNREADABLE destination counts as OCCUPIED', async () => {
  await expect(transferClassA(winner, unreadableLoser, wv, ID, { ...lv, summaryMd: 'other.md' }))
    .rejects.toThrow(/Refusing/);
});
```

- [ ] **Step 6: Write the §4 gate derivation script (behavior 20) — WITH A BODY**

⛔ **Round-1 Blocking, found by BOTH halves.** The v1 plan gave this script a docstring and no body,
and its own Self-Review called that "the one under-specified step". **Flagging is not enough here**:
an engineer creates a docstring-only file, `--self-test` exits 0, and behavior 20 — the instrument
whose whole job is proving the §4 SQL is not a hand-copied class — passes **vacuously**. That is a
green check over the wrong subject, the exact shape `portable-practices.md` §1 and §2 record.

**The hard part is the mapping, and it is what the script must pin:** `SAFE` is a JS regex literal
(`/^[A-Za-z0-9._-]+$/`) and the gate is a Postgres `~` pattern. They are different languages for the
same character class, so the check is *"the CHARACTER SET matches"*, not *"the strings match"*.

```python
#!/usr/bin/env python3
"""Behavior 20 — the section-4 gate's SQL predicate derives from the encoder, not from memory.

Reads the JS character class out of lib/storage/supabase/encode-segment.ts and the SQL `~` class
out of the gate query, normalises both to a SET of characters, and fails if they differ.

Exits 2 — NOT 0 — if either side cannot be located. A check that cannot reach its subject has NOT
passed (portable-practices section 2).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENCODER = os.path.join(ROOT, "lib/storage/supabase/encode-segment.ts")
GATE = os.path.join(ROOT, "docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md")

JS_SAFE = re.compile(r"export const SAFE\s*=\s*/\^\[([^\]]+)\]\+\$/")
SQL_CLASS = re.compile(r"~\s*'\^\[([^\]]+)\]\+\$'")

def charset(cls: str) -> set:
    """Expand a character class body to the SET it denotes. `A-Z` -> 26 chars."""
    out, i = set(), 0
    while i < len(cls):
        if i + 2 < len(cls) and cls[i + 1] == "-":
            out |= {chr(c) for c in range(ord(cls[i]), ord(cls[i + 2]) + 1)}
            i += 3
        else:
            out.add(cls[i]); i += 1
    return out

def main() -> int:
    for path in (ENCODER, GATE):
        if not os.path.isfile(path):
            print(f"  CANNOT READ {path} -> TREAT THIS AS NOT RUN"); return 2
    js = JS_SAFE.search(open(ENCODER, encoding="utf8").read())
    sql = SQL_CLASS.search(open(GATE, encoding="utf8").read())
    if not js:
        print("  SAFE not found in the encoder -> NOT RUN"); return 2
    if not sql:
        print("  no SQL character class found in the gate -> NOT RUN"); return 2
    a, b = charset(js.group(1)), charset(sql.group(1))
    if a != b:
        print(f"  DRIFT: only in JS {sorted(a - b)!r} | only in SQL {sorted(b - a)!r}"); return 1
    print(f"  PASS - both sides denote the same {len(a)} characters"); return 0

def self_test() -> int:
    cases = [("A-Za-z0-9._-", "A-Za-z0-9._-", True), ("A-Z", "A-Y", False),
             ("a-c", "abc", True), ("._-", "._", False)]
    bad = 0
    for x, y, same in cases:
        ok = (charset(x) == charset(y)) == same
        print(f"  {'ok  ' if ok else 'FAIL'} charset({x!r}) == charset({y!r}) is {same}")
        bad += 0 if ok else 1
    print(f"\n  {'PASS' if not bad else f'{bad} FAILURE(S)'}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
```

**⚠ If §4's SQL does not currently express its predicate as a `~ '^[...]+$'` class, this script exits
2 and that is CORRECT** — it means the gate and the encoder are not yet expressed in comparable form,
which is the drift the behavior exists to prevent. Fix the SQL, not the script.

- [ ] **Step 7: Run everything**

```bash
npx tsc --noEmit && npx jest && python3 scripts/check-encoder-gate-sql.py --self-test
for c in check-docs check-roadmap-consistency check-test-counts check-producer-enumeration; do
  python3 scripts/$c.py || echo "RED: $c"; done
```

- [ ] **Step 8: Commit**

```bash
git add lib/cloud-sync/sync-run.ts scripts/check-encoder-gate-sql.py tests/
git commit -m "feat(#36): the additive-create protocol and the section-4 gate derivation (behaviors 18-19, 20)"
```

---

## Task 14: End-to-end — the bug in backlog #36 is actually fixed

**Behaviors:** 14, 15, 16, 23.

**Files:** Test only — `tests/integration/korean-title-e2e.test.ts`

- [ ] **Step 1: Write the tests**

```ts
it('behavior 14 — a KOREAN-titled video ingests and serves 200, and the ledger is unmoved', async () => {
  const before = await ledgerTotal();
  const { videoId } = await ingest({ title: '한국어 강의' });
  expect((await serveSummary(videoId)).status).toBe(200);
  expect(await ledgerTotal()).toBe(before + EXPECTED_ONE_SUMMARY_COST);   // charged once, not lost
});

it('behavior 15 — an NFD accented-Latin title ingests and serves 200', async () => {
  const { videoId } = await ingest({ title: 'Café Introduction'.normalize('NFD') });
  expect((await serveSummary(videoId)).status).toBe(200);
});

it('behavior 16 — space / emoji / astral-at-the-boundary ingest and serve 200, and the vault filename is WELL-FORMED ON DISK', async () => {
  for (const title of ['hello world', 'intro \u{1F600}', 'a'.repeat(59) + '\u{20000}']) {
    const { videoId, vaultPath } = await ingestLocal({ title });
    expect((await serveSummary(videoId)).status).toBe(200);
    const onDisk = (await fs.readdir(dirname(vaultPath))).find((n) => n.includes('_'));
    expect(onDisk).toBe(basename(vaultPath));      // byte-for-byte; NO U+FFFD
  }
});

it('behavior 23 — a title ending in the U+2488..U+249B or U+1F100 class ingests and serves 200', async () => {
  for (const ch of ['⒈', '⒛', '\u{1F100}']) {
    const { videoId } = await ingest({ title: `Lesson ${ch}` });
    expect((await serveSummary(videoId)).status).toBe(200);
  }
});
```

- [ ] **Step 2: Run, verify green, commit**

```bash
npx jest tests/integration/korean-title-e2e.test.ts
git add tests/integration/korean-title-e2e.test.ts
git commit -m "test(#36): end-to-end — a title in any language ingests and serves (behaviors 14,15,16,23)"
```

---

## Task 15: ADR-0009 and the roadmap close-out

**Files:** Create `docs/adr/0009-logical-unicode-physical-ascii.md`; modify `docs/roadmap-to-launch.md`, `docs/backlog.md`.

- [ ] **Step 1: Write ADR-0009** — *logical keys are Unicode, physical keys are ASCII, the seam owns the mapping.* Record the decision, the three user decisions (①②③), premises P1–P8 with their falsifiers, and that **ADR-0008 survives** (`objectKey` encodes only `key`, so both physical keys stay under the same grant). Task #91.
- [ ] **Step 2: Tick backlog #36 and the roadmap step in the SAME commit as the work** — per Phase 5, the merge tick is written before the PR is opened.
- [ ] **Step 3: Run every ratchet, by exit code.**
- [ ] **Step 4: Commit, open the PR, notify. DO NOT MERGE — merging is a human gate.**

---

## Self-Review — v2, and what v1's self-review missed

**v1's self-review checked the plan against ITSELF** — spec coverage, placeholders, internal type
consistency — and passed. Round 1 then returned **25 findings**, 8 of them Blocking, because the one
question it never asked was *"does this compile against the repo?"* That question is now a Global
Constraint, and every snippet in v2 was verified against the file it will live in.

**Round-1 dispositions** (Post-Plan Gate 3/5 — a Medium or Low without a written disposition is how a
carry-forward with no destination happens):

| # | Finding | Disposition |
|---|---|---|
| B1 | Vitest → **Jest 30** | FIXED — 33 commands + 3 `vi.fn()`, Tech Stack corrected |
| B2 | `objectKey` dropped `p.id` and `assertLogicalKey` | FIXED — T2 now quotes the real method and changes one line |
| B3 | `list` called a nonexistent `rawList`, wrong slice offset | FIXED — real `collectObjectPaths`, `ownerRoot + physicalPrefix` |
| B4 | T1's property assertion fails on correct code | FIXED — asserts the PHYSICAL alphabet |
| B(cx) | T6 `ref.key` | FIXED — `ref.finalKey` |
| B(cx) | Class-A ownership guard had no step | FIXED — **new T13 step 4**, signature + both call sites + 4 tests |
| B(cx) | gate script was a docstring | FIXED — full body, `--self-test`, exit 2 on unreachable |
| H1 | 7 helpers missing | FIXED — **new Task 0** |
| H2 | `canonicallyEqualName` unimplemented | FIXED — Task 0, with 18i/18k |
| H3 | T8 refusal in the ship arm only; conflated re-read | FIXED — gates ship AND delete; uses the already-read envelope |
| H4 | SKIP visible one run then silent | FIXED — re-derived per run, not from the branch |
| M(cx) | seam predicate stricter than spec | **DECIDED** — scoped to `status === 'promoted'`; a guard stricter than its spec is one nobody agreed to |
| M(cx) | ratchet loop masked exit codes | FIXED — `set -e`, no `\|\| echo` |
| M1 | `statusCode: 409` dropped, 22 assertions | FIXED — preserved, with a warning to read first |
| M5 | `deletePrefix` listed, never modified | FIXED — named in T2 step 3 |
| M7 | commit after a slice narrower than blast radius | FIXED — T4 runs `npm test` |
| L1 | T7's count recalled | **ACCEPTED** — recounted this session: **41** (3 production + 38 test), and the count is now in the plan with its method |
| L2 | sweeps stride past most of the space | FIXED — labelled a smoke sweep; completeness claims use stride 1 |
| M2, M3, M4, M6, L3, L4 | assorted | **DEFERRED to round 2** — each needs a file read I have not done; they are recorded here so round 2 can check I did them, not so they can be forgotten |

**Type consistency, re-verified:** `isServableSummaryKey` (T4) used identically in T5/T9/T10/T11/T12;
`promoteIfAbsent(ref: StagedRef)` (T6) in T13; `ModelEnvelopeWrite` (T7) in T8; `videoDataPayload`
(T9) module-private, matching §3.5.1b row 1; `canonicallyEqualName` (T0) in T13.

**The one thing a fresh implementer must not do:** install any guard on the local/vault path.
Decision ① and round-16 B1.

**Known incomplete:** six round-1 findings are deferred above. **v2 is not claimed to be converged** —
it is claimed to have fixed every Blocking and High, which is what round 2 exists to test.
