# Adversarial review — append-only roadmap + M1 plan v2 (round 2, Claude half)

**Reviewer:** Claude, independent of the Codex half of round 2 (not read).
**Reviewed at:** `83663ff` (`docs(plan): v2 — the stamp becomes conditional, because promote often
publishes nothing`), tree clean apart from the untracked round-2 prompt.
**Date:** 2026-08-22.

**Counts: 1 Blocking, 3 High, 4 Medium, 6 Low.**

Round 1's own reviews (`plan-append-only-m1-r1-claude.md`, `plan-append-only-m1-r1-codex.md`) were
read first. The round-1 Claude half was written by a different instance; I disagree with one of its
findings below (H6, which v2 dissolves correctly) and extend another (B1's suggested fix, which v2
adopted and which I now believe is incomplete rather than wrong).

---

## What I executed

| Command | Result |
|---|---|
| `npm test` | **268 suites / 2,722 tests, all passing, 33.6 s.** ✅ reproduces the roadmap's figure exactly |
| `wc -l …/schema/*.sql` | 4 files, **4,108** lines. ✅ reproduces |
| `ls -1 supabase/migrations/*.sql \| tail -1` | `0025_settle_is_observable.sql`. ✅ reproduces |
| `grep -rli "generation_id" --exclude-dir=node_modules --exclude-dir=docs .` | **2 files**, both ratchet scripts. ❌ the row's parenthetical says "2 ratchet scripts **+ 1 contract test**" — see L1 |
| `grep -rln "summaryMd\|baseName\|baseOf(" … \| wc -l` | **40** files. ✅ reproduces |
| same grep without `-l` | **192** hits. ✅ reproduces the stated three-term figure |
| `ls -1 docs/reviews/spec-blob-addressing-r*-coordinator.md` | exactly r1,2,3,4,7,8,10,12,13,14,15,16,17 — **13 files**. ✅ reproduces |
| `head -3 docs/adr/0006-*.md` | `status: proposed — supersedes ADR-0002 if accepted`. ✅ reproduces |
| `python3 scripts/gen-backlog-page.py; python3 scripts/check-docs.py` | both exit **0**, no working-tree diff. ✅ clean baseline |
| r17's quote (roadmap `:103-105`) | verbatim at `spec-blob-addressing-r17-coordinator.md:121-123`. ✅ reproduces |
| the withdrawn ranking claim | ordering ends `a.generation_id desc` (`04_artifacts.sql:781`) and `generation_id` is in the PK `(workspace_id, video_id, generation_id)` (`03_generations.sql:358`) → **total**. ✅ the withdrawal is correct |

**NOT VERIFIED, said out loud:**

- **Integration and e2e were not run** (no live Supabase stack), per the brief.
- **The Fly `v7` row** (`roadmap:39`) is a doc claim; I did not run `flyctl releases`.
- **`SupabaseBlobStore` behaviour is read from source, never exercised.** In particular M2 below —
  whether Supabase Storage's authenticated `download()` is read-after-write consistent immediately
  following a `move()` — is **NOT VERIFIED and cannot be verified at the unit tier**, which is
  precisely the finding.
- I did not apply the plan's patch (the brief forbids editing), so every claim is traced by hand
  through quoted code.

---

## BLOCKING

### B1 — The silence does not reach the consumer: `deriveClassASignals` falls back to `processedAt`, which the worker still stamps unconditionally

