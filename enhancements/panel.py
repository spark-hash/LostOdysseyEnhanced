"""Portable settings panel for the installed Lost Odyssey Recomp runtime."""
import ctypes
import json
import hashlib
import os
import shutil
import subprocess
import tempfile
import sys
import queue
import threading
import time
import re
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

FROZEN = getattr(sys,'frozen',False)
ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parents[1]
RUNTIME = ROOT if FROZEN else ROOT / 'runtime/v0.9.52/LostOdysseyRecomp-windows-x64-v0.9.52'
SETTINGS = RUNTIME / 'settings.ini'
PREFERENCES = ROOT / 'panel-preferences.json' if FROZEN else ROOT / 'enhancements/preferences.json'
RESOLUTIONS = ['1280 × 720', '1920 × 1080', '2560 × 1440', '3840 × 2160',
               '1280 × 800', '1920 × 1200', '2560 × 1600', '2560 × 1080',
               '3440 × 1440', '3840 × 1600', '5120 × 2160',
               '3840 × 1080', '5120 × 1440', '7680 × 2160']
ASPECTS = {'跟随分辨率（含 32:9 / 16:10）': 0, '16:9': 1, '21:9': 2, '4:3': 3}
RENDER = {'跟随输出（最高 4K 高度）': 0, '原生像素': 1, '720p': 720,
          '1080p': 1080, '1440p': 1440, '2160p': 2160}
AA = {'关闭': (0, 0), 'SMAA': (0, 2), 'DLSS Quality': (1, 2),
      'DLSS Balanced': (1, 2), 'DLSS Performance': (1, 2), 'DLAA': (1, 2)}
QUALITY = {'DLSS Quality': 0, 'DLSS Balanced': 1, 'DLSS Performance': 2, 'DLAA': 3}
PANEL_MAX_NR_PASSES = 4
FG_MODES = {'关闭': 0, '固定倍率': 1, '动态倍率': 2}
FG_TARGETS = {'跟随屏幕': 0, '120': 120, '144': 144, '165': 165, '240': 240}

