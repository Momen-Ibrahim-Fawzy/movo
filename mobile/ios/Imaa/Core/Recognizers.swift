import CoreGraphics
import Foundation

/// Point in height units (x × aspect), y pointing down — same convention as desktop and Android.
struct P {
    var x: Double
    var y: Double
}

struct GestureEvent: Equatable {
    var gesture: String
    var phase: String = "start"
    var magnitude: Double = 1
    var source: String = "hand"
}

enum Geo {
    static func dist(_ a: P, _ b: P) -> Double { hypot(a.x - b.x, a.y - b.y) }

    static func angleAt(_ a: P, _ b: P, _ c: P) -> Double {
        let v1 = (a.x - b.x, a.y - b.y), v2 = (c.x - b.x, c.y - b.y)
        let n1 = hypot(v1.0, v1.1), n2 = hypot(v2.0, v2.1)
        if n1 < 1e-9 || n2 < 1e-9 { return 180 }
        let c = max(-1, min(1, (v1.0 * v2.0 + v1.1 * v2.1) / (n1 * n2)))
        return acos(c) * 180 / .pi
    }

    static func direction(_ a: P, _ b: P) -> Double { atan2(-(b.y - a.y), b.x - a.x) * 180 / .pi }

    static func angleDiff(_ a: Double, _ b: Double) -> Double {
        var d = (a - b + 180).truncatingRemainder(dividingBy: 360)
        if d < 0 { d += 360 }
        return abs(d - 180)
    }

    static func mean(_ pts: [P]) -> P {
        P(x: pts.map(\.x).reduce(0, +) / Double(pts.count), y: pts.map(\.y).reduce(0, +) / Double(pts.count))
    }
}

/// Port of desktop/imaa/core/hand.py.
final class HandRecognizer {
    var holdScale = 1.0
    var swipeEnabled = true
    private(set) var livePose: String?

    static let staticPoses: Set<String> = ["thumb_up", "thumb_down", "point_right", "point_left", "victory", "call", "fist", "rock", "three"]
    private let holdMs: [String: Double] = [
        "thumb_up": 300, "thumb_down": 300, "point_right": 300, "point_left": 300,
        "victory": 550, "call": 600, "fist": 600, "rock": 1200, "three": 550,
    ]

    struct Features {
        var palm: Double
        var extended: [Bool]
        var thumbDir: Double
        var indexDir: Double
        var pinchRatio: Double
        var indexReach: Double
        var center: P
        var indexTip: P
        var pinchPoint: P
    }

    private struct Sample { var t: Double; var x: Double; var y: Double; var open: Bool }

    private var raw: String?
    private var rawCount = 0
    private var stable: String?
    private var stableSince = 0.0
    private var fired: String?
    private var lastRepeat = 0.0
    private var lastStart = -10.0
    private var history: [Sample] = []
    private var swipeBlockUntil = 0.0
    private var pinching = false
    private var pinchStart = 0.0
    private var pinchOrigin = P(x: 0, y: 0)
    private var dragging = false
    private var dragRef = 0.0
    private var dragDir: String?
    private var joyActive = false
    private var joyAnchor = 0.0
    private var joyLast = 0.0
    private var joyDir: String?

    func reset() {
        raw = nil; rawCount = 0; stable = nil; stableSince = 0; fired = nil; lastRepeat = 0; lastStart = -10
        history.removeAll(); swipeBlockUntil = 0; pinching = false; dragging = false; dragDir = nil
        joyActive = false; joyDir = nil; livePose = nil
    }

