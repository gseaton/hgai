# Mutation Summary

## Intent
Fix a rendering bug in the Notes feature's Markdown display: a GFM-style task list item (`- [ ] todo` / `- [x] done`) rendered with both a checkbox AND the browser's normal disc bullet stacked next to each other, when only the checkbox should show.

## Context
Before touching anything, the actual HTML `marked.parse()` produces for a task list was inspected directly in the browser (`marked.parse("- [ ] foo\n- [x] bar\n- plain\n")`), since the root cause needed to be confirmed rather than assumed. It turned out `marked@12.0.2`'s default output is a bare `<li><input type="checkbox" disabled> foo</li>` — critically, with no distinguishing class on the `<li>` or the surrounding `<ul>` at all (unlike GitHub's own renderer, which adds a `task-list-item`/`contains-task-list` class specifically so its stylesheet can target it). Every browser's default `<ul>` styling puts a bullet marker on every `<li>` regardless of what's inside it, so without a way to select "only the `<li>`s that are task items," the checkbox and the bullet both rendered side by side. `DOMPurify.sanitize()` (the XSS-safety layer already in front of every rendered note) was also confirmed to pass the checkbox `<input>` through unmodified, so it wasn't a contributing factor.

## What Changed and Why
Since there's no class to hook a selector onto, the fix uses the CSS `:has()` relational selector (confirmed supported in this environment via `CSS.supports()`) to target exactly the `<li>` elements whose direct child is a checkbox `input`, and only those — `li:has(> input[type="checkbox"])` — removing their `list-style-type` while leaving every other list item's bullet untouched. A small negative margin on the checkbox itself pulls it into the space the removed bullet vacated, so the checkbox sits where a bullet normally would rather than reading as extra-indented — the same visual treatment GitHub's own task-list CSS applies for the identical reason.

This was scoped under `.note-preview-pane`, the shared class both of this feature's two rendered-content surfaces already use (Browse mode's `#note-browse-content` and Preview mode's `#note-preview`), so one CSS change fixes the bug everywhere task lists can appear in a note, without needing to touch either surface individually.

## Key Decisions
- **A CSS-only fix, not a change to the Markdown rendering pipeline** — the underlying `marked.parse()` output itself is standard, unmodified GFM task-list HTML; nothing about the rendering logic (placeholder substitution for `note:`/`media:` links, DOMPurify sanitization) needed to change. The bug was purely presentational, so the fix stayed purely presentational.
- **`:has()` over a JS-based post-processing pass** — an alternative would have been to walk the rendered DOM after `marked.parse()`/`DOMPurify.sanitize()` and tag task-item `<li>`s with a class manually, mirroring what GitHub's renderer does server-side. `:has()` accomplishes the identical targeting declaratively, with no additional JS and no risk of that walk interacting awkwardly with the existing `note:`/`media:` placeholder-substitution step; confirmed supported before committing to it rather than assumed.

## Live Verification Performed
Started an isolated test server and seeded a note whose text mixed two task-list items (one unchecked, one checked) with one ordinary bullet item. Confirmed in the browser, in both Browse mode (the default view) and Preview mode: the unchecked task shows only an empty checkbox, the checked task shows only a filled/checked checkbox, and the plain bullet item is completely unaffected, still showing its normal disc marker — a zoomed screenshot confirmed no bullet artifact remains next to either checkbox.

Test server killed and `hgai_notes_tasklist_verify` database dropped afterward. Full test suite: 84 passed, same 3 pre-existing unrelated `test_mesh.py` failures — this is a CSS-only change with no backend or JS logic touched.
