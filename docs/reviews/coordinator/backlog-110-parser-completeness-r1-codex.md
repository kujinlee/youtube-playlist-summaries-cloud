# Codex adversarial review — `fix/backlog-110-parser-completeness`, round 1

**Subject:** the working diff of `scripts/gen-backlog-page.py` on branch
`fix/backlog-110-parser-completeness` (150 insertions, 4 deletions), fixing backlog #110.
**Reviewer:** `codex exec` via `scripts/codex-review.py`, model `gpt-5.5`
(`gpt-5.6-sol` / `-terra` / `-luna` all returned HTTP 400 and were skipped by the wrapper).
**Verdict file:** `docs/reviews/verdicts/backlog-110-parser-completeness-r1-codex.verdict.json`
(`gate_ran=true`, `intrusions: []`).

> ⚠ **The wrapper was invoked with `--out codex-r1.md`, and that generic stem OVERWROTE the
> committed verdict of an unrelated earlier review** (`docs/reviews/verdicts/codex-r1.verdict.json`,
> a `spec-mutation-drift-report-contract-r1` run). This is the known *"a guard's evidence path has
> no allocator"* hazard, hit again. The committed file was restored from `HEAD` and this run's
> verdict refiled under the stem above. **Round 2 must pass a `--out` named after the subject.**

Everything below the rule is the reviewer's final message verbatim.

---

<!-- codex-review: model=gpt-5.5 -->

```
$ git rev-parse --abbrev-ref HEAD
fix/backlog-110-parser-completeness
```

```
$ git diff --stat
 scripts/gen-backlog-page.py | 154 ++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 150 insertions(+), 4 deletions(-)
```

```
$ git diff | head -40
diff --git a/scripts/gen-backlog-page.py b/scripts/gen-backlog-page.py
index a05cef34..c096e8f2 100644
--- a/scripts/gen-backlog-page.py
+++ b/scripts/gen-backlog-page.py
@@ -679,7 +679,52 @@ class ShapeError(Exception):
     cell is how a closed marker written for something else once closed two open items."""
 
 
-def parse(lines: Sequence[str]) -> list[dict]:
+SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+\|$")
+
+
+def table_ish(line: str) -> bool:
+    """Would a READER call this line a row of the table it sits in? One cell boundary is enough,
+    and the `|---|---|` rule under a header is not a row.
+
+    ⚠ INDENTATION IS STRIPPED FIRST, and that is the point rather than tidiness — one leading
+    space is one of the three decorations that hid a row from `parse` entirely (backlog #110).
+    Measured on the real `docs/backlog.md`: 114 lines begin with a pipe, of which 2 are separators
+    and 2 are headers, leaving 110 — exactly the number `parse` reads. So on the corpus that
+    matters this predicate has no false positives at all, which is what makes reporting on it
+    honest rather than noise."""
+    s = line.strip()
+    return s.startswith("|") and s.count("|") >= 2 and not SEPARATOR_ROW.match(s)
+
+
+def unread_note(unread: Sequence[str]) -> list[str]:
+    """Display lines for rows the parser could not read — EMPTY when there were none.
+
+    ⚠ It QUOTES each line rather than counting them. A bare count tells a reader that something is
+    missing from the page and gives them no way to find it; this file has already paid for an
+    unactionable warning once (r2 finding R2-9, three runs before anyone learned why the Ask tray
+    had gone). One implementation, two call sites — the terminal ⚠ channel and the on-page drift
+    box — because a second copy of a message is a copy that drifts."""
+    if not unread:
+        return []
+    return [f"UNREAD: {len(unread)} line(s) in docs/backlog.md look like table rows and were not "
+            f"read, so they are on no count and no card on this page"] + \
+           [f"UNREAD: {ln.strip()[:110]}" for ln in unread] + \
+           ["UNREAD: the number cell must be a bare integer — no ⭐, no #, no leading space"]
```

**Medium** — `scripts/gen-backlog-page.py:682`

Concrete failing input:

```python
[
    "| # | Item | Status |",
    "|---|---|---|",
    "| - | - | - |",
]
```

Reproduced output:

```text
'| - | - | - |' separator= True table_ish= False
rows= []
unread= []
```

Code:

```python
SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+\|$")
```

and:

```python
return s.startswith("|") and s.count("|") >= 2 and not SEPARATOR_ROW.match(s)
```

This classifies any all-space/colon/hyphen body row as a separator, not just the Markdown divider row under a header. A reader would call `| - | - | - |` a table row; `parse()` drops it, and `table_ish()` suppresses the unread report. I would replace the regex with a cell-wise Markdown separator recognizer: split cells and require each cell to be optional whitespace plus optional leading colon, at least three hyphens, optional trailing colon, optional whitespace.

**Medium** — `scripts/gen-backlog-page.py:747`

Concrete failing input:

```python
[
    "## Items",
    "",
    "| # | Item | Status |",
    "|---|------|--------|",
    "| 1 | 🟢 **Ok** | pending |",
    "",
    "This is a normal note table in the same section, not a backlog item table.",
    "",
    "| Key | Meaning | Status |",
    "|---|---------|--------|",
    "| A | Bundle A | active |",
]
```

Reproduced output:

```text
rows= [(1, 'Ok')]
unread= ['| Key | Meaning | Status |', '| A | Bundle A | active |']
```

Code:

```python
if unread is not None and header and table_ish(line):
    unread.append(line)
```

`header` stays live until the next `##`, not until the contiguous Markdown table ends. That makes a healthy later table in the same section warn as if it were missing backlog cards. I would track the active table block explicitly and clear it on the first non-pipe line after a header/table has started, or otherwise bound `unread` to the contiguous table following the `| # | ... |` header.

Checks run:

```text
python3 scripts/gen-backlog-page.py --self-test
99/99 passed

python3 scripts/gen-backlog-page.py
rc=0
wrote /Users/kujinlee/explainers/backlog-table.html  (110 rows, 69 open, Ask tray lifted)
```

Verdict: NOT CONVERGED.
