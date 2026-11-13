Reviewed head: 9d777115179b0d3b5ca8b57ae69f03369273718a

> **For the r4 fold of `false-hold-judgment` (PR #522, backlog #508).** This review was triggered by **THRASHING**,
> by the letter of `docs/dev-process.md` → *Phases*. `scripts/check-review-decision.py` prints
> `ARCHITECTURE_REVIEW — thrashing: 'scripts/codex-review.py' carried fix-induced findings in r2 and r3`. The
> scope ranker ties that file with `scripts/check-merge-ready.py`, so this review examines both.
>
> **Verdict:** the thrashing chain was real from r1 to r2, and **r2's redesign already ended it.** r3's only
> fix-induced finding is the other shape in Q5's table: a case the new rule did not cover. **No BLOCKER.**
> **Recommendation:** keep the r2 section design, and make no parser or budget change in r4. File two rows: the
> order-free pairing (§2b) and the one contract home (§2c).

# Phase 6 architecture review (narrow, triggered by thrashing): the loosening-answers channel and the flagged-line budget (PR #522, backlog #508)

**Scope:**
- `scripts/codex-review.py`: `loosening_answers`, `LOOSENING_SECTION`, `ANSWER_LINE`, `HEX_ID`, `flagged_block_for`.
- `scripts/check-merge-ready.py`: `failure_path_removals`, `rising_count`, `flag_id`, `flagged_block`,
  `REVIEW_RECORD`, `tree_matches`, `VERDICT_NAME`, `standing_findings`, `answered_flags`, `review_answers`.

**How:** read only. `CONTEXT.md` and `docs/adr/` were read, and no ADR governs this channel. The probe scripts are
outside the repository, in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/arch508/`
(`probe_order.py`, `probe_parser.py`, `probe_names.py`, `probe_tree.py`).

**Self-tests at 9d777115:**

| Script | Result |
|---|---|
| `check-merge-ready.py` | 328/328 |
| `codex-review.py` | 232/232 |
| `record-review-verdict.py` | 100/100 |

## 1. Thrashing or prose floor?

**Not a prose floor.** Every finding in r2 and r3 is a code defect with a run reproduction. **It was thrashing from
r1 to r2, and the r2 redesign removed that class. r3 does not continue the chain.**

Two columns below need defining:
- *Caused by the previous fix?* asks whether the previous round's fix created the defect.
- *Shape*:
  - **patch-on-patch**: the fix created the hole.
  - **residual**: the defect predates the fix, and the fix did not reach it.
  - **exhaustiveness**: the new rule does not say what happens in some case. This is row 2 of Q5's table.

| Round | Finding | Component | Caused by the previous fix? | Evidence | Shape |
|---|---|---|---|---|---|
| r2 | X1: a moved line plus a rise that drops a space | merge-ready | **yes** | r1's Codex 3 fix split the budget into a stripped `readded` list and a raw `raw` list. 54667f2c had ONE list; 358a3220 has `raw` beside `readded` (`git show`). | patch-on-patch |
| r2 | X2: an HTML comment closed and reopened on one line | codex-review | **yes** | r1 added the fence and comment tracker (`quoted_lines`), and the hole is in it. | patch-on-patch |
| r2 | X3: record exemptions matched by PREFIX | merge-ready | **partly** | r1 added the `coordinator/` and decision-log prefixes (fix-induced). The `claude/`, `codex/` and `verdicts/` prefixes were already in r0 (the r2 coordinator doc: "the same hole existed"). | patch-on-patch plus residual |
| r2 | X4: neutral prose naming an id became a finding | codex-review | **yes** | r1's loose dissent rule. Measured: re-parsing `false-hold-judgment-r2-codex.md` with 358a3220's parser gives `c8dcfcab4a36: finding`, from Codex's own sentence "The LOOSENING-CHECK parser was exercised for c8dcfcab4a36." | patch-on-patch |
| r2 | X5: a repaired line can never retire its finding | merge-ready | **yes** | r1's m3 rule made a finding hold on any tree, for ever. | patch-on-patch |
| r2 | X6: a dissent wrapped over two lines is lost | codex-review | **no; I dissent from the r2 record's `true`** | r0 dropped any non-exact dissent (r1 CM1). r1's loose rule was line-based and did not reach a wrapped line, but it did not cause the loss. | residual |
| r3 | M1: the shared budget is spent greedily, so the mirror order passes | merge-ready | **no** (agrees with r3) | 54667f2c already spent one shared budget greedily. r1 split it, and r2 re-shared it in hunk order. The mirror order is r0's original shape coming back. | residual |
| r3 | m1: a second heading, or a stray `VERDICT:`, inside the section | codex-review | **yes** (agrees with r3) | Reading after the LAST heading and stopping at the first `VERDICT:` were both r2's design. | **exhaustiveness** |
| r3 | m2: the "commit ticks before the final round" rule was not written down | docs | no | Decided in r1 and never written. | documentation |

**Per component:**
- **`codex-review.py`.** r2 has two patch-on-patch findings (X2, X4) and one residual (X6), all from one cause:
  *answers extracted from free text*. r2 **deleted** that parser rather than patching it (the r2 coordinator doc,
  "The class, and the redesign"). r3's m1 is not a third patch. It is an unspecified case in a strict grammar
  that is otherwise closed. Q5 sends that shape to **FIX plus an exhaustiveness pass**, not to an architecture
  review. §2a runs that pass, and it finds no fail-open.
- **`check-merge-ready.py`.** r2 has patch-on-patch findings (X1, X3, X5), but r3's M1 is a residual. So this
  component does not have two consecutive fix-induced rounds. The underlying shape (**pairing decided by
  position**) still has one live instance, in pass 1. See §2b.

## 2. Can a redesign remove the class?

### 2a. The answers channel: should it be a structured artifact (a JSON block, or a sidecar file)?

**There is already a structured artifact.** The recorder parses once and freezes the result in the verdict JSON
(`loosening_answers`), and the gate reads only that JSON.

Measured on `false-hold-judgment-r2-codex.md`:
- The committed `false-hold-judgment-r2-codex.verdict.json` equals 358a3220's parser output on that review exactly,
  including the X4-manufactured `c8dcfcab4a36: finding`.
- The HEAD parser reads `{}` from the same text, because that review has no section.

So a parser change never re-reads an old verdict. The markdown section is only the reviewer's **input channel**,
and the question is whether that channel should change.

| Option | What it removes | What it costs, or reintroduces |
|---|---|---|
| **A JSON block in the review text** | Line-grammar parsing. | The same "which block?" question returns: first or last, several blocks, a quoted fence. That is exactly r3 m1's class. **Measured:** `json.loads('{"aaaaaaaaaaaa":"finding","aaaaaaaaaaaa":"not a loosening"}')` returns `{'aaaaaaaaaaaa': 'not a loosening'}`. A naive JSON channel **erases a dissent by duplicate key**, which is m1's failure again. Avoiding it needs `object_pairs_hook`, plus rules for escaping and for a reviewer whose JSON does not parse. It is not simpler than 20 lines of fullmatch. |
| **A sidecar file written by the reviewer** | Extraction from text altogether. | It **breaks the per-half output contract** (`docs/plugins.md`: "Claude writes a file; Codex must not"; its final message IS the review). It also adds a second artifact per half with no allocator. That is the shape `codex-review.py`'s backlog #176 note retired. |

**The exhaustiveness pass on the current grammar (run; `probe_parser.py`).** The grammar's degrees of freedom:
heading count (0, 1, or 2 or more); the terminator (absent, present, or a stray `VERDICT:` inside); the kind of each
line inside (blank, assent, finding, other); and ids before the heading or after `VERDICT:`.

| Probe | Input | Result | Effect |
|---|---|---|---|
| P1 | the prompt's example quoted UNINDENTED in a fence before the real section | `{a: finding}` | false HOLD |
| P2 | a dissent in the body, an assent in the section | `{a: not a loosening}` | the **stated bound** (only the section is read) |
| P3 | U+2028 joining a finding and an assent on one physical line | `{a: finding}`, and b unanswered | fails closed |
| P4 | a 12-hex short sha after `VERDICT:` | both ids `finding` | false HOLD (stated bound) |
| P5 | prose after the section and no `VERDICT:` | `{a: finding}` | fails closed |
| P6 | a JSON-shaped answer inside the section | `{a: finding}` | fails closed |
| corpus | all 2,299 review `.md` files under `docs/reviews/` | 1 has the heading (`false-hold-judgment-r3-claude.md`), and it parses as intended | — |

**No probe at 9d777115 produced an assent the reviewer did not write.** What remains is the stated bound (P2) and
false HOLDs (P1, P4).

One residual cost belongs to the design, not to a defect. A malformed section becomes a *finding*, and a finding is
retired only by a later round of the same half (`standing_findings`). So a formatting slip like P1 costs a whole
round. That is deliberate: if malformed meant *no answer*, the other half's assent could clear a dissent this half
wrapped (r2 X6). I do not recommend changing it.

**Verdict on (a): no redesign. The class that thrashed was removed in r2.** A JSON channel moves the extraction
problem, it does not remove it, and the measured duplicate-key behaviour makes it worse by default.

### 2b. The budget: an order-free construction (multiset diff)

Two passes are in place since r3: exact re-adds first, then rises. **Moves against rises** is now order-free, and I
agree with the r3 fold's argument. A pass-2 pairing only joins lines that differ by a raised count, and a greedy
mis-pairing among rises can only flag (fail closed).

**Moves against moves is still decided by position. Measured with real `git diff -U5` (`probe_order.py`):**

1. The base has `gate()`, which contains `strict = True` 2 lines above `return 1`, and `other()`, which contains an
   identical 4-space `strict = True` more than 5 lines from any failure word.
2. The branch deletes `gate()`'s `strict = True`, which is a real loosening: `gate(['--lenient','--bad'])` goes from
   **1 to 0**, measured. It also moves `other()`'s `strict = True` to the top of `other()`.

| Input | Branch flags | `origin/master` (77adb51e) flags |
|---|---|---|
| B1: `gate` before `other` | `{}` (**false green**) | `{}` |
| B2: the same edit, `gate` after `other` | `{'scripts/check-x.py': ['strict = True']}` | the same |

Pass 1 credits the single re-add to whichever removal comes first in hunk order. That is r3 M1's class, *pairing
decided by position*, in the pass M1's fix did not touch. **It is pre-existing.** Master consumes `readded` in the
same order and gives the identical result on both inputs. #508 neither caused it nor widened it.

**The order-free construction** works per file and per distinct text `t`. It credits re-adds to the removals that
are *outside* every failure window first:

```
flagged_in_window(t) = max(0, R_in(t) − max(0, A(t) − R_out(t)))
```

where:
- `R_in(t)` counts the removals of `t` that sit near a failure word;
- `R_out(t)` counts the other removals of `t`;
- `A(t)` counts the exact re-adds of `t`.

The formula is a function of counts, so it is order-free by definition, and when the pairing is ambiguous it
resolves toward flagging. B1 would flag. Cost: about 10 lines in `failure_path_removals`, the B1 and B2 pair as
cases, and about 2 mutations. It changes no answer the gate gives today, except to add flags.

**A second pre-existing bound (measured, C in `probe_order.py`):** a removal is treated as a move if an identical
line is added ANYWHERE in the same file. Delete `gate()`'s `strict = True` and add an unrelated function that
contains `    strict = True`, and the branch flags `{}`. Master also flags `{}`; the control without the unrelated
function flags on both.

No multiset construction removes this. It is what "move" means in this detector (the docstring: "added back
identically anywhere in the same file"). Removing it needs a positional move detector, such as requiring the re-add
inside the same enclosing block or using git's moved-block detection. That is a new mechanism. It should be stated
as a bound and filed, not built here.

### 2c. One contract, two homes

The two components share two contracts, and neither component imports the other's half. `check-merge-ready.py` does
not import `codex-review.py`; `codex-review.py` reaches it only by subprocess (`--flagged-block`).

**1. The answer grammar.**
- `check-merge-ready.py` owns the id (`flag_id`, `[:12]` of sha256) and the assent literal (`NOT_A_LOOSENING`).
  It also *describes* the grammar in prose in `flagged_block`.
- `codex-review.py` *parses* the same grammar with its own `LOOSENING_SECTION`, `ANSWER_LINE` (`[0-9a-f]{12}`) and
  `HEX_ID`, and with the literal `"not a loosening"`.
- Today the two agree. Nothing pins that they keep agreeing: the prompt prose and the regex are two copies of one
  rule.

**2. The review-record names.**
- `codex-review.py` takes its review-id grammar from `check-review-rounds.parse` (`SHAPES`, subject `.+`, two
  forms), and says outright that a private regex would be "this repo's most-repeated defect".
- `check-merge-ready.py`'s `VERDICT_NAME` and `REVIEW_RECORD` are exactly such a private regex: subject
  `[a-z0-9][a-z0-9-]*`, first form only.

**Measured drift (`probe_names.py`, `probe_tree.py`).** Of 7 probe ids:

| Id | Writer (`review_identity`) | Gate (`VERDICT_NAME` / `REVIEW_RECORD`) |
|---|---|---|
| `foo-r1-codex` | accepts | accepts |
| `foo-r01-claude` | accepts | accepts |
| `Foo-r1-codex` | accepts | rejects |
| `foo_bar-r1-codex` | accepts | rejects |
| `foo.bar-r1-codex` | accepts | rejects |
| `foo-codex-r1` | accepts | rejects |
| `-foo-r1-claude` | accepts | rejects |

For a rejected name the consequence is total, and it fails closed:
- The verdict's OWN file is not a record. So
  `tree_matches(reviewed, {}, reviewed + its own verdict + review)` is **False**, and none of its answers ever
  count.
- A finding in it is never retired. `standing_findings` on a `foo_bar` r1 finding plus an r2 same-half assent on
  the tree returns the r1 finding as standing.

So every flagged line HOLDs. That is a false HOLD, the cost #508 exists to cut.

**Today it is latent:**
- 0 of the 191 subjects on disk fall outside the gate's class.
- The 68 second-form files (`<subject>-<who>-r<N>.md`) were last added 2026-08-31.
- 7 of the 31 verdict files `VERDICT_NAME` misses are `*-coordinator.verdict.json` files that the writer's grammar
  accepts. `REVIEW_RECORD` does not exempt those either. That is INFERRED as harmless: nothing current writes one,
  and if one is committed after a round it voids answers, which fails closed.

**Redesign:**
- `check-merge-ready.py` derives subject, round and half from `check-review-rounds.parse`, through `_import_sibling`
  as it already loads siblings. It keeps only the directory and extension checks as its own.
- The answer grammar (heading, line pattern, id width, assent literal, and the prompt paragraph that describes them)
  moves to ONE module, and both scripts import it. The natural owner is `codex-review.py`, which already owns the
  parser and the verdict schema. `flagged_block` would import the paragraph and the literal from it.

What this removes: the drift class, by construction. What it costs: one import edge, re-anchoring the mutations on
the moved constants, and a case that pins the prompt grammar against the parser.

## 3. Recommendation

**One option: KEEP the r2 section design and the r3 two-pass budget, and change NEITHER in r4. File 2b and 2c.**

**Why this option:**
- The class that thrashed (free-text extraction) was removed structurally in r2.
- The exhaustiveness pass (§2a) finds no fail-open.
- The two remaining items are order-free pairing and one contract home. One is pre-existing on master, and the
  other is latent and fails closed.

**Why each item is or is not a BLOCKER.** The tests are §0 Q4c's: (1) the PR as merged gives a false green on a
concrete input, (2) that input was run, and (3) the fix is local.

| Item | BLOCKER? | Reason |
|---|---|---|
| 2b (B1): moves against moves decided by position | **No. File.** | (2) and (3) hold. (1) holds only literally: the false green is **inherited**, because `origin/master` gives the identical `{}` on the identical input (measured). The PR does not make the gate weaker anywhere master was strong. ⚠ If the coordinator reads test 1 as "the merged gate gives a false green, whoever introduced it", this passes all three tests. I judge it inherited, because the round cap governs the PR's own findings; that is the coordinator's call to overrule. |
| 2b (C): any identical add anywhere counts as a move | **No. File as a bound.** | Inherited from master (measured), and the fix is a new mechanism, so test 3 fails. |
| 2c: grammar and record-name drift | **No. File.** | It fails closed (false HOLD, measured), so there is no false green and test 1 fails. Latent: 0 current subjects are affected. |
| 2a: the answers channel | **No change.** | No reachable fail-open was found. JSON and sidecar options are rejected above. |
| X6 classification | **Not code.** | Optional: record in the r4 coordinator doc that X6 is a residual, not fix-induced. It does not change the gate: r3's m1 alone, with r2's X2 and X4, still arms Q5 by the letter. |

**What the r4 fold should adopt now:** nothing in code. In the r4 coordinator doc, record this verdict: thrashing
ended by the r2 redesign, and r3 m1 is the exhaustiveness shape. Then file two backlog rows:
1. **Order-free move pairing in `failure_path_removals`** (2b; the formula above; B1 and B2 as cases), plus the C
   bound stated in its docstring.
2. **`check-merge-ready.py` takes its record-name grammar from `check-review-rounds.parse`, and the answer grammar
   has one home** (2c).

If the coordinator prefers to fold 2b now because it is about 10 lines and only adds flags, that is consistent with
this review. It is not required by the round cap.

## 4. Measured versus inferred

| Claim | Status | How |
|---|---|---|
| HEAD = 9d777115179b0d3b5ca8b57ae69f03369273718a | MEASURED | `git rev-parse HEAD` |
| The self-tests pass (328, 232, 100) | MEASURED | run at HEAD |
| r0 had ONE budget list; r1 split it into `readded` and `raw` | MEASURED | `git show 54667f2c / 358a3220` on `failure_path_removals` |
| The committed r2 Codex verdict equals r1's parser output on that review, `c8dcfcab4a36: finding` included; the HEAD parser reads `{}` | MEASURED | `cx_r1.py` (from 358a3220) and HEAD `loosening_answers` on `false-hold-judgment-r2-codex.md` |
| Parser probes P1–P6 fail closed except the stated bound P2 | MEASURED | `probe_parser.py` |
| Of 2,299 review `.md` files, 1 has the heading and parses as intended | MEASURED | `probe_parser.py` |
| B1 gives a false green on the branch AND on master; B2 flags on both; `gate` goes 1 → 0 | MEASURED | `probe_order.py`, real `git diff -U5`, master = `origin/master` 77adb51e |
| C (an unrelated identical add) exempts the removal on the branch and on master; the control flags | MEASURED | `probe_order.py` |
| JSON duplicate keys keep the LAST value | MEASURED | `python3 -c 'json.loads(...)'` |
| The writer accepts 7 of 7 probe ids; the gate's regexes accept 2 | MEASURED | `probe_names.py` |
| A rejected name voids its own verdict (`tree_matches` False) and makes its finding unretirable | MEASURED | `probe_tree.py` (pure functions, synthetic tree) |
| 0 of 191 on-disk subjects fall outside the gate's class; the last second-form review file was added 2026-08-31 | MEASURED | the `check-review-rounds.parse` corpus walk; `git log --diff-filter=A` |
| The order-free formula closes B1 and adds no false green | **INFERRED** | derivation only; **NOT RUN** (no code was changed) |
| The 2c import refactor is mechanical, and the mutations re-anchor cleanly | **INFERRED** | not attempted |
| Moves against rises is order-free since r3 | INFERRED, consistent with the r3 cases | read `failure_path_removals`; the r3 mirror cases pass in the self-test |
| A coordinator verdict committed after a round only fails closed | INFERRED | read `REVIEW_RECORD`; not run |
| The X6 classification (residual, not fix-induced) | INFERRED | read r0 and r1's dissent rules in the coordinator docs; not re-run against 54667f2c |
| The other parser-input shapes (CRLF, NBSP, VT) fail closed | NOT RE-RUN here | the r3 Claude half reports running them at 57a1def7; the parser has changed since only by the r3 m1 clause |
