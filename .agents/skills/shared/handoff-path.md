<!-- canon: handoff-path -->
# Where a session handoff goes, and why a hint sometimes appears

**This file is the ONE place this mechanism is described.** Everywhere else cites it. That is not a
style preference: the same mechanism was written out at SIX sites, nothing compared them, and for
five consecutive review rounds a reviewer found at least one copy that had drifted, lost a clause, or
kept a claim the others had withdrawn — ⛔ including a round-5 fix that reached the skill and never
reached the hook, leaving the hook printing a claim and its own withdrawal in one refusal message.
⭐ The pattern and its guard are the repo's answer to its most-measured defect, *a second
implementation of one rule drifts* (17 recorded instances). `scripts/check-canonical-source.py`
is what keeps this true; a prose rule saying "don't restate it" is the shape this project has
measured as insufficient — a convention catches what you READ, a script catches what is THERE.

---

## ⛔ THE RULE — a session-continuity handoff is written to `.remember/remember.md`. Nowhere else.

**NOT `.remember/handoff.md`.** That name looks right and nothing reads it. The path is
`REMEMBER_HANDOFF` in the installed `remember` plugin's `session-start-hook.sh`, where there are
**TWO** assignments — the per-session path, then the shared one.
⚠ Cite the **SYMBOL**, never a line number: a line number in a vendored file has no owner in this
repo, no guard can watch it, and a plugin bump invalidates it silently. Discover the file with:

    ls ~/.claude/plugins/cache/claude-plugins-official/remember/*/scripts/session-start-hook.sh

⚠ WITH the `ls` — pasting the bare glob EXECUTES the hook, and with two matches it runs the first
script with the second path as its argument.

**If a session-start block prints a path, obey THAT path.** It is always the right one. Three things
print it, and only the first has a subtle mechanism.

---

## ① A store directory whose LEXICAL PARENT differs, as TEXT, from the project directory

⛔ **Three LABELS for this trigger were each measured false, so what follows is the MECHANISM. A
fourth label is not written.** The refuted ones, for the record: *"outside the project"* (a
`data_dir` can relocate the store while leaving it inside); *"a resolved store root that is not the
project directory itself"* (predicts the opposite of the `data_dir=notes` control); and *"the store
directory is not an immediate CHILD of the project directory"* (refuted by `./notes`, which IS an
immediate child and DOES hint, and by `..`, which is outside and does NOT).

`REMEMBER_ROOT` is a pure STRING operation on the store path, with **no resolution of `.`, `..` or
symlinks**. All five branches, confirmed by executing the vendor's own parameter-expansion block:

| input shape | `REMEMBER_ROOT` |
|---|---|
| trailing slashes | stripped first — but `/` itself is never reduced |
| `/` | `/` |
| contains a slash | everything after the last `/` removed |
| …and that leaves nothing | `/` |
| no slash at all | `.` |

**The hint fires when that string differs from `PROJECT_DIR`** — ⚠ **not "iff the hint fires"**:
② and ③ below fire independently, and the vendor's test is a three-way **disjunction**
(`[ "$REMEMBER_ROOT" != "$PROJECT_DIR" ] || [ -n "$PER_SESSION_HANDOFF" ] || [ -n "$HANDOFF_MODE_DEGRADED" ]`).
Measured: `handoff_mode: per_session` hints while `REMEMBER_ROOT == PROJECT_DIR`.

**Measured against the installed 0.33.0 hook, isolated `HOME` and project per row, positive control
(`=== REMEMBER ===`) asserted on every row:**

| `data_dir` | hint |
|---|---|
| `notes` | no |
| `a/b` | **yes** |
| `.` | no |
| `./notes` | **yes** — physically an immediate child, and it hints |
| `notes/` | no |
| `a//b` | **yes** |
| absolute, immediate child of the project | no |
| absolute, outside the project | **yes** |
| immediate-child symlink to an outside directory | no |
| `..` | no — the store is OUTSIDE the project, and it does not hint |
| unset / empty | no / no |
| `~` | **yes** |
| `/` | ⛔ outside the mechanism: the hook **ABORTS**, printing neither block |

The mechanism is true of **13 of 13 rows where the hook completes**.

### The linked-worktree redirect — and the conditions it needs

A session in a linked worktree writes to the **MAIN checkout's** store, so the lexical parent is
`<main>` while `PROJECT_DIR` is `<worktree>`, the strings differ, and the hint fires.
`_resolve_memory_project_dir` in `lib-memory-dir.sh` performs the redirect.

⛔ **It is CONDITIONAL, and stating it generally is how it became an overbroad prediction once
already.** The vendor compares common-dir against git-dir and then **verifies a candidate main
checkout** — a `.git` FILE alone is not sufficient. Measured:

| case | result |
|---|---|
| main checkout, default config | no hint |
| ordinary linked worktree | hint → main checkout |
| worktree created from another worktree | hint → the original main checkout |
| subdirectory of a linked worktree | hint → main checkout |
| main checkout moved, then `git worktree repair` | hint → the moved main checkout |
| **bare-repository worktree**, default config | **no hint; the store stays local** |
| **ordinary submodule** | **no hint; the store stays in the submodule** |
| linked worktree, relative `data_dir=notes` | hint → `<main>/notes/remember.md` |
| **linked worktree, ABSOLUTE `data_dir=<worktree>/localnotes`** | **no hint; the store stays in the worktree** |
| main checkout moved **without** repair | completes, store local, no hint |

⛔⛔ **THE RULE IS ONE CLAUSE, AND THE TABLE ABOVE IS EXAMPLES OF IT RATHER THAN ITS BOUNDARY
(r6 CLAUDE H1).** The vendor derives a candidate main checkout as **`dirname(git-common-dir)`** and
redirects **if and only if git confirms THAT directory is inside a work tree**
(`_resolve_memory_project_dir`: `_main=$(dirname "$_gcd")`, then
`git -C "$_main" rev-parse --is-inside-work-tree`). Everything below follows from that one sentence,
and two measured configurations are NOT predictable without it:

* ⛔ **A bare-repository worktree whose bare repo sits inside ANOTHER work tree DOES hint — and it
  hints somewhere WRONG.** With `hostrepo/nested/bare.git` and a worktree at `hostrepo/nested/wt`,
  `dirname(common-dir)` is `hostrepo/nested`, which git confirms is inside `hostrepo` — an unrelated
  repository — so the handoff is written under `hostrepo`, not under the worktree. Measured; the
  resolved toplevel's HEAD differs from the subject repo's. ⚠ The vendor's own comment says it
  *"guard[s] against bare-repo worktrees (parent is not a work tree)"* — that is its ASSUMPTION, and
  this configuration is where the assumption is false. **This is the only case in which the redirect
  points somewhere wrong rather than merely staying local.**
* ⛔ **A linked worktree of a `--separate-git-dir` repository does NOT hint**, though it is ordinary
  and fully resolvable: `dirname(common-dir)` is the *gitdirs* directory, which is not a work tree,
  so the chain falls through.

⭐ **And the part that is unchanged:** an absolute `data_dir` bypasses main-relative placement
entirely, and a submodule or an unresolvable main checkout falls back to a local store.

---

## ② `per_session` mode

`handoff_mode: per_session` (in the plugin's config). The printed path is
`remember.<session-id>.md`, and it hints even when `REMEMBER_ROOT == PROJECT_DIR`.

## ③ A DEGRADED `per_session` request

A `per_session` request with no resolvable session id: the hook prints the **shared** `remember.md`
path plus a second line saying the mode you asked for did not apply. The printed path is still the
one to obey; only the reason differs.

---

## ⚠ What this file does NOT claim

* It does not claim the list of triggers is complete — it is the three the vendor's own test
  enumerates, at version 0.33.0, and a vendor bump can add a fourth.

⛔⛔ **AND A FOURTH ALREADY EXISTS AT 0.33.0 — NO VENDOR BUMP NEEDED (r6 CLAUDE H2).** A FLATTENED
CONFIG CACHE at `${TMPDIR:-/tmp}/remember-config-cache-<key>` is keyed on **`REMEMBER_DIR` alone**
(`log.sh`'s cache writer; its only identity line is `#REMEMBER_DIR=…`). Its source list includes
`${HOME}/.remember/config.json`, but an **absent** layer cannot be newer than the cache — so a cache
published under one `HOME` is served to a session whose `HOME` contributes no config at all, and
`handoff_mode=per_session` is set from a cached value. Measured 2/2, with a fresh-`TMPDIR` negative
control and a cache-removal control: `HOME=A` (no config) → no hint; `HOME=B` with the key → hint;
`HOME=A` again, still no config, same `TMPDIR` → **hint fires**; fresh `TMPDIR` → no hint.
⚠ **The bound, because it is narrow:** single-`HOME` config changes invalidate correctly (add the
key, remove it, delete the file — the hint stops immediately). What is reachable is **two `HOME`s
over one `REMEMBER_DIR` sharing a `$TMPDIR`** — two users where `TMPDIR` is unset so both fall back
to `/tmp`, or one user whose `HOME` changes.
⛔ **Why it matters even so:** this canon's stated job is answering *"why was a path printed at
session start"*, and a reader following it will inspect three config layers, find nothing, and
conclude the canon is wrong. ⚠ And the hinted path in that state is `remember.<session-id>.md`,
which the NEXT session (cache gone) will not read — the original *handoff with no reader* defect,
resurrected by a cache.
* It says nothing about what a reader SEES. Shell exit codes and stderr do not establish host or UI
  delivery, and that has never been measured here.
* The enforcement layering — which layer survives a vendor update and which does not — is in
  [`docs/plugins.md`](../../../docs/plugins.md), not here. One mechanism per file.
