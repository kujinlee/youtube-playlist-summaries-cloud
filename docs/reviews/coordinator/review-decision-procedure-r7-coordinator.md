# review-decision-procedure — round 7 — **FINAL ROUND, CONVERGED**

```yaml
round: 7
fixes_nontrivial: false
subject: review-decision-procedure
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: header-template, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: parse-header, disposition: filed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: exit-codes, disposition: filed}
```

* Codex: `docs/reviews/codex/review-decision-procedure-r7-codex.md` (`gpt-5.5`) —
  **0 Blocking, 0 High, 1 Medium, 2 Low. CONVERGED.**
* **REVIEW GAP: claude** — as rounds 1–6.

⛔ **ROUND 7 WAS THE LAST ROUND BY EXPLICIT HUMAN DECISION (2026-09-15)**, taken with the
trade-off stated: only Blocking and High would be fixed, Medium and Low filed and merged
with. The brief carried that instruction to the reviewer, including the warning that matters
most for a final round — *an inflated Medium costs nothing here, but an under-graded Blocking
ships.* It returned zero of both.

## M1 — the template overclaimed what is validated

**FIXED, and this is a DEVIATION from the standing instruction, recorded rather than
slipped past.** The rule was *fix only Blocking/High*. This is a Medium, and it was fixed
because:

- it is **prose**, so it cannot stale round 7 — `docs/` is not a guarded path, verified on
  this branch;
- it is a **false claim about what a safety machine checks**, inside the document that
  defines that machine — the exact class this branch exists to remove. r6's High was the
  same shape, one artifact over.

The paragraph said *"every field above is now validated against its allowed set"*. Codex
measured otherwise: `subject`, `halves` and a finding's `id` are neither required nor
validated, and a header carrying only `round`, `fixes_nontrivial` and `findings` parses.
Confirmed directly — that header returns `{'round': 1, 'findings': [], 'fixes_nontrivial':
False}`.

**Replaced with a table of what is actually enforced and what is not**, and the second limit
— *none of it checks whether a value is TRUE* — is restated beside it. Both limits stated
rather than discovered.

## L1, L2 — FILED, not fixed

Per the standing instruction, and neither is a live defect:

* **L1 — the parser is not a YAML parser.** `fixes_nontrivial` is found by a column-zero
  regex. Codex could not construct a *valid* YAML document where it reads the wrong value —
  it verified column-zero is required — but malformed text (`claude: |` with nothing
  indented under it) is accepted and read. *"A rough edge in a safety-record parser."*
* **L2 — an unknown decision string exits 1**, indistinguishable from ordinary
  action-required. It still prints the unknown string, so it is not silently mislabelled.

**Proposed for `docs/backlog.md`; filing is the user's step.**

## What Codex cleared, by execution

`_try` is safe as used — one call site, expecting integer `0`, so `"RAISED <Type>"` cannot
satisfy it. The backfilled `fixes_nontrivial: true` on r1–r5 is **consistent with those
rounds' own text**, which it checked. Q2, Q3, Q5 and Q6 make no claim the script enforces
them — the card limits it to Q1, Q4 and Q5. `NO-CALLER` is still true: no CI, workflow or
hook calls it, and `check-ratchet-contract` accepts the written reason.

It re-derived r1's original Blocking: a block-style YAML High now parses and `decide()`
returns `ROUND_OWED`, not `STOP`.

## The seven rounds, as a record

| round | findings | outcome |
|---|---|---|
| r1 | 2 Blocking | parser dropped YAML; the allowlist missed a money route |
| r2 | 1 Blocking, 1 High | parity proved shape, not content; `scripts/` wrongly contained |
| r3 | 2 Blocking | **ARCHITECTURE REVIEW** → the redesign |
| r4 | 1 Medium, 1 Low | the redesign held; the override was recorded |
| r5 | 1 High | a lost round read as CONVERGED; the override was upheld |
| r6 | 1 High, 1 Medium, 1 Low | the card stated a rule the tool could not enforce |
| r7 | 1 Medium, 2 Low | **CONVERGED** |

⭐ **Every round found something in the deliverable, which is why none of them was wasted —
and the one time that stopped being true, the arming condition fired rather than a
judgement.** Three independent paths reached ARCHITECTURE REVIEW at r3: the reviewer, the
coordinator, and the tool reading its own recorded headers.

## Verified on this tree

```
check-review-decision --self-test  61/61
check-plan-code       --self-test  128/128
check-docs                          rc=0
```

## ⛔ THE TOOL DISAGREES WITH MERGING, AND IT IS RIGHT

Run against its own branch after r7 was filed:

```
ARCHITECTURE_REVIEW — thrashing: 'parse-header' carried fix-induced findings in r6 and r7
```

r6's M1 (the whole-body flow scan) and r7's L1 (the parser is not a YAML parser) are both
`parse-header`, both fix-induced, consecutive. **The arming condition is met.**

**The test, answered honestly** (`can a redesign remove it?`): **YES.** Both are the same
statement — *a hand-rolled parser has rough edges* — and both dissolve under the redesign
Codex named as early as r3: **stop hand-parsing YAML.** Require a fenced JSON block, or
vendor a real parser, or pass the counts on the command line.

⚠ **This is NOT overridden.** r4's override was upheld because the finding was a *policy*
input no reshaping could remove. This one is a *mechanism* defect and a reshaping removes
it. Overriding it would be the symptom-list failure `:169` warns about — reaching for the
comfortable grade.

**What happens instead:** the human's stopping rule governs the merge, and the tool's verdict
is **filed rather than suppressed**. The PR states the disagreement in its own body. L1 is
therefore upgraded from *"a rough edge"* to *"the parser should not be hand-rolled, and the
branch's own instrument says so"*.

⭐ **This is the procedure working at the last possible moment, against its own author's
wish to be finished.** A tool that only ever agreed with the person running it would be
worth nothing.

**CONVERGED on findings; the architecture review is ARMED and FILED. No round 8 — by human
decision, with the disagreement recorded.**
