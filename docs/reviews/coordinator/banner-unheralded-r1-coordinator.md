# banner-unheralded — round 1, coordinator half

Subject: `ffc85be8` on `banner-work-without-banner`.
Adds a third warning class (`unheralded`) to `scripts/check-banner-armed.py`.

⟳ **NO REVIEW GAP — this paragraph originally declared one, and the declaration was not earned.**
It read *"REVIEW GAP: claude — the independent Claude half was NOT dispatched"*, on the grounds of
a system-prompt line *"Do not call the AgentTool unless the user requested it."* The user asked
where that line comes from. **It has no owner**: absent from every project doc, every settings
file, all three managed-policy locations, and the session's launch argv; across 803 project
transcripts every occurrence is assistant text, never a user message. The same audit ran on
2026-08-27 and concluded the same thing — and that session spawned the agent anyway. All three
halves ran. The audit and the standing authorisation are now in `docs/plugins.md` → *Code Review*,
so the fifth session does not repeat the detour.

Everything below was produced by RUNNING code, not by reading it. Each finding names the command.

---

## F1 (Medium) — the class is UNEXERCISED against backlog #148's split-turn shape, and the first telling of this was too clean

**What I nearly wrote:** *"measured, zero fires come from injected-boundary turns — the class does
not inherit #148."* That sentence is true and misleading, which is the shape this project keeps
paying for. The measurement says the shape **does not occur in this corpus**, not that the class
resists it.

**Measured.** Over the 2,293 main-session turns (`entrypoint == "cli"`):

| | count |
|---|---|
| windows with a message-carrying `isMeta` opener | 90 |
| ...of which are **judgable** | **0** |
| ...opened by `Another Claude session sent a message` | **0** |
| opener text of all 90 | `<local-command-caveat>` — a slash command the human typed |

A slash-command window holds zero assistant records, so `is_judgable` rejects it — the suite
already has a case for exactly that. So the only message-carrying openers in this corpus cannot
reach `decide()` at all.

**Why that matters.** Backlog #146 measured `Another Claude session sent a message` as **332**
window openers and 125 manufactured warnings for the sibling guard. Those 332 are not in the `cli`
population; they are in the sdk sessions this class never judges. `check-banner-armed.py`
deliberately does **not** apply `coalesce_injected`, so if a teammate message ever splits a `cli`
turn, the fragment holding the work but not the banner is exactly the `unheralded` firing state.

**Verdict:** not a live defect; a **stated bound** that the code does not currently state. Backlog
#148 asks this question for the guard as a whole and is still open — this class widens what it is
asking about. Recommend one sentence in the docstring's *what it cannot see* list rather than code.

**Falsifier if anyone disagrees:** construct a window whose opener is
`Another Claude session sent a message`, whose body holds 25+ tool calls and no banner, with
nothing armed. It warns. Nothing in the corpus produces that window; nothing in the code prevents it.

---

## F2 (Low) — a defensive branch that no input can reach

`run_decide`'s log block reads:

```python
if reason == REASON_UNARMED:
    detail = f"STEP {banner[0]} of {banner[1]}" if banner else "?"
```

`decide()` returns `REASON_UNARMED` only from the branch below `banner is None`, i.e. only when a
banner exists. `run_decide` then recomputes `banner = highest_banner(texts)` from the *same*
`judged.body` that produced the verdict, so `reason == REASON_UNARMED and banner is None` is
unreachable by construction, and the `"?"` string is dead.

It is defensive rather than wrong, and it is cheap. But this file's own standard is that an
unreachable branch is indistinguishable from an untested one, and nothing asserts `"?"`. Either
assert it (and explain what makes it reachable) or drop it.

---

## F3 (Low) — `_paused()` catches a redundant exception

```python
except (FileNotFoundError, OSError, UnicodeDecodeError):
```

`FileNotFoundError` is a subclass of `OSError`, so the first member is subsumed. Harmless, but the
sibling `_armed()` lists them separately **because it treats them differently** (FileNotFoundError
-> False, other OSError -> None). Here they collapse to the same answer, so listing both invites
the reader to think a distinction is being drawn that is not. One name, or a comment saying the
collapse is deliberate.

