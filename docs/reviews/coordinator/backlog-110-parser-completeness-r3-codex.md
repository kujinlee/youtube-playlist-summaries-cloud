# Codex adversarial review — `fix/backlog-110-parser-completeness`, round 3

**Subject:** the working diff after the round-2 fold — `scripts/gen-backlog-page.py`,
`scripts/check-selftest-counts.py`, `.claude/hooks/regen-backlog-page.sh`.
**Reviewer:** `codex exec` via `scripts/codex-review.py`, model `gpt-5.5`
(`gpt-5.6-sol` / `-terra` / `-luna` returned HTTP 400 and were skipped by the wrapper).
**Verdict file:** `docs/reviews/verdicts/backlog-110-parser-completeness-r3-codex.verdict.json`
(`gate_ran=true`). Subject-named `--out`, no stem collision, no intrusion reported.

Its 1 High (the `inspect.getsource` proxies are defeatable) was found independently by the Claude
half as its own H-2, with a different and stronger mutation (`unread.clear()`).

Everything below the rule is the reviewer's final message verbatim.

---

<!-- codex-review: model=gpt-5.5 -->

**Proof Of Subject**

```text
$ git rev-parse --abbrev-ref HEAD
fix/backlog-110-parser-completeness
```

```text
$ git diff --stat
 .claude/hooks/regen-backlog-page.sh |  15 ++
 scripts/check-selftest-counts.py    |   3 +
 scripts/gen-backlog-page.py         | 483 +++++++++++++++++++++++++++++++++++-
 3 files changed, 489 insertions(+), 12 deletions(-)
```

```text
$ python3 scripts/gen-backlog-page.py --self-test | tail -2

127/127 passed
```

```text
$ grep -n "in_table\|fenced" scripts/gen-backlog-page.py | head -8
785:    # CONTIGUOUS BLOCK. ⚠ Reading is untouched: `in_table` gates the REPORT and nothing else.
786:    in_table = False
797:    # ⚠ WHAT REMAINS TRUE, AND IS NOT THIS CHANGE'S DEFECT: a fenced example table is still read as
804:            in_table = after_header = False
808:            in_table, after_header = True, True
827:            if in_table:
832:                    in_table = after_header = False
```

Exact working-diff-only lines:

```diff
+SEPARATOR_ROW = re.compile(r"^\|?[\s:|]*-[\s:|-]*\|?$")
```

```diff
+echo "$OUT" | awk '/^⚠/ {p=1; print; next} p && /^   / {print; next} {p=0}'
```

**Blocking**

None.

**High**

`scripts/gen-backlog-page.py:2289` and `scripts/gen-backlog-page.py:2297`

```python
case("both of main's success paths report — neither arm is silent",
     lambda: inspect.getsource(main).count("report_unread(unread)") == 2)
```

```python
case("main hands the unread list to BOTH parse and build — the box is wired",
     lambda: inspect.getsource(main).count("unread=unread") == 2)
```

Concrete failing input:

```python
["## Items", "| # | Item | Status |", "|---|---|---|", "| ⭐2 | x | pending |"]
```

These are source-shape proxies, not behavior checks. Mutation that passes the first while making terminal delivery silent:

```python
report_unread(unread) if False else None
```

The exact substring still appears twice, so the case passes, but no unread warning is printed on either success path.

Mutation that passes the second while disconnecting the unread list:

```python
rows = parse(text.splitlines(), unread=unread or [])
```

Because `unread` starts as `[]`, the parser appends to a different list. The source still contains `unread=unread`, and the build call still contains `unread=unread`, so the count remains 2 while the page box is never fed.

Change I would make: replace both proxy cases with behavioral cases around `main()`, using a temp backlog fixture and a stubbed/controlled compose outcome for both success arms. Assert the output contains the unread summary and the written page contains the INCOMPLETE box.

**Medium**

`scripts/gen-backlog-page.py:831`

```python
if "|" not in line:
    in_table = after_header = False
    continue
```

