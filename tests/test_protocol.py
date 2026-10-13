"""协议层：codec + parser + dispatcher + commands 的单元测试。"""

import struct

import pytest

from mac_pcq.protocol import Frame, FrameCodec
from mac_pcq.protocol.codec import HEADER_SIZE, CRC_SIZE
from mac_pcq.protocol.spec import (
    TYPE_DATA_ECG, TYPE_DATA_PVDF, TYPE_DATA_RESISTIVE,
    TYPE_HR_RR, TYPE_SYS_STATUS, TYPE_DEVICE_INFO,
    TYPE_ACK, TYPE_CMD, TYPE_PARAM_CFG,
    CMD_START_ACQ, CMD_PROBE, CFG_ECG_FS,
)
from mac_pcq.protocol.errors import (
    BadMagicError, CRCMismatchError, TruncatedFrameError, UnknownTypeError,
)
from mac_pcq.protocol.parsers import (
    ECGFrame, PVDFFrame, ResistiveFrame, VitalSigns,
    SystemStatus, DeviceInfo, AckFrame, parse,
)
from mac_pcq.protocol.dispatcher import FrameDispatcher
from mac_pcq.protocol.commands import CommandBuilder


# ===== CRC =====

def test_crc_known_vector():
    # CCITT-FALSE of "123456789" == 0x29B1
    assert FrameCodec.crc16_ccitt(b"123456789") == 0x29B1


def test_crc_empty_zero_init():
    # crc of empty with init 0xFFFF == 0xFFFF (no bits flipped)
    assert FrameCodec.crc16_ccitt(b"") == 0xFFFF


# ===== Frame round-trip =====

def test_frame_roundtrip_basic():
    f = Frame(type=TYPE_DATA_ECG, seq=42, ts_us=123456789, payload=b"\x01\x02\x03\x04")
    enc = f.encode()
    assert len(enc) == HEADER_SIZE + len(f.payload) + CRC_SIZE
    f2 = Frame.decode(enc)
    assert f2.type == f.type
    assert f2.seq == f.seq
    assert f2.ts_us == f.ts_us
    assert f2.payload == f.payload


def test_frame_roundtrip_empty_payload():
    f = Frame(type=TYPE_HEARTBEAT_FROM_PROTO if False else 0xF2, seq=1, ts_us=0, payload=b"")
    f2 = Frame.decode(f.encode())
    assert f2.type == 0xF2
    assert f2.payload == b""


def test_find_magic_present():
    buf = b"\x00\x00\x55\xaa\x01"
    assert FrameCodec.find_magic(buf) == 2


def test_find_magic_absent():
    assert FrameCodec.find_magic(b"\x00\x01\x02") == -1


def test_decode_bad_magic_raises():
    with pytest.raises(BadMagicError):
        Frame.decode(b"\x00\x00" + b"\x00" * 16 + b"\x00\x00")


def test_decode_bad_crc_raises():
    f = Frame(type=TYPE_DATA_ECG, seq=1, payload=b"abc")
    enc = f.encode()
    bad = enc[:-2] + b"\x00\x00"
    with pytest.raises(CRCMismatchError):
        Frame.decode(bad)


def test_decode_truncated_raises():
    f = Frame(type=TYPE_DATA_ECG, seq=1, payload=b"abc")
    with pytest.raises(TruncatedFrameError):
        Frame.decode(f.encode()[:10])


# ===== feed 累加解析 =====

def test_feed_single_frame():
    f = Frame(type=TYPE_DATA_ECG, seq=1, payload=b"\x01\x02\x03\x04")
    enc = f.encode()
    buf = bytearray()
    out = []
    FrameCodec.feed(buf, b"\x00\x00" + enc, lambda fr: out.append(fr))
    assert len(out) == 1
    assert out[0].seq == 1


def test_feed_two_frames_packet():
    f1 = Frame(type=TYPE_DATA_ECG, seq=1, payload=b"\x01")
    f2 = Frame(type=TYPE_DATA_ECG, seq=2, payload=b"\x02")
    buf = bytearray()
    out = []
    FrameCodec.feed(buf, f1.encode() + f2.encode(), lambda fr: out.append(fr))
    assert len(out) == 2
    assert out[0].seq == 1 and out[1].seq == 2


