#!/usr/bin/env python3
"""Refuse an `AskUserQuestion` card that does not follow `docs/portable-practices.md` §19.

    python3 scripts/check-selection-card.py < tool-input.json
    python3 scripts/check-selection-card.py --self-test  # 59 cases

WHY THIS FILE EXISTS
--------------------
§19 has specified the shape of an option list since 2026-09-04: every option carries a LETTER, a
label, a rationale and a trade-off; exactly one is marked *Recommended* with its reason; the last
option is always *"I have a question about these"*; and the question text names the axis.

MEASURED 2026-09-10, which is the entire justification. Three cards in one session:

    card 1 (which slice to pick)   recommendation ✓   letters ✗   question-exit ✗
    card 2 (two decisions)         recommendation ✗   letters ✗   question-exit ✗
    card 3 (after two corrections) recommendation ✓   letters ✓   question-exit ✓

The rule was not missing. It was in §19, and restated in two memory files, the whole time — and it
was reconstructed from recall at the moment of use instead of read. The user's words: *"you seem to
deviate proven style. I'd like to have this style recorded and followed."* It was already recorded.
Recording was not the gap.

This is the project's own §7 applied to its own §19: **before adding a rule, ask whether it can be a
script.** Three of §19's six clauses are exactly decidable from the tool input, so they are decided
here rather than remembered.

⛔ WHAT THIS DOES NOT CHECK, STATED RATHER THAN IMPLIED
-------------------------------------------------------
A guard that covers half a rule and reads as covering all of it is a hazard this repo has paid for
more than once, so the uncovered half is named here and in the block message:

  * **whether two options produce DIFFERENT WORK.** This is the defect that caused §19 to be
    written — two of four options were the same action in different words — and it is not decidable
    from text. A card can pass every check here and still offer a fake choice.
  * **whether the question text names the AXIS.** Detectable only by heuristics that would fire on
    healthy cards, and a detector people learn to skip is worse than none (backlog #92).
  * **whether the rationale is TRUE.** Only that something was written. The floor below is a floor
    against a bare label, not a test for reasoning.

FAILS IF
--------
  * an option label does not begin `A — ` / `B — ` / `C — ` (any dash, one letter, one space);
  * the letters are not consecutive from A, in order;
  * the number of options marked `(Recommended)` is wrong — exactly one for a single-select card, at
    least one for a multi-select one — or the recommended option is not FIRST;
  * the last option is not the question-shaped exit;
  * an option other than that exit carries a description shorter than `MIN_DESCRIPTION` characters;
  * the input is not readable as an `AskUserQuestion` payload -> exit 2, CANNOT RUN, never a pass.
"""

from typing import Any, Callable, Sequence

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

# One capital, one dash of any of the three spellings a person actually types, one space. Strict on
# the letter and loose on the dash: blocking a card because someone typed a hyphen instead of an em
# dash would be the cry-wolf failure this guard is supposed to avoid.
# One capital, then a dash of any of the three spellings a person actually types, then AT LEAST ONE
# SPACE — the trailing space is required and the leading one is not, which the first docstring got
# backwards (r1 M-3). Strict on the letter, loose on the dash: refusing a card over a hyphen would be
# the cry-wolf failure this guard exists to avoid.
LETTER = re.compile(r"^([A-Z])\s*[—–-]\s+\S")
# ⛔ THE PARENTHESIS IS NOT PARSED ANY MORE, and two rounds of trying is why. A bare substring test
# read prose ABOUT the marker as a marker; an exact literal refused §19's own "with its reason"; an
# end-anchored regex then refused `(Recommended) — it is reversible`, `(Recommended).`,
# `(Recommended: see ADR-0010 (v2))`, and accepted `(Recommended against by CI)`. Every fold moved
# the false positive somewhere else, which is the tell that the rule was wrong rather than the
# regex: the question is not "is this parenthetical well-formed", it is "does this label advise me".
#
# So: the WORD, anywhere, minus the two negations that reverse it. A label that merely discusses the
# term now counts as a marker — a false NEGATIVE of the guard's intent — and that is the cheaper
# error by a wide margin, because this hook BLOCKS: a wrongly-refused card costs a real turn, a
# wrongly-accepted one costs a card that says "recommend" twice and gets a clear message about it.
RECOMMENDED = re.compile(r"\brecommend(?:ed|s)?\b", re.I)
NOT_RECOMMENDED = re.compile(r"\b(?:not|never|against|avoid)\s+recommend|recommend(?:ed)?\s+against",
                             re.I)