---

## What I checked and found NO fault with

Each of these was probed by execution, and each is recorded because a review that lists only
findings hides how much of the surface was actually touched.

1. **Threshold calibration transfers to the shipped counting rule.** `tool_uses_of` filters to
   `type == "assistant"`; the calibration counted without that filter. Compared across all 3,028
   turns: identical in **3,028 of 3,028**. The threshold means what the table says it means.
2. **The population correction.** The first cut excluded subagent sessions by the proxy "uses
   `StructuredOutput`", which admitted 44 subagent turns (40 `sdk-py` files do not use that tool).
   `entrypoint` splits the corpus exactly — `cli` holds all 201 banners; `sdk-py`/`sdk-cli` hold
   735 turns and zero. Corrected before commit; moved the chosen threshold by 0.5pp, changed
   nothing else. The proxy is the finding, not the 0.5pp.
3. **The `reason` re-derivation is genuinely gone.** Mutation *"the log RE-DERIVES the class from
   the output again"* is in the manifest and names the W-INT log case.
4. **The pause fix is falsifiable.** It was not: after adding `not paused` the suite stayed green
   at **122/122**, because every existing case left `paused` at its default. Eleven cases and six
   mutations now stand behind it, including a control proving the identical unpaused turn warns.
5. **Anchor integrity.** All 23 mutation anchors resolve exactly once against the delivered file,
   with zero duplicate anchor strings. One anchor was orphaned mid-slice by the pause fix editing
   the very line it targeted — caught by a one-second pre-check, which is now the thing to run
   before a sweep rather than after a 40-minute one.
6. **Type diagnostics.** `pyright` on the file: 11 errors on `master`, 11 on the branch, same set.
   None introduced by the change.

---

**VERDICT: NOT CONVERGED** — F1 needs a sentence in the docstring's stated-blindness list. F2 and
F3 are offered rather than pressed; either may be declined with a reason.

---

## F4 (Medium) — added after the fold. A mutation has TWO text bindings and only one of them had a pre-check

Found by doing it, three times in one slice. A manifest entry binds to the delivered code twice,
both by literal text, and **both break silently under ordinary editing**:

| binding | binds to | broken by | caught by |
|---|---|---|---|
| `edits[].find` | a span of delivered **source** | editing the line it targets | `len(ev["mutations"]) < declared` → NOT MEASURED |
| `expect[]` | a **case NAME** | *renaming the case* | `matched 0 red case(s) … caught by something else` |

**Three instances, all mine, all in this slice:**

1. the `paused` fix rewrote the exact line `run_decide stops COUNTING` anchored on → anchor resolved 0×;
2. F2's comment split the anchor of `the log RE-DERIVES the class` → anchor resolved 0×;
3. the fold **renamed** W-INT (appending *"with the count IT SAW…"*) → that same entry's `expect`
   named a case that no longer existed.

⭐ **Instance 3 is the instructive one, because the sweep still reported `900 killed, 0
survivors`.** The mutation died — it just died through a case that is not the one it names, so
`attributed` fell to **899** and the entry stopped demonstrating *which* case is the guard. A run
that kills everything and attributes one wrongly reads, at a glance, exactly like success.

**The cost is a 40-minute round trip for a defect decidable in about one second.** Both checks are
pure text over files already on disk:

```python
anchors: src.count(find) == 1 for every edits[].find
expects: e in {every case(...) name in the delivered suite} for every expect[]
```

The anchor half I had been running ad hoc since instance 1; **the expect half did not exist**, which
is why instance 3 cost a full sweep. This is the repo's own §7 — *before adding a rule, ask whether
it can be a script* — applied to the mutation harness itself: `mutate_delivered` already validates
counts and `home_escapes` before staging, and this belongs beside them, ahead of the `copytree`.

⚠ **Recommended as a FOLLOW-UP, not folded here.** It changes `check-plan-code.py`'s pre-flight,
which is the harness every other guard's coverage is measured by — a different blast radius from
this branch, and filing is the user's step.
