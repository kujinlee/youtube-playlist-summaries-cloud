# Dashboard asks state their choices — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** **v2 — round 1 folded in. NOT CONVERGED at v1**; both halves independently returned two
Blocking findings and they agreed on both. Reviews retained at
`docs/reviews/spec-dashboard-ask-choices-r1-{codex,claude}.md`
(Codex `gpt-5.5`: 2 Blocking, 3 High, 4 Medium, 1 Low. Claude: 2 Blocking, 5 High, 8 Medium, 4 Low.)

Extends [`2026-08-28-project-dashboard-design.md`](2026-08-28-project-dashboard-design.md) §4, §5,
§6.2; does not supersede it. §13 records the fold.

**Reported by the user, 2026-08-31**, reading the live page: *"current dashboard has three 'needs
you' item cards, but it doesn't specifically say what I can do. It just say merge or not but not
specifying PR. When it flags 'need me', it should list my choices clearly."*

⚠ **One decision needs re-taking by the user — see §3's box.** The v1 justification for "no expiry"
invoked a script that cannot reach this concern. The decision may stand; the reasoning does not.

---

## 1. The two defects, measured

### 1a. The page contradicts itself

`scripts/gen-dashboard.py` answers "does this need you?" in **two places, from two different
sources**:

| Site | Expression | Answer today |
|---|---|---|
| The tray (`:691`) | `unresolved(entries)` — flagged entries **not cleared** by a later `[resolved: <id>]` (`:439-451`) | `[]` → renders *"Nothing needs you."* (`:716`) |
| The entry card (`:768`) | `e["needs_you"]` — the **raw authored flag**, which nothing ever clears | three cards render the `needs you` badge |

Measured 2026-08-31 against `docs/dashboard-entries.md` at `7183111`, and **independently reproduced
by the round-1 Claude reviewer**:

```
raw needs_you flags : ['2026-08-29/1', '2026-08-30/5', '2026-08-30/6']
unresolved (tray)   : []
```

Line 44 carries `[resolved: 2026-08-29/1]`; line 923 carries `[resolved: 2026-08-30/5]
[resolved: 2026-08-30/6]`. **The tray is correct; the three badges are residue.**

⚠ This is the failure the parent spec exists to prevent, occurring inside the parent spec's own
renderer. §6.2's resolution rule was added *"because round 3 found §4 could only ever grow"* — the
tray learned to shrink and the card did not.

### 1b. An ask names a topic, not a decision

- **Entry ask** (`:692-694`) renders `{entry title} {date · id}` — a headline. The *"Waiting on
  you:"* sentence lives in the folded prose and never reaches the tray.
- **PR ask** (`:700-702`) renders `Pull request #N — {title} (open)` and **emits no link**.

The three real asks show the range the design must carry:

| id | what it actually asked |
|---|---|
| `2026-08-30/6` | *"Waiting on you: whether to merge, and nothing else."* — one binary decision |
| `2026-08-30/5` | *"Two things are waiting on you…"* — **two** decisions, one an accept/reject on a judgement call |
| `2026-08-29/1` | *"**Waiting on you:** CI now checks the plan document against the code…"* — **a risk, offering no decision at all** |

The glossary (`:677`) promises `needs you` means *"a decision is waiting on you"*. `2026-08-29/1`
broke that promise on the first day the dashboard existed, and the grammar permitted it.

---

## 2. Scope

**In:** a second entry category (`heads-up`) · a decision block in the `needs-you` grammar ·
derived badges · a "Worth knowing" block · live PR state on options carrying `PR #N` · one validator
with two callers · falsifiers and mutations for all of it.

**Out:** acting from the page. No merge button, no state-changing control. The user asked to
**see** the choices; merging stays a human gate performed in its own tool. Also out: any change to
`POST /questions` or the chart's window.

⚠ **NOT out of scope, corrected from v1:** the entry gate's `NO-ENTRY:` path. `verdict` consults
`exemption_reason` only when `added_entry` is false (`check-dashboard-entry.py:145-158`), so the new
validation interacts with that ordering and §8 must state where it sits.

---

## 3. Two categories, and the rule for each

