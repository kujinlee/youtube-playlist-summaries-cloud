Reviewed head: 8cb1bf6e952abaab73df7a3e019704494f9b39e8

# Round 3 — `dashboard-retire-spec` — Claude half (adversarial)

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `8cb1bf6e`. The focus was what the r2
fold added: K10, K9's `rstrip` comparison, and K8's seeded self-test. The owner's decisions (§7) were not argued.

**Method.** I built a real git repository in the scratchpad (`r3/k10.py`) holding the r2 fixture as commits: a
base with one narrative entry; a branch commit that adds ask B and `[resolved: 2026-11-25/1]`; a master commit
that adds ask A; and the branch merging master with A first. I then made the merge GitHub synthesises for a pull
request (first parent = master tip, second = PR head; parents checked). K10 was implemented exactly as §3 words
it: `git rev-list --first-parent --reverse <merge-base>..HEAD`, C = the first commit whose store holds the
answer by `raw.rstrip()`, the target compared by `raw.rstrip()`. It used the real `parse_entries` from
`scripts/check-dashboard-entry.py` and the real `unresolved` from `scripts/gen-dashboard.py`. K9 was probed the
same way (`r3/k9.py`).

## BLOCKER

### B1 — K10 passes vacuously in CI, the one place §3 says it runs

§3 (spec line 205) runs K10 in CI as `check-ask-store.py --base "origin/$GITHUB_BASE_REF"` against HEAD. The CI
checkout (`.github/workflows/ci.yml:81`–`:83`) passes no `ref:`. On `pull_request`, HEAD is therefore the
synthesised merge ref, and the workflow says so itself at `ci.yml:75`: "actions/checkout takes depth 1 on the
synthesised merge ref". That commit's FIRST parent is the base tip, so the merge base of `origin/master` and
HEAD is master's tip. `rev-list --first-parent <mb>..HEAD` then holds exactly one commit, HEAD. C is HEAD for
every added answer, and the comparison is HEAD against itself.

Measured on the fixture:

| HEAD | commits walked | K10 result | open asks |
|---|---|---|---|
| PR head (the branch tip) | 2 | refuses `2026-11-25/1`: written against "Branch ask B.", now names "Master ask A." | B open, A silently closed |
| synthesised merge ref (what CI checks out) | **1** | **`[]` — passes** | the same |

Fixture (a) in §3 builds commits and runs from the branch tip, so it goes red locally while the CI step can
never fail. Every fixture the spec names would pass while the gate checks nothing where it is enforced.
`check-merge-ready.py` replays the step from the PR's worktree (`scripts/check-merge-ready.py:2198`), where HEAD
is the branch tip, so that path would catch it. That makes CI and merge-ready disagree, and the CI step's green
is a false claim.

**Fix.** K10 must read the PR head, not the checkout's HEAD. Pass `--head "${{ github.event.pull_request.head.sha }}"`
(or use `HEAD^2` when HEAD is a merge whose first parent is the base), and add a fourth fixture: (a) wrapped in a
synthesised merge with the base as first parent must still REFUSE. The spec's CI paragraph (line 205–209) must
name which commit K10 walks from. A better shape, which also closes M1, is given under M1.

## MAJOR

### M1 — An edit to the answer after the merge launders the shift; "C = first commit holding the entry" is keyed on the wrong thing

K10 finds C by matching the answer's whole `raw.rstrip()` (spec line 191). Any later change to the answer's
body, such as a typo fix, a clarifying sentence or a reflowed line, makes the edited text first appear AFTER the
merge. C then becomes the edit commit, whose view already has the shift, and K10 compares the shifted view with
itself. Measured: on the branch tip of the fixture, one more commit changes "Answer to B." to "Answer to B (typo
fixed).". K10 walks 3 commits and returns `[]`, while `unresolved` still shows B open and A closed. The spec's
accepted exit, "the rewritten entry first appears at the merge, so K10 … passes", is the same mechanism. It
cannot tell a deliberate id rewrite from any other touch of the entry. The spec states the rebase bound, but not
this one, which is as easy to hit and needs no rule broken.

