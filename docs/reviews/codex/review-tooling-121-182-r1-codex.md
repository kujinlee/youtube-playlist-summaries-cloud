<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED**

1. **Major — `scripts/check-review-rounds.py:635`: a GAP for the wrong half excuses the missing review.**  
   With only `p-r1-codex.md` present:
   ```yaml
   halves:
     codex: "GAP: unavailable"
     claude: ran
   ```
   `audit(..., set())` returns no problems, although Claude neither ran nor has a declared gap. Flipping the halves in the new integration fixture stays green; removing the GAP reddens it. The audit tests only whether *any* GAP exists.

2. **Major — `scripts/check-review-rounds.py:227`: nested scalar contents become gap declarations.**  
   With only `p-r1-codex.md` present:
   ```yaml
   halves:
     notes: |
       claude: "GAP: example only"
   ```
   `yaml_gap()` returns `claude: example only`, and the audit passes. This YAML contains no `halves.claude` field. Indentation depth and block-scalar boundaries are ignored.

3. **Major — `scripts/check-review-rounds.py:212`: a YAML comment counts as a reason and waives a downstream gate.**
   ```yaml
   halves:
     codex: GAP: # comment only
   ```
   The scalar’s value is `GAP:`; it has no reason. The parser instead returns `codex: # comment only`. Passing this through `check-review-recorded.first_codex_gap()` and `tail_verdict({}, gap=...)` produces **exit 0**, waiving the final-tree check without a usable reason.

4. **Major — `scripts/codex-review.py:1269` and `:1112`: recorded and executed Git contexts can differ.**  
   Concrete input: invoke from repository A with `GIT_DIR=B/.git` and `GIT_WORK_TREE=B`, where A and B have different commits. `reviewed_root()` and `reviewed_state()` strip those variables and record A. `run_codex()` inherits them. A stub Codex executing `git rev-parse --show-toplevel` and `HEAD` reported B and B’s commit. The verdict therefore describes a different tree from the Git context handed to the reviewer.

5. **Major — `scripts/check-review-rounds.py:229`: returning only the first GAP breaks the Codex-gap consumer.**
   ```yaml
   halves:
     claude: "GAP: quota"
     codex: "GAP: quota"
   ```
   `has_gap_line()` returns only `claude: quota`. `check-review-recorded.first_codex_gap()` consequently returns `None`, and its final-tree check exits **2**, despite an explicit Codex gap. Reordering the YAML keys changes the result.

Verification completed:

- Codex self-test: **176/176 passed**.
- Round-check self-test: **99/99 passed**.
- Requested mutation slices: **49/49** and **41/41 killed**, all attributed.
- Additional bad mutations survived: selecting the **last** YAML fence passed 99/99; adding `cwd=REPO_ROOT` to the Codex subprocess passed 176/176. The refusal-only dispatch fixture never exercises where Codex actually runs.

Consumer tracing covered `check-review-rounds.py`, `check-review-recorded.py`, and `check-merge-ready.py`. The additive `tree` field caused no direct schema incompatibility found; the GAP changes affect the shared parser and therefore merge readiness.

Neither backlog row contains a literal `FAILS IF` clause; both rows and their stated contracts/falsifier were read. No file under `.claude/plans/` was accessed.
