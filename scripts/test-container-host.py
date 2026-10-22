#!/usr/bin/env python3
"""Run a Linux release toolchain and build all three OHOS targets in Docker.

Transport uses standard input, avoiding host bind-mount execution dependencies.
The image needs only sh, tar and sha256sum. This checks pure Go; SDK cgo checks
require an SDK compiler that can run on the selected host.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tarfile
import uuid

ROOT=Path(__file__).resolve().parent.parent
lock=json.loads((ROOT/'manifest.json').read_text())
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch',choices=['arm64','amd64'],required=True)
p.add_argument('--image',required=True,help='existing Linux image matching --arch')
p.add_argument('--output',type=Path)
a=p.parse_args()
out=(a.output or ROOT/'.work/host-check'/('linux-'+a.arch)).resolve()
out.mkdir(parents=True,exist_ok=True)
archive=ROOT/'dist'/(lock['go']['version']+'.linux-'+a.arch+'.tar.gz')
def sha(path):
    with open(path,'rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert sha(archive)==archive.with_suffix('.gz.sha256').read_text().split()[0],'archive checksum mismatch'
with tarfile.open(archive) as tar:
    info=json.load(tar.extractfile('go/BUILD-INFO.json'))
    assert info['patch_sha256']==sha(ROOT/'patch'/lock['patch']['filename']),'stale archive'
transport=out/'input.tar'
with tarfile.open(transport,'w',format=tarfile.GNU_FORMAT) as tar:
    tar.add(archive,arcname='toolchain.tar.gz')
    tar.add(ROOT/'tests/smoke/main.go',arcname='main.go')
script='''set -eu
mkdir -p /tmp/go-patch-host
cd /tmp/go-patch-host
tar -xf -
tar -xzf toolchain.tar.gz
export GOROOT=$PWD/go PATH=$PWD/go/bin:$PATH GOTOOLCHAIN=local GOENV=off
export GOCACHE=$PWD/cache GOMAXPROCS=2 CGO_ENABLED=0 GOARM=7
mkdir results
trap 'test ! -f results/build.log || cat results/build.log >&2' EXIT
go version > results/version.txt
go env GOHOSTOS GOHOSTARCH > results/host.txt
sha256sum go/bin/go > results/go.sha256
for arch in arm64 arm amd64; do
    GOOS=openharmony GOARCH=$arch go build -o results/$arch main.go >> results/build.log 2>&1
    echo HOST_CROSS_PASS linux/$arch >&2
done
tar -cf - results
'''
name='go-patch-host-'+a.arch+'-'+uuid.uuid4().hex[:10]
try:
    with open(transport,'rb') as inp,open(out/'results.tar','wb') as result,open(out/'docker.log','w') as log:
        subprocess.run(['docker','run','--rm','--name',name,'--platform','linux/'+a.arch,
            '--cpus','2','--memory','2g','-i','--entrypoint','sh',a.image,'-ec',script],
            stdin=inp,stdout=result,stderr=log,check=True)
finally:
    subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
with tarfile.open(out/'results.tar') as tar:
    def read(name):return tar.extractfile('results/'+name).read()
    version=read('version.txt').decode().strip()
    host='/'.join(read('host.txt').decode().split())
    assert host=='linux/'+a.arch,host
    assert version=='go version '+lock['go']['version']+' '+host,version
    results=[]
    for arch,machine in [('arm64',183),('arm',40),('amd64',62)]:
        data=read(arch)
        assert data[:4]==b'\x7fELF' and struct.unpack_from('<H',data,18)[0]==machine,arch+' ELF mismatch'
        results.append(dict(target='openharmony/'+arch,result='build-pass',cgo=False,pure_sha256=hashlib.sha256(data).hexdigest()))
    report=dict(host=host,version=version,patch_sha256=info['patch_sha256'],
        archive_sha256=sha(archive),go_binary_sha256=read('go.sha256').decode().split()[0],results=results)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
