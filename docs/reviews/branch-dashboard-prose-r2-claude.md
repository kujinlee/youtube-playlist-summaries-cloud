# Round 2 — Claude adversarial review, `feat/dashboard-prose-readability` (PR #178)

**Reviewed:** `df79f0c` (head), primary scope `git diff e450f5f..df79f0c`, widened to
`origin/master..df79f0c` where a fix touches earlier work.
**Reviewer:** Claude half of the dual adversarial pair. Codex half ran independently and
concurrently; nothing here assumes any of its coverage.

## Verdict: **NOT CONVERGED**

2 High · 2 Medium · 1 Low.

Both Highs are in the write sandbox — the mechanism this round rebuilt. Neither is in the
mechanism's *behaviour*, which is correct; both are in the **claim** the mechanism makes about
itself. The docstring at `scripts/gen-dashboard.py:969-1001` states two properties in its own
words, and the suite can falsify neither. One of them is false today under a one-line edit; the
other is armed by the manifest entry that this round added to protect it.

The `_inline_scan` rewrite, by contrast, is the strongest part of the round: I could not fault its
behaviour under 229,810 fuzzed inputs (§ *What I could not fault*). Its defects are all
under-guarding, not misbehaviour.

---

## Environment and safety

| | |
|---|---|
| `~/explainers/dashboard.html` before | `da60e10b361dc749505c235cfb0101674eb69b0350d87445338cffccceda8ef5` |
| `~/explainers/dashboard.html` after | `da60e10b361dc749505c235cfb0101674eb69b0350d87445338cffccceda8ef5` |
| Working tree | clean at `df79f0c` before and after every run |

**The live page was not modified by any command in this review, including `--mutate .`.** Every
mutation I ran for my own purposes was applied to a copy under
`$TMPDIR/{custmut,s1,s5,fals,fin,l1,d39b}-*`; no tracked file was written except this review doc.
The live-page-clobbering demonstration in **H2** was run against a **fake `HOME`**, so the file it
destroyed was a sentinel in a temp dir, never the reader's page.

The three commands the brief names all pass:

```
python3 scripts/gen-dashboard.py --self-test     → 193/193 passed
python3 scripts/check-plan-code.py --self-test   → 136/136 passed
python3 scripts/check-plan-code.py --mutate .    → OK — 2 file(s), 53 mutation(s), 0 survivor(s)
```

Also green: `check-docs.py`, `check-dashboard-entry.py`, `check-review-rounds.py`,
`check-anchors.py`, `check-explainer-delivery.py`, and `check-dashboard-entry.py --self-test`
(46/46 + 6/6 cannot-run).

---

# Findings

## H1 — `_write_sandbox` says it captures "the value in force"; nothing can tell that from a hardcoded copy, and the difference leaves the suite's tail pointed at the reader's live page

**REPRODUCED.** `scripts/gen-dashboard.py:1003`.

The docstring's closing sentence (`:1000-1001`):

> `Yields (sandbox_dir, real_out) so the suite asserts against the values in force, never a
> second copy of them.`

The line that is supposed to make that true:

```python
1003:    real_out = OUT_DEFAULT
```

Replace it with a second copy — the literal the suite itself uses — and the suite does not notice:

```python
    real_out = pathlib.Path.home() / "explainers" / "dashboard.html"
```

```
rc: 0
193/193 passed
```

That is not merely an unguarded refactor. It **breaks re-entrancy**, and re-entrancy is what the
nested-sandbox falsifier at `:1978-1985` depends on. With `real_out` hardcoded, the nested
`_write_sandbox()` restores `OUT_DEFAULT` to the *real page* instead of to the outer sandbox, and
every line of `_self_test` after `:1985` then runs unsandboxed. I probed it directly, by printing
`OUT_DEFAULT` immediately after the nested block:

```
PROBE OUT_DEFAULT AFTER NESTED BLOCK: /Users/kujinlee/explainers/dashboard.html
PROBE IS THE REAL PAGE: True
193/193 passed
```

