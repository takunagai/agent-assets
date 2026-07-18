// CGEvent による HID レベルクリック（Electron 等 System Events の click が効かないアプリ用）
// 使い方: click <x> <y> [--double|--right]
import CoreGraphics
import Foundation
let args = CommandLine.arguments
guard args.count >= 3, let x = Double(args[1]), let y = Double(args[2]) else {
    print("usage: click <x> <y> [--double|--right]"); exit(1)
}
let pt = CGPoint(x: x, y: y)
let isRight = args.contains("--right")
let isDouble = args.contains("--double")
let down: CGEventType = isRight ? .rightMouseDown : .leftMouseDown
let up: CGEventType = isRight ? .rightMouseUp : .leftMouseUp
let btn: CGMouseButton = isRight ? .right : .left
// カーソル移動イベントを先に送る（hover 依存 UI 対策）
CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: pt, mouseButton: .left)?.post(tap: .cghidEventTap)
usleep(50000)
func clickOnce(clickState: Int64) {
    for type in [down, up] {
        let ev = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: pt, mouseButton: btn)!
        ev.setIntegerValueField(.mouseEventClickState, value: clickState)
        ev.post(tap: .cghidEventTap)
        usleep(60000)
    }
}
clickOnce(clickState: 1)
if isDouble { clickOnce(clickState: 2) }
