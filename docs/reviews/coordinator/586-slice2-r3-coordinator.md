# Round 3 — `586-slice2` — coordinator — Claude NOT CONVERGED on one Major; the Major is fixed, three Minors filed

REVIEW GAP: codex — alternation (round 3 runs ONE half; Codex ran in rounds 1 and 2).

Subject: PR #565 (DRAFT), branch `586-slice2`, reviewed head `36bb765e` (the round-2 fix). Half:
`docs/reviews/claude/586-slice2-r3-claude.md`: one Major (F1, fail-open) and three Minors (F2–F4, each a false refusal
or a stall), plus a spec note. Every round-1 reviewer input still gives the same result at this head (22 cases re-run).

```yaml
round: 3
fixes_nontrivial: true
subject: 586-slice2
halves:
  claude: ran
  codex: gap
findings:
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: strace-parser, disposition: fixed}
  - {id: F2, severity: Minor, aim: deliverable, fix_induced: true, component: strace-parser, disposition: filed}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: true, component: strace-parser, disposition: filed}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: false, component: strace-parser, disposition: filed}
```

`fix_induced`: F1 predates every fold, because the cwd model has tracked only `chdir`/`fchdir` since the build. F2 and F3
come from the round-2 pass bound. The bound itself is sound: it stops, and it never admits a path. These two are a false
refusal and a slow refusal, so they fail safe. They are not a second fix-induced fail-open, so THRASHING does not arm.

## F1: a rename moves the kernel's cwd and leaves the model's stale

The kernel's cwd is the directory, not its path, so renaming the cwd or any ancestor moves the cwd with it. The model kept
the old text and resolved later relative paths against a place that no longer existed. The reviewer ran six inputs,
covering access, execve, stat, readlink, a renamed ancestor and a forked child. All six returned a smaller read set with no
refusal.

**Fix, by the round-1 rule (refuse where the model is short of the kernel):** `_cwd_pass` records every cwd any context
ever had (`held`). A successful or unknown-outcome rename whose source is, or holds, a held cwd refuses the log with the
new reason `cwd renamed`. A normal suite does not rename its own cwd or anything above it, so the false-refusal cost is
small and safe.

## How the fix was proved

- The reviewer's `adv6.py` at the fixed head: all six F1 inputs now return `cwd renamed`, and the control still returns
  `cwd model disagrees`.
- Three new cases: the cwd renamed, a forked child's inherited cwd under a renamed parent, and a control (a rename beside
  the cwd is not refused for it). **138/138** pass. Both refusal cases fail at `36bb765e`, because the reason did not exist
  there.
- Two new mutations: the refusal disabled, and a `chdir` target not remembered. A third, "a snapshot cwd not remembered",
  SURVIVED. That was correct: a snapshot is a parent's cwd value, which is already held, so the line was redundant. The line
  and the mutation were both deleted, and the sweep now gives **85 killed, 85 attributed, 0 survivors**. Pin 83 → 85.
- `check-selftest-counts.py` rc=0.

## Filed, not fixed (round cap: r3 is the last full round)

Backlog #621 holds F2 (order-blind closure refuses a sequence the kernel finishes), F3 (the bound counts passes, not work:
27 s with 400 unrelated renames, and a 2× blow-up on branching real renames), F4 (unmatched bracket in a path label →
`log did not parse`) and the spec note (an exec'd script's interpreter opens with no syscall). None loses a path.

## Next

Round 4 would file every non-BLOCKER. The F1 fix follows the same refuse-don't-model rule as the round-1 fold and has its
own failing-first cases and killed mutations. PR #565 goes ready, then merges on `check-merge-ready` READY.
