# PR #367 round 2 — Claude half

**NOT CONVERGED.** The deliverable carries **1 High** (no Blocking). 4 Medium, 3 Low.

Subject: `git diff 2780b05a..HEAD` plus the uncommitted corrections (`git diff --cached`).
Mandate: refute, not confirm. Every claim below names the command that produced it; anything I did
not run is labelled so and appears under *What I could not check*.

⛔ **The merge plan's premise is false.** The new dashboard entry says *"It came back with no
blocking or high issues, which is why this branch can merge."* There is a High, it is in a guarded
file, and the filing rule being cited as the authority for merging says in its own second sentence
*"Only Blocking or High in the deliverable is folded mid-review."* Details in **Is the merge plan
sound?** below. The mechanical half of the plan — that the staged corrections are prose and do not
re-open `check-review-recorded` — **is correct**, and I verified it through the gate's own code.

| Severity | Count |
|---|---|
| Blocking | 0 |
| High | 1 |
| Medium | 4 |
| Low | 3 |

---

## High

### H1 — The docstring asserts the claim r1 graded HIGH *and* its own refutation, and the commit that fixed r1's H1 is the commit that wrote the false half

**Claim under attack:** that r1's H1 ("the 0.142.5 cache no longer exists to compare against" is
false, named in three places) was fixed.

**Location:** `scripts/codex-frontier-model.py:83-85` — in the deliverable, in a guarded file.

**The text as it stands at HEAD:**

```
    offered seven listed models where it had had none. ⚠ **THAT IS AN ASSOCIATION, NOT A PROVEN
    SERVER-SIDE CAUSE** — round 1 Codex Medium 3 again: the 0.142.5 cache no longer exists to
    compare against, so "the server keys its answer to `client_version`" is the best explanation
    available and not something measured here. What IS measured is the before/after pair itself.
```

Ten lines below, in the same docstring:

```
    ⚠ AN EARLIER DRAFT SAID THE 0.142.5 CACHE "no longer exists to compare against" AND THAT WAS
    FALSE — round 1 Claude HIGH.
```

**Ran — the file is on disk and I read it, in this session:**

```
$ python3 -c "...json.load(open('~/.codex/models_cache.json.bak-2026-10-07'))..."
exists: True
client_version: 0.142.5
models: 2
visibilities: ['hide']
any gpt-6*: []
slugs: ['gpt-5.5', 'codex-auto-review']
```

**Ran — which commit introduced each half:**

```
$ git log --oneline -S"no longer exists to compare against" -- scripts/codex-frontier-model.py
879ba8a5 The fix for a false "nothing is watching" warning re-manufactured it in six of seven worktrees

$ git show 879ba8a5 -- scripts/codex-frontier-model.py | grep -n "^+.*\(ASSOCIATION\|no longer exists\)"
149:+    offered seven listed models where it had had none. ⚠ **THAT IS AN ASSOCIATION, NOT A PROVEN
150:+    SERVER-SIDE CAUSE** — round 1 Codex Medium 3 again: the 0.142.5 cache no longer exists to
159:+    ⚠ AN EARLIER DRAFT SAID THE 0.142.5 CACHE "no longer exists to compare against" AND THAT WAS
```

Both lines carry `+` in the **same hunk of the same commit** (`@@ -60,18 +78,26 @@`). At `2780b05a`
that paragraph did not exist in this docstring at all.

**Why this refutes, in four steps:**

1. r1's Claude half graded this exact clause **H1** and named its three sites, the **first** being
   `scripts/codex-frontier-model.py` (`docs/reviews/claude/ci-watch-checkrun-shape-r1-claude.md:94`).
   Two of the three were fixed. The one in the file that H1 listed first was not.
2. `879ba8a5`'s own commit message says: *"HIGH — 'the 0.142.5 cache no longer exists to compare
   against' was FALSE, in three places, as the stated reason for downgrading a claim."* The same
   commit then wrote a fourth instance, as the stated reason for downgrading the same claim.
3. The docstring now asserts **P and ¬P**. A reader going top-to-bottom is told the cache cannot be
   compared against, then that the before half is on disk, then that the first statement was "an
   earlier draft" — which it is not: it is the text ten lines above, from the same commit.
