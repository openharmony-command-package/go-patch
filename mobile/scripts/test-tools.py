#!/usr/bin/env python3
"""Execute paired commands on macOS, Linux containers, or native OHOS QEMU."""
import argparse,hashlib,io,json,os,pathlib,shlex,subprocess,tarfile,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1];REPO=ROOT.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--host',required=True)
p.add_argument('--product',type=pathlib.Path)
p.add_argument('--go-toolchain',type=pathlib.Path,help='real matching host Go prefix, required for Linux')
p.add_argument('--image',help='existing image ID matching the Linux host architecture')
p.add_argument('--output',type=pathlib.Path)
p.add_argument('--qemu-work',type=pathlib.Path,default=REPO/'.work/qemu')
a=p.parse_args();host,arch=a.host.split('-');assert host in ['darwin','linux','openharmony'] and arch in ['arm64','arm','amd64']
product=(a.product or REPO/'.work/mobile-products'/a.host/'gomobile').resolve()
out=a.output or REPO/'.work/mobile-tools-check'/a.host;out.mkdir(parents=True,exist_ok=True)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
info=json.loads((product/'BUILD-INFO.json').read_text());revision=sha(ROOT/'patch/mobile-ohos.patch')
assert info['patch_sha256']==revision and info['target']==a.host
for tool in ['gomobile','gobind']:assert sha(product/'bin'/tool)==info['binaries_sha256'][tool]
report=dict(host=a.host,accepted=False,patch_sha256=revision,binaries_sha256=info['binaries_sha256'],scope='paired command execution; not full SDK bind on this host')
log=open(out/'raw.log','w')
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,**kw)
 log.write(shlex.join(map(str,args))+'\n'+r.stdout);log.flush();r.check_returncode();return r.stdout
try:
 if host=='darwin':
  assert os.uname().sysname=='Darwin'
  env=dict(os.environ)
  if a.go_toolchain:env['PATH']=str(a.go_toolchain.resolve()/'bin')+os.pathsep+env.get('PATH','')
  text=run([product/'bin/gomobile','version'],env=env)+run([product/'bin/gobind','-version'],env=env)
 elif host=='linux':
  assert a.image and a.go_toolchain,'--image and --go-toolchain are required'
  go_binary=a.go_toolchain.resolve()/'bin/go'
  report['host_go_sha256']=sha(go_binary)
  image_arch=run(['docker','image','inspect',a.image,'--format','{{.Architecture}}']).strip();assert image_arch==arch
  payload=out/'input.tar'
  with tarfile.open(payload,'w') as tar:
   for tool in ['gomobile','gobind']:tar.add(product/'bin'/tool,arcname=tool)
   tar.add(go_binary,arcname='go/bin/go')
  name='go-patch-mobile-tools-'+uuid.uuid4().hex[:10]
  with payload.open('rb') as inp:
   text=run(['docker','run','--rm','--name',name,'--network','none','--cpus','1','--memory','512m','--platform','linux/'+arch,'-i','--entrypoint','sh',a.image,'-ec','cd /tmp; tar -xf -; export GOROOT=/tmp/go PATH=/tmp/go/bin:$PATH; ./gomobile version; ./gobind -version'],stdin=inp,timeout=180)
  report['image']=a.image
 else:
  qarch={'arm64':'arm64','arm':'armv7a','amd64':'x86_64'}[arch]
  def qemu(*args):return run(['python3',REPO/'scripts/qemu.py','--arch',qarch,'--work',a.qemu_work,*args])
  guest='/data/local/tmp/go-patch/mobile-cli-'+arch
  qemu('shell','mkdir -p '+guest+'/bin '+guest+'/scripts')
  for tool in ['gomobile','gobind']:qemu('send',product/'bin'/tool,guest+'/bin/'+tool)
  qemu('send',ROOT/'scripts/sign-installed.sh',guest+'/scripts/sign-installed.sh')
  text=qemu('shell','set -e\nexport PATH=/data/local/tmp/go-patch/go/bin:/data/local/tmp/go-patch/bin:/system/bin:/bin\nexport BINARY_SIGN_TOOL=/data/local/tmp/go-patch/bin/binary-sign-tool\nsh '+guest+'/scripts/sign-installed.sh '+guest+'\n'+guest+'/bin/gomobile version\n'+guest+'/bin/gobind -version','--timeout','180')
  report['deployment_self_signed']=True
 assert 'gomobile OHOS '+revision in text and 'gobind ohos '+revision in text,text
 report.update(accepted=True,output=text.strip())
except Exception as error:
 report['error']=str(error);raise
finally:
 log.close();report['raw_log_sha256']=sha(out/'raw.log');(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
