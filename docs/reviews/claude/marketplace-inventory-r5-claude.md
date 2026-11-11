# Round 5 — Claude half

**Subject:** `marketplace-inventory` (PR #376), commits `2e79f464..ae12bb3f`. Reviewing **the
coordinator's response to the Codex half** (`docs/reviews/coordinator/marketplace-inventory-r5-coordinator.md`),
per `review-method.md`'s alternating rule for rounds 2+.

**NOT CONVERGED.** 4 High, 3 Medium, 1 Low. No Blocking.

**The two Codex Highs are genuinely closed** — I re-verified both on tag-stripped text in BOTH
pages, and both citations resolve to the right spec sections. **But the repair is incomplete in the
way the dispatch suspected**, and the two new guard fixes each pin the instance they were handed
rather than its class:

- a **fourth** #297-class drift exists that tag-stripping would not have found (H3);
- the VOID case that explicitly claims to pin *"THE WHOLE VOID VOCABULARY, NOT ONE MEMBER"* pins
  **6 of 14**, and all 8 unpinned members survive (H1);
- the new `CANONS` case pins the string `"CONTEXT.md"`, not the class — `"./CONTEXT.md"` passes
  28/28 while reproducing the exact CI failure it was written to prevent (H2).

---

## What I executed

Every finding below was run, not reasoned about. Controls proved green before each mutation and
restored green after.

| # | Executed | Result |
|---|---|---|
| A | #297's three drifts re-verified on both pages with tags stripped via `html.parser` | **all three gone**; both new citations (§4b, §4d) resolve correctly |
| A⭐ | D1–D9 and C1–C5 compared spec ↔ both pages; then every spec withdrawal (`⟳`/`withdraw`/`struck`) searched for its retired form on the page | **one fourth drift found** (H3) |
| B | each new case broken at the code it names, watching which case reddens | all 3 discriminate; **the void loop leaves 8 of 14 members unpinned** (H1) |
| B | `"./CONTEXT.md"` / `"CONTEXT.md"` / `"docs/../CONTEXT.md"` against the new `CANONS` case | **only the bare spelling is caught** (H2) |
| C | all three suites run; manifest diffed against `8a583f7c^` by mutation identity; declared sum summed over all 63 manifests | **49/49, 28/28, 178/178; 18 + 7 entries; 17 retired — the coordinator's figures are correct** |
| C | scoped `--mutate .` over both changed manifests, in a pruned copy of all 7 `HARNESS_TREE` paths | **25 mutations, 25 killed, 25 attributed, 0 survivors — independently reproduced** |
| E | AST scan for dead symbols; deleted self-test **case** names diffed pre-shed → HEAD and each classified | **no dead code; every deleted case is prose-matcher; the carrier cases survive** |
| E | `audited_sites` / `CannotRun` paths with only `DERIVED` feeding `wanted`; M4's substitution mutation re-run | **correct**; M4's claim verifies exactly as written (`rc=1`, 1 `[FAIL]`, 0 tracebacks) |
| F | all 25 citing sites of the guard swept for false statements about the narrowed contract | **2 live false statements** (M1, M2) |

---

# Blocking

None.

# High

## H1 — The void case claims to pin the vocabulary and pins 6 of 14. All 8 unpinned members survive.

**Files:** `scripts/check-claim-propagation.py:653` (the loop), `:144-146` (`VOID`), `:649` (the claim).

The case was added by this round's fold and its comment states the reasoning explicitly:

> `# 2 — ⭐ THE WHOLE VOID VOCABULARY, NOT ONE MEMBER. Reducing VOID to {"img"} left the suite`
> `# green: the existing witness only ever proved img. This is the same mistake the DELETED`
> `# prose matcher made three times (each fix covered the spelling its finding named), so the case`
> `# is a LOOP over the set rather than a member of it.`

The loop is over a **hardcoded 6-tuple**, not over the set:

```python
for _v in ("br", "hr", "wbr", "col", "input", "img"):
```

`VOID` has **14** members. The loop is therefore a second copy of the vocabulary — the spellings
the finding named plus five the author chose — which is the defect the comment says it avoids.

**The observation that makes it fail:** remove any of the 8 uncovered members from `VOID` and the
suite stays green.

```
VOID members : 14 ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']
loop covers  :  6 ['br','col','hr','img','input','wbr']
UNPINNED     :  8 ['area','base','embed','link','meta','param','source','track']

# drop ALL 8 unpinned members from VOID:
49/49 self-test cases passed
# drop one ('area'):
49/49 self-test cases passed
```

Each such member is a live defect in the guard: a `<link data-derived="k">` carrier would be pushed
onto the stack and swallow the rest of the document into the value.

**⛔ And the obvious fix is wrong — I measured it, because it is what a fold would reach for.**
Looping over `_Carriers.VOID` itself makes the fixture derive from its own subject, so a mutation
to `VOID` silently *shrinks the case list* instead of reddening:

```
loop over _Carriers.VOID  + 'area' removed from VOID:
56/56 self-test cases passed      # was 57/57 — the case COUNT fell; nothing failed
```

That is this repository's `a-case-can-pass-for-an-ambient-reason` / `a-sever-substitutes-todays-value`
shape. **The fix that works is an independent literal plus an identity case**, verified:

```python
_VOID_EXPECTED = "area base br col embed hr img input link meta param source track wbr".split()
case("derived: the VOID vocabulary is exactly the 14 HTML void elements",
     sorted(_Carriers.VOID), sorted(_VOID_EXPECTED))
for _v in _VOID_EXPECTED:
```

```
control:                     58/58 passed
drop 'area' from VOID:       2 of 58 FAILED
  [FAIL] derived: the VOID vocabulary is exactly the 14 HTML void elements: got [...13...] want [...14...]
  [FAIL] derived: a <area> carrier captures nothing that follows it: got {'k': '771 after it'} want {}
```

Add a manifest entry dropping one unpinned member, expecting the identity case.

---

## H2 — The new `CANONS` case pins the SPELLING, not the class. `./CONTEXT.md` passes 28/28 while reproducing the CI failure.

**File:** `scripts/check-canonical-source.py:535-536`.

```python
case("CANONS: no declared citing site is a repo-root file (HARNESS_TREE stages none)",
     sorted(c for canon in CANONS for c in canon["cites"] if "/" not in c), [])
```

The predicate is `"/" not in c`. The consumer at `:378-380` is `cp = root / cite_rel`, so
`"./CONTEXT.md"` and `"CONTEXT.md"` resolve **identically** — but only the second has no `/`.

**The observation that makes it fail.** Control green first (28/28), then the offending entry
re-added under each spelling:

```
########## cites entry re-added as: ./CONTEXT.md
  self-test: 28/28 passed                                    <== SLIPS PAST
  staged-tree (HARNESS_TREE shape, no root files): rc=1
  ✗ ./CONTEXT.md is declared a citing site but does not exist
########## cites entry re-added as: CONTEXT.md
  self-test: 27/28 passed
  [FAIL] CANONS: no declared citing site is a repo-root file (HARNESS_TREE stages none): got ['CONTEXT.md'] want []
  staged-tree: rc=1
```

So the exact failure the case exists to prevent — the one that put **6 of 8 mutation shards into
NOT MEASURED** — is still reachable, under a spelling a reader would consider equivalent.

**Verified fix** (control green, all three spellings caught):

```python
if "/" not in os.path.normpath(c)
```

```
control:                    28/28 passed
  ./CONTEXT.md           -> 1 repo-root case failure(s)
  CONTEXT.md             -> 1 repo-root case failure(s)
  docs/../CONTEXT.md     -> 1 repo-root case failure(s)
```

---

## H3 — ⭐ A FOURTH #297-class drift, which tag-stripping would not have found: the page's `11,624 lines / 647 shared contracts` is undated and false at HEAD.

**Files:** `docs/explainers/…walkthrough.fragment.html:368` and `…walkthrough.html:445`.
**Canon:** `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md:225`.

The spec states the figure **with its commit**, because §3 is the section whose entire subject is
that counts decay:

> **The total, for scope sizing only, measured at `a4f6d4b5`:** 10,373 Python + 604 skills + **647**
> shared contracts = **11,624 lines** across the 17 components of effort (3).

The page restates all of it and **drops the provenance**:

> `<p class="prov"><strong>Scope sizing, a different and larger set:</strong> effort (3)'s 17`
> `components total <strong>11,624 lines</strong> — 10,373 Python (…) + 604 skills + 647 shared`
> `contracts.`

No commit, no date, in either page. **The spec says in the same section that these very figures are
false at `HEAD`** (`:174`: *"At `HEAD` the shared contracts are therefore no longer 647 and the nine
files no longer 6,542"*). Measured:

```
=== at HEAD ===        explainer-delivery 381 + corpus-search 73 + handoff-path 211 = 665
=== at a4f6d4b5 ===    explainer-delivery 363 + corpus-search  73 + handoff-path 211 = 647
page's 11,624 recomputed at HEAD: 10373 + 604 + 665 = 11642
```

So the page asserts `647` and `11,624` as present-tense fact where the truth is `665` and `11,642`.

**Why this matters more than the arithmetic — three things:**

1. **It is the retired form, reinstated.** Round 4 (r4 CLAUDE B1) found the component table carrying
   `346 / 73 / 211` **undated** and fixed it by dating the row. The page carries the same class of
   undated count, and nobody checked the page.
2. **The coordinator's root cause would not have caught it.** `647` is in plain text with no
   intervening tag. Stripping tags first changes nothing here. What was missing was not an
   instrument but a sweep of the class.
3. **It is in an uncovered class, confirmed.** `DERIVED` holds exactly two keys — `spec-path` and
   `spec-lines` (`:104-120`) — so nothing mechanical sees this figure, and ADR-0015 deliberately
   declined to extend it here (it would hold a second copy of the nine-file enumeration). Backlog
   **#295**'s corpus pass — *"every figure derivable or dated"* — is the standing remedy, and this
   drift is the evidence that it is the real one rather than the per-instance fixes.

**Fix:** date the page's block (`measured at a4f6d4b5`), exactly as the spec's row was dated.

---

## H4 — The spec's `(660 at HEAD)` was wrong when it was written, is wrong now, and reinstates the `HEAD` label round 4 explicitly retired.

**File:** `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md:124`.

```
| `.agents/skills/shared/` — … | **363 / 73 / 211** at `a4f6d4b5` (660 at `HEAD`; see §3's dated row) |
```

`git log -S` puts that text at `2e79f464` — the commit that opens this review range, the one whose
subject line is *"I argued past a gate that had already fired."* Measured at that commit and now:

```
shared total at 2e79f464 (where '660 at HEAD' was written):
  explainer-delivery=379  corpus-search=73  handoff-path=211   TOTAL=663   (spec claims 660)
shared total at HEAD:                                          TOTAL=665   (spec claims 660)
```

**Wrong by 3 the moment it was typed, wrong by 5 today.** And `:151` of the same file is the
round-4 correction that retired this exact label:

> ⛔ **THE THIRD ROW IS DATED, AND IT USED TO SAY `today` / `HEAD` — CORRECTED 2026-10-16 BY ROUND 4
> (CODEX B1)… A label reading `today` is therefore false the moment anything ships, and a dated row
> is the only form that stays true — which is **this section's own rule**.**

A `HEAD`-labelled figure 27 lines above that paragraph is the section contradicting itself.
**Fix:** drop the parenthetical, or date it. The `a4f6d4b5` half is correct and should stay.

---

# Medium

## M1 — `.github/workflows/ci.yml:312` names the step after a check ADR-0015 deleted.

```yaml
      - name: One rule, one place — a retired claim is not re-asserted
        run: python3 scripts/check-claim-propagation.py
```

*"A retired claim is not re-asserted"* is, verbatim, one of the **two halves the ADR removed** (the
guard's own docstring, `:24-26`: *"Two checks are GONE: *a RETIRED claim is not re-asserted*, and
*a LIVE claim reaches every site that must state it*"*). The step name is the label a reader sees on
a red required check, and it is now false. The comment block above it (`:305-311`) is false for the
same reason — it describes the token matcher (*"a rule restated in words no registered token matches
is invisible to it"*).

⚠ **The repository has already paid for a wrong name on this same guard**, and the note saying so
sits nine lines below the defect (`:318`): *"that wording was this guard's own defect (r6 CLAUDE H5)
and is corrected at all three sites it stood at."* The fold corrected `CONTEXT.md` and
`explainer-delivery.md` and did not sweep the workflow.

**Fix:** rename to its actual subject, e.g. *"A page's derived figure agrees with its producer"*.

## M2 — The roadmap bullet whose fifth number the fold corrected still carries four superseded ones.

**File:** `docs/roadmap-to-launch.md:2404-2407`.

```
- [x] **`scripts/check-claim-propagation.py` reduced to its derived-figures half** — 1,459 → 828
      lines, **41** self-test cases (was 96), **15** mutations, **15 killed and attributed over a
      green control with 0 survivors**, measured by a scoped `--mutate .` run. Declared sum
      1488 → 1472: a ratchet **FALL**, permitted because **17** entries are **retired with their
      subject** (⟳ r5 CODEX Low: this said 19…)
```

Measured actuals: **49** cases, **18** mutations, **25** killed (both manifests), declared sum
**1476**. The fold edited this sentence to correct `19 → 17` and left the four numbers beside it
stale — *"a fix inside a heredoc is not a class fix"*, applied to a sentence.

**Nothing mechanical covers it.** `check-selftest-counts.py` reads each script's own docstring and
is green (*"54 script(s) declare a count, every one verified by running it"*); the roadmap figure
has no owner. The append-only dashboard store is **correct** here — the superseded entry at
`docs/dashboard-entries.md:15477` stands beside its correction at `:15527`, which carries 49 / 18 /
1476. The roadmap is the live status document and carries no corrected figure anywhere.

## M3 — ADR-0015's Decision (3) states a measurement that was false at the commit that wrote it, and it is one of the ADR's own four falsifiers.

**File:** `docs/adr/0015-a-page-paraphrases-freely-and-cites-decision-symbols.md:72-74`.

> The tokens are therefore distinctive multi-word forms (`DON'T-SHIP`, `harvest: practice`,
> `SHIP /`, `BEST-EFFORT, VERSIONED`, `harvest: none`, `C4 is STRUCK`), each measured to occur in
> the spec and in **0** files outside the governed pair once the propagation registry is shed.

The ADR's *Falsifier* section then says: *"**The token set stops being distinctive** — any token here
reaching a file outside the governed pair means the oracle has become a false-positive generator,
and the measurement in *Decision* (3) must be re-run rather than assumed."*

Measured at `650ef620`, the ADR's own commit, excluding the governed pair:

```
C4 is STRUCK             2 file(s)      docs/adr/0015-….md, scripts/check-canonical-source.py
BEST-EFFORT, VERSIONED   2 file(s)      docs/adr/0015-….md, scripts/check-canonical-source.py
DON'T-SHIP               4 file(s)      CONTEXT.md, docs/adr/0015-….md,
                                        scripts/check-canonical-source.py, scripts/check-claim-propagation.py
```

`CONTEXT.md` is **not** exempt (`EXEMPT = ^(docs/reviews/|docs/dashboard-entries\.md$)`, `:241`).

⚠ **The mechanism is fine and I verified it** — the guard is green because every one of those sites
cites the canon, which is the design working as ADR-0015 describes. The defect is the **sentence**:
`0` is not the measurement, and stating it as measured is the repository's `an-inference-stated-as-measured`
shape in the decision of record. **Fix:** restate with its real exclusions — the registry that
declares the tokens, the ADR that decides them, and `docs/reviews/**` — or give the count as
*"0 non-citing files"*, which is what the guard actually establishes.

---

# Low

## L1 — The strip case's stated mechanism is invented; the behaviour is unobservable through `audit()`.

**File:** `scripts/check-claim-propagation.py:643`.

> `# every padded carrier silently gained surrounding whitespace, which int() then rejects as a`
> `# figure mismatch rather than as the parsing defect it is.`

There is no `int()` in either compare path. `:302` is `digits = re.sub(r"[^0-9]", "", claimed_raw)`
and `:337` is `claimed_raw.strip() != actual` — **both neutralise padding.** Measured on the real
pages, control green first:

```
### CONTROL: real audit on the real repo
derived figures OK — 2 figure(s) agree with their source          rc=0
### MUTATION: self.derived[key] += data   (padding enters the value)
derived figures OK — 2 figure(s) agree with their source          rc=0
  fragment.html {'spec-lines': '1137', 'spec-path': 'docs/…-design.md'}
  html          {'spec-lines': '1137', 'spec-path': 'docs/…-design.md'}
```

Byte-identical values, same verdict. Per `review-method.md:160-167` — *"Ask 'what caller reaches
this state?' of every measured defect"* — the gap closed here has no reachable caller on today's
pages; it is reachable only for a page shaped differently (a path split across nodes with internal
whitespace), where the mutated code gives a *false positive*. **The case is sound and worth keeping;
its justification is not.** Fix the comment to say what it actually pins: `_derived_values` returns
stripped text, and the compare paths must not be the only thing standing between padding and a
figure.

---

# The three questions, answered

## 1. Is this CONVERGED?

**No.** H1 and H2 are defects in code committed by the fold under review; H3 is a live false
statement in both delivered pages; H4 is a live false statement in the spec.

**Executed rather than read:** A (both halves — re-verification *and* the fourth-drift hunt),
B (all three new cases broken individually, plus the `CANONS` case against three spellings, plus
two candidate fixes measured), C (all three suites, the manifest diff by mutation identity, the
63-manifest sum, and a full scoped `--mutate .` reproducing 25/25/25/0), E (AST dead-symbol scan,
deleted-**case** classification, the `audited_sites`/`CannotRun` paths, and M4's mutation re-run),
F (all 25 citing sites). I did **not** re-run Codex's 20,000 differential parser inputs, as
instructed, and I did not execute all 1,476 manifest entries.

## 2. Thrashing or prose floor?

**Neither. It is branch-coverage plus stale cross-reference — so the architecture review stays
un-armed. I reach the coordinator's conclusion and reject its reasoning.**

`review-method.md`'s definition, quoted rather than paraphrased:

> `:525` | **Thrashing** | findings are **introduced by the previous round's own fix**; severity
> stays put | the design is fighting itself — a real architecture problem | **the architecture
> review.** …

> `:173` **If a component produces findings caused by the PREVIOUS round's fixes in two consecutive
> rounds, it escalates from FIX to REDESIGN, and the next round is a design review — not another
> defect hunt.**

> `:541` The question to answer, out loud and per finding, is: *did the previous fix cause this?* If
> yes for a meaningful share of the round, it is thrashing and the count is irrelevant.

Per finding:

| # | Introduced by the previous round's own fix? | Evidence |
|---|---|---|
| H1 | **YES** | the loop was written by `ae12bb3f`, this round's fold, answering r5 CODEX M3 |
| H2 | **YES** | the case was written by `ae12bb3f` |
| H3 | No | pre-existing; no round ever checked the page's figures |
| H4 | **YES** | written by `2e79f464`, and wrong at that commit (663 vs 660) |
| M1 | Partly | the shed (`8a583f7c`) made the name false; the fold corrected two sibling sites and not this one |
| M2 | **YES** | the fold edited this exact sentence and left four numbers in it stale |
| M3 | No | written by `650ef620`, false at that commit, never checked |
| L1 | **YES** | the comment was written by `ae12bb3f` |

**5 of 8 are fix-induced** — comfortably "a meaningful share". So by `:541` alone this *looks* like
thrashing, and it is the second consecutive round in one component (round 4 was declared thrashing,
8 of 9; r5 CODEX M3 was fix-induced by the coordinator's own words — *"gaps **I introduced** by
reducing `_Blocks` to `_Carriers`"*).

**⛔ But `:197` is the test, and the symptom list is explicitly not:**

> ### Can a redesign remove it?
> If a different shape would dissolve the finding, it is a mechanism defect and the redesign is
> owed. If the same finding would survive every reasonable reshaping … it is not.

Applied:

| # | Can a redesign remove it? | Kind |
|---|---|---|
| H1 | **No** — a 3-line literal + identity case, verified above | branch-coverage |
| H2 | **No** — a 1-line predicate change, verified above | branch-coverage |
| H3 | **Partly** — and the redesign is already filed and already chosen (#295's corpus pass); ADR-0015 reasoned about and rejected extending `DERIVED` here | branch-coverage, with the design answer on record |
| H4 | **No** — drop a parenthetical | stale cross-reference |
| M1 | **No** — rename a step | stale cross-reference |
| M2 | **No** — four numbers | stale cross-reference |
| M3 | **No** — one sentence | stale cross-reference |
| L1 | **No** — one comment | stale cross-reference |

Not one is a mechanism defect. **Four are the third outcome `:214` names explicitly** — *"A decision
changed and some sentences still state the old one"* — whose remedy is neither a redesign nor an
exhaustiveness pass but: **"When a decision is reversed, grep for every place that stated the old
one. A rewritten section does not rewrite its own cross-references."** That is exactly ADR-0015's
situation one commit after landing.

**So: do not re-arm. But the coordinator's stated reason has three holes, and they matter because
inventing a thrashing argument is this branch's recorded failure (`2e79f464`).**

1. It applies the test **only to the two Highs** (*"Its two Highs are not caused by the
   architecture review's redesign"*), where `:541` says per finding across the round.
2. It **contradicts itself four paragraphs apart**: *"These are gaps **I introduced** by reducing
   `_Blocks` to `_Carriers`"* under M3, then *"M3 is genuinely new ground"* in the verdict. The
   first sentence is the thrashing definition verbatim.
3. It never quotes or applies `:197`, the one test the repo's own 2026-08-14 measurement says to use
   *instead of* the symptom list — and `:197` is what actually carries the verdict it wants.

The right record is: **fix-induced in 5 of 8, and not thrashing anyway, because every one is
branch-coverage or a stale cross-reference and no reshaping removes any of them.** "False closure,
not thrashing" is a true description of H1/H2's *history* and the wrong frame for the *gate*.

## 3. Is `[^<>]` cannot cross a tag` a sufficient root cause?

**No. It is a true account of one instrument and the wrong level for the method.** Three pieces of
evidence from this round:

1. **H3 is a #297-class drift with no markup involved.** `647` sits in plain text. Tag-stripping
   changes nothing about finding it. What would have found it is comparing the spec's §3 figures
   against the page's — i.e. sweeping the class, not re-running a better regex on the three
   instances the architecture review happened to file.
2. **Both new guard fixes repeat the shape at a different altitude.** H1's comment *asserts* the
   loop covers the vocabulary; `len(VOID)` vs `len(loop)` refutes it in one line. H2's case
   *asserts* `"/" not in c` is the class; `"./CONTEXT.md"` refutes it in one try. Neither was run
   against a known negative. That is `measure-the-population-the-code-actually-sees` — **"check a
   KNOWN POSITIVE before trusting a negative"** — and it is the same error as the `[^<>]` regex, with
   the regex replaced by a predicate the author wrote for the instance in front of them.
3. **M2 is the method in miniature:** handed *"19 is wrong, it's 17"*, the fold corrected 19 and left
   `41`, `15`, `15` and `1472` in the same sentence.

**The deeper root cause:** *the coordinator verifies a fix against the instance a reviewer named,
using a predicate it authors for that instance, and does not run that predicate against a case it
expects to fail.* Tag-stripping fixes the instrument; it leaves the method — one instance, one
hand-written oracle, no negative control — intact. The repository already owns the remedy and names
it twice: `after-fixing-search-for-the-class`, and `a-case-can-pass-for-an-ambient-reason`'s rule —
**"Flip what the case names, check it reddens"** — which, applied to H1 and H2 before committing,
would have caught both in under a minute.

⭐ **The mechanism worth keeping from this round** is the one H1 produced by accident: the *obvious*
class fix (derive the loop from `VOID`) is **unsound**, because a fixture that derives from its own
subject shrinks instead of reddening. A class fix needs an independent copy plus an identity
assertion — which is the one place in this codebase where the second copy is correct, and it is
worth writing down beside `a-second-implementation-of-one-rule-drifts`.

---

## Note, out of scope for this branch

`scripts/check-test-counts.py` prints *"FAIL (cannot run): no jest results … Treat this check as NOT
RUN"* and **exits 0**. The words are right and the exit code contradicts them, against the spine's
*"'Cannot run' is a FAILURE, never a pass."* Untouched by this branch; recorded because I ran it.

## Measured state

| check | result |
|---|---|
| `check-claim-propagation --self-test` | 49/49 |
| `check-canonical-source --self-test` | 28/28 |
| `check-plan-code --self-test` | 178/178 |
| `check-selftest-counts` | 54 declarations, all verified by execution |
| `check-docs` | OK |
| scoped `--mutate .`, both changed manifests, 7/7 `HARNESS_TREE` paths staged | 25 mutations, 25 killed, 25 attributed, 0 survivors; controls and re-controls green (15.1s) |
| manifest retirement count, by mutation identity vs `8a583f7c^` | 21 names gone − 4 retarget re-adds = **17 retired**; 32 − 17 = 15, + 3 new = 18 ✓ |
| declared sum over all 63 manifests | **1476** actual = 1476 declared ✓ |
| #297's three drifts, both pages, tags stripped | **all absent**; §4b and §4d both resolve correctly |
| `check-test-counts` | **CANNOT RUN** — treat as NOT RUN |
