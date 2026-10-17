import XCTest
@testable import Imaa

/// Same synthetic hands as desktop/tests and the Android unit tests.
final class RecognizerTests: XCTestCase {
    private let mcps: [Int: P] = [1: P(x: -0.045, y: -0.17), 2: P(x: 0, y: -0.18), 3: P(x: 0.04, y: -0.17), 4: P(x: 0.075, y: -0.15)]

    private func finger(_ m: P, _ ext: Bool) -> [P] {
        ext ? [m, P(x: m.x, y: m.y - 0.06), P(x: m.x, y: m.y - 0.10), P(x: m.x, y: m.y - 0.135)]
            : [m, P(x: m.x, y: m.y - 0.045), P(x: m.x + 0.005, y: m.y - 0.015), P(x: m.x + 0.005, y: m.y + 0.02)]
    }

    private func hand(_ t: Bool, _ i: Bool, _ m: Bool, _ r: Bool, _ p: Bool, rotate: Double = 0, atX: Double = 0.65) -> [P] {
        let thumb = t ? [P(x: -0.03, y: -0.03), P(x: -0.07, y: -0.07), P(x: -0.11, y: -0.085), P(x: -0.15, y: -0.10)]
            : [P(x: -0.03, y: -0.03), P(x: -0.06, y: -0.07), P(x: -0.05, y: -0.11), P(x: -0.01, y: -0.13)]
        var pts = [P(x: 0, y: 0)] + thumb
        for (k, e) in zip([1, 2, 3, 4], [i, m, r, p]) { pts += finger(mcps[k]!, e) }
        let rad = rotate * .pi / 180
        return pts.map { P(x: atX + $0.x * cos(rad) + $0.y * sin(rad), y: 0.6 - $0.x * sin(rad) + $0.y * cos(rad)) }
    }

    func testClassify() {
        XCTAssertEqual(HandRecognizer.classify(HandRecognizer.analyze(hand(true, true, true, true, true))), "open_palm")
        XCTAssertEqual(HandRecognizer.classify(HandRecognizer.analyze(hand(false, false, false, false, false))), "fist")
        XCTAssertEqual(HandRecognizer.classify(HandRecognizer.analyze(hand(false, true, true, false, false))), "victory")
        XCTAssertEqual(HandRecognizer.classify(HandRecognizer.analyze(hand(true, false, false, false, false, rotate: -90))), "thumb_up")
        XCTAssertEqual(HandRecognizer.classify(HandRecognizer.analyze(hand(false, true, false, false, false, rotate: -90))), "point_right")
        XCTAssertEqual(HandRecognizer.classify(HandRecognizer.analyze(hand(false, true, false, false, false, rotate: 90))), "point_left")
    }

    func testHeldPoseFiresOnce() {
        let rec = HandRecognizer()
        var events: [GestureEvent] = []
        for k in 0..<36 { events += rec.update(hand(true, false, false, false, false, rotate: -90), t: Double(k) / 30) }
        XCTAssertEqual(events.filter { $0.phase == "start" }.map(\.gesture), ["thumb_up"])
    }

    func testSwipe() {
        let rec = HandRecognizer()
        var events: [GestureEvent] = []
        for k in 0..<10 { events += rec.update(hand(true, true, true, true, true, atX: 0.3 + 0.05 * Double(k)), t: Double(k) / 30) }
        XCTAssertEqual(events.map(\.gesture), ["swipe_right"])
    }

    func testPairingLink() {
        let parsed = RemoteClient.parse(URL(string: "imaa://pair?host=192.168.1.5&port=47813&code=123456")!)
        XCTAssertEqual(parsed?.0, "192.168.1.5")
        XCTAssertEqual(parsed?.1, 47813)
        XCTAssertEqual(parsed?.2, "123456")
    }
}
