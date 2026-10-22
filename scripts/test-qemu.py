#!/usr/bin/env python3
"""Provision, start and collect the complete Go dist test in a private OHOS QEMU.

Boot first with qemu.py. Native Zig, SDK and binary-sign-tool are explicit test
inputs, not redistributed inside Go archives. No user-mode QEMU is used.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
LOCK=json.loads((ROOT/'manifest.json').read_text())
GUEST = '/data/local/tmp/go-patch'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['arm64', 'armv7a', 'x86_64'], required=True)
p.add_argument('--work', type=Path, default=ROOT / '.work/qemu')
p.add_argument('--run-id')
sub = p.add_subparsers(dest='command', required=True)
provision = sub.add_parser('provision')
provision.add_argument('--sdk', type=Path, required=True)
provision.add_argument('--zig', type=Path, required=True, help='native OHOS Zig prefix')
provision.add_argument('--signer', type=Path, required=True, help='native binary-sign-tool')
provision.add_argument('--go', type=Path, default=ROOT / '.work/upstream/go/bin/go', help='patched host Go')
provision.add_argument('--archive', type=Path, help='native Go release tar.gz')
update_go=sub.add_parser('update-go',help='replace only Go, retaining the already provisioned SDK/compiler fixtures')
update_go.add_argument('--archive',type=Path,help='native Go release tar.gz')
start = sub.add_parser('start')
start.add_argument('--cgo', choices=['0', '1'], default='1')
start.add_argument('--scope', choices=['full', 'stdlib-tools'], default='full')
start.add_argument('--min-free-gib', type=int, default=8, help='minimum free /data space before starting a full native suite')
sub.add_parser('status')
collect = sub.add_parser('collect')
collect.add_argument('--output', type=Path, default=ROOT / '.work/logs/qemu')
a = p.parse_args()
arch = {'arm64': 'arm64', 'armv7a': 'arm', 'x86_64': 'amd64'}[a.arch]
run_id = a.run_id or arch + '-cgo1'
if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in run_id):
    p.error('run-id must use letters, digits, hyphens or underscores')

def qemu(command, *args, capture=False):
    cmd = ['python3', ROOT / 'scripts/qemu.py', '--arch', a.arch, '--work', a.work, command, *args]
    return subprocess.check_output(list(map(str, cmd)), text=True) if capture else subprocess.run(list(map(str, cmd)), check=True)

def shell(s, timeout=120):
    return qemu('shell', s, '--timeout', timeout, capture=True)

if a.command == 'provision':
    if 'yes' in shell('(test -d ' + GUEST + '/test-running || test -d ' + GUEST + '/language-running) && echo yes; true'):
        raise SystemExit('refusing to replace sources during an active suite')
    archive = a.archive or ROOT / ('dist/'+LOCK['go']['version']+'.openharmony-' + arch + '.tar.gz')
    expected = archive.with_suffix(archive.suffix + '.sha256').read_text().split()[0]
    if hashlib.file_digest(open(archive, 'rb'), 'sha256').hexdigest() != expected:
        raise SystemExit('Go archive checksum mismatch')
    work = ROOT / '.work/qemu-support' / a.arch
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GOOS='openharmony', GOARCH=arch, GOARM='7', CGO_ENABLED='0',
               GOTOOLCHAIN='local', GOCACHE=str(ROOT / '.work/gocache'))
    for src, dst in [('native-cc', 'cc'), ('native-runner', 'native-runner')]:
        subprocess.run([str(a.go.resolve()), 'build', '-o', str(work / dst),
                        str(ROOT / 'tests' / src / 'main.go')], env=env, check=True)
    triple = {'arm64': 'aarch64-linux-ohos', 'arm': 'arm-linux-ohos', 'amd64': 'x86_64-linux-ohos'}[arch]
    payload = work / 'support.tar.gz'
    with tarfile.open(payload, 'w:gz', format=tarfile.GNU_FORMAT) as tar:
        tar.add(a.zig, arcname='native-zig')
        for path in ['sysroot/usr/include', 'sysroot/usr/lib/' + triple,
                     'llvm/include/libcxx-ohos', 'llvm/lib/' + triple,
                     'llvm/lib/clang/15.0.4/lib/' + triple]:
            tar.add(a.sdk / path, arcname='sdk/' + path)
        tar.add(a.signer, arcname='bin/binary-sign-tool')
        tar.add(work / 'cc', arcname='bin/cc')
        tar.add(work / 'cc', arcname='bin/cxx')
        tar.add(work / 'native-runner', arcname='bin/native-runner')
        tar.add(ROOT / 'tests/run-native.sh', arcname='run-native.sh')
        tar.add(ROOT / 'scripts/sign-installed.sh', arcname='sign-installed.sh')
        script = work / 'ar'
        script.write_text('#!/system/bin/sh\nexport ZIG_GLOBAL_CACHE_DIR=' + GUEST + '/zig-global\nexec ' + GUEST + '/native-zig/zig ar "$@"\n')
        script.chmod(0o755)
        tar.add(script, arcname='bin/ar')
    shell('mkdir -p ' + GUEST)
    qemu('send', archive, GUEST + '/go.tar.gz')
    qemu('send', payload, GUEST + '/support.tar.gz')
    print(shell('cd ' + GUEST + ' && rm -rf go && tar -xzf go.tar.gz && tar -xzf support.tar.gz && chmod 755 bin/* && export PATH=' + GUEST + '/bin:$PATH && sh sign-installed.sh '+GUEST+'/go && go/bin/go version', timeout=1200))
elif a.command == 'update-go':
    if 'yes' in shell('(test -d ' + GUEST + '/test-running || test -d ' + GUEST + '/language-running) && echo yes; true'):
        raise SystemExit('refusing to replace sources during an active suite')
    archive=a.archive or ROOT/('dist/'+LOCK['go']['version']+'.openharmony-'+arch+'.tar.gz')
    expected=archive.with_suffix(archive.suffix+'.sha256').read_text().split()[0]
    if hashlib.file_digest(open(archive,'rb'),'sha256').hexdigest()!=expected:
        raise SystemExit('Go archive checksum mismatch')
    with tarfile.open(archive) as tar:
        info=json.load(tar.extractfile('go/BUILD-INFO.json'))
        if info['target']['goos']!='openharmony' or info['target']['goarch']!=arch:
            raise SystemExit('Go archive target does not match guest')
    qemu('send',archive,GUEST+'/go.tar.gz')
    qemu('send',ROOT/'scripts/sign-installed.sh',GUEST+'/sign-installed.sh')
    qemu('send',ROOT/'tests/run-native.sh',GUEST+'/run-native.sh')
    print(shell('cd '+GUEST+' && rm -rf go && tar -xzf go.tar.gz && export PATH='+GUEST+'/bin:$PATH && sh sign-installed.sh '+GUEST+'/go && go/bin/go version',timeout=1200))
elif a.command == 'start':
    if a.min_free_gib < 0:
        p.error('--min-free-gib must be nonnegative')
    disk=shell('df -Pk '+GUEST).splitlines()
    available_bytes=int(disk[-1].split()[3])*1024
    if available_bytes < a.min_free_gib*1024**3:
        raise SystemExit(f'not enough free space for a native suite: {available_bytes/1024**3:.1f} GiB available, {a.min_free_gib} GiB required. Preserve finished logs, then clean only this task GOCACHE after all native/language jobs have ended, or expand its private userdata image.')
    shell('test ! -d ' + GUEST + '/test-running && test ! -e ' + GUEST + '/results/' + run_id + '-dist.json')
    files=['bin/cc', 'bin/binary-sign-tool', 'bin/native-runner', 'native-zig/zig',
           'run-native.sh', 'go/bin/go', 'go.tar.gz']
    raw=shell('cat ' + GUEST + '/go/BUILD-INFO.json; echo __FIXTURES__; sha256sum ' + shlex.join([GUEST+'/'+x for x in files]))
    metadata, fingerprints=raw.split('__FIXTURES__',1)
    inputs=dict(run_id=run_id, scope=a.scope, cgo=a.cgo,
                free_data_bytes_at_start=available_bytes,
                go_build_info=json.loads(metadata),
                fixtures_sha256={line.split(None,1)[1]:line.split()[0]
                    for line in fingerprints.splitlines() if len(line.split())==2})
    path=ROOT/'.work/qemu-support'/a.arch/(run_id+'-inputs.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(inputs,indent=2)+'\n')
    shell('mkdir -p '+GUEST+'/results')
    qemu('send',path,GUEST+'/results/'+run_id+'-inputs.json')
    print(shell('cd ' + GUEST + ' && bin/native-runner ' + shlex.join([arch, a.cgo, run_id, a.scope])))
elif a.command == 'status':
    print(shell('tail -2 ' + GUEST + '/results/' + run_id + '-dist.json; cat ' + GUEST + '/results/' + run_id + '-status 2>/dev/null; true'))
else:
    output = a.output / a.arch / run_id
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ['dist.json', 'environment.txt', 'status']:
        qemu('recv', GUEST + '/results/' + run_id + '-' + suffix, output / suffix)
    counts, failures, build_failures = collections.Counter(), collections.defaultdict(list), []
    language_cases=0
    language_counts=collections.Counter()
    with open(output / 'dist.json') as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get('Action') in ('pass', 'fail', 'skip') and not event.get('Test'):
                counts[event['Action']] += 1
            if event.get('Action') == 'fail':
                failures[event.get('Package', '?')].append(event.get('Test', '<package>'))
            if event.get('Action') == 'build-fail':
                build_failures.append(event.get('ImportPath', '?'))
            if event.get('Package','').startswith('cmd/internal/testdir') and event.get('Test','').startswith('Test/'):
                if event.get('Action')=='run':language_cases+=1
                if event.get('Action') in ('pass','fail','skip'):language_counts[event['Action']]+=1
    status = int((output / 'status').read_text().strip())
    report = dict(arch=arch, run_id=run_id, exit_status=status, packages=counts,
                  failures=failures, build_failures=build_failures,
                  log_sha256=hashlib.file_digest(open(output / 'dist.json', 'rb'), 'sha256').hexdigest())
    report['qemu'] = json.loads((a.work / a.arch / 'state.json').read_text())
    report['inputs']=json.loads(shell('if test -f '+GUEST+'/results/'+run_id+'-inputs.json; then cat '+GUEST+'/results/'+run_id+'-inputs.json; else echo null; fi'))
    scope=(report['inputs'] or {}).get('scope','legacy-unrecorded')
    source=ROOT/'.work/upstream/go'
    driver=(source/'src/cmd/internal/testdir/testdir_test.go').read_text()
    dirs=re.findall(r'"([^"]+)"',re.search(r'dirs = \[\]string\{([^}]+)\}',driver).group(1))
    expected_cases=sum(1 for d in dirs for f in (source/'test'/d).glob('*.go') if not f.name.startswith('.'))
    report.update(scope=scope,language_cases=language_cases,language_tests=language_counts,expected_language_cases=expected_cases)
    report['accepted']=status==0 and not failures and not build_failures and (scope=='stdlib-tools' or scope=='full' and language_cases==expected_cases)
    profile = a.work / a.arch / 'profile.json'
    if profile.exists() and report['qemu'].get('profile') == 'posix':
        report['qemu_profile'] = json.loads(profile.read_text())
    (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['accepted'] else 1)
