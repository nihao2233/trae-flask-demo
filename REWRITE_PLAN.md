# 重构实施计划

本计划基于以下两份飞书设计文档：

- [多模态采集板上位机软件总体设计 v1.1](https://my.feishu.cn/wiki/KLpuwAHJBiJF0LkviICck1Ox6qc)
- [多模态采集板上位机 UI 设计](https://my.feishu.cn/wiki/I36gwEXD1ikXuukog9Gc7lCN6ad)

## 范围确认

- **范围**：完整骨架 + P0 模块
- **协议**：严格按 v1 新协议（magic=0xAA55、CRC16-CCITT、type=0x01~0xFF）
- **硬件**：全部 Mock 模拟器（无真实 USB/BLE）

## 已读取的设计章节（总体设计）

- §4 总体架构 / 跨切关注点 / 设计原则
- §5 技术栈选型
- §6 目录结构 / 模块职责矩阵
- §7 关键数据流 / DataBus
- §8 协议层契约
- §9 通讯适配层契约
- §10 业务层（数据模型 + SessionService 接口）
- §11 UI 契约（页面清单 + Signal/Slot 矩阵）
- §12 状态机

## 已读取的设计章节（UI 设计）

- §1 文档目的、§2 需求列表（UI-01~20 + UNFR-01~06）
- §3 Design Token（颜色 / 字号 / 间距 / 圆角 / 阴影 / 动画 / 字体）
- §4 信息架构（全局布局 + 9 页面路由）
- §5 通用组件库（12 个组件 + 状态指示灯 / 按钮 / 输入 / 反馈规范）
- §6 9 个页面详细设计
- §7 波形渲染规范
- §8 热力图规范
- §9 数据流图
- §10 交互模式（反馈 / 错误提示 / 快捷键 / 多窗口）
- §11 可访问性（A11y）
- §12 国际化（i18n）
- §13 响应式与多分辨率
- §14 设计交付物清单
- §15 视觉验收准则（10 条）
- §16 版本与变更
- §17 附录（UI 模块→业务层接口映射 + 图标 + 错误文案模板）

## UI 设计关键约束（实现必须遵守）

### Design Token（`ui/theme.py`）
- 浅色：`--brand-primary=#6355FF` / `--accent-success=#00B14F` / `--accent-warning=#FF7A45` / `--accent-danger=#E5453D` / `--accent-info=#1B6FF9`
- 通道色（不随主题变）：ch-1=紫 / ch-2=绿 / ch-3=橙 / ch-4=蓝
- 字号：`--font-display=28px/700`、`--font-h1=22px/700`、`--font-h2=18px/600`、`--font-h3=16px/600`、`--font-body=14px/400`、`--font-small=12px/400`
- 间距：`--space-1=4px` ... `--space-6=32px`
- 圆角：`--radius-sm=4px` / `--radius-md=8px` / `--radius-lg=12px`
- 数字字体：`Roboto Mono`；中文：`PingFang SC / Microsoft YaHei`

### 组件库（12 个）
`LinkIndicator` `StatusBadge` `ECGStrip` `PiezoStrip` `MatrixGrid` `VitalCard` `WaveformCanvas` `ColorScaleBar` `LogPanel` `RecordControls` `UpgradeProgress` `ParamForm`

### 9 个页面（P1~P9）
- P1 主监测 / P2 压阻矩阵 / P3 压电波形 / P4 生命体征 / P5 记录回放 / P6 设备状态 / P7 参数配置 / P8 固件升级 / P9 日志
- 每个页面均带线框图（参考 PNG，本次实现按规范还原）

### 主监测页（P1）核心布局
- 左上：4 路 ECG（Y±1mV、X 5s 滚动、0.5mV×0.2s 网格、ch 标签可点击显隐）
- 右上：矩阵缩略 60×60px 单元 + 色阶图例
- 左下：2 路压电（Y±10mV）
- 右下：HR/RR 大字卡片 + 电量 + 运行时长

### 波形规范（§7）
- pyqtgraph `PlotWidget` + `setData()` 增量
- 默认 5s 滚动窗 / 60fps / 环形缓冲 10s
- 滚轮=Y 缩放 / Shift+滚轮=X / 双击标签=Y 重置 / 点击标签=显隐

### 热力图规范（§8）
- 单元 60×60（详情 80×80）/ 间距 2px / 5 档深度 + 6 种基色
- 数值右下角小字 / 悬停边框高亮 + tooltip
- 色阶映射：电阻 10–500 kΩ / 压力 100–5000 N，下限固定 0

### 色阶基色（6 种）
- 蓝→红 / 蓝→绿 / 紫→黄 / 单色灰 / 彩虹 / 热成像

### 压力方程（§6.2.4）
- R<10kΩ：P=R×a₁（默认 0.01）
- R≥10kΩ：P=R×a₂+b（默认 0.005 / 25）
- 支持两点标定 → 解 a, b

### 错误文案规范（§10.2）
- 必须含"发生了什么 / 为什么 / 怎么办"
- 禁止直接抛 `CRCError`，必须翻译为用户语言

### 快捷键（§10.3）
`Ctrl+O` / `Ctrl+S` / `Ctrl+E` / `F1` / `F5` / `Esc` / `1~9`

### 验收准则（§15，10 条）
- Token 应用 / 主题切换 / 60fps / 色阶 / 通道互换 / 错误提示 / 快捷键 / WCAG AA / 多分辨率 / i18n

## 交付物（本轮 P0）

### 1. 项目骨架
- `pyproject.toml` + 依赖（PySide6、qasync、pyqtgraph、numpy、scipy、pyserial-asyncio、bleak、h5py）
- `src/mac_pcq/` 6 大子包：`core / transport / protocol / domain / ui / platform`
- `tests/` pytest 单元测试

### 2. core/ 跨切关注点
- `logger.py`：分级日志 + UI 事件总线
- `config.py`：用户偏好（端口、最近文件）
- `constants.py`：版本号 / 默认值
- `metrics.py`：FPS / 丢帧率 / 延迟直方图
- `error_handler.py`：全局 `UserFacingError`

### 3. protocol/ 新协议层
- `spec.py`：magic、HEADER_SIZE、CRC16、type 命名空间、命令码、配置码
- `codec.py`：`Frame` dataclass + `FrameCodec.encode/decode` + CRC16-CCITT + magic 查找
- `parsers.py`：`ECGFrame / PVDFFrame / ResistiveFrame / VitalSigns / SystemStatus / DeviceInfo`
- `dispatcher.py`：按 type 分发到 DataBus
- `commands.py`：`CommandBuilder`（start_acq / stop_acq / set_ecg_fs / 等）
- `errors.py`：`ProtocolError` + MCU 错误码表

### 4. transport/ 通讯适配层
- `adapter.py`：`DeviceAdapter` ABC + `LinkState` enum
- `models.py`：`DeviceInfo` / `LinkState` 等数据类
- `usb_cdc.py`：`UsbCdcAdapter`（pyserial-asyncio + 状态机）
- `ble.py`：`BleAdapter`（bleak，本轮 stub）
- `manager.py`：`ConnectionManager`（重连 / 心跳 / 指数退避）
- `sim.py`：`SimAdapter`（Mock，输出符合新协议的字节流）

### 5. domain/ 业务层
- `models.py`：`ECGSample / PVDFFrame / ResistiveSample / VitalSigns / SystemStatus` dataclass
- `data_bus.py`：`DataBus`（asyncio.Queue 生产 + Qt Signal 消费）
- `session.py`：`SessionService`（IDLE/STARTING/RUNNING/PAUSED/RECORDING/STOPPING/ERROR 状态机）
- `signal_proc.py`：`SignalProcessor`（ECG IIR 滤波 + R 峰检测 + HR 计算）
- `calibration.py`：`Calibration`（分段线性 + 两点标定）
- `export.py`：`ExportService`（CSV 导出，本轮实现；PNG/HDF5 留 stub）
- `replay.py`：`ReplayService`（CSV 回放，本轮 stub）

### 6. ui/ 表现层
- `main_window.py`：顶栏 + 左侧导航 + 主区 + 底栏
- `pages/monitor.py`：主监测页（ECG + 矩阵缩略 + 压电 + 生命体征卡片）— **P0 完整**
- 其余 8 页（压阻矩阵 / 压电波形 / 生命体征 / 记录回放 / 设备状态 / 参数配置 / 固件升级 / 日志）— **stub 框架**
- `widgets/` 复用控件（状态指示灯 / 按钮 / 数值卡）
- `theme.py`：颜色 / 字号 token
- `resources/` 占位

### 7. platform/
- `windows.py`：Windows 路径 / 串口枚举
- `paths.py`：用户配置目录

### 8. tests/
- `test_protocol_codec.py`：round-trip + CRC + magic 查找
- `test_protocol_parsers.py`：16 种 type 解析
- `test_calibration.py`：分段线性 + 两点标定
- `test_signal_proc.py`：滤波频率响应 + R 峰
- `test_session_state_machine.py`：合法/非法状态转换
- `test_data_bus.py`：生产者/消费者节流

### 9. 入口
- `main.py`：启动 `QApplication` + qasync 事件循环 + `AppController`
- `app.py`：`AppController` 装配 core/transport/protocol/domain/ui

### 10. 端到端
- 启动脚本 / 调试模式（mock 适配器直接跑通数据流）

## 留给后续轮次的（明确不做）

- 真实 USB CDC 连接（pyserial-asyncio）
- 真实 BLE 连接（bleak）
- Pan-Tompkins 完整 R 波检测（先用简单阈值）
- HDF5 / PNG 导出
- 主题切换 / i18n 翻译文件
- OTA 升级流程
- 9 个页面除主监测外的完整实现
- 安装包打包（PyInstaller + NSIS）

## 验证策略

1. 单元测试 `pytest` 全部通过
2. 启动 main.py 不报错，主窗口显示
3. Mock 适配器连接后，DataBus 有数据，PageMonitor 显示波形（pyqtgraph）
4. 启动后无未捕获异常

## 工作目录

`e:\File\上交\压电采集\PC\`（现有 Flask 演示工程将被替换）

- 旧 `app.py / core/* / static/* / templates/*` 保留为 `legacy/` 暂不删，便于回退
- 新代码全部在 `src/mac_pcq/`

## 提交策略

- 每完成一个子包就一次 commit（feat(protocol)、feat(transport) 等）
- 最后整体跑通后推送 + 发 PR

更新时间：2026-09-22
