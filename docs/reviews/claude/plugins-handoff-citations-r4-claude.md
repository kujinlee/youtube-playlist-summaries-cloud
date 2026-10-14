# Round 4 — Claude half, adversarial. Subject: the fold at `2ad7038a`

Reviewed the committed tree at `2ad7038a` (the round-4 fold), the review it folds
(`docs/reviews/codex/plugins-handoff-citations-r4-codex.md`), the whole branch
`origin/master..2ad7038a`, and all six prior round documents. Mandate: refute.

**Headline: the fold replaced one wrong mechanism sentence with another wrong mechanism sentence,
and I measured it.** r4 H1 corrected *"`git grep` reads the INDEX"* to *"it reads the working-tree
content of tracked files, not the index"*. Measured on `git 2.49.0`: for an `assume-unchanged`
entry, default `git grep` served the **index** content and missed what was on disk. Three further
**tracked** cases are silently missed, which is the class the fold's repair — *name the corpus* —
cannot cover, because those files *are* in the corpus.

**Convergence: this round is NOT clean. 0 of 2.**

---

## Blocking

None established.

---

## High

### H1 — The fourth version of the mechanism sentence is still false, at five sites, and the miss-list omits three TRACKED cases that defeat the fold's own repair

The fold's surviving prescription appears at five sites. Quoted:

* `.agents/skills/handoff/SKILL.md:15` — *"it reads the **working-tree** content of tracked files,
  not the index, so staged-only content needs `--cached` and an older version needs
  `git grep <commit>`"*, and earlier in the same sentence *"because it searches what git tracks
  rather than walking the filesystem"*.
* `.claude/hooks/enforce-handoff-path.sh:69–72` — *"(no flag needed -- it searches tracked files,
  so the symlinked skill file is found)"* … *"git grep misses untracked and ignored files,
  submodules, nested checkouts and vendored deps, and it reads tracked WORKING-TREE content
  (--cached for staged, git grep &lt;commit&gt; for a version)."*
* `scripts/check-handoff-path.py:70–71` — *"because it misses untracked, ignored, submodule,
  nested-checkout and vendored content and reads working-tree not staged content (r4 H1)"*; and
  `:80` — *"(`git grep` searches what git tracks)"*.
* `docs/process-rationale.md:372` — *"it misses untracked, ignored, submodule, nested-checkout and
  vendored content and reads working-tree rather than staged content (r4 H1)"*.
* `docs/memory/a-vendored-line-number-has-no-owner.md:21` — *"Default `git grep` reads the
  **working-tree** content of tracked files (`--cached` for staged, `git grep <commit>` for a
  version), and it misses untracked, ignored, submodule, nested-checkout and vendored content"*.

**Measured, in an isolated repo built for the purpose (`git version 2.49.0`), with a green control
in every run (a plain tracked file was found by the same invocation):**

| Fixture — all of these files are TRACKED | default `git grep -l` | `--cached` | `/usr/bin/grep -rl` |
|---|---|---|---|
| `assume-unchanged`, disk content replaced | found the **index/HEAD** string `AU-marker`; **missed** the on-disk string `DISKONLY-marker` | — | found `DISKONLY-marker` |
| `skip-worktree`, content present on disk | **0** (rc=0, no stderr) | 1 | 1 |
| sparse-checkout cone, path outside the cone | **0** | 1 | n/a (file absent) |
| tracked file deleted from the working tree | **0**, rc=0, **empty stderr** | 1 | n/a |

Three distinct refutations, each independently sufficient:

**(a) The mechanism sentence is wrong in the same direction as the one it replaced.** With
`assume-unchanged` set, `git grep -l AU-marker` printed `au.txt` while the working-tree copy
contained only `DISKONLY-marker replaced` (verified by `cat` in the same run, and
`/usr/bin/grep -rl DISKONLY-marker .` printed `./au.txt`). So default `git grep` served cached
content and did **not** read the working tree. *"Default `git grep` reads the working-tree content
of tracked files, **not the index**"* is therefore not a true statement of the mechanism — it is
the fourth version of this sentence on this branch and the fourth to be wrong. `git ls-files -v`
reported `h au.txt`, which is the observable that distinguishes the case.

**(b) The repair — "name the corpus" — does not cover its own corpus.** `skip-worktree`,
sparse-checkout and deleted-from-working-tree entries are **tracked**. A reader who scopes the claim
to "this repo's tracked files", exactly as all five sites instruct, still gets silent zeros. Note
that sparse-checkout *is* implemented with the skip-worktree bit (`git ls-files -v drop/d.txt`
printed `S drop/d.txt`), so this is one mechanism with two user-facing names — and a sparse checkout
is an ordinary way to work in a large repo.

