# Backlog #106 — composing is idempotent — round 4, CLAUDE half

**Reviewer:** Claude (adversarial half). **Date:** 2026-09-10.
**Verdict up front: NOT CONVERGED.** The new function is sound in the direction that matters — it
cannot destroy a bare tray rule, which is what r3 was about. The finding is elsewhere: **32 of the
40 unmarked pages will permanently freeze inherited pollution the next time they regenerate**, and
this round deleted the only tool that could have removed it. The PR says those pages "clean
themselves up". For 32 of them, regeneration is what makes it permanent.

This is also the round where the override falsifier I wrote in r3 **fires**. I said so in advance,
so I am saying so now.

---

## PROOF OF SUBJECT

```
$ git status --porcelain
                                    (empty — clean, and it stayed clean)
$ git log --oneline origin/master..HEAD
ded5bbe7 Round 3: delete the repair machinery rather than fix it a third time
51b0803f Round 2: the marked region is verbatim, and the repair is guarded
d9878eeb Round 1: the marker region goes back to being verbatim
370144b1 Backlog #106: composing a page twice now produces the same page

$ git merge-base origin/master HEAD
050913f6ab1d7d5dc68458b06260c0c9b697a436

$ git diff 51b0803f..ded5bbe7 --stat        # the round under review
 scripts/brief-compose.py             | 218 ++++----------
 scripts/mutations/brief-compose.json |  81 +-----
 ... 8 files changed, 540 insertions(+), 241 deletions(-)
```

**Pinned:** `brief-compose.py` md5 `2184da293d33e63b0e480b971624110b`, manifest md5
`4b269198c76eb1e18a75fedef090c0fa`, snapshot 19:45:50. `--self-test` rc=0, **119/119**;
`check-selftest-counts` rc=0; manifest **13** entries. No `--mutate .` run; every mutation below was
applied to a scratch copy of `scripts/*.py`.

---

## HIGH

### H1 — "The other pages clean themselves up" is true of the accumulation and FALSE of the inheritance, for 32 of 40

I verified your `goals.html` observation independently rather than taking it, and then asked how
many others.

```
goals.html marked? False                      (unmarked -> scan path)
lifted tray selectors include: '#tray #qbox', '#tray #qbox::placeholder', '#tray #qbox:focus'
goals' OWN fragment declares:  []             (zero tray rules)
$ grep -c "#tray #qbox" scripts/gen-goals-page.py
0
=> inherited, from backlog-table or an ancestor

unmarked tray pages: 40   carrying INHERITED #tray #qbox: 32
```

Simulating goals' next regeneration through the shipped code:

```
region that would be WRITTEN BETWEEN THE MARKERS: ['#tray #qbox', '#tray #qbox::placeholder', '#tray #qbox:focus']
```

`_selector_scan` subtracts only rules the page's **own** fragment declares. `goals.fragment.html`
declares none, so nothing is subtracted, and the inherited trio is written **inside the markers** —
where the marker path applies nothing, forever, and `--remigrate` no longer exists.

**The PR body says:** *"The other 43 pages are unmarked and clean themselves up the first time each
is regenerated."* That is **half true, and the half that is false is the half this branch is about.**
The accumulation genuinely cleans up — duplicates collapse, comment-matched rules go, the stacked
`</body>` pairs go. The inherited override does not: regeneration is precisely the event that
converts it from a soft state (re-derived by scan every time, repairable) into a hard one (verbatim
inside markers, unrepairable by any code now on the branch).

**What I am not claiming.** This is bounded and non-growing: one extra rule per page, once. Backlog
#106's own falsifier still passes. Nothing renders wrong today — the trio's declarations are
sensible. The cost is (a) 32 pages carry a tray rule nobody chose for them, (b) that copy outranks
the generator's own at equal specificity, so editing `gen-backlog-page.py:1480` will silently not
reach them, and (c) after regeneration there is no mechanism that can remove it.

**Cheapest correct action, needing no new code:** regenerate nothing until it is decided, or accept
it *with the number in the PR*. The sentence to fix is one sentence. What must not ship is a
verification claim that 32 artifacts contradict.

### H2 — Four clauses of the new function are covered by nothing. You asked for the fourth; there are four

Every clause mutated against the pinned snapshot:

```
[SURVIVED   ] [NOT in manifest] clause 1: selector whitespace NOT normalised          <<<<
[SURVIVED   ] [NOT in manifest] clause 2: the grouped-selector early return is dropped <<<<
[killed(3)  ] [NOT in manifest] clause 3: >=2 becomes >=1, so a BARE tray rule is an override
[SURVIVED   ] [NOT in manifest] clause 4: rooted ANYWHERE, not at parts[0]            <<<<
[killed(3)  ] [NOT in manifest] whole predicate: everything is an override
[killed(5)  ] [NOT in manifest] whole predicate: nothing is an override
[killed(3)  ] [NOT in manifest] CALL SITE: the predicate is not consulted at all
[SURVIVED   ] [NOT in manifest] CALL SITE: the `or keep` fallback is dropped          <<<<
```

