# Round 3 — Claude half, `marketplace-inventory`

**NOT CONVERGED** — 1 Blocking, 4 High, 9 Medium, 3 Low.

Reviewed `278b2d84` in a worktree. Round 3's Codex half was read first; both of its Blockings were
re-measured here from scratch and **both of its re-measurements reproduce exactly** — the fold's
corrections to B1 and B2 are right, and nothing below re-opens them. What is below is the fold
itself: three of the four Highs are the same propagation mechanism this branch exists to study,
found at the site the previous round's finding did *not* name, and the Blocking is a live fail-open
in the guard that was built to close that class.

Shorthand: **S** = `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md`,
**P** = `docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html`,
**H** = its composed `.html` sibling, **G** = `scripts/check-claim-propagation.py`.

---

## B1 — Blocking: the retirement-marker vocabulary is a live fail-open, and the code asserts it cannot be

**Site:** `G:253-265` (`RETIREMENT_MARKERS`), consumed at `G:378` (HTML) and `G:393` (markdown).

**What the code claims**, at `G:250-252`:

> `# A block counts as a marked retirement when it carries one of these. Deliberately narrow:`
> `# each is a token this project already uses to mark a correction, so the exemption cannot be`
> `# satisfied by ordinary prose that happens to mention the rule.`

**The observation that refutes it.** Four of the eleven members are ordinary English words, not
correction marks: `"previously"`, `"no longer"`, `"corrected"`/`"Corrected"`, `"retired"`. A block
that *asserts* a retired rule is exempted outright if it happens to contain any of them anywhere.
Against the **real tree**, not a fixture — I copied S/P/H into a temp root and appended one sentence
to the real spec:

```
A library inherits its support verdict from the entry-points; the mix rule is no longer in doubt.
```

`audit()` reported **no retired-claim problem at all** — only the two expected `spec-lines` drifts
caused by my own added lines. The registered token `inherits its support verdict from the` is
`RETIRED[0]`, retired because r2 refuted it; it was re-asserted in the present tense and the gate
stayed silent, because `"no longer"` is in the vocabulary.

Four constructed blocks, all `(asserted, quoted) == (0, 1)` — i.e. all exempted:

```python
'<p>A library inherits its support verdict from the entry-points, a rule that was previously debated.</p>'
'<p>A library inherits its support verdict from the entry-points. This is no longer in dispute.</p>'
'<p>A library inherits its support verdict from the entry-points, and retired components are excluded.</p>'
'<p>A library inherits its support verdict from the entry-points. The corrected list is below.</p>'
```

The markdown path behaves identically (`_markdown_occurrences` of the first sentence → `(0, 1)`).

This is strictly worse than a coverage gap, which is why it is Blocking rather than High: r3 CODEX
H1 and H2 were each *silence about a case*, and were graded High. Here the delivered code states the
property it does not have, in the one file whose entire subject is a claim that disagrees with its
site. By r3's own calibration the fail-open half alone is a High; the grade is for the assertion.

**Why the existing coverage cannot see it.** I removed each of the eleven markers individually and
ran the suite plus a real-tree audit. Only `⟳` reddens anything; the other **ten removals leave
45/45 green and the real tree at rc=0**. Codex reported that ratio in its *could not refute* section
and read it as a coverage limit. It is not only that — four of those ten are the fail-open above,
and the comment three lines up denies it.

**What I ran:** the real-tree append shown above; `_html_occurrences` / `_markdown_occurrences`
directly on the four blocks; a scripted sweep deleting one `RETIREMENT_MARKERS` member per run
(11 runs, self-test + `--root <repo>` each).

**Falsifier for this finding:** a word-boundary or line-position rule on the weak markers, or their
removal, making any of the four blocks above score `(1, 0)`.

---

## H1 — High: §9c tells the approver a decision is open in §4 that §4b decided, and the page already says so

**Sites:** `S:1050` (§9c, last paragraph) against `S:473-531` (§4b / D5); `P:683-690`.

**What S:1050 claims:**

> ⛔ **ONE FINDING IS DELIBERATELY NOT FOLDED** — whether `SHIP` may be recorded without demonstrated
> C4 evidence. It changes what this milestone promises rather than how it is reached, so it is the
> owner's decision and **is stated as an open question in §4.**

**The observations that refute it, two of them.**

1. `grep -n -i "open question" S` returns **exactly one line: 1050 itself.** §4 states no open
   question. The pointer has no referent.
