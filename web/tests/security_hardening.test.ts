import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { apiClient } from '../src/api/client.ts';
import { buildSafeCsvContent, sanitizeCsvCell, sanitizeExternalUrl } from '../src/utils/security.ts';

const createJwt = (payload: Record<string, unknown>) => {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `${header}.${body}.sig`;
};

describe('Frontend Security Hardening Regression Suite', () => {
  test('1. URL sanitizer blocks javascript, data, vbscript, control-char obfuscation, and protocol-relative links', () => {
    assert.equal(sanitizeExternalUrl('https://www.sebi.gov.in/legal/circulars'), 'https://www.sebi.gov.in/legal/circulars');
    assert.equal(sanitizeExternalUrl('http://localhost:5173/privacy'), 'http://localhost:5173/privacy');
    assert.equal(sanitizeExternalUrl('/privacy'), '/privacy');

    assert.equal(sanitizeExternalUrl('javascript:alert(1)'), null);
    assert.equal(sanitizeExternalUrl('java\tscript:alert(1)'), null);
    assert.equal(sanitizeExternalUrl('  JaVaScRiPt:alert(document.cookie)'), null);
    assert.equal(sanitizeExternalUrl('data:text/html,<script>alert(1)</script>'), null);
    assert.equal(sanitizeExternalUrl('vbscript:msgbox(1)'), null);
    assert.equal(sanitizeExternalUrl('//evil.example.com/phish'), null);
    assert.equal(sanitizeExternalUrl(''), null);
    assert.equal(sanitizeExternalUrl(null), null);
  });

  test('2. CSV export neutralizes spreadsheet formula payloads while preserving plain negative numbers', () => {
    assert.equal(sanitizeCsvCell("=cmd|'/C calc'!A0"), '"\'=cmd|\'/C calc\'!A0"');
    assert.equal(sanitizeCsvCell('+SUM(A1:A2)'), '"\'+SUM(A1:A2)"');
    assert.equal(sanitizeCsvCell('@HYPERLINK("http://evil.example")'), '"\'@HYPERLINK(""http://evil.example"")"');
    assert.equal(sanitizeCsvCell('\t=2+2'), '"\'\t=2+2"');
    assert.equal(sanitizeCsvCell('\r+2+2'), '"\'\r+2+2"');
    assert.equal(sanitizeCsvCell('-cmd|calc'), '"\'-cmd|calc"');
    assert.equal(sanitizeCsvCell('-125.50'), '"-125.50"');
    assert.equal(sanitizeCsvCell(-125.5), '-125.5');

    const csv = buildSafeCsvContent(['ID', 'Note'], [['ord-1', '=1+1']]);
    assert.equal(csv, '"ID","Note"\n"ord-1","\'=1+1"');
  });

  test('3. JWT client helper fails closed when exp claim is absent or expired', () => {
    const validToken = createJwt({ sub: 'usr-1', exp: Math.floor(Date.now() / 1000) + 3600 });
    const expiredToken = createJwt({ sub: 'usr-1', exp: Math.floor(Date.now() / 1000) - 60 });
    const noExpToken = createJwt({ sub: 'usr-1' });

    assert.equal(apiClient.isTokenExpired(validToken), false);
    assert.equal(apiClient.isTokenExpired(expiredToken), true);
    assert.equal(apiClient.isTokenExpired(noExpToken), true);
    assert.equal(apiClient.isTokenExpired('not-a-jwt'), true);
  });

  test('4. Root and web Vercel manifests enforce CSP and defensive browser security headers', () => {
    const repoRoot = path.resolve(import.meta.dirname, '..', '..');
    const files = [path.join(repoRoot, 'vercel.json'), path.join(repoRoot, 'web', 'vercel.json')];

    for (const filePath of files) {
      const parsed = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      const catchAll = parsed.headers.find((h: any) => h.source === '/(.*)');
      assert.ok(catchAll, `${filePath} must define headers on /(.*)`);

      const headerMap = Object.fromEntries(catchAll.headers.map((h: any) => [h.key, h.value]));
      assert.equal(headerMap['X-Content-Type-Options'], 'nosniff');
      assert.equal(headerMap['X-Frame-Options'], 'DENY');
      assert.ok(headerMap['Referrer-Policy']);
      assert.ok(headerMap['Permissions-Policy']);
      assert.ok(headerMap['Strict-Transport-Security']);

      const csp = headerMap['Content-Security-Policy'];
      assert.ok(csp, `${filePath} must define Content-Security-Policy`);
      assert.ok(!csp.includes("connect-src 'self' *"), 'CSP must not allow wildcard connect-src *');
      assert.ok(!csp.includes("script-src 'self' 'unsafe-inline'"), 'CSP script-src must not permit unsafe-inline');
      assert.ok(csp.includes("object-src 'none'"));
      assert.ok(csp.includes("frame-ancestors 'none'"));
    }
  });
});
