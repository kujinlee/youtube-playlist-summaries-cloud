# Adversarial review — round 3 — Claude half — `explainer-src-root-self-configures` (PR #295)

All claims below were produced by RUNNING code in a copy of the worktree at
`…/1d12d1a5…/scratchpad/exp/wt`. The worktree itself was not modified.

## Verdict

**FINDINGS** — 4 Medium, 2 Low. And I concur with the Codex half: **the architecture review is
armed**, though on stronger grounds than the ones Codex gave.

---

## ⛔ Verdict on the ARMING DECISION

**Armed. Justified — but NOT by Codex's finding on its own, and I want that on the record because
the finding as written would not carry the decision.**

### Codex's instance is real. I reproduced it.

```
src_root_help("", <an existing directory>)
  -> "no source root — EXPLAINER_DOCS_ROOT is set to '', which is not a directory.\n\n
      Unset it to serve sources from the repo this server runs from (…)"
```

The string is exactly as Codex described: it asserts the variable is *set* to `''` when it is
*unset*, and then advises `unset EXPLAINER_DOCS_ROOT`, which is already the state.

### But on reachability, Codex overstates it, and I tried hard to refute it.

Reaching that state through the only production caller requires `REPO.is_dir()` to be **false** at
`scripts/explainer-serve.py:478` and **true** at `:543` — two probes separated by a handful of
microseconds. As a directory-deletion race that is not hittable by a human. Codex labelled this
Medium; **as an observable symptom it is a Low.**

One measurement does widen it, and it is worth having:

```
is_dir on a real directory whose parent is mode 000: False   (it IS a directory)
after restoring the parent's permissions:            True
```

`Path.is_dir()` swallows `OSError` and returns `False`. So "not a directory" in this code does not
mean *gone*; it means *I could not confirm it*. The flip therefore does not require anyone to
delete and restore a checkout — a transient `stat` failure (a parent's permissions changing, an
unmounting volume, a stale NFS handle) produces it with no state change at all. Still a race, but
one with a much larger population of causes than "someone deleted the repo and put it back".

**On the strength of this finding alone I would argue AGAINST arming.** A microsecond-wide TOCTOU
in a 404 body, whose emitted commands still work, is not worth an architecture review.

### What actually arms it: the same defect, four times, in three rounds.

`docs/review-method.md:436` keys the trigger on **cause, not count** — *"did the previous fix cause
this?"* Here is the per-finding evidence the method doc asks for.

The component's defect class is one sentence: **`src_root_help` is not told why it was called, so
it reconstructs the reason, and the reconstruction can disagree with the original.**

| Round | Finding | The re-derivation |
|---|---|---|
| r1 M1 | the gone arm printed commands inside the missing directory | it derived the paths from `repo` rather than being handed a path known to survive |
| r2 M1 | r1's fix used `Path(__file__).resolve()` "which necessarily exists" | it re-derived an anchor from `__file__`; the caller's `repo` **contains** that file, so the claim was false in production |
| r2 M | the two arms disagreed about what survives a missing checkout | each arm re-derived its own view of the world |
| **r3 (Codex)** | the branch re-probes `repo.is_dir()` | it re-derives the reason `src_root` already computed |

That is four instances of one class, and **two of them were introduced by the previous round's own
fix** (r2 M1 by r1's fix; r3 by r2's fix). Two consecutive rounds, one component. The condition
fires on its own terms.

### The sharpest piece of evidence, which neither half has stated yet

The r2 fix **traded a guarantee for an observation**, and `git log -S` shows it precisely.

At r1 (`5e64d68b`) the branch was on the *argument*:

```python
if env_value:
    return <env arm>
return <gone arm: "EXPLAINER_DOCS_ROOT is unset and the fallback {repo} is not a directory">
```

In that shape the empty-env arm was **entailed by the caller's contract**: with an empty env value,
`src_root` returns `None` only via `:478`, i.e. only when `REPO.is_dir()` was false. The arm could
not be wrong about the fallback. It was correct by construction, not by luck.

