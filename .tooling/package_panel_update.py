import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = root / 'releases/LostOdysseyEnhanced-0.1.1-windows-x64-complete'
payload = {
    'LostOdysseySettings.exe': (root / 'downloads/panel-dist/LostOdysseySettings.exe').read_bytes(),
    'source/panel.py': (root / 'enhancements/panel.py').read_bytes(),
    '使用说明.txt': (base / '使用说明.txt').read_bytes().replace(b'0.1.1', b'0.1.2'),
}
manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
manifest['version'] = '0.1.2'
for name, data in payload.items():
    manifest['files'][name] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
payload['manifest.json'] = json.dumps(manifest, indent=2).encode('utf-8')
payload['更新说明.txt'] = ('启动面板更新 0.1.2\n\n关闭增强设置面板，将本压缩包解压到已有整合版目录，覆盖同名文件。\n'
    '本次去掉分隔条，将叠加处理次数和模型强度下拉框改为全宽。\n'
    '无需重新下载游戏资源，不改动游戏设置和存档。\n').encode('utf-8')
destination = root / 'releases/LostOdysseyEnhanced-0.1.2-panel-update.zip'
with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name, data in payload.items():
        archive.writestr(name, data)
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
destination.with_suffix('.zip.sha256').write_text(
    hashlib.sha256(destination.read_bytes()).hexdigest() + '  ' + destination.name + '\n', encoding='ascii')
print(destination)
