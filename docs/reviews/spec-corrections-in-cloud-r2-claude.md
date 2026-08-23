# Adversarial review — corrections-in-cloud design spec **v2** (round 2, Claude half)

**Reviewer:** Claude, independent of the Codex half (not read).
**Subject:** `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` — the **working-tree**
version (`a30b344` + one uncommitted hunk touching §10, `git diff` inspected).
**Round 1 read first, both halves**, as instructed: `spec-corrections-in-cloud-r1-{claude,codex}.md`.
The r1-claude half is a different Claude instance's work; I disagree with it in two places (noted).
**Date:** 2026-08-23.

**Counts: 3 Blocking, 11 High, 7 Medium, 7 Low.**

---

## Headline

v2 is a substantially better document than v1. §3.3, §5.2's field table, §3.2's `tags`, §3.4's abort
ordering and §9's consumer-side reframing are real repairs, and most of them adopt the round-1
suggested fix verbatim.

**But the primary question was whether the fixes broke something new, and three of them did.**

1. **§4.1's new `nothing-to-apply` arm silently deletes the local quick-view refresh.** v2 fixed the
   empty-case *inversion* and, in doing so, removed what a bare "Regenerate" press does today. **Seven**
   existing local tests change behaviour or fail, in two files. §5.1 says "two", and names the wrong arm.
2. **§8's new pre-check spends on a probe the repo documents as unable to prove absence.**
   `SupabaseBlobStore.provesAbsence = false`, and the class comment names `exists` by name as the
   reason. §8's guard therefore fails open on exactly the condition it guards, and §6.4 rests the
   whole no-lease decision on it.
3. **§6.1's cap collides with `fixSummary`'s retry loop.** The loop's documented premise is that
   truncation is *stochastic*; a hard `maxOutputTokens` makes it *deterministic*, so an over-cap
   document burns three full paid passes and then throws — on the unattended path, killing a ~115¢
   generation to save 0.6¢.

And the author's round-1 failure mode — *claims about what a function does, written without opening
it* — recurs. §6.1 says its new signature "mirror[s] `generateJson` (`lib/gemini.ts:264`)"; line 264
is real and says `opts?: { signal?: AbortSignal; billing?: BillingLatch }` — it contains **neither**
`maxOutputTokens` nor `thinkingBudget`, because in this repo those two are set together by `withCaps`
and never passed separately. The citation is accurate; the claim about it is not.

---

## What I executed

| Command | Result |
|---|---|
| `npm test` | **268 suites / 2,722 tests, all passing, 27.7 s.** Green baseline (matches r1) |
| `grep -rn fixSummary lib/ app/ worker/ components/` | 4 hits, **one** call site — `route.ts:63`. ✅ reproduces §1 row 1 |
| `grep -c corrections lib/job-queue/summary-handler.ts` | **0**. ✅ reproduces §1 row 3 |
| `grep -n getStorageBundle\|fs.promises …/regenerate/route.ts` | `getStorageBundle` at **`:36`**; `fs.promises` at `:50`, `:69`. ⚠ §3.3 still says `:35` — **L1**, the identical off-by-one r1 filed |
| `grep -rn maxDuration app/` | one hit, `app/api/quick-view/backfill/route.ts:10`. ✅ reproduces §1 row 10 |
| `sed -n '105p' lib/gemini.ts` | `const REQUEST_TIMEOUT_MS = 60_000;`. ✅ reproduces §1 row 9 |
| `wc -c` over `~/code/agentic-ai-docs/yps-sync-test/*/raw/0*.md` | **the path EXISTS on this machine.** Bare glob → n=12, mean 7,358. Excluding the two `-dig-deeper.md` siblings → **n=10, mean 7,288.4, min 6,247, max 8,961.** ✅ reproduces §1 row 6 exactly — see **L6** |
| `python3 len(read())` over the same 10 | **chars: mean 7,345 over n=12 / min 6,219 / max 8,955** — `wc -c` is bytes, not chars (**L5**) |
| hand-recompute of `perRunWorstCents({1800})` | **115¢** — inside the pinned `[110,130]` (`tests/lib/gemini-caps.test.ts:16-20`). Headroom to `summary_est_cents=150` is **35¢**. See **H3** |

**NOT VERIFIED — say it out loud:**

- **Integration and e2e were not run** (no live Supabase stack), per the brief. Every claim about
  `merge_video_data`, `update_video_annotations`, `promote` and the ledger is derived from SQL/TS
  source, **not observed against a database**.
- **No SQL was executed.** No `psql`.
- **No live Gemini call.** The Korean token-density figure in **H11** is a general property of the
  tokenizer, **not measured here** — treat the *direction* as verified from the repo's own first-class
  `'en' | 'ko'` handling (`lib/pipeline.ts:33,78`, `lib/gemini.ts:319`) and the *magnitude* as NOT VERIFIED.
- **No browser was driven.** The macOS smart-substitution premise in §4 remains NOT VERIFIED, exactly
  as r1 said. v2 now rests the curly-quote rule entirely on it.
- **The seven broken local tests (B3) were reasoned, not executed** — there is no implementation to
  run them against. Each is quoted with its assertion and the §4.1/§5.2 rule that contradicts it.
- **"99 existing free-form corrections"** — unverified, exactly as §1 says.
- I edited no file except this one.

---

## Round-1 findings → what v2 did

`✅` fixed · `◐` partly fixed · `⚠` **fix introduced or blessed a new problem** · `✗` not addressed

### Codex half

| # | Sev | Finding | v2 | Note |
|---|---|---|---|---|
| 1 | B | Cloud route underspecified | ✅ | §3.3 adopts the suggested fix verbatim |
| 2 | B | Metering has no implementable mechanism | ◐ | §6.1 adds the latch **parameter**; the attended route still has no reserve/settle and no job. **H1** |
| 3 | B | Unattended pays for a body `promote` discards | ⚠ | §8 is the right *intent* with the wrong *predicate*. **B2** |
| 4 | H | `updated_at` missed as a skip side effect | ✅ | §5.2's table enumerates it with both escape routes |
| 5 | H | Empty **and whitespace-only** ambiguous | ◐ | Rule 1 covers `''`. Whitespace-only never *becomes* the effective value. **M2** |
| 6 | H | Ledger "expected amount" undefined | ◐ | §6.2 names `correction_est_cents`; its value, and the cap it derives from, are both deferred. **H1** |
| 7 | M | Backlog #23 overcorrected | ◐ | §1.1 fixes the `startSec` half and repeats the selective quoting. **H6** |
| 8 | M | Mixed consumer/mechanism falsifiers | ◐ | Mostly fixed; two rows still broken (**H10**, **H1**) |

### Claude half

