// No private application paths are inferred. The test driver supplies a sandbox.
const fs=require('fs');const path=require('path');
const [typescript,generated,suite,guest,output]=process.argv.slice(2);
const ts=require(typescript);
let source=fs.readFileSync(path.join(generated,'Index.ts'),'utf8')
 .replace("import native from 'libgomobile.so';",'').replace(/export /g,'');
source+='\nglobalThis.GOMOBILE_TEST_BINDING={hello,hello_Counter,initialize,collect,dispose};\n';
source+='globalThis.GOMOBILE_TEST_CONTEXT='+JSON.stringify({filesDir:guest+'/files',cacheDir:guest+'/cache',tempDir:guest+'/tmp'})+';\n';
source+=fs.readFileSync(suite,'utf8').replace('const {hello, hello_Counter, initialize, collect, dispose} = globalThis.GOMOBILE_TEST_BINDING;','');
fs.writeFileSync(output,ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.None}}).outputText);
