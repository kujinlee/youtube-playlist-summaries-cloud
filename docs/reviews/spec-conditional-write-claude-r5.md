# Claude adversarial review — `2026-08-04-cas-fence-persist-summary-design.md` (round 5)

**Reviewer:** Claude (adversarial mandate)
**Branch:** `docs/cas-fence-spec` @ `435794a` (commit titled v5; the document's own Status line still
says v4 — see M-R5-5)
**Date:** 2026-08-05
**Method:** every v5 citation re-read on this branch. The load-bearing new mechanism — the
`docVersion` split — was **measured against the live `persist_summary`** in
`supabase_db_youtube-playlist-summaries-cloud` (transaction, rolled back), not inferred from the
migration text. Live row census re-run. Every consumer of `docVersion` enumerated by grep and read.

---

## Verdict

**NOT CONVERGED.** Two Blocking, six High.

The round-5 shape carried in from round 4 was *"v4's failures are no longer in the write sequence —
they are in what the spec says about itself."* That is still the shape, and it now has a sharper
form: **v5 fixes round 4's findings by naming the right mechanism and then specifying it in a way the
named mechanism cannot deliver.** Three of the eight findings below are of that exact kind —
`tryGet` adopted and its answer discarded (B-R5-2), `assertCloudSummaryMdKey` adopted and called with
the wrong signature and the wrong failure class (H-R5-1), `copyBlob`'s verify adopted and weakened to
a normalizing hash (H-R5-2).

And the headline: **the `docVersion` split works exactly as v5 claims against the one consumer v5
looked at, and is defeated by the second writer v5 did not look at.** Measured both halves.

Credit where it is due, and it is substantial — v5 genuinely closed B-R4-1's mechanism (measured),
B-R4-3's primitive choice (partially), H-R4-5's abort placement, M-R4-3, M-R4-4, and — unremarked by
the spec — H-R4-6/Codex C-B2, which the `docVersion` split closes for free.

---

## (A) Round-4 findings — genuinely fixed, or reworded?

### Claude round 4

