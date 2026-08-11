/** Scan text (a deployed JS bundle, an HTML page) for credentials that must never reach a browser.
 *
 *  WHY THIS EXISTS, and why it is not `check-service-confinement.ts`: that script is STATIC — it
 *  walks the source import graph and is identical in every environment. It cannot observe a
 *  deployment. This one reads what the live server actually served, so it can fail.
 *
 *  The discriminator is the whole design. Two Supabase credentials legitimately ship to the
 *  browser — the `anon` JWT and the `sb_publishable_` key — because both are public by
 *  construction and gated by RLS. A scanner that flags "a JWT" fires on every build, gets muted,
 *  and then detects nothing. So we decode the payload and judge the CLAIM, never the shape. */

export type LeakKind = 'service_role_jwt' | 'secret_api_key';

export interface Leak {
  kind: LeakKind;
  /** Byte offset in the scanned text — enough to locate it without reproducing it. */
  index: number;
  /** Deliberately NOT the secret. A finding that prints the credential leaks it a second time,
   *  into CI logs, which are retained and frequently world-readable. */
  hint: string;
}

const JWT_RE = /eyJ[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+/g;
const SECRET_KEY_RE = /sb_secret_[A-Za-z0-9_-]+/g;

function roleOf(payloadSegment: string): string | null {
  try {
    const claims = JSON.parse(Buffer.from(payloadSegment, 'base64url').toString('utf8'));
    return typeof claims?.role === 'string' ? claims.role : null;
  } catch {
    return null; // not a JWT payload; any base64-ish triple can match the shape
  }
}

const SCRIPT_SRC_RE = /<script\b[^>]*?\bsrc=(["'])(.*?)\1/gi;
const HREF_RE = /\bhref=(["'])(.*?)\1/gi;
/** Root-relative build-output paths, including ones that only ever appear inside Next.js's
 *  inline flight payload (where they are backslash-escaped, so quotes/backslashes end the match). */
const NEXT_CHUNK_RE = /\/_next\/static\/[A-Za-z0-9._/-]+\.js/g;

/** Every same-origin JS URL a served HTML page references — absolute, de-duplicated, in first-seen
 *  order. Collected from `<script src>`, `href` attributes, and bare `/_next/static/**.js` paths
 *  (which is how chunks appear inside Next.js's inline flight payload).
 *
 *  MEASURED on the real deployment 2026-08-11, and the honest number is: reading the extra two
 *  sources gains **nothing today** — `/login` yields the same 9 URLs either way, because every
 *  `_next` path and `href` there is already a script tag. The three sources are kept because the
 *  cost is one regex each and the failure they prevent is silent: if a future Next.js version
 *  preloads a chunk it does not script-tag, a `<script src>`-only reader would skip it and still
 *  print "clean". The tests pin that, so the behaviour cannot regress unnoticed.
 *
 *  (An earlier revision of this comment claimed 34-vs-9 and "~26% scanned". That was wrong — it
 *  compared total occurrences against distinct URLs. Corrected rather than deleted, because a
 *  plausible false measurement in a security check is worth a warning.)
 *
 *  Cross-origin scripts are deliberately NOT followed: the question is "did OUR deployment ship a
 *  secret", and fetching third-party hosts would make the answer depend on someone else's uptime. */
export function extractScriptUrls(html: string, baseUrl: string): string[] {
  const origin = new URL(baseUrl).origin;
  const out: string[] = [];

  const add = (raw: string) => {
    let abs: URL;
    try {
      abs = new URL(raw, baseUrl);
    } catch {
      return;
    }
    if (abs.origin !== origin) return;
    if (!abs.pathname.endsWith('.js')) return;
    const href = abs.toString();
    if (!out.includes(href)) out.push(href);
  };

  for (const m of html.matchAll(SCRIPT_SRC_RE)) add(m[2]);
  for (const m of html.matchAll(HREF_RE)) add(m[2]);
  for (const m of html.matchAll(NEXT_CHUNK_RE)) add(m[0]);

  return out;
}

export function findLeakedSecrets(text: string): Leak[] {
  const leaks: Leak[] = [];

  for (const m of text.matchAll(JWT_RE)) {
    if (roleOf(m[1]) === 'service_role') {
      leaks.push({
        kind: 'service_role_jwt',
        index: m.index ?? -1,
        hint: 'JWT with role=service_role',
      });
    }
  }

  for (const m of text.matchAll(SECRET_KEY_RE)) {
    leaks.push({
      kind: 'secret_api_key',
      index: m.index ?? -1,
      hint: 'sb_secret_* API key',
    });
  }

  return leaks;
}
