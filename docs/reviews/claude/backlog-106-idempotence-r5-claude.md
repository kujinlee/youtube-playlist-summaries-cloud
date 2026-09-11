# Backlog #106 — composing is idempotent — round 5, CLAUDE half

**Reviewer:** Claude (adversarial half). **Date:** 2026-09-10.
**Verdict up front: CONVERGED.** This round found no defect in the code. It found four stale
numbers in prose and two errors of my own from earlier rounds. You asked me to weigh the verdict
honestly and to say CONVERGED if the round turned up only cosmetics; it did, and I am saying so.

---

## PROOF OF SUBJECT

```
$ git status --porcelain
                                    (empty — clean, and it stayed clean)
$ git log --oneline origin/master..HEAD
8577e525 Round 4: both ends of an override must name a tray part
ded5bbe7 Round 3: delete the repair machinery rather than fix it a third time
51b0803f Round 2: the marked region is verbatim, and the repair is guarded
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page

$ git merge-base origin/master HEAD
050913f6ab1d7d5dc68458b06260c0c9b697a436

$ git diff ded5bbe7..8577e525 --stat        # the round under review
 scripts/brief-compose.py             | 60 ++++-
 scripts/mutations/brief-compose.json | 51 +++-
 ... 8 files changed, 523 insertions(+), 19 deletions(-)
```

**Pinned:** `brief-compose.py` md5 `fcdfed171af8ac53076f9d1b142595c4`, manifest md5
`ccdfc039747b6bbb675c6c3440e1d283`. `--self-test` rc=0, **125/125**; `check-selftest-counts` rc=0;
manifest **16** entries. No `--mutate .`; every mutation below ran against a scratch copy.

---

## Q1 — DID NARROWING OPEN A HOLE THE OTHER WAY? Yes, and it is the right trade

Enumerating the overrides a page could actually write, under the narrowed rule:

| selector | override? | |
|---|---|---|
| `#tray #qbox` | ✅ | the only shape any generator emits today |
| `#tray #qt` | ✅ | would be detected |
| `#tray .in` | ❌ | **missed — this is the narrowing** |
| `#tray .trow` | ❌ | missed; `.trow` is in the tray markup |
| `#tray #sendbtn` | ❌ | missed; `#sendbtn` is not in `TRAY_SELECTOR` |
| `#tray #closebtn` | ❌ | missed |
| `#tray textarea` / `#tray button` | ❌ | missed |

So yes — a page that legitimately overrides `#tray .in` now has that override lifted into the tray
and inherited by descendants.

**It is better than what it fixed, and the asymmetry is the whole argument.** The two failure
directions do not cost the same:

* **Missing an override** adds one bounded, non-growing rule to a residual bucket that is already
  documented and accepted. Nothing renders wrong.
* **Wrongly calling something an override** deletes a genuine tray rule. The page renders with
  pieces missing and no error — which is the failure `brief-compose.py`'s own docstring
  (`FAIL LOUD, NEVER SILENT`) exists to prevent.

The narrowing moved errors out of the second bucket and into the first. That is the correct
direction, and it is worth naming as a principle rather than a patch: **when a classifier's two
error directions have unequal blast radius, tighten until the expensive direction is empty and let
the cheap direction absorb the residue.** Six missed shapes is the price; the price is right.

One wording note: the docstring still asserts *"A page override is a DESCENDANT selector rooted at a
tray part"* as a definition. After r4 it is a statement about **the overrides we emit**, not about
what an override is — my r4 M2 point, still standing in the prose. Cosmetic.

## Q2 — `any(... for p in parts[1:])`, destructive direction only

```
live region: 12 rules; classified subtractable: NONE
#tray .in #qbox  -> True    (3 parts, qualifier at the end)
#qbox #tray      -> True    (reversed)
#tray #tray      -> True    (degenerate)
```

The three shapes you named all classify as overrides, and **none of them is a plausible genuine tray
rule**: the tray's own rules are either bare or `#tray <non-tray-part>`. Nothing in the tray
qualifies one tray part **by another** — that shape exists only because a page wanted to win the
cascade. Measured against the live 12-rule region, the set of genuine rules now classified as
subtractable is **empty**, down from one (`#tray .in`) before this round.

`any` over `all` is also right: `#tray .in #qbox` is an override and would fail an `all` test. And I
confirmed the deleted `len(parts) >= 2` really is implied — every bare selector returns `False`,
because `any()` over an empty `parts[1:]` is `False`:

```
#tray -> False   #qbox -> False   .askbtn -> False   #modechip -> False   body -> False
```

Deleting it rather than keeping and marking it was the right call: it was redundant, not unguarded,
and the two are distinguishable exactly as the comment says — a redundant clause's mutation survives
*because another clause already decides*, which is a different diagnosis from "nothing tests this".

## Q3 — Coverage: zero survivors, and the fifth instance does not exist

Every clause of the predicate, mutated independently:

```
[killed(1)] clause A: whitespace NOT normalised          red: the selector is whitespace-normalised before it is split
[killed(1)] clause B: grouped early return dropped       red: a GROUPED selector is one rule for several parts, not an override
[killed(1)] clause C: root test dropped                  red: an override must be ROOTED at a tray part, not merely mention one
[killed(2)] clause D: qualifier test dropped             red: a genuine tray rule that is descendant-rooted is NOT a page override
[killed(1)] clause E: root read from anywhere            red: an override must be ROOTED at a tray part, not merely mention one
[killed(5)] clause F: any() -> all()
[killed(8)] predicate always True
[killed(7)] predicate always False
```

**No survivors.** Each clause dies via a case named for that clause, and the names are specific
enough that the report says which rule broke. The manifest carries entries for the four r4 findings
by name (`…not whitespace-normalised (r4 H2)`, `…grouped-selector early return (r4 H2)`,
`…rooted ANYWHERE (r4 H2, the central claim)`, `…the qualifier need not be a tray part (r4 B1)`).

This is the r4 H2 diagnosis actually applied rather than acknowledged: the cases now pin the guard's
**content**, not its existence. Clause D is the sharpest — it distinguishes this round's rule from
*last* round's rule, which is the test a case usually fails to make.

I looked for a fifth instance of the pattern and did not find one. That is a negative result from a
sweep that found three in r3 and four in r4 with the same method, which is the only reason it carries
any weight.

## Q4 — The residual: 32 confirmed, denominator is 40

```
html pages (excl .fragment): 47   with a tray: 41
marked: 1   unmarked: 40
carrying INHERITED #tray #qbox: 32
```

**Your 32 is exact.** The denominator is not. The row says *"32 of the **43** unmarked pages"*; the
live count is **40**. 43 appears to descend from the historical *"44 tray pages"* the same row cites
as the corpus at the time of the fix, minus the one marked page — a true statement about September's
corpus written in the present tense about today's.

**Is the description otherwise accurate and complete?** I checked it clause by clause against the
code and the corpus, and every substantive claim holds:

* *"their own fragments never declared them; lifted from `backlog-table`"* — verified on
  `goals.html`: its fragment declares zero tray rules and `grep -c "#tray #qbox" gen-goals-page.py`
  is 0.
* *"on each page's next regeneration the inherited trio is written INSIDE the markers"* — verified by
  simulating goals' next regeneration.
* *"the verbatim path applies nothing and `--remigrate` no longer exists"* — true.
* *"bounded and non-growing (one rule per page, once)"* — true.
* *"the copy outranks the generator's own at equal specificity, so editing
  `gen-backlog-page.py:1480` will silently not reach those pages"* — true, and it is the part that
  actually costs something later.
* *"true of the ACCUMULATION and false of the INHERITANCE"* — this is the distinction my r4 H1 was
  about, stated better in the row than I stated it.

**Is accepting it defensible? Yes.** It is bounded, non-growing, renders correctly, is written down
with its mechanism and its irreversibility trigger, and the two previous attempts to build repair
machinery each produced a Blocking. Declining to build a third is the correct reading of the
evidence, not fatigue. The residual is now documented to a standard that makes it actionable by
someone who was not here — which is the actual test.

One completeness gap, and it is small: the row says regeneration makes it permanent but does not say
**what would remove it**. The answer — a canonical tray file that `_selector_scan` reads instead of
inferring — is in my r3 and r4 halves and in your backlog row for that follow-up, but a reader of
*this* row is left without the exit. One clause would fix it.

## Q5 — What the previous four rounds got wrong

You asked plainly, so: **two of the errors are mine**, and one is the more instructive.

