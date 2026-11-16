# Round 4 — `harness-ships-elsewhere-b` — coordinator — ⟳ NOT CONVERGED (Codex); 1 BLOCKER fixed, 1 MINOR filed; the Phase 6 bet LOST

```yaml
round: 4
fixes_nontrivial: true
subject: harness-ships-elsewhere-b
halves:
  claude: gap
  codex: ran
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: true, component: staging, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: isolation, disposition: filed}
```

REVIEW GAP: claude — alternation

Reviewed: PR #594 at `dfaf53a4`, after the Phase 6 redesign (`3e0fc963`). Half:
[`codex/harness-ships-elsewhere-b-r4-codex.md`](../codex/harness-ships-elsewhere-b-r4-codex.md) (1 BLOCKER, 0 MAJOR,
1 MINOR). Round 4 is at the round cap (`docs/review-method.md` §0 Q4c): a finding is FILED unless it is a BLOCKER.
X1 is a BLOCKER and was fixed; X2 was filed.

**The Phase 6 bet LOST.** It said round 4 would find no input where the source decision differs between two paths
the filesystem resolves to one object. X1 is one: with a tracked link `.claude/plans -> ..`, the private root and
the repository are one object, and `secret` (also `alias/secret` through a tracked `alias -> .`, and
`.claude/plans/secret`) was planned to ship. The coordinator reproduced it before the fold. X1 is caused by the
redesign: the parent commit refused the explicit `.claude/plans/secret` declaration.

## Dispositions

| Finding | Severity | Disposition |
|---|---|---|
| X1 — a private root that resolves to the repository bypasses the exclusion | BLOCKER, fix-induced, `staging` | **fixed** in `8c14fd8e` (below) |
| X2 — `measured(world, timeout)` gives each probe a whole timeout, so three probes take three times it | MINOR, not fix-induced, `isolation` | **filed** as backlog #659 |

Codex also noted that three isolation call-site mutations (`_reaches` swapped for `_inside` at the world root, a
HOME entry and a command) were dropped by the redesign while the three guards stay live. Not re-added: the only
cases that tell the two rules apart are the three case-alias filesystem cases, which do not run on case-sensitive
Linux CI, so the mutations could not die there. Each site keeps its `if False` mutation. Named in backlog #659.

## The fix (`8c14fd8e`)

Two rules in `scripts/mkt_stage.py`, stated in the docstrings of `_roots` and `_real`:

1. **`_roots` refuses a root that IS the repository or a directory HOLDING it.** The identity of each private root
   and of the skills home is compared with the repository's and with each of its ancestors'. A match is CANNOT RUN
   at `plan`, whatever is declared, because every file in the repository would be under that root. This is the only
   rule that can see an ancestor (`.claude/plans -> ../..`): the walk never stands above the directory it starts
   from.
2. **`_real` asks about the object the walk STANDS on, every time it stands anywhere.** The forbidden-identity
   check moved from "after stepping onto an object" to the top of the loop, so it covers the root the walk starts
   from, each object stepped onto, the directory a `..` or a link's target returns to, and the object the walk ends
   on. One check, one place.

Why one check at the top of the loop, and not three more checks (start, after a pop, after a link): a pop or a
link replacement only ever returns to a directory the walk already stood on, or to the root. A separate check there
would be a guard no input can reach once the start is checked, and a mutation deleting it could not die.

**Search for the class.** The skills home has the same gap (`.agents/skills -> ..` let `files=scripts/x.py` plan
on `dfaf53a4`): real, closed by rule 1, one case. `mkt_isolate._reaches` (the three preflight sites and the out
directory) does compare its STARTING object: measured in a temporary directory, `_reaches` is true for the checkout
itself, a link to it, `self -> .`, `sub/up -> ..` and a not-yet-existing path under that, and false for the
directory holding the checkout. Not real there; no case added.

Cases: staging 92 → 97 (4 red on `dfaf53a4`, 1 adjacent control green before and after). Mutations: 67 → 70, each
killed by the case it names. Isolation unchanged (71 cases, 53 mutations).

## Thrashing, and the route

Rounds 2, 3 and 4 each carry a fix-induced finding in `staging` (X3, F2, X1). Phase 6 already convened after round
3; its stated next route if the bet was lost is `split`: staging stops accepting links in a declared path. The
coordinator folded the BLOCKER instead and continued. One fact bears on that choice: `split` as written would not
have closed X1. `files=["secret"]` holds no link in the declared path; the link is the private root itself. A
`split` would need the rule "a private root must be a real directory below the repository" as well, which is rule 1
above in a stricter form.

The decision-log row for this round is recorded with `route: accrete`, as the two earlier rows of this subject
are: `check-decision-scheme.py` keys its ladder on (subject, unit), each round's unit is a new string, and it
refuses any other first route for a new unit. The unit it names is the Phase 6 redesign.

## Round-5 bet

**Round 5 finds no input where a file whose only path from the repository root passes through a private root's
object is planned to ship**, and nothing caused by this fold in `staging`. Falsified by one such input. The stated
bounds are unchanged (another filesystem, a tree changed during staging, a destination alias beyond case and
canonical form). If lost, the route is `split` with the stricter root rule above.
