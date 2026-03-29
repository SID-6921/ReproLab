"""Core data models for corrections, logging, and lineage."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class CorrectionRecord:
    """Represents a single cell-level correction."""

    row_index: int
    column: str
    original_value: Any
    corrected_value: Any
    constraint_name: str
    rationale: str
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        """Convert the record into a JSON-serializable dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class LineageRecord:
    """Captures deterministic metadata for reproducibility."""

    dataset_hash_before: str
    dataset_hash_after: str
    step_name: str
    step_version: str
    timestamp_utc: str
    deterministic_signature: str

    @staticmethod
    def now_iso() -> str:
        """Return an ISO timestamp in UTC."""
        return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ValidationDecision:
    """Describes the outcome of a candidate correction."""

    accepted_value: Any
    confidence: float
    conflict_with: Optional[str] = None
