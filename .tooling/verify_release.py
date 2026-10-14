import hashlib
import json
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
name='LostOdysseyEnhanced-0.2.0-windows-x64-complete'
archive=root/'releases'/f'{name}.zip'
with zipfile.ZipFile(archive) as output:
    assert output.testzip() is None
    manifest=json.loads(output.read(f'{name}/manifest.json'))
    assert manifest['version']=='0.2.0'
    for relative in ('LostOdysseySettings.exe','GpuCapabilities.exe','LostOdysseyEnhanced.exe',
                     'source/panel.py','source/gpu_capabilities.cpp','settings.ini'):
        payload=output.read(f'{name}/{relative}')
        assert hashlib.sha256(payload).hexdigest()==manifest['files'][relative]['sha256']
    assert output.read(f'{name}/source/panel.py')==(root/'enhancements/panel.py').read_bytes()
    settings=output.read(f'{name}/settings.ini').decode('utf-8').splitlines()
    assert 'frame_generation_provider=0' in settings
    assert 'dlss_neural_rendering=0' in settings
    names=output.namelist()
    assert all(any(f'/game/disc{disc}/' in item for item in names) for disc in (1,2,3,4))
    assert any('/game/dlc/' in item for item in names)
    assert not any(any(f'/{folder}/' in item for folder in ('save','profile','logs','settings-backups')) for item in names)
    print(f'ZIP CRC verified: {len(names)} files, four discs, DLC, neutral defaults, current panel and helper.')
source=root/'releases/LostOdysseyEnhanced-0.2.0-source.zip'
if source.is_file():
    with zipfile.ZipFile(source) as output:
        assert output.testzip() is None
        assert 'LostOdysseyEnhanced-source/enhancements/gpu_capabilities.cpp' in output.namelist()
    print('Source ZIP CRC verified.')
