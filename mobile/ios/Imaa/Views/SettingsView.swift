import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    NavigationLink("help.title") { HelpView() }
                }
                Section("settings.appearance") {
                    Picker("settings.theme", selection: $model.theme) {
                        Text("settings.system").tag("system")
                        Text("settings.light").tag("light")
                        Text("settings.dark").tag("dark")
                    }
                    Button("settings.language") {
                        if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
                    }
                }
                Section("settings.detection") {
                    Picker("settings.power", selection: $model.powerMode) {
                        Text("settings.power_eco").tag("eco")
                        Text("settings.power_balanced").tag("balanced")
                        Text("settings.power_performance").tag("performance")
                    }
                    VStack(alignment: .leading) {
                        Text("settings.hold")
                        Slider(value: $model.holdScale, in: 0.5...2)
                    }
                    VStack(alignment: .leading) {
                        Text("settings.head_sens")
                        Slider(value: $model.headSensitivity, in: 0.6...1.8)
                    }
                    Button("settings.recalibrate") { model.recalibrate() }
                }
                Section("settings.gestures") {
                    ForEach(Catalog.hand + Catalog.head) { g in
                        HStack {
                            Text(g.emoji)
                            Text(g.name)
                            Spacer()
                            Text(Catalog.viewerBindings[g.id]?.title ?? "—").foregroundStyle(.secondary).font(.footnote)
                        }
                    }
                }
                Section("settings.privacy") {
                    Text("settings.privacy_text").foregroundStyle(.secondary)
                }
                Section("settings.about") {
                    Text("settings.meaning").foregroundStyle(.secondary)
                    LabeledContent("settings.version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "")
                }
            }
            .navigationTitle("nav.settings")
        }
    }
}
