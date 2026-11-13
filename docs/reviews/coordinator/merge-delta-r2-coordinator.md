# Round 2 — `merge-delta` (PR #491, backlog #426) — coordinator — NOT CONVERGED (Codex); two Mediums FIXED as one class

REVIEW GAP: claude — alternation. Round 2 runs ONE half; round 1 ran both.

Codex half: `docs/reviews/codex/merge-delta-r2-codex.md`, on `ba86d9c1`.

```yaml
round: 2
fixes_nontrivial: true
subject: merge-delta
halves:
  codex: ran
  claude: gap
findings:
  - {id: X-M1, severity: Medium, aim: deliverable, fix_induced: true, component: master-side, disposition: fixed}
  - {id: X-M2, severity: Medium, aim: deliverable, fix_induced: false, component: master-side, disposition: fixed}
```

**Codex NOT CONVERGED.** It ran the self-test (237/237) and the scoped mutation sweep (90 killed, 90 attributed). Both
findings are false CLEARs, measured on real fixtures.

⚠ **The wrapper exited 3, and the filed review is kept.** Codex wrote `merge-delta-r2-codex.md` into the tree itself
during the run. The wrapper then refused to promote its own capture over it (the verdict's `reason`: *NOT PROMOTED:
REFUSING — the promoted review already exists*). Its capture was outside the repository, in the session scratchpad,
and it held the same two findings, rated High there. The filed document rates them Medium, and this record follows
the filed document.

**X-M1 — FIXED.** r1 forced `-c merge.default=text`, but git still honours a configured `merge.text.driver`. A driver
set in repository config, in an included file, or through `GIT_CONFIG_COUNT` turned a real conflict into a clean merge
equal to HEAD. Fix-induced: the `text` name was r1's own flag.

**X-M2 — FIXED.** The system `gitattributes` (`$(prefix)/etc/gitattributes`) survives `--attr-source=<empty tree>`, and
`* merge=union` there cleared the same conflict. Not fix-induced: the layer was open before r1. r1's claim that it had
removed every attribute source was what was wrong.

**THE CLASS, NOT A THIRD `-c`.** This is the third round to find another configuration source: the in-tree attributes
and `info/attributes` (r1), then the `text` driver and the system attributes (r2). One more override per source cannot
terminate, so the synthetic merge now runs in an ISOLATED repository:

- `_isolated_git` makes a temp bare `GIT_DIR` with `init --template=`. Its `objects/info/alternates` points at the
  real object store, resolved through `rev-parse --git-common-dir`. It has no config, no attributes, no hooks and no
  refs.
- `isolated_env` (pure) is the whole environment, built from scratch and never filtered from the caller's:
  `GIT_DIR`, an empty `HOME`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_ATTR_NOSYSTEM=1`,
  `GIT_TERMINAL_PROMPT=0` and `PATH`. No `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS` or `XDG_CONFIG_HOME` gets in.
- `merge-tree`, and the `ls-tree` of its result, run there. `--attr-source=<empty tree>` stays. If the repository
  cannot be built, the result is `None`, the strict rule.

**What the isolation made redundant, and was REMOVED.** These were removed: `-c core.attributesFile=/dev/null`,
`-c merge.default=text`, and the `info/attributes` refusal (`attributes_in_force`, `_info_attributes`, and their six
mutations and four cases). The r1 real-git cases for a worktree `.gitattributes`, `core.attributesFile`, a repository
`merge.default` and `info/attributes` stay, and they are green without those mechanisms. The mutation that runs the
merge in the real `GIT_DIR` reds four of them, and the `merge.text.driver` and `info/attributes` cases too. So the
isolation is what protects them now. `info/attributes` is now stronger than in r1: the merge is BUILT and the
conflict is named, where r1 refused to build it and returned `None`.

**Cases (253, up from 237).** Each real-git source has a CONTROL. The control runs r1's own command in the real
repository and shows the source is live (rc 0, clean):

- `merge.text.driver` plus `merge.default=text` in repository config, in an `include.path` file, through
  `GIT_CONFIG_COUNT` env, and through an inherited `GIT_CONFIG_SYSTEM`. Each is still charged.
- The review's `includeIf.gitdir:` did not match under this suite's temp path on git 2.49 (measured), so the include
  case uses a plain `include.path`. The layer is the same.
- `info/attributes`: the conflict is named and charged through the gatherer.
- Replace refs: see below.
- Failure paths: an unresolvable object store, a common dir with no objects, no `git` on PATH, a `git` whose `init`
  fails, and a failed `hash-object` or `ls-tree` injected into the isolated runner. Each gives `None`.
- Pure: the exact environment keys, `GIT_ATTR_NOSYSTEM=1`, no PATH meaning no PATH, and the argv.

⚠ **X-M2 has NO real-git case.** The system attributes path is compiled in, and no environment variable relocates
it. The suite does not write outside its temp dir, and it never writes `/usr/local`. The layer is pinned by the pure
environment case. The live effect was measured by the review: `GIT_ATTR_NOSYSTEM=1` restored the conflict.

**Replace refs and grafts.** The isolated repository has NO refs, so `refs/replace/` and `info/grafts` are not read.
The merge is of the objects the SHAs name. Measured: with `git replace <round> HEAD`, r1's merge in the real repository
is clean (rc 0), and the isolated merge still names the conflict. That direction REQUIRES a round. The rest of the
checker (`diff`, ancestry, HEAD's entries) still reads the real repository with its replacements, which is unchanged
from before and what Codex probed. CI's checkout fetches no `refs/replace/`.

**Mutations: 90 → 94.** Six were removed with the code they mutated. r1's *merge-tree reads the branch's own
.gitattributes again* (the `--attr-source` drop) now names the pure argv case. The flag is a belt: in an unborn bare
repository no tree attributes are read, and no real-git case reds without it (measured). r1's merged-tree `ls-tree`
mutation was re-anchored. Ten were added: inherit the caller's environment, drop each of `GIT_ATTR_NOSYSTEM`,
`GIT_CONFIG_NOSYSTEM` and `GIT_CONFIG_GLOBAL`, run in the real `GIT_DIR`, borrow no objects, crash on `OSError`, proceed
with no isolated repository, drop `PATH`, and fall back to the caller's `PATH`.

⚠ **SECOND LOCKS, not mutation targets** (measured as survivors, and the code says so): the common dir's empty-answer
and `is_dir` checks, and `init`'s return code. Without them the alternates name nothing, or no repository exists. The
merge then cannot find the round's commit, and `parse_merge_tree` reads that as `None`.

**Thrashing?** No. Round 1's findings were not fix-induced. Round 2's X-M1 is. One fix-induced round is not two
consecutive ones (`dev-process.md`, Phase 6). The class fix above is meant to stop a third.
