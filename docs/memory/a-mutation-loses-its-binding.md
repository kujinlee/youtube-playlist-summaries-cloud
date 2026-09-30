---
name: a-mutation-loses-its-binding
description: "FIRES-WHEN: refactoring code mutation entries anchor to, or promoting a mutation — ⭐ A mutation stops measuring when the code moves under it: anchors bind by TEXT so a refactor ORPHANS them, and promoting a mutation into CI leaves its protection (the fake-$HOME redirect) behind"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `a-refactor-orphans-the-mutation-guarding-it`, `promoting-a-mutation-leaves-its-protection-behind`

## a refactor orphans the mutation guarding it

**MEASURED TWICE IN ONE DAY, 2026-09-01.**

1. **PR #197 → red on master (`86ecade5`, repaired by PR #198).** The backlog-#80 palette retune
   changed a colour token; a mutation in `scripts/mutations/page_chrome.json` anchored on the old
   value. Anchor gone → mutation not applied → CI **FAILED** on the trunk.
2. **`fix-no-entry-emphasis`.** Collapsing two copies of `startswith(NO_ENTRY)` into one
   `_declaration_reason()` helper deleted the text that **two** mutations anchored on
   (`head path skips the indent check`, `line-leading rule removed`). The harness refused both:
   *"anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless"*, and
   reported **FAILED** rather than a clean run with two fewer mutations.

**Why:** a mutation is coupled to the code by **literal text**, not by meaning. Improving the code —
deduplicating, renaming, retuning a constant — is exactly the operation that breaks that coupling.
Nothing local looks wrong: the code is better, the manifest count is unchanged, and **the suite stays
green** (104/104 throughout, in case 2). Coverage evaporates with no signal at the site of the change.

**How to apply:**
- **Any edit to a line a mutation anchors on is a two-file edit.** After touching guard code, grep
  `scripts/mutations/*.json` for the old text *before* running anything.
- Repair by **preserving the mutation's INTENT, not its text** — re-point it at the new code so the
  *same named case* still goes red (delete the indent guard; accept the marker mid-line). A repair
  that changes which case fires is a different mutation wearing the old name.
- **"Anchor not found" must be FAILED, never skipped.** A verdict from a mutation that never applied
  is worse than no verdict — this is the whole reason the harness refuses by name.
- ⚠ Related trap from the same run: an `expect` naming a case that **cannot** go red is rejected too
  (`NO-ENTRY reason is echoed` asserts a SUBSTRING, and the un-stripped value still contains it).
  A mutation whose expectation is vaguely right proves nothing.

## ⟳ 2026-09-08, backlog #91 — the SAME mutation orphaned TWICE, one commit apart. A HOT LINE.

Two consecutive review-round fixes rewrote the same expression in `check()`'s honest-zero return, and
each rewrite orphaned `the plan-mode HONEST ZERO becomes a refusal (r3 B2 successor)`:

| | fix | anchor became |
|---|---|---|
| r1 H2 | `Measured(declared=0)` → branch on `muts` | orphaned |
| r2 H3 | `if not muts` → `if not muts and not mut_unreadable` | orphaned **again** |

**Both times `--self-test` stayed GREEN** (201/201, then 207/207) and only the full `--mutate .` saw
it: `358 of 359 … NOT MEASURED`, rc=1.

**The new part is WHY, and it generalises.** The anchor quoted *the branch expression under active
revision* — the one line every fix to that logic must touch. An anchor on a hot line is not unlucky;
it is **guaranteed** to be orphaned by the next fix, and the only instrument that notices costs a full
sweep (~10 min). Prefer an anchor that quotes something the fix will NOT rewrite — a constant, a
message string, a signature — or accept that the entry needs re-pointing every round and say so.

⚠ The silver lining is the design validating itself: what refused the tally was the CARDINALITY
CLAUSE, one of the three the same change moves into `Measured.__post_init__`. 358 verdicts for 359
declared means no `Measured` can exist, so the run prints NOT MEASURED instead of a clean-looking
tally. The harness caught its own refactor breaking itself, twice, using the rule being hardened.

Related: [[a-mutation-loses-its-binding]], [[what-mutation-testing-proves]],
[[assert-the-property-not-the-mechanism]], [[a-report-format-is-a-contract]],
[[measure-the-population-the-code-actually-sees]].

---