**Where:** plan `:5-7` (the Goal), `:284-309` (the patch), `:89` (Consequences row 2), `:366-400`
(Task 2's tests); `lib/cloud-sync/backfill.ts:8-16`; `lib/job-queue/summary-handler.ts:163`;
`supabase/migrations/0021_cloud_sync_signals.sql:124`.

v2's whole design rests on one premise, stated at `:12-14`:

> *"Silence is therefore a meaningful signal: it means 'I am not telling you anything about this
> field.' M1 makes the worker use that signal correctly — speak when it published, stay silent when
> it did not."*

**Silence about `mdGeneratedAt` is not silence to the consumer.** The consumer is
`deriveClassASignals`, and it does not read `mdGeneratedAt`; it reads `mdGeneratedAt`-or-`processedAt`:

```ts
// lib/cloud-sync/backfill.ts:7-16
export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
  const hasReal = video.mdGeneratedAt != null;
  return {
    …
    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
    …
    backfilled: !hasReal,
  };
}
```

`processedAt` is stamped by the worker on **every** run, published or not, inside the literal the
plan deliberately leaves untouched (`:271`: *"The `const video: Video = { … }` literal at `:149-164`
stays exactly as it is"*):

```ts
// lib/job-queue/summary-handler.ts:162-163
      docVersion: CURRENT_DOC_VERSION,
      processedAt: new Date().toISOString(),
```

and it is one of the twelve keys layer (3) re-applies (`0021:124`), so it lands on both persists
regardless of the `published` gate.

**Concrete failure scenario — the designed re-run, i.e. a `CURRENT_DOC_VERSION` bump. This is the
case the repo's own test header calls "the dangerous case" (`summary-handler-promote-divergence.test.ts:16-19`).**

1. Cloud row for video V holds generation 1: blob `007_alpha.md` = `body_1`, `processedAt = T1`, and
   **no `mdGeneratedAt`** — the worker has never written one (plan `:78`, roadmap `:70-71`). Any
   cloud-first video that has not been through a sync transfer is in this state.
2. Doc version bumps weeks later. The idempotency skip at `summary-handler.ts:86-92` deliberately
   does not fire. Gemini runs and is **paid for**. `core.mdContent = body_2`.
3. `promote` → final key occupied → staged deleted, `body_1` stays live
   (`supabase-blob-store.ts:120-123`).
4. M1's read-back: `mdHash(body_1) ≠ mdHash(body_2)` → `published = false` → the two card keys are
   withheld. **This is v2 working exactly as designed.**
5. `persistSummary('promoted')` nevertheless writes `processedAt = T2`.

Row afterwards: `body_1` live, `mdGeneratedAt` still absent, `processedAt = T2`. Then:

`deriveClassASignals(row, body_1).mdGeneratedAt` = **`T2`** — a timestamp minted for a document the
worker discarded, attached as the provenance of `body_1`. And `backfilled` is `true`, which no
consumer reads (verified below, M2 of round 1 stands).

That value is what the tiebreak consumes. Local holds `body_1'` (the user's corrected copy,
generated at `T1.5`), corrections settled so both sides read current, same major:

```ts
// lib/cloud-sync/reconcile-class-a.ts:49-50
  const winnerIsLocal = newer(local.mdGeneratedAt, cloud.mdGeneratedAt);
  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
```

`newer('T1.5', 'T2')` is false → **`copyToLocal`**: the stale cloud `body_1` overwrites the newer
local body, decided by a timestamp the worker stamped for bytes it threw away. The fallback also
becomes **durable** on the additive path — `baselineFromOneSided` writes `classA.mdGeneratedAt`
straight into the persisted `VideoBaseline` (`sync-run.ts:314-318`), so the provisional value is
laundered into the manifest as if it were real.

**Why this is Blocking rather than Medium, given it is not a regression against today.** It is not
a regression — the outcome is identical pre-M1. It is Blocking because:

1. **The plan asserts the opposite.** `:5-7`: *"so a video row can never advertise one document's
   provenance beside another document's content."* After v2 it still can, on the branch v2 added.
2. **Every v2 test certifies the fix as complete while the defect stands.** Task 2's assertions are
   `expect(Object.keys(p.video)).not.toContain('mdGeneratedAt')` (`:383`, `:397`) — they measure the
   *mechanism* (a key is absent from a payload), not the *outcome* (what signal the row produces).
   An assertion on `deriveClassASignals(...).mdGeneratedAt` would fail. This is the repo's own
   `a-checklist-item-can-be-an-unfalsifiable-guard` shape one level down: the observation that would
   catch the residue is not made.
3. It is exactly the error class v2's own retrospective names at `:52-56` — *"v1 reasoned about a
   write the storage layer does not actually perform"*. v2 reasons about a **read** the consumer
   does not actually perform.

**Suggested fix.** Make the silence cover every layer-3 key that feeds a Class-A signal, not just
the two the plan is named after. Concretely, on `published === false` withhold `processedAt` as well
— layer (2) then preserves the previous `processedAt`, which correctly describes the body that *is*
at the key, and the first-ever-write case is unaffected because an empty key always publishes.
`docVersion` is the harder half (H2). And **change Task 2's assertions to run
`deriveClassASignals`** on the resulting row plus the live body, and assert on
`.mdGeneratedAt` — the payload-key assertion cannot see this class at all.

---

## HIGH

### H2 — `docVersion` outranks `mdGeneratedAt` at the consumer and stays unconditional; the repo's own test already says so

**Where:** plan `:5-7`, `:76` (the "always sent — yes" row), `:271`;
`lib/cloud-sync/reconcile-class-a.ts:43-46`;
`tests/lib/job-queue/summary-handler-promote-divergence.test.ts:160-172`.

The plan's scope section (`:66-83`) carefully carves out five optional fields that inherit "when
Gemini omits them", and lists `processedAt` and `docVersion` in the **"Always sent? yes"** row
(`:76`) as if that made them safe. On the not-published branch, "always sent" is the *problem*, not
the reassurance: they are sent for a body that was discarded.

`docVersion` matters more than the two fields M1 fixes, because `reconcileClassA` consults it
**before** the recency tiebreak:

```ts
// lib/cloud-sync/reconcile-class-a.ts:43-46
  if (local.docVersionMajor !== cloud.docVersionMajor) {
    const winnerIsCloud = cloud.docVersionMajor > local.docVersionMajor;
    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
  }
```

Replay B1's scenario across a **major** bump: the cloud row now claims major 2 over `body_1`, which
is major-1 content, and the never-downgrade rung hands the whole decision to the cloud on a false
premise — no tie needed.

The repo has already written this down as executable fact, in the file the plan tells the engineer
to copy its fixture from, immediately below the `it.failing` tripwire v2 correctly declines to
duplicate:

```ts
// tests/lib/job-queue/summary-handler-promote-divergence.test.ts:160-172
  // The silence is the second half of the defect: whatever the blob ends up holding, the
  // handler unconditionally reports 'promoted' at the CURRENT doc version.
  it('stamps promoted at the current doc version regardless of what the blob holds', async () => {
    …
    expect(persisted.at(-1)?.docVersion).toEqual(CURRENT_DOC_VERSION);
  });
```

**That test passes unchanged after M1.** A plan whose goal sentence is *"speak when it published,
stay silent when it did not"* leaves green a test whose comment says the handler speaks
unconditionally. That is a direct contradiction between the plan's claim and a live assertion.

**This is pre-existing (backlog #22 / #17 §6) and I am not asking M1 to fix it here.** I am asking
the plan to stop claiming it did. Withholding `docVersion` on the un-published persist is *not* a
free change: it also breaks the second conjunct of the idempotency skip (`summary-handler.ts:86-92`)
— which backlog #22 argues is **desirable** (`docs/backlog.md:51`, *"The fix (#17 §6): withhold
`docVersion` from the `committed` write"*) but which changes re-run and therefore **spend** behaviour
and belongs in its own slice.

**Suggested fix:** narrow the Goal sentence to the two fields it actually delivers; add a row to the
Consequences table saying that `docVersion`, `processedAt` and the eight scalar fields remain
unconditional on the not-published branch, name `reconcile-class-a.ts:43-46` as the consumer that
ranks `docVersion` **above** the field M1 fixes, and cite
`summary-handler-promote-divergence.test.ts:162` as the standing evidence. Then either fold the
`processedAt` half into M1 (B1) or file it with the five-field row in Task 4 Step 2.

### H3 — The read-back reads through `get`, which cannot distinguish "not published" from "could not tell", and reports nothing either way — so M1 can be a permanent silent no-op

**Where:** plan `:303` and `:302` (*"Fail closed — an unreadable read-back is not proof"*);
`lib/storage/supabase/supabase-blob-store.ts:34-44`, `:11`, `:70-83`.

```ts
// plan :303-307
    const live = await bundle.blobStore.get(bundle.principal, key).catch(() => null);
    const published = live != null && mdHash(live.toString('utf-8')) === mdHash(core.mdContent);
```

On the backend this runs against, `get` is the read the codebase has explicitly labelled dishonest:

```ts
// lib/storage/supabase/supabase-blob-store.ts:34-44
  async get(p: Principal, key: string): Promise<Buffer | null> {
    const { data, error } = await this.b().download(this.objectKey(p, key));
    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
    // so a null here does NOT prove the object is absent. Callers that treat "no bytes" as a
    // semantic fact … must corroborate it against the record that advertises the key
```

and `provesAbsence = false` on that class (`:11`). The seam already ships the honest read for exactly
this job — `tryGet` (`:70-83`), which separates `absent` from `unreadable` and swallows the
transport throw internally, making the `.catch(() => null)` unnecessary. `sync-run.ts:668-699`
spends thirty lines explaining why the Class-A path had to stop using `get` this way; the memory
`rls-denial-is-indistinguishable-from-absence` records that the same substitution on the serve path
cost a 6¢→12¢ double charge.

Failing closed is the right *policy*. The defect is that **the two closed outcomes are merged and
neither is observable**:

- `published = false` because the bytes genuinely did not land — correct, silence is honest.
- `published = false` because the read blipped, was rate-limited, timed out, or the worker's grant
  changed — the bytes **did** land, and the row now keeps a card describing the *previous*
  generation over a body that is no longer there. **That is the original defect M1 exists to
  remove, silently reintroduced.**

Nothing distinguishes them at runtime. There is no log line, no `report.errors` entry, no metric,
no throw. Ask this repo's own question — *"what would I see if it were silently doing nothing?"*
(`a-mechanism-can-be-silently-overridden`) — and the answer is **nothing at all**: a misconfigured
read path makes M1 a total no-op in production while all four unit tests stay green, because they
exercise an in-memory `Map`.

**Suggested fix:** use `tryGet`. Treat `{ ok: true }` + hash match as published; treat
`{ ok: false, reason: 'absent' }` and a hash mismatch as not published (silence, no noise); treat
`{ ok: false, reason: 'unreadable' }` as an **anomaly** — still fail closed on the stamp, but surface
it (throw, or at minimum a `console.warn` with the key and cause, matching how the worker reports
other non-fatal faults). Add a test for the `unreadable` branch built on the double's own
`failReads` (see M4). Drop `.catch(() => null)`, which currently also swallows programmer errors
such as an `assertLogicalKey` throw.

### H4 — Task 4's Steps 3, 5 and 6 contradict each other: Step 6 will fail, and the check that fails is one the plan never names

**Where:** plan `:475-502`; `scripts/gen-backlog-page.py:357-366` (`DEPENDS`), `:369-397`
(`depends_errors`), `:678-691` (`coverage_errors`), `:641` (the open/closed rule), `:767-773`.

Step 3 says:

> *"Change the status cell away from `pending (needs spec)` — **#19 is a symptom, not work.**"*

Step 5 says to **keep** the edge and only change its relation:

> *"`DEPENDS[19]` → `dissolved-by` (was `survives`; §5.2 decided it)."*

Whether a row is open is decided by one character in its status cell:

```python
# scripts/gen-backlog-page.py:641
            status=status, closed=("✅" in status),
```

and both graph checks are keyed off that set:

```python
# scripts/gen-backlog-page.py:374
        if item not in open_nums:
            errors.append(f"#{item} has a dependency but is not an open item")
```
```python
# scripts/gen-backlog-page.py:683-686
    extra = sorted(n for n in grouped if n not in open_nums)
    …
        errors.append(f"GROUPS names items that are not open: {extra}")
```

Both raise `ShapeError` at `:769` / `:772`, so `python3 scripts/gen-backlog-page.py` exits non-zero.

**Concrete failure:** the engineer reads Step 3 plus the roadmap's *"There is nothing to build for
it"* (`roadmap:161-163`) and marks #19 `✅ re-filed as a symptom`. `#19` leaves `open_nums`. Step 6
then fails twice — once on `DEPENDS[19]` (which Step 5 just told them to keep), and once on
`GROUPS`, where #19 is listed at `scripts/gen-backlog-page.py:98-99`. **Task 4 never mentions
`GROUPS` at all.**

Two smaller errors ride along:

- Step 6's diagnostic is wrong: *"A non-zero `depends_errors` means an edge points at nothing"*
  (`:502`). The error actually raised here is `#19 has a dependency but is not an open item` — a
  different cause with a different fix, and the message the engineer will see is a `ShapeError`, not
  a non-zero `depends_errors`.
- `depends_errors` never validates direction, so the plan's warning at `:490-494` (do not reverse
  the arrow) is correct and load-bearing: I confirmed the function checks only relation-known,
  root-exists, item-open and numeric cycles. **The plan's Task 4 Step 5 claim is verified true.**

**Suggested fix:** say explicitly whether #19 closes. If it does: delete `DEPENDS[19]` and remove
#19 from `GROUPS` in the same step, and say so. If it does not (it stays open with a reworded status
that contains no ✅): say *that*, because it is the non-obvious half. Either way, replace Step 6's
diagnostic with the two real ones.

---

## MEDIUM

### M1 — No test covers the occupied-key case that actually happens in production, and `setup`'s third parameter is dead

**Where:** plan `:195` (`setup(store, mdContent, existingRow)`), `:219`, `:238`, `:374`, `:389` —
all four call sites pass `null`; `:372-373` (the comment).

Task 2's comment says:

> *"Modelling it as null is what makes this the #19 window rather than a re-summarize."*

I traced the #19 window and it **is** reachable, so the comment is not wrong: `readVideo` at
`summary-handler.ts:84` runs *before* `reserveVideoSlot` at `:95`, so a first run legitimately sees
`null` and then creates the row; a sync that finds `cv.summaryMd` unset takes
`reconcileClassA`'s `!cHas` branch (`reconcile-class-a.ts:23`) → `copyToCloud` → `transferClassA`
lands the local body at that key while the worker is still in Gemini. Good.

But by choosing that window the plan tests only the **rarer** of the two occupied-key paths and
leaves the common one — the doc-version re-summarize, where the *previous generation* occupies the
key — with **no coverage at all**, despite `existingRow` existing as a parameter for exactly that
and being passed `null` four times out of four. The fixture the plan copies from does model it:
`setup(store, 'REGENERATED summary body', { major: 1, minor: 0 })`
(`summary-handler-promote-divergence.test.ts:133`, `:153`, `:167`).

This is also where B1 and H2 bite hardest, which is presumably not a coincidence.

**Fix:** add a third Task-2 test with `existingRow` = a `{major:1,minor:0}` row plus a pre-seeded
blob, asserting silence — and, per B1, asserting on `deriveClassASignals`, not on payload keys.
If `existingRow` genuinely has no non-null caller, drop the parameter.

### M2 — The read-back's correctness depends on read-after-write consistency the unit tier cannot test, and the plan does not name the assumption

**Where:** plan `:303`, `:537-540` ("Known gaps"); `supabase-blob-store.ts:124` (`.move(from, to)`),
`:35` (`.download(...)`).

`published` is decided by downloading the object microseconds after `move()` returned. The double
that proves the design is a `Map` (`in-memory-blob-store.ts:45`), where that is trivially
consistent. Against hosted Supabase Storage it is an assumption about the authenticated download
path's behaviour immediately after a move — and if it is ever wrong (a stale read, an edge cache, a
replica lag), `published` is `false`, M1 silently no-ops, and by H3 nothing reports it.

