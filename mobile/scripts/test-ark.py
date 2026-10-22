#!/usr/bin/env python3
"""Run generated HAR bindings in a real OHOS Ark VM, including environment cleanup.

This is a shell sandbox test, not HAP installation or application UID evidence.
The runner's pinned inner runtime API is deliberately confined to the harness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['arm64', 'arm', 'amd64'], required=True)
p.add_argument('--har', type=Path, required=True)
p.add_argument('--go', type=Path, required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--node', type=Path, required=True)
p.add_argument('--typescript', type=Path, required=True)
p.add_argument('--es2abc', type=Path, required=True)
p.add_argument('--qemu-work', type=Path, default=REPO / '.work/qemu')
p.add_argument('--output', type=Path)
p.add_argument('--run-id', default='current')
a = p.parse_args()
assert a.run_id and all(c.isalnum() or c in '-_' for c in a.run_id)
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
qarch = {'arm64': 'arm64', 'arm': 'armv7a', 'amd64': 'x86_64'}[a.arch]
abi = {'arm64': 'arm64-v8a', 'arm': 'armeabi-v7a', 'amd64': 'x86_64'}[a.arch]
work = REPO / '.work/mobile-ark' / a.run_id / a.arch
work.mkdir(parents=True, exist_ok=True)
guest = '/data/local/tmp/go-patch/mobile-ark-' + a.run_id + '-' + a.arch
output = a.output or work / 'summary.json'
report = dict(accepted=False, arch=a.arch, run_id=a.run_id,
              scope='OHOS Ark N-API shell sandbox, two runtime environments',
              hap_installation=False, application_private_directory_test=False,
              har_sha256=sha(a.har), runner_sha256=sha(ROOT/'tests/ark/runner.cpp'),
              suite_sha256=sha(ROOT/'tests/suite.js'),
              compile_driver_sha256=sha(ROOT/'tests/compile-ark.cjs'),
              harness_header=json.loads((ROOT/'tests/ark/runtime-header-pin.json').read_text()),
              started_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
log = open(work/'raw.log', 'w')
def run(cmd, **kw):
    log.write('$ ' + shlex.join(map(str, cmd)) + '\n'); log.flush()
    r = subprocess.run(list(map(str, cmd)), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, **kw)
    log.write(r.stdout); log.flush()
    r.check_returncode()
    return r.stdout
def qemu(*args, **kw):
    return run(['python3', REPO/'scripts/qemu.py', '--arch', qarch,
                '--work', a.qemu_work, *args], **kw)
try:
    with tarfile.open(a.har) as tar:
        tar.extractall(work, filter='data')
    package = work/'package'
    info = json.loads((package/'BUILD-INFO.json').read_text())
    patch = ROOT/'patch/mobile-ohos.patch'
    assert info['mobile_patch_revision'] == sha(patch), 'HAR mobile revision differs from current patch'
    assert info.get('go_patch_sha256', 'unrecorded') != 'unrecorded', 'HAR has no Go patch provenance'
    library = package/'libs'/abi/'libgomobile.so'
    assert sha(library) == info['native_libraries_sha256'][abi]
    report.update(mobile_patch_sha256=sha(patch), go_patch_sha256=info['go_patch_sha256'],
                  native_library_sha256=sha(library), go_executable_sha256=info['go_executable_sha256'])
    env = dict(os.environ, OHOS_NDK_HOME=str(a.sdk.resolve()))
    goroot = Path(run([a.go.resolve(), 'env', 'GOROOT'], env=env).strip())
    runner = work/'runner'
    run([goroot/'ohos-scripts'/('cxx-'+a.arch), '-I', ROOT/'tests/ark',
         ROOT/'tests/ark/runner.cpp', '-o', runner, '-lace_napi.z', '-ldl'], env=env)
    run([a.node, ROOT/'tests/compile-ark.cjs', a.typescript.resolve(),
         package, ROOT/'tests/suite.js', guest, work/'test.js'])
    run([a.es2abc, '--target-api-version', '12', '--output', work/'test.abc', work/'test.js'])
    qemu('shell', 'mkdir -p ' + shlex.quote(guest) + '/files ' + shlex.quote(guest) + '/cache ' + shlex.quote(guest) + '/tmp')
    for local, name in [(runner,'runner'),(library,'libgomobile.so'),(work/'test.abc','test.abc')]:
        qemu('send',local,guest+'/'+name)
    script = 'set -e\ncd '+shlex.quote(guest)+'\n'
    for name in ['runner','libgomobile.so']:
        script += '/data/local/tmp/go-patch/bin/binary-sign-tool sign -inFile '+name+' -outFile '+name+' -selfSign 1\n'
    script += 'chmod 755 runner\n./runner ./libgomobile.so '+shlex.quote(guest+'/test.abc')
    text = qemu('shell', script, '--timeout', '720', timeout=750)
    rows = [json.loads(line.split('GOMOBILE_ARK_REPORT ',1)[1]) for line in text.splitlines() if line.startswith('GOMOBILE_ARK_REPORT ')]
    assert len(rows) == 2 and [r['round'] for r in rows] == [1,2], 'missing runtime reports'
    assert [r['cases'] for r in rows] == [27,2] and all(r['accepted'] for r in rows), rows
    file_content = qemu('shell','cat '+shlex.quote(guest+'/files/go-context.txt')).strip()
    assert file_content == 'GOMOBILE_CONTEXT_WRITE_OK', 'Go did not write into the Context files directory'
    report.update(accepted=True, runtime_reports=rows, cases=sum(r['cases'] for r in rows),
                  runner_binary_sha256=sha(runner), bytecode_sha256=sha(work/'test.abc'))
except Exception as error:
    report['error'] = str(error)
    raise
finally:
    log.close()
    report['raw_log_sha256'] = sha(work/'raw.log')
    report['finished_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
