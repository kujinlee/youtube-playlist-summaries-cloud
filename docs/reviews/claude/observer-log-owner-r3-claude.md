# Round 3 — Claude half — `observer-log-owner` (PR #342)

**Subject:** the FOLD, not the original. `9c843358` (r2 fold part 1) and `6367c90f` (r3 fold part 2,
HEAD), plus `git diff origin/master...HEAD` for what the folds broke.

**Mandate:** refute, not confirm. Every claim below that I could not refute is reported as verified
**by what I ran**, with the command and its output.

**Counts:** 1 Blocking · 3 High · 4 Medium · 4 Low

⛔ **THE BLOCKING IS THE HUNTED SHAPE AGAIN, AND IT IS IN THE MECHANISM THIS TIME, NOT THE PROSE.**
M1's four new mutation entries are **refused by the harness at HEAD**. The fold measured each entry
by applying its edit; it never ran the loader that reads the manifest. Rounds 1 and 2 committed
their defect inside the fix for it; round 3 did too.

⚠ **Two environment facts that bound everything below.**

1. **The working tree is NOT HEAD.** While I was reviewing, `git status` showed three files modified
   by the coordinator (`scripts/check-plan-code.py`, `scripts/mutations/check-ci-watched.json`,
   `scripts/mutations/check-closing-table.json`) — an in-flight repair of exactly the Blocking
   below. My first per-mutation run read manifests from that live tree and so measured the
   **uncommitted** anchors, not HEAD's. I discarded that reading and re-derived HEAD separately from
   `git archive HEAD`. Where a measurement is against the working tree rather than HEAD I say so.
2. **`timeout` does not exist on macOS.** My first attempt at running the eight suites was
   `timeout 600 python3 …`, which printed `timeout: command not found` **eight times with `rc=0`**
   from the trailing `echo`. That run measured nothing and is discarded — recorded because a
   "cannot run" that reports 0 is the failure mode this repo files hardest against.

---

## What I verified GREEN, by running it

### Every touched suite, in the repo

```
$ for f in observer_log check-banner-armed check-ci-watched check-closing-table \
           check-dashboard-entry check-plan-code check-selftest-counts check-fixture-variation; do
    python3 scripts/$f.py --self-test; done
observer_log             41/41 passed          rc=0
check-banner-armed      160/160 passed         rc=0
check-ci-watched         57/57 passed          rc=0
check-closing-table     153/153 passed         rc=0
check-dashboard-entry   149/149 passed  +13/13 cannot-run cases   rc=0
check-plan-code         128/128 passed         rc=0
check-selftest-counts    18/18 passed          rc=0
check-fixture-variation  67/67 passed          rc=0
```

All six suite counts the commit message declares match: `observer_log 41/41, banner 160/160, ci
57/57, closing 153/153, dashboard-entry 149/149, plan-code 128/128`. **Verified.**

Repo-level gates, run against a `git archive HEAD` tree with `node_modules` and `.git` symlinked in
(without them `check-plan-code` reports 125/128 and `check-paid-caller-arrival` 12/32 — both copy
artifacts, not branch defects):

```
check-ratchet-contract  → ratchet contract OK (40 guards discovered)           rc=0
check-docs              → Documentation integrity OK                           rc=0
check-anchors           → 13 registered, all claimed; floor 22 held            rc=0
check-review-rounds     → 330 parsed, 0 silent gaps, 181 verdicts read         rc=0
check-selftest-counts   → 46 scripts declare a count, every one verified       rc=0
check-plan-code --self-test (HEAD tree) → 128/128                              rc=0
check-dashboard-entry (repo) → ok — an entry block was added                   rc=0
```

### H3 (a) — all four observer write sites delegate, and there are no others

```
$ git grep -nE 'banner-warnings|banner-flush-observations|ci-unwatched|closing-table-warnings'
$ grep -rnE '\.open\("a"|open\([^)]*"a"' scripts/
```

Exactly four write sites exist and all four go through `observer_log`:

| site | call |
|---|---|
| `check-banner-armed.py:977` | `observer_log.append(FLUSH_LOG, …)` |
| `check-banner-armed.py:1197` | `observer_log.append_or_raise(WARN_LOG, …)` |
| `check-ci-watched.py:415` | `observer_log.append_or_raise(WARN_LOG, …)` |
| `check-closing-table.py:878` | `observer_log.append(WARN_LOG, line)` |

The only remaining `open("a", …)` in `scripts/` outside the module is
`explainer-serve.py:1299` (`QUESTIONS`, an unrelated file). The other `mkdir` calls in the three
observers target `JOURNAL_DIR` (`check-banner-armed.py:951`) and `SENTINEL`
(`check-ci-watched.py:434`) — different files, correctly out of scope.

**Claim (a) and (b) verified:** one write, one `mkdir`, one `encoding=` for the observer logs.

### H3 (c) — the separate-function rationale is grounded in a real call site

The docstring argues `append` must not return `OSError | None` because `if append(...)` would
silently invert. That call shape actually exists:

```
scripts/check-closing-table.py:935:        if _append_log(log_line(acts, when, session_id, turn_id_of(judged))):
```

**Verified** — not a hypothetical. The design choice is sound and I could not refute it.

### H3 — both rewired call sites are exercised

Neutered each site (replaced the call with `pass`) on an isolated copy:

```
banner WARN_LOG write neutered → 152/160   (control 160/160)
ci     WARN_LOG write neutered → IndexError in _self_test:638, suite crashes  (control 57/57)
```

Matches the commit message's "banner 152/160, ci crashes outright". **Verified** — though see
Medium 4 on what "crashes outright" does and does not buy.

### M1 — every count in the rewritten removal account, re-derived as sets

`git show origin/master:scripts/mutations/<f>.json` vs the branch copy, names diffed as sets:

| manifest | master | branch | removed | added |
|---|---|---|---|---|
| `check-banner-armed` | 47 | 47 | 2 | 2 |
| `check-ci-watched` | 29 | 29 | 3 | 3 |
| `check-closing-table` | 47 | 48 | 1 | 2 |
| `check-dashboard-entry` | 43 | 44 | 0 | 1 |
| `observer_log` | — (new) | 16 | — | 16 |

- **Six entry names left the three adapters** — 2 + 3 + 1. **Verified.**
- **Class ⑴ RETIRED WITH THEIR SUBJECT — 3**: ci's *fields stop being sanitised*, ci's *sanitiser
  EMPTIES the field*, closing's *empty-session fallback*. Exactly the three the comment lists.
  **Verified.**
- **Class ⑵ RENAMED AND RETARGETED — 2**: both banner `flush_line` entries, present in both the
  removed and added sets, netting zero. **Verified.**
- **Class ⑶ REPLACED BY A DIFFERENT PROPERTY — 1**: ci's *drops its SESSION column* → *drops a
  PAYLOAD column*. **Verified.**
- 3 + 2 + 1 = 6, and every removal falls in exactly one class. **Verified.**
- **"Net: banner 47→47, ci 29→29, closing 47→48, +16 for the new owner"** — matches master→branch
  exactly. **Verified.**
- **Pins "observer_log 15→16, ci 27→29, closing 46→48, dashboard-entry 43→44, sum 966→972"** — these
  are the intra-fold deltas (previous branch commit → HEAD), not master→branch, and every one is
  right read that way. Measured per commit:

