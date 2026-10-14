import tempfile
import unittest
import hashlib
import json
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
from panel import merge_config, save_config, validate_resolution, inspect_nr, nr_execution_status, runtime_pass_limit, runtime_supports_fps, graphics_options, Panel

class SettingsTests(unittest.TestCase):
    def test_preserves_unrelated_controls_and_deduplicates(self):
        original = '# user settings\nwidth=1280\nkeyboard_map=a:29,b:27\nwidth=1920\nhdr=1\n'
        updated = merge_config(original, {'width':5120,'height':1440})
        self.assertEqual(updated.count('width='),1)
        self.assertIn('keyboard_map=a:29,b:27\nhdr=1\n',updated)
        self.assertTrue(updated.startswith('# user settings\n'))

    def test_backup_and_atomic_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'settings.ini'
            path.write_text('save_anywhere=0\nwidth=1280\n',encoding='utf-8')
            save_config({'width':3440,'height':1440,'aspect_ratio':0},path)
            backups = list((path.parent/'settings-backups').glob('*.ini'))
            self.assertEqual(len(backups),1)
            self.assertEqual(backups[0].read_text(), 'save_anywhere=0\nwidth=1280\n')
            self.assertIn('width=3440',path.read_text())
            self.assertFalse(list(path.parent.glob('*.tmp')))

    def test_ultrawide_and_invalid_resolution(self):
        self.assertEqual(validate_resolution('5120 × 1440'),(5120,1440))
        self.assertEqual(validate_resolution('7680x2160'),(7680,2160))
        for invalid in ['0x1440','8000x2160','5120x0','1920x1080\nwidth=1','oops']:
            with self.assertRaises(ValueError):
                validate_resolution(invalid)

    def test_nr_does_not_claim_missing_or_invalid_dll_works(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'nvngx_dlssnr.dll'
            self.assertFalse(inspect_nr(path)[0])
            path.write_bytes(b'not a DLL')
            self.assertFalse(inspect_nr(path)[0])

    def test_nr_recorded_call_is_distinct_from_file_presence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'logs').mkdir()
            log=root/'logs/runtime-test.log'
            log.write_text('DLSS NR: 1 feature(s) created for 3440x1440\n',encoding='utf-8')
            self.assertIn('尚未确认',nr_execution_status(root))
            log.write_text('DLSS NR: first evaluate recorded for 3440x1440, 1 pass(es)\n',encoding='utf-8')
            self.assertIn('仍需验收',nr_execution_status(root))

    def test_five_pass_receipt_is_bound_to_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)
            exe=runtime/'LostOdysseyRecomp.exe'
            exe.write_bytes(b'enhanced test build')
            self.assertEqual(runtime_pass_limit(runtime),4)
            (runtime/'enhancements-build.json').write_text(json.dumps({'max_nr_passes':5,'exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}))
            self.assertEqual(runtime_pass_limit(runtime),5)
            exe.write_bytes(b'original runtime')
            self.assertEqual(runtime_pass_limit(runtime),4)

    def test_240_requires_matching_enhanced_build(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)
            exe=runtime/'LostOdysseyEnhanced.exe'
            exe.write_bytes(b'240 FPS build')
            receipt={'max_nr_passes':5,'executable':exe.name,'exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'native_rates':[30,60,90,120,240]}
            (runtime/'enhancements-build.json').write_text(json.dumps(receipt))
            self.assertTrue(runtime_supports_fps(240,runtime))
            receipt.pop('native_rates')
            (runtime/'enhancements-build.json').write_text(json.dumps(receipt))
            self.assertFalse(runtime_supports_fps(240,runtime))

    def test_panel_limits_selection_to_four_passes(self):
        def variable(value):
            return SimpleNamespace(get=lambda:value)
        panel=SimpleNamespace(values={key:variable(value) for key,value in {
            'resolution':'3440 × 1440','aa':'DLSS Quality','backend':'Direct3D 12',
            'aspect':'跟随分辨率（含 32:9 / 16:10）','render':'跟随输出（最高 4K 高度）',
            'window':'窗口','fps':'30','fg':'关闭','fg_multiplier':'2×','fg_target':'跟随屏幕'}.items()},
            nr=variable('5'),nr_intensity=variable('100'),nr_compatible=True,detecting=False,
            selected_adapter=lambda:{'name':'NVIDIA GeForce RTX 5090','vendor':0x10de},
            reports={'d3d12':{'sr':True}})
        with patch('panel.runtime_pass_limit',return_value=5):
            with self.assertRaises(ValueError):
                Panel.changes(panel)
            panel.nr=variable('4')
            self.assertEqual(Panel.changes(panel)['dlss_neural_rendering'],4)
        panel.nr=variable('5')
        with patch('panel.runtime_pass_limit',return_value=4):
            with self.assertRaises(ValueError):
                Panel.changes(panel)

    def test_sdk_capabilities_filter_generation_and_backend(self):
        adapter={'name':'NVIDIA GeForce RTX 5090','vendor':0x10de}
        reports={'d3d12':{'sr':True,'fg':True,'max_multiplier':6,'dynamic':True},
                 'vulkan':{'sr':True,'fg':True,'device_name':'Vulkan adapter name'}}
        d3d=graphics_options(adapter,reports,'Direct3D 12',True)
        self.assertEqual(d3d['multipliers'],['2×','3×','4×','5×','6×'])
        self.assertIn('动态倍率',d3d['fg_modes'])
        self.assertTrue(d3d['nr'])
        vk=graphics_options(adapter,reports,'Vulkan',True)
        self.assertEqual(vk['fg_modes'],['关闭','固定倍率'])
        self.assertFalse(vk['nr'])
        self.assertEqual(vk['device_name'],'Vulkan adapter name')
        # Even a 5090 gets no FG when the SDK rejects the runtime/driver.
        reports['d3d12']['fg']=False
        self.assertEqual(graphics_options(adapter,reports,'Vulkan',True)['fg_modes'],['关闭'])

    def test_older_and_unknown_adapters_do_not_gain_unsupported_features(self):
        adapter={'name':'NVIDIA GeForce RTX 4090','vendor':0x10de}
        reports={'d3d12':{'sr':True,'fg':True,'max_multiplier':2,'dynamic':False}}
        options=graphics_options(adapter,reports,'Direct3D 12',True)
        self.assertEqual(options['multipliers'],['2×'])
        self.assertNotIn('动态倍率',options['fg_modes'])
        self.assertFalse(options['nr'])
        reports['d3d12']['fg']=False
        self.assertIn('DLAA',graphics_options(adapter,reports,'Direct3D 12',True)['aa'])
        unknown=graphics_options({}, {}, 'Direct3D 12',True)
        self.assertEqual(unknown['aa'],['关闭','SMAA'])
        self.assertEqual(unknown['fg_modes'],['关闭'])
        self.assertFalse(unknown['nr'])

    def test_frame_generation_configuration_and_invalid_requests(self):
        def variable(value): return SimpleNamespace(get=lambda:value)
        panel=SimpleNamespace(values={key:variable(value) for key,value in {
            'resolution':'1920 × 1080','aa':'SMAA','backend':'Direct3D 12',
            'aspect':'16:9','render':'原生像素','window':'窗口','fps':'60',
            'fg':'固定倍率','fg_multiplier':'4×','fg_target':'240'}.items()},
            nr=variable('0'),nr_intensity=variable('100'),nr_compatible=False,detecting=False,
            selected_adapter=lambda:{'name':'RTX 5090','vendor':0x10de},
            reports={'d3d12':{'sr':True,'fg':True,'max_multiplier':4,'dynamic':True},
                     'vulkan':{'sr':True,'fg':True}})
        result=Panel.changes(panel)
        self.assertEqual(result['frame_generation_provider'],1)
        self.assertEqual(result['frame_generation_mode'],1)
        self.assertEqual(result['frame_generation_multiplier'],4)
        self.assertEqual(result['gpu_device'],'RTX 5090')
        panel.values['fg_multiplier']=variable('6×')
        with self.assertRaises(ValueError): Panel.changes(panel)
        panel.values['fg_multiplier']=variable('2×')
        panel.values['fg']=variable('动态倍率')
        self.assertEqual(Panel.changes(panel)['frame_generation_target_fps'],240)
        panel.values['backend']=variable('Vulkan')
        with self.assertRaises(ValueError): Panel.changes(panel)
        panel.detecting=True
        with self.assertRaises(ValueError): Panel.changes(panel)

if __name__=='__main__':
    unittest.main()