| # | Finding | Status | The v5 text, and whether behaviour changes |
|---|---|---|---|
| **B-R4-1** | The residual's boundedness claim is measured false | **FIXED (mechanism) / NOT FIXED (argument)** | §6:289-293 splits the payload (`committedPayload := video WITHOUT docVersion`); §6:311-324 and §6:408-427 rewrite the residual on the new premise. **I measured the mechanism and it works**: after a `'committed'` persist with no `docVersion` key, `0021`'s layer (2) `\|\| (v.data - 'artifacts')` wins it back, so the row keeps `{"major":2,"minor":1}` while `tldr` advances to `NEW RUN` — the skip's second conjunct is genuinely broken. **But the argument is one consumer wide.** §6:311-324 names `summary-handler.ts:86-92` and nothing else. `docVersion` is read or written by six other modules, one of which re-arms the skip. **B-R5-1.** |
| **B-R4-2** | `publish = put` still makes a stale same-address write destructive | **NOT FIXED — converted into a test instruction** | §8:487-490 asks for a two-worker test and then says *"state the outcome the slice accepts."* The spec does not state it. `publish` is still bare `put` (§6:352); `CopyResult`/`destination-exists` still has **zero** occurrences in the document; `summary-handler.ts:166-170`'s *"a stale write is idempotent and non-corrupting"* is still falsified and still unmentioned. **H-R5-6.** |
| **B-R4-3** | The verify reads with `get` | **FIXED IN LETTER, INERT IN EFFECT** | §6:353 is now `tryGet`, and §6:361-366 argues the case well. But §6:355 and §6:357 take the **identical action** (`throw RETRYABLE`) on `unreadable` and on `absent`/mismatch. The distinction `tryGet` exists to expose changes no behaviour, so the money consequence `blob-store.ts:46-56` cites (6¢→12¢ on a transient blip) is unchanged. Round 4 asked *"say which — retry the read, or proceed"*; v5 answered by not distinguishing. **B-R5-2.** |
| **H-R4-1** | `adoptBase` says "VALIDATED" and specifies nothing | **PARTIALLY** | §6:278-284 now names `assertCloudSummaryMdKey` by file, states fail-closed, and assigns `PS002` → `NonRetryableError`. Real progress. But the function **returns `void` and throws** (`assert-cloud-summary-md-key.ts:16-20`), and §6:282 calls it as a boolean predicate (`if not assertCloudSummaryMdKey(...)`). As written the throw escapes before the branch, is a plain `Error` with `statusCode: 409`, and `worker-runner.ts:76` classifies it **retryable**. **H-R5-1.** |
| **H-R4-2** | Guard conditions on `data->>'summaryMd'`; both consumers prefer `artifacts.summaryMd.key`; 23 live rows diverge | **NOT FIXED — zero new text** | §5:215 still selects `v.data->>'summaryMd'`; §6:277 still adopts from it. `grep -n artifacts <spec>` returns **two** lines (446, 476), neither about the guard. **Re-measured live this round: 12 rows `<null> \| a.md \| promoted` + 11 rows `<null> \| summaries/vidAAAAAAAA.md \| promoted` = 23.** Third round raised, third round unaddressed. **H-R5-4.** |
| **H-R4-4** | *"inert and swept"* is false; v4 leaks on more paths | **PARTIALLY — and the false sentence is still in the document** | §6:368-374 is a good new paragraph: verified false, `_staging` in exactly three files, up to 15 leaked objects. **But §6:435 still reads, verbatim, *"A leaked staging object is inert and swept."*** The spec now contains the claim and its refutation 60 lines apart. And the pseudocode does not implement the new paragraph: §6:302's abort check and §6:355/357's two `publish` throws delete nothing. **H-R5-3.** |
| **H-R4-5** | Abort does not cover the destructive window | **FIXED** | §6:298 (`discard temp; throw AbortError`, immediately before the irreversible span, mirroring `summary-handler.ts:170`) and §6:302 (between `'committed'` and `publish`). Matches the fix direction. (The §6:302 check leaks its temp — that is H-R5-3, not this.) |
| **H-R4-6** | #22's scope-out is narrower than the defect | **SUBSTANTIVELY FIXED, TEXTUALLY NOT** | The `docVersion` split closes Codex C-B2's no-relocation case too: a same-key re-summarize at a new `docVersion` now leaves the row's **old** `docVersion` during the window, so the retry does not skip. Measured. But §6:408 and §9:539 still both say *"on a re-address"*, and §6:402 still describes the broader case only as an argument against a removed parameter. The fix is real and the record of it is wrong. **M-R5-4.** |
| **M-R4-1** | §8's 154-row premise is unreachable (`0009:90` raises first) | **NOT FIXED** | §8:517 unchanged. |
| **M-R4-2** | `observedSerial` not asserted non-null at capture | **NOT FIXED** | §6:272-274 mandates the `?? null` coercion; nothing asserts non-null at `:95`, so a null still reaches `p_expected_serial` and raises `22004` **after** billing. |
| **M-R4-3** | `promoteSemantics` knob is inert | **FIXED** | §8:477-479 drops it explicitly and says why: *"the requirement is inert and is dropped rather than left as decoration."* Correct disposition. |
| **M-R4-4** | No contention test for `FOR UPDATE` (3rd round) | **FIXED** | §8:492-495 adds it, and names the argument-vs-test distinction. Fourth-round ask, finally satisfied. |
| **M-R4-5 / H-R3-1** | The adopt rule silently changes re-summarize addressing; contradicts §0 + #20 | **NOT FIXED — zero new text** | §6:277 still adopts unconditionally whenever `observedSummaryMd` is non-null. §0:63-64 still says *"Unguarded, deliberately: a re-summarize that moves the key itself after a title change… That is backlog #20"*; §9:537 still files #20 as open. Under §6 the worker can no longer move the base, so `summary-handler.ts:96`'s behaviour changes and nothing says so. **M-R5-1.** |
| **M-R4-6** | `PS003.detail` parse failure undefined, now load-bearing for both values | **NOT FIXED** | §5:231 and §6:307 unchanged. |
| **M-R4-7** | §11 is stale | **NOT FIXED — and worse** | §11:596 still *"rounds 1 and 2 complete… **Round 3 mandatory**"*; §11:599 still *"carry into **round 3**"*. The **Status line itself (§:3-4) still says "v4 … round 4 pending"** on a document whose commit message is v5, and the review trail (:6-13) omits round 4 entirely. **M-R5-5.** |
| **L-R4-1** | §4's code block shows only the key coercion | **NOT FIXED** | §4:164 unchanged. |
| **L-R4-2** | `mdHash` vs `bytes.equals` | **NOT FIXED — and it is a type error** | §6:356 is `mdHash(readBack.bytes) != mdHash(stagedBytes)`. `mdHash` is `(md: string)` (`content-hash.ts:16`) and calls `md.replace()`; a `Buffer` has no `.replace`. Upgraded — **H-R5-2**. |
| **L-R4-3** | Blocking tally stale | **NOT FIXED** | §7:460 still *"Two rounds have now produced six Blockings"* — it is four rounds and 21. |
| **L-R4-4** | G13's path omits `lib/html-doc/` | **NOT FIXED** | §3:133 unchanged. |

### Codex round 4

| # | Finding | Status | The v5 text |
|---|---|---|---|
| **C-B1** | `adoptBase` validation unspecified; should be fail-closed `PS002` | **PARTIALLY** | Named and classified (§6:278-284); called with the wrong signature and inheriting the wrong error class. **H-R5-1.** |
| **C-B2** | publish mismatch handling under-specified; can freeze row/body mismatch; use `tryGet` | **NOT FIXED, AND THE NEW TEXT ASSERTS THE OPPOSITE** | `tryGet` adopted (§6:353). But §6:357's recovery claim — *"do NOT persist `'promoted'`; the row stays `'committed'` → 503 → repair"* — is **false on the re-address path**, by v5's own §6:408-410: the `'committed'` persist inherited `'promoted'`, so the serve path returns **200** over whatever bytes are at the key. Codex's "different valid summary" case is still unanswered. **B-R5-2.** |
| **C-H1** | *"swept"* still claimed; up to 15 leaked objects | **PARTIALLY** — §6:368-374 concedes it; §6:435 still asserts it; the pseudocode still leaks on three paths. **H-R5-3.** |
| **C-H2** | Abort only at attempt top | **FIXED** — §6:298, §6:302. |
| **C-H3** | No concurrent-session test (3rd round) | **FIXED** — §8:492-495. |
| **C-"existing mechanisms"** | `copyBlob` shape, `assertCloudSummaryMdKey`, `transferClassA`'s missing verify | **PARTIALLY** — all three now cited; two are cited while the property that makes them work is dropped (H-R5-1, H-R5-2). `writeArtifact`: **zero occurrences**. **H-R5-5.** |

