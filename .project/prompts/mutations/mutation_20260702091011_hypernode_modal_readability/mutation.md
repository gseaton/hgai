# Mutation Log

## Modified
- **ui/index.html** — Removed all `<i class="bi bi-...">` icon elements from the four node-modal section headers (Identity, Classification, Temporal Validity, Attributes). Headers are now plain text with inline hints where applicable.
- **ui/css/hgai.css** — Updated `.node-form-section-header` to use `font-weight: 800`, `font-size: 0.72rem`, and `color: #374151` (near-black) instead of the previous grey. Removed the now-unused `.node-form-section-header i` rule. Added `#modal-node .form-label` rule setting `font-weight: 600` and `color: #111827` to bold all field labels inside the node modal.
