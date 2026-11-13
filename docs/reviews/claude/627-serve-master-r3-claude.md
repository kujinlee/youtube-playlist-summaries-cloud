Reviewed head: 25ce6e0699e7a9fac83dec156ce1fe117dcb10fe

# Round 3 — `627-serve-master` (backlog #627) — Claude half (adversarial)

Codex is skipped this round by alternation (owner 2026-10-28). I reviewed the r2 fold
(`git diff 416ab6c1..25ce6e06 -- scripts/`), read every function it touched, and tried to refute each r2
finding by giving it an input.

## How I tested

- **Self-tests at head, in the worktree:** `explainer-serve.py --self-test` gave 282/282 (rc 0, 27 s).
  `regen-pages.py --self-test` gave 121/121 (rc 0, 24 s).
- **Mutations:** every mutation ran on a `git archive HEAD scripts docs/explainers` copy in my scratchpad,
  outside the repository and with no `.git`. Nothing was edited in place. On that copy the controls gave
  explainer-serve 281/282 and regen-pages 119/119. The one red control is the docs-fixture case
  `...and every declared source is a real file in the repo`, which Codex and the coordinator also saw. I
  checked the system temp dir after the runs, and no `not-the-suites-*` or mutant directory was left there.

### Does each r2 case fail when its fix is removed?

| Mutant (on the staged copy) | Result |
|---|---|
| M1: delete `decide`'s early `retired_name` return | **RED**: the M1 case |
| M1: put back r1's `if verdict == "retired": return` after `retirement()` | **RED**: the M1 case |
| M2: make `_suite_may_write` a no-op | **RED**: the every-writer case, and the on-merge-move case |
| M2: delete each guard call separately (fetch_master, clone_tree, Private, tree_lock, move_serve_copy) | **RED** ×5: the every-writer case (move_serve_copy also reddens the on-merge case) |
| M2: drop `and _suite_owns(setup.copy)` in `serve_state` | **RED**: the M2 explainer-serve case |
| M2: Codex's mutant (`serve_copy_path` answers a fixed outside dir) | **RED**: the identity case |
| M3: delete the `/` and `/latest` poke | **RED**: the M3 case |
| M3: drop the note from the index source line | **RED**: the M3 case |
| m4: `isdigit` without `isascii` | **RED**: the port class case |
| m4: drop the `try/except ValueError` | **RED**: the port class case |
| M3: drop the note from `/latest`'s 404 | **survives** (m6 below) |
| M3: `poke(FETCH_WAIT)` becomes `poke(0)` on `/` and `/latest` | **survives** (m6 below) |
| explainer-serve: drop `_suite_owns(setup.checkout) and` | **survives** (m5 below) |
| `_inside_suite_tmp` and `_suite_owns`: `real != base and startswith(base + os.sep)` becomes `startswith(base)` | **survives in both scripts** (m7 below) |

### The r2 findings

- **M1 (retired verdicts):** I could not refute it. `decide` now settles only `retired_name(url_path)` before
  it consults master. Every verdict the working tree produces falls through to master's regular entry.
- I looked for a url that names the retired page but escapes `retired_name` while `served_candidate` and
  `_url_rels` still reach it: `/./work-lines.html`, `/work-lines.html/`, `/WORK-LINES`, `/Work-Lines.HTML`,
  and the long-s spelling `work-lineſ` (U+017F, which casefolds to `s`). `requested_name` uses the same
  decode and `normpath` as `lexical_candidates`, and `retired_name` casefolds. So every one of these
  redirects, and none reaches master's `work-lines.html`.
- The paths where a local retired verdict now falls through (preview, no copy, tree None, master lacks the
  page) each still return the local verdict. `choose_source(None, ...)` with master present answers
  `"master"`, so the `local[1]` dereference cannot see a `None` local.
- **M2 (every writer guarded):** the five regen-pages writers are guarded and each guard is case-bound. One
  gap is that explainer-serve's guard checks a different path from the one its fetcher writes (m8). Another
  is that r2's new clause masks r1's clause (m5).
- **M3 (`/` and `/latest` poke and note):** the poke and the index note are bound. The 404 note and the wait
  are not (m6). `source_footer` escapes the note, so a fetch error string cannot inject markup.
- **m4 (`port_from`):** I could not refute it. `+80`, `8_0`, Unicode digits, 4301 digits and padded zeros
  all behave as stated.

## BLOCKER

None.

## MAJOR

None.

## MINOR

### m5: r2's new `_suite_owns(setup.copy)` clause masks r1's `_suite_owns(setup.checkout)` clause

**Caused by r2 fix: YES.** r2's own new clause hides r1's clause from its case. This is the only finding
this round that the previous round's fix caused, so thrashing (two consecutive rounds) is not armed: none
of r2's findings were fix-induced.

The case `⛔ #627: inside the suite the server builds a fetcher ONLY for a checkout inside the suite's own
temp dir` (`_no_fetcher_in_suite`) makes the checkout unowned by moving `tempfile.tempdir` to `t`. That
move makes the COPY unowned at the same time. So since r2 the copy clause alone produces the expected
`fetcher is None`.

**Reproduction:** on the staged copy, replace
`(_suite_owns(setup.checkout) and _suite_owns(setup.copy))` with `(_suite_owns(setup.copy))`. The suite
gives 281/282, and the only red is the docs-fixture control.

