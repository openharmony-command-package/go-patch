#!/usr/bin/env python3
"""Verify the nine local release archives, metadata and host executable formats."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--dist', type=Path, default=ROOT/'dist')
p.add_argument('--source',type=Path,default=ROOT/'.work/upstream/go',help='patched source used to build the archives')
p.add_argument('--require-validation',action='store_true',help='require complete QEMU, signing and native matrix evidence, and preserve tested toolchain bytes')
p.add_argument('--require-tested-toolchains',action='store_true',help='require complete QEMU and tested binary provenance; does not certify signing boundaries or the native target matrix')
a = p.parse_args()
lock = json.loads((ROOT/'manifest.json').read_text())
patch = ROOT/'patch'/lock['patch']['filename']
patchsha = hashlib.file_digest(open(patch,'rb'),'sha256').hexdigest()
tested_native={}
tested_hosts={}
if a.require_validation:
    reports=ROOT/'docs/test-results'
    for filename in ['summary.json','signing-boundary.json','native-targets.json']:
        if not (reports/filename).is_file():
            raise SystemExit('complete validation before final packaging: missing docs/test-results/'+filename)
        proof=json.loads((reports/filename).read_text())
        assert proof['accepted'] is True and proof['patch_sha256']==patchsha,filename+' incomplete or stale validation'
        assert proof['go_version']==lock['go']['version'],filename+' version mismatch'
    if lock['patch'].get('abi_revision',1)>=2:
        platform_script_sha=hashlib.sha256((ROOT/'scripts/test-platform.py').read_bytes()).hexdigest()
        paths=(ROOT/'patch/source-paths.txt').read_text().splitlines()
        source_inputs={name:hashlib.sha256((a.source/name).read_bytes()).hexdigest() for name in paths
            if name and not name.startswith('#') and (a.source/name).is_file()}
        source_digest=hashlib.sha256(json.dumps(source_inputs,sort_keys=True).encode()).hexdigest()
        for arch in ['arm64','arm','amd64']:
            proof=json.loads((reports/('platform-'+arch+'.json')).read_text())
            assert proof['accepted'] and proof['patch_sha256']==patchsha,'incomplete platform integration: '+arch
            assert proof['script_sha256']==platform_script_sha,'stale platform integration driver: '+arch
            assert proof['source_digest']==source_digest,'platform integration source mismatch: '+arch
            fixtures={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'tests/platform').iterdir() if path.is_file()}
            assert proof['fixtures_sha256']==fixtures,'platform test fixture mismatch: '+arch
            expected={binary+'-'+case for binary in ['pure','cgo','netgo','pie','debug'] for case in ['system','context','network']}
            expected.update(binary+'-hook' for binary in ['cgo','netgo','pie'])
            expected.update(['pure-panic','cgo-panic','pure-copy','cgo-copy','cgo-fatal','long','disabled','timezone-override','timezone-empty','stdio-closed'])
            assert {row['test'] for row in proof['cases'] if row['result']=='pass'}==expected,'incomplete platform cases: '+arch
if a.require_validation or a.require_tested_toolchains:
    reports=ROOT/'docs/test-results'
    proof=json.loads((reports/'tested-toolchains.json').read_text())
    assert proof['patch_sha256']==patchsha and proof['go_version']==lock['go']['version'],'tested toolchain provenance'
    tested_native={row['arch']:row for row in proof['native']}
    assert set(tested_native)=={'arm64','arm','amd64'},'missing tested native toolchain'
    validation=json.loads((reports/'summary.json').read_text())
    assert validation['accepted'] and validation['patch_sha256']==patchsha and validation['go_version']==lock['go']['version'],'incomplete or stale QEMU validation'
    assert {row['arch'] for row in validation['targets']}==set(tested_native),'incomplete QEMU matrix'
    for row in validation['targets']:
        assert tested_native[row['arch']]['archive_sha256']==row['tested_archive_sha256'],'native test/archive mismatch: '+row['arch']
if a.require_validation:
    native_hashes={row['arch']:row['signed_native_go_sha256'] for row in validation['targets']}
    signing=json.loads((reports/'signing-boundary.json').read_text())
    assert {row['arch'] for row in signing['targets']}==set(native_hashes),'incomplete signing matrix'
    for row in signing['targets']:
        assert row['accepted'] and row['go_binary_sha256']==native_hashes[row['arch']],'signing test/toolchain mismatch: '+row['arch']
    matrix=json.loads((reports/'native-targets.json').read_text())
    assert {row['host'] for row in matrix['hosts']}==set(native_hashes),'incomplete native host matrix'
    combinations=set()
    for row in matrix['hosts']:
        assert row['accepted'] and row['native_go_sha256']==native_hashes[row['host']],'native matrix/toolchain mismatch: '+row['host']
        combinations.update((case['host'],case['target']) for case in row['cases'] if case['exit_status']==0)
    assert combinations=={(h,t) for h in native_hashes for t in native_hashes},'missing native host/target execution'
if a.require_validation or a.require_tested_toolchains:
    for target in lock['hosts']:
        if target['goos']=='windows':
            continue  # Windows archives receive static format checks only.
        proof=json.loads((reports/('host-'+target['name']+'.json')).read_text())
        assert proof['patch_sha256']==patchsha,'stale host evidence: '+target['name']
        assert {row['target'] for row in proof['results'] if row['result']=='build-pass'}=={'openharmony/arm64','openharmony/arm','openharmony/amd64'},'incomplete host matrix: '+target['name']
        tested_hosts[target['name']]=proof['go_binary_sha256']
source=a.source.resolve()
port_sources=[p for p in (ROOT/'patch/source-paths.txt').read_text().splitlines() if p and not p.startswith('#')]
bundle_files=[ROOT/name for name in ['README.md','README.zh-CN.md','CONTRIBUTING.md',
                                   'CONTRIBUTING.zh-CN.md','LICENSE','THIRD-PARTY-NOTICES.md','manifest.json']]
bundle_directories=['docs','patch','scripts','tests']
if (ROOT/'mobile').is_dir():bundle_directories.append('mobile')
for directory in bundle_directories:
    bundle_files.extend(path for path in (ROOT/directory).rglob('*')
                        if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc')
results=[]
def check_format(data,target):
    arch=target['goarch']
    if target['goos']=='windows':
        assert data[:2]==b'MZ'
        offset=struct.unpack_from('<I',data,60)[0]
        assert data[offset:offset+4]==b'PE\0\0'
        assert struct.unpack_from('<H',data,offset+4)[0]=={'amd64':0x8664,'arm64':0xaa64}[arch]
    elif target['goos']=='darwin':
        assert data[:4]==b'\xcf\xfa\xed\xfe'
        assert struct.unpack_from('<I',data,4)[0]=={'amd64':0x1000007,'arm64':0x100000c}[arch]
    else:
        assert data[:4]==b'\x7fELF' and data[4]==(1 if arch=='arm' else 2) and data[5]==1
        assert struct.unpack_from('<H',data,18)[0]=={'amd64':62,'arm64':183,'arm':40}[arch]
for target in lock['hosts']+lock['native']:
    name = lock['go']['version']+'.'+target['name']+('.zip' if target['goos']=='windows' else '.tar.gz')
    archive=a.dist/name
    sha=hashlib.file_digest(open(archive,'rb'),'sha256').hexdigest()
    assert archive.with_suffix(archive.suffix+'.sha256').read_text().split()[0]==sha, name+' checksum'
    if name.endswith('.zip'):
        z=zipfile.ZipFile(archive)
        read=z.read
        names=set(z.namelist())
    else:
        z=tarfile.open(archive)
        def read(path):
            f=z.extractfile(path)
            assert f is not None,path
            return f.read()
        names={x.name for x in z.getmembers()}
    assert read('go/VERSION').splitlines()[0].decode()==lock['go']['version'], name+' version'
    info=json.loads(read('go/BUILD-INFO.json'))
    assert info['target']==target and info['patch_sha256']==patchsha,name+' patch provenance'
    assert json.loads(read('go/OHOS-MANIFEST.json'))==lock,name+' manifest'
    assert read('go/ohos-scripts/sign-installed.sh')==(ROOT/'scripts/sign-installed.sh').read_bytes(),name+' stale signature installer'
    for path in bundle_files:
        assert read('go/ohos-port/'+path.relative_to(ROOT).as_posix())==path.read_bytes(),name+' stale port bundle: '+str(path)
    assert b'ohos-port/README.md' in read('go/OHOS-README.md'),name+' missing standalone guide'
    assert len([n for n in names if n.startswith('go/test/') and n.endswith('.go')])>1000,name+' missing official language tests'
    for path in port_sources:
        expected=source/path
        if expected.exists():
            assert read('go/'+path)==expected.read_bytes(),name+' stale port source: '+path
        else:
            assert 'go/'+path not in names,name+' obsolete port source: '+path
    exe='.exe' if target['goos']=='windows' else ''
    data=read('go/bin/go'+exe)
    check_format(data,target)
    go_sha=hashlib.sha256(data).hexdigest()
    if target['name'] in tested_hosts:
        assert go_sha==tested_hosts[target['name']],name+' host Go differs from tested binary'
    if target['goos']=='openharmony' and tested_native:
        proof=tested_native[target['goarch']]
        assert proof['files_sha256'],name+' missing tested binaries'
        for path,expected in proof['files_sha256'].items():
            assert hashlib.sha256(read(path)).hexdigest()==expected,name+' differs from tested toolchain: '+path
    for arch in ['arm64','arm','amd64']:
        for kind in ['cc','cxx']:
            wrapper='go/ohos-scripts/'+kind+'-'+arch+exe
            assert wrapper in names,wrapper
            data=read(wrapper)
            check_format(data,target)
            if target['goos']=='openharmony' and tested_native:
                canonical=tested_native[target['goarch']]['files_sha256']['go/ohos-scripts/cc-amd64']
                assert hashlib.sha256(data).hexdigest()==canonical,name+' wrapper differs from tested binary: '+wrapper
    assert not any('/pkg/tool/darwin_arm64' in n for n in names) or target['name']=='darwin-arm64',name+' leaked bootstrap tools'
    z.close()
    results.append(dict(filename=name,sha256=sha,bytes=archive.stat().st_size,target=target['name'],go_binary_sha256=go_sha,result='archive-pass'))
    print('ARCHIVE_PASS',target['name'],flush=True)
report=dict(go_version=lock['go']['version'],patch_sha256=patchsha,
            release_status='validated' if a.require_validation else 'candidate',
            validation_required=a.require_validation,
            tested_toolchains_required=a.require_validation or a.require_tested_toolchains,archives=results)
(a.dist/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['filename']+'\n' for r in results))
(a.dist/'release-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
