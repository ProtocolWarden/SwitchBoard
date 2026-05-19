# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""Tests for LaneDecision.metadata — worker_backend injection by LaneSelector."""

from __future__ import annotations

from switchboard.contracts import LaneDecision, TaskProposal
from switchboard.contracts.common import TaskTarget
from switchboard.contracts.enums import (
    BackendName,
    ExecutionMode,
    LaneName,
    Priority,
    RiskLevel,
    TaskType,
)
from switchboard.lane.engine import LaneSelector
from switchboard.lane.policy import FallbackPolicy, LaneRoutingPolicy, LaneRule


def _target() -> TaskTarget:
    return TaskTarget(
        repo_key="svc",
        clone_url="https://git.example.com/svc.git",
        base_branch="main",
    )


def _proposal(task_type=TaskType.BUG_FIX, risk_level=RiskLevel.LOW) -> TaskProposal:
    return TaskProposal(
        task_id="T-1",
        proposal_id="P-1",
        project_id="proj-1",
        goal_text="fix something",
        task_type=task_type,
        risk_level=risk_level,
        priority=Priority.NORMAL,
        execution_mode=ExecutionMode.GOAL,
        target=_target(),
    )


def _policy_routing_to(lane: str, backend: str) -> LaneRoutingPolicy:
    return LaneRoutingPolicy(
        version="1",
        rules=[
            LaneRule(
                name="test_rule",
                priority=10,
                select_lane=lane,
                select_backend=backend,
                when={},
                confidence=1.0,
            )
        ],
        fallback=FallbackPolicy(lane="claude_cli", backend="team_executor"),
    )


def test_metadata_has_worker_backend():
    selector = LaneSelector()
    decision = selector.select(_proposal())
    assert "worker_backend" in decision.metadata


def test_claude_cli_lane_emits_claude_code():
    policy = _policy_routing_to("claude_cli", "team_executor")
    selector = LaneSelector(policy=policy)
    decision = selector.select(_proposal())
    assert decision.selected_lane == LaneName.CLAUDE_CLI
    assert decision.metadata["worker_backend"] == "claude_code"


def test_codex_cli_lane_emits_codex_cli():
    policy = _policy_routing_to("codex_cli", "team_executor")
    selector = LaneSelector(policy=policy)
    decision = selector.select(_proposal())
    assert decision.selected_lane == LaneName.CODEX_CLI
    assert decision.metadata["worker_backend"] == "codex_cli"


def test_aider_local_lane_emits_claude_code():
    policy = _policy_routing_to("aider_local", "aider_local")
    selector = LaneSelector(policy=policy)
    decision = selector.select(_proposal())
    assert decision.metadata["worker_backend"] == "claude_code"


def test_lane_decision_metadata_is_dict():
    selector = LaneSelector()
    decision = selector.select(_proposal())
    assert isinstance(decision.metadata, dict)


def test_default_policy_decisions_always_have_worker_backend():
    selector = LaneSelector()
    from switchboard.contracts.enums import TaskType, RiskLevel
    for task_type in [TaskType.BUG_FIX, TaskType.FEATURE, TaskType.LINT_FIX, TaskType.REFACTOR]:
        proposal = _proposal(task_type=task_type, risk_level=RiskLevel.LOW)
        decision = selector.select(proposal)
        assert "worker_backend" in decision.metadata, f"Missing for task_type={task_type}"
