---
status: accepted
---

# The hosted product never downloads YouTube video (no `yt-dlp`/`ffmpeg` server-side)

The **hosted** product obtains all YouTube content through **Gemini's native YouTube-URL
ingestion** — Google's API consuming Google's own video — and **never downloads video bytes
to our server**. The server image therefore ships **no `yt-dlp` and no `ffmpeg`/`ffprobe`**
(`Dockerfile` installs only Chromium, for PDF export). The **local** single-user tool keeps
the full `yt-dlp`/`ffmpeg` slide-capture path.

**This is a Terms-of-Service decision, not a packaging or performance one.** That distinction
is the whole reason this ADR exists: from the code, the absence of `ffmpeg` in the Dockerfile
is indistinguishable from an oversight, and reads as a gap someone should close.

Source: `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §2.1
("Legal/ToS gate (Codex H9) — RESOLVED 2026-07-02").

## Why this is recorded as an ADR

The decision previously lived **only** in that spec — which is marked **Draft v3**, so a
reader cannot tell that §2.1 is binding while the surrounding document is provisional — plus
a single clause in `docs/deploy.md`.

It was misread on 2026-07-30. The first architecture review (`docs/reviews/architecture-review-2026-07-30.md`)
read exactly what Phase 6 requires — `CONTEXT.md` and `docs/adr/` — found no mention, and
described cloud slide capture as an incidental packaging limitation. `improve-codebase-architecture`
treats ADRs as the decisions a review must not re-litigate; a decision absent from `docs/adr/`
is, in practice, a decision a future review will propose reversing.

## Considered options

- **`yt-dlp` on the server (rejected — the ToS gate itself).** Reuse the existing local
  capture code in the worker. This is a server-side download of YouTube video, which the ToS
  gate exists to forbid. Datacenter IPs are also blocked in practice, so it fails
  operationally as well as legally.
- **Headless Chromium screenshotting the player (rejected — the same violation).** Tempting
  because **Chromium is already in the image** for PDF export, so it looks free. It is not:
  per §2.1, *any* server capture — `yt-dlp` **or** Chromium screenshotting the player — is
  the same ToS violation. **Swapping the tool does not change the posture.** Anyone proposing
  "we already have Chromium, just screenshot the frame" is re-opening this ADR, not finding a
  loophole.
- **Browser extension (rejected for now).** Cleaner frames and low per-use friction, but
  frame extraction is more aggressive, and it carries Chrome-Web-Store takedown risk under
  YouTube-downloader policy, plus a per-browser build.
- **Gemini YouTube-URL ingestion (chosen).** The Gemini API accepts a YouTube URL directly;
  Google's infrastructure watches the video and returns transcript/summary/analysis. No bytes
  touch our server. Already present in the codebase as `transcribeViaGemini`, promoted from
  caption-gated fallback to the primary hosted path. Constraints to design around: **public
  videos only**, a per-day YouTube quota, and the URL feature being in preview.

## Consequences

- **ToS-clean hosted deliverables** are summaries, dig-deeper *text*, section timestamps, and
  visual *descriptions* ("at 4:32 a diagram shows…"). Gemini returns understanding, not frames.
- **No pixel slides in the cloud, by construction.** Real YouTube pixels can only be obtained
  on the **user's own device** — via the official player or a file the user already holds.
  Slide capture is therefore a capability with two implementations: a cloud one (descriptions
  / no image) and an on-device one (the current `yt-dlp`/`ffmpeg` code).
- **When hosted slides are added, `getDisplayMedia` is the default mechanism** — the user
  screenshots their own screen, needs no install, and keeps the cleanest posture. It is a
  deferred, self-contained feature, not part of the spine.
- **The absent binaries are load-bearing, not an oversight.** Do not add `yt-dlp` or `ffmpeg`
  to the `Dockerfile` to "fix" cloud slide capture. A lighter worker image is a side effect of
  this decision, never its justification.
- **CI installing `ffmpeg` does not contradict this** (`.github/workflows/ci.yml`). The test
  runner is not the product: `tests/lib/dig/slide-crop.integration.test.ts` exercises the
  **local** capture path, which legitimately uses `ffmpeg`. The constraint is on what the
  hosted product does to YouTube, not on what a test machine has installed.
- **The CSP is consistent with this, not accidentally inert.** `buildDigCsp` sets
  `img-src 'none'` while the dig renderer can emit `data:` images; that combination never
  fires in the cloud because the cloud dig path carries no assets. Exploration during the
  2026-07-30 review raised this as latent risk "if cloud slide capture ships" (it was not
  carried into that document's findings). Under this ADR server-side capture does not ship,
  so it stays inert by design. Revisit the CSP only if on-device capture starts delivering
  pixels into a cloud-served document.
- **Reversing this decision is a legal question first.** Any change that makes the server
  acquire YouTube frames — regardless of tool — requires re-opening the ToS gate, not merely
  an engineering plan.

---

## Amendment 2026-08-06 — may the CLIENT upload locally-captured frames to our cloud? **No.**

**Why this is recorded even though the answer is no.** This ADR's own rationale is that *"a decision
absent from `docs/adr/` is, in practice, a decision a future review will propose reversing."* The
proposal below was made once, during round 3 of the stable-blob-addressing review, on reasoning that is
genuinely sound as far as it goes. Without an entry it will be made again.

**The proposal.** The hosted product cannot capture frames, but the **local** tool can and does. Since
sync exists to unify local and cloud content, local could upload its captured frames so the cloud can
*display* what it cannot *capture*. The cloud never runs `ffmpeg`; it only serves bytes a user's own
device legitimately obtained.

**Why it is refused — capture and redistribution are different surfaces.** The body of this ADR forbids
*obtaining* pixels server-side, and states "no pixel slides in the cloud" as a **consequence** of that.
The proposal does not violate the capture rule, so the original text does not settle it. It is refused
on a second ground the original did not reach:

- **The ToS is contractual and independent of copyright fair use.** Extracting static frames for
  commentary in a small team is textbook transformative fair use and very likely safe *in court*. That
  is irrelevant here: YouTube's terms bind us as a platform consumer regardless, and are enforced by
  API-key revocation and account action rather than by litigation. **A strong fair-use position is not
  a ToS defence.** There is no "internal use" or "private document" exemption in the developer terms.
- **A backend that accepts frame uploads, stores them, and syncs them onward is an unauthorised media
  redistribution pipeline** for YouTube-derived content. That is a materially worse posture than
  capture, because it makes *us* the distributor rather than a user's own device the recorder.

**Rejected alternative — client-side capture from the embedded player.** Proposed as: render the
official IFrame player at timestamp *T*, snapshot the frame with HTML5 Canvas on the user's device, so
no server is involved. **It does not work, and if it did it would be the violation.**

- **Technically impossible.** There is no API to draw an `<iframe>` to a canvas — canvas accepts images,
  video elements and canvases, not documents. Even for a `<video>`, cross-origin content taints the
  canvas and `getImageData`/`toDataURL` raise `SecurityError`. The YouTube player is cross-origin by
  construction. (Commonly described as "CORS"; the mechanism is the Same-Origin Policy and canvas
  tainting.)
- **And it is the same argument this ADR already rejected**, relocated to the client: the terms target
  copying pixels *outside the official player*, and programmatically snapshotting frames out of the
  official player to persist them is exactly that. Compare the Chromium-screenshot option above —
  *"swapping the tool does not change the posture."*

**What we do instead — the deep-link pattern.** Cloud-side, a slide token renders as its caption plus a
**timestamp deep link** into the official player (`watch?v=<id>&t=<sec>s`), reusing the `▶ (mm:ss)`
treatment `render-dig-deeper.ts:289` already applies to section headings. Optionally, on click, an
inline `youtube-nocookie.com/embed/<id>?start=<sec>` player. Zero pixels traverse our servers; the
official player renders the frame on the user's device under YouTube's own contract.

**Not the default renderer, deliberately.** An embed with `autoplay=0` displays the video's *poster
thumbnail*, not the frame at *T* — the frame appears only once playback starts, and mobile requires a
user gesture. So an always-embedded player shows the **wrong** image while costing one full player per
slide, and a dig-deeper section can carry several. Caption + link by default, embed on demand.
*(Verify the poster behaviour in a browser before implementing; the design depends on it.)*

**Consequences.** `ADR-0005` holds unbroken and needs no redistribution exception. Assets remain a
**local-backend concern only**: nothing writes them to the bucket, sync does not copy them
(`lib/cloud-sync/` contains zero references to assets), and the cloud dig path already rewrites slide
tokens to caption-only placeholders (`parse-dig-section-blob.ts`). Cloud storage design — keys,
retention, GC — must therefore say nothing about slide assets. **If either of those two facts ever
changes, this amendment is void and the question reopens.**

