@Entry
@Component
struct Index {
 build() {
  Column({ space: 16 }) {
   Text('Go OHOS bindings').fontSize(28)
   Text('EntryAbility runs the bindings and writes gomobile-result.txt in the application files directory.').fontSize(18)
  }.width('100%').height('100%').justifyContent(FlexAlign.Center).padding(24)
 }
}