At r2 (`f1daca10`) the branch became `if not repo.is_dir():` (`:543`). That fixes the genuinely
reachable r2 Medium (env set + repo gone), and it is a real improvement. But the empty-env case is
no longer decided by the contract — it is **re-decided by a fresh syscall**, and the code's own
comment at `:548-552` asserts the lost guarantee as if it still held:

> `repo` EXISTS here, so a bad `env_value` is the only remaining reason to be in this function …
> and the second is answered above. There is deliberately NO trailing arm

"Answered above" is the error in one phrase. `repo.is_dir()` at `:543` does not *answer* what
`REPO.is_dir()` returned at `:478`; it **re-asks** it. And on the strength of that false invariant
the fix **removed the fallthrough arm**. An entailment was replaced by a re-observation, and the
safety net that would have absorbed the disagreement was deleted in the same edit.

**That is a design regression, not a patchable slip** — which is exactly what distinguishes
thrashing from a normal round. The observable symptom is Low; the thing the symptom is evidence of
is what arms the review.

### The record should also note what Q5's own instrument currently says

```
$ python3 scripts/check-review-decision.py
ROUND_OWED — r1 produced a Blocking
  branch=explainer-src-root-self-configures  scope=full-loop  rounds=2  tree_reviewed=False
```

It has not consumed an r3 header, so it reports neither thrashing nor convergence.
`review-method.md:20` says deciding this from memory **is** the defect. **The coordinator should
record r3's header with `fix_induced` set before acting on the arming**, so the call is derived
rather than remembered.

---

## ⛔ Verdict on the PROPOSED REDESIGN

**Right axis. Under-scoped as stated — it would remove round 3's instance and leave two of the
earlier three standing.** Build it, but not in the form Codex wrote.

### What it does fix

Carrying the reason instead of re-probing removes the disagreement at `:478`/`:543` structurally.
There is no way to express Codex's finding once `src_root_help` has no filesystem access. Correct,
and it is the right primitive.

### Concrete failure modes the redesign would still have

**(a) It carries the REASON; it does not carry the ANCHORS — and r1 M1 and r2 M1 both lived in the
anchors.** Those two findings were about *which paths the message offers* (`repo/scripts/…`,
`Path(__file__)`, the pidfile), not about which branch it takes. A `missing_fallback(repo)` variant
tells the help *why* it was called and says nothing about *what path is safe to print*.
`_gone_checkout_help` would still reach for the module-level `PIDFILE` through a default argument
(`:484`) and the sibling arm would still build `repo / "scripts" / "explainer-serve.py"` itself.
**Two thirds of this component's history is untouched by the proposal.**

**(b) The reason is still a snapshot, so the message must stop being a diagnosis.** See Finding 3:
`:571` asserts *"The checkout this server was started from has moved or been deleted"*, which the
`is_dir()` measurement above shows is one cause among several, and whose remedy is wrong for the
others. A structured result narrows the branch and does nothing to that sentence. The redesign must
phrase the body as an **observation** — *"`EXPLAINER_DOCS_ROOT` was unset and `<repo>` did not stat
as a directory when this request was handled"* — not as a cause. The branch applied exactly this
rule to `page_chrome`'s `_why` in the same commit (`3a42194c`) and did not carry it one file over.

**(c) `bad_env(value)` must carry the value the PROBE used, and Codex did not say so.** The caller
reads the env **twice** (`:472`, then again at `:1102`). An implementer could carry the reason and
still write `src_root_help(os.environ.get(SRC_ROOT_ENV, "").strip(), …)`, leaving the oldest
instance of the class in place — see Finding 2. Say it explicitly in the redesign, or it will be
rebuilt.

**(d) A three-member sum type invites a fourth, and Python will not force the match to be
exhaustive.** `src_root` has visible pressure to grow `repo_is_a_file` and `permission_denied`
(that is what (b) implies). If a member is added and the help's dispatch is not updated, the
failure is a silent fallthrough — the same shape as the arm this round is about. It needs either
`assert_never` on the else, or a case that iterates every member and asserts each renders.

### Cost

Bounded and small. One sum type, one call site (`:1100-1102`), and about twelve self-test cases to
re-point. `check-fixture-variation` will demand the new parameter be varied and a new
`EXAMINED_KEYS` pin — it already caught precisely this for `src_root_help.pidfile`, so that cost is
known rather than guessed.

