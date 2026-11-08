<!-- codex-review: model=gpt-6.1-sol -->

Both self-tests passed: regen **85/85**, explainer **238/238**. All **14 new mutations**, plus three retargeted mutations, failed their named cases. Attacks ran only in scratch clones; the worktree is unchanged.

### R2-F1 — Blocking — Cleanup follows a swapped ancestor into unrelated data

**File:line:** `scripts/regen-pages.py:259`

**Scenario:** `rmtree` protects against symlinks inside its target, but the pathname’s ancestors remain redirectable.

**Repro:** After `own_entries` returns, rename `<common>/worktrees` and replace it with a symlink to an external scratch directory containing a same-named directory with an `UNCOMMITTED` file. `discard()` deletes that external directory without reporting an error. Reproduced with the real admin entry.

**Fix:** Anchor deletion to previously opened directory descriptors, retain directory identities, and refuse changed identities. Apply equivalent protection to the private directory’s parent.

### R2-F2 — High — Matching mutable `gitdir` text deletes another worktree’s admin entry

**File:line:** `scripts/regen-pages.py:245`

**Scenario:** Cleanup treats every matching entry as owned, although another entry’s text can be edited.

**Repro:** Create a live victim worktree and this run’s tree. Rewrite the victim admin entry’s `gitdir` to `<private>/tree/.git`, then call `discard()`. The victim admin directory disappears; `git status` in the victim fails with “not a git repository.”

**Fix:** Record the specific admin directory created by this add, including its identity. Delete only that entry after revalidation; never infer ownership by scanning mutable text during cleanup.

Ordinary basename collisions were safe: Git allocated `tree1` and `tree2`. Symlinks inside the private directory also survived as external targets. Neither protection prevents the attacks above.

### R2-F3 — High — An escaped descendant can outlive cleanup and the lock

**File:line:** `scripts/regen-pages.py:437`

**Scenario:** The inherited descriptor protects descendants only while they retain it. A conventional subprocess exec closes it by default.

**Repro:** A generator double-forks, calls `setsid`, and starts a Python subprocess using default `Popen(close_fds=True)`, with standard streams redirected. The generator exits. `launch()` returns `(0, '')`; another lock acquisition succeeds while the escaped descendant remains alive. It subsequently writes its delayed marker.

The claimed `SURVIVED` warning is absent because `gone` measures only the original process group.

**Fix:** Use descendant containment or explicit descendant tracking that covers session changes, and wait before cleanup. Descriptor inheritance alone cannot establish the stated guarantee across arbitrary execs.

### R2-F4 — High — Refresh timeout can wait indefinitely for escaped pipe holders

**File:line:** `scripts/explainer-serve.py:162`

**Scenario:** After SIGKILL, the final unbounded `communicate()` waits for EOF from descendants outside the killed group.

**Repro:** Run a child that forks; the descendant calls `setsid` and retains stdout/stderr. With timeout `0.2` and grace `0.1`, master’s `subprocess.run` raises after **0.21 seconds**; `run_in_group` raises after **3.08 seconds**, when the descendant exits. An indefinitely sleeping descendant makes this wait indefinite.

**Fix:** Bound pipe draining after termination, close the streams when that bound expires, and reap the direct child without requiring descendant EOF.

### R2-F5 — Medium — Publishing failure suppresses edited-file validation warnings

**File:line:** `.claude/hooks/regen-backlog-page.sh:123`

**Scenario:** Validation reads the edited checkout correctly, but its successful-run warnings are relayed only after publishing succeeds.

**Repro:** In a scratch clone, make the validation generator emit an `⚠ UNREAD` warning and return zero; make the publisher return `CANNOT RUN offline`, exit 2. The hook prints only the publishing failure. The edited-row warning disappears.

**Fix:** Relay `$VAL` warnings immediately after validation, before any publishing failure can exit.

The new success message correctly identifies origin/master, but the warning channel remains conditional on an unrelated network/build result.

### R2-F6 — Medium — SIGKILL escalation has an uncovered surviving mutation

**File:line:** `scripts/regen-pages.py:416`

**Scenario:** The suites exercise children that accept SIGTERM, leaving escalation untested.

**Repro:** Replace `(signal.SIGTERM, signal.SIGKILL)` with `(signal.SIGTERM, signal.SIGTERM)` in a scratch clone. The suite still passes **85/85**. No manifest mutation covers this escalation, and no exemption explains it.

**Fix:** Add a real child that ignores SIGTERM, assert it is gone before cleanup, and register the escalation mutation against that case.

## Loosening answers
LOOSENING-CHECK fb89f268396d: finding: Refresh timeout cleanup can wait indefinitely for an escaped descendant holding its pipes; master returned the timeout without waiting for that EOF
LOOSENING-CHECK 712c0aacc4cf: finding: Refresh timeout cleanup can wait indefinitely for an escaped descendant holding its pipes; master returned the timeout without waiting for that EOF
LOOSENING-CHECK 4fbb22a7ffb6: not a loosening
LOOSENING-CHECK d3cc57ddef63: not a loosening
LOOSENING-CHECK 606dad727ce8: not a loosening
LOOSENING-CHECK 935e69a64e55: not a loosening
LOOSENING-CHECK 705455503855: not a loosening
LOOSENING-CHECK 0ca3caeb1539: not a loosening
LOOSENING-CHECK 06eb9b4d1609: not a loosening
LOOSENING-CHECK 68a9fd0367a4: not a loosening
LOOSENING-CHECK e29b3fb8fa9a: not a loosening
LOOSENING-CHECK ef8c9de45337: not a loosening
LOOSENING-CHECK b25e1072da48: not a loosening
LOOSENING-CHECK 0670c030fae3: not a loosening
LOOSENING-CHECK 51049a3f8433: not a loosening
LOOSENING-CHECK 75ec8edc4012: not a loosening
LOOSENING-CHECK 27004bcf2f0b: not a loosening
LOOSENING-CHECK 4a9e19b085f0: not a loosening
LOOSENING-CHECK 647fd36ca84a: not a loosening
LOOSENING-CHECK 1004179b2d29: not a loosening
LOOSENING-CHECK afddc8ea43c6: not a loosening
LOOSENING-CHECK 302dad7bb9d4: not a loosening
LOOSENING-CHECK e2fc910cf7f5: not a loosening
LOOSENING-CHECK 62376f70e7a2: not a loosening
LOOSENING-CHECK 0b55d8682aec: not a loosening
LOOSENING-CHECK e74a4c7a0c52: not a loosening
VERDICT: NOT CONVERGED
