# Page chrome seam (#76/#77) — round 1, coordinator half

**Subject:** branch `feat/page-chrome-seam`.
**Codex half:** [`page-chrome-codex-r1.md`](page-chrome-codex-r1.md), `gpt-5.5`. **7 findings, 2 High.**

**REVIEW GAP: claude — an independent subagent reviewer could not be dispatched under this session's
tool constraints; the coordinator ran the adversarial pass in its place.** Third round with this
caveat, and it keeps mattering: on this branch Codex found more than I did, and two of its findings
were in code I had written specifically to prevent the class it caught me in.

---

## Codex findings, all reproduced, all fixed

| # | Sev | Finding | Fix |
|---|---|---|---|
| 1 | **High** | `assert_wired` accepted **any** script containing `"chrome-theme"` — `<script>console.log("chrome-theme")</script>` passed with no handler | `chrome_script()` emits `CHROME_SCRIPT_MARK` (`yps-chrome-v1`) and the binding check requires **that**. Asserting the mechanism, not a word anything may contain |
| 2 | **High** | `brief-compose` trusted the button id alone, so a fragment with the button and no script composed to **one inert control and no stamp** — the fail-silent, reached through the composer | that branch now calls `assert_wired` on the fragment and supplies a stamp if it lacks one |
| 3 | Med | `gen-dashboard --fragment-only` wrote **before** the gate | gate moved ahead of every write of that page |
| 4 | Med | the served index is a page producer carrying a control with **no gate at all** | `assert_wired(doc, …)` before it is returned; verified over HTTP |
| 5 | Med | duplicate `:root[data-theme=…]` blocks **overwrote** instead of cascading, hiding a reachable bad colour behind a later partial block | merged in source order, as the browser cascades |
| 6 | Med | `/regenerate` had no per-page lock (`ThreadingHTTPServer` — concurrency is real), and a generator exiting 0 after writing a **degraded** page reported plain success | one lock per page, so same-page rebuilds serialise and different pages stay parallel; a `⚠` line on the generator's stdout now travels back as `warning` and the button **says so instead of reloading over it** |
| 7 | Low | `brief-compose` wrote the file **before** the tray check that calls it unusable | check first; a bad page is not written |

## What the fixes then cost, which is the honest part

**My fix for #1 broke two things, and the mutation harness — not I — found both.**

- The manifest anchor for the binding check went stale; `--mutate .` reported *anchor NOT FOUND* rather than silently passing.
- With the marker in place, **nothing distinguished "inside a `<script>`" from "anywhere on the page"**, so `_scripts` returning the whole page went from caught to **SURVIVING**. A case for a marker in a comment closes it.
- Then that mutation was caught by a *different* case than its `expect` named, and the harness refused it rather than recording a green. The `expect` was retaken **from the run**.

**And my fix for #2 was caught by my own tightened check**: the composer case's fixture was itself a bare button — an inert control, the exact thing being guarded against, sitting in the test for it.

## Measurements

```
page_chrome --self-test       43 -> 47      brief-compose --self-test     38 -> 40
gen-dashboard --self-test     217/217        explainer-serve --self-test   71/71
gen-backlog-page --self-test  71/71          gen-goals-page --self-test    15/15
check-plan-code --mutate .    5 files, 105 mutations, 0 survivors
check-docs / check-anchors / check-ratchet-contract          OK
```

Driven, not read: `/regenerate` refuses `../../etc/passwd` and `goals; touch /tmp/pwned` as **data**
(the file never appears); two concurrent rebuilds of the same page both return 200 and the page
survives `assert_wired`; the served index passes its own gate over HTTP; each of dashboard,
backlog-table and goals carries **exactly one** control and **one** stamp.

## The gap this section used to record, now closed by DRIVING it

Codex labelled `chrome_script()` **NOT CHECKED** — reviewed and probed statically, never executed —
and so had I. `assert_wired` proves the parts are present and bound; it cannot prove that pressing
the button does anything. So the button was pressed, in Chrome, on the served page:

| | observed |
|---|---|
| start (OS dark) | `data-theme` unset, `body` background `rgb(20, 24, 27)`, `aria-pressed=true` |
| after one click | `data-theme="light"`, background `rgb(247, 248, 250)`, `aria-pressed=false`, `localStorage` `light` |
| after a second | back to `dark` and `rgb(20, 24, 27)` — it returns, rather than only leaving |
| after a full reload | `data-theme="light"` applied before paint, background still light |
| refresh button | `POST /regenerate` → 200, and the page rebuilt |

⭐ **And the provenance flag was observed CHANGING, not merely asserted.** The stamp read
`08:39 · 4572635 · uncommitted changes` before the round-1 commit and
`09:12 · 0b5284d` after it — the dirty qualifier appearing and disappearing against a real tree,
which no unit case can demonstrate.

**Still not covered by anything automated:** these were driven by hand this once. Nothing re-runs
them, so a future change could break the click path with every suite green. That is a real gap and
it is stated rather than implied.
