# Round 3 — `backlog-multi-tag` (backlog #381, PR #421) — Claude half

Subject: HEAD `988a5dbf`. Scope: `git diff 65ef2b68..988a5dbf` (the round-2 schema fold and the docs fix), read in
the context of `git diff origin/master...HEAD`. Mandate: refute the bet in the last `backlog-multi-tag` row of
`docs/reviews/decision-scheme/decision-log.jsonl`. The bet says no table shape or header lets a reader accept a table
while losing a row's tags, and no gate is looser than master's.

**The bet is refuted.** The gate is looser than master's on a row whose number cell is decorated. The header-schema
fold is sound for every header probe I ran. The hole is next to it: it is the row branch that `check-features` stopped
reading when round 1 moved it onto the shared parser.

Method: I built `origin/master` and HEAD trees in a `mktemp -d` with `git archive` (`scripts/` plus
`docs/{features,anchors,backlog}.md`). For each probe I appended the block to that ref's own `docs/backlog.md` and ran
that ref's `scripts/check-features.py` with a temp `HOME`. The probe tag is `(not-claimed)`, which no node claims, so
any reader that reads the row correctly goes red. Both unmodified controls exit 0: master reports 21 areas, HEAD 22.

## Findings

### C1 — Major — `scripts/check-features.py:188` (`backlog_areas`): the parser's unread lines are thrown away, so a decorated row is dropped from the gate in silence, and the gate passes where master's fails

`backlog_areas` calls `bp.parse(text.split("\n"))` without the `unread=` out-parameter. `parse` reads a row only if
it matches `^\|\s*\d+\s*\|` (`scripts/gen-backlog-page.py:1093`). Any other row-shaped line inside a table goes into
`unread` (`:1117-1118`) and is not returned as a row. The backlog page reports those lines as `⚠ UNREAD`.
`check-features` never asks for them, so the row's tags drop out of `areas_in_use` and nothing reports it. Master's
`backlog_areas` read every line that starts with `"| "` and has at least 7 cells, positionally. It saw these rows and
went red.

Executed, with each probe appended in a new `## Probe` section under a valid six-column header (exit codes are master
first, then HEAD):

| Probe row (number cell) | master | HEAD |
|---|---|---|
| `\| ⭐999 \| … \| (not-claimed) \| open \|` | **1** — `(not-claimed)` is claimed by no node | **0** — "22 backlog areas all claimed exactly once" |
| `\| #999 \| …` | **1** | **0** |
| `\| **999** \| …` | **1** | **0** |
| `\| 999a \| …` | **1** | **0** |

The same thing happens inside the real `## Items` table, with no new section. I inserted
`| ⭐999 | 🟡 **Probe** | f | S | (tooling) (not-claimed) | open |` directly under the real delimiter. Master exits 1
(`(tooling) (not-claimed)` claimed by no node), HEAD exits 0.

On the `999a` tree I called `parse(..., unread=u)` directly: 336 rows, row 999 absent, and
`u == ['| 999a | 🟡 **Probe** | f | S | (not-claimed) | open |']`. The parser knows about the line. Only the gate
discards it.

This is backlog #110's decoration class (⭐, #, bold), and the parser already has a channel for it. The fault is in
the consumer. It came in with the round-1 fold (XM2, `133d08b1`), and Codex r2 did not probe it, so the bet as written
was never true. `gen-features-page.backlog_rows` (`scripts/gen-features-page.py:258`) also drops the `unread`
argument, so the row is missing from `/features` too. That part is pre-existing: master's `gen-features-page` already
read through `parse`. The gate is the part that is looser than master.

**Fix (verified in a temp copy):** in `backlog_areas`, pass `unread: list[str] = []` to `bp.parse` and add one
problem per unread line to `bad`, for example
`docs/backlog.md line '<line[:60]>' sits in a table and was not read as a row`. The patched copy gave:

- the real backlog: exit 0, unchanged (the real file has **0** unread lines today, measured);
- the `⭐999` and `999a` probes: exit 1, with the line named;
- `--self-test`: 45/45 still green.

Add a regression case using the `⭐999` probe, plus a mutation that drops the new problem line, attributed to that
case. Optionally, have `gen-features-page` surface `unread` the same way. That is pre-existing and can be filed
separately.

## The other probes held: HEAD is never green where master is red

