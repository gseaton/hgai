# Response Summary

## Question / Intent
The user asked how to install tools so that Claude (working via Claude Code in this repo) can work better with the project's HTML, JS, and CSS — i.e. what to set up to improve Claude's ability to see/test/lint the frontend (`ui/` directory).

## Answer / Recommendation
Two independent levers were identified, in priority order:

1. **Install the Claude in Chrome browser extension** (claude.ai/chrome, signed into the same account as this CLI session). This was the actual pain point hit in the prior session: `mcp__claude-in-chrome__tabs_context_mcp` reported "Browser extension is not connected," forcing a manual workaround — spinning up a local MongoDB + the hgai server and driving headless Chrome directly via the Chrome DevTools Protocol (a hand-written Python script using the `websockets` package) just to click through and screenshot the new Visualize tab. With the extension installed, Claude gets native click/type/screenshot/console-log/network access to the running app, which is a much faster and more reliable feedback loop for UI work than scripting CDP by hand.
2. **Add JS/CSS lint & format tooling** (optional, secondary): the repo has no `package.json` or ESLint/Prettier/Stylelint config for `ui/` — it's hand-written HTML/JS/CSS with no build step. Node 22 / npm are already installed on the machine, so ESLint + Prettier (JS) and Stylelint (CSS) could be added as dev dependencies to let Claude catch syntax/style issues automatically instead of relying on `node --check` plus manual review.

Recommendation given: install the Chrome extension first (bigger, one-time unlock); treat the lint tooling as optional and only add it if the user wants it, since it wasn't clear that was the intent.

## Key Points
- No mutating action was taken — this was purely informational; the user was asked whether they want the lint/format tooling actually set up.
- Verified before answering: no `package.json`, `.eslintrc*`, `.prettierrc*`, or `stylelint*` config exists anywhere in the repo (outside `node_modules`), and `node`/`npm`/`npx` are available on the machine (Node v22.22.1, npm 9.2.0).

## Context
In the immediately preceding session, the `mcp__claude-in-chrome__tabs_context_mcp` tool call failed with "Browser extension is not connected," which is what motivated this question and shaped the top recommendation.