### The better reshaping — and the thing this component has never had

Do the structured result, **and add a falsifier for the CLASS rather than for the instance.** Every
guard this component has grown so far names one instance; that is why the fourth instance arrived
unguarded. Purity is directly testable:

```python
# hypothesis, not verified
case("src_root_help renders from what it was TOLD, not from the world",
     lambda: _renders_with(os_environ={}, is_dir=_raises))   # monkeypatch both
```

Call `src_root_help` with `os.environ` emptied and `pathlib.Path.is_dir` patched to raise. **If the
body still renders, it carried. If it raises or changes, it re-derived.** That case fails on every
one of the four historical findings, including ones nobody has thought of yet — which is the
property `review-method.md` is asking for when it tests *can a redesign remove it?*

---

## Findings

### [Medium, fix-induced] `src_root_help` re-probes the filesystem instead of carrying `src_root`'s reason, and the fix deleted the fallthrough on the strength of a false invariant

**Where:** `scripts/explainer-serve.py:543-552`, against `:473-478` and `:1100-1102`

**What:**

```python
# :473-478
if not v:
    return REPO if REPO.is_dir() else None
# :543-544
if not repo.is_dir():
    return _gone_checkout_help(env_value, repo, pidfile)
# :548-552
# `repo` EXISTS here, so a bad `env_value` is the only remaining reason to be in this function:
# … and the second is answered above. There is
# deliberately NO trailing arm …
```

**Why it matters:** "answered above" is false — `:543` re-asks `:478` rather than answering it.
Measured output when the two disagree: *"EXPLAINER_DOCS_ROOT is set to `''`, which is not a
directory"* plus *"unset it"*, about a variable that is unset. Reachable only through a
microsecond-wide window, but `Path.is_dir()` swallowing `OSError` (measured above: a real directory
under a mode-000 parent reports `False`) means the window can open without any state change. The
design cost is the larger one: r1's `if env_value:` branch was entailed by the caller's contract and
could not be wrong; this one can, and the arm that would have caught the disagreement was removed.

**Suggested fix:** *(hypothesis)* the structured-result redesign, with the four caveats above.
Confirms the Codex half's finding; I disagree with its Medium label for the symptom and with
"reappearing directory" as the only trigger.

---

### [Medium] The caller reads `EXPLAINER_DOCS_ROOT` twice — the oldest instance of this component's defect class, unnamed in three rounds

**Where:** `scripts/explainer-serve.py:472` and `:1102`

**What:**

```python
# :472, inside src_root()
v = os.environ.get(SRC_ROOT_ENV, "").strip()
# :1102, in the caller, after src_root() has already returned
body = src_root_help(os.environ.get(SRC_ROOT_ENV, "").strip(), REPO)
```

**Why it matters:** the same *re-derive rather than carry* move as Finding 1, two lines apart, and
it has survived every round. It is also what made r1's entailment conditional in the first place:
the r1 arm was only correct by construction *given* the two env reads agree. Not reachable in
production today — I checked every `os.environ` write in the file and all four are inside the
self-test's `with_env` helper (`:1692-1701`), so nothing mutates the environment under the running
server. **Label: structural, not currently reachable.** It matters because a redesign that carries
the reason but not the value leaves it standing, and then the class survives the architecture
review that was convened to remove it.

**Suggested fix:** *(hypothesis)* have `src_root`'s error variant carry the exact string it read;
the caller should never name `SRC_ROOT_ENV` again.

---

### [Medium] `_gone_checkout_help` states a CAUSE it cannot know, and offers a remedy that is wrong for the causes it cannot distinguish

**Where:** `scripts/explainer-serve.py:571-576`

**What:**

```python
f"The checkout this server was started from has moved or been deleted, so no command "
f"under it can be offered. …"
f"then start it again from a checkout that exists, setting {SRC_ROOT_ENV} to that "
```