**Decided with the user 2026-08-31.**

| Category | Means | Must carry | Appears in |
|---|---|---|---|
| `needs-you` | a decision is blocked on the reader | **≥1 decision, each with ≥2 options** | "What needs you" |
| `heads-up` | worth knowing; asks for nothing | prose explaining it — no options | "Worth knowing" |

**They render in separate blocks under separate headings.** The entire defect in §1a was two
promises under one heading; merging them back with different badge colours rebuilds it.

**Both are cleared by the same `[resolved: <id>]` marker. There is no expiry.**

> ⚠ **RE-DECISION NEEDED — v1's justification for this was wrong.**
>
> v1 refused an expiry on the grounds that `scripts/check-vocabulary-collisions.py` enforces *one
> mechanism per concern*. **Both reviewers rejected that and they are right.** Measured: that script
> holds `TABLES = ("video_artifacts", "video_generations", … "spend_ledger")` and
> `MECHANISM_STEMS = ("lease", "token", "lock", "claim", …)` — it compares **database column-name
> stems across tables**. It cannot see a dashboard entry and would never have fired on an expiry.
> The spec claimed mechanical backing that does not exist, which is a green check over the wrong
> subject — the failure this project is most alert to.
>
> **The honest argument for no-expiry, without borrowed authority:** a heads-up that ages out
> silently is indistinguishable from one that was dealt with, and this page's whole purpose is that
> absence and denial must not look alike (parent §4). An expiry would also add a second answer to
> "is this item finished with", and the two would eventually disagree — that reasoning is sound on
> its own; it just is not *enforced* by anything today.
>
> **The decision stands unless the user overturns it.** Recorded here because they approved it partly
> on reasoning that has since failed.

**A heads-up does not colour the chart.** Parent §5 defines orange as *"that day has an unresolved
`needs-you` entry"*. Unchanged.

---

## 4. Grammar — an addendum to parent §6.2

`FLAG` in `scripts/check-dashboard-entry.py:26` gains one alternative. Written exactly (v1's version
left the brackets unescaped and would not have matched):

```python
FLAG = re.compile(r"\[(needs-you|heads-up|resolved:\s*[^\]]*)\]")
```

⚠ **`scripts/gen-dashboard.py:369-383` must be extended in the same change.** Its own comment records
that adding an alternative to `FLAG` while leaving the parser's `if/elif/else` alone left the gate's
suite fully green and made `f.split(":", 1)[1]` raise `IndexError` on **every** render — the page
stopped existing rather than degrading one entry. A `heads-up` flag reaching that `else` is the
identical bug.

### The decision block

```
## 2026-08-30 [needs-you]
The tool that deliberately breaks our own code can no longer touch the pages you read.

**Decide:** Merge the mutation-harness change
- merge PR #181 [recommended]
- hold it and tell me what to change
- close it unmerged
<!--tech-->
```

| Rule | Definition |
|---|---|
| Decision opener | a line whose first non-space content is exactly `**Decide:**`, followed by **non-empty** question text |
| Recognition context | recognised **only outside** fenced code, indented code, HTML comments and blockquotes — see the box below |
| Options | list items beginning on the **line immediately after** the opener. Marker is `-`, `*` or `+`. A blank line, a non-list line, or a new opener ends the list |
| Option text | after removing the marker and any trailing `[recommended]`, must be **non-empty** |
| Nesting | a list item indented more than the first option is a **continuation of it**, not a new option |
| Minimum | **≥1 decision per `needs-you` entry; ≥2 options per decision** |
| Recommendation | **optional.** At most one option per decision may end with `[recommended]`. Two is malformed |
| Adjacent decisions | a second `**Decide:**` may follow the previous option list with or without a blank line |
| PR reference | the literal token **`PR #N`** (N = digits) names pull request N (§6) |
| Placement | decision blocks live in the plain section, before `<!--tech-->` |
| In a `heads-up` | a recognised `**Decide:**` is **malformed** |
| Both categories at once | `[needs-you]` and `[heads-up]` on one header is **malformed** |

