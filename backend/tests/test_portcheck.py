"""Tests for snihunter.portcheck — TCP connect port probe.

Uses a real localhost listener (no mock) for the open-port case and a
closed port for the closed-port case. The MAX_PORTS_PER_HOST cap is also
unit-tested.
"""
from __future__ import annotations

import asyncio
import socket

import pytest

from snihunter.portcheck import (
    DEFAULT_PORTS,
    MAX_PORTS_PER_HOST,
    check_ports,
    probe_port,
)


def _find_free_port() -> int:
    """Get an OS-assigned free port (opened and immediately closed)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def listening_port():
    """A port with a real TCP listener bound to it for the duration of the test."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    yield port
    s.close()


# ── probe_port ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_port_open(listening_port):
    assert await probe_port("127.0.0.1", listening_port, timeout=2.0) is True


@pytest.mark.asyncio
async def test_probe_port_closed():
    # Use a port that's almost certainly closed — 1 is privileged + unused on
    # most sandboxes. The connect fails immediately.
    assert await probe_port("127.0.0.1", 1, timeout=1.0) is False


@pytest.mark.asyncio
async def test_probe_port_invalid_host():
    # NXDOMAIN-ish — the connect raises OSError, which we treat as closed.
    assert await probe_port("nonexistent-host-zzz.invalid", 80, timeout=1.0) is False


# ── check_ports ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_ports_default_set_returns_all():
    result = await check_ports("127.0.0.1", ports=[1], timeout=1.0)
    assert result["host"] == "127.0.0.1"
    assert result["ports"] == {"1": False}
    assert result["open"] == []
    assert result["closed"] == [1]
    assert result["error"] is None


@pytest.mark.asyncio
async def test_check_ports_finds_open_port(listening_port):
    result = await check_ports("127.0.0.1", ports=[listening_port, 1], timeout=2.0)
    assert result["ports"][str(listening_port)] is True
    assert result["ports"]["1"] is False
    assert result["open"] == [listening_port]
    assert result["closed"] == [1]


@pytest.mark.asyncio
async def test_check_ports_empty_host_returns_error():
    result = await check_ports("", ports=[80])
    assert result["error"] == "no host provided"
    assert result["ports"] == {}


@pytest.mark.asyncio
async def test_check_ports_truncates_oversized_list():
    # Pass way more ports than MAX_PORTS_PER_HOST — the cap should clamp.
    huge = list(range(1, MAX_PORTS_PER_HOST + 50))
    result = await check_ports("127.0.0.1", ports=huge, timeout=0.5)
    # Only the first MAX_PORTS_PER_HOST entries should be probed.
    assert len(result["ports"]) == MAX_PORTS_PER_HOST


def test_default_ports_is_small_and_web_only():
    # The default set must stay small (ADR-6) and cover the common web ports.
    assert DEFAULT_PORTS == (80, 443, 8080, 8443)
    assert len(DEFAULT_PORTS) <= 8
