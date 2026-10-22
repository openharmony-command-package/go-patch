#!/usr/bin/env python3
"""Apply the pinned x/mobile patch and package gomobile/gobind for nine hosts."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,tarfile,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parent
LOCK=json.loads((ROOT/'manifest.json').read_text())
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',type=pathlib.Path,default=REPO/'.work/upstream/mobile')
s=p.add_subparsers(dest='command',required=True)
s.add_parser('prepare');s.add_parser('refresh');s.add_parser('check')
b=s.add_parser('build');b.add_argument('--go',type=pathlib.Path,default=REPO/'.work/upstream/go/bin/go');b.add_argument('--targets',default=','.join(LOCK['targets']));b.add_argument('--output',type=pathlib.Path,default=REPO/'dist/gomobile');b.add_argument('--skip-build',action='store_true')
a=p.parse_args();a.source=a.source.resolve();patch=ROOT/'patch'/LOCK['patch']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
paths=(ROOT/'patch/source-paths.txt').read_text().splitlines()
if a.command=='prepare':
 if not a.source.exists():
  a.source.parent.mkdir(parents=True,exist_ok=True)
  run(['git','clone','--no-checkout','git@github.com:golang/mobile.git',a.source])
  run(['git','checkout','--detach',LOCK['upstream']['commit']],cwd=a.source)
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip()
 assert head==LOCK['upstream']['commit'],'source revision differs from manifest'
 assert sha(patch)==patch.with_suffix('.patch.sha256').read_text().split()[0]
 reverse=subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=a.source,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if reverse.returncode:run(['git','apply','--check',patch],cwd=a.source);run(['git','apply',patch],cwd=a.source)
 print('Prepared',a.source)
elif a.command=='refresh':
 run(['git','add','-N','--',*paths],cwd=a.source)
 data=subprocess.check_output(['git','diff','--binary',LOCK['upstream']['commit'],'--',*paths],cwd=a.source)
 patch.write_bytes(data);patch.with_suffix('.patch.sha256').write_text(sha(patch)+'  '+patch.name+'\n');print(sha(patch))
elif a.command=='check':
 assert sha(patch)==patch.with_suffix('.patch.sha256').read_text().split()[0]
 with tempfile.TemporaryDirectory(prefix='mobile-ohos-apply-') as tmp:
  archive=subprocess.Popen(['git','archive',LOCK['upstream']['commit']],cwd=a.source,stdout=subprocess.PIPE)
  with tarfile.open(fileobj=archive.stdout,mode='r|') as tar:tar.extractall(tmp,filter='data')
  assert archive.wait()==0
  # A private empty Git directory avoids inheriting the parent repository.
  run(['git','init','-q',tmp])
  run(['git','apply','--check',patch],cwd=tmp);run(['git','apply',patch],cwd=tmp)
  for name in paths:assert (pathlib.Path(tmp)/name).read_bytes()==(a.source/name).read_bytes(),name+' differs from reusable patch'
 print('Fresh upstream + patch equals every adapted source file')
else:
 targets=a.targets.split(',');assert targets and len(set(targets))==len(targets) and set(targets)<=set(LOCK['targets'])
 a.go=a.go.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ,GOTOOLCHAIN='local',GOENV='off',CGO_ENABLED='0',GOARM='7',GOCACHE=str(REPO/'.work/gocache'),GOWORK='off')
 env.pop('GOOS',None);env.pop('GOARCH',None);env.pop('GOROOT',None)
 version=subprocess.check_output([a.go,'version'],env=env,text=True).strip();assert version.startswith('go version '+LOCK['go_version']+' '),version
 goroot=pathlib.Path(subprocess.check_output([a.go,'env','GOROOT'],env=env,text=True).strip())
 goinfo_path=goroot/'BUILD-INFO.json'
 go_patch=json.loads(goinfo_path.read_text())['patch_sha256'] if goinfo_path.exists() else sha(REPO/'patch'/json.loads((REPO/'manifest.json').read_text())['patch']['filename'])
 revision=sha(patch);assert revision==patch.with_suffix('.patch.sha256').read_text().split()[0]
 rows=[]
 for target in targets:
  goos,arch=target.split('-');product=REPO/'.work/mobile-products'/target/'gomobile';bin_dir=product/'bin';bin_dir.mkdir(parents=True,exist_ok=True)
  suffix='.exe' if goos=='windows' else ''
  metadata=product/'BUILD-INFO.json'
  if a.skip_build:
   old=json.loads(metadata.read_text());assert old['patch_sha256']==revision and old['target']==target and old['go_patch_sha256']==go_patch,'cannot reuse binaries from another patch'
   for tool in ['gomobile','gobind']:assert sha(bin_dir/(tool+suffix))==old['binaries_sha256'][tool],'refusing to repack altered binaries'
  else:
   build_env=dict(env,GOOS=goos,GOARCH=arch)
   for tool in ['gomobile','gobind']:
    run([a.go,'build','-trimpath','-ldflags','-buildid= -X main.ohosRevision='+revision,'-o',bin_dir/(tool+suffix),'./cmd/'+tool],cwd=a.source,env=build_env)
  for name in ['README.md','README.zh-CN.md','manifest.json','THIRD-PARTY-NOTICES.md','PATENTS']:
   shutil.copy2(ROOT/name,product/name)
  for name in ['patch','scripts','docs','tests','examples']:
   dst=product/name
   if dst.exists():shutil.rmtree(dst)
   shutil.copytree(ROOT/name,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
  shutil.copy2(a.source/'LICENSE',product/'LICENSE')
  info=dict(upstream=LOCK['upstream'],patch_sha256=revision,go_version=version,go_patch_sha256=go_patch,build_go_sha256=sha(a.go),target=target,binaries_sha256={tool:sha(bin_dir/(tool+suffix)) for tool in ['gomobile','gobind']},features=LOCK['features'])
  metadata.write_text(json.dumps(info,indent=2)+'\n')
  name='gomobile-'+LOCK['upstream']['commit'][:12]+'.'+target+('.zip' if goos=='windows' else '.tar.gz');archive=a.output/name
  if goos=='windows':
   with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(product.rglob('*')):
     if f.is_file():z.write(f,'gomobile/'+str(f.relative_to(product)))
  else:
   with tarfile.open(archive,'w:gz',format=tarfile.GNU_FORMAT) as t:t.add(product,arcname='gomobile')
  digest=sha(archive);archive.with_suffix(archive.suffix+'.sha256').write_text(digest+'  '+name+'\n');rows.append(dict(filename=name,target=target,sha256=digest,bytes=archive.stat().st_size,binaries_sha256=info['binaries_sha256']))
  print('PACKAGED',target,archive,flush=True)
 bundle_name='gomobile-ohos-port-'+LOCK['upstream']['commit'][:12]+'.tar.gz';bundle=a.output/bundle_name
 with tarfile.open(bundle,'w:gz',format=tarfile.GNU_FORMAT) as tar:
  for name in ['README.md','README.zh-CN.md','LICENSE','PATENTS','THIRD-PARTY-NOTICES.md','manifest.json','patch','scripts','docs','tests','examples']:
   tar.add(ROOT/name,arcname='gomobile-ohos-port/'+name,filter=lambda info:None if '__pycache__' in info.name or info.name.endswith('.pyc') else info)
 bundle_row=dict(filename=bundle_name,sha256=sha(bundle),bytes=bundle.stat().st_size)
 bundle.with_suffix('.gz.sha256').write_text(bundle_row['sha256']+'  '+bundle_name+'\n')
 (a.output/'SHA256SUMS').write_text(''.join(row['sha256']+'  '+row['filename']+'\n' for row in rows+[bundle_row]))
 (a.output/'manifest.json').write_text(json.dumps(dict(upstream=LOCK['upstream'],patch_sha256=revision,archives=rows,port_bundle=bundle_row),indent=2)+'\n')
