"""Package only shader sources, with a reproducible ZIP timestamp."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
target = root / 'dist' / 'Aqualumen-0.4.0.zip'
target.parent.mkdir(exist_ok=True)
with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
    for source in sorted([*(root / 'shaders').rglob('*'), root / 'LICENSE']):
        if source.is_file():
            entry = ZipInfo(source.relative_to(root).as_posix(), (2026, 10, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, source.read_bytes())
print(target)