I could not test this. **NOT VERIFIED — and it is not verifiable at the tier the plan chose**, which
is the point worth writing down rather than the risk itself.

**Fix:** name the assumption in "Known gaps" beside the existing two, and say what would falsify it
(an integration-tier test on a real bucket: `putStaged` → `promote` → `get`, assert the bytes come
back). If H3's `unreadable` reporting lands, a stale read at least becomes visible in production
instead of inferable.

### M3 — The read-back lengthens a user-visible 503 window, uncapped and unabortable

**Where:** plan `:291-309`; `lib/html-doc/serve-summary-core.ts:50`; `summary-handler.ts:170`.

Between `promote` (blob live) and `persistSummary('promoted')` (row says promoted), a reader gets:

```ts
// lib/html-doc/serve-summary-core.ts:50
  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
```

v2 inserts a full object **download** into that window. `BlobStore.get` takes no `AbortSignal` and
the handler does not re-check `ctx.signal.aborted` after `promote` (the only check is at `:170`,
before the write sequence), so a slow or hanging read extends the 503 by however long Supabase takes
and cannot be cut short by lease loss.

The plan's cost framing (`:539`, *"negligible against a Gemini call"*) is right about **money** and
silent about **latency in a window that is already user-visible**. Small, but the plan's Known-gaps
entry should say the true thing rather than the cheaper one.

