# Portable Practices — what this project learned that a NEW project can use

**This project has two deliverables.** One is the product. The other is a battle-tested harness and
the documents that make it reproducible somewhere else. This file is the second one's index.

**Status: STARTED 2026-08-11, deliberately incomplete.** §1–§7 were measured on 2026-08-11, §8 on
2026-08-12. The great majority of the memory files and review documents have **not** been mined yet —
see *Not yet mined*, whose counts are re-enumerated, not recalled, whenever this file is edited.

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

## Not yet mined

**Re-enumerated 2026-08-13** (counted, not recalled): **61 memory files**, **633 review documents**,
**8 ADRs** (`ls docs/adr | grep -cE '^[0-9]{4}-'` — a bare `ls *.md` says 9 and is wrong, because
`README.md` lives there; the naive count was tried first and produced exactly that error), and
`process-rationale.md`
(323 lines). Apply the two filters above to those, cluster the survivors, and expect **5–8** to make
it — most will fail filter 2, which is the correct outcome, not a disappointing one.

**Do this in a session with fresh context.** Doing it at the end of a long one is precisely the
condition under which recollection substitutes for reading.
