import importlib.util
import hashlib
import json
import struct
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Import a matching set of four Lost Odyssey GOD packages.')
parser.add_argument('source', type=Path, help='GOD package directory (00007000).')
SOURCE = parser.parse_args().source
DEST = ROOT / 'runtime/v0.9.52/LostOdysseyRecomp-windows-x64-v0.9.52/game'
spec = importlib.util.spec_from_file_location('god', ROOT / 'upstream/tools/god_extract.py')
god = importlib.util.module_from_spec(spec)
spec.loader.exec_module(god)
records = []
required = {'default.xex', 'lo.fpd', 'lo.fpi', *('xenon_' + x + '.fpd' for x in ['battle','chr','event','field','loc','mov','obj','scr','snd','sys','vfx','world'])}
expected = {4: ['39F7D748','0EF8CEA8','309E3386','7B21A91D'], 3: ['368DE6DD','1888BE4E','6DD59D08','0C0E80B5']}
for package in sorted(SOURCE.iterdir()):
    if not package.is_file():
        continue
    reader = god.Svod(str(package) + '.data')
    try:
        vd = reader.read(0x10000, god.SECTOR)
        assert vd[:20] == god.GDF_MAGIC and vd[0x7EC:0x800] == god.GDF_MAGIC
        entries = list(god.walk(reader, *struct.unpack_from('<II', vd, 20)))
        assert required <= {p.lower() for p, _, _, d in entries if not d}, 'Missing required files'
        xentry = next(e for e in entries if e[0].lower() == 'default.xex')
        xex = reader.read(xentry[1] * god.SECTOR, xentry[2])
        assert xex[:4] == b'XEX2'
        count = struct.unpack_from('>I', xex, 20)[0]
        exec_offset = next(v for k,v in (struct.unpack_from('>II', xex, 24+i*8) for i in range(count)) if k == 0x40006)
        media, version, base, title = struct.unpack_from('>IIII', xex, exec_offset)
        disc, discs = xex[exec_offset+18:exec_offset+20]
        assert title == 0x4D5307FA and 1 <= disc <= 4 and discs == 4
        assert version == base and f'{media:08X}' == expected[version][disc-1], 'Unsupported edition'
        destination = DEST / f'disc{disc}'
        total = sum(s for _,_,s,d in entries if not d)
        print(f'Disc {disc}: version {version}, media {media:08X}, {total/2**30:.2f} GiB', flush=True)
        for path, start, size, is_dir in entries:
            target = (destination / path).resolve()
            assert target.is_relative_to(destination.resolve()), 'Unsafe path'
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.stat().st_size == size:
                continue
            partial = target.with_name(target.name + '.partial')
            with partial.open('wb') as stream:
                reader.copy(start * god.SECTOR, size, stream.write)
            assert partial.stat().st_size == size
            partial.replace(target)
        records.append(dict(disc=disc,version=version,media=f'{media:08X}',package=package.name,files=sum(not e[3] for e in entries),bytes=total,xex_sha256=hashlib.sha256(xex).hexdigest()))
        print(f'Disc {disc}: extracted and file sizes checked', flush=True)
    finally:
        for stream in reader.files:
            stream.close()
assert {r['disc'] for r in records} == {1,2,3,4}
assert len({r['version'] for r in records}) == 1, 'Mixed editions'
(ROOT / 'downloads').mkdir(exist_ok=True)
(ROOT / 'downloads/disc-inventory.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print('All four discs imported; matching supported edition.', flush=True)
