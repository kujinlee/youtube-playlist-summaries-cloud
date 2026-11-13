Reviewed head: 4ae91ab30a808806b7f882751e4972e7bd5c46a8

# batch-ci (PR #529, backlog #534): round 1, Claude half (adversarial, mandate REFUTE)

Scope: `git diff fb2a7e4b...HEAD`. Both self-tests were run at HEAD: `batch-ci.py --self-test` gave 55/55 (rc 0), and `check-merge-ready.py --self-test` gave 270/270 (rc 0).
Every experiment ran on a scratch copy (`git archive HEAD | tar -x`) or in throwaway git repositories. Nothing in the worktree was touched except this file, and GitHub was not contacted.

### R1-F1 — Blocking — `plan`/`land` batch and merge PRs that `check-merge-ready` would HOLD, and PRs whose review has not converged

`scripts/batch-ci.py:130-156` (`select`), `:563-584` (`land` loop)

`select` defines READY as: open, not a draft, based on master, not from a fork, and own CI green. That is all.
- Nothing consults `check-merge-ready.py`. (`grep -n "merge-ready\|HOLD\|NO-REVIEW\|review" scripts/batch-ci.py` matches only the decision-log path.)
- So `land --land` will squash-merge PRs that the house rule says must not merge (`docs/dev-process.md`: "exit 3 HOLD … ⇒ do NOT merge, notify"). That covers a PR that loosens a gate, needs a deploy, carries `NO-REVIEW:`, or holds app code without local tests.
- Concrete case: `docs/goal-threads.md` lists PR #392 as "HELD: migration 0028 deploys first". If its CI is green, `plan` batches it and `land --land` merges it before the migration is deployed.
- The same goes for any non-draft PR still in review. PR #529 itself, mid-review right now, would be batched and landed.
- A merge cannot be undone, and the merge is the act that the house rule gates.

Reproduced by reading the code. There is no other filter: `select` is the only gate between `gh pr list` and the batch, and `land` reads members straight from the batch's merge commits.

Fix:
- In `select`, require `check-merge-ready.py --pr N` to return READY (rc 0), and print the reason for a skip.
- Or, at minimum, have `land` re-run it per member just before `gh pr merge`, and STOP on anything that is not READY.
- A case: a PR with green CI whose merge-ready answer is HOLD is skipped (or `land` stops on it).

### R1-F2 — High — the `lines` union fuses two same-day dashboard entries: the second entry loses its `## date` heading and its `<!--tech-->` marker

`scripts/batch-ci.py:252-260` (`resolve_hunk`, policy `lines`)

`ta = [x for x in _added(theirs, …) if not (x.strip() and x in oa)]` drops every non-blank line that theirs added if ours added the same line.
- Dashboard entries are headed by DATE (`## 2026-11-06`; `docs/dashboard-entries.md` holds 19 `## 2026-09-07` headings, for example), and every entry carries a literal `<!--tech-->` line.
- So two PRs from the same day that each append an entry always collide on exactly the two structural lines.

Reproduced end to end with real git: a base file, two branches each appending `\n## 2026-11-06\nSummary X.\n<!--tech-->\ntech X\n`, then `merge_into(_run, ".", HB)` from the scratch copy. It returned `None` (resolved) and wrote:

```
## 2026-11-06
Summary A.
<!--tech-->
tech A

Summary B.
tech B
```

B's summary is now part of A's tech section, and B's tech text has no marker.
- Calling `resolve_hunk("lines", ours, [], theirs)` directly returns `['', '## 2026-11-06', 'Summary A.', '<!--tech-->', 'tech A', '', 'Summary B.', 'tech B']`.
- This damages the page `gen-dashboard.py` derives. Because `land` pins master to the batch tree, the damage is what lands.
- The self-test misses it because its fixture uses unique headings (`## e1`, `## e2`), and the "same line added on both sides lands once" case asserts this very behaviour.

Fix:
- Dedupe whole ADDED BLOCKS, or dedupe only for `decision-log.jsonl` (lines are records there). For the markdown files, never drop a line of theirs: append theirs' added lines verbatim.
- Add a case with two entries under the same date heading, each with `<!--tech-->`.

### R1-F3 — High — `land` checks the tree only AFTER `gh pr merge`, so it can merge a tree the green batch never measured

`scripts/batch-ci.py:584-593`

The tree assertion runs after the squash has already landed on master. "STOP LOUDLY" then reports a master that is already untested.

GitHub's squash and the batch can produce different trees from equal inputs, because the merge base differs:
- In the batch, `merge(batch_{i-1}, head_i)` uses `merge-base(batch_{i-1}, head_i)`. That base includes earlier members' heads.
- On GitHub, after the earlier members were squashed, the merge base is the old master.
- The two diverge whenever a member's history shares commits with an earlier member's head. That happens with a stacked PR retargeted to master, or with two branches that merged a common branch.

Reproduced in a throwaway repository:
- PR j adds line `L`. PR i is branched from j and removes `L`.
- The batch (master, then merge j, then merge i) has `f` = `a b c`.
- The squash path (squash j, then `git merge-tree --write-tree master HI`) gives `a L b c`, cleanly with no conflict. So PR i is not DIRTY, `land` takes the `use = cur` path, merges, and only then sees the mismatch.
- The `tamper` e2e case also shows detection only after the fact: the merge has already happened when it asserts.

Fix: before `gh pr merge`, predict the result with `git merge-tree --write-tree origin/master <use>` and require it to equal `want`. Refuse without merging if it differs. Keep the post-merge assertion as the second line of defence.

### R1-F4 — Medium — `status` reports a cancelled, skipped or stale run as RED and bisects, which ejects an innocent PR

