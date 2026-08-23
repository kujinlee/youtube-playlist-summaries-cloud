# Corrections in the cloud — design spec (v2)

**Backlog:** #23. **Status:** v2, after round-1 dual adversarial review returned NOT CONVERGED from
both halves (26 findings: `docs/reviews/spec-corrections-in-cloud-r1-{codex,claude}.md`).
**Phase:** 1.

**Goal.** Make user corrections work on the cloud path with the same felt behaviour as local, and
stop the video row claiming corrections it never applied.

**Architecture.** Two pure modules — an applicability predicate and an apply pipeline — called from
two thin places: the regenerate route (given a real cloud branch) and the summary handler. One core,
so the attended and unattended paths cannot drift.

---

## 0. What v1 got wrong

v1 was reviewed and failed. Recording the failures because five of six share one shape.

| v1 claimed | Measured |
|---|---|
| Exposure is bounded at ≤0.6¢ | `fixSummary` has **zero** `maxOutputTokens` and **zero** `thinkingBudget` refs. Not a bound. 1.7–2.3¢ with retries |
| Metering through the ledger is non-negotiable | `fixSummary(mdContent, corrections, retries, baseDelayMs)` takes **no billing latch**. Unimplementable as specified |
| The applicability rule skips only on proof | **It inverts on the empty case** — no corrections → no terms → skip condition false → *run* |
| Making the route storage-agnostic is two `fs` calls | The route cannot execute under Supabase at all (§3.3) |
| §8's gap is inherited, not introduced | The unattended path would **pay** for a correction on a body `promote` discards |
| The panel's help text renders with curly quotes | Outer quotes are curly; the quotes **around the terms** are straight (`&apos;`) |

**The shape:** claims about what a function does or bounds, written without opening it. Same shape
as both M1 rounds. **Every load-bearing claim in v2 cites `file:line`.**

---

## 1. Measured starting position

Produced by command on 2026-08-22/23. Re-derive before trusting.

| Fact | Value | How |
|---|---|---|
| Apply paths | one — `app/api/videos/[id]/regenerate/route.ts:63` | `grep -rn fixSummary lib/ app/ worker/ components/` |
| …reachable from cloud | none — `fs.promises` at `:50`, `:69` | same |
| `corrections` in the worker | **0** in `lib/job-queue/summary-handler.ts` | `grep -c` |
| Corrections UI | local-gated (`components/VideoRow.tsx:19`); nothing in `components/cloud/` | `grep -rn` |
| Gemini calls per correction | two — `:63`, `:66` | `grep -n` |
| Mean summary size | 7,288 chars (n=10, 6,247–8,961) | `wc -c` over `~/code/agentic-ai-docs/yps-sync-test/*/raw/0*.md` (⚠ **outside this repo**; a reviewer could not reproduce it) |
| Typical correction cost | ≈0.6¢ | `lib/gemini-cost.ts:33,35` + sizes above |
| **Worst-case correction cost** | **unbounded today** — no output cap, up to 3 attempts | `awk` over `fixSummary`, 0 matches for `maxOutputTokens\|thinkingBudget` |
| Summary job reservation | **`summary_est_cents` default 150** — *"WORST-CASE one-run upper bound from ENFORCED token caps"* | `supabase/migrations/0011_cost_guardrails.sql:29` |
| Per-call Gemini timeout | 60,000 ms | `lib/gemini.ts:105` |
| Route `maxDuration` | none on this route; only `app/api/quick-view/backfill/route.ts:10` sets one | `grep -rn maxDuration app/` |

⚠ Token counts use ~4 chars/token. Treat cent figures as order-of-magnitude.
**Not verified:** the row's "99 existing free-form corrections" — no `psql`; `pg` cannot verify
Supabase's TLS chain.

### 1.1 Corrections to backlog #23 — restated precisely

v1 overcorrected. The accurate statements:

