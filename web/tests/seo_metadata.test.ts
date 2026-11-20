import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';

describe('SEO, Favicon & Google Site Names Metadata Contract', () => {
  const indexHtmlPath = resolve(process.cwd(), 'index.html');
  const indexHtml = readFileSync(indexHtmlPath, 'utf8');
  const publicDir = resolve(process.cwd(), 'public');

  test('1. Canonical domain is configured to https://www.finexai.tech/', () => {
    assert.match(indexHtml, /<link\s+rel="canonical"\s+href="https:\/\/www\.finexai\.tech\/"\s*\/?>/);
  });

  test('2. Primary favicon link satisfies Google Search 48px square requirement (raster PNG)', () => {
    assert.match(indexHtml, /<link\s+rel="icon"\s+type="image\/png"\s+sizes="48x48"\s+href="\/favicon-48x48\.png"\s*\/?>/);
    assert.match(indexHtml, /<link\s+rel="icon"\s+type="image\/x-icon"\s+href="\/favicon\.ico"\s+sizes="any"\s*\/?>/);
    assert.match(indexHtml, /<link\s+rel="apple-touch-icon"\s+sizes="180x180"\s+href="\/apple-touch-icon\.png"\s*\/?>/);
    
    // SVG icon link must NOT be declared as rel="icon" in <head> because Google Search SERP does not support SVG favicons
    assert.doesNotMatch(indexHtml, /<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="\/favicon\.svg"\s*\/?>/);
  });

  test('3. Open Graph og:site_name is set to "FinEx"', () => {
    assert.match(indexHtml, /<meta\s+property="og:site_name"\s+content="FinEx"\s*\/?>/);
  });

  test('4. WebSite structured data (JSON-LD) specifies name "FinEx" and alternateName array', () => {
    const scripts = [...indexHtml.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)];
    assert.ok(scripts.length >= 1, 'Expected at least 1 JSON-LD script block');

    const websiteBlock = scripts
      .map((m) => {
        try {
          return JSON.parse(m[1].trim());
        } catch {
          return null;
        }
      })
      .find((b) => b && b['@type'] === 'WebSite');

    assert.ok(websiteBlock, 'Must contain a top-level @type: "WebSite" JSON-LD block');
    assert.equal(websiteBlock.name, 'FinEx');
    assert.equal(websiteBlock.url, 'https://www.finexai.tech/');
    assert.ok(Array.isArray(websiteBlock.alternateName), 'alternateName must be an array');
    assert.ok(websiteBlock.alternateName.includes('FinEx AI'));
    assert.ok(websiteBlock.alternateName.includes('Finex'));
  });

  test('5. Static fallback header has semantic FinEx branding text', () => {
    assert.match(indexHtml, /aria-label="FinEx"/);
  });

  test('6. Favicon assets exist in public/ and are non-empty', () => {
    const requiredFiles = [
      'favicon.ico',
      'favicon-48x48.png',
      'favicon-96x96.png',
      'favicon-192x192.png',
      'apple-touch-icon.png',
      'site.webmanifest',
      'robots.txt',
    ];

    for (const file of requiredFiles) {
      const filePath = join(publicDir, file);
      assert.ok(existsSync(filePath), `Required public asset missing: ${file}`);
      const content = readFileSync(filePath);
      assert.ok(content.length > 0, `File ${file} must not be empty`);
    }
  });

  test('7. site.webmanifest is valid JSON and declares FinEx name and icons', () => {
    const manifestPath = join(publicDir, 'site.webmanifest');
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
    assert.equal(manifest.name, 'FinEx');
    assert.equal(manifest.short_name, 'FinEx');
    assert.ok(Array.isArray(manifest.icons) && manifest.icons.length >= 3);
  });

  test('8. robots.txt allows crawlers on / and does not block favicons', () => {
    const robotsPath = join(publicDir, 'robots.txt');
    const robots = readFileSync(robotsPath, 'utf8');
    assert.match(robots, /User-agent:\s*\*/i);
    assert.match(robots, /Allow:\s*\//i);
    assert.doesNotMatch(robots, /Disallow:\s*\/favicon/i);
  });
});