**(c) The enumerated miss-list is incomplete, and the sentence that would have covered the gap
frames it too narrowly.** The list is *"untracked, ignored, submodule, nested-checkout and vendored
content"*. None of the four tracked cases above is in it. The working-tree clause is the only part
that could cover them, and it states exactly one consequence — *"so staged-only content needs
`--cached`"* — which does not tell a reader that a tracked file **deleted** from the working tree
returns nothing with **rc=0 and no stderr**, i.e. indistinguishable from "no such string in the
repo". That is the precise failure shape this whole branch exists to prevent.

**Concrete failure scenario.** A future session repeats this branch's inventory on a machine where
the repo is sparse-checked-out, or where someone has run
`git update-index --skip-worktree .agents/skills/handoff/SKILL.md` (a routine move to stop a
locally-patched vendored file showing as dirty — and `docs/plugins.md` records that this very file
*is* locally patched and gets reverted by `npx skills@latest add`, which is exactly the situation
that invites the bit). `git grep -l session-start-hook` returns the other sites and **not** that
one, rc=0, no warning. The inventory reports complete; the fifth site is missed again — the same
outcome as round 1 H1, reached through the instrument this branch adopted to make it impossible.

**Repair.** State the mechanism as what it is: default `git grep` searches the paths in the index,
reading each from the working tree *unless* the entry is marked `skip-worktree`/`assume-unchanged`
or absent, in which case it reads the cached blob or nothing. Then give the one instruction that
survives all of it — compare `git grep -l` against `git grep --cached -l` and against a filesystem
walk, and treat any disagreement as the signal. One command cannot be trusted here, which is the
generalisation of r4 H1 the fold stopped one step short of.

---

### H2 — The hint-trigger label is on its third version and still mispredicts Codex's own control case; the repair r4 M3 actually named was applied at zero of three sites

Codex r4 M3 closed with an explicit instruction: *"Name the actual comparison—`REMEMBER_ROOT != PROJECT_DIR`—and explain its causes consistently across the sites."*

The fold instead substituted a paraphrase, at all three sites:

* `.agents/skills/handoff/SKILL.md:17` — *"a resolved store root that is not the project directory
  ITSELF"*
* `.claude/hooks/enforce-handoff-path.sh:80–81` — *"a resolved store root that | is not the project
  directory itself"*
* `docs/plugins.md:87` — *"(a resolved store root ≠ the project dir ITSELF"*

`REMEMBER_ROOT` appears at none of them. **Measured against the installed hook** (`remember` 0.33.0,
`~/.claude/plugins/cache/claude-plugins-official/remember/0.33.0/scripts/session-start-hook.sh`),
each case run in its own throwaway project with its own `$HOME`, `data_dir` set in
`$HOME/.remember/config.json` (the only layer that resolves it — `lib-memory-dir.sh:241–247` reads
the bundled and user-global files, while the per-project `config.json` at `:274` is read only
*after* `REMEMBER_DIR` already exists):

| `data_dir` | store directory actually created | hint printed? |
|---|---|---|
| *(absent)* | `<proj>/.remember` | no |
| `notes` | `<proj>/notes` | **no** |
| `a/b` | `<proj>/a/b` | **yes** — `Write next handoff to: <proj>/a/b/remember.md` |
| `.` / `./` / `.remember` / `.remember/` | `<proj>/…` | no |
| `/tmp/yps-ext-store/.remember` | `/tmp/yps-ext-store/.remember` | yes |
| *(none)*, `handoff_mode: per_session`, session id present | `<proj>/.remember` | yes — `remember.sess-AAA.md` |
| *(none)*, `handoff_mode: per_session`, **no** session id | `<proj>/.remember` | yes — shared `remember.md` **+** `(handoff_mode is "per_session", but no session_id reached this hook …)` |

Controls: the `data_dir=notes` row reproduces Codex's own control (no hint) and the `a/b` row
reproduces its finding verbatim; a main checkout printed no hint while a linked worktree of the same
repo printed one, so the harness demonstrably distinguishes hint from no-hint.

**The refutation.** For `data_dir=notes` the store is `<proj>/notes`. That is *"a resolved store root
that is not the project directory itself"* on any ordinary reading of those words — and **no hint
prints**. For `data_dir=a/b` the store is `<proj>/a/b`, equally "not the project directory itself",
and a hint does print. The new label cannot tell the two apart, and on the control case it predicts
the opposite of what happens. The distinguishing fact is that `notes` is an *immediate child* of the
project directory and `a/b` is not, because the condition at `:1544` is

```
if [ "$REMEMBER_ROOT" != "$PROJECT_DIR" ] || [ -n "$PER_SESSION_HANDOFF" ] || [ -n "$HANDOFF_MODE_DEGRADED" ]; then
```

