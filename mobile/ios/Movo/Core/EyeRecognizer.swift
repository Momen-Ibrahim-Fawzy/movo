import Foundation

/// Eye features in the user's left/right (see desktop/movo/core/eyes.py).
struct EyeFeatures {
    var earLeft: Double
    var earRight: Double
    var blinkLeft: Double?
    var blinkRight: Double?
    var gazeX: Double = 0
    var gazeY: Double = 0
    var lookUp: Double = 0
    var lookDown: Double = 0
    var smile: Double = 0
}

struct EyeCalibration: Codable, Equatable {
    var openL: Double, openR: Double, closedL: Double, closedR: Double, gazeX: Double, gazeY: Double
}

/// Port of the desktop eye recogniser: winks, double/long blinks, eyes closed, held glances; glasses-aware.
final class EyeRecognizer {
    var sensitivity = 1.0
    var holdScale = 1.0
    var glasses = false { didSet { if glasses != oldValue { window = glasses ? 5 : 3 } } }
    var calibration: EyeCalibration? { didSet { if let c = calibration { center = (c.gazeX, c.gazeY); centerSamples = 999 } } }
    private(set) var livePose: String?
    private(set) var openness: (Double, Double) = (1, 1)

    private var window = 3
    private var buffers: [[Double]] = Array(repeating: [], count: 8)
    private var closed = [false, false]
    private var bothSince: Double?
    private var closedFired = false
    private var lastShort: Double?
    private var winkSide: Int?
    private var winkSince = 0.0
    private var winkFired = false
    private var glance: String?
    private var glanceSince = 0.0
    private var glanceFired = false
    private var glanceLast = 0.0
    private var earHist: [(Double, Double)] = []
    private var center = (0.0, 0.0)
    private var centerSamples = 0
    private var capture: String?
    private var captured: [String: [(Double, Double, Double, Double)]] = [:]
    private var muteFor = 0.0
    private var muteUntil = -1.0

    private func med(_ i: Int, _ v: Double) -> Double {
        buffers[i].append(v)
        if buffers[i].count > window { buffers[i].removeFirst(buffers[i].count - window) }
        let s = buffers[i].sorted()
        return s[s.count / 2]
    }

    func reset() {
        closed = [false, false]; bothSince = nil; closedFired = false; lastShort = nil
        winkSide = nil; winkFired = false; glance = nil; glanceFired = false; livePose = nil
    }

    func beginCapture(_ kind: String) { captured[kind] = []; capture = kind }
    func endCapture() { capture = nil; muteFor = 1.5 }

    func finishCalibration() -> EyeCalibration? {
        let op = captured["open"] ?? [], cl = captured["closed"] ?? []
        captured = [:]
        guard op.count >= 5, cl.count >= 5 else { return nil }
        func m(_ rows: [(Double, Double, Double, Double)], _ pick: ((Double, Double, Double, Double)) -> Double) -> Double {
            let s = rows.map(pick).sorted()
            return s[s.count / 2]
        }
        let c = EyeCalibration(
            openL: m(op) { $0.0 }, openR: m(op) { $0.1 }, closedL: m(cl) { $0.0 }, closedR: m(cl) { $0.1 },
            gazeX: m(op) { $0.2 }, gazeY: m(op) { $0.3 }
        )
        guard min(c.openL - c.closedL, c.openR - c.closedR) >= 0.03 else { return nil }
        calibration = c
        return c
    }

    func update(_ feat: EyeFeatures?, t: Double, yaw: Double = 0, pitch: Double = 0, headBusy: Bool = false) -> [GestureEvent] {
        guard let feat else { reset(); return [] }
        let ear = (med(0, feat.earLeft), med(1, feat.earRight))
        let bs: (Double?, Double?) = (feat.blinkLeft.map { med(2, $0) }, feat.blinkRight.map { med(3, $0) })
        let gx = med(4, feat.gazeX), gy = med(5, feat.gazeY)
        let up = med(6, feat.lookUp), down = med(7, feat.lookDown)
        if muteFor > 0 { muteUntil = t + muteFor; muteFor = 0 }
        if let kind = capture {
            captured[kind]?.append((ear.0, ear.1, gx, gy))
            bothSince = nil; winkSide = nil; glance = nil
            return []
        }
        let frontal = abs(yaw) < 20 && abs(pitch) < 20
        if frontal { earHist.append(ear); if earHist.count > 400 { earHist.removeFirst() } }
        let c = [closure(0, ear.0, bs.0, down), closure(1, ear.1, bs.1, down)]
        openness = (1 - c[0], 1 - c[1])
        if !frontal || headBusy || t < muteUntil { bothSince = nil; winkSide = nil; glance = nil; livePose = nil; return [] }
        let on = min(0.85, 0.6 / sensitivity)
        for i in 0..<2 {
            if !closed[i] && c[i] >= on { closed[i] = true } else if closed[i] && c[i] <= 0.35 { closed[i] = false }
        }
        var events = blinks(t)
        events += winks(t, c, feat.smile)
        let bothOpen = !closed[0] && !closed[1]
        if bothOpen { updateCenter(gx, gy, yaw, pitch) }
        events += glances(t, gx, gy, up, down, bothOpen, yaw, pitch)
        return events
    }

