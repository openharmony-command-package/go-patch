import { hello, initialize, dispose, hello_Counter } from './Index';
async function main(): Promise<void> {
 await initialize({filesDir:'/tmp',cacheDir:'/tmp',tempDir:'/tmp'});
 const result: string=await hello.Hello('typed');
 const count: bigint=await hello.EchoInt64(1n);
 const counter: hello_Counter=await hello_Counter.create();
 const n: number=await counter.Add(1);
 const listener=await hello.NewListener();
 if(listener!==null) await listener.OnMessage(result);
 dispose(listener);counter.dispose();
 await hello.Invoke({OnMessage: async (s: string): Promise<string>=>s+count+n},'callback');
}
void main;