```
master   954  pins: banner 47, closing 47, ci 29, dash 43
088649a6 964  pins: banner 45, observer_log 15, closing 46, ci 27, dash 43
b360f7cf 966  pins: banner 47  (the unearned fall restored)
9c843358 966  (no pin change)
6367c90f 972  pins: observer_log 16, closing 48, ci 29, dash 44
```
  Declared literal and `sum(EXPECTED_MUTATIONS.values())` agree at **every** commit. **Verified.**

### M1 — the four new entries die through the case they name

⚠ **Against the WORKING-TREE anchors, because HEAD's cannot be loaded at all** (Blocking 1). Applied
each edit by hand to a `git archive HEAD` copy with `HOME` redirected; green control first.

| entry | anchor resolves | result | named case red? |
|---|---|---|---|
| ci freezes session | 1× | 49/57 | ✅ `the SESSION column comes from the Stop payload…` |
| ci freezes TIMESTAMP | 1× | 56/57 | ✅ `log_line carries the version cell plus all FOUR columns…` |
| ci drops a PAYLOAD column | 1× | 53/57 | ✅ same case |
| closing freezes session | 1× | 2 cases red | ✅ `log: the session is the THIRD field, verbatim` |
| closing freezes TIMESTAMP | 1× | 1 case red | ✅ `log: the timestamp is the SECOND field…` |
| `append_or_raise` swallows | 1× | 39/41 | ✅ `append_or_raise RAISES OSError where append returns False` |

**49/57 and 56/57 match the commit message's claimed measurements, and closing-table's two are
clean single-case reds.** Verified — for the working-tree manifest.

### M2 — the #168 case can fail and is not ambient

```
mutation "the #168 push clause is dropped from the refusal" → 148/149, rc=1
  [FAIL] the refusal telling you to edit the PR body also says you must PUSH, and why (#168):
         got (True, True→False, True→False) want (True, True, True)
```

The case (`check-dashboard-entry.py:891-894`) asserts three halves as one tuple. Deleting the clause
flips two of the three — so `"PUSH"` and `"frozen event payload"` are not satisfied by any other
text in the refusal. **Verified, non-ambient.**

### M3 — the withdrawal's CONCLUSION is correct. I re-derived it independently.

Extracted every run of ≥3 digits from backlog rows #170–#174 with their surrounding context, then
searched for the literal `964`:

```
$ sed -n '201p' docs/backlog.md | grep -o '964' | wc -l     →  0
$ python3 -c "print('964' in '35889056587')"                →  False
```

**Row #173 contains no `964` and no live mutation count.** Its only quantities are a ratio (79%) and
timings measured on a *named* run (`35889056587`), which is provenance-anchored, not a moved number.
**The withdrawal of that half is correct.** (Its stated *reason* is not — see Low 2.)

The kept half is also right: row #174 quotes `964` twice, and both are now frozen —
*"**964** live mutations **as the manifest stood at `088649a6`** (⚠ r2 M3 — the live total moved to
**972** on this same branch; the RATIO is what this argument rests on, and a reader sizing the work
must re-derive the total…)"* and *"488 of the 964 counted at `088649a6` — 51%"*. I verified `964`
**is** the real `sum(EXPECTED_MUTATIONS.values())` at `088649a6`, and 488/964 = 50.6%. **Verified.**

### r2 H1 did not regress

`check-banner-armed.py:666-670` states the false claim and then refutes it in the same breath — it
is the correction, not a survival. `check-selection-card.py:176` says *"two entries with the same
anchor — which `check-plan-code` refuses"*, which is **true** (identical tuples are refused); it is
not the stronger claim r2 H1 killed. **No regression.**

### r2 L1 was folded

`observer_log.py:276-277` now reads `not in ("", "-", "T1")` — the literal, not `EMPTY`. **Verified.**

### Anchor hygiene across all 980 anchors

```
TOTAL ANCHORS = 980 ;  anchors NOT resolving exactly once: 0
```

Every anchor in every manifest resolves exactly once against the delivered file. The harness also
backs this at `check-plan-code.py:1460` (`src.count(find) > 1` → refusal) and `:1468` (`find not in
src` → refusal), so the in-flight repair's weaker substring anchors are protected. **Verified.**

One duplicate anchor tuple exists **across** manifests — `CELL_SPLIT = re.compile(r"(?<!\\)\|")` in
both `check-docs.json` and `check-features.json`. `seen_anchors` is reset per manifest
(`check-plan-code.py:1215`), and the two target different files, so this is correct behaviour and
pre-existing on master. **Not a finding.**

### `check-fixture-variation` live, and `analyse()` re-derived

```
fixture variation OK — 637 parameter(s) examined across 58 file(s); 121 known-unvaried
ratcheted, 7 exempt with a written reason                                          rc=0
```

`analyse()` on `scripts/observer_log.py` returns **findings = []** — so the comment's *"It reports NO
findings — all six parameters are genuinely varied by the suite"* is right about the findings.
It is wrong about "six" (Medium 3).

---

## Blocking

### B1 — HEAD's manifests are REFUSED by the harness: all four of M1's new entries share an anchor tuple with an existing entry, so `--mutate .` cannot run and M1's fix is not in force

`load_manifests` refuses an entry whose **anchor tuple** repeats an earlier one in the same manifest
(`scripts/check-plan-code.py:1251-1253`). At HEAD, all four entries M1 added use the **whole `return`
line** as their anchor — the same line an existing entry already claims:

```
check-ci-watched.json     anchor '    return observer_log.record(session, reason, detail, when=when)'
    - the log line drops a PAYLOAD column, so a record loses a field        (pre-existing)
    - ci log_line freezes its session column…                              (NEW, r3)
    - ci log_line freezes its TIMESTAMP column…                            (NEW, r3)

check-closing-table.json  anchor '    return observer_log.record(session, "+".join(acts), turn, when=when)'
    - the turn id is dropped from the log line…                            (pre-existing)
    - closing log_line freezes its session column…                         (NEW, r3)
    - closing log_line freezes its TIMESTAMP column…                       (NEW, r3)
```

**What I ran** — `git archive HEAD | tar -x` into a clean tree, then `load_manifests` on it:

```
entries LOADED = 968   (EXPECTED_MUTATIONS sum = 972)
PROBLEMS = 4
   check-ci-watched.json: entry 'ci log_line freezes its session column, so entries stop being
     attributable' repeats the edit anchors of an earlier entry — it measures nothing new
   check-ci-watched.json: entry 'ci log_line freezes its TIMESTAMP column, …'  (same)
   check-closing-table.json: entry 'closing log_line freezes its session column, …'  (same)
   check-closing-table.json: entry 'closing log_line freezes its TIMESTAMP column, …'  (same)
```

**Why this is Blocking and not Medium.** M1's entire deliverable was *the four entries the two
sibling adapters never had*, justified by *"the RATCHET is what proves the cases can fail, and for
two of three adapters nothing held it."* At HEAD the ratchet holds nothing: the four entries do not
load, 968 ≠ 972 so the pinned count cannot be satisfied, and the sweep refuses the manifest before
mutating anything. The fold's headline fix is absent from the commit that claims it.

