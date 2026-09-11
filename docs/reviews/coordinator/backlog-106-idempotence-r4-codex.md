<!-- codex-review: model=gpt-5.5 -->

**Proof Of Subject**

`git log --oneline origin/master..HEAD`:
```text
ded5bbe7 Round 3: delete the repair machinery rather than fix it a third time
51b0803f Round 2: the marked region is verbatim, and the repair is guarded
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page
```

`git diff origin/master...HEAD --stat`:
```text
 .agents/skills/brief/SKILL.md                      |   6 +-
 docs/backlog.md                                    |   2 +-
 docs/dashboard-entries.md                          | 161 ++++++
 .../claude/backlog-106-idempotence-r1-claude.md    | 644 +++++++++++++++++++++
 .../claude/backlog-106-idempotence-r2-claude.md    | 386 ++++++++++++
 .../claude/backlog-106-idempotence-r3-claude.md    | 313 ++++++++++
 .../backlog-106-idempotence-r1-codex.md            |  42 ++
 .../backlog-106-idempotence-r2-codex.md            |  70 +++
 .../backlog-106-idempotence-r3-codex.md            |  88 +++
 .../backlog-106-idempotence-r1-codex.verdict.json  |  20 +
 .../backlog-106-idempotence-r2-codex.verdict.json  |  16 +
 .../backlog-106-idempotence-r3-codex.verdict.json  |  20 +
 scripts/brief-compose.py                           | 555 +++++++++++++++++-
 scripts/check-plan-code.py                         | 219 ++++++-
 scripts/check-selftest-counts.py                   |   8 +
 scripts/mutations/brief-compose.json               | 171 ++++++
 scripts/mutations/check-plan-code.json             |  43 +-
 17 files changed, 2717 insertions(+), 47 deletions(-)
```

`git status --porcelain`:
```text
```

Read all six prior review halves and read-only inspected `~/explainers/`.

**Blocking**

B1 — `_is_page_override()` treats a genuine tray rule as a page override, so scan migration can delete real tray CSS.

The new predicate says page overrides are descendant selectors rooted at a tray part: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:585). `_selector_scan()` subtracts any rule that is both in the fragment CSS and satisfies that predicate: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:650). But `#tray .in` is not page pollution; it is a real tray layout rule in the live tray: `/Users/kujinlee/explainers/backlog-table.html:374` and `/Users/kujinlee/explainers/goals.html:15752`.

Measured:

```text
input tray: #tray, #qbox, .askbtn, #tray .in, #qt, #sentnote
fragment:  #tray .in{max-width:53rem;margin:0 auto}
output:    #tray, #qbox, .askbtn, #qt, #sentnote
lost_in=True
```

Damage: the tray’s `.in` wrapper loses `max-width:53rem;margin:0 auto`, so the tray contents stop being width-bound/centered. This is exactly the r3 class in a new shape: duplicate a genuine tray rule, and the replacement guard approves deleting it. The old structural floor is gone, and the new “shape” rule is not sufficient because genuine tray CSS can itself be descendant-rooted.

**High**

H1 — The premise “page override must be tray-rooted descendant” is false for plausible cascade-winning overrides.

`gen-backlog-page.py` uses `#tray #qbox` because plain `#qbox` loses to the lifted tray: [scripts/gen-backlog-page.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:1474), [scripts/gen-backlog-page.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:1480). But `body #qbox` also beats plain `#qbox` by specificity and is a perfectly plausible page override. Today `_tray_rules()` selects it, `_is_page_override()` rejects it because `parts[0] == "body"`, and `_selector_scan()` migrates it into the tray.

Measured selector outcomes:

```text
#qbox.wide                 selected, not subtracted
body #qbox                 selected, not subtracted
:where(#tray) #qbox        selected, subtracted
@media{#tray #qbox{...}}   flattened to #tray #qbox, subtracted
@media{body #qbox{...}}    flattened to body #qbox, not subtracted
#tray>#qbox                selected, not subtracted
#tray > #qbox              selected, subtracted
#tray+#qbox                selected, not subtracted
#tray + #qbox              selected, subtracted
```

So the current rule is neither “descendant” nor “all plausible overrides.” It is “whitespace-split first token matches the tray regex.”

**Medium**

M1 — The parsing clauses are undercovered.

The implementation normalizes whitespace, rejects commas, splits on spaces, and checks only `parts[0]`: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:602). I mutation-checked those clauses in memory:

```text
len(parts) > 2                         -> 5 named failures
bare selectors count as overrides       -> 3 named failures
drop whitespace normalization           -> 0 failures
drop comma guard                        -> 0 failures
root on any matching part               -> 0 failures
root on parts[1]                        -> 0 failures
```

So only the bare-vs-descendant and minimum length behavior are pinned. The fourth uncovered guard is the root-position guard: `#foo #qbox` currently does not count as an override, and changing the implementation to treat any later tray token as rooted enough leaves 119/119 green.

M2 — Deleting `--remigrate`, `pollution()`, `remigration_risk()`, `_all_rules()`, 15 cases, and 4 manifest entries removed live guard behavior that no longer exists.

That deletion is mostly defensible because the machinery repeatedly produced worse behavior, and marked extraction is now verbatim: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:697). But the removed cases also pinned the “repair/warn about already-marked pollution” behavior. That behavior is now intentionally absent. The branch should be honest that inherited or already-marked pollution is no longer detectable, only bounded by verbatim extraction plus de-dupe on future unmarked scans.

**Low**

L1 — Comma handling is conservative but untested. `#tray, #qbox #qt` is preserved, not subtracted. That is safer than deleting grouped tray CSS, but it also means a grouped page override can still migrate. I would keep the behavior, add the case.

L2 — Comments/tabs/newlines mostly work by accident of normalization. `#tray/*x*/ #qbox` is normalized by `_tray_rules()` before `_is_page_override()` sees it; tabs/newlines become spaces and subtract. Good behavior, but not pinned.

**Residual**

Accepting r3 H3 is defensible only as a stated limitation, not as a correctness claim. Marked extraction is verbatim, and scan de-duplication keeps inherited pollution at one copy, so the 12.4 MB growth class is closed. But inherited pollution still wins the cascade and is invisible once the descendant page’s fragment no longer declares the rule. That is okay for backlog #106 idempotence; it is not a full pollution-repair story.

Verification run:
```text
python3 scripts/brief-compose.py --self-test -> 119/119 passed
python3 scripts/check-plan-code.py --self-test -> 101/101 passed
python3 scripts/check-selftest-counts.py -> every declared count verified
```

NOT CONVERGED. Single most important fix: make `_is_page_override()` stop classifying genuine tray descendant rules like `#tray .in` as page overrides; selector shape alone is too broad.
