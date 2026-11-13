Reviewed head: aa5c4d78f5f926649f3c6a7c2652efaad0a93042

# Round 3 — `586-slice3` — Claude half (adversarial)

Subject: `scripts/strace_reads.py` slice 3, PR #567, branch `586-slice3`. Drivers were run with `python3 -I` from a
scratch directory outside the repo. They import the module and build `Record`s with `record_from_log`, `merge_seeds`
and `cross_run`.

## Gates run

- `python3 scripts/strace_reads.py --self-test`: **284/284 passed**.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/strace_reads.py`: **206 mutations, 206 killed, 206
  attributed, 0 survivors**, rc=0 (a partial run over one file, as the tool itself says).

## Round 1 and round 2 inputs, re-run

Each one refuses, and each control is still accepted. The copy roots were `/tmp/cU` and `/tmp/cT` (or `/t`), with
staged roots `docs` and `.home` under the copy.

| Input | T's result |
|---|---|
| r2 X1: `openat(AT_FDCWD</tmp/cT>, "/tmp/cT/docs/../.home/cur") = 3</tmp/cT/docs/b.md>`, whole line and split | `unresolved ..` |
| r2 X1: `/proc/self/cwd/.home/cur`, and `/dev/fd/7/cur`, as the SHADOW argument | `unresolved /proc path` |
| relative `../.home/cur` with dirfd `5</tmp/cT/docs>` | `unresolved ..` |
| control: `/tmp/cT/.home/cur` (U planted it) | `cross-run flow` |
| control: `/tmp/cT/.home/other` | `complete` |
| control (read view, `cross` False): `docs/../docs/a.md` with a label | resolved, no refusal |
| `//`, `/./`, and a trailing `/` in the SHADOW argument; relative `cur` / `./cur` with dirfd `5</tmp/cT/.home>`; `chdir` then relative | `cross-run flow` (normalised correctly) |
| undecorated dirfd `5` | `unresolved path` |
| r1 X1 rename of a directory, then a read below it; a write below, then a probe above | `cross-run flow`; sibling control `complete` |
| r1 X2 quoted `sun_path="@state"` | `unresolved path` |
| r1 C1 a `.git` write that a peer reads; r1 C1 S a planted symlink opened by name | `cross-run flow` |
| r1 C2 `write(5, ...)` with no label | `unresolved path` |

`cross` False never reaches `cross_run`. `record_from_log` is the only code that builds a `Record` with sets, and it
passes `cross=True`. `merge_seeds` and `cross_run` only reuse records or refuse them.

## Findings

### Major — R3-1: a SHADOW argument still skips the LINK checks, so a symlink in its prefix hides a peer's symlink

The round-2 fold handled only part of the class. Round 1 exempted the SHADOW argument from three groups of checks:
`..`, `/proc`, and the links (`through a runtime link` and `through a pre-existing link`, in `_resolve`'s
`from_label is False` branch). The `elif cross:` branch in round 2 put back `..` and `/proc`. It did not put back the
link checks. A SHADOW argument is compared by its TEXT across runs. If that text goes through a symlink, it names a
different path from the one the kernel walked. A peer's symlink further down that walk is then never met. This is
the same mechanism as r2 X1.

**Input A (T's own runtime link):**

```text
U:  1  symlink("/tmp/cU/docs/b.md", "/tmp/cU/.home/cur") = 0
T:  1  symlink("/tmp/cT/.home", "/tmp/cT/a") = 0
    1  openat(AT_FDCWD</tmp/cT>, "/tmp/cT/a/cur", O_RDONLY|O_CLOEXEC) = 3</tmp/cT/docs/b.md>
```

The kernel resolves this through U's `.home/cur`.
Actual: `U complete`, `T complete`. `T.all_named = {copy:a, copy:a/cur, copy:docs/b.md}` and
`U.wrote = {copy:.home/cur}`, so nothing meets.
Expected: T refuses (`through a runtime link`), or `cross-run flow`.
The split `<unfinished ...>` / `<... openat resumed>` form gives the same result: `complete`, `complete`.
Control: the same path as a FAILED open (no label, so no SHADOW) refuses as `through a runtime link`.

**Input B (a pre-existing link outside the copy that points into it):** this needs a real filesystem, because the
check calls `os.path.realpath`. Set up `<base>/alias -> <base>/cT`, with copies `<base>/cU` and `<base>/cT`.

```text
U:  1  symlink("<base>/cU/docs/b.md", "<base>/cU/.home/cur") = 0
T:  1  openat(AT_FDCWD<<base>/cT>, "<base>/alias/.home/cur", O_RDONLY|O_CLOEXEC) = 3<<base>/cT/docs/b.md>
```

Actual: `U complete`, `T complete`. `T.all_named = {<base>/alias/.home/cur, copy:docs/b.md}`. The path is outside the
copy, so `copy_norm` leaves it as raw text.
Expected: T refuses (`through a pre-existing link`).
Control: the same path as a failed probe refuses as `through a pre-existing link`. The direct path
`<base>/cT/.home/cur` gives `cross-run flow`.

**Fix (the class, not the instances):** under `cross`, a SHADOW argument should go through every check that a
`from_label is False` path goes through. Simplest: in the cross view, treat SHADOW like False for the
`..`/`/proc`/runtime-link/pre-existing-link refusals, while it stays out of `kept`. `_cwd_pass`'s refusals cannot be
reused as they are, because they also serve the read view. But `_resolve`'s link checks live in the same loop as the
`elif cross:` branch. Each input above, plus its control, should become a self-test case, and the new branches need
mutations.

No other finding. The `.`, `//` and trailing-`/` forms, relative arguments with a labelled dirfd, an undecorated
dirfd, chdir then relative, and the split forms of `..` and `/proc` were all handled correctly. `PROC` also covers
`/dev/fd/N` and `/dev/std*`.

VERDICT: NOT CONVERGED
