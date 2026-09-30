---
name: fixing-a-premise-is-not-covering-the-branch
description: "FIRES-WHEN: fixing the condition a fail-open branch depends on — ⭐⭐ TWICE. PR #177: I corrected the CONDITION a fail-open branch depended on and left the branch with zero coverage — 3 mutations survived at 117/117. PR #181: the guard I wrote scanned the source BEFORE the mutation, and a mutation is the one thing that rewrites it. Plus: correctness resting on a TYPE ACCIDENT, and 3 vacuous absence-assertions in one session"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7e830c04-6e2d-4fff-b4c9-baee2d50d9a8
  modified: 2026-08-31T01:50:55.603Z
---

**MERGED 2026-08-29 — PR #177, squash `1172722`.** Dual review, both halves NOT CONVERGED, 2 High.
Full account: `docs/reviews/branch-dashboard-cwd-r1-{claude,codex}.md` + its Disposition table.

## ⭐⭐ SERIES RESULT, 2026-09-08: TWELVE unfalsifiable cases across EIGHT guards

Paying off the R4 mutation-manifest debt (21 -> 0, PRs #256-#263) put a first mutation manifest on
eight guards that had none. Every guard was green and stayed green. **Roughly twelve of their
existing self-test cases turned out to be unable to fail for the reason their name gave** — found
by mutation, none by reading, several in files whose own docstrings warn about this exact class.

**Two recurring causes. Ask both of any case that asserts a rule holds:**

1. **The fixture used an input a DIFFERENT rule filters first**, so the named rule was never
   reached. `check-plan-task-order` had FIVE at once: `lib/…` and `parse.ts:42` are stopped by a
   lowercase-prose rule, not by the path and file:line guards those cases are named for; `epsilon`
   and `omega` are lowercase, so the mode-reset and prose-termination branches could both be
   deleted; and every fixture symbol had exactly ONE producer, so `all` / `any` and `>` / `>=`
   agreed and the ordering predicate was unfalsifiable. Also `check-ci-watched`'s
   case-insensitivity case (masked by the unknown-state fallback).
2. **The assertion is an ABSENCE that deleting the subject also satisfies.**
   `check-review-rounds` asserted `problems == []` for two layouts; delete the code that FINDS the
   files and you get the same empty list. *"Nothing went wrong" satisfied by "nothing happened."*
   Fix: assert the subject was SEEN (`stats["rounds"] == 1`), not merely un-complained-about.

**A third, distinct shape: the FIX shipped without the CASE.** `check-live-schema` added `idx` to
`ATTRIBUTABLE_KINDS` on 2026-08-28 after a measured miss — and no case came with it. Removing
`"idx"` again survived all 117. *When a fix is prompted by a measured defect, the case is part of
the fix; a comment recording the defect is not coverage of it.*

⚠ **It happened to my own tooling twice in the same session**, which is the honest bound on
"I will notice this". A manifest generator checked anchor uniqueness against the FILE when the
consuming rule scopes it to the MANIFEST (8 of 9 loaded, no error at the call site); and a mutation
I wrote deleted prose that READ like the guidance a case names while the token it actually asserts
sat on the next line. Both were caught by the harness, not by care.

## 1. Fixing a branch's PREMISE is not covering the BRANCH

The dashboard rendered a green *"No entries yet"* over 8 real entries. Root cause: `main()`'s
carve-out *"a missing DEFAULT store is nothing written yet"* was correct, but its premise — that the
default path is repo-anchored — was false. I anchored the path. **I never tested the branch.**

Review measured three mutations of `if a.store != ap.get_default("store")` — `!=`→`==`, delete the
guard, `pass` — **all surviving at 117/117**. And `!=`→`==` renders the same green *"No entries
yet"* for `--store docs/typo.md`: **the exact reported symptom, on different input, at a green suite.**

**Why:** every existing `main()` case passed `--store` explicitly, so the omitted-store path through
that comparison was never executed by any assertion. I reasoned correctly about the cause *in the
commit message* and still shipped the branch unguarded.

**How to apply:** after fixing a fail-open, mutate **the branch itself**, not only the input it reads.
Ask *"which case executes this line?"* — if the answer is a case that takes a different path to get
there, there is no coverage. Extends [[guard-operands-from-one-closure]].

### ⚠ SECOND OCCURRENCE, 2026-08-30, PR #181 — one hour after writing the fix it broke

Codex found that the mutation harness's `$HOME` redirect covers `Path.home()` and a bare `~` and
**nothing else** (`pwd.getpwuid().pw_dir` and `expanduser("~user")` return the REAL home, measured).
I fixed it with `home_escapes()`, a scan refusing any mutation target that uses those routes — and
wired it to read **`root / target`, the source as it is BEFORE the mutation.** A mutation is the one
thing that rewrites that source, so a clean target says nothing about what the manifest is about to
put there: an entry whose *replacement text* introduced `getpwuid` passed the brand-new check.

**The premise I corrected was "the code is clean"; the branch I left uncovered was "the mutation
makes it dirty".** Same shape, different substrate, and I did not recognise it while writing it.

**How to apply, sharpened:** when you add a check over an artefact, ask *which version of that
artefact the check reads* — before or after the transformation the system exists to perform. In a
mutation harness the answer is almost always "the wrong one".

## 2. ⚠ Correctness by TYPE ACCIDENT is not correctness

Post-fix, "did the caller name a store?" was `a.store != ap.get_default("store")`, comparing a `str`
to a `PosixPath`. It worked **only because `PosixPath.__eq__(str)` is `NotImplemented`**. Adding the
obvious cleanup `type=pathlib.Path` would have silently restored the fail-open, and review measured
that **nothing in the suite objected**. Worse, the comment beside it invited exactly that tidy-up.

Now an `is None` **sentinel**. **How to apply:** when a guard's correctness depends on the *types* of
its operands rather than their meaning, name the property explicitly. Ask: *what obvious refactor
would silently break this, and would anything fail?*

## 3. ⭐ THREE vacuous absence-assertions in ONE session — the dominant shape

Each asserted a wrong answer was ABSENT without proving the positive path ran:

1. store test coupled to `docs/` existing — **caught by the `--mutate` control going red**;
2. `"DECOY" not in _txt`, where `_txt = "" if not file.is_file()` — **green at 117/117 with the bug
   live**. Found by BOTH review halves;
3. `_store_label` — I fixed the `$HOME` leak and shipped **no guard**, the same omission the round
   had just penalised twice. Caught only by running the battery.

`gen-dashboard.py:786` already stated the rule — *"Both assertions are NEGATIVE, so each carries a
POSITIVE companion"* — written by me, for this hazard, and not applied. Same family as
[[rls-denial-is-indistinguishable-from-absence]] (`provesAbsence`) one layer up, in the tests.

**How to apply:** a negative assertion ships with a positive companion in the SAME `case(...)` tuple,
e.g. `("DECOY" in txt, bool(txt)), (False, True)`. And **run the mutation battery before claiming a
fix is guarded** — reasoning did not catch #3; execution did.

## 4. What worked, worth keeping

- **Both halves earned their keep and found DIFFERENT things.** Overlap: 1. Codex-only: the `$HOME`
  leak. Claude-only: the deepest finding (#1 above). One reviewer would have missed it —
  [[dual-review-what-it-catches]] again.
- **Holding all edits until the second reviewer returned.** #176's reviewer measured `e006604` while
  HEAD was `d16dcd8`; both halves here reviewed one commit.
- **Codex gate held:** `gpt-5.6-*` → HTTP 400 → fell to `gpt-5.5` unaided; `--out` outside the repo,
  `docs/reviews/` verified untouched (backlog #68's hand mitigation, still not a mechanism).
- **`gh pr checks` reported the OLD run after a push.** Re-verified by matching `headSha` — same
  class as [[a-check-result-is-not-the-claim]].

## Carried, stated not ticked

Explicit **relative** `--store` still resolves against cwd (deliberate: right convention for a typed
path, and it FAILS LOUDLY). `GIT_DIR` overrides `cwd=` (latent, no caller sets it). Neither filed —
[[feedback-agree-before-filing]].
