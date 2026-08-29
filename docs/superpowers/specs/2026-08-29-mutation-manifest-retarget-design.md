# Mutation manifest retarget — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** v1 — design approved by the user 2026-08-29, not yet reviewed.
**Closes:** backlog #70. **Related:** backlog #69 (an external observer for declared counts).

---

## 1. What is wrong today

`.github/workflows/ci.yml` runs:

```
python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md \
        --compare . --verify-evidence
```

`--compare` asserts `scripts/gen-dashboard.py` (1,207 lines) and `scripts/check-dashboard-entry.py`
(344) are **byte-identical** to 12 tagged blocks inside a 3,170-line planning document.
`--verify-evidence` asserts a pasted evidence block equals what the tool currently emits.

**So the first bug fixed in either script turns CI red until the identical edit lands in the plan
and its evidence block is regenerated.** That is a planning document holding a permanent veto over
production scripts.

**It is not simply wrong, and that is why it must be superseded rather than switched off.** The
criterion has been defeated twice: v1 (*"run the mutation checks"*) was satisfied by running them
and ignoring the result; v2 read the result but never opened `scripts/`, so round 4 found it passing
over a plan that had drifted from the code — a green verdict over the wrong subject. `--compare`
closed that hole and is sound. What is wrong is the *route*, not the guarantee.

### Measured, 2026-08-29

| | |
|---|---|
| Manifest entries | **43** — 32 on `gen-dashboard.py`, 11 on `check-dashboard-entry.py` |
| Distinct anchored source lines | **45** |
| Lines currently under byte-identity | **1,551** (both files, in full) |
| Other plans in the repo with `<!-- file: -->` blocks | **none** — this tool has one consumer |
| CI already runs the delivered suites? | **yes** — `ci.yml:176` and `:179`, directly |

**The tax, measured over the five commits merged as PR #175 (`96626cd`):** +166 / −14 lines across
the two scripts, in three commits. All three paid the byte-identity tax. **Zero of the 45 mutation
anchors were disturbed.**

## 2. What this changes, and what it deliberately does not

**The guarantee is unchanged:** *the mutation evidence describes the code that ships*. It gets
**stronger** — it will describe the delivered files rather than a copy asserted to match them.

**Residual coupling is NOT eliminated, and this spec does not claim it is.** A mutation anchor is an
exact source string. Wherever the manifest lives, changing the line it names breaks it. The change
is a reduction from **1,551 coupled lines (100%) to 45 (2.8% / 3.2%)**.

That residual is **signal, not friction**, and the distinction is the point:

- today's coupling fires on *unrelated* edits and teaches nothing;
- the residual fires only on a line a guard is asserted against — where being forced to re-confirm
  the guard still guards is the check doing its job.

**Rejected: marker comments** (`# MUT:bar-height` in the source, manifest anchored to markers). It
would shrink the residual further, but it puts test scaffolding into production source to solve a
problem that occurred **zero times** in the only sample available, and it trades a coupling that
fails loudly for one that can silently drift onto the wrong line. YAGNI.

## 3. Design

### 3.1 The manifest moves to data files beside the code

`scripts/mutations/gen-dashboard.json` and `scripts/mutations/check-dashboard-entry.json`, holding
exactly the entries that are in the plan today. **No entry is re-authored** — every one of the 43 was
bought with a review round, and rewriting them would re-earn the defects they encode.

The **manifest filename determines the target script**. Each entry keeps its `file` key, and the
runner **refuses** any entry whose `file` disagrees with the filename. A redundancy that fails
loudly, rather than one that drifts.

### 3.2 The runner mutates the delivered scripts

`scripts/check-plan-code.py` keeps its mutation engine **verbatim** and gains a mode that changes
only *what it mutates*: it copies the delivered `scripts/` tree into a temp directory and mutates
that, instead of a temp copy assembled from the plan.

Everything downstream is untouched, and each piece of it was bought with a round:

- refuses a mutation whose anchor **is not found** (`:347`);
- refuses one whose anchor is **ambiguous** — `src.count(find) > 1`, because `replace(…, 1)` would
  land on the first occurrence and a `caught` verdict would not be about the line named (`:339`);
