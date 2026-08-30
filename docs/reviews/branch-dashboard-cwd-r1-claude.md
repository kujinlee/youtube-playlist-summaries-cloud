# Branch review — dashboard cwd-independence (PR #177), round 1, Claude half

**Subject:** `969ad71` on `fix/dashboard-cwd-independence`, diffed against `master`.
`scripts/gen-dashboard.py` (+71/−3), `docs/dashboard-entries.md` (+41, append-only).

**Verdict: NOT CONVERGED.**

**Counts:** 0 Blocking · 2 High · 2 Medium · 4 Low.

The production fix is correct and I reproduced both the original break and its repair. The problem
is the *coverage that shipped with it*. Three of the four new cases are load-bearing; the fourth —
the only one guarding the fail-open the PR exists to close — passes with the original bug fully
restored, which I demonstrated by execution. Separately, the carve-out that the commit message
correctly identifies as the reason the bug was invisible is still not covered by anything: three
independent mutations of it survive at 117/117.

---

## H1 — the new decoy case is a negative assertion with no positive companion, and it fails open

**Severity: High. REPRODUCED.**
`scripts/gen-dashboard.py:1098-1099`

```python
        case("the DEFAULT store resolves against the REPO, not the caller's cwd",
             "DECOYENTRYTEXT" in _txt, False)
```

`_txt` is defined three lines above as:

```python
            _txt = _frag.read_text(encoding="utf-8") if _frag.is_file() else ""
```

The case asserts an **absence**. Emptiness satisfies absence. Any independent defect that stops
`main()` writing a substantive fragment makes this case green *while the defect it exists to catch
is live*.

**Measured.** I copied `scripts/` to a scratch dir and applied two edits — the store bug restored
verbatim, plus the fragment write emptied:

```
ap.add_argument("--store", default=STORE_DEFAULT)
  -> ap.add_argument("--store", default="docs/dashboard-entries.md")     # the bug, back
a.fragment_only.write_text(frag, encoding="utf-8")
  -> a.fragment_only.write_text("", encoding="utf-8")
```

Result, run from `/tmp`: **`117/117 passed`**. `main()` still returns 0; no other case notices,
because `--fragment-only` is used by no other case in the suite.

I first demonstrated the same masking with a more realistic pair (store bug + `if a.window < 1` →
`< 20`, so `main()` refuses before writing): the decoy case did not appear in the FAIL list —
verified with `grep -c "DEFAULT store resolves"` = 0 over the full output — while two unrelated
`main()`-contract cases failed. Two defects are needed to reach the masked state, which is why this
is High and not Blocking.

**This file already states the rule that was not applied.** `scripts/gen-dashboard.py:786-791`,
written by the same author for the same hazard:

> `# Both assertions are NEGATIVE, so each carries a POSITIVE companion — otherwise a page that`
> `# failed to render at all would pass them.`

The new case is the one negative assertion in the file without that companion.

**What would close it:** assert the pair, e.g. `("DECOYENTRYTEXT" in _txt, bool(_txt)), (False, True)`.
That keeps the decoy design (no dependency on `docs/` existing beside `scripts/`, which is what broke
the first version under `--mutate`) and removes the emptiness escape. I confirmed the positive half is
available: in the delivered code the fragment is 29,139 bytes in this scenario.

---

## H2 — the carve-out named as the root cause is still guarded by nothing

**Severity: High. REPRODUCED (3 surviving mutations).**
`scripts/gen-dashboard.py:1221-1222`

```python
        if a.store != ap.get_default("store"):
            store_error = f"no such file: {store}"
```

The commit message, the code comment at `:1214-1220`, and the dashboard entry all correctly identify
this branch as the reason a wrong cwd rendered green. The PR fixed its **premise** and left the
**branch itself** with zero coverage. Every `main()`-contract case at `:1154-1184` passes `--store`
explicitly, so the default path through this comparison is never executed by an assertion.

