# Adversarial review — `ship-src-root-alone`, round 2, CLAUDE half

Reviewer: Claude (second half of round 2, alternating — ran after the Codex half, which is filed at
`docs/reviews/codex/ship-src-root-alone-r2-codex.md` and which I read before starting).

**Subject: the WORKING TREE, pinned.** `scripts/explainer-serve.py` md5
`323bc2a48fa87c8a928f0b7a3af2ec14`. Every line number below is against that revision. See
*Process note* at the end — the file changed twice under me while I was reading it.

---

## Verdict, first

**NOT CONVERGED — and the ARCHITECTURE-REVIEW ARMING CONDITION IS MET.**

`docs/dev-process.md` arms a Phase 6 architecture review when **two consecutive rounds carry
findings caused by the previous round's own fix, in one component.** That has now happened in
`src-caller`:

| Round | Fix | Finding it caused | Who found it |
|---|---|---|---|
| 1 → 2 | r1's fix for H2 built `_drive_src` + `_Counting` | `_Counting` overrode only `get`; `SRC_ROOT_ENV in os.environ` passed 133/133 | Codex, r2, labelled fix-induced |
| 2 → 3 | r2's fix replaced the counter with a stubbed `src_root` + `_Forbidden` | **H1 below** — the "consulted the world twice" invariant is now unguarded; plus L1, L2 | this review |

**Both rounds, same component, and it is code rather than prose** — H1 is a measured coverage
regression with a surviving mutation, not a wording quibble, so the *thrashing or prose floor?*
question that `review-method.md` requires answers **thrashing**. The prose-floor reading is
available for L3 alone, and L3 is not what arms the rule.

I am stating this plainly because the brief asked me not to soften it: **I did not go looking for a
way to arm the rule, and I checked the opposite direction first.** The Codex half's two Mediums are
genuinely fixed — I re-ran both of its exact mutations against the current tree and both now die
(M1, M9 below). H1 is a different defect, introduced by the repair.

**Findings: 1 High, 3 Medium, 3 Low.** No Blocking — nothing here is wrong in shipped *behaviour*;
`/src/` serves correctly and confinement holds, both measured. M2 and M3 were added after the
coordinator asked me to judge two episodes from the round rather than take their account of them;
both are instrument defects, and both are reconstructed from artefacts rather than inferred.

---

## H1 — High — the round-2 rewrite retired the only coverage for the defect class the branch exists to guard

**fix-induced: YES.** Killed at the round-1 commit; survives in the round-2 working tree. Measured
both ways.

`scripts/explainer-serve.py:1959-1995` (`_drive_src`), `:2039-2047` (the comment that justifies the
deletion), `:1122-1123` (the subject).

Round 2 replaced the read-counter with a harness that **stubs `src_root` out of the request**:

```
1989:                globals()["src_root"] = lambda: _obs
1990:                os.environ = _Forbidden("the environment")
```

and deleted the two cases that asserted a read count, on this stated reasoning (`:2044-2047`):

> The two cases that used to assert a read COUNT are gone with the counter they needed — an explicit
> pair asserting "the mechanism did not fire" would be a second, weaker statement of what the
> mechanism already enforces on every call.

**That sentence is false, and the falsification is one line.** Once `src_root` is a stub, the caller
can call it as many times as it likes for free — so the most natural spelling of "the caller looked
at the world a second time" is now invisible.

**Measured.** Mutation applied to `:1122-1123`, a copy-aside/restore-by-`cp` harness, never git:

```python
             observed = src_root()
-            root = observed.root
+            root = src_root().root
```