**Summary of (A):** of 22 tracked findings — **6 fixed, 6 partially, 10 not fixed.** The dominant
shape has shifted from round 4's *"removed the ingredient the reviewer named, not the one that did
the damage"* to **"adopted the mechanism the reviewer named, and dropped the property that made it
work."**

---

## (B) Attacking v5's new design

### Blocking

#### B-R5-1 — the `docVersion` split is argued against one consumer of a field six modules touch, and the second writer re-arms the skip it was introduced to break

**First, the half that works — measured, not inferred.** Against live `persist_summary`
(`0021:95-155`), a `'committed'` persist whose payload omits `docVersion`:

```
label                            | docversion               | tldr    | processedat          | art_status
A: committed WITHOUT docVersion  | {"major": 2, "minor": 1} | NEW RUN | 2026-08-05T12:00:00Z | promoted
B: committed WITH docVersion     | {"major": 3, "minor": 3} |         |                      | promoted
```

Layer (3)'s `jsonb_strip_nulls` drops the absent key, so layer (2) `|| (v.data - 'artifacts')` wins
the **old** value back. Row A's `docVersionKey({2,1}) = "2.1"` ≠ `job.version = "3.3"`, so
`summary-handler.ts:86-92`'s second conjunct is false and the retry does **not** skip. §6:320's claim
is true. Row B reproduces v4's freeze. **The split does what §6 says it does.**

**Now the half v5 did not look at.** §6:311-324 is the entire boundedness argument and it names
exactly one reader: `summary-handler.ts:86-92`. `docVersion` is read or written by six other places:

| Module | What it does with `docVersion` |
|---|---|
| `lib/cloud-sync/sync-run.ts:400` | **`transferClassA` WRITES it**, in the same `updateVideoFields` as `artifacts: { summaryMd: { key, status: 'promoted' } }` (`:429`) |
| `lib/cloud-sync/backfill.ts:12` | `deriveClassASignals` → `docVersionMajor: video.docVersion?.major ?? 1` |
| `lib/cloud-sync/reconcile-class-a.ts:34,43-45` | the *never-downgrade-format* tie-break |
| `lib/html-doc/ensure.ts:34,66` | reads it, and **writes `docVersion: current`** after a render |
| `lib/html-doc/eligibility.ts:12` | `summaryNeedsWork` |
| `components/VideoMenu.tsx:148` | the "current" badge |

**The freeze returns through `transferClassA`.** Sequence, every step verified in code:

