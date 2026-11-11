<!-- codex-review: model=gpt-6.1-sol -->

- **High — `scripts/check-reference-namespace.py:246`: deleted content can impersonate a source header and exempt new prose. Fix-induced: false; the r1 bypass survives through a different parsing mechanism.** Reproduced with real Git:
  
  Base `docs/backlog.old.md` contains:
  ```text
  -- a/docs/backlog.md
  | 31 | **Gate** see #17 and #18 | x | S | (tooling) | open |
  ```
  Delete that file and append this previously absent row to `docs/backlog.md`:
  ```text
  | 31 | **Gate** see #17 and #18 ⟦kind: task⟧ | x | S | (tooling) | open |
  ```
  Git renders the first deleted content line as `--- a/docs/backlog.md`. `removed_lines()` treats it as a header and credits the following deleted row to the backlog. Result: **zero violations**; removing the marker produces **two violations**. New prose from an out-of-scope deleted file therefore passes the narrowed exemption.

  **Fix:** distinguish file headers from hunk content using diff state and hunk counts; apply that distinction to both source and destination parsing. Add this real-Git regression case.

- **Low — `docs/backlog.md:51`: row #22 is marked `task` despite explicitly documenting a false claim and a live defect. Fix-induced: false.** Concrete input: the current row says a re-address falsifies the artifact-identity assumption, describes stale bytes under new metadata, and ends with “a live wrong result today” pinned by a failing tripwire. Under ruling 3, this is `defect`, regardless of whether the eventual repair needs design work.

  **Fix:** change its marker to `⟦kind: defect · part of: backlog #17⟧`.

- **Low — `docs/backlog.md:40`: row #2 remains `story` although its remaining work requires a product decision. Fix-induced: false.** Concrete input: “Decide: keep PDF, or make the HTML printable” and “Needs a product decision before it's actionable”; its status confirms that decision remains open. Ruling 1 requires a task plus NEEDS-OWNER.

  **Fix:** use `⟦kind: task⟧` and explicitly mark the outstanding decision NEEDS-OWNER.

- **Low — `scripts/check-reference-namespace.py:460`: the same-file case passes for an ambient reason, leaving a rename mutant alive. Fix-induced: false.** Its fixtures always have identical source and destination paths. Insert this branch before the `/dev/null` branch:
  ```python
  elif line.startswith("+++ b/") and src and src != line[6:]:
      src = line[6:]
  ```
  **All 33 self-tests still pass.** In a real-Git rename from `docs/backlog.old.md` to `docs/backlog.md`, with sufficient unchanged content to retain rename detection and the row above changed only by adding its marker, shipped code reports **two violations**; the mutant reports **zero**.

  **Fix:** add a rename fixture whose source and destination differ, assert that moved prose is judged, and register this mutant.

Merge verification passed: after stripping **every marker**, including the Status-cell example, and excluding rows #394 and #395, `docs/backlog.md` equals `origin/master` **byte-for-byte**. No other row or surrounding text changed. Mutation manifests sum to **2559**. No contradiction found among the newly merged rows #398–#407.

All five requested commands ran successfully:

| Command | Result |
|---|---|
| `gen-backlog-page.py --self-test` | 202/202 |
| `check-features.py --self-test` | 54/54 |
| `check-reference-namespace.py --self-test` | 33/33 |
| `check-features.py` | Passed |
| `check-plan-code.py --mutate . --only scripts/check-reference-namespace.py` | 16/16 killed and attributed; diagnostic slice |

The additional rename mutant survives despite that green manifest slice. No repository files written; no `.claude/plans/` files read or quoted.

**NOT CONVERGED**
