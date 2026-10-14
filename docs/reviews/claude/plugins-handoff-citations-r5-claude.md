# Round 5 — Claude half: the withdrawal deleted a measured TRUE clause, and `rg` cannot see the two files this branch is about

**Verdict: 0 Blocking / 2 High / 2 Medium / 5 Low — ⛔ NOT CONVERGED.**

Reviewed `1a2cc8de` (the round-5 fold), its testimony `d80b12f9`, `docs/reviews/codex/plugins-handoff-citations-r5-codex.md`, rounds 1–4 both halves, and `git diff origin/master..1a2cc8de`. Mandate was to REFUTE.

⭐ **The thirteenth incomplete withdrawal exists and a position sweep could not have found it.** Every phrase-sweep hit for a retired position in a live file is a **quotation** recording the retirement — I checked each one and none is an assertion. The thirteenth instance is the **mirror form**: the withdrawal of a false LABEL deleted a TRUE measured clause along with it, at every site, with no mention in the commit. Finding it needs a sweep for *what the replacement no longer lets a reader derive*, not for retired wording. That is H1.

---

## Blocking

None established.

---

## High

### H1 — The linked-worktree trigger was DELETED from all three instruction sites, the new mechanism MISPREDICTS it, and this re-opens r4 Codex M3

**Measured, three consecutive runs, a green positive control (`=== REMEMBER ===` present) on every one:**

| `CLAUDE_PROJECT_DIR` | config | positive control | hint | printed path |
|---|---|---|---|---|
| main checkout | default (no `data_dir`) | ✅ | **NO** | — |
| linked worktree of the same repo | default (no `data_dir`) | ✅ | **YES** | `<main>/.remember/remember.md` |

The store directory was created only under `<main>/.remember`; `<wtree>/.remember` never existed. Deterministic 3/3.

**The mechanism in the vendored source.** `REMEMBER_DIR` is not derived from `PROJECT_DIR`. In `lib-memory-dir.sh` the resolution is `MEMORY_PROJECT_DIR=$(_resolve_memory_project_dir "$PROJECT_DIR")` and then `REMEMBER_DIR=$(_resolve_remember_dir "$_data_dir_raw" "$MEMORY_PROJECT_DIR")`; `_resolve_memory_project_dir` returns **the main checkout** when `PROJECT_DIR` is a linked worktree (its own comment: *"memory should live with the main checkout so it survives `git worktree remove`"*). So `REMEMBER_ROOT` = `<main>` while `PROJECT_DIR` = `<worktree>`, the strings differ, and the hint fires. Cited by symbol, per this branch's rule.

**What the fold did to that fact.** Live `worktree` tokens at the three sites that describe the hint:

| site | at `7bf8867c` (r4) | at `1a2cc8de` (HEAD) | the survivor |
|---|---|---|---|
| `.claude/hooks/enforce-handoff-path.sh` | 1 bare + 1 `skip-worktree` | **0 bare** + 1 `skip-worktree` | unrelated (`git grep` paragraph) |
| `docs/plugins.md` | 2 | **1** | unrelated (`REVIEW GAP` line `:148`) |
| `.agents/skills/handoff/SKILL.md` | 0 bare (3× `skip-worktree`) | **0 bare** | unrelated |

The r4 text that is gone, verbatim:

* hook `:88` — *"the store directory is not an immediate CHILD of the project directory -- **which INCLUDES a linked git worktree**, and a data_dir nested two deep"*
* `plugins.md:87` — *"(a resolved store root ≠ the project dir ITSELF — ⚠ **a linked WORKTREE counts**, and r4 M3: so does a `data_dir` that stays INSIDE the project; …)"*