| # | Actor | State |
|---|---|---|
| 1 | worker | `'committed'` persist without `docVersion` → row: `docVersion` **2.1 (stale)**, `tldr` new, `processedAt` now, `artifacts.summaryMd.status` **promoted** (inherited, key unchanged). *Measured above.* |
| 2 | sync | a run overlaps. `reconcileClassA` (`sync-run.ts:768`) has **no in-flight-job probe** — `deps.inFlightJob` is wired only into `reconcileCloudBase` at `sync-run.ts:732`. Nothing defers a Class-A transfer for an active job. |
| 3 | sync | cloud row has no `mdCorrectionsHash` (the worker never writes one), so `cCur = false`; a locally-generated row has `mdCorrectionsHash: mdHash('')` (`pipeline.ts:272`), so `lCur = true` → `reconcile-class-a.ts:39` returns **`copyToCloud`** immediately. **Live: 2227 of 2488 summary-bearing rows lack `mdCorrectionsHash`.** |
| 4 | sync | `transferClassA(local → cloud)`: `put`s local's body over the key (**destroying the freshly published paid bytes if publish already landed** — that part is backlog #19), then `updateVideoFields` writes `docVersion: wv.docVersion` **and** `artifacts.summaryMd.status: 'promoted'` (`sync-run.ts:400,429`) through `merge_video_data`. Local's `docVersion` is `CURRENT_DOC_VERSION` = `{3,3}` for anything the local pipeline produced (`pipeline.ts:267`). |
| 5 | worker | any fault in the window (crash, SIGTERM, lease loss, a failing `put`, **or either of `publish`'s own new `throw RETRYABLE` branches**) |
| 6 | worker (retry) | reads the row: `status === 'promoted'` ✓ **and** `docVersionKey({3,3}) === "3.3" === job.version` ✓ → **the idempotency skip fires** → job returns `done`. Row keeps the scalars of a Gemini run whose output was never published. Permanent. |

That is B-R4-1's freeze, reached by a different writer, on the same money path, in the same sync run
this spec exists to race. **§8:481-485's mutation test cannot detect it** — it restores `docVersion`
to the worker's *own* `'committed'` payload, so it only ever exercises step 1. A second writer
stamping the field is structurally invisible to it, and §8 has no test in which a sync runs during
the window at all.

**A second, independent consequence — the split flips a sync tie-break backwards.** When both sides
are corrections-stale (so `reconcile-class-a.ts:39-40` does not fire), the decision falls to
`:43-45`, comparing `docVersionMajor`. During the window the cloud row reports the **old** major
while `deriveClassASignals` reports a **fresh** `mdGeneratedAt` (it falls back to `processedAt`
(`backfill.ts:14`), which the `'committed'` persist *does* advance — measured above):

- **v5:** cloud major 2 vs local major 3 → `winnerIsCloud = 2 > 3` = false → **`copyToCloud`** → local's older body overwrites the new one.
- **v4:** cloud major 3 = local major 3 → falls to `:49` recency → cloud's `mdGeneratedAt` is *now* → **`copyToLocal`** → cloud wins, correct.

**Live reachability: 185 promoted rows sit at major 1 or 2 against `CURRENT_DOC_VERSION = {3,3}`** —
exactly the population a re-summarize job targets, and exactly where the withheld field is the one
that decides.

**Why Blocking.** §6:311-324 and §9 #22 rest the entire scope-out on this one field, for the second
round running, and for the second round running the claim is made about a state without enumerating
who else observes it. The standing rule is explicit — *"At fix time, list the consumers. Before a fix
that changes what state means, name every reader — including the same code in a different process.
`grep` for the field name is usually the job."* That grep returns seven files. The spec names one.

**Fix directions.** (a) Make the skip's **first** conjunct honest instead of sabotaging a second
field — the row already has a purpose-built "this artifact is not final" channel in
`artifacts.summaryMd.status`, and the defect is that the key-scoped rule at `0021:142-149` *lies*
about it on a re-address. Fixing the liar is in-slice; corrupting an unrelated field to route around
it is what created B-R5-1. (b) If the split is kept: enumerate all seven consumers in a G-fact, state
that `docVersion` now means *"the last **promoted** generation"*, and give §8 a test in which a sync
`copyToCloud` lands inside the window and the retry still does not skip. (c) Note that the
in-flight-job probe is wired into A3 but not into the Class-A transfer — that asymmetry is worth a
line either way.

---

#### B-R5-2 — `publish()`'s failure handling: `tryGet`'s answer is discarded, and the stated recovery is false on the one path the slice exists for

§6:348-359:

```
publish(ref, key):
    put(key, stagedBytes)
    readBack := tryGet(key)                     # tryGet, NOT get — see below (B-R4-3)
    if readBack is 'unreadable':
        throw   RETRYABLE      # a fault, not a verdict: we do NOT know what is at the key
    if readBack is 'absent' or mdHash(readBack.bytes) != mdHash(stagedBytes):
        throw   RETRYABLE      # do NOT persist 'promoted'; the row stays 'committed' → 503 → repair
    delete(ref.tempKey)
```

**Two defects, both in text written this round.**

**(i) The distinction is introduced and then not used.** Both branches `throw RETRYABLE`. The
observable behaviour is byte-identical to v4's `get`. `blob-store.ts:46-56` does not say *"name the
outcomes"*; it says *"Treating an unreadable read as 'absent' is the defect class that produced …
a live double-charge on the serve path … 6¢ → 12¢."* The charge is the point. Here: `put` has
**already succeeded**, so on a transient 5xx read-back the bytes are at the key and correct — and v5
throws retryable, the row is not promoted, and the retry pays **~8¢ for a fresh Gemini run** for a
write that worked. Up to `max_attempts` = 5 ≈ 40¢ → `dead_letter`, row parked, permanent 503 on a
video whose bytes are fine. That is the identical money shape `tryGet` exists to prevent, and
round 4's fix direction asked in as many words which action each branch takes. Round 5's answer is
"the same one".

**(ii) `"the row stays 'committed' → 503 → repair"` is false on the re-address path.** v5 says so
itself 50 lines later, at §6:408-410: *"On a re-address the intermediate `'committed'` write inherits
the prior `'promoted'` status for the duration of one publish, so a reader in that window is served
the older copy rather than a 503."* Measured above: `art_status = promoted` after a
`'committed'` persist at an unchanged key. So on the path this whole slice exists to guard, a publish
verify failure leaves a **`promoted`** row (`serve-summary-core.ts:50` → **200**, not 503), whose
scalars are the new run's and whose bytes are whatever survived — and the recovery sentence points
the implementer at a 503 that will not happen. This is Codex round-4 Blocking 2, restated and
answered with its own false premise; it is also the third consecutive round in which a confidently
worded recovery claim in §6 turns out to be measurably wrong.

**Fix.** State the two actions separately and truthfully. `absent` after a successful `put` is a real
fault → fatal or retry-the-write, say which. `unreadable` is not proof of anything and must not
discard a successful write — retry the read (bounded), or proceed and let the next attempt's guard
adjudicate. Mismatch is Codex's *"a different valid summary"* case and still needs an answer, which
`copyBlob`'s `destination-exists` vocabulary already supplies. And whatever the branch does, correct
the recovery sentence: on a re-address the row is `promoted`, not `committed`.

---

### High

#### H-R5-1 — `assertCloudSummaryMdKey` returns `void` and throws; §6 calls it as a predicate and claims it yields `PS002`

§6:278-284:

```
      if not assertCloudSummaryMdKey(observedSummaryMd):
          raise PS002 (serial-unusable / address-unusable) -> NonRetryableError   # repair-needed
```

`lib/html-doc/assert-cloud-summary-md-key.ts:16-20`:

```ts
export function assertCloudSummaryMdKey(mdKey: string): void {
  if (typeof mdKey !== 'string' || !CLOUD_SUMMARY_MD_KEY.test(mdKey)) {
    throw Object.assign(new Error(`invalid cloud summary md key: ${mdKey}`), { statusCode: 409 });
  }
}
```

It returns `undefined` on success and **throws** on failure — the `if` is never reached on the path
it is written for. The consequence is not cosmetic: the thrown value is a plain `Error` carrying a
`statusCode: 409` shaped for the HTTP serve path, **not** a `NonRetryableError`. `worker-runner.ts:76`
classifies it **retryable**, so a row with a bad key burns `max_attempts` = 5 Gemini runs (≈40¢)
before `dead_letter` — which is precisely the retry storm §5:204-210 says the classifier exists to
prevent, and precisely the outcome §6:283's `-> NonRetryableError` annotation promises to avoid.

**Live:** 11 rows hold `summaryMd = 'summaries/vidAAAAAAAA.md'` — nested, rejected by that regex.

**Fix.** Specify the call as a try/catch that re-raises as the `PS002` class (or add a
`isCloudSummaryMdKey(): boolean` companion and use it), and say explicitly that the 409-shaped error
must not reach the runner unwrapped. §8 needs the three bad-shape rows round 4 asked for (`''`,
`'nested/foo.md'`, `'no-extension'`) asserting `NonRetryableError`, not just "fails".

#### H-R5-2 — the publish verify uses `mdHash` on a `Buffer`: a type error, and deliberately weaker than the precedent it cites

§6:356: `mdHash(readBack.bytes) != mdHash(stagedBytes)`.

`content-hash.ts:16` is `mdHash(md: string)` and delegates to `canonicalizeMd(md)`, whose first line
is `md.replace(/\r\n?/g, '\n')`. A `Buffer` has no `.replace` — as written this is a runtime
`TypeError` inside the publish path, after billing.

Worse than the type: `canonicalizeMd` **normalizes** — LF line endings, exactly one trailing newline,
Unicode NFC. It is built for *cross-backend* comparison, where that is correct. Used as a
verify-after-write it means the check **cannot detect** a corruption that differs only in line
endings, trailing whitespace, or Unicode normalization form. `copyBlob` — the precedent §6:375-379
cites by name and line — uses `check.bytes.equals(src.bytes)` (`blob-store.ts:167-171`): no encode,
no normalization, strictly stronger, and free. Round 4 raised this as L-R4-2 with the fix spelled
out; v5 kept the weaker one.

**Fix.** `readBack.bytes.equals(stagedBytes)`.

#### H-R5-3 — "every discard path deletes its own temp" is asserted, contradicted in the same section, and not implemented by the pseudocode

§6:368-374 is correct and well-evidenced: no sweeper exists, `_staging` appears in exactly three
`putStaged` implementations, up to 15 leaked objects per job. **Then §6:435 says, verbatim and
unchanged from v3 and v4:**

> **Cleanup.** A leaked staging object is inert and swept.

The document now asserts the claim and its refutation 60 lines apart, in the same section. An
implementer reading §6's Cleanup paragraph — which is where you look for cleanup — gets the false
one. Round 3 disproved this sentence; round 4 reported it retained verbatim; round 5 reports it
retained verbatim again.

The pseudocode does not implement the new paragraph either. Deletion appears on three paths
(§6:298 abort, §6:307 `PS003`, §6:308 `PS001`/`PS002`) and is **absent** from three:

- §6:302 — the second abort check (`throw AbortError`, no temp handling)
- §6:355 — `publish`'s `unreadable` throw
- §6:357 — `publish`'s `absent`/mismatch throw

§6:358's `delete(ref.tempKey)` is inside `publish`, reachable only on success. Note also that §6:298
says *"discard temp"* while §6:307-308 say *"DELETE temp explicitly"* — round 4 flagged "discard" as
the vague word; it survives.

**Fix.** Delete §6:435's first sentence. Add the delete to all three paths (and to loop exhaustion,
§6:431). Say what a failed delete does. §8 needs *"the temp is gone after a successful publish"* and
*"the temp is gone after a publish verify failure."*

