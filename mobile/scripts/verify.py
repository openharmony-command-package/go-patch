#!/usr/bin/env python3
"""Verify nine gomobile archives and the three-ABI example HAR."""
import argparse,hashlib,json,pathlib,struct,tarfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];REPO=ROOT.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--dist',type=pathlib.Path,default=REPO/'dist/gomobile')
p.add_argument('--require-validation',action='store_true')
a=p.parse_args();lock=json.loads((ROOT/'manifest.json').read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
revision=sha((ROOT/'patch'/lock['patch']).read_bytes())
assert revision==(ROOT/'patch/mobile-ohos.patch.sha256').read_text().split()[0]
manifest=json.loads((a.dist/'manifest.json').read_text())
assert manifest['patch_sha256']==revision and manifest['upstream']==lock['upstream']
assert {r['target'] for r in manifest['archives']}==set(lock['targets'])
assert len(manifest['archives'])==len(lock['targets'])
def executable(data,target,shared=False):
 host,arch=target.split('-')
 if host in ['linux','openharmony']:
  assert data[:4]==b'\x7fELF' and data[5]==1,target
  assert data[4]==(1 if arch=='arm' else 2),target
  assert struct.unpack_from('<H',data,18)[0]=={'arm64':183,'arm':40,'amd64':62}[arch],target
  if shared:assert struct.unpack_from('<H',data,16)[0]==3
 elif host=='windows':
  assert data[:2]==b'MZ';offset=struct.unpack_from('<I',data,60)[0]
  assert data[offset:offset+4]==b'PE\0\0'
  assert struct.unpack_from('<H',data,offset+4)[0]=={'arm64':0xaa64,'amd64':0x8664}[arch]
 else:
  assert data[:4]==b'\xcf\xfa\xed\xfe'
  assert struct.unpack_from('<I',data,4)[0]=={'arm64':0x100000c,'amd64':0x1000007}[arch]
products={}
for row in manifest['archives']:
 f=a.dist/row['filename'];assert sha(f.read_bytes())==row['sha256']
 assert row['sha256']==f.with_suffix(f.suffix+'.sha256').read_text().split()[0]
 if f.suffix=='.zip':
  archive=zipfile.ZipFile(f);read=archive.read
 else:
  archive=tarfile.open(f);read=lambda name:archive.extractfile(name).read()
 with archive:
  info=json.loads(read('gomobile/BUILD-INFO.json'))
  assert info['patch_sha256']==revision and info['upstream']==lock['upstream'] and info['target']==row['target']
  assert info['go_version'].startswith('go version '+lock['go_version']+' ')
  assert len(info['go_patch_sha256'])==64 and len(info['build_go_sha256'])==64
  suffix='.exe' if row['target'].startswith('windows-') else ''
  for tool in ['gomobile','gobind']:
   data=read('gomobile/bin/'+tool+suffix);executable(data,row['target'])
   assert sha(data)==info['binaries_sha256'][tool]==row['binaries_sha256'][tool]
  for name in ['README.md','README.zh-CN.md','manifest.json','patch/mobile-ohos.patch','scripts/sign-installed.sh','scripts/test-ark.py','tests/ark/runtime.h']:
   assert read('gomobile/'+name)==(ROOT/name).read_bytes(),'stale packaged file: '+name
 products[row['target']]=info
bundle=manifest['port_bundle'];assert sha((a.dist/bundle['filename']).read_bytes())==bundle['sha256']
with tarfile.open(a.dist/bundle['filename']) as tar:
 assert tar.extractfile('gomobile-ohos-port/patch/mobile-ohos.patch').read()==(ROOT/'patch/mobile-ohos.patch').read_bytes()
 assert tar.extractfile('gomobile-ohos-port/scripts/manage.py').read()==(ROOT/'scripts/manage.py').read_bytes()
har=a.dist/'gomobile-ohos-example.har'
with tarfile.open(har) as archive:
 read=lambda name:archive.extractfile('package/'+name).read()
 info=json.loads(read('BUILD-INFO.json'))
 assert info['mobile_patch_revision']==revision
 assert info['go_patch_sha256']==products['darwin-arm64']['go_patch_sha256']
 assert set(info['architectures'])=={'arm64','arm','amd64'}
 libs={}
 for arch,abi in [('arm64','arm64-v8a'),('arm','armeabi-v7a'),('amd64','x86_64')]:
  data=read('libs/'+abi+'/libgomobile.so');executable(data,'openharmony-'+arch,True)
  libs[arch]=sha(data);assert libs[arch]==info['native_libraries_sha256'][abi]
 assert json.loads(read('src/main/module.json'))['module']['type']=='har'
 assert json.loads(read('oh-package.json5'))['main']=='Index.ts'
 for name in ['Index.ts','Index.d.ts','src/main/cpp/types/libgomobile/index.d.ts']:assert read(name)
if a.require_validation:
 evidence=ROOT/'docs/test-results'
 for arch in libs:
  r=json.loads((evidence/('ark-'+arch+'.json')).read_text())
  assert r['accepted'] and r['cases']==29 and r['mobile_patch_sha256']==revision
  assert r['har_sha256']==sha(har.read_bytes()) and r['native_library_sha256']==libs[arch]
  assert r['suite_sha256']==sha((ROOT/'tests/suite.js').read_bytes())
  assert r['runner_sha256']==sha((ROOT/'tests/ark/runner.cpp').read_bytes())
  assert r['compile_driver_sha256']==sha((ROOT/'tests/compile-ark.cjs').read_bytes())
  assert r['go_patch_sha256']==info['go_patch_sha256']
 r=json.loads((evidence/'host-node.json').read_text())
 assert r['accepted'] and r['cases']==27 and r['typescript_strict'] and r['patch_sha256']==revision
 assert r['gobind_binary_sha256']==products['darwin-arm64']['binaries_sha256']['gobind']
 assert r['suite_sha256']==sha((ROOT/'tests/node.cjs').read_bytes())
 for target in set(lock['targets'])-{'windows-arm64','windows-amd64'}:
  r=json.loads((evidence/('tools-'+target+'.json')).read_text())
  assert r['accepted'] and r['patch_sha256']==revision and r['binaries_sha256']==products[target]['binaries_sha256']
 r=json.loads((evidence/'hap-runtime.json').read_text())
 assert r['accepted'] and r['mobile_patch_sha256']==revision and r['har_sha256']==sha(har.read_bytes()),'HAP application execution remains unverified'
print(json.dumps(dict(archives=len(products),har_abis=len(libs),patch_sha256=revision,validation_required=a.require_validation),indent=2))
