# Slice A — Corrections in the Cloud (Attended Path) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A cloud user edits corrections, presses the button, and gets a corrected summary — the same behaviour as local.

**Architecture:** A new store-agnostic `lib/corrections/apply-core.ts` owns the correction pipeline (strip callout → `fixSummary` → structural validation → `extractQuickView` → re-insert). `app/api/videos/[id]/regenerate/route.ts` gains a cloud branch that resolves a Supabase principal and writes the corrected body with `blobStore.put`. Magazine-model staleness is **derived** from the envelope's existing `sourceMdHash` via one new conjunct in `isFresh` — nothing is deleted and the correction path writes no envelope.

**Tech Stack:** Next.js (see `AGENTS.md` — read `node_modules/next/dist/docs/` before writing route code), TypeScript, Supabase (Postgres + Storage), Gemini via `lib/gemini.ts`, Jest.

**Spec:** `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md`
**Reviews:** `docs/reviews/spec-corrections-in-cloud-r{1,2,3,4,5}-{codex,claude}.md` and `…-r5-bare-press-write.md`

---

## Global Constraints

- **Read the Next.js docs in `node_modules/next/dist/docs/` before writing any route code.** This version has breaking changes (`AGENTS.md`).
- **`fixSummary` runs ⟺ the request's corrections are non-empty after trimming.** The apply input is the *request's* corrections; the stamp input is a different quantity. Never use one word for both. (spec §3)
- **Caps are applied through `withCaps` by passing a `CloudGeminiCaps` OBJECT as the second argument.** `withCaps` returns `base` unchanged when `caps` is undefined (`lib/gemini.ts:41`) — naming only the constant ships an uncapped call that reads correct in the diff. On the **local** branch `caps` is absent by design.
- **The corrected body is written with `blobStore.put`** (`lib/storage/blob-store.ts:69`), **never** `writeArtifact`/`putStaged`→`promote`: the key never changes, so create-if-absent (`supabase-blob-store.ts:120-123`) would discard the correction.
- **Negative tests assert WHICH error**, never "any error".
- **Anything longer than a line goes in a file** — `git commit -F`, `gh --body-file`. A backtick inside a double-quoted bash string is command substitution.
- **Branch + PR, always.** Merging is a human gate.
- `export const maxDuration = 420` on the regenerate route. It bounds *the work*, not *the request* — nothing on Fly enforces it.

---

## ⚠ Hard ordering constraints — read before scheduling

**The chain is `T3 → T10 → T4`. Task 4 lands last of the three.**

Both constraints have the same shape, and it is the shape that makes them easy to lose: **Task 4 is
the task that arms a mechanism, and Tasks 3 and 10 are the tasks that make that mechanism safe.**
Arming first is not "a slightly worse order" — it is a live defect for as long as the gap lasts.

Task 4 adds the `sourceMdHash` conjunct to `isFresh`. Two things change the moment it lands: any
body-hash change starts invalidating the magazine model, and a corrected document stops
short-circuiting at `serve-doc.ts:78-79` and starts falling through the reserve state machine on
every serve until a regeneration succeeds.

| Order | What it prevents | Cost of getting it wrong |
|---|---|---|
| **T3 before T4** | T3 makes the body write conditional, so a *bare* press stops moving the body hash | Ship 4 first and **every bare press costs ~6¢** — round 5's Blocking, live |
| **T10 before T4** | T10 gives the owner's page a stale-model fallback on `attempts_exhausted` and `at_capacity`, which T4 makes reachable for the first time | Ship 4 first and a failing regeneration returns **503 for the rest of the UTC day** — attempts are keyed `(owner_id, doc_key, day)` with `max_serve_attempts` default 5 (`0012_serve_model_charge.sql:13,21,80`) — while a readable model sits in the bucket |

All three may ship in **one PR**; the order must hold *within* it. T10 has no dependency on T3, so
`T3 → T10 → T4` and `T10 → T3 → T4` are both fine — what must not happen is T4 before either.

*(T10 was originally scheduled after T4. Promoted here 2026-08-24 rather than left as a note inside
Task 10, because a coupling written inside a task is a coupling that gets scheduled around.)*

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `lib/corrections/structural-validation.ts` | **Create.** Pure comparator: pre/post H2 sequence + `▶` tuples + H1/frontmatter presence. Throws a named error. No I/O, no Gemini | T1 |
| `lib/corrections/apply-core.ts` | **Create.** Store-agnostic pipeline. In `{ md, corrections, tags, signal }`, out `{ content, tldr, takeaways }` | T2 |
| `lib/gemini.ts` | **Modify.** `fixSummary` gains `caps`, `signal` (three sites), and an exported input-preflight | T5 |
| `app/api/videos/[id]/regenerate/route.ts` | **Modify.** Conditional file write + conditional stamp (T3); annotations surface (T6); length cap + 413 (T7); cloud branch (T8); spend recording (T9) | T3, T6, T7, T8, T9 |
| `lib/html-doc/read-model.ts` | **Modify.** `isFresh` + `readFreshMagazineModel` gain `currentMdHash` | T4 |
| `lib/html-doc/serve-doc.ts` | **Modify.** Pass `mdHash(mdBody)` at both call sites; extend the stale fallback (r5 H1) | T4, T10 |
| `components/CorrectionsPanel.tsx`, `components/VideoMenu.tsx` | **Modify.** Reachable in cloud mode; render the outcome discriminator | T11 |
| `tests/lib/html-doc/read-model.test.ts` | **Modify.** Retire the §3.5.1 tripwire with a pointer; add current/stale/**absent** `sourceMdHash` cases | T4 |

---

## Task list (12), with the reviewer's gate for each

| # | Task | A reviewer could reject this alone because… |
|---|---|---|
| 1 | Structural validator | the comparison is inexact or repairs instead of throwing |
| 2 | `apply-core` pipeline | `tags`/`signal` dropped, or ordering wrong |
| 3 | **Bare press stops rewriting the file, and stops recomputing `mdCorrectionsHash`** | the §4.3 defect survives, or the write guard is wrong |
| 4 | **(e): `isFresh` learns `sourceMdHash`** + retire the tripwire + fixtures | absent-hash not treated as *cannot prove stale*, or no mutation-check |
| 5 | `fixSummary` caps + signal ×3 + preflight | caps object missing → uncapped call |
| 6 | Corrections written via `updateVideoAnnotations`, read-before-write | the stamp moves on a no-op, or the Supabase clear is still a no-op |
| 7 | Server-side length cap + 413 over-cap refusal + `maxDuration` | an already-long row is bricked, or the refusal is a 500 |
| 8 | The cloud branch | `writeArtifact` used instead of `put`, or resolution outside the try |
| 9 | Post-hoc spend recording | records an estimate rather than actual, or records before the call |
| 10 | r5 H1 — stale fallback for the other non-ok statuses | the owner's page 503s with a readable model in the bucket |
| 11 | UI reachable in cloud + outcome discriminator | a no-op press reads as a bug |
| 12 | Falsifiers + mutation-check | a falsifier passes on a wrong implementation |

---

## Out of the 12 — must not be forgotten

Four things the spec asks for that are **not** tasks. Each is recorded here because a plan that omits
them silently reads as complete. Tracked as task **#130**.

| | Why it is not one of the 12 |
|---|---|
| **What actually bounds the request in prod** (§5.4) | Not code. `maxDuration = 420` is kept for portability but is **inert** on this deployment — standalone output under Fly, no adapter reads it. The real bound (Fly proxy / idle timeout / client `fetch`) is **NOT VERIFIED** and needs a live run against the deployed app |
| **Count the already-drifted envelopes before (e) ships** (§2) | Not code. §2 gates a staged rollout on this number. Read-only via `CLAUDE_RO_DATABASE_URL`: envelopes whose `sourceMdHash` is present and differs from the current body hash. ⚠ Per `separate-the-rule-from-the-fetch`: the *logic* does not need a database even though the *fetch* does — do not let the credential requirement make the whole thing untestable |
| **Does a cloud rendered-HTML BLOB cache exist at all?** (§8.1 item 2) | Code, but unassigned — and it is a *question* before it is a task. T8 nulls the `summaryHtml` **index field**; nobody has checked for a cached rendered **artifact**, and (e) does not cover one because it has no tie to the body hash. **This is the same "what else touches this?" class as both round-4 Blockings** |
| **Panel copy for the structural-validation throw and for abort** (§8.1 item 3) | Code, but unassigned. T11 covers the 413 and `no-corrections` only. Two of the four new failure classes have no specified message |

---

## ⏸ Deferred structural edit — do NOT apply until task #129 is answered

The coordinator asked for T9's usage-capture steps to be folded into T5, on the grounds that
`fixSummary`'s return type is T5's deliverable and T5 should not ship a signature T9 immediately
rewrites. **That instruction is withdrawn until #129 resolves**, because it is only correct under one
of the three options:

| #129 answer | What happens to usage capture |
|---|---|
| **(b) accept one narrow RPC migration** | Fold it into T5 as originally instructed — slice A keeps both halves |
| **(a) move recording to slice C (#61)** | Usage capture leaves slice A **entirely**. Folding it into T5 would be actively wrong |
| **(c) log-only** | Fold into T5, but T9's sink becomes a structured log line, not a ledger write |

Folding now would have to be undone in two of the three cases.

---

## Tasks

Each task ends with an independently testable deliverable and a commit. Run the unit suite with
`npx jest <path>`; the whole suite is `npx jest` (268 suites / 2,722 tests / ~25 s at the time of
writing).

---

### Task 1: Structural validator

A correction must not restructure the document. `generateSummary` may *repair* structure
(`ensureSectionTimestamps`, `gemini.ts:391-403`, called at `:401`) because it authored it; a
correction did not, so a structural change means the model disobeyed and the result is discarded.
This task is a pure comparator — no I/O, no Gemini, no storage.

**Files:**
- Create: `lib/corrections/structural-validation.ts`
- Test: `tests/lib/corrections/structural-validation.test.ts`

**Interfaces:**
- Consumes: `parseSections(body: string): ParsedSection[]` from `lib/html-doc/parse.ts` (already
  exported at `parse.ts:42`). `ParsedSection` is
  `{ numeral: string | null; title: string; prose: string; timeRange?: SectionTimeRange | null }`
  and `SectionTimeRange` is `{ startSec: number; endSec: number; label: string; url: string }`
  (`lib/html-doc/types.ts:4-18`).
- Produces:
  - `class StructuralValidationError extends Error` with `readonly reason: StructuralFailureReason`
  - `type StructuralFailureReason = 'missing-frontmatter' | 'missing-h1' | 'section-count' | 'section-title' | 'section-timestamp'`
  - `function assertStructurePreserved(before: string, after: string): void` — returns `void`,
    throws `StructuralValidationError` otherwise.

- [ ] **Step 1: Write the failing test**

Create `tests/lib/corrections/structural-validation.test.ts`:

```ts
import {
  assertStructurePreserved,
  StructuralValidationError,
} from '@/lib/corrections/structural-validation';

const DOC = `---
video_id: abc12345678
lang: EN
---

# A Title

**Channel:** Ch | **Duration:** 10:00 | **URL:** https://www.youtube.com/watch?v=abc12345678

---

## 1. Intro

▶ [0:00–5:00](https://www.youtube.com/watch?v=abc12345678&t=0s)

Original prose one.

---

## Conclusion

▶ [5:00–10:00](https://www.youtube.com/watch?v=abc12345678&t=300s)

Original prose two.
`;

describe('assertStructurePreserved', () => {
  it('accepts a prose-only rewrite', () => {
    const after = DOC.replace('Original prose one.', 'Corrected prose one.');
    expect(() => assertStructurePreserved(DOC, after)).not.toThrow();
  });

  it('rejects a renamed H2 with reason section-title', () => {
    const after = DOC.replace('## 1. Intro', '## 1. Introduction');
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-title' }));
  });

  it('rejects a dropped section with reason section-count', () => {
    const after = DOC.slice(0, DOC.indexOf('## Conclusion'));
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-count' }));
  });

  it('rejects a moved ▶ start second with reason section-timestamp', () => {
    const after = DOC.replace('&t=300s', '&t=301s');
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'section-timestamp' }));
  });

  it('rejects a dropped H1 with reason missing-h1', () => {
    const after = DOC.replace('# A Title\n', '');
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'missing-h1' }));
  });

  it('rejects dropped frontmatter with reason missing-frontmatter', () => {
    const after = DOC.replace(/^---\nvideo_id: abc12345678\nlang: EN\n---\n\n/, '');
    expect(() => assertStructurePreserved(DOC, after))
      .toThrow(expect.objectContaining({ reason: 'missing-frontmatter' }));
  });

  it('throws StructuralValidationError, not a bare Error', () => {
    const after = DOC.replace('## 1. Intro', '## 1. Introduction');
    expect(() => assertStructurePreserved(DOC, after)).toThrow(StructuralValidationError);
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails for the right reason**

Run: `npx jest tests/lib/corrections/structural-validation.test.ts`
Expected: FAIL — `Cannot find module '@/lib/corrections/structural-validation'`.

- [ ] **Step 3: Write the implementation**

Create `lib/corrections/structural-validation.ts`:

```ts
import { parseSections } from '@/lib/html-doc/parse';

/** Why the post-correction document was rejected. Named so a negative test can assert WHICH
 *  failure it provoked rather than "any error" (a test that catches any error passes on a typo). */
export type StructuralFailureReason =
  | 'missing-frontmatter'
  | 'missing-h1'
  | 'section-count'
  | 'section-title'
  | 'section-timestamp';

export class StructuralValidationError extends Error {
  readonly reason: StructuralFailureReason;
  constructor(reason: StructuralFailureReason, message: string) {
    super(message);
    this.name = 'StructuralValidationError';
    this.reason = reason;
  }
}

/**
 * Throw unless `after` has the SAME structure as `before`: identical H2 sequence (count, order and
 * exact text, including the leading ordinal), identical `▶` `(startSec, endSec)` tuples, and an H1
 * plus frontmatter still present.
 *
 * NO REPAIR, deliberately. `generateSummary` repairs (`ensureSectionTimestamps`, gemini.ts:391-403)
 * because it authored the structure. A correction did not: a structural change means the model
 * disobeyed its prompt (`gemini.ts:480` — "do NOT add, remove, or restructure any sections"), and the
 * result is discarded rather than patched up.
 *
 * `before` is the PRE-correction document AFTER the quick-view callout has been stripped, so both
 * sides are compared in the same shape.
 */
