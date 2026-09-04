# Comprehensibility Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Goal:** Work the ten open `(comprehensibility)` backlog rows to closure in an order where each
slice ships something a returning human can actually see, and no slice waits on a decision nobody
has been asked for.

**Architecture:** The ten rows are **not one subsystem**, so this is a sequencing plan plus one
fully-specified implementation slice. Slice A is the only group whose shape is decided in every row;
it ships first and alone. Everything after it is gated on a decision or a spec, each named below
with the question that unblocks it. This structure is deliberate: writing bite-sized steps over an
undecided shape produces a plan full of placeholders, which the writing-plans skill forbids and
which this project has measured as worse than no plan.

**Tech Stack:** Python 3.10+ (`scripts/*.py`), the repo's `--self-test` convention,
`scripts/check-plan-code.py --mutate .` for mutation coverage, Chrome for the visual gate.

## Global Constraints

- Every guard script carries a `--self-test` and declares its case count as `--self-test  # N cases`
  when pinned in `check-selftest-counts.POPULATION`.
- `EXPECTED_MUTATIONS` may grow, never shrink. A relocation retargets an entry; it never deletes one.
- A gate must not import the thing it guards (`_gate_module` docstring). Relocation, not import.
- Branch + PR for every change under `scripts/`; merging is a human gate.
- A branch changing tracked files records a dashboard entry or declares `NO-ENTRY: <reason>`.
- Anything longer than a line goes in a file — `--body-file`, `git commit -F`, `--prompt-file`.

---

## Scope check — why this is one plan and six slices

The writing-plans skill says to split when a spec spans independent subsystems. It does. The ten
rows touch five different surfaces: the dashboard gate, the dashboard page, the explainer server,
the `/brief` composer, and the backlog's own schema. They are grouped below by **what unblocks
them**, not by what they touch, because the binding constraint on this bundle is decisions, not code.

| Slice | Rows | Status | Blocked on |
|---|---|---|---|
| **A** | #83, #87 | ✅ **Ready — every shape decided** | nothing |
| **B** | #88 → #89 | 1 small decision | confirm the fragment location |
| **C** | #78 half (2) | 1 decision | where the entry check runs |
| **D** | #82 | Spec first | Phase 1 spec, then dual review |
| **E** | #56 | Spec first | what the roadmap's derived set IS |
| **F** | #40 + #50 | 2 user decisions | public repo naming; PR-number disclosure |
| **G** | #90 | Deferred by the user ("later") | story/task split vs a `Kind` column |

**Ordering rationale.** A first because it is the only slice that needs nothing from anyone. B next
because #88 is XS and is a **stated precondition** of #89, so doing it out of order strands the
larger item. C, D and E are all dashboard-gate/page work and share `check-dashboard-entry.py` and
`gen-dashboard.py` — C and D in particular both restructure the gate, so **D must follow C**, or the
same file is restructured twice with the second change rebasing over the first. F is last of the
active work because it is the largest and its decisions are outward-facing (a public repo). G is
deferred at the user's own instruction.

⚠ **Slice A and Slice D both touch `gen-dashboard.py`.** A touches CSS tokens and the card element;
D relocates the entry parser. Different regions, but if they run concurrently the append-only
`docs/dashboard-entries.md` will conflict — this repo has measured that three same-day branches each
appending to that file produce one clean merge and two conflicts. **Run them in sequence.**

---

# SLICE A — the settled items look settled, and the server stops dropping sockets

Two rows, one PR, one browser pass. #83's own recorded recommendation is *ONE PR, (B) then (A), and
not as a drive-by* — splitting them pays the visual-review cost twice for one surface. #87 rides
along because it is XS, needs no browser pass, and touches a file neither #83 half touches.

**Files:**
- Modify: `scripts/gen-dashboard.py` — the card `<article>` tag, `.prose strong`, `.flag.resolved`, `_ask_block`
- Modify: `scripts/explainer-serve.py:214-229` — `safe_path`, and the `/_rev` resolver
- Modify: `scripts/mutations/gen-dashboard.json`, `scripts/check-plan-code.py` (`EXPECTED_MUTATIONS`)

