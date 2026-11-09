<!-- codex-review: model=gpt-6.1-sol -->

1. **F1 — HIGH — §2 Use 3(b–c), §3: `R..HEAD` loses changes that undo intervening master additions.**  
   Reproduced in a temporary Git repository:

   ```text
   R:    docs/activated absent; directory listed
   BASE: docs/activated added, containing UPPER
   HEAD: PR deletes docs/activated

   BASE..HEAD: D docs/activated
   R..HEAD:    empty
   ```

   A suite lists `docs`, reads its files, and asserts that a guard lowercases their contents. Its identity mutant is killed at BASE but survives at HEAD; both controls pass. At R, `activated` was neither read nor probed. No recorded dependency was modified, and the net `R..HEAD` diff supplies no addition/deletion to match the listed directory. The target is skipped despite its changed verdict. Today’s directory naming rule picks it.

   This occurs at **lag 1**, beyond the accepted mutant-only-read bound.

   **Proposed fix:** Match PR additions/deletions independently against recorded listings and literal names. Union those matches with intervening `R..BASE` activation checks; do not replace them with a net `R..HEAD` diff.

2. **F2 — HIGH — §2 Record: the plain pass can hide dependencies from the traced pass.**  
   Reproduced outside the repository with a suite that caches `docs/value` under its redirected home:

   ```text
   recording plain:  reads docs/value; passes
   recording traced: reads cache only; passes
   BASE mutant:      survives
   HEAD control:     reads changed docs/value into fresh cache; passes
   HEAD mutant:      killed
   ```

   Changing `lower` to `UPPER` produces that verdict change for the identity mutant of a lowercase function. Equal case counts and green controls accept the incomplete read set. This discrepancy arises **within the new plain-then-traced pair**, independently of the already acknowledged difference in preceding suites between recording and shards.

   **Proposed fix:** Run plain and traced passes from equivalent pre-run snapshots, including home and relevant caches. Trace the cold execution whose dependencies initialize subsequent mutant runs.

3. **F3 — HIGH — §2 recorder syscall list and record schema: supported execution can silently omit filesystem dependencies.**  
   `readlink`/`readlinkat`, `openat2`, and `rename`/`unlink` families are absent from the specified dependency extraction. A suite can directly `readlink` a computed path or branch on a failed `unlink`, without opening, statting, or listing that path. A PR modification—or addition after the failed probe—then matches neither recorded dependencies nor necessarily the literal-name safeguard. These are ordinary unmutated dependencies, not mutant-only branches. [`readlink` explicitly reads symlink contents](https://man7.org/linux/man-pages/man2/readlink.2.html).

   `execve` is logged for parentage, but the schema does not say its executable becomes a dependency. Executing a repository binary need not generate a userspace `openat` for that binary. [The kernel loads the executable through `execve`.](https://man7.org/linux/man-pages/man2/execve.2.html)

   **Proposed fix:** Define extraction for execution dependencies, link reads, additional open variants, and successful/failed namespace operations. Unsupported dependency-bearing operations must refuse the target rather than yield `complete`. Ordinary `mmap` following a captured open is already covered; the explicitly accepted `io_uring` limitation is separate.

4. **F4 — HIGH — §2 path filtering, §5 git-only spawners: dropping every `.git` read loses real-repository membership dependencies.**  
   Consider a guard whose suite invokes:

   ```text
   git -C "$GITHUB_WORKSPACE" ls-files docs
   ```

   It can consume tracked filenames from the real repository’s index without opening those working-tree files or listing `docs`. Those metadata reads are either outside staged roots or discarded by the blanket `.git` rule. A PR adding a dynamically matched filename can change the suite and mutant verdicts while leaving the recorded set “unaffected.” [`git ls-files` defaults to tracked files from the index.](https://git-scm.com/docs/git-ls-files)

   Fixture repositories’ metadata and the real checkout’s index therefore cannot share one exclusion rule. Tracing the child does not establish that distinction.

   **Proposed fix:** Exclude only proven fixture metadata. Translate real-repository Git queries into membership/content dependencies, or refuse that target when such queries cannot be represented. This repairs the mechanism’s classification without changing the owner’s choice of recorder.

5. **F5 — HIGH — §2 staged-path normalization; `stage_tree`, `scripts/check-plan-code.py:917`: staged paths can conceal their repository provenance.**  
   `stage_tree` uses `shutil.copytree` with its default symlink dereferencing. Reproduced with:

   ```text
   docs/alias -> value
   suite reads staged docs/alias
   PR modifies only docs/value
   ```

   The staged alias is a regular file. Re-staging after the PR changes its contents, although its recorded path is `docs/alias` and the Git diff names `docs/value`. Resolving symlinks *inside the staged tree* cannot recover the source relationship because staging already erased it.

   **Proposed fix:** Record staging provenance and expand dependencies to their source paths and symlink components, or refuse affected targets. Add this case alongside the normalizer fixtures; changing staging semantics would require its own compatibility check.

6. **F6 — HIGH — §2 normalizer: copying cwd at `clone` is incorrect for shared filesystem state.**  
   The specified model gives a child its parent’s cwd at creation and updates each process separately. With `CLONE_FS`, a child/thread’s `chdir` changes the parent’s cwd too. A later parent-relative open can consequently be assigned to the wrong, perfectly resolvable staged path. The trace passes the “every path resolved” condition while recording the wrong dependency. [Linux documents this shared cwd behavior.](https://man7.org/linux/man-pages/man2/clone.2.html)

   **Proposed fix:** Model filesystem-context sharing and separation, including `clone3`, or refuse traces using unsupported sharing/namespace operations. Test a thread changing cwd followed by another thread’s relative open, including a failed probe.

7. **F7 — HIGH — §8.1 and §8.6: the shadow evaluator can lose pending comparisons and overlook earlier misses.**  
   Evaluation scans PRs “merged since the last” scheduled evaluation. If a comparison is PENDING at that evaluation, the following evaluation’s time window excludes the PR unless an unspecified persistent pending queue retains it. The spec therefore does not define how every pending comparison eventually receives a verdict.

   Separately, §8.1 defines a miss at **any push**, while §8.6 counts completeness using the **final push**. An earlier push can expose a false skip, then be amended so the final push compares cleanly. A final-push-only evaluator would permit switching despite §8.1’s stopping condition.

   **Proposed fix:** Require a persistent evaluation ledger owned by the scheduled comparator. Retain pending comparisons until resolved; evaluate every push required by §8.1; latch any miss. Count a PR toward twenty only after its required comparisons are complete and clean.

**Could not check:** The feature is unbuilt. This host is Darwin without `strace`, so I could not exercise Linux trace parsing, ptrace availability, runner-specific syscall variants, CI cache restoration, or shadow artifacts. The spike’s raw scripts/data were unavailable. The reproductions establish constructed mechanism failures, not failures in named existing guards. I changed no repository files, took no GitHub actions, and did not read `.claude/plans/`.

NOT CONVERGED
