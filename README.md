# binder.dev

The project site for [binder](https://github.com/uRadical/binder), a
zero-dependency HTTP request binding library for Go.

Static HTML, two stylesheets, one small module of custom elements. No
framework, no bundler, no dependencies — what is in this repository is exactly
what is served. The only build step generates `/docs` from its fragments, so
that ten pages can share one header, sidebar and footer without ten copies of
them drifting apart.

```
index.html                  the landing page — hand-written
404.html                    noindex, links back into /docs
docs/                       GENERATED — do not edit by hand
tools/pages/*.html          the docs sources: front matter plus a body fragment
tools/build.py              the generator
assets/css/site.css         all shared styling; custom properties for light/dark
assets/css/docs.css         /docs layout only
assets/js/components.js     <bd-code>, <bd-tabs>, <bd-theme-toggle>
assets/binder.svg           the project mark — hero, header, footer
assets/favicon.svg          browser tab icon
assets/uradical-logo.webp   uRadical wordmark — footer attribution
assets/uradical-mark.png    uRadical brandmark (unused by the page; kept as a source)
sitemap.xml                 GENERATED
llms.txt                    GENERATED
CNAME                       binder.dev
.nojekyll                   serve files as-is, no Jekyll pass
.github/workflows/pages.yml
```

## Editing the docs

Never edit `docs/*.html` — the next build overwrites it. Edit the matching
fragment in `tools/pages/` and rebuild:

```bash
python3 tools/build.py
```

A fragment is front matter (`title` and `desc`, one per line) then a `---` line
then the page body. Everything around it — head, header, sidebar, breadcrumb,
prev/next links, footer — comes from `tools/build.py`.

To add a page, drop a fragment in `tools/pages/` and add it to `NAV` in
`tools/build.py`. The nav order, the sitemap, `llms.txt` and the prev/next
links all follow from that one list. A fragment not listed in `NAV` is skipped,
and the build says so.

Only three things need updating when binder itself releases: `VERSION` and
`LASTMOD` in `tools/build.py`, and the version in the landing page's hero and
JSON-LD.

## Preview locally

No tooling required — any static server will do:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

Use a server rather than opening the files directly: every link and asset path
is site-absolute, so `file://` will not resolve them.

## Deploying

Pushing to `main` publishes, via `.github/workflows/pages.yml`. The workflow
rebuilds `/docs` and fails on a diff, so a hand-edited page cannot be published
and then silently overwritten by the next real build.

Enable it once under **Settings → Pages → Source: GitHub Actions**, and point
`binder.dev` at GitHub Pages with the four `A` records for `185.199.108.153`,
`185.199.109.153`, `185.199.110.153` and `185.199.111.153` (or a `CNAME` to
`uradical.github.io` on a subdomain).
