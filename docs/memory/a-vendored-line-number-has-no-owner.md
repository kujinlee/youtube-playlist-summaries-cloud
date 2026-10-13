# A line number in SOMEBODY ELSE'S file has no owner here, so it rots silently

**Measured 2026-10-13.** **FIVE** sibling documents cited `session-start-hook.sh:795` (and
`:809-812`, `:814-825`, `:800-802`) as the evidence for where a session handoff must be written.
Against the live **0.33.0** hook — **2,027 lines** — the real locations are `:1171`, `:1666`,
`:1571-1640`, `:1546`. ⚠ **How FAR they drifted is NOT measured and must not be claimed:** the
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
  blocked reader to open. ⭐ **Why it was missed, exactly: `grep -r` does not follow the symlink
  `.claude/skills/handoff` → `../../.agents/skills/handoff`. `grep -R` does.** One file, two paths —
  see [[verify-the-other-copy-exists-before-deleting]], which is the same symlink shape.

⭐ **The fix is to REMOVE the number, not to update it.** Nothing here can hold a vendored line: no
guard can watch it, and `npx skills@latest add` or a plugin bump invalidates it with no commit. Name
the SYMBOL and give the command (`grep -n 'REMEMBER_HANDOFF=' <hook>`). This is
[[a-retrospective-number-needs-provenance]] applied to a dependency.

## ⛔⛔ AND THE CORRECTION REPEATED THE DEFECT ONE LAYER IN — the part worth remembering

The replacement text asserted, as a ⭐ lesson to copy, that *"the hook refuses to degrade quietly …
withholds the hint"*. **Measured false.** Driven in an isolated tree, a `per_session` request with no
resolvable session id prints the hint anyway — the **shared** path, plus a line saying the mode did
not apply. There are **three** hint triggers, not two.

⭐ **The claim came from a COMMENT in the same vendored file (`:1153-1163`), and that comment is
stale.** Fifty lines down the hook corrects itself: *"NOT withheld on degrade … That reasoning was
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
