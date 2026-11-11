#!/usr/bin/env python3
"""ONE bounded reader for the untrusted input five guards read — data, or CANNOT RUN with a reason.

    python3 scripts/bounded_read.py --self-test  # 56 cases
    python3 scripts/bounded_read.py --stdin      # stdin to stdout, bounded; rc 2 = CANNOT RUN (the Stop hook's read)

⛔ WHY THIS EXISTS (PR #440 round 2, the redesign). Five guards read input they do not control — the Stop hook's
payload on stdin, the transcript it names, `gh`'s checks answer, a vendored SKILL.md — and each validated a
different subset of the ways that input can be bad. Every review round found the next way, one step beside the
case that looked: round 1 a NUL byte, a number, undecodable payload bytes; round 2 a 200,000-deep JSON array
(`RecursionError`, which no handler named), a FIFO as `transcript_path` (an unbounded blocking read that hung the
Stop hook), and an undecodable line in mid-transcript that round 1's own fold had made SKIPPABLE, so the hook
returned 0 over a corrupt record. A per-guard fold adds the next check and leaves the class open. So the reading
is done ONCE, here, and every public function below has a CLOSED set of outcomes:

    (value, "")      the input was read; `value` is what it says
    (None,  why)     CANNOT RUN; `why` names the step that failed — never an exception, never a hang

(`parse_json` is the one exception to the `None` rule, because `null` is valid JSON: its failure is `why != ""`.)

THE RULES, each owned here and nowhere else
-------------------------------------------
  * ONLY A REGULAR FILE IS READ, OR STDIN (r2 X4). A path is opened `O_NONBLOCK`, then `fstat`-ed ON THE
    DESCRIPTOR and refused unless `S_ISREG` — so a FIFO is refused without blocking, and nothing can be swapped
    between the check and the read. A directory, a device and a socket are refused the same way.
  * UNDER A BYTE BOUND. A file is read whole only up to `MAX_FILE` bytes (256 MiB). MEASURED 2026-10-30: the
    largest of 614 real transcripts under `~/.claude/projects/*/*.jsonl` was 100,443,912 bytes, a live session
    still growing, so the bound is 2.5x the largest real input and a transcript past it is CANNOT RUN — loud,
    never truncated into a different verdict. Stdin is bounded at `MAX_STDIN` (1 MiB; a Stop payload is a few
    hundred bytes) and in TIME by `STDIN_WAIT`, because `read()` on a pipe that never closes blocks forever.
    ⟳ PR #440 r3 C5: the registered Stop hook used to read its stdin with `INPUT=$(cat)` BEFORE any guard ran, so
    those bounds held for a guard's direct `--decide` and not on the hook path. The hook now reads it through
    `python3 scripts/bounded_read.py --stdin`, the same `read_stream`, and hands each guard the bytes it got.
  * EVERY EXCEPTION FROM A PARSE IS CANNOT RUN (r2 X2). The handler at each public function is `except
    Exception`, DELIBERATELY BROAD, and this module is the one place in the five guards it is allowed: the
    failures that escaped before (`RecursionError`, `ValueError` from a NUL byte, `TypeError` from a number,
    `UnicodeDecodeError`) were each one member missing from a hand-written union, and the next one would be
    `MemoryError`. A broad catch is fail-OPEN when it returns success; here it can only return CANNOT RUN.
    `KeyboardInterrupt` and `SystemExit` are not `Exception` and still propagate.
  * ONLY A TORN FINAL RECORD IS TOLERATED (r2 X1, reverting round 1's m2). A JSONL stream is split on `\n` alone
    — never `splitlines()`, which also breaks on U+2028, U+2029 and `\x85` inside JSON strings (measured over
    580 real transcripts, 16 files and 140 fragments, backlog #331(f)). A record that cannot be decoded or parsed
    is CANNOT RUN — EXCEPT the last one when no newline follows it, which is a write still in progress, not
    corruption, and is dropped. A record that parses to something other than an object is not a record: CANNOT
    RUN wherever it sits.

WHAT THIS MODULE DOES NOT DO, stated rather than implied: it does not decide what a record MEANS (the turn
rule, `check-banner-armed._turn_records`, keeps only records whose `message` is an object), and the three other
regular-file readers in this repo (`session-state._read_whole`, `compaction-state._open_regular` and its
`read_in`) predate it and are not migrated by PR #440 — they are the same rule in three more places.
"""
from __future__ import annotations

import io
import json
import os
import stat
import sys
from pathlib import Path

