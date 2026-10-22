#!/usr/bin/env python3
"""Pinned Go source, patch, cross-toolchain and release package management."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
LOCK = json.loads((ROOT / 'manifest.json').read_text())
WORK = ROOT / '.work'
SOURCE = WORK / 'upstream/go'


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(cmd, *, cwd=None, env=None, log=None):
    print('+', ' '.join(map(str, cmd)), flush=True)
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        with open(log, 'w') as out:
            subprocess.run(list(map(str, cmd)), cwd=cwd, env=env, stdout=out,
                           stderr=subprocess.STDOUT, check=True)
    else:
        subprocess.run(list(map(str, cmd)), cwd=cwd, env=env, check=True)


def fetch(item):
    path = WORK / 'downloads' / item['filename']
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(path.suffix + '.partial')
        urllib.request.urlretrieve('https://go.dev/dl/' + item['filename'], tmp)
        tmp.replace(path)
    if digest(path) != item['sha256']:
        raise SystemExit('SHA256 mismatch: ' + str(path))
    return path


def unpack(path, parent):
    parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path) as archive:
        # Source archives are pinned, but still reject path traversal and links.
        for member in archive.getmembers():
            dest = (parent / member.name).resolve()
            if not dest.is_relative_to(parent.resolve()):
                raise SystemExit('unsafe archive path: ' + member.name)
            if member.issym() or member.islnk():
                raise SystemExit('unexpected archive link: ' + member.name)
        archive.extractall(parent)


def apply(source):
    source = source.resolve()
    version = (source / 'VERSION').read_text().splitlines()[0]
    if version not in [LOCK['go']['tag'], LOCK['go']['version']]:
        raise SystemExit('source VERSION does not match pinned release')
    patch = ROOT / 'patch' / LOCK['patch']['filename']
    expected = patch.with_suffix(patch.suffix + '.sha256').read_text().split()[0]
    if digest(patch) != expected:
        raise SystemExit('patch checksum mismatch')
    # Isolate git apply from a possible parent repository without changing source.
    with tempfile.TemporaryDirectory(prefix='go-patch-git-') as tmp:
        run(['git', 'init', '-q', tmp])
        cmd = ['git', '--git-dir=' + str(Path(tmp) / '.git'),
               '--work-tree=' + str(source), 'apply', '--whitespace=nowarn']
        if subprocess.run(cmd + ['--reverse', '--check', str(patch)], cwd=source,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            print('OHOS patch is already applied')
            return
        run(cmd + ['--check', patch], cwd=source)
        run(cmd + [patch], cwd=source)


def prepare(a):
    if not a.source.exists():
        a.source.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='go-source-', dir=a.source.parent) as tmp:
            unpack(fetch(LOCK['go']['source']), Path(tmp))
            shutil.move(str(Path(tmp) / 'go'), a.source)
    apply(a.source)
    hostos = {'Darwin': 'darwin', 'Linux': 'linux'}[platform.system()]
    hostarch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'amd64'}[platform.machine()]
    bootstrap = WORK / 'bootstrap/go'
    if not bootstrap.exists():
        item = next(f for f in LOCK['go']['bootstrap']
                    if f['os'] == hostos and f['arch'] == hostarch)
        unpack(fetch(item), bootstrap.parent)
    print('source:', a.source)
    print('bootstrap:', bootstrap)


def build(a):
    source = a.source.resolve()
    env = os.environ.copy()
    env.update(GOCACHE=str(WORK / 'gocache'), GOTOOLCHAIN='local', LC_ALL='C')
    env.pop('GOROOT', None)
    env['GOROOT_BOOTSTRAP'] = str(WORK / 'bootstrap/go')
    host = source / 'bin/go'
    if not a.skip_host:
        run(['bash', './make.bash'], cwd=source / 'src', env=env,
            log=WORK / 'logs/build-host.log')
    if not host.exists():
        raise SystemExit('build the native host toolchain first')
    hostpair = subprocess.check_output([host, 'env', 'GOHOSTOS', 'GOHOSTARCH'],
                                       env=env, text=True).split()
    hostpair = '_'.join(hostpair)
    targets = LOCK['hosts'] + LOCK['native']
    names = set(a.targets.split(',')) if a.targets != 'all' else {x['name'] for x in targets}
    unknown = names - {x['name'] for x in targets}
    if unknown:
        raise SystemExit('unknown targets: ' + ','.join(sorted(unknown)))
    for t in targets:
        if t['name'] not in names:
            continue
        prefix = WORK / 'products' / t['name'] / 'go'
        if prefix.exists():
            shutil.rmtree(prefix)
        prefix.mkdir(parents=True)
        for name in ['src', 'lib', 'api', 'doc', 'misc', 'test']:
            if (source / name).exists():
                shutil.copytree(source / name, prefix / name)
        for name in ['LICENSE', 'PATENTS', 'README.md', 'VERSION', 'go.env', 'SECURITY.md']:
            if (source / name).exists():
                shutil.copy2(source / name, prefix / name)
        tools = prefix / 'pkg/tool'
        tools.mkdir(parents=True)
        shutil.copytree(source / 'pkg/include', prefix / 'pkg/include')
        # The host compiler builds the target tools from this exact source tree.
        same_host = t['goos'] + '_' + t['goarch'] == hostpair
        if same_host:
            shutil.copytree(source / 'pkg/tool' / hostpair, tools / hostpair)
            shutil.copytree(source / 'bin', prefix / 'bin',
                            ignore=shutil.ignore_patterns('*_*'))
        else:
            (tools / hostpair).symlink_to(source / 'pkg/tool' / hostpair, target_is_directory=True)
        tenv = dict(env, GOROOT=str(prefix), GOOS=t['goos'], GOARCH=t['goarch'],
                    CGO_ENABLED='0', GOARM='7')
        if not same_host:
            run([host, 'install', 'std', 'cmd'], cwd=prefix / 'src', env=tenv,
                log=WORK / 'logs' / ('build-' + t['name'] + '.log'))
            (tools / hostpair).unlink()
            crossbin = prefix / 'bin' / (t['goos'] + '_' + t['goarch'])
            for exe in crossbin.iterdir():
                exe.rename(prefix / 'bin' / exe.name)
            crossbin.rmdir()
        shutil.copy2(ROOT / 'manifest.json', prefix / 'OHOS-MANIFEST.json')
        (prefix / 'ohos-scripts').mkdir()
        for script in ['cc.py', 'cc-arm64', 'cc-arm', 'cc-amd64', 'cxx-arm64', 'cxx-arm', 'cxx-amd64']:
            shutil.copy2(ROOT / 'scripts' / script, prefix / 'ohos-scripts' / script)
        # Native wrappers also work on Windows without Bash or Python, and
        # retain target flags when cmd/link probes CC as a single executable.
        suffix = '.exe' if t['goos'] == 'windows' else ''
        driver = prefix / 'ohos-scripts' / ('sdk-cc' + suffix)
        run([host, 'build', '-o', driver, ROOT / 'scripts/sdk-cc/main.go'],
            env=dict(tenv, GOROOT=str(source)), log=WORK / 'logs' / ('sdk-cc-' + t['name'] + '.log'))
        for kind in ['cc', 'cxx']:
            for arch in ['arm64', 'arm', 'amd64']:
                wrapper = prefix / 'ohos-scripts' / (kind + '-' + arch + suffix)
                if wrapper.exists():
                    wrapper.unlink()
                os.link(driver, wrapper)
        driver.unlink()
        # Keep the reusable port and its relative documentation links together.
        # A toolchain archive can then reproduce the port without this checkout.
        port = prefix / 'ohos-port'
        port.mkdir()
        for name in ['README.md', 'README.zh-CN.md', 'CONTRIBUTING.md',
                     'CONTRIBUTING.zh-CN.md', 'LICENSE', 'THIRD-PARTY-NOTICES.md', 'manifest.json']:
            shutil.copy2(ROOT / name, port / name)
        for name in ['docs', 'patch', 'scripts', 'tests']:
            shutil.copytree(ROOT / name, port / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (prefix / 'OHOS-README.md').write_text(
            '# Go OHOS toolchain\n\n'
            + LOCK['go']['version'] + ' / ' + t['name'] + '\n\n'
            'Supports openharmony/arm64, openharmony/arm (GOARM=7), and openharmony/amd64.\n\n'
            'See [the complete guide](ohos-port/README.md), '
            '[validation](ohos-port/docs/VALIDATION.md), and '
            '[issue audit](ohos-port/docs/ISSUES.md). '
            'Reusable patches, build scripts, and tests are in `ohos-port/`.\n\n'
            'SDK C/C++ wrappers are in `ohos-scripts/`. Native OHOS installation '
            'uses [sign-installed.sh](ohos-scripts/sign-installed.sh) with a real '
            '`binary-sign-tool`. Automatic output signing applies only when both '
            'the running Go host and the build target are OHOS.\n')
        shutil.copy2(ROOT / 'THIRD-PARTY-NOTICES.md', prefix / 'OHOS-NOTICES.md')
        shutil.copy2(ROOT / 'scripts/sign-installed.sh', prefix / 'ohos-scripts/sign-installed.sh')
        (prefix / 'BUILD-INFO.json').write_text(json.dumps({
            'target': t, 'upstream': LOCK['go']['tag'],
            'patch_sha256': digest(ROOT / 'patch' / LOCK['patch']['filename'])
        }, indent=2) + '\n')
        a.output.mkdir(parents=True, exist_ok=True)
        name = LOCK['go']['version'] + '.' + t['name']
        if t['goos'] == 'windows':
            archive = a.output / (name + '.zip')
            pending = archive.with_name(archive.name + '.partial')
            with zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED) as z:
                for f in sorted(prefix.rglob('*')):
                    if f.is_file():
                        z.write(f, f.relative_to(prefix.parent))
        else:
            archive = a.output / (name + '.tar.gz')
            pending = archive.with_name(archive.name + '.partial')
            with tarfile.open(pending, 'w:gz', compresslevel=6, format=tarfile.GNU_FORMAT) as tar:
                tar.add(prefix, arcname='go')
        pending.replace(archive)
        archive.with_suffix(archive.suffix + '.sha256').write_text(
            digest(archive) + '  ' + archive.name + '\n')
        print('packaged:', archive, flush=True)


def refresh(a):
    source = a.source.resolve()
    base = a.base
    if not base:
        # An upstream clone must compare to the release, never Go's root commit.
        for candidate in [LOCK['go']['commit'], LOCK['go']['tag']]:
            if subprocess.run(['git', '-C', source, 'cat-file', '-e', candidate + '^{commit}'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                base = candidate
                break
    if not base:
        raise SystemExit('refresh needs the pinned release commit/tag or --base for an archive baseline')
    # A temporary index includes additions without modifying the developer index.
    with tempfile.TemporaryDirectory(prefix='go-patch-index-') as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / 'index'))
        run(['git', '-C', source, 'read-tree', base], env=env)
        # Release source archives omit build-generated files. Export only
        # intentional port sources, never host configuration or tzdata blobs.
        paths = [p for p in (ROOT / 'patch/source-paths.txt').read_text().splitlines()
                 if p and not p.startswith('#')]
        run(['git', '-C', source, 'add', '-A', '--', *paths], env=env)
        data = subprocess.check_output(['git', '-C', source, 'diff', '--cached',
                                        '--binary', '--full-index', base], env=env)
    if not data:
        raise SystemExit('refusing to export an empty patch')
    patch = ROOT / 'patch' / LOCK['patch']['filename']
    patch.parent.mkdir(exist_ok=True)
    patch.write_bytes(data)
    patch.with_suffix(patch.suffix + '.sha256').write_text(digest(patch) + '  ' + patch.name + '\n')
    print('refreshed:', patch)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=SOURCE)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare')
    sub.add_parser('apply')
    r = sub.add_parser('refresh')
    r.add_argument('--base', help='pristine archive baseline commit, if not using an upstream clone')
    b = sub.add_parser('build')
    b.add_argument('--targets', default='all')
    b.add_argument('--skip-host', action='store_true')
    b.add_argument('--output', type=Path, default=ROOT / 'dist')
    a = p.parse_args()
    {'prepare': prepare, 'apply': lambda a: apply(a.source),
     'refresh': refresh, 'build': build}[a.command](a)


if __name__ == '__main__':
    main()
