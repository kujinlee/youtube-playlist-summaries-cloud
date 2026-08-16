# Portable Practices — what this project learned that a NEW project can use

**This project has two deliverables.** One is the product. The other is a battle-tested harness and
the documents that make it reproducible somewhere else. This file is the second one's index.

**Status: STARTED 2026-08-11, deliberately incomplete.** §1–§7 were measured on 2026-08-11, §8 on
2026-08-12, §10 on 2026-08-13, §11 on 2026-08-15. The great majority of the memory files and review
documents have **not** been mined yet — see *Not yet mined*, whose counts are re-enumerated, not
recalled, whenever this file is edited.

---

## How an entry earns a place here

Two filters, both required:

1. **Measured** — it cites an incident with files, numbers, or a command output. Not a belief someone
   held confidently.
2. **Project-independent** — it would hold in a repo with no Supabase, no Gemini, no Fly.

Most of this project's hard-won lessons fail filter 2 and that is fine — *"postgrest returns aborts,
doesn't throw"* is expensive knowledge that travels nowhere. Do not dilute this file to make it longer.

**Write entries by ENUMERATING, not by recalling.** On the day this file was created, three separate
descriptions-from-memory were wrong: *"there are three ratchets"* (six), *"34 chunks referenced, 9
scanned"* (9 either way), *"most projects have no gates"* (unevidenced). None was caught by re-reading.
Each was caught by running something that counts. **A summary written at the end of a long session is
the highest-risk artifact in the repo.**

---

## 1. The method: measurement beats assertion — and a script can be either

> **A script beats a claim only when it reads the thing the claim is about.**
> The test is one question: *what does this thing actually open?*

**Measured.** `scripts/check-service-confinement.ts` is static — no env, no fetch, no network. Gate
"B5" cited it as evidence about **production**. It ran in CI, was green for months, and could only
ever pass. A script pointed at the wrong subject is an assertion in better packaging, and **more**
dangerous than prose because a green check is not re-examined.

Contrast, same day: `supabase migration list --linked` read prod and beat the doc (prod was at `0022`,
docs said `0021`, and `0023` had been unapplied for eight days). `check-ratchet-contract.py` read the
scripts and beat the author's memory (six ratchets, not three).

**Portable:** the question. **Local:** every script named here.

## 2. "Cannot run" is a FAILURE, never a pass

If a check cannot reach what it measures, it must fail loudly and say *treat this as NOT RUN*.

