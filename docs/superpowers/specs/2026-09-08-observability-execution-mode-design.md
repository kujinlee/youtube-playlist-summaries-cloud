# Who RUNS a page-producing skill — and who is allowed to say it is ready

> **Anchor:** `explanation-on-demand` — **ADR:** none
> **Goal:** A person working now can have a subject they choose — a change, a concept, or a set of
> findings — explained in a page they can read and ask questions inside.

**Backlog #89.** **v1 (DRAFT), 2026-09-08.** Answers questions (1), (2), (3) and (5); (4) was the
precondition and is re-measured below. **Nothing here is implemented.** The spec is the human gate.

---

## 0. Why this anchor exists, and why widening the old one was refused

`status-visibility` is scoped to *"a person who was **away**"*. Three of the four Group-A skills —
`explain-diff`, `explain-topic`, `explain-findings` — serve someone who is **here**, working, and
wants a subject they chose explained. `brief` is the away-reader and keeps `status-visibility`.

⚠ **One name for two readers is how a goal stops being falsifiable.** Widening the existing sentence
to cover both would make it true of everything the four skills do and therefore a test of nothing.
The registry entry is the cheap part; the discipline is refusing to let one sentence mean two things.

---

## 1. MEASURED FIRST: the precondition is cleared in code and unproven in practice

#89 names #88 as a precondition — *"without a durable fragment beside the page, no later session,
forked or not, can answer in the page at all."*

| Measurement | Result |
|---|---|
| `frag_out.write_text(content)` entered `brief-compose.py` | `65cd509e`, **2026-09-04 15:28** — unconditional, no flag |
| Files in `~/explainers/` | **47** |
| `*.fragment.html` | **2** — `dashboard.fragment.html`, `goals.fragment.html` |
| `/brief` pages | **32** |
| `/brief` fragments | **0** |
| Most recent `/brief` page | `2026-09-05-brief-pr225-reviews.html`, mtime **2026-09-05 10:14** — *after* the fix |

**Both surviving fragments belong to Group B** (`gen-dashboard.py`, `gen-goals-page.py` — the
hook-regenerated pages that compose through `brief-compose.py`). The mechanism has never produced a
fragment for the agent-authored group it was written for.

⚠ **Stated honestly, because I cannot see why:** I do not know whether the 2026-09-05 page bypassed
`brief-compose.py` or something else happened. What is certain is that **#88's own falsifier still
fails for every brief page on disk** — *"in a fresh session, answer a reader's question in an
existing `~/explainers/*brief*.html` without reconstructing the fragment by hand."*

**Consequence for this design:** question (2)'s answer below assumes a durable fragment. That
assumption is currently unbacked for Group A. **T0 must close it before anything else ships**, and
its falsifier is an observation, not a code read: *build one `/brief` and assert the sibling
`.fragment.html` exists.*

---

## 2. Decision (1) — delivery: the fork BUILDS, the parent VERIFIES and announces

#89 sketched: fork does everything, then `SendMessage({to: "main"})` after §5b. **This spec deviates,
and the reason is the constraint #89 itself puts in bold:** *verification must not be delegated away.*

| | Fork | Parent |
|---|---|---|
| Research the subject, read the diff/findings/topic | ✅ | |
| Write the fragment, compose the page | ✅ | |
| **Execute the page in a browser (§5b)** | | ✅ |
| Print the URL to the human | | ✅ |

**Why this split and not #89's.** The cost #89 measured is the *research and drafting* — a 22,576-byte
fragment rewritten five times, a 986,929-byte composed page, ten ratchet exit codes, `git log -15`,
review inventories, `flyctl releases`, browser probes returning JSON. Browser verification is a
handful of tool calls. **Forking the expensive half captures nearly all the saving; keeping the cheap
half in the parent keeps the one step that has caught real defects.**

Two defects in the 2026-09-03 page were visible **only** by executing it — a `document.hidden` gate
producing a false *"0 of 5 buttons reachable"* (a backgrounded tab has 0×0 geometry, so every
geometric assertion is an artifact), and a missing `#modechip` block whose CSS and JS both existed.
Neither appears in the source. **A fork that skips §5b ships a page that looks verified and is not** —
and the parent has no way to tell, because a fork's report is prose.

**This dissolves question (1) rather than answering it.** The parent verifies, so the parent already
holds the URL. No `SendMessage` is needed for delivery, and the "announced before verified" failure
mode cannot occur — there is no path where an unverified page reaches the human.

---

## 3. Decision (2) — the ask-back loop: parent owns the Monitor, fork is resumed by name

Constraint, from `explainer-delivery.md`: **one monitor per session, not per page.** It watches
`questions.md`, which every page shares, so a second monitor duplicates every event rather than
covering a second document. It is also session-scoped and fires only while the session lives.

```
reader selects text → Send → questions.md
        ↓  (the ONE session monitor, in the PARENT)
   parent receives the question
        ↓  SendMessage({to: "<fork-name>"})
   fork resumes WITH ITS TRANSCRIPT — still knows the fragment path and why each number is there
        ↓  edits fragment → re-composes
   parent re-verifies (§5b) → confirms to the reader
```

