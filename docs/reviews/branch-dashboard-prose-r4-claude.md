# Round 4 adversarial review — PR #178 (Claude half)

**Subject:** `git diff 7bbabad..dee62f2`, prose renderer only, per `r4-brief.md`.
**Head reviewed:** `dee62f2` — materialised with `git archive dee62f2` into a scratch tree, **not**
read from the working tree (see *Instrument note* below; the working tree was being edited by a
concurrent peer during this review).

## VERDICT: NOT CONVERGED

| Severity | Count |
|---|---|
| Blocking | 1 |
| High | 1 |
| Medium | 2 |
| Low | 2 |

**The pattern held for a fourth round.** Round 3's headline fix (`_close_orphan_markup`, written to
stop a literal `**` reaching the reader's page) puts a literal `**` on the reader's page, through a
sibling route. Reproduced end-to-end through the real generator, not at unit level.

**Live page:** `~/explainers/dashboard.html` was `d8891c655150419f27eeabb4cb1fe295f62f3feb2d0f3d2328b01e3c7d772f47`
at the start and at the end of this round. Checksummed 6 times, including before and after every
`--mutate .` run. Every run that could write was executed under a fake `HOME` with a sentinel; the
sentinel is intact. No tracked file was modified by me; this review doc is the only file I created.

---

## Blocking — B1

**`scripts/gen-dashboard.py:156-170` — `_close_orphan_markup` has no notion of a code span, so it
fabricates delimiters inside a title that was already balanced, and prints them on the page.**

`_inline_scan` treats a backtick span as literal — its own comment says so at `:269-270`
("Code is LITERAL — no markup inside"). `_close_orphan_markup` does not know that. It toggles on
`**` wherever it appears, including inside a code span:

```python
        if s.startswith("**", i):
            stack.pop() if stack and stack[-1] == "**" else stack.append("**")
```

On the balanced input `` `a**b` `` the stack goes `["`"]` → `["`","**"]` → `["`","**","`"]` (the
closing backtick does not match top-of-stack, so it is *pushed* rather than popped), and three
closers are appended to a string that needed none.

**REPRODUCED end-to-end** through the delivered generator — a store with one entry, rendered via
`--fragment-only`:

```
$ python3 scripts/gen-dashboard.py --store <tmp>/store.md --fragment-only <tmp>/frag.html --window 14
wrote fragment <tmp>/frag.html
```

Entry text (the kind of sentence this branch's own dashboard entries contain):

> We printed a bare `` `**` `` on the reader page and then spent the whole morning working out which
> of the two scanners was actually responsible for putting it there.

Emitted title:

```html
class="title">We printed a bare <code>**</code> on the reader page and then spent the whole morning
working out which of the two<code>**</code>…</p>
```

The trailing `<code>**</code>` is fabricated. The author opened one code span; the page shows two,
and ends on a `**` nobody typed.

**Both halves of the round's stated claim are false.** The brief records it as: *"no truncated title
ever renders a bare delimiter, and no displayed text is dropped to achieve that."* The first half
fails above. The second half was the wrong invariant to guard — `_close_orphan_markup` cannot drop
text, it can only **add** it, and adding characters to the reader's prose is the exact trade M1 was
filed for in this same round (`:183-192`, the stray `;`).

**It fails the branch's own new case assertion.** Applying the case's own predicate at `:1949-1953`
(strip `strong|code|a` tags, then look for a delimiter) to that input returns `True`; the case
demands `False`. The case does not catch it because its filler is single-delimiter-type —
`"x" * 95 + f" {_delim}bold tail…"` at `:1943` never interleaves `**` with `` ` ``. That is the same
blind-filler shape the round-3 comment at `:1938-1940` correctly identifies for the older `"x" * 40`
case, and then reintroduces one case later.

**Class, not instance.** Grepping the shape rather than the instance, four input families produce a
delimiter on the page that the author did not type:

| typed (padded past the cap) | visible tail after render |
|---|---|
| `` `a**b` `` — balanced code span containing `**` | `…word word**…` |
| ``**a`b**`` — balanced bold containing a backtick | ``…word word`…`` |
| ``**a `b** c` `` — interleaved | ``…word word`…`` |
| `text ** unpaired` — author's own orphan (see M1 below) | `…word word**…` |

Over a 768-input fuzz across `{a, space, **, ` }`, **310 inputs gain visible delimiter characters**
relative to the pre-fix tree. The fix does improve the aggregate (inputs showing a bare delimiter
fall 701 → 555), so it is not a net regression — but it is not the property claimed, and it
manufactures the specific symptom the round was opened to remove.

**Not yet reachable from the committed store, but one entry away.** The real store has 17 entries,
5 with truncated titles, 0 currently tripping this. `docs/dashboard-entries.md` is append-only and
its subject matter is this renderer; the next entry whose first sentence names a delimiter inside
backticks either ships a fabricated `**` to the page or turns the suite red.

---

## High — H1

**`scripts/gen-dashboard.py:2232-2237` — the case "every --out / --fragment-only path in this suite
is ABSOLUTE" cannot see any call site the suite actually has. It is green while the defect it names
is present.**

```python
    _src = _inspect.getsource(_self_test)
    _rel = [m.group(0) for m in
            re.finditer(r'"--(?:out|fragment-only)",\s*"(?!/)[^"]*"', _src)]
