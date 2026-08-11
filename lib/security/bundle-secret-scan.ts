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

/** Same-origin `<script src>` URLs in a served HTML page, absolute and de-duplicated.
 *
 *  Cross-origin scripts are deliberately NOT followed: this check answers "did OUR deployment
 *  ship a secret", and fetching third-party hosts would make the result depend on someone
 *  else's uptime. (A CSP already blocks foreign scripts here; that is a separate concern.) */
export function extractScriptUrls(html: string, baseUrl: string): string[] {
  const origin = new URL(baseUrl).origin;
  const out: string[] = [];
  for (const m of html.matchAll(SCRIPT_SRC_RE)) {
    let abs: URL;
    try {
      abs = new URL(m[2], baseUrl);
    } catch {
      continue;
    }
    if (abs.origin !== origin) continue;
    const href = abs.toString();
    if (!out.includes(href)) out.push(href);
  }
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