    static func analyze(_ lm: [P]) -> Features {
        let wrist = lm[0]
        let palm = max(Geo.dist(wrist, lm[9]), 1e-6)
        var ext = [Bool](repeating: false, count: 5)
        let fingers = [[5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]
        for (i, f) in fingers.enumerated() {
            let far = Geo.dist(wrist, lm[f[3]]) > Geo.dist(wrist, lm[f[1]]) * 1.2
            let straight = Geo.angleAt(lm[f[0]], lm[f[1]], lm[f[3]]) > 130
            ext[i + 1] = far && straight
        }
        let thumbStraight = Geo.angleAt(lm[2], lm[3], lm[4]) > 140
        let thumbAway = Geo.dist(lm[4], lm[5]) > 0.6 * palm && Geo.dist(lm[4], lm[17]) > Geo.dist(lm[2], lm[17]) * 1.05
        ext[0] = thumbStraight && thumbAway
        return Features(
            palm: palm, extended: ext,
            thumbDir: Geo.direction(lm[2], lm[4]), indexDir: Geo.direction(lm[5], lm[8]),
            pinchRatio: Geo.dist(lm[4], lm[8]) / palm, indexReach: Geo.dist(wrist, lm[8]) / palm,
            center: Geo.mean([lm[0], lm[5], lm[9], lm[13], lm[17]]), indexTip: lm[8], pinchPoint: Geo.mean([lm[4], lm[8]])
        )
    }

    static func classify(_ f: Features, tol: Double = 35) -> String? {
        let thumb = f.extended[0]
        let four = Array(f.extended[1...4])
        switch four {
        case [false, false, false, false]:
            if !thumb { return "fist" }
            if Geo.angleDiff(f.thumbDir, 90) <= tol + 5 { return "thumb_up" }
            if Geo.angleDiff(f.thumbDir, -90) <= tol + 5 { return "thumb_down" }
            return nil
        case [true, false, false, false]:
            if Geo.angleDiff(f.indexDir, 0) <= tol { return "point_right" }
            if Geo.angleDiff(f.indexDir, 180) <= tol { return "point_left" }
            if Geo.angleDiff(f.indexDir, 90) <= tol { return "point_up" }
            return nil
        case [true, true, false, false]: return "victory"
        case [true, true, true, false]: return "three"
        case [true, false, false, true]: return "rock"
        case [false, false, false, true]: return thumb ? "call" : nil
        case [true, true, true, true]: return "open_palm"
        default: return nil
        }
    }

    func update(_ lm: [P]?, t: Double) -> [GestureEvent] {
        guard let lm, lm.count >= 21 else { reset(); return [] }
        let f = Self.analyze(lm)
        var events: [GestureEvent] = []
        let label = Self.classify(f)
        history.append(Sample(t: t, x: f.center.x, y: f.center.y, open: label == "open_palm"))
        history.removeAll { t - $0.t > 0.45 }
        let speed = self.speed(t)
        updateStable(label, t)
        if swipeEnabled, let ev = detectSwipe(t) { events.append(ev) }
        let (pinchEvents, active) = updatePinch(f, t)
        events += pinchEvents
        if active { livePose = "pinch"; joyActive = false; return events }
        events += updateJoystick(f, t)
        if speed <= 1.1 { events += updateStatic(t) } else { stableSince = t }
        return events
    }

    private func speed(_ t: Double) -> Double {
        let recent = history.filter { t - $0.t <= 0.15 }
        guard recent.count >= 2, let a = recent.first, let b = recent.last, b.t > a.t else { return 0 }
        return Geo.dist(P(x: a.x, y: a.y), P(x: b.x, y: b.y)) / (b.t - a.t)
    }

    private func updateStable(_ label: String?, _ t: Double) {
        if label == raw { rawCount += 1 } else { raw = label; rawCount = 1 }
        if rawCount >= 2 && label != stable {
            stable = label
            stableSince = t
            if label != fired { fired = nil }
        }
        livePose = stable
    }

    private func start(_ g: String, _ t: Double, _ m: Double = 1) -> GestureEvent? {
        if t - lastStart < 0.25 { return nil }
        lastStart = t
        return GestureEvent(gesture: g, phase: "start", magnitude: m, source: "hand")
    }

    private func detectSwipe(_ t: Double) -> GestureEvent? {
        guard t >= swipeBlockUntil, history.count >= 3, let first = history.first, let last = history.last else { return nil }
        let openRatio = Double(history.filter(\.open).count) / Double(history.count)
        if openRatio < 0.6 { return nil }
        let dx = last.x - first.x, dy = last.y - first.y
        if abs(dx) >= 0.30 && abs(dy) < abs(dx) * 0.6 {
            swipeBlockUntil = t + 0.8
            history.removeAll()
            stableSince = t
            return start(dx > 0 ? "swipe_right" : "swipe_left", t)
        }
        return nil
    }

    private func updatePinch(_ f: Features, _ t: Double) -> ([GestureEvent], Bool) {
        var events: [GestureEvent] = []
        let canPinch = f.indexReach > 1.15 && !["fist", "thumb_up", "thumb_down"].contains(stable ?? "")
        if !pinching {
            if canPinch && f.pinchRatio < 0.28 {
                pinching = true; pinchStart = t; pinchOrigin = f.pinchPoint; dragging = false; dragDir = nil
            }
            return (events, pinching)
        }
        if f.pinchRatio > 0.42 {
            if !dragging && (t - pinchStart) * 1000 <= 450 && Geo.dist(f.pinchPoint, pinchOrigin) < 0.08, let ev = start("pinch", t) {
                events.append(ev)
            }
            pinching = false; dragging = false
            return (events, false)
        }
        if !dragging && (t - pinchStart) * 1000 >= 350 { dragging = true; dragRef = f.pinchPoint.y }
        if dragging {
            var delta = dragRef - f.pinchPoint.y
            while abs(delta) >= 0.07 {
                let d = delta > 0 ? "up" : "down"
                events.append(GestureEvent(gesture: "pinch_drag_\(d)", phase: dragDir == d ? "repeat" : "start", magnitude: 1, source: "hand"))
                dragDir = d
                dragRef -= delta > 0 ? 0.07 : -0.07
                delta = dragRef - f.pinchPoint.y
            }
        }
        return (events, true)
    }

    private func updateJoystick(_ f: Features, _ t: Double) -> [GestureEvent] {
        guard stable == "point_up" else { joyActive = false; joyDir = nil; return [] }
        if !joyActive {
            if (t - stableSince) * 1000 >= 220 * holdScale { joyActive = true; joyAnchor = f.indexTip.y; joyLast = t }
            return []
        }
        let offset = joyAnchor - f.indexTip.y
        let excess = abs(offset) - 0.035
        if excess <= 0 || (t - joyLast) * 1000 < 90 {
            if excess <= 0 { joyDir = nil }
            return []
        }
        joyLast = t
        let d = offset > 0 ? "up" : "down"
        let phase = joyDir == d ? "repeat" : "start"
        joyDir = d
        return [GestureEvent(gesture: "index_up_move_\(d)", phase: phase, magnitude: 0.25 + 0.75 * min(1, excess / 0.15), source: "hand")]
    }

    private func updateStatic(_ t: Double) -> [GestureEvent] {
        guard let label = stable, Self.staticPoses.contains(label) else { return [] }
        let hold = (holdMs[label] ?? 400) * holdScale / 1000
        if t - stableSince < hold { return [] }
        if fired != label {
            guard let ev = start(label, t) else { return [] }
            fired = label; lastRepeat = t
            return [ev]
        }
        if (t - lastRepeat) * 1000 >= 280 {
            lastRepeat = t
            return [GestureEvent(gesture: label, phase: "repeat", magnitude: 1, source: "hand")]
        }
        return []
    }
}

struct FaceObservation {
    var yaw: Double
    var pitch: Double
    var roll: Double
    var expressions: [String: Double]?
}

/// Port of desktop/imaa/core/head.py.
final class HeadRecognizer {
    var sensitivity = 1.0
    var holdScale = 1.0
    private(set) var livePose: String?
    private(set) var baseline: (Double, Double, Double)?