```

The regex requires a **string literal** immediately after the flag. Measured against the delivered
source: 5 occurrences of `--out`/`--fragment-only`, and **0** adjacent string literals — absolute or
relative. Every real call site passes `str(<Path>)`:

```
"--fragment-only", str(_frag), "--window", "14"]))
"--fragment-only", str(_f1)]))
"--fragment-only", str(_f2),
"--out") + 1]).write_text("<html>")
"--out", str(_out)]
```

So `_rel == []` holds because the regex is structurally incapable of examining the form the suite
uses, not because the paths are absolute. The second conjunct
(`len(re.findall(r'"--(?:out|fragment-only)"', _src)) > 0`) is the author's anti-vacuity check, and
it only proves the *flags* appear — never that the path regex engaged. A green check over the wrong
subject.

**REPRODUCED, both directions.** I added one line to a scratch copy, in the style every real call
site uses, and ran the suite from a sentinel directory under a fake `HOME`:

```python
    main(["--fragment-only", str(pathlib.Path("frag.html"))])
```

```
$ cd <scratch>/cwdtest && HOME=<fakehome> python3 <scratch>/scripts/gen-dashboard.py --self-test
206/206 passed

--- sentinel BEFORE ---   SENTINEL-DO-NOT-DESTROY
--- sentinel AFTER  ---   <title>Project dashboard</title>
```

The suite stayed **fully green at 206/206** while overwriting the cwd sentinel — which is verbatim
the outcome the docstring at `:1076-1079` says was REPRODUCED in round 3 and that this guard was
written to prevent.

Positive control, so this is not a claim that the guard is dead code — changing that same line to a
bare literal `"frag.html"` does fire it:

```
  [FAIL] every --out / --fragment-only path in this suite is ABSOLUTE
205/206 passed
```

**Why the mutation gate did not catch the vacuity.** The manifest entry *"a case passes a RELATIVE
--out, escaping the sandbox to the cwd"* injects `main(["--out", "relative-escape.html"])` — a
string literal, the one form the guard can see and the one form the suite never uses. The mutation
goes red and certifies the regex against a shape that does not occur, which is precisely how the
gap survived. Assert the property (*the path resolved is absolute*), not the mechanism (*a literal
in the source begins with `/`*) — e.g. wrap `main` for the duration of the suite and assert
`pathlib.Path(arg).is_absolute()` on the value actually passed.

---

## Medium — M1

**`scripts/gen-dashboard.py:149-151` — the comment's scoping claim is false on the truncation path,
which is the only path the function runs on.**

```
        # Only on the TRUNCATION path. A delimiter the AUTHOR left unpaired in a
        # short title still prints as itself — that is `_inline_scan`'s rule and
        # it is about the author's text. These orphans are artefacts of OUR cut.
```

`_close_orphan_markup` receives only the truncated prefix and cannot distinguish an orphan the cut
created from one the author typed. In a title long enough to truncate, an author's deliberate
unpaired `**` gets a closer appended.

**REPRODUCED:**

```
typed    : A title with an unpaired ** delimiter in it that the author typed on purpose and that
           keeps going long enough to be cut by the truncation
