# Round 4 — Claude half — `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md`

**Subject:** the plan the coordinator calls **v5**, at HEAD `5273f06`, branch `docs/dashboard-plan-review`.
**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5). §-refs are to the spec.
**Method:** every Python block was assembled twice — once with the plan's own `extract()`, once with an
independent hand parser — and the two assemblies `diff`ed byte-for-byte before any green was believed.
Both suites were run, controls A–F were run verbatim in a throwaway repo, **50 mutations that the
manifest does not declare** were written and run — 42 against the plan's code, 8 against
`scripts/check-plan-code.py` itself.

---

## READY TO EXECUTE: **NO**

**Must change:**

1. **Regenerate the "Standing evidence" block** — it is stale, and it is wrong about the one thing the
   plan says it cannot be wrong about. Fix the version header (`Version: v4`) and the closing line
   while you are there; there is no v4 or v5 section at all.
2. **Stop claiming `check-plan-code.py` verifies the delivered scripts.** It never opens them.
   Acceptance criterion 5 and the new permanent CI step measure a copy that lives inside the plan.
3. **Declare mutations for the impure layer, or state in the Gaps that it has none.** Every `main`,
   every collector and every *cannot-run* path in both files survives deletion. Fifteen measured.
4. **Give `check-plan-code.py` a case for its own primary job** — a plan whose assembled suite goes
   red must make the check fail. Today no case covers it, and neither does the untagged-fence rule
   v5 was written to add.
5. **Make Task 1 Step 6's controls fail when the gate file is absent.** Measured: with the script
   deleted, every control prints `rc=2`, none prints `ok`, and the plan's stated stop-condition is
   therefore satisfied.
