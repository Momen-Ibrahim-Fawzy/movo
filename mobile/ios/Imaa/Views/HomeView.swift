import SwiftUI

struct HomeView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    VStack(spacing: 12) {
                        PowerButton(running: model.running) { model.toggle() }
                        Text(LocalizedStringKey(model.running ? (model.paused ? "state.paused" : "state.running") : "state.stopped"))
                            .font(.title2.weight(.semibold))
                        Text(LocalizedStringKey(model.running ? (model.paused ? "state.paused_d" : "state.running_d") : "state.stopped_d"))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                        if model.running {
                            HStack(spacing: 6) {
                                Text("home.seeing")
                                Text(model.livePose.flatMap { Catalog.all[$0] }.map { "\($0.emoji)  \($0.name)" } ?? "—")
                            }
                            .font(.callout)
                            if !model.someoneInView {
                                Text("home.idle").font(.caption).foregroundStyle(.secondary)
                            }
                            Button(LocalizedStringKey(model.paused ? "home.resume" : "home.pause")) { model.paused.toggle() }
                                .buttonStyle(.bordered)
                        }
                        if model.cameraDenied {
                            Text("home.camera_denied").font(.footnote).foregroundStyle(.red).multilineTextAlignment(.center)
                            Button("home.open_settings") {
                                if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
                            }
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .card()

                    VStack(alignment: .leading, spacing: 10) {
                        Text("home.quick").font(.headline)
                        Toggle("home.hand", isOn: $model.handEnabled)
                        Toggle("home.head", isOn: $model.headEnabled)
                        Toggle(isOn: $model.practice) {
                            VStack(alignment: .leading) {
                                Text("home.practice")
                                Text("home.practice_d").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                    .card()

                    VStack(alignment: .leading, spacing: 8) {
                        Text("home.last").font(.headline)
                        Text(model.lastAction ?? NSLocalizedString("home.nothing", comment: ""))
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .card()

                    Label("home.privacy", systemImage: "lock")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 4)
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("app.name")
        }
    }
}

struct PowerButton: View {
    let running: Bool
    let action: () -> Void
    @State private var pulse = false

    var body: some View {
        Button(action: action) {
            ZStack {
                if running {
                    Circle().stroke(Brand.teal.opacity(pulse ? 0 : 0.5), lineWidth: 2)
                        .frame(width: pulse ? 176 : 140, height: pulse ? 176 : 140)
                        .animation(.easeOut(duration: 1.6).repeatForever(autoreverses: false), value: pulse)
                    Circle().fill(Brand.gradient).frame(width: 140, height: 140)
                } else {
                    Circle().fill(Color(.secondarySystemBackground)).frame(width: 140, height: 140)
                        .overlay(Circle().stroke(Color(.separator), lineWidth: 2))
                }
                Image(systemName: "power").font(.system(size: 48, weight: .semibold)).foregroundStyle(running ? .white : .secondary)
            }
            .frame(width: 180, height: 180)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text(LocalizedStringKey(running ? "a.stop" : "a.start")))
        .onAppear { pulse = true }
    }
}

extension View {
    func card() -> some View {
        padding(18)
            .background(RoundedRectangle(cornerRadius: 22, style: .continuous).fill(Color(.secondarySystemGroupedBackground)))
    }
}