MAX_FILE = 256 * 1024 * 1024   # bytes; the measurement behind it is in the docstring
MAX_STDIN = 1024 * 1024        # bytes
STDIN_WAIT = 2.0               # seconds a payload may take to arrive and close
# The words every non-regular-file refusal carries, so a case can tell "refused as not regular" from "read as
# empty and refused for that" — under a dropped S_ISREG check both are rc 2 (PR #440 r3 C4).
NOT_REGULAR = "is not a regular file"


def _failed(step: str, exc: BaseException) -> str:
    text = str(exc)
    if len(text) > 160:
        text = text[:160] + "…"
    return f"{step} ({type(exc).__name__}: {text})" if text else f"{step} ({type(exc).__name__})"


# ── reading: a regular file, or stdin ───────────────────────────────────────────────────────────

def read_file(path: object, cap: int = MAX_FILE) -> tuple[bytes | None, str]:
    """-> (the whole file, "") for a REGULAR file of at most `cap` bytes, else (None, why)."""
    try:
        if isinstance(path, Path):
            path = str(path)
        if not isinstance(path, str) or not path:
            return None, f"the path is not a non-empty string ({type(path).__name__})"
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                return None, f"{path} {NOT_REGULAR} — NOT READ (a FIFO or a device would block, a directory has no bytes)"
            # ONE bound, enforced on the bytes actually read: a pre-check on `st_size` as well would be a second
            # copy that masks this one, and a live transcript can grow after the `fstat`.
            chunks, total = [], 0
            while True:
                block = os.read(fd, min(1 << 20, cap + 1 - total))
                if not block:
                    break
                chunks.append(block)
                total += len(block)
                if total > cap:
                    return None, f"{path} is over the {cap}-byte bound — NOT READ, never truncated"
            return b"".join(chunks), ""
        finally:
            os.close(fd)
    except Exception as exc:          # deliberate: see "EVERY EXCEPTION" in the module docstring
        return None, _failed(f"{path!r} could not be read", exc)


def read_text(path: object) -> tuple[str | None, str]:
    """-> (the file as STRICT UTF-8 text, "") or (None, why). `read_file`, then a decode that may not guess."""
    data, why = read_file(path)
    if data is None:
        return None, why
    try:
        return data.decode("utf-8"), ""
    except Exception as exc:          # deliberate: see "EVERY EXCEPTION" in the module docstring
        return None, _failed(f"{path} is not UTF-8", exc)


def read_stream(stream: object, wait: float | None = None, cap: int = MAX_STDIN) -> tuple[bytes | None, str]:
    """-> (everything on `stream` up to EOF, "") or (None, why). Bounded in bytes AND in time.

    Three ways there is nothing safely readable, each CANNOT RUN rather than a crash or a hang: `stream is None`
    (stdin CLOSED, `0<&-`), a TTY (reading would wait on a human), and a pipe that does not reach EOF within
    `wait` seconds (a harness holding stdin open; `read()` would block forever). A stream with no file
    descriptor — a `StringIO` in a case — cannot block, and is read directly under the same byte bound.
    """
    try:
        if stream is None:
            return None, "stdin is closed"
        if stream.isatty():
            return None, "stdin is a terminal, not a payload"
        try:
            fd = stream.fileno()
        except (OSError, ValueError, AttributeError, io.UnsupportedOperation):
            fd = None
        if fd is None:
            got = stream.read(cap + 1)
            data = got.encode("utf-8") if isinstance(got, str) else bytes(got)
            if len(data) > cap:
                return None, f"stdin carries more than the {cap}-byte bound — NOT READ"
            return data, ""
        import select
        import time
        deadline = time.monotonic() + (STDIN_WAIT if wait is None else wait)
        chunks: list[bytes] = []
        total = 0
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return None, f"stdin did not close within {STDIN_WAIT if wait is None else wait}s — NOT READ"
            ready, _, _ = select.select([fd], [], [], left)
            if not ready:
                return None, f"stdin did not close within {STDIN_WAIT if wait is None else wait}s — NOT READ"
            block = os.read(fd, 65536)
            if not block:
                return b"".join(chunks), ""          # EOF — the whole payload is in hand
            chunks.append(block)
            total += len(block)
            if total > cap:
                return None, f"stdin carries more than the {cap}-byte bound — NOT READ"
    except Exception as exc:          # deliberate: see "EVERY EXCEPTION" in the module docstring
        return None, _failed("stdin could not be read", exc)


# ── parsing: JSON, and JSON Lines ───────────────────────────────────────────────────────────────

def parse_json(data: bytes | str) -> tuple[object, str]:
    """-> (the value, "") or (None, why). ⚠ `null` parses to None, so the failure signal is `why`, never the value."""
    try:
        text = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
        if not isinstance(text, str):
            return None, f"the input is not text ({type(data).__name__})"
        return json.loads(text), ""
    except Exception as exc:          # deliberate: RecursionError, MemoryError, UnicodeDecodeError, ValueError
        return None, _failed("the input is not JSON", exc)


