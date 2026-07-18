// 接続中ディスプレイのグローバル座標系での配置を一覧表示
import CoreGraphics
import Foundation
var count: UInt32 = 0
CGGetActiveDisplayList(0, nil, &count)
var ids = [CGDirectDisplayID](repeating: 0, count: Int(count))
CGGetActiveDisplayList(count, &ids, &count)
for (i, id) in ids.enumerated() {
    let b = CGDisplayBounds(id)
    let isMain = CGDisplayIsMain(id) == 1 ? " (main)" : ""
    print("display \(i + 1): origin=(\(Int(b.origin.x)),\(Int(b.origin.y))) size=\(Int(b.width))x\(Int(b.height))\(isMain)")
}
