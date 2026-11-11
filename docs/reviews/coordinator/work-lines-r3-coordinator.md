# Round 3 — `work-lines` — coordinator — ✅ CONVERGED (6 Minor; 5 folded, 1 recorded)

```yaml
round: 3
fixes_nontrivial: true
subject: work-lines
halves:
  claude: ran
  codex: "GAP: alternation — Codex took r2, so r3 is the Claude half"
findings: [trailing-separator-serving, blank-serving-erases, one-separator-tested, cut-member-untested, md-directory-stops-page, symlink-naming]
```

REVIEW GAP: codex — alternation, per `review-method.md` -> Round topology step 4: Codex took round 2, so round 3 is the Claude half — a fresh subagent, not the coordinator that wrote the round-2 fold. Not a failure to run.

## Thrashing, or the prose floor? — asked because the next round is the fourth

**Prose floor, with one honest qualification.** The letter of the arming rule is met:
rounds 2 AND 3 each carry findings caused by the previous round's fix — r2's two Majors were in the
r1 fold, and r3's #1 (trailing separator), #3 (one separator tested) and #4 (cut member untested)
were in the r2 fold. But not in one component (`begin-plan.py` and `gen-work-lines.py` alternate),
and the CHARACTER fell sharply:

| Round | Blocking | Major | Minor | Fix-induced | What the fix-induced ones were |
|---|---|---|---|---|---|
| r1 | 1 | 4 | 5 | — | (first review) |
| r2 | 0 | 2 | 0 | 2 of 2 | real behaviour: one line split into three; an unrelated parent attached |
| r3 | 0 | 0 | 6 | 3 of 6 | one cosmetic regression (a trailing separator), two TESTS too weak |

r3's reviewer ran 200,000 random parent graphs against the delivered `build_forest` with zero
failures, and found the delivered behaviour correct everywhere it looked. A redesign would remove
none of the r3 findings — they are a regression in one boolean and two fixtures — so the
`can a redesign remove it?` test says this is not a design problem. Not convened.

⚠ What the table also shows, and is worth keeping: **every round's fix-induced findings were in
code the PREVIOUS fold wrote without a case that varied the input the fix was about** — `t` sorted
after the cycle, one separator, a short cycle. The repair that follows is the same each time: the
case must use the input that DISTINGUISHES the fix from the defect.

## Folded (`34aceb4f..` this round's commit)

1. `--serving` must equal its own `splitlines()` and be non-blank — closes #1 AND #2 (an empty
   `--serving` on re-arm can no longer erase the stored objective, because it is refused).
3. One case drives EVERY separator `splitlines()` honours (derived over the whole code-point range,
   10 of them), not one.
4. A three-node cycle entered from a tail pins the alphabetically-first-member rule; `cut = n`
   now reddens.
5. `read_plans` skips a non-file `*.md` (a directory, a broken symlink) instead of CANNOT RUN.

**Recorded, not fixed — #6:** a symlinked plan is named by its TARGET in `begin-plan` and by the
LINK in the generator. Neither claims anything false (the child would show its parent as missing),
plan files are not symlinked in practice here, and the fix would mean choosing which name is
canonical — a decision this round has no evidence for.

## Found by re-verifying, not by the reviewer

Re-applying every mutation this branch added showed the round-2 commit had **orphaned two of
round 1's entries** — both anchored on condition lines that fold rewrote. `check-plan-code
--self-test` passed throughout (it does not apply anchors); only CI's `--mutate` sweep would have
gone red. Re-anchored to distinct slices of the live conditions; all 22 of this branch's entries (15 in `gen-work-lines.json`, 7 in `begin-plan.json`)
across both manifests are killed by the case each names.