export function assertStructurePreserved(before: string, after: string): void {
  if (!after.startsWith('---\n')) {
    throw new StructuralValidationError(
      'missing-frontmatter',
      'corrected document does not start with a YAML frontmatter delimiter',
    );
  }
  if (!/^#\s+\S/m.test(after)) {
    throw new StructuralValidationError('missing-h1', 'corrected document has no H1 heading');
  }

  const a = parseSections(before);
  const b = parseSections(after);

  if (a.length !== b.length) {
    throw new StructuralValidationError(
      'section-count',
      `corrected document has ${b.length} sections, expected ${a.length}`,
    );
  }

  for (let i = 0; i < a.length; i++) {
    if (a[i].numeral !== b[i].numeral || a[i].title !== b[i].title) {
      throw new StructuralValidationError(
        'section-title',
        `section ${i} heading changed: "${a[i].numeral ?? ''} ${a[i].title}" → "${b[i].numeral ?? ''} ${b[i].title}"`,
      );
    }
    const ta = a[i].timeRange ?? null;
    const tb = b[i].timeRange ?? null;
    if ((ta === null) !== (tb === null)) {
      throw new StructuralValidationError(
        'section-timestamp',
        `section ${i} ▶ timestamp ${ta === null ? 'appeared' : 'disappeared'}`,
      );
    }
    if (ta !== null && tb !== null && (ta.startSec !== tb.startSec || ta.endSec !== tb.endSec)) {
      throw new StructuralValidationError(
        'section-timestamp',
        `section ${i} ▶ tuple changed: (${ta.startSec},${ta.endSec}) → (${tb.startSec},${tb.endSec})`,
      );
    }
  }
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `npx jest tests/lib/corrections/structural-validation.test.ts`
Expected: PASS, 7 tests.

- [ ] **Step 5: Typecheck**

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add lib/corrections/structural-validation.ts tests/lib/corrections/structural-validation.test.ts
git commit -m "feat(#23): structural validator for corrections — compare, never repair"
```

---

### Task 2: `apply-core` — the store-agnostic correction pipeline

The whole correction, with no knowledge of where the markdown came from or where it goes. The route
calls this **only when the request's trimmed corrections are non-empty**; a bare press never reaches
it.

**Files:**
- Create: `lib/corrections/apply-core.ts`
- Test: `tests/lib/corrections/apply-core.test.ts`

**Interfaces:**
- Consumes:
  - `assertStructurePreserved(before: string, after: string): void` and
    `StructuralValidationError` from Task 1 (`lib/corrections/structural-validation.ts`).
  - `fixSummary(mdContent: string, corrections: string, retries?: number, baseDelayMs?: number): Promise<string>`
    from `lib/gemini.ts:470` — **its CURRENT signature.** ⚠ Task 5 changes it to take a required
    third `opts` argument and updates the call site in this file. Write the current form here so
    this task typechecks on its own.
  - `extractQuickView(summaryMarkdown: string, caps?: CloudGeminiCaps, billing?: BillingLatch): Promise<{ tldr: string; takeaways: string[] }>`
    from `lib/gemini.ts:426`.
  - `stripQuickViewCallout(mdContent: string): string` and
    `insertQuickViewCallout(mdContent: string, tldr: string, takeaways: string[], tags: string[]): string`
    from `lib/quick-view-callout.ts:14,24`. Import from **`@/lib/quick-view-callout`**, not
    `lib/pipeline` — pipeline pulls in `fs` and storage, and this module must stay store-agnostic.
- Produces:
  - `interface ApplyCorrectionInput { md: string; corrections: string; tags: string[]; signal: AbortSignal }`
  - `interface ApplyCorrectionResult { content: string; tldr: string; takeaways: string[] }`
  - `function applyCorrection(input: ApplyCorrectionInput): Promise<ApplyCorrectionResult>`

`tags` and `signal` are both **required, not optional**. `tags` because dropping it deletes the
callout's Concepts line (`route.ts:67` passes `video.tags ?? []`). `signal` because an optional one
lets a caller silently restore an uncancellable ~181 s paid call — a required parameter makes
omission a compile error.

- [ ] **Step 1: Write the failing test**

Create `tests/lib/corrections/apply-core.test.ts`:

```ts
jest.mock('@/lib/gemini');

import { applyCorrection } from '@/lib/corrections/apply-core';
import { StructuralValidationError } from '@/lib/corrections/structural-validation';
import * as gemini from '@/lib/gemini';

const mockFixSummary = jest.mocked(gemini.fixSummary);
const mockExtractQuickView = jest.mocked(gemini.extractQuickView);

const BODY = `---
video_id: abc12345678
lang: EN
---

# A Title

**Channel:** Ch | **Duration:** 10:00 | **URL:** https://www.youtube.com/watch?v=abc12345678

---

## 1. Intro

▶ [0:00–5:00](https://www.youtube.com/watch?v=abc12345678&t=0s)

Clawcode is great.
`;

const CORRECTED = BODY.replace('Clawcode', 'Claude Code');

beforeEach(() => {
  jest.clearAllMocks();
  mockFixSummary.mockResolvedValue(CORRECTED);
  mockExtractQuickView.mockResolvedValue({ tldr: 'New TL;DR.', takeaways: ['New point'] });
});

describe('applyCorrection', () => {
  it('returns the corrected body with a re-inserted callout', async () => {
    const r = await applyCorrection({
      md: BODY, corrections: "Clawcode -> Claude Code", tags: ['ai'],
      signal: new AbortController().signal,
    });
    expect(r.content).toContain('Claude Code');
    expect(r.content).toContain('> [!summary] Quick Reference');
    expect(r.content).toContain('> **TL;DR:** New TL;DR.');
    expect(r.tldr).toBe('New TL;DR.');
    expect(r.takeaways).toEqual(['New point']);
  });

  it('passes the CALLOUT-STRIPPED body to fixSummary, not the raw body', async () => {
    const withCallout = BODY.replace(
      '\n\n---\n\n## 1. Intro',
      '\n\n> [!summary] Quick Reference\n> **TL;DR:** Old.\n\n---\n\n## 1. Intro',
    );
    await applyCorrection({
      md: withCallout, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    expect(mockFixSummary.mock.calls[0][0]).not.toContain('Quick Reference');
  });

  it('renders the Concepts line from tags', async () => {
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: ['ai', 'rag'], signal: new AbortController().signal,
    });
    expect(r.content).toContain('> **Concepts:** ai · rag');
  });

  it('throws StructuralValidationError and never calls extractQuickView when structure moved', async () => {
    mockFixSummary.mockResolvedValue(BODY.replace('## 1. Intro', '## 1. Introduction'));
    await expect(applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    })).rejects.toThrow(expect.objectContaining({ reason: 'section-title' }));
    expect(mockExtractQuickView).not.toHaveBeenCalled();
  });

  it('surfaces StructuralValidationError as its own class', async () => {
    mockFixSummary.mockResolvedValue(BODY.replace('## 1. Intro', '## 1. Introduction'));
    await expect(applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    })).rejects.toBeInstanceOf(StructuralValidationError);
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails for the right reason**

Run: `npx jest tests/lib/corrections/apply-core.test.ts`
Expected: FAIL — `Cannot find module '@/lib/corrections/apply-core'`.

- [ ] **Step 3: Write the implementation**

Create `lib/corrections/apply-core.ts`:

```ts
import { fixSummary, extractQuickView } from '@/lib/gemini';
import { stripQuickViewCallout, insertQuickViewCallout } from '@/lib/quick-view-callout';
import { assertStructurePreserved } from './structural-validation';

/** `tags` and `signal` are REQUIRED. `tags` because omitting it deletes the callout's Concepts
 *  line; `signal` because an optional one lets a caller silently restore an uncancellable ~181 s
 *  paid call, and a required parameter makes that a compile error instead. */
export interface ApplyCorrectionInput {
  md: string;
  corrections: string;
  tags: string[];
  signal: AbortSignal;
}

export interface ApplyCorrectionResult {
  content: string;
  tldr: string;
  takeaways: string[];
}

/**
 * strip callout → fixSummary → structural validation → extractQuickView → re-insert callout.
 *
 * STORE-AGNOSTIC: no `fs`, no BlobStore, no Supabase. Import the callout transforms from
 * `@/lib/quick-view-callout`, never from `lib/pipeline` — pipeline drags in `fs` and storage.
 *
 * Call this ONLY when the request's corrections are non-empty after trimming. A bare press must not
 * reach it: `fixSummary` runs ⟺ trimmed corrections are non-empty (spec §3).
 */
export async function applyCorrection(input: ApplyCorrectionInput): Promise<ApplyCorrectionResult> {
  const stripped = stripQuickViewCallout(input.md);
  const fixed = await fixSummary(stripped, input.corrections);
  // Validate BEFORE paying for quick-view: a structural failure discards the correction, so there is
  // no reason to buy an extraction of a document that is about to be thrown away.
  assertStructurePreserved(stripped, fixed);
  const { tldr, takeaways } = await extractQuickView(fixed);
  return {
    content: insertQuickViewCallout(fixed, tldr, takeaways, input.tags),
    tldr,
    takeaways,
  };
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `npx jest tests/lib/corrections/apply-core.test.ts`
Expected: PASS, 5 tests.

- [ ] **Step 5: Typecheck and run the full suite**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass.

- [ ] **Step 6: Commit**

```bash
git add lib/corrections/apply-core.ts tests/lib/corrections/apply-core.test.ts
git commit -m "feat(#23): store-agnostic apply-core pipeline with required tags and signal"
```

---

### Task 3: A bare press stops rewriting the file, and stops recomputing `mdCorrectionsHash`

⚠ **This task MUST land before Task 4.** Task 4 makes any body-hash change invalidate the magazine
model and book a ~6¢ regeneration on the next owner serve. This task is what stops a *bare* press
from moving the body hash. Ship 4 first and every bare press costs ~6¢.

Two defects, one file, one commit — they are the same press.

**(a) The write.** `route.ts:66-69` re-extracts quick-view and re-inserts the callout on **every**
press, then writes. On a bare press `fixed === stripped`, so the prose is unchanged, but
`extractQuickView` is a non-deterministic LLM call whose output is spliced into the hashed region.
Measured 2026-08-23 (`docs/reviews/spec-corrections-in-cloud-r5-bare-press-write.md`): the callout
lands in the preamble `parseSections` discards (`parse.ts:45-47`), so it can change **no** input to
the magazine model — the ~6¢ would recompute from byte-identical inputs. The whole suite (268 suites
/ 2,722 tests) passes with the write skipped.

**(b) The stamp.** `route.ts:77-79` resolves `effectiveCorrections` to the **stored** value on a bare
press and `:88` writes `mdHash(stored)` — flipping a corrections-*stale* row to *current* with no
Gemini call. `mdCorrectionsHash` is the sole input to `reconcileClassA`'s currency predicate
(`reconcile-class-a.ts:8`), and `sync-run.ts:358` delivers corrections without doing MD work, so one
bare press permanently discards a pending correction (spec §4.3).

**Files:**
- Modify: `app/api/videos/[id]/regenerate/route.ts:62-89`
- Test: `tests/api/regenerate.test.ts` (add cases), `tests/lib/cloud-sync/regenerate-stamp.test.ts` (change one case)

**Interfaces:**
- Consumes: nothing from earlier tasks. This is a standalone change to existing code.
- Produces: no new exports. The route's observable contract is unchanged except that a bare press
  no longer writes the file and no longer sends `mdCorrectionsHash` or `mdGeneratedAt`.

**The three cases, stated once so the steps are unambiguous:**

| Request | `fixSummary` runs? | File written? | `mdCorrectionsHash` | `mdGeneratedAt` |
|---|---|---|---|---|
| `corrections: "fix X"` (non-empty after trim) | yes | **yes** | `mdHash("fix X")` | now |
| `corrections: ""` (explicit clear) | no | **no** | `mdHash("")` — unchanged behaviour, imperfect and accepted (spec §4.3) | **omitted** |
| absent, or `"  "` (bare press) | no | **no** | **omitted** | **omitted** |

- [ ] **Step 1: Write the failing tests**

Append to `tests/api/regenerate.test.ts` (the file's existing mocks, `post()` helper and `beforeEach`
at `:1-74` already give you `mockWriteFile`, `mockUpdateVideoFields` and `mockFixSummary`):

```ts
describe('bare press does not rewrite the file (spec §2, r5 B1)', () => {
  it('writes the file when corrections were applied', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix Clawcode' });
    expect(mockWriteFile).toHaveBeenCalledTimes(1);
  });

  it('does NOT write the file on a bare press (no corrections key)', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockFixSummary).not.toHaveBeenCalled();
    expect(mockWriteFile).not.toHaveBeenCalled();
  });

  it('does NOT write the file on a whitespace-only press', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '   ' });
    expect(mockWriteFile).not.toHaveBeenCalled();
  });

  it('does NOT write the file on an explicit clear', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockWriteFile).not.toHaveBeenCalled();
  });

  it('still refreshes tldr/takeaways on a bare press — quick-view stays unconditional', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockExtractQuickView).toHaveBeenCalledTimes(1);
    expect((await res.json()).tldr).toBe('This video teaches X.');
  });
});
```

Now change the bare-press case in `tests/lib/cloud-sync/regenerate-stamp.test.ts`. Replace the body
of the existing `it('a bare regenerate (no corrections param) stamps against the UNCHANGED stored
corrections', …)` at `:98` with this, and rename it:

```ts
  it('a bare regenerate omits mdCorrectionsHash entirely (spec §4.3)', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    const patch = mockUpdateVideoFields.mock.calls.at(-1)![2] as Record<string, unknown>;
    expect(patch).not.toHaveProperty('mdCorrectionsHash');
    expect(patch).not.toHaveProperty('mdGeneratedAt');
    // The stored value already describes what the body reflects. :77-79 tried to DERIVE that truth
    // and got it wrong when sync-run.ts:358 delivered corrections the body never saw; leaving the
    // field alone PRESERVES it and needs no assumption.
  });
```

- [ ] **Step 2: Run the tests and confirm they fail for the right reasons**

Run: `npx jest tests/api/regenerate.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts`
Expected: FAIL — the three "does NOT write" cases report
`expect(jest.fn()).not.toHaveBeenCalled()` with 1 call, and the stamp case reports the patch
*does* have property `mdCorrectionsHash`.

- [ ] **Step 3: Make the write conditional**

In `app/api/videos/[id]/regenerate/route.ts`, replace line 69:

```ts
    await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');
```

with:

```ts
    // WRITE ONLY WHEN A CORRECTION WAS APPLIED (spec §2, round-5 Blocking). On a bare press
    // `fixed === stripped`, so the prose is unchanged — but `extractQuickView` above is a
    // non-deterministic LLM call and `insertQuickViewCallout` splices its output into the hashed
    // region, so writing would move `mdHash(body)`. Under §2's option (e) that invalidates the
    // magazine model and books a ~6¢ regeneration for a press that applied nothing. Measured: the
    // callout sits in the preamble `parseSections` discards (parse.ts:45-47), so it can change no
    // input the model is built from — the regeneration would recompute an identical result.
    if (trimmedCorrections) {
      await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');
    }
```

- [ ] **Step 4: Make the stamp conditional**

Replace lines 71-89 (the `effectiveCorrections` block and the `updateVideoFields` call) with:

```ts
    // Stage 3 (§5.1/§5.7) + spec §4.3. Stamp corrections-currency ONLY when fixSummary actually ran,
    // and stamp it against the REQUEST's corrections — the quantity that was applied.
    //
    // The old rule (`:77-79`) fell back to the STORED value on a bare press, which flipped a
    // corrections-stale row to current with no Gemini call. `mdCorrectionsHash` is the sole input to
    // reconcileClassA's currency predicate (reconcile-class-a.ts:8), and sync-run.ts:358 writes
    // `corrections` without touching the body, so one bare press permanently discarded a pending
    // correction. Omitting the field preserves whatever the row already claimed.
    //
    // An explicit clear still stamps mdHash('') — unchanged, imperfect (the body may still carry
    // previously applied corrections) and out of scope for slice A.
    const patch: Partial<Video> = { tldr, takeaways, summaryHtml: null };
    if (trimmedCorrections) {
      patch.mdGeneratedAt = new Date().toISOString();   // the body DID change
      patch.mdCorrectionsHash = mdHash(trimmedCorrections);
    } else if (corrections === '') {
      patch.mdCorrectionsHash = mdHash('');
    }

    await store.updateVideoFields(principal, videoId, patch);
```

Add the `Video` type import at the top of the file, beside the existing imports:

```ts
import type { Video } from '../../../../../types';
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `npx jest tests/api/regenerate.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts`
Expected: PASS. `regenerate.test.ts` gains 5 tests; `regenerate-stamp.test.ts` still has 4.

- [ ] **Step 6: Typecheck and run the full suite**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass.

- [ ] **Step 7: Commit**

```bash
git add app/api/videos/[id]/regenerate/route.ts tests/api/regenerate.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts
git commit -m "fix(#23): a bare press writes no body and stamps no currency (spec §2, §4.3)"
```

---

### Task 4: Option (e) — `isFresh` learns `sourceMdHash`

⚠ **Task 3 must already be committed.** This task is what turns a body-hash change into a paid
regeneration; Task 3 is what stops a bare press from producing one.

Magazine freshness is `sameTitles && generatorVersion` — it ignores the `sourceMdHash` the envelope
has carried since 2026-07-17 (`model-store.ts:23`, written by `serve-doc.ts:181` and
`generate.ts:59`). A correction changes the prose and pins the headings, so the cached model reads
fresh forever and serves pre-correction gists. Option (e) adds one conjunct, guarded exactly the way
`decideCompanion` already guards the same field (`companion.ts:151-152`).

**Files:**
- Modify: `lib/html-doc/read-model.ts:20-39`
- Modify: `lib/html-doc/serve-doc.ts:78`, `:141`
- Test: `tests/lib/html-doc/read-model.test.ts:39-51` (retire the tripwire), plus new cases

**Interfaces:**
- Consumes: `mdHash(md: string): string` from `lib/cloud-sync/content-hash.ts:16` — already imported
  in `serve-doc.ts:7`.
- Produces (both signatures change; `currentMdHash` is **required** so omission is a compile error,
  matching the `mdBody` precedent at `serve-doc.ts:67`):
  - `isFresh(envelope: { sourceSections: string[]; generatorVersion?: string; sourceMdHash?: string }, titles: string[], currentMdHash: string): boolean`
  - `readFreshMagazineModel(args: { blobStore: ReadOnlyBlobStore; principal: Principal; base: string; titles: string[]; currentMdHash: string }): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }>`
- **Unchanged, deliberately:** `readTitleStableModel` (`read-model.ts:57-69`). It is the only input
  the anonymous `/s/<token>` render has (`app/s/[token]/route.ts:102-103`, a generate-free leaf) and
  the `owner_over_budget` fallback (`serve-doc.ts:147-151`). Leaving it alone is what keeps backlog
  **#57 — tolerate version skew on the share path** standing. Do not touch it in this task.

- [ ] **Step 1: Retire the tripwire and write the new cases**

`tests/lib/html-doc/read-model.test.ts:39-51` is a **deliberate guard against this exact change**.
Its comment says *"WHEN THIS GOES RED: someone made isFresh hash-aware. That is a MONEY decision —
prose-only edits would then force paid regeneration — so read §3.5.1 before deleting this test."*
Retiring it is a decision, not a cleanup, so it is replaced by a test asserting the new behaviour
with a pointer to the decision that overturned it.

Delete the whole `it('treats an envelope with a STALE sourceMdHash as fresh when titles match', …)`
block at `:39-51` and put this in its place:

```ts
  // WAS: a tripwire asserting isFresh IGNORES sourceMdHash, installed by the serve-path-deadline
  // work (#46 §3.5.1) which accepted the stale-model residual because no detection mechanism
  // existed. That residual is CLOSED here. The decision is
  // docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md §2, "DECIDED 2026-08-23 (user)
  // — option (e)", reviewed in docs/reviews/spec-corrections-in-cloud-r5-{codex,claude}.md.
  // The money consequence is intended and stated there: a prose-only edit now forces one paid
  // regeneration on the next OWNER serve. The share path is untouched (readTitleStableModel).
  it('false when sourceMdHash is present and does not match the current body', () => {
    expect(isFresh(envelope({ sourceMdHash: 'hash-of-OLD-markdown' }), titles, 'hash-of-NEW-markdown'))
      .toBe(false);
  });

  it('true when sourceMdHash matches the current body', () => {
    expect(isFresh(envelope({ sourceMdHash: 'hash-X' }), titles, 'hash-X')).toBe(true);
  });

  // ABSENT means CANNOT PROVE STALE, exactly as decideCompanion reads the same field
  // (companion.ts:151-152: `sourceMdHash !== undefined`). Pre-2026-07-17 envelopes predate the
  // field; invalidating them would mass-regenerate a population nobody has counted.
  it('true when sourceMdHash is ABSENT — absent cannot prove stale', () => {
    expect(isFresh(envelope(), titles, 'any-hash-at-all')).toBe(true);
  });