**This was a closed finding.** `docs/reviews/codex/plugins-handoff-citations-r4-codex.md` **M3** faulted the sites for *"omitting the linked-worktree case"*; `docs/reviews/claude/plugins-handoff-citations-r4-claude.md:459–462` measured it (*"A main checkout printed no hint; a linked worktree of the same repo printed `Write next handoff to: <main>/.remember/remember.md`. 'A linked WORKTREE counts' is correct"*). The r4 fold closed it at two sites. The r5 fold deleted both and left the skill as it was, so **r4 Codex M3 is now more open than it was at r4** — and the fold's commit message does not contain the word *worktree*.

**The replacement cannot recover it.** The published mechanism is *"the store directory's LEXICAL PARENT differs, as TEXT, from the project directory."* No site says where the store directory is in a linked worktree. A reader applies it as written — store `<worktree>/.remember`, parent `<worktree>`, equal to the project directory — and predicts **no hint**. That is the opposite of the measurement. The fold's own instruction *"predict nothing from where the store is — read the printed path"* is the mitigation, but it is advice to distrust the mechanism the same sentence just published, and the hook's refusal text still tells a blocked reader, flatly, `Write the handoff to:  .remember/remember.md`.

**Why this matters here specifically.** The operational consequence is that in a linked worktree the session-continuity handoff belongs in the **main checkout's** `.remember/remember.md`, not the worktree's. This repo runs linked worktrees as routine — this review was produced in one (`.../scratchpad/wt-plugins`) — so the deleted clause is the one most likely to be needed.

The fact survives at exactly one place: `docs/dashboard-entries.md:14905–14906`, in the language of the retired label (*"from a linked worktree the same store reports as EXTERNAL"*), inside a dated retrospective. That is a record, not a rule a reader follows at the moment of need — which is the distinction this branch's own narrowing turns on.

**Repair.** Restore the worktree trigger at the skill, the hook and `plugins.md`, as a consequence of the mechanism rather than a label: say that the store follows the **main checkout** in a linked worktree (`_resolve_memory_project_dir`, `lib-memory-dir.sh`), so the lexical parent is `<main>` while `PROJECT_DIR` is `<worktree>`. State in the commit that r5 deleted it, so this does not become a fourteenth instance.

### H2 — `rg` is offered as the filesystem leg of the prescribed cross-check and misses the two files this entire branch is about; the one `rg` limit named is not the cause

The cross-check is published as *"compare it against `git grep --cached -l` **and** against a filesystem walk (`grep -rl` / `rg`)"* — `rg` offered as an equal alternative — at the skill `:17`, the memory lesson `:21`, `process-rationale.md:371`, the guard comment, the hook, and the dashboard. The single `rg` limit named at every site is **"default `rg` skips ignored files"**.

**Measured in this worktree, stdin closed, explicit path argument, needle `session-start-hook`:**

| leg | files found |
|---|---|
| `git grep -l session-start-hook` | **13** |
| `/usr/bin/grep -rl session-start-hook .` | **13** |
| `rg -l session-start-hook .` | **11** |
| `rg --hidden -l session-start-hook .` | **13** ← control |

The two files default `rg` misses:

```
.agents/skills/handoff/SKILL.md
.claude/hooks/enforce-handoff-path.sh
```

Those are the vendored skill this branch exists to protect and the hook that enforces it — layers 3 and 2 of the mechanism `plugins.md` documents. `--hidden` recovers **exactly** those two and nothing else, so the cause is **hidden (dot-prefixed) paths**, not ignored files: neither file appears in any `.gitignore`, and `git grep` lists both.

**Consequences, in the direction that matters:**

1. A reader who takes the `rg` option sees a disagreement and finds **no matching cause** in the published innocent-cause list (ignored, `.git`, submodules, binary, case-only rename) — the list sends them hunting for an index mask that is not there.
2. A reader who uses `rg` as their *only* filesystem leg — which the `/` in "`grep -rl` / `rg`" permits — concludes those two files **do not exist on disk**. That is the original defect of this branch (an inventory that silently missed `SKILL.md`) reproduced by the instruction written to prevent it.

