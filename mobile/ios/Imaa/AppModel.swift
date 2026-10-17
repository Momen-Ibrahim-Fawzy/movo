import AVFoundation
import SwiftUI
import UIKit

/// App-wide state. Settings live in UserDefaults on the device only.
@MainActor
final class AppModel: ObservableObject {
    @Published var running = false
    @Published var paused = false
    @Published var livePose: String?
    @Published var lastAction: String?
    @Published var someoneInView = false
    @Published var cameraDenied = false
    @Published var remoteStatus: RemoteClient.Status = .off
    @Published var pairedBanner = false

    @AppStorage("theme") var theme = "system"
    @AppStorage("handEnabled") var handEnabled = true { didSet { pipeline.handEnabled = handEnabled } }
    @AppStorage("headEnabled") var headEnabled = false { didSet { pipeline.headEnabled = headEnabled } }
    @AppStorage("holdScale") var holdScale = 1.0 { didSet { pipeline.hand.holdScale = holdScale } }
    @AppStorage("headSensitivity") var headSensitivity = 1.0 { didSet { pipeline.head.sensitivity = headSensitivity } }
    @AppStorage("powerMode") var powerMode = "balanced" { didSet { pipeline.targetFps = fps(for: powerMode) } }
    @AppStorage("practice") var practice = false
    @AppStorage("remoteEnabled") var remoteEnabled = false
    @AppStorage("remoteHost") var remoteHost = ""
    @AppStorage("remotePort") var remotePort = 47813
    @AppStorage("remoteCode") var remoteCode = ""

    /// Actions requested by gestures, consumed by the viewer.
    @Published var viewerCommand: (ViewerAction, UUID)?

    private let pipeline = GesturePipeline()
    private var remote: RemoteClient?

    init() {
        pipeline.handEnabled = handEnabled
        pipeline.headEnabled = headEnabled
        pipeline.hand.holdScale = holdScale
        pipeline.head.sensitivity = headSensitivity
        pipeline.targetFps = fps(for: powerMode)
        pipeline.onEvents = { [weak self] events in self?.handle(events) }
        pipeline.onPose = { [weak self] pose, present in
            self?.livePose = pose
            self?.someoneInView = present
        }
    }

    private func fps(for mode: String) -> Double {
        switch mode {
        case "eco": return 10
        case "performance": return 24
        default: return 15
        }
    }

    func toggle() {
        running ? stop() : start()
    }

    func start() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            begin()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { granted in
                Task { @MainActor in
                    if granted { self.begin() } else { self.cameraDenied = true }
                }
            }
        default:
            cameraDenied = true
        }
    }

    private func begin() {
        cameraDenied = false
        pipeline.start()
        running = true
        paused = false
        UIApplication.shared.isIdleTimerDisabled = true
        if remoteEnabled { connectRemote() }
    }

    func stop() {
        pipeline.stop()
        running = false
        paused = false
        livePose = nil
        UIApplication.shared.isIdleTimerDisabled = false
        remote?.close()
        remote = nil
    }

    func recalibrate() { pipeline.head.recalibrate() }

    func connectRemote() {
        remote?.close()
        let client = RemoteClient(host: remoteHost, port: remotePort, code: remoteCode)
        client.onStatus = { [weak self] status in Task { @MainActor in self?.remoteStatus = status } }
        remote = client
        client.connect()
    }

    func disconnectRemote() {
        remote?.close()
        remote = nil
        remoteStatus = .off
    }

    func handlePairing(_ url: URL) {
        guard let pairing = RemoteClient.parse(url) else { return }
        remoteHost = pairing.0
        remotePort = pairing.1
        remoteCode = pairing.2
        pairedBanner = true
    }

    private func handle(_ events: [GestureEvent]) {
        for ev in events {
            let action = Catalog.viewerBindings[ev.gesture] ?? ViewerAction.none
            if practice {
                if ev.phase == "start", let g = Catalog.all[ev.gesture] { lastAction = "\(g.emoji)  \(g.name)" }
                continue
            }
            if action == .pause {
                if ev.phase == "start" { paused.toggle() }
                continue
            }
            if paused { continue }
            if remoteEnabled, remoteStatus == .connected {
                remote?.send(gesture: ev)
                if ev.phase == "start", let g = Catalog.all[ev.gesture] { lastAction = "📡  \(g.name)" }
                continue
            }
            guard action != .none, ev.phase == "start" || action.repeatable else { continue }
            viewerCommand = (action, UUID())
            lastAction = action.title
        }
    }
}
