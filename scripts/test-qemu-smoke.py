#!/usr/bin/env python3
"""Run real signed SDK-built Go and C interop regressions in an OHOS guest."""
import argparse
import json
from pathlib import Path
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['arm64', 'armv7a', 'x86_64'], required=True)
p.add_argument('--work', type=Path, default=ROOT / '.work/qemu')
p.add_argument('--input', type=Path)
a = p.parse_args()
arch = {'arm64': 'arm64', 'armv7a': 'arm', 'x86_64': 'amd64'}[a.arch]
source = a.input or ROOT / '.work/smoke' / arch
payload = ROOT / '.work/smoke' / (arch + '-runtime.tar.gz')
files = ['smoke', 'smoke-pure', 'libanswer.so', 'loader', 'archive-loader']
with tarfile.open(payload, 'w:gz', format=tarfile.GNU_FORMAT) as t:
    for name in files:
        t.add(source / name, arcname=name)

def call(command, *args):
    cmd = ['python3', ROOT / 'scripts/qemu.py', '--arch', a.arch, '--work', a.work, command, *args]
    return subprocess.check_output(list(map(str, cmd)), text=True)
guest = '/data/local/tmp/go-patch'
call('send', payload, guest + '/smoke.tar.gz')
script = f'''set -e
cd {guest}
mkdir -p smoke
cd smoke
tar -xzf ../smoke.tar.gz
export PATH={guest}/bin:$PATH
for f in {' '.join(files)}; do
 binary-sign-tool sign -inFile "$f" -outFile "$f" -selfSign 1
done
chmod 755 smoke smoke-pure loader archive-loader
./smoke-pure
./smoke
./loader ./libanswer.so
./archive-loader
'''
started = time.time()
output = call('shell', script, '--timeout', 1200)
for marker in ['GO_OHOS_SMOKE_OK', 'GO_OHOS_DLOPEN_OK', 'GO_OHOS_CARCHIVE_OK']:
    if marker not in output:
        raise SystemExit('missing runtime regression marker: ' + marker)
log = source / 'qemu-runtime.log'
log.write_text(output)
(source / 'qemu-runtime.json').write_text(json.dumps(dict(arch=arch, result='pass',
    elapsed_seconds=time.time()-started, qemu=json.loads((a.work/a.arch/'state.json').read_text())),indent=2)+'\n')
print(output[-5000:])
