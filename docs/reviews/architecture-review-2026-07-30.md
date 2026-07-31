# Architecture Review — 2026-07-30

First run of `improve-codebase-architecture` on this codebase. Trial run for
**backlog #17** (proposed periodic architecture review gate).

Method: three parallel explorers (rendering, storage seam, job/money path), then
every load-bearing claim spot-checked by hand against the code. Where a claim did
not verify, it was dropped or corrected — noted inline.

**Nothing here is a proposal yet.** This document explains *what was found and why
it costs you something*. Designing the fix comes after you pick one.

> **What "fixed" means for each finding:**
> [`architecture-findings-acceptance.md`](architecture-findings-acceptance.md) — per-finding
> invariant, mechanical criteria, and the specific ways each fix can go green without working.
> Measure current state any time with `python3 scripts/check-arch-findings.py`; it also runs in
> CI as a **ratchet**, so these numbers can no longer quietly grow.

---

## First: the five words this review uses

The vocabulary is small, and everything below leans on it. Plain versions:

| Term | Plain meaning |
|---|---|
| **Module** | Anything with an inside and an outside. A function, a file, a package. |
| **Interface** | Everything a caller must *know* to use it correctly — not just the argument types, but the ordering rules, the invariants, the "you must call X first" facts. |
| **Deep** | A lot of behaviour behind a small interface. You learn a little, you get a lot. |
| **Shallow** | The interface is nearly as complicated as the implementation. You had to learn everything anyway, so the module bought you nothing. |
| **Seam** | The place where an interface sits — a spot where behaviour can be swapped without editing the code around it. |

### The deletion test

The main tool. **Imagine deleting the module.** Then ask what happens to the
complexity it held:

- It **vanishes** → the module was a pass-through. It wasn't hiding anything.
- It **reappears in five different callers** → the module was earning its keep.

### A tiny worked example

Shallow:

```ts
function getVideoTitle(v: Video) { return v.title; }
```

Delete it, and every caller writes `v.title`. Complexity didn't concentrate — it
just moved, and you now maintain a name for it. **Shallow.**

Deep:

```ts
await writeArtifact({ ... });   // stages, verifies, commits, promotes, stamps metadata
```

Delete it, and five callers each have to remember a five-step ordering where
step 3 must not happen before step 2. Complexity **reappears everywhere**. **Deep.**

That second example is real, and it is finding #2 — with a twist.

---

## The one-paragraph summary

The codebase has **good seams that callers reach around**. `CONTEXT.md` defines a
Storage Seam; eleven route modules check `STORAGE_BACKEND` themselves and fork
instead. A module implements the exact commit→promote protocol the glossary
defines; it has zero production callers while five writers hand-roll their own
version. There is no in-memory adapter, so tests mock *modules* rather than
substituting at the *seam*. The pattern repeats in rendering and in the money
path. In every case the right structure is already there — it's just optional,
and callers opted out.

---

## 1. The Storage Seam doesn't hold

### The evidence

`app/api/videos/[id]/quick-view/route.ts` — the whole route is a fork:

```ts
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-.../i;   // ← copy-pasted into 11 files

export async function GET(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId);
}
```

Verified: **11 route files** outside `resolve.ts` do this.

### Why it costs you

This route answers one question — *"give me this video's quick view."* That
question has nothing to do with which storage backend is configured. But the
route is now **two routes in one file**, and the business logic after the fork is
byte-identical on both sides.

Concretely, adding a field to the quick-view response means:

1. edit `serveLocal`
2. edit `serveCloud`
3. remember that step 2 exists

Step 3 is the whole problem. Nothing fails if you forget — the local tests still
pass, and the cloud path silently lacks the field.

### The tell that it isn't really about storage

`lib/pdf/generate-doc-pdf.ts:69`:

```ts
const launchOpts = process.env.STORAGE_BACKEND === 'supabase'
  ? { timeout: timeoutMs, args: ['--no-sandbox', '--disable-dev-shm-usage'] }
  : { timeout: timeoutMs };
```

This reads the **storage** selector to choose **Chromium sandbox flags**. Once a
variable is readable everywhere, it stops meaning "which store" and starts meaning
"am I in the container." That's a seam leaking into an unrelated decision.

### What "deep" would look like

*Illustrative only — not a proposal.* The route stops asking which backend it is
on. Something upstream resolves the adapter once, hands it over, and the route
reads:

