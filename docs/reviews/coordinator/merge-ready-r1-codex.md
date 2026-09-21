<!-- codex-review: model=gpt-5.5 -->

**High** — [scripts/check-merge-ready.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:138) can report `READY` for a PR GitHub still cannot merge.

The script never asks GitHub for `baseRefName`, `headRefOid`, `isDraft`, or `mergeStateStatus`; it only reads the PR body and check buckets:

```python
ap.add_argument("--pr", type=int, default=None)
...
rc = _run(["gh", "pr", "checks", str(pr), "--json", "name,bucket"])
```

Trigger: a draft PR, conflicted PR, wrong-base PR, or explicit `--pr` pointing at a different green PR. If local subprocess gates return `0` and `gh pr checks` returns only `pass`/`skipping`, `verdict()` returns `READY`, even though the selected PR may be draft/conflicted/not based on `master`, or not the PR for the current checkout at all. This is the catastrophic class the script is meant to prevent: “checks green” is not the same as “mergeable”.

**Medium** — [scripts/check-merge-ready.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:73) `pr_only_steps()` is not actually parsing YAML step `if:` fields.

The load-bearing code is substring scanning after the last `name:`:

```python
m = re.match(r"\s*-\s+name:\s*(.+?)\s*$", line)
...
if current and PR_ONLY_COND in line:
    names.append(current)
```

Concrete hostile inputs:

```yaml
- name: x
  if: github.event_name == "pull_request"
  run: y
```

returns `[]` even though the step is PR-only.

```yaml
- name: x
  # if: github.event_name == 'pull_request'
  run: y
```

and

```yaml
- name: x
  run: echo "github.event_name == 'pull_request'"
```

both return `["x"]` even though the step is not PR-only. Against the current `.github/workflows/ci.yml`, it does find exactly `dashboard entry ratchet` and `check-review-recorded (PR only)`, so this is not a live undercount today. But the “derived, never hand-written” claim is brittle the moment someone uses valid alternate YAML spelling.

**Low** — [scripts/check-merge-ready.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:173) says the PR-only gates are invoked like CI, but dashboard entry is not.

CI runs:

```yaml
python3 scripts/check-dashboard-entry.py \
  --base "origin/$GITHUB_BASE_REF" --pr-body-file /tmp/pr-body.md
```

The script runs:

```python
("dashboard entry", ["python3", "scripts/check-dashboard-entry.py"]),
```

Trigger: branch has no dashboard entry but the PR body contains a valid `NO-ENTRY:` waiver. CI can pass; `check-merge-ready.py` reports `NOT READY`. This is a false negative, not a false READY, but it makes the “one command answering can this PR merge?” contract noisy.

Verified:
`git diff origin/master..HEAD` is 2 commits, 10 files, not 7. `ci.yml` has 52 `run:` steps and the current parser finds exactly 2 PR-only steps. `check-docs.py --self-test`, `check-docs.py`, `check-merge-ready.py --self-test`, `check-plan-code.py --self-test`, `check-fixture-variation.py --self-test`, `check-selftest-counts.py --self-test`, and `check-ratchet-contract.py` passed. Live `check-merge-ready.py --pr 324` returned `NOT READY`, not a false READY. NOT RUN: full mutation sweep.
