# Adversarial review — `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` v4, round 3 (Claude half)

**Reviewer:** Claude, independent half of round 3. `docs/reviews/spec-project-dashboard-r3-codex.md`
was deliberately left unopened. Rounds 1 and 2 (both halves) were read, because this round judges
what the cut took with it.

**Method.** The v1→v4 diff was taken from git (`git show <sha>:<path>` for `eb3838e`, `91a1ec0`,
`4897947`, `f9618fc`, `4b93902`). Every round-1 and round-2 finding was walked and given a
disposition: **moot** (the thing that carried it is gone), **retained** (fixed and still fixed), or
**silently dropped** (still applies, not mentioned). Every file:line in v4 was opened. The one claim
about git merge behaviour was **executed**, not reasoned about.

**Counts:** 2 Blocking · 6 High · 8 Medium · 3 Low.

---

## IS v4 READY TO BECOME AN IMPLEMENTATION PLAN?

**No.** But it is much closer than v3, and the cut was the right call — five Blockings are genuinely
dissolved, and I verified each one rather than taking the table's word.

**The shortest list of what must change first — five items:**

1. **Say how a `needs-you` item stops needing you.** §4.1 derives the page's first block from an
   append-only log with no id and no resolution mechanism. As specified it only grows. (B1)
2. **Say whether entries are rendered once or twice**, and what happens to an entry older than the
   chart's 14 days or on a day with zero commits. §4.2 and §4.3 both claim to present the entries and
   neither references the other. (B2)
3. **Define "malformed", and give the `##` delimiter an escape rule.** Without a definition,
   *"rendered as an error in place"* and its self-test row cannot fail. (H1, H2)
4. **Address round-2 H7 — the store inherits this repo's change process** — and either withdraw
   *"conflicts are rare"* or evidence it. I falsified it by execution. (H3)
5. **Re-derive §2's three figures from git or drop them.** Two of the three are wrong, in the
   section that is the entire argument for the cut. (M1)

Items 1 and 2 are design decisions an implementer would have to invent, which is round 1's own
definition of a spec that is not ready. Items 3–5 are a day's editing.

---

## Part 1 — what the cut silently took with it

This was the highest-weighted question in the prompt, so it goes first. Every round-1/round-2 finding
that was **accepted** is below with a disposition. "Moot" means I checked that the thing carrying it
is genuinely absent from v4, not merely unmentioned.

### Genuinely moot — VERIFIED, do not re-review

| Finding | Why moot |
|---|---|
| B2 (r1 Claude) — §5.1's source did not contain what was claimed | No progress chart in v4. `grep -n "roadmap-to-launch\|milestone" <v4>` → 0 hits |
| B1 (r2 Claude) — the replacement renders 100/100/100 | Same |
| B1 (r1 Codex) — "bundled" ≠ "loadable" | No Mermaid, nothing bundled. `grep -in mermaid <v4>` → 0 hits |
| H6 (r1 Claude) — "no fallback renderer" was rationalisation | Same |
| H2 (r2 Claude) — "both paths run on every build" false for Mermaid | Same |
| H3 (r2 Claude) — `dependency_svg` draws one parked slice | No backlog section, no dependency diagram |
| H4 (r2 Claude) — §5.5b specifies a page §5.5d forbids | Both sections gone |
| Licence audit, Apache-2.0/MPL-2.0 notices | Nothing redistributed |
| Page-class change to `explainer-delivery.md` | No external asset |
| H7 (r1 Claude) — health lamps had no third state | Lamps gone, **and** v4 §4.1 carries the principle forward to what-needs-you. This is the single best change in v4 |
| H5 (r2 Claude) — §5.7 sourced from a machine-local memory dir | §5.7 re-deferred, and §2 lists it |
| M6/M7, L1/L2 (r2 Claude) — startup assertion, SVG probe, `dependency_svg` line | All Mermaid/backlog residue |
| H1 (r2 Claude) — "Nothing needs you." when the source could not be read | **FIXED**, not dissolved. §4.1's ⚠ is the correct fix |
| M5 (r2 Claude) — "benefits every existing page" unearned | **WITHDRAWN explicitly** in §6, with the reason. Also exemplary |

**§2's dissolution table is honest.** I tried to break it and could not. Five of the nine Blockings
are truly gone, the arithmetic (4 + 5 = 9) checks out against the four review files, and nothing left
in v4 needs a data source that does not exist or an asset that is not delivered. That question is
closed.

### Silently dropped — the finding still applies and v4 does not mention it