**How it got past the author, exactly.** The fold measured each entry *by applying its edit* — which
is how it produced the honest "49/57, 56/57, and two clean closing-table reds" — and then verified
*anchor resolution counts* ("979 anchors re-verified to resolve exactly once AFTER the code was
final"). Both checks pass. Neither is the rule that fails. This is *a check result is not the claim*:
the thing that had to be opened was the manifest **loader**, and nothing opened it.

**The repo already knew this rule.** `scripts/check-selection-card.py:168-178` documents it as a
lesson paid for once: *"they were one line, and the manifest then wanted two entries with the same
anchor — which `check-plan-code` refuses… The fix is two lines, not a weaker rule."*

**Fix.** Give each of the four a distinct substring of the line, or split the `return` into named
statements so each entry anchors on its own line. Then re-measure each mutation, because a moved
anchor is a different mutation until something proves otherwise.

⚠ **Already in flight, uncommitted.** The live working tree contains precisely this repair
(substring anchors such as `"detail, when=when)"`, plus a new `:756-763` comment explaining it). I
snapshotted the live tree and confirmed it clears the refusal:

```
entries LOADED = 972   pinned sum = 972   agree=True   PROBLEMS = 0
```

So the defect is in the **committed fold**, and the fix exists locally. It must be committed before
this PR is merged, and B1 must not be recorded as "already fixed" without that commit — r2 B1 was
the mirror image of this (a correction that lived in the commit message and not the file).

⚠ **NOT A DISCOVERY, AND I AM SAYING SO.** While writing this I found
`docs/reviews/claude/observer-log-fold-r3-claude.md` (untracked, written 13:00) — a separate review
of *"the uncommitted anchor-retarget fold"* which reports 0 Blocking and confirms the retargeting.
So the coordinator already knew. What B1 adds is the part that review could not see, because its
subject was the repair rather than the commit: **`6367c90f` as committed is broken, and its message
declares the four entries and the 972 pin as delivered.** The severity is about the state of the
branch tip, not about whether anyone has noticed.

⚠ **Side effect worth one line:** that file gives round 3 a second subject stem, so
`check-review-rounds.py` now reports **two** round-3s (`observer-log-fold` and
`observer-log-owner`), each missing its codex half. Whatever the codex half covers, it needs a
`REVIEW GAP:` line or a filed half under **both** stems, or one of them blocks.

---

## High

### H1 — the module claims the encoding CANNOT be mutation-covered. It can. I built the case and killed the mutant.

`scripts/observer_log.py:165-169`:

> ⚠ **THE ENCODING IS NOT MUTATION-COVERED AND CANNOT BE FROM HERE, which is stated rather than
> left to be discovered.** Deleting `encoding="utf-8"` survives every case on this machine and in
> CI, because the platform default IS utf-8 on macOS and on the ubuntu runner — **a case would pass
> for an ambient reason.**

The premise is true; the conclusion is false. The ambient reason is **an input to the case**, not a
fact about the world: the locale-default encoding is set before interpreter start, so a case can
choose it. Under `PYTHONCOERCECLOCALE=0 PYTHONUTF8=0 LC_ALL=C LANG=C` this interpreter reports
`locale.getencoding() = US-ASCII`.

**What I ran** — a child process that imports `observer_log`, writes a record containing `⛔`
through `append_or_raise`, and compares the raw **bytes**. It prints ASCII only, so the verdict
cannot be an artefact of stdout's encoding (my first attempt made exactly that mistake and failed the
*control*):

```
=== CONTROL (delivered observer_log.py) ===
VERDICT: GREEN (bytes are utf-8 and round-trip exactly)                   rc=0
=== MUTANT (encoding="utf-8" deleted from append_or_raise) ===
VERDICT: RED (UnicodeEncodeError -- the write took the platform default)  rc=1
=== child locale ===
child locale encoding: US-ASCII
```

Green control, red mutant, and the mutant is red **because of the write**. A second, fully
platform-independent falsifier also works: `python3 -X warn_default_encoding -W
error::EncodingWarning` turns any `open()` without `encoding=` into an exception regardless of what
the platform default happens to be.

**Why this is High.** The whole argument for `append_or_raise` is *"one site that can be wrong
instead of four"* — the value is concentrated in a single line, and the module writes down that the
single line is unfalsifiable. That is a self-authored exemption in the place the module claims to
own, and it will be believed: a future reader has an explicit, confident paragraph telling them not
to try. It is also the shape this repo has filed repeatedly as *a self-authored retreat is not a
gate* and *a case can pass for an AMBIENT reason — build the world*.

**Fix.** Add a case to `observer_log._self_test` that spawns `sys.executable` with the env above,
writes a non-ASCII record via `append_or_raise`, and asserts the bytes decode as utf-8; add the
`encoding="utf-8"` deletion to `scripts/mutations/observer_log.json` naming that case; delete the
paragraph. If the subprocess route is judged too heavy, the `-X warn_default_encoding` form is a
two-line alternative. Either way the paragraph must go — it is the load-bearing part of the finding.

### H2 — nothing in `check-plan-code --self-test` reads the real manifests, which is why B1 shipped green through every cheap gate

At HEAD, with four entries refused and 968 ≠ 972, the owning suite is **128/128 green**:

```
$ (cd <HEAD tree> && python3 scripts/check-plan-code.py --self-test)   →  128/128 passed
```

Every `load_manifests` call in `_self_test` uses a temp-directory fixture:

```
scripts/check-plan-code.py:2264, :2270, :2273, :2278, :2290, :2299   → root `_r`  (tempfile)
scripts/check-plan-code.py:2304                                      → root `_r2` (tempfile)
```

and the declared-count case compares the **dict to a literal**, never to disk:

```
scripts/check-plan-code.py:3517:
    case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 972)
```

So `EXPECTED_MUTATIONS` is checked against a number a human typed, and the manifests on disk are
checked by nothing until the 8-minute sweep runs. The comment above `:3517` calls that literal *"the
outside observer of the sum"* — it observes the dict, not the manifests the dict is a claim about.

**Why this is High, separately from B1.** B1 is one defect; H2 is why a whole class of manifest
defect is invisible to every check a person runs before pushing. And backlog **#173 proposes to skip
the sweep on PRs that change no `scripts/**`** — sound on its own terms, but it makes the only
instrument that catches this class conditional, while nothing cheap replaces it.

**Fix.** Two lines in `_self_test`, over the real root (which the file already computes at `:3524` as
`_repo`):

```python
_live_entries, _live_problems = load_manifests(_repo)
case("the manifests ON DISK load without refusal", _live_problems, [])
case("...and the count they yield is the pinned one",
     len(_live_entries), sum(EXPECTED_MUTATIONS.values()))
```

Measured: this is red at HEAD (`968` / 4 problems) and green on the in-flight working tree (`972` /
0), in well under a second. It also wants a mutation entry, since a case with no ratchet is the
thing M1 was about.

### H3 — 4 of 4 line citations added on this branch resolve wrong; two land on blank lines, and one was invalidated by the commit that wrote it

I extracted every `` `…:NNN` `` citation from the 886 lines this branch adds under `scripts/` and
resolved each against the file it names.

| in | cites | actually resolves to | the real site |
|---|---|---|---|
| `observer_log.py:29` | `:44` (same file) | **blank line** | `:59` |
| `observer_log.py:103` | `check-plan-code.py:1166` | a comment about `explainer-serve.py` having no mutation coverage | `:1223` (tuple) / `:1251` (refusal) |
| `observer_log.py:104` | `:1172-1176` | tail of that same `explainer-serve` comment (or past EOF, read as same-file) | `:1248-1250` |
| `observer_log.py:106` | `check-plan-code.py:1191` | **blank line** | `:1249` |

**The first one is self-inflicted within a single commit.** At `088649a6` and `b360f7cf`, line 44 of
`observer_log.py` really was *"It does not parse. Nothing reads these logs today (measured)…"*. Then
`9c843358` inserted the 13-line r2 H2 paragraph **and the `:44` citation in the same commit**,
pushing the target down to `:59`:

