<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking**: `_BLOCK_SCALAR` still misses valid dash-opened block scalar spellings, so the guard can still false-green. The new regex at [scripts/check-python-pin.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:311) only accepts an unquoted bare key and no node property before `|`/`>`. These both still pass incorrectly:

```text
--- anchor
declared ['3.12', '3.12']
unpinned []
verdict (0, 'python pin OK — every job pins 3.12, and this interpreter is 3.12, from /tmp/py')
--- quoted
declared ['3.12', '3.12']
unpinned []
verdict (0, 'python pin OK — every job pins 3.12, and this interpreter is 3.12, from /tmp/py')
```

Fixtures used `- run: &x |` and `- "run": |`. Ruby Psych parses both as YAML; GitHub Actions now supports YAML anchors/aliases per GitHub’s changelog and docs, and workflow files are YAML syntax. Sources: [GitHub changelog](https://github.blog/changelog/2025-09-18-actions-yaml-anchors-and-non-public-workflow-templates/), [GitHub Docs](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations). This is the same false-green class as #154, not just a fail-closed bound.

**Medium**: the “live path” self-test does not exercise the `pin_took_effect` interaction it claims. The case at [scripts/check-python-pin.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:920) calls only `unpinned_jobs(...)`; `pin_took_effect` is reached only inside `verdict(...)` at [scripts/check-python-pin.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:605). It is still load-bearing for the all-jobs reader, but the comment overclaims the tested path.

**Low**: the manifest fails the strict “no duplicate anchor with any other entry” mandate. My manifest scan found a shared edit anchor between entries 35 and 38:

```text
DUP_ANCHOR scripts/check-python-pin.py [(35, "any steps: key re-scopes..."), (38, "job keys stop being excluded...")]
```

The shipped harness allows this because it only rejects identical full anchor tuples at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1127) and [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1155). The two #154 entries themselves each had exactly one anchor match.

**Low**: the explanatory comment overstates the current call path. It says `Step.body` blanks the dash before `_structural` sees the line at [scripts/check-python-pin.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:303), but current `_steps()` calls `_structural(text.split("\n"))` first at [scripts/check-python-pin.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:232); `Step.body` is built later at [scripts/check-python-pin.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:264).

**Sound Checks**

The core ordinary fix is real. Reverting only the dash-scalar regex in a temp copy made all three #154 cases red:

```text
[FAIL] ...and a job holding only those still reports as unpinned
[FAIL] a pin quoted inside a DASH-opened block scalar is not a pin
[FAIL] ...so a SIBLING job pinned only by heredoc text is still unpinned
83/86 passed
```

The original false green also reproduces with only that regex reverted:

```text
declared ['3.12', '3.12']
unpinned []
verdict ci good provenance (0, 'python pin OK — every job pins 3.12, and this interpreter is 3.12, from /tmp/py')
```

The group(1) indent choice looks sound for ordinary YAML. I tested `-   run: >`, `-\trun: |`, `|-`, `|+`, `>2 # c`; the regex matches them. Ruby rejected the “line between dash column and key column” termination/body examples I constructed, so I did not find a valid YAML counterexample there.

The deleted mutation sounds right to delete: stripping `uses:` from the repaired fixture makes the case vacuous. The replacement behavior mutation exists: entry 29 removes the dash opener from `_BLOCK_SCALAR`, and it reddens the named dash case plus the repaired/two-job cases.

**Counts And Runs**

Ran:

```text
python3 scripts/check-python-pin.py --self-test
86/86 passed

python3 scripts/check-selftest-counts.py
self-test counts: 45 script(s) declare a count, every one verified by running it

python3 scripts/check-plan-code.py --self-test
128/128 passed

python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 52 file(s), 869 mutation(s), 869 killed, 869 attributed to the case each names, 0 survivor(s)
```

Re-derived counts: manifest entries `40`, `EXPECTED_MUTATIONS["scripts/check-python-pin.py"] == 40`, declared sum `869`, docstring count `86`.

No repo files were modified during review.
