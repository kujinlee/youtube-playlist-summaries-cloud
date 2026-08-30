# Project Dashboard Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local page at `http://127.0.0.1:7391/dashboard` showing what needs the user, what changed, and one chart of daily activity — plus the gate that makes the entries actually get written.

**Architecture:** Three pure-Python pieces on the server that already exists. `scripts/gen-dashboard.py` parses an append-only markdown store and renders a standing page; `scripts/check-dashboard-entry.py` is a CI ratchet that refuses a branch with no entry; a small change to `scripts/explainer-serve.py` makes `<details>` folds survive live reload. No new process, no new port, no new dependency.

**Tech Stack:** Python 3 standard library only (`argparse`, `re`, `datetime`, `subprocess`, `pathlib`). No pip installs. Rendering is hand-written HTML/CSS; page composition reuses `scripts/brief-compose.py`.

**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5, merged `c5fcb07`).

> ⚠ **THE CODE BLOCKS THAT WERE HERE ARE GONE — read `scripts/` instead.**
> This document held byte-identical copies of `scripts/gen-dashboard.py` and
> `scripts/check-dashboard-entry.py`, kept in step by a CI check. That check was retired
> 2026-08-29 (backlog #70) and the copies were **deleted rather than banner-warned**: code in a
> document that nothing validates stops being true quietly, and creates a belief that something
> is covered.
>
> **The delivered scripts are the only source:** [`scripts/gen-dashboard.py`](../../../scripts/gen-dashboard.py),
> [`scripts/check-dashboard-entry.py`](../../../scripts/check-dashboard-entry.py).
> Their 43 mutations now live in [`scripts/mutations/`](../../../scripts/mutations/) and run against
> the delivered files in CI via `check-plan-code.py --mutate .`.
>
> What remains below is the **reasoning and the task breakdown** — the part that was ever worth
> reading, and the part that is now free to go stale honestly.
Section references below (§4, §5, §6.2, §7) are to that spec.

**Version: v8** — folds in **both halves of round 6**, a short re-review scoped to round 5's
own fixes. It found them correct in verdict and INCOMPLETE IN MECHANISM — the shape now named
at the end of *v8 — round 6*. v7 folded in **both halves of round 5**, which was SCOPED to
`scripts/check-plan-code.py` rather than to this plan. Not one of its findings was about the tasks
below; all of them were about the tool that checks them. See *v7 — round 5* at the end. v6 folded in
**both halves of round 4** (Codex 3 findings; Claude 1 Blocking, 6 High,
6 Medium, 5 Low; both NOT CONVERGED). v5 folded in round 4's Codex half; v4 folded in both halves of
round 3 (Codex 2B/2H, Claude 2B/4H/7M/7L) and made the evidence generated rather than typed.

**Round 4's Blocking is the point of v6, and it is about this header.** The evidence block was
generated at v4 and never regenerated, so it described v4's run while sitting under a v5 document —
the fourth round running in which what failed was *the plan's account of its own verification*, this
time **inside the mechanism built to stop exactly that**. The lesson is not that generating was
wrong. It is that **a derived artifact which is not re-derived on every change is a cached claim
with better provenance**, and therefore worse than a typed one. v6 replaces the rule with a check:
`check-plan-code.py --verify-evidence` exits 1 when the pasted block is not what the current
document produces, and it runs in CI.

**Round 3's finding was that this document's evidence could not be trusted.** Its blocks did not
assemble — no import block for one file, no `__main__` dispatch for the other, three functions
present only as prose — while its evidence line read `19/19 mutations caught` and one it *named*
survived. Every earlier reviewer had injected the missing pieces into a private harness, so the hole
lived through two rounds.

**The fix is structural, not editorial.** Every Python block is now tagged with the file it belongs
to, and `scripts/check-plan-code.py` assembles them, runs both suites, and applies the mutation
manifest at the end of this document — requiring each to go red **via the case it names**. The
evidence block near the end is that script's output. Nobody types it, so it cannot be wrong about
itself.

v2 folded in round 1
(`docs/reviews/plan-project-dashboard-r1-codex.md`, `…-r1-claude.md`; both **NOT CONVERGED**,
3 Blocking + 3 High + 3 Medium + 1 Low and 3 Blocking + 5 High + 8 Medium + 7 Low respectively).
Both halves **executed** every Python block in v1 before judging it, which is why they found
defects three prose rounds on the spec did not. What changed, and why, is listed under
*What v2 changed* at the end.

## Global Constraints

- **Python 3 standard library only.** No new dependency, no pip install, no npm.
- **Every script gets `--self-test`** with pure functions only, exiting non-zero on failure, matching `scripts/check-function-revokes.py:113` and `scripts/gen-goals-page.py:457`.
- **`"cannot run" is a FAILURE, never a pass`** (`CLAUDE.md`). Every derivation that can fail must render a distinct *could not tell* state, never a silent empty or a zero.
- **Never `$?` after a pipe** — it reports the last command's status. Use `PIPESTATUS` or avoid the pipe. Measured three times in this repo.
- **Anything longer than a line goes in a file** — `--body-file`, `git commit -F`, `--prompt-file`. A backtick inside a double-quoted bash string is command substitution.
- **The store is append-only.** Nothing edits or deletes an existing entry block; corrections are appended.
- **Bare citations are a defect.** Every path written into code comments or page output is repo-relative and complete.
- **Never write an expected self-test COUNT.** v1 said `19/19` where the truth was `18/18`, and an
  implementer following its own TDD loop would have stopped to hunt for a case that does not exist.
  A count in a plan is a claim about a number that moves every time a case is added. Every "run the
  self-test" step below asserts **exit 0 and no `[FAIL]` lines** instead. If a step names a count
  anywhere, that is a defect in this plan, not in the code.
- **A falsifier must be shown to FIRE.** v1's Task 4 falsifier could not fail — `git stash push` on
  a committed file is a no-op — and the plan told the implementer to read its success as failure.
  Every step below that claims to falsify something states the observation that makes it go red,
  and the implementer must see red before proceeding. This is `docs/portable-practices.md` §17.
- Branch + PR for every task group; **merging is a human gate**.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/check-dashboard-entry.py` | **Create FIRST.** The ratchet, **and the owner of the entry-header grammar**. |
| `docs/dashboard-entries.md` | **Create.** The append-only store. Owned by humans and the skill, never rewritten by a script. |
| `scripts/gen-dashboard.py` | **Create.** Parse the store, derive activity, open PRs and recorded exemptions, then **compose and write** `~/explainers/dashboard.html` via `brief-compose.py`. |
| `scripts/explainer-serve.py` | **Modify.** Persist `<details>` open state across live reload. |
| `scripts/check-explainer-delivery.py` | **Modify** (`:53`). Add `dashboard` to `PAGE_SKILLS`. |
| `.agents/skills/dashboard/SKILL.md` + `.claude/skills/dashboard` | **Create.** Real file plus symlink. |
| `.claude/hooks/regen-dashboard.sh` + `.claude/settings.json` | **Create + modify.** A hook with no settings entry never runs. |
| `.github/workflows/ci.yml` | **Modify.** `fetch-depth: 0`, both `--self-test`s, **and the ratchet itself**. |
| `docs/dev-process.md` | **Modify.** One pointer row per new mechanically-enforced script. |
| `docs/roadmap-to-launch.md` | **Modify — UPDATE the existing section**, do not add one. |

⚠ **The skill path:** all twenty existing skills are a real directory under `.agents/skills/` plus a
symlink from `.claude/skills/`; `scripts/check-explainer-delivery.py:46` reads `.agents/skills`.

### ⛔ Why the gate is Task 1 and the parser is Task 2

The ratchet and the page must agree on what an entry header **is**, or the gate passes branches whose
entry the page renders under *"Could not parse this entry"*. Round 2 measured five such shapes.

One grammar, therefore, owned by `check-dashboard-entry.py` and imported by `gen-dashboard.py`. The
arrow points **generator → gate**, never the reverse: a gate must not import the thing it guards.
That import is why the order changed — building the parser first would recreate the task-ordering
defect rounds 2 and 3 filed three times between them.

### How this plan is verified

**Every Python block below is either tagged with the file it belongs to — assembled, run and
mutated by a script — or explicitly marked `<!-- illustrative -->`.** An untagged block now FAILS
the checker: three functions once lived as prose through two review rounds because nothing counted
the blocks it could not see. `python3 scripts/check-plan-code.py <this file>` concatenates the tagged blocks in
document order, runs each file's `--self-test`, then applies every mutation in the manifest at the
end and requires each to go **red via the case it names**.

That exists because three review rounds each found the plan's stated evidence wrong, and each found
it by hand — a transcription that quietly weakened an assertion, then blocks that did not assemble at
all while the evidence line read `19/19 mutations caught` and one it *named* survived. Prose about a
measurement is not the measurement. **The evidence block at the end is generated output, not typed.**

---

## Task 1: The gate, and the grammar it owns

**Files:** Create `scripts/check-dashboard-entry.py`.

- [ ] **Step 1: Write the failing test.** Create the file with the module docstring, the imports, the
constants and the grammar — then a stub `verdict` raising `NotImplementedError`, and the self-test
from Step 4.

⚠ **`import re` belongs in this first block.** A `re.compile` above the import makes Step 2's
expected `NotImplementedError` a `NameError` instead — measured in round 2, for this very file.


- [ ] **Step 2: Run it.** Expected: **`NotImplementedError`**, non-zero exit. A `NameError` means an
import is missing from Step 1.

- [ ] **Step 3: Implement the exemption reader and the verdict**


⚠ `reason` is **three-valued**: a non-empty string exempts, `""` means the marker was present with
nothing after it and must **refuse**, `None` means absent. `if reason:` alone conflates the last two.

- [ ] **Step 4: Add the PURE self-test and run it.** Expected: exit 0, no `[FAIL]` lines. **Do not
check the count** — see Global Constraints.

⚠ This block is `_self_test` and nothing else. It covers only functions that exist by the end of
Step 3; the cannot-run cases for `collect` and `main` arrive in Step 5 as a **second** function,
because a step must be runnable at the point it is read. **Until v6 this block was silently
re-included whole inside Step 5's**, so an implementer following the blocks wrote 74 lines twice and
one following the step titles wrote them once — and neither suite could tell, because Python keeps
the second definition. Worse, `check-plan-code.py` applies each edit with `replace(…, 1)`, so any
mutation anchored in the self-test landed on the **dead first copy**.


- [ ] **Step 5: Add the git collector, its cannot-run suite, `main`, and the dispatch**

⚠ **The `if __name__` line is part of this step.** Without it the file exits 0 silently, and a
control harness reads that as success — round 3 measured controls A–F all printing `rc=0` against
exactly that.

⚠ **`_impure_self_test` is the point of this step, not decoration.** `collect` and `main` are the
only two functions in this file that can *fail to run*, and they were the only two with no coverage
at all. The gate refusing to run must be distinguishable from the gate passing — `main` returns
**2**, never 0. Run `--self-test` after this step and expect **two** result lines.


- [ ] **Step 6: Prove it passes, then make it go RED**

⛔ **No `set -e`** — controls A, C and D are *expected* to exit non-zero, and `set -e` kills the
script at A before it prints a verdict. ⛔ **No `git stash`** — on a committed file it does nothing;
the only input `collect()` has is `git diff <base>...HEAD`, so a falsifier must change that.

⛔ **The block asserts an exact code per row, and refuses to start if the gate script is not
there.** v5 stopped at *"if any row prints `ok`, stop"*, and round 4 measured what that misses: run
from a directory where the `cp` silently failed, **every row prints `rc=2`, no row prints `ok`, and
the stated stop-condition is satisfied by a run that tested nothing**. `rc=2` is the gate's own
*cannot run* code — the one value that is neither pass nor refusal — and the criterion was blind to
exactly it. The reviewer hit this by accident, having the file one directory up, which is precisely
how an implementer meets it.

```bash
D=$(mktemp -d); cd "$D" || exit 1
git init -q .; git config user.email t@t; git config user.name t
mkdir -p docs scripts
cp "$OLDPWD/scripts/check-dashboard-entry.py" scripts/ \
  || { echo "CANNOT RUN — the gate script did not copy. Treat this as NOT TESTED."; exit 1; }
test -s scripts/check-dashboard-entry.py \
  || { echo "CANNOT RUN — scripts/check-dashboard-entry.py is absent or empty. NOT TESTED."; exit 1; }
git add -A; git commit -qm base; git branch -M master; git checkout -qb feature

GOT=""
row() {  # row <label> — records the code so the verdict is compared, never eyeballed
  python3 scripts/check-dashboard-entry.py --base master; local rc=$?
  printf '  %-32s rc=%s\n' "$1" "$rc"; GOT="$GOT$1=$rc;"
}

mkdir -p lib; echo "x" > lib/x.ts; git add -A; git commit -qm code
row A                                                                      # want REFUSED 1

printf '## 2026-08-28\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm entry
row B                                                                      # want ok 0

git rm -q docs/dashboard-entries.md; git commit -qm remove                 # THE FALSIFIER
row C                                                                      # want REFUSED 1

mkdir -p docs   # NOT optional: C's `git rm` removed the last file in docs/ and git
                # removed the directory. Without this the printf fails, nothing is
                # committed, and D refuses because there is no entry AT ALL —
                # passing without ever exercising the date rule. MEASURED.
printf '## not-a-date\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm baddate
git diff -U0 master...HEAD -- docs/dashboard-entries.md | grep '^+##'      # must print it
row D                                                                      # want REFUSED 1

printf '## 2026-08-28\nDid a thing.\n' > docs/dashboard-entries.md
git add -A; git commit -qm gooddate
row E                                                                      # want ok 0

n=0
for h in '## 2026-08-28-foo' '## 2026-08-28.' '## 2026-08-28 [needs-yo]' \
         '## 2026-08-28 rambling title' '##2026-08-28'; do
  n=$((n+1))
  printf '%s\nBody.\n' "$h" > docs/dashboard-entries.md
  git add -A; git commit -qm t >/dev/null
  row "F$n"                                                                # want 1 each
done

WANT="A=1;B=0;C=1;D=1;E=0;F1=1;F2=1;F3=1;F4=1;F5=1;"
if [ "$GOT" = "$WANT" ]; then echo "CONTROLS OK"; else
  echo "CONTROLS FAILED — the gate does not behave as specified."
  echo "  want $WANT"; echo "  got  $GOT"
fi
cd "$OLDPWD"; rm -rf "$D"
```

**Anything but `CONTROLS OK` is a stop.** C is the falsifier proper; D and E are a matched pair,
because D alone can pass for the wrong reason. The `want`/`got` pair is printed on failure so the
*shape* of the disagreement is visible — an all-`2` row means the gate never ran, not that it refused.

- [ ] **Step 7: Commit.**

---

## Task 2: The entry store and its parser

**Files:** Create `docs/dashboard-entries.md`, `scripts/gen-dashboard.py`.

- [ ] **Step 1: The module header, the imports, and the grammar import**


⚠ **`BLOCK` is loose and `HEADER` is strict, deliberately.** `BLOCK` decides what *starts* an entry,
so `##2026-08-28` is CAPTURED rather than vanishing. `HEADER` decides whether it is *well-formed*.

- [ ] **Step 2: implement the parser.** ⚠ **Its cases live in Task 4 Step 3**, with the rest of
`gen-dashboard.py`'s suite — this step writes the parser and nothing else, and there is no `--self-test`
to run until Task 4. v5 titled this *"Write the failing test, then implement the parser"* and followed
it with one block, the parser. **A step whose stated outcome cannot occur at that point is the defect
rounds 2, 3 and 4 each filed** — and v5's own warning to that effect sits three lines below this line.


- [ ] **Step 4: Create the store with its first real entry**

```markdown
# Dashboard entries

Append-only. One `## YYYY-MM-DD` block per entry; **newest at the end**.
Nothing here is edited or deleted — corrections are appended.
Grammar: `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` §6.2.
Rendered by `scripts/gen-dashboard.py`; enforced by `scripts/check-dashboard-entry.py`.

## 2026-08-28
Started building the dashboard — a page that shows what changed while you were away.
<!--tech-->
Spec v5 merged as `c5fcb07`. Task 2 of the project-dashboard plan.
```

⚠ **"Newest at the end" is load-bearing**, not formatting: `_ordered` places malformed blocks
relative to their file neighbours, and the render reverses this file. This header line is the
durable statement of that rule — `_ordered`'s docstring points here rather than at a step number.

- [ ] **Step 5: Verify the real store parses** — expected `1 entries; [None]` — then commit.

⚠ **The full self-test does not run until Task 4.** It exercises `unresolved` (Task 3) and `build`
(Task 4), so at this point run only the parser cases you have. A step whose stated outcome cannot
occur at that point is the defect rounds 2 and 3 filed three times.

---

## Task 3: Activity, open pull requests, and recorded exemptions

**Files:** Modify `scripts/gen-dashboard.py`.

- [ ] **Step 1: `unresolved` and `bucket_days`**


⚠ `unresolved` iterates `e["resolves"]` as a **list** — §6.2 says flags are "zero or more", and a
scalar silently discarded the first of two, clearing one item and leaving the other open forever.

- [ ] **Step 2: The impure collectors**


⚠ **`--first-parent` is spec §5's requirement, not a preference**: after a squash-merge a plain
`git log` also counts the branch's own commits, so "commits" would mean two things — and the §9
alarm is derived from this number.

- [ ] **Step 3: Verify `commit_dates` and `open_prs` against the real repo**, then falsify the
could-not-tell contract with `gh` off the `PATH`. **Compare the PAIR — the run with the binaries and
the run without. A `0` is meaningful only next to the `None` it is not.**

```bash
cat > /tmp/probe.py <<'PY'
import importlib.util as u
s = u.spec_from_file_location("g", "scripts/gen-dashboard.py")
g = u.module_from_spec(s); s.loader.exec_module(g)
for label, call in (("commit_dates", lambda: g.commit_dates(14)),
                    ("open_prs",     g.open_prs),
                    ("no_entry_prs", g.no_entry_prs)):
    v, err = call()
    print(f"  {label:14} n={'None' if v is None else len(v):>4}  err={err!r}")
PY
PY3=$(command -v python3)   # ⛔ absolute: emptying PATH hides the INTERPRETER too, and
                            #    `env PATH=/nonexistent python3` then dies before the
                            #    falsifier runs at all. Measured while writing this step.
echo "--- WITH the binaries ---";  "$PY3" /tmp/probe.py
echo "--- WITHOUT them ---";       env PATH=/nonexistent "$PY3" /tmp/probe.py
```

**Stop unless BOTH hold:** with the binaries present every `err` is `None`; with the `PATH` emptied
every one of the three returns `n=None` and a non-empty `err`. **Do not stop merely because a count
is `0`.**

⚠ Round 4 measured why: against this repo today `open_prs` returns `0 / err: None` and that is the
**correct answer** — there are genuinely no open pull requests — so v5's *"if either prints `0` with
`err: None`, stop"* halts the implementer on a working collector. The plan already makes exactly this
argument three tasks later for `no_entry_prs` (*"`0` is also the correct answer today, so the
falsifier is the only thing that distinguishes them"*) and did not apply it to the step in front of
it. **A count cannot discriminate "nothing" from "could not ask"; only the pair can.**

⛔ `no_entry_prs` is additionally verified in Task 6 Step 5, where a synthetic body makes a `0`
distinguishable from a `[]` on live data.

---

## Task 4: Render the page

**Files:** Modify `scripts/gen-dashboard.py`.

- [ ] **Step 1: The render helpers**


- [ ] **Step 2: `build`**


⚠ **The `{`/`}` escapes are load-bearing** — one f-string containing CSS; every literal brace is
doubled. An unbalanced brace is a `SyntaxError` at import time.

- [ ] **Step 3: The assembled self-test**


- [ ] **Step 4: `main`, which COMPOSES the page rather than writing the fragment**

`build()` returns a **fragment** — no `<!doctype>`, no charset, **no Ask tray**. `main` calls
`brief-compose.py` with `--out` and fails non-zero when the file is not written, copying
`scripts/gen-goals-page.py:487-498`. `--fragment-only` is the only way to emit the raw fragment.


- [ ] **Step 5: Run the plan's own checker — against the files you just wrote**

> ⛔ **RETIRED 2026-08-29 by backlog #70 — the command below now EXITS 1 and cannot be followed.**
> The tagged `<!-- file: … -->` blocks it assembled from were deleted with the rest of the
> duplicated source; a run at `d16dcd8` prints
> *no tagged Python blocks found — nothing to assemble*.
> **The live equivalent, and what CI runs, is:**
>
> ```bash
> python3 scripts/check-plan-code.py --mutate .
> ```
>
> It applies every entry in `scripts/mutations/*.json` to the **delivered** scripts, over a control
> proved green first. The paragraphs below are kept as the RECORD of why `--compare` existed — that
> reasoning is what `--mutate` inherits — not as an instruction to run anything.

This assembles both files from the blocks above, runs both suites, runs every mutation in the
manifest, **and diffs each assembled file against the one in `scripts/`.** It fails if any mutation
survives, is caught by a case other than the one it names, or **the file you wrote differs by a
single byte from the plan's blocks.**

⛔ **`--compare` is not optional here, and v5 omitting it was round 4's H1.** Without it the checker
works entirely inside a `TemporaryDirectory` written from the markdown: it never opens
`scripts/gen-dashboard.py` at all. v5 offered this step to the implementer as verification of *their
own work* and it verified **the document**. Mistype a line into the delivered file and v5's Step 5
still printed `OK`.

That is this session's own recurring defect — *a checker pointed at the wrong subject* — committed
while building the tool against it. `CLAUDE.md`: **"A script beats a claim only when it reads the
thing the claim is about. A green check over the wrong subject is an assertion in better packaging,
and more dangerous than prose, because nobody re-examines it."**

The evidence block now names its subject in its own output, so a bare run cannot be mistaken for a
compared one:

```
  subject: the PLAN'S COPY of the code. --compare was not given, so
           nothing here was measured against the files in scripts/.
```

- [ ] **Step 5a: Regenerate the Standing evidence block in the COMPARED form, and commit it.**

> ⛔ **RETIRED 2026-08-29 by backlog #70 — both commands below EXIT 1, for the same reason as
> Step 5, and the CI step they served no longer exists.** `--verify-evidence` is not run by CI;
> the evidence block under *Standing evidence* is now a dated record and is free to go stale, which
> was the entire point of #70. **Nothing here needs regenerating or committing.**

```bash
python3 scripts/check-plan-code.py \
  docs/superpowers/plans/2026-08-28-project-dashboard-plan.md --compare . --evidence
# paste the block over the one under "Standing evidence", then:
python3 scripts/check-plan-code.py \
  docs/superpowers/plans/2026-08-28-project-dashboard-plan.md --compare . --verify-evidence
```

⛔ **This step is not optional and it is not cosmetic — without it the CI step added in Task 6 is
red by construction.** The block committed today was generated *without* `--compare`, because
`scripts/gen-dashboard.py` does not exist until this task creates it; its subject line says so in as
many words. The CI step runs `--compare . --verify-evidence`, and a compared run produces a
different block. **The two must be brought into agreement here, at the first moment both files
exist.** Expected after the paste: `OK — compared + evidence-verified`, and the block's subject
reading `the plan's blocks, DIFFED against the delivered files` with both files `identical`.

⛔⛔ **AND rewrite the two commands printed under *Standing evidence* to carry `--compare .` in the
same edit.** They read `--evidence` and `--verify-evidence` with no `--compare`, and **the evidence
block is invocation-specific**: the moment this step regenerates it in compared form, those two bare
commands exit 1 and print *"the pasted evidence block is STALE"* about a block that is perfectly
fresh.

**A falsifier that fires unconditionally is worse than none** — the first person to run it learns the
check lies, and stops reading it. That is round 4's B1 inverted, and round 5 (H4) caught v6
introducing it while fixing B1. **Both invocations must name the same mode as CI, or the freshness
check is theatre.**

- [ ] **Step 6: Generate and look at it**

```bash
python3 scripts/gen-dashboard.py && python3 scripts/explainer-serve.py
```

Confirm **on the page**: the entry with its id; the fold opens; a zero-commit day with an entry is
distinguishable **with the mouse elsewhere**; a day with commits and **no** entry is marked; clicking
a bar lands on that day; the **Ask tray** is present; `/latest` still points at the newest briefing.

⚠ Check `document.hidden` first — a backgrounded tab has no geometry.

---

## Task 5: Folds survive live reload

**Files:** Modify `scripts/explainer-serve.py`.

- [ ] **Step 1: Confirm it is broken.** Open a fold, `touch` the page, watch it close.

- [ ] **Step 2: Extend `RELOAD_JS`** — save and restore `<details>` open state, keyed on `d.id`
**only**. An index key shifts when a new entry is appended at the top, so the restore would work when
the page had not changed and misapply itself when it had.

```javascript
  var DKEY = 'explainer-details:' + here;
  function saveDetails() {
    try {
      var open = [];
      document.querySelectorAll('details[id]').forEach(function (d) {
        if (d.open) open.push(d.id);
      });
      sessionStorage.setItem(DKEY, JSON.stringify(open));
    } catch (e) {}
  }
  function restoreDetails() {
    try {
      var raw = sessionStorage.getItem(DKEY);
      if (!raw) return;
      sessionStorage.removeItem(DKEY);
      var open = JSON.parse(raw);
      document.querySelectorAll('details[id]').forEach(function (d) {
        if (open.indexOf(d.id) !== -1) d.open = true;
      });
    } catch (e) {}
  }
  restoreDetails();
```

- [ ] **Step 3: Rows that can fail** — COUNT, not presence, since `"restoreDetails()"` is a substring
of `function restoreDetails()`:

<!-- illustrative: assertion rows added to scripts/explainer-serve.py's OWN suite, not to a file this plan assembles -->
```python
        case("reload client defines and CALLS saveDetails",
             lambda: RELOAD_JS.count("saveDetails()") >= 2)
        case("reload client defines and CALLS restoreDetails",
             lambda: RELOAD_JS.count("restoreDetails()") >= 2)
        case("reload client keys folds on id, never on position",
             lambda: "details[id]" in RELOAD_JS and "String(i)" not in RELOAD_JS)
```

- [ ] **Step 4: Run, then MUTATE.** Delete the `restoreDetails();` call, leaving the definition; the
row must go red. **These rows only assert that text was typed** — Step 5 is the real test.

- [ ] **Step 5: Two folds open, `touch` the file, both still open.** Then commit.

---

## Task 6: The skill, the hook, and the wiring that makes the gate real

- [ ] **Step 1: Register the skill in `PAGE_SKILLS`** (`scripts/check-explainer-delivery.py:53`).
⚠ This check **cannot enforce its own list** — an absent skill is invisible to it.

- [ ] **Step 2: Write the skill at `.agents/skills/`, with a symlink**

```bash
mkdir -p .agents/skills/dashboard
ln -s ../../.agents/skills/dashboard .claude/skills/dashboard
ls -l .claude/skills/dashboard        # must print '-> ../../.agents/skills/dashboard'
```

The SKILL.md instructs: append one block, never edit an existing one; `[needs-you]` only when a
decision is genuinely waiting; clear one with a **later** `[resolved: YYYY-MM-DD/N]`, reading the id
**off the page**. Regeneration is one command — `python3 scripts/gen-dashboard.py` — which composes
and writes the page and exits non-zero if it does not. **No `mv` glob.**

**For serving, the tray, the push loop and verification, follow
`.agents/skills/shared/explainer-delivery.md`.** Cite it; never restate it.

- [ ] **Step 3: `check-explainer-delivery.py` and `check-docs.py` both rc=0.**

- [ ] **Step 4: The regen hook, and its registration**

⚠ **A hook script with no entry in `.claude/settings.json` never runs**, and it exits 0
unconditionally so there is no signal either way. Model it on
`.claude/hooks/regen-goals-page.sh`, match only `docs/dashboard-entries.md`, and register it in the
existing `PostToolUse` → `"Edit|Write"` array.

**Then prove it fires**: append a whole throwaway `## <date>` **block** with the Edit tool and
confirm the turn prints `↻ dashboard regenerated`. ⚠ A bare *line* would become part of the previous
entry's text; append a block and remove it afterwards.

- [ ] **Step 5: Wire the ratchet into CI — this is what makes §7 real**

```yaml
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
```

```yaml
      - name: gen-dashboard self-test
        run: python3 scripts/gen-dashboard.py --self-test

      - name: check-dashboard-entry self-test
        run: python3 scripts/check-dashboard-entry.py --self-test

      # --compare is what makes this step mean what its name says. Without it the
      # step measures the plan's COPY of ~1,100 lines and never opens the files CI
      # ships; the first bug fixed in scripts/gen-dashboard.py would leave the plan
      # green while the mutation evidence described a file that no longer exists in
      # that form. Round 4, H1.
      # --verify-evidence is the other half. The block is GENERATED, which round 4
      # proved buys provenance and not freshness: it was generated once at v4 and
      # described a run two versions old. CI is where "regenerate it" stops being a
      # rule somebody has to remember.
      - name: the plan's code and the DELIVERED scripts are the same, its mutations are caught, and its evidence is fresh
        run: |
          python3 scripts/check-plan-code.py \
            docs/superpowers/plans/2026-08-28-project-dashboard-plan.md \
            --compare . --verify-evidence

      - name: dashboard entry ratchet
        if: github.event_name == 'pull_request'
        env:
          BODY: ${{ github.event.pull_request.body }}
        run: |
          printf '%s' "$BODY" > /tmp/pr-body.md
          python3 scripts/check-dashboard-entry.py \
            --base "origin/$GITHUB_BASE_REF" --pr-body-file /tmp/pr-body.md
```

⛔ **`fetch-depth: 0` is the fix; a bespoke `git fetch` is not.** `actions/checkout` takes depth 1 on
the synthesised merge ref, so `HEAD` is a graft with no merge base:

```
fetch_rc=0
CANNOT RUN — git diff exited 128: fatal: origin/master...HEAD: no merge base
ratchet_rc=2
```

An explicit refspec creates `origin/master` and **still leaves that error** — it fixes the symptom a
review reported, not the outcome. Measured: full history costs **~0.85s and ~3.7MB** over 1,398
commits, and nothing else in CI reads git history.

**Also verify `no_entry_prs` here**, now that both files exist — once for `no-entry: 0 err: None`,
then again with the gate file moved away, which must print
`no-entry: None err: could not load the gate's exemption reader: …`. **If the second prints `0`
with `err: None`, the loader is swallowing the failure — stop.** `0` is also the correct answer
today, so the falsifier is the only thing that distinguishes them.

⚠ **The reader is resolved LAZILY, and that is what makes this falsifier reachable.** Bound at
import time it raised `FileNotFoundError` before `no_entry_prs` could return anything, so the whole
page failed to render over a section that is allowed to say *"could not check"* — and the stated
expected output above was unreachable. The GRAMMAR is still imported eagerly, because without it
nothing can parse at all; only the exemption reader degrades.

**Then falsify the ratchet in CI, not locally.** Open the PR with no entry, confirm **red**, add the
entry, confirm green.

- [ ] **Step 6: Pointer rows and the roadmap**

Add to `docs/dev-process.md`'s "What is mechanically enforced" table:

| Check | Enforces |
|---|---|
| `scripts/check-dashboard-entry.py` | a branch that changes tracked files records a dashboard entry, or declares `NO-ENTRY: <reason>` — which the dashboard then **displays**. Owns the entry-header grammar the page imports (`--self-test`) |
| `scripts/gen-dashboard.py` | the dashboard page is derived, never hand-edited; composed through `brief-compose.py` so it cannot lose its Ask tray (`--self-test`) |
| `scripts/check-plan-code.py` | a plan's code blocks ASSEMBLE and run, every mutation it declares is caught by the case it names, the DELIVERED scripts match the plan byte-for-byte (`--compare`), and its evidence block is not stale (`--verify-evidence`) (`--self-test`) |

⚠ **Re-measure the line budget with `wc -l` first, and know that it is tight.** Measured 2026-08-29:
`docs/dev-process.md` is **214** lines against `scripts/check-docs.py`'s budget of **220** — three
pointer rows leave **three lines of headroom**, and the third row above is long enough to wrap. If it
does not fit, the fix is a shorter row, not a bigger budget.

**UPDATE** the existing `## Project dashboard` section in `docs/roadmap-to-launch.md` — tick the
steps and refresh the status line. **Do not add a section**; one already exists.

- [ ] **Step 7: Commit and open the PR**

```bash
git log --oneline origin/master..HEAD      # confirm the branch carries ONLY this work
git push -u origin <branch>

# WRITE the body first. The only other /tmp/pr-body.md in this plan is created by the
# CI snippet in Step 5, inside the runner — it does not exist on your machine, and
# `gh --body-file` against a missing path fails at the last step of the last task.
cat > /tmp/pr-body.md <<'EOF'
<the PR description — anything longer than a line goes in a file, never a -m argument>
EOF
gh pr create --title "..." --body-file /tmp/pr-body.md
```

**Acceptance criteria — all five observable, or it is not ready:**

1. The ratchet has been **seen to refuse** on GitHub, not only locally.
2. The regen hook has been **seen to fire** on a real store write.
3. The served page has its **Ask tray**.
4. `check-docs.py` and `check-explainer-delivery.py` are green.
5. **`check-plan-code.py --compare . --verify-evidence` exits 0** — every declared mutation
   caught by the case it names, the delivered scripts **byte-identical** to the plan's blocks, and
   the Standing evidence block **exactly what that invocation produces**. The block must read
   `subject: the plan's blocks, DIFFED against the delivered files` with every file `identical`;
   anything else, including the `--compare was not given` line, fails this criterion.
   *(Criterion 5 replaces "their mutation checks were run", which was satisfied by running them and
   ignoring the result — a checkbox with no observation that could fail it. **Round 4 then found it
   was still satisfiable by a plan that had drifted from the code**: without `--compare` the check
   never opened `scripts/`. FAILS IF: `scripts/gen-dashboard.py` is edited without the same edit
   landing in this plan's blocks.)*

**Merging is a human gate. Do not merge.**

---

## Mutation manifest

Run by `scripts/check-plan-code.py`. Each must go **red via the case it names**; a survivor, or a
mutation caught by a different case, fails the check.


---

## Self-Review

⚠ **Read this sceptically.** v1's asserted *"every row has a case"* where one falsifier had neither
code nor case; v2's carried a ✅ on §9 for an alarm that was never built, and a ✅ on §4 for "four
cases" when half of §4's sources had none. **A self-review fails in the direction self-reviews
always fail — toward believing the mapping rather than running it.** Every ✅ below was mutation-
tested: the behaviour was broken and the named case was watched going red.

| Spec | Where | Checked by |
|---|---|---|
| §3 in-scope list | Tasks 2–4 | ✅ glossary now built and asserted on its **content**, not the word (the CSS rule `#glossary` matched, so the whole section could be deleted and the case still passed) |
| §4 what-needs-you | Task 4 | ✅ store half **and** the `gh` half — v2 had no case passing a non-empty PR list, so half of §4 could be deleted silently |
| §5 the chart | Tasks 3–4 | ✅ buckets, oldest-left direction, the under-count sentence, and the bar→entry anchor; **✗ the "control to widen the window" is still a CLI argument** — see Gaps |
| §6.1 rendered once, marked bars | Task 4 | ✅ both marks asserted on **sighted output only** — hover text and screen-reader labels excluded |
| §6.2 grammar | Tasks 1–2 | ✅ every row, including the unknown-resolve-id falsifier, two `[resolved:]` flags, the missing space, the empty title, tie order, ordinal stability, and "in place" on the order the store **actually uses** |
| §7 the gate | Tasks 1, 6 | ✅ verdict cases + controls A–F; **display** built; CI wiring is Task 6 Step 5 and is an acceptance criterion, not an assumption |
| §9 checks | Tasks 1, 4, 5 | ⚠ **PARTIAL — one ✅ covered five bullets of unequal standing.** Bullet 2 (the commits-with-no-entry alarm) is built and mutation-tested. Bullet 4 (a resolved item leaves §4 **and stays in §6**) has a case for the leaving half and none for the staying half — filtering cleared entries out of *What changed* is green. Bullet 5 (folds) the row below downgrades to *partial*. **Bullet 1 — "the page names the last date an entry was written" — is NOT BUILT**: `build()` renders no such element, a reader infers it from the first `<h3>`, and an empty store says "No entries yet". Round 4's M5, and the third round in which a Self-Review row claimed coverage it did not have |
| §10.1 folds | Task 5 | partial — three text-shape rows that go red when the call is deleted, plus a manual two-fold check. **No automated behavioural test**; see Gaps |
| §10.2 store created | Task 2 Step 5 | ✅ Step 6 parses the real file |
| §10.3 `PAGE_SKILLS` | Task 6 Step 1 | ✅ via `check-explainer-delivery.py`, which **cannot enforce its own list** — stated in the step |
| §10.4 `gh` failure | Tasks 3–4 | ✅ **now automated, not only manual.** v5's ✅ rested on the Task 3 falsifier alone: a **human step**, covering two of the four collectors, and blind to unparseable `gh` output entirely. v6 stubs `subprocess.run` in the suite, so a missing binary, a non-zero exit and unreadable JSON each have a case and a declared mutation. The manual falsifier stays — it is the only thing that exercises the real binaries |

**Gaps, stated rather than hidden — five.**

1. §5's *"control to widen the window"* is a `--window` **argument**, not an in-page control.
2. §9's affordance probe is inherited from `.agents/skills/shared/explainer-delivery.md` §5b.
3. **Task 5 has no automated test of the actual behaviour.** Three static rows plus a human opening
   two folds is all a check of a JS string can do.
4. **`no_entry_prs` is bounded at 40 merged PRs** and depends on `gh`. An older exemption stops
   being displayed — a silent horizon, named here.
5. **The gate cannot see a missing title.** `header_error` is shared, so parser and ratchet agree on
   every *header* shape; but a well-formed header over an empty body is malformed to the page and
   invisible at the diff level. Perfect agreement is impossible there, so it is stated instead of
   claimed away — which is what v2 did.

**Type consistency.** `parse_entries` returns dicts whose `resolves` is a **list**; `unresolved`,
`bucket_days` and `build` all iterate it as one. The dependency is one-way: `gen-dashboard.py`
imports the grammar and `exemption_reason` from `check-dashboard-entry.py`, never the reverse, and
the gate is built first so no step depends on a file a later task creates.

**Placeholders:** none.


## What v2 changed

Grouped by the review finding that forced it. Nothing here was found by re-reading the plan; every
item came from running it.

| # | Change | Task |
|---|---|---|
| B1 | The Task 4 falsifier could not fire (`git stash push` on a committed file is a no-op) **and the plan told the implementer to read its success as failure**. Replaced with scratch-repo controls A–E, one of which removes the entry from the branch diff — the only input the check reads | 4 Step 6 |
| B2 | `build()` returns a fragment; v1's default `--out` wrote it straight to the served page, losing the Ask tray and the charset silently, and the regen hook would have done it on every entry. `main` now calls `brief-compose.py` and fails non-zero | 3 Step 5 |
| B3 | `[resolved:]` naming an unknown id was accepted — silent in the worst direction, leaving an item on "What needs you" forever with no diagnostic. Added a second parser pass | 1 Step 3 |
| B/H | The skill was to be created at `.claude/skills/dashboard/` as a real directory, failing two checks. Moved to `.agents/skills/` + symlink | 6 Step 2 |
| B/H | The ratchet was never wired to a PR body, so it shipped a tested script and not a gate. Wired, with an injection-safe body path, and made an acceptance criterion | 6 Step 5 |
| H1 | §7 requires `NO-ENTRY:` to be **displayed**; nothing rendered it, which is the mechanism by which the gate hollows out leaving no trace. Added `no_entry_prs` + a page section | 2, 3 |
| H3 | A malformed block always rendered at the very bottom, and the case named "rendered in place" asserted only that the string appeared somewhere | 3 |
| H4 | The zero-commit "marked" bar was marked only inside a visually-hidden span — pixel-identical on screen | 3 |
| H5 | A `gh` failure blanked "What needs you", discarding needs the local store knew — in exactly the scenario the page exists for | 3 |
| M1–M8 | Entry ids rendered; duplicate DOM ids removed; same-date ties keep file order; `unresolved` enforces "later"; the hook became code plus registration; Task 5's rows can now fail; folds key on stable ids; `##` with no space is no longer silently dropped | 1–5 |
| L1–L7 | Expected counts removed from every step (v1 said `19/19`, actual `18/18`); untitled entries rejected; `gh` output shape-checked; fenced `NO-ENTRY:` ignored; exempt paths matched as paths; a non-positive window refuses; pointer rows added | all |
| — | The roadmap has no dashboard entry at all. Added | 6 Step 6 |

**Two of v2's own defects were found by running v2, not by reading it** — recorded because they are
the argument for the method, not incidental:

1. The new pass-2 guard was written `if e["error"] or not e["resolves"]`, which treats `""` — the
   flag declared with nothing after it — as "no flag at all". The case asserting `[resolved: ]` is
   malformed **failed**. `resolves` is three-valued; a falsy test collapses two of the three.
2. Control D was written without `mkdir -p docs`. Control C's `git rm` had removed the last file in
   `docs/`, git removed the directory, the `printf` failed, nothing was committed — and D **still
   printed `REFUSED`**, because there was no entry at all. It passed without ever exercising the
   rule it names. Fixed, and paired with control E so that D alone cannot look convincing.

Both are the same shape as B1 and as `docs/portable-practices.md` §17: a check that reports success
about a subject it never reached. Writing that rule into the Global Constraints did not stop it
happening twice on the next page. **Only running it did.**

### v2.1 — a third, found by attacking v2's own new code before the reviewers saw it

Round 1's lesson was *execute the material*, so before dispatching round 2 I ran v2's additions
against their edge cases rather than re-reading them. `_ordered()` held (malformed block first,
last, several consecutively, entire file malformed — all render in place) and pass 2 held. The
exemption reader did not:

| Probe | v2 did | Should |
|---|---|---|
| `<!--`…`NO-ENTRY: x`…`-->` | **exempted the branch** | ignore |
| `    NO-ENTRY: x` (4-space indent) | exempted | ignore — Markdown code block |
| ` ``` ` opened, `~~~` "closing" it | read the line after as a declaration | ignore — a fence closes only with its own character |

**The HTML-comment case is the one that mattered.** GitHub pull-request templates put their
instructions inside `<!-- ... -->`. A template that documented this very escape hatch would have
silently exempted every branch that used it — the gate would have reported success on every PR
while enforcing nothing, and the dashboard's exemption list would have shown it happening, which is
the only reason it would ever have been caught.

**Why this is not Blocking:** it is latent, not active. Measured 2026-08-28 — this repo has **no**
`.github/PULL_REQUEST_TEMPLATE`, and PRs #170–#173 contain zero HTML comments. Nothing is exempt
today that should not be.

`exemption_reason` now tracks fences by their own character, honours the 4-space rule, and skips
HTML comments across line boundaries; 11 new self-test rows cover all of it, including the three
constructs that must **still** be read as real declarations (after a closed comment, after a closed
fence, and a 3-space indent). Re-verified after the change: generator self-test green, gate
self-test green, controls A–E unchanged, and end-to-end a commented-out `NO-ENTRY:` now refuses
while a real one passes.

A fourth, smaller: pass 2 said *"names no entry in this file"* even when the entry existed and was
merely unparseable, sending the author to hunt for a typo that was not there. It now distinguishes
the three cases.

---

## Round 2 — Codex half, and the thing it caught me doing

`docs/reviews/plan-project-dashboard-r2-codex.md`, against `4077817`. **NOT CONVERGED**: 3 Blocking,
2 High, 2 Medium. All seven are addressed below; every fix was re-run, not reasoned about.

### ⛔ The finding that matters most is about the VERIFICATION, not the plan

**Blocking — `gen-dashboard.py --self-test` FAILS.** The case
`case("gh failure says could not tell", "could not tell" in html_err.lower(), True)` asserts a
string the renderer stopped emitting when H5's fix reworded it to *"I could not **also** check open
pull requests"*. A stale assertion against live code — ordinary enough.

**What is not ordinary is that I had run this and reported 55/55.** Transcribing the plan into a
scratch file, I wrote `"could not" in html_err.lower()` — dropping one word — and the weakened
version passed. Codex transcribed faithfully and got `54/55`.

So the green I reported was measured against **an assertion I had softened while copying it**. This
is `docs/portable-practices.md`'s *test harness can launder failures*, committed by the author of
the section warning about it, one commit after writing it. **A transcription is not a copy unless
it is diffed.** The case now asserts the contract — an unchecked source is announced as
`NOT CHECKED` and its reason is surfaced — rather than one version's wording.

### The rest

| Sev | Finding | Fix |
|---|---|---|
| **B** | Task 2 Step 6 verifies `no_entry_prs()`, which imports `check-dashboard-entry.py` — a file **Task 4 creates**. The stated expected output cannot occur in task order | The check moved to **Task 4 Step 6a**, plus a falsifier that hides the gate file and requires a loud `CANNOT RUN` |
| **B** | `set -e` at the top of the Task 4 controls **kills the script at Control A**, whose whole purpose is to exit 1. It never printed a verdict line and never reached B–E | `set -e` removed, with the reason stated so nobody restores it |
| **H** | `git fetch --no-tags --depth=200 origin master` **exits 0 and creates no `origin/master`** on a shallow branch-only checkout, so the CI ratchet cannot run | Explicit refspec `+refs/heads/X:refs/remotes/origin/X`. **Reproduced and re-verified here**: bare form → `origin/master MISSING`, `diff rc=128`; refspec form → ref created, diff clean |
| **H** | `NO-ENTRY:` inside an HTML comment exempts the branch | **Already fixed in v2.1**, independently. Two reviewers reaching the same defect from different directions is the strongest signal available that it was real |
| **M** | A ` ``` ` fence treated as closed by `~~~` | **Already fixed in v2.1** |
| **M** | The parser comment says a spaceless `##2026-08-28` "must become a MALFORMED entry"; the code accepted it as ordinary, and a self-test row asserted the accepting behaviour | The comment was right. `HEADER` now requires the space, the entry is malformed with a diagnostic naming the space, and the gate's `_ADDED_ENTRY` requires it too — so the two can no longer disagree about what an entry is |

**Re-verified after all seven, not assumed:** generator **58/58**, gate **32/32**, controls A–E run
to completion (`A rc=1`, `B rc=0`, `C rc=1`, `+## not-a-date` present, `D rc=1`, `E rc=0`), and the
CI refspec reproduced end to end.

**Two Codex findings were things v2.1 had already fixed**, which is worth noting rather than
glossing: it reviewed `4077817`, and v2.1 landed as `7ce2ac6` while it was running. The overlap is
confirmation, not waste.

**Still NOT CONVERGED, and the Claude half of round 2 has NOT run.** Round 1's two halves overlapped
on 2 of ~26 findings; one reviewer is not the gate. That gap is the next action, and it is recorded
rather than papered over.

---

## v3 — round 2's Claude half, and the task reorder it forced

`docs/reviews/plan-project-dashboard-r2-claude.md` — **2 Blocking, 8 High, 6 Medium, 5 Low, NOT
CONVERGED.** Twenty-one findings, of which **none** duplicated the Codex half and **one** overlapped
the coordinator's mutation pass. Two rounds now say the same thing: a single reviewer is not the gate.

### The two Blocking

| | |
|---|---|
| **B1** | The CI ratchet **still could not run**. v2.2's refspec created `origin/master` and left a second error behind it — `actions/checkout` takes depth 1 on the synthesised merge ref, so `HEAD` is a graft with **no merge base**. Same `ratchet_rc=2`, different sentence. It had been verified against the *symptom the previous round reported* rather than the *outcome*, in a scratch repo that was not shallow and therefore could not observe it. **Fixed with `fetch-depth: 0`** — measured at ~1.2s and ~4MB over 1,398 commits, with nothing else in CI reading history |
| **B2** | Task 4's Step 1 block had no `import re`, so Step 2's expected `NotImplementedError` was a `NameError` and Step 4's green was unreachable. v2.1 added `FENCE` above the block that imported `re`; both prior reviewers assembled the **final** file and never executed the intermediate states the task prescribes |

### The reorder, and why it was not optional

H1 measured **five header shapes** where the ratchet and the parser disagreed, while v2.2's own text
claimed *"they can no longer disagree"* — v2.2 had closed exactly the two shapes Codex named.
Instance-not-class, answered this time with a run rather than a recollection.

The fix is one grammar, owned by the gate and imported by the page. **But that makes the parser
depend on a file the gate task creates** — which is the very defect B2 and H8 filed. Fixing one
finding would have reintroduced another.

**So the gate is now Task 1 and the parser Task 2.** Considered and rejected: a third shared module
(more concept than the problem needs), and inverting the import so the gate depends on the generator
(a gate must never import the thing it guards).

### The rest

| Sev | Finding | Fix |
|---|---|---|
| H2 | §9's alarm — *every day with commits and no entry is visibly marked* — was **not built, had no case, and its Self-Review row carried a ✅**. Bars measured byte-identical | Built, with a hatched bar and a gap mark, asserted on sighted output |
| H3 | Two `[resolved:]` flags on one header: the first silently discarded, `error: None` — verbatim the failure pass 2 exists to prevent, in the sibling case it did not consider | `resolves` is a list; every consumer iterates it |
| H4 | *"Rendered in place"* held only for a newest-**first** file. The store is newest-**last** by the plan's own Step 5, so on a real store the malformed block still fell to the bottom. **The certifying case was built on the one ordering where the bug is invisible** | `_ordered` splices a malformed block after whichever neighbour renders first — order-agnostic, verified under both orderings |
| H5 | The marked-bar row survived losing **both** on-screen marks, because it still compared `title=` and `aria-label=` | Compares the bar's own class and its child elements; hover text and aria excluded |
| H6 | The `gh` half of §4 had **no case at all** — every fixture passed an empty or `None` PR list | A case with a real open PR, asserted inside its own section |
| H7 | The indent rule was bypassable two ways: a **tab**-indented declaration, and the text before an HTML comment, which never ran through the check | Tabs count to the 4-column stop; the head runs through the same rule |
| H8 | *"Replace the direct call"* had a literal reading returning `([], None)` — a confident *"No branch has skipped its entry"* on every page — and Step 6a could not tell, because `0` is also today's correct answer | The finished function is shown; the check is paired with a falsifier that hides the gate file |
| M1–M6 | Ordering untested; a roadmap step duplicating work the same commit already did; a falsifier expecting output its own snippet cannot print; §3's glossary and §5's under-count sentence absent; dead bar links on days without entries; ordinals that shifted when a typo was repaired, silently rebinding a standing `[resolved:]` | all fixed and mutation-checked |
| L1–L5 | A cited line number off by one; a visible declaration after a closed comment; a row passing for an unrelated reason; chart direction untested; a verification step whose "scratch line" becomes part of the previous entry | all fixed |

### Three more found by attacking v3 itself, before any reviewer saw it

Mutation-testing the new suite — 19 mutations — caught three cases that could not fail for what they
named, **all written in the same sitting as the fixes they certify**:

1. The `§6.1` mark comparison read the **container's own class as a child element**, an artifact of
   the §5 fix that made the container tag vary. It passed with every visible mark deleted.
2. The glossary case matched the **CSS rule** `#glossary`, so the entire section could be removed.
3. The CRLF normalisation was **dead code** — `.strip()` already covered it. Removed rather than
   left as a line no test can reach.

**That is the fourth, fifth and sixth instance of one shape today**, after the falsifier that could
not fire, the transcription that weakened its own assertion, and the two vacuous regression cases.
The lesson is not "write better cases": it is that **the only thing distinguishing a real guard from
a decorative one is breaking the code and watching it go red.**

## v6 — round 4, both halves

Round 4 is the **fourth consecutive non-converging round**, which is `docs/dev-process.md`'s Phase 6
trigger. It is also the first *complete* round since round 2 — three of the last four had a half that
did not really run or was not really independent, so the count is inflated by process failures as
well as by defects. Read the trigger off the **cause**: rounds 1–2 found broken code; rounds 3–4
found the document wrong about its own checks. The code side is strong and stayed strong. What kept
failing was the prose around it, and v6 is the version that stops relying on prose for it.

**Its method is the bar for the next round.** It assembled the plan's code twice — once with the
plan's own `extract()`, once with an independent hand parser — and `diff`ed the two before believing
any green; ran controls A–F verbatim in a throwaway repo; and wrote **50 mutations the manifest does
not declare**, 42 against the plan's code and 8 against `check-plan-code.py` itself.

### The Blocking, and why the fix is a check and not a resolution

**B1 — the generated evidence block was stale.** Generated at v4, never regenerated, so under a v5
document it reported 25 mutations against 26 and 77 tests against 79. *Fourth round running that
what failed was the plan's account of its own verification — this time inside the mechanism built to
stop exactly that.*

The tempting reading is "generating was a mistake". It was not. **Generating bought provenance and
not freshness**, and a block headed `GENERATED` is read with more trust than typed prose, which makes
a stale one strictly worse than a typed one. So v6 does not add a rule saying *remember to
regenerate*; it adds `--verify-evidence`, which exits 1 when the pasted block is not what the current
document produces, and puts it in CI. Pointed at the v5 block it printed a diff naming `25 → 33` and
`77 → 89`.

### The six High

| # | Finding | Fix |
|---|---|---|
| **H1** | `check-plan-code.py` **never opens the delivered scripts** — everything happens in a `TemporaryDirectory` written from the markdown. Acceptance criterion 5, Task 4 Step 5 and the new CI step all said otherwise. *A checker pointed at the wrong subject — this session's own recurring defect, committed while building the tool against it* | `--compare DIR` diffs each assembled file against `scripts/` and fails on one byte, or on a file it cannot read. The evidence block now **names its subject**, so a bare run cannot be mistaken for a compared one. Step 5, the CI step and criterion 5 all pass `--compare`; new **Step 5a** regenerates the block in the compared form at the first moment both files exist |
| **H2** | The **whole impure layer was unguarded** — 15 undeclared mutations survived, 6 turning *cannot tell* into a silent pass. `collect()` and `main()` had no coverage at all; `return 2` → `return 0` makes the ratchet **fail-open** | `_impure_self_test` in the gate and a collector block in `gen-dashboard.py`, both stubbing `subprocess.run`. **7 new declared mutations**, each caught by the case that names it |
| **H3** | The checker's self-test had **no case for its primary job**. Three mutants passed 19/19: `rc != 0` no longer failing, `ok = not problems` → `ok = True`, and an unknown mutation target | Cases for all three, plus `--compare` and `--verify-evidence` coverage. **44 cases**, and the declared count is now checked against the real one — it fired on its author's first guess |
| **H4** | Task 1 Step 6's controls **report a pass when the gate script is absent**: every row prints `rc=2`, none prints `ok`, and the stop-condition is satisfied by a run that tested nothing | The block refuses to start without the file, and compares a full `want`/`got` vector instead of scanning for one token. Falsified both ways: `CONTROLS OK` with the gate present, `CANNOT RUN … NOT TESTED` without |
| **H5** | The **orange `needs-you` bar** — spec §5's primary chart signal — was built and no case could see it go | A third `_marks` comparison, plus a declared mutation |
| **H6** | Task 3 Step 3's stop-condition **fires on the correct answer**: `open_prs` returns `0 / err: None` against this repo today because there are genuinely no open PRs | Compare the **pair**, with and without the binaries. ⚠ The falsifier as first written hid `python3` along with `git`, so it could never run — fixed with an absolute interpreter path, measured |

### Medium and Low

- **M1** — `_self_test` was assembled **twice, byte-identical**, into the gate. Step 5 silently
  re-included all 74 lines of Step 4's block; Python keeps the second, so both suites were green
  either way, and `replace(…, 1)` meant any mutation anchored there landed on the **dead first
  copy**. The duplicate is gone; Step 5 now carries `_impure_self_test` instead.
- **M2** — Task 2 Step 2 told the implementer to write a test that does not exist until Task 4.
  Retitled to what the block actually is.
- **M3** — `verdict`'s three-valued `reason`: both branches return `1`, so deleting the empty-reason
  branch was green. The **message** is now asserted, with a mutation.
- **M5** — §9's row carried one ✅ over five bullets, one of which (*the page names the last date an
  entry was written*) **is not built**. Downgraded to ⚠ PARTIAL, per bullet.
- **M6** — `<!-- illustrative -->` was an unbounded hiding vector: arbitrary broken code behind it
  passed. The tag now **requires a reason**, and `--evidence` prints what was excluded and why. ⚠ Both
  forms must stand alone on their line — a `.search()` reported the paragraph *describing* the
  convention as a defect, measured while adding the rule.
- **Lows** — the checker's `# 12 cases` against a 19-case suite (now derived and self-falsifying);
  `extract()`'s 3-tuple annotation on a 4-tuple return; a `TimeoutExpired` traceback where a
  `CANNOT RUN` belonged; the `dev-process.md` line budget named as **214 of 220** rather than left to
  be discovered at the gate; and a `gh --body-file` reading a path only the CI runner creates.

### Two defects v6 introduced and caught in itself

Both are the same shape as the ones above, which is the argument for running the checks rather than
trusting the edit:

1. The Step 3 falsifier emptied `PATH` to hide `git` and `gh` — **and hid `python3`**, so it died
   before testing anything. A falsifier that cannot run is H4 again, one file over.
2. `ILLUS_BARE` used `.search()`, so the sentence explaining the convention matched it and the
   checker failed on its own documentation.

### Deliberately NOT fixed

- **M4** — `collect()`'s three-dot `...HEAD` survives becoming `..HEAD`, and controls A–F structurally
  cannot see it because `master` never advances in them. Real, and the fix is a longer control repo;
  filed as work, not folded in.
- **U15/U16/U30/U31** — `main`'s compose path, the `--window < 1` guard, `--store`, and a frozen
  `today`. These need a subprocess and a written page to observe; **stated here as a gap rather than
  covered by a ✅**, which is what round 4 asked for.

**Round 5 should be SCOPED to `scripts/check-plan-code.py`.** H1 is a genuine design defect in the
tool — a checker verifying the wrong subject — and the tool grew a lot in v6: `--compare`,
`--verify-evidence`, the illustrative-reason rule, the result-line and colon parsers. The rest of the
plan has now survived four rounds, 34 declared plus 50 undeclared mutations, and controls A–F; a
fifth full reading would be the fifth reading of material that stopped yielding code defects two
rounds ago.

---

## v7 — round 5, SCOPED to the tool

Round 5 deliberately did not re-read the plan. The plan side had survived four rounds and stopped
yielding code defects two rounds earlier; **the subject was `scripts/check-plan-code.py`**, because
round 4's H1 was a design defect *in the tool* — it verified the plan's copy of the code and never
opened the files CI ships — and the fix, plus four other mechanisms, had landed with no independent
read.

That scoping was right. Both halves found real defects in the new code, and **not one finding was
about the plan's tasks.**

**Codex:** 1 misapplied Blocking, 3 High, 2 Medium, 1 Low, plus 6 self-test survivors.
**Claude:** 0 Blocking, 4 High, 6 Medium, 6 Low, plus **18 survivors out of 42 valid mutants** —
having written 44 undeclared mutations against the checker itself.

### What was actually wrong

| Finding | Fix, and how it was falsified |
|---|---|
| **`--compare` resolved the BASENAME.** Two tags — `one/m.py`, `two/m.py` — both compared to a single delivered `m.py` and both reported `identical`. A tag naming a path that exists nowhere reported `identical` too. **The exact defect `--compare` was added to fix, one layer in** | `--compare` now takes the **repo root** and resolves each tag whole. The plan's six call sites move from `--compare scripts/` to `--compare .`. Falsified: distinct tags now resolve to their own targets, and a same-basename plan passes |
| **The file tag was used as a path with no sanitisation.** `<!-- file: ../escape.py -->` wrote OUTSIDE the `TemporaryDirectory` — measured, the file landed in `$TMPDIR`. An absolute tag aimed at the compare root would make the checker **overwrite the delivered file and then certify it `identical`** | Absolute and `..` tags are refused. Reject, not sanitise: silently rewriting a tag makes the evidence describe a file the plan does not name |
| **`main()` had ZERO coverage** — and it is the only layer CI and acceptance criterion 5 read. `return 0 if ok else 1` → `return 0` left the suite at 44/44. The proposition the whole gate rests on, *that a non-zero exit follows from a failed check*, was asserted nowhere | Nine cases on `main`: green → 0, red → 1, missing plan → 2, no plan → 2, `--compare` at a non-directory → 2, stale evidence → 1, compared-and-matching → 0. **Round 4's H3 recurring one layer out**: the fix there added cases for `check()`, and nobody asked the same question of its wrapper |
| **A mutation that HANGS was recorded as `caught`.** `run_suite`'s own comment says rc 2 must not read as either verdict; its very next caller did `caught = rc != 0`. Two minutes of NOT CHECKED, printed into the evidence as proof a guard works | rc 2 is now a loud cannot-run. The timeout became a module constant so a case can reach it in 2s instead of 120 |
| **`expect` was a bare substring**, and `"does NOT count"` matched **7** case names. Combined with first-occurrence replacement it certified an *untouched* guard as caught | Each `expect` must resolve to **exactly one** red case, and it may now be a **list** when a mutation legitimately breaks several — more honest than naming one of five arbitrarily. **It immediately found 4 loose entries in this plan's own manifest**, all now explicit case sets |
| **An ambiguous mutation anchor** mutates the first match, which need not be the line it names | Refused. It found a real ambiguity in the checker's own `GOOD` fixture on its first run |
| **Two evidence blocks:** a stale one after a fresh one was never read | More than one marker is a failure, not a choice of which to believe |
| **Indented and info-string fences were invisible** — not counted, not reported, not excused | Reported. `FENCE` stays anchored at column 0 so an indented ``` inside a python block still cannot close it |
| **Only `ILLUS_*` were anchored.** `FILE_TAG` and `MUT_TAG` still used `.search()`, so a tag in a SENTENCE parsed as a tag | All four anchored. v6 fixed the instance it measured and left the class — the shape this project has now filed five times |
| Block order, the per-mutation source restore, the `[FAIL]` prefix, `count_drift`, the no-files guard, and the evidence block's own content were all unpinned | A case each |
| **The three modes were indistinguishable** from stdout and exit code, so a CI log could not show which subject ran | The final line names the mode: `OK — compared + evidence-verified: …` |

### The one I introduced while fixing round 4

**H4.** v6's Step 5a regenerates the evidence block in compared form — and the plan's own two
documented commands do not pass `--compare`. From the moment 5a lands, *the command the plan
advertises as its freshness falsifier exits 1 and reports a fresh block as STALE.* **A falsifier that
fires unconditionally is worse than none**: the first person to run it learns the check lies and
stops reading it. That is round 4's B1 inverted, introduced by B1's own fix. Step 5a now rewrites
those commands in the same edit, and the block says plainly that it is invocation-specific.

### Not fixed — three EQUIVALENT mutants, verified as such rather than waved away

`caught = rc == 1` → `rc != 0` (the `rc == 2` guard returns first, so rc ∈ {0,1} there);
un-anchoring `FENCE` (it is only ever used with `.match()`, which anchors at 0 regardless); and
`replace(find, repl, 1)` → replace-all (the ambiguity guard means only one occurrence can exist).
Each was checked by reading the path, not assumed.

**Suite: 44 → 92 cases.** Re-running round 5's survivor set: **13 of 16 caught, 3 equivalent, 0 real
survivors.**

### The shape worth remembering

Every High in this round is the same sentence with a different subject: **a check that reports
success over something it did not measure.** The basename collapse, the unsanitised tag, the
uncovered `main`, the hang read as a catch, the substring `expect`. v6 fixed that sentence for
`check()` and reproduced it five times in the code it added while doing so. The lesson is not to
write better checks; it is that **the question "what would this report if it were measuring nothing?"
has to be asked of every layer, every time — including the layer you just wrote to ask it.**

---

## v8 — round 6, the short scoped re-review

Round 6 was deliberately short and pointed at the eleven things round 5 changed, with both halves
told that *a short clean round is a real result*. It was not clean, and what it found is the most
useful result of the six rounds: **round 5's fixes were correct in verdict and incomplete in
mechanism, in the same shape as the defects they fixed.**

**Codex:** 0 Blocking, 0 High, 1 Medium, 1 Low, 6 survivors of 27.
**Claude:** 0 Blocking, **2 High**, 5 Medium, 5 Low, 9 genuine survivors of 60 (2 proven equivalent).

**No finding in either half was about the plan's tasks.** That is now two consecutive rounds.

### The two that mattered

**H2 — an escaping file tag was reported and then WRITTEN ANYWAY.** Round 5's fix added the problem
to `extract()` and left the write loop in `check()` untouched, so the checker still created the file.
An absolute tag pointing into the `--compare` root **overwrote a delivered file**, and the run that
did it printed `identical <path>` inside its own evidence block beside `FAILED`. The verdict was
right; the side effect was silent data loss in a tool whose stated premise is that everything happens
inside a `TemporaryDirectory`.

The reason nothing caught it is the sharpest sentence in the round: **the case that claimed to cover
it asserted against `extract()` — the layer that reports — and never ran `check()`, the layer that
acts.** Round 5's must-change asked for two things and one landed. There is now a single predicate,
`unsafe_tag()`, used both to report and to refuse, and a case that runs `check()` and asserts the
delivered file still holds its original bytes.

**H1 — the `expect` LIST form had ZERO coverage.** Round 5 added the mode, moved the plan's most
important mutations onto it (4 entries declaring 11 named guards, including its own headline example),
and asserted nothing about it. Deleting the list handling outright, and checking only its first entry,
both left the 92-case suite **and the real plan** green.

### And the rule itself was still not the rule

Codex found that round 5's "exactly one" guard is **cardinality-only**: it required exactly one
*match*, never that the match was the right case. Measured — an `expect` naming a **completely
unrelated** case, or a mere fragment of a name, still certified the mutation. The plan's rule is *"red
via the case it NAMES"*, and only equality says that.

`expect` is now an **exact** case name. Applying it exposed **19 of the 34 entries** as shortenings;
all are now spelled out, four as explicit sets where a mutation legitimately breaks several guards.
An empty list is refused rather than read as "no expectation".

### The rest

| Finding | Fix |
|---|---|
| **M3** `INVISIBLE_FENCE` rejected a **four-backtick fence** — the standard idiom for quoting a fence, already in this repo — and then demanded the fence quoted *inside* it be tagged, which is advice that cannot be followed. Also ` ```c++ `, ` ```{r} ` | Narrowed to the only hazard that matters: a **python** block the parser cannot see. Everything else is somebody else's fence |
| **M1** `MISSING` — the one compare verdict meaning *not checked* — was the only one with no assertion; the evidence block would print `identical` for a file that could not be opened | Pinned by value |
| **M2** the anchor-NOT-FOUND case passed via the wrong branch. With one edit a missing anchor and a survivor coincide; with **two**, the guard is the only thing between a typo and a mutation certified `caught` on its second edit | A two-edit fixture, asserting the message |
| **M4** "all four tag patterns anchored" was three-of-four | ⚠ The first version of this case did not diverge either — the prose tag needed a JSON block after it to be observable |
| **M5** `count_drift` was covered; the CALL that makes it load-bearing was not | `_drift_rc` — and see the gap below |
| **L1** the evidence block's per-file result line had no assertion | Pinned |

### The one thing NOT fixed, and why it is written in the docstring instead

`_self_test`'s last line is `return _drift_rc(__doc__, ok, fail)`. Deleting the drift check there is
**not caught**, and it cannot be: a suite cannot observe its own exit code without recursing into
itself. `_drift_rc` has three cases; its call site has none. **The honest closure is an external
observer** — a ratchet that runs `--self-test` and compares the printed count to the docstring, the
way `check-test-counts.py` does for the jest suite. That is recorded as a declared gap in the
script's own header rather than ticked, and it is the first finding in six rounds whose fix belongs
somewhere else entirely.

**Suite: 92 → 121 cases.** Re-running round 6's survivor set: **11 of 12 caught**, the twelfth being
that declared gap.

### Where this leaves convergence

Six rounds, and the severity curve on the *plan* went 3 Blocking → … → 1 Blocking → 0 → 0, with the
last two rounds finding nothing in it at all. The curve on the *tool* went 4 High → 2 High → and
round 6's Highs are both "the fix was half a fix", not new defects.

⚠ **The recurring shape is now precisely nameable, and it is not "bad checks".** It is: **a fix that
corrects the verdict without covering the mechanism.** H2 reported and did not refuse. H1 added a mode
and asserted nothing. M5 extracted a function and left its call. M4 anchored three of four patterns.
Each was a real fix that stopped one instance and left the class — six times, in six rounds, by the
same author. That is the finding worth carrying out of this slice, and it is in
`docs/portable-practices.md` territory rather than this plan's.

---

## v9 — the whole-branch review, and the two findings that were MEASURED

The branch review (2026-08-29, after Tasks 1–6 landed) returned **nothing Critical** and two
Important findings, both reproduced rather than argued. Neither is about the plan's prose; both are
in `scripts/gen-dashboard.py`, so the plan's blocks and the delivered file moved together and the
evidence block below was regenerated in the same edit.

**C1 — the generator imported the grammar's SYMBOLS but not its MEANING.** `parse_entries`'s flag
loop ended in a bare `else` that assumed every non-`needs-you` flag contains a colon. That was true
only by accident of `FLAG`'s current alternation — in `scripts/check-dashboard-entry.py`, a file
whose header says it **owns** the grammar and whose `_gate_module()` docstring invites you to extend
it there. Measured: adding one alternative to `FLAG` left the gate at **46/46 + 5/5**, fully green,
and made `parse_entries` raise `IndexError` on **every** render — so `gen-dashboard.py` exits
non-zero, `regen-dashboard.sh` prints *"the page is now STALE"*, and the reader sees a page that has
silently stopped moving. **This slice's own failure mode, reached through the seam built to prevent
it.** An unknown flag now errors that ENTRY; the page degrades one block instead of dying.

**C2 — `main()` had zero coverage**, which is round 4's finding about
`check-dashboard-entry.py`'s `collect`/`main` recurring in the sibling file the fix did not reach.
Four one-line mutations each survived a fully green **95/95**, and two of them are the exact promise
`.agents/skills/dashboard/SKILL.md` makes about the exit code — the promise
`.claude/hooks/regen-dashboard.sh`'s error branch rests on. All four are now declared mutations
caught by cases that name them.

**N1 — the re-review then found C1's own case exercising a MOCK of the seam, and saying it did not.**
The case swapped only this module's `FLAG`. But `header_error` is the **gate's** function and closes
over the **gate's** `FLAG`, which still rejected `[blocked]` at the header — so `err` was truthy and
overwrote the flag-loop's message before it was ever read. Measured, the two readings differ:

```
under the TEST's setup      : "unrecognised text in header: '[blocked]'"   <- header_error
with BOTH extended (REAL)   : "unrecognised flag [blocked]"                <- the new else
```

**Consequence: `else: entry["error"] = …` → `else: pass` SURVIVED at 102/102.** The case pinned
*"does not crash"* — which was the defect, so the fix was never unguarded — but not the graceful
degradation the same fix added. And the comment above it claimed `_flagged` was *"built through the
gate's own grammar rather than a literal, so this case exercises the real seam instead of a mock of
it"*, while being a hand-written literal duplicating the gate's pattern. **The comment asserted the
very property the case lacked** — which is the sentence this slice keeps rediscovering, this time
written by the author of the fix, in the same edit.

Now: `_flagged` is derived from `_GATE.FLAG.pattern`; **both** attributes are swapped so the two
readings agree by construction; the derivation is itself a case, because a no-op `replace` would
leave a pattern that does not know the flag and the case would pass for the wrong reason; and the
assertion is the **exact** degradation message rather than a substring both strings satisfy. The
`else: pass` form is declared as its own manifest entry. Re-measured: `else: pass` → **101/103**.

⚠ **The shape is the one this plan has now filed eight times**: a seam narrower than the prose
describing it. C1's `else`, C2's uncovered wrapper and N1's half-bound fixture are all *"a check that
reports success over something it never measured"*, each one layer out from where the previous fix
landed. N1 is the sharpest instance, because the thing that was wrong was **a comment claiming the
case was not a mock**.

---

### Standing evidence — GENERATED, not typed

OK — compared: 2 file(s), 43 mutation(s), 0 survivor(s)

Reproduce with `python3 scripts/check-plan-code.py <this file> --compare . --evidence`.

⚠ **This block is INVOCATION-SPECIFIC, and the command above must match the one that generated it.**
It is in the **compared** form as of Task 4 Step 5a (2026-08-29), which is the form CI runs: both
files now exist, so the block's subject is the delivered code and not only the document. The command
above, the one below, and the CI step all carry `--compare .` — if you find them disagreeing, the
disagreement is the defect, not the block.

**⛔ Do not paste this block by hand, and do not trust it because it says GENERATED.** Round 4's
Blocking was that this block *was* generated — at v4 — and then never again. By v5 it reported
**25 mutations against 26** and **77 tests against 79**: wrong, inside the one mechanism built to
stop this document being wrong about its own verification. **Generating bought provenance, not
freshness, and a `GENERATED` header is read with more trust than prose, not less.**

v6 closes that with a check rather than a rule:

```bash
python3 scripts/check-plan-code.py <this file> --compare . --verify-evidence   # exit 1 if stale
```

**FAILS IF:** any block above changes, any mutation is added or removed, or the invocation's
`--compare` mode changes, without this block being regenerated. Verified 2026-08-29 by pointing it
at the v5 block: it printed a diff naming `25 → 33` and `77 → 89` and exited 1.

**v5 was reviewed by both halves of round 4 (Codex 3 findings, Claude 1 Blocking / 6 High / 6 Medium
/ 5 Low, both NOT CONVERGED); v6 is the result and has NOT been reviewed.**
