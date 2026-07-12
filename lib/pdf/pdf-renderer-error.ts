/**
 * Thrown by `generateDocPdf` whenever the PDF render pipeline could not produce a document —
 * Chromium failed to launch, or the render/timeout race was lost. Callers (API routes) can map
 * `statusCode` straight onto the HTTP response without inspecting the message.
 */
export class PdfRendererUnavailable extends Error {
  statusCode = 503;

  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options as ErrorOptions);
    this.name = 'PdfRendererUnavailable';
  }
}
