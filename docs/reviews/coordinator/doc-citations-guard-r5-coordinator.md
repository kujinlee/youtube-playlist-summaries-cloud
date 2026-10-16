# Round 5 — `doc-citations-guard` (backlog #291) — coordinator

Both halves ran against the #291 rebuild. Filed after the Codex half landed, because a coordinator
document for a round whose halves are incomplete makes `check-review-rounds.py` exit 1.

```yaml
round: 5
fixes_nontrivial: true
subject: doc-citations-guard
halves:
  claude: ran
  codex: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: manifest-retirement, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: false, component: index-state, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: cited-file-reader, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: false, component: suite, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: true, component: blob-reader, disposition: declined}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: base-selection, disposition: declined}
  - {id: M6, severity: Medium, aim: deliverable, fix_induced: false, component: cited-file-reader, disposition: fixed}
  - {id: M7, severity: Medium, aim: instrument, fix_induced: false, component: declared-counts, disposition: fixed}
  - {id: M8, severity: Medium, aim: instrument, fix_induced: true, component: delivery-figures, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: stale-prose, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: git-invocation, disposition: declined}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: git-invocation, disposition: declined}
  - {id: L4, severity: Low, aim: instrument, fix_induced: true, component: manifest-retirement, disposition: fixed}
  - {id: L5, severity: Low, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: L6, severity: Low, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: L7, severity: Low, aim: instrument, fix_induced: true, component: stale-prose, disposition: fixed}
  - {id: L8, severity: Low, aim: deliverable, fix_induced: false, component: one-oracle, disposition: declined}
  - {id: L9, severity: Low, aim: deliverable, fix_induced: false, component: cannot-run, disposition: fixed}
  - {id: L10, severity: Low, aim: deliverable, fix_induced: false, component: resolution-oracle, disposition: declined}
  - {id: XH1, severity: High, aim: deliverable, fix_induced: true, component: path-decoding, disposition: fixed}
  - {id: XH2, severity: High, aim: instrument, fix_induced: true, component: manifest-retirement, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: blob-reader, disposition: fixed}
  - {id: XM2, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
```

## Verdict: NOT CONVERGED — 4 High across the two halves

## ⭐ THE RESULT: THE COMPARISON SURVIVED, AND THAT IS NEW

Both halves attacked the #291 rule directly and neither broke it. Independently, with different
methods — the Codex half replayed history through a temporary `GIT_INDEX_FILE` and `read-tree`
rather than the blob reader the Claude half used — they reproduced every figure:

| figure | Claude half | Codex half |
|---|---|---|
| last 40 commits | 9 firings, 3 commits, 0.23/commit | same, same four-commit table |
| the old line rule, for comparison | 10, 4 commits, 0.25 | same |
| living corpus | 111/895 = 12.4% | same |
| reviews excluded | 96.7% | 96.7%, absolutes moved as documented |
| ranges / fenced | 369/895 · 56/895 · 41/879 | same |

**The figure the scope decision rests on holds under two independent derivations.** That is the
first round in five where this guard's CORE was not the defect.

## ⛔ WHAT THE ROUND FOUND INSTEAD: FOUR DISTINCT WAYS COVERAGE WENT SILENTLY MISSING

All four are a check that measured the FORM of coverage instead of constructing an input where the
property fails. Listed together because the pattern is the finding:

| # | shape | how it was found |
|---|---|---|
| 1 | **Ambient cases** — a fixture satisfying a case for a reason other than the property named. Twelve on this file | flipping what the case names |
| 2 | **A shadowed refusal** — a new check caught what an older one guarded, so the older one's mutation went from killed to SURVIVING with nobody touching it, suite green throughout | the mutation sweep |
| 3 | **Retirement by anchor** — SIX live mutations retired by asking *"does this anchor still bind?"* when the question was *"does this property still exist"*. They differ exactly when code MOVES, which is what a rebuild does | both halves, independently; the sixth only by Codex |
| 4 | **A near-miss declaration** — `--self-test runs N cases` where the canonical form is `--self-test # N cases`. One missing `#`, so `declares()` returned FALSE and the file was not "a script that declares a count" at all. The guard's own loud rule (*declares but unpinned → FAIL*) could not fire either | the Claude half |

### ⛔ Shape 3 has the sharpest evidence, and it is in my own words

The comment above the split statement still reads:

> ⚠ TWO STATEMENTS, because the fix has TWO INDEPENDENT HALVES and each needs its own mutation
> anchor

