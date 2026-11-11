<!-- codex-review: model=gpt-6.1-sol -->

1. **F1 — HIGH — §2 Use 3(b): deleting the last descendant changes a higher directory’s listing without selecting its reader.**

   Reproduced in a temporary Git repository:

   ```text
   R:    docs contains keep and sub/only
         suite lists docs, sees sub, does not read computed path F
   BASE: deletes docs/sub/only; docs/sub disappears
   HEAD: modifies F, which the suite reads when sub is absent
   Δ:    D docs/sub/only; M F
   ```

   The deepest ancestor of the deleted path existing at R is `docs/sub`. The suite listed only `docs`, so 3(b) misses; F was neither read nor probed at R. Unioning the two diffs preserves the deletion but does not make it match. Today’s directory quotation selects this suite.

   The command reproduction confirmed that Git reports only `D docs/sub/only` while the `docs` listing changes from `keep, sub` to `keep`.

   **Proposed fix:** Include directory entries that disappear between endpoint trees. Match each removed directory against listings of its parent, including cascading removal of empty ancestors. Add this lagged history to §8.3.

2. **F2 — HIGH — §2 recorder command: the specified filter never sees two mandatory refusal triggers.**

   The command traces `%file,%process,getdents64,fchdir,io_uring_setup`, but `unshare` and `setns` are not members of those classes. Strace’s x86-64 syscall table marks `unshare` with class `0` and `setns` with `TD`, rather than `TF` or `TP`. Therefore neither reaches the parser, and the promised on-sight refusal cannot fire. [Strace syscall table](https://github.com/strace/strace/blob/master/src/linux/x86_64/syscallent.h).

   In particular, an unseen `unshare(CLONE_FS)` invalidates the new shared-cwd model while leaving the trace apparently complete.

   **Proposed fix:** Explicitly include `unshare,setns` in the filter. Verify every refusal trigger against the pinned strace version’s actual classes, using executed calls rather than synthetic parser lines.

3. **F3 — HIGH — §2 path normalisation: folding `..` before following links resolves the wrong dependency.**

   Reproduced outside the repository:

   ```text
   outside/link -> staged/docs/nested
   probe: outside/link/../flag

   specified lexical-first result: outside/flag
   actual resolved path:           staged/docs/flag
   ```

   Creating `staged/docs/flag` changed that probe from absent to present. Lexical folding removes the link component before the link table can inspect it, so the recorder can silently drop the probe as external. Linux resolves pathname components and follows the link before processing the subsequent component. [Linux pathname resolution](https://man7.org/linux/man-pages/man7/path_resolution.7.html).

   **Proposed fix:** Resolve components in kernel order, preserving link traversal before `..`. Refuse paths whose resolution cannot be established. Add failed probes and path-only calls using `link/../name` to §8.4.

4. **F4 — HIGH — §2 staging provenance: directory listings do not inherit provenance.**

   The map expands a **read or probe**, but the spec does not expand `listed`:

   ```text
   repo:   docs/alias -> real/
   suite:  lists staged/docs/alias, without opening its entries
   PR:     adds docs/real/new
   ```

   Staging dereferences the directory link. The recorded listing is `docs/alias`; the addition’s deepest existing ancestor is `docs/real`. Recording the directory open as reads/probes of both directory paths does not help: neither directory path appears in Git’s file diff. Rule 3(b) misses the changed listing.

   This also permits a stale recording to miss an intervening master addition that activates another dependency.

   **Proposed fix:** Translate `listed` through directory provenance as well as reads/probes, preserving the dependency on the link itself. Test additions and deletions beneath a dereferenced directory link.

5. **F5 — HIGH — §2 cross-run refusal: directory-mediated flows remain complete.**

   The intersection checks only `reads` and `probed`, excluding `listed`:

   ```text
   U: reads F; writes docs/generated/flag in an existing directory
   T: lists docs/generated; conditionally reads G when flag is present
   ```

   T’s isolated recording sees no flag and never reads G. Its directory open records `docs/generated`, while U’s write records `docs/generated/flag`; those paths do not intersect. In the shared shard tree, U creates the flag before T runs. Changing F or G can change T’s behavior while T’s recording remains complete.

   **Proposed fix:** Treat namespace changes to entries of listed directories as cross-run flows. Keep whole-trace listings for this check, including outside staged roots, and account for creation, deletion and both sides of renames.

6. **F6 — HIGH — §2 `wrote` extraction: traced mutations are classified only as probes.**

   The specified write cases omit `truncate(path, ...)`, `chmod`, timestamp changes and other metadata mutations. For example, U can read F and use `truncate` to change an existing shared file’s size; T can then branch on that file’s size. `truncate` is traced through `%file`, but the extraction rules record its path only as `probed`, leaving U’s `wrote` empty for that operation. The promised cross-run refusal does not fire. Strace’s table explicitly classifies pathname `truncate` as `TF`. [Strace syscall definitions](https://github.com/strace/strace/blob/master/src/linux/64/syscallent.h).

   **Proposed fix:** Define write extraction for every supported filesystem mutation, including metadata changes. Include or refuse descriptor-only mutation paths where a writable open does not establish the dependency.

7. **F7 — MEDIUM — §2 shadow replay: current PR and push sweeps have no reproducible seed to replay.**

   The comparator promises three reruns “under the seed each side used.” However, `.github/workflows/ci.yml:1298–1317` supplies explicit seeds only for scheduled sweeps. PR and master-push sweeps leave them unset; `mutation_env(..., seed=None)` preserves that behavior (`scripts/check-plan-code.py:256–267`).

   A verdict record containing `seed: null` cannot recover Python’s original random hash secret. Three reruns therefore sample fresh orders, rather than reproducing either original execution. The flake filter can reject a real difference or report a difference caused by different hash orders across the two trees.

   **Proposed fix:** Give shadow-comparison executions explicit, recorded comparison seeds and replay each seed on both trees. Treat historical unseeded differences as inconclusive.

Could not check: the feature is unbuilt, and this Darwin host has no `strace`. I could not execute Linux tracing, CI cache validation, artifact retention, or the comparator. I did not remeasure the spike or runner costs. Counterexamples are constructed mechanism failures, not demonstrated failures of named existing guards. No repository files or GitHub state were changed; `.claude/plans/` was not read.

NOT CONVERGED
