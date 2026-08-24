# Measurement — what breaks if a bare press does NOT rewrite the markdown

Not a review. A measurement, requested after r5 B1 was folded in (`a8fef30`), to replace a three-way
fork with facts. **No recommendation on the fork — that is the user's.**

**Question.** `route.ts:63-69` always runs `extractQuickView` → `insertQuickViewCallout` → write, even
when `fixed === stripped`. Is that write load-bearing or incidental?

## Headline

| | Answer |
|---|---|
| Does the callout affect what the ~6¢ magazine regeneration is computed from? | **No — provably not.** It lands in the preamble `parseSections` discards. Measured, PROBE 1 |
| Does anything read the callout out of the file? | **Yes.** `parseSummaryMarkdown` parses it, and the magazine/PDF/share renders all display it. Measured, PROBE 2 |
| How many of the 18 tests fail if the write is skipped? | **Zero.** So does the rest of the suite: **268 suites / 2,722 tests, all green** with the write removed. Executed |
| Would the row and the file diverge? | **Yes**, on one named axis: the card shows the new TL;DR, every rendered/downloaded surface shows the old one |
| Is the naive `mdHash(new) !== mdHash(old)` variant useless? | **Largely yes.** But a **prose-scoped** comparison is exact, not probabilistic. Measured, PROBE 4 |

**The sharpest single fact:** the magazine model's inputs are `parsed.sections` (titles + prose) —
`serve-doc.ts:169`, `generate.ts:41` — and its freshness key is `sourceSections`, also
`parsed.sections` (`serve-doc.ts:71,177`; `generate.ts:53`). The callout is in **neither**. So under
option (e), a callout-only body change books a ~6¢ regeneration whose output is computed from
**byte-identical inputs**. That is not a stale cache being refreshed; it is the same call, run again,
paid for again.

## How this was measured

Everything below was **executed**, not reasoned. To avoid the
`an-instrument-that-edits-the-repo-corrupts-its-peers` failure — a concurrent Codex half may be
reading this tree — all mutation happened in a **detached `git worktree`** in the scratchpad with
`node_modules` symlinked. The worktree was removed afterwards and
`git status --porcelain` on the main checkout is **empty**. No tracked file in the working repo was
touched.

The patch under measurement, applied in the worktree only:

```diff
-    await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');
+    if (trimmedCorrections) await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');
```

i.e. **the call stays, the write is skipped when nothing was applied** — exactly the change the
question asks about, and a different change from removing `extractQuickView`.

The five PROBE assertions below were run as a temporary spec in the worktree against the **real**
`parseSummaryMarkdown`, `insertQuickViewCallout`, `stripQuickViewCallout` and `mdHash` — no
reimplementation, no mocks.

---

## Q1 — who reads the callout, and can it touch the model?

### The callout is invisible to everything the magazine model is built from

`insertQuickViewCallout` splices at the **first** `\n\n---\n`, the metadata/body divider
(`lib/quick-view-callout.ts:33-34`), which is before the first `## ` heading. `parseSections` then
discards everything ahead of the first `##`:

```ts
// lib/html-doc/parse.ts:45-47
// Fence-aware, line-based split on H2 headings. …
// The first chunk (before any ##) is preamble — discarded.
```

Its lines all begin `> `, so none can match `^##\s+` even if the position ever changed.

> **PROBE 1 — passed.** Two documents identical except for the callout (`TLDR ALPHA.` + 2 takeaways
> vs `TLDR BETA.` + 1 takeaway) produce **byte-identical `parsed.sections`** — `JSON.stringify`
> equality across `numeral`, `title`, `prose` and `timeRange` — and both equal the callout-free base.

**Therefore a callout-only change cannot alter:** `sourceSections` (`serve-doc.ts:177` ← `:71`;
`generate.ts:53`), the section count, any section's prose, any `▶` tuple, or any gist — the model is
generated from `parsed.sections.map(s => ({ title, prose }))` (`serve-doc.ts:169`,
`generate.ts:41`). It also cannot affect `sameTitles`, `readTitleStableModel`'s section-count check,
or `dig-merge.ts:62`.

