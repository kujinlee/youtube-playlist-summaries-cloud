#!/usr/bin/env bash
# The LEADING half of the memory-index budget gate — the lagging half is the
# "Memory index injection budget" step in `.github/workflows/ci.yml`.
#
# ⛔ WHY A HOOK EXISTS AT ALL, and it is not belt-and-braces. Measured 2026-10-19 (r1 CLAUDE N2)
# over two worktrees at the same HEAD: a working tree grown past the limit with NOTHING COMMITTED
# gives rc=1 OVER BUDGET, while a fresh checkout of that same HEAD — what CI sees — gives rc=0 ok.
# A session loads the WORKING TREE, so the overflow that actually degrades a session is invisible
# to CI by construction. That is backlog #309's class: the matcher reads the working file, so no
# git-shaped guard can see it. The guard was never blind; it simply had no caller here.
#
# ⛔ THE ROOT COMES FROM THE FILE THAT WAS EDITED, NOT FROM THIS SCRIPT'S LOCATION, AND THAT IS A
# CORRECTION OF MY OWN REGRESSION (r2 CLAUDE H3). The first version read
# `dirname "${BASH_SOURCE[0]}"`; I then "fixed" it by resolving symlinks, and MEASURED that made it
# worse: with this hook shared by symlink into a second checkout, it reported SILENT on a
# 25,000-character over-budget index, where the unresolved version had correctly fired OVER BUDGET.
# A loud wrong answer became a quiet one. ⚠ Neither location is the subject — the subject is the
# index the tool just wrote, so the repository is the one CONTAINING THAT FILE. This is also what
# makes it correct across git worktrees, whose indexes are different inodes.
#
# ⚠ ADVISORY, DELIBERATELY. It warns and always exits 0. A blocking hook on a docs-only threshold is
# what backlog #56 measured getting switched off, and the remedy (move history rows to the triggered
# `slice-history.md` entry) is a judgement about which rows are history — not something to force
# mid-edit. The CI step stays the one that fails.
#
# ⚠ WHAT IT CANNOT DO: it fires on writes THROUGH THE TOOL. An edit by any other route — another
# agent, an editor, a script — is unobserved, which is exactly how the backlog #309 instance arrived.
#
# ⛔ STRUCTURED JSON, NOT STDERR, AND THE PROVENANCE MATTERS MORE THAN MY OPINION.
# `.claude/hooks/surface-recall.sh` in this directory records a MEASURED finding (2026-09-29): a
# hook's plain output at exit 0 reaches the USER'S TRANSCRIPT, not the model's context. This repo
# names that defect — a gate's channel can be weaker than the gate — and I had written this advisory
# to stderr (r2 CLAUDE medium). The ACTOR here is the model: the remedy is "move history-shaped rows
# to the triggered entry", which the model performs. So it goes to `additionalContext`, by the same
# reasoning and the same mechanism as its sibling.
# ⚠ I did NOT independently re-measure the channel; this adopts a sibling's measurement. If the
# advisory is ever observed reaching nobody, that observation refutes this choice.
#
#     echo '{"tool_input":{"file_path":"docs/memory/MEMORY.md"}}' | .claude/hooks/check-memory-index-budget.sh
#     .claude/hooks/check-memory-index-budget.sh --self-test   # 16 cases
set -uo pipefail

# PURE: -> the repo root for an index path, or empty. Walks UP from the file, because the file is
# the subject. Accepts a root only if the guard it needs actually lives there.
root_for_index() {
  # ⟳ PR #430 r2 (Codex): the walk is done in PYTHON and the answer comes back with a trailing "/"
  # sentinel. `$(dirname …)` and command substitution both strip trailing NEWLINES, so a checkout
  # named "nl<newline>" resolved to its sibling "nl" and measured the wrong index, silently.
  local r
  [ -n "$1" ] || return 0
  r=$(python3 -c 'import os,sys
a=sys.argv[1]; d=os.path.dirname(a if os.path.isabs(a) else os.path.join(os.environ.get("PWD") or os.getcwd(), a))
while True:
    if os.path.isfile(os.path.join(d,"scripts","check-memory-index-budget.py")):
        sys.stdout.write(d+"/"); break
    p=os.path.dirname(d)
    if p==d: break
    d=p' "$1" 2>/dev/null) || return 0
  [ -n "$r" ] && printf '%s' "${r%/}"
  return 0
}

# PURE: -> 0 when this path names the always-loaded index. ⛔ Both the absolute and the
# repository-RELATIVE form must match: `*/docs/memory/MEMORY.md` alone requires a slash before
# `docs`, so a relative `docs/memory/MEMORY.md` matched nothing and the hook exited silently at 0 —
# measured (r2 CODEX finding 3) against a sentinel that was returning OVER BUDGET.
is_index_path() {
  case "$1" in
    */docs/memory/MEMORY.md|docs/memory/MEMORY.md|./docs/memory/MEMORY.md) return 0 ;;
    *) return 1 ;;
  esac
}