1. *"Carry-forward is unaffordable by construction"* → **wrong**. ≈0.6¢ typical. Wasteful, not
   unaffordable. (Worst case is unbounded, but that is a missing cap, not an inherent cost.)
2. *"A reworded heading orphans paid digs"* → **overstated, not simply wrong.** A reworded heading
   **alone** does not orphan a dig while `startSec` is stable: the blob key uses `startSec`
   (`lib/dig/cloud/dig-blob-key.ts:13-23`) and enqueue validates by it
   (`enqueue-dig-core.ts:33-39`). What it **does** do is drop the magazine gists for *every* section
   (`sameTitles` is positional and all-or-nothing, `read-model.ts:12-24`), and it removes the
   title fallback (`dig-merge.ts:120-155`) that exists precisely to survive `startSec` drift. **If
   both move, orphaning is real.** §4.2.1 records that generation-scoping dissolves the dependency;
   until then the title is load-bearing.

**And "regenerate" is a misnomer.** The route contains zero references to `summaryCore`,
`generateSummary` or `resolveTranscriptSegments`. It **corrects** an existing document. This spec
says *correct*; the URL stays for compatibility.

---

## 2. Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Scope | Corrections work everywhere — not representation-only |
| 2 | Pairs or the existing rewrite? | Keep `fixSummary`; pairs cannot express non-substitution instructions |
| 3 | Property of the video, or an action? | **Property of the video** |
| 4 | Spend on a correction that cannot apply? | No — deterministic short-circuit (§4) |
| 5 | Attended path | A synchronous route, no lease (§6) |
| 6 | Structure | Two pure modules, two thin callers |
| 7 | Unattended stamp when `promote` skips | Do not spend, do not stamp (§8) — **changed in v2** |
| 8 | **Capping and metering `fixSummary`** | **In scope** (user decision, 2026-08-23) — §6 |

---

## 3. Components

### 3.1 `lib/corrections/applicable.ts` — new, pure

No I/O. Must not be able to throw. §4 defines it.

### 3.2 `lib/corrections/apply-core.ts` — new, store-agnostic

`stripQuickViewCallout` → `fixSummary` → `extractQuickView` → `insertQuickViewCallout`.

**Signature must carry `tags`.** `insertQuickViewCallout(fixed, tldr, takeaways, video.tags ?? [])`
(`route.ts:67`) — v1's stated signature dropped it, which would delete the callout's Concepts line
from every corrected document. Input: `{ md, corrections, tags }`. Output:
`{ content, tldr, takeaways }`.

### 3.3 `app/api/videos/[id]/regenerate/route.ts` — modified, and this is real work

v1 said "replace two `fs` calls". **False.** The route cannot execute under Supabase:

- `CorrectionsPanel` POSTs `{ outputFolder, corrections }` (`:52`); the route rejects a missing
  `outputFolder` (`:20-21`) and calls `getPrincipal(outputFolder)` (`:30`) — cloud has no
  `outputFolder`.
- `getStorageBundle()` with no Supabase client throws on the Supabase backend
  (`lib/storage/resolve.ts:51-57`), and that call is at `:35`, **outside the try block**.

**The cloud branch must be specified, mirroring the existing cloud routes:** `?playlist=<uuid>`,
`createServerSupabase`, `getUser`, `resolveOwnedPlaylistKey`, `getPrincipalFromSession`,
`getStorageBundle({ supabaseClient })`. The client becomes scope-aware and must **reject
`outputFolder` in cloud mode** rather than ignoring it. Local behaviour and the local response shape
are unchanged.

**`maxDuration` must be set explicitly.** Per-call timeout is 60 s (`gemini.ts:105`) and `fixSummary`
allows 3 attempts, so the chain's own bound is ~180 s before `extractQuickView`. v1's "10–30 seconds"
was an order of magnitude low. The plan sets a route `maxDuration` consistent with the capped worst
case, or reduces the retry count on this path — and states which.

### 3.4 `lib/job-queue/summary-handler.ts` — modified

