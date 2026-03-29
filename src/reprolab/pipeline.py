"""Top-level ReproLab pipeline orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from .constraints.base import ClinicalConstraint
from .lineage.logger import TransformationLogger
from .lineage.tracker import LineageTracker
from .models import CorrectionRecord
from .preprocessing import DataPreprocessor, PreprocessingConfig
from .validation.engine import ValidationEngine

LOGGER = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Container for pipeline outputs."""

    cleaned_data: pd.DataFrame
    transformation_log: pd.DataFrame
    lineage_history: list[dict[str, str]]


class ReproLabPipeline:
    """Runs preprocessing + validation with explainable logging and lineage."""

    def __init__(
        self,
        constraints: list[ClinicalConstraint],
        preprocess_config: PreprocessingConfig | None = None,
    ) -> None:
        self.preprocessor = DataPreprocessor(preprocess_config)
        self.validator = ValidationEngine(constraints)
        self.transform_logger = TransformationLogger()
        self.lineage = LineageTracker()

    def run(self, df: pd.DataFrame) -> PipelineResult:
        """Run ReproLab pipeline deterministically and return full outputs."""
        raw = df.copy(deep=True)

        preprocessed, pre_logs = self.preprocessor.process(raw)
        self._record_step(raw, preprocessed, "preprocessing", "1.0.0", pre_logs)

        validated, val_logs = self.validator.validate_and_correct(preprocessed)
        self._record_step(
            preprocessed, validated, "clinical_validation", "1.0.0", val_logs
        )

        return PipelineResult(
            cleaned_data=validated,
            transformation_log=self.transform_logger.to_frame(),
            lineage_history=self.lineage.history(),
        )

    def export_logs(self, json_path: str, csv_path: str) -> None:
        """Export transformation log in JSON and CSV formats."""
        self.transform_logger.export_json(json_path)
        self.transform_logger.export_csv(csv_path)

    def _record_step(
        self,
        before: pd.DataFrame,
        after: pd.DataFrame,
        step_name: str,
        step_version: str,
        records: list[CorrectionRecord],
    ) -> None:
        self.transform_logger.add(records)
        self.lineage.add_step(before, after, step_name, step_version)
        LOGGER.info("Recorded step %s with %d corrections", step_name, len(records))
