# Round 3 — Claude adversarial half — `explainer-emphasis-baseline`

START HEAD: `1c13190a5ef50b79d6895167b398af247cd6ef63`
END HEAD: `1c13190a5ef50b79d6895167b398af247cd6ef63`
Subject: `git diff 72df637b..HEAD` — one commit, `1c13190a`.
Mandate: refute. No git mutations; every mutation below ran on a copy in `$TMPDIR`.

---

## ⚠⚠ THRASHING DETERMINATION — **YES. THE CLASS RECURRED, A THIRD CONSECUTIVE ROUND.**

Stated first because the brief is right that it outweighs any individual finding.

| Round | The severance that stayed green | Where the fix landed |
|---|---|---|
| r1 | `body = decorate_html(body)` → `body = body` | extracted `decorate_html`, then drove `do_GET` |
| r2 | `self.wfile.write(body)` → `pass`, through r1's `_send` stub | put a `BytesIO` on `wfile` in `_drive_page` |
| **r3** | **`self.send_response(code)` → `self.send_response(200)`** — **208/208 GREEN** | — |

**The round-3 severance is not one I went looking for. It is row four of the table round 2 printed,
and the fold acted on rows one to three.** Round 2's Claude half, `emphasis-baseline-r2-claude.md:56-66`:

```
########## M2  self.wfile.write(body)  ->  pass ##########        self-test: 206/206 passed
########## M3  Content-Length: str(len(body))  ->  "0" ##########  self-test: 206/206 passed
########## M4  send_response(code)  ->  send_response(200) ######   self-test: 206/206 passed
```

Round 2's *proposed fix* then listed three assertions (i, ii, iii) and silently dropped M4. The
commit message says **"Falsified across all three severances"** over a four-row table, and the new
docstring says the driver **"observes the complete reply"**. It does observe it; nothing asserts it.
Re-measured on `HEAD`, below: **M4 still survives at 208/208.**

That is the exact shape ADR-0014 names — *"the repair's direction is downward; the defect's home is
upward"* — on its third consecutive iteration in one component. `docs/dev-process.md`'s arming
condition (**two consecutive rounds whose findings came from the previous round's fix, in one
component**) was already met before this round; this round is the third.

**And the fold introduced a new instance of the propagation failure ADR-0014 was written about.**
Before `1c13190a` this file had three handler drivers and all three stubbed `_send` — uniform, and
uniformly blind. The fold hardened **one**:

| Driver | Line | Mechanism | Routes it measures |
|---|---|---|---|
| `_drive_page` | `:1704` | **`BytesIO` on `wfile` — real `_send`** | `/probe.html` only (hardcoded) |
| `_drive_get` | `:2474` | **stubs `_send`** | `/`, `/_rev`, `/_stale`, 404 tail, `/questions` |
| `_drive_src` | `:2221` | **stubs `_send`** | every `/src/` case |
| `_sent_headers_for` | `:2702` | stubs `send_response`/`send_header`/`end_headers`/`wfile` | header **presence**, one value |

ADR-0014's own origin story is `check-ci-watched.py:860` — the right repair, written once, which
*"propagated to zero siblings, because a docstring is read by whoever opens that file and nothing
carries it anywhere else."* **That happened again inside a single file, in the commit written to
close it.** The hypothesis the brief puts on the table — that today's instances are the measured
cost of **D2 never being built** — is supported: no rule anywhere asks *does this suite observe what
reaches the wire?*, so the fix reached exactly the one call site a human had been pointed at.

---

## Measurement method

Mutations applied to a fresh copy of `HARNESS_TREE` (`scripts`, `supabase`, `docs`,
`.claude/hooks`, `.github`) in `$TMPDIR`, `$HOME` redirected, replicating
`check-plan-code.run_mutations` semantics (anchor must be unique, suite must go red, red must be
**via the case the entry names**, using `parse_fail_names`). Control green before every run:

```
CONTROL rc=0 tail='self-test: 208/208 passed'
```

