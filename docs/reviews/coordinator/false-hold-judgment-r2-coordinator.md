# Round 2 — `false-hold-judgment` (backlog #508) — coordinator — ⟳ NOT CONVERGED (Codex); folded

Codex ran on `358a3220` and returned NOT CONVERGED with 5 MAJOR and 1 MINOR findings, each with a reproduction.
REVIEW GAP: claude — alternation

```yaml
round: 2
fixes_nontrivial: true
subject: false-hold-judgment
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: scripts/codex-review.py, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: true, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: true, component: scripts/codex-review.py, disposition: fixed}
  - {id: X5, severity: High, aim: deliverable, fix_induced: true, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: X6, severity: Low, aim: deliverable, fix_induced: true, component: scripts/codex-review.py, disposition: fixed}
```

## The class, and the redesign

Findings 2, 4 and 6 come from one cause, and so did round 1's M1 and m4: the parser read answers out of
free text. Round 1 patched that parser twice. It skipped fences and comments, and it read any mention as
dissent. Each patch opened a new hole: a comment that reopens on its own closing line, prose that names
an id, a dissent wrapped over two lines. **The free-text parser is deleted, not patched again.**
Answers are now read ONLY from one section: the lines after the LAST line that is exactly
`## Loosening answers`, up to the `VERDICT:` line. Blank lines are ignored. Every other line must be
exactly `LOOSENING-CHECK <12-hex id>: not a loosening` or `LOOSENING-CHECK <12-hex id>: finding: <non-empty text>`.
Any other line makes the WHOLE section malformed: no assent, and every id the section names, in any
case, counts as a finding. Text outside the section is never read.

I checked the coordinator's hypothesis for soundness and adopted it. Assent now needs an unbroken run of
exact lines in one place, so nothing a reviewer quotes, wraps or comments elsewhere can create assent.
**Bound, stated:** a dissent written ONLY outside the section is not seen. The line then has no answer
from that review, so it stays held unless the other half's exact assent clears it. That is the same
bound as a reviewer who never mentions the line. The prompt says outright that only the section is read.

**Deleted:** `quoted_lines` (the fence and HTML-comment tracker), `FENCE`, `MENTION`, `ASSENT_LINE`, and
the loose "any line naming LOOSENING-CHECK is dissent" rule. The parser is now 20 lines of code with no
state machine.

## Each finding: what was done, and which case covers it

Every fix was written test-first. Each case below was run and seen red before the fix, then green after it.