**Interfaces:**
- Consumes: `cleared_ids()` (already computes both sides of the resolved link), `entry["title"]` (already parsed)
- Produces: a `settled` class on the entry `<article>`; `safe_path` returning `None` on an unresolvable path

---

### Task A1: The card knows it is settled

**Why first:** (B) forces the card-class change that (A) then styles and links against. Doing (A)
first means adding the class twice.

**Files:**
- Modify: `scripts/gen-dashboard.py` — the `<article class="entry" id="…">` emitter
- Test: `scripts/gen-dashboard.py` `_self_test`

- [ ] **Step 1: Write the failing test** — a cleared entry's article carries the marker, an uncleared one does not.

```python
        # ⛔ THE FALSIFIER FROM BACKLOG #83(B), STATED AS A CASE. If an entry that is NOT
        # cleared stops rendering its warning, the fix reached the TOKEN instead of the STATE
        # and every live warning in the store went silent at once.
        _cleared = {"id": "2026-08-29/1", "title": "t", "body": "**Waiting on you:** x",
                    "date": "2026-08-29"}
        _live = {"id": "2026-09-04/9", "title": "t", "body": "**Waiting on you:** x",
                 "date": "2026-09-04"}
        case("a cleared card is marked settled",
             'class="entry settled"' in render_entry(_cleared, cleared={"2026-08-29/1"}))
        case("an UNCLEARED card is not marked settled",
             'class="entry settled"' not in render_entry(_live, cleared=set()))
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: FAIL — the emitter writes `class="entry"` unconditionally.

- [ ] **Step 3: Emit the class from the cleared set**

```python
    settled = " settled" if entry["id"] in cleared else ""
    out.append(f'<article class="entry{settled}" id="{html.escape(entry["id"])}">')
```

- [ ] **Step 4: Run the suite green**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: PASS, count risen by 2.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen-dashboard.py
git commit -F .git/COMMIT_MSG_A1
```

---

### Task A2: Emphasis follows settled state, both directions

**Files:**
- Modify: `scripts/gen-dashboard.py` — `.prose strong` and `.flag.resolved` rules
- Test: `scripts/gen-dashboard.py` `_self_test`

- [ ] **Step 1: Write the failing test**

```python
        # MEASURED 2026-09-01: exactly TWO entries author `**Waiting on you:**` and BOTH are
        # cleared, so 2 of 2 live-warning marks sit on settled items. The marker that is
        # CORRECT whispers (opacity .55) while the sentence that is STALE shouts.
        _css = build_css()
        case("a settled card mutes prose emphasis",
             ".entry.settled .prose strong{color:var(--ink)" in _css)
        case("a settled card's resolved flag stops whispering",
             ".entry.settled .flag.resolved{opacity:1" in _css)
        case("the LIVE prose-mark rule survives untouched",
             ".entry .prose strong{color:var(--p-mark)" in _css)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: FAIL — neither `.entry.settled` rule exists.

- [ ] **Step 3: Add the two rules, leaving the live rule alone**

```css
.entry.settled .prose strong{color:var(--ink);font-weight:600}
.entry.settled .flag.resolved{opacity:1;font-weight:600;color:var(--ink-soft)}
```

- [ ] **Step 4: Run the suite green**

Run: `python3 scripts/gen-dashboard.py --self-test`

- [ ] **Step 5: Commit**

---

### Task A3: A settled ask says who settled it

**Files:**
- Modify: `scripts/gen-dashboard.py` — `_ask_block`
- Test: `scripts/gen-dashboard.py` `_self_test`

**Interfaces:**
- Consumes: `cleared_ids()` → `{asked_id: resolver_id}`; `entry["title"]`

- [ ] **Step 1: Write the failing test**

```python
        # MEASURED across all 6 `[resolved: …]` links in the store: the RESOLVER TITLE already
        # states the outcome in plain words in 6 of 6. Recording the chosen option instead would
        # need a FLAG grammar change, and that regex produced a High this same week (row #82).
        _b = _ask_block(asked={"id": "2026-09-01/3", "title": "x"},
                        resolver={"id": "2026-09-01/11",
                                  "title": "You chose to hold the automatic check"})
        case("a settled ask links its resolver by id", 'href="#2026-09-01/11"' in _b)
        case("a settled ask states the outcome in the resolver's own words",
             "You chose to hold the automatic check" in _b)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 scripts/gen-dashboard.py --self-test`
Expected: FAIL — `_ask_block` renders `Decided:` and stops.

- [ ] **Step 3: Render the back-reference**

```python
    if resolver:
        out.append(f'<p class="settled-by">settled by '
                   f'<a href="#{html.escape(resolver["id"])}">{html.escape(resolver["id"])}</a>: '
                   f'{html.escape(resolver["title"])}</p>')
