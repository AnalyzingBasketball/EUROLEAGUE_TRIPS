import pandas as pd

from models.db import DEFAULT_DB_PATH, connect
from models.sqlite_model import METRICS_FILE, compute_metrics


def test_precomputed_metrics_match_a_fresh_calculation():
    """Si cambia la base o el cálculo y no se regenera el parquet, la app mostraría datos viejos: este test lo avisa."""
    fresh = compute_metrics(connect(DEFAULT_DB_PATH, read_only=True))
    stored = pd.read_parquet(METRICS_FILE)
    pd.testing.assert_frame_equal(stored.reset_index(drop=True), fresh.reset_index(drop=True), check_dtype=False)
