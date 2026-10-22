#!/usr/bin/env python3
"""Compile the standalone ArkTS caller and verify all three HAR libraries in its HAP."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];REPO=ROOT.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--har',type=pathlib.Path,required=True)
p.add_argument('--sdk-home',type=pathlib.Path,required=True)
p.add_argument('--node',type=pathlib.Path,required=True)
p.add_argument('--ohpm',type=pathlib.Path,required=True)
p.add_argument('--hvigor',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True,help='new ignored project directory')
p.add_argument('--hap-output',type=pathlib.Path,default=REPO/'dist/gomobile/gomobile-ohos-example-unsigned.hap')
a=p.parse_args();a.output=a.output.resolve();assert not a.output.exists(),'choose a new output directory'
source=ROOT/'examples/arkts';shutil.copytree(source,a.output)
shutil.copy2(a.har,a.output/'gomobile-ohos-example.har')
(a.output/'local.properties').write_text('hwsdk.dir='+str(a.sdk_home.resolve())+'\n')
env=dict(os.environ,DEVECO_SDK_HOME=str(a.sdk_home.resolve()))
env.pop('HOS_SDK_HOME',None);env['PATH']=str(a.node.resolve().parent)+os.pathsep+env.get('PATH','')
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
report=dict(accepted=False,scope='ArkTS caller compilation and embedded library checks',runtime_accepted=False,
 mobile_patch_sha256=sha(ROOT/'patch/mobile-ohos.patch'),har_sha256=sha(a.har),
 example_sources_sha256={str(f.relative_to(source)):sha(f) for f in sorted(source.rglob('*')) if f.is_file()})
log=open(a.output/'build.log','w')
def run(args,cwd):
 log.write(repr(list(map(str,args)))+'\n');log.flush()
 subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
try:
 run([a.ohpm.resolve(),'install'],a.output/'entry')
 run([a.hvigor.resolve(),'--mode','module','-p','product=default','-p','module=entry@default','assembleHap','--no-daemon'],a.output)
 hap=a.output/'entry/build/default/outputs/default/entry-default-unsigned.hap'
 with zipfile.ZipFile(hap) as zip:
  libraries={abi:hashlib.sha256(zip.read('libs/'+abi+'/libgomobile.so')).hexdigest() for abi in ['arm64-v8a','armeabi-v7a','x86_64']}
 import tarfile
 with tarfile.open(a.har) as tar:info=json.load(tar.extractfile('package/BUILD-INFO.json'))
 assert libraries==info['native_libraries_sha256'],'HAP library differs from tested HAR'
 a.hap_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(hap,a.hap_output)
 a.hap_output.with_suffix('.hap.sha256').write_text(sha(hap)+'  '+a.hap_output.name+'\n')
 report.update(accepted=True,hap_sha256=sha(hap),native_libraries_sha256=libraries)
except Exception as error:
 report['error']=str(error);raise
finally:
 log.close();report['raw_log_sha256']=sha(a.output/'build.log')
 (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