The function has two manifest entries. Both attack it wholesale — *"a bare tray rule counts as a
page override"* and *"the predicate is not consulted"* — and between them they pin **clause 3 and
the wiring**. Nothing pins the other three.

**Clause 4 is the one that matters**, because it is the function's central claim. The suite cannot
distinguish *"rooted at a tray part"* from *"mentions a tray part anywhere"* — which is exactly the
Q4 question, and it means `body #qbox` vs `#tray #qbox` is undefended by any case. Production edit
that should fail a named case: `re.search(TRAY_SELECTOR, parts[0])` → `…, selector)`. Today: nothing
goes red.

**Clause 2** is the grouped-selector rule the docstring calls out in its own ⚠ paragraph
(*"A GROUPED selector is not an override"*). Deleting the early return changes nothing the suite can
see. **Clause 1** is the whitespace normalisation — no fixture has a tab, newline or double space in
a selector.

This is the same shape as r3's three survivors and the branch's earlier three: **the guard's
existence is cased; its content is not.** Four rounds, four instances. That is no longer a series of
accidents; it is the default outcome of writing the case from the fix rather than from the clause.

---

## MEDIUM

### M1 — `or keep` is live, unguarded, and its case has been hollowed out

The manifest entry *"the subtraction is allowed to empty the tray, so nothing composes at all"* was
**removed** this round. Removing it was right — I confirmed the mutation no longer kills. But the
**clause it guarded is still in the code**, and the case that named it now passes for a different
reason than it was written for:

```
the OLD case fixture ("#tray{a:1}\n#qbox{b:2}" declared by the fragment)
  -> subtracted = ['#tray{a:1}', '#qbox{b:2}']      NOT empty
  => the or-keep branch is not what makes that case pass any more
```

`_is_page_override` protects bare rules, so the fixture can never empty `subtracted`. The branch does
execute once in the whole suite — and only from here:

```
extract_tray("<style>body{a:1}</style><div>no tray</div>")   # the "no tray at all" fixture
```

where `keep` is empty *before* subtraction and `extract_tray` raises either way. So the branch is
reached and its result is never asserted, which is why the mutation survives.

**Recommendation: delete `or keep`.** With `_is_page_override` in place, the state it defended — a
fragment declaring every tray rule — requires a "tray" whose every rule is descendant-rooted, i.e.
not a tray. On that degenerate input, returning the unsubtracted set *silently* is the fail-silent
behaviour; letting `css` go empty makes `extract_tray` refuse, which is the module's stated contract.
*Falsifier for my proposal:* the backlog #88 fixture and the two bare-rule cases must stay green, and
`extract_tray` must still raise on the no-tray fixture.

### M2 — The premise is false in six shapes, and true in one it should not be

Answering Q1 by enumeration:

| selector | override? | |
|---|---|---|
| `#tray #qbox` | ✅ True | the canonical one |
| `#tray > #qbox` | ✅ True | spaced child combinator |
| `#tray>#qbox` | ❌ False | **unspaced — missed** |
| `#qbox.wide` | ❌ False | compound, more specific — missed |
| `body #qbox` | ❌ False | rooted elsewhere — missed (Q4) |
| `html #tray #qbox` | ❌ False | rooted elsewhere — missed |
| `#qbox:focus` | ❌ False | pseudo-class — missed |
| `#tray #qbox, #tray #qt` | ❌ False | grouped — missed |
| `:where(#tray) #qbox` | ⚠ **True** | **zero specificity — does NOT win the cascade, yet classed as an override** |

**Six misses, all in the safe direction** — an unrecognised override is not subtracted, so nothing is
destroyed; the pollution merely persists (and feeds H1). I would not fix them individually.

Two are worth a line each. `#tray>#qbox` and `#tray > #qbox` classify **differently** on whitespace
alone, which no principle justifies. And `:where(#tray) #qbox` is the only false positive: `:where()`
contributes zero specificity — SHIM's own comments rely on this — so it is not functioning as an
override, yet it is subtractable. Damage is bounded by the residual (the page itself declares it; a
descendant loses it).

**Answering Q4 directly: rooting on `parts[0]` is right for what it claims and incomplete as a
definition of "override".** The justification — shape is intent, per `gen-backlog-page.py:1480` — only
licenses the rooted form, so the narrow reading is honest. It should say *"the overrides we emit"*
rather than *"a page override is"*.

---

## LOW

### L1 — `#tray .in` is the one live genuine tray rule the predicate would subtract

