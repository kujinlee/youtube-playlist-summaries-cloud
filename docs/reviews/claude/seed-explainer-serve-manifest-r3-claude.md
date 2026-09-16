# Round 3 — `seed-explainer-serve-manifest` — Claude half

**Branch `seed-explainer-serve-manifest`, HEAD `5357b5c3`. Tree clean at start and at end; I never
wrote to the repo.** Every mutation below was applied to a copy of `scripts/` living outside the
checkout, proved to reproduce the suite exactly (188/188, and 188/188 under a non-existent `$HOME`),
and restored by `cp` with an md5 check after every single run.

**CONVERGED: NO.** One High, five Medium.

---

## Lead

**Round 2's fixes are sound and its corrections hold — I re-measured the one it corrected twice and
it is now right. The attribution audit is clean: all 36 manifest entries kill, and all 36 kill the
case they name, by an exact plain-`False` match, zero by exception. The coordinator's
pre-commitment is NOT triggered.** The real gate agrees: `check-plan-code.py --mutate .` reports
**679 mutations, 679 killed, 679 attributed, 0 survivors**, and all ten other gates are green.

**What I found is that the suite is still mostly a suite about the file's PURE half.** I wrote 153
mutations across the whole file, 151 applied (2 refused on a non-unique anchor), and **78 survived
at 188/188 — a 73/151 kill rate. Exactly one of the 78 is inside backlog #129's named scope**
(`_send`'s `Content-Length` value); I deliberately did not mutate `start`, `stop`, `detach_streams`
or `main`'s routing at all. So **77 survivors sit outside the filed process layer.**

The sharpest of them is not a coverage statistic. It is the one defect this file's longest docstring
says it exists to prevent, rebuilt one layer below where that docstring is enforced.

---

## H1 — HIGH — `/questions` can record nothing and still answer `{"ok": true}`, at 188/188

**`scripts/explainer-serve.py:1241-1246`. fix-induced: YES** — round 2's M5 added seven cases to
`do_POST`'s *preamble* and none to its *success arm*.

`question_text`'s docstring (`:805-822`) is the longest justification in the file, and its subject is
one sentence:

> Measured that day: a POST with the keys `question`/`section` instead of `doc`/`text` returned
> `{"ok": true}` and appended a block reading "(empty)". **The caller had no way to learn its words
> were gone.** … That is the shape `CLAUDE.md` files hardest against: *"cannot run" is a FAILURE,
> never a pass* — here, in the one channel whose entire job is carrying the user's words back.

Eight cases guard the *empty-question* half of that. **Zero guard the write.** Measured, each alone:

| mutation | verdict |
|---|---|
| `with QUESTIONS.open("a", …): fh.write(…)` → `if False: pass` | **188/188 SURVIVED** |
| `QUESTIONS.open("a", …)` → `QUESTIONS.open("w", …)` (truncates every past question) | **188/188 SURVIVED** |
| `ROOT.mkdir(parents=True, exist_ok=True)` deleted | **188/188 SURVIVED** |
| the success reply's body → `{"ok": False}` | **188/188 SURVIVED** |

**Proved by execution, not by reading.** Under the first, driving the real `do_POST` with
`{"doc": "brief.html", "text": "does the reservation ever release?"}`:

```
reply status : 200
reply body   : {"ok": true, "file": ".../explainers/questions.md"}
questions.md : DOES NOT EXIST — the words are gone
```

That is the 2026-08-17 bug verbatim, with the rejection guard intact above it. The seven preamble
cases all assert *refusals*; nothing asserts that an accepted question is ever written, or written
where the reply says it was. Round 2's own H1 against round 1 was "it cased the reply shape, not the
argument" — this is the same class, one round later, in the function round 2 worked in.

**Fix:** one case. Point `ROOT`/`QUESTIONS` at a sandbox (the `_drive_stale` pattern already does
this correctly), POST a question, and assert the file named in the reply exists and contains the
text — plus a second POST asserting the first entry survives, which is what kills the `"w"` variant.

**Falsifier:** if a case exists that reddens when the `fh.write` line is deleted, this finding is
wrong. I ran the whole suite under that deletion and it reported `188/188 passed`.

---

## M1 — MEDIUM — the seven-case allow-list argument is not wired to the route it defends

**`:1232-1233`. fix-induced: YES** (round 2's H1 built the seven cases).

```
if route == "/regenerate":  →  if route == "/regenerate-disabled":      188/188 SURVIVED
```

Every one of the seven `_regenerate` cases calls `Handler._regenerate(h, payload)` **directly**.
Nothing drives `POST /regenerate` through `do_POST`, so nothing proves the route reaches the handler
those seven cases defend. Under the mutation a real `POST /regenerate` falls into the questions arm
and answers a 400 about a missing `"text"` field.

The security argument itself is fine — the allow-list is genuinely hard (`D10`, a defaulted
`.get(want, "gen-dashboard.py")`, was killed by three cases; `D09`, a `shell=True` f-string, by two).
The gap is that it is cased at the function and not at the wiring.

**Fix:** `_drive_post("/regenerate", b'{"page":"dashboard"}')` with the spy installed, asserting the
recorded argv — one case, reusing both existing drivers.

**Falsifier:** a case that reddens when that route literal is changed.

---

## M2 — MEDIUM — two of round 2's new cases pass for a reason their own names deny

**fix-induced: YES** — both are round 2's M5/M6 cases.

**(a) `:1163-1165` — "an unknown path is a 404, *not an unhandled KeyError on the suffix map*".**
Deleting `".md"` from the content-type map **survived 188/188**. The fixture
(`/yps-no-such-page-2026-09-16.md`) returns 404 at `resolved is None`, one line *above* the map, and
never touches it. The map cannot be reached by an unknown path at all — `SERVABLE` and the map have
the same six keys, so a resolvable file always has an entry. The second half of the name describes a
property the case structurally cannot test.

**(b) `:1227` — "*undecodable bytes* are a 400, not an unhandled `UnicodeDecodeError`".**
`.decode("utf-8")` → `.decode("utf-8", "ignore")` **survived 188/188**. Measured directly:
`b"\xff\xfe".decode("utf-8", "replace")` is `'��'`, and `json.loads` on that raises
`JSONDecodeError` — so the 400 comes from the JSON parser either way. The strict decode the case is
named for is not what makes it pass.

Neither has a manifest entry, so neither is an attribution defect — they are coverage claims that
overstate. **Fix:** (a) rename to what it tests ("an unknown path is a 404") or delete the second
clause; (b) assert the reply *body* distinguishes the two 400s, or drop the clause.

**Falsifier:** apply either mutation and watch the named case redden. Neither does.

---

## M3 — MEDIUM — `/_stale`'s fixture declares ONE source, so every multi-source property is unfalsifiable

**`:1132-1135` and the driver at `:2326-2343`. fix-induced: YES** (round 2's rebuilt `_drive_stale`).

`PAGE_SOURCES` values are **lists**, and the handler takes the **newest** of them. `_drive_stale`
builds exactly one source file, and with one element `max` and `min` agree:

| mutation | verdict |
|---|---|
| `max(…)` → `min(…)` — the oldest source decides, so a stale page reads fresh | **188/188 SURVIVED** |
| `if (REPO / s).is_file()` filter dropped — one missing source makes a real stale page answer `fresh` | **188/188 SURVIVED** |
| `.removesuffix(".html")` dropped from the slug — a `.html` request never matches a source | **188/188 SURVIVED** |

And the documented fail-quiet claim at `:1114` has three clauses —

> An unknown page, an absent source **or an unreadable one** all answer "fresh".

— of which two are cased. `except (OSError, ValueError)` → `except ValueError` **survived 188/188**,
so an unreadable source drops the connection instead of answering. That is the #87/#123 class
arriving at a fourth site, and *enumerate the sentence* is this branch's own round-1 rule.

**Fix:** give `_drive_stale` a `sources=(…)` parameter, declare two with different mtimes (kills
`min`), and one present + one missing (kills the dropped filter). Add a `p=/{slug}.html` case, and
one where the source exists but `stat` raises.

**Falsifier:** a two-source fixture where `max`→`min` reddens a case.

---

## M4 — MEDIUM — the live-reload client is asserted as a STRING and never as a delivery

**`:1167-1168`, and the case block at `:1603-1666`. fix-induced: no.**

Seventeen cases assert what is *inside* `RELOAD_JS`. None assert the server ever sends it:

| mutation | verdict |
|---|---|
| `body += RELOAD_JS.encode()` deleted — live reload is off for every page | **188/188 SURVIVED** |
| the same injection applied to **every** suffix, including `.png` | **188/188 SURVIVED** |

And the shape checks have the weakness the file already diagnosed one screen lower. At `:1657` it
says, correctly:

> COUNT, not presence: `"restoreDetails()"` is a substring of its own definition … so a presence
> check stays green even after the CALL that invokes it is deleted.

That lesson was applied to `saveDetails` and `restoreDetails` and **not carried to `busyTyping`**:

| mutation | verdict |
|---|---|
| `if (rev === mine \|\| busyTyping()) return;` → `if (rev === mine) return;` — reload eats a half-typed question | **188/188 SURVIVED** (the case asserts `"busyTyping" in RELOAD_JS`) |
| `open.indexOf(d.id)` → `open.indexOf(i)` — folds restore by POSITION, the bug the comment names | **188/188 SURVIVED** (the case asserts `"String(i)" not in RELOAD_JS` — the token the *old fix* introduced) |
| `var MISS_LIMIT = 3;` → `1` — the "⛔ NOT 1" decision, with a measured justification | **188/188 SURVIVED** |
| `v.indexOf('stale') === 0` → `!== -1` | **188/188 SURVIVED** |

The fold case is the memory note *assert the PROPERTY, not the mechanism* exactly: a guard naming the
tokens the fix introduced defends only that fix's deletion.

**Fix:** one delivery case — `_drive_get` a real `.html` fixture and assert the body ends with
`RELOAD_JS`, and a `.md` one asserting it does not. For the shape checks, `count("busyTyping()") >= 2`
and `"open.indexOf(d.id)" in _js_code_only(RELOAD_JS)`.

**Falsifier:** any case that reddens when the injection line is deleted.

---

## M5 — MEDIUM — `_send`'s Content-**TYPE** value is unasserted, and it is the half of L11 that was not filed

**`:1067-1074`; the case at `:2415-2426`. fix-induced: no.**

The one case reads `{"content-type", "content-length"} <= {k for k, _ in _sent_headers()}` — key
**presence**. Round 2 filed the `Content-Length` *value* as backlog #129/L11 and stopped there. The
same case, the same line, has a second unasserted value:

| mutation | verdict |
|---|---|
| `send_header("Content-Type", ctype)` → `send_header("Content-Type", "text/plain")` — every page served as plain text | **188/188 SURVIVED** |
| `end_headers()` deleted — the driver stubs it to `lambda: None`, so it can never see this | **188/188 SURVIVED** |

I am **not** re-filing #129. I am reporting that the finding which produced it named one of the two
values in that case and not the other — *after fixing, SEARCH for the class*, inside the round that
cited it.

**Fix:** widen `_sent_headers` to compare the `(key, value)` pair for `content-type`, and have the
stub record that `end_headers` was called. One line each; no bound port needed, so this does not
belong in #129's "needs a new mechanism" bucket.

---

## L1 — LOW — one case asserts the runner's ORDER, not `revision` — measured, red in 9 of 15 shuffles

**`:1568-1599`. fix-induced: no.**

`revision is stable when nothing changes` compares `revision(rev_file)` against a snapshot taken at
construction — and its two neighbours then rewrite `rev_file` twice. It is true only because the
runner happens to call it first.

Measured: I patched the runner to `random.shuffle(cases)` and ran 15 seeds plus a control.
**`revision is stable when nothing changes` was the only red case, and it went red in 9 of 15 seeds.**
No other case is order-dependent — including all of round 2's new `/_stale` and `_regenerate` ones,
which is the brief's question 3 answered in the negative.

The rule this breaks is written **five lines above it** (`:1565-1567`): *"An instrument must not
perturb the fixtures its neighbours assert on."*

⚠ **My first attempt at this measurement silently did nothing** — the patch anchor
(`for name, fn in cases:`) occurs twice, the second inside `_runner_src()`'s own split literal, so the
assertion tripped and twelve "188/188" lines printed from the *unpatched* suite. I caught it because
the patch printed no `SHUFFLED` marker. Recording it because it is this project's own class: a
stand-in weaker than its subject reports a pass over a check that never ran.

**Fix:** give the case its own file, or take the snapshot inside the lambda's own fixture.

---

## L2 — LOW — "refuses the bare root path" does not test the guard it names, and its premise is ambient

**`:278-279`; the case at `:1328`. fix-induced: no.**

```
if not raw:  →  if raw == "\x00IMPOSSIBLE":        188/188 SURVIVED
```

Measured why: with the guard gone, `safe_path("/", root)` still returns `None` — but because
`tempfile.TemporaryDirectory()` produces a name with no suffix, so `SERVABLE` refuses it. The
`if not raw` guard contributes nothing to this case. With a root directory named `looks.html` or
`a.md`, the mutated resolver hands back **the directory itself** as a servable file:

```
plain tempdir       : None      <- what the suite uses
root named 'looks.html': /var/folders/.../looks.html
root named 'a.md'      : /var/folders/.../a.md
```

Same shape as round 2's own S14 — *a case whose premise depends on the ambient world asserts the
world, not the code* — third occurrence on this project. Benign in practice (`mkdtemp` never emits a
dotted name), which is why it is Low and not Medium.

**Fix:** drive the case through a root whose own name carries a servable suffix, or assert the
property directly (`safe_path("", root) is None`).

---

## L3 — LOW — `explainer-serve.safe_href` has no caller; the mutation survives because nothing runs it

**`:319-339`. fix-induced: no.**

```
return page_markup.safe_href(url)  →  return url        188/188 SURVIVED
```

Grepped: the only other mentions of `safe_href` in this file are prose and a case *name*. `md_inline`
delegates to `page_markup.scan`, which calls `page_markup.safe_href` itself (`page_markup.py:185`),
so the three `md: … href is neutered` cases never touch this function.

**This is not a coverage hole — it is dead code**, and I am flagging it so nobody writes a manifest
entry against it later and certifies a claim about a function that is never called. Its 20-line
docstring, with the counted `javascript:` fixtures, reads exactly like the live guard.

**Fix:** delete the wrapper and move the docstring's measured history to `page_markup.safe_href`, or
leave it and mark it explicitly vestigial. **Falsifier:** a caller I failed to find.

---

## L4 — LOW — `…and start() binds THAT constant` is over-broad: two property-preserving refactors redden it

**`:2410`. fix-induced: YES** (round 2's H2 fix).

The brief asks what innocent refactor breaks it and whether it fails loudly. Measured — it fails
**loudly** (a plain `False`, perfectly attributable), but on changes that preserve the property:

| change | still binds `HOST`? | case |
|---|---|---|
| `address = (HOST, PORT)` then `ThreadingHTTPServer(address, Handler)` | yes | **red** |
| `ThreadingHTTPServer` → `HTTPServer`, tuple unchanged | yes | **red** |

It is the right fix for H2 and I am not asking for it to be removed; the note is that a source-shape
case pinned to one spelling will cost a red on an unrelated edit, and the second row above is a
change someone might make for a real reason. **Fix (optional):** assert `"(HOST, PORT)" in
inspect.getsource(start)` — the property is the tuple, not the server class.

---

## L5 — LOW — `index_html`'s page-chrome wiring check is itself unchecked

**`:782` and `:789`. fix-induced: no.**

| mutation | verdict |
|---|---|
| `page_chrome.assert_wired(doc, "explainer-serve index")` → `pass` | **188/188 SURVIVED** |
| `page_chrome.theme_control()` dropped from the chrome div | **188/188 SURVIVED** |

The comment at `:787` says *"this is a page PRODUCER carrying a control, and nothing checked it"* —
the check it then added has the same status. **Fix:** one case asserting `assert_wired` refuses a doc
with the control stripped, i.e. `_raises(lambda: page_chrome.assert_wired(doc.replace(…), …),
AssertionError)`.

---

## The brief's five questions, answered

**1 — a surviving mutation outside the process layer.** 78 of 151, 77 outside backlog #129. Full
inventory below.

**2 — are round 2's 21 new cases honest?** Nineteen of twenty-one are. Two are not, both measured:
the suffix-map clause and the undecodable-bytes clause (**M2**). The seven `_regenerate` allow-list
cases are **honest and strong** — the spy restores `subprocess.run` on the raising path (measured:
forced a `RuntimeError` through it; `subprocess.run is before` → `True`), and the three argv cases
assert the handler's behaviour, not the spy's: a `shell=True` f-string reddens two of them and a
defaulted `.get` reddens three. The four `/_stale` cases genuinely build their world — the vacuity
did **not** move, it was removed; but the world they build is single-source (**M3**). The three
`_raises(...) is False and <assertion>` wrappings are sound as written.

**3 — state leaks and ordering.** No leak in the new drivers. Measured by forcing an exception
through each: `_drive_stale` restores `ROOT`, `REPO` and `PAGE_SOURCES` on the raising path
(`restored=True` on all three); `_drive_regen` restores `subprocess.run`. Ordering: exactly one
order-dependent case, and it is an older one (**L1**).

**4 — the 36 manifest entries.** ⭐ **Clean. No third attribution defect; the pre-commitment does not
fire.** I applied all 36 individually and matched each entry's `expect` against the parsed red set:
**36/36 kill, 36/36 name a case that is red, all 36 by exact plain-`False` match, zero by exception.**
The widest are M14 (12 red, including `serves a plain html name`) and M07 (10 red, six of them dying
by `IndexError`) — coarse, but each still reddens the case it names for the reason it claims.

⚠ My first pass at this check flagged nine entries as mis-attributed. **That was my parser, not the
manifest**: I split red lines on `" — "` to strip exception text, and nine `expect` strings contain
an em-dash themselves. Corrected by matching `== expect` or `startswith(expect + " — ")`. Fourth time
on this project that a stand-in has been weaker than its subject; I am reporting it rather than
quietly re-running, because the wrong version of this paragraph would have fired the pre-commitment.

**5 — the corrected prose (`:2117-2130`).** ⭐ **Re-measured, and round 2's third attempt is
correct.** Applying the manifest's own re-reading mutation:

```
7 red cases
6 carry exception text — all "AssertionError: do_GET read the environment — it must carry, not re-derive"
1 reports a plain False — "driving /src/ never consults the environment — the _Forbidden property, RATCHETABLE"
```

Which is exactly what the paragraph now says: **SEVEN red, six carrying exception text, the seventh
the RATCHETABLE case.** Two corrections failed here; the third holds.

---

## Survivor inventory — 78 of 151 applied (`188/188` each, under the harness's non-existent `$HOME`)

Grouped by where the gap is. Entries in **bold** are written up above.

**`do_POST` / questions (7)** — **the write deleted**; **`"a"` → `"w"`**; `ROOT.mkdir` dropped;
`{"ok": False}`; **the `/regenerate` route literal**; `route` keeps its query string; a missing
`Content-Length` defaults to 1; `rfile.read()` instead of `read(length)`; **`errors="ignore"` decode**.

**`_regenerate` (6)** — one GLOBAL lock instead of per-page (the documented Codex-Medium fix); **no
lock at all**; `REGEN_LOCKS_GUARD` dropped; `capture_output=False`; the 500 drops the stderr tail;
the 504 drops the timeout value; the success body stops naming the page; `REGEN_TIMEOUT` → 1.

**`/_stale` (5)** — **`max`→`min`**; **the `is_file` filter**; **`.removesuffix(".html")`**;
**`except` narrowed to `ValueError`**; the fail-quiet arm answers 404.

**`/_rev` and `/latest` (5)** — `/_rev` 404 → 200 with an empty body; `/_rev` returns the path
instead of the revision; `/latest` 302 → 200; the `Location` header dropped; the empty-state 404 → 200.

**`/src/` (5)** — prefix length off by one; `raw=1` matched anywhere in the URL; always raw, never
rendered; the label stops being relative; `source_shell` renders every file as markdown.

**`do_GET` tail and `_send` (6)** — **the RELOAD_JS injection deleted**; injected into every suffix;
the whole content-type map re-pointed; `.svg` → `text/plain`; **`Content-Type` hardcoded**;
**`end_headers` deleted**; `Content-Length` → `"0"` *(this one is backlog #129 — not re-filed)*; the
index route serves `REPO`.

**`RELOAD_JS` internals (4)** — **`busyTyping()` call**; **fold restore by index**; **`MISS_LIMIT` 3→1**;
the `stale` prefix test.

**markdown / `md_blocks` (10)** — `&`-escaping dropped; `md_cells` stops unescaping; a fence includes
its own opening line; a fence's closing line re-scanned; a single dash becomes `<hr>`; a table no
longer needs its separator row; list nesting baseline hardcoded; paragraph lines joined with no
space; headings stop rendering inline spans; `MD_FENCE` stops matching a language-tagged fence.

**pure helpers (8)** — **`safe_path`'s bare-root guard**; case-sensitive suffix test;
`_js_strip_is_sound` drops the double-quote half; `explainers()` on a missing dir raises;
`is_fragment` matches the word; `DATED` loses its anchor; `latest_target` stops URL-quoting;
`index_html` stops URL-quoting; **`safe_href` (dead code)**.

**instrument / constants (6)** — `_raises` reports True for the WRONG exception type (every refusal
case in the file weakens); `read_pid` stops tolerating a non-numeric pidfile; `pid_alive` stops
probing; `port_busy` inverts; `port_busy` drops its timeout; `MAX_BODY` ×1000; `ROOT` and `QUESTIONS`
relocated; **`assert_wired` and `theme_control` dropped from `index_html`**.

⚠ **`_raises` deserves its own line even though I scored it Low.** Its docstring says *"asserting
that something fails is the only way to prove a guard is not vacuous"* — and `except Exception:
return False` → `return True` survives, which makes every `_raises(fn, _Forbidden)` and
`_raises(fn, AssertionError)` in the file report a refusal when the code raised something else
entirely. It is the memory note *test harness can launder failures*, in the helper written to prevent
it. One case fixes it: `_raises(lambda: 1/0, KeyError) is False`.

---

## Evidence

- Mutation rig: `scripts/` + the three `PAGE_SOURCES` files copied outside the repo; control
  **188/188** and **188/188 under `HOME=/nonexistent-home-r3`** before every batch; the target
  restored and md5-verified after every run. `scripts/explainer-serve.py` is byte-identical to
  `5357b5c3` (`f3fac832…`).
- Verdicts read **only** from the `self-test: N/M passed` line. I never grepped for a FAIL-shaped
  token as a verdict (round 2's S13).
- Gates, all green: `explainer-serve.py --self-test` 188/188 (and under a non-existent `$HOME`);
  `check-plan-code.py --self-test` 128/128; `check-ratchet-contract.py --self-test` 41/41 and bare;
  `check-fixture-variation.py --self-test` 67/67 and bare (530 parameters, 51 files);
  `check-selftest-counts.py` (39 scripts); `check-docs.py`; `gen-backlog-page.py --self-test`
  165/165; `gen-dashboard.py --self-test` 325/325.
- ⭐ `python3 scripts/check-plan-code.py --mutate .` — **46 files, 679 mutations, 679 killed, 679
  attributed to the case each names, 0 survivors**, every control proved green first.
- No port was bound; no process was started or signalled.

## REVIEW GAP: codex — status unknown to this half

A Codex reviewer was reported as running concurrently and writes only to `docs/reviews/codex/`. I did
not read or wait on it. As of this half's completion the only untracked file in the tree is
`docs/reviews/verdicts/seed-explainer-serve-manifest-r3-codex.verdict.json`, which is that run's, not
mine. **Rounds 1 and 2 both recorded `REVIEW GAP: codex`; whether round 3 closes it is the
coordinator's to record, not mine to assume.**

## Q4 / Q5

**Convergence: NOT reached.** One High (a silent success in the one channel whose job is carrying the
user's words back), five Medium, five Low. `fixes_nontrivial` will be true if H1 and M1–M5 are taken.

**Thrashing: NOT armed by this round.** The armed component was `manifest-attribution`, and the
attribution audit came back clean at 36/36 — so the pre-commitment ("a third fix-induced attribution
defect means stop") is **not triggered**. Four of this round's findings are fix-induced, but in
`do_post-write`, `regenerate-routing`, `case-honesty` and `stale-endpoint` — four different
components, none of them `manifest-attribution`, and none of them the same component two rounds
running.

⚠ **The honest caveat on that verdict, stated rather than implied.** H1, M1 and M2 are all the same
*shape* — round 2 cased a function's refusals and not its effect, exactly as round 1 cased a
function's replies and not its argument, which was round 2's own headline against round 1. That is
two consecutive rounds producing the same class of finding about the previous round's fix. It is not
thrashing by the arming condition, because the condition is per-component and these are not one
component. But if round 4 produces a fourth instance of *"the new cases assert the refusal, never the
effect"*, the answer is a rule rather than a fourth repair — and I would rather write that down now
than have round 4 discover it.
