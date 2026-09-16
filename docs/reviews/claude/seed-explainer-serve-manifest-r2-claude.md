# Round 2 — `seed-explainer-serve-manifest` — Claude (adversarial, standing in for the Codex half)

**Lead:** the branch is correct and round 1's fixes hold — I could not find a defect in the shipped
behaviour, every gate I ran is green (ten of them, listed below), entry 13's contested repair is
honest, and the S2 state-leak is really gone. What I found is that **the manifest's 25 entries and the suite's 167
cases both stop at the pure-helper boundary**: I applied **73 plausible mutations across the whole
file and 58 survived at 167/167 (79%)**, and they are not scattered — **eleven of them are inside
`_regenerate`, the function round 1 declared fixed with five new cases**, including one that lets a
POST body name the script the server executes.

**Convergence: NOT reached.** Two High findings, one of them fix-induced on the
`manifest-attribution` component the coordinator pre-committed against. Round 3 owed.

```yaml
round: 2
subject: seed-explainer-serve-manifest
halves: {claude: ran, codex: standin-by-claude}
findings:
  - {id: H1, severity: High,   aim: deliverable, fix_induced: false, component: regenerate,            disposition: open}
  - {id: H2, severity: High,   aim: instrument,  fix_induced: true,  component: manifest-attribution,  disposition: open}
  - {id: M3, severity: Medium, aim: instrument,  fix_induced: true,  component: regenerate,            disposition: open}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: stale-endpoint,        disposition: open}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: post-preamble,         disposition: open}
  - {id: M6, severity: Medium, aim: deliverable, fix_induced: false, component: get-routing,           disposition: open}
  - {id: M7, severity: Medium, aim: instrument,  fix_induced: false, component: claimed-bound,         disposition: open}
  - {id: L8, severity: Low,    aim: instrument,  fix_induced: true,  component: bookkeeping,           disposition: open}
  - {id: L9, severity: Low,    aim: instrument,  fix_induced: true,  component: fixture-variation,     disposition: open}
  - {id: L10, severity: Low,   aim: instrument,  fix_induced: false, component: process-layer,         disposition: open}
  - {id: L11, severity: Low,   aim: instrument,  fix_induced: false, component: send-headers,          disposition: open}
  - {id: L12, severity: Low,   aim: instrument,  fix_induced: false, component: explainers-ordering,   disposition: open}
  - {id: S13, severity: Low,   aim: instrument,  fix_induced: true,  component: reviewer-harness,      disposition: fixed}
```

## Method, and its one self-inflicted defect

Every mutation below was **applied to `scripts/explainer-serve.py` and run**, never reasoned about.
Harness: `cp` the file to a temp path outside the repo, edit the original, run `--self-test`, read
the **`N/M passed`** line, `cp` back, assert md5. `git status --short` empty at start and end; md5
`bee6d8d3befa1df111233b87f2a65b36` before and after every batch. No git command touched the tree.

**S13 — my own instrument was wrong for the first three batches, and it is worth recording because
it is this repo's `measure the population the CODE sees`.** I parsed failure names with
`^\[FAIL\] `, and the runner prints `  [FAIL] {name}` — **two leading spaces** (`:2447`, `:2449`).
So every batch reported `fails=0`. It changed **no survivor verdict**, because a survivor is decided
by the `N/M passed` line and every survivor here read `167/167` — which is exactly why the brief
says to read that line and not to grep for FAIL-shaped tokens. It did silently empty the name lists,
and the first run of the M7 measurement below printed `red cases: 0` over a genuinely red suite.
Fixed and re-measured; every name list in this document is post-fix.

---

## H1 — HIGH — `_regenerate`'s allow-list is "the whole security argument" and nothing can falsify it

`scripts/explainer-serve.py:1173-1188`. The docstring is unambiguous:

> ⚠ THE ALLOW-LIST IS THE WHOLE SECURITY ARGUMENT, and it is a dict of literals: the caller names a
> KEY, never a path, an argument or a command. **Nothing the caller sends reaches the command line**
> … `shell=False` (a list argv) and a timeout are the belt to that brace.

