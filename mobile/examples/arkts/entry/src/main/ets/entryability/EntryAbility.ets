import UIAbility from '@ohos.app.ability.UIAbility';
import window from '@ohos.window';
import hilog from '@ohos.hilog';
import i18n from '@ohos.i18n';
import fs from '@ohos.file.fs';
import { initialize, hello, hello_Counter } from '@gomobile/bindings';

export default class EntryAbility extends UIAbility {
 onCreate(): void { this.runBindings(); }
 onWindowStageCreate(stage: window.WindowStage): void { stage.loadContent('pages/Index'); }
 async runBindings(): Promise<void> {
  let result: string;
  try {
   await initialize(this.context, { timezone: i18n.getTimeZone().getID() });
   const expected = this.context.filesDir+'\n'+this.context.cacheDir+'\n'+this.context.tempDir;
   if (await hello.DirectoryState() !== expected) throw new Error('Context directory mismatch');
   await hello.WritePrivateFile('go-context.txt','GOMOBILE_CONTEXT_WRITE_OK');
   if (await hello.Hello('应用') !== 'Hello, 应用') throw new Error('UTF8 call');
   const c = await hello_Counter.create();
   if (await c.Add(7) !== 7) throw new Error('counter');
   c.dispose();
   const callback = await hello.InvokeLater({OnMessage: async (s: string): Promise<string> => await hello.Hello(s)}, 'callback');
   if (callback !== 'Hello, callback') throw new Error('nested async callback');
   result = 'GOMOBILE_OHOS_HAP_PASS';
  } catch (e) { result = 'GOMOBILE_OHOS_HAP_FAIL '+String(e); }
  hilog.info(0, 'GoMobileTest', '%{public}s', result);
  try {
   const file=fs.openSync(this.context.filesDir+'/gomobile-result.txt',fs.OpenMode.CREATE|fs.OpenMode.READ_WRITE|fs.OpenMode.TRUNC);
   try { fs.writeSync(file.fd,result); } finally { fs.closeSync(file); }
  } catch (e) { hilog.error(0, 'GoMobileTest', 'Cannot save result: %{public}s', String(e)); }
 }
}
