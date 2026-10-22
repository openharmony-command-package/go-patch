#!/usr/bin/env python3
"""Build and verify OHOS system-service bridges in a private full-system QEMU."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tarfile
import uuid
import zoneinfo

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['arm64', 'armv7a', 'x86_64'], required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--go', type=Path, default=ROOT/'.work/upstream/go/bin/go')
p.add_argument('--work', type=Path, default=ROOT/'.work/qemu')
p.add_argument('--run-id', default='platform-r1')
a = p.parse_args()
arch = {'arm64':'arm64', 'armv7a':'arm', 'x86_64':'amd64'}[a.arch]
out = ROOT/'.work/logs/platform'/a.arch/a.run_id
out.mkdir(parents=True, exist_ok=False)
work = ROOT/'.work/platform'/a.arch/a.run_id
work.mkdir(parents=True, exist_ok=False)
sha = lambda f: hashlib.file_digest(open(f,'rb'),'sha256').hexdigest()
def failure(kind, error, traceback):
    path = out/'failure.json'
    if not path.exists():
        path.write_text(json.dumps(dict(accepted=False,phase='build/deployment',
            error=str(error),cases=globals().get('records',[])),indent=2)+'\n')
    sys.__excepthook__(kind,error,traceback)
sys.excepthook = failure
patch = ROOT/'patch'/json.loads((ROOT/'manifest.json').read_text())['patch']['filename']
patch_sha = sha(patch)
probe_env=dict(os.environ,GOENV='off',GOTOOLCHAIN='local',GOROOT=str(a.go.resolve().parent.parent))
source = Path(subprocess.check_output([str(a.go),'env','GOROOT'],text=True,env=probe_env).strip())
go_version=subprocess.check_output([str(a.go),'env','GOVERSION'],text=True,env=probe_env).strip()
compiler_version=subprocess.check_output([str(a.go),'tool','compile','-V'],text=True,env=probe_env).strip()
if compiler_version != 'compile version '+go_version:
    raise RuntimeError('host toolchain is rebuilding; wait for make.bash to finish before testing')
source_inputs = {name:sha(source/name) for name in
    (ROOT/'patch/source-paths.txt').read_text().splitlines()
    if name and not name.startswith('#') and (source/name).is_file()}
source_digest = hashlib.sha256(json.dumps(source_inputs,sort_keys=True).encode()).hexdigest()
fixture_inputs={str(path.relative_to(ROOT)):sha(path) for path in (ROOT/'tests/platform').iterdir() if path.is_file()}
env = dict(os.environ, GOOS='openharmony', GOARCH=arch, GOARM='7',
	GOROOT=str(source),
    GOTOOLCHAIN='local', GOCACHE=str(ROOT/'.work/gocache'),
    OHOS_NDK_HOME=str(a.sdk.resolve()), CC=str(ROOT/'scripts'/('cc-'+arch)))
def qemu(command, *args):
    return subprocess.check_output(list(map(str, ['python3',ROOT/'scripts/qemu.py',
        '--arch',a.arch,'--work',a.work,command,*args])), text=True)
def shell(s): return qemu('shell', s, '--timeout', 180)
def build(cmd, **kw):
    with open(out/'build.log','a') as log:
        subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,**kw)
for name, cgo, flags in [('pure','0',[]),('cgo','1',[]),('netgo','1',['-tags=netgo']),('pie','1',['-buildmode=pie']),('debug','1',['-gcflags=all=-N -l'])]:
    build([a.go,'build',*flags,'-o',work/name,ROOT/'tests/platform/main.go'],env=dict(env,CGO_ENABLED=cgo))
cc = [ROOT/'scripts'/('cc-'+arch)]
build([*cc,'-shared','-fPIC',ROOT/'tests/platform/socket-hook.c','-o',work/'socket-hook.so'],env=env)
build([*cc,'-I'+str(source/'src/runtime/cgo'),ROOT/'tests/platform/cgo-fatal.c',
       '-ldl','-o',work/'cgo-fatal'],env=env)
for name in ['pure','cgo','netgo','pie','debug']:
    data=(work/name).read_bytes()
    assert data[:4]==b'\x7fELF' and struct.unpack_from('<H',data,18)[0]=={'arm':40,'arm64':183,'amd64':62}[arch], name+' ELF architecture'
    if name=='pie': assert struct.unpack_from('<H',data,16)[0]==3,'PIE is not ET_DYN'
build([a.sdk/'llvm/bin/llvm-readelf','-h','-l','-d',*[work/name for name in ['pure','cgo','netgo','pie','debug']]])
files = ['pure','cgo','netgo','pie','debug','socket-hook.so','cgo-fatal']
payload = work/'payload.tar.gz'
with tarfile.open(payload,'w:gz') as tar:
    for name in files: tar.add(work/name,arcname=name)
guest = '/data/local/tmp/go-patch/platform-'+uuid.uuid4().hex
qemu('send',payload,guest+'.tar.gz')
nonce = uuid.uuid4().hex
records = []
def run(name, command, markers=()):
    output = shell(command)
    (out/(name+'.log')).write_text(output)
    for marker in markers:
        if marker not in output: raise RuntimeError(name+': missing '+marker)
    records.append(dict(test=name,result='pass',log_sha256=sha(out/(name+'.log'))))
try:
    shell('set -e\nmkdir '+shlex.quote(guest)+'\ncd '+shlex.quote(guest)+
        '\ntar -xzf '+shlex.quote(guest+'.tar.gz')+
        '\nfor f in '+shlex.join(files)+'; do /data/local/tmp/go-patch/bin/binary-sign-tool sign -inFile "$f" -outFile "$f" -selfSign 1 >/dev/null; done\nchmod 755 '+shlex.join(files))
    prefix = 'set -e\ncd '+shlex.quote(guest)+'\nunset TZ SSL_CERT_FILE SSL_CERT_DIR\nexport GO_OHOS_PLATFORM_RUN='+nonce+'\n'
    timezone = shell('param get persist.time.timezone').strip()
    expected_offset = int(datetime.datetime.now(zoneinfo.ZoneInfo(timezone)).utcoffset().total_seconds())
    for binary in ['pure','cgo','netgo','pie','debug']:
        run(binary+'-system',prefix+'./'+binary+' system',[
            'GO_OHOS_SYSTEM_CA_OK','GO_OHOS_LOCAL_ZONE_OK','GO_OHOS_HILOG_STDOUT'])
        line=next(line for line in (out/(binary+'-system.log')).read_text().splitlines() if line.startswith('GO_OHOS_LOCAL_ZONE_OK '))
        assert int(line.split()[-1])==expected_offset, binary+' default timezone differs from the system'
        run(binary+'-context',prefix+'./'+binary+' context',['GO_OHOS_CONTEXT_OK'])
        run(binary+'-network',prefix+'./'+binary+' network',['GO_OHOS_SOCKET_OK'])
    for binary in ['cgo','netgo','pie']:
        run(binary+'-hook',prefix+'LD_PRELOAD='+shlex.quote(guest+'/socket-hook.so')+' ./'+binary+' hook-denied',['GO_OHOS_SOCKET_HOOK_OK'])
    run('timezone-override',prefix+'TZ=UTC ./pure system UTC\nTZ=UTC ./cgo system UTC',['GO_OHOS_LOCAL_ZONE_OK UTC 0'])
    run('timezone-empty',prefix+"TZ='' ./pure system UTC\nTZ='' ./cgo system UTC",['GO_OHOS_LOCAL_ZONE_OK UTC 0'])
    run('stdio-closed',prefix+'./pure stdio-closed\necho GO_OHOS_STDIO_CLOSED_OK',['GO_OHOS_STDIO_CLOSED_OK'])
    for binary in ['pure','cgo']:
        run(binary+'-panic',prefix+'set +e\n./'+binary+' panic >panic.log 2>&1\nr=$?\ncat panic.log\ntest "$r" -ne 0', ['GO_OHOS_HILOG_PANIC'])
        run(binary+'-copy',prefix+'./'+binary+' copy',['GO_OHOS_COPY_WRITETO','GO_OHOS_COPY_READFROM'])
    run('cgo-fatal',prefix+'set +e\n./cgo-fatal >fatal.log 2>&1\nr=$?\ncat fatal.log\ntest "$r" -ne 0',['GO_OHOS_CGO_FATAL'])
    run('long',prefix+'./pure long',['GO_OHOS_LONG_OK'])
    run('disabled',prefix+'GO_OHOS_HILOG=0 ./pure quiet',['GO_OHOS_HILOG_DISABLED '+nonce])
    shell('hilog -x -T Go,GoPort > '+shlex.quote(guest+'/hilog.log'))
    qemu('recv',guest+'/hilog.log',out/'hilog.log')
    logs = (out/'hilog.log').read_text()
    for marker in ['GO_OHOS_HILOG_LOG','GO_OHOS_HILOG_SLOG','GO_OHOS_HILOG_STDOUT',
                   'GO_OHOS_HILOG_RUNTIME','GO_OHOS_HILOG_WRITER','GO_OHOS_HILOG_HANDLER',
                   'GO_OHOS_HILOG_PANIC','GO_OHOS_CGO_FATAL','GO_OHOS_LONG_START','GO_OHOS_LONG_END',
                   'GO_OHOS_COPY_WRITETO','GO_OHOS_COPY_READFROM','GO_OHOS_CLOSED_STDOUT','GO_OHOS_CLOSED_STDERR','GO_OHOS_CLOSED_RUNTIME']:
        if marker+' '+nonce not in logs: raise RuntimeError('HiLog missing '+marker)
    if 'GO_OHOS_HILOG_DISABLED '+nonce in logs: raise RuntimeError('disabled stdio was mirrored')
    assert patch_sha == sha(patch), 'patch changed during verification'
    report = dict(go_version=json.loads((ROOT/'manifest.json').read_text())['go']['version'],
        patch_sha256=patch_sha,arch=arch,accepted=True,cases=records,
        source_digest=source_digest,go_binary_sha256=sha(a.go),system_timezone=timezone,
        fixtures_sha256=fixture_inputs,
        binaries_sha256={name:sha(work/name) for name in files},
        hilog_sha256=sha(out/'hilog.log'),script_sha256=sha(Path(__file__)),
        scope='full-system QEMU shell; native app sandbox and physical network policies require application tests')
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
except BaseException as error:
    (out/'failure.json').write_text(json.dumps(dict(accepted=False,patch_sha256=patch_sha,error=str(error),cases=records),indent=2)+'\n')
    raise
finally:
    shell('rm -rf '+shlex.join([guest,guest+'.tar.gz']))