```ts
export async function GET(request, { params }) {
  const { store, principal, videoId } = await resolveRequest(request, params);
  const video = await store.readVideo(principal, videoId);
  ...                                    // one path, not two
}
```

**Locality**: the backend decision lives in one module. **Tests**: the route is
tested once against a substituted adapter instead of twice.

---

## 2. The commit→promote protocol has no owner

This is the most striking finding, so it's worth walking slowly.

### The domain rule

`CONTEXT.md` defines **Promoted**:

> an artifact whose blob has completed its final write and is safe to serve. An
> artifact that is *committed* but not yet *promoted* may still be finalizing.

So writing an artifact safely has a required order: stage the bytes → verify they
landed → mark committed → promote → mark promoted. Get it wrong and a reader can
see a half-written artifact.

### The module that implements it exactly right

`lib/storage/supabase/consistency.ts`:

```ts
/**
 * Sequence: putStaged → verify temp exists → updateVideoFields(committed)
 *           → promote → updateVideoFields(promoted)
 */
export async function writeArtifact(opts: { ... }): Promise<void> {
  const ref = await opts.blob.putStaged(...);
  if (!(await opts.blob.exists(opts.principal, ref.tempKey))) {
    throw new Error('staged upload not verified');
  }
  await opts.meta.updateVideoFields(..., { artifacts: { [kind]: { status: 'committed' } } });
  await opts.blob.promote(ref);
  await opts.meta.updateVideoFields(..., { artifacts: { [kind]: { status: 'promoted' } } });
}
```

**Verified: this function has zero production callers.** Its only callers are 8
tests.

### What the real writers do instead

**Writer 1** — `lib/job-queue/summary-handler.ts`, the same protocol retyped:

```ts
const ref = await bundle.blobStore.putStaged(bundle.principal, key, ..., 'text/markdown');
if (!(await bundle.blobStore.exists(bundle.principal, ref.tempKey))) {
  throw new Error('staged upload not verified');
}
await persistSummary(serviceClient, ..., 'committed');   // raw RPC, not the interface
await bundle.blobStore.promote(ref);
await persistSummary(serviceClient, ..., 'promoted');
```

**Writer 2** — `lib/dig/cloud/write-dig-section-blob.ts`, **no metadata stamping at all**:

```ts
const ref = await input.blobStore.putStaged(input.principal, key, ...);
if (!(await input.blobStore.exists(input.principal, ref.tempKey))) {
  throw new Error('staged dig upload not verified');
}
await input.blobStore.promote(ref);
return key;                       // ← no committed/promoted stamps
```

**Writer 3** — `lib/cloud-sync/sync-run.ts`, which **abandons `promote()` entirely**:

```ts
// promote() is NOT uniform across backends here: local rename overwrites, but
// SupabaseBlobStore.promote() is create-if-absent ... so on the cloud winner-copy
// path the loser's stale body would survive. Commit the VERIFIED staged bytes to
// the final key with an atomic upsert ...
await loser.blob.put(loser.p, key, staged, 'text/markdown');
await loser.blob.delete(loser.p, ref.tempKey).catch(() => {});
```

Plus two more variants elsewhere. **Three different verification strategies**
across the five: `exists(tempKey)`, `get(tempKey)` + hash compare, and
re-read-the-index-and-assert.

### Why it costs you

Two things, and the second is worse.

**First**, the domain rule lives in five heads instead of one module. A change to
what "promoted" means is a five-site edit where each site looks different.

**Second — and this is the real damage — writer 3's comment is a bug report about
the seam.** The two adapters disagree on what `promote()` means: local overwrites,
Supabase skips if the target exists. That's a genuine contract violation at the
seam. But because no module owns the protocol, the discovery got handled *by one
caller working around it locally*, in a comment. The other four writers still call
`promote()` believing it does the same thing on both backends.

That's the cost of a protocol with no owner: **a fix applied at one call site
instead of at the seam** leaves everyone else holding the original bug.

### Note on the deletion test

Normally "zero callers" means delete it. Here the conclusion inverts: the module
is the *right* shape and the callers are wrong. Deleting `writeArtifact` would
remove the only correct statement of the rule in the codebase. The 8 tests
currently guard **dead code** — they'd be guarding production if the writers went
through it.

---

## 3. The seam is not the test surface

### The principle