Answering Q2 against the real region:

```
SUBTRACTABLE  #tray .in
(every other rule in the live region is bare and therefore protected)
```

`#tray .in` styles the tray's inner container. It is a genuine tray rule and it is descendant-rooted,
so the new predicate classifies it as a page override; a fragment duplicating it byte-identically
would remove it. Same residual shape as before, now narrowed to exactly one rule out of fifteen —
which is a large improvement and worth recording as such.

### L2 — Parsing is solid; two curiosities

Answering Q3: tabs and newlines normalise correctly (`#tray\t#qbox` → True, `#tray\n  #qbox` → True);
a comment inside the selector is moot in production because `_tray_rules` strips it first; a trailing
space correctly yields `False`. The `,` early return is right for `#tray, #qbox #qt` — a grouped
selector is one rule for several parts. The only oddity is `'#tray >'`, a dangling combinator, which
returns **True**; it requires malformed CSS to arise.

---

## WHAT THE DELETION GOT RIGHT

Answering Q6 beyond M1: I checked all 15 removed cases against the surviving code. Fourteen pinned
`--remigrate`, `pollution()` or `remigration_risk()` and are correctly gone with their subjects —
retired *with* the thing they described, which is the sanctioned kind of coverage fall. Only the
`or keep` entry left a live clause behind (M1). The two new cases are real: I verified
`a fragment duplicating a BARE tray rule never subtracts it` and its `all(...)` sibling both go red
under clause 3's mutation and under `return True`.

Deleting rather than fixing a third time was the right call, and the shape of the fix is better than
what it replaced: a rule about **what may be subtracted at all**, applied before subtraction, instead
of a floor checked afterwards. r3's Blocking is structurally impossible now, not merely guarded.

---

## Q7 — IS ACCEPTING H3 DEFENSIBLE? PARTLY, AND THE r3 FALSIFIER HAS FIRED

**As a residual: yes.** Inherited pollution is bounded, non-growing, one rule per page, and renders
correctly today. Declining to build a third generation of repair machinery to chase it is a sound
call — the previous two generations each produced a Blocking.

**As stated: no**, for two reasons.

1. **The number is missing and it is 32, not "some".** A residual accepted without its magnitude is
   not accepted, it is deferred silently. And the acceptance is not neutral: H1 shows the state
   becomes *irreversible* on ordinary regeneration, so "accept" here means "accept permanently, for
   32 artifacts, starting the next time anything regenerates".
2. **It contradicts a verification claim in the PR.** Both cannot ship.

**And this is where I have to hold myself to what I wrote.** r3's override falsifier said:

> *fires to REDESIGN if round 4 produces a finding that requires knowing which rules are canonically
> the tray's — i.e. if any fix for B1, H2 or H3 needs a trusted reference tray.*

H1 is exactly that. There is no way to stop 32 pages freezing a rule nobody chose without a statement
of what the tray canonically **is** — `_selector_scan` cannot tell an inherited override from a tray
rule, because by the time it sees it, the fragment that declared it is not the fragment being asked.
**The falsifier has fired and I am not going to explain it away.**

What I am *not* saying is that this branch should be reopened for a redesign. The redesign is small,
it is orthogonal to #106, and it is the same one I named in r3: **check in a canonical tray file and
read it**, at which point `_selector_scan`, `_is_page_override` and the whole notion of inferring the
tray from whichever page is newest collapse into one read. #106's own falsifier passes; that work is
done. This should be **filed as its own backlog row with the 32-page measurement and the
irreversibility trigger**, and the PR sentence corrected — not folded into round 5.

---

## VERDICT

**NOT CONVERGED.**

**The single most important thing to fix: H1** — not by writing code, but by correcting the sentence
and deciding, with the number in front of you, whether 32 pages should freeze an inherited rule on
their next regeneration. It is the only finding here that is **irreversible**, and it becomes
irreversible through completely normal operation, which is the worst property a defect can have.

Ranked: **High ×2** (H1 the 32 pages; H2 four uncovered clauses). **Medium ×2** (M1 `or keep` live
and unguarded; M2 the premise's six misses and one false positive). **Low ×2**. **No Blocking** —
and that is the first time in four rounds, which is the real news: the new function cannot do the
class of damage its three predecessors could.

**Stop-condition counter: reset to 0 for the transform.** H1 is not caused by r3's fix — it is an
older condition that r3's *deletion* newly exposed, and the deletion was correct. H2 and M1 are
coverage, not mechanism. The r3 falsifier fired on H3, and I have routed that to its own backlog row
rather than to another round here, because a fifth round on this branch would be attacking a design
that is now right.

⚠ Pinned to `brief-compose.py` md5 `2184da29…`, manifest md5 `4b269198…`. Tree clean throughout.
