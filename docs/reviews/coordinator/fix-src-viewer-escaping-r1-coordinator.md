# Round 1 — `fix-src-viewer-escaping` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: fix-src-viewer-escaping
halves:
  claude: ran
  codex: gap
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: review-bookkeeping, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: encoded-path, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: html-escaping, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: true, component: timeout-advice, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: true, component: timeout-advice, disposition: fixed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: true, component: plugins-doc, disposition: fixed}
  - {id: M7, severity: Medium, aim: instrument, fix_induced: true, component: dashboard-gate, disposition: fixed}
  - {id: L6, severity: Low, aim: instrument, fix_induced: true, component: escaper-pinning, disposition: fixed}
```

## REVIEW GAP: codex — its round-1 artifact reviewed the PARENT commit, not this branch

⛔ **H1, and it is the finding I am most glad was caught.** I ran Codex retroactively against
`master` (`32c56bfa`), it found the two defects this branch fixes, and I then filed that review as
**round 1 of the branch that fixes them** — a review of the code *before* the fixes, presented as the
review *of* the fixes. The verdict recorded `head: 32c56bfa` and named a review stem that was not on
disk.

⚠ **`check-review-rounds.py` cannot see this class**, measured: `verdict_problems` returns early on
`if rec.get("gate_ran"): continue`, so it only ever asks whether a review is filed for a gate that did
**not** run. A verdict that ran, against a different commit, naming a file that does not exist,
produces **zero problems** and the gate exits 0.

**Resolved honestly:** the retro review is renamed to
`docs/reviews/codex/explainer-serve-manifest-retro-codex.md`, carries a header stating its subject is
master, and its verdict travels with it. The gate then immediately complained that this branch had no
Codex half — correctly — and round 2 is that half, run against the fixes.

⭐ **A mechanical check is available and does not exist:** a verdict whose `head` is not an ancestor
of the branch under review is detectable with one `git merge-base --is-ancestor`. Noted for #130's
neighbourhood rather than built here.

## M1 — MEDIUM — my own fix was a REGRESSION, not an incomplete fix

The Codex finding was that `resolve_page` judged "did this name have an extension?" on the **raw**
path, so `/secret%2eenv` bypassed a rule `/secret.env` obeyed. My repair decoded `bare` — and handed
it back to `safe_path`, **which decodes again**. Measured end-to-end with `secret.env.html` present:

| request | master | my fix | now |
|---|---|---|---|
| `/secret.env` | None | None | None |
| `/secret%2eenv` | **SERVED** | None | None |
| `/secret%252eenv` | None | **SERVED** | None |

⭐ **The middle and bottom rows INVERTED** — master refused the double-encoded spelling and my fix
accepted it. That makes it a regression I introduced, not a gap I failed to reach.

**The general shape, which is the part worth keeping:** the rule needs the classifier and the
resolver to agree about what the request says. My fix changed *whether* one side decodes without
asking whether both sides decode the **same number of times**. Re-encoding before the fallback
restores the invariant.

⚠ **And making it falsifiable took two more attempts.** With the re-`quote` in place, deleting the
`unquote` became **invisible** — both versions are internally consistent, differing only in which
spelling is authoritative, and they diverge observably only when a file whose **literal** name
contains `%2e` exists. A decoy makes the choice visible. Placing that decoy then broke the sibling
case, correctly: `/secret%252eenv` *legitimately* resolves to a file named `secret%2eenv.html`, so
that case must assert **which file must never be reached**, not `None`. Two questions, two sandbox
roots.

## M2 — MEDIUM — `rel` was not the only filesystem-derived value reaching HTML

`index_html` percent-encodes the **href** and left the **link text** raw — the identical defect,
twelve lines of diff from the one I fixed, and easy to read past because the line *looks* like it
handles a hostile name. Measured with a file named
`2026-09-16-brief-evil<img src=x onerror=alert(1)>.html`: the payload appears raw in the index and
nowhere escaped. ⚠ Reachable: `brief-compose.py` builds its output filename from `--slug` with no
validation anywhere in that file. `gen-goals-page.py` escapes every filesystem-derived value it
renders — the convention exists and this was the outlier.

## M3, M4 — MEDIUM — my timeout fix had its own two defects

- **M3** it printed *"EVERY ATTEMPT TIMED OUT"* while testing `any`, so a mixed failure (one timeout,
  one auth error) would have been told to double the budget — a loop that cannot succeed. And it
  printed the advice **instead of** the fallback line, so a genuinely unavailable Codex lost its
  instruction. Now `all`, and additive.
- **M4** the whole branch was **deletable at 85/85**. Extracted to a pure `timeout_advice(attempts,
  timeout)` and cased with six cases; deleting it now reddens three, `all`→`any` reddens one, and
  hardcoding the doubled number reddens one. ⭐ A message nothing asserts is a message the next
  refactor removes quietly — which is the entire subject of the manifest work this branch sits on.

## M5, M7, L6 — MEDIUM/LOW — fixed

- **M5** `plugins.md` had a **second** place telling the caller to give up early: the *Bounded wait*
  paragraph said treat a quiet output file as a hang after ~2–3 minutes. That is exactly what cost
  three rounds their Codex half, and it survived the first repair because I fixed the paragraph I was
  looking at. It now says a quiet file is not a hang until `--timeout` has elapsed. ⚠ Rewritten in
  the **same eight lines** — the file sits at its 260-line budget and the gate refused three attempts
  to grow it, correctly each time.
- **M7** the branch did not satisfy its own dashboard gate. Entry added.
- **L6** the new cases did not pin **which** escaper is used. They assert behaviour through
  `page_markup.escape`, which is the repo's one escaper — a second implementation would be the
  duplicate-vocabulary shape `check-vocabulary-collisions.py` exists for.

## Evidence

689 mutations, 689 killed, 689 attributed, 0 survivors. Suite **199 → 202**, manifest **44 → 46**,
`codex-review.py` **85 → 91**. Green in all three `$HOME` shapes, including `$HOME` inside the
resolved repo root — the shape that caught a Linux-only defect the night before.

## Q4 / Q5

**Round 2 owed** — `fixes_nontrivial: true`, and this round's Codex half never saw the branch.

**Thrashing: not armed.** M1, M3, M4, M5 and H1 are fix-induced but in five different components.
⚠ Worth naming anyway: **three of them are the same shape** — fix the instance, miss the sibling
(the `%25` level, the second HTML producer, the second doc paragraph). That is four consecutive
branches on which this pattern has appeared, and it is the strongest argument for the survivor sweep
filed as #130 being done as a sweep rather than finding-by-finding.
