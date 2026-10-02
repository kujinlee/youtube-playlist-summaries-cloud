<!-- codex-review: model=gpt-5.5 -->

START HEAD: `1c13190a5ef50b79d6895167b398af247cd6ef63`  
END HEAD: `1c13190a5ef50b79d6895167b398af247cd6ef63`  
Working tree: clean.

**Thrash Determination**

I did **not** find the same wiring-class defect again in Round 2’s fold. The new driver now uses real `_send` with `BytesIO` on `wfile`, and the three severances Round 2 named now red through the intended cases: call-site decoration removed, body write removed, and `Content-Length` falsified.

**Finding**

Low / Structural — the 200-status assertion can be satisfied by a non-200 status line whose reason phrase contains `200`.

Premise: `scripts/explainer-serve.py:1749-1750` says:

```python
case("...under a 200, so the case cannot pass on an error response",
     lambda: _wire.startswith(b"HTTP/1.0 200") or b" 200 " in _wire.split(b"\r\n")[0])
```

Measurement: the second disjunct is true for a non-200 status line:

```text
b"HTTP/1.0 404 200 OK" -> True
b"HTTP/1.0 404 Not Found" -> False
```

I also mutated `_send` in a copy to `send_response(404, "200 OK")`; this specific status predicate did not catch the error-status shape. The suite still went red elsewhere because some older header-capture cases stub `send_response` with a one-arg lambda, so this is not a current surviving production mutation. The problem is narrower: the case’s own assertion does not prove the claim in its name.

Severity reasoning: Low because the main wire tests still catch the important Round 2 severances, and the full suite is not green under the direct mutation I tried. Structural because it is a test-oracle weakness in the fold’s new driver.

Fix: parse the status line exactly, e.g. split the first line and require field 2 to be `b"200"`; drop the reason-phrase substring check.

**Measurements**

`python3 scripts/explainer-serve.py --self-test`: `208/208 passed`.

`python3 scripts/check-plan-code.py --self-test`: `131/131 passed`.

Targeted `scripts/mutations/explainer-serve.json` sweep using the harness’s own `run_mutations`: control `208/208`, re-control `208/208`, `49` entries, `49` caught, `49` attributed, `0` survivors.

The three new/relevant severances in copies behaved as claimed: decoration call severed -> named wire case red; `wfile.write(body)` -> wire/body/length cases red; `Content-Length: 0` -> length case red.

`Content-Length` parser attacks: header-in-body, missing header, chunked-without-length, and missing delimiter all failed closed for the actual case set; I did not find a `-1 == -1` vacuous pass in the shipped driver.

Text/html count: `do_GET` has exactly three 200 `text/html` exits, only the static `.html` path is decorated; `_regenerate` emits JSON/plain text, not HTML. The corrected comment is true on that count.

`ROOT` restore: forced an exception after rebinding and before `do_GET`; `ROOT` restored to the original value.

Could Not Measure: I started the full repo `python3 scripts/check-plan-code.py --mutate .` and interrupted it at `394/1181`; I am not using that partial run as a pass. The subject-specific 49-entry sweep above completed.

NOT CONVERGED: 0 Blocking · 0 High · 0 Medium · 1 Low