**1. My r3 H2 proposed fix was worse than the one you shipped.** I recommended widening the floor's
token list — derive it from the tray markup plus `.askbtn`. You deleted the floor and replaced it
with a per-rule predicate applied *before* subtraction. Yours is structurally better: it makes the
damage **impossible** rather than **detected**, and it retires a hand-written token list that my own
r3 H1 had just shown could be halved with the suite still green. I proposed to widen a detector when
the right move was to narrow what may be acted on. Recording it because the failure is reusable: when
a guard keeps being found too weak, the question is not *"what else should it check"* but *"why is
anything being destroyed at all"*.

**2. My r4 L1 severity was too low.** I graded `#tray .in` **Low**; Codex graded it **Blocking**; you
adjudicated that I was right on blast radius and Codex was right that the rule was wrong. On
reflection Codex was closer and the honest grade was **Medium**. I weighted *"no live trigger
today"* — a fact about the corpus — against *"the classification rule is wrong"* — a fact about the
code, and the corpus can change under a rule in a way the rule cannot change under a corpus. This is
precisely the error I criticised in r2 when I wrote that *a residual must state what happens, not
only how often*; I made the same mistake one round later in the grading column.

**3. My r1 measurement was wrong before it was right.** My first corpus diff used a multiset
difference, so de-duplication read as dropping and I reported four extra dropped selectors that were
not dropped. I caught it myself and redid it as a presence-set diff. Listing it because Q5 asks and
because the correction is the reason the r1 finding was trusted.

**4. My r2 H2a went stale mid-write** — the page was repaired at 17:03 while I was drafting the claim
that it was still polluted. Corrected in place.

**Nothing I found in the other seven halves was wrong.** The r4 Codex Blocking on `#tray .in` was
right about the rule. Your r2 verification of the four-line diff was accurate as a computed result
and I flagged only that it was not a statement about the file — which it then became.

**Was any fix worse than its defect?** No. I checked the two deletions specifically: `or keep` is
gone and the no-tray fixture still raises (my r4 falsifier), and `len(parts) >= 2` is genuinely
implied by the qualifier clause.

---

## FINDINGS

**No Blocking. No High. No Medium.**

### Low — four stale numbers in the closure row

| the row says | live |
|---|---|
| `32 of the **43** unmarked pages` | 40 unmarked (Q4) |
| `Suite 86 → 119` | **125** |
| `the file joins the mutation manifest … with 13 entries` | **16** |
| `EXPECTED_MUTATIONS moves 412 → 428` | **431** |

All four are one round stale — r5's own changes moved three of them. Nothing mechanical catches this:
`check-selftest-counts` reads the docstring, `check-test-counts` reads the roadmap, and neither reads
this row's prose.

I would not raise it on most branches. I raise it on this one because **the row itself carries a ⚠
about a number that "was never true at any commit"**, and shipping it stale on three counts at merge
time is that same disease in the same paragraph. It is a one-line edit each.

### Low — the docstring still states the narrow rule as a definition

*"A page override is a DESCENDANT selector rooted at a tray part"* is, after r4, a claim about the
overrides this project emits. Saying so would stop the next reader generalising it.

### Low — the residual does not name its exit

Q4 above. One clause pointing at the canonical-tray follow-up.

---

## VERDICT

**CONVERGED.**

Weighing it honestly, as asked. Four rounds of NOT CONVERGED were each earned by a real defect in the
previous round's fix — r1's parsed-list rebuild, r2's text surgery, r3's floor-after-subtraction, r4's
rooting-alone rule. **This round I ran the same instrument that found those and it came back empty:**
zero survivors across eight clause mutations, an empty destructive-classification set on the live
region, and every substantive claim in the residual paragraph confirmed against the corpus. What is
left is four stale integers and two sentences of wording.

The reason the series terminated is visible in the code: each round replaced a *detector* with a
*constraint*, and constraints do not have the failure mode detectors have. The final predicate cannot
destroy a bare tray rule — not because a case checks it, but because the function cannot return True
for one.

**The single most important thing to fix: the four stale numbers**, before merge. They are prose
edits, they are in the artifact that outlives this conversation, and a closure row that misstates its
own counts is the one defect this branch has apologised for twice.

**On the residual:** ship it. It is bounded, non-growing, measured, documented with its mechanism and
its irreversibility trigger, and the two attempts to fix it each cost a Blocking. Add the clause
naming the exit and it is a model of how to accept one.

⚠ Pinned to `brief-compose.py` md5 `fcdfed17…`, manifest md5 `ccdfc039…`. Tree clean throughout.
