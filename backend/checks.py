import platform
import re
import socket
import subprocess
import time

import psutil
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

def check_port(host: str, port: int, timeout_seconds: int = 3) -> dict:
    """Try a TCP connection to host:port. Report open, closed or filtered."""

    if not re.fullmatch(r"[A-Za-z0-9.\-]+", host) or host.startswith("-"):
        return {"host": host, "port": port, "is_open": False,
                "state": "invalid", "connect_time_ms": None,
                "error": "Invalid host name"}

    if not 1 <= port <= 65535:
        return {"host": host, "port": port, "is_open": False,
                "state": "invalid", "connect_time_ms": None,
                "error": "Port must be between 1 and 65535"}

    start = time.perf_counter()
    try:
        connection = socket.create_connection((host, port), timeout=timeout_seconds)
        connection.close()
    except ConnectionRefusedError:
        return {"host": host, "port": port, "is_open": False,
                "state": "closed", "connect_time_ms": None,
                "error": "Connection refused"}
    except (socket.timeout, TimeoutError):
        return {"host": host, "port": port, "is_open": False,
                "state": "filtered", "connect_time_ms": None,
                "error": "No response (timed out)"}
    except socket.gaierror:
        return {"host": host, "port": port, "is_open": False,
                "state": "unreachable", "connect_time_ms": None,
                "error": "Host name could not be resolved"}
    except OSError as exc:
        return {"host": host, "port": port, "is_open": False,
                "state": "unreachable", "connect_time_ms": None,
                "error": str(exc)}

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    return {"host": host, "port": port, "is_open": True,
            "state": "open", "connect_time_ms": elapsed_ms, "error": None}
def get_system_metrics() -> dict:
    """Read CPU and memory usage of the machine this program runs on."""

    # interval=1 means: measure CPU activity over 1 second.
    cpu_percent = psutil.cpu_percent(interval=1)

    memory = psutil.virtual_memory()

    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_used_mb": round(memory.used / (1024 * 1024)),
        "memory_total_mb": round(memory.total / (1024 * 1024)),
    }
def get_network_stats() -> dict:
    """Measure network traffic speed over one second."""

    before = psutil.net_io_counters()
    time.sleep(1)
    after = psutil.net_io_counters()

    return {
        "upload_kb_per_sec": round((after.bytes_sent - before.bytes_sent) / 1024, 1),
        "download_kb_per_sec": round((after.bytes_recv - before.bytes_recv) / 1024, 1),
        "total_sent_mb": round(after.bytes_sent / (1024 * 1024), 1),
        "total_received_mb": round(after.bytes_recv / (1024 * 1024), 1),
        "packets_sent": after.packets_sent,
        "packets_received": after.packets_recv,
        "errors_in": after.errin,
        "errors_out": after.errout,
        "dropped_in": after.dropin,
        "dropped_out": after.dropout,
    }

if __name__ == "__main__":
    # This part runs only when we start this file directly, to test it.
    for target in ["8.8.8.8", "google.com", "192.0.2.1", "-bad host"]:
        print(ping_host(target))