| Finding | Status |
|---|---|
| **H4 (r1 Claude)** — 14 days is shorter than the absences the page exists for; no way to look further back | ⛔ **REVERTED.** v3 §5.2 fixed it (window a parameter, a widening control, *"days beyond the window are still in the store and reachable"*). v4 §4.3 hard-codes 14 days, deletes the widening control and the reachability sentence, and demotes the whole thing to §9 open question 1: *"14 days is a guess; adjust after use."* The chart that carried the finding is **still present**, so this is not moot. Not in §2's table. → **B2** |
| **H7 (r2 Claude)** — the in-repo store inherits branch + PR + human merge gate; append-only is not conflict-free | ⛔ **STILL APPLIES, AND NOW CONTRADICTED.** The store is still `docs/dashboard-entries.md` in the repo. v4 adds *"conflicts are rare"*, which I falsified. → **H3** |
| **M1 (r1 Codex)** — duplicate derivation vs `gen-goals-page.py`; "a fourth status surface" | ⛔ **DROPPED WITHOUT DISPOSITION.** v3 §7 carried a shared-module requirement with a redesign trigger; v4 §7 deletes it in silence. §2 claims B2 (r2) GONE — true, but B2 (r2) was about *milestone state specifically*. The general concern is not addressed. → **M6** |
| **M3 (r2 Claude)** — §9 sub-criteria require page content §5 does not specify | ⚠ **PARTIALLY RECURS.** The branch/release criteria were dropped, but §8's first bullet — *"the page names the last date an entry was written"* — still has no slot anywhere in §4. → **M5** |
| **M4 (r2 Claude)** — the chart counts squashed PR merges, not work | ⚠ **HALF-FIXED.** v4 names the ref (*"first-parent"*), which was the smaller half. The metric problem is untouched and the disclosed caveat is still the wrong one. → **H5** |
| **L3 (r1 Claude) / M1 (r2 Claude)** — `explainer-delivery.md` cited with no path | ⛔ **STILL OPEN.** 8 in v3 → 3 in v4, but zero carry a path. → **L1** |
| M2 (r2 Claude) — volatile page sizes | ✅ Resolved by removal; §10 says so |

**Everything else round 1 and round 2 accepted is either moot or retained.** The two that matter are
H4 (r1) and H7 (r2): both were about mechanisms the cut *kept*, and both lost their fixes anyway.

---

# BLOCKING

## B1 — "What needs you" is derived from an append-only log with no way to mark anything resolved. The page's first block can only grow.

**Claims attacked.** §4.1 lines 83-88:

> *"One line per item awaiting the human, each naming the decision — or the words **"Nothing needs
> you."** Derived from entries flagged `needs-you`, plus open pull requests."*

against §5 lines 121, 135-136:

> *"**Store: `docs/dashboard-entries.md`**, in the repo, **append-only**."*
> *"One `##` block per entry. **Multiple entries on one day are separate blocks — the date is not a key.**"*
> *"Merge conflicts: append-only, newest at the end…"*

**What I checked.** I read §4.1, §4.2, §4.3, §5 and §9 looking for any mechanism by which a
`[needs-you]` entry ceases to need you. There is none. The store is append-only by design, an entry
carries no id, and §5 states explicitly that the date is not a key — so no later entry can *refer to*
an earlier one. `grep -n "resolv\|clear\|close\|done\|answered" <v4>` finds nothing on this subject.

**What is actually true.** On the day the first `[needs-you]` entry is written, §4.1 gains a line it
can never lose. Every subsequent one is added. Within a fortnight the first block on the page — the
answer to a third of the registered goal (`docs/anchors.md:39`) — is a growing list of decisions the
user made weeks ago, and the words *"Nothing needs you."* become unreachable for the life of the
project.

**This is a defect the cut created, and the mechanism it removed is the one that would have solved it.**
v3 §8 specified request ids and *"a **resolution line** naming that id"* — an explicit resolution
record. v4 deleted the request box (correctly; the channel has no identity, §3 is right about that),
and the resolution concept went with it. Entries never had one, and now nothing on the page does.
Round-2 H6 raised this shape against §8 — *"a handled request shows `waiting` forever"* — and it has
migrated to the block where it costs most.

**Why Blocking rather than High.** Fixing it is a design decision, not an implementation detail: it
requires either entry ids (breaking *"the date is not a key"*), or a resolution marker that violates
append-only, or restricting §4.1 to open PRs only (which discards the entry half of its stated
source). An implementer would have to pick one, and each changes what §5's store is.

*(VERIFIED: the absence of any resolution mechanism in v4, and its presence in v3 §8. INFERRED:
nothing — the growth follows from append-only plus no reference mechanism.)*

## B2 — §4.2 and §4.3 both claim to present the entries, with no stated relationship and different windows. Whether the page serves a three-week absence depends on which reading is intended, and v4 does not say.

**Claims attacked.** §3 In-2 and In-3 (lines 67-68):

> *"2. **What changed** — dated plain entries, newest first, detail folded.
>  3. **One chart** — days, which is also how you navigate into the entries."*

§4.2 line 91: *"Newest first. Each entry is three layers"* — then a table of title line, Fold 1,
Fold 2, with **no window stated**.

§4.3 lines 105-110: *"One bar per day for the **last 14 days**… **Clicking a bar opens that day's
entries below it.** That is why this is the one chart kept: it is the only one that is also
navigation."*

**What I checked.** I read §3, §4.1, §4.2, §4.3, §5 and §9 for any sentence relating the two. There
is none. §4.2 never mentions the chart; §4.3 never mentions §4.2's list. `grep -n "14 days\|window"`
→ §4.3 line 105 and §9 line 197 only; §4.2 has no window and no "all entries" statement either.

**Two readings, and they differ in whether the design meets its goal.**

- **Reading A — §4.2 is the complete list, §4.3 is a jump-to.** Then §4.3's *"which is also how you
  navigate"* is a convenience, not a requirement, and the 14-day window is harmless. But §4.3's
  claim to be *"the one chart kept… because it is the only one that is also navigation"* is then the
  justification for keeping a chart whose navigation is redundant.
