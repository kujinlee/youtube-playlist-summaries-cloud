# Round 15 — coordinator adjudication

**Verdict: NOT CONVERGED.** 3 Blocking, 3 High, 6 Medium, 2 Low. Round 16 required.

Gate strength: **not downgraded.** Both reviewers executed `verify-schema.sh` against live Postgres
inside a rollback; Claude ran two additional structural probes (cascade depth, clamp arithmetic) in
throwaway schemas. Tree clean throughout. Codex reached `gpt-5.5` after three HTTP 400s.

**The core decision was not attacked this round and remains unbroken after three design reviews.**
Every finding is in a round-14 fix or in the split. That is the signature — *each round's fix causes
the next round's defect* — on its **third consecutive round**.

---

## The thing worth saying before the findings

**All three Blockings, and two of the three Highs, are reconciliation failures — not design errors.**

- **B1**: I struck out the render design in one section and left the implementer's instruction list
  mandating it in another.
- **B3**: I dropped a column without checking which surviving code writes it.
- **H1**: I rewrote a script and left the ADR quoting its old text at a line that now holds a newline.
- **H2**: I reworded one table row and not the row four lines below making the same claim.

Round 14's M4 named this exactly — *"the revision grew 339 lines in one pass with no pass reconciling
the new sections against each other"* — and prescribed the fix: *"before round 15, do one read whose
only question is: which two of these new sections constrain each other?"* **I did not do that read.**
Round 15 is largely the cost of skipping it.

The corollary matters for round 16: **more review rounds are not the remedy.** Three reviews have
failed to break the decision and keep finding the same class of clerical incoherence. The remedy is a
reconciliation pass, which is cheap, and which has now been prescribed twice.

**And the substitution error repeated a third time.** Round 13's B1: a true lemma about *writes* read
as a conclusion about *money*. Round 14's H3: a true rule about *spend* read as a conclusion about
*availability*. Round 15's H3: **the fix for that** states an availability-only bound for a clamp that
also moves money. Same shape, three rounds running, each time inside the fix for the previous one.

---

## BLOCKING

### B1 — the implementer's instruction list still mandates the withdrawn render design (both reviewers)

`video_artifacts_free_uq` now has **three fates in one document**: *stays* (`:296`), *replaced by
uniqueness on (…, `render_id`)* (`:330-333`), *neither* (`:352-357`). `:334-335` also specifies a
two-column `art_paid_has_generation` premised on the withdrawn column, and `:442` still opens
*"**Address** = `sha256(rendered bytes)` (previous section)"* — a pointer to a section the split
deleted.

**This is round 14's B1 exactly, reintroduced by the change meant to remove the refuted material.**
An implementer reading top-down hits *replaced* last before Consequences.

*Verified by me independently before either review landed.*

**Fix:** delete `:328-339` and `:440-443`; leave `video_artifacts_free_uq` exactly one statement, in
Consequences.

### B2 — the `model` GC-floor successor expires before the call it covers (both reviewers, MEASURED)

Round 14's B2 fix named the live `serve_model_charge` lease as `model`'s in-flight guarantee. The
lease is **180 s with no renewal**; the call it covers is bounded by
`GENERATE_JSON_RETRIES = 2` → **3 passes** × `REQUEST_TIMEOUT_MS = 60_000`
`[VERIFIED: lib/gemini-cost.ts:22]` `[VERIFIED: lib/gemini.ts:94]` = **180 000 ms**, plus 400 + 800 ms
backoff, plus an **untimed** `countTokens` preflight and an unbounded upload.

**181 200 ms > 180 000 ms before the untimed parts.** The worst case does not merely risk outliving
the lease — it exceeds it by construction. `grep -rn "renew" supabase/migrations/*.sql` → zero hits.

So the successor goes cold while the paid call runs, and the generation becomes collectable:
*"Money spent, bytes queued for deletion, no error anywhere."* Round 9's B1, on the one kind the fix
was written for. The ADR itself lists *"no renewal RPC, a 180 s TTL"* as why `model` is the worst kind
to leave uncovered — then designates that lease as the cover, **without ever comparing the TTL to the
call's duration.**

**Fix — the ADR must state the comparison it omits: the covering mechanism's lifetime ≥ the covered
operation's worst case.** Then either add a renewal RPC (this is the ADR's own revisit trigger firing
*now*), derive the TTL from `MAGAZINE_MAX_PASSES × REQUEST_TIMEOUT_MS + backoff + margin` and put a
timeout on `countTokens`, or give `model` a real in-flight marker the sweeper reads.

### B3 — dropping `source_generation_id` leaves the join table with no writer (Claude only — and Codex explicitly cleared it)

**Reviewers split, and I adjudicate for Claude after reading the SQL myself.** Codex listed the drop
under "could not break", having found no **TypeScript** consumer. Claude enumerated the **SQL**
consumers and found two that the ADR never mentions:

- `[VERIFIED: schema/04_artifacts.sql:470]` — `record_artifact` takes `p_source_generation_id`, and
  `:661-671` writes it with a `coalesce(p_source_generation_id, v_src)` carry-forward at `:663`.
  **`record_artifact` survives this ADR** (`:350`).
- `[VERIFIED: schema/04_artifacts.sql:969-973]` — the append-only trigger raises
  *"the PROVENANCE of a % paid row is immutable"* on any change to the column.

