"""Tests for the chat agent's web-fetch tool (hgai_module_agentchat.web_toolkit).

Pure-logic tests only — HTML extraction/truncation, and the SSRF-guard
classification logic — with DNS resolution mocked. The actual network fetch
(`HgaiWebToolkit.web_fetch`) is verified live against the running server;
see the mutation history for that verification, following the same
convention already used for other network-touching code in this project.
"""

from unittest.mock import patch

import pytest

from hgai_module_agentchat.web_toolkit import (
    HgaiWebToolkit,
    _check_url_safety,
    _extract_text_from_html,
    _is_blocked_ip,
    _truncate,
)


# ─── IP classification ──────────────────────────────────────────────────────

@pytest.mark.parametrize("ip", [
    "127.0.0.1", "127.0.0.53",       # loopback
    "10.0.0.1", "172.16.0.1", "192.168.1.1",  # RFC1918 private
    "169.254.169.254",               # link-local / cloud metadata
    "0.0.0.0",                       # unspecified
    "::1",                           # IPv6 loopback
    "fc00::1",                       # IPv6 unique local (private)
    "fe80::1",                       # IPv6 link-local
])
def test_blocked_ips(ip):
    assert _is_blocked_ip(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_allowed_public_ips(ip):
    assert _is_blocked_ip(ip) is False


# ─── URL safety (DNS resolution mocked) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_rejects_non_http_scheme():
    safe, reason = await _check_url_safety("file:///etc/passwd")
    assert safe is False
    assert "scheme" in reason


@pytest.mark.asyncio
async def test_rejects_url_with_no_hostname():
    safe, reason = await _check_url_safety("http://")
    assert safe is False


@pytest.mark.asyncio
async def test_blocks_hostname_resolving_to_private_ip():
    with patch("hgai_module_agentchat.web_toolkit._resolve_ips", return_value=["169.254.169.254"]):
        safe, reason = await _check_url_safety("http://metadata.internal/latest/meta-data")
        assert safe is False
        assert "private/internal" in reason


@pytest.mark.asyncio
async def test_blocks_localhost_by_name():
    with patch("hgai_module_agentchat.web_toolkit._resolve_ips", return_value=["127.0.0.1"]):
        safe, reason = await _check_url_safety("http://localhost:8357/api/v1/agent/vendors")
        assert safe is False


@pytest.mark.asyncio
async def test_allows_public_hostname():
    with patch("hgai_module_agentchat.web_toolkit._resolve_ips", return_value=["93.184.216.34"]):
        safe, reason = await _check_url_safety("https://example.com/")
        assert safe is True
        assert reason == ""


@pytest.mark.asyncio
async def test_dns_failure_is_not_safe():
    import socket
    with patch("hgai_module_agentchat.web_toolkit._resolve_ips", side_effect=socket.gaierror("nope")):
        safe, reason = await _check_url_safety("https://this-does-not-resolve.invalid/")
        assert safe is False


# ─── HTML text extraction ───────────────────────────────────────────────────

def test_extract_text_strips_script_and_style():
    html = """
    <html><head><title>Test Page</title>
    <style>.a{color:red}</style></head>
    <body>
      <script>alert('x')</script>
      <nav>Home | About</nav>
      <h1>Hello</h1>
      <p>Some real content here.</p>
      <footer>copyright 2026</footer>
    </body></html>
    """
    text = _extract_text_from_html(html)
    assert "# Test Page" in text
    assert "Hello" in text
    assert "Some real content here." in text
    assert "alert" not in text
    assert "color:red" not in text
    assert "Home | About" not in text
    assert "copyright" not in text


def test_extract_text_without_title():
    html = "<html><body><p>No title here.</p></body></html>"
    text = _extract_text_from_html(html)
    assert text.strip() == "No title here."


# ─── Truncation ──────────────────────────────────────────────────────────────

def test_truncate_short_text_unchanged():
    assert _truncate("short", limit=100) == "short"


def test_truncate_long_text_adds_note():
    text = "x" * 200
    truncated = _truncate(text, limit=50)
    assert truncated.startswith("x" * 50)
    assert "truncated" in truncated
    assert "150 more characters" in truncated


# ─── Toolkit registration ────────────────────────────────────────────────────

def test_toolkit_registers_web_fetch_tool():
    toolkit = HgaiWebToolkit()
    assert toolkit.name == "hgai_web"
    assert "web_fetch" in toolkit.get_async_functions()
