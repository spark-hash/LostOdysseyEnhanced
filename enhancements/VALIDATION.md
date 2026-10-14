# 五次神经渲染验收

日期：2026-10-14（Asia/Singapore）

- 源码基线：c258491acb1ea6a38f6220a4c50342d91503e782，叠加本地增强补丁。
- 配置上限：`DlssNeuralRenderingMaxPasses = 5`。
- 渲染器上限：`kMaxNeuralRenderingPasses = 5`；游戏与预览功能句柄数组随常量扩展。
- 游戏内处理次数：关闭、1×、2×、3×、4×、5×。
- 增强面板保留单次强度 0–200%，与处理次数分别保存。
- 独立 EXE：`LostOdysseyEnhanced.exe`。面板核对 EXE SHA-256 后才允许 5 次，保留官方 EXE。
- 构建通过；帧计划 150 项检查、面板 7 项测试、独立 C++ 显示与上限检查通过。

运行：RTX 5090，D3D12，3440×1440。

日志 `runtime-1791971119440577.log`：

```text
[14.701] DLSS NR: 5 feature(s) created for 3440x1440
[14.727] DLSS NR: first evaluate recorded for 3440x1440, 5 pass(es)
```

已观察开场场景渲染。未作所有场景 / 全通关 / 长时间稳定性测试，也未作 1–5 次公平性能对照。

## 240 FPS 扩展

同日新增原生 240 FPS 档：`kNativeRates` 为 30/60/90/120/240，配置、游戏内菜单与帧率调度同步使用此列表。增强版重新编译并部署；前一增强版另存 `LostOdysseyEnhanced-before-240.exe`。面板 8 项测试、帧计划 150 项检查、含 240 FPS 的原生帧率调度 / 档位切换检查通过。此次未运行全游戏 240 FPS 场景验收。

## 0.2.0 显卡适配和帧生成面板

- 新增独立原生能力查询程序，DXGI 枚举设备并使用 LUID 映射 Vulkan 物理设备；按实际设备名称保存显卡选择。
- RTX 5090：D3D12 NGX SR 可用；Streamline 查询 `numFramesToGenerateMax=5`，动态 MFG 可用；Vulkan SR / FG 接口支持查询通过。
- AMD Radeon(TM) Graphics：NGX SR 不可用，D3D12 FG 不可用；Vulkan 的初步 FG 查询虽然返回成功，但缺少同一设备的 D3D12 能力资格，面板不会开放 DLSS FG。
- 不用显卡型号推算帧生成倍率。D3D12 根据实际 SDK 状态开放 2×–6× / 动态；Vulkan 仅固定倍率，倍率上限使用同一设备的 D3D12 查询值，游戏初始化再次检查。
- 面板 11 项设置与能力策略测试通过，覆盖 SDK 拒绝、未知设备、2× 限制、6× 支持、Vulkan 禁止动态倍率及错误设置拒绝。
- PyInstaller 便携程序在移动后的目录自检通过；实际 GPU 检测结果、后端可用选项、固定倍率的配置映射正确。自检不写入个人设置。
- 临时日志占用不会丢弃已成功取得的检测结果；外部检测 / 游戏子进程使用独立 DLL 搜索环境。
- 神经渲染面板仍限制 0–4 次，附带运行库只对 RTX 50 / D3D12 / DLSS 或 DLAA 开放。

以上验证不包含全场景插帧画质、实际显示帧率 / 延迟、全通关或长期稳定性验收。帧生成默认关闭。
