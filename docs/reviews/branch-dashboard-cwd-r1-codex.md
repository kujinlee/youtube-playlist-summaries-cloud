# Branch review — dashboard cwd-independence (PR #177), round 1, Codex half

**Subject:** `969ad71` on `fix/dashboard-cwd-independence`.
**Claude half:** [`branch-dashboard-cwd-r1-claude.md`](branch-dashboard-cwd-r1-claude.md).

**Gate provenance.** `scripts/codex-review.py`, `WRAPPER_RC=0`. `gpt-5.6-sol`, `-terra` and `-luna`
each returned HTTP 400; the wrapper fell through to **`gpt-5.5`** unaided. `--out` pointed OUTSIDE
the repository and the file was promoted here only after the wrapper reported success — backlog
#68's mitigation. `docs/reviews/` was verified untouched by checksum during the run.

Everything below the rule is the reviewer's verbatim final message.

---

<!-- codex-review: model=gpt-5.5 -->

**Verdict: NOT CONVERGED**

**Findings**

**High — explicit relative `--store` is still cwd-dependent**  
[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:1210)

Quoted code:

```python
store, store_error, entries = pathlib.Path(a.store), None, []
...
if a.store != ap.get_default("store"):
    store_error = f"no such file: {store}"
```

Concrete scenario, REPRODUCED in memory: from `/tmp`, call the fixed script with:

```bash
python /repo/scripts/gen-dashboard.py --store docs/dashboard-entries.md --fragment-only ...
```

The repo’s real store exists, but `pathlib.Path(a.store)` resolves `docs/dashboard-entries.md` against `/tmp`, not `ROOT`. Result: no real entries are rendered, and the page says it could not read `docs/dashboard-entries.md`.

This fixes the omitted default case, but not the explicit “same as default” CLI case. If the PR claim is cwd-independence of dashboard generation, this is incomplete.

**Low — default empty-state now leaks the absolute repo path**  
[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:421)

Quoted code:

```python
entries_html = (f'<p class="none">No entries yet. They live in '
                f'<code>{_html.escape(str(store))}</code>.</p>')
```

Concrete scenario, REPRODUCED by calling `build()` directly with `store=STORE_DEFAULT` and no entries: the fragment contains:

```html
/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dashboard-entries.md
```

That is a user/home path in a generated page. It only appears in the empty-store state, so current repo content masks it, but the changed default makes this the normal empty-state rendering.

**Medium — the new decoy test can pass when `main()` never writes the fragment**  
[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:1094)

Quoted code:

```python
_with_run(lambda *a, **k: _R(0, "", ""),
          lambda: main(["--fragment-only", str(_frag), "--window", "14"]))
_txt = _frag.read_text(encoding="utf-8") if _frag.is_file() else ""
case("the DEFAULT store resolves against the REPO, not the caller's cwd",
     "DECOYENTRYTEXT" in _txt, False)
```

Concrete scenario, REPRODUCED by in-memory mutation: replace the fragment write branch with an early `return 1` before writing. `_frag` does not exist, `_txt` becomes `""`, `"DECOYENTRYTEXT" not in _txt` is true, and `_self_test()` still reports `117/117 passed`.

The decoy assertion does catch the intended one-line regression:

```python
STORE_DEFAULT = "docs/dashboard-entries.md"
```

But it does not prove `main()` succeeded or produced a fragment, so it can pass for the wrong reason.

**Checks Performed**

`python3 scripts/gen-dashboard.py --self-test`: `117/117 passed`.

`python3 scripts/check-plan-code.py --mutate .`: `OK — delivered scripts mutated: 2 file(s), 44 mutation(s), 0 survivor(s)`.

Reproduced original vs fixed behavior from foreign cwd in memory: `master` rendered git cwd failure plus green “No entries yet”; `HEAD` read the real repo store and avoided the git cwd failure.

No fourth unanchored subprocess found in production paths: `commit_dates`, `_gh_json`, and brief-compose all now pass `cwd=ROOT`. `_gate_module()` is `__file__`-anchored.

The local `_ctx`/`_io`/`_os` imports are safe: they occur before first use in that block, and the later repeated `_ctx`/`_io` import uses the same local names.

The `os.chdir()` restore is in a `finally`, so ordinary exceptions from `main()` restore cwd. Later cases would not reliably detect every possible leak, but I do not see an actual restore bug.
