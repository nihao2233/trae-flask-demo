"""ExportService：CSV / PNG / HDF5 导出（本轮仅 CSV 完整实现）。

CSV 列：ts_us, ecg1..ecg4, m0..m15, piezo1, piezo2, hr
"""

from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..core.logger import get_logger

_log = get_logger("domain.export")


@dataclass
class ExportRow:
    ts_us: int
    ecg: List[float]
    matrix: List[float]
    piezo: List[float]
    hr: int


class CsvExporter:
    """流式 CSV 写出（P0 完整）。"""

    COLUMNS = (
        ["ts_us", "ecg1", "ecg2", "ecg3", "ecg4"]
        + [f"m{i}" for i in range(16)]
        + ["piezo1", "piezo2", "hr"]
    )

    def __init__(self, path: str) -> None:
        self.path = path
        self._f = None
        self._w = None
        self._count = 0

    def open(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._f = open(self.path, "w", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        self._w.writerow(self.COLUMNS)
        self._f.flush()

    def write(self, row: ExportRow) -> None:
        if self._w is None:
            raise RuntimeError("CsvExporter not opened")
        rec = (
            [row.ts_us]
            + list(row.ecg)
            + list(row.matrix)
            + list(row.piezo)
            + [row.hr]
        )
        self._w.writerow(rec)
        self._count += 1

    def flush(self) -> None:
        if self._f:
            self._f.flush()

    def close(self) -> int:
        if self._f:
            self._f.close()
        return self._count


class ExportService:
    """对外门面：根据 format 调用对应实现。"""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir or os.path.join(os.path.expanduser("~"), ".mac_pcq", "data")
        os.makedirs(self.data_dir, exist_ok=True)

    def new_csv(self, name: Optional[str] = None) -> CsvExporter:
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = (name or f"record_{ts}") + ".csv"
        path = os.path.join(self.data_dir, filename)
        exp = CsvExporter(path)
        exp.open()
        return exp

    def export_png(self, page_snapshot, path: str) -> None:
        """PNG 导出留 stub。"""
        _log.warning("PNG export not implemented (P2)")

    def export_hdf5(self, session, path: str) -> None:
        """HDF5 导出留 stub。"""
        _log.warning("HDF5 export not implemented (P2)")
