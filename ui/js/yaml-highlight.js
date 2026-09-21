/**
 * YAML syntax highlighter (no dependencies, no build step).
 *
 * Used for (1) ```yaml / ```yml / ```shql fenced code blocks rendered in Notes
 * (Browse and Preview) and Help topics, and (2) the YAML front-matter panel of
 * a Note. It is a line-oriented tokenizer, not a full YAML parser — enough to
 * colour real-world YAML correctly:
 *
 *   keys (plain, quoted, `rel:member`-style with colons), scalars by type
 *   (strings, numbers, booleans, null, ISO dates), comments (full-line and
 *   inline, never inside quotes), block scalars (`|` / `>`) whose content is
 *   shown as one string, flow collections (`[a, b]`, `{k: v}`, multi-line),
 *   anchors / aliases / tags, document markers, list dashes — and SHQL
 *   `?variables`, since SHQL queries are YAML.
 *
 * The output is HTML built from escaped text only, and stripping the tags and
 * unescaping always reproduces the input exactly (verified by
 * tests/js/test_yaml_highlight.js), so highlighting can never alter content.
 *
 * Token classes (styled in ui/css/hgai.css): yaml-key, yaml-str, yaml-num,
 * yaml-bool, yaml-null, yaml-date, yaml-var, yaml-anchor, yaml-tag,
 * yaml-punct, yaml-comment, yaml-doc.
 */
