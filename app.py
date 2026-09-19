"""Flask 入口：路由 + SSE 实时推送 + 记录/导出/回放 API。

启动:
    python app.py
    浏览器访问 http://127.0.0.1:5000/
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
    stream_with_context,
)

from core.business import BusinessService
from core.device import SimDevice
from core.storage import StorageService

app = Flask(__name__)

# 禁用模板缓存，确保模板修改立即生效
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # 禁用静态文件缓存

# 导航图标映射
NAV_ICONS = {
    "index": "📊", "matrix": "▦", "piezo": "〰", "vitals": "♥",
    "replay": "⏮", "device": "🔌", "config": "⚙", "upgrade": "⬆", "logs": "☰",
}


@app.context_processor
def inject_icons():
    return {"nav_icons": NAV_ICONS}


# 全局共享对象（演示用单例即可；后续可放进 application context）
device = SimDevice(sample_rate=500)
business = BusinessService(sample_rate=device.sample_rate)
storage = StorageService()

# 当前显示模式：电阻 / 压力
MATRIX_MODE = "resistance"


# ---------- 页面路由（9 个页面）-------------------------------------------
PAGES = [
    ("index", "主监测", "monitor"),
    ("matrix", "压阻矩阵", "matrix"),
    ("piezo", "压电波形", "piezo"),
    ("vitals", "生命体征", "vitals"),
    ("replay", "记录回放", "replay"),
    ("device", "设备状态", "device"),
    ("config", "参数配置", "config"),
    ("upgrade", "固件升级", "upgrade"),
    ("logs", "日志", "logs"),
]


def _nav(active: str):
    return [{"id": i, "label": l, "active": i == active} for i, l, _ in PAGES]


@app.route("/")
def index():
    return render_template("index.html", nav=_nav("index"))


@app.route("/matrix")
def matrix_page():
    return render_template("matrix.html", nav=_nav("matrix"))


@app.route("/piezo")
def piezo_page():
    return render_template("piezo.html", nav=_nav("piezo"))


@app.route("/vitals")
def vitals_page():
    return render_template("vitals.html", nav=_nav("vitals"))


@app.route("/replay")
def replay_page():
    return render_template("replay.html", nav=_nav("replay"))


@app.route("/device")
def device_page():
    return render_template("device.html", nav=_nav("device"))


@app.route("/config")
def config_page():
    return render_template("config.html", nav=_nav("config"))


@app.route("/upgrade")
def upgrade_page():
    return render_template("upgrade.html", nav=_nav("upgrade"))


@app.route("/logs")
def logs_page():
    return render_template("logs.html", nav=_nav("logs"))


# ---------- SSE 实时数据流 -------------------------------------------------
@app.route("/stream")
def stream():
    """SSE：每个事件推送一个采样点 JSON。

    前端通过 EventSource 订阅，事件名 `sample`。
    """

    def gen():
        sample_rate = device.sample_rate
        # 控制推送速率：演示时按 ~50Hz 下推一批采样点，否则浏览器吃不消
        batch = max(1, sample_rate // 50)
        while True:
            samples: List[Dict[str, Any]] = []
            for _ in range(batch):
                s = device.next_sample()
                ecg_f = [business.filter_ecg(i, v) for i, v in enumerate(s["ecg"])]
                piezo_f = [business.filter_piezo(i, v) for i, v in enumerate(s["piezo"])]
                hr = business.estimate_hr(ecg_f[0])
                matrix = s["matrix"]
                samples.append(
                    {
                        "t": round(s["t"], 4),
                        "ecg": [round(v, 5) for v in ecg_f],
                        "matrix": [round(v, 3) for v in matrix],
                        "piezo": [round(v, 4) for v in piezo_f],
                        "hr": hr,
                    }
                )
                # 同步落盘 CSV（如果正在记录）
                if storage.is_recording:
                    storage.write(ecg_f, matrix, piezo_f, hr or 0)
            payload = json.dumps(
                {
                    "samples": samples,
                    "matrix_mode": MATRIX_MODE,
                    "is_recording": storage.is_recording,
                    "record_file": storage.current_filename,
                },
                ensure_ascii=False,
            )
            yield f"event: sample\ndata: {payload}\n\n"
            # 间隔约 20ms，模拟 50Hz 推送节奏
            time.sleep(0.02)

    return Response(
        stream_with_context(gen()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------- 记录 / 停止 ----------------------------------------------------
@app.route("/api/record/start", methods=["POST"])
def record_start():
    name = (request.json or {}).get("name")
    try:
        fn = storage.start(name)
        device.add_log("INFO", f"Recording started: {fn}")
        return jsonify({"ok": True, "filename": fn})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/record/stop", methods=["POST"])
def record_stop():
    fn = storage.stop()
    if fn:
        device.add_log("INFO", f"Recording stopped: {fn}")
    return jsonify({"ok": True, "filename": fn})


# ---------- 列出 / 删除 / 回放 CSV ----------------------------------------
@app.route("/api/records")
def list_records():
    return jsonify(storage.list_records())


@app.route("/api/records/delete", methods=["POST"])
def delete_record():
    fn = (request.json or {}).get("filename")
    if not fn:
        return jsonify({"ok": False, "error": "filename required"}), 400
    storage.delete(fn)
    return jsonify({"ok": True})


@app.route("/api/playback/<path:filename>")
def playback(filename: str):
    """读取 CSV 用于回放。一次性返回所有行（演示数据量不大）。"""
    try:
        rows = list(storage.read_for_playback(filename))
        return jsonify({"ok": True, "rows": rows, "count": len(rows)})
    except FileNotFoundError:
        return jsonify({"ok": False, "error": "not found"}), 404


@app.route("/data/<path:filename>")
def download_data(filename: str):
    """下载 CSV / 导出 PNG 时下载等。"""
    return send_from_directory(storage.data_dir, filename, as_attachment=True)


# ---------- 通道映射互换 ---------------------------------------------------
@app.route("/api/matrix/map", methods=["GET"])
def get_map():
    return jsonify(
        {
            "mapping": [
                {"ch": i, "row": r, "col": c}
                for i, (r, c) in enumerate(business.channel_map.mapping)
            ]
        }
    )


@app.route("/api/matrix/map", methods=["POST"])
def set_map():
    """接收 [{ch, row, col}, ...] 重设映射。"""
    data = request.json or []
    mapping = [None] * 16
    for item in data:
        mapping[item["ch"]] = (item["row"], item["col"])
    if any(m is None for m in mapping):
        return jsonify({"ok": False, "error": "incomplete mapping"}), 400
    business.channel_map.set_mapping(mapping)
    return jsonify({"ok": True})


# ---------- 矩阵显示模式切换 ----------------------------------------------
@app.route("/api/matrix/mode", methods=["POST"])
def set_matrix_mode():
    global MATRIX_MODE
    mode = (request.json or {}).get("mode")
    if mode not in ("resistance", "pressure"):
        return jsonify({"ok": False, "error": "invalid mode"}), 400
    MATRIX_MODE = mode
    return jsonify({"ok": True, "mode": MATRIX_MODE})


@app.route("/api/matrix/mode")
def get_matrix_mode():
    return jsonify({"mode": MATRIX_MODE})


# ---------- 设备状态页接口 ------------------------------------------------
@app.route("/api/device/info")
def device_info():
    info = device.info
    return jsonify(
        {
            "mcu": info.mcu,
            "firmware": info.firmware,
            "hw_revision": info.hw_revision,
            "link": info.link,
            "sample_rate": info.sample_rate,
            "buffer": info.buffer,
            "voltage": info.voltage,
            "temperature": info.temperature,
            "connected": info.connected,
        }
    )


@app.route("/api/device/logs")
def device_logs():
    return jsonify(device.get_logs())


@app.route("/api/device/logs/clear", methods=["POST"])
def clear_logs():
    device.logs.clear()
    return jsonify({"ok": True})


@app.route("/api/device/config", methods=["POST"])
def device_config():
    """下发配置（演示用：仅更新 info 字段 + 记日志）。"""
    data = request.json or {}
    if "link" in data:
        device.info.link = data["link"]
    if "sample_rate" in data:
        device.info.sample_rate = int(data["sample_rate"])
        business.sample_rate = device.info.sample_rate
    device.add_log("INFO", f"Config updated: {data}")
    return jsonify({"ok": True, "info": device.info.__dict__})


@app.route("/api/device/upgrade", methods=["POST"])
def firmware_upgrade():
    """演示用：模拟固件升级流程。"""
    version = (request.json or {}).get("version", "1.0.1")
    steps = [
        ("INFO", f"Start upgrading to {version}"),
        ("INFO", "Erasing flash..."),
        ("INFO", "Writing firmware..."),
        ("INFO", f"Upgrade done: {version}"),
    ]
    for lvl, msg in steps:
        device.add_log(lvl, msg)
    device.info.firmware = version
    return jsonify({"ok": True, "firmware": device.info.firmware})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
