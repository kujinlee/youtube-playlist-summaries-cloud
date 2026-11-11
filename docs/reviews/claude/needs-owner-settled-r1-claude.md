Reviewed head: 435ef151c73ea64c393461072537b30e5d4c9c85

# needs-owner-settled — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` on branch `needs-owner-settled` (PR #528, backlog #496): clauses 1 and 2 in
`scripts/goal-tree.py` `needs_from_backlog`, `git_head_when_marked`, the 11-03 fixture and 13 new mutations.

`python3 scripts/goal-tree.py --self-test` → **430/430 passed** (1.4 s).

## What I tried to refute, and what held

All of these were measured with harnesses outside the repo that import the script as it is at HEAD.

| Claim / probe | Result |
|---|---|
| The row's proposed predicate alone misses backlog #384 | **HOLDS.** At `11a70deb`, clause 1 flags only backlog #306. Backlog #384 is reached only by clause 2. |
| 11-03 corpus: 2/2 hit, 0 false positives, 4 adjacent open rows unflagged | **HOLDS.** Run against REAL git history (not the fixture's table) on `git show 11a70deb:docs/backlog.md`: 306 → clause 1, 384 → clause 2, and 2, 86, 198, 307 → None. That took 10 git calls and 3.6 s. |
| 18 flags over the daily revisions, all settled | **HOLDS.** I took the last commit per day, 10-24..11-05, plus `11a70deb`: 3+3+3+3+4+2 = 18 flags, covering backlog #90, #194 and #306 (clause 1) and backlog #384 (clause 2). I read #90 and #194 at `b6c3c0bb`: each records the owner's answer after its marker. My row-revision count is 118, not the builder's 136, because the day boundaries differ. The flag count is the same. |
| **Clause 2 false positives from unrelated head rewrites** (a typo, a renumber, a merge rewrite, an IN PROGRESS tick) | **None found, over a much denser corpus than the builder's.** I took EVERY commit to `docs/backlog.md` since 10-23: 115 revisions, 1131 listed row-revisions, 34 distinct (row, segment) pairs. Clause 2 fired on exactly one pair: backlog #384, from `fd804427` (11-02 11:44) to `11a70deb`. The row records the walkthrough at 11-02 09:20–09:40, so that is a true positive. Clause 1 fired on #306 (47 revisions), #90 (43) and #194 (43), and nothing else. |
| Pickaxe hits the WRONG commit (a duplicated segment, another row) | **None.** For all 35 segments, the oldest `-S` commit holds the segment inside that row's own status. No revision contains any segment twice. |
| A marker removed and then re-added | No re-add was observed. 27 segments match 2 commits, and each pair is the add and then the later removal when the row was answered. Taking the oldest commit is right for all of them. A re-add of identical text would anchor to the first add. That is not measured; see F7. |
| History unreadable | **Loud** at `head_moved_on`. In a directory that is not a git repo, the row reads `its history was NOT READ (git log -S exited 128: fatal: not a git repository …)`. See F1: the git path's own raises are not pinned. |
| Shallow clone | **Silent miss**, measured on a synthetic repo (F4). |
| Cost | Grows with the number of listed rows. I could not measure `--snapshot --print` on HEAD (F3). |

## Findings

### F1 — Medium — no test pins that a failing git call in the real history reader reports NOT READ
`scripts/goal-tree.py:718` and `:724`

**Scenario.** Someone changes either `raise ValueError(...)` in `git_head_when_marked` to `return None`. Typical reasons are "a failed show just means not found" or an over-eager refactor. After that, a `git log -S` or `git show` that fails because of a timeout, a lock, or a missing object is silently read as "the marker was never written". Clause 2 goes quiet on every row, which is exactly the outcome the docstring forbids with "⛔ A history that cannot be read is said, never taken as 'unchanged'". The suite stays green.

**Evidence.** I ran my own mutations on a temp copy:
- mutation A (`git show` failure → `return None`) leaves the suite at **430/430**;
- mutation B (`git log -S` failure → `return None`) leaves it at **430/430**.

The only NOT-READ case (`_boom`) injects a raising `history` lambda. It never exercises `git_head_when_marked`. The collect-level case (`:3602`) fakes only rc=0 answers. None of the 13 new manifest entries targets these two lines.

**Fix.** Add a collect-level case whose fake `git log --reverse` returns rc 128, and a second where `git show` does. Assert that the row's flag starts with `its history was NOT READ`.

### F2 — Medium — nothing pins what the real git reader compares, so a reader that flags every row passes
`scripts/goal-tree.py:726`

**Scenario.** `git_head_when_marked` returns the old row's FULL status instead of `status_head(...)`. That string almost never equals today's head, so clause 2 would flag every listed row whose marker sits after a ⟳. That is a "may already be settled" on every open ask. The suite stays green.

**Evidence.**
- Mutation E (`return row["status"] if row else None`) → **430/430**.
- The one git-path case only feeds a fixture whose head DID change. No git-path case has an unchanged head, so a reader that always disagrees passes it.

Two weaker survivors come from the same gap:
- Mutation G (`marker_segment` uses `find` rather than `rfind`, so the FIRST marker's segment) → 430/430. Only a status with two markers can tell `find` from `rfind`, and no case has two.
- Mutation F (dropping the `-- docs/backlog.md` path filter) → 430/430.

**Fix.** Add one collect-level case where `git show` returns the same head as today and the expected flag is None. That kills E. Add one status with an older answered marker and a newer open marker. That kills G.

### F3 — Medium — clause 2 runs serial git calls on every refresh, measured at 19–33 s on a realistic backlog
`scripts/goal-tree.py:712-727`, `:1021`

**Scenario.** `collect` builds the NEEDS YOU list on every `/goal-tree` refresh, and the bare invocation is the page's Refresh button. For each listed row whose marker sits after a ⟳, clause 2 makes two git calls: a full-history `git log --reverse -S` (≈0.6 s each, measured twice) and a `git show`. Each call has a 30 s timeout.

**Evidence.** Time to run `needs_from_backlog` with the real git reader:

| Backlog revision | Listed rows | Git calls | Time |
|---|---|---|---|
| `1b4b74d3` (10-26) | 28 | 56 | **19.4 s** |
| `d678369d` (10-27) | 28 | 56 | **33.0 s** |
| 11-02 | 8 | 10 | ≈5 s |
| any of the above, without clause 2 | | | ≈0.13 s |

At HEAD the list is empty: `needs_owner` is false for every row, so the added cost today is 0. The cost returns with the next audit sweep that marks rows NEEDS-OWNER. The 10-26 sweep marked 22. Worst case per row is 2 × 30 s. The cost also grows with history length, because `-S` scans every revision of `docs/backlog.md` (300 so far).

**What I could not measure.** I did NOT run `--snapshot --print` on HEAD. `--snapshot` appends to the main checkout's goal-tree log, which is shared state outside this worktree. The figures above isolate the added step.

**Fix.** Cache `(num, segment) → oldest sha`. That answer cannot change once found, unless history is rewritten. Alternatively, answer every segment in one `git log -p --reverse` pass.

### F4 — Low — in a shallow clone clause 2 skips the check without saying so
`scripts/goal-tree.py:712-727`

**Scenario.** In a shallow clone, the boundary commit diffs as a full add. `-S` therefore "finds" the marker at the boundary, and the head read there is today's head, so there is no flag and no NOT READ. That is a quiet "unchanged", the outcome F1's docstring forbids.

**Evidence.** I built a synthetic repo with three commits:
1. `OPEN then ⟳ NEEDS-OWNER — pick A`
2. `OPEN now ⟳ …`
3. an empty commit

The full clone flags the row. `git clone --depth 1` returns flag `None`.

**Bound.** No caller today runs `collect` in a shallow clone. CI runs only `--self-test`, and its jobs use `fetch-depth: 0`. Hence Low.

**Fix.** Raise (NOT READ) when `git rev-parse --is-shallow-repository` prints `true`.

### F5 — Low — the history is parsed with today's parser, so a stricter parser would break the check permanently
`scripts/goal-tree.py:725`

**Scenario.** `gen-backlog-page.parse` is applied to the file as it stood at the marker commit. If a later change makes `block_error`, `header_error` or the width check reject a shape that old revision had, the `ShapeError` becomes a NOT READ on that row. It would stay NOT READ for as long as the marker stands, because history never changes. The failure is loud, so this is not silent, but nothing can make it go away.

**Evidence.** Today all 35 marker commits parse (0 NOT READ). Mutation I (return `status_head(row["status"])` even when the row is missing) also survives at 430/430, so the "row absent at the marker commit" path is untested.

**Fix.** Read the row at that commit with a tolerant line match (`^| N |`), or state the bound.

### F6 — Low — when clause 1 and a cross-reference both apply, which message wins is not pinned
`scripts/goal-tree.py:821`

**Scenario.** Remove `if it["flag"] is None else []`. A row with clause 1 text that also names a closed `backlog #N` then shows "may already be answered by backlog #N" in place of its own `DECIDED`. It is still flagged, so the effect is cosmetic.

**Evidence.** Mutation C → 430/430. The manifest's "clause 2 runs over a flag clause 1 already set" covers the clause-2 overwrite, not this one.

### F7 — Low — a false clause-2 flag can only be dismissed in ways the message does not mention
`scripts/goal-tree.py:673`, `:707-708`

**Scenario.** The repo rewrites status heads in place, so ordinary progress on a row whose owner question is still open trips clause 2. Examples are `PARTLY CLOSED …` and `IN PROGRESS on branch …`, the shape backlog #496's own head has right now. The code's BOUND says as much. The only remedy the flag offers is "write `NEEDS-OWNER answered`", which would be a false record in that case.

The working dismissal is to re-word the marker's segment or append a fresh `⟳ NEEDS-OWNER — …`. Either one moves the oldest `-S` commit to a revision whose head matches today's. Neither is stated. The same mechanism also means an identical segment that is removed and later re-added anchors to the FIRST add.

**Evidence.** I measured 0 occurrences over 1131 row-revisions, so this is Low.

**Fix.** Extend the clause-2 text: "…or, if it is still open, restate the ask as a new `⟳ NEEDS-OWNER — …`".

## Summary

The behaviour claims reproduce. They hold on a denser corpus than the builder used: every backlog commit since 10-23, not one per day. I found no clause-2 false positive and no wrong-commit pickaxe hit.

The open items are:
- **Test strength:** seven of my ten mutations survive (A, B, C, E, F, G, I; only D, H and J went red). Two of those gaps are on the property the change most needs, NOT READ and "never flags everything", on the real git path (F1, F2).
- **Refresh cost:** an unbounded refresh cost that is invisible today only because no row is waiting (F3).

VERDICT: NOT CONVERGED