rendered : …that the author typed on purpose and that keeps going long enough**…
```

The appended `**` produces no emphasis (the body fails `body == body.strip()` at `:260`, so
`_inline_scan` prints it literally) and adds two characters to the reader's prose for no benefit.
Applying the branch's own case predicate: bare delimiter present → `True`, case demands `False`.

The behaviour is a consequence of B1's root cause; filed separately because it is a **claim**
defect. An equivalence asserted in a comment and never executed is exactly what `:241-251` corrects
elsewhere in this same diff — the file states the rule and then breaks it three functions earlier.

---

## Medium — M2

**`scripts/gen-dashboard.py:177` — `ENTITY_TAIL` misses `&#x27;`, the only numeric entity
`html.escape` actually emits. The M1 defect this round filed and fixed survives verbatim for an
apostrophe.**

```python
ENTITY_TAIL = re.compile(r"&(?:#[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);$")
```

The numeric branch accepts hex *digits* but not the `x` that introduces a hex entity. It therefore
matches `&#39;` (decimal — a form `html.escape` never produces) and fails `&#x27;` (the form it
always produces for `'`). The character class `[0-9a-fA-F]` shows hex was intended; the `x` is
simply missing.

**Complete enumeration of what `_inline` can hand `_trim_url_tail`** — `_inline:222` is
`_html.escape(s)` with `quote` default-true, so the entity set is exactly five:

| escape | `ENTITY_TAIL` matches | verdict |
|---|---|---|
| `&amp;` | True | safe |
| `&lt;` | True | safe |
| `&gt;` | True | safe |
| `&quot;` | True | safe |
| **`&#x27;`** | **False** | **severed** |

**REPRODUCED:**

```
typed   : https://x.ee/?q=it'**bold**
escaped : https://x.ee/?q=it&#x27;**bold**
rendered: <a href="https://x.ee/?q=it&#x27">https://x.ee/?q=it&#x27</a>;<strong>bold</strong>
```

Character-for-character the defect M1 was filed for at `:183-186`: the entity severed, and a `;`
the author never typed pushed outside the link into the reader's prose. The fix covered the
reproduction (`&amp;`) and the named-entity class, and missed the numeric class.

Reachability is as narrow as M1's own — the character must be the last one before a `**`/backtick
cut — so this is Medium, matching the severity M1 was filed at.

---

## Low — L1

**`scripts/gen-dashboard.py:152` — a truncated title can now exceed `TITLE_CAP`, and the length case
at `:1975-1977` uses delimiter-free filler so it cannot see it.**

The closers are appended *after* the cap is applied. Measured against `TITLE_CAP = 110`
(case allows `TITLE_CAP + 1`):

| leading fragment | resulting title length |
|---|---|
| ``**a`b**`` | 113 |
| ``**a `b** c` `` | 113 |
| `` `**`**`**`**` `` | 122 |

The existing case uses `"x" * 40 + " " + "y" * 200` — no delimiters, so no closers, so it can never
observe the overflow. Same blind-filler shape as B1. Cosmetic (layout only), hence Low, but it means
`TITLE_CAP` is no longer a bound.

---

## Low — L2

**`scripts/gen-dashboard.py:1918-1921` — the entity case's three conjuncts are all satisfied with
`_trim_url_tail` removed entirely, and it never asserts a link is produced.**

```python
    _ent = _inline("https://x.ee/?a=1&**bold**")
    case("the URL trim never severs an HTML entity",
         ("&amp;" in _ent, "&amp<" in _ent, "</a>;" in _ent), (True, False, False))
```

**REPRODUCED** by substituting an identity trim:

```
delivered _trim_url_tail -> (True, False, False)  PASS=True   link produced? False
NO TRIM AT ALL           -> (True, False, False)  PASS=True   link produced? False
```

`"&amp;" in _ent` is satisfied by the *escape*, not by the trim. The case distinguishes only the
`rstrip` mutant, and for this input the delivered code produces **no link at all** (the trimmed URL
ends in `;`, which `INLINE_URL` forbids as a final character, so `fullmatch` at `:289` fails) — a
fact the case does not record either way. The project's standard is *pair every negative assertion
with a positive*; the neighbouring M3 case at `:1907-1910` obeys it, this one does not.

The class is not uncovered overall — the `while False:` mutation is caught by the M3 case — so this
is Low, a weak assertion rather than a hole.

---

## Instrument note — a concurrent peer edited the shared working tree mid-review

Not a defect in `dee62f2`; recorded because it produced a **false red on a gate**, and because any
gate another agent runs on this tree right now is untrustworthy.

`git status` was clean at the start of this round. My first `--mutate .` run then reported:

```
✗ mutation 'a truncated headline is not re-balanced, so an orphan delimiter ships':
  anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless
FAILED — delivered scripts mutated: 2 file(s), 66 mutation(s), 0 survivor(s)
```

`git status` immediately afterwards showed ` M scripts/gen-dashboard.py`, and the diff is not a
mutation artefact — it is a **peer's in-flight rewrite** of the very function under review:
`_close_orphan_markup` re-signatured to `(cut, full)`, a new `_orphaned_delimiters` helper, and new
`io`/`tokenize` imports. The anchor was missing because the file had been rewritten, not because
the manifest is wrong.

**Re-measured alone, against a pristine `git archive dee62f2` tree:**

```
$ python3 scripts/check-plan-code.py --self-test
136/136 passed
$ python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 2 file(s), 67 mutation(s), 0 survivor(s)
```

67 mutations, 0 survivors, exactly as the brief predicts. **Treat the 66-mutation FAILED result as
NOT RUN.** Every finding above was reproduced against a copy byte-identical to `dee62f2` (verified
by `diff` against `git show dee62f2:scripts/gen-dashboard.py`).

Two side observations the peer's edit implies: the round-3 fixes are being changed while under
review, so this review describes `dee62f2` and not whatever lands next; and the peer's direction
(passing the full pre-cut string so an author's orphan can be told from the cut's) is aimed at M1
above, but does not by itself address B1, whose cause is code-span blindness rather than missing
context.

---

## What I attacked and could not fault

Stated explicitly so no area here reads as merely unexamined.

- **The 8 new manifest entries.** All 8 apply and are caught, on a pristine tree, at 67/0. The
  runner enforces that each `expect` names **exactly one** red case (`check-plan-code.py:549`), so
  none can be satisfied by an unrelated failure. I found no equivalent mutant among them. The one
  criticism I have is not of the entry but of what it certifies — see H1.
- **`_trim_url_tail` termination.** `:194-197` either strictly shortens `url` or breaks; it cannot
  loop. No input reaches it that does not terminate.
- **`_trim_url_tail` stripping too little.** Tested the adversarial shapes: `&amp;;` (author's own
  `;` after an entity) correctly strips one `;` and stops at the entity; `...amp;` with no `&` is
  correctly stripped; `&amp;.` strips the `.` then stops. `&amp;`/`&lt;`/`&gt;`/`&quot;` are all
  preserved. Only the `&#x27;` gap in M2 stands.
- **The "0 regressions" claim in the docstring at `:188-192`.** Held. Over a 3,744-input corpus of
  URL-tail × delimiter × surrounding-text combinations, the set of inputs the delivered-r2 `rstrip`
  rendered faithfully and the r3 version breaks is **empty**. I could not reproduce the author's
  absolute counts (my fidelity metric counts emphasis rendering as a difference, so my three
  variants tie at 1664/3744) — but the *direction* claim, which is the load-bearing one, survives.
- **The declared-skip case at `:1969-1971`.** Not vacuous, contra the brief's suspicion. It fails if
  `docs/` exists while the store file does not, so it is not a skip that only guards itself. It is
  weak only against deleting `docs/` wholesale, which is what the `--mutate` temp tree legitimately
  does.
- **The real-store case at `:1963-1966`.** Not vacuous. `bool(_store_titles)` is `True` today
  (5 truncated titles of 17 entries), so it cannot pass on an empty set. It just does not catch B1
  yet, because no committed entry has that shape.
- **The `strong=False` equivalent-mutant argument at `:253-259`.** Traced and correct. `close` is
  the first `**` at or after `i + 2`, so `body` cannot contain `**`, so the flag gates an
  unreachable branch. The comment's refusal to claim it is doing work is right.
- **The write sandbox itself** (out of scope except at the three named points) and the live page.
  `~/explainers/dashboard.html` is byte-identical to its round-start checksum after every run,
  including two full `--mutate .` runs and a suite run that deliberately wrote to a relative path.

## What would make this converge

B1 and H1 are the two that matter. B1 needs `_close_orphan_markup` to share `_inline_scan`'s notion
of what a span is — the two scanners disagreeing is the defect, and a third scanner would be more of
the same cause. H1 needs the guard to observe the path `main` actually receives rather than the
source text that spells it.

---

# Disposition — coordinator, same session

