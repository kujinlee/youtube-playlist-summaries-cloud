# emphasis-baseline r2 — Claude adversarial half

**Subject:** the **FOLD**, not the original change — `git diff 22baf584..HEAD` on branch
`explainer-emphasis-baseline` (PR #363). Round 1's fixes are the unreviewed code
`check-review-recorded` refused the PR over.
**HEAD at start:** `72df637bb99620c3d018023f32ad8607aa0e9360`
**HEAD at end:** `72df637bb99620c3d018023f32ad8607aa0e9360` — unchanged, the round stands.

**Isolation.** No git mutation was performed. Every mutation below was applied to a
`git archive HEAD` extract under the scratchpad, never the live tree; a Codex reviewer is
concurrent. `git status --short` was empty at start and at end.

---

## Summary verdict in one line

**The Blocking round 1 found is genuinely closed at the call site it names — I severed it and the
named case reddens.** But the suite still reports a full green while the server writes **nothing
to the wire on every response**, because the new driver stubs out `_send`, which is the verb its
own case name uses. Round 1 handed the author the strictly stronger driver, in runnable form, and
said in terms that the stub version *"structurally cannot"* make that check. The fold took the
weaker one and did not say so.

---

## High 1 — the untested layer moved one frame out, into the verb the new case is named for · Structural

**Premise — the case name and the docstring.** `scripts/explainer-serve.py:1709`:

```python
case("do_GET SENDS the decorated body — the shipped call, not just decorate_html",
     lambda: _served.get("code") == 200 and b"/_rev?p=" in _served.get("body", b""))
```

and `scripts/explainer-serve.py:1124-1125`:

> `do_GET` is now driven by a real case below, **so the call site is covered and not merely
> confessed.**

And the driver that backs both, `scripts/explainer-serve.py:1701`:

```python
h._send = lambda c, b, t: got.update(code=c, body=b, ctype=t)  # type: ignore[method-assign]
```

**`_send` is the only thing in this file that touches the wire** (`:1139-1146`): `send_response`,
`send_header("Content-Type")`, `send_header("Content-Length", str(len(body)))`, `end_headers`,
`self.wfile.write(body)`. The new case replaces that whole function with a dict update. Nothing
is sent.

**Measurement A — three severances inside `_send`, each on its own fresh copy of `HEAD`, control
`206/206` green first:**

```
########## control (unmutated HEAD copy) ##########
self-test: 206/206 passed
########## M2  self.wfile.write(body)  ->  pass ##########
self-test: 206/206 passed
########## M3  Content-Length: str(len(body))  ->  "0" ##########
self-test: 206/206 passed
########## M4  send_response(code)  ->  send_response(200) ##########
self-test: 206/206 passed
```

**M2 is the one that matters: the server writes an empty body to every response, for every route,
and the suite is fully green at 206/206.** That is the same shape as the Blocking — "the suite
passes with the shipped behaviour severed" — one stack frame further out, and it survives the fix
for it.

**Measurement B — the manifest does not reach there either.** Querying all 47 entries for any
edit touching `_send`, `wfile` or `Content-Length`:

```
['a CORS header is emitted, so any origin can read private source',
 'a regenerate TIMEOUT is reported as a successful rebuild']
```

Both are about *headers*, via `_sent_headers_for` (`:2648-2656`), which drives the real `_send`
but stubs `wfile.write` to a no-op and only asserts header **presence**
(`{"content-type","content-length"} <= keys`, `:2661`), never a value. That is why M3 survives a
falsified `Content-Length` and M2 survives no write at all. **No case in the suite exercises the
body write.**

**Measurement C — this is NOT a regression. It is pre-existing, and that is the point.** Same
severance against a pristine `master` extract:

```
=== master control ===                         self-test: 202/202 passed
=== master with wfile.write severed ===        self-test: 202/202 passed
```

So the fold did not break anything. What the fold did was write a case named **SENDS** and a
docstring saying the thing is **covered**, over a layer that is still entirely unmeasured.

**Measurement D — the stronger driver was already written, in round 1, and catches both.** This is
round 1 Claude's Measurement B driver verbatim (`BytesIO` on `wfile`, real `_send`, real
`send_response`), run against the **post-fold** tree:

```
########## HEAD (control) ##########
  wire body carries the reload client : True
  wire body carries the page's bytes  : True
  Content-Length header               : [b'Content-Length: 8356']
  header matches actual bytes written : True
########## M2: wfile.write severed ##########
  wire body carries the reload client : False      <-- CAUGHT
  wire body carries the page's bytes  : False      <-- CAUGHT
  Content-Length header               : [b'Content-Length: 8356']
  header matches actual bytes written : False      <-- CAUGHT
########## M3: Content-Length falsified ##########
  wire body carries the reload client : True
  wire body carries the page's bytes  : True
  Content-Length header               : [b'Content-Length: 0']
  header matches actual bytes written : False      <-- CAUGHT
```

It is strictly stronger: it also still kills M1 (the call-site sever), because `/_rev?p=` reaching
the wire implies `decorate_html` was called. It is a drop-in replacement, about six extra lines of
handler attribute setup, and round 1 said so explicitly:

> It stubs `_send` […] so a `Content-Length` or header regression is invisible to it. […] My
> `BytesIO` variant on `wfile` goes through the real `_send` and does catch that — **it is the
> strictly stronger driver, and the fourth check in Measurement B is the one `_drive_src`
> structurally cannot make.**
> — `docs/reviews/claude/emphasis-baseline-r1-claude.md`, Blocking 1, Measurement D

The fold adopted `_drive_src`'s pattern — the one round 1 named as the weaker of the two — and the
commit message, the docstring and the PR body all present the result as closure.

**Why High and not Blocking.** Nothing regressed: served bytes are byte-identical to `master`
(measured, Verified sound below), and the call site the Blocking named *is* covered. It is not
Medium either, because (a) it is the identical defect class the round was convened to close,
reproduced at the next frame, which is exactly ADR-0014's prediction and round 1's stated lesson;
(b) the fix was delivered to the author as runnable code and silently not taken, with no sentence
saying which driver was chosen or why; and (c) the case's own name asserts the property it
removes.

**Proposed fix.** Replace the `_send` stub in `_drive_page` with `h.wfile = io.BytesIO()` plus the
four base-class attributes, parse the raw bytes, and assert (i) the reload client is on the wire,
(ii) the page's bytes are on the wire, (iii) `Content-Length` equals `len(body actually written)`.
Then add a manifest entry severing `self.wfile.write(body)` whose `expect` names it. If the
stronger driver is rejected, the minimum is to rename the case away from **SENDS** and amend
`:1124-1125` to say *the call is covered; `_send` is not*.

---

## Medium 2 — two comments in this file say the server decorates every HTML page; two of its three `text/html` exits get nothing · Structural

**Premise — the new line, added by the fold.** `scripts/explainer-serve.py:1116`:

> `"""Everything the server appends to an HTML page at send time.`

**Premise — the pre-existing line it rhymes with**, untouched by this branch,
`scripts/explainer-serve.py:960-961`:

> The server already reads and sends the bytes, so it can add this at send time: **every page gets
> it, including the ones already on disk**, and brief-compose.py does not change at all.

**Measurement — `do_GET` has exactly three `text/html` exits and one is decorated:**

```
  exit 1151: return self._send(200, index_html(ROOT).encode(), "text/html; charset=utf-8")
  exit 1231: return self._send(200, source_shell(rel, text).encode(), "text/html; charset=utf-8")
  exit 1240/1241: body = decorate_html(body) ; return self._send(200, body, ctype)
```

Driving the two renderers directly:

```
index_html   is text/html ; contains /_rev?p= ? -> False
source_shell is text/html ; contains /_rev?p= ? -> False
source_shell emits <strong>? -> True
source_shell emits <b>?      -> True
```

So the index page never live-reloads (a reader sitting on `/` does not see a new explainer
appear), and the `/src/` viewer never live-reloads the source it is displaying — which is the one
page whose subject changes while you watch it.

**On the mandate's question — should the fold have closed round 1's Medium 5?** My judgement:
**not the behaviour, but yes the claim, and it chose the local fix over the structural one at a
cost it did not price.** Round 1's proposed fix was *"move the decoration into `_send` keyed on
`ctype.startswith("text/html")` — which closes all three exits at once and makes Finding 1's case
cover them."* That fix would have **also closed High 1 above**, because once decoration lives
inside `_send`, the only honest driver for it is one that runs `_send`. The fold took the
per-branch fix and inherited both halves of what the structural one would have removed. Injecting
a reload client into the escaped source viewer is a real behaviour change with its own questions,
so declining it is defensible — writing `"Everything the server appends to an HTML page"` over it
is not.