Three mutations, each applied alone to a scratch copy, run from `/tmp`:

| Mutation | Result |
|---|---|
| `if a.store != ap.get_default("store"):` → `==` | **117/117 passed** |
| delete the `if`, always set `store_error` | **117/117 passed** |
| replace both lines with `pass` (never set `store_error`) | **117/117 passed** |

The first is the dangerous one. With `!=` → `==`, `python3 scripts/gen-dashboard.py --store
docs/typo.md` — a store the caller *named* and that does not exist — sets no `store_error`, so
`build` takes the `elif not entries:` branch at `:421` and renders the green
`<p class="none">No entries yet.` That is the **exact reported symptom**, reachable on a different
input, at a fully green suite. The `store_error` cases that do exist (`:793-796`) pass `store_error`
into `build` as a parameter; they never ask whether `main()` produces it.

**What would close it:** two cases through `main()` — a missing **default** store is silent, a
missing **named** store sets `store_error` — plus manifest entries so `--mutate` pins them.

---

## M1 — the comment at `:1218-1220` now states a residual this same commit eliminated

**Severity: Medium. REPRODUCED.**
`scripts/gen-dashboard.py:1218-1220`

```python
        # Residual, stated rather than hidden: passing the default path
        # explicitly is indistinguishable from not passing it. The page still
        # names that path, so it stays honest about WHICH file it means.
```

That was true when the default was the string `"docs/dashboard-entries.md"`. It is false now. The
default is a `PosixPath` and `--store` has no `type=`, so an explicitly-passed value is always a
`str`; `PosixPath.__eq__(str)` is `NotImplemented` in both directions, so the comparison falls back
to identity and is always unequal. Measured:

```
default = PosixPath("/repo/docs/dashboard-entries.md")
argv []                                              -> named = False
argv ["--store","docs/dashboard-entries.md"]         -> named = True
argv ["--store","/repo/docs/dashboard-entries.md"]   -> named = True
```

Against master's string default, the second row was `named = False` — the residual, live.

This matters beyond accuracy, because the correct behaviour now rests on an **accidental type
mismatch that the comment invites a reader to tidy away**. Measured:

```
as shipped (no type=)        explicit-default treated as NAMED = True
with type=pathlib.Path       explicit-default treated as NAMED = False
```

Adding `type=pathlib.Path` to `--store` is the obvious cleanup — it would remove the
`pathlib.Path(a.store)` coercion at `:1210` — and it silently restores the fail-open. Nothing in the
suite would object (see H2: the whole branch is unmutated). The comment should say the residual is
closed and say *what closes it*, or the code should close it deliberately (compare resolved absolute
paths) rather than by type accident.

---

## M2 — instance, not class: the sibling script of the same feature is still cwd-dependent

**Severity: Medium. Reasoning + grep, not reproduced as a live failure.**
`scripts/check-dashboard-entry.py:233,235`

```python
        names = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
        patch = subprocess.run(["git", "diff", "-U0", f"{base}...HEAD",
```

Neither passes `cwd`. This is the same class the PR closes in `gen-dashboard.py`, in the script
`gen-dashboard.py` loads at import time as `_GATE` (`:44`), for the same feature. It happens to work
because CI invokes it from the repo root (`.github/workflows/ci.yml:216-222`) — but "works because
of where the caller stood" is precisely the property this PR set out to remove, and the dashboard
entry describes the fix in class terms ("cwd-dependent in three places") without saying the audit
stopped at one file. I did not find a live caller that runs the ratchet from elsewhere, so this is
latent.

Note also `scripts/gen-dashboard.py:1243`: *"This runs from a git hook"*. It does not —
`.claude/hooks/regen-dashboard.sh` is a Claude Code `PostToolUse` hook (`.claude/settings.json:71`).
Pre-existing, and it interacts with L2 below.

---