def run_gpu_probe(selection, backend='d3d12', runtime=RUNTIME):
    executable=runtime/'GpuCapabilities.exe'
    if not executable.is_file():
        raise OSError('缺少显卡能力检测程序。')
    with tempfile.TemporaryDirectory(prefix='lost-odyssey-gpu-',ignore_cleanup_errors=True) as folder:
        output=Path(folder)/'capabilities.json'
        # PyInstaller adds its Tcl/Python DLL directory to child processes.
        # Native GPU helpers must use the installed runtime and system DLLs.
        if FROZEN and os.name=='nt':
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            result=subprocess.run([str(executable),str(output),str(selection),backend],cwd=runtime,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        finally:
            if FROZEN and os.name=='nt':
                ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
        if result.returncode or not output.is_file():
            raise OSError(f'显卡能力检测失败（退出码 {result.returncode:#x}）。')
        report=json.loads(output.read_text(encoding='utf-8'))
        if report.get('error'):
            raise OSError(report['error'])
        return report

def graphics_options(adapter, reports, backend, nr_compatible):
    """The SDK qualifies FG; Vulkan is fixed-only and shares the queried hardware ceiling."""
    api='vulkan' if backend=='Vulkan' else 'd3d12'
    current=reports.get(api,{})
    d3d=reports.get('d3d12',{})
    maximum=min(6,max(1,int(d3d.get('max_multiplier',1))))
    fg=bool(current.get('fg') and d3d.get('fg') and maximum>=2)
    modes=['关闭']+(['固定倍率'] if fg else [])
    if fg and api=='d3d12' and d3d.get('dynamic'):
        modes.append('动态倍率')
    nr=bool(nr_compatible and api=='d3d12' and current.get('sr') and
        adapter.get('vendor')==0x10de and re.search(r'\bRTX\s*50\d{2}\b',adapter.get('name',''),re.I))
    return {'aa':list(AA) if current.get('sr') else ['关闭','SMAA'],
            'fg_modes':modes,'multipliers':[f'{n}×' for n in range(2,maximum+1)] if fg else ['2×'],
            'nr':nr,'device_name':current.get('device_name',adapter.get('name',''))}

def runtime_pass_limit(runtime=RUNTIME):
    receipt=runtime/'enhancements-build.json'
    if receipt.exists():
        info=json.loads(receipt.read_text(encoding='utf-8'))
        name=info.get('executable','LostOdysseyRecomp.exe')
        if name not in {'LostOdysseyRecomp.exe','LostOdysseyEnhanced.exe'}:
            return 4
        executable=runtime/name
        if info.get('max_nr_passes')==5 and executable.is_file():
            if hashlib.sha256(executable.read_bytes()).hexdigest()==info.get('exe_sha256'):
                return 5
    return 4

def runtime_executable(runtime=RUNTIME):
    if runtime_pass_limit(runtime)==5:
        info=json.loads((runtime/'enhancements-build.json').read_text(encoding='utf-8'))
        return runtime/info.get('executable','LostOdysseyRecomp.exe')
    return runtime/'LostOdysseyRecomp.exe'

def runtime_supports_fps(fps, runtime=RUNTIME):
    if fps in (30,60,90,120):
        return True
    if fps==240 and runtime_pass_limit(runtime)==5:
        info=json.loads((runtime/'enhancements-build.json').read_text(encoding='utf-8-sig'))
        return 240 in info.get('native_rates',[])
    return False

def read_config(path=SETTINGS):
    text = path.read_text(encoding='utf-8-sig') if path.exists() else ''
    return {line.split('=', 1)[0]: line.split('=', 1)[1]
            for line in text.splitlines() if '=' in line}

def merge_config(text, changes):
    """Preserve unrelated settings, comments and line ordering."""
    pending = {k: str(v) for k, v in changes.items()}
    lines = []
    for line in text.splitlines():
        key = line.split('=', 1)[0] if '=' in line else None
        if key in changes:
            # Drop duplicate controlled keys so the runtime cannot read stale values.
            if key in pending:
                lines.append(f'{key}={pending.pop(key)}')
        else:
            lines.append(line)
    lines.extend(f'{key}={value}' for key, value in pending.items())
    return '\n'.join(lines) + '\n'

def save_config(changes, path=SETTINGS):
    if not path.parent.is_dir():
        raise ValueError('未找到游戏目录。')
    original = path.read_text(encoding='utf-8-sig') if path.exists() else ''
    if path.exists():
        backup = path.parent / 'settings-backups'
        backup.mkdir(exist_ok=True)
        shutil.copy2(path, backup / f'settings-{datetime.now():%Y%m%d-%H%M%S-%f}.ini')
    fd, temporary = tempfile.mkstemp(prefix='settings-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as output:
            output.write(merge_config(original, changes))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def game_running():
    if os.name != 'nt':
        return False
    class Entry(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('usage', ctypes.c_ulong),
                    ('pid', ctypes.c_ulong), ('heap', ctypes.c_size_t),
                    ('module', ctypes.c_ulong), ('threads', ctypes.c_ulong),
                    ('parent', ctypes.c_ulong), ('priority', ctypes.c_long),
                    ('flags', ctypes.c_ulong), ('exe', ctypes.c_wchar * 260)]
    dll = ctypes.WinDLL('kernel32', use_last_error=True)
    dll.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    dll.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(Entry)]
    dll.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(Entry)]
    dll.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = dll.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError('无法检查游戏进程，暂不修改设置。')
    entry = Entry()
    entry.size = ctypes.sizeof(entry)
    try:
        found = dll.Process32FirstW(handle, ctypes.byref(entry))
        while found:
            if entry.exe.casefold() in {'lostodysseyrecomp.exe','lostodysseyenhanced.exe'}:
                return True
            found = dll.Process32NextW(handle, ctypes.byref(entry))
        return False
    finally:
        dll.CloseHandle(handle)

def validate_resolution(value):
    try:
        width, height = map(int, value.lower().replace('×', 'x').replace(' ', '').split('x'))
    except ValueError:
        raise ValueError('分辨率格式应为 3440 × 1440。') from None
    if not (640 <= width <= 7680 and 480 <= height <= 4320):
        raise ValueError('宽度须为 640–7680，高度须为 480–4320。')
    return width, height