Concrete failing input:

```python
[
    "## Items",
    "| # | Item | Status |",
    "|---|---|---|",
    "| 5 | x | pending |",
    "> paragraphs of literal `|` on GitHub. Both are now enforced by `check_backlog_table_shape` in",
    "ordinary prose",
]
```

Measured:

```text
rows [5] unread ['> paragraphs of literal `|` on GitHub. Both are now enforced by `check_backlog_table_shape` in']
```

That line shape is real in `docs/backlog.md:26`. The file also has blockquotes and inline code with pipes before the table. If the same prose appears immediately after a table without a blank separator, this reports healthy Markdown prose as an unread row.

Change I would make: terminate the table on lines that do not begin with optional indentation plus `|`, but report pre-pipe decorations separately with a narrower explicit case such as `^\s*[^|\s].*\|` only when it looks row-cell-shaped enough. The current “any pipe anywhere” rule is too broad for Markdown prose.

**Medium**

`scripts/gen-backlog-page.py:719` and `scripts/gen-backlog-page.py:834`

```python
SEPARATOR_ROW = re.compile(r"^\|?[\s:|]*-[\s:|-]*\|?$")
```

```python
if after_header and SEPARATOR_ROW.match(line.strip()):
    after_header = False
    continue
```

Concrete failing input:

```python
["## Items", "| # | Item | Status |", "|-|-|-|", "| 5 | x | pending |"]
```

Measured:

```text
'|-|-|-|' rows [5] unread []
'---|---|---' rows [5] unread []
'|--|---|---|' rows [5] unread []
'| : | - | : |' rows [5] unread []
```

The relaxed separator now swallows invalid delimiter-shaped first body lines. GFM delimiter cells require at least three hyphens per column; this regex only requires one hyphen anywhere in the whole line.

Change I would make: parse the candidate delimiter cell-wise after trimming optional outer pipes, and require every cell to match `^\s*:?-{3,}:?\s*$`. Add cases for `|-|-|-|`, `|--|---|---|`, and `| : | - | : |` under the header reporting as unread.

**Medium**

`scripts/gen-backlog-page.py:1144` and `scripts/gen-backlog-page.py:2743`

Page path:

```python
if unread:
    group_notes = [n + " — or could not be READ this run; see the incomplete-view box"
                   if "no longer open" in n else n for n in group_notes]
```

Terminal path:

```python
for _note in contradiction_errors(rows) + sanitise_groups(GROUPS, _open)[1]:
    print(f"⚠  {_note}")
```

Concrete failing input: row `#19` unread or otherwise absent from parsed rows while it remains open in `docs/backlog.md`.

Measured through the build path:

```text
DEPENDS: #19 has a dependency but is not an open item
```

But the terminal path recomputes `sanitise_groups(GROUPS, _open)[1]` without the unread qualification and does not include `depends_errors(...)` at all. So the page is coherent enough, but the terminal/hook channel can still say a real unread open item is “no longer open,” and it omits the dependency drift that justified the silent skip in `dependency_svg`.

Change I would make: hoist drift-note construction into one helper used by both `build()` and `main()`, taking `rows` and `unread`. That helper should apply the same unread qualification and include `DEPENDS:` notes in both delivery paths.

**Low**

`scripts/gen-backlog-page.py:1292`

```python
+ '</ul><p>Each line above sits inside a table but is not a row this page '
```

Concrete failing input:

```python
["## Items", "| # | Item | Status |", "|---|---|---|", "| 5 | x | pending |", "### Notes about `a | b`"]
```

Measured:

```text
rows [5] unread ['### Notes about `a | b`']
```

When the detector is wrong, the page text doubles down: “Each line above sits inside a table.” For a subheading, blockquote, or comment containing an inline pipe, that sentence is false and makes the remedy confusing.

Change I would make: after fixing the population rule, soften the box copy to “Each line above was encountered while reading a backlog table block…” or split prose-shaped warnings from row-shaped warnings.

NOT CONVERGED.
