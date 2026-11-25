Reviewed head: c89ce07fa7068f466d06f9faf8aaa7e26070dade

# Backlog #688 X2: adversarial review, round 1 (Claude half)

Subject: branch `usage-hook-r4-findings` (PR #634), diff against `origin/master`. Files: `.claude/hooks/run-hook.sh`,
`scripts/check-run-hook.py`, `docs/backlog.md` row 688, `docs/dashboard-entries.md`.

## What I ran (evidence)

| Check | Result |
|---|---|
| `python3 scripts/check-run-hook.py --self-test` at c89ce07f | **172/172 passed**, rc 0, 1m28s. x2a, x2b, x2c and x2d each print `is killed`. |
| CONTROL: the branch's `check-run-hook.py` run (plain mode) over **origin/master's** `run-hook.sh`, in a scratch copy | rc 1. Exactly three rows go red: OUT_USAGE, GONE_USAGE and OUT_PROMPT, each `got (1, None, True, '')`. OUT_PLAIN and GONE_PLAIN stay green, which is correct because master already exits 1 there. So the new cases fail against the defect they name, and they do not pass for an ambient reason. |
| Anchor resolve over every `scripts/mutations/*.json` edit (each `edits[i][0]` counted in its `file`) | 0 anchors that do not occur exactly once. Moving `usage_not_run` unbound nothing. |
| X1 alternative, in a scratch git world: worktree `wt` of `main` with `.git` rewritten to `gitdir: <other>/.git`, plus a healthy worktree `wt2` | git reports `common = other/.git` and `toplevel = wt`. `git -C other worktree list --porcelain` lists only `other`, without `wt`. `git -C main worktree list` lists `main`, `wt` and `wt2`. |

## Refutation attempts that did not land

- **Any other silent pre-root exit for a usage hook.** The launcher has four more exits before a root exists: `[ $# -eq 1 ]`
  and the three name refusals (`run-hook.sh` lines 49–54, exit 2). The registered command always passes exactly one fixed
  name, so none of them is reachable for a `usage-pace-*` hook. The other silent case is bash's own 127: with
  `CLAUDE_PROJECT_DIR` unset and a cwd that is not an exported root, the launcher file is never found. No launcher can
  answer that, and it is stated already (W14, `scripts/check-run-hook.py:641`, and row 688's "reachable only from an
  exported tree's root"). After the root, every usage exit already went through `usage_not_run`: the git failure, the
  answer shape, bare, no owner, and the missing hook file. A missing `perl` makes `git_clean` fail, so it is a git failure
  and also NOT RUN.
- **Collateral change to other hooks.** For a non-usage name, both new `case` lines match nothing, so control reaches
  the unchanged `echo …; exit 1`. Moving the function definition only changes where it sits; it is not called on any
  non-usage path. x2c and x2d (every hook speaks usage JSON) are killed by OUT_PLAIN and GONE_PLAIN, which assert
  rc 1 and an EMPTY stdout. The control run shows these two rows hold on master too.
- **Can each case fail?** Yes. The control above, plus x2a–x2d killed in the self-test. A `usage_not_run` defined after
  the walk again would hit "command not found" and fall through to exit 1, the same observable as x2a and x2b, so it is
  killed too.
- **The export world could pass by falling back to the cwd.** It cannot: the world plants probe copies of every usage
  hook in the exported tree, and the cases assert NOT_RAN.

## Findings

### MINOR 1: X1's written reason generalises from one prototype

`docs/dashboard-entries.md:21629` says that fixing X1 "would also stop the guard running inside submodules, which
reverses a design decision of 2026-11-20". Row 688 likewise rests the "design decision, not a fold" claim on a single
prototype: refuse a common dir unlike `CLAUDE_PROJECT_DIR`'s. A narrower pin exists that does not touch submodules, and
git still names it: require the session's `--show-toplevel` to appear in `git -C "$main" worktree list --porcelain`. In
the scratch world it refuses X1, because `wt` is absent from `other`'s list, and it admits a healthy worktree. A
submodule session (U3) has `top == main`, and so does a separate-git-dir checkout, and in both cases `top` is the list's
first entry. I did not run it over the suite, so it is a lead, not a measured fix. **X1 staying FILED is still right.**
The trigger argument stands on its own: the `.git` file is untracked, and anyone who can rewrite it can rewrite main's
hook directly.
**Fix:** reword the dashboard sentence and row 688 to "the one pin tried (to `CLAUDE_PROJECT_DIR`'s common dir) made 12
cases red". Then add the worktree-list membership check to row 688's **Fix** as the candidate to measure first if the
trigger appears.

### MINOR 2: no unreadable-cwd case for the prompt hook

The no-checkout exit has both channels (OUT_USAGE as a systemMessage, OUT_PROMPT as additionalContext). The
unreadable-cwd exit has only GONE_USAGE (`scripts/check-run-hook.py:624`). The dispatch is shared inside
`usage_not_run`, so nothing is uncovered today. Still, a refactor that inlines a systemMessage-only line at
`run-hook.sh:67` stays green.
**Fix:** add a `GONE_PROMPT` case (`args=["usage-pace-prompt.sh"]`, `want_out=PROMPT_JSON`, `vanish=True`) and list it
in x2b's kill set.

### MINOR 3: the "X2" label now names two different findings in one file

The new rows are named `X2 #688 …` (`scripts/check-run-hook.py:738–745`), and mutants `x2a`–`x2d`. The existing
backlog #513 r1 rows are named `X2 a worktree … newline` (`:756`, and the manifest's "X2's commondir holds no
newline"). A red line reading "X2" no longer says which finding failed.
**Fix:** prefix the new rows `688-X2` (and the mutants `688x2a…`), or rename them to say what they test (for example
`NOROOT`/`NOCWD`).

Note, not a finding: the fixed JSON text says "could not locate this hook in the main checkout (… the copy in a worktree
is not trusted …)", which fits the deleted-cwd and exported-tree exits loosely. It is a FIXED string shared with
`usage-pace-run.sh`'s `cannot` contract, and the detail is on stderr. Changing it is out of scope for this row.

No BLOCKER or MAJOR. X2 is fixed as described, each new case goes red against the defect it names, and no other hook's
behaviour changed.

VERDICT: CONVERGED