#### H-R5-4 — the guard still conditions on `summaryMd` while both consumers prefer `artifacts.summaryMd.key`; 23 divergent rows re-measured, zero v5 text

Re-measured on this branch:

```
data->>'summaryMd' | artifacts.summaryMd.key  | status   | count
<null>             | a.md                     | promoted |    12
<null>             | summaries/vidAAAAAAAA.md | promoted |    11
```

`resolve-summary-key.ts:14` (`artifacts?.summaryMd?.key ?? summaryMd`) and
`serve-summary-core.ts:56` (`artifact?.key ?? …summaryMd`) both prefer the artifact record. §5:215
guards the other field; §6:277-286 adopts from the other field; §6:286's `else` branch is annotated
*"first summary only (G2)"* — which reads `summaryMd is null` as "no artifact", when it means "no
*top-level pointer*". On such a row the guard passes (`NULL is distinct from NULL` → false), the
`else` branch mints a fresh base, and the previously-promoted artifact plus every dig under it is
orphaned **by the guarded write, with the guard reporting success**.

Raised Medium in round 3, upgraded to High with measurements in round 4, **zero** responsive text in
v5. Same provenance caveat as round 4 (I could not attribute the rows to a production writer, and the
count is on the dev database the spec cites for G1's 154/2902) — the *asymmetry* is a defect
regardless of those rows.

**Fix (unchanged from round 4).** Either a G-fact enumerating every writer of the pair and asserting
they move together, plus a §8 assertion after every persist; or make the second conjunct
`coalesce(v.data->'artifacts'->'summaryMd'->>'key', v.data->>'summaryMd')`, matching the consumers'
resolution order.

#### H-R5-5 — the seventh hand-rolled commit→promote, still against a recorded architecture decision the spec never mentions

`grep -n "writeArtifact\|CopyResult" <spec>` → **zero hits**, unchanged from round 4.

`lib/storage/supabase/consistency.ts` implements this exact protocol with zero production callers and
8 tests. The 2026-07-30 architecture review makes it finding #2 and adjudicates the deletion test
(*"the module is the right shape and the callers are wrong"*), with the fix direction: *"Do not fix
it a second time at a single call site — that is what `sync-run.ts:322` already did, and it is why
the other writers never learned."* v5 fixes it a third time at a single call site — and §6:375-379
now *observes* the consequence in print (`transferClassA` copied the mechanism without the verify,
*"a defect worth its own entry"*) without connecting it to the seam.

`docs/dev-process.md` Phase 6 requires **marking** a candidate that contradicts a recorded decision
rather than silently proposing it. One paragraph either adopting the seam or recording why not, with
the review cited, satisfies this. It is the cheapest open finding in the document and it is now three
rounds old.

#### H-R5-6 — the two-worker semantics are delegated to the test author

§8:487-490:

> *"`publish = put` overwrites unconditionally, so a worker whose address never moved can still
> overwrite a concurrent worker's paid bytes — the guard cannot see it, because nothing moved.
> **Assert what actually happens** with two workers racing the same key, **and state the outcome the
> slice accepts.**"*

The paragraph states the defect correctly and then hands the decision to whoever writes the test.
Nowhere does the document say what the correct outcome *is*. That is the one thing a design spec has
to do, and the prompt for this round asked the question directly: **what IS the correct outcome when
two workers legitimately hold the same address?**

The repo already answers it for the neighbouring case. `BlobStore.copy`'s contract
(`blob-store.ts:38-44`): *"Never overwrites: a destination holding different bytes is
`destination-exists`, and the caller decides."* And `CopyResult.already: true` exists precisely so a
proven-byte-identical destination is a **success**, not a conflict — `blob-store.ts:20-24` explains
that without it *"a fail-closed `destination-exists` would deadlock every retry."* Applied here that
gives a complete, non-arbitrary rule with no new vocabulary:

- destination absent → `put`, verify, proceed;
- destination byte-identical to staged → the other worker produced the same artifact → proceed (this
  is the ordinary retry-after-crash case, and must not fail);
- destination holds **different** bytes → someone else's paid output → refuse, do not `put`, do not
  persist `'promoted'`; classify and let the guard's next attempt adjudicate.

Note this also retires B-R4-2 as a live defect rather than as a test to be written, and it is one
extra `tryGet` on a path that already pays for one.

Separately: `summary-handler.ts:166-170` records *"after FIX 1/FIX 2 a stale write is idempotent and
**non-corrupting**"* — a property `publish = put` falsifies. v5 neither updates that comment nor
names the regression. A slice may leave a defect unfixed; a spec should not leave a comment in the
file it edits asserting the opposite of what it ships.

### Medium

- **M-R5-1 — §0/§9 still describe backlog #20 as live while §6 makes it unreachable** (H-R3-1 →
  M-R4-5, third round unfixed). §6:277's adopt is unconditional, so the worker can no longer move the
  base on a title change; §0:63-64 and §9:537 still say it does. §8 needs *"re-summarize with a
  changed title writes at the existing base"* — currently the opposite of `summary-handler.ts:96`,
  so it would otherwise ship as an unremarked behaviour change.
