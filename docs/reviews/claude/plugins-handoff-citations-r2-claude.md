# Round 2 — CLAUDE half — branch `plugins-handoff-citations` @ `7cf48d43`

⚠ **FILED LATE, AND WHY THAT MATTERS TO HOW YOU READ IT.** Rounds 2 and 3 were run with the Codex
half only — a coordinator lapse, not a `CANNOT RUN`. This is round 2's missing half, written against
round 2's subject (`7cf48d43`) while the worktree sits at `b972afee`, two folds later. So every
finding below is labelled with which of two things it is:

* **(a) MISSED IN `7cf48d43`** — present in round 2's subject, not reported by the Codex half, and
  still present at `b972afee`.
* **(b) THE FOLD GOT THE REPAIR WRONG** — round 2 or 3 reported it, `755c35a6`/`b972afee` repaired
  it, and the repair is incomplete or introduced something new.

**Verdict: 0 Blocking / 1 High / 4 Medium / 2 Low.** The High and two of the Mediums are in the
branch's own thesis — a document that prohibits a practice and then performs it, and an
enumeration whose *label* is wrong where its *arithmetic* is right. The two prior Codex halves
checked the arithmetic of both and passed them.

---

## Blocking

None established.

---

## High

### H1 — The branch removes four vendored line numbers and publishes **nineteen new ones**, and its flagship memory lesson states the prohibition absolutely while holding five of its own. **(a)**

The branch's thesis, in its own words
(`docs/memory/a-vendored-line-number-has-no-owner.md:25-27`):

> ⭐ **The fix is to REMOVE the number, not to update it.** Nothing here can hold a vendored line: no
> guard can watch it, and `npx skills@latest add` or a plugin bump invalidates it with no commit.
> Name the SYMBOL and give the command.

**MEASURED, over the non-review diff only** (`git diff 74a44551 7cf48d43 -- docs/ scripts/ .claude/
.agents/ ':!docs/reviews'`, added lines, pattern `:1[0-9]{3}(-1[0-9]{3})?`):

```
   4 :1171      3 :1666      3 :1571-1640      3 :1546
   2 :1164      2 :1153-1163    1 :1544          1 :1168
```

**19 occurrences, 8 distinct locators, all of them inside `session-start-hook.sh` — the same
vendored file whose four line numbers this branch exists to delete.** They are not confined to the
tech block of a dated record:

* `docs/memory/a-vendored-line-number-has-no-owner.md:5` publishes `:1171`, `:1666`, `:1571-1640`,
  `:1546` in its opening measurement, and `:37` cites `:1153-1163` **as a live pointer** — *"The
  claim came from a COMMENT in the same vendored file (`:1153-1163`), and that comment is stale."*
  That sentence sends a reader to a line range. It is the thing the file two paragraphs earlier
  says must never be written.
* `docs/process-rationale.md:366` cites **`.agents/skills/handoff/SKILL.md:13`** — a line number in
  a file that `docs/plugins.md`'s own layer table marks *"Layer 3 — Convenience — ❌ reverted"* by
  `npx skills@latest add mattpocock/skills`. By the branch's own classification that is a vendored
  file, and `:13` in it is the prohibited act committed in the paragraph that explains the
  prohibition.
* `docs/dashboard-entries.md:14847`, the **reader-facing** half, says *"The documents now name the
  thing to search for and leave the finding to the reader"* — 38 lines above a tech block
  (`:14885-14889`) that hands the reader six fresh locators.

⚠ **The defence, stated so it can be weighed rather than hidden.** A locator pinned to a named
version is arguably testimony, not a pointer: the memory file says *"Against the live **0.33.0**
hook"* and the dashboard says *"Measured against `remember` **0.33.0**"*. That distinction is
sound — and **it is never stated anywhere in the branch**. The prohibition is written absolutely
("Nothing here can hold a vendored line"), so the document's rule and the document's practice
contradict each other, in a file whose whole purpose is to be recalled and copied. A reader who
applies the lesson literally deletes the file's own measurements; a reader who copies its practice
keeps writing locators. Both readings are wrong, which is what makes this the file's defect rather
than the reader's.