## L1 — `--mutate` gained nothing; the new guards live only in `--self-test`

**Severity: Low. Measured.**
`scripts/mutations/gen-dashboard.json` (32 entries) · `scripts/check-plan-code.py:302-305`

`python3 scripts/check-plan-code.py --mutate .` passes on this branch — I ran it:
`OK — delivered scripts mutated: 2 file(s), 44 mutation(s), 0 survivor(s)`. So the edit disturbed
none of the anchors, which is good. But the manifest still holds **32** entries for
`gen-dashboard.py` and `EXPECTED_MUTATIONS["scripts/gen-dashboard.py"]` is still **32**; a JSON scan
for `cwd` or `STORE_DEFAULT` across the manifest returns **0** entries. The mechanism backlog #70
just installed as the primary mutation gate covers none of the new code.

This is not a coverage *shrink*, and `ci.yml:176-177` does run `gen-dashboard.py --self-test`, so the
new cases execute in CI. But the three collector cases are demonstrably falsifiable (I measured all
three going red) and are therefore cheap manifest entries; the decoy case should not be added until
H1 is fixed, or the manifest would pin a case that fails open.

---

## L2 — `cwd=ROOT` is overridden by `GIT_DIR`, and the code believes it runs from a git hook

**Severity: Low (latent). Mechanism REPRODUCED; no current caller sets the variable.**
`scripts/gen-dashboard.py:202-205`

```
GIT_DIR=/tmp/other.git, cwd=<repo>  -> rc 128  "fatal: not a git repository: '/tmp/other.git'"
clean env,              cwd=<repo>  -> rc 0    "2026-08-29"
```

`cwd=` is the weaker of the two anchors: git resolves `GIT_DIR`/`GIT_WORK_TREE` from the environment
first. No caller today sets them — `.claude/hooks/regen-dashboard.sh:40` is a Claude Code hook — but
`:1243` asserts *"This runs from a git hook"*, and a real git hook (or `git rebase -x`, or
`git bisect run`) **does** export `GIT_DIR`. If that comment ever becomes true, the fix stops working
and reports the same "not a git repository" the page just stopped showing. Failing loudly, at least,
unlike the store panel. Cheap hardening: pass `env` with `GIT_DIR`/`GIT_WORK_TREE` popped.

---

## L3 — the empty state now renders an absolute path containing `$HOME`

**Severity: Low. Reasoning; branch not reachable in the current repo.**
`scripts/gen-dashboard.py:423`

```python
                        f'<code>{_html.escape(str(store))}</code>.</p>')
```

`store` is now `PosixPath("/Users/<user>/code/.../docs/dashboard-entries.md")` rather than
`docs/dashboard-entries.md`. Only rendered when the store is genuinely missing, and the page is
written to `~/explainers/` and served on `127.0.0.1:7391`, so the exposure is local. Arguably an
improvement in honesty. Flagged only because the page's own case at `:783-785` still asserts against
a relative literal, so nothing pins which form is intended.

---

## L4 — two small claims in the dashboard entry

**Severity: Low. Measured.**

- `docs/dashboard-entries.md` (new block): *"had its own case at `:785`"*. Line 784-785 is
  `"the empty state names the store that was read"`. The `store_error` cases are at `:794` and
  `:796`. Off by roughly ten lines.
- *"→ 8 entries, zero error markers"*. True at measurement time; the commit adds the ninth, so a
  reader re-running gets 9 (`grep -c 'class="entry"'` = 9 on my run). Per the global rule about
  recording which build a manual check was verified against, worth saying "8 before this entry".

`113 → 117 cases` is correct — I ran master's version (`113/113 passed`) and the branch's
(`117/117 passed`).

---

## Verified sound

Each of these was checked by running something, not by reading.