Both halves **NOT CONVERGED**. Codex: 1 Blocking + 1 High + 1 Medium. Claude: 1 Blocking + 1 High +
2 Medium + 2 Low. **The two halves independently found the same Blocking** (`_close_orphan_markup`
blind to code spans) and the same entity gap — the first time in four rounds that both reviewers
converged on one root cause. Every finding re-reproduced by the coordinator before action.

| # | Finding | Re-verified how | Disposition |
|---|---|---|---|
| **B1** (C+X) | `_close_orphan_markup` was a SECOND scanner; it counted `**` inside a code span as bold, fabricating a delimiter the author never typed | REPRODUCED both halves' inputs | **FIXED STRUCTURALLY.** There is now ONE implementation: candidate closers are judged by running the shipping renderer. A third scanner would have been more of the same cause |
| **H1** (C) | The absolute-path guard read SOURCE TEXT for a literal after the flag — the suite has 5 flags and **0** adjacent literals, so it was green because it could not look | REPRODUCED: `str(pathlib.Path("frag.html"))` destroyed a cwd sentinel at a green 206/206 | **FIXED** — replaced by a recording proxy over `main`, asserting on the value actually PASSED. The source-scanning version is deleted, not kept alongside |
| **H(X)/M2(C)** | `ENTITY_TAIL` missed `&#x27;` — the only numeric entity `html.escape` emits | REPRODUCED | **FIXED** — `#[xX]?` |
| **M1** (C) | The comment claimed the closer runs only on the truncation path and cannot touch an author's own orphan | REPRODUCED on `dee62f2` | **ALREADY FIXED by the B1 rewrite** — `full` is the baseline, so an author's unpaired delimiter is preserved. Re-verified against the reviewer's own input |
| **M(X)** | The path guard saw only double-quoted literals | REPRODUCED | **SUPERSEDED** — the whole source-scanning mechanism is gone. ⚠ The battery showed narrowing the regex alone was an **equivalent mutant** on today's suite; recorded rather than papered over |
| **L1** (C) | Closers were appended AFTER the cap, so `TITLE_CAP` stopped being a bound | REPRODUCED: 148 of 60,000 inputs, max 113 | **FIXED** — the closers live inside the cap; a word is dropped when nothing fits. Re-fuzzed: 0 of 60,000 exceed |
| **L2** (C) | The entity case's three conjuncts all pass with the trim removed | REPRODUCED | **FIXED** — asserts the rendered text equals the typed text. ⚠ It still does not distinguish "no trim at all"; that is covered by the neighbouring case and is now **stated** rather than implied |

## ⚠ Two process failures of mine, recorded because they cost real work

**1. I edited the working tree while a reviewer was reading it.** In round 2 I explicitly held edits
for this reason; in round 4 I started fixing Codex's findings immediately and the Claude half hit a
**false red** (`66 mutations, anchor NOT FOUND`) caused by my in-flight rewrite. It recovered by
re-measuring against a pristine `git archive dee62f2` tree and correctly labelled the first result
**NOT RUN** — but it should not have had to. The rule that already exists for peer agents applies to
the coordinator too.

**2. My first cap case repeated the exact mistake the reviewer had just named.** I wrote
`"**a`b** " + "word " * 40` — delimiters in the LEAD, so the cut lands in plain words, no closer is
produced, and the mutation **SURVIVED at 208/208**. The blind-filler shape was described to me in
writing, in the same review, about the case one line above. The passing input is now taken from the
fuzz that found the defect rather than invented.

## Falsification of the fixes

Battery on scratch copies, control green, sentinel intact: the second scanner restored **verbatim**,
`ENTITY_TAIL` reverted, the cap check dropped, the recorder silenced, and a relative path passed as
`str(Path(...))` — **all killed via the case each names**.

`--mutate .` **73 mutations, 0 survivors**; **61/61** manifest entries proved unable to reach a real
file. The anchor ratchet refused **three times** during this round as my edits moved lines it quotes,
and once for an entry whose subject I had deleted — that one was retired rather than re-pointed at
something it never measured.

Manifest 59 → 61 (one retired, three added); pins 71 → 73. 208 → 209 cases.

**Verdict after fixes: NOT RE-REVIEWED.** Round 5 would be the fifth on the same standing ground.
`docs/dev-process.md` fires **Phase 6** — an architecture review — on four non-converging rounds, and
that trigger is now met by the count as well as by the pattern.