- **Reading B — entries are rendered under their bars.** Then entries older than 14 days are
  **unreachable from the page**, and so is any entry on a day with zero commits — because bar height
  is commits, a zero-commit day has no bar, and there is nothing to click. §4.3 itself concedes the
  metric *"under-counts uncommitted work"*, so the chart's own admitted blind spot is exactly the
  case where an entry exists and cannot be opened. An entry about a decision, a review round, or a
  design conversation typically produces no commits at all.

**And the round-1 finding that governs this was reverted without a word.** Round-1 H4 (Claude) was
accepted: *"the absence this page exists for can exceed two weeks, and v2 gave no way to look further
back."* v3 §5.2 fixed it — *"The window defaults to 14 days and is a parameter, with a control to
widen it… Days beyond the window are still in the store (§6a) and reachable."* **v4 deletes both the
control and the reachability sentence** and moves the whole question to §9 as a guess to be adjusted
after use. §2's dissolution table does not list H4, because the chart that carried it survived the
cut. The registered goal is *"A person who was away"* (`docs/anchors.md:39`, verified) — a three-week
absence is the case the page exists for, and under reading B v4 cannot serve it.

**Why Blocking.** Round 1's own criterion: *"A plan written from this spec would have to invent the
answer, and inventing it is a design decision."* An implementer must decide whether entries render
once or twice and what happens past the window. Both choices are visible on the page and one of them
defeats the goal.

---

# HIGH

## H1 — "Malformed" is never defined, so §5's error path and §8's self-test row cannot fail. The falsifier is vacuous for exactly the case it names.

**Claims attacked.** §5 line 136: *"A malformed block is **rendered as an error in place**, never
skipped silently."* §8's check table: *"`gen-dashboard.py --self-test` | entry parsing, day
bucketing, or **the malformed-block path** mis-derives."*

**What I checked.** §5's entire grammar, quoted in full, is: an example block, plus *"One `##` block
per entry"*, plus *"Multiple entries on one day are separate blocks"*. There is no production, no
charset, no whitespace rule (the example uses **two** spaces before `[needs-you]`), no statement of
which deviations are malformed and which are merely unflagged.

**Concrete cases the spec cannot answer, each with a different right answer:**

| Input | Malformed, or valid-and-unflagged? |
|---|---|
| `## 2026-13-45  [needs-you]` | Unstated. And **an unparseable date has no sort key** — so *"rendered as an error **in place**"* has no defined place in a newest-first, date-ordered rendering, and no day to bucket into for §4.3's chart. The error path is undefined precisely for the input that triggers it |
| `## 2026-08-28  [needs you]` (space, not hyphen) | Unstated. The dangerous default is *valid, unflagged* — the entry renders normally and **silently drops out of §4.1**. A typo in the flag makes the page say nothing needs you when something does. This is the exact failure §4.1's ⚠ was written to prevent, arriving through the grammar instead of through a failed read |
| `## 2026-08-28  [Needs-You]` | Unstated |
| `## Fixed the backlog note` (no date at all) | Unstated |
| A `##` block with no `<!--plain-->` | Unstated — is a title-only entry legal? §4.2's table implies both folds always exist |
| A block with `<!--tech-->` before `<!--plain-->` | Unstated |

**Why this is High rather than Medium.** §8 lists the malformed-block path as one of three things
`--self-test` must catch. A self-test can only assert what the implementer decided "malformed" means,
so the check compares the implementation to itself. That is this project's own named shape —
`a-checklist-item-can-be-an-unfalsifiable-guard`, and `CLAUDE.md`'s *"State the observation that would
make it FAIL. If none can be named, it is a decision or an investigation wearing a checkbox."* The
row is currently a checkbox.

## H2 — `##` is the only entry delimiter and nothing is escaped, so an entry whose text contains `##`, `<!--plain-->` or `<!--tech-->` corrupts the store. The spec's own example is such an entry.

**Claim attacked.** §5's format block and *"One `##` block per entry."*

**What I checked.** §5 in full. There is no fence, no escape, no indentation rule, no "markers are
recognised only at column 0 immediately after the plain section" — nothing. Fold 2 is specified
(§4.2) to carry *"commits, paths, commands"*.

**Three concrete corruptions, in descending likelihood:**

1. **A pasted command or commit message beginning `##`.** Fold 2's stated content is exactly the
   material most likely to contain one — a shell comment, a Markdown snippet, a diff hunk of a `.md`
   file. The parser splits one entry into two, the second with a garbage date, hitting H1's
   undefined error path.
2. **An entry about the entry format.** The fenced block at §5 lines 126-133 of this very spec
   contains `## 2026-08-28  [needs-you]`, `<!--plain-->` and `<!--tech-->`. Written as a dashboard
   entry — which is precisely what one would write on the day this ships — it destroys the store.
   That is not a contrived attack; it is the first entry the feature will provoke.
3. **A marker inside prose.** `<!--plain-->` appearing in Fold 2 while explaining the format
   silently re-opens the plain section.

The write path is a skill appending free text. Round-2 H6 made the same argument about
`format_question_entry` (`explainer-serve.py:476-488`, verified: `f"\n---\n\n## {now} — {doc}\n\n{text}\n"`,
**no escaping of either field**), and v4 inherits the pattern without inheriting the warning.

