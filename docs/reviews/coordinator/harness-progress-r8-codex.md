<!-- codex-review: model=gpt-5.5 -->

NOT CONVERGED.

**Proof Of Subject**

`git log --oneline origin/master..HEAD`:

```text
e314c235 Round 7: the guard failed the way it was built to detect
48d8cabb Round 6: ask the fixture question with a script, not with a reviewer
6a660454 Round 5: a fixture must differ from itself along the axis it tests
d6f55881 Round 4: an input far inside the boundary pins nothing, a third time
c3d53a70 Round 3: the want was not the only thing deriving from its subject
5e4bd163 Round 2: a guard whose want moves with its subject has no ceiling
b64b4cbc Round 1: inject the reporter, instead of emitting progress
915dfa67 File the review round for the progress change — both halves NOT CONVERGED
7ae516fc The mutation harness says where it is, instead of going silent for minutes
```

`git show --stat e314c235` showed:

```text
8 files changed, 1138 insertions(+), 40 deletions(-)
docs/reviews/claude/harness-progress-r7-claude.md
docs/reviews/coordinator/harness-progress-r7-codex.md
docs/reviews/verdicts/harness-progress-r7-codex.verdict.json
scripts/check-fixture-variation.py
scripts/check-plan-code.py
scripts/mutations/check-fixture-variation.json
scripts/mutations/check-plan-code.json
docs/dashboard-entries.md
```

Controls first:

```text
check-plan-code --self-test: 128/128 passed
check-fixture-variation --self-test: 38/38 passed
check-fixture-variation: OK — 484 parameter(s), 48 file(s)
--mutate .: 39 files, 493 mutations, 493 killed, 493 attributed, 0 survivors, exit 0
```

**Blocking**

1. [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:92) pins population by count, not identity, so an examined script can disappear while the guard reports OK.

Premise: discovery skips parse failures at [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:97), only enforces `POPULATION_FLOOR` after counting targets at [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:411), and [scripts/check-docs.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-docs.py:542) is currently one of the discovered self-test scripts.

Measurement in a temp copy:

```text
CONTROL rc 0
fixture variation OK — 484 parameter(s) examined across 48 file(s)

# make scripts/check-docs.py unparseable; add scripts/zz_replacement_suite.py with a clean self_test
PROBE rc 0
fixture variation OK — 485 parameter(s) examined across 48 file(s)

POP 48 contains_check_docs False contains_replacement True
```

Failing scenario: a previously examined guard becomes unparseable or otherwise undiscoverable, while a new script keeps the population count at 48. The guard says OK over a different set. This is exactly the “count holds, set changed” failure mode.

2. [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:114) can hide a new finding behind an old `KNOWN_UNVARIED` key.

Premise: the ratchet is keyed only by `t.name` and `function.parameter` at [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:373), and `check-dashboard-entry.py` already ratchets `fence_closes.open_run` at [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:135). Only two files have examined floors at [scripts/check-fixture-variation.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:221), so this file can shrink without tripping H1’s floor.

Measurement in a temp copy: replace `scripts/check-dashboard-entry.py` with a different tiny script whose only unvaried parameter is `fence_closes.open_run`.

```text
CONTROL 0
fixture variation OK — 484 parameter(s) examined across 48 file(s)

PROBE 0
fixture variation OK — 466 parameter(s) examined across 48 file(s)
```

Removing only the old ratchet key made the same subject fail:

```text
WITHOUT_RATCHET_KEY 1
FAILED — 1 parameter(s) never varied by any case:
  ✗ check-dashboard-entry.py: `fence_closes(open_run=…)` is passed the SAME value...
```

Failing scenario: a file is rewritten or renamed into an old basename/key shape; a fresh unvaried parameter is swallowed as historical debt, with no debt-paid line and no examined-floor failure.

**High**

Empty.

**Medium**

Empty.

**Low**

Empty.

**Named Attacks That Held**

The r7 manifest population is counted correctly: `scripts/mutations/check-fixture-variation.json` has 22 entries, and the full `--mutate .` run attributed all 493 mutations, including entries `[131/493]` through `[152/493]`.

`dead_exemptions` held the intended any/all edge: one-file needed exemption passes, needed-only-in-second-file passes, dead exemption reports. `dead_exemptions([])` reports dead, but `main()` refuses empty/unreadable populations before that helper matters.

**What I Did Not Measure**

I did not classify all 124 ratcheted names for semantic freshness. I did not test non-`.py` scripts or async self-test spellings. I did not propose a redesign; the measured failures are coverage identity failures in r7’s current method.

I did not edit the repo. I observed an untracked `docs/reviews/claude/harness-progress-r8-claude.md` after the run and left it alone.
