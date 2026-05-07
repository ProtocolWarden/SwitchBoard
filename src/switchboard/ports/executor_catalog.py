# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Velascat
"""ExecutorCatalog port — the three v1 queries SB consumes.

SwitchBoard does not import OperationsCenter's catalog implementation
directly. OC supplies an adapter implementing this protocol; SB calls
through it to validate/inform routing decisions.

The three queries match the catalog's V1 contract (see
OperationsCenter docs/architecture/backend_control_audit.md Phase 10).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExecutorCatalog(Protocol):
    def backends_supporting_runtime(self, *, runtime_kind: str) -> list[str]:
        ...

    def backends_supporting_capabilities(
        self, *, required_capabilities: Iterable[str]
    ) -> list[str]:
        ...

    def backends_by_outcome(self, *, outcome: str) -> list[str]:
        ...