## H3 — Round-2 H7 is fully applicable and unaddressed, and v4 replaces it with a claim I falsified by execution.

**Claim attacked.** §5 line 137: *"Merge conflicts: append-only, newest at the end, so **conflicts
are rare** and resolved by keeping both."*

**What I checked — EXECUTED, not reasoned about.** Two branches each appending one entry to the tail
of the same file:

```
$ git init -q . && printf '## 2026-08-01\nfirst\n' > e.md && git commit -qm base
$ git checkout -qb A && printf '## 2026-08-02\nfrom A\n' >> e.md && git commit -qam A
$ git checkout -qb B master && printf '## 2026-08-03\nfrom B\n' >> e.md && git commit -qam B
$ git merge A
Auto-merging e.md
CONFLICT (content): Merge conflict in e.md
Automatic merge failed; fix conflicts and then commit the result.
MERGE RC=1
```

**Two branches appending at the tail of one file conflict every time.** Not rarely — always. Git's
merge is line-based and both sides changed the same region. Round-2 H7 said this in words
(*"conflict on merge, every time"*); v4 asserts the opposite without engaging it.

**And the larger half of H7 is not mentioned at all.** `docs/dev-process.md` Phase 5: **`Docs` →
"Branch + PR, batched"**, *"Standalone doc edits accumulate"*, and merging is a **human gate**. This
repo has a remote, so the direct-commit escape does not apply. Measured: the last 12 commits on
`origin/master` are one squash per PR. So a dashboard entry written today is on a branch; a dashboard
rendered from `master` cannot see it; a dashboard rendered from the working tree shows entries
nobody else can; and *"batched"* — the prescribed remedy for doc-PR friction — is the opposite of
what a same-day continuity page needs. §5 does not mention the trade, §9's open questions do not
carry it.

*(VERIFIED: the merge conflict, by execution. The dev-process rule, by reading. The squash history,
by `git log`.)*

## H4 — §6's fold key does not identify every fold on the page, and "index" has no stated basis. Under the page's own newest-first ordering it is unstable on every append.

**Claim attacked.** §6 lines 151-154:

> *"The fix persists open/closed state across reload, **keyed by the entry's date-and-index**, which
> `gen-dashboard.py` assigns and which is **stable because the store is append-only**."*

**What I checked.** The reload client, `scripts/explainer-serve.py:556-604` (v4 cites `:559-580`,
which is accurate for the scroll/`busyTyping`/`poll` body). Verified: `KEY = 'explainer-scroll:' + here`
at `:559` is the only key; `sessionStorage` carries `window.scrollY` and nothing else;
`grep -n details scripts/explainer-serve.py` → no relevant hits. §6's measurement is correct and its
withdrawal of v3's *"benefits every existing page"* is correct — the server does not add ids to
markup it did not generate.

**Two defects in the key itself.**

1. **It does not identify a fold.** §4.2 gives every entry **two** `<details>` (Fold 1 plain, Fold 2
   technical), and §3 In-5 adds a folded glossary. `date-and-index` identifies an *entry*, so both
   folds of one entry collide on one key and the glossary has no key at all. The falsifier — *"open
   two folds, touch a source file, confirm both are still open"* — passes if the two folds chosen
   belong to different entries and fails if they are Fold 1 and Fold 2 of the same one. As written it
   does not say which.
2. **"Index" has no stated basis, and the page renders newest-first.** If index counts from the top
   of the append-only file, it is stable — that is what §6 asserts. If it is assigned in **render
   order**, which is newest-first (§4.2), then **every append shifts every index**, and after each
   new entry the reload restores the wrong folds — silently, which is worse than closing them all.
   This is verbatim round-2 M5's argument (*"A DOM-order key is exactly what a regeneration
   invalidates"*), and v4 answers it with an assertion of stability rather than by naming the basis.

**Minor, but worth stating:** §6's *"It fails today"* is a claim about a page that does not exist.
It is true of existing pages (round 1 measured 119 `<details>` on `backlog-table.html`), so the
falsifier is real — but it is a falsifier for the *server change*, not for the dashboard.

## H5 — The chart's stated purpose — "it shows the gap where you were away" — is falsified by this repo's own merge model. MEASURED.

**Claim attacked.** §4.3 lines 106-113:

> *"**Height = commits authored that day**, on the current branch's **first-parent** history —
> derivable, no judgement, and **it under-counts uncommitted work, which the page states**… it shows
> the gap where you were away. **A day with commits and no entry renders a bar with nothing under
> it.** That is the visible tell that I skipped writing."*

**What I checked — this spec's own branch.**

```
eb3838e a=2026-08-28 14:18   dashboard v1
91a1ec0 a=2026-08-28 14:48   dashboard v2
4897947 a=2026-08-28 15:14   dashboard v3
f9618fc a=2026-08-28 15:58   dashboard v4
  SQUASH ->
4b93902 a=2026-08-28 16:36   … (#169)
```

and on `origin/master`, the last 10 commits all have **author date == committer date == merge time**
(e.g. `9733102 a=2026-08-28 12:20 c=2026-08-28 12:20 … (#167)`). Also measured:
`git rev-list --count origin/master` = 1394, `--first-parent` = 411, and 82 merge commits exist in
the older era.

**What is actually true, in three parts.**