4. This is `docs/process-checklists.md:500` rule 2 exactly — *"An appended correction is not a fix.
   The reader meets the wrong sentence first and may stop there."* `docs/process-rationale.md:1010`
   handled the same correction **correctly**, by marking the bullet at the point of the claim. The
   script did not get the same treatment.

**Severity.** High, by this repository's own grading of the identical claim one round earlier. It
is a comment rather than behaviour, which is why it is not Blocking; it is in a guarded file in the
deliverable, which is why it is not a Medium. ⚠ **The Codex half of round 2 reviewed
`2780b05a..93e3133a`, which contains `879ba8a5`, and did not find it.**

**Fix:** delete the false clause at `:84-85` and keep the premise that survives — *Codex's own
wording was "unverifiable from the current cache"; the remaining honest gap is that `client_version`
is the likeliest, not the only, thing that changed in those eleven minutes* — which is what
`process-rationale.md:1012-1015` already says. Then the paragraph at `:93` has a real antecedent.

---

## Medium

### M1 — The merge decision rests on "no Blocking, no High", which H1 falsifies, and on a rule that says a High must be folded

**Claim under attack:** `docs/dashboard-entries.md` (staged) — *"It came back with no blocking or
high issues, which is why this branch can merge"*, and the three rows' *"FILED NOT FOLDED under the
filing rule."*

**Ran** — the filing rule, verbatim, from the only document that defines it
(`docs/explainers/2026-10-06-brief-dev-process-speed.html` §9, rule 1):

```
1 · The filing rule
A finding aimed at the instrument and below High is recorded as a backlog row, not fixed in
the PR that found it. Only Blocking or High in the deliverable is folded mid-review.
```

Rule 2 (the freeze rule) repeats the carve-out: *"findings are filed rather than fixed **unless
Blocking or High in the deliverable**."*

**Why it refutes.** H1 is in the deliverable. By the rule cited as the authority for filing, it is
folded, not filed — so the conclusion does not follow from its own premise, and the premise is
false independently. This is not a disagreement with the filing rule; it is the filing rule applied.

⚠ **There is no free path, and it should be said plainly rather than discovered later.** The fix for
H1 edits `scripts/codex-frontier-model.py`, which is guarded (measured below), so committing it
after `93e3133a` makes the r2 verdict's tail non-empty and obliges **round 3**. The choice is
between round 3 and merging NOT CONVERGED with a High — not between round 3 and merging clean.

### M2 — #253's severity rationale is false in the half that matters: the race does not add noise, it deletes the warning

**Claim under attack:** `docs/backlog.md:268` — *"The window is narrow and the hook is non-blocking,
so a traceback here is noise rather than a stopped gate — which is why this is 🟠 and not higher."*

**The non-blocking half is TRUE.** Verified at `.claude/hooks/block-idle-stop.sh:149-163`: any
non-zero from `--decide` collapses to hook `exit 1`, documented at `:29-31` as *"allows the stop,
shows stderr, does not block."* Nothing is blocked.

**The "noise" half is false.** Ran — same probe as Codex's, but **with a control**, and with a
pending check and HEAD un-armed so a real warning is at stake:

```
CONTROL (no race): rc=1
CONTROL (no race): WARNING TEXT THE HUMAN SEES ->
⚠ CI is running on aaaaaaaa and nothing is watching it — 1 pending: verify
  (a watcher is armed for bbbbbbbb, but HEAD is now aaaaaaaa — a new push un-arms it BY DESIGN, so that one no longer covers this commit)
----------------------------------------------------------------------
RACE    (concurrent --clear): RAISED FileNotFoundError: [Errno 2] No such file or directory: '…/ci-watching.d/bbbb…'
RACE    (concurrent --clear): WARNING TEXT THE HUMAN SEES -> ''
```

**Why it refutes.** The crash happens at `scripts/check-ci-watched.py:512-513`, **before** `decide`
is called at `:516`, so the output is not a traceback *plus* the warning — it is a traceback
*instead of* the warning. The reader loses the one line this entire PR exists to deliver, and the
`observer_log` write at `:553` never happens, so the false-alarm log that `:551` calls *"the
justification for warn-only mode"* silently loses the entry too.

The marker 🟠 is defensible. The **reason given for it is not**, and it is the reason a future
triager will read: "noise" invites deferral, "the warning is suppressed in the exact situation it
exists for" does not. The repo has measured this failure costing **43 minutes blind on a red CI**.