Drop the column, keep the RPC unchanged, and **`video_artifact_sources` is always empty** — at which
point *both* of the ADR's new guards go vacuously true: the ranking rung and the GC `not exists`.

**That is the identical failure the ADR diagnoses 100 lines earlier** for the GC floor — *"the
predicate goes vacuously true and the guard stops guarding without being deleted … a guard that never
started, arriving by subtraction."* Committed inside the fix set that names it.

Second consequence: provenance stops being append-only. The trigger branch has no analogue on the new
child table, which has `on delete cascade` on both FKs — in the ADR titled *"artifacts are an
append-only log."*

**Fix:** state that `record_artifact` writes the join rows in the same statement (and what re-record
does, since the carry-forward has no join-table analogue); move the trigger's provenance branch onto
`video_artifact_sources`; rewrite — not delete — the four assertions in `05_assert.sql`.

---

## HIGH

- **H1 — a `[VERIFIED:]` tag created by the split is wrong.** The ADR quotes the sentinel entry's old
  trigger and tags `check-sentinel-meanings.py:90`; that line now holds a bare newline, and the quoted
  string no longer exists anywhere in the file — **the same commit rewrote it**. In the paragraph
  whose subject is *"deleting it would be the gate laundering an unfixed defect."*
- **H2 — the concern table still claims "exclusivity" for `model`**, one row after that word was
  removed from `jobs` for being unsupportable. B2 supplies the measurement: `reserve_serve_model`'s
  reclaim clause admits a second producer the moment the lease expires, which B2 proves happens
  mid-call. It is a **bounded single-flight window**, exactly like the heartbeat. This propagates to
  falsifier #2, which tests for the breach of a guarantee the table no longer claims.
- **H3 — the clamp is a money change carrying an availability-only bound.** `least(sum, K-1)` applies
  to **every** row, not only merged ones. Verified: `least(5,4) = 4`, so a single-playlist document
  that legitimately exhausted all 5 attempts is rewritten to 4 and **gets a new paid Gemini attempt**.
  `least(1,0) = 0` fully resets an exhausted document. My honest-bound paragraph omits exactly the
  already-exhausted subset the clamp changes. **Fix:** apply the clamp only where a merge occurs
  (`count(*) > 1`), which also makes the migration re-runnable — an idempotency question the ADR never
  addresses.

## MEDIUM

**M1 — the `model` successor is outside BOTH executable gates.** `verify-schema.sh` and
`mutate-schema.py` read only the spec `schema/` dir; `serve_model_charge` lives in
`supabase/migrations/`. So the one successor row that is not staged-write ordering can never be
asserted or mutation-scored. **Same blind spot the ADR self-indicts one section away** for
`check-vocabulary-collisions.py` — and unnoticed there.
· **M2** `on delete cascade` makes an orphaned render vacuously current (MEASURED); no caller reaches
it today, so the invariant it rests on must be written down.
· **M3** the rewritten ranking rung leaves "current" undefined for non-summary sources — the exact
multi-source case that motivated the join table.
· **M4** `[VERIFIED: 0012:3]` cites "no **release** RPC" to support "no **renewal** RPC" — different
mechanism, and the cited claim is now false anyway (`settle_serve_model` is a release RPC). The
renewal claim is true; the citation resolves without supporting.
· **M5** the surviving partition claim names `render_id`, a column that exists in no schema and whose
home is now the brief.
· **M6** (coordinator) Codex's L1: `check-sentinel-meanings.py:52-53` still reads *"ADR-0007 removes
this"* — a second stale spot I missed when editing the other block. **Verified.**

## LOW

**L1** the causal account of round-14 B3 is the wrong lemma — MEASURED, the break is caused by the
join table sitting **one hop deeper**, not by `RESTRICT` as such; a one-hop `NO ACTION` child survives
while a two-hop one fails. The fix is right, the stated reason invites an obvious objection the ADR
cannot answer.
· **L2** `:517` says two producers *"do not double-append"*, but under the ADR's own central claim two
producers with different generation ids append two rows **by design**; the mechanism provides
merge-safety, not non-appending.

## What round 15 could NOT break — do not re-run

- **The split is not lossy** — every carved-out piece landed in the brief; B1 is the reverse problem.
- **The headline is still honest** — `model`/`serve_model_charge` is named in the first ten lines, so
  no reader reaches the concern table without meeting the exception.
- **`check-docs.py`'s index tightening is a genuine fix**, not laundering (both reviewers).
- **The sentinel rewrite is correct in substance**; only its ADR citation is wrong (H1).
- **The `restrict → cascade` change opens no GC window** (Codex) — collection is an
  `update body_collected`, not a generation delete.
- **`settle_serve_model` cannot be turned into a double-refund** (Claude).
- **The `doc_key` re-key coupling stands as written**, and ~20 other `[VERIFIED:]` tags spot-check
  clean.

---

## Recommendation for round 16 — and it is not another review round

Three design reviews have failed to break the decision and keep returning the same class of clerical
incoherence. **The prescribed remedy already exists and has now been skipped once**: round 14's M4
asked for a pass whose only question is *"which two sections constrain each other?"*

So: fix B1/B2/B3/H1/H2/H3 and the Mediums, **then run the reconciliation pass before round 16**, and
let round 16 verify only the fixes. B2 is the one genuine design question left — it needs a decision
(renewal RPC vs derived TTL vs a real in-flight marker), not an edit.