`scripts/batch-ci.py:488-531`

Any `conclusion != "success"` on a completed run is treated as red.
- When the conclusion is `cancelled` (a person cancelled it, or a runner was lost), `skipped`, `stale` or `action_required`, there are no `failure` jobs. `other` is then empty, the log yields nothing, and `attribute` returns bisect.
- The output is `RED … BISECT … --exclude <newest>` with rc 1. The newest PR is dropped for a run that measured nothing.
- That is CANNOT RUN reported as a verdict.
- A shard that hits `timeout-minutes` is reported by the jobs API with conclusion `cancelled`, so it is excluded from `bad` in the same way.

Reproduced by driving `status()` on the scratch copy with `_fetch_batch`, `_runs_at` and `members_of` stubbed, and jobs all `cancelled`. For `cancelled`, `skipped` and `stale`, every one printed `RED — run 5 … (cancelled); members [3, 9]` and `BISECT … --exclude 9`, with rc 1.

Fix: treat only `failure` / `timed_out` as RED. Report any other non-success as `NO VERDICT … NOT RUN`, rc 2. Add a case.

### R1-F5 — Medium — attribution ejects an innocent PR when the culprit changed a helper that the target imports

`scripts/batch-ci.py:291-321` (`failures`, `attribute`)

A failure is owned by `{manifest, target}` only.
- If PR Y edits a shared helper (`scripts/fixture_git.py` is imported by 94 scripts) so that a target's cases become vacuous, and PR X made a harmless edit to that target, then X is the single owner and is EJECTED.
- The output tells X's author "its diff owns the failing manifest".
- The re-assembled batch stays red, and only the next round bisects to Y.

Reproduced: `attribute([{"paths": {"scripts/a.py", "scripts/mutations/a.json"}}], {3: {"scripts/a.py"}, 9: {"scripts/lib_helper.py"}})` returns `('eject', [3])`.

Fix:
- Option 1: bisect, rather than eject, when any member's diff touches a non-doc file under `scripts/` that the target imports. The harness's own `harness_files` / import closure can supply this.
- Option 2, at minimum: word the message as "suspect", and say that a still-red re-batch means the cause is elsewhere.

### R1-F6 — Medium — the batch does not run `schema-gates.yml`, yet `land` and the docs claim master is "exactly what the green sweep measured"

`.github/workflows/ci.yml:22` adds `batch/**`. `.github/workflows/schema-gates.yml:113-117` is still `push: branches: [master]`. `scripts/batch-ci.py:540-543` requires a green `--workflow CI` run only.

Two PRs whose migrations compose badly each pass `schema-gates` alone. The batch never runs that workflow, and `land` merges both.
- This is not a regression: composition was previously only checked after merge.
- But the claim at `batch-ci.py:26-28` and in the dashboard entry ("each merge is checked to leave the main branch exactly as tested") overstates what was tested.

Fix: add `batch/**` to `schema-gates.yml` and require that run to be green in `land`. Otherwise, state the limit in the docstring and the dashboard entry.

### R1-F7 — Medium — safety guards whose deletion leaves the suite green (55/55)

Each mutation below was applied alone to the scratch copy, and `--self-test` was re-run:

| Guard removed | Line | Result |
|---|---|---|
| `_runs_at` filters runs to `headSha == tip` (land's "only the tested tip" guard) | :479 | SURVIVED |
| `status`: an in-progress run is NO VERDICT (otherwise a `None` conclusion reads RED and bisects) | :489 | SURVIVED |
| `status`: no run at the tip is NO VERDICT | :485 | SURVIVED |
| `land`: members landed out of batch order STOP | :548 | SURVIVED |
| `land`: a member that is not OPEN STOPs | :567 | SURVIVED |
| `land`: a `gh pr merge` failure STOPs (masked by the post-merge tree check) | :585 | SURVIVED |
| `_refresh`: refresh tree != want is never pushed | :612 | SURVIVED (masked on re-run by the acceptance check, which IS killed) |
| `merge_into`: a file deleted on one side is refused | :379 | SURVIVED |
| `parse_conflicts`: a nested marker is refused | :192 | SURVIVED |
| `members_of`: a branch with no members is refused | :471 | SURVIVED |
| `plan`: an existing branch name is refused | :417 | SURVIVED |

The first three matter most. The first is the guard behind probe 1; the second and third separate CANNOT RUN from a verdict.

Fix: add a case per row (the e2e fake already has `runs` / `jobs` / PR state to vary), plus a manifest entry for each.

### R1-F8 — Low — the advisory batch line in `check-merge-ready` makes up to N sequential, unbounded `gh api` calls

`scripts/check-merge-ready.py:1376-1390`

This cannot move the verdict. I confirmed it sits in `try/except Exception`, never enters `results`, and the READY-with-no-batch case passes.
- However, `_contains` issues one `gh api …/compare` per green batch run, with no `timeout=`.
- A hung or slow API call therefore stalls the whole merge-ready check.
- `--limit 100` over ALL push runs (master included) can also push older batch runs out of the window, giving a spurious "no green batch".

Fix: pass a timeout to `_run` for these calls, and filter on `--branch`-prefixed runs, or cap the compare calls.

### R1-F9 — Low — counts in the new prose are not what the code holds

- `docs/dashboard-entries.md` (the #534 entry) says "54 cases". The suite runs 55.
- The `EXEMPT` reason for `batch-ci.py:main.root` in `scripts/check-fixture-variation.py` says "eight PRs". The e2e creates five (`make_pr` 1-5).

Fix: correct both, or derive them.

VERDICT: NOT CONVERGED
