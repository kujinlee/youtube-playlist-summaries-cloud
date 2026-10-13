# Round 3 — CLAUDE half — branch `plugins-handoff-citations` @ `755c35a6`

Subject: `755c35a6` (round 2's fold), reviewed against the whole branch
`2413b003..755c35a6`, with `b972afee` — round 3's fold, written from the Codex half alone — read
afterwards to separate *what the Codex half missed* from *what the fold got wrong*.

⚠ **Arriving late, and why that matters to the reader of this file:** rounds 2 and 3 were run with
the Codex half only. That was a coordinator lapse, not a reviewer that could not run, so no
`REVIEW GAP:` applies and none is declared. **This file is round 3's missing half. Round 2's is
still missing** — see Blocking B1, which is a live CI red, not a process remark.

Mandate: **refute**, not confirm. Every finding below states which of the two it is:

* **(a)** something in `755c35a6` that the Codex half missed;
* **(b)** a place where the fold at `b972afee` got round 3's repair wrong.

**The round's one-sentence verdict.** The branch's thesis is right and I did not try to argue it;
what three rounds have not asked is why the inventory was a *working-tree grep* at all — `git grep`,
with no flag, finds all five sites including the symlinked one, which makes the fold's recorded
lesson ("prescribe no flag; symlink-following is tool-specific") the wrong lesson rather than a
cautious one. Separately, the fold publishes as **measured** a GNU-grep fact that the very review it
folds recorded under **CANNOT RUN**.

---

## Blocking

### B1 — `check-review-rounds.py` exits **1** at `b972afee`, and it is this branch's own rounds

Neither (a) nor (b): a gate neither half ran against its own absence. Codex's round 3 reports
*"Documentation guard passes; handoff guard passes"* — `check-review-rounds.py` is a third guard,
it is in `.github/workflows/ci.yml`, and it is red.

Run in the worktree at `b972afee`:

```
FAILED — 2 review round(s) with one half and no stated reason:
  ✗ plugins-handoff-citations round 2: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
  ✗ plugins-handoff-citations round 3: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
```

Filing *this* file clears round 3. **Round 2 stays red** — the branch cannot pass CI until a round-2
Claude half exists or a written reason does, and a `REVIEW GAP:` is not available because the half
could have run. ⛔ Do not read my filing as clearing the gate; re-run the guard and read its output.

**Falsifier:** if `python3 scripts/check-review-rounds.py` exits 0 after this file lands, B1 is
wrong and round 2 was recorded somewhere I did not look. **It did not fire.** Re-run with this file
on disk:

```
FAILED — 1 review round(s) with one half and no stated reason:
  ✗ plugins-handoff-citations round 2: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
rc=1
```

Round 3 cleared; round 2 is the whole of what remains.

---

## High

### H1 — three rounds optimised a grep flag for a corpus where `git grep` has no flag problem

**(a), and the fold doubled down on it — so also (b).** Rounds 1 (H1), 2 (M2) and 3 (M1) are all
one question: which recursive-search flag follows `.claude/skills/handoff` →
`../../.agents/skills/handoff`. The fold's answer is to prescribe **none** and to record, as a
⭐ lesson in `docs/memory/a-vendored-line-number-has-no-owner.md:21`, that *"whether your tool
follows it is TOOL-SPECIFIC"* and *"symlink-following is tool-specific: check"*
(`docs/process-rationale.md:372`).

The corpus being searched is **this repo's tracked files**. `.agents/skills/handoff/SKILL.md` is
tracked, and `.claude/skills/handoff` is a tracked symlink (`git ls-files -s` → mode `120000`), so
git indexes the real file and the symlink never enters the search at all.

**Measured — the counterfactual, run against the pre-branch base so it is the actual missed
inventory, not a re-creation of it:**

```
$ git grep -n -e ':795' -e ':809-812' -e ':814-825' -e ':800-802' 2413b003 \
      -- . ':(exclude)docs/reviews'
2413b003:.agents/skills/handoff/SKILL.md:13        ← THE FIFTH SITE
2413b003:.claude/hooks/enforce-handoff-path.sh:64,66,67
2413b003:docs/plugins.md:82,83,84,87
2413b003:docs/process-rationale.md:353,355
2413b003:scripts/check-handoff-path.py:42
```

All five sites, no flag, first try. BSD grep, ugrep, GNU grep and ripgrep differ about `-r`/`-R`/`-S`
and none of that is reachable from here.

**Why this is a High and not a tidy-up.** The branch conflated two different searches and answered
the wrong one:

| the search | right instrument |
|---|---|
| inventory **this repo** for stale citations of a vendored symbol | `git grep` — tracked files, symlink-proof |
| locate the symbol inside the **vendored plugin** (outside the repo) | name the path and the symbol, as the fold now does |

The fold gives the second as the answer to the first. The lesson that goes into memory — and memory
here is re-read every session — therefore tells a future author to *check their tool's symlink
behaviour* before an inventory, which is advice with no executable content, in place of a one-word
instrument the repo already uses (`scripts/check-plan-task-order.py` and
`scripts/check-surface-recall.py` both read git's file list rather than walking the tree).

**Stated bound, because it is the honest half of this finding:** `git grep` sees **tracked** content
only. A sixth site in an uncommitted file is invisible to it; `git grep --untracked` covers that, and
neither covers the vendored plugin tree. So the prescription is *"`git grep -n --untracked <symbol>`
for this repo; the plugin path for the dependency"* — two instruments for two corpora, which is what
the three rounds were missing. **Falsifier:** if `.agents/skills/handoff/SKILL.md` were untracked,
`git grep` would miss it and this finding dies. It is tracked — measured above.

### H2 — the fold publishes as **measured** a claim its own source recorded as CANNOT RUN

**(b).** Round 3's Codex half, under *CANNOT RUN — these are validation failures, not passes*:

> *"GNU grep binary replay could not complete: its source build failed during configuration. The
> unsupported `-S` finding rests on its actual source option table, not a successful GNU runtime
> probe."*

The fold then writes, at two sites:

* `docs/process-rationale.md:372` — *"v2 prescribed `-RS`; **round 3 measured** GNU grep having no
  `-S` at all and ripgrep rejecting `-R`."*
* `scripts/check-handoff-path.py:58` — *"v2: `grep -RS` — **round 3 measured** GNU grep having NO
  `-S` option at all, and ripgrep rejecting `-R`."*

and at two more as a flat assertion:

* `.agents/skills/handoff/SKILL.md:15` — *"GNU grep has no `-S`"*;
* `docs/memory/a-vendored-line-number-has-no-owner.md:21` — *"GNU grep has **no `-S`**; ripgrep
  rejects `-R`. **Each prescription was verified against the binaries I had**"* — and GNU grep was
  not among the binaries anyone had.

**What I could and could not reproduce, separately:**

| leg of the claim | my result |
|---|---|
| BSD grep `-r`/`-R` skip the symlink, `-RS` finds it | ✅ reproduced — `/usr/bin/grep -r`/`-R` on `.claude/skills` print nothing; `-RS` prints `.claude/skills/handoff/SKILL.md` |
| this shell's `grep` is a `ugrep` wrapper | ✅ reproduced — `type -a grep` is a function exec'ing the claude binary as `ugrep`; `ugrep 7.8.4` |
| ripgrep rejects `-R` | ✅ reproduced — `ripgrep 14.1.1` → `rg: unrecognized flag -R` |
| **GNU grep has no `-S`** | ⛔ **NOT RUN** — no GNU grep on this machine (`ggrep` absent at all three usual prefixes). **Treat this as NOT RUN.** |

I am not claiming the GNU leg is false — it is very likely true. I am claiming the branch wrote
**"measured"** over it, in the document whose subject is *"an inference stated as MEASURED"*, four
rounds after that exact pattern produced round 1's Blocking. The sentence two clauses later —
*"Each was verified against the binaries the author had and published for every reader's"* — is the
branch's own indictment of itself, applied to a binary the author did not have.

**Fix:** keep the claim, change the verb, and say where it comes from: *"round 3 read GNU grep's
source option table and found no `S`; the runtime probe could not be built (CANNOT RUN)."*

---

## Medium

### M1 — `SKILL.md:15` still states, affirmatively, the thing the fold withdrew — in the same paragraph

**(b), and it is the site Codex's M1 named by line number.** Codex round 3 M1 closed with: *"the
withdrawal also remains incomplete: the skill's same paragraph still says '`-R` does' follow the
symlink."* The fold edited that same line — and only its second half.

`.agents/skills/handoff/SKILL.md:15`, as it stands at `b972afee`, reads (one sentence, then four
clauses later):

> *"`grep -r` does not follow the symlink at `.claude/skills/handoff`, **and `-R` does**."*
> … *"`-R` and `-RS` were each tried and each is wrong on some common tool (**BSD grep ignores
> `-R`'s symlink sense**, GNU grep has no `-S`, ripgrep rejects `-R`)."*

The paragraph contradicts itself inside 300 characters, and the first clause is the one a reader
acts on. The parallel sentence in `docs/process-rationale.md:371-372` **was** repaired in the same
fold (*"a recursive search that does not follow symlinks misses it"*), so this is one of two
identical sentences fixed and the other left — the branch's own *"a withdrawal has a blast radius
and mine kept stopping short of it"* (`scripts/check-handoff-path.py:52`), fourth instance, inside
the fold that writes it down.

**Measured:** `git grep -nE 'grep -[rRS]+|-RS'` over every branch-touched file shows exactly one
surviving affirmative flag prescription, and it is this one.

### M2 — `plugins.md`'s RULE box says "NO hint means this rule's path". Measured false.

**(a) — in the subject, untouched by the fold, and missed by all three Codex rounds.**

`docs/plugins.md:86-87` (the ⛔ RULE box — Layer 1, the authority that "governs, whatever the skill
file says"):

> *"**If a session-start block prints `Write next handoff to: <path>`**, obey it — ⟳ **THREE
> triggers** (external, `per_session`, degraded); **NO hint means this rule's path**"*

The hint condition in the installed hook (`session-start-hook.sh:1546`) is:

```sh
if [ "$REMEMBER_ROOT" != "$PROJECT_DIR" ] || [ -n "$PER_SESSION_HANDOFF" ] || [ -n "$HANDOFF_MODE_DEGRADED" ]; then
```

A **relative** `data_dir` moves `REMEMBER_DIR` but leaves `REMEMBER_ROOT == PROJECT_DIR`
(`lib-memory-dir.sh:161` returns `"${proj}/${data_dir}"`; `_set_store_root` gives a relative
`data_dir` no store root at all). So no leg fires, and the destination is not `.remember/remember.md`.

**Measured** — six cases, each in its own throwaway project with `$HOME` redirected so the real
user-global config is never touched, driving the installed `0.33.0` hook with `REMEMBER_DEFER=0`:

| config (user-global tier) | session id | hint? | destination |
|---|---|---|---|
| `{}` | present | no hint | `<proj>/.remember/remember.md` |
| `{"handoff_mode":"per_session"}` | present | hint | `<proj>/.remember/remember.sess-bbb.md` |
| `{"handoff_mode":"per_session"}` | absent | hint + degrade line | `<proj>/.remember/remember.md` |
| **`{"data_dir":"notes"}`** | **present** | ⛔ **NO HINT** | ⛔ **`<proj>/notes/remember.md`** |
| `{"data_dir":"notes","handoff_mode":"per_session"}` | absent | hint + degrade line | `<proj>/notes/remember.md` |
| `{"data_dir":"<abs path>"}` | present | hint | `<abs path>/remember.md` |

Row 4 is a configuration in which the RULE box's path is wrong **and nothing prints a correction** —
the only such combination, and the one the sentence promises cannot exist.

**Why the two Codex rounds did not reach it.** Round 2 asked whether there was a fourth *config
layer* (a fourth file tier) and correctly answered no. Round 3 found the `data_dir` case only
*combined with* degraded `per_session` — where a hint does print — and filed it as the refusal's
wrong qualification (its M2). Neither separated `data_dir` from the degradation, so neither reached
the no-hint cell.

**This is an over-strengthening, not a weakening** — the brief asked me to watch for a replacement
sentence that quietly weakens its instruction, and this one does the opposite. The text it replaced
said *"It is absent in legacy mode by design"* — a correct narrow claim about one mode. The
replacement generalised it into *"NO hint means this rule's path"*, and the generalisation is where
the falsehood entered.

**Not a live defect today, stated so the severity is readable:** all three config tiers are absent
on this machine — `<plugin>/config.json`, `~/.remember/config.json` and
`<repo>/.remember/config.json`, each verified absent by `ls` — so `handoff_mode` is `single`,
`data_dir` is unset, and `.remember/remember.md` is in fact correct here. The defect is a universal
claim in the authority document, and the guard that enforces it (`check-handoff-path.py`,
`CONSUMED_PATH = ".remember/remember.md"`) is a hardcoded constant that would enforce the wrong path
in row 4 without noticing.

**Fix:** *"no hint means this rule's path **unless `data_dir` is set** — which this install does not
set (all three config layers absent, verified)."*

### M3 — "THREE triggers (external, `per_session`, degraded)" never says a linked git worktree is one

**(a).** The enumeration appears, asserted as a *corrected and exhaustive* count, in four places:
`docs/plugins.md:86-87`, `.agents/skills/handoff/SKILL.md:17`,
`.claude/hooks/enforce-handoff-path.sh:75-79`, and `docs/dashboard-entries.md:14858`. The first
trigger is described as *"an external store"* / *"external mode (the store is outside the project)"*.

In a **linked git worktree**, `_resolve_memory_project_dir` redirects memory to the main checkout
(remember's own #56), so `REMEMBER_ROOT != PROJECT_DIR` and leg 1 fires — with no external store, no
`data_dir`, and nothing configured. **Measured**, a temp main repo plus `git worktree add`:

```
CLAUDE_PROJECT_DIR = <main>      → NO HINT PRINTED
CLAUDE_PROJECT_DIR = <worktree>  → Write next handoff to: <main>/.remember/remember.md
```

This is this repo's standard workflow — `superpowers:using-git-worktrees` is in the tool table, and
the branch under review is itself being reviewed from a linked worktree. It is also the mechanism
behind the one thing round 3 *did* notice and filed in the wrong section (see *Where I disagree*):
the plugin's own `doctor.sh` reports `Storage mode: legacy` from the main checkout and
`Storage mode: external` from a worktree, **with an identical `REMEMBER_DIR` in both**. Reproduced:

```
from main checkout : OK Storage mode: legacy (in-project: <repo>/.remember)
from this worktree : OK Storage mode: external (<repo>/.remember)
```

So "external" in both the branch's prose and the plugin's own diagnostic can mean *"you are in a
worktree"*, and a reader who has configured no external store will not match their situation to
the word. `git grep -i worktree` over every branch-touched file returns nothing on this subject.

Count-wise the branch is defensible — a worktree fires the *same boolean leg*, so "THREE things
print it" is not arithmetically wrong. The defect is the **label**: leg 1's dominant local cause is
never named, in four documents that exist to stop a reader guessing.

### M4 — `:1571-1640` does not bound the mechanism it is cited for, and it was wrong on arrival

**(a).** The branch grants itself one deliberate exception to its own thesis: it writes fresh
vendored line numbers, version-stamped. `docs/dashboard-entries.md:14886-14888` and
`docs/memory/a-vendored-line-number-has-no-owner.md:5`:

> *"Measured against `remember` **0.33.0**, a **2,027-line** hook: `REMEMBER_HANDOFF` `:1171`
> (per-session `:1168`, mode selected `:1164`), emit `:1666`, delivery record `:1571-1640`, hint
> `:1546`."*

**Six of seven are exact** — I read each line out of the installed hook: `:1164` is
`config_into HANDOFF_MODE ".handoff_mode" "single"`; `:1168` and `:1171` are the two
`REMEMBER_HANDOFF=` assignments; `:1546` is `echo "Write next handoff to: $REMEMBER_HANDOFF"`;
`:1666` is `echo "=== LAST HANDOFF ==="`; the hook is 2,027 lines. (`:1153-1163`, cited in the
memory file for the stale comment, also bounds it exactly.)

`:1571-1640` does not. It opens mid-sentence in a comment (`:1571` = *"# The cost of keeping it is
that the same note can be delivered more than once,"*) and closes on an unrelated definition
(`:1640` = `_remember_handoff_fingerprint() {`). The delivery record it names — the thing the claim
*"delivery is fingerprinted … so reading one does not consume it"* rests on — is implemented
**outside** the range: the state paths at `:1599`/`:1601`, the delivery check at `:1648`, the record
read at `:1653-1660`, and the record **write** at `:1696-1698`.

So the one place the branch chose to publish fresh vendored locators produced an instance of the
defect it is arguing about — not by rotting, but wrong when written, in both a dashboard entry and a
memory file. That is worth more than the citation: it is evidence *for* the branch's thesis that the
convention it kept is not safe either. **Fix:** cite the symbol (`REMEMBER_HANDOFF_STATE`) rather
than a range, which is the branch's own rule.

---

## Low

### L1 — the refusal's replacement locator is still not pasteable, which was round 3's L1

**(b).** Round 3 L1: *"The refusal at `:68` still prints `grep -n 'REMEMBER_HANDOFF=' <the hook>`,
which produces a shell syntax error when pasted. Supply an actual plugin-cache path."* The fold
supplied the path — split across two lines. Rendered (stub guard exiting 1; `rc=2`, stdout empty,
33 stderr lines, no sentinel expansion — `$TMPDIR` and `$EDITOR` survive literally):

```
  To check it yourself, the assignment is named REMEMBER_HANDOFF, in
  ~/.claude/plugins/cache/claude-plugins-official/remember/<version>/scripts/
  session-start-hook.sh  (two assignments: per-session, then the shared one).
```

The path is 96 characters and the box is ~76 wide, so the wrap is forced by the layout rather than
careless — but the line break falls **inside the path**, after `scripts/`, and a reader copying what
they were told to check gets a directory and an orphan filename. Third version of this line, third
version that cannot be used as given. **Fix:** shorten the prefix so the path survives on one line
(*"under `~/.claude/plugins/cache/`, at `claude-plugins-official/remember/<version>/scripts/session-start-hook.sh`"*),
or break before `~/`, not inside it.

### L2 — removing the flag also removed the `=`, and the "two assignments" count is no longer true of the token given

**(b).** All four sites now name the bare symbol: *"the assignment is named `REMEMBER_HANDOFF` …
TWO of them"* (`SKILL.md:15`), *"`REMEMBER_HANDOFF` in `…/session-start-hook.sh` — there are TWO
assignments"* (memory file `:26`), the same in `check-handoff-path.py:48-51`, and
`enforce-handoff-path.sh:68-70`. The previous text searched `'REMEMBER_HANDOFF='`.

**Measured** against the installed hook:

| token | lines matched | assignments matched |
|---|---|---|
| `REMEMBER_HANDOFF=` | 2 | **2** — `:1168`, `:1171`, exactly as claimed |
| `REMEMBER_HANDOFF` | **24** | **5**, across 3 distinct variables (`REMEMBER_HANDOFF`, `REMEMBER_HANDOFF_STATE` ×2, `_REMEMBER_HANDOFF_STATE_LEGACY`) |

Strictly the sentence is true — there are two assignments *to that name*. Operationally the reader
told to find "two assignments" finds twenty-four lines and three similar names, and the one
character that disambiguated them was dropped as collateral of the flag removal. Keep the `=`: it is
not a flag and no tool disagrees about it.

---

## Checked and found SOUND

Things I tried to break and could not. Each names what I ran, because a list of adjectives is not
evidence.

* **The plugin path the fold introduced is correct.** `find ~/.claude/plugins -name session-start-hook.sh`
  → exactly one hit,
  `~/.claude/plugins/cache/claude-plugins-official/remember/0.33.0/scripts/session-start-hook.sh`.
  The `<version>` placeholder is the right shape.
* **"TWO assignments: per-session, then the shared one"** — order and count correct for
  `REMEMBER_HANDOFF=`: `:1168` per-session, `:1171` shared. (Operational caveat is L2, not a
  correctness defect.)
* **BSD grep, ugrep and ripgrep legs all reproduce** — table in H2. I read the *output*, not `$?`,
  because the probes were piped and a pipe's exit status is the last command's.
* **The refusal renders safely.** rc=2, empty stdout, 33 stderr lines, the `VERDICT_OUT` expansion
  intact, and nothing else expands inside the unquoted heredoc — `$TMPDIR` (`:59`) and `$EDITOR`
  (`:82`) both survive as literals.
* **The `:1153-1163` citation for the stale hook comment bounds it exactly** — `:1153` opens
  *"# Per-session mode needs CURRENT_SESSION_ID"*, `:1163` closes *"# applied."*. The memory file's
  account of that comment being contradicted fifty lines down is also right: `:1180-1196` is the
  hook correcting itself (*"NOT withheld on degrade … The honest fix is not silence"*), and the code
  at `:1546` matches the second comment, not the first.
* **`docs/reviews/claude/velocity-177-r5-claude.md:161` exists and says what the entry says it
  says** — *"`docs/plugins.md` (1: `session-start-hook.sh:795`)"*, inside a *Siblings — searched*
  block about locator scope. The dashboard's softened wording (*"which overstates what that review
  said"*) is the accurate reading; I checked whether the harder original claim was recoverable and
  it is not.
* **The store census is right and my first count was wrong.** `ls -1` gives 102, `ls -A` gives
  **104**, exactly one entry matching `remember*`. The entry's 104 is reproducible; I record my own
  miss because it is the same defect class the branch is about (the population, not the code).
* **"FIVE sibling documents cited `:795`"** — all five did, verified at the base commit `2413b003`
  (list in H1). `:800-802` was unique to `plugins.md`; the other three ranges were shared.
* **`docs/plugins.md` is 260 lines**, exactly on its stated budget, and the branch's claim of a
  five-for-five line swap holds (`git diff 2413b003 b972afee -- docs/plugins.md`: 5 added, 5
  removed in the RULE box).
* **Memory file 2's provenance paths resolve on the branch it names.**
  `docs/reviews/architecture-review-2026-10-13.md` and the nine `backlog-249-260-r{11,12,13}-*.md`
  halves do **not** exist at `b972afee`, which looked like round 1 M4's defect recurring — but a
  sweep of every local and remote ref finds all of them on `backlog-249-260-fixes`, which the
  provenance line names first. Not a finding; disclosed by naming the branch. ⚠ It does mean those
  paths are hostage to an unmerged branch, which is worth knowing when that branch lands or dies.
* **`check-handoff-path.py`'s guard and self-test still cover their stated falsifier.**
  `--self-test` → `10/10 passed` (7 text cases + 3 file cases, matching the printed declaration),
  normal invocation rc=0 against the live `SKILL.md`. The two documented near-misses
  (`.remember/handoff.md`, bare `remember.md`) are present and both return 1; missing and empty
  files return 2 with *"Treat this as NOT RUN"*. The `[FAIL] …: got … want …` and the literal word
  `passed` — both load-bearing contracts with `check-plan-code.py`, per the comments at `:101` and
  `:160` — are intact in the output I captured.
* **Shell syntax of the edited hook** — `bash -n .claude/hooks/enforce-handoff-path.sh` clean; the
  hook exits 0 fast for a non-handoff skill name (tested with `tool_input.skill = "brief"`).
* **Agreement, not findings** (the brief rules these out and I agree): removed line numbers are not
  re-pointed; `MEMORY.md` over budget; the standing `dev-process.md` WARN; trailing whitespace
  inside a filed review. On the last — `git diff --check 755c35a6 b972afee` fails at
  `docs/reviews/codex/plugins-handoff-citations-r3-codex.md:13`, i.e. the same property as round
  2's L2, again inside Codex's own filed text. Recorded, not re-raised.

---

## CANNOT RUN

⛔ **These are validation failures, not passes. Treat every one as NOT RUN.**

* **`GNU grep has no -S` — NOT RUN.** No GNU grep on this machine: `ggrep` absent at `/usr/bin`,
  `/usr/local/bin` and `/opt/homebrew/bin`; `/usr/bin/grep` is BSD; the shell `grep` is a `ugrep`
  wrapper. Round 3's Codex half also could not run it (its source build failed). **Both halves of
  round 3 have now failed to measure the claim that four repo documents state as measured** — which
  is H2, and H2 is the finding, not this bullet.
* **`check-selftest-counts.py` exits 1 — NOT RUN as a verdict on the branch.** It names
  `check-paid-caller-arrival.py` and `check-plan-code.py` as having red suites.
* **`check-plan-code.py --self-test` exits 1 — 175/178.** All three failures are one cause:
  `CANNOT RUN — node_modules/typescript is missing under <worktree>, so the mutation tree would be
  incomplete and every verdict below it an artefact. TREAT THIS AS NOT CHECKED`. `node_modules` is
  absent in this worktree. Pre-existing, outside this diff, and the guard says so itself — but it
  means **the mutation sweep is unmeasured here**, so no claim below it is available to this round.
* **`check-plan-code.py --mutate .` — NOT RUN**, deliberately: it needs the `node_modules` above,
  and nothing in this branch's diff is in a mutation manifest.
* **`check-test-counts.py --results jest-results.json` — NOT RUN**: no `jest-results.json` in this
  worktree (the unit suite was not run; this is a docs branch and CI produces that file).
* **The PR-only steps — `check-dashboard-entry.py --base …` and `check-review-recorded.py --base …`
  — NOT RUN**: both take a `--base` the CI job supplies from the PR, and `check-review-recorded.py`
  keys on `--diff-filter=A` over committed Codex verdicts, so a locally-written, uncommitted review
  file is invisible to it either way.
* **Historical claims not replayable from here**, and therefore not validated by me: the pre-0.33.0
  hook's length (the branch withdraws this itself — correct), the authoring-time installation state,
  and the round-11-to-13 harness experiments on `backlog-249-260-fixes` (I verified the documents
  exist; I did not re-run their subjects).

---

## Instruments

* `git log`/`git show`/`git diff` across `2413b003 → 678a35db → 55975f92 → 7cf48d43 → 755c35a6 →
  b972afee`, per-commit and cumulative; commit messages read before diffs.
* `git grep` at the **base commit** for the counterfactual inventory (H1), and `git ls-files -s` for
  the symlink's object mode.
* All repo-wide greps scoped with `':(exclude)docs/reviews'` so no part of this review was primed by
  the Codex half's filed text — round 1's Claude half disclosed that hazard and it is the reason the
  exclusion is here.
* **The installed `remember` 0.33.0 hook, executed**, not read: a 6-cell store × mode × session-id
  matrix (M2) and a `git worktree` pair (M3), each in a throwaway project with `$HOME` redirected to
  a temp directory so the real user-global config was never written to or read; `REMEMBER_DEFER=0`
  for determinism.
* The plugin's own `doctor.sh`, run twice — from the main checkout and from this linked worktree
  (M3).
* The refusal text **rendered** through a stub `check-handoff-path.py` exiting 1, under the real
  hook, capturing rc, stdout and the full 33-line stderr (L1, and the heredoc-expansion check).
* `/usr/bin/grep` (BSD) at `-r`, `-R`, `-RS`; `rg 14.1.1`; `type -a grep` for the `ugrep` wrapper;
  `ugrep --version` 7.8.4.
* **Every `python3 scripts/...` step extracted from `.github/workflows/ci.yml` by parsing the
  workflow**, not from memory — 58 invocations, 54 executed, 4 excluded for the reasons in CANNOT
  RUN. Results: **51 rc=0**, 3 rc=1 (`check-review-rounds.py` → B1; `check-selftest-counts.py` and
  `check-plan-code.py --self-test` → node_modules, CANNOT RUN).
  ⚠ My first sweep returned `rc=127` on all 54 and I nearly reported 54 red guards: the cause was
  `timeout` not existing on macOS, not the guards. Recorded because a reviewer who trusts an
  implausible negative is the failure mode this repo keeps paying for.
* `check-review-rounds.py` re-run with this file on disk: rc=1, **round 3 cleared, round 2 still
  named** (output quoted under B1). The claims in *Checked and found SOUND* about the handoff guard
  were all executed after writing them, not asserted from reading the code: `--self-test`
  `10/10 self-test cases passed` (7 text + 3 file, matching its own printed declaration), normal
  invocation `ok — .agents/skills/handoff/SKILL.md names .remember/remember.md` rc=0, `bash -n` rc=0,
  and a non-handoff skill name (`brief`) → rc=0 with **0 bytes** of output.

---

## Where I disagree with the Codex half

I agree with all three of round 3's findings on the merits and did not find them overstated. Where
I part from it:

1. **Its M1's repair is not what the fold did, and the fold is worse for it.** M1 asked to *"name
   the supported binary or provide implementation-specific commands."* The fold instead removed the
   command. That is defensible for the vendored-plugin search, but it deleted the only executable
   instruction for the **repo inventory**, where a portable command exists and is `git grep` (H1).
   M1 also named `SKILL.md:15`'s surviving `-R` claim and the fold left it (M1 above).
2. **It filed a finding inside `Checked and found SOUND`, and so nothing acted on it.** The bullet
   *"`doctor.sh` reports legacy storage from the main checkout; from this linked worktree it reports
   the shared main-checkout store as **external**. The dashboard quotation needs that
   execution-directory qualification"* is a defect with a prescribed fix sitting in the section
   reserved for things that held. The fold touched no dashboard file, and the qualification is still
   absent. I reproduced the behaviour and found it is larger than a dashboard wording issue — it is
   an unnamed cause of hint trigger 1 in four documents (M3).
3. **It reports `0 Blocking` and the branch is CI-red.** Codex round 3 checked the documentation and
   handoff guards; `check-review-rounds.py` is neither, and it fails on this branch's own rounds 2
   and 3 (B1). A reviewer cannot be faulted for not noticing its own absence — which is the argument
   for both halves running, and the reason this file exists.
4. **On its M2, I think the fold over-corrected in the safe direction and under-corrected in the
   dangerous one.** M2 was right that *"the path above when the store is in-project"* was false, and
   the fold's replacement (*"a `data_dir` setting moves it"*) is accurate — measured. But it files
   `data_dir` under *"things that print a hint"*, and the cell where `data_dir` moves the file with
   **no** hint is the one that can silently lose a handoff. Neither M2 nor the fold reaches it (M2
   above).

---

**Result: 1 Blocking / 2 High / 4 Medium / 2 Low. This round is not clean.**

Verdict for the coordinator, stated so it cannot be read as clearance: filing this file clears
`check-review-rounds.py` for **round 3 only**. Re-run after committing:
`python3 scripts/check-review-rounds.py` — it still names **round 2** until that half exists or a
written reason does, and `REVIEW GAP:` is not the right reason because the half could have run.