> ⚠ **Reuse `exemption_reason`'s scanner — do not write a fifth one.**
> `check-dashboard-entry.py:83-138` already solves exactly this problem for `NO-ENTRY:`, and each
> branch records a **measured** escape: fenced code with the CommonMark closing-length rule
> (`:104-111`), indented code counting tab stops (`:63-80`), HTML comments spanning lines
> (`:114-132`), blockquotes.
>
> **This is not hypothetical.** The dashboard entry announcing this very feature will quote
> `**Decide:**` inside a fenced example. Under a naive line scan, that entry trips §9's *"heads-up
> cannot ask"* falsifier and the gate refuses the branch that documents the grammar.

> ⚠ **`PR #N`, never a bare `#N`.** This repo writes `#N` for backlog rows constantly — *"backlog
> #74"*, *"#76/#77"*. Under a bare-`#N` rule, *"close backlog #74"* resolves pull request 74 and
> renders a confident, wrong link.

**Why `[recommended]` is optional** (user decision): *"optional, but mark it when you have one."* A
mandatory marker forces a preference to be manufactured where none is held. A held view must be
**marked rather than buried in the prose**.

---

## 5. What the page renders

### 5a. "What needs you"

One row per **decision**, not per entry — `2026-08-30/5` would contribute two, the honest count of
what is blocked on the reader. Each row states the question, then its options as a list,
**unfolded**; parent §4 requires this block be *"first, unfolded"*, and an ask whose options need a
click has not stated them. An option carrying `PR #N` is linked.

⚠ **The same decision block also lands in the entry card's prose** (`:774-776`, rendered through
`page_markup.py`). Its appearance there is specified as: rendered as ordinary markdown by the shared
renderer, with no special-casing. The tray is the actionable surface; the card must not silently
render a *different* option list from the tray's.

### 5b. "Worth knowing"

Below the needs-you block. One row per unresolved `heads-up`, showing its **first paragraph,
unfolded**, and linking to the entry.

⚠ **Corrected from v1**, which said *"title sentence and first paragraph"*. The title **is** the
first sentence of the first paragraph (`:405-411`), so v1 specified rendering it twice.

⚠ **Unfolded is the requirement.** An entry's prose otherwise lives inside `<details id="…-plain">`
(`:774-776`). The user's words were *"say heads-up **and explain it**"*; an explanation behind a
click has not explained.

**Omitted entirely when there are none — but only when the store was read successfully.** On
`store_error` the heading renders with the NOT CHECKED note. Otherwise two individually correct
dead-input rules compose into a silent one: zero parsed heads-ups from an unreadable store would
omit the heading, and a missing heading reads as *"nothing worth knowing"*.

### 5c. The badge — the fix for §1a

| Entry state | Badge today | Badge after |
|---|---|---|
| unresolved `needs-you` | `needs you` | `needs you` |
| unresolved `heads-up` | — | `heads-up` |
| **resolved, either kind** | **`needs you`** ← the defect | `resolved`, muted |
| no flag (ordinary entry) | — | — (unchanged) |
| malformed | no badge; *"Could not parse this entry"* | unchanged |

### 5d. Glossary and legend

`:677` gains `heads-up` and `resolved`. **The `needs you` gloss is trimmed** to *"a decision is
waiting on you"*, dropping *"— nothing else on the page is asking for anything"*. That second clause
was already untrue of the open-PR rows in the same tray (`:700-702`) and a "Worth knowing" block
makes it plainly false. v1 claimed the gloss *"becomes true for the first time"*; only the first
clause does.

---

## 6. Live PR state

When an option carries the token **`PR #N`**, the renderer resolves N through the existing
`_gh_json` helper (defined `:490`) and renders one of:

| PR state | Rendered |
|---|---|
| open | the option, linked |
| merged / closed | the option, linked, marked **stale — already merged/closed** |
| no such PR | the option, marked **no such pull request** |
| `gh` failed, or unexpected JSON shape | the option, marked **could not check** |

The stale case is the one that matters: it is the trap the user hit by hand, a page sending them at
a decision that no longer exists.

**Shape validation is required, not implied.** `_gh_json` only parses JSON; `open_prs` validates
shape separately. The resolver must name its fields explicitly —
`gh pr view N --json number,state` — and treat any missing or unexpected field as **could not
check**, never as a state.