**Fix:** say it in the Known gaps and the PR body. Optionally re-check `ctx.signal.aborted` before
the read-back — a worker that has lost its lease has no business lengthening the window.

### M4 — Task 2's second test bypasses the double's purpose-built fault injector, and the shape the real backend actually produces is untested

**Where:** plan `:390` (`jest.spyOn(store, 'get').mockRejectedValue(...)`);
`lib/storage/testing/in-memory-blob-store.ts:58-62`, `:109-119`, `:32-37`.

Answering the brief's question directly: **`InMemoryBlobStore.get` can reject, and the real backend
can too — the test is not asserting an unreachable scenario.** The double rejects when a read fault
is armed and `provesAbsence` is true, which is the default the plan's constructor call inherits:

```ts
// lib/storage/testing/in-memory-blob-store.ts:111-116
    if (this.readFaults.has(key)) {
      // Local rethrows every non-ENOENT errno; Supabase swallows into null. That
      // difference is the whole reason `provesAbsence` exists.
      if (this.provesAbsence) throw this.readFaults.get(key);
      return null;
    }
```

and `SupabaseBlobStore.get` has no `try/catch`, while `tryGet`'s comment states the throw is real:
*"download() throws rather than returning `error` on a transport failure"* (`supabase-blob-store.ts:80`).