**Measured — five distinct instances in one day.** A reviewer sandboxed out of the Docker socket that
reviewed by *reading* and reported success. An integration suite green against the wrong schema. A
`npm run … | tail` pipeline reporting exit 0 while the command errored (the exit code was `tail`'s).
A bundle scanner that would have reported "clean" had its extractor matched zero scripts. A staleness
check that needed an explicit fail-closed branch when the release could not be determined.

**Portable in full.** This is the single most transferable rule the project produced.

## 3. A gate states the observation that would make it FAIL

If none can be named, it is a **decision** or an **investigation** wearing a checkbox.

**Measured.** Rewriting seven gates in this format: five were easy, and two were never checkable.
*"Check whether a rendering share starts returning 503"* has no pass condition because nobody had
decided what version skew **should** do — tolerate, refuse, or heal are all coherent and **the same
observation grades differently under each**. *"We chose 5000¢"* cannot fail at all; it became a real
gate as *"fails if the configured value is no longer 5000"* — a drift assertion, which is also the
only form that would have caught the value being changed by hand.

**Portable:** the rule and the two failure shapes. **Local:** the linter that enforces it.

## 4. A tick records *that* something was verified, never *what against*

Manual checks need the build they were verified on.

**Measured.** Two acceptance items were ticked on 2026-07-22/23 — the v3/v4 era — while the app ran
**v6**. Both were claims about code that had not run in two releases, and no document knew. Same shape
as the migration drift found the same morning: the record captured a claim without its subject.

**Nuance worth keeping:** code-enforced acceptance points do **not** go stale on deploy; only the
human-checked ones do. Reopen the part that rots, not the whole item.

## 5. Reconciliation reads the running system, not just git and files

Session resume checks **three** things: `git log`, the files, and the deployed reality.

**Measured.** A rule saying *"write down out-of-band changes at the moment you make them"* existed for
three weeks and did not prevent a recurrence — because every clause fires at mutation time and depends
on remembering. What caught it was a routine live read at session start, with no suspicion attached.
**Move the check from the mutation to the reconcile.**

**Portable:** the principle, and the habit of one read-only status query per external system.

## 6. Structure: a short spine, detail routed by READ-TRIGGER

The document layout transfers even though every document does not.

- a **short spine** — what must be true, in what order, who decides
- **detail routed by read-trigger**, not by topic: *"read this when a review round is starting"* beats
  *"review documentation"*, because it tells a reader when they are **not** the audience
- **line budgets on always-loaded files, enforced by a script** — this project's spine reached 576
  lines, ~28% added in two days, each addition individually justified and the aggregate unread

**Portable:** the skeleton. **Local:** the four documents it points at.

## 7. Before adding a rule, ask whether it can be a script

**Measured, and it cuts both ways.** Of six mechanisms proposed on one day, five went unbuilt and the
only thing added was prose. But the counter-case matters too: a convention written as prose and
*then* enforced was found to be **factually wrong about its own subject** the moment the enforcement
was built. Build the enforcement first, or at least before you believe the description.

## 8. Sort findings by what they ATTACK, before fixing any of them

> A lopsided distribution is telling you the **shape** is wrong. It is not telling you that you have
> N bugs.

**Measured 2026-08-12.** A dual adversarial review of a proposed pre-merge gate returned **26 findings,
5 Blocking**. Sorted by target, every Blocking and every High landed on the **enforcement layer** — the
mandatory scope, a score recorded in the PR body and bound to the head SHA, the CI check, a renderer,
an override valve. The thing the whole design existed to deliver — a generated explainer document —
drew **none**.

Removing that layer **dissolved 21 of the 26**. Three were genuinely fixed and two stayed live. The
alternative was 26 patches, and the reason that fails is worth quoting rather than paraphrasing:
*"a local question can always be answered yes by patching… a wrong shape never fails a round."* Each
patch would have made the gates greener while the shape stayed wrong.

The sort costs minutes and needs no tooling — it is a column in a table you already have. What makes
it work is that it asks a question no individual finding can answer: *is this design accumulating
defects everywhere, or in one place?* Everywhere means ordinary work. **One place means that component
is load-bearing and shouldn't be.**

**And the removal is itself an unreviewed design change — re-review it.** Round 2 on the stripped-down
version returned **20 more findings, 3 Blocking**, several of them *caused by* the removal. The
sharpest: the surviving rule had been rehomed into a document that nothing loads at session start,
whose stated read-trigger was a gate — and the whole point of the removal was that this was no longer
a gate. Deleting the mechanism deleted its activation path with it, and nothing said so.

**Portable:** the sort, the reading of a lopsided result, and re-reviewing the removal.
**Local:** the gate that was removed.

---

## 9. If your agent generates an interactive artifact, it must be able to RUN it

> An affordance the author cannot execute is an affordance nobody has tested. Not "lightly tested" —
> **untested**, however carefully the code was read.

**Measured 2026-08-12/13.** An agent skill generated a self-contained HTML document and delivered it
as a `file://` path. A small question-capture widget was added to it — select text, type a question,
send. It shipped **four separate defects in four rounds**, and the reader found every one:

| | defect | why reading the code did not catch it |
|---|---|---|
| 1 | No send affordance at all — a textarea, and Enter did nothing | The code was *present and correct*; the interaction was missing |
| 2 | The only button was squeezed to a sliver | A flex row with `flex:1` on a long hint and no `flex-shrink:0` on the button. Invisible in source, obvious on screen |
| 3 | The Enter handler referenced a variable declared **below** it | Would have thrown on first use; caught only by re-reading, never by running |
| 4 | "Send" wrote to a directory the agent **cannot read** | The OS denies it (`Operation not permitted`). No amount of re-reading the page reveals this |

Defect 4 is the important one: **it was not in the code at all.** It was a false belief about the far
side of a boundary — *the browser writes the file, therefore the agent reads it* — where only the near
half was ever checked.

The root cause of all four was one property: `file://` is the most isolated context a browser has, so
the automation could not open the page. **Serving the same bytes over `http://127.0.0.1` dissolved
the whole class**, and did it twice over:

- the artifact gained a **channel** — it can `POST` to something that writes where the agent reads;
- the agent gained **execution** — it can navigate, click, and read the DOM back.

The first affordance verified after that change was verified *by clicking it* and watching the effect
land on disk. The bytes did not change: served, it posts; opened as a bare file, it hides the control
and falls back to the clipboard. **Progressive enhancement, so the artifact still opens untouched in
five years with no server running.**

**How to apply.** Ask, of any artifact your tooling emits: *can I execute this, or only read it?* If
only read it, the interactive parts are unverified by construction and a human becomes your test
suite. Serving a directory over loopback is ~350 lines and removes the constraint. Bind `127.0.0.1`
only, resolve paths **before** checking containment, and allowlist extensions — a generated artifact
usually quotes private source.

**The generalisation, which showed up four times in one session:** a claim about the *other* side of a
boundary is the one nothing tests. Three more instances, same shape, same night — a route's comment
asserting what its caller guaranteed; a skill asserting that a delivery tool rendered HTML; a script's
docstring asserting a sibling would discover it. Each was written confidently, each was false, and
each was caught only by *running the neighbour* rather than re-reading the sentence.

---

## 10. A surviving mutation does not mean "add a test" — first ask whether the guard can FIRE

> Two instruments both reported on this guard. One said **untested**, the other said **protected**.
> It was neither: it was *incapable of ever being true*, and nothing either instrument measures can
> tell that apart.

**Measured 2026-08-13.** A guard was added to stop one user's data rendering under another account,
inside an async continuation:

```js
const requestedFor = userId;               // captured when the load starts
// …await…
if (requestedFor !== userId) return null;  // "is it still the same account?"
```

The enclosing function is a **closure recreated on every render**. The caller held the version from
the render where `userId === 'a'`, so after a switch to `'b'` **both operands still read `'a'`**. The
condition could not be true. It read like a check and did nothing.

**Why neither signal was enough, and this is the whole entry:**

| instrument | what it reported | why that was not a lie |
|---|---|---|
| mutation run | *"no test fails when I delete it"* | true of an untested guard **and** of a no-op guard — the same output for two different diseases |
| reading the code | *"this compares the right two concepts"* | also true; the names were right, the values were not |

Only a test that **reached that branch** separated them. The first attempt at that test did not: an
earlier guard short-circuited the path, so the test passed with the account check deleted. It asserted
a real property against a code path it never entered.

**How to apply.** When a mutation survives, do not jump to *"needs a test"* — that is one of two
diagnoses and the less interesting one. First ask: **can this guard fire at all?** For any predicate
inside an async continuation, name where each operand was captured; if both came from the same closure,
it is decoration. Then check the test reaches the branch you think it does, not merely the outcome you
expect — an earlier guard short-circuiting the path is indistinguishable, from the outside, from the
later guard working.

**The fix is usually to make one operand live** — a ref updated on every render, a value re-read at the
moment of use — rather than to strengthen the comparison. A guard is only as good as the freshness of
what it compares.

Same family as §2 (*cannot run is a failure*): in all three cases a mechanism reports success while
inspecting nothing, and the reported value is indistinguishable from the healthy one.

---

## 11. A rule has two halves — what it asserts and WHERE it applies. Enumerate placements × branches

> Seventeen adversarial rounds on one spec. **Since round 14, every finding has been about placement**
> — and placement fails on two axes that look like one.

**Measured 2026-08-14 → 08-15**, across rounds 14–17 of a single spec. The rule being placed was a
`key is servable` predicate. It *was* contested — round 14 found its bidi class covered 9 of 12 code
points — but that was the last finding about what it asserts. Rounds 15, 16 and 17 produced two
Blockings and a Medium, and **all of them were about where the check goes.**

> ⚠ **The two sentences above were WRONG in the first draft of this entry, and the error is worth
> keeping.** It claimed the predicate had been *"stable since round 12"* and *"correct and
> uncontested"*. Both were written from recall, in a file whose own header says three
> descriptions-from-memory were wrong on the day it was created. Caught within the hour by re-reading
> the predicate, whose inline comments cite the rounds that changed it. **Enumerate; do not recall** —
> including in the entry that is telling you to enumerate.

### The two axes, and they are orthogonal

| Axis | Question | Structure it is about | What it missed here |
|---|---|---|---|
| **Vertical — dominance** | does every path to the guarded state pass through this point? | the **call graph** | a second writer function the rule named one of (**Blocking**); a third interface method the rule named two of |
| **Horizontal — branch** | for every branch **in the provenance of the value being guarded**, does the rule apply? | **control flow** | a helper called in two directions, guarded in both when only one was meant (**Blocking**); a guarded name with **two producers**, specified for one (**Blocking**) |

> ### ⛔ ASK THE BRANCH QUESTION ABOUT THE OPERAND, NOT THE CALL SITE. This entry got it wrong first.
>
> **Measured 2026-08-15, and it cost a Blocking.** The first version of this entry — and the table it
> describes — asked *"which side is the receiver?"*. That felt total, because the two known instances
> were both **direction** defects. It is not the general question.
>
> The very next round found a **third** instance, in a row the table had marked **"One branch"** and
> that an independent second reviewer had **verified as one branch**. Both verifications were correct
> *about the direction*: the call site really was hard-wired to one side. But the **name the guard
> tests** was assembled from **two different sources** one ternary apart —
>
> ```ts
> const to = local.summaryMd
>   ? baseOf(local.summaryMd)                              // arm A: a LOCAL filename
>   : baseOf(applySerial(cloud.summaryMd, local.serial));  // arm B: the REMOTE key, renumbered
> ```
>
> — and the design was written for arm A, three times over, including an operator message telling them
> to rename a local file that on arm B **does not exist**.
>
> **The general question is: what are the branches of the VALUE this guard tests?** Direction is one
> way a value can branch, and it is the conspicuous one because it appears in the signature. Provenance
> is the one that hides, because both arms produce the same *type* and the ternary is upstream of the
> guard.
>
> **The meta-lesson is the expensive part.** The table was built *specifically* to pre-empt a third
> instance. It enumerated every placement, was independently verified, and a third instance walked
> through it — because **the instrument asked a narrower question than the defect class it was built
> for.** When a prophylactic fails, check whether it disagreed with the defect or merely asked
> something adjacent.

**Fixing the first does not prevent the second, and that is the entry.** The guard that failed on the
branch axis had *already* been moved to satisfy dominance — it ran before the durable write, exactly as
an earlier round demanded. **A rule can sit above every writer and still be wrong on one case.**

### The trigger: the SECOND instance, not the third

The two branch-axis defects were the same shape **one table row apart**, found a round apart — one
graded Medium, the next graded Blocking. The response to a *recurring* shape is not a better fix; it is
enumerating the whole domain of that shape. Here that was a table: **7 placements × the branches of the
path each sits in.** Four had exactly one branch; three had two or three.

**Write the trivial rows.** The four single-branch rows cost one line each and are what makes the table
a ratchet rather than an observation: the next reader does not re-derive them, and a placement added
later has a visibly empty cell. *"All branches"* is a valid answer and must still be written down.

### The failure mode it catches that reviewing does not

Filling in every cell forces a question a review never asks: **"how would the code even know?"**

Run before dispatching the next round, the table immediately found that the previous round's
**Blocking fix could not be written**. The rule said *"apply the guard only when the receiver is the
cloud"* — but the function it sat in received the receiver as an **interface** both implementations
satisfy, so the direction was simply absent from its scope. Recovering it meant sniffing the concrete
type, which silently misclassifies any future third implementation.

**The fix was not the rule. It was moving the rule to where the branch is chosen** — the caller, which
had already computed the direction. That placement was also *strictly earlier* than the constraint an
earlier round imposed, so it satisfied both axes at once.

> **For a direction-dependent rule, the dominating point is the line that CHOOSES the direction** — not
> the function downstream that has already lost the information. Same principle as putting an invariant
> in the one private function every writer funnels through, applied to control flow instead of the call
> graph.

### How to apply

1. When a reviewer says *"this rule is stated for one branch/writer of N"* **a second time**, stop
   fixing instances. Enumerate.
2. Table it: one row per placement, one column for the branch set of its path, **one outcome per cell**.
3. For each cell ask **three** things: *"does the rule apply here?"*, *"can this code observe which
   branch it is on?"*, and — the one that costs a Blocking to learn — *"where does the value being
   tested come from, and does it have more than one source?"* Name the operand in the table, not just
   the call site: a row reading *"guards `newBase`, produced by A or B"* asks the question by itself,
   where *"one branch"* answers a different one.
4. Prefer placements the branch set cannot escape: a **private function with no external callers** for
   the dominance axis (a list of exported names is a count), and the **line that selects the branch**
   for the horizontal one.

**Cost and limits, stated honestly.** The table is ~10 lines of spec, and the next adversarial round
verified it row by row against the code and found no third instance — but it did find that the move it
prompted left **stale references to the old location** in the surrounding prose, which is its own
recurring tax. Do this when the shape has recurred or the rule is money- or safety-relevant. Not for
every rule; a table nobody needed is the same clutter as an unread rule.

---

## Not yet mined

**Re-enumerated 2026-08-13** (counted, not recalled): **61 memory files**, **633 review documents**,
**8 ADRs** (`ls docs/adr | grep -cE '^[0-9]{4}-'` — a bare `ls *.md` says 9 and is wrong, because
`README.md` lives there; the naive count was tried first and produced exactly that error), and
`process-rationale.md`
(323 lines). Apply the two filters above to those, cluster the survivors, and expect **5–8** to make
it — most will fail filter 2, which is the correct outcome, not a disappointing one.

**Do this in a session with fresh context.** Doing it at the end of a long one is precisely the
condition under which recollection substitutes for reading.

---

## Prior art is a research step, not a memory (measured 2026-08-15)

**Cost of not having it: thirteen adversarial review rounds and a design review, rediscovering a
decision that was on disk in three places the whole time.** The failure was not that nobody knew — a
reviewer had *caught* the drift and filed it. It was filed under a heading called **"Carry-forward"**
with no destination id, and nothing carried it.

Three things, in increasing order of what they cost to build:

**1. A carry-forward that names no destination is not a carry-forward. It is a note.**
Free. When you defer something, give it a backlog or task id **in the same turn**. A heading that
says *Carry-forward* manufactures the belief that something is carrying it.

**2. Search the documents before designing against an identifier — and record the search.**
One script. Give it the key constructors, schema fields, and functions whose contract you are
changing; rank hits by document class (ADR › spec › process › review › plan). Put the result in the
spec, **including "searched X, found nothing"** — an unrecorded search is indistinguishable from no
search.

> ⚠ **Default to showing everything.** The first version of this project's tool filtered to
> decision-vocabulary lines and answered *"No hits"* for a term with 80 hits — **a false negative from
> the tool built to prevent false negatives**, caught on first use. Narrowing must be opt-in.

**3. A knowledge graph over document fragments — only with derived edges.**
The ambitious version, and the one with a trap: a hand-maintained graph over hundreds of documents
goes stale silently and is then **worse than grep**, because it looks authoritative. Extract edges a
script can re-derive from scratch (doc→doc, doc→`file:line`, doc→identifier, finding→destination),
and note that the highest-value query is a **dangling edge** — *which deferrals name no destination?*
— not a path. That is the failure above, made mechanically detectable.
