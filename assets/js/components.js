/* ==========================================================================
   binder — site components
   Three custom elements, no dependencies, no build step. Each renders into
   light DOM so the page CSS applies and the markup stays readable, and each
   is written so the page is complete before (or without) the upgrade.
   ========================================================================== */

let uid = 0;

/* ---------------------------------------------------------------------------
   Go highlighting.

   A tokeniser rather than a parser: enough to colour keywords, literals and
   struct tags, and never enough to be wrong in a way that loses text. Every
   branch of the alternation either emits its match escaped or falls through
   to plain text, so the output always reads back as the input.

   Struct tags get their own colour because in this library the tag *is* the
   API — `query:"page,required"` is the thing the reader came to look at.
   --------------------------------------------------------------------------- */

const GO_KEYWORDS = new Set([
  'break', 'case', 'chan', 'const', 'continue', 'default', 'defer', 'else',
  'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import', 'interface',
  'map', 'package', 'range', 'return', 'select', 'struct', 'switch', 'type',
  'var',
]);

const GO_BUILTINS = new Set([
  'any', 'bool', 'byte', 'complex64', 'complex128', 'error', 'float32',
  'float64', 'int', 'int8', 'int16', 'int32', 'int64', 'rune', 'string',
  'uint', 'uint8', 'uint16', 'uint32', 'uint64', 'uintptr',
  'append', 'cap', 'copy', 'delete', 'len', 'make', 'new', 'panic', 'recover',
  'false', 'nil', 'true', 'iota',
]);

const GO_TOKEN = new RegExp([
  '(//[^\\n]*)',                    // 1 line comment
  '(/\\*[\\s\\S]*?\\*/)',           // 2 block comment
  '(`[^`]*`)',                      // 3 raw string — struct tags live here
  '("(?:\\\\.|[^"\\\\\\n])*")',     // 4 interpreted string
  "('(?:\\\\.|[^'\\\\\\n])*')",     // 5 rune
  '(\\b\\d[\\d_.xXa-fA-F]*\\b)',    // 6 number
  '([A-Za-z_][A-Za-z0-9_]*)',       // 7 identifier
].join('|'), 'g');

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;' };
const esc = (s) => s.replace(/[&<>]/g, (c) => ESCAPES[c]);
const span = (cls, text) => `<span class="${cls}">${esc(text)}</span>`;

function highlightGo(src) {
  let out = '';
  let last = 0;
  let m;

  GO_TOKEN.lastIndex = 0;
  while ((m = GO_TOKEN.exec(src)) !== null) {
    out += esc(src.slice(last, m.index));
    last = GO_TOKEN.lastIndex;

    const [text, comment1, comment2, raw, str, rune, num, ident] = m;

    if (comment1 || comment2) {
      out += span('tok-com', text);
    } else if (raw) {
      out += span('tok-tag', text);
    } else if (str || rune) {
      out += span('tok-str', text);
    } else if (num) {
      out += span('tok-num', text);
    } else if (ident) {
      if (GO_KEYWORDS.has(ident)) out += span('tok-kw', text);
      else if (GO_BUILTINS.has(ident)) out += span('tok-typ', text);
      // An exported name, or a package qualifier such as `binder.` or `http.`
      else if (/^[A-Z]/.test(ident) || src[GO_TOKEN.lastIndex] === '.') out += span('tok-typ', text);
      else out += esc(text);
    } else {
      out += esc(text);
    }
  }

  return out + esc(src.slice(last));
}

/* ---------------------------------------------------------------------------
   <bd-code> — wraps a <pre> and adds a copy button, plus Go colouring when
   the element carries data-lang="go".

   Without JS the block is simply a code block, which is the whole point: the
   markup in the file is the real source, uncoloured but complete.
   --------------------------------------------------------------------------- */