So the finding is not reachability. It is that the plan reaches for `jest.spyOn` when the double
ships `failReads` (`:60-62`) written for this, and in doing so tests the **local** shape (throw)
while the cloud worker runs against the backend whose failure shape is **`return null`**
(`supabase-blob-store.ts:42`, `provesAbsence = false` at `:11`). Both paths reach `published =
false`, so the gate is fine — but the more common branch has no test, and the version that *does*
have a test was written in a way the double's own docstring (`:15-30`) argues against.

**Fix:** replace the spy with `store.failReads(SUMMARY_KEY)`, and add the cloud shape as a second
case: `new InMemoryBlobStore({ promoteSemantics: 'create-if-absent', provesAbsence: false })` plus
`failReads`, which returns `null` exactly as Supabase does. Two cases, one line each, and they model
the two shipped adapters instead of a hypothetical third.

---

## LOW

- **L1 — round-1 L5 is not fixed.** `roadmap:34` still reads *"(2 ratchet scripts + 1 contract test
  only)"*. Its own command returns **two** files — `check-guard-coverage.py` and
  `check-sentinel-meanings.py` — and `grep -c generation_id tests/lib/blob-addressing-caller-contract.test.ts`
  is **0**. The row now carries the command that refutes its own parenthetical, which is worse than
  carrying no command. Drop "+ 1 contract test".