**A third `rg` blind spot, also measured** (traversal form, in a throwaway repo, controls green): a committed binary containing the needle is found by `git grep -l` and `/usr/bin/grep -rl` and **missed by default `rg`**. So the fold's "binary files" innocent cause is real, but it is the same tool failing a second way. Three distinct `rg` blind spots; one is named.

⚠ Related, and worth a line because it bears on every `grep -rl` in these documents: **`grep` is a shell function on this machine** (`type -a grep` → *"grep is a function"*), consistent with `process-rationale.md`'s note about a `ugrep` wrapper. Every measurement in this review used `/usr/bin/grep` explicitly. A prescribed `grep -rl` is not a determinate instrument here, and no site says so.

**Repair.** Either name `rg`'s hidden-path and binary behaviour alongside its ignore behaviour, or stop offering `rg` as an interchangeable filesystem leg and prescribe one invocation that reaches dot-paths (`rg --hidden`, or `/usr/bin/grep -RSl` with its symlink leg stated).

---

## Medium

### M1 — The commit claims the four limits are named at six sites; the site it singles out as *"the reader-facing"* one names two

Commit `1a2cc8de`: *"it is now stated as a PROMPT TO LOOK and never a proof, **with the four measured limits named**: agreement proves nothing about CONTENT; disagreement has innocent causes (…); the filesystem leg's reach is TOOL-SPECIFIC; and outside a repository `git grep` exits 128 … Sites: the skill, the hook comment, the guard comment, `process-rationale.md`, the memory lesson, and **the reader-facing dashboard entry**."*

Per-site presence, counted over each file:

| site | agreement≠content | innocent causes | TOOL-SPECIFIC | rc=128 |
|---|---|---|---|---|
| skill | ✅ | ✅ | ✅ | ✅ |
| hook comment | ✅ | ✅ | ✅ | ✅ |
| guard comment | ✅ | ✅ | ✅ | ✅ |
| `process-rationale.md` | ✅ | ✅ | ✅ | ✅ |
| memory lesson | ✅ | ✅ | ✅ | ✅ |
| **dashboard entry** | ✅ | ✅ | **✗** | **✗** |

The dashboard text (`docs/dashboard-entries.md:14860`) ends at *"Agreement is not a guarantee: compare the CONTENT when content is what matters"* — no tool-specific reach, no rc=128 — and its innocent-cause list drops `.git` internals, which it carries at the five other sites. So the dashboard names **2 of 4**, and the commit's "four limits … six sites" is not reproducible as written. Its being the reader-facing site is what makes this worth filing rather than a Low: it is the one a person outside the review loop reads.

### M2 — The fold declares interpreter parity NOT RUN while the same round's other half had already run it, on this machine

The fold's NOT-RUN list: *"interpreter parity (local 3.14, CI pins 3.12)"*.

* `python3.12` is installed at `/usr/local/bin/python3.12` → **Python 3.12.9**; CI pins `python-version: '3.12'` (four jobs in `.github/workflows/`).
* The r5 Codex half being folded ran **its entire guard set** as `python3.12 scripts/…` and recorded *"Python 3.12.9 is available"* and *"The pin guard confirms the interpreter matches the CI major/minor pin."*
* I ran the fold's own published 29-command set under both: **3.14 → 29 green / 0 red**, **3.12 → 29 green / 0 red** (set named under *Instruments*).

A CANNOT RUN is a failure here, not a pass. One declared over something reachable on the same machine — and already reached in filed testimony from the same round the fold was folding — degrades the instrument in the same way a false green does, just in the opposite direction: it spends a failure the evidence does not support, which makes the rest of the list cheaper to read past.

---

## Low

### L1 — The published derivation is wrong in three of the five branches of the case statement it claims to describe

Claim (skill `:19`, hook `:46–47`): *"`REMEMBER_ROOT` strips trailing slashes, then drops everything after the last `/`."*

Actual, from the `REMEMBER_ROOT` case statement in `_remember_memory_paths` (`lib-memory-context.sh`):

