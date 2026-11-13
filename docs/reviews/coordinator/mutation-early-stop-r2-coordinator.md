# Round 2 — `mutation-early-stop` (draft PR #476, backlog #405) — coordinator — NOT CONVERGED (Codex half)

Codex half: `docs/reviews/codex/mutation-early-stop-r2-codex.md`, which reviewed `594039e5`.
REVIEW GAP: claude — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 2
fixes_nontrivial: true
subject: mutation-early-stop
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X2-H1, severity: High, aim: deliverable, fix_induced: true, component: stop-rule, disposition: fixed}
```

**What it found:**
- **X2-H1 (Codex), the execution ENVIRONMENT moved, not a file.** The r1 rule, `early_must_run_full`, forced
  FULL only for the paths it recognised: the target file, its manifest, and a `.py` whose stem the target's
  source names. Every other path let early stop through. Codex added `scripts/startup/sitecustomize.py`, which
  rewrites `sys.exit` to exit 0, and put it on the mutation job's `PYTHONPATH` in `ci.yml`. On the first mutant
  of `check-function-revokes.py` it measured FULL: survived, EARLY: killed (`stop='sigint'`). It is
  fix-induced: the r1 fold introduced the deny-shaped precondition.

**The fold replaces the deny list with an ALLOW list.** `early_path_allowed` admits only the paths the per-file
rule can reason about: anything under `docs/`, any `*.md`, a manifest directly in `scripts/mutations/`, and a
`scripts/**/*.py` that is neither startup-capable (`sitecustomize.py`, `usercustomize.py`, `conftest.py`,
`__init__.py`) nor named like a standard-library module. The last exclusion was added during the fold, beyond the
coordinator's brief: `scripts/` is each suite's `sys.path[0]`, so a new `scripts/tempfile.py` would shadow
`import tempfile` in every suite. Any other changed path makes the WHOLE run FULL. That includes `.github/**`,
`package.json`, lockfiles, `.python-version`, `requirements*`, `*.pth`, shell scripts, `.py` outside `scripts/`,
`*.ts`, and anything unknown. The check is applied in two places: `early_must_run_full`, which serves the local
`--early-stop` path, and `early_stop_ci`, which prints the refused path. The per-file rule still applies on top.
- **Bound (in the docstring):** a computed import, or a module reached only transitively through one the source
  does not spell, is still not seen.
- **Cost, MEASURED** over the last 40 merged PRs (`gh pr list --state merged -L 40 --json number,files`):
  30 of 40 (75%) change only allowed paths, so they still get early stop. The 10 that do not each touch
  `.github/workflows/ci.yml`, `.claude/hooks/*.sh`, `.claude/settings.json`, `.githooks/` or `.gitignore`.
- **Test:** Codex's reproducer is now a run-level self-test case. A trailer exiting 0 is recorded SURVIVED, with
  `forced_full: "diff"`, when the PR changed `ci.yml` and when it added `scripts/startup/sitecustomize.py`. The
  existing control (only `docs/x.md` changed: stopped early) is what lets those cases fail. Pure cases cover
  each refused shape and each allowed shape. Twelve new mutations each name their `expect`; the pin moves
  187 -> 199.
