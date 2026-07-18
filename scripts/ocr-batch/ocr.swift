import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count > 1 else {
  FileHandle.standardError.write("usage: ocr <image>\n".data(using:.utf8)!); exit(2)
}
guard let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
  FileHandle.standardError.write("cannot load: \(args[1])\n".data(using:.utf8)!); exit(1)
}
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = true
req.recognitionLanguages = ["ja-JP","en-US"]
do {
  try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
  for o in (req.results ?? []) { if let t = o.topCandidates(1).first { print(t.string) } }
} catch {
  FileHandle.standardError.write("ocr error: \(error)\n".data(using:.utf8)!); exit(1)
}