1. **A bar's height is PRs landed that day, not commits authored.** In the squash era, four commits
   spanning ninety minutes become one. In the older merge-commit era, `--first-parent` deliberately
   *skips* the branch commits and counts merge commits. The chosen ref makes the metric one unit per
   PR in **both** eras — so *"commits authored that day"* names something the derivation is
   specifically constructed not to count. v4 added `first-parent` in response to round-2 M4, which
   answered the ref question and left the metric question exactly where it was.
2. **The disclosed caveat is the wrong one.** *"It under-counts uncommitted work"* is true but minor.
   The larger effect is **mis-dating**: work committed on Monday and merged on Thursday appears
   entirely on Thursday. So the chart does not show *"the gap where you were away"* — it shows the
   gap where nothing merged, which for a week-long branch is the same shape as a week off.
3. **The alarm survives, but not as described.** *"A day with commits and no entry"* still fires for
   one real case — a PR merged without an entry — and that is a useful signal. It does **not** fire
   for a day of work whose merge slipped, and it cannot fire at all for a day with an entry and no
   commits (no bar, see B2). §5 calls the empty bar the mitigation for *"the single largest risk to
   the whole design"*; the mitigation covers a narrower case than the sentence claims.

*(VERIFIED: every date and count above. INFERRED: nothing — the mis-dating follows from author date
== merge time.)*

## H6 — `/brief` already produces the page §4.1 and §4.2 describe, and v4 never mentions it.

**Claim attacked.** §2's framing that the design is new, and §3's In list.

**What I checked.** `.agents/skills/brief/SKILL.md` (191 lines). Its `description`: *"Build a
one-page visual briefing on where a piece of work stands right now — state, evidence, and **any
decision waiting on the human**. Use when the user asks 'what is the status', 'how has it been going',
'catch me up', 'where are we'."* Its "Why this exists (measured 2026-08-17)" records the **same user
complaint** v4 §1 quotes: *"I want to have some tool to follow your work as your text proses are hard
for me to follow."* Its Step 3 section list is:

> *1. Masthead — … a visible stamp if a decision is pending. A reader who stops here should still
> know whether they are needed. … 3. The shape — the chart from Step 2 … 4. What is blocked — a
> table, one row per item: what, blocked on whom or what, since when. … 6. Ground-truth footer.*

And its governing rule is *"Every number, name and status on the page comes from a command run in
THIS invocation"* — the anti-staleness discipline §10 of the spec is reaching for.

It is in active use: six briefs in `~/explainers` from the last three days, including
`2026-08-28-brief-status-all-green-four-decisions.html` (69,049 B — the same file §2 of v3 measured).

`grep -n "brief" <v4>` → **one hit**, and it is `brief-compose.py` cited as a stale-count example.
`/brief` as a *capability* is never mentioned, compared, or ruled out.

**What is actually true.** There *is* a real difference and I want to state it fairly: `/brief` is
**pull** (someone must invoke it, per subject, producing a dated snapshot) and the dashboard is
**push** (a standing page with accumulated history that the user can open unasked). That difference
is genuine and it is the dashboard's strongest justification. But §4.1 (what needs you) and §4.2 (what
changed, folded, plain) are close to a re-implementation of `/brief` sections 1, 4 and 5 — and
`/brief`'s versions are *derived from commands run at compose time*, where §4.1's and §4.2's are
*written by hand and can be skipped*.

This is the user's own recorded failure shape — `it-already-exists-under-a-name-i-didnt-search`
(⭐, measured 3× in one day). A spec justified as "an addition, not a new system" must name the
existing system it is closest to and say what it does differently. §7's build table names one script
and one skill and compares itself only to `/goals` and `/backlog-table`.

---

# MEDIUM

## M1 — §2 is the argument for the whole cut, and two of its three supporting figures are wrong

**Claim attacked.** §2 lines 38-41:

> *"Measured: v1 234 lines → v2 324 → v3 **388**; §5 reached twelve numbered units where **v1 had
> four**. Round 1 said the page already had too many blocks; **v3 added one and removed none**."*

**What I checked.**

```
$ for s in eb3838e 91a1ec0 4897947 f9618fc 4b93902; do
    git show $s:docs/superpowers/specs/2026-08-28-project-dashboard-design.md | wc -l; done
234  324  388  208  208
```

✅ **The line counts are exactly right** — 234 → 324 → 388 → 208, all four verified. So is
*"twelve numbered units"*: v3's §5 carries 5.0–5.7 plus 5.5a–5.5d = 12.

**Two errors.**

1. **v1's §5 had five numbered units, not four.** `git show eb3838e:… | grep -n "^###* "` →
   `### 5.1 Progress`, `### 5.2 Activity`, `### 5.3 Health`, `### 5.4 How work moves`,
   `### 5.5 ⛔ Not Mermaid`. The "four" is a count of *graphics* (5.5 being a renderer decision),
   compared against a count of *numbered units*. Two different bases in one sentence.
2. **Round 1 did not review v1 — it reviewed v2 — and v3 added two blocks over it, not one.**
   `r1-codex` cites `spec:285-286` and `spec:298-299`; v1 is 234 lines, so those lines do not exist
   in it. v2 line 285 is *"Request state is derived by comparing `questions.md` entries…"* — the
   exact text quoted. v2 line 162-166 is the *"there is no fallback renderer"* passage r1-codex
   attacked. So round 1's subject is `91a1ec0`. Against v2, v3 added **§5.0 and §5.7** (plus §4a and
   §5.5a–d). Round-2 Claude said so in as many words: *"v3 answered that with §5.0 … But it also
   added §5.7 and removed nothing."*

