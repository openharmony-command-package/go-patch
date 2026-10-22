#!/usr/bin/env python3
"""Exercise an unpacked release toolchain on its real host (including Windows).

Always builds all three OHOS pure-Go targets. --sdk additionally builds cgo,
c-shared and c-archive using the packaged native compiler wrappers.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
LOCK=json.loads((ROOT/'manifest.json').read_text())
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain', type=Path, required=True, help='unpacked go directory')
p.add_argument('--sdk', type=Path)
p.add_argument('--output', type=Path, default=ROOT/'.work/host-check')
a = p.parse_args()
a.toolchain, a.output = a.toolchain.resolve(), a.output.resolve()
exe = '.exe' if os.name == 'nt' else ''
go = a.toolchain/'bin'/('go'+exe)
env = dict(os.environ, GOROOT=str(a.toolchain), GOTOOLCHAIN='local', GOENV='off',
           GOCACHE=str(a.output/'cache'), GOARM='7')
host = subprocess.check_output([str(go),'env','GOHOSTOS','GOHOSTARCH'],env=env,text=True).split()
version = subprocess.check_output([str(go),'version'],env=env,text=True).strip()
assert version.startswith('go version '+LOCK['go']['version']+' '),version
info=json.loads((a.toolchain/'BUILD-INFO.json').read_text())
patch=ROOT/'patch'/LOCK['patch']['filename']
assert info['patch_sha256']==hashlib.sha256(patch.read_bytes()).hexdigest(),'toolchain does not match the current patch'
def compiler_path(path):
    # CC/CXX are parsed by Go's quoted.Split, including on Windows.
    value=str(path)
    if "'" not in value:return "'"+value+"'"
    if '"' not in value:return '"'+value+'"'
    raise ValueError('compiler path contains both quote characters')
a.output.mkdir(parents=True,exist_ok=True)
results=[]
with open(a.output/'build.log','w') as log:
    for arch in ['arm64','arm','amd64']:
        out=a.output/arch
        out.mkdir(exist_ok=True)
        targetenv=dict(env,GOOS='openharmony',GOARCH=arch,CGO_ENABLED='0')
        def build(args):
            cmd=list(map(str,[go,'build',*args]))
            log.write(repr(cmd)+'\n');log.flush()
            subprocess.run(cmd,env=targetenv,stdout=log,stderr=subprocess.STDOUT,check=True)
        binary=out/'smoke-pure'
        build(['-o',binary,ROOT/'tests/smoke/main.go'])
        data=binary.read_bytes()
        assert data[:4]==b'\x7fELF' and struct.unpack_from('<H',data,18)[0]=={'arm64':183,'arm':40,'amd64':62}[arch]
        if a.sdk:
            targetenv.update(CGO_ENABLED='1',OHOS_NDK_HOME=str(a.sdk.resolve()),
                CC=compiler_path(a.toolchain/'ohos-scripts'/('cc-'+arch+exe)),
                CXX=compiler_path(a.toolchain/'ohos-scripts'/('cxx-'+arch+exe)),
                AR=str(a.sdk.resolve()/'llvm/bin'/('llvm-ar'+exe)))
            build(['-o',out/'smoke',ROOT/'tests/smoke/main.go'])
            build(['-buildmode=c-shared','-o',out/'libanswer.so',ROOT/'tests/shared/main.go'])
            build(['-buildmode=c-archive','-o',out/'libanswer.a',ROOT/'tests/shared/main.go'])
            assert (out/'libanswer.a').read_bytes()[:8]==b'!<arch>\n'
        results.append(dict(target='openharmony/'+arch,result='build-pass',cgo=bool(a.sdk),
            pure_sha256=hashlib.sha256(data).hexdigest()))
        print('HOST_CROSS_PASS','/'.join(host),arch,flush=True)
report=dict(host='/'.join(host),version=version,patch_sha256=info['patch_sha256'],
    go_binary_sha256=hashlib.sha256(go.read_bytes()).hexdigest(),results=results)
(a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
