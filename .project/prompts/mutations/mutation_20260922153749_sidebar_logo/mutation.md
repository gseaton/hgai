# Mutation Log

## Modified
- **ui/index.html** — The sidebar brand mark (`.sidebar-brand`, upper-left corner) now renders `<img class="brand-mark" src="/ui/logo.png" alt="HypergraphAI"/>` instead of the CSS-drawn `<span class="brand-mark">h<sub>AI</sub></span>` placeholder.
- **ui/css/hgai.css** — `.brand-mark` changed from a 32×32px colored box with "h_AI" text (`display: inline-flex`, background, font styling) to a 32×32px `<img>` rule (`object-fit: contain`, same `border-radius: 8px`, same `flex-shrink: 0`) — identical footprint, now showing the actual logo image. Removed the now-unused `.brand-mark sub` rule.
