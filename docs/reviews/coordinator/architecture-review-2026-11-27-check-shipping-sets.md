# Architecture review (Phase 6, narrow): `subject-status-386`, the depth guard in `check-shipping-sets.py`'s `load_map`

Subject: `scripts/check-shipping-sets.py` at `56a97a1c` (branch `subject-status-386`, PR #650), `load_map` (`:774`),
its parse handler (`:781`), its depth walk (`:786-792`) and the two depth cases (`:1550`, `:1554`). Written
2026-11-27 14:59. Base: `origin/master` `4e247843`, which is also the merge base.
Read: `CONTEXT.md` (silent on the component map; *Guard*, line 137, is the governing term: a guard that cannot
reach its subject says NOT RUN), `docs/adr/` (ADR-0014 on drivable mains is the nearest; none decides this, none
re-litigated), the three coordinator documents and four review halves of this subject, backlog rows #386, #700, #747.
Every claim below was run by me in this session on python3.14.4 and python3.12.9 (CI's pin), on copies of the two
versions of each script under the session scratchpad. The repository was not edited.

## Arming evidence

| Round | Finding | Caused by the previous fix? |
|---|---|---|
| r1 Claude C1 | `load_map` raised `RecursionError` on a deeply nested map | no (the build) |
| r2 Codex D1 (BLOCKER) | the 100,000-level case expected the walk's message; python3.12 refuses it in the parse | yes, the r1 fold |
| r2 Codex D2 (declined) | the walk bounds unknown fields too | yes, the r1 fold |
| r3 Claude E1 (filed, backlog #747) | the 200,000-level case reads only the prefix both paths share | yes, the r1 and r2 folds |

All three fix-induced findings sit in the depth guard that r1's C1 fold added. None is in the type checks that
backlog #700 asked for. Two consecutive fix-induced rounds in one component: THRASHING, as the gate says.

## 1. Can a redesign remove the class? Yes, a small one. Not in this PR: amend backlog #747

**The class.** One refusal has two messages, and the interpreter decides which one a given input gets.

| Depth of `[[…]]` | python3.14.4 | python3.12.9 |
|---|---|---|
| 33, 50, 5,000 | walk: `nested deeper than 32 levels` | walk |
| 100,000 | walk | **parse: `nested too deep to parse`** |
| 200,000 | parse | parse |

Every row is `CANNOT RUN` on both interpreters; depth 32 is read (and then refused as "not a JSON object"). So the
mechanism is right. What moved each round was a CASE that asserts which path refused:

- D1 named the walk at a depth where python3.12 uses the parse.
- E1 is the opposite edge: the case stopped naming a path, so it cannot tell them apart.
- **Backlog #747's written fix would re-open D1.** It says "assert `nested too deep to parse`" at 200,000 levels.
  On python3.14 the parse limit is the stack size (r3 measured "Stack overflow (used 16352 kB)"), so a runner
  with a larger stack parses 200,000 levels, the walk refuses them, and that case goes red with nothing changed.

**Is it a mechanism defect or branch coverage** (`docs/review-method.md`, *The arming condition — full account*)?
Neither branch can be deleted: the parse can overflow, and the walk is what makes `repr` safe. But the
DISTINCTION between them is authored, not forced, and a redesign can delete it.

**The change (two parts, both in the row that already exists):**

1. **One message.** The parse handler at `:782` prints the walk's message. It is true there too: a document that
   overflows the parser is deeper than 32 levels. Measured on a scratch copy with that one line changed: depths
   33 to 200,000 give exactly one message on both interpreters, where the branch gives two.
   - Deletes: the string `nested too deep to parse`, E1's surviving mutant (it becomes the identity), and the
     possibility of a case that names a path.
2. **The parse handler is tested by injection, not by a depth.** A case replaces `json.loads` with a function that
   raises `RecursionError` and asserts `CANNOT RUN`. Measured: it returns `CANNOT RUN` on both interpreters, and
   no interpreter limit is involved. A mutation deleting the `except RecursionError` clause names that case
   (pin 220 → 221). The 200,000-level case stays as a whole-path check and is renamed so it claims no path.

**Why not in this PR.** Round 3 CONVERGED and is the last full round (§0 Q4c). The tree is correct on both
interpreters. Re-run by me: `subject_status.py --self-test` 18/18 on both, `check-shipping-sets.py --self-test`
176/176 on both (2m58s on python3.14.4), on `56a97a1c`.
A fold now is an unreviewed change on a converged tree, for a case-strength gap that lets nothing wrong through.

**Why "keep as is" alone is not enough.** The class is closed in the code and still open in the filed fix. Leaving
backlog #747 as worded schedules a third fix-induced round.

**Rejected: importing `check-inventory.py`'s `_read_json`** (`check-inventory.py:458`, the same reader, which
`:783-785` cites). It removes the second copy but keeps both messages (`check-inventory.py:468`, `:474`), so it
does not touch this class, and it adds a load to this script's shipping set. It is the retreat (see STOP).

### Did the type checks (the part backlog #700 asked for) leave the class open? No

A differential run over 5,533 maps: every position of a valid two-component map replaced by each of 42 values and
by deletion, plus field pairs. The set is hand-built, so its counts are not a base rate.

| master | branch | maps |
|---|---|---|
| accepted | accepted | 99 |
| accepted | refused | 44 |
| traceback | refused | 304 |
| refused | refused | 5,086 |
| refused or traceback | **accepted** | **0** |
| any | traceback | **0** |

Identical counts on python3.14.4 and python3.12.9. The 44 tightenings are a non-string `measured_at` and a
`True` or float `effort`. `load_map`'s callers treat both refusals as a stop: `main` (`:1319-1326`) and
`closure_main` (`:1303-1308`) return 2 or 1, `check-publishability.py:1266` and `mkt_stage.py:556` turn either
into their own CANNOT RUN. So Refused becoming CANNOT RUN on a deep document (rc 1 → rc 2) lets nothing through.

## 2. Leads outside this subject (file, do not fold)

| Where | Measured | Same class as backlog #700? |
|---|---|---|
| `load_declaration`, `check-shipping-sets.py:1182` | a 200,000-deep `shipping-sets.json`, and a `channel` 100,000 deep, raise `RecursionError` on both interpreters | Yes: a sibling loader with no depth bound and no parse handler. Unchanged from master |
| `registered_hooks`, `:715` | a 200,000-deep `.claude/settings.json` raises `RecursionError` on both | Yes, same |
| the walk's bound, `:790` | NOT RUN, by reading: the only walk case nests 50 (`:1550`), so a bound of 40, or `>=` for `>`, would leave it green | No: a missing boundary case. `check-inventory.py:1622` has the pair (32 read, 33 refused) to copy |

The first two are why the reader should exist once in this file (one helper called by all three loaders) when
backlog #747 is built. That is the same change as part 1, applied at three sites.

## 3. Decided in this slice and not written down

- **(a) Which path refuses is not a contract.** No rule, caller or message consumer reads it. The cases treated
  it as one for two rounds. Part 1 writes the decision into the code by removing the second message.
- **(b) The depth bound covers fields no rule reads** (D2, declined). The reason is in the r2 coordinator
  document only. The comment at `:783` says why the bound exists, not that it is whole-document on purpose.
- **(c) E1's `fix_induced: true` is arguable** (the 200,000 case dates from r1; r2 only added the claim about
  it). The arming stands either way: D1 and D2 alone do not arm, D1 plus E1 do, and E1 is the same component and
  the same fold. I did not relabel it.

## Recommendation

1. **Merge PR #650 as it stands; do not fold.** The code is closed for the class on this tree (table in 1).
2. **Amend backlog #747's Fix before anyone builds it:** one message for both depth paths, the parse handler
   tested by an injected `RecursionError`, one bounded reader shared by `load_map`, `load_declaration` and
   `registered_hooks`, and a 32/33 boundary pair. Strike "assert `nested too deep to parse`".
3. Nothing else changes in this PR. The two `RecursionError` leads ride in the amended row, not a new one.

**FAILS IF** (after backlog #747 is built): `grep -c 'too deep to parse' scripts/check-shipping-sets.py` is not 0;
or `load_map` gives anything but one `CANNOT RUN` message for any depth from 33 to 200,000 on python3.12 or
python3.14; or any self-test case of this script passes on one of the two interpreters and fails on the other.
**STOP:** if the round after that fix carries a fix-induced finding in the depth guard, stop tuning the local
copy and take "import `check-inventory.py`'s `_read_json`" to the owner, because it changes this script's
shipping set, which is a marketplace packaging decision.

**Owner:** nothing needs the owner. Amending a filed row is the coordinator's. The HOLD is this review's to clear.

## Flagged lines: how each was checked

- **`4072b5d4d33b`, `b19a207a2de5`, `1d3b07e57dd1`** (`check-shipping-sets.py`, master `:800`, `:807`, `:810`;
  branch `:815`, `:822`, `:825`). Each branch condition is `<new type test> or <master's condition, unchanged>`,
  and the refusal it guards is unchanged, so it refuses a superset. Run on both versions, both interpreters:

  | Input | master | branch |
  |---|---|---|
  | `effort`: 4, `"3"`, `null` | refused | refused |
  | `effort`: `true`, `1.0` | accepted | refused |
  | `package`: `"nope"`, `null`, 1 | refused | refused |
  | `package`: `[]`, `{}` | `TypeError` traceback | refused |
  | `shared_with`: `"q"`, `["nope"]`, own package, `[1]`, `{"q": 1}` | refused | refused |
  | `shared_with`: `[[]]`, `[{}]` | `TypeError` traceback | refused |
  | `shared_with`: `["q"]` on a library (control) | accepted | accepted |

  Plus the 5,533-map run above: 0 maps that master refused and the branch accepts.
- **`ef089d0d344e`, `41cc984570e8`, `646328fa1bc6`** (`subject_status.py`, master `:8`, `:10`, `:11`). All three
  are inside the module docstring (master lines 2-36, branch 2-37, by `ast`). An `ast.dump` comparison of every
  top-level definition: `subject_banner`, `subject_tables`, `runtime_references`, `last_commit`, `_git`,
  `self_test` and the module-level statements are IDENTICAL; only `_self_test_body` differs. No executed line
  outside the self-test changed, so nothing the script refuses can have changed.

## Loosening answers
LOOSENING-CHECK 4072b5d4d33b: not a loosening
LOOSENING-CHECK b19a207a2de5: not a loosening
LOOSENING-CHECK 1d3b07e57dd1: not a loosening
LOOSENING-CHECK ef089d0d344e: not a loosening
LOOSENING-CHECK 41cc984570e8: not a loosening
LOOSENING-CHECK 646328fa1bc6: not a loosening
VERDICT: CONVERGED
