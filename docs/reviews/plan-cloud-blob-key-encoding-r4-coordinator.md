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

## 1b. Verification of the Claude half — and it earns the dual-review rule again

The Claude half took far longer and landed after this file's first draft, which is why §4 carried a
wrong sentence for one commit. Its verdict: **NOT CONVERGED**, 2 Blocking / 1 High / 1 Medium / 4 Low.

| Claude finding | Verdict | Overlap |
|---|---|---|
| **Blocking 1 — T8 18j4, the legacy envelope cannot be seeded once T7 lands** | ✅ **CONFIRMED** | **Same as Codex, found independently.** Two reviewers converging on one Blocking from different directions is the strongest signal this round produced |
| **Blocking 2 — T12 Step 6's `ctx` is undeclared, AND THE OBVIOUS REPAIR IS WRONG** | ✅ **CONFIRMED** | Codex found the missing `ctx`; **only Claude saw that a shared `beforeEach` would be a NEW bug**, because each `makeOwnerContext()` mints a new user. The coordinator hit the same trap and avoided it while writing T11's header — three parties, one conclusion |
| **High 1 — T13 behavior 18 asserts a property of the VOLUME, in the suite CI runs** | ✅ **CONFIRMED, and it is the best finding of the round** | **Neither Codex nor the coordinator found this.** Verified here: `.github/workflows/ci.yml:27,57` runs `npm test` on `ubuntu-latest`; `jest.config.ts` `testMatch` collects `tests/lib/**`, which is where T13 deliberately moved this file *so that CI would run it*; and this Mac measures APFS as normalization-INSENSITIVE (`linkSync` → `EEXIST`, one file). On ext4 the link succeeds, two files exist, and `toEqual([NFC])` is red. ⚠ The ext4 half is **reasoned, not measured** — no ext4 volume was available here |
| **Medium 1 — the rollout count is both 42 and 41** | ✅ CONFIRMED | Same as Codex and the coordinator. Three independent parties, one answer: **41** |
| **Low 1 — the wrong noun is repeated elsewhere** | ✅ CONFIRMED | Same as Codex |
| **Low 2 — round 3's citation fix took; four neighbours did not** | ✅ CONFIRMED | **The held-back lead — see §4.** Found one the coordinator missed |
| **Low 3 — two "verbatim today" quotes silently elide comment blocks** | ✅ CONFIRMED as stated | Neither other party found it. Every code line and their order are accurate; the plan marks elisions explicitly elsewhere, so an unmarked one reads as a discrepancy |
| **Low 4 — no step adds the `isServableSummaryKey` import to the two files that call it** | ✅ CONFIRMED | Neither other party found it. `tsc` catches it in seconds, hence Low — but T10 bothers to note which imports *already* exist, which makes omitting the one that does not conspicuous |

**Score for the dual-review rule.** Codex-only would have shipped a plan whose money-path test goes
red in CI on merge (High 1), with two unmarked non-verbatim quotes and a missing import step.
Claude-only would have shipped the wrong severity on the file-header Blocking, since Claude scoped
it to T12 as well and neither half traced it to T11 or swept the class. **Each half caught something
the other could not, on the same commit, from the same prompt.** That is the third time this project
has measured it (`docs/reviews/` passim, and the `dual-review-halves-are-not-redundant` memory).

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

### Writing T11's header surfaced two more defects in the same block

Neither was reported by any of the four rounds, because T11 was never in a round's scope:

- **`ctx` was used free in all four tests, and a `beforeEach` would have been the WRONG fix.** The
  repo idiom is per-test — `sync-run.int.test.ts:25,48` and `e2e.int.test.ts` each open with
  `const ctx = await makeOwnerContext();`, because every call mints a new user and a shared `ctx`
  would leak state across tests. Writing the header naively would have introduced a fixture bug.
- **`RecordingBlobStore` is invented** — used once at 26f (plan:2341) and defined nowhere. That is
  the **fourth** invented identifier in this plan's history, after `rawList` (v1) and
  `receiverEnvelope` (v2). It is now written out, modelled on `FailPromoteBlobStore`
  (`tests/integration/helpers/cloud.ts:168`), including full-surface delegation and `copy` routed
  through `this` — a narrower decorator would silently change the store the code under test sees.

### T14 — a helper described in prose instead of written

`ingestViaHandler({ title })` is the task's most complex helper: it creates a user, signs in, seeds
a playlist, builds the job, and runs `makeSummaryHandler(admin())(job, mockCtx)`. The plan gives it
**one paragraph of prose and no code**, which is exactly what the plan's own governing rule forbids
("code blocks required for code steps"). All five tests in T14 call it. **Blocking**, same class.

*(Checked and CLEARED: T14 appears to call `ingestLocal`, `serveSummary`, `ledgerTotal` and
`EXPECTED_ONE_SUMMARY_COST` — the identifiers Task 0 declares dissolved. It does not. Those occur
only in the "v2 called" column of T14's own disposition table, explaining what was replaced. A
mechanical scan flagged it; reading it cleared it.)*

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
checks citations mechanically or by eye.

⚠ **CORRECTION.** An earlier draft of this section said *"neither half found it."* **That was written
while the Claude half was still running, and it is wrong.** The Claude half found it independently —
its **LOW 2**, *"round 3's line-reference fix took; four neighbours in the same table did not"* — and
found one the coordinator's sweep MISSED: the `Ctx` interface's declaration of `syncDeps`, cited at
`:66`, which is a mid-docstring line; the declaration is at `:69`. Codex did not find it.
**Total: SEVEN wrong citations, from two sweeps that each missed something the other caught.**

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
| `Ctx.syncDeps` declaration — `helpers/cloud.ts:66` | 69 | −3 — **found by the Claude half, missed here** |

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
