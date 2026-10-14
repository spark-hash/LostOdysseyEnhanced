import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.2.0'
NAME=f'LostOdysseyEnhanced-{VERSION}-windows-x64-complete'
DEST=ROOT/'releases'/NAME
RUNTIME=ROOT/'runtime/v0.9.52/LostOdysseyRecomp-windows-x64-v0.9.52'
DEST.mkdir(parents=True,exist_ok=False)

def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)

def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(8*1024*1024):
            digest.update(block)
    return digest.hexdigest()

needed=['LostOdysseyEnhanced.exe','dxcompiler.dll','dxil.dll','msvcp140.dll',
        'vcruntime140.dll','vcruntime140_1.dll','NvLowLatencyVk.dll',
        'nvngx_dlss.dll','nvngx_dlssg.dll','nvngx_dlssnr.dll',
        'sl.common.dll','sl.dlss_g.dll','sl.interposer.dll','sl.pcl.dll','sl.reflex.dll',
        'enhancements-build.json']
for filename in needed:
    copy(RUNTIME/filename,DEST/filename)
copy(ROOT/'downloads/panel-dist/LostOdysseySettings.exe',DEST/'LostOdysseySettings.exe')
shutil.copytree(RUNTIME/'licenses',DEST/'licenses')
copy(ROOT/'upstream/LICENSE',DEST/'LICENSE.txt')
copy(ROOT/'enhancements/panel.py',DEST/'source/panel.py')
copy(ROOT/'enhancements/test_panel.py',DEST/'source/test_panel.py')
copy(ROOT/'downloads/GpuCapabilities.exe',DEST/'GpuCapabilities.exe')
copy(ROOT/'enhancements/gpu_capabilities.cpp',DEST/'source/gpu_capabilities.cpp')
copy(ROOT/'.tooling/build_gpu_probe.cmd',DEST/'source/build_gpu_probe-reference.cmd')
copy(ROOT/'patches/display-enhancements.patch',DEST/'source/display-enhancements.patch')
copy(ROOT/'.tooling/build_enhanced.cmd',DEST/'source/build_enhanced-reference.cmd')
print('Copying all four discs and three DLC packages...',flush=True)
shutil.copytree(RUNTIME/'game',DEST/'game')
(DEST/'game-path.txt').write_text('game/disc1\n',encoding='utf-8')

# Neutral defaults, independent of the user's monitor, keyboard, saves and paths.
settings={'ui_language':4,'game_language':9,'width':1920,'height':1080,'window_mode':0,
          'aspect_ratio':0,'graphics_backend':0,'frame_rate':60,'internal_resolution':0,
          'antialiasing':2,'upscaler':0,'dlss_quality':0,'dlss_neural_rendering':0,
          'dlss_nr_intensity':100,'frame_generation_provider':0,'frame_generation_mode':0,
          'frame_generation_multiplier':2,'frame_generation_target_fps':0,
          'vsync':1,'automatic_updates':0,'debug_log':0}
(DEST/'settings.ini').write_text(''.join(f'{k}={v}\n' for k,v in settings.items()),encoding='utf-8')
for label,arguments in [('启动游戏',''),('导入四盘和DLC','--install')]:
    (DEST/f'{label}.cmd').write_text('@echo off\ncd /d "%~dp0"\nset "LO_NO_UPDATE=1"\nstart "" "%~dp0LostOdysseyEnhanced.exe" '+arguments+'\n',encoding='ascii')
(DEST/'打开增强设置.cmd').write_text('@echo off\ncd /d "%~dp0"\nstart "" "%~dp0LostOdysseySettings.exe"\n',encoding='ascii')

