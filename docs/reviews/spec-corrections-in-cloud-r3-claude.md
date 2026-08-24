# Adversarial review — corrections-in-cloud design spec **v3** (round 3, Claude half)

**Reviewer:** Claude, independent of the Codex half (not read).
**Subject:** `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` @ `72cf17d`
(*"docs(#23): spec v3 — delete both optimisations; what is left is the feature"*), clean working tree.
**Rounds 1 and 2 read first, all four documents.** The r1 and r2 Claude halves are other instances'
work; I disagree with r2 in one place (noted in the disposition table, claude-H1).
**Date:** 2026-08-23.

**Counts: 3 Blocking, 7 High, 8 Medium, 9 Low.**

---

## Top line — read this before the findings

**The deletion was right, and it worked.** I checked every round-2 finding that belonged to the two
deleted optimisations: **thirteen** of them are gone outright, not relocated. The apostrophe-parity
false skip, the empty clause, the trailing `;`, the multi-arrow discard, the `exists()` fail-open, both
TOCTOU directions, the `If-None-Match` seam — all dissolved with the machinery. §0's diagnosis
(*"I was designing a tokenizer in prose"*) is correct and the remedy was correct. v3 is by a wide
margin the best of the three documents, and §6.2's arithmetic — the part the brief told me to
recompute — **checks out to the digit, all five numbers** (§ *Arithmetic, recomputed*, below).

**But the answer to the brief's primary question is: the deletion left three things dangling, and one
of them is load-bearing.**

1. **§4's one-line rule is stated over the wrong variable.** It says `fixSummary` runs iff *effective*
   corrections are non-empty, and then claims that is *"exactly the guard that exists today at
   `route.ts:63`"*. `route.ts:63` tests `trimmedCorrections`; *effective* corrections are `:77-79`, a
   different quantity that §1's own table names — and that §5.1 says, in the next section, must stay
   **separate from the apply input**. Read literally, v3's thesis sentence reinstates the paid
   bare-press rewrite that §5.1 exists to reject. (**B1**)
2. **§9 row 3 asserts an outcome §8 says cannot happen.** *"Unattended corrections survive a version
   bump | the published body | both corrected"* is, under Supabase `promote` semantics, the same
   assertion as `summary-handler-promote-divergence.test.ts:148` — an `it.failing` tripwire that is
   **failing right now**, on the same scenario, and that §9 cites two paragraphs later. (**B2**)
3. **§6.2's rewrite dropped `correction_est_cents` and §6.3 still demands a reserve.** v2 had the
   constant with no consumer; v3 has the consumer with no constant. §10's schema-change list names the
   two smaller changes and omits this one. (**H1**)

And v3 introduced **one new cost the deletion did not remove but created**: §3's structural validation
is a new, mandatory, model-output-dependent failure gate sitting inside the summary job between
`summary-handler.ts:170` and `:173`. A throw there discards a completed ~115¢ generation. §6.1 names
that blast radius, prescribes a preflight, and the preflight makes the failure *free* without making it
*contained*. (**B3**)

### The recommendation, stated as the brief asks

**Do not write v4 as one document. Split it — and only B1, B2, B3 and H1 need to be settled first.**

I am not saying "revise again." Most of what is left is cheap: B1 is one clause, B2 is a scope
qualifier on a falsifier row, half the Lows are line numbers. What is *not* cheap, and what a fourth
revision of one document will not fix, is that **v3 is three slices wearing one spec**:

| Slice | What it is | Why it is separable |
|---|---|---|
| **A — the attended cloud route** | the real cloud branch (§3), `apply-core`, the caps via `withCaps` (§6.1), the §5.2 write-hygiene fields, the §5.3 clear, the §7 discriminator | This is the feature. It is buildable today and it is what the user asked for |
| **B — the unattended correction** | worker integration (§3), the §5.1 re-read, the §8 stamp | Needs failure containment (**B3**), collides with backlog #22 (**B2**) and with the append-only M1 plan (**M8**, r2-M5, still unaddressed after two rounds) |
| **C — the money instruments** | route-side reserve/settle (§6.3), `correctionWorstCents()`, the `cap-soundness` extension, the duration ratchet (§6.2, §11.3) | §6.3 is a money-path slice. This repo's own record says those take five to seven rounds (`serve-path-bounding`, PR #67) |

Slice A can ship behind the caps with the attended path **knowingly unmetered and named as the accepted
risk** — which is what r2-claude-H1 recommended and v3 declined. v3 chose "metered", specified the
mechanism, and omitted the amount: the worst of both. That single decision is what turns a shippable
slice into a money-path spec, and it is a decision the human should make, not another review round.

Findings that **die with the split** are marked ⊘. Findings that survive it are marked ●.

---

## What I executed

| Command | Result |
|---|---|
| `npm test` | **268 suites / 2,722 tests, all passing, 25.3 s.** Green baseline (matches r2) |
| `npx jest tests/api/regenerate.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts --verbose` | **2 suites, 18 tests, all passing.** §9 says *seven*. See **H3** |
| hand-recompute `perRunWorstCents({1800})` from `lib/gemini-cost.ts:78-98` | **114.984 → `Math.ceil` 115¢.** ✅ §6.2 row 1 |
| `sed -n '29p;33p' supabase/migrations/0011_cost_guardrails.sql` | `summary_est_cents … default 150`; `max_duration_seconds … default 1800`. ✅ §6.2 row 2, §1 rows 8–9 |
| hand-recompute the correction term | **17.4317¢.** ✅ §6.2 row 4 (see the basis I had to reconstruct — **M1**) |
| hand-solve `perRunWorst(d) + 17.4317 ≤ 150` | **d ≤ 4,416.96 → 4,416s.** ✅ §6.2's bound, exactly. At 4,417s it breaks |
| hand-check §6.2's 5,400s claim | `0.00672·5400 + 102.888 = 139.176`; slack **10.824¢**. ✅ *"at 5,400s the slack is 10.8¢"* |
| `grep -n "withCaps(" lib/gemini.ts` | `36` (def), **`326`, `433`, `536`, `686`** — four call sites, not two. **L3** |
| `grep -c fixSummary` / `grep -c corrections lib/job-queue/summary-handler.ts` | one call site `route.ts:63`; **0**. ✅ §1 rows 1, 3 |
| `grep -n "signal" <spec>` | **zero hits.** v2 threaded `signal?` into `fixSummary`; v3 dropped it. **H4** |
| `grep -n "est_cents" <spec>` | `summary_est_cents` only. No `correction_est_cents`. **H1** |
| read `lib/storage/supabase/supabase-blob-store.ts:34-43,85-87,120-123` | ✅ all three §0/§8 citations correct |
| read `supabase/migrations/0021_cloud_sync_signals.sql:89` | `updated_at = now()`. ✅ §5.2 |
| read `lib/cloud-sync/backfill.ts:13`, `:22` | `:13` ✅ correct; `updatedAt ?? processedAt` is `:22`, spec says `:21`. **L4** (r2-L4, unfixed) |

**NOT VERIFIED — say it out loud:**

- **No integration or e2e run** (no live Supabase stack), per the brief. Every claim about
  `merge_video_data`, `update_video_annotations`, `promote`, `persist_summary` and the ledger is read
  from SQL/TS source, **not observed against a database**.
