<!-- codex-review: model=gpt-6-astra -->

**Major — `scripts/gen-work-lines.py:425–446`: identical children of different parents collapse, hiding outstanding work.**

**Input/state (executed):** A temporary repository with a real linked worktree. Both checkouts contain:

- Different `parent.md` plans, each fully ticked.
- Byte-identical `kid.md` files containing `<!-- parent: parent -->` and an unticked follow-up step.

The children have different meanings: each belongs to its checkout’s parent. The fold merges them before resolving that relationship, then resolves the merged child using only `checkouts[0]`.

**Observed output:**

```text
ROWS [('kid', 'parent @ main'), ('parent @ main', None), ('parent @ side', None)]
STATES [('parent @ main', 'open'), ('parent @ side', 'done')]
OPEN 1
SIDE BANNER > **Line:** _(no objective recorded)_ `parent @ main` → `kid`
```

Running the same fixture against `a3f34d6a` produces **`OPEN 2`**, with each child attached to its own parent. This is a fold regression: the side line falsely appears finished, and its banner gives the wrong ancestry despite using the shared resolver.

**Fix:** Resolve checkout-specific parent identity before collapsing copies. Keep separate rows whenever their resolved ancestry differs, including differences further up the chain. Add this fixture asserting two open lines and the side banner’s correct parent. More generally, equal content alone cannot establish that independently created plans are the same plan; reliable deduplication needs persistent identity or provenance.

Other mandate results:

- **Thread-check placement:** No additional defect found. Turn selection and the already-judged gate still precede it; the original verdict calculation remains intact.
- **Resolver callers:** No separate duplicate-slug resolver found. The failure above occurs before `row_for` can recover the discarded relationship.
- **`GIT_*` removal:** No supported caller relying on intentional `GIT_DIR` redirection found; the function explicitly takes the checkout root.
- **Mutations:** Executed all **19 new/changed entries** through the shipped mutation runner: **19 killed, 19 attributed to their named cases, zero survivors**. They do not cover the ancestry-collapse regression.

Validation in temporary copies: `check-banner-armed` **236/236**, `gen-work-lines` **55/55**, `begin-plan` **121/121**. No real repository/worktree files or `.claude/` state were written.

VERDICT: NOT CONVERGED