**Verified accurate, which is the point.** I checked all eight: `:1164`, `:1168`, `:1171` (mode
gate, per-session, shared), `:1544`, `:1546` (hint condition and emit), `:1666` (`=== LAST HANDOFF
===`), `:1153-1163` (the stale comment, exact), and `:1571-1640` (delivery-record block) are all
correct against the 2,027-line 0.33.0 hook **today**. Accuracy is not the finding — ownership is.
The next `remember` bump invalidates all nineteen, and this branch has just finished establishing
that no guard in this repo can see it happen.

**Falsifier for the fix:** either (i) state the exception — *a locator under an explicit version pin
is a measurement and is allowed; an unpinned one is not* — and then make `a-vendored-line-number-has-no-owner.md:25-27`
agree with it and re-point `process-rationale.md:366` at `SKILL.md`'s symbol rather than its line;
or (ii) drop the locators from the two *lesson* documents and keep them only in the dated dashboard
record. After either, re-run the grep above over the whole non-review diff and the count outside
`docs/dashboard-entries.md` must be **0**.

**This is the shape round 1 already paid for once.** Round 1's own summary was *"the correction
repeated the defect one layer in"*. This is the third layer.

---

## Medium

### M1 — `docs/plugins.md:86-87`'s new clause **"NO hint means this rule's path"** is false in a configuration the plugin supports, and it replaced a sentence that was true. **(a)** and **(b)**

The ⛔ RULE box at `7cf48d43` (unchanged at `b972afee`):

> **If a session-start block prints `Write next handoff to: <path>`**, obey it — ⟳ **THREE triggers**
> (external, `per_session`, degraded); **NO hint means this rule's path**.

**MEASURED — probe C** (isolated tree: temp `HOME`, fresh git project, real hook, real
`CLAUDE_PLUGIN_ROOT`). User-global config `{"data_dir":"notes"}`, `handoff_mode` absent (so
`single`), main checkout, valid `session_id`:

```
hook stdout:  (no `=== HANDOFF ===` block, no hint line at all)
store created: <proj>/notes
REMEMBER_HANDOFF: <proj>/notes/remember.md
```

**No hint, and the path is not `.remember/remember.md`.** The mechanism is visible in
`lib-memory-dir.sh:255-268` and `lib-memory-context.sh:83-95`: `REMEMBER_DIR` is
`<project>/<data_dir>`, `REMEMBER_ROOT` is its *parent*, and the hint's first disjunct
(`session-start-hook.sh:1544`) is `REMEMBER_ROOT != PROJECT_DIR`. A one-level relative `data_dir`
moves the store while leaving `REMEMBER_ROOT == PROJECT_DIR`, so the hint stays silent over a
store that is not the one the rule names.

**Why this is the fold's defect and not only the subject's.** Round 1's M7 asked for the clause
that was deleted:

> Removed: *"It is absent in legacy mode by design."*