def test_feed_fragmented():
    f = Frame(type=TYPE_DATA_ECG, seq=1, payload=b"\x01\x02\x03\x04")
    enc = f.encode()
    buf = bytearray()
    out = []
    mid = len(enc) // 2
    FrameCodec.feed(buf, enc[:mid], lambda fr: out.append(fr))
    assert len(out) == 0
    FrameCodec.feed(buf, enc[mid:], lambda fr: out.append(fr))
    assert len(out) == 1


def test_feed_reports_crc_error():
    f = Frame(type=TYPE_DATA_ECG, seq=1, payload=b"abc")
    enc = f.encode()
    # 改最后一个字节让 CRC 失败
    bad = enc[:-1] + bytes([enc[-1] ^ 0xFF])
    buf = bytearray()
    out = []
    errs = []
    FrameCodec.feed(buf, bad, lambda fr: out.append(fr), lambda e, r: errs.append(e))
    assert len(out) == 0
    assert any(isinstance(e, CRCMismatchError) for e in errs)


# ===== Parsers =====

def test_ecg_parser():
    payload = struct.pack("<I", 100) + struct.pack("<4i", 1, 2, 3, 4)
    f = ECGFrame.from_payload(payload)
    assert f.seq == 100
    assert f.ch == (1, 2, 3, 4)


def test_pvdf_parser():
    payload = struct.pack("<I", 1) + struct.pack("<2i", 1000, -2000)
    f = PVDFFrame.from_payload(payload)
    assert f.ch == (1000, -2000)


def test_resistive_parser():
    payload = struct.pack("<I", 1) + struct.pack("<16H", *range(10000, 10016))
    f = ResistiveFrame.from_payload(payload)
    assert len(f.r_ohm) == 16
    assert f.r_ohm[0] == 10000


def test_vital_parser():
    payload = struct.pack("<IHHB", 1, 75, 20, 90)
    f = VitalSigns.from_payload(payload)
    assert f.hr_bpm == 75 and f.rr_bpm == 20 and f.quality == 90


def test_system_status_parser():
    payload = struct.pack("<I", 1) + struct.pack("<BBHHHBI B", 1, 86, 3850, 3300, 3300, 35, 1234, 0)
    s = SystemStatus.from_payload(payload)
    assert s.charging is True and s.level_pct == 86


def test_device_info_parser():
    payload = struct.pack("<I", 1) + struct.pack("<BBB", 1, 2, 3)
    payload += b"SN12345\x00" + b"\x00" * 8
    payload += b"HW-A\x00" + b"\x00" * 28
    d = DeviceInfo.from_payload(payload)
    assert d.fw_version == (1, 2, 3)
    assert d.serial == "SN12345"
    assert d.hw_id == "HW-A"


def test_unknown_type_raises():
    with pytest.raises(UnknownTypeError):
        parse(0x99, b"")


# ===== Dispatcher =====

def test_dispatcher_dispatches_known_type():
    disp = FrameDispatcher(on_payload=lambda t, s, m: None)
    payload = struct.pack("<I", 1) + struct.pack("<4i", 1, 2, 3, 4)
    f = Frame(type=TYPE_DATA_ECG, seq=10, payload=payload)
    got = []
    disp2 = FrameDispatcher(on_payload=lambda t, s, m: got.append((t, s, m)))
    disp2.feed(f.encode())
    assert len(got) == 1
    assert got[0][0] == TYPE_DATA_ECG
    assert isinstance(got[0][2], ECGFrame)


# ===== Commands =====

def test_cmd_start_acq():
    enc = CommandBuilder.start_acq(mode=1)
    f = Frame.decode(enc)
    assert f.type == TYPE_CMD
    cmd, mode = struct.unpack("<BB", f.payload)
    assert cmd == CMD_START_ACQ and mode == 1


def test_cmd_probe():
    enc = CommandBuilder.probe()
    f = Frame.decode(enc)
    assert f.type == TYPE_CMD
    cmd, _ = struct.unpack("<BB", f.payload)
    assert cmd == CMD_PROBE


def test_cfg_set_ecg_fs():
    enc = CommandBuilder.set_ecg_fs(250)
    f = Frame.decode(enc)
    assert f.type == TYPE_PARAM_CFG
    cfg, val = struct.unpack("<BI", f.payload)
    assert cfg == CFG_ECG_FS and val == 250
