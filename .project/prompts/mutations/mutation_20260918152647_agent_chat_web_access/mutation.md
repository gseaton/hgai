# Mutation Log

## Created
- **hgai_module_agentchat/web_toolkit.py** — `HgaiWebToolkit(agno.tools.Toolkit)` exposing one tool, `web_fetch(url)`, that fetches a single web page and returns its cleaned, readable text (HTML stripped of script/style/nav/header/footer, truncated to 12,000 characters). Includes SSRF protection: `_check_url_safety()` restricts to http/https schemes and resolves the hostname, rejecting loopback/private/link-local/reserved/multicast/unspecified addresses (via Python's stdlib `ipaddress` — no new dependency for this part); the safety check re-runs at every redirect hop (up to 5), not just the initial URL, closing the standard "safe URL that 302s to an internal address" bypass. Also caps response size at 2MB and rejects non-HTML/text/JSON content types with a clear message instead of dumping binary data into the model's context.
- **tests/test_web_toolkit.py** — 24 tests: IP-classification table (loopback/private/link-local/metadata-address/IPv6-equivalents all blocked; public IPs allowed), URL-safety checks with DNS resolution mocked (scheme rejection, no-hostname rejection, private-IP-resolution rejection, DNS-failure-is-unsafe, public-hostname-allowed), HTML text extraction (script/style/nav/footer stripped, title extracted, no-title case), truncation, and toolkit tool registration.

## Modified
- **hgai_module_agentchat/engine.py** — `build_agent()` now attaches `HgaiWebToolkit()` alongside the existing `HgaiMcpToolkit` in the Agent's `tools=[...]` list, so every chat turn has both the resident-hypergraph-MCP tools and the new web-fetch tool available.
- **pyproject.toml**, **requirements.txt** — Added `beautifulsoup4` (pinned to the installed `4.15.0` in requirements.txt), used only for the HTML-to-text extraction in `web_toolkit.py`. Chosen deliberately over Agno's own built-in `agno.tools.website.WebsiteTools` — its `read_url()` defaults to crawling up to `max_depth=3`/`max_links=10` pages per call, an unbounded amount of work/token cost for what a chat user expects to be "read this one page"; the custom toolkit fetches exactly the one URL asked for.

No files were deleted.
