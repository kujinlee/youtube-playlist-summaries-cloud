# review-loop-batch1 — round 3 — Claude half

Subject: `git diff origin/master...HEAD` on `fix/review-loop-batch1`, head `c659055c`. Merge base is
`e916edeb` (= current `origin/master`). Reviewed the whole branch fresh, under a REFUTE mandate.
I wrote nothing except this file. Mutations and corpus runs used `git archive` copies under
`scratchpad/r3rev/`.

## What I ran (all on the head tree)

| Check | Result |
|---|---|
| `check-review-decision.py --self-test` | `118/118 self-test cases passed` |
| `check-review-rounds.py --self-test` | `90/90 self-test cases passed` |
| `check-review-rounds.py` (live audit) | `472 parsed, 18 pre-existing exemptions, 0 silent gaps` |
| `check-plan-code.py --self-test` | `215/215 passed` (this includes the `sum(EXPECTED_MUTATIONS) == 2003` case) |
| `check-selftest-counts.py` | `59 script(s) declare a count, every one verified by running it` |
| `check-docs.py` | `Documentation integrity OK` |
| `check-backlog-closure.py` | WARN, `#339: MERGED but its row does not carry ✅`. See L1 |
| Manifest vs `EXPECTED_MUTATIONS`, recounted independently over every `scripts/mutations/*.json` | sum 2003 = 2003, zero per-file mismatches. `check-review-decision` 30, `check-review-rounds` 36 |
| Anchors in both touched manifests | all 66 resolve exactly once |
| Each new or re-pointed #318/#339 mutation, applied by hand to a temp copy (`HOME` redirected) | all 6 go red (rc=1), and the named `expect` case is among the failures in every one |

## Mandate items

**a. backlog #306.** I spot-checked the backfilled fields against their sources:
- r3 `halves.claude` quotes the Codex half's own `REVIEW GAP` line (`codex/…-r3-codex.md:4`, *"single-reviewer round BY CONSTRUCTION"*), word for word.
- r3 L1 and r5 L1 are the masking-pair Lows (`r3-codex.md:16`, `r5-codex.md:22`).
- `decide` reproduces exactly as recorded. My own import of `rounds_for('chrome-bar-reachable')` gives `[(3, 6), (5, 8), (6, 9)]`, and `decide` returns `('CANNOT_RUN', 'rounds are not gapless: found [3, 5, 6], expected [1, 2, 3] — refusing to infer adjacency from list position')` in both `full-loop` and `one-round`.

CANNOT RUN is the right behaviour: inferring adjacency across missing rounds would invent the counter the procedure exists to read. The row states the remainder truthfully: it is a decision, not a backfill, the falsifier's "15 of 15" is unreachable as written, and rc=2 must not be read as "no thrashing". I found no invented value. Two fields are judgements, and both are flagged as such in their provenance sections: r6 claude-M1 `aim: deliverable`, and the literal-wording `fix_induced: true` on r3 L1 and on the within-round r6 findings (the latter filed as backlog #347).

**b. backlog #318.** Adding `refuted` is the row's own WORK ("add `refuted` to the enum with its meaning stated"). Fixing the documents instead is what the row warns against. I ran the corpus before and after: `rounds_for` + `decide` (both scopes) over every subject with a coordinator document, master copy vs head copy. The diff has exactly three lines:
- `chrome-bar-reachable`: REFUSED → PARSE (CANNOT_RUN). This comes from #306, not #318.
- `ship-src-root-alone`: still REFUSED, now at `H1 … 'redesigned'` instead of `L4 … 'refuted'`.
- `review-loop-batch1` appears, because this branch added its own subject.

**No other subject's verdict changed.** The row states that `redesigned`/`retreat`/`moot` are still refused, and that is true.

**c. backlog #339.** `PAIRING_RULE` is appended only at the solo-half problem line, and only when `key[1] > 1`. A round 2+ solo half with a `REVIEW GAP:` line produces no problem, so it never sees the hint. A round-1 solo half does not get it either: the case exists, and the `> 0` mutation kills it. The hint can over-fire on a round 2+ half whose partner is still in flight. The code comment states this, and it is harmless because the failure itself is correct. The row is now honestly PARTLY / NEEDS-OWNER, not CLOSED. Its falsifier ("the gate must name the pairing rule") is met in the neutral form the r1 fold chose.

**d.** Covered in the table above.

**e. Neutrality.** `review-method.md` step 4, the `plugins.md` sentence, the `PAIRING_RULE` text, the dashboard entry and the #339 row all present the two readings without choosing one. The only place that still states the pair reading as settled is a commit message. See L1.

**f.** `d2e5db17` adds both the `"a finished document is exempted like a fragment"` mutation and `_is_document(page)`. `4f4e2748` adds `"the pin selector must touch the brace again"` and the r4 grouped-selector case. Both corrected `fix_induced: true` values match git.

**g.** No added line refers to a `#345` meaning this row. The one mention says the row was renumbered *from* 345. Master has no row 345.

**h.** `git diff origin/master HEAD -- docs/backlog.md` touches only rows 306, 318 and 339, and adds 347.

## Findings

### L1 — Low — commit `4950d352`'s subject still settles #339 and carries its closing tail

- **Input:** `python3 scripts/check-backlog-closure.py` on the head.
- **What happens:** `⚠ #339: MERGED but its row does not carry ✅` — *"A review round is a PAIR: alternation orders its two halves, and the round check now says so (backlog #339)"*.
- **Why it matters:** the subject asserts the pair reading, which the r1 fold withdrew. Its `(backlog #339)` tail is the closing token, but the row is now PARTLY / NEEDS-OWNER, so the guard warns.
- **Scope:** the guard is warn-only. Master's history shows squash merges (`(#NNN)` subjects), so only the PR title reaches master.
- **Fix:** the PR title must neither carry a `(backlog #339)` tail nor state the pair rule. No rewrite of branch history is needed.

### L2 — Low — `docs/backlog.md` row 318: absolute corpus counts name no base, and are stale after the master merge

- **What the row says:** *"31 subjects; 17 → 18 parse and 14 → 13 refused … Of the 18 that parse, 6 still `decide` CANNOT_RUN"*.
- **Where those numbers come from:** they were measured at `92c78bff` (the implementer's report says so; the row does not).
- **What I measured at the current base and head:** master copy 33 subjects, 19 parse, 14 refused. Head copy 34 subjects (this branch adds its own), 21 parse, 13 refused. Of the 20 that parse excluding this branch's own subject, 7 return CANNOT_RUN.
- **Unchanged:** the delta and the attribution (one gained, by #306).
- **Fix:** say "measured at `92c78bff`", or drop the absolute counts and keep the delta. The repo's *qualify every number* rule asks for one or the other.

### L3 — Low — `docs/review-method.md` step 4: "its failure line names both" omits round 1

- **Status:** a nit.
- **What happens:** the doc says the failure line names both readings. It does so for rounds 2+ only, by design.
- **Fix:** "its round 2+ failure line names both".

Nothing at Medium or above. All three Lows are wording or provenance. None changes a verdict, a gate or a header value.

VERDICT: CONVERGED
