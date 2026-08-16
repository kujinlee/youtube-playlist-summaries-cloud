# Plan review round 4 — COORDINATOR adjudication

Subject: `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md` at commit `c964672`.
Written 2026-08-16 by the coordinator, alongside the Codex and Claude halves, not instead of them.

This file records three things the two review halves cannot: findings the coordinator made
independently before either half reported, the **verification** of each half's findings by hand
(agent output is a lead, not a finding), and the re-attribution where a half was right about the
defect and wrong about its address.

---

## 1. Verification of the Codex half

| Codex finding | Verdict | Note |
|---|---|---|
| **Blocking — T8, plan:1711** — `seedEnvelope(cloud, base, undefined as unknown as string, …)` cannot seed a legacy envelope once T7 makes `videoId` required | ✅ **CONFIRMED** | And worse than stated: `seedEnvelope` casts `as ModelEnvelopeWrite` (plan:1632), so `tsc` stays green and it fails at **runtime** inside `ModelEnvelopeWriteSchema.parse`. Behavior 18j4's test cannot construct its own precondition through the writer whose new rule it exists to test |
| **Blocking — T12, plan:2649** — the 26d2 block declares no `ctx`, `EVIL`, imports | ✅ **CONFIRMED as a defect**, ❌ **wrong address** — see §2 |
| **Medium — rollout count** — plan says 42, should be 41 | ✅ **CONFIRMED** | Independently recounted; see §3 |
| **Low — sweep noun** — "3,479,131 iterations" survives at plan:3326 and :3359 | ✅ **CONFIRMED** | Both sites read verbatim |

Codex also cleared T10 and T13's blocks as pasteable with biting assertions, and confirmed the
round-3 `cloud.ts:131` fix. The coordinator independently resolved every import and free identifier
in T8, T10 and T13 and agrees.

---

## 2. Re-attribution: the T12 Blocking belongs to T11, and the class is four files wide

Codex read Task 12 in isolation, saw `tests/integration/cloud-sync/adopt-guard.int.test.ts` in its
Files block, observed the file does not exist, and concluded T12 creates it. **It does not.**
**Task 11 creates it** — plan:2269, explicitly marked `(new)` — and defines `EVIL` at plan:2280.
T12's block is an *append*, which is legitimate; T12's real (smaller) defect is that it does not
*say* it is an append, whereas T12's Step 1 does say exactly that for the unit file (plan:2414).

The larger finding is the one neither half reported. Measured over all ten integration-test blocks
in the plan, splitting on whether the target file exists in the tree today:

| New file (header REQUIRED) | Task | Header shown in the plan? |
|---|---|---|
| `tests/integration/blob-encoding.test.ts` | T2 | ❌ **no** |
| `tests/integration/cloud-sync/companion-videoid.int.test.ts` | T8 | ✅ yes — v4 |
| `tests/integration/metadata-seam.test.ts` | T9 | ❌ **no** |
| `tests/integration/summary-handler-guard.test.ts` | T10 | ✅ yes — v4 |
| `tests/integration/cloud-sync/adopt-guard.int.test.ts` | T11 creates, T12 appends | ❌ **no** |
| `tests/integration/korean-title-e2e.test.ts` | T14 | ❌ **no** |

Existing files — `share-route.test.ts`, `share-serve.test.ts` (T5), `blob-store.test.ts` (T6, T13) —
are appends and correctly show no header. That is not a defect.

**So four new integration files have no imports, no `ctx` lifecycle and no `beforeEach` anywhere in
the plan.** Each is a step that cannot be executed as written: **Blocking**.

### Why this was missed twice

Round 3 named **four** incomplete fixture blocks. v4 fixed **those four**. Round 3 named **one**
stale line citation. v4 fixed **that one** (see §4). Both times the fix treated the reviewer's
sample as the population.

A reviewer names instances. **Deciding whether an instance is a class is the coordinator's job**,
and on this plan it was not done — twice in one round. This is the same shape already recorded in
`docs/portable-practices.md` and in the two-sandboxes note in `docs/plugins.md`: *solving one
instance and reading as if it covered the class.*

---

## 3. The rollout count, got wrong for the fourth time — and the plan contradicts itself

The plan states the count in **four places with three different values**:

| Site | Says |
|---|---|
| plan:1401 (the table) | total **42**, test **39** |
| plan:1401 per-file itemization (14+8+5+4+3+2+1+1) | test **38** |
| plan:1494 (Step 4) | "fix all **41** call sites … Expected: ~**42** errors" |
| plan:3325 (disposition C-L1) | "**FIXED — 41** (3 prod + 38 test)" |

**The table is inconsistent with its own itemization**, which is stronger evidence than any recount.

Coordinator's independent count under the plan's own stated rule — *"the identifier followed by `(`
OUTSIDE a string literal, excluding imports, comments and the two definitions"*:

- production **3** — `lib/cloud-sync/sync-run.ts:464`, `lib/html-doc/serve-doc.ts:174`,
  `lib/html-doc/generate.ts:50`
