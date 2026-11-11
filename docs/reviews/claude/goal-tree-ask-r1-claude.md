Reviewed head: f21e47985e1a89a2e7054f1ee1ca1c52d4648eff

# PR #558 — goal-tree Ask tray + answers — round 1, Claude half

Subject: branch `goal-tree-ask`, head `f21e4798`, diff `git diff origin/master...HEAD` (7 files, +414/−37).
Mandate: adversarial; try to refute each of the PR's three claims. REPORT only.

## What was run

| Check | Result |
|---|---|
| `python3 scripts/goal-tree.py --self-test` (worktree, head f21e4798) | **458/458 self-test cases passed** |
| End-to-end `write_page` on the REAL main-checkout snapshot log (8.1 MB page), lifting from a tracked explainer, with an answers file holding a thread answer, a goal answer and an orphan; through `page_markup.link_html` | `why == ""`, tray lifted, 3 markers, Older section present, `</pre>` and `<script>` in an answer arrive escaped, `PR #538` in an answer becomes a link. **The in-`<pre>` marker passes `require_subset`** (the existing self-test only puts an ORPHAN answer through `write_page`, so this path was untested before this run) |
| 9 hand mutations on a `git archive` copy in scratch (never the worktree) | 3 red, **6 survive** — table under F3 |
| `load_answers` fed 4 malformed shapes | **3 crash** — F1 |

## Claim 1 — the tray is lifted; it degrades loudly

