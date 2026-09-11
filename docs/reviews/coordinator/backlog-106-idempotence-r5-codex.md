<!-- codex-review: model=gpt-5.5 -->

**Proof Of Subject**

`git log --oneline origin/master..HEAD`:
```text
8577e525 Round 4: both ends of an override must name a tray part
ded5bbe7 Round 3: delete the repair machinery rather than fix it a third time
51b0803f Round 2: the marked region is verbatim, and the repair is guarded
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page
```

`git diff origin/master...HEAD --stat`:
```text
 .agents/skills/brief/SKILL.md                      |   6 +-
 docs/backlog.md                                    |   2 +-
 docs/dashboard-entries.md                          | 169 ++++++
 .../claude/backlog-106-idempotence-r1-claude.md    | 644 +++++++++++++++++++++
 .../claude/backlog-106-idempotence-r2-claude.md    | 386 ++++++++++++
 .../claude/backlog-106-idempotence-r3-claude.md    | 313 ++++++++++
 .../claude/backlog-106-idempotence-r4-claude.md    | 281 +++++++++
 .../backlog-106-idempotence-r1-codex.md            |  42 ++
 .../backlog-106-idempotence-r2-codex.md            |  70 +++
 .../backlog-106-idempotence-r3-codex.md            |  88 +++
 .../backlog-106-idempotence-r4-codex.md            | 118 ++++
 .../backlog-106-idempotence-r1-codex.verdict.json  |  20 +
 .../backlog-106-idempotence-r2-codex.verdict.json  |  16 +
 .../backlog-106-idempotence-r3-codex.verdict.json  |  20 +
 .../backlog-106-idempotence-r4-codex.verdict.json  |  18 +
 scripts/brief-compose.py                           | 595 ++++++++++++++++++-
 scripts/check-plan-code.py                         | 219 ++++++-
 scripts/check-selftest-counts.py                   |   8 +
 scripts/mutations/brief-compose.json               | 210 +++++++
 scripts/mutations/check-plan-code.json             |  43 +-
 20 files changed, 3221 insertions(+), 47 deletions(-)
```

`git status --porcelain`:
```text
```

**Findings**

Blocking: empty. High: empty. Medium: empty.

Low — The residual denominator is stale in the docs: the numerator is still 32, but I measure `32 of 40` current unmarked tray pages, not `32 of 43`. The repo docs say `32 of the 43` in [docs/backlog.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/backlog.md:134) and [docs/dashboard-entries.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dashboard-entries.md:99). My read-only scan of `~/explainers/` found 52 HTML files, 41 tray pages, 1 marked page (`backlog-table.html`), 40 unmarked tray pages, and 32 unmarked pages carrying the inherited `#tray #qbox` trio with no own fragment trio. So r4’s `32 of 40` matches the live corpus now; `32 of 43` may have been true at an earlier artifact count, but it is not true today. I could not verify PR-body wording: `gh pr view` reports no PR found for this branch.

**Predicate Attacks**

Narrowing did open misses in the non-destructive direction. A page could legitimately write `#tray .in`, `#qbox.wide`, `#qbox:focus`, `body #qbox`, `html #tray #qbox`, `#tray>#qbox`, or grouped overrides like `#tray #qbox, #tray #qt`; current `_is_page_override` misses those unless both whitespace-split ends match `TRAY_SELECTOR` [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:602). That means the override can migrate into the tray on scan [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:661). It is worse than ideal, but not worse than r4’s destructive bug: `#tray .in` is now preserved, and the real tray’s own wrapper rule at `~/explainers/backlog-table.html:374` is no longer subtractable.

`any(... for p in parts[1:])` is not destructive in the shapes named. `#tray .in #qbox`, `#qbox #tray`, and `#tray #tray` all return true, but the destructive case would require that shape to be genuine tray CSS rather than a page-owned override. `#tray .in #qbox` is a plausible page override; `#qbox #tray` is DOM-inverted for this tray; `#tray #tray` needs duplicate IDs. I do not see a destructive hole there. There is a coverage wrinkle: mutating `parts[1:]` to `parts[1:2]` leaves `125/125` green, so “any later part” as distinct from “the next part” is not pinned. That miss is safe-direction only.

**Coverage**

The four r4-uncovered clauses now have named cases and manifest entries:

- Whitespace normalization edit `split()` → `strip()` reddens `the selector is whitespace-normalised before it is split` [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1069), manifest [scripts/mutations/brief-compose.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/brief-compose.json:158).
- Comma guard deletion reddens `a GROUPED selector is one rule for several parts, not an override` [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1071), manifest [scripts/mutations/brief-compose.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/brief-compose.json:171).
- Root check `parts[0]` → `selector` reddens `an override must be ROOTED at a tray part, not merely mention one` [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1073), manifest [scripts/mutations/brief-compose.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/brief-compose.json:184).
- Qualifier clause `any(...)` → `True` reddens `a genuine tray rule that is descendant-rooted is NOT a page override` [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:1057), manifest [scripts/mutations/brief-compose.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/brief-compose.json:197).

The “fifth instance” is only the `any later` vs `immediate later` nuance above; not merge-blocking.

Verification run:
```text
python3 scripts/brief-compose.py --self-test -> 125/125 passed
python3 scripts/check-plan-code.py --self-test -> 101/101 passed
python3 scripts/check-selftest-counts.py -> every declared count verified
```

CONVERGED. Single most important thing to fix: update the residual denominator from `32 of 43` to the current `32 of 40`, or explicitly date it as the older corpus measurement.