> *The interface is the test surface.* Callers and tests cross the same seam. If
> you have to test *past* the interface, the module is the wrong shape.

### The evidence

**No in-memory adapter exists** anywhere in `lib/` or `tests/` (verified). So each
test builds its own partial fake:

```ts
// tests/lib/pdf/generate-doc-pdf.test.ts — 1 of BlobStore's 9 methods
const fakeBlobStore = { put: fakePut } as unknown as typeof localBlobStore;
```

`as unknown as` is the tell. It means *"the compiler would reject this, so tell it
to look away."* Anything the code touches beyond `put` crashes at runtime instead
of failing at compile time.

Three integration tests instead build decorators that hand-forward **all ten**
members around a real Supabase store. Adding one method to `BlobStore` means
editing three test files that have nothing to do with the change.

**And local tests must write inside your home directory:**

```ts
// tests/lib/archive.test.ts
// Must be under homedir — assertOutputFolder enforces this
const dir = path.join(os.homedir(), `.tmp-archive-test-${crypto.randomUUID()}`);
```

`os.tmpdir()` — the normal answer — is unavailable, because `getPrincipal` runs a
home-containment check. A production security guard is dictating where tests write
files.

**The consequence:** 16 test files `jest.mock('lib/index-store')` and 10 mock
`@/lib/storage/resolve`. Tests substitute at the **module** level — reaching in and
replacing a file wholesale — rather than at the **interface**. Module mocking has
become the de-facto seam, and it's a seam that doesn't typecheck.

### Why it costs you

- A fake that implements 1 of 9 methods **cannot catch** a caller that starts using
  a second method. The test still passes.
- 63 integration files need a running Supabase stack and are forced `--runInBand`
  (serial), because they share one database.
- Every interface change ripples into unrelated test files.

### What "deep" would look like

*Illustrative only.* One real in-memory adapter, implementing the interface
honestly, used everywhere:

```ts
const store = new InMemoryBlobStore();      // typechecks; all 9 methods real
await runTheThingUnderTest({ blobStore: store });
expect(store.get(principal, 'x.md')).resolves.toEqual(...);
```

**Leverage**: one adapter pays back across ~26 currently-mocking test files. This
is also why it's the highest-value pick — it unlocks testing for findings #1, #2
and #7.

---

## 4. The release rule lives in five places

### The evidence

`lib/job-queue/worker-runner.ts:66`:

```ts
// RELEASE only on a positively-not-metered class-A failure, gated by the live-verification flag.
const release = releaseGateOpen()
  && classifyGeminiFailure(e, signal) === 'release'
  && !billing.metered;
```

`lib/html-doc/serve-doc.ts:130`:

```ts
// Same rule as generation: refund only a positively-not-metered class-A failure.
const released = releaseGateOpen()
  && classifyGeminiFailure(err, signal) === 'release'
  && !billing.metered;
```

Character-for-character the same rule. The comment on the second one — *"Same rule
as generation"* — is doing the work a shared module should do.

> **Correction to my own review:** my first grep for this returned nothing and I
> nearly reported the claim as unverified. The expression is line-wrapped, so a
> single-line pattern missed it. The explorer was right; my check was wrong.

Three more copies exist as plpgsql predicates in
`supabase/migrations/0020_reservation_release.sql`, and they are **not identical** —
two gate on `attempts = 0`, the third on `p_metered`.

### Why it costs you

This is the money path. The rule decides whether a user gets refunded.

Worse, `JobQueue.fail` takes three independent booleans (`retryable`,
`billableSucceeded`, `metered`) — eight combinations, only some valid. The database
defends against a bad one:

> *"belt-and-suspenders vs a contradictory p_metered=true + billable=false call"*

When SQL has to defend against its own TypeScript caller, the **type is permitting
a state that cannot be true**. The interface is letting callers express nonsense,
so the innermost layer polices it.

---

## 5. Two renderers restate one document

### The evidence

`lib/html-doc/render.ts:48` and `lib/html-doc/render-dig-deeper.ts:58` —
character-identical:

```ts
function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;')
          .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
```

Neither is exported, so **neither can be unit-tested**. This is HTML escaping — the
function that stops a section title from injecting script.

Roughly 35–40% of `render.ts` is restated in `render-dig-deeper.ts`, including the
11-step document shell built independently in both.

### The most revealing part

`lib/html-doc/theme.ts`:

```ts
/**
 * Shared magazine palette prefix (keys: page, card, ink).
 * render.ts inserts `meta` after `ink` (between PRE and POST).
 * Split into pre/post to allow byte-identical insertion.
 */
export const BASE_PALETTE_LIGHT_PRE: Palette = { ... }
```

The palette was cut in half **so that one renderer can insert a key in the middle
and keep a golden snapshot byte-identical**.

That is an interface shaped by a test's output format rather than by the domain.
The snapshot test is supposed to describe the code; here the code was contorted to
satisfy the snapshot. Worth noticing as a smell in its own right: when a test
forces an odd shape, the test is usually asserting something too specific.

*Backlog #5 (palette dedup) covers the palette only. The actual duplication is
much larger.*

---

## 6. The shipped nav engine has no unit coverage

### The evidence

`lib/html-doc/nav.ts` — 315 of 607 lines are JavaScript inside a template literal.
The file warns about itself, twice:

```ts
// DRIFT WARNING: the inline JS functions (applyDug/applyIdle) intentionally
// duplicate the TS helpers above and must be kept in sync — the inline string
// is not covered by jsdom tests.
```

So there are two copies of six behaviours: a TypeScript version and an ES5-string
version. **The TypeScript ones are unit-tested. The ES5 ones are what ships.**

The timing constants `180000 / 2000 / 2000 / 10000` are declared once and
re-hardcoded twice more inside the strings.

### Why it costs you

Your tests verify a **mirror** of the shipped code. A bug fixed in the tested copy
and forgotten in the string copy leaves production broken with a green suite. The
comment says "keep the two in sync by hand" — that's a maintenance obligation the
compiler could carry instead.

Real verification currently lives in **4,371 lines of Playwright**, which is slow
and only exercises the paths someone thought to click.

---

## 7. The local app has no seam and no test

| | `CloudApp.tsx` (339 lines) | `LocalApp.tsx` (690 lines) |
|---|---|---|
| Direct `fetch()` calls | 0 | 10 |
| Goes through `lib/client/api.ts` | yes | **no** |
| Test files | 2 | **0** |

Same story as everywhere else: the seam exists, `CloudApp` uses it and is
testable, `LocalApp` reaches around it and isn't. Seven behaviours are duplicated
between them — the 7-predicate filter chain, the stale-response guard, and
`handleFilterChange` byte-identical.

The largest untested module in the tree is untested *because* it has no seam, not
because nobody got around to it.

---

## Defects found along the way

Not architecture — actual bugs the friction produced. Each verified.

| # | Defect | Evidence |
|---|---|---|
| D1 | **Cloud dug sections are ordered lexicographically.** `load-dig-for-serve.ts` builds `dug` straight from `blobStore.list()` with no sort, so `1000.r9.md` sorts before `65.r9.md`. The local path guarantees ascending `startSec`, and `dig-merge` assumes it. | read the loop — no sort |
| D2 | **No reaper for `serve_model_charge`.** Nothing cron-shaped exists in the migrations, and `sweep_expired_leases` never mentions `reserved_cents` (0 occurrences in its body). A process death between reserve and settle appears to strand the reservation permanently. | grep + function body |
| D3 | **A newline in a section title corrupts cloud dig frontmatter.** The two YAML escapers are asymmetric — the local one escapes `\n`, the cloud one doesn't. The parse failure is swallowed by a `catch`, silently dropping a section the user paid for. | both escapers read |
| D4 | **`<meta name="generator" content="dig-deeper-doc v1">` is write-only.** Exactly one occurrence in the tree — nothing reads it. The dig-deeper doc has no cache-version story while the summary doc has two. | grep: 1 hit |
| D5 | **A style-only (MINOR) doc-version bump re-summarizes the whole playlist on cloud.** The documented rule (`lib/doc-version.ts:4`) is *MAJOR ⇒ re-summarize, MINOR ⇒ re-render*, and `needsResummarize()` encodes it — with **one caller, the local path** (`ensure.ts:41`). The cloud skip compares the flattened `docVersionKey()` string `"major.minor"` (`summary-handler.ts:89`), so a minor bump fails the equality and runs a full Gemini summarize per video. Local costs **0** API calls for the same bump; cloud serve also costs 0. Only cloud *ingest* pays — and per W1 the result is then discarded by `promote()`. | code read + no cloud plan/spec mentions major vs minor |
| D6 | **The magazine model's drift guard is a title proxy; the exact signal exists and is unused.** `isFresh()` = `sameTitles(...) && generatorVersion` (`read-model.ts:20-25`) — `docVersion` is absent and `sourceMdHash` is never consulted, though it is written into every fresh envelope (`generate.ts:59`, `serve-doc.ts:124`). A prose-only MD change with stable titles is therefore served as fresh **forever**. Already documented, in the wrong module: `companion.ts:43-45`. `fixSummary`'s prompt *pins headings on purpose*, so this is the designed shape of a corrections regenerate, not a coincidence. | `tests/lib/html-doc/section-identity-after-resummarize.test.ts` (5 passing) + companion.ts comment |
| D7 | **Section identity is answered three ways; two of them are the title string.** Magazine model ↔ section = positional + exact title; dig ↔ section step 1 = numeric `startSec`; step 2 = exact title fallback (`dig-merge.ts:10-12`). `startSec` is minted by `ensureSectionTimestamps` **inside** `generateSummary` (`gemini.ts:387`), unique only *within* a generation and carried solely in the MD's `▶` line — nothing anchors it across regenerations. So a re-summarize breaks step 1 always, and when it also rewords a heading, **paid dug content orphans off its section**. A single retitled heading also nulls the gists of *every* section (`sameTitles` is all-or-nothing). | same test file — orphaning and all-or-nothing both asserted |