    private var samples: [(Double, Double, Double)] = []
    private var holdLabel: String?
    private var holdSince = 0.0
    private var fired: String?
    private var lastRepeat = 0.0
    private var pitchHist: [(Double, Double, Double)] = []
    private var yawHist: [(Double, Double, Double)] = []
    private var blockUntil = 0.0
    private var exprSince: [String: Double] = [:]
    private var exprFired: Set<String> = []

    static func poseFromPoints(_ a: P, _ b: P, _ nose: P) -> (Double, Double, Double) {
        let (left, right) = a.x <= b.x ? (a, b) : (b, a)
        let ex = right.x - left.x, ey = right.y - left.y
        let eyeDist = max(hypot(ex, ey), 1e-6)
        let r = atan2(ey, ex)
        let mid = P(x: (left.x + right.x) / 2, y: (left.y + right.y) / 2)
        let nx = nose.x - mid.x, ny = nose.y - mid.y
        let lx = (nx * cos(-r) - ny * sin(-r)) / eyeDist
        let ly = (nx * sin(-r) + ny * cos(-r)) / eyeDist
        return (atan2(lx, 0.5) * 180 / .pi, -ly * 119, r * 180 / .pi)
    }

    func recalibrate() {
        samples.removeAll(); baseline = nil; holdLabel = nil; fired = nil
        pitchHist.removeAll(); yawHist.removeAll(); blockUntil = 0; exprSince.removeAll(); exprFired.removeAll()
    }

