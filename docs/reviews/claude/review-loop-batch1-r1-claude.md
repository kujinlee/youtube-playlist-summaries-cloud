# review-loop-batch1 — round 1 — Claude half

Subject: `fix/review-loop-batch1`, `92c78bff..a6918597` (+ `33d53b7e`, the decision-log bet), worktree
`scratchpad/wt-rl1`. Mandate: REFUTE. Rows: backlog #306, backlog #318, backlog #339.

## Reproduced (run by me, in the worktree or a temp copy of it)

| Check | Result |
|---|---|
| `check-review-decision.py --self-test` | `118/118 self-test cases passed`, rc=0 |
| `check-review-rounds.py --self-test` | `89/89 self-test cases passed`, rc=0 |
| `check-plan-code.py --self-test` | `215/215 passed`, rc=0 |
| `check-docs.py` | `Documentation integrity OK` |
| Every edit anchor in both touched manifests | resolves exactly once: `check-review-decision.json 30 bad 0`, `check-review-rounds.json 35 bad 0` |
| Scoped `--mutate .` (temp copy, implementer's `rl1-scoped.sh`, which I read first) | `30 mutation(s), 30 killed, 30 attributed … 0 survivor(s)` and `35 mutation(s), 35 killed, 35 attributed … 0 survivor(s)` |
| `rounds_for('chrome-bar-reachable')` + `decide(…, 'full-loop', True)` | `[(3, 6), (5, 8), (6, 9)]` → `('CANNOT_RUN', 'rounds are not gapless: found [3, 5, 6], expected [1, 2, 3] — refusing to infer adjacency from list position')` |
| Corpus, master `check-review-decision.py` vs branch, **same (branch) corpus**, all 31 coordinator subjects | 18 parse under both. The **only** diff is `ship-src-root-alone`'s refusal reason: `L4 … 'refuted'` → `H1 … 'redesigned'`. No verdict changed |
| Hand mutation: `ANSWERED` gains `"wontfix"` | killed by `…while a disposition outside the vocabulary still REFUSES` (117/118) |
| Hand mutation: `REQUIRED["disposition"]` loses `"filed"` | killed, but by an **uncaught `ValueError` aborting the suite** (rc=1, 0 `[FAIL]` lines), not a named case — pre-existing shape, not this branch's |

So mandate (b) and (d) hold up: `refuted` is the right change per the row's WORK (*"add `refuted` to the
enum with its meaning stated, then re-measure"*), it changes no verdict anywhere in the corpus, the row
says `redesigned`/`retreat`/`moot` are still refused, and the counts, manifests and anchors are consistent.
CANNOT RUN on a non-gapless sequence (mandate a) is the right behaviour — r3→r5 is not adjacency — and the
#306 row states the remaining work truthfully. The findings are below.

---

## HIGH 1 — `review-method.md` says "practice already matches" and that mis-filing "fails `check-review-rounds.py`"; the corpus holds 40 counter-instances that pass the gate today

**File:** `docs/review-method.md`, *The protocol* step 4 (the added ⛔ paragraph).

The added text: *"Filing it that way fails `check-review-rounds.py` twice … Practice already matches:
`main-drivable` and `shard-mutation-sweep` carry both halves for each of r7, r8 and r9."*

**Input:** the corpus on this branch.

```
$ grep -rliE 'REVIEW GAP:\**\s*claude.*alternat' docs/reviews | wc -l
      40
   5 chrome-bar-reachable   4 work-lines-backfill   4 backlog-154-dash-scalar   3 velocity-177
   3 trigger3-lost-bet      3 banner-unheralded     2 work-lines-always-on  2 work-lines  …
```

and the lines themselves, e.g. `trigger3-lost-bet` (merged as PR #387, the newest subject on master):

```
REVIEW GAP: claude — alternation, per `review-method.md` -> Round topology step 4. Not a failure to run.
```

**What happens:** the dominant practice is the one backlog #339 calls wrong. It does not fail
`check-review-rounds.py`: a `REVIEW GAP: claude` line satisfies the audit, which is why
`check-review-rounds.py` on this tree reports `0 silent gaps` over those 40 documents. Two cherry-picked
subjects that pair correctly do not make "practice already matches" true. The doc sentence promises
enforcement the check does not give for the form people actually use. The new `PAIRING_RULE` message
only reaches someone who files **no** gap line. Whoever writes `REVIEW GAP: claude — alternation`, the
escape `plugins.md` forbids, gets a green check.

**Why this matters for the #339 closure:** the row's falsifier (*"file a single-half round under a new
number; the gate must name the pairing rule"*) is met, and I agree the row's own WORK is done. But its
title, *"the only escape is one the process forbids"*, describes a live escape the gate still accepts.
That escape was used through the most recent merged subject. The commit narrows the claim, and
`CLOSED` sitting beside the false "practice already matches" sentence will be read as *this class is
handled*.

**Fix:**
1. Replace "Practice already matches" with the measured figure: both halves are the rule, and 40 round
   documents across at least 10 subjects instead record `REVIEW GAP: claude — alternation`, which this
   paragraph now forbids.
2. Qualify "fails twice": it fails *unless a `REVIEW GAP:` line is written*.
3. File the mechanical half as a follow-up row, and record it in the #339 closure text: `check-review-rounds` should refuse, or at least warn on, a `REVIEW GAP: claude` whose reason cites alternation. That is a SHAPE the gap-line parser already reads. It is the only way the forbidden escape stops passing.

---

## MEDIUM 2 — two backfilled `fix_induced: false` values are contradicted by git, and r5's provenance states a falsehood to justify one

**Files:** `docs/reviews/coordinator/chrome-bar-reachable-r5-coordinator.md` (header `L1`, provenance
bullet *`fix_induced`*); `…-r3-coordinator.md` (header `L1`).

The template's definition (`docs/round-header-template.md`): *"`fix_induced` — was the defect introduced
by a fix written **after** a previous round?"*

**r5 L1.** The provenance says L1 is *"a harness limit the half places within the documented
pair-coverage exclusion, **not something r4 wrote**"*. The r5 Codex half names the pair: *"the pin
selector must touch the brace again"* + *"the reachability predicate never fires"*, masking *the
grouped-selector case*. Git:

```
$ git log -S "must touch the brace" -- scripts/mutations/page_chrome.json scripts/page_chrome.py
4f4e2748 … The id predicates were still substring tests … — r4's remainder, folded
$ git show 4f4e2748 | grep -E '^\+.*(must touch the brace|grouped)'
+  "name": "the pin selector must touch the brace again",
+    # ── r4 LOW: the pin may appear in a grouped selector, or with whitespace before `{`.
```

Both the mutation and the case it masks were written by r4's fold. By the template's definition L1 is
`fix_induced: true`. r5 then reads 8 of 8, not the note's 7 of 8. The header copied the note's count,
the provenance asserted a reason that git refutes, and the word *DERIVED* in the section heading covers
both.

**r3 L1.** The provenance's only evidence is *"L1 is not in [the *Introduced by* table]"*, which infers
from absence. The masking pair is *"the has_control gate is dropped"* (added `89471c9d`, pre-review) and
*"a finished document is exempted like a fragment"*. `git show d2e5db17` (the *Round 1 fold*) shows that
second entry being renamed and re-anchored onto the new `_is_document(page)` branch that fold added. So
half of r3 L1's pair is r1-fold code. That makes `true` under the template's wording, though not under
the narrower thrashing reading (previous round only). Either way it is a judgement the record does not
settle, and the header states `false` as derived.

**Effect today:** none on a decision. `decide` is CANNOT_RUN and both are Lows. But the decision-log bet
(`33d53b7e`) names *"an invented value"* as its failure observation, and these headers are the input any
future answer on this subject will read.

**Fix:** set r5 L1 to `fix_induced: true` and correct the provenance bullet, citing `4f4e2748`. Note
that the header now disagrees with the note's own "7 of 8", as the r6 provenance already does for its
own count. For r3 L1, either set `true` and cite `d2e5db17`, or keep `false` and state that it is a
judgement and why, rather than inferring it from absence in a table.

---

## MEDIUM 3 — backlog #339 makes "the second half reviews the first half's fold" the normal shape of every round, and `fix_induced` does not say whether that counts

**Files:** `docs/round-header-template.md` (`fix_induced` row); `docs/review-method.md` step 4 (new text);
`chrome-bar-reachable-r6-coordinator.md` header.

The new step-4 text: *"The two halves of round N run one AFTER the other, the second seeing the first's
fold."* So in every alternating round from now on, the second half's findings can be caused by a fix
written **inside the same round**. The r6 backfill shows the consequence. Five of its six `fix_induced:
true` values (claude-B1, H1, H2, H3, L1) are caused by `38e31fc6`/`a0fe9916`, the r6 *Codex-half* folds,
and the r6 note itself calls them *"3 of 6, **within the round**"*. The thrashing condition the procedure
computes is *"findings caused by the **previous round's** fix"*. `fix_induced` is defined as *"after a
previous round"*, which within-round fold-induced findings satisfy only literally.

**What happens:** once the pairing rule is followed, each round's second half routinely produces
within-round fix-induced findings. Recorded as `true`, they arm thrashing on what the rule itself made
routine. Recorded as `false`, they hide the r6 shape the note calls *"the clearest instance yet"*. The
branch adopts one reading in the r6 header without the template saying which is meant. This is a
composition gap between #339's new sentence and #306's backfill, and neither row's review would see it
alone. UNVERIFIED how `thrashing_component` weights it beyond the implementer's informational
`page_chrome leads by 2`.

**Fix:** one sentence in the template's `fix_induced` row stating whether a fix written by the same
round's first half counts, plus a matching note in the r6 provenance. If it changes the procedure's
semantics, file it rather than decide it here.

---

## LOW 4 — `PAIRING_RULE` is appended to every solo-half failure, including round 1 and the in-flight case

**File:** `scripts/check-review-rounds.py`, `audit` (the `problems.append` f-string) + `PAIRING_RULE`.

**Input:** this very round, run while my half was still being written:

```
✗ review-loop-batch1 round 1: only codex — claude neither ran nor recorded a `REVIEW GAP:` line — a round
is a PAIR — rounds 2+ alternate the ORDER of its two halves, they do not halve it; if the other half ran
under another round number, file it under this one (docs/review-method.md → *The protocol*, step 4)
```

Round 1 is concurrent, so "rounds 2+ alternate the ORDER" and "file it under this one" do not apply. The
true cause here is "the other half has not landed yet". The message is not wrong, but it diagnoses
mis-numbering for every solo half. The falsifier only requires that the rule is named, so this is
cosmetic.

**Fix (optional):** name the specific mis-numbering when it is detectable, i.e. the adjacent round N±1
carries only the opposite half. Otherwise keep the generic pointer without the "file it under this one"
imperative.

---

## LOW 5 — the r3/r5 `halves.claude` GAP strings editorialise past their source

The headers say *"the r3 Codex half records `REVIEW GAP: claude`, reading alternation as one half per
round (the reading backlog #339 corrects)"*. The first clause is a quotation the half supports. The
parenthetical is this branch's later judgement, placed inside a field the template defines as *whether
each half ran; a gap carries its reason*. The reason the half gave was alternation; the correction is
#339's. Harmless, but the provenance sections already carry that commentary, so the field could quote
the half alone. **Fix (optional):** move the parenthetical to the provenance bullet.

---

## Checked and not a finding

- r3/r5/r6 ids, severities and order match each half (r3 6, r5 8, r6 3+6). Dispositions trace to the named fold commits: `03b78e94`; `cfe586fb` folded exactly r5 M1 (dict-attrs) and M3 (shield order); `8ea57020` the option-A narrowing; and `38e31fc6`/`a0fe9916`/`2ee4371c`/`cbf0e294`/`003fb932` for r6. `declined` for the option-A five and for r6 claude-L1 is right under the template's new meanings ("real, not being fixed"), not `refuted`.
- r5 M5 → r6 codex-M2, declined then fixed, is recorded in both headers as the provenance says.
- The #306 row's restated falsifier (3 of 3 coordinator documents, not 15 of 15) is correct per the template's structural argument, and the row keeps PARTLY. The "do not read rc=2 as no thrashing" warning is in the r6 note.
- The three `chrome-bar-reachable` rounds with headers lead the corpus count from 17 to 18 parsing, through the backfill and not through the `refuted` change, as the report says. I reproduced that by holding the corpus fixed.

## NOT RUN

The full unsharded `--mutate .`; CI. (`check-selftest-counts.py` finished after drafting: *"59 script(s)
declare a count, every one verified by running it"*, rc=0.)

VERDICT: NOT CONVERGED