The manifest entry for r1 deletes the WHOLE clause, so it still goes red, and it cannot see this. No real
write is exposed: regen-pages' `refresh_serve_copy` still refuses a repo outside the suite. But the
docstring says the server's guard is "a second guard, independent of regen-pages' refusal", and that
property is no longer witnessed for the checkout half.

**Fix:** vary one operand at a time. Use an owned copy with an unowned checkout (and the reverse), and
bind a mutation to each half.

### m6: two lines of the M3 fix have no case that reaches them

**Caused by r2 fix: yes, in the narrow sense.** These are r2's own new lines, and r2's case does not reach
them. They are a coverage gap, not a change in behaviour.

1. **`/latest`'s 404 note.** Replace `" · ".join(x for x in ("no explainers yet", note) if x).encode()` with
   `"no explainers yet".encode()` and the suite gives 281/282 (control red only). The M3 case drives
   `/latest` only while pages exist.
2. **The wait.** On `/` and `/latest`, replace `fetcher.poke(FETCH_WAIT)` with `fetcher.poke(0)` and the
   suite gives 281/282 (control red only). The case joins `f.thread` between its two drives, so it cannot
   tell "the first load waits up to FETCH_WAIT for a merge" apart from "the first load never waits". The fix
   claims the routes poke "exactly as a page GET does", and the GET's own mutant (r1 Claude survivor) is
   bound only on whether it pokes, not on how long it waits.

**Fix:** drive `/latest` on an empty root with a failed fetch and assert that the 404 body says `FAILED`.
For the wait, use a sync that sleeps briefly, drive `/` ONCE without joining, and assert that the merged
page is listed.

### m7: the strict-inside boundary in `_inside_suite_tmp` and `_suite_owns` is unbound in both scripts

**Caused by r2 fix: no.** Both functions came from r1. r2 raised the stakes: `_inside_suite_tmp` is now
the predicate behind all five regen-pages writer guards.

**Reproduction:** on the staged copy, `return real != base and real.startswith(base + os.sep)` becomes
`return real.startswith(base)`. regen-pages gives 119/119 and explainer-serve 281/282 (control red only).

The mutant accepts the suite's temp dir itself, which `base_ok` exists to keep to `Private` alone. It also
accepts any sibling that shares the prefix, for example `/T/fixture-tmp-abc` versus `/T/fixture-tmp-abcd/x`.
The real-world risk is low because the names are `mkdtemp`-random. But this boundary is the guard's whole
meaning, and no case pins it.

**Fix:** add one class case over (base itself, a prefix-sharing sibling, a strict child) for each of the
two independent copies, with a mutation for each.

### m8: the server's fetcher moves `serve_copy_path()` at call time, but its guard and every read use `setup.copy` from construction time

**Caused by r2 fix: no.** The lambda `refresh_serve_copy(setup.checkout)` (no `copy=`) predates r2. r2's
new guard, and its comment ("the CHECKOUT the fetcher moves — the serve copy, `serve_copy_path()`"),
assume that the two are the same path.

**Reproduction (measured):** a script in my scratchpad imports `scripts/explainer-serve.py` with
`_IN_SUITE` set, `tempfile.tempdir` set to a `fixture-tmp-demo` dir, and `EXPLAINER_SERVE_COPY` set to a
copy inside it. `refresh_serve_copy` is replaced by a recorder, so nothing is written. `serve_state()`
builds a fetcher. Then `EXPLAINER_SERVE_COPY` is set to an OUTSIDE path and `f.sync()` is called. The
output:

```text
setup.copy = …/fixture-tmp-demo/copy/master | fetcher built: True
copy passed to refresh_serve_copy = None | it would move: …/demo/OUTSIDE/master
explainer-serve guard's subject == the writer's subject: False
```

In production the environment does not change, so this is inert there, and regen-pages' `move_serve_copy`
guard refuses the outside path in the suite. But the server's "independent" guard checks one path while
its writer writes another, so it does not stand on its own. It is also a latent correctness split, because
the server reads `setup.copy` while the fetcher moves a different copy.

**Fix:** `CopyFetcher(lambda: _regen().refresh_serve_copy(setup.checkout, setup.copy))`. That makes the
guarded path, the moved path and the read path one value. Add an identity case that asserts the copy
argument the recorder sees.

## Isolation and path safety

- Each new outsider path (`not-the-suites-627-copy-*`, `not-the-suites-627-dest-*`) sits BESIDE the
  suite's temp dir, carries the pid, and is removed in `finally`. With the guards intact, nothing is made.
  Under every M2 mutant I ran, nothing was left behind afterwards.
- The m4 subprocess case runs `--status` with an isolated `EXPLAINER_SERVE_ROOT` and exits before it binds
  or writes anything.
- I found no writer in `regen-pages.py` that the M2 class search missed. `discard` deletes only through the
  private dir's fd, `origin_url` and `main_of` only read, and generators run inside the guarded clone. The
  generators' own writes (through `REGEN_MAIN_CHECKOUT`) predate #627 and are outside this branch.

## Summary

All four r2 findings hold under refutation, and each of their cases goes red when its fix is removed. The
four MINORs are gaps in what the cases bind: one masking pair that the r2 fix caused (m5), two unbound
lines in the r2 fix (m6), and one boundary that predates r2 (m7). There is also one subject mismatch in the
server's guard (m8). None exposes a write outside the suite, because the regen-pages guards stand, and none
changes what a reader sees in production. Under the round cap these can be filed or folded at the
coordinator's discretion.

VERDICT: CONVERGED
