# Architecture review — the `glob` component of `scripts/check-rm-backup.py`: THRASHING, and what the union fold does not cover

> **Anchor:** none. PR #608 and backlog #685 declare no anchor (#685's goal column reads `(tooling/hooks)`), none of
> the 15 names in `docs/anchors.md` has a goal covering an agent-safety hook, and `docs/reviews/` documents are
> outside ADR-0010's scope. I am recording that as a gap, not inventing a name for it.

**Date:** 2026-11-20 · **Subject:** `bash_brackets` and the glob step of `plan` in `scripts/check-rm-backup.py` ·
**Branch:** `rm-backup-hook` (PR #608) · **Measured against:** `4cc1cedf` (the round-5 fold) · **Convened by:** the
arming condition in [`docs/dev-process.md`](../dev-process.md) → *Phases*, row 6, recorded as armed in
[`coordinator/rm-backup-r5-coordinator.md`](coordinator/rm-backup-r5-coordinator.md).

- **Method:** I edited no tracked file except this one. Every probe ran in fresh fixtures under the session scratchpad
  (`…/scratchpad/p6/runs/`). `p6/drv/probe.py` builds a fixture, calls the hook's own `plan()` (the script imported
  unchanged), then runs the command with real `/bin/bash` 3.2.57 in that fixture and diffs the tree. A deleted path
  counts as covered when it, or a directory above it, is in the plan. The environment was the Bash tool's own:
  `LANG=en_US.UTF-8`, `LC_ALL` unset, every glob `shopt` off.
- **Tags:** **[M]** means measured here (a command ran and I read its output). **[I]** means inferred.
- `python3 scripts/check-rm-backup.py --self-test` → **126/126 passed** at `4cc1cedf` **[M]**.

## Verdict

1. **It is THRASHING, not a prose floor.** The component is code. Every finding in the chain is a real `rm` that
   deleted a file the plan did not cover, and every one was probed against bash. The last three links were each caused
   by the fix before them **[M, from the round documents]**.
2. **The union fold does NOT remove the class "the hook's reading differs from bash's".** It removes one cause: the
   negator a quote hides. I found **three more causes that appear in ordinary commands** and one obscure one. Each
   loses a backup without a refusal at `4cc1cedf` **[M]**. Three are BLOCKERs under this PR's own definition.
3. **A redesign removes the class: ask bash to match the pattern.** It is safe, measured: the pattern goes in as DATA
   and nothing in it runs. It costs about 5 ms a call. But it needs a lexer that keeps quotes, and that is backlog
   #686 work, too large to fold past the cap.
4. **Recommendation: MERGE AFTER A NAMED SMALL FIX.** The fix is two changes (below), already prototyped on a copy.
   It turns all three BLOCKERs into refusals. It changes the verdict on **0 of 562** past `rm` calls that use a
   bracket glob, because there are none.

## 1. Thrashing or prose floor — the chain

| round · finding | what it found (probed by the round's coordinator) | what caused it |
|---|---|---|
| r1 C3 (`targets`) | `rm 'a[1].txt'`: the lexer drops the quotes, so the target was globbed as `a1.txt` and nothing was copied | the original design (Python `glob` on quote-stripped text). The fix reads each target BOTH as a pattern and as a literal |
| r4 R4-1 BLOCKER (`glob`) | `rm -f [^k]*`: bash reads `[^` as negation, Python as `^` or `k`. `[[:digit:]]*` matched nothing | the original design. The fix rewrote `[^` to `[!` with a regex and refused POSIX classes |
| r4 S29 (`glob`, `fix_induced`) | `[][:digit:]]*` slipped the regex (a leading `]` is a member), so `]` was lost | **R4-1's fix.** The fix is the `bash_brackets` scanner |
| r5 R5-1 BLOCKER (`glob`, `fix_induced`) | `[\^a]*` / `["^"a]*`: a literal caret, but after quote removal it looks like `[^a]`, so `apple` was lost | **S29's fix.** The scanner picked ONE reading of the caret |
| r5 R5-2 (`glob`, `fix_induced`) | `[^a/b]*`: bash leaves a set that spans `/` literal, but the scanner rewrote the directory part | **S29's fix** |
| **this review P6-1…P6-4** | below | **not** caused by the r5 fold: all four miss at `4cc1cedf` and at every earlier head **[I: the glob step has always been Python `glob`]** |

Two consecutive rounds (r4 push-time S29, then r5 R5-1/R5-2) carry findings caused by the previous fix, in one
component. That is the rule's shape. It is not a prose floor, because every link is a deleted file **[M, in the round
documents; R5-1 re-run here: `[^k]*` now plans `a1 b2 keep` and bash deletes `a1 b2`, so nothing is missed]**.

