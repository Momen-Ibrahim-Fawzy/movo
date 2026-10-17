import SwiftUI

struct HelpView: View {
    private let steps = (1...5).map { ("help.s\($0)", "help.s\($0)_d") }

    var body: some View {
        List {
            Section {
                ForEach(Array(steps.enumerated()), id: \.offset) { i, step in
                    HStack(alignment: .top, spacing: 12) {
                        Text("\(i + 1)")
                            .font(.subheadline.bold())
                            .foregroundStyle(Brand.accent)
                            .frame(width: 28, height: 28)
                            .background(Circle().fill(Brand.accent.opacity(0.12)))
                        VStack(alignment: .leading, spacing: 3) {
                            Text(LocalizedStringKey(step.0)).font(.headline)
                            Text(LocalizedStringKey(step.1)).font(.subheadline).foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            Section("help.gestures") {
                ForEach(Catalog.hand + Catalog.head) { g in
                    HStack {
                        Text(g.emoji)
                        Text(g.name)
                        Spacer()
                        Text(Catalog.viewerBindings[g.id]?.title ?? "—").font(.footnote).foregroundStyle(.secondary)
                    }
                }
            }
        }
        .navigationTitle("help.title")
    }
}