- **M-R5-2 — `PS003.detail` parse failure still undefined** (M-R4-6). §5:231 / §6:307 unchanged;
  attempt 2+ sources **both** expected values from it, so a malformed detail yields `undefined` →
  `?? null` → `22004` → retryable → storm.
- **M-R5-3 — `observedSerial` still not asserted non-null at capture** (M-R4-2). `reserveVideoSlot`
  returns `data as number` (`worker-persistence.ts:13`), an unchecked cast, captured pre-Gemini and
  first used post-Gemini. The failure is free at capture and costs a billed run where it currently
  lands.
- **M-R5-4 — the record of what the `docVersion` split fixes is narrower than the fix.** The split
  closes Codex C-B2 / H-R4-6 (same-key re-summarize at a new `docVersion`, no relocation) — the
  dominant re-run path. §6:408 and §9:539 still frame everything as *"on a re-address"*. One sentence
  in each, and #22 stops under-claiming.
- **M-R5-5 — the document's own metadata is a round behind, again.** Status line (:3-4) says *"v4 …
  round 4 pending"* on the v5 commit; the review trail (:6-13) omits round 4 entirely; §7:460 says
  *"Two rounds … six Blockings"* (four rounds, 21); §11:596 says *"rounds 1 and 2 complete … Round 3
  mandatory"*; §11:599 carries the standing shapes *"into round 3"*. The standing-shapes list is the
  one artifact the process says measures the prompt (`docs/dev-process.md` → *"Convergence measures
  the prompt too"*); two rounds stale, it measures nothing.
- **M-R5-6 — §8's 154-row premise still unreachable** (M-R4-1). `0009:90` raises at
  `summary-handler.ts:95`, before Gemini and before the classifier.

### Low

- **L-R5-1** — §4:164 still shows only the `p_expected_summary_md` coercion; the `p_expected_serial`
  one lives in a §6 comment (L-R4-1).
- **L-R5-2** — §3:133 / §6:341 still cite `serve-summary-core.ts:50` without `lib/html-doc/`
  (L-R4-4, L-R3-2 — third round).
- **L-R5-3** — §6:435's *"The `publish`-then-rejected branch leaks differently"* now describes a
  branch §6 no longer has (there is no publish-then-reject; the reject is inside `publish`). Stale
  with the sentence in front of it.

---

## (C) Does an equivalent already exist in this repo, and is v5's worse?

Full sweep of the mechanisms **new in v5**.

| v5 mechanism | Existing equivalent | Verdict |
|---|---|---|
| Withhold `docVersion` to signal "this artifact is not final yet" | `artifacts.summaryMd.status` (`0021:137-149`) — a purpose-built, key-scoped, monotonic field that means exactly that | **Worse.** v5 adds a second, informal, undocumented "not final" channel on a field with six other consumers, instead of fixing the one whose key-scoped rule is the actual liar. **B-R5-1** |
| `publish` reads back with `tryGet` | `copyBlob` (`blob-store.ts:155-172`) — `tryGet`, then **acts differently** per reason (`source-absent` vs `source-unreadable` vs `failed/phase`) | **Worse.** The primitive is adopted; the classification is not — both branches throw the same thing. **B-R5-2** |
| `mdHash(readBack.bytes) != mdHash(stagedBytes)` | `check.bytes.equals(src.bytes)` (`blob-store.ts:167-171`) | **Worse** — and a type error. Normalizing hash hides CRLF/NFC/trailing-newline corruption. **H-R5-2** |
| `if not assertCloudSummaryMdKey(k)` | `assertCloudSummaryMdKey` itself (`assert-cloud-summary-md-key.ts:16`), used correctly by `resolveSummaryMdKey:16` and `serve-summary-core.ts:60` | **Worse** — right function, wrong signature, wrong error class. **H-R5-1** |
| explicit `delete(tempKey)` on discard | `transferClassA`'s `.catch(() => {})` best-effort delete (`sync-run.ts:391`) | **Better where specified** (explicit, on named paths) — but not applied to three of the six paths, and the false "swept" sentence survives. **H-R5-3** |
| "two workers on one key" as a test requirement | `CopyResult` — `destination-exists` + `already: true` (`blob-store.ts:20-31, 38-44`) is a complete, already-adjudicated answer to this exact question | **Worse** — the repo has the semantics; v5 asks the test author to invent them. **H-R5-6** |
| abort immediately before the irreversible span | `summary-handler.ts:170` (*"Shrink the stale-worker write window"*) | **Same discipline, correctly applied.** ✅ |
| concurrent-session test for `FOR UPDATE` | none | genuinely new, correctly added ✅ |
| dropping the inert `promoteSemantics` requirement | — | correct disposition ✅ |

**Seven of eight new mechanisms have an existing equivalent. Five are worse.** The pattern is now
stable across three rounds and worth stating plainly: this spec reliably *finds* the right precedent
and reliably drops the property that makes it work. A round-6 prompt should ask, for every citation
in the document, *"is the cited property actually preserved in what §6 specifies?"* — that single
question would have caught B-R5-2, H-R5-1 and H-R5-2 before they were written.

---

## Verified, not findings

Recorded because a checked-and-clean answer is worth as much as a finding.

- **The `docVersion` split's core mechanism works.** Measured against live `persist_summary`, not
  inferred: an omitted `docVersion` is dropped by layer (3)'s `jsonb_strip_nulls` and the old value
  is won back by layer (2), so the skip's second conjunct is genuinely false during the window. The
  contrast case (payload *with* `docVersion`) reproduces v4's freeze exactly. §6:320 is true as far
  as it goes; B-R5-1 is about how far that is.
- **It also closes H-R4-6 / Codex C-B2 for free** — the same-key re-summarize at a new `docVersion`,
  which needs no relocation and no second writer. v5 does not claim this; it should.
- **The abort placement (H-R4-5) is right.** §6:298 mirrors `summary-handler.ts:170`, and §6:302
  covers the non-atomic span. I could not construct a fault between them that the two checks miss.
- **The contention test (M-R4-4 / Codex H4, four rounds) is finally specified** — §8:492-495, and it
  correctly separates the argument from the test rather than re-arguing.
- **`promoteSemantics` was dropped rather than left as decoration** (§8:477-479). The right way to
  retire an inert requirement.
- **No deadlock from the new `FOR UPDATE`** — re-derived a fifth time, still sound. `persist_summary`
  takes no `playlists` lock (`0021:104` is a bare `perform 1`); `reserve_video_slot:84` and
  `claim_video_slot:50-52` take `playlists` first. No cycle.
- **The admitted torn read (§6:263-274) still holds.** I re-ran round 4's four attacks against v5's
  text; the `docVersion` split does not touch the tuple, and attempt 2's single locked snapshot still
  self-corrects. No new interaction.
- **The 7-argument shape still matches G14 exactly**, and the deploy stub's parameter-name
  preservation (G15) is unchanged and correct.
- **`scripts/check-docs.py`** — re-run, *"Documentation integrity OK"*. §11's claim holds (it is the
  only claim in §11 that does).

