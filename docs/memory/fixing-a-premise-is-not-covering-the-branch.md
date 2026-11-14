---
name: fixing-a-premise-is-not-covering-the-branch
description: "FIRES-WHEN: fixing the condition a fail-open branch depends on, adding a check over an artefact a transformation rewrites, or writing a case that asserts something is ABSENT — ⭐⭐ PR #177: corrected the CONDITION and left the branch with zero coverage (3 mutations survived at 117/117). PR #181: a guard scanned the source BEFORE the mutation rewrote it. 2026-09-08: ~12 unfalsifiable cases across 8 guards. Plus correctness resting on a TYPE ACCIDENT"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7e830c04-6e2d-4fff-b4c9-baee2d50d9a8
  modified: 2026-08-31T01:50:55.603Z
---

**CURRENT RULE — after fixing a fail-open, cover the BRANCH, not only its premise:**
1. **Mutate the branch itself** (`!=`→`==`, delete the guard, `pass`). Ask *"which case executes this line?"* — a case
   that reaches it by a different path is not coverage. Extends [[guard-operands-from-one-closure]].
2. **When a check reads an artefact, ask WHICH VERSION it reads** — before or after the transformation the system
   exists to perform. In a mutation harness the answer is almost always "the wrong one".
3. **A negative assertion ships with a POSITIVE companion in the same case**, e.g.
   `("DECOY" in txt, bool(txt)), (False, True)` — assert the subject was SEEN (`stats["rounds"] == 1`), not merely
   un-complained-about. *"Nothing went wrong" is satisfied by "nothing happened."*
4. **The fixture must reach the named rule** — check no DIFFERENT rule filters the input first, and that values
   which should differ actually differ (one producer per symbol makes `all`/`any` and `>`/`>=` agree).
5. **A fix prompted by a measured defect ships WITH its case**; a comment recording the defect is not coverage.
6. **When correctness depends on operand TYPES, not meaning, name the property** (use a sentinel). Ask: *what obvious
   refactor would silently break this, and would anything fail?*
7. **Run the mutation battery before claiming a fix is guarded** — reasoning missed these; execution caught them.

**Why:** every instance below was green, several in files whose own docstrings warned about the class, and twice in
my own tooling the same session I wrote the rule. "I will notice" is not a bound.

## History

**PR #177 (merged 2026-08-29, squash `1172722`; both halves NOT CONVERGED, 2 High;
`docs/reviews/branch-dashboard-cwd-r1-{claude,codex}.md`).** The dashboard rendered a green *"No entries yet"* over 8
real entries. `main()`'s carve-out "a missing DEFAULT store is nothing written yet" was right; its premise (the
default path is repo-anchored) was false. I anchored the path and never tested the branch: three mutations of
`if a.store != ap.get_default("store")` survived at **117/117**, and `!=`→`==` reproduced the reported symptom for
`--store docs/typo.md`. Every `main()` case passed `--store` explicitly.
- **Type accident:** that comparison was `str` vs `PosixPath` and worked only because `PosixPath.__eq__(str)` is
  `NotImplemented`; the tidy-up `type=pathlib.Path` would have restored the fail-open with nothing objecting, and
  the adjacent comment invited it. Now an `is None` sentinel.
- **Three vacuous absence-assertions:** a store test coupled to `docs/` existing (caught by the `--mutate` control);
  `"DECOY" not in _txt` with `_txt = ""` when the file is missing — green at 117/117 with the bug live (both halves
  found it); `_store_label` `$HOME` leak fixed with no guard (caught by running the battery). `gen-dashboard.py`
  already said *"Both assertions are NEGATIVE, so each carries a POSITIVE companion"* — written by me, not applied.
  Family: [[rls-denial-is-indistinguishable-from-absence]].
- **What worked:** both halves found different things (overlap 1; Codex-only the `$HOME` leak; Claude-only the
  deepest) — [[dual-review-what-it-catches]]; holding edits until both halves reviewed one commit; Codex fell from
  `gpt-5.6-*` (HTTP 400) to `gpt-5.5` unaided; `gh pr checks` showed the OLD run after a push — match `headSha`
  ([[a-check-result-is-not-the-claim]]).
- Carried, not filed: explicit relative `--store` resolves against cwd (deliberate, fails loudly); `GIT_DIR`
  overrides `cwd=` (latent). See [[feedback-agree-before-filing]].

**PR #181, 2026-08-30 — one hour later, same shape.** The harness's `$HOME` redirect covers `Path.home()` and bare
`~` only (`pwd.getpwuid().pw_dir`, `expanduser("~user")` return the real home, measured). My `home_escapes()` scan read
`root / target` — the source BEFORE mutation — so an entry whose replacement text introduced `getpwuid` passed.

**Series, 2026-09-08 (R4 manifest debt 21 → 0, PRs #256–#263).** First manifests on eight guards found **~12** cases
unable to fail for the reason their name gave — by mutation, none by reading. `check-plan-task-order` had FIVE (inputs
stopped by a lowercase-prose rule; lowercase `epsilon`/`omega`; one producer per symbol). `check-ci-watched`'s
case-insensitivity case was masked by the unknown-state fallback. `check-review-rounds` asserted `problems == []` for
two layouts. `check-live-schema` added `idx` to `ATTRIBUTABLE_KINDS` on 2026-08-28 with no case — removing it survived
all 117. Twice in my own tooling: a manifest generator checked anchor uniqueness per FILE when the rule scopes it to the
MANIFEST (8 of 9 loaded, no error), and a mutation deleted prose that read like the asserted guidance while the asserted
token sat on the next line. Both caught by the harness, not care.
