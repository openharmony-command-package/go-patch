#!/usr/bin/env python3
"""Build all three OHOS targets with native OHOS Go and execute each output."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent.parent
LOCK = json.loads((ROOT / 'manifest.json').read_text())
ARCHES = {'arm64': 'arm64', 'arm': 'armv7a', 'amd64': 'x86_64'}
MACHINES = {'arm64': 183, 'arm': 40, 'amd64': 62}
GUEST = '/data/local/tmp/go-patch'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--hosts', default='arm64,arm,amd64', help='native Go hosts to build on')
p.add_argument('--work', type=Path, default=ROOT / '.work/qemu')
a = p.parse_args()
hosts = a.hosts.split(',')
if not hosts or len(set(hosts)) != len(hosts) or any(x not in ARCHES for x in hosts):
    p.error('hosts must be a unique subset of arm64,arm,amd64')


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def qemu(arch, command, *args):
    return subprocess.check_output(list(map(str, ['python3', ROOT / 'scripts/qemu.py',
        '--arch', ARCHES[arch], '--work', a.work, command, *args])), text=True)


patch_sha = sha(ROOT / 'patch' / LOCK['patch']['filename'])
script = ROOT / 'tests/native-targets.sh'
output = ROOT / '.work/logs/native-targets'
output.mkdir(parents=True, exist_ok=True)
for host in hosts:
    busy = qemu(host, 'shell', '(test -d ' + GUEST + '/test-running || test -d ' +
                GUEST + '/language-running) && echo busy; true')
    if 'busy' in busy:
        raise SystemExit('wait for active native/language suite before native target builds: ' + host)
    metadata = qemu(host, 'shell', 'cat ' + GUEST + '/go/BUILD-INFO.json; echo __GO_BIN__; sha256sum ' + GUEST + '/go/bin/go')
    info, fingerprint = metadata.split('__GO_BIN__', 1)
    info = json.loads(info)
    assert info['target']['goarch'] == host and info['target']['goos'] == 'openharmony'
    assert info['patch_sha256'] == patch_sha and info['upstream'] == LOCK['go']['tag']
    qemu(host, 'send', script, GUEST + '/native-targets.sh')
    build_log = qemu(host, 'shell', 'sh ' + GUEST + '/native-targets.sh', '--timeout', 7200)
    (output / ('build-' + host + '.log')).write_text(build_log)
    cases = []
    for target in ARCHES:
        assert 'NATIVE_BUILD_OK ' + host + ' ' + target in build_log
        name = 'from-' + host + '-to-' + target
        binary = ROOT / '.work/native-targets' / name
        binary.parent.mkdir(parents=True, exist_ok=True)
        qemu(host, 'recv', GUEST + '/native-targets/' + name, binary)
        with binary.open('rb') as f:
            header = f.read(20)
        assert header[:4] == b'\x7fELF' and header[5] == 1
        assert int.from_bytes(header[18:20], 'little') == MACHINES[target]
        destination = GUEST + '/native-targets-received/' + name
        qemu(target, 'shell', 'mkdir -p ' + GUEST + '/native-targets-received')
        qemu(target, 'send', binary, destination)
        # Preserve the signature produced by the native Go build. No deployment
        # signing is allowed here, including for foreign-architecture outputs.
        result = qemu(target, 'shell', 'chmod 755 ' + shlex.quote(destination) + ' && ' + shlex.quote(destination))
        assert result.strip() == 'NATIVE_TARGET_OK ' + target, result
        cases.append(dict(host=host, target=target, program_sha256=sha(binary),
                          output=result.strip(), exit_status=0))
    report = dict(host=host, go_version=LOCK['go']['version'], patch_sha256=patch_sha,
                  native_go_sha256=fingerprint.split()[0], script_sha256=sha(script),
                  deployment_resigned=False, accepted=True, cases=cases)
    (output / (host + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)

reports = [output / (host + '.json') for host in ARCHES]
if all(path.exists() for path in reports):
    matrix = [json.loads(path.read_text()) for path in reports]
    assert all(r['accepted'] and r['patch_sha256'] == patch_sha and r['script_sha256'] == sha(script) for r in matrix)
    cases = [c for report in matrix for c in report['cases']]
    assert {(c['host'], c['target']) for c in cases} == {(h, t) for h in ARCHES for t in ARCHES}
    report = dict(go_version=LOCK['go']['version'], patch_sha256=patch_sha,
                  accepted=True, deployment_resigned=False, hosts=matrix)
    (ROOT / 'docs/test-results/native-targets.json').write_text(json.dumps(report, indent=2) + '\n')
    print('All nine native OHOS host/target combinations passed.')