### But `parseSummaryMarkdown` does read it, and the renders display it

```ts
// lib/html-doc/parse.ts:126
const { tldr, takeaways } = parseCallout(md);
```

`parseCallout` (`:88-109`) pulls `**TL;DR:**` and the `**Key Takeaways:**` bullets straight out of the
blockquote. `renderMagazineHtml` then renders them — from the **file**, never from the row, and never
from the cached envelope:

```ts
// lib/html-doc/render.ts:72-80
const callout = parsed.tldr ? `<div class="callout">
    <div class="lbl">Quick Reference</div>
    <p>${esc(parsed.tldr)}</p> …
```

> **PROBE 2 — passed.** `parseSummaryMarkdown(withA).tldr === 'TLDR ALPHA.'`,
> `parseSummaryMarkdown(withB).tldr === 'TLDR BETA.'`, takeaways likewise.

**Consumer trace, all verified by reading the call site:**

| Surface | Reads the callout from | Line |
|---|---|---|
| Magazine HTML (owner) | the **file** — `parsed.tldr` | `serve-summary-core.ts:99-102` → `app/api/html/[id]/route.ts:88` → `render.ts:72-80` |
| PDF | the **file**, same `parsed` | `app/api/pdf/[id]/route.ts:53` |
| Share `/s/<token>` | the **file**, same `parsed` | `app/s/[token]/route.ts:110` |
| Download `format=md` | the **raw bytes**, no parse at all | `app/api/html/[id]/route.ts:75-81` (`load.mdBytes`, money short-circuit) |
| Local Obsidian / file view | the raw file on disk | n/a — the file *is* the surface |
| Local re-render | the **file** | `rerender.ts:60,71` |
| Video card / quick-view panel | the **row** (`tldr` prop, or a fetch) | `components/VideoQuickView.tsx:23-34, 80-85` |

So the split is clean: **one surface reads the row, every other surface reads the file.**

---

## Q2 — do the 18 tests assert the write? No. Neither does anything else.

`fs.promises.writeFile` is mocked in both suites, and the mock is **only ever configured, never
asserted**. Full enumeration of every occurrence:

```
tests/api/regenerate.test.ts:28              const mockWriteFile = jest.mocked(fs.promises.writeFile);
tests/api/regenerate.test.ts:67              mockWriteFile.mockResolvedValue(undefined);
tests/lib/cloud-sync/regenerate-stamp.test.ts:36   const mockWriteFile = jest.mocked(fs.promises.writeFile);
tests/lib/cloud-sync/regenerate-stamp.test.ts:76   mockWriteFile.mockResolvedValue(undefined);
```

No `expect(mockWriteFile)` anywhere. The 14 + 4 = **18** `it()` blocks assert `mockFixSummary`,
`mockUpdateVideoFields` and the JSON response body; none reads the file back.

**Executed, not inferred:**

| Run | Result |
|---|---|
| Baseline, main checkout, the two suites | **18 passed / 18** |
| Worktree, write skipped on a bare press, the two suites | **18 passed / 18** — **0 failures** |
| Worktree, write skipped, **whole unit suite** | **268 suites, 2,722 tests, 1 snapshot — all passed**, 25.5 s |

**So the answer to "how many would fail" is zero, and the stronger statement holds: nothing in the
2,722-test suite observes the bare-press write.** §3's claim that "18 tests cover this path" is
accurate about the `extractQuickView` **call** and says nothing about the **write** — they are, as the
brief suspected, different changes, and only the call is covered.

⚠ Scope of that measurement: unit suite only. `test:integration` and `test:e2e` were **NOT RUN** —
they need a live Supabase/Postgres stack (`docs/dev-process.md`, "Not yet in CI"). **NOT VERIFIED**
whether any integration or Playwright assertion observes the file after a bare press. Given that no
unit test does, and that the e2e suite never exercises corrections at all (backlog #44 records the
cloud e2e never mounts the main pane), I would expect none — but I did not measure it.

---

## Q3 — the divergence, and where a user would see it

With the write skipped, `route.ts:85-89` still updates the row (`tldr`, `takeaways`,
`summaryHtml: null`) while the file's callout keeps its previous text. Per the Q1 table, that is
observable:

> **The video card shows the new TL;DR and takeaways. The magazine page, the PDF, the share page and
> the downloaded `.md` all show the old ones.** One user, two numbers, same video.

Two things bound how much that matters, both measured rather than argued:

1. **On a bare press the prose did not change** — `fixed === stripped` by construction
   (`route.ts:63`). So the "new" `tldr`/`takeaways` are a fresh LLM sample of **unchanged text**, not
   a more-correct summary of changed text. The divergence is between two equally-valid extractions of
   the same prose, not between right and wrong.
2. **`summaryHtml: null` still fires** (`route.ts:86`), so any cached rendered HTML is invalidated and
   re-derived from the file — producing the old callout again, consistently. Skipping the write does
   not create a *third* state.

The inverse also holds and is worth stating: **today, with the write, the divergence is the other way
round for anyone holding a share link.** The file gets the new callout immediately; the magazine
*model* keeps pre-correction gists until an owner serve. Neither option produces a fully coherent
document at all times.

---

## Q4 — the cheap variant: the naive form is largely useless, the prose-scoped form is exact

**Naive form** — write only when `mdHash(updatedContent) !== mdHash(mdContent)`:

> **PROBE 5 — passed.** `insertQuickViewCallout(stripQuickViewCallout(withA), 'TLDR ALPHA.', ['a1','a2'], ['t1'])`
> is **byte-identical** to `withA`. Strip→insert round-trips exactly when `tldr`, `takeaways` and
> `tags` are unchanged.

So the naive comparison is *correct* — it does skip when `extractQuickView` returns the same strings —
but it only helps as often as `extractQuickView` is stable. **The config does not pin stability:**
`extractQuickView`'s `generationConfig` is
`withCaps({ responseMimeType, responseSchema }, caps, caps?.summaryOutputTokens ?? 0)`
(`lib/gemini.ts:432-437`) — **no `temperature`, no `seed`, no `topK`**, so the API default applies and
identical output is not contracted. **NOT VERIFIED:** the empirical repeat rate — measuring it means
live Gemini calls, which I did not make. What is verified is that nothing in the code makes it
deterministic, so the variant cannot be relied on.

**Prose-scoped form** — compare the document *without* its callout:

> **PROBE 3 — passed.** `mdHash(withA) !== mdHash(withB)`: a callout-only change **does** move the
> whole-body hash. (This is r5 B1's mechanism, now measured directly rather than argued.)
>
> **PROBE 4 — passed.** `mdHash(stripQuickViewCallout(withA)) === mdHash(stripQuickViewCallout(withB))`:
> the prose-scoped hash is **invariant** under a callout-only change.

On a bare press `stripQuickViewCallout(updatedContent) === stripped === stripQuickViewCallout(mdContent)`
holds **by construction**, not by luck. So a prose-scoped guard skips the write on **100%** of bare
presses and never skips a real correction, with no dependence on model determinism.

⚠ One consequence the fork should carry: a prose-scoped guard makes the *write* deterministic but does
**not** change what `sourceMdHash` hashes. `mdHash` is applied to the whole body at both writers
(`generate.ts:59`, `serve-doc.ts:181`), so if the write is skipped the hash never moves and (e) is
satisfied; but if anyone later re-enables a callout-only write, the ~6¢ returns. The two decisions —
*when to write* and *what to hash* — are separable, and only the first is on the table here.

---

## Everything I could not verify

- **Integration and e2e coverage of the bare-press write** — both suites need a live stack and were
  not run. **NOT VERIFIED.**
- **How often `extractQuickView` returns identical output** — needs live Gemini spend. **NOT
  VERIFIED.** Only the absence of any determinism setting in the config is verified.
- **The production population of documents whose callout differs from their row** — needs the
  database. **NOT VERIFIED**, and unrelated to this question except that it sizes the divergence in
  Q3 if the write is skipped going forward but historical files already diverge.
