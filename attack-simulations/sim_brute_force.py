import argparse
import time

import requests


def main():
    parser = argparse.ArgumentParser(description="Trigger brute force LOGIN_FAILED events.")
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--source-ip", default="10.10.66.10")
    parser.add_argument("--attempts", type=int, default=7)
    args = parser.parse_args()

    headers = {"X-Forwarded-For": args.source_ip, "User-Agent": "hydra-hospital-audit"}
    for i in range(args.attempts):
        response = requests.post(
            f"{args.url}/login",
            json={"username": "doctor", "password": f"bad-password-{i}"},
            headers=headers,
            timeout=5,
        )
        print(f"attempt={i + 1} status={response.status_code}")
        time.sleep(0.4)


if __name__ == "__main__":
    main()
