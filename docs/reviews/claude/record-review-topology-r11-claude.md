# record-review-topology — round 11, Claude half

**Subject:** branch `record-review-topology` @ `d9f25d2a` — the merge of `origin/master` (#298) into
the branch, which is the tree that would ship.

**This is the Claude half owed by all ten previous rounds.** r1–r10 each carry
`REVIEW GAP: claude — not invoked; built by a worker fork that cannot spawn subagents`. Those
declarations are honoured, not backfilled: rounds 1–9 reviewed trees that no longer exist, and this
branch's own thesis is that a review of a superseded tree is not a review. Re-running them would
have violated the rule under review. **One whole-branch Claude review against the shipping tree is
the correct discharge**, and it doubles as the Claude half of the r11 that r10 declared owed.

**Method.** Three reviewers with disjoint lenses, dispatched concurrently against the same commit,
adjudicated here by the coordinator:

| Lens | Subject |
|---|---|
| 1 — rule semantics and evadability | `check-review-recorded.py`: what the rule decides, and how to ship past it |
| 2 — producer correctness | `codex-review.py`'s `reviewed_state()` / verdict schema 2: does the record describe what the reviewer was handed? |
| 3 — test falsifiability | are the 77 + 75 cases and the 23-entry manifest able to fail? |

Each was told to read rounds 1–10 first and not re-file what is closed. Where a finding is adjacent
to a closed one, it says which and how it differs. Baselines taken before anything else:
`check-review-recorded.py --self-test` **77/77**, `codex-review.py --self-test` **75/75**,
`check-plan-code.py --self-test` **128/128**.

**Everything marked REPRODUCED was built and run.** Reasoned-only findings say so.

---

## ⚠ An incident, recorded first because it is evidence for H4

While this round was running, lens 2 ran `codex-review.py --self-test` in the worktree with an
ambient `GIT_DIR` / `GIT_WORK_TREE` pointed at that worktree, probing env-var redirection. **The
suite's fixture committed into the real repository**, moving the branch ref `record-review-topology`
off `d9f25d2a` to a scratch fixture commit `"base"` (`ae5641f2`).

Repaired with `git reset --mixed d9f25d2a` — ref and index only, working tree untouched. Verified
after: in sync with `origin`, `git diff d9f25d2a` empty, no stash, no ref containing the scratch
commit, and 128/128 · 77/77 · 75/75 green again. Nothing was lost; `d9f25d2a` was already pushed.

Two things follow, and both belong in the record rather than in a postmortem nobody reads.

1. **It is a live demonstration of H4**, which lens 2 had filed as reasoned-only ("I did not find a
   path in this repo that exports `GIT_DIR`"). One now exists: the suite itself, run by anyone
   probing that variable. A test fixture that can commit into the developer's real repository is not
   a hypothetical.
2. **The coordinator's brief caused it.** It said "never run mutating git in the worktree" and then
   "running `python3 scripts/<guard>.py --self-test` in the worktree is safe and encouraged". Those
   contradict — that suite *is* mutating git. The prohibition named the tool and the escape was a
   wrapper around the same tool. `docs/review-method.md` lists this as hazard 2 and states that none
   of its three hazards is mechanically enforced; this is that sentence being cashed.
   Lens 3 found the sharper version independently: a `cp -R` of a git **worktree** carries a `.git`
   *pointer file*, so "I only mutate copies" is not isolation — deleting that one file is what makes
   a copy safe. Lens 3 re-established every number in its review under that isolation.

---

## Blocking

### B1 — A reverted dirty file is never compared, so the gate certifies content no round saw

`round_tail` only inspects paths that changed between the round's commit and `HEAD`
(`scripts/check-review-recorded.py:244-251`, called at `:391-396`). For a path the reviewer saw as an
uncommitted **overlay**, the version in the round's own commit is not what the reviewer read — so
reverting that overlay leaves the path unchanged since `head`, outside the compared set entirely, and
the round is credited with having seen the final tree.

The keys of `reviewed` are by construction the paths where the reviewer's view differs from `head`'s
tree (`codex-review.py:311-325` stages `read-tree HEAD` + `add -A` and keeps `diff-index --cached
HEAD`). So for every key of `reviewed`, "unchanged since `head`" means **"not what the reviewer
read"** — precisely the case the rule drops.

**REPRODUCED**, end to end in a throwaway repository: commit `C1` adds `lib/x.py` returning `"BAD"`;
the author writes the fix `"GOOD"`, leaves it uncommitted (the documented practice,
`docs/review-method.md:252-254`) and dispatches a round; the fix is then abandoned with
`git checkout -- lib/x.py`; `C2` carries only the review document and the verdict.

```
$ git show HEAD:lib/x.py
def f():
    return "BAD"
$ python3 scripts/check-review-recorded.py --base master --pr-body-file /tmp/body.md
ok — review recorded in this range: docs/reviews/codex/feat-r1-codex.md
ok — the final tree was reviewed by feat-r1-codex.verdict.json
rc=0
```

`lib/x.py` merges as `BAD`. The only round that ran read `GOOD`. The gate prints its strongest green
line and names the round.

**Not r1's finding.** r1's Blocking was *edit it AGAIN and commit* — the path stays in the candidate
set and the entry comparison handles it. This is the opposite move: the path **leaves** the candidate
set, so no comparison happens at all. Confirmed by grepping all ten Codex rounds for
`revert|restore|stash|checkout --`; the only hit is r1 describing the edit-again case.

**Not exotic.** Under the branch's own protocol — hold the round's fixes uncommitted — "the reviewer
said that fix is wrong, so I dropped it" is an ordinary next action. It is also the cheapest
deliberate bypass on the branch: review good code, ship the committed code, exit 0.

---

## High

### H1 — The tail is charged over the BASE's commits too, so CI reds every PR whose base moved

`round_tails` computes its candidate set as a raw `diff(head, HEAD)`, unscoped
(`check-review-recorded.py:387-391`). The two sibling questions both scope to the branch via
`merge-base(base, HEAD)` (`:463-478`, `:481-491`). The tail is the only one that does not, so every
commit the **base** made since the branch forked is charged against this branch's rounds.

In CI this is not a corner case: `HEAD` is GitHub's synthesised PR merge ref — the workflow says so
itself at `.github/workflows/ci.yml:32-34` — so `diff(head_of_round, HEAD)` contains the base's whole
movement **with no merge performed by the author**.

**REPRODUCED** twice. In a scratch repo, a branch that merged nothing went red for `scripts/newguard.py`,
a file master landed on its own reviewed PR. And on this very branch:

```
FAILED — 10 round(s) ran and guarded code was committed after every one of them.
  The closest (record-review-topology-r10-codex.verdict.json) never saw:
    scripts/check-guard-coverage.py, scripts/check-plan-code.py, scripts/codex-review.py,
    scripts/mutations/check-guard-coverage.json, scripts/mutations/check-storage-independence.json
```

Three of those five are `origin/master`'s own files, unchanged by this branch —
`git diff --name-only 31fc8a72 HEAD -- <those three>` is **empty**. The branch is being told to
review PR #298's already-reviewed work.

**Not r9's accepted cost.** r9 accepted that *a branch which must merge master to resolve a conflict
in guarded code owes another round, because the merged result is code no earlier round had seen*.
That is about a **merge result**. Here the files are taken verbatim from the base, with no conflict
and no resolution — and under the PR merge ref it fires with no merge action at all.

**Why High.** It contradicts the stated contract (`docs/review-method.md:258`: *"committed after"* —
the base's commits were not committed on this branch) and it is a livelock: run a round, master
moves, red again, with no author action that reaches green. Backlog #56's measured verdict is that a
guard going red for reasons outside the author's control gets switched off. It fails **closed**, so
it is not Blocking.

**Merge parentage is not considered at all** — established mechanically. Of the seven git invocations
in the file, only two touch the commit graph: `:384` is a *reachability* test (`--is-ancestor`), and
`:387` is a plain two-tree diff. There is no `rev-list`, no `--first-parent`, and no `merge-base`
between the round's `head` and the base. *"This file arrived from upstream"* is not a proposition the
rule can currently form.

### H2 — `NO-REVIEW:` waives the final-tree question silently, and the pass names the wrong basis

`check-review-recorded.py:531`:

```python
    if not guarded_changes(changed) or reason_of(body, NO_REVIEW) is not None:
        return 0
```

`verdict()` has already returned at its review-document branch (`:185-195`), so the `NO-REVIEW:` echo
at `:196-198` never runs — while the docstring at `:179` promises *"the reason is ECHOED so it lands
in the log"*.

**REPRODUCED.** A branch failing `rc=1` on a stale round, given a body containing
`NO-REVIEW: master moved, cannot keep up`, prints:

```
ok — review recorded in this range: docs/reviews/codex/feat2-r1-codex.md
rc=0
```

The words `NO-REVIEW` and the author's reason appear nowhere, and neither does any statement that the
final-tree question was waived. The log names a *review document* — attributing exit 0 to evidence
that did not clear it.

**Why High.** This is r4's High in a new place — *"a review record that over-claims is worse than the
gap it excuses"* — and it does worse than omit its basis: it names a different one. It also compounds
with H1: the livelock's predictable escape is `NO-REVIEW:`, and that escape leaves no trace in the log.

### H3 — The record credits every file that was merely dirty at dispatch, and the gate calls that "the final tree was reviewed"

`reviewed_state()` stages the whole working tree with no scope — `codex-review.py:318` is
`git("add", "-A", env=env)` and the signature at `:264` takes no scope argument. A guarded file that
was uncommitted at dispatch but never in the review's subject is recorded as handed to the reviewer,
and `check-review-recorded.py:292` certifies it with `the final tree was reviewed by …`.

**REPRODUCED.** Scratch repo with two dirty files at dispatch — `lib/subject.py` (the subject) and
`scripts/unrelated.py` (never in any prompt) — then one commit of everything:

```
--- S2  an unrelated dirty file, never in the review's scope, is credited
rc=0
ok — the final tree was reviewed by topic-r1-codex.verdict.json
```

The gap the branch closes is *"a review was recorded"* vs *"the reviewed code is the code that
merges"*. This opens a third: **"was in the tree" vs "was handed"** — and the SCOPE section at
`:52-70`, which honestly enumerates five other limits, does not name it. This round is the worked
example: three reviewers were dispatched with three narrow lenses, and under that topology any
guarded file dirty at dispatch is credited by all three.

Not exotic for the same reason as B1: the practice this branch is built around maximises the dirty
set at dispatch.

**Accepted closure (either):** record the prompt (a digest, or the `--prompt-file` path) in the
verdict so the scope is visible; and/or add the limit to the SCOPE list and weaken `:292` to claim
what it establishes — *"was in the tree handed to …"*.

### H4 — Environment-variable repo redirection is unguarded, in the producer and in the fixture — DEMONSTRATED LIVE

`git -C root` does not mean "the repository at `root`" when `GIT_DIR`, `GIT_WORK_TREE` or
`GIT_COMMON_DIR` is exported. Every git call in `reviewed_state` inherits the full ambient
environment (`codex-review.py:286-292`), and `:310` overrides `GIT_INDEX_FILE` only. r10 closed
config **files**; the env-var door is open.

**REPRODUCED** — two unrelated scratch repos, A asked about, B's `GIT_DIR` exported:

```
honest answer  : ('0db97b95…', {'A-file.py': '100644 69cf25e0…'})
with GIT_DIR=B : ('23c26c81…', {'A-file.py': '100644 69cf25e0…',
                                'B-file.py': '000000 0000000000000000000000000000000000000000'})
```

The record names **B's** commit as what the reviewer was handed and **fabricates a deletion** of
`B-file.py` — and an all-zero entry is the one shape `is_absent` (`check-review-recorded.py:111-114`)
credits without an equality check. Suite effect, against a stable 75/75 baseline:
`GIT_DIR` → 71/75, `GIT_WORK_TREE` → 69/75, `GIT_COMMON_DIR` → 69/75
(`GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES` → 75/75).

**Filed as Medium by lens 2 on the grounds that no path in this repo exports those variables.
Upgraded to High by the coordinator, because during this round one did**: the incident above. The
fixture's `_git` (`:1051-1055`) neutralises `GIT_CONFIG_*` and not the redirection variables, so
running the suite under an exported `GIT_DIR` committed into the real repository and moved a real
branch ref. Lens 3 independently found the same hole from the other side — its P4 mutation removes
`GIT_INDEX_FILE` isolation at `:310` and the suite stays **75/75**.

**Closure:** drop `GIT_DIR` / `GIT_WORK_TREE` / `GIT_COMMON_DIR` from the environment in both
`reviewed_state`'s `git()` and the fixture's `_git`, so `-C root` means root — the same one line r10
already wrote, applied to the other class of input.

### H5 — The git-reading layer has eight decision points, none reachable from any case; two flip a live refusal into a live pass

`round_tails` (`:362-397`), `declared_gap` (`:453-456`) and `main`'s second-question gate (`:531-543`)
hold the rules deciding whether the headline feature runs at all and whose testimony it believes.
**Eight mutations, one at a time, all leave the suite at 77/77**, and no manifest entry touches these
functions — every one of the 23 `before` anchors lands in the pure layer.

Two are live fail-opens, both demonstrated end to end:

**S1** — deleting the `gate_ran` check (`:378-379`) turns a verdict that says *the gate did not run*
into testimony that a round saw the final tree: `EXIT=2 → EXIT=0`, printing
`ok — the final tree was reviewed by x-r1-codex.verdict.json` over a file reading `"gate_ran": false`.

**S6** — `:531-532` rewritten to `if True:` switches off the entire second question — the reason this
branch exists — with the suite green: `EXIT=1 → EXIT=0`. `tail_verdict` and `round_tail` are
exhaustively cased and manifested; the single line that **calls** them is not.

This is the **class** of the r1 Low the file itself records at `:240-242`: *"`guarded_changes` is
CALLED here rather than upstream so this rule … is pure and reachable from a case."* The r1 repair
moved one call out of the gatherer; the gatherer still holds seven more. The brief asked whether the
r10 repair was instance-only — this is the same question one round earlier, and the answer is yes.

*(Lens 3's S8 is listed in its review and is **not** counted here: `round_tail` re-filters anyway, so
it is behaviourally inert.)*

### H6 — Three new rules inside `reviewed_state` survive mutation, two of them regressing earlier rounds' own fixes

| # | `file:line` | Mutation | Suite | What it breaks |
|---|---|---|---|---|
| P2 | `:333-338` | all-zero destinations skipped again | **75/75** | the **r3 Medium** fix verbatim — *"A DELETION IS RECORDED, NOT SKIPPED"* |
| P3 | `:338` | `parts[1]` → `parts[0]` (source mode, not destination) | **75/75** | the producer half of the **r2 Blocking** mode contract |
| P4 | `:310` | `GIT_INDEX_FILE` isolation removed | **75/75** | `review-method.md` hazard 2 — collides with a concurrent agent's `git add` |

The suite is not inert — deleting `git("add","-A")` → 72/75 and dropping the mode → 73/75 — these
three are gaps. P3 is the costly one: for an untracked file the source mode is `000000`, so it would
record `000000 <sha>` for **every newly-added file**, which can never equal the final entry
`100644 <sha>` — the gate would falsely fail any branch that adds a file. The existing case asserts
`re.fullmatch(r"\d{6} [0-9a-f]{40}", …)` (`:1078-1081`), and `000000` matches `\d{6}`, which is why
it survives.

For P2, the *consumer* has four cases pinning the all-zero spelling
(`check-review-recorded.py:677-684`, `:761-762`) and the *producer* has none: two halves of one wire
format, only one end held.

**Scope note, stated rather than hidden.** `codex-review.py` is in `WIDENED_MANIFEST_DEBT`
(`check-ratchet-contract.py:368`), so the absence of a manifest for it is declared pre-existing debt
and is **not** filed. What is filed is narrower: the branch adds new rules and new cases to that
file, and the new cases do not reach three of the new rules.

### H7 — `codex-review.py:1088` is a case that cannot fail

```python
# An UNCHANGED file is not the reviewer's credit to claim.
chk("a file identical to HEAD is not recorded as handed over", "unchanged" in _dirty2, False)
```

The fixture (`:1046-1076`) commits exactly one file `a.txt`, modifies it, and adds untracked `b.txt`.
There is no unchanged file and no path containing `"unchanged"`, so the assertion is `False` for
**every possible implementation** of `reviewed_state`. This is the named defect class exactly: a
world is set up, the setup is asserted, and the decision the case is named after is never reached.

**Measured both ways.** Mutating `reviewed_state` to diff against the empty tree — so every tracked
file is recorded whether it changed or not — leaves the suite at **75/75 (survived)**. With the
fixture repaired (one committed-and-never-touched `unchanged.txt`, assertion pointed at it), the same
mutation gives **74/75, killed via the case that names it**.

The rule is real and correct in the shipped code; it simply has no falsifier.

---

## Medium

### M1 — Three of `reviewed_state`'s four failure exits are indistinguishable from "the tree was clean"

Found **independently by lens 1 and lens 2**, which is the strongest signal in this round.

The docstring states the fail-safe as a `None` head (`codex-review.py:280-283`: *"The cost of failing
is a `None` head, which downstream reads as 'cannot tell' — reported as CANNOT RUN, never as a
pass"*). Only `rev-parse` honours it. Three exits return a **real head with an empty `dirty`**
(`:311-312`, `:320-321`, `:322-323`), byte-identical to a round dispatched against a genuinely clean
tree. The consumer's usability test is head presence, not measurement success (`:380-383`).

**REPRODUCED** both halves — producer, with HEAD's tree object removed so `read-tree` fails, returns
`('cc2afad0…', {})`; and end to end, the careful workflow with that record produces:

```
FAILED — 1 round(s) ran and guarded code was committed after every one of them.
  The closest (topic-r1-codex.verdict.json) never saw:
    lib/x.ts
```

The direction is fail-closed, which is right — but it is a **false accusation indistinguishable from
a true one**, aimed at the author who did the documented careful thing, and neither the verdict nor
the message carries any trace that the measurement failed. `CLAUDE.md`'s rule is that a check which
cannot reach what it measures must say *treat this as NOT RUN*; here it says nothing.

**Closure:** a third state — omit `dirty`, or set it `null`, when the snapshot failed — and have
`round_tails` count that `unusable`, which already routes to exit 2.

### M2 — The r10 repair is instance-only, and reintroduced r10's own defect through a different door

r10 neutralised host git config for the **fixture's** git calls (`:1051-1055`) but not for the
**subject's** (`:310`), and `:1084-1086` now compares the two against each other. A host-level clean
filter therefore turns the suite red for a host policy — precisely what r10 filed — *because of*
r10's fix.

**REPRODUCED** with a global `core.attributesFile` defining `clean = tr a-z A-Z`:
`74/75 passed`, `[FAIL] …and the recorded object id is the one git computes for that content`.
Against a copy with `_env` reverted to the pre-r10 shape, the same config produces no new failure —
before r10 both sides read the same config and agreed.

**Measured which side is right: the subject is.** Under that filter, `reviewed_state` records
`{'c.txt': '100644 6333d309…'}` and the real commit stores `100644 blob 6333d309… c.txt`. **The
decision not to neutralise config inside `reviewed_state` is correct and must stay** — neutralising
it would be the defect. The repair belongs in the case: compute `_lstree` under plain `os.environ`.

This reaches CI: `check-selftest-counts.py:317` runs this suite and fails on a non-zero exit, wired
at `.github/workflows/ci.yml:275`.

### M3 — `changed_paths` / `added_paths` parse `--name-only` without `-z`

Both read `git diff --name-only` and `splitlines()` (`:475-478`, `:487-491`) while `round_tails`
correctly uses `-z` (`:387`). With default `core.quotePath` any non-ASCII path comes back C-quoted:

```
$ git diff --name-only master HEAD
"lib/na\303\257ve.ts"
added_paths sees : ['"docs/reviews/codex/na\\303\\257ve-r1-codex.md"']
review_added()   : []
```

A branch that genuinely adds a review document whose subject name carries an accent is told *"no
review round was recorded"*. Every direction traced fails **closed**, which is why this is Medium. It
is the same defect class r1's Medium #6 fixed in the sibling gatherer — fixed there as an instance,
not searched for as a class. Fix: `-z` plus `split("\0")` in both.

### M4 — `check-review-recorded.py:753` names a scenario its fixture does not contain

The case asserts that a gitlink cannot compare equal to *"a blob with the same sha"*, but `_LS`
(`:735-737`) gives the two entries **different** shas, so it only asserts that entries differing in
both mode and sha differ. Mutation B (`parse_ls_tree` drops the mode, restoring the r2 Blocking)
reds three sibling cases and **not** `:753`. With `_LS` repaired so the gitlink and the blob share
sha `1111…`, the same mutation kills it (`73/77`). Medium rather than High: the underlying property
*is* covered three other ways. Fix is one character range in `_LS`.

### M5 — `check-review-recorded.py` declares no case count and is invisible to `check-selftest-counts.py`

`grep -c check-review-recorded scripts/check-selftest-counts.py` → **0**, on this branch and on
`31fc8a72`. Its `population_errors` (`:255-265`) reports in exactly two directions —
pinned-but-no-longer-declaring, and declaring-but-not-pinned — so a script that has a `--self-test`,
declares no count and is not pinned is reported by **neither**.

Measured: master `31/31`, branch `77/77`. The branch adds 46 cases to a suite whose size nothing
observes, while both its closest siblings are observed — and `codex-review.py` was pinned
*specifically* because docs claimed 35 while the suite ran 51 (`check-selftest-counts.py:126-127`).
This repo has measured that drift at least three times. Pre-existing, filed because this branch is
what makes it material. Fix: `# 77 cases` in the docstring invocation plus the filename in
`POPULATION`.

### M6 — `codex-review.py`'s producer half has no mutation coverage

The branch took `check-review-recorded.py` from 6 to 23 mutations and `codex-review.py` from zero to
zero. The only falsifiers `reviewed_state` has ever had were r10's hand-run scratch mutations,
recorded in prose and not rerunnable by anything. Partly the declared `WIDENED_MANIFEST_DEBT`; noted
because H3, H6 and H7 are all defects a manifest would have caught, and H6's P2/P3 are regressions of
findings earlier rounds already paid for.

---

## Low

- **L1** — `round_tails`'s missing-file branch (`:365-370`) cannot be reached for the reason its
  comment gives: `added_paths` diffs two trees, so a file added and deleted inside the range is
  absent from both and never reported. Harmless (fails closed), but the comment states a scenario the
  code cannot see, and a mutation flipping `unusable += 1` to `continue` would survive.
- **L2** — a quoted `REVIEW GAP:` line can act as a live declaration: `check-review-rounds.py:81-83`
  admits `>` and `#` in its leading class, so a document quoting another branch's declaration
  illustratively is read as this branch's own. Narrow (only bites when no usable round exists) and
  not introduced here. REASONED from the regex.
- **L3** — `VERDICT_SCHEMA` is written (`codex-review.py:250`) and read by nothing; both consumers key
  off `head` presence. Deleting the field changes no test and no gate outcome, while
  `check-review-recorded.py:61-62` claims schema is handled — true today only because schema 1
  happens to lack `head`. A proxy, not a version check. *(r5/r6 deferred schema validation by explicit
  agreement and that is not re-filed; this is the narrower unfalsifiable-constant point.)*
- **L4** — `run_codex` passes no `cwd` (`:553-582`) while `reviewed_state` describes `REPO_ROOT`
  derived from `__file__` (`:284`, `:359`). Nothing asserts the two are the same repository. They
  agree in normal invocation. Not reproduced against a live Codex run.
- **L5** — `check-ratchet-contract.py:337,351` still says `codex-review.py 63/63` and *"Its 63
  cases"*; the suite is 75. The canonical docstring declaration at `codex-review.py:45` **was**
  correctly updated and is verified by running it, so only the prose is stale.
- **L6** — `check-plan-code.py:3018-3020` disagrees with itself inside one sentence: *"559 -> 576 …
  FIVE entries for FOURTEEN behaviours"* over a delta of +17 (the manifest really grew 6 → 23). The
  file explicitly labels these blocks as history and the live assertion is derived and correct.
- **L7** — `check-review-recorded.py:745` also names a scenario absent from its fixture (*"two files
  with identical content"* over differing shas). Unlike M4 the assertion is genuinely falsifiable —
  killed by manifest entry 15 — so this is naming only.

---

## What was checked and found clean

Stated so the pass is not read as wider than it is.

- **Entry comparison itself** — mode-only change, symlink, gitlink/submodule, reviewed deletion,
  file↔symlink, absent-from-both. The r2/r3/r4 repairs hold.
- **All 23 manifest entries KILLED, via the case each names**, every `before` anchor occurring exactly
  once. No entry is `MUTATION_EXEMPT`.
- **The declared totals are genuinely derived** — `EXPECTED_MUTATIONS` parsed with `ast`: 43 keys
  summing to **597**, matching the case; every key compared against its manifest file on disk, no row
  mismatched.
- **The snapshot moment** is taken once at `:665`, before candidate resolution and any run, captured
  by closure. Every subsequent change moves the recorded entry away from the final entry — fail-closed.
- **Ignored files, empty directories, unmerged stages, the `-z` two-field parser, `GIT_INDEX_FILE`
  isolation** — all driven directly and behaving as documented or failing closed.
- **Guarded scope** — `PROSE_DIRS`/`PROSE_FILES` (`:118-143`) is a denylist, so a new top-level path
  is guarded by default; `docs/` searched for executable artefacts that would be wrongly exempt, none
  found.
- **Round selection** — `min(tails.items(), key=…)` (`:293`) is deterministic, and "any round clears
  it" cannot be gamed.
- **Fail-open sweep of every `except` / early return / default in the new code** — unreadable verdict,
  `merge-base`, shallow clone, missing `.git`, `_final_entries` failure, `gate_ran` false: all exit 2
  or fail closed. The genuine fail-opens in this set are M1 and H5.
- **The r10 repair is complete for what r10 named** — the config isolation plus `--no-verify
  --no-gpg-sign` plus the commit-succeeded assertion do close r10's finding. H4 and H6 are different
  holes in the same block, not re-files.
- `check-selftest-counts` 37 scripts verified · `check-fixture-variation` OK, 488 parameters across
  50 files · `check-ratchet-contract` OK · `check-gate-falsifiability` OK.
- **Not re-filed:** r5/r6's deferred schema validation, r10's `_head2 == _head` weakness, and the
  `:665` "no final blob to equal" comment left deliberately unfixed.

**Methodological limitation, stated.** Lens 3 attempted a `trace`-based line-coverage measurement and
it mis-attributed, reporting plainly-executing lines as unreached. It was discarded rather than
reported. Every coverage claim above rests on mutation instead — the stronger evidence anyway.

---

## Adjudication

**B1 and H1 dissolve to one change.** B1 needs the candidate set **widened** by `dirty.keys()`; H1
needs it **intersected** with the branch's own delta (`changed_paths(base)`, already computed in
`main()` at `:513`, so no extra git call). The two compose into one expression, `round_tail` stays
pure, and one new mutation entry covers it. Measured in both directions by lens 1 against a driver
over the module's own functions:

| scenario | shipped rule | scoped rule |
|---|---|---|
| B1, reverted dirty fix | `rc=0` "the final tree was reviewed by …" | `rc=1` "never saw: **lib/x.py**" |
| H1, base moved under a PR merge ref | `rc=1` "never saw: **scripts/newguard.py**" | `rc=0` |
| this branch, live | 5 files named, 3 of them master's | `rc=1`, naming **`check-plan-code.py`, `codex-review.py`** — exactly the two genuinely unreviewed |

**The strongest argument for the current behaviour, and why it loses.** A clean-merge *semantic*
conflict — master changes a signature, the branch changes a caller, both merge cleanly, no file
carries a resolution — is genuinely lost under the scoped rule. Three reasons it still loses: (1) the
shipped rule does not catch it either, it **carpets** it, firing on every upstream pickup so its
output cannot distinguish "master moved" from "your resolution invented code" — this branch's own run
names five files of which three are noise; (2) review is the wrong instrument for "these two changes
do not compose" — `tsc --noEmit` and the unit suite are, and CI already runs both on the same merge
ref; (3) backlog #56 applies exactly, and the escape people will take is `NO-REVIEW:`, which by H2 is
silent. H1 and H2 compound.

**The fix is a hypothesis, not a verified patch** (`docs/review-method.md:246-249`) — the *rule* was
verified, not a patch to the shipped function.

**Ordering.** B1, H1, H2 are one coherent edit to the consumer. H3, H4, H6, H7 and M1, M2 are the
producer and its fixture. H5 and M4, M5 are falsifiability debt that should land with the code it
observes, not after it.

---

VERDICT: **NOT CONVERGED**
