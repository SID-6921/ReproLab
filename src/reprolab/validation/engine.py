"""Clinically-constrained validation engine with conflict resolution."""

from __future__ import annotations

import logging
from collections import defaultdict

import pandas as pd

from ..constraints.base import CandidateCorrection, ClinicalConstraint
from ..models import CorrectionRecord

LOGGER = logging.getLogger(__name__)


class ValidationEngine:
    """Runs constraints and resolves correction conflicts deterministically."""

    def __init__(self, constraints: list[ClinicalConstraint]) -> None:
        self.constraints = constraints

    def validate_and_correct(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[CorrectionRecord]]:
        """Apply constraints, resolve candidate conflicts, and return corrections."""
        working = df.copy(deep=True)
        all_candidates: list[CandidateCorrection] = []
        for constraint in self.constraints:
            result = constraint.apply(working)
            all_candidates.extend(result.candidates)

        grouped: dict[tuple[int, str], list[CandidateCorrection]] = defaultdict(list)
        for candidate in all_candidates:
            grouped[(candidate.row_index, candidate.column)].append(candidate)

        logs: list[CorrectionRecord] = []
        for (row_idx, col), candidates in grouped.items():
            winner = self._select_winner(candidates)
            original = working.at[row_idx, col]
            if original == winner.proposed_value:
                continue
            working.at[row_idx, col] = winner.proposed_value
            conflict_note = ""
            if len(candidates) > 1:
                conflict_note = " Conflict resolved by highest confidence."
            logs.append(
                CorrectionRecord(
                    row_index=row_idx,
                    column=col,
                    original_value=original,
                    corrected_value=winner.proposed_value,
                    constraint_name=winner.constraint_name,
                    rationale=f"{winner.rationale}{conflict_note}",
                    confidence=winner.confidence,
                )
            )

        LOGGER.info("Validation complete with %d accepted corrections", len(logs))
        return working, logs

    @staticmethod
    def _select_winner(candidates: list[CandidateCorrection]) -> CandidateCorrection:
        """Deterministically pick correction candidate by confidence then name."""
        ordered = sorted(
            candidates,
            key=lambda c: (-c.confidence, c.constraint_name, str(c.proposed_value)),
        )
        return ordered[0]
