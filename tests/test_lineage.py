from __future__ import annotations

import pandas as pd
from reprolab.lineage.tracker import LineageTracker


def test_lineage_hash_is_deterministic_for_same_input() -> None:
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    h1 = LineageTracker.dataset_hash(df)
    h2 = LineageTracker.dataset_hash(df)
    assert h1 == h2


def test_lineage_tracks_step_metadata() -> None:
    before = pd.DataFrame({"a": [1, 2]})
    after = pd.DataFrame({"a": [1, 3]})
    tracker = LineageTracker()
    tracker.add_step(before, after, "test_step", "1.0.0")
    history = tracker.history()
    assert len(history) == 1
    assert history[0]["step_name"] == "test_step"
