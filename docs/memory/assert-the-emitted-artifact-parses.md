---
name: assert-the-emitted-artifact-parses
description: "FIRES-WHEN: a generator emits code (JS/CSS/SQL/YAML) and the suite asserts what it CONTAINS — ⭐⭐ 201 cases were GREEN over syntactically invalid JavaScript; every control on every page was dead, and a browser reading '0 flips' looked like success. No substring assertion can see a missing brace. Parse the artifact"
metadata:
  node_type: memory
  type: feedback
---

**Measured 2026-10-19, `scripts/page_chrome.py`.** A rewrite of the pin block dropped **one
closing brace**. `chrome_script()` emitted invalid JavaScript, Chromium reported
`Unexpected token ')'`, the whole IIFE was dead and the theme and text-style controls on every
generated page were inert.

**The suite reported 201/201 passed.**

⛔ **AND THE BROWSER MEASUREMENT AGREED WITH IT.** I was counting class mutations per second to
confirm an oscillation fix; a page whose script never runs produces **0 flips**, which is exactly
what the fix was supposed to produce. The instrument and the suite were both green over a page
where nothing worked at all.

## Why no case could see it

Every one of the two hundred cases asked **what the script CONTAINS** — a substring, an exact
expression, an ordering. Not one asked **whether it is a program**. A substring assertion is
structurally blind to a missing delimiter, and two hundred of them are blind in the same way.

## How to apply

* **Add a case that PARSES the emitted artifact.** `node --check` for JS, `cssutils`/a parser for
  CSS, `yaml.safe_load`, `sqlparse` — whatever the real consumer uses.
* ⚠ **A balance check is not a parse.** `}{` balances and does not parse. Keep both: the balance
  check always runs, the parse catches what it cannot. Both were verified falsifiable — dropping
  a brace reddens, and so does a balanced-but-invalid `}{)(;`.
* ⛔ **A missing interpreter is a FAILURE, not a skip** — the parse case must say
  `CANNOT RUN … treat this as NOT CHECKED` and fail. Verified: with `node` off PATH the suite
  reports 199/201 with two named failures, not a silent pass.
* **Check the LIVE artifact too, not only the producer.** Parsing every `<script>` on a generated
  page is a different corpus from parsing the function's return value.

Related: [[a-test-that-cannot-fail]], [[measure-the-population-the-code-actually-sees]],
[[a-check-result-is-not-the-claim]], [[a-report-format-is-a-contract]].
