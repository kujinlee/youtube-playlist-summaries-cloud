---
name: a-second-implementation-of-one-rule-drifts
description: "FIRES-WHEN: about to write a check, parser, probe or split that a script already owns — a stand-in for a slow check, a quick python3 - probe, an awk/split over a table row. RUN the subject or CALL its function; never paraphrase its rule. 15 instances, 2026-09-07..09-22"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1a77c065-69d1-45d3-a26f-69d46b3fffeb
  modified: 2026-09-14T23:57:25.907Z
---

**The rule: when you need to know what a mechanism will do, RUN IT or CALL ITS OWN FUNCTION — never re-implement its rules.** A checker whose rule is WEAKER than its subject's reports a pass the subject REFUSES. A scratch stand-in or a one-off `python3 -` probe is CODE and gets the same discipline.

**How to apply:**
- **Ask "can I just call it?" before "what are its rules?"** — `importlib` the script and call `load_manifests(REPO)`, `extract()`, `m.run_mutations(d, mine, {target})`, `check_docs.CELL_SPLIT`. One line, and it cannot drift.
- **Before writing a stand-in for a slow check, ask which PART is slow.** `check-plan-code.py --mutate .` validates the manifest FIRST and refuses in under a second (measured `15:06:26.1483` → `15:06:26.2139`); only the mutation run is slow. Run the real gate in the background: refusal within ~1 s = bad manifest; silence for 60 s = accepted.
- **If a stand-in is genuinely needed, copy the subject's EXPRESSION with its location** (cite the symbol), not your reading of its intent — a paraphrase is a second implementation by definition.
- **Test for the GOOD state positively; treat "no data" as a THIRD state, never success.** `! grep -q pending` passes on empty output, an error message and a typo'd command alike (`docs/portable-practices.md` §24).
- **Table rows (backlog/roadmap):** split with `check_docs.CELL_SPLIT` (`(?<!\\)\|`, `scripts/check-docs.py`), never `awk -F'|'` or `split("|")` — a cell may hold an escaped `\|`. To append to a cell, locate the Nth-from-last unescaped pipe; verify the cell count before and after. `scripts/gen-backlog-page.py` already borrows the splitter for exactly this reason.
- **When a review names a defect in test DATA, re-derive the data from the run that found it** (the fuzz corpus, the repro), not a tidy new example chosen by the intuition that missed it.

**Why:** every stand-in keeps the shape and drops a constraint, and its pass looks exactly like the real one. Knowing this rule — even while writing the explainer about it — prevented none of the instances below; only running the real thing did.

## History (condensed)

- **2026-09-07, scratch `verify_mutations.py`:** re-implemented the kill rule by parsing `[FAIL]` lines and ignored the exit code; the real rule is `caught = rc == 1` (exactly one). Copy said **6/6**, CI said **2 survivors**. It surfaced a real defect: `check-paid-caller-arrival.self_test()` returned the COUNT of failing cases, so a louder failure counted less. *The copy built to check the checkers was the one thing nothing checked.*
- **2026-09-08 (#91, PR #269):** hand sweep "does this anchor resolve once in the FILE?" → **375 edits, 0 problems**; `load_manifests()` asks the stricter "is this anchor used by ANOTHER ENTRY?" and CI refused the manifest. Same day, a hand fence rule found **zero** matches while the tool's own `extract()` matched all 12 lines — cheap only because a zero is not believable.
- **PR #178 r3:** a hand scanner for `_close_orphan_markup` missed `_inline_scan`'s rule that code-span content is literal, appending a `**` inside `<code>`. Both reviewers found it independently. Fix was to DELETE the copy and judge closers by running the real renderer. Same round, a new case I wrote with delimiters in the lead SURVIVED the mutation at **208/208** — the exact defect the reviewer had just described one case above.
- **2026-09-11 (PR #289), five in one session:** "does ANY `expect` name a red case?" vs EACH-exactly-one (×2); "appears in an anchor" vs "an edit CHANGES it" (6 of 7 green rows never moved); needles vs escaped JSON; `out[-800:]` let 500 progress lines evict the verdict; orphans only, no duplicates. Cost two 7-minute runs and a false "15/15 covered".
- **2026-09-14 (PRs #300/#301), six one-off probes:** regex → **59 files / 3067** vs import → **44 / 629**; sibling walk → "1 item, ours absent" vs **11 items, ours PRESENT**; `e["resolved"]` vs the real field `resolves`; `t[:3000]` window too small; `! grep -q "pending"` → "CHECKS SETTLED" while CI had **not started**; `grep -o ".{120}…"` empty because `.` does not cross newlines. Two were caught by the USER.
- **2026-09-21 (PRs #327, #328):** v1 stand-in reported **6/6 KILLED**, v2 "45 distinct ✅", both on a manifest the gate refused — the gate compares ANCHORS ONLY (`tuple(f for f, _ in e["edits"])` in `check-plan-code.py`), v2 compared (old, new) pairs. v2 was written to fix v1 and still paraphrased.
- **2026-09-22, backlog row 100:** `awk -F'|'` said **9** cells (truly **8**), then a `split("|")` append inserted text inside the previous correction, splitting `` `str \| None` ``; the row was restored and redone.
- Sibling, PR #178: a guard checked `--out` paths were absolute by matching source text for a quoted literal — 5 flags, **0** adjacent literals; green because it could not look.

Related: [[measure-the-population-the-code-actually-sees]], [[a-hang-is-not-a-diagnosis]], [[a-check-result-is-not-the-claim]], [[assert-the-property-not-the-mechanism]], [[a-convention-catches-what-you-read]], [[a-filed-finding-s-proposed-fix-is-a-hypothesis]], [[after-fixing-search-for-the-class]], [[a-mutation-loses-its-binding]].
