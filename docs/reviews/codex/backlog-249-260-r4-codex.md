<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — Malformed-cache refusal bypasses the caller’s CANNOT RUN contract.**  
`scripts/codex-frontier-model.py`, `resolve_candidates()`:

```python
sys.exit(f"error: {CACHE} parsed but its `models` is "
         ...
         f"⛔ TREAT THIS AS THE GATE NOT HAVING RUN.")
```

Input `{"models":"oops"}` raises `SystemExit` with a string, which exits **1**, not **2**. At the actual caller:

```python
models = [args.model] if args.model else resolve_candidates()
```

the exception escapes before `emit()`. The refusal text reaches stderr, but the caller neither translates the outcome nor records `gate_ran=False`.

**Ran:** Python 3.12 invocation of `codex-review.main()` with the actual resolver, mocked cache input, and mocked filesystem/service boundaries. Result: string-valued `SystemExit` → exit **1**; `write_verdict` called **0** times; `run_codex` called **0** times. The new refusal still represents an unrun gate as a violation and leaves no testimony.

## Medium

**M1 — New sentence boundaries split valid inline code spans, making wrapping change the verdict.**  
`scripts/check-withdrawal.py`, `SENTENCE_SPLIT`:

```python
r"|(?<=:)\n"
r"|(?<=\s\s)\n"
r"|\n(?=\s*(?:[|#>]|[*+-]\s|\d+[.)]\s))"
```

These alternatives also match *inside* multiline inline code. For example:

```text
the count was `anchors:
1,414` today
```

is historical prose containing one code span. The colon boundary separates `was` from the figure and reports a survivor. The equivalent unwrapped text is suppressed.

**Ran:** `main(["--strict", "--base", base], root=temp_repo)` over real two-commit repositories, correcting `1,414` to `1,416` in `docs/src.md` while retaining the historical copy in `docs/live.md`.

- Unwrapped inline span: **rc=0**, suppressed by `was`.
- Colon-wrapped inline span: **rc=1**, `SURVIVOR docs/live.md:2`.
- Inline span containing two tabs before the newline: **rc=1**, same false survivor.

Also executed the pre-fold and current `history_marker()` against colon, tab, and `1)` wraps inside inline spans: old returned `'was '`; new returned `''` for all three. This is a regression introduced by this fold, beyond the explicitly deferred fenced-code case.

**M2 — The new top-level classification guard has no discriminating suite case.**  
`scripts/find-claim.py`, `collect_files()`:

```python
try:
    is_dir, is_file = p.is_dir(), p.is_file()
except OSError as exc:
    unreadable_dirs.append(f"{raw}: {type(exc).__name__}")
    continue
```

Removing this entire guard restores the exact explicitly named unreadable-path crash it fixes, while every self-test remains green.

**Ran:** syntax-compiled, in-memory mutation replacing the block with:

```python
is_dir, is_file = p.is_dir(), p.is_file()
```

Then ran `self_test()`: **rc=0, 79/79, no `[FAIL]`**.

With an actual chmod-000 directory containing an explicitly named `claim.md`, plus readable control file:

- Shipped `main()`: **rc=2**, names `PermissionError`.
- Mutated `main()`: unhandled **`PermissionError`**.

The suite exercises the walk classification site, but does not protect this newly added site.

## Low

**L1 — The new metadata-fix explanation falsely claims disappearance is handled.**  
`scripts/find-claim.py`, `collect_files()`:

```python
if not q.is_file():
    continue
```

The new comment says a file deleted between discovery and classification now joins the unreadable channel and exits 2. Under Python 3.12, `Path.is_file()` returns `False` for this disappearance; it does not raise an exception for the guard to catch.

**Ran:** real temporary directory with control and claim files; intercepted classification to delete the already-discovered claim immediately before the actual `Path.is_file()` call. `main()` returned **0**:

```text
ok — absent in the searched files ... so the search worked.
(1 file(s) searched)
```

The runtime omission predates this fold; the in-scope defect is the newly added assertion that the fold fixed it.

