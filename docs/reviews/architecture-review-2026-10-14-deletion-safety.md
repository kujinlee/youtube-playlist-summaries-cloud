# Architecture review — 2026-10-14 — the mechanism nothing ran, and the four rounds that each fixed it

**Arming condition: THRASHING** — four consecutive rounds whose findings came from the previous
round's own fix, in one component (`dev-process.md` Phase 6). Convened at the owner's approval,
2026-10-14. Subject: `docs/memory/verify-the-other-copy-exists-before-deleting.md` and the
"is it safe to delete this?" mechanism, at `588da838` on `process-281-mechanism-question`.

⚠ **Written per the skill: the deepening candidates at the end are NOT designed here. The owner
picks.** ⚠ And per `review-method.md`'s rule for a thrashing-armed review, the candidate list must
contain the option that **removes the recurring claim itself** — not merely a mechanism-level
alternative. Candidate 1 is that option; candidate 2 is its constructive form.

---

## The recurring claim, named

> **A check shipped in this note establishes, at the moment of deletion, that removing the file
> loses nothing.**

Four spellings, each refuted by the round after the one that wrote it:

| round | the check | how it was false |
|---|---|---|
| r3 | a "reversible proof" | hashes `B` twice and never `A` — **SAFE** over an unrelated or empty `B` |
| r4 | a tracked-state check | `git diff --quiet HEAD` exits 0 on a path matching **nothing**, so an untracked file read as safe |
| r5 | a byte comparison | a failing `git show` emits zero bytes, and `shasum` of nothing equals `shasum` of an empty file (`e3b0c442…` both ways) |
| r5-claude | a blob-id comparison | `git hash-object` applies clean/eol filters without `--no-filters`, so `OBSERVED: HEAD held these exact bytes` printed over bytes HEAD never held — **and a delete then destroyed the only copy** |

⭐ The fourth is the sharpest, because it was produced by the fold that **withdrew the permission**.
The r5 fold correctly concluded that no rule could license a delete, replaced the rule with an
*observation* — and the observation was false on a case the r5 **Codex** half had recorded one
commit earlier under *Checked and found SOUND*.

## The answer, in one line

**The note shipped a mechanism that nothing ever ran, and the project had no word for what kind of
thing it was** — so its only falsifier was a human reading it, and each reading could name just the
instance in front of it.

## The mechanism — two defects that masked each other

### Defect 1 — zero callers. It was advice formatted as executable code.

Measured over the whole tree, excluding `docs/reviews/`, with newline folding and both a
known-positive and a bogus-pattern control:

```
references to the note outside docs/reviews/ : 3
  docs/dashboard-entries.md                  (a DATED entry — a record, not a reader)
  docs/memory/MEMORY.md                      (its index row)
  docs/memory/verify-the-…-deleting.md        (itself)
```

`rev-parse --verify --quiet "HEAD` occurs in **exactly one file in the repository** — the note. No
hook, skill, guard or script reads the fence or depends on it existing.

⛔ **Apply the deletion test.** Delete the fence outright and no complexity reappears anywhere,
because there are no callers for it to reappear in. By the skill's own criterion it was never
earning its keep as a mechanism: *"if complexity vanishes, it was a pass-through."*

⚠ And that is exactly why each refutation cost a round. A **Guard** is falsified by running it; this
was falsified only by a reviewer reading it and constructing a fixture. The interface is the test
surface — and this interface had no test surface at all.

### Defect 2 — the project's vocabulary explicitly excludes it, so no round could name the class.

`CONTEXT.md`'s Verification Stack defines:

> **Guard** — a script that fails when a claim the project makes about itself stops being true.
> **Its subject is this repo, not a user's data.**

The deletion check's subject is *a user's file*. So it is **not** a Guard by the project's own
definition, and no other term in that section covers it: Ratchet, Control, Mutation, Anchor,
Coverage verdict, Testimony and Cannot-run are all about the self-checking machinery.

⭐ **That section exists because of this exact failure, one component over.** It was added
2026-09-03 by Architecture Review #7, whose finding was that *"seven consecutive review rounds had
been argued in words this file did not contain: with no shared terms, each round could only name the
instance in front of it, and the same defect kept recurring in a sibling."* Four rounds here, four
spellings, no shared term — the same cause, in a component that section does not reach.

### The interaction, which is the part no round could have found by probing

A mechanism with **no caller** and **no name** can only be improved one counterexample at a time.
Every round did the locally correct thing: read the fence, construct an input it got wrong, write a
narrower fence. Nothing in that loop can reach the question *"should this file ship a check at
all?"*, because answering it requires a term for the kind of thing the check is — which is Defect 2
— and a way to observe that nothing depends on it — which is Defect 1.

## Why this produced exactly this thrashing shape, measured

The note's growth is the tell, and it is derivable rather than remembered:

| commit | bytes | bash fences |
|---|---:|---:|
| `d3324f86` (before round 1) | 4,724 | — |
| `3f3a78a1` (r2 fold) | 7,840 | 2 |
| `38a22070` (r3 fold) | 8,552 | 2 |
| `26697f70` (r4 fold) | 13,339 | **4** |
| `07b307cf` (r4 Claude fold) | 17,299 | 4 |
| `da8375b7` (r5 fold) | 19,228 | 4 |
| `3cacc805` (r5 Claude fold) | 20,907 | 4 |
| `588da838` (procedure deleted) | 16,240 | 3 |

**11 of the branch's 25 commits touched this one file, and it grew 4.4× while the central rule was
false in every version.** The mechanism doubled — 2 fences to 4 — across exactly the rounds in which
it was being refuted.

