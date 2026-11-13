# Architecture review — the marketplace document pair and `check-claim-propagation.py`

**Convened 2026-10-16 because the thrashing condition fired**, not on a schedule: 8 of round 4's 9
findings were introduced by round 3's own fix, with Blocking flat at 2 → 2, which is
`review-method.md`'s definition. Subject at `2e79f464`. Prior reviews read and not re-litigated:
`architecture-review-2026-10-03.md`, `architecture-review-2026-10-14-canonical-source.md`;
ADR-0010 and ADR-0014 govern parts of this area and are taken as settled.

⚠ **Every number here was measured by the coordinator, not taken from the exploring agent.** Three
figures the agent reported are corrected below, and the brief I gave it was wrong about one.

---

## The finding that decides the review

> ### ⛔ THE GUARD IS GREEN RIGHT NOW, OVER THREE LIVE INSTANCES OF THE CLASS IT EXISTS TO CATCH.

`python3 scripts/check-claim-propagation.py` → **rc=0**, *"7 retired claim(s) not re-asserted, 11
live claim(s) at every declared site, 2 derived figure(s) agree with their source."* And at that same
commit:

| # | The claim | Withdrawn / corrected at | Still asserted at |
|---|---|---|---|
| ① | *D9 is C4's grading predicate* | spec `:297`, spec `:623` (**"THAT CLAIM IS WITHDRAWN"**) | **the spec's own §4d heading, `:580`** · fragment `:487` · served page `:564` |
| ② | D5's falsifier | spec `:525` — the checkable *"same visual unit"* form | fragment `:584` still carries the **retired, unobservable** *"read and acted on as though"* form |
| ③ | D8's acceptance bound | spec `:1047` — *"ANY OF THE THREE"* | fragment `:954` still *"either correction"*, over a list of three |

Measured: `grep -c 'same visual unit'` → spec **1**, page **0**. `grep -c 'either correction'` →
spec **0**, page **1**. ⭐ **And ① makes the page contradict itself** — it asserts the withdrawn claim
at `:487` and withdraws it at `:1020`, 533 lines apart.

**So the guard does not have a coverage gap. It has the wrong shape.** It was built in round 2, has
been extended in every round since, and at the end of four rounds it certifies a document pair that
is drifted in at least three places, one of which is a section heading in the file it audits.

---

## Why: the remedy is the opposite of the repo's own decided one

⛔ **`scripts/check-canonical-source.py` ALREADY SOLVES THIS, AND I DID NOT LOOK.** Its first line:

> *"A mechanism described in more than one place drifts. This refuses the second copy."*

Its origin, from its own docstring, is this review's situation almost word for word: a mechanism
written out at **six sites**, *"nothing compared them"*, and **across five consecutive review rounds
a reviewer found, every single round, at least one copy that had drifted.* It names the cause as this
repository's most-measured defect — *a second implementation of one rule drifts*, 17 recorded
instances — **applied to prose instead of code.** It is green today over 2 registered mechanisms.

**The two guards take opposite remedies, and that is the whole finding:**

| | `check-canonical-source.py` | `check-claim-propagation.py` |
|---|---|---|
| what it permits | **one** statement; a citing site carries a marker and no copy | the same claim at **every** site |
| what it refuses | the second copy | the sites **disagreeing** |
| failure it prevents | drift cannot exist | drift is **reported after it happens** |
| its own words | *"a guard that waits for the drift is a guard that reports the damage"* | — |

**My guard institutionalises the duplication it exists to police.** Requiring a claim at N sites
makes N−1 copies mandatory, then audits them. That is why every round found another one: the shape
guarantees a supply.

### ⛔⛔ AND THE REPO DID NOT MERELY HAVE A GUARD — IT RAN THIS EXACT REVIEW TWO DAYS EARLIER, UNDER THIS EXACT TRIGGER, AND THE REDESIGN LANDED

