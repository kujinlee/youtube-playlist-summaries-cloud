# Round 5 — review-tooling-121-182 — claude

**Subject:** PR #439, branch `review-tooling-121-182`, reviewed at `60dc0b14` (the DEFER fold `c9dcc13c..HEAD` first, then the branch against `origin/master`). Final-tree round on the DEFER route, so every finding below is to be FILED, not folded.

**Mandate:** refute the bet *"the final-tree round finds no write into any docs/reviews through --out"*.

**The bet is REFUTED.** A symlink that appears at a **parent** component of `--out` during the run (not at the leaf) still sends the capture into `docs/reviews/<writer>/`. I reproduced it through the real CLI with a stub codex: a filed review was overwritten, rc 0, and `intrusions: []`.

## Findings

### 1. Major — `scripts/codex-review.py:591-624` (`write_capture`), `:1465`. A symlink at a PARENT component of `--out` redirects the exclusive create and the rename into a filed review. Fix-induced: **no**.

**Why it gets through.** The fold made the LEAF safe: `O_EXCL|O_NOFOLLOW` on the temporary name, then `os.replace` over the entry. But `write_capture` looks up the directory again by its path string at write time, minutes after `out_location_refusal` checked it. `O_NOFOLLOW` covers only the last component, so the temporary file is created wherever the parent resolves *then*, and `os.replace` renames it there.

**Concrete inputs, run through the real CLI** (sandbox checkout A holds the scripts; the reviewed git repo B contains a committed `docs/reviews/claude/victim-r1-claude.md`; the scratch directory is under `$TMPDIR`; the stub codex runs an action and then returns a valid review):

| Case | `--out` | Stub action during the run | Result |
|---|---|---|---|
| S1 | `<scr>/sub1/victim-r1-claude.md` (`sub1` absent at check time) | `ln -s <B>/docs/reviews/claude <scr>/sub1` | **rc 0, victim OVERWRITTEN with the capture, verdict `intrusions: []`**, no warning. `git status` in B shows `M docs/reviews/claude/victim-r1-claude.md` |
| S2 | `<scr>/sub2/victim-r1-claude.md` (`sub2` a real empty directory at check time) | `rmdir sub2 && ln -s <B>/docs/reviews/claude sub2` | **rc 0, victim overwritten**, no warning |
| S2b | `<scr>/sub2b/planted-r9-claude.md` | same swap | rc 0, `planted-r9-claude.md` **created in B's `docs/reviews/claude/`**. The watch reports a change here only because the victim file shows up through the swapped directory |

S1 needs no swap at all. `--out` under a directory that does not exist yet is an ordinary call shape (`mktemp -d` plus a subdirectory), and the agent only has to create that directory as a link. The docstring's *"Not covered: a directory SWAPPED for a link"* names S2. It does not name S1, and neither case is tested. This is the same actor and the same victim as r4 X3, one path component up.

**One-line fix:** pin the directory once, right after `out_location_refusal`: `os.makedirs(parent)`, then `dfd = os.open(parent, O_RDONLY|O_DIRECTORY)`. `write_capture` then creates the file with `os.open(name, …, dir_fd=dfd)` and renames with `os.replace(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)`.

**Verified in a scratch copy** (the worktree was not touched). With that patch, S1 writes the capture into the pinned scratch directory and the victim stays intact. S2 and S2b fail loudly, because the pinned directory was removed, and nothing is written into `docs/reviews`. The patched copy still passes X1, X2, X3 and the false-refusal shapes below. A fixture for S1 should be added beside the r4 X3 case: the stub creates the missing parent as a link.

### 2. Minor — `scripts/codex-review.py:570`. Stale docstring. Fix-induced: **yes**.

`same_dir_or_inside` still says *"A tree that does not exist yet has no identity and matches nothing here; the lexical rule beside it still covers it."* This fold deleted the lexical rule. A not-yet-existing tree is now covered because the rule compares against the CHECKOUT, which exists. **Fix:** replace the sentence with that reason.

### 3. Minor — `scripts/codex-review.py:1465`. A capture write that raises after a paid review exits **1** with no testimony. Fix-induced: **no** (the old `open(…, "w")` raised the same way).

**Inputs:**
- `--out <scr>/isdir.md --allow-overwrite`, where `isdir.md` is an existing directory. Result: `IsADirectoryError` traceback, rc 1.
- `--out <scr>/ro/r.md`, where `ro` is mode 0555. Result: `PermissionError` traceback, rc 1. No verdict file for that review id exists afterwards.

In both cases the gate RAN. rc 1 is documented as *"the gate did NOT run → fall back"*, and no `emit` happens, so a review that was paid for is lost and the caller is told to fall back. The new code does not leak its temporary file on this path: I checked, and no `.tmp` was left.

**Fix:** wrap `write_capture` in a `try/except OSError` that still promotes and then `emit(RC_NOT_FILED or 2, gate_ran=True, …)`. Alternatively, check at pre-flight that `--out` is not a directory and that its parent is writable.

## What the fold did not break (RAN)

- **The r4 inputs, re-run through the real CLI, all hold:**
  - X1, other capitals of a missing `docs/reviews`: rc 2, the tree is not created.
  - X1, an NFD spelling of an NFC `café` root: rc 2, not created.
  - X2, a hard link to the victim with `--allow-overwrite`: rc 0, victim intact, the scratch entry replaced.
  - X3, a late LEAF symlink: rc 0, victim intact, the link replaced by a regular file.
  - Neighbour: a late leaf symlink to the writer DIRECTORY. rc 0, the link is replaced and `claude/` is unchanged.
- **No false refusal** (rc 0) of:
  - `$(mktemp -d)/r.md` (macOS `/var/folders`, resolved to `/private/var/…`);
  - `/tmp/<d>/r.md` (`/tmp` is a symlink to `/private/tmp`);
  - a relative `../../<scr>/rel.md` run from inside the reviewed tree;
  - a scratch path three levels deep that does not exist yet.
- **Mode:** the capture is now always `0o644`. Under umask 002 the old `open` would have produced `0o664`. I measured `0o644`, which is harmless for a scratch file.
- **Cross-filesystem:** the temporary file lives in `--out`'s own directory, so `os.replace` cannot hit `EXDEV`. This holds by construction; I did not exercise it across a real mount.
- **`--allow-overwrite`:** a pre-existing `--out` without the flag is still refused (self-test case). With the flag, a hard-linked or symlinked entry is replaced, not written through.
- `python3 scripts/codex-review.py --self-test`: **203/203 passed** (5.6s).
- `python3 scripts/check-plan-code.py --mutate . --only scripts/codex-review.py`: **66/66 killed, 66 attributed, 0 survivors**, rc 0. The tool labels this run a diagnostic slice, not the gate. ⚠ No mutant could have exposed finding 1: it is a missing protection, not a weakened one.

## Verdict

**NOT CONVERGED.** The bet's named failure observation occurred: a write into `docs/reviews` through `--out` (finding 1). Counts: **0 Blocking, 1 Major, 2 Minor**. On the DEFER route, all three are filed, not folded.