---

## Verified sound (stated before the findings, because several attack lines came back clean)

**Attack 4 — all 49 manifest entries bind uniquely and die via the case each names. No orphans.**
Full sweep of this file's manifest, control green at both ends:

```
  1 ok  src_root stops falling back to the checkout it runs from
  …
 46 ok  index_html leaves the link TEXT unescaped while encoding the href
 47 ok  the server stops decorating what it sends, so every static .html page loses the live-reload client
 48 ok  the reply body is never written to the wire, so every response is headers only
 49 ok  Content-Length is hardcoded to 0 while the body is still sent, so the reply self-contradicts

49 entries, 0 problem(s)
```

**Attack 6 — the corrected comment is TRUE, and the count is three, not four.** Every `text/html`
emission in the file: `:1156` (`/` → `index_html`), `:1236` (`/src/` → `source_shell`), `:1240`
(the ctype table, used at `:1246`). `_regenerate` and `do_POST` emit only `text/plain` and
`application/json`; `/latest` emits no body. Exactly one of the three is decorated. The comment's
substance is correct — only its line numbers are not (Low 1).

**Attack 2 — the hand parse cannot be fooled the four ways named, and cannot pass vacuously.**
`partition(b"\r\n\r\n")` takes the **first** separator, so only the real header block is scanned —
a header-like line inside the body is unreachable. `declared` is `-1` only when the header is
absent, and `len(body)` is never negative, so `-1 == -1` is unreachable. A missing blank line gives
`body = b""`/`declared = -1` → fails. An empty wire fails case 3 first. The one residual is a raise,
not a pass (Medium 3).

**Attack 5 — the `ROOT` restore is correct on the exception path.** `return h.wfile.getvalue()`
sits in the `try`; the `finally` runs before the value leaves. Nothing later in the suite depends on
the real `ROOT` — which is also why the line is unfalsifiable (Low 3).

