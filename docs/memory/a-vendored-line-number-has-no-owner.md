# A line number in SOMEBODY ELSE'S file has no owner here, so it rots silently

**Measured 2026-10-13.** **FIVE** sibling documents cited `session-start-hook.sh:795` (and
`:809-812`, `:814-825`, `:800-802`) as the evidence for where a session handoff must be written.
Against the live **0.33.0** hook — **2,027 lines** — the real locations are `:1171`, `:1666`,
`REMEMBER_HANDOFF_STATE` for the delivery record (⟳ a `:1571-1640` range stood here and UNDER-BOUNDED the mechanism — round 3 M4; ⭐ the symbol is the honest citation and that is this lesson applied to itself), `:1546`. ⚠ **How FAR they drifted is NOT measured and must not be claimed:** the
earlier version of this file said *"stale by 370–870 lines"* and that the hook *"grew by a thousand
lines"*. Both are inferences — the pre-0.33.0 hook was never fetched, so its length is unknown. The
measurable fact is that every citation names a line whose content is now something else.

**Where they were, and why that matters more than the drift:**

* `docs/plugins.md` — the ⛔ RULE box;
* `docs/process-rationale.md` — the account;
* `scripts/check-handoff-path.py` — **a code comment, which no document guard reads**;
* `.claude/hooks/enforce-handoff-path.sh` — ⛔ **the refusal text printed to the reader**, so the one
  moment someone needed the locator was the moment it sent them to the wrong line;