- reads rc=2 as **CANNOT RUN**, never as a catch (`:374`);
- requires red **via the exactly-named case**, not a substring (`:414`).

⚠ **The whole `scripts/` tree is copied, not the two files.** `gen-dashboard.py` loads
`check-dashboard-entry.py` as a sibling at import time, and generators in this directory resolve a
repo root from their own path. Measured 2026-08-29: three separate hand-run mutation harnesses
reported a **red or meaningless control** on first use for exactly this reason.

**The runner asserts a GREEN CONTROL before applying any mutation** and refuses to report otherwise.
A mutation table without a green control is not evidence.

### 3.3 The evidence block is deleted, not relocated

It exists because a pasted artifact went stale — generated at v4, describing a run two versions old,
which is why `--verify-evidence` had to be built. With no stored copy, **CI's own output is the
evidence and there is nothing to go stale.** This removes a failure mode rather than moving it.

### 3.4 The new hole this opens, and its guard

Once the manifest is a data file, **deleting an entry silently narrows coverage while CI stays
green.** That is backlog #69's class — a guard whose own removal is invisible — and it is the exact
shape found in `CONTRAST_MIN` on 2026-08-29, where one token switched off a whole check at 111/111.

**The runner declares an expected mutation count per manifest and fails when the manifest shrinks.**
Built in from the start, not deferred. The count lives with the runner, so deleting an entry
requires also lowering a number someone will see in review.

### 3.5 The plan's code blocks are deleted

**User decision 2026-08-29.** The 12 `<!-- file: -->` blocks (1,401 lines of duplicated source) are
removed and replaced with pointers to `scripts/`. Once nothing validates them they are guaranteed to
rot, and this project's own rule is that an unread rule is worse than none because it creates a
belief something is covered. The plan keeps its prose — the reasoning, the task breakdown, the
review history — which is the part that was ever worth reading.

### 3.6 CI after the change

| Step | Fate |
|---|---|
| `gen-dashboard.py --self-test` | unchanged |
| `check-dashboard-entry.py --self-test` | unchanged |
| `check-plan-code.py <plan> --compare . --verify-evidence` | **removed** |
| the mutation run against delivered scripts | **added** |

The plan reverts to a Phase-2 record, free to go stale, with no mechanical role.

## 4. How we will know it worked

**Equivalence is demonstrated, not asserted.** Before the old step is removed, both paths run green
**simultaneously**: the plan-based run and the delivered-script run each report **43 mutations,
0 survivors**. Only then does the old step come out.

### Falsifiers — the observation that makes each claim FAIL

| Claim | FAILS IF |
|---|---|
| The runner mutates the code that ships | a mutation is applied while `scripts/gen-dashboard.py` on disk is unchanged, and the run still reports `caught` |
| Every mutation is really applied | an anchor is missing or matches more than once and the run does not refuse |
| A catch is a catch | the suite times out (rc=2) and the run records `caught` |
| Coverage cannot silently narrow | an entry is deleted from a manifest and the run stays green |
| The control is honest | the unmutated copy fails its own suite and the run still reports a mutation table |
| The retarget preserved the guarantee | the delivered-script run reports a different mutation or survivor count than the plan-based run, at the same commit |
| The plan has no mechanical role left | `git rm` the plan and CI goes red |

The last one is the retirement condition stated as an observation, and it is checkable.

## 5. Scope

**In:** the two manifests, the runner mode, the count ratchet, the CI swap, deleting the plan's code
blocks, the equivalence demonstration.

**Out:** backlog #69's external `--self-test` count observer (this spec adds a count ratchet for
*mutations*, which is narrower and does not close #69); marker-comment anchoring; any change to the
43 mutation entries themselves; any change to the two scripts' behaviour.

## 6. Open, and deliberately not settled here

Nothing. Every question raised in design was answered; the two that needed the user
(manifest location, and the fate of the plan's code blocks) were decided 2026-08-29.