def parse_jsonl(data: bytes) -> tuple[list[dict] | None, str]:
    """-> (every record, each a JSON OBJECT, "") or (None, why). Only a torn FINAL record is dropped.

    "Torn" is exact: the last piece after `split(b"\\n")`, non-blank (so no newline follows it), whose bytes fail
    to DECODE or to PARSE. A final piece that parses to a non-object, or raises anything but a decode or parse
    error (a 200,000-deep array raises RecursionError), is not a write in progress and is CANNOT RUN.
    """
    try:
        pieces = bytes(data).split(b"\n")
        last = len(pieces) - 1
        records: list[dict] = []
        for i, piece in enumerate(pieces):
            if not piece.strip():
                continue
            try:
                obj = json.loads(piece.decode("utf-8"))
            except ValueError as exc:            # UnicodeDecodeError and JSONDecodeError are both ValueError
                if i == last:
                    break                         # a torn final record: the writer has not finished it
                return None, _failed(f"record {i + 1} of {last + 1} is not JSON, and it is not the last", exc)
            if not isinstance(obj, dict):
                return None, f"record {i + 1} of {last + 1} is a JSON {type(obj).__name__}, not an object"
            records.append(obj)
        return records, ""
    except Exception as exc:          # deliberate: see "EVERY EXCEPTION" in the module docstring
        return None, _failed("the records could not be parsed", exc)


# ── the Stop hook's payload and the transcript it names ────────────────────────────────────────

def stop_transcript(payload: bytes | str) -> tuple[dict, list[dict] | None, str]:
    """-> (payload object, the transcript's records, "") or (payload object or {}, None, why).

    The ONE read of a Stop payload for the three transcript guards. The payload must be a JSON OBJECT (empty is
    read as `{}`, which then names no transcript); `transcript_path` must be a non-empty string; the file is
    read by `read_file` and parsed by `parse_jsonl`; and a transcript with no record is CANNOT RUN, because a
    guard that reads nothing has not looked.
    """
    try:
        if isinstance(payload, (bytes, bytearray)):
            empty = not bytes(payload).strip()
        else:
            empty = not str(payload).strip()
        data, why = ({}, "") if empty else parse_json(payload)
        if why:
            return {}, None, f"the hook payload: {why}"
        if not isinstance(data, dict):
            return {}, None, f"the hook payload is JSON but not an object ({type(data).__name__})"
        path = data.get("transcript_path")
        if not isinstance(path, str) or not path:
            return data, None, "the hook payload names no transcript_path string"
        raw, why = read_file(path)
        if raw is None:
            return data, None, f"the transcript: {why}"
        records, why = parse_jsonl(raw)
        if records is None:
            return data, None, f"the transcript: {why}"
        if not records:
            return data, None, "no record in the transcript parses, so there is no turn to read"
        return data, records, ""
    except Exception as exc:          # deliberate: see "EVERY EXCEPTION" in the module docstring
        return {}, None, _failed("the hook payload could not be read", exc)


# ── the hostile inputs, ONE list for every guard's cases ───────────────────────────────────────

def hostile_payloads(d: Path) -> list[tuple[str, bytes]]:
    """SELF-TEST FIXTURE: every Stop payload a review round has found, as (name, bytes), its files made under `d`.

    Each must be CANNOT RUN at each transcript guard's REAL `--decide` — rc 2, no traceback, no hang. ONE list,
    so the next input a reviewer finds is added once and every guard's case is red until it is handled; three
    hand-kept copies is how round 1's inputs were tested in one guard and missed one step beside it.
    """
    def rec(kind: str, text: str, uuid: str = "") -> bytes:
        msg = {"role": kind, "content": text if kind == "user" else [{"type": "text", "text": text}]}
        return json.dumps({"type": kind, "uuid": uuid or kind, "message": msg}).encode()
    turn = [rec("user", "go", "u1"), rec("assistant", "see #291"), rec("user", "again", "u2"), rec("assistant", "x")]
    files = {
        # r2 X1: an undecodable record in mid-transcript (round 1's m2 had made it skippable; the hook returned 0)
        "undecodable.jsonl": turn[0] + b"\n\xff\n\xfe\n",
        # r2 X1: the JUDGED assistant record truncated, with a whole record after it (warn 1 -> 0 under m2)
        "truncated.jsonl": b"\n".join([turn[0], turn[1][:-3], turn[2], turn[3]]) + b"\n",
        # r1 m3 / backlog #331(e): one good record, then three that are not JSON
        "not-json.jsonl": turn[0] + b"\nnot json\nnot json\nnot json\n",
    }
    for name, data in files.items():
        (d / name).write_bytes(data)
    fifo = d / "hostile.fifo"
    if not fifo.exists():
        os.mkfifo(fifo)
    path = lambda p: json.dumps({"transcript_path": str(p), "session_id": "s"}).encode()
    return [
        ("r1 X1: a NUL byte in transcript_path", b'{"transcript_path": "x\\u0000y"}'),
        ("r1 X1: a number as transcript_path", b'{"transcript_path": 123}'),
        ("r1 m1: undecodable payload bytes", b'{"transcript_path": "/x\xff"}'),
        ("r1 M2: null", b"null"), ("r1 M2: true", b"true"), ("r1 M2: 1", b"1"), ('r1 M2: "s"', b'"s"'),
        ("#357(2): []", b"[]"),
        ("r2 X2: a 200,000-deep array", b"[" * 200000 + b"]" * 200000),
        ("r2 X4: a FIFO with no writer as transcript_path", path(fifo)),
        ("a directory as transcript_path", path(d)),
        # r3 C4: a DEVICE. Read without the S_ISREG check it is not empty, as a writer-less FIFO is: it is 256 MiB.
        ("r3 C4: /dev/zero, a device, as transcript_path", path("/dev/zero")),
        ("r2 X1: an undecodable record mid-transcript", path(d / "undecodable.jsonl")),
        ("r2 X1: the judged record truncated mid-transcript", path(d / "truncated.jsonl")),
        ("r1 m3: one good record then three non-JSON", path(d / "not-json.jsonl")),
    ]


