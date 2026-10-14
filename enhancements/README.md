# 失落的奥德赛 PC 增强

双击项目根目录 `PC增强.cmd` 打开中文增强面板。使用现有 v0.9.52 程序，保存前退出游戏。

## 当前可用

- 输出分辨率预设及自定义尺寸：640–7680 × 480–4320。
- 跟随分辨率模式支持 16:10、21:9、32:9；使用移植版本已有的场景扩展与 UI 布局，不是全画面拉伸。
- 匹配主屏幕像素尺寸、窗口 / 无边框全屏、内部渲染分辨率与原生像素。
- SMAA、DLSS Quality / Balanced / Performance / DLAA；帧率上限 30 / 60 / 90 / 120 / 240 FPS。
- 0.2.0：选择渲染显卡，后台使用 NGX / Streamline 检测显卡与驱动能力，再显示支持的 DLSS 模式。
- DLSS 帧生成固定倍率 2×–6×（按 SDK 检测上限）；D3D12 另支持 SDK 允许的动态倍率和目标显示帧率，Vulkan 仅固定倍率。
- 保存前检查游戏进程；保留键位、存档选项和未知配置；自动备份并原子写入。

全屏使用桌面尺寸，输出分辨率选项主要影响窗口模式。原有菜单、电影等可能保留黑边；超宽屏各个场景仍需验收。

240 FPS 档已编译进增强版，菜单、配置校验与原生帧率调度使用同一档位列表。面板检查构建凭据后才允许保存 240，避免旧程序把该值重置为 30。此次通过帧率调度和 150 项帧计划检查，未证明全游戏在 240 FPS 下时序正确或性能达标。垂直同步仍按原设置工作，实际帧率受显示器刷新率和 GPU 开销影响。

## DLSS 5 社区接入

面板复用移植版本现有的实验 NGX 神经渲染路径，默认读取程序目录中的 `nvngx_dlssnr.dll`，后台静态检查 x64 PE 和 D3D12 导出接口。面板处理次数为 0（关闭）、1、2、3、4；单次模型强度另设 0–200%。叠加次数不是帧率倍数。无需 ReShade 或替换 `dxgi.dll`。0.1.1 界面只保留设置控件，移除了四盘启动字样、技术说明、诊断状态和运行库选择按钮。

增强程序内部保留第 5 次处理能力，当前面板按用户选择限制为 0–4 次。面板核对 `enhancements-build.json` 中的 EXE SHA-256 后选择增强程序；原版程序保留，增强版自动更新检查禁用以防被官方程序覆盖。

接口检查不验证数字签名，也不证明模型成功执行；须查看游戏的神经渲染日志、画面和帧时间。实验选项要求 D3D12 + DLSS / DLAA。默认关闭。未添加所谓自动下载 SDK，也未将超分辨率或帧生成冒充 DLSS 5。

参考来源：

- https://github.com/faisalkindi/DLSS5oneclick
- https://github.com/Dagherbou/OptiScaler_DLSSNR
- https://github.com/RankFTW/rhi-repo/releases
- https://github.com/freefrank/LostOdysseyRecomp

## 源码扩展

`patches/display-enhancements.patch` 为当前 upstream 工作副本的显示增强补丁，新增固定 32:9 / 16:10 比例、对应分辨率预设与 Windows 原生像素选项。保持已有保存 ID 0–3，不影响旧配置。新增宽高适配测试用例。

这些新增游戏内选项已编译进独立的 `LostOdysseyEnhanced.exe`，增强面板会根据构建凭据启动它。原 `LostOdysseyRecomp.exe` 保留。当前本机构建启用 DLSS SR、D3D12 / Vulkan DLSS FG；FSR 和 XeSS 提供器未纳入本次构建，需使用原程序或后续补齐 SDK 构建。

## 验证

显卡检测程序 `GpuCapabilities.exe` 源码位于 `enhancements/gpu_capabilities.cpp`，用 `.tooling/build_gpu_probe.cmd` 构建，需要 Visual Studio / Windows SDK、NVIDIA DLSS SDK、Streamline SDK 和已检出的 Vulkan-Headers / json.hpp。检测不创建游戏交换链，也不执行插帧或神经渲染；D3D12 使用 NGX 能力参数和 Streamline 状态查询，Vulkan 使用同一 LUID 对应的物理设备查询 API 支持。Vulkan 倍率上限取同一显卡的 D3D12 SDK 查询值，游戏初始化时还会再次验证。双显卡通过实际设备名称写入 `gpu_device`。未知或失败的检测不会开放高级选项。

面板和外部原生程序分别使用各自 DLL 搜索环境；检测在子进程和后台线程内执行，有超时，保存前必须等待检测完成。正式包不依赖 Python。

运行 `enhancements/test_panel.py` 检查配置保留、重复键处理、备份、尺寸边界与无效 DLL 拒绝。完整 C++ 构建需 Visual Studio C++ 工具链、Windows SDK、Clang、CMake、Ninja、子模块及本机生成的 PPC 源码。

2026-10-14 本机验证：增强版完整编译通过；帧计划 150 项检查、面板 7 项测试、屏幕比例与五次处理上限 C++ 检查通过。RTX 5090 / D3D12 / 3440×1440 的运行日志 `runtime-1791971119440577.log` 记录 `DLSS NR: 5 feature(s) created` 和 `DLSS NR: first evaluate recorded ... 5 pass(es)`。已观察开场场景渲染；这不代表全流程、各个处理次数或长期稳定性均已验收。