### Reference: when the magazine model changes (established while proving D5–D7)

The **magazine model** (CONTEXT.md:45) is the per-section `{lead, bullets}` structure the
rendered HTML is built from — produced by a capped Gemini call, cached as `models/<base>.json`,
**lazily materialized on view**, never pre-produced by the worker.

**Every event that writes or invalidates it:**

| # | Event | Path |
|---|---|---|
| 1 | absent → first materialization on view | cloud `serve-doc.ts` (under `reserve_serve_model`); local `runHtmlDoc` |
| 2 | **drift** — MD section titles ≠ `envelope.sourceSections` | both, on view |
| 3 | **`GENERATOR_VERSION`** mismatch (`'magazine-skim v2'`) | cloud `isFresh`; local HTML-cache check `build-doc-html.ts:56` |
| 4 | explicit delete on re-summarize | local only — `ensure.ts:51` |
| 5 | `summaryHtml: null` → next view runs `runHtmlDoc`, which regenerates **unconditionally** | local corrections route |
| 6 | sync ships a replacement envelope, or deletes a provably-stale one | `companion.ts`, keyed on **`sourceMdHash`** |

**Never invalidated by:** a `docVersion` bump (major or minor — `docVersion` is not in the
freshness test), or an MD body change that leaves section titles intact.

**Does a regenerated MD require a regenerated model? YES — always.** The model is derived from
each section's *prose*, so any MD body change makes it stale by definition. The correct
predicate is "the MD body changed" — exactly what `sourceMdHash` measures. The implemented
predicate is "the titles changed", which is a proxy that fails precisely when a regeneration
deliberately preserves headings. Rows 4, 5 and 6 above exist because three different authors
each noticed their path needed more than the proxy and fixed it locally; the **cloud summary
handler is the one MD writer that adds no compensating step** and relies on the proxy alone.

### Evidence for finding #2: a SECOND local workaround of the promote divergence

The review claimed the pattern "a fix applied at one call site instead of at the seam" from one
instance (`sync-run.ts:329`). There are **two**. `serve-doc.ts:100-103`:

> The model uses `writeModelEnvelope` (plain `put` → `upload(upsert:true)`), **NOT** staged→promote:
> a regenerated model on drift / version-bump must OVERWRITE the stale blob so the doc self-heals
> (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).

A second author independently hit the divergence, reasoned it through correctly, and worked
around it in a comment at their own call site. The measurable pattern: **the writers that
avoided the bug are exactly the ones that stopped calling `promote()`** — both switched to
`put`/upsert. The three still calling it are the three that assume uniformity. The interface is
teaching every careful caller to abandon it, which is the argument for fixing it at the seam.

### ⚠️ UPDATE 2026-07-30 — finding #2 is a CONFIRMED DEFECT, not just friction

`tests/lib/dig/write-dig-section-blob-promote.test.ts` drives the real
`writeDigSectionBlob` against `InMemoryBlobStore` in both promote semantics:

- local (`overwrite`) → re-dug section serves **REGENERATED** content ✅
- Supabase (`create-if-absent`) → re-dug section serves **ORIGINAL** content ❌

