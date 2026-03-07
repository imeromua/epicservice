"""
webapp/utils/client_ip.py

Proxy-aware client IP extraction for rate limiting and abuse protection.

Strategy:
- If the connecting IP is in the configured TRUSTED_PROXIES list/CIDR ranges,
  parse the X-Forwarded-For header and use the left-most (original client) entry.
- Otherwise, use request.client.host directly.

This prevents IP spoofing via X-Forwarded-For injection from untrusted clients
while still working correctly behind reverse proxies and load balancers.

Configuration:
  TRUSTED_PROXIES  Comma-separated list of trusted proxy IPs or CIDR ranges.
                   Examples:
                     TRUSTED_PROXIES=10.0.0.1
                     TRUSTED_PROXIES=10.0.0.1,192.168.1.0/24,172.16.0.0/12
                   Default: empty (no trusted proxies — direct client IP used).

Important:
- Do NOT set TRUSTED_PROXIES to 0.0.0.0/0 or trust all IPs; that re-introduces
  the spoofing risk.
- Only list IPs/ranges you actually control (e.g. your load balancer or nginx
  upstream address).
"""

import ipaddress
import logging
import os
from typing import List, Optional, Union

from fastapi import Request

logger = logging.getLogger(__name__)

# Module-level cache of parsed trusted proxy networks (loaded once from env).
# Reset via _reset_trusted_proxies_cache() in tests.
_TRUSTED_PROXY_NETWORKS: Optional[List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]] = None


def _load_trusted_proxies() -> List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
    """Parse TRUSTED_PROXIES env var into a list of ip_network objects."""
    raw = os.getenv("TRUSTED_PROXIES", "").strip()
    if not raw:
        return []

    networks: List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            # strict=False allows host bits to be set (e.g. 192.168.1.5/24 treated as 192.168.1.0/24)
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("TRUSTED_PROXIES: invalid entry ignored: %r", entry)
    return networks


def _get_trusted_proxy_networks() -> List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
    """Return the parsed trusted proxy network list, loading lazily on first call."""
    global _TRUSTED_PROXY_NETWORKS
    if _TRUSTED_PROXY_NETWORKS is None:
        _TRUSTED_PROXY_NETWORKS = _load_trusted_proxies()
    return _TRUSTED_PROXY_NETWORKS


def _reset_trusted_proxies_cache() -> None:
    """Reset the module-level cache so tests can vary TRUSTED_PROXIES via env."""
    global _TRUSTED_PROXY_NETWORKS
    _TRUSTED_PROXY_NETWORKS = None


def _is_trusted_proxy(ip_str: str) -> bool:
    """Return True if ip_str matches any configured trusted proxy network."""
    networks = _get_trusted_proxy_networks()
    if not networks:
        return False
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in networks)
    except ValueError:
        return False


def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address for rate limiting and abuse protection.

    When the connecting peer is a configured trusted proxy (TRUSTED_PROXIES), the
    X-Forwarded-For header is parsed and the left-most (original client) IP is
    returned.  When no trusted proxies are configured, or the connecting peer is
    not one of them, request.client.host is used directly — this keeps the default
    behavior safe even when no TRUSTED_PROXIES is set.

    Args:
        request: The FastAPI/Starlette Request object.

    Returns:
        A string containing the best-effort real client IP address,
        or "unknown" if it cannot be determined.
    """
    connecting_ip: Optional[str] = request.client.host if request.client else None

    if connecting_ip and _is_trusted_proxy(connecting_ip):
        xff = request.headers.get("X-Forwarded-For", "").strip()
        if xff:
            # X-Forwarded-For: client, proxy1, proxy2, ...
            # The left-most address is the original client IP.
            candidate = xff.split(",")[0].strip()
            if candidate:
                try:
                    # Validate that the candidate is a well-formed IP address.
                    ipaddress.ip_address(candidate)
                    return candidate
                except ValueError:
                    logger.warning(
                        "Malformed X-Forwarded-For entry from trusted proxy %s: %r — "
                        "falling back to connecting IP",
                        connecting_ip,
                        candidate,
                    )
        # Trusted proxy but no usable XFF header: use the connecting IP itself.
        return connecting_ip

    # Not behind a trusted proxy (or no trusted proxies configured): use direct IP.
    return connecting_ip or "unknown"
