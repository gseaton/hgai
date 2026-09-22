# Mutation Summary

## Intent
Replace the placeholder "h_AI" text-in-a-box logo in the sidebar's upper-left corner with the real logo artwork already present at `ui/logo.png`, without changing its size or position.

## Context
Two separate "h_AI" placeholder marks exist in the UI: the sidebar brand mark (`.brand-mark`, 32×32px, upper-left, always visible in the app shell) and a larger centered one on the login screen (`.hgai-logo-mark`, 72×72px). The request named the "upper-left" one specifically, so only the sidebar mark was changed; the login-screen logo was left as-is since it wasn't in scope.

## What Changed and Why
The sidebar mark was a `<span>` styled as a colored square with "h_AI" text via CSS (background color, font-weight, a `<sub>` for the "AI"). It was swapped for an `<img>` pointing at `/ui/logo.png` (already served — confirmed `200 image/png` from the running server), and `.brand-mark`'s CSS was reduced to just the sizing/shape rule (32×32px, 8px border-radius, `object-fit: contain` so the square 256×256 source scales cleanly without distortion or cropping) — dropping the now-inapplicable background/font/color declarations. The `.collapsed` sidebar state was checked and doesn't touch `.brand-mark` (it only hides the adjacent text spans), so the logo stays visible and correctly sized whether the sidebar is expanded or collapsed.

## Key Decisions
- **Only the sidebar mark, not the login-screen logo** — the user said "upper-left," which is unambiguously the sidebar brand mark; the login screen's centered logo is a different element at a different size and wasn't mentioned.
- **`object-fit: contain` over `cover`** — the source image is a perfect square (256×256) matching the target's aspect ratio, so either would look identical here; `contain` was chosen defensively in case the logo asset is ever swapped for a non-square image later.
- **Verified live in Chrome**: confirmed via a zoomed screenshot that the logo renders at the correct 32×32 size in the same rounded-square slot the placeholder occupied, confirmed no console errors (which would include a broken-image load failure), and confirmed via a direct request that the server serves `/ui/logo.png` with `200 image/png`. Full test suite still passes (440 passed; this is a static-asset/CSS change with no test coverage of its own).
