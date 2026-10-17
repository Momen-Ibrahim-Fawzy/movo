import AVFoundation
import Vision

/// Front camera → Apple Vision (on-device, Neural Engine) → recognisers.
/// Frames are analysed in memory and released immediately; nothing is stored or sent.
final class GesturePipeline: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    var onEvents: (([GestureEvent]) -> Void)?
    var onPose: ((String?, Bool) -> Void)?  // live pose, someone in view

    var handEnabled = true
    var headEnabled = false
    var eyesEnabled = false
    let eyes = EyeRecognizer()
    var targetFps = 15.0
    let hand = HandRecognizer()
    let head = HeadRecognizer()

    private let session = AVCaptureSession()
    private let queue = DispatchQueue(label: "imaa.vision", qos: .userInitiated)
    private let handRequest: VNDetectHumanHandPoseRequest = {
        let r = VNDetectHumanHandPoseRequest()
        r.maximumHandCount = 1
        return r
    }()
    private let faceRequest = VNDetectFaceLandmarksRequest()
    private var lastFrame = 0.0
    private var lastSeen = 0.0
    private var configured = false

    private static let joints: [VNHumanHandPoseObservation.JointName] = [
        .wrist, .thumbCMC, .thumbMP, .thumbIP, .thumbTip,
        .indexMCP, .indexPIP, .indexDIP, .indexTip,
        .middleMCP, .middlePIP, .middleDIP, .middleTip,
        .ringMCP, .ringPIP, .ringDIP, .ringTip,
        .littleMCP, .littlePIP, .littleDIP, .littleTip,
    ]

    func start() {
        queue.async { [weak self] in
            guard let self else { return }
            if !self.configured { self.configure() }
            if !self.session.isRunning { self.session.startRunning() }
            self.lastSeen = CACurrentMediaTime()
        }
    }

    func stop() {
        queue.async { [weak self] in
            self?.session.stopRunning()
            self?.hand.reset()
        }
    }

    private func configure() {
        session.beginConfiguration()
        session.sessionPreset = .vga640x480
        guard
            let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front)
                ?? AVCaptureDevice.default(for: .video),
            let input = try? AVCaptureDeviceInput(device: device),
            session.canAddInput(input)
        else {
            session.commitConfiguration()
            return
        }
        session.addInput(input)
        let output = AVCaptureVideoDataOutput()
        output.alwaysDiscardsLateVideoFrames = true
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
        output.setSampleBufferDelegate(self, queue: queue)
        if session.canAddOutput(output) { session.addOutput(output) }
        if let connection = output.connection(with: .video) {
            if connection.isVideoOrientationSupported { connection.videoOrientation = .portrait }
            if connection.isVideoMirroringSupported {
                connection.automaticallyAdjustsVideoMirroring = false
                connection.isVideoMirrored = true
            }
        }
        session.commitConfiguration()
        configured = true
    }

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        let now = CACurrentMediaTime()
        let idle = now - lastSeen > 3
        let fps = idle ? 5 : targetFps
        guard now - lastFrame >= 1 / fps, let buffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        lastFrame = now
        let w = Double(CVPixelBufferGetWidth(buffer)), h = Double(CVPixelBufferGetHeight(buffer))
        let aspect = w / max(h, 1)
        var requests: [VNRequest] = []
        if handEnabled { requests.append(handRequest) }
        if headEnabled || eyesEnabled { requests.append(faceRequest) }
        guard !requests.isEmpty else { return }
        let handler = VNImageRequestHandler(cvPixelBuffer: buffer, orientation: .up, options: [:])
        do { try handler.perform(requests) } catch { return }

        var events: [GestureEvent] = []
        var present = false
        if handEnabled {
            let lm = landmarks(aspect: aspect)
            present = lm != nil
            events += hand.update(lm, t: now)
        }
        if headEnabled || eyesEnabled {
            let obs = face(aspect: aspect)
            present = present || obs != nil
            let headEvents = head.update(obs, t: now)
            if headEnabled { events += headEvents }
            if eyesEnabled {
                let d = head.baseline == nil ? (0.0, 0.0, 0.0) : head.delta
                events += eyes.update(obs?.eyes, t: now, yaw: d.0, pitch: d.1, headBusy: now - head.lastEventAt < 0.8)
            }
        }
        if present { lastSeen = now }
        let pose = hand.livePose ?? head.livePose ?? (eyesEnabled ? eyes.livePose : nil)
        DispatchQueue.main.async { [weak self] in
            self?.onPose?(pose, present)
            if !events.isEmpty { self?.onEvents?(events) }
        }
    }

    /// Vision uses a bottom-left origin; convert to height units with y down.
    private func landmarks(aspect: Double) -> [P]? {
        guard let obs = handRequest.results?.first, let points = try? obs.recognizedPoints(.all) else { return nil }
        var out: [P] = []
        for joint in Self.joints {
            guard let p = points[joint], p.confidence > 0.3 else { return nil }
            out.append(P(x: Double(p.location.x) * aspect, y: 1 - Double(p.location.y)))
        }
        return out
    }

    private func face(aspect: Double) -> FaceObservation? {
        guard let obs = faceRequest.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width }),
              let lm = obs.landmarks,
              let leftEye = lm.leftEye, let rightEye = lm.rightEye, let crest = lm.noseCrest else { return nil }
        let size = CGSize(width: aspect, height: 1)
        func pts(_ r: VNFaceLandmarkRegion2D) -> [P] { r.pointsInImage(imageSize: size).map { P(x: Double($0.x), y: 1 - Double($0.y)) } }
        let a = Geo.mean(pts(leftEye)), b = Geo.mean(pts(rightEye))
        guard let nose = pts(crest).max(by: { $0.y < $1.y }) else { return nil }
        let (yaw, pitch, roll) = HeadRecognizer.poseFromPoints(a, b, nose)
        var expressions: [String: Double] = [:]
        let eye = Geo.dist(a, b)
        if let inner = lm.innerLips, let outer = lm.outerLips, eye > 0 {
            let ip = pts(inner), op = pts(outer)
            let open = ((ip.map(\.y).max() ?? 0) - (ip.map(\.y).min() ?? 0)) / eye
            let width = ((op.map(\.x).max() ?? 0) - (op.map(\.x).min() ?? 0)) / eye
            expressions["mouth_open"] = max(0, min(1, (open - 0.08) / 0.35))
            expressions["smile"] = max(0, min(1, (width - 0.95) / 0.35))
        }
        // Eye openness from the eye outlines and gaze from the pupils. Assign eyes by screen side: the video is
        // mirrored, so the eye on the screen-left is the user's left eye.
        var eyeFeatures: EyeFeatures?
        if let lp = lm.leftPupil, let rp = lm.rightPupil {
            let regions = [(pts(leftEye), pts(lp)), (pts(rightEye), pts(rp))].sorted { Geo.mean($0.0).x < Geo.mean($1.0).x }
            func measure(_ outline: [P], _ pupil: [P]) -> (Double, Double, Double) {
                let xs = outline.map(\.x), ys = outline.map(\.y)
                let w = max((xs.max() ?? 0) - (xs.min() ?? 0), 1e-6), h = (ys.max() ?? 0) - (ys.min() ?? 0)
                let c = Geo.mean(pupil.isEmpty ? outline : pupil)
                let hx = (c.x - (xs.min() ?? 0)) / w - 0.5
                let vy = 0.5 - (c.y - (ys.min() ?? 0)) / max(h, 1e-6)
                return (h / w, hx, vy)
            }
            let l = measure(regions[0].0, regions[0].1), r = measure(regions[1].0, regions[1].1)
            eyeFeatures = EyeFeatures(earLeft: l.0, earRight: r.0, blinkLeft: nil, blinkRight: nil,
                                      gazeX: (l.1 + r.1) / 2, gazeY: (l.2 + r.2) / 2, smile: expressions["smile"] ?? 0)
        }
        return FaceObservation(yaw: yaw, pitch: pitch, roll: roll, expressions: expressions, eyes: eyeFeatures)
    }
}