def nr_path():
    if PREFERENCES.exists():
        saved = json.loads(PREFERENCES.read_text(encoding='utf-8'))
        if saved.get('nr_path'):
            return Path(saved['nr_path'])
    return RUNTIME / 'nvngx_dlssnr.dll'

def inspect_nr(path):
    """Inspect PE structure and exports without executing the DLL."""
    if not path.is_file():
        return False, '缺少 nvngx_dlssnr.dll；DLSS 5 尚未启用。'
    import struct
    data = path.read_bytes()
    try:
        pe = struct.unpack_from('<I', data, 0x3C)[0]
        assert data[:2] == b'MZ' and data[pe:pe+4] == b'PE\0\0'
        machine, sections = struct.unpack_from('<HH', data, pe+4)
        assert machine == 0x8664, '运行库不是 Windows x64。'
        size = struct.unpack_from('<H', data, pe+20)[0]
        optional = pe+24
        assert struct.unpack_from('<H', data, optional)[0] == 0x20B
        export_rva = struct.unpack_from('<I', data, optional+112)[0]
        table = optional + size
        def offset(rva):
            for i in range(sections):
                virtual_size, address, raw_size, raw = struct.unpack_from('<IIII', data, table+i*40+8)
                if address <= rva < address+min(virtual_size, raw_size):
                    return raw+rva-address
            raise ValueError('无法解析运行库导出表。')
        export = offset(export_rva)
        names_count = struct.unpack_from('<I', data, export+24)[0]
        names_offset = offset(struct.unpack_from('<I', data, export+32)[0])
        assert names_count <= 65536
        exports = set()
        for i in range(names_count):
            name = offset(struct.unpack_from('<I', data, names_offset+i*4)[0])
            end = data.find(b'\0', name, name+256)
            assert end >= 0
            exports.add(data[name:end].decode('ascii'))
        required = {'NVSDK_NGX_D3D12_Init_Ext', 'NVSDK_NGX_D3D12_CreateFeature',
                    'NVSDK_NGX_D3D12_EvaluateFeature', 'NVSDK_NGX_D3D12_ReleaseFeature'}
        if not required <= exports:
            return False, '运行库缺少当前移植程序所需的 D3D12 NGX 接口。'
        return True, '接口检查通过；实验接入，实际运行状态仍须游戏日志确认。'
    except (AssertionError, ValueError, struct.error, UnicodeError) as error:
        return False, f'运行库检查未通过：{error or "无效 PE 文件"}'

def nr_execution_status(runtime=RUNTIME):
    logs = list((runtime / 'logs').glob('runtime-*.log'))
    if not logs:
        return '尚无游戏运行日志；神经渲染未验证。'
    latest = max(logs,key=lambda path:path.stat().st_mtime_ns)
    with latest.open('rb') as stream:
        stream.seek(max(0,latest.stat().st_size-2*1024*1024))
        text = stream.read().decode('utf-8',errors='replace')
    lines = [line for line in text.splitlines() if 'DLSS NR:' in line]
    for line in reversed(lines):
        if 'first evaluate recorded' in line:
            return '本次运行：已记录神经渲染 Evaluate 调用；画面与 GPU 执行仍需验收。'
        if 'fail' in line.lower():
            return '本次运行：神经渲染失败，查看最新 runtime 日志。'
        if 'feature(s) created' in line:
            return '本次运行：NR 功能已创建，尚未确认 Evaluate。'
    return '本次运行尚无神经渲染 Evaluate 记录。菜单 / 视频可能不触发模型。'