- **The production fix works, and the original break is real.** I wrote `git show
  master:scripts/gen-dashboard.py` into a scratch tree with `docs/` beside it and ran it from `/tmp`:
  three `<p class="unknown">` panels (`git log exited 128`, two `gh exited 1`, all
  *"not a git repository"*) plus `<p class="none">No entries yet.` — the reported page, exactly. The
  branch version run from `/tmp` and again from `$HOME` produced **byte-identical** fragments
  (`cmp` clean), 9 entries, zero `unknown`/`none` error panels.
- **The three collector cases are load-bearing, and assert equality not presence.** Removing
  `cwd=ROOT` from `commit_dates` → `116/117`, the named case failing. Removing it from `_gh_json` →
  `115/117`, both `open_prs` and `no_entry_prs` failing. Changing `cwd=ROOT` to `cwd=None` (presence
  preserved, value wrong) → `116/117`. So they are not satisfied by the kwarg merely existing.
- **The decoy case does discriminate the store default itself.** Restoring only
  `default="docs/dashboard-entries.md"` → `116/117` with exactly that case failing, both in the repo
  tree and in a `scripts/`-only tree with no `docs/` sibling (the `--mutate` shape). The rewrite the
  author describes genuinely fixed the environment coupling rather than moving it. H1 is a separate
  hole in the same case.
- **The suite is clean in both trees.** `117/117` in the repo, and `117/117` from `/tmp` against a
  `scripts/`-only copy with no `docs/` directory anywhere.
- **`--mutate` is undisturbed.** `check-plan-code.py --mutate .` → 44 mutations, 0 survivors. The 45
  source anchors still match.
- **The local re-imports are safe.** `import contextlib as _ctx / io as _io / os as _os` at
  `:1074-1076` and `import contextlib as _ctx, io as _io, tempfile as _tf` at `:1126` bind only the
  aliases; `import X as Y` never binds `X`, so module-level `tempfile` (used at `:1085`) is not
  shadowed. I grepped `_self_test`'s whole body (`:750-1193`) for bare `os.`, `io.`, `contextlib.` —
  no hits. No `UnboundLocalError` hazard, and the rebinding of `_ctx`/`_io` is idempotent.
- **`os.chdir` is restored on every path.** `_real_cwd` is captured before the `try` and restored in
  `finally` (`:1084`, `:1100-1101`), which covers `main()` raising. The `TemporaryDirectory` is
  removed while the process cwd is still inside it, which POSIX allows; `case()` does no filesystem
  work in that window. I ran the suite 3× with no ordering effects, and the later `main()`-contract
  cases use absolute paths throughout.
- **`_seen.update(k)` accumulation is not currently a masking risk.** `commit_dates`, `open_prs` and
  `no_entry_prs` each make exactly one `subprocess.run` call (`:202`, `:229` via `_gh_json`, `:253`
  via `_gh_json`), so there is no second call whose missing `cwd` a stale dict entry could hide. It
  would become one if a collector ever made two calls.
- **A bad `ROOT` degrades loudly rather than crashing.** `subprocess.run(cwd=<missing>)` raises
  `FileNotFoundError`, a subclass of `OSError`, which both call sites catch (`:206`, `:219`) into a
  could-not-tell.
- **The repo's own gates are green on this branch.** `check-dashboard-entry.py --base master` →
  *"ok — an entry block was added"*; `check-dashboard-entry.py --self-test` → 46/46 plus 5/5
  cannot-run cases; `check-docs.py` → *"Documentation integrity OK"*.

## Not checked

- The **historical invocation** that produced the broken page — out of scope per the brief.
- The six carried mutation survivors against backlog #69 — out of scope per the brief.
- `brief-compose.py`'s own cwd behaviour. It is invoked with `cwd=ROOT` (`:1250`, pre-existing), so
  the seam is anchored, but I did not audit inside it.

---

## Recommendation

