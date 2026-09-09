# retire-plan-mode — code review round 1, Claude half

**Subject:** commit `71f86f9a` on branch `retire-plan-mode` (7 files, +604/−41).
**Verdict:** NOT CONVERGED — 1 High, found and fixed in this round. 2 Medium accepted as designed.

✅ **THE GAP IS CLOSED — the Codex half RAN on the second dispatch.** See
`docs/reviews/coordinator/retire-plan-mode-r1-codex.md` (`gate_ran: true`, gpt-5.5). What follows
is kept as the record of the first attempt, not as a live gap.

⭐ **AND IT FOUND A HIGH THAT THIS HALF MISSED** — `DOCS` is read by `main()` but by no case, so
narrowing the corpus left both the live run and the suite green while 220 documents went unread.
Re-measured and confirmed by me on HEAD before fixing. **Fifth recorded instance of *dual halves
are not redundant*, and the first where the half that would have been skipped is the one that
caught the defect.** Had I merged on the Claude half alone, that hole would have shipped.

The wrapper walked its whole candidate list and refused to write a review file rather than write an
empty one — behaving exactly as designed. Recorded in
`docs/reviews/verdicts/retire-plan-mode-r1-codex.verdict.json` (`gate_ran: false`, `exit_code: 1`),
which is the machine-readable half CI reads:

    gpt-5.6-sol    HTTP 400
    gpt-5.6-terra  HTTP 400
    gpt-5.6-luna   HTTP 400
    gpt-5.5        timed out — a partial message is an incomplete review

The one sanctioned retry was taken: `codex-frontier-model.py --write-config` re-synced to
**`gpt-5.6-sol`** — the same slug that 400s — which is the limitation its own docstring states (it
ranks by `priority` and cannot know what the pinned CLI accepts). Beyond that, `docs/plugins.md`
says do not burn time retrying. **`gpt-5.5` is the live lead: it timed out rather than 400'd, so it
is reachable and merely slower than the wrapper's timeout.**

⚠ **This is an ABSENT reviewer, not a clean Codex verdict, and it should be re-attempted before
merge.** This repo has four recorded instances of the halves disagreeing with the second one right —
most recently backlog #91 round 4, where Codex CONVERGED and Claude found the High. Here the Claude
half found an H1; that says nothing about what Codex would have found.

⚠ **A correction to my own reading, recorded because it is the repo's own recorded hazard.** I first
read this run as a success from an `rc=0`. That `0` came from an `echo "rc=$?"` after a pipe to
`tail` — `$?` after a pipe is the LAST command's, not the wrapper's. The wrapper's real exit was
**1**. Trust the verdict JSON and the output FILE, never a shell `$?` taken through a pipe.

---

## H1 — BLOCKING-adjacent, CONFIRMED BY MEASUREMENT, FIXED IN THIS ROUND

**The fence used `splitlines()`; the parser it fences uses `split("\n")`. They disagree in the
direction that HIDES a live tag.**

`check-plan-file-tags.audit` iterated `text.splitlines()`. `check-plan-code.extract` iterates
`md.split("\n")`. `splitlines()` additionally breaks on **nine** separators:

    \v  \f  \x1c  \x1d  \x1e  \x85        \r

That is not cosmetic. A separator immediately before a ``` sequence opens a fence in the guard that
never opens in the parser — so a tag on the following line is skipped as "fenced" while `extract()`
assembles it.

**Measured**, input `x<SEP>```\n<!-- file: m.py -->\n```python\nV=1\n``` `:

| SEP | `extract()` | fence findings | |
|---|---|---|---|
| `0xb` `0xc` `0x1c` `0x1d` `0x1e` | `['m.py']` | **0** | ✗ DISAGREE |
| `0x85` `0x2028` `0x2029` | `['m.py']` | **0** | ✗ DISAGREE |

Eight of eight in the dangerous direction. The guard's entire premise is *"the fence and the parser
must agree on what a tag is"* — and it was built on an imitation of the parser's line rule rather
than the rule itself. This is the **third recorded instance** of that shape in this repo.

**Fix:** `text.split("\n")` — the parser's own splitter. Re-measured after the fix: **0
disagreements across all nine separators**, over the file *both* consumers actually read.

⚠ **My first re-measurement reported `\r` still disagreeing, and that was a defect in the TEST, not
the code.** `read_text()` performs universal-newline translation, so I was feeding `extract()` a raw
string while the fence read a translated file — comparing two different inputs and calling it a
divergence. Corrected by routing both sides through the same `read_text()`. Recording it because a
false finding accepted here would have driven a fix to code that was already right.

**Cases:** +8, one per separator, pinning the class rather than the instance noticed first
(21 → 29). **Mutation:** +1 reverting to `splitlines()`, red via the `0xb` case
(`EXPECTED_MUTATIONS` 8 → 9, sum 382 → 383).

---

## M1 — ACCEPTED AS DESIGNED: the fence is stricter than the parser on `~~~` fences

