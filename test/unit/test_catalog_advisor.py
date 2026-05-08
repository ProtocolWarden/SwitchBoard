# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Velascat
"""CatalogAdvisor tests — non-mutating advisory layer over LaneDecision."""
from __future__ import annotations

from collections.abc import Iterable

from switchboard.contracts import LaneDecision
from switchboard.contracts.enums import BackendName, LaneName

from switchboard.lane.catalog_advisor import (
    AdvisoryLevel,
    advise,
)


class FakeCatalog:
    """Minimal in-memory ExecutorCatalog satisfying the SB port."""

    def __init__(
        self,
        *,
        outcomes: dict[str, list[str]] | None = None,
        capabilities: dict[str, list[str]] | None = None,
        runtimes: dict[str, list[str]] | None = None,
    ) -> None:
        self._outcomes = outcomes or {}
        self._capabilities = capabilities or {}
        self._runtimes = runtimes or {}

    def backends_supporting_runtime(self, *, runtime_kind: str) -> list[str]:
        return list(self._runtimes.get(runtime_kind, []))

    def backends_supporting_capabilities(self, *, required_capabilities: Iterable[str]) -> list[str]:
        required = set(required_capabilities)
        return sorted(
            backend
            for backend, advertised in self._capabilities.items()
            if required.issubset(set(advertised))
        )

    def backends_by_outcome(self, *, outcome: str) -> list[str]:
        return list(self._outcomes.get(outcome, []))


def _decision(backend: str = "kodo", lane: str = "claude_cli") -> LaneDecision:
    return LaneDecision(
        proposal_id="p", selected_lane=LaneName(lane),
        selected_backend=BackendName(backend), confidence=0.9,
    )


class TestOutcomeAdvisories:
    def test_adapter_only_no_advisories(self):
        cat = FakeCatalog(outcomes={"adapter_only": ["kodo"]})
        out = advise(catalog=cat, decision=_decision("kodo"))
        assert out == []

    def test_adapter_plus_wrapper_emits_info(self):
        cat = FakeCatalog(outcomes={"adapter_plus_wrapper": ["kodo"]})
        out = advise(catalog=cat, decision=_decision("kodo"))
        assert len(out) == 1
        assert out[0].level == AdvisoryLevel.INFO
        assert out[0].code == "BACKEND_ADAPTER_PLUS_WRAPPER"

    def test_upstream_patch_pending_emits_warn(self):
        cat = FakeCatalog(outcomes={"upstream_patch_pending": ["archon"]})
        out = advise(catalog=cat, decision=_decision("archon"))
        assert any(a.level == AdvisoryLevel.WARN and a.code.startswith("BACKEND_UPSTREAM") for a in out)

    def test_fork_required_emits_block(self):
        cat = FakeCatalog(outcomes={"fork_required": ["openclaw"]})
        out = advise(catalog=cat, decision=_decision("openclaw"))
        assert any(a.level == AdvisoryLevel.BLOCK for a in out)

    def test_unknown_backend_emits_warn(self):
        # direct_local is a real BackendName but absent from this catalog mock
        cat = FakeCatalog()
        out = advise(catalog=cat, decision=_decision("direct_local"))
        assert any(a.code == "BACKEND_NOT_IN_CATALOG" for a in out)


class TestCapabilityAdvisories:
    def test_block_when_capability_missing(self):
        cat = FakeCatalog(
            outcomes={"adapter_only": ["kodo"]},
            capabilities={"kodo": ["repo_read"]},
        )
        out = advise(
            catalog=cat,
            decision=_decision("kodo"),
            required_capabilities={"repo_read", "repo_patch"},
        )
        assert any(a.code == "BACKEND_MISSING_CAPABILITIES" and a.level == AdvisoryLevel.BLOCK for a in out)

    def test_no_block_when_capabilities_satisfied(self):
        cat = FakeCatalog(
            outcomes={"adapter_only": ["kodo"]},
            capabilities={"kodo": ["repo_read", "repo_patch", "test_run"]},
        )
        out = advise(
            catalog=cat,
            decision=_decision("kodo"),
            required_capabilities={"repo_read", "repo_patch"},
        )
        assert all(a.code != "BACKEND_MISSING_CAPABILITIES" for a in out)


class TestRuntimeAdvisories:
    def test_block_when_runtime_unsupported(self):
        cat = FakeCatalog(
            outcomes={"adapter_plus_wrapper": ["kodo"]},
            runtimes={"cli_subscription": ["kodo"]},
        )
        out = advise(
            catalog=cat, decision=_decision("kodo"),
            requested_runtime_kind="hosted_api",
        )
        assert any(a.code == "BACKEND_MISSING_RUNTIME" and a.level == AdvisoryLevel.BLOCK for a in out)

    def test_no_block_when_runtime_supported(self):
        cat = FakeCatalog(
            outcomes={"adapter_plus_wrapper": ["kodo"]},
            runtimes={"cli_subscription": ["kodo"]},
        )
        out = advise(
            catalog=cat, decision=_decision("kodo"),
            requested_runtime_kind="cli_subscription",
        )
        assert all(a.code != "BACKEND_MISSING_RUNTIME" for a in out)