**Why it matters:** the only observation behind this sentence is `repo.is_dir() == False`, and I
measured that a directory which exists and has not moved reports `False` when a parent denies
search — likewise for an unmounted volume or a stale network handle. In those states the message
tells the reader their checkout was deleted when it is sitting there, and *"start it again from a
checkout that exists"* is unactionable because the checkout does exist. This is the identical
defect the branch fixed in `page_chrome`'s `_why` in commit `3a42194c` — *"a failure message that
names the wrong cause sends the next reader to the wrong place"* — not carried across files.

**Partly fix-induced.** The sentence predates r2 (`5e64d68b`), so it is not new. But the r2 fix
**widened its reach**: it now also serves the env-var-set arm, so the text now asserts "your
checkout was deleted" in a state where a stale `EXPLAINER_DOCS_ROOT` is the more likely culprit.

**Suggested fix:** *(hypothesis)* name the observation and leave the cause open — *"`<repo>` did not
stat as a directory"* — and list the plausible causes rather than picking one.

---

### [Medium] `explainer-serve.py`'s failure printer cannot be read by the mutation harness, so the file holding this branch's Blocking can never join `--mutate .`

**Where:** `scripts/explainer-serve.py:1882,1884` vs `scripts/check-plan-code.py:1508`

**What:**

```python
# explainer-serve.py:1882
print(f"  FAIL: {name}")
# check-plan-code.py:1508 — the consumer half of the contract
for l in out.split("\n") if l.strip().startswith("[FAIL] ")]
```

**Why it matters — measured, not reasoned.** I ran `parse_fail_names` from the delivered
`check-plan-code.py` against both real printer shapes:

```
parse_fail_names(explainer-serve shape) -> []
parse_fail_names(page_chrome shape)     -> ['the control renders a button']
```

So every mutation entry ever written for `explainer-serve.py` would be refused with *"the suite went
RED but printed no `[FAIL] <case>` line"*. `check-plan-code.py:3185-3215` documents this as a
repeatedly-costly class with an abandoned pre-flight guard and a deliberately-underived population —
**`explainer-serve.py` is the next member of that list and nothing in this branch says so.**

The asymmetry is what makes it worth filing rather than shrugging at: this branch's **Blocking**
(r1 B1, shell quoting) was in `explainer-serve.py`, and the branch paid the ratchet for
`page_chrome.py` (11 → 13, `check-plan-code.py:834`) citing exactly this kind of invisibility —
while the file where the Blocking actually lived stays structurally ineligible. It fails **loud**,
not open, which is why this is Medium and not High.

**Suggested fix:** *(hypothesis)* change the two `print` lines to the `[FAIL] ` marker — it is a
one-line repair that makes the file manifest-eligible — then pay entries for the shell-quoting and
branch code this branch added. Alternatively record a written reason here for why it stays out.

---

### [Low] The first delegation case uses the substring instrument this branch condemned one commit earlier, and is redundant with the case beside it

**Where:** `scripts/explainer-serve.py:1832-1834`

**What:**

```python
case("help: src_root_help passes its own pidfile through to the gone-checkout arm",
     lambda: "/tmp/injected here/x.pid" in
             src_root_help("", _missing, pathlib.Path("/tmp/injected here/x.pid")))
```

**Why it matters:** this is `str(PIDFILE) in _arm` — the exact instrument the r2 High condemned as
**inverted**, reintroduced in the commit that condemned it. It passes only because the fixture
contains no apostrophe. Substitute the suite's own hostile fixture `/tmp/it's home/…` and
`shlex.quote` emits `'/tmp/it'"'"'s home/…`, the raw path stops being a substring, and **correct
code fails** — the precise failure the r2 High documents.

It is also redundant. I mutated the delegation away (`_gone_checkout_help(env_value, repo, PIDFILE)`)
and measured:

```
FAIL: help: src_root_help passes its own pidfile through to the gone-checkout arm
FAIL: …and quoted, so an injected hostile path is still one operand
self-test: 120/122 passed
```

The second case — which uses `_inner_argv` and an apostrophe-bearing fixture — carries the property
on its own and is sound. The first adds no coverage and adds a trap for whoever next edits the
fixture.

**Suggested fix:** *(hypothesis)* delete it, or convert it to the `_inner_argv` form so both
delegation cases use the instrument the branch adopted.

---

