import argparse
import time

import requests


def main():
    parser = argparse.ArgumentParser(description="Touch several services from one source IP.")
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--source-ip", default="10.10.88.30")
    args = parser.parse_args()

    headers = {"X-Forwarded-For": args.source_ip, "User-Agent": "internal-admin-tool"}
    calls = [
        ("POST", "/login", {"username": "doctor", "password": "doctor123"}, {}),
        ("GET", "/patients/P-1001", None, {"X-User": "doctor"}),
        ("GET", "/patients/P-1002", None, {"X-User": "doctor"}),
        ("POST", "/simulate/file-access", {"count": 30, "outbound_bytes": 90000}, {}),
    ]
    for method, path, body, extra_headers in calls:
        merged = dict(headers)
        merged.update(extra_headers)
        if method == "POST":
            response = requests.post(f"{args.url}{path}", json=body, headers=merged, timeout=5)
        else:
            response = requests.get(f"{args.url}{path}", headers=merged, timeout=5)
        print(f"{method} {path} -> {response.status_code}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