**L2 — The claimed fifteen explicitly labelled heuristic cases are eleven.**  
`scripts/check-provenance.py`, `BOLD_CASES`; the explanatory comment says:

```text
The witnesses above are kept as cases
```

**Ran:** enumerated runtime case tables and executed all labelled inputs under Python 3.12. Found **11** `KNOWN WRONG` / `KNOWN MISSED` cases. Five of the fifteen documented witnesses have no corresponding case:

```text
option 3 chosen
level 2 access
attempt 2 failed the gate
table 3 lists them
6 that survived
```

Their outputs reproduce the documented limitations, but their claimed case coverage does not. This is a coverage/population finding, not a complaint that the heuristic is imprecise.

**L3 — Threshold sensitivity remains partly unguarded; this is a coverage lead.**  
`scripts/check-plan-code.py`, `expect_explained()`:

```python
EXPECT_OVERLAP_FLOOR = 12
EXPECT_OVERLAP_FRACTION = 0.3
need = max(floor, int(len(expect) * fraction))
```

**Ran:** independently syntax-compiled each in-memory threshold mutation and executed `_self_test()`:

- Floor **12→11**: **234/234**, rc=0.
- Floor **12→13**: **234/234**, rc=0.
- Fraction **0.3→0.4**: **234/234**, rc=0.
- Fraction **0.3→0.2**: rc=1 with the named overlap `[FAIL]`.

The suite guards dropping the fraction, but does not pin both stated constants by adjacent-step cases. No live binding failure from these surviving mutations was established.

**L4 — The modified overlap case’s length is wrong.**  
`scripts/check-plan-code.py`, `_self_test()`:

```text
a 12-char overlap does NOT explain a 54-char expect
```

**Ran:** `len("the REVISED wording counts as unresolved, never as done")` under Python 3.12: **55**, not 54.

## Checked and found SOUND

**The clean-fold hypothesis is refuted:** M1 establishes another fix-induced regression.

Executed all five requested `--self-test` commands under **Python 3.12.9**, capturing command exit codes directly:

| Suite | Passed | rc |
|---|---:|---:|
| find-claim | 79/79 | 0 |
| check-withdrawal | 90/90 | 0 |
| check-provenance | 128/128 | 0 |
| check-plan-code | 234/234 | 0 |
| codex-frontier-model | 39/39 | 0 |

Independently reproduced:

- `EXPECTED_MUTATIONS`: **62 manifests, 1,509 entries**.
- Disk JSON: **62 manifests, 1,509 entries**, every declared per-manifest count matches.
- `--binding`: **rc=0, 1,517 anchors / 1,509 entries**.
- Requested diff statistics: **9 files, 625 insertions, 66 deletions**.
- Final worktree status: clean.

Additional checks:

- `figure_offsets_in_hit()` returns `[0]` when absent, so its caller cannot receive an empty offset list through this function. The fallback has a case.
- Executed all five new withdrawal manifest mutations in memory. Each parsed and produced named `[FAIL]` output. The caller’s `all→any` mutation was killed by the real-repository case.
- Each new sentence-boundary alternative has a discriminating case: deleting it independently produced its named `[FAIL]`.
- Executed the inode-to-resolved-string manifest mutation: parsed, rc=1, named shape `[FAIL]`; local alias cases also failed.
- All located `collect_files()` tuple-unpacking callers use five fields.
- Checked all five accepted case-name keywords, `CASES` table acceptance, `CASE_CALL_RE` assignment exclusion, and `.split(...)` exclusion.
- HEAD probes accepted backticked `HEAD`, `HEAD~1`, `HEAD~`, `HEAD^`; refused `HEAD123`, `HEADS`, and bare prose about HEAD.
- `{"models":[]}` reaches the distinct **EMPTY** refusal, not the new malformed-shape refusal.

All mutations were executed in memory; repository files were not edited.

## CANNOT RUN

Native Ubuntu/case-sensitive-filesystem execution was unavailable in this macOS run. Consequently, cross-filesystem behavior of the inode replacement is **not certified**. Local suite success and the structural mutation kill do not constitute a native Linux pass.
