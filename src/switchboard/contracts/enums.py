# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 ProtocolWarden
"""SwitchBoard-owned routing vocabulary.

These enums define the values SwitchBoard uses for lane selection and
routing policy evaluation. They are intentionally SB-owned rather than
imported from OperationsCenter — SB must not depend on OC types.

Values are kept in sync with the platform by convention; a mismatch
surfaces as a test or integration failure, not a compile-time error.
"""
from __future__ import annotations

from enum import Enum


class TaskType(str, Enum):
    LINT_FIX = "lint_fix"
    BUG_FIX = "bug_fix"
    SIMPLE_EDIT = "simple_edit"
    TEST_WRITE = "test_write"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    FEATURE = "feature"
    DEPENDENCY_UPDATE = "dependency_update"
    UNKNOWN = "unknown"


class LaneName(str, Enum):
    CLAUDE_CLI = "claude_cli"
    CODEX_CLI = "codex_cli"
    AIDER_LOCAL = "aider_local"


class BackendName(str, Enum):
    DIRECT_LOCAL = "direct_local"
    AIDER_LOCAL = "aider_local"
    KODO = "kodo"
    ARCHON = "archon"
    ARCHON_THEN_KODO = "archon_then_kodo"
    OPENCLAW = "openclaw"
    DEMO_STUB = "demo_stub"


class ExecutionMode(str, Enum):
    GOAL = "goal"
    FIX_PR = "fix_pr"
    TEST_CAMPAIGN = "test_campaign"
    IMPROVE_CAMPAIGN = "improve_campaign"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