- **L2 — round-1 L2 is not fixed.** Plan `:534` still cites *"`ClassASignals` (`types.ts:32`)"*.
  `ClassASignals` is `lib/cloud-sync/types.ts:4-11`; the two fields are `:8-9`; line 32 is
  `VideoBaseline['classA']`.
- **L3 — the choice of `mdHash` over a byte compare is unasserted.** An implementation using
  `live.toString('utf-8') === core.mdContent` passes all four tests. `mdHash` canonicalizes CRLF,
  trailing newlines and NFC (`content-hash.ts:9-13`), which is a deliberate and different decision —
  and the only one that survives a backend that normalizes line endings. Worth one assertion, or one
  sentence saying it does not matter here.
- **L4 — `jest.restoreAllMocks()` sits in the test body** (`:399`), so it does not run if an
  assertion above it throws. Use `afterEach`.
- **L5 — Task 1 Step 1's "copy the fixture" instruction is now redundant and slightly wrong.** The
  plan supplies the complete fixture inline (`:138-209`), so there is nothing to copy; and the
  supplied version differs from the source in four ways, not the two the comment lists (`:135-137`)
  — it also adds `WORKER_BODY`, changes `setup`'s third parameter from `existingDocVersion` to
  `existingRow`, and adds the `promoted()`/`committed()` selectors. `setup` does close at `:112`, so
  round-1 L1's line-range half is fixed.
