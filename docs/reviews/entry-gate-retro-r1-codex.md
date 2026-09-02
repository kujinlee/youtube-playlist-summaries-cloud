<!-- codex-review: model=gpt-5.5 -->

High — Entry-only branches can still ship dashboard entries the page marks unparseable
- WHERE: scripts/check-dashboard-entry.py:25, scripts/check-dashboard-entry.py:328, scripts/gen-dashboard.py:517
- WHAT: `FLAG = re.compile(r"\[(needs-you|heads-up|resolved:\s*[^\]]*)\]")` accepts `[resolved:]`, and `added_entry_problems()` only runs `err = header_error(line[1:])`. The page later rejects the same entry in `parse_entries()` with `if not r: e["error"] = "[resolved:] with no entry id after it"`.
- WHY IT MATTERS: this patch closes only malformed header syntax. An entry-only patch like `+## 2026-09-01 [resolved:]\n+Title\n` produces `added_entry_problems: []` and `verdict(...): (0, "no tracked files changed outside the exempt paths")`, but `gen-dashboard.parse_entries()` sets `"[resolved:] with no entry id after it"`, so the page renders a broken entry after the gate passed.
- FIX: either make `header_error()` reject an empty `resolved:` payload, or have `added_entry_problems()` validate the added block through the same entry parser path that produces page errors.

Low — Nested emphasized NO-ENTRY marker is still refused
- WHERE: scripts/check-dashboard-entry.py:93, scripts/check-dashboard-entry.py:112
- WHAT: `EMPH = re.compile(r"^(\*{1,3}|_{1,3})")` strips only one homogeneous opener before `if not rest.startswith(NO_ENTRY): return None`.
- WHY IT MATTERS: `exemption_reason("**_NO-ENTRY:_** x")` returns `None`, even though this is the same deliberate emphasized-marker shape as `**NO-ENTRY:** x`, just nested. The new matcher fixes the tested bold/italic instances but not the common bold+italic form.
- FIX: recognize balanced nested emphasis around the marker, for example by peeling leading `*`/`_` runs repeatedly only when the corresponding closer appears immediately after `NO_ENTRY`.

Checks run: `python3 scripts/check-dashboard-entry.py --self-test` passed `104/104` + `13/13`; `python3 scripts/check-plan-code.py --mutate .` passed `7 files / 150 mutations / 0 survivors`. I also checked current non-doc callers for the `collect()` four-tuple and found no stale three-value unpack.

VERDICT: NOT CONVERGED

---
## Coordinator adjudication (author, not an independent half)

**Codex High — CONFIRMED BY EXECUTION**, and the class is WIDER than reported. Measured:

| header | gate | page |
|---|---|---|
| `[resolved:]` | PASS | "with no entry id after it" |
| `[resolved:   ]` | PASS | same |
| `[resolved: nonsense]` | PASS | "names no entry in this file" |
| `[resolved: 2026-09-01/99]` | PASS | same |
| `[resolved: 2026-13-45/1]` | PASS | same |

FIVE shapes, splitting into TWO problems:
- **Syntactic** (first two) — `FLAG`'s `resolved:\s*[^\]]*` permits ZERO characters. `header_error`
  can reject these with no extra information.
- **Referential** (last three) — whether an id names a real entry is a property of the WHOLE STORE.
  `added_entry_problems` only ever sees a PATCH, so it is structurally incapable of answering.

⛔ `header_error`'s docstring claims parser and ratchet "CANNOT disagree about what a header is".
**That claim is false** and was false before this slice: `parse_entries` has a PASS 2 the ratchet
never had. The author's #78 fix said it validated "the SAME grammar the page's parser uses" — it
validates a SUBSET.

**Codex Low (nested `**_NO-ENTRY:_**` refused) — CONFIRMED**, independently reproduced by the
coordinator before reading the Codex review. Fails CLOSED. Low stands.

**Author-run checks, NOT an independent review half:**
- Vacuity: reverting the emphasis fix in a /tmp copy reddens 8 of the new cases. Non-vacuous.
- The four "still inert" cases pass in both worlds BY DESIGN — they are regression guards. The
  blockquote one IS mutation-covered (`line-leading rule removed`).
- Hypothesis RAISED AND REFUTED: widening `EMPH` to `^[>\s]*(...)` left 104/104 green. Not a
  coverage gap — that mutant is EQUIVALENT, because `rest = s[len(opener):]` slices by the captured
  group's length and a `> ` prefix leaves `rest` starting at `**NO-ENTRY:`.
- ⚠ NIT: `s[len(opener):]` should be `s[m.end():]`. Identical today only because the group starts at
  position 0 — correct by luck, not construction.
- `+++ b/docs/dashboard-entries.md` does NOT match `^\+##(?!#)`; no misfire on patch headers.

## ⛔ CORRECTION — the Claude half DID run; my gap note was false

An earlier revision of this file said `REVIEW GAP: claude — produced nothing`. **That was wrong.**
The half ran ~25 tool calls and wrote **26,764 characters** of review, twice. Its output never
reached the coordinator, and the cause was the COORDINATOR'S BRIEF: it said *"YOUR FINAL MESSAGE IS
THE REVIEW. Write no file."* — correct for a Task-tool subagent whose final message is returned,
WRONG for a named background teammate, where plain text is not delivered and `SendMessage` is
required. It followed the brief and went idle. Recovered from its transcript and filed as
`entry-gate-retro-r1-claude.md`.

⚠ **The gap note itself was the day's own failure class**: a confident claim about a mechanism,
written without checking the mechanism. The transcript was on disk the whole time.

**Its three Highs, two verified by the coordinator:**
1. `(?!#)` re-opens the gate/page divergence on `###` — the renderer's `BLOCK = ^##\s*\S` MATCHES
   `### Worth knowing` (`\s*` takes zero, `\S` takes the third `#`). VERIFIED. My justification
   *"several entries use one"* is FALSE — the store has **zero** `^###` lines. Still open.
2. `no_entry_prs` retroactively re-judged merged PR bodies, putting a FALSE exemption for PR #198
   (which wrote a 49-line entry) on the live page. VERIFIED, and **FIXED in this branch** — control
   against live `gh`: before `[198]`, after `[]`.
3. Further gate-passes/page-breaks shapes (blank title line; PASS-2 dangling references) — the
   referential family, filed as backlog #82.

**ROUND VERDICT: NOT CONVERGED** — finding 1 remains open.
