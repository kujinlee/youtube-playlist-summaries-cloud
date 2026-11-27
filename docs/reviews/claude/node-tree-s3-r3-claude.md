# Round 3: `node-tree-s3`, Claude half (NOT CONVERGED)

**Subject:** the round 2 fold, `git diff dcbaa53f 7a83d09c`. It changes `scripts/check-features.py`, its mutation manifest and the pin. **Tree:** HEAD `735f306e`, worktree `node-tree-s3`.

## What held

- **The real tree passes.** `python3 scripts/check-features.py` exits 0 and reports 45 nodes, with 29 backlog areas each claimed once. `docs/goal-threads.md` has no PRIORITY line today, so `priority_order` returns None, the same as before the fold. The one place its preamble describes the format (line 31) starts with `- `, so it is never read as an attempt.
- **No valid declaration is newly refused.** Every string that `PRIORITY_LINE` matches also matches the first branch of `_PRIORITY_ATTEMPT` (`\d{4}-\d{2}-\d{2} "`), so the fold cannot turn a valid line into a refusal.
- **Self-test:** 130 of 130 cases pass, which matches the docstring's 130.
- **Mutations:** on a scratch copy built with `git archive HEAD`, `check-plan-code.py --mutate . --only scripts/check-features.py` reported 79 mutations, 79 killed, 79 attributed to the case each names, and 0 survivors.
- **Anchors:** I applied each of the 6 new and 3 re-bound PRIORITY mutations by hand to a second copy. Each one fails exactly the cases it expects. All 79 anchors appear exactly once in the source.
- **Pin:** `expected_mutations.py:1813` says 79, and the manifest has 79 entries.
- **No gate is loosened:** the fold only makes the attempt test match more lines, never fewer, apart from the defects below.

## Findings

### H1: MINOR, fix_induced: **yes** (caused by the r2 fold). Prose containing ` · ` is now refused.

`scripts/check-features.py:522`, `.* ·(?: |$)` branch, at the call site `:578`.

- **Failing input:** `PRIORITY is decided by the owner · see ADR-0010.` in the preamble. It is refused as a malformed declaration with the message "a PRIORITY line is written ONCE …". That message is also misleading here.
- **Before the fold:** round 1's `_PRIORITY_START` accepted this line as prose, because `\S+ "` does not match `is d`. So the fold caused this.
- **This is the class of G1 in round 2:** prose wrongly refused. The fold's comment (`:515`) says the separator is "a part prose never does in that place". That is false in this repo. The middle dot is the house separator in prose: `docs/goal-threads.md` alone has 151 lines containing ` · `, and its own preamble prose (line 20) uses it.
- **Severity:** MINOR rather than NIT, matching G1. The failure is loud, so nothing is lost in silence. A related input, `PRIORITY 2026-11-12 "dev speed first" was the owner's call.`, is refused too, but round 1 refused it as well, so it is not caused by the fold.
- **Proposed fix:** see the recommendation below. Any intent-guessing regex trades one of these cases for another.

### H2: MINOR, fix_induced: no (round 1 caused it; the r2 fold claims to close it and does not). A separator directly after the word is ignored in silence.

`scripts/check-features.py:522`.

- **Failing input:** `PRIORITY · a > b` is accepted as prose, so the ranking is dropped in silence. `PRIORITY ·` and `PRIORITY · see below` behave the same way.
- **Cause:** the literal space after `PRIORITY` is consumed before `.* ·`, and that branch needs a second space before the `·`.
- **Contradicts its own documentation:** the comment at `:516-517` says a line with the separator, "anywhere", "is never dropped in silence". Row 12 (`PRIORITY tomorrow · a > b`, refused) is meant to pin exactly this case, but the case with no date token escapes it.
- **Narrow fix:** `^PRIORITY(?: \d{4}-\d{2}-\d{2} "|.* ·(?: |$))`, which moves the space inside the date branch. Add a table row for `PRIORITY · a > b` → refused.

### H3: NIT, fix_induced: no. Other near-miss declarations are ignored in silence, beyond row 15.

All of these are accepted as prose, so their ranking is dropped without a word:
- `PRIORITY someday "w" ·a`: no space after the separator, and no date.
- `PRIORITY 2026/11/12 "w" a > b`: a slash date and no separator.
- `PRIORITY 2026-11-12 “w” a > b`: curly quotes and no separator.
- `PRIORITY: 2026-11-12 "w" · a`, `Priority 2026-11-12 "w" · a`, `  PRIORITY 2026-11-12 "w" · a`, and `PRIORITY<TAB>2026-11-12 "w" · a`.

**Where these came from:**
- The colon, tab and indented forms have been silent since round 1 required the literal `PRIORITY ` with a space. Round 0's `startswith("PRIORITY")` refused the colon and tab forms.
- The slash-date and curly-quote forms are the row 15 bound, but the comment's bound at `:521` names only "an undated, separator-less line".

**Proposed fix:** the recommendation below removes all of these. Failing that, state them in the bound.

## Is this the third consecutive fix-induced round in check-features?

**Two in a row, not three, and two is the arming condition.**
- Round 2's G1 and G2 were caused by round 1's F1 fix.
- Round 3's H1 is caused by round 2's fold: the same input passed under round 1's regex and is refused under round 2's.
- H2 and H3 come from round 1, not round 2.

That makes two consecutive rounds with findings caused by the previous round's own fix, in one component (`check-features`, the PRIORITY attempt test). That is the **THRASHING** shape, so per `docs/dev-process.md` Phase 6 arms on this component. This is also r3; from r4 the round cap files every non-BLOCKER.

**Can a redesign remove it? Yes.** Every round has fixed the same unbounded question, "does this prose-looking line intend to be a declaration?", with a better guess, and each guess moves the boundary to a new place.

The structural fix is to stop guessing:
1. **Change the rule.** In the preamble, a line whose first word is `PRIORITY` is the declaration, and it must match `PRIORITY_LINE`. That means `^\s*\**PRIORITY\b`, ignoring case, after optional whitespace or Markdown emphasis.
2. **Document it.** Add one sentence to `docs/goal-threads.md` line 31: "a preamble line never begins with the word PRIORITY unless it is that line."
3. **Swap the tests.** Retire the 15-row table's prose-accept rows in favour of "prose starting with PRIORITY is refused, and the message says to reword".

The cost is round 1's F1, which was a Claude MINOR about a loud refusal of prose, a harmless false positive. In exchange, every silent drop (H2, H3, row 15) becomes loud, and H1's question disappears. A loud, occasionally annoying refusal is the right side of this trade for a field whose only failure mode that matters is a silently discarded owner decision.

## Verdict

NOT CONVERGED: H1 (MINOR, fix-induced, prose with ` · ` refused), H2 (MINOR, `PRIORITY · a > b` dropped in silence), H3 (NIT, near-miss forms dropped). The component is thrashing; I recommend the first-word redesign over a fourth regex.