**Why this matters more than a normal count slip.** §2 exists to justify the cut, §10 says *"Every
figure here was produced by running something on 2026-08-28"*, and §2 itself narrates three
occasions when a count in this spec went stale. These two figures were not run — they were carried
over from the round-2 review's prose (which made the same "four" slip, inherited from r1-claude's
own header calling its subject *"v1 DRAFT"*). That is *"a number was read rather than run"*, in the
paragraph that coined the phrase.

## M2 — §4.1's load-bearing citation points at a file that does not contain the rule

**Claim attacked.** §4.1 line 88: *"`"cannot run" is a FAILURE, never a pass` (`CLAUDE.md`)."*

**What I checked.**

```
$ cat CLAUDE.md
@AGENTS.md
@docs/dev-process.md
@docs/plugins.md

$ grep -rn 'is a FAILURE, never a pass' --include=*.md .
docs/portable-practices.md:50:## 2. "Cannot run" is a FAILURE, never a pass
docs/process-checklists.md:300:**1. "Cannot run" is a FAILURE, never a pass.** …
```

**What is actually true.** The repo's `CLAUDE.md` is three import lines and contains nothing else.
The rule lives in `~/.claude/CLAUDE.md` — a **machine-local, per-user file that is not in this
repository** — and, in-repo, at `docs/portable-practices.md:50` and `docs/process-checklists.md:300`.
A reader following the citation finds three `@` lines.

Round 1 caught the spec describing a file it had not opened (B2), and v4 does it again in a sentence
the cut newly added, on the page's most important guarantee. Note also that `docs/backlog.md` row 49
is already an open item for `scripts/check-doc-citations.py`, filed because **eight** citations were
wrong in one document — this is the ninth.

*(The rule itself is real and correctly quoted. Only the pointer is wrong.)*

## M3 — §10 says "two stale numbers" and names one

§10 lines 207-208, the last two lines of the document:

> *"**Two** stale numbers found and left for their owners: `explainer-delivery.md:68` says
> `brief-compose.py` has **14** self-test cases; it has **30**."*

**Verified true, as far as it goes:** `.agents/skills/shared/explainer-delivery.md:68` still reads
*"It has a `--self-test` (**14 cases**)"*, and `python3 scripts/brief-compose.py --self-test` →
`30/30 passed`. But that is **one** number, and the file ends there. The second is either missing or
was cut with the Mermaid material and the sentence not updated. In the section headed *"What was
measured, and when"*, a count that does not match its own list is the defect the section is about.

## M4 — §7's supporting sentence about `check-explainer-delivery.py` is over-broad

**Claim attacked.** §7 lines 170-173: *"**That check cannot enforce its own list** — verified: **it
only inspects skills already on it**, so an absent skill is invisible and it exits green."*

**What I checked.** `scripts/check-explainer-delivery.py:53` — `PAGE_SKILLS = ["explain-diff",
"brief", "explain-findings", "explain-topic"]`; the citation loop at `:76` is `for name in
page_skills:`; then `:83` is `for f in sorted(skills_dir.glob("*/SKILL.md")):` — the **restatement**
half scans *every* skill, listed or not, and its self-test proves it (`✓ restatement in another skill
caught`). Ran it: `python3 scripts/check-explainer-delivery.py` → rc=0, `--self-test` → 8/8.

**The load-bearing claim is TRUE and important** — the check cannot enforce its own membership, an
absent skill escapes the *citation* requirement, and stating that as a manual step with no gate is
the right disposition. But *"it only inspects skills already on it"* is false of the check as a whole,
and it is the same over-reach round-1 M2 corrected in v1 (*"'entirely' is false"*). v3 §9 phrased it
more carefully; v4's compression reintroduced the error.

## M5 — §8's first sub-criterion requires page content §4 does not specify

§8 line 181: *"the page names **the last date an entry was written**."*

I walked §4.1, §4.2, §4.3 and §3's In list. There is no block, slot or field for it. §4.2 renders
entries newest-first but is never required to surface a "last written" stamp, and §4.1 is about
what needs you. This is round-2 M3 in reduced form: an acceptance criterion for content the design
does not contain will either fail forever or be quietly dropped.

## M6 — round-1 Codex M1 (duplicate derivation / "a fourth status surface") was dropped without a disposition

v3 §7 carried: *"`gen-dashboard.py` **must import** the shared derivation rather than re-implement
it; if that proves impractical, §2's claim of 'an addition, not a new system' is withdrawn and this
needs redesign."* v4 §7 deletes the requirement and the trigger with no mention.

§2's table claims **B2 (r2)** — *"the derivation cannot be shared with `gen-goals-page.py`"* —
**GONE**, and that is correct: the milestone derivation is gone. But B2 (r2) was the *milestone
instance*; **M1 (r1 Codex)** was the general concern, and it is not the same finding.