**Attack 1, the attribute half — the gap is real but is not what hides anything today.** Set by the
real `handle_one_request`/`__init__` and **not** by the driver: `connection`, `headers`,
`raw_requestline`, `request`. `do_GET` reads none of them (`self.headers` is `do_POST`'s, `:1298`).
Measured status line and header block through the driver:

```
protocol_version = 'HTTP/1.0'
first line: b'HTTP/1.0 200 OK'
headers: [b'HTTP/1.0 200 OK', b'Server: explainer-serve Python/3.14.4',
          b'Date: …', b'Content-Type: text/html; charset=utf-8', b'Content-Length: 8356']
```

**So the answer to "is the new driver stronger, or differently weak?" is: it is strictly stronger as
an *instrument* and it is not weak at all as an instrument — the whole reply is in `_wire`. What is
weak is the set of assertions over it.** Five cases read three facts out of a five-line header block
plus a body. The status line is read only for `200`; `Content-Type`, `Server` and `Date` are never
read. That is where High 1 and Medium 2 live.

**Other gates run:** `check-selftest-counts.py` → *50 script(s) declare a count, every one verified
by running it*. `check-plan-code.py --self-test` → `131/131`. Manifest parsed independently: 49
entries, no duplicate names, `EXPECTED_MUTATIONS` sum consistent at 1181.

**Could Not Measure:** the full `check-plan-code.py --mutate .` (1181 entries, ~27 min — backlog
#208). I ran this file's 49 in full, which is the only file the diff touches; the other 1132 entries
and their subjects are byte-identical to `72df637b`, where Codex measured `1179/1179 killed`.

---

## High 1 — `send_response(code)` can be hardcoded to `200` and the suite is green. This is round 2's own M4, dropped from round 2's fix. *(Structural)*

**Premise.** Commit `1c13190a`: *"Falsified across all three severances."* `scripts/explainer-serve.py:1716-1718`:

> ⚠ Nothing in `_send` (`:1178`) touches a socket directly — `send_response`, `send_header`,
> `end_headers` and the write all route through `wfile`. So a BytesIO observes the complete reply
> and still binds no port.

**Measurement.** `self.send_response(code)` → `self.send_response(200)` in `_send` (`:1145`):

```
 54 ⛔ SURVIVED: PROBE E: _send hardcodes status 200, so every error reply claims success
```

208/208 green with every error response on the wire reading `HTTP/1.0 200 OK`.

**Why nothing sees it.** Eighteen assertion sites in the suite compare a status code, and **all eighteen read the argument
handed to a stubbed `_send`, never the status line**:

```
  :2280  lambda: _drive_src("/src/srcfix.md", str(_srcroot))[0] == 200)
  :2533  lambda: _drive_stale()[0] == 200)
  :2569  lambda: _drive_post("/nope", b"{}")[0] == 404)
  :2571  lambda: _drive_post("/questions", b"", length=0)[0] == 413)
  :2606  case("an unknown path is a 404", lambda: _drive_get("/yps-no-such-page-…")[0] == 404)
  :2751  lambda: _drive_regen({"page": _page}, _timeout_runner)[0] == 504)
  …18 lines total
```

The one driver that holds the status line asserts only `200` on a path that is a `200` anyway, so
hardcoding `200` is invisible from both sides.

**Why High, not Medium — this is a live defect, not only a coverage hole.** The injected client
branches on `r.ok` for both endpoints (`:1036`, `:1065`):

```js
.then(function (r) { return r.ok ? r.text() : null; })
```

With the status hardcoded, `/_rev`'s *"no such page"* 404 arrives as a `200` and the client adopts
the string `no such page` as the page's revision. Every later poll compares equal, so the page never
reloads and never reports the failure — and the file's own `:1195` comment promises the opposite:
*"The UNREACHABLE case is not silenced — that is `/_rev`'s failure path, which now speaks up."* Same
for `/_stale`. It is the project's recurring *degraded gate that reports success*, inside the
mechanism that exists to tell the reader the page is stale.

It is **pre-existing on master** — nothing in this fold regressed it. It is High for round 2's own
stated reason: it is the identical class the round was convened to close, it was measured and handed
to the author in the round-2 document, and the delivered docstring asserts the property it omits.

**Proposed fix.** One case over `_wire`, and one manifest entry:

```python
case("...and a 404 route puts 404 ON THE WIRE, not merely into _send's argument",
     lambda: _drive_page("/yps-no-such-page-2026-10-02.md").startswith(b"HTTP/1.0 404"))
```

which requires the parameterisation in High 2.

---

## High 2 — the fold hardened one of three drivers; two still measure through the mechanism this commit documents as insufficient *(Structural — this is the thrashing finding)*

**Premise.** `scripts/explainer-serve.py:1705-1713`:

> ⛔⛔ `BytesIO` ON `wfile`, NOT A STUBBED `_send`, AND ROUND 2 IS WHY. The first version of this
> case stubbed `self._send` — the ONE method in this file that touches the wire — so everything
> below it was invisible.

**Measurement.** That sentence is true of `_drive_page` and false of the file. `_drive_src`
(`:2225-2226`) and `_drive_get` (`:2477-2478`) are unchanged by this commit and still read:

```python
h._send = lambda code, body, ctype: got.update(code=code, body=body, ctype=ctype)
```

Every route except `/probe.html` is measured through them. The consequences are High 1 above and
Mediums 1 and 2 below — three distinct severances, all surviving, all behind the stub.

**And the new driver was written so it cannot be reused.** `_drive_page()` takes no arguments and
hardcodes `h.path = "/probe.html"` (`:1727`). It is the only instrument in the file capable of
observing a status line or a header value, and it can be pointed at exactly one route.

**Why this is the finding and not bookkeeping.** ADR-0014 exists because the correct repair, written
once in `check-ci-watched.py:860`, *"propagated to zero siblings."* This commit reproduced that
inside one file: the sibling drivers sit 500 and 800 lines below the new one, under comments
(`:2218-2220`, `:2472-2473`) that still advertise the stub as the technique — so the next person to
add a route copies the blind one. Severity High for the same reason round 2 chose High: nothing
regressed, and the class the round was convened to close is reproduced one frame out.

**Proposed fix (one piece of work, closes High 1 and Mediums 1–2):**

1. Give `_drive_page` a `url_path` parameter and a `root=` for the sandbox, returning raw bytes.
2. Re-point `_drive_get` at it, returning a parsed `(status, headers, body)` triple rather than the
   captured arguments; keep `_drive_src`'s env-forbidding wrapper but drive through the same core.
3. Delete the `_send` stub from the file. **The refusal is the ratchet**: with no stub left, a new
   route cannot be cased blind.

---

## Medium 1 — `/latest` has no handler case at all, and it is the one arm no stub driver can reach *(Structural)*

**Premise.** `do_GET:1157-1164` is the only arm that writes to `wfile` **without** going through
`_send`:

```python
if path == "/latest":
    target = latest_target(ROOT)
    if not target:
        return self._send(404, b"no explainers yet", "text/plain; charset=utf-8")
    self.send_response(302)
    self.send_header("Location", target)
    self.end_headers()
    return
```

**Measurement.** Three severances, each on a fresh copy:

```
 50 ⛔ SURVIVED: PROBE A: /latest stops sending the Location header, so the redirect goes nowhere
 51 ⛔ SURVIVED: PROBE B: /latest answers 200 instead of 302, so the bookmark never redirects
 52 ⛔ SURVIVED: PROBE C: /latest stops ending its headers, so the reply is never terminated
```

**Why it is uncovered, structurally.** `latest_target()` has seven unit cases (`:1444`, `:1462`,
`:1484`, `:1598`, `:1603`, …). The **route** has none, and it cannot have one through `_drive_get`:
that driver reads `got` out of an `_send` stub, and this arm never calls `_send`, so
`_drive_get("/latest")` returns `(None, b"", "")` whatever the code does. The unit/call-site split
is ADR-0014's, and here the call site is not merely uncovered — it is unreachable by the
instrument the suite uses everywhere else.

**Consequence.** `/latest` is the advertised entry point: the module docstring prints it at `:27`
and `start()` prints *"one-click: http://…/latest"* at `:1331` and `:1345`. Severing it gives a
blank page or a dead redirect with the suite fully green.

Medium rather than High: unlike High 1 it fails **loudly** on first human use, so it cannot ship
unnoticed for long.

**Proposed fix.** With the parameterised driver: assert `b"HTTP/1.0 302"` and
`b"Location: /<the dated page>"` on the wire over a sandbox `ROOT`, plus the `404 no explainers yet`
arm; two manifest entries.

---

## Medium 2 — `do_GET`'s content-type **argument** is unobserved; the callee half of this same defect was already bought once *(Structural)*

**Premise.** `scripts/explainer-serve.py:2675-2680`:

> ⛔ r3 MEDIUM 5 — `_send`'s Content-TYPE VALUE was unasserted; only its presence was.
> `send_header("Content-Type", ctype)` → a hardcoded `"text/plain"` survived 188/188, i.e. every
> page in the server served as plain text with nothing going red.

That bought a case on the **callee**: `_send passes the caller's content type through, not a
hardcoded one` (`:2678`). Measured here: manifest entry 40 (`_send hardcodes a content type…`) does
die via that case.

**Measurement — the identical defect at the call site is still open.** `do_GET:1246`
`return self._send(200, body, ctype)` → `return self._send(200, body, "text/plain; charset=utf-8")`:

```
 55 ⛔ SURVIVED: PROBE F: do_GET's tail hardcodes text/plain, so .html is served as plain text
```

208/208 green, every `.html`, `.md`, `.css`, `.js`, `.svg` and `.png` served as plain text. The
ctype table at `:1240` — six entries — has no case that reads what the server actually sends.

**Why it matters for this round specifically.** The prose that bought the callee case describes
*exactly this outcome* ("every page in the server served as plain text"), and the fix landed one
frame below where the defect can still occur. Same pattern as round 1 → round 2, already paid for
once in this file, on these two lines.

**Proposed fix.** `case("...and the Content-Type on the wire is the one the route chose")` reading
the header out of `_wire`, driven at `.html` and at one non-`.html` suffix so a single constant
cannot satisfy it; one manifest entry on the `:1246` call site.

---

## Medium 3 — an exception inside `do_GET` takes the suite down with **zero `[FAIL]` lines**, so no manifest entry can ever name it *(Structural)*

**Premise.** `scripts/explainer-serve.py:2981-2988` records why the report format is a contract:

> MEASURED with that function: this file's old shape returned `[]` … so every mutation of this file
> would have reported "matched 0 red case(s) — caught by something else", i.e. a kill nobody can see.

**Measurement A.** `_wire = _drive_page()` (`:1744`) is **eager** — it runs at suite-build time,
outside the `for name, fn in cases:` loop and therefore outside its `except`. Dropping `.html` from
the ctype table (a plausible one-line edit) raises `KeyError` inside `do_GET`:

```
 50 ⛔ WRONG CASE: PROBE I: the ctype table loses .html, so serving any page raises KeyError
       actual fails=[]
       tail=['…}[resolved.suffix.lower()]', "KeyError: '.html'"]
```

Zero `[FAIL]` lines, a bare traceback, `208/208` never printed. Under `--mutate .` that is *"matched
0 red case(s)"* — the invisibility the comment above says was fixed, reintroduced for one family of
defects by the eager call. Every other driver in the file (`_drive_src`, `_drive_get`,
`_drive_stale`, `_sent_headers_for`, `_drive_regen`) is invoked **inside** a lambda; `_drive_page`
alone is not.

**This family is not hypothetical here.** Backlog #87 — documented in this file at `:1408-1424` — was
an exception escaping a handler: *"`GET /_stale?p=%00` gave curl exit 52 ('empty reply from server')"*.
That is the class whose mutations this suite cannot attribute.

**Measurement B — the new case has the same shape.** `int()` in `_declared_vs_actual` (`:1761`)
raises on a non-numeric header. The loop *does* catch it, but it prints
`[FAIL] {name} — ValueError: …`, and `parse_fail_names` returns the name **with the suffix**, so no
`expect` can match:

```
 51 ⛔ WRONG CASE: PROBE J: Content-Length is emitted non-numeric
       actual fails=["...and Content-Length states the body's REAL length, not a stale or zero one
                      — ValueError: invalid literal for int() with base 10: b'yes'"]
```

So `Content-Length: "0"` is a manifestable kill and `Content-Length: "yes"` — a strictly worse
defect — is not.

**Proposed fix.** Wrap the body of `_drive_page` at its call site (`_wire = None` plus a lazy
`_wire_once()` memo inside the lambdas), or make every case call it; and parse `declared`
defensively (`int(x) if x.isdigit() else -1`) so a malformed header is a clean red.

---

## Low 1 — every line citation introduced by this commit is wrong, and one of them re-imports a number round 2 had already corrected *(Transitional)*

**Premise.** `:1693-1696`:

> `do_GET` has THREE `text/html` exits and only one is decorated: `/` returns
> `index_html(ROOT).encode()` (`:1151`) and `/src/` returns `source_shell(...).encode()` (`:1231`)

and `:1717`: *"Nothing in `_send` (`:1178`) touches a socket directly"*.

**Measurement.** On `HEAD`:

| Cited | What is actually there | The real line |
|---|---|---|
| `:1151` | `self.wfile.write(body)` | `index_html` is at **`:1156`** |
| `:1231` | `return self._send(404, b"no such source file", …)` | `source_shell` is at **`:1236`** |
| `:1178` | a comment inside `/_rev` | `def _send` is at **`:1144`** |

**Provenance, which makes it a class and not three typos.** `:1151` and `:1231` are correct against
the **parent** `72df637b` — they are Codex's round-2 citations
(`emphasis-baseline-r2-codex.md`), copied in verbatim. This commit's own 5-line insertion at
`decorate_html` (`:1127-1131`) shifted everything below it by exactly 5. So **every line number this
commit writes was computed against the tree before the commit.** `:1178` is worse: it is round 1's
citation, which round 2 had already corrected to `:1139-1146` in its own text — the fold reinstated
the superseded number.

Each wrong number lands on a **different real line of code**, which is the failure mode that makes
a reader trust it.

**Proposed fix.** Cite the symbol (`decorate_html`'s call site in `do_GET`, `Handler._send`), not
the line. The repo's standing rule.

---

## Low 2 — case 3's disjunction has two clauses and both are true today, so neither is load-bearing *(Transitional)*

**Premise.** `:1749-1750`:

```python
case("...under a 200, so the case cannot pass on an error response",
     lambda: _wire.startswith(b"HTTP/1.0 200") or b" 200 " in _wire.split(b"\r\n")[0])
```

**Measurement.**

```
first line: b'HTTP/1.0 200 OK'
disjunct1 startswith HTTP/1.0 200: True
disjunct2 b' 200 ' in first line : True
```

`protocol_version` is `'HTTP/1.0'` (class default; `Handler` does not override it), and
`b"HTTP/1.0 200 OK"` also contains `b" 200 "`. The second clause exists to tolerate a future
`HTTP/1.1`, but since both are satisfied by the same bytes, deleting either leaves the suite green —
so nothing records which one is the guard, and a later `protocol_version` change would silently kill
the first with no signal.

To be clear, the case **is** load-bearing as a whole: removing `end_headers()` from `_send` is caught
by it (`PROBE D`, red via this case plus the Content-Length case). It is the OR that is untestable.

**Proposed fix.** Assert the status line itself — `_wire.split(b"\r\n")[0].split(b" ")[1] == b"200"`
— one clause, true for either protocol version.

---

## Low 3 — the `finally` restore the fold added a comment to justify can be deleted at 208/208 *(Transitional)*

**Premise.** `:1740-1741`, new in this commit:

> ⚠ RESTORED IN `finally`, so an exception above cannot leave the module pointing at a deleted temp
> dir for every case after this one.

**Measurement.** Deleting `globals()["ROOT"] = saved_root` from the `finally`:

```
 52 ⛔ SURVIVED: PROBE K: _drive_page's ROOT restore is dropped from the finally
```

208/208. No case after `_drive_page` reads the real `ROOT` — `_drive_stale` saves and restores its
own, and every other fixture builds its world — so the hazard the comment names has no witness
today. The line is **correct** and should stay; the comment asserts a protection nothing measures,
and the next case added after `:1744` inherits a silent dependency.

**Proposed fix.** Either add the falsifier (`case("…and _drive_page leaves ROOT where it found it",
lambda: globals()["ROOT"] == _root_before)`) or soften the comment to say the restore is defensive
and currently unobserved. The first is two lines.

---

## Anything round 2 verified as sound that this fold broke

None found. Round 2 Codex's four green gates were re-run: `--self-test` 208/208 (was 206/206, +2 as
declared), `check-selftest-counts.py` all 50 verified, `check-plan-code.py --self-test` 131/131,
manifest independently parsed at 49 with `EXPECTED_MUTATIONS` summing to 1181. The withdrawn
`BASELINE_CSS`/`--emph` strings are still absent from the code. The served bytes for a static
`.html` page are unchanged apart from the two new cases, which touch no production path.

Round 2 Codex's single Low (the "EVERY served page" overstatement) is **correctly closed** — the
mutation name, the comment and the manifest entry all now say *static `.html`*, and `/` and `/src/`
are named as the known gap with round 1's Medium 5 cited.

---

NOT CONVERGED: 0 Blocking · 2 High · 3 Medium · 3 Low