class Panel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('失落的奥德赛 · PC 增强')
        self.geometry('850x860')
        self.minsize(780, 600)
        self.configure(bg='#101820')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10), background='#182530', foreground='#e3e9ed')
        style.configure('TFrame', background='#101820')
        style.configure('TLabel', background='#101820')
        style.configure('TButton', padding=(12, 8))
        style.configure('TCombobox', fieldbackground='#223543', foreground='#ffffff')
        style.map('TCombobox', fieldbackground=[('readonly', '#223543')], foreground=[('readonly', '#ffffff')])
        config = read_config()
        self.initial_config=config
        self.values = {}
        self.boxes = {}
        self.labels = {}
        self.adapters=[]
        self.capability_cache={}
        self.reports={}
        self.detecting=True
        self.probe_token=0
        self.probe_results=queue.Queue()
        canvas = tk.Canvas(self,bg='#101820',highlightthickness=0)
        scrollbar = ttk.Scrollbar(self,orient='vertical',command=canvas.yview)
        scrollbar.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        outer = ttk.Frame(canvas,padding=26)
        item = canvas.create_window((0,0),window=outer,anchor='nw')
        outer.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda event:canvas.itemconfigure(item,width=event.width))
        self.bind('<MouseWheel>',lambda event:canvas.yview_scroll(-int(event.delta/120),'units'))
        ttk.Label(outer, text='LOST ODYSSEY', font=('Segoe UI', 24, 'bold'), foreground='#d9b56b').pack(anchor='w')
        ttk.Label(outer, text='PC 增强设置', foreground='#8ca7b8').pack(anchor='w', pady=(0, 18))
        form = ttk.Frame(outer)
        form.pack(fill='x')
        form.columnconfigure(1, weight=1)
        def choice(key, title, options, initial, editable=False):
            row = len(self.values)
            ttk.Label(form, text=title,width=14).grid(row=row, column=0, sticky='w', pady=7, padx=(0, 25))
            self.labels[key]=form.grid_slaves(row=row,column=0)[0]
            variable = tk.StringVar(value=initial)
            self.values[key] = variable
            box = ttk.Combobox(form, textvariable=variable, values=options, state='normal' if editable else 'readonly')
            box.grid(row=row, column=1, sticky='ew', pady=7)
            self.boxes[key]=box
            return box
        def label(mapping, value):
            return next((k for k,v in mapping.items() if str(v)==str(value)), next(iter(mapping)))
        choice('resolution', '输出分辨率', RESOLUTIONS, f'{config.get("width",3440)} × {config.get("height",1440)}', True)
        choice('gpu', '渲染显卡', ['检测中…'], '检测中…')
        choice('aspect', '画面比例', list(ASPECTS), label(ASPECTS, config.get('aspect_ratio',0)))
        choice('render', '渲染分辨率', list(RENDER), label(RENDER, config.get('internal_resolution',0)))
        mode = 'SMAA' if config.get('antialiasing')=='2' else '关闭'
        if config.get('upscaler')=='1':
            mode = label(QUALITY, config.get('dlss_quality',0))
        choice('aa', '抗锯齿 / 超分辨率', list(AA), mode)
        choice('backend', '图形后端', ['Direct3D 12','Vulkan'], 'Vulkan' if config.get('graphics_backend')=='1' else 'Direct3D 12')
        choice('window', '窗口模式', ['窗口','无边框全屏'], '窗口' if config.get('window_mode','0')=='0' else '无边框全屏')
        choice('fps', '帧率上限', ['30','60','90','120','240'], config.get('frame_rate','30'))
        choice('fg', 'DLSS 帧生成', ['关闭'], '关闭')
        choice('fg_multiplier', '帧生成倍率', ['2×'], '2×')
        choice('fg_target', '目标显示帧率', list(FG_TARGETS), label(FG_TARGETS,config.get('frame_generation_target_fps',0)))
        ttk.Label(outer, text='DLSS 5 · 神经渲染', font=('Microsoft YaHei UI',12,'bold')).pack(anchor='w', pady=(18,0))
        nr_row = ttk.Frame(outer)
        nr_row.pack(fill='x',pady=(12,0))
        self.nr = tk.StringVar(value=str(min(PANEL_MAX_NR_PASSES,runtime_pass_limit(),int(config.get('dlss_neural_rendering','0')))))
        ttk.Label(nr_row,text='叠加处理次数',width=14).pack(side='left',padx=(0,25))
        self.nr_toggle = ttk.Combobox(nr_row,textvariable=self.nr,values=['0','1','2','3','4'],state='readonly',width=5)
        self.nr_toggle.pack(side='left', fill='x', expand=True)
        intensity_row=ttk.Frame(outer)
        intensity_row.pack(fill='x',pady=(10,0))
        ttk.Label(intensity_row,text='单次模型强度（%）',width=14).pack(side='left',padx=(0,25))
        self.nr_intensity=tk.StringVar(value=str(min(200,int(config.get('dlss_nr_intensity','100')))))
        self.nr_strength=ttk.Combobox(intensity_row,textvariable=self.nr_intensity,values=['0','25','50','75','100','125','150','175','200'],state='readonly',width=6)
        self.nr_strength.pack(side='left', fill='x', expand=True)
        actions = ttk.Frame(outer)
        actions.pack(fill='x', pady=18)
        ttk.Button(actions, text='匹配当前屏幕', command=self.match_screen).pack(side='left')
        ttk.Button(actions, text='保存设置', command=self.save).pack(side='right', padx=6)
        ttk.Button(actions, text='保存并启动', command=self.launch).pack(side='right')
        self.status = tk.StringVar(value='保存前请退出游戏。')
        ttk.Label(outer, textvariable=self.status, wraplength=730).pack(anchor='w')
        self.refresh_nr()
        self.boxes['gpu'].bind('<<ComboboxSelected>>',lambda event:self.detect_selected_gpu())
        self.boxes['backend'].bind('<<ComboboxSelected>>',lambda event:self.refresh_graphics())
        self.boxes['aa'].bind('<<ComboboxSelected>>',lambda event:self.refresh_graphics())
        self.boxes['fg'].bind('<<ComboboxSelected>>',lambda event:self.refresh_graphics())
        self.refresh_graphics()
        threading.Thread(target=self.load_adapters,daemon=True).start()
        self.after(50,self.poll_capabilities)

    def refresh_nr(self):
        self.nr_compatible, _ = inspect_nr(nr_path())
        self.nr_toggle.configure(state='readonly' if self.nr_compatible else 'disabled')
        if not self.nr_compatible:
            self.nr.set('0')

    def load_adapters(self):
        try:
            result=run_gpu_probe('list')
            self.probe_results.put(('inventory',result,None))
        except (OSError,ValueError,subprocess.TimeoutExpired) as error:
            self.probe_results.put(('inventory',None,str(error)))

    def selected_adapter(self):
        name=self.values['gpu'].get()
        return next((adapter for adapter in self.adapters if adapter['label']==name),{})

    def detect_selected_gpu(self):
        adapter=self.selected_adapter()
        self.probe_token+=1
        token=self.probe_token
        self.reports={}
        self.detecting=True
        self.refresh_graphics()
        if adapter['index'] in self.capability_cache:
            self.accept_capabilities(self.capability_cache[adapter['index']])
            return
        self.status.set('正在检测显卡与运行库能力…')
        def worker():
            reports={}
            errors=[]
            for backend in ('d3d12','vulkan'):
                try:
                    reports[backend]=run_gpu_probe(adapter['index'],backend)
                except (OSError,ValueError,subprocess.TimeoutExpired) as error:
                    errors.append(f'{backend}: {error}')
            self.probe_results.put((token,reports,'; '.join(errors)))
        threading.Thread(target=worker,daemon=True).start()

    def accept_capabilities(self,reports,error=''):
        self.reports=reports
        self.capability_error=error
        self.detecting=False
        if not error:
            self.capability_cache[self.selected_adapter()['index']]=reports
        self.refresh_graphics()
        if not error:
            self.status.set('显卡能力检测完成；保存前请退出游戏。')
        else:
            self.status.set('部分能力检测失败，相关选项已关闭。')

    def poll_capabilities(self):
        try:
            while True:
                token,result,error=self.probe_results.get_nowait()
                if token=='inventory':
                    self.adapters=(result or {}).get('adapters',[])
                    for adapter in self.adapters:
                        adapter['label']=f"{adapter['name']} [{adapter['index']+1}]"
                    if self.adapters:
                        preferred=self.initial_config.get('gpu_device','').strip('"')
                        adapter=next((item for item in self.adapters if item['name']==preferred),
                            max(self.adapters,key=lambda item:item['memory']))
                        self.boxes['gpu'].configure(values=[item['label'] for item in self.adapters])
                        self.values['gpu'].set(adapter['label'])
                        self.detect_selected_gpu()
                    else:
                        self.detecting=False
                        self.values['gpu'].set('未检测到显卡')
                        self.boxes['gpu'].configure(state='disabled')
                        self.refresh_graphics()
                        self.status.set('显卡检测失败；高级选项已关闭。')
                elif token==self.probe_token:
                    self.accept_capabilities(result,error)
        except queue.Empty:
            pass
        self.after(50,self.poll_capabilities)

    def refresh_graphics(self):
        options=graphics_options(self.selected_adapter(),self.reports,self.values['backend'].get(),self.nr_compatible)
        self.options=options
        for key,choices in [('aa',options['aa']),('fg',options['fg_modes']),('fg_multiplier',options['multipliers'])]:
            self.boxes[key].configure(values=choices,state='disabled' if self.detecting else 'readonly')
            if not self.detecting and self.values[key].get() not in choices:
                self.values[key].set(choices[0])
        if not self.detecting and not getattr(self,'restored_fg',False):
            self.restored_fg=True
            saved=self.initial_config
            desired=next((name for name,mode in FG_MODES.items() if str(mode)==saved.get('frame_generation_mode','0')),'关闭')
            if saved.get('frame_generation_provider')=='1' and desired in options['fg_modes']:
                self.values['fg'].set(desired)
                multiplier=saved.get('frame_generation_multiplier','2')+'×'
                if multiplier in options['multipliers']:
                    self.values['fg_multiplier'].set(multiplier)
        mode=self.values['fg'].get()
        for key,visible in [('fg_multiplier',mode=='固定倍率'),('fg_target',mode=='动态倍率')]:
            for widget in (self.boxes[key],self.labels[key]):
                widget.grid() if visible else widget.grid_remove()
        nr_enabled=options['nr'] and self.values['aa'].get() in QUALITY and not self.detecting
        self.nr_toggle.configure(state='readonly' if nr_enabled else 'disabled')
        self.nr_strength.configure(state='readonly' if nr_enabled else 'disabled')
        if not nr_enabled and not self.detecting:
            self.nr.set('0')

    def match_screen(self):
        self.values['resolution'].set(f'{self.winfo_screenwidth()} × {self.winfo_screenheight()}')
        self.values['aspect'].set(next(iter(ASPECTS)))
        self.values['render'].set(next(iter(RENDER)))
        self.status.set('已匹配屏幕；保存后生效。')

    def changes(self):
        if self.detecting:
            raise ValueError('请等待显卡能力检测完成。')
        width,height = validate_resolution(self.values['resolution'].get())
        aa = self.values['aa'].get()
        passes = int(self.nr.get())
        fps=int(self.values['fps'].get())
        if not runtime_supports_fps(fps):
            raise ValueError('当前游戏程序不支持此帧率档位，请使用已部署的 240 FPS 增强版。')
        if not 0 <= passes <= PANEL_MAX_NR_PASSES:
            raise ValueError('面板叠加处理次数范围为 0–4。')
        if passes>runtime_pass_limit():
            raise ValueError('当前游戏程序最高支持 4 次；5 次需要已编译的增强版本。')
        backend = 0 if self.values['backend'].get()=='Direct3D 12' else 1
        options=graphics_options(self.selected_adapter(),self.reports,self.values['backend'].get(),self.nr_compatible)
        if aa not in options['aa']:
            raise ValueError('所选显卡或运行库不支持此 DLSS 模式。')
        fg=self.values['fg'].get()
        multiplier=self.values['fg_multiplier'].get()
        if fg not in options['fg_modes'] or (fg!='关闭' and multiplier not in options['multipliers']):
            raise ValueError('所选显卡或图形后端不支持此帧生成设置。')
        if passes and not options['nr']:
            raise ValueError('当前显卡或图形后端不支持附带的神经渲染运行库。')
        if passes and (not self.nr_compatible or aa not in QUALITY or backend != 0):
            raise ValueError('实验 DLSS 5 当前要求兼容运行库、DLSS / DLAA 和 Direct3D 12。')
        return dict(width=width,height=height,aspect_ratio=ASPECTS[self.values['aspect'].get()],
                    internal_resolution=RENDER[self.values['render'].get()],
                    upscaler=AA[aa][0],antialiasing=AA[aa][1],fxaa=0,
                    dlss_quality=QUALITY.get(aa,0),graphics_backend=backend,
                    window_mode=int(self.values['window'].get()=='无边框全屏'),
                    frame_rate=fps,dlss_neural_rendering=passes,
                    dlss_nr_intensity=int(self.nr_intensity.get()),
                    gpu_device=options['device_name'],frame_generation_provider=int(fg!='关闭'),
                    frame_generation_mode=FG_MODES[fg],
                    frame_generation_multiplier=int(multiplier.removesuffix('×')),
                    frame_generation_target_fps=FG_TARGETS[self.values['fg_target'].get()])

    def save(self):
        try:
            if game_running():
                raise ValueError('请先退出游戏，再保存或启动，避免覆盖运行中的设置。')
            save_config(self.changes())
            self.status.set('设置已保存，原配置已备份到 settings-backups。')
            return True
        except (ValueError,OSError,KeyError) as error:
            messagebox.showerror('未保存',str(error))
            return False

    def launch(self):
        if not self.save():
            return
        executable = runtime_executable()
        if not executable.is_file():
            messagebox.showerror('未启动','未找到 LostOdysseyRecomp.exe。')
            return
        env = os.environ.copy()
        env.pop('LO_FPS',None)  # Let the saved frame cap apply.
        env.pop('LO_GRAPHICS_API',None)
        for key in ('LO_FG_PROVIDER','LO_FG_MODE','LO_FG_MULTIPLIER','LO_FG_TARGET_FPS','LO_DLSS_FG'):
            env.pop(key,None)
        if executable.name=='LostOdysseyEnhanced.exe':
            env['LO_NO_UPDATE']='1'
        if int(self.nr.get()):
            env['LO_DLSS_NR_PATH']=str(nr_path())
        else:
            env.pop('LO_DLSS_NR_PATH',None)
        try:
            if FROZEN and os.name=='nt':
                ctypes.windll.kernel32.SetDllDirectoryW(None)
            try:
                subprocess.Popen([str(executable)],cwd=RUNTIME,env=env)
            finally:
                if FROZEN and os.name=='nt':
                    ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
            self.status.set('游戏已启动；运行中不要修改配置。')
        except OSError as error:
            messagebox.showerror('未启动',str(error))

