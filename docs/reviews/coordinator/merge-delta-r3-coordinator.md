# Round 3 — `merge-delta` (PR #491, backlog #426) — coordinator — NOT CONVERGED (Claude); one Medium and one Low FIXED

REVIEW GAP: codex — alternation. Round 3 runs ONE half; round 2 ran the Codex half.

Claude half: `docs/reviews/claude/merge-delta-r3-claude.md`, on `5f8b270f`.

```yaml
round: 3
fixes_nontrivial: true
subject: merge-delta
halves:
  claude: ran
  codex: gap
findings:
  - {id: C-M1, severity: Medium, aim: deliverable, fix_induced: false, component: master-side, disposition: fixed}
  - {id: C-L1, severity: Low, aim: deliverable, fix_induced: true, component: master-side, disposition: fixed}
```

**Claude NOT CONVERGED.** It ran the self-test (253/253) and the scoped mutation sweep (94 killed, 94 attributed). M1 is
a false CLEAR measured on a real fixture. L1 is a temp-dir leak, measured as one new `crr-merge-*` dir per sweep.

**C-M1 — FIXED.** Both tree lookups (`_final_entries` on HEAD, `_master_side` on the merged tree) passed the changed
paths to `ls-tree` after `--`. Git reads that argument as a PATHSPEC. So `:/evil.sh`, `:(top)evil.sh` and
`:(literal)x/evil.sh` were looked up under another name, came back absent on both sides, and absent == absent cleared
an unreviewed file. A decomposed-Unicode name did the same under `core.precomposeunicode=true`, the macOS default,
because git precomposes its argv and not the names stored in a tree. Not fix-induced: the pathspec lookup predates
round 1, and #426's absent/absent arm is what turned the miss into a clear.

The fix removes the class rather than escaping each magic:

- `ls_tree_argv(tree)` (pure) lists the WHOLE tree with no path argument:
  `-c core.precomposeunicode=false ls-tree -r -t -z --full-tree <tree>`. With no path in the argv, git has nothing to
  reinterpret. `-t` keeps the tree entries on the way, so a path that is a directory still has an entry, as the
  pathspec form gave it. The `-c` is a belt.
- `select_entries(listing, paths)` (pure) keeps exactly the names asked for, by string equality.
- Both runners (`_git` and the isolated one) decode with `utf-8` + `surrogateescape`. A non-UTF-8 name then decodes to
  the same string in `diff -z`'s changed-path list and in the listing. Before this, it would have raised. The changed
  paths already came from `diff --name-only -z` (`diff_argv`), so no C-quoting is involved.

**C-L1 — FIXED.** In `_isolated_git`, `mkdtemp` and the setup sat outside the `try/finally` that removes the temp dir.
Any exception other than `OSError` left `crr-merge-*/home` behind. The `try/finally` now opens right after `mkdtemp`.
Fix-induced: `_isolated_git` is round 2's own code.

**Cases (275, up from 253).** All are real git except the three marked pure. Each file is added after the round
through the index alone. There is no checkout, because a non-UTF-8 name cannot exist on APFS.

- `:/evil.sh` and `:(top)evil.sh`, 4 cases each:
  - a CONTROL showing the old pathspec lookup returns nothing in this very repository;
  - HEAD's lookup finds the name;
  - the merged tree's lookup finds the name;
  - the gatherer charges the file.
- A decomposed (NFD) name under `core.precomposeunicode=true`. The same three cases, plus a control whose want is the
  platform's own answer, because git precomposes argv only on macOS.
- A name holding a newline, and a name holding non-UTF-8 bytes. Each gets the same three cases.
- A path that is a directory in HEAD still has a `040000` entry.
- Pure: the argv, and exact selection (`:/a` is selected, `a` is not).
- L1: `isolated_env` is swapped for one that raises `ValueError`, under a private `TMPDIR`. The case asserts the crash
  happened AND that no `crr-merge-*` dir remains.

Measured before the fix: the pathspec controls return `''` for `:/x.sh` and for the NFD name under precomposition
(macOS, git 2.49). That is the reviewer's result.

**Mutations: 94 → 102.** The `except OSError` mutation (r2) was re-anchored to the new indentation. It still names the
"no `git` on PATH" case: under it, `FileNotFoundError` escapes, and the case reads `raised FileNotFoundError`.
Eight were added:

- each lookup passes the paths as a pathspec again (two mutations);
- the listing drops `-r`;
- the listing drops `-t`;
- the listing drops the precompose `-c`;
- the selection returns the whole listing;
- the isolated runner decodes strictly;
- the temp dir is removed only on the normal path.

⚠ `_git`'s own `surrogateescape` has no mutation: the real-git fixture drives its own runner, so `_git` is reached only
through `main`. It is there so the two runners agree. The precompose `-c` is pinned only by the pure argv case, because
with no path in the argv nothing is normalised.

**Temp dirs.** The three `crr-merge-*` dirs the reviewer found (11:30, 11:43, 11:55) were older than this fold and
each held only an empty `home/`. They were deleted. The scoped sweep was run after the fix and its temp-dir delta was
measured: see the fold report.

**Thrashing?** ⚠ **The arming condition is MET in `master-side`, by the letter.** Round 2's X-M1 was fix-induced by
round 1's `-c merge.default=text`. Round 3's C-L1 is fix-induced by round 2's `_isolated_git`. Those are two
consecutive rounds, in one component (`dev-process.md`, Phase 6). C-M1, the round's only Medium, is not fix-induced.
The fix-induced finding is a Low cleanup leak, which fails toward NOT clearing. Whether that convenes an architecture
review is the coordinator's call, through `check-review-decision.py`. This record does not soften the header to avoid it.

**Round 4 is under the cap.** `docs/review-method.md` §0 Q4c: from round 4, findings are FILED unless they are a
BLOCKER. The decision-log `merge-delta` row keeps `outcome: null`, with no `rounds_at_termination`. Rounds 1 and 2 left
it that way, and the value is written when the loop terminates.
