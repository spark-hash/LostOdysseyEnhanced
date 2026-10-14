# Lost Odyssey Enhanced

《失落的奥德赛》PC 增强工程，基于 [LostOdysseyRecomp](https://github.com/freefrank/LostOdysseyRecomp) v0.9.52。

当前版本为 **0.2.0**。本仓库保存增强面板、显卡能力检测源码、上游补丁、构建和发行脚本，不包含游戏资源、生成的 PowerPC 代码、个人存档或第三方运行库二进制。

## 当前进度

- 输出分辨率与渲染分辨率设置，16:10 / 21:9 / 32:9 比例适配。
- 原生帧率档位 30 / 60 / 90 / 120 / 240 FPS。
- DLSS 超分辨率和 DLAA；按所选显卡、驱动与 SDK 检测结果限制可用选项。
- DLSS 帧生成固定倍率最高 6×；D3D12 在支持时提供动态倍率，Vulkan 仅固定倍率。
- 实验神经渲染：面板提供 0–4 次处理、单次强度 0–200%。附带运行库适配路径要求 RTX 50 系、D3D12 和 DLSS / DLAA。
- 中文启动面板、设置备份和原子保存、四盘与 DLC 整合发行脚本。

帧生成默认关闭。11 项面板测试、RTX 5090 / AMD 集成显卡能力检测和便携版自检已通过；未完成全场景插帧、240 FPS 游戏时序和全流程稳定性验收。详见 [验证记录](enhancements/VALIDATION.md)。

## 文件布局

| 路径 | 内容 |
| --- | --- |
| `enhancements/panel.py` | Tkinter 启动面板及设置管理 |
| `enhancements/gpu_capabilities.cpp` | 独立 NGX / Streamline 显卡能力查询程序 |
| `patches/display-enhancements.patch` | 相对固定上游提交的完整游戏源码改动 |
| `.tooling/` | 构建、验证、资源导入与发行脚本 |
| `UPSTREAM.json` | 上游来源和固定提交 |

## 准备源码

```powershell
git clone https://github.com/freefrank/LostOdysseyRecomp.git upstream
git -C upstream checkout c258491acb1ea6a38f6220a4c50342d91503e782
git -C upstream submodule update --init --recursive
git -C upstream apply ../patches/display-enhancements.patch
```

接着按照上游 `docs/BUILDING.md` 准备工具链、依赖补丁和你自己的匹配版本游戏资源，并生成本地 PowerPC 源码。不要将生成代码或游戏数据提交到 Git。

原生增强版构建参考 `.tooling/build_enhanced.cmd`；显卡检测程序使用 `.tooling/build_gpu_probe.cmd`。这些脚本按本工程目录布局寻找 Visual Studio Build Tools、Windows SDK、NVIDIA DLSS / Streamline SDK 和 FFmpeg，依赖需自行准备到 `.tooling/` 对应目录。Python 路径可用 `LO_PYTHON` 指定。

开发面板使用 Python 3.12 或更新版本，并需要 Tkinter。已安装的游戏程序放在 `runtime/v0.9.52/LostOdysseyRecomp-windows-x64-v0.9.52/`，启动面板前需部署 `GpuCapabilities.exe`。运行 `python enhancements/panel.py`，或使用 `PC增强.cmd`。

```powershell
python -m unittest discover -s enhancements -p test_panel.py
```

## 发行

先用 PyInstaller 生成 `downloads/panel-dist/LostOdysseySettings.exe`，将显卡检测程序放到 `downloads/GpuCapabilities.exe`，准备好运行目录和构建凭据后执行：

```powershell
python .tooling/package_release.py
python .tooling/verify_release.py
```

完整整合包仅在本地 `releases/` 生成，不纳入本仓库。正式面板不依赖另装 Python。第三方 SDK 与运行库遵循各自许可证。

## 许可证

本增强工程沿用上游 GPL-3.0 许可证，见 [LICENSE](LICENSE)。保留上游和第三方版权声明；本仓库不提供游戏资产。
