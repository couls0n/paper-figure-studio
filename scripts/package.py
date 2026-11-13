#!/usr/bin/env python3
"""Package this independent skill and its complete resources using stdlib only."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('output', help='ZIP path outside the skill directory')
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
output = Path(args.output).expanduser().resolve()
if output == root or root in output.parents:
    parser.error('Write the archive outside the skill to avoid recursive packaging')
manifest_path = root / 'references' / 'bundle-manifest.json'
files = []
for path in sorted(root.rglob('*')):
    relative = path.relative_to(root)
    if relative.parts[0] in {'.git', '.idea', '.vscode', '.venv', '.figureforge', 'node_modules', 'projects', 'output', 'dist'}:
        continue
    if len(relative.parts) == 1 and path.name.startswith('.env') and path.name != '.env.example':
        continue
    if path.is_symlink():
        raise SystemExit(f'Refusing dependent symlink: {path}')
    if not path.is_file() or path == manifest_path:
        continue
    if '__pycache__' in path.parts or path.name == '.DS_Store':
        continue
    content = path.read_bytes()
    files.append({'path':path.relative_to(root).as_posix(), 'size':len(content),
                  'sha256':hashlib.sha256(content).hexdigest()})
manifest = {'schema':'figureforge-skill-bundle-v1', 'name':'figureforge',
            'files':files, 'file_count':len(files), 'total_bytes':sum(x['size'] for x in files),
            'platform_requirements':['Node.js >=20', 'Chrome/Chromium',
                                     'Host agent with file/script/vision capabilities',
                                     'Host image tool for the bitmap generation route']}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
output.parent.mkdir(parents=True, exist_ok=True)
temporary = output.with_suffix(output.suffix+'.tmp')
with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                     allowZip64=True) as archive:
    for entry in files:
        archive.write(root/entry['path'], 'figureforge/'+entry['path'])
    archive.write(manifest_path, 'figureforge/references/bundle-manifest.json')
with zipfile.ZipFile(temporary) as archive:
    broken = archive.testzip()
    if broken:
        raise SystemExit('ZIP checksum failure: '+broken)
temporary.replace(output)
checksum=hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix(output.suffix+'.sha256').write_text(checksum+'  '+output.name+'\n')
print(json.dumps({'archive':str(output),'files':len(files)+1,'uncompressed_bytes':manifest['total_bytes']+manifest_path.stat().st_size,
                  'archive_bytes':output.stat().st_size,'sha256':checksum},ensure_ascii=False,indent=2))
