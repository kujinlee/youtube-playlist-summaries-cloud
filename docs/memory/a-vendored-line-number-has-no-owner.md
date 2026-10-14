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
  blocked reader to open. ⭐⭐ **Why it was missed, and the lesson is ONE INSTRUMENT, not a flag:** the inventory walked the filesystem, and `.claude/skills/handoff` is a symlink to `../../.agents/skills/handoff` — one file under two paths, which a recursive search that does not follow symlinks skips. ⛔⛔ **For a TRACKED corpus, `git grep` has no flag problem and no symlink problem at all** — measured against the pre-branch base, `git grep -l session-start-hook` finds all FIVE tracked sites including the symlinked one, because it searches what git tracks instead of walking the filesystem. ⛔ **r4 H1 corrected two things in that sentence: it is a CORPUS, not "every site", and it does NOT read the index.** Default `git grep` reads the **working-tree** content of tracked files (`--cached` for staged, `git grep <commit>` for a version), and it misses untracked, ignored, submodule, nested-checkout and vendored content — measured, an untracked file holding the string: `grep -rl` 1, `git grep` 0. ⟳ **Three rounds of this branch argued about `-r` vs `-R` vs `-RS`** (BSD grep ignores `-R`'s symlink sense; GNU grep has **no `-S`** — ⚠ that leg is from GNU's source option table, not a runtime probe, because the round that found it could not build GNU grep and said so; ripgrep rejects `-R`) **and every one of those rounds was optimising the wrong instrument** (round 3 H1). ⚠ Keep the `=` when you search: `REMEMBER_HANDOFF=` matches exactly the 2 assignments, the bare name matches 23 lines across three variables. See [[verify-the-other-copy-exists-before-deleting]], the same symlink shape.

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
