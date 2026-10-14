<!-- canon: corpus-search -->
# Inventorying every place a string appears in this repo

**This file is the ONE place this instruction is described.** Everywhere else cites it. The same
instruction was written at SIX sites, nothing compared them, and five consecutive review rounds
each found a copy that had drifted — a withdrawn claim left standing, a count with no unit, a
provenance qualification applied at one site and not its neighbour.
`scripts/check-canonical-source.py` is what keeps this true.

---

## ⭐ IT IS A PROMPT TO LOOK, NOT A PROOF

Run all three and compare:

    git grep -l <string>              # the INDEX's paths, read from the worktree when it can
    git grep --cached -l <string>     # the cached blobs
    /usr/bin/grep -RSl <string> .     # the filesystem, following symlinks
                                      # (or `rg --hidden -l` — see the rg trap below)

**Treat any disagreement as a reason to LOOK.** It may mean something is untracked, ignored,
index-masked or deleted — and it may equally be a binary file, a submodule, `.git` internals, or a
case-only rename on a case-insensitive filesystem.

⛔ **"Two that agree can be trusted" is WITHDRAWN.** It was the fifth claim this one instruction
made and the fifth to be refuted. Four measured limits:

1. **Agreement proves nothing about CONTENT.** With `NEEDLE OLD` indexed and `NEEDLE new` on disk in
   an `assume-unchanged` file, every `-l` lists the same path while `git grep` returns the **stale
   indexed line**. Compare CONTENT when content is what matters.
2. **Disagreement has innocent causes** — ignored files, `.git` internals, registered submodules,
   binary files, case-only renames.
3. **The filesystem leg's reach is TOOL-SPECIFIC** (next section).
4. **Outside a repository `git grep` exits 128** — an error, not an empty result.

## ⛔ What each tool misses — the SHAPES, not a count

⚠ **Counts here move whenever a file is committed, so they are not the finding.** A round published
`13/14/12/14` and the next round could not replay it, because the file explaining the difference had
itself been committed in between. **State the SHAPE and name the ref if you must give a number.**

| leg | what it misses |
|---|---|
| `git grep -l` | untracked, ignored, submodule, nested-checkout and vendored content |
| `git grep -l` | **TRACKED files too**: `assume-unchanged` returns the stale indexed string; `skip-worktree` and worktree-deleted return nothing |
| default `rg` | **DOT-PREFIXED paths** — measured, it missed exactly `.agents/skills/handoff/SKILL.md` and `.claude/hooks/enforce-handoff-path.sh`, the two files that whole investigation was about, and `rg --hidden` recovered exactly those two and nothing else |
| default `rg` | ignored files, and a committed BINARY that both git legs find |
| plain recursive `grep` | symlinked directories, unless the symlink-following flag is given |

⛔ **Three distinct `rg` blind spots exist and only the ignore-rule one used to be written down.**
Use `rg --hidden`, or `/usr/bin/grep -RSl`.
⚠ **And `/usr/bin/grep` EXPLICITLY**: `grep` is a shell FUNCTION on this machine, so a prescribed
bare `grep -rl` is not a determinate instrument.
⚠ A single-line `grep` cannot see a clause that WRAPS. Three measurements were wrong this way in one
day. Fold newlines (`tr '\n' ' '`) when counting prose, and prove a known-positive control with the
same instrument before trusting a zero.

## ⚠ Flag provenance, and keep the version

Three rounds argued about `grep -r` versus `-R` versus `-RS`: BSD grep ignores `-R`'s symlink sense,
**GNU grep 3.12** has no `-S` at all, and ripgrep rejects `-R`.

⛔ **The GNU leg is from GNU grep 3.12's SOURCE option table, not from a runtime probe** — the round
that found it could not build the binary and said so. ⛔ *"Each version was checked against the
binaries the author happened to have"* is **WITHDRAWN**: it contradicts the source-only provenance
in the same breath, and it stood beside its own qualification at two sites.
⚠ The version is load-bearing: `-S` could appear in a later release, at which point an unversioned
claim goes silently wrong exactly like a stale line number.

## ⭐ For a VENDORED file, no repo-side search reaches it at all

Name the SYMBOL and the path, never a line number — a line number in a vendored file has no owner
here, no guard can watch it, and a plugin bump invalidates it silently.