**A green 193/193 while the global points at the reader's live page is exactly the state the
sandbox was built to make impossible**, and it is reached by an edit that reads as a simplification.

Why no case sees it: the only assertion about `real_out` is `:1969-1970`

```python
    case("...and the real path is still what a normal run would use",
         real_out == pathlib.Path.home() / "explainers" / "dashboard.html", True)
```

which is satisfied *by construction* under the mutation. The guard names the mechanism (the path
literal) rather than the property (that `real_out` is whatever was in force at entry). This is the
project's own recorded shape — *Assert the PROPERTY, not the mechanism*.

**A falsifier exists and I verified it discriminates.** Adding one case beside the existing pair:

```python
    case("PROPOSED: the nested sandbox restores the value IN FORCE, not a copy of the real path",
         (_outer == sandbox / "dashboard.html",
          _outer != pathlib.Path.home() / "explainers" / "dashboard.html"), (True, True))
```

| tree | result |
|---|---|
| delivered `df79f0c` | `194/194 passed` |
| + the H1 mutation | `193/194 passed` — red via **exactly** the new case |

Note the shape of the assertion: a positive (`_outer` *is* the outer sandbox path) paired with the
negative (it is *not* the real page). The negative alone would be satisfied by `_outer` being any
third thing.

---

## H2 — manifest entry 39 disarms the sandbox and runs the whole suite against the reader's real page; the docstring simultaneously invites the case that makes it fire

**REPRODUCED — a sentinel "live page" was destroyed.**
`scripts/mutations/gen-dashboard.json`, entry *"the suite runs UNSANDBOXED against the real
dashboard path"*.

The mutation replaces `scripts/gen-dashboard.py:2007-2008`

```python
        with _write_sandbox() as (_box, _real):
            return _self_test(real_out=_real, sandbox=_box)
```

with

```python
        return _self_test(real_out=OUT_DEFAULT, sandbox=pathlib.Path('/nowhere'))
```

`_write_sandbox` never runs, so `OUT_DEFAULT` stays at `pathlib.Path.home() / "explainers" /
"dashboard.html"` — an **absolute path in the real home directory**, unaffected by the fact that
`--mutate .` runs from a temp copy of `scripts/`. For the duration of that mutation, `--mutate .`
executes all 193 cases with the global pointed at the reader's live page.

Today that is harmless by accident: of the four nested `main()` calls in the suite, three pass
`--fragment-only` (`:1809`, `:1845`, `:1854`) and one refuses at `--window 0` (`:1958`), and the
four `main()` calls through the compose path (`:1927-1953`) all pass an explicit `--out`. Nothing
currently lets `--out` default. I confirmed the accident holds — the mutation alone, run under a
fake `HOME`, leaves the sentinel intact.

**But `_write_sandbox`'s docstring tells the next author they need not maintain that accident**
(`:976-978`):

> `Redirecting the DEFAULT — not the four call sites — is what makes it structural: a case written
> later inherits the sandbox instead of having to remember it.`

I took the docstring at its word. I appended one case that lets `--out` default, using the suite's
own existing helpers, and ran it twice under a fake `HOME` with a sentinel file:

```python
    rc, _ = _run_main([], _compose(writes=True, collectors_ok=True))
    case("a later case that lets --out default", rc, 0)
```

```
--- sandbox INTACT:            rc=0  194/194 passed
    live page intact? True     content now: 'SENTINEL-LIVE-PAGE\n'
--- manifest entry 39 applied: rc=1  193/194 passed
    live page intact? False    content now: '<html>'
```

