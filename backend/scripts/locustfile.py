"""Locust scenarios for Phase T6 (Performance, Load, and Reliability
Testing) — run against scripts/perf_server.py, never against a real
deployment or a real LLM provider (see that script's docstring for why:
fake embedding/LLM, so every millisecond measured here is this backend's
own overhead).

Usage (from backend/, with the perf server already running on :8001):
    locust -f scripts/locustfile.py --host http://127.0.0.1:8001 \
        --headless -u 20 -r 5 -t 30s --csv=perf_results/load
"""

import random
import string

from locust import HttpUser, between, task


def _random_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"loadtest-{suffix}@example.com"


class OpsMindUser(HttpUser):
    """One simulated user's whole session: register + log in ONCE
    (on_start — matches how a real user actually behaves; login is not
    something a real user repeats every few seconds), then a realistic
    mix of the app's actual traffic. Task weights are relative, not
    percentages — health_check(weight=10) is chosen roughly 10x as often
    as list_documents(weight=1), matching a real deployment's shape: a
    load balancer / uptime monitor hits /health constantly and cheaply;
    chat and document actions are the actual product traffic and are
    comparatively rarer and heavier.
    """

    wait_time = between(1, 3)

    def on_start(self):
        email = _random_email()
        password = "loadtest123"
        self.client.post(
            "/users",
            json={"email": email, "name": "Load Test User", "password": password},
            name="/users [signup]",
        )
        response = self.client.post(
            "/auth/login", json={"email": email, "password": password}, name="/auth/login"
        )
        token = response.json().get("access_token") if response.status_code == 200 else None
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    @task(10)
    def health_check(self):
        # No auth required — the cheapest, most frequent request in any
        # real deployment (load balancer / uptime monitoring), and a
        # useful BASELINE: if /health's own latency rises under load,
        # the bottleneck is infrastructure-wide (event loop saturation,
        # CPU), not something specific to a heavier endpoint.
        self.client.get("/health", name="/health")

    @task(5)
    def ask_chat_question(self):
        self.client.post(
            "/chat",
            json={"question": "What does OpsMind do?"},
            headers=self.headers,
            name="/chat",
        )

    @task(3)
    def list_documents(self):
        self.client.get("/documents", headers=self.headers, name="/documents [list]")

    @task(2)
    def upload_document(self):
        files = {
            "file": (
                "loadtest.txt",
                b"OpsMind helps teams find operational bottlenecks. " * 20,
                "text/plain",
            )
        }
        self.client.post(
            "/documents", files=files, headers=self.headers, name="/documents [upload]"
        )
