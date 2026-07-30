# Architecture Review — 2026-07-30

First run of `improve-codebase-architecture` on this codebase. Trial run for
**backlog #17** (proposed periodic architecture review gate).

Method: three parallel explorers (rendering, storage seam, job/money path), then
every load-bearing claim spot-checked by hand against the code. Where a claim did
not verify, it was dropped or corrected — noted inline.

**Nothing here is a proposal yet.** This document explains *what was found and why
it costs you something*. Designing the fix comes after you pick one.

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
