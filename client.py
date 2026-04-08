"""
Reference client for local testing of the SOC OpenEnv server.
"""

from __future__ import annotations

import requests


class SOCClient:
    def __init__(self, base_url: str = "http://127.0.0.1:7860"):
        self.base_url = base_url.rstrip("/")

    def reset(self, task_id: str = "easy") -> dict:
        response = requests.post(f"{self.base_url}/reset", json={"task_id": task_id}, timeout=30)
        response.raise_for_status()
        return response.json()

    def step(self, tool: str, params: dict) -> dict:
        response = requests.post(f"{self.base_url}/step", json={"tool": tool, "params": params}, timeout=30)
        response.raise_for_status()
        return response.json()

    def state(self) -> dict:
        response = requests.get(f"{self.base_url}/state", timeout=30)
        response.raise_for_status()
        return response.json()