`extract`'s `FENCE` only matches backtick fences, and so does the guard's — they agree. But
CommonMark also allows `~~~`. A tag inside a `~~~` block is flagged by the guard and would also have
been assembled by `extract` (neither treats `~~~` as a fence), so **the two still agree**, which is
the property that matters. No change. Noted so the next reader does not "fix" it into a divergence.

## M2 — ACCEPTED: the duplicated regexes are a real second implementation

`FILE_TAG`, `MUT_TAG` and `FENCE` are hand-copies of `check-plan-code`'s, and this repo has measured
that a second implementation of one rule drifts — H1 above IS that drift. Importing was rejected
because PR 2 deletes the originals, which would break the fence exactly when it becomes the only
definition left. **The mitigation is the case set**: leading-whitespace accepted, trailing prose
rejected, all four fence branches, and now all nine line separators — every one taken by running
`extract()`, not by reading it. Stated as a live risk rather than resolved.

---

## Checks that came back clean

- **Falsifiability.** The live baseline is 0 findings over 1,115 documents. All 9 mutations go red
  via the case each names, over a control proved green first — no mutation leaves both the suite
  and the live run green.
- **Empty-corpus rc=2** fires: `audit(empty) == ([], 0)` and `main` refuses it.
- **The refusal.** `grep` over hooks, CI, `scripts/`, `.claude/` and `.agents/` finds no surviving
  caller of a retired form. `--mutate` is not caught by the refusal net (presence twin), and a bare
  invocation still exits 2, never 0.
- **Counts.** 383 = sum of `EXPECTED_MUTATIONS`, verified by running; docstrings 229 and 29 verified
  by `check-selftest-counts.py` (30 scripts).
- **No collateral.** `check-ratchet-contract` discovers 29 guards including the new one and passes
  R1/R2/R3/R4; `check-docs` green with `dev-process.md` at 219/220.

---

# Round 1, CODEX half — dispositions (coordinator)

Filed at `docs/reviews/coordinator/retire-plan-mode-r1-codex.md`. Every claim below was
RE-MEASURED by the coordinator before acting; an agent's output is a lead, not a finding.

| | Codex severity | Disposition |
|---|---|---|
| `splitlines()` vs `split("\n")` | Blocking | **Already fixed** in `92b2b362`. Codex reviewed `71f86f9a`, so it independently rediscovered the Claude half's H1 — same defect, same nine separators, same dangerous direction. Two reviewers converging on one measurement. |
| `DOCS` narrowing is undetectable | High | **CONFIRMED and FIXED.** See below. |
| the `--mutate` combination refusal cannot fire | Low | **CONFIRMED; comment corrected, behaviour unchanged.** |

## Cx-H1 — the corpus SELECTION was unguarded (CONFIRMED, FIXED)

`DOCS` is read by `main()` and by no case — every case drives `audit()` on a temp root. So a
mutation narrowing it is invisible. Coordinator re-measurement on HEAD `fceecdfa`, monkeypatching
`ft.DOCS` to `docs/reviews`:

    live run    rc=0   "plan-mode tags: 0 across 896 documents under docs/"   (vs 1116)
    --self-test rc=0   "29/29 self-test cases passed"

Both green while 220 documents went unread — **including all 92 plans, which are the actual
subject of the fence.** I had built the empty-corpus rc=2 clause believing it closed the
"zero over nothing" hole. It refuses a corpus of *nothing*; it says nothing about a corpus of
*something smaller*, and narrowing produces the latter. The clause I was most confident in was
guarding the case that could not happen.

**Fix:** `coverage_shortfall(docs_root, scanned)` — `main()` refuses rc=2 unless `scanned`
equals the document count under `ROOT / "docs"`, a root re-derived by the CALLER. That
asymmetry is the mechanism: mutating `DOCS` moves what `audit` reads and not what this counts,
so the two disagree. Falsifier re-run after the fix: narrowed `DOCS` → **rc=2, "read 896 of
1116"**. Cases 29 → 33 (including a presence twin, so an always-fires comparison is caught too);
mutations 9 → 11.

## Cx-L1 — an unreachable refusal described as reachable (CONFIRMED)

The retirement gate returns before the `--mutate`-combination check, so `--mutate ROOT --evidence`
gets the generic retirement sentence. Coordinator re-measurement: both `--mutate … --evidence`
and `--mutate … --compare` return rc=2 with the RETIREMENT message; the combination message is
unreachable. Behaviour is fail-closed and correct — the defect was the **comment**, which implied
a specific refusal a caller can still reach. Corrected in place; the guard is kept because the
deletion slice removes the flags, and removing the guard first would leave a window with neither.

## Codex's own CANNOT RUN, recorded rather than glossed

It could not complete `--mutate .` (two attempts, both interrupted, the second inside
`run_mutations`). That is exactly the check that caught the orphaned mutation, and Codex was
right to report it as not-run rather than infer a result.
