# Round 4 — `merge-delta` (PR #491, backlog #426) — coordinator — NOT CONVERGED (Codex); one BLOCKER and one Medium FIXED as one class, and the architecture review's one-line narrowing adopted

REVIEW GAP: claude — alternation. Round 4 runs ONE half; round 3 ran the Claude half.

Codex half: `docs/reviews/codex/merge-delta-r4-codex.md`, on `98e7877d`.

```yaml
round: 4
fixes_nontrivial: true
subject: merge-delta
halves:
  codex: ran
  claude: gap
findings:
  - {id: X-H1, severity: High, aim: deliverable, fix_induced: true, component: master-side, disposition: fixed}
  - {id: X-M2, severity: Medium, aim: deliverable, fix_induced: false, component: branch-delta, disposition: fixed}
```

**Codex NOT CONVERGED.** It ran the self-test (275/275) and the scoped mutation sweep (102 killed, 102 attributed).
X-H1 is a false CLEAR from the full CLI, measured on a real fixture (macOS, git 2.49, Python 3.14).

**Round 4 is under the cap** (`docs/review-method.md` §0 Q4c): from round 4, findings are FILED unless they are a
BLOCKER. X-H1 is a BLOCKER by that test (a measured false green on a normal developer machine). X-M2 is not, and on
its own would be filed; it is FOLDED because it is the same class as X-H1 and closes by the same change, and leaving
two of the six git readers on the defective capture would be the instance-not-class fix this file's own history
records against itself.

**X-H1 — BLOCKER — FIXED.** `subprocess.run(text=True)` applies universal newlines even with `encoding=` and `errors=`
given, so `lib/a\r.py` came back as `lib/a\n.py`. In r3's whole-tree listing the unchanged CR-named entry then
overwrote the edited LF-named one under the same key, HEAD and the synthetic merge agreed on the wrong entry, and the
full CLI said `ok`, rc 0. Fix-induced: r3's whole-tree listing is what admits the unrelated colliding entry.

**X-M2 — FIXED, same class.** `changed_paths` and `added_paths` still captured with strict text decoding, so a path
name holding a raw `0xe9` byte raised `UnicodeDecodeError`. Fails closed (no completion), which is why it was not a
BLOCKER. Not fix-induced: the two readers predate #426.

**The fix removes the class.** Every git read in `scripts/check-review-recorded.py` now goes through one reader,
`_run_git`, which captures BYTES and decodes them with `git_text` (`utf-8` + `surrogateescape`, pure). The call
sites, each with its disposition:

| Site | Before | Now |
|---|---|---|
| `_git` (repository runner) | `text=True` + surrogateescape | `_run_git` |
| `_isolated_git`'s `run` | `text=True` + surrogateescape | `_run_git` |
| `changed_paths`: shallow probe | strict `text=True` | `_git` (output is `true`/`false`; no case can tell, so no mutation) |
| `changed_paths`: merge base | strict `text=True` | `_git` (output is a hex sha; no mutation, same reason) |
| `changed_paths`: diff | strict `text=True` | `_git` |
| `added_paths`: merge base | strict `text=True` | `_git` (hex sha; no mutation) |
| `added_paths`: diff | strict `text=True` | `_git` |
| self-test fixture `_g` | `text=True` + surrogateescape | bytes, decoded in place — its own copy, NOT `_run_git`, because it feeds the production parsers and a mutant of the reader must not reach the fixture |
| self-test `_blob_of` | — (new) | bytes; output is a hex sha |

No other `subprocess`, `Popen`, `check_output` or `os.system` call exists in the file. The remaining `encoding=` uses
are file reads and writes, not git output.

**Cases (285, up from 275).**

- The FULL CLI, in-process, with `ROOT` pointed at a fixture repository holding `lib/a\n.ts`, `lib/a\r.ts` and
  `lib/caf\xe9.ts`, only the LF one edited after the round: rc 1 (`--base master`). The CONTROL is the same tree with the round taken at
  the edited commit: rc 0 (`--base <the fork commit>`), so the rc 1 is the tail and not a setup failure. The gate's own inputs (`scripts/`,
  `docs/superpowers/`) are untracked links to the checkout's, so no diff the gate reads contains them.
- `changed_paths` and `added_paths` over that fixture return the three names distinct (X-M2), and against the
  reviewed commit as base they return only the edited LF name and nothing, so the `base` each reads is varied.
- A carriage-return name joins r3's odd-name loop: HEAD's lookup, the merged tree's lookup, and the gatherer's charge.

**The architecture review — ADOPTED, one predicate.** Convened on THRASHING (r2's X-M1 caused by r1, r3's C-L1 caused
by r2, both in `master-side`). Filed at `docs/reviews/architecture-review-2026-11-03-merge-delta.md`. Its verdict:
KEEP the merge-tree design (it clears 1 of 3 charged master merges over the last 40 merged PRs; the narrower rules
clear 0), and drop the absent/absent arm of `master_explains`, which turned every lying lookup into a clear (r1's X-H1,
r3's C-M1). `master_explains` now returns `not is_absent(now) and now == want`. The pure case that pinned
`({}, ∅), ABSENT → True` is flipped to `False`, with a control that a present equal entry still clears. The
derivation was checked against the gatherer and no counterexample was found: a path reaches `master_explains` only
from `after ∩ branch_delta` without a dirty overlay, so the round's commit or HEAD holds it and `onto` differs from
HEAD; a branch that ADDS a file after the round has it present in HEAD, so it never reaches absent/absent. The r1
fold's raising `_final_entries` stays: it also protects `round_tail.same()`'s legitimate deletion arm. The docstring's
claim that a both-touched file was "already reviewed on master's own PR" is replaced by the stated same-file
composition waiver. **Not adopted, left open:** the isolated repository's init-written `core.ignorecase` /
`core.precomposeunicode` (a docstring inaccuracy) and the `.gitmodules ignore = all` route in `diff_argv` (latent,
pre-existing, outside this component).

**ADR-0014 debt paid.** Driving `main` over the fixture makes `check-review-recorded.py` comply with ADR-0014 (route:
rebind), so it leaves `MAIN_DEBT` in `scripts/check-main-drivable.py` in this commit, as that set requires.

**Mutations: 102 → 109.** Two re-anchored (r3's strict-decoding isolated runner; #426's "HEAD deleting a file the merge
keeps"). Seven added: the shared reader in text mode; `_git` alone in text mode; the isolated runner alone in text
mode; each branch-level diff in strict text mode (two); `git_text`'s error handler as `replace`; the absent/absent arm
restored.

**Round 5 is the final-tree check under the cap.** The decision-log `merge-delta` row keeps `outcome: null`, with no
`rounds_at_termination`, as rounds 1–3 left it; the value is written when the loop terminates.
