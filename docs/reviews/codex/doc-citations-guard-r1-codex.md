<!-- codex-review: model=gpt-6.1-sol -->

NOT CONVERGED — 1 High, 3 Medium, 1 Low.

**High — Git-quoted document names bypass the guard entirely.**  
At [check-doc-citations.py:160](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-doc-citations.py:160), only `+++ b/` establishes the document being examined. Git’s default quoting produces a different header for Unicode filenames.

Executed in a temporary repository containing a one-line `lib/a.ts`, after adding `` `lib/a.ts:999` `` to `docs/한글.md`:

```text
git diff --unified=0 HEAD
+++ "b/docs/\355\225\234\352\270\200.md"
@@ -1,0 +2 @@
+`lib/a.ts:999`

python3 scripts/check-doc-citations.py --base HEAD --root <temporary-repository>
doc citations OK — every `path:line` added under docs/ resolves to a real line
rc=0
```

This is an actual fail-open path, independent of citation grammar. Depending on preceding diff sections, `current` can also retain another document’s scope.

Fix: decode Git’s quoted paths, reset document state at file boundaries, and use NUL-delimited tracked filenames. Add a subprocess test using a Unicode document name.

**Medium — The citation grammar silently excludes valid paths beyond the two admitted blind spots.**  
The extension whitelist and path character class omit ordinary source files and Next.js route groups.

Executed against the imported module:

```python
for text in [
    "lib/a.css:999",
    "app/(auth)/page.tsx:999",
]:
    print(text, g.CITE.findall(text))
```

Output:

```text
lib/a.css:999 []
app/(auth)/page.tsx:999 []
```

An actual invocation over an added `lib/a.css:999` citation also returned:

```text
doc citations OK — every `path:line` added under docs/ resolves to a real line
rc=0
```

Neither failure is a range or fence limitation. The guard’s success message therefore overstates coverage.

Fix: support the repository’s filename grammar and relevant extensions, with failing fixtures for each supported form. Explicitly document any remaining excluded forms.

**Medium — The nine historical firings measure later drift, not nine PR-time defects.**  
The claimed count reproduces when historical diffs resolve against today’s working tree. But some cited lines contained content when those commits introduced them.

Executed:

```sh
git show 5128b99b:scripts/check-ci-watched.py | sed -n '860p'
git show 5128b99b:docs/portable-practices.md | sed -n '643p'
git show 71a32378:scripts/check-ci-watched.py | sed -n '183p'
```

Output:

```text
def main(argv: "list[str] | None" = None, stream=None) -> int:
**Re-enumerated 2026-08-13** (counted, not recalled): **61 memory files**, **633 review documents**,
        log_line("unwatched", "d", "T", "s\tinjected")   -> SIX columns, not four
```

These citations appear among the nine “blank line” firings against today’s tree. The shipped predicate would accept these populated lines at those historical revisions. Thus `0.23/commit` is not established as the gate’s historical firing rate.

Fix: calibrate each commit against its own tree, explicitly account for unavailable untracked files, and distinguish subsequent drift from defects detectable when added. This is separate from the previously fixed prototype-regex measurement error.

**Medium — Two advertised cases pass after their supposed behavior is removed.**  
The Markdown-target case checks only that a valid citation produces no finding; ignoring Markdown citations entirely produces the same result. The header case contains no citation that could trigger a finding.

Executed in-memory source mutations, followed by `self_test()`:

```text
replace "|json|md" with "|json":
rc=0 output=32/32 passed

remove ' or line.startswith("+++")':
rc=0 output=32/32 passed
```

The first mutation removes all `.md` target coverage without any test noticing. The second demonstrates that the named header case does not witness the exclusion it claims.

Fix: pair the valid Markdown target with an invalid Markdown target. Give the header test citation-shaped content that would fire if examined as an added line.

**Low — URL text is misidentified as a repository citation.**  
The regex lacks boundaries distinguishing local paths from URLs.

Executed:

```python
g.violations(
    "+++ b/docs/x.md\n+http://localhost:3000/lib/a.ts:2",
    (),
    lambda p: None,
)
```

Output:

```text
['docs/x.md: `3000/lib/a.ts:2` does not resolve — no such file, and no tracked file ends with it']
```

A URL becomes a nonexistent repository path beginning with its port.

Fix: distinguish URL tokens before extracting local citations, and add URL/port negative controls.

The other checks held: **32,004/32,901 = 97.3%** and **110/897 = 12.3%** reproduce. All seven mutations were killed, with each named case among the failures; mutations 2–7 failed only their named case, while mutation 1 failed nine cases. I could not break the tested unique/ambiguous suffix behavior. CI invokes the guard on master-targeting PRs without suppressing failure, so a nonzero exit fails `verify`; server-side branch protection was not verified.
