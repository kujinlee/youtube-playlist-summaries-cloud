# Dashboard asks state their choices — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** v1 — design approved by the user 2026-08-31 in conversation. Extends
[`2026-08-28-project-dashboard-design.md`](2026-08-28-project-dashboard-design.md) §4, §5 and §6.2;
does not supersede it.

**Reported by the user, 2026-08-31**, reading the live page: *"current dashboard has three 'needs
you' item cards, but it doesn't specifically say what I can do. It just say merge or not but not
specifying PR. When it flags 'need me', it should list my choices clearly."*

---

## 1. The two defects, measured

### 1a. The page contradicts itself

`scripts/gen-dashboard.py` answers "does this need you?" in **two places, from two different
sources**:

| Site | Expression | Answer today |
|---|---|---|
| The tray (`:691`) | `unresolved(entries)` — flagged entries **not cleared** by a later `[resolved: <id>]` (`:439-451`) | `[]` → renders *"Nothing needs you."* (`:716`) |
| The entry card (`:768`) | `e["needs_you"]` — the **raw authored flag**, which nothing ever clears | three cards render the `needs you` badge |

Measured 2026-08-31 against `docs/dashboard-entries.md` at `7183111`:

```
raw needs_you flags : ['2026-08-29/1', '2026-08-30/5', '2026-08-30/6']
unresolved (tray)   : []
```

All three were resolved — line 44 carries `[resolved: 2026-08-29/1]`, line 923 carries
`[resolved: 2026-08-30/5] [resolved: 2026-08-30/6]`. **The tray is correct; the three badges are
residue.** The badge is the louder of the two: it is coloured, and there are three of them against
one line of body text.

⚠ This is the failure the parent spec exists to prevent, occurring inside the parent spec's own
renderer. §6.2's resolution rule was added *"because round 3 found §4 could only ever grow"* — the
tray learned to shrink and the card did not.

### 1b. An ask names a topic, not a decision

Neither row shape in the tray states a choice:

- **Entry ask** (`:692-694`) renders `{entry title} {date · id}`. The title is the entry's first
  sentence — a headline. The *"Waiting on you:"* sentence lives in the folded prose and never
  reaches the tray.
- **PR ask** (`:700-702`) renders `Pull request #N — {title} (open)`. It names the number and
  **emits no link**.

The three real asks show the range the design must carry:

| id | what it actually asked |
|---|---|
| `2026-08-30/6` | *"Waiting on you: whether to merge, and nothing else."* — one binary decision |
| `2026-08-30/5` | *"Two things are waiting on you. One is whether to merge... The other is a recommendation:"* — **two** decisions in one entry, one of them accept/reject on a judgement call |
| `2026-08-29/1` | *"**Waiting on you:** CI now checks the plan document against the code... nothing says when it stops applying"* — **a risk, offering no decision at all** |

That last row is load-bearing. The glossary (`:677`) promises `needs you` means *"a decision is
waiting on you"*. `2026-08-29/1` broke that promise on the first day the dashboard existed, and the
grammar permitted it.

---

## 2. Scope

**In:** a second entry category (`heads-up`) · a decision block in the `needs-you` grammar ·
derived badges · a "Worth knowing" block · live PR state on options that name a PR · one validator
with two callers · falsifiers and mutations for all of it.

**Out:** acting from the page. No merge button, no state-changing control. The user asked to
**see** the choices; merging stays a human gate performed in its own tool. Also out: any change to
`POST /questions`, the chart's window, or the entry gate's existing NO-ENTRY path.

---

## 3. Two categories, and the rule for each

**Decided with the user 2026-08-31.**

| Category | Means | Must carry | Appears in |
|---|---|---|---|
| `needs-you` | a decision is blocked on the reader | **≥1 decision, each with ≥2 options** | "What needs you" |
| `heads-up` | worth knowing; asks for nothing | prose explaining it — no options | "Worth knowing" |