- **L6 — round-1's uncovered item 4 is not fixed:** `generatedAt` (`:277`) and `processedAt`
  (`summary-handler.ts:163`) are still two separate `new Date()` calls one line apart. Harmless, but
  the plan claims the worker stamps *the* provenance and that is two instants. Also, v2 dropped
  round-1's other uncovered item — the Global Constraint enumerating all four writers of these two
  fields (`pipeline.ts:271-272`, `regenerate/route.ts:87-88`, `sync-run.ts:401-402`,
  `summary-handler.ts` after this change) — rather than correcting it.
- **L7 —** plan `:491` cites `gen-backlog-page.py:356-366` for `DEPENDS`; the dict is `:357-366`
  (`:356` is its comment). Roadmap `:171`'s `:358` for `DEPENDS[19]` is exact.

---

## Every round-1 finding: fixed, partly fixed, or made worse

| R1 finding | Verdict |
|---|---|
| **Claude B1** — unconditional stamp is wrong when promote skips | **Partly fixed.** The gate is real and correct for the two named fields; the tests prove it (an unconditional-stamp implementation fails Task 2 test 1). But the fix stops at the payload and does not reach the consumer — **B1 above**. |
| **Claude H1** — vacuous assertions in a loop over an empty list | **Fixed.** All four tests carry `expect(...length).toBeGreaterThan(0)` (`:224`, `:242`, `:378`, `:395`), and Task 1 test 1 adds a genuine precondition assertion at `:226`. The unreachable `status: 'committed'` fixture is gone. |
| **Claude H2 / Codex Blocking** — characterization duplicates the `it.failing` tripwire | **Fixed, correctly.** The test is deleted and `:356-360` explains why, quoting the ban. I confirmed nothing in v2 contradicts `summary-handler-promote-divergence.test.ts:148`, and that the `it.failing` still fails (hence passes) after M1: the read-back does not change what `promote` does. |
| **Claude H3 / Codex Medium** — Task 3 pastes over an existing file | **Fixed.** Task 3 appends inside the existing `describe` and reuses `S`/`CUR`, which exist at `reconcile-class-a.test.ts:4-8`. I verified the tie case is genuinely uncovered (`:39-44` covers strict-newer only) and that the snippet's expected value is right: same major, both current, different `mdHash` → `:49` `newer(at, at)` is false → `copyToLocal`. |
| **Claude H4** — convergence row seven rounds stale | **Fixed and reproduces.** 13 coordinator files, exactly the list given. |
| **Claude H5** — M3's ranking instruction refuted by the schema | **Fixed.** Withdrawn at `roadmap:109-114`, and I verified the withdrawal is itself correct: the order-by ends `a.generation_id desc` and `generation_id` is in the PK, so the ordering is total. |
| **Claude H6** — M1 converts `skip` into a redundant `transferClassA` | **Genuinely dissolved, and I agree with v2 against round 1.** H6 depended on the cloud card being overwritten with `mdHash('')` when promote skipped. Under v2 the worker stays silent, layer (2) preserves the inherited card, `cCur` stays true, and the `skip` at `reconcile-class-a.ts:33` survives. Recorded at `:89`. |
| **Claude M1** — Task 3 described as proof of M1 | **Fixed.** `:425-428` says the opposite in bold, and the duplicated first test is gone. |
| **Claude M2** — `backfilled` row cited the wrong reader | **Fixed, with the stronger claim.** Verified: `grep -rn "\.backfilled"` over `lib app components worker types` returns exactly one property read, `reconcile-class-b.ts:43`, on `FieldState`. `ClassASignals.backfilled` has zero readers. |
| **Claude M3** — the `DEPENDS` reverse edge is not expressible | **Fixed as prose, and the claim is true** (`ROOTS` values are `label`/`detail` only, `:336-343`; `depends_errors` validates no direction). But Task 4 now has a *different* executable problem — **H4 above**. |
| **Claude M4** — five more fields inherit the same way | **Fixed for the omitted-by-Gemini case** (`:66-83` + Task 4 Step 2). **Not fixed for the not-published case**, which is the larger one — H2. |
| **Claude M5** — wrong backlog row on every commit | **Fixed.** `#23a` throughout the plan, the roadmap and all four commit messages; the Global Constraint at `:25-27` states the correction. |
| **Claude M6 / Codex Medium** — Step 6 had no decision procedure | **Fixed.** `:326-334` is a real stop rule with a named artifact to record. One gap: it is scoped to *"any Class-A or sync test"*, and the tests most likely to move are in `tests/lib/job-queue/`. |
| **Codex High** — the corrections consequence ignores the unresolved-conflict guard | **Fixed and verified.** Row at `:91`; the guard is `sync-run.ts:707-721` (`correctionsUnresolved` at `:707`, `continue` at `:720`). |
| **Codex Low / Claude L4** — the 192/40 figure | **Fixed and reproduces exactly**, with the command and an honest note that the count varies with the pattern. |
| **Claude L1** | Half fixed — `:112` is right; see L5. |
| **Claude L2** | **Not fixed** — L2 above. |
| **Claude L3** (`'Clawcode -> Clawcode'`) | Fixed by deletion. |
| **Claude L5** | **Not fixed** — L1 above. |
| **Claude L6** (`0021` citation) | **Fixed** — `:10` now cites `:115-153`. |

