#!/usr/bin/env python3
"""Official Go language-test driver with -target and full-system OHOS execution.

This uses the same runOnHost design as cmd/dist's cmd/internal/testdir tests.
Every test file is present. Target executables run through qemu-exec.py; failed
transport/signing/runner operations fail the aggregate even in runfail cases.
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
import sys
import tarfile

ROOT=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch',choices=['arm64','armv7a','x86_64'],required=True)
p.add_argument('--source',type=Path,default=ROOT/'.work/upstream/go')
p.add_argument('--sdk',type=Path,required=True)
p.add_argument('--work',type=Path,default=ROOT/'.work/qemu')
p.add_argument('--run-id',default='language-r1')
p.add_argument('--run',help='optional test-name filter for diagnosis; omitted for full acceptance')
p.add_argument('--parallel',type=int,default=2)
p.add_argument('--timeout',default='4h',help='official test driver timeout')
p.add_argument('--exec-timeout',type=int,default=7200,help='per-target execution timeout in seconds')
a=p.parse_args()
a.source,a.sdk,a.work=a.source.resolve(),a.sdk.resolve(),a.work.resolve()
arch={'arm64':'arm64','armv7a':'arm','x86_64':'amd64'}[a.arch]
work=ROOT/'.work/language'/a.arch/a.run_id
work.mkdir(parents=True,exist_ok=True)
output=ROOT/'.work/logs/language'/a.arch/a.run_id
output.mkdir(parents=True,exist_ok=True)
go=a.source/'bin/go'
def sha(path):return hashlib.file_digest(open(path,'rb'),'sha256').hexdigest()
lock=json.loads((ROOT/'manifest.json').read_text())
patch=ROOT/'patch'/lock['patch']['filename']
assert (a.source/'VERSION').read_text().splitlines()[0]==lock['go']['version'],'source version does not match manifest'
test_source=a.source/'src/cmd/internal/testdir/testdir_test.go'
tracked=[patch,test_source,ROOT/'scripts/qemu-exec.py',Path(__file__).resolve()]
input_hashes={str(x):sha(x) for x in tracked}
dirs=re.findall(r'"([^"]+)"',re.search(r'dirs = \[\]string\{([^}]+)\}',test_source.read_text()).group(1))
expected_cases=sum(1 for d in dirs for f in (a.source/'test'/d).glob('*.go') if not f.name.startswith('.'))
base=dict(os.environ,GOROOT=str(a.source),GOCACHE=str(ROOT/'.work/gocache'),GOTOOLCHAIN='local',GOENV='off',GOMAXPROCS='2')
for key in ['GOOS','GOARCH','CC','CXX']:base.pop(key,None)
assert len(list((a.source/'test').rglob('*.go')))>1000,'official language-test data is missing'
driver=work/'testdir.test'
with open(output/'build.log','w') as log:
    subprocess.run([str(go),'test','-c','-o',str(driver),'cmd/internal/testdir'],
        env=dict(base,CGO_ENABLED='0'),stdout=log,stderr=subprocess.STDOUT,check=True)
wrapper=work/('go_openharmony_'+arch+'_exec')
wrapper.write_text('#!/bin/sh\nexec '+shlex.join([sys.executable,str(ROOT/'scripts/qemu-exec.py'),
    '--arch',a.arch,'--work',str(a.work),'--timeout',str(a.exec_timeout)])+' "$@"\n')
wrapper.chmod(0o755)
env=dict(base,GOOS='openharmony',GOARCH=arch,GOARM='7',CGO_ENABLED='1',
    CC=str(ROOT/'scripts'/('cc-'+arch)),CXX=str(ROOT/'scripts'/('cxx-'+arch)),
    OHOS_NDK_HOME=str(a.sdk),GO_BUILDER_NAME='openharmony-'+arch+'-cross-language',GO_TEST_TIMEOUT_SCALE='20',
    PATH=str(work)+os.pathsep+str(a.source/'bin')+os.pathsep+os.environ['PATH'])
def qemu(command,*args):
    cmd=['python3',ROOT/'scripts/qemu.py','--arch',a.arch,'--work',a.work,command,*args]
    return subprocess.check_output(list(map(str,cmd)),text=True)
# A separate fixture root lets a concurrently running native standard-library
# audit keep its source tree immutable. Programs see the complete official test
# tree, while bin/src/pkg resolve to the guest's matching native Go toolchain.
root='/data/local/tmp/go-patch'
qemu('shell','mkdir '+root+'/language-running')
try:
    archive=work/'language-data.tar.gz'
    with tarfile.open(archive,'w:gz',format=tarfile.GNU_FORMAT) as tar:
        tar.add(a.source/'test',arcname='test')
    qemu('send',archive,root+'/language-data.tar.gz')
    links=['bin','pkg','src','lib','api','doc','misc','VERSION','go.env']
    script='set -e\nmkdir -p '+root+'/language-goroot '+root+'/language-exec\ncd '+root+'/language-goroot\ntar -xzf ../language-data.tar.gz\n'
    script+='\n'.join('test -e '+x+' || ln -s ../go/'+x+' '+x for x in links)
    qemu('shell',script,'--timeout',300)
    # A few official programs invoke the compiler/linker themselves. Supply
    # matching target export archives and rewrite every host cache path, rather
    # than giving those native compiler children an unusable host importcfg.
    export_env=dict(env,GOFLAGS='')
    exports=subprocess.check_output([str(go),'list','-export','-f',
        '{{if .Export}}packagefile {{.ImportPath}}={{.Export}}{{end}}','std'],env=export_env,text=True)
    stdlib_archive=work/'stdlib-data.tar.gz'
    guest_stdlib=root+'/language-stdlib'
    entries=set();config=[]
    with tarfile.open(stdlib_archive,'w:gz',format=tarfile.GNU_FORMAT) as tar:
        for line in exports.splitlines():
            if not line:continue
            package,path=line.split('=',1)
            archive_path=Path(path)
            name='archives/'+archive_path.name+'.a'
            if name not in entries:
                tar.add(archive_path,arcname=name);entries.add(name)
            config.append(package+'='+guest_stdlib+'/'+name)
        config_file=work/'target-importcfg'
        config_file.write_text('\n'.join(config)+'\n')
        tar.add(config_file,arcname='importcfg')
    qemu('send',stdlib_archive,root+'/stdlib-data.tar.gz')
    qemu('shell','mkdir -p '+guest_stdlib+' && cd '+guest_stdlib+' && tar -xzf ../stdlib-data.tar.gz','--timeout',1200)
    errors=output/'infrastructure-errors.jsonl'
    errors.unlink(missing_ok=True)
    audit=output/'target-executions.jsonl'
    audit.unlink(missing_ok=True)
    env.update(GO_QEMU_EXEC_ERROR_LOG=str(errors),GO_QEMU_EXEC_AUDIT_LOG=str(audit))
    flags=['-test.v=test2json','-test.short','-test.count=1','-test.timeout='+a.timeout,
        '-test.parallel='+str(a.parallel),'-target=openharmony/'+arch]
    if a.run:flags+=['-test.run='+a.run]
    command=[str(go),'tool','test2json','-t','-p','cmd/internal/testdir:openharmony/'+arch,str(driver),*flags]
    (output/'command.json').write_text(json.dumps(command,indent=2)+'\n')
    with open(output/'events.jsonl','w') as log:
        result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    counts=collections.Counter();failures=[];runs=0
    for line in (output/'events.jsonl').read_text().splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get('Action')=='run' and event.get('Test','').startswith('Test/'):runs+=1
        if event.get('Test','').startswith('Test/') and event.get('Action') in ['pass','fail','skip']:counts[event['Action']]+=1
        if event.get('Action')=='fail':failures.append(event.get('Test','<package>'))
    infrastructure=[] if not errors.exists() else [json.loads(x) for x in errors.read_text().splitlines()]
    executions=0 if not audit.exists() else len(audit.read_text().splitlines())
    inputs_unchanged=all(sha(Path(path))==value for path,value in input_hashes.items())
    accepted=result.returncode==0 and not failures and not infrastructure and inputs_unchanged and (runs==expected_cases or bool(a.run) and runs>0) and executions>0
    report=dict(arch=arch,method='official runOnHost -target; signed execution in full-system OHOS QEMU',
        run_id=a.run_id,diagnostic_filter=a.run,exit_status=result.returncode,test_cases=runs,expected_cases=expected_cases,
        target_timeout_seconds=a.exec_timeout,recipe_timeout_scale=20,
        target_stdlib_archive_sha256=sha(stdlib_archive),target_stdlib_packages=len(config),
        tests=counts,target_executions=executions,failures=failures,infrastructure_errors=infrastructure,accepted=accepted,
        patch_sha256=input_hashes[str(patch)],input_hashes=input_hashes,inputs_unchanged=inputs_unchanged,driver_sha256=sha(driver),
        qemu=json.loads((a.work/a.arch/'state.json').read_text()),
        log_sha256=hashlib.file_digest(open(output/'events.jsonl','rb'),'sha256').hexdigest())
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
finally:
    qemu('shell','rmdir '+root+'/language-running')
raise SystemExit(0 if accepted else 1)
