<!-- codex-review: model=gpt-6.1-sol -->

**F1 — HIGH — Parse-time link resolution can lose a probe while retaining `complete`.**

Evidence: §2 normalisation, lines 202–210. The new pre-existing-link refusal checks `realpath` only after execution.

Construction: a pre-existing external `L -> /tmp` lets guard T stat `L/<copy>/docs/value`. T then unlinks L during cleanup. At parse time, the longest-existing-prefix algorithm leaves the probe lexically outside the copy, so it neither records `docs/value` nor refuses T. No runtime `symlink*` or in-copy rename occurred.

Let T’s normal predicate be `size >= 1`, with a mutant `size == 1`. A PR modifies `docs/value` from one byte to two. Both controls pass; the mutant changes from survived to killed, using the **same stat path** as its control. With another target naming that file to avoid FULL, T has no rule-3 selection reason.

I reproduced the resolution failure with `python3 -B` in a temporary directory outside the repository: the original stat succeeded, but after unlinking L the folded algorithm returned `inside copy: False`.

Proposed fix: refuse path-only/failed-path traces when an external namespace component was removed or replaced during the trace and its original resolution cannot be established. Include `unlink*`, not only link creation and rename.

**Caused by round-3 fold: Yes**, by replacing unresolved-link handling with a parse-time-only test.

**F2 — HIGH — Classifying every `ioctl` as read-only defeats the cross-run refusal.**

Evidence: §2 lines 144–158 explicitly classify `ioctl` as read-only, while requiring metadata changes to count as writes. Linux provides modifying ioctls such as `FS_IOC_SETFLAGS`; its implementation changes inode attributes without requiring an `O_RDWR` open. See the [kernel implementation](https://code.googlesource.com/linux/torvalds/linux/+/78273df7f646f8daf2604ec714bea0897cd03aae/fs/ioctl.c).

Construction on a supporting filesystem:

- U’s **control** reads tracked file F, opens an existing carrier K read-only, and sets K’s `FS_NODUMP_FL` according to F using `FS_IOC_SETFLAGS`.
- T’s control and mutant both read K’s flags using `FS_IOC_GETFLAGS`. Its normal predicate accepts either flag value; its mutant accepts only the unset value.
- The PR modifies F, selecting U. T’s trace records K but not F. U’s modifying ioctl contributes nothing to `wrote`, so T remains `complete` and is skipped, although its mutant’s verdict changes.

This is a flow from another target’s **control**, which §2 and §4.3 promise to refuse. It requires neither a mutant-only file dependency nor another mutant’s leftovers.

Proposed fix: classify ioctls by request with a closed read-only allowlist; treat other requests as writes or INCOMPLETE.

**Caused by round-3 fold: Yes**, by explicitly exempting all `ioctl` calls from the write class.

I could not run Linux `strace`, verify its descriptor decorations/interleaving, or execute the ioctl construction on this Darwin host. The implementation and CI measurements remain unbuilt, so I could not verify end-to-end selection or replay behavior. Beyond these holes, I found no independently substantiated buildability gap in the twelve answers. No repository files were written or GitHub actions taken.

NOT CONVERGED