⚠ **The bound is on the TOTAL, corrected from v1.** `_gh_json` imposes `timeout=30` **per call**
(`:495`), so v1's *"bounded like every other subprocess here"* was wrong: ten distinct PRs is ten
timeouts, not one. The resolver issues **at most one call per distinct PR number per render**, and
the render is bounded by a total budget across all PR lookups; on exhaustion the remaining options
render **could not check**.

---

## 7. Cannot-run is a failure

Parent §4: *"It must distinguish 'nothing needs you' from 'I could not tell'."* Extended:

| Dead input | Page says |
|---|---|
| entry store unreadable | existing `store_note` — *"Treat this as NOT CHECKED"* |
| `gh pr list` fails | existing `pr_note` |
| `gh pr view` fails / bad shape for an option's PR | that option marked *"could not check"* |
| **a `needs-you` entry that fails `decision_errors`** | **the tray renders "could not read one ask", naming the entry id** |
| store unreadable, for the Worth-knowing block | the heading renders with the NOT CHECKED note (§5b) |

> ⚠ **The fourth row is the one v1 missed, and it is the one the new mechanism itself creates.**
> `unresolved` filters `e["needs_you"] and not e["error"]` (`:451`). Once `decision_errors` can set
> `entry["error"]`, a `[needs-you]` entry with a **typo in its decision block** is excluded from the
> tray, `rows` is empty, `store_error` is `None`, and `build` falls through to
> `'<p class="none">Nothing needs you.</p>'` (`:716`) — in green.
>
> **An authoring slip would convert a live ask into a confident all-clear: §1a, rebuilt by its own
> fix.** A malformed ask must be *louder*, never quieter.

These compose. Multiple dead inputs produce multiple notes; none masks another.

---

## 8. Where the rule is enforced — one validator, two callers

`scripts/check-dashboard-entry.py` owns the entry-header grammar and says so at `:24`. It gains:

```python
decision_errors(plain: str, category: str) -> list[str]
```

### 8a. The gate — v1 specified a call it could not make

⚠ **v1 was unbuildable and both reviewers caught it.** `collect()` (`:241-254`) runs
`git diff -U0` and reduces the whole patch to a boolean —
`added = any(_added_entry_line(l) for l in patch.stdout.split("\n"))` — and `verdict()` takes
`added_entry: bool`. With zero context lines the entry **body is not in the patch at all**. There is
no `plain` to pass. A branch adding `+## 2026-08-31 [needs-you]` with no decision block would set
`added=True` and `verdict()` would return success before any grammar could run: *a shared validator
silently checking nothing in the highest-risk caller.*

**v2:** `collect()` returns the **added entry ids**, not a boolean. The gate then reads
`docs/dashboard-entries.md` **from the working tree** — a path it already names in `EXEMPT_FILES`
(`:21`) — parses it with the shared parser, and calls `decision_errors` on each entry the diff
added. `verdict()` fails when any added entry's list is non-empty, naming the entry and what is
missing.

**Ordering with `NO-ENTRY:`.** `verdict` consults `exemption_reason` only when `added_entry` is
false (`:145-158`). Decision validation runs on the *added-entry* branch, so a `NO-ENTRY:` branch is
unaffected: it adds no entry and reaches the exemption path unchanged.

### 8b. The renderer

