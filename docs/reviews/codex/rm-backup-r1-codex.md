<!-- codex-review: model=gpt-6.1-terra -->

## Findings

**R1-1 — BLOCKER: Escaped whitespace makes the comment scanner hide an executable `rm`.**  
In a temporary directory containing `victim`, I imported the hook by path and passed this command to `plan`, then ran it with Bash:

```bash
echo foo\ #; rm victim
```

Observed: `plan = []`, Bash exited 0, and `victim` no longer existed. The escaped space is part of the preceding word, so Bash treats `#` as part of that word; the scanner treats it as the start of a comment and discards the `rm`.

Proposed fix: track shell word boundaries through escapes, and add this command as a regression case.

**R1-2 — BLOCKER: An unquoted heredoc can execute a deletion that the hook removes from its input.**

```bash
cat <<EOF
$(rm victim)
EOF
```

Observed in a temporary directory: `plan = []`, Bash exited 0, and `victim` no longer existed. Bash performs command substitution in an unquoted heredoc body. The hook discards the body before looking for commands.

Proposed fix: account for shell expansions in unquoted heredocs, or refuse calls containing expansions the hook cannot safely inspect.

**R1-3 — BLOCKER: The `mktemp` exemption follows symlinks outside the fresh directory.**

```bash
T=$(mktemp -d); ln -s /path/to/victim-directory "$T/out"; rm "$T/out/victim"
```

Observed with the link pointing to the temporary experiment directory: `plan = []`, Bash exited 0, and the outside `victim` no longer existed. The hook treats every descendant of the fresh directory as exempt without resolving intermediate symlinks.

Proposed fix: do not exempt unresolved descendants of a fresh directory when earlier commands can populate it; refuse them or resolve and verify their actual targets.

**R1-4 — MAJOR: A symlink outside the backup root is exempt when its referent is inside it.**

```bash
ln -s /path/to/backups/inside link
rm link
```

Observed: `plan("rm link") = []`. The object `rm` deletes is the outside symlink, but `_inside` resolves it to its referent and exempts it. No copy of the link is made.

Proposed fix: check containment of the directory entry being deleted without following its final symlink, while still resolving intermediate path components.

**R1-5 — MAJOR: Pruning follows a session-directory symlink and deletes outside the backup root.**

In a temporary directory, I created `root/session` as a symlink to `outside`, with `outside/20200101-000000` beneath it, then called:

```python
prune(root, datetime.datetime(2026, 11, 20))
```

Observed: `outside/20200101-000000` no longer existed. The first glob follows the session symlink and `rmtree` removes the old directory through it.

Proposed fix: reject symlinked session directories and verify each deletion target remains physically inside the backup root.

**R1-6 — MAJOR: Wrapper options with arguments hide an executable `rm`.**

```bash
sudo -u root rm victim
```

Observed: `plan = []`. In the experiment Bash reached `sudo`, which exited 1 because it required a password; where that sudo invocation is permitted, it executes the unseen `rm`. The parser skips `-u` but treats its argument, `root`, as the command name.

Proposed fix: parse supported wrapper options and their arguments, or refuse wrapper forms whose command position cannot be established.

**R1-7 — MINOR: The failed-copy self-test can pass without testing a refusal.**

The suite reports `64/64 self-test cases passed`. Its failed-copy case compares whether a refusal occurred to `os.geteuid() != 0`. When run as root, a successful copy and no refusal satisfy the case, so the named case does not establish that a failed copy is refused.

Proposed fix: inject a deterministic copy failure and assert the refusal independently of the test runner’s privileges.

## Verdict

NOT CONVERGED. The reproductions show executable deletions that receive no backup, and pruning can delete outside the backup root.

## Loosening answers
LOOSENING-CHECK 90d77bf9cc7d: not a loosening

VERDICT: NOT CONVERGED
