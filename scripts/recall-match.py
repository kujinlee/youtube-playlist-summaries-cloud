#!/usr/bin/env python3
"""Does anything in memory FIRE at this moment? — the matcher backlog #191 calls C5.

WHY THIS EXISTS
---------------
The assistant's project memory holds 142 files behind a ~150-line index, and **nothing reads it**.
Measured 2026-09-28: no file in the `remember` plugin references `MEMORY.md`; all 133 index rows
arrive every session, unfiltered; and the only "matcher" is attention over the whole context window.
Measured the same day: of six failure classes sampled from one session, FIVE were already written
down there and were not applied.

⛔ **The failure is MATCHING, not retrieval.** Nothing was un-found — the entries were in context and
did not fire. So a search tool is the wrong instrument: measured, `anchor` returns 34 of 141 files.

WHAT CHANGED THAT MAKES THIS POSSIBLE (2026-09-29)
--------------------------------------------------
Every one of the 141 entries now opens its `description:` with a fixed-grammar trigger:

    FIRES-WHEN: about to open, check or merge a PR; about to call a branch ready

and the situation is already written, in a fixed grammar, on disk:

    Doing: opening the PR for backlog #192        (.claude/plans/<slug>.md, via begin-plan.py)

**Both sides are short strings in one vocabulary**, so this compares them. No embeddings, no index,
no model call. That is not a cost decision — it is what makes the matcher MUTATION-TESTABLE like
every other guard here. A semantic matcher cannot have a case that says *break this line and the
guard goes red via the case that names it*; this can.

⭐ WHY IDF, AND WHY THERE IS BARELY A STOPWORD LIST
---------------------------------------------------
`about` appears in ~70 of the 141 triggers. A raw overlap count would score it the same as
`abortsignal`, which appears in one — and everything would match everything. Inverse document
frequency over THE TRIGGER CORPUS ITSELF drives common words to near-zero weight and rare ones high,
so the discrimination comes from a **measured property of the corpus** rather than a hand-curated
list that would drift. The tiny STOPWORDS set below removes only pure function words that survive
IDF because they are short and ubiquitous; it is a floor, not the mechanism.

⛔ FAIL CLOSED — "no matches" AND "could not look" MUST NOT LOOK THE SAME
-------------------------------------------------------------------------
This is the repo rule this script is most likely to break. A matcher that returns "nothing fired"
when the memory directory is missing, unreadable, or contains zero triggers is reporting a PASS it
did not earn — the exact shape `check_advisory_count`'s missing-anchor rule and §2 of
`docs/portable-practices.md` exist to prevent. So:

    rc=0   matched, or genuinely nothing scored above threshold OVER A NON-EMPTY CORPUS
    rc=2   CANNOT RUN — no memory directory, no readable entries, or ZERO triggers found

A zero over nothing is not a finding.

Usage:
    scripts/recall-match.py --situation "about to open a PR"     # explicit
    scripts/recall-match.py --from-plan                          # read the armed plan's current step
    scripts/recall-match.py --from-stdin                         # a PreToolUse hook payload (JSON)
    scripts/recall-match.py --list                               # every trigger, for review
    scripts/recall-match.py --self-test  # 40 cases
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

OK, CANNOT_RUN = 0, 2

# Minimal floor only — IDF does the real work. See the docstring.
STOPWORDS = frozenset("""
a an the to of in on at for with and or but is are be am was were been it its this that these those
i you my your we our they them he she his her as by from into if then than so not no do does did
""".split())

# Suffixes stripped in that order; `-ing` before `-in` never matters because we only strip once.
_SUFFIXES = ("ing", "edly", "ed", "es", "s")
_MIN_STEM = 4

TRIGGER_PREFIX = "FIRES-WHEN:"
# ⟳ 3 -> 5, MEASURED 2026-09-29 against the real corpus: a correct hit for "stating a figure as
# measured" ranked SIXTH and was discarded by top-3, while the two above it were plausible. Five
# is still short enough to read and wide enough not to throw away a right answer.
DEFAULT_TOP = 5
# ⛔ A FRACTION of the maximum possible weight, never an absolute IDF sum.
# Found by the self-test, not by review: IDF is corpus-size-dependent — a token unique in 141
# entries scores log(141)=4.95, the same token in a 3-entry corpus scores log(3)=1.10. An absolute
# cutoff tuned for 141 therefore stops firing entirely on a smaller corpus, silently, which is the
# fail-open shape this whole script exists to avoid. Expressed as a fraction of log(N) it means the
# same thing at any size. ⟳ TUNED BY MEASUREMENT 2026-09-29, not chosen: over 30 representative
# commands, 0.30 fires on 17% of them while keeping `gh pr create` and silencing `npm test`;
# 0.20 fires on 43% (noise) and 0.40 on 7% (drops the must-fire case).
DEFAULT_THRESHOLD = 0.30


# ----------------------------------------------------------------- pure core
def stem(word: str) -> str:
    """PURE. Crude suffix strip, guarded so short words survive intact.

    Deliberately NOT a real stemmer: every transformation here must be obvious enough that a
    reviewer can predict it, because a surprising stem produces a surprising match and the whole
    argument for this design is that its behaviour is checkable by hand.
    """
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= _MIN_STEM:
            return word[: -len(suf)]
    return word


def tokenise(text: str) -> list[str]:
    """PURE. -> content tokens, lowercased and stemmed, stopwords dropped, order preserved.

    Keeps `_` `-` `.` INSIDE a token, so dotted and hyphenated identifiers survive whole —
    `check-merge-ready.py` stays one high-IDF token, and `.abortSignal()` yields `abortsignal`.

    ⚠ MEASURED, because the first version of this docstring claimed more than the code does:
    a token must START with a letter or digit, so leading punctuation and bracketed suffixes are
    dropped. `cells[-2]` -> `['cell']`, `--mutate` -> `['mutate']`, `tail -1` -> `['tail']`.
    The distinctive marker degrades to its stem rather than surviving intact. That is ACCEPTED,
    not overlooked: widening the class to keep `[` and `]` shatters `split()[i]` into worse noise,
    and an obvious tokeniser a reviewer can predict is worth more here than a clever one. The
    self-test pins these exact outputs so the behaviour cannot drift back into the claim.
    """
    raw = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.\-]*", text.lower())
    return [stem(w) for w in raw if w not in STOPWORDS and len(w) > 1]


def idf(docs: list[list[str]]) -> dict[str, float]:
    """PURE. Inverse document frequency over the trigger corpus itself.

    `log(N / df)`, so a token in every trigger scores 0 and a token in one scores log(N). No
    smoothing: a token absent from the corpus never reaches this function, because the weight is
    only ever looked up for tokens that appeared in it.
    """
    n = len(docs)
    if n == 0:
        return {}
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    return {t: math.log(n / c) for t, c in df.items()}


def score(situation: list[str], trigger: list[str], weights: dict[str, float]) -> float:
    """PURE. Summed IDF of the tokens the two share.

    Set intersection, not multiset: repeating a word in the situation must not inflate the score,
    or a verbose `Doing:` line outranks a precise one.
    """
    return sum(weights.get(t, 0.0) for t in set(situation) & set(trigger))


def coverage(situation: list[str], trigger: list[str]) -> float:
    """PURE. Fraction of the TRIGGER's distinct tokens that the situation shares.

    Asymmetric on purpose: divided by the TRIGGER's length, never the situation's. A long `Doing:`
    line must not be penalised for being descriptive, but a long trigger matched on one word must be.
    """
    tt = set(trigger)
    return len(set(situation) & tt) / len(tt) if tt else 0.0


def relevance(situation: list[str], trigger: list[str], weights: dict[str, float]) -> float:
    """PURE. rarity (summed IDF) x completeness (coverage). Both, because either alone fails.

    ⛔ MEASURED 2026-09-29 over 30 representative commands, and this is why the function exists:
    with IDF ALONE the fire rate was **73% at every threshold from 0.30 to 0.70** — completely flat,
    because one token unique in 141 triggers scores log(141)=4.95 and clears any cutoff by itself.
    A single coincidental word fired as loudly as a real situational match, so the threshold was
    controlling nothing.

    Multiplying by coverage damps exactly that case: `npm test` shares one token with *"writing
    tests that mock a model, API or service boundary"* (1 of 7 -> 0.14) and goes silent, while
    `gh pr create` shares two with *"using gh pr and unsure which remote it resolves"* (2 of 7)
    and still fires. Re-measured: **17% at 0.30**, with the must-fire case kept and the
    must-be-silent case silenced.
    """
    return score(situation, trigger, weights) * coverage(situation, trigger)


def rank(situation: str, entries: list[tuple[str, str]], top: int = DEFAULT_TOP,
         threshold: float = DEFAULT_THRESHOLD) -> list[tuple[str, str, float]]:
    """PURE. -> [(name, trigger, score)] above `threshold`, best first, at most `top`.

    ⚠ `top` is a NOISE control, not an accuracy one. A matcher that prints six entries every time
    is one nobody reads, which is the failure mode of the 133-row index it replaces.

    `threshold` is a FRACTION of log(N), not an absolute score — see DEFAULT_THRESHOLD for the
    measured reason.
    """
    docs = [tokenise(t) for _, t in entries]
    weights = idf(docs)
    # Scale to the corpus: see DEFAULT_THRESHOLD. max(len,2) keeps log() positive for a 1-entry
    # corpus, where no token can be rare relative to anything and nothing should fire.
    cutoff = threshold * math.log(max(len(docs), 2))
    sit = tokenise(situation)
    scored = [
        (name, trig, relevance(sit, toks, weights))
        for (name, trig), toks in zip(entries, docs)
    ]
    hits = [s for s in scored if s[2] >= cutoff]
    hits.sort(key=lambda s: (-s[2], s[0]))
    return hits[:top]


def parse_trigger(description: str) -> str | None:
    """PURE. -> the trigger clause of a `description:` value, or None if it carries no trigger.

    The trigger runs to the first em-dash, which is what the 2026-09-29 rewrite used to separate it
    from the pre-existing summary. A description with no `FIRES-WHEN:` returns None rather than ""
    so the caller can COUNT entries that have not been rewritten instead of silently scoring them 0.
    """
    d = description.strip()
    if not d.startswith(TRIGGER_PREFIX):
        return None
    return d[len(TRIGGER_PREFIX):].split("—", 1)[0].strip() or None


def plan_situation(sentinel_text: str, plan_text: str) -> str | None:
    """PURE. -> the `Doing:` line of the first UNTICKED step, or None.

    Reads the plan `begin-plan.py` writes. Returns None for a finished plan, a paused one with
    nothing outstanding, or a shape it does not recognise — never a guess, because a wrong
    situation surfaces wrong entries and that is worse than surfacing none.
    """
    if "paused:" in sentinel_text:
        return None
    for block in re.split(r"^### ", plan_text, flags=re.M)[1:]:
        if re.search(r"^- \[ \]", block, re.M):
            m = re.search(r"^\s*-\s*\*\*Doing:\*\*\s*(.+)$", block, re.M)
            if m:
                return m.group(1).strip()
            head = block.split("\n", 1)[0]
            return re.sub(r"^Task \d+:\s*", "", head).strip() or None
    return None


def tool_situation(payload: dict) -> str | None:
    """PURE. -> a situation string from a PreToolUse hook payload, or None.

    The command itself is the situation: `gh pr create` IS "about to open a PR" without anyone
    having to write a breadcrumb. Falls back to the tool name so a non-Bash tool still says
    something, and returns None rather than "" when the payload carries neither.
    """
    ti = payload.get("tool_input") or {}
    for key in ("command", "file_path", "pattern", "path"):
        v = ti.get(key)
        if isinstance(v, str) and v.strip():
            return f"{payload.get('tool_name', '')} {v}".strip()
    name = payload.get("tool_name")
    return name.strip() if isinstance(name, str) and name.strip() else None


# ------------------------------------------------------------------ corpus IO
def memory_dir(cwd: Path | None = None) -> Path | None:
    """-> the memory directory for this project, or None.

    The corpus lives OUTSIDE the repository, under the harness's own per-project slug: an absolute
    path with every non-alphanumeric character replaced by `-`. Derived, never hardcoded, so this
    keeps working in a worktree or a clone at a different path.
    """
    root = (cwd or Path.cwd()).resolve()
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(root))
    d = Path.home() / ".claude" / "projects" / slug / "memory"
    return d if d.is_dir() else None


def load_entries(d: Path) -> tuple[list[tuple[str, str]], int]:
    """-> ([(name, trigger)], files_seen). Unreadable files are COUNTED, never silently skipped.

    ⛔ No try/except that swallows and continues as if nothing happened: a file this cannot parse is
    a file whose lesson cannot fire, and the caller needs the count to tell a real empty result from
    a broken read.
    """
    entries: list[tuple[str, str]] = []
    seen = 0
    for p in sorted(d.glob("*.md")):
        if p.name == "MEMORY.md":
            continue
        seen += 1
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.match(r"^---\n(.*?\n)---\n", text, re.S)
        if not m:
            continue
        for line in m.group(1).split("\n"):
            if line.startswith("description:"):
                val = line[len("description:"):].strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                trig = parse_trigger(val)
                if trig:
                    entries.append((p.stem, trig))
                break
    return entries, seen


# --------------------------------------------------------------------- report
def report(situation: str, hits: list[tuple[str, str, float]], total: int) -> str:
    if not hits:
        return f"recall-match: nothing fires for this situation ({total} triggers checked)"
    out = [f"⭐ recall-match — {len(hits)} of {total} memory entries fire here:"]
    for name, trig, sc in hits:
        out.append(f"   [{sc:.1f}] {name}")
        out.append(f"          FIRES-WHEN: {trig}")
    out.append("   (open the named file for the detail)")
    return "\n".join(out)


# ------------------------------------------------------------------ self-test
def _self_test() -> int:
    ok = fail = 0

    def check(label, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}\n   got:  {got!r}\n   want: {want!r}")

    # --- stem (5)
    check("stem strips -ing", stem("indexing"), "index")
    check("stem strips -ed", stem("merged"), "merg")
    check("stem keeps short words whole", stem("adds"), "adds")
    check("stem leaves a bare stem alone", stem("open"), "open")
    check("stem strips -s on a long word", stem("reviews"), "review")

    # --- tokenise (6)
    check("tokenise drops function words but KEEPS 'about' (IDF's job, not the list's)",
          tokenise("about to open a PR"), ["about", "open", "pr"])
    check("tokenise keeps dotted names", tokenise("check-merge-ready.py"), ["check-merge-ready.py"])
    check("tokenise drops leading dashes from a flag", tokenise("run --mutate ."),
          ["run", "mutate"])
    check("tokenise degrades a bracketed index to its stem (measured, not assumed)",
          tokenise("cells[-2]"), ["cell"])
    check("tokenise lowercases", tokenise("AbortSignal"), ["abortsignal"])
    check("tokenise drops single chars", tokenise("a b cd"), ["cd"])
    check("tokenise on empty text", tokenise(""), [])

    # --- idf (4)
    w = idf([["a"], ["a"], ["b"]])
    check("idf is 0 for a token in every doc", round(w["a"] - math.log(3 / 2), 6), 0.0)
    check("idf is higher for a rarer token", w["b"] > w["a"], True)
    check("idf of an empty corpus is empty", idf([]), {})
    check("idf of one doc gives weight 0", idf([["x"]])["x"], 0.0)

    # --- score (3)
    weights = {"pr": 2.0, "merge": 3.0, "open": 1.0}
    check("score sums shared weights", score(["pr", "merge"], ["pr", "merge"], weights), 5.0)
    check("score ignores unshared tokens", score(["pr"], ["merge"], weights), 0.0)
    check("score does not double-count a repeat",
          score(["pr", "pr"], ["pr"], weights), 2.0)

    # --- parse_trigger (4)
    check("parse_trigger takes text up to the em-dash",
          parse_trigger("FIRES-WHEN: about to open a PR — PR #324 MERGED"), "about to open a PR")
    check("parse_trigger returns None with no prefix",
          parse_trigger("PR #324 MERGED (af4d9033)"), None)
    check("parse_trigger returns None on an empty trigger",
          parse_trigger("FIRES-WHEN:  — body"), None)
    check("parse_trigger works with no em-dash at all",
          parse_trigger("FIRES-WHEN: using .abortSignal()"), "using .abortSignal()")

    # --- coverage (3)
    check("coverage divides by the TRIGGER's length",
          coverage(["a", "b", "c"], ["a", "b"]), 1.0)
    check("coverage damps one token matched in a long trigger",
          round(coverage(["a"], ["a", "b", "c", "d"]), 3), 0.25)
    check("coverage of an empty trigger is 0, never a divide-by-zero",
          coverage(["a"], []), 0.0)

    # --- relevance (2)
    check("relevance multiplies rarity by completeness",
          relevance(["pr", "merge"], ["pr", "merge"], {"pr": 2.0, "merge": 3.0}), 5.0)
    check("relevance halves a score when half the trigger is matched",
          relevance(["pr"], ["pr", "gone"], {"pr": 4.0}), 2.0)

    # --- rank (5)
    corpus = [
        ("merge-ready", "about to open, check or merge a PR; about to call a branch ready"),
        ("positional-read", "indexing a parsed row or list by position"),
        ("abort-returns", "using .abortSignal() with postgrest-js"),
    ]
    top = rank("opening the PR for backlog #192", corpus)
    check("rank surfaces the PR entry for a PR situation",
          top[0][0] if top else None, "merge-ready")
    check("rank does not surface the unrelated entry",
          "abort-returns" in [h[0] for h in top], False)
    check("rank surfaces the abort entry for an abortSignal situation",
          rank("adding .abortSignal() to the query", corpus)[0][0], "abort-returns")
    check("rank returns nothing for an unrelated situation",
          rank("cooking dinner tonight", corpus), [])
    check("rank respects top-N", len(rank("open merge PR indexing position abortsignal",
                                          corpus, top=1)), 1)

    # --- the three parameters check-fixture-variation caught as never-varied (3)
    # Each of these passes a DIFFERENT value for a parameter every other case held constant, so a
    # clause reading it is no longer unguarded. Found by the guard, not by review.
    other_corpus = [
        ("docker-restart", "a gate needs Docker and it is unresponsive"),
        ("worktree-push", "pushing from a git worktree"),
    ]
    check("rank reads `entries` — a different corpus surfaces a different entry",
          rank("the docker gate is unresponsive", other_corpus)[0][0], "docker-restart")
    check("rank reads `threshold` — the same hit disappears when it is raised",
          rank("adding .abortSignal() to the query", corpus, threshold=0.99), [])
    check("score reads `weights` — a different weighting changes the total",
          score(["pr"], ["pr"], {"pr": 9.0}), 9.0)

    # --- plan_situation (4)
    plan = ("### Task 1: Write it\n\n- [x] **Step 1 of 2** — Write it\n"
            "  - **Doing:** writing the matcher\n  - **Why:** because\n\n"
            "### Task 2: Wire it\n\n- [ ] **Step 2 of 2** — Wire it\n"
            "  - **Doing:** wiring a PreToolUse hook\n  - **Why:** a guard needs a caller\n")
    check("plan_situation takes the first UNTICKED step",
          plan_situation("plan: x\n", plan), "wiring a PreToolUse hook")
    check("plan_situation returns None when paused",
          plan_situation("plan: x\npaused: waiting on CI\n", plan), None)
    check("plan_situation returns None when everything is ticked",
          plan_situation("plan: x\n", plan.replace("- [ ]", "- [x]")), None)
    check("plan_situation falls back to the task heading with no Doing line",
          plan_situation("plan: x\n", "### Task 1: Wire it\n\n- [ ] **Step 1 of 1** — Wire it\n"),
          "Wire it")

    print(f"\n{ok}/{ok + fail} self-test cases passed" if not fail
          else f"\n{ok} passed, {fail} FAILED")
    return 0 if not fail else 1


# ----------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--situation")
    ap.add_argument("--from-plan", action="store_true")
    ap.add_argument("--from-stdin", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return _self_test()

    d = memory_dir()
    if d is None:
        print("CANNOT RUN: no memory directory for this project — nothing was checked.",
              file=sys.stderr)
        return CANNOT_RUN
    entries, seen = load_entries(d)
    if not entries:
        print(f"CANNOT RUN: {seen} memory file(s) read, ZERO carry a '{TRIGGER_PREFIX}' trigger. "
              f"A zero over an empty corpus is not a finding.", file=sys.stderr)
        return CANNOT_RUN

    if a.list:
        for name, trig in entries:
            print(f"{name}\n    {trig}")
        print(f"\n{len(entries)} of {seen} entries carry a trigger")
        return OK

    if a.situation:
        situation = a.situation
    elif a.from_stdin:
        raw = sys.stdin.read().strip()
        if not raw:
            print("CANNOT RUN: --from-stdin got an empty payload.", file=sys.stderr)
            return CANNOT_RUN
        try:
            situation = tool_situation(json.loads(raw))
        except json.JSONDecodeError:
            print("CANNOT RUN: --from-stdin payload is not JSON.", file=sys.stderr)
            return CANNOT_RUN
        if not situation:
            return OK  # a payload with no usable field is a real "nothing to match on"
    elif a.from_plan:
        sentinel = Path(".claude/executing-plan")
        if not sentinel.is_file():
            print("CANNOT RUN: no plan is armed (.claude/executing-plan absent).", file=sys.stderr)
            return CANNOT_RUN
        st = sentinel.read_text(encoding="utf-8")
        m = re.search(r"^plan:\s*(.+)$", st, re.M)
        if not m or not Path(m.group(1).strip()).is_file():
            print("CANNOT RUN: the sentinel names no readable plan file.", file=sys.stderr)
            return CANNOT_RUN
        situation = plan_situation(st, Path(m.group(1).strip()).read_text(encoding="utf-8"))
        if not situation:
            print("recall-match: the armed plan has no outstanding step to match on.")
            return OK
    else:
        ap.error("one of --situation / --from-plan / --from-stdin / --list / --self-test")

    print(report(situation, rank(situation, entries, a.top, a.threshold), len(entries)))
    return OK


if __name__ == "__main__":
    sys.exit(main())