---

## What I could not verify, and why

1. **That a sync `copyToCloud` actually lands inside a live worker's publish window** (B-R5-1,
   step 4). Every mechanism is established in code and measured — no in-flight probe on the Class-A
   path (`sync-run.ts:732` vs `:768`), `transferClassA` writes `docVersion` + `status:'promoted'`
   together (`:400, :429`), the currency ladder sends 2227/2488 rows to `copyToCloud`
   (`reconcile-class-a.ts:39`), local rows carry `CURRENT_DOC_VERSION` (`pipeline.ts:267`) — but I
   did not run a sync concurrently with a worker. The finding does not depend on frequency: it is the
   premise of a scope-out decision, and a premise that holds "usually" is not a premise.
2. **Whether `ensureHtmlDoc` can write `docVersion` to a cloud row.** It is reached only through
   `app/api/videos/[id]/html-doc/route.ts` and uses `getStorageBundle()` (`resolve.ts:51`), which
   returns the Supabase bundle only with an authenticated client. I did not trace whether that route
   is wired in cloud mode. Listed as a `docVersion` writer in B-R5-1's table for completeness; the
   Blocking does not rest on it — `transferClassA` alone is sufficient.
3. **A production writer for the 23 `artifacts.key`-without-`summaryMd` rows** (H-R5-4). Same as
   round 4: `transferClassA`, `copyAdditiveVideo`, `persist_summary` and A3's patch all write the
   pair together. Unattributed, on the same database the spec cites as ground truth for G1.