After `summaryCore`, **after the abort check at `:170`** (v1 put it before, so a correction could run
on a job whose lease was already lost), and **before** staging.

### 3.5 Why correction stays out of `summaryCore`

`summaryCore` turns transcripts into documents; correction consumes one. Folding them together
deletes the cheap path.

---

## 4. The applicability check — rewritten

v1's rule inverted on the empty case. v2 is an **ordered decision procedure**, not three overlapping
bullets.

```
1. effective corrections is empty or whitespace-only
     → NOTHING TO APPLY. No Gemini. No blob write. Not a "skip" — a different outcome (§4.1).
2. otherwise, split on ';' and newlines into clauses. For each clause, in order:
     a. contains an arrow (→ or ->)  → take quoted tokens LEFT of the first arrow.
                                       If there are none, the clause is IRREDUCIBLE.
     b. contains quoted tokens        → take all of them.
     c. otherwise                     → IRREDUCIBLE.
3. any clause IRREDUCIBLE                        → RUN.
4. no terms extracted (all clauses empty of terms) → RUN.
5. any term occurs in body or card (case-insensitive) → RUN.
6. otherwise                                     → SKIP.
```

Rule 2a's "if there are none, irreducible" resolves v1's overlap: a clause with an arrow but no
quotes matched both bullet 1 and bullet 3, and the two readings disagreed on whether to spend.

**Quote matching** accepts ASCII `'` `"` and curly `‘ ’ “ ”`. ⚠ **v1's stated reason was wrong** —
the panel's example uses straight quotes (`&apos;`, `CorrectionsPanel.tsx:97`); only the surrounding
prose quotes are curly. The real reason is macOS smart substitution in a textarea, which the spec
should say rather than citing the help text.

**Apostrophes.** `don't` contains a `'`. A naive paired-quote scan pairs it with the next apostrophe
and extracts nonsense — which would then not occur in the document and could produce a **false
SKIP**, silently discarding a real correction. Mitigation: a single `'` not followed by a closing
`'` on the same clause **makes the clause irreducible** (fail toward running). The plan carries
explicit cases for `don't`, `it's`, and a possessive inside a quoted term.

**Search body and card.** The body can be clean while `tldr`/`takeaways` still carry the misspelling.

### 4.1 Three outcomes, not two

`nothing-to-apply` (rule 1) is distinct from `skip` (rule 6):

| Outcome | Gemini | Blob | `mdCorrectionsHash` |
|---|---|---|---|
| nothing-to-apply | no | no | set to the empty-corrections constant if it differs |
| skip | no | no | set to `mdHash(effective)` if it differs |
| run | yes | yes | set to `mdHash(effective)` |

Both no-write outcomes are **honest**: with no corrections, or with none that occur, the document
already satisfies what is asked of it.

---

## 5. Data flow

### 5.1 Effective corrections — and the rule v1 conflated

The three-way rule at `route.ts:78-80` is the **stamping** rule: what the hash describes. v1 also
fed it to the apply core, but today only the **request's** corrections reach `fixSummary` (`:63`
passes `trimmedCorrections`, not `effectiveCorrections`). Those differ on a bare correction pass:
the stamp says "the stored corrections are baked in", the apply does nothing.

**v2 makes the apply input explicit and equal to the stamp input.** Both use effective corrections.
This is a deliberate behaviour change on the local bare-pass path — a bare pass now re-applies stored
corrections rather than only claiming them — and it is what decision 3 requires. **The plan must
carry a test for it**, because two existing local tests encode the current behaviour.

⚠ **Staleness.** In the unattended path, corrections are read at `:84` and applied minutes later
after Gemini. A Class-B sync landing in between means we apply a stale set and stamp the stale hash.
v1 called this read "free" and did not name the risk. **Bounded, not fixed:** re-read corrections
immediately before applying and stamp what was actually applied.

### 5.2 Attended