and `REMEMBER_ROOT` is the **parent** of the store directory, not the store
(`lib-memory-context.sh:77–96` computes it as a fork-free `dirname` of `REMEMBER_DIR`, with a table
of cases in its own comment). Calling that *"the resolved store root"* names the store when the code
means the store's parent — so the one word a reader would reason from is the word that is wrong.

This is the **third** version of this label (v1 *"External mode (the store is outside the project)"*;
v2 added the worktree; v3 the above), and the first version it has had that contradicts a measurement
already filed on the branch.

**Repair.** Either name the symbol as the reviewer asked — *"the hook prints the hint when
`REMEMBER_ROOT != PROJECT_DIR`, where `REMEMBER_ROOT` is the PARENT of the resolved store"* — or
state the observable consequence, which gets every measured row right in one clause: *"the store
directory is not an immediate child of the project directory"*.

**Severity.** High rather than Medium: it is a measured-behaviour claim, stated identically at three
sites, which is wrong on the control case of the very finding it is folding; and the branch's whole
subject is claims that stop being true where a reader needs them.

---

### H3 — The ELEVENTH incomplete withdrawal, and it is the ninth's exact shape: the retired lesson is the bolded lead-in of the paragraph that corrects it, on a line this fold edited

The fold's own commit message states the retirement:

> *"The lesson is now **name the corpus and the content version you are inventorying**, not 'one
> instrument cannot have the problem'. Fixed at the skill, the hook refusal and the memory file."*

`docs/memory/a-vendored-line-number-has-no-owner.md:21` still reads, as the bolded ⭐⭐ lead-in to
that paragraph:

> *"⭐⭐ **Why it was missed, and the lesson is ONE INSTRUMENT, not a flag:**"*

and two clauses later, still affirmatively:

> *"⛔⛔ **For a TRACKED corpus, `git grep` has no flag problem and no symlink problem at all**"*

before its own correction arrives: *"⛔ **r4 H1 corrected two things in that sentence…**"*.

**The fold edited this exact line.** `git show 2ad7038a -- docs/memory/a-vendored-line-number-has-no-owner.md`
has a single `-`/`+` pair whose both halves begin
*"blocked reader to open. ⭐⭐ **Why it was missed, and the lesson is ONE INSTRUMENT, not a flag:**"* —
the retired lesson was carried through unchanged, as the heading of the paragraph that retires it.