`docs/reviews/architecture-review-2026-10-14-canonical-source.md`, tracked in the roadmap as
**"One canonical source per mechanism — ARMED BY THRASHING, redesign LANDED 2026-10-14"**. Its
convening story, from the roadmap: *"the `plugins-handoff-citations` branch produced a drifted copy
in five consecutive rounds, **each caused by the previous round's own fix**."* Same trigger, same
clause of `review-method.md`, forty-eight hours earlier. Its completed items:

- ✅ *"Two mechanisms collapsed to one file each, **with every live site citing rather than
  restating**"*
- ✅ `check-canonical-source.py`, wired into CI, each failure mode proved detected and falsified over
  a green control

⭐ **AND ITS OPEN ITEM IS THIS PAIR.** The same review left behind: *"a mechanism missing from
`CANONS` is unprotected — backlog #282"*, split to **#288**, which records that
`shared/explainer-delivery.md` *"carries no `<!-- canon: -->` marker at all (grep: 0)"*.

**So candidate 1 is not a proposal. It is the application of a decision this project already made,
to an instance its own follow-up row already names** — and `check-claim-propagation.py` was built
*two days after* that decision, under the same trigger, implementing the opposite remedy, because I
did not read the review whose title I had been shown.

⚠ **This also shrinks the work rather than growing it:** the mechanism, the guard, the CI wiring and
the marker grammar all exist and are green over two registered mechanisms. What is missing is a
`CANONS` entry.

### The deletion test

