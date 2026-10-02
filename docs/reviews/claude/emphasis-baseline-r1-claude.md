# emphasis-baseline r1 — Claude adversarial half

**Subject:** branch `explainer-emphasis-baseline`, `git diff master...HEAD`
**HEAD at start:** `22baf58496ef55f9da26471312f2fa3193d9f4e2`
**HEAD at end:** `22baf58496ef55f9da26471312f2fa3193d9f4e2` — unchanged, the round stands.

**Tree hygiene note (not a finding against the change).** At 12:43 the working tree carried an
uncommitted edit to the file under review — `BASELINE_CSS` with the `--fg2` arm severed, which is
mutation entry 2 applied in place. It reverted seconds later. The concurrent Codex reviewer is
mutating the live tree rather than a copy; `docs/plugins.md` → *Running agents concurrently* names
this hazard. **No measurement in this document was taken from the working tree.** Everything below
ran against `git archive 22baf584` extracted to a scratchpad, or against isolated copies of it.
The one self-test I ran in the real repo (`210/210`) was re-run in the pristine extract and agrees.

---

## Blocking 1 — the suite passes 210/210 with the entire feature severed at its call site, and `do_GET` **is** drivable · Structural

**Premise.** `scripts/explainer-serve.py:1015-1017`:

> `do_GET`'s CALL to this function is still unreachable by any case: driving it needs a bound
> server, and this suite deliberately binds no port. What is covered is that `decorate_html`
> appends both; what is not is that `do_GET` calls it.

**Measurement A — sever the call site at `scripts/explainer-serve.py:1279`** (`body = decorate_html(body)` → `body = body`), in a copy:

```
-- existing suite on the severed tree --
self-test: 210/210 passed
```

Every named case stays green while the emphasis baseline reaches **no page**, the live-reload
client reaches **no page**, and the branch's entire user-visible effect is gone. This is the
wiring class from `docs/reviews/architecture-review-2026-10-01.md`, reproduced inside the fix for
the wiring class — which the docstring predicts, and then declines to close.

**Measurement B — the premise for declining is false. `do_GET` needs no port and no socket.**
`Handler.__new__` plus a `BytesIO` for `wfile` drives the real handler end to end:

```python
h = es.Handler.__new__(es.Handler)
h.path = "/p.html"; h.wfile = io.BytesIO(); h.rfile = io.BytesIO(b"")
h.requestline = "GET /p.html HTTP/1.1"; h.request_version = "HTTP/1.1"; h.command = "GET"
h.client_address = ("127.0.0.1", 0); h.server = None; h.close_connection = True
h.log_message = lambda *a, **k: None
h.do_GET()
```

Nothing in `_send` (`:1178-1185`) touches the socket — it calls `send_response`, `send_header`,
`end_headers`, `self.wfile.write`, all of which the base class routes through `wfile`. Run on the
shipped tree and on the severed tree:

```
########## shipped tree ##########
  ok   do_GET SENDS the emphasis baseline (not merely composes it)
  ok   do_GET SENDS the live-reload client
  ok   do_GET still sends the page's own bytes
  ok   Content-Length matches the decorated body
ALL GREEN

########## call site severed (body = body) ##########
  FAIL do_GET SENDS the emphasis baseline (not merely composes it)
  FAIL do_GET SENDS the live-reload client
  ok   do_GET still sends the page's own bytes
  ok   Content-Length matches the decorated body
2 RED
```

**Measurement C — the manifest has no entry for the call site, on either side.** Querying both
manifests for any entry whose edits touch `RELOAD_JS.encode` or `decorate_html`:

```
=== master manifest: any entry touching the do_GET append? ===
(nothing)
=== HEAD manifest: same query ===
the emphasis baseline is dropped from what the server appends...
   edits: [['    return body + BASELINE_CSS.encode() + RELOAD_JS.encode()',
            '    return body + RELOAD_JS.encode()']]
```

The one new composition entry severs the body of `decorate_html`, never its caller. So the hole is
exactly where ADR-0014 says to look, and it swallows the live-reload client too — a pre-existing
gap this branch had the opportunity to close and instead documented as unclosable.

**Measurement D (added after Codex filed) — the technique is already in this same file, 1,170
lines below the docstring that denies it.** `scripts/explainer-serve.py:2185-2188`:

```python
# ⚠ NO PORT IS BOUND, and none is needed: `do_GET` touches the socket only through
# `self._send`, so an instance-level stub captures the whole reply. `object.__new__`
# skips `BaseHTTPRequestHandler.__init__`, which is what would want a socket.
def _drive_src(url_path: str, env_value):
    """GET `url_path` through the REAL do_GET. Returns (code, body, env_reads)."""
```

So `:1016`'s *"driving it needs a bound server, and this suite deliberately binds no port"* is
contradicted by a comment in its own file that says, in capitals, the opposite — and nine existing
cases (`:2236-2307`) already drive `do_GET` through it. Codex found this independently; we agree.
This moves the finding from *an option the author did not find* to *a facility the author already
owns*, which is why it stays Blocking.

**What I can add on top of Codex's half — `_drive_src` cannot be reused as-is for this case, and
the difference is the reason it did not get used.** Two gaps:

1. **It stubs `_send`** (`h._send = lambda code, body, ctype: got.update(...)`), so it captures the
   argument handed to `_send` and never exercises `_send` itself. That is right for the `/src/`
   cases it was built for, but it means a `Content-Length` or header regression is invisible to
   it. My `BytesIO` variant on `wfile` goes through the real `_send` and does catch that — it is
   the strictly stronger driver, and the fourth check in Measurement B is the one `_drive_src`
   structurally cannot make.
2. **`ROOT` must be rebound for the static-file branch.** `_drive_src` exercises the `/src/` arm,
   which resolves through `src_root()` and never reads `ROOT`. The decoration lives on the
   *static page* arm at `:1277-1279`, which goes through `resolve_page(path, ROOT)` against the
   module global. A case for it must point `ROOT` at a sandbox holding a real `.html` file
   (`es.ROOT = tmp` in Measurement B) and restore it afterwards, exactly as the neighbouring cases
   do with their own tmp roots. Without that rebind the request 404s and the case passes
   vacuously — a forced-choice test that cannot fail.

**Why Blocking.** The docstring is the honest-accounting artefact this repo relies on, and its
load-bearing clause — *driving it needs a bound server* — is false, refuted in fifteen lines. The
"one layer tested, one layer owed" framing therefore understates the state: the owed layer is
**drivable today**, so what exists is not an accepted debt but an unexamined one. A reader who
trusts the docstring will not retry, which is how this class survives.

**Proposed fix.** Add the socket-less driver above as a case (it belongs beside the existing
`decorate_html` trio at `:1715-1720`), and add a manifest entry severing `:1279` whose `expect`
names it. Then rewrite `:1015-1017` to say what is actually owed — a real request *parse* path, if
anything — rather than claiming the call is undrivable. If the author prefers not to reach into
`__new__`, a `ThreadingHTTPServer` on `127.0.0.1:0` in a daemon thread is a second option, but it
is not needed: the above binds nothing.

---

## High 2 — the cascade safety argument is wrong at equal specificity; 44.3% of bold elements change colour · Structural

**Premise.** `scripts/explainer-serve.py:980-984`:

> ⚠ THE CASCADE IS THE SAFETY, NOT A CONVENIENCE. `b,strong` is specificity (0,0,1), the lowest a
> rule can carry, so ANY page rule — `.card b{}` at (0,1,1) — still wins and deliberate per-page
> design is untouched. […] this can soften a page, and it cannot break one.

Specificity is only half of the cascade. `BASELINE_CSS` is **appended** (`:1018`), so it is later
in document order than any `<style>` in the page head. At **equal** specificity, later wins.

**Measurement — Chromium, `node_modules/playwright`:**

```
CHANGED  bare b{} page rule, equal specificity (0,0,1)    rgb(255, 0, 0) -> rgb(136, 136, 136)
  same    class rule .card b{} (0,1,1)                     rgb(255, 0, 0) -> rgb(255, 0, 0)
  same    descendant main b{} (0,0,2)                      rgb(255, 0, 0) -> rgb(255, 0, 0)
  same    inline style attribute                           rgb(255, 0, 0) -> rgb(255, 0, 0)
```

The example the comment chose (`.card b{}`) is one of the cases that *does* hold. The case it did
not choose is the one the corpus is full of. Parsing every `<style>` in the 62 served pages for a
selector-list member that is exactly `b` or `strong` carrying a `color` declaration:

```
pages with a bare b/strong colour rule: 47
   ('2026-08-17-brief-backlog-36.html', 'b', 'font-weight:600;color:var(--strong)')
   ('2026-08-17-brief-brief-deploy-v7.html', 'b', 'font-weight:600;color:var(--strong)')
   …
```

