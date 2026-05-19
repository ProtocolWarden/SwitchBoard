# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""
lane/defaults.py — default lane routing policy.

This policy is used when no external config file is provided.
It encodes the intended routing tendencies of the platform:

  low-risk, bounded, local-acceptable  → aider_local + direct_local
  medium implementation work           → claude_cli + team_executor
  structured premium workflow          → claude_cli + dag_executor
  explicit premium task types          → claude_cli + team_executor (fallback)

Rules are evaluated in ascending priority order (lower number = higher priority).
"""

from __future__ import annotations

from .policy import (
    AlternativeRoute,
    BackendRule,
    DecisionThresholds,
    FallbackPolicy,
    LaneRoutingPolicy,
    LaneRule,
)

DEFAULT_POLICY = LaneRoutingPolicy(
    version="1",
    rules=[
        # ----------------------------------------------------------------
        # Priority 10 — force_local_only: explicit local-only constraint
        # ----------------------------------------------------------------
        LaneRule(
            name="force_local_only",
            priority=10,
            select_lane="aider_local",
            select_backend="aider_local",
            when={"local_only": True},
            confidence=1.0,
            description="Proposal explicitly requires local-only execution.",
        ),

        # ----------------------------------------------------------------
        # Priority 20 — low-risk local tasks
        # ----------------------------------------------------------------
        LaneRule(
            name="local_low_risk",
            priority=20,
            select_lane="aider_local",
            select_backend="aider_local",
            when={
                "task_type": ["lint_fix", "documentation", "simple_edit"],
                "max_risk_level": "low",
            },
            confidence=0.95,
            description=(
                "Low-risk, bounded task suitable for local execution at zero marginal cost."
            ),
        ),

        # ----------------------------------------------------------------
        # Priority 30 — medium implementation work (test writing, bug fixes)
        # ----------------------------------------------------------------
        LaneRule(
            name="medium_implementation",
            priority=30,
            select_lane="claude_cli",
            select_backend="team_executor",
            when={
                "task_type": ["bug_fix", "test_write", "dependency_update"],
                "risk_level": ["low", "medium"],
            },
            confidence=0.90,
            description="Medium implementation work; team_executor execution under Claude CLI lane.",
        ),

        # ----------------------------------------------------------------
        # Priority 40 — structured premium workflows (refactor / feature)
        # ----------------------------------------------------------------
        LaneRule(
            name="premium_structured",
            priority=40,
            select_lane="claude_cli",
            select_backend="dag_executor",
            when={
                "task_type": ["refactor", "feature"],
                "risk_level": ["medium", "high"],
            },
            confidence=0.85,
            description=(
                "High-complexity structured task; Archon workflow wrapper over team_executor execution."
            ),
        ),

        # ----------------------------------------------------------------
        # Priority 50 — high-risk escalation: anything high-risk goes premium
        # ----------------------------------------------------------------
        LaneRule(
            name="high_risk_escalation",
            priority=50,
            select_lane="claude_cli",
            select_backend="team_executor",
            when={"risk_level": "high"},
            confidence=0.92,
            description="High-risk task escalated to premium lane regardless of type.",
        ),

        # ----------------------------------------------------------------
        # Priority 60 — catch-all for remaining local-eligible types
        # ----------------------------------------------------------------
        LaneRule(
            name="local_catchall",
            priority=60,
            select_lane="aider_local",
            select_backend="aider_local",
            when={
                "task_type": ["lint_fix", "documentation", "simple_edit"],
            },
            confidence=0.80,
            description=(
                "Local-eligible type with relaxed risk constraint; prefer local."
            ),
        ),
    ],

    backend_rules=[
        # When codex_cli is selected and risk is low, prefer team_executor over dag_executor
        BackendRule(
            name="codex_team_executor_low_risk",
            lane="codex_cli",
            select_backend="team_executor",
            when={"risk_level": ["low", "medium"]},
            description="Prefer lightweight team_executor execution for codex lane on low/medium risk.",
        ),
    ],

    fallback=FallbackPolicy(
        lane="claude_cli",
        backend="team_executor",
        rationale="Default fallback: no policy rule matched; using premium lane with team_executor.",
    ),

    thresholds=DecisionThresholds(
        min_confidence_to_select=0.0,
        local_lane_max_risk="low",
    ),

    excluded_backends=[],

    alternative_routes=[
        # ----------------------------------------------------------------
        # FALLBACK routes
        # ----------------------------------------------------------------

        # When primary is local, fall back to premium lane if local unavailable.
        # Blocked by local_only and no_remote labels (explicit constraint).
        AlternativeRoute(
            name="local_to_remote_fallback",
            lane="claude_cli",
            backend="team_executor",
            role="fallback",
            cost_class="medium",
            capability_class="enhanced",
            from_lanes=["aider_local"],
            blocked_by_labels=["local_only", "no_remote"],
            priority=10,
            confidence=0.85,
            reason="Premium lane available if local execution is unavailable or produces poor results.",
            notes="Only use if local execution attempt has failed or is explicitly unavailable.",
        ),

        # When primary is the dag_executor workflow backend, fall back to
        # plain team_executor in the same lane (lighter, without workflow orchestration).
        AlternativeRoute(
            name="workflow_to_team_executor_fallback",
            lane="claude_cli",
            backend="team_executor",
            role="fallback",
            cost_class="medium",
            capability_class="enhanced",
            from_lanes=["claude_cli"],
            from_backends=["dag_executor"],
            blocked_by_labels=[],
            priority=10,
            confidence=0.80,
            reason="Lightweight team_executor execution if Archon workflow backend is unavailable.",
        ),

        # ----------------------------------------------------------------
        # ESCALATION routes
        # ----------------------------------------------------------------

        # Local primary + medium/high risk → escalate to premium lane.
        # Only relevant when the primary is local (low-risk path).
        # Blocked by local_only and no_remote constraints.
        AlternativeRoute(
            name="local_to_premium_escalation",
            lane="claude_cli",
            backend="team_executor",
            role="escalation",
            cost_class="medium",
            capability_class="enhanced",
            from_lanes=["aider_local"],
            applies_when={"risk_level": ["medium", "high"]},
            blocked_by_labels=["local_only", "no_remote"],
            priority=10,
            confidence=0.90,
            reason=(
                "Higher risk level warrants escalation to a premium lane "
                "with stronger reasoning capability."
            ),
        ),

        # team_executor primary + refactor/feature task type → escalate to workflow backend.
        # Structured workflow orchestration adds validation discipline for complex changes.
        # Not offered for simple task types — cost must be justified.
        AlternativeRoute(
            name="team_executor_to_workflow_for_complex_task",
            lane="claude_cli",
            backend="dag_executor",
            role="escalation",
            cost_class="high",
            capability_class="workflow",
            from_lanes=["claude_cli"],
            from_backends=["team_executor"],
            applies_when={"task_type": ["refactor", "feature"]},
            blocked_by_labels=["local_only", "no_remote"],
            priority=10,
            confidence=0.85,
            reason=(
                "Complex structural change benefits from Archon's structured workflow "
                "(plan → execute → validate) to reduce the risk of partial or inconsistent edits."
            ),
            notes="Only warranted when task is a refactor or feature; not for simpler task types.",
        ),

        # team_executor primary + high risk → escalate to workflow backend.
        # High-risk work benefits from workflow discipline regardless of task type.
        AlternativeRoute(
            name="team_executor_to_workflow_for_high_risk",
            lane="claude_cli",
            backend="dag_executor",
            role="escalation",
            cost_class="high",
            capability_class="workflow",
            from_lanes=["claude_cli"],
            from_backends=["team_executor"],
            applies_when={"risk_level": "high"},
            blocked_by_labels=["local_only", "no_remote"],
            priority=20,
            confidence=0.88,
            reason=(
                "High-risk change benefits from structured workflow orchestration "
                "to enforce disciplined execution and validation steps."
            ),
        ),
    ],
)
