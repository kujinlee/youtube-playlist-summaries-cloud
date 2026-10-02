---
name: a-second-implementation-of-one-rule-drifts
description: "FIRES-WHEN: about to write a check, parser or split a script already owns — ⭐⭐ THIRTEEN INSTANCES — five in one session (2026-09-11, PR #289), SIX MORE in another (2026-09-14). A checker whose rule is WEAKER than its subject's reports a pass the subject REFUSES; a predicate testing for the BAD token's ABSENCE passes on empty output. Never approximate the rule — call the subject's own function, or run it. A scratch stand-in is CODE"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1a77c065-69d1-45d3-a26f-69d46b3fffeb
  modified: 2026-09-14T23:57:25.907Z
---

**When you need to know what a mechanism will do, RUN IT — do not re-implement its rules.**

⟳ **INSTANCE 2, 2026-09-08 (#91, PR #269), and the copy was WEAKER in a direction I never considered.** I hand-wrote a manifest sweep asking *"does this anchor resolve exactly once in the FILE?"* and it reported **375 edits, 0 problems**. The harness `load_manifests()` asks something STRICTER — *"is this anchor already used by ANOTHER ENTRY?"* — because two entries on one line measure the same site twice. **CI refused the manifest outright** (`NOT MEASURED — the mutation harness produced no coverage verdict`) over a manifest my check had just cleared.

⭐ The tell was available and I missed it: I could name the property I was checking, but not where the tool's version of it lived. **Ask the tool: `entries, problems = load_manifests(REPO)`.** One line, and it cannot drift. See also [[measure-the-population-the-code-actually-sees]].

⟳ **INSTANCES 3–7, 2026-09-11 (PR #289), FIVE IN ONE SESSION — and instance 7 is instance 2 AGAIN.**
Every one was a fast stand-in I wrote for a slow check, and every one kept the shape and dropped a
constraint:

| my stand-in asked | the subject asks |
|---|---|
| does ANY `expect` name a red case? (×2) | does EACH name match **exactly one**? |
| does this expression appear in an entry's anchor? | does an edit **change** it? (6 of 7 "green" rows were anchored-but-never-moved) |
| *(compared needles against escaped JSON, then against a real newline)* | the parsed anchors, the literal `\n` |
| printed `out[-800:]` of merged streams | …so 500 progress lines evicted the verdict — **the exact defect I was measuring** |
| orphaned anchors only | **plus duplicates** — the harness refused a manifest my verifier had just cleared |

⭐ **THE RULE: a checker whose rule is WEAKER than its subject's reports a pass the subject refuses.**
It cost two 7-minute runs, a false "15/15 covered", and a false green on an entry the real run
rejected. The fix is never a better approximation — it is to call the subject's own function, or to
run the subject. ⚠ And a stand-in is CODE: it deserves the same discipline, which is the exemption I
kept granting myself because it lived in a scratchpad.

## ⟳ INSTANCES 8–13, 2026-09-14 (PRs #300/#301) — SIX in one session, and a NEW sub-shape

Every one was a throwaway probe written to answer a question fast. None was in a scratchpad script;
they were one-off `python3 -` blocks and JS snippets, which is exactly why they felt exempt.

| my probe asked | the truth | how it was caught |
|---|---|---|
| regex for `EXPECTED_MUTATIONS` → **59 files / 3067** | `import` the module → **44 / 629** | the number was implausible |
| walked top-level siblings for tray items → **1 item, "ours absent"** | position-based scan → **11 items, ours PRESENT** | the user said "I don't see it" — then the opposite |
| `e["resolved"]` → `None`, "the 8 flags didn't register" | the field is **`resolves`** — all 8 were fine | printed `sorted(e.keys())` |
| scanned `t[:3000]` for `§N` → "17–24 missing" | window too small, and `§1–§7` is a RANGE it can't parse | read the actual line |
| `! grep -q "pending"` → **"CHECKS SETTLED"** | CI had **not started** (`no checks reported`) | `gh run list` disagreed |
| `grep -o ".{120}Could not read…"` → empty | `.` doesn't cross newlines; the count was 1 | asked for the class, got 0 |

⭐ **THE NEW SUB-SHAPE, and it is the dangerous one: a predicate written as "the BAD token is absent"
passes vacuously on empty output, an error message, and a typo'd command alike.** `grep -q done` and
`! grep -q pending` are not complements — they differ on exactly the inputs that matter. **Test for
the GOOD state positively, and treat "no data" as a THIRD state, never as success.** Written up as
`docs/portable-practices.md` §24 (PR #301) with the three-state predicate and a deadline that reports
`HANG` rather than "still waiting". See [[a-hang-is-not-a-diagnosis]] and [[a-check-result-is-not-the-claim]].

⚠ **The session-level tell: this happened while writing the explainer ABOUT this defect class.**
Knowing the rule, and having just committed a backlog row describing it, prevented none of the six.
Only running the real thing did. Two were caught by the USER, not by me.

Round 3 of PR #178 added `_close_orphan_markup` to close markup spans a title truncation had
orphaned. To decide which closers were needed I wrote a small scanner: toggle a stack on `**`,
toggle on `` ` ``. `_inline_scan`, the shipping renderer, has one rule that copy did not: **code
span content is literal**. So on `` `code ** tail `` the copy counted the `**` as bold and appended
a `**` closer, which then rendered INSIDE the `<code>` — a bare delimiter still on the page, plus
text the author never typed.

**Both reviewers found it independently** — the first time in four rounds they converged on one root
cause, which is itself a signal about how findable it was.

The fix was to **delete the copy**: candidate closers are now judged by running the real renderer and
comparing orphan counts. There is one implementation, so there is nothing to drift. A third scanner
with better rules would have been more of the same cause.

Sibling shape, same round: a guard asserting every `--out` path was absolute did it by matching
**source text** for a quoted literal. The suite has 5 such flags and **0** adjacent literals — every
call site passes `str(<Path>)`. Green because it could not look. See
[[assert-the-property-not-the-mechanism]] and [[a-convention-catches-what-you-read]].

## ⟳ SECOND INSTANCE, 2026-09-07 — I did it again, in the tool that CHECKS the tools

Writing mutation manifests, I built `<scratchpad>/verify_mutations.py` to avoid a ~5-minute CI cycle.
It re-implemented `check-plan-code`'s kill rule by parsing `[FAIL]` lines. **It ignored the exit code
entirely.** The real rule is `caught = rc == 1` (`check-plan-code.py:998`) — EXACTLY one, not
non-zero. My copy reported **6/6**; CI reported **2 survivors**; both were right about what they
measured.

The underlying defect was real and worth having: `check-paid-caller-arrival.self_test()` returned
`bad`, the COUNT of failing cases, so a mutation breaking 16 cases exited 16 and was recorded as a
survivor **while its named case sat in the red list**. The louder the failure, the less it counted.
Twelve sibling guards already returned 0/1; this one was alone. That is a FOURTH latent output
contract, binding only once a manifest points at a file.

⚠ **The shape to notice: the copy was built to check the checkers, and it was the one thing nothing
checked.** A speed shortcut around a slow verifier is a second implementation of the verifier.
If the real instrument is too slow to run whole, call ITS functions on a subset —
`m.run_mutations(d, mine, {target})` took seconds — rather than re-deriving its verdict.

## ⟳ THIRD INSTANCE, 2026-09-08 — and this one cost nothing, because the copy failed LOUD

Hunting the subject of an F7 baseline (`/tmp/v91/base/plan.txt`, which complains about untagged
```python blocks at 12 specific lines), I needed to know WHICH document `check-plan-code.py` would
emit that complaint set for. I wrote the fence rule by hand — `line.strip().startswith("```python")`
— and swept every `.md` in the repo and the scratch tree. **Zero matches, not even partial.**

I then imported the tool and ran its own `extract()` over the same corpus. **Exact match, all 12
lines:** `docs/superpowers/plans/2026-08-29-mutation-manifest-retarget.md`. Re-derived both baselines
from it: byte-for-byte identical, so F7 has a real control.

⚠ **The tell was a ZERO, and that is why this instance was cheap.** A copy that drifts by returning a
plausible-but-wrong answer gets believed; this one returned "nothing matches anything", which is not
a believable answer to "which file produced this output that a file produced". Compare the second
instance, where the copy said 6/6 and was trusted. See
[[measure-the-population-the-code-actually-sees]] — a zero count is the dangerous shape when you
believe it, and the useful shape when you do not.

**The cheap habit that fixed it:** the tool was importable. `importlib` + call `extract()` cost four
lines. Ask "can I just call it?" before "what are its rules?".

## And the part that is about ME, not the code

**I repeated a mistake the review had just described, one case above the one it described it in.**
The reviewer explained that the existing truncation case used `"x" * 40` — delimiter-free filler
that could never exercise the bug. I then wrote a new case with `"**a`b** " + "word " * 40`:
delimiters in the LEAD, so the cut lands in plain words, no closer is produced. It **SURVIVED the
mutation at 208/208**.

Reading a criticism of a specific case is not the same as applying it to the case you are about to
write. **When a review names a defect in test DATA, re-derive the data from the run that found the
defect** — the fuzz corpus, the repro input — rather than composing a tidy new example. The tidy
example is chosen by the same intuition that missed it the first time.

Related: [[after-fixing-search-for-the-class]],
[[a-mutation-loses-its-binding]].

---

## ⟳ INSTANCES 14–15, 2026-09-21 (PRs #327, #328) — **INSTANCE 2, TWICE, IN ONE MORNING**

Same manifest, same gate, same refusal text as instance 2. This file already told me the fix —
*"Ask the tool"* — and I wrote a stand-in anyway, then wrote a SECOND stand-in to repair the first.

    v1  checked nothing about distinctness  -> reported 6/6 KILLED on a manifest the gate REFUSED
    v2  compared the full (old, new) PAIRS  -> reported "45 distinct ✅" on a manifest it REFUSED
    the gate compares ANCHORS ONLY          -> check-plan-code.py:1093
                                               `tuple(f for f, _ in e["edits"])`

Two entries sharing an anchor with DIFFERENT replacements are distinct to v2 and identical to the
gate. ⭐ **v2 is the more instructive failure: I had just been burned, I set out to fix exactly this,
and I still paraphrased the rule instead of reading it.** Fixing the instance is not covering the
rule — [[a-filed-finding-s-proposed-fix-is-a-hypothesis]].

### ⭐⭐ THE NEW FACT, AND THE ONE THAT MAKES "JUST RUN IT" PRACTICAL

**I wrote stand-ins because the real gate takes ~50 minutes. THAT PREMISE IS FALSE, AND THE CI LOG
SAYS SO.** `check-plan-code.py --mutate .` validates the manifest FIRST and refuses in **under a
second** — measured, `15:06:26.1483` start → `15:06:26.2139` refusal. The expensive part runs only
AFTER validation passes.

So the cheap pre-check is the REAL GATE, invoked exactly as CI invokes it:

    python3 scripts/check-plan-code.py --mutate .   # in background
    # refusal within ~1s  -> manifest is bad, fix it
    # silence for 60s     -> manifest ACCEPTED, mutations now running

⭐ **Before writing a stand-in for a slow check, ask which PART is slow.** A gate that validates then
executes gives you its validation for free. I built two wrong re-implementations of a rule whose
real implementation was one background call away.

⚠ And when a stand-in genuinely is needed: **copy the subject's EXPRESSION with its file:line**, not
your reading of its intent. A paraphrase is a second implementation by definition.

⟳ **2026-09-22 — TWICE IN ONE SESSION, ON THE SAME TABLE ROW, AND THE OWNING RULE WAS ONE IMPORT AWAY.**
Editing `docs/backlog.md` row 100, I asked *"how many cells does this row have?"* with `awk -F'|'`
and got **9**; the answer is **8**, because a markdown table cell may contain an escaped `\|` and
`awk` cannot see escaping. I then wrote a Python `append_to_row` using `split("|")` — the same wrong
rule — which treated the `\|` I had just added as a cell boundary and **inserted the new text INSIDE
the previous correction**, splitting `` `str \| None` `` in half. The row had to be restored from
the index and redone.

⭐ **The repo OWNS the rule and says so out loud.** `scripts/gen-backlog-page.py:85-96` refuses to
re-implement it — *"Borrow the row splitter from the ratchet that owns it, so there is ONE definition
of where a table cell ends"* — and imports `check_docs.CELL_SPLIT`. A generator I had already read
during this same session was demonstrating the correct move while I made the wrong one twice.

**How to apply, concretely:** to split a backlog/roadmap table row, do

    spec = importlib.util.spec_from_file_location("cd", "scripts/check-docs.py")
    ...; cells = mod.CELL_SPLIT.split(line)

and to APPEND to a cell, locate the Nth-from-last **unescaped** pipe (`(?<!\\)\|`) rather than
splitting at all. Verify the cell count with `CELL_SPLIT` before and after — a row that changes cell
count is corrupted even when it renders plausibly.
