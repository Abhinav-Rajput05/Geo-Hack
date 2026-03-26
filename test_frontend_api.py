#!/usr/bin/env python3
"""
Smoke tests for frontend alignment APIs.
Run this while backend is running on localhost:8000.
"""

import json
from typing import Any, Dict

import requests

BASE_URL = "http://localhost:8000/api/v1/frontend"


def call(method: str, path: str, payload: Dict[str, Any] | None = None) -> tuple[int, Dict[str, Any]]:
    url = f"{BASE_URL}{path}"
    response = requests.request(method, url, json=payload, timeout=20)
    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}
    return response.status_code, data


def assert_envelope(data: Dict[str, Any]) -> None:
    assert "success" in data, "Missing success field"
    assert "data" in data, "Missing data field"
    assert "message" in data, "Missing message field"


def run() -> None:
    checks = [
        ("GET", "/dashboard?country=India", None),
        ("GET", "/intelligence/India", None),
        ("GET", "/analysis/India", None),
        ("POST", "/analysis/chat", {"question": "Summarize India risk drivers", "country": "India"}),
    ]

    for method, path, payload in checks:
        status, body = call(method, path, payload)
        print(f"{method} {path} -> {status}")
        print(json.dumps(body, indent=2)[:500])
        print("-" * 60)
        assert status == 200, f"Expected 200, got {status} for {path}"
        assert_envelope(body)

    print("Frontend alignment API smoke tests passed.")


if __name__ == "__main__":
    run()