`gen-dashboard.py:parse_entries` sets `entry["error"]`, so a malformed entry renders in place under
*"Could not parse this entry"* (§6.2's malformed-block rule) — **subject to the cutover in §11**, and
**never by disappearing from the tray** (§7's fourth row).

**One implementation, two callers.** Two copies would drift; this project has measured that — a
re-implemented renderer's rules disagreed with the renderer and put fabricated text on a live page.
Matches the `page_markup.py` seam: one renderer, four callers, built after four inline copies
diverged.

---

## 9. Falsifiers

Each names the observation that makes it **fail**. ⚠ **Every row requires a paired positive and
negative fixture, and must assert the responsible output** — not merely the absence of a bad string.
v1's rows were largely absence assertions, which pass when the feature is missing entirely.

| Falsifier | Fails if |
|---|---|
| **No historical entry breaks** | **any** entry in the store at `7183111` renders malformed after the change *(this is B1; it fails against a naive implementation)* |
| **Badge is derived** | an entry cleared by a later `[resolved:]` still renders the `needs you` badge *(fails on today's build)* |
| **Malformed ask is louder, not quieter** | a store whose only `needs-you` entry has a broken decision block renders *"Nothing needs you."* |
| **Gate sees bodies** | a branch adding a `[needs-you]` header with no decision block passes the gate |
| **`heads-up` reaches the parser** | the `heads-up` flag falls to `unrecognised flag`, **or** the flag loop is made exception-proof by a `try/except` rather than by handling the case *(v1's "must not raise" was satisfiable by swallowing)* |
| **Two options required** | a decision with one option passes |
| **Non-empty text** | `**Decide:**` with no question, or an option that is only `[recommended]`, passes |
| **One recommendation** | a decision with two `[recommended]` options passes |
| **Heads-up cannot ask** | a `[heads-up]` containing a recognised `**Decide:**` passes |
| **Inert markdown is inert** | a `**Decide:**` inside a fence, indented code, HTML comment or blockquote is counted as a decision |
| **One category per entry** | a header carrying both flags passes |
| **Options are unfolded** | the tray's options are absent from the page, **or** present only inside a `<details>` |
| **Heads-up explains on sight** | a heads-up's first paragraph is absent, **or** rendered only inside the fold |
| **Worth-knowing NOT CHECKED** | an unreadable store omits the Worth-knowing heading silently |
| **Stale PR is marked** | an option naming a merged PR renders identically to one naming an open PR |
| **A backlog `#N` is not a PR** | an option reading `close backlog #74` links or resolves pull request 74 |
| **`gh` failure is loud** | a failed or malformed `gh pr view` renders the option as though checked |
| **PR lookups are bounded** | a render with many distinct PR numbers exceeds the total budget without degrading to *"could not check"* |
| **Gate and renderer agree** | the gate accepts an entry the renderer marks malformed, **or** both accept an entry violating a rule in §4 *(v1's version passed when both were broken the same way)* |

**Mutation coverage.** New behaviour gets entries in
`scripts/mutations/{gen-dashboard,check-dashboard-entry}.json`; `EXPECTED_MUTATIONS`
(`check-plan-code.py:443,:445`) rises from `gen-dashboard.py: 47` and `check-dashboard-entry.py: 12`
by the number added. Coverage cannot shrink — the pin refuses a lower count, and
`check-plan-code.py:496-504` refuses duplicate names **and** duplicate edit anchors, so a count
cannot be held by copying an entry.

**Not measured by any of the above: whether the reader can now act.** Only the user can report that.

---

## 10. What this does NOT enforce, stated rather than hidden

- **Option wording is not validated beyond structure.** There is no verb detector — only a wordlist
  pretending to be one, which would reject valid options and accept invalid ones while reporting
  confidence. What *is* checked: option count, recommendation count, non-empty text, and the
  presence of a decision.
- **It cannot tell whether the options are the right ones.** A `needs-you` offering two useless
  choices passes every check here. The gate defends the *shape* of an ask, never its quality.
- **It does not read the rendered page.** Every falsifier runs against the generator and the store.
  The affordance and fold-survival probes in parent §9 remain the only checks touching HTML.

---

## 11. Existing entries — the cutover

The store is append-only (parent §6.2). **v1 claimed the grammar work changes nothing on today's
page. That was false, and the reviewers measured it.**

Simulated against the real store with the real pass-2 code, a naive implementation breaks **five**
entries — three directly, two by cascade, because `parse_entries` builds `ids` from `not e["error"]`
(`:418`) so the entries carrying the clearing markers hit `:427-429`:

```
2026-08-29/1  a [needs-you] entry with no **Decide:** block
2026-08-29/2  [resolved: 2026-08-29/1] names an entry that could not be parsed…
2026-08-30/5  a [needs-you] entry with no **Decide:** block
2026-08-30/6  a [needs-you] entry with no **Decide:** block
2026-08-30/7  [resolved: 2026-08-30/5] names an entry that could not be parsed…
```

Two of those five are entries the new rule has no opinion about at all.

**v2's rule:** `decision_errors` is applied **only to entries whose header date is on or after the
cutover date**, which is the date this change merges. Entries before it are grandfathered and render
exactly as they do now. The first falsifier in §9 asserts this against the real store.

⚠ **Latent, and stated so it is not rediscovered:** `bucket_days` builds `with_entry` from
`not e["error"]` (`:458`), so if a date's *only* entries went malformed, `_bar`'s `unwritten` alarm
(`:651`) would report *"SHIPPED WITH NO ENTRY"* for a day that has one. On today's store both dates
carry other valid entries, so this does not fire — but the coupling is real and the cutover is what
keeps it dormant.

**Consequence, stated so it is not oversold:** the visible defect dies with §5c. The grammar work
changes nothing on the page as it stands — it is what makes the **next** "whether to merge" name its
pull request and link to it.

---

## 12. Decisions taken

| # | Decision | By |
|---|---|---|
| 1 | `needs you` must offer real actions with details; awareness becomes `heads-up` | user, 2026-08-31 |
| 2 | `[recommended]` optional; a held view must be marked, not buried | user, 2026-08-31 |
| 3 | Separate "Worth knowing" block; same `[resolved:]`; no expiry; no chart colour | user, 2026-08-31 — **justification withdrawn, see §3; decision open to re-taking** |
| 4 | One validator, two callers | user, 2026-08-31 |
| 5 | The page is read-only — no merge control | this spec, §2 |
| 6 | Grandfather entries before the cutover date | v2, forced by B1 |

---

## 13. Round 1 fold record

| Finding | Severity | Where fixed |
|---|---|---|
| Seam unbuildable — gate has no entry body | Blocking ×2 (both halves) | §8a rewritten: `collect()` returns entry ids; gate reads the working-tree store |
| Naive validation breaks 5 live entries | Blocking ×2 (both halves) | §11 cutover date + §9's first falsifier |
| Malformed ask silently becomes "Nothing needs you." | High | §7 fourth row + falsifier |
| Worth-knowing omitted on unreadable store | High | §5b |
| §6/§9 still said bare `#N` while §4 said `PR #N` | High / Medium | §6, §9 — the class, not the instance |
| `**Decide:**` in fences/comments/blockquotes | High | §4 recognition-context row; reuse `exemption_reason` |
| Empty opener / `- [recommended]` alone passes | High | §4 non-empty rules |
| List markers, nesting, adjacency undefined | High | §4 |
| Vacuous falsifiers (absence assertions, "both broken" agreement) | Medium ×2 | §9 preamble + rewritten rows |
| `gh pr view` shape unvalidated | Medium | §6 |
| Nonexistent PR unhandled | Medium | §6 table |
| `_gh_json` timeout is per-call, not total | Medium | §6 ⚠ box |
| Decision block's appearance in the entry card unspecified | Medium | §5a ⚠ box |
| Heads-up title rendered twice | Medium | §5b |
| `check-vocabulary-collisions.py` cited out of scope | Medium ×2 | §3 box — justification withdrawn, re-decision flagged |
| `FLAG` regex written without escaping | Medium | §4 code block |
| `_gh_json` cited at `:494`, defined at `:490` | Medium | §6 |
| `NO-ENTRY:` interaction unstated | Medium | §2, §8a |
| Glossary gloss's second clause already false | Low | §5d |
| Parent grammar says title = first line; renderer uses first sentence | Low | Recorded; parent §6.2 to be amended when this ships |

**Premises the Claude half checked and found correct** (recorded so round 2 need not re-open them):
§1a's measurement reproduces exactly; every line citation in §1a/§1b; the `:369-383` `else`-branch
warning; `check-dashboard-entry.py:24` does own the grammar; the `EXPECTED_MUTATIONS` values and the
duplicate-anchor refusal; all three ask quotations and their id mapping; §5c's malformed-no-badge
row; and that the store contains no `**Decide:**` today, so the grammar collides with nothing already
written.

**Open questions:** one — §3's expiry re-decision.
