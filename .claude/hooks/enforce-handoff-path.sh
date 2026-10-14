#!/usr/bin/env bash
# PreToolUse hook on Skill — stop /handoff writing to a path nothing reads.
#
# WHY THIS FILE EXISTS (measured 2026-08-27).
#   The handoff skill upstream saves to `mktemp -t handoff-XXXXXX.md`. THREE such files accumulated
#   in $TMPDIR and NOT ONE was ever read by a resuming session — random suffix, outside the repo,
#   unindexed. A produced artifact with no consumer, which is this repo's recurring "live gate with
#   NO CALLER" wearing different clothes.
#
#   The repair points the skill at .remember/remember.md, which the remember plugin's SessionStart
#   hook already injects as `=== LAST HANDOFF ===` ahead of identity and memory.
#
#   ⚠ THAT REPAIR LIVES IN A VENDORED FILE that `npx skills@latest add mattpocock/skills` overwrites.
#   The first guard written for it was a SENTENCE in docs/plugins.md — "if a resume ever finds a
#   handoff-XXXXXX.md in $TMPDIR, the skill was overwritten". That fires only AFTER a session has
#   already lost its handoff. This hook is the leading half: it fires at invocation.
#
# WHAT IT BLOCKS: invoking the handoff skill while the vendored SKILL.md no longer names
# .remember/remember.md.
#
# WHAT IT DELIBERATELY ALLOWS: every other skill, untouched (exit 0 fast). And when the skill is
# intact this is silent — a hook that talks on the happy path gets ignored on the unhappy one.
#
# ⚠ LIMIT, STATED RATHER THAN HIDDEN: this guards the INSTRUCTION, not the outcome. It cannot
# observe where the file actually lands. If the skill names the right path and the agent writes
# elsewhere anyway, only the next resume finds out — that is what the docs/plugins.md falsifier
# still covers. Two layers, different failure modes.

INPUT=$(cat)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

IS_HANDOFF=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("no"); sys.exit()
ti = d.get("tool_input", {}) or {}
skill = str(ti.get("skill", "")).lower()
# Plugin-qualified names arrive as "vendor:handoff"; match the bare segment.
print("yes" if d.get("tool_name") == "Skill" and skill.split(":")[-1] == "handoff" else "no")
' 2>/dev/null) || IS_HANDOFF="no"

[[ "$IS_HANDOFF" == "yes" ]] || exit 0

VERDICT_OUT=$(python3 "$REPO_ROOT/scripts/check-handoff-path.py" --quiet 2>&1)
VERDICT_RC=$?

[[ $VERDICT_RC -eq 0 ]] && exit 0

cat >&2 <<EOF

╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — the handoff skill would write where nothing reads          ║
╚══════════════════════════════════════════════════════════════════════════╝

$VERDICT_OUT

MEASURED: three handoff docs were written to \$TMPDIR and none was ever read.
The documents were fine. They had no consumer.

Write the handoff to:  .remember/remember.md

That is REMEMBER_HANDOFF in the remember plugin's session-start-hook.sh —
emitted as '=== LAST HANDOFF ===' and injected BEFORE identity and memory so it
survives context-preview truncation. Delivery is fingerprinted on the handoff's
CONTENT, so reading one does not consume it.
  To inventory this repo's TRACKED files:  git grep -l session-start-hook
  (no flag needed -- it searches tracked files, so the symlinked skill file is found)
  r4 H1: ONE COMMAND IS NOT ENOUGH. git grep searches the paths in the INDEX,
  reading each from the working tree UNLESS it is marked skip-worktree or
  assume-unchanged or is gone from disk -- then it reads the cached blob, or
  nothing. Measured: a TRACKED file marked assume-unchanged returns the stale
  indexed string and misses the one on disk. It also misses untracked, ignored,
  submodule, nested-checkout and vendored content.
  So CROSS-CHECK: git grep -l  vs  git grep --cached -l  vs  grep -rl .
  Any disagreement IS the signal.
  The assignment itself is REMEMBER_HANDOFF= -- keep the '=', it matches the two
  assignments where the bare name matches 23 lines. This locator is also a
  runnable discovery command (r4 L1: a literal <version> is a shell REDIRECT):
  ls ~/.claude/plugins/cache/claude-plugins-official/remember/*/scripts/session-start-hook.sh

NOT .remember/handoff.md — nothing reads that name either.

If a session-start block printed 'Write next handoff to: <path>', obey THAT path
-- it is always the right one. THREE things print it: the store directory is not
an immediate CHILD of the project directory -- which INCLUDES a linked git
worktree, and a data_dir nested two deep (measured: data_dir=a/b prints a hint,
data_dir=notes does NOT, because the hook compares the store's PARENT with the
project dir -- r4 H2 corrected this label twice); per_session
mode (.handoff_mode), where the path is remember.<session-id>.md; and a per_session
request with no usable session id, where it prints the SHARED file in whatever
store is resolved -- which is NOT always the path above: a data_dir setting moves
it -- plus a line saying the mode you asked for did not apply.

Then repair the vendored skill so this stops recurring:
  \$EDITOR .agents/skills/handoff/SKILL.md      # see docs/plugins.md -> Session Handoff
  python3 scripts/check-handoff-path.py         # must exit 0
EOF
exit 2
