"""Client for the Go-based orchestration service.

This module shows how Python agents can offload performance-critical work
via a lightweight HTTP API.
"""

from __future__ import annotations

import requests


def get_priority_score(name: str, url: str = "http://localhost:8080/score") -> int:
    """Request a priority score for a mission title from the Go service.

    Parameters
    ----------
    name: str
        Mission title to evaluate.
    url: str, optional
        Base URL of the Go service.
    """

    response = requests.get(url, params={"name": name}, timeout=5)
    response.raise_for_status()
    data = response.json()
    return int(data["score"])


def get_fibonacci(n: int, url: str = "http://localhost:8080/fib") -> int:
    """Request the nth Fibonacci number from the Go service.

    Parameters
    ----------
    n: int
        Which Fibonacci number to compute.
    url: str, optional
        Base URL of the Go service.
    """

    response = requests.get(url, params={"n": n}, timeout=10)
    response.raise_for_status()
    data = response.json()
    return int(data["result"])


if __name__ == "__main__":
    print(get_fibonacci(10))
    print(get_priority_score("Major wildfire"))