**47 of 62 pages.** Measuring every visible `b`/`strong` on all 62 pages in both colour schemes,
before and after appending the rule — 13,614 element/scheme observations:

```
bold elements measured (page x scheme x element): 13614
colour changed by baseline: 6036 (44.3%)
```

**Why High and not Blocking.** Overriding `color:var(--strong)` on those pages is plausibly the
*intent* — `--strong` is what the complaint was about. The defect is that the comment asserts the
opposite ("deliberate per-page design is untouched", "it cannot break one") and that assertion is
what a future reader will reason from. A change whose actual blast radius is 44% of bold text,
documented as touching none of it, is a trap for the next person, and it is the premise Finding 3
then falls through.

**Proposed fix.** Replace the claim with the measured rule: *a page rule wins only at specificity
above (0,0,1); the 47 pages whose `b`/`strong` colour is set at (0,0,1) are deliberately
overridden.* If per-page design really must survive, the mechanism is `:where(b,strong)`
(specificity (0,0,0)) — which loses to every author rule including equal-specificity ones, and is
a one-token change worth measuring against the same corpus.

---

## High 3 — the accepted rule fails the author's own acceptance criterion, and that test was never run on it · Structural

**Premise.** `scripts/explainer-serve.py:986-991`:

> `color-mix(...)` WAS TRIED AS THAT LAST ARM […] AND IS REJECTED — MEASURED, NOT ARGUED. It
> reaches them, and on `2026-08-12-explanation-absence-protection-enforced` it drove one bold to
> **4.37:1** against the page background, under WCAG AA's 4.5.

A variant was killed by a WCAG AA measurement on one page. The accepted variant was never put
through that test. Running it over the whole corpus, every visible `b`/`strong`, both schemes,
alpha composited over the nearest opaque ancestor background:

```
*** crossed AA 4.5:1 downward (was OK, now NOT) : 56 ***
  5.23 -> 2.21 [light] 2026-09-27-topic-memory-recall-taxonomy.html :: "You asked: if you find somet"
  5.23 -> 2.21 [light] 2026-09-27-topic-memory-recall-taxonomy.html :: "the gate is alignment, not p"
  …
crossed 3.0:1 downward (large-text AA): 238
below AA before: 303  after: 351

worst post-change ratios among CHANGED elements:
  1.15 (was 2.41) [dark] 2026-09-27-topic-memory-recall-taxonomy.html :: "You asked: if you find somet"
```

**1.15:1 is effectively invisible text.** By the exact criterion that killed `color-mix` at 4.37,
the accepted rule fails 56 times and bottoms out four times lower.

**The rejection of `color-mix` was nevertheless correct, and more strongly than stated.** Holding
all three variants to the same corpus:

```
variant                                   min  <4.5  <3.0  newly<4.5
today (no rule)                             1.00   303    84          0
ACCEPTED var(--emph,var(--fg2,inherit))     1.00   351   322         56
REJECTED color-mix 78%                      1.00  5886  5675       5656
```

So the decision stands; the *evidence given for it* was a single page when a corpus run was
available and decisive. The asymmetry is the finding: one variant got a corpus-free single-page AA
test and died, the other got no AA test at all and shipped.

**The stated mechanism is also the wrong way round.** `:989-991` argues `--fg2` "is a ROOT token,
so it dims relative to the page and cannot compound". True, and that is precisely what causes the
1.15:1 — being root-relative makes it **blind to the local background**. On
`2026-09-27-topic-memory-recall-taxonomy.html` the page defines `--fg2: var(--ink-soft, #4a5563)`
with dark `--ink-soft: #c8c5cf`, while a card sets `--bg2: var(--card, #fff)`; a light-grey root
token lands on a white card. Root-ness is a trade — immunity to compounding bought with
insensitivity to context — and the comment presents only the half that favours the choice.

**Why High and not Blocking.** Nothing is *more* broken than before on a page-count basis (303 →
351 below AA), the direction is the one the user asked for, and the worst cases are concentrated
on a handful of pages. But 56 elements crossing a line the author set themselves, discovered by
the reviewer rather than the author, is not a Medium.

**Proposed fix.** Run the corpus measurement (script pattern above, ~40 lines of Playwright) and
either (a) accept with the numbers recorded in the comment, replacing the one-page 4.37 anecdote
with the corpus table, or (b) scope the rule away from elements on non-root backgrounds. Minimum:
fix `:989-991` to state the trade rather than only its favourable half.

---

## Medium 4 — case 8's expression constrains neither specificity nor "page rules win" · Structural

