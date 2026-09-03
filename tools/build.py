#!/usr/bin/env python3
"""Build /docs from the fragments in tools/pages.

Ten documentation pages share one header, one sidebar and one footer. Writing
that shell into each file by hand guarantees the nav drifts out of step, so the
shell lives here and each fragment carries only its own prose.

    python3 tools/build.py

Writes docs/*.html, sitemap.xml and llms.txt. Everything it writes is listed in
GENERATED below and should not be edited by hand.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ROOT / "tools" / "pages"

SITE = "https://gobinder.dev"
VERSION = "1.1.0"

# The sitemap's <lastmod>. Pinned rather than taken from the clock, so that
# rebuilding an unchanged site produces an unchanged sitemap — CI rebuilds and
# fails on a diff, and a date that moved every midnight would fail every day.
# Bump it when the content changes.
LASTMOD = "2026-08-23"
REPO = "https://github.com/uRadical/binder"
MODULE = "uradical.io/go/binder"

GENERATED = "docs/*.html, sitemap.xml, llms.txt"

# Sidebar order and grouping. Each entry is (slug, nav label, card blurb).
# The slug doubles as the fragment filename and the output filename.
NAV = [
    ("Getting started", [
        ("index",         "Overview",            "What binder does, and the shape of a bound request."),
        ("install",       "Install &amp; quick start", "Add the module, bind your first handler."),
        ("sources",       "Binding sources",     "path, query, body, json, cookie, header — and which wins."),
    ]),
    ("Reference", [
        ("types",         "Types &amp; conversion",   "Primitives, slices, nested structs, TextUnmarshaler."),
        ("options",       "Options",             "omitempty, required, BindOptions, MaxBodySize."),
        ("errors",        "Error handling",      "BindError, the sentinels, and the status code for each."),
        ("validation",    "Validation",          "The Validator interface, and what binder deliberately leaves out."),
        ("api",           "API reference",       "Every exported identifier in the package."),
    ]),
    ("Project", [
        ("performance",   "Performance",         "Measured cost per bind, and where it goes."),
        ("comparison",    "Comparison",          "binder against Echo, Gin, gorilla/schema and hand-written code."),
        ("compatibility", "Compatibility",       "What is covered by semver, and the Go version policy."),
    ]),
]

ORDER = [slug for _, items in NAV for slug, _, _ in items]
LABELS = {slug: (label, blurb) for _, items in NAV for slug, label, blurb in items}


def url_for(slug: str) -> str:
    return "/docs/" if slug == "index" else f"/docs/{slug}.html"


def read_fragment(slug: str) -> tuple[dict[str, str], str]:
    """Split a fragment into `key: value` front matter and an HTML body."""
    text = (PAGES / f"{slug}.html").read_text(encoding="utf-8")
    head, _, body = text.partition("\n---\n")
    if not body:
        sys.exit(f"{slug}.html: missing the '---' line that ends the front matter")

    meta = {}
    for line in head.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()

    for required in ("title", "desc"):
        if required not in meta:
            sys.exit(f"{slug}.html: front matter is missing '{required}'")

    return meta, body.strip("\n")


def sidebar(current: str) -> str:
    out = []
    out.append(f'      <p class="docs-version">Documents <strong>v{VERSION}</strong></p>')
    for group, items in NAV:
        out.append(f'      <p class="docs-nav-title">{group}</p>')
        out.append("      <ul>")
        for slug, label, _ in items:
            on = ' class="on"' if slug == current else ""
            out.append(f'        <li><a href="{url_for(slug)}"{on}>{label}</a></li>')
        out.append("      </ul>")
    return "\n".join(out)


def pager(current: str) -> str:
    i = ORDER.index(current)
    prev_slug = ORDER[i - 1] if i > 0 else None
    next_slug = ORDER[i + 1] if i < len(ORDER) - 1 else None
    if not prev_slug and not next_slug:
        return ""

    parts = ['    <nav class="docs-pager" aria-label="Pagination">']
    if prev_slug:
        parts.append(f'      <a class="prev" href="{url_for(prev_slug)}">{LABELS[prev_slug][0]}</a>')
    else:
        parts.append("      <span></span>")
    if next_slug:
        parts.append(f'      <a class="next" href="{url_for(next_slug)}">{LABELS[next_slug][0]}</a>')
    parts.append("    </nav>")
    return "\n".join(parts)


GITHUB_MARK = (
    '<svg viewBox="0 0 16 16" width="17" height="17" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 '
    "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 "
    "1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 "
    "0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 "
    ".27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 "
    "3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8Z\"/>"
    "</svg>"
)


def page(slug: str, meta: dict[str, str], body: str) -> str:
    url = SITE + url_for(slug)
    title = meta["title"]
    desc = meta["desc"]
    full_title = title if slug == "index" else f"{title} — binder"

    crumb = ""
    if slug != "index":
        crumb = (
            '    <p class="crumb"><a href="/">binder</a> / '
            f'<a href="/docs/">Docs</a> / {title}</p>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#FBFBFD" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#080E2B" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="article">
<meta property="og:site_name" content="binder">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{full_title}">
<meta name="twitter:description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sen:wght@400;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/site.css">
<link rel="stylesheet" href="/assets/css/docs.css">
<script src="/assets/js/components.js" type="module"></script>
<script>
  // Applied before first paint so a stored theme choice never flashes.
  try {{
    var t = localStorage.getItem('bd-theme');
    if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
  }} catch (e) {{}}
</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
  <div class="wrap header-inner">
    <a class="wordmark" href="/">
      <img class="mark" src="/assets/binder.svg" alt="" width="36" height="24" decoding="async">
      <span>binder</span>
    </a>
    <nav aria-label="Primary">
      <ul class="nav">
        <li><a href="/#why">Why</a></li>
        <li><a href="/#sources">Sources</a></li>
        <li><a href="/docs/" aria-current="page">Docs</a></li>
        <li><a href="/#install">Install</a></li>
      </ul>
    </nav>
    <div class="header-actions">
      <a class="icon-link" href="{REPO}" rel="noopener"
         aria-label="binder on GitHub" title="GitHub">{GITHUB_MARK}</a>
      <bd-theme-toggle></bd-theme-toggle>
    </div>
  </div>
</header>

<div class="wrap docs-layout">
  <nav class="docs-nav" aria-label="Documentation">
{sidebar(slug)}
  </nav>

  <main id="main" class="docs-main">
{crumb}{body}

{pager(slug)}
  </main>
</div>

<footer class="site-footer">
  <div class="wrap footer-inner">
    <div>
      <span class="footer-brand">
        <img src="/assets/binder.svg" alt="" width="39" height="26" decoding="async">
        <span class="footer-mark">binder</span>
      </span>
      <p class="footer-note">MIT licensed. Written in Go, with no dependencies.</p>
      <a class="by-uradical" href="https://uradical.io" rel="noopener">
        <span>An open-source library from</span>
        <img src="/assets/uradical-logo.webp" alt="uRadical" width="132" height="26" decoding="async">
      </a>
    </div>
    <nav aria-label="Footer">
      <ul class="footer-links">
        <li><a href="{REPO}" rel="noopener">GitHub</a></li>
        <li><a href="https://pkg.go.dev/{MODULE}" rel="noopener">pkg.go.dev</a></li>
        <li><a href="{REPO}/releases" rel="noopener">Releases</a></li>
        <li><a href="{REPO}/issues" rel="noopener">Issues</a></li>
      </ul>
    </nav>
  </div>
</footer>

</body>
</html>
"""