```

Then update the three existing `isFresh` calls at `:30`, `:33` and `:36` to pass a third argument,
and the three `readFreshMagazineModel` calls at `:59`, `:68` and `:74`:

```ts
    expect(isFresh(envelope(), titles, 'hash-X')).toBe(true);                                 // :30
    expect(isFresh(envelope({ sourceSections: ['A', 'C'] }), titles, 'hash-X')).toBe(false);  // :33
    expect(isFresh(envelope({ generatorVersion: 'old' }), titles, 'hash-X')).toBe(false);     // :36
```

```ts
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles, currentMdHash: 'hash-X' });
```

- [ ] **Step 2: Run the tests and confirm they fail for the right reason**

Run: `npx jest tests/lib/html-doc/read-model.test.ts`
Expected: FAIL — TypeScript reports `Expected 2 arguments, but got 3` for `isFresh`, and the
mismatch case returns `true` where `false` is expected.

- [ ] **Step 3: Add the conjunct**

In `lib/html-doc/read-model.ts`, replace `isFresh` (`:20-25`) and `readFreshMagazineModel`'s body
(`:29-39`) with:

```ts
/**
 * OWNER-path freshness: refusing an envelope here triggers a reserve-and-charge regeneration
 * (serve-doc.ts:112-151), so every conjunct is a money decision.
 *
 * `sourceMdHash` (spec §2, option (e), 2026-08-23). ABSENT means "cannot prove stale" and stays
 * fresh — the same reading decideCompanion gives the same field (companion.ts:151-152). Only a
 * PRESENT hash that disagrees with the current body invalidates. That closes #46 §3.5.1's accepted
 * residual, and its tripwire in tests/lib/html-doc/read-model.test.ts was retired with this change.
 */
export function isFresh(
  envelope: { sourceSections: string[]; generatorVersion?: string; sourceMdHash?: string },
  titles: string[],
  currentMdHash: string,
): boolean {
  return sameTitles(envelope, titles)
    && envelope.generatorVersion === GENERATOR_VERSION
    && (envelope.sourceMdHash === undefined || envelope.sourceMdHash === currentMdHash);
}

/** Read-only, generation-free: returns the cached model iff present AND fresh; otherwise
 *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call).
 *  `currentMdHash` is REQUIRED — an optional one would let a new caller silently reinstate the
 *  hash-blind behaviour this exists to remove. */
export async function readFreshMagazineModel(args: {
  blobStore: ReadOnlyBlobStore;
  principal: Principal;
  base: string;
  titles: string[];
  currentMdHash: string;
}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }> {
  const { blobStore, principal, base, titles, currentMdHash } = args;
  const existing = await readModelEnvelope(principal, base, blobStore);
  if (existing && isFresh(existing, titles, currentMdHash)) return { status: 'ok', model: existing.model };
  return { status: 'not_ready' };
}
```

- [ ] **Step 4: Pass the hash at both call sites**

In `lib/html-doc/serve-doc.ts`, immediately after `const titles = parsed.sections.map((s) => s.title);`
(`:71`) add:

```ts
  // The body hash the envelope's own `sourceMdHash` is compared against (spec §2, option (e)).
  // Same function, same input shape as the write at :181, so an unchanged document hashes equal
  // on every serve: canonicalizeMd folds CRLF, trailing newlines and NFC (content-hash.ts:9-13).
  const currentMdHash = mdHash(mdBody);
```

Then change `:78`:

```ts
  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles, currentMdHash });
```

and `:141`:

```ts
      const now = await readFreshMagazineModel({ blobStore, principal, base, titles, currentMdHash });
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `npx jest tests/lib/html-doc/read-model.test.ts`
Expected: PASS. The `isFresh` describe block now has 6 tests.

- [ ] **Step 6: Mutation-check — prove the conjunct is load-bearing**

⚠ **This step is not optional.** No fixture anywhere in `tests/` sets `sourceMdHash`
(`grep -rn sourceMdHash tests/` returns only this file and two comments), so every pre-existing
envelope fixture takes the `=== undefined` branch and the whole suite would pass with the conjunct
deleted. Without this check, option (e) can ship as a silent no-op.

Revert the conjunct by hand — change the `isFresh` return to:

```ts
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
```

Run: `npx jest tests/lib/html-doc/read-model.test.ts`
Expected: **FAIL** on `false when sourceMdHash is present and does not match the current body`.
If it passes, the test is not reaching the branch — fix the test, not the implementation.

Now restore the conjunct and re-run:

Run: `npx jest tests/lib/html-doc/read-model.test.ts`
Expected: PASS.

- [ ] **Step 7: Typecheck and run the full suite**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass. If any other suite fails here it has found a caller the
`lib/`+`app/`+`components/` grep did not — read it before changing it.

- [ ] **Step 8: Commit**

```bash
git add lib/html-doc/read-model.ts lib/html-doc/serve-doc.ts tests/lib/html-doc/read-model.test.ts
git commit -m "feat(#23): isFresh derives staleness from sourceMdHash (spec §2 option (e))"
```

---

### Task 5: `fixSummary` gains caps, a signal in three places, a preflight, and usage capture

**Files:**
- Modify: `lib/gemini.ts:470-511` (`fixSummary`), and add an exported preflight beside
  `assertMagazineInputWithinCap` (`:73-99`)
- Modify: `lib/gemini-cost.ts` (add `correctionActualCents`)
- Modify: `lib/corrections/apply-core.ts` (the `fixSummary` call site from Task 2)
- Test: `tests/lib/gemini-fix-summary.test.ts` (create), `tests/lib/corrections/apply-core.test.ts`

**Interfaces:**
- Consumes: `applyCorrection` / `ApplyCorrectionInput` / `ApplyCorrectionResult` from Task 2;
  `PRICE_IN_PER_1M_CENTS = 30` and `PRICE_OUT_PER_1M_CENTS = 250` from `lib/gemini-cost.ts:33,35`.
- Produces:
  - `interface GeminiUsage { promptTokens: number; outputTokens: number }` — from `lib/gemini.ts`
  - `fixSummary(mdContent: string, corrections: string, opts: { signal: AbortSignal; caps?: CloudGeminiCaps }, retries?: number, baseDelayMs?: number): Promise<{ text: string; usage: GeminiUsage | null }>`
    — `opts` is a **required third parameter**; `retries`/`baseDelayMs` keep their defaults and move
    to positions four and five.
  - `assertCorrectionInputWithinCap(model: Pick<GenerativeModel, 'countTokens'>, prompt: string, generationConfig: GenerationConfig, caps: CloudGeminiCaps, opts?: { signal?: AbortSignal; timeoutMs?: number }): Promise<void>`
    — throws `NonRetryableError` (`lib/job-queue/errors.ts:1`) when over cap.
  - `correctionActualCents(usage: { promptTokens: number; outputTokens: number }): number` — from
    `lib/gemini-cost.ts`.
  - `CORRECTION_CAPS: CloudGeminiCaps` — exported from `lib/corrections/apply-core.ts`.
  - `CORRECTION_PREFLIGHT_TIMEOUT_MS = 10_000` — exported from `lib/corrections/apply-core.ts`.
  - `ApplyCorrectionResult` gains `actualCents: number | null`.

⚠ **Usage capture belongs here, not in Task 9.** Measuring spend changes `fixSummary`'s return type,
which is this task's deliverable — splitting it would have this task ship `Promise<string>` for a
later task to immediately rewrite, and edit these tests twice. Task 9 keeps only the *sink*, which is
the part that is blocked. `grep -rn usageMetadata lib/ app/` is currently empty: nothing in this
repo has ever read Gemini token counts, so this is new ground, not a pattern to copy.

⚠ **`usage` is `null`, never `0`, when the SDK reports nothing.** "Could not measure" and "cost
nothing" are different facts, and collapsing them understates spend exactly where it matters.

⚠ **`withCaps` decides *whether to cap at all* from its SECOND argument** — `lib/gemini.ts:41` is
`if (!caps) return base;`. Passing only `MAX_SUMMARY_OUTPUT_TOKENS` as the third argument with
`undefined` as the second ships an **uncapped call with thinking enabled**, and the diff reads
correct. A `CloudGeminiCaps` object shaped like `SERVE_CAPS` (`serve-doc.ts:26-33`) must be
constructed and passed as argument two.

⚠ **The signal goes in THREE places, not two.** `generateJson` has all three; `fixSummary` has none:

| # | `generateJson` | `fixSummary` today |
|---|---|---|
| 1 | loop-top abort guard, `:271` | **absent** — `:494` goes straight to `try` |
| 2 | `generateContent(prompt, { timeout, signal })`, `:273` | `:496` passes no signal |
| 3 | `abortableSleep(ms, signal)`, `:281` | `:505` is a bare `new Promise((r) => setTimeout(r, …))` |

Wire only #2 and an abort still runs the backoff to completion and issues another **paid** call.

- [ ] **Step 1: Write the failing test**

Create `tests/lib/gemini-fix-summary.test.ts`:

