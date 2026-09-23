"""ReplayService：历史 CSV 文件回放（P0 stub）。"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Iterator, List, Optional


@dataclass
class ReplayRow:
    ts_us: int
    ecg: List[float]
    matrix: List[float]
    piezo: List[float]
    hr: int


class ReplayService:
    def list_files(self, data_dir: str) -> List[str]:
        if not os.path.isdir(data_dir):
            return []
        return sorted(
            [f for f in os.listdir(data_dir) if f.endswith(".csv")],
            reverse=True,
        )

    def load(self, path: str) -> Iterator[ReplayRow]:
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield ReplayRow(
                    ts_us=int(row["ts_us"]),
                    ecg=[float(row[k]) for k in ("ecg1", "ecg2", "ecg3", "ecg4")],
                    matrix=[float(row[f"m{i}"]) for i in range(16)],
                    piezo=[float(row["piezo1"]), float(row["piezo2"])],
                    hr=int(row["hr"]),
                )