QUESTION_EXIT = re.compile(r"i\s+have\s+a\s+question", re.I)
# Reaching for the exit without landing on it — "I have questionS", "Ask me something first".
NEAR_EXIT = re.compile(r"\b(?:questions?|ask|asking|clarif\w*|unclear|unsure)\b", re.I)
# A floor against a BARE LABEL, not a test for rationale. §19's own argument is that an option with
# no stated cost is either obviously right (so it should not have been asked) or not yet thought
# through (so it should not have been offered). 40 characters cannot tell those apart from a real
# rationale — it can only tell them from nothing at all, which is what it is for.
# ⛔ ONE FLOOR, SCRIPT-NEUTRAL, and deliberately low. It was 40 with a 15 "dense script" relaxation
# keyed on `len(desc.split()) > 1` — which measured SPACES, not information. Korean is
# space-delimited, so no Korean description could ever reach the relaxation; Japanese lost it the
# moment a Latin product name or an ideographic space appeared; and a single 15-character token (a
# bare URL) sailed past the 40. Wrong in both directions, for whole languages.
#
# §19's actual requirement — a rationale AND a trade-off — is not machine-checkable in any script,
# and pretending otherwise is what produced two rounds of false positives. What IS checkable is
# whether anything was written at all. This number rejects "", "ask", "short", "do it"; it never
# fires on a real sentence in any language. The rest is the reader's job, and the block message and
# the docstring both say so.
REPO = pathlib.Path(__file__).resolve().parent.parent
MIN_DESCRIPTION = 15
# `AskUserQuestion` accepts 2–4 options. NOT a style choice: it is the tool's schema, and the block
# message has to respect it or it prescribes a repair that fails (r1 Blocking).
MAX_OPTIONS = 4


