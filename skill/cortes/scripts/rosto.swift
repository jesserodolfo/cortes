// Detecta rostos a cada PASSO segundos com Vision e grava as caixas em JSON.
// Uso: swift rosto.swift VIDEO SAIDA.json [PASSO=0.5]
// Saída: {"largura", "altura", "passo", "amostras": [{"t", "rostos": [{"x","y","w","h"}]}]}
// x/y = centro do rosto e w/h = tamanho, normalizados 0–1, origem no canto de cima à esquerda.
import AVFoundation
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("uso: swift rosto.swift VIDEO SAIDA.json [PASSO]\n".data(using: .utf8)!)
    exit(2)
}
let passo = args.count > 3 ? (Double(args[3]) ?? 0.5) : 0.5
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
guard let trilha = asset.tracks(withMediaType: .video).first else {
    FileHandle.standardError.write("sem trilha de vídeo\n".data(using: .utf8)!)
    exit(1)
}
let tamanho = trilha.naturalSize.applying(trilha.preferredTransform)
let duracao = CMTimeGetSeconds(asset.duration)

let gerador = AVAssetImageGenerator(asset: asset)
gerador.appliesPreferredTrackTransform = true
gerador.requestedTimeToleranceBefore = CMTime(value: 1, timescale: 30)
gerador.requestedTimeToleranceAfter = CMTime(value: 1, timescale: 30)
gerador.maximumSize = CGSize(width: 960, height: 960)

var amostras: [[String: Any]] = []
var t = 0.0
while t < duracao {
    var rostos: [[String: Double]] = []
    if let imagem = try? gerador.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
        let pedido = VNDetectFaceRectanglesRequest()
        try? VNImageRequestHandler(cgImage: imagem, options: [:]).perform([pedido])
        for rosto in pedido.results ?? [] {
            let b = rosto.boundingBox  // Vision: origem embaixo à esquerda
            rostos.append(["x": Double(b.midX), "y": Double(1 - b.midY),
                           "w": Double(b.width), "h": Double(b.height)])
        }
    }
    amostras.append(["t": (t * 1000).rounded() / 1000, "rostos": rostos])
    t += passo
}

let saida: [String: Any] = ["largura": Int(abs(tamanho.width)), "altura": Int(abs(tamanho.height)),
                            "passo": passo, "amostras": amostras]
let dados = try JSONSerialization.data(withJSONObject: saida)
try dados.write(to: URL(fileURLWithPath: args[2]))
let comRosto = amostras.filter { !(($0["rostos"] as? [Any]) ?? []).isEmpty }.count
print("\(amostras.count) amostras, \(comRosto) com rosto -> \(args[2])")
