<!-- codex-review: model=gpt-5.5 -->

**Proof Of Subject**
`git log --oneline origin/master..HEAD`:
```text
51b0803f Round 2: the marked region is verbatim, and the repair is guarded
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page
```

`git diff origin/master...HEAD --stat`:
```text
 .agents/skills/brief/SKILL.md                      |   6 +-
 docs/backlog.md                                    |   2 +-
 docs/dashboard-entries.md                          | 106 ++++
 .../claude/backlog-106-idempotence-r1-claude.md    | 644 ++++++++++++++++++++
 .../claude/backlog-106-idempotence-r2-claude.md    | 386 ++++++++++++
 .../backlog-106-idempotence-r1-codex.md            |  42 ++
 .../backlog-106-idempotence-r2-codex.md            |  70 +++
 .../backlog-106-idempotence-r1-codex.verdict.json  |  20 +
 .../backlog-106-idempotence-r2-codex.verdict.json  |  16 +
 scripts/brief-compose.py                           | 667 ++++++++++++++++++++-
 scripts/check-plan-code.py                         | 219 ++++++-
 scripts/check-selftest-counts.py                   |   8 +
 scripts/mutations/brief-compose.json               | 236 ++++++++
 scripts/mutations/check-plan-code.json             |  43 +-
 14 files changed, 2418 insertions(+), 47 deletions(-)
```

`git status --porcelain`:
```text
```

Tree is clean.

**Blocking**
B1 — The M1 floor still permits a partial tray with no `.askbtn` CSS.

The code says the floor is “the selectors without which what survives is not a tray: its container and its input” and defines only `("#tray", "#qbox")`: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:555). `_selector_scan` then allows subtraction whenever those two tokens survive: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:662), [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:667), [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:668).

But this same block documents the measured partial-loss class as `['.askbtn', '#tray', '#qbox']` and names `.askbtn` as one of “the tray’s load-bearing three”: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:656). The heading ask path depends on `.askbtn`: the shim explains the tray appends absolutely positioned `.askbtn` buttons to headings, and without the affordance geometry the heading path silently dies: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:118), [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:126). The self-test repeats that this is about the painted affordance, not just the handler: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1384).

Measured through production `main()` in a temp directory: a begin-only source with `#tray`, `.askbtn`, and `#qbox`, plus a fragment declaring the same `.askbtn` rule, exits `0`, writes output, and the marked tray region becomes only:
```text
#tray{a:1}
#qbox{b:2}
```
`askbtn_count` in the tray region was `0`; no warning fired. This is the fourth uncovered guard: the case added for the floor only proves `#tray`/`#qbox` loss is caught: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1066). It also explicitly asserts that subtraction may proceed when those two remain: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1069). It never asks whether `.askbtn` survived.

Fix: add `.askbtn` to `TRAY_STRUCTURE`, or replace the token floor with an explicit required-selector set for every tray affordance that must survive scan-path subtraction.

**High**
Empty.

**Medium**
Empty.

**Low**
Empty.

**Other Attacks**
Marked path: current `extract_tray` really is verbatim when markers exist and `--remigrate` is absent: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:706), [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:715).

`pollution()`/normal warning: read-only scan of `~/explainers/` found 52 HTML files, 1 currently marked page, 38 begin-only legacy pages, and 0 current marked-region duplicate hits with sibling fragments. I am not filing the warning as noisy in the live corpus.

Round-2 production edits verified in temp copies:
```text
brief #14 main stops passing --remigrate -> expected case failed
brief #15 pollution warning silenced -> expected case failed
brief #16 risk guard disabled -> expected case failed
brief #17 nothing-to-repair guard disabled -> expected case failed
brief #18 structure floor weakened -> expected case failed
check-plan-code #34 red-with-no-readable branch dropped -> expected case failed
check-plan-code #35 tally drops killed/attributed -> expected case failed
check-plan-code #36 per-mutation attributed removed -> expected case failed
```
Those entries are in [scripts/mutations/brief-compose.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/brief-compose.json:171) and [scripts/mutations/check-plan-code.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/check-plan-code.json:371).

Verification run:
```text
python3 scripts/brief-compose.py --self-test -> 130/130 passed
python3 scripts/check-plan-code.py --self-test -> 101/101 passed
python3 scripts/check-selftest-counts.py -> every declared count verified
```

I did not run `--mutate .`.

NOT CONVERGED. Single most important fix: make the scan-path structural floor require `.askbtn` to survive partial subtraction.
