# Architecture review (Phase 6, narrow): `node-tree-s3`, the PRIORITY detection in `check-features.py`

Subject: `scripts/check-features.py` at `e4fa741b` (branch `node-tree-s3-goals`), `_PRIORITY_ATTEMPT` (`:522`),
`priority_order` (`:546`), `thread_name_problems` (`:558`). Written 2026-11-27 05:55.
Read: `CONTEXT.md` (silent on PRIORITY), ADR-0016 (lists "a `PRIORITY` slug" among the names G2 checks; not
re-litigated), spec `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` (Q3, rows 294, 381–386, 503, 589),
the r1 and r3 Claude reviews, the r2 Codex review, backlog #744 (uncommitted).
Every claim below was run by me on Python 3 on macOS, in this worktree. The probe corpus is 33 lines I built from the
three rounds' inputs plus my own near misses. It is a hand-built set, so its counts are not a base rate.

## Arming evidence

| Round | Finding | Caused by the previous fix? |
|---|---|---|
| r1 Claude F1 | prose beginning `PRIORITY` refused | no (the build) |
| r2 Codex M1, M2 | quoted prose refused; multi-token date dropped | yes, the r1 fold `_PRIORITY_START` |
| r3 Claude H1 | `PRIORITY is decided by the owner · see ADR-0010.` refused | yes, the r2 fold `7a83d09c` |

Re-run: H1 is `attempt=True valid=False`; H2 `PRIORITY · a > b` is `attempt=False`; all seven H3 forms are
`attempt=False`. Two consecutive fix-induced rounds in one component: THRASHING, as the r3 reviewer says.

## 1. Can a redesign remove the class? Yes, and backlog #744's rule is right, with one amendment

**The class:** the detector sits BETWEEN two boundaries, "begins with the word" and "is a valid declaration". Every
predicate placed between them has two edges, and each round moved one edge and exposed the other. Backlog #744
collapses the detector onto the outer boundary, so only one question is left, and it is lexical.

| Design | Makes impossible | Makes loud | Leaves silent |
|---|---|---|---|
| today (`_PRIORITY_ATTEMPT`) | nothing | some malformed attempts | 15 of 33 probe lines carry a ranking and are read as prose |
| backlog #744 as worded | a silent drop of any line starting `PRIORITY`, any case, indented, with `:` | prose starting with the word | 5 of 33: `- PRIORITY …`, `**PRIORITY** …`, a backticked line, `> PRIORITY …`, `PRIORITIES …` |
| **#744 amended: first WORD after any non-word prefix** (`^\W*priority\b`, ignoring case) | the four prefixed forms too | the same, plus prose that starts by quoting the keyword | 1 of 33: a misspelt keyword |
| `## PRIORITY …` heading (closed heading set) | a misspelt keyword after `## ` | every `## ` near miss, by `parse_threads`' existing refusal | a line without `## ` |

- **The amendment matters here.** The grammar is documented at `docs/goal-threads.md:31` inside a `- ` bullet with
  the form in backticks. An author copying the surrounding style writes `- PRIORITY …`, which #744 as worded drops.
- **Cost, measured:** the real preamble is 39 lines; 0 match either rule, and 2 contain ` · `. The price is r1's F1,
  a loud refusal that names the line.
- **The heading design is better on paper and I do not recommend it.** It moves the line out of "the preamble",
  which the owner chose in spec Q3 (11-23 21:20). That moves the goal, and it touches three readers
  (`parse_threads`, `requests_by_goal`, `thread_name_problems`). Keep it as the retreat (see STOP).
- **No detector can make a misspelt keyword loud for an OPTIONAL line.** Only the reader can: S4's agenda must print
  "no PRIORITY declared" when `priority_order` returns None, so absence is seen where the owner looks.
- **Build note:** in the preamble the first-word test must run BEFORE the `>` skip at `:575`, and
  `priority_order` and the gate must share ONE function. Today they are two predicates (see 4b).

## 2. Other hand-written lines read by a heuristic in this slice

| Where | Risk | Same class? |
|---|---|---|
| `ALSO_FIELD`, `check-features.py:512`, read by `goal-tree.py:255` | `· Also a`, `·also a` and `· also: a` fall into `<what>` in BOTH readers with no message: the thread is not shared. `· also see the spec` is refused loudly | **Yes, the silent half only.** A field found by a pattern inside free prose. Lower stakes: the text still shows on the page. File it |
| the first `## GOAL` heading, `goal-tree.py:378` | above the first goal everything is prose, so a mis-typed FIRST heading (`##GOAL a`, `### GOAL a`) followed by a valid goal swallows its threads in silence. Later goals are refused (measured) | **Yes**, same open region. Predates this slice (backlog #363). File it |
| `_GOAL_ANY`, `:524`; request lines, `:336` | closed: inside a goal every line is a request, a thread, or refused (`goal-tree.py:395`) | No |
| `was:` and node lines, `parse_features` `:104–143` | closed: a non-field line inside a node is refused, and no prefix is exempt | No. This is the model to copy |

## 3. Block S3's merge? No. Ship it after S3 and before S4

- `priority_order` has **no caller** outside the self-test (grep over `scripts/`, `.claude/hooks`, `.github`). Spec
  row 294 says "none yet", and S4 adds the agenda line (row 503). No line exists either, so a drop loses nothing today.
- Every finding is MINOR or NIT, and r4 is the round cap. Folding into S3 buys a fourth round on a path no reader uses.
- **What S3 does ship that is wrong:** the comment at `:515–517` ("a part prose never does in that place", "never
  dropped in silence") is measured false. Accept it for the gap; backlog #744 deletes it.
- **So backlog #744 is a PREREQUISITE of S4, not a 🟢 someday row.** Record that in the row and the roadmap.

## 4. Decided in this slice and not written down

- **(a) Whether preamble prose may begin with `PRIORITY`.** The spec is silent. The r1 fold decided "yes", and #744
  reverses it. The real decision is the side of the trade: a loud false refusal over a silent drop of an owner's order.
- **(b) The reader trusts the gate.** `priority_order` takes the first valid line and knows no "attempt"; it is
  correct only when G2 passed. The "ONE OWNER" comment at `:508` covers the pattern, not the decision.
- **(c) A machine-read line was put in the file's only OPEN region.** "Prose belongs above the first goal" and the
  body is closed. PRIORITY is the first line read from the open part; that is the structural cause of all three rounds.
- **(d) The grammar and its gate shipped a slice ahead of the only consumer.** Three rounds were spent on a dead path.
- **(e) `also` is case- and space-sensitive**, and the date in `PRIORITY_LINE` is not a calendar date
  (`2026-13-99` is read). Neither bound is stated.

## Recommendation

1. Merge S3 as it stands; do not fold. Amend backlog #744 to the first-WORD rule (`^\W*priority\b`, ignoring case,
   tested before the `>` skip), one shared function for gate and reader, and the rule stated at `goal-threads.md:31`.
2. Make backlog #744 a prerequisite of S4, and have S4's agenda print the absence of a PRIORITY line.
3. File two rows: the `also` silent forms, and the first-heading swallow. Write 4a and 4c into the spec's Q3 row.

**FAILS IF:** in a constructed preamble, any line whose first word (after any non-word prefix, any case) is
`PRIORITY` is neither refused nor returned by `priority_order`; or the gate and `priority_order` disagree on any
line of the 33-line corpus; or S4 merges while `grep -c _PRIORITY_ATTEMPT scripts/check-features.py` is not 0.
**STOP:** if the round after that fix carries a fix-induced finding in the detector, stop tuning it and take the
`## PRIORITY` heading to the owner, since it changes spec Q3.
