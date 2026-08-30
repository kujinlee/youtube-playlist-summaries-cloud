# Round 3 — Claude adversarial review, `feat/dashboard-prose-readability` (PR #178)

**Reviewed:** `7bbabad` (head). Primary scope `git diff df79f0c..7bbabad` (round 2's fixes),
widened to `origin/master..7bbabad` where a fix touches earlier work.
**Reviewer:** Claude half of the dual adversarial pair. The Codex half ran independently and
concurrently; nothing here assumes any of its coverage.

## Verdict: **NOT CONVERGED**

1 High · 3 Medium · 1 Low.

The round-2 fixes to the **write sandbox** hold up. I attacked them with two independent,
control-validated instruments and could not make any of the 47 manifest entries reach a real file
(§ *What I checked and could not fault*). The author's partial refutation of `strong=False` as an
equivalent mutant is also **sound**, and I proved it exhaustively rather than by reading.

The defects are all on the other side of the round — the **prose renderer**. One of them is
**live on the user's dashboard right now**, put there by this branch's own newest entry, and it is
the same symptom round 1 filed and claimed to fix.

---

## Environment and safety

| | |
|---|---|
| `~/explainers/dashboard.html` before | `d2f8a54bb865953ab12d94a11d010c22ecb46c4f5a131312696998cb0f2ad467` |
| `~/explainers/dashboard.html` after `--mutate .` | `d2f8a54bb865953ab12d94a11d010c22ecb46c4f5a131312696998cb0f2ad467` |
| Tracked files written by me | **only this review doc** |

Every mutation in this review was applied to a copy of `scripts/` under
`$SCRATCH/claude-r3-39560/`, never to the repo. No `git stash`, `checkout`, `commit`, `add`.
The clobbering demonstrations all ran under a **fake `HOME`** holding a sentinel page.

The three commands the brief names all pass:

```
python3 scripts/gen-dashboard.py --self-test    → 198/198 passed
python3 scripts/check-plan-code.py --self-test  → 136/136 passed
python3 scripts/check-plan-code.py --mutate .   → OK — 2 file(s), 59 mutation(s), 0 survivor(s)
```

Also green: `check-docs.py`, `check-dashboard-entry.py`, `check-review-rounds.py`,
`check-anchors.py`, `check-explainer-delivery.py`.

⚠ **Not mine, reported because a peer instrument editing tracked files has produced a false
Blocking here twice:** `git status` showed `M docs/reviews/branch-dashboard-prose-r2-claude.md`
throughout my run. I did not write it. A peer also created files
(`levers.py`, `sweep.py`, `verify.py`, `m2_attack.py`) inside the shared scratchpad directory I
first used, which is why I moved to a PID-suffixed one.

---

# Findings

## H1 — a literal `**` is on the reader's live dashboard right now, and this branch's own entry put it there

**REPRODUCED, on the delivered artifact.** `scripts/gen-dashboard.py:137` + `:418` + `:774`.

Read straight off `~/explainers/dashboard.html`:

```html
<p class="title">Round two of the review found something worth telling you plainly:
**the check I added this morning to prove…</p>
```

That is entry `2026-08-29/15` — the entry **round 2 wrote to describe its own fixes**. The
reader sees raw markdown syntax in the headline of a branch whose entire purpose is
*"typeset the prose instead of dumping it"*.

**The mechanism.** The title is truncated **before** it is marked up. `_first_sentence`
(`:136-137`):

```python
    if len(out) > cap:
        out = out[:cap].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"
```

`parse_entries` stores that truncated string as the title (`:418`), and the renderer marks it up
afterwards (`:774`):

```python
                f'<p class="title">{_inline(e["title"])}</p>'
```

With `TITLE_CAP = 110` (`:85`), a `**…**` span that straddles the cap loses its closer. `_inline`
then behaves *exactly as designed* — `:172-174` says unpaired delimiters print as themselves
rather than dropping text — so the opener is printed. The renderer is not wrong; **the truncation
and the scan do not know about each other**, and nothing owns the seam.

Minimal repro, on a scratch copy of the delivered script:

```
title: 'xxx…xxx **bold tail…'                      (input: 95 x's + " **bold tail that is long enough to be cut**")
  ->   xxx…xxx **bold tail…
title: 'xxx…xxx `code tail…'                       (same with backticks)
  ->   xxx…xxx `code tail…
```

Both delimiters are affected, so this is a class, not the `**` instance.

**Why the suite is green at 198/198.** The two cases that could have caught it never meet:

```python
1805: case("the headline is the first SENTENCE, not the first typed line", ...)
1810: case("an over-long headline is cut at a WORD, with an ellipsis",
1811:      (len(_first_sentence("x" * 40 + " " + "y" * 200)) <= TITLE_CAP + 1,
1812:       _first_sentence("x" * 40 + " " + "y" * 200).endswith("…")), (True, True))
```

The truncation case uses **markup-free** filler. And round 1's fix for this same symptom —

```python
1487: _bold_page = _B(parse_entries("## 2026-08-29\n**Correction** to the entry.\nMore.\n"), ...)
1489: case("a headline renders **bold** as emphasis, like the body does",
1490:      ("<strong>Correction</strong>" in _bold_page, "**Correction**" in _bold_page),
1491:      (True, False))
```

— uses a title far **shorter** than the cap. Round 1 fixed *"titles are not marked up"*; the class
it filed (*a literal `**` on the live page*) survived through a second route, and the branch's own
prose walked straight into it. This is the project's recorded shape: **after fixing, search for the
class.** The search here was for the mechanism (`_inline` not wired in), not the property (no
delimiter reaches the page unpaired).

I scanned all 16 parsed entries: **exactly one** is affected today, and it is the round-2 entry.
The 14 other raw delimiters in the emitted page are all inside CSS comments in the `<style>`
block — harmless, and I checked rather than assumed.

**Must fix before merge.** The falsifier is one case: a title longer than `TITLE_CAP` whose
markup straddles the cap must render with no bare `**` and no bare `` ` `` — paired with the
positive that the surviving text is still there.

---

## M1 — round 2's URL cut severs an HTML entity, and on the measure the round used it made the renderer WORSE, not better

**REPRODUCED.** `scripts/gen-dashboard.py:220`.

```python
217:            cut = min((p for p in (url.find("**"), url.find("`")) if p != -1),
218:                      default=-1)
219:            if cut != -1:
220:                url = url[:cut].rstrip(".,;:)]")
```

`_inline_scan` runs on **already-escaped** text (`:170`, its own docstring). `rstrip(".,;:)]")`
therefore strips the `;` that *terminates an HTML entity*:

```
IN   https://x.ee/?a=1&**bold**
OUT  <a href="https://x.ee/?a=1&amp">https://x.ee/?a=1&amp</a>;<strong>bold</strong>
```

The `&amp;` is cut in half. The anchor text and the `href` both carry a bare `&amp`, and a
**semicolon the author never typed** is emitted outside the link. Same for `&quot;`, `&#x27;`,
`&lt;` — every entity `html.escape` produces ends in `;`.

**This is a net regression, measured rather than argued.** Rendering 66,174 inputs through
`_inline` on each tree and comparing the text a browser would show (unescaping each text node
independently, the way a parser does) against the text the author typed:

| tree | inputs whose rendered text ≠ typed text |
|---|---|
| `b520125` (the original three-pass renderer) | 1867 |
| `df79f0c` (**pre-round-2**) | 1862 |
| `7bbabad` (**delivered**) | **1897** |

- **243** inputs are broken by round 2 that `df79f0c` rendered correctly.
- **208** inputs round 2 fixed.

The round's stated aim was to stop the autolinker swallowing markup. It does that — and hands back
more damage than it removes, of a **worse kind**: the pre-existing failures are cosmetic (`**`
inside an `href`), while the new ones insert a character into the reader's text. That collides
with this function's own rule at `:172-174`:

> *Dropping text to make the tags balance would trade a cosmetic defect for content loss.*

Emitting a `;` nobody typed is the same trade in the other direction.

**Not live today** — measured, not assumed. The only `http(s)` tokens in
`docs/dashboard-entries.md` are `http://127.0.0.1:7391/dashboard` (`:87`) and
`https://x.ee/z**bold**` (`:560`), and **both sit inside code spans**, which are literal. I
generated the fragment and confirmed: zero severed entities, zero `</a>;` in the emitted page.

**Note on scope:** a *subset* of this class predates round 2 — `INLINE_URL`'s own final-character
exclusion `[^\s<.,;:)\]]` already refused to end a match on `;`, so a bare URL ending in `&`
severed its entity before this branch touched anything. Round 2 did not create the class; it
**extended it by 243 inputs and moved the total the wrong way** while claiming an improvement. The
fix belongs at the seam: trim on unescaped offsets, or refuse to strip a `;` that closes an
`&…;`.

---

## M2 — the Codex Low was reported with TWO reproductions, fixed for both, and given a falsifier for only one

**REPRODUCED.** `scripts/gen-dashboard.py:217` / `scripts/mutations/gen-dashboard.json` entry 46.

The round-2 Codex review filed the greedy autolinker with two worked cases
(`docs/reviews/branch-dashboard-prose-r2-codex.md`):

```text
IN  https://x.y/z**bold**      →  href swallowed the emphasis
IN  https://x.y/z`code`        →  href swallowed the code span      ← "Same class"
```

The fix handles both — `cut` looks for `**` **and** `` ` ``. The guard handles one. The only new
case (`:1780-1782`) asserts on `https://x.ee/z**bold**`, and the only new manifest entry sets
`cut = -1`, killing both arms at once. Delete just the backtick arm:

```python
            cut = min((p for p in (url.find("**"),) if p != -1),
                      default=-1)
```

```
rc=0   198/198 passed   fails=[]
```

and Codex's second reproduction comes straight back:

```
delivered  <a href="https://x.ee/z">https://x.ee/z</a><code>code</code>
mutant     <a href="https://x.ee/z`code`">https://x.ee/z`code`</a>
```

The fix covered the class; the falsifier covers the instance. That inverts the project's own rule —
*assert the PROPERTY, not the mechanism* — and it is the cheapest finding here to close: one more
tuple element in the existing case.

---

## M3 — two more decisions inside the same twelve new lines have no falsifier, and one of them is justified by a comment that names an outcome nothing tests

**REPRODUCED.** `scripts/gen-dashboard.py:220-221`. Both survive at **198/198**, measured against a
control proved green first.

| mutation | survives? | what comes back |
|---|---|---|
| `url = url[:cut]` — drop the `rstrip` | **198/198** | `https://x.ee/z.**bold**` loses its link entirely: `https://x.ee/z.<strong>bold</strong>` |
| `if url:` — drop the `fullmatch` re-validation | **198/198** | `https://**bold**` gains a bogus link: `<a href="https://">https://</a><strong>bold</strong>` |

The second is the sharper one, because the code comments its own reason (`:215-216`):

> *Re-validate after the cut, because the trim can leave something that is no longer a URL at all
> (`https://`).*

That sentence describes an outcome — a link whose `href` is the bare scheme — and **no case in
the suite can tell whether it happens.** A comment that states a property the suite cannot falsify
is precisely what rounds 1 and 2 kept filing on this branch; it recurred inside round 2's own fix.

**Honest subtraction:** I also tried `INLINE_URL.match(url)` in place of `fullmatch` and it
survives, but I could not construct an input where it differs — after `url[:cut]` the string
contains no whitespace and no `<`, so `match` and `fullmatch` coincide. **That one is an equivalent
mutant and I am not filing it.**

---

## L1 — the manifest retired its only mutation of `main()`'s sandbox wiring, while the declared count grew 41 → 47

**REPRODUCED (both halves).** `scripts/mutations/gen-dashboard.json` entry 39;
`scripts/check-plan-code.py:302`.

Round 2 was right to change the old entry — it was the live hazard. But the replacement keeps the
`with` block:

```json
"        with _write_sandbox() as (_box, _real):\n            return _self_test(real_out=OUT_DEFAULT, sandbox=_box)"
```

so **no manifest entry any longer mutates the wiring at `scripts/gen-dashboard.py:2077-2078`**,
and `--mutate .` — what CI runs — no longer exercises it. The r2 doc claims the H1 case "subsumes
the `main()` wiring coverage entry 39 used to provide". **I verified that claim and it holds**:

| disarm applied to `main()` | result |
|---|---|
| `return _self_test(real_out=OUT_DEFAULT, sandbox=pathlib.Path('/nowhere'))` | `196/198` — red via *the suite never writes to the REAL dashboard path* **and** *…restores the value IN FORCE* |
| sandbox by hand, no `finally`, honest `real_out` | `195/198` — three cases red |
| enter and **exit** the sandbox before the suite runs | `196/198` — two cases red |

So the property is guarded. What is gone is the *mutation*, and `EXPECTED_MUTATIONS`
(`check-plan-code.py:302`) cannot see it, because a **count is not coverage** — it went up while
this subject went uncovered. A safe replacement exists and I ran it: point `OUT_DEFAULT` at a fresh
`mkdtemp` in the mutant before calling `_self_test`, which is red via the same named case and
destroys no sentinel under either instrument below.

Filed **Low**, not higher, because the anchor for entry 39 still quotes the `with` block verbatim,
so deleting it makes `--mutate .` *refuse* with `anchor NOT FOUND` rather than silently pass. That
is a real second line of defence — it just is not the one the count claims.

---

# What I checked and could NOT fault

Stated explicitly, because a silent area reads as unexamined.

**Not one of the 47 manifest entries can reach a real file — two instruments, both control-validated.**
Each entry was applied to a scratch copy under a fake `HOME` holding a sentinel page.

| lever | what it does | control (no mutation) | **instrument control** (old entry 39) | 47 entries |
|---|---|---|---|---|
| **A** (the author's) | append a case that lets `--out` default, `brief-compose` stubbed to write | sentinel intact | ⛔ **sentinel destroyed** | **0 breaches** |
| **C** (mine, stronger) | write **directly through `OUT_DEFAULT`** — breaches whenever the global points at a real file, whether or not any code path reaches the writer | sentinel intact | ⛔ **sentinel destroyed** | **0 breaches** |
| **C + mid-suite probe** | same, plus a second write immediately after the nested-sandbox block (the H1 re-entrancy window) | sentinel intact | ⛔ **sentinel destroyed** | **0 breaches** |

⚠ **One lever must be reported as NOT RUN.** I also tried driving the *real* `brief-compose`
subprocess with no `--out`. It left the sentinel intact **even under the old dangerous entry 39** —
so it cannot detect the breach it was built to detect, and its "0 breaches" is not evidence. I am
recording it as a cannot-run rather than folding it into the total.

**`_write_sandbox`'s docstring promise is now true, and I tested the promise rather than reading it.**
`:976-978` tells the next author that redirecting the DEFAULT means *"a case written later inherits
the sandbox instead of having to remember it."* Levers A and C **are** that later case, and under
the delivered tree both are sandboxed.

**The `strong=False` refutation is SOUND — this is the claim the brief asked me to attack.**
Two independent proofs:

- **Exhaustive execution.** Every string over `{**, *, `, a, space, x, ., https://x.ee/}` up to
  length 5 — **37,448 inputs** — through the delivered scanner and through a mutant whose recursive
  call passes `strong=True`: **0 differences.**
- **Exhaustive search for the premise.** Over every string of length ≤ 6 in `{**, *, a, space}`,
  the number of times `body = s[i+2:close]` contained `**` was **0**. `close = s.find("**", i + 2)`
  is by construction the first such occurrence, so no earlier one can be inside. The flag gates an
  unreachable branch. Correcting the comment instead of inventing a case was the right call.

**L1's `_existed` pairing is real, not vacuous.** Four attacks, all caught red via the named case
*"…and it removes the temp tree it really did create"* at `197/198`:

| attack | delivered result |
|---|---|
| sandbox dir never created (r2 reported this SURVIVED at 193/193) | **caught** |
| …and `_shutil.rmtree` deleted on top (also SURVIVED at 193/193) | **caught** |
| `_shutil.rmtree` deleted alone (control — manifest entry 38) | **caught** |
| `_existed` recorded after the `with` instead of before the raise | **caught** |

**Every sandbox and scanner manifest entry goes red via the case it names.** I ran entries 37–46
individually and compared the red set to each `expect`: **10/10 named-case-red**. Three also turn a
second, closely related case red (39 and 41 both also fail *"…the real path is still what a normal
run would use"*; 40 also fails the empty-span case) — permitted, since `expect` still resolves to
exactly one case name under `run_mutations`' exact-name rule (`check-plan-code.py:1015-1040`).

**Scanner totality, on the DELIVERED code.** The r2 fuzz predated round 2's rewrite of this block,
so I redid it: **156,174 inputs** (all products of length 1–3 over an 18-token delimiter/entity
alphabet, plus 150,000 random strings) through `_inline` —

- **0** crossed or ill-nested outputs;
- **0** losses or duplications of any non-delimiter character;
- **0** `href` breakouts (no `"`, `<`, `>` inside an emitted attribute);
- no exception, no hang, no unbounded recursion.

The `i += len(url)` advance is safe by construction: `url` is always a prefix of `s[i:]`
(`url[:cut]` truncates from the right, `rstrip` truncates further from the right), and `fullmatch`
cannot succeed on an empty string, so the loop always advances.

**Counts and pins are consistent.** `EXPECTED_MUTATIONS` 47 + 12 = 59 matches both manifests and
matches the deliberate ratchet literal at `check-plan-code.py:1520`; `--mutate .` reports 59
mutations, 0 survivors.

**The live page was not touched.** Checksummed immediately before and immediately after
`--mutate .`: identical (`d2f8a54b…`).

---

# Dispositions

| # | Severity | Must fix before merge? |
|---|---|---|
| H1 | High | **Yes.** It is on the reader's page now, this branch put it there, and it is the recurrence of a symptom round 1 recorded as fixed. |
| M1 | Medium | **Yes.** Round 2's fix moved the renderer's own measure the wrong way (1862 → 1897). Not live today, but it is new damage shipped as an improvement. |
| M2 | Medium | Yes — one tuple element. A reported, reproduced defect whose fix is half-unguarded. |
| M3 | Medium | Author's call per item; the `fullmatch` one I would not ship, because its comment asserts an outcome the suite cannot see. |
| L1 | Low | Optional. The property is guarded by cases (verified three ways); only the manifest lost the subject. |

**H1 and M1/M2/M3 are one story.** Every defect this round is in the *prose renderer*, and every
one has the same shape: a decision was made correctly, described accurately in a comment, and left
without anything that could tell if it stopped being true. The write sandbox — the mechanism rounds
1 and 2 spent themselves on — is now the strongest part of this branch, and I could not fault it
with instruments strictly stronger than the ones that certified it.

⚠ The pattern the brief names held for a **third** round: **H1 is live content damage introduced by
round 2's own dashboard entry**, and M1/M2/M3 are all inside round 2's own twelve-line fix. Round 4
is owed on the same standing ground.

---

# Disposition — coordinator, same session

Three inputs this round: this review, `branch-dashboard-prose-r3-codex.md`, and a **re-verification
of round 2's five findings** by the reviewer that filed them (appended to
`branch-dashboard-prose-r2-claude.md`). Every finding was **re-reproduced here** before being acted
on.

| # | Finding | Re-verified how | Disposition |
|---|---|---|---|
| **H1** (C) | A literal `**` on the reader's LIVE page, put there by round 2's own entry. Title truncated BEFORE markup, so a span straddling `TITLE_CAP` loses its closer | REPRODUCED off `~/explainers/dashboard.html` | **FIXED** — `_close_orphan_markup` closes what the cut orphaned. ⚠ Closing, not trimming: the truncated words are shown, so cutting them back would be the content-loss trade this file refuses. Applied ONLY on the truncation path — an author's unpaired delimiter still prints as itself |
| **M1** (C) | The round-2 URL trim severed HTML entities (`&amp;` → `&amp` + a stray `;`), and moved the renderer's own fidelity measure the WRONG way | REPRODUCED; re-ran the measure on three trees | **FIXED** — `_trim_url_tail` is entity-aware. **pre-r2 4157 · delivered-r2 4245 · fixed 3850**, with **0** inputs the r2 version got right broken by this one |
| **M2** (C) | Codex filed the greedy autolinker with TWO repros; the fix covered both, the guard covered one | REPRODUCED — deleting the backtick arm was green | **FIXED** — the case now asserts both arms |
| **M3** (C) | `rstrip` and `fullmatch` both survived; the `fullmatch` comment asserted an outcome nothing could see | REPRODUCED, both survived 198/198 | **FIXED** — a case each. ⚠ The reviewer's own honest subtraction stands: `match` vs `fullmatch` IS an equivalent mutant and was correctly not filed |
| **L1** (C) | After entry 39 was made safe, no manifest entry mutated `main()`'s wiring | REPRODUCED; the reviewer independently confirmed the property is still guarded by cases, three ways | **FIXED** — a new entry mutates the wiring and stays safe by redirecting `OUT_DEFAULT` at a temp file itself |
| **Medium** (X) | `rstrip` drops a closing paren from `https://x.ee/z(foo)**bold**` | **REFUTED as a regression** — I ran the pre-round-2 renderer on Codex's own repro and got **byte-identical** output | **NOT FIXED, and correctly so.** The paren is dropped by `INLINE_URL`'s trailing-character class, which predates this branch and is deliberate: it is what makes `see (https://x.ee/z)` render correctly. Real behaviour, wrong cause |
| **Low** (r2 re-verify) | The sandbox covers the `--out` DEFAULT only; `--fragment-only` and an explicit `--out` with a RELATIVE path escape to the cwd | REPRODUCED by the re-verifier | **FIXED** — the docstring's scope claim is corrected (it was the same over-claim shape that produced H2), and a case reads this suite's own source to require every such path to be absolute |
| **(mine)** | The comment claimed `body == body.strip()` "is the old regex's `\S(?:[^*]*\S)?`". **False** — the old regex also forbade `*` inside the body | Found by differential fuzz, not by reading: **59 of 96,104** inputs differ | **FIXED** — the claim is corrected and the real rule pinned by a case. Behaviour KEPT: the old rule dropped text (587 inputs; `******` → `**`), this one drops none. Store unaffected: 16 entries, 0 differing lines |

## Falsification of the fixes

**8/8 killed, each via the case it names**, control green, sentinel intact:

```
CONTROL: rc=0  206/206 passed  sentinel=True
[KILLED] H1 orphan-closing ×2 (synthetic + REAL store) · M1 entity-aware trim · M2 backtick arm
[KILLED] M3a trim · M3b fullmatch · mine-B the no-* rule · mine-A relative --out
8 killed, 0 survived
```

**No manifest entry can reach a real file — re-swept at 55 entries: 0 breaches**, with the old
dangerous form of entry 39 restored as an instrument control that IS reported as a breach.

⚠ **The gate refused twice during this round, both times correctly.** Two new entries repeated an
earlier entry's edit anchors (*"measures nothing new"*) and were re-pointed at distinct lines; and
the real-store case reported **CANNOT RUN** under `--mutate .`, which copies only `scripts/` — so the
store is genuinely absent there. The skip is now DECLARED and itself asserted, so it can only be
taken in a tree with no `docs/` at all.

Manifest 47 → 55; `EXPECTED_MUTATIONS` and the total pin 59 → 67. 198 → 206 cases.

**Verdict after fixes: NOT RE-REVIEWED.** Round 4 is owed on the standing ground — for the third
round running, the worst finding was introduced by the previous round's fix.