(function (root) {
  'use strict';

  const esc = s => String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const span = (cls, text) => (text === '' ? '' : `<span class="yaml-${cls}">${esc(text)}</span>`);

  const NUM_RE = /^(?:[-+]?(?:0|[1-9][\d_]*)(?:\.\d+)?(?:[eE][-+]?\d+)?|[-+]?\.\d+(?:[eE][-+]?\d+)?|0x[0-9a-fA-F]+|0o[0-7]+|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$/;
  const BOOL_RE = /^(?:true|false|True|False|TRUE|FALSE|yes|no|Yes|No|YES|NO|on|off|On|Off|ON|OFF)$/;
  const NULL_RE = /^(?:null|Null|NULL|~)$/;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}(?:[Tt ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:[ \t]*(?:Z|[-+]\d{2}(?::?\d{2})?))?)?$/;

  // A mapping key: quoted, or plain text up to a `:` that is followed by
  // whitespace or end of line (so `rel:member: x` and URLs in list items work).
  const KEY_RE = /^((?:"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s#'"\[\]{},&*!|>%@`](?:[^:#]|:(?![ \t]|$))*?))([ \t]*):(?=[ \t]|$)/;
  const BLOCK_SCALAR_RE = /^([|>][+-]?\d*[+-]?)([ \t]*(?:#.*)?)$/;

  function scalarClass(text) {
    if (NULL_RE.test(text)) return 'null';
    if (BOOL_RE.test(text)) return 'bool';
    if (NUM_RE.test(text)) return 'num';
    if (DATE_RE.test(text)) return 'date';
    return 'str';
  }

  // End index (exclusive) of the quoted scalar starting at `start`.
  function quotedEnd(text, start) {
    const q = text[start];
    let i = start + 1;
    while (i < text.length) {
      if (q === '"' && text[i] === '\\') { i += 2; continue; }
      if (text[i] === q) {
        if (q === "'" && text[i + 1] === "'") { i += 2; continue; }   // '' escapes a quote
        return i + 1;
      }
      i++;
    }
    return text.length;                                              // unterminated on this line
  }

  // Tokenize the value part of a line. `st.flow` carries the flow-collection
  // nesting depth across tokens and lines.
  function tokens(text, st) {
    let out = '';
    let i = 0;
    const n = text.length;
    while (i < n) {
      const ch = text[i];
      if (ch === ' ' || ch === '\t') {
        let j = i;
        while (j < n && (text[j] === ' ' || text[j] === '\t')) j++;
        out += text.slice(i, j);
        i = j;
        continue;
      }
      if (ch === '#' && (i === 0 || /\s/.test(text[i - 1]))) {       // inline comment
        out += span('comment', text.slice(i));
        break;
      }
      if (ch === '"' || ch === "'") {
        const end = quotedEnd(text, i);
        const raw = text.slice(i, end);
        const isKey = st.flow > 0 && /^[ \t]*:(?:[ \t]|$|[,\]}])/.test(text.slice(end));
        out += span(isKey ? 'key' : 'str', raw);
        i = end;
        continue;
      }
      if (ch === '[' || ch === '{') { st.flow++; out += span('punct', ch); i++; continue; }
      if ((ch === ']' || ch === '}') && st.flow > 0) { st.flow--; out += span('punct', ch); i++; continue; }
      if (ch === ',' && st.flow > 0) { out += span('punct', ch); i++; continue; }
      if (ch === ':' && st.flow > 0 && (i + 1 >= n || /[\s,\]}]/.test(text[i + 1]))) {
        out += span('punct', ch);
        i++;
        continue;
      }
      const rest = text.slice(i);
      let m;
      if ((m = /^[&*][^\s,\[\]{}]+/.exec(rest))) { out += span('anchor', m[0]); i += m[0].length; continue; }
      if ((m = /^!\S*/.exec(rest))) { out += span('tag', m[0]); i += m[0].length; continue; }
      if ((m = /^\?[A-Za-z_][\w.\-]*/.exec(rest))) { out += span('var', m[0]); i += m[0].length; continue; }

      // plain scalar
      let j = i;
      if (st.flow > 0) {
        while (j < n) {
          const c = text[j];
          if (c === ',' || c === ']' || c === '}') break;
          if (c === ':' && (j + 1 >= n || /[\s,\]}]/.test(text[j + 1]))) break;
          if (c === '#' && j > 0 && /\s/.test(text[j - 1])) break;
          j++;
        }
      } else {
        while (j < n && !(text[j] === '#' && j > 0 && /\s/.test(text[j - 1]))) j++;
      }
      if (j === i) j = i + 1;                                         // always make progress
      const raw = text.slice(i, j);
      const trimmed = raw.replace(/\s+$/, '');
      const trail = raw.slice(trimmed.length);
      const isKey = st.flow > 0 && text[j] === ':';
      out += span(isKey ? 'key' : scalarClass(trimmed), trimmed) + trail;
      i = j;
    }
    return out;
  }

  function highlightLine(line, st) {
    const ws = line.match(/^[ \t]*/)[0];
    const indent = ws.length;

    if (st.block !== null) {                                           // inside a | or > block scalar
      if (!line.trim() || indent > st.block) return span('str', line);
      st.block = null;
    }
    if (line.trim() === '') return line;
    if (st.flow > 0) return ws + tokens(line.slice(indent), st);      // continuation of a multi-line flow collection

    let rest = line.slice(indent);
    let out = ws;
    if (rest[0] === '#') return out + span('comment', rest);
    if (/^(?:---|\.\.\.)(?:[ \t]|$)/.test(rest)) {                    // document markers
      return out + span('doc', rest.slice(0, 3)) + tokens(rest.slice(3), st);
    }
    let m;
    while ((m = /^-([ \t]+|$)/.exec(rest))) {                          // list dashes (possibly nested)
      out += span('punct', '-') + m[1];
      rest = rest.slice(m[0].length);
      if (!rest) return out;
    }
    const km = KEY_RE.exec(rest);
    if (km) {
      out += span('key', km[1]) + km[2] + span('punct', ':');
      rest = rest.slice(km[0].length);
      const gap = rest.match(/^[ \t]*/)[0];
      out += gap;
      rest = rest.slice(gap.length);
    }
    const bm = BLOCK_SCALAR_RE.exec(rest);
    if (bm) {
      st.block = indent;
      return out + span('punct', bm[1]) + tokens(bm[2], st);
    }
    return out + tokens(rest, st);
  }

  /** YAML text → HTML (escaped, spans only). */
  function highlightYaml(text) {
    const st = { flow: 0, block: null };
    return String(text).split(/\r?\n/).map(line => highlightLine(line, st)).join('\n');
  }

  /**
   * Like highlightYaml, but each line is wrapped in `<span class="yaml-line" data-ln="N">`
   * so CSS can draw a non-selectable line-number gutter (used by the Media file
   * preview). Newlines stay real characters inside the <pre>, so copy/paste is
   * unchanged and the text round-trips exactly.
   */
  function highlightYamlNumbered(text) {
    return highlightYaml(text).split('\n')
      .map((html, i) => `<span class="yaml-line" data-ln="${i + 1}">${html}</span>`)
      .join('\n');
  }

  /**
   * Highlight every ```yaml / ```yml / ```shql code block (rendered by marked
   * as <pre><code class="language-yaml">) inside `container`. Content comes
   * from textContent and is re-escaped, so nothing can be injected.
   */
  function highlightYamlBlocks(container) {
    container.querySelectorAll('pre > code').forEach(code => {
      if (!/(?:^|\s)language-(?:ya?ml|shql)(?:\s|$)/.test(code.className)) return;
      code.innerHTML = highlightYaml(code.textContent);
      code.classList.add('yaml-highlighted');
    });
  }

  // Is this media file YAML? By content type (application/yaml, application/x-yaml,
  // text/yaml, text/x-yaml, text/vnd.yaml) or — because browsers often upload
  // .yml/.yaml with a generic type — by file extension when the stored type is
  // generic (octet-stream, text/plain, none).
  const YAML_MEDIA_TYPE_RE = /^(?:application|text)\/(?:x-|vnd\.)?ya?ml$/i;
  const GENERIC_MEDIA_TYPE_RE = /^(?:application\/octet-stream|binary\/octet-stream|text\/plain)?$/i;
  function isYamlMedia(contentType, filename) {
    const ct = (contentType || '').split(';')[0].trim();
    if (YAML_MEDIA_TYPE_RE.test(ct)) return true;
    return GENERIC_MEDIA_TYPE_RE.test(ct) && /\.ya?ml$/i.test(filename || '');
  }

  const api = { highlightYaml, highlightYamlNumbered, highlightYamlBlocks, isYamlMedia };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;   // node (tests)
  root.highlightYaml = highlightYaml;
  root.highlightYamlNumbered = highlightYamlNumbered;
  root.highlightYamlBlocks = highlightYamlBlocks;
  root.isYamlMedia = isYamlMedia;
})(typeof window !== 'undefined' ? window : globalThis);
