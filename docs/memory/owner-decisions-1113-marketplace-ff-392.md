---
name: owner-decisions-1113-marketplace-ff-392
description: "FIRES-WHEN: marketplace decision 5 or 7, the main-checkout fast-forward, or PR #392's migration 0028 comes up. Owner's inline answers 11-13 03:48: copyright = Kujin Lee; prepare a suspect-file list for the corpus review; I decide the ff myself; I may apply 0028 to prod. Decision 5 FINAL 11-13 17:15: A+B+C exclude, D paraphrased + anonymized (essence only)."
metadata:
  type: project
---

Owner's inline decisions, 2026-11-13 03:48 (on my owed-items table):
1. **Walkthrough decision 5 (corpus content review):** "prepare a list if suspected files for me to check". I prepare it; the owner still does the check, so decision 5 stays open until they answer.
2. **Walkthrough decision 7 (copyright holder):** "use my name \"Kujin Lee\"". DECIDED: the license names Kujin Lee.
3. **Main checkout fast-forward:** "you check the content of main checkout and decide proper action at the time of the action. If necessary, defer the action if main checkout is currently in a critical path. if main checkout changes just cosmetic ones, just do it." STANDING: I decide each time.
   ⚠ Found 11-13 03:50: `docs/memory/` in the main checkout IS the live auto-memory directory (`~/.claude/projects/<slug>/memory` is a symlink to it). So the "owner's modified files" there are mostly MY memory writes, and discarding them would delete memory. They get committed through a PR, never reset.
4. **PR #392 / migration 0028:** "I approve you doing it". I may apply `0028_correction_allowance` to production myself, then merge on READY.
5. **Decision 5 ANSWERED 11-13 11:25 (cards, per group of `docs/marketplace/decision-5-suspect-files.md`):** A (production infra) = SHIP REDACTED (ref, Fly URL, role names → placeholders); B (business/costs) = EXCLUDE; C (local machine) = EXCLUDE; D (owner's words) = SHIP WITH QUOTES PARAPHRASED (keep the rules, neutral wording). The ~170 other lesson files ship. Redaction + paraphrase happen when the corpus is built, and each needs a check.
6. **⟳ Decision 5 REPLACED 11-13 17:15 (asked on the walkthrough page):** "Suggested default: ship no file in A–C … I will take this suggestion. For D, paraphrase and anonymize the quote. Only convey essence of the example and not specifics." So A is now EXCLUDED too (not redacted); D ships with each quote paraphrased and anonymized, essence only. This replaces item 5. Recorded on master by PR #583 (20310a55), after #582 had merged with the 11:25 answer.