def sitemap() -> str:
    urls = [(SITE + "/", "1.0")]
    urls += [(SITE + url_for(slug), "0.9" if slug == "index" else "0.8") for slug in ORDER]
    entries = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{LASTMOD}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n    <priority>{pri}</priority>\n  </url>"
        for loc, pri in urls
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'


def llms_txt(metas: dict[str, dict[str, str]]) -> str:
    lines = [
        "# binder",
        "",
        f"> Zero-dependency HTTP request binding for Go, v{VERSION}. Maps path parameters, "
        "query strings, JSON and form bodies, cookies and headers onto a struct using "
        "struct tags. Binding only — no validation framework, no router, no logging.",
        "",
        f"Module: `{MODULE}` · Source: {REPO} · License: MIT · Requires Go 1.27.",
        "",
        "## Docs",
        "",
    ]
    for slug in ORDER:
        label = LABELS[slug][0].replace("&amp;", "&")
        lines.append(f"- [{label}]({SITE}{url_for(slug)}): {metas[slug]['desc']}")
    lines += [
        "",
        "## Optional",
        "",
        f"- [Source and README]({REPO}): the canonical documentation, kept in step with this site.",
        f"- [Go package reference](https://pkg.go.dev/{MODULE}): generated from the doc comments.",
        f"- [Changelog]({REPO}/blob/main/CHANGELOG.md): what changed in each release.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    metas: dict[str, dict[str, str]] = {}

    for slug in ORDER:
        meta, body = read_fragment(slug)
        metas[slug] = meta
        out = ROOT / "docs" / ("index.html" if slug == "index" else f"{slug}.html")
        out.write_text(page(slug, meta, body), encoding="utf-8")
        print(f"  docs/{out.name}")

    (ROOT / "sitemap.xml").write_text(sitemap(), encoding="utf-8")
    (ROOT / "llms.txt").write_text(llms_txt(metas), encoding="utf-8")
    print("  sitemap.xml\n  llms.txt")

    stray = sorted(p.stem for p in PAGES.glob("*.html") if p.stem not in ORDER)
    if stray:
        print(f"note: fragments not listed in NAV, so not built: {', '.join(stray)}")


if __name__ == "__main__":
    main()