* the strip loop is guarded `&& [ "$_remember_root_scratch" != "/" ]` — it does not strip `/` down to empty;
* `case (/)` → `REMEMBER_ROOT="/"`;
* `case (*/*)` → `${…%/*}`, **and if that is empty, `/`** (the `[ -n "$REMEMBER_ROOT" ] || REMEMBER_ROOT="/"` line);
* `case (*)` — no slash at all → `REMEMBER_ROOT="."`.

Reachable divergence: `data_dir: "/notes"` is accepted by `_resolve_remember_dir`'s absolute branch, so `REMEMBER_DIR="/notes"`; the code yields `/`, the published rule yields `""`. The hint is YES either way, so **no row's outcome changes** — this is a precision defect, not a wrong prediction. It is filed because the whole point of replacing the fourth label with a mechanism was that a mechanism is checkable, and three of five branches are not described. The no-slash branch is reachable only through the Windows `[A-Za-z]:\\*` form, which is why it is Low and not higher.

**And one value falls outside the stated mechanism entirely.** `data_dir: "/"`: the mechanism predicts a hint (`REMEMBER_ROOT="/"` ≠ `PROJECT_DIR`). Measured, the 0.33.0 hook **aborts** — `session-start-hook: ERROR -- failed to source …/log.sh`, 139 bytes, and **neither** `=== HANDOFF ===` nor `=== REMEMBER ===`. `bash -x` shows `REMEMBER_DIR=/` then the failed `source`. ⚠ My first pass recorded this row as `hint=NO`; that was **my own false negative**, caught only by adding a per-row positive control. Every other row in the table below printed `=== REMEMBER ===`.

**The full row set I ran against the installed 0.33.0 hook** (isolated `HOME` and project per row, `.git` directory present so `MEMORY_PROJECT_DIR == PROJECT_DIR`, stdin closed, positive control asserted per row):

| `data_dir` | predicted by the stated mechanism | measured hint | agrees |
|---|---|---|---|
| `notes` | no | NO | ✅ |
| `a/b` | yes | YES | ✅ |
| `.` | no | NO | ✅ |
| `./notes` | yes | **YES** | ✅ |
| `notes/` | no | NO | ✅ |
| `a//b` | yes | YES | ✅ |
| absolute immediate child | no | NO | ✅ |
| absolute outside project | yes | YES | ✅ |
| immediate-child symlink → outside | no | NO | ✅ |
| `..` | no | **NO** | ✅ |
| unset | no | NO | ✅ |
| empty | no | NO | ✅ |
| `~` | yes | YES | ✅ |
| `/` | yes | **hook aborts, prints nothing** | ✗ |

So the mechanism is **true of 13 of 13 rows where the hook completes**, including the two that refute the retired label, and the "no resolution of `.`, `..` or symlinks" clause is confirmed in both source and measurement. H2's substance is sound; L1 is about the derivation sentence, not the comparison.

### L2 — *"the hint fires iff that string differs from `PROJECT_DIR`"* is false, and the same sentence supplies the counterexample

Skill `:19` and hook `:48` both state a biconditional. Two clauses later each enumerates ② `per_session` and ③ degraded `per_session` as the other two things that print the hint — so the sentence refutes itself.

**Measured with `REMEMBER_ROOT == PROJECT_DIR` in every row** (default store `<proj>/.remember`), green positive control each:

| config | hint |
|---|---|
| `{}` | NO |
| `{"handoff_mode":"per_session"}` | **YES** |

The hook's own test is a three-way disjunction: `if [ "$REMEMBER_ROOT" != "$PROJECT_DIR" ] || [ -n "$PER_SESSION_HANDOFF" ] || [ -n "$HANDOFF_MODE_DEGRADED" ]; then`.

⚠ **The three H2 sites do not say the same thing, and the one that is right is the shortest.** `docs/plugins.md:87` states the comparison without "iff" and is correct as written; the skill and the hook both overclaim. Narrow "iff" to "this trigger fires iff", or drop it.

