# Claude adversarial review — `2026-08-04-cas-fence-persist-summary-design.md` (round 4)

**Reviewer:** Claude (adversarial mandate)
**Branch:** `docs/cas-fence-spec` @ `717eecf` (spec v4)
**Date:** 2026-08-05
**Method:** every v4 citation re-read on this branch; the two load-bearing mechanisms
(monotonic-status inheritance under a re-address, and the NULL-vs-NULL guard outcome) **measured**
against `supabase_db_youtube-playlist-summaries-cloud`, not inferred; live row-shape census re-run
(2902 rows). `scripts/check-docs.py` re-run — *"Documentation integrity OK"* (§11's claim holds).

---

## Verdict

**NOT CONVERGED.** Three Blockings and six Highs. Two of the three Blockings are *carried* defects
that v4 declared fixed by removing one of two ingredients; the third is new, inside v4's own new
`publish()`.

- **B-R4-1** — §6's residual claim is **false, and measured false**. The inherited-`promoted` window
  is *not* bounded: any fault inside it is frozen **permanently** by the idempotency skip
  (`summary-handler.ts:86-92`), and on that same path the pre-slice behaviour it claims to be
  "strictly smaller than" **self-heals**. The whole scope-out of #22 rests on this sentence.
- **B-R4-2** — removing `p_artifact_is_new` closed only the *status* half of round 3's B-R3-2.
  `publish = put` on its own still converts a stale same-address worker's write from
  **non-corrupting into destructive**, falsifying the property `summary-handler.ts:166-170` records
  in prose, with no acknowledgement anywhere in v4.
- **B-R4-3** — v4's new verify-after-write reads with **`get`**, the one primitive this repo's
  `BlobStore` contract explicitly forbids *"before any irreversible or billable decision"*
  (`blob-store.ts:46-56`), and which `copyBlob` — the precedent §6 cites by name — never uses
  (`blob-store.ts:125`). Fresh instance of *absent-vs-failed conflation*, a shape §11 carries in its
  own standing list, on the money path.

Three things v4 got right and I could not break: the **admitted torn read** really is correct and
self-correcting (I attacked it four ways; details below); the 7-argument shape now matches exactly
what G14 measured (M-R3-5 closed by construction); and the `p_expected_serial` provenance +
coercion gap (B-R3-1) is genuinely closed.

---

## (A) Round-3 findings — genuinely fixed, or reworded?

### Claude round 3

| # | Finding | Status | The v4 text, and whether behaviour changes |
|---|---|---|---|
| **B-R3-1** | `observedSerial` has no provenance; the only workable one is a torn read | **FIXED (design) / PARTIAL (test)** | §6:259-274 names it: *"Attempt 1: `observedSerial := reserveVideoSlot(...)` # NOT the `:84` read"*, and §6:272-274 adds *"Both values are coerced `?? null` at the wrapper. §4 originally mandated this for the key only; `p_expected_serial` needs it just as much."* The torn read is admitted at §6:263-270 instead of hidden. Real behaviour, not prose. **Residual gap:** §8 still has **no test for a brand-new video with no row at all** — §8:446 covers a `serialNumber`-*absent row*, which is a different case (and unreachable, see M-R4-1). §4's code block (line 164) still shows only the `p_expected_summary_md` coercion (L-R4-1). |
| **B-R3-2** | `p_artifact_is_new` + `publish = put` together make a stale write destructive | **PARTIALLY FIXED** | The flag is gone (§4:150-152, §10:504-509) — that closes steps 1-5 of round 3's table (the row no longer gets downgraded to `committed`). **Steps 6-7 are untouched.** `publish = put` overwrites unconditionally, so a stale worker still destroys a concurrent worker's paid bytes and then stamps `promoted` over them. See **B-R4-2**. §8 still mandates **no two-worker test** — round 3 asked for one explicitly. |
| **B-R3-3** | `publish = put` discards the verification it depends on | **PARTIALLY FIXED** | §6:322-331 adds `put → read back → compare → throw before persisting 'promoted'`, and §6:333-337 cites `copyBlob`'s *"an unproven copy is not a copy"* — **and** correctly notes that `transferClassA`, the precedent v3 cited, does **not** verify, calling that *"a defect in `transferClassA` worth its own entry, not a pattern to follow."* That is a genuine fix and an honest one. But it reads with `get` (**B-R4-3**), and §6:379 **retains verbatim** *"A leaked staging object is inert and swept"* — which round 3 proved false (**H-R4-4**). |
| **H-R3-1** | The adopt rule silently changes re-summarize addressing; contradicts §0/§9 #20 | **NOT FIXED** | §6:277-280's adopt branch is still unscoped to the recovery path — attempt 1 adopts whenever `observedSummaryMd` is non-null, so the worker can no longer move the key on a title change. §0:63-64 still says *"Unguarded, deliberately: a re-summarize that moves the key itself after a title change… That is backlog #20"*, and §9:465 still files #20 as open. Nothing in v4 acknowledges the change. **M-R4-5.** |
| **H-R3-2** | `p_artifact_is_new = NULL` fails open destructively | **FIXED (by removal)** | Parameter removed; the NULL-reachability trap is gone with it. Correct resolution. |
| **H-R3-3** | *"inert and swept"* is false — there is no sweeper | **NOT FIXED** | Re-verified on this branch: `_staging` appears in exactly three non-test files, all `putStaged` implementations (`supabase-blob-store.ts:85`, `local-blob-store.ts:53`, `in-memory-blob-store.ts:152`). No cron, no script, no `deletePrefix('_staging')` caller. §6:379 keeps the sentence **word for word**, and v4 made it load-bearing for *more* paths: `publish` now leaks the temp on every verify-throw as well as on every `PS003`. **H-R4-4.** |
| **H-R3-4** | The abort check does not cover the destructive window | **NOT FIXED** | §6:256 still checks `ctx.signal.aborted` only at the top of each attempt. The span `persist('committed') → publish → persist('promoted')` (§6:290-294) has no check, and v4 **lengthened** it — `publish` is now put + read-back + delete. **H-R4-5.** |
| **M-R3-1** | Two notions of "the address"; the guard uses the one the consumers don't prefer | **NOT FIXED** | The spec never mentions `artifacts.summaryMd.key` outside one §8:423 pointer assertion. Round 3 graded this Medium because I could not prove the two fields diverge. **They do — measured, 23 live rows.** Upgraded: **H-R4-2**. |
| **M-R3-2** | §8 mandates a `promoteSemantics` knob that no longer gates anything | **NOT FIXED** | §8:419-421 still requires *"Every re-address test runs with `promoteSemantics: 'create-if-absent'`"*. §6 calls `put`, not `promote`; `InMemoryBlobStore.promoteSemantics` gates only `promote`. The knob is inert. **M-R4-3.** |
| **M-R3-3** | Deploy stub analysed forward only (rollback / in-flight cost unstated) | **NOT FIXED** | §4:177-200 is unchanged on this point. Neither the rollback outage nor the in-flight post-Gemini failure is named. |
| **M-R3-4** | Coverage table of specified-but-untested behaviours | **PARTIALLY** | Two rows retired by the flag removal. The rest stand: no no-row test, no verify-after-publish/temp-deleted test, no two-worker test, no abort-mid-sequence test, no re-summarize-at-existing-base test, no contention test, no `summaryMd`-vs-`artifacts.key` assertion. |
| **M-R3-5** | G14 measured a shape v3 did not specify | **FIXED (by construction)** | v4 is back to 5-arg + **7**-arg with **no defaults** — exactly the pair G14 (§3:134) measured. §4:152 says so: *"Seven arguments, which is also the exact shape G14 was measured against."* The clean way to fix it. |
| **L-R3-1** | `baseOf` is adopted without validation | **NOT FIXED — annotated only** | §6:278 now reads `baseName := adoptBase(observedSummaryMd)   # VALIDATED — see below`. **There is no "below."** `grep -n "adoptBase\|validat" <spec>` returns exactly **one line** — that one. The word "VALIDATED" is doing the work a specification was supposed to do. **H-R4-1.** |
| **L-R3-2** | G13's path omits `lib/html-doc/` | **NOT FIXED** | §3:133 and §6:341 still cite `serve-summary-core.ts:50`. Cosmetic. |
| **L-R3-3** | `error.details` is a JSON *string*; parse failure undefined | **NOT FIXED — and now load-bearing** | §5:231 unchanged. v4 made attempt 2+ source **both** expected values from `PS003.detail` (§6:261), so a parse failure now poisons the serial as well as the key. **M-R4-6.** |

### Codex round 3

| # | Finding | Status | The v4 text |
|---|---|---|---|
| **C-B1** | `p_artifact_is_new` lets a stale/buggy caller disable the stale-caller defence | **PARTIALLY FIXED** | Flag removed. But Codex's own final sentence — *"If it continues, `publish()` overwrites `007_alpha.md` with stale bytes, then marks promoted"* — **is still true in v4**, because it never depended on the flag. **B-R4-2.** |
| **C-B2** | Same-key re-summarize at a new `docVersion` is also a new artifact; crash before publish freezes the mismatch | **NOT FIXED, AND NO LONGER NAMED** | v4 scopes the defect out as #22, but §6:366-371 and §9:467 both describe the residual as occurring *"on a re-address"*. Codex's case involves **no relocation at all** — it is the ordinary same-key re-summarize, the dominant re-run path. The scope-out text is narrower than the defect it scopes out. **H-R4-6.** |
| **C-B3** | `putStaged → verify staged → put final` does not verify the bytes that become final | **FIXED (mechanism)** | §6:322-331. Exactly the `tryGet`-style byte-compare Codex asked for — except it is spelled `get`. **B-R4-3.** |
| **C-B4** | `baseOf` adopts malformed keys (`""`, `nested/foo.md`, `raw/…`) instead of failing closed | **NOT FIXED** | Same single annotation as L-R3-1. Codex named the existing validator by file and line (`assert-cloud-summary-md-key.ts:14`); v4 cites neither. **H-R4-1.** |
| **C-H4** | No contention test for the new `FOR UPDATE` | **NOT FIXED — third consecutive round** | §5:242-245 still argues no deadlock (correct — re-verified a fourth time), and §8 still mandates no concurrent-session coverage. Raised r2, unfixed r3, unfixed r4. **M-R4-4.** |

**Summary of (A):** of 20 tracked findings, **6 genuinely fixed, 4 partially, 10 not fixed.** The
four partials all share one shape: v4 removed the ingredient the reviewer *named* and kept the
ingredient that did the damage.

---

## (B) Attacking v4's new design

### Blocking

#### B-R4-1 — the residual's load-bearing claim is false: the window is not bounded, and pre-slice behaviour on that path *self-heals*

§6:366-371 and backlog #22 both assert:

> *"**Bounded and non-destructive** — the bytes at that key are a valid summary throughout … and the
> following `'promoted'` persist reconciles the row. It is a staleness window, not corruption, and it
> is strictly smaller than the pre-slice behaviour it replaces."*

Every clause after the first is wrong. **Measured**, not inferred:

**Step 1 — the inheritance also carries the new run's scalars and `docVersion`.** The re-address
`'committed'` persist sends the adopted key (= the row's current key), so `0021:142-149`'s key-scoped
rule preserves `'promoted'`; simultaneously layer (3) at `0021:118-130` writes `docVersion`, `tldr`,
`ratings`, `takeaways`, `processedAt` from the payload. Measured against the live function's exact
CASE expression:

```
inherited_status=promoted | docVersion_after={"major": 4} | tldr_after=NEW RUN
```

So during the window the row advertises **`promoted` + the current doc version + the new run's
scalars**, while the bytes at the key are still A3's *old* copy. That is not "a valid summary" — it
is a coherent-looking record whose scalars and body come from different generations.

**Step 2 — that state satisfies the idempotency skip, so a fault inside the window is permanent.**
`summary-handler.ts:86-92` skips when `artifacts.summaryMd.status === 'promoted'` **and**
`docVersionKey(existing.docVersion) === job.version`. The `'committed'` persist has just made both
true. So:

| Fault point | Outcome under v4 |
|---|---|
| Crash / SIGTERM / lease loss after the `'committed'` persist, before `put` succeeds | retry → **skip** → job `done`. Row: `promoted`, new scalars, **A3's old body, forever**. The ~8¢ Gemini output is discarded and unrecoverable without manual repair. |
| `put` throws (network/5xx) | same |
| verify-after-write throws | same (though here the bytes did land, so the state is accidentally correct) |

**Step 3 — pre-slice, this exact fault is self-healing.** Today the stale worker writes the *old* key
`007_alpha.md` while the row's artifact key is `003_alpha.md`. The keys **differ**, so `0021:142-149`
does **not** preserve `promoted`; status becomes `committed` → `serve-summary-core.ts:50` returns
**503** → the retry does **not** skip → the job re-runs and repairs. v4 replaces a visible,
self-healing 503 with a silent, permanent, incoherent `promoted`. On this axis the residual is
strictly **larger** than what it replaces, not smaller.

This is precisely the failure §6:342-345 says it rejected v2's inversion for — *"replaced a visible,
non-serving crash window with a silent one … and the idempotency skip at `summary-handler.ts:86-92`
can freeze that state permanently."* v4 reintroduces it through the inheritance instead of through
the ordering. It is also the second v4 change composing badly with the first: the new
verify-after-write adds a **new throw** inside the window the inheritance made unrecoverable.

**Why Blocking:** the sentence is the entire justification for shipping #22 as a known defect. If it
is false, the scope-out decision was made on a false premise and has to be re-taken. It must be
fixed in **two** places — §6:366-371 and `docs/backlog.md` #22, which copies it verbatim.

**Fix directions** (either would restore boundedness, both are in-slice): (a) make the idempotency
skip require that the row's `mdGeneratedAt`/`mdCorrectionsHash` match a *published* blob, so an
inherited `promoted` cannot satisfy it; or (b) do not send `docVersion` on the `'committed'` persist
— send it only on the `'promoted'` one, which breaks the skip's second conjunct and restores
self-healing at the cost of one extra field write. (b) is a one-line change to the payload and needs
a mutation test.

---

#### B-R4-2 — removing the flag closed the status half; `publish = put` still makes a stale write destructive

Round 3's B-R3-2 had two ingredients. v4 removed one and closed the finding. Re-running the
interleaving with the flag gone:

| # | Actor | State / action under **v4** |
|---|---|---|
| 1 | W1 | reads `:84` → `(7,'007_alpha.md')`; Gemini; lease expires |
| 2 | W1 | attempt 1 top of loop: `ctx.signal.aborted` is **false** — heartbeat is every `leaseSeconds/3` = **40 s** (`worker-runner.ts:47-52`), so lease loss is detected up to 40 s late |
| 3 | W2 | (reclaimed the job) completes fully: row `(7,'007_alpha.md',promoted)`, blob = **W2's fresh bytes** |
| 4 | W1 | `putStaged` its own older bytes; verify staged ✅ |
| 5 | W1 | `persistSummary(expected := (7,'007_alpha.md'), 'committed')` → address **matches**, guard passes. Key unchanged → `0021:142-149` **preserves `promoted`**. ✅ *this is the half v4 fixed* |
| 6 | W1 | `publish` = **`put`** → **overwrites W2's fresh bytes with W1's older ones** |
| 7 | W1 | read-back returns W1's own bytes → **verify passes** — the new check confirms the destruction succeeded |
| 8 | W1 | `persistSummary(expected := (7,'007_alpha.md'), 'promoted')` → passes. Row + blob = W1's stale generation. **No error anywhere.** |

Today the same interleaving is non-corrupting: `SupabaseBlobStore.promote` is create-if-absent
(`supabase-blob-store.ts:94-97` — destination exists ⇒ delete temp, return **void**), so W2's bytes
survive. G12 says this in the spec's own ground-truth table, framed only as a *hazard*. It is also a
**defence**, and v4 removes it without noticing.

`summary-handler.ts:166-170` records the property this breaks, in prose, in the file the slice
edits:

> *"Full lease-fencing of `persist_summary` is deferred — **after FIX 1/FIX 2 a stale write is
> idempotent and non-corrupting**."*

v4 falsifies that comment and neither updates it nor names the regression. The address guard
structurally cannot see this case — the address never moved — which is exactly why the *bytes* need
their own condition.

**Why Blocking, not "out of scope":** §2 scopes *in* "a worker summary persist landing against a row
whose address changed." This is a write the slice **introduces** on a path it does not guard, on the
money path, against paid output. A slice may leave a defect unfixed; it may not create one silently.

**Fix.** Either (a) make `publish` conditional — read-before-write and refuse when the destination
holds bytes that are neither the staged bytes nor the pre-publish observation, using the
already-classified `CopyResult`/`destination-exists` vocabulary (`blob-store.ts:25-31`) rather than
bare `put`; or (b) accept it explicitly, update `summary-handler.ts:166-170`, and file it — but note
(a) costs one `tryGet`, which the verify step already pays for. §8 needs the two-worker test round 3
asked for and round 4 still does not have.

---

#### B-R4-3 — the new verify-after-write reads with `get`, which this repo forbids on exactly this decision

§6:325-331:

```
publish(ref, key):
    put(key, stagedBytes)
    readBack := get(key)
    if readBack is null or mdHash(readBack) != mdHash(stagedBytes):
        throw
```

`SupabaseBlobStore.get` (`supabase-blob-store.ts:27-37`) **swallows every failure into `null`** —
network, 5xx, timeout, RLS denial — and the adapter self-declares `provesAbsence = false`
(`:10`). The `BlobStore` contract states the rule in as many words (`blob-store.ts:46-56`):

> *"**Use this instead of `get` before any irreversible or billable decision.** Treating an
> unreadable read as 'absent' is the defect class that produced a Blocking and three Highs in the
> Stage 3 cloud-sync review, and a live double-charge on the serve path … 6¢ → 12¢."*

And `copyBlob` — the precedent §6:333-337 cites **by name and by line** — is documented at
`blob-store.ts:125` as reading *"exclusively through `tryGet` — never `exists()` or `get()`."* v4
imports the *idea* of copyBlob's verify and drops the property that makes it sound.

**Consequence, per path:**

| Path | A transient 5xx on the read-back causes |
|---|---|
| First-time summary | throw → row stays `'committed'` → 503 → retry → **fresh ~8¢ Gemini run**. Two workers or a flaky bucket can burn `max_attempts` = 5 (G11) → ≈40¢ → `dead_letter` with the row parked at `committed`, i.e. **permanent 503** for a video whose bytes are actually fine. |
| Re-address | throw lands inside B-R4-1's frozen window |

This is a fresh instance of *absent-vs-failed conflation* — a shape §11:528-531 carries in the
spec's own standing list — introduced by the fix under review, on the money path. That is the
definition of what the re-review loop exists to catch.

**Fix.** `readBack := tryGet(key)`; `{ok:false, reason:'absent'}` after a successful `put` is a real
fault (throw); `{ok:false, reason:'unreadable'}` is **not** proof of anything and must not discard a
successful write — retry the read, or proceed and let the next attempt's guard adjudicate. Say which,
in the spec. And byte-compare (`bytes.equals`) as `copyBlob` does rather than hashing (L-R4-2).

---

### High

#### H-R4-1 — `adoptBase` says "VALIDATED" and never specifies the validation

§6:278 is the only occurrence of `adoptBase` in the document, and the only occurrence of any form of
"validate":

```
      baseName := adoptBase(observedSummaryMd)                 # VALIDATED — see below
```

There is no "below." The nearest text is §6:383-384 — *"`baseOf` should be shared … extract it"* —
which is about deduplication, not validation. An unspecified validation on a money path is not a
fix; it is a note to the implementer that a decision remains to be made, in a document whose purpose
is to have made it.

**The validator already exists and the dig path already runs it on this exact value.**
`assertCloudSummaryMdKey` (`lib/html-doc/assert-cloud-summary-md-key.ts:14`) allowlists
`/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` — a **single path component**. `resolveSummaryMdKey`
(`lib/dig/cloud/resolve-summary-key.ts:16`) runs it and returns `null` on failure; `dig-handler.ts:55`
derives its base from that. The serve path runs it too and returns **409** on failure
(`serve-summary-core.ts:60-64`).

**Measured, live:** 11 of 2902 rows hold `summaryMd = 'artifacts/v/summary.md'` — a nested key that
validator **rejects**. Adopting it unvalidated means the worker writes ~8¢ of Gemini output to
`artifacts/v/summary.md`, the persist stamps `promoted`, and every reader then refuses it: serve
returns 409 *"corrupt summary key"*, `resolveSummaryMdKey` returns `null`, and the dig handler throws
`NonRetryableError('summary not available for dig')`. A promoted, paid, permanently unservable
artifact — reached through the guard, with the guard passing.

(Provenance, stated honestly: this is the dev/integration database. I traced no *production* writer
that emits a nested `summaryMd`. But it is the same database the spec cites as ground truth for G1's
*"154 of 2902 rows lack it"* — it is authoritative for both counts or for neither.)

**Fix.** Specify it: adopt through `assertCloudSummaryMdKey`; a rejection is `PS002`-class (fatal,
`NonRetryableError`, repair needed), **not** an address to write to and **not** a fallback to
re-deriving from the payload — re-deriving would silently relocate the artifact the guard exists to
protect. §8 needs one row per bad shape (`''`, `'nested/foo.md'`, `'no-extension'`).

---

#### H-R4-2 — the guard conditions on `data->>'summaryMd'`; both consumers prefer `artifacts.summaryMd.key`, and 23 live rows disagree

§5:215 selects `v.data->>'summaryMd'`; §6:277 adopts from it. But:

```ts
// lib/dig/cloud/resolve-summary-key.ts:14
const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
// lib/html-doc/serve-summary-core.ts:56
const mdKey = artifact?.key ?? (video as …).summaryMd;
```

Both the serve path and the dig path — the two consumers whose paid content this slice exists to
protect — prefer the **artifact record's** key. The spec conditions on the other one, never says
which is authoritative, and never asserts they agree. Round 3 graded this Medium because I could not
show a row where they differ. **Measured on this branch:**

```
data->>'summaryMd' | artifacts.summaryMd.key    | status   | count
<null>             | a.md                       | promoted |    12
<null>             | summaries/vidAAAAAAAA.md   | promoted |    11
```

23 rows carry a **promoted artifact key with a NULL top-level `summaryMd`**. On such a row:

1. `readVideo` (`worker-persistence.ts:32-39`, unchecked `data.data as Video`) yields
   `summaryMd: undefined` → `observedSummaryMd = null`.
2. The guard compares `NULL is distinct from NULL` — **measured `false`** → the guard **passes**.
3. §6:279-280's `else` branch fires — labelled *"first summary only (G2)"* — and mints a brand-new
   base `pad(serial) + '_' + slug(title)`.
4. The persist writes `summaryMd` = the new key and, via `0021:137`'s
   `coalesce(p_video->>'summaryMd', …)`, moves `artifacts.summaryMd.key` to it as well.
5. The previously-promoted artifact at `a.md`, and every dig under `dig/a/`, is **orphaned** — by the
   guarded write, with the guard reporting success.

The `else` branch's comment asserts a bare row (G2). `summaryMd is null` does **not** imply "no
promoted artifact"; it implies "no *top-level* pointer." That is the same absent-vs-unreadable shape
one field over.

(Same provenance caveat as H-R4-1: I traced no production writer that produces this shape —
`transferClassA` (`sync-run.ts:397-431`) and `copyAdditiveVideo` (`sync-run.ts:280-283`) both write
the two fields together, and `persist_summary`'s `jsonb_strip_nulls` cannot produce it. Graded High
rather than Blocking for that reason. The *asymmetry* — guarding one field while every consumer reads
the other — is a defect independent of whether these particular rows are fixtures.)

**Fix.** Either add a G-fact enumerating every writer of the pair and asserting they move together
(then assert it in §8 after every persist), **or** make the second conjunct compare
`coalesce(v.data->'artifacts'->'summaryMd'->>'key', v.data->>'summaryMd')` — the same resolution
order the consumers use. Per the standing rule *"at fix time, list the consumers,"* this is the grep
that still has not been run.

---

#### H-R4-3 — the slice adds a seventh hand-rolled commit→promote, against a recorded architecture-review direction it never mentions

`lib/storage/supabase/consistency.ts` implements `writeArtifact` — *"putStaged → verify temp exists →
updateVideoFields(committed) → promote → updateVideoFields(promoted)"* — with **zero production
callers** and 8 tests. The 2026-07-30 architecture review makes it finding #2, *"The commit→promote
protocol has no owner"*, and adjudicates the deletion test explicitly (`:238-247`): *"the module is
the right shape and the callers are wrong."* Its fix direction is stated at `:628-630`:

> *"Fix direction: route W1/W2 through `writeArtifact` (this finding), or make `promote()` uniform
> across adapters. **Do not fix it a second time at a single call site** — that is what
> `sync-run.ts:322` already did, and it is why the other writers never learned."*

v4 fixes it a **third** time at a single call site. It even *observes* the consequence — §6:335-337
notes that `transferClassA` copied the mechanism without the verify and calls that *"a defect …
worth its own entry"* — and then does the same thing again rather than fixing the seam. `grep` for
`writeArtifact`, `tryGet`, `CopyResult`, `assertCloudSummaryMdKey` across the spec returns **zero
hits**.

Phase 6 of `docs/dev-process.md` requires marking a candidate that contradicts a recorded decision
rather than silently proposing it. §7's migration table would also shrink: "publish semantics" would
become "unchanged, because it lives at the seam."

**Fix.** One paragraph in §6 or §7 either adopting the seam (extend `writeArtifact` to take a
`publish` strategy, route the summary handler through it, and the `transferClassA` gap closes for
free) or recording why this slice deliberately does not — with the architecture review cited, so the
next reviewer does not re-derive it.

---

#### H-R4-4 — *"A leaked staging object is inert and swept"* is still false, and v4 leaks on more paths

§6:379 retains the sentence verbatim. Re-verified on `717eecf`: `_staging` occurs in exactly three
non-test files, all of them `putStaged` implementations. There is no sweeper, no cron, no script.

v4 makes it worse in two ways. `publish` now deletes the temp **only on the success path**
(§6:331) — so every verify-throw leaks a permanent object holding a full summary body. And §6:296's
`on PS003 -> discard temp` is still the word "discard", not a `delete`, with no stated behaviour when
the delete fails. With N = 3 and `max_attempts` = 5, one pathological video leaks up to 15 permanent
objects in a bucket the user pays for and nothing enumerates. `deletePrefix` exists
(`supabase-blob-store.ts:110`) and would do the job — this is a missing line, not a missing
capability, but the spec asserts the line already exists.

**Fix.** Delete the claim. Specify `delete(tempKey)` on every abandonment path (`PS003`, verify
failure, abort, exhaustion), say what a failed delete does, and add the §8 assertion *"the temp is
gone after a successful publish."*

---

#### H-R4-5 — the abort check still does not cover the destructive window, which v4 lengthened

§6:256 checks `ctx.signal.aborted` at the top of each attempt only. The destructive span is now
`persist('committed')` → `put` → `get` → `delete` → `persist('promoted')` — **five** network
round-trips with no check, and it is steps 5-8 of B-R4-2's table. Today's code places a check
*immediately* before the write sequence for exactly this reason (`summary-handler.ts:170`, *"Shrink
the stale-worker write window"*); v4's loop moves that check further from the write by inserting
`putStaged` + verify after it, and then adds two more round-trips inside the span.

The measured window is not hypothetical: the heartbeat fires every `leaseSeconds/3` = **40 s**
(`worker-runner.ts:47-52`), so a worker runs up to 40 s past lease loss with `ctx.signal.aborted`
still `false`.

**Fix.** Re-check immediately before the `'committed'` persist **and** immediately before `publish` —
the latter is the irreversible one. §8:446's *"abort honoured on every attempt"* is satisfied by the
current text and would not catch this; it needs to read *"abort honoured immediately before each of
the three write steps."*

---

#### H-R4-6 — #22's scope-out is narrower than the defect it scopes out

§6:366-371 and §9:467 both frame the residual as occurring *"on a re-address."* Codex round-3
Blocking #2 described the same freeze on a path with **no relocation at all**:

- Row: `serialNumber 7`, `summaryMd '007_alpha.md'`, `promoted`, old `docVersion`.
- Worker re-summarizes at a new doc version, same title, same key.
- `'committed'` persist: key unchanged → `0021:142-149` preserves `promoted`; layer (3) writes the
  new `docVersion` and scalars.
- Fault before `publish` → retry → **idempotency skip fires** → frozen: current-version scalars over
  the old blob, permanently.

That is the *dominant* re-run path — every doc-version bump on every already-summarized video — and
it needs neither sync nor a second writer. It is pre-existing (v4 does not regress it), which is why
this is High rather than Blocking. But #22 is now the only record of it, and #22's text says
"re-address", so the broader case is neither fixed nor filed. A future reader will scope #22 to the
relocation path and miss it.

**Fix.** One sentence in §6 and in `docs/backlog.md` #22: the inheritance-plus-skip freeze occurs on
**any** same-key write whose payload advances `docVersion`, of which re-address is one instance.
Note this also makes B-R4-1's fix (b) — withhold `docVersion` until the `'promoted'` persist — close
both cases at once, which is a reason to prefer it.

---

### Medium

- **M-R4-1 — §8's 154-row test premise is unreachable.** §8:445-446 requires *"the `serialNumber`-absent
  row yields a clean non-retryable failure, not a retry storm (154 live rows)."* Those rows can never
  reach `persist_summary`: `reserve_video_slot` raises first — *"existing video %/% has no
  serialNumber (invariant)"* (`0009:90`) — at `summary-handler.ts:95`, **before** Gemini. That raise is
  a plain exception, classified retryable (`worker-runner.ts:76`), so the retry storm the test targets
  already happens **upstream of the classifier**, and `PS002`'s only reachable production trigger is a
  `serialNumber` erased between `:95` and the persist (G1's wholesale `upsertVideo`). Either retarget
  the test to that narrower trigger or state that PS002 is a defence-in-depth branch with no dominant
  live path — but do not cite 154 rows as its coverage.
- **M-R4-2 — `observedSerial` is not asserted non-null at capture.** `reserveVideoSlot` returns
  `data as number` (`worker-persistence.ts:13`), an unchecked cast. It is captured pre-Gemini at `:95`
  but first *used* as a guard input post-Gemini, so a null propagates into `p_expected_serial` → the
  `22004` raise **after billing**. §6 should require asserting it at capture time, where the failure is
  free. Same shape as B-R3-1, one step earlier.
- **M-R4-3 — the `promoteSemantics` knob still proves nothing** (M-R3-2 unfixed). §8:419-421 mandates
  it; §6 no longer calls `promote` on that path, and `InMemoryBlobStore.promoteSemantics` gates only
  `promote`. Replace with a spy asserting **no `promote` call** on the re-address path, so a future
  implementer reaching for `promote` goes red.
- **M-R4-4 — no contention test for `FOR UPDATE`, third round running** (Codex r2 H4, r3 H4). §5's
  no-deadlock argument is correct — re-derived a fourth time: `persist_summary` takes no `playlists`
  lock (`0021:104` is a bare `perform 1`), while `reserve_video_slot:84` and `claim_video_slot:50-52`
  take `playlists` first, so no transaction acquires `videos → playlists`. An argument is not a test.
  A finding that survives three rounds unaddressed should be either fixed or explicitly deferred with
  an owner — silence is the one disposition the loop does not allow.
- **M-R4-5 — §0/§9 still describe backlog #20 as live while §6 makes it unreachable** (H-R3-1
  unfixed). Under the unconditional adopt at §6:277, the worker can no longer move the base on a title
  change; §0:63-64 and §9:465 still say it does. Say which. §8 needs *"re-summarize with a changed
  title writes at the existing base"* — currently the **opposite** of `summary-handler.ts:96`, so it
  would otherwise ship as an unremarked behaviour change.
- **M-R4-6 — `PS003.detail` parse failure is undefined, and v4 made it load-bearing for both values.**
  Measured round 3: `error.details` arrives as a JSON **string**. §6:261 now sources *both* expected
  values from it, so a malformed or partial detail yields `undefined` → `?? null` → `22004` → retryable
  → storm. Specify: parse explicitly; a parse failure or a missing field is fatal
  (`NonRetryableError`), never "address unchanged" — that reading loops forever re-writing the same
  stale address.
- **M-R4-7 — §11 is stale.** It still reads *"rounds 1 and 2 complete, NOT converged. **Round 3
  mandatory**"* and *"Standing root-cause shapes — carry into **round 3**"*, on a v4 document under
  round-4 review. The standing-shapes list is the one artifact the process says measures the prompt;
  leaving it a round behind is not cosmetic.

### Low

- **L-R4-1** — §4:164's code block still shows only `p_expected_summary_md: expectedSummaryMd ?? null`.
  The `p_expected_serial` coercion lives in a §6 comment (`:272-274`). The two belong in one place, and
  §4 is it.
- **L-R4-2** — `mdHash` vs byte-compare. `mdHash` is `(md: string)` (`lib/cloud-sync/content-hash.ts:16`),
  so §6:328's `mdHash(readBack)` needs a `.toString('utf8')` on a Buffer. `copyBlob` uses
  `check.bytes.equals(src.bytes)` — no encode, no hash, strictly stronger. Prefer it.
- **L-R4-3** — the Blocking tally is stale. §7:405 and §11:533 both say *"six Blockings"* across
  *"two rounds"*; it is three rounds and, by the round-3 reviews' own count, nine before v4.
- **L-R4-4** — G13's path (§3:133, §6:341) still omits `lib/html-doc/` (L-R3-2).

---

## (C) Does an equivalent already exist in this repo, and is the spec's version worse?

The question that caught 3 of 4 Blockings last round. Full sweep of every mechanism v4 introduces:

| v4 mechanism | Existing equivalent | Verdict |
|---|---|---|
| `publish`: read back and compare after `put` | `copyBlob` (`blob-store.ts:155-172`) | **Worse** — reads with `get`, not `tryGet`. **B-R4-3** |
| `put` to a destination guaranteed to hold a paid artifact | `copy` + `CopyResult`'s `destination-exists` (`blob-store.ts:25-31, 42-44`) | **Worse** — v4 picks the one primitive with no outcome classification. **B-R4-2** |
| `adoptBase(observedSummaryMd)` | `assertCloudSummaryMdKey` (`assert-cloud-summary-md-key.ts:14`), run by `resolveSummaryMdKey` and by the serve path on this same value | **Worse** — asserts validation, specifies none. **H-R4-1** |
| stage → verify → commit → publish → promote | `writeArtifact` (`consistency.ts:17-42`), architecture-review finding #2 | **Worse** — a seventh hand-rolled copy, against a recorded "do not fix it at a single call site". **H-R4-3** |
| resolving "which key is this video's summary" | `resolveSummaryMdKey` (`artifacts.key ?? summaryMd`, validated) | **Worse** — the guard uses the un-preferred, unvalidated field. **H-R4-2** |
| `baseOf` | module-private `reconcile-serial.ts:84-86`; duplicated at `dig-handler.ts:55` | **Same, and §6:383 correctly says extract it.** ✅ |
| bounded retry with observed-state adoption | no equivalent | genuinely new ✅ |
| a required (not optional) probe parameter | `InFlightJobProbe` — *"REQUIRED, deliberately: an optional probe does not propagate"* (`reconcile-serial.ts:~215`) | **Same discipline, correctly applied** — §4 makes both new parameters required, non-defaulted. ✅ |
| named SQLSTATEs as the contract | `0023`'s `PJ00x` family | **Same.** ✅ |
| plan-before-mutate | `reconcile-serial.ts:262-280` | not applicable |

Five hits. The three from round 3 (`copyBlob`, `assert-cloud-summary-md-key`, `transferClassA`) are
each *cited* in v4 now — and two of them are cited while the property that makes them work is
dropped. Citing a precedent is not adopting it.

---

## Verified, not findings

Recorded because a checked-and-clean answer is worth as much as a finding.

- **The admitted torn read is genuinely correct and self-correcting.** I attacked it four ways and
  could not break it:
  1. *Relocation between t₀ (`:84`) and t₁ (`:95`)* → tuple `(3,'007_alpha.md')` vs row
     `(3,'003_alpha.md')` → `PS003` → attempt 2 uses one atomic snapshot → succeeds. **One attempt
     burned, never more**, because attempt 2's tuple is a single locked read.
  2. *Legitimate first-time write* → no row at t₀ ⇒ `observedSummaryMd = null`; `reserve_video_slot`
     creates the row; guard compares `NULL is not distinct from NULL` → passes. **Cannot be rejected.**
  3. *Row deleted and recreated between t₀ and t₁* (the `PermanentTranscriptError` rollback at
     `summary-handler.ts:132-134`, or a concurrent reclaim) → tuple `(newSerial, staleKey)` vs row
     `(newSerial, NULL)` → `PS003` → attempt 2 sees `null` → falls to the derive branch → correct.
     One attempt.
  4. *Exhausting all three attempts* requires something relocating on **every** attempt, which §6:376
     already names as a different bug.
  §6:263-270's *"correct and self-correcting … but it means attempt 1 can fail for a reason no single
  observed state explains"* is accurate, and admitting it rather than papering over it is the right
  call. **No interaction with G1's 154 rows** — those raise at `0009:90` before the loop is ever
  entered (which is M-R4-1, a test-scoping issue, not a torn-read issue).
- **The 7-argument shape now matches G14 exactly.** Removing `p_artifact_is_new` retired M-R3-5 by
  construction rather than by re-measurement — the cleanest possible disposition.
- **No deadlock from the new `FOR UPDATE`** — re-derived independently for the fourth time.
  `persist_summary` takes no `playlists` lock (`0021:104`); `reserve_video_slot:84` and
  `claim_video_slot:50-52` take `playlists` first. No cycle.
- **The `committed → publish → promoted` ordering with its 503 window still holds** (H-N3). §6:339-345
  is right that inverting it trades a visible window for a silent one. B-R4-1 shows the *inheritance*
  reintroduces the silent window by another route — the ordering itself is sound.
- **A3 always leaves a valid body at the new key before advancing metadata.** Verified:
  `reconcile-serial.ts:281-290` copies (retaining sources), `:293-296` writes the patch, `:350-353`
  verifies, `:355-361` cleans up. So §6's premise that the destination "always exists" on a re-address
  is correct. Note `:296` forces `status: 'promoted'` unconditionally — which is what makes the
  inheritance in B-R4-1 fire every time, not occasionally.
- **`scripts/check-docs.py` passes** — *"Documentation integrity OK"*. §11's claim is true (round 3
  did not re-run it).
- **Backlog #22 exists with the §9 title and the full rationale** (`docs/backlog.md`, entry 22). It
  also copies the *"bounded and non-destructive … the bytes at that key are a valid summary
  throughout"* claim verbatim, so B-R4-1 must be fixed in both files.

---

## What I could not verify, and why

1. **A production writer for the `artifacts.key`-without-`summaryMd` shape** (H-R4-2). I traced
   `transferClassA`, `copyAdditiveVideo`, `persist_summary`, `reconcile_membership` and A3's patch —
   all write the pair together. The 23 rows exist in the dev database the spec itself cites as ground
   truth; I could not attribute them. Graded High, not Blocking, for that reason. The *asymmetry* it
   exposes stands regardless.
2. **That B-R4-2's two-worker interleaving occurs in production.** Every mechanism is established (the
   40 s heartbeat, 120 s lease reclaim, `sweepExpired`, no abort check inside the span), but I did not
   run two workers against one job. The finding does not depend on frequency: `summary-handler.ts:166-170`
   asserts non-corruption as a *property*, and v4 removes it.
3. **Wall-clock cost of the loop against the 120 s lease.** Structural argument only — same limitation
   as rounds 1-3. §8:454-456 names it as uncovered, which remains the honest disposition. Note v4
   *increased* the per-attempt cost (publish is now 3 round-trips, not 1), so the argument is now
   weaker than when it was written.
4. **Whether `put` on Supabase Storage is atomic under a concurrent reader.** Round 3 measured
   per-object last-write-wins with no intermediate observed; I did not re-measure, and it is not the
   property at risk in B-R4-2 (provenance is).
5. **Whether the 11 nested-key rows are reachable by a summary job today** (H-R4-1) — that needs a
   playlist/job join I did not construct.

---

## Standing root-cause shapes — hits this round

| Shape | Where it recurred, in **v4's own fixes** |
|---|---|
| *absent-vs-failed conflation* | **B-R4-3** (`get` for the new verify) — fourth occurrence in this slice, now inside the fix for the third |
| *a claim asserted rather than checked* | **B-R4-1** (*"bounded and non-destructive"*, measured false); **H-R4-4** (*"inert and swept"*, retained verbatim after being disproved) |
| *a guard with no covering test* | **B-R4-2** (still no two-worker test); **M-R4-4** (still no contention test, third round) |
| *a value read in one process and written in another* | **B-R4-2** — W1's expected address is a fact W2 has since replaced |
| *a fix applied at the call site instead of the seam* | **H-R4-3** — the architecture review named this exact anti-pattern and the spec repeats it |
| **new: *removing the ingredient the reviewer named, not the one that did the damage*** | **B-R4-2** (flag removed, `put` kept); **H-R4-6** (flag removed, freeze kept and un-named) |

**Round-5 shape to carry:** *v4's failures are no longer in the write sequence — they are in what the
spec says about itself.* Two of three Blockings are false claims (§6's residual, §6's sweep), and the
third is a correct mechanism spelled with the wrong primitive. Twelve Blockings across four rounds,
**still zero in the predicate**.
