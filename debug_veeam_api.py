#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""
Veeam REST API Debug Script

This script helps diagnose connection and API issues when connecting to
the Veeam Backup & Replication REST API.

Tests performed:
1. Network connectivity (DNS, TCP port)
2. SSL/TLS handshake and certificate details
3. OAuth2 authentication with provided credentials
4. REST API endpoints (jobs, repositories, proxies, etc.)
5. License and server information
6. Backup objects and restore points
7. Performance comparison (bulk vs per-object API calls)

Additionally shows timing summary for all API calls to help identify
performance bottlenecks.

Usage:
    python3 debug_veeam_api.py --host 192.168.1.1 --user 'DOMAIN\\admin'
    python3 debug_veeam_api.py --host veeam.local --user admin@domain.com --redact
    python3 debug_veeam_api.py --host veeam.local --user admin --perf-objects 50

The password will be prompted securely (hidden input).
"""

from __future__ import annotations

import argparse
import getpass
import json
import socket
import ssl
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

# Check for required modules
try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("WARNING: urllib3 not found, SSL warnings may appear")

try:
    import requests

    REQUESTS_VERSION = requests.__version__
except ImportError:
    print("ERROR: 'requests' module not found. Install with: pip install requests")
    sys.exit(1)


# =============================================================================
# Helper Classes and Functions
# =============================================================================


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

    @classmethod
    def disable(cls):
        """Disable colors for non-terminal output."""
        cls.GREEN = cls.RED = cls.YELLOW = cls.BLUE = cls.CYAN = cls.BOLD = cls.END = ""


def ok(msg):
    return f"{Colors.GREEN}✓ {msg}{Colors.END}"


def fail(msg):
    return f"{Colors.RED}✗ {msg}{Colors.END}"


def warn(msg):
    return f"{Colors.YELLOW}⚠ {msg}{Colors.END}"


def info(msg):
    return f"{Colors.BLUE}ℹ {msg}{Colors.END}"


def print_header(title):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}{Colors.END}")


def print_subheader(title):
    """Print a subsection header."""
    print(f"\n{Colors.CYAN}--- {title} ---{Colors.END}")


# Global redact settings
REDACT_ENABLED = False
REDACT_VALUES: List[str] = []
REDACT_REPLACEMENT = "***redacted***"


def redact(text):
    """Redact sensitive values from text if redaction is enabled."""
    if not REDACT_ENABLED or not text:
        return text
    result = str(text)
    for value in REDACT_VALUES:
        if value and len(value) > 2:
            result = result.replace(value, REDACT_REPLACEMENT)
            result = result.replace(value.lower(), REDACT_REPLACEMENT)
            result = result.replace(value.upper(), REDACT_REPLACEMENT)
    return result


# =============================================================================
# Timing and Test Results
# =============================================================================


class TimingTracker:
    """Track timing for API calls."""

    def __init__(self):
        self.timings: List[Tuple[str, float, int]] = []  # (name, elapsed_ms, count)
        self.start_time = time.time()

    def add(self, name: str, elapsed_ms: float, count: int = 1) -> None:
        self.timings.append((name, elapsed_ms, count))

    def get_total_time(self) -> float:
        return (time.time() - self.start_time) * 1000

    def print_summary(self) -> None:
        print_header("TIMING SUMMARY")

        if not self.timings:
            print(info("No timing data collected"))
            return

        sorted_timings = sorted(self.timings, key=lambda x: x[1], reverse=True)

        print(f"\n{Colors.BOLD}Individual API Calls (sorted by duration):{Colors.END}")
        print("-" * 60)

        total_api_time = 0.0
        total_calls = 0
        for name, elapsed, count in sorted_timings:
            total_api_time += elapsed
            total_calls += count
            if elapsed > 1000:
                color = Colors.RED
            elif elapsed > 500:
                color = Colors.YELLOW
            else:
                color = Colors.GREEN
            count_str = f" ({count} calls)" if count > 1 else ""
            print(f"  {color}{elapsed:>8.0f}ms{Colors.END}  {name}{count_str}")

        print("-" * 60)
        print(f"  {Colors.BOLD}{total_api_time:>8.0f}ms{Colors.END}  Total API time ({total_calls} calls)")

        total_time = self.get_total_time()
        print(f"  {Colors.BOLD}{total_time:>8.0f}ms{Colors.END}  Total script time")

        if total_api_time > 30000:
            print(f"\n{warn('API time exceeds 30 seconds - may cause CheckMK timeouts!')}")
        elif total_api_time > 15000:
            print(f"\n{warn('API time exceeds 15 seconds - consider optimizing')}")


class TestResults:
    """Collect and summarize test results."""

    def __init__(self):
        self.results: List[Tuple[str, str, str]] = []
        self.details: Dict[str, Any] = {}

    def add(self, category: str, test_name: str, passed: bool, detail: str = "") -> None:
        status = "PASS" if passed else "FAIL"
        self.results.append((category, test_name, status))
        if detail:
            self.details[f"{category}:{test_name}"] = detail

    def add_warning(self, category: str, test_name: str, detail: str = "") -> None:
        self.results.append((category, test_name, "WARN"))
        if detail:
            self.details[f"{category}:{test_name}"] = detail

    def print_summary(self) -> None:
        print_header("TEST SUMMARY")

        current_category = ""
        for category, test_name, status in self.results:
            if category != current_category:
                print(f"\n{Colors.BOLD}{category}:{Colors.END}")
                current_category = category

            if status == "PASS":
                print(f"  {ok(test_name)}")
            elif status == "FAIL":
                print(f"  {fail(test_name)}")
            else:
                print(f"  {warn(test_name)}")

        passed = sum(1 for _, _, s in self.results if s == "PASS")
        failed = sum(1 for _, _, s in self.results if s == "FAIL")
        warnings = sum(1 for _, _, s in self.results if s == "WARN")

        print(f"\n{Colors.BOLD}Total: {passed} passed, {failed} failed, {warnings} warnings{Colors.END}")


# =============================================================================
# Network Tests
# =============================================================================


def test_dns_resolution(host: str, results: TestResults) -> Optional[str]:
    """Test DNS resolution for hostname."""
    print_subheader("DNS Resolution")

    try:
        socket.inet_aton(host)
        print(info(f"Host '{redact(host)}' is already an IP address"))
        results.add("Network", "DNS Resolution", True, "IP address provided")
        return host
    except socket.error:
        pass

    try:
        ip = socket.gethostbyname(host)
        print(ok(f"Resolved '{redact(host)}' to {redact(ip)}"))
        results.add("Network", "DNS Resolution", True, f"Resolved to {redact(ip)}")
        return ip
    except socket.gaierror as e:
        print(fail(f"DNS resolution failed for '{redact(host)}': {e}"))
        results.add("Network", "DNS Resolution", False, str(e))
        return None


def test_tcp_connection(host: str, port: int, results: TestResults) -> bool:
    """Test TCP connection to host:port."""
    print_subheader(f"TCP Connection (Port {port})")

    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        elapsed = (time.time() - start) * 1000
        sock.close()

        if result == 0:
            print(ok(f"Port {port} is open (connected in {elapsed:.1f}ms)"))
            results.add("Network", f"TCP Port {port}", True, f"{elapsed:.1f}ms")
            return True
        else:
            print(fail(f"Port {port} is closed or filtered"))
            results.add("Network", f"TCP Port {port}", False, "Connection refused")
            return False
    except socket.timeout:
        print(fail(f"Connection to port {port} timed out"))
        results.add("Network", f"TCP Port {port}", False, "Timeout")
        return False
    except Exception as e:
        print(fail(f"Connection error: {e}"))
        results.add("Network", f"TCP Port {port}", False, str(e))
        return False


def test_ssl_certificate(host: str, port: int, results: TestResults) -> Dict[str, Any]:
    """Test SSL/TLS connection and get certificate details."""
    print_subheader("SSL/TLS Certificate")

    cert_info: Dict[str, Any] = {}

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=True)
                cipher = ssock.cipher()
                version = ssock.version()

                cert_decoded = ssl.DER_cert_to_PEM_cert(cert)

                print(ok("SSL/TLS Handshake successful"))
                print(f"    Protocol: {version}")
                print(f"    Cipher: {cipher[0]} ({cipher[2]} bits)")

                cert_info["protocol"] = version
                cert_info["cipher"] = cipher[0]
                cert_info["bits"] = cipher[2]

                try:
                    import subprocess

                    proc = subprocess.run(
                        ["openssl", "x509", "-noout", "-subject", "-issuer", "-dates"],
                        input=cert_decoded.encode(),
                        capture_output=True,
                        timeout=5,
                    )
                    if proc.returncode == 0:
                        output = proc.stdout.decode()
                        print("\n    Certificate Details:")
                        for line in output.strip().split("\n"):
                            print(f"      {line}")
                            if "subject=" in line.lower():
                                cert_info["subject"] = line.split("=", 1)[1] if "=" in line else line
                            elif "issuer=" in line.lower():
                                cert_info["issuer"] = line.split("=", 1)[1] if "=" in line else line

                        if cert_info.get("subject") == cert_info.get("issuer"):
                            print(warn("Certificate is SELF-SIGNED"))
                            results.add_warning("SSL/TLS", "Certificate", "Self-signed certificate")
                        else:
                            results.add("SSL/TLS", "Certificate", True)
                except Exception:
                    print(info("(Could not parse certificate details - openssl not available)"))
                    results.add("SSL/TLS", "Certificate", True, "Details unavailable")

                results.add("SSL/TLS", "Handshake", True, f"{version} / {cipher[0]}")
                return cert_info

    except ssl.SSLError as e:
        print(fail(f"SSL Error: {e}"))
        results.add("SSL/TLS", "Handshake", False, str(e))
        return {}
    except Exception as e:
        print(fail(f"Connection error: {e}"))
        results.add("SSL/TLS", "Handshake", False, str(e))
        return {}


# =============================================================================
# Veeam API Functions
# =============================================================================

API_VERSION = "1.3-rev1"


def get_oauth_token(
    session: requests.Session,
    base_url: str,
    username: str,
    password: str,
    verify_ssl: bool,
    results: TestResults,
    timing: TimingTracker,
) -> Optional[str]:
    """Authenticate with Veeam REST API using OAuth2 password grant."""
    print_subheader("OAuth2 Authentication")

    token_url = f"{base_url}/api/oauth2/token"
    print(f"  URL: {redact(token_url)}")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-api-version": API_VERSION,
    }

    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    try:
        start = time.time()
        response = session.post(
            token_url,
            headers=headers,
            data=urlencode(data),
            timeout=30,
            verify=verify_ssl,
        )
        elapsed = (time.time() - start) * 1000
        timing.add("OAuth2 Token", elapsed)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            token_type = token_data.get("token_type", "Bearer")
            expires_in = token_data.get("expires_in", 0)

            print(ok(f"Authentication successful ({elapsed:.0f}ms)"))
            print(f"    Token type: {token_type}")
            print(f"    Expires in: {expires_in} seconds")

            results.add("Auth", "OAuth2 Token", True, f"{elapsed:.0f}ms")
            return access_token
        else:
            print(fail(f"Authentication failed: HTTP {response.status_code} ({elapsed:.0f}ms)"))
            try:
                error_body = response.json()
                print(f"    Error: {redact(json.dumps(error_body, indent=2))}")
            except json.JSONDecodeError:
                print(f"    Response: {redact(response.text[:500])}")

            results.add("Auth", "OAuth2 Token", False, f"HTTP {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print(fail("Authentication request timed out"))
        results.add("Auth", "OAuth2 Token", False, "Timeout")
        timing.add("OAuth2 Token", 30000)
        return None
    except Exception as e:
        print(fail(f"Authentication error: {e}"))
        results.add("Auth", "OAuth2 Token", False, str(e))
        return None


def api_get(
    session: requests.Session,
    base_url: str,
    endpoint: str,
    token: str,
    verify_ssl: bool,
    timeout: int = 30,
) -> Tuple[Optional[Any], float]:
    """Make a GET request to the API and return (data, elapsed_ms)."""
    url = f"{base_url}/api/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-version": API_VERSION,
        "Accept": "application/json",
    }

    start = time.time()
    response = session.get(url, headers=headers, timeout=timeout, verify=verify_ssl)
    elapsed = (time.time() - start) * 1000

    if response.status_code == 200:
        return response.json(), elapsed
    return None, elapsed


def api_get_paginated(
    session: requests.Session,
    base_url: str,
    endpoint: str,
    token: str,
    verify_ssl: bool,
    limit: int = 500,
    extra_params: Optional[Dict[str, str]] = None,
) -> Tuple[List[dict], float, int]:
    """Get all items from a paginated endpoint. Returns (items, total_ms, call_count)."""
    all_items = []
    skip = 0
    total_ms = 0.0
    call_count = 0

    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-version": API_VERSION,
        "Accept": "application/json",
    }

    while True:
        url = f"{base_url}/api/v1/{endpoint}?limit={limit}&skip={skip}"
        if extra_params:
            for key, value in extra_params.items():
                url += f"&{key}={value}"
        start = time.time()
        response = session.get(url, headers=headers, timeout=60, verify=verify_ssl)
        elapsed = (time.time() - start) * 1000
        total_ms += elapsed
        call_count += 1

        if response.status_code != 200:
            break

        data = response.json()
        items = data.get("data", []) if isinstance(data, dict) else data

        if not items:
            break

        all_items.extend(items)

        # Check pagination
        if isinstance(data, dict):
            pagination = data.get("pagination", {})
            total = pagination.get("total", len(items))
            if skip + len(items) >= total:
                break
        elif len(items) < limit:
            break

        skip += limit

    return all_items, total_ms, call_count


def test_api_endpoint(
    session: requests.Session,
    base_url: str,
    endpoint: str,
    token: str,
    test_name: str,
    results: TestResults,
    category: str,
    verify_ssl: bool,
    timing: TimingTracker,
    show_data: bool = False,
) -> Optional[Any]:
    """Test a Veeam REST API endpoint."""
    url = f"{base_url}/api/v1/{endpoint}"

    print(f"\n  Testing: {test_name}")
    print(f"  URL: {redact(url)}")

    headers = {
        "Authorization": f"Bearer {token[:20]}...{token[-10:]}" if len(token) > 30 else f"Bearer {token}",
        "x-api-version": API_VERSION,
        "Accept": "application/json",
    }
    print(f"  Headers: x-api-version={API_VERSION}")

    # Use actual token for request
    real_headers = {
        "Authorization": f"Bearer {token}",
        "x-api-version": API_VERSION,
        "Accept": "application/json",
    }

    try:
        start = time.time()
        response = session.get(url, headers=real_headers, timeout=30, verify=verify_ssl)
        elapsed = (time.time() - start) * 1000
        timing.add(test_name, elapsed)

        status_ok = response.status_code == 200

        if status_ok:
            print(f"  {ok(f'Status: {response.status_code} ({elapsed:.0f}ms)')}")
        else:
            print(f"  {fail(f'Status: {response.status_code} ({elapsed:.0f}ms)')}")

        if show_data or not status_ok:
            try:
                json_resp = response.json()
                if isinstance(json_resp, dict) and "data" in json_resp:
                    items = json_resp["data"]
                    print(f"    Response: {len(items)} items")
                    if items and show_data:
                        print(f"    First item: {redact(json.dumps(items[0], indent=4)[:500])}")
                elif isinstance(json_resp, list):
                    print(f"    Response: {len(json_resp)} items")
                    if json_resp and show_data:
                        print(f"    First item: {redact(json.dumps(json_resp[0], indent=4)[:500])}")
                else:
                    print(f"    Response: {redact(json.dumps(json_resp, indent=4)[:500])}")
            except json.JSONDecodeError:
                print(f"    Response: {redact(response.text[:500])}")

        results.add(category, test_name, status_ok, f"HTTP {response.status_code}")

        if status_ok:
            try:
                return response.json()
            except json.JSONDecodeError:
                return None
        return None

    except requests.exceptions.Timeout:
        print(f"  {fail('Request timed out')}")
        results.add(category, test_name, False, "Timeout")
        timing.add(test_name, 30000)
        return None
    except Exception as e:
        print(f"  {fail(f'Error: {e}')}")
        results.add(category, test_name, False, str(e))
        return None


def run_performance_test(
    session: requests.Session,
    base_url: str,
    token: str,
    verify_ssl: bool,
    timing: TimingTracker,
    max_objects: int = 10,
    restore_points_days: int = 7,
) -> None:
    """Run performance comparison between bulk and per-object API calls."""
    print_header("PERFORMANCE TEST: Bulk vs Per-Object API Calls")

    print_subheader("Fetching Backup Objects")

    # Get backup objects
    backup_objects, bo_time, bo_calls = api_get_paginated(
        session, base_url, "backupObjects", token, verify_ssl
    )
    print(f"  {ok(f'Fetched {len(backup_objects)} backup objects in {bo_time:.0f}ms ({bo_calls} calls)')}")
    timing.add("backupObjects (paginated)", bo_time, bo_calls)

    if not backup_objects:
        print(warn("No backup objects found - skipping performance test"))
        return

    # Test bulk restore points fetch with time filter
    print_subheader(f"Bulk Restore Points (filtered to last {restore_points_days} days)")

    # Calculate time filter
    rp_params: Optional[Dict[str, str]] = None
    if restore_points_days > 0:
        from datetime import datetime, timedelta, timezone
        created_after = (
            datetime.now(timezone.utc) - timedelta(days=restore_points_days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        rp_params = {"createdAfterFilter": created_after}
        print(f"  Filter: createdAfterFilter={created_after}")

    all_rp, bulk_time, bulk_calls = api_get_paginated(
        session, base_url, "restorePoints", token, verify_ssl, extra_params=rp_params
    )
    print(f"  {ok(f'Fetched {len(all_rp)} restore points in {bulk_time:.0f}ms ({bulk_calls} calls)')}")
    timing.add(f"restorePoints BULK ({restore_points_days} days)", bulk_time, bulk_calls)

    # Test per-object restore points (limited to max_objects)
    print_subheader(f"Per-Object Restore Points (OLD - first {max_objects} objects)")

    test_objects = backup_objects[:max_objects]
    per_object_total = 0.0
    per_object_count = 0
    per_object_rp_count = 0

    for obj in test_objects:
        object_id = obj.get("id")
        if not object_id:
            continue

        try:
            rp_data, rp_time = api_get(
                session, base_url, f"backupObjects/{object_id}/restorePoints",
                token, verify_ssl
            )
            per_object_total += rp_time
            per_object_count += 1
            if rp_data:
                items = rp_data.get("data", []) if isinstance(rp_data, dict) else rp_data
                per_object_rp_count += len(items) if isinstance(items, list) else 0
        except Exception as e:
            print(f"    {warn(f'Error for object {object_id}: {e}')}")

    avg_per_call = per_object_total / per_object_count if per_object_count > 0 else 0
    print(f"  Tested {per_object_count} objects: {per_object_total:.0f}ms total, {avg_per_call:.0f}ms avg/call")
    print(f"  Found {per_object_rp_count} restore points for tested objects")
    timing.add(f"restorePoints PER-OBJECT ({per_object_count} objects)", per_object_total, per_object_count)

    # Extrapolation
    print_subheader("Performance Comparison")

    total_objects = len(backup_objects)
    estimated_per_object = avg_per_call * total_objects

    print(f"\n  {Colors.BOLD}For {total_objects} backup objects:{Colors.END}")
    print(f"    Bulk API (optimized):     {bulk_time:>8.0f}ms  ({bulk_calls} calls)")
    print(f"    Per-Object (estimated):   {estimated_per_object:>8.0f}ms  ({total_objects} calls)")

    if estimated_per_object > 0:
        speedup = estimated_per_object / bulk_time if bulk_time > 0 else 0
        savings = estimated_per_object - bulk_time
        print(f"\n  {Colors.GREEN}Bulk API is ~{speedup:.1f}x faster ({savings:.0f}ms saved){Colors.END}")
        print(f"  {Colors.GREEN}API calls reduced from {total_objects} to {bulk_calls}{Colors.END}")


# =============================================================================
# Main Function
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Debug Veeam REST API connection issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 debug_veeam_api.py --host 192.168.1.1 --user 'DOMAIN\\admin'
    python3 debug_veeam_api.py --host veeam.local --user admin@domain.com --no-cert-check
    python3 debug_veeam_api.py --host 192.168.1.1 --user Administrator --redact
    python3 debug_veeam_api.py --host veeam.local --user admin --perf-objects 50

The password will be prompted securely (hidden input).
        """,
    )
    parser.add_argument("--host", required=True, help="Veeam server IP or hostname")
    parser.add_argument("--user", required=True, help="Username (DOMAIN\\user or user@domain)")
    parser.add_argument("--password", help="Password (will prompt securely if not provided)")
    parser.add_argument("--port", type=int, default=9419, help="REST API port (default: 9419)")
    parser.add_argument("--no-cert-check", action="store_true", help="Disable SSL certificate verification")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Redact sensitive data (hostnames, credentials, job/repository names, license info)",
    )
    parser.add_argument(
        "--perf-objects",
        type=int,
        default=10,
        help="Number of objects to test in per-object performance comparison (default: 10)",
    )
    parser.add_argument(
        "--restore-points-days",
        type=int,
        default=7,
        help="Only fetch restore points from the last N days (default: 7, 0=all)",
    )

    args = parser.parse_args()

    # Prompt for password securely if not provided
    password = args.password
    if not password:
        password = getpass.getpass(f"Password for {args.user}: ")

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    global REDACT_ENABLED, REDACT_VALUES
    if args.redact:
        REDACT_ENABLED = True
        REDACT_VALUES = [args.host, args.user, password]

    verify_ssl = not args.no_cert_check
    base_url = f"https://{args.host}:{args.port}"

    session = requests.Session()
    results = TestResults()
    timing = TimingTracker()

    # =========================================================================
    # HEADER: System Info
    # =========================================================================
    print_header("Veeam REST API Debug Script")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Requests: {REQUESTS_VERSION}")
    print(f"  Target: {redact(base_url)}")
    print(f"  User: {redact(args.user)}")
    print(f"  API Version: {API_VERSION}")
    print(f"  SSL Verify: {verify_ssl}")

    # =========================================================================
    # TEST 1: Network Connectivity
    # =========================================================================
    print_header("1. NETWORK CONNECTIVITY")

    resolved_ip = test_dns_resolution(args.host, results)
    if not resolved_ip:
        print(fail("\nCannot proceed without DNS resolution"))
        results.print_summary()
        return 1

    tcp_ok = test_tcp_connection(resolved_ip, args.port, results)
    if not tcp_ok:
        print(fail(f"\nCannot proceed - port {args.port} not reachable"))
        results.print_summary()
        return 1

    # =========================================================================
    # TEST 2: SSL/TLS
    # =========================================================================
    print_header("2. SSL/TLS CERTIFICATE")
    test_ssl_certificate(resolved_ip, args.port, results)

    # =========================================================================
    # TEST 3: Authentication
    # =========================================================================
    print_header("3. AUTHENTICATION")

    token = get_oauth_token(
        session, base_url, args.user, password, verify_ssl, results, timing
    )

    if not token:
        print(fail("\nCannot proceed without authentication"))
        print("\n  Hints:")
        print("    - Check username format: DOMAIN\\user or user@domain.com")
        print("    - Verify user has REST API access in Veeam")
        print("    - Ensure Veeam REST API service is running (port 9419)")
        results.print_summary()
        timing.print_summary()
        return 1

    # =========================================================================
    # TEST 4: Server Information
    # =========================================================================
    print_header("4. SERVER INFORMATION")

    server_info = test_api_endpoint(
        session, base_url, "serverInfo", token, "Server Info",
        results, "Server", verify_ssl, timing, show_data=True
    )

    if server_info:
        # Add server name to redact list
        server_name = server_info.get("name")
        if REDACT_ENABLED and server_name and server_name not in REDACT_VALUES:
            REDACT_VALUES.append(server_name)
        print(f"\n  {Colors.BOLD}Veeam Server Details:{Colors.END}")
        print(f"    Name: {redact(server_info.get('name', 'Unknown'))}")
        print(f"    Build: {server_info.get('buildVersion', 'Unknown')}")
        print(f"    Database: {server_info.get('databaseVendor', 'Unknown')}")
        patches = server_info.get("patches", [])
        if patches:
            print(f"    Patches: {len(patches)} installed")

    # =========================================================================
    # TEST 5: License Information
    # =========================================================================
    print_header("5. LICENSE INFORMATION")

    license_info = test_api_endpoint(
        session, base_url, "license", token, "License Info",
        results, "License", verify_ssl, timing, show_data=True
    )

    if license_info:
        # Add licensedTo to redact list
        licensed_to = license_info.get("licensedTo")
        if REDACT_ENABLED and licensed_to and licensed_to not in REDACT_VALUES:
            REDACT_VALUES.append(licensed_to)
        print(f"\n  {Colors.BOLD}License Details:{Colors.END}")
        print(f"    Status: {license_info.get('status', 'Unknown')}")
        print(f"    Type: {license_info.get('type', 'Unknown')}")
        print(f"    Edition: {license_info.get('edition', 'Unknown')}")
        print(f"    Licensed To: {redact(license_info.get('licensedTo', 'Unknown'))}")
        exp_date = license_info.get("expirationDate")
        if exp_date:
            print(f"    Expires: {exp_date}")
        instance_summary = license_info.get("instanceLicenseSummary", {})
        if instance_summary:
            licensed = instance_summary.get("licensedInstancesNumber", 0)
            used = instance_summary.get("usedInstancesNumber", 0)
            print(f"    Instances: {used}/{licensed} used")

    # =========================================================================
    # TEST 6: REST API Endpoints
    # =========================================================================
    print_header("6. REST API ENDPOINTS")

    print_subheader("Core Endpoints")
    core_endpoints = [
        ("jobs/states", "Job States"),
        ("backups", "Backups"),
        ("backupObjects", "Backup Objects"),
        ("taskSessions", "Task Sessions"),
        ("restorePoints", "Restore Points (Bulk)"),
    ]
    for endpoint, name in core_endpoints:
        data = test_api_endpoint(
            session, base_url, endpoint, token, name,
            results, "API", verify_ssl, timing
        )
        if data and isinstance(data, dict) and "data" in data:
            print(f"    Found: {len(data['data'])} items")
        elif data and isinstance(data, list):
            print(f"    Found: {len(data)} items")

    print_subheader("Infrastructure Endpoints")
    infra_endpoints = [
        ("backupInfrastructure/repositories/states", "Repositories"),
        ("backupInfrastructure/proxies/states", "Proxies"),
        ("backupInfrastructure/managedServers", "Managed Servers"),
        ("backupInfrastructure/scaleOutRepositories", "Scale-Out Repositories"),
        ("backupInfrastructure/wanAccelerators", "WAN Accelerators"),
    ]
    for endpoint, name in infra_endpoints:
        data = test_api_endpoint(
            session, base_url, endpoint, token, name,
            results, "Infrastructure", verify_ssl, timing
        )
        if data and isinstance(data, dict) and "data" in data:
            print(f"    Found: {len(data['data'])} items")
        elif data and isinstance(data, list):
            print(f"    Found: {len(data)} items")

    # =========================================================================
    # TEST 7: Data Summary
    # =========================================================================
    print_header("7. DATA SUMMARY")

    # Get jobs
    jobs_data, _ = api_get(session, base_url, "jobs/states", token, verify_ssl)
    if jobs_data:
        jobs = jobs_data.get("data", []) if isinstance(jobs_data, dict) else jobs_data
        # Add job names to redact list
        if REDACT_ENABLED:
            for job in jobs:
                job_name = job.get("name")
                if job_name and job_name not in REDACT_VALUES:
                    REDACT_VALUES.append(job_name)
        print(f"\n  {Colors.BOLD}Jobs ({len(jobs)}):{Colors.END}")
        for job in jobs[:10]:
            job_name = job.get("name", "Unknown")
            job_type = job.get("type", "Unknown")
            status = job.get("status", "Unknown")
            result = job.get("lastResult", "None")
            print(f"    - [{job_type}] {redact(job_name)}: {status}, {result}")
        if len(jobs) > 10:
            print(f"    ... and {len(jobs) - 10} more")

    # Get repositories
    repos_data, _ = api_get(session, base_url, "backupInfrastructure/repositories/states", token, verify_ssl)
    if repos_data:
        repos = repos_data.get("data", []) if isinstance(repos_data, dict) else repos_data
        # Add repository names to redact list
        if REDACT_ENABLED:
            for repo in repos:
                repo_name = repo.get("name")
                if repo_name and repo_name not in REDACT_VALUES:
                    REDACT_VALUES.append(repo_name)
        print(f"\n  {Colors.BOLD}Repositories ({len(repos)}):{Colors.END}")
        for repo in repos[:10]:
            repo_name = repo.get("name", "Unknown")
            repo_type = repo.get("type", "Unknown")
            capacity = repo.get("capacityGB", 0)
            free = repo.get("freeGB", 0)
            online = "Online" if repo.get("isOnline", False) else "Offline"
            print(f"    - [{repo_type}] {redact(repo_name)}: {capacity:.1f}GB capacity, {free:.1f}GB free, {online}")
        if len(repos) > 10:
            print(f"    ... and {len(repos) - 10} more")

    # Get backup objects count
    bo_data, _ = api_get(session, base_url, "backupObjects", token, verify_ssl)
    if bo_data:
        backup_objects = bo_data.get("data", []) if isinstance(bo_data, dict) else bo_data
        print(f"\n  {Colors.BOLD}Backup Objects ({len(backup_objects)}):{Colors.END}")
        # Group by platform
        by_platform: Dict[str, int] = {}
        for obj in backup_objects:
            platform = obj.get("platformName", "Unknown")
            by_platform[platform] = by_platform.get(platform, 0) + 1
        for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
            print(f"    - {platform}: {count} objects")

    # Get restore points count
    rp_data, _ = api_get(session, base_url, "restorePoints", token, verify_ssl)
    if rp_data:
        restore_points = rp_data.get("data", []) if isinstance(rp_data, dict) else rp_data
        print(f"\n  {Colors.BOLD}Restore Points ({len(restore_points)}):{Colors.END}")
        # Count by malware status
        malware_stats: Dict[str, int] = {}
        for rp in restore_points:
            status = rp.get("malwareStatus", "Unknown")
            malware_stats[status] = malware_stats.get(status, 0) + 1
        if malware_stats:
            print("    Malware Status:")
            for status, count in sorted(malware_stats.items(), key=lambda x: -x[1]):
                print(f"      - {status}: {count}")

    # =========================================================================
    # TEST 8: Warning Detection Test (Task Sessions)
    # =========================================================================
    print_header("8. WARNING DETECTION TEST")

    # Check for jobs with Warning/Failed result
    print_subheader("Jobs with Warning/Failed Status")
    warning_jobs = []
    if jobs_data:
        jobs = jobs_data.get("data", []) if isinstance(jobs_data, dict) else jobs_data
        for job in jobs:
            result = job.get("lastResult")
            if result in ("Warning", "Failed"):
                warning_jobs.append({
                    "name": job.get("name"),
                    "result": result,
                    "sessionId": job.get("sessionId"),
                    "lastRun": job.get("lastRun"),
                })
                job_name = job.get("name", "Unknown")
                print(f"  {warn(f'{job_name}: {result}')}")
                print(f"    Session ID: {job.get('sessionId')}")

    if not warning_jobs:
        print(info("No jobs with Warning or Failed status found"))

    # Test task sessions fetch with time filter
    if warning_jobs:
        print_subheader("Task Sessions (Warning Detection)")

        # Fetch with 24h filter
        from datetime import timedelta, timezone
        created_after_24h = (
            datetime.now(timezone.utc) - timedelta(hours=24)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        tasks_filtered, task_time, task_calls = api_get_paginated(
            session, base_url, "taskSessions", token, verify_ssl,
            extra_params={"createdAfterFilter": created_after_24h}
        )
        print(f"  {ok(f'Fetched {len(tasks_filtered)} task sessions (24h filter) in {task_time:.0f}ms')}")
        timing.add("taskSessions (24h filter)", task_time, task_calls)

        # Check for VMs with Warning/Failed results in warning sessions
        warning_session_ids = {j["sessionId"] for j in warning_jobs if j.get("sessionId")}
        vms_with_issues = []

        for task in tasks_filtered:
            if task.get("sessionId") not in warning_session_ids:
                continue
            task_result = task.get("result", {}).get("result")
            if task_result in ("Warning", "Failed"):
                vms_with_issues.append({
                    "name": task.get("name"),
                    "result": task_result,
                    "message": task.get("result", {}).get("message", ""),
                    "sessionId": task.get("sessionId"),
                })

        if vms_with_issues:
            print(f"\n  {Colors.BOLD}VMs with Warning/Failed task results:{Colors.END}")
            for vm in vms_with_issues[:20]:
                status_color = Colors.RED if vm["result"] == "Failed" else Colors.YELLOW
                print(f"    {status_color}[{vm['result']}]{Colors.END} {redact(vm['name'])}")
                if vm["message"]:
                    print(f"           Message: {redact(vm['message'][:100])}")
            if len(vms_with_issues) > 20:
                print(f"    ... and {len(vms_with_issues) - 20} more")
        else:
            print(info("No VMs with Warning/Failed task results found in warning sessions"))

        # Compare with unfiltered fetch
        print_subheader("Task Sessions Performance Comparison")
        tasks_all, task_all_time, task_all_calls = api_get_paginated(
            session, base_url, "taskSessions", token, verify_ssl
        )
        print(f"  All task sessions:     {len(tasks_all):>6} items in {task_all_time:>6.0f}ms ({task_all_calls} calls)")
        print(f"  Filtered (24h):        {len(tasks_filtered):>6} items in {task_time:>6.0f}ms ({task_calls} calls)")
        timing.add("taskSessions (ALL)", task_all_time, task_all_calls)

        if task_all_time > 0:
            speedup = task_all_time / task_time if task_time > 0 else 0
            print(f"\n  {Colors.GREEN}Filtered fetch is ~{speedup:.1f}x faster{Colors.END}")

    # =========================================================================
    # TEST 9: Performance Test (Bulk vs Per-Object API Calls)
    # =========================================================================
    run_performance_test(
        session, base_url, token, verify_ssl, timing,
        args.perf_objects, args.restore_points_days
    )

    # =========================================================================
    # SUMMARY AND RECOMMENDATIONS
    # =========================================================================
    results.print_summary()
    timing.print_summary()

    print_header("RECOMMENDATIONS")

    recommendations = []
    issues_found = False

    # Check network issues
    network_results = [r for r in results.results if r[0] == "Network"]
    if any(r[2] == "FAIL" for r in network_results):
        issues_found = True
        recommendations.append("- Network connectivity issues detected - check firewall and DNS")

    # Check auth issues
    auth_results = [r for r in results.results if r[0] == "Auth"]
    if any(r[2] == "FAIL" for r in auth_results):
        issues_found = True
        recommendations.append("- Authentication failed:")
        recommendations.append("  - Check username format (DOMAIN\\user or user@domain.com)")
        recommendations.append("  - Verify password is correct")
        recommendations.append("  - Ensure user has REST API access in Veeam")
        recommendations.append("  - Check if Veeam REST API service is running")

    # Check API issues
    api_results = [r for r in results.results if r[0] in ["API", "Infrastructure"]]
    api_ok = all(r[2] == "PASS" for r in api_results)

    if api_ok:
        recommendations.append("- REST API: All endpoints responding correctly")
    else:
        failed_endpoints = [r[1] for r in api_results if r[2] == "FAIL"]
        if failed_endpoints:
            issues_found = True
            recommendations.append(f"- REST API: Some endpoints failed: {', '.join(failed_endpoints)}")

    # Check license
    license_results = [r for r in results.results if r[0] == "License"]
    if any(r[2] == "PASS" for r in license_results):
        recommendations.append("- License: Information retrieved successfully")
    else:
        issues_found = True
        recommendations.append("- License: Could not retrieve license information")

    # Check timing
    total_api_time = sum(t[1] for t in timing.timings)
    if total_api_time > 30000:
        issues_found = True
        recommendations.append(f"- Performance: API calls take {total_api_time/1000:.1f}s - may cause timeouts")
        recommendations.append("  - Consider enabling section caching in the special agent")
        recommendations.append("  - Reduce session_age to limit historical data")

    # Final verdict
    print()
    if not issues_found:
        print(ok("All critical tests passed - Veeam REST API is properly configured"))
    else:
        print(warn("Some issues detected - see recommendations below"))

    print()
    for rec in recommendations:
        print(rec)

    print()
    session.close()

    critical_failed = any(
        r[2] == "FAIL" for r in results.results if r[0] in ["Auth", "Network"]
    )
    return 1 if critical_failed else 0


if __name__ == "__main__":
    sys.exit(main())
