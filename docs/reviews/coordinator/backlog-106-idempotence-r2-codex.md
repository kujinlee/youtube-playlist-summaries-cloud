<!-- codex-review: model=gpt-5.5 -->

`git log --oneline origin/master..HEAD`:

```text
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page
```

`git diff origin/master...HEAD --stat`:

```text
 .agents/skills/brief/SKILL.md                      |   6 +-
 docs/backlog.md                                    |   2 +-
 docs/dashboard-entries.md                          |  40 ++
 .../claude/backlog-106-idempotence-r1-claude.md    | 644 +++++++++++++++++++++
 .../backlog-106-idempotence-r1-codex.md            |  42 ++
 .../backlog-106-idempotence-r1-codex.verdict.json  |  20 +
 scripts/brief-compose.py                           | 501 +++++++++++++++-
 scripts/check-plan-code.py                         | 120 +++-
 scripts/check-selftest-counts.py                   |   8 +
 scripts/mutations/brief-compose.json               | 171 ++++++
 scripts/mutations/check-plan-code.json             |  13 +
 11 files changed, 1530 insertions(+), 37 deletions(-)
```

`git status --porcelain` produced no output: tree is clean.

**Blocking**
`_without_page_rules` still does substring removal, not whole-rule removal, and the marker path now runs it unconditionally after slicing the stated region. `extract_tray()` takes the marked CSS at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:689), then calls `_without_page_rules` at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:694). `_without_page_rules` builds fragment-owned rules with `_tray_rules` at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:644), then removes the first matching raw substring from `css` at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:653).

That is not whole-rule bounded. Constructed through the same production path, with fragment CSS from `css_of(content)`:

```text
css='.x#tray{a:1}\n#qbox{b:2}'
fragment owns '#tray{a:1}'
out='.x#qbox{b:2}'
```

and:

```text
css='@media (max-width:40rem){#tray{a:1}}\n#qbox{b:2}'
fragment owns '#tray{a:1}'
out='@media (max-width:40rem){}\n#qbox{b:2}'
```

So it can remove `#tray{...}` from inside `.x#tray{...}` or from inside an `@media` block, neither of which is the fragment’s whole top-level rule. This is reachable on the marker branch because `main()` reads the fragment before extraction and passes `css_of(content)` into `extract_tray` at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:840) and [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:844). It reintroduces the branch’s own defect shape: a “verbatim” marked region is still transformed by inference.

The MARKER-path subtraction is justified only by the already-polluted marked pages described in the new docstring at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:611). But r1 Claude’s other side is stronger now: this is permanent hot-path CSS surgery for a finite migration problem. The right fix is either an explicit one-off migration, or a bounded whole-rule remover that refuses ambiguity. The current substring transform is not the right permanent shape.

**High**
Empty.

**Medium**
Empty.

**Low**
Empty.

**Case/Manifest Notes**
The new round-2 cases do reach the branches they claim: the scan fixture is begin-only at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1554), the marker fixture includes real markers and fragment-owned CSS at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1582), and the END-marker case uses an exotic tray so fallback to scan is observably lossy at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1603). The removed manifest entry for `if not own` is correctly equivalent after text subtraction.

`_report_line` is ceremony-ish but useful ceremony: `check-plan-code` parses `[FAIL]` lines as a producer/consumer contract, and the parser behavior is documented around [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:979). Pinning the producer at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:918) adds real value because this branch already lost attribution once to output format drift.

What still wasn’t measured: whole-rule boundaries for `_without_page_rules`. The suite measures “doesn’t rebuild from `_tray_rules`” and “doesn’t flatten `@media` by rebuilding,” but not “subtraction only removes a complete sibling rule.” That is the sharp missing population.

Verification run: `python3 scripts/brief-compose.py --self-test` → `115/115 passed`; `python3 scripts/check-plan-code.py --self-test` → `93/93 passed`; `python3 scripts/check-selftest-counts.py` → all 34 counts verified.

NOT CONVERGED. Most important fix: make `_without_page_rules` subtract only complete top-level rule spans, or remove it from the permanent marker hot path and do an explicit migration.
