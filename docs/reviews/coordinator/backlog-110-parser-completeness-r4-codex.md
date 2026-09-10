# Codex adversarial review — `fix/backlog-110-parser-completeness`, round 4

**Subject:** the working diff after the round-3 fold — `scripts/gen-backlog-page.py`,
`scripts/check-selftest-counts.py`, `.claude/hooks/regen-backlog-page.sh`.
**Reviewer:** `codex exec` via `scripts/codex-review.py`, model `gpt-5.5`
(`gpt-5.6-sol` / `-terra` / `-luna` returned HTTP 400 and were skipped by the wrapper).
**Verdict file:** `docs/reviews/verdicts/backlog-110-parser-completeness-r4-codex.verdict.json`
(`gate_ran=true`). Subject-named `--out`; no stem collision; no intrusion reported.

**Verdict: CONVERGED** — 0 Blocking, 0 High, 0 Medium, 2 Low. It re-measured the read/report
symmetry across all six contexts and confirmed it holds, and confirmed the delivery regressions
r2 and r3 found are now killed. The Claude half of the same round returned NOT CONVERGED with
0 Blocking / 3 High / 4 Medium / 8 Low, all of them coverage rather than behaviour — its own
summary: *"none of them changes what this branch does; all of them change what a future edit can
quietly undo."* Both halves' findings were folded before merge.

Both of its Lows were taken:
* `row_ish` now measures the ORIGINAL line's first-pipe index rather than the stripped line's, so a
  four-space indented pipe line (a Markdown code block) is no longer reported;
* the end-to-end case's comment now says exactly what is and is not written outside the temp dir.

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
 .claude/hooks/regen-backlog-page.sh |  21 +
 scripts/check-selftest-counts.py    |   3 +
 scripts/gen-backlog-page.py         | 757 ++++++++++++++++++++++++++++++++++--
 3 files changed, 746 insertions(+), 35 deletions(-)
```

```text
$ python3 scripts/gen-backlog-page.py --self-test | tail -2

152/152 passed
```

```text
$ grep -n "def row_ish\|def is_delimiter\|def report_run\|def drift_notes_for" scripts/gen-backlog-page.py
717:def is_delimiter(line: str) -> bool:
740:def row_ish(line: str) -> bool:
757:def report_run(rows: list[dict], unread: Sequence[str]) -> None:
1078:def drift_notes_for(rows: list[dict], unread: Sequence[str] = ()) -> list[str]:
```

Exact working-diff-only lines:

```diff
+DELIMITER_CELL = re.compile(r"^:?-+:?$")
+def report_run(rows: list[dict], unread: Sequence[str]) -> None:
+        report_run(rows, unread)
```

**Blocking**

None.

**High**

None.

**Medium**

None.

**Low**

[ scripts/gen-backlog-page.py:753 ](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:753)

```python
head, sep, _ = line.strip().partition("|")
return bool(sep) and len(head) <= 3
```

Concrete failing input:

```python
[
    "## Items",
    "| # | Item | Status |",
    "|---|---|---|",
    "| 5 | x | pending |",
    "    | not | a backlog row |",
]
```

Measured:

```text
row_ish: True
first_pipe_index: 4
rows: [5]
unread: ['    | not | a backlog row |']
```

This contradicts the stated filter: “first pipe is within three characters of the start.” The implementation strips leading whitespace first, so a four-space indented Markdown/code-looking line is reported. Current real `docs/backlog.md` has no such false positive; all real pipe-leading backlog table lines are accepted correctly. I would change this to measure the original line’s first pipe position, e.g. `i = line.find("|"); return 0 <= i <= 3`, keeping the existing three-character boundary case.

[ scripts/gen-backlog-page.py:2933 ](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-backlog-page.py:2933)

```python
with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp:
```

Concrete failing input: the in-suite `main()` run with a doctored real backlog row, as described by the test.

Measured:

```text
out_under_tmp True
named_temp_paths ['/var/folders/.../T/tmp0bpops_l.html']
all_named_temp_under_tmp False
exists_after [False]
stdout_has_unread True
```

No module global leaked: `BACKLOG`, `attach_history`, and `sys.argv` are restored in `finally`. But the test’s claim that temp work stays in the temp dir is false for the intermediate fragment. It is deleted, so this is not a correctness blocker. I would pass `dir=args.out.parent` to `NamedTemporaryFile`, or have the end-to-end test explicitly assert and control the fragment temp location.

**Checks**

Read/report symmetry held in measured contexts: under delimiter, after prose, after subheading, after HTML comment, after pipe prose, and after a second table, a plain `| 111 | ... |` rendered exactly where `| ⭐111 | ... |` reported. In a new section or before any header, the plain row raises and the decorated row is silent, matching the stated gap.

Targeted mutation sweep: old delivery regressions are now killed (`unread.clear()`, disabling either success arm’s `report_run`, splitting parse/build unread, ignoring unread in `drift_notes_for`). Apparent survivors were semantically neutral or hit a test helper rather than production.

CONVERGED.
