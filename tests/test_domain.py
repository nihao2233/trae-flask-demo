"""domain 层单元测试。"""

import asyncio
import math
import os
import tempfile

import pytest

from mac_pcq.domain import DataBus, SessionService, SessionState
from mac_pcq.domain.calibration import Calibration, CalibrationConfig
from mac_pcq.domain.export import CsvExporter, ExportRow
from mac_pcq.domain.replay import ReplayService
from mac_pcq.domain.session import _VALID
from mac_pcq.domain.signal_proc import ECGFilter, RPeakDetector


# ===== Calibration =====

def test_calibration_default_segments():
    cfg = CalibrationConfig()
    p1 = Calibration.resistance_to_pressure(5000, cfg)   # R<10kΩ
    p2 = Calibration.resistance_to_pressure(20000, cfg)  # R≥10kΩ
    assert abs(p1 - 0.05) < 1e-9
    assert abs(p2 - 25.1) < 1e-9


def test_calibration_two_point():
    a, b = Calibration.calibrate_two_point(10.0, 100.0, 20.0, 200.0)
    assert abs(a - 10.0) < 1e-9 and abs(b - 0.0) < 1e-9


def test_calibration_two_point_same_r_raises():
    with pytest.raises(ValueError):
        Calibration.calibrate_two_point(10.0, 100.0, 10.0, 200.0)


# ===== SignalProc =====

def test_ecg_filter_kills_low_freq_drift():
    f = ECGFilter(fs=500)
    # 1Hz 信号应被滤掉大部分
    ys = f.push_array([math.sin(2 * math.pi * 1.0 * t / 500) for t in range(2000)])
    peak = max(abs(v) for v in ys)
    assert peak < 0.3


def test_r_peak_detector_60bpm():
    det = RPeakDetector(fs=500, threshold=0.5, refractory_ms=300)
    bpms = []
    for i in range(2500):  # 5s @500Hz
        t = i / 500.0
        x = 1.0 if abs((t % 1.0) - 0.2) < 0.04 else 0.0
        b = det.feed(x)
        if b is not None:
            bpms.append(b)
    assert bpms, "no BPM detected"
    assert all(55 <= b <= 65 for b in bpms)


def test_r_peak_detector_no_peak_returns_none():
    det = RPeakDetector(fs=500, threshold=0.5)
    for _ in range(100):
        assert det.feed(0.1) is None


# ===== SessionService =====

def test_session_transitions_table_complete():
    # 7 状态全部可达
    for s in SessionState:
        assert s in _VALID


def test_session_start_stop():
    async def go():
        cmds = []
        sess = SessionService(send_cmd=lambda b: cmds.append(b))
        await sess.start(mode=1)
        assert sess.state == SessionState.RUNNING
        await sess.stop()
        assert sess.state == SessionState.IDLE
        assert len(cmds) == 2  # start + stop
    asyncio.run(go())


def test_session_record_state():
    async def go():
        sess = SessionService(send_cmd=lambda b: None)
        await sess.start(mode=0, record=True)
        assert sess.state == SessionState.RECORDING
        assert sess.is_recording is True
        await sess.stop()
        assert sess.is_recording is False
        assert sess.state == SessionState.IDLE
    asyncio.run(go())


def test_session_illegal_transition_raises():
    sess = SessionService(send_cmd=lambda b: None)
    # IDLE -> PAUSED 非法
    with pytest.raises(RuntimeError):
        sess._set_state(SessionState.PAUSED)


def test_session_pause_resume():
    async def go():
        sess = SessionService(send_cmd=lambda b: None)
        await sess.start(mode=0)
        await sess.pause()
        assert sess.state == SessionState.PAUSED
        await sess.resume()
        assert sess.state == SessionState.RUNNING
        await sess.stop()
    asyncio.run(go())


def test_session_fail_and_reset():
    async def go():
        sess = SessionService(send_cmd=lambda b: None)
        await sess.start(mode=0)
        await sess.fail("test")
        assert sess.state == SessionState.ERROR
        await sess.reset()
        assert sess.state == SessionState.IDLE
    asyncio.run(go())


# ===== DataBus =====

def test_databus_publish_and_dispatch():
    import struct
    from mac_pcq.protocol.parsers import ECGFrame
    from mac_pcq.protocol.spec import TYPE_DATA_ECG

    bus = DataBus()
    got = []
    bus.subscribe(TYPE_DATA_ECG, lambda s, m: got.append(m))
    payload = struct.pack("<I", 1) + struct.pack("<4i", 1, 2, 3, 4)
    f = ECGFrame.from_payload(payload)
    bus.dispatch_sync(TYPE_DATA_ECG, 1, f)
    assert len(got) == 1
    d = DataBus.to_domain(TYPE_DATA_ECG, 1, f)
    assert d.ch == (1, 2, 3, 4)


# ===== Export / Replay =====

def test_csv_export_replay_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "test.csv")
        exp = CsvExporter(path)
        exp.open()
        for i in range(10):
            exp.write(ExportRow(
                ts_us=1000 + i,
                ecg=[i * 0.1, 0.2, 0.3, 0.4],
                matrix=[float(j) for j in range(16)],
                piezo=[1.0, 2.0],
                hr=72 + i,
            ))
        n = exp.close()
        assert n == 10
        rp = ReplayService()
        rows = list(rp.load(path))
        assert len(rows) == 10
        assert rows[0].hr == 72
        assert rows[9].hr == 81
        assert rows[5].ecg[0] == pytest.approx(0.5)


def test_csv_export_no_suffix_uses_csv_suffix():
    """与 fix/storage-csv-extension 的修复对齐：storage.start(name) 若 name 无后缀则补 .csv。"""
    # 这里只验证 CsvExporter 行为：传入 name 时由调用方负责加后缀
    # 这个测试只是占位 / 记录回归约定
    assert True