| Probe | master | HEAD | Note |
|---|---|---|---|
| header case and extra spaces (`ITEM`, `  Size  `, `BUNDLE`) | 1 | 1 | read correctly |
| reordered: `… Size \| Status \| Bundle` | 0 | 1 | master read `Status` positionally and missed the tag; HEAD refuses the header |
| reordered: `… Item \| Bundle \| Touches …` | 0 | 1 | same |
| duplicate `Bundle` column | 1 | 1 | HEAD refuses the header |
| extra `Note` column | 0 | 1 | HEAD refuses |
| missing `Status` | 0 | 1 | HEAD refuses |
| 3 columns, `# \| Item \| Bundle` | 0 | 1 | HEAD refuses (master skipped rows with fewer than 7 cells) |
| no header, delimiter + row | 1 | 1 | HEAD: row under an empty header raises `ShapeError` |
| non-`#` header `\| No \| Item …` in a new section | 1 | 1 | rows under no `\| # \|` header raise |
| two headers in one section, second misspells `Bundel` | 1 | 1 | the second `\| # \|` header is checked too |
| two headers in one section, second is `\| No \| …` | 1 | 1 | rows are read under the first header, and the second header line is reported unread on the page |
| header + row inside a ```` ``` ```` fence | 1 | 1 | both read fenced rows (pre-existing; the `parse` comment records it) |
| alignment row `\|:---\|:---:\|---:\|:-\|-\|:--:\|` | 1 | 1 | |
| literal `\|` in Item (7 cells) | 1 | 1 | HEAD: width `ShapeError` |
| escaped `\|` in Item | 1 | 1 | read as one cell |
| literal `\|` in Item plus a missing cell (6 cells) | 1 | 1 | the tag still lands in the Bundle slot |
| missing trailing pipe | 0 | 1 | HEAD: width `ShapeError` |
| tab-separated number cell | 0 | 1 | |
| leading space before the row | 0 | 0 | both skip it (HEAD puts it in `unread`, so the C1 fix covers it too) |
| `###` heading + row | 1 | 1 | |

Observation, not a finding: a fenced example table whose `| # |` header is not a declared schema, such as
`| # | Key | Note |`, is now a `ShapeError` for the page and the gate (master 0, HEAD 1). That is stricter than
master, not looser. `docs/backlog.md` has 0 fences today. If an example table is ever wanted, the fence handling the
`parse` comment defers is the fix.

## Other requested checks

| Check | Executed result |
|---|---|
| `TABLE_SCHEMAS` against the real `docs/backlog.md` | Exactly two `\| # \|` headers (lines 30 and 376), one per schema. The real file parses to 336 rows with 0 unread. No other table in the file starts with `\| # \|`, so none is accepted by accident. |
| Mutations, `--mutate . --only` | gen-backlog-page **18/18** killed and attributed; check-features **28/28**; gen-features-page **15/15**. Green controls and re-controls in every run. |
| `EXPECTED_MUTATIONS` | AST-read declared sum **2327** = manifest entries **2327**, with no per-file mismatch. The pinned self-test case reads 2327. `check-plan-code --self-test` passed 246/246. |
| Self-tests | gen-backlog-page **182/182**, check-features **45/45**, gen-features-page **18/18** |
| Counts against `collect`'s `match_rows`, open rows only | status-pages 14 (🟠3 🟡8 🟢3), feature-map 2 (🟡2), explainer-pages 19 (🟠4 🟡10 🟢5), **30 distinct**. These match the #381 row, the dashboard entry and the PR #421 body. |
| Page renders, temp `HOME` with a seeded Ask tray | backlog page: 336 rows, 213 open, tray lifted, multi-tag `data-tags` present (for example `tooling\|comprehensibility\|comprehensibility / explainers` ×9). Features page: 26 nodes, 515 fragments. |
| 988a5dbf docs fix | The #381 row is 6 cells again, and `check-docs` exits 0. Nit: the commit message credits "the schema check" for catching the 8-cell row. It was the width (shape) check. |
| Prose nit | The dashboard says "Measured on the real backlog: 334 rows". That was the count when it was measured; HEAD parses 336 (rows 380 and 382 came in with the master merge). It is accurate as history, so I am not raising it as a finding. |

## Classification

```yaml
round: 3
half: claude
subject: backlog-multi-tag
findings:
  - {id: C1, severity: Major, aim: deliverable, fix_induced: true, induced_by: r1 XM2 fold (133d08b1), component: check-features consumer of the shared parser}
```

VERDICT: NOT CONVERGED
