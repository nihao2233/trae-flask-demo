# 多模态采集板上位机软件（mac-pcq）

基于 [多模态采集板上位机软件总体设计 v1.1](#) + [UI 设计 v1.1](#) 重写的 PySide6 上位机。

## 当前进度

- [x] 设计文档阅读
- [x] 项目骨架与依赖
- [ ] core / protocol / transport / domain / ui 各子包
- [ ] 9 个 UI 页面（P1 完整 + 其余 8 个 stub）
- [ ] 单元测试 + 端到端验证

详见 [REWRITE_PLAN.md](REWRITE_PLAN.md)。

## 快速开始（本轮 P0 完成后）

```powershell
# 安装依赖
python -m pip install -e .[dev]

# 启动（Mock 适配器，无需硬件）
python -m mac_pcq.main
```

## 工程结构

```
src/mac_pcq/
├── core/         # logger / config / constants / metrics / error_handler
├── transport/    # adapter / usb_cdc / ble / manager / sim
├── protocol/     # spec / codec / dispatcher / commands / parsers / errors
├── domain/       # models / data_bus / session / signal_proc / calibration / export / replay
├── ui/           # theme / widgets / pages / main_window / dialogs / resources
└── platform/     # windows / paths
tests/            # pytest 单元测试
scripts/          # 构建 / 打包脚本
docs/             # 架构 / 协议映射 / release_notes
legacy/           # 旧 Flask 演示工程（不同步）
```

## 协议

- magic = 0xAA55
- HEADER_SIZE = 18 字节（magic u16 + ver u8 + type u8 + seq u32 + ts_us u64 + len u16）
- CRC = CRC16-CCITT（多项式 0x1021，初值 0xFFFF）
- payload 由 type 决定（参见总体设计 §8 / 附录 A）

## 文档

- 重构计划：[REWRITE_PLAN.md](REWRITE_PLAN.md)
- Git 协作：[GIT_WORKFLOW.md](GIT_WORKFLOW.md)