This is structurally identical to the ninth incomplete withdrawal the fold confesses in the same
commit, where `scripts/check-handoff-path.py:55` *"still HEADED the block 'NO SEARCH COMMAND IS
PRESCRIBED' four lines above its own correction"*. The guard's heading was repaired to *"TWO CORPORA,
TWO SEARCHES"*; the memory file's was not. Four of the five sites now say two corpora
(`check-handoff-path.py:55`, `:69`; `process-rationale.md:372` — *"There are **two corpora** and they
need different answers"*); this one still says one instrument.

**Why this site is the costly one.** `docs/memory/` is the artifact designed to be recalled and
copied forward, and the paragraph is written as transferable wisdom (*"the lesson is…"*). This file
itself records, at `:42`, the branch's own precedent for grading that: *"A review graded this
**Blocking**, not Medium, because it shipped as transferable wisdom rather than as a stray figure."*
I stop short of Blocking only because the correction is present later in the same paragraph, so a
reader who finishes the sentence reaches the current position — unlike the graded case, where the
claim was false and uncorrected.

**Related, and checked rather than assumed:** `docs/memory/MEMORY.md` gained one index row for this
file — *"⭐ A vendored LINE NUMBER has no owner … 5 sites, one the REFUSAL TEXT; `grep -r` skips
symlinks. ⛔ The FIX cited a stale COMMENT"* — and the fold did not touch it. By that file's own
header every row *"is always in context"*, so the always-loaded one-liner carries only the
round-1-era framing. I do **not** file this as a withdrawal: *"`grep -r` skips symlinks"* is a true
statement, not a retired position. It is the row to update when H3 is fixed.

**Repair.** Replace the lead-in with the two-corpora framing the other four sites now carry, and mark
the retired phrasing as retired rather than deleting it, consistent with how the guard comment and
`process-rationale.md` handle theirs.

---

## Medium

### M1 — "all five tracked sites" is a count with an unstated unit, and it is false as written: the query returns six

Two sites assert it:

* `.agents/skills/handoff/SKILL.md:15` — *"Measured against the pre-branch base: `git grep -l
  session-start-hook` finds all five TRACKED sites INCLUDING this symlinked file"*
* `docs/memory/a-vendored-line-number-has-no-owner.md:21` — *"`git grep -l session-start-hook` finds
  all FIVE tracked sites including the symlinked one"*

**Measured.** The pre-branch base is `origin/master` (`git merge-base origin/master 2ad7038a` =
`74a44551`, identical to `git rev-parse origin/master`). `git grep -l session-start-hook 74a44551`
returns **6** tracked files:

```
.agents/skills/handoff/SKILL.md
.claude/hooks/enforce-handoff-path.sh
docs/plugins.md
docs/process-rationale.md
docs/reviews/claude/velocity-177-r5-claude.md
scripts/check-handoff-path.py
```

Five excluding `docs/reviews`. At `2ad7038a` the same query returns **11** raw / **6** excluding
`docs/reviews`; at `f6d240a5`, **10** / **6**. An independent filesystem walk following symlinks at
the tip found the same 11 physical files.

So the figure is only right under the unit *"live stale-citation sites outside filed reviews"*, and
neither sentence states either qualifier. The sixth file is not incidental: on master
`docs/reviews/claude/velocity-177-r5-claude.md:161` carries `session-start-hook.sh:795` — a sixth
tracked stale citation, which is left alone because filed reviews are testimony. A reader who runs
the quoted command to check the quoted claim gets six paths and a sentence that says five.

Codex r4 recorded this distinction under *Checked and found SOUND* — *"Five original live
stale-citation sites is correct; five raw-query matches is not"* — so the fold had it in hand. Its
edit changed `sites` → `TRACKED sites`, which addresses the corpus axis. The defect was on the count
axis, and it is untouched.

**Repair.** *"finds all five live stale-citation sites, including this symlinked file — six tracked
files match in total, the sixth being a filed review left as written."*

---

### M2 — "the ninth and tenth incomplete withdrawal" is a count whose population is nowhere enumerated, and it cannot be reconciled with the branch's only other ordinal

The fold publishes three ordinals:

* commit message — *"That is the ninth and tenth incomplete withdrawal on this branch, and I authored
  them in the commit fixing the eighth."*
* `scripts/check-handoff-path.py:57–58` — *"I introduced that in the very commit that fixed the
  **eighth** incomplete withdrawal on this branch."*
* `docs/process-rationale.md:372` — *"which is the **eighth** incomplete withdrawal on this branch."*

I swept every file on the branch and every one of the six prior round documents for an enumeration
and found none. The only competing ordinal for this class anywhere on the branch is one round
earlier, in filed testimony:

* `docs/reviews/claude/plugins-handoff-citations-r3-claude.md:173` — *"the branch's own 'a withdrawal
  has a blast radius and mine kept stopping short of it' (`scripts/check-handoff-path.py:52`),
  **fourth instance**, inside the fold that writes it down."*

Four at round 3, eight before round 4's own two, and nothing on disk that reconciles them. The two
ordinals also count different subjects — *"instances of the blast-radius pattern"* versus
*"incomplete withdrawals"* — and neither is defined. I could not reproduce 8, 9 or 10 from any
source in the repository.

This is the shape the branch has already paid for twice: *"stale by 376 lines"*, withdrawn at
`scripts/check-handoff-path.py:51` because the population was never measured, and *"THE COUNT WAS
PUBLISHED AS FOUR AND IS FIVE"* at `docs/process-rationale.md:365`. A bare ordinal with no list is
the same instrument.

**Repair.** Either enumerate the ten, one line each with a file:line, in the place that claims the
number; or drop the ordinal and say *"another instance of this branch's recurring class"*, which is
the part that is actually established.

---

### M3 — The reader-facing dashboard entry asserts the retired "prescribe none" position in other words, and is three rounds stale; the fold did not touch it

`docs/dashboard-entries.md:14845–14848`, the branch's own entry:

> *"The fix removes the line numbers rather than updating them. A line number in a file that belongs
> to somebody else cannot be kept honest here — no check in this project can watch it, and the next
> plugin update silently invalidates it again. **The documents now name the thing to search for and
> leave the finding to the reader.**"*

*"Leave the finding to the reader"* is *"the repair is to prescribe none"* in other words — the
position r4 M2 retired. `scripts/check-handoff-path.py:68` now says so explicitly: *"'prescribe no
flag' is no longer what this repo does"*, and the repo does now prescribe `git grep -l <string>` for
the tracked corpus at five sites. The dashboard entry asserts the opposite.

**This is the site a literal-phrase sweep cannot reach**, which is the exact limitation the brief for
this round warned about: the entry nowhere contains "prescribe", "no flag", or "tool-specific". I
found it by sweeping for the retired *positions*, not their wording.

Two further observations about the same file, checked rather than assumed:

* The entry's commit trail ends at *"⟳ **Third commit: round 1's fold.** Reviewed by both halves —
  **1 Blocking, 1 High, 8 Medium, 6 Low**"* (`:14904–14905`). The file ends at line 14910. **Rounds
  2, 3 and 4 are not mentioned anywhere in it** — `grep -nE 'round 4|r4|Round 4|fourth'` over the
  entry returns nothing. So the reader-facing record stops three rounds before the tree it describes,
  and its last word on review severity is round 1's.
* `scripts/check-dashboard-entry.py` is **rc=0** on this branch, correctly: an entry exists. The gate
  cannot see that the entry has gone stale, which is why this is a review finding and not a red
  check.

**Repair.** Update the entry in the same commit as the next fold: correct `:14847–14848` to the
two-corpora position, and extend the commit trail through round 4.

---

## Low

### L1 — The restored locator does not paste; `<version>` is a shell redirect

The fold's claim: *"The full path is restored, still unbroken on one line **so it pastes**."*
Codex's L1 asked for *"a complete hook locator **or** an executable discovery command"*.

Rendered the real refusal by falsifying the guard on a copy of the tree. Line 29 of stderr:

```
  ~/.claude/plugins/cache/claude-plugins-official/remember/<version>/scripts/session-start-hook.sh
```

Verified true: it is one unbroken line (98 characters, no embedded newline — a soft wrap at 80
columns does not break a paste), the suffix is restored, nothing expands inside the unquoted heredoc,
and the template matches the installed layout exactly with `<version>` = `0.33.0`
(`ls` of the substituted path succeeds).

**Measured failure:** pasting the printed line into bash gives

```
line 1: version: No such file or directory
```

because `<version>` is parsed as an input redirect from a file named `version`. So the one claim the
fold makes about it — that it pastes — is false, and the alternative Codex offered is not taken. A
glob does work, measured:
`ls ~/.claude/plugins/cache/claude-plugins-official/remember/*/scripts/session-start-hook.sh` →
`…/remember/0.33.0/scripts/session-start-hook.sh`.

**Repair.** Print the glob form as the locator; it is both a complete locator and an executable
discovery command, and it survives the version bump the placeholder exists to tolerate.

---

### L2 — `docs/process-rationale.md:362–363` duplicates a clause across the line break, and two rounds have read past it

```
362  `REMEMBER_HANDOFF` is at `:1171`, the `=== LAST HANDOFF ===` emit at `:1666`, the delivery record at
363  the delivery record at **`REMEMBER_HANDOFF_STATE`** (⟳ cited as `:1571-1640` until round 3 M4, …
```

*"the delivery record at"* appears twice; the first occurrence has no object, so the enumeration
reads as though an item was dropped. `grep -c 'the delivery record at' docs/process-rationale.md` =
**2**; on `origin/master` the string does not occur at all.

Bisected across the branch: the count is 1 at every commit up to `f44ed402` and becomes **2** at
`f6d240a5` — the round-3 fold, which is the tree Codex r4 reviewed. Neither the r4 Codex half nor
this fold caught it, and it is live at the tip, inside the sentence that carries the branch's own
version-pinned citations.

---

### L3 — `.agents/skills/handoff/SKILL.md:17` is a sentence fragment introduced by the M3 substitution

> *"⟳ **Corrected 2026-10-13: THREE things print it, not one.** a resolved store root that is not the
> project directory ITSELF — ⛔ r4 M3: …"*

The fold replaced the list's first item, *"External mode (the store is outside the project)"*, with a
lowercase phrase, so the sentence after the full stop begins *"a resolved store root"* and the
three-item enumeration has no introduction. The hook's copy of the same sentence
(`enforce-handoff-path.sh:80`) keeps *"THREE things print it: a resolved store root…"* and reads
correctly, so this is one of two parallel edits where only one preserved the grammar — the same
one-of-two shape r3 Claude M1 filed against this file.

This is the file the refusal text sends a blocked reader to open
(`enforce-handoff-path.sh:90`: `$EDITOR .agents/skills/handoff/SKILL.md`).

---

### L4 — The M1 provenance correction names the artifact but drops its version, which is the clause the branch's new lesson adds

The fold's own new lesson is *"name the corpus **and the content version** you are inventorying"*,
and `docs/memory/a-vendored-line-number-has-no-owner.md:23` makes version-naming the condition under
which a vendored citation is legitimate at all: *"⭐ **A dated retrospective that NAMES THE VERSION
it measured may cite lines**, because that is what makes its own claim checkable."*

The source names the version. `docs/reviews/codex/plugins-handoff-citations-r3-codex.md:13`:
*"GNU grep **3.12**'s source option table contains **no `S`**"*.

All three corrected sites drop it:

* `docs/process-rationale.md:372` — *"the GNU leg came from GNU's **source option table**, not a
  runtime probe"*
* `scripts/check-handoff-path.py:63–64` — *"That leg came from GNU's SOURCE OPTION TABLE, not a
  runtime probe"*
* `docs/memory/a-vendored-line-number-has-no-owner.md:21` — *"that leg is from GNU's source option
  table, not a runtime probe"*

A reader who wants to check the claim cannot, without first rediscovering which GNU release was
read — and `-S` could be added in a later release, at which point an unversioned claim silently
becomes wrong in the same way a vendored line number does. Adding `3.12` costs four characters at
three sites.

---

## Checked and found SOUND

Each of these is something I tried to refute and could not.

**The fold's measured claims that hold**

* **The untracked-file control (r4 H1's own evidence).** Reproduced in a purpose-built repo:
  `/usr/bin/grep -rl` finds the untracked file holding the string (1), `git grep -l` does not (0).
  The ignored-file, `.git/info/exclude` and nested-checkout legs reproduce the same way.
* **`.gitattributes` is not a gap.** A tracked file marked `-diff export-ignore` and one marked
  `binary` were both found by default `git grep -l`. The fold does not claim otherwise; I checked
  because the brief asked whether the miss-list was missing `.gitattributes`-excluded paths. It is
  not — that class does not exist.
* **A path only in another worktree** is missed by default `git grep` and found by
  `git grep -l <needle> <branch>`; it is also missed by `grep -rl` from the main worktree, since the
  directory is a sibling. Adequately covered by *"an older version needs `git grep <commit>`"*.
* **`docs/plugins.md` is a net-zero edit.** 260 lines at `origin/master`, at `f6d240a5` and at
  `2ad7038a`. The budget is real and is 260 — `scripts/check-docs.py:193`,
  `"docs/plugins.md": 260`. `check-docs.py` reports
  `budget docs/plugins.md : 260 / 260 TIGHT (0 line(s) of runway)` and **warns** rather than
  blocking, which is the documented behaviour at `:197–209`. The edited line 87 is a single long line
  inside the `>` blockquote and is valid Markdown; it renders as part of the same block as `:86`.
* **`docs/plugins.md:84`'s "four stale LINE NUMBERS removed"** is right *for that file*: at
  `origin/master` it carried exactly four distinct citations (`:795`, `:809-812`, `:814-825`,
  `:800-802`, at its lines 82–87) and at `2ad7038a` it carries zero.
* **The installed-hook figures.** Against 0.33.0: `grep -c 'REMEMBER_HANDOFF=' ` = **2** (at `:1168`
  per-session and `:1171` shared), bare `REMEMBER_HANDOFF` = **23**, total **2,027** lines. The
  "keep the `=`" instruction is therefore exactly right.
* **Every vendored line citation in the dashboard entry's tech block verifies against 0.33.0**, which
  it names: `:1164` = `config_into HANDOFF_MODE ".handoff_mode" "single"`, `:1168`, `:1171`,
  hint `:1546` = `echo "Write next handoff to: $REMEMBER_HANDOFF"`, emit `:1666` =
  `echo "=== LAST HANDOFF ==="`. Same for `process-rationale.md:361–363`.
  `REMEMBER_HANDOFF_STATE` exists with that spelling, and its reads/writes do run past `:1660`
  (`:1653`, `:1660`, `:1698`-region), so round 3 M4's under-bounding correction is right and the
  symbol citation is the honest one.
* **The linked-worktree trigger.** A main checkout printed no hint; a linked worktree of the same
  repo printed `Write next handoff to: <main>/.remember/remember.md`. *"A linked WORKTREE counts"* is
  correct, and `lib-memory-dir.sh:72–134` is the mechanism (`REMEMBER_DIR` follows the main checkout
  while `PROJECT_DIR` stays the worktree).
* **Both `per_session` rows.** With a session id: `remember.sess-AAA.md`. Without: the **shared**
  `remember.md` plus *"(handoff_mode is "per_session", but no session_id reached this hook --
  writing to the shared file above, not a per-session one.)"*. Three triggers, not two — confirmed.
* **The GNU provenance claim is accurately sourced.** `docs/reviews/codex/plugins-handoff-citations-r3-codex.md:41`,
  under *CANNOT RUN*: *"GNU grep binary replay could not complete: its source build failed during
  configuration. The unsupported `-S` finding rests on its actual source option table, not a
  successful GNU runtime probe."* The fold's characterisation is exact.
* **No site now UNDER-claims the option-table finding.** `process-rationale.md:372` and
  `check-handoff-path.py:62` changed *"measured"* → *"found"* and kept the finding. I specifically
  checked `.agents/skills/handoff/SKILL.md:15`, which r3 Claude H2 listed as one of four sites and
  r4 Codex M1 did not: it states *"GNU grep has no `-S`"* with no provenance verb, so there is no
  "measured" to withdraw there and r4 M1's own words — *"the underlying option-table finding need not
  be withdrawn"* — cover it. Not a finding.

**The guard and its falsifier**

* **`check-handoff-path.py` rc=0, `--self-test` 10/10**, both re-run on the post-fold tree.
* **The real falsifier still fires**, re-verified independently on a dereferenced copy of
  `.agents/`, `.claude/` and `scripts/`: control → guard rc=0, hook rc=0 with **0 bytes** of stderr;
  with all 2 occurrences of `.remember/remember.md` replaced in the skill → guard **rc=1**, hook
  **rc=2**, stdout **0 bytes**, and `Write the handoff to:  .remember/remember.md` present in
  stderr; restore → rc=0. `bash -n` clean on the hook.
* **Both named near-misses still refused**, plus one of my own: `.remember/handoff.md` → rc=1,
  bare `remember.md` → rc=1, `.remember/remember.markdown` → rc=1.
* **The mutation manifest did not come unbound.** `scripts/mutations/check-handoff-path.json` is
  unchanged on this branch while `scripts/check-handoff-path.py` changed by 43 lines, so I checked
  every `edits` anchor against the **post-fold** file: all five bind exactly once, none orphaned,
  none ambiguous. (Codex verified the mutations against `f6d240a5`, i.e. before these edits — this
  closes that gap. The fold's edits were confined to the comment block above `CONSUMED_PATH`, which
  no anchor reaches.)
* **The refusal's heredoc is still safe.** No `$` or backtick in any of the fold's new lines expands;
  rendered output contains no sentinel expansion and no `--version`-style surprise.

**Other**

* **`.claude/skills/handoff` is a tracked symlink** (`git ls-tree -r 2ad7038a` lists it; `ls -la`
  shows `handoff -> ../../.agents/skills/handoff`), and `.claude/.git` / `.claude/.gitignore` are
  **absent** in this worktree — so the nested-checkout hazard `docs/plugins.md` records is not the
  current filesystem state, matching Codex's finding. `git grep` reads the symlink's blob (the target
  path), finds the needle once via `.agents/skills/handoff/SKILL.md`, and never follows the alias.
* **The three-layer `.handoff_mode` claim** at `process-rationale.md:390–393` is right: all three
  config layers are absent in a clean install and the default `single` stands. (Separately and not
  claimed anywhere: `data_dir` resolves from only **two** of those layers, because the per-project
  file is read after `REMEMBER_DIR` already exists. Not a finding — no site asserts otherwise — but
  it is why my first hint-matrix run was void.)

---

## CANNOT RUN

**These are validation failures, not passes. Treat every item here as NOT RUN.**

* **Interpreter parity: NOT RUN.** Every guard below ran on `Python 3.14.4`; CI pins 3.12.
  `scripts/check-python-pin.py` exists in this repo precisely because that difference has already
  changed a guard's behaviour (`Path.is_file()` and `ENAMETOOLONG`). A green sweep here is not
  evidence about CI.
* **`check-plan-code.py --mutate .` — the full shard matrix: NOT RUN.** I ran `--self-test` only.
  The five handoff mutations binding correctly is a static check of the manifest against the source,
  not an execution of the mutation suite.
* **`check-test-counts.py`: NOT RUN** — `FAIL (cannot run): no jest results at …/jest-results.json`
  … *"Treat this check as NOT RUN — an absent results file is not a passing suite."* The unit suite
  was not run. (Its `--self-test` passes.)
* **PR-event forms of the two PR-only guards: NOT RUN.** There is no PR for this branch, so
  `check-dashboard-entry.py` and `check-review-recorded.py` were exercised only in their local form.
* **My own `REMEMBER_ROOT` probe: VOID, and I am reporting it rather than its output.** Sourcing
  `log.sh`/`lib-memory-dir.sh`/`lib-memory-context.sh` directly produced `REMEMBER_ROOT=/` and an
  identical `REMEMBER_DIR` for all four `data_dir` values, including a hint prediction for the
  default case that the real hook contradicts — a red control, so the instrument. H2 therefore rests
  **only** on end-to-end runs of the installed hook and on the store directories it actually
  created, not on that probe.
* **My first hint matrix: VOID for the same reason** — `data_dir` written to the per-project
  `config.json` changed nothing, including for an absolute external store that must print a hint.
  Discarded and rerun with `$HOME/.remember/config.json`, which has a green positive control.
* **`git` version parity for H1: partially bounded.** All H1 fixtures ran on `git 2.49.0`, the same
  binary the branch's own claims were measured with. I did not test other git versions; the
  `skip-worktree`/`assume-unchanged` behaviours are long-standing but I measured one version.
* **Historical claims not replayed:** the pre-0.33.0 hook (never fetched — the branch withdraws any
  drift figure itself, correctly), the authoring-time installation state, and the cross-branch
  review history behind the `a-harness-cannot-read-a-cause-from-a-childs-text.md` lesson.

### The guard suite, in full

The list is every `python3 scripts/check-*` step in `.github/workflows/ci.yml`: **52 invocations,
all 52 attempted, none skipped.** `rc=0` on **48**; `rc=1` on three; `rc=2` on one. Named below —
nothing here is reported as a pass that was not run.

`check-selftest-counts.py` is **rc=0**, which is what certifies `check-handoff-path.py`'s declared
10 cases against the suite that actually runs; `check-docs.py`, `check-review-rounds.py --self-test`,
`check-plan-code.py --self-test`, `check-anchors.py`, `check-dashboard-entry.py` and
`check-plan-file-tags.py` are all rc=0.

### The four non-zero rows, and why none is a branch defect

* `check-review-recorded.py` **rc=1** — expected and declared: the fold changed guarded files, so the
  r4 Codex verdict (head `f6d240a5`) no longer covers this tree. A further round is owed.
* `check-review-rounds.py` **rc=1** — *"plugins-handoff-citations round 4: only codex — claude
  neither ran nor recorded a `REVIEW GAP:` line"*. **This document is what clears it.** It is the
  guard correctly reporting that the round was half-finished at the moment I measured.
* `check-test-counts.py` **rc=1** — the CANNOT RUN above, surfaced by my extraction dropping
  `--results jest-results.json`. Same outcome either way: no results file exists, and the guard says
  so in the right words.
* `check-plan-code.py` with no arguments **rc=2** — an artefact of **my** extraction, not of CI. CI
  invokes it as `--mutate .`; my `grep` over `ci.yml` truncated at the line continuation. The guard's
  own message is *"CANNOT RUN — nothing to do … Treat this as NOT CHECKED."* Reported so the row is
  not read as a repo defect.

---

## Instruments

Commit message read first (`git log -1 --format=%B 2ad7038a`); the fold diff and
`git diff origin/master..2ad7038a`; all six prior round documents in full, plus `r3-claude` H2/M1 and
`r3-codex`:13/:41 read directly for the provenance question.

**Purpose-built git fixtures** (two throwaway repos, `git 2.49.0`): untracked, gitignored,
`.git/info/exclude`, nested checkout, staged-but-reverted, tracked-deleted-from-worktree,
`skip-worktree`, `assume-unchanged`, sparse-checkout cone, second worktree, `.gitattributes`
`-diff export-ignore` and `binary` — each with a green control in the same invocation.

**Installed-hook matrix** (`remember` 0.33.0): ten isolated runs, each with its own project and
`$HOME`, over absent/`notes`/`a/b`/`.`/`./`/`.remember`/`.remember/`/absolute-external `data_dir`,
plus `per_session` with and without a session id, plus a main-checkout/linked-worktree pair;
store locations read from the filesystem rather than inferred.

**Copied-tree falsifier**: dereferenced copy of `.agents/`, `.claude/`, `scripts/`; control, five
falsifications (full removal plus three near-misses), restoration, refusal rendered and measured
line-by-line, and a paste test of the printed locator through `bash`.

**Mutation-anchor check**: every `edits` pair in `scripts/mutations/check-handoff-path.json` counted
against the post-fold source.

**Guard suite**: the `python3 scripts/check-*` steps extracted from `.github/workflows/ci.yml` and
run as a set (52 invocations), not a subset.

**Sweeps**: `/usr/bin/grep -rIn` following the repo's own layout over `.agents`, `.claude`, `scripts`,
`docs/plugins.md`, `docs/process-rationale.md`, `docs/memory`, `docs/dashboard-entries.md`,
`docs/dev-process.md`, `docs/process-checklists.md`, `docs/review-method.md`,
`docs/portable-practices.md`, `docs/backlog.md`, `AGENTS.md`, `CLAUDE.md` — for the retired
*positions* (seven of them) rather than the fold's phrase list, which is how M3 and H3 were found;
plus a per-commit bisect of the duplicated clause in L2.

⚠ The worktree was not modified. `git status --porcelain` was empty before and after every step; all
mutation and falsification work was done on copies or in throwaway repositories.

---

**Reviewed `2ad7038a`: 0 Blocking / 3 High / 3 Medium / 4 Low. ⛔ THE ROUND IS NOT CLEAN —
convergence remains 0 of 2.**
