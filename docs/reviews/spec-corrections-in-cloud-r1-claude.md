# Adversarial review — corrections-in-cloud design spec (round 1, Claude half)

**Reviewer:** Claude, independent of the Codex half (not read).
**Subject:** `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md`
**Reviewed at:** `9211f74`, working tree clean apart from the untracked round-1 prompt.
**Date:** 2026-08-22.

**Counts: 3 Blocking, 7 High, 8 Medium, 8 Low.**

Prior art read first, per the brief: `docs/reviews/plan-append-only-m1-r1-claude.md` and
`plan-append-only-m1-r2-claude.md`. Both killed a mechanism by the same move — *the author reasoned
about what a call achieves without reading the function that performs it* (r1 B1: `promote` is
create-if-absent; r2 B1: `deriveClassASignals` falls back to `processedAt`). **That shape is present
here at least four times**: `getStorageBundle()` (B3), `fixSummary`'s call guard (B1/B2),
`fixSummary`'s missing `billing`/caps parameters (H1/H2), and `updateVideoFields({corrections:
undefined})` (M2). Each time the spec describes an outcome the named function does not produce.

---

## What I executed

| Command | Result |
|---|---|
| `npm test` | **268 suites / 2,722 tests, all passing, 24.7 s.** Green baseline |
| `grep -rn fixSummary lib/ app/ worker/ components/` | 4 hits; **one** call site — `app/api/videos/[id]/regenerate/route.ts:63`. ✅ reproduces §1 row 1 |
| `grep -c corrections lib/job-queue/summary-handler.ts` | **0**. ✅ reproduces §1 row 3 |
| `grep -rni corrections components/cloud/` | **no hits**. ✅ reproduces the "nothing in `components/cloud/`" half of §1 row 4 |
| `wc -c` over `yps-sync-test/*/raw/0*.md` excl. dig-deeper | **n=10, mean 7288.4, min 6247, max 8961**. ✅ reproduces §1 row 6 exactly |
| the ≈0.6¢ arithmetic, against `lib/gemini-cost.ts:33,35` | 1822×250/1e6 = 0.456¢; 1900×30/1e6 = 0.057¢; +0.08¢ ⇒ **0.59¢**. ✅ the arithmetic reproduces (what it omits is H2) |
| `grep -n "fs.promises\|getStorageBundle" …/regenerate/route.ts` | `getStorageBundle` at **`:36`**, not `:35`; `fs.promises` at `:50`, `:69`. ⚠ off-by-one — L1 |
| `grep -rn "getStorageBundle(" app/` | 12 call sites; every cloud-capable one passes `{ supabaseClient }`. The regenerate route does not — **B3** |

**NOT VERIFIED — say it out loud:**

- **Integration and e2e were not run** (no live Supabase stack), per the brief.
- **No SQL was executed.** M2's conclusion (a cloud `corrections` clear is a no-op) is derived from
  `supabase-metadata-store.ts:143` + `JSON.stringify` semantics + the `0021` function body. It is
  **not** observed against a database.
- **No browser was driven.** I verified the *characters* in `CorrectionsPanel.tsx:97,108` from
  source. Whether macOS substitutes smart quotes inside a `<textarea>` — the spec's other stated
  reason for accepting curly quotes — is **NOT VERIFIED**.
- **Gemini's live billing behaviour is not measured.** H2 asserts only what the repo's own code and
  comments assert: that `withCaps` is how output and thinking are bounded, and `fixSummary` does not
  call it.
- **The "99 existing free-form corrections"** is unverified, exactly as §1 says.
- I edited no file except this one.

---

## BLOCKING

### B1 — An EMPTY corrections set takes the RUN branch, so every cloud generation pays for a `fixSummary` call with an empty instruction — and two existing local tests fail either way

**Where:** spec §4:128-129, §5.1:157, §3.2:84-87; `app/api/videos/[id]/regenerate/route.ts:63`;
`lib/job-queue/summary-handler.ts:84,93`; `tests/api/regenerate.test.ts:108,113`;
`tests/lib/cloud-sync/regenerate-stamp.test.ts:110-120`.

The rule is stated as a biconditional with an explicit default:

> §4:128-129 — *"Skip **iff** at least one term was extracted **and** every clause was reducible
> **and** no term occurs. Anything else runs."*

An empty corrections string extracts zero terms. "At least one term was extracted" is false.
Therefore **it runs.** The same is true of whitespace-only (trims to empty), and of a single
unquoted clause (§4:122-123 — *"No quoted tokens → the clause is irreducible"*, and §4:131 — *"One
irreducible clause forces the run for the whole set"*). Both readings of an empty input converge on
RUN.

Now read where the input comes from. §5.1:157:

> *"The unattended path has no request, so it is permanently in the third arm. Effective corrections
> are always 'whatever is stored on the row'."*

For the overwhelming majority of videos that value is absent, and for **every first ingest** it is
provably absent — `existing` is `null`, which the handler names:

```ts
// lib/job-queue/summary-handler.ts:84,93
    const existing = await readVideo(serviceClient, job.playlistId, job.videoId);
    …
    const createdThisRun = !existing;
```

So §5.3 step 3 runs the predicate with `''`, gets RUN, and §3.2's core executes. And §3.2 describes
that core as unconditional:

> §3.2:84-85 — *"The pipeline currently inline at `route.ts:60-68`: `stripQuickViewCallout` →
> `fixSummary` → `extractQuickView` → `insertQuickViewCallout`."*

That is **not** the pipeline that is inline there. The guard is on the line:

```ts
// app/api/videos/[id]/regenerate/route.ts:63
    const fixed = trimmedCorrections ? await fixSummary(stripped, trimmedCorrections) : stripped;
```

The spec's characterisation drops the ternary. An `apply-core` built to §3.2 calls
`fixSummary(stripped, '')` — handing Gemini a prompt whose *"Corrections to apply:"* section
(`lib/gemini.ts:484-485`) is blank, on a paid, uncapped call, for every video that has no
corrections at all.

**Concrete failure (unattended):** a user ingests a 30-video playlist, none with corrections. Under
§5.3 the worker runs `fixSummary('')` + a second `extractQuickView` on all 30 — two unmodelled paid
calls per job (see H2), producing a document Gemini was asked to change in no way, which it may
change anyway.

**Concrete failure (attended, and it is executable today):**

```ts
// tests/api/regenerate.test.ts:108-116
  it('does not call fixSummary when corrections is empty string', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockFixSummary).not.toHaveBeenCalled();
  });

  it('does not call fixSummary when corrections is absent', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockFixSummary).not.toHaveBeenCalled();
  });
```

The fixture `baseVideo` (`:46-53`) carries no `corrections`, so effective corrections is `''` on
both. **Both tests fail** under §4's rule.

**And the obvious repair fails the other test.** Add the missing "no corrections → skip"
short-circuit and §5.2 step 7's warning fires:

> §5.2:171 — *"⚠ **A skip must NOT stamp `mdGeneratedAt`**"*

against

```ts
// tests/lib/cloud-sync/regenerate-stamp.test.ts:110-120
  it('an explicit clear (corrections === "") stamps against empty corrections', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockUpdateVideoFields).toHaveBeenLastCalledWith(
      OUTPUT_FOLDER, VIDEO_ID,
      expect.objectContaining({
        mdCorrectionsHash: mdHash(''),
        mdGeneratedAt: expect.any(String),
      }),
    );
  });
```

Today a clear **does** re-extract the quick view, **does** rewrite the file, and **does** stamp
`mdGeneratedAt` — because the body genuinely changed (the callout was re-inserted). §5.2 step 7 says
it must not. So §9's row *"Local is unchanged | existing local tests | pass untouched"* is false in
both branches of the fork.

**Fix:** state the empty case explicitly as its own arm, before the predicate — *"effective
corrections empty ⇒ nothing to apply; no Gemini, no blob write, no stamp movement of any kind"* — and
say what happens to `mdGeneratedAt` and to the quick-view re-extraction in that arm, because the
existing tests assert both. Then decide, and write down, whether the two `regenerate.test.ts` cases
are preserved or deliberately changed; §9 currently promises preserved.

### B2 — §5.2 feeds *effective* corrections to the apply core, but only the *request's* corrections reach `fixSummary` today. §5.1's "unchanged" rule is the STAMPING rule, not the apply rule

**Where:** spec §5.1:153-155, §5.2 steps 5-8, §3.3:93-94;
`app/api/videos/[id]/regenerate/route.ts:54-56,63,77-79,88`.

§5.1 says the three-way rule is *"unchanged"* and cites `route.ts:78-80`. Read what that variable is
actually consumed by — it has exactly one reader:

```ts
// app/api/videos/[id]/regenerate/route.ts:77-79
    const effectiveCorrections = trimmedCorrections
      ? trimmedCorrections
      : corrections === '' ? '' : (video.corrections ?? '');
```
```ts
// :88
      mdCorrectionsHash: mdHash(effectiveCorrections),
```

`effectiveCorrections` reaches `mdHash` and nothing else. The value handed to Gemini is a *different
variable*, `trimmedCorrections`, which is the **request's** corrections only (`:54`, `:63`). The
route's own comment says so — `:74-76` describes the three arms purely as a stamping rule
(*"stamping `mdHash('')` there would wrongly mark a still-corrected MD as stale"*).

§5.2 collapses the two. Step 5 *"Compute effective corrections"*, step 6 the predicate, step 8
*"Run → apply-core"* — apply-core therefore receives the *effective* value. That is a **behaviour
change on the local path**: a bare POST (no `corrections` key) now re-runs `fixSummary` against the
stored corrections, where today it runs no correction at all. §3.3 asserts the opposite:

> §3.3:93 — *"**Local behaviour and the response shape stay identical**"*

**Concrete failure:** a video with stored corrections `"Fix 'Clawcode' → 'Claude Code'"`, already
corrected weeks ago. A user opens the panel and presses Regenerate without editing the text. Today:
one `extractQuickView`, no rewrite of prose. Under §5.2: the predicate finds `Clawcode` absent (it
was fixed) → skip — fine. But drop the quotes, or hit H4's apostrophe case, or store a
plain-English correction like `"the speaker's name is Kujin"` (irreducible ⇒ forced run) and every
bare Regenerate becomes a full paid document rewrite of an already-correct document. `tests/api/
regenerate.test.ts:113` is the executable statement that this does not happen today.

This is the round-1/round-2 shape precisely: a citation to `:78-80` that reads as "the effective
corrections rule" when the code makes it "the stamping rule", with the apply input two lines away
under a different name.

**Fix:** name the two inputs separately in §5.1 and §5.2 — *the stamp input* (effective) and *the
apply input* — and state whether they are being unified deliberately. If unified, §3.3's "identical"
claim must go and the cost model must account for corrections being re-applied on every bare press.

### B3 — The route cannot execute under `STORAGE_BACKEND=supabase` at all; §3.3's "only the body bypasses the seam" is false, and it fails *outside* the try block

**Where:** spec §1 row 8, §3.3:89-94; `app/api/videos/[id]/regenerate/route.ts:20-22,28-36,48`;
`lib/storage/resolve.ts:29-33,51-64`; `app/api/videos/[id]/review/route.ts:49-53,106-133`;
`components/CorrectionsPanel.tsx:49,52`.

> §3.3:91-93 — *"It already resolves the metadata store through `getStorageBundle` (`:35`); only the
> body bypasses the seam, so the change is replacing two `fs` calls (`:50`, `:69`) with
> `blobStore.get` / `blobStore.put`."*

Three things are wrong, and they compound.

**(a) `getStorageBundle()` with no client throws under the cloud backend.**

```ts
// lib/storage/resolve.ts:51-56
export function getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): StorageBundle {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'local') return LOCAL_BUNDLE;
  if (backend === 'supabase') {
    validateStorageEnv();
    if (!ctx?.supabaseClient) throw new Error('supabase backend requires an authenticated client (routes not wired in 1C)');
```

The route calls it bare at `:36` — and `:36` is **above** the `try` that opens at `:48`, so the
throw is unhandled: a framework 500 with no `logError`, not the 500 the route's own catch produces.

**(b) The principal is a *local* principal.** `route.ts:30` calls `getPrincipal(outputFolder)`,
which is `assertOutputFolder` + `localPrincipal(indexKey)` (`resolve.ts:29-33`). There is no
`cookies()`, no `createServerSupabase`, no `getUser`, no `resolveOwnedPlaylistKey`, no
`getPrincipalFromSession` anywhere in the file. A cloud principal is `{ id: userId, indexKey:
playlistKey }` (`resolve.ts:93-99`).

**(c) The request contract is filesystem-shaped, and the panel matches it.** `route.ts:20-22`
**requires** a non-empty `outputFolder`; in cloud mode that prop is `''` (`components/VideoRow.tsx:
19-20`), and the panel unconditionally posts it with no playlist query string:

```ts
// components/CorrectionsPanel.tsx:49,52
      const res = await fetch(`/api/videos/${encodeURIComponent(videoId)}/regenerate`, {
        …
        body: JSON.stringify({ outputFolder, corrections }),
```

The repo's shipped convention for this exact migration is the opposite of both: a backend switch at
the top and a separate cloud handler that **rejects** `outputFolder` and **requires** `?playlist=`:

```ts
// app/api/videos/[id]/review/route.ts:49-53
export async function POST(request: Request, { params }: Params) {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId);
}
```
```ts
// :114-124
  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) {
    return NextResponse.json({ error: 'invalid playlist' }, { status: 400 });
  }
  …
  if (body && 'outputFolder' in body) {
    return NextResponse.json({ error: 'outputFolder not valid on this backend' }, { status: 400 });
  }
```

So the work is not "replace two `fs` calls". It is a `serveCloud` handler with auth, owner
assertion, a playlist-UUID param, and a panel change to send it — which also falsifies §3.3's
*"`CorrectionsPanel` needs no change other than becoming reachable in cloud mode"* and §7's *"the
only UI surface this design adds"*. §1's row 8 (*"half migrated"*) reads as "one seam left"; the
measured state is "the seam call present cannot succeed".

**Fix:** rewrite §3.3 against `review/route.ts:49-53,106-133` as the template. Enumerate: the
backend switch, `createServerSupabase` + `getUser` (401), the `?playlist=` UUID guard,
`resolveOwnedPlaylistKey` (404), `getPrincipalFromSession`, `getStorageBundle({ supabaseClient })`,
the `outputFolder` rejection, and the corresponding `CorrectionsPanel` change. Then re-scope: this
is not a two-line edit.

---

## HIGH

### H1 — §6's "metering is non-negotiable" has no mechanism: `fixSummary` cannot accept a billing latch, and the spec's architecture excludes changing it

**Where:** spec §6:212-215, §3.1-§3.2, §10; `lib/gemini.ts:470-475,496`, `:274`, `:724-725`;
`lib/job-queue/billing-latch.ts:1-8`; `supabase/migrations/0020_reservation_release.sql:187,268`.

> §6:213-215 — *"The correction route **must** record spend through the same ledger, or we have
> created a paid surface the guardrails cannot see — a worse problem than double-spending."*

The mechanism that records "a paid call happened" is the latch, and it is set at the
`generateContent` primitive:

```ts
// lib/gemini.ts:274 (generateJson)
      if (opts?.billing) opts.billing.metered = true;   // body received = Google billed → latch
```
```ts
// lib/gemini.ts:724-725 (transcribeViaGemini)
      const result = await model.generateContent(request, { timeout: REQUEST_TIMEOUT_MS, signal: opts?.signal });
      if (opts?.billing) opts.billing.metered = true;
```

`fixSummary` has no such parameter and no such line:

```ts
// lib/gemini.ts:470-475
export async function fixSummary(
  mdContent: string,
  corrections: string,
  retries = 2,
  baseDelayMs = 400,
): Promise<string> {
```
```ts
// lib/gemini.ts:496
      const result = await model.generateContent(prompt, { timeout: REQUEST_TIMEOUT_MS });
```

So metering `fixSummary` requires a signature change in `lib/gemini.ts`. §3 lists two new modules and
two thin callers; §10 "Out of scope" does not mention `gemini.ts`; nothing in the spec says it
changes. **The requirement is stated in a section that forbids its own implementation.**

Worse, the latch is the *job*-scoped half. `BillingLatch` says so in its first line
(*"Job-scoped positive metering signal"*, `billing-latch.ts:1-5`), and a route has no job. The
route-side spend mechanism that exists is `reserve_serve_model` / `settle_serve_model`
(`0020:187,268`), keyed on `(playlist_id, video_id)` and priced at `magazine_est_cents`. There is no
correction reservation, no `correction_est_cents` in `guardrail_config`, and no release path.
Building one is a slice of the same shape as #46 — which §6:205 itself cites as having taken seven
review rounds.

**Fix:** either (a) move metering into scope explicitly, with the `gemini.ts` signature change, a
new `guardrail_config` estimate, a reserve/settle pair modelled on `0020`, and the review rounds that
implies; or (b) state plainly that the attended cloud route ships **unmetered**, name that as the
accepted risk with the sentence §6 currently uses to forbid it, and get it decided rather than
asserted. What cannot stand is a non-negotiable requirement with no owner.

### H2 — `fixSummary` has no output cap and no `thinkingBudget: 0`, so `≤0.6¢` is not a bound; and §5.3 puts two unmodelled paid calls inside the job whose 150¢ reservation is a *proof*

**Where:** spec §1 row 7, §6:198-199, §5.3; `lib/gemini.ts:476-477,473`, `:36-43`;
`lib/gemini-cost.ts:56-61,78-98`; `supabase/migrations/0011_cost_guardrails.sql:29`;
`tests/lib/gemini-caps.test.ts:16-20`.

Every capped cloud call goes through `withCaps`, which is what sets **both** the output ceiling and
the thinking off-switch:

```ts
// lib/gemini.ts:36-43
function withCaps(base: GenerationConfig, caps: CloudGeminiCaps | undefined, maxOutputTokens: number): GenerationConfig {
  if (!caps) return base;
  return { ...base, maxOutputTokens, thinkingConfig: { thinkingBudget: 0 } } as GenerationConfig;
}
```

`fixSummary` calls neither, and passes no `generationConfig` at all:

```ts
// lib/gemini.ts:476-477
  const client = new GoogleGenerativeAI(getApiKey());
  const model = client.getGenerativeModel({ model: SUMMARY_MODEL });
```

The repo has written down, at length, why that matters:

> `lib/gemini-cost.ts:56-61` — *"Thinking is genuinely DISABLED (not merely bounded) … so the
> thinking term in `digWorstCents()` is honestly 0 — **not an upper bound on an unbounded
> quantity**."*

Three consequences the spec does not carry:

1. **`≤0.6¢` is a typical value presented as a ceiling.** §6:199 writes it with a `≤`. Retries alone
   multiply it: `retries = 2` (`gemini.ts:473`) ⇒ up to **3** `fixSummary` passes, and
   `extractQuickView` goes through `generateJson` with its own `GENERATE_JSON_RETRIES = 2`. The
   spec's own failure table (§6:221) knows about the retries. Above that, output+thinking are
   uncapped, so there is no ceiling to quote at all.
2. **§5.3 invalidates the job reservation's derivation.** `summary_est_cents` defaults to 150 and is
   documented as *"WORST-CASE one-run upper bound from ENFORCED token caps incl audio pricing"*
   (`0011:29`). `perRunWorstCents` (`gemini-cost.ts:78-98`) models transcribe + summary + quickview
   — and only those. The guard test pins the result: `perRunWorstCents(1800s)` ∈ [110,130]
   (`tests/lib/gemini-caps.test.ts:16-20`). Adding an **uncapped** `fixSummary` plus a second
   `extractQuickView` inside that job means the reservation stops being derivable from the caps. It
   may still hold in practice; it is no longer *proved*, and this repo's guardrail story is built on
   the proof.
3. **The two are the same defect.** An uncapped call is exactly the one you most need metered (H1),
   and it is the one call that cannot be.

**Fix:** thread `CloudGeminiCaps` into `fixSummary` via `withCaps` (a `MAX_CORRECTION_OUTPUT_TOKENS`
sized off the input document is the natural constant), extend `perRunWorstCents` with the correction
term, and re-run the `[110,130]` guard against `summary_est_cents`. Then restate §1 row 7 as
*"≈0.6¢ typical per pass; up to 3 passes; **no enforced ceiling today**"*.

### H3 — §1.1's correction #2 quotes one bullet of §4.2.1 and omits the one that indicts this design; and the dig's anchor lives in the document `fixSummary` rewrites, with no repair pass on this path

**Where:** spec §1.1 item 2, §5.2 step 8, §5.3;
`docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:376-381`;
`lib/html-doc/read-model.ts:20-25,54-56`; `lib/html-doc/parse.ts:16,30-33`;
`lib/dig/cloud/dig-blob-key.ts`; `lib/dig/cloud/enqueue-dig-core.ts:34`; `lib/gemini.ts:401`;
`lib/gemini-cost.ts:54`.

I verified §4.2.1 myself, as instructed. The spec's narrow claim is **correct**: the dig blob address
is `dig/<base>/<startSec>.r<V>.md` and the lookup keys on `startSec`, not on the heading —

```ts
// lib/dig/cloud/enqueue-dig-core.ts:34
  const section = parsed.sections.find((s) => s.timeRange?.startSec === deps.sectionId);
```

— so *"a reworded heading orphans paid digs"* is not literally true. But §1.1 uses that to argue the
risk is small, and §4.2.1 contains two bullets. The spec quotes the first and omits the second:

> `…blob-addressing-design.md:379-381`
> - *a single reworded heading **drops the magazine gists for every section** …*
> - *titles held constant while the prose changes serves **stale gists as fresh** (that one is
>   deliberate: `fixSummary`'s prompt pins headings precisely so this holds).*

**The omitted bullet is a description of this design working as intended.** A successful correction
is, by construction, *prose changed, headings pinned*. Freshness is titles-plus-version, with no
content hash:

```ts
// lib/html-doc/read-model.ts:20-25
export function isFresh(envelope: { sourceSections: string[]; generatorVersion?: string }, titles: string[]): boolean {
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
}
```

So after every corrected generation the cached magazine model still reads fresh and serves
pre-correction gists over corrected prose. §5.2 step 8 clears `summaryHtml` — the rendered HTML, a
different blob — and §5.3 clears nothing. **The one place this spec makes corrections systematic is
the place §4.2.1 says the gists go stale silently.**

Two more corrections to the correction:

- **A reworded heading is not free on the owner path.** `read-model.ts:54-56` states it: *"that
  governs the OWNER path, where refusing an envelope triggers a **reserve-and-charge
  regeneration**."* §1.1 says the cost is that gists are dropped; on the owner path the cost is a
  charge. (I did not compute the cents — the constants are `MAX_MAGAZINE_INPUT_TOKENS` /
  `MAX_MAGAZINE_OUTPUT_TOKENS`, `gemini-cost.ts:17-18`. **NOT VERIFIED as a figure.**)
- **`startSec` is model-editable text with no guard on this path.** It is parsed out of a markdown
  line: `const TS_LINE_RE = /^▶\s+\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)\s*$/` (`parse.ts:16`) and
  `url.match(/[?&]t=(\d+)s/)` (`parse.ts:30-33`). The repair primitive exists — and runs **only**
  inside `generateSummary`:

  ```ts
  // lib/gemini.ts:401
        chosen.summary = ensureSectionTimestamps(chosen.summary, videoId, { firstStart, videoDuration });
  ```

  `fixSummary` has no equivalent. So a single mangled `▶` line re-keys `digSectionKey`, orphaning a
  dig priced at `DIG_EST_CENTS = 150` (`gemini-cost.ts:54`) to save 0.6¢ — and makes
  `enqueue-dig-core.ts:34` return 404 for that section. The whole reason the summary path has
  `ensureSectionTimestamps` is that a missing ▶ removes the dig button.

**Net:** the filed sentence names the wrong mechanism; the spec's replacement makes the risk look
*smaller* when the measured version is **larger** and lands on a 150¢ artifact. Decision #2 (keep
`fixSummary`) is argued partly from this correction and should be re-argued from the corrected facts.

**Fix:** rewrite §1.1 item 2 as *"the filed mechanism is wrong; the real ones are (i) stale gists
served as fresh — §4.2.1's second bullet, which this design makes systematic, (ii) a
reserve-and-charge model regeneration on the owner path if a heading does move, (iii) a mangled ▶
re-keys a 150¢ dig, and unlike `generateSummary` this path has no `ensureSectionTimestamps`."* Then
add to §3.2: apply-core must run `ensureSectionTimestamps` on the corrected document, and the
correction must invalidate the model envelope, not just `summaryHtml`.

### H4 — §4's extraction has no defence against an apostrophe, so "skip only on proof" is not what the rule computes — and the spec's stated reason for accepting curly quotes is refuted by the panel source

**Where:** spec §4:116-126, §4:140-142; `components/CorrectionsPanel.tsx:97,105,108`.

> §4:124-126 — *"Quote matching accepts **ASCII and curly pairs**. The panel's help text renders with
> curly quotes and macOS substitutes smart quotes inside a textarea, so an ASCII-only matcher would
> mark almost every real clause irreducible…"*

The first half is measurably false. The help text's **inner** quotes — the ones that delimit terms —
are `&apos;`, which is ASCII U+0027. Only the outer pair is curly:

```tsx
// components/CorrectionsPanel.tsx:97
          Describe transcription errors to fix, e.g. &ldquo;Fix &apos;Clawcode&apos; → &apos;Claude Code&apos;&rdquo;.
```
```tsx
// components/CorrectionsPanel.tsx:108
          placeholder="e.g. Fix 'Clawcode' → 'Claude Code'; fix 'Ant Throw Pick' → 'Anthropic'"
```

(The textarea-substitution half is **NOT VERIFIED** — no browser was driven.)

That matters because it inverts the risk. The character the panel teaches is `'`, which is **also
the apostrophe**, and naive left-to-right pair matching over prose containing an apostrophe produces
tokens that are not terms:

- Input: `The presenter's name is spelled 'Kujin' not 'Kujeen'`
- Quote positions: `presenter[']s`, `['] Kujin [']`, `['] Kujeen [']` — five ASCII `'` in total.
- Left-to-right pairing yields tokens **`s name is spelled `** and **` not `**, not `Kujin`/`Kujeen`.
- One clause, no arrow ⇒ §4's second bullet, *"take every quoted token"*. Two tokens extracted, so
  the clause is **reducible**, so §4:131's irreducibility escape does not fire.
- If neither garbage token occurs in the body or the card — plausible for `s name is spelled ` —
  the rule **skips** and §4:140-142 stamps `mdCorrectionsHash` as current: *"the document already
  satisfies what the corrections ask for"*. It does not. A real instruction was silently discarded
  and the row asserts it was applied. That is the #23 clause-(a) lie, re-created by the guard built
  to prevent waste.

The hole is structural, not a missing case: **irreducibility catches clauses from which we extracted
*no* tokens; nothing catches clauses from which we extracted the *wrong* tokens.** §4:130's
*"skip only on proof"* is therefore not what the rule computes — it computes *"skip on the absence of
tokens we guessed at"*, and the guess has no validity check.

Also unstated: the route validates only `typeof corrections === 'string'` (`route.ts:24-26`). The
1,000-char cap is client-side (`CorrectionsPanel.tsx:105`) and the sync path writes this field too,
so the predicate's input is unbounded server-side.

**Fix:** make extraction *conservative by shape*, not by count. Concretely: a clause is reducible
only if it matches a strict template — an optional lead-in, then `<q>term</q>` followed by an arrow
and `<q>replacement</q>`, or a `<q>term</q>` list — where `<q>` is a *balanced* pair, tokens contain
no leading/trailing whitespace, and a clause with an **odd** number of ASCII `'` is irreducible on
sight. Everything else is irreducible and runs. Add exactly the worked example above as a unit case
asserting **run**, not skip.

### H5 — §4's three extraction bullets overlap: "arrow, no quotes" matches bullets 1 and 3, and the two readings disagree on both money and correctness

**Where:** spec §4:118-123.

```
- Contains an arrow (`→` or `->`) → take quoted tokens **left** of it. …
- Quotes but no arrow → take every quoted token.
- **No quoted tokens** → the clause is **irreducible**.
```

A clause such as `Clawcode -> Claude Code` satisfies bullet 1's condition (arrow present) and
bullet 3's condition (no quoted tokens). The bullets are written as an exclusive ladder but their
guards are not disjoint.

- **Reading A** (bullet 1 wins; it yields zero tokens but the clause "was processed"): the clause is
  counted **reducible** and contributes nothing.
- **Reading B** (bullet 3 also applies): the clause is **irreducible** and forces the run.

**Concrete divergence:** corrections text `Clawcode -> Claude Code; fix 'Foo' → 'Bar'`, on a document
containing `Clawcode` but not `Foo`. Reading A extracts `['Foo']`, all clauses reducible, `Foo`
absent ⇒ **SKIP**, and the `Clawcode` instruction is silently discarded with the row stamped current.
Reading B ⇒ **RUN**, correct. Two engineers implementing §4 literally produce opposite behaviour on a
money path, and the unquoted arrow form is entirely natural — it is the form used in this repo's own
plan fixtures.

**Fix:** make the ladder total and disjoint by ordering it explicitly, and state the arrow-no-quotes
case by name: *"an arrow clause from which no quoted token was extracted is **irreducible**"*.

### H6 — §7's discriminator and §6's lease analysis both ignore the concurrency case that actually costs money: an attended correction racing the summary worker discards a ~150¢ generation

**Where:** spec §6:197-206, §8:259; `lib/storage/supabase/supabase-blob-store.ts:116-123`;
`lib/job-queue/summary-handler.ts:172-179`; `supabase/migrations/0011_cost_guardrails.sql:29`.

§6 bounds duplicate exposure by considering exactly one race — *"Two concurrent corrections of one
video"* — and concludes *"≤0.6¢ per duplicate"*. Locally that is the only race there is. **In cloud
there is a second actor**, and this spec is what puts the two on the same key.

§8 frames the attended write as an unqualified virtue:

> §8:259 — *"The **attended** path is fully honest. It writes with `put`, which overwrites
> unconditionally."*

Set that beside the worker's sequence and the cloud `promote`:

```ts
// lib/job-queue/summary-handler.ts:172-179
    const ref = await bundle.blobStore.putStaged(bundle.principal, key, …);
    if (!(await bundle.blobStore.exists(bundle.principal, ref.tempKey))) throw new Error('staged upload not verified');
    await persistSummary(…, 'committed');
    await bundle.blobStore.promote(ref);
    await persistSummary(…, 'promoted');
```
```ts
// lib/storage/supabase/supabase-blob-store.ts:119-123
    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    if (await this.exists(ref.principal, ref.finalKey)) {
      await this.b().remove([from]).catch(() => {});
      return;
    }
```

An attended correction that `put`s the final key while a summary job is mid-Gemini leaves the final
key occupied. The worker's `promote` finds it, **deletes its own staged bytes and returns** — a
generation reserved at `summary_est_cents` = 150 (`0011:29`) is discarded to preserve a 0.6¢ edit.
Run it the other way (worker promotes first, correction `put`s after) and the paid generation is
overwritten instead. Either ordering throws away roughly 250× what §6 says the concurrency exposure
is, and §6's stated reason for declining a lease is that duplicate exposure is *"a sub-cent
quantity"*.

This is newly reachable **because of this spec** — locally there is no worker to race.

**Fix:** §6 must analyse correction-vs-generation, not only correction-vs-correction, and restate
the exposure with the right number. The cheapest honest options are (a) refuse the attended
correction with 409 while a `summary` job for that video is `running` (the queue already knows), or
(b) accept it and say so with the 150¢ figure attached. §8's *"writes with `put`, which overwrites
unconditionally"* should note that the same property is what destroys the worker's generation.

### H7 — §9's falsifiers: two contradict §8, one is vacuous today, and the "skip is honest" row cannot observe dishonesty

**Where:** spec §9:274-284, §8:246-248; `lib/cloud-sync/reconcile-class-a.ts:8`;
`lib/cloud-sync/sync-run.ts:651`.

The brief asks whether any listed test would pass on a broken implementation. Row by row:

| Row | Verdict |
|---|---|
| *Corrections survive an unattended re-summarize \| **the published body** \| doc-version bump → the new body has them applied* | **Contradicts §8.** §8:246-248 says that on the common re-summarize *"the worker's corrected body is discarded and the old body stays live."* The named consumer is the one §8 says will not see the change. The test can only be made green by picking the uncommon fixture (empty final key) — which is exactly the "choose the reachable-but-rare state" error round 2 recorded as M1 |
| *The skip saves money \| the spend ledger \| zero movement, zero Gemini calls* | **Vacuous today.** The attended route touches no ledger at all (H1), so "zero movement" is true of every implementation, correct or broken, until the metering that §6 cannot scope is built |
| *The apply spends \| the spend ledger \| moves by the expected amount* | **Unspecified.** "The expected amount" has no value in the spec, and per H2 there is no ceiling to compare against |
| *The skip is honest \| `reconcileClassA`'s decision \| after a skip, sync does not read the cloud body as corrections-stale* | **Cannot fail on the bug it is for.** Both operands derive from the stamp, never from the body: `const current = (s, cur) => s.mdCorrectionsHash === cur` (`reconcile-class-a.ts:8`) and `const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''))` (`sync-run.ts:651`). A skip that was *wrong* (H4 — terms mis-extracted, correction never applied) produces the identical observation to a skip that was right. The falsifier measures that we wrote the stamp |
| *One core, no drift \| both entry points \| byte-identical output* | Sound as a structural guard, but it passes when **both** callers are wrong — e.g. M1's dropped `tags`. Worth keeping; not evidence of correctness |
| *Local is unchanged \| existing local tests \| pass untouched* | **False.** B1 |
| *Corrections work in cloud, attended \| the stored body* | The only row that is both at the consumer and capable of failing |
| *An irreducible clause always runs \| Gemini call count* | Good, and it should be joined by H4's apostrophe case asserting **run** |

**Fix:** for "the skip is honest", assert at a consumer that reads the **body**, not the stamp — e.g.
after a skip, the terms the predicate searched for genuinely do not occur in `blobStore.get(key)`
nor in `tldr`/`takeaways`. That is the observation that fails when extraction mis-fires. For row 2,
either change the consumer to "the staged bytes" and say why, or move the row under §8's bounded
dependency where it belongs.

---

## MEDIUM

### M1 — apply-core's stated signature drops `tags`, so every corrected document loses the callout's Concepts line

`route.ts:67` is `insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? [])`, and the callout
emits Concepts only when tags are non-empty:

```ts
// lib/quick-view-callout.ts:47-50
  if (tags.length > 0) {
    lines.push('>');
    lines.push(`> **Concepts:** ${tags.join(' · ')}`);
  }
```

§3.2:86-87 says apply-core *"Takes a document string, returns `{ content, tldr, takeaways }`"* —
no tags in, so the re-inserted callout has none, and `stripQuickViewCallout` has already removed the
old one. The `regenerate.test.ts` fixture carries `tags: ['ai','rag']` (`:50`), so this is not
hypothetical. §9's byte-identical falsifier cannot catch it: both callers share the core and
therefore share the defect. **Fix:** the signature is `(document, { tags })`.

### M2 — Clearing corrections is a silent no-op on the Supabase backend, and the route then stamps `mdHash('')` over it

`route.ts:57-58` clears by writing `undefined`:

```ts
    } else if (corrections === '') {
      await store.updateVideoFields(principal, videoId, { corrections: undefined });
```

The Supabase store forwards the object to the RPC (`supabase-metadata-store.ts:140-145`,
`p_fields: stripComputed(fields)` — and `stripComputed` only removes `updatedAt`/`summaryReady`).
`JSON.stringify` drops undefined-valued keys — the repo states this itself at
`summary-handler.ts:146-148`. So `p_fields` arrives as `{}`, and `merge_video_data` neither removes
the key nor stamps the timestamp:

```sql
-- supabase/migrations/0021_cloud_sync_signals.sql:75-77
  foreach k in array classb loop
    if p_fields ? k then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
  end loop;
```
```sql
-- :80
    data = (data || (p_fields - 'artifacts'))
```

`route.ts:88` then stamps `mdCorrectionsHash: mdHash('')` while `data.corrections` still holds the
user's text. `reconcileClassA` computes `cur` from the surviving corrections value
(`sync-run.ts:651`), so the cloud row reads **corrections-stale** and `needsRegen` fires — a paid
re-summarize caused by a clear that did nothing. §5.1's *"`''` means cleared"* is assumed, not true
on the backend this spec is enabling. The cloud convention for a clear is
`update_video_annotations`'s `p_clear` array (`0021:38-43`; `review/route.ts:137-144`), which the
store's own comment calls *"the sole caller-facing surface for personal-annotation writes"*
(`supabase-metadata-store.ts:258-262`) — so keeping `updateVideoFields` here is also a second
mechanism for one concern. **NOT VERIFIED against a live database** — derived from source.

### M3 — §5.2 step 7's field enumeration omits `annotationsEditedAt`, which step 3 moves *before* the skip decision

The prompt asked me to check `annotationsEditedAt` against "the body did not change". Step 3
(`route.ts:55-56`) persists corrections whenever the parameter is non-empty — including when the
text is byte-identical to what is stored — and `merge_video_data` stamps
`annotationsEditedAt.corrections` whenever the key is present (`0021:75-77`). So an attended skip,
which by definition changes nothing, still bumps a Class-B edit timestamp that drives newer-wins
Class-B sync (`lib/cloud-sync/backfill.ts:21-31`). Pressing Regenerate twice makes an unchanged value
win against an identical value on the other replica. The step-7 warning names six body-describing
fields and stops one short of the field that actually moves on a skip.
**Fix:** step 3 should be conditional on the corrections text having changed, and step 7's list
should say so.

### M4 — The synchronous route has no `maxDuration`, and §6's "10–30 seconds" is an order of magnitude under the code's own bound

`REQUEST_TIMEOUT_MS = 60_000` (`gemini.ts:105`). `fixSummary` retries 2 (`:473`) ⇒ 3 × 60 s;
`extractQuickView` goes through `generateJson` with 2 retries ⇒ another 3 × 60 s, plus exponential
backoff (`:505`). Worst case is ~6 minutes in a route the user is waiting on. §6:208-209 prices the
accepted duplicate-retry trade at *"plausibly 10–30 seconds"*.

The repo has already hit this: `app/api/quick-view/backfill/route.ts:10` declares
`export const maxDuration = 1800; // 30 minutes`. The regenerate route declares none, and decision
#5 (*"a synchronous route"*) does not mention it. **Fix:** set and justify `maxDuration`, and reprice
§6's trade off the real bound.

### M5 — The unattended correction runs before the abort check and cannot be aborted

§3.4 places the correction *"After `summaryCore` returns and **before** the blob is staged"*. The
only lease/cancel check in that window is `summary-handler.ts:170`, immediately before the write
sequence — so the correction's paid calls happen ahead of it. And `fixSummary` cannot be cancelled
even in principle: `gemini.ts:496` passes `{ timeout: REQUEST_TIMEOUT_MS }` with no `signal`, unlike
`generateJson` (`:273`) and `transcribeViaGemini` (`:724`). A worker that has lost its lease pays for
a correction it will discard — and it is the one call the ledger cannot see (H1).
**Fix:** re-check `ctx.signal.aborted` before the correction, and thread `signal` into `fixSummary`
alongside the caps and billing changes H1/H2 already require.

### M6 — Corrections are read minutes before they are applied; §5.3 calls that "free" and does not name the staleness, which §5.2.2's own round-1 finding is about

§5.3 step 2: *"Stored corrections come from `existing`, already fetched at `:84` for the idempotency
skip — free."* True and cheap. But `:84` runs before `summaryCore`, which is a transcript fetch plus
a summary generation. The blob spec's §5.2.2 records exactly this window as a High:

> `…blob-addressing-design.md:1252-1255` — *"Corrections are mutable while a generation runs
> (`update_video_annotations`, `0021:19`). A worker starts with C1, the user saves C2 during the
> Gemini call, and the worker publishes a generation stamped C1 — **born stale**"*

The corrections spec cites §5.2.2 twice (§2 decision 1, §5.3) and never mentions this. Today it
self-heals — the row's hash will not match the reconciled hash, so `reconcileClassA` flags
`needsRegen` — but that self-heal is *a paid re-summarize*, and it is the kind of thing a plan needs
stated rather than discovered. **Fix:** name the window and its resolution in §5.3.

### M7 — §8 and §9 both assume the unattended path stamps `mdCorrectionsHash`; `summary-handler.ts` does not, and the plan that adds it is at round 2, NOT CONVERGED

§8:248 — *"Stamping `mdCorrectionsHash` as current there describes a document we did not write."*
But the worker's `video` literal (`summary-handler.ts:149-164`) carries neither `mdCorrectionsHash`
nor `mdGeneratedAt`, and `persist_summary` layer (3) re-applies them only when the payload provides
them (`0021:131-132`) — which is why the defect described in backlog #23 clause (a) is
*"layer-2 preserves the previous hash"* rather than *"the worker writes a wrong hash"*.

That stamp is the append-only **M1** plan, whose latest review verdict is `NOT CONVERGED`
(`docs/reviews/plan-append-only-m1-r2-claude.md:546`). This spec states no dependency, no ordering,
and no behaviour for the case where M1 does not land. §9 row 5 ("the skip is honest") and §8's whole
boundary argument are unbuildable without it. **Fix:** state the dependency and the order explicitly
in §2 or §10, including what this slice does if M1 ships later.

### M8 — §6 asserts the panel's disabled button bounds duplicates, but the panel is not the only reachable caller once the route is cloud-enabled

§6:199-200 rests the duplicate bound on *"behind a button the panel already disables while busy
(`CorrectionsPanel.tsx:124`)"*. That citation is correct (`disabled={busy}`, and `:44-45`
`if (busy) return`). But it bounds one tab only: `:69` clears `busy` in `finally`, so a failed or
timed-out request re-enables immediately, and the route is a plain authenticated POST with no
idempotency key. §6 acknowledges the retry case in its ⚠ paragraph and then keeps the "sub-cent"
conclusion; combined with H6 the conclusion does not survive. **Fix:** fold this into H6's restated
concurrency analysis rather than leaving the button as the argument.

---

## LOW

- **L1** — `getStorageBundle` is at `route.ts:36`, not `:35` (§1 row 8, §3.3:91). Off by one in the
  row whose subject is that call.
- **L2** — three more citation drifts: the inline pipeline is `route.ts:62-67`, not `:60-68` (§3.2);
  the three-way rule is `:77-79`, not `:78-80` (§5.1); the corrections persist is `:54-59`, not
  `:52-59` (§5.2 step 3 — `:52-53` are its comment).
- **L3** — §1 row 4 cites `components/VideoRow.tsx:19` for the UI gate. That line is a **prop
  docstring**. The gate is `components/VideoMenu.tsx:181` — `{!cloudMode && video.summaryMd && (` —
  with `cloudMode` from `useScope()` at `:52`. "Nothing in `components/cloud/`" reproduces but
  misleads: the component is *shared and mode-gated*, not cloud-absent, so "make it reachable" is a
  one-line flip in a shared component plus B3's request-shape work.
- **L4** — §1 row 6 says *"Mean summary size 7,288 **chars**"* derived with `wc -c`, which counts
  **bytes**. All ten sampled files are one English playlist (`cs146s-…`). The repo supports
  `lang: KO` (`summary-core.ts:81`) and shipped backlog #36 for Korean two weeks ago; for a Korean
  document bytes and chars differ by ~3× and the chars→tokens rule of thumb differs again. Say
  "bytes, single English playlist".
- **L5** — the ≈0.6¢ input term (~1,900 tokens) omits the corrections text itself, capped at 1,000
  chars client-side (`CorrectionsPanel.tsx:105`) and uncapped server-side (`route.ts:24-26`).
  Immaterial to the total (~0.008¢), but the row is presented as a derivation.
- **L6** — on a skip the response still carries `summaryHtml: null` (`route.ts:95`) and the panel
  writes it into local state (`CorrectionsPanel.tsx:63`), so the client drops a cache pointer the
  server kept. §5.2 step 9 says "the shape the panel already consumes" without noting the field is
  now a lie on the skip branch.
- **L7** — §1.1 quotes backlog #23's `gemini.ts:456` for `fixSummary`; it is `:470` today. Worth
  fixing while §11 item 1 rewrites that row.
- **L8** — §3.1 says the predicate *"must not be able to throw"* and says nothing about not
  **hanging**. A quote/arrow tokenizer over a server-side-unbounded `corrections` string is a
  catastrophic-backtracking surface, and the unattended caller is a worker holding a lease. Add
  "must be linear in input length" to the module's contract.

---

## The brief's five pressure points, answered

1. **§4, the applicability check.** Attacked as instructed. Empty/whitespace-only → **runs**, which
   is the wrong default and breaks two live tests (**B1**). Arrow-without-quotes is **ambiguous
   between two bullets** with opposite outcomes (**H5**). Apostrophes silently produce garbage terms
   and can cause a **false skip that stamps as applied** (**H4**), and the spec's stated reason for
   the curly-quote rule is **refuted by the panel source** (H4). Substring matching and code-fence
   hits err toward running — safe, and the "known limitation" paragraph is honest as far as it goes.
   **Is "skip only on proof" what the rule computes? No.** It computes *skip on the absence of tokens
   we guessed at*; irreducibility catches zero tokens, never wrong tokens.
2. **§5.2 step 7 and its warning.** `mdGeneratedAt` is **not** the only field of that class.
   `annotationsEditedAt` moves *before* the skip decision and is not listed (**M3**). Of the six the
   prompt named: `summaryHtml`, `tldr`, `takeaways` are correctly left alone by step 7; `processedAt`
   and `docVersion` are not written by this route at all (they are the unattended path's problem, and
   round 2's B1/H2 own them); `mdCorrectionsHash` is the one claim that legitimately moves. The
   enumeration is right about what it lists and one field short.
3. **§6, no lease.** `≤0.6¢` is **not a bound** (**H2** — 3 passes, no `maxOutputTokens`, no
   `thinkingBudget: 0`). Things other than a button press reach it: a retry after the ~6-minute
   worst case (**M4**), and — the case §6 never considers — **the summary worker**, where the loser
   is a ~150¢ generation (**H6**). "Metering through the ledger" has **no mechanism**: `fixSummary`
   takes no billing latch, the latch is job-scoped, and the spec's architecture excludes changing
   `gemini.ts` (**H1**). As written it is an aspiration.
4. **§8, the bounded dependency.** The boundary is **not** honestly drawn. The attended path writes
   a card too, and `updateVideoFields`'s clear arm is a no-op in cloud (**M2**), so "fully honest"
   overstates it. Its `put` is simultaneously what discards a concurrent worker's paid generation
   (**H6**). And yes — the unattended correction **does** pay to correct a body `promote` will
   discard, which §8 states for the *stamp* but never for the *spend*: §8's cost sentence should say
   that on the promote-skipped path the correction's Gemini calls are pure waste, on top of the
   summary's.
5. **§9, the falsifiers.** Four of eight do not do the job — see **H7**. The two that matter most
   ("the skip is honest", "corrections survive an unattended re-summarize") respectively **cannot
   observe the failure they exist for** and **name a consumer §8 says will not see the change**.

## Also assessed

- **Internal consistency.** Four contradictions beyond the two caught in self-review: §3.3 "local
  identical" vs §5.2's effective-corrections input (**B2**); §9 "existing local tests pass untouched"
  vs `regenerate.test.ts:108,113` (**B1**); §9 row 2 vs §8:246-248 (**H7**); §6's duplicate bound vs
  §5.3's addition of two calls to a reserved job (**H2/H6**).
- **Built two different ways.** §4's bullet overlap (**H5**) is the clearest; §3.2's apply-core
  signature (**M1**) and §5.2's stamp-vs-apply conflation (**B2**) are the others.
- **Scope — this is not one implementable slice.** It is at least three, and one of them is a
  money-path slice of the shape §6 itself says took seven rounds: **(i)** cloud-enable the route
  (auth, playlist param, principal, panel wiring — B3); **(ii)** the predicate + apply-core + the
  unattended call site; **(iii)** metering, caps and the reservation term (H1, H2). (iii) gates (i)
  by §6's own rule. Recommend splitting, with (iii)'s decision — meter or knowingly ship unmetered —
  taken *before* (i) is planned.
- **What the spec does not cover but should.** The metering mechanism (H1); output caps and the
  reservation derivation (H2); model-envelope invalidation and `ensureSectionTimestamps` on the
  corrected document (H3); the cloud auth/request contract (B3); the cloud clear (M2); `maxDuration`
  and abortability (M4, M5); the M1 dependency and ordering (M7); the correction-vs-worker race
  (H6); and what an attended correction does when `video.summaryMd` is set but the blob is
  unreadable — `route.ts` currently 500s, and the cloud `get` cannot distinguish absent from
  unreadable (`supabase-blob-store.ts:34-44`, `provesAbsence = false` at `:11`), which round 2's H3
  covered for a different call site.
- **The two backlog corrections, adjudicated.**
  - **#1 "unaffordable by construction" → 0.6¢.** *Sustained in direction, overstated in force.* The
    arithmetic reproduces. But the backlog's body argues *waste* — "a full-document round trip per
    generation", "thousands of them to change two words" — and the spec **concedes both** (§1.1:41).
    Only the heading word "unaffordable" is refuted. And 0.6¢ is a typical value, not the bound the
    `≤` in §6 claims (**H2**). Record it as *"wasteful; ≈0.6¢ typical per pass, up to 3 passes, no
    enforced ceiling"* — not as a refutation.
  - **#2 "a reworded heading orphans paid digs".** *Correct that the filed mechanism is wrong;
    incorrect that this makes the risk small.* Verified: the dig key is `startSec`
    (`dig-blob-key.ts`, `enqueue-dig-core.ts:34`). But §4.2.1's **second** bullet — omitted by the
    spec — says a pinned-heading prose change serves **stale gists as fresh**, which is what this
    design makes routine; a heading that *does* move triggers a **reserve-and-charge** regeneration
    on the owner path (`read-model.ts:54-56`), not merely dropped gists; and `startSec` is parsed
    from a ▶ line inside the very document `fixSummary` rewrites, with `ensureSectionTimestamps`
    running only in `generateSummary` (`gemini.ts:401`) — so a mangled ▶ orphans a 150¢ dig
    (**H3**). **Neither correction, as written, is a safe basis for Decision #2.** Decision #2 may
    still be right — pairs genuinely cannot express "reword this section" — but it should be argued
    from parity, not from a cost/safety comparison that measurement does not support.

---

## Verdict

**NOT CONVERGED**
