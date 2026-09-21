// Tests for ui/js/yaml-highlight.js — run with:  node tests/js/test_yaml_highlight.js
// (tests/test_yaml_highlight_js.py runs this under pytest when node is installed.)
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { highlightYaml, highlightYamlNumbered, isYamlMedia } = require('../../ui/js/yaml-highlight.js');

const unescape = s => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
const plain = html => unescape(html.replace(/<\/?span[^>]*>/g, ''));
const spans = html => [...html.matchAll(/<span class="yaml-([a-z]+)">([^<]*)<\/span>/g)].map(m => [m[1], unescape(m[2])]);
const has = (html, cls, text) => spans(html).some(([c, t]) => c === cls && t === text);
let passed = 0;
const test = (name, fn) => { fn(); passed++; };

test('keys, scalars by type, comments', () => {
  const h = highlightYaml('name: Moe  # inline\nage: 49\nrate: -3.5e2\nok: true\nnothing: null\ntilde: ~\nwhen: 2026-09-21T04:35:58Z\n');
  assert(has(h, 'key', 'name') && has(h, 'str', 'Moe') && has(h, 'comment', '# inline'));
  assert(has(h, 'num', '49') && has(h, 'num', '-3.5e2') && has(h, 'bool', 'true'));
  assert(has(h, 'null', 'null') && has(h, 'null', '~') && has(h, 'date', '2026-09-21T04:35:58Z'));
});
test('quoted strings and # inside quotes are not comments', () => {
  const h = highlightYaml('a: "x # not a comment"\nb: \'it\'\'s ok\'\nc: "esc \\" quote" # real comment\n');
  assert(has(h, 'str', '"x # not a comment"') && has(h, 'str', "'it''s ok'") && has(h, 'str', '"esc \\" quote"'));
  assert(has(h, 'comment', '# real comment'));
});
test('keys with colons, quoted keys, URLs in list items', () => {
  const h = highlightYaml('rel:member: yes\n"quoted key": 1\n- http://example.org/x\n- name: v\n');
  assert(has(h, 'key', 'rel:member') && has(h, 'key', '"quoted key"'));
  assert(has(h, 'str', 'http://example.org/x'), 'URL list item is a string, not key/value');
  assert(has(h, 'key', 'name'));
});
test('block scalars keep colons and keys inside as one string', () => {
  const h = highlightYaml('source_prompt: |\n  Who is: the mother?\n  key: value\nnext: 1\n');
  assert(has(h, 'punct', '|') && has(h, 'str', '  Who is: the mother?') && has(h, 'str', '  key: value'));
  assert(has(h, 'key', 'next') && has(h, 'num', '1'));
  const list = highlightYaml('- |\n  text: not a key\n- x\n');
  assert(has(list, 'str', '  text: not a key'));
});
test('flow collections, including multi-line', () => {
  const h = highlightYaml('tags: [a, "b c", 3]\nobj: { k: v, n: 1 }\nseq: [\n  one,\n  two\n]\n');
  assert(has(h, 'punct', '[') && has(h, 'punct', ']') && has(h, 'punct', ',') && has(h, 'str', 'a') && has(h, 'num', '3'));
  assert(has(h, 'key', 'k') && has(h, 'str', 'v') && has(h, 'key', 'n'));
  assert(has(h, 'str', 'one') && has(h, 'str', 'two'));
  const block = highlightYaml('where: a, b, c\n');
  assert(has(block, 'str', 'a, b, c'), 'commas in a block-context plain scalar are text');
});
test('anchors, aliases, tags, document markers', () => {
  const h = highlightYaml('---\nbase: &b {x: 1}\ncopy: *b\nn: !!str 12\n...\n');
  assert(has(h, 'doc', '---') && has(h, 'doc', '...') && has(h, 'anchor', '&b') && has(h, 'anchor', '*b') && has(h, 'tag', '!!str'));
});
test('SHQL variables', () => {
  const h = highlightYaml('select:\n  - ?person.id\n  - ?e.attributes.born\nwhere:\n  - node:\n      bind: ?person\n      id: ?member_id\n');
  ['?person.id', '?e.attributes.born', '?person', '?member_id'].forEach(v => assert(has(h, 'var', v), v));
  assert(has(h, 'key', 'bind') && has(h, 'key', 'select'));
});
test('a SHQL filter string stays a string', () => {
  const h = highlightYaml('- filter: "CONTAINS(?p.description, \'Howard\')"\n');
  assert(has(h, 'key', 'filter') && has(h, 'str', '"CONTAINS(?p.description, \'Howard\')"'));
});
test('HTML in content is escaped', () => {
  const h = highlightYaml('x: <script>alert(1)</script> & "q"\n');
  assert(!/<script/i.test(h) && h.includes('&lt;script&gt;'));
});
test('edge cases do not throw or loop', () => {
  for (const s of ['', '\n\n', ':', '-', '- - -', '"unterminated', "'x", '[', ']', '{', '}', ', ,', '# only comment', 'a: [', 'a: ]', 'a:b:c', '?', '&', '*', '!', '|', '>', 'k: |', 'k: >-\n  x', '\t\tindented\ttab', 'a: b #c #d'])
    assert.strictEqual(plain(highlightYaml(s)), s, JSON.stringify(s));
});

test('numbered variant: one span per line, numbers in data-ln, text unchanged', () => {
  const src = 'a: 1\n\n# c\n- x: "y"\n';
  const h = highlightYamlNumbered(src);
  assert.strictEqual(plain(h), src);
  const nums = [...h.matchAll(/class="yaml-line" data-ln="(\d+)"/g)].map(m => Number(m[1]));
  assert.deepStrictEqual(nums, [1, 2, 3, 4, 5]);
});
test('isYamlMedia: content types, generic types by extension, and non-YAML', () => {
  ['application/yaml', 'application/x-yaml', 'text/yaml', 'text/x-yaml', 'text/vnd.yaml', 'application/x-yaml; charset=utf-8'].forEach(t => assert(isYamlMedia(t, 'x.bin'), t));
  ['application/octet-stream', 'text/plain', '', null, undefined].forEach(t => {
    assert(isYamlMedia(t, 'graph.export.yml') && isYamlMedia(t, 'A.YAML'), String(t));
    assert(!isYamlMedia(t, 'notes.txt') && !isYamlMedia(t, 'yaml') && !isYamlMedia(t, undefined), String(t));
  });
  ['image/png', 'video/mp4', 'application/json', 'application/pdf'].forEach(t => assert(!isYamlMedia(t, 'thing.yml'), `${t} must not be treated as YAML by extension`));
});

// Round trip: the highlighter must never change the text, for every ```yaml
// block in the repository's docs (README, Help topics, decks, notes).
function* mdFiles(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['node_modules', '.git', '.venv', '__pycache__', '.project'].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* mdFiles(p);
    else if (e.name.endsWith('.md')) yield p;
  }
}
test('round trip over every yaml block in the repo docs', () => {
  const root = path.join(__dirname, '..', '..');
  let blocks = 0;
  for (const f of mdFiles(root)) {
    const text = fs.readFileSync(f, 'utf8');
    for (const m of text.matchAll(/```(?:ya?ml|shql)\n([\s\S]*?)```/g)) {
      blocks++;
      assert.strictEqual(plain(highlightYaml(m[1])), m[1], `${path.relative(root, f)}: block changed by highlighting`);
    }
  }
  assert(blocks > 50, `expected many yaml blocks, found ${blocks}`);
  console.log(`  round-tripped ${blocks} yaml blocks`);
});

console.log(`yaml-highlight: ${passed} tests passed`);
