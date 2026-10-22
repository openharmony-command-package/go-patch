#!/usr/bin/env python3
"""go_GOOS_GOARCH_exec for official cross-driven language tests in real OHOS.

Compilation runs on the host; every target executable is deployed, signed and
executed in its architecture's full-system guest. Binary output/exit status are
preserved. This explicit deployment signature is separate from Go auto-signing.
"""
import argparse
import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shlex
import signal
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('go_patch_qemu',ROOT/'scripts/qemu.py')
q=importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch',choices=['arm64','armv7a','x86_64'],required=True)
p.add_argument('--work',type=Path,default=ROOT/'.work/qemu')
p.add_argument('--guest-goroot',default='/data/local/tmp/go-patch/language-goroot')
p.add_argument('--timeout',type=int,default=7200,help='target execution timeout in seconds, including slow TCG stress cases')
p.add_argument('program',type=Path)
p.add_argument('args',nargs=argparse.REMAINDER)
a=p.parse_args()
a.work=a.work.resolve()
q.load(a)
program=a.program.resolve()
root='/data/local/tmp/go-patch'
job=root+'/language-exec/'+uuid.uuid4().hex
cwd=Path.cwd().resolve()
goroot=Path(os.environ['GOROOT']).resolve()
arch={'arm64':'arm64','armv7a':'arm','x86_64':'amd64'}[a.arch]
remote_cwd=a.guest_goroot+'/'+str(cwd.relative_to(goroot)) if cwd.is_relative_to(goroot) else job+'/cwd'
remote_program=(remote_cwd if program.parent==cwd and not cwd.is_relative_to(goroot) else job)+'/'+program.name
interrupted=False
cleaned=False
started=time.monotonic()

def quote(s):return shlex.quote(str(s))
def shell(s,timeout=120):return q.shell(a,s,timeout=timeout)
def send(src,dst):q.hdc(a,'file','send',str(src),dst,timeout=300)
def receive(src,dst):q.hdc(a,'file','recv',src,str(dst),timeout=300)

def stop_remote():
    # setsid gives each target its own process group. Check the executable's
    # private job path before terminating that group, including on timeout.
    script='if test -f '+quote(job+'/pid')+'; then p=$(cat '+quote(job+'/pid')+'); case "$p" in ""|*[!0-9]*) exit 1;; esac; case "$(readlink /proc/$p/exe 2>/dev/null)" in '+quote(job+'/')+'*) kill -TERM -"$p";; esac; fi'
    shell(script,timeout=15)

def stop(signum,frame):
    global interrupted
    interrupted=True
    try:
        stop_remote()
    except Exception:pass
    raise SystemExit(128+signum)

signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
try:
    binary=program.read_bytes()
    if binary[:4]!=b'\x7fELF' or struct.unpack_from('<H',binary,18)[0]!={'arm64':183,'armv7a':40,'x86_64':62}[a.arch]:
        raise RuntimeError('target executable has the wrong architecture: '+str(program))
    with tempfile.TemporaryDirectory(prefix='go-qemu-exec-') as tmp:
        tmp=Path(tmp)
        archive=tmp/'payload.tar.gz'
        total=0
        with tarfile.open(archive,'w:gz',format=tarfile.GNU_FORMAT) as tar:
            tar.add(program,arcname=str(Path(remote_program).relative_to(job)))
            if not cwd.is_relative_to(goroot):
                for f in sorted(cwd.rglob('*')):
                    if f==program or f.suffix in ('.o','.a') or not f.is_file():continue
                    total+=f.stat().st_size
                    if total>128*1024*1024:raise RuntimeError('language test work directory exceeds 128MB')
                    tar.add(f,arcname='cwd/'+str(f.relative_to(cwd)),recursive=False)
            stdin=sys.stdin.buffer.read()
            inputfile='/dev/null'
            if stdin:
                (tmp/'stdin').write_bytes(stdin)
                tar.add(tmp/'stdin',arcname='stdin')
                inputfile=job+'/stdin'
        send(archive,job+'.tar.gz')
        # Preserve runtime knobs used by individual official test recipes.
        overrides={k:v for k,v in os.environ.items() if k in ['GODEBUG','GOTRACEBACK','GOMAXPROCS','GOGC','GOMEMLIMIT','GOEXPERIMENT'] or k.startswith('GO_TEST_')}
        overrides.update(GOROOT=a.guest_goroot,GOCACHE=root+'/go-cache',GOPATH=root+'/gopath',
            GOOS='openharmony',GOARCH=arch,GOARM='7',GOTOOLCHAIN='local',GOENV='off',CGO_ENABLED='1',
            CC=root+'/bin/cc',CXX=root+'/bin/cxx',AR=root+'/bin/ar',
            TMPDIR=job+'/tmp',PATH=root+'/bin:'+root+'/go/bin:/system/bin:/bin')
        if os.environ.get('STDLIB_IMPORTCFG'):
            overrides['STDLIB_IMPORTCFG']=root+'/language-stdlib/importcfg'
        args=[x.replace(str(goroot),a.guest_goroot).replace(str(cwd),remote_cwd) for x in a.args]
        command=shlex.join(['setsid','env',*[k+'='+v for k,v in overrides.items()],remote_program,*args])
        script='\n'.join([
            'set -e',
            'mkdir -p '+shlex.join([job,job+'/tmp',remote_cwd]),
            'cd '+quote(job)+' && tar -xzf '+quote(job+'.tar.gz'),
            quote(root+'/bin/binary-sign-tool')+' sign -inFile '+quote(remote_program)+' -outFile '+quote(remote_program)+' -selfSign 1 > '+quote(job+'/sign.log')+' 2>&1',
            'chmod 755 '+quote(remote_program),
            'cd '+quote(remote_cwd),
            'set +e',
            command+' < '+quote(inputfile)+' > '+quote(job+'/output')+' 2>&1 &',
            'p=$!; echo "$p" > '+quote(job+'/pid'),
            'wait "$p"; result=$?',
            'echo __LANGUAGE_DATA__',
            'base64 '+quote(job+'/output'),
            'echo "__LANGUAGE_EXIT__=$result"',
            'cd /; rm -rf '+shlex.join([job,job+'.tar.gz']),
        ])
        status=shell(script,timeout=a.timeout)
        match=re.search(r'__LANGUAGE_DATA__\r?\n([A-Za-z0-9+/=\s]*?)__LANGUAGE_EXIT__=(\d+)',status)
        if not match:raise RuntimeError('missing target exit status: '+status)
        cleaned=True
        sys.stdout.buffer.write(base64.b64decode(re.sub(r'\s','',match.group(1)),validate=True))
        sys.stdout.buffer.flush()
        result=int(match.group(2))
        audit_log=os.environ.get('GO_QEMU_EXEC_AUDIT_LOG')
        if audit_log:
            import json
            with open(audit_log,'a') as stream:
                stream.write(json.dumps(dict(arch=arch,program_sha256=hashlib.sha256(binary).hexdigest(),
                    exit_status=result,elapsed_seconds=time.monotonic()-started))+'\n')
except Exception as error:
    try:stop_remote()
    except Exception:pass
    error_log=os.environ.get('GO_QEMU_EXEC_ERROR_LOG')
    if error_log:
        import json
        record=json.dumps(dict(program=str(program),cwd=str(cwd),error=str(error)))+'\n'
        with open(error_log,'a') as stream:stream.write(record)
    raise
finally:
    if not interrupted and not cleaned:
        try:shell('rm -rf '+shlex.join([job,job+'.tar.gz']),timeout=30)
        except Exception:pass
raise SystemExit(result)