**Fix (a hypothesis; run it on the three fixtures and B1's fourth).** Check the invariant at the transitions
where the hazard arises, the merges, rather than at a "first holder". For every commit M in
`git rev-list --merges <mb>..<head>` (this includes the CI-synthesised merge), and for each parent P of M: for
every `[resolved: X]` entry added relative to the merge base that appears byte-identical (rstripped) in both P
and M, the entry X names at P must equal the entry X names at M, compared by content. A rewritten id in M is a
non-identical entry and is skipped. Later edits to the answer are irrelevant, because the merge is fixed
history. Mutation: drop `--merges` scope to first-parent and the fourth fixture must go red.

## MINOR

### m1 — K10's failure paths are not stated, so it can fail quietly

The spec does not say what K10 does when: (i) `merge-base` fails (a shallow or grafted clone; today
`ci.yml:73`–`:77` records exactly this "no merge base" exit); (ii) no commit in the walk holds the answer (the
lookup returns nothing; in my implementation `next(…, None)`); (iii) X names nothing at C (a target added in a
later commit). A natural implementation `continue`s on (ii) and treats (iii) as "unequal" or "skip" depending on
the author. **Fix:** state that (i) and (ii) exit 2 with "treat this as NOT RUN" (house rule: cannot-run is a
failure), and that (iii) is a refusal. Add a fixture for (ii) and a fixture for (iii). `fetch-depth: 0` (`ci.yml:83`)
covers (i) in CI today, but the spec should not rely on that silently. Its own line 208 is the only thing tying
the two together.

### m2 — K8's categories omit the shape that executes a retired script today

K8 claims "nothing still EXECUTES … a retired thing" (spec line 202). Its categories are file loads, a
`ROOT / "scripts" / …` literal, a settings hook `command`, a workflow `run:` line, manifests and page keys. None
covers a plain path string in a subprocess argv. The live instance is
`scripts/check-merge-ready.py:2198`, `["python3", "scripts/check-dashboard-entry.py", …]`. S2 repoints that one
line by name, but K8 is the permanent guard, and its seeded self-test can only prove the categories it lists.
**Fix:** add an argv category (a `"scripts/<retired>.py"` string literal in a list or tuple passed to
`subprocess.*` or `_run`), seeded from that line's shape. Also state K8's bound for "an `href` to `/dashboard`
emitted by a page generator": a static scan sees a literal and not an href assembled at run time (`f"/{name}"`).
Say which one it sees.

### m3 — K9 misattributes the one refusal that `rstrip` cannot explain

Checked and holding: `rstrip` hides only whitespace at the end of an entry. A whitespace-only edit to an old
entry passes (`r3/k9.py`: "ws-only edit to old True"), and that is harmless to the parse and the render. A body
edit and text appended to the base's last entry without a header both refuse. No real edit is hidden; **no
finding against the strip.** The gap is the diagnosis. If the base store ends inside an unclosed fence, every
appended `##` header is fenced into the last base entry. K9 refuses, which is correct, but in its own words
("an entry … altered"), and the author did not alter anything (measured: the append parses as 1 entry, prefix
False). **Fix:** when the only K9 difference is the base's last entry and the base parse ends in an open fence,
say so. One sentence in K9 and one fixture are enough.

## Checked, no finding

- K10 with the answer added IN the merge commit: C is the merge, which is the merged view the author resolved
  against. It passes, which is correct.
- Squash merge: CI runs before the squash, and the squash adds no new store state on the branch. Not a hole.
- A merge that places the branch's ask before master's: K9 refuses (prefix broken). Correct.
- K8's seeded self-test falsifier ("a scan that finds nothing fails the seeded cases") is stated and sufficient
  for the categories listed. m2 is about the list.
- Every gate in §3 states a FAILS IF.

VERDICT: NOT CONVERGED