    func update(_ obs: FaceObservation?, t: Double) -> [GestureEvent] {
        guard let obs else { holdLabel = nil; fired = nil; livePose = nil; pitchHist.removeAll(); yawHist.removeAll(); return [] }
        guard let base = baseline else {
            samples.append((obs.yaw, obs.pitch, obs.roll))
            if samples.count >= 12 {
                func med(_ v: [Double]) -> Double { v.sorted()[v.count / 2] }
                baseline = (med(samples.map(\.0)), med(samples.map(\.1)), med(samples.map(\.2)))
            }
            return []
        }
        let dy = obs.yaw - base.0, dp = obs.pitch - base.1, dr = obs.roll - base.2
        if abs(dy) < 5 && abs(dp) < 5 && abs(dr) < 5 {
            let a = 0.01
            baseline = (base.0 * (1 - a) + obs.yaw * a, base.1 * (1 - a) + obs.pitch * a, base.2 * (1 - a) + obs.roll * a)
        }
        var events = dynamic(dy, dp, t)
        events += holds(dy, dp, dr, t)
        if let e = obs.expressions { events += expressions(e, t) }
        return events
    }

    private func dynamic(_ dy: Double, _ dp: Double, _ t: Double) -> [GestureEvent] {
        pitchHist.append((t, dp, dy)); yawHist.append((t, dy, dp))
        pitchHist.removeAll { t - $0.0 > 1.0 }
        yawHist.removeAll { t - $0.0 > 1.4 }
        if t < blockUntil { return [] }
        let nod = 9 / sensitivity
        let below = pitchHist.filter { $0.1 < -nod }
        if let f = below.first, let l = below.last, dp > -nod / 3, let start = pitchHist.first,
           l.0 - f.0 < 0.5, start.1 > -nod / 2, (pitchHist.map { abs($0.2) }.max() ?? 0) < 12 {
            return fire("nod", t)
        }
        let shake = 9 / sensitivity
        var signs: [Int] = []
        for (_, y, p) in yawHist {
            if abs(p) > 14 { signs.removeAll(); break }
            let s = y > shake ? 1 : (y < -shake ? -1 : 0)
            if s != 0 && signs.last != s { signs.append(s) }
        }
        if signs.count >= 3 { return fire("shake", t) }
        return []
    }

    private func fire(_ name: String, _ t: Double) -> [GestureEvent] {
        blockUntil = t + 1
        pitchHist.removeAll(); yawHist.removeAll(); holdLabel = nil
        livePose = name
        return [GestureEvent(gesture: name, phase: "start", magnitude: 1, source: "head")]
    }

    private func holds(_ dy: Double, _ dp: Double, _ dr: Double, _ t: Double) -> [GestureEvent] {
        let axes: [(String, Double, Double)] = [
            ("turn_right", dy, 20.0), ("turn_left", -dy, 20.0), ("look_up", dp, 12.0),
            ("look_down", -dp, 12.0), ("tilt_right", dr, 15.0), ("tilt_left", -dr, 15.0),
        ]
        var cands: [(Double, String)] = []
        for (name, value, thr) in axes {
            let th = thr / sensitivity
            if value > th { cands.append((value / th, name)) }
        }
        let label = cands.max { $0.0 < $1.0 }?.1
        if label != holdLabel {
            holdLabel = label; holdSince = t
            if label == nil { fired = nil }
        }
        livePose = label ?? (t < blockUntil ? livePose : nil)
        guard let label, t >= blockUntil, (t - holdSince) * 1000 >= 450 * holdScale else { return [] }
        if fired != label { fired = label; lastRepeat = t; return [GestureEvent(gesture: label, phase: "start", magnitude: 1, source: "head")] }
        if (t - lastRepeat) * 1000 >= 380 { lastRepeat = t; return [GestureEvent(gesture: label, phase: "repeat", magnitude: 1, source: "head")] }
        return []
    }

    private func expressions(_ e: [String: Double], _ t: Double) -> [GestureEvent] {
        var events: [GestureEvent] = []
        let on = 0.5 / sensitivity, off = on * 0.6
        for (name, hold) in [("mouth_open", 350.0), ("smile", 450.0), ("brows_up", 400.0)] {
            let v = e[name] ?? 0
            if v >= on {
                if let since = exprSince[name] {
                    if !exprFired.contains(name) && (t - since) * 1000 >= hold * holdScale {
                        exprFired.insert(name); livePose = name
                        events.append(GestureEvent(gesture: name, phase: "start", magnitude: 1, source: "head"))
                    }
                } else { exprSince[name] = t }
            } else if v < off {
                exprSince[name] = nil
                exprFired.remove(name)
            }
        }
        return events
    }
}