Four claims. **None of the four has a case.** Measured, each applied alone:

| mutation | line | result |
|---|---|---|
| `REGENERABLE.get(want)` → `want` — the caller's own string becomes the script | `:1184` | **167/167 SURVIVED** |
| `REGENERABLE.get(want)` → `.get(want, "gen-dashboard.py")` — unknown page silently rebuilds something | `:1184` | **167/167 SURVIVED** |
| list argv → an f-string with `shell=True` | `:1193` | **167/167 SURVIVED** |
| `str(SCRIPTS / script)` → `script` (resolved against CWD) | `:1193` | **167/167 SURVIVED** |
| the 400 body stops naming the legal set | `:1186` | **167/167 SURVIVED** |

**Proved by execution, not by reading.** Under the first mutation I drove the real
`Handler._regenerate` with a recording stand-in for `subprocess.run`:

```
POST /regenerate  {"page": "../../../../../../tmp/evil.py"}
  response : 200 b'{"ok": true, "page": "../../../../../../tmp/evil.py"}'
  argv     : ['/usr/local/.../python3.14', '/private/var/.../scripts/../../../../../../tmp/evil.py']
```

The attacker-controlled string traverses out of `scripts/` and lands on the command line, the caller
is told `ok: true`, and the suite reports **167/167**.

⭐ **The pointed part is that round 1 worked inside this function.** H2 added five cases to
`_regenerate` and the commit says *"five cases driving the real handler through a stubbed
`subprocess.run`"* — and the allow-list, the argv shape and the timeout were not among them. The
only case that touches `want` at all is `a non-string page is refused`, which is about a `TypeError`.

**Also surviving in the same function** — the sibling of round 1's own headline:

| mutation | line | result |
|---|---|---|
| **delete the whole non-zero-exit arm** — a generator that exits 1 reports `{"ok": true}` | `:1201-1204` | **167/167 SURVIVED** |
| `if r.returncode != 0:` → `if r.returncode > 0:` — a signal-killed generator reports success | `:1201` | **167/167 SURVIVED** |
| drop the per-page lock (the ThreadingHTTPServer race the comment at `:116` exists for) | `:1189-1192` | **167/167 SURVIVED** |
| `REGEN_TIMEOUT = 300` → `30000` | `:111` | **167/167 SURVIVED** |

Round 1's H2 was *"a timeout is NOT a failure to report as rebuilt"*, and its fix cased **the 504
arm**. The **500 arm three lines below it says `NOT REBUILT` for the same reason** and can be deleted
silently. That is *after fixing, SEARCH for the class* failing one `if` later, in the commit that
cited the rule — the second time on this branch, per round 1's own H1.

**Falsifier:** add a case asserting `_drive_regen({"page": "gen-dashboard.py"}, …)[0] == 400` (the
allow-list refuses a value that is a *legal script name but not a key*), one asserting the recorded
argv is `[sys.executable, str(SCRIPTS / REGENERABLE[page])]`, and one driving a `returncode=1`
runner to a 500. If any of those passes with the mutations above applied, I am wrong.

---

## H2 — HIGH — manifest entry 17's kill is real and its attribution is misleading: the case guards the CONSTANT, not the listener

**fix-induced: yes** — verified, not assumed: `git show 214eb376 -- scripts/mutations/explainer-serve.json`
adds the entry (`+ "name": "the listener stops being loopback"`) and
`git show 214eb376 -- scripts/explainer-serve.py` adds exactly one line matching
`the listener is loopback`. Both are round 1's H1 fix.

⚠ **Severity calibration, stated so you can disagree with it.** Round 1 rated its structurally
similar M3 (*kill real, attribution misleading*) a **Medium**, and I have rated this a **High**. The
difference I am claiming is the subject, not the shape: M3's entry mis-certified a path helper; this
one mis-certifies **one of the four clauses of the security verdict governing whether an entire
checkout is reachable from the LAN**, and it is the only finding in this round where the ratchet
**actively certifies a claim that is false** rather than merely failing to check one. If you think
that is still a Medium, nothing else in this review depends on it — convergence is already blocked by
H1 on its own.

