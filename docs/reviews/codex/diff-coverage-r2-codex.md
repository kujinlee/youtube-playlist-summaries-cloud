<!-- codex-review: model=gpt-6.1-sol -->

1. **[P2] Whole-line insertions falsely cover unchanged decision lines** — `scripts/check-diff-coverage.py:162`. For insertion opcodes, coverage is assigned to an adjacent source line even when that line remains identical. Executed fixture: add `if bad:` above an existing `pass`; manifest edit finds `"if bad:\n"` and replaces it with `"audit = 1\nif bad:\n"`. The mutation preserves the decision verbatim, yet the checker exits **0**, reports **zero warnings**, and claims “every one is edited by a mutation.” Inserting a body statement after an unchanged `if` also falsely covers its header. Distinguish insertion at a line boundary from insertion within a source line.

2. **[P2] Binary diffs silently disappear** — `scripts/check-diff-coverage.py:79–100`. Adding a NUL byte to a manifested Python file makes Git emit `Binary files … differ`, without textual hunks. The parser drops the file before UTF-8 or syntax validation. Executed CLI result: **exit 0, zero manifested scripts changed, “every one is edited by a mutation.”** Identify binary changes and report NOT CHECKED.

3. **[P2] Deleting a script together with its manifest hides its deleted decisions** — `scripts/check-diff-coverage.py:214–221`. Membership comes exclusively from HEAD’s manifests. Executed fixture: delete a previously manifested script containing `if good:` and its manifest, while retaining another valid manifest. Result: **exit 0, zero warnings, “every one is edited by a mutation.”** Retaining the deleted script’s manifest instead produces CANNOT RUN because its target is absent. Consult merge-base manifests when identifying deleted scripts.

4. **[P3] Non-UTF-8 Git output still crashes** — `scripts/check-diff-coverage.py:196–202`. The file-read handler cannot catch decoding failures inside `subprocess.run(text=True)`. Executed fixture: base contains a Latin-1 comment byte `0xe9`; HEAD replaces it with valid UTF-8 source. Git’s diff includes the old byte. The CLI exits **1 with a UnicodeDecodeError traceback**, before checking the file. Handle decoding failures for Git output, including base-side reads.

5. **[P3] Unparseable base source becomes a clean zero** — `scripts/check-diff-coverage.py:187`. `decision_lines(old_source) or set()` collapses parse failure into “no decisions.” Executed fixture: remove base source containing `if good:` plus an unrelated syntax error, replacing it with `PIN = 1`. Result: **exit 0, zero warnings, “every one is edited by a mutation,”** without NOT CHECKED. Preserve and report the base-side parse failure.

6. **[P3] C-quoted Unicode paths can crash** — `scripts/check-diff-coverage.py:75`. Executed real-Git fixture named `scripts/한<TAB>x.py`, changing `if good:` to `if bad:`. With the checker’s `core.quotepath=off`, Git retains literal Unicode inside the quoted path. The Latin-1 round trip raises **UnicodeEncodeError**; CLI exits **1 with a traceback**. Decode Git’s escapes without forcing literal Unicode through Latin-1.

Validation, entirely under `/tmp/diff-review.Z2FDYL`:

- **39/39 self-tests passed; 20/20 mutations applied uniquely and failed their named cases.**
- **211/211 merge-ready self-tests passed.** The five PR-only steps are correctly accounted for; diff coverage follows `check-review-recorded`.
- Round 1 probes now behave correctly: trailing-newline anchor; real `return env` → `return {}`; multiline return/assert/except/exit; `if (` → `while (`; spaced and tabbed filenames; missing Git.
- Rename-with-edit reads deleted lines from the old path. Divergent-base history uses the merge-base correctly. Explicit `\ No newline at end of file` markers behave correctly.
- Re-measured against `origin/master` at `4aaa6ed7`: **57** at `16bed21b`, **32** at `b6e46a3a`. The latter includes `check-hook-commands.py:80`. Those quoted counts in the PR body, backlog #251, and dashboard reproduce; their broader completeness and failure-handling claims are refuted above.

The repository remained unchanged.

VERDICT: NOT CONVERGED