2. The question is *already decided, by the owner*, as D5: `S:508-510` reads **"`SHIP` + `argued` is
   permitted, and is the honest label for efforts (1) and (2)"**, where `argued` is defined at
   `S:500` as *"C1–C3 plus reasoning; no experiment reached it"* — i.e. precisely *`SHIP` without
   demonstrated C4 evidence*. §4b's header: *"SETTLED 2026-10-16 BY THE OWNER … Recorded as a
   decision of record; do not re-open."*

**And the page knows.** `P:683` opens *"What was left at the time — **and you have since decided
it, as D5 above**"*, and `P:690` carries *"✅ **You chose this, and it is now D5 — a decision of
record above.**"* So the page was folded and §9c was not: **the page and the spec now disagree about
whether the milestone's one deliberately-unfolded decision is still open.** That is this branch's
measured failure mechanism, in the fold that built the guard for it — and G registers no token for
it, so the gate is green over the disagreement.

The cost is at the human gate specifically: §9c is the last substantive paragraph before §10, so a
reader walking the spec is told at the end that a promise-changing decision awaits them in §4, and
will either hunt for something that is not there or re-open D5.

**What I ran/read:** `grep -n -i "open question"` over S and P; `sed -n '473,530p' S`;
`sed -n '678,700p' P`; `sed -n '1040,1051p' S`.

**Falsifier:** an open-question block in §4 naming this decision, or §9c marked as historical.

---

## H2 — High: four requirements stated in §4 and §6 that §7 produces nothing for and §10 does not defer

**Sites:** `S:270` (C5 content review), `S:787` + `S:826` (seeded stranger repository), `S:821-873`
(tier A / tier B), `S:805` (entry-point coverage matrix) — all against §7's deliverable list
(`S:884-964`) and §10 (`S:1052-1059`).

**What the documents claim.** §7 is *"What PR 1 produces"*, enumerated 0b, 0, 1–9, 9b, 10. §10 is
*"Out of scope, named so the gap is not read as closed."* Between them a reader is supposed to be
able to place every required artifact.

**The observation.** Four required artifacts are in neither list:

| Required at | What it requires | In §7? | Deferred by §10? |
|---|---|---|---|
| `S:270`, with `S:297-299` *"a component cannot be `SHIP` with C5 unanswered … C5 therefore grades `measured` or blocks"* | **a content review** of effort (1)'s 157 memory files | no | no |
| `S:787` *"the experiment runs against a SEEDED stranger repository with KNOWN facts"*; `S:826` *"a repository we build, with known facts"* | **the seeded repository itself** | no | no |
| `S:829` *"⛔ NEITHER REPLACES THE OTHER, AND THE ORDER MATTERS"* | **a tier-B run** against a real third-party repo | no | no (§10 defers only *"an install experiment for efforts (1) and (2)"*) |
| `S:805` | **the entry-point coverage matrix** | no | no |

Measured by position, not by reading: `grep -n -i "seed"` returns lines 787–830 **only**;
`grep -n -i "tier"` returns 821–873 **only**; `grep -n -i "coverage matrix"` returns **805 only**;
`grep -n "content review"` returns **270 only**. §7 spans 884–974. Every one of these requirements
lives entirely inside the section that *states* it and never reaches the section that *produces* it.

**Why this is the branch's signature defect and not pedantry.** The spec itself grades this shape
Blocking twice. `S:890`: *"⛔ **§6 REQUIRED a baseline and nothing produced one** — which is round
1's Blocking B3 (*"§5 requires a declared shipping set; nothing in §7 produces one"*) recurring one
round later in the same pair of sections."* Item 0b exists only because that pattern was caught.
By the spec's own standard these are instances three through six, and §7's item 4 — *"The
install-experiment record"* — is the record, i.e. the output; it does not build the seeded
repository, run tier B, or produce the matrix.