**NOT CONVERGED.** Fix H1 (one line: give the negative assertion a positive companion) and H2 (two
cases through `main()` covering both sides of the default-store carve-out, plus manifest entries).
M1 should ship with them — the comment currently invites a change that reopens the bug. M2, and the
`GIT_DIR` hardening in L2, are reasonable to file rather than fix here, but the entry's class-level
claim should be narrowed to the one file that was actually audited.

---

# Disposition — coordinator, same day

Both halves returned **NOT CONVERGED**. Every finding below was **re-verified by the coordinator by
execution** before being accepted; none was taken on the reviewer's word.

**Overlap:** the vacuous decoy case was found independently by both halves (Claude H1, Codex Medium).
**Codex-only:** the `$HOME` leak, and explicit-relative `--store`. **Claude-only, and the deepest
finding of the round:** H2 — the carve-out *named as the root cause* had zero coverage.

| Finding | Verified how | Disposition |
|---|---|---|
| **H1 / Codex-M** decoy case fails open on an empty fragment | mutated `main()` to skip the write → **117/117 green** | **FIXED** — paired with a positive companion, the rule `:786` already stated |
| **H2** carve-out branch unguarded (3 mutations survived) | `!=`→`==` survived at 117/117 **and** rendered the green "No entries yet" for `--store docs/typo.md` — the reported symptom on new input | **FIXED** — 2 paired cases through `main()`; named/omitted now decided by an `is None` **sentinel**, not a value comparison |
| **M1** stale comment; correctness rested on a type accident | reproduced: `PosixPath.__eq__(str)` is `NotImplemented`, so `type=pathlib.Path` would silently reopen the fail-open | **FIXED** — sentinel removes the accident; comment now states what closes it |
| **M2** sibling `check-dashboard-entry.py` same cwd bug | read + mutation-tested both call sites | **FIXED** (not deferred) — the entry claims a *class* fix; narrowing the claim was the alternative, making it true was cheaper |
| **L3 / Codex-Low** empty state leaked `$HOME` | measured `leaks $HOME: True` | **FIXED** — `_store_label()`, exact on both sides |
| **L4** two claims in the dashboard entry | measured | **FIXED** in place (entry not yet merged) |
| `:1329` "runs from a git hook" — false | it is a Claude Code PostToolUse hook | **FIXED** |
| **Codex-High** explicit *relative* `--store` resolves against cwd | reproduced: prints *"could not read … NOT CHECKED"* | **NOT FIXED, deliberate.** cwd-relative is the correct convention for a path the caller typed, and it **fails loudly** — categorically unlike the defect this PR closes. The PR's class-level wording is narrowed instead |
| **L2** `GIT_DIR` overrides `cwd=` | reviewer reproduced the mechanism; no caller sets it | **NOT FIXED.** Latent, fails loudly, and the false git-hook comment that motivated it is corrected. Not filed — filing is the user's call |

## Falsification of the fixes

Every fix was mutated back on a scratch copy. **8/8 killed**; before the round, 4 of these were the
reviewers' own surviving mutations.

```
KILLED 118/120  H2-a  named_store -> not named_store   (was: SURVIVED 117/117)
KILLED 119/120  H2-b  guard deleted, always error      (was: SURVIVED 117/117)
KILLED 119/120  H2-c  never set store_error            (was: SURVIVED 117/117)
KILLED 117/120  H1    store bug + fragment write emptied (was: SURVIVED 117/117)
KILLED 119/120  L3    store label leaks absolute path
KILLED 119/120  cwd=ROOT removed from `git log`
KILLED  5/6     M2-a  cwd removed from check-dashboard-entry's FIRST git call
KILLED  5/6     M2-b  ...and its SECOND call
```

⚠ **L3 survived on its first run** — I fixed the leak and shipped no guard for it, which is the same
omission the round had just penalised twice. Caught by running the battery rather than by reasoning
about it. Recorded because the pattern, not the instance, is the finding.

**Verdict after fixes: CONVERGED**, with the two NOT-FIXED items above stated rather than ticked.