| # | Sev | Finding | v2 | Note |
|---|---|---|---|---|
| B1 | B | Empty corrections take the RUN branch | ⚠ | Inversion fixed; the new arm deletes the quick-view refresh and breaks 7 tests. **B3** |
| B2 | B | Stamp input vs apply input conflated | ⚠ | Unified deliberately (good) — but §3.3's "Local behaviour … unchanged" survives beside it. **H5** |
| B3 | B | Route cannot execute under Supabase | ✅ | §3.3 |
| H1 | H | Metering has no mechanism | ◐ | as codex-2 |
| H2 | H | No cap; reservation proof invalidated | ⚠ | §6.1 caps it; §6.3 drops r1's "extend `perRunWorstCents`", leaving a live gate over the wrong subject. **H3**, **H2** |
| H3 | H | Stale gists served as fresh; no `ensureSectionTimestamps` | ✗ | **Zero occurrences** of `ensureSectionTimestamps`, `isFresh` or `envelope` in v2. **H6** |
| H4 | H | Apostrophe → false skip | ◐ | Odd-parity caught; **even-parity mis-pairing still false-skips**. **B1** |
| H5 | H | Extraction bullets overlap | ⚠ | Ordering fixes the overlap and adds two new gaps. **H7**, **H8** |
| H6 | H | Attended correction vs worker (150¢) | ⚠ | §6.4 declines a lease citing a mitigation that does not cover the attended→worker direction. **B2**, **M3** |
| H7 | H | Falsifiers | ◐ | Better; the ledger row and the sync-decision row still don't work. **H1**, **H10** |
| M1 | M | apply-core drops `tags` | ✅ | §3.2 |
| M2 | M | Clear is a no-op on Supabase | ◐ | Acknowledged; prescribes a **new** sentinel next to the existing `p_clear`. **M1** |
| M3 | M | `annotationsEditedAt` moves before the outcome | ⚠ | v2 declares it *correct* on a premise the code contradicts. **H9** |
| M4 | M | No `maxDuration` | ✅ | §3.3 |
| M5 | M | Correction runs before the abort check | ✅ | §3.4 + `signal?` in §6.1's opts |
| M6 | M | Corrections read minutes before applied | ✅ | §5.1 ⚠ |
| M7 | M | Unattended stamp depends on the M1 plan | ✗ | §8 ⚠ notes the absence; states no dependency or ordering. **M5** |
| M8 | M | Panel button isn't the bound | ✅ | §6.4 ⚠ |
| L1 | L | `getStorageBundle` is `:36` not `:35` | ✗ | **L1** |
| L2 | L | Three citation drifts | ◐ | `:78-80`→`:78-80` kept (fine, it is the rule); `:52-59` still wrong. **L2** |
| L3 | L | `VideoRow.tsx:19` is a docstring | ✗ | **L3** |
| L4 | L | bytes-vs-chars, English-only sample | ⚠ | Not fixed **and now load-bearing** — §6.1 sizes a money cap on it. **H11** |
| L5 | L | corrections text omitted from cost | ✗ | immaterial |
| L6 | L | `summaryHtml: null` on a skip | ✗ | **L7** |
| L7 | L | `gemini.ts:456` → `:470` | ✅ | citation dropped |
| L8 | L | Predicate must be linear (ReDoS) | ✗ | **M6** |

**Tally: 9 fixed · 11 partly · 7 made worse or newly blessed · 6 untouched.**
The seven `⚠` rows are the reason for the verdict.

---

## BLOCKING

### B1 — §4's apostrophe rule catches only the ODD case; an EVEN number of apostrophes still mis-pairs and produces a **false skip**, which the spec itself calls the worst outcome

**Where:** spec §4:169-171, §4:153-156; `components/CorrectionsPanel.tsx:97,108`;
`tests/api/regenerate.test.ts:33`.

The mitigation, quoted:

> §4:169-171 — *"Mitigation: a single `'` not followed by a closing `'` on the same clause **makes the
> clause irreducible** (fail toward running)."*

That is a **parity** test. It fires when the apostrophe count is odd. It says nothing about a clause
whose count is even but whose pairing is wrong — and r1 H4's structural point was exactly that:
*irreducibility catches clauses from which we extracted **no** tokens; nothing catches clauses from
which we extracted the **wrong** tokens.* v2 quotes the symptom (`don't`) and mitigates one parity.

**Concrete failure.** Corrections text, one clause, no arrow:

```
Fix the speaker's name to 'Kujin' and don't touch 'Anthropic'
```

Apostrophes: `speaker's`(1) · `'Kujin'`(2,3) · `don't`(4) · `'Anthropic'`(5,6) — **six, even**. Every
`'` is followed by a closing `'`, so §4's mitigation does not fire and the clause is **reducible**.
Left-to-right pairing (rule 2b, *"take all of them"*) yields:

| Pair | Extracted token |
|---|---|
| 1–2 | `s name to ` |
| 3–4 | ` and don` |
| 5–6 | `Anthropic` |

Now the document. It misspells Anthropic as *"Ant Throw Pick"* — that is why the user typed the
correction, and it is the panel's own worked example (`CorrectionsPanel.tsx:108`). So `Anthropic` does
**not** occur. Neither does `s name to ` nor ` and don`. Rule 3 does not fire (no clause irreducible),
rule 4 does not fire (three terms extracted), rule 5 does not fire (none occur) → **rule 6: SKIP**.

§4.1 then stamps `mdCorrectionsHash = mdHash(effective)`. The row now asserts the document satisfies a
correction that was never applied, `reconcileClassA` reads it as current (`reconcile-class-a.ts:8`),
and the user's instruction is gone. That is backlog #23 clause (a) — the exact lie this spec exists to
stop — **re-created by the guard built to prevent waste**.

This is not exotic. It needs one possessive or one contraction in the same clause as two quoted terms.

**And it is executable against a committed fixture today.** `tests/api/regenerate.test.ts:102`:

```ts
  it('calls fixSummary when corrections are provided', async () => {
    const corrections = "Fix 'Clawcode' → 'Claude Code'";
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections });
    expect(mockFixSummary).toHaveBeenCalledWith(MD_CONTENT, corrections);
  });
```

`MD_CONTENT` (`:33`) is `'# Title\n\n**URL:** …\n\n---\n\n## 1. Intro\nContent.'` and the fixture card
is `tldr: 'Old TL;DR.'`, `takeaways: ['Old point']`. `Clawcode` occurs in **neither**. Under §4 this
clean, well-formed, arrow-and-quotes correction — the canonical form the panel teaches — **skips**, and
this test fails. That is correct behaviour by §4's rules and it is also the design's central promise
("corrections work") failing on its own example, because the fixture document does not contain the
misspelling. It is a fixture artefact, but it shows how narrow the "proof" in *skip only on proof* is.

**Fix.** Make extraction **conservative by shape, not by count** — the r1 H4 fix, which v2 did not
take. A clause is reducible only if it matches a strict template: optional lead-in, then
`<q>term</q>` (arrow `<q>replacement</q>`)? or a `<q>term</q>` list, where `<q>` is a *balanced* pair,
tokens are non-empty after trim, and **tokens contain no space-delimited English function words**
(a cheap validity check that kills `s name to ` and ` and don`). Everything else is irreducible.
Carry the worked example above as a unit case asserting **RUN**. Until extraction can be *wrong*
rather than merely *absent*, "skip only on proof" is not what §4 computes.

---

### B2 — §8's spend guard calls `exists()`, the one probe this repo documents as **unable to prove absence**; it fails open on precisely the condition it guards, and §6.4 rests the no-lease decision on it

**Where:** spec §8:287-291, §6.4:263-266; `lib/storage/supabase/supabase-blob-store.ts:9-11,33-43,
44-68,85-87,116-123`.

> §8:288-289 — *"before spending anything on correction, the handler checks
> `blobStore.exists(principal, finalKey)`. If it exists: **do not correct, do not stamp.**"*

Open `exists`:

```ts
// lib/storage/supabase/supabase-blob-store.ts:85-87
  async exists(p: Principal, key: string): Promise<boolean> {
    return (await this.get(p, key)) !== null;
  }
```

and `get`:

```ts
// :34-43
  async get(p: Principal, key: string): Promise<Buffer | null> {
    const { data, error } = await this.b().download(this.objectKey(p, key));
    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
    // so a null here does NOT prove the object is absent. …
    if (error) return null;
```

and the class's own first three lines:

