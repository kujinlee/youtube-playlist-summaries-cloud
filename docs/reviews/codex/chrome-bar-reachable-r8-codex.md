<!-- codex-review: model=gpt-6.1-sol -->

**High — Nested slots turn the reserve into continuous layout growth.** `scripts/page_chrome.py:1134`, with the document-wide consumer at `:904`.

Concrete failing body, supplied with complete palettes and the emitted chrome script:

```python
'<h1>Title</h1><div class="chrome-slot"><div class="chrome">' \
+ chrome_bar("x", "t", refresh=False) \
+ '</div></div><div style="height:6000px"></div>'
```

`brief-compose.compose` accepts this. Chromium at 320×568, without scrolling, measured:

| Measurement | After 200ms | After another 1s | After another 1s |
|---|---:|---:|---:|
| `--chrome-h` | 225.625px | 1102.5px | 1965px |
| Document height | 6328px | 7205px | 8067px |

The selected outer `.chrome` contains the inner slot. Setting the global reserve enlarges that inner slot, enlarging the measured outer bar; `ResizeObserver` repeats the cycle. In a separate run, the content below moved from y=147.375 to y=1196.75 in 1.2 seconds.

**Inside the declared subject:** valid HTML nesting generated chrome inside a fragment wrapper; no duplicate controls or parser disagreement.

**Pre-existing:** restoring the previous selector still produces continuous growth. This is not evidence that the latest selector fix created another regression. It does refute the last-six-commits characterization in `docs/backlog.md:286` that the reserve defect is merely a permanent cosmetic band.

**Low — The removed exemptions describe lexical variation, but the suites still cannot distinguish either argument from a constant.** `scripts/brief-compose.py:1867`; `scripts/page_chrome.py:1502`.

Both removal claims are literally correct: `compose.title` receives `"T"` and `"t"`; `assert_wired.where` receives distinct labels. Consequently, removing these exemptions is consistent with the ratchet’s documented source-text rule.

However, these concrete severances remain undetected:

```python
# compose: ignore title
f"<title>T</title>\n{styled}\n</head>\n<body>\n"

# assert_wired: ignore where
where = "p"
```

I added these two entries **only in the temporary harness copy**, then ran the shipped harness. Result: **114 mutations, 112 killed, 112 attributed, two survivors**, specifically these two. The tests never require the requested title or diagnostic prefix to survive.

Concrete affected inputs are `compose(..., title="Quarterly review", ...)` and `assert_wired(theme_control(), "my-page")`: those severances replace their requested outputs while both suites remain green.

**Inside the declared subject:** a coverage finding concerning ordinary caller arguments, not a claim that current production output is wrong. The ratchet removals themselves are not defective.

Verification and unsuccessful attacks:

- All claimed checks reproduced: **220/220**, **149/149**, **178/178**; fixture variation **870 parameters, 114 ratcheted**, rc=0.
- The unchanged, shipped manifests reproduced **112 killed, 112 attributed, zero survivors**. No ambiguous mutation anchor was reported.
- A synchronous descendant selection guarantees a slot ancestor; I found no ordinary shape making `closest` return null. Template contents are absent from the document selector results.
- I ran `place_bar` on shield/interactive crossing inputs. The residual discrepancies required mismatched markup; I found no supported-input decrement defect worth filing.
- On the recomposed `2026-10-06` fragment, sampled scroll positions kept both controls reachable, with **zero stationary class flips**. After resize while pinned, returning to flow produced reserve **101.34375px**, exactly matching the in-flow bar. The pinned bar was **102.34375px**. This supports the one-pixel observation and source-dependent figure caveat; it does not establish every scroll position or every producer.

The last six commits contain substantive fixes. I did **not** establish an eighth fix-created-next-finding sequence.

**NOT CONVERGED — accepted nested generated markup still causes continuous layout growth, exceeding the newly recorded cosmetic bound.**
