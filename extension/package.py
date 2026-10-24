"""Package the local MV3 build without including source, .env files or secrets."""
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parent
out=Path(os.getenv('FIVE_BONES_EXTENSION_OUT',str(root/'dist'))).resolve()
archive=out.parent/'fivebones-extension.zip'
required=[out/'manifest.json',out/'content.js']
if not all(path.is_file() for path in required):
    raise SystemExit('Build the unpacked extension first')
with ZipFile(archive,'w',compression=ZIP_DEFLATED) as package:
    for path in sorted(out.rglob('*')):
        if path.is_file() and (path.name in ('manifest.json','content.js') or path.suffix=='.png'):
            package.write(path,path.relative_to(out))
print(f'Unpacked: {out}\nZIP: {archive}')