Delete `check-claim-propagation.py` (1,458 lines, 96 cases, 32 mutations) and what reappears is
**20 registered claims** losing their check — against a measured population of **68 verbatim shared
passages ≥ 8 words** between the two documents (and that is a floor: it cannot see paraphrase, which
the guard's own docstring declares as its false-negative direction). Its interface is three hand-kept
lists totalling **161 lines**; its implementation is **1,297**. By the depth test that is respectable
leverage — but leverage *in the wrong direction*: it is a deep implementation of a shallow idea.

⚠ **It is not a pass-through and deleting it is not the recommendation.** Its derived-figure check has
caught the spec's own line count **three times**, including twice in one session, and that half has no
equivalent in `check-canonical-source.py`. Any candidate below must keep it.

---

## Candidates

### 1 — Give rules one home and a citation form; let the page cite instead of restate

**Files** `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md`,
`docs/explainers/…walkthrough.fragment.html`, `scripts/check-canonical-source.py`,
`scripts/check-claim-propagation.py`.

**Problem** The **seam** between the spec and the walkthrough has two **adapters** — spec prose and
page prose — and no **interface**. Each adapter states the rules in its own words, so a rule is a
rule in two implementations, and the only thing tying them is a hand-kept registry covering 20 of
≥ 68 shared passages.

**Solution** Separate the **normative surface** from the **explanatory** one, using the mechanism
that already exists: **register the spec's rules as a `CANONS` entry** so the page must carry
`<!-- canon: … -->` and cite rather than restate. That discharges part of the already-filed #282 /
#288 gap. The propagation guard keeps the half with no equivalent — the derived figures, which have
caught the spec's own line count three times — and sheds the half that polices copies.

⭐ **And the exemption question is already shaped by precedent, which makes it decidable rather than
a matter of taste.** `check-canonical-source.py` exempts `docs/reviews/**` and
`docs/dashboard-entries.md` on a stated principle — *"a record, not a rule a reader follows"*. So the
owner's actual question is narrow: **is a walkthrough page a record, or does it state rules a reader
follows?** Round 4's evidence says the latter — the three drifted claims are all rules — but the page
is also the Phase 1 gate instrument, and that is the trade.

**Benefits** *Locality*: a rule changes in one place, and no fold can reach "the site the finding
named" because there is one site. *Leverage*: the citation marker is a far smaller interface than
20 hand-kept token registrations. *Tests*: the guard's suite stops growing one case per discovered
spelling — rounds 3 and 4 added 65 cases chasing `<em>`, a whitespace node and a `<br>`, all of which
exist only because a phrase must be matched across two prose copies.

⚠ **The honest objection, which belongs in the grilling loop:** a walkthrough exists *to* paraphrase
a 1,136-line spec for a reader. If "cite, don't restate" is applied to explanation as well as to
rules, the page stops being readable. The rule/explanation line is load-bearing and is not yet drawn.

### 2 — Name the mechanism in `CONTEXT.md`

**Files** `CONTEXT.md`.

**Problem** Four rounds could only name the instance in front of them, because the repo has **no term
for a claim stated at several sites and updated at one**. Measured: `grep -niE "propagat|restat|more
than one place"` over `CONTEXT.md` → **nothing**.

⭐ **This is a precedent, not a theory.** `CONTEXT.md`'s own Verification Stack section was added by
**architecture review #7**, whose recorded finding was that *"seven consecutive review rounds had
been argued in words this file did not contain: with no shared terms, each round could only name the
instance in front of it, and the same defect kept recurring in a sibling."* Identical shape, one
component over.

**Solution** Add the term, with the measured history and the two remedies (refuse the copy; or
require every site) distinguished by name.

**Benefits** Cheap, and it is the only candidate that makes the *next* review able to say what it is
looking at. It does not dissolve the class by itself.

### 3 — A document inside its own corpus names the producer, not the figure

**Files** the spec's §3; `scripts/check-claim-propagation.py`'s `DERIVED`.

**Problem** Round 4's B1 was the spec's own measurement going stale because a *sibling commit edited
a file the spec counts*. I fixed it by **dating** every count. ⛔ **The repo had already decided a
stronger remedy and I did not look:** `CONTEXT.md:119` once carried a guard count, and on 2026-09-21
*"the number is **removed rather than corrected** — it had no owner, and this file is inside the
corpus it describes, so any figure here is stale at the commit that writes it"*; it names
`check-ratchet-contract.py` instead. Verified: that producer prints **48** today.

**Solution** Where a producer exists, name it instead of carrying a figure. Where none exists, keep
the dated form — and say which of the two applies and why.

**Benefits** A named producer cannot decay; a dated figure becomes a historical note the reader must
discount. ⚠ **Bound:** §3's nine-file total has **no** producer, and inventing one would duplicate an
enumeration that lives in prose — the very defect under review. So this candidate is partial by
construction, and that is the honest reason the dating fix was not simply wrong.

### 4 — The fragment → composed-page seam has 21 instances and one adapter is checked

**Files** `.agents/skills/shared/explainer-delivery.md`, `scripts/brief-compose.py`,
`scripts/check-claim-propagation.py`.

**Problem** I wrote a recompose obligation into the shared delivery contract for **every** page
producer. Measured: `docs/explainers/` holds **62** composed pages, **21** with a fragment sibling;
`check-claim-propagation.py` audits **3 paths — one pair.** By *one adapter = hypothetical seam, two =
real seam*, this is a real seam with 21 instances and a guard over one, and round 4's B2 established
that even for that one the guard does **not** verify composition — only that registered claims appear
at both paths.

**Solution** Either a producer-side check (recompose and diff, once, for any fragment with a sibling)
or withdraw the contract's generality to what is actually enforced.

**Benefits** *Leverage*: one check covers 21 pages instead of 20 being covered by a paragraph.
*Locality*: the obligation and its enforcement stop being 21 pages apart.

---

## What I did NOT do, and why it matters

⛔ **The three live drifted claims above are recorded as EVIDENCE, not fixed.** Fixing the instance
in front of me is the behaviour that produced four rounds of this, and doing it a fifth time while
the architecture review is open would be the review's own subject. They are `docs/backlog.md` row
**297**; whichever candidate is chosen should dissolve them, and if the chosen candidate does not,
that is a fact about the candidate.

⚠ **No candidate is implemented.** Per this skill, candidates are presented and the choice is the
owner's — and here that is not deference: candidates 1 and 3 point in different directions about how
much the walkthrough may restate, which changes what the owner reads in the document they must
approve.

## What this milestone decided that is still not written down

**That a reader-facing page may restate a spec's rules in its own words.** Every round's findings
followed from it, no document states it, and no one ever decided it — it is simply how the first page
was written. Candidate 1 is that decision, made deliberately for the first time, in either direction.