That sentence was **true** — absence of a hint does imply legacy mode (`REMEMBER_ROOT ==
PROJECT_DIR`). The fold answered M7 with a different claim — absence implies a *path* — and that one
is false under `data_dir`. ⟳ And round 3 then found **exactly this error** one file over, in the
refusal text, and `b972afee` fixed it there (*"which is NOT always the path above: a data_dir
setting moves it"*) **while leaving it standing in Layer 1**, the box `docs/plugins.md` itself
declares governs *"whatever the skill file says"*. An instance fix on the weaker layer; the
authority layer still asserts the thing that was measured false.

⚠ **Mitigation, stated rather than hidden.** The plugin's own `/remember` skill
(`skills/remember/SKILL.md:9`) documents the same fallback: *"If no `=== HANDOFF ===` block is
present, fall back to `{project_root}/.remember/remember.md`."* So obeying this clause is no worse
than obeying the plugin. The defect is that the plugin calls it a **fallback** — the hook's own
comment at `:1159-1161` calls it *"the /remember skill's own hardcoded legacy fallback"* — and
`plugins.md` promotes it to an assertion about where the file **is read**. That is the branch's own
category: a claim stated more confidently than it is true, in the one box whose job is to be
trusted without checking.

**Falsifier:** replace with *"no hint ⇒ legacy in-project store at `.remember/` (the default); if
`data_dir` is ever set, the store moves and only the hook knows where"*, or restore the
legacy-mode form. Re-run probe C: the box must not predict `.remember/remember.md` for that run.

### M2 — **"external"** is the wrong name for hint trigger 1, and the case it actually fires in is the one every review in this repo runs inside. **(a)**

Four sites in the subject say the first of the three triggers is an external store:

| site | wording |
|---|---|
| `.agents/skills/handoff/SKILL.md:17` | "External mode (**the store is outside the project**)" |
| `docs/plugins.md:86` | "THREE triggers (**external**, `per_session`, degraded)" |
| `.claude/hooks/enforce-handoff-path.sh:73` | "THREE things print it: **an external store**; …" |
| `docs/process-rationale.md:409` | "three hint triggers … : **external mode**, per-session, and degraded" |

The condition is not "external". It is `REMEMBER_ROOT != PROJECT_DIR`.

**MEASURED — probe B.** Default config (no `data_dir`, no `handoff_mode`), a **linked git worktree**
of a fresh project:

```
=== HANDOFF ===
Write next handoff to: <MAIN-CHECKOUT>/.remember/remember.md
```

The hint fires. The store is `<main checkout>/.remember` — **inside the project**, and the ordinary
legacy layout. The cause is `lib-memory-dir.sh:259-263`: `_resolve_memory_project_dir` keys the
store to the main checkout (plugin issue #56) while `PROJECT_DIR` is the worktree, so the two
disagree and trigger 1 fires with nothing external anywhere.

**MEASURED — probe D**, a second, structurally different in-project case: `{"data_dir":"a/b"}`,
single mode, main checkout → hint fires, path `<proj>/a/b/remember.md`. (Note the pair with M1:
`a/b` fires the hint, `notes` does not. The discriminator is the *depth* of the relative path, which
no document mentions.)

**MEASURED — the plugin agrees with me against the documents.** `doctor.sh`, same store both times:

```
CLAUDE_PROJECT_DIR=<main checkout>   → OK   Storage mode: legacy (in-project: <main>/.remember)
CLAUDE_PROJECT_DIR=<this worktree>   → OK   Storage mode: external (<main>/.remember)
```

**Why it matters here and not in the abstract.** This repo does its implementation and review work
in linked worktrees — this review is being written in one. So the first trigger's *common* case in
this repo is the worktree case, and all four documents tell the reader it means "the store is
outside the project". The *instruction* survives ("use that path — it is always the right one"), so
nothing is lost today; what is lost is a reader's ability to recognise their own situation, in the
one paragraph written for the moment they must.

**Falsifier:** name the condition rather than one of its causes — *"the resolved store's parent is
not this project directory: an external store, **or a linked git worktree**, or a nested relative
`data_dir`"*. Re-run probe B: the enumeration must predict a hint there.

### M3 — "Fifty lines" is **22**, and the figure is published in three documents. **(a)**

| site | claim |
|---|---|
| `docs/dashboard-entries.md:14868` | "**Fifty lines further down** the same file says so" |
| `docs/memory/a-vendored-line-number-has-no-owner.md:38` | "**Fifty lines down** the hook corrects itself" |
| `docs/process-rationale.md:414` | "**Fifty lines later** the hook corrects itself" |

**MEASURED** against the 0.33.0 hook. The stale comment is `:1153-1163` (the branch's own citation,
exact). The correcting comment begins at `:1185` — *"NOT withheld on degrade."* Every reading, and
the bound:

```
1163 (end of stale note)   → 1185 (start of correction)   =  22   ← the natural reading
1153 (start of stale note) → 1185                          =  32
1159 ("hint below is withheld") → 1196 ("The honest fix…")  =  37
1153 → 1199 (end of correction block)                       =  46   ← widest possible span
```

Fifty is wrong on all four, and the only one within 10% of it measures block-start to block-end,
which is not what "fifty lines down … corrects itself" says. The natural reading is out by **2.3×**.

This is the branch's own defect class — *a figure written for a reader who will not check* — in the
paragraph the branch added to explain that defect class. Neither Codex half checked it; both
verified the locators beside it.

**Falsifier:** say "twenty-two lines later" or "later in the same comment block". Re-measure
`:1163 → :1185`.

### M4 — The fold's new `doctor.sh` evidence is execution-directory-dependent and is quoted unqualified. Round 3 saw this and filed it under SOUND, so nothing folded it. **(b)**

`755c35a6` repaired round 2's M3/M5 by adding to the dashboard tech block
(`docs/dashboard-entries.md:14890-14892`):

> the plugin's own read-only `doctor.sh` reports `Storage mode: legacy (in-project)`

**MEASURED** (the two runs in M2 above): the same store yields `legacy (in-project)` from the main
checkout and `external` from a linked worktree. `doctor.sh`'s "Storage mode" is a statement about
the relationship between the store and the directory you invoke it from — not about the store. The
quotation names neither the directory nor that the answer depends on it, so a reader reproducing it
from a review worktree gets the opposite word and must decide which run was wrong.

Round 3's Codex half **measured exactly this** and placed it in *"Checked and found SOUND"*:
*"`doctor.sh` reports legacy storage from the main checkout; from this linked worktree it reports
the shared main-checkout store as external. The dashboard quotation needs that execution-directory
qualification."* A row that ends *"needs that qualification"* is a finding; filing it as SOUND is
why `b972afee` left the sentence untouched. (See *Where I disagree with the Codex half*, #3.)

**Falsifier:** add the directory — *"`doctor.sh`, run from the main checkout, reports …; from a
linked worktree the same store reports `external`, because the verdict compares the store to the
invoking project directory"*. Then both of my runs confirm the sentence instead of splitting it.

---

## Low

### L1 — The same directory is "~102 entries" in one document and "**104**" in another; the fold repaired one site. **(b)**

**MEASURED** at `b972afee`, with `docs/reviews/` excluded from the grep:

```
docs/process-rationale.md:394      "it holds ~102 entries, of which exactly one matches remember*"
docs/dashboard-entries.md:14892    "the store's **104** entries include exactly ONE matching remember*"
```

Both describe `<main checkout>/.remember`. My own count today: **104** top-level entries, exactly
one matching `remember*` (`remember.md`). Round 2's M3 named the dashboard's version of this
sentence; the fold corrected the dashboard and left `process-rationale.md` at the round-1 figure —
the shape the fold's own new comment in `scripts/check-handoff-path.py` names: *"a withdrawal has a
blast radius and mine kept stopping short of it."*

⚠ Worth saying plainly: both figures are perishable. The store accumulates `today-*.done.md`, so a
count of it is stale within a day. `~102` hedges; a bolded `**104**` does not. The durable claim is
the one both sentences already make — *exactly one entry matches `remember*`*.

### L2 — Two CI gates are RED at `b972afee` because of the missing halves, and this file clears only half of that. **(b)**

**MEASURED in the worktree, not piped** (`rc` read directly):

```
python3 scripts/check-review-rounds.py                                           rc=1
  ✗ plugins-handoff-citations round 2: only codex — claude neither ran nor recorded a `REVIEW GAP:`
  ✗ plugins-handoff-citations round 3: only codex — claude neither ran nor recorded a `REVIEW GAP:`

python3 scripts/check-review-recorded.py --base origin/master --pr-body-file <empty>   rc=1
  FAILED — 3 round(s) ran and guarded code was committed after every one of them.
  The closest (plugins-handoff-citations-r1-codex.verdict.json) never saw:
    .agents/skills/handoff/SKILL.md, .claude/hooks/enforce-handoff-path.sh, scripts/check-handoff-path.py
```

`origin/master` is `74a44551`, which confirms the base I diffed against.

So `755c35a6` and `b972afee` each committed a single-half round with no `REVIEW GAP:` line, and the
gate that exists for precisely that fired.

⟳ **RE-MEASURED after writing this file: `check-review-rounds.py` is now rc=0 — and it is NOT this
file alone that did it.** `git status` shows two untracked reviews, mine and
`docs/reviews/claude/plugins-handoff-citations-r3-claude.md`, which a second agent filed
concurrently while I was measuring. My own prediction was "2 failures → 1"; the observed result is
"→ 0", and the extra half is the cause. Recording the discrepancy rather than the prediction,
because a re-verification that reports what I expected instead of what happened is worth nothing.

**`check-review-recorded.py` is still red** and this file does not address it: guarded code
(`SKILL.md`, `enforce-handoff-path.sh`, `check-handoff-path.py`) was committed after every verdict,
so it wants a round against the current tree, or `NO-REVIEW:` in the PR body. I am reporting the
residue rather than leaving the coordinator to discover it from CI.

---

## Checked and found SOUND

Each row is something I drove, not something I read.

1. **`=== LAST HANDOFF ===` really is emitted ahead of identity and memory.** Isolated tree with
   sentinel content in `remember.md`, `identity.md` and `now.md`; hook stdout ordering:
   `=== LAST HANDOFF ===` → body → `=== REMEMBER ===` → `=== MEMORY ===` → `IDENTITY SENTINEL` →
   `NOW SENTINEL`. The subject's rewritten sentence — *"injected before identity and memory,
   specifically so it survives context-preview truncation"* — holds, by execution.
2. **Delivery is fingerprinted on CONTENT and is non-destructive.** Two consecutive runs on the same
   note: run 2 printed *"[already delivered 2 times since …]"*, the body again, and the file was
   still 14 bytes on disk. The record is `fingerprint=992893365-14` — a `cksum` of the content, as
   the subject's replacement sentence claims. The old wording ("fingerprinted and non-destructive")
   and the new ("fingerprinted on the handoff's CONTENT") are both true; the new one is more
   specific and loses nothing.
3. **The three-trigger arithmetic is right, even though its first label is not (M2).**
   `session-start-hook.sh:1544` is a three-way disjunction and I found no fourth. Driven:
   valid session id + `per_session` → `remember.sess-fff.md` (probe F); empty session id +
   `per_session` → shared path **plus** the degradation line, verbatim
   *"(handoff_mode is "per_session", but no session_id reached this hook -- writing to the shared
   file above, not a per-session one.)"* (probe E). Round 1's B1 correction is confirmed: the hook
   neither goes silent nor misleads.
4. **The refusal renders correctly and nothing in the new lines expands.** Replica tree, stub guard
   exiting 1, `TMPDIR=/SENTINEL_TMPDIR EDITOR=/SENTINEL_EDITOR`: **rc=2**, stdout **0 bytes**,
   stderr **30 lines**, `grep -c SENTINEL` = **0** (literal `$TMPDIR` and `$EDITOR` survive the
   unquoted heredoc), and no trailing whitespace on any rendered line. (Codex r2 reported 29 lines;
   the count includes `$VERDICT_OUT`, so it is stub-dependent and the two are not in conflict.)
5. **The handoff guard's declared falsifier actually fires.** Its own stated falsifier is *"SKILL.md
   stops naming `.remember/remember.md`"*. Driven on a copy of the subject tree: control
   (subject `SKILL.md`, 2 occurrences) **rc=0**; every occurrence rewritten to `.remember/handoff.md`
   → **rc=1** with the REVERTED message; pristine-upstream body → **rc=1**; restore → **rc=0**.
   `--self-test` **10/10** (7 text + 3 file cases, declared count matches `len(CASES)+3`).
   The rewritten `SKILL.md` keeps the guard green without weakening what it can detect.
6. **The removal of `=== HANDOFF === /` from the quoted hint loses nothing.** I checked whether the
   section header was load-bearing as a discriminator: `"Write next handoff to"` occurs **once** in
   the whole plugin's shipped code (`:1546`), and the `=== LAST HANDOFF ===` delivery block prints no
   similar line. The shorter quotation is sufficient.
7. **`docs/plugins.md` is 260 lines at all three commits** (`74a44551`, `7cf48d43`, `b972afee`), and
   `scripts/check-docs.py:193` sets the budget at 260. Net-zero was required and achieved; the
   dashboard's claim is exact. `check-docs.py` reports this as *tight*, not *ok* — a warning, not a
   block (its own self-test case at `:655` pins that behaviour).
8. **The fifth-site claim and its symlink cause.** `.claude/skills/handoff` → `../../.agents/skills/handoff`
   is a real symlink; `.agents/skills/handoff/SKILL.md:13` at `74a44551` is exactly the locator
   paragraph, authored in `24ff8694`. The count of five original sites holds.
9. **The hook's own figures.** 2,027 lines; `REMEMBER_HANDOFF` shared at `:1171`, per-session at
   `:1168`, mode gate `config_into HANDOFF_MODE ".handoff_mode" "single"` at `:1164`, hint condition
   `:1544`, hint emit `:1546`, `=== LAST HANDOFF ===` `:1666`, delivery-record block `:1571-1640`,
   stale comment `:1153-1163`. All eight correct. (That they are correct is H1, not a pass.)
10. **`MEMORY.md`'s two new rows are inside the file's own ~200-char limit at the subject** — 190 and
    172 characters (196 and 178 **bytes**; the commit body's "178" is the byte count of the second
    row). Round 1's L3 said both exceeded 200; at `55975f92` they were 229 and 209, so the round-1
    fold fixed it and L3 does not survive into round 2.
11. **Document-guard sweep, list taken from `.github/workflows/ci.yml` by grep rather than from
    memory: 53 invocations, 50 green.** The three reds are L2's `check-review-rounds.py` plus two
    environmental (next section). No guard is red because of this branch's content.
12. **`check-dashboard-entry.py --base origin/master`: rc=0**, *"ok — an entry block was added"*.
13. **`doctor.sh` is read-only with respect to the store** — its only removals are its own
    `_RESOLVE_ERR_FILE` temporaries (`:106`, `:235`). The dashboard's "read-only" is fair.

---

## CANNOT RUN

⛔ **Every row here is a FAILURE to validate. Treat each as NOT RUN, never as a pass.**

1. **`scripts/check-selftest-counts.py` → rc=1.** Names `check-plan-code.py` and
   `check-paid-caller-arrival.py`: *"--self-test exited 1 — its own cases are red, so its declared
   count proves nothing."* **Treat the declared-count ratchet as NOT RUN.**
2. **`scripts/check-plan-code.py --self-test` → rc=1, 175/178.** The three red cases are all one
   cause: `node_modules/typescript` is absent, so `HARNESS_TREE` is incomplete and the guard
   correctly refuses — *"TREAT THIS AS NOT CHECKED"*. Pre-existing, outside this diff (the brief says
   so and I confirmed the two files are untouched by the branch). **Treat the mutation harness as NOT
   RUN**, including `--mutate .`, which I did not attempt for the same reason.
3. **`check-review-recorded.py` and `check-dashboard-entry.py` were run with an EMPTY PR body**, not
   the real one — no PR exists for this branch. Their PR-body half is **NOT RUN**; only their
   diff-and-verdict half was measured.
4. **The DB-backed gates were not run at all** — `schema-gates.yml`'s fifteen gates need a Postgres
   container. Nothing in this diff touches schema, but that is an argument from the diff, **not a
   measurement**, and must not be read as those gates passing.
5. **Historical claims cannot be replayed from here.** The pre-0.33.0 hook's length, "three handoff
   docs accumulated in `$TMPDIR`", and *"this installation uses the ordinary mode **and always
   has**"* are unverifiable in this worktree. I can confirm the present state (all three config
   layers absent, `handoff_mode` resolving to `single`); I cannot confirm "always has", and the
   branch should not be read as having established it. ⚠ The subject is **right** not to claim a
   drift figure — that withdrawal is this branch's best single edit.
6. **My probes used the installed 0.33.0 plugin.** Every hook behaviour above is true of *this*
   install. I did not test another version, so nothing here bounds what a future `remember` does —
   which is H1's whole argument.

---

## Instruments

**Worktree** `…/scratchpad/wt-plugins` @ `b972afee`; **subject** `7cf48d43`, read via `git show`
rather than by checking it out, so no `git` write command was issued in the worktree or in the main
checkout. `origin/master` = `74a44551`, which is the diff base I used for "what this branch
changed" (the merge-base with `master`, `2413b003`, is older and drags in seven unrelated merged
commits — diffing from it would have put ~33k lines of other people's work in scope).

**1. The live-hook matrix (M1, M2, SOUND #1, #2, #3).** `…/scratchpad/hookprobe2/probe.sh`. Each run
gets its own `mktemp -d` **inside the scratchpad**, a redirected `HOME` (so no probe can reach the
reader's real `~/.remember`), a fresh `git init` project, real `CLAUDE_PLUGIN_ROOT`, and the
SessionStart payload on stdin. Six runs: A default/single/main (no hint, store `.remember`);
B default/single/**linked worktree** (hint → main checkout); C `data_dir=notes`/single/main
(**no hint**, store `notes`); D `data_dir=a/b`/single/main (hint, store `a/b`); E
`handoff_mode=per_session` with **no** `session_id` (hint → shared + degradation line);
F `per_session` with a valid id (hint → `remember.sess-fff.md`). Plus two ordering/fingerprint runs
for SOUND #1 and #2.

**2. The refusal render (SOUND #4).** `…/scratchpad/refusal2`: the subject's
`enforce-handoff-path.sh` copied beside a 2-line stub `scripts/check-handoff-path.py` that exits 1,
driven with the real PreToolUse JSON and sentinel `TMPDIR`/`EDITOR`. rc, stdout size, stderr line
count and sentinel leakage all read from the captured files, not from the terminal.

**3. The guard falsifier (SOUND #5).** `…/scratchpad/guardfals`: a 2-file tree
(`scripts/` + `.agents/skills/handoff/`) so `REPO_ROOT = Path(__file__).parent.parent` resolves
there and no file in the worktree was touched. Control proved green **before** each mutation and
restored green after.

**4. The guard sweep (SOUND #11, L2, CANNOT RUN #1-#2).** Invocation list extracted from
`.github/workflows/ci.yml` by grep (not from memory, per `docs/CLAUDE.md` rule 1), then each
invocation run and its rc captured **without a pipe** — `$?` after a pipe is the pipe's. Log:
`…/scratchpad/guards-r2c.log`.

**5. Arithmetic (H1, M3, L1, SOUND #7, #10).** Locator census by `git diff … ':!docs/reviews' | grep
'^+'`; distances computed from `awk NR` line numbers in the installed hook; `MEMORY.md` row lengths
by `len(str)` in Python, with the byte count reported separately because the rows contain
multi-byte glyphs and `wc -c` answers a different question.

**6. Grep scoping (per the brief's item 7).** Every repo-wide search excluded `docs/reviews/`, so
nothing I report was primed by the Codex halves' filed text. I read the round-1 Claude half (my
own predecessor), the round-1 Codex half's findings list, and rounds 2 and 3 of Codex — deliberately
and up front, because this is a late half whose job is to find what they did not.

⚠ **Contamination to declare.** I read the Codex r2 and r3 reviews **before** measuring, as the
brief instructed. H1, M2, M3 and M4 are therefore findings I formed knowing what Codex had already
said; M1 began as a hypothesis from reading `lib-memory-dir.sh` and was confirmed by probe C before
I re-read r3's M2, which turned out to be the same error in a different file. I am stating this
because round 1's Claude half declared the reverse contamination and the comparison between rounds
is worth more than a clean claim.

**7. Re-verification after writing this file.** Pre-committed prediction: `check-review-rounds.py`
drops from 2 failures to 1 (round 3 only). **Observed: rc=0, both cleared** — because round 3's
Claude half was filed concurrently by another agent, which `git status` shows as a second untracked
file beside mine. The prediction was wrong about the cause and L2 now records the observation
instead. `check-docs.py`, `check-anchors.py`, `check-memory-link.py`, `check-arch-findings.py` all
rc=0 with this file present; it carries no trailing whitespace. ⚠ I did not read, stage or touch the
round-3 file — a live agent's output is not static, and `git add -A` over it is a hazard this repo
has already paid for twice.

---

## Where I disagree with the Codex half

**1. "No sixth distinct live stale-locator site established" (r2, SOUND) answers the wrong
question.** It is correct — I found no sixth *stale* site either. But the branch's thesis is not
*"these four locators are stale"*, it is *"a locator in a vendored file must not be written"*. Under
that thesis the right census is of locators the branch **authored**, and there are nineteen (H1).
Both halves inventoried the old ones and verified the new ones' accuracy; neither asked whether
writing them was permitted by the document doing the writing.

**2. "No fourth trigger established" (r2 and r3, SOUND) is right as arithmetic and silent on the
defect.** I confirm the three-way disjunction and found no fourth. The defect is that the *name* of
trigger 1 — "external" — is false in two in-project configurations, one of which is the linked
worktree every review in this repo runs inside (M2). A Boolean check on an enumeration cannot see a
mislabelled member; the plugin's own `doctor.sh` says the word the documents deny.

**3. Round 3 filed a finding as SOUND, and that is why nothing fixed it.** Its SOUND list contains
*"`doctor.sh` reports legacy storage from the main checkout; from this linked worktree it reports
the shared main-checkout store as external. **The dashboard quotation needs that execution-directory
qualification.**"* A row whose own sentence says a document needs changing is a Medium, not a
confirmation — and `b972afee` duly left the sentence alone (M4). This is worth more than the finding
itself: the SOUND section is where a review's unactioned work goes to die.

**4. r2's M3 was right and its repair was partial, in the direction r2 itself named.** M3 flagged a
withdrawal that *"stops short"*; the fold then repaired the dashboard's entry count and left
`process-rationale.md:394` at `~102` (L1). The fold's own new comment in `check-handoff-path.py`
articulates the rule it then broke: *"a withdrawal has a blast radius and mine kept stopping short
of it."*

**5. Where I agree, so the agreement is on the record.** r2's M1 (the refusal's "SHARED path above"
is wrong under an external store) and M2 (`grep -R` is not portable), and r3's M1, M2 and L1, are
all genuine against `7cf48d43` and all correctly repaired by `755c35a6`/`b972afee` — including the
best decision in either fold, which is prescribing **no search flag at all** after two
implementation-specific prescriptions were each measured wrong. r2's M4 (the "FIVE consecutive
rounds" overclaim) is also sound, and r3's narrowing to 11–13 is better evidenced than r2's
"bound it to the witnessed rounds". I re-derived none of those five; I checked that the fold
answered them and it did.

**6. One thing both halves and I agree on, stated because it is the branch's strongest edit.**
Removing the drift figure rather than re-deriving it, and saying *"How far they moved is not
something this work measured"*, is correct and is the behaviour the repo wants. H1 is the argument
that the same discipline has one more layer to go.

---

**Reviewed `7cf48d43`, with the folds at `755c35a6` and `b972afee` read for (b)-class findings.
This round is NOT clean: 0 Blocking / 1 High / 4 Medium / 2 Low.**
