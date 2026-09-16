<!-- codex-review: model=gpt-5.5 -->

> **Coordinator note — WHICH TREE THIS SAW.** Codex reviewed `HEAD = 71378cd3` **plus the
> uncommitted round-2 fixes**, which is deliberate: `review-method.md` step 5 says holding the last
> round's fixes uncommitted is how a reviewer gets to see the tree that will actually merge. The
> wrapper recorded a git tree entry for all 9 dirty files in
> `docs/reviews/verdicts/peer-sites-r3-codex.verdict.json`, so exactly what it read is on record
> rather than asserted. Everything after this block is verbatim.

---

**Findings**

**High** — timeout regressions survive mutation in the commit-time path.

Measured against the current working tree with uncommitted round-2 fixes.

`scripts/peer-sites.py:352`, `scripts/peer-sites.py:385`, `scripts/peer-sites.py:464`, and `scripts/peer-sites-hook.py:116` all carry `timeout=30`, but removing `, timeout=30` from the scratch-copy subjects leaves the suites green:

```text
peer-sites.py with all timeout=30 removed: 67/67 passed
peer-sites-hook.py with timeout=30 removed: 38/38 passed
```

The full sweep also stayed green because neither `scripts/mutations/peer-sites.json` nor `scripts/mutations/peer-sites-hook.json` contains a timeout mutation. This means r2 R4’s exact regression class is fixed in the delivered code but not ratcheted; the unbounded subprocess can come back under `718 killed, 0 survivors`.

Siblings searched: yes. I enumerated `subprocess.run` by AST in `scripts/peer-sites.py` and `scripts/peer-sites-hook.py`; found exactly four call sites, all currently bounded. I grepped both peer-sites mutation manifests for `timeout`; found none.

**Medium** — the bash pre-filter still charges non-commit commands that merely contain `commit`.

Measured against the current working tree with uncommitted round-2 fixes.

`.claude/hooks/peer-sites-advisory.sh:25-28`:

```bash
case "$payload" in
  *commit*) ;;
  *) exit 0 ;;
esac
```

The Python rule later rejects `echo commit`, but the bash shim has already spawned Python. Median over 8 live hook runs:

```text
ls -la                 12.7 ms, no output
echo commit           120.8 ms, no output
git log --grep commit 461.9 ms, advisory printed
```

So the cost is not only “a nudge”: some non-git/non-commit commands pay the Python startup and repo lookup cost with no user-visible reason. `git log --grep commit` also reaches the full advisory path, matching the deliberately loose `wants_check` behavior.

Siblings searched: yes. I grepped `.claude/hooks` and `scripts` for PreToolUse command parsing and whole-payload substring filters. This `*commit*` pre-filter is the only whole-payload substring stage I found; other hooks parse a specific payload field or delegate directly.

**Verification**

`python3 scripts/check-plan-code.py --mutate .` completed:

```text
OK — delivered scripts mutated: 48 file(s), 718 mutation(s), 718 killed, 718 attributed to the case each names, 0 survivor(s)
```

Live-fire ran:

```text
echo '{"tool_input":{"command":"git commit -m x"}}' | bash .claude/hooks/peer-sites-advisory.sh
```

It exited 0 and printed a peer-sites advisory for the current uncommitted `scripts/peer-sites.py` change.

I also probed `parse_hunks` with real multi-file, rename, binary, CRLF, and `git show --cc` combined-diff output. I did not find a real-git-output break in the counted walk. A synthetic mixed normal-plus-combined malformed diff can still produce line `0`, but I did not prove that shape is emitted by git.

CONVERGED: No