```

- [ ] **Step 4: Run the suite green**

- [ ] **Step 5: Commit**

---

### Task A4: The server answers a NUL byte instead of hanging up

**Files:**
- Modify: `scripts/explainer-serve.py:222` (`safe_path`), and the `/_rev` resolver
- Test: `scripts/explainer-serve.py` `_self_test`

⚠ **This is a CLASS, not an instance.** The row measured four URLs failing identically —
`/_stale?p=%00`, `/_rev?p=%00`, `/%00`, `/dashboard%00`. `safe_path` resolves at `:222` **outside**
its `try`, and `/_rev` uses `resolve_page`, a *different* resolver (pinned by the case at `:1175`
asserting `safe_path(` is absent from that branch). **Fixing `/_stale` alone leaves three broken.**

- [ ] **Step 1: Write the failing test — all four URLs, not one**

```python
        # MEASURED 2026-09-02: curl exit 52, Python RemoteDisconnected. A ValueError
        # ("embedded null byte") from pathlib escapes the handler's except, which wraps only
        # the stat calls. Every OTHER hostile input in that sweep failed CLOSED to `fresh`.
        case("a NUL byte does not escape safe_path", safe_path("/\x00.html", root) is None)
        case("a NUL byte does not escape the page resolver", resolve_page("\x00") is None)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 scripts/explainer-serve.py --self-test`
Expected: FAIL with `ValueError: embedded null byte`, not an assertion — the exception escapes.

- [ ] **Step 3: Make resolution total, at the resolver, not at each handler**

```python
    try:
        candidate = (root / raw).resolve()
        candidate.relative_to(root.resolve())
    except (OSError, ValueError):
        return None                      # escaped the root, or is not a resolvable path at all
```

- [ ] **Step 4: Run the suite green, then probe the live server**

```bash
python3 scripts/explainer-serve.py --self-test
for u in '/_stale?p=%00' '/_rev?p=%00' '/%00' '/dashboard%00'; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:7391$u"); echo "$u -> $code"
done
```
Expected: four HTTP status lines. **Any `000` means the socket still dropped.**

- [ ] **Step 5: Commit**

---

### Task A5: Mutation coverage, then the browser gate

- [ ] **Step 1: Add one mutation per new behaviour to `scripts/mutations/gen-dashboard.json`**

Each must go red **via the case it names**. Anchors must be unique — the harness refuses an entry
repeating an earlier entry's edit anchors, so verify with `grep -c` before adding.

- [ ] **Step 2: Raise `EXPECTED_MUTATIONS["scripts/gen-dashboard.py"]` by exactly the number added**

- [ ] **Step 3: Control first, then mutate**

```bash
python3 scripts/check-plan-code.py --self-test        # control, expect rc=0
python3 scripts/check-plan-code.py --mutate .         # expect rc=0, survivors 0
```

- [ ] **Step 4: THE GATE NO SCRIPT CAN CLOSE — drive it in Chrome**

Regenerate, serve, and confirm **by looking**: a settled card's `**bold**` lead-in is no longer
orange; its resolved flag is legible; the back-reference link jumps to the resolver's card; and — the
falsifier — an **uncleared** entry authoring `**Waiting on you:**` **still renders orange**.

- [ ] **Step 5: Dashboard entry, then the PR**

---

# SLICES B–G — sequenced, and each one's blocking question

**These are not tasks and must not be executed as such.** Each needs an answer first. Writing steps
for them now would be inventing the decision rather than taking it.

### Slice B — #88 then #89 (the durable fragment, then the fork question)

**#88 (XS).** A `/brief` page outlives its session; its source fragment does not, so a question asked
tomorrow cannot be answered *in* the page. 43 pages on disk, zero fragments. The proposed shape:
write the fragment beside the page as `~/explainers/<date>-brief-<slug>.fragment.html`.
⛔ A `--from-page` mode is **forbidden** — it makes the rendered page its own source of truth.
**Decision needed:** confirm the sibling-file shape. **Falsifier:** in a fresh session, answer a
question in an existing `~/explainers/*brief*.html` without hand-rebuilding the fragment.

**#89 (S + decision).** Depends on #88 — *without a durable fragment no later session, forked or
not, can answer in the page at all.* Five questions are open (delivery, the ask-back relay,
staleness, #88, concurrency). ⛔ Verification must not be delegated away: two defects in one page
were visible **only** by executing it.

### Slice C — #78 half (2) (when the gate runs)

Half (1) shipped. What remains is **timing**: the CI step runs `if: github.event_name ==
'pull_request'`, while the dashboard skill regenerates the page immediately — so the reader sees the
page long before the gate sees the branch. **Decision needed:** does the content check move earlier
(a local hook at entry-write time), run on push as well, or stay where it is and accept the lag?

### Slice D — #82 (the entry parser relocation) — **must follow C**

Three `[resolved: …]` shapes pass the gate and break the page. A regex cannot close it: whether an id
names a real entry is a property of the **whole store**, and the gate sees only a patch. ⛔ The
obvious fix is forbidden — a gate must not import the thing it guards. Shape: relocate the parser
*into* `check-dashboard-entry.py` and have `gen-dashboard` import it. **Spec first, explicitly.**

### Slice E — #56 (roadmap reconciliation)

The milestone half shipped in `/goals`. What remains is reconciliation — tick vs commit, milestone vs
merged PR, deploy line vs `flyctl releases`. ⚠ Do **not** rebuild it as a gate: it fires on every
docs-only commit and gets disabled. **Spec must settle:** what the roadmap's derived set IS.

### Slice F — #40 + #50 (package the harness as a plugin)

They ship together — `/brief` is the third member of the `explain-diff` family. Two blockers are
measured: the server is **POSIX-only** (`os.fork` does not exist on Windows), and two globals are
hardcoded (`~/explainers`, port `7391`). **User decisions needed:** the public repo name, and whether
a public plugin may cite this private repo's PR numbers.

### Slice G — #90 (stories vs tasks) — deferred by the user

25 distinct `Bundle` values including `A`, `B`, `C`, `D`, `?` and `—`. **Decision needed:** split
stories to the roadmap and tasks to the task list, or keep one table and add a checkable `Kind`
column.

---

## Self-review

**Spec coverage.** All ten rows appear: #83 and #87 as Slice A tasks; #88, #89, #78, #82, #56, #40,
#50, #90 as sequenced slices with their blocking question named.

**Placeholder scan.** Slice A contains no TBDs; every code step carries real code. Slices B–G contain
no steps *by design*, and say so — they are a sequence, not deferred tasks.

**Type consistency.** `settled` class introduced in A1 is consumed by A2's CSS and A3's link target.
`safe_path` returns `pathlib.Path | None` throughout; A4 widens the None case without changing the type.

**One correction folded in from reading the rows.** #78 was recommended twice in conversation as the
cheapest start. That was wrong: its remaining half is a timing decision, not a coded shape, so it
moved to Slice C and #83/#87 became Slice A.
