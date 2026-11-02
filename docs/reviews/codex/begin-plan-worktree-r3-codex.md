<!-- codex-review: model=gpt-6.1-sol -->

Confirmation review of `1ec48d8e`, mandate REFUTE: no finding refuted the SPLIT bet.

- Ordinary, symlinked `.git` directory/file, aliased `gitdir:`, relative CRLF, submodule-linked, and moved-main worktrees refused all eight commands before dispatch or state loading. Filesystem snapshots remained unchanged.
- `GIT_DIR` overrides in both directions caused neither bypass nor main-checkout refusal. The Git invocation scrubbed every `GIT_*` variable and used the required arguments and ROOT cwd.
- Ordinary main, separate-git-dir main under `worktrees/`, actual submodule, and staged copy without `.git` passed detection.
- The r1 legacy three-line output correctly triggered fallback, tested through an injected runner; Git 2.30 was not rebuilt.
- Suggested commands preserved spaced paths and pipe-containing arguments through shell parsing.
- `python3 scripts/begin-plan.py --self-test`: **139/139 passed**.

All experiments ran in `/tmp/bp-r3.wbmCj9`. No repository files were written or edited.

VERDICT: CONVERGED
