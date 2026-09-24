# Claude adversarial review — velocity-177 r1

Subject: `git diff origin/master...HEAD` on `velocity-177` (PR #345), 2 commits, 5 files,
+271/−24. Docs-only. Everything below was established by reading the file or running the command
quoted; nothing rests on recall.

⚠ **Independence caveat, stated rather than hidden.** While sibling-searching for stale
`development-velocity` references I ran a repo-wide `grep`, and its output included the truncated
first line of the concurrently-running Codex half's file
(`docs/reviews/codex/velocity-177-r1-codex.md`), which named `roadmap-to-launch.md:2064`. I did not
open that file, and I verified M2 below by reading `docs/roadmap-to-launch.md:2059-2090` myself —
but the pointer was not independent, and the coordinator should discount M2's independence
accordingly. No other finding here was touched by that leak.

## Verdict

**NOT CONVERGED — 2 High · 6 Medium · 5 Low.**

The two Highs are both instances of the defect class this PR exists to stop: an author-side claim
that its own cited source contradicts (H1), and a newly *governing* rule that re-adopts a scope the
repo already measured, fixed and documented as wrong (H2).

---

## Findings

### 🔴 H1 — The only evidence offered for adopting the draft-PR practice is contradicted by the review document it cites

**`docs/development-velocity.md:232-233`** (§9 Q3, added by this PR):

> **3 · Should the draft PR be automatic? → NO. Adopt the practice, do not build the hook.** It is
> already carrying its weight by hand: **it caught backlog #176 r2's Blocking on its first use.**

**`docs/roadmap-to-launch.md:2077-2079`** (added by this PR), same claim, and it is what ticks the
checkbox:

> - [x] **The draft-PR pattern — adopted as PRACTICE, deliberately not automated.** **It caught
>   #176 r2's Blocking on its first use.**

**The cited Blocking's own document says the opposite**, in a paragraph written specifically to
pre-empt this attribution — `docs/reviews/claude/review-identity-176-r2-claude.md:154-159`:

> **Status of the CI evidence.** Draft PR #343 is on exactly `d02ab66b` […] and `gh pr checks 343`
> showed `verify  pending` when I looked; `schema-gates` had already passed. So the sweep result is
> **not yet observed** — my Blocking rests on the anchor measurement above, **not on a CI verdict**,
> and I did not run `--mutate .` locally per the brief.

The r2 Blocking (`:121`, B1 — orphaned mutation anchors) was found by a *reviewer* doing a hand
anchor measurement. The draft PR's `verify` job had not reported. So the draft-PR practice did not
catch it, and the reviewer said so in advance.

**Why High rather than Medium.** Q3's decision (*adopt the practice, do not build the hook*) rests
on exactly one piece of evidence, and the evidence is not what the source says. Remove it and Q3
has an argument against the hook but nothing at all for the practice. The roadmap then carries a
`[x]` whose stated justification is false. This is category 1 of the PR's own table — *the author's
own unverified claim* — written into the commit that adopts the rule against it.

**What I ran.**
```
grep -n "Blocking" docs/reviews/*/review-identity-176-r2-*.md
sed -n '150,165p' docs/reviews/claude/review-identity-176-r2-claude.md
```

**Sibling search — DONE.** `grep -n "draft PR\|Draft PR\|draft-PR"` over
`development-velocity.md roadmap-to-launch.md process-checklists.md dashboard-entries.md`. Two
sites carry the credit claim (`development-velocity.md:233`, `roadmap-to-launch.md:2078`); both are
added by this PR. `dashboard-entries.md:12169` mentions the draft PR but only about CI minutes and
makes no catch claim. `process-checklists.md` does not mention it. I also searched
`review-identity-176-r3-claude.md` and the last 8 master commit bodies for a later CI confirmation
that would rescue the claim (`grep -rn "d02ab66b"`, `git log --grep='survivor'`) and found none —
if one exists it is not in the tree.

---

### 🔴 H2 — Rule 4 adopts `ci.yml`-alone as the gate-list scope; `check-merge-ready.py` records that exact scope as an already-fixed review finding, and cites it as its own precedent

**`docs/process-checklists.md:489-494`**, newly governing:

> ### 4 · Derive gate lists from `ci.yml`, never from memory
>
> Before claiming the gates pass, read `.github/workflows/ci.yml` and run what it names. […]
> `scripts/check-merge-ready.py` already derives its own list this way — prefer running it over
> assembling one.

**`scripts/check-merge-ready.py:52-56`:**

> ```
> # ⛔ EVERY WORKFLOW, NOT `ci.yml` ALONE — Claude r1, Medium. The first version parsed one file and
> # claimed the pull-request-only list was "derived, never hand-written"; the FILE SCOPE was the
> # hand-written part. `schema-gates` is the other required context on every PR, so a gate added
> # there was invisible to a derivation that congratulated itself on being immune to exactly that.
> WORKFLOW = WORKFLOW_DIR / "ci.yml"   # kept: the steps this script can actually invoke live here
> ```

Two separate defects:

**(a) The scope is the one already measured wrong.** `schema-gates` is a *required* context on
every PR (`docs/dev-process.md`, backlog #137) and `ci.yml` invokes none of its gates. Measured:

```
$ grep -oE '(python3|bash) scripts/[A-Za-z0-9_./-]+\.(py|sh)' .github/workflows/ci.yml \
    | awk '{print $2}' | sort -u | wc -l
33                       # scripts/check-schema-gates.sh is NOT among them
$ grep -nE 'run: .*(python3|bash|scripts/)' .github/workflows/schema-gates.yml
224:        run: scripts/ci/start-schema-db.sh m4_schema_gates
233:        run: scripts/check-schema-gates.sh          # the fifteen schema gates
303:        run: python3 scripts/check-live-schema.py --prod --expect-present
```
`scripts/check-schema-gates.sh` appears in `ci.yml` only inside a comment at `:267`, which itself
records that the script being "referenced zero times here" was architecture review #7's finding 4.
An author following Rule 4 literally derives a list that omits all fifteen schema gates and
`check-live-schema.py`.

**(b) The cited precedent is the defect, not the fix.** The rule says `check-merge-ready.py`
"already derives its own list this way." Its comment says the version that did exactly that was a
Claude r1 Medium, and that the residual `ci.yml` pin survives for a *narrower* purpose — "the steps
this script can actually invoke live here" — not as an endorsement of single-file derivation.

**Why High.** This is a rule that now governs, written to prevent a CI round-trip, whose stated
scope would cause the class of miss the repo already paid a review round to close. Per this repo's
own standard, a rule that cannot be followed correctly is a failure, not a pass.

**Sibling search — DONE.** `grep -rn "development-velocity"` plus targeted greps for the phrase.
Three further sites carry the `ci.yml`-only framing, all **pre-existing on master**, so this PR did
not introduce them but did promote one into a governing document:
`docs/development-velocity.md:184-185` (§6 "Proposed rules"), `docs/backlog.md:205` (row #177
strand ⑶). `docs/dashboard-entries.md:12130-12131` states it as "read the file that lists them" —
singular, same defect, vaguer. The PR body's own CHECK table partially escapes it by routing
"Heavy gates (`--mutate .`, Postgres)" to CI, but it never names `schema-gates`.

---

### 🟡 M1 — Rule 3's worked example states a survivor count its cited measurement does not support

**`docs/process-checklists.md:481-483`**, newly governing:

> **Worked example from the source session:** perturbing every module-level constant in both touched
> files — **1 survivor found, then 0.** That is an enumeration.

The source measurement is `docs/reviews/claude/observer-log-owner-r5-claude.md:259-266`, a table of
every module-level constant in `scripts/codex-review.py` over a green 119/119 control. It records
**two** survivors — `VERDICT_DIR` (119/119 passed, rc=0) and `MIN_REVIEW_CHARS` (119/119 passed,
rc=0). The same document's summary at `:548-551` widens it to both touched files and records
**three**: "finds three more survivors over green controls: `VERDICT_DIR` […] `MIN_REVIEW_CHARS`
[…] `SUITE_TIMEOUT`."

I could not find any record of a `1 → 0` sequence. Searched:
```
grep -rn "survivor" docs/reviews/claude/review-identity-176-r*.md docs/reviews/codex/review-identity-176-r*.md
grep -rn "module-level constant" docs/reviews/ docs/backlog.md
git log origin/master --grep='survivor' -i ; git log origin/master -8 --format='%h%n%b' | grep -n survivor
```
**Treat "1 survivor found, then 0" as NOT VERIFIED.** It is the worked example of the rule *"a class
claim requires a class sweep"*, inside the section whose Rule 1 is *no number unless measured in
this session*.

**Sibling search — DONE.** `grep -n "1 survivor found"` across `docs/`: two sites, this one and
`docs/development-velocity.md:184-185` (pre-existing on master, unchanged by the diff). The PR
copied the unverified figure from the rationale doc into the governing doc without re-deriving it.

---

### 🟡 M2 — `roadmap-to-launch.md:2063-2064` still says nothing in the velocity doc governs, and that its first line says so; both halves are now false

**`docs/roadmap-to-launch.md:2063-2064`** (context, not touched by the diff):

> ⛔ **Nothing in it governs until it lands in a process doc or a script** — the document says so in
> its own first line.

After this PR: (a) §6 and §7 *do* govern, from `docs/process-checklists.md:428` and `:644`; (b) the
document's first line no longer says so — the banner was replaced at
`docs/development-velocity.md:3-12` by this very commit, and now reads "⟳ **2026-09-24 — PARTLY
ADOPTED.**"

The heading **four lines above it** was updated (`:2059`, "🟠 §6+§7 ADOPTED 2026-09-24"), so the
section contradicts itself within five lines. This is the exact hazard the PR's own "Also in here"
paragraph gives as its reason for editing the banner — *"a reader who believed it would have cited
rules from their own rationale"* — left standing in a file the PR edits.

**Sibling search — DONE, and this is the only survivor.**
```
grep -rn "NOTHING ADOPTED\|nothing adopted\|Nothing in it governs\|nothing here governs\|NOT ADOPTED PROCESS" docs/*.md .claude/
→ docs/roadmap-to-launch.md:2064   (single hit)
grep -rn "development-velocity" --include=*.md --include=*.py --include=*.yml --include=*.sh .
→ 9 non-self sites; the other 8 are consistent with partial adoption.
```
⚠ See the independence caveat at the top: a grep incidentally surfaced the Codex half's pointer to
this line before I read it.

---

### 🟡 M3 — §6 and §7 still present the adopted rules in full, labelled "Proposed", under ✅ ADOPTED headings

`docs/development-velocity.md:161` reads `## 6. … — ✅ ADOPTED 2026-09-24`, and its new note says
"What follows is the measurement that justified them." What actually follows is the measurement
**and a second full copy of all four rules**, at `:179-185`:

> **Proposed rules, all free:**
> - **No number in a commit message, comment or doc unless it was measured in this session.**
> - **Fix the sentence IN PLACE.** …
> - **A class claim requires a class sweep.** …
> - **Derive gate lists from `ci.yml`, never from memory.** …

Same in §7 (`:191` heading ✅ ADOPTED) at `:201`:

> **Proposed addition:** naming a side job also **re-asks Q0**.

That is the *exact wording the PR says it deliberately did not adopt* — still on the page,
unstruck, labelled "Proposed addition", 10 lines below a note saying it was not adopted. A reader
landing on §7's body reads it as live.

The new banner at `docs/development-velocity.md:106-108` states the rule this violates:

> ⛔ **An adopted rule is not cited from here.** … Citing a rule from its rationale is how two
> copies start.

The PR chose to keep the *evidence* in place (defensible — "a rule without its evidence gets argued
away") but kept the *rules* too, so the second copy the banner warns about now exists, and it
disagrees with the first about whether it is a proposal.

**Sibling search — DONE.** `grep -n "Proposed"` across `docs/development-velocity.md`: three hits —
`:143` (§5), `:179` (§6), `:201` (§7). §5 is finding L2 below; §6 and §7 are this finding. No other
touched file carries a "Proposed" label over adopted content.

---

### 🟡 M4 — PR body says `ci.yml` names 28 gates; the rule this PR ships says thirty-three. Neither states a denominator

PR #345 body, *Checks*: "Gate list derived from `.github/workflows/ci.yml` (**28 gates named**),
per rule 4."

`docs/process-checklists.md:491-493`, the rule being applied, three paragraphs of the same PR away:
"the file named **thirty-three**."

Measured this session:

| Population | Count |
|---|---|
| unique scripts *invoked* by `ci.yml` (`run:` lines) | **33** ✅ matches the shipped rule |
| of those, `check-*` only | **28** ✅ matches the PR body |
| unique scripts *mentioned* anywhere in `ci.yml` incl. comments | 34 |
| `run:` steps invoking a script | 47 |

```
$ grep -oE 'run: (python3|bash) scripts/[A-Za-z0-9_./-]+' .github/workflows/ci.yml | awk '{print $3}' | sort -u | wc -l
33
$ grep -oE 'scripts/check-[A-Za-z0-9_-]+\.(py|sh)' .github/workflows/ci.yml | sort -u | wc -l
29      # 29 mentioned, 28 invoked
```

Both numbers are derivable, which is the problem: two different populations, same sentence subject
("gates named in `ci.yml`"), neither naming its denominator, in the PR that adopts *"no number
unless measured in THIS session"* and whose neighbouring section is about number resolvability. A
reader cannot tell whether 28 and 33 disagree or count different things.

**Severity Medium, not Low**, because the PR body is where the author reports having *applied* rule
4, and applying it produced a number that contradicts the rule's own worked figure.

**Sibling search — DONE.** `grep -rn "33\b.*gates\|gates named\|names 33"` over the touched docs:
`docs/development-velocity.md:185` and `docs/backlog.md:205` both say 33 (pre-existing, correct).
The 28 appears only in the PR body. No other count of this population found.

---

### 🟡 M5 — The "wrong in both directions" claim about `check-backlog-closure.py` names the wrong PR, and the inverse instance is not observable

PR #345 body:

> ⚠ Note also the inverse, recorded on **PR #344**: it was **silent** about #176 because **that
> squash subject** wrote the token unparenthesised. It is wrong in both directions, which is the
> shape that usually means the key is wrong rather than the threshold.

**(a) Wrong PR.** PR #344's squash subject is *"The page that says what needs you had stopped
reading nine days of its own store (#344)"* (`15a133fe`) — it mentions no backlog id at all. The
subject that closes #176 belongs to **PR #343**, `45b65cb7`: *"The review testimony names itself —
backlog #176 (#343)"*. "That squash subject" has no correct antecedent.

**(b) The inverse instance is unobservable, so it cannot support the claim.** Driven through the
shipped guard:

```python
>>> closing_ids(["The review testimony names itself — backlog #176 (#343)",
...              "The page that says what needs you had stopped reading nine days of its own store (#344)"])
{}                                   # neither parses — (a) confirmed
>>> row_markers(open("docs/backlog.md").read())["176"]
'✅'
>>> findings({"176": "s"}, row_markers(...))
([], [])                             # silent EVEN IF the token had parsed
```

`scripts/check-backlog-closure.py:117` sets `CLOSED_MARKER = "✅"` and its own self-test case at
`:279` is named *"closed row is quiet"*. Row #176 carries ✅. So the guard is silent about #176 for
a reason that has nothing to do with the token grammar, and would be silent either way. The
"inverse direction" has a demonstrated *mechanism* but **zero demonstrated effect**, and the PR
presents it as a measured instance supporting *"the key is wrong rather than the threshold."*

**(c) What I confirm.** The two *forward* false positives are correct as stated, verified by
`git show`:
- `939c97b4` — `git show 939c97b4 -- docs/backlog.md` shows a single `+| 117 |` line and no `-`: it
  **added** row #117. ✅
- `b184bbbc` — same shape for `+| 159 |`: it **added** row #159. ✅

**(d) The third instance is arguably the author's, not the guard's.** The #177 warning is raised by
this branch's own commit `c8364e6f`, whose subject ends `(backlog #177)` — the tail position
`docs/dev-process.md` documents as meaning *closes*. The guard is behaving exactly as specified; a
commit that does not close a row put the closing token at the tail. Framing all three as guard
defects understates the share that is convention drift. Not filed — the PR correctly says filing is
the owner's step — but the diagnosis should say which of the three is which.

**Sibling search — DONE.** Ran the guard live: `python3 scripts/check-backlog-closure.py` → rc=0,
`1565 subject(s) scanned, 13 closing token(s), 178 row(s) read`, exactly 3 WARNs (#117, #159, #177),
0 orphans. No fourth instance exists in the current corpus. I did not replay the guard over history
to look for silent false negatives — **not searched**, and a silent-direction sweep is the
measurement the PR's "wrong in both directions" claim would actually need.

---

### 🟡 M6 — Backlog row #177's Work list and `files` column still plan three things this same commit decided against

`docs/backlog.md:205` — the status cell was rewritten, the body was not. It still reads:

- strand ⑴: "Q0 into `review-method.md` §0 (⚠ `dev-process.md` is at 214/220 lines and **can hold
  only a pointer row**)" — but `development-velocity.md:223-224` (§9 Q1, added here) decides
  "`dev-process.md` (214/220) **gets nothing**; […] a pointer row would be a second pointer."
- strand ⑵: "draft-PR pattern" as work to do — decided NO at §9 Q3 (practice, not built).
- strand ⑷: "**side job re-asks Q0**" — the wording the PR says at three sites was deliberately not
  adopted.
- `files` column, unchanged: `docs/dev-process.md` **(pointer row only)**, `.github/workflows/ci.yml`
  **(draft-PR trigger)` — both now decided against.

A reader sizing the remaining work from the `files` column will scope two files that will not be
touched. The repo's own rule — *fix the sentence IN PLACE*, adopted at `process-checklists.md:464`
in this commit — is what this row needs.

**What I ran.** `awk -F'|' '/^\| 177 \|/{print $3}' docs/backlog.md`, and read the added status
cell from `git diff origin/master...HEAD -- docs/backlog.md`.

**Sibling search — DONE.** Checked the other row this PR could have staled, `docs/backlog.md:206`
(row #178) — its reference to `development-velocity.md` (#177) is about the un-adopted §4 thrashing
measurement and remains true. `check-roadmap-consistency.py` → rc=0, "2 tracked item(s) still open:
A6, Q0", consistent with the two unticked boxes I can see at `roadmap-to-launch.md:2082` and
`:2087`.

---

### 🔵 L1 — Rule 3 states the rule in full and then says not to restate it

`docs/process-checklists.md:475-487`. Two paragraphs state the rule:

> *"The class is closed"* means every member was **enumerated and tested**. It does not mean the
> named instance was fixed and the others look fine. If you cannot state how the members were
> enumerated, you do not have a class claim — you have an instance fix…

then `:485-487`:

> ⟳ **This is the AUTHOR-side twin of `review-method.md` §0 Q2 step 5** […] **Do not restate the
> reviewer rule here — read it there.**

**Attack 2's answer, in two parts.**

*The cross-reference resolves correctly.* `docs/review-method.md:59-64` is Q2 step 5 and it does say
"⛔ **EVERY FINDING NAMES A SAMPLE, NOT A SCOPE**", and it does bind the reviewer ("A finding's
boundary is the evidence the *reviewer* happened to have"; "Each finding must state whether siblings
were searched for"). ✅ The quote is accurate and the author/reviewer asymmetry is real as a matter
of *obligation*.

*But the "not a restatement" claim is false as written.* The rule is fully stated before the
pointer arrives. The PR body, `roadmap-to-launch.md:2073`, `dashboard-entries.md:12146` and
`development-velocity.md:165-167` all assert "Rule 3 landed as a CROSS-REFERENCE, **not** a
restatement". It landed as a restatement with a cross-reference attached. That is a defensible
design — an author needs the rule at hand — but it is not what four documents say it is, and the
sentence at `:487` instructs a future editor not to do the thing the two paragraphs above it
already did.

*Second-order.* §0 Q2 step 5 partly reaches the author's moment already: `review-method.md:68-71`
records that all six replayed misses "were eventually caught **by a reviewer, never by the
author**", that three had a query that "would have named the sibling **at the moment of the fix**",
and `scripts/peer-sites.py --diff <ref>` exists for exactly that moment. So "nothing bound the
author" is true of obligation and overstated as to tooling.

**Sibling search — DONE.** `grep -rn "cross-reference\|CROSS-REFERENCE"` over the four touched
docs: 4 assertion sites, listed above, all added by this PR, all carrying the same overstatement.

---

### 🔵 L2 — The new status banner mislabels §5, §9 and §10

`docs/development-velocity.md:3-12`. The banner instructs "Read this line before citing anything
below", so its rows are load-bearing.

- Row `:9` — "**§5 sweep policy** | ✅ draft-PR-at-slice-start adopted as practice". §5's body at
  `:143-144` still reads "**Proposed:** 1. **Open the PR as a DRAFT at the start of a slice.**"
  Unchanged by this PR.
- Row `:10` — "everything else | proposal". That bucket contains §9 (`:218`, "The five open
  questions — **ANSWERED** 2026-09-24") and §10 (`:254`, "the design session's brief"), both added
  by this PR as settled records. `roadmap-to-launch.md:2080-2081` ticks "**All five §9 questions
  ANSWERED** […] so none is re-opened from scratch" — so the roadmap treats as settled what the
  banner labels a proposal.

Low because a reader who follows the pointer finds the right answer; it is the index that is stale.

**Sibling search — not applicable** (single banner). I did check that the roadmap and backlog status
cells agree with §6/§7/§2 — they do.

---

### 🔵 L3 — §9 Q3's settling argument is in tension with the practice's own value proposition

`docs/development-velocity.md:235-237` (added):

> ⚠ The CI-minutes question that framed this turned out not to bind: `concurrency:
> cancel-in-progress` means repeated pushes cost **one** run…

`cancel-in-progress: true` is verified configured at `.github/workflows/ci.yml:21-23` (and
`schema-gates.yml:171-173`), so the *cost* claim is correct. But §5's stated reason for the practice
is `:144`: "**Every push then sweeps on GitHub.**" With `cancel-in-progress: true` they do not —
each push cancels its predecessor's sweep. The repo has already written down why that matters, at
`.github/workflows/schema-gates.yml:91-94`:

> A cancelled run reports nothing, which this repo treats as worse than a failure.

So the mechanism cited to make the practice cheap is the mechanism that prevents intermediate
commits from being swept. The decision (adopt the practice) is probably still right — what is
wrong is that the record now contains both claims and reconciles neither.

**Sibling search — DONE.** `grep -rn "cancel-in-progress"` across the repo: `ci.yml:23`,
`schema-gates.yml:92,173`, `development-velocity.md:150,236`, `roadmap-to-launch.md:2079`,
`dashboard-entries.md:12168`. Four prose sites, all making the cost claim; none reconciles it with
`:144`.

---

### 🔵 L4 — Rule 1's adopted scope silently drops code comments

Proposal, `docs/development-velocity.md:180`: "No number in a commit message, **comment** or doc
unless it was measured in this session."

Adopted, `docs/process-checklists.md:430-432`: "**Read when:** writing a commit message, a review
document, a PR body, or a claim about what a change does. **Not when reviewing** — this is about
what the AUTHOR puts on the page for a reviewer to find."

Code comments are not in the adopted scope. That matters because **backlog #175** — open, filed
2026-09-23 — is specifically about numeric claims inside `scripts/*.py` comments ("12 of the 95 …
are already broken"), and `docs/backlog.md:208` records four such citations added by one branch all
resolving wrong. The narrowing is not flagged anywhere in the diff, so it reads as an oversight
rather than a decision.

**Sibling search — DONE.** Compared each of the four proposal bullets (`development-velocity.md:
180-185`) against its adopted form (`process-checklists.md:450`, `:464`, `:475`, `:489`). Rule 1 is
the only one whose scope changed.

---

### 🔵 L5 — An adopted rule's operative criterion lives in a section the same PR labels un-adopted

`docs/process-checklists.md:666-668`, in the newly governing side-job subsection:

> Until then the question above is asked by hand, and **the four signals that say *seam* are in
> `development-velocity.md` §3**.

§3 is classified at `development-velocity.md:8` as "🟠 **DECIDED IN FORM, NOT BUILT**", in a banner
whose next line says "⛔ **An adopted rule is not cited from here.**" Letter-wise this is legal —
§3's signals are not an adopted rule — but an author applying the governing side-job rule is sent to
non-governing prose for the criterion that decides the answer.

**Attack 3's answer, for the record: the side-job rule IS usable today without Q0.**
`process-checklists.md:662-664` asks the question inline and defines the term inline — *"does this
move a seam — a new module, a change to who owns what, a new protocol or vocabulary — or is it logic
inside an existing one?"* — and `:666` names the by-hand fallback explicitly. It does not depend on
Q0 existing. The one soft spot: it prescribes an *outcome* ("Seam work wants its design settled
before it is built, on a branch of its own") without naming an artefact, where the parent rule at
`:638-642` names three concrete ones (plan slug, branch, backlog row). An author can follow it, but
two authors may produce different evidence of having done so.

---

## What I checked and found clean

Stated so the reader can tell coverage from silence.

**Attack 1 — is Rule 1 the rule it sits beside?** ✅ **They are genuinely two rules, and the
`check-vocabulary-collisions.py` framing in the brief does not apply.**
- `process-checklists.md:376-392` (*Qualify every number in prose*) is entirely about namespace
  resolvability: a table of `backlog #39` vs `#39`, `PR #155` vs `#155`. No sentence in it concerns
  whether a number is true.
- `process-checklists.md:450-462` (Rule 1) is entirely about provenance, and `:456-458` states the
  distinction explicitly. The counter-example it gives is real: `backlog #176 r1 M3` was a perfectly
  qualified and factually wrong number (`review-identity-176-r1-claude.md:369,378`).
- *What a merge would lose:* the provenance half. §0 of the older section argues the rule cannot be
  a ratchet because the property is semantic; a merged section would inherit that argument and the
  reader would conclude the *resolvability* check is the whole of it.
- *The vocabulary-collision shape does not arise.* `scripts/check-vocabulary-collisions.py:49,99-110`
  reads the **Postgres catalog** via `read_catalog` — its subject is table columns. It cannot see a
  Markdown file, so no adjacency of two doc sections can create a shape it catches. The velocity doc
  already states this bound correctly at `:96` ("invisible to `check-vocabulary-collisions`, whose
  subject is the database schema") — while `:250` (§9 Q5, added here) invokes the guard's name for a
  hook-vs-hook duplication as pure analogy. Borrowed authority, but the doc itself supplies the
  bound 150 lines earlier, so I am not filing it.

**Attack 4 — numbers, each one re-derived this session.**

| Claim | Site | Verified |
|---|---|---|
| `LINE_BUDGETS` covers exactly two files | `development-velocity.md:222-224` | ✅ `scripts/check-docs.py:191-194` — exactly 2 keys |
| `dev-process.md` at 220, `plugins.md` at 260 | same | ✅ same lines |
| `dev-process.md` is 214/220 | same | ✅ `wc -l docs/dev-process.md` → 214 |
| `review-method.md` is not budgeted | same | ✅ absent from `LINE_BUDGETS`; 721 lines |
| `dev-process.md` already points at `review-method.md` | same | ✅ its file table, row "review round is starting" |
| `cancel-in-progress` configured | `:236` | ✅ `ci.yml:21-23`, `schema-gates.yml:171-173` |
| `ci.yml` names thirty-three | `process-checklists.md:492-493` | ✅ 33 unique invoked scripts (command above) |
| `939c97b4` added row #117 | PR body | ✅ `git show` — one `+` line, no `-` |
| `b184bbbc` added row #159 | PR body | ✅ same |
| `1858 → 1755` claimed, `1858 → 1869` actual | `process-checklists.md:442` | ✅ `review-identity-176-r1-claude.md:481-485` |
| `183 verdicts` wrong (184), copied 3× | `:444` | ✅ `review-identity-176-r1-claude.md:369,378` |
| r5 H1 = correction appended below a false paragraph | `:441` | ✅ `observer-log-owner-r5-claude.md:169,183-186` — 25 lines above |
| r5 M1 + r5 Codex Medium = class asserted, instance fixed | `:443` | ✅ `observer-log-owner-r5-claude.md:242`, `:548` |
| `check-anchors` 13 registered | PR body | ✅ rc=0, "13 registered, all claimed" |
| `check-selftest-counts` 46 scripts | PR body | ✅ rc=0, "46 script(s) declare a count" |
| `check-plan-file-tags` 0 across 1,451 | PR body | ✅ rc=0, "0 across 1451 documents" |
| `check-banner-armed --self-test` 160/160 | PR body | ✅ rc=0 |
| `gen-dashboard.py` 253 entries | PR body | ✅ "wrote … (253 entries, window 14)" |
| `check-roadmap-consistency` 2 open (A6, Q0) | PR body | ✅ rc=0, same wording |
| **`1 survivor found, then 0`** | `:482` | ❌ **M1 — contradicted by source** |
| **draft PR caught #176 r2's Blocking** | `:233`, roadmap `:2078` | ❌ **H1 — contradicted by source** |
| **28 gates named** | PR body | ⚠ **M4 — derivable but a different population from the shipped 33** |
| **"three scopes"** | `:242` | ⚠ **L-grade, see below** |

⚠ **One more unverified number, filed here rather than as a finding because it is not this PR's
regression.** `development-velocity.md:241-242` (§9 Q4, added) says the older section "records the
identical question being tried **at three scopes** and rejected". `process-checklists.md:394` does
head itself "MEASURED 2026-08-27, three scopes" — but the table beneath it (`:398-401`) has exactly
**two** rows (all of `docs/`, added lines on one branch). `git show c517faa0:docs/process-checklists.md`
confirms it has had two rows since the section was written, so the "three" is pre-existing. This PR
re-asserts it in a new document without re-deriving it, which is Rule 1's own failure mode applied
to the answer that explains why Rule 1 cannot be a gate. Worth a one-word fix in both places.

**Gates run this session** (all from a clean tree at `c8364e6f`; `git status --porcelain` shows only
the two untracked review artefacts):

| Gate | rc | Output |
|---|---|---|
| `check-docs.py` | 0 | "Documentation integrity OK" |
| `check-anchors.py` | 0 | 13 registered, floor 22 held |
| `check-dashboard-entry.py` | 0 | "an entry block was added" |
| `check-roadmap-consistency.py` | 0 | 2 tracked items open (A6, Q0) |
| `check-explainer-delivery.py` | 0 | 1 shared description, 5 skills cite it, 0 restatements |
| `check-selftest-counts.py` | 0 | 46 scripts |
| `check-plan-file-tags.py` | 0 | 0 across 1451 documents |
| `check-group-claims.py` | 0 | 6 groups |
| `check-banner-armed.py --self-test` | 0 | 160/160 |
| `gen-dashboard.py` | 0 | 253 entries |
| `check-backlog-closure.py` | 0 | WARN ×3 — see M5 |

⛔ **NOT RUN, treat as NOT CHECKED:** `check-plan-code.py --mutate .` (the ~14-minute sweep) and the
Postgres-backed schema gates. Docs-only diff, no `scripts/` change, so no mutation anchor can have
moved — but I did not verify that by running it, and this review makes no claim about mutation
coverage. `timeout(1)` is unavailable on this machine (`/bin/bash: timeout: command not found`),
which is why the gate loop above was re-run without it rather than reported from a bad harness.

**Attack 6 — did anything become untrue?** One survivor, M2. Method: `grep -rn "development-velocity"`
across `*.md *.py *.yml *.sh` (9 non-self sites, 8 fine), plus a targeted phrase sweep for
`nothing adopted|Nothing in it governs|NOT ADOPTED PROCESS` across `docs/*.md` and `.claude/`. I did
**not** search `node_modules`, `.git`, or the `docs/superpowers/` spec corpus by full text — **not
searched**.

**Attack 7 — roadmap and backlog rows.** Roadmap checkboxes are correct as to *what landed*:
`:2075` §6+§7 adopted ✅ (verify: `process-checklists.md:428`, `:644` exist), `:2080` five questions
answered ✅ (verify: `development-velocity.md:218-252` has five), `:2082` Q0 open ✅, `:2087`
side-job hook open ✅. `:2077` ticks a *decision* rather than work, which this repo permits, but its
stated evidence is H1. The backlog row is M6. No checkbox is ticked for undone work and none is left
open for done work.

**Attack 3 — is the side-job rule usable today?** ✅ Yes; answered in full under L5.

**Attack 5 — is the guard behaving as designed?** Partly; answered in full under M5(c) and M5(d).

---

## Recommended disposition

- **H1** — either produce the CI evidence (a red `verify` on PR #343 at `d02ab66b` attributable to
  B1) or rewrite both sites to say what actually happened: the practice was in use, and a reviewer
  found the Blocking by hand while the sweep was still pending. The decision can survive; the
  sentence cannot.
- **H2** — retitle Rule 4 to *derive gate lists from the workflows*, name `schema-gates.yml` beside
  `ci.yml`, and change the `check-merge-ready.py` sentence to cite it as the *tool to run* rather
  than as precedent for single-file derivation.
- **M1** — re-derive the survivor count or cite `observer-log-owner-r5-claude.md:259-266` and use
  its numbers.
- **M2** — one sentence at `roadmap-to-launch.md:2063-2064`.
- **M3** — strike or re-label the "Proposed" blocks at `development-velocity.md:179` and `:201`.
- **M4/M5** — PR-body edits before merge; M5(a) is a one-word fix (#344 → #343).
- **M6** — fix row #177's strands ⑴/⑵/⑷ and `files` column in place, per the rule adopted here.
