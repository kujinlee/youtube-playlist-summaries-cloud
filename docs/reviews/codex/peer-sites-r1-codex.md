<!-- codex-review: model=gpt-5.5 -->

> **Coordinator note — WHICH TREE THIS SAW.** Codex reviewed `52010914`, the branch's only commit,
> recorded in `docs/reviews/verdicts/peer-sites-r1-codex.verdict.json` as `head`. Its findings were
> fixed *after* this review, so the fixes below are **not** what it read. Stating the reviewed
> commit is mandatory because round 1 of `fix-src-viewer-escaping` filed the opposite as a High:
> a review of the parent filed as a review of the child. Everything after this block is verbatim.

---

**Blocking** — [scripts/peer-sites.py:126](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/peer-sites.py:126)

`_if_chain()` treats `else: if ...` as an `elif`, because the AST shape is the same and the code does not check `col_offset`. That means it invents a single `if/elif chain` across two different syntactic containers.

Measured fixture:

```python
def f(x, y):
    if x:
        return 1
    else:
        if y == 1:
            return 2
        elif y == 2:
            return 3
```

`containers(src)` returns:

```python
[('exits', 'f()', [4, 7, 9]), ('branches', 'if/elif chain', [3, 6, 8])]
```

Line 6 is not an `elif` peer of line 3; it is a nested `if` inside the `else` body. `report(src, {6})` then advises checking the outer `if x:` as a peer of the inner `if y == 1:`. That falsifies “bounded by syntax, so every member is legitimately in scope.”

Falsifier: show that the detector distinguishes `elif y == 1:` from `else:\n    if y == 1:` and reports the latter as two separate branch containers.

Sibling search: I scanned repo Python with an AST check for `If.orelse == [If]` where the child has greater indentation than the parent. I found no current `scripts/*.py` live sibling, so this is a latent detector bug rather than triggered by this branch’s own changed files.

**High** — [scripts/peer-sites.py:91](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/peer-sites.py:91), [scripts/peer-sites.py:194](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/peer-sites.py:194)

The detector only records the head line of a peer (`return`, `if`, `except`) and `report()` only intersects exact line numbers. A diff that changes the value/condition on a continuation line silently misses a partially touched container.

Measured fixture:

```python
def f(x):
    if x == 1:
        return (
            "old"
        )
    if x == 2:
        return (
            "other"
        )
    return "done"
```

`containers(src)` returns exits at `[4, 8, 11]`. `report(src, {4})` flags `1 of 3 exits`, but `report(src, {5})` returns `[]`, even though line 5 is the returned value for the first exit. Same shape for multi-line branch conditions: touching the condition continuation line returns `[]`.

Falsifier: represent each peer as a source range, or otherwise prove that a `git diff -U0` touching any line inside a peer’s syntactic member intersects that member.

Sibling search: I searched for current multi-line `return (` / `if (` / `elif (` / `except (` in repo Python. Current siblings exist at `scripts/brief-compose.py:840`, `scripts/page_chrome.py:120`, and `scripts/page_chrome.py:169` for multi-line returns. I did not find multi-line branch/except heads with that simple search. So the false negative is reachable in this repo today.

**Medium** — [scripts/peer-sites.py:134](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/peer-sites.py:134)

`parse_hunks()` claims “Line numbers the NEW side of a unified diff added or changed,” but it returns the entire new hunk range. That is only accurate because `changed_lines()` happens to call `git diff -U0`. With normal unified context it marks unchanged context lines as touched.

Measured:

```python
parse_hunks("@@ -1,3 +1,3 @@ heading\n context\n-old\n+new\n context\n")
# => {1, 2, 3}
```

Only line 2 changed. It also accepts combined-diff headers:

```python
parse_hunks("@@@ -1,2 -1,2 +1,2 @@@\n- a\n+ b\n")
# => {1, 2}
```

Falsifier: either document and name this as a `-U0` hunk parser, or parse hunk bodies so only new-side added/replaced lines are returned and combined diffs are skipped/refused.

Sibling search: I checked the only production caller; `changed_lines()` uses `git diff -U0`, so the live CLI path is not currently overmarking from context. The bug is in the split-out pure parser’s contract and tests.

**Low** — [scripts/check-fixture-variation.py:542](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-fixture-variation.py:542)

The exemption premise for `changed_lines.ref` and `changed_lines.path` says varying them “would require a real `.git`.” It does not. `changed_lines()` can be tested without git by monkeypatching `subprocess.run`, and both parameters are observable in the argument vector.

Measured with a fake `subprocess.run`:

```python
changed_lines("ref-A", "path/one.py")
changed_lines("ref-B", "path/two.py")
```

captured:

```python
['git', '-C', REPO, 'diff', '-U0', 'ref-A', '--', 'path/one.py']
['git', '-C', REPO, 'diff', '-U0', 'ref-B', '--', 'path/two.py']
```

Falsifier: show that this project’s self-test convention forbids monkeypatching subprocess shells, or replace the exemption with cases that vary the arguments without requiring `.git`.

Sibling search: I searched only the two new `peer-sites.py:changed_lines.*` exemptions. I did not audit all existing exemptions in `check-fixture-variation.py`.

Real-history volume: `python3 scripts/peer-sites.py --diff master` reported zero containers. I also ran it against several recent refs; most were zero. `origin/explainer-src-root-self-configures` produced one finding, and `origin/arm-prod-drift-cron` produced three containers, including one 13-exit function. I did not find runaway volume, but the central “no false positives by construction” claim is still false.

Verification run:
`peer-sites.py --self-test` 32/32, `check-plan-code.py --self-test` 128/128, `check-fixture-variation.py --self-test` 67/67, `check-selftest-counts.py` OK, `check-docs.py` OK, `check-ratchet-contract.py` OK, `gen-dashboard.py --self-test` 325/325. I did not run the 12-minute mutation sweep.

CONVERGED: **No**. The detector’s claimed container semantics have a Blocking counterexample.
