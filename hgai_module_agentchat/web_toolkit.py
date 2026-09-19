"""Web access for the chat agent: fetch a single URL and return its cleaned,
readable text content.

A dedicated custom Agno Toolkit (same reasoning as HgaiMcpToolkit — a small,
purpose-built tool beats pulling in a heavier off-the-shelf option): Agno
ships `agno.tools.website.WebsiteTools`, but its `read_url()` defaults to
crawling up to `max_depth=3` / `max_links=10` pages per call — a surprising
amount of unbounded work and token cost for what a chat user expects to be
"read this one page". This toolkit fetches exactly the one URL asked for.

Security: this fetch runs server-side on the agent's behalf, and the URL can
originate from an LLM tool call (which may itself have been influenced by
content the model already read from a *previous* untrusted web page — classic
prompt-injection-to-SSRF chaining). `_is_safe_url` blocks the request-side
mitigation: only http(s) schemes, and the resolved IP (checked at the initial
host AND at every redirect hop, not just the first) must not be
loopback/private/link-local/reserved/multicast — closing off the common
"fetch http://169.254.169.254/..." or "fetch http://localhost:8357/..."
SSRF patterns. This is a network-reachability guard, not a content-trust
guarantee: the fetched page's text is still untrusted data handed to the
model like any tool result, never instructions to follow.
"""

import asyncio
import ipaddress
import socket
from typing import List, Tuple
from urllib.parse import urlparse

import httpx
from agno.tools import Toolkit

MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2MB — plenty for an HTML page, not a video/binary
MAX_TEXT_CHARS = 12000  # keeps one fetch from dominating the model's context/cost
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 15.0
USER_AGENT = "HypergraphAI-Agent/1.0 (+web_fetch tool)"


async def _resolve_ips(hostname: str) -> List[str]:
    def _do_resolve() -> List[str]:
        infos = socket.getaddrinfo(hostname, None)
        return sorted({info[4][0] for info in infos})

    return await asyncio.to_thread(_do_resolve)


def _is_blocked_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


async def _check_url_safety(url: str) -> Tuple[bool, str]:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported URL scheme '{parsed.scheme}' — only http/https are allowed"
    if not parsed.hostname:
        return False, "URL has no hostname"

    try:
        ips = await _resolve_ips(parsed.hostname)
    except socket.gaierror as e:
        return False, f"Could not resolve host '{parsed.hostname}': {e}"

    if not ips:
        return False, f"Could not resolve host '{parsed.hostname}'"
    for ip in ips:
        if _is_blocked_ip(ip):
            return False, f"Refusing to fetch '{parsed.hostname}' — resolves to a private/internal address ({ip})"
    return True, ""


def _extract_text_from_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "svg"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)

    return f"# {title}\n\n{cleaned}" if title else cleaned


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[... truncated, {len(text) - limit} more characters not shown ...]"


class HgaiWebToolkit(Toolkit):
    """Gives the chat agent the ability to fetch and read a web page."""

    def __init__(self, **kwargs):
        super().__init__(name="hgai_web", tools=[self.web_fetch], **kwargs)

    async def web_fetch(self, url: str) -> str:
        """Fetch a web page and return its readable text content.

        Use this to read the contents of a specific URL — e.g. one the user
        pasted, or one found in a hypergraph's node/edge attributes. Follows
        redirects (each hop is safety-checked). Only a single page is
        fetched — it does not crawl links found on the page.

        Args:
            url: The full http(s) URL to fetch.

        Returns:
            The page's cleaned, readable text (HTML is stripped of markup/
            scripts/styles), truncated if very long. For non-HTML content
            (JSON, plain text), the raw text is returned. Returns a short
            error message instead of raising if the URL is invalid,
            unreachable, or points at a private/internal address.
        """
        current_url = url
        async with httpx.AsyncClient(follow_redirects=False, timeout=REQUEST_TIMEOUT) as client:
            for _ in range(MAX_REDIRECTS + 1):
                safe, reason = await _check_url_safety(current_url)
                if not safe:
                    return f"Error: {reason}"

                try:
                    async with client.stream(
                        "GET", current_url, headers={"User-Agent": USER_AGENT}
                    ) as resp:
                        if resp.is_redirect:
                            next_url = resp.headers.get("location")
                            if not next_url:
                                return f"Error: redirect from {current_url} had no Location header"
                            current_url = httpx.URL(current_url).join(next_url).human_repr()
                            continue

                        content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                        body = bytearray()
                        async for chunk in resp.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > MAX_RESPONSE_BYTES:
                                return f"Error: response from {current_url} exceeded the {MAX_RESPONSE_BYTES // (1024*1024)}MB size limit"

                        if resp.status_code >= 400:
                            return f"Error: {current_url} returned HTTP {resp.status_code}"

                        text = bytes(body).decode(resp.encoding or "utf-8", errors="replace")
                        if content_type in ("text/html", "application/xhtml+xml"):
                            return _truncate(_extract_text_from_html(text))
                        if content_type.startswith("text/") or content_type in ("application/json",):
                            return _truncate(text)
                        return f"Error: unsupported content type '{content_type}' at {current_url} — only HTML/text/JSON pages can be read"
                except httpx.RequestError as e:
                    return f"Error: could not fetch {current_url}: {e}"

            return f"Error: too many redirects fetching {url}"
