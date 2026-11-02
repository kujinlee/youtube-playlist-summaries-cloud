---
name: no-command-approval-ceremony
description: "FIRES-WHEN: I am about to run a Bash call that will prompt the owner (dangerouslyDisableSandbox, a risky or complex command) or ask them to run or approve one — the owner, 2026-10-30: approving a complex bash command is ceremony, not a gate; design a dry-run or a recovery point instead"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-30T16:18:29.708Z
---

**Never make the owner approve or run a complex shell command as a safety step.** They said on 2026-10-30: *"do not ask me to run a bash command. instead, devise a dry-run or recovery means if the command actually make harmful side effects. asking me to check complex bash command is just a ceremony not a real gate."*

**Why:** nobody audits a 20-line command at a glance, so the approval proves nothing and spends their attention. On 10-30 I set `dangerouslyDisableSandbox: true` on most Bash calls out of habit, including local git commits and file edits that didn't need it. Each one can prompt.

**How to apply:**
- Set `dangerouslyDisableSandbox` only where the sandbox really blocks the call: a network push or `gh` call, or docker. Local git commits, edits and test runs go through the sandbox.
- Before anything with side effects, use a DRY-RUN where one exists: `git push --dry-run`, a diff or `--stat` preview, a `--self-test` on a copy.
- Before anything destructive, make a RECOVERY point: a backup ref before a rebase or reset (`git branch backup/<x>`), a `.bak` copy before editing the owner's config (as done for `statusline.sh`). Never write to master.
- The owner's own interactive commands (a login, `/clear`) are still theirs. That is not what this rule covers.

Related: [[defaults-i-decide-myself]], [[a-check-result-is-not-the-claim]].