# The hostile payloads whose refusal must NAME a non-regular file (r3 C4). Writer-less, a FIFO reads as EMPTY
# and a directory raises, so without the S_ISREG check each is still rc 2 — for a different reason.
NON_REGULAR = ("r2 X4: a FIFO with no writer as transcript_path", "a directory as transcript_path",
               "r3 C4: /dev/zero, a device, as transcript_path")


def non_regular_payloads(d: Path) -> list[tuple[str, bytes]]:
    """SELF-TEST FIXTURE: the members of `hostile_payloads` named in `NON_REGULAR` — the same list, filtered."""
    return [(n, b) for n, b in hostile_payloads(d) if n in NON_REGULAR]


def _spawn(argv: list[str], stdin: bytes, timeout: float):
    """-> the CompletedProcess, or None past `timeout`. PYTHONIOENCODING pins STRICT UTF-8 stdin: under the C
    locale Python reads stdin with surrogateescape, which would hide an undecodable payload on one machine and
    not another (r1 m1)."""
    import subprocess
    try:
        return subprocess.run([sys.executable, *argv], input=stdin, capture_output=True, timeout=timeout,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except subprocess.TimeoutExpired:
        return None


def run_cli(argv: list[str], stdin: bytes, timeout: float = 30) -> tuple[object, bool]:
    """SELF-TEST HELPER: run a guard's REAL entry point as the Stop hook does — raw stdin BYTES, a subprocess.
    -> (rc, printed a traceback?), or ("HUNG", False) past `timeout`, so a hang is a NAMED red, not a dead suite."""
    p = _spawn(argv, stdin, timeout)
    if p is None:
        return "HUNG", False
    return p.returncode, b"Traceback" in p.stderr


def run_cli_naming(argv: list[str], stdin: bytes, reason: str, timeout: float = 30) -> tuple[object, bool, bool]:
    """SELF-TEST HELPER: `run_cli`, and whether the output NAMES `reason` -> (rc, traceback?, named?), or
    ("HUNG", False, False). rc 2 alone cannot tell which refusal fired; this can (PR #440 r3 C4)."""
    p = _spawn(argv, stdin, timeout)
    if p is None:
        return "HUNG", False, False
    return p.returncode, b"Traceback" in p.stderr, reason.encode() in p.stdout + p.stderr


def main_stdin() -> int:
    """`--stdin`: copy THIS process's stdin to stdout, bounded by `read_stream` — rc 0 — or print CANNOT RUN and
    return 2 with nothing on stdout. The registered Stop hook's one read of its payload (PR #440 r3 C5)."""
    data, why = read_stream(sys.stdin)
    if data is None:
        print(f"CANNOT RUN — the Stop hook's stdin: {why}. Every guard after this gets an EMPTY payload, so each is "
              f"CANNOT RUN too. Treat this stop's checks as NOT RUN.", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    return 0


# ── --self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import subprocess
    import tempfile
    import threading

    cases: list[tuple[str, bool]] = []

    def case(name: str, got: object, want: object) -> None:
        cases.append((name, got == want))
        print(f"  ✓ {name}" if got == want else f"  [FAIL] {name}: got {got!r} want {want!r}")

    def outcome(fn, secs: float = 5.0) -> object:
        """Run `fn` on a daemon thread. A raise is a VALUE ("RAISED <type>") and a block past `secs` is "HUNG", so a
        mutant that crashes or hangs is a NAMED red case — never a dead suite the harness cannot attribute."""
        box: list = []
        def run() -> None:
            try:
                box.append(fn())
            except Exception as exc:                   # noqa: BLE001 — a crash is a named red, not a dead suite
                box.append(f"RAISED {type(exc).__name__}")
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(secs)
        return box[0] if box else "HUNG"

    def rc(result) -> str:
        """`(value, why)` -> "data" or "CANNOT RUN", so a case names the OUTCOME, not a message's wording."""
        return "CANNOT RUN" if result[-1] else "data"

    deep = b"[" * 200000 + b"]" * 200000

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        good = d / "good.jsonl"
        good.write_bytes(b'{"type": "user", "n": 1}\n{"type": "assistant", "n": 2}\n')
        n_good = len(good.read_bytes())
        fifo = d / "fifo"
        os.mkfifo(fifo)

        # ── read_file: only a regular file, under a bound ─────────────────────────────────────────
        case("read_file reads a regular file whole", outcome(lambda: read_file(good)), (good.read_bytes(), ""))
        case("read_file takes a Path as well as a str", outcome(lambda: read_file(Path(good))[1]), "")
        case("read_file: a missing file is CANNOT RUN", outcome(lambda: rc(read_file(str(d / "absent")))), "CANNOT RUN")
        case("read_file: a directory is CANNOT RUN", outcome(lambda: rc(read_file(str(d)))), "CANNOT RUN")
        # ⛔ r2 X4: a FIFO with NO WRITER. A blocking open or read waits forever.
        case("⭐ r2 X4: a FIFO with no writer is refused at once, never a blocking read",
             outcome(lambda: rc(read_file(str(fifo)))), "CANNOT RUN")
        case("read_file: a NUL byte in the path is CANNOT RUN, never ValueError",
             outcome(lambda: rc(read_file("x\x00y"))), "CANNOT RUN")
        case("read_file: a number as the path is CANNOT RUN, never TypeError", outcome(lambda: rc(read_file(123))), "CANNOT RUN")
        case("read_file: an empty path is CANNOT RUN", outcome(lambda: rc(read_file(""))), "CANNOT RUN")
        case("⭐ read_file: a file of exactly `cap` bytes is read", outcome(lambda: read_file(good, cap=n_good)[1]), "")
        case("⭐ read_file: one byte over `cap` is CANNOT RUN, never truncated",
             outcome(lambda: read_file(good, cap=n_good - 1)[0]), None)
        case("the file bound is 256 MiB, 2.5x the largest real transcript measured", MAX_FILE, 268435456)
        denied = d / "denied"
        denied.write_bytes(b"x")
        denied.chmod(0)
        try:
            readable_anyway = os.access(denied, os.R_OK)      # root reads a mode-0 file; the case says so
            case("read_file: a permission-denied file is CANNOT RUN (root: read)",
                 outcome(lambda: rc(read_file(denied))), "data" if readable_anyway else "CANNOT RUN")
        finally:
            denied.chmod(0o600)

        # ── read_text: strict UTF-8 ───────────────────────────────────────────────────────────────
        utf = d / "skill.md"
        utf.write_bytes("names .remember/remember.md — ok\n".encode("utf-8"))
        case("read_text decodes UTF-8", outcome(lambda: read_text(utf)), ("names .remember/remember.md — ok\n", ""))
        bad = d / "bad.md"
        bad.write_bytes(b"ok\xff\n")
        case("read_text: an undecodable byte is CANNOT RUN, never a guess", outcome(lambda: rc(read_text(bad))), "CANNOT RUN")
        case("read_text: a FIFO is CANNOT RUN through it too", outcome(lambda: rc(read_text(fifo))), "CANNOT RUN")

        # ── parse_json: every exception is CANNOT RUN ─────────────────────────────────────────────
        case("parse_json reads an object", outcome(lambda: parse_json(b'{"a": 1}')), ({"a": 1}, ""))
        case("parse_json reads `null` as None with NO failure — the signal is `why`", outcome(lambda: parse_json("null")),
             (None, ""))
        case("⭐ r2 X2: a 200,000-deep array is CANNOT RUN, never RecursionError",
             outcome(lambda: rc(parse_json(deep))), "CANNOT RUN")
        case("parse_json: bad JSON is CANNOT RUN", outcome(lambda: rc(parse_json("{not json"))), "CANNOT RUN")
        case("parse_json: undecodable bytes are CANNOT RUN", outcome(lambda: rc(parse_json(b'{"a": "\xff"}'))), "CANNOT RUN")
        case("parse_json: a non-text input is CANNOT RUN", outcome(lambda: rc(parse_json(5))), "CANNOT RUN")

        # ── parse_jsonl: only a torn FINAL record is tolerated ────────────────────────────────────
        case("parse_jsonl reads every record", outcome(lambda: parse_jsonl(good.read_bytes())),
             ([{"type": "user", "n": 1}, {"type": "assistant", "n": 2}], ""))
        case("⭐ r2 X1: an undecodable record in the MIDDLE is CANNOT RUN, never skipped",
             outcome(lambda: rc(parse_jsonl(b'{"a": 1}\n\xff\n\xfe\n'))), "CANNOT RUN")
        case("⭐ r2 X1: a non-JSON record in the middle is CANNOT RUN (backlog #331(e))",
             outcome(lambda: rc(parse_jsonl(b'{"a": 1}\nnot json\n{"b": 2}\n'))), "CANNOT RUN")
        case("...and an undecodable LAST record that a newline FOLLOWS is complete, so it is corrupt: CANNOT RUN",
             outcome(lambda: rc(parse_jsonl(b'{"a": 1}\n{"b": "x\xff"}\n'))), "CANNOT RUN")
        case("⭐ a torn FINAL record cut mid-character is dropped, its predecessors kept",
             outcome(lambda: parse_jsonl(b'{"a": 1}\n{"b": "ab\xe2\x9b')), ([{"a": 1}], ""))
        case("⭐ a torn FINAL record cut on ASCII is dropped too — one class, one verdict (r1 m2)",
             outcome(lambda: parse_jsonl(b'{"a": 1}\n{"b": "ab')), ([{"a": 1}], ""))
        case("a final record that PARSES to a non-object is not torn: CANNOT RUN",
             outcome(lambda: rc(parse_jsonl(b'{"a": 1}\n5'))), "CANNOT RUN")
        case("a record that is a JSON number, mid-stream, is CANNOT RUN",
             outcome(lambda: rc(parse_jsonl(b'5\n{"a": 1}\n'))), "CANNOT RUN")
        case("⭐ a deep final record raises RecursionError, which is not a torn write: CANNOT RUN",
             outcome(lambda: rc(parse_jsonl(b'{"a": 1}\n' + deep))), "CANNOT RUN")
        case("⭐ records split on \\n ALONE — a U+2028 inside a string keeps its record whole (backlog #331(f))",
             outcome(lambda: parse_jsonl('{"t": "a\u2028b"}\n{"t": "c\x85d"}\n'.encode("utf-8"))),
             ([{"t": "a\u2028b"}, {"t": "c\x85d"}], ""))
        case("blank lines between records are not records, and not corruption",
             outcome(lambda: parse_jsonl(b'{"a": 1}\n\n  \n{"b": 2}\n')), ([{"a": 1}, {"b": 2}], ""))

        # ── stop_transcript: the payload, then the file ───────────────────────────────────────────
        p = json.dumps({"transcript_path": str(good), "session_id": "s"})
        case("stop_transcript returns the payload object and the records", outcome(lambda: stop_transcript(p)[0:2]),
             ({"transcript_path": str(good), "session_id": "s"}, [{"type": "user", "n": 1}, {"type": "assistant", "n": 2}]))
        hostile = hostile_payloads(d) + [("bad JSON", b"{not json"), ("empty", b""), ("no path", b'{"session_id": "s"}')]
        case("⭐ every r1/r2 payload — NUL, number, bad bytes, non-objects, deep, FIFO, directory, corrupt records — "
             "is CANNOT RUN", outcome(lambda: [(n, rc(stop_transcript(b))) for n, b in hostile], 30),
             [(n, "CANNOT RUN") for n, _ in hostile])
        empty = d / "empty.jsonl"
        empty.write_bytes(b"\n")
        case("⭐ a transcript with NO record is CANNOT RUN — nothing read is not quiet (backlog #331(a))",
             outcome(lambda: rc(stop_transcript(json.dumps({"transcript_path": str(empty)})))), "CANNOT RUN")
        corrupt = d / "corrupt.jsonl"
        corrupt.write_bytes(b'{"a": 1}\nnot json\n{"b": 2}\n')
        case("the payload object survives a failed transcript read — missing, corrupt or empty — so the session id is "
             "not lost", outcome(lambda: [stop_transcript(json.dumps({"transcript_path": str(t), "session_id": "s"}))[0]
                                          .get("session_id") for t in (d / "absent", corrupt, empty)]), ["s"] * 3)
        # ⚠ The OUTCOME of a non-object payload is CANNOT RUN even without the type check — `None.get` raises into
        # the boundary's broad catch. So the check is held by its MESSAGE: the reader names the step that failed.
        case("a non-object payload is refused BY NAME, at two distinct types — not by the broad catch's fallback",
             outcome(lambda: [stop_transcript(b)[2] for b in (b"null", b"5")]),
             ["the hook payload is JSON but not an object (NoneType)", "the hook payload is JSON but not an object (int)"])
        # ⛔ r3 C4: rc 2 alone passed for an AMBIENT reason — with the S_ISREG check dropped, a writer-less FIFO
        # reads as empty ("no record") and a directory raises, both still CANNOT RUN. So the reason is asserted.
        case("⭐ r3 C4: each non-regular transcript_path — a FIFO, a directory, /dev/zero — is refused AS not "
             "regular, never read and refused for something else",
             outcome(lambda: [(n, NOT_REGULAR in stop_transcript(b)[2]) for n, b in non_regular_payloads(d)], 30),
             [(n, True) for n in NON_REGULAR])

        # ── read_stream: bytes AND time ───────────────────────────────────────────────────────────
        class _Tty:
            def isatty(self):
                return True
            def read(self, n=-1):
                return '{"session_id": "typed"}'
        case("read_stream: a closed stdin is CANNOT RUN", outcome(lambda: rc(read_stream(None))), "CANNOT RUN")
        case("read_stream: a TERMINAL is CANNOT RUN — reading would wait on a human", outcome(lambda: rc(read_stream(_Tty()))),
             "CANNOT RUN")
        case("read_stream: a StringIO is read directly", outcome(lambda: read_stream(io.StringIO('{"a": 1}'))), (b'{"a": 1}', ""))
        case("read_stream: a stream with no descriptor over the byte bound is CANNOT RUN",
             outcome(lambda: rc(read_stream(io.BytesIO(b"x" * 11), cap=10))), "CANNOT RUN")

        def _pipe(data: bytes, close: bool, wait: float, cap: int = MAX_STDIN):
            r, w = os.pipe()
            try:
                os.write(w, data)
                if close:
                    os.close(w)
                with os.fdopen(r, "rb") as fh:
                    return read_stream(fh, wait=wait, cap=cap)
            finally:
                if not close:
                    os.close(w)
        case("read_stream: a pipe that closes is read to EOF",
             outcome(lambda: _pipe(b'{"session_id": "s"}', True, 5.0)), (b'{"session_id": "s"}', ""))
        case("read_stream: a PIPE over the byte bound is CANNOT RUN", outcome(lambda: rc(_pipe(b"x" * 11, True, 2.0, cap=10))),
             "CANNOT RUN")
        case("⭐ read_stream: a pipe that NEVER closes is CANNOT RUN after `wait`, never a hang",
             outcome(lambda: rc(_pipe(b"", False, 0.2))), "CANNOT RUN")
        # ⛔ r3 C3: the bound's VALUES and its exact-cap edge were unpinned — three mutants survived every suite.
        case("⭐ r3 C3: the stdin bound is 1 MiB", MAX_STDIN, 1048576)
        case("⭐ r3 C3: the stdin wait is 2 s", STDIN_WAIT, 2.0)
        case("⭐ r3 C3: read_stream: a PIPE of exactly `cap` bytes is read",
             outcome(lambda: _pipe(b"x" * 10, True, 2.0, cap=10)), (b"x" * 10, ""))
        case("⭐ r3 C3: read_stream: a descriptor-less stream of exactly `cap` bytes is read",
             outcome(lambda: read_stream(io.BytesIO(b"x" * 10), cap=10)), (b"x" * 10, ""))

        def _late(data: bytes, after: float):
            """A pipe whose writer sends `data` and closes `after` seconds in, read under the DEFAULT wait."""
            r, w = os.pipe()
            def send() -> None:
                import time
                time.sleep(after)
                os.write(w, data)
                os.close(w)
            threading.Thread(target=send, daemon=True).start()
            with os.fdopen(r, "rb") as fh:
                return read_stream(fh)
        case("⭐ r3 C3: a payload that arrives 0.5 s late is read under the DEFAULT wait",
             outcome(lambda: _late(b'{"a": 1}', 0.5)), (b'{"a": 1}', ""))
        # Through a real process, as a hook runs it: stdin held open by the parent.
        child = subprocess.Popen([sys.executable, "-c",
                                  "import sys; sys.path.insert(0, sys.argv[1]); import bounded_read as b; "
                                  "print(b.read_stream(sys.stdin, wait=0.2)[1] != '')", str(Path(__file__).resolve().parent)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            child.wait(timeout=30)            # stdin is still OPEN here: nothing has written or closed it
            said = child.stdout.read().strip()
        except subprocess.TimeoutExpired:
            child.kill()
            said = "HUNG"
        finally:
            child.stdin.close()
            child.stdout.close()
        case("read_stream in a child whose stdin pipe is EMPTY and OPEN refuses rather than hanging", said, "True")

        # ── --stdin, and the registered Stop hook that reads its payload through it (r3 C5) ──────────
        me = [str(Path(__file__).resolve()), "--stdin"]
        payload = b'{"transcript_path": "/t.jsonl", "session_id": "s", "x": "\\u00e9"}'
        got = _spawn(me, payload, 30)
        case("--stdin copies a closed payload to stdout byte for byte, rc 0",
             None if got is None else (got.returncode, got.stdout), (0, payload))
        got = _spawn(me, b"x" * (MAX_STDIN + 1), 30)
        case("--stdin: a payload over MAX_STDIN is rc 2, NOTHING on stdout, CANNOT RUN on stderr",
             None if got is None else (got.returncode, got.stdout, b"CANNOT RUN" in got.stderr), (2, b"", True))

        # The REAL hook file, in a fake checkout whose five scripts are stubs that record the stdin they get, so
        # nothing is written into this checkout's `.claude/`. Its subject is the hook's OWN read, before any guard.
        root = Path(__file__).resolve().parent.parent
        hook = root / ".claude" / "hooks" / "block-idle-stop.sh"
        if not hook.exists():
            case("the hook cases NOT CHECKED — no .claude/ in this tree (a real checkout missing the hook FAILS here)",
                 (root / ".claude").exists(), False)
        else:
            fake = d / "checkout"
            (fake / ".claude" / "hooks").mkdir(parents=True)
            (fake / "scripts").mkdir()
            (fake / ".claude" / "hooks" / hook.name).write_bytes(hook.read_bytes())
            (fake / "scripts" / "bounded_read.py").write_bytes(Path(__file__).resolve().read_bytes())
            readers = ("check-banner-armed.py", "check-transcript-references.py", "check-closing-table.py",
                       "check-ci-watched.py")
            for name in readers:
                (fake / "scripts" / name).write_text(
                    "import sys\nopen(__file__ + '.in', 'wb').write(sys.stdin.buffer.read())\n")
            (fake / "scripts" / "check-plan-progress.py").write_text("import sys\nsys.exit(0)\n")

            def through_hook(data: bytes, close: bool, secs: float = 15.0):
                """-> (rc, stderr) of the hook with `data` on stdin, held OPEN unless `close`; "HUNG" past `secs`."""
                for name in readers:
                    (fake / "scripts" / (name + ".in")).unlink(missing_ok=True)
                h = subprocess.Popen(["bash", str(fake / ".claude" / "hooks" / hook.name)], cwd=fake,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    if close:
                        _, err = h.communicate(data, timeout=secs)
                    else:
                        h.stdin.write(data)
                        h.stdin.flush()
                        h.wait(timeout=secs)          # stdin still OPEN: nothing has closed it
                        err = h.stderr.read()
                    return h.returncode, err
                except subprocess.TimeoutExpired:
                    h.kill()
                    h.wait()
                    return "HUNG"
                finally:
                    for f in (h.stdin, h.stdout, h.stderr):
                        if f and not f.closed:
                            f.close()
            def seen() -> list:
                """What each stub guard was handed on stdin; None for one that never ran."""
                return [(fake / "scripts" / (n + ".in")).read_bytes() if (fake / "scripts" / (n + ".in")).exists()
                        else None for n in readers]
            got = through_hook(payload, True)
            case("the REAL hook hands every guard the payload byte for byte when stdin closes, and exits 0",
                 got if got == "HUNG" else (got[0], seen()),
                 (0, [payload] * len(readers)))
            got = through_hook(payload, False)
            case("⭐ r3 C5: the REAL hook with stdin held OPEN finishes on the bound — CANNOT RUN, exit 1 — never "
                 "the unbounded `$(cat)` that waited for the pipe to close",
                 got if got == "HUNG" else (got[0], b"did not close" in got[1],
                                            seen()),
                 (1, True, [b""] * len(readers)))
            got = through_hook(b"x" * (MAX_STDIN + 1), True)
            case("⭐ r3 C5: the REAL hook refuses a payload over MAX_STDIN — exit 1, the bound named — and passes "
                 "nothing on", got if got == "HUNG" else (got[0], b"byte bound" in got[1],
                                                          seen()),
                 (1, True, [b""] * len(readers)))

    failed = sum(1 for _, ok in cases if not ok)
    print(f"\n{len(cases) - failed}/{len(cases)} self-test cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        sys.exit(_self_test())
    if sys.argv[1:] == ["--stdin"]:
        sys.exit(main_stdin())
    print(__doc__.split("\n\n")[0], file=sys.stderr)
    sys.exit(2)