**The sharpest of the four is C5.** It is a veto criterion (`S:299`), it applies to a `data`
component by the row r3 CODEX M2 just repaired (`S:320`: *"A `data` component is graded **C1–C3 and
C5**"*), and `S:260` says it is *"NOT YET ANSWERABLE"*. So the memory corpus cannot be graded inside
PR 1, nothing in §7 makes it answerable, and §10 does not say it is deferred. §7 item 5 nonetheless
promises *"every component of all three efforts with … its verdict"*, and `S:506` says deliverable 5
*"is not done until every row has one"*. As written, deliverable 5 cannot be completed.

**What I ran:** the four greps above with line numbers; `sed -n '884,974p' S`; `sed -n '1052,1059p' S`.

**Falsifier:** a §7 item naming any of these four, or a §10 clause deferring it.

---

## H3 — High: §5 specifies seven detectors in a list that prints six and miscounts what precedes it

**Sites:** `S:602-636` (the detector list) and `S:662` (detector 6's actual definition); `P:605`.

**What the text claims.** `P:605` asserts *"⟳ **Seven** detectors — round 2 added inbound
registration, and this cell said *six* until round 3 caught it."* `S:617` opens detector 7 with
*"⛔ **All six detectors above look OUTWARD from a component**"*.

**The observation.** §5's list — *"Per component it reports:"* — is numbered **1, 2, 3, 4, 5, 7**:

```
604:1. **project-specific references** …
606:2. **cross-repo dependencies** …
607:3. **presence of a self-test and of user-facing documentation;**
608:4. ⭐ **bare-name references** …
612:5. ⭐ **prose-declared skill dependencies** …
617:7. ⭐ **inbound registration dependencies** …
```

There is no detector 6 in it. Detector 6 is defined 45 lines later, inside a *different* numbered
list (§5's behavioural rules), as that list's **item 2**: `S:662` *"2. ⭐ **Detector 6 — runtime
prerequisites (added by r2 CODEX 6)**"*. So detector 7's *"All six detectors above"* is false as
printed — **five** are above it; the sixth is below. A builder of `check-publishability.py` cannot
enumerate its subject from §5, and the approver cannot check the page's "Seven" against the spec.

`S:707` compounds it by referring to *"detectors 3, 4, 5 and 6"*, a range the list cannot resolve.

**What I ran/read:** `grep -n "^[0-9]\+[a-z]*\. " S`; `sed -n '598,620p' S`; `sed -n '660,668p' S`;
`grep -n -i "detectors" S P H`.

**Falsifier:** detector 6 appearing in §5's numbered list, or item 7 saying *"all six above"* truly.

---

## H4 — High: §7 item 8 presents D8's delivery list as what remains, and a third index defect — the one §3 itself diagnoses — is missing from it

**Sites:** `S:927-956` (§7 item 8's table) and `S:198` against `S:164-170` (§3);
`docs/portable-practices.md:13-23`.

**What the documents claim.** `S:198`: *"**What remains, and what D8 therefore delivers, is in §7
item 8** — this section does not restate it."* `S:941`: *"**What D8 actually delivers, both still
present in the index today and both measured**"*, then a two-row table — the *"roughly 3x"*
cross-set ratio and *"concentrated in one file"*.

**Both listed defects are real; I verified them.** `docs/portable-practices.md:13` still prints
*"undercounted its own subject by roughly 3x"* and `:30` still prints *"The problem is concentrated
in one file"*. The arithmetic behind calling 3x cross-set reproduces exactly (see *could not
refute*).

**The observation that refutes completeness.** The index's replacement headline carries the same
wrong-corpus defect, and §3 says so about the identical number thirteen lines earlier. `S:167-170`:

> 10,977 is the six Python files plus the four skills — a set that **adds** the two generators and
> **omits** the three shared contracts. A paragraph whose subject is *a measurement is only as good
> as its corpus* has now mis-described its own corpus twice.

`docs/portable-practices.md:13` now publishes that very set as its headline: *"The suite is ~11,000
lines ( … the Python machinery alone is **10,373 lines across six files** (`brief-compose` 1,780,
`explainer-serve` 2,907, `page_chrome` 450, `page_markup` 438, `gen-dashboard` 3,546,
`gen-goals-page` 1,252), before 604 lines of skills."* Measured: `1780+2907+450+438+3546+1252 =
10,373`, `+604 = 10,977` — and the enumeration **in the same sentence** names *"the shared delivery
contract"*, whose 346 lines that arithmetic excludes, while the 4,798 lines of the two generators it
includes appear in the enumeration only as four shell hooks. `wc -l .agents/skills/shared/*.md` →
`346 / 73 / 211 = 630`; the spec's own full-set figure is `S:186-187`'s **11,607**.

So the index's current figure is over a set that disagrees with its own adjacent enumeration — the
third one-line repair D8 should carry, diagnosed by §3, absent from the list §3 points at. The same
incompleteness that made B2 necessary, one layer in.

**What I ran:** `sed -n '1,60p' docs/portable-practices.md`; `wc -l` over the six Python files and
the three shared contracts; the sums above by hand.

**Falsifier:** a third row in §7 item 8's table, or §3 dropping *"What remains … is in §7 item 8"*.

---

## M1 — Medium: the spec states two different totals for its own subject

`S:186-187` — *"10,373 Python + 604 skills + 630 shared contracts = **11,607 lines** across the 17
components of effort (3)"* — against `S:985`, the §8 risks table: *"| ~11,000 lines is too much to
assess per line |"*. Same subject, two figures, 5.2% apart, and §3's own closing warning on the line
above (*"That is a different and larger set … the two must not be compared without saying so"*) is
what §8 then does silently. `grep -n "11,607\|~11,000" S` locates both. **Falsifier:** §8 carrying
11,607, or saying which set its figure is over.

## M2 — Medium: the all-failing inheritance row added by r3 CODEX M3 has an unreachable branch

`S:336`: *"A failure attributed elsewhere leaves it with **no measured scenario at all** — `argued`
if its importers were argued, otherwise `none`."*

Construct the population the clause names: a library whose importers **all fail**. To fail the
install experiment an entry-point must have been exercised. But `argued` is defined at `S:500` as
*"C1–C3 plus reasoning; **no experiment reached it**"*, and `S:806` says *"an unexercised
entry-point is `argued`, never `measured`"*. An importer therefore cannot be both failing and
`argued`, so the `argued` branch of this row can never be taken; every instance falls through to
`none`.

The one reading that saves it — an entry-point the experiment *cannot run* — is unclassified: this
repository's spine says *"Cannot run is a FAILURE, never a pass"* (so: in the all-failing
population), while `S:806` says unexercised entry-points are `argued`. The spec never says which.
Either way the row as written carries a dead clause, introduced by the fix for M3.
**Falsifier:** a construction in which an importer is simultaneously failing and `argued`, or a
clause saying how CANNOT RUN is classified.

## M3 — Medium: detector 7's new predicate is not mechanically decidable, so the false positive it was filed for is restated rather than closed

`S:634-636`: *"the predicate is: a component that requires a host registration in order to do
anything must declare it — and the detector decides *requires* **from how it is reached in
production**, not from whether any caller exists. A **test-only** invoker does not discharge it; a
component whose production caller is a person needs no registration and is not flagged."*

§5's opening (`S:598`) commits the scan to being a script with a `--self-test` and a mutation
manifest. Of the two qualifications, *test-only invoker* is decidable (classify the invoking file).
*"Production caller is a person"* is not: nothing in S states how a scanner recognises
`S:631`'s *"documented standalone CLI whose caller is the **user**"* — not a marker, not a docs
convention, not a manifest field. So detector 7's false-positive exemption has no observable
predicate, and r3 CODEX M4's false-positive case is answered by a sentence the scan cannot execute.
**Falsifier:** a stated mechanical signal for *"its production caller is a person"*.

## M4 — Medium: the page promises the guard checks its derived figures, and one of the two is unregistered and falsifiable with the gate green

`P:169` tells the reader: *"The spec length above carries `data-derived` and
`scripts/check-claim-propagation.py` refuses a page whose **derived figures** disagree with the
spec."* The page declares two: `P:159` `data-derived="spec-lines"` and `P:162`
`data-derived="spec-path"`. `G:227-234` registers **only** `spec-lines`.

Measured: I copied S/P/H to a temp root, replaced the `spec-path` value with
`docs/NOT/A/REAL/PATH-totally-wrong.md` **at both page sites**, and ran `audit()` → `problems: []`.
`G`'s derived loop looks up each registered key in the page's extracted map and ignores every
unregistered one, so there is no closure rule for `data-derived` and the plural in `P:169` overstates
what is enforced. **Falsifier:** registering `spec-path`, or a rule refusing an unregistered
`data-derived` key, or narrowing `P:169` to the spec length.

## M5 — Medium: three fail-open paths in the guard with no case between them

All measured by import-and-call against the real tree or a temp root:

1. **A registry entry with an empty site list is silently unchecked.** Appending
   `{"id":"ghost","token":"THIS PHRASE IS IN NO DOCUMENT ANYWHERE","sites":[]}` to `LIVE` and running
   `audit(repo_root)` → `problems: []`. `G:474-477`: `sites = []` ⇒ `absent = []` ⇒ both arms are
   `if absent and …`, so neither fires and nothing reports the entry as unauditable. The registry is
   hand-edited and removing a site is exactly how a list empties.
2. **An empty registry over an empty tree exits 0.** With `RETIRED`/`LIVE`/`DERIVED` set to `[]`,
   `audit(mkdtemp())` → `problems: []`, `notes: []` — `wanted` is empty, so `absent_paths` is empty
   and the `CannotRun` at `G:434` never fires. The success line then reads *"0 retired claim(s) … 0
   live claim(s) … 0 derived figure(s)"*. This repository has already paid for exactly this and
   written the rule down: `check-plan-file-tags.py` treats *"an empty corpus [as] **CANNOT RUN**,
   because a zero over nothing is not a finding"* (`docs/dev-process.md`). G has no such assertion.
3. **The `compute` dispatch's refusal has no case.** `G:496-497` raises `CannotRun` on an unknown
   `compute` rule; replacing it with `pass` leaves the suite **45/45 green**, so a future `DERIVED`
   entry declaring any other rule would be silently line-counted instead of refused.

**Falsifier:** a case for each — a non-empty-sites assertion, a non-empty-registry assertion, and a
`DERIVED` fixture with an unknown `compute`.

## M6 — Medium: `_html_occurrences` claims parity with the markdown path, and the two grade a table differently

`G:362-366`: *"a retirement marker ANYWHERE in a block now exempts the whole block, **exactly as
`_markdown_occurrences` has always behaved per markdown block**."*

The block *boundaries* are not comparable, and tables are where it bites. `_markdown_blocks`'
docstring states its own rule (`G:340`): *"A table is one block, **so a row inherits its header's
marker**."* `_Blocks.BLOCK` contains `table`, `tr`, `td` and `th`, so in HTML every cell is its own
block. Measured:

```python
_html_occurrences('<table><tr><th>⟳ corrected</th></tr><tr><td>a library '+tok+' x</td></tr></table>', tok)
→ (1, 0)      # asserted — the header's marker does NOT exempt the body row
_markdown_occurrences('| ⟳ corrected |\n| a library '+tok+' x |\n', tok)
→ (0, 1)      # quoted — it does
```

Both documents carry correction tables (S §3's three-stage table, S §7 item 8's; P's round-by-round
tables), so the same content expressed in the two languages is graded oppositely. The HTML
behaviour is the stricter and better one; the defect is the docstring asserting equivalence, and a
one-rule-one-place divergence between the guard's two matchers. **Falsifier:** the two matchers
returning the same pair for the table pair above, or the docstring naming the divergence.

## M7 — Medium: `handle_data` states first-wins and the code concatenates

`G:300-301`: *"key -> accumulated text … **Keyed first-wins so a later stray cannot overwrite.**"*
`G:335-336` does `setdefault(key, "")` then `+=`, which is neither first-wins nor last-wins but
concatenation. Measured:

```python
_derived_values('<strong data-derived="spec-lines">669</strong><p>x</p><strong data-derived="spec-lines">99999</strong>')
→ {'spec-lines': '66999999'}
_derived_values('<p data-derived="spec-lines">10<em data-derived="spec-lines">59</em></p>')
→ {'spec-lines': '105959'}
```

A later stray *does* change the value; it appends to it. And no case pins multi-carrier behaviour —
rewriting the body to `self.derived[key] = data.strip()` (true last-wins) leaves the suite
**45/45 green**. The failure direction is loud (a concatenated digit string will mismatch), so this
is Medium, not High; the defect is a stated property the code lacks, plus the gap that lets either
spelling pass. **Falsifier:** a case asserting the two-carrier result.

## M8 — Medium: the stated bound names one direction of incompleteness and the other is unnamed

`G:43-45`, `G:248` and the success line declare *"this registry is a floor, not a closure: a rule restated
in words no registered token matches is invisible to this guard"* — the false-negative direction.
The opposite direction is unnamed: **a registered token can be satisfied by text that is not the
rule.** `LIVE`'s `d7-licence-mit` token is the three characters `MIT`, matched as a raw substring
after `flat()`, with no word boundary — so an uppercase `COMMIT`, `SUBMIT` or `LIMIT` anywhere in
either document satisfies D7's registration vacuously; `first commit` and `harvest` are generic in
the same way.

Not live today, and I checked rather than assumed: `grep -o "[A-Za-z]\{0,8\}MIT[A-Za-z]\{0,8\}"`
over S, P and H returns **only bare `MIT`** (6, 7, 7 occurrences), and a diff-derived extraction of
H's 12,411 injected non-fragment bytes contains **no registered token, no `data-derived`, and no
MIT-containing word** — so `audited_sites`' expansion to `PAGE_HTML` is not vacuous and the derived
check is not double-counting from the chrome. But the chrome is produced by `brief-compose.py`,
outside this registry's control, and `G`'s bound does not say this direction exists.
**Falsifier:** a bound sentence naming it, or word-boundary matching for short tokens.

## M9 — Medium: a new permanent CI gate is absent from the spine that is supposed to point at every one

`G` runs as two CI steps — `.github/workflows/ci.yml:313` (`python3 scripts/check-claim-propagation.py`)
and `:316` (`--self-test`). It appears in **none** of `docs/dev-process.md`,
`docs/process-checklists.md`, `docs/review-method.md`, `docs/backlog.md`,
`docs/roadmap-to-launch.md` (`grep -n "claim-propagation"` over all five → no match), while
`docs/dev-process.md`'s *"What is mechanically enforced"* table carries 23 `scripts/check-` rows and
says of itself *"The script is the truth. These lines are pointers."*

This is also the answer to the architecture-review question — see *what this branch decided that is
not written down* below. **Falsifier:** a pointer row for it.

## L1 — Low: §4c prints before §4b

`grep -n "^## " S`: `426:## 4c`, `473:## 4b`, `532:## 4d`. In a 1,059-line document the owner has to
walk, D6 arrives before D5 even though D5's grades are what D6's harvest axis sits beside.

## L2 — Low: "three invocations" and "4 of 4" are adjacent with different denominators

`S:391-392` — *"Every one of the three invocations is CWD-relative"* — and `S:411` — *"those resolve to
nothing — measured, 4 of 4, exit 2"*. The three invocations
(`.agents/skills/shared/explainer-delivery.md:118, 141, 218` — one `brief-compose.py`, two
`explainer-serve.py`) are **two distinct filenames**, and the 4 is 2 files × 2 repositories. Both
numbers are right; neither says what it is over, in a document whose own rule is that a number in
prose must be derivable.

## L3 — Low: three near-equivalent mutants the suite does not notice

From a 31-mutation neutering sweep of `audit()`, `_Blocks`, `_html_occurrences`,
`_markdown_occurrences`, `audited_sites`, `flat` and `DERIVED` handling (26 killed, 4 crashed loudly,
and the survivors in M5/M7): removing `handle_data`'s `if not data.strip(): return`; making
`handle_startendtag` push the tag; and both `wanted |= {… DERIVED …}` lines at `G:422-423`, which are
redundant given today's registry because `SPEC`, `PAGE` and `PAGE_HTML` all enter `wanted` from
`RETIRED`/`LIVE`. Each leaves 45/45 green. The first two are behaviourally near-equivalent (I could
construct a difference only for a whitespace-only `<span class="note">` inside an asserting block);
the third matters the moment a `DERIVED` entry names a document no claim registers.

---

## Is this spec fit to be walked through with the owner as the Phase 1 human gate?

**Not yet — H1 alone disqualifies it, and it is cheap to fix.** The last substantive paragraph of
the document tells the approver that one promise-changing decision is still theirs to make and is
waiting in §4; §4 has no such question and §4b records the owner having already made it. A gate
whose closing instruction is to go and decide something already decided will either waste the
session or re-open a decision of record. H3 is the second disqualifier for a different reason: the
owner is asked to approve a scan whose detector set cannot be enumerated from the section that
specifies it, while the page tells them there are seven.

H2 is the one to fix before the walkthrough rather than during it, because it changes what PR 1 is:
as written, deliverable 5 cannot be completed (C5 is a veto, the corpus is graded against it, and
nothing produces the content review), and whether PR 1 includes a tier-B run is unanswerable from
§7 and §10. Those are scope questions the owner should be asked, not discover.

B1 does not block the walkthrough — it blocks trusting the guard's green between now and the fix.

## Is it still readable by the person who has to approve it?

Measured over 1,059 lines: **67 round-citations** on 56 lines, 20 `⟳` correction glyphs, 55 `⛔`,
55 `⚠`, 36 `⭐` — 166 lines, about one in six, open with an emphasis glyph. The corrections have not
*become* the document; the arguments are still arguments. But the document now reads in two registers
at once, and the second is addressed to reviewers rather than to the owner.

If asked what to cut, I would cut nothing load-bearing and move three things: **§9b and §9c** (the
self-review and the round-1 inventory — provenance for reviewers, not input to approval) into the
round documents, which already hold them; and the per-round attributions inside decision sections
(*"(r2 CLAUDE H5, High, INTRODUCED BY ROUND 2'S FIX)"*) into footnote form, keeping the finding and
dropping the citation from the reading line. The *attribution* is why this spec is trustworthy, so
it must not be deleted — only moved out of the sentence the owner is reading.

## What this branch decided that is not written down anywhere

**That `check-claim-propagation.py` becomes a permanent CI gate whose subject is one dated document
pair.** Its `SPEC`, `PAGE` and `PAGE_HTML` constants hard-code the three
`2026-10-15-marketplace-inventory-*` paths, and `G:430-432` states the consequence deliberately:
*"if these documents are ever renamed or archived, this gate goes red and the registry has to be
updated with them."* That is a real, defensible decision — and it is recorded only inside the file
it governs. Nothing in `docs/dev-process.md`, `docs/backlog.md` or the roadmap says this gate exists
(M9), so the person who later archives this milestone's documents will meet a red required check
with no pointer explaining it.

**And a second, smaller one:** the guard now makes the *composed* `docs/explainers/**.html` a gated
artifact that must be recomposed in the same commit as its fragment (`audited_sites`, `G:206-223`).
That is a new obligation on every page-producing skill in the repo, and
`.agents/skills/shared/explainer-delivery.md` — the contract all four route through — does not
mention it.

---

## What I checked and could not refute

- **B1's re-measurement.** Reproduced independently, from inside each clone:
  `omc` at `679b418f32409e6d0edecf5038fd2de460cfce04`, `openai-codex` at
  `807e03ac9d5aa23bc395fdec8c3767500a86b3cf`; `python3 scripts/brief-compose.py --help` and
  `python3 scripts/explainer-serve.py --help` in each, exit codes read **without a pipe** —
  `2, 2, 2, 2`, each with `can't open file '<cwd>/scripts/<name>.py': [Errno 2] No such file or
  directory`. `find` over both repos for either filename returns **nothing**, so the *"a collision
  needs the FILE name"* reasoning holds. The surviving *"the mechanism is unchanged"* claim is
  supported by the error text itself, which names the path resolved under the caller's directory.
  The correction reached S §6, S §4's harvest entry, and both page copies; `grep -i "silent"` finds
  the old outcome only inside the quoted retired sentence. **Falsifier:** a non-2 exit, a file of
  either name in either repo, or a site still asserting the silent run.
- **B2's replacement defects and their arithmetic.** Both are present in
  `docs/portable-practices.md` today (`:13`, `:30`). The three-stage table reproduces exactly, by
  `git show <commit>:<path> | wc -l` over the same nine files at each commit — **3,599** at
  `cacbac17`, **3,737** at `100cf498`, **6,525** at HEAD; `6525/3599 = 1.8130`,
  `6525/3737 = 1.7461`, `138/3737 = 3.69%`, `10,977/3,599 = 3.0500`. So *"1.81x"* and *"cross-set"*
  are both right, and the generators the cross-set figure adds are `3,546 + 1,252 = 4,798` lines,
  none of them among the nine. **Falsifier:** different same-set totals, or the nine files' own
  ratio reaching 3x. (H4 is about what the list *omits*, not about this arithmetic.)
- **The guard's declared count and its mutation ratchet.** `--self-test` → **45/45**; a live run
  over the real tree → **rc=0** with 4 allowed quotations. `scripts/check-selftest-counts.py`
  → rc=0, *"54 script(s) declare a count, every one verified by running it"*. The scoped sweep,
  built per the recipe — `rsync -aL` of the seven `HARNESS_TREE` paths read out of
  `scripts/check-plan-code.py:199-226`, every other `scripts/mutations/*.json` deleted,
  `EXPECTED_MUTATIONS` reduced to the one key — gives **control green, then 14 mutations, 14 killed,
  14 attributed to the case each names, 0 survivors**. `check-plan-code.py --self-test` → 178/178.
  **Falsifier:** a surviving mutation, an unattributed kill, or a red control.
- **r3 CODEX H2's central arm is genuinely pinned now.** Replacing
  `if absent and len(absent) < len(auditable):` with `if False:` fails **4 cases**, led by *"audit: a
  LIVE claim at the spec and NOT the page is a problem"*. Weakening the comparison to `<=` fails
  *"absent from all its sites"*. Disabling `audited_sites`' expansion fails 3, including *"a token in
  the fragment and NOT the served page"*. The fixture derives its subject from `LIVE`, so a registry
  edit cannot leave it testing nothing. **Falsifier:** any of those three edits leaving 45/45 green.
- **r3 CODEX M5's unguarded retired claim is closed, and the entry bites.** Appending *"The missing
  licence blocks this milestone."* to a copy of the real P and H produces a
  `RETIRED claim re-asserted: licence-blocks-the-milestone` problem at both; appending it to the real
  S produces one there. **Falsifier:** any of the three staying silent.
- **H's injected chrome cannot satisfy a registration.** A `SequenceMatcher` diff of fragment against
  composed page isolates **12,411 bytes** of injected content; no registered `LIVE` or `RETIRED`
  token appears in it, it declares no `data-derived`, and it contains no MIT-substring word. So
  `PAGE_HTML` auditing is real coverage rather than a tautology, today. **Falsifier:** any token
  present in that extraction. (The forward risk is M8.)
- **D9 at every site.** §4d (`S:532-595`), the C4 row (`S:259`, *"It is **NOT** graded against D9"*),
  §9's falsifier bullet (`S:999-1003`, carrying all three observations **and** *"PR 1 produces
  none … cannot fire inside this milestone"*), §10 (`S:1058`) and both page copies (`P:1006-1027`)
  agree: three failing observations, D9 is not C4's predicate, and D9 is a deferred publication
  requirement rather than a milestone gate. I could not find a sixth site or a disagreement.
  **Falsifier:** any site carrying two of the three promises, or calling D9 a gate.
- **The criteria count and the detector count on the page.** *"four criteria"* appears nowhere;
  `S:985` and `P:476`/`H:553` all say five. `P:605` says *"Seven"* detectors. (H3 is the spec-side
  enumeration, not these.) **Falsifier:** a surviving "four".
- **D8's placement rule survives its subject's replacement.** `S:931-940` states D8 as a rule about
  placement with the owner's words quoted, records that the three claims it was decided about were
  already fixed in `b200f2cf`, and keeps the bound and its falsifier (*"PR 1 open with either
  correction not yet committed"*). I could not construct a case where the rule depends on which
  corrections are outstanding. **Falsifier:** a D8 clause naming a specific correction.
- **§7 item 4 against §6's bounded capture.** `S:913-918` now asks for *"the resource record the
  capture mechanism of §6 can actually produce, together with what that mechanism cannot see"*,
  which is satisfiable by `S:771-775`'s permitted mechanism; the exhaustive *"every resource"*
  wording is gone and marked retired. r3 CODEX M6 is closed. **Falsifier:** either clause demanding
  an observation the other forbids.
- **The `data` role composing with C5 and D5.** A `data` component graded C1–C3 and C5 (`S:320`)
  with C5 unanswered yields `NEEDS-WORK` + a named defect under `S:510`, and `argued` under §6's
  bound — one grade, no contradiction. r3 CODEX M2 is closed as a *rule*. (H2 is that nothing
  produces the evidence, which is a different defect.) **Falsifier:** two rules assigning it
  different grades.
- **The repo's own guards over this tree.** `check-docs`, `check-anchors`,
  `check-vocabulary-collisions`, `check-ratchet-contract`, `check-main-drivable`,
  `check-fixture-variation`, `check-selftest-counts`, `check-dashboard-entry` all **rc=0**.
  `check-review-rounds` → **rc=1**, for exactly the stated reason: *"marketplace-inventory round 3:
  only codex — claude neither ran nor recorded a `REVIEW GAP:` line"* — which this document resolves.
  G has a caller (`ci.yml:313`, `:316`), so its ratchet contract is satisfied.
- **The `⟳`-only marker result.** Confirmed Codex's measurement independently (10 of 11 removals
  green). I am **not** re-filing it as a coverage limit; B1 is the part of it that is a live defect.

### UNVERIFIED, and why

- **`check-publishability.py`'s actual behaviour**, and detectors 1–6 in operation: nothing is built.
  Everything above about them is a reading of a written contract.
- **The install experiment, tier A or tier B**, the packaging spike, and `${CLAUDE_PLUGIN_ROOT}`
  substitution inside a real installed package: no isolated package exists on this machine. I
  verified only that our suite references that variable **nowhere** (`grep -rn` over
  `.agents/skills/`, `brief-compose.py`, `explainer-serve.py` → no match) and that both third-party
  plugins use it.
- **The full `--mutate .` ratchet.** Deliberately not run — the scoped result establishes this
  manifest's 14 entries over a green control, not the whole-repo ratchet, the declared sum, or any
  unrelated control.
- **`docs/portable-practices.md`'s remaining content beyond lines 1–60**, and whether defects other
  than the three in H4's orbit are present in it.
