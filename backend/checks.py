import platform
import re
import subprocess
import time

import requests


def ping_host(host: str, timeout_seconds: int = 2) -> dict:
    """Ping a host once. Return whether it is up and how long it took."""

    # Safety: only allow letters, numbers, dots and dashes in the host name.
    if not re.fullmatch(r"[A-Za-z0-9.\-]+", host) or host.startswith("-"):
        return {"host": host, "is_up": False, "latency_ms": None,
                "error": "Invalid host name"}

    # Windows and Linux/macOS use different ping options.
    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", str(timeout_seconds * 1000), host]
    else:
        command = ["ping", "-c", "1", "-W", str(timeout_seconds), host]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout_seconds + 3
        )
    except subprocess.TimeoutExpired:
        return {"host": host, "is_up": False, "latency_ms": None,
                "error": "Ping timed out"}

    output = result.stdout

    # A real reply always contains "TTL=" (time-to-live) in its text.
    is_up = result.returncode == 0 and "ttl=" in output.lower()

    latency_ms = None
    if is_up:
        match = re.search(r"time[=<]\s*([\d.]+)\s*ms", output, re.IGNORECASE)
        if match:
            latency_ms = float(match.group(1))

    return {"host": host, "is_up": is_up, "latency_ms": latency_ms, "error": None}


def check_http(url: str, timeout_seconds: int = 5) -> dict:
    """Request a URL. Return whether it works, its status code, and timing."""

    if not url.startswith(("http://", "https://")):
        return {"url": url, "is_up": False, "status_code": None,
                "response_time_ms": None,
                "error": "URL must start with http:// or https://"}

    start = time.perf_counter()
    try:
        response = requests.get(url, timeout=timeout_seconds)
    except requests.exceptions.SSLError:
        return {"url": url, "is_up": False, "status_code": None,
                "response_time_ms": None, "error": "SSL certificate problem"}
    except requests.exceptions.Timeout:
        return {"url": url, "is_up": False, "status_code": None,
                "response_time_ms": None, "error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"url": url, "is_up": False, "status_code": None,
                "response_time_ms": None, "error": "Could not connect"}
    except requests.exceptions.RequestException as exc:
        return {"url": url, "is_up": False, "status_code": None,
                "response_time_ms": None, "error": str(exc)}

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return {
        "url": url,
        "is_up": response.status_code < 400,
        "status_code": response.status_code,
        "response_time_ms": elapsed_ms,
        "error": None,
    }


if __name__ == "__main__":
    # This part runs only when we start this file directly, to test it.
    for target in ["8.8.8.8", "google.com", "192.0.2.1", "-bad host"]:
        print(ping_host(target))