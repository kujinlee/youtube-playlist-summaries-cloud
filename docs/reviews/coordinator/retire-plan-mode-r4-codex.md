# retire-plan-mode — code review round 4, Codex half

**Subject:** the r3 FOLD — `git diff f9d2c498..259dfa15 -- scripts/`, head `259dfa15`.
**Model:** gpt-5.5 (forced). **Verdict JSON:** `docs/reviews/verdicts/retire-plan-mode-r4-codex.verdict.json` — `gate_ran: true`.

**Verdict:** 1 Low. No Blocking, High or Medium.
⭐ This half ran the FULL `--mutate .` sweep — `33 file(s), 390 mutation(s), 0 survivor(s)` —
which the Claude half declared CANNOT RUN and substituted a targeted pass for. Between them the
manifest is verified both ways.

---

<!-- codex-review: model=gpt-5.5 -->

`git rev-parse HEAD`
```text
259dfa15816fecd03ffc22329b8ab3f7ca409e08
```

`git log --oneline -1`
```text
259dfa15 Fold round 3 — the inert discriminator gets a consumer, not a deletion
```

`git diff --stat f9d2c498..259dfa15 -- scripts/`
```text
 scripts/check-plan-code.py                  |   6 +-
 scripts/check-plan-file-tags.py             | 195 ++++++++++++++++++++++++----
 scripts/mutations/check-plan-file-tags.json |  42 ++++--
 3 files changed, 204 insertions(+), 39 deletions(-)
```

**Findings**

Low — [scripts/check-plan-file-tags.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-file-tags.py:27) says “19 documents on 2026-09-09 mention `<!-- file: … -->` inside backticks”, but the 19 is the broader mention count, not the backticked count. Observation: `rg -l --pcre2 --glob '*.md' -e '`<!--\s*file:[^`]*-->`' docs | wc -l` returned `15`; `rg -l --pcre2 --glob '*.md' -e '<!--[^`\n]*file[^`\n]*-->' docs | wc -l` returned `19`. The four extra files are non-backticked mentions. The code behavior is not affected, but this is another stale/misdescribed measurement in the explanatory contract. I would change the prose to say 19 documents mention the grammar, with only 15 of those inside backticks, or drop the number.

**Checks Run**

`python3 scripts/check-plan-file-tags.py --self-test` -> `43/43 self-test cases passed`.

`python3 scripts/check-selftest-counts.py` -> `self-test counts: 30 script(s) declare a count, every one verified by running it`.

`python3 scripts/check-plan-code.py --self-test` -> `229/229 passed`.

`python3 scripts/check-plan-code.py --mutate .` -> `OK — delivered scripts mutated: 33 file(s), 390 mutation(s), 0 survivor(s)`.

I also ran a temp-file manifest pass over all 16 `check-plan-file-tags.py` mutations. Every entry hit its expected `[FAIL]`, reached a self-test summary, and produced no traceback, including the retargeted r2-H1 mutation and the two new remedy-branch mutations.

`_drive_main()` restore was tested by monkeypatching `main()` to raise: output was `raised boom`, `root_restored True`, `docs_restored True`. Sequential `_drive_main()` calls also restored globals between cases. The `any(not f.unreadable for f in findings)` branch matches the reachable mixes: tag-only gets backticks, unreadable-only gets NOT CHECKED, mixed gets backticks, clean bypasses the branch. A tag marked unreadable would choose the unreadable message, but the producer invariant is pinned by the existing “TAG finding is not marked unreadable” case and the full mutation run.

Final `git status --porcelain` was clean.

---

## COORDINATOR ADJUDICATION of Cx-L1 — UPHELD, and it is worse than reported

The docstring says *"**19 documents on 2026-09-09** mention `<!-- file: … -->` inside backticks"*.
Codex is right that 19 is not the backticked count. Re-measured with three predicates:

    A  a backtick BEFORE the tag on the same line (the coordinator's) : 19
    B  the tag fully ENCLOSED in a code span                          : 18
    C  mentions the tag at all, in any form                           : 19
    (Codex's stricter enclosed form, via ripgrep)                     : 15

**No two predicates agree, and the sentence names none of them.** The number was never going to be
right — which is the actual finding. It has now produced a review finding in TWO CONSECUTIVE
ROUNDS (r3 C2 said 13→17; r4 says the predicate is wrong) while the code it describes has been
correct throughout.

**Disposition: DROP THE NUMBER.** The load-bearing claim is qualitative — *documents discuss this
grammar in backticks, and every one must keep passing* — and that is already pinned by four
self-test cases taken verbatim from real repo lines. A count that changes whenever anyone writes
about the grammar, and whose value depends on an unstated predicate, is a liability in the one
place whose job is to be exactly right. Correcting it a third time would be the third instance of
the same class.

# DISPOSITION — folded 2026-09-09

**Cx-L1 — ACCEPTED, and resolved by DELETING the number rather than correcting it a third time.**

The sentence has now been wrong three ways: "13 documents" (undated, stale), "19 documents on
2026-09-09" (dated, but naming a predicate nobody shares), and — per this finding — a value that
depends entirely on how "inside backticks" is read. Three measurements, three answers: 19 / 18 / 15.

The header now says explicitly that there is deliberately no count, lists all three predicates and
their disagreeing answers, and states **"Do not reintroduce a count here."** The claim that actually
matters — every document discussing the grammar must keep passing — is asserted by four self-test
cases copied verbatim from real repo lines, which is a falsifier rather than an arithmetic claim.

⭐ Codex's full `--mutate .` run (`390 mutation(s), 0 survivor(s)`) was the stronger half of this
round's verification: the Claude half declared that CANNOT RUN and substituted a targeted pass.
Neither alone would have covered both the manifest and the other 32 files.