```ts
const mockGenerateContent = jest.fn();
const mockCountTokens = jest.fn();
const mockGetGenerativeModel = jest.fn(() => ({
  generateContent: mockGenerateContent,
  countTokens: mockCountTokens,
}));

jest.mock('@google/generative-ai', () => ({
  ...jest.requireActual('@google/generative-ai'),
  GoogleGenerativeAI: jest.fn(() => ({ getGenerativeModel: mockGetGenerativeModel })),
}));

import { fixSummary } from '@/lib/gemini';
import { CORRECTION_CAPS } from '@/lib/corrections/apply-core';

const ok = (text: string, usage?: { promptTokenCount: number; candidatesTokenCount: number }) => ({
  response: {
    text: () => text,
    candidates: [{ finishReason: 'STOP' }],
    ...(usage ? { usageMetadata: usage } : {}),
  },
});

beforeEach(() => {
  jest.clearAllMocks();
  process.env.GEMINI_API_KEY = 'test-key';
  mockGenerateContent.mockResolvedValue(ok('corrected'));
  mockCountTokens.mockResolvedValue({ totalTokens: 10 });
});

describe('fixSummary caps and cancellation', () => {
  it('applies maxOutputTokens and thinkingBudget:0 when a caps OBJECT is supplied', async () => {
    await fixSummary('md', 'c', { signal: new AbortController().signal, caps: CORRECTION_CAPS });
    expect(mockGetGenerativeModel).toHaveBeenCalledWith(
      expect.objectContaining({
        generationConfig: expect.objectContaining({
          maxOutputTokens: CORRECTION_CAPS.summaryOutputTokens,
          thinkingConfig: { thinkingBudget: 0 },
        }),
      }),
    );
  });

  it('leaves the local call uncapped when caps is absent — by design', async () => {
    await fixSummary('md', 'c', { signal: new AbortController().signal });
    const arg = mockGetGenerativeModel.mock.calls[0][0] as Record<string, unknown>;
    expect(arg).not.toHaveProperty('generationConfig.maxOutputTokens');
  });

  it('forwards the signal to generateContent', async () => {
    const ac = new AbortController();
    await fixSummary('md', 'c', { signal: ac.signal });
    expect(mockGenerateContent).toHaveBeenCalledWith('md' && expect.any(String), expect.objectContaining({ signal: ac.signal }));
  });

  it('throws AbortError from the loop-top guard without calling Gemini when already aborted', async () => {
    const ac = new AbortController();
    ac.abort();
    await expect(fixSummary('md', 'c', { signal: ac.signal }))
      .rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
    expect(mockGenerateContent).not.toHaveBeenCalled();
  });

  it('aborts DURING the backoff instead of sleeping it out and paying again', async () => {
    const ac = new AbortController();
    mockGenerateContent.mockImplementationOnce(async () => { throw new Error('transient'); });
    const p = fixSummary('md', 'c', { signal: ac.signal });
    await Promise.resolve();
    ac.abort();
    await expect(p).rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
    expect(mockGenerateContent).toHaveBeenCalledTimes(1);   // no second PAID attempt
  });
});

describe('fixSummary reports what the call actually used', () => {
  it('returns the token counts the SDK reported', async () => {
    mockGenerateContent.mockResolvedValue(ok('corrected', { promptTokenCount: 10_000, candidatesTokenCount: 4_000 }));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe('corrected');
    expect(r.usage).toEqual({ promptTokens: 10_000, outputTokens: 4_000 });
  });

  it('returns usage: null — NOT zero — when the SDK reported no usageMetadata', async () => {
    mockGenerateContent.mockResolvedValue(ok('corrected'));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.usage).toBeNull();   // "could not measure" is not "cost nothing"
  });
});
```

Add the pricing and result cases to `tests/lib/corrections/apply-core.test.ts` as well. Task 2's
`beforeEach` sets `mockFixSummary.mockResolvedValue(CORRECTED)` — **change every
`mockFixSummary.mockResolvedValue(x)` in that file to `mockResolvedValue({ text: x, usage: null })`**,
then append:

```ts
describe('actual spend is measured, not estimated', () => {
  it('prices the real token counts', async () => {
    mockFixSummary.mockResolvedValue({
      text: CORRECTED,
      usage: { promptTokens: 10_000, outputTokens: 4_000 },
    });
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    // 10_000 * 30/1e6 + 4_000 * 250/1e6 = 0.3 + 1.0 = 1.3¢ → ceil 2
    expect(r.actualCents).toBe(2);
  });

  it('reports null rather than zero when the SDK returned no usageMetadata', async () => {
    mockFixSummary.mockResolvedValue({ text: CORRECTED, usage: null });
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    expect(r.actualCents).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails for the right reason**

Run: `npx jest tests/lib/gemini-fix-summary.test.ts`
Expected: FAIL — TypeScript reports `Argument of type '{ signal: AbortSignal; }' is not assignable
to parameter of type 'number'` (the current third parameter is `retries`), and
`Cannot find module '@/lib/corrections/apply-core'` exports `CORRECTION_CAPS`.

- [ ] **Step 3: Add the preflight to `lib/gemini.ts`**

Insert immediately after `assertMagazineInputWithinCap` ends at `:99`:

```ts
/** countTokens preflight for the correction path (mirrors assertMagazineInputWithinCap). The
 *  correction's output is the whole assembled document, so the OUTPUT cap is the right bound to
 *  check the input against: an input already over it cannot come back under it.
 *
 *  Why a preflight at all: fixSummary retries twice on truncation (loop at :494-508), so an
 *  over-cap document would cost three full paid passes and then throw. */
export async function assertCorrectionInputWithinCap(
  model: Pick<GenerativeModel, 'countTokens'>,
  prompt: string,
  generationConfig: GenerationConfig,
  caps: CloudGeminiCaps,
  opts?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<void> {
  const { totalTokens } = await model.countTokens(
    {
      generateContentRequest: { contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig },
    },
    {
      ...(opts?.signal ? { signal: opts.signal } : {}),
      ...(opts?.timeoutMs ? { timeout: opts.timeoutMs } : {}),
    },
  );
  if (totalTokens > caps.summaryOutputTokens) {
    throw new NonRetryableError(
      `correction input ${totalTokens} tokens exceeds cap ${caps.summaryOutputTokens}`,
    );
  }
}
```

- [ ] **Step 4: Rewrite `fixSummary`**

Replace `lib/gemini.ts:470-511` in full:

```ts
export async function fixSummary(
  mdContent: string,
  corrections: string,
  // REQUIRED third parameter. `signal` optional here would let a caller silently restore an
  // uncancellable ~181 s paid call; `caps` stays optional because the LOCAL pipeline passes none by
  // design (withCaps returns `base` unchanged when caps is undefined, :41).
  opts: { signal: AbortSignal; caps?: CloudGeminiCaps },
  retries = 2,
  baseDelayMs = 400,
): Promise<string> {
  const client = new GoogleGenerativeAI(getApiKey());
  const model = client.getGenerativeModel({
    model: SUMMARY_MODEL,
    // The caps OBJECT is argument TWO — that is what decides whether any cap is applied at all.
    generationConfig: withCaps({}, opts.caps, opts.caps?.summaryOutputTokens ?? 0),
  });

  const prompt = `You are editing a video summary document. Apply the correction instructions below to the document and return the complete corrected document. Rules:
- Only fix the text as instructed — do NOT add, remove, or restructure any sections
- Preserve all markdown formatting exactly: headings, bold text, horizontal rules, frontmatter
- Return ONLY the complete corrected document with no preamble or explanation

Corrections to apply:
${corrections}

<document>
${mdContent}
</document>`;

  // Retry loop mirrors generateJson: a truncated (non-STOP) or empty correction re-rolls rather
  // than silently persisting a half-corrected document (this path returns text, not JSON).
  let lastErr: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    // (1 of 3) Loop-top abort guard — generateJson:271 has this; without it an abort during the
    // backoff below is not noticed until the NEXT paid call has already been issued.
    if (opts.signal.aborted) throw new DOMException('aborted', 'AbortError');
    try {
      // (2 of 3) Forward the signal to the call itself — generateJson:273.
      const result = await model.generateContent(prompt, {
        timeout: REQUEST_TIMEOUT_MS,
        signal: opts.signal,
      });
      assertNotTruncated(result);
      const corrected = result.response.text().trim();
      if (!corrected) throw new Error('Gemini returned empty content');
      return corrected;
    } catch (err) {
      // Preserve AbortError identity unwrapped so the caller can distinguish cancellation from a
      // real failure (same rule as generateSummary's catch).
      if ((err as { name?: string })?.name === 'AbortError') throw err;
      lastErr = err;
      if (attempt < retries) {
        console.warn(`[gemini-retry] fix-summary: attempt ${attempt + 1} failed (${err instanceof Error ? err.message : String(err)}); retrying…`);
        // (3 of 3) Interruptible backoff — generateJson:281. A bare setTimeout waits out up to
        // 1.2 s of sleep it cannot cancel, then issues another paid attempt.
        if (baseDelayMs > 0) await abortableSleep(baseDelayMs * 2 ** attempt, opts.signal);
      }
    }
  }
  const cause = lastErr instanceof Error ? lastErr.message : String(lastErr);
  throw new Error(`Gemini summary fix failed: ${cause}`, { cause: lastErr });
}
```

- [ ] **Step 5: Wire the caps, the signal and the preflight into `apply-core`**

In `lib/corrections/apply-core.ts`, add these imports and exports at the top:

```ts
import { fixSummary, extractQuickView, assertCorrectionInputWithinCap, SUMMARY_MODEL } from '@/lib/gemini';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS } from '@/lib/gemini-cost';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';

/** Caps for the paid correction transform. Only `summaryOutputTokens` is load-bearing; the rest
 *  satisfy the CloudGeminiCaps type. Shaped like SERVE_CAPS (serve-doc.ts:26-33) on purpose — this
 *  OBJECT is what makes withCaps cap anything (gemini.ts:41). */
export const CORRECTION_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
};

/** STATED, never inherited. Inheriting REQUEST_TIMEOUT_MS (60 s, gemini.ts:105) would push §5.4's
 *  worst case to 422.4 s — over the 420 s maxDuration. This is a token count, not a generation. */
export const CORRECTION_PREFLIGHT_TIMEOUT_MS = 10_000;
```

Then change `applyCorrection` to take `caps` and run the preflight before the paid call:

```ts
export interface ApplyCorrectionInput {
  md: string;
  corrections: string;
  tags: string[];
  signal: AbortSignal;
  /** Absent on the LOCAL branch by design — withCaps then returns the base config unchanged. */
  caps?: CloudGeminiCaps;
}

export async function applyCorrection(input: ApplyCorrectionInput): Promise<ApplyCorrectionResult> {
  const stripped = stripQuickViewCallout(input.md);

  if (input.caps) {
    const client = new GoogleGenerativeAI(process.env.GEMINI_API_KEY ?? '');
    const model = client.getGenerativeModel({ model: SUMMARY_MODEL });
    await assertCorrectionInputWithinCap(
      model, stripped, {}, input.caps,
      { signal: input.signal, timeoutMs: CORRECTION_PREFLIGHT_TIMEOUT_MS },
    );
  }

  const fixed = await fixSummary(stripped, input.corrections, { signal: input.signal, caps: input.caps });
  assertStructurePreserved(stripped, fixed);
  const { tldr, takeaways } = await extractQuickView(fixed, input.caps);
  return {
    content: insertQuickViewCallout(fixed, tldr, takeaways, input.tags),
    tldr,
    takeaways,
  };
}
```

Update the existing `applyCorrection` call in `app/api/videos/[id]/regenerate/route.ts` if Task 2's
route wiring has landed; otherwise the route still calls `fixSummary` directly at `:63` and that call
becomes `await fixSummary(stripped, trimmedCorrections, { signal: request.signal })`.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `npx jest tests/lib/gemini-fix-summary.test.ts tests/lib/corrections/apply-core.test.ts`
Expected: PASS.

- [ ] **Step 7: Mutation-check the caps object**

Change the `withCaps` call in `fixSummary` to `withCaps({}, undefined, opts.caps?.summaryOutputTokens ?? 0)`.
Run: `npx jest tests/lib/gemini-fix-summary.test.ts`
Expected: **FAIL** on `applies maxOutputTokens and thinkingBudget:0 when a caps OBJECT is supplied`.
This is the exact defect the test exists for — a diff that names the constant and caps nothing.
Restore `opts.caps` and re-run; expected PASS.

- [ ] **Step 8: Typecheck and run the full suite**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass.

- [ ] **Step 9: Commit**

```bash
git add lib/gemini.ts lib/corrections/apply-core.ts tests/lib/gemini-fix-summary.test.ts
git commit -m "feat(#23): fixSummary gains a caps object, a signal in three places, and a preflight"
```

---

### Task 6: Corrections written through `updateVideoAnnotations`, read-before-write

Two problems with `route.ts:54-59`.

**(a) The clear is a no-op on Supabase.** `updateVideoFields(p, id, { corrections: undefined })`
(`:58`) reaches `merge_video_data` via `supabase-metadata-store.ts:133-146`, and `undefined` is
dropped by JSON serialization — the RPC receives `{}`. The route then stamps `mdHash('')` over a row
that still holds corrections.

**(b) The stamp moves on a no-op.** `update_video_annotations` stamps `annotationsEditedAt` for every
Class-B key **set OR cleared** (`0021:33-43`), and the local store does the same through one
`changed` array (`local-metadata-store.ts:139-159`). Neither store can implement "only when it
changed", so the **caller** must: read the stored value first and issue **no call at all** when it
already equals the incoming one — including clearing an already-empty field, which would otherwise
stamp an edit that did not happen.

**Files:**
- Modify: `app/api/videos/[id]/regenerate/route.ts:52-59`
- Test: `tests/api/regenerate.test.ts`

**Interfaces:**
- Consumes:
  `updateVideoAnnotations(p: Principal, videoId: string, set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>, clear: ('personalScore' | 'personalNote' | 'corrections')[], opts?: { editedAt?: string }): Promise<{ found: boolean }>`
  — the seam at `lib/storage/metadata-store.ts:73`, implemented at
  `lib/storage/local/local-metadata-store.ts:125` and
  `lib/storage/supabase/supabase-metadata-store.ts:269`.
- Produces: no new exports.

- [ ] **Step 1: Write the failing test**

Append to `tests/api/regenerate.test.ts`. Add the store mock beside the existing ones — the route
reaches the annotations surface through `getStorageBundle().metadataStore`:

```ts
describe('corrections are written through updateVideoAnnotations (spec §4.1)', () => {
  it('SETS corrections when the incoming text differs from the stored text', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix Clawcode' });
    expect(mockUpdateVideoAnnotations).toHaveBeenCalledWith(
      expect.anything(), VIDEO_ID, { corrections: 'fix Clawcode' }, [],
    );
  });

  it('CLEARS via the clear array, never via corrections: undefined', async () => {
    mockReadIndex.mockReturnValue({ ...baseIndex, videos: [{ ...baseVideo, corrections: 'old' }] } as any);
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockUpdateVideoAnnotations).toHaveBeenCalledWith(
      expect.anything(), VIDEO_ID, {}, ['corrections'],
    );
  });

  it('issues NO call when the incoming text equals the stored text', async () => {
    mockReadIndex.mockReturnValue({ ...baseIndex, videos: [{ ...baseVideo, corrections: 'same' }] } as any);
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'same' });
    expect(mockUpdateVideoAnnotations).not.toHaveBeenCalled();
  });

  it('issues NO call when clearing an ALREADY-EMPTY field', async () => {
    mockReadIndex.mockReturnValue({ ...baseIndex, videos: [{ ...baseVideo, corrections: undefined }] } as any);
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockUpdateVideoAnnotations).not.toHaveBeenCalled();
  });

  it('404s when the annotations write reports the row was not found', async () => {
    mockUpdateVideoAnnotations.mockResolvedValue({ found: false });
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix X' });
    expect(res.status).toBe(404);
    expect((await res.json()).error).toBe('video not found');
  });
});
```

Add to the mock block at the top of the file:

```ts
jest.mock('../../lib/storage/resolve', () => ({
  ...jest.requireActual('../../lib/storage/resolve'),
  getStorageBundle: jest.fn(),
}));
```

and to the imports and `beforeEach`:

```ts
import * as resolve from '../../lib/storage/resolve';
const mockUpdateVideoAnnotations = jest.fn();
const mockGetStorageBundle = jest.mocked(resolve.getStorageBundle);
// inside beforeEach:
mockUpdateVideoAnnotations.mockResolvedValue({ found: true });
mockGetStorageBundle.mockReturnValue({
  metadataStore: {
    readIndex: mockReadIndex,
    updateVideoFields: mockUpdateVideoFields,
    updateVideoAnnotations: mockUpdateVideoAnnotations,
  },
} as any);
```

- [ ] **Step 2: Run the tests and confirm they fail for the right reason**

Run: `npx jest tests/api/regenerate.test.ts`
Expected: FAIL — `expect(jest.fn()).toHaveBeenCalledWith(…)` reports zero calls, because the route
still uses `updateVideoFields`.

- [ ] **Step 3: Replace the corrections write**

In `app/api/videos/[id]/regenerate/route.ts`, replace lines 52-59 with:

```ts
    // Save corrections BEFORE the Gemini call so a page refresh shows the latest text even if
    // Gemini fails.
    //
    // updateVideoAnnotations, not updateVideoFields (spec §4.1). Two reasons:
    //  - `updateVideoFields(p, id, { corrections: undefined })` is a NO-OP on Supabase — `undefined`
    //    is dropped by JSON serialization before merge_video_data ever sees it, after which the
    //    route stamped mdHash('') over a row that still held corrections.
    //  - the RPC enforces the allowlist and `owner_id = auth.uid()` in SQL, and returns { found }.
    //
    // READ BEFORE WRITE, and issue NO CALL when nothing changed. Both backends stamp
    // annotationsEditedAt for every Class-B key set OR cleared (0021:33-43;
    // local-metadata-store.ts:139-159), so "only when it changed" cannot live in the store. A no-op
    // press must not beat a real remote edit in Class-B reconciliation — including the
    // clear-an-already-empty case, which would otherwise stamp an edit that did not happen.
    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    const storedCorrections = video.corrections ?? '';
    if (trimmedCorrections && trimmedCorrections !== storedCorrections) {
      const { found } = await store.updateVideoAnnotations(
        principal, videoId, { corrections: trimmedCorrections }, [],
      );
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    } else if (corrections === '' && storedCorrections !== '') {
      const { found } = await store.updateVideoAnnotations(principal, videoId, {}, ['corrections']);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    }
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `npx jest tests/api/regenerate.test.ts`
Expected: PASS.