`scripts/mutations/explainer-serve.json` entry 17 is named *"the listener stops being loopback"* and
points at the case *"the listener is loopback — clause 3 of the /src/ reach verdict"*
(`scripts/explainer-serve.py:2285-2286`). The case is:

```python
case("the listener is loopback — clause 3 of the /src/ reach verdict",
     lambda: HOST == "127.0.0.1")
```

The entry mutates `HOST = "127.0.0.1"` → `"0.0.0.0"` (`:99`) and the case goes red. **The kill is
real. What it guards is the value of a constant.** Measured — leave `HOST` alone and change the bind
at `:1272`:

```python
with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler) as httpd:   # 167/167 SURVIVED
```

**The listener really does stop being loopback and the manifest still certifies clause 3.** This is
round 1's own M3 shape — *the entry certifies a property using a case that is about something
else* — arriving on a **security clause** rather than a helper, and it is the one clause of the four
whose failure exposes the whole checkout to the LAN.

⚠ The sharp version: round 1 wrote, of the clause-4 case, *"asserted on what `_send` actually emits,
via a header-capturing stub — **not on the absence of a string in source, which would pass on a
header added through a helper**."* That reasoning is correct and it was applied to clause 4 only.
Clause 3, added in the same commit, three lines above, does the weaker thing — and the weaker thing
is exactly what the sentence warned about, one indirection over.

### ⭐ A repair, and I measured it rather than proposing it

Round 1's M3 records that a reviewer's proposed fix was refuted by the harness, so I ran mine before
writing it down. Replace the case with one that asserts **the address `start()` hands the server**,
driving `start()`'s child path with `os.fork`, `os.setsid`, `detach_streams`, `port_busy` and
`http.server.ThreadingHTTPServer` all stubbed and restored in a `finally` — the `_drive_regen`
pattern already in the suite:

```
control (fix applied, code correct)  : self-test: 167/167 passed
bind → "0.0.0.0", HOST untouched     : self-test: 166/167 passed
                                       [FAIL] the listener is loopback — clause 3 of the /src/ reach verdict
   → attributable (plain name, no exception text): True
entry 17's own mutation (HOST → 0.0.0.0): self-test: 166/167 passed, same single name
```

So the repaired case kills **both** mutations, stays green on correct code, and reports a **plain
`False`** — so entry 17 keeps attributing and needs no re-pointing. ⚠ Stated residual: the stub
proves the *address `start()` passes to the constructor*, not that a real socket bound loopback.
That is strictly stronger than `HOST == "127.0.0.1"` and it is not a proof about sockets.

⚠ **Coordinator's pre-commitment.** Round 1 pre-committed: *"if round 2 finds a fix-induced defect in
`manifest-attribution` … that is one round of thrash there, and a third attempt at an entry's
attribution should be answered by deleting the entry."* The **trigger condition is met** (this is a
fix-induced attribution defect in that component). The **remedy clause is not** — entry 17 is on its
first attempt, not its third, and the repair above is measured rather than hypothesised. Flagging
both halves so the call is yours, not mine.

---

## M3 — MEDIUM — round 1's `_regenerate` cases are stubbed at a seam that cannot see the arguments, so one passes for a reason other than its name

**fix-induced: yes.** `scripts/explainer-serve.py:2310-2326` (`_timeout_runner` at `:2322`). `_drive_regen` replaces
`subprocess.run` **globally** with a runner that ignores every argument:

```python
def _timeout_runner(*_a, **_k):
    raise subprocess.TimeoutExpired(cmd="x", timeout=REGEN_TIMEOUT)
```

It raises **unconditionally**. So the case *"a regenerate TIMEOUT is 504 NOT REBUILT, never a
reported success"* asserts the handler's **reaction** to a `TimeoutExpired` and nothing about a
timeout ever being **requested**. Measured:

| mutation | line | result |
|---|---|---|
| delete `timeout=REGEN_TIMEOUT` from the `subprocess.run` call | `:1194` | **167/167 SURVIVED** |
| delete `capture_output=True` | `:1194` | **167/167 SURVIVED** |