The pattern behind the chain is the one the `variables` component showed in rounds 2–3. Each fold taught the Python
re-derivation one more bash rule. The next review found the next rule. Round 3 ended that by refusing instead of
following (the allowlist). Round 5 tried to end it by covering every reading instead of choosing one. Section 2 tests
whether that worked.

## 2. Does the union of readings remove the class? Refutation attempts

The fold's claim (r5 coordinator): *"the class 'the hook chose a reading bash did not' cannot recur for a bracket set
— it can only over-back-up."* That claim holds only when the union contains bash's reading. These probes produce
readings it does not contain. All were run at `4cc1cedf`; the output is the driver's JSON, trimmed **[M]**.

| Id | Command (fixture) | Hook plans | bash deleted | Missed |
|---|---|---|---|---|
| **P6-1** | `rm -f [a-z]*` (`Makefile README.md notes.log build.log`) | `build.log notes.log` | `Makefile README.md build.log notes.log` | **`Makefile`, `README.md`** |
| P6-1b | `rm -f [A-Z]*.log` (`Zeta.log notes.log …`) | `Zeta.log` | `Zeta.log notes.log` | **`notes.log`** |
| P6-1c | `rm -f [a-z]` (`é e f`) | `e f` | `e f é` | **`é`** |
| **P6-2** | `cd "app/[id]" && rm -f *.bak` (`app/[id]/a.bak b.bak page.tsx`) | nothing | `a.bak b.bak` | **both** |
| P6-2b | `rm -f *.bak` with the payload `cwd` = `…/app/[id]` | nothing | `x.test.tsx` (same shape) | **all** |
| **P6-3** | `rm -f "app/[id]/"*.bak` | nothing | `a.bak b.bak` | **both** |
| P6-3b | `rm -f app/\[id\]/*.bak` · `rm -rf 'app/[id]'/*` | nothing | every file in `app/[id]/` | **all** |
| P6-3c | `rm -f "[draft]"*.md` (`[draft] a.md`, `[draft] b.md`, `d.md`) | `d.md` | `[draft] a.md`, `[draft] b.md` | **both** |
| P6-4 | `rm -f -- [a\-z]x` (`-x ax zx mx`) | `ax mx zx` | `-x ax zx` | **`-x`** |

**The causes, one per row.**

- **P6-1: bash 3.2 matches a range by locale COLLATION, and Python matches by code point.** With
  `LANG=en_US.UTF-8`, bash's `[a-z]` takes `A`–`Y` and `é`. The same `compgen -G '[a-z]*'` under `LANG=C` returns
  only the lowercase names **[M]**. No quoting is involved, so no reading in the union could cover it. This shape was
  never found because every review probed with lowercase fixtures **[I]**.
- **P6-2: the hook joins the LITERAL working directory into a glob pattern.** `plan` builds
  `t = os.path.join(here, t)` and globs it, so a `[id]` in the directory is read as the set `{i,d}`. This repository
  has **seven** such directories: `app/s/[token]`, `app/api/{playlists,pdf,html,videos,share}/[id]` and
  `app/api/videos/[id]/dig/[sectionId]` **[M, `find`]**. Neither quoting nor reading choice is involved.
- **P6-3: a quoted or escaped bracket next to a wildcard.** This is the r5 cause, one character over. Quote removal
  turns a literal `[id]` into a set, and the union has no reading where a whole set is literal. Its only literal
  reading is the raw target, which keeps `*` a wildcard, so it never matches. r1's C3 fix (the literal reading)
  covers a bracketed name only when the target has NO other wildcard.
- **P6-4: a quoted `-` inside a set.** The union moves a negator but never a hyphen. It is obscure, but it shows the
  union needs one more alternative for each character class quoting can neutralise. That is the thrash, rebuilt as
  combinatorics.