- [ ] **Step 5: Prove it on BOTH backends**

A test that only proves this on one backend proves nothing about the seam. Add to
`tests/lib/storage/metadata-store-parity.test.ts` (create it if absent):

```ts
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';

it('local updateVideoAnnotations stamps annotationsEditedAt on a CLEAR, not just a set', async () => {
  // Pins the property that forces read-before-write into the CALLER: the store stamps
  // unconditionally in both directions, so it can never implement "only when it changed".
  const store = new LocalFsMetadataStore();
  // …seed an index with corrections: 'x' via indexStore, then:
  await store.updateVideoAnnotations(principal, VIDEO_ID, {}, ['corrections']);
  const after = indexStore.readIndex(principal.indexKey).videos[0];
  expect(after.annotationsEditedAt?.corrections).toEqual(expect.any(String));
});
```

Run: `npx jest tests/lib/storage/metadata-store-parity.test.ts`
Expected: PASS. The Supabase half of this parity is an integration test (needs a live Postgres) —
add it to `tests/integration/` and note in the PR that it was **NOT RUN** locally if no stack is up.

- [ ] **Step 6: Typecheck and run the full suite**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass.

- [ ] **Step 7: Commit**

```bash
git add app/api/videos/[id]/regenerate/route.ts tests/api/regenerate.test.ts tests/lib/storage/metadata-store-parity.test.ts
git commit -m "fix(#23): corrections via updateVideoAnnotations, read-before-write, no no-op stamp"
```

---

### Task 7: Server-side length cap (400), over-cap refusal (413), and `maxDuration`

Corrections are the **only unbounded input to a paid call**. `route.ts:24-26` validates the *type*
and nothing else; the 1,000 limit is a browser `maxLength` (`CorrectionsPanel.tsx:105`), and §5.3
concedes the route is reachable by any authenticated client, so a 200 KB blob is a real request.

Two distinct refusals, two distinct codes, both **before any Gemini call**:

| Refusal | Code | Trigger |
|---|---|---|
| corrections field too long | **400** `corrections-too-long` | more than 1,000 characters |
| the *document* is too large to correct | **413** `summary-too-large` | `assertCorrectionInputWithinCap` throws (Task 5) |

⚠ **The 413 is a permanent refusal for a real population.** `MAX_SUMMARY_OUTPUT_TOKENS` (8192) bounds
`generateSummary` **only when caps are present**, and the local pipeline passes none — so a large
locally-generated summary, synced to the cloud, can be **permanently uncorrectable**. The spec keeps
8192 anyway (raising it is slice C) and requires the refusal be *stated*, not discovered: a
distinguishable code, and a panel message, so the falsifier cannot read green while the feature is
silently refused.

**Plan-level decision, not settled by the spec:** count characters with `[...corrections].length`
(Unicode code points), not `.length` (UTF-16 units) and not `Buffer.byteLength`. The browser's
`maxLength` counts UTF-16 units, so this is *marginally* more permissive than the client — a
correction the browser accepts is never rejected by the server, which is the direction that avoids
bricking a user. Given backlog #36's history with non-ASCII, this is written down rather than left
implicit.

**Files:**
- Modify: `app/api/videos/[id]/regenerate/route.ts:1-30` (add `maxDuration`, the cap check) and the
  `catch` block at `:97-100` (map the preflight error to 413)
- Test: `tests/api/regenerate.test.ts`

**Interfaces:**
- Consumes: `NonRetryableError` from `lib/job-queue/errors.ts:1` — thrown by
  `assertCorrectionInputWithinCap` (Task 5) with a message beginning `correction input `.
- Produces:
  - `export const maxDuration = 420` on the route module.
  - `export const MAX_CORRECTIONS_CHARS = 1000` from
    `lib/corrections/apply-core.ts` — one definition, so the route and any future caller cannot
    drift. The client's `maxLength={1000}` stays a literal in the JSX; Task 11 adds a comment
    pointing at this constant.
  - Error response bodies gain a `code` field: `{ error: string; code: 'corrections-too-long' | 'summary-too-large' }`.

- [ ] **Step 1: Write the failing test**

Append to `tests/api/regenerate.test.ts`:

```ts
import { NonRetryableError } from '../../lib/job-queue/errors';

describe('input bounds (spec §2, §5.1)', () => {
  it('rejects corrections over 1,000 characters with 400 and a distinguishable code', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'x'.repeat(1001) });
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: expect.any(String), code: 'corrections-too-long' });
    expect(mockFixSummary).not.toHaveBeenCalled();
  });

  it('accepts corrections of exactly 1,000 characters — the boundary is inclusive', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'x'.repeat(1000) });
    expect(res.status).toBe(200);
  });

  it('counts code points, so 1,000 emoji are accepted', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '🙂'.repeat(1000) });
    expect(res.status).toBe(200);
  });

  it('returns 413 summary-too-large when the preflight refuses the document, NOT 500', async () => {
    mockFixSummary.mockRejectedValue(new NonRetryableError('correction input 9000 tokens exceeds cap 8192'));
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix X' });
    expect(res.status).toBe(413);
    expect((await res.json()).code).toBe('summary-too-large');
  });

  it('still returns 500 for an ordinary Gemini failure — the 413 is not a catch-all', async () => {
    mockFixSummary.mockRejectedValue(new Error('Gemini summary fix failed: 503'));
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix X' });
    expect(res.status).toBe(500);
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails for the right reason**

Run: `npx jest tests/api/regenerate.test.ts`
Expected: FAIL — the over-length case returns 200 (no cap exists) and the preflight case returns 500.

- [ ] **Step 3: Export the constant**

Add to `lib/corrections/apply-core.ts`:

```ts
/** Server-side bound on the corrections field, matching the client's maxLength
 *  (CorrectionsPanel.tsx:105) and enforced where it BINDS. Counted in Unicode CODE POINTS
 *  (`[...s].length`), not UTF-16 units: the browser counts UTF-16, so this is marginally more
 *  permissive and a correction the browser accepted is never refused by the server. */
export const MAX_CORRECTIONS_CHARS = 1000;
```

- [ ] **Step 4: Add `maxDuration` and the length check to the route**

At the top of `app/api/videos/[id]/regenerate/route.ts`, after the imports:

```ts
/** Bounds THE WORK, not THE REQUEST. Derived in spec §5.4 from three phases — a 10 s countTokens
 *  preflight plus two Gemini phases of 3 × 60 s + 1.2 s backoff each = 372.4 s — leaving ~48 s for
 *  the blob read, the blob write and the metadata RPC.
 *
 *  ⚠ NOTHING ON THIS DEPLOYMENT ENFORCES IT. Next's own docs call maxDuration an output annotation
 *  ("Deployment platforms CAN use maxDuration from the Next.js build output"), and this app ships
 *  `output: 'standalone'` (next.config.ts:11) running `node server.js` under Fly, where no adapter
 *  consumes it. Kept because it is correct-by-portability and free. */
export const maxDuration = 420;
```

Then, immediately after the existing type check at `:24-26`:

```ts
  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
  }

  // Corrections are the ONLY unbounded input to a paid call on this route. The 1,000 limit lives in
  // the browser (CorrectionsPanel.tsx:105) and §5.3 concedes any authenticated client can reach this
  // handler, so enforce it where it binds. Code points, not UTF-16 units — see MAX_CORRECTIONS_CHARS.
  if (typeof corrections === 'string' && [...corrections].length > MAX_CORRECTIONS_CHARS) {
    return NextResponse.json(
      { error: `corrections must be ${MAX_CORRECTIONS_CHARS} characters or fewer`, code: 'corrections-too-long' },
      { status: 400 },
    );
  }
```

Add the import:

```ts
import { MAX_CORRECTIONS_CHARS } from '../../../../../lib/corrections/apply-core';
```

- [ ] **Step 5: Map the preflight refusal to 413**

Replace the `catch` at `:97-100`:

```ts
  } catch (err) {
    logError(`regenerate:${videoId}`, err);
    // The preflight refusal is a CLIENT-side fact about this document, not a server fault: the
    // summary is larger than the correction cap can accept and no retry will change that. A 500
    // would tell the user to try again forever. Matched on the NonRetryableError class AND the
    // message prefix that assertCorrectionInputWithinCap emits, so an unrelated NonRetryableError
    // from elsewhere in the graph still reports 500.
    if (err instanceof NonRetryableError && err.message.startsWith('correction input ')) {
      return NextResponse.json(
        { error: 'This summary is too long to correct', code: 'summary-too-large' },
        { status: 413 },
      );
    }
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  }
```

Add the import:

```ts
import { NonRetryableError } from '../../../../../lib/job-queue/errors';
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `npx jest tests/api/regenerate.test.ts`
Expected: PASS.

- [ ] **Step 7: Typecheck and run the full suite, then commit**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass.

```bash
git add app/api/videos/[id]/regenerate/route.ts lib/corrections/apply-core.ts tests/api/regenerate.test.ts
git commit -m "feat(#23): server-side corrections cap (400) and over-cap document refusal (413)"
```

---

### Task 8: The cloud branch

The route cannot execute under Supabase today. The panel sends `outputFolder`
(`CorrectionsPanel.tsx:52`), the route rejects its absence (`:20-21`) and calls
`getPrincipal(outputFolder)` (`:30`), and `getStorageBundle()` at `:36` throws without a client —
**outside the try block**, so it 500s rather than returning an error.

**Files:**
- Modify: `app/api/videos/[id]/regenerate/route.ts` — split into `POST` → `serveLocal` / `serveCloud`
- Test: `tests/api/regenerate-cloud.test.ts` (create)

**Interfaces:**
- Consumes:
  - `createServerSupabase(cookieStore: CookieStore)` and `type CookieStore` from `lib/supabase/server`
  - `resolveOwnedPlaylistKey(supabase: SupabaseClient, playlistId: string, userId: string): Promise<string | null>` from `lib/storage/serve-playlist`
  - `getPrincipalFromSession(session: { userId: string | null }, indexKey: string): Principal` from `lib/storage/resolve:93`
  - `getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): StorageBundle` from `lib/storage/resolve:51`
  - `applyCorrection`, `CORRECTION_CAPS`, `MAX_CORRECTIONS_CHARS` from `lib/corrections/apply-core` (Tasks 2, 5, 7)
  - `blobStore.get(p, key): Promise<Buffer | null>` and `blobStore.put(p, key, bytes, contentType): Promise<void>` from `lib/storage/blob-store.ts:68-69`
- Produces: no new exports. The cloud branch is addressed by `?playlist=<uuid>`.

⚠ **Write the corrected body with `blobStore.put`, NEVER `writeArtifact`.** `writeArtifact`
(`lib/storage/supabase/consistency.ts:17`) is the repo's convention for a `summaryMd` artifact and it
is the wrong one here: it goes `putStaged → promote`, and `promote` is **create-if-absent** —
`supabase-blob-store.ts:120-123` returns early when the final key already exists, deleting the temp.
A correction never changes the key (the headings are pinned by Task 1's validator and the key derives
from the persisted `summaryMd`), so the final object **always** exists and `promote` would discard
the correction while the row was stamped `promoted`.

⚠ **A failed blob read must never become "empty document — correct it anyway".** `blobStore.get`
collapses RLS denials and transport faults into the same `null` as a genuine 404
(`blob-store.ts:57-66`, `provesAbsence`). Return **409 `repair-needed`**, matching
`serve-summary-core.ts:66-67`.

- [ ] **Step 1: Write the failing test**

Create `tests/api/regenerate-cloud.test.ts`:

```ts
jest.mock('../../lib/gemini');
jest.mock('../../lib/supabase/server');
jest.mock('../../lib/storage/serve-playlist');
jest.mock('../../lib/storage/resolve', () => ({
  ...jest.requireActual('../../lib/storage/resolve'),
  getStorageBundle: jest.fn(),
  getPrincipalFromSession: jest.fn(() => ({ id: 'owner-1', indexKey: 'pl-key' })),
}));
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({})) }));

import { POST } from '../../app/api/videos/[id]/regenerate/route';
import * as serverSupabase from '../../lib/supabase/server';
import * as servePlaylist from '../../lib/storage/serve-playlist';
import * as resolve from '../../lib/storage/resolve';
import * as gemini from '../../lib/gemini';

const PLAYLIST_ID = '11111111-2222-3333-4444-555555555555';
const VIDEO_ID = 'testVideoId1';
const MD = `---
video_id: testVideoId1
lang: EN
---

# T

**Channel:** C | **Duration:** 1:00 | **URL:** https://www.youtube.com/watch?v=testVideoId1

---

## 1. Intro

▶ [0:00–1:00](https://www.youtube.com/watch?v=testVideoId1&t=0s)

Clawcode.
`;

const mockPut = jest.fn();
const mockGet = jest.fn();
const mockUpdateVideoFields = jest.fn();
const mockUpdateVideoAnnotations = jest.fn();

function post(body: Record<string, unknown>, qs = `?playlist=${PLAYLIST_ID}`) {
  return POST(
    new Request(`http://localhost/api/videos/${VIDEO_ID}/regenerate${qs}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
    { params: Promise.resolve({ id: VIDEO_ID }) },
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  jest.mocked(serverSupabase.createServerSupabase).mockReturnValue({
    auth: { getUser: async () => ({ data: { user: { id: 'owner-1' } } }) },
  } as any);
  jest.mocked(servePlaylist.resolveOwnedPlaylistKey).mockResolvedValue('pl-key');
  mockGet.mockResolvedValue(Buffer.from(MD, 'utf-8'));
  mockPut.mockResolvedValue(undefined);
  mockUpdateVideoAnnotations.mockResolvedValue({ found: true });
  jest.mocked(resolve.getStorageBundle).mockReturnValue({
    metadataStore: {
      readIndex: async () => ({ videos: [{ id: VIDEO_ID, summaryMd: 'a.md', tags: ['ai'] }] }),
      updateVideoFields: mockUpdateVideoFields,
      updateVideoAnnotations: mockUpdateVideoAnnotations,
    },
    blobStore: { get: mockGet, put: mockPut },
  } as any);
  jest.mocked(gemini.fixSummary).mockResolvedValue(MD.replace('Clawcode', 'Claude Code'));
  jest.mocked(gemini.extractQuickView).mockResolvedValue({ tldr: 'New.', takeaways: ['P'] });
});