### M3 — #253's stated fix is an instance fix; the sibling needs no race at all

**Claim under attack:** `docs/backlog.md:268` — *"The fix is small: tolerate a vanished record when
building the mtime key."*

**Ran** — seven probes against the read path, each with the sentinel in a different state:

```
[SENTINEL is a FILE]              rc=1  ⚠ CI is running on aaaaaaaa and nothing is watching it…
[record name not a sha]           rc=1  ⚠ CI is running on aaaaaaaa and nothing is watching it…
[record name '..weird']           rc=1  ⚠ CI is running on aaaaaaaa and nothing is watching it…
[a subdirectory inside sentinel]  rc=1  ⚠ CI is running on aaaaaaaa and nothing is watching it…
[empty sentinel dir]              rc=1  ⚠ CI is running on aaaaaaaa and nothing is watching it…
[dangling symlink record]         rc=1  ⚠ CI is running on aaaaaaaa and nothing is watching it…
[directory unreadable (0o000)]    *** RAISED PermissionError: [Errno 13] Permission denied: '…/ci-watching.d'
```

**Why it refutes.** Five of the six benign states degrade correctly (this also independently
confirms Codex's "a file at `SENTINEL` degraded to WARN"). The seventh raises from
`SENTINEL.iterdir()` itself at `:512` — **outside** the mtime key — so a `try/except
FileNotFoundError` around `q.stat()` leaves it live. It is also **deterministic**, not a window.

The class is *"the sentinel read path has no exception barrier"*, and it has at least two members
(`iterdir` raising, `stat` raising). This is the repo's own *after fixing, SEARCH for the class*
lesson: #253 as written closes one member and reads as closing the subject.

### M4 — The rule that authorises the whole merge plan is not in the repository

**Claim under attack:** three backlog rows (`:268`, `:269`, `:270`) each cite *"the filing rule"* as
their authority; the dashboard entry cites *"rule 5 (withdrawal)"*, *"rule 4 (provenance)"* and
*"the filing rule, adopted today"*.

**Ran:**

```
$ grep -rn -i "withdrawal rule|### 5 ·|rule 5|filing rule" docs/ --include=*.md --include=*.html
  (excluding docs/reviews/) -> only the two documents written tonight: docs/dashboard-entries.md
  and docs/backlog.md rows 253-255. No definition anywhere.

$ ls docs/explainers/*speed*            # this worktree
ls: docs/explainers/*speed*: No such file or directory

$ git -C <main worktree> status --short docs/explainers/
?? docs/explainers/2026-10-06-brief-dev-process-speed.html
```

The rules **are** defined — in that HTML page, §9 — but the page is **untracked**, absent from this
worktree, and its own heading frames them as *"Six rules you could paste into dev-process.md"*,
i.e. a proposal. The rows present them as adopted policy and will outlive the page; a reader who
follows the citation into `docs/process-checklists.md` finds rule 1 is about numbers, rule 4 is
*"Derive gate lists from the WORKFLOWS"*, and there is **no rule 5**.

**Why it matters rather than being pedantry.** The repo's standard is *"Name and define every
reference"*, and the house test for a gate is *state the observation that would make it FAIL*. Three
rows and one merge decision rest on an authority nothing in the repository holds. The repair is one
commit: paste rules 1, 2, 5 and the second-spelling rule into `docs/process-checklists.md` beside
rules 1b–4, and cite the section rather than the page.

---

## Low

### L1 — The anchor-count correction introduces a broken bold marker, measured through the page's own renderer

`docs/backlog.md:267` reads `****1,416 anchors across 59 manifests at \`93e3133a\`**` — four
asterisks opening, two closing.

**Ran** `page_markup.render_inline`, the exact function `scripts/gen-backlog-page.py:827` calls:

```
RENDERED: … repository: *<strong>*1,416 anchors across 59 manifests at <code>93e3133a</code></strong>. …
CONTROL : … repository: <strong>1,416 anchors across 59 manifests at <code>93e3133a</code></strong>. ok
```

The rendered backlog page will show a literal `**` before the number. `python3 scripts/check-docs.py`
returns **rc=0** over it (`Documentation integrity OK`), so nothing mechanical catches it. The live
page at `~/explainers/backlog-table.html` is dated Oct 6 and predates the row, so the defect is in
the source, not yet on the page.

### L2 — #255's rationale names a caller that does not exist, and it has an unnamed sibling that is worse

**Claim under attack:** `docs/backlog.md:270` — *"a caller checking rc believes the sentinel is
cleared."*

**Ran:**

```
$ grep -rn -- "--clear" --include=*.sh --include=*.py --include=*.md --include=*.yml . | grep -i ci-watched
scripts/check-ci-watched.py:41     (the module docstring, for a human to type)
scripts/check-ci-watched.py:986    rc = main(["--clear"], None)        (the self-test)
docs/backlog.md:268,270            (the rows themselves)
```

There is **no non-test caller**. The property #255 states is real and its `FAILS IF` line is sound;
the consequence it offers as the reason to care is hypothetical, which is the shape this repo calls
*a cost-benefit finding whose denominator is empty*.

**The sibling it does not name, measured:**

```
A unreadable HEAD, no legacy:  rc= 0  stdout= nothing to clear for ?    record remains= True
B unreadable HEAD + legacy:    rc= 0  stdout= cleared ci-watching.d/?   record remains= True
```

In case B (`scripts/check-ci-watched.py:1148-1153`) the legacy pre-directory file is removed, `gone`
becomes `True`, and the command prints **`cleared ci-watching.d/?`** — it reports clearing a record
for a head it could not identify, while this head's record is still there. That is a false success
line, which is strictly worse than #255's honest `nothing to clear for ?` plus a wrong exit code.

### L3 — "the provenance rule **now** in `process-checklists.md`" implies an addition that did not happen

`docs/backlog.md:267` (new text). The rule is there — `docs/process-checklists.md:454-465`, rule 1,
which calls itself *"about **provenance** — whether the number is true"* and says *"Cite the symbol
or the command, not the recollection."* So the citation resolves and the claim is substantially
right. But `docs/process-checklists.md` is **unchanged** in `2780b05a..HEAD` (it does not appear in
`git diff --stat`), so "now" is wrong: the rule has been there since 2026-09-24 and this work did
not add it. Rule 1's own standard applied to a sentence about rule 1.

---

## Where the Codex half is wrong or overstated

1. **Low 1 understates itself.** Codex says the 1,414 figure *"belongs to the pre-fold tree"* and
   that *"the two added mutations increase the count"* — i.e. made stale by a later change. Derived
   by the harness's own rule (`load_manifests` globs `scripts/mutations/*.json`; an anchor is
   `edits[i][0]`, `check-plan-code.py:1513`):

   ```
   2780b05a: manifests_loaded=59  anchors=1414
   879ba8a5: manifests_loaded=59  anchors=1416
   93e3133a: manifests_loaded=59  anchors=1416
   WORKTREE: manifests_loaded=59  anchors=1416
   ```

   `docs/dashboard-entries.md:14388` was written **in `879ba8a5`** (`git blame`), where the count was
   **already 1,416**. So the sentence *"whole-population pass now 1,414 anchors / 59 manifests, 0
   unbound"* was **false at its own commit**, not made stale afterwards. Same for `:14451`, written
   in `93e3133a`.
