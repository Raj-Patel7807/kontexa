#!/usr/bin/env python3

"""Check whether the local backend service is healthy."""

import json
import sys
import urllib.request


DEFAULT_HEALTH_URL = "http://localhost:8000/health"


def check_health(url: str = DEFAULT_HEALTH_URL) -> bool:
    """Check the backend health endpoint."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status != 200:
                print(f"[ERROR] Service returned status code: {response.status}")
                return False

            data = json.loads(response.read().decode())
            print(f"[OK] Service is healthy: {data}")
            return True

    except Exception as exc:
        print(f"[ERROR] Could not connect to {url}: {exc}")
        return False


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HEALTH_URL
    sys.exit(0 if check_health(target_url) else 1)
