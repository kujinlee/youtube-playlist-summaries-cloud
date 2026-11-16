Reviewed head: eca9ada3e81ac7e2d6eb6cd615287a30b2e7cf96

# Adversarial review — `harness-ships-elsewhere` slice B, round 5 (Claude half)

**Subject:** PR #594 at `eca9ada3`. The round-4 fold is `8c14fd8e` (code: `_roots` refuses a private root or skills
home that is the repository or a directory holding it; `_real` checks the object it stands on at the top of every
loop turn) and `eca9ada3` (records). I diffed it against `dfaf53a4`.
**Mandate:** refute "Codex r4 #1 is closed for every shape, the new rule refuses nothing legitimate, and nothing in
`staging` is caused by the fold". Every fixture below is a temporary git repository I built in my scratch space.
Nothing under `.claude/plans/` of the real repository was read.

## Verdict: **CONVERGED**: 0 BLOCKER, 0 MAJOR, 0 MINOR

**The round-5 bet holds.** I found no input where a file whose only path from the repository root passes through a
private root's object is planned to ship, and nothing in `staging` caused by this fold.

## Gates run (results)

| Check | Result |
|---|---|
| `python3 scripts/mkt_stage.py --self-test` | `LIVE ok: the written marketplace.json passes claude plugin validate …; not in the count below` / `97/97 self-test cases passed` |
| `python3 scripts/mkt_isolate.py --self-test` | `71/71 self-test cases passed` |
| Pin vs manifest | `scripts/mutations/mkt_stage.json` holds 70 entries; `EXPECTED_MUTATIONS["scripts/mkt_stage.py"]` is 70 |
| The 3 new mutations, each applied by hand to a copy of `scripts/` (each edit's anchor matches exactly once) | `if False` (holding) → 94/97, the named case red; `(top,)` only → 96/97, the named `../..` case red; `if cur and …` → 96/97, the named `_real` start case red |
| `python3 scripts/check-features.py` | `feature map: 29 nodes …; 15 anchors and 23 backlog areas all claimed exactly once` |
| Backlog #659 | well formed (area `(tooling)` claimed, `⟦kind: defect⟧`, size S, status cell), carries `**Fails if:**` with two observations |

## Q1 — is Codex r4 #1 closed for every shape? (calling `plan()` directly)

| Fixture (all links tracked unless said) | `files=["secret"]` | `files=["scripts/x.py"]` |
|---|---|---|
| `.claude/plans -> ..` | REFUSED (`.claude/plans is the repository …`) | REFUSED (same) |
| `.claude/plans -> ../..` | REFUSED | REFUSED |
| `.claude/plans -> ../a`, `a -> .` (two hops) | REFUSED | REFUSED |
| the same, `a` UNTRACKED | REFUSED (`_roots` follows with `os.stat`, tracking is irrelevant) | REFUSED |
| `.claude/plans -> ../../repo` (leaves and re-enters) | REFUSED | REFUSED |
| `.claude/plans -> <absolute path of the repo>` | REFUSED | REFUSED |
| `.agents/skills -> ..`, `-> ../../repo` | REFUSED (`.agents/skills is the repository …`) | REFUSED |
| `.claude/plans -> .` (the root is `.claude` itself) | STAGED — correct, `secret` is not under `.claude` | STAGED — correct |
| `.claude -> .` (so `.claude/plans` is `plans`, absent) | STAGED — correct, nothing is there | STAGED — correct |
| `.claude/plans -> ../scripts` (control from r3) | STAGED — correct | REFUSED (`is under .claude/plans (scripts)`) |

## Q2 — over-refusal

An ordinary `.claude/plans/` directory with a file in it, a `.claude/plans` link to a sibling OUTSIDE the
repository that does not hold it, and a repository with no `.claude` at all each STAGE `scripts/x.py` and skill
`.agents/skills/s`. No false refusal.

Observation, not a finding: a private root that links to a directory far ABOVE the repository (for example the home
directory) is now refused whole. That is the stated rule (every file here would be under the private root), not an
accident, and it is not a configuration a real author would ship.

## Q3 — is the top-of-loop check ever too late?

I looked for a read or decision made between standing on an object and the next turn's check. Between them the loop
only (a) `lstat`s a child, (b) on a link, calls `_tracked_as` (a dict lookup) and `os.readlink` on a link whose
PARENT was already checked, then resets `st` to that checked parent, or (c) on `..`, resets `st` to an ancestor. A
link's own `lstat` identity is never in `forbidden`, because `_roots` stores the FOLLOWED identity (`os.stat`); a
private root that is a hard-linked file is refused by `st_nlink > 1` anyway. The final object is checked on the last
turn before `break`, so the regular-file test after the loop runs on a checked object. `_tree` calls `os.listdir`
only on a directory `_real` already returned. The fold's claim holds: a separate check after a pop or link
replacement could not be reached once the top of the loop checks.

Note on the first mutation (`if False` in `_roots`): with it, the repository's identity enters `forbidden` and the
walk still refuses; the case dies because it asserts `_roots`'s message (`is the repository`). Two layers refuse the
same input, and the mutation proves the first one is the one answering.

## Findings

None.

VERDICT: CONVERGED
