# Mutation Log

## Modified
- **ui/css/hgai.css** — Extended the existing task-list bullet-suppression rule (`.note-preview-pane li:has(> input[type="checkbox"])`) with a second selector arm, `li:has(> p > input[type="checkbox"])`, and extended the matching checkbox-margin rule the same way. This covers GFM "loose" lists (any blank line adjacent to any item makes marked wrap the *entire* list's item content in `<p>`, per the CommonMark/GFM spec), where the checkbox becomes a grandchild of `<li>` rather than a direct child, which the original direct-child-only selector missed.
