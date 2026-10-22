#!/usr/bin/env python3
"""Verify native signing boundaries in full OHOS QEMU guests, then merge evidence."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
GUEST = '/data/local/tmp/go-patch'
ARCHES = {'arm64': 'arm64', 'arm': 'armv7a', 'amd64': 'x86_64'}
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--hosts', default=','.join(ARCHES), help='native hosts to test sequentially')
p.add_argument('--work', type=Path, default=ROOT / '.work/qemu')
p.add_argument('--run-id', default=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
a = p.parse_args()
hosts = a.hosts.split(',')
if not hosts or len(set(hosts)) != len(hosts) or any(host not in ARCHES for host in hosts):
    p.error('hosts must be a unique subset of arm64,arm,amd64')
if not a.run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in a.run_id):
    p.error('run-id must use letters, digits, hyphens or underscores')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(host, *args):
    return list(map(str, ['python3', ROOT / 'scripts/qemu.py', '--arch', ARCHES[host],
                         '--work', a.work, *args]))


def qemu(host, *args):
    return subprocess.check_output(command(host, *args), text=True)


lock = json.loads((ROOT / 'manifest.json').read_text())
patch_sha = sha(ROOT / 'patch' / lock['patch']['filename'])
script = ROOT / 'tests/signing-boundary.sh'
reports = ROOT / 'docs/test-results'
reports.mkdir(parents=True, exist_ok=True)
logs = ROOT / '.work/logs/signing-boundary'
logs.mkdir(parents=True, exist_ok=True)
for host in hosts:
    busy = qemu(host, 'shell', '(test -d ' + GUEST + '/test-running || test -d ' +
                GUEST + '/language-running) && echo busy; true')
    if 'busy' in busy:
        raise SystemExit('wait for active native/language suite before signing tests: ' + host)
    metadata = qemu(host, 'shell', 'cat ' + GUEST + '/go/BUILD-INFO.json; echo __GO_BIN__; sha256sum ' + GUEST + '/go/bin/go')
    info, fingerprint = metadata.split('__GO_BIN__', 1)
    info = json.loads(info)
    assert info['target']['goarch'] == host and info['target']['goos'] == 'openharmony'
    assert info['patch_sha256'] == patch_sha and info['upstream'] == lock['go']['tag']
    log = logs / (host + '-' + a.run_id + '.log')
    if log.exists():
        raise SystemExit('refusing to overwrite an earlier attempt: ' + str(log))
    qemu(host, 'send', script, GUEST + '/signing-boundary.sh')
    result = subprocess.run(command(host, 'shell', 'GOMAXPROCS=2 GO_OHOS_SIGNING_RUN_ID='+a.run_id+' sh ' + GUEST +
                            '/signing-boundary.sh', '--timeout', '7200'), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_text(result.stdout)
    result.check_returncode()
    assert 'NATIVE_SIGNING_BOUNDARY_PASS' in result.stdout and 'SIGN_BOUNDARY_OK' in result.stdout
    report = dict(arch=host, go_version=lock['go']['version'], patch_sha256=patch_sha,
                  script_sha256=sha(script), accepted=True,
                  linux_build_without_signer=True, ohos_build_without_signer_rejected=True,
                  ohos_signed_build_direct_execution=True, go_binary_sha256=fingerprint.split()[0],
                  log_sha256=sha(log), log_path=log.relative_to(ROOT).as_posix())
    (reports / ('signing-boundary-' + host + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print('SIGNING_BOUNDARY_PASS', host, flush=True)

paths = [reports / ('signing-boundary-' + host + '.json') for host in ARCHES]
if all(path.is_file() and json.loads(path.read_text()).get('patch_sha256') == patch_sha
       and json.loads(path.read_text()).get('script_sha256') == sha(script) for path in paths):
    rows = [json.loads(path.read_text()) for path in paths]
    assert all(row['accepted'] and row['patch_sha256'] == patch_sha and
               row['script_sha256'] == sha(script) and row['go_version'] == lock['go']['version']
               for row in rows), 'incomplete or stale signing evidence; test remaining hosts'
    report = dict(go_version=lock['go']['version'], patch_sha256=patch_sha,
                  script_sha256=sha(script), accepted=True, targets=rows)
    (reports / 'signing-boundary.json').write_text(json.dumps(report, indent=2) + '\n')
    print('All three native signing boundaries passed.')
