const fs=require('fs');const path=require('path');
const [typescript,dir]=process.argv.slice(2);const ts=require(typescript);
const source=fs.readFileSync(path.join(dir,'Index.ts'),'utf8')
 .replace("import native from 'libgomobile.so';","const native = require('./bridge.node');");
fs.writeFileSync(path.join(dir,'Index.js'),ts.transpileModule(source,
 {compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS}}).outputText);
