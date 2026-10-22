// Portable binding conformance: executed by the real OHOS Ark runtime.
// The harness injects the generated binding and Context paths, never app paths.
const {hello, hello_Counter, initialize, collect, dispose} = globalThis.GOMOBILE_TEST_BINDING;
let checks = [];
function failure(message) { throw Error(message); }
const assert = {
 equal(a,b) { if(a!==b) failure('expected '+String(b)+', got '+String(a)); },
 ok(a) { if(!a) failure('assertion failed'); },
 deepEqual(a,b) {
  if(a===null || b===null) { if(a!==b) failure('null mismatch'); return; }
  if(a.length!==b.length) failure('length mismatch');
  for(let i=0;i<a.length;i++) this.equal(a[i],b[i]);
 },
 async rejects(p,pattern) { try { await p; } catch(e) { if(pattern.test(String(e)))return; throw e; } failure('expected rejection'); },
 throws(fn,pattern) { try { fn(); } catch(e) { if(pattern.test(String(e)))return; throw e; } failure('expected exception'); }
};
async function check(name,fn) { await fn(); checks.push(name); }
(async()=>{
 if(globalThis.GOMOBILE_TEST_ROUND===2) {
  await initialize(globalThis.GOMOBILE_TEST_CONTEXT);
  await check('previous-environment-closed',()=>assert.rejects(hello.FireSaved('closed'),/environment closed/));
  await hello.SaveListener(null);collect();
  await check('fresh-environment-usable',async()=>assert.equal(await hello.Hello('fresh'),'Hello, fresh'));
 } else {
 await check('initialization-required',()=>assert.rejects(hello.Hello('early'),/initialize/));
 await initialize(globalThis.GOMOBILE_TEST_CONTEXT);
 await check('Context-directories-visible-in-Go',async()=>{
  const c=globalThis.GOMOBILE_TEST_CONTEXT;
  assert.equal(await hello.DirectoryState(),c.filesDir+'\n'+c.cacheDir+'\n'+c.tempDir);
  await hello.WritePrivateFile('go-context.txt','GOMOBILE_CONTEXT_WRITE_OK');
 });
 await check('UTF8-and-NUL',async()=>assert.equal(await hello.Hello('鸿蒙\0😀'),'Hello, 鸿蒙\0😀'));
 await check('int64-lossless',async()=>{for(const n of [0n,-1n,9223372036854775807n,-9223372036854775808n])assert.equal(await hello.EchoInt64(n),n);});
 await check('bytes-copy',async()=>assert.deepEqual(await hello.EchoBytes(new Uint8Array([0,1,127,128,255])),new Uint8Array([0,1,127,128,255])));
 await check('nil-bytes',async()=>assert.equal(await hello.EchoBytes(null),null));
 await check('Go-errors',()=>assert.rejects(hello.Divide(1,0),/division by zero/));
 await check('Go-panic-rejection',()=>assert.rejects(hello.PanicNow(),/Go panic: fixture panic/));
 await check('scalar-type-check',()=>assert.rejects(hello.Hello(12),/expected string/));
 await check('integer-range-check',()=>assert.rejects(hello.ByteValue(256),/out of range/));
 await check('struct-constructor-fields-method',async()=>{const c=await hello_Counter.create();assert.equal(await c.GetValue(),0);await c.SetValue(8);assert.equal(await c.Add(3),11);await c.SetLabel('测试');assert.equal(await c.GetLabel(),'测试');c.dispose();});
 await check('Go-constructor',async()=>{const c=await hello.NewCounter(20);assert.equal(await c.Add(2),22);c.dispose();});
 await check('disposed-reference',async()=>{const c=await hello.NewCounter(1);c.dispose();await assert.rejects(c.Add(1),/disposed/);assert.throws(()=>c.dispose(),/disposed/);});
 await check('variables-constants',async()=>{await hello.SetGreeting('Changed');assert.equal(await hello.GetGreeting(),'Changed');assert.equal(await hello.GetVersion(),'1.0');});
 await check('sync-interface-callback',async()=>assert.equal(await hello.Invoke({OnMessage:s=>'JS '+s},'世界'),'JS 世界'));
 await check('async-interface-callback',async()=>assert.equal(await hello.InvokeLater({OnMessage:async s=>{await Promise.resolve();return 'Async '+s;}},'世界'),'Async 世界'));
 await check('callback-rejection',()=>assert.rejects(hello.Invoke({OnMessage:async()=>{throw Error('callback failed');}},'x'),/callback failed/));
 await check('nil-interface',()=>assert.rejects(hello.Invoke(null,'x'),/nil listener/));
 await check('invalid-interface',()=>assert.rejects(hello.Invoke({},'x'),/missing interface method/));
 await check('Go-interface-result',async()=>{const l=await hello.NewListener();assert.equal(await l.OnMessage('x'),'Go: x');dispose(l);});
 await check('retained-callback',async()=>{await hello.SaveListener({OnMessage:s=>'Retained '+s});collect();assert.equal(await hello.FireSaved('later'),'Retained later');await hello.SaveListener(null);collect();});
 await check('concurrent-callbacks',async()=>{const out=await Promise.all(Array.from({length:40},(_,i)=>hello.InvokeLater({OnMessage:async s=>s+'!'},String(i))));assert.deepEqual(out,Array.from({length:40},(_,i)=>i+'!'));});
 await check('floating-point-special-values',async()=>{for(const n of [NaN,Infinity,-Infinity,-0]){assert.ok(Object.is(await hello.EchoFloat(n),n));assert.ok(Object.is(await hello.EchoFloat32(n),n));}assert.equal(await hello.EchoFloat32(0.1),Math.fround(0.1));});
 await check('callback-external-named-type',async()=>assert.equal(await hello.ClockDelay({Delay:async d=>d+3n},9223372036854775800n),9223372036854775803n));
 await check('callback-returning-interface',async()=>assert.equal(await hello.InvokeFactory({Create:async()=>({OnMessage:s=>'Factory '+s})},'OK'),'Factory OK'));
 await check('callback-object-bytes-bigint',async()=>{const result=await hello.InvokeObject({Update:async(c,b,n)=>{assert.deepEqual(b,new Uint8Array([0,128,255]));assert.equal(n,9223372036854775807n);await c.Add(5);return c;}});assert.equal(await result.GetValue(),15);result.dispose();});
 await check('nested-Go-calls-from-callbacks',async()=>{const values=await Promise.all(Array.from({length:20},(_,i)=>hello.InvokeLater({OnMessage:async s=>await hello.Hello(s)},String(i))));assert.deepEqual(values,Array.from({length:20},(_,i)=>'Hello, '+i));});

  await hello.SaveListener({OnMessage:s=>'retained until environment closes: '+s});
 }
 globalThis.GO_OHOS_TEST_REPORT=JSON.stringify({accepted:true,cases:checks.length,checks,scope:'OHOS Ark N-API conformance',round:globalThis.GOMOBILE_TEST_ROUND});
 globalThis.GO_OHOS_TEST_OK=true;
})().catch(e=>{globalThis.GO_OHOS_TEST_ERROR=String(e)+' '+(e.stack||'');});