1. Panel POSTs. 2. Resolve scope, principal, storage bundle (§3.3). 3. **Persist corrections first**
(`:52-59`). 4. Read body. 5. Compute effective corrections. 6. §4 procedure. 7/8. Per §4.1.
9. Respond with the shape the panel consumes **plus** the outcome discriminator (§7).

⚠ **Clearing corrections must work on Supabase.** `corrections: undefined` is dropped by JSON
serialization, so `updateVideoFields(p, id, { corrections: undefined })` (`:58`) is a no-op on the
Supabase backend — and the route then stamps `mdHash('')` over a row that still holds corrections.
The plan specifies an explicit clear (a null sentinel the store understands) and tests it against
both backends.

**What a no-write outcome must NOT touch.** v1 listed one field; the enumeration is:

| Field | On a no-write outcome |
|---|---|
| `mdCorrectionsHash` | **the only intended write** |
| `mdGeneratedAt` | **must not move** — no body was generated. `deriveClassASignals` (`backfill.ts:13`) feeds it to the recency tiebreak; a false stamp lets an unchanged cloud body beat a newer local one |
| `summaryHtml`, `tldr`, `takeaways`, `docVersion`, `processedAt` | must not move — the body did not change |
| `annotationsEditedAt.corrections` | **moved by step 3, before the outcome is known.** That is correct — the user *did* edit corrections — but the spec must say so, because it is a Class-B write on a path that otherwise claims to write nothing |
| **`updated_at`** | ⚠ **bumped unconditionally by `merge_video_data`** (`0021:89`), and `deriveHumanSnapshot` reads `updatedAt ?? processedAt` as the provisional timestamp (`backfill.ts:21`). A no-write outcome can therefore make an old `personalNote` look newly edited to sync. **The plan must either use a narrow RPC that does not bump `updated_at`, or prove every affected row has a real `annotationsEditedAt`** |

### 5.3 Unattended

1. `summaryCore` → `core.mdContent`. 2. **Abort check** (`:170`). 3. **Publication pre-check (§8).**
4. Re-read corrections (§5.1). 5. §4 procedure. 6. Stage and promote the result.

---

## 6. Money — capping, metering, and the lease

**In scope by decision 8.** v1 asserted metering as a requirement without a mechanism; v2 makes it
tasks.

**6.1 `fixSummary` gains a cap and a latch.** Today it has neither. It takes
`opts?: { signal?, billing?: BillingLatch, maxOutputTokens?, thinkingBudget? }`, mirroring
`generateJson` (`lib/gemini.ts:264`). The cap is derived from the measured maximum (8,961 chars)
with headroom; `assertNotTruncated` already guards this path, so a cap that is too tight fails loudly
rather than silently truncating a paid document.

⚠ **This changes the local path too.** A document longer than the cap that previously succeeded will
now fail. That is the cost of the decision, and the plan states the chosen cap and its headroom.

**6.2 A correction estimate constant.** `guardrail_config` gains `correction_est_cents`, sized as a
worst-case upper bound from the enforced caps — the same construction as `summary_est_cents`
(`0011:29`), whose comment is explicit that 150 is *"WORST-CASE … from ENFORCED token caps"*. This is
what makes §9's "the ledger moves by the expected amount" writable at all.

**6.3 The unattended path spends inside the summary job's reservation.** Two extra paid calls inside
a job whose 150¢ reservation is a **proof derived from caps** invalidates that proof unless they are
accounted for. The plan either raises `summary_est_cents` by `correction_est_cents` or demonstrates
the capped correction fits existing headroom — **and says which, with the arithmetic.**

**6.4 No lease — re-decided on corrected facts.** The exposure that matters was never duplicate
corrections; it is an attended correction racing the summary worker. Both write the same blob key,
and the worker's generation is the 150¢ side. **The mitigation is the §8 publication pre-check plus
`If-None-Match`-style ordering, not a lease** — and if that proves insufficient in the plan, a lease
returns as an explicit task rather than an assumption.