| Finding | Disposition | Case(s) that cover it |
|---|---|---|
| **Codex 1**: a moved line and a rising count each drew on their OWN list of added lines, so one added line excused two removals | **fixed**. One budget of added lines serves both exemptions. Each line is spent once and compared EXACTLY, trailing whitespace included. A move that also changes trailing whitespace is now flagged; that false HOLD fails closed. | `#508 r2 Codex 1: a MOVED line cannot also excuse a rising count that drops a trailing space`; `...one re-added line excuses ONE identical removal, not two`; `...and a line a rising count consumed cannot also excuse a move`; real git through `gather`, Codex's file VERBATIM: `⭐ #508 r2 Codex 1 real git: the verbatim move + space-dropping rise is flagged and HELD` |
| **Codex 2**: an HTML comment that closes and reopens on one line exposed a quoted assent | **fixed by the redesign**. Comments are never parsed. Outside the section they are not read, and inside it they make the section malformed. | `#508 r2 Codex 2: an assent in an HTML comment closed and reopened on one line is no answer` (both of Codex's forms, verbatim); `...and the same comment INSIDE the section makes it malformed: a finding` |
| **Codex 3**: the record exemptions were path PREFIXES, so `docs/reviews/coordinator/policy.py` or `decision-log.jsonl.extra.py` could change after the round | **fixed**. `REVIEW_RECORDS` (prefixes) is replaced by `REVIEW_RECORD`, an exact `fullmatch`. It accepts `docs/reviews/{claude,codex,coordinator}/<subject>-r<N>-<same dir>.md`, `docs/reviews/verdicts/<subject>-r<N>-{claude,codex}.verdict.json`, and `docs/reviews/decision-scheme/decision-log.jsonl` by equality. The same hole existed for `verdicts/`, `claude/` and `codex/`, so all four directories are exact now, not only the two Codex named. Bound (in the comment): a gate that EXECUTES a file with an exact record name is not caught. | `#508 r2 Codex 3: a file under docs/reviews/coordinator/ that is not a round's coordinator doc does not match`; `...nor a file whose name only STARTS with the decision log's`; `...nor any other name in a review directory — ...` (6 shapes); real git: `⭐ #508 r2 Codex 3 real git: a .py under docs/reviews/coordinator/ committed after the round voids its answer, rc=3` (pinned to that verdict's own note, so other verdicts' notes cannot mask it) |
| **Codex 4**: neutral prose naming an id became a permanent finding | **fixed by the redesign**. Prose outside the section is not read; inside it, prose makes the section malformed. | `#508 r2 Codex 4: prose naming an id OUTSIDE the section is ignored; the section's assent stands` (Codex's text verbatim, with and without a section) |
| **Codex 5** (with round 1's **m3**): a repaired replacement keeps its id (the id hashes the REMOVED base text), so its earlier finding held for ever | **fixed**, rule below | `#508 r2 Codex 5: a LATER round of the SAME half, on this tree, answering not a loosening retires its finding`; negatives: `...but not a later round of the OTHER half`; `...nor a later round of the same half that does not answer THAT id`; `...nor the same half's later assent on ANOTHER tree`; `...nor an EARLIER round's assent — rounds compare as numbers, r10 after r9`; `...nor another SUBJECT's later round, nor anything after a verdict whose name gives no round`; real git, Codex's sequence: `⭐ #508 r2 Codex 5 real git: a REPAIRED line's finding is retired by the same half's later assent on the exact tree (rc=0), and not by the other half's (rc=3)`; the round-1 m3 cases still pass |
| **Codex 6**: a dissent wrapped across two lines was lost | **fixed by the redesign**. Inside the section, a wrapped line is malformed, so every id in the section becomes a finding. Outside it: the stated bound above. | `#508 r2 Codex 6: a dissent WRAPPED inside the section voids its assent: every id a finding` (Codex's lines verbatim) |

### Codex 5: the rule, and why it is the simplest sound one

**A finding (any answer other than exactly `not a loosening`) stands until a LATER round, by number, of the
SAME subject and the SAME half answers that id `not a loosening` in a verdict on the tree being merged.**
Subject, round and half come from the verdict's name (`<subject>-r<N>-<half>.verdict.json`), because no
record carries a time. `standing_findings` implements it, and `answered_flags` is the on-tree assents minus the standing findings.

- *Why not keep m3's "a finding holds for ever"?* Codex 5 shows the id cannot change through a repair. A
  repaired line would hold for ever and push every fixed PR to the owner. That is the false HOLD backlog
  #508 exists to remove.
- *Why the same half?* The objecting reviewer is the one who can say the repair satisfies the objection.
  The other half's assent is the case m3 refused, and it still does not retire the finding.
- *Why later, and on the merging tree?* A finding on an earlier tree is then superseded only by a
  judgment of the code actually being merged.
- *Why fail closed on an unparsable name?* A finding in a verdict with no round in its name can never
  be followed, so it stands.
- *Rejected: hashing the replacement into the id.* The replacement can be spread over many added lines,
  and a new id per edit would discard findings on unrelated edits, which is round 1's m3 hole again.

## Mutations

**`codex-review.json` 84 → 87.** 7 entries were REMOVED with the machinery they guarded: the mention
rule and the six fence/comment entries. 3 were re-anchored: finding wins, `fullmatch`, and the upper-case
id. 10 were added: a malformed line skipped; only the bad line's ids; `HEX_ID` case; the FIRST section;
no stop at `VERDICT:`; blank lines malformed; any heading naming the section; no section read as the
whole text; an empty finding text; lines not right-stripped.

**`check-merge-ready.json` 127 → 141.** 12 were re-anchored to the clauses that now carry the same rule:
the move, the indentation, the rising-count skip, the docs exemption, finding wins, the exact answer, the
trailing whitespace, the three r1 M2 records, and the two r1 m3 entries. 14 were added:
- Codex 3 (3): the coordinator pattern, `fullmatch`, and the half's own directory.
- Codex 5 (8): retirement off; the other half retires; another subject retires; any round retires;
  rounds compared as text; an assent on another tree retires; a round that does not answer that id
  retires; and the notes loop.
- Codex 1 (3): the rise not spending its line, the move not spending its line, and the move compared stripped.

`record-review-verdict.json` is unchanged at 23. Every anchor in the three manifests matches exactly once.
Each new or changed entry was applied to a staged COPY (`check-plan-code.stage_tree` → `run_mutations`).
Results: `codex-review.json` **13/13** new or changed entries killed through their named cases, and `check-merge-ready.json` **26/26**. The first gate run had ONE survivor, the notes-loop entry. The m3 real-git case looked for `k-r7-claude` anywhere in the output, and that verdict's `reviewed a different tree` note also names it, so the case could not fail for its own note. The case now looks for that note's own words (`k-r7-claude.verdict.json: answered <id> a finding`), and the re-run killed the entry. `load_manifests` also refused five entries whose anchor sets repeated an earlier entry's. Each was given a distinct anchor on the same clause and re-run: 6/6 killed.

**Fixture tightenings** (no behaviour change): the real-git `_verdict8` files each review under its own half's directory, as the exact record names now require; the `tree_matches` fixture uses `<subject>-r<N>-<half>` names; the real-git Codex 3 case checks that verdict's own note, not any `different tree` text.

Not mutated: the `k is not None` guard in `standing_findings`. Removing it does not change any verdict;
it crashes on `None[:2]`, so it is a crash guard, not a rule.

## Round 1 m6

**Filed** as backlog #526: a Claude half's overlay is captured when its verdict is recorded, not when
the half reviewed.
