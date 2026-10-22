#!/usr/bin/env python3
"""Check generated TypeScript and run host Node N-API binding conformance."""
import argparse,hashlib,json,os,pathlib,subprocess,time,shlex
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--go',type=pathlib.Path,required=True)
p.add_argument('--gobind',type=pathlib.Path,required=True)
p.add_argument('--node',type=pathlib.Path,required=True)
p.add_argument('--node-include',type=pathlib.Path,required=True)
p.add_argument('--typescript',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,default=REPO/'.work/mobile-host/current')
a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
env=dict(os.environ,GOTOOLCHAIN='local',GOENV='off',GOWORK='off',CGO_ENABLED='1',GOCACHE=str(REPO/'.work/gocache'))
env['PATH']=str(a.go.resolve().parent)+os.pathsep+env.get('PATH','')
for name in ['GOROOT','GOOS','GOARCH','CC','CXX','CGO_CFLAGS','CGO_LDFLAGS']:env.pop(name,None)
report=dict(accepted=False,scope='host Node N-API conformance; not OHOS execution',
 patch_sha256=sha(ROOT/'patch/mobile-ohos.patch'),go_binary_sha256=sha(a.go.resolve()),
 gobind_binary_sha256=sha(a.gobind.resolve()),suite_sha256=sha(ROOT/'tests/node.cjs'),
 typecheck_sha256=sha(ROOT/'tests/typecheck.ts'))
log=open(a.output/'raw.log','w')
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,**kw)
 log.write(repr(list(map(str,args)))+'\n'+r.stdout);log.flush();r.check_returncode();return r.stdout
try:
 assert report['patch_sha256'] in run([a.gobind.resolve(),'-version'])
 run([a.gobind.resolve(),'-lang=go,openharmony','-outdir',a.output,'.'],cwd=ROOT/'tests/hello')
 (a.output/'go.mod').write_text('module gomobile.local/hosttest\n\ngo 1.27.0\n\nrequire example.org/ohoshello v0.0.0\nreplace example.org/ohoshello => '+json.dumps(str(ROOT/'tests/hello'))+'\n')
 (a.output/'typecheck.ts').write_bytes((ROOT/'tests/typecheck.ts').read_bytes())
 config=dict(compilerOptions=dict(target='ES2020',module='commonjs',strict=True,noEmit=True,baseUrl='.',paths={'libgomobile.so':['native.d.ts']},types=[]),files=['Index.ts','typecheck.ts'])
 (a.output/'tsconfig.json').write_text(json.dumps(config))
 run([a.node,a.typescript.resolve().parent/'tsc.js','-p',a.output/'tsconfig.json'])
 env['CGO_CFLAGS']='-DGOMOBILE_NODE_TEST '+shlex.join(['-I'+str(a.node_include.resolve())])
 env['CGO_LDFLAGS']='-Wl,-undefined,dynamic_lookup' if os.uname().sysname=='Darwin' else ''
 run([a.go.resolve(),'-C',a.output,'build','-tags=gomobile_ohos_test','-buildmode=c-shared','-o',a.output/'bridge.node','./src/gobind'])
 run([a.node,ROOT/'tests/transpile-node.cjs',a.typescript.resolve(),a.output])
 text=run([a.node,ROOT/'tests/node.cjs',a.output],timeout=180)
 result=json.loads(text.strip().splitlines()[-1]);assert result['accepted'] and result['cases']==27
 report.update(accepted=True,cases=27,typescript_strict=True,node_version=run([a.node,'--version']).strip(),native_library_sha256=sha(a.output/'bridge.node'))
except Exception as error:
 report['error']=str(error);raise
finally:
 log.close();report['raw_log_sha256']=sha(a.output/'raw.log')
 (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