2. **Low 1's location list is incomplete.** Codex named `docs/backlog.md:267` and
   `docs/dashboard-entries.md:14388`. There is a third: `:14451`, in the `93e3133a` entry's table
   row for #252. ⚠ **This is NOT a finding against the fold** — `docs/process-checklists.md:507`
   makes `docs/dashboard-entries.md` an explicit append-only exception where *"a correction is
   required to be a new entry"*, and the new entry records it. Leaving both standing is the
   sanctioned handling. But r2 Medium 3's own lesson is *enumerate every site*, and the Codex half
   enumerated two of three.
3. **Medium 3's quotation is exact — confirmed, not assumed.** Fetched the vendor source live:
   `openai_models.rs:287` reads `/// Visibility of a model in the picker or APIs.` The corrected
   `docs/plugins.md:142-144` quotes it verbatim and the surrounding sentence makes no claim about
   what the field means. **Correction (a) is sound.** (The page adds bold to *"or APIs"* that the
   source does not have; it is emphasis, not alteration.)
4. **Medium 2 is correct and its proposed repair works.** Ran `refusal_message` against three caches:

   ```
   A mixed (the r2 witness):  usable=[]  any list-visible=True   claims 'none is listed'=True   -> FALSE DIAGNOSIS
   B real 0.142.5:            usable=[]  any list-visible=False  claims 'none is listed'=True   -> consistent
   C listed, bad priority:    usable=[]  any list-visible=True   claims 'none is listed'=False  -> consistent
   ```

   #254's repair (branch on whether any model is `list`-visible) suppresses the line in A and
   preserves it in B. ⚠ It is complete **only** because of the row's second clause (*"name the
   predicate that actually failed"*): the first clause alone leaves case A with the near-miss list
   and no diagnosis at all, because `elif models:` cannot fire while `near` is non-empty.