**They render in separate blocks under separate headings.** The entire defect in §1a was two
promises under one heading; merging them back with different badge colours rebuilds it. Separation
is what keeps *"Nothing needs you."* a trustworthy all-clear on a day that has three heads-ups.

**Both are cleared by the same `[resolved: <id>]` marker. There is no expiry.**

> ⚠ **The rejected alternative, and why.** Ageing heads-ups out after the chart window would let the
> block self-clean. It is refused because `scripts/check-vocabulary-collisions.py` exists to enforce
> *one mechanism per concern* — "this item is finished with" already has a mechanism, and a second
> one would eventually disagree with the first about the same entry. A long block means things need
> resolving; the page should say so rather than tidy itself.

**A heads-up does not colour the chart.** Parent spec §5 defines orange as *"that day has an
unresolved `needs-you` entry"*. Orange is the page's one loud signal; spending it on items that ask
nothing devalues it. Unchanged.

---

## 4. Grammar — an addendum to parent §6.2

The header grammar gains exactly one flag. `FLAG` in `scripts/check-dashboard-entry.py:26` becomes:

```
[(needs-you|heads-up|resolved:\s*[^\]]*)]
```

⚠ **`scripts/gen-dashboard.py:369-383` must be extended in the same change.** Its own comment
records that adding an alternative to `FLAG` while leaving the parser's `if/elif/else` alone left
the gate's suite fully green and made `f.split(":", 1)[1]` raise `IndexError` on **every** render —
the page stopped existing rather than degrading one entry. A `heads-up` flag reaching that `else`
is the identical bug. This is a falsifier in §9, not a note.

### The decision block

Inside a `[needs-you]` entry's plain prose:

```
## 2026-08-30 [needs-you]
The tool that deliberately breaks our own code can no longer touch the pages you read.

**Decide:** Merge the mutation-harness change
- merge PR #181 [recommended]
- hold it and tell me what to change
- close it unmerged

**Decide:** Accept or reject my re-measurement of the guard stack
- keep all four layers — cost per page quartered when sharing landed [recommended]
- flatten it as the August review originally said
- park it; I will re-measure after the next milestone
<!--tech-->
```

| Rule | Definition |
|---|---|
| Decision opener | a line whose first non-space content is exactly `**Decide:**`, followed by the question |
| Options | the markdown list items (`- `) beginning on the **line immediately after** the opener. A blank line, or any non-list line, ends the list. No blank line is permitted between the opener and the first option |
| Minimum | **≥1 decision per `needs-you` entry; ≥2 options per decision** |
| Recommendation | **optional.** At most one option per decision may end with `[recommended]`. Two is malformed |
| PR reference | the literal token **`PR #N`** (N = digits) names pull request N; the renderer resolves its live state (§6) |
| Placement | decision blocks live in the plain section, before `<!--tech-->`; one in the tech section is not a decision |
| In a `heads-up` | a `**Decide:**` line is **malformed** — a heads-up that asks something is a `needs-you` |
| Both categories at once | `[needs-you]` and `[heads-up]` on one header is **malformed** — an entry is one or the other |

> ⚠ **The PR reference is `PR #N`, never a bare `#N`, and that is not stylistic.** This repo writes
> `#N` constantly for backlog rows — *"backlog #74"*, *"#76/#77"* — so an option reading
> *"close backlog #74"* under a bare-`#N` rule would resolve pull request 74 and render a confident,
> wrong link. The user's standing instruction is to **qualify every reference's namespace**; here it
> is also what makes the rule mechanically safe.

**Why `[recommended]` is optional** (user decision, 2026-08-31): *"optional, but mark it when you
have one."* A mandatory marker would force a preference to be manufactured on asks where none is
held, and a nudge that isn't meant is worse than silence. The rule is that a held view must be
**marked rather than buried in the prose**.

---

## 5. What the page renders

### 5a. "What needs you"

