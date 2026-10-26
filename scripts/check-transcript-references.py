#!/usr/bin/env python3
"""Did the turn just completed show the reader a bare `#N`?

    python3 scripts/check-transcript-references.py --decide   # reads a Stop-hook payload on stdin
    python3 scripts/check-transcript-references.py --self-test # 19 cases

WHY THIS EXISTS (owner's decision, 2026-10-20)
----------------------------------------------
`check-reference-namespace.py` enforces "qualify the namespace" across 14 reader-facing FILES.
The owner asked whether the transcript was covered too, and it was not — not by a decision like
the other exclusions, each of which is named in that file with a reason, but by OMISSION: its
`SCOPE` is a tuple of repo-relative paths and the transcript lives in `~/.claude/projects/`, so
it was never in the frame.

⭐ MEASURED on the session that prompted this, using that guard's OWN predicates over the
transcript's assistant text: **64 bare references against 10 qualified** — a worse ratio than the
files, on the surface the human reads LIVE. The owner's words were *"when I see bare #N, it is
confusing to me"*, and they had already had to ask twice in one session which namespace a number
belonged to.

⛔ AND IT INVERTS THE 2026-08-27 VERDICT ONLY ON THIS SURFACE, WHICH IS WHY IT IS NOT A
RE-LITIGATION. That verdict — *"do not script it; the property is semantic"* — was measured over
DOCUMENTS, where ~90% of bare `#N` are titles and ordinals (`Phase 6 #1`, `#54(a)`). Prose written
to a human contains almost none of those: the first five firings in the measured sample were
`#321 #323 #324 #325`, every one a real cross-namespace reference. The false-positive population
that killed the idea for documents is largely absent here. ⚠ That is an ARGUMENT FROM ONE SESSION,
not a corpus, which is exactly why this ships WARN-ONLY and logs every firing: the log is how the
false-positive rate becomes knowable instead of asserted.

ONE RULE, ONE PLACE — THIS FILE PARSES NOTHING AND DEFINES NOTHING
------------------------------------------------------------------
Both halves are IMPORTED from the modules that own them, because a second implementation of a rule
is this repository's most-measured defect (17 instances):

  * the REFERENCE rule — `BARE`, `QUALIFIER`, and the inline-code quotation exemption — from
    `check-reference-namespace.py`. If that file's vocabulary grows a word, this guard grows it too,
    in the same commit, with no action.
  * the TRANSCRIPT reader — `_parse_records`, `windows`, `judged_window`, `texts_of` — from
    `check-banner-armed.py`, which already reads this exact file from this exact hook and has paid
    for the subtleties: one turn of latency (the live turn's final assistant message is not flushed
    when a Stop hook fires), and judging the last NON-LIVE window rather than stepping back N.

WARN-ONLY, AND THE CHANNEL QUESTION ANSWERED RATHER THAN ASSUMED
-----------------------------------------------------------------
It reports; it never blocks. `a-gates-channel-can-be-weaker-than-the-gate` says to ask of every
gate *"WHERE does the failure land, and does a human read that place?"* — its measured case being a
refusal printed to hook stdout, which `CLAUDE.md` states is "shown to the assistant and not reliably
to the user", so eight defects accumulated while a HARD gate fired into silence.

⛔⛔ WHAT THIS SECTION CLAIMED WAS FALSE OF BOTH THE CODE AND THE CALLER, AND IT MADE THE WHOLE
GUARD INERT FOR A DAY — r4 CLAUDE H1, 2026-10-21. It read: *"HERE THE ANSWER INVERTS, AND THAT IS
WHY STDOUT IS THE RIGHT CHANNEL. […] The actor who must change is the ASSISTANT, and hook stdout
reaches exactly the assistant."* Two measured refutations:

  * THIS MODULE NEVER WRITES TO STDOUT. Both prints in `run_decide` carry `file=sys.stderr`, and
    there is no stdout print anywhere outside `--self-test`. The section argued for a channel the
    code does not use — so it was a claim about intent, read as a claim about behaviour.
  * THE CALLER THEN MUTED THE CHANNEL THAT DOES EXIST. `block-idle-stop.sh` invoked this with
    `|| true` and never captured the rc, so quiet, FIRED, CANNOT RUN and an uncaught crash all
    produced `exit 0` — the code that wrapper's own contract header defines as *"allows the stop
    SILENTLY"*. Executed with the sibling observers stubbed to 0: `exit 0`, stdout 0 bytes, the
    warning stranded on stderr where nothing surfaced it.

⛔ THE HONEST STATEMENT, WHICH IS ALL THAT IS CLAIMED NOW: the channel is **stderr**, surfaced by
the wrapper as `exit 1` (*"allows the stop, shows stderr, does not block"*), and the reader there is
the HUMAN — the same auditor the sibling observers reach, by the same mechanism. ⚠ NO CLAIM IS MADE
THAT HOOK STDOUT REACHES THE ASSISTANT. It may; it is not measured here, and an unverified channel
claim is precisely what failed above. The actor-vs-channel question this section was named for is
therefore OPEN, not answered: the human still relays the correction. Warn-only is unchanged.

Two consequences are still real and are not hidden:
  * ONE TURN OF LATENCY, inherited from the reader: the nudge arrives after the human has already
    read the message. This guard cannot prevent the first occurrence, only the next one.
  * A warning nobody must act on has failed in this repository before. So every firing is APPENDED
    to `.claude/transcript-reference-warnings.log`, which is the durable channel and the only way
    the false-positive rate becomes measurable instead of argued.

FAILS CLOSED ON ITS OWN BLINDNESS
----------------------------------
No transcript, an unreadable one, or a payload without `transcript_path` is CANNOT RUN (rc=2),
never a quiet pass. NO SUBJECT — the first turn of a session — is quiet and distinct from both.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / ".claude" / "transcript-reference-warnings.log"


def _owner(stem: str):
    """Import a sibling guard by path. Hyphens make these un-importable by name."""
    spec = importlib.util.spec_from_file_location(
        stem.replace("-", "_"), ROOT / "scripts" / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bare_references(text: str) -> list[tuple[str, str]]:
    """PURE given the owners. -> [(token, the line it sits on)] for every UNQUALIFIED `#N`.

    ⛔ The three clauses are the reference guard's, not this file's: the `BARE` pattern with its
    lookbehind, the adjacent-`QUALIFIER` exemption, and inline-code quoting. Restating any of them
    here would create the second copy that drifts.
    """
    crn = _owner("check-reference-namespace")
    out: list[tuple[str, str]] = []
    for line in text.split("\n"):
        for m in crn.BARE.finditer(line):
            before = line[max(0, m.start() - 40):m.start()]
            if crn.QUALIFIER.search(before.lower()):
                continue
            if line[:m.start()].count("`") % 2 == 1:      # a quotation, not a reference
                continue
            out.append((m.group(0), line.strip()))
    return out


def judge(payload: str) -> tuple[int, str, list[tuple[str, str]]]:
    """-> (rc, message, findings). rc 0 quiet | 1 fired (warn-only) | 2 CANNOT RUN."""
    try:
        data = json.loads(payload) if payload.strip() else {}
    except json.JSONDecodeError as exc:
        return 2, f"CANNOT RUN — the hook payload is not JSON: {exc}", []
    raw = data.get("transcript_path")
    if not raw:
        return 2, "CANNOT RUN — the hook payload carries no `transcript_path`", []
    path = pathlib.Path(raw)
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        return 2, f"CANNOT RUN — the transcript could not be read: {exc}", []

    cba = _owner("check-banner-armed")
    try:
        window = cba.judged_window(cba.windows(cba._parse_records(lines)))
    except Exception as exc:
        # ⛔ backlog #152 r1: unguarded, anything the borrowed turn rule raised left as exit 1 — the warning code.
        return 2, f"CANNOT RUN — the turn rule raised {type(exc).__name__}: {exc}", []
    if window is None:
        return 0, "no completed turn to judge yet", []

    findings: list[tuple[str, str]] = []
    for text in cba.texts_of(window.body):
        findings.extend(bare_references(text))
    if not findings:
        return 0, "the last completed turn qualified every reference it showed", []
    return 1, (f"{len(findings)} bare reference(s) shown to the reader in the last turn — "
               f"a number alone does not say WHICH namespace"), findings


def run_decide(payload: str, log: pathlib.Path | None = None) -> int:
    """⛔ `log` IS A DEFAULTED PARAMETER so a case can drive this without appending to the real
    log. An instrument that edits the repository it measures is backlog #326, and a self-test that
    writes a firing into the evidence file would corrupt the very rate this guard exists to make
    measurable."""
    log = LOG if log is None else log
    rc, message, findings = judge(payload)
    if rc == 2:
        print(f"[transcript-references] {message}", file=sys.stderr)
        return 2
    if rc == 0:
        return 0
    seen: list[str] = []
    for token, line in findings:
        if token not in seen:
            seen.append(token)
    print(f"⚠ [transcript-references] {message}: {', '.join(seen[:10])}"
          f"{' …' if len(seen) > 10 else ''} — write `backlog #N`, `PR #N`, `round N`.",
          file=sys.stderr)
    try:                                   # the durable channel; stdout alone has reached nobody
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as fh:
            for token, line in findings:
                fh.write(json.dumps({"token": token, "line": line[:200]}) + "\n")
    except OSError:
        pass                               # a log that cannot be written must not break a turn
    return 1


def transcript_for(td: str, first: str, second: str) -> str:
    """Build a two-turn transcript and return the hook payload naming it. Test-only."""
    import uuid
    p = pathlib.Path(td) / f"{uuid.uuid4().hex}.jsonl"
    def user(text):
        return {"type": "user", "message": {"role": "user", "content": text}}
    def assistant(text):
        return {"type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}
    recs = [user("go"), assistant(first), user("again"), assistant(second)]
    p.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return json.dumps({"transcript_path": str(p)})


def self_test() -> int:
    import tempfile
    cases = failed = 0

    def case(name: str, got, want=True) -> None:
        nonlocal cases, failed
        cases += 1
        if got != want:
            failed += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    # ── the rule is the OWNER'S, so these cases pin the COMPOSITION, not a copy of it ──
    # backlog #152 r1 (Claude M1): the borrowed turn rule ran unguarded here too — exit 1, the warning code.
    def _tr_rule_raises():
        class _B:
            @staticmethod
            def _parse_records(lines): return [{"type": "user"}]
            @staticmethod
            def windows(recs): raise AttributeError("'str' object has no attribute 'get'")
            @staticmethod
            def judged_window(wins): return wins[-1]      # present, so the raise is the RULE's, not the fake's
        with tempfile.TemporaryDirectory() as d:
            tp = pathlib.Path(d) / "t.jsonl"; tp.write_text('{"type": "user"}\n')
            real = globals()["_owner"]; globals()["_owner"] = lambda name: _B
            try:
                return judge(json.dumps({"transcript_path": str(tp)}))[0]
            finally:
                globals()["_owner"] = real
    try:
        _tr_rc = _tr_rule_raises()
    except Exception as exc:                           # noqa: BLE001 — a crash is a NAMED red, not a dead suite
        _tr_rc = f"RAISED {type(exc).__name__}"
    case("⭐ a raising turn rule is CANNOT RUN (2), never the warning code (backlog #152 r1)", _tr_rc, 2)
    case("⭐ a bare #N in assistant prose is DETECTED",
         [t for t, _ in bare_references("see #291 for the redesign")], ["#291"])
    case("...and a QUALIFIED one is not",
         bare_references("see backlog #291 for the redesign"), [])
    case("the ordinal slack the owner grants is inherited, not re-implemented",
         bare_references("Phase 6 #1 is next"), [])
    case("the inline-code QUOTATION exemption is inherited too",
         bare_references("never write a bare `#39` in prose"), [])
    case("`deliverable #2` passes, which only holds if the OWNER's vocabulary is used",
         bare_references("this is deliverable #2 work"), [])
    case("several on one line are each reported",
         len(bare_references("answers #321, #323 and #325")), 3)
    case("the finding carries the LINE, so the reader can see the context",
         bare_references("answers #321 now")[0][1], "answers #321 now")

    # ── payload handling: CANNOT RUN is distinct from QUIET ──
    case("no transcript_path is CANNOT RUN", judge("{}")[0], 2)
    case("a non-JSON payload is CANNOT RUN", judge("not json")[0], 2)
    case("an unreadable transcript is CANNOT RUN",
         judge(json.dumps({"transcript_path": "/nonexistent/x.jsonl"}))[0], 2)

    with tempfile.TemporaryDirectory() as td:
        def transcript(*turns: list[dict]) -> str:
            p = pathlib.Path(td) / f"t{len(list(pathlib.Path(td).iterdir()))}.jsonl"
            recs = []
            for turn in turns:
                recs.extend(turn)
            p.write_text("".join(json.dumps(r) + "\n" for r in recs))
            return json.dumps({"transcript_path": str(p)})

        def user(text):
            return {"type": "user", "message": {"role": "user", "content": text}}

        def assistant(text):
            return {"type": "assistant",
                    "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}

        # ⛔ ONE TURN OF LATENCY IS THE OWNER'S BEHAVIOUR AND THIS PINS IT: the LIVE turn is never
        # judged, because its final assistant message is not flushed when a Stop hook fires.
        payload = transcript([user("go"), assistant("see #291")],
                             [user("again"), assistant("all qualified: backlog #291")])
        rc, _, found = judge(payload)
        case("the COMPLETED turn is judged, not the live one",
             ([t for t, _ in found], rc), (["#291"], 1))

        clean = transcript([user("go"), assistant("see backlog #291")],
                           [user("again"), assistant("x")])
        case("a turn that qualified everything is QUIET", judge(clean)[0], 0)

        single = transcript([user("go"), assistant("see #291")])
        case("a session with only a live turn has NO SUBJECT, which is quiet not CANNOT RUN",
             judge(single)[0], 0)

    # ── main() is DRIVEN, not just its predicates — ADR-0014 ──
    import io
    with tempfile.TemporaryDirectory() as mtd, tempfile.TemporaryDirectory() as mtd2:
        # ⛔ `td` and `second` are VARIED across these call sites deliberately. With one value each
        # no case can tell either parameter from a constant, so any clause reading them is
        # unguarded — `check-fixture-variation` caught exactly that here, and the fix is two real
        # inputs rather than an exemption.
        mlog = pathlib.Path(mtd) / "warn.log"
        case("main(--decide) on a payload with no transcript is CANNOT RUN",
             main(["--decide"], stdin=io.StringIO("{}"), log=mlog), 2)
        fire = transcript_for(mtd, "see #291", "x")
        case("main(--decide) on a firing turn returns 1 — a WARNING, never a block",
             main(["--decide"], stdin=io.StringIO(fire), log=mlog), 1)
        case("...and the firing is APPENDED to the log, which is the durable channel",
             mlog.exists() and "#291" in mlog.read_text(), True)
        # ⛔ COUNT LINES, NOT TOKENS. The first version asserted `count("#291") == 1` and failed:
        # each logged record carries the token TWICE, once as `token` and once inside `line`. The
        # case was wrong, not the code — and a substring count over a JSON record is exactly the
        # weaker-than-the-contract probe this repository keeps paying for.
        # argv VARIED: the no-action branch is a real path (it prints help and refuses), and
        # driving it is what lets a case tell `argv` from a constant.
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            case("main() with no action refuses rather than doing something by default",
                 main([], stdin=io.StringIO(""), log=mlog), 2)
        before_lines = len(mlog.read_text().splitlines())
        quiet = transcript_for(mtd2, "see backlog #291", "nothing bare here")
        mlog2 = pathlib.Path(mtd2) / "other.log"
        rc_quiet = main(["--decide"], stdin=io.StringIO(quiet), log=mlog2)
        case("a quiet turn returns 0 and APPENDS NOTHING to EITHER log",
             (rc_quiet, len(mlog.read_text().splitlines()), mlog2.exists()),
             (0, before_lines, False))

    print(f"{cases - failed}/{cases} passed")
    return 1 if failed else 0


def main(argv: list[str], *, stdin=None, log: pathlib.Path | None = None) -> int:
    """⛔ ITS WORLD IS A SET OF DEFAULTED PARAMETERS, per ADR-0014, so a case can DRIVE it.
    The assembly — which rc reaches the hook, and whether a firing is logged — is exactly where a
    warning could silently become a block, and that is the part a predicate test cannot reach."""
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--decide", action="store_true",
                    help="read a Stop-hook JSON payload on stdin and report (never blocks)")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.decide:
        return run_decide((stdin or sys.stdin).read(), log=log)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
