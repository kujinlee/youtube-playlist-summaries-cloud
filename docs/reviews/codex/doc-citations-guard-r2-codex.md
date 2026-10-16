<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED — 1 High, 1 Medium, 1 Low.

**High — The strict-decoding fix introduces a real Git-header fail-open.**

With `core.quotePath=false`, Git can emit quoted paths containing literal UTF-8 alongside escaped control characters. `_header_path()` treats literal `é` as a Latin-1 byte, then rejects it during strict UTF-8 decoding. It returns `None`, disabling inspection of that document.

Reproduction:

```bash
SCRIPT="$PWD/scripts/check-doc-citations.py"
T=$(mktemp -d)
git -C "$T" init -q
git -C "$T" config user.email probe@example.com
git -C "$T" config user.name probe
git -C "$T" config core.quotePath false
mkdir "$T/docs" "$T/lib"
printf 'x\n' > "$T/lib/a.ts"
git -C "$T" add .
git -C "$T" commit -qm base
printf '`lib/a.ts:999`\n' > "$T/docs/"$'é\t.md'
git -C "$T" add .
git -C "$T" diff --unified=0 HEAD
python3 "$SCRIPT" --base HEAD --root "$T"
echo "rc=$?"
```

Relevant output:

```text
+++ "b/docs/é\t.md"
@@ -0,0 +1 @@
+`lib/a.ts:999`

doc citations OK — every `path:line` added under docs/ resolves to a real line
rc=0
```

Restoring the previous replacement decoder produces a finding for the same diff:

```text
docs/�\t.md: `lib/a.ts:999` is outside the file (1 lines)
```

Thus this round changed an incorrectly displayed finding into a silent pass.

**Fix:** decode Git’s quoting at the byte level while preserving literal UTF-8, then decode the resulting bytes consistently with filesystem paths. Add a subprocess regression using this actual Git output. An undecodable scoped header should produce CANNOT RUN rather than silently disable inspection.

**Medium — The new read-error handler has no self-test witness; returning success survives.**

The handler behaves correctly when driven with `PermissionError`, but none of the 40 cases exercises it. The existing CANNOT RUN case exercises the separate Git-error handler.

Executed in memory, replacing only the new handler’s `return 2` with `return 0`, then running `self_test()` and driving `main()` with a reader that raises `PermissionError`:

```python
def read(path):
    raise PermissionError("fixture is unreadable")

main(
    [],
    fetch_diff=lambda *_: "+++ b/docs/x.md\n+`lib/a.ts:1`",
    fetch_tracked=lambda *_: ("lib/a.ts",),
    make_reader=lambda *_: read,
)
```

Output:

```text
40/40 passed
shipped rc=2 CANNOT RUN — a cited file could not be read: fixture is unreadable
mutant rc=0 CANNOT RUN — a cited file could not be read: fixture is unreadable
```

This is a coverage hole in this round’s fix, although it does not invalidate the seven existing manifest kills.

**Fix:** add an injected reader-error case asserting rc=2 and a mutation targeting this handler specifically.

**Low — The numerical repair leaves contradictory figures in the delivery documents and CI.**

Executed:

```bash
sed -n '561,564p' .github/workflows/ci.yml
sed -n '77p' docs/backlog.md
sed -n '15107,15115p' docs/dashboard-entries.md
```

The output still claims:

```text
ci.yml: living corpus fires 175 times on 838 ... (20.9%)
ci.yml: ADDED lines fire 6 times over 40 commits (0.15/commit)
backlog row 49: ships with 30 cases
dashboard: 30 cases, 7 mutations
dashboard: Final: ... 111/895 ...
```

The script runs **40 cases**. Its current approximate corpus figures reproduce, but the CI figures describe the superseded rule, and the dashboard retains an exact “Final” count alongside the approximation rationale.

**Fix:** update the case counts, remove superseded CI calibration figures, and apply the approximation wording consistently.

The remaining requested checks held:

- `python3 scripts/check-doc-citations.py --base origin/master` passes, rc=0.
- Self-tests report **40/40**. All seven manifest mutations are killed and attributed. Mutation 1 fails eleven cases; mutations 2–7 each fail exactly their named case.
- Restoring the `---` reset fails **exactly** the new horizontal-rule regression case.
- Making headers retain the first established scope fails **both** directional header cases, as expected for that mutation. I could not find a third ambient case among the new cases.
- Importing the shipped functions yields **26,356/27,251** review citations and **111/895** living-corpus findings, consistent with the approximate claims.
- Sweeping `git rev-list -n 40 origin/master`, resolving each commit’s added citations against today’s tree, yields **exactly 10 findings, 0.25/commit**.
- I could not establish a cross-file scope leak from deleting the `---` clause in the production `git diff --unified=0 <base>` path. Combined diffs use different boundary markers, but that command does not request combined output. Renames, mode-only changes, and binary sections did not establish another finding.
- I found no incorrect exception classification in the new OSError handler itself; the defect there is the missing regression witness.
