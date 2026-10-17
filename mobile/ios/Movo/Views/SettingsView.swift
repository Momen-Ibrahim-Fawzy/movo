import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var model: AppModel
    @State private var calibrating = false
    @State private var calStep = "eyes.cal_ready"
    @State private var calResult: Bool?

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
                Section("eyes.title") {
                    Toggle("home.eyes", isOn: $model.eyesEnabled)
                    Toggle("eyes.glasses", isOn: $model.eyesGlasses)
                    Text(LocalizedStringKey(model.eyesCalibrated ? "eyes.cal_status_done" : "eyes.cal_status_auto"))
                        .font(.footnote).foregroundStyle(.secondary)
                    Button("eyes.calibrate") { calibrating = true }.disabled(!model.running || !model.eyesEnabled)
                    if model.eyesCalibrated { Button("eyes.cal_reset", role: .destructive) { model.resetEyeCalibration() } }
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
                    Text("settings.developer").font(.footnote)
                    Link("LinkedIn", destination: URL(string: "https://www.linkedin.com/in/momen-ibrahim-fawzy-0b067a1b8/")!)
                    Link("GitHub", destination: URL(string: "https://github.com/Momen-Ibrahim-Fawzy")!)
                    LabeledContent("settings.version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "")
                }
            }
            .navigationTitle("nav.settings")
            .sheet(isPresented: $calibrating) {
                VStack(spacing: 18) {
                    Image(systemName: "eye").font(.system(size: 44)).foregroundStyle(Brand.accent)
                    if let ok = calResult {
                        Text(LocalizedStringKey(ok ? "eyes.cal_done" : "eyes.cal_failed")).font(.title3.bold())
                        Text(LocalizedStringKey(ok ? "eyes.cal_done_d" : "eyes.cal_failed_d")).multilineTextAlignment(.center).foregroundStyle(.secondary)
                        Button("eyes.cal_close") { calibrating = false }.buttonStyle(.borderedProminent)
                    } else {
                        Text(LocalizedStringKey(calStep)).font(.title3.bold())
                        Text(LocalizedStringKey(calStep + "_d")).multilineTextAlignment(.center).foregroundStyle(.secondary)
                        ProgressView()
                    }
                }
                .padding(32)
                .presentationDetents([.medium])
                .interactiveDismissDisabled(calResult == nil)
                .task {
                    calResult = nil
                    calResult = await model.calibrateEyes { calStep = $0 }
                }
            }
        }
    }
}
