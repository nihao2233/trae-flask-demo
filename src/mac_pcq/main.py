"""主入口：启动 QApplication + qasync 事件循环 + AppController + MainWindow。"""

from __future__ import annotations

import asyncio
import sys

from PySide6.QtWidgets import QApplication

from .app import AppController
from .ui.main_window import MainWindow

# 尝试引入 qasync；缺失则退化为纯 asyncio 模式（GUI 仍能起但事件循环无集成）
try:
    import qasync  # type: ignore
    _HAS_QASYNC = True
except ImportError:
    _HAS_QASYNC = False


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        QApplication.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    if _HAS_QASYNC:
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    controller = AppController()
    win = MainWindow(app_controller=controller)
    controller.attach_window(win)

    async def _go():
        await controller.start()

    try:
        loop.run_until_complete(_go())
    except Exception as e:  # noqa: BLE001
        # 真实应用应走 UserFacingError；这里仅打印
        import traceback
        traceback.print_exc()
        return 1

    win.show()

    if _HAS_QASYNC:
        with loop:
            return loop.run_forever() or 0
    else:
        # 退化模式：用 QTimer 驱动 asyncio
        from PySide6.QtCore import QTimer
        t = QTimer()
        t.setInterval(50)
        t.timeout.connect(lambda: loop.stop() if loop.is_running() else None)
        # 简化：直接 exec 会卡，提示用户装 qasync
        print("WARN: qasync not installed, GUI and asyncio are not integrated.", file=sys.stderr)
        return app.exec()


if __name__ == "__main__":
    sys.exit(main())
