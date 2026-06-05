import argparse

import requests


def main():
    parser = argparse.ArgumentParser(description="Trigger high file access and exfiltration indicators.")
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--source-ip", default="10.10.99.40")
    args = parser.parse_args()

    response = requests.post(
        f"{args.url}/simulate/file-access",
        json={"count": 180, "outbound_bytes": 150000, "username": "radiology-workstation"},
        headers={"X-Forwarded-For": args.source_ip, "User-Agent": "powershell-archive-client"},
        timeout=5,
    )
    print(f"status={response.status_code} body={response.text}")


if __name__ == "__main__":
    main()