With the first applied, the real server hangs forever on a wedged generator and **the 504 arm becomes
unreachable dead code** — while the two cases whose names are about that arm stay green. This is the
priority-2 target exactly: a round-1 case that fails for a reason other than the one its name gives.

The restore itself is **safe** — `finally: subprocess.run = _real`, verified: three consecutive
in-process `_self_test()` runs each returned 167/167 and `subprocess.run` was `is`-identical to the
real one afterwards.

**Falsifier:** have `_drive_regen` record the `kwargs` its runner receives and assert
`kw["timeout"] == REGEN_TIMEOUT` and `kw["capture_output"] is True` and that the first argument is a
`list`. If deleting `timeout=` then leaves the suite green, I am wrong.

---

## M4 — MEDIUM — `/_stale` has no case at all, and losing one guard drops the connection

`scripts/explainer-serve.py:1107-1141`. No case names this branch. `stale_verdict` is well covered
as a **function**; the handler that calls it is not. Measured:

| mutation | line | result |
|---|---|---|
| `verdict = stale_verdict(built, newest)` → `verdict = "fresh"` — the banner dies silently | `:1136` | **167/167 SURVIVED** |
| drop ` {newest_src}` — the client can no longer say WHICH file moved | `:1140` | **167/167 SURVIVED** |
| drop `.removesuffix(".html")` from the slug | `:1119` | **167/167 SURVIVED** |
| drop `or not sources` from the guard | `:1122` | **167/167 SURVIVED** |

The last one is the serious one. `PAGE_SOURCES.get(slug)` returns `None`, and the `try` below catches
only `(OSError, ValueError)`. Driven through the real `do_GET`:

```
mutated : TypeError: 'NoneType' object is not iterable   → escapes do_GET, connection dropped, no status line
control : 200 b'fresh'
```

That is **backlog #87/#123's exact symptom at a fourth site** — the class round 1's H2 named when it
found it at a third. The `removesuffix` one is quieter and still bad: the injected client sends
`location.pathname`, so a reader who arrived at `/dashboard.html` gets `slug == "dashboard.html"`,
no source match, and `fresh` forever. A banner that silently stops firing is the failure this
endpoint's own comment (`:1113-1117`) says it is choosing between.

**Falsifier:** a case driving `do_GET` with `path="/_stale?p=/<a real page with no PAGE_SOURCES entry>"`
asserting a 200 `fresh` **and no raise**, plus one asserting `/_stale?p=/dashboard.html` and
`/_stale?p=/dashboard` agree.

---

## M5 — MEDIUM — `do_POST`'s whole preamble is uncased, including the wiring of the 2026-08-17 measured bug

`scripts/explainer-serve.py:1215-1239`. `question_text` and `format_question_entry` are covered
thoroughly as functions (seven cases). The handler that wires them is covered by nothing:

| mutation | line | result |
|---|---|---|
| `if length <= 0 or length > MAX_BODY:` → `if length <= 0:` — the 64 KB ceiling is gone | `:1223` | **167/167 SURVIVED** |
| `MAX_BODY = 64 * 1024` → `64 * 1024 * 1024` | `:103` | **167/167 SURVIVED** |
| drop `if not isinstance(payload, dict): raise` — a JSON list reaches the handlers | `:1227-1228` | **167/167 SURVIVED** |
| delete the two-route allow-list, so any POST path is handled | `:1217-1218` | **167/167 SURVIVED** |
| `if question_text(payload) is None:` → `if False:` | `:1235` | **167/167 SURVIVED** |

The last is the notable one. `question_text`'s docstring is the longest in the file and exists
because *"a POST with the keys `question`/`section` … returned `{"ok": true}` and appended a block
reading '(empty)'"*. Its **handler wiring** has no case, so the 400 arm can be removed at 167/167 —
and `format_question_entry`'s deliberate `raise ValueError("refusing to format a question with no
text")`, written so *"a future caller cannot reintroduce the silent (empty)"*, then escapes
`do_POST`. Driven:

```
POST /questions {"doc":"x","text":"   "}
  RAISED: ValueError: refusing to format a question with no text  → connection dropped
```

So the guard that was supposed to make the regression loud converts it into #87/#123's symptom at a
**fifth** site, and nothing sees it.

**Falsifier:** a `_drive_post` helper (the `_drive_regen` pattern) asserting 400 for a
whitespace-only `text`, 413 for `length > MAX_BODY`, 400 for a JSON array, and 404 for `/whatever`.

---

## M6 — MEDIUM — `do_GET`'s content-type map and reload-injection have no case

`scripts/explainer-serve.py:1159-1168`.

| mutation | line | result |
|---|---|---|
| `if resolved.suffix.lower() == ".html":` → `if True:` — `RELOAD_JS` appended to **every** file | `:1166-1167` | **167/167 SURVIVED** |
| `".svg": "image/svg+xml"` → `"text/html"` | `:1164` | **167/167 SURVIVED** |
| `".md": "text/markdown…"` → `"text/html…"` | `:1162` | **167/167 SURVIVED** |
| 404 arm serves `index_html(ROOT)` with a 200 instead | `:1160-1161` | **167/167 SURVIVED** |

The injection one, driven through the real handler over a real PNG:

```
GET /logo.png → 200 image/png, 8389 bytes (original 48) — still a valid PNG: False
```

Every served `.png`, `.svg`, `.css` and `.js` is corrupted with 8 KB of JavaScript, at 167/167. The
comment at `:1167` (*"appended, so a page that lacks `</body>` still gets it"*) explains the append
and not the guard, which is the shape that invites the guard's removal.

⚠ The `.svg → text/html` one I am **labelling as reasoning, not measurement**: the measured fact is
only that the ctype map has no case. That an SVG served as `text/html` executes script same-origin
with this server — which can then read `/src/<anything>` under the reach documented at `:213-216` —
follows from the same-origin policy, and this project did not drive a browser to confirm it. That is
the standard the `:243` comment sets for itself and I am holding to it.

**Falsifier:** one case per `SERVABLE` suffix asserting `(code, ctype, body)` from a driven `do_GET`,
with the body compared byte-for-byte for the non-`.html` ones.

---

## M7 — MEDIUM — the claim round 1 corrected in four places is still false, in its load-bearing half

`scripts/explainer-serve.py:2113-2117`. Round 1's M4 corrected *"a case dying by RAISING can never be
named by a manifest entry"*. The replacement text says:

> ⚠ MEASURED: a caller re-reading the environment reddens **SIX** cases, and **every one of them
> dies by AssertionError** — `_Forbidden` works by raising. So the single property the previous
> round left genuinely guarded was, by construction, **outside `--mutate .`**

I applied manifest entry 16's own mutation (`:1144`) and read the names:

```
self-test: 160/167 passed — SEVEN red cases
  6 × AssertionError: do_GET read the environment — it must carry, not re-derive
  1 × driving /src/ never consults the environment — the _Forbidden property, RATCHETABLE   ← plain False
```

**Seven, not six — and "every one" is false.** The seventh is the RATCHETABLE case, which reports a
plain `False` and is therefore perfectly attributable. It is the counterexample, and it is the case
the same paragraph goes on to describe as the fix (*"the fix is to convert the raise into a VALUE"*).
So the sentence measures a pre-fix world against a post-fix tree.

**And it was already false when written, not made false by round 1.** `git show 214eb376 --
scripts/explainer-serve.py` adds **zero** lines matching any of the seven case names, so the
population was the same in commit `7915f6ed` where the sentence appears. Round 1's M4 re-read this
very paragraph, corrected its qualitative claim in four places, and left the quantitative premise —
which is the half the conclusion rests on: *"every one dies by AssertionError"* is what makes
*"outside `--mutate .`"* follow.

**fix-induced: no.** **Falsifier:** re-run entry 16's mutation; if the red count is six and no red
case reports a bare name, I am wrong.

---

