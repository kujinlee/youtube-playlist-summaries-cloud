# Whole-branch review #46 — COORDINATOR findings, round 1

Written BEFORE reading either reviewer's output, so it is an independent third data point rather
than an echo. `docs/review-method.md`: *"Each gate re-derives ONE inherited assumption — chosen
because this gate has information the earlier one lacked."*

**The assumption I chose to re-derive:** `lib/serve-budget.ts` states that every constant in
`SERVE_BOUNDED_MS` except `SERVE_MARGIN_MS` corresponds to a timeout the code ACTUALLY APPLIES, and
that their sum bounds the serve path's work. The spec graded a violation of this Blocking once
already (a `SETTLE_SLACK_MS` that appeared in the sum and nowhere else). The plan gate could not
check it, because at plan time no code existed to apply anything.

---

## C-1 (Medium) — the settle is counted ONCE and can run TWICE; the sum survives only by an unstated coincidence

**Claim.** `SERVE_BOUNDED_MS` adds `SERVE_SETTLE_RPC_TIMEOUT_MS` exactly once
`[VERIFIED: lib/serve-budget.ts:62-68]`, but `settleBounded` runs up to **two** attempts of that
timeout on the release path:

```
lib/html-doc/serve-doc.ts:168     const attempts = released ? 2 : 1;
lib/html-doc/serve-doc.ts:169-175 for (let i = 0; i < attempts; i++) { ... SERVE_SETTLE_RPC_TIMEOUT_MS ... }
```
`[VERIFIED: lib/html-doc/serve-doc.ts:168-175]`

The retry was added in Task 6. The sum was computed in Task 1, before the retry existed, and was
never revisited.

**Why it is NOT Blocking — the arithmetic, worked.**

| path | reserve | countTokens | 2 × attempt | backoff | put | settle | total |
|---|---|---|---|---|---|---|---|
| keep (success)   | 5 000 | 10 000 | 100 000 | 400 | 15 000 | 1 × 5 000 | **135 400** |
| release (refund) | 5 000 | 10 000 | 100 000 | 400 |      — | 2 × 5 000 | **125 400** |

`SERVE_BOUNDED_MS = 135_400`. Both paths fit. The second settle is paid for out of the put's 15 s,
which the release path never spends — the generation failed, so there is nothing to upload.

**What actually holds it up.** The two paths are mutually exclusive, and that exclusion is enforced
by two independent mechanisms, NEITHER of which is mentioned in `lib/serve-budget.ts`:

1. **The billing latch.** `if (opts?.billing) opts.billing.metered = true;` fires the moment the
   response body is received, before parsing `[VERIFIED: lib/gemini.ts:274]`. So any failure at or
   after the put has `metered === true`, and `released` is
   `... && !billing.metered` `[VERIFIED: lib/html-doc/serve-doc.ts:130-132]` → `false` → 1 attempt.
2. **The classifier.** A put timeout raises a `DOMException` named `TimeoutError`
   `[VERIFIED: lib/html-doc/model-store.ts:76]`, which matches none of `classifyGeminiFailure`'s
   release branches; its own doc comment says *"everything else (timeout, non-lease abort, 500/502/504,
   stripped connection, post-return) → keep"* `[VERIFIED: lib/gemini-failure.ts:70-84]`.

**What caller reaches the bad state?** *None today* — which is exactly why this is Medium and not
Blocking, per the method's *"a defect with no reachable caller is a fact about expressiveness, not
about the system."* But the bound is one edit away from being wrong: make any post-generation
failure refundable (relax the latch, or add a status to `RELEASE_STATUSES` that can arrive after the
body), and the worst case becomes **140 400 > 135 400**. The lease floor then silently stops
covering the work — silently, because `SERVE_FLOOR_SECONDS` is a build-time constant that no test
compares against a measured worst case.

**Proposed fix (cheap, and it is the method's own preference — turn a deferred finding into an
assertion rather than a note):**

1. Document the exclusion where the money is spent, in `lib/serve-budget.ts`, naming both
   mechanisms and both `file:line`s. The file's whole thesis is *"every term is a timeout the code
   applies"*; a term that is applied twice on a path the sum does not model is precisely the
   ambiguity it was written to remove.
2. Add a unit assertion that the RELEASE path's worst case also fits `SERVE_BOUNDED_MS` — i.e. that
   `reserve + countTokens + attempts·attempt + backoff + 2·settle <= SERVE_BOUNDED_MS`. It is one
   line in `tests/lib/serve-budget.test.ts`, it goes red the day someone raises the settle timeout
   or adds a third attempt, and it costs nothing.
3. Optionally assert the invariant directly: a post-put failure must not be refundable. That is the
   *decision* being relied on, and per the method a decision defended only by the scenario that
   prompted it is the shape that has broken here before.

**Shape.** This is standing shape #7 — *a rule preserved verbatim that stopped working because the
mechanism carrying it changed* — caught one step before it bit. The rule ("the sum bounds the work")
still reads true; the mechanism under it (a single settle) changed in a different task.

---

## Guard classification for this branch (method Step 4)

One guard is added to the database by this diff:

| guard | kind | verdict |
|---|---|---|
| `guardrail_config_lease_ttl_covers_serve` (`supabase/migrations/0024_lease_covers_serve.sql`) | **SHAPE** | correct as a rejecter |

*Asks:* is this configuration value well-formed? *A violation means:* the caller — an operator or a
migration writing config — is wrong. *Therefore:* reject. There is no "who got here first" question
here; a second writer setting a valid value simply succeeds, and no money has been spent by the time
the CHECK fires. A SEQUENCE reconciliation is not owed.

Verified NOT to be part of `scripts/check-guard-coverage.py`'s population (that script inventories
the blob-addressing `schema/` tables): its finding list is byte-identical with and without
migration 0024.
