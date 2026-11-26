/**
 * Shared frontend security helpers for URL validation and CSV export sanitization.
 */

const ALLOWED_EXTERNAL_PROTOCOLS = new Set(['http:', 'https:']);

/**
 * Validate an untrusted URL for safe anchor navigation.
 * Permits only http/https URLs or single-slash relative paths; rejects javascript:/data:/vbscript:.
 */
export function sanitizeExternalUrl(raw?: string | null): string | null {
  if (!raw || typeof raw !== 'string') return null;
  const trimmed = raw.replace(/[\u0000-\u001F\u007F]/g, '').trim();
  if (!trimmed) return null;

  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) {
    return trimmed;
  }

  try {
    const parsed = new URL(trimmed);
    if (!ALLOWED_EXTERNAL_PROTOCOLS.has(parsed.protocol.toLowerCase())) {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

/**
 * Sanitize and RFC-4180 quote a single CSV export cell to neutralize formula injection
 * when opened in spreadsheet software (=, +, @, tab, CR, or formula-style leading '-').
 */
export function sanitizeCsvCell(value: unknown): string {
  if (value === null || value === undefined) {
    return '""';
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(value) : '""';
  }
  let text = String(value);
  const trimmedStart = text.trimStart();
  const isPlainNegativeNumber = /^-\d+(\.\d+)?$/.test(trimmedStart);
  if (
    trimmedStart.startsWith('=') ||
    trimmedStart.startsWith('+') ||
    trimmedStart.startsWith('@') ||
    text.startsWith('\t') ||
    text.startsWith('\r') ||
    (trimmedStart.startsWith('-') && !isPlainNegativeNumber)
  ) {
    text = `'${text}`;
  }
  return `"${text.replace(/"/g, '""')}"`;
}

/**
 * Serialize an array of CSV rows into safe CSV file text.
 */
export function buildSafeCsvContent(headers: string[], rows: Array<Array<unknown>>): string {
  const headerLine = headers.map((h) => sanitizeCsvCell(h)).join(',');
  const rowLines = rows.map((row) => row.map((cell) => sanitizeCsvCell(cell)).join(','));
  return [headerLine, ...rowLines].join('\n');
}
