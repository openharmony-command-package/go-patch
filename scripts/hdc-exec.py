#!/usr/bin/env python3
"""Noninteractive go test -exec runner for an explicitly selected OHOS device."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--hdc', default=os.environ.get('GO_OHOS_HDC') or shutil.which('hdc'))
p.add_argument('--target', default=os.environ.get('GO_OHOS_HDC_TARGET'))
p.add_argument('--server', default=os.environ.get('GO_OHOS_HDC_SERVER'))
p.add_argument('--remote-root', default='/data/local/tmp/go-patch-exec')
p.add_argument('--signer', default='binary-sign-tool', help='real signer on the device PATH or absolute device path')
p.add_argument('--guest-goroot', default=os.environ.get('GO_OHOS_GUEST_GOROOT'), help='optional already deployed native Go tree')
p.add_argument('--timeout', type=int, default=7200)
p.add_argument('program', type=Path)
p.add_argument('args', nargs=argparse.REMAINDER)
a = p.parse_args()
if not a.hdc or not a.target: p.error('--hdc and --target (or their environment variables) are required')
if not a.remote_root.startswith('/') or '\n' in a.remote_root: p.error('remote-root must be an absolute path')
program = a.program.resolve()
if program.read_bytes()[:4] != b'\x7fELF': p.error('program is not an ELF binary')
client = [a.hdc]+(['-s', a.server] if a.server else [])+['-t',a.target]
def hdc(*args, timeout=120):
    r = subprocess.run([*client,*map(str,args)],capture_output=True,timeout=timeout)
    text = (r.stdout+r.stderr).decode(errors='replace')
    if r.returncode or re.search(r'\[Fail\]|Device not found|E001005',text): raise RuntimeError(text)
    return text
job = a.remote_root.rstrip('/')+'/job-'+uuid.uuid4().hex
token = uuid.uuid4().hex
quote = shlex.quote
try:
    with tempfile.TemporaryDirectory(prefix='go-ohos-hdc-') as directory:
        temp = Path(directory)
        stdin = b'' if sys.stdin.isatty() else sys.stdin.buffer.read()
        (temp/'stdin').write_bytes(stdin)
        archive = temp/'payload.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            tar.add(program,arcname='program')
            tar.add(temp/'stdin',arcname='stdin')
            # Preserve ordinary package testdata while bounding accidental copies.
            total = 0
            cwd = Path.cwd()
            for path in sorted(cwd.rglob('*')):
                if not path.is_file() or path.resolve()==program or path.suffix in ['.o','.a']: continue
                total += path.stat().st_size
                if total > 128*1024**2: raise RuntimeError('working directory exceeds the 128 MiB transport limit')
                tar.add(path,arcname='cwd/'+str(path.relative_to(cwd)),recursive=False)
        hdc('shell','mkdir -p '+quote(job))
        hdc('file','send',archive,job+'/payload.tar.gz',timeout=1200)
        env = {k:v for k,v in os.environ.items() if k in ['GODEBUG','GOTRACEBACK','GOGC','GOMEMLIMIT','GOMAXPROCS','TZ','GO_OHOS_HILOG'] or k.startswith('GO_TEST_')}
        env['TMPDIR'] = job+'/tmp'
        if a.guest_goroot:
            env.update(GOROOT=a.guest_goroot,GOCACHE=job+'/cache',GOPATH=job+'/gopath',
                GOTOOLCHAIN='local',GOENV='off',PATH=str(Path(a.signer).parent)+':'+a.guest_goroot+'/bin:/system/bin:/bin')
        command = shlex.join(['setsid','env',*[k+'='+v for k,v in env.items()],job+'/program',*a.args])
        script = '\n'.join([
            'set -e','cd '+quote(job),'tar -xzf payload.tar.gz','mkdir -p cwd tmp',
            shlex.join([a.signer,'sign','-inFile',job+'/program','-outFile',job+'/program','-selfSign','1'])+' >sign.log 2>&1',
            'chmod 755 program','cd cwd','set +e',
            command+' <../stdin >../stdout 2>../stderr &','p=$!; echo "$p" >../pid','wait "$p"; result=$?',
            'echo '+token+'_STDOUT','base64 ../stdout','echo '+token+'_STDERR','base64 ../stderr',
            'echo "'+token+'_EXIT=$result"',
        ])
        output = hdc('shell',script,timeout=a.timeout)
        match = re.search(token+r'_STDOUT\r?\n([A-Za-z0-9+/=\s]*?)'+token+r'_STDERR\r?\n([A-Za-z0-9+/=\s]*?)'+token+r'_EXIT=(\d+)',output)
        if not match: raise RuntimeError('missing remote exit/stdio trailer: '+output[-4000:])
        for stream, data in [(sys.stdout.buffer,match[1]),(sys.stderr.buffer,match[2])]:
            stream.write(base64.b64decode(re.sub(r'\s','',data),validate=True)); stream.flush()
        code = int(match[3])
except BaseException as error:
    print('OHOS HDC runner: '+str(error),file=sys.stderr)
    code = 125
    # Only terminate a process whose command line belongs to this unique job.
    try:
        hdc('shell','p=$(cat '+quote(job+'/pid')+' 2>/dev/null); case "$p" in ""|*[!0-9]*) ;; *) if grep -aqF '+quote(job+'/program')+' /proc/$p/cmdline; then kill -KILL -$p; fi ;; esac')
    except Exception: pass
finally:
    try: hdc('shell','rm -rf '+quote(job))
    except Exception: pass
sys.exit(code)