**Measured, so this is not hypothetical:** `scripts/gen-goals-page.py:29` — *"last activity <- git
log, per document"* — and `:153-155` shells `git log -1 --format=%as`. v4 §7 gives `gen-dashboard.py`
*"the day counts and open PRs"*. The overlap is now much smaller than in v3 (per-document last-touch
vs per-day counts is not the same derivation), so the finding's **severity has genuinely fallen** —
but it was never dispositioned, and §2's table implies otherwise. A finding that shrinks should be
recorded as shrunk, not silently omitted from the table that exists to record dispositions.

## M7 — §2's finding labels are ambiguous between review halves, and one cross-reference points at the wrong section

§2's table has no column saying which half a finding came from, and two labels are reused:

- `B1 (r1)` is used for *"'bundled' ≠ 'loadable'"* (Codex), while `B1 (r1)` in the Claude half was
  the entry store — which §5 also refers to, as *"Round 1 found v2 had no store at all"*.
- `B2 (r1)` appears **twice in the same table**: once for *"§5.1 cited a source that did not contain
  what was claimed"* (Claude) and once for *"request identity on a channel with no id"* (Codex).

v3's §0 disambiguated (`B1 (Codex)`, `B1 (Claude)`); v4 dropped the qualifier. This is the memory
`feedback-name-every-reference` (⭐, *"never a bare `#39` or `M4`: qualify the namespace"*), and here
it is load-bearing: the table is the record of what was disposed, and two rows currently claim the
same identifier.

**Also, one pointer is simply wrong.** §2 line 57: *"**B2 (r1)** request identity … **DEFERRED to
v2** — **§7**"*. §7 is *"Build"* (the script/skill split). The explanation is in **§3**, lines 74-80
(*"Why the request box is out even though the user asked for it"*).

## M8 — the store's delimiters are invisible in the one view the store was put in the repo to get

§5 justifies the in-repo store (inherited from v3 §6a) on the grounds that entries are *"versioned,
reviewable"*. The section separators chosen are `<!--plain-->` and `<!--tech-->` — **HTML comments**.

A `docs/*.md` file in this repo is read, in practice, in a GitHub PR diff and in GitHub's rendered
Markdown view — that is what "reviewable" means here, since every doc change goes through a PR
(`docs/dev-process.md` Phase 5). In the rendered view HTML comments are **not displayed**, so the
plain paragraph and the technical paragraph run together as one block of prose with no visible
boundary — and the plain/technical separation is the whole content contract of §4.2. The diff view is
fine; the rendered view is not. This is small and cheap to fix (a visible marker, or a fenced block),
but it undercuts the stated reason for the store's location.

---

# LOW

## L1 — round-1 L3 is still open: three bare `explainer-delivery.md` citations, no path

`grep -n "explainer-delivery" <v4>` → lines 56, 170, 190, 207. Of these, 170 is the *script*
(`check-explainer-delivery.py`, which does live in `scripts/`); the other three cite the shared
document. `grep -n "\.agents/\|\.claude/skills" <v4>` → **no matches**. The file is at
`.agents/skills/shared/explainer-delivery.md` (verified by `ls`). The count is down from v3's eight
to three, which is progress, but round-1 L3 asked for paths and none were added.

Consistency note: v4 cites `scripts/gen-dashboard.py` with its directory in §7's table and then
`explainer-serve.py`, `gen-goals-page.py`, `brief-compose.py` and `regen-goals-page.sh` without one
— the last of which lives at `.claude/hooks/regen-goals-page.sh`, a directory a reader would not
guess.

## L2 — "one prerequisite remains, where v3 had five" undercounts by one

§2 line 60-61 and §6's title. Round-2 Claude listed v3's five as: the `explainer-delivery.md` page
class, closing the `PAGE_SKILLS` hole, the licence audit, the fold change, and the shared doc's stale
`14`. In v4 the page class and the licence audit are genuinely dissolved, and the fold change is §6 —
the named one. But **§7's manual `PAGE_SKILLS` addition is still a required, ungated step** (§7 says
so itself), and §10 still leaves the stale `14` *"for their owners"*. Calling §6 *"the one
prerequisite"* is defensible for *design* prerequisites; it is not accurate as a list of what must
happen before this can be called done.

## L3 — the flag's surface form is unstated, and the example is internally inconsistent with §4.1's prose

§5's example writes `## 2026-08-28  [needs-you]` — **two** spaces before the bracket. §4.1 refers to
entries *"flagged `needs-you`"*, without brackets. Nothing states whether the separator is one space
or any whitespace, whether the flag is case-sensitive, whether it may appear before the date, or
whether other bracketed tokens are legal. Per H1 this is not merely cosmetic — it is the input space
the parser must classify.

---

# Part 2 — the question the prompt asked me to answer straight

> *§1 ranks continuity as the user's number-one problem. §5 concedes that entries — the ONLY
> mechanism serving continuity — exist solely if the assistant remembers to write them… Is this
> design worth building at all?*

**Yes — but not as specified, and the premise of the question is slightly wrong in a way that
matters.**

**First, the correction.** Entries are not the only mechanism serving continuity in v4. The page has
**three** sources, and two of them are fully derived and require no discipline from me:

| Block | Source | Reliable without me remembering? |
|---|---|---|
| §4.3 the chart | `git log`, first-parent | **Yes** |
| §4.1 open pull requests | `gh pr list` | **Yes** |
| §4.1 needs-you entries, §4.2 what changed | me, by hand | **No** |