I wrote that hours before retiring both of its entries. I had split the statement in two
*specifically* so each property could be measured, said so in the code, and then retired both
because their anchors had moved. **The failure was not forgetting — it was asking a mechanical
question in place of reading.** Four clause-splittings happened in one day for exactly this reason
(`pair_source`/`paths`, `last_line`/its comparison, `hunkless`/its refusal, `raw`/its split), each
with a comment explaining why both halves needed an entry.

⤳ **THE RULE THAT FOLLOWS:** when an entry's anchor stops binding, READ THE CODE AT THE NEW
LOCATION. A moved anchor and a deleted subject are indistinguishable from the manifest alone, and a
rebuild produces the first far more often than the second. Where the code argues for its own
coverage, that comment is the answer.

### ⛔ Shape 4's consequence, stated plainly

For this file's entire life — four rewrites in one day, 41 → 58 → 74 → 64 → 72 cases — no outside
observer ever verified the count, and **64 was committed against a suite running 67**. The guard
existed, was green, and was looking elsewhere. A near-miss declaration is SILENT, not wrong, which
is worse: a wrong number gets corrected and a missing one gets no attention at all.

## The Codex half's own contribution: three of its four were MY fixes

| id | finding | shipped by |
|---|---|---|
| XH1 | `text=True` on git's NUL-delimited path stream translated a CR inside a FILENAME into a newline, so the blob lookup asked for a nonexistent path and the staged document read as DELETED — a real fail-open | the #291 rebuild |
| XH2 | the SIXTH live retirement: accepting an ordinary cited code symlink, which I assumed the directory mutation covered | the #291 retirement pass |
| XM1 | the PRE-image was read before the post-image, so deleting a legacy UTF-16 document returned CANNOT RUN on an ordinary staged deletion | this round's own M3 fix |
| XM2 | two of my new witnesses carried a control that could not DISCRIMINATE | this round's own fixes |

⭐ **XM2 is the one worth carrying forward.** I applied the adjacent-control discipline — every new
witness returns a tuple with a control — but a blank-line citation produces one finding whether the
reader reads the blank line or refuses the file entirely. So a reader returning `None` for every
path satisfied a witness whose comment asserted in those words that it could not. The discipline had
become a SHAPE I reproduced rather than a property I checked, which is an ambient case one level up.
**A control is adjacent only when the degenerate implementation gives a DIFFERENT ANSWER** — so a
control is now a citation that resolves cleanly (0) paired with one that fails (1). Verified: both
of Codex's degenerate substitutions now redden 5 and 13 cases.

⚠ And XH1 was not only where the finding pointed: the same mistake sat in `tracked_files`, which
used `ls-files` with NO `-z`, so git C-quotes an unusual name and a newline splits the list. That
one shows up as a citation silently failing to resolve, which reads like a true finding.

## Three findings DECLINED, with reasons rather than silence

* **M4** — `blob`'s `cat-file -p` handler has no witness and I could not build one: `-e` has just
  answered that the object exists, so a failure means the repository changed between two
  subprocesses. A case would test `subprocess`, not this rule. Recorded as unwitnessed in the code.
* **M5** — `--base` names a TIP, not a merge base, so a branch can be charged for a citation the
  base deleted. Pre-existing, not reachable in CI, now a stated limit.
* **L2 / L3 / L8 / L10** — `--no-color` and `--literal-pathspecs` measurably protect nothing on the
  one remaining invocation (measured byte-identical output), but asserting *"git never colourises
  this"* from one version and one configuration is the overreach that has cost this file several
  rounds, and being wrong costs a CANNOT RUN on every run. A `clean` filter would break "one
  oracle" but is not committable. A citation differing only in case resolves on APFS and not on
  Linux, so the guard is quieter on a Mac than in CI — the safe direction, and real.

## Thrashing

Per finding: **14 of 24 fix-induced**, and three of the Codex half's four were defects the two
Claude folds had shipped hours earlier. That is a fourth consecutive fix-induced round.
⚠ **But the CHARACTER has changed, and that is the thing to weigh.** Rounds 1–4 produced fail-opens
in the deliverable, by five routes through one seam. Round 5's deliverable findings are a filename
decoding bug, an index state, a read order and a path-containment test — four unrelated edges, not
one seam with five doors. The instrument findings dominate (14 of 24 are `aim: instrument`), and the
single defect CLASS that drove four rounds is gone.

## State

78 cases · 37 mutations, 37 killed, 37 attributed to the case each names, 0 survivors · declared sum
1456, each step read from the guard's own `got N want 0` · `check-selftest-counts` now verifies this
file (53 scripts, was 52) · `ci.yml`'s figures corrected after four rounds carrying the first
generation.
