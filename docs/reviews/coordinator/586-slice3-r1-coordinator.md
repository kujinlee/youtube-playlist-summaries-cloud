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
