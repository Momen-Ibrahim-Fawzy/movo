import CryptoKit
import Foundation
import UIKit

/// Sends gesture names (never images) to the Movo desktop app on the local network. See docs/REMOTE_PROTOCOL.md.
final class RemoteClient {
    enum Status: String { case off, connecting, connected, failed }

    var onStatus: ((Status) -> Void)?
    private var task: URLSessionWebSocketTask?
    private var authed = false
    private let code: String

    init(host: String, port: Int, code: String) {
        self.code = code
        guard !host.isEmpty, let url = URL(string: "ws://\(host):\(port)") else { return }
        task = URLSession(configuration: .default).webSocketTask(with: url)
    }

    static func proof(code: String, nonce: String) -> String {
        let mac = HMAC<SHA256>.authenticationCode(for: Data(nonce.utf8), using: SymmetricKey(data: Data(code.utf8)))
        return mac.map { String(format: "%02x", $0) }.joined()
    }

    /// movo://pair?host=…&port=…&code=…
    static func parse(_ url: URL) -> (String, Int, String)? {
        guard url.scheme == "movo", url.host == "pair", let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems,
              let host = items.first(where: { $0.name == "host" })?.value,
              let code = items.first(where: { $0.name == "code" })?.value else { return nil }
        let port = Int(items.first(where: { $0.name == "port" })?.value ?? "") ?? 47813
        return (host, port, code)
    }

    func connect() {
        guard let task else { onStatus?(.failed); return }
        onStatus?(.connecting)
        task.resume()
        receive()
    }

    private func receive() {
        task?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .failure:
                self.authed = false
                DispatchQueue.main.async { self.onStatus?(.failed) }
            case .success(let message):
                if case .string(let text) = message,
                   let data = text.data(using: .utf8),
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    self.handle(json)
                }
                self.receive()
            }
        }
    }

    private func handle(_ json: [String: Any]) {
        switch json["type"] as? String {
        case "challenge":
            let nonce = json["nonce"] as? String ?? ""
            let device = UIDevice.current.name
            send(["type": "auth", "device": device, "proof": Self.proof(code: code, nonce: nonce)])
        case "welcome":
            authed = true
            DispatchQueue.main.async { self.onStatus?(.connected) }
        default:
            break
        }
    }

    func send(gesture: GestureEvent) {
        guard authed else { return }
        send(["type": "gesture", "gesture": gesture.gesture, "phase": gesture.phase, "magnitude": gesture.magnitude])
    }

    private func send(_ obj: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: obj), let text = String(data: data, encoding: .utf8) else { return }
        task?.send(.string(text)) { _ in }
    }

    func close() {
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
        onStatus?(.off)
    }
}