- **No SQL executed.** No `psql`.
- **No live Gemini call.** `thinkingBudget: 0` correction quality (§6.1's own ⚠) remains NOT VERIFIED
  here too — I agree with §6.1 that a fixture eval is the right gate.
- **The eighteen tests were run; the claim that they still pass after v3 is reasoned, not executed** —
  there is no implementation. **H3** quotes the specific assertion I believe breaks and why.
- **"99 existing free-form corrections"** — unverified, exactly as §1 says.
- The Korean/token-density question from r2-H11 is **moot** in v3 (the cap is no longer sized off a byte
  sample) and I did not re-test it.
- I edited no file except this one.

---

## Arithmetic, recomputed

The brief asked for all five. **All five are right.** I reproduce the derivation because §6.2 does not,
and that omission is itself **M1**.

```
audio(d)      = 32·d                                   AUDIO_TOKENS_PER_SEC
video(d)      = max(0, 300000 − 32·d)                  MAX_TRANSCRIBE_INPUT_TOKENS
transcribe    = 3 · [ 32d·100/1e6 + (3e5−32d)·30/1e6 + 4000·30/1e6 + 32768·250/1e6 ]
              = 0.00672·d + 51.936
perSummaryPass= (40960+4000)·30/1e6 + 8192·250/1e6 = 3.3968
summary+qv    = (12+3) · 3.3968 = 50.952
perRunWorst(d)= 0.00672·d + 102.888
```

| Spec claim | §6.2 | Recomputed | Verdict |
|---|---|---|---|
| Summary worst at the live 1800s cap | 115¢ | `0.00672·1800 + 102.888 = 114.984 → ceil 115` | ✅ |
| `summary_est_cents` | 150¢ | `0011:29` default 150 | ✅ |
| Slack | 35¢ | `150 − 115 = 35` (35.016 unrounded) | ✅ |
| Correction worst | 17.4¢ | `3·[(8192+4000)·30/1e6 + 8192·250/1e6] + 3·3.3968 = 7.2413 + 10.1904 =` **17.4317** | ✅ (**L8** — rounded *down*) |
| Fit holds while `max_duration_seconds ≤` | 4,416s | `(150 − 17.4317 − 102.888)/0.00672 = 4416.96` → **4,416**; at 4,417 the total is 150.0002¢ | ✅ exact |

The 4,416 bound is not approximately right, it is right to the second. Whoever computed it did open the
file. That is worth saying, given the failure mode the brief warned me about.

**Two caveats that are findings, not arithmetic errors:** the per-term basis is nowhere stated
(**M1** — I had to solve for it), and the input term `8192 + 4000` is bounded only by a preflight
described in a different subsection for a different reason (**M2**).

**The aggregate question, answered.** The brief asked whether unconditional `fixSummary` is affordable
in the aggregate and under a playlist-wide doc-version bump. **Yes, and the reason is structural, not
arithmetic: the reservation does not rise.** Admission is
`reserved_cents + actual_cents + v_est <= daily_cap_cents` (`0011:114`, `0018:63`), `v_est` is
`summary_est_cents`, and §6.2's whole point is that it stays 150¢. A playlist-wide bump of N videos is
therefore admitted at exactly the rate it is today; the *actual* spend rises by ~0.6¢ per corrected
video (§1.1), so all 99 rows cost about 60¢ more in total. **The deletion introduced no unbounded
aggregate cost.** I checked this specifically and found nothing.

---

## Round-2 findings that are NOT about the deleted optimisations

`✅` fixed · `◐` partly · `⚠` fix introduced a new problem · `✗` untouched · `⊗` **dissolved with the deletion**

### Codex half

| # | Sev | Finding | v3 | Note |
|---|---|---|---|---|
| 1 | B | `exists()` cannot prove absence | ⊗ | deleted |
| 2 | B | pre-check is TOCTOU | ⊗ | deleted |
| 3 | H | apostrophe tokenizer buildable two ways | ⊗ | deleted |
| 4 | H | cap based on unreproducible byte sample | ✅ | §6.1 derives from `MAX_SUMMARY_OUTPUT_TOKENS`; §1 row 6 marks the sample unused |
| 5 | H | reservation arithmetic deferred | ✅ | §6.2, and it is correct — see above |
| 6 | H | local bare-pass behaviour changed | ✅ | §5.1 reverts it — **but §4 re-opens it. B1** |
| 7 | H | no validation after `fixSummary` | ⚠ | §3 adds one, underspecified, with a new failure class. **H2, H5, B3** |
| 8 | M | punctuation cases only "fail toward spend" | ⊗ | deleted |
| 9 | M | ledger consumer/mechanism mismatch | ◐ | §6.3 + §9's row are the right shape; the **amount** is missing. **H1** |
| 10 | M | `thinkingBudget: 0` quality unproven | ✅ | §6.1 ⚠ marks it NOT VERIFIED and requires a fixture eval |
| 11 | L | "chars" for a `wc -c` measurement | ✅ | §1 row 6 says **bytes** |
| 12 | L | three citation drifts | ◐ | `:36` ✅ `:77-79` ✅ `VideoMenu` ◐ — cites the label, not the gate. **L6** |

### Claude half

| # | Sev | Finding | v3 | Note |
|---|---|---|---|---|
| B1 | B | even-parity apostrophe false skip | ⊗ | deleted |
| B2 | B | `exists()` fails open | ⊗ | deleted |
| B3 | B | `nothing-to-apply` deletes the quick-view refresh; 7 tests | ✅ | §4 keeps `extractQuickView` unconditional — but §9 mis-transcribes "7 tests **break**" as "there are 7 tests". **H3** |
| H1 | H | attended path has no ledger | ◐ | v3 picks *metered* and specifies reserve/settle **without an amount**. **H1**. *(I disagree with r2's framing that naming the decision suffices — v3 named it and the gap moved rather than closed.)* |
| H2 | H | cap × retry = 3 paid passes, kills the job | ◐ | preflight added → 0 paid passes; **the job still dies. B3** |
| H3 | H | `cap-soundness` green over the wrong subject | ✅ | §6.2 ⚠ requires it extended **in the same change**. Correct and well-aimed |
| H4 | H | bypasses `withCaps` | ✅ | §6.1 now says *applied through `withCaps`*, correctly, and the citation `gemini.ts:36` is right |
| H5 | H | "local behaviour unchanged" contradiction | ✅ | the sentence is gone from v3 |
| H6 | H | stale magazine gists; no `ensureSectionTimestamps` | ◐ | §1.1 now quotes **both** §4.2.1 bullets ✅ — and the **envelope invalidation is still absent**, now made certain rather than likely by §3. **H7** |
| H7 | H | empty clause → forced paid run | ⊗ | deleted |
| H8 | H | multi-arrow discards terms | ⊗ | deleted |
| H9 | H | `annotationsEditedAt` on unchanged text | ✅ | §5.2's row is now conditional on the text actually changing |
| H10 | H | sync-decision falsifier inverted | ✗ | **unfixed. H6** |
| H11 | H | English-byte cap basis | ⊗ | dissolved with the byte sample |
| M1 | M | invented clear sentinel | ✅ | §5.3 defers to the store's surface — without naming it. **M7** |
| M2 | M | whitespace-only | ✅ | §4's last line |
| M3 | M | `If-None-Match` undefined | ⊗ | deleted with the pre-check |
| M4 | M | other TOCTOU direction | ⊗ | deleted |
| M5 | M | append-only M1 ordering | ✗ | **unfixed, second round. M8** |
| M6 | M | predicate must be linear | ⊗/◐ | ReDoS surface deleted; the **server-side length cap** is still absent and now matters more. **M8** |
| M7 | M | apostrophe-check scope ambiguous | ⊗ | deleted |
| L1 | L | `getStorageBundle` `:35`→`:36` | ✅ | |
| L2 | L | `route.ts:52-59` | ✗ | **L7** |
| L3 | L | `VideoRow.tsx:19` | ◐ | moved to `VideoMenu`, wrong line. **L6** |
| L4 | L | `backfill.ts:21` | ✗ | **L4** |
| L5 | L | bytes vs chars | ✅ | |
| L6 | L | "a reviewer could not reproduce it" overstates | ✗ | §1 row 6 repeats it verbatim; the path exists on this machine and reproduces to the digit |
| L7 | L | `summaryHtml` on a no-write outcome | ◐ | §5.2 says "updated"; the route writes `null`. **M5** |

**Tally of the non-dissolved rows: 9 fixed · 6 partly · 1 made worse · 5 untouched.**
**Tally including the dissolved: 22 of 33 round-2 findings are gone.** That is the deletion working.

---

## BLOCKING

### ● B1 — §4's rule is written over `effective` corrections, cites a line that tests `trimmed` corrections, and read literally reinstates the paid bare press §5.1 exists to reject

**Where:** spec §4:123, §4:126-127, §5.1:144, §5.1:152-153, §1 row 7 (`:49`);
`app/api/videos/[id]/regenerate/route.ts:54,63,77-79`; `tests/api/regenerate.test.ts:113-116`;
`tests/lib/cloud-sync/regenerate-stamp.test.ts:98-108`.

This is v3's thesis sentence — the *one line* §0 says the whole design collapses to:

> §4:123 — *"`fixSummary` runs ⟺ **effective corrections** are non-empty after trimming."*
> §4:126-127 — *"That is the whole rule, and it is **exactly the guard that exists today** at
> `route.ts:63` (`trimmedCorrections ? await fixSummary(…) : stripped`)."*

The two halves of that sentence name **two different variables**, and the spec's own §1 table is what
proves it:

> §1 row 7 (`:49`) — *"Effective-corrections rule | `route.ts:77-79`"*

```ts
// route.ts:54 — the request's corrections
const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
// route.ts:63 — the guard §4 cites, which tests THAT
const fixed = trimmedCorrections ? await fixSummary(stripped, trimmedCorrections) : stripped;
// route.ts:77-79 — "effective corrections", a DIFFERENT quantity
const effectiveCorrections = trimmedCorrections
  ? trimmedCorrections
  : corrections === '' ? '' : (video.corrections ?? '');
```

On a **bare press of a video that has stored corrections** the two disagree, and this is not
hypothetical — it is a committed, passing test:

```ts
// tests/lib/cloud-sync/regenerate-stamp.test.ts:98-108  (baseVideo.corrections = 'old corrections')
it('a bare regenerate (no corrections param) stamps against the UNCHANGED stored corrections', …
   expect.objectContaining({ mdCorrectionsHash: mdHash('old corrections') })
```
```ts
// tests/api/regenerate.test.ts:113-116
it('does not call fixSummary when corrections is absent', async () => {
  await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
  expect(mockFixSummary).not.toHaveBeenCalled();
});
```

`effectiveCorrections` is `'old corrections'` — non-empty. §4's rule therefore says **run**.
`route.ts:63` says **do not run**. Both cannot be "the whole rule".

And the reading §4 prescribes is the exact behaviour §5.1 spends its opening paragraph rejecting:

> §5.1:144-147 — *"**Attended: the request's corrections — unchanged from today.** v2 changed this to
> *effective* corrections, which would have made a bare button press re-run a paid full-document
> rewrite of stored free-form text. That is a UX change nobody asked for…"*
> §5.1:152-153 — *"The stamping rule at `route.ts:77-79` is unchanged and remains **separate from the
> apply input** — v2 conflated them."*

**§4 conflates precisely what §5.1 says must not be conflated, using the term §1 defines as the stamp
input.** An implementer who reads §4 as the normative rule (it is labelled *"That is the whole rule"*)
ships v2's regression, breaks `regenerate.test.ts:113-116`, and falsifies §9's last row in the same
commit. An implementer who reads §5.1 ships the right thing and finds §4 describing something else.

This matters more in v3 than it would have in v2, because **deletion made §4 the entire specification
of when money is spent.** There is no longer a procedure, a table, or a set of rules to cross-check it
against. One sentence carries it, and the sentence is wrong about the code it quotes.

**Fix — one clause.** Replace §4:123 with:

```
fixSummary runs  ⟺  the corrections being applied on this path are non-empty after trimming
                    (attended: the request's, §5.1; unattended: the stored, §5.1).
```

and change §4:127 to say the attended half is `route.ts:63`'s existing guard. Then delete the phrase
*"effective corrections"* from §4 entirely — §1 has bound that term to `:77-79` and it should keep
exactly one meaning in this document.

---

### ● B2 — §9's third falsifier asserts the outcome §8 documents as impossible, and it is byte-for-byte the scenario of a known-failing tripwire the same section cites

**Where:** spec §9:261 (row 3), §8:239-241, §9:271-272;
`tests/lib/job-queue/summary-handler-promote-divergence.test.ts:140-158`;
`lib/storage/supabase/supabase-blob-store.ts:120-123`.

> §9 row 3 — *"Unattended corrections survive a version bump | the **published** body and card | both
> corrected"*

§8, four sections earlier, in the same document:

> §8:239-241 — *"**An occupied final key still discards the whole generation** — `promote` is
> create-if-absent (`supabase-blob-store.ts:120-123`). The correction is wasted along with the summary
> that produced it."*

Verified in source:

```ts
// lib/storage/supabase/supabase-blob-store.ts:120-123
if (await this.exists(ref.principal, ref.finalKey)) {
  await this.b().remove([from]).catch(() => {});
  return;                    // ← staged bytes deleted, live body untouched
}
```

A **version bump** is by definition a re-run against a key that is already occupied — the video already
has a promoted `summaryMd`. So §9 row 3's consumer (*the published body*) holds the **old, uncorrected**
bytes, exactly as §8 says. The falsifier is unsatisfiable on the scenario it names.

Worse, the repo already owns that exact assertion, and it is red:

```ts
// tests/lib/job-queue/summary-handler-promote-divergence.test.ts:148-158
it.failing('serves the NEW body under Supabase semantics (promote is create-if-absent)', async () => {
  const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
  setup(store, 'ORIGINAL summary body', null);
  await makeSummaryHandler(serviceClient)(job(), ctx);
  setup(store, 'REGENERATED summary body', { major: 1, minor: 0 });   // ← the version bump
  await makeSummaryHandler(serviceClient)(job(), ctx);
  const bytes = await store.get(principal, SUMMARY_KEY);
  expect(bytes?.toString()).toContain('REGENERATED summary body');
});
```

Its header comment (`:140-142`) reads *"Do NOT rewrite the assertion to match current behaviour
(dev-process.md bans it)"*, and **§9:271-272 cites this very file** — *"backlog #22's `it.failing`
tripwire (`summary-handler-promote-divergence.test.ts:148`) already owns that"*. The author read line
148, quoted it correctly, and did not notice their own row 3 is the same claim with "corrected"
substituted for "REGENERATED".

**Concrete failure scenario for the implementer.** They write row 3 as an integration test against
Supabase (or `InMemoryBlobStore` with `promoteSemantics: 'create-if-absent'`) and it fails on correct
code. The only ways to make it pass are (a) construct the fixture so the final key is *free*, which
makes it a first-generation test wearing a version-bump name — vacuous, and the second time this
review series has caught a falsifier rescued by an unrepresentative fixture; or (b) run it against the
default overwrite semantics, which re-asserts the behaviour `:140-142` bans.

**Fix.** Scope the row to what v3 actually delivers:

| Claim | Consumer | Assertion |
|---|---|---|
| Unattended corrections reach the **staged** body | the staged blob before `promote` | corrected |
| …and become published **when the final key is free** | the published body and card | both corrected |
| A version bump onto an occupied key is **#22's loss, not a new one** | — | covered by `…promote-divergence.test.ts:148`; **do not add a second characterization test** (§9:271) |

That is three honest rows in place of one dishonest one, and it costs no engineering.

---

### ● B3 — a correction failure discards a completed ~115¢ generation; §6.1 names the blast radius, prescribes only the preflight, and §3 adds a *new* way to trigger it

**Where:** spec §3:94-103, §6.1:190-193; `lib/job-queue/summary-handler.ts:170-179`;
`lib/gemini.ts:494-510`; `supabase/migrations/0011_cost_guardrails.sql:31`.

§6.1 states the danger itself:

> §6.1:191-193 — *"`fixSummary` retries twice on a truncated response (`:492-505`), so a document that
> cannot fit would cost three full passes and then throw — and **on the unattended path that failure
> kills the whole generation.** The plan checks the input against the cap before the first call and
> fails fast."*

The preflight is the right idea and it fixes the **cost** half of r2-H2 (3 paid passes → 0). It does
nothing about the half the same sentence names. Read the write sequence:

```ts
// lib/job-queue/summary-handler.ts:170-179
if (ctx.signal.aborted) throw new DOMException('worker signal aborted before write', 'AbortError');
                              // ← §3:116 puts the correction HERE
const key = `${baseName}.md`;
const ref = await bundle.blobStore.putStaged(bundle.principal, key, Buffer.from(core.mdContent, …));
if (!(await bundle.blobStore.exists(bundle.principal, ref.tempKey))) throw new Error('staged upload not verified');
await persistSummary(serviceClient, …, 'committed');
await bundle.blobStore.promote(ref);
await persistSummary(serviceClient, …, 'promoted');
```

`summaryCore` has already completed — the transcribe and the summary loop are paid and done, and
`core.mdContent` is in hand. **Any throw between `:170` and `:173` discards all of it.** Nothing is
staged, nothing is persisted, the handler propagates, and with
`summary_max_attempts int not null default 1` (`0011:31`) the job does not get another billed run.

**v3 has more ways to throw there than v2 did, not fewer:**

1. the input preflight rejecting an over-cap document (§6.1) — *v3's own new gate*;
2. `fixSummary` exhausting its three attempts on a transient error, which `gemini.ts:509-510` turns
   into a plain `throw new Error('Gemini summary fix failed: …')` — no `NonRetryableError`, no
   containment;
3. **`extractQuickView`**, which §4:133 says now runs on the unattended path whenever a correction was
   applied — a second `generateJson` with its own three attempts;
4. **§3's structural validation** — *"A failure is an error, not a silent write"* (§3:103).

Item 4 is the one that changes the risk class. `fixSummary` **only asks** the model to preserve
structure — §3:100-101 says so, correctly, citing `gemini.ts:479-489`, and I read the prompt: it is
three bullet points of English. A stochastic model asked politely to preserve structure will sometimes
not. v3 therefore makes *"the model reworded a heading"* — a routine, expected outcome — into a
**hard failure that destroys a ~115¢ generation to protect a ~0.6¢ edit.** That trade is upside-down
by a factor of ~190.

**Fix — one sentence in §3, and it is the sentence r2-H2(c) asked for and v3 did not carry:**

> On the unattended path a correction failure of any kind — preflight rejection, `fixSummary` throw,
> validation failure, or quick-view failure — is **caught**. The handler publishes `core.mdContent`
> uncorrected, does **not** stamp `mdCorrectionsHash`, and logs. `reconcileClassA` then reads the row
> as corrections-stale and the correction is retried on the next pass. Losing a generation to a
> correction is strictly worse than shipping the generation uncorrected.

Add a falsifier: *"a `fixSummary` that throws inside the job | the published body | present and
uncorrected; `mdCorrectionsHash` unmoved"*. Note that this also makes the attended path's behaviour the
asymmetric one (a 500 the user sees and can retry), which is correct — the user is there.

---

## HIGH

### ● H1 — §6.2's rewrite deleted `correction_est_cents`; §6.3 still requires a reserve, so the attended money path has a mechanism and no amount, and §10's schema list omits it

**Where:** spec §6.2:199-217, §6.3:219-222, §9:263, §10:281-282;
`supabase/migrations/0011_cost_guardrails.sql:27-35`; `0014_serve_owner_budget.sql:84`;
`0018_enqueue_dig.sql:63`.

`grep -n "est_cents"` over v3 returns `summary_est_cents` and nothing else. v2 had
`correction_est_cents` with no consumer (r2-H1); v3 has the consumer with no constant:

> §6.3:220-222 — *"the plan specifies **route-side reserve / settle / release**, following the serve
> path's shape, and a test that fails if `fixSummary` is called without a latch."*

Reserve **how much**? §6.2 proves one thing only: that the *unattended* correction fits inside the
existing `summary_est_cents` reservation. The attended route is not inside a summary job and has no
reservation to fit inside. Following "the serve path's shape" means what the serve path does:

```sql
-- 0014_serve_owner_budget.sql:84  (and 0011:114, 0018:63 — the same shape)
and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
```

— a named `guardrail_config` column, checked against `daily_cap_cents`. There is no such column for
corrections, and §10's enumeration of what changes in the schema does not mention adding one:

> §10:281-282 — *"No **data** migration… ⚠ There **is** a schema change: §5.2 may need a narrow RPC,
> and §6.2's duration ratchet may need config."*

Two smaller items named; the largest one absent. Consequences: §9:263's row (*"A run spends a bounded
amount | the ledger | ≤ the capped worst case"*) is unwritable on the attended path, because "the
ledger" moves by an amount no section defines; and the plan gate cannot size the slice, because a new
`guardrail_config` column plus an admit/settle/release RPC pair is not a detail — it is the reason
slice C exists.

**Fix.** Either (a) add `correction_est_cents` to §6.2 with its value derived from the 17.43¢ already
computed there (18¢ is the honest ceiling), name the RPC pair, and add the column to §10's schema list
— accepting that this is a money-path slice; or (b) declare the attended path **knowingly unmetered
behind the caps**, delete §6.3's reserve/settle sentence, keep the latch requirement (it is cheap and
it is what §9:263's second clause actually tests), and rewrite §9:263's consumer from *the ledger* to
*the cap*, which is observable without any of this. **(b) is slice A and ships. (a) is slice C.**
What cannot stand is a required mechanism with an undefined amount.

### ● H2 — §3's structural validation is the deleted prose-rule relocated: "the same invariants" are not computable from apply-core's inputs, and §9 specifies a different check

**Where:** spec §3:94-103, §9:264; `lib/gemini.ts:391-403`; `lib/html-doc/parse.ts:16,18-39`.

The brief asked whether §3's new requirement is *"specified precisely enough to build, or the same
prose-rule problem the deleted extraction had, relocated."* It is relocated. Three reasons.

**1. "The same invariants" are not available to apply-core.** §3 grounds the requirement in
`ensureSectionTimestamps`:

```ts
// lib/gemini.ts:391-401 — inside generateSummary, NOT reachable from apply-core
if (hasSegments && !sectionStartsComplete(chosen.summary)) {
  const lastSeg = segments[segments.length - 1];
  const videoDuration = Math.floor(lastSeg.offset + lastSeg.duration);
  const firstStart = Math.floor(segments[0].offset);
  …
  chosen.summary = ensureSectionTimestamps(chosen.summary, videoId, { firstStart, videoDuration });
```

It needs `segments`, `videoId`, `firstStart`, `videoDuration`. §3:96 fixes apply-core's input as
`{ md, corrections, tags }`. None of those four are in it, and none are recoverable from the markdown.
So "validated for the same invariants" names a check apply-core structurally cannot perform. It is also
a **repair**, not a validation — §3 borrows the word "invariants" from a function that fixes rather
than rejects.

**2. §3 and §9 specify two different checks.** §9's row is *relative*:

> §9:264 — *"Structure survives correction | the parsed document | headings and `▶` timestamps
> **unchanged**; dig anchoring intact"*

A before/after comparison **is** computable from `{md, corrected}` — it is the right check, and it is
not what §3 says. Two engineers reading §3 and §9 build different gates, and one of them (§3's
absolute reading) rejects documents that were already valid on the way in.

**3. The absolute reading fails on committed fixtures, today.** `MD_CONTENT` in both test files is
`'# Title\n\n**URL:** …\n\n---\n\n## 1. Intro\nContent.'` — one `##` heading, **no `▶` line**
(`parse.ts:18-23` returns `null` for a section whose first prose line does not start with `▶`). An
absolute "every section carries a monotonic `▶`" validator rejects it and 500s the route, taking most
of the eighteen tests in **H3** with it.

**4. And it creates a new false-negative class of its own.** The corrections panel's own placeholder
teaches `Fix 'Clawcode' → 'Claude Code'` (`components/CorrectionsPanel.tsx:108`). If *Clawcode* appears
in a section heading — which is exactly where a mis-transcribed product name lands — then a **correct**
correction changes a heading, §9's relative check fires, and the user's correction is thrown away
(attended) or the generation is destroyed (unattended, **B3**). §0's table says the deletion removed
the false-negative class. It removed the *parsing* one and §3 added a *validation* one, uncounted.

**Fix.** Specify §9's relative form and drop §3's appeal to `ensureSectionTimestamps`:

> apply-core parses the input and the corrected document with `parseSummaryMarkdown` and compares the
> ordered list of `timeRange.startSec` values. **Only that list must be identical** — it is the sole
> input to `digSectionKey` (`enqueue-dig-core.ts:34`, `dig-blob-key.ts:22`). Heading *text* may change;
> §1.1 establishes it does not orphan a dig. On mismatch, attended returns 422 with the offending
> section; unattended catches per **B3**.

That is buildable, it is one predicate over one list, and it is narrower than what §3 asks for in the
only direction that matters.

### ● H3 — §9's "the seven existing tests … all pass unmodified" is wrong twice: there are **18**, and at least one has an exact-arity assertion §6.1 breaks

**Where:** spec §9:266; `tests/api/regenerate.test.ts` (14 tests), `tests/lib/cloud-sync/regenerate-stamp.test.ts` (4 tests); `tests/api/regenerate.test.ts:102-106`.

> §9:266 — *"Local is unchanged | **the seven existing tests** in `tests/api/regenerate.test.ts` and
> `tests/lib/cloud-sync/regenerate-stamp.test.ts` | **all pass unmodified**"*

Executed:

```
npx jest tests/api/regenerate.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts --verbose
Test Suites: 2 passed, 2 total
Tests:       18 passed, 18 total
```

**Where "seven" came from.** r2-claude-B3's headline was *"**Seven** existing local tests change
behaviour or fail, in two files."* That was a count of tests v2 would have **broken**. v3 read it as an
inventory of the files. The number was never a property of the test suite, and copying it into a
falsifier turns a fixed defect into a wrong gate: an implementer ticks this row having run seven of
eighteen and has no way to know which eleven they skipped. This is the "cannot run / partial run is not
a pass" shape the repo's own `CLAUDE.md` opens with.

**And the claim itself is not free.** The most likely break:

```ts
// tests/api/regenerate.test.ts:102-106
it('calls fixSummary when corrections are provided', async () => {
  const corrections = "Fix 'Clawcode' → 'Claude Code'";
  await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections });
  expect(mockFixSummary).toHaveBeenCalledWith(MD_CONTENT, corrections);
});
```

`toHaveBeenCalledWith` matches the **full argument list**. §6.1 gives `fixSummary` caps and §6.3
requires a latch, so apply-core will call it as `fixSummary(md, corrections, retries, delay, opts)`.
The moment any fifth (or third) argument is passed on the local path, this assertion fails. The repo
knows this hazard and documents it — `lib/ingestion/summary-core.ts:64-66`:

> *"signal/caps/billing threaded only when present — an explicit `undefined` opts arg is a DIFFERENT
> call signature than omitting it (**callers/tests assert exact arg lists**), so build the opts object
> conditionally."*

So the claim can be made true, but only by an explicit design choice v3 does not state.

**Fix.** §9:266 → *"**all 18** existing tests in those two files pass unmodified (14 + 4, `npm test`
2026-08-23)"*, and add to §3: *"apply-core builds `fixSummary`'s `opts` conditionally and omits the
argument entirely when no caps/latch/signal are present, per the `summary-core.ts:64-66` precedent —
local call shapes stay byte-identical."* Then the row is both correct and achievable.

### ● H4 — v3 lost `signal` from `fixSummary`, so the abort ordering §3 keeps is now a point check in front of ~181s of uncancellable paid work

**Where:** spec §3:115-116, §6.1:180-184 (`grep -n "signal"` over v3 → **zero hits**);
`lib/gemini.ts:470-474,494-508`; `lib/job-queue/summary-handler.ts:170`; `lib/gemini.ts:262-273`.

§3 keeps the ordering r1-M5 asked for:

> §3:115-116 — *"applies stored corrections after `summaryCore`, **after the abort check at `:170`**,
> before staging."*

v2 paid for that with a thread: r2 quotes §6.1 as giving `fixSummary`
`opts?: { signal?, billing?: BillingLatch, maxOutputTokens?, thinkingBudget? }`. **v3's §6.1 lists only
the two cap settings**, and the word `signal` does not occur anywhere in the document.

```ts
// lib/gemini.ts:470-474 — today's signature; no opts at all
export async function fixSummary(mdContent: string, corrections: string, retries = 2, baseDelayMs = 400): Promise<string>
// :496 — no signal forwarded
const result = await model.generateContent(prompt, { timeout: REQUEST_TIMEOUT_MS });
```

`ctx.signal.aborted` at `summary-handler.ts:170` is a **point** check. Once `fixSummary` starts, a lost
lease or SIGTERM cannot stop it: three attempts × 60 s + 1.2 s backoff ≈ **181 s**, then
`extractQuickView` → `generateJson`, which *does* honour a signal (`gemini.ts:271,273`) but only
because it is passed one. The comparison is the point — `generateJson` takes `opts.signal`,
`generateSummary` takes `opts.signal`, `summaryCore` threads it (`summary-core.ts:67-73,82-88`).
`fixSummary` is now the only paid call in the job that cannot be cancelled, and v3 is what puts it
there.

This is a **regression introduced by the rewrite**, not a pre-existing gap: v2 had it and the §6.1
rewrite dropped it while keeping the §3 sentence that depends on it.

**Fix.** §6.1: *"`fixSummary` gains `opts?: { signal?: AbortSignal; billing?: BillingLatch; caps?:
CloudGeminiCaps }`. `caps` reaches `generationConfig` through `withCaps` (`gemini.ts:36`); `signal` is
forwarded to `generateContent` and checked at the top of each retry attempt, as `generateJson` does at
`:271`."* One line, and it restores what §3 already assumes.

### ● H5 — §3's justification for structural validation contradicts §1.1, the section that exists to retract exactly that overstatement

**Where:** spec §3:101-102 vs §1.1:63-70; `lib/dig/cloud/dig-blob-key.ts:13-25`;
`lib/dig/cloud/enqueue-dig-core.ts:33-38`.

> §3:101-102 — *"Since **§1.1 establishes that heading and `▶` stability is load-bearing** for dig
> anchoring, the corrected document is validated for the same invariants…"*

§1.1 establishes close to the opposite:

> §1.1:63-65 — *"*'A reworded heading orphans paid digs'* → **overstated**. A reworded heading alone
> does not orphan a dig while `startSec` is stable (`lib/dig/cloud/dig-blob-key.ts:13-23`,
> `enqueue-dig-core.ts:33-39`)."*

Verified — the key contains no title at all:

```ts
// lib/dig/cloud/dig-blob-key.ts:22
const key = `dig/${base}/${sectionId}.r${DIG_GENERATOR_VERSION}.md`;
// lib/dig/cloud/enqueue-dig-core.ts:34 — sectionId IS startSec
const section = parsed.sections.find((s) => s.timeRange?.startSec === deps.sectionId);
```

So for **dig anchoring** specifically — the property §3 names — `▶`/`startSec` is load-bearing and
heading text is not. §1.1 is a correction filed against backlog #23 for overstating this; §3 then
justifies a new mandatory gate by citing §1.1 as saying the overstated thing. The document argues both
sides of its own correction, four sections apart.

The practical cost is **H2.4**: the overstatement is what makes the validator reject heading changes,
which is the false-rejection class. Narrow the premise and the class disappears.

**Fix.** §3:101-102 → *"Since §1.1 establishes that **`startSec` stability** is load-bearing for dig
anchoring (`dig-blob-key.ts:22`, `enqueue-dig-core.ts:34`), the corrected document is validated for
**that** invariant…"*. Then move the heading-text concern where §1.1 actually puts it — the magazine
gists, which is **H7**, and which is a cache-invalidation problem rather than a validation one.

### ● H6 — §9's sync-decision falsifier is still inverted; a correct implementation fails it (r2-H10, unfixed)

**Where:** spec §9:265, §5.2:164; `lib/cloud-sync/reconcile-class-a.ts:8,22-23,25-26,39-40`;
`app/api/videos/[id]/regenerate/route.ts:77-79,88`.

> §9:265 — *"A no-correction pass disturbs nothing extra | the **sync decision** | `reconcileClassA`
> **unchanged**; `annotationsEditedAt` unmoved when the text did not change"*

But §5.2 keeps the stamp on that very pass:

> §5.2:164 — *"`mdCorrectionsHash` | set per the `route.ts:77-79` rule"*

and `mdCorrectionsHash` is the **sole** input to the currency predicate:

```ts
// lib/cloud-sync/reconcile-class-a.ts:8
const current = (s: ClassASignals, cur: string): boolean => s.mdCorrectionsHash === cur;
// :22-23, :39-40 — every branch that consumes it
if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };
if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
```

Flipping `cCur` false → true is the **entire purpose** of stamping. If `reconcileClassA` is unchanged,
the stamp did nothing and the row stays corrections-stale forever — the Blocking the stamp was
originally added to fix (`regenerate-stamp.test.ts:1-7` header). So the decision *must* change, and a
test written to §9:265 literally fails on correct code; a test written to make it pass needs a fixture
where the hash already matched, which is vacuous.

r2-H10 filed this with a two-row fix. v3 rewrote the row's *second* clause (the `annotationsEditedAt`
half, correctly — that is r2-H9 fixed) and left the first clause verbatim. **⊘ if slice B is deferred
— but only the unattended half; the attended stamp is slice A and the row still needs splitting.**

**Fix — the two rows r2 proposed, unchanged:**
(i) *"the `needsRegen` verdict goes **from true to false** after a correction pass"* — this is the
change we want, and it fails if the stamp is missing.
(ii) *"nothing else moves: `mdHash`, `docVersionMajor`, `backfilled`, and every `annotationsEditedAt`
entry byte-identical before and after."* — that is the "disturbs nothing" claim, and it is falsifiable.

### ● H7 — the magazine envelope is still not invalidated, and §3's heading-pinning now makes stale gists *certain* rather than likely (r2-H6, half-fixed)

**Where:** spec §1.1:66-70, §3:94-103, §9:258-268; `lib/html-doc/read-model.ts:12-25`;
`lib/gemini.ts:479-489`.

§1.1 now quotes **both** bullets of the stable-blob-addressing §4.2.1 — that is r2-H6's first half
genuinely fixed, and the ⚠ at §1.1:67-70 saying so is exactly right. The second half is untouched:

```ts
// lib/html-doc/read-model.ts:12-25
export function sameTitles(envelope: { sourceSections: string[] }, titles: string[]): boolean {
  return envelope.sourceSections.length === titles.length &&
    envelope.sourceSections.every((t, i) => t === titles[i]);
}
export function isFresh(envelope: {…; generatorVersion?: string }, titles: string[]): boolean {
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
}
```

**Freshness is titles + generator version. There is no content hash.** A successful correction is by
construction *prose changed, headings pinned* — `fixSummary`'s prompt pins them
(`gemini.ts:480`: *"do NOT add, remove, or restructure any sections"*) and **§3's new validator now
enforces it**. So after every cloud correction the cached magazine model still reads fresh and the
rendered HTML serves **pre-correction** gists over corrected prose, indefinitely.

v3 makes this worse than v2 in a precise way: in v2 heading stability was a hope, so the envelope
sometimes self-invalidated by accident. In v3 it is a hard gate, so the cache is *guaranteed* to look
fresh. The one mechanism that used to break the staleness is now forbidden.

§9's second row covers three card consumers (*`tldr`, `takeaways`, and the Concepts line*) and not this
one. §10 does not list it as out of scope.

**Fix.** One line in §3: *"apply-core's caller deletes the magazine model envelope for the video after
a successful correction (`readModelEnvelope`'s blob, `lib/html-doc/model-store.ts`) — `isFresh`
compares titles only, so a prose-only correction cannot invalidate it."* Plus a §9 row: *"the rendered
magazine after a correction | the served HTML | contains the corrected prose, not the cached gists."*
If the team would rather defer it, it belongs in §10 with a reason — silence is what r2-H6 objected to
and it is still what §10 offers.

---

## MEDIUM

### ● M1 — §6.2 states five totals and none of the per-term basis, so the arithmetic is checkable only by solving for it

§6.2:201-206 gives a four-row table of results. The correction row — *"3 × capped `fixSummary` +
3 × quick-view | **17.4**"* — does not say what a capped `fixSummary` pass costs or what its input is. I
recovered the basis by solving the 4,416s bound backwards: input `8192 + 4000` tokens @30¢/1M, output
`8192` @250¢/1M, ×3, plus `3 × 3.3968`. That reproduces 17.4317 and 4,416.96 exactly, so the number is
right — but a reviewer who guessed `+250` for the corrections text (as r2 did) gets 17.45 and a
**4,414s** bound, and would have filed the spec's headline number as wrong. **Fix:** add the two lines
of derivation, and name `MAX_SUMMARY_OUTPUT_TOKENS` + `PROMPT_SCHEMA_OVERHEAD_TOKENS` as the input
basis. Four extra cells make the table self-checking, which is the whole reason §6.2 was moved into the
spec.

### ● M2 — the input term is bounded only by a preflight stated elsewhere for another reason, and a locally-generated body has no output cap at all

§6.2's `fixSummary` input assumes the document is ≤ `MAX_SUMMARY_OUTPUT_TOKENS`. That holds for a body
this repo generated **in the cloud**. It does not hold for a body that arrived by `copyToCloud`:
`withCaps` returns the base config unchanged when `caps` is absent (`gemini.ts:41-42`), and
`summary-handler.ts:30-31` says so explicitly — *"Local callers of summaryCore pass no caps → no
maxOutputTokens"*. A locally-generated summary is **unbounded**, and it is a first-class way for a body
to reach the cloud row. Two gaps follow: (a) §6.2's arithmetic is sound only *because of* §6.1's
preflight, and §6.2 never says so; (b) the preflight then makes such a video **permanently
uncorrectable in the cloud**, with a hard error and no fallback, which no section mentions. **Fix:**
state the dependency in §6.2 (*"the input term is bounded by §6.1's preflight, not by construction"*),
and in §6.1 say what the attended path returns when the preflight rejects (422 with a message the panel
can show — not a 500).

### ● M3 — §6.4's `maxDuration` derivation stops before the second Gemini call, and never states the value

> §6.4:226-227 — *"`maxDuration` is set from the capped worst case: per-call timeout is 60s
> (`gemini.ts:105`) with up to 3 attempts, so the chain's bound is **~180s before quick-view**."*

`gemini.ts:105` is `const REQUEST_TIMEOUT_MS = 60_000;` ✅ and `fixSummary`'s loop is 3 attempts ✅ (+1.2 s
backoff). But quick-view goes through `generateJson`, which is *also* 3 × 60 s (`gemini.ts:262-273`,
`GENERATE_JSON_RETRIES = 2`). The real chain is **~362 s**, and §3:113 says the `maxDuration` is *set
from* this number — which is stated as a partial and never resolved to a value. A `maxDuration` set to
180 truncates the call it was computed to survive. **Fix:** finish the sum and state the number.

### ● M4 — §0's ⚠ tells the user their optimisation survives, and it does not

> §0:31-34 — *"⚠ **Your original optimisation survives in its dominant form.** You asked not to pay when
> the misspelling is already gone. The overwhelmingly common version of 'gone' is *the corrections field
> is empty*, and that case is handled by a guard that already exists…"*

"The misspelling is already gone" means *the corrections text is present and no longer matches
anything*. "The corrections field is empty" means *there is nothing to apply* — the base case, true
before this spec existed and unrelated to the request. And it is not "overwhelmingly common" on either
path that matters: the unattended scenario (§9 row 3, a version bump) requires stored corrections to be
**non-empty** by definition, and on the attended path the user has just typed them. No evidence is
offered for the frequency claim. §0 is the section addressed to the human whose optimisation is being
deleted, and it is the one place the deletion should be stated plainly. **Fix:** *"Your optimisation is
fully deleted. What remains is the base case — empty corrections cost nothing, which was already true.
The saving you asked for was ~0.6¢ and it cost four Blockings to chase."* That is a better argument for
the deletion than the one §0 makes.

### ● M5 — §5.2 is a v2 artifact: v3 has no no-write pass, so the table's premise and two of its rows no longer fit

§5.2's title is *"What a no-correction pass must not touch"*. In v2 such a pass genuinely wrote almost
nothing. In v3 §4:130-131 keeps `extractQuickView` unconditional on the attended path, so a
no-correction pass re-extracts the card, rebuilds the body through `insertQuickViewCallout`
(`route.ts:67`), rewrites the file (`:69`) and updates four fields (`:85-89`). It touches nearly
everything. Two rows suffer:

- **`mdGeneratedAt` — *"must not move if the body did not change"*.** The spec never says how "the body
  did not change" is evaluated, and on this path the body usually *does* change (a fresh `tldr` goes
  into the callout). The rule is right; it needs *"compare the rendered `updatedContent` against the
  bytes read; move `mdGeneratedAt` only on a difference"* to be buildable.
- **`summaryHtml` — *"updated"*.** Today the route writes `summaryHtml: null` (`route.ts:86`) and two
  committed tests pin it (`regenerate.test.ts:159-166`, `:168-173`). "Updated" and "null" are not the
  same instruction. (r2-L7, still open.)

**Fix:** retitle to *"What an attended pass must and must not move"*, and make both rows concrete.

### ● M6 — v3 is not one slice

Enumerated from the document: a cloud route branch with auth/scope/storage wiring; a scope-aware
`CorrectionsPanel`; `apply-core`; structural validation; worker integration with failure containment;
`fixSummary` caps through `withCaps` plus a signal and a latch; an input preflight; route-side
reserve/settle/release with a new `guardrail_config` column and RPC pair; a narrow no-`updated_at` RPC
for §5.2; a clear-surface change tested on both backends; `correctionWorstCents()` plus the
`cap-soundness` extension; a `max_duration_seconds` ratchet; a fixture eval for `thinkingBudget: 0`; and
the §7 discriminator. See the split proposed in the top line. **This is the finding I would act on
first**, because every other finding is cheaper to fix once the slice it belongs to is named.

### ⊘ M7 — §5.3 defers to a surface it does not name, and that surface has a side effect §5.2 constrains

> §5.3:172-174 — *"The plan uses **the store's own documented clear surface**, not an invented
> sentinel, and tests it against both backends."*

The surface exists on both backends and r2-M1 named it: `updateVideoAnnotations(set, clear)` —
`lib/storage/local/local-metadata-store.ts:125`, `lib/storage/supabase/supabase-metadata-store.ts:269`,
allowlist `supabase/migrations/0021_cloud_sync_signals.sql:25,39-40`. Not naming it in a spec that
otherwise cites `file:line` for everything invites the plan to re-derive it. And it **stamps**:

```sql
-- 0021:41-43 — every Class-B clear stamps its timestamp
foreach k in array v_clear loop
  if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
