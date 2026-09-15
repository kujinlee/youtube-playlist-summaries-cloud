# Adversarial review — `ship-src-root-alone`, round 1, Claude half

Subject: commit `e06ddb2e` on top of `master` (`bef4865e`). Four files, +666/−22.
Everything below was measured on this worktree on 2026-09-15. Mutations were applied to the
DELIVERED scripts and restored by `cp` from a pristine copy taken before anything ran; the tree was
verified byte-identical after every batch (`md5 -q`), and `git` was never used to restore.

**VERDICT: NOT CONVERGED.** Two High findings, both of them extraction damage in the sense the
brief asked for — one is a shipped comment that is factually false about the tree it ships in, the
other is that the branch's own call site is not covered by any of the 35 new cases.

---

## What I verified green first (the control)

| Ran | Result |
|---|---|
| `explainer-serve.py --self-test` | 123/123 — matches the docstring |
| `check-fixture-variation.py --self-test` | 64/64 — matches the docstring |
| `check-fixture-variation.py` (population) | OK, 528 params / 51 files |
| `gen-dashboard.py --self-test` | 325/325 |
| `check-plan-code.py --self-test` | 128/128 |
| `check-docs`, `check-selftest-counts`, `check-ratchet-contract`, `check-guard-coverage`, `check-producer-enumeration`, `check-explainer-delivery`, `check-anchors`, `check-dashboard-entry`, `check-arch-findings`, `check-review-rounds`, `check-gate-falsifiability`, `check-plan-file-tags` | all rc=0 |

**Extraction hygiene — clean.** `RESTART_LOCK`, `Handler._restart`, `/_alive`, `/_restart`,
`RESTART_LOG`, `respawn`, `--restart`, `--respawn`, `page_chrome.restart_control`, `repo_root`,
`restart_commands`: **zero** live references in `scripts/`. Every import is used (AST check: only
`__future__.annotations` is "unused", as expected). `start()` is master's. The single
`inspect.getsource` case (`explainer-serve.py:1417`) still resolves — both markers exist and the
slice is 4,160 chars, so it is not vacuous.

**Every mutation anchor still resolves.** I parsed all 45 manifests in `scripts/mutations/` and
counted each `edits` anchor against the file it names: **0 orphaned or ambiguous anchors**. The
`check-fixture-variation.py` `!= 60` → `__doc__` rewrite and the `gen-dashboard.py` F3 rewrite
orphaned nothing.

**A non-finding I checked because it looks like one.** Disabling `check-fixture-variation.py`'s own
`if ok + fail != _declared:` survives 64/64 — but that is fine: `check-selftest-counts.py` derives
the drift itself. Measured with the docstring at 65 AND the in-file check disabled: the subject
printed `64/64 passed` and exited **0**, while the observer independently reported
`[DRIFT] the docstring declares 65 cases; the suite ran 64`, rc=1. The external observer is not
downstream of the in-file one.