`digSectionKey(base, sectionId)` is deterministic, so re-digging a section at the same
`DIG_GENERATOR_VERSION` writes the SAME key. The final already exists, Supabase `promote()`
skips the move, and the stale body survives. W2 is also the one writer that stamps **no
metadata at all**, so nothing records that the newer content was discarded.

#### Scope of the trace below — W2 ONLY

This finding names FIVE writers. The trace that follows covers **W2, the dig writer**, and
nothing else. Live `promote()` callers still assuming uniformity: `summary-handler.ts:178`
(W1), `write-dig-section-blob.ts:50` (W2), `sync-run.ts:210` (W3). **W1 and W3 are untraced.**

### ⚠️ W1 (summary) — CONFIRMED DEFECT 2026-07-30. Finding #2 is a BUG FIX, not a refactor.

`tests/lib/job-queue/summary-handler-promote-divergence.test.ts` drives the **real**
`makeSummaryHandler` (real key derivation, real write sequence) against `InMemoryBlobStore`:

- local (`overwrite`) → re-summarized video serves **REGENERATED** body ✅
- Supabase (`create-if-absent`) → serves **ORIGINAL** body ❌

**Why W1 is worse than W2.** W2 is protected by an accident of key design — the dig key embeds
the generator version (`.r{V}`), so a bump yields a fresh key and cannot collide. The summary
key has no version anywhere: `baseName = padSerial(serial) + slugify(title)`
(`summary-handler.ts:96`), and `reserve_video_slot` deliberately returns the **existing** serial
for a known video (`0009…sql:88` — `if v_serial is not null then return v_serial`), so the key
is **stable for the life of the video**.

**The reachable path is a designed re-run, not a crash path** *(corrected 2026-07-30 — an
earlier revision of this section wrongly implied it fires automatically on deploy; it does not.
It needs an explicit user action)*:

1. `CURRENT_DOC_VERSION` bumps (now `3.3`, so it has moved before) and is deployed
2. **a user re-submits the same playlist URL** to `POST /api/jobs`. This is the ONLY production
   trigger for a cloud summary job — verified: `enqueuePlaylist` is the sole caller of
   `enqueuer.enqueue` for `kind: 'summary'`, and `app/api/videos/[id]/regenerate` is a
   **local-only** route (`fs.readFile` + `outputFolder`) that enqueues nothing
3. the new version opens a new `jobs_idem_active` slot, so jobs are created for **every** video
   in that playlist — at the *same* version they would have joined the completed rows instead
4. the idempotency skip at `summary-handler.ts:85-91` does **not** fire on a version mismatch
5. full charged Gemini summarize runs
6. `promote()` lands on the occupied key → Supabase **skips the move** → old body survives
7. `persistSummary(..., 'promoted')` stamps the **new** docVersion regardless

Unlike the dig case, **the two bodies are supposed to differ** — that is what a doc-version bump
is *for*. End state on cloud: the database asserts a version its blob does not contain, for
every already-summarized video in that playlist, silently, at full Gemini cost. Local is
unaffected.

**What is NOT a trigger:** viewing a stale doc. A version bump makes the *rendered HTML* stale
(`summaryNeedsWork`, `lib/html-doc/eligibility.ts:12`) and that re-renders from the **existing
markdown** — it never runs `summary-handler` and never touches the summary blob. Only the
rendered-HTML cache is lazily refreshed today, not the markdown.

> ⚠️ **Design constraint for any future lazy per-video regeneration.** If "re-generate the
> summary when the user opens a stale doc" is ever built, this defect stops needing an explicit
> re-submit and starts firing **on view** — silently, per video, at Gemini cost, with the DB
> claiming the new version each time. Fix finding #2 **before** building lazy regeneration, or
> the feature ships a data-correctness bug on day one.

The 4th test in that file passes and is the silent half: the handler reports
`['committed','promoted']` at the current docVersion no matter what the blob ended up holding.

**W3 (`sync-run.ts:210`) remains untraced.**

#### Scope note retained: the trace below covers W2 only

#### W2 (dig) reachability — TRACED 2026-07-30. Reachable, but narrow; severity is LOW.

The writer-level defect is real. The path to it is much narrower than the test implies,
because three plausible routes turn out to be blocked:

| Route | Blocked by |
|---|---|
| User re-clicks "dig" | `lib/dig/cloud/enqueue-dig-core.ts:39` — blob-existence dedupe → `ready`, no enqueue, no charge |
| Two concurrent triggers | `jobs_idem_active` (`0009…sql:11`) covers `queued/active/completed` — the second joins |
| `DIG_GENERATOR_VERSION` bump | the version is **in the key** (`dig-blob-key.ts:22`, `.r{V}`) → fresh key, never a collision |

The one route that IS open — same-job re-execution:

1. handler generates → `writeDigSectionBlob` promotes → final key occupied (`dig-handler.ts:119`)
2. `queue.complete()` runs **after** that write (`worker-runner.ts:56` → `:59`); `!ok`/throw
   leaves the row `active`
3. `sweep` requeues expired-lease active jobs with **no backoff** (`0008_jobs_queue.sql:173-182`)
4. handler re-runs, regenerates (charged), promotes into the occupied key → local overwrites,
   Supabase discards the new body silently

**Why severity is LOW:** on every reachable path both bodies are legitimate digs of the same
section at the same generator version. The user is shown the *first* successful generation
instead of the *last* — not wrong content. This is a **divergence + a silence**, not data loss.

**The one bad conjunction worth keeping on file:** blob written → `complete()` throws →
`fail()` marks the job terminally `failed` (NOT in `jobs_idem_active`, which excludes
`failed`/`cancelled`) → a later `exists()` false-negative → fresh job, fresh Gemini charge,
output discarded with no trace. Note `SupabaseBlobStore.exists` is `get() !== null` and `get`
swallows every failure (the adapter self-declares `provesAbsence = false`), so the false
negative is a transient blip, not an exotic case. Rare, but each link is independently real.

**Composition note:** the blob check and the idem index are a two-layer defence that nobody
designed — neither file mentions the other, and the index's exclusion of `failed`/`cancelled`
is precisely where the blob check is weakest. This is the class of defect per-task review
cannot see, which is why Phase 6 exists.

Fix direction: route W1/W2 through `writeArtifact` (this finding), or make `promote()`
uniform across adapters. Do not fix it a second time at a single call site — that is what
`sync-run.ts:322` already did, and it is why the other writers never learned.

### ⚠️ UPDATE 2026-07-30 — finding #2 is a CONFIRMED DEFECT, not just friction

`tests/lib/dig/write-dig-section-blob-promote.test.ts` drives the real
`writeDigSectionBlob` against `InMemoryBlobStore` in both promote semantics:

- local (`overwrite`) → re-dug section serves **REGENERATED** content ✅
- Supabase (`create-if-absent`) → re-dug section serves **ORIGINAL** content ❌

`digSectionKey(base, sectionId)` is deterministic, so re-digging a section at the same
`DIG_GENERATOR_VERSION` writes the SAME key. The final already exists, Supabase `promote()`
skips the move, and the stale body survives. W2 is also the one writer that stamps **no
metadata at all**, so nothing records that the newer content was discarded.

Severity depends on whether the dig path can re-dig an already-dug section at the same
version — **not yet traced.** The writer-level defect is proven; the reachability is not.

Fix direction: route W1/W2 through `writeArtifact` (this finding), or make `promote()`
uniform across adapters. Do not fix it a second time at a single call site — that is what
`sync-run.ts:322` already did, and it is why the other writers never learned.

**D2 is the one to look at first** — it's on the money path, and unlike the others
it fails silently in production rather than in a document.

---

## Where this leaves backlog #17

The trial run produced findings a per-task diff review structurally could not:
every finding here is about *the relationship between files*, and per-task review
only ever sees one change at a time.

Three observations for deciding whether to make this a standing gate:

1. **It found real defects, not just style opinions** — four, one on the money path.
2. **The verification step mattered.** Explorer claims were mostly right, but I
   dropped and corrected claims on both sides — including one where my own check
   was the thing that was wrong. Agent output is a lead, not a finding.
3. **Cadence should be low.** Nothing here appeared in a single merge; it all
   accreted. Per-milestone is right; per-task would find nothing most times.

---

## Next step

Pick one to explore and it moves into a design conversation.

- **#3 (in-memory adapter)** — broadest payoff; unlocks #1, #2 and #7.
- **#4 (release rule)** — pick this if the money path worries you most.
- **D2 (no reaper)** — pick this if you'd rather fix a live bug before refactoring.
