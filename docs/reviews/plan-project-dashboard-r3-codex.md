<!-- codex-review: model=gpt-5 -->

READY TO EXECUTE: NO

Shortest must-change list: make the visible Python blocks reproduce the claimed runs; fix `_ordered` for consecutive malformed blocks; add a mutation-catching check for the day anchors.

Blocking — “Every Python block below was executed before it was written down, and then EXTRACTED PROGRAMMATICALLY from the file that was executed … The suites stand at 70/70 (generator) and 42/42 (gate)”
What I checked: programmatically extracted every fenced Python block from `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`, wrote the exact concatenations to `/tmp/dashboard-plan-r3-assembled/check-dashboard-entry.py` and `/tmp/dashboard-plan-r3-assembled/gen-dashboard.py`, then ran them and Task 1 Step 6’s controls verbatim in a throwaway git repo.
Actually true: the visible gate blocks do not contain an entrypoint, so running the script is a false green and the control harness “passes” for the wrong reason:
```text
=== run check-dashboard-entry.py rc=0
(no output)

A rc=0
B rc=0
C rc=0
+## not-a-date
D rc=0
E rc=0
  ## 2026-08-28-foo                rc=0
  ## 2026-08-28.                   rc=0
  ## 2026-08-28 [needs-yo]         rc=0
  ## 2026-08-28 rambling title     rc=0
  ##2026-08-28                     rc=0
```
The plan’s required A/C/D/F refusals were never exercised. The only reason the gate’s suite reaches `42/42` is by importing the assembled module and calling `_self_test()` manually, which is not what Task 1 tells the implementer to run.
VERIFIED

Blocking — “Every Python block below was executed … 33 symbols, verified byte-for-byte against the running copy”
What I checked: the same exact extraction, then `python3 -c '…exec_module…; print(m._self_test())'` against the assembled generator file, plus a symbol scan of the fenced Python blocks.
Actually true: the visible generator blocks are not the claimed running copy. The exact concatenation dies before the suite can run, because prose-stated globals are missing from the code blocks, and Task 3’s collector symbols are not embedded at all:
```text
=== import+_self_test gen-dashboard.py rc=1
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    ...
  File "/tmp/dashboard-plan-r3-assembled/gen-dashboard.py", line 348, in _self_test
    e = parse_entries("## 2026-08-28 [needs-you]\nFixed a thing.\n")
  File "/tmp/dashboard-plan-r3-assembled/gen-dashboard.py", line 36, in parse_entries
    if BLOCK.match(line):
       ^^^^^
NameError: name 'BLOCK' is not defined
```
Search results in the plan show `commit_dates`, `open_prs`, and `no_entry_prs` only in prose lines, not in any fenced Python block. Counting the fenced top-level Python symbols yields `27`, not the claimed `33`. The only way to reach `70/70` is to inject non-fenced code (`TECH_MARKER`, `BLOCK`, imports) in a harness, which disproves the byte-identical extraction claim.
VERIFIED

High — “That formulation is order-agnostic” / “malformed block stays adjacent to its file neighbours”
What I checked: using the exact extracted generator logic with only the prose-stated globals injected, parsed and rendered the malformed-order fixtures the plan calls out, including several consecutive malformed blocks.
Actually true: two consecutive malformed blocks between two valid entries render in reverse file order:
```text
two-consecutive-malformed [('Newest good.', 4083), ('Older good.', 4730), ('Broken A.', 4542), ('Broken B.', 4361)]
```
That order is `Newest good.` → `Broken B.` → `Broken A.` → `Older good.`. The malformed run stays between the valid neighbours, but it does not keep file order inside the malformed run. The v3 splice fixes the single-malformed case and still gets the multi-malformed case wrong.
VERIFIED

High — “§5 the chart | Tasks 3–4 | ✅ … the bar→entry anchor” / “Every ✅ below was mutation-tested”
What I checked: mutated the extracted generator to delete the day-anchor emission in `build()` while leaving the bar `href="#day-..."` logic intact, then re-ran the plan’s `70/70` suite.
Actually true: the suite stays green after the anchor target is removed:
```text
=== remove day_anchor emission rc 0
70/70 passed
0
```
This means the named “bar→entry anchor” behavior is not actually covered by the suite. The bars still “link” in the HTML string, but they link to nowhere; the Self-Review’s ✅ is unearned.
VERIFIED

What I ran

- Extracted every fenced Python block from the plan into `/tmp/dashboard-plan-r3-run` and executed each one as its own file.
- Exact concatenations:
```text
=== run check-dashboard-entry.py rc=0
(no output)
=== import+_self_test check-dashboard-entry.py rc=0
42/42 passed
0

=== run gen-dashboard.py rc=0
(no output)
=== import+_self_test gen-dashboard.py rc=1
NameError: name 'BLOCK' is not defined
```
- Generator harness using the exact extracted logic plus only the prose-stated globals:
```text
=== gen-dashboard-harness.py self-test rc=0
70/70 passed
0
```
- Mutation checks I ran:
```text
=== remove day_anchor emission rc 0
70/70 passed
0

=== reverse chart note phrase rc 0
[FAIL] the chart says what it under-counts
69/70 passed
1

=== drop open PR rows rc 0
[FAIL] an open PR appears in what-needs-you
[FAIL] the open PR is numbered
68/70 passed
1
```
- Local `fetch-depth: 0` shape reproduction with a base branch containing a slash (`release/foo`):
```text
(['lib/x.ts'], False, None)
```
That part does run locally once full history is present. GitHub itself was NOT RUN.
- Browser/manual checks were NOT RUN: Task 5’s live-reload fold behavior, the Ask tray, and the affordance probe all need a real implementation served in a browser, not a plan transcription.

NOT CONVERGED
