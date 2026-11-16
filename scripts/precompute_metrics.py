"""Precalcula las métricas y las guarda en app/data/metricas.parquet para que la app no las calcule al arrancar.

Uso: python scripts/precompute_metrics.py   (después de build_db.py, y siempre que cambie la base o build_metrics)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from models.db import DEFAULT_DB_PATH, connect
from models.sqlite_model import METRICS_FILE, compute_metrics


def main() -> None:
    metrics = compute_metrics(connect(DEFAULT_DB_PATH, read_only=True))
    metrics.to_parquet(METRICS_FILE, index=False)
    print(f"{METRICS_FILE}: {len(metrics)} filas, {METRICS_FILE.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