### L3 — L2's own fix left the list non-parallel, and the two copies diverge in form

The r5 L2 finding (*"the list lacks an introduction"*) **is fixed** — the skill now has the colon and the ①②③ markers. Residual:

* skill `:19` — *"THREE things print it, not one: ① **the store directory's LEXICAL PARENT differs, as TEXT, from the project directory.** … ② `per_session` mode … ③ a DEGRADED `per_session` request"*: ① is a finite clause, ② and ③ are noun phrases. Read top to bottom, "three things print it: the parent differs" does not parse as a thing.
* hook `:43–54` uses `(1)(2)(3)` and a period rather than a colon, which makes (1) a full sentence and leaves (2) and (3) as fragments.

Both copies are now readable; neither is parallel, and they differ in marker style and punctuation. The skill also drops the hook's `(.handoff_mode)` gloss on ②.

### L4 — The guard comment's new `ls` broke the sentence it sits in

`scripts/check-handoff-path.py:48–51`:

```
# is stable is the SYMBOL and the PATH — `REMEMBER_HANDOFF` in
# `ls ~/.claude/plugins/cache/claude-plugins-official/remember/*/scripts/session-start-hook.sh`
# — r5 L1: WITH the `ls`. Pasting the bare glob EXECUTES the hook, …
```

A symbol is not *"in"* an `ls` invocation. The hook got the same repair right by keeping the prose and the command apart (`:36–38`: *"This locator is also a runnable discovery command … "* then the command on its own line). This is the fold's own L2 class — a correction applied to the token rather than to the sentence — in the file the fold was editing to fix L1.

The L1 behaviour itself is correct; see *Checked and found SOUND*.

### L5 — *"`bash -n` clean"* names no subject

The fold touched exactly one shell file and `bash -n .claude/hooks/enforce-handoff-path.sh` is rc=0, so the claim is true. But it is a verdict over an unnamed population, which is the shape the fold's own L3 objected to in *"14/14 green"*. Name the file. (Weakest finding here; filed only because the commit is otherwise careful to name its sets.)

---

## Checked and found SOUND

**H1's detection half — reproduced, with a green control before and after each sever** (throwaway repo, `git 2.49.0`, controls on an ordinary tracked file `d_control.txt` green at both ends):

| fixture | `git grep` | `git grep --cached` | `/usr/bin/grep -r` |
|---|---|---|---|
| `assume-unchanged`, edited on disk | `NEEDLE OLD` (stale indexed) | `NEEDLE OLD` | `NEEDLE replacement` |
| `skip-worktree` | **0** | finds it | finds it |
| tracked, deleted from worktree | **0** | finds it | **0** |

**All four published limits — reproduced:**

* *Agreement while reading different content:* the `-l` form of all three lists `a_assume.txt` identically while `git grep -h` returns `NEEDLE OLD` and `cat` shows `NEEDLE replacement`.
* *Innocent causes:* ignored file — `git grep` 0, `/usr/bin/grep -rl` finds it, default `rg` misses it; binary — both git legs find it, default `rg` misses it; `.git` internals — `/usr/bin/grep -rl .` returns `.git/logs/HEAD`, `.git/logs/refs/heads/master`, `.git/COMMIT_EDITMSG`, none of which git legs return; submodule — `git grep -l` misses `sub/s.txt`, `--recurse-submodules` finds it, filesystem grep finds it; case-only rename — `git status --porcelain` **empty** while `git grep -l` says `Subject.txt`, `ls` and filesystem grep say `subject.txt`.
* *Tool-specific reach:* `/usr/bin/grep -rl` MISSES a matching file behind a symlinked directory; `-Rl` also misses it (BSD `-R` has no symlink sense); `-RSl` finds it — positive control for the leg.
* *rc=128 outside a repository:* `git grep -l NEEDLE` → **128** at `/` and in an empty non-repo tmpdir, with `fatal: not a git repository`. An error, not an empty result. ✅

**L4 (GNU grep 3.12) — verified from source, with a positive control.** Downloaded `grep-3.12.tar.xz` (1,918,448 bytes) from `ftp.gnu.org/gnu/grep/`; `src/grep.c:487–488`:

```c
static char const short_options[] =
"0123456789A:B:C:D:EFGHIPTUVX:abcd:e:f:hiLlm:noqRrsuvwxyZz";
```

Uppercase `S` occurrences: **0**. Control — uppercase `R` occurrences: **1** (and `-R` is real). `grep-3.12.tar.xz` is also the **newest** release in that directory, so "GNU grep 3.12 has no `-S`" is both true and current. The version qualification is present in the live skill, `process-rationale.md` and the memory lesson.

**L1 (the `ls`-prefixed locator) — run at zero, one and several matches**, isolated `HOME`, stub hooks that print their argv:

| matches | `ls <glob>` | bare `<glob>` |
|---|---|---|
| 0 | rc=1, names the unexpanded path | rc=**127** |
| 1 | rc=0, prints the path | **EXECUTES the hook** (argv empty) |
| 2 | rc=0, lists both | **runs the FIRST with the SECOND as `$1`** |

Exactly as the fold states. Against the real `HOME` the live glob resolves to one path, rc=0. **Both** locators now carry the `ls` (guard `:49`, hook `:38`), so the "only one of the two" half of r5 L1 is closed.

**Layer-2 enforcement, end to end, ON A COPY** (`.agents`, `.claude`, `scripts`, `docs/plugins.md` copied out; `shasum` of the source `SKILL.md` identical before and after the whole exercise — `82dd4850…`, so nothing was severed in a tracked tree):

| step | guard | hook (`handoff`) | hook (`brainstorming`) |
|---|---|---|---|
| control | **0** | **0** | 0 |
| every `.remember/remember.md` removed (2 → 0 occurrences) | **1** | **2** | **0** ← no collateral block |
| restored | **0** | **0** | — |

On refusal: stdout **0 bytes**, stderr **4,536 bytes** containing `.remember/remember.md` **3 times**. stdout being empty is the right channel shape given this repo's measured *"a refusal on hook stdout reached NOBODY"*. `python3.12 scripts/check-handoff-path.py --self-test` → **10/10**.

**M1 (six tracked files) — reproduced.** `git grep -l session-start-hook origin/master` returns exactly **6**: the five live sites plus `docs/reviews/claude/velocity-177-r5-claude.md`, which is genuinely a filed review and carries the stale locator at its `:161` (`session-start-hook.sh:795`). The qualification now reads correctly at both the skill and the memory lesson. (Cosmetic only: the skill credits "r4 M1", the memory lesson "r5 M1", for the same clause.)

**M2 (the memory lesson) — coherent.** `:21` now leads *"The repairs that were ATTEMPTED were all SUBTRACTIVE or NARROWING … ⛔ r5 M2: 'that worked' is WITHDRAWN"* and closes *"What the evidence supports is the DIRECTION, not the outcome"*, which agrees with `:7`'s *"the repairs are not finished"*. The enumeration that follows is imperative — directions, not outcomes — so it no longer reads as a success claim.

**L3's substitute — the 29-command set reproduces exactly.** The published list expands to **29** invocations (18 bare + 9 `--self-test` + 2 self-test-only), and I got **29 green / 0 red** under both interpreters. All 20 named scripts exist.

**Figures in `git log -1 1a2cc8de`:**

* `plugins.md` **260** lines at both `origin/master` and HEAD; budget **260** (`scripts/check-docs.py:193`). Exactly-at-budget is "tight" by its own case at `:655`, and `check-docs.py` is green. The fold's `docs/plugins.md` numstat is `1 1` — net-zero, as claimed.
* Dashboard `^## ` headings: **307** at HEAD, **306** at `origin/master`. ✅
* `bash -n` rc=0 on the only shell file the fold touched (see L5 on the naming).

**Every vendored line number this branch publishes checks out against the installed 0.33.0** — worth recording because the branch's subject is stale vendored citations: hook total **2,027** lines; `REMEMBER_HANDOFF=` at `:1168` (per-session) and `:1171` (shared) — **two** assignments, bare token on **23** lines; the hint test at `:1544` (`process-rationale.md`'s figure); `Write next handoff to:` at `:1546` (the dashboard's figure — the two sites name the test and the print, not the same line twice); `config_into HANDOFF_MODE ".handoff_mode" "single"` at `:1164`; `echo "=== LAST HANDOFF ==="` at `:1666`.

**The retired-position sweep.** Over every file the branch touches, for *"two that agree can"*, *"as the signal"*, *"immediate CHILD"*, *"not the project directory itself"*, *"project dir ITSELF"*, *"repairs that worked"*, *"(all) FIVE tracked sites"*, *"no twelfth"*, *"prescribe none"*, *"name the corpus"*, *"working-tree content of tracked"*, and `-S`/`-RS` as a prescription: **every hit in a live file is a QUOTATION recording the retirement, not an assertion of it.** The only bare assertions sit in filed review documents (`…r4-claude.md:96`), which are testimony and are not rewritten. The "no twelfth" claim is retracted in the commit rather than left standing, as the commit says.

`docs/process-rationale.md:408–409` (*"there are **three** hint triggers … external mode, per-session, and degraded"*), which the Codex half flagged, is **not** a retired label: `session-start-hook.sh:1126–1127` is the plugin's own usage — *"(external mode only). In legacy mode REMEMBER_ROOT == PROJECT_DIR"* — so "external mode" is the vendor's name for exactly the condition the fold now states as a mechanism. Not filing it. ⚠ But no site connects the two terms, so a reader meeting "external mode" at one site and "lexical parent differs" at three others cannot tell they are one trigger; worth one clause when H1 is repaired.

---

## CANNOT RUN

⛔ **These are failures to validate. Treat every item here as NOT RUN, not as a pass.**

* **Actual host/UI delivery of the refusal.** I established rc=2 with a 4,536-byte stderr and empty stdout, which is the shell contract, not what a user sees. I cannot observe the installed Claude Code UI from this worktree. **NOT RUN** — and this is the repo's own measured failure mode (*"a gate's CHANNEL can be weaker than the gate"*), so it stays open.
* **The commit's claim that *"only a before/after `shasum` caught"* the four lost `SKILL.md` edits.** This is testimony about the author's previous session. Nothing in the tree can confirm or refute it; the only checkable part is that the fold's `SKILL.md` changes are present (2 lines, 4 plausible logical edits), which is consistent and not evidence. **NOT RUN.**
* **The root cause of the `data_dir: "/"` abort.** I established the abort deterministically (`bash -x`: `REMEMBER_DIR=/`, then `source …/log.sh` fails, rc=0 with an ERROR line and no output blocks). Whether that is a plugin defect or an artifact of an isolated `HOME` I did **not** determine. The L1 observation rests only on the measured outcome. **Cause NOT RUN.**
* `check-withdrawal.py` **does not exist on this branch** — stated in the fold, not hidden. The incomplete-withdrawal class, now at **thirteen** instances with H1, has no mechanical guard here, and H1 is the shape a phrase-based guard would also have missed: it is a DELETION, not a standing sentence.
* `check-test-counts.py` — no `jest-results.json`. The `--mutate .` shard matrix and the PR-event forms of the PR-only guards — out of reach on a branch with no PR.
* **Population bound.** The H2 hint rows are 14 `data_dir` values plus a main/worktree pair plus two `per_session` configs, against **0.33.0 only**, on macOS, with `MEMORY_PROJECT_DIR` pinned equal to `PROJECT_DIR` except in the worktree pair. This is a selected set, not a population estimate; no false-alarm rate is claimed for the cross-check.

**Not filed, per the brief and verified as expected:** `check-review-rounds.py` rc=1 (this half's file was absent when measured); `check-review-recorded` red at `1a2cc8de` by design; no PR; filed reviews left as written; nothing merged.

---

## Instruments

* `git log -1 --format=%B 1a2cc8de` read first; `git show 1a2cc8de` (8 files, 35 insertions / 18 deletions); `git show d80b12f9`; `git diff origin/master..1a2cc8de` (3,175 lines); r1–r4 both halves; `git show 7bf8867c:<path>` for before/after comparisons.
* **Vendored source read by symbol, never by line:** `_remember_memory_paths` / the `REMEMBER_ROOT` case statement in `lib-memory-context.sh`; `_resolve_memory_project_dir`, `_resolve_remember_dir`, `_set_store_root`, and the `MEMORY_PROJECT_DIR`/`REMEMBER_DIR` assignments in `lib-memory-dir.sh`; the hint disjunction and `REMEMBER_HANDOFF=` in `session-start-hook.sh`; `lib-env-cache.sh`, `resolve-paths.sh` for how `PROJECT_DIR` arrives.
* **Real executions of the installed 0.33.0 hook**, isolated `HOME` and project per row, `</dev/null`, with a **per-row positive control** (`=== REMEMBER ===` must appear, or the row is reported as "hook did not run"). 14 `data_dir` rows; a `git init` + `git worktree add` main/worktree pair run 3× each; 3 `handoff_mode` rows.
* **Git fixtures in throwaway repos** (`git 2.49.0`), each with an ordinary-tracked-file control green before and after: `assume-unchanged` + edited disk, `skip-worktree`, tracked-deleted-from-worktree, ignored file, committed binary with a NUL, case-only rename, registered submodule (`-c protocol.file.allow=always`), `.git` internals, and `git grep` outside a repository.
* **Layer-2 falsifier on a COPIED tree only.** No tracked file in any checkout was severed; the source `SKILL.md` `shasum` was taken before and after and is unchanged. `git` was never run in `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`.
* **GNU grep 3.12 source** fetched from `https://ftp.gnu.org/gnu/grep/grep-3.12.tar.xz` and `src/grep.c`'s `short_options` inspected, with `R` as the positive control; the release directory listed to confirm 3.12 is current.
* **Locator probes** at 0/1/2 glob matches with stub hooks printing their argv, in an isolated `HOME`.
* **The 29-command invocation set**, each with stdin closed, run under `python3` (3.14.4) and `python3.12` (3.12.9):

```text
check-docs            check-anchors          check-anchors --self-test
check-arch-findings   check-backlog-closure  check-backlog-closure --self-test
check-explainer-delivery                     check-features
check-features --self-test                   check-gate-falsifiability
check-handoff-path    check-handoff-path --self-test
check-main-drivable   check-memory-link      check-plan-file-tags
check-plan-file-tags --self-test             check-plan-task-order
check-producer-enumeration                   check-python-pin
check-python-pin --self-test                 check-rc-contract
check-rc-contract --self-test                check-review-rounds --self-test
check-roadmap-consistency                    check-selftest-counts
check-selftest-counts --self-test            check-selection-card --self-test
check-surface-recall  check-surface-recall --self-test
```

  29 invocations; **29 green / 0 red under 3.14 and 29 green / 0 red under 3.12**. ⛔ This is not the CI suite, and the difference is not a pass.

* ⚠ **Two harness errors of my own, recorded because each would have produced a false finding.** (1) I first reported `data_dir: "/"` as `hint=NO`; the hook had aborted and printed nothing, and only a per-row positive control distinguished "no hint" from "did not run". (2) `rg -l <pattern>` with no path argument **reads stdin** and hangs under a non-tty; one probe had to be killed and re-run with an explicit `.` and `</dev/null`. Every `rg` figure in H2 is from the deterministic form.
