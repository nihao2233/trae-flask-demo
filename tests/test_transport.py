"""transport 层单元测试（仅 SimAdapter，不依赖硬件）。"""

import asyncio

import pytest

from mac_pcq.protocol.codec import Frame
from mac_pcq.protocol.spec import (
    TYPE_DATA_ECG, TYPE_DATA_PVDF, TYPE_DATA_RESISTIVE,
    TYPE_HR_RR, TYPE_SYS_STATUS, TYPE_DEVICE_INFO,
)
from mac_pcq.transport.adapter import LinkState
from mac_pcq.transport.manager import ConnectionManager
from mac_pcq.transport.sim import SimAdapter


@pytest.mark.asyncio
async def test_sim_streams_all_types():
    rx = []
    sim = SimAdapter(ecg_fs=50, pvdf_fs=50, resistive_fs=10, vital_period_s=0.2)

    mgr = ConnectionManager(sim, on_data=lambda b: rx.append(b))
    await mgr.start()
    await asyncio.sleep(0.6)
    await mgr.stop()

    types = {}
    for chunk in rx:
        buf = bytearray(chunk)
        while True:
            idx = buf.find(b"\x55\xaa")
            if idx < 0:
                break
            try:
                total_size, _ = Frame.decode_header(bytes(buf[idx:]))
            except Exception:
                del buf[:idx + 1]
                continue
            if len(buf) < idx + total_size:
                break
            try:
                f = Frame.decode(bytes(buf[idx:idx + total_size]))
                types[f.type] = types.get(f.type, 0) + 1
                del buf[:idx + total_size]
            except Exception:
                del buf[:idx + 1]
    assert types.get(TYPE_DATA_ECG, 0) > 0
    assert types.get(TYPE_DATA_PVDF, 0) > 0
    assert types.get(TYPE_DATA_RESISTIVE, 0) > 0
    assert types.get(TYPE_HR_RR, 0) > 0
    assert types.get(TYPE_SYS_STATUS, 0) > 0
    assert types.get(TYPE_DEVICE_INFO, 0) > 0


@pytest.mark.asyncio
async def test_sim_state_progression():
    seen = []
    sim = SimAdapter(ecg_fs=20, pvdf_fs=20, resistive_fs=5, vital_period_s=0.5)
    mgr = ConnectionManager(sim, on_data=lambda b: None, on_state=lambda s: seen.append(s))
    await mgr.start()
    await asyncio.sleep(0.3)
    await mgr.stop()
    # CONNECTING 可能因为 await sleep(0.05) 而被旁路；至少要看到 CONNECTED/STREAMING/DISCONNECTED
    assert LinkState.STREAMING in seen
    assert LinkState.CONNECTED in seen
    assert seen[-1] == LinkState.DISCONNECTED


@pytest.mark.asyncio
async def test_sim_write_consumes_command():
    sim = SimAdapter()
    await sim.connect()
    n = await sim.write(b"\x00\x00")
    assert n == 2
    await sim.disconnect()