**Did any fix break something new?** No fix introduced a new *defect*. Two introduced new *problems*:
Task 4's Steps 3/5/6 became mutually inconsistent while fixing M3 and M5 (**H4**), and the read-back
introduced by fixing B1 brought its own silent-degradation surface (**H3**) and a latency cost in an
already-visible window (**M3**). The Blocking is not a break either — it is the round-1 fix stopping
one layer short of the consumer, certified complete by tests that measure the mechanism instead of
the outcome.

---

## Test quality: would any of these pass on a broken implementation?

I mutated the intended implementation on paper against all four tests:

| Mutation | Caught by |
|---|---|
| stamp unconditionally (i.e. v1) | Task 2 test 1 ✅ |
| never stamp | Task 1 test 1 ✅ |
| stamp whenever `live != null`, no hash compare | Task 2 test 1 ✅ |
| stamp on the `committed` persist too | Task 1 test 2 ✅ |
| byte-compare instead of `mdHash` | **nothing** — L3 |
| leave `processedAt` unconditional | **nothing** — B1 |
| leave `docVersion` unconditional | **nothing** — H2 (and `promote-divergence.test.ts:162` positively asserts it) |

The round-1 shape (assertions inside a loop over an empty list) is gone, and the guards that replace
it are load-bearing. The residue is that three of seven mutations survive, all three on the "what
does the row end up claiming" axis, because every assertion is on a payload key rather than on the
signal the row produces.

---

## Decomposition, placeholders, type/name consistency

- **Decomposition.** Tasks 1→2 correctly ordered (2 consumes `setup`, `persists`, `promoted()`,
  `SUMMARY_KEY`, `WORKER_BODY` from 1 — all declared at `:193-212`). Task 3 is independent and
  correctly labelled as not proving M1. Task 4 depends on nothing in 1–3. **No finding.**
- **Placeholders.** `:530-531` claims none. Nearly right: Task 4 Steps 1–4 specify prose outcomes
  without the text, which is defensible. Step 5 is no longer a placeholder — it is now an
  under-specified *instruction* (H4).
- **Type consistency.** `mdGeneratedAt: string` / `mdCorrectionsHash: string` match
  `types/index.ts:87-88` (both `.optional()`), the layer-3 keys at `0021:131-132`, and
  `ClassASignals` at `lib/cloud-sync/types.ts:8-9`. `promotedVideo` is `{ ...video, … }`, assignable
  to `Partial<Video>` as `persistSummary` requires (`worker-persistence.ts:18-27`). Task 3 declares
  nothing and collides with nothing. **No finding beyond L2's wrong citation.**

## What v2 still does not cover and should

1. **The consumer.** B1 and H2 — the payload is not the interface; `deriveClassASignals` is.
2. **Observability of the closed branch.** H3 — a gate with two indistinguishable failure modes and
   no output is a gate you cannot audit in production.
3. **The re-summarize path.** M1 — the common occupied-key case, untested.
4. **The other three writers of these two fields.** `pipeline.ts:271-272`,
   `regenerate/route.ts:87-88`, `sync-run.ts:401-402`. v2 dropped round 1's Global Constraint about
   them instead of correcting it; if the point is that the four writers must not drift, enumerating
   them is cheap and the plan is where it belongs.

---

## Verdict

**NOT CONVERGED**
