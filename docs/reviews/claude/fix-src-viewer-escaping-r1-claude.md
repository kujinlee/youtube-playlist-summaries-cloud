# Round 1 — Claude half — `fix-src-viewer-escaping` @ `42a84e6d`

**VERDICT: NOT CONVERGED.** Seven findings — one High, five Medium, one Low — all outside backlog
#129 and #130. The headline is that **fix 1 moves the bypass rather than closing it** — `/secret%252eenv`
serves `secret.env.html` on this branch and returned `None` on master — and that **`rel` was not the
only filesystem-derived value reaching HTML unescaped in this file**; `index_html` has the identical
defect twelve lines below the one that was fixed.

Both of Codex's findings are real and both fixes are in the right *place*. Neither is complete.

---

## High 1 — r1's Codex half reviewed the PARENT commit; nothing on this branch has had a Codex pass

`docs/reviews/verdicts/fix-src-viewer-escaping-r1-codex.verdict.json:8,:12` records

```json
"head": "32c56bfa370fd45ef294db80d2b6aa533ae522bc",
"review": "explainer-serve-manifest-retro-codex.md",
```

`32c56bfa` is **master**, the parent of `42a84e6d`. The `review` field names a stem that is not on
disk — the artifact was filed as `fix-src-viewer-escaping-r1-codex.md`. So the Codex half of round 1
is a review of the code *before* the fixes, filed as round 1 *of the fixes*, and it is the only
adversarial pass either fix has had from that side.

`scripts/check-review-rounds.py` cannot see this. `verdict_problems` (`:141-158`) returns early on
`if rec.get("gate_ran"): continue` — it only ever asks whether a review is filed for a gate that did
**not** run. A verdict that ran, against a different commit, naming a review file that does not
exist, produces zero problems. Measured: `check-review-rounds.py` exits 0 on this tree.

This matters beyond bookkeeping. `docs/plugins.md` requires rounds 2+ to **alternate** precisely
because *"a concurrent pair never reviews the FIXES, and that is where both of 2026-09-13's surviving
defects were."* Four of the six findings below are in the fixes themselves. The commit message is
candid that the Codex run was retroactive; the two artifacts a gate and a later reader will consult
are not.

**Fix:** a header line in the review doc saying which commit it reviewed, and a Codex half in round 2
run against the branch. **Falsifier:** a verdict whose `head` is `42a84e6d` or later.

---

## Medium 1 — the encoded-dot fix relocates the bypass one encoding level up, and is a regression there

`scripts/explainer-serve.py:772-776`

`bare` is now decoded, but it is then handed back to `safe_path`, **which decodes again**
(`:277`). The direct attempt (`:760`) is decoded once; the fallback attempt is now decoded twice.
The classifier and the resolver still disagree about what the request says — at `%25` instead of
`%2e`.

