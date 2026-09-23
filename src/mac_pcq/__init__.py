"""多模态采集板上位机软件。

包结构遵循《多模态采集板上位机软件总体设计》v1.1：
- core/      跨切关注点（logger / config / metrics / error_handler / i18n / constants）
- transport/ 通讯适配层（DeviceAdapter ABC + USB/BLE/Mock 实现）
- protocol/  协议层（magic=0xAA55 / CRC16-CCITT / 二进制帧）
- domain/    业务层（数据模型 / DataBus / SessionService / 信号处理）
- ui/        表现层（PySide6 / 9 个二级页面）
- platform/  平台相关封装
"""

__version__ = "0.1.0"
