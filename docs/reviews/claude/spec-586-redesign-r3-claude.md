Reviewed head: 31e94dd81704bf6dc218edc53cd14ed007652105

# Round 3 (CAP) — `spec-586-redesign` — Claude half

REVIEW GAP: codex — alternation

Subject: `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `31e94dd8` (the round-2 fold).
Mandate: REFUTE. Owner §7 decisions are not re-litigated. Attribution to the round-2 fold was checked with
`git diff 4686aafc 31e94dd8 -- <spec>`, not from memory.

**Thrashing answer, up front.** One HIGH (F1), and the round-2 fold did NOT cause it: rule 3(a) has read the same
way since before round 1. It is the PROBE twin of r2 Codex F1, which round 2 fixed for listings only. Two findings
ARE caused by the round-2 fold (F4 from R2-X6's wording, F6 from R2-X7's disposition). Both are MEDIUM, and
neither loses a read. Round 2's simplifications held up: none of its widened refusals (`..`, listings through
links, listed-ancestor cross-run, the unfiltered table, write-by-default) lets a lost read through as `complete`.

## Findings

### F1 — HIGH — §2 Use rule 3(a) (and §8.3) — a probed DIRECTORY appears or vanishes through a descendant's `A`/`D`, and nothing picks
- **Construction.** Guard T's suite runs `d = ROOT/"docs/superpowers/archive"; if d.is_dir(): for f in sorted(d.glob("*.md")): check(f)`
  (the exact shape of `check-goal-status.py:183` and `check-anchors.py:118`, MEASURED by reading them). At R,
  `archive` does not exist: the trace shows a failed `stat` of `docs/superpowers/archive` (so it is in `probed`),
  no `getdents64` of it, and no listing of `docs/superpowers` or `docs` in this branch. The trace is `complete`.
  The PR adds `docs/superpowers/archive/x.md`, with an invalid header. `Δ` = {A `docs/superpowers/archive/x.md`}.
  - 3(a): the `A` path is not in `reads`/`probed`. Only its PARENT is.
  - 3(b): no ancestor was LISTED.
  - 3(c): directory quotes are dropped, and `x.md` is named nowhere.
  - 3(d): `git_membership` is false.

  T is skipped. At HEAD its control now globs the new file and goes red, or its mutants' verdicts change.
- The mirror case is just as live. `archive` exists at R with one file, and T stat-probes it but does not list
  it (for example `if d.is_dir(): run_subcheck(d)`, where a child lists it under a path the child resolves
  outside the copy). The PR deletes that last file, the staged tree has no `archive`, and the branch flips.
- **Not the owner-accepted bound.** The UNMUTATED run probed the path. That is exactly Q1 B's own premise:
  "an existence check may be its only dependency".
- **Caused by the r2 fold?** No. 3(a) compares only exact paths in this text and in the pre-r1 text. The fold
  fixed this class (directories appearing or vanishing that git reports only as file `A`/`D`) for `listed`
  (R2-X1) and not for `probed`/`reads`. So it is a sibling of a fix, not a consequence of one.
- **Fix (a widening, no model).** In 3(a), an `A` or `D` path P also picks when ANY ancestor of P is in `reads`
  or `probed`. This mirrors 3(b)'s any-ancestor reading. Cost: about nil. The import system already stats and
  lists `scripts`, so 3(b) already picks those targets. Add §8.3 cases for both directions, each with an
  adjacent negative (an `A` under an unprobed sibling directory).

### F2 — MEDIUM — §2 Record (two seeds, union) and §4 — a hash-order read under the PR sweep's RANDOM seed is in neither fixed seed's set
- **Construction.** T's suite does
  `for p in {"docs/a.md", "docs/b.md", "docs/c.md"}: if p in index: use(p); break`, all three files exist, and
  only the first one in set order is opened. Under the two fixed seeds both runs open `a`, so the sets are
  equal, `seed_dependent` is false and the trace is `complete`. A PR sweep is unseeded (`mutation_env(seed=None)`
  inherits, and Python randomises). A PR modifies `docs/c.md`, so T is skipped, yet under about a third of
  seeds T at HEAD reads `c`.
- **Not the accepted bound.** The unmutated run reads `c` under those seeds. Two samples bound nothing, and the
  harness's own comment measured seed-dependent outcomes at about 1 in 120.
- **Caused by the r2 fold?** No. This is round 1's rule (r1 Claude F6).
- **Fix (as a refusal, simplest).** A `seed_dependent` target is INCOMPLETE (`seed-dependent reads`), not
  unioned. This does NOT close the agreeing-seeds case above. State that case in §4 as a bound, or have each PR
  shard set and log an explicit random `PYTHONHASHSEED` per suite run. That is still unseeded in distribution, so
  it leaves the 2026-11-06 decision intact, and it also repairs F6.

### F3 — MEDIUM — §2 cross-run rule and §4.3 — another target's MUTANT writes in the shared shard tree are not recorded, yet §4.3 says cross-run flows are "no longer in this bound"
- `seed_trees`' docstring (`scripts/check-plan-code.py`, read at this head): "Within one seed's tree, a later
  mutant still sees what an earlier mutant's run left there". `wrote` is recorded from each target's CONTROL
  only.
- **Construction.** U reads F (so U is picked) and has a mutant whose run leaves
  `<tree>/docs/generated/flag` when F has some value. T, later in the same shard, probes that path, and its
  cold trace shows the probe. U's control never writes it, so no cross-run refusal fires. The PR changes F and
  T is skipped. At HEAD, T's verdict in a full shard depends on U's mutant's leftover.
- **Caused by the r2 fold?** No. This is round 1's claim in §4.3; round 2 widened the check but kept the claim.
- **Fix.** Restate §4.3. A flow through another target's MUTANT run is in the bound, the same family as §4.1,
  and pre-existing harness exposure (cite `seed_trees`). Do not add a mechanism.

### F4 — MEDIUM (buildability; fail-closed to a zero saving) — §2 "How each call counts" — under `-yy` every descriptor call "names a path", so the literal text classes `read`, `close`, `lseek`, `mmap`, `fcntl`, `ioctl` as WRITES
- The text says: "Every other call that names a path or a descriptor `-yy` labels ... is `wrote`". The
  read-only class lists "the descriptor and process calls that name no path". With `-yy`, every fd argument is
  printed with its path (`close(3</t/scripts/fixture_git.py>)`), so no descriptor call "names no path".
- Read literally, every target "writes" every file it closes. Paths under the copy are compared relative, so
  U's `close` of `scripts/fixture_git.py` refuses every T that reads it (cross-run). That is all targets, and
  the saving is 0. The implementer must guess which fd calls are read-only.
- **Caused by the r2 fold?** YES: R2-X6's sentence.
- **Fix.** Enumerate the fd-only read-only calls by name: `read*`, `pread*`, `lseek`, `close`, `dup*`,
  `fcntl` (all but lock commands, or all), `ioctl`, `mmap`, `fstat`/`newfstatat` with `AT_EMPTY_PATH`, `poll`,
  `select`, `epoll_*`, `getdents64` (`listed`), `fsync`, `fadvise64`. The table then classifies by NAME, and
  the `-yy` label only supplies the path for the write-class calls (`write`, `pwrite*`, `ftruncate`,
  `fchmod`, `fchown`, `fallocate`, `f*xattr` setters).

### F5 — MEDIUM (cost, unmeasured, fail-closed) — §2 cross-run rule — whole-trace comparison refuses most spawner pairs over `/dev/null`
- Python's `subprocess.DEVNULL` opens `/dev/null` `O_RDWR`, so it is in `wrote`, and the path is in that
  target's `probed`. 17 `scripts/*.py` use `DEVNULL` (MEASURED, `grep -l`). Any two such targets refuse each
  other ("reads or probed ... meet a path any OTHER target's run wrote"). git and Node may add more (`/dev/tty`,
  `/dev/pts/*`). §5 says these refusals are UNMEASURED. This one is predictable now, and it may erase most of
  strace's gain over the audit hook.
- **Caused by the r2 fold?** Partly. The whole-trace scope and `O_RDWR` = write are round 1's. Round 2 made the
  whole-trace scope explicit ("the cross-run check's reads, probes and listings keep every path") and widened
  `wrote` by default.
- **Fix.** Exempt from the cross-run comparison only paths that carry no state between runs: character devices
  (`/dev/null`, `/dev/zero`, `/dev/full`, `/dev/*random`, `/dev/tty`, `/dev/pts/*`), `/proc/**` and `/sys/**`.
  NOT `/dev/shm`, which is tmpfs. Case it.

### F6 — MEDIUM — §2 *A MISS, precisely* and §8.6 — a real, seed-dependent miss is classed INCONCLUSIVE, so the Q4 gate cannot fail on it
- The fold makes a difference that does not reproduce under the two fixed replay seeds INCONCLUSIVE ("the PR is
  not counted"). F2's hole shows itself exactly that way: it lives in seeds OTHER than the replay seeds. Such a
  miss never latches, and shadow mode switches after 20 other clean PRs. Q4's decision is "switch only if no
  would-skip target's verdicts differ", and here a difference WAS observed.
- The replay also runs one mutant in isolation, without the shared-tree leftovers of the shard's earlier runs
  (F3). So a shard-order difference also reads INCONCLUSIVE.
- **Caused by the r2 fold?** YES: R2-X7's disposition ("anything else ... INCONCLUSIVE").
- **Fix.** A difference that did not reproduce is not a clean comparison. Either latch it as a MISS-UNCONFIRMED
  that blocks the switch until a human reads it, or (better, with F2) log each PR suite run's actual seed and
  replay under it.

### F7 — LOW — §2 staging provenance and listing-through-link — the machinery maps NOTHING today; the "21 tracked symlinks" figure is not staged
- `git ls-files -s` mode `120000` gives 21 paths, ALL under `.claude/skills/` (MEASURED). `HARNESS_TREE` stages
  `.claude/hooks` and `.agents/skills`, not `.claude/skills` (read at `scripts/check-plan-code.py`
  `HARNESS_TREE`). So 0 tracked symlinks are staged, and the provenance map and the listing refusal fire on
  nothing.
- The spec also leaves open whether the map is keyed by PREFIX (a directory link covers `docs/alias/new`, which
  did not exist at staging) or by enumerating existing paths. Enumeration loses a failed probe of
  `alias/new` when a PR adds `real/new`.
- **Fix (simpler and sound).** Replace both rules with one refusal: a read, probe or listing at or under a
  staged path that was a repo symlink is INCOMPLETE (`through a repo link`). Cost today: 0 targets (MEASURED
  above). It removes the map and its ambiguity.
- **Caused by the r2 fold?** No (r1). Round 2 added the listing refusal on top of the map.

### F8 — LOW — §2 `.git` rule and real-checkout mapping — no suite reaches the real checkout today
- `grep -l GITHUB_WORKSPACE scripts/*.py` gives 0 hits (MEASURED). The staged copy lives under the temp dir,
  outside the workspace, so git discovery cannot reach the checkout either. The real-checkout mapping and
  `git_membership` serve no suite today.
- **Simpler.** Any path under `$GITHUB_WORKSPACE`, its `.git` included, is INCOMPLETE. That is today's rule,
  which owner Q3 already accepts as the fallback. Cost today: 0 targets. Keep the fixture rule (drop a `.git`
  component outside the checkout) as it stands.
- **Caused by the r2 fold?** No.

### F9 — LOW — §2 link table — "a link that already existed ... cannot point into it, since the copy's temp path did not exist yet" is false for a link to an ANCESTOR of the copy
- A pre-existing `L -> /tmp` makes `L/<copy>/docs/x` name a staged path. On a GitHub runner the INFERRED
  instances are few: `/proc/self/root` is already refused by the `/proc` rule. But the reasoning is wrong, and
  the implementer cannot tell how to detect "a link the table cannot resolve" for a pre-existing component
  without lstat at parse time.
- **Simpler.** A failed or path-only call that traverses ANY link created during the trace is INCOMPLETE, and
  a pre-existing link is resolved by `realpath` at parse time and refused if it lands at or above the copy.
  This removes the table's resolution logic: chains, relative targets, renames of links. Cost: targets that
  probe through a runtime link into the tree (`check-review-recorded`'s `_cli` fixture is the named one) lose
  their read set for FAILED probes only. Successful opens keep the `-yy` label.
- **Caused by the r2 fold?** No (r1). Round 2 only removed the `..` fold in front of it.

### F10 — LOW — §2 Use and validity key — a dependency change over R..BASE is not seen
- Rule 1 fires on a dependency manifest in the PR's own diff only. The validity key holds Node MINOR but no
  lockfile. A `package-lock.json` bump over R..BASE changes the staged, UNTRACKED `node_modules/typescript`,
  whose reads are never in `Δ`. So T's reads at BASE can differ from R's.
- **Fix.** Add the dependency manifests' blob ids to the validity key, or treat a rule-1 dependency path in
  R..BASE as no usable set.
- **Caused by the r2 fold?** No.

## Round-1 rules: simpler as a refusal?

| Rule | Verdict | Selection it costs, in words |
|---|---|---|
| Shared-cwd / `CLONE_FS` model | **Keep.** The per-task copy-on-fork cwd is needed for ANY relative path in a child; the sharing rule adds one map. A refusal ("relative failed/path-only call in a task sharing FS with a task that chdir'd") is about as long | ~nothing either way (threaded chdir is rare); build step 1 should count it |
| Link table | **Refuse** (F9) | targets whose FAILED probes go through a runtime-created link; successful opens are unaffected |
| Staging provenance for reads + listing-through-link | **Refuse** (F7) | nothing today: 0 staged tracked links (MEASURED) |
| `.git` membership / real-checkout mapping | **Refuse** for the real checkout (F8); keep the fixture-`.git` drop | nothing today: 0 suites name `GITHUB_WORKSPACE` (MEASURED) |
| `Δ = R..BASE ∪ BASE..HEAD` | **Keep.** The refusal ("R ≠ BASE → today's rule") is simpler, but it gives up every lag-1+ run | the lag-1/2 saving: 31 of 113 PR runs under §5's dedicated-job model (INFERRED there), 63% under the save-at-end model |

## Buildability: where an implementer must guess

1. Which descriptor-only calls are read-only (F4).
2. `probed`'s record definition ("tried to open and could not, or passed to a `stat`- or `access`-family call")
   disagrees with the recorder bullet ("EVERY path any call names"). A failed `execve` of an optional script,
   a `chdir`, `statfs` or `inotify_add_watch` is in one and not the other. Following the record definition
   loses a probe while the trace reads `complete`. Make the record definition cite the bullet.
3. "Under the staged roots": does it INCLUDE a root itself? `.agents/skills`, `docs` and `scripts` are roots,
   and listings of them are what 3(b) needs (`check-docs.py:302-306` lists `.agents/skills`). §5's scoring
   treated `scripts` as included. Write "at or under".
4. The provenance map's key: prefix or enumeration (F7).
5. How a pre-existing link component is detected on a failed or path-only call (F9).
6. `git diff --name-status` statuses beyond `A`/`M`/`D` (`T` typechange, `U`). Say whether they are FULL
   (unparseable) or `M`.
7. On-sight refusals omit the mount family (`mount`, `umount2`, `open_tree`, `move_mount`, `fsmount`). Each
   changes path resolution. Under write-by-default they would be `wrote`, not INCOMPLETE.
8. `-yy` labels can carry ` (deleted)` and strace's escaping (`\"`, octal). The parser's handling of both is
   unspecified. The label is read by strace after the syscall returns, not "at that moment"; a concurrent
   rename shows the new name.
9. `strace -f -o` interleaves: a child's first lines can precede its parent's `clone(...) = PID` line. The cwd
   model needs a rule for lines from a pid it has not yet seen being created (defer, or INCOMPLETE).
10. "The strace version the one the recorder pins": nothing says the recorder pins a version, or how
    `sweep-select` (which runs no strace) learns it.
11. §8.3 still cases a "stale (read or probed path modified)" set falling back. §3 REPLACED that row: such a
    path is in `Δ` and PICKS. The case tests a rule that no longer exists.
12. The comparator's re-run (§2 *A MISS*): which job runs mutants (`shadow-compare` is a read-only daily job),
    on which staged trees, and in what shard state (F6).

## Verdict

One HIGH (F1, not fix-induced) with a one-clause fix; five MEDIUMs, two of them fix-induced (F4, F6) and neither
losing a read; four LOWs. The round-2 fold's own refusals held: no construction against them loses a read while
`complete`. The spec is NOT yet buildable without the twelve guesses above. Items 1 and 2 are the
load-bearing ones.

VERDICT: NOT CONVERGED