Measured, end-to-end through the real `do_GET` with `secret.env.html` in the root (no port bound;
`object.__new__(Handler)` with `_send` stubbed, the suite's own driver):

```text
                        master 32c56bfa      branch 42a84e6d
GET /secret.env         404                  404
GET /secret%2eenv       200  THE SECRET PAGE  404            <- Codex's finding, fixed
GET /secret%252eenv     404                  200  THE SECRET PAGE   <- NEW
```

`/notes%252emd` behaves the same way. Note the middle and bottom rows are *inverted* between the two
columns: master refused the double-encoded spelling and the branch accepts it, so this is a
regression introduced by the fix, not a pre-existing gap it failed to reach.

**Bounded honestly:** this does not expose a non-servable file. The fallback appends `.html`
unconditionally and `safe_path`'s `SERVABLE` check still holds, so the reachable set is unchanged.
What is defeated is the rule the branch exists to enforce — *"it HAD an extension; the fallback is
not a second chance."*

I also measured `%2E` (closed), `%2e%65nv` (closed), `%25252e` (closed — it decodes to `%252e`,
which is not a dot), an encoded slash, a trailing dot, and the U+2024 one-dot-leader lookalike (all
closed, all correctly). **Double-encoding is the only surviving spelling**, which is what makes the
root cause a double *decode* rather than a missing spelling.

**Repair, measured:**

```python
alt = safe_path(urllib.parse.quote(bare) + ".html", root)
```

Re-encoding makes `safe_path` decode exactly once, so the fallback sees the same string the
classifier judged. With it applied: every spelling above returns `None`, the `/plain` extensionless
control still resolves to `plain.html`, and the suite is **199/199**.

**Falsifier:** add `resolve_page("/secret%252eenv", _l7) is None` to the encoded-twin case. It is red
today.

---

## Medium 2 — `rel` was not the only filesystem-derived value reaching HTML unescaped in this file

`scripts/explainer-serve.py:783`

```python
rows.append(f'<li><a href="/{urllib.parse.quote(p.name)}">{p.name}</a>'
```

The **href** is percent-encoded. The **link text** is not. `index_html` is one of exactly two
`text/html` producers in the file (`:1104` and `:1184`) — the other is the one that was fixed.

Measured end-to-end, same driver, with a file named
`2026-09-16-brief-evil<img src=x onerror=alert(1)>.html` in the explainers root:

```text
GET / (index) -> 200 text/html; charset=utf-8
   raw payload present in the page: True
   escaped anywhere:                False
```

The quoted href is what makes this easy to read past: the line *looks* like it handles a hostile
name, and it handles the half that does not matter here.

**Reachable by the same route the branch argues for `/src/`.** `scripts/brief-compose.py:866` builds
the output filename as `ROOT / f"{date}-brief-{a.slug}.html"` with **no validation of `--slug`** —
grepped, there is none anywhere in that file. A slug taken from a topic, a PR title or a document
heading lands verbatim in a filename, and that filename lands verbatim in `/`.

**This is the outlier, not the norm.** `scripts/gen-goals-page.py` escapes every filesystem-derived
value it renders (`:605-606`, `:620-621`, `:666`, `:681`). The convention exists; this one site
predates or missed it.

**Repair:** `page_markup.escape(p.name)` in the link text. Applied out-of-tree: **199/199** — which
is also the measurement that says nothing currently covers it.

No backlog row mentions `index_html` (grepped `docs/backlog.md`: 0 hits), so this is not a re-file of
#129 or #130.

---

## Medium 3 — the new timeout branch fires on ANY timeout while claiming EVERY, and silences the fallback instruction when Codex really is unavailable

`scripts/codex-review.py:847-856`

The predicate is `any("timed out" in a for a in attempts)`; the message it prints is
`⚠ EVERY ATTEMPT TIMED OUT`. Because the branch is an `if/else`, a mixed failure also **suppresses**
the sentence that used to print unconditionally — *"The Codex gate did NOT run. Fall back to a Claude
adversarial review and note the gap in the review doc."*

Measured by driving `main()` with `run_codex` stubbed, four attempt shapes:

| shape | attempts | printed |
|---|---|---|
| A — all timed out | 2 timeouts | `EVERY ATTEMPT TIMED OUT` · re-run at 1800s |
| B — 2 CLI failures, then a timeout | 1 of 3 timed out | `EVERY ATTEMPT TIMED OUT` · re-run at 1800s |
| C — **a timeout, then a usage limit** | 1 of 2 timed out | `EVERY ATTEMPT TIMED OUT` · re-run at 1800s |
| D — no timeout | 0 of 2 | `The Codex gate did NOT run. Fall back…` |

**C is the harmful one.** A usage/rate limit is the first entry on `plugins.md`'s "unavailable" list
and doubling the timeout cannot fix it; the caller is told to spend another 1800s and is never told
the gate did not run. The branch's own advice line — *"fall back only if it … fails for a non-timeout
reason (auth, HTTP 4xx/5xx, usage limit)"* — describes exactly the situation in which it has just
suppressed the fallback.

**B is the ordinary case, not a corner.** `plugins.md` documents the candidate walk as
`gpt-5.6-sol → -terra → -luna → gpt-5.5`, with the first three rejected by the pinned CLI. Whenever
the last candidate times out, three attempts that did *not* time out are reported as if they had.

Nothing here is tripped by stdout: I checked `classify` (`:525-593`) and no branch embeds stdout into
`reason`, so a review whose *content* discusses timeouts — likely, reviewing this very repo — cannot
trip the grep. The predicate is sound about what it reads; it is wrong about what it concludes.

**Repair:** keep the fallback sentence unconditional and make the timeout note additive, with a real
count (`N of M attempts timed out`). **Falsifier:** shape C prints the fallback sentence.

---

## Medium 4 — the whole new branch can be deleted at 85/85

The diff adds **zero** cases to `scripts/codex-review.py` (`git show 42a84e6d -- scripts/codex-review.py | grep -c '^+.*case('` → `0`), and the declared count is unchanged.

Mutated out-of-tree against its own suite:

```text
CONTROL (unmutated)                        -> 85/85 passed
any -> all (the honest predicate)          -> 85/85 passed
the whole timeout branch is DELETED        -> 85/85 passed
the doubling advice says the SAME budget   -> 85/85 passed
```

The commit message's claim is *"SO IT CANNOT RECUR BY MEMORY ALONE … the rule lives where the failure
happens."* The rule is a `print` with no falsifier, in a file that carries both a self-test and a
mutation manifest. On this repo's own terms that is a rule that has been *written down*, not
mechanised — the distinction `dev-process.md` opens with.

`classify` is pure and already directly tested; the branch predicate is trivially extractable into a
helper of the same shape, which is what would make Medium 3's repair testable too.

---

## Medium 5 — `plugins.md` fixed one of the two places that tell the caller to give up early

`docs/plugins.md:230-235`, unchanged by this branch:

> **Bounded wait …** Within ~2–3 minutes, **read the actual Codex task output file** … Treat as a
> hang → fall back immediately if: the file shows only `Thread ready` / `Turn started` with no
> findings, **it hasn't grown**, …

This is the same instruction the branch corrected two paragraphs earlier, still standing, and it is
*more* aggressive than the 900s default that caused the incident — it licenses abandoning Codex after
two to three minutes on the evidence that an output file has not grown. On a 45-minute review that is
the normal state of the file.

The fallback paragraph now excepts timeouts; this one does not mention them and reaches the same
outcome by a different route. Same class, same document, one instance fixed.

**Fix:** one clause — a quiet output file is a hang signal only after the budget the run was actually
given.

---

## Low 6 — the new cases do not pin *which* escaper is used

`scripts/explainer-serve.py:655-657` records a decision — *"`page_markup.escape`, not a local
replace-chain: this repo already owns one escaper"* — with no falsifier. Measured:

```text
rel = rel.replace("<", "&lt;")   (partial escaper)  -> 199/199 passed
rel = ""                         (escape by deleting) -> 198/199   <- correctly caught
```

The second line is the good news and I want to state it plainly: the second new case, *"…and still
shows the reader which file they are looking at"*, is **load-bearing and honest** — it is the only
thing standing between the fix and escaping-by-deletion.

The first line is a gap in the *stated decision* rather than in safety: `<`-only escaping is
sufficient for element text, so this is not an injection hole. It means an unescaped `&` in a
filename renders as markup-ish text, and it means the comment's rule has no guard.
`check-vocabulary-collisions.py` will not see it either. **Low, and arguably fine to leave** — filed
so the next reader does not assume the comment is enforced.

---

## Medium 7 — the branch does not satisfy its own dashboard gate

```text
$ python3 scripts/check-dashboard-entry.py
REFUSED — 6 tracked file(s) changed and no entry was added to docs/dashboard-entries.md.
exit=1
```

Eight tracked files changed between `32c56bfa` and `42a84e6d`; six of them count (the two under
`docs/reviews/` are excluded). `dev-process.md` requires the entry to ride in the **same PR** as the
work it describes, so this is a pre-merge blocker rather than a defect in the code. The `NO-ENTRY:`
escape is available but would be the wrong call here — a fix to a viewer the reader actually opens,
plus a change to how the review gate reports failure, is exactly what the dashboard exists to carry.

Every other branch-level gate is green: `check-review-rounds.py` (257 rounds, 0 silent gaps, 121
verdicts, none contradicted — see High 1 for why that is not reassuring here), `check-anchors.py`,
`check-docs.py`, `check-backlog-closure.py` (1 pre-existing warn on #117, unrelated).

---

## What I checked and found CORRECT

- **Escaping `rel` breaks nothing.** `body` is computed at `:639-641` **before** the rebinding at
  `:657`, so `rel.lower().endswith(".md")` still sees the raw name; the `.md`-renders-as-markdown
  case confirms it. `rel` reaches no URL or attribute — the only link in the shell is a relative
  `?raw=1`. `page_markup.escape` uses `quote=True`, so an apostrophe becomes `&#x27;`, which renders
  correctly as element text.
- **The 404 bodies are not an HTML sink.** `src_root_help` and `_gone_checkout_help` interpolate
  `observed.env_value` and `observed.fallback`, but every one of their sends is
  `text/plain; charset=utf-8` (`:1175`, `:1179`). Checked all four `text/html` occurrences in the
  file; only two are producers.
- **`latest_target`'s `Location` header is safe.** `urllib.parse.quote` encodes CR and LF, so a
  filename cannot inject a header.
- **Both new manifest entries are honestly attributed.** Applied to an out-of-tree copy over a
  control proved green first:

  ```text
  CONTROL                                                       199/199, no red cases
  resolve_page judges the extension on the RAW, pre-decoded …   198/199
      red: ['…and the encoded spelling of a dot gets the SAME refusal']       <- exactly the entry's
  the /src/ viewer interpolates the filename into HTML unescaped 197/199
      red: ["source_shell escapes the FILENAME, not just the file's contents",  <- the entry's
            '…and still shows the reader which file they are looking at']
  ```

  Entry 1 reddens **only** its named case — the neighbouring fallback cases are undisturbed, and the
  red is caused by `/notes%2emd` returning the decoy, which is the reason the name gives. Entry 2
  reddens its named case plus the sibling, which is normal for one edit and not misleading. Neither
  attribution overstates what its mutation kills.
- **`classify` cannot be tripped by review content** — see Medium 3.
- Green on this tree: `explainer-serve.py --self-test` **199/199 in all three `$HOME` shapes**
  (normal; `HOME=$(mktemp -d)/.home`; `$HOME` inside the resolved repo root);
  `codex-review.py --self-test` 85/85; `check-plan-code.py --self-test` 128/128;
  `check-docs.py`, `check-ratchet-contract.py` (41/41), `check-selftest-counts.py` (18/18),
  `check-fixture-variation.py` all exit 0.
## ⚠ `--mutate .` — STARTED, NOT COMPLETED BY THIS HALF — treat it as NOT INDEPENDENTLY VERIFIED

I started `python3 scripts/check-plan-code.py --mutate .` at the top of this review. After **three
hours** it had reached **572 of 687** and was still running; it is nowhere near the ~12 minutes the
brief estimates, because the `check-plan-code.py` self-mutation entries each spawn nested suites and
crawl (241 mutations in the first 12 minutes, then 55 in the next 50). No survivor was reported in
the 572 that ran. Log: `…/scratchpad/r1/mutate.log`, still being written.

**So the branch's recorded `687/687/687/0` is unconfirmed by me.** I am recording that rather than
implying otherwise — a gate I did not finish is not a gate that passed. CI runs this, and it should
be read there before merge.

What I *did* verify is the part this round is actually about: **both new manifest entries ran in the
real harness** (`[563/687]` and `[564/687]`, no survivor), and I reproduced their kills directly over
a green control — see the attribution block above. That is the same measurement the harness makes for
those two entries.

## Method note

Every mutation above was applied to a **copy** outside the repo (a directory of symlinks to the real
`scripts/` with the one target replaced), never to the tree. No `git checkout`/`restore`/`stash`/
`reset`/`add`/`commit` was run. `git status --short` was empty at start and is empty at end.

⚠ One thing worth recording for whoever runs a similar probe: driving `codex_review.main()` wrote
four verdict files into `docs/reviews/verdicts/` even though `--out` pointed outside the repo — the
verdict path is derived from the `--out` **stem**, not from `--out`. They were untracked and were
removed. That is the known *"a guard's evidence path has no allocator"* shape; a colliding stem would
have overwritten a committed verdict.
