#!/usr/bin/env python3
"""Serve ~/explainers over localhost so an explainer can talk back to the session.

WHY THIS EXISTS
---------------
`/explain-diff` writes a self-contained HTML file and opens it with `file://`. That is the most
isolated context a browser has, and it cost two things, both measured on 2026-08-12/13:

  1. NO CHANNEL. A `file://` page cannot reach the session. The first attempt at a "Send" button
     downloaded a Markdown file instead — and `~/Downloads` turns out to be blocked from this agent
     by macOS privacy protection (`Operation not permitted`), so the questions landed somewhere
     unreadable. The channel was built by assuming both halves and verifying only the first.

  2. NO VERIFICATION. Chrome's automation refuses `file://` URLs, so the page could not be driven,
     clicked, or read. FOUR rounds of defects shipped in the question tray — no send affordance, a
     button squeezed to a sliver by a flex row, an Enter handler referencing a variable declared
     below it, and the dead download channel — and every one was found by the reader, because the
     author could not execute the page.

Over `http://127.0.0.1` both problems dissolve. The page can POST; the browser automation can drive
it. Nothing about the HTML changes: it stays a self-contained artifact that still works from
`file://` in five years, and its Send button falls back to the clipboard when nothing is listening.
Progressive enhancement, not a dependency.

THE ONE-CLICK URL
-----------------
    http://127.0.0.1:7391/latest

Redirects to the most recently modified explainer. Bookmark it once; it always points at the newest
one, so no filename ever has to be copied again. `/` lists them all, newest first.

SECURITY, DELIBERATE AND NARROW
-------------------------------
An explainer quotes private source and internal reasoning, so:

  * binds 127.0.0.1 ONLY — never 0.0.0.0, so nothing off this machine can reach it;
  * serves ~/explainers and nothing else — every resolved path is re-checked to be inside it, so
    `..` traversal cannot escape even if the URL parser is fooled;
  * serves only .html/.md/.css/.js/.svg/.png;
  * caps a POSTed question body, and appends it as data — never executes or renders it.

USAGE
-----
    python3 scripts/explainer-serve.py            # start (no-op if already running)
    python3 scripts/explainer-serve.py --status
    python3 scripts/explainer-serve.py --stop
    python3 scripts/explainer-serve.py --self-test   # 20 cases, binds no port

NOT a ratchet, and deliberately not claiming to be. An earlier draft of this docstring said it was
"a ratchet in the sense scripts/check-ratchet-contract.py means" — which was FALSE: that script
discovers by globbing `scripts/check-*.py`, so this file is never even read, and the claim went
unchecked for the same reason every other claim about a neighbour's behaviour has tonight. It is a
tool, not a gate; it keeps the two contract rules (a --self-test exists, no `except` returns 0)
because they are good practice, not because anything enforces them here.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import http.server
import json
import os
import pathlib
import signal
import socket
import sys
import urllib.parse
from typing import Callable

PORT = 7391
HOST = "127.0.0.1"
ROOT = pathlib.Path.home() / "explainers"
PIDFILE = ROOT / ".serve.pid"
QUESTIONS = ROOT / "questions.md"
MAX_BODY = 64 * 1024
SERVABLE = {".html", ".md", ".css", ".js", ".svg", ".png"}


# ── pure helpers, all covered by --self-test ─────────────────────────────────────────────────────

def safe_path(url_path: str, root: pathlib.Path) -> pathlib.Path | None:
    """Resolve a URL path inside `root`, or None if it escapes or is not a servable type.

    Checked AFTER resolution, not before: a prefix test on the raw string is defeated by `..`,
    symlinks and percent-encoding, all of which resolve() collapses first."""
    raw = urllib.parse.unquote(url_path.split("?", 1)[0].split("#", 1)[0]).lstrip("/")
    if not raw:
        return None
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None                      # escaped the root
    if candidate.suffix.lower() not in SERVABLE:
        return None
    return candidate


def explainers(root: pathlib.Path) -> list[pathlib.Path]:
    """Explainer pages, newest first by mtime."""
    if not root.is_dir():
        return []
    return sorted((p for p in root.glob("*.html") if p.is_file()),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def latest_target(root: pathlib.Path) -> str | None:
    """The URL path /latest should redirect to, or None when there is nothing to serve."""
    found = explainers(root)
    return "/" + urllib.parse.quote(found[0].name) if found else None


def index_html(root: pathlib.Path) -> str:
    rows = []
    for p in explainers(root):
        when = _dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        rows.append(f'<li><a href="/{urllib.parse.quote(p.name)}">{p.name}</a>'
                    f'<span> · {when}</span></li>')
    body = "\n".join(rows) or "<li><em>No explainers yet.</em></li>"
    return (
        "<!doctype html><meta charset=utf-8><title>Explainers</title>"
        "<style>body{font:16px/1.6 ui-sans-serif,system-ui,sans-serif;max-width:52rem;"
        "margin:3rem auto;padding:0 1rem;background:#fcfbf9;color:#191817}"
        "@media(prefers-color-scheme:dark){body{background:#131318;color:#eceaf2}a{color:#e8a860}}"
        "h1{font-size:1.4rem}li{margin:.4rem 0}span{color:#8a8496;font-size:.85rem}"
        "code{background:#0001;padding:.1em .35em;border-radius:4px}</style>"
        "<h1>Explainers</h1><p>Newest first. <code>/latest</code> always redirects to the top one — "
        "bookmark that.</p><ul>" + body + "</ul>"
    )


def _raises(fn, exc: type[BaseException]) -> bool:
    """True when `fn()` raises `exc`. Used by the self-test to assert a REFUSAL — asserting that
    something fails is the only way to prove a guard is not vacuous."""
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


def question_text(payload: dict) -> str | None:
    """The question itself, or None when the payload carries none.

    FAIL LOUD, ADDED 2026-08-17. This used to substitute "(empty)" and return 200, on the reasoning
    that recording an empty question beats dropping one. The instinct was right; the implementation
    told the SENDER it had succeeded.

    Measured that day: a POST with the keys `question`/`section` instead of `doc`/`text` returned
    `{"ok": true}` and appended a block reading "(empty)". The caller had no way to learn its words
    were gone. If the tray's JS ever drifts on a key name — a rename, a refactor, a hand-written
    client — every question vanishes while the UI says "✓ Sent".

    That is the shape CLAUDE.md files hardest against: *"cannot run" is a FAILURE, never a pass* —
    here, in the one channel whose entire job is carrying the user's words back.

    Rejecting loses nothing: the tray only clears its textarea on a 2xx (`if (!r.ok) throw`), so on
    a 400 the question stays on screen with an error beside it. The user keeps their text AND
    learns. That is strictly better than a silent "(empty)" in a file nobody re-reads."""
    text = payload.get("text")
    if not isinstance(text, str):
        return None
    text = text.strip()
    return text or None


def format_question_entry(payload: dict, now: str) -> str:
    """A POSTed question, as the Markdown block appended to questions.md.

    The payload is DATA. Nothing in it is executed, and it is written under a heading that records
    when and from which page it arrived, so a later reader can tell questions apart.

    Assumes `question_text(payload)` already returned non-None; raises if not, so a future caller
    cannot reintroduce the silent "(empty)" by skipping the check."""
    text = question_text(payload)
    if text is None:
        raise ValueError("refusing to format a question with no text")
    doc = str(payload.get("doc") or "(unknown explainer)")
    return f"\n---\n\n## {now} — {doc}\n\n{text}\n"


def read_pid(pidfile: pathlib.Path) -> int | None:
    try:
        return int(pidfile.read_text().strip())
    except (OSError, ValueError):
        return None


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def port_busy(host: str, port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def revision(p: pathlib.Path) -> str:
    """A cheap identity for a file's CONTENT, for change detection. mtime alone is not enough —
    a rewrite within the same clock tick would look unchanged — so size is included."""
    st = p.stat()
    return f"{st.st_mtime_ns}:{st.st_size}"


# The live-reload client. INJECTED BY THE SERVER at send time, never written into the page.
#
# WHY INJECTED RATHER THAN AUTHORED INTO THE HTML. The question tray is lifted verbatim from one
# explainer into the next by scripts/brief-compose.py. Putting this there would reach only pages
# generated AFTERWARDS, and would re-enter the hand-copied-code failure this project measured on
# 2026-08-17 (45 of 97 review findings were identifiers and counts that did not survive a copy).
# The server already reads and sends the bytes, so it can add this at send time: every page gets
# it, including the ones already on disk, and brief-compose.py does not change at all.
#
# It is also why `file://` still behaves exactly as before — nothing injects there. The file stays
# a self-contained artifact that works in five years; live reload is a property of being SERVED.
RELOAD_JS = """
<script>
(function () {
  var here = location.pathname, mine = null, KEY = 'explainer-scroll:' + here;
  // Restore the reading position saved just before the last auto-reload.
  try {
    var y = sessionStorage.getItem(KEY);
    if (y !== null) { sessionStorage.removeItem(KEY); window.scrollTo(0, parseInt(y, 10) || 0); }
  } catch (e) {}
  function busyTyping() {
    // NEVER reload out from under a half-typed question. The tray's textarea is #qbox; if it holds
    // text or has focus, the reader is mid-thought and a reload would silently eat it.
    var box = document.getElementById('qbox');
    if (!box) return false;
    return document.activeElement === box || (box.value || '').trim().length > 0;
  }
  function poll() {
    fetch('/_rev?p=' + encodeURIComponent(here), { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (rev) {
        if (rev === null) return;                 // page gone or not servable — stay put
        if (mine === null) { mine = rev; return; }  // first sample establishes the baseline
        if (rev === mine || busyTyping()) return;
        try { sessionStorage.setItem(KEY, String(window.scrollY)); } catch (e) {}
        location.reload();
      })
      .catch(function () {});                     // server stopped: keep showing the page, keep trying
  }
  setInterval(poll, 2000);
  poll();
})();
</script>
"""


# ── the server ───────────────────────────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "explainer-serve"

    def log_message(self, format: str, *args):  # noqa: A002 — name fixed by the base class
        sys.stderr.write("  %s\n" % (format % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # The page is same-origin with this server, so no CORS header is needed — and its absence
        # is what stops any OTHER site in the browser from reading private source through it.
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/":
            return self._send(200, index_html(ROOT).encode(), "text/html; charset=utf-8")
        if path == "/latest":
            target = latest_target(ROOT)
            if not target:
                return self._send(404, b"no explainers yet", "text/plain; charset=utf-8")
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return
        if path == "/_rev":
            # Change detection for the injected live-reload client. Goes through safe_path, so it
            # can only ever report on a file this server would already serve — it is not a stat()
            # oracle for the filesystem.
            qs = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            target = safe_path((qs.get("p") or [""])[0], ROOT)
            if target is None or not target.is_file():
                return self._send(404, b"no such page", "text/plain; charset=utf-8")
            return self._send(200, revision(target).encode(), "text/plain; charset=utf-8")
        resolved = safe_path(path, ROOT)
        if resolved is None or not resolved.is_file():
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        ctype = {".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8",
                 ".css": "text/css", ".js": "text/javascript",
                 ".svg": "image/svg+xml", ".png": "image/png"}[resolved.suffix.lower()]
        body = resolved.read_bytes()
        if resolved.suffix.lower() == ".html":
            body += RELOAD_JS.encode()   # appended, so a page that lacks </body> still gets it
        return self._send(200, body, ctype)

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/questions":
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._send(400, b"bad length", "text/plain; charset=utf-8")
        if length <= 0 or length > MAX_BODY:
            return self._send(413, b"body too large or empty", "text/plain; charset=utf-8")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return self._send(400, b"expected a JSON object", "text/plain; charset=utf-8")
        # Reject rather than record "(empty)" — see question_text(). The 400 body names the key,
        # because the measured failure was a caller sending the RIGHT question under the WRONG name.
        if question_text(payload) is None:
            got = ", ".join(sorted(str(k) for k in payload)) or "(no keys)"
            body = (f'expected a non-empty "text" field; got: {got}. '
                    'Nothing was recorded — resend with {"doc": "<page>", "text": "<question>"}.')
            return self._send(400, body.encode("utf-8"), "text/plain; charset=utf-8")
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ROOT.mkdir(parents=True, exist_ok=True)
        with QUESTIONS.open("a", encoding="utf-8") as fh:
            fh.write(format_question_entry(payload, now))
        return self._send(200, json.dumps({"ok": True, "file": str(QUESTIONS)}).encode(),
                          "application/json")


def start() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    if port_busy(HOST, PORT):
        pid = read_pid(PIDFILE)
        print(f"already serving on http://{HOST}:{PORT}" + (f" (pid {pid})" if pid else ""))
        print(f"  one-click:  http://{HOST}:{PORT}/latest")
        return 0
    pid = os.fork()
    if pid > 0:
        PIDFILE.write_text(str(pid))
        for _ in range(20):
            if port_busy(HOST, PORT):
                break
            import time
            time.sleep(0.1)
        if not port_busy(HOST, PORT):
            print(f"FAIL: forked pid {pid} but nothing is listening on {HOST}:{PORT}. NOT RUNNING.")
            return 1
        print(f"serving {ROOT} on http://{HOST}:{PORT}  (pid {pid})")
        print(f"  one-click:  http://{HOST}:{PORT}/latest")
        print(f"  questions:  {QUESTIONS}")
        return 0
    os.setsid()
    with http.server.ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()
    return 0


def stop() -> int:
    pid = read_pid(PIDFILE)
    if not pid_alive(pid):
        PIDFILE.unlink(missing_ok=True)
        print("not running")
        return 0
    assert pid is not None
    os.kill(pid, signal.SIGTERM)
    PIDFILE.unlink(missing_ok=True)
    print(f"stopped pid {pid}")
    return 0


def status() -> int:
    running, pid = port_busy(HOST, PORT), read_pid(PIDFILE)
    n = len(explainers(ROOT))
    print(f"listening : {'yes' if running else 'NO'} on http://{HOST}:{PORT}")
    print(f"pidfile   : {pid if pid else '(none)'}"
          + ("" if pid_alive(pid) or not pid else "  ⚠ stale — that pid is gone"))
    print(f"explainers: {n} in {ROOT}")
    print(f"questions : {QUESTIONS}" + ("" if QUESTIONS.exists() else "  (none yet)"))
    return 0 if running else 1


# ── self-test ────────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    import tempfile
    ok = 0
    cases: list[tuple[str, Callable[[], object]]] = []

    def case(name, fn):
        cases.append((name, fn))

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "a.html").write_text("a")
        (root / "b.html").write_text("b")
        os.utime(root / "a.html", (1, 1))          # a is OLDER
        os.utime(root / "b.html", (9_000_000, 9_000_000))
        (root / "secret.env").write_text("nope")
        (root / "notes.md").write_text("ok")

        # path safety — the property that keeps private source private
        case("serves a plain html name", lambda: safe_path("/a.html", root) == (root / "a.html").resolve())
        case("serves an allowed .md", lambda: safe_path("/notes.md", root) is not None)
        case("refuses a non-servable extension", lambda: safe_path("/secret.env", root) is None)
        case("refuses traversal with ..", lambda: safe_path("/../../etc/passwd", root) is None)
        case("refuses ENCODED traversal", lambda: safe_path("/%2e%2e/%2e%2e/etc/passwd", root) is None)
        case("refuses an absolute-looking escape", lambda: safe_path("//etc/passwd", root) is None)
        case("refuses the bare root path", lambda: safe_path("/", root) is None)
        case("ignores a query string", lambda: safe_path("/a.html?x=1", root) is not None)
        case("ignores a fragment", lambda: safe_path("/a.html#s3", root) is not None)

        # newest-first, which is the whole point of /latest
        case("orders newest first", lambda: [p.name for p in explainers(root)] == ["b.html", "a.html"])
        case("/latest points at the newest", lambda: latest_target(root) == "/b.html")
        case("index lists both", lambda: "a.html" in index_html(root) and "b.html" in index_html(root))

        empty = root / "empty"
        empty.mkdir()
        case("/latest is None when there is nothing", lambda: latest_target(empty) is None)
        case("index says so when empty", lambda: "No explainers yet" in index_html(empty))
        case("explainers() on a missing dir returns []", lambda: explainers(root / "nope") == [])

        # question formatting — payload is data, and a missing field must not crash
        case("formats a question with its source",
             lambda: "## T — d.html" in format_question_entry({"doc": "d.html", "text": "q"}, "T"))
        # ⟲ REPLACED 2026-08-17. This case used to assert the opposite:
        #     case("an empty question is recorded, not dropped",
        #          lambda: "(empty)" in format_question_entry({"doc": "d"}, "T"))
        # It encoded a fail-open. "Recorded, not dropped" was the right instinct about the FILE and
        # the wrong answer for the CALLER, who got 200 either way. The tray keeps its textarea on a
        # non-2xx, so rejecting loses no text and gains a visible error.
        case("a payload with no text yields None",
             lambda: question_text({"doc": "d"}) is None)
        case("a whitespace-only question yields None",
             lambda: question_text({"doc": "d", "text": "   \n\t "}) is None)
        case("a non-string text yields None",
             lambda: question_text({"doc": "d", "text": 42}) is None)
        case("THE MEASURED BUG: right question, wrong key name, yields None",
             lambda: question_text({"question": "why?", "section": "s"}) is None)
        case("a real question survives, stripped",
             lambda: question_text({"text": "  why?  "}) == "why?")
        case("format_question_entry REFUSES an empty question",
             lambda: _raises(lambda: format_question_entry({"doc": "d"}, "T"), ValueError))
        # A case here grepped this file for the literal "(empty)" to prove the sentinel was gone.
        # It failed — on the docstring that EXPLAINS the sentinel's removal. A check whose subject
        # is "this string does not appear" cannot tell a live value from prose about it, so it
        # penalises documenting the very fix it guards. The behaviour is already pinned by the five
        # cases above, which test what the code DOES rather than what it says. Removed, not weakened.
        case("a missing doc is labelled, not crashed",
             lambda: "(unknown explainer)" in format_question_entry({"text": "q"}, "T"))

        # liveness helpers
        case("pid_alive(None) is False", lambda: pid_alive(None) is False)
        case("pid_alive on this process is True", lambda: pid_alive(os.getpid()) is True)

        # live reload — change detection, and the injected client.
        # ⚠ IN ITS OWN SUBDIRECTORY, NOT `root`. The first draft put rev.html straight in root and
        # broke "orders newest first", because explainers() globs root/*.html and the fixture became
        # a third page. An instrument must not perturb the fixtures its neighbours assert on — the
        # same lesson the mutation harness taught this repo when it rewrote tracked files.
        rev_dir = root / "revfix"
        rev_dir.mkdir()
        rev_file = rev_dir / "rev.html"
        rev_file.write_text("one")
        os.utime(rev_file, (5_000, 5_000))
        rev_before = revision(rev_file)
        case("revision is stable when nothing changes",
             lambda: revision(rev_file) == rev_before)

        def _rewrite_same_mtime_different_size():
            # THE REASON SIZE IS IN THE REVISION. A rewrite inside one clock tick has an identical
            # mtime; without size the page would never learn an answer had been posted.
            rev_file.write_text("one-plus-more")
            os.utime(rev_file, (5_000, 5_000))          # force the mtime back to identical
            return revision(rev_file) != rev_before
        case("revision changes on a same-mtime rewrite (size is load-bearing)",
             _rewrite_same_mtime_different_size)

        def _rewrite_later():
            rev_file.write_text("two")
            os.utime(rev_file, (9_999, 9_999))
            return revision(rev_file) != rev_before
        case("revision changes when the file is rewritten later", _rewrite_later)

        # The client is a STRING constant, so its guards can be asserted without a browser. These
        # are shape checks, not behaviour — the behaviour was driven in a real browser on 2026-08-18.
        case("reload client guards the half-typed question (#qbox)",
             lambda: "qbox" in RELOAD_JS and "busyTyping" in RELOAD_JS)
        case("reload client preserves scroll across the reload",
             lambda: "sessionStorage" in RELOAD_JS and "scrollY" in RELOAD_JS)
        case("reload client establishes a baseline before it can reload",
             lambda: "mine === null" in RELOAD_JS)
        case("reload client asks /_rev, the only endpoint added",
             lambda: "/_rev?p=" in RELOAD_JS)

        for name, fn in cases:
            try:
                result = fn()          # called EXACTLY once — a case may have side effects
                if result:
                    ok += 1
                else:
                    print(f"  FAIL: {name}")
            except Exception as exc:  # noqa: BLE001
                print(f"  FAIL: {name} — {type(exc).__name__}: {exc}")
    print(f"self-test: {ok}/{len(cases)} passed")
    return 0 if ok == len(cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.stop:
        return stop()
    if a.status:
        return status()
    return start()


if __name__ == "__main__":
    sys.exit(main())