```
$ for c in 088649a6 b360f7cf 9c843358 6367c90f; do git show $c:scripts/observer_log.py | sed -n '44p'; done
088649a6  cites_:44=0   line44=<<It does not parse. Nothing reads these logs today (measured), …>>
b360f7cf  cites_:44=0   line44=<<It does not parse. Nothing reads these logs today (measured), …>>
9c843358  cites_:44=1   line44=<<>>
6367c90f  cites_:44=1   line44=<<>>
```

**Why this is High rather than Low.** Three of the four sit inside the r2 H1 repair, whose subject
is *"a comment asserting a property the code lacks"* — and they cite the wrong code while saying so.
The sentence at `observer_log.py:105-107` reads *"The harness says so itself at `:1172-1176`. A
comment asserting a property the code lacks is the defect `check-plan-code.py:1191` calls this
branch's signature one"* — and `:1191` is a blank line. The claim itself is **true** (I verified the
tuple comparison at `:1223` and the refusal at `:1251`), so no reader is misled about the mechanism;
what fails is every reader's ability to check it, which is the entire function of a citation. This
is also the repo's own standing rule — *cite the SYMBOL, not the line* — violated 4 for 4 in the
commits that were folding a finding about false comments.

**Fix.** Replace all four with symbol references: *"`load_manifests` compares the anchor tuple
(`check-plan-code.py`, `seen_anchors` / the `repeats the edit anchors` refusal)"*, and *"see WHAT
THIS MODULE DOES NOT DO, below"* for the intra-file one. The sibling copy of this same correction at
`check-banner-armed.py:666-670` cites nothing and is correct — it is the model.

---

## Medium

### M1 — the sum comment still states the withdrawn `-5`, contradicting the corrected account 2,900 lines above it, and its arithmetic no longer reaches any literal in the file

`scripts/check-plan-code.py:3506-3509`:

```
# ⟳ 2026-09-23, backlog #166 + #170: 954 -> 964. +15 for the new owner `observer_log.py`
# (14 at first write, +1 from r1 HIGH 4), and -5 for anchors RETIRED WITH THEIR SUBJECT
# when the record grammar moved out of the three producers. Net +10.
```

Against `:578`, rewritten by this very fold:

```
#   ⑴ RETIRED WITH THEIR SUBJECT — 3. …
#   ⑵ RENAMED AND RETARGETED, NOT RETIRED — 2 … ⛔ THEY WERE BRIEFLY IN CLASS ⑴ AND THAT WAS WRONG
```

**`-5` is the pre-withdrawal number.** It counts the two banner entries that r2 established were
*renamed, not retired* — the unearned ratchet fall. The real retirement fall is **3**, so the
arithmetic should read 954 + 15 − 3 = **966**, and 966 is exactly the literal `b360f7cf` installed.
The changelog as it stands runs 954 → 964, then jumps to "966 → 972" with **no entry for the 964 →
966 step** — which is the step where the unearned fall was corrected, i.e. the one change this
branch most insists must be recorded.

```
$ for c in 088649a6 b360f7cf 9c843358 6367c90f; do git show $c -- scripts/check-plan-code.py \
    | grep -E '^[+-].*(954|964|966|972|RETIRED WITH THEIR SUBJECT)'; done
088649a6  + …: 954 -> 964 … -5 for anchors RETIRED WITH THEIR SUBJECT
b360f7cf  - case(… 964)   + case(… 966)          ← literal bumped, comment untouched
9c843358  (nothing)
6367c90f  + ⑴ RETIRED WITH THEIR SUBJECT — 3     ← account rewritten at :578, :3507 untouched
```

**This is r2 B1 exactly, one copy over.** r2 B1 was *"the correction had landed in the COMMIT MESSAGE
and not in the file, and a justification that disagrees with its own pins is not a justification."*
Round 3 landed the correction in the file — in **one** of the two places in that file that state the
number. No gate can see it: `:3517` is derived, so it passes.

**Fix.** Rewrite `:3506-3509` as two changelog entries — `954 → 966` with `+15 −3` and a pointer to
the three classes at `:578`, then the existing `966 → 972`. Do not leave `-5` anywhere.

### M2 — `col()` defeats the EMPTY sentinel for the module's own primary separator, and the case named for the general property tests only the one separator that works

`scripts/observer_log.py:108-110`:

```python
s = "" if v is None else str(v)
flat = s.replace(SEP, " ")
return " ".join(flat.splitlines()) if flat else ""
```

`SEP` becomes a **space** before the emptiness test, and a space is truthy — so `col(v) or EMPTY`
never fires for a tab. Measured:

```
col('\n')   = ''      → session cell '-'     ← the sentinel
col('\t')   = ' '     → session cell ' '     ← NOT the sentinel
col(' ')    = ' '     → session cell ' '
col('\t\t') = '  '    → session cell '  '
record('\t','f',when='T')  = 'v1\tT\t \tf\n'
```

The case at `:263-264` is named for the class and exercises one member of it:

```python
case("a session that is ONLY a separator becomes the sentinel",
     record("\n", "f", when="T").split(SEP)[2], "-")
```

`"\n"` is the separator for which the property holds, and only because `"\n".splitlines()` is `[]`.
For `SEP` itself — the separator this grammar is built on — the property is false. `session` comes
from the Stop hook payload, so `"\t"` or `" "` is reachable input, and the module's stated reason for
`EMPTY` is *"a bare empty column is indistinguishable from a truncated record; a sentinel is not"* —
a space-filled column is equally indistinguishable in a TSV, so the sentinel's purpose is defeated
for exactly the inputs it was written for.

**The suite cannot tell the two implementations apart.** I applied a candidate fix on a copy:

```python
out = " ".join(flat.splitlines()) if flat else ""
return out if out.strip() else ""
```

```
suite under the candidate fix                → 41/41 passed   (control also 41/41)
newline → '-'   TAB → '-'   space → '-'   two tabs → '-'
interior content preserved: col('a\tb') = 'a b'   col(' lead and trail ') = ' lead and trail '
```

Both the delivered code and the fixed code pass 41/41 — which is the proof that no case observes the
property. **Severity argued:** Medium, not High, because nothing reads these logs today, so the cost
is latent; but it is a functional gap in the new module plus a case whose name over-claims what it
tests, and the module exists precisely to make this grammar trustworthy for the reader who does not
exist yet.