## ⭐ THIRD INSTANCE, 2026-09-09, AND IT IS THE INVERSE — the deletion orphaned the CASE, not the anchor

`retire-plan-mode` PR 2 (#271) deleted plan mode's parser, runner and 143 of its cases.
CI went red: **3 mutations SURVIVED + 2 `expect` fields matched 0 red cases**, over a
local suite sitting at **74/74 green** with all seven doc/ratchet gates rc=0.

**The anchors all still resolved.** What broke was the other end. Those five mutations
guard `run_mutations` / `run_suite` — code the slice does not touch — but each one's only
red case was a **plan-mode case** that reached those functions end-to-end through
`check(plan)`. Delete the caller and the alarm goes, while the thing it guarded keeps
running unwatched.

**So the question to ask before ANY deletion is two-sided:**
- does this delete an anchor a surviving mutation needs? (instances 1 and 2)
- does this delete the only CASE that can go red for a surviving mutation? (this one)

Nothing local can see the second. `--self-test` is green by construction — the case is
gone, so it cannot fail. Only `--mutate .` compares the two ends.

⚠ **The tempting repair is the wrong one.** The slice was already retiring 20 mutations,
so retiring five more looked consistent. It is not: those 20 go because their **subject**
is gone; these five subjects still ship. Retiring them shrinks real coverage inside the
one change whose whole discipline is *coverage falls only with its subject*. The repair
is to re-anchor the property onto a case that drives the surviving function **directly**.

**The general form, worth more than the instance:** a case that reaches a rule through two
layers of someone else's parser is a case that dies when that parser does. Coverage routed
through a caller is coverage held hostage to it. See [[assert-the-property-not-the-mechanism]].

## promoting a mutation leaves its protection behind

**The protection was in the HARNESS, not in the mutation — so promoting the mutation dropped it.**

Round 1 of PR #178 rebuilt `_write_sandbox` so `--mutate .` could never again overwrite the user's
`~/explainers/dashboard.html`. To prove the sandbox worked I wrote a hand battery containing the
mutation *"call `_self_test` WITHOUT the sandbox"*, and I ran it under `env HOME=<tmp>` **because I
could see it would otherwise hit the real page.** I wrote that reasoning down in the same turn.

Then I lifted that mutation verbatim into `scripts/mutations/gen-dashboard.json` — where it is run
by CI, with the real `HOME`. `OUT_DEFAULT` is `pathlib.Path.home() / "explainers" / "dashboard.html"`:
**absolute, so running `--mutate .` from a temp copy of `scripts/` does nothing to protect it.**

Round 2's Claude half found it. REPRODUCED with a sentinel file under a fake `HOME`:

| | |
|---|---|
| entry 39 + one `--out`-defaulting case | `SENTINEL INTACT=False` — destroyed |
| sandbox intact, same case | `SENTINEL INTACT=True` |

Harmless *that day* only because no case let `--out` default — and `_write_sandbox`'s own docstring
invites the next author to write one (*"a case written later inherits the sandbox"*). See
[[a-test-that-cannot-fail]] for the sibling shape.

## The habit

**When moving a check from a scratch harness into a permanent one, ask what the HARNESS was
providing that the check itself does not.** Redirected env, a fake HOME, a temp cwd, a scratch clone,
a stubbed credential — those are part of the test, and they do not travel with the diff.

**And ask whether the mutation needs to be that dangerous at all.** It usually does not. Entry 39
never had to *disarm* the sandbox to fail the case it names — handing the suite a `real_out` that
disagrees was enough, and is red via the same case. **Prefer the weakest mutation that still fails
via the case it names.**

**A guard that reproduces the incident it guards is worse than no guard**, because it runs on a
schedule and nobody re-reads it. This is [[after-fixing-search-for-the-class]] pointed at my own
instruments rather than at product code, and [[an-instrument-that-edits-the-repo-corrupts-its-peers]]
one layer further out — that one harmed a peer reviewer; this one would have harmed the user.

## The falsifier I should have written first

Enumerate every manifest entry, apply it with a case that exercises the dangerous default, run under
a fake HOME with a sentinel, assert the sentinel survives — **and control the instrument by
restoring the old dangerous form and confirming it reports a breach.** 47/47 clean, control = 1
breach. A "0 breaches" from an instrument that cannot detect one is an assertion in better
packaging ([[a-convention-catches-what-you-read]]).