## ⭐ The terminating principle was written down at round 2, on this branch, and did not travel

`3f3a78a1`'s message states it:

> *"BOTH OF MY CORRECTIONS OVERSHOT, AND THE REPAIR IS TO STOP ASSERTING RATHER THAN TO ASSERT
> SOMETHING ELSE."*

⚠ **Stated precisely, because the obvious reading is wrong and I checked:** that decision was about
**`review-method.md`**, not this note — round 2 removed a categorical test *there*. My first
hypothesis was that the terminating move had been reached here at round 2 and abandoned; measured,
it was reached in a sibling document and never applied to this one, for three more rounds and three
more assertions.

⭐ This is finding **F2** of the 2026-10-14 canonical-source review recurring in a second component
the same day: *the repo had already solved this and the solution did not travel.* There, the
governing rule sat in `check-explainer-delivery.py`'s docstring and was enforced for skills only.
Here, it sat in a commit message on the same branch.

## Decided here, and written down nowhere before

1. **The demoted procedure is deleted and the four-defect ledger is KEPT** — the owner chose this
   2026-10-14 when asked, against a literal reading of the earlier approval that would have removed
   the ledger too. The reason is load-bearing and belongs in the open: the note's single claim is
   *nothing here makes deleting safe*, and the ledger is the only evidence for it.
2. **`--no-filters` is load-bearing in any `git hash-object` comparison**, and the reason is now
   recorded at the flag rather than in a commit message. It was 0-for-3 across the delivered copies.
3. **A CANNOT RUN can hide a live permit.** The r5 Codex half filed the note's last fence as CANNOT
   RUN over a placeholder path, and so never read the comment beside it — which still licensed `rm`.
   That is a second reason *cannot-run is a failure, never a pass*: not only can it be believed, it
   can conceal.

## Candidates — NOT designed here; the owner picks

**1. ⭐ Ship no check at all** *(this is the option that removes the recurring claim)*
**Files**: `docs/memory/verify-the-other-copy-exists-before-deleting.md`.
**Problem**: the note's claim is false in every version anyone has written, and the thing making the
claim has no caller, so nothing but a review round can falsify it.
**Solution**: the note keeps the incident, the four-defect ledger, the generalisation, and *if you
cannot afford to lose it, `mv` it aside* — and offers no executable fence.
**Benefits**: the recurring claim cannot recur, because nothing asserts it. **Locality**: the lesson
lives in one place with no mechanism to drift from it. Zero callers means zero migration cost.
**Cost**: a reader wanting to check a specific file gets no tool, only the advice.

**2. Make moving-aside the only sanctioned operation** *(the constructive form of 1)*
**Files**: the note; plus whatever runs it — precedent exists in the Codex wrapper's `quarantine()`
and `watched_dirs`, which already **move** a file out of the way rather than deleting it.
**Problem**: the question *"is it safe to delete?"* has no sound answer, because every check observes
an instant and the `rm` destroys the interval after it.
**Solution**: replace the question. Nothing sanctioned deletes; the sanctioned operation moves to a
scratch location, and reclaiming space is a separate, later, deliberate act.
**Benefits**: **leverage** — one operation with no false-permit mode replaces four refuted checks.
The repo already has an adapter for this shape, so this is a second adapter at an existing **seam**
rather than a new invention. **Cost**: scratch space accumulates, and nothing here reaps it.

**3. Name the thing in `CONTEXT.md`** *(removes the cause of instance-naming, not the claim)*
**Files**: `CONTEXT.md`.
**Problem**: Defect 2 — a check whose subject is a user's file has no term, so each round could name
only its instance.
**Solution**: add the term, with the Guard contrast explicit.
**Benefits**: exactly what Architecture Review #7 bought for the Verification Stack. **Cost**: it is
vocabulary, not a mechanism; on its own it would not have stopped any of the four rounds.

**4. Promote it to a real Guard, with a `--self-test`, a falsifier and mutation coverage**
**Files**: a new `scripts/`, its mutation manifest, a `ci.yml` step.
**Problem**: the four prose versions had no control, no mutation and no caller — the machinery every
other checking thing in this repo is subject to.
**Benefits**: it becomes falsifiable by running it instead of by reading it.
⛔ **Contradicts `CONTEXT.md`'s Guard definition** — *"its subject is this repo, not a user's data"* —
so picking this one means resolving that first, which is why it is listed last rather than omitted.

---

## Falsifiers

* **Defect 1 is false if** any hook, skill, script or guard reads the note's fence. Measured: 3
  references outside `docs/reviews/`, all of them records rather than readers; `rev-parse --verify
  --quiet "HEAD` occurs in one file. Known-positive and bogus-pattern controls both behaved.
* **Defect 2 is false if** a `CONTEXT.md` term covers a check over a user's file. Measured: the Guard
  entry excludes it in its own words.
* **The growth claim is false if** the byte counts or fence counts differ from the table. Both are
  derived from `git show <commit>:<path>`, per commit, not recalled.
* **The round-2 claim is false if** `3f3a78a1` removed a categorical test from *this note*. Measured:
  it removed one from `review-method.md`; the note carried 2 fences before and after.

## Not measured — treat each as NOT RUN

* Whether candidate 2's scratch location would be reaped by anything. Nothing here reaps one.
* Whether a Guard-shaped version (candidate 4) could be made sound at all — the interval between
  observation and `rm` is why four checks failed, and no candidate here is designed.
* The explore pass dispatched for this review had not reported when this document was written; its
  map of sibling sites may add members to Defect 1's population. The counts above are my own.
