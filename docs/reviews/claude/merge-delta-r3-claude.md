Reviewed head: 5f8b270fbd01ec51b8c1b3345b52e7821173520e

# Round 3 — `merge-delta` (PR #491, backlog #426) — Claude half — NOT CONVERGED

Subject: `git diff ba86d9c1..5f8b270f` and the whole clear path. The path runs from `round_tails` through
`round_tail` and `master_explains` to `_final_entries`, `merge_onto`, `_isolated_git`, `isolated_env` and
`_master_side`. Mandate: refute "no false clear remains". Codex half: `REVIEW GAP: codex — alternation`
(round 3 runs one half).

## Gates run

| Check | Result |
|---|---|
| `python3 scripts/check-review-recorded.py --self-test` | `253/253 passed`, rc 0, 6 s. No new `crr*` temp dir after the run (before/after listing diffed) |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-review-recorded.py --allow-long-local` | `94 mutation(s), 94 killed, 94 attributed ... 0 survivor(s)`, rc 0. Without `--allow-long-local` it REFUSED (rc 2, budget 10.1 min over 10), and nothing was measured on that run. The sweep LEAKED one `crr-merge-*` dir (finding L1) |

## Findings

### M1 (Medium): an unreviewed guarded file is CLEARED when its NAME is not the literal pathspec `ls-tree` reads. Platform-independent

**Where:** `scripts/check-review-recorded.py:958` (`master_explains`, the `is_absent(want) and is_absent(now)` arm).
The paths reach it through `:1062` (`_final_entries`: `git ls-tree -z HEAD -- *paths`) and `:1207` (`_master_side`:
`iso("ls-tree", "-z", tree, "--", *paths)`).

**What breaks.** Both lookups pass the changed path to `ls-tree` as a PATHSPEC, not as a literal name. `ls-tree`
permits the `top` and `literal` magic. So a path that starts with `:/`, `:(top)` or `:(literal)` is looked up under a
different name. It is missing from BOTH answers, both sides read it as ABSENT, and `master_explains` returns True
("absent and absent"). The strict rule that ran before #426 (`if not seen: return False`, at the merge base `c206f95d`)
CHARGED this path. #426 turned it into a clear.

`seen` is the uncommitted map the reviewer was handed. That map is empty for every file that was already committed at
the round's head. So this is not limited to new files: a COMMITTED `:/x.sh` that is edited after the round also falls
into the `master_explains` arm and is cleared.

**Fixture** (real git, `core.precomposeunicode=false`, `core.ignorecase=false`, i.e. Linux/CI-shaped). The steps:

1. Base commit `a.sh`. Branch `br`. Round commit edits `a.sh`. The verdict's reviewed map is `{"a.sh": ...}`.
2. After the round, a commit adds a guarded file holding `evil()` (via `update-index --cacheinfo`).
3. `after` = `diff --name-only -z --no-renames <round> HEAD`. `final` = `_final_entries(guarded_changes(after), git=g)`.
   `ms` = `_master_side(round, merge_onto("master", git=g), guarded, git=g)`.
4. Then `round_tail(after, {"a.sh": "x"}, final, ms)`.

| added path | `final` | master side | `round_tail` |
|---|---|---|---|
| `:/evil.sh` | `{}` | `({}, ∅)` | **`[]` — CLEARED** |
| `:(top)evil.sh` | `{}` | `({}, ∅)` | **`[]` — CLEARED** |
| `:(literal)x/evil.sh` | `{}` | `({}, ∅)` | **`[]` — CLEARED** |
| `:!evil.sh` | raises CANNOT RUN (exclude magic refused, rc 128) | `None` | fails closed |
| `lib/evil[1].sh`, `lib/*.sh` | found | `({}, ∅)` | charged (control: `ls-tree` disables wildcards) |

`round_tail(..., master=None)` charges the first three. That makes this a #426 regression, not a pre-existing hole for
unseen paths. Pre-existing and narrower: a path the reviewer's map recorded ABSENT is cleared the same way by
`same()`'s own absent/absent arm.

**Same class, macOS (Low on its own).** The fixture is the same, but the added file is `lib/café.ts` (an NFD
name, written into the tree via `mktree`) with `core.precomposeunicode=true`. That value is the macOS default: this
repository's own `.git/config` has it, and `init --bare` in `_isolated_git` sets it on macOS. `diff -z` reports the
NFD name, and git precomposes the `ls-tree` argv to NFC. Both lookups miss. Result: `final={}`, master `({}, ∅)`,
**`round_tail=[]`**. With `precomposeunicode=false` it is charged.

**Why the r2 isolation does not cover it.** The defect is not a config or attributes SOURCE. It is how the argv path is
interpreted, and it happens identically in the isolated repository and in the real one. So the two lookups agree on a
wrong "absent".

**Fix direction.** Make both lookups literal. Two options:

- Pass `--literal-pathspecs` (a global option, before `ls-tree`) and `-c core.precomposeunicode=false` to both calls.
  Measured: `git --literal-pathspecs ls-tree -z HEAD -- ':/evil.sh'` returns the entry, and the plain form returns nothing.
- Better, list the tree with no pathspec at all and select exact names in Python.

Either way, "absent" stays an answer git gave about THAT name, never about a name git rewrote. A case per lookup with
`:/x.sh` reds today.

### L1 (Low): `_isolated_git` leaks its temp dir on any exception in the setup block, and the mutation sweep does it on every run

**Where:** `scripts/check-review-recorded.py:1156-1176`. The `mkdtemp` and the setup `try ... except OSError` sit
OUTSIDE the `try/finally` that holds `shutil.rmtree(tmp)` (`:1177` onward). Any exception other than `OSError`
escapes the generator before the `finally` exists, and so does a mutant that removes the `except OSError`. Both leave
`crr-merge-XXXX/home` behind.

**Fixture / measurement.** I listed `$TMPDIR/crr*` before and after the scoped sweep. One NEW dir appeared,
`crr-merge-5_t6k932`, holding only `home/`. That matches mutant 91, *a failure to build the isolated repository
crashes*. Under that mutant the "no `git` on PATH" case raises `FileNotFoundError` after `os.mkdir(home)`. Three
identical `crr-merge-*/home` dirs from 11:30, 11:43 and 11:55 today were already present. They are consistent with
earlier sweeps by the builder and the fold, but I did not attribute them. The self-test alone leaked nothing.

In production, the reachable non-`OSError` exceptions are narrow (`KeyboardInterrupt`, an unexpected `ValueError` from
`subprocess`). It is backlog #411's class, and the fix is one structural move: open the `try/finally` right after
`mkdtemp`. Fail direction is unaffected: an escaping exception crashes `main`, which does not clear.

I removed the leaked dir from my run. I did not touch the three older ones.

## Refuted hypotheses (no finding)

- **Inherited config, PATH git, system prefix.** With both `/usr/local/bin/git` (2.49.0, which has a system
  `/usr/local/etc/gitconfig`) and `/usr/bin/git` (Apple 2.50.1), `env -i` + `isolated_env`'s keys gives
  `config --list --show-origin --show-scope` = ONLY the temp repository's own `config` lines from `init`.
  `GIT_CONFIG_NOSYSTEM` is honoured by both.
- **`XDG_CONFIG_HOME`.** It is not inherited. `GIT_CONFIG_GLOBAL=/dev/null` replaces both `~/.gitconfig` and the XDG
  file, and `$HOME` is empty, so the XDG `attributes` default resolves into an empty dir.
- **`GIT_EXEC_PATH`.** It is not inherited, so git uses its compiled path. A relocated install fails, and a failure
  reads as `None`.
- **Alternates.** I measured `_master_side` over a real conflict fixture, and each layout below returned the correct
  entries:
  - repo A;
  - B, a `clone --shared` of A (absolute alternates);
  - C, a `--shared` clone of B, with its alternates rewritten RELATIVE (a chain of two);
  - a submodule (`.git/modules/sub` as the common dir);
  - this worktree itself (common dir = the main `.git`).
- **Shallow clone.** It returns `None`, because the isolated repository has no `shallow` file. That is the strict
  rule, so it fails closed. The cost is that the feature never clears in a shallow CI checkout.
- **Replace refs and grafts.** The isolated merge reads raw objects. `is_ancestor`, `merge_onto`, `_changed_since` and
  `_final_entries` honour `refs/replace` in the real repository. For the mismatch to CLEAR, a replacement would have to
  make HEAD's real-repo entry equal the raw merge while the raw HEAD differs. That needs a local `refs/replace`, which
  CI does not fetch. Anyone who can do that can already bypass the local run in simpler ways. No CI-reachable clear.
- **A branch-controlled verdict `commit` as a `merge-tree` option.** `head` must first pass
  `merge-base --is-ancestor <head> HEAD` in the real repository, so it is a resolvable commit. A rev expression
  (`HEAD~1`, a ref name) does not resolve in the ref-less isolated repository. It reads as `None`.
- **`--attr-source` covered only by a pure argv case.** That is acceptable. The isolated `HEAD` is unborn and nothing
  writes a ref, so no tree attributes can be read without the flag. It is a belt, and the r2 record says so.
- **Mutation evidence.** 94/94 killed and attributed. The removed r1 mechanisms are covered by the
  real-`GIT_DIR` mutant (#89) reddening the source cases, as the r2 record claims.

## Fail direction

Every injected failure in `_isolated_git` and `_master_side` returns `None`, and the strict rule then applies. That
covers no common dir, no objects, no `git`, a failed `init`, `hash-object`, `merge-tree` or `ls-tree`, and a shallow
or partial store. **The exception is M1.** There the failure is not detected as a failure: a lookup that answered
about the wrong name is read as a true "absent", in both places.

VERDICT: NOT CONVERGED