afterEach(() => { delete process.env.STORAGE_BACKEND; });

describe('regenerate — cloud branch', () => {
  it('401s when there is no authenticated user', async () => {
    jest.mocked(serverSupabase.createServerSupabase).mockReturnValue({
      auth: { getUser: async () => ({ data: { user: null } }) },
    } as any);
    expect((await post({ corrections: 'fix' })).status).toBe(401);
  });

  it('400s when playlist is not a UUID', async () => {
    expect((await post({ corrections: 'fix' }, '?playlist=nope')).status).toBe(400);
  });

  it('400s when outputFolder is sent in cloud mode', async () => {
    const res = await post({ corrections: 'fix', outputFolder: '/tmp/out' });
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe('outputFolder not valid on this backend');
  });

  it('404s when the playlist is not owned by the caller', async () => {
    jest.mocked(servePlaylist.resolveOwnedPlaylistKey).mockResolvedValue(null);
    expect((await post({ corrections: 'fix' })).status).toBe(404);
  });

  it('409s repair-needed when the markdown blob cannot be read — never "empty, correct it anyway"', async () => {
    mockGet.mockResolvedValue(null);
    const res = await post({ corrections: 'fix' });
    expect(res.status).toBe(409);
    expect((await res.json()).code).toBe('repair-needed');
    expect(jest.mocked(gemini.fixSummary)).not.toHaveBeenCalled();
  });

  it('writes the corrected body with blobStore.put — never putStaged/promote', async () => {
    await post({ corrections: 'fix Clawcode' });
    expect(mockPut).toHaveBeenCalledTimes(1);
    const [, key, bytes] = mockPut.mock.calls[0];
    expect(key).toBe('a.md');
    expect(bytes.toString('utf-8')).toContain('Claude Code');
  });

  it('returns applied for a real correction and no-corrections for a bare press', async () => {
    expect((await (await post({ corrections: 'fix X' })).json()).outcome).toBe('applied');
    expect((await (await post({})).json()).outcome).toBe('no-corrections');
  });

  it('does not write the blob on a bare press', async () => {
    await post({});
    expect(mockPut).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails for the right reason**

Run: `npx jest tests/api/regenerate-cloud.test.ts`
Expected: FAIL — every case returns 400 `outputFolder is required`, because `POST` has no cloud
branch yet.

- [ ] **Step 3: Split `POST` into two handlers**

Replace the top of `app/api/videos/[id]/regenerate/route.ts` (the current `export async function POST`
through the end of its body) with a dispatcher, and move the existing body verbatim into
`serveLocal`:

```ts
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId);
}
```

- [ ] **Step 4: Write `serveCloud`**

Append to the same file:

```ts
async function serveCloud(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) {
    return NextResponse.json({ error: 'invalid playlist' }, { status: 400 }); // before any DB call
  }

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  if (body && 'outputFolder' in body) {
    return NextResponse.json({ error: 'outputFolder not valid on this backend' }, { status: 400 });
  }
  const corrections = body?.corrections;
  if (corrections !== undefined && typeof corrections !== 'string') {
    return NextResponse.json({ error: 'corrections must be a string' }, { status: 400 });
  }
  if (typeof corrections === 'string' && [...corrections].length > MAX_CORRECTIONS_CHARS) {
    return NextResponse.json(
      { error: `corrections must be ${MAX_CORRECTIONS_CHARS} characters or fewer`, code: 'corrections-too-long' },
      { status: 400 },
    );
  }

  // EVERYTHING BELOW IS INSIDE THE TRY. On the local branch `getStorageBundle()` sits OUTSIDE it
  // (route.ts:36 before this task), so a missing client 500s instead of returning an error.
  try {
    assertVideoId(videoId);
    const playlistKey = await resolveOwnedPlaylistKey(supabase, playlistId, user.id); // owner-asserted
    if (!playlistKey) return NextResponse.json({ error: 'not found' }, { status: 404 });

    const principal = getPrincipalFromSession({ userId: user.id }, playlistKey);
    const { metadataStore: store, blobStore } = getStorageBundle({ supabaseClient: supabase });

    const index = await store.readIndex(principal);
    const video = index.videos.find((v) => v.id === videoId);
    if (!video) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    if (!video.summaryMd) return NextResponse.json({ error: 'no summary file for this video' }, { status: 422 });

    const mdBytes = await blobStore.get(principal, video.summaryMd);
    // A failed read is NOT an empty document. blobStore.get collapses RLS denials and transport
    // faults into the same null as a genuine 404 (blob-store.ts:57-66), so treating null as "no
    // content" would hand Gemini an empty string and overwrite a real document with its correction.
    // Same 409 the serve path returns (serve-summary-core.ts:66-67).
    if (!mdBytes) {
      return NextResponse.json({ error: 'repair needed', code: 'repair-needed' }, { status: 409 });
    }
    const mdContent = mdBytes.toString('utf-8');

    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    const storedCorrections = video.corrections ?? '';
    if (trimmedCorrections && trimmedCorrections !== storedCorrections) {
      const { found } = await store.updateVideoAnnotations(principal, videoId, { corrections: trimmedCorrections }, []);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    } else if (corrections === '' && storedCorrections !== '') {
      const { found } = await store.updateVideoAnnotations(principal, videoId, {}, ['corrections']);
      if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });
    }

    let tldr: string;
    let takeaways: string[];

    if (trimmedCorrections) {
      const applied = await applyCorrection({
        md: mdContent,
        corrections: trimmedCorrections,
        tags: video.tags ?? [],
        signal: request.signal,
        caps: CORRECTION_CAPS,
      });
      tldr = applied.tldr;
      takeaways = applied.takeaways;
      // `put`, NEVER writeArtifact. writeArtifact goes putStaged → promote, and promote is
      // create-if-absent (supabase-blob-store.ts:120-123): the key never changes on a correction, so
      // the final object always exists and the corrected body would be silently discarded while the
      // row was stamped `promoted`. That is backlog #22, and it applies to slice A too.
      await blobStore.put(principal, video.summaryMd, Buffer.from(applied.content, 'utf-8'), 'text/markdown');
    } else {
      // Bare press or explicit clear: quick-view still refreshes (spec §3), but NOTHING is written to
      // the blob — the prose did not change and a rewritten callout would move the body hash, which
      // under §2 option (e) books a ~6¢ magazine regeneration for a press that applied nothing.
      const qv = await extractQuickView(stripQuickViewCallout(mdContent), CORRECTION_CAPS);
      tldr = qv.tldr;
      takeaways = qv.takeaways;
    }

    const patch: Partial<Video> = { tldr, takeaways, summaryHtml: null };
    if (trimmedCorrections) {
      patch.mdGeneratedAt = new Date().toISOString();
      patch.mdCorrectionsHash = mdHash(trimmedCorrections);
    } else if (corrections === '') {
      patch.mdCorrectionsHash = mdHash('');
    }
    await store.updateVideoFields(principal, videoId, patch);

    return NextResponse.json({
      outcome: trimmedCorrections ? 'applied' : 'no-corrections',
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
  } catch (err) {
    logError(`regenerate:cloud:${videoId}`, err);
    if (err instanceof NonRetryableError && err.message.startsWith('correction input ')) {
      return NextResponse.json(
        { error: 'This summary is too long to correct', code: 'summary-too-large' },
        { status: 413 },
      );
    }
    return NextResponse.json({ error: errorSummary(err) }, { status: 500 });
  }
}
```

Add these imports at the top of the file:

```ts
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '../../../../../lib/supabase/server';
import { resolveOwnedPlaylistKey } from '../../../../../lib/storage/serve-playlist';
import { getPrincipalFromSession } from '../../../../../lib/storage/resolve';
import { applyCorrection, CORRECTION_CAPS } from '../../../../../lib/corrections/apply-core';
```

- [ ] **Step 5: Add the same `outcome` field to the local branch**

In `serveLocal`'s success response, add `outcome` so both branches return the §6 discriminator:

```ts
    return NextResponse.json({
      outcome: trimmedCorrections ? 'applied' : 'no-corrections',
      tldr,
      takeaways,
      corrections: trimmedCorrections,
      summaryHtml: null,
    });
```

- [ ] **Step 6: Run both route suites and confirm they pass**

Run: `npx jest tests/api/regenerate.test.ts tests/api/regenerate-cloud.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts`
Expected: PASS.

- [ ] **Step 7: Grep-guard against the wrong write**

Run: `grep -n "writeArtifact\|putStaged\|promote" app/api/videos/\[id\]/regenerate/route.ts`
Expected: **no output.** If any of the three appears, the correction can be silently discarded — stop
and re-read Step 4's comment.

- [ ] **Step 8: Typecheck and run the full suite, then commit**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass.

```bash
git add app/api/videos/[id]/regenerate/route.ts tests/api/regenerate-cloud.test.ts
git commit -m "feat(#23): cloud branch for the correction route, body written with blobStore.put"
```

---

### Task 9: Post-hoc spend recording

⛔ **BLOCKED ON A DECISION — read this before starting. Do not invent an RPC.**

Spec §5.2 says *"The route records **actual** spend to the ledger after the call returns."* Measured
2026-08-24, **there is no mechanism to do that and creating one is out of scope:**

| Fact | Evidence |
|---|---|
| `spend_ledger.actual_cents` has **no writer** anywhere — no SQL, no TypeScript | `grep -rn actual_cents supabase/migrations/` returns six hits, all *reads* inside cap arithmetic (`0011:114`, `0011:187`, `0012:88`, `0014:84`, `0018:63`, `0020:246`). `0011:15` says the column is *"inert in 1D; written by the deferred reconcile"* — that reconcile does not exist |
| The route cannot write it directly | `spend_ledger` grants are `service_role` only (`0011:18`), and this route runs on the user's session client |
| Using `service_role` here fails CI | `.github/workflows/ci.yml:69` runs `scripts/check-service-confinement.ts` — *"static guard: service_role stays out of request paths"* |
| Adding an RPC is a migration | spec §8: **"No migration — …"**. Slice A adds no schema change |
| There is also no **source** for the number | `grep -rn usageMetadata lib/` returns nothing. No code anywhere reads Gemini token usage, and `fixSummary` discards `result` after `result.response.text()` |

**Three ways forward. The user picks; the implementer does not.**

1. **Move recording to slice C** (`docs/backlog.md` #61), which already owns the money instruments.
   Slice A then ships capped-but-unrecorded, and §5.2 changes to say so. Smallest, and consistent
   with the slice boundary that was drawn to keep A off the money path.
2. **Accept one migration** for a single `record_correction_spend(p_cents int)` RPC. Contradicts §8's
   "no migration of any kind", which is currently load-bearing in the spec's own scope list.
3. **Log-only.** No ledger write; a structured line the operator can grep and a follow-up filed. The
   guardrails gain nothing — the daily cap still cannot see the spend — so §5.2's stated benefit
   ("the daily cap and per-owner budget see the spend on the *next* decision") does **not** hold.

**Steps 1–4 below implement the parts that are unblocked under ANY of the three** — capturing the
number. Step 5 is the sink and is gated on the decision.

**Files:**
- Modify: `lib/gemini.ts` (`fixSummary` returns usage alongside the text)
- Modify: `lib/corrections/apply-core.ts` (surface usage on the result)
- Test: `tests/lib/corrections/apply-core.test.ts`

**Interfaces:**
- Consumes: `PRICE_IN_PER_1M_CENTS = 30` and `PRICE_OUT_PER_1M_CENTS = 250` from
  `lib/gemini-cost.ts:33,35`.
- Produces:
  - `interface GeminiUsage { promptTokens: number; outputTokens: number }`
  - `fixSummary(...): Promise<{ text: string; usage: GeminiUsage | null }>` — ⚠ **this changes Task
    5's return type.** `usage` is `null` when the SDK response carries no `usageMetadata`; a null is
    reported, never silently treated as zero.
  - `ApplyCorrectionResult` gains `actualCents: number | null`
  - `correctionActualCents(usage: GeminiUsage): number` in `lib/gemini-cost.ts`

- [ ] **Step 1: Write the failing test**

Append to `tests/lib/corrections/apply-core.test.ts`:

```ts
describe('actual spend is measured, not estimated', () => {
  it('prices the real token counts', async () => {
    mockFixSummary.mockResolvedValue({
      text: CORRECTED,
      usage: { promptTokens: 10_000, outputTokens: 4_000 },
    });
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    // 10_000 * 30/1e6 + 4_000 * 250/1e6 = 0.3 + 1.0 = 1.3¢ → ceil 2
    expect(r.actualCents).toBe(2);
  });

  it('reports null rather than zero when the SDK returned no usageMetadata', async () => {
    mockFixSummary.mockResolvedValue({ text: CORRECTED, usage: null });
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    expect(r.actualCents).toBeNull();   // "could not measure" is NOT "cost nothing"
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `npx jest tests/lib/corrections/apply-core.test.ts`
Expected: FAIL — `r.actualCents` is `undefined`.

- [ ] **Step 3: Return usage from `fixSummary`**

In `lib/gemini.ts`, add the type and change the success path of the loop written in Task 5:

```ts
export interface GeminiUsage { promptTokens: number; outputTokens: number }
```

```ts
      assertNotTruncated(result);
      const corrected = result.response.text().trim();
      if (!corrected) throw new Error('Gemini returned empty content');
      const um = (result.response as { usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number } }).usageMetadata;
      // null, never 0. "The SDK did not report usage" and "this call cost nothing" are different
      // facts, and collapsing them would understate spend exactly where it matters.
      const usage = um && um.promptTokenCount != null && um.candidatesTokenCount != null
        ? { promptTokens: um.promptTokenCount, outputTokens: um.candidatesTokenCount }
        : null;
      return { text: corrected, usage };
```

and the declared return type to `Promise<{ text: string; usage: GeminiUsage | null }>`.

- [ ] **Step 4: Price it and surface it**

Add to `lib/gemini-cost.ts`:

```ts
/** Whole cents (rounded up) for one correction call, from MEASURED token counts. Uses the same
 *  dated prices as every other estimate here so a price change moves all of them together. */
export function correctionActualCents(usage: { promptTokens: number; outputTokens: number }): number {
  return Math.ceil(
    (usage.promptTokens * PRICE_IN_PER_1M_CENTS + usage.outputTokens * PRICE_OUT_PER_1M_CENTS) / 1e6,
  );
}
```

In `lib/corrections/apply-core.ts`, update the call site and the result:

```ts
export interface ApplyCorrectionResult {
  content: string;
  tldr: string;
  takeaways: string[];
  /** null means "the SDK reported no usage", NOT "free". */
  actualCents: number | null;
}
```

```ts
  const { text: fixed, usage } = await fixSummary(stripped, input.corrections, { signal: input.signal, caps: input.caps });
  assertStructurePreserved(stripped, fixed);
  const { tldr, takeaways } = await extractQuickView(fixed, input.caps);
  return {
    content: insertQuickViewCallout(fixed, tldr, takeaways, input.tags),
    tldr,
    takeaways,
    actualCents: usage ? correctionActualCents(usage) : null,
  };
```

Run: `npx jest tests/lib/corrections/apply-core.test.ts tests/lib/gemini-fix-summary.test.ts`
Expected: PASS (update the Task 5 tests' `mockResolvedValue` to the new `{ text, usage }` shape).

- [ ] **Step 5: ⛔ THE SINK — do not implement until the user has chosen**

Under **option 3 (log-only)** this is the whole step, and it is what the plan can specify today.
It goes **inside** `serveCloud`'s `if (trimmedCorrections) { … }` block from Task 8, immediately after
the `blobStore.put` — `applied` is scoped to that block, and a bare press has no spend to report:

```ts
    // Spend visibility, spec §5.2. NOT a ledger write: spend_ledger.actual_cents has no writer
    // (0011:15 "inert in 1D; written by the deferred reconcile" — which does not exist), the table
    // is service_role-only (0011:18), and service_role is statically barred from request paths
    // (.github/workflows/ci.yml:69). Adding an RPC is a migration, which §8 excludes from slice A.
    // Tracked as the slice-A residue on backlog #61.
    console.info(
      `[correction-spend] owner=${principal.id} video=${videoId} cents=${applied.actualCents ?? 'unmeasured'}`,
    );
```

Under **option 1** delete this step and amend §5.2. Under **option 2** the migration and its RPC are
a task this plan does not contain — stop and re-plan rather than improvising one here.

- [ ] **Step 6: Typecheck, full suite, commit**

Run: `npx tsc --noEmit && npx jest`

```bash
git add lib/gemini.ts lib/gemini-cost.ts lib/corrections/apply-core.ts tests/lib/corrections/apply-core.test.ts tests/lib/gemini-fix-summary.test.ts
git commit -m "feat(#23): measure a correction's actual spend; ledger sink blocked on a decision"
```

---

### Task 10: Give the owner's page a stale fallback on the other non-ok statuses (r5 H1)

Before Task 4, a corrected document was `isFresh === true`, so `serve-doc.ts:78-79` short-circuited
and the owner got **200 every time**. After Task 4 the same document falls into the reserve path on
every serve until a regeneration succeeds — and five of its exits become **503 with no second look at
the bucket**:

```ts
// lib/html-doc/serve-summary-core.ts:120-123
case 'busy':               return { ok: false, status: 503, error: 'generating, retry shortly' };
case 'attempts_exhausted': return { ok: false, status: 503, error: 'temporarily unavailable, try later' };
case 'at_capacity':        return { ok: false, status: 503, error: 'at capacity' };
```

Only `owner_over_budget` consults `readTitleStableModel` (`serve-doc.ts:146-151`). Attempts are keyed
`(owner_id, doc_key, day)` with `max_serve_attempts` default **5**
(`0012_serve_model_charge.sql:13,21,80`), so an owner whose regeneration keeps failing loses their own
page for **the rest of the UTC day** while a readable model sits in storage. Option (e) protected the
anonymous reader and left the paying owner worse off; this task completes the argument.

**Files:**
- Modify: `lib/html-doc/serve-doc.ts:144-151`
- Test: `tests/lib/html-doc/serve-doc-mapping.test.ts`

**Interfaces:**
- Consumes: `readTitleStableModel(args: { blobStore: ReadOnlyBlobStore; principal: Principal; base: string; titles: string[] }): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'none' }>` — `read-model.ts:57`, **unchanged by Task 4**.
- Produces: no signature change. `ResolveResult`'s `ok` arm already carries `stale?: boolean`
  (`serve-doc.ts:36`), so the caller needs no change.

- [ ] **Step 1: Write the failing test**

Append to `tests/lib/html-doc/serve-doc-mapping.test.ts`:

```ts
describe('a stale-but-readable model beats a 503 (r5 H1)', () => {
  it('serves the title-stable model when attempts are exhausted', async () => {
    mockReserve.mockResolvedValue({ ok: true, data: [{ status: 'attempts_exhausted', release_token: null }] });
    mockReadTitleStableModel.mockResolvedValue({ status: 'ok', model: FAKE_MODEL });
    const r = await resolveMagazineModel(baseArgs());
    expect(r).toEqual({ status: 'ok', model: FAKE_MODEL, stale: true });
  });

  it('serves the title-stable model at capacity', async () => {
    mockReserve.mockResolvedValue({ ok: true, data: [{ status: 'at_capacity', release_token: null }] });
    mockReadTitleStableModel.mockResolvedValue({ status: 'ok', model: FAKE_MODEL });
    const r = await resolveMagazineModel(baseArgs());
    expect(r).toEqual({ status: 'ok', model: FAKE_MODEL, stale: true });
  });

  it('still reports attempts_exhausted when there is genuinely no model to serve', async () => {
    mockReserve.mockResolvedValue({ ok: true, data: [{ status: 'attempts_exhausted', release_token: null }] });
    mockReadTitleStableModel.mockResolvedValue({ status: 'none' });
    expect(await resolveMagazineModel(baseArgs())).toEqual({ status: 'attempts_exhausted' });
  });

  it('does NOT reach for a stale model on `denied` — that is an authorization answer, not a capacity one', async () => {
    mockReserve.mockResolvedValue({ ok: true, data: [{ status: 'denied', release_token: null }] });
    expect(await resolveMagazineModel(baseArgs())).toEqual({ status: 'denied' });
    expect(mockReadTitleStableModel).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `npx jest tests/lib/html-doc/serve-doc-mapping.test.ts`
Expected: FAIL — the first two cases receive `{ status: 'attempts_exhausted' }` / `{ status: 'at_capacity' }`.

- [ ] **Step 3: Extend the fallback**

Replace `lib/html-doc/serve-doc.ts:144-151`:

```ts
    // CAPACITY answers, not authorization answers: the owner is entitled to this document, we just
    // cannot regenerate it right now. Serving the stale-but-readable render beats a 503 — the same
    // trade backlog #57 made for the share path, and the reason option (e) invalidates rather than
    // deletes. Without this, a correction can take a page that was unconditionally 200 and make it
    // 503 for the rest of the UTC day (attempts are keyed (owner, doc, day), K=5 —
    // 0012_serve_model_charge.sql:13,21,80).
    //
    // `denied` is deliberately NOT here: it is an authorization answer, and serving a cached render
    // to someone we just refused would leak the document.
    case 'attempts_exhausted':
    case 'at_capacity':
    case 'owner_over_budget': {
      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
      if (staleRead.status === 'ok') return { status: 'ok', model: staleRead.model, stale: true };
      return reserveStatus === 'owner_over_budget'
        ? { status: 'over_budget' }
        : reserveStatus === 'at_capacity'
          ? { status: 'at_capacity' }
          : { status: 'attempts_exhausted' };
    }
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `npx jest tests/lib/html-doc/serve-doc-mapping.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck, full suite, commit**

Run: `npx tsc --noEmit && npx jest`

```bash
git add lib/html-doc/serve-doc.ts tests/lib/html-doc/serve-doc-mapping.test.ts
git commit -m "fix(#23): serve the stale model on attempts_exhausted and at_capacity, not a 503"
```

---

### Task 11: The UI — reachable in cloud mode, and the outcome discriminator

`VideoMenu.tsx:181` gates the corrections item out of cloud mode with
`{!cloudMode && video.summaryMd && (`, and `CorrectionsPanel.tsx:52` posts
`{ outputFolder, corrections }` — which the cloud branch rejects. Both need to become scope-aware.

**Files:**
- Modify: `components/VideoMenu.tsx:181`
- Modify: `components/CorrectionsPanel.tsx:44-70, 95-105`
- Modify: `components/VideoRow.tsx:199-207` (the panel's props)
- Test: `tests/components/CorrectionsPanel.test.tsx` (create)

**Interfaces:**
- Consumes: `useScope(): Scope` from `@/lib/client/scope`, where
  `Scope = { mode: 'local'; outputFolder: string; baseOutputFolder: string } | { mode: 'cloud'; playlistId: string }`
  (`lib/client/scope.tsx:10-12`). `VideoMenu.tsx:47` and `VideoRow.tsx:49` already call it.
- Consumes: the route's response shape from Task 8 —
  `{ outcome: 'applied' | 'no-corrections'; tldr: string; takeaways: string[]; corrections?: string; summaryHtml: null }`
  and error bodies `{ error: string; code?: 'corrections-too-long' | 'summary-too-large' | 'repair-needed' }`.
- Produces: `CorrectionsPanel` drops its `outputFolder` prop and reads the scope itself.

- [ ] **Step 1: Write the failing test**

Create `tests/components/CorrectionsPanel.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CorrectionsPanel from '@/components/CorrectionsPanel';
import { ScopeProvider, type Scope } from '@/lib/client/scope';

const CLOUD: Scope = { mode: 'cloud', playlistId: '11111111-2222-3333-4444-555555555555' };
const LOCAL: Scope = { mode: 'local', outputFolder: '/tmp/out', baseOutputFolder: '/tmp' };

function renderIn(scope: Scope, initial?: string) {
  return render(
    <ScopeProvider scope={scope}>
      <CorrectionsPanel videoId="v1" initialCorrections={initial} onClose={() => {}} onSuccess={() => {}} />
    </ScopeProvider>,
  );
}

beforeEach(() => { global.fetch = jest.fn(); });

it('posts ?playlist=<uuid> and NO outputFolder in cloud mode', async () => {
  jest.mocked(global.fetch).mockResolvedValue(
    new Response(JSON.stringify({ outcome: 'applied', tldr: 't', takeaways: [] }), { status: 200 }),
  );
  renderIn(CLOUD, 'fix X');
  await userEvent.click(screen.getByRole('button', { name: /regenerate/i }));
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(String(url)).toContain(`?playlist=${CLOUD.mode === 'cloud' ? CLOUD.playlistId : ''}`);
  expect(JSON.parse(String(init!.body))).toEqual({ corrections: 'fix X' });
});

it('posts outputFolder and no query string in local mode', async () => {
  jest.mocked(global.fetch).mockResolvedValue(
    new Response(JSON.stringify({ outcome: 'applied', tldr: 't', takeaways: [] }), { status: 200 }),
  );
  renderIn(LOCAL, 'fix X');
  await userEvent.click(screen.getByRole('button', { name: /regenerate/i }));
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(String(url)).not.toContain('?playlist=');
  expect(JSON.parse(String(init!.body))).toEqual({ outputFolder: '/tmp/out', corrections: 'fix X' });
});

it('reports no-corrections so a press that changed nothing does not read as a bug', async () => {
  jest.mocked(global.fetch).mockResolvedValue(
    new Response(JSON.stringify({ outcome: 'no-corrections', tldr: 't', takeaways: [] }), { status: 200 }),
  );
  renderIn(CLOUD, '');
  await userEvent.click(screen.getByRole('button', { name: /regenerate/i }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/no corrections to apply/i));
});

it('shows the over-cap message, not a generic failure', async () => {
  jest.mocked(global.fetch).mockResolvedValue(
    new Response(JSON.stringify({ error: 'This summary is too long to correct', code: 'summary-too-large' }), { status: 413 }),
  );
  renderIn(CLOUD, 'fix X');
  await userEvent.click(screen.getByRole('button', { name: /regenerate/i }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/too long to correct/i));
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `npx jest tests/components/CorrectionsPanel.test.tsx`
Expected: FAIL — TypeScript reports the missing required `outputFolder` prop.

- [ ] **Step 3: Make the panel scope-aware**

In `components/CorrectionsPanel.tsx`, remove `outputFolder` from `CorrectionsPanelProps`, add
`import { useScope } from '@/lib/client/scope';`, and replace `handleRegenerate`'s fetch (`:49-53`):

```ts
  const scope = useScope();
  const [outcome, setOutcome] = useState<'applied' | 'no-corrections' | null>(null);
```

```ts
      const qs = scope.mode === 'cloud' ? `?playlist=${encodeURIComponent(scope.playlistId)}` : '';
      // The cloud branch REJECTS outputFolder (it is a local filesystem concept), so send one or the
      // other — never both.
      const payload = scope.mode === 'cloud'
        ? { corrections }
        : { outputFolder: scope.outputFolder, corrections };
      const res = await fetch(`/api/videos/${encodeURIComponent(videoId)}/regenerate${qs}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({})) as Record<string, unknown>;
      if (!res.ok) {
        setError((data.error as string | undefined) ?? 'Regeneration failed');
        return;
      }
      setOutcome(data.outcome === 'no-corrections' ? 'no-corrections' : 'applied');
```

Add the §6 discriminator to the JSX, beside the existing `{error && …}` at `:110`:

```tsx
        {outcome === 'no-corrections' && (
          <p role="status" className="text-xs text-zinc-400 mt-1">
            No corrections to apply — the quick reference was refreshed.
          </p>
        )}
```

And annotate the `maxLength` at `:105`:

```tsx
          maxLength={1000}   {/* mirrored server-side as MAX_CORRECTIONS_CHARS (lib/corrections/apply-core.ts) */}
```

- [ ] **Step 4: Update the two call sites**

`components/VideoRow.tsx:199-207` — drop the prop:

```tsx
        <CorrectionsPanel
          videoId={video.id}
          initialCorrections={video.corrections}
          onClose={() => setShowCorrections(false)}
          onSuccess={(patch) => onAnnotationChange(video.id, patch)}
        />
```

`components/VideoMenu.tsx:181` — drop the cloud gate:

```tsx
      {video.summaryMd && (
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `npx jest tests/components/CorrectionsPanel.test.tsx`
Expected: PASS, 4 tests.

- [ ] **Step 6: Typecheck, full suite, commit**

Run: `npx tsc --noEmit && npx jest`

```bash
git add components/CorrectionsPanel.tsx components/VideoMenu.tsx components/VideoRow.tsx tests/components/CorrectionsPanel.test.tsx
git commit -m "feat(#23): corrections UI reachable in cloud mode, with the outcome discriminator"
```

---

### Task 12: The spec's falsifiers, asserted at the consumer

Spec §7 says **assert at the consumer**, not at the code that produces the value. Tasks 1–11 each
tested their own unit; this task adds the end-to-end rows that no single task owns, and the
mutation-checks that stop a green suite from certifying a no-op.

**Files:**
- Test: `tests/integration/corrections-cloud.int.test.ts` (create)
- Test: `tests/lib/corrections/falsifiers.test.ts` (create)

**Interfaces:**
- Consumes: everything Tasks 1–11 produce. No new production code — **if a falsifier cannot be
  written without changing production code, that is a finding, not a licence to change it.** Stop and
  report.

⚠ **The integration file needs a live Supabase stack** (`docs/dev-process.md`, "Not yet in CI"). If
none is running, the run must **fail loudly and say NOT RUN** — a skipped money assertion that
reports green is worse than a red one.

- [ ] **Step 1: Write the unit-level falsifiers**

Create `tests/lib/corrections/falsifiers.test.ts`:

```ts
import { isFresh } from '@/lib/html-doc/read-model';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { stripQuickViewCallout, insertQuickViewCallout } from '@/lib/quick-view-callout';

const env = (over: Record<string, unknown> = {}) => ({
  sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A'],
  generatorVersion: GENERATOR_VERSION, model: { sections: [{ lead: 'l', bullets: [] }] },
  ...over,
} as any);

describe('§7 — the reader sees the correction', () => {
  it('a corrected body makes the cached model stale', () => {
    const before = 'body one';
    const after = 'body two';
    expect(isFresh(env({ sourceMdHash: mdHash(before) }), ['A'], mdHash(after))).toBe(false);
  });

  it('an unchanged body keeps it fresh — no regeneration loop', () => {
    const body = 'body one';
    expect(isFresh(env({ sourceMdHash: mdHash(body) }), ['A'], mdHash(body))).toBe(true);
  });

  it('a legacy envelope with no sourceMdHash stays fresh and moves no money', () => {
    expect(isFresh(env(), ['A'], mdHash('anything'))).toBe(true);
  });
});

describe('§7 — a bare press disturbs nothing the sync decision reads', () => {
  const DOC = '---\nvideo_id: v\n---\n\n# T\n\n**Channel:** C\n\n---\n\n## 1. A\n\nProse.\n';

  it('a callout-only change moves the whole-body hash — which is why the write is skipped', () => {
    const a = insertQuickViewCallout(DOC, 'TLDR A', ['x'], []);
    const b = insertQuickViewCallout(stripQuickViewCallout(a), 'TLDR B', ['y'], []);
    expect(mdHash(a)).not.toBe(mdHash(b));
  });

  it('…while the PROSE hash is invariant under it', () => {
    const a = insertQuickViewCallout(DOC, 'TLDR A', ['x'], []);
    const b = insertQuickViewCallout(stripQuickViewCallout(a), 'TLDR B', ['y'], []);
    expect(mdHash(stripQuickViewCallout(a))).toBe(mdHash(stripQuickViewCallout(b)));
  });
});
```

Run: `npx jest tests/lib/corrections/falsifiers.test.ts`
Expected: PASS, 5 tests.

- [ ] **Step 2: Write the integration falsifiers**

Create `tests/integration/corrections-cloud.int.test.ts`. It uses the existing harness —
`adminClient`, `newUser`, `signInAs` from `./helpers/clients` and `seedPlaylist`,
`seedPromotedVideo` from `./helpers/seed` — the same imports
`tests/integration/serve-doc-materialize.test.ts:2-3` uses.

```ts
// NOT RUN WITHOUT A LIVE STACK. global-setup.ts applies migrations and refuses to run if it cannot.
// A skipped money assertion reporting green is worse than a red one — do NOT add describe.skip here.
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';
import { POST } from '@/app/api/videos/[id]/regenerate/route';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { deriveClassASignals } from '@/lib/cloud-sync/backfill';
import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';

jest.mock('@/lib/gemini', () => ({
  fixSummary: jest.fn(async (md: string) => ({
    text: md.replace('Clawcode', 'Claude Code'),
    usage: { promptTokens: 1000, outputTokens: 500 },
  })),
  extractQuickView: jest.fn(async () => ({ tldr: 'Corrected TL;DR.', takeaways: ['Corrected point'] })),
}));
import { fixSummary } from '@/lib/gemini';

const svc = adminClient();

const MD = `---
video_id: vvvvvvvvvvv
lang: EN
---

# T

**Channel:** C | **Duration:** 1:00 | **URL:** https://www.youtube.com/watch?v=vvvvvvvvvvv

---

## 1. Intro

▶ [0:00–1:00](https://www.youtube.com/watch?v=vvvvvvvvvvv&t=0s)

Clawcode is great.
`;

/** Seeds an owned playlist + promoted video and puts MD at the video's summaryMd key, so the route
 *  has a real body to read through the SAME principal it will write with. */
async function seedCorrectable() {
  const ownerId = await newUser();
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId } = await seedPromotedVideo(svc, { ownerId, playlistId });
  const principal = { id: ownerId, indexKey: playlistKey };
  const blob = new SupabaseBlobStore(svc);
  const key = `${videoId}.md`;
  await blob.put(principal, key, Buffer.from(MD, 'utf-8'), 'text/markdown');
  await svc.rpc('merge_video_data', {
    p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryMd: key, tags: ['ai', 'rag'] },
  });
  return { ownerId, playlistId, playlistKey, videoId, principal, blob, key };
}

function press(videoId: string, playlistId: string, body: Record<string, unknown>) {
  return POST(
    new Request(`http://localhost/api/videos/${videoId}/regenerate?playlist=${playlistId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }),
    { params: Promise.resolve({ id: videoId }) },
  );
}

beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { delete process.env.STORAGE_BACKEND; });

it('§7 cloud correction works — the stored blob holds the corrected text, not the original', async () => {
  const s = await seedCorrectable();
  await signInAs(s.ownerId);
  const res = await press(s.videoId, s.playlistId, { corrections: 'Clawcode -> Claude Code' });
  expect(res.status).toBe(200);
  const stored = (await s.blob.get(s.principal, s.key))!.toString('utf-8');
  expect(stored).toContain('Claude Code');
  expect(stored).not.toContain('Clawcode is great');
});

it('§7 and the card — tldr, takeaways AND the Concepts line reflect the corrected document', async () => {
  const s = await seedCorrectable();
  await signInAs(s.ownerId);
  await press(s.videoId, s.playlistId, { corrections: 'Clawcode -> Claude Code' });
  const { data } = await svc.from('videos').select('data').eq('video_id', s.videoId).single();
  expect(data!.data.tldr).toBe('Corrected TL;DR.');
  expect(data!.data.takeaways).toEqual(['Corrected point']);
  const stored = (await s.blob.get(s.principal, s.key))!.toString('utf-8');
  expect(stored).toContain('> **Concepts:** ai · rag');
});

it('§7 clearing works on Supabase — corrections are absent afterwards', async () => {
  const s = await seedCorrectable();
  await signInAs(s.ownerId);
  await press(s.videoId, s.playlistId, { corrections: 'something' });
  await press(s.videoId, s.playlistId, { corrections: '' });
  const { data } = await svc.from('videos').select('data').eq('video_id', s.videoId).single();
  expect(data!.data.corrections).toBeUndefined();
});

it('§7 clearing an ALREADY-EMPTY field issues no call, so annotationsEditedAt does not move', async () => {
  const s = await seedCorrectable();
  await signInAs(s.ownerId);
  const before = (await svc.from('videos').select('data').eq('video_id', s.videoId).single()).data!.data;
  await press(s.videoId, s.playlistId, { corrections: '' });
  const after = (await svc.from('videos').select('data').eq('video_id', s.videoId).single()).data!.data;
  expect(after.annotationsEditedAt).toEqual(before.annotationsEditedAt);
});

it('§7 a BARE press on a needsRegen=true video leaves it TRUE', async () => {
  const s = await seedCorrectable();
  // Sync delivers corrections without doing MD work — the sync-run.ts:358 path.
  await svc.rpc('update_video_annotations', {
    p_playlist_id: s.playlistId, p_video_id: s.videoId, p_set: { corrections: 'C2' }, p_clear: [],
  });
  await signInAs(s.ownerId);
  const cur = mdHash('C2');
  const read = async () => {
    const { data } = await svc.from('videos').select('data').eq('video_id', s.videoId).single();
    const body = (await s.blob.get(s.principal, s.key))!.toString('utf-8');
    return deriveClassASignals({ ...data!.data, id: s.videoId } as never, body);
  };
  const beforeDecision = reconcileClassA({ local: await read(), cloud: await read(), reconciledCorrectionsHash: cur });
  expect(beforeDecision.needsRegen).toBe(true);

  await press(s.videoId, s.playlistId, {});   // bare press: no corrections key at all

  const afterDecision = reconcileClassA({ local: await read(), cloud: await read(), reconciledCorrectionsHash: cur });
  expect(afterDecision.needsRegen).toBe(true);   // still owed — the press applied nothing
  expect(fixSummary).not.toHaveBeenCalled();
});

it('§7 an oversized corrections field never reaches Gemini — 400, and no Gemini call', async () => {
  const s = await seedCorrectable();
  await signInAs(s.ownerId);
  const res = await press(s.videoId, s.playlistId, { corrections: 'x'.repeat(1001) });
  expect(res.status).toBe(400);
  expect((await res.json()).code).toBe('corrections-too-long');
  expect(fixSummary).not.toHaveBeenCalled();
});
```

**Five more rows need the serve path and belong beside the existing serve integration tests** — add
them to `tests/integration/serve-doc-materialize.test.ts`, which already has the reserve/ledger
harness (`setOwnerCap`, `utcDay`) this needs:

The file already has `seed()`, `parsed()`, `MD_BODY`, `utcDay()`, `setOwnerCap()` and a
`generateMagazineModel` mock at `:11-23`. Three rows can be written directly against them:

```ts
const PRE = '# T\n\n## 1. Intro\nbefore\n';
const POST = '# T\n\n## 1. Intro\nafter\n';

it('§7 the reader sees the correction — a changed body regenerates on the next owner serve', async () => {
  const ownerId = await newUser();
  const s = await seed(ownerId);
  await signInAs(ownerId);
  const principal = { id: ownerId, indexKey: s.playlist_key };
  await writeModelEnvelope(principal, s.videoId, {
    sourceMd: `${s.videoId}.md`, generatedAt: 'then', sourceSections: ['Intro'],
    generatorVersion: GENERATOR_VERSION, model: { sections: [{ lead: 'OLD', bullets: [] }] } as never,
    sourceMdHash: mdHash(PRE),          // the PRE-correction body
  }, new SupabaseBlobStore(svc));

  const r = await resolveMagazineModel({ ...baseArgs(s), parsed: parsed(), mdBody: POST });

  expect(r.status).toBe('ok');
  expect(generateMagazineModel).toHaveBeenCalledTimes(1);   // the stale envelope was refused
  expect((r as { model: { sections: Array<{ lead: string }> } }).model.sections[0].lead).toBe('L');
});

it('§7 …and fires ONCE — a second serve of the same corrected body calls Gemini no more', async () => {
  const ownerId = await newUser();
  const s = await seed(ownerId);
  await signInAs(ownerId);
  await resolveMagazineModel({ ...baseArgs(s), parsed: parsed(), mdBody: POST });
  await resolveMagazineModel({ ...baseArgs(s), parsed: parsed(), mdBody: POST });
  expect(generateMagazineModel).toHaveBeenCalledTimes(1);   // no regeneration loop
});

it('§7 a legacy envelope with NO sourceMdHash serves from cache and moves no money', async () => {
  const ownerId = await newUser();
  const s = await seed(ownerId);
  await signInAs(ownerId);
  const principal = { id: ownerId, indexKey: s.playlist_key };
  await writeModelEnvelope(principal, s.videoId, {
    sourceMd: `${s.videoId}.md`, generatedAt: 'then', sourceSections: ['Intro'],
    generatorVersion: GENERATOR_VERSION,
    model: { sections: [{ lead: 'LEGACY', bullets: [] }] } as never,
    // sourceMdHash deliberately OMITTED — pre-2026-07-17 envelope.
  }, new SupabaseBlobStore(svc));
  const ledgerBefore = (await svc.from('spend_ledger').select('*').eq('day', utcDay()).maybeSingle()).data;

  const r = await resolveMagazineModel({ ...baseArgs(s), parsed: parsed(), mdBody: POST });

  expect(generateMagazineModel).not.toHaveBeenCalled();     // absent cannot prove stale
  expect((r as { model: { sections: Array<{ lead: string }> } }).model.sections[0].lead).toBe('LEGACY');
  const ledgerAfter = (await svc.from('spend_ledger').select('*').eq('day', utcDay()).maybeSingle()).data;
  expect(ledgerAfter?.reserved_cents ?? 0).toBe(ledgerBefore?.reserved_cents ?? 0);
});
```

`baseArgs(s)` is the existing per-file argument builder for `resolveMagazineModel`
(`supabaseClient`, `blobStore`, `principal`, `playlistId`, `videoId`, `base`, `language`) — read it
at the top of that file and reuse it rather than rebuilding the object.

⚠ **Two rows are specified but NOT written here, because their harness is in files this plan has not
read.** Do not improvise helper names — open the file named, copy its setup, then write the test:

| Row | Where the setup lives | The assertion |
|---|---|---|
| the share link still returns 200 immediately after a correction | `tests/integration/share-route.test.ts` (token minting + `GET /s/<token>`) | status **200** and the rendered gists present — `readTitleStableModel` is untouched by Task 4, so this is the row that fails if anyone reintroduces a delete |
| `attempts_exhausted` + a corrected body serves the stale render | `tests/integration/serve-owner-budget.test.ts` (drives `serve_model_charge` for `(owner_id, doc_key, utcDay())`) | `{ status: 'ok', stale: true }`, **not** 503 — Task 10's row |

Every negative case asserts **which** error, never "any error".

- [ ] **Step 3: Mutation-check every guard this slice added**

⚠ **This is the step that stops (e) shipping as a no-op.** For each row, break the implementation by
hand, run the named test, confirm it goes **RED**, then restore and confirm **GREEN**. A guard whose
mutation survives is untested, which is indistinguishable from "does nothing".

| Mutation | Test that must go RED |
|---|---|
| Delete the `sourceMdHash` conjunct in `isFresh` | `read-model.test.ts` → *false when sourceMdHash is present and does not match* |
| Change the conjunct to `envelope.sourceMdHash !== currentMdHash` (inverted) | `falsifiers.test.ts` → *an unchanged body keeps it fresh* |
| Make the absent case invalidate (`envelope.sourceMdHash === currentMdHash` alone) | `read-model.test.ts` → *true when sourceMdHash is ABSENT* |
| Make the bare-press write unconditional again | `regenerate.test.ts` → *does NOT write the file on a bare press* |
| Restore `mdCorrectionsHash: mdHash(effectiveCorrections)` unconditionally | `regenerate-stamp.test.ts` → *a bare regenerate omits mdCorrectionsHash entirely* |
| Pass `undefined` as `withCaps`' second argument | `gemini-fix-summary.test.ts` → *applies maxOutputTokens and thinkingBudget:0* |
| Drop the loop-top abort guard in `fixSummary` | `gemini-fix-summary.test.ts` → *aborts DURING the backoff* |
| Replace `abortableSleep` with `new Promise(setTimeout)` | `gemini-fix-summary.test.ts` → *aborts DURING the backoff* |
| Drop the read-before-write comparison in the route | `regenerate.test.ts` → *issues NO call when the incoming text equals the stored text* |
| Swap `blobStore.put` for `writeArtifact` | `regenerate-cloud.test.ts` → *writes the corrected body with blobStore.put* |
| Remove `attempts_exhausted` from the stale fallback | `serve-doc-mapping.test.ts` → *serves the title-stable model when attempts are exhausted* |

- [ ] **Step 4: Record the result**

Write the mutation table above into the PR body with a PASS/FAIL column filled in from what you
actually observed, and state plainly which integration tests were **NOT RUN** and why. A tick that
does not say what it was verified against is not evidence.

- [ ] **Step 5: Full suite, typecheck, commit**

Run: `npx tsc --noEmit && npx jest`
Expected: no type errors; all suites pass.

```bash
git add tests/lib/corrections/falsifiers.test.ts tests/integration/corrections-cloud.int.test.ts
git commit -m "test(#23): spec §7 falsifiers at the consumer, plus the mutation-check table"
```