### [Low] `_inner_argv` raises on a pidfile path containing a newline

**Where:** `scripts/explainer-serve.py:1797-1798`

**What:**

```python
def _inner_argv(line: str) -> "list[str]":
    return shlex.split(line[line.index("$(") + 2:line.rindex(")")])
```

**Why it matters:** measured — a pidfile of `/tmp/new\nline/x.pid` makes `splitlines()` in the
caller hand `_inner_argv` a fragment with no `$(`, giving `ValueError: substring not found`. It is
**not** a vacuous pass: the runner at `:1883` catches it and prints a FAIL. Same shape as r2's Low 4
one file over, at much lower stakes — `HOME` containing a newline is not a real configuration. Noted
for completeness because Finding 4 means that FAIL line is unparseable by the harness anyway.

**Suggested fix:** *(hypothesis)* leave it; or extract the `kill` line by index rather than by
`splitlines()` if the fixture set ever grows a newline.

---

## What I checked and found CLEAN

Stating these so the round records what would have had to be true for me to find something.

- **ARGV slicing against `)` and `$(` — Codex's negative result independently confirmed, not
  trusted.** I ran nine fixtures including `/tmp/a)b/x.pid`, `/tmp/ab)/x.pid`, `/tmp/a$(id)/x.pid`
  and `/tmp/)$(/x.pid`; all eight non-newline cases returned exactly `["cat", str(pf)]`. The slicing
  is safe by construction: the emitted line always ends `)"`, so `rindex(")")` is always the closer,
  and it always begins `kill "$(`, so `index("$(")` is always the opener. No vacuous pass.
- **`kill "$(cat …)"` under a missing / empty / whitespace / multi-line / non-numeric pidfile.** All
  benign: the substitution is double-quoted, so there is no word splitting and the worst outcome is
  `kill` printing a usage error. **And a stale pidfile does not block recovery** — I traced `start()`
  (`:1249-1255`), which gates on `port_busy`, not on the pidfile, and overwrites it at `:1258`. The
  `kill` remedy leaving the pidfile behind costs nothing.
- **All three r2 fixes are load-bearing.** Mutation-tested against a green control (122/122): the
  delegation → 2 red; unquoting the pidfile → 5 red across 4 hostile fixtures; reverting the branch
  to `if not env_value:` → 2 red. Each dies via a case that names it.
- **`repo` as a FILE is unreachable in production.** `REPO` is the parent of a resolved `__file__`'s
  directory, so it is always a directory; and an env var pointing at a file routes correctly to the
  env arm, which describes it accurately.
- **`page_chrome`'s non-raising `shlex.split` cannot mask a regression.** The sentinel
  `f"UNPARSEABLE: {_e}"` never equals the expected argv, so a raise becomes a FAIL, printed with the
  conforming `[FAIL]` marker.
- **`page_chrome`'s `_why` is correct on every reachable path.** It is pre-assigned optimistically
  but only ever *read* in the `else` branch, where it names the last attempted step in all three
  failure routes.
- **`gen-dashboard`'s `_fragment` repair is right.** It anchors to the card's own article and
  `raise`s at `:2100` when the id is absent, so the anchor cannot silently slide onto another
  `<summary>` the way the positional read did.
- **Guards all green on the delivered tree:** `explainer-serve` 122/122, `page_chrome` 76/76,
  `check-plan-code` 128/128, `check-fixture-variation` 60/60 and 533 parameters across 51 files,
  `check-selftest-counts` 39 scripts each verified by running it.
- **`EXAMINED_KEYS` pins behave as documented** — one-directional (`pinned - examined`), so a
  misspelled pin is reported and an unpinned examined parameter is not. The comment says this.

---

## Recommendation

Arm the architecture review, and record r3's header so `check-review-decision.py` derives the call
instead of the coordinator remembering it. Take the structured-result redesign as the starting
point, but widen it with (a) the anchors, (b) observation-not-diagnosis in the message, (c) a single
source for the env value, and (d) the purity falsifier — without those it removes one instance of a
class that has now produced four.

Findings 2, 3, 4 and the two Lows do not need to wait for the architecture review; 4 in particular
is a one-line printer change plus manifest entries.
