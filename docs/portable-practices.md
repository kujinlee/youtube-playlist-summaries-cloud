# Portable Practices — what this project learned that a NEW project can use

**This project has two deliverables.** One is the product. The other is a battle-tested harness and
the documents that make it reproducible somewhere else. This file is the second one's index.

**Status: STARTED 2026-08-11, deliberately incomplete.** Everything below was measured on 2026-08-11.
The other ~47 memory files and 623 review documents have **not** been mined yet — see *Not yet mined*.

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

---

## Not yet mined

54 memory files (23 tagged as lessons), 623 review documents, 7 ADRs, and `process-rationale.md`
(323 lines). Apply the two filters above to those, cluster the survivors, and expect **5–8** to make
it — most will fail filter 2, which is the correct outcome, not a disappointing one.

**Do this in a session with fresh context.** Doing it at the end of a long one is precisely the
condition under which recollection substitutes for reading.
