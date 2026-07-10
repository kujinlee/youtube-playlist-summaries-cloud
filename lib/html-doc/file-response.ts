// PURE LEAF (spec D10): imports nothing rooted at the project's "@" path alias, so the 1F-b
// import guard can scan it and the share route's use of it cannot smuggle in charging code.
// Do not add app imports here.

function asciiSafe(base: string): string {
  const cleaned = base
    .replace(/[^\x20-\x7e]/g, '_') // non-printable-ASCII (incl. all >=0x80 and control 0x00-0x1f,0x7f) → _
    .replace(/["\\/;]/g, '_')       // quote, backslash, slash, semicolon → _
    .replace(/^[.\s]+|[.\s]+$/g, ''); // trim leading/trailing dots and spaces
  return cleaned || 'summary';
}

function encodeRFC5987(s: string): string {
  // Strict allowlist: A-Za-z0-9 + RFC 5987 attr-char punctuation. `-` is at the class EDGE so the
  // literal `+.` chars are NOT parsed as a range (which would admit `,`). Everything else → %HH of
  // its UTF-8 bytes (so CR/LF/;/" and all multibyte chars are percent-encoded, never literal).
  const out: string[] = [];
  for (const byte of Buffer.from(s, 'utf-8')) {
    const ch = String.fromCharCode(byte);
    if (/[A-Za-z0-9!#$&+.^_`|~-]/.test(ch)) out.push(ch);
    else out.push('%' + byte.toString(16).toUpperCase().padStart(2, '0'));
  }
  return out.join('');
}

export function fileResponse(
  body: Buffer | string,
  opts: {
    kind: 'md' | 'html'; download: boolean; base: string; title?: string;
    cache: string; csp?: string; referrerPolicy?: string;
  },
): Response {
  const contentType =
    opts.kind === 'html' ? 'text/html; charset=utf-8'
    : opts.download ? 'text/markdown; charset=utf-8'
    : 'text/plain; charset=utf-8';

  const headers: Record<string, string> = {
    'Content-Type': contentType,
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': opts.cache,
  };
  if (opts.csp) headers['Content-Security-Policy'] = opts.csp;
  if (opts.referrerPolicy) headers['Referrer-Policy'] = opts.referrerPolicy;

  if (opts.download) {
    const ext = opts.kind; // 'md' | 'html'
    const ascii = `${asciiSafe(opts.base)}.${ext}`;
    const uni = `${encodeRFC5987(opts.title?.trim() || opts.base)}.${ext}`;
    headers['Content-Disposition'] = `attachment; filename="${ascii}"; filename*=UTF-8''${uni}`;
  }
  // `as BodyInit`: @types/node's `Buffer` is not structurally assignable to lib.dom's `BodyInit`
  // under this TS/lib combination (a known @types/node/lib.dom generic mismatch) even though a
  // Buffer is a valid runtime Response body (Node's fetch impl accepts it). Type-only cast, no
  // behavior change.
  return new Response(body as BodyInit, { status: 200, headers });
}
