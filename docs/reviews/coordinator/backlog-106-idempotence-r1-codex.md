<!-- codex-review: model=gpt-5.5 -->

**Proof Subject**
`git log --oneline origin/master..HEAD`:
`370144b1 Backlog #106: composing a page twice now produces the same page`

`git diff origin/master...HEAD --stat` changed-file list:
```text
.agents/skills/brief/SKILL.md
docs/backlog.md
docs/dashboard-entries.md
scripts/brief-compose.py
scripts/check-plan-code.py
scripts/check-selftest-counts.py
scripts/mutations/brief-compose.json
scripts/mutations/check-plan-code.json
```

**Findings**

**Medium — Legacy migration still promotes `gen-backlog-page.py`’s fragment-specific qbox overrides into the reusable tray.**  
`_selector_scan` keeps any selector matching `#tray|\.askbtn|#qbox|#qt\b|#sentnote|#modechip` and then keeps the last exact rule: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:576). Legacy pages with `TRAY_BEGIN` but no `TRAY_END` take that scan path: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:613). `compose()` then writes whatever `css` came back between the new markers: [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:728).

The problem is that the three backlog qbox overrides are explicitly source-page overrides, not tray source: [scripts/gen-backlog-page.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:1474) says they exist because plain `#qbox` loses to the lifted tray, and the actual rules are at [scripts/gen-backlog-page.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:1480). On the live read-only corpus, `~/explainers/goals.html` is a begin-only legacy page and already contains these rules at `/Users/kujinlee/explainers/goals.html:140`. Extracting from it on this branch returns those rules as part of the tray CSS.

This closes unbounded growth, but not the claim that the fragment’s own `#tray #qbox` overrides stop being lifted. They are lifted once during migration and then frozen inside `TRAY_BEGIN`/`TRAY_END` for future pages. Falsifier for a fix: recompose a legacy begin-only source that contains the `gen-backlog-page.py` `#tray #qbox` rules; the newly marked tray region should not contain those three `#tray #qbox*` selectors, while a backlog page’s own fragment should still contain them outside the tray markers.

**Notes**

I did not find Blocking or High issues.

The author’s four comment-only selector claim checks out against current live legacy pages I could still inspect: `goals.html`, `dashboard.html`, and `2026-09-08-brief-plan-mode-question.html` all produced `.titleline`, `:where(h1, h2, h3, h4)`, `body`, and `h1,h2,h3` as the unique comment-only matches. Of those, `:where(h1, h2, h3, h4)` is load-bearing for heading ask-button geometry, but it is still supplied by `SHIM` at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:116), so dropping it from lifted tray CSS is okay.

Mutation manifest: `scripts/mutations/brief-compose.json` has 8 entries, and my anchor scan found no shared edit anchors. Full mutation run passed: `OK — delivered scripts mutated: 38 file(s), 421 mutation(s), 0 survivor(s)`. That satisfies the §22 attribution concern at the runner level; the failures are parseable after the branch’s `[FAIL]` printer change.

`globals()["ROOT"] = _r` is restored exception-safely by `finally` at [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1419). The `find_source(root=None)` change is behaviorally relevant only for callers that mutate module global `ROOT`; ordinary callers still resolve to `ROOT` at call time via [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:527).

Verification run:
`python3 scripts/brief-compose.py --self-test` → `102/102 passed`  
`python3 scripts/check-plan-code.py --self-test` → `93/93 passed`  
`python3 scripts/check-selftest-counts.py` → all 34 declared counts verified  
Browser probe on a temp composed page from legacy `goals.html`: h2/h3 ask buttons were separate and hit-testable; `#tray` rendered; `#qbox` had visible border/background. Byte comparison alone would not catch the failure where heading ask buttons stack because the positioning rule disappeared.