So the page degrades. On a day I wrote nothing, it still answers *"when did work happen, and what is
open"* — which is more than the chat transcript does, and more than nothing. That is not the whole of
continuity, but it is the skeleton of it, and it is free. **A design whose derived half stands alone
is worth building even if its written half is unreliable.**

**Second, the honest part of the answer.** The *narrative* half — the part that actually tells a
returning human what happened and why — is discretionary, and §5 is right that I would skip it
exactly when busy. Worse, H5 above shows the alarm meant to make that skipping visible does not fire
where §4.3 says it does. So as specified, the rank-1 problem is served by a mechanism with **no
forcing function and a broken detector**. Building it that way produces a page that is trustworthy
about dates and untrustworthy about meaning — and a page that is *sometimes* complete is worse than
one that is never complete, because the reader cannot tell which day they are looking at.

**Third — what would make entry-writing reliable.** The answer is not more discipline, and it is not
a nag. It is this project's own doctrine, from `docs/dev-process.md`: *"Before adding a rule here, ask
whether it can be a script."*

**Bind the entry to an artifact that already must exist.** In this repo, every unit of work already
produces exactly one thing that cannot be skipped: a **pull request**, with a body, gated on a human
merge (`docs/dev-process.md` Phase 5 — *"Branch + PR, always"*). That artifact is unconditional in a
way that "remember to write an entry" never will be. Three consequences:

1. **The entry rides the PR, not a separate act of virtue.** Written into `docs/dashboard-entries.md`
   in the same branch, so it lands when the work lands.
2. **A ratchet makes it falsifiable.** `scripts/check-dashboard-entry.py` — fails when a branch
   touches tracked files and adds no entry block; `--self-test` covering the near-misses, like the
   fourteen ratchets already in `scripts/check-schema-gates.sh`. That converts *"I must remember"*
   into *"the gate refuses"*, which is the only conversion this project has ever measured as working
   (`a-convention-catches-what-you-read`: a hand pass fixed 2, a 20-line ratchet found 3 more the
   next day).
3. **It fixes H5 as a side effect.** If the entry and the commits arrive in the same squash, the
   entry and the bar land on the same day by construction, and "a bar with nothing under it" becomes
   a precise statement — *this PR shipped without an entry* — instead of an artifact of merge timing.

The cost is honest and should be stated: an entry written to satisfy a gate can be a compliance
artifact rather than a briefing. That is a real risk. It is a smaller risk than no entry at all, and
the user is the only detector for quality either way (§8 says so, correctly).

**So my recommendation, plainly.** Build it. But either add the forcing function above, or scope v1
to the derived half only (chart + open PRs + links + glossary) and add entries once there is a gate
behind them. What should **not** ship is the middle version: a page that promises continuity, rests it
on a voluntary act, and carries an alarm that does not fire.

---

# What I checked and found nothing wrong with

Recorded so round 4 does not redo it.

- **§2's line-count progression** — 234 / 324 / 388 / 208, all four verified against git.
- **§2's Blocking arithmetic** — r1-codex 2 + r1-claude 2 = 4; r2-codex 3 + r2-claude 2 = 5; total 9,
  five dissolved. Every number correct.
- **§2's dissolution table** — all ten rows verified. Nothing left in v4 needs an absent data source
  or an undelivered asset.
- **§3's request-box reasoning** — `explainer-serve.py:671-698` is `do_POST` (ends exactly at 698);
  it reads only `doc` and `text`, generates `now` server-side, and
  `format_question_entry` (`:476-488`) emits `f"\n---\n\n## {now} — {doc}\n\n{text}\n"`. **No id, no
  type, no status.** The decision to cut the box is correct and correctly evidenced.
- **§4.1's ⚠ (cannot-tell)** — the correct fix for round-2 H1, and the best change in v4.
- **§6's measurement of the reload client** — `explainer-serve.py:556-604`; `:559` is
  `KEY = 'explainer-scroll:' + here`; scroll only; `#qbox` draft guard at `:565-571`; nothing for
  `<details>`. Cited range `:559-580` is accurate. The withdrawal of *"benefits every existing page"*
  is correct: the server injects JS but does not rewrite markup.
- **§7's skill-vs-script decision** — `.claude/hooks/regen-goals-page.sh:4-10` says exactly what §7
  says it says (*"WHY A HOOK AND NOT A SKILL … every field is derived (ADR-0010)"*), and the
  dashboard is genuinely not purely derived.
- **§7's `PAGE_SKILLS` conclusion** — verified; see M4 for the one over-broad sentence beside it.
- **§8's affordance probe** — `.agents/skills/shared/explainer-delivery.md:147` is §5b, and `:163-164`
  is *"assert the AFFORDANCE, not the handler — the button must be the topmost element at its own
  centre"*. Citation exact.
- **§10's `14` vs `30`** — `explainer-delivery.md:68` still says 14; `brief-compose.py --self-test`
  → 30/30. Still stale, correctly reported (see M3 for the missing second number).
- **The anchor** — `docs/anchors.md:39` carries `status-visibility` with the identical goal sentence;
  `python3 scripts/check-anchors.py` → *"10 registered, all claimed … floor 22 held"*, rc=0.
  `python3 scripts/check-docs.py` → *"Documentation integrity OK"*, rc=0.
- **`docs/dashboard-entries.md` does not exist**, which is correct for a spec.

---

NOT CONVERGED
