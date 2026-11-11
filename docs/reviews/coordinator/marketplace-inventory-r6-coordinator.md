# Round 6 — coordinator: the PRE-COMMITMENT, written before the round ran

**Subject:** `marketplace-inventory` (PR #376) at `4d07ee59`. Scoped to the guard code across six
files that no review half has seen — `ae12bb3f..HEAD`: **123 insertions, 140 changed lines**.
⟳ r6 CLAUDE L8: this said *"123 lines"* while the per-file table below gave diffstat CHANGED
totals summing to 140 — two different measurements presented as one figure. Both are now named.

⛔ **THIS SECTION IS WRITTEN BEFORE THE REVIEW IS DISPATCHED, AND THAT IS THE POINT.** This
repository's `proving-a-negative-by-interception-cannot-terminate` records **five unearned passes**
produced by authoring the retreat after seeing the result. So the retreat is authored now.

## The decision, and who made it

The owner chose this shape on 2026-10-17 by selection card, over two alternatives (`NO-REVIEW:`
immediately, and a full unscoped round 6):

> **Round 6 is the LAST review pass on this branch. Whatever it finds is folded once, and then
> `NO-REVIEW:` goes in the pull-request body naming exactly what that fold touched.**

## Why a stop condition had to be pre-committed rather than judged afterwards

`check-review-recorded` **cannot be made green by reviewing**, and this is structural rather than a
quirk: it requires a Codex verdict whose head covers the current tree, and every round's fold is new
code committed *after* that verdict. So the gate re-reds unless a round finds nothing requiring a
change. Measured on this branch: rounds 1–5 each produced code-changing findings, and r5's two
halves produced 13 between them. **Planning to review until the gate is green is planning a loop.**

## What this round is scoped to, and why these six

| file | changed lines (ins+del) | what is new and unexamined |
|---|---|---|
| `scripts/check-canonical-source.py` | +45 | `root_level_cites()` — a newly EXTRACTED function, plus a fixture case over four path spellings |
| `scripts/check-claim-propagation.py` | +42 | the `_VOID_EXPECTED` independent literal and its identity case — a mechanism novel to this repo — plus 8 cases |
| `scripts/mutations/check-canonical-source.json` | +13 | the retargeted normpath mutation |
| `scripts/mutations/check-claim-propagation.json` | +6 | the extended VOID expect list |
| `scripts/check-plan-code.py` | +16 | the ratchet arithmetic, which r5 CODEX already caught wrong once (19 vs 17) |
| `.github/workflows/ci.yml` | +18 | the step rename off a deleted check |

⚠ **The documents in the same range are deliberately NOT the subject.** They are review documents,
memory entries and dashboard entries — records rather than rules — and the substantive document
changes were examined by the r5 Claude half at `ae12bb3f`. ⛔ **The owner was told the cost of that
scoping choice when they made it:** r5 CLAUDE H3, a live false figure on a reader-facing page, was
found by *sweeping* rather than targeting, so breadth has paid on this branch before. Scoping is a
judgement about where the remaining risk is, and it can be wrong.

## The falsifier for this round's own verdict

⭐ **The risk being bought is specific and measurable: guard code written in response to a review is
2-for-2 for containing defects on this branch today** — the r5 Codex fold produced H1, H2 and the
Low, and the r5 Claude half's findings were in code written an hour earlier. If round 6 finds
**zero** findings in these six files, that run of 2-for-2 is broken and the scoping was unnecessary.
If it finds any, the scoping was right and the pre-commitment is what stops the loop.

**Either outcome is recorded here before it is known.**

---

# The Codex half ran — and the pre-commitment's falsifier did NOT fire

`docs/reviews/codex/marketplace-inventory-r6-codex.md` (`gate_ran: true`, head `4d07ee59`, model
`gpt-6-astra`). **NOT CONVERGED: 1 Medium, 1 Low. No Blocking, no High.**

⭐ **The falsifier recorded above said: if round 6 finds ZERO findings in these six files, the
2-for-2 run is broken and the scoping was unnecessary. It found two, both inside the scope, and both
fix-induced. The scoping was right and the pre-commitment is what stops the loop.**

## ⛔ An output-contract violation, caught by the wrapper — rc=3, not a fallback

The wrapper exited **3**: the gate ran and the review was NOT filed. ⚠ **This is not the
fall-back-to-Claude case and treating it as one would have discarded a review that was paid for.**
Cause: the agent **wrote its own file** to the target path, which its brief forbids — *"your final
message IS the review; write no file"* — so the wrapper refused to overwrite it with the capture.

Remedy taken, per `docs/plugins.md`: the **capture** (the final message, 5,231 bytes) is now filed as
the review; the agent's self-written 10,193-byte file is preserved **outside the repo** in the
scratchpad as a report, not as testimony. The verdict is intact (`gate_ran: true`, `refused: false`)
because the target was untracked, so no committed testimony needed protecting.

## r6 CODEX Medium — the root-file predicate pinned a SPELLING for the third time

**Two spellings reached the root file through the consumer while the predicate returned `[]`** —
reproduced independently before folding:

```
../<checkout-name>/CONTEXT.md    predicate []   consumer is_file True   resolves to root CONTEXT.md
/abs/path/to/CONTEXT.md          predicate []   consumer is_file True   resolves to root CONTEXT.md
```

`normpath` cannot remove a **leading** parent segment, because it has no base directory. ⚠ The
absolute case is worse than unstageable: read from inside a staged tree it reaches the **original
checkout**, silently breaching the staging boundary the harness exists for.

**Folded by asserting the PROPERTY instead of a spelling** — resolve the entry the way `audit()`
does (`root / cite_rel`) and ask where it lands. Two arms: *resolves to a file directly in the root*,
and *absolute or resolves outside the root*. Verified: all seven bad spellings caught, both
legitimate nested entries still pass, and no declared entry in the live table is absolute or
parent-escaping (so no false fire).

⭐⭐ **AND MY OWN FIX HAD AN UNPINNED ARM, WHICH THE NEGATIVE CONTROL CAUGHT AND READING WOULD NOT
HAVE.** The absolute arm's mutation did **not** redden, because the absolute input I chose pointed at
a *root-level* file — which the other arm catches anyway. Isolating it required an absolute path to a
**nested** file. That is `exercise-the-producer-at-two-distinct-inputs`, in the form where two arms of
one rule both answer for the same input. Both arms now have a witness and a mutation
(`check-canonical-source` 8 → 9).

## r6 CODEX Low — an audit trail wrong in the one number this round was asked to verify

The comment read `18 -> 19`; no nineteenth mutation exists, because the r5 H1 fix **extended an
existing entry's `expect`** after the harness refused a duplicate anchor. The executable count was
right and the arithmetic comment below it already said `18 -> 18`. **Corrected the comment, not the
ratchet** — the reviewer said so explicitly and it is the right direction.

## Also folded — found by the reviewer outside its two findings

`.github/workflows/ci.yml` described the canon guard's oracle as *"four directories and three
extensions"*. **ADR-0015's `*.html` widening made that false the same day** — it is four — in a
comment the r5 fold did not sweep. Same class as M1 last round: the rename was corrected, the
paragraph around it was not.

## What the reviewer CONFIRMED, which is worth as much as the findings

- ⭐ **The coordinator's claim that deriving the VOID loop is UNSOUND is VERIFIED** — independently
  reproduced 57/57 → 56/56 green after removing `area`. *"The coordinator's objection is valid; no
  escaping vocabulary divergence found."* So the deliberate second copy is justified, and is not an
  instance of `a-second-implementation-of-one-rule-drifts`.
- Removing **each of the 14** VOID members independently fails its own test.
- **Every expectation is red** for all eight canonical mutations and the extended VOID mutation;
  none of the other canonical entries is unfalsifiable.
- The strip case's documented bound holds: identical on today's pages, and through a synthetic
  split-node carrier `audit()` does change — so the narrowed justification is accurate.
- 26 mutations / 26 killed / 26 attributed / 0 survivors, reproduced with all seven `HARNESS_TREE`
  paths staged.

## ⚠ And it qualified a claim of mine that was too broad

I reported **"document guards 54/54"**. The reviewer's separate sweep ran 30 production invocations:
**28 green, two red** — a missing `jest-results.json` and the then-pending round-6 review record.
Both are explained (my sweep deliberately excludes the CI-only invocations that need `--results`,
`--base` and `--mutate`), but **"54/54" was over that runnable subset and I stated it as the
`ci.yml` list.** The qualification is fair and is adopted here.

## Thrashing or prose floor?

Both findings are **fix-induced** — the reviewer traced the invariant's introduction to `ae12bb3f`
with `git log -S`, and the inaccurate history to the same fold. ⚠ But severity **fell** (2 High →
0 High), and `review-method.md:525` requires *"severity stays put"* for thrashing. By `:197` — *can a
redesign remove it?* — neither can: one is a predicate rewrite, one is a comment. **Branch-coverage
and stale cross-reference again, so the architecture review stays un-armed.**

---

# The Claude half ran — 1 High, 6 Medium, 2 Low, all nine folded. And it is RIGHT about the gate.

`docs/reviews/claude/marketplace-inventory-r6-claude.md`. **NOT CONVERGED.**

## ⛔ THE THRASHING GATE IS ARMED, AND BOTH I AND THE CODEX HALF GOT THAT WRONG THE SAME WAY

I wrote *"severity fell, 2 High → 0 High, so not thrashing"*; r6 CODEX reasoned the same way. **Both
of us reasoned over the ROUND. `dev-process.md`'s arming condition is per COMPONENT:**

> two consecutive rounds whose findings came from the previous round's own fix, **in one component**

Taking `root_level_cites()` as the component — one function, rewritten three times in two days:

| round | finding | severity | caused by |
|---|---|---|---|
| r5 CLAUDE | H2 — `"/" not in c` pins a spelling | High | v1 |
| r6 CODEX | Medium — `normpath` cannot strip a leading `..` | Medium | **v2, the r5 fix** |
| r6 CLAUDE | M2 — resolution ERASES the `..`, so the nested class escapes | Medium | **v3, the r6 fix** |

Fix-induced in two consecutive rounds, one component, **severity Medium → Medium**. Both clauses of
the tell are satisfied. ⚠ And this is the second time on this branch that a thrashing judgement of
mine was wrong — `2e79f464` is the first, where I invented the definition. **Here I quoted the right
document and applied it at the wrong GRANULARITY**, which is a different error with the same outcome.

## ⭐ The gate's remedy is a REDESIGN, and the redesign is what this fold did

`review-method.md:199` — *can a redesign remove it?* — answers **yes**, and the reviewer named the
shape: refuse a registration that is not a relative path, free of `..`, under a `HARNESS_TREE`
prefix. **A lexical test over the declared string.** That dissolves M2 and M3 *together*, which no
third arm would:

- **M2**, measured end to end: `../<checkout>/.agents/skills/handoff/SKILL.md` → predicate `[]`,
  live `audit()` `[]`, **staged `audit()` RED** with the exact message the docstring says it exists
  to prevent. `resolve()` erases the `..` that makes the string nonportable.
- **M3**, the opposite direction: `node_modules/typescript/…` — a path the harness **stages** — was
  **falsely refused**, because `node_modules` is a symlink in a worktree and `resolve()` followed it
  out of the tree. ⛔ **That made the guard's verdict depend on the host**: `npm ci` in CI creates a
  real directory, so this machine and CI disagreed about the same registration.

⭐⭐ **THE LESSON, and it is about my own repair:** v3 was *"assert the property, not the mechanism"*
applied to the **wrong property**. The property that matters is **portability of the registration
string into a staged tree**, which is lexical. By resolving, I imported the filesystem's accidents —
symlinks, existence, host differences — into a verdict that should depend only on the text someone
typed. One wrong property, two opposite failures.

**v4 is lexical: three refusals (absolute, a `..` segment, not under a staged prefix), no `stat`, no
symlink following.** Verified 0 wrong verdicts over 9 must-catch and 8 must-pass spellings, the
must-pass set including one per staged prefix so a blanket refusal cannot pass.

⚠ **`STAGEABLE_PREFIXES` is a deliberate second copy of `HARNESS_TREE`** — deriving it is not
available, because `check-plan-code` raises at import outside its package context. So it carries an
**identity case** parsing `HARNESS_TREE` with `ast`, which is the only shape in which a duplicate is
a ratchet. Four witnesses: one per arm, plus one for the prefix drift.

## ⛔ Convening a separate Phase 6 review would repeat a RECORDED error

The gate armed and its remedy — the redesign — **is landed in this fold.** Convening a formal
architecture review now for a component whose redesign is already in the tree is exactly what
`docs/reviews/architecture-review-2026-10-16-claim-propagation.md` found had happened two days
earlier: *the same review ran twice under the same trigger with its redesign already landed.*
**Recorded here as armed-and-answered rather than convened**, and that is a judgement the owner can
overrule.

## H1 — the figure I corrected in the spec, left standing on both pages

The fold fixed `157` at three spec sites and left it at **four sites across the two pages the branch
ships** — in `4d07ee59`, *the commit whose subject is this exact class*, which dated five other
figures on those same pages and walked past this one twice. **Instance-not-class, inside the commit
that was fixing the class.** Both page sites now carry `159` with provenance; swept, and `157` now
appears nowhere unqualified in the spec or either page.

⛔ **AND IT REFUTES MY SCOPING JUSTIFICATION.** The pre-commitment says *"the substantive document
changes were examined by the r5 Claude half at `ae12bb3f`"*. **False** — the page edits happened at
`d06da80c` and `4d07ee59`, both after `ae12bb3f`, so no half had examined them. H1 was sitting there.
⭐ The reviewer named five further figures that commit dated and that it did not verify; **I have now
re-derived all five and all five are correct**: 665 shared at HEAD, 647 at `a4f6d4b5`, 6,542 for the
nine at `a4f6d4b5`, 11,642 total (10,373 + 604 + 665), and 248 product files.

## The rest, folded

| # | Finding | Fold |
|---|---|---|
| **M4** | the arithmetic trail did not close — shown 1476, asserted 1478 | ⭐ **the hand arithmetic is DELETED, not corrected a fourth time.** It was wrong three times in two days (19 vs 17; a 19th mutation that never existed; 1476 vs 1478). Only per-file deltas remain; the total's authority is the `case` that sums the dict |
| **M5** | *"three extensions"* corrected in `ci.yml` and left in the guard's OWN docstring | fixed — ⚠ the guard against second copies was the drifted second copy, missed by the same fold that corrected its sibling |
| **M6** | `ci.yml:330`'s *"the step above"* names the wrong guard after a rename moved a step between the sentence and its subject | now names `check-explainer-delivery.py` — a positional reference in prose, the shape `a-positional-read-needs-a-verified-shape` records |
| **M7** | the §3 producer counts `MEMORY.md` (159) where the component's own `memory_files()` returns 158; and *"already published"* omits that `memory_dir()` is `None` in a clone | both stated in the row: both counts with their definitions, and that the FILES ship while the HARNESS PATH does not |
| **L8** | my own *"123 lines"* vs per-file figures summing to 140 | both named — 123 insertions, 140 changed lines; the table column now says which it is |
| **L9** | *"four directories"* undercounts: the population is four directories **plus the repo root** | fixed at both sites — and this is the second half of the very sentence M5 is about, so the correction had itself been partial |