**Premise.** `scripts/explainer-serve.py:1731-1732`:

```python
case("the baseline selector is BARE b,strong — specificity (0,0,1), so page rules win",
     lambda: "b,strong{" in BASELINE_CSS and "." not in BASELINE_CSS.split("{")[0])
```

`BASELINE_CSS.split("{")[0]` is `'\n<style>b,strong'`. The predicate asks only whether a period
appears before the first `{`. Feeding it realistic alternatives:

```
PASS  shipped                               prefix='\n<style>b,strong'
PASS  !important (defeats ALL page rules)   prefix='\n<style>b,strong'
PASS  ID selector #main b,strong (1,0,1)    prefix='\n<style>#main b,strong'
PASS  attribute [data-x] b,strong (0,1,1)   prefix='\n<style>[data-x] b,strong'
PASS  descendant main b,strong (0,0,2)      prefix='\n<style>main b,strong'
PASS  second rule adds a class              prefix='\n<style>b,strong'
FAIL  class prepended (.card b,strong)      prefix='\n<style>.card b,strong'
FAIL  cosmetic respacing 'b, strong {'      prefix='\n<style>b, strong '
```

It catches exactly one way of raising specificity — a leading class — and misses an ID, an
attribute selector, a descendant combinator, a class in any rule after the first, and
`!important`, which is the one edit that would defeat *every* page rule at *every* specificity and
sits inside the braces where the predicate cannot see it. **The regression the case is named for
is the one it cannot observe.** It also goes red on a whitespace-only reformat, so what it most
reliably detects is cosmetic.

Per the mandate's "name any case for which the honest answer is nothing would": every other new
case has a real falsifier (1 and 2 are proved by the manifest entries below; 3 catches a prepend
rather than an append; 4, 5 and 7 each pin a named token). Case 8 is the one whose description and
predicate are about different things — and, per Finding 2, the property it claims is false anyway.

**Proposed fix.** Assert the thing: `BASELINE_CSS.count("{") == 2` (one rule, one style element),
`"!important" not in BASELINE_CSS`, and a selector equality check after normalising whitespace —
`BASELINE_CSS.split("{")[0].replace("<style>","").split() == ["b,strong"]` — or drop the
specificity clause from the description and keep it as the "one bare rule" check it actually is.

---

## Medium 5 — `/src/` serves `text/html` containing `<strong>` and bypasses `decorate_html` · Transitional

**Premise.** `do_GET` has three `text/html` exits: `:1190` (`index_html`), `:1270`
(`source_shell`), and `:1279` (a page file). Only `:1279` is decorated. Driving the renderer
directly:

```
index_html emits <b>/<strong>?  False
source_shell(.md) emits <strong>? True
  sample: ['<body>\n', '<b>x.md', '<strong>bold text']
```

`source_shell` renders `.md` through `md_render`, so `**bold**` becomes `<strong>`, and its own
header is a `<b>`. Those are served as `text/html` and get neither the baseline nor the live-reload
client. The comment at `:960-962` says "every page gets it, including the ones already on disk".

**Why Medium / Transitional.** The exclusion is inherited from RELOAD_JS and is defensible for a
source viewer, but the baseline's stated goal is uniform emphasis across what the server serves,
and `index_html` is clean only by accident (it happens to emit no bold today — nothing holds it
there). Transitional because the right fix may be to decorate at `_send` rather than per branch.

**Proposed fix.** Either move the decoration into `_send` keyed on `ctype.startswith("text/html")`
— which closes all three exits at once and makes Finding 1's case cover them — or state in the
comment that `/src/` is deliberately outside the contract.

---

## Low 6 — the fallback cases do not constrain arm **order** · Transitional

`:1723-1728` assert `"var(--emph,"`, `"var(--fg2,"` and `"inherit"` are each present somewhere in
the string. Reordering to `var(--fg2, var(--emph, inherit))` keeps all three green while inverting
the override semantics — a page that sets `--emph` would no longer beat `--fg2`, and `--emph` is
documented at `:982` as *the* override hook. The arm order is the contract; membership is not.

**Proposed fix.** One case asserting the composed string: `"var(--emph, var(--fg2, inherit))" in
BASELINE_CSS`. It subsumes 4, 5 and 6 and is the thing mutation entry 2 already targets.

---

## Low 7 — the insertion orphans the RELOAD_JS comment · Transitional

