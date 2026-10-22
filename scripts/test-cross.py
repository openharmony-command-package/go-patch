#!/usr/bin/env python3
"""Build executable, cgo, c-shared and c-archive regressions for three OHOS ABIs."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--go', type=Path, default=ROOT / '.work/upstream/go/bin/go')
p.add_argument('--sdk', type=Path, default=os.environ.get('OHOS_NDK_HOME'))
p.add_argument('--arch', choices=['all', 'arm64', 'arm', 'amd64'], default='all')
p.add_argument('--output', type=Path, default=ROOT / '.work/smoke')
a = p.parse_args()
if not a.sdk:
    p.error('--sdk or OHOS_NDK_HOME is required')
results = []
for arch in (['arm64', 'arm', 'amd64'] if a.arch == 'all' else [a.arch]):
    out = a.output.resolve() / arch
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GOOS='openharmony', GOARCH=arch, GOARM='7',
               GOCACHE=str(ROOT / '.work/gocache'), GOTOOLCHAIN='local',
               OHOS_NDK_HOME=str(a.sdk.resolve()), CGO_ENABLED='1',
               CC=shlex.join([str(ROOT / ('scripts/cc-' + arch))]),
               CXX=shlex.join([str(ROOT / ('scripts/cxx-' + arch))]),
               AR=str(a.sdk.resolve() / 'llvm/bin/llvm-ar'))
    def run(cmd, **kw):
        print('+', shlex.join(list(map(str, cmd))), flush=True)
        subprocess.run(list(map(str, cmd)), cwd=ROOT, env=env, check=True, **kw)
    with open(out / 'build.log', 'w') as log:
        run([a.go, 'build', '-o', out / 'smoke', ROOT / 'tests/smoke/main.go'],
            stdout=log, stderr=subprocess.STDOUT)
        subprocess.run([str(a.go), 'build', '-o', str(out / 'smoke-pure'),
                        str(ROOT / 'tests/smoke/main.go')], cwd=ROOT,
                       env=dict(env, CGO_ENABLED='0'), stdout=log,
                       stderr=subprocess.STDOUT, check=True)
        run([a.go, 'build', '-buildmode=c-shared', '-o', out / 'libanswer.so',
             ROOT / 'tests/shared/main.go'], stdout=log, stderr=subprocess.STDOUT)
        run([a.go, 'build', '-buildmode=c-archive', '-o', out / 'libarchive.a',
             ROOT / 'tests/shared/main.go'], stdout=log, stderr=subprocess.STDOUT)
        run(['python3', ROOT / 'scripts/cc.py', '--arch', arch,
             ROOT / 'tests/shared/loader.c', '-pthread', '-ldl', '-o', out / 'loader'],
            stdout=log, stderr=subprocess.STDOUT)
        run(['python3', ROOT / 'scripts/cc.py', '--arch', arch,
             ROOT / 'tests/shared/archive-loader.c', out / 'libarchive.a',
             '-pthread', '-ldl', '-lm', '-o', out / 'archive-loader'],
            stdout=log, stderr=subprocess.STDOUT)
    readelf = a.sdk.resolve() / 'llvm/bin/llvm-readelf'
    meta = subprocess.check_output([str(readelf), '-h', '-l', '-d',
                                    str(out / 'smoke'), str(out / 'libanswer.so')], text=True)
    (out / 'elf-metadata.txt').write_text(meta)
    interp = {'arm64': 'aarch64', 'arm': 'arm', 'amd64': 'x86_64'}[arch]
    if '/lib/ld-musl-' + interp + '.so.1' not in meta:
        raise SystemExit('incorrect OHOS ELF interpreter: ' + arch)
    results.append(dict(arch=arch, result='build-pass', runtime='pending'))
    print('CROSS_BUILD_PASS', arch, flush=True)
(a.output / ('cross-' + a.arch + '.json')).write_text(json.dumps(results, indent=2) + '\n')