## L8 — LOW — the debt-retirement comment still says the manifest has 17 entries; it has 25

**fix-induced: yes.** `scripts/check-ratchet-contract.py:381-382`:

> ⟳ 2026-09-16, backlog #122: `scripts/explainer-serve.py` LEAVES this set — it has a manifest now
> (`scripts/mutations/explainer-serve.json`, **17 entries**) …

Measured: `len(json.load(open("scripts/mutations/explainer-serve.json"))) == 25`. Commit `7915f6ed`
wrote 17 when it was true; commit `214eb376` raised it to 25 and did not update the sentence.

⚠ It sits **twenty-five lines below** this in the same constant's comment block (`:356-358`):

> ⚠ NO CASE COUNT IS QUOTED HERE ANY MORE: this line said "Its 63 cases" while the suite ran 91 …
> a number in prose has no owner.

Same file, same comment block, same defect, one round later. (`codex-review.json` is also stale here
— *"9 entries"* at `:375` against 12 on disk — pre-existing, not this branch's.)

**Falsifier:** `grep -c "17 entries" scripts/check-ratchet-contract.py` returns 0 after the fix, and
the count either disappears or is derived.

---

## L9 — LOW — a ratchet is printing an instruction this branch created and did not follow

**fix-induced: yes.** `python3 scripts/check-fixture-variation.py` prints, on the current tree:

```
⭐ explainer-serve.py: `safe_path.root` now varies — delete it from KNOWN_UNVARIED
fixture variation OK — 530 parameter(s) examined … 127 known-unvaried ratcheted
```

Round 1's M3 repair added `safe_path("/../sp-outside.md", _inner)` against a **nested** root
(`git show 214eb376` line `+ lambda: safe_path("/../sp-outside.md", _inner) is None`), which is what
made the parameter vary. `'safe_path.root'` is still pinned in `KNOWN_UNVARIED`
(`scripts/check-fixture-variation.py:220-221`). The gate exits 0, so nothing blocks — but a debt that
has become payable and is not paid is precisely what `widened_debt_drift` refuses in the other
direction two files over.

**Measured repair** (applied to a copy, gate re-run, file restored, md5 verified): delete
`'safe_path.root'` from that tuple →

```
fixture variation OK — 530 parameter(s) examined … 126 known-unvaried ratcheted    rc=0
check-fixture-variation.py --self-test : 67/67 passed
```

**Falsifier:** if removing the pin turns the gate red, I am wrong. It did not.

---

## L10 — LOW — the process layer has zero cases, and `port_busy` is the one round 1 stubbed

`start()`, `stop()`, `status()`'s output, `detach_streams()`, `main()` — every one of these survived:

| mutation | line | result |
|---|---|---|
| `port_busy` inverts its verdict (`== 0` → `!= 0`) | `:888` | **167/167 SURVIVED** |
| `detach_streams` stops redirecting stdout/stderr | `:881-882` | **167/167 SURVIVED** |
| `start()` stops writing the pidfile | `:1257` | **167/167 SURVIVED** |
| `start()` drops the post-fork *"FAIL: nothing is listening"* probe | `:1263-1265` | **167/167 SURVIVED** |
| `start()` drops `os.setsid()` | `:1270` | **167/167 SURVIVED** |
| `ThreadingHTTPServer` → `HTTPServer` (the Codex Medium at `:116`) | `:1272` | **167/167 SURVIVED** |
| `stop()` sends `SIGKILL` instead of `SIGTERM` | `:1284` | **167/167 SURVIVED** |
| `main()`: `--stop` and `--status` swapped | `:2464-2467` | **167/167 SURVIVED** |
| `main()`: `--status` falls through to `start()` | `:2466-2467` | **167/167 SURVIVED** |
| `status()`'s `listening` line prints `yes` unconditionally | `:1293` | **167/167 SURVIVED** |

The pointed pair: round 1's M6 fixed *"`status()` reported success with nothing listening"* by
casing the **exit code** with `port_busy` stubbed in `globals()` — and the real `port_busy` can now
be inverted at 167/167, and the human-readable line it prints can be hardcoded to `yes` at 167/167.
The stub is correct for what M6 asserts; it just means the function that answers the question
`--status` exists to ask is itself unguarded. `detach_streams` is the one with a measured incident
behind it (`:867` — *"MEASURED 2026-08-21, three times in a row"*) and no case.

⚠ `main()` and `start()` are genuinely awkward to case (fork, bind, exec). `port_busy`,
`detach_streams` and `main()`'s routing are not — `main()` can be driven with `sys.argv` patched and
`stop`/`status`/`start` stubbed in `globals()`, which the suite already does for `port_busy`.

---

## L11 — LOW — `_send`'s `Content-Length` VALUE is unasserted

`scripts/explainer-serve.py:1069`, case at `:2301`. The case asserts header **names**:
`{"content-type", "content-length"} <= {k for k, _ in _sent_headers()}`. Measured:

| mutation | result |
|---|---|
| **delete** the `Content-Length` header | 166/167 — **killed** |
| `str(len(body))` → `str(len(body) + 1)` | **167/167 SURVIVED** |

The case name (*"still carries the headers it is supposed to"*) is honest about being a presence
test. The failure mode that matters is a wrong value, which truncates or hangs a real client.
One-character fix: compare `dict(_sent_headers())["content-length"] == str(len(b"x"))`.

## L12 — LOW — "orders newest first" passes on a name-sort

`scripts/explainer-serve.py:1354`, fixture at `:1313-1316`. `key=lambda p: p.stat().st_mtime` →
`key=lambda p: p.name` survives **167/167**: `a.html` is older *and* sorts first, so reverse-by-name
and reverse-by-mtime give the same answer, and the two other `/latest` fixtures agree by accident
too. The case's name is about mtime. Rename one fixture so the two orders disagree
(e.g. `z.html` as the older file) and the case discriminates.

---

## What I checked and found SOUND — stated because a review that only reports defects is not a measurement

- **Entry 13's contested repair is honest.** Under its mutation the case it names,
  *"safe_path refuses a traversal to a SERVABLE file that really exists outside the root"*, goes red
  **by a plain `False`** — attributable, and red for containment rather than for the suffix
  allowlist. Round 1's M3 fix holds. Entries 11, 23 and 24 each attribute to exactly one red case.
- **S2 (state leakage) is genuinely gone.** Three consecutive in-process `_self_test()` runs:
  167/167 each. `subprocess.run` and `port_busy` `is`-identical to the originals afterwards;
  `EXPLAINER_DOCS_ROOT` unset. Under `HOME=$(mktemp -d)/.home`: 167/167, **no** files created under
  that `HOME`, `git status --short` empty.
- **Bookkeeping is correct.** `EXPECTED_MUTATIONS["scripts/explainer-serve.py"] == 25`
  (`check-plan-code.py:852`); the declared sum over 46 files is **668**; the docstring at `:66`
  declares **167 cases** and `check-selftest-counts.py` verifies it by running it;
  `explainer-serve.py` is out of `WIDENED_MANIFEST_DEBT`. Only the prose count in L8 is wrong.
- **Gates green — ten, all rc=0**, which is the set my brief names minus the full `--mutate .`
  sweep below: `explainer-serve.py --self-test` 167/167 **and again under a non-existent `$HOME`**;
  `check-plan-code.py --self-test` 128/128; `check-ratchet-contract.py --self-test` 41/41 **and its bare run**
  (36 guards, `ratchet contract OK`); `check-selftest-counts.py` (39 scripts, each verified by
  running it); `check-docs.py`; `check-fixture-variation.py` (with the L9 nudge);
  `gen-backlog-page.py --self-test` 165/165; `gen-dashboard.py --self-test` 325/325;
  `check-review-rounds.py --self-test` 29/29; `check-anchors.py --self-test` 15/15.
- **No defect found in shipped behaviour.** Every finding above is *"nothing would notice if this
  broke"*, not *"this is broken"*. The code is correct today.

⚠ **One gate is RED and it is supposed to be, until the coordinator half lands.** With only this
file present, `python3 scripts/check-review-rounds.py` exits **1**:

```
✗ seed-explainer-serve-manifest round 2: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
```

That is the gate doing its job. **I am the Codex stand-in, so round 2 needs its own
`REVIEW GAP: codex` line** — round 1's line does not carry forward to round 2, and writing it is the
coordinator's step, not mine. Do not read this red as a defect in the branch, and do not let it be
closed by anything other than a written reason.

## Where the 58 survivors sit — the shape, not the list

Every mutation I applied, bucketed by the layer it lands in. Survivors + kills = 73; entries = 25.

| layer | survived | killed | manifest entries |
|---|---|---|---|
| `_regenerate` (r1's H2 component) | **11** | 0 | 2 |
| `do_POST` preamble | **6** | 0 | 0 |
| `do_GET` routing, ctype, `_send`, `/_stale`, `/src/` serving | **14** | 2 | 3 |
| process layer (`start`/`stop`/`status`/`detach_streams`/`main`/`port_busy`/`read_pid`) | **13** | 0 | 3 |
| pure helpers (`md_*`, `src_root*`, `safe_path`, `resolve_page`, `explainers`, `revision`) | 14 | **13** | 17 |
| **total** | **58** | **15** | **25** |

**Thirteen of the fifteen kills are in the pure-helper layer, and so are 17 of the 25 entries.** That
is round 1's finding — *"the 17 entries sat almost entirely in the pure-helper layer"* — still true
at 25 entries, and it now has a number: **the four non-helper layers account for 44 of the 58
survivors while holding 8 of the 25 entries, and two of those layers have no entry or no kill at
all.** The `_regenerate` and process rows are the ones to read: 24 survivors, zero kills, five
entries between them.

⚠ **The branch does not claim completeness and this is not a demand for 58 entries.** A 25-entry
manifest over 2,472 lines cannot be complete. The finding is about **where** the gap is: the
subsystem carrying the security argument, the subprocess execution, and the request preamble.

## Evidence

`python3 scripts/check-plan-code.py --mutate .` — **run to completion against this tree**, final
line read rather than inferred from an exit code:

```
OK — delivered scripts mutated: 46 file(s), 668 mutation(s), 668 killed,
     668 attributed to the case each names, 0 survivor(s)
```

Every file's control was proved green first (`[41/46] re-control scripts/explainer-serve.py` among
the 46 re-controls), so no verdict here is an artefact of a red control. **All 25 entries attribute.**
⚠ That is the ratchet's claim and it is true — *attribution is not the same as guarding what the
entry's name says*, which is H2.

73 plausible mutations applied and measured; 58 survived at 167/167, 15 killed. Four batches, tree
restored and md5-verified after each (`bee6d8d3befa1df111233b87f2a65b36`); `git status --short` empty
at start and end. No port bound, no process signalled, no scratch file inside the repo.

## Q4 / Q5

**Convergence: NOT reached.** Two High, one fix-induced on `manifest-attribution`.

**Thrashing: not armed, and the pre-commitment needs a human call.** The rule needs *two consecutive
rounds carrying findings caused by the previous round's fix in one component*. Round 1 had S3 in
`manifest-attribution`; round 2 has H2 in `manifest-attribution` — **that is two consecutive
rounds**, which arms the condition on the letter of it. But H2 is a *different entry* on its *first*
attempt, with a repair that is measured green rather than hypothesised, and round 1's prescribed
remedy ("delete the entry") addresses a third attempt at **one** entry, which this is not. My read:
the arming condition is met and the remedy it names does not fit, so this is a *"prose floor or
thrash?"* question for the coordinator rather than one I should answer inside a review half. I have
stated both halves rather than picking the one that lets the round close.

**Pre-committed for round 3:** if a round-3 finding shows that the H2 repair above — the stubbed
`start()` drive — guards something other than what it names, that is a third consecutive
`manifest-attribution` defect and entry 17 should be **deleted**, not re-pointed, on round 1's own
reasoning: an entry that cannot find an honest case to name is telling you the case does not exist.