def card_problems(questions: Sequence[dict]) -> list[str]:
    """PURE. Every §19 clause that is exactly decidable, over one AskUserQuestion payload."""
    problems: list[str] = []
    if not questions:
        return ["CANNOT RUN — the payload carries no questions at all."]

    for qi, q in enumerate(questions, 1):
        where = f"question {qi} ({str(q.get('header') or q.get('question', ''))[:40]!r})"
        options = q.get("options") or []
        # ⚠ r2: `MAX_OPTIONS` shaped the ADVICE and enforced nothing, so a five-option card passed
        # this guard clean and then failed the tool's own schema — the guard handing over a card it
        # had just approved. The ceiling is the tool's, not a preference.
        if len(options) > MAX_OPTIONS:
            problems.append(
                f"{where}: {len(options)} options; the tool accepts {MAX_OPTIONS}. Merge two, or "
                f"drop the weakest — and remember the question-exit spends one of the four.")
            continue

        # ⚠ THREE, not two (r1 M-1). The floor was written before the question-exit became
        # mandatory; with it, a two-option card offers exactly ONE course of action — a
        # confirmation dialog wearing a selection card, which is the defect §19 is about.
        if len(options) < 3:
            problems.append(
                f"{where}: {len(options)} option(s). With the mandatory question-exit that leaves "
                f"{max(0, len(options) - 1)} real choice(s) — §19 wants a decision, not a confirm.")
            continue

        labels = [str(o.get("label", "")) for o in options]

        # ── the letter prefix, and that the letters actually run A, B, C … ──────────────────────
        for li, label in enumerate(labels):
            if not LETTER.match(label):
                problems.append(
                    f"{where}: option {li + 1} is not lettered — {label[:48]!r}. "
                    f"§19: every option carries a letter, e.g. 'A — Keep the current shape'.")
        matched = [LETTER.match(label) for label in labels]
        if all(matched):
            got = [m.group(1) for m in matched if m]
            want = [chr(ord("A") + i) for i in range(len(got))]
            if got != want:
                problems.append(f"{where}: letters run {''.join(got)}, expected {''.join(want)}.")

        # ── exactly one recommendation, and it goes FIRST ───────────────────────────────────────
        marked = [i for i, label in enumerate(labels)
                  if RECOMMENDED.search(label) and not NOT_RECOMMENDED.search(label)]
        multi = bool(q.get("multiSelect"))
        if not marked:
            problems.append(
                f"{where}: nothing is marked (Recommended). §19: withholding a recommendation is "
                f"not neutrality, it is handing over an unfinished analysis.")
        elif not multi and len(marked) > 1:
            problems.append(
                f"{where}: {len(marked)} options marked (Recommended) on a single-select card; "
                f"§19 says exactly one.")
        elif not multi and marked[0] != 0:
            # ⚠ SINGLE-SELECT ONLY (r1 M-5). The reason for "first" is that the reader meets the
            # answer before the alternatives — which does not survive an answer that is a SET. On a
            # multi-select card the first slot is often "none of these", or the options carry an
            # intrinsic order, and demanding a recommendation there is an arbitrary line.
            problems.append(
                f"{where}: the recommended option is #{marked[0] + 1}, not first. It goes first so "
                f"the reader meets the answer before the alternatives.")

        # ── the question-shaped exit ────────────────────────────────────────────────────────────
        if not QUESTION_EXIT.search(labels[-1]):
            # ⛔ THE ADVICE HAS TO BE POSSIBLE, and the first version's was not (r1 Blocking).
            # `AskUserQuestion` accepts 2–4 options. Measured over 49 real historical questions:
            # 29 already use all four slots, and 22 of those were being told to "add a fifth" — an
            # instruction the schema refuses, so following it produces a SECOND failure and leaves
            # the reader to work out unaided that the repair was to REPLACE, not append. A guard
            # that blocks correctly and then misdirects the repair is worse at the moment of use
            # than the prose it replaced, because prose never asserted a wrong next step.
            # ⚠ A NEAR-MISS IS REWORDED (r2 H-3). Told to ADD an exit beside `C — I have questionS
            # about these`, you get two options doing the same work — the defect §19 exists for, and
            # the one this guard's docstring admits it cannot see. So the advice would have created
            # a violation invisible to the machine that gave it.
            near = NEAR_EXIT.search(labels[-1])
            last_letter = chr(ord("A") + len(labels) - 1)
            fix = (f"REWORD option {len(labels)} to '{last_letter} — I have a question about "
                   f"these' — it is already reaching for the exit, and adding a second one would "
                   f"give you two options doing the same work"
                   if near else
                   f"add '{chr(ord('A') + len(labels))} — I have a question about these'"
                   if len(labels) < MAX_OPTIONS else
                   f"REPLACE option {len(labels)} with "
                   f"'{last_letter} — I have a question about these' — the tool accepts "
                   f"{MAX_OPTIONS} options at most, so the exit costs you a choice")
            problems.append(
                f"{where}: the last option is {labels[-1][:48]!r}, not a question-shaped exit. "
                f"§19: {fix}. "
                f"A form with no way to ask turns every clarification into a rejected choice.")

        # ── a floor against the bare label ──────────────────────────────────────────────────────
        for li, o in enumerate(options[:-1]):
            desc = str(o.get("description", "") or "").strip()
            if len(desc) < MIN_DESCRIPTION:
                problems.append(
                    f"{where}: option {li + 1} carries {len(desc)} characters of "
                    f"description. §19: each option states its rationale AND its trade-off — what "
                    f"it costs or gives up.")
    return problems


def payload_of(raw: str) -> list[dict]:
    """The questions, out of either a hook envelope or a bare tool input. Raises on anything else —
    a payload this cannot read is CANNOT RUN, and CANNOT RUN is a failure."""
    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    # PreToolUse wraps it; a direct invocation does not. Accept both rather than making the caller
    # unwrap — the two shapes have appeared in this repo's hooks already.
    wrapped = data.get("tool_input")
    inner: dict = wrapped if isinstance(wrapped, dict) else data
    questions = inner.get("questions")
    if not isinstance(questions, list):
        raise ValueError("no `questions` list in the payload")
    return [q for q in questions if isinstance(q, dict)]