readme='''失落的奥德赛 PC 增强版 0.2.0 · Windows x64 · 实验发行版

基于 LostOdysseyRecomp v0.9.52，保留上游 GPL-3.0 许可和第三方声明。

首次使用（完整整合版）
1. 把整个压缩包解压到可写文件夹，保留所有文件；无需安装 Python。
2. 已包含四盘资源与三个 DLC，无需再次导入。
3. 打开 LostOdysseySettings.exe（增强设置），选择分辨率和画质，保存并启动。
4. 后续可直接打开“启动游戏.cmd”。四盘资源放在 game/disc1–disc4，自动换盘。

增强选项
• 自定义输出分辨率、原生像素、固定 16:10 / 21:9 / 32:9 与自动比例。
• DLSS SR / DLAA，DLSS 5 神经渲染叠加 0–4 次，单次强度 0–200%。
• 帧率 30 / 60 / 90 / 120 / 240；这是原生游戏帧上限，不保证实际帧率。
• 渲染显卡选择与 SDK 能力检测；检测期间暂不能保存，检测失败时关闭相关高级选项。
• DLSS 帧生成：关闭 / 固定倍率；D3D12 支持时另开放动态倍率与目标显示帧率。
• 倍率按当前显卡、驱动与附带运行库检测，最高 6×；Vulkan 固定倍率上限使用同一显卡的 D3D12 SDK 查询值。
• 不支持 DLSS 的显卡仅显示关闭 / SMAA，附带神经渲染仅对 RTX 50 系 / D3D12 开放。
• 游戏内也提供显示与帧率选项。增强程序内部保留五次处理能力，面板按最新选择限制为四次。

要求与验证范围
Windows x64，支持 AVX 的 CPU，D3D12 或 Vulkan GPU。
附带的 DLSS 5 运行库为 310.8.0 RTX 50 路径，仅在 RTX 5090 / D3D12 / 3440×1440 验证过。
DLSS 5 默认关闭，开启需先选择 DLSS 或 DLAA 与 D3D12。
默认 1920×1080 窗口、60 FPS、SMAA；240 FPS 的游戏速度 / 战斗时序需进一步实玩验证。
FSR / XeSS 提供器未纳入此增强程序。DLSS FG 代码已构建，发行包未做全场景 FG 验收。
RTX 5090 的 NGX / Streamline 能力检测及面板配置映射已验证；能力检测不等于全场景插帧画质验收。
帧生成不提升游戏逻辑和输入响应的基础帧率；游戏仍会按实际设备重新验证功能、倍率和输入资源。
场景布局、视频黑边、跨盘剧情和全通关仍需测试。

包内包含从本机 GOD 提取的四盘资源及三个 DLC，不包含个人存档、日志、个人配置或本机缓存。无需填写开发者目录。
存档、设置和后续缓存均保存在解压目录中。更新前保留 game、save、profile 与 settings.ini。
官方自动更新已关闭，以免覆盖此本地增强程序。

源码
同目录发布 LostOdysseyEnhanced-0.2.0-source.zip，含本次修改后的上游源码及已检出的依赖源码。
source/ 内另附面板源码与补丁。完整游戏构建仍需自行提供原版数据并生成 PPC 源码，详见上游 docs/BUILDING.md。
第三方运行库许可证位于 licenses/；社区提供的 DLSS 5 二进制单列在第三方来源记录中，不属于本项目开源代码。

校验
manifest.json 列出发行包文件 SHA-256；ZIP 的 SHA-256 在外部 .sha256 文件。
'''
(DEST/'使用说明.txt').write_text(readme,encoding='utf-8-sig')
provenance={'dlss_nr':{'version':'310.8.0','source':'https://github.com/RankFTW/rhi-repo/releases/tag/dlssnr-310.8.0',
             'archive_sha256':'388c0a7912e15ec911b9c9e11a692142b11fe387ddf2b637d8c358138fffb3ac',
             'classification':'NVIDIA proprietary binary, community supplied; not project source'},
            'upstream':'https://github.com/freefrank/LostOdysseyRecomp',
            'upstream_commit':'c258491acb1ea6a38f6220a4c50342d91503e782'}
(DEST/'THIRD_PARTY_SOURCES.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
manifest={'version':VERSION,'upstream_version':'0.9.52','platform':'windows-x64','files':{}}
for path in sorted(DEST.rglob('*')):
    if path.is_file():
        manifest['files'][path.relative_to(DEST).as_posix()]={'size':path.stat().st_size,'sha256':sha256(path)}
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

def archive(folder,destination):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                is_game=path.is_relative_to(folder/'game')
                output.write(path,path.relative_to(folder.parent).as_posix(),compress_type=zipfile.ZIP_STORED if is_game else zipfile.ZIP_DEFLATED)
    digest=sha256(destination)
    destination.with_suffix(destination.suffix+'.sha256').write_text(f'{digest}  {destination.name}\n',encoding='ascii')
    print(f'{destination.name}: {destination.stat().st_size} bytes; SHA-256 {digest}',flush=True)

archive(DEST,DEST.parent/(DEST.name+'.zip'))
source_zip=ROOT/'releases'/f'LostOdysseyEnhanced-{VERSION}-source.zip'
files=subprocess.check_output(['git','-C',str(ROOT/'upstream'),'ls-files','--recurse-submodules','-z']).decode('utf-8').split('\0')
with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
    for filename in files:
        path=ROOT/'upstream'/filename
        if filename and path.is_file():
            output.write(path,'LostOdysseyEnhanced-source/upstream/'+filename)
    for filename in ['panel.py','test_panel.py','gpu_capabilities.cpp','README.md','VALIDATION.md']:
        output.write(ROOT/'enhancements'/filename,'LostOdysseyEnhanced-source/enhancements/'+filename)
    output.write(ROOT/'.tooling/build_gpu_probe.cmd','LostOdysseyEnhanced-source/.tooling/build_gpu_probe.cmd')
    audio_files=subprocess.check_output(['git','-C',str(ROOT/'.tooling/ffmpeg'),'ls-files','-z']).decode('utf-8').split('\0')
    for filename in audio_files:
        path=ROOT/'.tooling/ffmpeg'/filename
        if filename and path.is_file():
            output.write(path,'LostOdysseyEnhanced-source/dependencies/ffmpeg/'+filename)
source_zip.with_suffix('.zip.sha256').write_text(sha256(source_zip)+'  '+source_zip.name+'\n',encoding='ascii')
print(f'Source snapshot: {source_zip.stat().st_size} bytes',flush=True)
