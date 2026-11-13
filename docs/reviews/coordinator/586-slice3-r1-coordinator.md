# Round 1 — `586-slice3` — coordinator — both halves NOT CONVERGED; every finding goes to the fold

Subject: branch `586-slice3` (no PR yet, because its base, slice 2's PR #565, was still in CI), reviewed head `42ba603d`.
Halves:
- `docs/reviews/codex/586-slice3-r1-codex.md`: 3 Major.
- `docs/reviews/claude/586-slice3-r1-claude.md`: 1 Major, 1 Minor.

Every finding is a FAIL-OPEN in the cross-run record, the part of slice 3 that decides whether one guard's write
reaches another guard's read.

```yaml
round: 1
fixes_nontrivial: true
subject: 586-slice3
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: cross-run-record, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: cross-run-record, disposition: fixed}
  - {id: X3, severity: Major, aim: deliverable, fix_induced: false, component: cross-run-record, disposition: fixed}
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: cross-run-record, disposition: fixed}
  - {id: C2, severity: Minor, aim: deliverable, fix_induced: false, component: cross-run-record, disposition: fixed}
```

## The class, not the instances

1. **The cross-run sets are a view built for something else.** `record_from_log` builds `wrote`/`named`/`listed` from
   slice 2's `kept` list, which was filtered for READ selection. It drops any path with a `.git` component (C1 J, I, B).
   It also drops an open's argument path whenever the kernel's label replaces it, so a symlink a peer planted goes
   unseen (C1 S). Socket paths are added after `resolve_log`, so they skip its link refusals (X3). Fold rule: the
   cross-run sets come from every path the trace NAMED, before any selection filter, and socket paths go through the
   same resolution and refusals as every other path.
2. **Comparing paths exactly where the meaning is a subtree.** A write to a directory (rename, chmod, mkdir) is compared
   to reads by exact equality, so a read of a descendant is missed (X1). The ancestor rule existed for listings only.
   Fold rule: a write to D conflicts with any read, probe or listing at, below or above D.
3. **Text read where the meaning is structural:** `"@state"` (a relative file name) was taken for `@"state"` (an
   abstract socket) (X2). A write on a descriptor with no label recorded nothing (C2). Fold rule: only the unquoted
   `@"…"` form is abstract. An undecorated write descriptor refuses as `unresolved path`.

A false refusal is safe, so the fold should prefer refusing to modelling.

## Also to file in this PR

Four guards call `io_uring_setup` on the runner (measured by the build). With io_uring denied, `peer trace
incomplete` refuses every guard, so slice 4 would skip nothing until it records with `UV_USE_IO_URING=0` set. This
goes in a backlog row, owned by slice 4.

## Next

A fresh fold agent first turns every reviewer input above into a failing self-test case, then fixes the code. After
that, round 2 runs ONE half (alternation).

## How the fixes were proved

**Before → after.** Every reviewer input (X1–X3, C1 J/I/B/S, C2) and an adjacent control for each became a self-test
case before any code changed. Run with the round-1 code (HEAD `df8cdcbe`) under the new tests: **258/282** passed, and
the 24 failures are exactly the new reviewer cases plus the rewritten X2 case. After the fix: **282/282** (the slice-2
cases unchanged). The baseline before this round was 250/250.

**The fix, by class.**
1. *A view built for something else.* `_resolve` now returns two lists per call: `kept` (the read view, unchanged)
   and `every` (each path the trace named, `.git` included). The cross-run fields `wrote`, `all_named` and
   `all_listed` come from `every`. A labelled open's argument is kept as a SHADOW path: it is named for the cross-run
   check, it skips the label-replaced checks (`..`, `/proc`, links), and it is left out of reads (C1 J, I, B, S).
   Socket `sun_path`s go through `_named`, so they get slice 2's resolution and refusals like every other path (X3).
2. *Exact equality where the meaning is a subtree.* `_meets(n, w)` is true when the two are equal, or either one is
   an ancestor of the other. `cross_run` uses it for every name, and `all_listed ⊆ all_named` covers listings (X1).
   `_cross_forms` adds `copy:` for a path above the copy, so a probe of `/tmp` meets a write in the copy.
3. *Text read where the meaning is structural.* Only the unquoted `@"…"` is abstract; a quoted `"@x"` is a relative
   name and refuses as `unresolved path` (X2). Any call in `FD_OPERANDS` with an undecorated descriptor operand that
   is not known to have failed refuses as `unresolved path` (C2). This covers both sides of a transfer and the
   read/list/stat calls too, because a missed read is the same fail-open.

**Mutations.** 184 → **203**. A refactor orphans an anchor, because anchors bind by exact text; 22 were re-bound in
place, and 19 were added for the new branches (SHADOW, the cross-run view, each `_meets` direction, `_cross_forms`,
the bare-descriptor rule and its operand table). The pin `expected_mutations.py` is now 203. `check-plan-code.py
--mutate . --only scripts/strace_reads.py`: 203 killed, each by the case it names, **0 survivors**. The first run
attributed 201 of them: the adjacent "labelled open's argument" case used an argument outside the staged roots, so
it could not see a leak, and it was moved inside `docs/`.

**Flagged for slice 4's measurement.** `_meets` reads "at, below or above" literally for reads and probes as well
as listings, and an ancestor of the copy stands for the whole copy. Both can only add refusals (safe), but they may
refuse broadly on real logs. Slice 4's first real-corpus run should count them.

Also filed: backlog #622 (`UV_USE_IO_URING=0`, owned by slice 4).
