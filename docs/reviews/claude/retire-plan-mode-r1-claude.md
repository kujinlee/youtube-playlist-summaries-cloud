# retire-plan-mode — code review round 1, Claude half

**Subject:** commit `71f86f9a` on branch `retire-plan-mode` (7 files, +604/−41).
**Verdict:** NOT CONVERGED — 1 High, found and fixed in this round. 2 Medium accepted as designed.

**REVIEW GAP:** codex — dispatched via `scripts/codex-review.py --prompt-file` and produced a
**0-byte** output file; a hang under `docs/plugins.md`'s bounded-wait rule, so the fallback applies
and this Claude adversarial pass ran in its place.

⚠ That is a Codex **gap**, not a clean Codex verdict, and it must be re-attempted before merge.
This repo has four recorded instances of the two halves disagreeing with the second half right —
most recently backlog #91 round 4, where Codex CONVERGED and Claude found the High. Here the
asymmetry runs the other way, which is exactly why the missing half still matters.

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