5. **The coverage claim reproduces exactly.** Built a pruned copy (all six `HARNESS_TREE` paths:
   `scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`, `.github/workflows`),
   kept only the two subject manifests, reduced `EXPECTED_MUTATIONS` in the copy to
   `{check-ci-watched: 37, codex-frontier-model: 7}`:

   ```
   OK — delivered scripts mutated: 2 file(s), 44 mutation(s), 44 killed, 44 attributed to the
   case each names, 0 survivor(s) — measured over the WHOLE manifest      rc=0
   ```

   37 + 7 = 44 also matches the manifests' own entry counts, so the declared total is derived, not
   asserted.
6. **The honest gap Codex declares is real and I did not close it either.** *"48/48 document guards
   remains unverified."* See *What I could not check*.

### Candidate findings I could NOT sustain, stated so they are not re-derived

* **`relevant_arm` handed a name whose file was just deleted** — not a defect. It is pure
  (`:299-309`), takes `list[str]`, and returns a sha string. `decide`'s verdict stays correct
  (nothing covers HEAD, so WARN is right); only the sha named in the explanatory parenthetical is
  stale by one record. Probed at four inputs: `([], HEAD) -> None`, `(['b'*40], None) -> 'b'*40`,
  `([], None) -> None`, `(['x','y'], 'x') -> 'x'`.
* **Two processes arming the same sha simultaneously** — the record is named after the sha and
  rewritten with the same content, so the second write is idempotent. Codex's "concurrent arms
  preserved both files" is the different case (two shas) and also held.
* **Non-sha record names / subdirectories / dangling symlinks / `SENTINEL` as a file** — all degrade
  to WARN, no crash. Measured above.
* **`docs/dashboard-entries.md:14388` and `:14451` left uncorrected** — sanctioned by the
  append-only exception at `process-checklists.md:507`. Not a finding.

---

## Is the merge plan sound?

### The mechanical half — YES, and I verified it through the gate's own code, not its description

Loaded `scripts/check-review-recorded.py` as a module and classified every staged path through the
real `is_prose`:

```
STAGED FILES AND CLASSIFICATION (is_prose):
  True   docs/backlog.md
  True   docs/dashboard-entries.md
  True   docs/plugins.md
  True   docs/reviews/codex/ci-watch-checkrun-shape-r2-codex.md
  True   docs/reviews/verdicts/ci-watch-checkrun-shape-r2-codex.verdict.json
guarded_changes(staged) = []

PROSE_DIRS       = ('docs/',)
PROSE_FILES      = ('README.md', 'CLAUDE.md', 'AGENTS.md', 'CONTEXT.md', '.gitignore')
CODE_UNDER_PROSE = ('docs/superpowers/specs/2026-08-03-stable-blob-addressing/',
                    'docs/superpowers/specs/m4/')
```

No staged path is guarded. `is_prose` reaches `PROSE_DIRS` for all five (none is under
`CODE_UNDER_PROSE`, so the `.md`-only carve-out at `:214-215` is not in play). **The claim in the
dashboard entry — `PROSE_DIRS = ("docs/",)`, so the corrections do not re-open the gate — is
correct.**

And the tail, which is the mechanism that actually forced round 2:

```
paths after 93e3133a (committed + staged): docs/backlog.md, docs/dashboard-entries.md,
  docs/plugins.md, docs/reviews/codex/…-r2-codex.md, docs/reviews/verdicts/…-r2-codex.verdict.json
GUARDED among them -> []

diff_argv("<head>") = ['diff', '--name-only', '-z', '--no-renames', '<head>', 'HEAD']
```

`round_tails` (`:1051-1095`) filters candidates through `guarded_changes`, `diff_argv` compares
`verdict-head..HEAD` with **no** working-tree component, and `tail_verdict` (`:915-953`) passes when
**any** round's tail is empty. Simulated with the real function:

```
SIMULATED POST-COMMIT tail_verdict rc= 0
the final tree was in the tree handed to ci-watch-checkrun-shape-r2-codex.verdict.json
```

So the reasoning is right in both directions: a docs-only commit keeps the r2 tail empty, and
folding any of #253/#254/#255 — all of which touch `scripts/` — would make it non-empty and oblige
round 3.

### Does round 2 clear the gate? NOT YET, and this is the plainest thing I can tell you

```
$ python3 scripts/check-review-recorded.py --base origin/master
FAILED — 1 round(s) ran and guarded code was committed after every one of them.
  The closest (ci-watch-checkrun-shape-r1-codex.verdict.json) never saw:
    scripts/check-ci-watched.py, scripts/check-plan-code.py, scripts/codex-frontier-model.py,
    scripts/mutations/check-ci-watched.json, scripts/mutations/codex-frontier-model.json
RC=1
```

It counts **one** round, not two: `branch_verdicts` reads verdicts this branch **ADDED** to the
range, and the r2 verdict is **staged, not committed**. This resolves on commit — the simulation
above is the proof — but until the r2 verdict and both review documents are committed, the gate is
red and the branch is not mergeable.

```
$ python3 scripts/check-review-rounds.py
✗ ci-watch-checkrun-shape round 2: only codex — claude neither ran nor recorded a `REVIEW GAP:` line   rc=1
```

Also expected, and resolved by this document existing.

### The judgement half — NO

The corrections themselves have been read by **no reviewer but me**. Codex's subject was
`2780b05a..93e3133a`; the `plugins.md` and `backlog.md` corrections and rows #253–#255 are newer
than its head. That is the third consecutive round in which the highest-severity finding sits in a
correction: r1's Blocking and both Highs, r2's Medium 3 and Low 1, and now H1 — which was *written
by the commit that fixed r1's H1*. The pattern is not that corrections are risky; it is that the
round that clears the merge never sees them.

**Recommendation.** Fold H1 (one clause deleted from a docstring), keep #253–#255 filed with their
rationales amended per M2/M3/L2, add the four unwritten rules to `process-checklists.md` per M4, fix
L1's asterisks, and run round 3 against the result. Round 3's subject is small — a docstring clause,
three row bodies, one markdown marker, and a checklist section — so it is cheap, and it is the only
path that does not merge a High.

---

## What I could not check

* **`48/48` document guards.** Codex declared this unverified after two 45-second timeouts; I did
  not close it either. I ran four of them individually — `check-docs.py` **rc=0**,
  `check-dashboard-entry.py` **rc=0** (*"an entry block was added"*), `check-anchors.py` **rc=0**
  (*"13 registered, all claimed; floor 22 held"*), `check-selftest-counts.py` **rc=0** (*"52
  script(s) declare a count, every one verified by running it"*) — which independently covers the
  82/22/178 declarations. The remaining guards in that set are **NOT RUN**, not passing.
* **The whole-population mutation sweep.** I ran only the two-manifest scoped copy (44/44/44/0),
  per the instruction not to run `--mutate .` unscoped. Whether the *other 57* manifests still bind
  against this branch's sources is **NOT MEASURED** here; #252 exists because that question has
  gone wrong five times this session, and the scoped run cannot answer it.
* **`ModelVisibility::None` behaviour.** `openai_models.rs:293-297` has three values. I verified the
  resolver requires `== "list"` so `None` is excluded like `hide`, but I did not find a live cache
  containing a `None` entry, so its real-world shape is **unverified**.
* **Whether the r2 verdict's `dirty: {}` is accurate.** I read the record and the tree is clean at
  `93e3133a`, but I did not reconstruct what the wrapper staged at dispatch.
* **CI itself.** Nothing here was run on a GitHub runner. The three local `--self-test` runs
  (82/82, 22/22, 178/178) and `check-docs.py` reproduce on this machine with its Python; the
  `schema-gates` job and the sharded sweep are **NOT RUN**.
* **`PermissionError` reachability in practice.** M3's probe used `chmod 000` on a temporary
  directory. Whether a `.git`-resident sentinel directory can realistically become unreadable on
  this setup is **not measured** — the defect is the missing barrier, not a demonstrated incident.