`:955-965` is the live-reload client's explanatory block, ending "live reload is a property of
being SERVED." `:966` begins "The shared emphasis baseline…" with **no blank line between them**,
so two distinct comment blocks are now one, positionally documenting `BASELINE_CSS`. `RELOAD_JS`
itself (`:1021`) is left with no comment above it at all — its documentation is now 66 lines up,
above a different constant and a function. In a file this comment-dense that is a real navigation
cost.

**Proposed fix.** A blank line at `:966`, and move the RELOAD_JS block down to sit above
`RELOAD_JS` — or add a one-line pointer there.

---

## Verified sound — things I tried to refute and could not

These were attacked and held. Recording them so the next round does not re-spend the budget.

- **The 56-of-62 claim is exactly right.** Over `docs/explainers/*.html` excluding
  `.fragment.html` — 58 tracked at `22baf584` plus 4 gitignored derived pages — `62` pages, `56`
  define `--fg2:`, `0` define `--emph:`. The six without it are listed by the same command.
- **Both new mutation entries die via exactly the case they name, and nothing else.** Applied
  individually to isolated copies:
  ```
  === mut1 self-test ===   [FAIL] decorate_html appends the emphasis baseline to an HTML body
                           self-test: 209/210 passed
  === mut2 self-test ===   [FAIL] ...then --fg2, the softer token 56 of 62 pages already define
                           self-test: 209/210 passed
  ```
  209/210 in both cases — one casualty each, the named one. No unmanifested hole here.
- **The `file://` contract holds.** `BASELINE_CSS` and `decorate_html` appear nowhere in the tree
  outside `scripts/explainer-serve.py`, except the mutation manifest and a comment in
  `check-plan-code.py:3881`. The only call is `:1279`. No generator imports either; nothing writes
  the baseline to disk. (A browser's "Save Page As" of a *served* page would capture the injected
  style — but that is equally true of RELOAD_JS and is the contract as written.)
- **The fallback chain degrades safely.** `--fg2` set to an empty value or to a non-colour
  (`12px`) both fall through to the inherited colour rather than to an initial black/white:
  ```
    same    --fg2 defined as an EMPTY value       rgb(0, 0, 255) -> rgb(0, 0, 255)
    same    --fg2 defined as a NON-COLOR (12px)   rgb(0, 0, 255) -> rgb(0, 0, 255)
  ```
- **`inherit` genuinely reproduces today's behaviour.** The UA stylesheet sets `font-weight` on
  `b`/`strong` and not `color`, so today's computed colour is the inherited one; `color:inherit`
  computes the same. Confirmed: a page with only `p{color:green}` is unchanged.
- **The `#45423d` / `#bdb9b2` figures at `:977-978` are accurate.** On
  `2026-10-02-topic-recent-prs-found-solved.html`, `--fg2:#45423d` is in the light block and
  `--fg2:#bdb9b2` in the `prefers-color-scheme:dark` block; `#1b1a18` and `#e8e6e2` are that
  page's light and dark `--fg`. "against body X" means the body *text* colour, which is the right
  comparison for "softer than its surroundings". I checked this expecting the pairing to be
  inverted; it is not.
- **The manifest diff is pure reformatting, as stated.** Parsed both sides: 46 → 48 entries, the
  46 pre-existing entries compare equal as objects **with order unchanged** (`kept == oe` → True).
- **Counts reconcile.** In the real repo at `22baf584`: `explainer-serve.py --self-test` →
  `210/210`; `check-plan-code.py --self-test` → `131/131`; `check-selftest-counts.py` → "50
  script(s) declare a count, every one verified by running it". `EXPECTED_MUTATIONS` 48 equals the
  48 entries actually in the manifest; the declared sum 1180 is asserted by a green case.

---

## Cross-check against the Codex half

Added after Codex filed, at the coordinator's request. I had not seen its document; these are my
own measurements against its four findings.

- **Its (1) — `do_GET` can drop the injection with the suite green, technique already in-file.**
  **Independently confirmed**, and it is my Blocking 1 — I reached it before being told, by
  writing a driver from scratch, and reproduced `210/210` on the severed tree. **I grade it
  Blocking where Codex graded it High**, because the branch's docstring makes a positive claim of
  impossibility that its own file refutes in capitals; that is worse than an untested path. See
  Measurement D above for the two things `_drive_src` cannot do here.

