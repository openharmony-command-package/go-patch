#!/usr/bin/env python3
"""Require complete, matching OHOS runtime-test evidence for all three targets."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__)
for arch in ['arm64','arm','amd64']:
    p.add_argument('--'+arch,type=Path,required=True,help='native dist summary.json')
for arch in ['arm','amd64']:
    p.add_argument('--'+arch+'-language',type=Path,help='cross-language summary.json when native scope is stdlib-tools')
p.add_argument('--output',type=Path,default=ROOT/'docs/test-results/summary.json')
a=p.parse_args()
lock=json.loads((ROOT/'manifest.json').read_text())
def sha(path):
    with open(path,'rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
patch_sha=sha(ROOT/'patch'/lock['patch']['filename'])
results=[]
for arch,qarch in [('arm64','arm64'),('arm','armv7a'),('amd64','x86_64')]:
    path=getattr(a,arch).resolve()
    native=json.loads(path.read_text())
    assert native['arch']==arch and native['accepted'] is True,arch+' native suite not accepted'
    assert native['exit_status']==0 and not native['failures'] and not native['build_failures'],arch+' native failures'
    inputs=native['inputs']
    assert inputs['cgo']=='1' and inputs['scope']==native['scope'],arch+' incomplete native scope'
    info=inputs['go_build_info']
    assert info['patch_sha256']==patch_sha and info['upstream']==lock['go']['tag'],arch+' source mismatch'
    assert info['target']['goos']=='openharmony' and info['target']['goarch']==arch,arch+' target mismatch'
    assert sha(path.parent/'dist.json')==native['log_sha256'],arch+' native log checksum'
    image=next(x for x in lock['qemu']['targets'] if x['name']==qarch)
    assert native['qemu']['archive_sha256']==image['sha256'],arch+' QEMU image mismatch'
    profile=native['qemu'].get('profile')
    profile_evidence=None
    if profile is None:
        # Early ARM64 collection predated the explicit profile field. Require
        # a separate comparison of its retained read-only images to the pin.
        evidence=path.parent/'stock-image-verification.json'
        proof=json.loads(evidence.read_text())
        assert proof['arch']==qarch and proof['profile']=='stock',arch+' missing profile provenance'
        assert proof['archive_sha256']==image['sha256'],arch+' profile archive mismatch'
        checks=proof['read_only_images']
        assert checks and any(x['file'].endswith('/system.img') for x in checks),arch+' missing system image proof'
        assert all(x['match'] and x['archive_sha256']==x['local_sha256'] for x in checks),arch+' modified stock image'
        assert all(x['match'] or x.get('metadata_only') is True for x in proof['product_partitions']),arch+' product image content changed'
        profile='stock'
        profile_evidence=sha(evidence)
    item=dict(arch=arch,native_run=native['run_id'],packages=native['packages'],
              native_log_sha256=native['log_sha256'],qemu_profile=profile,
              tested_archive_sha256=inputs['fixtures_sha256']['/data/local/tmp/go-patch/go.tar.gz'],
              signed_native_go_sha256=inputs['fixtures_sha256']['/data/local/tmp/go-patch/go/bin/go'])
    if profile_evidence:
        item['stock_image_evidence_sha256']=profile_evidence
    if profile=='posix':
        assert native.get('qemu_profile'),arch+' missing modified-image provenance'
    if native['scope']=='full':
        assert native['language_cases']==native['expected_language_cases']>1000,arch+' missing native language tests'
        item.update(language_cases=native['language_cases'],language_tests=native['language_tests'],method='native full dist')
    else:
        assert native['scope']=='stdlib-tools' and native['language_cases']==0,arch+' unexpected native filter'
        langpath=getattr(a,arch+'_language')
        assert langpath is not None,arch+' missing separate language evidence'
        langpath=langpath.resolve()
        language=json.loads(langpath.read_text())
        assert language['arch']==arch and language['accepted'] is True,arch+' language suite not accepted'
        assert language['diagnostic_filter'] is None and language['inputs_unchanged'] is True,arch+' filtered or changed language inputs'
        assert language['exit_status']==0 and not language['failures'] and not language['infrastructure_errors'],arch+' language failures'
        assert language['patch_sha256']==patch_sha,arch+' language source mismatch'
        stdlib=ROOT/'.work/language'/qarch/language['run_id']/'stdlib-data.tar.gz'
        assert language['target_stdlib_packages']>100 and sha(stdlib)==language['target_stdlib_archive_sha256'],arch+' target import archives mismatch'
        assert language['test_cases']==language['expected_cases']==native['expected_language_cases']>1000,arch+' incomplete language coverage'
        assert language['qemu']['archive_sha256']==image['sha256'] and language['qemu']['profile']==item['qemu_profile'],arch+' different language QEMU'
        assert sha(langpath.parent/'events.jsonl')==language['log_sha256'],arch+' language log checksum'
        executions=[json.loads(x) for x in (langpath.parent/'target-executions.jsonl').read_text().splitlines()]
        assert len(executions)==language['target_executions']>0,arch+' missing actual target execution'
        assert all(x['arch']==arch for x in executions),arch+' incorrect execution architecture'
        item.update(language_run=language['run_id'],language_cases=language['test_cases'],
                    language_tests=language['tests'],target_executions=len(executions),
                    language_log_sha256=language['log_sha256'],method='native stdlib-tools plus official cross-language driver in full-system QEMU')
    results.append(item)
report=dict(go_version=lock['go']['version'],patch_sha256=patch_sha,
            verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),accepted=True,targets=results)
a.output.parent.mkdir(parents=True,exist_ok=True)
temporary=a.output.with_suffix('.json.partial')
temporary.write_text(json.dumps(report,indent=2)+'\n')
temporary.replace(a.output)
print(json.dumps(report,indent=2))
