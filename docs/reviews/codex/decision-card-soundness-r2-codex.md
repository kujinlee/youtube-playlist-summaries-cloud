<!-- codex-review: model=gpt-5.5 -->

Blocking: found 1.

1. severity: Blocking  
component: hidden-thrashing condition  
aim: instrument  
fix_induced: yes  
evidence: §1’s third clause suppresses a needed refusal whenever the previous pair had any shared component, even if the current hidden candidate is a different component. The clause is at `docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:90-99`.

Command run:

```text
round components: [['A'], ['A', 'B'], ['C']]
previous pair thrashing_component: A
last pair thrashing_component: None
last pair hidden-thrashing two-clause: True
last pair hidden-thrashing with third clause: False
suppressed candidate pair: r2 B vs r3 C
```

That sequence means r1/r2 already arms on `A`, but r2/r3 still has an unresolved `B` vs `C` no-overlap pair. The third clause removes the only signal for that second candidate.

2. severity: High  
component: backlog-136 scope  
aim: instrument  
fix_induced: yes  
evidence: The spec says #136 is untouched because `CANNOT_RUN` is not a route and this only fixes upstream evidence (`docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:165-199`). That is not an honest read of #136. #136 explicitly includes the same mechanical defect this spec designs around: `thrashing_component()` is free-text over `component`, and “the partition should be derived from the file/symbol a finding names, removing author naming from the loop” (`docs/backlog.md:164`). This spec instead preserves free-text `component` and adds an optional testimony escape. That is not merely a prerequisite to #136; it chooses a competing direction for part of #136’s named work.

3. severity: High  
component: components-distinct scope  
aim: instrument  
fix_induced: yes  
evidence: The spec claims the placement rule makes the declaration cover “that pair only” (`docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:127-132`), then deliberately removes component names from the declaration (`docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:153-155`). That scopes the escape only to a round-number pair, not to the candidate sets that were judged. On a later re-run after either round document is edited, the old `components_distinct:` in round N can suppress a newly-created refusal over different component sets for the same N-1/N pair. The “one declaration cannot silence later refusals forever” claim is too narrow; a declaration can still silence future meanings of the same pair.

4. severity: Medium  
component: calibration corpus  
aim: instrument  
fix_induced: no  
evidence: I cannot reproduce `147` findings in §3 (`docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:214-220`) using the stated corpus and parser. Command run: import `scripts/check-review-decision.py`, parse `docs/reviews/coordinator/*-r*-coordinator.md` with `parse_header`.

Output:

```text
coordinator r docs 71
parseable 29 failed 42 subjects 8 findings 152
```

The subject/round count reproduces as 8/29, but the finding count is 152, not 147. Per the mandate, that is a finding.

5. severity: Medium  
component: exit-code settlement  
aim: instrument  
fix_induced: yes  
evidence: The #118 subsection claims “this spec moves 5 cases from exit 1 to exit 2” (`docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:201-207`). That only holds for the pre-third-clause condition. Replaying the corpus with the third clause gives 4 refusals, not 5:

```text
would refuse 2clause 5
would refuse 3clause 4
```

Also, `exit_code_for` still maps unknown decisions to 1: `return {"STOP": 0, "CANNOT_RUN": 2}.get(decision, 1)` at `scripts/check-review-decision.py:391-393`. So the spec has not settled #118 by use; it asserts a policy while the live owner still encodes the ambiguity #118 filed.

6. severity: Low  
component: card-mention measurement  
aim: instrument  
fix_induced: yes  
evidence: The 14/134 count is reproducible only as `check-review-decision` mentions, but the subcount is wrong. Command run over `docs/reviews/coordinator/*.md`:

```text
check-review-decision only 14
['decision-card-soundness-r1-coordinator.md',
 'peer-sites-r2-coordinator.md',
 'peer-sites-r3-coordinator.md',
 'peer-sites-r4-coordinator.md',
 'review-decision-procedure-r1-coordinator.md',
 'review-decision-procedure-r2-coordinator.md',
 'review-decision-procedure-r3-coordinator.md',
 'review-decision-procedure-r4-coordinator.md',
 'review-decision-procedure-r5-coordinator.md',
 'review-decision-procedure-r6-coordinator.md',
 'review-decision-procedure-r7-coordinator.md',
 'velocity-177-r1-coordinator.md',
 'velocity-177-r2-coordinator.md',
 'velocity-177-r4-coordinator.md']
```

The spec says 7 of the 14 are on the two subjects about the card (`docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:365-372`). The two subjects are `review-decision-procedure` and `decision-card-soundness`, and they account for 8 documents, not 7.
