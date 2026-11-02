<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `88f18c6d` against `origin/master`, both r1 reviews, the coordinator fold, and PR #407’s current body. No repository files changed; probes used a temporary directory and disposable Ubuntu 26.04 containers.

1. **P2 — Fold-induced: cache preparation can still prevent the required install.** `.github/workflows/ci.yml:295–298`  
   The new save-copy loop executes inside the required install step, before dpkg. Under Bash’s `-e`, a failed `mkdir` or `cp` aborts that step. The save action’s `continue-on-error` cannot protect this earlier code.

   **Executed:** restored a forged manifest-named file with mode `0444`, then ran the extracted save loop as an unprivileged user with a readable genuine archive available. `cp` reported `Permission denied`, the script exited 1, and the marker representing the subsequent install was never reached. Hash rejection leaves that restored file in place, so successful redownload does not repair this failure.

   This refutes the folded availability guarantee. Prepare the save directory separately and make every preparation failure nonfatal to installation.

2. **P3 — Fold incomplete: the saved directory can still contain unlisted files.** `.github/workflows/ci.yml:293–298`  
   The loop copies only manifest entries but never removes existing extras from `~/ffmpeg-debs`; the save action uploads that whole directory.

   **Executed:** an injected `extra.deb` was ignored during verification but remained after save preparation. Thus “saves only manifest files” in the workflow, PR body, and dashboard is false whenever save follows a partial restore containing extras. Build a fresh staging directory containing only current manifest entries.

Other confirmation results:

- Real `--print-uris -o Acquire::ForceHash=SHA256` output parsed correctly. Filename punctuation (`:`, `+`, `~`) survived. A missing-SHA256 entry produced unequal listed/kept counts and disables caching.
- The same-size forgery was rejected, a missing file was downloaded, and an unlisted file never entered apt’s archive directory. Genuine packages subsequently installed successfully.
- `updated=yes` survives print-uris failure as intended: the install can reuse the successful update while running uncached.
- All three cache steps have `continue-on-error` and three-minute limits.
- The stated arithmetic is correct: 28.3 and approximately 26.0 minutes. It is not a strict worst-case bound: verification and save preparation consume additional time, and the remaining-job allowance is measured.
- The PR body and dashboard are therefore **not fully true yet**. No signed-index hash bypass was demonstrated, but the fold introduced an install-blocking cache-preparation path.

VERDICT: NOT CONVERGED