end loop;
```

`corrections` is in `classb` (`:25`). So the clear moves `annotationsEditedAt.corrections`
unconditionally, which §5.2:166 says must happen *"only when the corrections text actually changed"* —
correct when clearing a non-empty value, wrong when clearing an already-empty one. **Fix:** name the
call, and add *"the clear is issued only when the stored value is non-empty."*

### ● M8 — two round-2 Mediums untouched, and the second one is now the only unbounded input to a paid call

- **r2-M5 / r1-M7 — the append-only M1 ordering.** §8:247-249 notes the unattended path stamps nothing
  today and v3 adds it; the plan that *also* adds `mdCorrectionsHash` to the worker write path is
  append-only M1, last recorded `NOT CONVERGED`. Two specs writing one field through `persist_summary`
  need an order. Unaddressed for the third round running. **Fix:** one line in §10.
- **r2-M6 residue — no server-side length cap on `corrections`.** The ReDoS surface died with the
  tokenizer, but `route.ts:24-26` still validates only `typeof corrections === 'string'`; the 1,000-char
  limit is client-side (`CorrectionsPanel.tsx:105`), and the sync path writes this field too. It is now
  the **only unbounded input** to a call §6.2 prices at a fixed token count — a 200 KB corrections blob
  breaks the input term the arithmetic assumes. **Fix:** a server-side cap in §3, and add the
  corrections term to §6.2's input basis so the bound is honest.

---

## LOW — citations and precision

Round 2 caught several drifts by one line; the brief asked me to check v3's. Six are new or unfixed.

- **L1** — §3:100 cites `lib/gemini.ts:390-402` for the `ensureSectionTimestamps` repair. Measured: the
  block is **`:391-403`** and the call is **`:401`**; `:390` is the closing brace of the preceding
  `if (!c.complete)`.
- **L2** — §6.1:192 cites `:492-505` for `fixSummary`'s retry loop. Measured: the loop is
  **`:494-508`**; `:492` is a comment line and `:505` is the `setTimeout` inside it.
- **L3** — §1's `withCaps` row says *"used at `:326` and `:433`"*. Measured: **four** call sites —
  `326` (`generateSummary`), `433` (`extractQuickView`), `536` (`generateMagazineModel`), `686`
  (`transcribeViaGemini`). The row understates how established the mechanism is, which weakens §6.1's
  own (correct) argument.
- **L4** — §5.2:167 cites `backfill.ts:21` for `updatedAt ?? processedAt`. Measured: **`:22`**; `:21` is
  the signature. (r2-L4, unfixed. `backfill.ts:13` for `mdGeneratedAt` is **correct**.)
- **L5** — §5.1:156 — *"The unattended path reads corrections at `:84`"* — **names no file**. It
  resolves to `lib/job-queue/summary-handler.ts:84` (`readVideo`, before `reserveVideoSlot` and
  `summaryCore` — which makes the "minutes later" claim exactly right). But the nearest preceding
  citation in the same section is `route.ts:77-79`, and `route.ts:84` is a comment. Name the file.
- **L6** — §1's UI-gate row cites `components/VideoMenu.tsx:188`. Measured: `:188` is the button's
  label text; the **gate** is `:181` (`{!cloudMode && video.summaryMd && (`), with `cloudMode` from
  `:52`. (r2-codex-12 said `:181`; v3 moved off `VideoRow.tsx` — good — and landed seven lines past it.)
- **L7** — §5.2:166 cites `route.ts:52-59` for the corrections persist; `:52-53` are its comment, the
  code is **`:54-59`**. (r2-L2, unfixed.)
- **L8** — §6.2's correction row displays **17.4** for a computed **17.4317**. Rounding a worst-case
  *bound* downward is the wrong direction, even at 0.03¢. Write 17.44 or 17.5.
- **L9** — §1.1:64 cites `lib/dig/cloud/dig-blob-key.ts:13-23`; `digSectionKey` spans **`:13-25`** and
  the key expression is **`:22`**. Immaterial, but the range stops two lines before the line that
  carries the claim.
- **L10** — §1 row 6's parenthetical *"a reviewer could not reproduce it"* is a fact about one
  reviewer's checkout, not about the derivation: the path exists on this machine and r2 reproduced the
  row to the digit. §11 item 2 is the right follow-up; the row overstates the problem. (r2-L6, unfixed.)

---

## The brief's questions, answered directly

**1. Did deleting the two optimisations remove those findings, or leave the spec incoherent?**
It removed them — 22 of round 2's 33 findings are gone, including all four Blockings, and none
reappeared in another mechanism. Three things dangle: **§4's rule now names the stamp-input variable**
(**B1**, the serious one — the rule became load-bearing when the surrounding machinery went away, and
it was not re-read against the code afterwards); **§6.2's rewrite dropped `correction_est_cents` while
§6.3 kept requiring a reserve** (**H1**); and **§5.2's title and two rows describe a no-write pass that
v3 no longer has** (**M5**). §7's `no-corrections` outcome survives the deletion intact and is fine.

**2. New costs the deletion introduced — is unconditional `fixSummary` affordable in the aggregate?**
**Yes, and I checked it specifically.** The reservation does not rise (§6.2 is correct), admission is
`reserved + actual + summary_est_cents <= daily_cap_cents` (`0011:114`, `0018:63`), so a playlist-wide
doc-version bump is admitted at exactly today's rate and costs ~0.6¢ per corrected video more in actual
spend — about 60¢ across all 99 rows. **No unbounded aggregate.** The cost the deletion *did* introduce
is not money: unconditional running plus §3's new mandatory validation multiplies the ways a correction
can throw inside the summary job, and a throw there discards a completed ~115¢ generation (**B3**).

**3. Is §4's one-line rule genuinely total?** **No — but not for the reason it worries about.** As a
predicate over corrections *text* it is total: there are no input classes, and I could not construct a
string that produces a false negative. The claim fails on the level above: the rule is stated over the
**wrong quantity** (**B1**), so it is not the rule the implementation will have. Separately, §0's
"no false negatives" claim is scoped to the deleted parser and does not cover the two false-negative
paths v3 adds — §3's validator rejecting a legitimate heading correction (**H2.4**) and §8's
promote-skipped stamp, which §8 honestly admits and §9 row 3 then contradicts (**B2**). One thing I
looked for and did **not** find: the §5.1 re-read is safe — `readVideo`
(`worker-persistence.ts:32-40`) does `if (error) throw error`, so it cannot silently report absent
corrections the way `BlobStore.get` can. That is the repo's canonical trap and this path avoids it.

**4. §6.2's five numbers.** All five verified, one exact to the second (4,416s). See the table above.
Two caveats: the basis is unstated (**M1**) and the input term is bounded by a preflight in another
subsection (**M2**).

**5. §9's "seven existing tests".** **Eighteen**, executed. The number is a mis-copy of r2-claude-B3's
count of tests v2 would have *broken*. At least one assertion (`regenerate.test.ts:105`) is
exact-arity and breaks under §6.1/§6.3 unless the opts argument is built conditionally (**H3**).

**6. §6.1's `withCaps` claim.** **Verified and correct.** `withCaps` is `lib/gemini.ts:36`;
`fixSummary` (`:470-511`) does not use it — it calls `getGenerativeModel({ model: SUMMARY_MODEL })`
with no `generationConfig` at all (`:477`). Coupling the cap to `thinkingBudget: 0` there is right, and
it is what keeps the cost bound honest (`gemini-cost.ts:56-61`). The only defect in the row is that it
undercounts the call sites (**L3**).

**7. §3's structural validation — precise enough to build?** **No — it is the deleted prose rule
relocated** (**H2**), it is justified by a premise §1.1 retracts (**H5**), and §3 and §9 specify two
different checks. It is also the single largest new risk in v3 (**B3**).

**8. Is v3 one implementable slice?** **No** (**M6**). Three, with the money path the natural cut.

**9. What v3 still does not cover.** The magazine envelope (**H7**); the attended reserve amount
(**H1**); the append-only M1 ordering (**M8**, third round); a server-side length cap (**M8**); what
the attended path returns when the preflight rejects (**M2**); what happens when `video.summaryMd` is
set but the cloud blob is unreadable — `get` cannot distinguish absent from unreadable
(`supabase-blob-store.ts:36-41`) and the route would 500 (r2, unaddressed); and the `maxDuration`
value itself (**M3**).

---

## Verdict

**NOT CONVERGED** — but with the qualifier the brief invited, and I want it read as the finding rather
than as a tally.

v3's thesis is correct and it discharged 22 of 33 prior findings without relocating any of them. The
three Blockings are **one clause (B1), one falsifier row (B2), and one paragraph of failure
containment (B3)** — none of them require rethinking the design, and I would expect all three plus
every Low to be fixed in an hour.

What another revision of *this document* will not fix is **M6**. This spec has now spent three rounds
converging a document that describes three slices, and the round-3 finding set is dominated by the
seams between them: **H1** exists because §6.2 (slice C) and §6.3 (slice C) drifted apart; **B3** and
**H6** exist because slice B's failure and sync semantics were never separated from slice A's; **H3**
exists because slice A's test surface was asserted rather than counted.

**Recommendation: fix B1, B2, B3 and the ten Lows in place — they are cheap and they make the document
honest. Then make the one decision that is genuinely the human's: metered or knowingly-unmetered for the
attended cloud route. If unmetered, slice A converges immediately and ships. If metered, slice C is a
money-path spec and should be taken through Phase 1 on its own, as `#46 serve-path bounding` was.**
That is a smaller ask than a fourth round on one document, and it is the ask I would make.