6. **Assert the orange `needs-you` bar** (spec §5's primary chart signal). It is built and nothing
   can see it go.
7. **Fix Task 3 Step 3's stop-condition**, which fires on the correct answer against this repo today.

**Counts:** 1 Blocking · 6 High · 6 Medium · 5 Low.

---

## What reproduced exactly

Stated so the failures below are not read as a general indictment. Everything the plan says about its
**pure** code is true, and I could not break it:

```
$ python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md --evidence
  python fences: 13 (12 assembled, 1 illustrative)
  scripts/check-dashboard-entry.py  4 blocks assembled -> 45/45 passed
  scripts/gen-dashboard.py      8 blocks assembled -> 79/79 passed
  mutations declared and run: 26, caught 26
OK — 2 file(s), 26 mutation(s), 0 survivor(s)     real 0m3.749s
```

Independent hand assembly `diff`ed clean against `extract()`'s (`GATE IDENTICAL`, `GEN IDENTICAL`).
Controls A–F ran verbatim with the script present: `A rc=1`, `B rc=0`, `C rc=1`, `+## not-a-date`
printed, `D rc=1`, `E rc=0`, and all five F rows `rc=1`. The 26 declared mutations each go red via a
case matching their `expect`; I measured the red set per mutation and the `expect` strings are tight
enough (four match more than one case, but in each the extra matches are the same behaviour). Of the
50 undeclared mutations I ran, **21 were caught** — the parser, the renderer and the exemption reader
are genuinely well guarded. Every finding below is about something else.

---

## Blocking

### B1 — the generated evidence block is stale, and the plan's headline claim about it is false

> "**The evidence block near the end is that script's output. Nobody types it, so it cannot be wrong
> about itself.**" — plan:30
>
> "  mutations declared and run: 25, caught 25 … scripts/gen-dashboard.py 8 blocks assembled -> 77/77
> passed" — plan:2133-2136

**What I checked:** ran the generator the plan names, and diffed its output against the pasted block.

```
$ python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md --evidence
```

**Actually true** — three differences from the pasted block:

| Pasted (plan:2130-2162) | Generated today |
|---|---|
| *(line absent)* | `python fences: 13 (12 assembled, 1 illustrative)` |
| `scripts/gen-dashboard.py 8 blocks assembled -> 77/77 passed` | `-> 79/79 passed` |
| `mutations declared and run: 25, caught 25` (25 names listed) | `26, caught 26` (26 names) |

The missing name is `a run of malformed blocks loses its file order` — **v5's own new mutation**, the
one round 4's Codex half asked for. v5 added the mutation, added the two self-test cases, added the
`python fences:` tally line to `evidence()` (`scripts/check-plan-code.py:194-197`), and did not
re-paste the block.

`git show 5273f06 -- docs/superpowers/plans/…-plan.md` confirms it: the diff touches the manifest, the
suite and the prose, and never the evidence fence.

**Why this is Blocking and not cosmetic.** It is the fourth consecutive round whose headline is *the
plan's own stated evidence is wrong*. The generated-evidence mechanism was built specifically to end
that, and the mechanism did not fail — it was simply not re-run. A reader who trusts the sentence at
plan:30 is trusting a hand-copy again, which is the exact posture rounds 2, 3 and 4 each punished. The
plan's own Global Constraints say a written count "is a claim about a number that moves every time a
case is added" (plan:48-52); the paste froze three of them.

**Two more staleness defects in the same class, in the same document:**

- **plan:17** reads `**Version: v4**`. The commit, the coordinator's brief and the manifest are v5.
- **plan:2166** reads `**v3 was reviewed by both halves of round 3; v4 is the result and has NOT been
  reviewed.**` v4 *was* reviewed — `docs/reviews/plan-project-dashboard-r4-codex.md` is committed in
  the same commit as this sentence.
- `grep -n "^#\{1,3\} " …plan.md` returns headings for *What v2 changed*, *v2.1*, *Round 2*, and *v3*
  — and **no v4 or v5 section**. Round 3's and round 4's finding→fix maps exist only in the commit
  message. My brief told me those sections existed; they do not. A reviewer cannot check "is each fix
  correct" against a map that is not in the document.

VERIFIED.

---

## High

### H1 — `check-plan-code.py` never opens the scripts the plan delivers, and two acceptance gates say it does

> "**5. `check-plan-code.py` exits 0** — every declared mutation caught by the case it names." — plan:1599
>
> "- [ ] **Step 5: Run the plan's own checker** … This assembles both files from the blocks above,
> runs both suites, and runs every mutation in the manifest." — plan:1402-1409
>
> `- name: plan code assembles and its mutations are caught` — plan:1529-1530 (added to CI permanently)

**What I checked:** read `check()` at `scripts/check-plan-code.py:126-188`. Every file it touches is
written into `tempfile.TemporaryDirectory()` from the plan's markdown (`:135-139`) and run there
(`:120-123`). It never resolves a path in the repository.

**Actually true:** the checker proves that *the plan's copy* of ~1,100 lines of Python assembles,
self-tests and dies under 26 mutations. It says nothing whatever about `scripts/gen-dashboard.py` or
`scripts/check-dashboard-entry.py` — the files Task 1 and Task 2 create and CI will ship.

Three consequences, in order of cost:

1. **Task 4 Step 5 is offered to the implementer as verification of their own work and is not.** An
   implementer who mistypes a line into `scripts/gen-dashboard.py` gets a green from Step 5. (The
   real files *are* self-tested by the two other CI steps at plan:1523-1527, so this is caught
   downstream — but Step 5's stated meaning is wrong at the point it is read.)
2. **Acceptance criterion 5 is satisfied by a plan that has drifted from the code.** After merge the
   repo holds two copies of the same 1,100 lines and CI enforces only the plan's. The first bug fixed
   in `scripts/gen-dashboard.py` leaves the plan green and the mutation evidence describing a file
   that no longer exists in that form.
3. **The mutation manifest — the only artifact proving the guards are load-bearing — is permanently
   about the wrong subject** the moment the shipped script changes. `CLAUDE.md`: *"A script beats a
   claim only when it reads the thing the claim is about. A green check over the wrong subject is an
   assertion in better packaging."*

Nothing in the plan asserts that the plan's blocks equal the delivered files. The cheapest fix is a
step that `diff`s the assembled files against `scripts/` and fails on any difference; then the CI step
means what its name says.

VERIFIED.

### H2 — the whole impure layer of both scripts is unguarded; 15 undeclared mutations survive, 6 of them turning *cannot tell* into a silent pass

> "**`\"cannot run\" is a FAILURE, never a pass`** (`CLAUDE.md`). Every derivation that can fail must
> render a distinct *could not tell* state, never a silent empty or a zero." — plan:43 (Global Constraint #3)

**What I checked:** wrote 51 mutations the manifest does not contain, applied each to the assembled
files, and ran **both** suites. Harness copies the tree per mutation; anchors verified present.

**Actually true** — survivors, grouped. Each is a behaviour the plan states and nothing can observe:

**(a) The *cannot-run* contract itself — the plan's own first constraint.**

| # | Mutation | Effect |
|---|---|---|
| U1 | gate `main`: `print(CANNOT RUN…); return 2` → `return 0` | a git failure becomes a **passing gate** |
| U2 | gate `collect`: `if names.returncode != 0: return …` → `if False` | a broken git = "no files changed" = pass |
| U3 | gate `collect`: `return [], False, f"could not run git: {exc}"` → `…, None` | an OSError becomes a pass |
| U11 | `open_prs`: `return None, err` → `return [], None` | "could not ask `gh`" renders as "nothing needs you" |
| U12 | `commit_dates`: git-failure branch → `return [], None` | an empty chart with no *could not read* note |
| U13 | `_gh_json`: `JSONDecodeError` → `return [], None` | unparseable `gh` output renders as zero |

U1 is the worst single line in the set: it converts the ratchet from fail-closed to fail-open, and
`45/45 passed` is unchanged. `collect()` and `main()` have **no self-test coverage at all**, and the
controls never reach the error path.

**(b) `no_entry_prs` — spec §7's display half.**

- **U10:** replace the loader guard with `return [], None`. The suite stays green. This is H8's exact
  defect from round 2 (*"a confident 'No branch has skipped its entry' on every page"*), restored, and
  nothing automated notices. The plan's answer is the manual Task 6 Step 5 falsifier — which is a
  human step, in a task nobody has reached, guarding the mechanism whose whole purpose is to make the
  gate's erosion visible.

**(c) `main` — the composition path B2 exists to protect.**

- **U14:** `if r.returncode != 0 or not a.out.is_file():` → `if False:` — brief-compose failing
  silently, the page written or not, exit 0.
- **U16:** insert `a.out.write_text(frag); return 0` before the compose call — **v1's B2 defect
  verbatim**: the raw fragment written straight to the served path, no `<!doctype>`, no charset, no
  Ask tray. Green.
- **U15:** delete the `--window < 1` guard. Green. (`build`'s zero-window case tests `build`, not the CLI.)
- **U30/U31:** `--store` never read; `today` frozen. Green.

**(d) Grammar/render behaviours the spec names.**

- **U32** — spec §5: *"Orange = that day has an unresolved `needs-you` entry."* Delete `cls = "bar
  needs" if day["needs_you"] else "bar"` → `cls = "bar"`. **Green.** See H5.
- **U33** — spec §9: *"a resolved `needs-you` item disappears from §4 **and stays in §6**."* Filter
  cleared entries out of *What changed*. **Green** — the "stays in §6" half has no case.
- **U35/U37** — the `needs you` label on the card, and the §4→§6 link on each needs-you row. Green.
- **U7** — replace `_html.escape` with the identity. Green. No case asserts escaping anywhere, on a
  page built from a file a skill writes and a `gh` API response.
- **U8** — `_slug` becomes the identity, so DOM ids and fragments keep their `/`. Green.
- **U9** — `_pos` drops the ordinal, so a **same-day** `[resolved:]` silently stops clearing. Green.
- **U29** — `bucket_days`' `has_entry` stops excluding malformed blocks, so a broken block marks its
  day as written-up. Green.
- **U20** — `tag = "a"` unconditionally, restoring a linkless `<a>` on entryless days. Green.

**What I am *not* saying:** several of these need a subprocess and cannot be unit-mutated cheaply.
That is a reason to write them down in *Gaps*, not a reason for §7 and §10.4 to carry a ✅. The
Self-Review's §10.4 row reads "✅ including a falsifier with `gh` off the `PATH`" — I ran that
falsifier and it does fire (`open_prs: (None, "could not run gh: …")`), but it is a manual step, it
covers two of the four collectors, and it cannot see U13 at all.

VERIFIED (harness and per-mutation output retained in the session scratchpad).

### H3 — `check-plan-code.py`'s own self-test has no case for its primary job

> "`python3 scripts/check-plan-code.py --self-test          # 12 cases`" — `scripts/check-plan-code.py:6`
>
> "an untagged python fence is now a hard **FAILURE** in the checker" — commit `5273f06`

**What I checked:** mutated the checker and ran its `--self-test`, then ran the mutant against a real
plan. Three mutants survive 19/19:

```
$ python3 c7.py p_red.md          # c7: `if rc != 0: ok = False` → `ok = ok`
  ✗ b.py: --self-test exited 1
    [FAIL] everything: got 0 want 1
OK — 1 file(s), 0 mutation(s), 0 survivor(s)
rc=0
$ python3 c7.py --self-test
19/19 passed
```

**Actually true:**

| Mutant | What it disables | Self-test |
|---|---|---|
| **C7** `if rc != 0: ok = False` → `ok = ok` | *a plan whose assembled suite FAILS still reports `OK` and exits 0* | 19/19 |
| **C6** `ok = not problems` → `ok = True` | every structural finding — untagged fence, tag with no block, invalid mutations JSON, non-python block under a file tag — becomes advisory | 19/19 |
| **C8** unknown-file mutation target | a mutation aimed at a file that does not exist no longer fails | 19/19 |

C7 is the tool's single most important behaviour and there is no case: the only "failing file" fixture
in the suite (`a file with no entrypoint`) exits **0**. C6 is v5's own headline fix — the untagged-fence
rule has a case proving `extract()` *reports* the problem (`:239-240`) and none proving `check()`
*fails* on it. Under C6 the ✗ line still prints and the exit code is 0; CI reads the exit code.

**Related, measured on the real checker:**

```
$ python3 …/check-plan-code.py p_vac.md    # a _self_test that prints "0/0 passed" and returns 0
OK — 1 file(s), 0 mutation(s), 0 survivor(s)     rc=0
$ python3 …/check-plan-code.py p_illus.md  # real code hidden behind <!-- illustrative -->
OK — 1 file(s), 0 mutation(s), 0 survivor(s)     rc=0
$ python3 …/check-plan-code.py p_zero.md   # a plan with tagged blocks and NO mutations at all
OK — 1 file(s), 0 mutation(s), 0 survivor(s)     rc=0
```

The zero-mutation and vacuous-suite cases at least disclose themselves in the summary line. The
`<!-- illustrative -->` escape does not: it is an unbounded hiding vector, and the tag it replaces is
the one the checker exists to forbid. One good thing, tested: a column-0 ` ``` ` inside a tagged
python block truncates the assembly and fails **loud** (`SyntaxError: unterminated triple-quoted
string literal`), so that hazard is fail-closed.

VERIFIED.

### H4 — Task 1 Step 6's controls report a pass when the gate script does not exist

> "**If A, C, D or any F row prints `ok`, the gate does not work — stop.**" — plan:529

**What I checked:** ran the control block verbatim from a directory containing `scripts/` but **not**
`scripts/check-dashboard-entry.py`, i.e. the state after a `cp` typo or a wrong `cd`.

**Actually true:**

```
A rc=2   B rc=2   C rc=2   D rc=2   E rc=2
  ## 2026-08-28-foo                rc=2   … (all five F rows rc=2)
$ … | grep -c '^ok —'
0
```

Zero rows print `ok`, so the plan's stated stop-condition is **satisfied**. The block reports a pass
having tested nothing. `⛔ No set -e` (plan:486, correct for A/C/D) means the failing `cp` does not
stop the script either.

I found this by accident — my first run had the file one directory up — which is precisely how it
would happen to an implementer. The criterion also never states what B and E must be, though their
comments say `want ok 0`; `rc=2` is not `ok`, so it slips through both halves of the matched pair the
plan built specifically so that "D alone cannot look convincing" (plan:530).

Round 3 filed the same shape ("controls A–F all printing `rc=0`"), and the fix — adding the
`if __name__` dispatch — addressed the *cause it had then*, not the class. The falsifier the harness
needs is an assertion on the expected code per row, or `test -f scripts/check-dashboard-entry.py ||
exit 1` before control A.

VERIFIED.

### H5 — the orange `needs-you` bar is built and no case can see it go

> "**Orange = that day has an unresolved `needs-you` entry.**" — spec §5
>
> "§6.1 rendered once, marked bars | ✅ **both** marks asserted on **sighted output only**" — plan:1923

**What I checked:** mutation U32 — `cls = "bar needs" if day["needs_you"] else "bar"` → `cls = "bar"`,
in `_bar` (plan:909).

**Actually true:** `79/79 passed`. The `_marks()` comparisons (plan:1272-1286) cover the quiet-day dot
and the §9 gap mark; there is no third comparison for the needs-you colour. `case("needs-you day is
flagged", days[2]["needs_you"], True)` asserts `bucket_days`' *data*, not the bar. The only surviving
trace of the mutation is the `title`/`aria-label` text and the `.vh` span — the exact three channels
`_marks` was rewritten to exclude because H4 of round 2 showed they let a mark be deleted invisibly.

The Self-Review's "**both** marks" is accurate about the two it names and silent about the third,
which is the spec's *primary* chart signal. This is the third instance of one shape (r2 H4: the
zero-commit mark; r3 H2: the §9 alarm; now the orange bar) — and the second time the fix closed the
instance and not the class.

VERIFIED.

### H6 — Task 3 Step 3's stop-condition fires on the correct answer, today, in this repo

> "**If either prints `0` with `err: None`, the collector reports \"nothing\" where it means \"could not
> ask\" — stop.**" — plan:841-842

**What I checked:** ran `commit_dates(14)`, `open_prs()` and `no_entry_prs()` from the assembled
`gen-dashboard.py` against this working tree, then re-ran with `gh` and `git` off the `PATH`.

**Actually true:**

```
commit_dates: 80 err: None
open_prs: 0 err: None            <-- the plan says STOP
no_entry_prs: 0 err: None

$ gh pr list --state open --json number,title
[]                                gh rc=0
```

There are genuinely zero open pull requests, so `0 / err: None` is the *right* answer and the plan
instructs the implementer to stop. The could-not-tell contract is fine — with the binaries hidden it
returns `(None, "could not run gh: [Errno 2] …")` for all three.

The plan makes exactly this argument three tasks later — "**`0` is also the correct answer today, so
the falsifier is the only thing that distinguishes them**" (plan:1558-1559) — for `no_entry_prs`, and
did not apply it to the step immediately in front of it. Step 3 needs the same treatment: run it once
normally, once with `gh` off the `PATH`, and compare the **pair**.

VERIFIED.

---

## Medium

### M1 — `_self_test` is assembled twice, byte-identical, into `scripts/check-dashboard-entry.py`

**What I checked:** `grep -n "^def " ` on the assembled file, then diffed the two ranges.

```
150:def _self_test() -> int:      (Task 1 Step 4 block, plan:284-357)
240:def _self_test() -> int:      (Task 1 Step 5 block, plan:383-455)
copy1 lines 74  copy2 lines 74  IDENTICAL
```

Step 5 is titled *"Add the git collector, `main`, and the dispatch"* and its block silently re-includes
all 74 lines of Step 4's suite. An implementer who appends the block as shown writes 22% of the file
twice; one who follows the step title writes it once — and the checker validated the first reading.
Python takes the second definition, so both suites are green either way and `check-plan-code.py`
cannot see it. It also creates a live blind spot: `check()` uses `src.replace(find, repl, 1)`
(`:167`), so any future mutation anchored in the self-test would land on the **dead** first copy.

### M2 — Task 2 Step 2 tells the implementer to write a test that does not exist until Task 4

> "- [ ] **Step 2: Write the failing test**, then **Step 3: implement the parser**" — plan:598

One block follows, and it is the parser. Every `parse_entries` case lives in `gen-dashboard.py`'s
`_self_test`, which is **Task 4 Step 3**. Step 5 of the same task already carries the plan's own
warning — *"A step whose stated outcome cannot occur at that point is the defect rounds 2 and 3 filed
three times"* (plan:703-704) — three lines below the step that commits it.

### M3 — `verdict`'s three-valued `reason` is asserted in prose and untested in code

> "⚠ `reason` is **three-valued** … `\"\"` means the marker was present with nothing after it and must
> **refuse** … `if reason:` alone conflates the last two." — plan:276-277

Deleting the whole `if reason == "": return 1, f"{NO_ENTRY} was declared with no reason after it"`
branch leaves `45/45 passed` (U5). Both branches return `1`; the only difference is the message, and
`case("NO-ENTRY without a reason is refused", …[0], 1)` reads the code, not the message. So the
distinction the ⚠ calls load-bearing is, as built, cosmetic and unguarded. Either assert the message
(as the sibling case `NO-ENTRY reason is echoed` already does for the other branch) or drop the ⚠.

### M4 — `collect()`'s three-dot diff is load-bearing, survives its removal, and the controls structurally cannot see it

`...HEAD` → `..HEAD` in both `subprocess.run` calls leaves `45/45 passed` (U4). It is a real behaviour
change — measured in a throwaway repo where `master` advances after the branch point:

```
--- three-dot (as written) ---   docs/reviews/r.md
ok — no tracked files changed outside the exempt paths        rc=0
--- two-dot (the mutation)  ---  docs/reviews/r.md
                                 lib/other.ts
REFUSED — 1 tracked file(s) changed and no entry was added…    rc=1
```

A review-only branch is refused for a file `master` changed. Controls A–F cannot observe it because
`master` never advances in them — the control repo is built so the two forms coincide. The most common
real shape (a branch behind a moving default) is the one the harness excludes.

### M5 — §9's first bullet is not built, under a blanket ✅

> spec §9: "the page names **the last date an entry was written**"
>
> "§9 checks | Tasks 1, 4, 5 | ✅ **including the commits-with-no-entry alarm**" — plan:1926

`build()` renders no element that states the last entry date; a reader infers it from the first
`<h3>`, and on an empty store gets "No entries yet". No case mentions it. §9's fourth bullet is half
covered (M-list above, U33). The ✅ is a blanket over five bullets of which one is unbuilt, one is
half-asserted, and one (folds) the Self-Review itself downgrades to *partial* two rows later. Rounds
1, 2 and 3 each had a headline of a Self-Review claiming coverage it did not have; this is the same
mark, smaller.

### M6 — `<!-- illustrative -->` is an unbounded hiding vector for the checker

Measured (H3 above): a `<!-- illustrative -->` block containing arbitrary broken code passes with
`rc=0`. The tag was introduced in v5 to legitimise Task 5's `explainer-serve.py` rows, which is the
right call — but it now means "an untagged block FAILS the checker" is enforced against typos and not
against intent. A one-line mitigation: require the tag to carry a reason
(`<!-- illustrative: explainer-serve.py rows, not assembled -->`) and print the reasons in the
evidence block, so a reader sees what was excluded and why.

---

## Low

1. `scripts/check-plan-code.py:6` — `# 12 cases`; the run prints `19/19 passed`. The plan's own Global
   Constraint (plan:48-52) forbids exactly this, and the script is being added to the mechanically-
   enforced table by Task 6 Step 6.
2. `scripts/check-plan-code.py:63` — `extract()` is annotated
   `-> tuple[dict[str, list[str]], list[dict], list[str]]` and returns a **4**-tuple (`:116-117`).
3. `docs/dev-process.md` is **214** lines against a `check-docs.py` budget of **220**
   (`scripts/check-docs.py:191`). Task 6 Step 6's three pointer rows leave three lines of headroom.
   The plan's "⚠ Re-measure the line budget with `wc -l` first" is right; the margin is worth naming
   in the step so it is not discovered at the gate.
4. Task 6 Step 7's `gh pr create --body-file /tmp/pr-body.md` reads a file only the CI snippet
   (Step 5) creates, and only inside the runner. Nothing tells the implementer to write it locally.
5. `run_suite` (`scripts/check-plan-code.py:120-123`) passes `timeout=120` and nothing catches
   `subprocess.TimeoutExpired`, so a hung assembled suite ends the checker in a traceback rather than
   a `CANNOT RUN — treat this as NOT CHECKED` line. Cheap to fix, and it is the shape this repo keeps
   filing.

---

## The undeclared mutations that SURVIVED — the requested list

50 run — 42 against the plan's code (26 survived) and 8 against the checker (3 survived).
**21 caught, 29 survived.** Ordered by what a reader should care about; the trivially cosmetic ones
are grouped at the end.

**Cannot-run turned into a silent pass (6)**

1. `U1` gate `main` — git failure returns `0` instead of `2`. **The ratchet becomes fail-open.**
2. `U2` gate `collect` — `git diff`'s exit code ignored; a broken git reads as "nothing changed".
3. `U3` gate `collect` — `OSError`/`SubprocessError` returns `err=None`.
4. `U11` `open_prs` — a `gh` failure returns `([], None)`.
5. `U12` `commit_dates` — a `git log` failure returns `([], None)`.
6. `U13` `_gh_json` — `JSONDecodeError` returns `([], None)`.

**Spec behaviours with no case (7)**

7. `U32` — §5's **orange `needs-you` bar** class deleted. *(H5)*
8. `U33` — §9: a resolved entry vanishes from *What changed* instead of staying.
9. `U10` — `no_entry_prs` always `([], None)`: §7's display, round 2's H8 restored.
10. `U9` — `_pos` drops the ordinal; a **same-day** `[resolved:]` stops clearing.
11. `U35` — the `needs you` label on the entry card removed.
12. `U37` — the §4 row loses its link into §6.
13. `U29` — `bucket_days.has_entry` counts malformed blocks, so a broken block marks its day written-up.

**`main` / composition — B2's territory (5)**

14. `U16` — the raw fragment written straight to `--out`, bypassing `brief-compose.py`. **B2 verbatim.**
15. `U14` — brief-compose's failure ignored.
16. `U15` — the `--window < 1` refusal deleted.
17. `U30` — `--store` never read; the page renders empty on any store.
18. `U31` — `today` frozen; the chart window stops moving.

**Correctness of the gate's inputs (3)**

19. `U6` — `--pr-body-file` read replaced by `body = ""`; **every `NO-ENTRY:` stops working.**
20. `U4` — `...HEAD` → `..HEAD`. *(M4)*
21. `U5` — the empty-`NO-ENTRY:` message branch deleted. *(M3)*

**Output hygiene (3)**

22. `U7` — `_html.escape` becomes the identity. No case asserts escaping.
23. `U8` — `_slug` becomes the identity; `/` survives into DOM ids and `href="#…"`.
24. `U20` — `tag = "a"` unconditionally.

**Cosmetic (2)**

25. `U41` — the *Elsewhere* cross-links to `/goals`, `/backlog-table`, `/latest` removed.
26. `U42` — the entire `<style>` block commented out; the page renders unstyled.

**And three against the checker itself (H3):** `C6` structural problems become advisory, `C7` a failing
assembled suite still reports `OK`, `C8` a mutation aimed at an unknown file no longer fails — each
leaving `19/19 passed`.

The manifest's 26 are all in the pure parse/render layer, and that layer is genuinely hard to break —
21 of my 51 died there. **The declaration is complete for what it covers and empty everywhere else**,
and the boundary runs exactly along "does this function call a subprocess or touch a file".

---

## Not re-reported

Checked and confirmed fixed, so recorded here rather than as findings: the `import re` placement
(r3 B2 — Step 2 raises `NotImplementedError`, not `NameError`); `fetch-depth: 0` and the absence of a
`with:` block on `actions/checkout@v4` (`.github/workflows/ci.yml:31`); the `_ordered` splice and its
`placed` run-ordering fix (mutation 26 kills it, and my own run/append/all-malformed probes all held);
the lazy `_exemption_reader` (the split is right — the grammar must be eager or nothing parses, and I
confirmed the falsifier is now reachable); the untagged-python-fence rule (works, though see C6); the
`--first-parent` argument case; `would_be_id` and the three distinguishable resolve diagnoses; fence
length and character tracking; the tab-indent column rule; and every line citation I could check —
`check-explainer-delivery.py:46` (`SKILLS = ROOT / ".agents" / "skills"`) and `:53` (`PAGE_SKILLS`),
`gen-goals-page.py:457` (`--self-test`) and `:487-498` (the brief-compose pattern),
`check-function-revokes.py:113` (`def _self_test`), `brief-compose.py`'s `--content/--slug/--title/--out`,
`explainer-serve.py:559` (`var here`, which Task 5's snippet needs), and
`docs/roadmap-to-launch.md:1331` (the `## Project dashboard` section the plan says to **update**).

The gate's exemption list is out of scope by the user's 2026-08-28 decision and was not examined.

---

## Verdict: **NOT CONVERGED**

Round 4's Codex half found one undeclared mutation and named the reason it existed. That reason —
*the checker proves the declared mutations are caught, never that the declaration is complete* —
turns out to describe a boundary, not a gap: **every impure function in both files is undeclared, and
so is every behaviour the checker itself relies on.** Thirty survivors, six of which convert the
plan's own first Global Constraint into its opposite.

The pure layer is finished work and should not be touched. What is not finished is the layer where
this repo's measured defects actually live, and the document's account of its own verification, which
is stale for the fourth round running in the very block built to stop that happening.