**The fork must be named at spawn** (`name:` on the Agent call), or it is not addressable and this
loop has no second half. A fresh agent cannot substitute: it would have the fragment path but not the
reasons, and `brief`'s own known-gaps section warns it may then **manufacture** an answer to fill the
slot.

---

## 4. Decision (3) — staleness: make it a CHECKED property, not a remembered one

A fork's inherited context is a snapshot taken at spawn. The measured failure: on 2026-09-03 the user
chose an option **mid-build**, and the page would have shipped stamped *decision pending*.

`SendMessage` fixes it **only if someone remembers to send** — which is a record, not a mechanism, and
this project has a name for that.

**So the mechanism is §5b, which §2 already puts in the parent.** Verification is not only "does the
page render" — it includes reading the page's decision/status section against what the parent knows
*now*. The parent is the one participant that cannot be stale about its own session.

- **Rule:** the spawn prompt carries an explicit `as of <commit/time>` line, so the page can state its
  own horizon rather than implying it is current.
- **Falsifier:** a page whose decision section contradicts the parent's current state reaches the
  human. If §5b is performed, it cannot.
- **Honest bound:** this catches staleness in what the page *says*. It cannot catch a subject that
  changed in a way neither participant noticed.

---

## 5. Decision (5) — concurrency: the fork writes NOTHING inside the repo

The Codex review wrapper snapshots the top level of `docs/reviews/` **non-recursively** and its
intrusion detector fires on **any** concurrent write; it cried wolf twice on 2026-09-03, and on the
failure path `quarantine()` has **moved a concurrent half out of the repo**.

A page-building fork has no legitimate reason to write inside the repository:

