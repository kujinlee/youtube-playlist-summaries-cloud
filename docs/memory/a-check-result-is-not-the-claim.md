---
name: a-check-result-is-not-the-claim
description: "FIRES-WHEN: about to quote a green check as evidence, or reading a red one — ⭐⭐ A green check says nothing about the branch BASE (use `origin/master`, READ THE FILE LIST) and a red check is a STOP — I merged on a red I \"recognised\" as fixed and it was hiding a second failure"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `a-green-check-says-nothing-about-the-branch-base`, `a-red-check-is-a-stop`

## a green check says nothing about the branch base

**MEASURED 2026-08-24.** PR #146 (ADR-0010, described as *"Documentation only"*, 3 files) squash-merged
as `329b7f5` carrying **6 files** — the entire content of PR #144 came with it, and #144 had to be
closed as already-merged.

**Cause:** `git checkout -b docs/adr-0010-anchor` was run while sitting on `docs/stable-id-roadmap-findings`
(#144's branch) rather than on `master`. Squash-merge collapses **every** commit on the branch into
one, so the message described the ADR and the commit contained #144 as well.

**Why nothing caught it — this is the part worth keeping.** Every check was green, and *none of them
can see the base*:

| Signal | Said | Could it catch this? |
|---|---|---|
| check-run against the exact head SHA | `success` | no — the head was right |
| `mergeStateStatus` | `CLEAN` | no |
| the diff I reviewed | what I intended | no — I reviewed my own commit, not the range |
| 5 ratchets on the edited tree | all 0 | no — the extra content was *valid* |

**"The right commit passed CI" and "the branch contains only what I claim" are different assertions.**
I had deliberately verified the first — twice, and said so out loud — which made the second feel
covered. It was never tested.

**How to apply — one command, before opening any PR:**

```bash
git log --oneline origin/master..HEAD    # expect EXACTLY the commits you wrote
```

And when starting a branch, cut it explicitly: `git checkout -b <name> origin/master`, never bare
`git checkout -b` from wherever the working tree happens to sit after a force-push.

**Second-order damage is the message, not the code.** Nothing wrong landed (`master − #144's branch`
= exactly the 3 ADR files, ratchets green), but `329b7f5`'s message is permanently silent about three
documents it carries, and pushed `master` history is not rewritten to fix a message. Comments on both
PRs are the record.

---

## ⟳ SECOND INSTANCE, 2026-09-19 — a different cause, the same blindness, and `master` was the liar

On `feature-hub-spec`, about to dispatch the final whole-branch review, `git merge-base master HEAD`
returned `a37a14c1` (PR #321). **The LOCAL `master` ref was two PRs stale**; `origin/master` was
`e693f36a` (PR #322, merged). The review package built from it was **20 commits / 50 files /
581 KB / 8,126 insertions and contained the whole of PR #322** — `fly.worker.toml`,
`worker/main.ts`, `lib/job-queue/worker-wake.ts`, three worker test files. The true branch is
**19 commits / 24 files / 4,347 insertions**.

⭐ **THE PART THAT MAKES THIS WORTH A SECOND ENTRY: the stale ref had already handed me a
REASSURING answer, hours earlier.** I ran `git rev-list --count HEAD..master` → **`0`**, read it as
"not behind master", and reported that to the user. The count was **not wrong about the ref it
read** — it was wrong about the question asked. Unlike 2026-08-24, where every green check was
merely *blind* to the base, here a check actively **answered in the affirmative about the wrong
subject**. That is the more dangerous form, because it feels like verification.

Caught only because the diffstat was implausible: `fly.worker.toml` and `worker/main.ts` have
nothing to do with a docs-and-guards branch. **A number would not have caught it; a filename did.**

**How to apply, in this repo specifically:**
- Compute branch scope against **`origin/master`, never bare `master`** — `git merge-base
  origin/master HEAD`, `git log --oneline origin/master..HEAD`, `git diff --stat origin/master..HEAD`.
- A local ref that no `git fetch` has updated *this session* is not evidence about the remote.
- **Read the FILE LIST of any review package before dispatching it.** A file that has no business
  in this branch is the cheapest possible detector, and it is the one that worked.

Same family as [[a-check-result-is-not-the-claim]] (a CI signal reasoned about instead of read),
[[a-test-that-cannot-fail]], and — for the second instance specifically —
[[a-measurement-is-only-as-good-as-its-corpus]] and
[[measure-the-population-the-code-actually-sees]]: the command was correct, the corpus was not.
Ask of any green check: *what would it look like if the thing I actually care about were wrong?*
Here: identical, both times.

## a red check is a stop

**2026-08-24, PR #134.** `gh pr checks` showed `verify=fail`. I opened the log, recognised the exact
`check-docs` error I had fixed minutes earlier, concluded the run was simply behind, and merged.
**master went red.**

Two distinct errors, and the second is the one that generalises.

**1. "Stale failure" and "real failure" are indistinguishable when the fix lives only in your
working tree.** The run *was* against an older commit — and my fix had never reached the PR: I
pushed it after GitHub had resolved the merge head, so the squash excluded it. The story I told
myself was true about the CI run and silent about whether the repair was in the branch. One command
would have settled it (`gh pr view --json headRefOid`), and I ran it only after the damage.

**2. THE RED CHECK WAS HIDING A SECOND FAILURE.** CI stops at the first failing step, so
`check-arch-findings` had **never run** on that branch. Slice A had pushed three findings *past
baseline* — an inline `STORAGE_BACKEND` read, a 12th `const UUID_RE`, a 9th local/cloud fork, all
with target zero. I only saw it because the follow-up PR got far enough for that step to execute.
**An early failure means every later step reported nothing — not that it passed.**

**How to apply — merge only when all three hold, checked in this order:**
1. `gh pr view N --json headRefOid` **equals** local `HEAD`, and `git status` is clean.
   Re-check after pushing; the first read can lag and that lag is what caused this.
2. A **green run on that exact commit**. Never an explanation of why a red one does not count.
3. If a check is red, read it — then remember the steps *after* it did not run at all.

Related: I ran five ratchets locally and there are **six**; `check-arch-findings` is in
`docs/dev-process.md`'s enforced-checks table and was simply not in my habit. A habit is not a
reading of the table — see [[a-convention-catches-what-you-read]] and
[[a-hang-is-not-a-diagnosis]], which is the same "silent about the adjacent layer" shape in a
different tool.

---

## ⟳ 2026-09-22 — I ran the subject's OWN suite and its sweep, and no other guard that reads it

Folding round 5 of the banner review, I committed `02218390` after running
`check-banner-armed.py --self-test` (150/150) **and** the 912-mutation sweep. Both green.
**`check-fixture-variation.py` was RED on that same file and I never ran it** — measured the next
session: `rc=1` at the branch head, `rc=0` on `master`, so the fold introduced it.

**Why it was invisible:** the fold ADDED direct `flush_line(...)` calls, giving that function its
first call sites in the suite — all four passing the same `when`. The other guard's rule had
something to fail on **for the first time**, created by the very commit that did not run it. A
guard you have never tripped is not in your habit *because* you have never tripped it.

⚠ **The two guards are different rules and neither subsumes the other**, which is why the green one
felt sufficient: `check-fixture-variation` asks *do two CASES pass different values for a
PARAMETER?*; the property the fold was applying asks *does ONE CASE exercise a producer at two
inputs?* See [[exercise-the-producer-at-two-distinct-inputs]].

**How to apply:** before committing a change to any `scripts/` file, run **every guard whose
population includes that file**, not just the file's own suite. Cheap discovery:

```bash
grep -rln "$(basename CHANGED.py)" scripts/*.py scripts/mutations/*.json
```

⭐ And more generally: **a new call site can turn a guard red without changing that guard's rule.**
Adding coverage is a tree change like any other. Same family as [[after-fixing-search-for-the-class]].

---

## ⟳ 2026-09-22 — I ran the gate over the WORKING TREE and CI reads the COMMITTED diff

Merging master into `quiet-stop-observers-wt`, my conflict resolution fused two dashboard entries
under one `## 2026-09-22` header — the conflict region began *after* the shared header line, so
keeping one header meant the branch **added no entry at all**. I ran `check-dashboard-entry.py`
before committing the resolution and it returned **rc=0**. CI returned **REFUSED**.

**Both were right.** The gate reads the committed diff against the base; my run was over a working
tree whose resolution was not yet a commit. *"I ran the gate"* and *"I ran the gate against what CI
will read"* are different claims, and the first is the one that feels like verification.

⚠ **And I captured `rc=$?` after an `echo` twice in the same session**, reporting a gate's exit code
as 0 when it was 1 — including a 35-minute mutation sweep whose log said `NOT MEASURED — treat this
as NOT CHECKED`. A background-task notification's "exit code 0" is the *shell's* status, not the
command's.

**How to apply:**
- **Commit the resolution, THEN run the gate** — or pass the same `--base`/`--pr-body-file` CI does.
- `cmd >out 2>&1; echo "rc=$?"` captures the redirect, not the command; put `rc=$?` on its own line
  immediately after, and **read the log, never the notification**.

---

## ⟳ 2026-09-26 — the PIPELINE form, and the `||` form that CANNOT report absence

The `rc=$?` note above covers a **redirect** (`cmd >out 2>&1`). It does not cover a **pipe**, and a
pipe hit twice in one session, in two different agents, on the same branch.

| what was written | what it reported | why |
|---|---|---|
| `python3 scripts/check-dashboard-entry.py 2>&1 \| tail -4; echo "rc=$?"` | `rc=0` while the text above it said **REFUSED** | `$?` is the LAST stage's status — `tail`'s |
| `grep … \| head -5 \|\| echo "NO REFERENCE"` | nothing, read as *"fine"* | `head` exits 0, so the `\|\|` branch can **never** fire |

⭐ **The second is the worse shape and is a new member of this family: it is not a check that gave the
wrong answer, it is a check STRUCTURALLY INCAPABLE of giving the failing answer.** Its `||` fallback
is dead code. It printed nothing because the thing genuinely was missing — and it would have printed
nothing had it been present. See [[a-test-that-cannot-fail]]: the falsifier was unreachable.

**How to apply:**
- Never read `$?` after a pipe. Either drop the pipe (`cmd > /tmp/out; rc=$?; tail -4 /tmp/out`), or
  use `${PIPESTATUS[0]}`, or `set -o pipefail`.
- ⛔ **Before trusting any `A || echo "MISSING"` guard, ask whether `A` can actually exit non-zero.**
  `grep | head`, `grep | wc -l`, `grep | cut` — all exit 0 regardless. Put `grep -q` alone on the
  left, or compare a count.
- For presence/absence, prefer `grep -c` and read the NUMBER over an exit-code branch.

⚠ **And two of my own verification greps were wrong the same day for a different reason:** a
single-line pattern against text that WRAPS across lines (`"statement about the local figure's
missing provenance"`) and a selector for a class the code does not use (`[class*=float]` where the
element is `.askbtn`). Both reported absence of something present. Related:
[[measure-the-population-the-code-actually-sees]] and [[a-positional-read-needs-a-verified-shape]] —
`tail -n +10` on a 10-line header was off by one and reported a reviewer's testimony as ALTERED.
**Verify a negative result against a known-positive control before reporting it.**

---

## ⟳ 2026-09-26 — I DESTROYED A REVIEW DOCUMENT, and my check could only confirm what I had done

**The most expensive instance in this file, and the cheapest to have prevented.** Cost: the original
`velocity-backfill-r3-claude.md`, 32,331 bytes of review testimony — **unrecoverable**.

**What happened.** `git reset --hard b8a8a828` deliberately discarded the last TWO commits on the
branch. One was the migration; the other had created r3's review document. To restore, I copied back
the files listed by **the migration commit** — 8 of them. r3's review came from the *other* discarded
commit, so it was never restored. PR #348 merged without it, and a later `git gc --prune=now` (run
while proving an archive tag protected a *different* commit) collected the object.

⛔ **THE CHECK THAT PASSED.** Afterwards I asked *"are those 8 files back?"* They were. **That question
can only confirm what I just did; it cannot report what my action removed.** The question that would
have found it — and it is one command — is *what else was on this branch before I discarded those
commits?*

```bash
git diff --name-only <the-commit-you-are-resetting-TO>..<the-old-tip>   # BEFORE reset --hard
```

⭐ **AND IT IS THE SAME SHAPE AS THE FINDING IN THE DOCUMENT I DESTROYED.** r3's own diagnosis of my
earlier work: *"a pointer changes and the repair covers only the sites the previous round named."* Mine:
the restore covered only the files the previous **commit** named. **Both let the previous step decide
how far to look.** See [[after-fixing-search-for-the-class]].

⛔ **AND NO GATE SAW IT.** `check-review-rounds.py` returned rc=0 with *"0 silent gaps"* on the branch
and on master, and never mentioned the subject — it checks whether a round has **both halves**, so a
round whose documents vanish entirely leaves **nothing to check**. I then reported that green tick to
the user as evidence the review was recorded. Accurate and meaningless.

**How to apply:**
- ⛔ **Before any `reset --hard`, `checkout -f`, force-push or branch-ref move: record the old tip and
  diff it against the target.** Restore from THAT list, never from one commit's file list.
- **Tag or note the old tip first** if it is not reachable from another ref — `gc` is not hypothetical;
  mine ran within the hour, by my own hand, for an unrelated reason.
- ⚠ **A green gate over a MISSING artifact is not evidence.** Ask of any passing check: *would this
  still pass if the thing I care about had been deleted?* Here: yes, identically.
- ⭐ **A naming inversion found while repairing it, worth its own line.** I first named the
  reconstruction `…-r3-claude-RECONSTRUCTED.md` so the warning would travel in the filename — correct
  for #177's spec, where the goals-page generator renders nothing *but* the filename. Wrong here:
  `check-review-rounds.parse()` reads filenames by grammar and returns **nothing** for that name,
  `('velocity-backfill', 3, 'claude')` for the plain one. The suffix would have made the round invisible
  to the gate, reproducing the defect being repaired. **The rule is not "label the filename" — it is put
  the label where the READER looks, and identify the reader first.**
