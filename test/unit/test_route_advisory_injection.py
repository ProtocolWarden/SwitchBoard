# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""R4 — /route endpoint surfaces catalog advisories under metadata."""
from __future__ import annotations

from fastapi.testclient import TestClient

from switchboard.app import create_app


def _proposal() -> dict:
    return {
        "task_id": "route-advisory-1",
        "project_id": "advisory-test",
        "task_type": "documentation",
        "execution_mode": "goal",
        "goal_text": "Refresh the architecture summary",
        "target": {
            "repo_key": "docs",
            "clone_url": "https://example.invalid/docs.git",
            "base_branch": "main",
            "allowed_paths": [],
        },
        "priority": "normal",
        "risk_level": "low",
        "constraints": {"allowed_paths": [], "require_clean_validation": True},
        "validation_profile": {"profile_name": "default", "commands": []},
        "branch_policy": {"push_on_success": True, "open_pr": False},
        "labels": [],
    }


class _StubCatalog:
    def __init__(self, *, fork: list[str] = (), wrapper: list[str] = (), patch: list[str] = ()):
        self._fork = list(fork)
        self._wrapper = list(wrapper)
        self._patch = list(patch)

    def backends_supporting_runtime(self, *, runtime_kind: str) -> list[str]:
        return []

    def backends_supporting_capabilities(self, *, required_capabilities) -> list[str]:
        return []

    def backends_by_outcome(self, *, outcome: str) -> list[str]:
        return {
            "fork_required": self._fork,
            "adapter_plus_wrapper": self._wrapper,
            "upstream_patch_pending": self._patch,
            "adapter_only": [],
        }.get(outcome, [])


def test_route_omits_advisories_when_no_catalog():
    """Default app has no executor_catalog wired — route returns no advisories."""
    with TestClient(create_app()) as client:
        response = client.post("/route", json=_proposal())
    data = response.json()
    assert "metadata" in data
    assert "catalog_advisories" not in data["metadata"]


def test_route_emits_block_advisory_for_fork_required_backend():
    app = create_app()
    # The default selector picks (aider_local, direct_local) for the test
    # proposal; mark direct_local as fork_required to force a BLOCK.
    app.state.executor_catalog = _StubCatalog(fork=["direct_local"])
    with TestClient(app) as client:
        response = client.post("/route", json=_proposal())
    advisories = response.json()["metadata"]["catalog_advisories"]
    assert any(a["level"] == "block" and a["code"] == "BACKEND_FORK_REQUIRED" for a in advisories)


def test_route_emits_info_advisory_for_wrapper_backend():
    app = create_app()
    app.state.executor_catalog = _StubCatalog(wrapper=["direct_local"])
    with TestClient(app) as client:
        response = client.post("/route", json=_proposal())
    advisories = response.json()["metadata"]["catalog_advisories"]
    assert any(a["level"] == "info" and "WRAPPER" in a["code"] for a in advisories)