| Artifact | Location | In repo? |
|---|---|---|
| the page | `~/explainers/YYYY-MM-DD-<kind>-<slug>.html` | no |
| the fragment (#88) | `~/explainers/<same>.fragment.html` | no |
| working notes | session scratchpad | no |

**Rule: a page-building fork writes only under `~/explainers/` and its scratchpad.** If that holds,
page-building and a Codex review can run concurrently without tripping the detector.

⚠ **This is a HYPOTHESIS, not a measurement.** #89 records the detector firing twice; I have not
reproduced it with a fork that touches no repo path. **Falsifier T4 below.** Until it runs, the
conservative rule stands: **do not start a page-building fork while a Codex review is in flight.**

---

## 6. What would have to be true — tasks, each with an observation that fails it

| | Task | Falsifier |
|---|---|---|
| **T0** ✅ | **Close #88 in practice for Group A** (precondition) | Build one `/brief`; assert the sibling `.fragment.html` exists. Fails today for all 32 pages — **DISCHARGED 2026-09-08**, see §8 |
| T1 | `explainer-delivery.md` gains an **execution-mode** section — it currently says nothing about who RUNS the skill | The section names, for each of build / verify / announce / answer, which participant does it |
| T2 | The four Group-A skills cite T1 rather than restating it | `check-explainer-delivery.py` already enforces cite-not-restate; it stays green |
| T3 ✅ | The fork is spawned **named**, and the parent performs §5b | A page reaches the human that the parent never executed — **RUN 2026-09-08, §8** |
| T4 ✅ | **Measure** the concurrency hypothesis (§5) | Run a page-building fork beside a Codex review; read `docs/reviews/verdicts/<stem>.verdict.json`. If the intrusion field fires on a fork that wrote nothing in the repo, §5 is wrong and the conservative rule stays — **RUN 2026-09-08, and the falsifier CANNOT FIRE; §8** |

---

## 7. What this spec does NOT settle

- ~~**Whether forking is worth it at all.**~~ ✅ **SETTLED 2026-09-08 by the user — see §9.** The
  trial ran, the benefit was observed, and the split is adopted. Kept struck-through rather than
  deleted because the *reason* it was open — the cost was measured and the benefit only inferred — is
  what the trial was designed to resolve, and a reader should be able to see that it was answered by
  running it rather than by argument.
- **Group B is out of scope and must stay out.** `regen-backlog-page.sh`, `regen-dashboard.sh` and
  `regen-goals-page.sh` are `PostToolUse` hooks — **no agent runs them**, they already cost zero
  context, and the goals page is *derived* by ADR-0010. Proposing to fork them is a category error:
  they are solved by a stronger mechanism than an agent.
- **`explain-topic`'s free-form subject** may need a different spawn prompt from the other three;
  not investigated.

---

## 8. RESULTS — T0, T3 and T4 were run on 2026-09-08

### T0 — DISCHARGED

Baseline taken before the build: `~/explainers/` held **47 files, 32 `/brief` pages, 2 fragments**,
both belonging to `dashboard`/`goals`. After: **49 files, 3 fragments**, the new one being the first
fragment ever written for a Group-A page. §1's measurement is closed in practice.

### T3 — RUN, and the split paid for itself on its first use

A fork named `brief-builder` researched and composed; the parent performed §5b and delivered.

| Measured | Value |
|---|---|
| Spent inside the fork (build + fix + revision) | **~786k tokens, 82 tool uses** |
| Reached the parent's context | three reports, ~2,000 words |
| Parent's §5b cost | ~15 tool calls |

**The fork shipped a defect only execution could reveal:** light-theme body contrast **1.03:1**, dark
text on a dark background. Its fragment declared `[data-theme="light"]` overrides for `--ink` but not
`--bg`, so from the source both directions looked defined. Two controls placed the fault: `/dashboard`
measured 15.46:1, and a 2026-09-05 brief page measured 15.22:1 **in both themes** — a fully inert
toggle, readable by accident. After the fix, re-measured **by the parent** in Chrome: worst case
**8.69:1**, all eight states pass AA.

⛔ **This is §2's claim, demonstrated rather than argued: a fork that also performed §5b would have
shipped 1.03:1 and reported success.** Note the fork had even flagged the toggle as worth checking.

The geometry probe **passed** — 8 buttons, 8 distinct positions, 8 reachable — which *refutes* the
fork's own prediction that `.sh` being `display:flex` would collapse them. Recorded because a failed
prediction is evidence too. Both question paths drove clean, section label and 156-character quote
intact.

⚠ **Two hazards met, neither anticipated by this spec.** (1) §5b's render gate fired for real: the
tab reported `document.hidden: true`, and the geometry probe was correctly refused as CANNOT RUN
until a human surfaced the window — `osascript` could not do it, because two Chrome instances were
running and the one AppleScript addresses had no windows. (2) Driving the question path revealed
**five** monitors armed on `questions.md` when this session armed one; see backlog #103.

### T4 — RUN, §5 CONFIRMED, and the scope is narrower than the task implies

**Attempt 1 was VACUOUS and is recorded as such.** Review and fork were started together; the verdict
read `intrusions: []`. But a page build researches for minutes and writes for a fraction of a second
at the end: page mtime **10:18:36** against verdict mtime **10:17:09**. The window contained no
concurrent write. It passed for a reason unrelated to what it names — and both the parent and the
fork initially read it as a result.

**Attempt 2 arranged the overlap.** The fork recomposed repeatedly at ~40s intervals for the
review's duration. Review window **10:20:51 → 10:21:50**; a page write landed at **10:21:28**,
provably inside it. Verdict: `intrusions: []`, `gate_ran: true`, `docs/reviews/` unchanged at 866
entries, **zero quarantine directories**.

⚠ **THE FALSIFIER CANNOT FIRE, so state the narrow claim.** An adversarial review of the experiment
established that `ARTIFACT_ROOTS = ("docs/reviews",)` (`codex-review.py:283`), `watched_dirs()` returns
only `dirname(--out)` plus `<repo>/docs/reviews` (`:286`), and `dir_snapshot()` uses `os.listdir()`
with **no recursion** (`:332`). A writer confined to `~/explainers/` can therefore *never* appear in a
watched directory, whatever the timing. What T4 licenses:

> A page-building fork that honours the write rule is **invisible to this repo-artifact detector**.

What it does **not** license: *"forks are safe beside reviews."* Other interference channels are
untouched and unmeasured — CPU contention, and a shared Postgres, which this project has already seen
produce a **false Blocking** from two concurrent reviewers. **The §5 conservative rule may be lifted
for this mechanism only**, and the sentence that replaces it must say which mechanism.

The reviewer also noted there is **no discriminating scenario at all** while the agent honours the
rule — a rule whose violation this instrument cannot observe. That is worth knowing and is not a
defect in the rule.

---

## 9. DECISION — the split is adopted (user, 2026-09-08)

> *"Keep the split, and treat the trial as passed. A fork researches and writes; the main session
> executes the finished page and only then hands it over. The step that must stay undelegated is
> verification — that is what earned its keep today."*

**This closes §7's first open item.** The question was never whether the split was elegant; it was
whether a measured cost bought an inferred benefit. It ran once, and the benefit stopped being
inferred.

**What the decision fixes, and what it deliberately does not:**

| | |
|---|---|
| **Fixed — the default** | a fork researches, writes the fragment and composes; the parent executes §5b and delivers |
| **Fixed — the invariant** | ⛔ **verification is never delegated.** This is the load-bearing half. It is the step that caught 1.03:1, and it is the one a fork's prose report structurally cannot substitute for |
| **NOT fixed** | that every page must be forked. A trivial page built inline is fine — what may never happen is a page reaching the human that the parent did not execute |

⚠ **The falsifier for this decision, stated so it can expire rather than calcify:** if a future page
is built by a fork and §5b finds nothing on several consecutive runs, the *verification* half is
still justified (it is cheap and the failure it prevents is silent), but the *forking* half should be
re-argued on cost — the benefit is context saved, and that number moves with model context limits.
Re-read the measured figures in §8 before assuming they still hold.

**Recorded here rather than only in the roadmap** because this file is the spec a future reader opens
to ask *"why is it built this way?"*, and the answer is now an observation instead of an argument.