if __name__=='__main__':
    if os.name=='nt':
        ctypes.windll.user32.SetProcessDPIAware()
    if '--self-test' in sys.argv:
        index=sys.argv.index('--self-test')
        destination=Path(sys.argv[index+1])
        gui=Panel()
        gui.withdraw()
        deadline=time.monotonic()+65
        while gui.detecting and time.monotonic()<deadline:
            gui.update()
            time.sleep(0.02)
        gui.update_idletasks()
        result={'frozen':FROZEN,'runtime':str(RUNTIME),'executable':str(runtime_executable()),
                'supports_240':runtime_supports_fps(240),'panel_nr_max':PANEL_MAX_NR_PASSES,
                'nr_runtime_compatible':inspect_nr(nr_path())[0],
                'adapter':gui.selected_adapter(),'capabilities':gui.reports,'available':gui.options,
                'capability_error':getattr(gui,'capability_error',''),
                'tk':gui.tk.call('info','patchlevel'),'settings':gui.changes()}
        result['backend_options']={backend:graphics_options(gui.selected_adapter(),gui.reports,backend,gui.nr_compatible)
            for backend in ('Direct3D 12','Vulkan')}
        if '固定倍率' in gui.options['fg_modes']:
            gui.values['fg'].set('固定倍率')
            gui.values['fg_multiplier'].set('2×')
            gui.refresh_graphics()
            result['fixed_fg_settings']=gui.changes()
        destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        gui.destroy()
    else:
        Panel().mainloop()