⚠ The panel's disabled button does **not** bound callers once the route is cloud-enabled: the route
is reachable by any authenticated client. The bound is the ledger and the caps, not the UI.

---

## 7. The outcome discriminator

An unattended no-write is silent, correctly. An **attended** one is a button press that changes
nothing, which reads as a bug. The route returns `applied` / `skipped` / `nothing-to-apply` with the
searched terms, and the panel reports it. This is the only UI surface beyond making the panel
reachable in cloud mode.

---

## 8. Publication pre-check — v1's §8 was wrong

v1 said the unattended gap was inherited. It is not: v1 would have **paid** for a correction on a
body that `promote` discards, then written a card describing it.

`SupabaseBlobStore.promote` is create-if-absent (`:120-123`). **If the final key already exists, the
generation cannot publish** — so before spending anything on correction, the handler checks
`blobStore.exists(principal, finalKey)`. If it exists: **do not correct, do not stamp.**

This is a **spend guard, not a stamping rule** — which is why it avoids what made M1 incoherent. It
does not attempt to gate the card on publication; it declines to buy something that cannot be
delivered.

**Residual, stated:** an occupied key means the whole generation is wasted, not just the correction.
That is backlog #22 and M5 closes it. This spec makes the correction not add to the waste.

⚠ **The unattended path does not stamp `mdCorrectionsHash` today** — `summary-handler.ts` contains
zero `corrections` references. v2 adds that stamp; §9's assertions cover it.

---

## 9. Falsifiers

**Assert at the consumer.** Both M1 versions passed tests measuring the payload while the consumer
never saw the change.

| Claim | Consumer | Assertion |
|---|---|---|
| Cloud attended correction works | the stored body | POST → blob holds corrected text |
| …and the card | `tldr`/`takeaways` **and the callout's Concepts line** | all three reflect the corrected document |
| Unattended corrections survive a version bump | the **published** body and card | both corrected |
| Empty corrections cost nothing | the spend ledger | **zero** movement, zero Gemini calls — the v1 inversion |
| A skip costs nothing | the spend ledger | zero movement |
| A run spends a bounded amount | the ledger | moves by `correction_est_cents`, and the actual is ≤ the cap |
| An occupied final key costs nothing | the ledger | zero movement — §8 |
| An irreducible clause runs | the **body**, not the call count | the document changes; call-count alone is a mechanism assertion |
| A no-write outcome disturbs nothing | the **sync decision** | `reconcileClassA` returns the same action before and after; `updated_at`-driven `deriveHumanSnapshot` unchanged for untouched fields |
| One core, no drift | both entry points | same inputs → byte-identical output **and** the output is correct, not merely equal |
| Local is unchanged | existing local tests | pass, except the two encoding the bare-pass behaviour §5.1 deliberately changes |

**Tiers.** Predicate: unit, many cases — quote styles, apostrophes (`don't`, `it's`), arrow without
quotes, irreducible poisoning the set, empty, whitespace-only, term only in the card. Apply-core:
unit, Gemini mocked at `lib/gemini.ts`. Route, ledger, clearing-on-Supabase: integration.

**Negative tests assert which error**, not that something threw.

**No characterization test for §8's residual.** Backlog #22 already has an `it.failing` tripwire
(`summary-handler-promote-divergence.test.ts:148`) whose comment bans re-asserting current behaviour.

---

## 10. Out of scope

- Deterministic `{from,to}` pairs — **rejected with reasons**, not deferred.
- Backlog #22 itself. §8 stops adding to it.
- Re-authoring existing corrections — no migration; the field keeps its type.
- A real two-sided interleaving test — needs a live stack; M5.

## 11. Follow-ups

1. Correct backlog #23 per §1.1 and record the representation clause as rejected.
2. The measured-sizes row cites a path **outside this repo**; move a fixture in or restate.
3. If the ledger shows duplicate correction traffic, revisit §6.4.