```ts
// :9-11
  /** `get` swallows EVERY download failure into null (see the note on it below) and `exists` is
   *  defined in terms of `get`, so this backend can never prove an object is absent. */
  readonly provesAbsence = false;
```

**The comment names `exists` by name as the reason `provesAbsence` is false, and §8 chose `exists` as
a money guard.** The repo also ships the honest probe, `tryGet`, whose 24-line comment (`:44-68`) is a
*corrected* account of exactly this class of mistake ("Checking one direction of a two-directional
question is how it survived"), and the `copy` comment at `:94-99` says copyBlob "reads exclusively
through `tryGet`, which is the honest probe on this backend."

**Concrete failure.** A transient 5xx or timeout on the pre-check download → `get` returns `null` →
`exists` returns `false` → §8 concludes the key is free → the handler pays for `fixSummary` +
`extractQuickView` → `promote` (`:120`) finds the final key present, deletes the staged bytes and
returns. We paid for a correction on a body `promote` discarded. **That is the identical outcome
§8 was written to prevent, reached through the guard.** The guard is one-directional: `true` is
trustworthy (bytes came back), `false` is not.

This is the shape of backlog #34 (*serve path trusts an absence it cannot prove*) reappearing at a new
call site, three weeks after that one was closed.

**Second defect, independent of the probe: it is TOCTOU, and the window is minutes.** §5.3 orders it
step 3, before steps 4–6. Between the check and `promote` sit two Gemini calls whose own bound §3.3
puts at ~180 s. `promote` publishes iff the final key is absent **at promote time**. So `exists` is the
right predicate evaluated at the wrong instant:

- **`false` at check, occupied by promote time** (an attended correction `put`s the same key, or a job
  retry promotes) → we paid for the correction and the generation is discarded anyway.
- **`true` at check, deleted by promote time** (a hard delete — `components/…` ships full hard-delete
  since PR #17) → we skipped correcting and **the generation publishes an uncorrected body with no
  stamp**. §8 says "do not stamp", which is at least honest, but the row then reads
  corrections-stale, `reconcileClassA` sets `needsRegen`, and the self-heal is a **~115¢ paid
  re-summarize** to recover a 0.6¢ edit. See **M4**.

**Third, and this is why it is Blocking rather than High: §6.4 spends the lease decision on it.**

> §6.4:264-265 — *"**The mitigation is the §8 publication pre-check plus `If-None-Match`-style
> ordering, not a lease**"*

The race §6.4 names is *"an attended correction racing the summary worker"*. The §8 pre-check lives
in the **worker**. It does nothing whatsoever about the attended route's unconditional `put` landing
on the final key while the worker is mid-Gemini — the direction that destroys the ~115¢ side. And
`If-None-Match`-style ordering is named nowhere else in the spec and defined nowhere (**M3**). So the
no-lease decision is carried by one mechanism that guards the wrong direction and one that does not
exist.

**Fix.** (a) Use `tryGet` and treat only `{ok:false, reason:'absent'}` as free; treat `unreadable` as
**occupied** (fail closed — declining to spend is the cheap error). (b) State that the pre-check is
advisory, not a guarantee, and that the residual cost of losing the race is one wasted correction —
or move the check to immediately before `promote` and make correction lazy. (c) §6.4 must either
define `If-None-Match`-style ordering concretely (a conditional `put`/`promote` at the seam, which
the `BlobStore` interface does not currently expose) or re-open the lease question, because as written
the decision has no mechanism behind it.

---

### B3 — §4.1's `nothing-to-apply` arm silently deletes the local quick-view refresh; **seven** existing local tests change or fail, in two files, and §5.1/§9 say "two" and name the wrong arm

**Where:** spec §4:146-147, §4.1:177-186, §5.1:199-202, §9:320; `app/api/videos/[id]/regenerate/
route.ts:62-67,85-89`; `tests/api/regenerate.test.ts:46-53,126,148,156,164,171`;
`tests/lib/cloud-sync/regenerate-stamp.test.ts:60,110-120`.

v2 correctly killed r1 B1's inversion. But look at what the route does **today** on a bare pass with
no stored corrections — which is what the `regenerate.test.ts` fixture is (`:46-53` has no
`corrections` key):

```ts
// route.ts:62-67
    const stripped = stripQuickViewCallout(mdContent);
    const fixed = trimmedCorrections ? await fixSummary(stripped, trimmedCorrections) : stripped;
    const { tldr, takeaways } = await extractQuickView(fixed);       // ← ALWAYS runs
    const updatedContent = insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? []);
```

The ternary guards `fixSummary` only. `extractQuickView`, the file write and the `summaryHtml: null`
cache-clear are **unconditional**. A bare Regenerate today is *"refresh the quick view and drop the
HTML cache"* — a real, cheap, user-visible behaviour.

§4.1 deletes it:

> §4.1:181 — *nothing-to-apply · Gemini **no** · Blob **no** · `mdCorrectionsHash` set to the
> empty-corrections constant if it differs*

and §5.2's table adds `summaryHtml`, `tldr`, `takeaways`, `docVersion`, `processedAt`, `mdGeneratedAt`
to the must-not-move list. **The spec nowhere says the quick-view refresh is being removed.** r1 B1's
fix instruction was explicit — *"say what happens to `mdGeneratedAt` **and to the quick-view
re-extraction** in that arm, because the existing tests assert both"*. v2 answered the first half.

**The seven.** All quoted assertions are from the committed files.

| # | Test | Effective corrections | §4 outcome | Result |
|---|---|---|---|---|
| 1 | `regenerate.test.ts:126` *returns 200 with new tldr, takeaways on success* — `expect(body.tldr).toBe('This video teaches X.')` | `''` | nothing-to-apply | **FAILS** — `extractQuickView` never called |
| 2 | `:148` *updates the index with new tldr and takeaways* | `''` | nothing-to-apply | **FAILS** |
| 3 | `:156` *returns 500 when Gemini throws* — mocks `extractQuickView` to reject | `''` | nothing-to-apply | **FAILS** — no Gemini call, route returns 200 |
| 4 | `:164` *clears summaryHtml in the index update on success* | `''` | nothing-to-apply | **FAILS** — §5.2 forbids moving `summaryHtml` |
| 5 | `:171` *includes summaryHtml: null in the JSON response on success* | `''` | nothing-to-apply | **FAILS / undefined** — §7 does not give the no-write response shape |
| 6 | `:102` *calls fixSummary when corrections are provided* | `"Fix 'Clawcode' → 'Claude Code'"` | **skip** (B1) | **FAILS** |
| 7 | `regenerate-stamp.test.ts:110` *an explicit clear stamps against empty corrections* — asserts `mdGeneratedAt: expect.any(String)` | `''` | nothing-to-apply | **FAILS** — §5.2 forbids moving `mdGeneratedAt` |

Against that, §5.1 and §9 say:

> §5.1:201-202 — *"**The plan must carry a test for it**, because **two** existing local tests encode
> the current behaviour."*
> §9:320 — *"Local is unchanged | existing local tests | pass, **except the two** encoding the
> bare-pass behaviour §5.1 deliberately changes"*

Both are wrong twice over: the count is seven, and the arm is `nothing-to-apply`, not bare-pass. The
two tests §5.1 is presumably thinking of — `regenerate.test.ts:108,113` ("does not call fixSummary
when corrections is empty/absent") — are the two that **now pass**, because rule 1 is exactly what they
assert. And `regenerate-stamp.test.ts:98` (the actual bare-pass test, fixture `corrections: 'old
corrections'` at `:60`) also still passes, because `old corrections` has no quotes → rule 2c
irreducible → RUN. §5.1's "deliberate behaviour change" is real but its blast radius is inverted:
the bare-pass path with stored corrections keeps passing (while now silently costing a paid rewrite),
and the path §5.1 does not mention is the one that breaks seven tests.

**Fix.** Decide explicitly, in §4.1, what `nothing-to-apply` does about the quick-view refresh and the
`summaryHtml` cache-clear — they are not corrections, and removing them is a separate product change
riding in on a money guard. Then enumerate the affected tests by name in §9 rather than by count, and
say for each whether it is preserved, rewritten, or deleted. A count is the one form of this claim
that cannot be checked against the repo.

---

## HIGH

### H1 — the attended path still has no ledger, so §9's `correction_est_cents` falsifier is unwritable, and §6's three money subsections do not compose

**Where:** spec §6.1:243-247, §6.2:252-255, §6.3:257-260, §9:315;
`lib/job-queue/billing-latch.ts:1-9`; `supabase/migrations/0011_cost_guardrails.sql:26-38`.

r1 H1 / codex-2 said the requirement had no mechanism. v2 adds one **parameter**:

> §6.1:244 — *"It takes `opts?: { signal?, billing?: BillingLatch, maxOutputTokens?, thinkingBudget? }`"*

`BillingLatch` is a boolean, and its first line says what it is scoped to:

```ts
// lib/job-queue/billing-latch.ts:1-5
/**
 * Job-scoped positive metering signal. Flips to true the instant ANY billable Gemini call
 * returns a response body (proof-of-meter). … Job is the maximal scope for a
 * reservation, so this is terminal-correct.
 */
```

A route has no job, no `ctx`, no reservation to latch against. §6.3 covers only the **unattended**
path (*"spends inside the summary job's reservation"*). §6.2's `correction_est_cents` is therefore
consumed by nobody: on the unattended path the spend is inside `summary_est_cents`; on the attended
path there is no reserve/settle pair, no `guardrail_config` read, no `spend_ledger` write. §6 never
says what the attended route does with money.

So §9's row cannot be written:

> §9:315 — *"A run spends a bounded amount | the ledger | **moves by `correction_est_cents`**"*

On the attended path the ledger moves by zero under every implementation, correct or broken —
r1 H7's "vacuous today", unchanged. On the unattended path it moves by `summary_est_cents`, not
`correction_est_cents`.

I disagree with r1 H1's proposed remedy (build a reserve/settle pair now) — that is a money-path slice
of the shape §6 itself says took seven rounds, and pulling it into this spec is how a slice becomes
three. **Fix:** state plainly which of the two the attended cloud route ships as — metered (and then
scope the reserve/settle explicitly, accepting the size) or knowingly unmetered behind the caps
(and then name it as the accepted risk, and delete §9's ledger row for the attended path or rewrite
its consumer to "the cap", which *is* observable). What cannot stand is a falsifier asserting a
movement no described mechanism produces.

### H2 — §6.1's cap and `fixSummary`'s retry loop are incompatible: an over-cap document costs **three** full paid passes and then throws, and on the unattended path it kills the whole generation

**Where:** spec §6.1:243-250; `lib/gemini.ts:237-250,470-511`.

> §6.1:246-247 — *"`assertNotTruncated` already guards this path, so a cap that is too tight **fails
> loudly rather than silently truncating** a paid document."*

The narrow claim is **true** — `assertNotTruncated` is called at `:497` and throws on `MAX_TOKENS`.
But read the loop it throws into, and the comment that justifies it:

```ts
// lib/gemini.ts:237-243 (assertNotTruncated's doc comment)
 * … Throwing lets the caller's retry
 * loop re-roll; **the truncation is stochastic (thinking-model token budget), so a re-roll usually
 * succeeds.** …
```
```ts
// lib/gemini.ts:492-506
  for (let attempt = 0; attempt <= retries; attempt++) {       // retries = 2 ⇒ 3 passes
    try {
      const result = await model.generateContent(prompt, { timeout: REQUEST_TIMEOUT_MS });
      assertNotTruncated(result);
      …
    } catch (err) {
      lastErr = err;
      if (attempt < retries) { … await new Promise((r) => setTimeout(r, baseDelayMs * 2 ** attempt)); }
    }
  }
  throw new Error(`Gemini summary fix failed: ${cause}`, { cause: lastErr });
```

**The retry loop's stated premise is that truncation is stochastic. A hard `maxOutputTokens` makes it
deterministic.** A document longer than the cap truncates on attempt 1, attempt 2 and attempt 3 —
identically, because the input is identical and the ceiling is fixed. Google bills all three (the
body is generated up to the cap each time). So v2's "fails loudly" costs **3 × the cap's worth of
output tokens**, plus backoff, and then throws.

Consequences v2 does not carry:

1. **Attended:** ~3 × 60 s + backoff, then a 500 the user sees, for a document that was fine yesterday.
2. **Unattended (worse):** the correction runs after `summaryCore` (§3.4). A throw there propagates out
   of the handler *before* `putStaged`/`promote` (`summary-handler.ts:171-178`), so **the entire
   summary generation is lost** — the ~115¢ transcribe+summarize that already succeeded is discarded
   because a 0.6¢ edit could not fit its cap. §6.1's "⚠ This changes the local path too" names the
   smaller of the two blast radii and misses this one entirely.
3. **The cap-too-tight risk is not hypothetical** — see **H11**.

**Fix.** Either (a) set `retries = 0` on a capped `fixSummary` (the re-roll cannot help a deterministic
truncation) and state the pass count in §6.3's arithmetic, or (b) make a truncation
`NonRetryableError` (the repo already has that class, `lib/job-queue/errors.ts`, and uses it for the
transcribe over-cap preflight), and (c) **§3.4 must say that a correction failure does not fail the
job** — catch it, publish the uncorrected body, do not stamp. Losing a generation to a correction is
strictly worse than shipping the generation uncorrected.

### H3 — §6.3's deferral leaves `tests/integration/cap-soundness.test.ts:20` asserting a bound that no longer covers all of the job's paid calls: a green gate over the wrong subject

**Where:** spec §6.3:257-260; `tests/integration/cap-soundness.test.ts:10-22`;
`lib/gemini-cost.ts:78-98`; `supabase/migrations/0011_cost_guardrails.sql:29`.

The brief asks whether the deferral is legitimate. **I ran the arithmetic; it is derivable today, and
the answer is that it fits — but the deferral still breaks a live gate.**

Recomputing `perRunWorstCents({maxDurationSeconds: 1800})` by hand from `gemini-cost.ts:78-98`:

| Term | Value |
|---|---|
| transcribe: (57,600 audio @100¢/1M + 242,400 video @30¢/1M + 4,000 overhead @30¢) + 32,768 out @250¢ | 21.344¢ × 3 passes = **64.03¢** |
| summary: 12 passes × ((40,960+4,000) @30¢ + 8,192 @250¢ = 3.397¢) | **40.76¢** |
| quickview: 3 × 3.397¢ | **10.19¢** |
| **total** | **115¢** (`Math.ceil`) — inside the pinned `[110,130]`, `gemini-caps.test.ts:16-20` |

Headroom to `summary_est_cents = 150` is **35¢**. A capped correction, sized off the existing
`MAX_SUMMARY_OUTPUT_TOKENS = 8192`, costs at most 3 × ((8,192 doc + 4,000 overhead + ~250 corrections)
@30¢ + 8,192 @250¢) ≈ **7.2¢**, plus a **second** `extractQuickView` at 3 × 3.397 ≈ **10.2¢** —
about **17.4¢**. 115 + 17.4 = **132.4¢ ≤ 150¢**. **It fits.** §6.3 could have said so.

**The defect is what the deferral leaves standing.** This is the gate:

```ts
// tests/integration/cap-soundness.test.ts:10-21
it('est >= independently-recomputed worst case x max_attempts (live config)', async () => {
  const { data: cfg } = await adminClient().from('guardrail_config').select('*').single();
  const d = cfg!.max_duration_seconds;
  …
  const worst = tr + (C.SUMMARY_MAX_PASSES + C.QUICKVIEW_MAX_PASSES) * perSummaryPass;
  expect(cfg!.summary_est_cents).toBeGreaterThanOrEqual(Math.ceil(worst) * cfg!.summary_max_attempts);
```

`worst` enumerates transcribe + summary + **one** quickview. Adding a correction and a second
quickview to the job changes the real worst case and changes **nothing** in this recomputation.
Whichever of §6.3's two options the plan picks, this test stays green while no longer measuring the
job's actual maximum. r1 H2's fix instruction said *"extend `perRunWorstCents` with the correction
term"*; **v2's §6.3 dropped that sentence.** The gate's own header comment says its purpose is that
"a bug in that helper can't hide the drift" — it cannot catch a drift in *what the helper enumerates*.

**Second, the headroom is not a constant.** `max_duration_seconds` is a live, editable column
(`0011:34`, `default 1800`), and the unit guard hardcodes 1800. Marginal cost is
32 × (100−30) / 1e6 × 3 ≈ **0.0067¢/s**. Without the correction, 150¢ is reached at ~7,000 s
(~117 min); **with** it, at ~4,400 s (~74 min). The correction consumes 37% of the operating range
before the reservation is unsound. That is the number §6.3 owes the reader.

**Fix.** §6.3 must require the plan to add a `correctionWorstCents()` term to `lib/gemini-cost.ts`,
fold it into `perRunWorstCents`, and extend `cap-soundness.test.ts:19`'s inline recomputation to match
— otherwise the only mechanical check on this reservation silently stops covering it.

### H4 — §6.1's `{ maxOutputTokens?, thinkingBudget? }` bypasses `withCaps`, decoupling the two settings the cost proof needs coupled — and it does **not** "mirror `generateJson`"

**Where:** spec §6.1:243-245; `lib/gemini.ts:29-43,264`; `lib/gemini-cost.ts:56-61,63-70`.

> §6.1:244-245 — *"It takes `opts?: { signal?, billing?: BillingLatch, maxOutputTokens?,
> thinkingBudget? }`, **mirroring `generateJson` (`lib/gemini.ts:264`)**."*

Line 264, read:

```ts
// lib/gemini.ts:264
  opts?: { signal?: AbortSignal; billing?: BillingLatch },
```

`generateJson` takes **neither** cap field. Nothing in this repo does. Every capped call sets both
through one function:

```ts
// lib/gemini.ts:29-43
/** Merge the enforced cloud caps (`maxOutputTokens` + `thinkingConfig.thinkingBudget:0`) into an
 * existing `generationConfig`. When `caps` is absent (the local pipeline) the base object is returned
 * UNCHANGED (same reference) so the local `generateContent` call shape stays byte-identical … */
function withCaps(base: GenerationConfig, caps: CloudGeminiCaps | undefined, maxOutputTokens: number) {
  if (!caps) return base;
  return { ...base, maxOutputTokens, thinkingConfig: { thinkingBudget: 0 } } as GenerationConfig;
}
```

Three things follow.

1. **The coupling is the proof.** `gemini-cost.ts:56-61` states that the thinking term is *"honestly 0
   — **not an upper bound on an unbounded quantity**"* precisely because `thinkingBudget: 0` is set
   wherever a cap is. Two independent optional parameters let a caller set `maxOutputTokens` without
   `thinkingBudget`, and the cost bound silently stops holding. `withCaps` makes that unrepresentable.
2. **§6.1's "⚠ this changes the local path too" is self-inflicted.** `withCaps` returns the base
   unchanged when `caps` is absent — that is the repo's existing, deliberate mechanism for *"cloud is
   capped, local is not"*. Threading `caps?: CloudGeminiCaps` instead of raw numbers gives v2 the
   cloud cap **without** breaking the local path, which is the cost §6.1 asks the reader to accept.
3. **It is a second vocabulary for one concern** — the pattern `scripts/check-vocabulary-collisions.py`
   exists to catch.

To the brief's question: **`thinkingBudget: 0` is safe for this task.** Correction is a mechanical
edit; the repo already runs *summary generation* — strictly harder — with thinking disabled on every
cloud path, and `gemini-cost.ts:56-61` records that flash's `0` is a genuine off-switch (unlike pro's).
The risk is not the value; it is decoupling it from the cap.

**Fix.** `fixSummary(md, corrections, retries, baseDelayMs, opts?: { signal?, billing?, caps?:
CloudGeminiCaps })`, and add `correctionOutputTokens` to `CloudGeminiCaps` (`gemini-cost.ts:63-70`)
next to the two optional serve-path fields already there. Then §6.1's local-path ⚠ disappears.

### H5 — §3.3 still says local behaviour and the local response shape are unchanged; §5.1 and §7 both change them. r1 B2's contradiction, reproduced verbatim in v2

**Where:** spec §3.3:120-121, §5.1:199-201, §7:275-277.

> §3.3:120-121 — *"**Local behaviour and the local response shape are unchanged.**"*
> §5.1:200-201 — *"This is a **deliberate behaviour change on the local bare-pass path** …"*
> §7:275-277 — *"The route returns `applied` / `skipped` / `nothing-to-apply` with the searched terms"*

Three sentences, two direct contradictions, one of them the exact sentence r1 B2 flagged in v1
(*"§3.3:93 — Local behaviour and the response shape stay identical"*). The word "local" was inserted;
the claim was not re-checked against the sections that falsify it. §7 does not say the discriminator
is cloud-only, and it could not sensibly be — the panel is one shared component
(`components/VideoMenu.tsx:52,181` gates it by `cloudMode`, it is not duplicated).

Per **B3**, local behaviour changes far more than §5.1 admits. **Fix:** delete the §3.3 sentence and
replace it with a pointer to a single "what changes locally" list — §5.1 and §7 both write into it.

### H6 — r1 H3 is **entirely absent** from v2, and §1.1's rewrite repeats the selective quoting that produced it

**Where:** spec §1.1 item 2:62-69; `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md`
§4.2.1; `lib/html-doc/read-model.ts:12-24`; `lib/gemini.ts:401`; `lib/html-doc/parse.ts:16,30-33`.

`grep -n "ensureSectionTimestamps\|isFresh\|envelope\|stale gists\|reserve-and-charge"` over v2 returns
**zero hits.** A High from round 1, unmentioned — not deferred, not rejected, not in §10, not in §11.

And §1.1's rewrite does the same thing that earned the finding. It now says:

> §1.1:64-66 — *"What it **does** do is drop the magazine gists for *every* section (`sameTitles` is
> positional and all-or-nothing, `read-model.ts:12-24`), and it removes the title fallback
> (`dig-merge.ts:120-155`)…"*

Both citations check out — `sameTitles` is `.every((t, i) => t === titles[i])` with a length equality
(`read-model.ts:14-19`), and `dig-merge.ts:120-155` is the title-fallback pass. **But this is still
§4.2.1's first bullet only.** The second bullet — *"titles held constant while the prose changes serves
**stale gists as fresh** (that one is deliberate: `fixSummary`'s prompt pins headings precisely so this
holds)"* — describes **this design running correctly**, and is still omitted. A successful correction
is by construction *prose changed, headings pinned*:

```ts
// lib/html-doc/read-model.ts:21-24
export function isFresh(envelope: { sourceSections: string[]; generatorVersion?: string }, titles: string[]) {
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
}
```

No content hash. So after every corrected generation the cached magazine model still reads fresh and
serves pre-correction gists over corrected prose. §5.2's table now *forbids* touching `summaryHtml` on
a no-write outcome (correct) and §4.1 forbids a blob write — but on the **run** path nothing in v2
invalidates the model envelope. §9's row *"…and the card | `tldr`/`takeaways` **and the callout's
Concepts line**"* covers three consumers and not this one.

Separately, `fixSummary` still has no `ensureSectionTimestamps` — that repair runs only inside
`generateSummary` (`lib/gemini.ts:401`) — while `startSec`, the dig blob key's only input
(`dig-blob-key.ts:19`, `enqueue-dig-core.ts`), is parsed out of a `▶` markdown line
(`parse.ts:16,30-33`) inside the document `fixSummary` rewrites. One mangled `▶` re-keys a
`DIG_EST_CENTS = 150` artefact (`gemini-cost.ts:54`).

**Fix.** §1.1 item 2 must quote both bullets of §4.2.1 — a correction to a correction that reproduces
the original's omission is not a correction. Then either add to §3.2 that apply-core runs
`ensureSectionTimestamps` and invalidates the model envelope, or move both to §10 with a reason. What
is not acceptable is silence, because §1.1's current text makes the risk read *smaller* than measurement
supports, and decision 2 is argued partly from it.

### H7 — §4 has no rule for an **empty clause**, so a trailing `;` — the separator the panel itself teaches — makes every correction irreducible and forces a paid run

**Where:** spec §4:145-157, §2 decision 4:84, §9:313; `components/CorrectionsPanel.tsx:108`.

The procedure:

```
1. effective corrections is empty or whitespace-only → NOTHING TO APPLY
2. otherwise, split on ';' and newlines into clauses. For each clause, in order:
     …  c. otherwise → IRREDUCIBLE.
3. any clause IRREDUCIBLE → RUN.
```

Rule 1 tests the **whole string**; rule 2 splits it. Nothing says what happens to a clause that is
empty after the split.

**Concrete failure.** The panel's placeholder is:

```tsx
// components/CorrectionsPanel.tsx:108
  placeholder="e.g. Fix 'Clawcode' → 'Claude Code'; fix 'Ant Throw Pick' → 'Anthropic'"
```

A user follows it and ends with a trailing separator: `Fix 'Clawcode' → 'Claude Code';`. Split on `;`
→ `["Fix 'Clawcode' → 'Claude Code'", ""]`. The second clause has no arrow (2a no) and no quoted
tokens (2b no) → **2c IRREDUCIBLE** → rule 3 **RUN**, unconditionally, before rules 4–6 are ever
consulted. **A trailing semicolon disables the entire skip mechanism.** So does a blank line between
two corrections, and so does `";"` or `"."` typed alone (neither is whitespace-only, so rule 1 misses
them).

That is a direct violation of decision 4 (*"Spend on a correction that cannot apply? **No** —
deterministic short-circuit"*), and §9's row *"Empty corrections cost nothing | the spend ledger |
**zero** movement"* will be written against `''` and pass while `';'` spends. It is the same class as
the v1 inversion §4 was rewritten to fix — the empty case reappearing one level down, at the clause.

**Fix.** Add to rule 2: *"clauses that are empty or whitespace-only after the split are **discarded**;
if no clauses remain, the outcome is nothing-to-apply."* Carry `";"`, `"a;"`, `".":` and `"x\n\ny"` as
unit cases. This costs one line and closes the arm the brief asked about.

### H8 — §4's rule 2a discards every term after the second arrow in a multi-arrow clause → false skip

**Where:** spec §4:149-151.

> *"a. contains an arrow (→ or ->) → take quoted tokens **LEFT of the first arrow**."*

v2 formalised r1 H5's ambiguity into an unambiguous rule, and the rule is wrong for a clause with two
arrows. Input, one clause, no `;`:

```
Fix 'Clawcode' → 'Claude Code' and 'Ant Throw Pick' → 'Anthropic'
```

Left of the **first** arrow: `'Clawcode'`. `'Ant Throw Pick'` is never extracted and never searched.
Document already says *Claude Code* (corrected last week) but still says *Ant Throw Pick*: one term,
reducible, does not occur → **rule 6 SKIP**, and the live instruction is discarded and stamped as
applied. Joining clauses with "and" instead of ";" is the whole of the input required.

**Fix.** Either take quoted tokens left of **each** arrow (segment the clause on arrows first), or make
a clause containing more than one arrow **irreducible**. The second is one line and fails toward
running. Add this exact string as a unit case asserting RUN.

### H9 — §5.2 blesses the `annotationsEditedAt` bump on a premise the route contradicts: step 3 fires on an **unchanged** text, so a no-op button press can beat a real remote edit

**Where:** spec §5.2:228; `app/api/videos/[id]/regenerate/route.ts:54-56`;
`supabase/migrations/0021_cloud_sync_signals.sql:75-77`; `lib/cloud-sync/backfill.ts:19-32`.

> §5.2:228 — *"`annotationsEditedAt.corrections` | **moved by step 3, before the outcome is known.**
> That is correct — **the user *did* edit corrections** — but the spec must say so…"*

The premise is false. Step 3 is `route.ts:54-56`:

```ts
    const trimmedCorrections = typeof corrections === 'string' ? corrections.trim() : undefined;
    if (trimmedCorrections) {
      await store.updateVideoFields(principal, videoId, { corrections: trimmedCorrections });
```

The condition is *"the parameter is non-empty"*, **not** *"the value changed"*. The panel posts the
textarea contents on every press (`CorrectionsPanel.tsx:49-52`), so pressing Regenerate twice without
touching the text writes the identical string twice, and `merge_video_data` stamps on key presence:

```sql
-- supabase/migrations/0021_cloud_sync_signals.sql:75-77
  foreach k in array classb loop
    if p_fields ? k then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
  end loop;
```

**Concrete data loss.** A user edits `corrections` on **local** at T2. On **cloud** they press
Regenerate at T3 without changing the text. `deriveHumanSnapshot` (`backfill.ts:22`,
`editedAt: real ?? provisional`) now reports the cloud value as edited at T3. Newer-wins keeps the
cloud's *unchanged* value and **discards the local T2 edit**. r1 M3 named this; v2 converted it from a
defect into documented, blessed behaviour by asserting something the four lines above disprove.

This is the round-1 shape verbatim: an outcome attributed to a function without opening it.

**Fix.** Step 3 must be conditional on `trimmedCorrections !== (video.corrections ?? '')`, and §5.2's
row should read *"moved by step 3 **only when the text actually changed**"*.

### H10 — §9's sync-decision falsifier asserts the **opposite** of what §4.1 prescribes, so a correct implementation fails it

**Where:** spec §9:318, §4.1:181-183; `lib/cloud-sync/reconcile-class-a.ts:8,20-40`.

> §9:318 — *"A no-write outcome disturbs nothing | the **sync decision** | `reconcileClassA` returns
> the same action **before and after**"*

But §4.1 says a `skip` **sets** `mdCorrectionsHash` to `mdHash(effective)`, and that field is the sole
input to the currency predicate:

```ts
// lib/cloud-sync/reconcile-class-a.ts:8
const current = (s: ClassASignals, cur: string): boolean => s.mdCorrectionsHash === cur;
```
```ts
// :22-23, :38-39
  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };
  …
  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
```

Flipping `cCur` from false to true is the *entire point* of stamping on a skip — it is what stops the
row from being read as corrections-stale and triggering a paid `needsRegen`. So the decision **must**
change. A test written to §9 literally fails on a correct implementation; a test written to make §9
pass has to be built on a fixture where the hash already matched, which makes it vacuous — r1 H7's
finding relocated, not fixed.

**Fix.** Split the row. (i) *the `needsRegen` verdict goes from true to false after a skip* — the
change we want, and it fails if the stamp is missing. (ii) *nothing else in `ClassASignals` /
`HumanSnapshot` moves* — `mdHash`, `mdGeneratedAt`, `docVersionMajor`, and every `annotationsEditedAt`
entry byte-identical before and after. That is the "disturbs nothing" claim, and it is falsifiable.

### H11 — §6.1 sizes a money cap on a 10-file **English byte** sample; Korean is a first-class language here, and an over-cap document hard-fails (H2)

**Where:** spec §1 row 6:45, §6.1:246; `lib/pipeline.ts:33,78`; `lib/gemini.ts:319`;
`lib/ask-gemini.ts:7-8,23-27`.

> §6.1:246 — *"The cap is derived from the **measured maximum (8,961 chars)** with headroom"*

Two defects compound.

1. **It is 8,961 bytes, not chars.** I reproduced the row exactly with `wc -c` (n=10, mean 7,288.4,
   max 8,961) and then counted characters: max **8,955**, mean 7,345 over the full n=12 glob. For
   ASCII the two are nearly equal, which is why the error looked cosmetic in round 1 (r1 L4) — but
   §6.1 has now made it the basis of a cap whose violation costs a generation.

2. **All ten files are one English playlist** (`cs146s-…`), and this repo shipped Korean as a
   first-class path: `language: 'en' | 'ko'` (`lib/pipeline.ts:33`), `langRaw?.toLowerCase() === 'ko'`
   (`:78`), Korean prompt branches (`lib/ask-gemini.ts:8,27`), and backlog #36 (non-ASCII titles) closed
   nine days ago. For Korean, bytes are ~3× chars, and — the part that matters — Gemini tokenizes
   Hangul far denser than English. A cap set at `8,961 / 4 ≈ 2,240 output tokens + headroom` is
   comfortable for these ten documents and **too small for a Korean summary of the same reading
   length**. Per **H2**, too small means three paid passes and a thrown error; on the unattended path
   that discards the whole generation.
   *(The token-density ratio is NOT VERIFIED here — no live tokenizer call. The direction is not in
   doubt; the multiplier is.)*

**Fix.** Do not derive a new constant from this sample. Use `MAX_SUMMARY_OUTPUT_TOKENS = 8192`, which
already bounds the output of the document `fixSummary` is rewriting, is language-agnostic, is already
inside the 150¢ proof, and is already the number `digWorstCents()` reuses for exactly this reason
(`gemini-cost.ts:118`: *"section summaryProse <= whole-summary output cap"*). Then restate §1 row 6 as
*"bytes, single English playlist, n=10"* and delete it from §6.1's derivation.

---

## MEDIUM

### M1 — §5.2 invents a "null sentinel" for clearing next to the mechanism the store calls its *sole* surface

§5.2:219 — *"The plan specifies an explicit clear (**a null sentinel the store understands**)"*. The
repo already has the clear: `update_video_annotations`'s `p_clear` array
(`0021_cloud_sync_signals.sql:38-43`), allowlisted and Class-B-stamping, reached through
`updateVideoAnnotations`, whose own comment says it is *"the **sole caller-facing surface** for
personal-annotation writes"* (`supabase-metadata-store.ts:257-262`), and which
`app/api/videos/[id]/review/route.ts` already uses. Adding a sentinel to `updateVideoFields` is a
second mechanism for one concern. **Fix:** route the clear through `updateVideoAnnotations({}, {clear:
['corrections']})` and say so.

### M2 — whitespace-only corrections are still unresolved (codex-5)

Rule 1 tests *effective* corrections. `"   "` never becomes effective: `route.ts:54` trims it to `''`
(falsy), `corrections === ''` is false, so neither persist branch fires and `effectiveCorrections`
falls back to `video.corrections ?? ''` (`:79`). Clearing the textarea to spaces therefore leaves the
stored corrections in place **and re-applies them** under §5.1's new rule. Codex-5 asked for
"normalization before persistence and applicability: empty/whitespace means clear or absent, exactly
one". v2 answers for `''` and not for `"   "`. **Fix:** normalise at the route boundary —
`corrections?.trim()` — and state which of clear/absent whitespace means.

### M3 — `If-None-Match`-style ordering is load-bearing in §6.4 and defined nowhere

§6.4:264-265 names it as half the reason not to take a lease. It appears once in the document. The
`BlobStore` interface exposes no conditional write (`put` is `upsert: true`,
`supabase-blob-store.ts:29-32`), so this is a new seam capability, not a usage note. Either specify it
(a `putIfAbsent`, or an ETag threaded through `StagedRef`) or drop it and let §8 carry the decision
alone — in which case **B2** applies with full force.

### M4 — §8's other TOCTOU direction publishes an uncorrected, unstamped body

Covered in **B2**; separated because the fix differs. Key deleted between check and `promote` → we
declined to correct, the generation publishes clean, the row keeps its old `mdCorrectionsHash`,
`reconcileClassA` sets `needsRegen`, and the self-heal is a ~115¢ re-summarize. §8 should state this
residual explicitly next to the one it already states, and say whether the re-summarize is acceptable.

### M5 — the new unattended stamp has no stated dependency on the append-only M1 plan

§8:298-299 says the unattended path stamps nothing today and v2 adds it. The plan that also adds
`mdCorrectionsHash` to the worker's write path is append-only M1, whose last recorded verdict is
`NOT CONVERGED` (`docs/reviews/plan-append-only-m1-r2-claude.md`). Two specs writing the same field
through `persist_summary` need an order. **Fix:** state the dependency in §2 or §10 and say what this
slice does if M1 lands after it. (r1 M7, unaddressed.)

### M6 — §3.1 requires the predicate not to throw, and says nothing about not hanging

§3.1:96 — *"No I/O. **Must not be able to throw.**"* The input is server-side unbounded (`route.ts:24-26`
validates only `typeof === 'string'`; the 1,000-char cap is client-side at `CorrectionsPanel.tsx:105`),
and the sync path writes this field too. A quote/arrow tokenizer over unbounded input is a
catastrophic-backtracking surface, and the unattended caller holds a lease. **Fix:** add *"must be
linear in input length"* and a server-side length cap. (r1 L8, unaddressed.)

### M7 — the scope of the apostrophe parity check is ambiguous; the brief's own example resolves two ways

The brief asks about `'Clawcode's' → 'Claude Code's'`. §4:169-170 says *"on the same **clause**"*, but
rule 2a extracts from a **window** (left of the first arrow). The clause has six `'` (even → not
irreducible); the window has three (odd → irreducible). Two engineers, two behaviours:

- **window scope** → IRREDUCIBLE → RUN. Safe.
- **clause scope** → reducible; pairing gives `Clawcode` (and a straddling junk token) → `Clawcode`
  occurs as a substring → RUN. Safe **by accident** — the substring match rescues it, not the rule.

Both happen to run here, so this example is not itself a defect; it is a fork the plan will resolve by
coin-flip, and **B1** shows the neighbourhood where the coin matters. **Fix:** say the parity check
applies to the **extraction window**, and carry `'Clawcode's' → 'Claude Code's'` as a named case.

---

## LOW

- **L1** — §3.3:115 says `getStorageBundle` is at `route.ts:**35**`. Measured: **`:36`**. This is the
  exact off-by-one r1 filed as L1, in the row whose subject is that call, in a document whose §0 ends
  *"Every load-bearing claim in v2 cites `file:line`."*
- **L2** — §5.2 step 3 cites `route.ts:52-59` for the corrections persist; `:52-53` are its comment,
  the code is `:54-59`. (r1 L2, unfixed.)
- **L3** — §1 row 4 still cites `components/VideoRow.tsx:19` for the UI gate. Line 19 is the first line
  of a **prop docstring**; the gate is `components/VideoMenu.tsx:181` (`{!cloudMode && video.summaryMd
  && (`) with `cloudMode` from `useScope()` at `:52`. (r1 L3, unfixed.)
- **L4** — §5.2 cites `backfill.ts:21` for `updatedAt ?? processedAt`; `:21` is the function signature,
  the expression is `:22`. `backfill.ts:13` for `mdGeneratedAt` is **correct**.
- **L5** — §1 row 6 says "chars" and derives with `wc -c`, which counts **bytes**; and the "How" column
  gives a bare `0*.md` glob, which yields **n=12** (mean 7,358) because two `-dig-deeper.md` siblings
  match. The stated n=10 requires an unstated exclusion. Say *"bytes; `0*.md` excluding
  `*-dig-deeper.md`; one English playlist"*.
- **L6** — §1 row 6's parenthetical *"a reviewer could not reproduce it"* is a fact about the Codex
  reviewer's **checkout**, not about the derivation: the path exists on this machine and reproduces to
  the digit. §11 item 2 (move a fixture in) is still the right follow-up, but the row overstates the
  problem as unreproducibility.
- **L7** — no section says what the response's `summaryHtml` field is on a no-write outcome. Today the
  route returns `summaryHtml: null` (`route.ts:95`) and the panel writes it into local state
  (`CorrectionsPanel.tsx:63`); under §5.2 the server keeps the cached HTML, so the client would drop a
  pointer the server still holds. §7 adds a discriminator and does not revisit the rest of the shape.

---

## The brief's six pressure points, answered

1. **§4's ordered procedure.** The overlap is fixed and two new gaps opened. Rule 1 does **not** catch
   everything it must: separator-only and punctuation-only inputs (`";"`, `"."`) fall through to
   rule 2, become empty/unquoted clauses, and **RUN** (**H7**) — a trailing `;`, the panel's own
   separator, disables the whole skip mechanism. Arrow-only and quotes-with-nothing-inside are safe
   (both run; the empty token trivially "occurs"). **The ordering itself creates one new inversion**:
   rule 2a's *"LEFT of the first arrow"* discards every term after a second arrow (**H8**).
2. **§4's apostrophe rule.** It is a parity test, and the false skip survives at even parity
   (**B1**), on an ordinary sentence containing one possessive and one contraction. It does not
   over-run on the brief's `'Clawcode's'` example, but the scope of "the same clause" is ambiguous
   there and the two readings differ (**M7**). r1 H4's structural point — nothing catches the *wrong*
   tokens — is unaddressed.
3. **§6.1's cap.** The measured maximum is **not** a sound basis: it is bytes not chars, from one
   English playlist, in a codebase where Korean is first-class (**H11**). `assertNotTruncated`
   **does** throw as claimed (`gemini.ts:245-250`, called at `:497`) — but into a 3-attempt retry loop
   whose documented premise ("truncation is stochastic") a hard cap falsifies, so an over-cap document
   costs three paid passes and then kills the job (**H2**). `thinkingBudget: 0` is **safe** for this
   task and well-precedented; the defect is decoupling it from the cap by not going through `withCaps`
   (**H4**).
4. **§8's pre-check.** Yes, TOCTOU, in both directions, across a ~180 s window (**B2**, **M4**). And
   `exists` is **not** the right predicate — not because the *kind* is wrong (`promote` does turn on
   final-key presence) but because on this backend `exists` cannot prove absence, by the class's own
   declaration (`provesAbsence = false`, `supabase-blob-store.ts:9-11`), so the guard fails open on
   exactly the condition it guards. `tryGet`'s `absent` is the honest probe, and "unreadable" must be
   treated as occupied.
5. **§5.1's behaviour change.** The tests that encode the old behaviour are **seven**, not two, and
   they sit on the `nothing-to-apply` arm §5.1 does not mention rather than the bare-pass arm it does
   (**B3**). The change *is* required by decision 3 — a property of the video means a bare pass
   re-asserts it — so it is not scope creep. But it **interacts badly with the local UX**: a bare
   Regenerate today refreshes the quick view and clears the HTML cache unconditionally
   (`route.ts:64-67`), and §4.1 removes that for every video without corrections, silently.
6. **§6.3's arithmetic.** The deferral is **half legitimate**. The arithmetic is fully derivable from
   constants already in the repo and I ran it: 115¢ measured worst case, 35¢ headroom, ~17¢ for a
   capped correction plus its second quickview ⇒ **it fits at the default duration** (**H3**). What
   the deferral is dodging is not the sum but the **instrument**: `tests/integration/
   cap-soundness.test.ts:19` enumerates transcribe + summary + one quickview, and stays green under
   either of §6.3's two options while no longer covering the job's real maximum. r1's fix instruction
   ("extend `perRunWorstCents`") was dropped in the rewrite. And the headroom is not a constant —
   `max_duration_seconds` is editable, and the correction consumes 37% of the range before the
   reservation goes unsound.

## Also assessed

- **Internal consistency.** Three contradictions remain: §3.3 "local unchanged" vs §5.1 + §7
  (**H5**, r1 B2 verbatim); §9's sync-decision row vs §4.1's stamping rule (**H10**); §6.2's
  `correction_est_cents` vs §6.3's "spends inside the summary reservation" — the constant has no
  consumer (**H1**).
- **§9's falsifiers — do any still measure the mechanism?** Mostly repaired; the reframing to
  consumers is genuine and the *"call-count alone is a mechanism assertion"* line is right. Two rows
  still fail: the ledger row is vacuous on the attended path (**H1**) and the sync-decision row is
  inverted (**H10**). One more is weaker than it reads: *"Empty corrections cost nothing"* will be
  written against `''` and will not catch `";"` (**H7**).
- **Ambiguous enough to be built two ways.** The apostrophe-check scope (**M7**); empty clauses
  (**H7**); `If-None-Match`-style ordering (**M3**); the no-write response shape (**L7**); whether the
  outcome discriminator is local too (**H5**).
- **What v2 still does not cover.** The magazine envelope and `ensureSectionTimestamps` (**H6**); the
  attended money path (**H1**); the append-only M1 ordering (**M5**); predicate linearity (**M6**);
  what an attended correction does when `video.summaryMd` is set but the blob is unreadable — the
  cloud `get` cannot distinguish absent from unreadable and the route currently 500s.
- **Where I disagree with the r1 Claude half.** (i) Its H1 remedy — build a route-side reserve/settle
  now — would triple this slice; the decision, not the mechanism, is what §6 owes (**H1**). (ii) Its
  B1 claimed `tests/api/regenerate.test.ts:108,113` fail under v1's rule; under **v2** those two are
  the ones that now pass, and five different tests in the same file fail instead (**B3**). The
  finding was right; the specific tests were not the ones that break.

---

## Verdict

**NOT CONVERGED**