| Revision | Result |
|---|---|
| **Working tree (round 2's fix)** | `self-test: 142/142 passed` — **SURVIVES** |
| Commit `78100320` (round 1's fix) | `self-test: 130/133` — **KILLED**, by exactly the two cases round 2 deleted: `the caller reads the environment ONCE — src_root is the only reader` and `…including on the 404 path, where the help is rendered` |

*(The `78100320` control was run out-of-tree with `PYTHONPATH=scripts`, which costs one unrelated
pre-existing red case — `...and every declared source is a real file in the repo` — present in the
control too: control `132/133`, mutant `130/133`. The delta is exactly the two named cases.)*

And it is not merely the one suite. With the mutation applied, **every declared-green gate stays
green**:

```
rc=0  scripts/explainer-serve.py --self-test          self-test: 142/142 passed
rc=0  scripts/check-fixture-variation.py --self-test  67/67 passed
rc=0  scripts/check-fixture-variation.py              fixture variation OK — 528 parameter(s) …
rc=0  scripts/check-selftest-counts.py                39 script(s) declare a count, every one verified
rc=0  scripts/check-ratchet-contract.py               ratchet contract OK
rc=0  scripts/check-docs.py                           Documentation integrity OK
```

**Why this is a real defect and not a harness preference.** `src_root` reads the environment on
every call (`:517  v = os.environ.get(SRC_ROOT_ENV, "").strip()`), so a second `src_root()` call
**is** a second environment read in production. The code's own comment three lines below the
mutation site forbids exactly this:

```
1125:                # ⛔ NO SECOND READ. The observation carries the env value and the
1126:                # fallback's state as they were when the decision was made — r3 M1/M2.
```

and `src_root`'s docstring (`:512-514`) calls a second downstream reader "the whole class". Two
`src_root()` calls inside one request can disagree — the env can be re-set, the fallback directory
can vanish between them — which is the TOCTOU the `SrcRoot` value object was created to eliminate.
Round 1's H2 existed because this call site had no coverage at all; round 2's fix gave it coverage
of a *narrower* property than the one round 1 bought.

**Falsifier:** the mutation above reddens the suite on the working tree; or the `:2044-2047` comment
stops claiming the deleted count cases were redundant and instead states which mutations the new
mechanism does not catch.

**Cheapest fix I can see** (offered as a hypothesis, not a spec — this project's own rule is that a
filed finding's proposed fix is a hypothesis): have the stub count its own invocations —
`_calls = []; globals()["src_root"] = lambda: (_calls.append(1), _obs)[1]` — and assert
`len(_calls) == 1` per request. That keeps `_Forbidden`'s "no direct env read" property *and*
restores the count, without rebuilding the rival env-interception class the fix rightly removed.
**But see the arming condition above: the next patch to this component is exactly what the rule
says not to take.**

---

## M1 — Medium — the branch deletes a committed verdict belonging to an unrelated, already-merged review round, for the second round running

**fix-induced: no** (it is a review-process defect, not a code-fix defect) — but it is a
**recurrence**: round 1 committed one, round 2 stages another.

`git status --short` on the working tree:

```
 D docs/reviews/verdicts/r2-codex.verdict.json
?? docs/reviews/verdicts/ship-src-root-alone-r2-codex.verdict.json
```

These are **not a rename.** Measured by reading both:

| File | `schema` | `head` | `reason` |
|---|---|---|---|
| `r2-codex.verdict.json` (committed, being deleted) | 1 | *absent* | `5591 chars` |
| `ship-src-root-alone-r2-codex.verdict.json` (this branch's) | 2 | `78100320…` | `3482 chars` |

Different runs. The deleted one was last written by merged work (`git log` →
`58d82658`/`87ea0001`), and this branch is destroying it.

**Round 1 already did this and it is committed.** `78100320` deletes
`docs/reviews/verdicts/r1-codex.verdict.json`, whose record is `head: bb265c08…` —
`git merge-base --is-ancestor bb265c08 HEAD` → **NOT an ancestor**; `bb265c08` is
*"My new CSS hollowed out someone else's falsifier"*, an unrelated merged PR. Its verdict is gone
from this branch.

`docs/plugins.md` says these verdicts exist so `check-review-rounds.py` can read, **in CI**, that a
gate ran. Deleting one erases the evidence that a merged round's adversarial gate ran at all — and
**nothing notices**: `check-review-rounds.py` and `check-docs.py` are both green over the deletion
(measured above; `check-review-rounds.py`'s only complaint was my own then-missing half).

The mechanism is visible in the artifacts themselves: both of this branch's verdicts carry
`"review": "r1-codex.md"` / `"r2-codex.md"`, i.e. the Codex runs were invoked with a **generic
`--out` stem**, and `codex-review.py:218-232` derives the verdict path from that stem — straight
onto a committed file's name. That is this project's recorded *"a guard's evidence path is a
namespace with no allocator"* shape, hit twice more on this one branch.

**Falsifier:** `git show HEAD:docs/reviews/verdicts/r2-codex.verdict.json` is byte-identical to
`docs/reviews/verdicts/ship-src-root-alone-r2-codex.verdict.json` (it is not), or the branch restores
both deleted files, or it carries a written reason for removing them.

**✅ CLOSED while this review was being written** — the falsifier's second clause is now satisfied.
Both `r1-codex.verdict.json` and `r2-codex.verdict.json` are present again on disk and
`git status docs/reviews/verdicts/` no longer reports a deletion. Recorded rather than deleted,
because the *mechanism* — a generic `--out` stem landing the verdict on a committed file's name
(`codex-review.py:218-232`) — is unchanged and will do it again on the next round that reuses a bare
`rN-codex` stem. **The finding is the allocator, not the two files.**

---

## L1 — Low — `_Forbidden`'s failure message names the wrong function from its new call site

**fix-induced: YES** — round 2's fix reused `_Forbidden` at a second call site without generalising
the message it was written for.

`:1726-1728`:

```python
            def _raise(self, *_a, **_k):
                raise AssertionError(f"src_root_help read {self._what} — it must carry, "
```

`src_root_help` is hardcoded. Round 2 introduced a second user at `:1990` — `do_GET`. **Measured**:
inserting `os.environ.get(SRC_ROOT_ENV)` into `do_GET`'s `/src/` branch reddens six cases, every one
reporting

```
[FAIL] /src/ serves a real file from the observed root — AssertionError: src_root_help read the environment — it must carry, not re-derive
```

The mechanism fires correctly; the line tells the reader to go and look at the wrong function. This
file already carries the rule at `:475` — *"THE REASON FOR A FAILURE WAS INFERRED RATHER THAN
CARRIED"*. One-line fix: `_Forbidden(what, by="do_GET")`, or interpolate the caller.

**Falsifier:** the same mutation produces a message naming `do_GET`.

---

## L2 — Low — `_SURFACES` re-types `_Forbidden`'s surface list instead of deriving it, and drifts in the direction that hides a gap

**fix-induced: YES** — `_SURFACES` (`:2058-2074`) is new in round 2's fix.

Eleven names are hand-listed beside the eleven `_Forbidden` assigns at `:1732-1733`. The loop is
live for *removals* but blind to *additions*:

| Mutation of `_Forbidden` | Result |
|---|---|
| **add** `popitem = update = _raise` | `142/142 passed` — **SURVIVES**; the two new surfaces are unasserted and the case count does not move, so `check-selftest-counts.py` sees nothing either |
| **remove** `pop` (control) | `141/142` — `[FAIL] _Forbidden refuses the \`pop\` read surface — the guard is not vacuous` |

So the vacuity guard's own coverage claim is maintained by hand, next to the definition it mirrors —
the same second-copy-drifts shape that produced the `_Counting`-beside-`_Forbidden` defect one round
ago, which the fix's comment at `:1974-1981` correctly diagnoses and then re-enacts one level down.
Deriving it removes the hazard: `[n for n, v in vars(_Forbidden).items() if v is _Forbidden._raise]`.

**Boundary — see the item-2 answer below, which is where this leads.** `os.environb` bypasses the
`os.environ` patch entirely (measured, survives). I am *not* filing that as a twelfth-surface
finding: "enumerate harder" is the trap `:1974` correctly names. The reason it matters is
structural, not local, and it is set out next.

**Falsifier:** `_SURFACES` is derived from `_Forbidden` rather than re-typed, or adding a surface to
`_Forbidden` reddens the suite.

**✅ CLOSED while this review was being written** — the falsifier's first clause is now satisfied:
the population is derived via `vars(_Forbidden)` (`:2140`). Not re-verified by me; the redesign it
arrived in is round 3's subject.

---

## L3 — Low — the reach comment's security claim is true about the response body and silent about the metadata channel the widening opens

**fix-induced: no.**

`:238-241` now reads *"no CORS header is emitted — so a cross-origin page can cause a request but
cannot read the response."*

**The load-bearing half is verified independently** (the brief asked me not to take Codex's word).
I drove the real `do_GET` in-process — no port bound, no server started, no pidfile touched — and
read `Handler._send` (`:1046-1052`): it emits `send_response(code)`, `Content-Type`,
`Content-Length`, `end_headers()`. **No `Access-Control-Allow-Origin`, measured, and no other route
in `do_GET`/`do_POST` emits one either.** The claim about the response *body* holds.

Same run, with nothing set, confirms the corpus claim behaviourally:

```
src_root() with nothing set -> /Users/…/youtube-playlist-summaries-cloud
/src/node_modules/next/dist/docs/index.md  -> (200, 'text/html; charset=utf-8', 6445)
/src/.remember/remember.md                 -> (200, 'text/html; charset=utf-8', 9325)
/src/CONTEXT.md                            -> (200, 'text/html; charset=utf-8', 37198)
/src/.env.local                            -> (404, …)     # SERVABLE suffix filter
/src/../../../etc/passwd                   -> (404, …)     # safe_path
```

So `node_modules/` is present and served, `.remember/` session notes are served, and both exclusions
hold. Round 1's H1 fix is correct on the facts.

**What the sentence does not say:** status is not body, and status *is* observable cross-origin
without CORS (`<script src>`/`<img>` `onload` vs `onerror`, `<link>`). With reach = the whole
checkout, a page on any origin the developer visits gains a **file-existence oracle over the entire
repository** — 200 for every `.md`/`.html`/`.css`/`.js`/`.svg`/`.png` that exists, 404 otherwise.
For `.png` it additionally leaks intrinsic dimensions. The 200/404 discrimination is **measured
above**; the "a cross-origin page can observe it" step is **reasoning, not measurement** — I did not
drive a browser, and it should be read as such.

Given this branch's round-1 H1 was itself *"a false factual claim in shipped source that a security
judgement is resting on"*, a sentence one clause short of accurate in the replacement is worth one
clause, not a redesign: *"…cannot read the response body; 200-vs-404 remains observable
cross-origin, so the widened reach leaks file existence."*

**Falsifier:** `_send` emits a CORS header (it does not), or `/src/` returns an identical status for
present and absent files (it does not — measured 200 vs 404 above), or the comment gains the clause.

---

## M2 — Medium — a fix was not "reverted": it was **overwritten by an edit computed from a stale base**, and nothing could tell the two apart

**fix-induced: no** (an instrument/process defect, not a code defect). Added after the coordinator
asked me to judge this rather than take their account. **Reconstructed, not inferred** — the
scratchpad holds seven timestamped copies of the subject.

| time | file | md5 | `_Counting` | two-arm `[FAIL] ` | src_root stub |
|---|---|---|---|---|---|
| 16:35 | `es.bak` | `b99d151a` | 4 | — | — |
| 16:37 | `es2.bak` | `6a1b435f` | 4 | **present** | — |
| 16:42 | `es3.bak` | `dbe1e6d3` | 4 | **GONE** | — |
| 16:44 | `es4.bak` | `da82190f` | 0 | — | ✓ |
| 16:47 | `es6.bak` | `323bc2a4` | 0 | re-applied | ✓ |

**The mechanism, proven rather than guessed.** `diff es.bak es3.bak` has **exactly one hunk** — the
reach-comment repair — and contains **zero** lines matching `FAIL`. The `[FAIL] ` region of
`es3.bak` is **byte-identical to `es.bak`**, the file from *before* the fix existed. Line
arithmetic agrees: 2152 → 2159 (`+7`, the fix) → 2160 (`= 2152 + 8`, the reach comment alone).

So the 16:42 edit did not *undo* the 16:37 fix. **The fix was never in its input.** The edit was
computed from the 16:35 file and written out whole, and everything done in between vanished with
it. One write carried a forward fix in one region and a seven-minute rollback in another.

**Why nothing caught it, which is the part worth keeping.** The 16:37 fix changed the lambda body
and added a comment, but **left the case NAME untouched** —
`"the failure line is \`[FAIL] \`, the shape check-plan-code can parse"` is identical before the fix,
after the fix, and after the rollback. Therefore:

- the **case count did not move** (a body edit, not a new case), so `check-selftest-counts.py` and
  the declared docstring count were satisfied in both states;
- a human grepping `the failure line is` saw a present, correctly-named case in both states;
- the only observable difference was a mutation that had died coming back to life — which is
  exactly how it was eventually found, several steps late and by luck.

This is the mirror of this project's recorded *"a refactor ORPHANS the mutation guarding it —
anchors bind by TEXT"*: here the **fix** left the anchor unmoved, so a stale-base rewrite reinstated
the defect under a name that still read as correct.

**Already closed by accident, and worth making deliberate.** The 16:47 re-application *did* rename
the case — `"…at BOTH report sites — the shape check-plan-code parses"` — so fixed and unfixed are
now textually distinguishable. The durable rule: **when a fix changes what a case asserts, change
the case's NAME too.** The name is the only thing a human greps and the only thing a stale-base
rewrite cannot silently satisfy.

⚠ **One artefact of the reverted window is in this round's paperwork.** My review brief was written
at **16:42** — inside the 16:42→16:47 rollback — and states that the `[FAIL] ` fix "now asserts both
prints", quoting the `count(…) == 2` expression. It was describing `es2` while the tree was `es3`.
Harmless here because I measured rather than believed it, but it is a document asserting a fix that
had already been overwritten.

**Falsifier:** `diff es.bak es3.bak` touches the `[FAIL] ` region (it does not), or `es3.bak`'s
`[FAIL] ` block differs from `es.bak`'s (it does not).

---

## M3 — Medium — the mutation harness's FAIL-grep is not merely unsound here, it is **stuck**: it returns the same count for a killed and a surviving mutation

**fix-induced: no.** The coordinator flagged the grep as unsound and asked whether any r1 evidence
depends on it. It does — one entry — and the instrument is worse than "miscounts".

**Measured, on the pinned snapshot, out of tree** (a foreign path costs one unrelated pre-existing
red case, present in control and mutant alike — the *delta* is what matters):

| | `N/M passed` | what a `[FAIL] `-grep counts |
|---|---|---|
| control | `141/142` | **1** |
| `[FAIL] ` → `FAIL: ` | `140/142` | **1** |

Same at the r1 revision `78100320`: control `132/133` grep **1**; mutant `131/133` grep **1**.

**The count is identical in both states because two errors cancel.** The grep (a) misses both real
red lines, which now begin `FAIL: `, and (b) counts a **phantom** — the surviving hit is the
substring `` `[FAIL] ` `` *inside the red case's own name*, on a line whose prefix is `FAIL: `:

```
  FAIL: the failure line is `[FAIL] ` at BOTH report sites — the shape check-plan-code parses
```

An instrument that returns `1` whether the mutation was killed or survived is not under-reporting;
it carries no signal at all for this mutation.

**The audit the coordinator asked for.** Everything read off `N/M passed` is sound — that is every
"passed 123/123", "64/64", "123 → 133", "64 → 67" and "140/140" claim in the r1 commit message and
coordinator doc, including M2's own *"reverting `[FAIL] ` → `FAIL: ` passed 123/123"*
(`…r1-coordinator.md:122`). **One claim, in two places, is not:**

- `docs/reviews/coordinator/ship-src-root-alone-r1-coordinator.md:159-172` — the *"red cases"*
  column, under *"each goes red **via the case that names it**"*;
- the r1 commit message `78100320` — *"each red via the case it names: … `[FAIL]` reverted (1) …"*.

Seven of the eight rows are safe: their mutations do not touch the token the grep keys on. **Row
`` `[FAIL] ` → `FAIL: ` | 1 `` is unsupported by the instrument that produced it.** The number is
*numerically correct* — I measured `133 → 131`, one additional red case — but the grep returns `1`
for that row in both directions, and the *"via the case that names it"* half is **false** for it:
the grep cannot name that case, because the case's report line no longer starts with `[FAIL] `.

**Suggested correction, one clause, to both places:** *"`[FAIL] ` → `FAIL: ` — killed, measured
`133 → 131` on the `N/M` line. Per-case attribution for this row alone cannot come from the
FAIL-line parser, because the mutation removes the token that parser keys on."*

⭐ **The shipped consumer is NOT affected, and that is the sharpest part.**
`check-plan-code.parse_fail_names` requires `l.strip().startswith("[FAIL] ")`, so on the mutant it
correctly yields **zero** names rather than the phantom — and its docstring already records this
exact lesson: *"only a line STARTING with `[FAIL] ` is a case name. A mid-line marker is not —
measured round 5, where slicing `[7:]` blind produced a confident, wrong name."* The ad-hoc harness
grep re-made, in this branch, the bug the shipped code carries a paragraph about not making.

**Falsifier:** the `[FAIL] `-grep returns different counts for control and mutant (it does not —
`1` and `1`), or `parse_fail_names` returns a name for the mutant (it does not).

---

## Checks Run

**Green controls, working tree, before and after every mutation:**

```
scripts/explainer-serve.py --self-test                     142/142   (docstring declares 142 ✓)
HOME=$(mktemp -d)/.home … explainer-serve.py --self-test   142/142
scripts/check-fixture-variation.py --self-test              67/67
scripts/check-fixture-variation.py                          OK — 528 parameters, 51 files
scripts/gen-dashboard.py --self-test                       325/325
scripts/check-plan-code.py --self-test                     128/128
scripts/check-docs.py                                       OK
scripts/check-selftest-counts.py                            39 scripts, all verified
scripts/check-ratchet-contract.py                           OK — 36 guards
scripts/check-review-rounds.py                              rc=1, and correctly so: it named
                                                            "ship-src-root-alone round 2: only codex"
                                                            — i.e. this file's absence. Re-run after filing.
```

**Mutations. All applied to the live file from a pinned `cp` snapshot and restored by `cp` in a
`finally`, md5-asserted after each. No git command that writes was run at any point.**

| # | Mutation | Result | Reads as |
|---|---|---|---|
| M1 | `except`-arm `[FAIL] ` prefix → `EXC: ` (Codex r2 M2's exact mutation) | **141/142 KILLED** | Codex's Medium is genuinely fixed |
| M2 | `root = observed.root` → `root = src_root().root` | **142/142 SURVIVES** | **H1** |
| M2′ | same, against `78100320` | **130/133 KILLED** (control 132/133) | H1 is fix-induced |
| M3 | `os.environ.get(SRC_ROOT_ENV)` inside `do_GET` | 136/142 KILLED | mechanism works; message misattributes → **L1** |
| M4 | `safe_path(...)` → `root / path[...]` | 139/142 KILLED | confinement case is load-bearing |
| M5 | `src_root` drops `.strip()` | 141/142 KILLED | pre-existing case still live |
| M6 | `_Forbidden` gains `popitem`, `update` | **142/142 SURVIVES** | **L2** |
| M7 | `_Forbidden` loses `pop` (control for M6) | 141/142 KILLED | the loop is live for removals |
| M8 | re-read via `os.environb` | **142/142 SURVIVES** | boundary, stated under L2, not filed |
| M9 | re-read via `dict(os.environ)` | 136/142 KILLED | `__iter__` forces `dict_merge`'s slow path → `keys()` raises. Measured, not assumed |

**On the brief's item 3 — is the new `[FAIL] ` case brittle or vacuous?** Neither, as far as I can
measure. `_runner_src().count('print(f"  [FAIL] ') == 2` (`:2122-2123`): the literal lives *before*
the `for name, fn in cases:` split point so it is not in its own search space (hazard ① avoided);
M1 shows mangling either arm reddens it. A third legitimate report site does red it, which the
comment at `:2119-2121` claims deliberately and I agree with — `parse_fail_names` is a contract, so a
third site should arrive with a decision. The one innocent edit that breaks it is rewriting a print
as `print("  [FAIL] " + name)`; that is narrow enough to accept.

**On the brief's item 5 — vacuity.** M4 and M5 are pre-existing cases (from the 88-case era) and
both still kill. The suite's growth did not hollow them out. M4's kill arrives via a `ValueError`
from `relative_to` rather than by serving `escaped.md`, which is incidental to `/var`→`/private`
symlink resolution on macOS; the case is still discriminating (on a machine without that symlink the
body would be `escaped.md`'s HTML, also `!= b"no such source file"`). No finding.

**On the brief's item 6 — extraction hygiene.** Clean, confirming Codex. `grep` over `scripts/`,
`app/`, `lib/`, `.claude/` for `RESTART_LOCK`, `Handler._restart`, `/_alive`, `/_restart`,
`RESTART_LOG`, `respawn`, `--restart`, `--respawn`, `page_chrome.restart_control`,
`restart_commands` returns only: `pid_alive` (an unrelated pre-existing function), two prose
mentions of the word "restart" in comments, and `gen-dashboard.py:2220-2223` which explicitly says
the restart chrome is *not* in this branch. No live reference.

**Not re-filed, per the brief:** backlog #122 (no mutation manifest for this file), #123
(`EXPLAINER_DOCS_ROOT=~unknownuser/x`), #125/#126/#127 (the parked restart feature), and r1's L4
(refuted by measurement).

---

## Item 2, as the coordinator re-framed it: *is v3 complete, and was collapsing two mechanisms into one the right call?*

**Complete: NO — and no interception-based version can be.** Right call: **yes on the collapse,
but it does not reach the real problem.**

The coordinator measured ten second-read surfaces against v3, all caught, and named three as
untested. I measured all three, on the pinned snapshot, out of tree (control `141/142`):

| surface | result | is it a genuine read? |
|---|---|---|
| `os.environb.get(SRC_ROOT_ENV.encode())` | **SURVIVES** `141/142` | **yes** — reads the real value |
| `subprocess.run(…)` child reading `os.environ` | **SURVIVES** `141/142` | **yes** — the child inherits the real environ |
| `os.putenv(SRC_ROOT_ENV, …)` | SURVIVES `141/142` | **no** — a write; no read semantics, so not a violation of *this* invariant |

**The two genuine survivors are not enumeration gaps; they are the approach's ceiling.** Swapping
`os.environ` replaces a *Python object*. `os.environb` and every child process read the **C-level
environ**, which no Python-level object swap can intercept. Add a twelfth surface and a thirteenth
and these two remain, by construction.

Put that beside H1 and the shape is clear. The set of ways to consult the world is **open**, so
every interception-based guard is defeated by its next member — and the record is four for four:

| attempt | surface it covered | what defeated it |
|---|---|---|
| `_Forbidden` v1 (#295 r4) | `get` | `dict()`, `len()`, `for k in` |
| `_Counting` v1 (r1) | `get` | `SRC_ROOT_ENV in os.environ` |
| `_Counting` v2 (r2) | eight surfaces | `setdefault`, `pop`, `repr`, `==` |
| stub + `_Forbidden` (r2, v3) | every `os.environ` spelling | **a second `src_root()` call** (H1), `os.environb`, subprocess |

**So: collapsing two mechanisms into one was right** — maintaining a rival to `_Forbidden` was a
real defect and removing it was correct. **But it fixed the duplication, not the incompleteness**,
and in doing so it lost the one property the counter had (H1). That is why I do not think a fifth
interception patch is the answer, and why the arming below matters more than any single finding
here: **the durable instrument asks the question where the set is CLOSED** — over the ten lines of
source the branch owns, where "does this region call `src_root()` twice or name an environment API"
is decidable, and where `os.environb` and subprocess fall to the same rule as the second
`src_root()`. I note the coordinator has begun exactly that (see the third drift, below); on the
evidence above I think that direction is correct.

---

## Process note — the subject moved THREE times while I was reviewing it

Recording this because it nearly cost the round, and because a reviewer reporting on a revision that
no longer exists is the *"a reviewer can review the WRONG SUBJECT"* failure this project has already
paid for once.

1. My first `git diff` returned round 2's fix as the brief describes it: `_Counting` broadened to
   eight surfaces. A `grep` seconds later found **no `_Counting` in the file** — it had been replaced
   wholesale by the `_Forbidden` reuse. File mtime `16:44:46`; md5 `da82190f…`.
2. I snapshotted, messaged the team lead asking for a freeze, and continued. At `16:47:20` the file
   changed **again** — this time the `[FAIL] ` fix landed — md5 `323bc2a4…`.

3. After I filed, the coordinator declared the tree **frozen** at `323bc2a4…` and asked me to
   re-base. No re-base was needed — `323bc2a4…` is the revision every measurement above already ran
   against; I had re-pinned mid-review. **Three minutes after the freeze was declared, the file
   changed again** (`17:00:40`, md5 `bf23d242…`, docstring `142 → 150 cases`): a redesign of
   `_drive_src` that adds a **static source check** over the `/src/` branch, citing H1. At that
   point I stopped touching the working tree altogether and ran the remaining measurements against
   my snapshot copy, out of tree.

**Everything above is against `323bc2a4…`** — the revision the coordinator froze, and the last one
that was stable long enough to measure. `bf23d242…` is **round 2's response to this review**, so it
is round 3's subject, not mine; reviewing it here would collapse the two rounds and leave the
response unreviewed by anyone. H1's mutation is two lines and the table above says exactly what each
revision should print, so re-measuring it against `bf23d242…` is cheap — **and it should be done by
round 3, over a tree that is actually still.**

⚠ **The recurring hazard, stated once.** Three times in one review the subject changed under the
reviewer, and once (M2) a change silently discarded seven minutes of work. This project's own record
already carries *"a reviewer can review the WRONG SUBJECT"*. The cheap structural fix is not a
promise to hold still — that was made and broken in three minutes, with no bad faith involved — it
is to review a **commit or a worktree copy**, so the reviewer's subject cannot move at all. Editing
and reviewing the same mutable file concurrently is what made M2 possible and nearly invalidated H1.

---

## Verdict

**NOT CONVERGED.**

- **H1 must be fixed before merge**, and **the architecture-review rule arms on it.** Round 1's fix
  caused round 2's Medium; round 2's fix caused H1. Same component, two consecutive rounds, code not
  prose. The process says that is a Phase 6 trigger, not a third patch — and the branch it forked
  from, PR #295, was parked by this exact rule. My recommendation is therefore **not** "apply the
  counting-stub fix I sketched in H1"; it is to take the arming seriously and let a design pass
  decide whether `_drive_src` should exist in this shape at all. The component has now produced a
  half-covering guard in four consecutive attempts (`_Forbidden` v1, `_Counting` v1, `_Counting` v2,
  and now the stub), which is a stronger signal than any individual finding here.
- **M1 should be fixed before merge** and is nearly free: restore the two deleted verdicts. It is
  unrelated to H1 and does not depend on the architecture review.
- **M2 and M3 need no code change** — both are already closed or one clause from it. M2's hazard was
  accidentally removed when the re-applied case got a new name; make that deliberate (*a fix that
  changes what a case asserts changes the case's name too*). M3 needs the one-clause correction
  quoted in the finding, in `…r1-coordinator.md:159-172` and in `78100320`'s message. Both belong in
  the architecture review's input, because both are instrument defects on the component that armed
  it, and the arming rule exists to catch exactly the pattern they evidence.
- **L1, L2** are one-liners inside the component H1 concerns; they should ride with whatever that
  review decides, not be patched ahead of it.
- **L3** is one clause of comment text and can ride with anything.

**Tree state on exit.** Nothing was staged, committed, stashed, restored or reset at any point; no
`explainer-serve.py` process was signalled; no port was bound. Every mutation I applied to the
working tree was applied from a `cp` snapshot and restored by `cp` in a `finally` with an md5
assertion, and all of those ran while the file was at `323bc2a4…`; after `17:00:40` I stopped
writing to the tree entirely and measured only against my out-of-tree copy.

`scripts/explainer-serve.py` is at `bf23d242…` on exit — **not** my doing and not damage: that is
the coordinator's in-flight redesign, landed at `17:00:40`. The last revision I wrote to that path
was the restore to `323bc2a48fa87c8a928f0b7a3af2ec14`, verified by md5 immediately afterwards.