**Fix.** The two-line `col` change above, plus a case asserting the sentinel **at two distinct
separators** (`"\t"` and `"\n"`, per the module's own #164 rule), plus a mutation that reverts the
`.strip()` guard and names that case.

### M3 — the `EXAMINED_KEYS` pin was not re-derived after `append_or_raise` was added, and its comment says it was

`scripts/check-fixture-variation.py:287-300` pins six keys for `observer_log.py` and says:

> **DERIVED by running `analyse()` on the final source, not transcribed:** ⚠ an earlier slice
> derived this honestly and then invalidated it with a later edit IN THE SAME COMMIT, so it is
> re-derived after the module is frozen. It reports NO findings — **all six parameters** are
> genuinely varied by the suite.

Running the guard's own `analyse()` on the delivered module:

```
DERIVED keys : ['append.line', 'append.path', 'append_or_raise.line', 'append_or_raise.path',
                'col.v', 'record.fields', 'record.session', 'record.when']     ← 8
PINNED  keys : ['append.line', 'append.path', 'col.v', 'record.fields',
                'record.session', 'record.when']                              ← 6
MATCH        : False
```

The two missing keys belong to **`append_or_raise`** — the function this fold added as its headline
fix. The pin was derived when the module had four functions and not re-derived when the fifth
arrived, which is the failure the comment's own ⚠ describes and then commits.

Nothing catches it because the check is one-directional — `check-fixture-variation.py:978` iterates
`sorted(pinned - keys)` only, so coverage *leaving* is a finding and parameters *arriving* are not.
The live guard is `rc=0`. No coverage is actually missing (`findings = []`; the suite varies `path`
and `line` for both functions), so this is a documentation-and-derivation defect, not a coverage one
— hence Medium.

**Fix.** Add `'append_or_raise.line', 'append_or_raise.path'` to the tuple and change "all six" to
"all eight". Separately worth a backlog note: `EXAMINED_KEYS` cannot see a new parameter, so a pin
that silently under-describes its file is invisible by design — the same asymmetry M1 was about.

### M4 — the two rewired write call sites are exercised but unratcheted, which is the class M1 just closed for the passthrough properties

No manifest entry anchors on either site:

```
$ (per-manifest scan for entries whose anchor mentions append / WARN_LOG / FLUSH_LOG)
check-banner-armed:  0 entries anchored on a write/append
check-ci-watched:    1  (unrelated — "the bounded read gives up without collecting")
check-closing-table: 6  (all pre-existing, none on the delegation)
```

Neutering shows both are reached (`banner 152/160`, `ci` raises `IndexError`), so the cases exist —
but as M1 itself puts it, *"the properties were never uncovered; the RATCHET is what proves the cases
can fail."* The fold applied that reasoning to the passthrough properties it found missing and did
not apply it to the delegation it introduced in the same commit. *After fixing, search for the
class* — the class here is *this fold's own new call sites*.

⚠ **And "ci crashes outright" is weaker evidence than it reads.** The banner site dies through 8
named case failures; the ci site dies through an `IndexError` at `check-ci-watched.py:638`, i.e. a
suite crash with no named case. A manifest entry there could not satisfy `expect` (the harness
requires death *via the case it names*), so adding the ratchet requires adding a case that asserts
the line was written before the entry can exist. That is worth saying in the fold rather than
recording the crash as equivalent.

**Fix.** Add a case to `check-ci-watched` that asserts a WARN wrote its line (there is one at `:626`
— confirm it fails by name rather than by `IndexError`), then one manifest entry per site neutering
the `append_or_raise` call.

---

## Low

### L1 — "979 anchors re-verified" — I measure 980, and no reading of the manifests yields 979

```
entries (mutations)      = 972
sum of edits (anchors)   = 980     ← 8 entries carry 2 edits
unique anchor strings    = 977
unique anchor TUPLES     = 971
```

Commit-message-only, and the underlying property (every anchor resolves exactly once) is **true** —
so nothing is broken. Filed because it is a recalled rather than derived number in the commit whose
thesis is that recalled numbers are the defect, and because the sentence's authority is what made the
wrong check feel sufficient in B1.

### L2 — the M3 withdrawal's stated reason is false in its first half, though its conclusion is right

Commit message: *"#173 quotes no live mutation count: the 964 read in it sits inside the run id
35889056587, and the other 964 in the file is inside the SHA 8b9643d9."*

- Second half **true**: `8b9643d9` contains `964`, in row **#48**.
- First half **false**: `'964' in '35889056587'` is `False`, and row #173 contains no `964` at all
  under any reading. There was nothing in #173 to misread as a live count.

The withdrawal itself is correct (verified above). What is wrong is the invented provenance for the
original mistake — the recorded shape *a retrospective number needs provenance; the CORRECTIONS fail
too*. Commit-message-only; nothing in a tracked file repeats it.

**Fix.** If the withdrawal is restated anywhere durable, say "#173 quotes no live count" and stop
there, rather than explaining a misreading that did not happen that way.

### L3 — the fold made a `KNOWN_UNVARIED` entry stale and left the guard asking for its deletion

```
$ (HEAD tree) python3 scripts/check-fixture-variation.py
  ⭐ check-banner-armed.py: `log_line.reason` now varies — delete it from KNOWN_UNVARIED
fixture variation OK — …                                                        rc=0
$ (master tree) python3 scripts/check-fixture-variation.py
fixture variation OK — …          ← no such line
```

Branch-caused: this fold's rewrite of `check-banner-armed.log_line` means `log_line.reason` is now
varied by the suite, so `KNOWN_UNVARIED['check-banner-armed.py'] = ('log_line.reason',)`
(`check-fixture-variation.py:172-173`) is a debt that has been paid and not recorded. Advisory only
(`rc=0`), which is why it is Low — but it is a ratchet entry that should shrink, and leaving it keeps
a stale exemption alive.

**Fix.** Delete `'log_line.reason'` from `KNOWN_UNVARIED` (and the now-empty tuple's entry if it is
the last one) in this PR.

### L4 — r2 L2 was folded for `check-banner-armed` and not for `check-closing-table`

r2 L2 asked that each adapter pin the literal `"v1"`. Banner now does, at two distinct inputs:

```
scripts/check-banner-armed.py:1345-1346:
     log_line("unarmed", "d", "T", "s").split("\t")[0] == "v1"
     and log_line("stale", "e", "U", "t").split("\t")[0] == "v1")
```

`check-closing-table.py:1359-1361` still asserts only a cell count, exactly as r2 L2 described:

```python
check("log: the record carries a version cell plus FOUR payload fields",
      len(log_line(["a commit"], "2026-09-21T07:00:00-0700", "sess-a", "u")
          .rstrip("\n").split("\t")[1:]), 4)
```

Measured — blanking `VERSION` in `observer_log.py`:

```
check-ci-watched     56/57    (named case)
check-banner-armed  159/160   (named case)
observer_log         39/41    (named case)
check-closing-table  1 FAILED — [FAIL] run: the logged line carries the JUDGED turn's opener id,
                     not the live one: got 'RAISED IndexError' want 'OPENER-OF-THE-JUDGED-TURN'
```

So closing-table does go red, but through an **`IndexError` in an unrelated positional read**, not
through any assertion about the version cell — the *harness launders failures* shape. The property is
owned and correctly killed in `observer_log`'s own suite, so nothing is uncovered; this is Low, and
it is a half-folded carry-over rather than a new defect.

**Fix.** One line in `check-closing-table`: assert `split("\t")[0] == "v1"` at two distinct inputs,
as banner now does.

---

## What I could not finish

- **The full `--mutate .` sweep — NOT RUN, by instruction** (the coordinator has it running). So I
  cannot state survivor counts across the 972 declared entries. Everything I say about mutations
  comes from applying individual edits by hand to an isolated copy with a green control first. ⚠ In
  particular, B1 means a sweep against **HEAD** would refuse the manifest rather than produce a
  tally — if the coordinator's sweep reported a clean tally, check which tree it read.
- **The per-mutation verification of M1's four entries is against the WORKING TREE, not HEAD.** HEAD's
  versions of those four cannot be loaded at all (B1), so "they die through the case they name" is
  established for the in-flight anchors only. Both trees share identical `.py` code for the two
  adapters, so the measurement transfers — but it is not a measurement of the commit.
- **I did not verify "14 at first write, +1 from r1 HIGH 4"** for `observer_log`'s pin. No commit on
  this branch has 15 → the first commit already carries 15, so the 14 is an intra-session state git
  cannot show. **Treat as NOT MEASURED**, not as verified.
- **I measured the locale-default encoding on macOS/Python 3.14.4 only.** I did **not** check the
  ubuntu runner's default, so the docstring's premise ("the platform default IS utf-8 … on the
  ubuntu runner") is untested by me. It does not matter for H1 — the falsifier I built *sets* the
  locale rather than depending on it, and the `-X warn_default_encoding` variant is
  platform-independent — but the premise itself stands unverified.
- **`check-guard-coverage.py`, the schema gates, `test:integration` and `test:e2e` were not run.**
  The first needs Postgres; the rest are outside this branch's subject (no schema, lib, or app
  changes). **Treat as NOT RUN** rather than as clean.
- **Standalone `check-dashboard-entry.py` in the archive copy reported `rc=2` CANNOT RUN** (no
  `.git`). I re-ran it in the repo, where it reports `ok — an entry block was added`. The copy's
  result is an artefact and is discarded.
- **I did not review the 77 added lines of `docs/dashboard-entries.md` or the backlog prose beyond
  rows #170–#174** for accuracy against the code. The r2 half filed B2 against that record; I
  checked only that #170's closure line and #173/#174's numbers are consistent with what I measured.
- **I did not re-audit r2's B2 fix** (the four backlog rows claimed closed). Out of the four findings
  this fold was scoped to, and I ran out of subject before reaching it.

---
---

# ADDENDUM — the same round, reviewing the IN-FLIGHT anchor repair

⛔ **WHY THIS IS A SECTION AND NOT ITS OWN FILE.** It was written as
`docs/reviews/claude/observer-log-fold-r3-claude.md`, which gave round 3 a SECOND subject stem, and
`check-review-rounds.py` then reported **two** round-3s — `observer-log-fold` and
`observer-log-owner` — each missing its codex half:

```
✗ observer-log-fold round 3: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
✗ observer-log-owner round 3: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
```

One stem, one round, one pair of halves. The content is unchanged from the file it replaces; only
its home moved. B1 above flagged this side effect in the same breath as the defect it was reviewing.

**What it covers that the main review could not:** its subject is the coordinator's uncommitted
repair of B1, dispatched mid-review, so it measures the RETARGETED anchors rather than the committed
ones. Both readings are needed — the commit is broken and the repair is sound, and neither sentence
implies the other.

# Adversarial review — `observer-log-owner`, the uncommitted anchor-retarget fold (Claude half)

**Status: COMPLETE.** Verdict **NOT CONVERGED** — 0 Blocking, 1 High, 2 Medium, 1 Low.
Both of the coordinator's claims about the retargeting itself are **CONFIRMED** — I could not
refute either, and the full sweep is clean at 972/972. The findings are in the prose.

## ⚠ Subject correction — this is a DIFFERENT BRANCH, not a correction to r3's subject

The coordinator's message framed this as "a correction to your subject". It is not. Measured:

```
$ git rev-parse --abbrev-ref HEAD ; git rev-parse HEAD
observer-log-owner
6367c90ff75260a468d3022365a025539a881fab

$ git merge-base --is-ancestor 5e4bd163 6367c90f  ->  NO — separate line of work
$ git merge-base 5e4bd163 6367c90f                ->  f6c03fd8   (= origin/master, the shared base)
$ git branch -a | grep -i harness                 ->  (no such branch)
```

`5e4bd163` (`harness-progress-output`) and `6367c90f` (`observer-log-owner`) are **two
independent branches off the same base**, not two states of one. The branch my r3 review was
written against **no longer exists**; the commit is reachable only via reflog. Nothing in this
document supersedes `docs/reviews/claude/harness-progress-r3-claude.md`, and none of its five
findings were "already found" here — they are about a different file's `progress_line` and
`run_suite`, neither of which this fold touches.

**⟳ RESOLVED WHILE THIS REVIEW WAS BEING WRITTEN — no action needed.** I raised that review file
as at-risk because it was untracked in a working tree on a foreign branch, one `git clean` from
gone. It has since been committed and merged:

```
$ git log --oneline --all -- docs/reviews/claude/harness-progress-r3-claude.md
28532810 The mutation harness says where it is — and a guard for the defect its review kept finding (#289)

$ git branch -a --contains 28532810   ->  master, origin/master, + 14 local branches
$ git show 28532810:docs/reviews/claude/harness-progress-r3-claude.md | cmp - <the file>
   IDENTICAL — committed intact, 31,352 bytes
```

Recorded rather than deleted, because the *hazard* was real and the next untracked review will hit
it again: nothing in the process commits a review half, and the branch it describes was deleted
before the file was safe.

## Subject of THIS review

Per the coordinator's instruction: the **working tree**, not `6367c90f`. Verified:

```
$ git status --short
 M scripts/check-plan-code.py
 M scripts/mutations/check-ci-watched.json
 M scripts/mutations/check-closing-table.json
```

Staged copy verified `cmp`-identical to the working tree for all four subject files.

## Controls, proved green FIRST

```
scripts/check-ci-watched.py      rc=0   57/57 self-test cases passed
scripts/check-closing-table.py   rc=0   153/153 passed
```

And the coordinator's refusal claim, **verified independently** rather than taken on trust —
committed tip `6367c90f`, staged via `git archive`, `$HOME` redirected:

```
rc=1
  ✗ check-ci-watched.json: entry 'ci log_line freezes its session column…' repeats the edit anchors of an earlier entry — it measures nothing new
  ✗ check-ci-watched.json: entry 'ci log_line freezes its TIMESTAMP column…' repeats the edit anchors of an earlier entry — it measures nothing new
  ✗ check-closing-table.json: entry 'closing log_line freezes its session column…' repeats the edit anchors of an earlier entry — it measures nothing new
  ✗ check-closing-table.json: entry 'closing log_line freezes its TIMESTAMP column…' repeats the edit anchors of an earlier entry — it measures nothing new
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
```

Exactly four refusals, exactly as described. The claim holds.

### Manifest pre-flight — and a staging error of my own, recorded rather than hidden

My first staging tree copied only the list from a *different* branch's brief and omitted
`.github/workflows`, which `HARNESS_TREE` on this branch requires
(`scripts/check-plan-code.py`'s tuple, kept for `check-ratchet-contract.py`'s reading of
`ci.yml`). The run refused at staging:

```
✗ CANNOT RUN — .github/workflows is missing under ., so the mutation tree would be incomplete
  and every verdict below it an artefact. TREAT THIS AS NOT CHECKED
```

The harness was right and I was wrong — this is the tuple's own recorded failure mode catching a
reviewer. Restaged with all six entries present and verified before re-running.

**What that aborted run does establish**, because `mutate_delivered` runs the manifest drift
checks *before* `stage_tree`: the working tree's manifest passed the duplicate-anchor rule and
reached staging, whereas `6367c90f` never gets that far. And re-running the committed tip on a
**complete** tree reproduces the four refusals byte-identically, so they are a manifest verdict
and not an artefact of my incomplete first tree:

```
rc=1   (same four ✗ lines, same NOT MEASURED)
```

### And the full sweep, over the restaged working tree — CLEAN

```
OK — delivered scripts mutated: 53 file(s), 972 mutation(s), 972 killed,
     972 attributed to the case each names, 0 survivor(s)
```

So the fold does what it set out to do: `6367c90f` returns **NOT MEASURED**, and the amended tree
returns a full coverage verdict with every mutation attributed. That is the strongest available
evidence for claim 1, and it is independent of my per-entry runs above rather than a restatement of
them. ⚠ Scope: see *what I did not measure* — the tree moved again after I staged it.

---

## Coordinator's claim 1 — "all four retargeted mutations are killed by their named cases": **CONFIRMED, and I could not refute it**

I attacked it three ways.

### (a) Anchor uniqueness and location — all four land on the intended line

```
check-ci-watched.py:     'record(session, reason'          -> count=1, line 181
check-ci-watched.py:     'detail, when=when)'              -> count=1, line 181
check-closing-table.py:  'record(session, "+".join(acts)'  -> count=1, line 868
check-closing-table.py:  'turn, when=when)'                -> count=1, line 868
```

`scripts/check-ci-watched.py:181` and `scripts/check-closing-table.py:868` are the intended
`return observer_log.record(...)` lines. No shortened anchor matches a docstring, comment or
second call site — and a second match would be refused anyway by
`scripts/check-plan-code.py:995-1006`, so the residual risk was only *one* match in the *wrong*
place. There is none.

### (b) Attribution under the harness's OWN rule, not a weaker one

I imported `parse_fail_names` from `scripts/check-plan-code.py` and applied the exact predicate
at `scripts/check-plan-code.py:1075` — each `expect` name must equal **exactly one** red case —
specifically so as not to repeat the r2 mistake the coordinator flagged (a verifier accepting
"any named hit"). All six entries on the two lines, including the two pre-existing ones:

| entry | rc | red cases | crash? | attributed |
|---|---|---|---|---|
| ci: drops a PAYLOAD column (pre-existing) | 1 | 4 | no | ✅ |
| ci: freezes its session column | 1 | 8 | no | ✅ |
| ci: freezes its TIMESTAMP column | 1 | **1** | no | ✅ |
| closing: turn id dropped (pre-existing) | 1 | 6 | no | ✅ |
| closing: freezes its session column | 1 | 2 | no | ✅ |
| closing: freezes its TIMESTAMP column | 1 | **1** | no | ✅ |

No `Traceback` in any of the six. The two timestamp entries are *minimal* kills — one red case
each, which is the strongest shape available.

### (c) Killed for the property it NAMES, not incidentally

The coordinator asked specifically about kills for a reason other than the named property. I
evaluated the mutated `log_line` directly, at both of the case's distinct inputs:

```
CONTROL            call1=['v1', 'T1', 's1', 'unwatched', '3 unresolved on aaaaaaaa\n']
                   call2=['v1', 'T2', 's2', 'stale',     '1 unresolved on bbbbbbbb\n']
TIMESTAMP frozen   call1=['v1', 'T',  's1', …]   call2=['v1', 'T',  's2', …]   <- column 2 only
SESSION frozen     call1=['v1', 'T1', 'cw-text', …] call2=['v1','T2','cw-text', …] <- column 3 only
```

Each mutation changes exactly the column its name claims, and collapses it to a constant at two
distinct inputs — so the case cannot pass by accident. `check-closing-table`'s timestamp entry is
even cleaner; its failure line names the value outright:

```
[FAIL] log: the timestamp is the SECOND field, after the version cell, verbatim: got 'T' want '2026-01-02T03:04:05+0000'
```

**I could not refute claim 1.** One thing I checked and cleared: the three `check-closing-table`
mutations print **no tally line**, which looked like an early abort. It is not —
`scripts/check-closing-table.py:1647-1648` returns 1 *before* `print(f"{total}/{total} passed")`,
so the tally is green-only by design. That is also what makes `control_is_green`'s
`"passed" in out` clause correct for this file rather than incidental.

---

## HIGH 1 — the 8-line comment invalidated its own line citations, and 5 more besides. All 7 in-file citations below it are now off by exactly 8.

This is the defect the coordinator predicted, and it is in the fix's own prose — but the
mechanism is worse than "a claim left behind": **the comment broke the citations by existing.**

### The premise

`scripts/check-plan-code.py:759-766` (the added comment), citing two locations:

```python
    # ⚠ **BOTH ANCHOR ON A SUBSTRING, NOT THE WHOLE `return` LINE, AND THE HARNESS IS WHY.** The
    # first draft gave all three entries on that line the IDENTICAL find-string and `--mutate .`
    # REFUSED the manifest — `:1215` computes the anchor tuple from the find-strings alone, so a
    # differing replacement does not distinguish two entries. `:1221-1225` names the escape: a
    # distinct substring per entry.
```

### The measurement

The insertion is 8 lines at working line 759. The file went 3,716 → 3,724 lines. Every in-file
`:NNNN` citation below the insertion point therefore points 8 lines too high. For each, I compared
`committed[N]`, `working[N]` and `working[N+8]`:

```
backtick line-citations in the file: 19
  below the insertion point: 7
  now resolving to the WRONG line (their text moved +8): 7   <- all of them
```

| cited at | citation | committed[N] — what the citation MEANT | now at |
|---|---|---|---|
| **:761** | `:1215` | `nm, anchors = e.get("name"), tuple(f for f, _ in e.get("edits", []))` | **:1223** |
| **:762** | `:1221-1225` | `# ⚠ EXACT TUPLE EQUALITY, SO THE MESSAGE CLAIMS MORE THAN THE TEST DELIVERS — r12 Low.` | **:1229** |
| :202 | `:835` | `# is NOT "does the anchor text mention a doomed function" — the retargeted \`r3 B2\` entry` | :843 |
| :844 | `:1541` | `ok = False` | :1549 |
| :3449 | `:2818` | `"scripts/check-review-recorded.py",` | :2826 |
| :967 | `:1019` | *(see below — already stale)* | — |
| :2220 | `:916-919` | *(see below — already stale)* | — |

The two most damaging are the new comment's **own**: it cites `:1215` for "computes the anchor
tuple from the find-strings alone" and that is precisely what sits at *committed* `:1215` — the
citation was correct when written and is wrong as delivered. At working `:1215` a reader now finds
`seen_names, seen_anchors = set(), set()`; at `:1221` they find a comment about thresholds. The
comment that exists to explain the anchor rule sends its reader to the wrong lines, and the reason
is its own length.

**Two of the seven were already stale and I am not attributing them to this change** —
`:1019` (claimed: "keys the duplicate refusal on the `old` half alone"; committed `:1019` is a
comment about `all`/`any` producers) and `:916-919` (claimed: "a case NAME may contain a colon";
committed `:916` is about the zero-round gate). Those two point at the wrong thing in *both*
numberings. So **5 correct citations were broken by this insertion, and 2 were broken before it.**

### Why this is High and not Low

`docs/dev-process.md` and this file's own conventions treat a stale pointer as a defect because the
next reader follows it. But the sharper point is the **class**: this file cites its own lines 19
times, and *any* insertion invalidates every citation below it. There is no guard —
`check-docs.py` polices documentation integrity, not in-file line self-references. So the cost is
not the two wrong numbers; it is that this will recur on every future insertion, silently, and the
only detector is a human following a pointer.

### Fix

Two options, and I recommend the second:

- **(a)** renumber the 5 broken citations to `N+8` and re-check before committing. Cheap, and wrong
  by next week.
- **(b) stop citing line numbers within the same file.** Cite the **symbol** — `` `seen_anchors`'s
  tuple construction`` and `` the `EXACT TUPLE EQUALITY` note`` — which is the repo's own recorded
  lesson (*"cite the SYMBOL, not the line"*). A symbol survives insertion; a line number cannot.
  A grep-based guard for `:\d{3,4}` in `scripts/*.py` is then possible and would have caught all 7.

---

## MEDIUM 1 — the commit message records a per-anchor verification for a commit whose manifest the harness REFUSED

`6367c90f`'s message states:

> `966->972. 979 anchors re-verified to resolve exactly once AFTER the code was final.`

Measured at that exact commit: `--mutate .` exits **1** and prints **`NOT MEASURED — the mutation
harness produced no coverage verdict. Treat this as NOT CHECKED.`**

To be fair and precise about what is and is not falsified: the sentence is about anchors
*resolving exactly once*, and the refusal is a **different rule** — duplicate anchor *tuples*
between entries. So the narrow claim may well be true, and I did not find a counterexample to it.
What is false is the impression the sentence creates, which is that the manifest was verified at
that commit. **No coverage verdict existed for `6367c90f` at all.** The code was not "final" —
four entries had to be retargeted afterwards.

This matters because of where the sentence lives: a commit message is the durable record, and this
one asserts a verification for a build on which the gate returned NOT CHECKED. The repo's own rule
is that a manual check records the build it was verified against; here the build it names is one
where the check could not complete.

**Fix:** the fold commit should say so explicitly — that `6367c90f` was refused, that the four
anchors were retargeted, and that the verdict quoted below belongs to the amended tree. Do not
amend `6367c90f`'s message silently; the refusal is useful history.

---

## MEDIUM 2 — the two twins guard the same property at different strengths, and `check-ci-watched`'s report cannot tell three distinct mutations apart

### The premise

`scripts/check-ci-watched.py:588-592` — one boolean conjunction covering every column:

```python
    case("log_line carries the version cell plus all FOUR columns it is given, at two distinct inputs each",
         safe(lambda: log_line("unwatched", "3 unresolved on aaaaaaaa", "T1", "s1").split("\t")
     == ["v1", "T1", "s1", "unwatched", "3 unresolved on aaaaaaaa\n"]
     and log_line("stale", "1 unresolved on bbbbbbbb", "T2", "s2").split("\t")
     == ["v1", "T2", "s2", "stale", "1 unresolved on bbbbbbbb\n"]))
```

`scripts/check-closing-table.py:1367-1369` — one case per column, asserting the **value**:

```python
    check("log: the timestamp is the SECOND field, after the version cell, verbatim",
          _safe(lambda: log_line(["a push"], "2026-01-02T03:04:05+0000", "sess-b", "u")
                .split("\t")[1]), "2026-01-02T03:04:05+0000")
```

### The measurement

`check-ci-watched.py` has **no dedicated timestamp case** — grep finds none, and the timestamp
entry consequently names the column-passthrough case instead. Two *different* entries on line 181
therefore name the *same* case:

- `the log line drops a PAYLOAD column, so a record loses a field` → `log_line carries the version cell plus all FOUR columns…`
- `ci log_line freezes its TIMESTAMP column, so the records lose their order` → the same case

and all three mutations of that line produce the **byte-identical** failure line:

```
[FAIL] log_line carries the version cell plus all FOUR columns it is given, at two distinct inputs each: got False want True
```

against the sibling's:

```
[FAIL] log: the timestamp is the SECOND field, after the version cell, verbatim: got 'T' want '2026-01-02T03:04:05+0000'
```

### Why it matters, stated honestly

Attribution is **not** broken — I verified in (c) above that each mutation breaks exactly the
clause it names. This is a weaker claim: *"red via the case it names"* delivers less on the
`check-ci-watched` side, because the case is a conjunction and a conjunction going `False` does not
say which conjunct failed. A reader of the mutation log cannot distinguish "the timestamp froze"
from "a column was dropped", and `check-closing-table`'s own comment at `:1362-1366` records that
an earlier draft of exactly these cases passed `when="T"` at every call site and no case could tell
the parameter from a constant — i.e. this file already paid for the lesson that the twin has not
yet applied.

**Fix:** give `check-ci-watched.py` a per-column case in the shape its sibling already uses —
`got`/`want` carrying the value, one case per column — and repoint the timestamp entry at the
timestamp case. That also removes the two-entries-one-case pairing.

I am flagging this as **transitional rather than structural**: the fold's job was to unrefuse the
manifest, and it did. The asymmetry predates it. But the fold is what made the timestamp entry
exist, so this is the moment it is cheapest to fix.

---

## LOW 1 — the pin comment says "all three entries on that line", which is true per-file but reads as the whole change

`scripts/check-plan-code.py:760` — *"the first draft gave all three entries on that line the
IDENTICAL find-string"*. Measured: there are indeed **3** entries on `check-ci-watched.py:181` and
**3** on `check-closing-table.py:868`, of which **2 per line** were retargeted — the pre-existing
full-line entry was left alone, correctly, since it is the one entry whose anchor *should* be the
whole line.

The comment sits inside the `"scripts/check-ci-watched.py": 29` block, so "that line" is
unambiguous in context. But it then says "Each of the **four** was RE-MEASURED", mixing a
per-file count (3) and a cross-file count (4) in one paragraph, with no statement that the third
entry on each line kept its full-line anchor. A reader reconciling 3 against 4 has to open both
manifests. One clause — *"the third entry on each line keeps the full-line anchor deliberately"* —
removes the ambiguity.

---

## What I did not measure

- **A `--mutate .` over the working tree as it stands NOW.** My full run (below) completed clean,
  but it was staged before two further edits landed: `scripts/observer_log.py`,
  `scripts/check-plan-code.py` and `scripts/mutations/observer_log.json` have all moved since, and
  `git status` now shows five modified files rather than three. The four files this review is about
  — both manifests and both adapters — are still `cmp`-identical to what I measured. The rest of
  the corpus is not, so **the 972/972 below belongs to the tree I staged, not to today's working
  tree.** Someone should re-run it before the fold is committed.
- **The other 966 anchors** individually. The clean sweep is evidence for the commit message's
  "979 anchors re-verified to resolve exactly once"; it is not a per-anchor confirmation of that
  count, and I did not derive the 979.
- **The other 973-odd anchors** in the 33 manifests. I verified the four retargeted ones and the
  two pre-existing ones on the same lines. The commit message's "979 anchors re-verified to resolve
  exactly once" I have neither confirmed nor refuted — the pre-flight accepting the manifest is
  evidence for it, not proof of the count.
- **Whether `observer_log.record`'s own suite covers the version cell** independently of these two
  callers. `scripts/check-banner-armed.py:648,675` has two more `record(...)` call sites; I did not
  check whether they carry the same anchor hazard, and they are outside the stated subject.
- **Anything on `5e4bd163`.** Out of subject here; see the other review file.

---

# Conclusion

**NOT CONVERGED** — but the retargeting itself is sound and I say so without hedging. Both of the
coordinator's claims survived a deliberate attempt to break them: the four anchors are unique,
land on the intended lines, kill via exactly the case each names, break exactly the column each
names at two distinct inputs, and none is killed by a crash. The refusal at `6367c90f` reproduced
exactly as described.

The open items are in the prose, which is where the coordinator predicted they would be. The
sharpest is that the comment explaining the anchor rule **broke its own line citations by being
eight lines long**, along with five others in the same file — a class with no guard, which will
recur on the next insertion. Closing it by citing symbols instead of lines is the fix that lasts.

**One thing needs a human decision, not a finding:** `docs/reviews/claude/harness-progress-r3-claude.md`
is an untracked file, in a working tree, on a branch that is not its own, describing a commit whose
branch has been deleted. One `git clean` ends it.