4. **Wall-clock cost of the loop against the 120 s lease.** Structural argument only, rounds 1-5.
   §8:526-528 names it as uncovered, which remains honest.
5. **Whether the 11 nested-key rows are reachable by a summary job today** (H-R5-1) — needs a
   playlist/job join I did not construct. The signature/classification defect stands regardless of
   how many rows can reach it.

---

## Standing root-cause shapes — hits this round

| Shape | Where it recurred, in **v5's own fixes** |
|---|---|
| *a value read in one process and written in another* | **B-R5-1** — the boundedness argument names one reader of a field `transferClassA` writes in the racing process |
| *a claim asserted rather than checked* | **B-R5-2** (*"the row stays `'committed'` → 503"*, false by v5's own §6:408); **H-R5-3** (*"inert and swept"*, retained a third time) |
| *a guard with no covering test* | **B-R5-1** (the mutation test cannot see a second writer); **H-R5-6** (still no two-worker semantics to test) |
| *absent-vs-failed conflation* | **B-R5-2** — `tryGet` adopted, both outcomes given the same action. Fifth occurrence in this slice, now *inside* the fix for the fourth |
| *a fix applied at the call site instead of the seam* | **H-R5-5** — third round, still unmarked |
| **new: *the precedent is cited and the property that makes it work is dropped*** | **B-R5-2** (`copyBlob`'s classification), **H-R5-1** (`assertCloudSummaryMdKey`'s signature + error class), **H-R5-2** (`bytes.equals` → normalizing hash) |

**Round-6 shape to carry:** for every mechanism the document cites by file and line, ask *"does §6
preserve the property that citation was for?"* Three of this round's eight findings are the answer
being no. **21 + 8 = 29 findings across five rounds, still zero in the predicate.**

---

## Everything I attacked and could not break

Listing this explicitly because the convergence gate requires it, and it has not been met.

- The predicate itself (`v_actual_serial <> to_jsonb(p_expected_serial) or v_actual_md is distinct
  from p_expected_summary_md`) — not re-checked per the round-5 mandate, and five rounds have found
  nothing in it.
- The torn read, re-attacked with v5's text: relocation between `:84` and `:95`; legitimate
  first-time write; row deleted and recreated; three-attempt exhaustion. All still self-correcting.
- The `docVersion` split against the idempotency skip **in isolation** — measured, works.
- The `FOR UPDATE` deadlock argument — fifth derivation, still no cycle.
- The `committed → publish → promoted` ordering and its 503 window — still the right trade against
  v2's inversion.
- The deploy stub, parameter-name preservation, grants, and the 7-arg/5-arg coexistence — unchanged
  from v4 and still correct.
- Attempt-2's single-snapshot recovery under repeated relocation — terminates, and exhaustion is
  correctly characterised as a different bug.
- Whether the abort checks at §6:298 and §6:302 leave an uncovered gap — they do not.

The findings above are all in the protocol, the payload, the publish path, the failure
classification, and the test list. None is in the predicate.