def self_test() -> int:
    cases: list[tuple[str, Callable[[], object]]] = []

    def case(name, fn):
        cases.append((name, fn))

    def card(labels, descs=None, multi=False, question="Which one? A/B differ in scope."):
        descs = descs or ["x" * 60] * len(labels)
        return [dict(question=question, header="H", multiSelect=multi,
                     options=[dict(label=lb, description=d) for lb, d in zip(labels, descs)])]

    GOOD = ["A — Do the thing (Recommended)", "B — Do a different thing",
            "C — I have a question about these"]

    case("a card following §19 passes", lambda: card_problems(card(GOOD)) == [])
    case("an unlettered option is refused",
         lambda: any("not lettered" in p for p in card_problems(
             card(["Do the thing (Recommended)", "B — Other", "C — I have a question"]))))
    case("a hyphen is accepted, not just an em dash",
         lambda: card_problems(card(["A - Do it (Recommended)", "B - Other",
                                     "C - I have a question about these"])) == [])
    case("an en dash is accepted too",
         lambda: card_problems(card(["A – Do it (Recommended)", "B – Other",
                                     "C – I have a question about these"])) == [])
    case("letters out of order are refused",
         lambda: any("letters run" in p for p in card_problems(
             card(["A — One (Recommended)", "C — Two", "D — I have a question"]))))
    case("a missing recommendation is refused",
         lambda: any("nothing is marked" in p for p in card_problems(
             card(["A — One", "B — Two", "C — I have a question about these"]))))
    case("two recommendations on a single-select card are refused",
         lambda: any("2 options marked" in p for p in card_problems(
             card(["A — One (Recommended)", "B — Two (Recommended)",
                   "C — I have a question about these"]))))
    # ⚠ On a multi-select card "exactly one" is the wrong rule — several can legitimately be
    # advised together — so the clause relaxes to "at least one" rather than being switched off.
    case("two recommendations on a MULTI-select card are allowed",
         lambda: card_problems(card(["A — One (Recommended)", "B — Two (Recommended)",
                                     "C — I have a question about these"], multi=True)) == [])
    case("a multi-select card with NO recommendation is still refused",
         lambda: any("nothing is marked" in p for p in card_problems(
             card(["A — One", "B — Two", "C — I have a question"], multi=True))))
    case("a recommendation that is not first is refused",
         lambda: any("not first" in p for p in card_problems(
             card(["A — One", "B — Two (Recommended)", "C — I have a question about these"]))))
    case("a missing question-exit is refused",
         lambda: any("question-shaped exit" in p for p in card_problems(
             card(["A — One (Recommended)", "B — Two", "C — Three"]))))
    case("the question-exit ignores case and trailing words",
         lambda: card_problems(card(["A — One (Recommended)", "B — Two",
                                     "C — I Have A Question, actually several"])) == [])
    case("a bare label is refused",
         lambda: any("characters of description" in p for p in card_problems(
             card(GOOD, descs=["short", "x" * 60, "x" * 60]))))
    # ⚠ THE EXIT OPTION IS EXEMPT from the floor: "say what is unclear" needs no trade-off, and
    # demanding one would teach the writer to pad it.
    case("the question-exit option needs no rationale",
         lambda: card_problems(card(GOOD, descs=["x" * 60, "x" * 60, "ask"])) == [])
    case("a one-option card is refused",
         lambda: any("real choice" in p for p in card_problems(card(["A — Only one"]))))
    # ⭐ r1 M-1. Two options plus the mandatory exit is ONE course of action.
    case("a card whose only alternative is the exit is refused",
         lambda: any("real choice" in p for p in card_problems(
             card(["A — Ship it (Recommended)", "B — I have a question about these"]))))

    # ⭐⭐ r1 BLOCKING (Claude), measured over 49 real questions: 29 already use all four option
    # slots, and 22 of those were told to add a fifth — which the tool's schema refuses. The advice
    # has to change shape at the ceiling, or following it produces a second, different failure.
    def _exit_advice(n: int) -> str:
        labels = [f"{chr(ord('A') + i)} — Option {i}" for i in range(n)]
        labels[0] += " (Recommended)"
        return " ".join(card_problems(card(labels)))

    case("below the ceiling the advice is to ADD the exit",
         lambda: "add 'D — I have a question" in _exit_advice(3))
    # ⭐ r2, both halves: MAX_OPTIONS shaped the ADVICE and enforced nothing, so a five-option card
    # passed this guard clean and then failed the tool's own schema.
    # ⚠ ASSERT ON THE CEILING MESSAGE, not on a phrase two messages share. The first spelling of
    # this case matched "the tool accepts 4", which the EXIT ADVICE also says at the ceiling — so
    # deleting the ceiling check entirely left the case green. A substring case is satisfied by any
    # message containing the substring, which is not the same as the one you meant.
    case("a card above the tool's ceiling is refused here, not by the tool",
         lambda: any("5 options; the tool accepts 4" in p for p in card_problems(
             card([chr(ord("A") + i) + " — Option " + str(i) for i in range(5)]))))
    # ⭐ r2 H-3. Telling a NEAR-MISS exit to add a second exit manufactures two options doing the
    # same work — the defect §19 exists for, and the one this guard admits it cannot see. The advice
    # would have created a violation invisible to the machine that gave it.
    def _near_miss() -> list[str]:
        return card_problems(card(["A — Ship it (Recommended)", "B — Wait",
                                   "C — I have questions about these"]))

    case("a near-miss exit is told to REWORD, not to add a second one",
         lambda: any("REWORD option 3" in p for p in _near_miss())
         and not any("add 'D" in p for p in _near_miss()))
    # ⭐ r2, Codex: "any option contains the exit" survived, because no case put it in the middle.
    case("an exit in the MIDDLE does not satisfy the last-option rule",
         lambda: any("question-shaped exit" in p for p in card_problems(
             card(["A — Ship it (Recommended)", "B — I have a question about these",
                   "C — Wait a week"]))))
    # ⭐ r2, Codex: `[A-Z]` was not pinned — a lowercase letter passed.
    case("the letter must be a CAPITAL",
         lambda: any("not lettered" in p for p in card_problems(
             card(["a — Ship it (Recommended)", "b — Wait",
                   "c — I have a question about these"]))))
    case("AT the ceiling the advice is to REPLACE, because the tool takes four options",
         lambda: "REPLACE option 4" in _exit_advice(4)
         and "add 'E" not in _exit_advice(4))

    # ⭐ r1: Codex's High and Claude's M-2 wanted this token looser and stricter respectively.
    # Anchoring at the END of the label is what satisfies both.
    case("a reason may ride inside the marker — §19 asks for one",
         lambda: card_problems(card(["A — Ship it (Recommended — it is reversible)",
                                     "B — Wait", "C — I have a question about these"])) == [])
    case("the marker is case-insensitive",
         lambda: card_problems(card(["A — Ship it (recommended)", "B — Wait",
                                     "C — I have a question about these"])) == [])
    case("markdown emphasis around the marker still counts",
         lambda: card_problems(card(["A — Ship it **(Recommended)**", "B — Wait",
                                     "C — I have a question about these"])) == [])
    # ⭐ r2 BLOCKING. Every natural rendering of "marked Recommended, WITH ITS REASON" must pass;
    # two rounds of parenthesis-parsing refused a different one each time.
    case("the reason may sit outside the parenthesis, after a full stop, or nest",
         lambda: all(card_problems(card(["A — Ship it " + suffix, "B — Wait",
                                         "C — I have a question about these"])) == []
                     for suffix in ["(Recommended)", "(Recommended).", "(recommended)",
                                    "(Recommended) — it is reversible",
                                    "(Recommended — costs one review round)",
                                    "(Recommended: see ADR-0010 (v2))",
                                    "**(Recommended)**", "— recommended, it is reversible"]))
    # ⚠ THE DELIBERATE TRADE, pinned so it reads as a decision and not an oversight: a label that
    # merely DISCUSSES the word now counts as a marker. Refusing a compliant card costs a real turn;
    # accepting one that says "recommend" twice costs a clear message. The second is cheaper, and
    # this hook BLOCKS, so the direction of the cheaper error is the whole design question.
    case("a label that merely discusses the word counts — the accepted false positive",
         lambda: card_problems(card(["A — Explain what (Recommended) means to a reader",
                                     "B — Use plainer wording",
                                     "C — I have a question about these"])) == [])
    case("but a NEGATED recommendation is not one",
         lambda: all(any("nothing is marked" in problem for problem in card_problems(
             card(["A — Delete the branch (" + neg + ")", "B — Keep it",
                   "C — I have a question about these"])))
             for neg in ["Recommended against by CI", "not recommended", "never recommended"]))

    # ⭐ r1 M-5. "First" exists so the reader meets the answer before the alternatives; that reason
    # does not survive an answer which is a SET.
    case("on a MULTI-select card the recommendation need not be first",
         lambda: card_problems(card(["A — Neither of these", "B — Do it (Recommended)",
                                     "C — I have a question about these"], multi=True)) == [])
    case("on a single-select card it must still be first",
         lambda: any("not first" in p for p in card_problems(
             card(["A — Neither", "B — Do it (Recommended)",
                   "C — I have a question about these"]))))

    # ⭐ r1 M-4. 24 CJK characters carry what ~60 ASCII ones do; the floor's claim is about
    # information, not len().
    case("a dense description with no spaces clears the lower floor",
         lambda: card_problems(card(GOOD, descs=["今すぐ出荷する。巻き戻せるがレビューを一回失う。",
                                                 "x" * 60, "ask"])) == [])
    case("a dense description that is still bare is refused",
         lambda: any("characters of description" in p for p in card_problems(
             card(GOOD, descs=["出荷", "x" * 60, "ask"]))))
    # ⭐ r1 L-2. The manifest mutated the floor to 0, which the 5-character fixture kills; the
    # NUMBER 40 — what §19's floor actually claims — was pinned only above 5. A boundary pair pins
    # it, and pins the `.strip()` at the same time.
    case("the floor is 15 exactly — 14 is refused, 15 is accepted",
         lambda: any("characters of description" in p
                     for p in card_problems(card(GOOD, descs=["a b" + "x" * 11, "x" * 60, "ask"])))
         and card_problems(card(GOOD, descs=["a b" + "x" * 12, "x" * 60, "ask"])) == [])
    # ⭐ r2 H-4. The old floor had a "dense script" relaxation keyed on SPACES, so no Korean
    # description could ever reach it and Japanese lost it to one Latin product name. One floor for
    # every script, or the guard holds an opinion about languages it cannot defend.
    case("a description in any script clears the floor",
         lambda: all(card_problems(card(GOOD, descs=[d, "x" * 60, "ask"])) == []
                     for d in ["지금 배포한다. 되돌릴 수 있다.",
                               "今すぐ出荷する。巻き戻せるがレビューを一回失う。",
                               "PR を今すぐマージする。巻き戻せるがレビュー一回分を失う。",
                               "Fast, exact, costs 30s."]))
    case("whitespace does not count toward the floor",
         lambda: any("characters of description" in p for p in card_problems(
             card(GOOD, descs=["a b" + " " * 60, "x" * 60, "ask"]))))
    case("an empty payload is CANNOT RUN, not a pass",
         lambda: card_problems([]) and "CANNOT RUN" in card_problems([])[0])
    case("every question in a multi-question payload is checked",
         lambda: len(card_problems(card(GOOD) + card(["A — One", "B — Two", "C — Three"]))) == 2)
    # ⚠ `bool(probs) and` — r1 L-1. Without it, `all([])` is True and the case stayed GREEN with
    # `card_problems` neutered to `return []`: an assertion that deleting the subject satisfies.
    case("the problem names WHICH question, so a two-question card is actionable",
         lambda: (lambda probs: bool(probs) and all(p.startswith("question ") for p in probs))(
             card_problems(card(["A — One", "B — Two", "C — Three"]))))

    case("a PreToolUse envelope is unwrapped",
         lambda: payload_of(json.dumps({"tool_name": "AskUserQuestion",
                                        "tool_input": {"questions": card(GOOD)}}))
         == card(GOOD))
    case("a non-dict entry in the questions list is dropped, not passed on",
         lambda: payload_of(json.dumps({"questions": ["not a question", {"header": "H"}]}))
         == [{"header": "H"}])
    case("a bare tool input is accepted too",
         lambda: payload_of(json.dumps({"questions": card(GOOD)})) == card(GOOD))
    case("a payload with no questions list RAISES rather than passing",
         lambda: _raises(lambda: payload_of(json.dumps({"tool_input": {}})), ValueError))
    case("a JSON array RAISES rather than passing",
         lambda: _raises(lambda: payload_of("[]"), ValueError))
    case("malformed JSON RAISES rather than passing",
         lambda: _raises(lambda: payload_of("{not json"), json.JSONDecodeError))
    # ⭐ The clause this guard does NOT cover, pinned so nobody reads its silence as coverage.
    case("two options that are the SAME WORK pass — this guard cannot see that",
         lambda: card_problems(card(["A — Merge both, in order (Recommended)",
                                     "B — Merge both, review after",
                                     "C — I have a question about these"])) == [])

    # ⭐⭐ r1 H-2. The hook reads exactly ONE thing from this script — its exit code — and nothing
    # executed `main()`. `return 2` -> `return 0` left 24/24 green, so the manifest was green, so CI
    # was green, while every malformed card was admitted. The fail-open one layer OUT of the one the
    # manifest already guarded.
    def _rc_for(raw) -> int:
        # ⚠ BYTES, not str — r2 H-2's input cannot be expressed as valid UTF-8 text, and a helper
        # that could not carry it is exactly how that path went unexercised.
        data = raw if isinstance(raw, bytes) else raw.encode()
        return subprocess.run([sys.executable, __file__], input=data,
                              capture_output=True).returncode

    case("a bad card EXITS 2 — the exit code is all the hook can see",
         lambda: _rc_for(json.dumps({"questions": card(["A — One", "B — Two", "C — Three"])})) == 2)
    case("a good card exits 0",
         lambda: _rc_for(json.dumps({"questions": card(GOOD)})) == 0)
    case("an unreadable payload exits 2, never 0",
         lambda: _rc_for("{not json") == 2 and _rc_for("") == 2)
    # ⭐ r1 L-5. A malformed option shape raised through `main` and rendered a Python traceback as
    # the body of the refusal panel. Still fail-closed, now with the CANNOT RUN sentence instead.
    # ⭐ r2 H-2. `sys.stdin.read()` sat outside every handler, so undecodable bytes produced a
    # Python traceback rendered inside the refusal panel AND rc=1 — neither of this script's two
    # verdicts.
    case("undecodable stdin is a verdict, not a traceback",
         lambda: _rc_for(b"\xff\xfe garbage") == 2)
    # ⚠ A JSON ARRAY raises `ValueError` from `payload_of`, not `JSONDecodeError` — which is what
    # makes the handler's WIDTH observable. Without this, narrowing `except Exception` to
    # `except json.JSONDecodeError` changed nothing any case could see, because `errors="replace"`
    # means the decode itself never raises and every other bad input is a JSON error.
    case("a payload that is valid JSON but the wrong SHAPE is a verdict too",
         lambda: _rc_for("[]") == 2 and _rc_for('{"tool_input": {}}') == 2)
    case("a malformed option shape is CANNOT RUN, not a traceback",
         lambda: _rc_for(json.dumps({"questions": [{"header": "H", "options": "nope"}]})) == 2)

    # ⭐⭐ THE HOOK ITSELF — r2 M-6. `.claude/hooks/enforce-selection-card.sh` is shell: no
    # `--self-test`, not a `check-*` guard, and BOTH of r1's fixes lived in it while nothing
    # executed it. r2 then found two defects there, one of them Blocking. These run the real file.
    HOOK = REPO / ".claude/hooks/enforce-selection-card.sh"

    def _hook_rc(payload: bytes, path_prefix: str = "") -> int:
        env = dict(os.environ)
        if path_prefix:
            env["PATH"] = path_prefix + os.pathsep + env.get("PATH", "")
        return subprocess.run(["bash", str(HOOK)], input=payload,
                              capture_output=True, env=env).returncode

    _GOOD_CARD = json.dumps({"tool_name": "AskUserQuestion", "tool_input": {"questions": card(GOOD)}})
    _BARE_BAD = json.dumps({"questions": card(["A — One", "B — Two", "C — Three"])})
    _OTHER_TOOL = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})

    case("the hook blocks a bad card",
         lambda: _hook_rc(_BARE_BAD.encode()) == 2)
    case("the hook passes a good card",
         lambda: _hook_rc(_GOOD_CARD.encode()) == 0)
    # ⚠ r1 Blocking: absence of a `tool_name` is not "some other tool" — the checker accepts a bare
    # tool input, and treating that as none-of-my-business was a silent fail-open.
    case("a bare tool input is CHECKED, not waved through",
         lambda: _hook_rc(_BARE_BAD.encode()) == 2
         and _hook_rc(json.dumps({"questions": card(GOOD)}).encode()) == 0)
    case("the hook leaves a positively different tool alone",
         lambda: _hook_rc(_OTHER_TOOL.encode()) == 0)
    # ⚠ r2 Blocking: `INPUT=$(cat)` strips NUL, so bytes the checker refuses became valid JSON on
    # the way in — measured `direct=2 hook=0`.
    case("a NUL byte survives the trip to the checker",
         lambda: _hook_rc(b'{"quest\x00ions":true}') == 2)
    case("empty stdin is a verdict, not a pass",
         lambda: _hook_rc(b"") == 2)

    def _shim(script: str) -> str:
        """A directory whose `python3` is `script`. Not a fixture of the hook — a fixture of the
        ENVIRONMENT, which is where both of r2's hook defects actually lived."""
        d = tempfile.mkdtemp()
        exe = pathlib.Path(d) / "python3"
        exe.write_text(script)
        exe.chmod(0o755)
        return d

    # ⚠ r2 High: the detector reported through STDOUT, so a banner made the skip test fail and the
    # hook rendered the §19 panel over a Bash payload. Exit codes cannot be prefixed.
    case("a chatty interpreter does not make the hook block another tool",
         lambda: _hook_rc(_OTHER_TOOL.encode(),
                          _shim("#!/bin/sh\necho 'pyenv: shim banner'\nexec %s \"$@\"\n"
                                % sys.executable)) == 0)
    # ⚠ r1 H-3: a broken interpreter exited 0 in silence, disarming the guard for a whole session.
    case("a broken interpreter warns and exits 1 — never a silent 0",
         lambda: _hook_rc(_GOOD_CARD.encode(), _shim("#!/bin/sh\nexit 1\n")) == 1)

    failed = 0
    for name, fn in cases:
        why = ""
        try:
            ok = bool(fn())
        except Exception as exc:                                   # noqa: BLE001 - report, not hide
            ok, why = False, repr(exc)
        if ok:
            print(f"  ok     {name}")
        else:
            print(f"  [FAIL] {name}")
            if why:
                print(f"    raised: {why}")
        failed += not ok
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def _raises(fn, exc: type[BaseException]) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:                                              # noqa: BLE001
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    try:
        # ⚠ INSIDE the try (r2 H-2). `sys.stdin.read()` sat outside every handler, so undecodable
        # bytes produced a Python traceback rendered inside the refusal panel AND rc=1 — which is
        # neither of this script's two verdicts. Read as bytes and decode leniently: the payload is
        # arbitrary user text arriving through a shell, and mojibake in a label is the reader's
        # problem, not a reason to refuse to look at the card at all.
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        questions = payload_of(raw)
    except Exception as exc:                                       # noqa: BLE001
        print(f"CANNOT RUN — {exc}. Treat this as NOT CHECKED, never as a pass.", file=sys.stderr)
        return 2

    try:
        problems = card_problems(questions)
    except Exception as exc:                                       # noqa: BLE001
        # ⚠ r1 L-5. `options` as a dict, or a list of strings, raised through here and rendered a
        # Python traceback as the body of the refusal panel. The DIRECTION was already right —
        # fail closed — so only the message changes.
        print(f"CANNOT RUN — the card could not be read ({exc!r}). Treat this as NOT CHECKED.",
              file=sys.stderr)
        return 2
    if not problems:
        return 0
    for p in problems:
        print(f"  ✗ {p}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