class BdCode extends HTMLElement {
  connectedCallback() {
    if (this.dataset.ready) return;
    this.dataset.ready = '1';

    const pre = this.querySelector('pre');
    if (!pre) return;

    // Highlight before the button is added, so the button is not in the source
    // text the tokeniser sees or the text the copy button reads back.
    if (this.dataset.lang === 'go') {
      const code = pre.querySelector('code') || pre;
      code.innerHTML = highlightGo(code.textContent);
    }

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy-btn';
    btn.textContent = 'Copy';
    btn.setAttribute('aria-label', 'Copy code to clipboard');

    btn.addEventListener('click', async () => {
      const text = pre.innerText.replace(/\n+$/, '');
      const ok = await writeClipboard(text);
      btn.textContent = ok ? 'Copied' : 'Press ⌘C';
      btn.dataset.state = ok ? 'done' : '';
      clearTimeout(this._t);
      this._t = setTimeout(() => {
        btn.textContent = 'Copy';
        delete btn.dataset.state;
      }, 1800);
    });

    this.appendChild(btn);
  }
}

async function writeClipboard(text) {
  // Clipboard API needs a secure context; fall back to a throwaway textarea
  // so the button still works over plain http and in older browsers.
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) { /* fall through */ }

  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:0;left:-9999px';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch (e) {
    return false;
  }
}

/* ---------------------------------------------------------------------------
   <bd-tabs> — tabs over child <section data-label="…"> panels.
   Until this upgrades, CSS shows every panel with its label as a heading, so
   no instruction is ever hidden behind JS that did not run.
   --------------------------------------------------------------------------- */
class BdTabs extends HTMLElement {
  connectedCallback() {
    if (this.dataset.ready) return;
    this.dataset.ready = '1';

    const panels = [...this.querySelectorAll(':scope > section')];
    if (panels.length < 2) return;

    const group = `bd-tabs-${++uid}`;
    const list = document.createElement('div');
    list.className = 'tablist';
    list.setAttribute('role', 'tablist');

    this.tabs = panels.map((panel, i) => {
      const tabId = `${group}-tab-${i}`;
      const panelId = `${group}-panel-${i}`;

      panel.id = panelId;
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tabId);
      panel.setAttribute('tabindex', '0');
      panel.hidden = i !== 0;

      const tab = document.createElement('button');
      tab.type = 'button';
      tab.className = 'tab';
      tab.id = tabId;
      tab.textContent = panel.dataset.label || `Option ${i + 1}`;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', panelId);
      tab.setAttribute('aria-selected', String(i === 0));
      tab.tabIndex = i === 0 ? 0 : -1;

      tab.addEventListener('click', () => this.select(i));
      tab.addEventListener('keydown', (e) => this.onKey(e, i));

      list.appendChild(tab);
      return tab;
    });

    this.panels = panels;
    this.prepend(list);
  }

  select(index, focus = false) {
    this.tabs.forEach((tab, i) => {
      const on = i === index;
      tab.setAttribute('aria-selected', String(on));
      tab.tabIndex = on ? 0 : -1;
      this.panels[i].hidden = !on;
    });
    if (focus) this.tabs[index].focus();
  }

  onKey(e, i) {
    const last = this.tabs.length - 1;
    const map = {
      ArrowRight: i === last ? 0 : i + 1,
      ArrowLeft: i === 0 ? last : i - 1,
      Home: 0,
      End: last,
    };
    if (!(e.key in map)) return;
    e.preventDefault();
    this.select(map[e.key], true);
  }
}

/* ---------------------------------------------------------------------------
   <bd-theme-toggle> — light/dark override on top of prefers-color-scheme.
   Hidden until defined, so no dead control appears if the module fails.
   --------------------------------------------------------------------------- */
class BdThemeToggle extends HTMLElement {
  connectedCallback() {
    if (this.dataset.ready) return;
    this.dataset.ready = '1';

    this.btn = document.createElement('button');
    this.btn.type = 'button';
    this.btn.addEventListener('click', () => {
      const next = this.current() === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('bd-theme', next); } catch (e) { /* private mode */ }
      this.render();
    });

    this.appendChild(this.btn);
    this.render();

    // Follow the system while the visitor has not chosen for themselves.
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', () => {
      if (!document.documentElement.dataset.theme) this.render();
    });
  }

  current() {
    const set = document.documentElement.dataset.theme;
    if (set) return set;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  render() {
    const dark = this.current() === 'dark';
    this.btn.textContent = dark ? '☀' : '☾';
    this.btn.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} theme`);
    this.btn.title = `Switch to ${dark ? 'light' : 'dark'} theme`;
  }
}

customElements.define('bd-code', BdCode);
customElements.define('bd-tabs', BdTabs);
customElements.define('bd-theme-toggle', BdThemeToggle);