**Tried and NOT a miss at `4cc1cedf`** **[M]**: `[^k]*`, `[.]*` and `.[!.]*` (dotfiles agree), `**/*.log` (bash 3.2
has no globstar, and Python without `recursive` agrees), `l/*.log` through a symlinked directory, `rm -f "a b"*`,
`'x*'y` and `q\?1` (backed up more than needed, which is harmless), `"[^a]"x`, `[0-9]` with `¹ ٣` present, `[ab]]`,
`X="*.bak"; rm -f $X`, `{a,b}.bak` and `{1..3}` (refused), and five negating sets (refused at the cap of four). An
invalid-UTF-8 name could not be made: APFS refuses it. Already filed, re-confirmed: `shopt -s nocaseglob` and
`shopt -s dotglob` in the command miss (backlog #686 R4-2), and `GLOBIGNORE=` backs up more than needed, which is
harmless.

**Base rate.** Over every `rm` in this project's 562 recorded Bash calls, **no** target is a real bracket glob. The 42
targets containing `[` are Python source text quoted inside commands (`targets("rm -f …")`). Targets with only `*` or
`?` number 30 **[M, a scan of `~/.claude/projects/<slug>/*.jsonl`]**. So refusing bracket globs costs about nothing.
The misses are BLOCKERs because of how ordinary the commands look, not because they occur often: `[^k]*` (R4-1) had the
same base rate and was ruled a BLOCKER on the same definition.

**Answer: no.** The union removes "the hook chose the wrong caret". It does not remove the class, because the class
has at least three more causes: the matching engine (collation), the directory part (an unescaped cwd), and quoting
that neutralises a whole set. None of them is a reading choice.

## 3. Can a redesign remove the whole class? Ask bash — measured

The idea: give bash the pattern as DATA and let it match.
`bash --noprofile --norc -c 'compgen -G "$1"' _ "$pat"`, or, NUL-safe,
`… -c 'shopt -s nullglob; IFS=; set -- $1; printf "%s\0" "$@"' _ "$pat"`. Pathname expansion of a parameter's value
does not re-parse it, so no substitution in the value can run. Results in a fixture holding a literal file named
`$(touch PWNED)` **[M]**:

| pattern | bash returns | matches the real `rm`? |
|---|---|---|
| `[a-z]*` | `a1 app banana Makefile notes.log README.md` | yes (P6-1's collation) |
| `app/\[id\]/*.bak` | `app/[id]/a.bak` | yes (P6-3, once the escape is kept) |
| `[\^a]*` / `[^a]*` | `^note a1 app` / everything but `a…` | yes (R5-1, R4-1) |
| `[[:digit:]]*` / `[][:digit:]]*` | `7x` / `] 7x` | yes (R4-1, S29, where the hook must refuse today) |
| `$(touch PWNED)*` and `` `touch PWNED2`* `` | the literal file / nothing | **nothing ran**: no `PWNED` or `PWNED2` file was created |

Cost: 10 calls in **53 ms** in total **[M]**. Locale matters: the same call under `LANG=C` gives a different answer
**[M]**. So the hook must pass on its own `LANG`/`LC_*`, plus any `LC_ALL=` the command assigns.

**What it does not give for free, and why it is #686 and not this PR:**

- **It needs the quoting the lexer throws away.** bash has to receive `app/\[id\]/*.bak`, not `app/[id]/*.bak`, so the
  lexer must record which characters were quoted and backslash-escape them in the pattern it builds. `words()` uses
  `shlex`, which discards that. A quote-preserving lexer is a change to the scanner every other component depends on
  (M size, by #686's own estimate) **[I]**.
- **It reads the hook's shell state, not the command's.** An in-command `shopt -s dotglob` (R4-2) still disagrees,
  but it can be refused by text. Time of check (R4-4) is untouched.
- **It is safe under this threat model.** The pattern is passed as an argument and never `eval`ed, so a mistake in the
  hook cannot run anything the agent wrote. Targets holding `$(` or a backtick are already refused before globbing.

**Needed before merge? No — the class can be closed by REFUSAL, the way round 3 closed `variables`.** A refusal is the
safe side of every row in §2. The measured base rate says a refusal of bracket globs blocks no real command. The
ask-bash redesign then stays in backlog #686, which already names it (`compgen -G`), as the way to turn those
refusals back into backups.

## 4. Recommendation: MERGE AFTER A NAMED SMALL FIX

**The fix, two changes in `plan`, prototyped on a copy (`…/scratchpad/p6/proto/crb.py`):**

1. **Escape the directory part:** `t = os.path.join(glob.escape(here), t)` in place of `os.path.join(here, t)`. This
   closes P6-2.
2. **Refuse a target that pairs a closed bracket set (one not spanning `/`) with `*`/`?`, or with a range `-` inside
   the set:**
   `re.search(r"\[[^\]/]+\]", t) and (re.search(r"[*?]", t) or re.search(r"\[[!^]?\]?[^\]/]*-[^\]/]", t))` →
   `Refuse`. This is checked on the target as the user wrote it, before the cwd is joined. It closes P6-1, P6-3 and
   P6-4. A bracket name alone (`rm 'a[1].txt'`, `rm app/[id]/page.tsx`) keeps today's pattern-plus-literal union.

**Measured on the prototype** **[M]**:

- The probes: P6-2 and P6-2b now back up `a.bak` and `b.bak`. P6-1, P6-1b, P6-3, P6-3c and P6-4 are refused.
  `rm -f app/[id]/page.tsx`, `rm -rf "app/[id]"` and `rm -f 'a[1].txt'` are still backed up, and nothing was missed.
- Self-test: **123/126**. The three that fail are exactly the r4/r5 bracket cases (`[^k]*`, `[]…]`, `[\^a]*`), and they
  now get `refused` where a backup was expected. Their expectations must change to `refused`, which is the safe side,
  and their mutations in `scripts/mutations/check-rm-backup.json` must be re-pointed: this is a two-file edit. The
  `[^a/b]*` case (R5-2) still passes, because a set spanning `/` is not refused.
- Not run: the scoped mutation sweep and the transcript replay on the prototype. The fold must run both. The replay
  should show 0 changed verdicts if the base-rate scan is right.

| Id | Severity | Disposition |
|---|---|---|
| P6-1 `[a-z]*` collation | **BLOCKER**: a silent miss of `Makefile`/`README.md` on a command typed without any intent to bypass | fix 2 (refuse), pre-merge |
| P6-2 bracket dir in cwd | **BLOCKER**: this repo has 7 such dirs, and `cd` into one followed by a plain `rm *.x` misses every file | fix 1 (escape), pre-merge |
| P6-3 quoted/escaped bracket + wildcard | **BLOCKER**: `rm -f "app/[id]/"*.bak` is the natural way to type a Next.js route path | fix 2 (refuse), pre-merge |
| P6-4 quoted `-` in a set | Minor: typed only on purpose | closed by fix 2 anyway |
| R4-2 `shopt`/`GLOBIGNORE` in the command | Major (already filed) | stays in #686. A text refusal of `shopt`/`GLOBIGNORE` next to a glob would be one more line, but it is not required here |
| The class itself (Python re-derives bash's matching) | structural | backlog #686: amend it with P6-1…P6-4 as evidence for the ask-bash redesign, and with this review's measurement that the redesign is safe and costs about 5 ms |

**What we decided this milestone that is not written down:** that a **refusal is an acceptable answer to a shape the
hook cannot read**. The hook already acts on that (`xargs rm`, brace lists, opaque variables), and round 3 adopted it
for `variables`. But the docstring states it only as a list of cases, not as the principle that ends a thrash. The
fold should add one sentence saying so to the `THE DECISION` block.

**Summary.** The `glob` component thrashed on its own terms. R4-1's regex caused S29, and S29's scanner caused
R5-1/R5-2. The round-5 union fold fixes the cause it was aimed at (a negator that quoting hides) and nothing beyond it.
At `4cc1cedf`, three ordinary commands still lose backups with no refusal, each probed against real bash 3.2: `rm -f
[a-z]*` (bash ranges follow locale collation and also take `Makefile` and `README.md`); `rm *.bak` run from inside a
bracketed directory, of which this Next.js repo has seven (the hook globs the literal cwd); and `rm -f
"app/[id]/"*.bak` (quote removal turns a literal set into a pattern, and the union has no literal-set reading). Asking
bash to match the pattern as data removes the whole class, safely and cheaply (no substitution ran, about 5 ms a
call). But it needs a quote-preserving lexer, which is backlog #686 work. Refusing the ambiguous shapes closes the
BLOCKERs now: two lines, prototyped, three self-test expectations moved to `refused`, and a measured 0 of 562 past
`rm`s affected.

**Recommendation: MERGE AFTER A NAMED SMALL FIX:** escape the cwd before globbing (`glob.escape(here)`), and refuse a
bracket set paired with a wildcard or a range. Then amend backlog #686 with P6-1…P6-4 as the ask-bash redesign's
evidence.
