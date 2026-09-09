<!-- codex-review: model=gpt-5.5 -->

3afe62c095a6ec0bab0bdc12e8f73beca0e37512
3afe62c0 Retire plan mode — delete the unreachable code (PR 2 of 2) (#271)
4ec7e82a Retire plan mode — refuse the entry points, fence the hole they leave (PR 1 of 2) (#270)
307423f1 Backlog #91 — the coverage verdict becomes a type you cannot read wrongly (#269)
 scripts/check-plan-code.py                  | 2008 ++++-----------------------
 scripts/check-plan-file-tags.py             |  649 +++++++++
 scripts/check-selftest-counts.py            |    3 +
 scripts/mutations/check-plan-code.json      |  252 +---
 scripts/mutations/check-plan-file-tags.json |  244 ++++
 5 files changed, 1158 insertions(+), 1998 deletions(-)

**Verdict**

No findings. I did not read anything under `docs/reviews/`.

I checked the 23 `scripts/mutations/check-plan-code.json` entries against the current implementation and ran each entry individually through `run_mutations`; each named `expect` appeared in the actual red case set for that mutation. I also ran:

`python3 scripts/check-plan-code.py --self-test` -> `rc=0`, `78/78 passed`

`python3 scripts/check-plan-code.py --mutate .` -> `rc=0`, `OK — delivered scripts mutated: 33 file(s), 371 mutation(s), 0 survivor(s)`

**Targeted Checks**

The five 2026-09-09 repaired entries are faithful:

- Entry 2, `a cannot-run is credited as a catch`, reddens both timeout verdict cases at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1685). The list `expect` is legitimate: one case checks the verdict is not `Measured`, the other checks the report says cannot-run rather than catch.
- Entry 3, ambiguous anchor, reaches the direct duplicate-anchor refusal at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1383).
- Entry 4, missing anchor, reaches the direct anchor-not-found refusal at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1345). It also reddens later shortfall printer cases, but the named case is independently on the intended branch.
- Entry 5, mid-line `[FAIL]`, is falsifiable. I computed `'> note: mid-line [FAIL] marker'.strip()[7:] == 'mid-line [FAIL] marker'`; the marker starts at index 17, so the mutated parser can produce the exact expected name. The current parser refuses it via [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1420).
- Entry 9, empty expect list, reaches the explicit empty-list refusal at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1388).

The four kept helpers still have real coverage:

- `run_suite`: entries 1 and 13 cover timeout rc handling and spawned HOME wiring.
- `run_mutations`: entries 2, 3, 4, 5, 9, and 17 cover cannot-run, ambiguous/missing anchors, fail-line parsing, empty expects, and non-1 exits.
- `control_is_green`: entry 23 covers the rc-only weakening via the silently exiting control fixture at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1654).
- `not_measured_line`: entry 22 covers the remaining live `--mutate` refusal output path at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1990).

For the deletion-orphan search: `git diff --name-only 307423f1..HEAD -- scripts/mutations scripts/*.py` shows only `check-plan-code`, `check-plan-file-tags`, and `check-selftest-counts` changed in `scripts/`. `rg` over `scripts/mutations/*.json` for retired plan-mode vocabulary found no remaining `check-plan-code.py` plan-mode expects; the only intentional retired-grammar coverage moved to `scripts/mutations/check-plan-file-tags.json`. The full `--mutate .` exact-name run also found no missing `expect`/shortfall path. So I found no evidence that the five CI-surfaced reanchors were only a subset.