if [ "${1:-}" = "--self-test" ]; then
  ok=0; fail=0
  t() { if [ "$2" = "$3" ]; then ok=$((ok+1)); else fail=$((fail+1));
        printf '  [FAIL] %s\n         got  %s\n         want %s\n' "$1" "$2" "$3"; fi; }
  for p in "/a/b/docs/memory/MEMORY.md" "docs/memory/MEMORY.md" "./docs/memory/MEMORY.md"; do
    if is_index_path "$p"; then t "is_index_path accepts $p" yes yes; else t "is_index_path accepts $p" no yes; fi
  done
  # ⛔ ADJACENT negatives, not absurd ones: each is one edit away from the real path.
  for p in "docs/memory/MEMORY.md.bak" "docs/memory/OTHER.md" "memory/MEMORY.md" "" "docs/memory/MEMORY.mdx"; do
    if is_index_path "$p"; then t "is_index_path REJECTS '$p'" yes no; else t "is_index_path REJECTS '$p'" no no; fi
  done
  tmp=$(mktemp -d)
  mkdir -p "$tmp/repo/scripts" "$tmp/repo/docs/memory" "$tmp/outside"
  : > "$tmp/repo/scripts/check-memory-index-budget.py"
  : > "$tmp/repo/docs/memory/MEMORY.md"
  t "root_for_index walks UP from an absolute index to the repo holding the guard" \
    "$(root_for_index "$tmp/repo/docs/memory/MEMORY.md")" "$tmp/repo"
  t "root_for_index finds nothing when no guard lives above the file" \
    "$(root_for_index "$tmp/outside/docs/memory/MEMORY.md")" ""
  mkdir -p "$tmp/harness/projects/slug"; ln -s "$tmp/repo/docs/memory" "$tmp/harness/projects/slug/memory"
  alias_real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$tmp/harness/projects/slug/memory/MEMORY.md")
  if is_index_path "$tmp/harness/projects/slug/memory/MEMORY.md"; then t "the harness alias is NOT an index path lexically" yes no; else t "the harness alias is NOT an index path lexically" no no; fi
  if is_index_path "$alias_real"; then t "the harness alias RESOLVES to an index path (PR #430 r1 P1)" yes yes; else t "the harness alias RESOLVES to an index path (PR #430 r1 P1)" no yes; fi
  mkdir -p "$tmp/nl/scripts" "$tmp/nl/docs/memory" "$tmp/nl
/scripts" "$tmp/nl
/docs/memory"
  : > "$tmp/nl/scripts/check-memory-index-budget.py"; : > "$tmp/nl
/scripts/check-memory-index-budget.py"
  got=$(root_for_index "$tmp/nl
/docs/memory/MEMORY.md"; printf x); got=${got%x}
  t "root_for_index keeps a checkout name ending in a NEWLINE (PR #430 r2)" "$got" "$tmp/nl
"
  mkdir -p "$tmp/alias/docs"; ln -s "$tmp/repo/docs/memory" "$tmp/alias/docs/memory"
  ar=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$tmp/alias/docs/memory/MEMORY.md")
  t "a LEXICALLY matching alias resolves to the checkout that holds the file (PR #430 r2)" "$(root_for_index "$ar")" "$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$tmp/repo")"
  t "root_for_index on an empty path is empty, not the filesystem root" \
    "$(root_for_index "")" ""
  ( cd "$tmp/repo" && [ "$(root_for_index "docs/memory/MEMORY.md")" = "$tmp/repo" ] ) \
    && t "root_for_index resolves a RELATIVE index against the cwd" yes yes \
    || t "root_for_index resolves a RELATIVE index against the cwd" no yes
  rm -rf "$tmp"
  printf 'self-test: %s/%s cases passed\n' "$ok" "$((ok+fail))"
  [ "$fail" -eq 0 ] && exit 0 || exit 1
fi

# -> the advisory, as `additionalContext` so it reaches the model rather than only the transcript.
emit() {
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))' <<<"$1"
}

payload=$(cat)
path=$(printf '%s' "$payload" | python3 -c 'import json,sys
try:
    v = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
    print(v if isinstance(v, str) else "")
except Exception:
    print("")' 2>/dev/null || echo "")

# ⛔ RESOLVE THE EDITED FILE'S SYMLINKS FIRST (PR #430 r1, Codex P1). The harness writes the index
# through its own alias, ~/.claude/projects/<slug>/memory/MEMORY.md, a symlink into this repo's
# docs/memory/. Matched lexically, that path is not "docs/memory/MEMORY.md", so the hook was SILENT
# on the very writes it exists for. This resolves the EDITED FILE — the subject — never this
# script's own location, which is the regression recorded above.
real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]) if sys.argv[1] else "")' "$path" 2>/dev/null || echo "")
# ⟳ PR #430 r2 (Codex): the RESOLVED path is used whenever resolution succeeded — also when the
# lexical path already looks like an index. An alias `x/docs/memory -> B/docs/memory` matches
# lexically, and keeping it selected x (no checker: NOT MEASURED) or another checkout's checker.
if [ -n "$real" ] && is_index_path "$real"; then path="$real"; elif is_index_path "$path"; then :; else exit 0; fi

root=$(root_for_index "$path"; printf x); root=${root%x}
if [ -z "$root" ]; then
  # ⛔ NOT silent. The index was edited and the budget was NOT measured, which is a CANNOT RUN —
  # and this hook exists because a silent miss is indistinguishable from a healthy index.
  emit "⚠ memory index budget: NOT MEASURED — $path was edited but no scripts/check-memory-index-budget.py was found above it. Treat this as NOT RUN, never as a pass."
  exit 0
fi

out=$(cd "$root" && python3 scripts/check-memory-index-budget.py 2>&1)
rc=$?
if [ "$rc" -ne 0 ] || printf '%s' "$out" | grep -q '^WARNING'; then
  emit "⚠ memory index budget (advisory, rc=$rc, root $root):
$out"
fi
exit 0