* `.agents/skills/handoff/SKILL.md` — ⛔⛔ **the fifth, and it was MISSED by the correction that
  fixed the other four.** Git-tracked, authored in the SAME commit as them (`24ff8694`), listed as
  Layer 3 of this very mechanism in `plugins.md`, and it is the file the refusal text tells a
  blocked reader to open. ⭐⭐ **Why it was missed — and r4 H3: this lead-in read "the lesson is ONE INSTRUMENT, not a flag" until round 4, which is the RETIRED position left standing as the HEADLINE of the paragraph that corrects it. The fold that corrected the clause inside this very line did not touch its opening, the eleventh instance of this branch's class and the third I authored in one session. The lesson is TWO CORPORA AND A CROSS-CHECK:** the inventory walked the filesystem, and `.claude/skills/handoff` is a symlink to `../../.agents/skills/handoff` — one file under two paths, which a recursive search that does not follow symlinks skips. ⛔⛔ **For a TRACKED corpus, `git grep` has no flag problem and no symlink problem at all** — measured against the pre-branch base, `git grep -l session-start-hook` finds all five LIVE stale-citation sites including the symlinked one — ⚠ r5 M1: **six** tracked files match in total, the sixth being a filed review left as written (the clause the skill already carried and this file did not), because it searches what git tracks instead of walking the filesystem. ⛔ **r4 H1 corrected two things in that sentence: it is a CORPUS, not "every site", and it does NOT read the index.** ⛔ **AND THE FOURTH VERSION WAS WRONG TOO (r4 H1).** It said `git grep` reads the working-tree content of tracked files. It searches the paths in the **INDEX**, reading each from the working tree UNLESS the entry is `skip-worktree`/`assume-unchanged` or absent — then it reads the **cached blob**, or nothing. Measured with a green control: a TRACKED file marked `assume-unchanged` and edited on disk returns the **stale indexed string** and misses the on-disk one (`git grep` 0, `grep -rl` 1); `skip-worktree` → 0; a tracked file deleted from the worktree → 0. All TRACKED, so "name the corpus" does not save a reader. It also misses untracked, ignored, submodule, nested-checkout and vendored content (untracked, measured: `grep -rl` 1, `git grep` 0). ⭐ **The instruction that survives all of it is a CHECK, not a command:** run `git grep -l`, then compare against `git grep --cached -l` AND a filesystem walk, and treat any disagreement as a PROMPT TO LOOK. ⛔ **r5 — AND "TWO THAT AGREE CAN" IS WITHDRAWN; it was the fifth claim this one sentence has made and the fifth to be refuted.** Measured: all three can **AGREE while reading different content** (`assume-unchanged`, `NEEDLE OLD` indexed and `NEEDLE new` on disk — every `-l` lists the same path while `git grep` returns the stale indexed line); **disagreement has INNOCENT causes** (ignored files, `.git` internals, registered submodules, binary files, and a case-only rename on a case-insensitive filesystem); the filesystem leg's reach is **TOOL-SPECIFIC** (default `rg` skips ignored files; a plain recursive `grep` does not follow symlinks); and **outside a repository `git grep` exits 128** — an error, not an empty result. ⭐ So it is a **PROMPT TO LOOK, not a proof**: compare CONTENT when content is what matters. ⛔ **r5 CLAUDE H2 — NOT a bare `rg` as the filesystem leg:** default `rg` skips DOT-PREFIXED paths, and measured here it misses exactly `.agents/skills/handoff/SKILL.md` and `.claude/hooks/enforce-handoff-path.sh` — the two files this lesson is ABOUT — which `rg --hidden` recovers and nothing else; it also misses a committed BINARY that both git legs find. So three distinct `rg` blind spots and only the ignore-rule one was named. Use `rg --hidden`, or `/usr/bin/grep -RSl` with its symlink leg stated. ⚠ And `/usr/bin/grep` EXPLICITLY: `grep` is a shell FUNCTION on this machine, so a prescribed `grep -rl` is not a determinate instrument, and no site said so. ⟳ **Three rounds of this branch argued about `-r` vs `-R` vs `-RS`** (BSD grep ignores `-R`'s symlink sense; GNU grep has **no `-S`** — ⚠ that leg is from **GNU grep 3.12's** source option table (r4 L4: the version is the clause this file's own rule requires), not a runtime probe, because the round that found it could not build GNU grep and said so; ripgrep rejects `-R`) **and every one of those rounds was optimising the wrong instrument** (round 3 H1). ⚠ Keep the `=` when you search: `REMEMBER_HANDOFF=` matches exactly the 2 assignments, the bare name matches 23 lines across three variables. See [[verify-the-other-copy-exists-before-deleting]], the same symlink shape.

⭐ **The fix is to REMOVE the number, not to update it — ⟳ AND THE OWNER NARROWED WHAT "REMOVE" BINDS (2026-10-13, after a review measured this file breaking its own rule).** ⛔ **The prohibition binds a RULE A READER MUST FOLLOW** — where a stale locator misleads at the moment of need, which is exactly where it did: the ⛔ RULE box in `plugins.md`, the handoff skill, and the hook's REFUSAL TEXT. ⭐ **A dated retrospective that NAMES THE VERSION it measured may cite lines**, because that is what makes its own claim checkable, and a reader at a later version can see at a glance that the citation is about 0.33.0 and not about theirs. ⚠ **Why this narrowing exists: the first version of this rule admitted no exception, and the branch that shipped it removed 4 vendored citations while its own diff added 44 distinct line references** — explaining the staleness required saying where the content went. A rule that cannot be followed by the document stating it is not a rule. Nothing here can hold a vendored line: no guard can watch it, and `npx skills@latest add` or a plugin bump invalidates it with no commit. Name the SYMBOL and give a command that works on the reader's tools, not yours
(`REMEMBER_HANDOFF` in `…/remember/<version>/scripts/session-start-hook.sh` — there are TWO
assignments, per-session and shared, which is itself the thing worth seeing). This is
[[a-retrospective-number-needs-provenance]] applied to a dependency.

## ⛔⛔ AND THE CORRECTION REPEATED THE DEFECT ONE LAYER IN — the part worth remembering

The replacement text asserted, as a ⭐ lesson to copy, that *"the hook refuses to degrade quietly …
withholds the hint"*. **Measured false.** Driven in an isolated tree, a `per_session` request with no
resolvable session id prints the hint anyway — the **shared** path, plus a line saying the mode did
not apply. There are **three** hint triggers, not two.

⭐ **The claim came from a COMMENT in the same vendored file (`:1153-1163`), and that comment is
stale.** ⟳ **22 to 26 lines** down the hook corrects itself — ⚠ *the span is ambiguous by construction and three parties gave three numbers: the stale SENTENCE is at `:1159`, its comment BLOCK ends at `:1163`, the correction is at `:1185`. I published "fifty", then "26"; a reviewer said "22". State the anchors, not a distance*: *"NOT withheld on degrade … That reasoning was
wrong … The honest fix is not silence, it is a visible line."* The code matches the second comment.

⛔ **So a correction written to stop citing a vendored file from memory cited that file's COMMENT
from memory — the same defect with the line number taken out.** Quote the CODE
([[quote-the-code-dont-characterise-it]]); a comment is a characterisation, and in a dependency it
is one nobody here owns either. ⚠ A review graded this **Blocking**, not Medium, because it shipped
as transferable wisdom rather than as a stray figure.

⭐ **The true behaviour is the better lesson:** the hook neither goes silent nor lies — it prints the
real path and a second line saying the mode you asked for did not apply. Its own history records
that silence was tried, reviewed and rejected.

## The second finding: a rule stated unconditionally over a two-mode mechanism

`.handoff_mode` is `single` by default (`remember.md`) or `per_session`
(`remember.<session-id>.md`). The rule naming one path is right for this install — but ⚠ **the
evidence first published for that was the wrong SET**: `.handoff_mode` comes from no Claude settings
file at all, but from three deep-merged layers (bundled plugin config, `~/.remember/config.json`,
`<repo>/.remember/config.json`), **all absent**. When a rule names one world, ask what the other
world does — [[true-about-the-name-silent-about-the-layer]].

⤳ **Provenance:** branch `plugins-handoff-citations`, reviewed round 1 (Codex + Claude) —
`docs/reviews/{codex,claude}/plugins-handoff-citations-r1-*.md`. Every correction above comes from
that round, not from the authoring pass.