**Why Medium.** No behaviour is wrong; two sentences are, and this repo files that shape as its
own row (`docs/backlog.md` #216, *a comment asserting what the code does not do*). Round 1's
Blocking was a false sentence in this same docstring; the fold replaced it with a narrower true
sentence (`"the call site is covered"` — I checked, that clause is true) while leaving a false
one directly above it in the same string.

**Proposed fix.** `"""Everything the server appends to a page file it reads off disk — NOT the two
generated `text/html` exits, `index_html` (:1151) and `source_shell` (:1231), which are served
undecorated by design."""` and the same qualifier at `:960-961`.

---

## Low 3 — the new driver runs outside the case protocol, so an exception there is a traceback instead of a `[FAIL]` line, and the rest of the suite never runs · Structural

**Premise.** `scripts/explainer-serve.py:1708` calls the driver eagerly, at registration time:

```python
_served = _drive_page()
case("do_GET SENDS the decorated body …", lambda: _served.get("code") == 200 and …)
```

Every other driver in this file is invoked **inside** the lambda (`_sent_headers()` at `:2660`,
`_both()` at `:2127`, `_drive_regen(...)` in its cases), so the runner's handler at `:2937` turns a
raise into a named red:

```python
except Exception as exc:  # noqa: BLE001
    print(f"  [FAIL] {name} — {type(exc).__name__}: {exc}")
```

**Measurement — make `do_GET` raise on the decorated branch, in a copy:**

```
  File ".../scripts/explainer-serve.py", line 1708, in _self_test
    _served = _drive_page()
  File ".../scripts/explainer-serve.py", line 1240, in do_GET
    raise RuntimeError("boom")
RuntimeError: boom
```

No `[FAIL]` line, no summary line, and the ~1,240 cases registered after `:1708` are never even
appended, let alone run. **This file is itself the place that calls that output shape a contract**
(`:2929-2936`): *"`[FAIL] `, NOT `FAIL: ` — the shape is a CONTRACT, not a style.
`check-plan-code.parse_fail_names` reads a red case with `startswith("[FAIL] ")`."* A crash
returns `[]` from that parser.

**Why Low, not higher — I checked that it is fail-closed and currently latent.** I ran the whole
`explainer-serve` manifest by hand, one fresh copy per entry, replicating the harness's
`parse_fail_names` semantics:

```
entries: 47
NOT killed via named case: 0
CRASHED (no [FAIL] line at all): 0
```

So the commit's *"Partial sweep 47/47 killed via the case each names"* is **true as stated** — I
reproduced it independently. A future crash would surface as *"matched 0 red case(s)"*, i.e. a red
that misdescribes its own cause, not a green.

**Proposed fix.** Memoise rather than pre-compute: `_page_once = functools.lru_cache(1)(_drive_page)`
and call it inside both lambdas. One line, and the file's own idiom.

---

## Low 4 — the `ROOT` restore is correct and completely unguarded · Structural

**Premise.** `scripts/explainer-serve.py:1694-1705` rebinds the module global and restores it in a
`finally`.

**Measurement A — the restore survives the exception path.** The traceback in Low 3 propagates
*through* `_drive_page`, so the `finally` ran; the assignment is inside the `try` (`:1699`), after
`saved_root` is captured (`:1695`), so there is no window where it can be skipped.

**Measurement B — and nothing observes it. Deleting the restore keeps the suite green:**

```
########## S3  globals()["ROOT"] = saved_root  ->  pass ##########
self-test: 206/206 passed
```

That answers the mandate's question — **no later case depends on `ROOT`** — but it is the answer
that makes it a finding rather than a clean bill. With the restore gone, `ROOT` points at a
**deleted** temporary directory for the remaining 1,240 cases; the next person to add a
`ROOT`-reading case after `:1708` gets silent 404s and a vacuously passing test. This is the
project's *"a case can pass for an ambient reason"* family, pre-armed.

For contrast, the scaffolding that *is* load-bearing is properly falsifiable — I severed both
halves and both named cases redden, so the new case is not vacuous:

```
########## S1  globals()["ROOT"] = sandbox  ->  pass ##########
  [FAIL] do_GET SENDS the decorated body — the shipped call, not just decorate_html
  [FAIL] ...and the page's own bytes survive the decoration on that same path
self-test: 204/206 passed
########## S2  (sandbox/"probe.html").write_bytes(...)  ->  pass ##########
  [FAIL] do_GET SENDS the decorated body — the shipped call, not just decorate_html
  [FAIL] ...and the page's own bytes survive the decoration on that same path
self-test: 204/206 passed
```

**Proposed fix.** One case: `case("…and the drive left ROOT exactly as it found it", lambda: ROOT
is _root_before)`, captured before `:1708`. It kills S3 and costs a line.

---

## Low 5 — the fold deleted `master`'s only recorded reason for appending rather than inserting · Transitional

**Premise.** `master:scripts/explainer-serve.py:1224`:

```python
body += RELOAD_JS.encode()   # appended, so a page that lacks </body> still gets it
```

**Measurement.** `grep -n "lacks </body>\|appended, so a page" scripts/explainer-serve.py` at HEAD
→ **not present**. The rationale is in neither the new docstring nor the comment block above the
call site. The *property* survives in a case (`decorate_html(b"<p>SENTINEL</p>").startswith(...)`,
`:1679`), so nothing is unprotected — but in a file whose entire convention is that the reason
lives beside the code, a why that existed on `master` and does not exist on the branch is a
regression in the only dimension this file optimises for.

**Proposed fix.** Restore the clause into `decorate_html`'s docstring, one sentence.

---

## Low 6 — the PR body's case arithmetic does not reconstruct its own number · Transitional

**Premise.** PR #363 body, Verification table:

> | Self-test | **206/206** (was 210; **the 5 withdrawn-constant cases went with the constant**) |

210 − 5 = 205. **Measurement**, counting `case(` lines across `git diff 22baf584..HEAD --
scripts/explainer-serve.py`:

```
removed case( lines: 7
added   case( lines: 3
--- removed ---
  decorate_html appends the emphasis baseline to an HTML body
  ...and the live-reload client, so neither term can be dropped silently
  emphasis baseline reads --emph first, so a page can override it
  ...then --fg2, the softer token 56 of 62 pages already define
  ...and falls back to inherit, which is today's behaviour unchanged
  the fallback does NOT use color-mix — measured 4.37:1, under WCAG AA, by compounding
  the baseline selector is BARE b,strong — specificity (0,0,1), so page rules win
--- added ---
  decorate_html appends the live-reload client to an HTML body
  do_GET SENDS the decorated body — the shipped call, not just decorate_html
  ...and the page's own bytes survive the decoration on that same path
```

The true accounting is **−7 +3 = −4**: five `BASELINE_CSS` constant cases, one composition case,
and one case **renamed** (so it reads as a removal and an addition), plus the two new `do_GET`
cases. 210 − 4 = 206. The sentence names only the 5 and leaves the reader two short.
`memory/a-retrospective-number-needs-provenance.md` is this exact shape. Code and commit message
are unaffected — the commit says only `"self-test 210 -> 206"`, which is correct.

**Proposed fix.** `(was 210; 7 cases removed — 5 constant cases, 1 composition case, 1 renamed —
and 3 added)`.

---

## Verified sound — attacked and held

Recording these so round 3 does not re-spend the budget.

- **The Blocking IS closed at the site it names.** Severing the shipped call on a fresh copy:
  ```
  ########## M1  body = decorate_html(body)  ->  body = body ##########
    [FAIL] do_GET SENDS the decorated body — the shipped call, not just decorate_html
  self-test: 205/206 passed
  ```
  **One casualty, the named one.** The manifest entry's `expect` string matches it exactly.
- **Every count is honest, each derived independently.**
  `python3 scripts/explainer-serve.py --self-test` → `self-test: 206/206 passed`; the USAGE
  docstring at `:66` declares 206. `len(json.load(scripts/mutations/explainer-serve.json))` → 47;
  `EXPECTED_MUTATIONS["scripts/explainer-serve.py"]` at `check-plan-code.py:1228` → 47.
  Parsing `EXPECTED_MUTATIONS` with `ast` and counting every manifest on disk:
  ```
  files declared: 57   sum: 1179
  sum of actual manifest entries: 1179
  mismatches: none
  ```
  `python3 scripts/check-plan-code.py --self-test` → `131/131 passed`;
  `python3 scripts/check-selftest-counts.py` → *"50 script(s) declare a count, every one verified
  by running it"*.
- **The sweep claim is true.** 47/47 killed via the case each names, 0 crashes — my own harness,
  one fresh copy per entry (quoted in Low 3).
- **The manifest is `master`'s 46 plus exactly one, unreordered.** Comparing objects:
  ```
  master entries: 46   HEAD entries: 47
  kept by name: 46
  order preserved & objects equal: True
  NEW: ['the server stops decorating what it sends, so every served page loses the live-reload client']
  REMOVED vs master: none
  ```
  The 1,045-line diff `22baf584..HEAD` is reformatting churn against the *branch's* intermediate
  state; `master..HEAD` is `32` added / `21` removed lines. Nothing hid in it.
- **The withdrawal is complete.** `git grep BASELINE_CSS` outside `docs/reviews/` → **nothing**.
  `--emph` outside `docs/explainers/` and `docs/reviews/` → one hit, `docs/backlog.md:248`, which
  is #220 quoting the withdrawn rule. The two hits under `docs/explainers/`
  (`backlog-table.html`, `backlog-table.fragment.html`) are that same backlog row rendered, inside
  `<code>` and HTML-escaped — **not** a page that captured the injected style while it was live.
  `color-mix` in `scripts/` → only `gen-features-page.py` and `gen-goals-page.py`, unrelated and
  pre-existing. `decorate_html` outside the server → only the manifest entry and
  `check-plan-code.py:3884`'s explanatory comment, both current.
- **Served output is byte-identical to `master`,** so the PR's `NO-ENTRY: no product behaviour
  change` is honest. Driving `do_GET` on a pristine `master` extract and on HEAD over the same
  sandbox page: `PRISTINE master bytes == HEAD bytes : True 8349 8349`.
- **Low 7 is genuinely fixed.** `RELOAD_JS` is at `:1114` with its explanatory block at `:954-963`
  directly above it; `decorate_html` now sits at `:1115`, *after* the constant it references, which
  also removes the forward-reference the old ordering carried. (There is a three-blank-line run at
  `:1128-1130`; cosmetic, not filed.)
- **The second new case is independently falsifiable**, so it is not a passenger:
  `body = decorate_html(body)` → `body = decorate_html(b"")` leaves case 1 green (reload client
  present, code 200) and reddens case 2 only.
- **CI does reach the new case.** `explainer-serve` appears nowhere in `.github/workflows/`, which
  looked like a hole — but `ci.yml:483` runs `check-plan-code.py --mutate .`, which proves a green
  control before applying each of the 47 entries, and `ci.yml:368` runs `check-selftest-counts.py`,
  which executes each declared self-test as a subprocess. ⚠ Noting for the record that the latter
  is **not** the gate: `printed_total` (`check-selftest-counts.py:320-342`) reads only the
  **denominator**, so `205/206` would satisfy it. The green control inside `--mutate .` is what
  actually holds the suite green in CI.
- **`python3 scripts/check-docs.py`** → `Documentation integrity OK`;
  **`check-ratchet-contract.py`** → `ratchet contract OK`;
  **`check-fixture-variation.py`** → `fixture variation OK — 753 parameter(s) examined across 62
  file(s)`. The new `_drive_page` did not trip the unvaried-parameter ratchet.

---

## Could Not Measure

- **`check-dashboard-entry.py` REFUSES locally** — *"11 tracked file(s) changed and no entry was
  added to docs/dashboard-entries.md"*. I verified the PR #363 body carries `NO-ENTRY: no product
  behaviour cha…`, which is the sanctioned escape and which CI reads from the event payload, so
  this is **not** a finding — but I cannot execute the CI-side read from here, so I am recording
  it rather than calling it green.
- **The browser was not used.** Nothing in the fold is visual: the emphasis rule is withdrawn and
  the served bytes are byte-identical to `master` (measured). No rendering claim is made or
  needed.
- **`tools/partial-sweep.py` was not used** — I wrote my own sweep rather than depend on a tool
  outside the repo, and quoted its full output in Low 3.
- **`check-merge-ready.py` was not run.** It is the coordinator's PR-only gate and running it here
  would reach GitHub from a reviewer; its verdict is not mine to relay.

---

NOT CONVERGED: 0 Blocking · 1 High · 1 Medium · 4 Low