One row per **decision** — not per entry. `2026-08-30/5` therefore contributes two rows, which is
the honest count of what is blocked on the reader.

Each row states the question, then its options as a list, **unfolded**. Parent §4 requires this
block be *"first, unfolded"*; an ask whose options need a click has not stated them. An option
naming a PR carries a link to it.

### 5b. "Worth knowing"

Below the needs-you block. One row per unresolved `heads-up`, showing its **title sentence and its
first paragraph, unfolded**, and linking to the entry for the rest.

⚠ **Unfolded is the requirement, not a preference.** An entry's prose otherwise lives inside the
`<details id="…-plain">` fold (`:774-776`). A heads-up whose explanation is behind a click has not
explained anything — the user's words were *"say heads-up **and explain it**"*. The first paragraph
bounds the cost; the link carries the remainder.

**Omitted entirely when there are none** — a heading over nothing is a claim nobody made.

### 5c. The badge — the fix for §1a

The card badge stops reading the authored flag and reads derived state, from the same source as the
tray:

| Entry state | Badge today | Badge after |
|---|---|---|
| unresolved `needs-you` | `needs you` | `needs you` |
| unresolved `heads-up` | — | `heads-up` |
| **resolved, either kind** | **`needs you`** ← the defect | `resolved`, muted |
| no flag (an ordinary entry) | — | — (unchanged) |
| malformed | no badge; renders under *"Could not parse this entry"* | unchanged |

`resolved` is kept rather than dropped: reading back through the log, it is useful to see that an
entry *was* an ask and has since been closed. It must not shout.

### 5d. Glossary and legend

`gen-dashboard.py:677` gains `heads-up` and `resolved`. The `needs you` gloss is unchanged and
becomes true for the first time.

---

## 6. Live PR state

When an option names `#N`, the renderer resolves N through the existing `_gh_json` helper
(`:494`) and renders one of:

| PR state | Rendered |
|---|---|
| open | the option, linked |
| merged / closed | the option, linked, marked **stale — already merged/closed** |
| `gh` failed | the option, linked, marked **could not check** |

The stale case is the one that matters: it is exactly the trap the user hit by hand this morning —
a page sending them at a decision that no longer exists.

⚠ **Bounded like every other subprocess here.** `_gh_json` already imposes a timeout; the resolver
issues **one** `gh pr view` per distinct PR number per render, never per option.

---

## 7. Cannot-run is a failure

Parent §4: *"It must distinguish 'nothing needs you' from 'I could not tell'."* Extended:

| Dead input | Page says |
|---|---|
| entry store unreadable | existing `store_note` — *"Treat this as NOT CHECKED"* |
| `gh pr list` fails | existing `pr_note` |
| **`gh pr view` fails for an option's PR** | that option marked *"could not check"* — **never silently rendered as live** |

These compose. Two dead inputs produce two notes; none masks another. This preserves the shape
already built at `:695-714`.

---

## 8. Where the rule is enforced — one validator, two callers

`scripts/check-dashboard-entry.py` already owns the entry-header grammar and states so at `:24`
(*"ONE definition, imported by scripts/gen-dashboard.py"*). It gains one function:

```
decision_errors(plain: str, category: str) -> list[str]
```

Called by **both**:

1. **The gate** — `check-dashboard-entry.py` refuses a branch whose new `[needs-you]` entry carries
   no valid decision, naming what is missing.
2. **The renderer** — `gen-dashboard.py:parse_entries` sets `entry["error"]`, so a malformed entry
   renders in place under the existing *"Could not parse this entry"* card (§6.2's malformed-block
   rule) instead of appearing as a well-formed ask with nothing to do.

**One implementation.** Two copies would drift, and this project has measured that: a
re-implemented renderer's rules disagreed with the renderer and put fabricated text on a live page.
The seam matches `page_markup.py` — one renderer, four callers — built after four inline copies
diverged.

---

## 9. Falsifiers

Each names the observation that makes it **fail**.

