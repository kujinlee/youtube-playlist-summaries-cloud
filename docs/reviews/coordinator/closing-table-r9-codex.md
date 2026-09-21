# closing-table — round 9 — Codex half (Tier 1 of #149)

Subject: PR #328, branch `fix/closing-table-log-turn-identity`, +163/−8. Run via `scripts/codex-review.py` (`gpt-5.5`); verdict `docs/reviews/verdicts/r9-codex.verdict.json` records `gate_ran=true`.

<!-- codex-review: model=gpt-5.5 -->

**Finding**

Low — [docs/dashboard-entries.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dashboard-entries.md:10973) records stale verification numbers for this change. It says the log-id work has “10” new log cases, “2 mutations”, “148 cases, 44 mutations, sum 826”, but the branch now has 13 log/turn-id checks, 3 new mutation entries, `scripts/check-closing-table.py --self-test` prints `151/151 passed`, `EXPECTED_MUTATIONS["scripts/check-closing-table.py"]` is `45`, and the declared mutation sum is `827`.

Concrete failing input: this PR branch itself. Run:
```sh
python3 scripts/check-closing-table.py --self-test
python3 - <<'PY'
import json
from pathlib import Path
print(len(json.loads(Path("scripts/mutations/check-closing-table.json").read_text())))
PY
rg '"scripts/check-closing-table.py":|the declared counts are the real ones' scripts/check-plan-code.py
```
Those contradict the dashboard entry’s `(148 cases, 44 mutations, sum 826)` claim.

**Notes**

I did not find a code defect in the load-bearing identity path. Corpus replay over 773 transcripts / 3,267 boundaries produced 630 warning emissions collapsing to 315 unique judged-turn opener UUIDs, with 0 `-` ids; the 71-emission worst turn shared one UUID.

Executed:
```sh
python3 scripts/check-closing-table.py --self-test
```
Targeted mutation runs for the last 3 and last 13 `check-closing-table` manifest entries: all caught and attributed.

Not run to completion: full `python3 scripts/check-plan-code.py --mutate .`; I interrupted it at 223/827 because it was outliving the PR-specific review.
