import XCTest
@testable import Movo

/// Mirrors desktop/tests/test_eyes.py (iOS has no learned blink score, so features use eye openness only).
final class EyeRecognizerTests: XCTestCase {
    private func eye(_ l: Double = 0.30, _ r: Double = 0.30, gx: Double = 0) -> EyeFeatures {
        EyeFeatures(earLeft: l, earRight: r, blinkLeft: nil, blinkRight: nil, gazeX: gx)
    }

    private func run(_ rec: EyeRecognizer, _ seq: [(EyeFeatures, Double)], t0: Double = 1.5) -> [String] {
        var t = t0, names: [String] = []
        for (f, secs) in seq {
            for _ in 0..<max(1, Int((secs * 20).rounded())) {
                names += rec.update(f, t: t).filter { $0.phase == "start" }.map(\.gesture)
                t += 0.05
            }
        }
        return names
    }

    private func warm(glasses: Bool = false) -> EyeRecognizer {
        let r = EyeRecognizer()
        r.glasses = glasses
        _ = run(r, [(eye(), 1.5)], t0: 0)
        return r
    }

    func testNaturalBlinkIgnored() {
        XCTAssertEqual(run(warm(), [(eye(), 0.5), (eye(0.08, 0.08), 0.15), (eye(), 2)]), [])
    }

    func testDoubleBlinkWithAndWithoutGlasses() {
        for g in [false, true] {
            let seq = [(eye(0.08, 0.08), 0.2), (eye(), 0.25), (eye(0.08, 0.08), 0.2), (eye(), 0.5)]
            XCTAssertEqual(run(warm(glasses: g), seq), ["blink_double"])
        }
    }

    func testWinks() {
        XCTAssertEqual(run(warm(), [(eye(0.08, 0.30), 0.6), (eye(), 0.4)]), ["wink_left"])
        XCTAssertEqual(run(warm(), [(eye(0.30, 0.08), 0.6), (eye(), 0.4)]), ["wink_right"])
    }

    func testEyesClosed() {
        XCTAssertEqual(run(warm(), [(eye(0.08, 0.08), 3), (eye(), 0.5)]), ["eyes_closed"])
    }
}