- **Its (2) — bold inside a link loses the link colour, "4 real occurrences across 4 pages".
  ⛔ I DISAGREE WITH THE COUNT, in both halves.** Measuring every `a b` / `a strong` on all 62
  pages in both schemes:

  ```
  a b / a strong whose colour CHANGED at all: 4
  distinct pages: 2
    [light] 2026-09-23-topic-pr-336-338.html   :: "revised"  rgb(122,59,18)  -> rgb(74,85,99)   (link rgb(122,59,18))
    [light] 2026-09-24-brief-velocity-ledger.html :: "Development velocity — the mig"  rgb(38,36,31) -> rgb(96,92,85) (link rgb(138,90,43))
    [dark]  2026-09-23-topic-pr-336-338.html   :: "revised"  rgb(232,160,106) -> rgb(200,197,207) (link rgb(232,160,106))
    [dark]  2026-09-24-brief-velocity-ledger.html :: "Development velocity — the mig"  rgb(234,230,222) -> rgb(164,160,153) (link rgb(203,154,104))
  ```

  **4 observations, but 2 pages — and the same single element counted twice (light + dark).** The
  "4 pages" figure does not survive. Worse for the finding's substance: only
  `2026-09-23-topic-pr-336-338.html` actually *loses a link colour* — its bold matched the link
  (`rgb(122,59,18)`) before and does not after. On `2026-09-24-brief-velocity-ledger.html` the
  bold was **already not the link colour** (`rgb(38,36,31)` vs link `rgb(138,90,43)`), so nothing
  is lost; it is softened like every other bold on the page, which is the intended effect.
  Restricting to the real failure — bold that carried the link colour and stops:

  ```
  bold-inside-link that LOSES the link colour: 2
  distinct pages: 1
  ```

  **One element, on one page, in two schemes.** The finding is real and I would keep it, but at
  **Low**, not Medium.

  ⚠ **And I have a reservation about its proposed fix, `a b,a strong{color:inherit}`.** It works
  mechanically — (0,0,2) beats the baseline's (0,0,1) — but it is not confined to the defect. It
  would also force the `velocity-ledger` bold *to* the link colour, which is a change to a page
  that is correct today, and by Finding 2's mechanism it beats the bare `b{}` rules on the 47
  pages that have them wherever those sit inside a link. A fix scoped to one element on one page
  should not be a corpus-wide selector; `a b{color:inherit}` deserves the same corpus measurement
  the baseline itself still needs.

- **Its (3) — the "BARE b,strong" case does not test bare.** **Independently confirmed**; it is my
  Medium 4. **I grade it Medium where Codex graded it Low**, on the strength of the enumeration in
  that section: the predicate admits `!important`, an ID, an attribute selector and a descendant
  combinator, i.e. it is blind to every realistic way of defeating the property it is named for,
  and it false-fires on whitespace. A case whose most reliable trigger is cosmetic is worse than
  no case.

- **Its (4) — the new comment block splits RELOAD_JS's comment from RELOAD_JS.** **Independently
  confirmed**; my Low 7, same severity. I add the detail that there is no blank line at `:966`, so
  the two blocks are lexically merged, and that `RELOAD_JS` at `:1021` is left with no comment at
  all.

**Findings of mine that Codex did not report:** Finding 2 (the cascade claim is false at equal
specificity; 47 pages, 44.3% of bold elements), Finding 3 (56 elements cross WCAG AA downward,
worst 1.15:1, and the accepted variant was never put through the test that killed `color-mix`),
Finding 5 (`/src/` serves `text/html` with `<strong>` and bypasses the decoration), and Finding 6
(the fallback cases do not constrain arm order).

---

## Could Not Measure

- **Nothing material.** Two guards (`check-plan-code.py --self-test`,
  `check-selftest-counts.py`) initially reported CANNOT RUN against my scratchpad extract because
  `git archive` omits `node_modules/typescript`. That is an artefact of my isolation, not of the
  change: both were re-run in the real repo at the same SHA and are green (quoted above). I am
  recording it rather than dropping it, since a CANNOT RUN I resolved is still a CANNOT RUN that
  happened.
- **`tools/partial-sweep.py` was not run** — the coordinator corrected its path after I had filed; it lives outside the repo at `~/.claude/projects/.../tools/partial-sweep.py`. Not consulted; no finding here depends on it.
- **Rendering was measured in Chromium only.** The cascade and `var()` fallback semantics asserted
  here are specified behaviour, but the contrast figures are one engine's. Safari/Firefox
  unmeasured.
- **Contrast was computed against the nearest opaque ancestor background.** Where bold text sits
  over a gradient or image, that number is an approximation.

---

NOT CONVERGED: 1 Blocking · 2 High · 2 Medium · 2 Low
