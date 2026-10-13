# A line number in SOMEBODY ELSE'S file has no owner here, so it rots silently

**Measured 2026-10-13.** Four live sites cited `session-start-hook.sh:795` (and `:809-812`,
`:814-825`, `:800-802`) as the evidence for where a session handoff must be written. Against the
live **0.33.0** hook — **2,027 lines** — the real locations are `:1171`, `:1666`, `:1571-1640`,
`:1546`. **Every citation was stale by 370–870 lines and pointed into the wrong third of the file.**

**Where they were, and why that matters more than the drift:**

* `docs/plugins.md` — the ⛔ RULE box;
* `docs/process-rationale.md` — the account;
* `scripts/check-handoff-path.py` — **a CODE COMMENT, which `check-withdrawal` cannot see** (it
  globs `docs/`), so no guard could ever have caught it;
* `.claude/hooks/enforce-handoff-path.sh` — ⛔ **the refusal text printed to the reader**, so the one
  moment someone needed the locator was the moment it sent them to the wrong line.

⭐ **The fix is to REMOVE the number, not to update it.** Nothing in this repo can hold a vendored
line: no guard can watch it, and `npx skills@latest add` or a plugin bump invalidates it with no
commit. Name the SYMBOL and give the command (`grep -n 'REMEMBER_HANDOFF=' <hook>`). This is
[[a-retrospective-number-needs-provenance]] applied to a dependency.

⚠ **A review half had ALREADY flagged it** — `docs/reviews/claude/velocity-177-r5-claude.md:161`
counted the locators in `plugins.md` and named `:795` as one. The observation was filed and nothing
consumed it: [[an-escalation-has-no-closer]] one class over.

⭐ **The second finding was the one worth having.** The RULE stated its path UNCONDITIONALLY and the
hook has **two modes** (`.handoff_mode`: `single` → `remember.md`, `per_session` →
`remember.<session-id>.md`). The rule is right for this install and never wrong in practice — but
*correct here* is not *unconditional*, and what made it safe was a clause present for another
reason: **obey the printed `Write next handoff to:` hint whenever one appears.** When a rule names
one world, ask what the other world does — [[true-about-the-name-silent-about-the-layer]].
