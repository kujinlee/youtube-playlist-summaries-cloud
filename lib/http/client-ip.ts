/** `Fly-Client-IP` is set by Fly.io's edge and cannot be spoofed by the client past the
 *  proxy; `X-Forwarded-For`'s FIRST hop is the original client when present (later hops are
 *  appended by intermediate proxies), so prefer Fly's header and fall back to XFF[0]. */
export function parseClientIp(req: Request): string | null {
  const fly = req.headers.get('fly-client-ip');
  if (fly) return fly;
  const xff = req.headers.get('x-forwarded-for');
  if (xff) {
    const first = xff.split(',')[0]?.trim();
    if (first) return first;
  }
  return null;
}