**Holds on the path I traced.** The tray JS posts `{doc: location.pathname…}`, so a question from
`http://127.0.0.1:7391/goal-tree` reaches `explainer-serve.format_question_entry` and lands in
`~/explainers/questions.md` under `## <now> — goal-tree`. A Refresh runs `regen-pages.py` → `goal-tree.py`
with no arguments (= `--snapshot --page`) from a fresh `origin/master` tree; `tray_source` is then None,
so `brief-compose.find_source` takes the newest `~/explainers/*.html` that has a tray, EXCLUDING the
output (backlog #106), so a Refresh keeps the tray as long as one other page in `~/explainers` has one.
Side effect worth knowing: every Refresh also writes an ~8 MB `~/explainers/goal-tree.fragment.html`
(brief-compose's backlog #88 copy); the server excludes fragments from listing, so it is harmless.

## Claim 2 — answers: collapsed, never interlaced, orphans kept, malformed file reported — PARTLY REFUTED

### F1 — MEDIUM — a malformed answers file CRASHES the page instead of being reported — `scripts/goal-tree.py:106-110`, `:121`

`load_answers` catches only the `json.loads`/`data["answers"]` step. The shape checks after it are outside the
`try`, and `asked` is never type-checked. Measured on a scratch copy:

| answers file | result |
|---|---|
| `{"answers": null}` | `TypeError: 'NoneType' object is not iterable` (line 106, `enumerate(rows)`) |
| `{"answers": 5}` | `TypeError: 'int' object is not iterable` |
| `{"answers": [{"key":"pr-1","q":"q","a":"a","asked":5}]}` | loads cleanly, then `_qa_item` → `html.escape(5)` → `AttributeError` |
| `[1]` | reported by name (correct) |

Failure scenario: pages are built from a fresh `origin/master` (`regen-pages.py` docstring, backlog #408). One
merged answers file with `"asked": null`'s cousin `"asked": 1107` or `"answers": null` makes every Refresh and
every post-merge regen of the goal tree exit non-zero — the page is not written at all, the opposite of
"reported by name and the page is still written". Fix: validate `rows` is a list and every present field is a
`str` inside the same refusal; add the three shapes to the existing "REFUSED by name" case.

### F2 — LOW — a thread's answer marker is hidden inside a closed fold — `scripts/goal-tree.py:85-86`

The goal marker was deliberately placed OUTSIDE its fold ("so a folded goal still shows it has answers"),
but a thread's marker rides its key's first occurrence, wherever that is. Measured on the real log: an answer
keyed `backlog-251` (first thread of the first goal) rendered inside `<details class="fold older">`, closed by
default — the reader sees no 💬 until they open "older". Questions about finished work are exactly the ones
whose thread sits in `older`. The self-test's `PR #21` case uses a thread that is not folded, so it cannot see
this. Fix options: hoist a count onto the fold's summary, or accept and say so.

### F3 — MEDIUM — the self-test does not pin the escapes or the file-side tray check it claims — `scripts/goal-tree.py:121-145`, `:2348-2351`

Mutations on a scratch copy (`git archive HEAD`), `--self-test` after each:

| mutation | result |
|---|---|
| `q` unescaped in `_qa_item` | RED (457/458) |
| `a` (answer paragraphs) unescaped | **survives 458/458** |
| `asked` unescaped | **survives** |
| Older-section `key` unescaped | **survives** |
| `answers_error` unescaped in the ⚠ line | **survives** |
| `if not _has_tray(written)` → `if False` (the "asked of the FILE, not the exit code" check) | **survives** |
| Older section `<details … open>` | RED |
| goal marker moved inside the fold | RED |
| compose timeout → `why = ""` | survives (expected: no case reaches it) |

The answer body `a` is the field most likely to carry markup (an answer quoting `<details>`, `</pre>` or a
selector), and nothing would catch its escape being dropped: the "escaped" case only checks `q`. The prompt
asked whether removing the escape goes red: for one of five escaped fields, yes. Add `<` to the fixture's
`a`, `asked` and orphan key; the file-side tray check needs a stub compose that exits 0 without writing a tray
(e.g. `tray_source` pointing at a compose shim, or a monkeypatched `_has_tray`). None of the new mutation
manifest entries covers an escape.

### F4 — LOW — an answer reaches the page only after a PR merges, and nothing flags it stale — `scripts/explainer-serve.py:234`, `scripts/regen-pages.py:27`

`docs/goal-tree-answers.json` is tracked and the page is built from `origin/master`, so answering a question
asked on the page is a branch + PR + merge; until then the page shows nothing. It is also not a declared
`/_stale` source and not an after-edit trigger. Not a defect against the PR's claims (the merge hook rebuilds),
but the latency of the ask→answer loop is a design consequence the PR body does not state. Recommend one line
in the `_doc` field or the PR body.

## Claim 3 — the two ledger items no longer show under "no goal" — holds, with a placement question

### F5 — LOW — PR #558 is declared under `dev-speed-first`, its own ledger entry says `comprehensibility-suite` — `docs/goal-threads.md:200`

The ledger entry `goal-tree-ask` carries `goal: comprehensibility-suite`; the tracked line puts `side · PR #558`
under `dev-speed-first`. Because the tracked file wins (`refs & declared` → skip), the page will show the Ask
tray work under dev speed. The work is the comprehensibility suite's (the owner's DIRECTION lane). Also: PR #557
is now declared in two goals (`:54` guard-harness-audit, `:199` dev-speed-first); only the first occurrence gets
the anchor id and any answers. If deliberate, fine.

## The observation the prompt asked about — namespace collision, PRE-EXISTING, exposed by this PR

### F6 — MEDIUM (pre-existing; not introduced here) — `_ledger_numbers` flattens `(kind, n)` to bare `n` — `scripts/goal-tree.py:359-363`, used at `:533`, `:578`, `:587`

```python
return ({int(n) for n in LEDGER_NUM_RE.findall(f"{entry.get('id', '')} {entry.get('what', '')}")}
        | ({n for _, n in t["refs"]} if t else set()))
```

and `derive_thread` intersects that with `nums = set(prs) | set(rows)` — PR numbers and backlog numbers in ONE
integer set.

- `goal-tree-ask`: its ledger `thread` is `side · PR #558` → `{558}`. The thread `fix · backlog #558, PR #538`
  has `nums = {538, 558}`. **Namespace collision:** PR #558 ≠ backlog #558, matched by integer. That attaches
  "in flight: OWNER 11-11 06:15 …" to a merged, unrelated thread.
- `s1-phase6`: its `what` says "Phase 6 architecture review of #586 slice 1" and its thread names PR #557,
  backlog #600/#601 → `{586, 557, 600, 601}`; matches both `backlog #586` lines. That is **ref-intersection
  over-matching by prose number**, not a collision: the entry really is about backlog #586, but a bare `#586` in
  prose hangs it on the MERGED `backlog #586, PR #552` thread too. (`state` stays `merged` because only
  `next/notfound/superseded/withdrawn` flip to `inflight`; the damage is the detail text.)

Caused by: blame puts `_ledger_numbers` at 95ec78a2 (2026-11-05); this PR does not touch it. The PR EXPOSED it by
being the first PR whose number equals a live backlog row number in the same tree. It will recur for every PR
number that equals a backlog row number (both sequences are in the 500-600s now and grow together), so it is
not transient. Recommend filing: keep `(kind, n)` pairs for structured refs and intersect pairs; treat a bare
prose `#N` as ambiguous. Not this PR's fix.

## Escaping of page content (asked explicitly)

Every new insertion point escapes in the CODE: `q`, `a`, `asked`, the Older key, `answers_error`, `head` is
derived from an int. Thread text and owner quotes continue through the existing `segments`/`html.escape`
path. `link_html` splices links into text nodes only and refuses outside its subset. **No unescaped insertion
found** — the gap is the tests (F3), not the code.

## Also noted (not findings)

- `COMPOSE_TIMEOUT = 40` (`scripts/goal-tree.py:2311`) inside the 60 s Refresh bound: the measured normal whole
  `--page` is 28.0 s, of which compose 18.2 s, so ~10 s is the rest; the Refresh also runs `--snapshot` (gh), not
  measured in that comment. A HANGING compose therefore leaves roughly 60 − 40 − (10 + gh) seconds to write the
  tray-less page. INFERENCE, not measured: on a slow day the fallback the bound exists for could itself be cut
  off by the 504. Deriving the bound from the remaining budget, or measuring a `--snapshot --page` with a hung
  compose, would settle it.

## Findings

| # | Severity | Where | One line |
|---|---|---|---|
| F1 | MEDIUM | `scripts/goal-tree.py:106` | `answers: null`/non-list/non-str `asked` crashes the page; refutes "malformed file reported, page still written" |
| F2 | LOW | `scripts/goal-tree.py:85` | a thread's 💬 marker sits inside a closed `older` fold, invisible (measured on the real log) |
| F3 | MEDIUM | `scripts/goal-tree.py:121` | escapes of `a`, `asked`, older key, `answers_error` and the file-side `_has_tray` check all survive mutation |
| F4 | LOW | `scripts/explainer-serve.py:234` | answers reach the page only after a merge; not a `/_stale` source — unstated |
| F5 | LOW | `docs/goal-threads.md:200` | PR #558 declared under dev-speed-first; its ledger entry and its nature say comprehensibility-suite |
| F6 | MEDIUM (pre-existing) | `scripts/goal-tree.py:359` | `_ledger_numbers` drops the kind: PR #558 matches backlog #558 — collision, exposed not caused; file it |

VERDICT: NOT CONVERGED
