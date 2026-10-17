import Foundation

struct GestureInfo: Identifiable, Hashable {
    let id: String
    let emoji: String
    let accurateOnly: Bool

    var name: String { NSLocalizedString("g.\(id)", comment: "") }
}

/// Actions available inside the iOS app (the viewer). When the phone acts as a remote, gestures are sent to the
/// computer, which applies its own bindings.
enum ViewerAction: String, CaseIterable, Identifiable {
    case none, next, previous, scrollUp = "scroll_up", scrollDown = "scroll_down", zoomIn = "zoom_in", zoomOut = "zoom_out", pause = "pause_control"

    var id: String { rawValue }
    var title: String { NSLocalizedString("a.\(rawValue)", comment: "") }
    var repeatable: Bool { [.next, .previous, .scrollUp, .scrollDown, .zoomIn, .zoomOut].contains(self) }
}

enum Catalog {
    static let hand: [GestureInfo] = [
        .init(id: "thumb_up", emoji: "👍", accurateOnly: false), .init(id: "thumb_down", emoji: "👎", accurateOnly: false),
        .init(id: "point_right", emoji: "👉", accurateOnly: false), .init(id: "point_left", emoji: "👈", accurateOnly: false),
        .init(id: "pinch", emoji: "🤏", accurateOnly: false), .init(id: "index_up_move_up", emoji: "☝️", accurateOnly: false),
        .init(id: "index_up_move_down", emoji: "☝️", accurateOnly: false), .init(id: "pinch_drag_up", emoji: "🤏", accurateOnly: false),
        .init(id: "pinch_drag_down", emoji: "🤏", accurateOnly: false), .init(id: "swipe_right", emoji: "✋", accurateOnly: false),
        .init(id: "swipe_left", emoji: "✋", accurateOnly: false), .init(id: "victory", emoji: "✌️", accurateOnly: false),
        .init(id: "call", emoji: "🤙", accurateOnly: false), .init(id: "fist", emoji: "✊", accurateOnly: false),
        .init(id: "rock", emoji: "🤘", accurateOnly: false), .init(id: "three", emoji: "🖖", accurateOnly: false),
    ]
    static let head: [GestureInfo] = [
        .init(id: "nod", emoji: "🙂", accurateOnly: false), .init(id: "shake", emoji: "🙅", accurateOnly: false),
        .init(id: "tilt_right", emoji: "↗️", accurateOnly: false), .init(id: "tilt_left", emoji: "↖️", accurateOnly: false),
        .init(id: "look_up", emoji: "⬆️", accurateOnly: false), .init(id: "look_down", emoji: "⬇️", accurateOnly: false),
        .init(id: "turn_right", emoji: "➡️", accurateOnly: false), .init(id: "turn_left", emoji: "⬅️", accurateOnly: false),
        .init(id: "mouth_open", emoji: "😮", accurateOnly: true), .init(id: "smile", emoji: "😁", accurateOnly: true),
    ]
    static let all: [String: GestureInfo] = Dictionary(uniqueKeysWithValues: (hand + head).map { ($0.id, $0) })

    static let viewerBindings: [String: ViewerAction] = [
        "point_right": .next, "point_left": .previous, "swipe_left": .next, "swipe_right": .previous,
        "tilt_right": .next, "tilt_left": .previous, "index_up_move_up": .scrollUp, "index_up_move_down": .scrollDown,
        "look_up": .scrollUp, "look_down": .scrollDown, "pinch_drag_up": .zoomIn, "pinch_drag_down": .zoomOut,
        "rock": .pause,
    ]
}
