# Round 1 — `marketplace-task16` — coordinator — NOT CONVERGED (both halves): the scan reads names file-wide and calls an expressible failure a limit

Both halves ran on 07664d06 (plan Task 16: the publishability scan predicts the install experiment's scan-clean
failures S1 and S3). Codex `docs/reviews/codex/marketplace-task16-r1-codex.md`: 1 MAJOR, 1 MINOR. Claude
`docs/reviews/claude/marketplace-task16-r1-claude.md`: 1 BLOCKER, 3 MAJOR, 6 MINOR. They have two causes. Detector 2's
`install-root` bound a name file-wide and counted every use of the root, so it reported false findings. And the
records filed three failures the scan can express (a home-path guard, a store path that opens a section, a `..`
part) as limits.

The fold (3db9d353) does two things. Detector 2 now reads a name as Python resolves it: by scope, and only when
every store of it agrees. It skips the uses that do not hand the root on. The scan also gains the cases the limits
had stood in for: detector 6 `home-path` for B1 and detector 4 section openers for M1, and the `..` climb for M3. Each
case was RED before its code. The self-test went from 109 to 116 cases and the mutations from 175 to 226; each new
mutation was run red on its named case on a scratch copy.

```yaml
round: 1
fixes_nontrivial: true
subject: marketplace-task16
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: fixed}
  - {id: X2, severity: Minor, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: fixed}
  - {id: B1, severity: Blocker, aim: deliverable, fix_induced: false, component: publishability-prerequisites, disposition: fixed}
  - {id: M1, severity: Major, aim: deliverable, fix_induced: false, component: publishability-doc-path, disposition: fixed}
  - {id: M2, severity: Major, aim: deliverable, fix_induced: false, component: experiment-records, disposition: bounded}
  - {id: M3, severity: Major, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: fixed}
  - {id: m1, severity: Minor, aim: deliverable, fix_induced: false, component: experiment-records, disposition: fixed}
  - {id: m2, severity: Minor, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: fixed}
  - {id: m3, severity: Minor, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: fixed}
  - {id: m4, severity: Minor, aim: deliverable, fix_induced: false, component: experiment-records, disposition: fixed}
  - {id: m5, severity: Minor, aim: deliverable, fix_induced: false, component: experiment-records, disposition: fixed}
  - {id: m6, severity: Minor, aim: deliverable, fix_induced: false, component: publishability-cwd-relative, disposition: fixed}
```

| # | Severity | Finding | Disposition |
|---|---|---|---|
| X1 / m2 | MAJOR | Names are bound file-wide, ignoring scope: `check-plan-code.py:3446` (`_sp.run = _real`) is a false install-root finding. | **Fixed.** `_Scopes` + `_Bound`: a name is looked up in the scope Python resolves it in (functions, lambdas, comprehensions, class bodies skipped from methods, `global`/`nonlocal`), and it is followed only when every store agrees. Two cases, RED first. The rescan drops `check-plan-code:3446` and `check-docs:254`. Bound in L5: a name whose stores disagree is not followed. |
| X2 / m3 | MINOR | Every use of the root counts, including comparisons and `relative_to` (`gen-dashboard:33`, `regen-pages:421`, `check-rc-contract:449`). | **Fixed.** `_inert`: a comparison, an f-string, `print`/`os.path.relpath`, either side of `relative_to`/`is_relative_to`/`samefile`, and an existence test of the root itself are not reported. One case, RED first. `regen-pages:2:1` now sits at `:423`, the git call. |
| B1 | BLOCKER | L3 records `~/explainers` as a limit, but `brief-compose.py`'s guard is the decision the scan said it could not make. | **Fixed.** A detector 6 `home-path` finding: a guard that turns a path below HOME's absence into a failure (a `raise`, a non-zero exit or a non-zero return). An exit of 0 is a working default and is not reported. One case, RED first. The rescan gives `brief-compose:6:1` at `:789`. L3 is dropped. |
| M1 | MAJOR | `docs/dashboard-entries.md` opens `## The store`, a section that says to append to it. That is a prerequisite, not a convention cited in prose. | **Fixed.** `_heads_section`: a backticked `docs/` path that is alone on its line, right under a heading, and followed by a body that acts is a prerequisite. A span that holds more than the path is still a mention. One case, RED first, and the rescan gives `skill-dashboard:4:1`. L2 narrows to `docs/anchors.md` (`:14`), which is a citation. |
| M2 | MAJOR | Tier B's `dashboard` run reported two shipped files absent, `scripts/check-dashboard-entry.py` and `.claude/hooks/regen-dashboard.sh`. No case and no limit covered them. | **Bounded.** This is new limit L6. Both files are named in description, not in an INSTRUCTS, REQUIRES or read/follow shape, so they are mentions under spec rule 1. Both are now listed in the tier-B table. |
| M3 | MAJOR | `install-root` misses the `..` form (`os.path.join(dirname(...), "..")`). | **Fixed.** `_placed` normalises the parts: a leading `..` climbs a level and an absolute part leaves the tree. An annotated binding (`X: Path = ...`) now holds its value. One case, RED first. |
| m1 | MINOR | The scan's `measured_at` names the base, which does not produce it. | **Fixed.** The scan was regenerated at the fold commit: `measured_at` is `3db9d353`, so the scanner and the tree are the same commit. Both records cite that commit. |
| m4 | MINOR | The gen-dashboard row cites `docs/backlog.md`, but its finding names `docs/dashboard-entries.md`. | **Fixed.** The read goes through `gen-backlog-page` (`gen-dashboard.py:3495-3498`, `publish_rows(ROOT)`). The row names `gen-backlog-page:2:2`. |
| m5 | MINOR | Two tier-B degraded results are missing from the Task-16 table. | **Fixed.** One row for `brief` "written for a different repo", predicted by `skill-brief:4:1` and `4:3`. One row for `explain-diff`'s page having no tray, covered by L1. |
| m6 | MINOR | The cross-clause `seen` dedup is not pinned by any case. | **Fixed (regression lock).** One case puts an invocation and a read of the same target on one line. It passed on its first run because the dedup existed, so it locks behaviour that already worked. Its mutation clears `seen` before the read loop and goes red. |

**The rescan against the previous scan:** findings went from 364 to 365.
- **Removed (seven, all false):** `check-docs:254`, `check-plan-code:3446`, `check-rc-contract:449`, `explainer-serve:690`, `gen-dashboard:33` (×2) and `regen-pages:421`.
- **Added (eight):** `brief-compose:6:1`, `skill-dashboard:4:1`, `check-docs:369` and `:563` (both were masked by the file-wide binding), `explainer-serve:692`, `gen-dashboard:514` and `:3305`, and `regen-pages:423`.

**Thrashing watch for r2 (Codex, alternation):** the r2 fold is thrashing only if r2 finds a defect caused by this
fold in detector 2 (`_Scopes`/`_Bound`/`_inert`/`_rebinds`). The bet is in the decision log.
