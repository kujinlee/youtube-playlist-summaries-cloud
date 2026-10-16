<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED — 1 High, 3 Medium. No Blocking finding.

**High — Added content beginning `++` silently bypasses citation checking.**

At `scripts/check-doc-citations.py:189`, every diff line beginning `+++` is discarded as a header. An actual added Markdown line beginning `++` has exactly that prefix.

Reproduction in a scratch repository with a committed, one-line `lib/a.ts`:

```bash
printf '++ `lib/a.ts:999`\n' > docs/x.md
git add docs/x.md
git diff --unified=0 HEAD
python3 "$SCRIPT" --base HEAD --root "$PWD"
```

Observed:

```text
@@ -0,0 +1 @@
+++ `lib/a.ts:999`

doc citations OK — every `path:line` added under docs/ resolves to a real line
rc=0
```

The existing “a +++ header inside the body” case endorses this overbroad exclusion.

**Fix:** identify content by unified-diff hunk structure. Skip headers outside hunks; examine every added line inside them. Add this real-git regression.

**Medium — Per-file diffing turns a pure rename into newly added citations.**

The pathspec for the destination excludes the source, preventing Git from recognizing the rename. Historical citations then become additions, contradicting the added-lines-only contract.

Using a committed `docs/i.md` containing an already-invalid citation:

```bash
git mv docs/i.md docs/new.md
python3 "$SCRIPT" --base HEAD --root "$PWD"
```

Observed:

```text
⛔ 1 drifted citation(s) added:
  docs/new.md: `lib/a.ts:777` is outside the file (1 lines)
rc=1
```

No citation was added. Thus Claude’s clean-rename result does not establish that renames preserve the ratchet.

**Fix:** obtain rename information from Git and preserve both source and destination when generating the corresponding diff. Test a pure rename containing a historical violation, plus a rename that actually adds one.

**Medium — `_nul_witness()` inherits Git configuration and crashes on an ordinary signing requirement.**

The new helper ignores every setup command’s return code. A failed signed commit leaves no `HEAD`; the eventual traceback misleadingly points at file listing.

Command:

```bash
GIT_CONFIG_COUNT=2 \
GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=true \
GIT_CONFIG_KEY_1=gpg.program GIT_CONFIG_VALUE_1=/nonexistent/gpg \
python3 scripts/check-doc-citations.py --self-test
```

Observed:

```text
RuntimeError: git diff --name-only HEAD failed:
fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree.
rc=1
```

Hooks, templates and repository-routing `GIT_*` variables are also inherited; this is not an isolated fixture.

**Fix:** sanitize repository-routing environment variables, isolate configuration/templates/hooks, disable signing explicitly, and check setup return codes. Report fixture setup failure distinctly from a failed assertion.

With Git absent, self-test similarly raises `FileNotFoundError`, rc=1. Failing is the correct direction; an uncaught traceback is poor diagnostics. The temporary-directory context cleans up on exceptions, and subprocesses are synchronous; I found no directory or process leak.

**Medium — The literal-pathspec fix has no regression witness, although an isolating witness is straightforward.**

Removing only `--literal-pathspecs` from `file_diff`, then invoking `self_test()`, produces:

```text
37/37 passed
```

I constructed a scratch repo with changed `docs/[id].md` and `docs/i.md`, each containing one bad citation, and evaluated:

```python
violations(
    "docs/[id].md",
    file_diff("HEAD", root, "docs/[id].md"),
    tracked_files(root),
    _reader(root),
)
```

Observed:

```text
literal flag present: 1 finding
literal flag absent:  2 findings
```

This can be a separate, precisely named case asserting the complete result. Dropping the flag would fail that case alone. Contrary to the commit’s explanation, `_nul_witness()` never calls `file_diff`, so it cannot catch that mutation.

**Fix:** ship this case and the corresponding mutation.

The remaining checks:

- The branch gate passes: `python3 scripts/check-doc-citations.py --base origin/master`, rc=0.
- Control: **37/37**. All **10 mutations are killed and attributed**. Mutation 1 fails six cases; mutations 2–10 each fail exactly one. Both CANNOT RUN mutations isolate.
- I could not establish a fifth ambient case under the previous rounds’ definition. The missing literal-pathspec witness is a separate coverage hole.
- Omitting `--literal-pathspecs` from `changed_files` is harmless: that invocation supplies no filename pathspec. `tracked_files` likewise supplies none.
- Newline/tab/Unicode document names produced correctly attributed findings under both `core.quotePath` settings. Empty diffs and deletions returned rc=0. I found no hidden I/O in `violations()` beyond its injected reader.
- Re-derived through `changed_files(empty_tree)` → `file_diff` → `violations`: reviews **26,334/27,229 = 96.7%**; living corpus **111/895 = 12.4%**. The review total differs from counting complete file text because the shipped parser skips some `+++` lines.
- Sweeping the 40 commits with per-commit file lists and per-file diffs, resolving against today’s tree, reproduces **10/40 = 0.25**.
- The three documents’ approximate calibration figures agree with those measurements. The previous Low remains unresolved: the dashboard still says **30 cases, 7 mutations**, while the shipped counts are **37 and 10**.
