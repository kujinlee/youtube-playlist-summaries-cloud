# Claude adversarial review — velocity-doc-consistency r1

Subject: `git diff origin/master...HEAD` on `velocity-doc-consistency` (PR #346), 1 commit
(`873fa44b`), 2 files, docs only. Everything below was established by reading the file or running
the command quoted. Nothing rests on recall.

⭐ **Key enabling fact for this round:** the `velocity-177` branch is deleted locally and the PR was
squash-merged as `91f38afe`, so `git log -- docs/development-velocity.md` shows only two commits and
cannot answer any provenance question. The pre-squash fold commits **are still reflog-reachable**:

    git log --all --reflog --oneline -- docs/development-velocity.md
    873fa44b (this PR) · 91f38afe (#345 squash) · 2d4d874c (r4) · ccc19857 (r3)
    e44be4b0 (fold r1) · 229be47a (r1 both halves) · c8364e6f (initial)

Every provenance claim below was taken from those commits, not from the round documents' prose.

## Verdict

**NOT CONVERGED — 2 High · 1 Medium.**

The three contradictions the PR set out to fix are genuinely fixed, and fixed in the right
*direction* (removing counts, not correcting them). The two Highs are both in the **replacement
text**: the paragraph rewritten for contradicting itself still contradicts itself in its final
clause (H1), and the banner note introduced by this PR attributes the defect to the wrong review
round (H2). Both are the exact class the rules being documented exist to stop — a claim about a
population nobody counted, and a provenance assertion that its own source refutes — committed inside
the document that argues for them.

---

## Findings

### 🔴 H1 — The replacement paragraph contradicts itself, in the same clause, and the six-round count names a population of three

`docs/development-velocity.md:198-203` (added by this PR):

> ⟳ **THIS PARAGRAPH CONTRADICTED ITSELF FOR HOURS, AND THE WAY IT DID IS THE POINT.** It opened
> *"Four rules came out of this"* and closed *"five rules, not four"* — because r3 (Low) found the
> count stale after rule 1b was added and **appended the correction to the end instead of editing the
> opening sentence.** […] The fix for one rule's defect broke another rule, in the paragraph that
> introduces both, **and six review rounds plus an architecture review passed over it — none of them
> had this file's internal consistency in scope.**

Two independent defects in that final clause.

**(a) The sentence refutes itself.** It says r3 *found the count stale*, and then says *none of them
had this file's internal consistency in scope*. Both cannot be true, and the first is the correct
one. `docs/reviews/claude/velocity-177-r3-claude.md:153` is a finding titled *"four rules" names
a population of five*, whose second bullet (`:158-161`) is:

> - `docs/development-velocity.md:192-195` outlines the adopted rules as four — *"provenance of
>   numbers, fixing a sentence in place, a class claim requiring a class sweep, and deriving gate
>   lists"* — and **omits 1b entirely**.

That is this file, this paragraph, these line numbers, filed as a finding. r3 did not pass over it;
r3 **caught** it. What went wrong is downstream of the review — the *fold* repaired it badly. That is
a materially different and more useful story than "no round had it in scope", and the PR's own
sentence already contains it.

r3 is not the only counter-example. `docs/reviews/codex/velocity-177-r4-codex.md:7` records that the
r4 Codex half searched **this file** for exactly this defect class and reports *"the surviving
sibling copy in the changed rationale is `docs/development-velocity.md:203`"*. And
`docs/reviews/coordinator/velocity-177-r1-coordinator.md:26` states the r1 subject as
`git diff origin/master...HEAD`, which included this file — `:63` of the same document discusses
*"§6 and §7 of `development-velocity.md`"*. The file was in the diff, in the subject, and in the
findings of at least three rounds.

**(b) "six review rounds" is a count over a population of three.** The contradiction being described
was *created by the r3 fold*. Verified by reading the hunk:

    git show ccc19857 -- docs/development-velocity.md

    -you know what this measurement bought: provenance of numbers, fixing a sentence in place, a class
    -claim requiring a class sweep, and deriving gate lists rather than recalling them.
    +you know what this measurement bought: provenance of numbers (rule 1), **the population a number
    +names** (rule 1b), fixing a sentence in place, a class claim requiring a class sweep, and deriving
    +gate lists rather than recalling them — **five rules, not four.**

Only **r4, r5 and r6** ran after `ccc19857`. Three rounds could have seen this defect; r1, r2 and r3
could not, because it did not exist. The architecture review *is* correctly included — confirmed by
ancestry, `git merge-base --is-ancestor ccc19857 c9679f6e` → true, and `c9679f6e` → `2d4d874c` → true,
so the review sat between r3 and r4.

This is **rule 1b** — *the population a number names* — failing in the paragraph whose subject is
rule 1b. The honest figure is *three rounds and an architecture review*.

**Suggested fix:** replace the clause with what the evidence supports — *"r3 caught the stale count;
the fold that answered it left the opening sentence, and the three rounds plus the architecture review
that followed did not re-read the paragraph as a whole."* That is both true and a sharper argument for
rule 2 than the current version, because the failure moves from *nobody looked* to *the fix was
applied where the reader does not arrive first*, which is rule 2's actual thesis.

**Sibling search — DONE.** `grep -n "six review rounds\|no round\|in scope" docs/development-velocity.md`
→ the single instance at `:203`. The same claim also appears in the dashboard entry at
`docs/dashboard-entries.md:12258` (*"six review rounds and a Phase 6 architecture review passed over
all three"*), which is worse, because "all three" makes the population claim for each defect
separately — and see H2 for the third. No other instance in the diff.

---

### 🔴 H2 — The banner note introduced by this PR attributes the defect to the r5 fold; it was the r1 fold

`docs/development-velocity.md:13` (added by this PR):

> `⟳ **§3 and §4 were in this row AND in their own rows above — two statuses each**, in a banner whose first line says to read it before citing anything below. Removed here, r5-fold defect found 2026-09-24`

and `docs/dashboard-entries.md:12269`:

> *"Both introduced by the r5 fold, which added the new rows and left the old one."*

**Measured — it was `e44be4b0`, the fold of round 1.** One command shows the whole thing, because the
defect and its cause are in a single hunk:

    git show e44be4b0 -- docs/development-velocity.md   # "Fold round 1: thirteen findings…"

    -> | **§2 Q0**, §3 signals, §4 timing rules | 🟠 **DECIDED IN FORM, NOT BUILT** — see §9 Q2 |
    -> | everything else | proposal |
    +> | **§2 Q0**, §4 timing rules | 🟠 **DECIDED IN FORM, NOT BUILT** — see §9 Q2 |
    +> | **§3 seam signals** | 🟠 not MECHANISED — but they are **observations you can apply by hand today**… |
    +> | **§9 answers**, **§10 brief** | ✅ **DECISIONS, not proposals.**… |
    +> | §1, §3, §4, §8 | measurement and rationale — proposal |

The r1 fold is the commit that split `everything else | proposal` into the enumerated catch-all
`| §1, §3, §4, §8 |` **and** gave §3 its own row **and** kept §4 in the DECIDED-IN-FORM row. Both
double-statuses were created there, in one commit. Neither `ccc19857` (r3) nor `2d4d874c` (r4) touches
a banner row at all — verified by `git show <c> -- docs/development-velocity.md | grep -E "^[+-]> \|"`,
which returns **nothing** for `229be47a`, `ccc19857` and `2d4d874c`. **No r5 or r6 fold commit touches
this file**; the reflog-reachable set above has no such commit.

Two consequences, and the second is the reason this is High rather than Low:

1. The attribution is simply wrong, in delivered text, in a document whose §6 argues that a claim
   must be traceable to the thing it names. A reader auditing "the r5 fold" will open the wrong round.
2. It changes the arithmetic the PR rests on in the **opposite** direction to H1(b). If the r1 fold
   introduced it, the banner defect was live for **r2, r3, r4, r5 and r6** — five rounds, not one.
   The PR's framing ("introduced by the r5 fold", so barely reviewable) understates how long this one
   stood, while H1(b) overstates it for the other defect. The same claim is wrong in both directions,
   which is the tell that no round count was derived.

Note the §3 row itself carries `(r1 Low: …)` and `:15` says *"r1 Low: the three rows above were wrong
in the first version of this banner"* — the file already records r1 as the round that rewrote these
rows. The evidence for the correct attribution was on the adjacent line.

**Sibling search — DONE.** `grep -n "r5 fold\|r5-fold" docs/` across the diff → the two sites above
(`development-velocity.md:13`, `dashboard-entries.md:12269`). I also checked every other provenance
attribution added by this PR: the `r3 (Low)` attribution at `:199` is **correct** (see *What I
checked and found clean*, attack 3), and the §6 banner claim is correct (the count there was added by
`c8364e6f`, the branch's first commit, so all six rounds did see that one).

---

### 🟡 M1 — The completeness claim "no count-of-rules survives" is refuted 66 lines above the entry that makes it

`docs/dashboard-entries.md:12272-12273` (added by this PR):

> *"Verified: no section appears in two banner rows, and no count-of-rules survives outside the quoted
> description of the defect."*

The first half is true (I verified it independently — see clean list). The second half is false in the
file the sentence is written in. `docs/dashboard-entries.md:12177`, inside the **immediately preceding**
`## 2026-09-24` entry (the one for PR #345 — entry headers at `:12110` and `:12174` bracket it):

> *"The change itself is modest: **four rules** about what an author writes down, because a study
> earlier today found…"*

That is a count of the same population — five rules (1, 1b, 2, 3, 4) — stated as four, in the
human-facing narrative half of the dashboard log, which `scripts/gen-dashboard.py` renders for a
reader. It is the same defect as the §6 banner count this PR removes, in a file this PR edits.

⚠ **I am not asserting the fix is to rewrite it.** `docs/dashboard-entries.md` is an append-only
record and editing a shipped entry may be the wrong move — that is the coordinator's call. The finding
is the **claim**, not the line: the PR asserts a swept scope it did not sweep. Either narrow the
sentence to the file it is true of (*"no count-of-rules survives in `development-velocity.md` outside
the quoted description"*) or fix the sibling. As written it is an unverified completeness claim in a
PR about unverified claims.

**Sibling search — DONE.** `grep -rn "four rules\|five rules\|These four" --include=*.md docs/ *.md`
excluding `docs/reviews/`. Hits: `development-velocity.md:199` (the quoted defect description —
legitimate, and the PR's sentence explicitly exempts it); `dashboard-entries.md:12177` (the finding
above); `dashboard-entries.md:12243`/`:12263` (this PR's own quoted description — legitimate);
`dashboard-entries.md:112` and `:7861` and
`docs/superpowers/plans/2026-09-14-review-decision-procedure.md:355` — all three about **different**
populations, read and confirmed unrelated. `docs/process-checklists.md` carries **no** count of the
rules (the r3/r5 fixes landed there), which I confirmed by the same grep returning no hit in it.

---

## What I checked and found clean

**Attack 3 — "r3 APPENDED the correction rather than editing the wrong sentence" is TRUE.** Verified
from `git show ccc19857 -- docs/development-velocity.md` (hunk quoted in H1(b)). The opening sentence
`**Four rules came out of this, all free.**` is a **context line** in that hunk — untouched — while
the correction `— **five rules, not four.**` and the whole `⟳ **r3 Low: …**` note are additions after
it. The load-bearing clause (*"instead of editing the opening sentence"*) is exactly right.
⚠ One nuance, not a finding: the r3 fold *did* edit inside that paragraph — it inserted `(rule 1)` and
`**the population a number names** (rule 1b)` into the list mid-sentence. So "appended the correction
to the end **instead of** editing" compresses slightly; what it actually did was edit the list and
leave the count. The PR's characterisation survives because its claim is about the *opening sentence*,
which is verifiably untouched.

**Defect 3's fix is COMPLETE — no section now carries two statuses.** Method: extracted every `§n`
token from the banner's status rows only (`sed -n '5,13p' docs/development-velocity.md`, rows read
individually) and mapped section → row. Result: `{§6,§7}` `{§2,§4}` `{§3}` `{§5}` `{§9,§10}` `{§1,§8}`
— each of §1–§10 in exactly one status row. A naive `grep -oE "§[0-9]+" | uniq -c` over the same range
reports §3, §4, §5, §9 and §10 more than once and is **wrong**: the extra occurrences are inside the
new explanatory note at `:13` and inside prose within the §5 and §9/§10 status cells, not status
assignments. I checked each by reading the row.

**Defect 2's fix is complete.** `grep -n "These four rules\|four rules now live" docs/development-velocity.md`
→ no hits. The §6 banner at `:176` now reads *"✅ **These rules now live in…**"*.

**The surviving self-counts in the file are TRUE, so I did not file them.** The brief asked for any
surviving count of the repo or of the file's own contents. Three remain and all check out:
- `:58`, `:61`, `:93` — *"§3's four signals"* / *"all four signals"*. §3's body has exactly four
  numbered items (verified by `sed -n '/^## 3\./,/^## 4\./p' … | grep -E "^[0-9]+\."` → items 1–4).
- `:252`, `:254` — *"The five open questions"* / *"All five were settled"*. §9 has exactly five
  (verified the same way → `1 ·` through `5 ·`).
- `:258` — *"covers exactly two files"*, about `check-docs.LINE_BUDGETS`; independently confirmed by
  r1 at `docs/reviews/claude/velocity-177-r1-claude.md:504` against `scripts/check-docs.py:191-194`.
⚠ Worth stating for the coordinator: `development-velocity.md` is **not** governed by the shape
invariant — `docs/process-checklists.md`'s invariant is scoped to *that* section, its preamble and its
five rule bodies (`docs/reviews/coordinator/velocity-177-r5-coordinator.md:58`). So a true count here
is not a violation, and I did not treat it as one. Only false or self-contradicting counts are in
scope for this PR, which is the right scope.

**Attack 2 — did removing the counts lose anything?** No. The outline at `:192-196` now names all five
rules with their numbers in reading order (1, 1b, 2, 3, 4), which is strictly **more** information
than the total it replaced, and it is the form that cannot go stale when a rule is added. The one thing
a reader loses is the ability to check they have seen all of them without counting — which is exactly
the check the PR argues should be done against `process-checklists.md`, not here.

**Attack 5 — does anything else under `docs/` now contradict the edited text?** Nothing found.
Method: `grep -rn "development-velocity" --include=*.md docs/ *.md` (excluding `docs/reviews/`, which
is historical testimony and is *supposed* to record the old state), then read each referring passage
in `docs/roadmap-to-launch.md`, `docs/backlog.md` and `docs/process-checklists.md`. None cites a rule
count or a banner row status, so nothing became stale. `docs/process-checklists.md` is untouched by
this PR (`git diff --stat origin/master...HEAD` → 2 files, neither is it), and the PR's claim that it
is untouched is therefore true.

**Both repo gates pass on the deliverable.** Run, not assumed:
- `python3 scripts/check-docs.py` → `Documentation integrity OK`, **rc=0**.
- `python3 scripts/check-dashboard-entry.py` → `ok — an entry block was added`, **rc=0**.
I specifically checked whether the new table row at `:13` with an **empty first cell** upsets the
banner grammar — it does not; `check-docs.py` passes with the row present.

**Attack 6 — the dashboard entry.** The human-facing half is accurate and does not overclaim; in
particular *"nothing that governs was wrong"* is correct (`process-checklists.md` untouched, verified
above), and *"⛔ Not a governing-document change"* is correct. The two overclaims are in the `<!--tech-->`
half and are filed as H1 (the six-round count) and H2 (the r5 attribution); M1 is its verification
sentence.

## Sibling-search summary

| Finding | Searched for siblings? | How | Turned up |
|---|---|---|---|
| H1 | Yes | `grep -n "six review rounds\|no round\|in scope"` on the file; read all 6 coordinator + 3 claude + 4 codex round docs for this file's name | one in-file instance, one in the dashboard entry (`:12258`, same claim, worse form) |
| H2 | Yes | `grep -n "r5 fold\|r5-fold"`; then audited **every** provenance attribution added by this PR against the reflog commits | 2 sites for this claim; the other two attributions (`r3 (Low)`, §6 banner) are correct |
| M1 | Yes | `grep -rn "four rules\|five rules\|These four" --include=*.md docs/ *.md` minus `docs/reviews/` | 1 true sibling (`dashboard-entries.md:12177`); 3 unrelated populations, each read |
