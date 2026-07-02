# Mutation Summary

## Intent
Improve text readability in the Hypernode Editor modal by removing decorative icons from section headers and increasing the visual weight of both section headers and field labels through bolding.

## Context
The previous redesign added Bootstrap Icons to section headers. The user found the icons unnecessary and wanted cleaner, bolder text instead. The changes are purely typographic — no layout or ID changes.

## What Changed and Why
- **Icons removed**: The `<i class="bi bi-...">` elements were stripped from all four section headers (Identity, Classification, Temporal Validity, Attributes). Headers now read as plain uppercase text, which is more scannable without visual noise.
- **Section headers darkened and heavier**: `color` changed from `#9ca3af` (light grey) to `#374151` (dark grey/near-black) and `font-weight` raised from 700 to 800. The slightly larger `font-size: 0.72rem` (from 0.685rem) improves legibility at small sizes.
- **Field labels bolded**: Added `#modal-node .form-label { font-weight: 600; color: #111827; }` so every label inside the node modal appears bold and near-black, providing clear contrast against the form inputs below.
- The unused `.node-form-section-header i` CSS rule was removed along with the icons.