- test/e2e **38**
- **total 41.** Codex independently got 41. The itemization sums to 38 test. **41 is correct.**

⚠ **The coordinator's first count was 42**, because the script excluded string literals but *not*
comments, and `lib/html-doc/serve-doc.ts:158` mentions `writeModelEnvelope (plain put …)` inside a
comment. **The written rule caught its own author.** That is the fix from v4 working exactly as
intended, on its fourth victim — and it is the argument for writing derivation rules next to derived
numbers rather than trusting a recount.

The plan's cited `model-store-cloud.test.ts:52` is **correct** (`it('writeModelEnvelope overwrites an
existing final via upsert…')`); only the directory was elided — the file is `tests/lib/`.

---

## 4. Held back from both halves — Task 0's inventory citations

Not put in the round-4 prompt, deliberately, so that finding it would measure whether a reviewer
checks citations mechanically or by eye. **Neither half found it.**

Round 3 (Codex, Low) found ONE citation in Task 0's inventory table wrong: `helpers/cloud.ts:132`
should be `:131`. v4 fixed that one and rechecked none of the others.

**All 19 `path:line` citations in Task 0 were then resolved mechanically. SIX are wrong:**

| Plan claims | Actual | Delta |
|---|---|---|
| `Ctx.spendLedgerTotal()` — `helpers/cloud.ts:157` | 153 | −4 |
| `cloudVideoRecord` — `helpers/cloud.ts:468` | 471 | +3 |
| `localVideoRecord` — `:473` | 476 | +3 |
| `seedVideo` — `helpers/cloud.ts:378` | **296** | **−82** |
| `seedFreshModel` — `share-route.test.ts:78` | 79 | +1 (points at the doc comment) |
| `putBudget` — `tests/support/budget.ts:21` | 18 | −3 |

The other thirteen are correct, including every `sync-run.ts` export offset (`:40`, `:51`, `:62`,
`:221`, `:371`, `:444`, `:547`), `model-store.ts:46/:66`, `blob-store.ts:87`,
`supabase-blob-store.ts:151`, `share-serve.test.ts:17`, `reconcile-serial.ts:152`, and the `:131`
round 3 fixed.

`seedVideo` is the material one — 82 lines off lands an implementer inside a different function.
The rest are navigational. **Severity: Medium** (misleading, not blocking).

⚠ **Note the shape of the discovery itself.** The coordinator's *first* pass checked the five
citations that looked related to the ones round 3 flagged and found four wrong. Only sweeping all
nineteen found six — **50% more than the targeted pass**. The targeted pass was itself an instance
of the §2 failure, committed while writing up §2. That is how strong this pull is, and it is the
argument for a script rather than a more careful human: *the criterion for which citations to check
must not be "the ones that look suspicious."*

All six are corrected in v5.

---

## 5. What v4 got right, verified rather than assumed

- Every one of the 22 modules imported by the T8/T10/T13 blocks **exists**.
- T8's switch to `@/tests/integration/helpers/cloud` is the *structural* fix to round 3's
  relative-path Blocking: `@/*` → `./*` is mapped identically in `jest.config.ts:9` and
  `jest.integration.config.ts:5`, so the import no longer depends on the test file's depth.
- Every symbol round 3 listed as undeclared in T8 is now bound — including `cloudVideoRecord` and
  `localVideoRecord`, which exist at `helpers/cloud.ts:471,476`.
- `ModelEnvelopeWrite` is a forward reference to T7 and is **coherent**: T7 defines it in
  `lib/html-doc/model-store.ts` (plan:1482), T8 declares it in *Consumes* (plan:1537) and imports it
  from that exact path.
- Task 0 exports all four symbols the later tasks import (`Side`, `copyAdditiveVideo`,
  `transferClassA`, `companionTransfer`) — plan:203 and plan:283.
- `docVersionKey`, `adminClient`/`newUser`/`signInAs` all exist with the names T10 uses.

---

## Verdict

**NOT CONVERGED.** Two Blockings stand (T8's legacy-envelope seed; four new integration files with
no header), plus a Medium count contradiction, a Medium citation sweep, and a Low noun.

## Proposed disposition for v5

1. **T8/18j4** — seed the legacy envelope as raw JSON through `side.blob.put(side.p, MODEL_KEY(base), …)`
   with the `videoId` property *omitted*, not `undefined`. Keep `writeModelEnvelope` for the rest.
   Then re-run the block; the round's own rule is that a fixture is EXECUTED or it is quoted.
2. **T2, T9, T11, T14** — give each new integration file its complete header, as T8 got. Add one
   line to T12 Step 6 saying it appends to T11's file.
3. **Count** — make plan:1401 say 41 / 3 / 38 and plan:1494 say 41 errors. Leave the rule beside it.
4. **Citations** — correct the four Task 0 numbers. File the durable fix (a script resolving every
   `path:line` citation in plan and spec docs) as a backlog item rather than building it inside this
   slice, which is four plan rounds deep on a subject that is not citation hygiene.
5. **Noun** — plan:3326 and :3359, "iterations" → "non-empty slug assertions".
