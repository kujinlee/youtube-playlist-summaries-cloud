---
name: owner-decisions-1113-marketplace-ff-392
description: "FIRES-WHEN: marketplace decision 5 or 7, the main-checkout fast-forward, or PR #392's migration 0028 comes up. Owner 11-13: copyright = Kujin Lee; decision 5 FINAL 17:15 = A+B+C exclude, D paraphrased + anonymized (essence only); I decide the ff myself; I may apply 0028 to prod."
metadata:
  type: project
---

## Current decisions (owner, 2026-11-13)

1. **Walkthrough decision 5 (corpus content review) — FINAL 17:15**, per group of
   `docs/marketplace/decision-5-suspect-files.md`: *"Suggested default: ship no file in A–C … I will take this
   suggestion. For D, paraphrase and anonymize the quote. Only convey essence of the example and not specifics."*
   A (production infra), B (business/costs), C (local machine) = EXCLUDE. D (owner's words) = ship with each quote
   paraphrased and anonymized, essence only. The ~170 other lesson files ship. Recorded on master by PR #583
   (`20310a55`).
2. **Decision 7 (copyright holder):** *"use my name \"Kujin Lee\""* — the license names Kujin Lee.
3. **Main checkout fast-forward — STANDING, mine each time:** *"you check the content of main checkout and decide
   proper action at the time of the action. If necessary, defer the action if main checkout is currently in a critical
   path. if main checkout changes just cosmetic ones, just do it."*
   ⛔ `docs/memory/` in the main checkout IS the live auto-memory directory (`~/.claude/projects/<slug>/memory` is a
   symlink to it, found 11-13 03:50). Its "modified files" are mostly my memory writes — commit them through a PR,
   never reset them.
4. **PR #392 / migration 0028:** *"I approve you doing it"* — I may apply `0028_correction_allowance` to production
   myself, then merge on READY.

## History

- **03:48:** decision 5 was first *"prepare a list if suspected files for me to check"* — I prepared it; the owner did
  the check.
- **11:25 (cards):** A = SHIP REDACTED (ref, Fly URL, role names → placeholders), B and C = EXCLUDE, D = ship with
  quotes paraphrased. PR #582 merged with this answer; replaced at 17:15 (item 1).
