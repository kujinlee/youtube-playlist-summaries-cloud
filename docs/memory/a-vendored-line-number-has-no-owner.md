---
name: a-vendored-line-number-has-no-owner
description: "FIRES-WHEN: citing a line number (or a comment) in a VENDORED/plugin file, or searching a corpus for every citation of something. Name the SYMBOL, never the line, in any rule a reader must follow; quote the code, not its comment"
metadata:
  type: feedback
---

**The rule: a line number in somebody else's file has no owner here and rots silently — a plugin bump or `npx skills@latest add` invalidates it with no commit and no guard can watch it. In a RULE A READER MUST FOLLOW (a ⛔ rule box, a skill, a hook's refusal text), name the SYMBOL and give a command that works on the reader's tools — e.g. `REMEMBER_HANDOFF` in `…/remember/<version>/scripts/session-start-hook.sh` (there are TWO assignments, per-session and shared).**

- **Owner narrowing, 2026-10-13:** a DATED RETROSPECTIVE that NAMES THE VERSION it measured MAY cite lines — that is what makes its claim checkable, and a later reader sees the citation is about that version. (The first, exception-free version of the rule was broken by the branch that shipped it: it removed 4 vendored citations while adding 44 line references to explain where content went.)
- **Quote the CODE, not a comment.** A comment in a dependency is a characterisation nobody here owns ([[quote-the-code-dont-characterise-it]]).
- **To find every citation, search the right corpus.** The instruction lives in ONE place and is not restated here: [`.agents/skills/shared/corpus-search.md`](../../.agents/skills/shared/corpus-search.md). The handoff delivery mechanism likewise: [`.agents/skills/shared/handoff-path.md`](../../.agents/skills/shared/handoff-path.md).
- **When a rule names one mode of a two-mode mechanism, ask what the other mode does** ([[true-about-the-name-silent-about-the-layer]]).

**Why:** the stale locator misled exactly where it was needed — including the hook's refusal text, which sent a blocked reader to the wrong line.

## History (condensed; branch `plugins-handoff-citations`, reviews `docs/reviews/{codex,claude}/plugins-handoff-citations-r*`)

- **2026-10-13:** FIVE documents cited `session-start-hook.sh:795` (and `:809-812`, `:814-825`, `:800-802`) as evidence for where a handoff must be written. Against the live **0.33.0** hook (**2,027 lines**) the content had moved (to `:1171`, `:1666`, `:1546`, and the `REMEMBER_HANDOFF_STATE` symbol). How FAR they drifted is NOT measured — the pre-0.33.0 hook was never fetched; an earlier "stale by 370–870 lines" was an inference and was withdrawn.
- **The five sites:** `docs/plugins.md` (rule box), `docs/process-rationale.md`, `scripts/check-handoff-path.py` (a code comment no doc guard reads), `.claude/hooks/enforce-handoff-path.sh` (the refusal text), and `.agents/skills/handoff/SKILL.md` — **missed by the correction that fixed the other four**, because `.claude/skills/handoff` is a symlink and the filesystem walk skipped it. `git grep -l session-start-hook` against the pre-branch base found all five live sites (six tracked files in total, the sixth a filed review).
- **`git grep` is not complete either (r4 H1, measured with a green control):** it searches the INDEX — an `assume-unchanged` file edited on disk returns the stale indexed string (`git grep` 0, `grep -rl` 1); `skip-worktree` → 0; a tracked file deleted from the worktree → 0; untracked content → 0. Three earlier rounds argued `-r` vs `-R` vs `-RS` (BSD grep ignores `-R`'s symlink sense; GNU grep 3.12 has no `-S` per its source option table, not a runtime probe) — optimising the wrong instrument (r3 H1).
- **The correction repeated the defect one layer in:** it taught, as a ⭐ lesson, that the hook "withholds the hint" on degrade — taken from a stale COMMENT in the same vendored file (sentence `:1159`, block ends `:1163`); the correction at `:1185` and the code say the opposite: a `per_session` request with no session id prints the shared path plus a line saying the mode did not apply. There are **three** hint triggers, not two. Graded Blocking because it shipped as transferable wisdom. (The distance between them was published as "fifty", then "26", then a reviewer's "22" — state the anchors, not a distance.)
- **Second finding:** `.handoff_mode` (`single` → `remember.md`, `per_session` → `remember.<session-id>.md`) comes from three deep-merged layers (bundled plugin config, `~/.remember/config.json`, `<repo>/.remember/config.json`), all absent here — the first published evidence named the wrong set.
- The lead-in of this very file kept a RETIRED position as its headline until round 4 (r4 H3) — the class this file records, applied to itself.

Related: [[a-retrospective-number-needs-provenance]] (this is it, applied to a dependency), [[verify-the-other-copy-exists-before-deleting]] (same symlink shape — ⚠ no memory file by that name exists as of 2026-11-14; dangling link).
