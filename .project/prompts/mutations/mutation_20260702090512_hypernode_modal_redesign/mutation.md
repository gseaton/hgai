# Mutation Log

## Modified
- **ui/index.html** — Replaced the flat `#modal-node` form body with a structured layout: a new header with an icon badge and subtitle, four labeled form sections (Identity, Classification, Temporal Validity, Attributes) with visual dividers, description moved into the Identity section, Valid From/To placed side-by-side in a dedicated section (removing the broken `offset-md-3` layout), and a cleaner footer. All element IDs preserved unchanged.
- **ui/css/hgai.css** — Added global `.modal-content` enhancement (rounded corners + elevated shadow) and a full set of scoped node-modal classes: `.node-modal-header`, `.modal-entity-badge`, `.modal-entity-badge-node`, `.modal-entity-subtitle`, `.node-form-section`, `.node-form-section-header`, `.node-form-section-hint`, `.node-form-section-last`, `.node-graph-display-field`, `.node-attributes-editor` (dark code theme), and `.node-modal-footer`.
