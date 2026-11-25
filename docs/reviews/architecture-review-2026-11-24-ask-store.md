# Architecture review — how an owner ask and its answer are stored and identified

- **Date:** 2026-11-24
- **Convened on:** THRASHING — `check-review-decision.py`: component `store-gate` carried fix-induced findings in
  round 3 and round 4 of the `dashboard-retire-spec` review (and, by the round-3 coordinator's reading, round 2).
- **Subject:** the ask store designed in `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` §2.3,
  §2.3a and §3 (K1–K3, K9, K11), at commit `f63709f3` (branch `dashboard-retire-spec`). Nothing in it is built.
- **Reviewer:** Claude (Fable 5.2), one agent, no second half.
- **Legend:** **[M]** = a command I ran at `f63709f3` (Python 3, git, macOS). **[I]** = inferred, not run.
  **[D]** = documented behaviour of a service I was told not to reach (GitHub), not run.
- **Instruments and raw material:**
  `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/askstore/`
  (`exp.sh` builds eight scratch git repositories and merges them; `proto.py` is a prototype reader that imports
  the REAL `fenced_lines`, `decisions`, `decision_errors`, `parse_entries`, `unresolved` from this tree).
  Nothing in the repository was edited except this file.

---

## 1. Verdict

**Thrashing, and a redesign removes the class. Recommend option (b): one file per ask, with the answer written
into the same file. The existing store is frozen whole and no longer written to.**

| Question | Answer |
|---|---|
| Is it one defect class? | Yes. Every finding in the chain is about a REFERENCE from an answer to an ask inside one shared, ordered file (table in §2) |
| Can a redesign remove it rather than gate it? | Yes. With the answer inside the ask's own file there is no reference to resolve, and with identity = the file path there is no identity to allocate or to move |
| Which checks disappear? | K2, K3, K9 (as an append-only rule over entries), K11 — and with them `key` / `ref` / `dup_key` / `unapplied`, the fail-safe duplicate read and the conditional positional resolve. K10 is already withdrawn |
| Does it contradict a fixed owner decision? | Not one in this review's brief. One wording point for the approval walkthrough — §7 |

## 2. The class, stated once

| Round | Finding | What moved or was ambiguous |
|---|---|---|
| r2 | XM1 — a same-day merge shifts ids; an answer closes the other branch's ask | the ask's identity (an ordinal in a shared file) |
| r3 | B1, M1 — the history walk is vacuous on CI's merge ref, defeated by a later edit | the check that tried to detect the move afterwards |
| r4 | B1 — re-keying a duplicate re-points an existing answer | the identity again, now a hand-chosen key with no allocator |
| r4 | B2 — the repair exception lets an old ask be answered or unflagged in place | the rule that made editing identity "safe" |

Two properties of the store produce all four, and the r4 design (option (a)) keeps both:

1. **An answer is a separate entry that NAMES its ask.** So a name must resolve, resolve to the right entry,
   to an earlier entry, to an ask — K2, K3, and half of K11.
2. **Identity is allocated inside one file that every branch appends to.** Git merges two appends to different
   places without complaint, so uniqueness has to be re-established by a check that runs on a possibly stale
   CI result — K9, the other half of K11, and the fail-safe read for when that check loses the race.

A fix that keeps both properties can only add a detector for the newest way they fail. That is what each fold did.

## 3. Options

### (a) The spec as it stands after the r4 fold

Explicit key on new asks; K9 strict append-only; K11 (four refusal clauses); a duplicate that races onto master
is read fail-safe (both open, the answer `unapplied`, `ref` falls back to `id`); recovery by a positional resolve
permitted only for a duplicated key.

- **Removes the class?** No. It removes the r2 shift for new asks and then spends five mechanisms on the
  consequences of the key having no allocator. Identity is carried twice (`id` and `ref`) across seven consumers
  (spec §2.3a table), one of which the r4 half found missing.
- **State of evidence:** the r4 fold's rules are measured on a scratch parser, K11 itself is a sketch (spec §8),
  and no round has reviewed the fold. **I did not find a new defect in it, and I did not hunt for one** — the
  question here is the count of mechanisms, not a fifth finding.
- **What can still go wrong:** an answered ask REOPENS when a duplicate lands (stated in the spec as the safe
  direction; it is also a NEEDS YOU item the owner already answered); the conditional positional resolve is a
  third way to name an ask; every later change to the grammar has to hold all of this.

### (b) One file per ask — RECOMMENDED

```
docs/asks/2026-11-25-archive-form.md
    # Which archive form do we keep?            <- the question (title)
    One plain sentence.
    **Decide:** which archive form to keep       <- today's Decide grammar, read by decisions()
    - A small record page [recommended]
    - A full frozen render
    ## Answer                                    <- absent = OPEN; present (outside a fence) = answered
    The owner chose the record page. 2026-11-26.
```

Identity is the file's stem. An ask is open while its file has no `## Answer` heading. There is no `[resolved: …]`.

**What git does for free — [M], eight scratch repositories, `exp.sh`:**

| Case | Result |
|---|---|
| two branches add the same path with different questions, merged in either order | `git merge` rc 1, status `AA docs/asks/k.md` — both orders |
| two branches add the same path with identical content | merges clean, ONE file — one ask, which is correct |
| two branches add different asks the same day; one also answers its own | merges clean in sequence; the other ask is the only open one. No id exists to shift |
| two branches answer one ask differently | rc 1, `UU` |
| one branch answers, one deletes the file | rc 1, `UD` |
| a branch writes a new question over an existing path | not an add: `git diff --name-status` says `M` — caught by F1 below, not by git |
| `Foo.md` beside `foo.md` | both sit in the index (what Linux CI sees) — caught by the name-shape rule, not by git |

The duplicate-key race of r4 (two pull requests, each green on stale CI) has no subject: the second one to
merge has a path conflict, and GitHub does not merge a conflicting pull request whatever its check state **[D]**.
The uniqueness check is the merge itself, so it cannot be stale.

**The reader — [M], `proto.py`, about 20 lines, using this tree's real `fenced_lines` and `decision_errors`:**
an open ask, an answered ask, a `## Answer` inside a code fence (still OPEN), an ask with no `**Decide:**` block
(open, with today's decision warning), an empty file and a badly named file (each a named PROBLEM, so the source
is NOT READ, never "nothing waits on you"), and a missing directory (NOT READ).

**Checks that remain, each with its falsifier:**

| # | Check | FAILS IF |
|---|---|---|
| A1 | every file in `docs/asks/` is a readable ask (replaces K1; reads HEAD's tree only, no base) | a file's name is not `YYYY-MM-DD-<lowercase-kebab>.md`, or it has no `# <question>` first line. Conflict markers committed by mistake fail this (the first line is `<<<<<<<`) **[I]** |
| F1 | an existing ask only grows (optional — see the retreat below) | for a file present at the merge base, the base text is not a prefix of HEAD's text, or the file is gone. **[M]** on six cases: gaining an answer and appending a superseding note pass; an edited question, a rewritten answer and a deletion are refused |
| L1 | the old store is frozen | `docs/dashboard-entries.md` differs from a pinned SHA-256 (today `d58f8056c7fea06a…`, 1,721,850 bytes at `f63709f3` **[M]**; re-pinned once, after S2's header edit) |
| K4–K8 | unchanged in purpose | as the spec states them; K4 and K6 run against the new reader |

**Pre-committed retreat for F1.** F1 protects the RECORD of one ask; it protects no other ask, because no ask
depends on another file. If a review round finds a fix-induced defect in F1, the answer is to delete F1 and
accept that an ask's text can be edited (git history keeps the original), not to patch it. It must not become
the next K9.

**Checks and mechanisms deleted relative to (a):**

| Deleted | Why it has no subject |
|---|---|
| K2 — an added reference resolves, to an earlier entry | there are no references |
| K3 — asks and answers only, a resolve targets an ask | the directory holds ask files only (A1); an answer cannot exist apart from its ask |
| K9 — append-only over entries, the `rstrip` rule, the unclosed-fence diagnosis | no shared file is appended to; a fence left open in one ask cannot swallow another ask |
| K11 — all four clauses | the path is the key; git refuses a duplicate |
| `key` / `ref` beside `id`; `dup_key`; `unapplied`; the fail-safe read; the positional resolve for a duplicated key | no duplicate can be merged |
| the `[needs-you: <key>]` grammar extension; "one id per bracket" trap in the skill | no flags, no brackets |
| the S2 entry `[resolved: 2026-08-31/5] [resolved: 2026-09-15/10]` | the old store is not written to again |

**Readers that change:**

| Reader | Change |
|---|---|
| `goal-tree.py` `needs_from_dashboard` (`:1305`) | reads `docs/asks/`; item `ref` = the file stem; question and options from `decisions()` over the file body (spec §2.4 unchanged in intent) |
| `compaction-state.py` `pending_asks` (`:473`) | counts open ask files; "newest" = filename order. It must keep its bounded, regular-file read for EACH file (the hook once hung on a FIFO — its own docstring) **[I]** |
| the `/needs-you` skill | teaches: create a file to ask; add `## Answer` to that file to answer |
| `parse_entries`, `unresolved`, `resolvers`, `cleared_ids`, `header_error`, `FLAG` | no longer on any live path once the page is deleted (S3) — see the migration |

**Migration of the 96 flagged entries: none.** They stay in `docs/dashboard-entries.md`, untouched, as legacy
record. Measured with the real parser at `f63709f3` **[M]**: 591 entries, 71 `needs-you`, 28 resolving,
0 parse errors, **0 open asks**, 2 open heads-ups (`2026-08-31/5`, `2026-09-15/10`). A frozen file with zero
open asks contributes a constant empty list, so no reader has to parse it again. Two conditions make that safe:

- **Cutover assertion:** the slice that freezes the store runs the real `unresolved(parse_entries(store))` one
  last time and FAILS if it is not empty; any ask still open on that day is re-asked as a file first.
  ⚠ The zero is measured on this branch; `origin/master` has added entries since (PR #632 touched the store),
  and the per-PR rule keeps adding them until S2.
- **L1** holds the file still afterwards.

The two open heads-ups stay open in a file nothing displays. That matches the spec's own reason for closing
them ("after S3 nothing would display them") without writing an entry.

**What can still go wrong with (b):**

| Risk | Size |
|---|---|
| `explainer-serve.py` `PAGE_SOURCES` takes FILES only — its own comment records that a directory turned a case red (`:247`–`:250`). The goal-tree page's staleness watch needs a way to see a new ask file | real work, UNVERIFIED how; not a correctness hazard for NEEDS YOU itself, which reads the directory directly |
| a key chosen twice on DIFFERENT days gives two files | harmless: two distinct identities, each answered in its own file |
| an agent resolves an `AA` conflict by taking one side | the other ask is lost from that branch — but it was the OTHER branch's file on master, so F1 refuses the pull request (base file changed) **[I]** |
| path-keyed guards that exempt the old store by path (`check-canonical-source.py:248`, `check-reference-namespace.py:61`, `batch-ci.py:99`) do not know `docs/asks/` | UNVERIFIED; the plan must run every document guard over a sample ask |
| GitHub's refusal to merge a conflicting pull request | **[D]**, not run here |
| the reader forgets a file kind (symlink, directory, oversized file) inside `docs/asks/` | the plan owes cases; each must be a NOT READ problem |

### (c) Others considered

| Option | Verdict |
|---|---|
| asks in the in-flight ledger (`.claude/inflight.jsonl`) | Rejected. The ledger is git-ignored (`.gitignore:199` **[M]**) and lives only in the main checkout: no history, no review, lost on a clone. It is also what the 2026-11-02 spec planned and the owner's O1 set aside (spec *Out of scope*) |
| asks as backlog rows | Rejected. `docs/backlog.md` is again one shared file with hand-allocated row numbers — the same two properties as §2 |
| GitHub issues | Rejected. The repository is public and an ask may be private; the compaction hook must answer offline within its time bound; "cannot reach GitHub" becomes a new NOT READ state on the one list that must not go quiet |
| one file, answer written under the ask's own heading (no references, shared file) | Removes property 1, keeps property 2: two same-key asks inserted at different places still merge clean. (b) dominates it |

## 4. Why (b) is a removal and not a relocation

The test from `docs/review-method.md` is whether the redesign leaves the defect nowhere to live.

- Wrong-ask resolution needs a reference. (b) has none.
- A duplicate identity needs an allocator that can be raced. (b)'s allocator is the tree, and the race is
  decided by the merge, which is atomic.
- A moved identity needs position. (b) has none.

What is left (A1, F1, L1) are single-file shape checks with no cross-entry consequence: a failure of one
cannot change the state of a different ask.

## 5. What this changes in the spec (for the coordinator to fold — the spec is not edited here)

- §2.1 rows 2–3, §2.2, §2.3, §2.3a, §3 K1–K3 / K9 / K11, §5 S2, §7's "coordinator mechanism choice", §8's
  key and duplicate rows: replaced by the file-per-ask design, A1, F1, L1 and the cutover assertion.
- `check-ask-store.py` shrinks to: the fence rule, `exemption_reason` (K7), `decisions` / `decision_errors`,
  the directory reader, A1, F1, L1. `parse_entries` and the ask model leave with the page in S3 rather than
  moving in S1 — **S1 as written (move the model beside the grammar) may no longer be needed**; the ordering
  constraint becomes "the goal tree reads `docs/asks/` and the cutover assertion passes BEFORE the page and
  the old reader are deleted".
- Unchanged: O1's retirement of the page and the per-PR rule, O2, Q1 (the file is kept whole — now strictly,
  by L1), Q2 (`/needs-you`), Q3, K4–K8, §2.4, §4's inventory apart from the rows above.

## 6. Findings that become work (for `docs/backlog.md` — NOT edited here)

| # | Finding | Severity |
|---|---|---|
| W1 | Fold option (b) into the dashboard-retire spec (§5 above) and re-run round 1 on the changed sections | blocks the spec |
| W2 | The goal-tree page's staleness watch cannot name a directory (`PAGE_SOURCES` is files-only); decide how a new ask file marks the page stale | plan item of the same work |
| W3 | Run every document guard over a sample `docs/asks/` file and add path exemptions only where one fires | plan item |
| W4 | The cutover assertion and the L1 pin are sequenced against a store that master is still appending to; the plan states the order | plan item |

## 7. What was decided here that is not written down elsewhere

- **O1's recorded wording** is "KEEP the needs-you / resolved asks in `docs/dashboard-entries.md` as the goal
  tree's NEEDS YOU source". This review was briefed that where NEW asks live is not fixed. Under (b) the
  existing asks are kept in that file and the goal tree's source for new asks is `docs/asks/`. That is a
  mechanism choice inside the brief, but it does move the literal source named in O1, so it belongs on the
  owner's approval walkthrough of the spec, stated in one line — not as a new blocking question.
- **F1 has a pre-committed retreat** (delete it, do not patch it).
- **"Zero open asks" is a cutover precondition, not a standing fact.**