**The `/src/` fix works, live.** Server run in-process on 127.0.0.1:7893 with `$HOME` redirected to
a scratch dir (so the user's `~/explainers/.serve.pid` was never touched — asserted before binding):
`/src/CONTEXT.md` 200, `/src/docs/dev-process.md` 200, `/src/../../etc/passwd` 404,
`/src/.env.local` 404. The bad-env 404 body renders with a real pasteable path.

---

## H1 — HIGH. The comment that is the ONLY statement of `/src/`'s reach is measurably false in this tree, and it tells the next reader not to re-measure

`scripts/explainer-serve.py:205-229` (the paragraph above `SRC_ROOT_ENV`, `:231`).

The comment says, of this worktree, on this date:

> the fallback makes **~1,345 files** servable at /src/ with nobody opting in — 1,290 under `docs/`,
> 40 under `.agents/`, 5 under `public/`, 2 under `prototype-darkmode/`, 2 under `.claude/`, plus
> `CONTEXT.md`. … ⚠ `node_modules/` is absent here and WOULD be reachable in a real checkout; that
> is stated rather than measured away.

**Measured now, in `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`,** by
walking the repo for files whose suffix is in `SERVABLE`:

```
TOTAL servable-suffix files under REPO: 11504
  9528  node_modules      <-- the comment says this is ABSENT
  1292  docs
   379  .next
   105  .superpowers
    76  .remember
    44  scratchpad
    40  .agents
    19  .claude           <-- the comment says 2
     6  (top level)       <-- the comment says 1 (CONTEXT.md)
     5  .screenshots
     5  public
     2  prototype-darkmode
```

And served, live, over HTTP with nothing set (same in-process server, port 7895):

```
/src/node_modules/next/dist/docs/index.md  -> 200  (6445 bytes)
/src/.remember/remember.md                 -> 200  (9325 bytes)
/src/.superpowers/sdd/progress.md          -> 200  (34641 bytes)
```

Three things are wrong, and they are different kinds of wrong:

1. **The one thing the comment flags as its stated bound is refuted.** `node_modules/` is *present*
   and *is* reachable — 9,528 files, confirmed by a 200 on a real path. The sentence "stated rather
   than measured away" is doing the work of a risk acknowledgement while naming the wrong world.
2. **The total is off by ~8.5x** (11,504 vs ~1,345), and the miss is not only `node_modules`:
   `.superpowers/` (105), `.remember/` (76, including session handoff notes), `scratchpad/` (44),
   `.screenshots/` (5) and `.next/` (379) appear in no line of the enumeration. `.claude/` is 19,
   not 2. Even taken on its own terms the itemisation sums to **1,340**, not 1,345.
3. **`git worktree list` explains it, and that is the finding.** The second worktree is
   `…/62196080-…/scratchpad/wt [explainer-src-root-self-configures]` — a scratch checkout with no
   `npm install`. The count was almost certainly taken there and shipped into the repo where it is
   false. This is the corpus failure this project files under *"a measurement is only as good as
   its CORPUS"*, committed inside the very comment that warns the reader about staleness.

**Why this is High and not Low.** The comment states it is "the only statement of the subsystem's
REACH", and the sentence immediately after the count is the security judgement — *"Not judged a
security finding — `safe_path` resolves BEFORE the containment test … `SERVABLE` excludes `.env*`,
the listener is 127.0.0.1"*. That judgement is recorded against a corpus 8.5x smaller than the real
one and explicitly excluding the directory the comment itself names as the risk. The brief asks
that the security conclusion be challenged only with a NEW argument: **the new argument is that the
premise the conclusion rests on is refuted by the tree, measured.** I am not asserting the verdict
flips — `safe_path`'s resolve-then-contain is sound, `.env*` is excluded by the suffix allowlist
(verified: `/src/.env.local` 404s), and the listener is loopback. I am asserting the verdict has not
actually been taken against what is served.

Worse, the comment forecloses the repair: *"Do not 'correct' it by re-running; re-derive it if the
answer ever has to be exact."* That instruction, written to defend against a stale digit, now
defends a wrong order of magnitude and a false claim about `node_modules`.

**Falsifier:** run the suffix walk above in this worktree and get ~1,345 with `node_modules` absent.
It returns 11,504 with `node_modules` present.

**Suggested repair (pick one, do not just tweak the digits):** either (a) delete the count and keep
the qualitative claim — *"/src/ reaches every `.md`/`.html`/`.css`/`.js`/`.svg`/`.png` file under the
checkout, including `node_modules/`, `.remember/` and `.superpowers/`"* — which is true in every
worktree and cannot go stale; or (b) derive it, by making the reach a thing the server can report
(a `/src/` index count) rather than a number a human typed. (a) is one line and closes the finding.

---

## H2 — HIGH. The `/src/` 404 caller — the whole point of the branch — has zero self-test coverage; three separate mutations of it pass 123/123

`scripts/explainer-serve.py:1099-1107` (the `if path.startswith("/src/"):` branch of `do_GET`).

35 new cases were added, and every one of them calls `src_root()` or `src_root_help()` directly.
**Nothing calls the branch that wires them together.** Confirmed by grep: the only occurrence of
`/src/` anywhere in the suite is at `:1419`, where the string is used as the *end marker* of the
`_rev` slice.

Measured (mutate the delivered file, run `--self-test`, restore):

| # | Mutation | Result |
|---|---|---|
| — | control (comment added, no behaviour change) | 123/123 |
| M13 | `body = src_root_help(observed)` → `body = f"no source root — start the server with {SRC_ROOT_ENV}=<dir>"` — **master's exact broken text, the unfilled `<dir>` this branch exists to kill** | **123/123 passed** |
| M16 | the branch stops calling `src_root_help` at all and sends `b"no source root"` | **123/123 passed** |
| M17 | `root = observed.root` → `root = observed.root if os.environ.get(SRC_ROOT_ENV, "").strip() else None` — **a second read of the environment, at the caller** | **123/123 passed** |

M17 is the sharp one. The `SrcRoot` type's own docstring says *"⛔ THE ONLY PLACE `os.environ` AND
`.is_dir()` ARE CONSULTED for this decision. That is the invariant the architecture review bought;
a second reader anywhere downstream reintroduces the whole class."* The class falsifier
(`_renders_without_the_world`) enforces that inside `src_root_help` — and it does, well: I killed it
with both an `os.path.exists` re-derivation (M10) and an `os.environ.get` re-read (M11). But the
falsifier is applied to the *renderer* only. At the *consumer*, the invariant is unguarded, and
M17 restores exactly the forbidden second read with the suite fully green.

By contrast, everything downstream of the seam is well covered. For the record, these all died:
`fallback_ok = REPO.is_dir()` → `True` (2 red), deleting the fallback entirely (3 red), dropping
`shlex.quote` on the script path (1 red) and on the pidfile (5 red), delegating `PIDFILE` instead of
the parameter (6 red), removing either `ValueError` guard (1 red each), a bad env value silently
falling back (4 red), inverting the `why` ternary (1 red), widening `SRC_REASONS` (1 red), and
ignoring `fallback_ok` (10 red). The seam is genuinely strong. The wiring is untested.

**Why High.** The defect this branch exists for — 55 dead links for four days behind a green suite —
was a *wiring* defect: `src_root()` returned `None` and the caller did the wrong thing with it. The
branch rebuilt the observation beautifully and left the same joint unguarded. A future edit to the
`/src/` branch of `do_GET` reverts the user-visible fix with no signal, which is the exact failure
mode by name.

**Falsifier:** write a case that drives the route and assert on the body. It does not need a port —
the suite already has `root`/sandbox fixtures, and `Handler.do_GET` can be driven with a stub
`self.path` and a captured `_send`, or at minimum a source-slice case in the shape of the `/_rev`
one asserting `src_root_help(` appears in the `/src/` branch and `SRC_ROOT_ENV}=<dir>` does not. If
such a case exists and M13 still passes, this finding is wrong.

---

## M1 — MEDIUM. The new duplicate-key guard claims three ratchet literals; only one is exercised, and the narrowing that makes it correct is unfalsifiable

`scripts/check-fixture-variation.py:883-928` (`_duplicate_ratchet_keys`), cases at `:950-963`.

The function's docstring says *"Every key written more than once in this file's **three** ratchet
literals"* and `:907` is `wanted = {"EXEMPT", "KNOWN_UNVARIED", "EXAMINED_KEYS"}`. Measured:

| # | Mutation | Result |
|---|---|---|
| CF8 | `wanted = {"EXEMPT", "KNOWN_UNVARIED", "EXAMINED_KEYS"}` → `{"EXAMINED_KEYS"}` | **64/64 passed** |
| CF3 | `for node in tree.body:` → `for node in _ast.walk(tree):` (the r6 Low regression, restored verbatim) | **64/64 passed** |
| CF2 | the duplicate is detected but never appended | 63/64 — caught |
| CF4 | unparseable source returns `[]` instead of CANNOT RUN | 63/64 — caught |

**CF8:** all three fixture literals in the suite are spelled `EXAMINED_KEYS`, and the one case that
runs over the real file asserts `== []`, which stays `[]` under the narrowing. So the guard's cover
of `KNOWN_UNVARIED` (127 entries) and `EXEMPT` (7) is asserted by prose only. A duplicate key in
`KNOWN_UNVARIED` is the identical silent-discard defect the r5 High was filed for — the last entry
wins and the earlier one vanishes at import — and the guard for it can be deleted with no case going
red. This is the *"a framing widened to fit is no longer a claim"* shape: the finding was about one
literal, the fix was widened to three, and the widening was never measured.

**CF3:** the `tree.body` narrowing has a whole comment block explaining it is a r6 Low fix, and it
is unfalsifiable. The comment says *"No false positive today; a trap laid for the next person"* —
but a case is trivially writable and does not need a real duplicate:

```python
case("a duplicate inside a FUNCTION body is not this guard's subject",
     _duplicate_ratchet_keys("def f():\n    EXAMINED_KEYS = {'a.py': (), 'a.py': ()}\n"), [])
```

That case is red under CF3 and green as shipped. Two fixture strings (one naming `KNOWN_UNVARIED`,
one `EXEMPT`, each with a duplicate) close CF8 in the same edit.

**Falsifier:** add those three cases; if CF8 and CF3 still pass, this finding is wrong.

---

## M2 — MEDIUM. The `[FAIL] ` report-format repair — the one thing the commit message calls "the precondition" — is guarded by nothing

`scripts/explainer-serve.py:1935` (and the `except` line below it).

The commit message ships this as a named deliverable: *"the `[FAIL] ` report-format repair — the
shape check-plan-code can parse"*, and the dashboard entry calls it *"the precondition for this file
ever joining `--mutate .`"*.

Measured: `print(f"  [FAIL] {name}")` → `print(f"  FAIL: {name}")` — **123/123 passed, rc=0.**
Nothing else in the tree reads it either: `explainer-serve.py` has no manifest in
`scripts/mutations/` (that is backlog #122), so `check-plan-code.parse_fail_names` never sees this
file; `check-selftest-counts.py` reads the `N/M passed` line, not the failure lines (verified — it
reports CANNOT RUN when that line is removed, and says nothing about `[FAIL]`).

I am filing this **separately from #122 on purpose.** #122 is "the 123 cases have not been shown
able to fail", which is about the cases. This is about the *report contract* itself: it was repaired
in this commit, it is load-bearing for the future manifest, and it can be reverted silently by
anyone reformatting output — including by the person who eventually writes the manifest and cannot
tell why their mutations report "matched 0 red cases". This project's own memory has this shape
filed as *"a report format is a CONTRACT"* and *"removing a signal hollows out its falsifier"*.

**Cheapest fix, one case, no manifest needed:**

```python
case("the failure line is `[FAIL] `, the shape check-plan-code can parse",
     lambda: '"  [FAIL] {name}"' in inspect.getsource(_self_test))
```

**Falsifier:** if a mutation of the print shape reddens any check in this repo, this is wrong.
I ran the file's own suite and `check-selftest-counts.py`; neither noticed.

---

## L1 — LOW. `expanduser()` can be deleted with the suite green

`scripts/explainer-serve.py:504`. `p = pathlib.Path(v).expanduser()` → `pathlib.Path(v)` passes
123/123. No case sets `EXPLAINER_DOCS_ROOT` to a `~`-relative path. This is distinct from backlog
#123 (which is about `~unknownuser` *raising*): it is that the supported `~/docs` spelling has no
case at all, in the commit that took `src_root` from 0 cases to 12. One line closes it:
`case("src_root: a ~ path is expanded", lambda: with_env("~", src_root).root == pathlib.Path.home())`.

## L2 — LOW. The `gen-dashboard.py` F3 fix has no falsifier in this tree, and its cited evidence is not reproducible here

`scripts/gen-dashboard.py:2213-2220`. Reverting `_bcard = _fragment(_bh2, "2026-08-31-1")` to the
old `_bsum = _bh2[_bh2.index("<summary>"):…]` passes **325/325**, because the chrome that broke it —
`<summary>Server not responding?` — is the restart control, which this branch deliberately does not
carry. The comment states *"MEASURED 2026-09-15: adding the restart fallback to the page chrome put
`<summary>Server not responding?` at index 0"*; that is the **only** surviving textual reference to
the parked feature anywhere in `scripts/` (confirmed by grep), and a reader in this tree cannot
reproduce it.

The change is still right — `_fragment` raises rather than sliding onto a stranger's `<summary>`,
which I confirmed by pointing it at a non-existent card id (`AssertionError: no entry card with id
'2026-08-31-99'`). So this is not "revert it". It is: the comment should say the measurement was
taken on PR #295's worktree and is not reproducible here, or the case should carry a fixture whose
chrome contains a `<details>` so the anchoring is asserted rather than merely preferred.

## L3 — LOW. A line documented as fixing a crash is dead code

`scripts/check-fixture-variation.py:925`: `names = {n for n in names if isinstance(n, str)}`, with a
comment saying the first version *"put `None` into this set and then `sorted()` raised TypeError"*.
In the shipped code both later uses are `names & wanted` (`:926`, `:928`), and `wanted` contains only
`str`, so `None` can never reach `sorted()`. Deleting the filter passes 64/64 (CF5) — not a coverage
gap but a redundancy. The cost is the comment: it tells the next reader the line is load-bearing
against a crash the surrounding code already makes impossible, which is how a defensive line
survives a refactor that should have removed it.

## L4 — LOW. Two live documents give different case counts for the same file

`docs/backlog.md:152`, `:153` (and #127) say *"none of that file's **140** cases has ever been shown
load-bearing"* about `scripts/explainer-serve.py`. On `master` that file runs **88** cases (verified:
I ran `git show master:scripts/explainer-serve.py --self-test` → `87/88`, the single red being my
copy sitting outside the repo); on this branch it runs **123**, which is what the new dashboard
entry says. 140 was the parked branch's number. This is **pre-existing on master** (`#309`), not
introduced here — but this branch is the one that moves the count and adds a second document
asserting a different one, and the rows it cites as "travelling with the parked half" now
demonstrably describe no tree in the repo.

---

## Notes, not findings

- `_rev_branch_src` (`:1417-1419`) slices from `if path == "/_rev":` to `if path.startswith("/src/"):`,
  which spans the **entire `/_stale` branch** as well — 4,160 characters. The case still works (a
  `safe_path` reversion in `/_rev` reddens it) but it would also redden for a change in `/_stale`
  while naming `/_rev`. Identical markers on master, so pre-existing and not extraction damage.
- `M19`: deleting the `({observed.fallback})` parenthetical from the bad-env body passes 123/123,
  because the two cases that assert the fallback path is named are satisfied by the same path
  appearing inside the `python3 …` command. Sub-Low; mentioned only because it shows those two
  cases are weaker than they read.
- The brief's item 5 checks out exactly: `pinned - examined` and `examined - pinned` are both **empty**
  for `explainer-serve.py` (19 keys each side, verified by importing the guard and calling
  `analyse()`). `_gone_checkout_help`'s parameters are correctly absent — the suite reaches it only
  through `src_root_help`, so it has zero direct call sites and the guard does not examine it.
- `EXPECTED_MUTATIONS` sums to 643 across 45 files, and all 45 manifests exist on disk with every
  anchor resolving. `explainer-serve.py` is in neither, consistently — nothing pins it, nothing
  expects it.

---

## Verdict

**NOT CONVERGED.** H1 and H2 are both blocking-adjacent in my judgement but neither breaks a gate,
so I have them at High rather than Blocking: nothing here is wrong *in behaviour* — the fix works,
verified live — and both are one small edit away from closed.

- **H1** must be fixed before merge. It is a false factual claim in shipped source that a security
  judgement is resting on, and it instructs the reader not to check it.
- **H2** should be fixed before merge. The branch exists because a wiring defect hid behind a green
  suite; shipping it with the new wiring uncovered repeats the premise.
- **M1, M2** are cheap (three cases and one case respectively) and are the difference between a
  guard and a decoration.
- **L1–L4** are one-liners or comment repairs; L4 is pre-existing and is the user's call whether it
  rides along.

Tree state on exit: `git status --short` shows only `docs/reviews/verdicts/r1-codex.verdict.json`
(the Codex half's, not mine) plus this review file. All three mutated scripts verified
byte-identical to their pre-review md5s.