    private func openLevel(_ i: Int) -> Double {
        if let c = calibration { return i == 0 ? c.openL : c.openR }
        let v = earHist.map { i == 0 ? $0.0 : $0.1 }.sorted()
        if v.count >= 15 { return v[Int(Double(v.count) * 0.9) - 1] }
        return v.last ?? 0.3
    }

    private func closure(_ i: Int, _ ear: Double, _ bs: Double?, _ down: Double) -> Double {
        let open = max(openLevel(i), 1e-3)
        let closedEar = calibration.map { i == 0 ? $0.closedL : $0.closedR }
        let span = closedEar.map { open - $0 } ?? 0.6 * open
        let geo = max(0, min(1, (open - ear) / max(span, 1e-3)))
        var c = geo
        if let bs {
            let w = glasses ? 0.6 : 0.5
            c = w * bs + (1 - w) * geo
            if geo >= 0.9 && bs >= 0.3 { c = max(c, 0.75) }
        }
        return max(0, min(1, c - 0.35 * down))
    }

    private func blinks(_ t: Double) -> [GestureEvent] {
        if closed[0] && closed[1] {
            if let since = bothSince {
                if !closedFired && t - since >= 2 * holdScale {
                    closedFired = true; lastShort = nil; livePose = "eyes_closed"
                    return [GestureEvent(gesture: "eyes_closed", phase: "start", magnitude: 1, source: "eye")]
                }
            } else { bothSince = t }
            return []
        }
        guard let since = bothSince else { return [] }
        let d = t - since
        bothSince = nil
        if closedFired { closedFired = false; return [] }
        if d >= 0.6 * holdScale && d <= 1.5 * max(1, holdScale) {
            lastShort = nil; livePose = "blink_long"
            return [GestureEvent(gesture: "blink_long", phase: "start", magnitude: 1, source: "eye")]
        }
        if d >= 0.06 && d <= 0.45 {
            if let last = lastShort, t - last <= 0.8 {
                lastShort = nil; livePose = "blink_double"
                return [GestureEvent(gesture: "blink_double", phase: "start", magnitude: 1, source: "eye")]
            }
            lastShort = t
        }
        return []
    }

    private func winks(_ t: Double, _ c: [Double], _ smile: Double) -> [GestureEvent] {
        var side: Int?
        if closed[0] != closed[1] {
            let i = closed[0] ? 0 : 1
            if c[1 - i] < 0.3 && smile < 0.5 { side = i }
        }
        if side != winkSide {
            winkSide = side; winkSince = t
            if side == nil { winkFired = false }
            return []
        }
        guard let side, !winkFired, t - winkSince >= 0.35 * holdScale else { return [] }
        winkFired = true
        let name = side == 0 ? "wink_left" : "wink_right"
        livePose = name
        return [GestureEvent(gesture: name, phase: "start", magnitude: 1, source: "eye")]
    }

    private func updateCenter(_ gx: Double, _ gy: Double, _ yaw: Double, _ pitch: Double) {
        guard calibration == nil, abs(yaw) <= 5, abs(pitch) <= 5 else { return }
        if centerSamples < 15 {
            let n = Double(centerSamples + 1)
            center = (center.0 + (gx - center.0) / n, center.1 + (gy - center.1) / n)
            centerSamples += 1
        } else if abs(gx - center.0) < 0.05 && abs(gy - center.1) < 0.04 {
            center = (center.0 * 0.99 + gx * 0.01, center.1 * 0.99 + gy * 0.01)
        }
    }

    private func glances(_ t: Double, _ gx: Double, _ gy: Double, _ up: Double, _ down: Double, _ bothOpen: Bool, _ yaw: Double, _ pitch: Double) -> [GestureEvent] {
        let k = sensitivity
        let hx = (gx - center.0) / (0.10 / k)
        let vIris = (gy - center.1) / (0.08 / k)
        let vy = (up != 0 || down != 0) ? (vIris + (up - down) / (0.5 / k)) / 2 : vIris
        var label: String?
        if bothOpen && abs(yaw) < 8 && abs(pitch) < 8 && centerSamples >= 15 {
            let best = [(hx, "eye_look_right"), (-hx, "eye_look_left"), (vy, "eye_look_up"), (-vy, "eye_look_down")].max { $0.0 < $1.0 }!
            if best.0 >= 1 { label = best.1 }
        }
        if label != glance { glance = label; glanceSince = t; glanceFired = false; return [] }
        guard let label, t - glanceSince >= 0.6 * holdScale else { return [] }
        livePose = label
        if !glanceFired { glanceFired = true; glanceLast = t; return [GestureEvent(gesture: label, phase: "start", magnitude: 1, source: "eye")] }
        if t - glanceLast >= 0.4 { glanceLast = t; return [GestureEvent(gesture: label, phase: "repeat", magnitude: 1, source: "eye")] }
        return []
    }
}