The sandbox works. **The manifest entry that exists to prove the sandbox works is the one thing in
the repo that defeats it** — and `--mutate .` is what CI runs (`docs/dev-process.md:155`). The
incident this whole mechanism was built after (`:971-973`: *"`check-plan-code.py --mutate .`
replaced the reader's live dashboard with an empty page"*) is reproduced above, verbatim, by the
guard for it.

**Fix, verified.** The mutation does not need to disarm the sandbox to fail the case it names —
it only needs `real_out` to disagree with `OUT_DEFAULT`:

```python
        with _write_sandbox() as (_box, _real):
            return _self_test(real_out=OUT_DEFAULT, sandbox=pathlib.Path('/nowhere'))
```

```
safe-39: rc=1  191/193 passed
     red: the suite never writes to the REAL dashboard path        ← the named case
     red: ...and the real path is still what a normal run would use
```

`expect` is the single string `"the suite never writes to the REAL dashboard path"`, which still
resolves to exactly one red case, so this satisfies `run_mutations`' exact-name rule
(`scripts/check-plan-code.py:1015-1040`) as a drop-in.

---

## M1 — code spans are literal *(a real change to a real store line)*, and reverting it is green at 193/193

**REPRODUCED.** `scripts/gen-dashboard.py:193-196`.

The comment states the fix as a fact:

```python
193:                # Code is LITERAL — no markup inside. The old pass ORDER ran the
194:                # autolinker over code content too, so a URL in backticks came
195:                # out as a link nested in a <code>.
196:                out.append(f"<code>{s[i + 1:close]}</code>")
```

This is not hypothetical — it changes what the page shows for a line already in
`docs/dashboard-entries.md`. Making code non-literal again:

```python
                out.append(f"<code>{_inline_scan(s[i + 1:close], strong=True)}</code>")
```

on that store line:

```
MUTANT   : ⚠ Verified in a real browser at <code><a href="http://127.0.0.1:7391/dashboard">http://127.0.0.1:7391/dashboard</a></code> — every link computes to
DELIVERED: ⚠ Verified in a real browser at <code>http://127.0.0.1:7391/dashboard</code> — every link computes to
```

and the suite: **`193/193 passed`.** The round's own stated improvement, on live content, has no
falsifier. A case asserting `_inline("`https://x.example`")` contains no `<a` **and** does contain
`<code>https://x.example</code>` (positive paired with negative) closes it.

---

## M2 — three further `_inline_scan` decisions are asserted in comments and by nothing else

**REPRODUCED.** All three survive at `193/193`, run against a scratch copy of the delivered script.

| `file:line` | the decision the comment claims | mutation that survives |
|---|---|---|
| `:185` | `` `body == body.strip()` is the old regex's `\S(?:[^*]*\S)?`: `** a **` is spacing, not emphasis`` | drop the clause → `if close != -1 and body:` |
| `:186` | `` `strong=False` inside, because emphasis did not nest before and gains nothing by nesting now`` | `_inline_scan(body, strong=True)` |
| `:192` | `` `-1 > i + 1` is False, so an unclosed span needs no separate test`` — the `+ 1` also encodes *an empty span is not a span* | `if close > i:` → ` `` ` emits `<code></code>` and eats both delimiters |

The first is the one that matters most: `:185`'s comment is an explicit **equivalence claim against
the code this round deleted**. A rewrite that says "this reproduces the old regex" and cannot show
it is the shape that lets a silent behaviour change ride along with a refactor. (I separately
measured that no such change happened *today* — see below — but that measurement lives in this
review, not in the suite.)

The third also contradicts the round's own stated principle at `:172-174` (*"Unpaired delimiters
print as themselves… Dropping text to make the tags balance would trade a cosmetic defect for
content loss"*): under `close > i`, two adjacent backticks are silently consumed.

---

## L1 — "…and it removes the temp tree" is an unpaired negative, and is vacuous if the tree never existed

**REPRODUCED.** `scripts/gen-dashboard.py:1984-1985`.

```python
1984:    case("...and it removes the temp tree on that same raising path",
1985:         (_nested is not None and _nested.exists()), False)
```

Nothing asserts the tree ever existed. Make the sandbox directory a unique path that is never
created, and both the case and its manifest mutation go silent:

| mutation | result |
|---|---|
| sandbox dir never exists (unique path) | **SURVIVED** `193/193` |
| …and `_shutil.rmtree(sandbox, …)` at `:1010` deleted on top | **SURVIVED** `193/193` |
| `_shutil.rmtree` deleted alone *(control — manifest entry 38)* | caught `192/193`, red via the named case |

Manifest entry 38 ("the write sandbox leaks its temp tree") therefore catches its mutation only
because the directory happens to exist — a property no case states. The brief's own rule applies
verbatim: *pair every negative assertion with a positive.* Asserting `_during`'s parent exists
inside the body, before the raise, is enough.

---

# What I checked and could NOT fault

Stated explicitly, because a silent area reads as unexamined.

**The scanner is total, on measurement not argument.** 229,810 inputs — all products of length 1–5
over `{**, `, *, a, space, <, &, "}` plus ~140,000 random strings of length 1–10 over a 16-symbol
alphabet including `https://x.ee/`, `>`, `'`, `.`, `)`, `]`, tab — through `_inline`:

- **0** ill-nested or crossed outputs (tags close in the order opened);
- **0** losses or duplications of any non-delimiter character (compared as an ordered sequence
  after stripping tags and unescaping);
- **0** `href` attribute breakouts;
- no exception, no unbounded recursion, no hang.

Recursion is bounded by construction and I checked the argument as well as the measurement:
`body = s[i+2:close]` is strictly shorter than `s`, and the single recursive call passes
`strong=False`, so depth is at most 2.

**The rewrite lost no behaviour the real store depended on.** I re-implemented the three deleted
`re.sub` passes verbatim and diffed old against new across all 15 parsed entries of
`docs/dashboard-entries.md`, over every line of every entry's `plain` text and every title:
**0 differences**. The five raw-line differences a naive whole-file diff shows are all in
`<!--tech-->` blocks, which never reach `_inline` — they are `<pre>{_html.escape(...)}</pre>`
at `scripts/gen-dashboard.py:745-747`. I initially mistook one of those for a rendering defect;
it is not, and I verified by generating a fragment and reading the emitted HTML.

**The 9 new manifest entries are honest.** All 53 mutations go red via the case each names —
`--mutate .` reports 0 survivors, and `run_mutations` enforces **exact case-name equality**, not
substring (`scripts/check-plan-code.py:1015-1040`), refusing an `expect` that matches zero or two
cases. I found no no-op mutation, no `expect` naming an unrelated case, and no duplicate reach:
entries 34 and 40 share one `expect` string but are distinct edits at distinct anchors, and each
`expect` entry still resolves to exactly one red case. `EXPECTED_MUTATIONS` (41 + 12) matches the
manifests, and the `53` literal at `check-plan-code.py:1515` is a deliberate ratchet.

**The `quote` case is not vacuous.** `:1694-1696` pairs a positive (`&quot;` present,
`onmouseover=x` still present) with a count (`_q.count('"') == 2` — only the two `href` delimiters).
Manifest entry 33 (`quote=False`) catches it, and removing the URL branch entirely also turns it
red, so it is genuinely reachable through the autolinker.

**`_well_nested` is not vacuous, and this was tested rather than read.** `_well_nested → return
True` is caught by the companion case at `:1732-1733`; weakening the stack pop to ignore the tag
name is caught by the primary case. Both were mutated, both went red.

**I searched for the class of the L1/L2 defect and found no second instance.** `STORE_DEFAULT` is
the other module global the suite rebinds (`:1836-1861`). It already uses `try/finally` with a
tightly scoped window, and — unlike the old `atexit` handler — its restore **does** have a
falsifier: deleting `:1861` is caught by *"the store label hides the generating machine, and only
that"* at `:1868`. Measured, not assumed.

**Concurrency hygiene.** `mutate_delivered` copies the whole `scripts/` tree into a
`TemporaryDirectory` before touching anything (`scripts/check-plan-code.py:398-400`), and runs a
control both before *and* after the sequence. The working tree was clean at `df79f0c` before and
after my `--mutate .` run, so the instrument did not disturb the concurrent Codex reviewer.

---

# Dispositions

| # | Severity | Must fix before merge? |
|---|---|---|
| H1 | High | **Yes.** Add the verified re-entrancy case; it is two lines and measured to discriminate. |
| H2 | High | **Yes.** One-line manifest change, verified to keep the named case red. This is a live hazard to the user's page on every CI `--mutate .`. |
| M1 | Medium | Yes — it guards a change to live content. |
| M2 | Medium | Author's call per item; `:185` (the equivalence claim) is the one I would not ship unguarded. |
| L1 | Low | Cheap; fold in with H1 since it is the same `finally`. |

**H1 and H2 are one story from two directions.** The round moved the restore out to `main()` so the
window would cover lines not yet written, and documented that promise. H1 shows the promise has no
falsifier; H2 shows the manifest entry guarding it is precisely what breaks it the moment someone
believes the promise. Fixing either alone leaves the other live.

---

# Disposition — coordinator, same session

Both halves **NOT CONVERGED**. Codex: 1 Low. Claude: 2 High + 2 Medium + 1 Low.
**Every finding was re-reproduced by the coordinator before being acted on** — agent output is a
lead, not a finding. The reproduction script and the H2 falsifier are recorded below.

| # | Finding | Re-verified how | Disposition |
|---|---|---|---|
| **H2** (C) | Manifest entry 39 disarmed the sandbox, so `--mutate .` ran 193 cases with `OUT_DEFAULT` on the reader's live page | **REPRODUCED, sentinel DESTROYED.** Under a fake `HOME`, entry 39 + one `--out`-defaulting case → `SENTINEL INTACT=False`; with the sandbox intact → `True` | **FIXED.** The entry never needed to disarm the sandbox to fail the case it names — only to hand the suite a `real_out` that disagrees. Renamed *"the suite is told a real_out that is not the sandbox in force"* |
| **H1** (C) | `real_out = OUT_DEFAULT` had no falsifier; a hardcoded copy is green AND breaks re-entrancy | REPRODUCED — hardcoding survived 193/193, and a probe showed `OUT_DEFAULT` pointing at the real page after the nested block | **FIXED** — case asserts the value IN FORCE, positive paired with negative. It also covers the `main()` wiring that entry 39 used to cover, safely |
| **M1** (C) | Code-literal — a change to a line already in the store — had no falsifier | REPRODUCED, survived 193/193 | **FIXED** |
| **M2** (C) | Three scanner decisions asserted only in comments | 2 of 3 REPRODUCED | **2 FIXED. The third is PARTLY REFUTED** — see below |
| **L1** (C) | The temp-tree case was an unpaired negative, vacuous if the tree never existed | REPRODUCED, survived 193/193 | **FIXED** — records that the tree existed, inside the body, before the raise |
| **Low** (X) | The scanner made the autolinker greedy: `https://x.ee/z**bold**` swallowed the emphasis into the `href` | REPRODUCED | **FIXED** — the URL stops at a delimiter and is re-validated after the cut |

## Partial refutation — M2's second item is an EQUIVALENT MUTANT

The review asks for a falsifier for `strong=False` in the recursive call. **There cannot be one.**
`close = s.find("**", i + 2)` is the *first* `**` after the opener, so `body = s[i+2:close]` can never
*contain* `**` — measured on `**a**b**c**`, `**outer **inner** tail**`, `**a*b**`: body is `'a'`,
`'outer '`, `'a*b'`, none containing `**`. The flag therefore gates a branch the recursive call
cannot reach, and flipping it to `True` changes nothing.

Filing a case would have produced an untestable assertion. The comment claiming the flag was
load-bearing is corrected instead, and now says what is true: it is a fence for anyone who changes
how `close` is chosen, and is not doing work today. The review was right that the claim was
unguarded; it was wrong that a guard was available.

## Falsification of the fixes

**The H2 fix has its own falsifier, and the falsifier was itself controlled.** All **47**
`gen-dashboard.py` manifest entries were applied to scratch copies with an `--out`-defaulting case
appended, under a fake `HOME` holding a sentinel:

```
CONTROL (no mutation, --out defaults): rc=0  sentinel intact=True
47 entries tested. Breaches: 0
```

and, restoring the OLD dangerous form of entry 39 as a control for the instrument:

```
⛔ BREACH — OLD DANGEROUS FORM (control)
47 entries tested. Breaches: 1        harness exit: 1
```

A "0 breaches" from an instrument that cannot detect one is an assertion in better packaging. This
one detects one.

⚠ **`--mutate .` REFUSED once during the fix**, because renaming a case left entry 38's `expect`
naming a case that no longer existed. Same class as round 1's anchor drift, same correct behaviour:
it refused rather than quietly measuring one mutation less.

Manifest 41 → 47 for `gen-dashboard.py`; `EXPECTED_MUTATIONS` and the total pin 53 → 59, same commit.
193 → 198 cases.

**Verdict after fixes: NOT RE-REVIEWED.** A round 3 is owed on the same standing ground — these
fixes were again written by the author of the defects, and this round is the second in a row where
that produced a live hazard (H2 was created by round 1's own fix for M5).

---

# Round 3 verification of the round-2 fixes

**Verified against `7bbabad`** by the same reviewer that filed the round-2 findings, using the
baselines measured in this document. Every mutation below was applied to a **scratch copy** of
`scripts/`; no tracked file was written except this appendix.

| | |
|---|---|
| `~/explainers/dashboard.html` before | `d2f8a54bb865953ab12d94a11d010c22ecb46c4f5a131312696998cb0f2ad467` |
| `~/explainers/dashboard.html` after | `d2f8a54bb865953ab12d94a11d010c22ecb46c4f5a131312696998cb0f2ad467` |
| Working tree | clean at `7bbabad` before and after, including `--mutate .` |

Baseline: `gen-dashboard.py --self-test` **198/198**, `check-plan-code.py --self-test` **136/136**,
`check-plan-code.py --mutate .` **59 mutations, 0 survivors** (47 + 12; `EXPECTED_MUTATIONS`
`scripts/check-plan-code.py:302-305`, total pinned at `:1520`).

## Summary

| Finding | Verdict |
|---|---|
| H1 | **CLOSED** |
| H2 | **CLOSED** — with a narrower residual found (**new L2**, below) |
| M1 | **CLOSED** |
| M2 | **CLOSED** for 2 of 3 items; the third is **WITHDRAWN — the refutation is correct** |
| L1 | **CLOSED** |

None of the five is closed only in appearance. Each was re-run as the *same* mutation that
produced the original finding, and each now goes red **via the case written for it** — not via a
neighbour.

---

## H1 — CLOSED

The round-2 mutation, re-run verbatim against `7bbabad`:

```python
    real_out = pathlib.Path.home() / "explainers" / "dashboard.html"   # was: = OUT_DEFAULT
```

```
[caught] 197/198 passed
     red: ...and it restores the value IN FORCE, not a copy of the real path
```

Red via the new case at `scripts/gen-dashboard.py:2052-2055`, and via nothing else — so the case is
carrying the finding, not sharing it with a sibling. The pairing I asked for is present: the
positive (`_outer == sandbox / "dashboard.html"`) alongside the negative (`_outer` is not the real
page).

**The author's additional claim is also true.** Deleting the `with _write_sandbox()` block in
`main()` (`:2077-2078`) — the shape the old dangerous manifest entry used to cover — is caught:

```
[caught] 196/198 passed
     red: the suite never writes to the REAL dashboard path
     red: ...and it restores the value IN FORCE, not a copy of the real path
```

So the wiring lost no coverage when entry 39 was made safe; it gained a second independent case.

**Re-entrancy confirmed directly**, not just inferred from the mutation. A guarded probe running a
nested `main(["--self-test"])` inside the suite reports:

```
OUT_DEFAULT restored to the value in force: True | == outer sandbox: True
outer: 198/198 passed   live page intact: True
```

*(Incidental, not a defect: the nested run itself reports 197/198, failing "…and the real path is
still what a normal run would use", because in a nested run `real_out` is the outer sandbox rather
than `~/explainers/dashboard.html`. Nobody nests self-tests; the mechanism is re-entrant, which is
what H1 was about. My first probe of this was self-recursive and its `rc=1` was a stack overflow,
not a property of the code — the number above is from the corrected, guarded probe.)*

---

## H2 — CLOSED

Manifest entry 39 is now *"the suite is told a `real_out` that is not the sandbox in force"*, and
keeps `_write_sandbox()` wrapped around the call — it only lies about `real_out`. The sandbox is
never disarmed by any entry.

**The sweep the brief asked for.** All **47** entries in `scripts/mutations/gen-dashboard.json`,
each applied to a fresh scratch copy, each run under a **fake `HOME`** holding a sentinel
`explainers/dashboard.html`, with the `--out`-defaulting case appended:

```python
    rc, _ = _run_main([], _compose(writes=True, collectors_ok=True))
    case("LEVER: a later case that lets --out default", rc, 0)
```

```
control (no mutation, lever present): ok, rc=0
... 47 entries ...
TOTAL BREACHES: 0 []
ANCHOR MISSES: 0 []
```

Every entry went red (`rc=1`), no entry modified the fake home, and — checked separately by hashing
the tree before and after — **no entry wrote into the `scripts/` tree either**. Compare round 2,
where the same experiment on entry 39 turned the sentinel into `<html>`. That breach is gone.

The battery is green on the real tree with the live page unchanged:
`OK — delivered scripts mutated: 2 file(s), 59 mutation(s), 0 survivor(s)`.

### New L2 (Low) — the sandbox covers the `--out` DEFAULT only; a relative path escapes it

**REPRODUCED.** This is *not* a reopening of H2 — the live page is unreachable by it — but it is a
lever the sweep cannot see, and the brief asked me to look for one.

`_write_sandbox` redirects the module global `OUT_DEFAULT`. Two paths bypass that entirely:

| lever | result |
|---|---|
| a case calling `main(["--fragment-only", "dashboard-entries.md"])` | **199/199 passed**, cwd sentinel destroyed |
| a case calling `main(["--out", "dashboard-entries.md"])` | **199/199 passed**, cwd sentinel destroyed |

`--fragment-only` never touches `OUT_DEFAULT` at all — `scripts/gen-dashboard.py:2118` writes
`a.fragment_only` directly. An explicit `--out` overrides the default the sandbox rebinds. In both
cases a **relative** path resolves against the caller's cwd.

Bounding it honestly, because it matters for severity:

- **The live page cannot be reached this way.** `OUT_DEFAULT` is an absolute path under `$HOME`; a
  relative path cannot resolve to it. I confirmed both sentinels independently — the fake home page
  survived both levers.
- **CI is safe.** `run_suite` launches each suite with `cwd=d`, the temp copy
  (`scripts/check-plan-code.py`, `run_suite`), so a relative write under `--mutate .` lands in the
  temp tree. I hashed the `scripts/` tree across all 47 entries and saw no change.
- **The exposure is a hand-run from the repo root** — `python3 scripts/gen-dashboard.py
  --self-test`, which is how a developer and the `regen-dashboard.sh` hook invoke it. A future case
  written with a relative path would write into the working tree at a fully green suite. That is
  the *"an instrument that edits the repo corrupts its peers"* hazard, one layer over from the one
  just fixed.
- **No current case does this.** All three `--fragment-only` cases and all four `--out` cases pass
  absolute temp paths. This is latent, not live — hence Low.

---

## M1 — CLOSED

```python
                out.append(f"<code>{_inline_scan(s[i + 1:close], strong=True)}</code>")
```

```
[caught] 197/198 passed
     red: a URL inside `code` stays literal — code is not marked up
```

Red via the new case at `:1789-1791`, which pairs the positive (`<code>https://x.example/p</code>`
is present) with the negative (`<a ` is not) — so it cannot be satisfied by a scanner that stopped
emitting anything. This is the mutation that reverted `docs/dashboard-entries.md:87` to the old
nested-link rendering at a green 193/193 in round 2.

---

## M2 — 2 of 3 CLOSED; the third item is WITHDRAWN, the refutation is right

| item | mutation | result at `7bbabad` |
|---|---|---|
| the strip clause (`:185`) | drop `body == body.strip()` | **caught** 197/198, red via *"`** a **` is spacing, not emphasis — while `**a**` still is"* (`:1796`) |
| the empty-span rule (`:192`) | `close > i + 1` → `close > i` | **caught** 197/198, red via *"an empty `` is not a code span — the delimiters print"* (`:1802`) |
| `strong=False` in the recursion | `strong=True` | **equivalent mutant — I withdraw the item** |

**I attacked the refutation as instructed, and it survived.** The author's argument is that
`close = s.find("**", i + 2)` returns the *first* `**` at or after `i + 2`, so `body = s[i + 2:close]`
can never contain `**`, so the flag gates a branch the recursive call cannot reach. Rather than
re-reason it, I measured it: both builds run over **173,488 inputs** — every product of length 1–6
over `{**, *, a, space, `, ***}`, ~200,000 random strings over a 15-symbol alphabet, plus
hand-built nesting attempts (`**a **b** c**`, `****a****`, `***a***`, `**a`**`b**`, `*****`,
`**a*b**c**`, …):

```
INPUTS WHERE strong=False vs strong=True DIFFER: 0
```

The refutation is correct and no case is owed. **Going further than the author did:** the *whole*
`strong` parameter is vestigial by the same argument, not just the call-site value. Deleting the
guard outright — `if strong and s.startswith("**", i):` → `if s.startswith("**", i):` — is also
equivalent, over the same corpus:

```
`if strong and ...` -> `if ...`  DIFFERING INPUTS: 0
```

That is an observation, not a finding: dead-but-fenced code with a comment that says so is a
defensible choice, and the rewritten comment at `:183-190` states it plainly instead of claiming
the flag does work. Correcting the claim rather than manufacturing a case for it is the right
disposition — the opposite of the failure mode this round exists to catch.

---

## L1 — CLOSED

The unpaired negative is now paired: `_existed = _nested.exists()` is recorded inside the body
before the raise (`:2039`), and the case asserts `(_existed, …exists())` is `(True, False)` (`:2043`).
Re-running the round-2 mutation that made it vacuous:

| mutation | round 2 (`df79f0c`) | round 3 (`7bbabad`) |
|---|---|---|
| sandbox dir never exists (unique path) | **SURVIVED** 193/193 | **caught** 197/198, red via *"…and it removes the temp tree it really did create"* |
| …and `_shutil.rmtree` deleted on top | **SURVIVED** 193/193 | **caught** 197/198, same case |
| `_shutil.rmtree` deleted alone *(control)* | caught | **caught** 197/198, same case |

Manifest entry 42 (*"the write sandbox never creates the tree it claims to remove"*) encodes the
first row, so the gap is now in the battery rather than only in this document.

---

## The new code in `7bbabad` — checked, not faulted

`7bbabad` also fixes a Codex Low by trimming abutting markup out of an autolinked URL
(`:205-222`), which is new logic written during a review round — historically where this branch's
defects have come from. I re-ran the round-2 totality fuzz against it: **127,624 inputs**, 0
ill-nested outputs, 0 non-delimiter content losses, 0 `href` breakouts, 0 exceptions, no hang. The
trim cannot loop (`cut ≥ 8` because the match begins `http`, and a failed `fullmatch` falls through
to the one-character advance).