| Falsifier | Fails if |
|---|---|
| **Badge is derived** | an entry cleared by a later `[resolved:]` still renders the `needs you` badge. *(This is §1a; it fails on today's build.)* |
| **`heads-up` reaches the parser** | adding `heads-up` to `FLAG` without extending `gen-dashboard.py:369-383` — the render must not raise, and the flag must not fall to `unrecognised flag` |
| **Decision required** | a `[needs-you]` entry with no `**Decide:**` block passes the gate |
| **Two options required** | a decision with one option passes |
| **One recommendation** | a decision with two `[recommended]` options passes |
| **Heads-up cannot ask** | a `[heads-up]` entry containing `**Decide:**` passes |
| **One category per entry** | a header carrying both `[needs-you]` and `[heads-up]` passes |
| **Options are unfolded** | a decision's options are rendered inside a `<details>` |
| **Heads-up explains on sight** | a heads-up's first paragraph is rendered only inside the `<details>` fold |
| **A backlog `#N` is not a PR** | an option reading `close backlog #74` resolves or links pull request 74 |
| **Stale PR is marked** | an option naming a merged PR renders identically to one naming an open PR |
| **`gh` failure is loud** | `gh pr view` failing renders the option as though it were checked |
| **Separate blocks** | a `heads-up` appears under the "What needs you" heading |
| **Empty worth-knowing** | the "Worth knowing" heading renders with no items beneath it |
| **Gate and renderer agree** | a `[needs-you]` entry the gate accepts renders as a broken entry, or the reverse |

**Mutation coverage.** New behaviour gets manifest entries in
`scripts/mutations/{gen-dashboard,check-dashboard-entry}.json`, and `EXPECTED_MUTATIONS`
(`scripts/check-plan-code.py:432-451`) rises from `gen-dashboard.py: 47` and
`check-dashboard-entry.py: 12` by the number added. **Coverage cannot shrink** — the pin refuses a
lower count, and duplicate names or anchors are refused, so a count cannot be held by replacing one
entry with a copy of another.

**Not measured by any of the above: whether the reader can now act.** Only the user can report
that.

---

## 10. What this does NOT enforce, stated rather than hidden

- **Option wording is not validated beyond structure.** An earlier draft proposed requiring each
  option to begin with a verb. There is no verb detector — only a wordlist pretending to be one,
  which would reject valid options and accept invalid ones while reporting confidence. Verb form is
  a **writing convention**, not a gate. What *is* mechanically checked: the count of options, the
  count of recommendations, and the presence of a decision.
- **It cannot tell whether the options are the right ones.** A `needs-you` offering two useless
  choices passes every check here. The gate defends the *shape* of an ask, never its quality.
- **It does not read the page.** Every falsifier above runs against the generator and the store. The
  affordance and fold-survival probes in parent §9 remain the only checks that touch rendered HTML.

---

## 11. Existing entries are not rewritten

The store is append-only (parent §6.2). The three entries in §1a stay exactly as written —
including `2026-08-29/1`, which under the new rule would be a `heads-up`. All three are already
resolved, so once the badge is derived they render as `resolved` and the contradiction is gone
without editing history.

**Consequence, stated so it is not oversold:** the visible defect dies with §5c. The grammar work in
§4 changes nothing on the page as it stands today — it is what makes the **next** "whether to merge"
name its pull request and link to it.

---

## 12. Decisions taken

| # | Decision | By |
|---|---|---|
| 1 | `needs you` must offer real actions with details; awareness-only becomes `heads-up` | user, 2026-08-31 |
| 2 | `[recommended]` optional; a held view must be marked, not buried | user, 2026-08-31 |
| 3 | Separate "Worth knowing" block; same `[resolved:]` mechanism; no expiry; no chart colour | user, 2026-08-31 |
| 4 | One validator, two callers | user, 2026-08-31 (after clarification) |
| 5 | The page is read-only — no merge control | this spec, §2 |

No open questions.
